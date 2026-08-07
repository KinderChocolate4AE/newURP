"""draw_threat_v3 v2 (docs/68 r1) + P95′ triplet — 순수 draw 수준 회귀.

P92′/P95′ 게이트(threat_v3_gates)가 정본 판정이고, 여기는 그 성질들이
회귀하지 않게 잠그는 경량판이다 (env 불필요 — SHA-256 산술만).
v1 (docs/61 결합 반응성 층)은 P95 RED 로 봉인 — 재현은 git 이력.
"""
from __future__ import annotations

import pytest

from shepherd.scale_v2 import (A2_V4, EPISODE_LEN_TRAIN, SCALE_V3_TRAIN_CFG,
                               THREAT_V3_SPAWN, V3_SENSE_COMMON, V3_STANDBY_R,
                               V3_TRAIN_GAIN, draw_threat_v3,
                               p95_confirm_triplet, reaction_stratum)


def test_deterministic_and_layer_separated():
    a = draw_threat_v3(0, 3, "train")
    b = draw_threat_v3(0, 3, "train")
    assert a["attacker"] == b["attacker"] and a["standby"] == b["standby"]
    assert a["cell"] == b["cell"]
    assert any(draw_threat_v3(0, ep, "iid")["attacker"]
               != draw_threat_v3(0, ep, "train")["attacker"] for ep in range(8))


def test_unknown_layer_rejected():
    with pytest.raises(ValueError):
        draw_threat_v3(0, 0, "nominal")   # NOMINAL 로 학습 금지 (관통 규율 2)


def test_bounds_and_cell_consistency():
    for ep in range(300):
        d = draw_threat_v3(0, ep, "train")
        att, (a_name, b_name) = d["attacker"], d["cell"]
        rg = V3_TRAIN_GAIN[a_name]
        assert rg[0] <= att.route_gain <= rg[1]
        # sense 는 층과 무관한 공통 nuisance (docs/68 §1)
        assert V3_SENSE_COMMON[0] <= att.sense_range <= V3_SENSE_COMMON[1]
        assert V3_STANDBY_R[0] <= d["standby"].R <= V3_STANDBY_R[1]
        assert d["spawn"] == THREAT_V3_SPAWN
        assert d["cfg"] is SCALE_V3_TRAIN_CFG
        if b_name == "cruise":
            assert att.sprint_range == 0.0 and att.slowdown_range == (0.0, 0.0)
        elif b_name == "sprint_slowdown":
            far, near = att.slowdown_range
            assert near == att.sprint_range and 20.0 <= far - near <= 40.0
            assert 0.4 <= att.slowdown_frac <= 0.8


def test_sense_is_stratum_independent():
    """같은 에피소드에서 층이 바뀌어도 sense draw 는 동일해야 한다 (공통 축)."""
    for ep in range(20):
        senses = {reaction_stratum(0, ep, s)["attacker"].sense_range
                  for s in V3_TRAIN_GAIN}
        assert len(senses) == 1


def test_all_nine_cells_reachable():
    cells = {draw_threat_v3(0, ep, "train")["cell"] for ep in range(400)}
    assert len(cells) == 9


def test_cruise_is_nested_v2_profile():
    cruise = next(d["attacker"] for ep in range(200)
                  if (d := draw_threat_v3(0, ep, "train"))["cell"][1] == "cruise")
    for f in ("level", "jink_amp", "jink_freq", "homing_gain", "sprint_range",
              "sprint_frac", "slowdown_range", "slowdown_frac", "lam_gain",
              "lam_range", "seed"):
        assert getattr(cruise, f) == getattr(A2_V4, f), f


def test_horizon_declared():
    assert EPISODE_LEN_TRAIN == 1100                     # docs/61 §2 (P93 확정)
    assert SCALE_V3_TRAIN_CFG["train.episode_len"] == 1100


def test_gain_bin_names_display_only():
    """docs/69 §6-2: GAIN_BIN_NAMES 는 표시용 — 키 집합만 일치하면 되고
    sampling/SHA 개입은 parity pin (test_contract_parity) 이 잡는다."""
    from shepherd.scale_v2 import GAIN_BIN_NAMES
    assert set(GAIN_BIN_NAMES) == set(V3_TRAIN_GAIN)
    assert sorted(GAIN_BIN_NAMES.values()) == ["G1", "G2", "G3"]


def test_reaction_stratum_is_paired_crn():
    """CRN 계약 v2: route_gain 만 교체, 그 외 전부 base 와 bit 동일."""
    from dataclasses import fields

    for ep in (0, 3, 11):
        base = draw_threat_v3(0, ep, "train")
        got = {s: reaction_stratum(0, ep, s) for s in V3_TRAIN_GAIN}
        for s, d in got.items():
            rg = V3_TRAIN_GAIN[s]
            assert rg[0] <= d["attacker"].route_gain <= rg[1]
            assert d["standby"] == base["standby"]        # P_init 고정
            assert d["spawn"] == base["spawn"]
            assert d["cell"][1] == base["cell"][1]        # 속도 regime 고정
            for f in fields(d["attacker"]):
                if f.name in ("route_gain", "label"):
                    continue
                assert getattr(d["attacker"], f.name) == \
                    getattr(base["attacker"], f.name), f.name
        u = ((got["weak"]["attacker"].route_gain - 0.2) / 0.2)
        for s, lo in (("medium", 0.4), ("strong", 0.6)):
            assert abs(got[s]["attacker"].route_gain - (lo + u * 0.2)) < 1e-12

    with pytest.raises(ValueError):
        reaction_stratum(0, 0, "nominal")


# ── P95′ confirmatory triplet (docs/68 §3) ─────────────────────────────────
def test_p95_confirm_regime_preassignment():
    regs = [p95_confirm_triplet(ep)["regime"] for ep in range(30)]
    assert regs[:10] == ["cruise"] * 10
    assert regs[10:20] == ["sprint"] * 10
    assert regs[20:] == ["sprint_slowdown"] * 10
    with pytest.raises(ValueError):
        p95_confirm_triplet(30)


def test_p95_confirm_triplet_paired_and_bounded():
    from dataclasses import fields

    for ep in (0, 12, 25):
        trip = p95_confirm_triplet(ep)
        arms = trip["arms"]
        assert set(arms) == set(V3_TRAIN_GAIN)
        senses = {a.sense_range for a in arms.values()}
        assert len(senses) == 1                          # 동일 sense 공유
        assert V3_SENSE_COMMON[0] <= senses.pop() <= V3_SENSE_COMMON[1]
        for s, att in arms.items():
            rg = V3_TRAIN_GAIN[s]
            assert rg[0] <= att.route_gain <= rg[1]
        # route_gain·label 외 전 필드 동일 (paired)
        ref = arms["weak"]
        for att in (arms["medium"], arms["strong"]):
            for f in fields(att):
                if f.name in ("route_gain", "label"):
                    continue
                assert getattr(att, f.name) == getattr(ref, f.name), f.name
        assert V3_STANDBY_R[0] <= trip["standby"].R <= V3_STANDBY_R[1]
        assert trip["cfg"]["train.episode_len"] == 1100


def test_p95_confirm_namespace_separated_from_train():
    """confirm ns 는 기존 TRAIN draw 와 분리 (docs/68 §3 — 봉인 규율)."""
    diff = any(
        p95_confirm_triplet(ep)["arms"]["weak"].sense_range
        != draw_threat_v3(0, ep, "train")["attacker"].sense_range
        for ep in range(8))
    assert diff
