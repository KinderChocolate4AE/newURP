"""PPO (pure JAX) for either side. Defender = centralized residual policy over the scripted defense.
Attacker (red team) = residual over direct pursuit. Opponent is frozen (scripted or a saved network).

Attacker kinds: 0 direct, 1 weave, 2 evade (scripted), 3 learned red team (net params).
"""
import time, json, pickle, functools
from typing import NamedTuple
import jax, jax.numpy as jnp, numpy as np
from sim import *

EVAL_SEEDS = tuple(range(100001, 100009))  # 8 x 1000 episodes; never used for training


# ---------------- tiny MLP + Adam ----------------

def mlp_init(key, sizes, last_scale=0.01):
    ps = []
    for i, (a, b) in enumerate(zip(sizes[:-1], sizes[1:])):
        key, k = jax.random.split(key)
        sc = last_scale if i == len(sizes) - 2 else jnp.sqrt(2.0 / a)
        ps.append((jax.random.normal(k, (a, b)) * sc, jnp.zeros(b)))
    return ps


def mlp(ps, x):
    for w, b in ps[:-1]:
        x = jnp.tanh(x @ w + b)
    w, b = ps[-1]
    return x @ w + b


def adam_init(p):
    z = jax.tree.map(jnp.zeros_like, p)
    return (z, z, jnp.int32(0))


def adam(p, g, st, lr, b1=0.9, b2=0.999, eps=1e-8):
    m, v, t = st
    t = t + 1
    m = jax.tree.map(lambda m, g: b1 * m + (1 - b1) * g, m, g)
    v = jax.tree.map(lambda v, g: b2 * v + (1 - b2) * g * g, v, g)
    mh = 1 / (1 - b1 ** t); vh = 1 / (1 - b2 ** t)
    p = jax.tree.map(lambda p, m, v: p - lr * m * mh / (jnp.sqrt(v * vh) + eps), p, m, v)
    return p, (m, v, t)


# ---------------- sides ----------------

class Side(NamedTuple):
    name: str
    obs: callable      # s -> obs
    cont_dim: int
    has_fire: bool
    act: callable      # (s, cont, fire_bool) -> action for env
    fire_bias: callable  # s -> scalar logit bias
    reward: callable   # status -> reward at termination
    shape: callable    # (s, s2) -> dense shaping reward
    log_std0: float


def def_side(n, residual=True, log_std0=-2.3):
    def act(s, cont, fire):
        sc = def_script(s)
        base_l = sc.lim_acc if residual else 0.0
        base_n = sc.nd_acc if residual else 0.0
        return DefAct(base_l + P.lim_a * cont[:3 * n].reshape(n, 3), base_n + P.nd_a * cont[3 * n:], fire)
    bias = (lambda s: 3.0 * (2.0 * def_script(s).fire - 1.0)) if residual else (lambda s: -2.0)
    rew = lambda st: jnp.select([(st == 1) | (st == 2), st == 3], [1.0, -1.0], 0.0)
    return Side("def", def_obs, 3 * n + 3, True, act, bias, rew, lambda s, s2: 0.0, log_std0)


def att_base(s):
    return 3.0 * (P.att_v * unit(-s.ap) - s.av)


def att_side(log_std0=-0.7, shape_w=1.0):
    act = lambda s, cont, fire: att_base(s) + 2 * P.att_a * cont
    rew = lambda st: jnp.select([st == 3, st == 4], [1.0, -2.0], -1.0)  # timeout < intercept: no loitering exploit
    # progress toward the asset (sums to <=1 over an episode): gives signal even when every episode is intercepted
    shape = lambda s, s2: shape_w * (norm(s.ap) - norm(s2.ap)) / 600. * (s.status == 0)
    return Side("att", att_obs, 3, False, act, lambda s: 0.0, rew, shape, log_std0)


def init_params(key, side, n, hidden=256):
    s = reset(jax.random.PRNGKey(0), n)
    od = side.obs(s).shape[0]
    k1, k2 = jax.random.split(key)
    return dict(pi=mlp_init(k1, [od, hidden, hidden, side.cont_dim + side.has_fire], last_scale=0.0),  # start exactly at the base policy
                vf=mlp_init(k2, [od, hidden, hidden, 1], last_scale=1.0),
                log_std=jnp.full(side.cont_dim, side.log_std0))


