"""MAPPO building blocks (L2 Phase 2C, docs/09 SS5 Phase 2C).

2B (IPPO) + ONE central critic = CTDE. The actors are the 2B designs
unchanged (limiter: parameter-shared Gaussian + one-hot agent id; finisher:
Gaussian axis + Bernoulli fire); what changes is the VALUE pathway:

  * central critic input = the SHARED 63-dim obs (ratified 2026-07-04):
    obs == env.state() (54 kinematic) + FSM (6) + v-triple (3), i.e. a strict
    superset of the plan's literal "env.state()" -- a critic blind to the
    magazine/fire state cannot price the pre/post-commit value change.
  * ONE value stream per env step (not per agent): all cooperative agents
    share the reward J, so GAE runs once and every actor consumes the same
    advantage. This removes the 2B artifact of N+1 critics re-learning the
    same target through different heads.
  * MAPPO tricks (ratified ON, 2026-07-04): value-target normalization
    (shepherd/train/value_norm.py) + orthogonal init (hidden gain sqrt(2),
    policy head 0.01, value head 1.0). Ablation caveat: 2C differs from 2B by
    {central critic, value norm, ortho init} -- state this when reading the
    IPPO->MAPPO comparison.

Phase-1/2B conventions kept: state-independent log-std with forward clamp,
actions in NORMALIZED [-1,1] (runner scales), raw-sample ratios, rollout-level
advantage normalization (gae.py), target-KL epoch early stop, set_lr hook.
"""
from __future__ import annotations

import itertools
import pathlib
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Bernoulli, Normal

from shepherd.train.gae import compute_gae, normalize_advantages
from shepherd.train.ppo import _mlp
from shepherd.train.value_norm import ValueNorm

__all__ = ["MAPPOConfig", "GaussianActor", "MixedActor", "CentralCritic",
           "MAPPORollout", "MAPPOTrainer", "ortho_init_", "coma_advantages"]


def coma_advantages(coma_D, dones, gamma: float, lam: float):
    """(T, N) one-step-shifted analytic D -> (T, N) difference-return
    advantages: the (gamma*lam)-discounted forward sum of each limiter's D
    stream (compute_gae with V == 0), stopping at episode boundaries.
    gamma=0 recovers the purely myopic per-step D_i."""
    coma_D = np.asarray(coma_D, dtype=np.float64)
    T, N = coma_D.shape
    zeros = np.zeros(T)
    return np.stack([compute_gae(coma_D[:, i], zeros, zeros,
                                 np.asarray(dones, np.float64), gamma, lam)[0]
                     for i in range(N)], axis=1)

LOG_STD_MIN, LOG_STD_MAX = -5.0, 2.0


def ortho_init_(mlp: nn.Sequential, head_gain: float) -> None:
    """Orthogonal init for an ``_mlp`` stack: hidden Linears gain sqrt(2),
    the LAST Linear gets ``head_gain`` (0.01 policy heads / 1.0 value head --
    CleanRL/MAPPO convention). Biases zero."""
    linears = [m for m in mlp if isinstance(m, nn.Linear)]
    for i, lin in enumerate(linears):
        gain = head_gain if i == len(linears) - 1 else float(np.sqrt(2.0))
        nn.init.orthogonal_(lin.weight, gain=gain)
        nn.init.zeros_(lin.bias)


# ---------------------------------------------------------------- config ---
@dataclass
class MAPPOConfig:
    total_timesteps: int = 200_000
    rollout_steps: int = 512
    epochs: int = 10
    minibatch_size: int = 128          # TIME indices (limiter rows = x N)
    lr: float = 3e-4
    max_grad_norm: float = 0.5

    clip_eps: float = 0.2
    gamma: float = 0.99
    lam: float = 0.95
    ent_coef_limiter: float = 0.0
    ent_coef_finisher: float = 0.003
    vf_coef: float = 0.5
    target_kl: Optional[float] = 0.02  # epoch early stop on max(role KLs)

    hidden_sizes: tuple[int, ...] = (128, 128)
    init_log_std: float = 0.0
    ortho_init: bool = True            # ratified ON (2026-07-04)
    value_norm: bool = True            # ratified ON (2026-07-04)

    # Phase 2D -- COMA difference-reward credit for limiters (D1-A stage 1,
    # docs/09 SS1/SS5). coma_mix blends the limiter advantage:
    #   adv_lim = (1-mix)*A_shared + mix*A_D
    # where A_D = normalized (coma_gamma*coma_lam)-discounted forward sum of
    # the ONE-STEP-SHIFTED analytic coma_D (the runner assigns step t+1's
    # pre-move D to action t -- causality; see train_mappo.py). mix=0 -> exact
    # 2C behavior (coma arrays ignored). mix=1 -> the ratified "use D_i as the
    # limiter advantage" literal form. CAVEAT (flagged in docs/09 SS8): at
    # mix=1 the limiter gradient no longer sees the shared J's -lambda3 loss
    # cost; if limiter_loss regresses, mix=0.5 is the documented fallback arm.
    coma_mix: float = 0.0
    coma_gamma: float = 0.99
    coma_lam: float = 0.95

    seed: int = 0
    device: str = "cpu"

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "MAPPOConfig":
        d = dict(d or {})
        if d.get("hidden_sizes") is not None:
            d["hidden_sizes"] = tuple(d["hidden_sizes"])
        unknown = set(d) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown MAPPOConfig keys: {sorted(unknown)}")
        return cls(**d)


