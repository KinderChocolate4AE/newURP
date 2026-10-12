"""WORLD-v1 (scoreboard S1) engagement simulator, pure JAX, single-env functions (vmap outside).

Status codes: 0 running, 1 net capture, 2 limiter kill, 3 leak (asset hit), 4 timeout.
"""
from typing import NamedTuple
import jax
import jax.numpy as jnp


class P:  # WORLD.md §1 nominal values. Changing any of these = new scoreboard.
    dt = 0.02; repeat = 5; T = 30.0
    att_v = 30.; att_a = 20.; att_tau = 0.20
    nd_v = 22.; nd_a = 8.; nd_tau = 0.30
    lim_v = 45.; lim_a = 30.; lim_tau = 0.10
    net_r = 1.5; net_speed = 25.; net_open = 0.25; net_tmax = 1.0; net_shots = 2; net_reload = 1.0
    kill_r = 2.5; asset_r = 3.0
    trk_sp = 1.0; trk_sv = 1.0  # defense track noise (m, m/s)
    trk_lag = 1  # defense track latency in control steps (x0.1 s)
    obs_hist = 0  # defender design (not world): # of past measured tracks in def_obs
    def_standoff = 40.0; def_fire_lo = 0.3; def_fire_hi = 0.7  # scripted-defense design (GK preset changes these)


WORLDS = {"S1": "", "S2": "trk_lag=3",
          "GK": "def_standoff=8,def_fire_lo=0.25,def_fire_hi=0.5"}  # GK = goalkeeper net-drone prior (defender design, not world)  # scoreboards: S2 = WORLD-v1.1 + 0.3 s defense track latency (LAB_LOG 03:21)


def set_world(spec):
    """'lim_a=25,att_v=40' -> mutate P (call before any jit). Returns dict of overrides."""
    out = {}
    spec = ",".join(WORLDS.get(t, t) for t in (spec or "").split(","))
    for kv in filter(None, (spec or "").split(",")):
        k, v = kv.split("=")
        assert hasattr(P, k), k
        setattr(P, k, type(getattr(P, k))(float(v)) if not isinstance(getattr(P, k), int) else int(v))
        out[k] = getattr(P, k)
    return out


CTRL_DT = P.dt * P.repeat
N_CTRL = int(round(P.T / CTRL_DT))  # 300 control steps per episode max


class S(NamedTuple):
    ap: jax.Array; av: jax.Array; aa: jax.Array            # attacker (3,)
    akind: jax.Array; aphase: jax.Array; asign: jax.Array  # scripted attacker type/phase/evade fallback dir
    dp: jax.Array; dv: jax.Array; da: jax.Array            # net drone (3,)
    shots: jax.Array; reload: jax.Array
    net_on: jax.Array; net_p: jax.Array; net_v: jax.Array; net_age: jax.Array
    lp: jax.Array; lv: jax.Array; la: jax.Array; lalive: jax.Array  # limiters (n,3)/(n,)
    t: jax.Array; status: jax.Array
    trk_p: jax.Array; trk_v: jax.Array; key: jax.Array  # defense's delayed noisy attacker track
    hist_p: jax.Array; hist_v: jax.Array  # (trk_lag,3) past true attacker states
    trk_prev: jax.Array  # (max(obs_hist,1),6) past *measured* tracks (p,v), oldest first


class DefAct(NamedTuple):
    lim_acc: jax.Array  # (n,3)
    nd_acc: jax.Array   # (3,)
    fire: jax.Array     # bool


def norm(x):
    return jnp.sqrt(jnp.sum(x * x, -1) + 1e-12)


def unit(x):
    return x / norm(x)[..., None]


def clipnorm(x, m):
    n = norm(x)[..., None]
    return x * jnp.minimum(1.0, m / n)


def cpa(d0, d1):
    """Min distance over a step when relative position moves linearly d0 -> d1."""
    e = d1 - d0
    s = jnp.clip(-jnp.sum(d0 * e, -1) / (jnp.sum(e * e, -1) + 1e-12), 0.0, 1.0)
    return norm(d0 + s[..., None] * e)