def policy_fn(side, params):
    """Deterministic policy s -> env action."""
    def pol(s):
        out = mlp(params["pi"], side.obs(s))
        cont = out[:side.cont_dim]
        fire = (out[-1] + side.fire_bias(s) > 0) if side.has_fire else jnp.bool_(False)
        return side.act(s, cont, fire)
    return pol


def make_opponent(own, opp_side=None, opp_params=None):
    """Frozen opponent policy for env stepping. For defender training the attacker is
    script (kinds 0-2) or a red-team net (kind 3); for attacker training the defender is script or a net."""
    if own == "def":
        net = policy_fn(opp_side, opp_params) if opp_params is not None else None
        def att(s):
            a = att_script(s)
            return a if net is None else jnp.where(s.akind == 3, net(s), a)
        return att
    return policy_fn(opp_side, opp_params) if opp_params is not None else def_script


# ---------------- PPO ----------------

def train(side, n, opp, seed, iters, num_envs=2048, T=64, lr=3e-4, epochs=4, nmb=8, gamma=0.99, lam=0.95,
          clip=0.2, ent=1e-3, red_frac=0.0, init=None, log=None, use_net=True, use_lim=True, save=None):
    key = jax.random.PRNGKey(seed)
    key, kp = jax.random.split(key)
    params = init if init is not None else init_params(kp, side, n)
    opt = adam_init(params)

    def reset_one(k):
        k1, k2, k3 = jax.random.split(k, 3)
        s = reset(k1, n, use_net, use_lim)
        red = jax.random.uniform(k2) < red_frac
        return s._replace(akind=jnp.where(red, 3, s.akind))

    def env_step(s, action):
        if side.name == "def":
            s2 = step(s, action, opp(s))
        else:
            s2 = step(s, opp(s), action)
        done = s2.status != 0
        return s2, side.reward(s2.status) * done + side.shape(s, s2), done

    def sample(params, s, k):
        o = side.obs(s)
        out = mlp(params["pi"], o)
        mu = out[:side.cont_dim]
        std = jnp.exp(params["log_std"])
        k1, k2 = jax.random.split(k)
        cont = mu + std * jax.random.normal(k1, mu.shape)
        logp = jnp.sum(-0.5 * ((cont - mu) / std) ** 2 - params["log_std"] - 0.9189385)
        if side.has_fire:
            logit = out[-1] + side.fire_bias(s)
            fire = jax.random.uniform(k2) < jax.nn.sigmoid(logit)
            logp = logp + jnp.where(fire, jax.nn.log_sigmoid(logit), jax.nn.log_sigmoid(-logit))
        else:
            fire = jnp.bool_(False)
        v = mlp(params["vf"], o)[0]
        return o, cont, fire, logp, v

    def rollout(params, s, key):
        def body(carry, _):
            s, key = carry
            key, ka, kr = jax.random.split(key, 3)
            o, cont, fire, logp, v = jax.vmap(sample, (None, 0, 0))(params, s, jax.random.split(ka, num_envs))
            fb = jax.vmap(side.fire_bias)(s) if side.has_fire else jnp.zeros(num_envs)
            a = jax.vmap(side.act)(s, cont, fire)
            s2, r, d = jax.vmap(env_step)(s, a)
            st = s2.status
            sr = jax.vmap(reset_one)(jax.random.split(kr, num_envs))
            s2 = jax.tree.map(lambda x, y: jnp.where(d.reshape((-1,) + (1,) * (x.ndim - 1)), y, x), s2, sr)
            return (s2, key), (o, cont, fire, fb, logp, v, r, d, st)
        (s, key), tr = jax.lax.scan(body, (s, key), None, length=T)
        lastv = jax.vmap(lambda x: mlp(params["vf"], side.obs(x))[0])(s)
        return s, tr, lastv

    def gae(r, d, v, lastv):
        def body(nxt, x):
            adv_next, v_next = nxt
            r, d, v = x
            delta = r + gamma * v_next * (1 - d) - v
            adv = delta + gamma * lam * (1 - d) * adv_next
            return (adv, v), adv
        _, adv = jax.lax.scan(body, (jnp.zeros_like(lastv), lastv), (r, d, v), reverse=True)
        return adv, adv + v

    def loss_fn(params, b):
        o, cont, fire, fb, logp_old, adv, ret = b
        out = jax.vmap(lambda x: mlp(params["pi"], x))(o)
        mu = out[:, :side.cont_dim]
        std = jnp.exp(params["log_std"])
        logp = jnp.sum(-0.5 * ((cont - mu) / std) ** 2 - params["log_std"] - 0.9189385, -1)
        entropy = jnp.sum(params["log_std"])
        if side.has_fire:
            logit = out[:, -1] + fb
            logp = logp + jnp.where(fire, jax.nn.log_sigmoid(logit), jax.nn.log_sigmoid(-logit))
            pf = jax.nn.sigmoid(logit)
            entropy = entropy + jnp.mean(-(pf * jax.nn.log_sigmoid(logit) + (1 - pf) * jax.nn.log_sigmoid(-logit)))
        ratio = jnp.exp(logp - logp_old)
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)
        pl = -jnp.mean(jnp.minimum(ratio * adv, jnp.clip(ratio, 1 - clip, 1 + clip) * adv))
        v = jax.vmap(lambda x: mlp(params["vf"], x)[0])(o)
        vl = jnp.mean((v - ret) ** 2)
        return pl + 0.5 * vl - ent * entropy, (pl, vl)

    @jax.jit
    def update(params, opt, s, key):
        key, kr = jax.random.split(key)
        s, tr, lastv = rollout(params, s, kr)
        o, cont, fire, fb, logp, v, r, d, st = tr
        adv, ret = gae(r, d.astype(jnp.float32), v, lastv)
        flat = lambda x: x.reshape((T * num_envs,) + x.shape[2:])
        data = tuple(map(flat, (o, cont, fire, fb, logp, adv, ret)))
        N = T * num_envs
        mb = N // nmb

        def epoch(carry, k):
            params, opt = carry
            perm = jax.random.permutation(k, N)
            def mbstep(carry, i):
                params, opt = carry
                idx = jax.lax.dynamic_slice(perm, (i * mb,), (mb,))
                b = tuple(x[idx] for x in data)
                (l, aux), g = jax.value_and_grad(loss_fn, has_aux=True)(params, b)
                params, opt = adam(params, g, opt, lr)
                return (params, opt), aux
            (params, opt), aux = jax.lax.scan(mbstep, (params, opt), jnp.arange(nmb))
            return (params, opt), aux
        key, ke = jax.random.split(key)
        (params, opt), aux = jax.lax.scan(epoch, (params, opt), jax.random.split(ke, epochs))
        ndone = d.sum()
        stats = dict(done=ndone, icpt=((st == 1) | (st == 2)).sum() / jnp.maximum(ndone, 1),
                     leak=(st == 3).sum() / jnp.maximum(ndone, 1), pl=aux[0].mean(), vl=aux[1].mean(),
                     std=jnp.exp(params["log_std"]).mean())
        return params, opt, s, key, stats

    key, ks = jax.random.split(key)
    s = jax.vmap(reset_one)(jax.random.split(ks, num_envs))
    t0 = time.time()
    hist = []
    for it in range(iters):
        params, opt, s, key, stats = update(params, opt, s, key)
        if it % 10 == 0 or it == iters - 1:
            stats = {k: float(v) for k, v in stats.items()}
            stats.update(it=it, sec=round(time.time() - t0, 1))
            hist.append(stats)
            line = json.dumps(stats)
            print(line, flush=True)
            if log:
                open(log, "a").write(line + "\n")
            if save:
                pickle.dump(jax.device_get(params), open(save, "wb"))
    if save:
        pickle.dump(jax.device_get(params), open(save, "wb"))
    return params, hist


# ---------------- evaluation ----------------

def evaluate(n, def_pol, att_pol, eps=1000, seeds=EVAL_SEEDS, kind=None, use_net=True, use_lim=True):
    f = jax.jit(lambda k: run_episodes(k, eps, n, def_pol, att_pol, use_net, use_lim, kind).status)
    sts = [np.asarray(f(jax.random.PRNGKey(sd))) for sd in seeds]
    per = [summarize(x)["intercept"] for x in sts]
    tot = summarize(np.concatenate(sts))
    tot.update(seed_std=float(np.std(per)), seeds=len(seeds), eps_per_seed=eps)
    return tot


def red_pol(params):
    """Attacker policy from red-team params, usable as att_pol in evaluate()."""
    return policy_fn(att_side(), params)


def load(path):
    return jax.tree.map(jnp.asarray, pickle.load(open(path, "rb")))
