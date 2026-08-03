"""A-3d robust potential Phi + PBRS shaping pieces + Wilson bounds
(docs/17 SS2-SS4, V-3/V-5 ratified; docs/09 (ll) adoption 4, (oo)).

Phi(s) = mean_z m_z(s) - beta * std_z m_z(s),
m_z(s) = sigmoid((v_soft^(z)(s) - theta) / tau) * 1[not boxed^(z)(s)],
evaluated over a FIXED train seed bank Z (CRN-noise control: the same bank
for s_t and s_{t+1}; audit bank kept disjoint). Shaping is the PBRS
difference r_Phi = gamma * Phi(s') - Phi(s) with terminal Phi := 0 --
policy-invariant for the team objective; pays TRANSITIONS, not spawn luck.

Pure numpy; obs-vector parsing follows the frozen layout (env.py
_obs_vector): [lim s9 x N_MAX | fin s9 | att s9 | fsm 6 | v_soft worst
p_feasible]. n_phi < n_judgment is an explicit SCAFFOLD-fidelity choice
(docs/09 (oo)); judgment never reads Phi.
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple

import numpy as np

from shepherd.game import viability as V
from shepherd.stats import wilson
from shepherd.train.spawn_bank import APEX, N_F

# frozen constants (configs/m2_l2_train.yaml)
TAU_DEPLOY, A_ATT, KILL_R, THETA = 0.4, 30.0, 2.0, 0.9
CONE = dict(judge="se3_cone", net_apex=list(APEX), n_F=list(N_F),
            theta_net=0.067, range_min=0.0, range_max=29.847)
N_MAX = 4
PHI_SEEDS_TRAIN = (61, 62, 63, 64, 65)     # Z_train (V-3); audit: 71..75
PHI_SEEDS_AUDIT = (71, 72, 73, 74, 75)

__all__ = ["parse_obs_kin", "phi_value", "teacher_fire", "wilson_lcb",
           "wilson_ucb", "PHI_SEEDS_TRAIN", "PHI_SEEDS_AUDIT", "THETA"]


def teacher_fire(obs_raw, theta: float = THETA) -> bool:
    """A-3d U-2 teacher gate: RAW-obs readout clean -> fire (docs/17 SS3).
    obs[-3] = v_soft, obs[-1] = p_feasible of the CURRENT sampled state."""
    o = np.asarray(obs_raw, float)
    return bool(o[-3] >= theta and o[-1] > 0.0)


def parse_obs_kin(obs: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RAW obs vector -> (att_p(3), att_v(3), limiter_pos(N,3))."""
    o = np.asarray(obs, float)
    lim = np.stack([o[9 * i: 9 * i + 3] for i in range(N_MAX)])
    base = 9 * N_MAX + 9                       # skip finisher s9
    return o[base: base + 3], o[base + 3: base + 6], lim


def phi_value(obs: np.ndarray, *, seeds: Sequence[int] = PHI_SEEDS_TRAIN,
              n: int = 600, theta: float = THETA, tau: float = 0.05,
              beta: float = 1.0) -> float:
    """Robust potential at the state encoded by RAW obs (docs/17 SS3)."""
    att_p, att_v, lim = parse_obs_kin(obs)
    ms = []
    for z in seeds:
        u = V.build_reachable_union(att_p, att_v, tau=TAU_DEPLOY,
                                    a_att_max=A_ATT, n=int(n), n_segments=4,
                                    seed=int(z), **CONE)
        r = V.eval_union_with_limiters(u, lim, KILL_R)
        gate = 0.0 if r.boxed_in else 1.0
        ms.append(gate / (1.0 + math.exp(-(r.v_shot_soft - theta) / tau)))
    ms = np.asarray(ms, float)
    return float(ms.mean() - beta * ms.std())


def wilson_lcb(k: int, n: int, z: float = 1.645) -> float:
    """One-sided 95% lower confidence bound (advance gate, docs/17 SS2)."""
    return wilson(int(k), int(n), float(z))[0]


def wilson_ucb(k: int, n: int, z: float = 1.645) -> float:
    """One-sided 95% upper confidence bound (backoff gate)."""
    return wilson(int(k), int(n), float(z))[1]
