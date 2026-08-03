"""P41/P42: 스윕 판정식의 무결성 (docs/47 §4.3).

판정식은 **결과를 보기 전에** 고정되어야 하고, 성립 불가능한 조건을 담아서도 안 된다.
처음 선언("hold 대비 무력화율과 비손실 비율을 둘 다 개선")이 후자였다 -- 스크립트
기준선은 구조적으로 하드킬을 못 해 비손실 비율이 자명하게 1.00 이기 때문이다.
"""
from __future__ import annotations

import json

import pytest

from shepherd.scripts.sweep_m4 import SHAPE, aggregate, wilson


def _summary(tmp, name, *, w_kill, seed, obs, shape_n, shape_rate,
             nondestructive=1.0, overall=0.2):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "summary.json").write_text(json.dumps({
        "seed": seed, "w_kill": w_kill, "attacker": "A2",
        "threat_randomized": True, "threat_obs": obs,
        "final_eval_episodes": 300,
        "final_eval": {
            "n": 300, "neutralized_rate": overall,
            "nondestructive_frac": nondestructive,
            "by_regime": {SHAPE: {"n": shape_n, "neutralized_rate": shape_rate}},
        }}))
    return d


BASE = {"n": 500, "neutralized_rate": 0.155, "nondestructive_frac": 1.0,
        "by_regime": {SHAPE: {"n": 305, "k": 0, "neutralized_rate": 0.0,
                              "wilson_lo": 0.0, "wilson_hi": 0.0125}}}


def test_p41_wilson_is_finite_at_zero():
    """k=0 에서도 상한이 유한해야 판정식이 성립한다 (rule of three 근방)."""
    lo, hi = wilson(0, 122)
    assert lo == 0.0
    assert 0.02 < hi < 0.04                     # 3/122 = 0.0246 근방
    lo5, hi5 = wilson(0, 500)
    assert hi5 < hi, "n 을 늘리면 상한이 조여야 한다"
    assert wilson(0, 0) == (0.0, 1.0)           # 표본 없음 -> 정보 없음


def test_p41b_wilson_lower_bound_orders():
    """성공이 늘면 하한이 단조 증가한다."""
    los = [wilson(k, 183)[0] for k in (0, 3, 9, 20)]
    assert all(los[i] < los[i + 1] for i in range(len(los) - 1))


def test_p42_verdict_requires_separated_intervals(tmp_path):
    """1차 판정: shape 무력화율의 Wilson 하한이 기저 상한을 넘어야 '순이득'."""
    # 9/183 -> 하한 0.026 > 기저 상한 0.0125  => 넘는다
    _summary(tmp_path, "a", w_kill=0.5, seed=0, obs=True, shape_n=183, shape_rate=9 / 183)
    r = aggregate(str(tmp_path), baseline=BASE)
    assert r["runs_beating_baseline"] == 1
    assert "순이득 있음" in r["verdict"]


def test_p42b_small_effect_does_not_pass(tmp_path):
    """1/183 은 기저와 구간이 겹치므로 통과하면 안 된다 (검정력 부족을 성공으로 읽지 않기)."""
    _summary(tmp_path, "b", w_kill=0.5, seed=0, obs=True, shape_n=183, shape_rate=1 / 183)
    r = aggregate(str(tmp_path), baseline=BASE)
    assert r["runs_beating_baseline"] == 0
    assert "순이득 없음" in r["verdict"]


def test_p42c_nondestructive_is_not_compared_to_hold(tmp_path):
    """2차 지표는 hold 대비가 아니라 w_kill 축을 따라 정책끼리 본다.

    모든 런의 비손실이 hold 와 같은 1.00 이어도 판정이 막히지 않아야 한다.
    """
    for i, w in enumerate((0.0, 0.5, 1.0)):
        _summary(tmp_path, f"w{i}", w_kill=w, seed=0, obs=True,
                 shape_n=183, shape_rate=9 / 183, nondestructive=1.0)
    r = aggregate(str(tmp_path), baseline=BASE)
    assert r["runs_beating_baseline"] == 3        # 1차는 통과
    assert "secondary_nondestructive_monotone" in r
    assert set(r["secondary_nondestructive_by_w_kill"]) == {"0.0", "0.5", "1.0"}


def test_p42d_empty_root_is_not_a_pass(tmp_path):
    """산출물이 없으면 '순이득 없음' 이 아니라 '못 쟀음' 이어야 한다."""
    r = aggregate(str(tmp_path), baseline=BASE)
    assert r.get("n") == 0
    assert r.get("verdict") is None


REF = {"n": 300, "limiter_mode": "intercept", "nondestructive_frac": 0.611,
       "by_regime": {SHAPE: {"n": 182, "k": 15, "neutralized_rate": 15 / 182,
                             "wilson_lo": 0.0506, "wilson_hi": 0.1315}}}


