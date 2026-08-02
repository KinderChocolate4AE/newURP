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