# ---------------------------------------------------------------- actors ---
class GaussianActor(nn.Module):
    """Limiter actor: Gaussian mean MLP + state-independent log-std (no critic)."""

    def __init__(self, obs_dim: int, act_dim: int,
                 hidden_sizes: tuple[int, ...] = (64, 64),
                 init_log_std: float = 0.0, ortho: bool = True) -> None:
        super().__init__()
        self.mean = _mlp(obs_dim, hidden_sizes, act_dim)
        self.log_std = nn.Parameter(torch.full((act_dim,), float(init_log_std)))
        if ortho:
            ortho_init_(self.mean, head_gain=0.01)

    def _dist(self, obs: torch.Tensor) -> Normal:
        log_std = self.log_std.clamp(LOG_STD_MIN, LOG_STD_MAX)
        mean = self.mean(obs)
        return Normal(mean, log_std.exp().expand_as(mean))

    @torch.no_grad()
    def act(self, obs: torch.Tensor, deterministic: bool = False):
        dist = self._dist(obs)
        raw = dist.mean if deterministic else dist.sample()
        return raw, dist.log_prob(raw).sum(-1)

    def evaluate(self, obs: torch.Tensor, raw: torch.Tensor):
        dist = self._dist(obs)
        return dist.log_prob(raw).sum(-1), dist.entropy().sum(-1)


class MixedActor(nn.Module):
    """Finisher actor: Gaussian(cont) + Bernoulli(fire) heads (no critic).
    Same head semantics as 2B MixedActorCritic (exact {0,1} fire sample)."""

    def __init__(self, obs_dim: int, cont_dim: int,
                 hidden_sizes: tuple[int, ...] = (64, 64),
                 init_log_std: float = 0.0, ortho: bool = True) -> None:
        super().__init__()
        self.cont_dim = int(cont_dim)
        self.mean = _mlp(obs_dim, hidden_sizes, cont_dim)
        self.fire_logit = _mlp(obs_dim, hidden_sizes, 1)
        self.log_std = nn.Parameter(torch.full((cont_dim,), float(init_log_std)))
        if ortho:
            ortho_init_(self.mean, head_gain=0.01)
            ortho_init_(self.fire_logit, head_gain=0.01)

    def _dists(self, obs: torch.Tensor):
        log_std = self.log_std.clamp(LOG_STD_MIN, LOG_STD_MAX)
        mean = self.mean(obs)
        return (Normal(mean, log_std.exp().expand_as(mean)),
                Bernoulli(logits=self.fire_logit(obs)))

    @torch.no_grad()
    def act(self, obs: torch.Tensor, deterministic: bool = False):
        dist_g, dist_b = self._dists(obs)
        g = dist_g.mean if deterministic else dist_g.sample()
        fire = (dist_b.probs > 0.5).float() if deterministic else dist_b.sample()
        raw = torch.cat([g, fire], dim=-1)
        logp = dist_g.log_prob(g).sum(-1) + dist_b.log_prob(fire).sum(-1)
        return raw, logp

    def evaluate(self, obs: torch.Tensor, raw: torch.Tensor):
        dist_g, dist_b = self._dists(obs)
        g, fire = raw[..., : self.cont_dim], raw[..., self.cont_dim:]
        logp = dist_g.log_prob(g).sum(-1) + dist_b.log_prob(fire).sum(-1)
        ent = dist_g.entropy().sum(-1) + dist_b.entropy().sum(-1)
        return logp, ent


