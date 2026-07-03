"""Running observation normalizer (L2 Phase 2B; docs/09 SS7.1 carry-over).

torch-free on purpose: the numerically load-bearing statistics live here so the
default CI suite covers them (same policy as shepherd/train/gae.py). The
shepherd obs is 63-dim with wildly mixed scales (positions ~O(10), velocities
~O(10), attitude unit vectors, FSM one-hots, v-triple in [0,1]) -- without
normalization the Phase-1 core's value/policy nets train poorly.

Usage contract (the IPPO runner owns it):
  * update() ONCE per env step with the shared full-state obs (every agent sees
    the identical vector -- updating per-agent would just replay the same
    sample N+1 times and bias nothing but the count).
  * normalize() everywhere a policy/critic consumes an obs; the one-hot agent
    id is appended AFTER normalization and is never normalized.
  * eval / deterministic rollouts call normalize() only (stats frozen).
  * state_dict()/load_state_dict() ride inside the run checkpoint so a resumed
    or reloaded policy sees the same input distribution.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

__all__ = ["RunningNorm"]


class RunningNorm:
    """Chan/Welford parallel running mean-variance with clipping.

    ``update`` accepts a single obs ``(dim,)`` or a batch ``(B, dim)``.
    ``normalize`` returns ``clip((x - mean) / sqrt(var + 1e-8), -clip, clip)``
    as float32. The initial pseudo-count ``eps`` keeps the very first
    normalizations dominated by observed data instead of the zero/one prior.
    """

    def __init__(self, dim: int, eps: float = 1e-4, clip: float = 10.0) -> None:
        if dim <= 0:
            raise ValueError(f"dim must be positive, got {dim}")
        self.dim = int(dim)
        self.clip = float(clip)
        self.mean = np.zeros(self.dim, dtype=np.float64)
        self.var = np.ones(self.dim, dtype=np.float64)
        self.count = float(eps)

    # ------------------------------------------------------------- update ---
    def _as_batch(self, x) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        if x.ndim == 1:
            x = x[None, :]
        if x.ndim != 2 or x.shape[1] != self.dim:
            raise ValueError(f"expected (*, {self.dim}) obs, got shape {x.shape}")
        if not np.all(np.isfinite(x)):
            raise FloatingPointError("non-finite observation fed to RunningNorm")
        return x

    def update(self, x) -> None:
        x = self._as_batch(x)
        b = x.shape[0]
        batch_mean = x.mean(axis=0)
        batch_var = x.var(axis=0)

        delta = batch_mean - self.mean
        tot = self.count + b
        new_mean = self.mean + delta * (b / tot)
        m_a = self.var * self.count
        m_b = batch_var * b
        m2 = m_a + m_b + np.square(delta) * (self.count * b / tot)

        self.mean = new_mean
        self.var = m2 / tot
        self.count = tot

    # ---------------------------------------------------------- normalize ---
    def normalize(self, x, update: bool = False) -> np.ndarray:
        if update:
            self.update(x)
        x = np.asarray(x, dtype=np.float64)
        z = (x - self.mean) / np.sqrt(self.var + 1e-8)
        return np.clip(z, -self.clip, self.clip).astype(np.float32)

    # -------------------------------------------------------- checkpointing ---
    def state_dict(self) -> Dict[str, object]:
        return {
            "dim": self.dim,
            "clip": self.clip,
            "count": float(self.count),
            "mean": self.mean.tolist(),
            "var": self.var.tolist(),
        }

    def load_state_dict(self, state: Dict[str, object]) -> None:
        if int(state["dim"]) != self.dim:
            raise ValueError(
                f"RunningNorm dim mismatch: checkpoint {state['dim']} != {self.dim}"
            )
        self.clip = float(state["clip"])
        self.count = float(state["count"])
        self.mean = np.asarray(state["mean"], dtype=np.float64).copy()
        self.var = np.asarray(state["var"], dtype=np.float64).copy()
        if self.mean.shape != (self.dim,) or self.var.shape != (self.dim,):
            raise ValueError("RunningNorm checkpoint arrays have wrong shape")