def kin(p, v, a, acmd, amax, vmax, tau, dt):
    a = a + (clipnorm(acmd, amax) - a) * (dt / tau)
    v = clipnorm(v + a * dt, vmax)
    p = p + v * dt
    below = p[..., 2] < 0
    p = p.at[..., 2].set(jnp.maximum(p[..., 2], 0.0))
    v = v.at[..., 2].set(jnp.where(below, jnp.maximum(v[..., 2], 0.0), v[..., 2]))
    return p, v, a


def lead_aim(r, w, s):
    """Direction u and time t so that r + w t = s u t (projectile speed s rel. to shooter). ok=False -> aim at r."""
    qa = jnp.sum(w * w) - s * s
    qb = 2 * jnp.sum(r * w)
    qc = jnp.sum(r * r)
    disc = qb * qb - 4 * qa * qc
    sq = jnp.sqrt(jnp.maximum(disc, 0.0))
    qa_safe = jnp.where(jnp.abs(qa) < 1e-6, 1e-6, qa)
    t1 = (-qb - sq) / (2 * qa_safe)
    t2 = (-qb + sq) / (2 * qa_safe)
    big = 1e9
    t1 = jnp.where(t1 > 1e-4, t1, big)
    t2 = jnp.where(t2 > 1e-4, t2, big)
    t = jnp.minimum(t1, t2)
    ok = (disc >= 0) & (t < big)
    t = jnp.where(ok, t, norm(r) / s)
    return unit(r + w * t), t, ok


def reset(key, n, use_net=True, use_lim=True, kind=None):
    k = jax.random.split(key, 7)
    R = jax.random.uniform(k[0], (), minval=500., maxval=700.)
    b = jax.random.uniform(k[1], (), minval=-jnp.pi / 3, maxval=jnp.pi / 3)
    alt = jax.random.uniform(k[2], (), minval=20., maxval=80.)
    ap = jnp.array([R * jnp.cos(b), R * jnp.sin(b), alt])
    akind = jax.random.randint(k[3], (), 0, 3) if kind is None else jnp.int32(kind)
    ang = jnp.linspace(-jnp.pi / 4, jnp.pi / 4, n) if n > 1 else jnp.zeros((n,))
    lp = jnp.stack([30 * jnp.cos(ang), 30 * jnp.sin(ang), jnp.full((n,), 20.)], -1)
    z3 = jnp.zeros(3)
    return S(ap=ap, av=25. * unit(-ap), aa=z3,
             akind=akind, aphase=jax.random.uniform(k[4], (), maxval=2 * jnp.pi),
             asign=unit(jax.random.normal(k[5], (3,))),
             dp=jnp.array([0., 0., 25.]), dv=z3, da=z3,
             shots=jnp.int32(P.net_shots if use_net else 0), reload=jnp.float32(0.),
             net_on=jnp.bool_(False), net_p=z3, net_v=z3, net_age=jnp.float32(0.),
             lp=lp, lv=jnp.zeros((n, 3)), la=jnp.zeros((n, 3)), lalive=jnp.full((n,), use_lim),
             t=jnp.float32(0.), status=jnp.int32(0),
             trk_p=ap + P.trk_sp * jax.random.normal(k[6], (3,)), trk_v=25. * unit(-ap), key=jax.random.fold_in(k[6], 1),
             hist_p=jnp.tile(ap, (P.trk_lag, 1)), hist_v=jnp.tile(25. * unit(-ap), (P.trk_lag, 1)),
             trk_prev=jnp.tile(jnp.concatenate([ap, 25. * unit(-ap)]), (max(P.obs_hist, 1), 1)))


