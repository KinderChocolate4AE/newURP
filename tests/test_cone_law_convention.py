"""cone 여유 법칙 정정(2026-08-28)의 게이트.

지키려는 것 넷:
  1. 기하 — 내접구 반경이므로 측면 항은 sin(theta) 다 (tan 이 아니다).
  2. 동결 재현 — 사전등록 E1e 스크립트는 여전히 "tan" 을 쓴다.
  3. 재구현 금지 — Fig.1 이 법칙을 자체 구현하지 않고 정본을 import 한다.
  4. 판정 불변 — 판별 가설 H3 는 두 규약에서 같은 예측을 낸다.
"""
import math
import pathlib

import pytest

from shepherd.m4_config import m4_config
from shepherd.scripts.e1e_axial_optimum import a_star, ax_optimum, s_of_ax

ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = m4_config()
THETA = float(CFG["viability"]["cone"]["half_angle"])
RMAX = float(CFG["viability"]["cone"]["range_max"])
TAU = float(CFG["physics"]["tau_deploy"])


def test_lateral_term_is_perpendicular_distance():
    """축 위의 점에서 원뿔 측면까지의 최단거리 = ax*sin(theta).

    독립 검산: 2D 단면에서 점 (ax,0) 과 원점을 지나 각 theta 인 직선
    x*sin - y*cos = 0 사이의 거리.
    """
    ax = 5.0
    expect = abs(ax * math.sin(THETA)) / math.hypot(math.sin(THETA), math.cos(THETA))
    got = float(s_of_ax(ax, theta=THETA, rmax=RMAX))       # far-edge 는 여유 있음
    assert RMAX - ax > expect, "이 ax 에서는 측면 항이 binding 이어야 게이트가 산다"
    assert got == pytest.approx(expect, rel=1e-12)
    assert got < ax * math.tan(THETA)                       # tan 은 과대평가


def test_default_convention_is_inscribed():
    assert float(a_star(ax_optimum(theta=THETA, rmax=RMAX), theta=THETA,
                        rmax=RMAX, tau=TAU)) == pytest.approx(31.77, abs=0.02)


def test_frozen_prereg_script_still_pins_tan():
    """동결 아티팩트 재현성 -- main() 이 규약을 명시 고정해야 한다."""
    src = (ROOT / "shepherd/scripts/e1e_axial_optimum.py").read_text(encoding="utf-8")
    assert 'FROZEN_CONVENTION = "tan"' in src
    assert "convention=FROZEN_CONVENTION" in src
    assert float(a_star(ax_optimum(theta=THETA, rmax=RMAX, convention="tan"),
                        theta=THETA, rmax=RMAX, tau=TAU,
                        convention="tan")) == pytest.approx(32.37, abs=0.02)


def test_figure_does_not_reimplement_the_law():
    """docs/85 R-001/R-012 재발 방지 -- Fig.1 은 정본을 import 만 한다."""
    src = (ROOT / "shepherd/scripts/paper_figs.py").read_text(encoding="utf-8")
    assert "from shepherd.scripts.e1e_axial_optimum import" in src
    assert "r_max * tan_t" not in src, "법칙 자체 구현이 되살아났다"


def test_discriminating_arm_is_convention_invariant():
    """E-3(ax=7.20) 은 far-edge 가 binding -- H3 예측이 규약에 무관해야 한다."""
    vals = [float(a_star(7.20, theta=THETA, rmax=RMAX, tau=TAU, convention=c))
            for c in ("tan", "inscribed")]
    assert vals[0] == pytest.approx(vals[1], rel=1e-12)
    assert vals[0] == pytest.approx(22.67, abs=0.02)


def test_recompute_preserves_prereg_verdicts():
    """정정 후에도 S1 은 사전등록 수락선(>=0.95)을 넘는다."""
    from shepherd.scripts.e1e_law_recompute import recompute
    src = ROOT / "results/e1e.json"
    if not src.exists():
        pytest.skip("frozen E1e artifact not present")
    r = recompute(src)
    for cv in ("tan", "inscribed"):
        assert r["conventions"][cv]["s1_min_accuracy"] >= 0.95
    # 측정값(cross50)은 규약과 무관하므로 두 규약에서 동일해야 한다
    a_t = r["conventions"]["tan"]["arms"]
    a_i = r["conventions"]["inscribed"]["arms"]
    assert [v["cross50"] for v in a_t.values()] == [v["cross50"] for v in a_i.values()]


def test_bad_convention_rejected():
    with pytest.raises(ValueError):
        s_of_ax(5.0, theta=THETA, rmax=RMAX, convention="sin")