class CentralCritic(nn.Module):
    """ONE value function on the shared full-state obs (CTDE central critic)."""

    def __init__(self, obs_dim: int, hidden_sizes: tuple[int, ...] = (64, 64),
                 ortho: bool = True) -> None:
        super().__init__()
        self.v = _mlp(obs_dim, hidden_sizes, 1)
        if ortho:
            ortho_init_(self.v, head_gain=1.0)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.v(obs).squeeze(-1)


# ---------------------------------------------------------------- rollout ---
class MAPPORollout:
    """Fixed-size on-policy buffer: ONE row per env step (shared obs/reward/
    value), with per-limiter and finisher action/log-prob blocks."""

    def __init__(self, size: int, obs_dim: int, n_limiters: int) -> None:
        self.size, self.obs_dim, self.n = size, obs_dim, n_limiters
        self.obs = np.zeros((size, obs_dim), np.float32)
        self.lim_raw = np.zeros((size, n_limiters, 3), np.float32)
        self.lim_clip = np.zeros((size, n_limiters, 3), np.float32)
        self.lim_logp = np.zeros((size, n_limiters), np.float32)
        self.fin_raw = np.zeros((size, 4), np.float32)
        self.fin_clip = np.zeros((size, 4), np.float32)
        self.fin_logp = np.zeros(size, np.float32)
        self.rewards = np.zeros(size, np.float32)
        self.values = np.zeros(size, np.float32)        # DENORMALIZED V(s_t)
        self.next_values = np.zeros(size, np.float32)   # denorm bootstrap
        self.dones = np.zeros(size, np.float32)
        # Phase 2D: ONE-STEP-SHIFTED analytic coma_D per limiter -- row t holds
        # the D computed on the state action t PRODUCED (the runner writes it
        # back when step t+1 returns; stays 0 for the last action of an
        # episode/rollout). Ignored unless cfg.coma_mix > 0.
        self.coma_D = np.zeros((size, n_limiters), np.float32)
        self._i = 0

    def add(self, **kw) -> None:
        i = self._i
        if i >= self.size:
            raise IndexError("MAPPORollout is full")
        for k, v in kw.items():
            getattr(self, k)[i] = v
        self._i += 1

    @property
    def full(self) -> bool:
        return self._i >= self.size

    def reset(self) -> None:
        self._i = 0
        # coma_D rows are written BACK one step later (train_mappo.py), so a
        # row that never gets its write-back (episode/rollout tail) must read
        # 0, not a stale value from the previous rollout.
        self.coma_D[:] = 0.0

    def clip_fraction_action(self, atol: float = 1e-6) -> float:
        lim = np.abs(self.lim_raw - self.lim_clip) > atol
        fin = np.abs(self.fin_raw - self.fin_clip) > atol
        return float((lim.sum() + fin.sum()) / (lim.size + fin.size))