def _substep(s, dact, aacc):
    dt = P.dt
    run = s.status == 0
    ap, av, aa = kin(s.ap, s.av, s.aa, aacc, P.att_a, P.att_v, P.att_tau, dt)
    dp, dv, da = kin(s.dp, s.dv, s.da, dact.nd_acc, P.nd_a, P.nd_v, P.nd_tau, dt)
    lp, lv, la = kin(s.lp, s.lv, s.la, dact.lim_acc, P.lim_a, P.lim_v, P.lim_tau, dt)
    alive = s.lalive[:, None]
    lp, lv, la = (jnp.where(alive, x1, x0) for x1, x0 in ((lp, s.lp), (lv, s.lv), (la, s.la)))
    net_p = s.net_p + s.net_v * dt
    age = s.net_age + dt

    leak = cpa(s.ap, ap) <= P.asset_r
    lhit = s.lalive & (cpa(s.ap[None] - s.lp, ap[None] - lp) <= P.kill_r)
    nhit = s.net_on & (age >= P.net_open) & (s.net_age <= P.net_tmax) & (cpa(s.ap - s.net_p, ap - net_p) <= P.net_r)
    t = s.t + dt
    # leak wins ties (conservative for the defense)
    status = jnp.where(leak, 3, jnp.where(nhit, 1, jnp.where(lhit.any(), 2, jnp.where(t >= P.T - 1e-6, 4, 0))))
    new = s._replace(ap=ap, av=av, aa=aa, dp=dp, dv=dv, da=da, lp=lp, lv=lv, la=la,
                     lalive=s.lalive & ~lhit, net_p=net_p, net_age=age,
                     net_on=s.net_on & (age <= P.net_tmax), reload=s.reload - dt, t=t, status=status)
    return jax.tree.map(lambda a, b: jnp.where(run, a, b), new, s)


def fire_net(s, fire):
    u, th, ok = lead_aim(s.trk_p - s.dp, s.trk_v - s.dv, P.net_speed)
    # fire-control interlock: no shot without an intercept solution inside the net's flight time
    can = fire & (s.shots > 0) & (s.reload <= 0) & ~s.net_on & (s.status == 0) & ok & (th <= P.net_tmax)
    return s._replace(net_on=s.net_on | can,
                      net_p=jnp.where(can, s.dp, s.net_p),
                      net_v=jnp.where(can, s.dv + P.net_speed * u, s.net_v),
                      net_age=jnp.where(can, 0., s.net_age),
                      shots=s.shots - can.astype(jnp.int32),
                      reload=jnp.where(can, P.net_reload, s.reload))


def step(s, dact, aacc):
    """One control step (CTRL_DT) with zero-order-hold commands."""
    s = fire_net(s, dact.fire)
    key, kp, kv = jax.random.split(s.key, 3)
    ap0, av0 = s.ap, s.av
    s = jax.lax.fori_loop(0, P.repeat, lambda i, x: _substep(x, dact, aacc), s)
    hp = jnp.concatenate([s.hist_p[1:], ap0[None]])
    hv = jnp.concatenate([s.hist_v[1:], av0[None]])
    tp = jnp.concatenate([s.trk_prev[1:], jnp.concatenate([s.trk_p, s.trk_v])[None]])
    return s._replace(key=key, hist_p=hp, hist_v=hv, trk_prev=tp, trk_p=hp[0] + P.trk_sp * jax.random.normal(kp, (3,)),
                      trk_v=hv[0] + P.trk_sv * jax.random.normal(kv, (3,)))


# ---------------- scripted policies ----------------

def _threat(ap, av, tp, tv, on, horizon):
    """(tgo, evade dir) for one threat; tgo=inf if not threatening."""
    r = ap - tp
    w = av - tv
    d = norm(r)
    closing = -jnp.sum(r * w) / d
    tgo = d / jnp.maximum(closing, 1e-3)
    zem = r + w * tgo  # miss vector at closest approach -> push it further out
    threat = on & (closing > 0) & (tgo < horizon) & (d < 150)
    return jnp.where(threat, tgo, jnp.inf), zem


def att_script(s):
    to = -s.ap
    dist = norm(to)
    acc = 3.0 * (P.att_v * unit(to) - s.av)
    lat = unit(jnp.array([to[1], -to[0], 0.]) + 1e-6)
    weave = 0.8 * P.att_a * jnp.sin(2 * jnp.pi * 0.5 * s.t + s.aphase) * lat
    acc_weave = jnp.where(dist > 60, acc + weave, acc)
    tg_l, zem_l = jax.vmap(_threat, (None, None, 0, 0, 0, None))(s.ap, s.av, s.lp, s.lv, s.lalive, 1.5)
    tg_n, zem_n = _threat(s.ap, s.av, s.net_p, s.net_v, s.net_on, 1.0)
    tg = jnp.concatenate([tg_l, tg_n[None]])
    zem = jnp.concatenate([zem_l, zem_n[None]])
    i = jnp.argmin(tg)
    z = zem[i]
    z = jnp.where(norm(z) < 0.3, s.asign, z)
    acc_evade = jnp.where(jnp.isfinite(tg[i]) & (dist > 30), P.att_a * unit(z), acc)
    return jnp.select([s.akind == 0, s.akind == 1], [acc, acc_weave], acc_evade)


