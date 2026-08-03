"""Reserved-dim action padding utilities (torch-free, env-import-free).

Split out of shepherd/train/make_env.py (2026-07-03 GPT-review fix) so the
padding logic can be unit-tested without pulling in the full env composition
stack (roles / env / analytic backend). make_env re-exports these names, so
existing imports keep working.

RESERVED ACTION DIMS (decision 2026-07-03, Hyunjun -- docs/09 SS2):
The frozen env (shepherd/env.py) ACCEPTS limiter Box(4)=accel3+pressure and
finisher Box(5)=axis3+slew+fire but IGNORES pressure (idx 3) and slew (idx 3).
Policies must output only the LIVE dims (limiter 3 = accel, finisher 4 =
axis3+fire, adversary 3 = accel); pad_env_action() re-inserts zeros at the
reserved indices before env.step().
"""
from __future__ import annotations
from typing import Dict, Iterable, Optional, Tuple

import numpy as np

__all__ = ["LIVE_DIMS", "role_of", "live_action_dim", "pad_env_action", "pad_env_actions"]

# role -> (env action dim, LIVE indices). Complement = RESERVED (env ignores; pad 0).
LIVE_DIMS: Dict[str, Tuple[int, Tuple[int, ...]]] = {
    "limiter":   (4, (0, 1, 2)),        # accel xyz     | reserved: pressure (idx 3)
    "finisher":  (5, (0, 1, 2, 4)),     # axis xyz+fire | reserved: slew     (idx 3)
    "adversary": (3, (0, 1, 2)),        # accel xyz     | (scripted in-env; kept for API)
}


def role_of(agent_id: str) -> str:
    """'limiter_2' -> 'limiter'. LIVE_DIMS 의 키가 곧 유효한 역할 집합이다."""
    role = agent_id.rsplit("_", 1)[0]
    if role not in LIVE_DIMS:
        raise KeyError(f"unknown agent id '{agent_id}' (role '{role}')")
    return role


def live_action_dim(agent_id: str) -> int:
    """Policy output dim for this agent (reserved dims excluded)."""
    return len(LIVE_DIMS[role_of(agent_id)][1])


def pad_env_action(agent_id: str, live_action) -> np.ndarray:
    """Map a policy's LIVE-dim action to the env's full Box, zeros at RESERVED idx.

    finisher example: live (ax, ay, az, fire) -> env (ax, ay, az, 0.0, fire).
    """
    env_dim, live_idx = LIVE_DIMS[role_of(agent_id)]
    la = np.asarray(live_action, np.float32).reshape(-1)
    if la.shape[0] != len(live_idx):
        raise ValueError(f"{agent_id}: expected live dim {len(live_idx)}, got {la.shape[0]}")
    out = np.zeros(env_dim, np.float32)
    out[list(live_idx)] = la
    return out


def pad_env_actions(live_actions: Dict[str, np.ndarray],
                    expected_agents: Optional[Iterable[str]] = None
                    ) -> Dict[str, np.ndarray]:
    """Dict convenience wrapper over pad_env_action.

    If ``expected_agents`` is given (e.g. ``env.agents``), a missing action for
    any live agent raises KeyError instead of silently stepping a partial dict
    (multi-agent runner guard, 2026-07-03 GPT-review fix).
    """
    if expected_agents is not None:
        missing = set(expected_agents) - set(live_actions)
        if missing:
            raise KeyError(f"missing actions for agents: {sorted(missing)}")
    return {aid: pad_env_action(aid, a) for aid, a in live_actions.items()}