def test_p43_partial_gain_is_named(tmp_path):
    """hold 는 넘었지만 최선의 손튜닝은 못 넘으면 '부분 순이득' 으로 구분해야 한다.

    hold(0/297) 만 넘는 것은 약한 기준이다. 그것만 보고 '협력의 순이득 있음' 으로
    적으면 최선의 손튜닝에 진 결과를 승리로 읽게 된다.
    """
    _summary(tmp_path, "a", w_kill=0.5, seed=0, obs=True, shape_n=183, shape_rate=9 / 183)
    r = aggregate(str(tmp_path), baseline=BASE, reference=REF)
    assert r["runs_beating_baseline"] == 1
    assert r["runs_beating_reference"] == 0
    assert "부분 순이득" in r["verdict"]


def test_p43b_full_gain_requires_beating_reference(tmp_path):
    """참조까지 넘으면 '순이득 있음'."""
    _summary(tmp_path, "b", w_kill=0.5, seed=0, obs=True, shape_n=183, shape_rate=40 / 183)
    r = aggregate(str(tmp_path), baseline=BASE, reference=REF)
    assert r["runs_beating_reference"] == 1
    assert "순이득 있음" in r["verdict"]


def test_p43c_reference_is_optional(tmp_path):
    """참조가 없어도 1차 판정은 그대로 동작한다."""
    _summary(tmp_path, "c", w_kill=0.5, seed=0, obs=True, shape_n=183, shape_rate=9 / 183)
    r = aggregate(str(tmp_path), baseline=BASE)
    assert r["runs_beating_baseline"] == 1
    assert "순이득 있음" in r["verdict"]


# ─────────────────────────────────────────────────────────────────────────
# P45: BAND_AIM 배선 (docs/47 §4.4)
#
# 축을 문서에만 선언하고 코드에 안 꽂으면 정정 6(선언 그림자)이 재발한다.
# 스윕이 끝난 뒤에 다시 뽑으면 **결과를 본 뒤 축을 만든 모양**이 되므로,
# 판정용 최종 평가와 같은 호출에서 나와야 한다.
# ─────────────────────────────────────────────────────────────────────────
def _summary_with_bands(tmp, name, *, w_kill, seed, aim_neut, aim_cap, aim_n=110):
    d = tmp / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "summary.json").write_text(json.dumps({
        "seed": seed, "w_kill": w_kill, "attacker": "A2",
        "threat_randomized": True, "threat_obs": True,
        "final_eval_episodes": 300,
        "final_eval": {"n": 300, "neutralized_rate": 0.2, "nondestructive_frac": 1.0,
                       "by_regime": {SHAPE: {"n": 183, "neutralized_rate": 0.0}}},
        "final_eval_bands": {
            "EASY": {"n": 60, "net_capture": {"k": 50, "p": 0.83},
                     "neutralized": {"k": 50, "p": 0.83}},
            "BAND_AIM": {"n": aim_n, "net_capture": {"k": 1, "p": aim_cap},
                         "neutralized": {"k": 2, "p": aim_neut}},
            SHAPE: {"n": 130, "net_capture": {"k": 0, "p": 0.0},
                    "neutralized": {"k": 0, "p": 0.0}},
        }}))
    return d


def test_p45_aggregate_reports_band_aim(tmp_path):
    """세 칸 집계가 summary.json 에서 그대로 올라와야 한다."""
    from shepherd.scripts.sweep_m4 import BAND, aggregate

    for i, (nz, cp) in enumerate([(0.10, 0.05), (0.20, 0.09), (0.30, 0.13)]):
        _summary_with_bands(tmp_path, f"r{i}", w_kill=0.5, seed=i,
                            aim_neut=nz, aim_cap=cp)
    out = aggregate(str(tmp_path), baseline=dict(BASE))

    assert BAND == "BAND_AIM"
    a = out["band_aim"]
    assert a["n_runs"] == 3
    assert a["run_neutralized_med"] == pytest.approx(0.20)
    assert a["run_net_capture_med"] == pytest.approx(0.09)
    assert "1차 판정식" in a["_note"]


def test_p45b_band_aim_never_enters_the_primary_verdict(tmp_path):
    """★ BAND_AIM 이 아무리 좋아도 1차 판정은 안 바뀐다 (사전 등록 보호)."""
    from shepherd.scripts.sweep_m4 import aggregate

    for i in range(3):
        _summary_with_bands(tmp_path, f"r{i}", w_kill=0.5, seed=i,
                            aim_neut=0.99, aim_cap=0.99)
    out = aggregate(str(tmp_path), baseline=dict(BASE))
    assert out["runs_beating_baseline"] == 0
    assert "순이득 없음" in out["verdict"]


def test_p45c_old_runs_without_bands_do_not_crash(tmp_path):
    """구버전 summary.json(밴드 없음)이 섞여도 집계가 죽지 않는다."""
    from shepherd.scripts.sweep_m4 import aggregate

    _summary(tmp_path, "old", w_kill=0.5, seed=0, obs=True,
             shape_n=183, shape_rate=0.0)
    out = aggregate(str(tmp_path), baseline=dict(BASE))
    assert out["band_aim"]["n_runs"] == 0
    assert "구버전" in out["band_aim"]["_note"]
