"""draw_threat_v3 (docs/61 §1-§2, P92 대상 성질) — 순수 draw 수준 회귀.

P92 게이트(threat_v3_gates.p92)가 정본 판정이고, 여기는 그 성질들이
회귀하지 않게 잠그는 경량판이다 (env 불필요 — SHA-256 산술만).
"""
from __future__ import annotations

import pytest

from shepherd.scale_v2 import (A2_V4, EPISODE_LEN_TRAIN, SCALE_V3_TRAIN_CFG,
                               THREAT_V3_SPAWN, V3_STANDBY_R, V3_TRAIN_CELLS_A,
                               draw_threat_v3)


def test_deterministic_and_layer_separated():
    a = draw_threat_v3(0, 3, "train")
    b = draw_threat_v3(0, 3, "train")
    assert a["attacker"] == b["attacker"] and a["standby"] == b["standby"]
    assert a["cell"] == b["cell"]
    # IID 는 namespace 가 다르다 -- 같은 (seed, ep) 에서 다른 draw
    assert any(draw_threat_v3(0, ep, "iid")["attacker"]
               != draw_threat_v3(0, ep, "train")["attacker"] for ep in range(8))


def test_unknown_layer_rejected():
    with pytest.raises(ValueError):
        draw_threat_v3(0, 0, "nominal")   # NOMINAL 로 학습 금지 (관통 규율 2)


def test_bounds_and_cell_consistency():
    for ep in range(300):
        d = draw_threat_v3(0, ep, "train")
        att, (a_name, b_name) = d["attacker"], d["cell"]
        rg, sr = V3_TRAIN_CELLS_A[a_name]
        assert rg[0] <= att.route_gain <= rg[1]
        assert sr[0] <= att.sense_range <= sr[1]
        assert V3_STANDBY_R[0] <= d["standby"].R <= V3_STANDBY_R[1]
        assert d["spawn"] == THREAT_V3_SPAWN
        assert d["cfg"] is SCALE_V3_TRAIN_CFG
        if b_name == "cruise":
            assert att.sprint_range == 0.0 and att.slowdown_range == (0.0, 0.0)
        elif b_name == "sprint_slowdown":
            far, near = att.slowdown_range
            assert near == att.sprint_range and 20.0 <= far - near <= 40.0
            assert 0.4 <= att.slowdown_frac <= 0.8


def test_all_nine_cells_reachable():
    cells = {draw_threat_v3(0, ep, "train")["cell"] for ep in range(400)}
    assert len(cells) == 9


def test_cruise_is_nested_v2_profile():
    """cruise 층 = 속도 프로파일 필드가 A2_V4 기본값과 bit 동일 (v2 nested)."""
    cruise = next(d["attacker"] for ep in range(200)
                  if (d := draw_threat_v3(0, ep, "train"))["cell"][1] == "cruise")
    for f in ("level", "jink_amp", "jink_freq", "homing_gain", "sprint_range",
              "sprint_frac", "slowdown_range", "slowdown_frac", "lam_gain",
              "lam_range", "seed"):
        assert getattr(cruise, f) == getattr(A2_V4, f), f


def test_horizon_declared():
    assert EPISODE_LEN_TRAIN == 1100                     # docs/61 §2 (P93 확정)
    assert SCALE_V3_TRAIN_CFG["train.episode_len"] == 1100


def test_reaction_stratum_is_paired_crn():
    """P95 CRN 계약: reaction 축만 교체, 그 외 전부 base 와 bit 동일."""
    from dataclasses import fields

    from shepherd.scale_v2 import V3_TRAIN_CELLS_A, reaction_stratum

    for ep in (0, 3, 11):
        base = draw_threat_v3(0, ep, "train")
        got = {s: reaction_stratum(0, ep, s) for s in V3_TRAIN_CELLS_A}
        for s, d in got.items():
            rg, sr = V3_TRAIN_CELLS_A[s]
            assert rg[0] <= d["attacker"].route_gain <= rg[1]
            assert sr[0] <= d["attacker"].sense_range <= sr[1]
            assert d["standby"] == base["standby"]        # P_init 고정
            assert d["spawn"] == base["spawn"]
            assert d["cell"][1] == base["cell"][1]        # 속도 regime 고정
            for f in fields(d["attacker"]):
                if f.name in ("route_gain", "sense_range", "label"):
                    continue
                assert getattr(d["attacker"], f.name) == \
                    getattr(base["attacker"], f.name), f.name
        # 축 내 상대 위치(u)가 같아야 paired: 층 간 route_gain 차 = 범위 이동분
        u = ((got["weak"]["attacker"].route_gain - 0.2) / 0.2)
        for s, lo in (("medium", 0.4), ("strong", 0.6)):
            assert abs(got[s]["attacker"].route_gain - (lo + u * 0.2)) < 1e-12

    with pytest.raises(ValueError):
        reaction_stratum(0, 0, "nominal")
