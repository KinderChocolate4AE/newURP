"""FS1 정책·가치망 + PPO 갱신 (docs/123). 양 팀 공용 빌딩 블록.

행동은 정규화 공간: 연속 = Gaussian raw sample (env 쪽에서 [-1,1] clip 후 스케일),
이산 = Bernoulli. ratio 는 raw sample 로 계산 (repo 관례, mappo.py 와 동일).
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Bernoulli, Normal

HID = (256, 256)                      # G&B: 2×256 ReLU
BIN_INIT_LOGIT = -5.0
STD_FLOOR = 1.0                       # RunningNorm std 하한 (원 단위)                 # FIRE/commit 초기 p≈0.7%/step (gate 제거 후 즉시 발사 방지)


def mlp(i, o, hid=HID, head_gain=0.01):
    layers, d = [], i
    for h in hid:
        lin = nn.Linear(d, h)
        nn.init.orthogonal_(lin.weight, np.sqrt(2)); nn.init.zeros_(lin.bias)
        layers += [lin, nn.ReLU()]; d = h
    head = nn.Linear(d, o)
    nn.init.orthogonal_(head.weight, head_gain); nn.init.zeros_(head.bias)
    return nn.Sequential(*layers, head)


class Actor(nn.Module):
    """연속 n_cont (Gaussian) + 이산 n_bin (Bernoulli)."""

    def __init__(self, obs_dim, n_cont, n_bin=0, init_log_std=-0.5):
        super().__init__()
        self.n_cont, self.n_bin = n_cont, n_bin
        self.net = mlp(obs_dim, n_cont + n_bin)
        with torch.no_grad():
            self.net[-1].bias[n_cont:] = BIN_INIT_LOGIT
        self.log_std = nn.Parameter(torch.full((n_cont,), float(init_log_std)))

    def dists(self, obs):
        out = self.net(obs)
        mu, logit = out[..., :self.n_cont], out[..., self.n_cont:]
        std = self.log_std.clamp(-3.0, 1.0).exp().expand_as(mu)
        return Normal(mu, std), (Bernoulli(logits=logit) if self.n_bin else None)

    @torch.no_grad()
    def act(self, obs, deterministic=False):
        g, b = self.dists(obs)
        c = g.mean if deterministic else g.sample()
        lp = g.log_prob(c).sum(-1)
        if b is None:
            return c, lp
        k = (b.probs > 0.5).float() if deterministic else b.sample()
        return torch.cat([c, k], -1), lp + b.log_prob(k).sum(-1)

    def evaluate(self, obs, a):
        g, b = self.dists(obs)
        c, k = a[..., :self.n_cont], a[..., self.n_cont:]
        lp, ent = g.log_prob(c).sum(-1), g.entropy().sum(-1)
        if b is not None:
            lp = lp + b.log_prob(k).sum(-1)
            ent = ent + b.entropy().sum(-1)
        return lp, ent


class RunningNorm:
    def __init__(self, dim):
        self.n, self.mean, self.m2 = 1e-4, np.zeros(dim), np.ones(dim)

    def update(self, x):
        x = np.asarray(x, np.float64).reshape(-1, self.mean.size)
        for row in (x.mean(0, keepdims=True),):     # batch Welford (Chan)
            nb = x.shape[0]; d = row[0] - self.mean; tot = self.n + nb
            self.mean = self.mean + d * nb / tot
            self.m2 = self.m2 + x.var(0) * nb + d ** 2 * self.n * nb / tot
            self.n = tot

    def __call__(self, x):
        # std 하한: 데이터에서 상수였던 채널 (예: BC 의 정지 방어자 속도) 이 작은 변화에
        # ±10 으로 폭주하지 않게 한다 (BC 검증 2026-10-04).
        std = np.maximum(np.sqrt(self.m2 / self.n), STD_FLOOR)
        return np.clip((x - self.mean) / std, -10, 10).astype(np.float32)

    def state(self):
        return {"n": self.n, "mean": self.mean.copy(), "m2": self.m2.copy()}

    def load(self, s):
        self.n, self.mean, self.m2 = s["n"], np.array(s["mean"]), np.array(s["m2"])


class Team(nn.Module):
    """한 팀의 actor 묶음 + 중앙 critic. roles = {name: (n_cont, n_bin, n_copies)}.
    n_copies > 1 이면 parameter sharing + one-hot id 를 관측에 붙인다.
    init_log_std = {role: float} (기본 −0.5)."""

    def __init__(self, obs_dim, roles: dict, init_log_std: dict | None = None,
                 disc: tuple | None = None):
        super().__init__()
        self.roles = roles
        # 다양성 판별기 (공격자 스타일 z 예측, DIAYN 식): disc = (in_dim, z_dim)
        self.disc = mlp(disc[0], disc[1], hid=(128, 128), head_gain=1.0) if disc else None
        ils = init_log_std or {}
        self.actors = nn.ModuleDict({
            r: Actor(obs_dim + (n if n > 1 else 0), c, b, ils.get(r, -0.5))
            for r, (c, b, n) in roles.items()})
        self.critic = mlp(obs_dim, 1, head_gain=1.0)
        self.norm = RunningNorm(obs_dim)

    def role_inputs(self, role, obs_n):
        n = self.roles[role][2]
        if n == 1:
            return obs_n[None]
        return np.concatenate([np.repeat(obs_n[None], n, 0), np.eye(n, dtype=np.float32)], 1)

    @torch.no_grad()
    def act(self, obs, deterministic=False):
        """obs (raw, 1 step) → {role: (inputs, actions (n, d), logp (n,))}, value."""
        on = self.norm(obs)
        out = {}
        for r in self.roles:
            x = torch.as_tensor(self.role_inputs(r, on))
            a, lp = self.actors[r].act(x, deterministic)
            out[r] = (x.numpy(), a.numpy(), lp.numpy())
        v = float(self.critic(torch.as_tensor(on)[None])[0, 0])
        return out, v, on

    def snapshot(self):
        # numpy 로 보관: torch 텐서를 워커로 pickle 하면 Linux 에서 텐서마다 fd 를 열어
        # "Too many open files" 로 멈춘다 (서버 run0 2026-10-04).
        return {"sd": {k: v.detach().cpu().numpy().copy() for k, v in self.state_dict().items()},
                "norm": self.norm.state()}

    def load_snapshot(self, s):
        self.load_state_dict({k: torch.as_tensor(v) for k, v in s["sd"].items()})
        self.norm.load(s["norm"])


def gae(rew, val, done, gamma, lam):
    T = len(rew); adv = np.zeros(T); last = 0.0
    for t in reversed(range(T)):
        nv = 0.0 if done[t] else val[t + 1] if t + 1 < T else 0.0
        d = rew[t] + gamma * nv - val[t]
        last = d + gamma * lam * (0.0 if done[t] else last)
        adv[t] = last
    return adv, adv + np.asarray(val[:T])


def ppo_update(team: Team, opt, batch: dict, *, epochs=5, mb=4096, clip=0.2,
               ent=0.01, vf=0.5, max_grad=0.5, target_kl=0.03):
    """batch: obs_n (T,D), ret (T,), adv (T,), roles {r: (x (M,·), a, lp_old, adv_idx (M,))}.
    target_kl: 어느 role 이든 approx KL > 1.5·target_kl 이면 남은 epoch 중단 (좁은 BC
    정책에서 Adam 초기 step 이 정책을 수십 nat 밀어내던 문제, 2026-10-04)."""
    adv = batch["adv"]; adv = (adv - adv.mean()) / (adv.std() + 1e-8)
    obs = torch.as_tensor(batch["obs_n"]); ret = torch.as_tensor(batch["ret"], dtype=torch.float32)
    T = len(ret); stats = {}; stop = False; n_ep = 0
    for _ in range(epochs):
        perm = np.random.permutation(T)
        for s in range(0, T, mb):
            idx = perm[s:s + mb]; sel = set(idx.tolist())
            loss = vf * ((team.critic(obs[idx])[:, 0] - ret[idx]) ** 2).mean()
            for r, (x, a, lp0, ti) in batch["roles"].items():
                m = np.fromiter((t in sel for t in ti), bool, len(ti))
                if not m.any():
                    continue
                lp, en = team.actors[r].evaluate(torch.as_tensor(x[m]), torch.as_tensor(a[m]))
                logr = lp - torch.as_tensor(lp0[m])
                ratio = logr.exp()
                A = torch.as_tensor(adv[ti[m]], dtype=torch.float32)
                pg = -torch.min(ratio * A, ratio.clamp(1 - clip, 1 + clip) * A).mean()
                loss = loss + pg - ent * en.mean()
                kl = float(((ratio - 1) - logr).mean().detach())       # approx KL (k3)
                stats[f"{r}_ratio"] = float(ratio.mean().detach()); stats[f"{r}_kl"] = round(kl, 5)
                stop = stop or kl > 1.5 * target_kl
            opt.zero_grad(); loss.backward()
            nn.utils.clip_grad_norm_(team.parameters(), max_grad); opt.step()
            if stop:
                break
        n_ep += 1
        if stop:
            break
    stats["loss"] = float(loss.detach()); stats["epochs"] = n_ep
    return stats
