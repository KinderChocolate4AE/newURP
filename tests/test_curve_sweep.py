"""P44: 포획 확률 곡선의 무결성 (docs/45 §9).

곡선이 두 번째 경계의 **검증 증거**로 쓰이므로, 그 증거가 성립하려면 세 가지가
참이어야 한다.

  1. 구간 격자에 `a*` 가 **정확히** 놓인다 -- 안 그러면 "경계 위 0%" 가 칸 안에서
     희석돼 주장 자체가 흐려진다.
  2. `a*(psi=0)` 은 명제 N 과 **같은 값**이어야 한다 -- 일반형이 특수해를 포함하지
     않으면 "같은 경계의 확장"이라고 말할 수 없다.
  3. `mode="hold"` 는 커밋을 켜지 않는다 -- 정정 8. 이걸 켠 채로 hold 를 돌리면
     intercept 와 같은 조건이라고 **착각**하게 된다 (실제로 300판 헛돌렸다).
"""
from __future__ import annotations

import math

import pytest

from shepherd.m4_config import THREAT_BRACKET, m4_config
from shepherd.scripts.curve_sweep import (MODES, a_star, a_star_psi, bin_edges,
                                          summarize_curve, wilson)


def test_p44_boundary_sits_exactly_on_a_grid_line():
    """`a*` 가 격자선 위에 정확히 놓여야 '경계 위' 집계가 오염되지 않는다."""
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    cfg = m4_config()
    astar = a_star(cfg["physics"]["net_radius"], cfg["physics"]["tau_deploy"])
    edges = bin_edges(float(lo), float(hi), astar, per_side=4)

    assert len(edges) == 9
    assert edges[0] == pytest.approx(float(lo))
    assert edges[-1] == pytest.approx(float(hi))
    assert min(abs(e - astar) for e in edges) < 1e-9, "a* 가 격자선 위에 없다"
    assert edges == sorted(edges)
    # 어떤 칸도 경계를 가로지르지 않는다
    for a, b in zip(edges[:-1], edges[1:]):
        assert not (a < astar < b), f"칸 [{a}, {b}) 가 a* 를 가로지른다"


def test_p44b_general_form_reduces_to_proposition_n():
    """`a*(psi=0)` == `2 rho / tau^2`. 일반형이 특수해를 포함해야 한다."""
    cfg = m4_config()
    rho = cfg["physics"]["net_radius"]
    tau = cfg["physics"]["tau_deploy"]
    cone = cfg["viability"]["cone"]

    assert a_star_psi(0.0, range_max=cone["range_max"],
                      half_angle=cone["half_angle"], tau=tau) == \
        pytest.approx(a_star(rho, tau), rel=2e-3)


def test_p44c_psi_lowers_the_boundary_monotonically():
    """조준오차가 커지면 경계는 **내려간다** (협력 필요 영역이 넓어진다)."""
    cfg = m4_config()
    cone, tau = cfg["viability"]["cone"], cfg["physics"]["tau_deploy"]
    vals = [a_star_psi(math.radians(d), range_max=cone["range_max"],
                       half_angle=cone["half_angle"], tau=tau)
            for d in (0.0, 2.0, 4.26, 6.0)]
    assert vals == sorted(vals, reverse=True)
    assert vals[2] == pytest.approx(25.75, abs=0.15)      # docs/45 §9.3 고정값


def test_p44d_hold_never_commits():
    """정정 8 — hold 는 커밋을 켜지 않는다. 켜면 intercept 와 혼동된다."""
    from shepherd.scripts import curve_sweep as cs
    import inspect

    src = inspect.getsource(cs.run_curve)
    assert 'commit = (mode == "intercept")' in src, \
        "커밋 조건이 intercept 전용이 아니다"
    assert set(MODES) == {"hold", "ring", "intercept"}


def test_p44e_wilson_upper_bound_is_finite_at_zero():
    """k=0 구간에서도 상한이 유한해야 '0회' 주장에 구간을 붙일 수 있다."""
    p, lo, hi = wilson(0, 297)
    assert p == 0.0 and lo == 0.0
    assert 0.0 < hi < 0.02


def test_p44g_run_curve_matches_mission_eval_episode_for_episode():
    """★ 두 계측 경로가 **같은 판**을 도는가.

    `mission_eval(records=...)` 와 `run_curve` 는 같은 draw 를 돈다고 주장한다.
    주장만 하고 두면 한쪽만 고쳐졌을 때 곡선과 기준선이 조용히 갈라진다.
    """
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.m4_env import mission_eval
    from shepherd.scripts.curve_sweep import run_curve
    from shepherd.spawn_rand import SpawnSpec

    n = 4
    ref = []
    mission_eval(0, n, system=SystemSpec(),
                 reward=RewardSpec(w_kill=0.5, enabled=True),
                 attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                 spawn=SpawnSpec(), limiter_mode="hold", records=ref)
    got = run_curve(0, n, mode="hold")["records"]

    assert [r["label"] for r in got] == [r["label"] for r in ref]
    assert [round(r["a_att"], 9) for r in got] == [round(r["a_att"], 9) for r in ref]
    assert [r["regime"] for r in got] == [r["regime"] for r in ref]