def lim_pn(lp, lv, ap, av, N=4.0):
    r = ap - lp
    w = av - lv
    d = norm(r)
    ru = r / d
    closing = -jnp.sum(r * w) / d
    tgo = d / jnp.maximum(closing, 5.0)
    zem = r + w * tgo
    zperp = zem - jnp.sum(zem * ru) * ru
    alat = clipnorm(N * zperp / tgo ** 2, P.lim_a)
    rem = jnp.sqrt(jnp.maximum(P.lim_a ** 2 - jnp.sum(alat * alat), 0.0))
    return alat + rem * ru


def def_script(s, fire_lo=None, fire_hi=None, standoff=None):
    fire_lo = P.def_fire_lo if fire_lo is None else fire_lo
    fire_hi = P.def_fire_hi if fire_hi is None else fire_hi
    standoff = P.def_standoff if standoff is None else standoff
    lim = jax.vmap(lim_pn, (0, 0, None, None))(s.lp, s.lv, s.trk_p, s.trk_v)
    goal = s.trk_p * (standoff / norm(s.trk_p))
    nd = 1.5 * (goal - s.dp) - 2.0 * s.dv
    _, th, ok = lead_aim(s.trk_p - s.dp, s.trk_v - s.dv, P.net_speed)
    fire = ok & (th >= fire_lo) & (th <= fire_hi)
    return DefAct(lim, nd, fire)


# ---------------- observations ----------------

def def_obs(s, script=None):
    script = def_script(s) if script is None else script
    lrel = (s.trk_p[None] - s.lp) / 100.
    return jnp.concatenate([
        s.trk_p / 100., s.trk_v / 30.,
        s.dp / 100., s.dv / 30., (s.trk_p - s.dp) / 100.,
        jnp.array([s.shots / 2., jnp.maximum(s.reload, 0.), s.net_on, s.net_age, s.t / 30.]),
        lrel.ravel(), (s.lv / 45.).ravel(), s.lalive.astype(jnp.float32),
        (script.lim_acc / P.lim_a).ravel(), script.nd_acc / P.nd_a, script.fire[None].astype(jnp.float32),
    ] + ([((jnp.concatenate([s.trk_p, s.trk_v])[None] - s.trk_prev[-P.obs_hist:]) / 10.).ravel()] if P.obs_hist else []))


def att_obs(s):
    rel = lambda p: (p - s.ap) / 100.
    return jnp.concatenate([
        s.ap / 100., s.av / 30., s.aa / 20.,
        rel(s.dp), s.dv / 30.,
        rel(s.net_p) * s.net_on, s.net_v / 30. * s.net_on, jnp.array([s.net_on, s.net_age, s.shots / 2., s.t / 30.]),
        jax.vmap(rel)(s.lp).ravel() , (s.lv / 45.).ravel(), s.lalive.astype(jnp.float32),
    ])


# ---------------- evaluation ----------------

def run_episodes(key, n_eps, n, def_pol, att_pol, use_net=True, use_lim=True, kind=None):
    """def_pol(s)->DefAct, att_pol(s)->acc (deterministic, single env). Returns final S (batched)."""
    s0 = jax.vmap(lambda k: reset(k, n, use_net, use_lim, kind))(jax.random.split(key, n_eps))

    def body(s, _):
        s = jax.vmap(lambda x: step(x, def_pol(x), att_pol(x)))(s)
        return s, None

    s, _ = jax.lax.scan(body, s0, None, length=int(round(P.T / CTRL_DT)))  # obs time is normalized by a fixed 30 s
    return s


def summarize(status):
    status = jnp.asarray(status)
    n = status.size
    f = lambda c: float(jnp.mean(c))
    return dict(n=int(n), intercept=f((status == 1) | (status == 2)), net=f(status == 1), lim=f(status == 2),
                leak=f(status == 3), timeout=f(status == 4))
