"""IPPO building blocks (L2 Phase 2B, docs/09 SS5 Phase 2B).

Two INDEPENDENT PPO learners on the frozen shepherd env -- decentralized
critics, no central critic, env.state() unconsumed (that is 2C/MAPPO):

  * limiter -- ONE parameter-shared Gaussian policy for the N homogeneous
    limiters, reusing the Phase-1 core (``PPOTrainer``/``ActorCritic``)
    verbatim. The frozen env hands EVERY agent the identical full-state obs
    (docs/09 SS2 CTDE note), so a shared policy without an identity feature is
    permutation-degenerate: all limiters would emit the same action
    distribution and could never take the asymmetric escape-lobe roles that
    shaping needs. Standard parameter-sharing fix: the trainer appends a
    one-hot agent id to the (normalized) obs -- ``limiter_inputs``. The frozen
    env is untouched.

  * finisher -- separate policy with the MIXED action head. 2B decision
    (docs/09 SS5 "here it closes" / SS7): **Bernoulli head** for the binary
    irreversible fire dim + Gaussian for the 3 net-axis dims, over
    Gaussian+threshold. The stored fire action is the exact {0,1} sample, so
    the PPO importance ratio is exact on the fire dim (a thresholded Gaussian
    stores a density the executed action does not have -- the same
    clipped-density wart Phase 1 accepted for the box, made worse by a hard
    binary). Joint log-prob = Gaussian.sum + Bernoulli; entropies add.

Action-space convention (2B, recorded in docs/09 SS8): policies act in
NORMALIZED [-1, 1] space; the runner scales by the env Box bounds. Phase 1
acted in raw env units, but on the +-30 limiter accel box a std~1 Gaussian
would explore ~3% of the range and the LOG_STD clamp (e^2 ~ 7.4) cannot reach
box scale -- normalized space keeps ``init_log_std = 0`` sane for every role.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Bernoulli, Normal

from shepherd.train.ppo import PPOTrainer, _mlp

__all__ = ["MixedActorCritic", "MixedPPOTrainer", "limiter_inputs"]


def limiter_inputs(norm_obs: np.ndarray, n_limiters: int) -> np.ndarray:
    """(n_limiters, obs_dim + n_limiters) policy inputs: shared normalized obs
    + one-hot agent id (appended AFTER normalization; never normalized)."""
    norm_obs = np.asarray(norm_obs, dtype=np.float32).reshape(-1)
    base = np.tile(norm_obs, (n_limiters, 1))
    eye = np.eye(n_limiters, dtype=np.float32)
    return np.concatenate([base, eye], axis=1)


class MixedActorCritic(nn.Module):
    """Gaussian (continuous dims) + Bernoulli (final fire dim) actor-critic.

    Mirrors the Phase-1 ``ActorCritic`` API exactly -- ``act`` returns
    ``(raw_action, log_prob, value)`` and ``evaluate`` returns
    ``(log_prob, entropy, value)`` -- so ``PPOTrainer.update`` runs unmodified.
    ``raw_action = [gaussian_sample(cont_dim), fire in {0, 1}]``; the runner
    clips/scales ONLY the continuous part (fire passes through untouched, so
    the ``clip_fraction_action`` diagnostic is unaffected by the fire dim).
    Separate actor / fire / critic MLPs (Phase-1 separate-network choice);
    state-independent Gaussian log-std with the same forward clamp.
    """

    LOG_STD_MIN: float = -5.0
    LOG_STD_MAX: float = 2.0

    def __init__(
        self,
        obs_dim: int,
        cont_dim: int,
        hidden_sizes: tuple[int, ...] = (64, 64),
        init_log_std: float = 0.0,
    ) -> None:
        super().__init__()
        if cont_dim < 1:
            raise ValueError(f"cont_dim must be >= 1, got {cont_dim}")
        self.cont_dim = int(cont_dim)
        self.actor_mean = _mlp(obs_dim, hidden_sizes, cont_dim)
        self.fire_logit = _mlp(obs_dim, hidden_sizes, 1)
        self.critic = _mlp(obs_dim, hidden_sizes, 1)
        self.log_std = nn.Parameter(torch.full((cont_dim,), float(init_log_std)))

    def _dists(self, obs: torch.Tensor):
        mean = self.actor_mean(obs)
        log_std = self.log_std.clamp(self.LOG_STD_MIN, self.LOG_STD_MAX)
        std = log_std.exp().expand_as(mean)
        return Normal(mean, std), Bernoulli(logits=self.fire_logit(obs))

    def value(self, obs: torch.Tensor) -> torch.Tensor:
        return self.critic(obs).squeeze(-1)

    @torch.no_grad()
    def act(self, obs: torch.Tensor, deterministic: bool = False):
        """Sample ``[gaussian(cont), fire]``; fire is an exact {0, 1} float.

        Deterministic mode: Gaussian mean + fire = 1[p > 0.5] (used for eval).
        """
        dist_g, dist_b = self._dists(obs)
        g = dist_g.mean if deterministic else dist_g.sample()
        fire = (dist_b.probs > 0.5).float() if deterministic else dist_b.sample()
        raw_action = torch.cat([g, fire], dim=-1)
        log_prob = dist_g.log_prob(g).sum(-1) + dist_b.log_prob(fire).sum(-1)
        return raw_action, log_prob, self.value(obs)

    def evaluate(self, obs: torch.Tensor, raw_action: torch.Tensor):
        """Joint log-prob / entropy / value for stored ``(obs, raw_action)``."""
        dist_g, dist_b = self._dists(obs)
        g = raw_action[..., : self.cont_dim]
        fire = raw_action[..., self.cont_dim :]
        log_prob = dist_g.log_prob(g).sum(-1) + dist_b.log_prob(fire).sum(-1)
        entropy = dist_g.entropy().sum(-1) + dist_b.entropy().sum(-1)
        return log_prob, entropy, self.value(obs)


class MixedPPOTrainer(PPOTrainer):
    """Phase-1 ``PPOTrainer`` with the mixed-head network swapped in.

    Keeps the ``(obs_dim, act_dim, cfg)`` constructor signature -- ``act_dim``
    INCLUDES the fire dim (finisher: 4 = 3 axis + 1 fire; cont = act_dim - 1)
    -- so the inherited ``save``/``load`` checkpoint format round-trips through
    ``cls(ckpt["obs_dim"], ckpt["act_dim"], cfg)`` unchanged. ``update`` is
    inherited verbatim: the buffer stores the raw [gaussian, fire] vector and
    ``MixedActorCritic.evaluate`` recomputes the joint ratio.
    """

    def __init__(self, obs_dim: int, act_dim: int, cfg) -> None:
        # Mirror PPOTrainer.__init__ except for the network class; calling
        # super().__init__ would build-and-discard a Gaussian ActorCritic and
        # leave the optimizer pointing at the wrong parameters.
        self.cfg = cfg
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.device = torch.device(cfg.device)
        self.ac = MixedActorCritic(
            obs_dim, act_dim - 1, cfg.hidden_sizes, cfg.init_log_std
        ).to(self.device)
        self.optimizer = torch.optim.Adam(self.ac.parameters(), lr=cfg.lr)
        # Private minibatch-shuffle RNG -- same contract as the base class
        # (trainer state, not re-seeded per update).
        self._rng = np.random.default_rng(cfg.seed)