# ---------------------------------------------------------------- trainer ---
class MAPPOTrainer:
    """Two actors + one central critic + one optimizer (single loss, Phase-1
    pattern). Runner owns global seeding and the LR schedule (set_lr)."""

    def __init__(self, obs_dim: int, n_limiters: int, cfg: MAPPOConfig) -> None:
        self.cfg = cfg
        self.obs_dim = obs_dim
        self.n = int(n_limiters)
        self.device = torch.device(cfg.device)
        self.lim_actor = GaussianActor(obs_dim + self.n, 3, cfg.hidden_sizes,
                                       cfg.init_log_std, cfg.ortho_init).to(self.device)
        self.fin_actor = MixedActor(obs_dim, 3, cfg.hidden_sizes,
                                    cfg.init_log_std, cfg.ortho_init).to(self.device)
        self.critic = CentralCritic(obs_dim, cfg.hidden_sizes,
                                    cfg.ortho_init).to(self.device)
        self.optimizer = torch.optim.Adam(self.parameters(), lr=cfg.lr)
        self.value_norm = ValueNorm() if cfg.value_norm else None
        self._rng = np.random.default_rng(cfg.seed)
        self._eye = np.eye(self.n, dtype=np.float32)

    def parameters(self):
        return itertools.chain(self.lim_actor.parameters(),
                               self.fin_actor.parameters(),
                               self.critic.parameters())

    def set_lr(self, lr: float) -> None:
        for group in self.optimizer.param_groups:
            group["lr"] = float(lr)

    # ------------------------------------------------------------- values ---
    @torch.no_grad()
    def value_np(self, obs_np: np.ndarray) -> float:
        """DENORMALIZED V(s) for rollout collection / bootstraps."""
        t = torch.as_tensor(obs_np[None, :], dtype=torch.float32, device=self.device)
        v = float(self.critic(t)[0].item())
        if self.value_norm is not None:
            v = float(self.value_norm.denormalize(v))
        return v

    def _lim_inputs_flat(self, obs: np.ndarray) -> np.ndarray:
        """(T,obs) -> (T*N, obs+N): shared obs repeated + one-hot ids."""
        T = obs.shape[0]
        rep = np.repeat(obs, self.n, axis=0)
        eye = np.tile(self._eye, (T, 1))
        return np.concatenate([rep, eye], axis=1)

    # ------------------------------------------------------------- update ---
    def update(self, buf: MAPPORollout) -> dict:
        cfg = self.cfg
        if not buf.full:
            raise ValueError(f"MAPPORollout not full: {buf._i}/{buf.size}")
        T, N = buf.size, self.n

        adv_np, ret_np = compute_gae(buf.rewards, buf.values, buf.next_values,
                                     buf.dones, cfg.gamma, cfg.lam)
        adv_np = normalize_advantages(adv_np)
        explained_var = 1.0 - float(np.var(ret_np - buf.values)
                                    / (np.var(ret_np) + 1e-8))
        if self.value_norm is not None:
            self.value_norm.update(ret_np)
            targets_np = self.value_norm.normalize(ret_np)
        else:
            targets_np = ret_np

        dev = self.device
        obs = torch.as_tensor(buf.obs, device=dev)
        lim_in = torch.as_tensor(self._lim_inputs_flat(buf.obs), device=dev)
        lim_raw = torch.as_tensor(buf.lim_raw.reshape(T * N, 3), device=dev)
        lim_old = torch.as_tensor(buf.lim_logp.reshape(T * N), device=dev)
        fin_raw = torch.as_tensor(buf.fin_raw, device=dev)
        fin_old = torch.as_tensor(buf.fin_logp, device=dev)
        adv = torch.as_tensor(adv_np.astype(np.float32), device=dev)
        adv_lim_np = np.repeat(adv_np, N)
        coma_stats = {}
        if cfg.coma_mix > 0.0:
            # Phase 2D: per-limiter difference-return advantage from the
            # shifted analytic D, normalized jointly over limiter rows, then
            # blended with the shared advantage.
            advD = coma_advantages(buf.coma_D, buf.dones,
                                   cfg.coma_gamma, cfg.coma_lam)   # (T, N)
            advD_flat = normalize_advantages(advD.reshape(T * N))
            adv_lim_np = ((1.0 - cfg.coma_mix) * adv_lim_np
                          + cfg.coma_mix * advD_flat)
            coma_stats = {
                "limiter/coma_D_raw_mean": float(buf.coma_D.mean()),
                "limiter/coma_D_raw_pos_frac": float((buf.coma_D > 0).mean()),
            }
        adv_lim = torch.as_tensor(adv_lim_np.astype(np.float32), device=dev)
        targets = torch.as_tensor(targets_np.astype(np.float32), device=dev)

        def _pg(ratio, a):
            s1 = ratio * a
            s2 = torch.clamp(ratio, 1 - cfg.clip_eps, 1 + cfg.clip_eps) * a
            return -torch.min(s1, s2).mean()

        logs = {k: [] for k in ("pg_l", "pg_f", "vf", "ent_l", "ent_f", "kl_l",
                                "kl_f", "clip_l", "clip_f", "gnorm")}
        idx = np.arange(T)
        epochs_ran = 0
        for _ in range(cfg.epochs):
            self._rng.shuffle(idx)
            ep_kl_l, ep_kl_f = [], []
            for start in range(0, T, cfg.minibatch_size):
                mb = idx[start:start + cfg.minibatch_size]
                rows = (mb[:, None] * N + np.arange(N)).ravel()
                mb_t = torch.as_tensor(mb, device=dev)
                rows_t = torch.as_tensor(rows, device=dev)

                lp_l, ent_l = self.lim_actor.evaluate(lim_in[rows_t], lim_raw[rows_t])
                ratio_l = torch.exp(lp_l - lim_old[rows_t])
                pg_l = _pg(ratio_l, adv_lim[rows_t])

                lp_f, ent_f = self.fin_actor.evaluate(obs[mb_t], fin_raw[mb_t])
                ratio_f = torch.exp(lp_f - fin_old[mb_t])
                pg_f = _pg(ratio_f, adv[mb_t])

                v_pred = self.critic(obs[mb_t])           # normalized space
                vf = ((v_pred - targets[mb_t]) ** 2).mean()

                loss = (pg_l + pg_f + cfg.vf_coef * vf
                        - cfg.ent_coef_limiter * ent_l.mean()
                        - cfg.ent_coef_finisher * ent_f.mean())

                self.optimizer.zero_grad()
                loss.backward()
                gnorm = nn.utils.clip_grad_norm_(self.parameters(), cfg.max_grad_norm)
                self.optimizer.step()

                with torch.no_grad():
                    kl_l = ((ratio_l - 1.0) - (lp_l - lim_old[rows_t])).mean()
                    kl_f = ((ratio_f - 1.0) - (lp_f - fin_old[mb_t])).mean()
                    clip_l = ((ratio_l - 1.0).abs() > cfg.clip_eps).float().mean()
                    clip_f = ((ratio_f - 1.0).abs() > cfg.clip_eps).float().mean()

                for k, v in (("pg_l", pg_l), ("pg_f", pg_f), ("vf", vf),
                             ("ent_l", ent_l.mean()), ("ent_f", ent_f.mean()),
                             ("kl_l", kl_l), ("kl_f", kl_f),
                             ("clip_l", clip_l), ("clip_f", clip_f)):
                    logs[k].append(float(v.item()))
                logs["gnorm"].append(float(gnorm))
                ep_kl_l.append(float(kl_l.item()))
                ep_kl_f.append(float(kl_f.item()))

            epochs_ran += 1
            if cfg.target_kl is not None and max(
                    float(np.mean(ep_kl_l)), float(np.mean(ep_kl_f))) > cfg.target_kl:
                break

        return {
            "limiter/policy_loss": float(np.mean(logs["pg_l"])),
            "finisher/policy_loss": float(np.mean(logs["pg_f"])),
            "critic/value_loss": float(np.mean(logs["vf"])),
            "critic/explained_var": explained_var,
            "limiter/entropy": float(np.mean(logs["ent_l"])),
            "finisher/entropy": float(np.mean(logs["ent_f"])),
            "limiter/approx_kl": float(np.mean(logs["kl_l"])),
            "finisher/approx_kl": float(np.mean(logs["kl_f"])),
            "limiter/clip_fraction": float(np.mean(logs["clip_l"])),
            "finisher/clip_fraction": float(np.mean(logs["clip_f"])),
            "grad_norm": float(np.mean(logs["gnorm"])),
            "clip_fraction_action": buf.clip_fraction_action(),
            "limiter/log_std": float(self.lim_actor.log_std.mean().item()),
            "finisher/log_std": float(self.fin_actor.log_std.mean().item()),
            "epochs_ran": float(epochs_ran),
            **coma_stats,
        }

    # --------------------------------------------------------- checkpoint ---
    def save(self, path) -> None:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "lim_actor": self.lim_actor.state_dict(),
            "fin_actor": self.fin_actor.state_dict(),
            "critic": self.critic.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "config": asdict(self.cfg),
            "obs_dim": self.obs_dim,
            "n_limiters": self.n,
            "value_norm": (self.value_norm.state_dict()
                           if self.value_norm is not None else None),
        }, path)

    @classmethod
    def load(cls, path, map_location: Optional[str] = None) -> "MAPPOTrainer":
        ckpt = torch.load(path, map_location=map_location, weights_only=False)
        cfg = MAPPOConfig(**{**ckpt["config"],
                             **({"device": map_location} if map_location else {})})
        if isinstance(cfg.hidden_sizes, list):
            cfg.hidden_sizes = tuple(cfg.hidden_sizes)
        tr = cls(ckpt["obs_dim"], ckpt["n_limiters"], cfg)
        tr.lim_actor.load_state_dict(ckpt["lim_actor"])
        tr.fin_actor.load_state_dict(ckpt["fin_actor"])
        tr.critic.load_state_dict(ckpt["critic"])
        tr.optimizer.load_state_dict(ckpt["optimizer"])
        if ckpt["value_norm"] is not None:
            tr.value_norm = ValueNorm()
            tr.value_norm.load_state_dict(ckpt["value_norm"])
        return tr
