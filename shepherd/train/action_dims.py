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

2026-08-03 결함 2 -- 프로파일화 (M4_LIVE_DIMS)
---------------------------------------------
M4(docs/29 SS3.1)는 limiter Box 의 idx 3 을 **커밋 비트**로 재사용한다
(`env_sys.ModeSystemEnv` 가 `a[3] > commit_threshold` 로 읽는다). 그런데 이 파일의
`LIVE_DIMS` 는 M4 이전 주석 그대로 idx 3 을 RESERVED 로 두고 있었고, 그래서
`pad_env_action` 이 그 자리에 **0 을 넣고 있었다** -- 학습 중에도, 평가에서도.
즉 정책에게 하드킬이라는 행동이 아예 존재하지 않았다. 파일럿 3런의 `shape_hk`
가 정확히 0 이었던 것은 탐색 실패가 아니라 이것이다.

`LIVE_DIMS` 는 전역이므로 limiter 를 그냥 바꾸면 M2/M3 정책(3차원 출력)과 그
테스트가 전부 깨진다. 그래서 **프로파일**로 가둔다: 기본값은 손대지 않고
`M4_LIVE_DIMS` 를 따로 두고, 패딩 함수들이 `dims=` 로 프로파일을 받는다.
`dims` 를 안 주면 기존 `LIVE_DIMS` -> M2/M3 경로는 bit-identical.

**선언 변경이 아니라 선언대로의 배선이다** -- docs/29 SS3.1 은 처음부터 idx 3 을
커밋 비트로 선언했고 이 파일이 그것을 구현한 적이 없을 뿐이다. P48 이 지킨다.
"""
from __future__ import annotations
from typing import Dict, Iterable, Mapping, Optional, Tuple

import numpy as np

__all__ = ["LIVE_DIMS", "M4_LIVE_DIMS", "role_of", "live_action_dim",
           "pad_env_action", "pad_env_actions"]

DimsMap = Mapping[str, Tuple[int, Tuple[int, ...]]]

# role -> (env action dim, LIVE indices). Complement = RESERVED (env ignores; pad 0).
LIVE_DIMS: Dict[str, Tuple[int, Tuple[int, ...]]] = {
    "limiter":   (4, (0, 1, 2)),        # accel xyz     | reserved: pressure (idx 3)
    "finisher":  (5, (0, 1, 2, 4)),     # axis xyz+fire | reserved: slew     (idx 3)
    "adversary": (3, (0, 1, 2)),        # accel xyz     | (scripted in-env; kept for API)
}

# M4 프로파일: limiter idx 3 = 커밋 비트 (docs/29 SS3.1). 나머지 역할은 기본과 동일.
# 역할 키 집합은 LIVE_DIMS 와 반드시 같다 (role_of 는 기본 맵으로 역할을 검증한다).
M4_LIVE_DIMS: Dict[str, Tuple[int, Tuple[int, ...]]] = {
    **LIVE_DIMS,
    "limiter": (4, (0, 1, 2, 3)),       # accel xyz + commit | reserved: 없음
}


def _dims(dims: Optional[DimsMap]) -> DimsMap:
    """None -> 기본 프로파일. 호출부가 프로파일을 안 주면 기존 동작 그대로."""
    return LIVE_DIMS if dims is None else dims


def role_of(agent_id: str) -> str:
    """'limiter_2' -> 'limiter'. LIVE_DIMS 의 키가 곧 유효한 역할 집합이다."""
    role = agent_id.rsplit("_", 1)[0]
    if role not in LIVE_DIMS:
        raise KeyError(f"unknown agent id '{agent_id}' (role '{role}')")
    return role


def live_action_dim(agent_id: str, dims: Optional[DimsMap] = None) -> int:
    """Policy output dim for this agent (reserved dims excluded).

    dims=None -> 기본 프로파일. M4 는 `dims=M4_LIVE_DIMS` (limiter 4).
    """
    return len(_dims(dims)[role_of(agent_id)][1])


def pad_env_action(agent_id: str, live_action,
                   dims: Optional[DimsMap] = None) -> np.ndarray:
    """Map a policy's LIVE-dim action to the env's full Box, zeros at RESERVED idx.

    finisher example: live (ax, ay, az, fire) -> env (ax, ay, az, 0.0, fire).
    M4 limiter example (dims=M4_LIVE_DIMS): live (ax, ay, az, commit) -> env 그대로.
    """
    env_dim, live_idx = _dims(dims)[role_of(agent_id)]
    la = np.asarray(live_action, np.float32).reshape(-1)
    if la.shape[0] != len(live_idx):
        raise ValueError(f"{agent_id}: expected live dim {len(live_idx)}, got {la.shape[0]}")
    out = np.zeros(env_dim, np.float32)
    out[list(live_idx)] = la
    return out


def pad_env_actions(live_actions: Dict[str, np.ndarray],
                    expected_agents: Optional[Iterable[str]] = None,
                    dims: Optional[DimsMap] = None
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
    return {aid: pad_env_action(aid, a, dims) for aid, a in live_actions.items()}
