"""Running value-target normalizer (L2 Phase 2C; MAPPO trick, ratified ON).

torch-free (same CI policy as gae.py / obs_norm.py). This is the MAPPO paper's
"value normalization": the critic is trained against NORMALIZED return targets
and its outputs are DENORMALIZED wherever a real-scale value is needed (GAE
bootstraps, logging). Rationale: the return scale in the shepherd game drifts
with behavior mode (escort ~23-step vs blocking 80-step episodes -- docs/09
SS8 (h) diagnosis item on critic-target swings); normalizing targets keeps the
value-loss surface stationary across that drift.

Contract:
  * update(returns) ONCE per rollout with the fresh return targets.
  * normalize(targets) for the critic loss; denormalize(critic_out) for use.
  * state rides inside the trainer checkpoint (state_dict/load_state_dict).
"""
from __future__ import annotations

from typing import Dict

import numpy as np

__all__ = ["ValueNorm"]


class ValueNorm:
    """Chan/Welford running mean-variance over a SCALAR return stream."""

    def __init__(self, eps: float = 1e-4) -> None:
        self.mean = 0.0
        self.var = 1.0
        self.count = float(eps)

    def update(self, x) -> None:
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        if x.size == 0:
            raise ValueError("ValueNorm.update called with an empty array")
        if not np.all(np.isfinite(x)):
            raise FloatingPointError("non-finite return fed to ValueNorm")
        b = x.size
        batch_mean = float(x.mean())
        batch_var = float(x.var())
        delta = batch_mean - self.mean
        tot = self.count + b
        self.mean += delta * (b / tot)
        m2 = self.var * self.count + batch_var * b + delta * delta * (self.count * b / tot)
        self.var = m2 / tot
        self.count = tot

    def _std(self) -> float:
        return float(np.sqrt(self.var + 1e-8))

    def normalize(self, x) -> np.ndarray:
        return ((np.asarray(x, dtype=np.float64) - self.mean) / self._std())

    def denormalize(self, z) -> np.ndarray:
        return np.asarray(z, dtype=np.float64) * self._std() + self.mean

    # -------------------------------------------------------- checkpointing --
    def state_dict(self) -> Dict[str, float]:
        return {"mean": float(self.mean), "var": float(self.var),
                "count": float(self.count)}

    def load_state_dict(self, state: Dict[str, float]) -> None:
        self.mean = float(state["mean"])
        self.var = float(state["var"])
        self.count = float(state["count"])