def test_p44f_summary_carries_the_caveat():
    """곡선이 학습 성능으로 오독되면 안 된다 — 단서는 데이터에 붙어 다닌다."""
    data = {"mode": "hold", "seed0": 0, "n_done": 2, "n_target": 2,
            "level": "A2", "jink_amp": 0.6,
            "records": [{"episode": 0, "label": "NET_CAPTURE",
                         "regime": "FREE_CAPTURE", "a_att": 15.0,
                         "att_speed": 20.0, "net_radius": 1.77, "tau": 0.3},
                        {"episode": 1, "label": "PENETRATED",
                         "regime": "SHAPING_NEEDED", "a_att": 60.0,
                         "att_speed": 20.0, "net_radius": 1.77, "tau": 0.3}]}
    s = summarize_curve(data)
    assert "손튜닝" in s["_caveat"] and "학습 정책의 성능이 아니다" in s["_caveat"]
    assert s["above_a_star"]["net_capture_k"] == 0
    assert s["above_a_star"]["n"] == 1
    assert sum(b["n"] for b in s["bins"]) == 2


def test_p44h_band_aim_is_declared_and_frozen():
    """BAND_AIM 은 **결과 전에** 선언된 보고 축이다 (docs/47 §4.4).

    경계값이 코드 밖(문서에만) 있으면 선언 그림자(정정 6)가 재발한다.
    여기에 못을 박아 두면 나중에 조용히 옮길 수 없다.
    """
    from shepherd.scripts.curve_sweep import (BANDS, PSI_MED_DEG, _band_bounds,
                                              band_of)

    assert PSI_MED_DEG == pytest.approx(4.26)
    lo, hi = _band_bounds()
    assert lo == pytest.approx(25.75, abs=0.15)
    assert hi == pytest.approx(39.33, abs=0.05)
    assert BANDS == ("EASY", "BAND_AIM", "SHAPING_NEEDED")

    assert band_of(11.0) == "EASY"
    assert band_of(lo - 1e-6) == "EASY"
    assert band_of(lo) == "BAND_AIM"
    assert band_of(hi - 1e-6) == "BAND_AIM"
    assert band_of(hi) == "SHAPING_NEEDED"
    assert band_of(78.0) == "SHAPING_NEEDED"


def test_p44i_top_band_agrees_with_regime_of():
    """가장 위 칸은 `regime_of` 와 **같은 경계**여야 한다 -- 표에서 갈리면 안 된다."""
    from shepherd.m4_env import regime_of
    from shepherd.scripts.curve_sweep import band_of

    cfg = m4_config()
    tau, rho = cfg["physics"]["tau_deploy"], cfg["physics"]["net_radius"]
    for a in (11.0, 20.0, 30.0, 39.0, 39.4, 50.0, 78.0):
        assert (band_of(a) == "SHAPING_NEEDED") == \
            (regime_of(a, tau, rho) == "SHAPING_NEEDED"), f"a={a} 에서 경계가 갈린다"


def test_p44j_wilson_has_exactly_one_definition():
    """★ Wilson 은 `shepherd.stats` 한 곳에서만 정의된다.

    2026-08-03: 네 곳에 복사돼 있었고 **z 기본값이 서로 달랐다**
    (`curve_sweep` 1.96 / `sweep_m4` 1.959964). 판정식이 이 식에 걸려 있으므로
    복사본이 다시 생기면 여기서 깨진다.

    `curve_sweep.wilson` 은 3-튜플 + `n<=0 -> (0,0,0)` 이라는 **다른 계약**을 갖는
    래퍼다. 그 차이를 여기 못 박는다 -- 표본 없는 밴드를 0 으로 찍기 위한 것이라
    `stats` 의 `(0, 1)`(정보 없음)로 바꾸면 안 된다.
    """
    import inspect

    from shepherd.scripts import curve_sweep as cs
    from shepherd.scripts import sweep_m4 as sw
    from shepherd.stats import Z_TWO_SIDED_95
    from shepherd.stats import wilson as canonical

    assert sw.wilson is canonical, "sweep_m4 가 자체 구현으로 되돌아갔다"

    src = inspect.getsource(cs.wilson)
    assert "_wilson(" in src, "curve_sweep 가 자체 구현으로 되돌아갔다"
    assert cs.wilson.__defaults__ == (Z_TWO_SIDED_95,), "z 기본값이 갈라졌다"

    for n in (1, 5, 182, 297, 500, 904):
        for k in (0, 1, n // 2, n):
            p, lo, hi = cs.wilson(k, n)
            assert (lo, hi) == canonical(k, n)
            assert p == k / n
    assert cs.wilson(0, 0) == (0.0, 0.0, 0.0)      # 래퍼 계약
    assert canonical(0, 0) == (0.0, 1.0)           # 정본 계약
