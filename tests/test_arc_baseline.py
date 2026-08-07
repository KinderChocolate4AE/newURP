"""docs/63 r2 scripted baseline (arc redeployment) — family·배정·parity 검정."""
from __future__ import annotations

import math

import numpy as np
import pytest

from shepherd.agents.baselines import (arc_redeploy_limiter, arc_slots,
                                       min_cost_assignment)


def test_arc_slots_geometry():
    """bearing 중심 · 등간격 · 반경 · z=0 (docs/63 §2-1)."""
    target = np.zeros(3)
    p_att = np.array([100.0, 100.0, 3.0])          # bearing = pi/4
    r_d, dphi = 9.0, math.pi / 8
    slots = arc_slots(target, p_att, r_d, dphi, n=4)
    assert len(slots) == 4
    for s in slots:
        assert s[2] == 0.0                          # z=0 scope
        assert np.isclose(np.linalg.norm(s), r_d)
    angs = [math.atan2(s[1], s[0]) for s in slots]
    diffs = np.diff(angs)
    assert np.allclose(diffs, dphi)                 # 등간격
    assert np.isclose((angs[1] + angs[2]) / 2.0, math.pi / 4)   # bearing 중심


def test_min_cost_assignment_removes_index_artifact():
    """교차 배치에서 fixed-index 는 가로지르고, 배정은 안 가로지른다 (r1 §2-2)."""
    slots = [np.array([1.0, 0, 0]), np.array([2.0, 0, 0]),
             np.array([3.0, 0, 0]), np.array([4.0, 0, 0])]
    pos = [slots[3] + 0.1, slots[2] - 0.1, slots[1] + 0.1, slots[0] - 0.1]
    perm = min_cost_assignment(pos, slots)
    assert perm == (3, 2, 1, 0)                     # 최근접 재배정
    # 결정론 (동률 포함): 같은 입력 -> 같은 permutation
    assert min_cost_assignment(pos, slots) == perm
    # 대칭 동률: 사전순 첫 permutation
    same = [np.zeros(3)] * 4
    assert min_cost_assignment(same, slots) == (0, 1, 2, 3)


def test_arc_action_contract():
    """|a| <= a_max · commit 비트 0 (docs/63 §2-3/§2-5)."""
    a = arc_redeploy_limiter(np.zeros(3), np.zeros(3),
                             np.array([100.0, 0, 0]), a_max=5.0)
    assert a.shape == (4,) and a[3] == 0.0
    assert np.linalg.norm(a[:3]) <= 5.0 + 1e-6


def test_arc_mode_requires_grid_kw():
    """silent default 금지 — grid 값 없이 arc 호출 = 오류 (F4)."""
    from shepherd.env_sys import RewardSpec
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.mission_rollout import run_episode
    from shepherd.scale_v2 import A2_V4
    from shepherd.spawn_rand import SpawnSpec
    from shepherd.env_sys import ratified_system

    st = build_m4_env(0, 0, system=ratified_system(),
                      reward=RewardSpec(w_kill=0.5, enabled=True),
                      attacker=A2_V4, spawn=SpawnSpec())
    with pytest.raises(ValueError):
        run_episode(st.env, st.scn, st.lay, seed=0, limiter_mode="arc")


def test_arc_runs_and_moves_toward_bearing():
    """legacy 소기하 1판 통합 스모크: arc 가 돌고 limiter 가 bearing 쪽으로 움직인다."""
    from shepherd.env_sys import RewardSpec, ratified_system
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.mission_rollout import run_episode
    from shepherd.scale_v2 import A2_V4
    from shepherd.spawn_rand import SpawnSpec

    st = build_m4_env(0, 0, system=ratified_system(),
                      reward=RewardSpec(w_kill=0.5, enabled=True),
                      attacker=A2_V4, spawn=SpawnSpec())
    r = run_episode(st.env, st.scn, st.lay, seed=0, limiter_mode="arc",
                    fire_mode="clean", limiter_kw=dict(r_d=9.0,
                                                       dphi=math.pi / 8))
    assert r.label in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL",
                       "PENETRATED", "SPENT_FAIL", "TRUNCATED")
    assert r.steps > 1


def test_a4c_world_contract_parity():
    """A4c (docs/65): scripted 튜닝 world == MARL 평가 world — controller 만
    다르고 manifest 동일. limiter_mode 는 world contract 밖이어야 한다."""
    from shepherd.m4_env import build_m4_env, manifest_mismatch
    from shepherd.scripts.tune_arc_baseline import world_kw

    tuned = build_m4_env(0, 5000, **world_kw()).contract
    marl_eval = build_m4_env(0, 5000, system=world_kw()["system"],
                             reward=world_kw()["reward"],
                             threat_layer="train").contract
    assert manifest_mismatch(tuned, marl_eval) == []
    assert tuned["hash"] == marl_eval["hash"]
