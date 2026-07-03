"""From-scratch single-agent PPO core (L2 Phase 1).

This is the algorithmic foundation for the Phase-2 MAPPO/COMA trainer -- it is
implemented directly in torch (no SB3 / RLlib / tianshou), which is the point:
``docs/05_learning_goals.md`` makes a hand-rolled PPO the deliverable's value
signal. Only ``numpy`` / ``torch`` are used here; the numerically load-bearing
GAE lives in the torch-free :mod:`shepherd.train.gae` so it can be CI-tested
without torch.

Design choices (locked in the Phase-1 plan):
  * State-independent Gaussian log-std (a learnable parameter vector), not a
    network head. ``init_log_std`` is config-driven (default 0.0) because the
    shepherd action space is narrower than Pendulum's.
  * No value-function clipping -- plain MSE value loss.
  * Actions are clipped to the Box before stepping, but log-probs / ratios are
    computed on the *raw* Gaussian sample (storing the clipped action would
    corrupt the ratio). The importance ratio is therefore exact w.r.t. the
    Gaussian; the executed clipped-action density is not corrected (accepted in
    Phase 1, surfaced via the ``clip_fraction_action`` diagnostic).
  * Advantage normalization happens once at rollout level (see gae module),
    not per-minibatch.

Seeding ownership (2026-07-03 review): GLOBAL seeding (torch.manual_seed /
np.random.seed / deterministic algorithms) is the RUNNER's job, done once
before the trainer is constructed (see ``train_ppo_toy.seed_everything``).
The trainer only owns its private minibatch-shuffle RNG (``self._rng``,
seeded from cfg.seed at construction so successive update() calls see
different permutations while staying reproducible). A future MAPPO runner
must replicate the runner-side seeding.

The trainer is env-agnostic: it consumes a rollout that the runner collects
(``shepherd/scripts/train_ppo_toy.py``) and returns diagnostics. Nothing here
imports the shepherd env -- Phase 1 validates on a Gymnasium toy env only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Normal

from shepherd.train.gae import compute_gae, normalize_advantages

__all__ = ["PPOConfig", "ActorCritic", "RolloutBuffer", "PPOTrainer"]


# ---------------------------------------------------------------- config ---
@dataclass
class PPOConfig:
    """PPO hyperparameters. Loaded from YAML (``PPOConfig(**cfg["ppo"])``) so the
    Phase-2 MAPPO config can reuse the same pattern."""

    # optimization
    total_timesteps: int = 300_000
    rollout_steps: int = 2048
    epochs: int = 10
    minibatch_size: int = 64
    lr: float = 3e-4
    max_grad_norm: float = 0.5

    # PPO objective
    clip_eps: float = 0.2
    gamma: float = 0.9
    lam: float = 0.95
    ent_coef: float = 0.0
    vf_coef: float = 0.5

    # policy / network
    hidden_sizes: tuple[int, ...] = (64, 64)
    init_log_std: float = 0.0

    # misc
    seed: int = 0
    device: str = "cpu"

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "PPOConfig":
        d = dict(d or {})
        if "hidden_sizes" in d and d["hidden_sizes"] is not None:
            d["hidden_sizes"] = tuple(d["hidden_sizes"])
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown PPOConfig keys: {sorted(unknown)}")
        return cls(**d)


# ------------------------------------------------------------- networks ---
def _mlp(in_dim: int, hidden: tuple[int, ...], out_dim: int) -> nn.Sequential:
    layers: list[nn.Module] = []
    last = in_dim
    for h in hidden:
        layers += [nn.Linear(last, h), nn.Tanh()]
        last = h
    layers += [nn.Linear(last, out_dim)]
    return nn.Sequential(*layers)


class ActorCritic(nn.Module):
    """Separate actor and critic MLPs with a state-independent Gaussian log-std.

    The actor outputs the Gaussian mean; ``log_std`` is a free parameter vector
    (one per action dim). The critic outputs a scalar value.
    """

    def __init__(
        self,
        obs_dim: int,
        act_dim: int,
        hidden_sizes: tuple[int, ...] = (64, 64),
        init_log_std: float = 0.0,
    ) -> None:
        super().__init__()
        self.actor_mean = _mlp(obs_dim, hidden_sizes, act_dim)
        self.critic = _mlp(obs_dim, hidden_sizes, 1)
        self.log_std = nn.Parameter(torch.full((act_dim,), float(init_log_std)))

    # log_std bounds: std in [e^-5 ~ 0.007, e^2 ~ 7.4]. Clamped in the forward
    # pass so a drifting parameter can neither kill exploration (std -> 0) nor
    # blow the action scale up; the raw parameter may sit outside, but every
    # density/sample uses the clamped value.
    LOG_STD_MIN: float = -5.0
    LOG_STD_MAX: float = 2.0

    def _dist(self, obs: torch.Tensor) -> Normal:
        mean = self.actor_mean(obs)
        log_std = self.log_std.clamp(self.LOG_STD_MIN, self.LOG_STD_MAX)
        std = log_std.exp().expand_as(mean)
        return Normal(mean, std)

    def value(self, obs: torch.Tensor) -> torch.Tensor:
        return self.critic(obs).squeeze(-1)

    @torch.no_grad()
    def act(self, obs: torch.Tensor, deterministic: bool = False):
        """Sample a raw action for env interaction.

        Returns ``(raw_action, log_prob, value)``. The caller clips the raw
        action to the Box before stepping but stores the *raw* action for the
        PPO ratio.
        """
        dist = self._dist(obs)
        raw_action = dist.mean if deterministic else dist.sample()
        log_prob = dist.log_prob(raw_action).sum(-1)
        value = self.value(obs)
        return raw_action, log_prob, value

    def evaluate(self, obs: torch.Tensor, raw_action: torch.Tensor):
        """Recompute log-prob, entropy, value for stored (obs, raw_action)."""
        dist = self._dist(obs)
        log_prob = dist.log_prob(raw_action).sum(-1)
        entropy = dist.entropy().sum(-1)
        value = self.value(obs)
        return log_prob, entropy, value


# --------------------------------------------------------------- buffer ---
class RolloutBuffer:
    """Fixed-size on-policy buffer.

    Stores BOTH the raw Gaussian sample (``raw_actions``, used to recompute the
    PPO ratio) and the Box-clipped action actually stepped (``env_actions``,
    used only for the ``clip_fraction_action`` diagnostic).
    """

    def __init__(self, size: int, obs_dim: int, act_dim: int) -> None:
        self.size = size
        self.obs = np.zeros((size, obs_dim), dtype=np.float32)
        self.raw_actions = np.zeros((size, act_dim), dtype=np.float32)
        self.env_actions = np.zeros((size, act_dim), dtype=np.float32)
        self.log_probs = np.zeros(size, dtype=np.float32)
        self.values = np.zeros(size, dtype=np.float32)
        self.rewards = np.zeros(size, dtype=np.float32)
        self.next_values = np.zeros(size, dtype=np.float32)
        self.dones = np.zeros(size, dtype=np.float32)
        self._i = 0

    def add(self, obs, raw_action, env_action, log_prob, value, reward,
            next_value, done) -> None:
        i = self._i
        if i >= self.size:
            raise IndexError("RolloutBuffer is full")
        self.obs[i] = obs
        self.raw_actions[i] = raw_action
        self.env_actions[i] = env_action
        self.log_probs[i] = log_prob
        self.values[i] = value
        self.rewards[i] = reward
        self.next_values[i] = next_value
        self.dones[i] = done
        self._i += 1

    @property
    def full(self) -> bool:
        return self._i >= self.size

    def reset(self) -> None:
        self._i = 0

    def clip_fraction_action(self, atol: float = 1e-6) -> float:
        """Fraction of action components altered by Box clipping -- an early
        signal that the policy is training outside the action bounds. Uses a
        tolerance (not exact float equality) so dtype round-trips through the
        env cannot register as phantom clipping."""
        return float(np.mean(np.abs(self.raw_actions - self.env_actions) > atol))


# -------------------------------------------------------------- trainer ---
class PPOTrainer:
    """Owns the network, optimizer, and the PPO update. Env interaction /
    rollout collection lives in the runner script."""

    def __init__(self, obs_dim: int, act_dim: int, cfg: PPOConfig) -> None:
        self.cfg = cfg
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.device = torch.device(cfg.device)
        self.ac = ActorCritic(
            obs_dim, act_dim, cfg.hidden_sizes, cfg.init_log_std
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.ac.parameters(), lr=cfg.lr)
        # Private minibatch-shuffle RNG (trainer state, NOT re-seeded per update:
        # re-creating it inside update() would replay the identical permutation
        # sequence every rollout -- 2026-07-03 review fix).
        self._rng = np.random.default_rng(cfg.seed)

    # ----------------------------------------------------------- checkpoint ---
    def save(self, path) -> None:
        """Persist weights + optimizer + config + dims so a run is restorable.

        Binary checkpoints are gitignored (``*.pt``); the seed + config make a
        run reproducible without committing weights."""
        import pathlib
        from dataclasses import asdict

        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state": self.ac.state_dict(),
                "optimizer_state": self.optimizer.state_dict(),
                "config": asdict(self.cfg),
                "obs_dim": self.obs_dim,
                "act_dim": self.act_dim,
            },
            path,
        )

    @classmethod
    def load(cls, path, map_location: Optional[str] = None) -> "PPOTrainer":
        ckpt = torch.load(path, map_location=map_location, weights_only=False)
        cfg = PPOConfig(**ckpt["config"])
        if map_location is not None:
            cfg.device = map_location
        trainer = cls(ckpt["obs_dim"], ckpt["act_dim"], cfg)
        trainer.ac.load_state_dict(ckpt["model_state"])
        trainer.optimizer.load_state_dict(ckpt["optimizer_state"])
        return trainer

    def update(self, buf: RolloutBuffer) -> dict:
        """Run ``epochs`` × minibatch PPO updates over one full rollout.

        Advantages are computed once (torch-free GAE) and normalized once at
        rollout level; minibatches consume the pre-normalized values. Returns a
        dict of scalar diagnostics.
        """
        cfg = self.cfg
        if not buf.full:
            # A partially-filled buffer would silently train on the zero-valued
            # tail (fake transitions). Phase 1 policy: full rollouts only.
            raise ValueError(
                f"RolloutBuffer is not full: {buf._i}/{buf.size} -- collect a "
                "complete rollout before update()"
            )
        n = buf.size

        advantages_np, returns_np = compute_gae(
            buf.rewards, buf.values, buf.next_values, buf.dones,
            cfg.gamma, cfg.lam,
        )
        advantages_np = normalize_advantages(advantages_np)  # rollout-level once

        obs = torch.as_tensor(buf.obs, device=self.device)
        raw_actions = torch.as_tensor(buf.raw_actions, device=self.device)
        old_log_probs = torch.as_tensor(buf.log_probs, device=self.device)
        advantages = torch.as_tensor(
            advantages_np.astype(np.float32), device=self.device
        )
        returns = torch.as_tensor(
            returns_np.astype(np.float32), device=self.device
        )

        pg_losses, vf_losses, ent_losses, approx_kls, grad_norms = [], [], [], [], []
        clip_fracs = []

        idx = np.arange(n)
        for _ in range(cfg.epochs):
            self._rng.shuffle(idx)
            for start in range(0, n, cfg.minibatch_size):
                mb = idx[start:start + cfg.minibatch_size]
                mb_t = torch.as_tensor(mb, device=self.device)

                new_log_probs, entropy, values = self.ac.evaluate(
                    obs[mb_t], raw_actions[mb_t]
                )
                ratio = torch.exp(new_log_probs - old_log_probs[mb_t])
                adv = advantages[mb_t]

                # clipped surrogate (maximize -> negate for loss)
                surr1 = ratio * adv
                surr2 = torch.clamp(ratio, 1.0 - cfg.clip_eps, 1.0 + cfg.clip_eps) * adv
                pg_loss = -torch.min(surr1, surr2).mean()

                value_loss = ((values - returns[mb_t]) ** 2).mean()  # plain MSE
                entropy_loss = entropy.mean()

                loss = pg_loss + cfg.vf_coef * value_loss - cfg.ent_coef * entropy_loss

                self.optimizer.zero_grad()
                loss.backward()
                grad_norm = nn.utils.clip_grad_norm_(
                    self.ac.parameters(), cfg.max_grad_norm
                )
                self.optimizer.step()

                with torch.no_grad():
                    # approx KL (Schulman): mean((ratio-1) - log ratio) >= 0
                    log_ratio = new_log_probs - old_log_probs[mb_t]
                    approx_kl = ((ratio - 1.0) - log_ratio).mean()
                    clip_frac = ((ratio - 1.0).abs() > cfg.clip_eps).float().mean()

                pg_losses.append(pg_loss.item())
                vf_losses.append(value_loss.item())
                ent_losses.append(entropy_loss.item())
                approx_kls.append(approx_kl.item())
                grad_norms.append(float(grad_norm))
                clip_fracs.append(clip_frac.item())

        return {
            "policy_loss": float(np.mean(pg_losses)),
            "value_loss": float(np.mean(vf_losses)),
            "entropy": float(np.mean(ent_losses)),
            "approx_kl": float(np.mean(approx_kls)),
            "grad_norm": float(np.mean(grad_norms)),
            "clip_fraction": float(np.mean(clip_fracs)),
            "clip_fraction_action": buf.clip_fraction_action(),
            "log_std": float(self.ac.log_std.mean().item()),
        }
