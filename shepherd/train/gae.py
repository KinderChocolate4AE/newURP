"""Torch-free numeric core for PPO advantage estimation (L2 Phase 1).

Kept deliberately free of any ``torch`` import so the numerically load-bearing
logic -- GAE and advantage normalization -- can be unit-tested in the existing
torch-free CI suite (see ``tests/test_ppo_gae.py``).

Design note (truncation-dominant setting).  The shepherd env terminates mostly
by *truncation* at ``episode_len=80``, with occasional true terminations
(captured / penetrated / spent_fail).  Bootstrapping these two cases
differently is the main correctness concern, so ``compute_gae`` takes an
explicit per-step ``next_values`` array rather than a single trailing
``last_value``.  The rollout collector is responsible for filling it:

    if terminated:   next_values[t] = 0.0
    elif truncated:  next_values[t] = V(final_obs)   # NOT V(reset_obs)
    else:            next_values[t] = V(next_obs)

``dones = terminated | truncated`` marks episode boundaries and only controls
whether the GAE recursion propagates advantage backward across a boundary -- it
does *not* re-zero the bootstrap (that is already encoded in ``next_values``).
"""

from __future__ import annotations

import numpy as np

__all__ = ["compute_gae", "normalize_advantages"]


def compute_gae(
    rewards: np.ndarray,
    values: np.ndarray,
    next_values: np.ndarray,
    dones: np.ndarray,
    gamma: float,
    lam: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Generalized Advantage Estimation (Schulman et al., 2016).

    Parameters
    ----------
    rewards : (T,) reward received at each step.
    values : (T,) critic value ``V(obs_t)`` at the step's own observation.
    next_values : (T,) bootstrap value for step ``t`` -- already 0.0 on true
        termination, ``V(final_obs)`` on truncation, ``V(next_obs)`` otherwise.
    dones : (T,) episode-boundary flag (``terminated | truncated``); stops the
        GAE recursion from crossing an episode boundary.
    gamma : discount factor.
    lam : GAE lambda.

    Returns
    -------
    advantages : (T,) float64
    returns : (T,) float64  (``advantages + values``; value-function targets)
    """
    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    next_values = np.asarray(next_values, dtype=np.float64)
    dones = np.asarray(dones, dtype=np.float64)

    if rewards.ndim != 1:
        raise ValueError(f"rewards must be 1-D (T,); got shape {rewards.shape}")
    T = rewards.shape[0]
    if not (values.shape == next_values.shape == dones.shape == (T,)):
        raise ValueError(
            "rewards, values, next_values, dones must all be 1-D length T; "
            f"got {rewards.shape}, {values.shape}, {next_values.shape}, {dones.shape}"
        )
    if not (0.0 <= gamma <= 1.0):
        raise ValueError(f"gamma must be in [0, 1], got {gamma}")
    if not (0.0 <= lam <= 1.0):
        raise ValueError(f"lam must be in [0, 1], got {lam}")
    if not np.all((dones == 0.0) | (dones == 1.0)):
        raise ValueError("dones must contain only 0/1 values")

    advantages = np.zeros(T, dtype=np.float64)
    gae = 0.0
    for t in range(T - 1, -1, -1):
        # next_values[t] already encodes the terminal (0.0) / bootstrap value.
        delta = rewards[t] + gamma * next_values[t] - values[t]
        # (1 - dones[t]) stops advantage from propagating across a boundary.
        gae = delta + gamma * lam * (1.0 - dones[t]) * gae
        advantages[t] = gae

    returns = advantages + values
    return advantages, returns


def normalize_advantages(adv: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Standardize advantages to mean 0 / std 1 over the whole batch.

    Applied once at rollout level (not per-minibatch) so every minibatch sees a
    consistent advantage scale.
    """
    adv = np.asarray(adv, dtype=np.float64)
    return (adv - adv.mean()) / (adv.std() + eps)
