"""Phase III 착수 코드의 계약 잠금 (docs/74 r3.2 · docs/75 게이트 1~3).

여기서 지키는 것은 성능이 아니라 **계약**이다:
  P76a  모든 Phase III artifact 는 provenance 스탬프를 싣는다 (없으면 무효)
  P76b  `Z_master` 는 결과 전에 확정되고 `lattice_hash` 는 격자 정의에만 의존한다
  P76c  core Π 는 2~3 축 · 전체 Π 목록에 포함 · conditioning 순서는 core 와 겹치지 않음
  P76d  measure 게이트 기준은 코드 상수로 고정 (2k/8k/32k · 0.02/0.05)
  P76e  informative 규칙은 **자명한 0/1 상태를 배제**한다 (게이트가 공짜로 통과하면 안 된다)

torch 불요.
"""
from __future__ import annotations

import numpy as np

from shepherd.scripts import lattice_spec as L
from shepherd.scripts import measure_harness as M
from shepherd.scripts.pivot_manifest import stamp


def test_p76a_stamp_carries_every_required_field():
    s = stamp(artifact="unit-test")
    for k in ("protocol_hash", "code_commit", "judge_commit",
              "scenario_manifest_hash", "map_spec_hash", "lattice_hash",
              "generated_at"):
        assert k in s, f"스탬프 필드 누락: {k} (docs/74 §0-4)"
    assert s["protocol_hash"], "protocol_hash 가 비었다 -- manifest 를 먼저 만들어야 한다"
    assert len(s["judge_commit"]) == 16


def test_p76b_lattice_hash_depends_only_on_the_grid_definition():
    a = L.build_lattice()
    b = L.build_lattice()
    assert a["lattice_hash"] == b["lattice_hash"], "격자 해시가 불안정하다"
    # 격자를 바꾸면 해시가 바뀌어야 한다 (봉인이 의미를 가지려면)
    orig = L.AXIS_GRID["chi"]
    try:
        L.AXIS_GRID["chi"] = orig + [2.1]
        assert L.build_lattice()["lattice_hash"] != a["lattice_hash"]
    finally:
        L.AXIS_GRID["chi"] = orig
    assert a["n_points"] == (len(L.AXIS_GRID["chi"]) * len(L.AXIS_GRID["kappa"])
                             * len(L.AXIS_GRID["mu"]) * len(L.N_GRID_DISCRETE))


def test_p76c_core_axes_and_conditioning_are_disjoint_and_declared():
    assert 2 <= len(L.CORE_AXES) <= 3, "plotted axes 는 2~3 개 (docs/74 §3.9)"
    for k in L.CORE_AXES:
        assert k in L.PI_GROUPS and k in L.AXIS_GRID
    for k in L.CONDITIONING_ORDER:
        assert k in L.PI_GROUPS, f"미선언 Π: {k}"
        assert k not in L.CORE_AXES, "conditioning 이 core 축과 겹친다"
    # 결과 후 축 추가 금지 규칙이 산출물에 실려 있어야 한다
    rules = " ".join(L.build_lattice()["rules"]).lower()
    assert "phase iii-b" in rules and "never creates new points" in rules


def test_p76d_measure_gate_constants_are_frozen():
    assert M.N_GRID == (2000, 8000, 32000)
    assert M.GATE2 == {"median": 0.02, "p95": 0.05}
    assert M.GATE3 == {"max_shift": 0.05}
    assert M.THETA == 0.90, "게이트 판정 θ 는 Stage-2 θ (0.90) 와 같아야 한다"
    assert "base" in M.ALLOC_VARIANTS and len(M.ALLOC_VARIANTS) >= 5


def test_p76e_informative_rule_excludes_degenerate_states():
    """0/1 로 자명한 상태는 통계에서 빠져야 한다 -- 안 그러면 게이트가 공짜로 통과한다."""
    zero = [{"V_hold": 0.0, "V_nolim": 0.0}] * 3
    one = [{"V_hold": 1.0, "V_nolim": 1.0}] * 3
    mixed = [{"V_hold": 0.0, "V_nolim": 0.0}, {"V_hold": 0.42, "V_nolim": 0.0}]
    assert not M._informative(zero)
    assert not M._informative(one)
    assert M._informative(mixed)


def test_p76f_per_episode_aggregation_is_episode_unit():
    """에피소드 안의 상태들을 먼저 평균한 뒤 에피소드 분포를 본다 (pseudoreplication 금지)."""
    diffs = {0: [0.0, 0.0, 0.0, 0.0], 1: [1.0]}      # ep0 4 상태, ep1 1 상태
    out = M._per_episode(diffs)
    assert out["n_episodes"] == 2
    assert out["median"] == 0.5, "상태 수로 가중되면 0.2 가 된다 (= 잘못)"
    assert out["max"] == 1.0
