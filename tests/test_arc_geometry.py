"""docs/122 P1d: arc_geometry — rho 없으면 c5 와 동일, 있으면 c5 대형을 중점으로 전진."""
from shepherd.agents.baselines import arc_geometry


def test_arc_geometry():
    tgt, dphi = [0.0, 0.0, 0.0], 0.5
    assert arc_geometry(tgt, [96.0, 0.0, 3.0], 9.0, dphi) == (9.0, dphi)  # c5: 거리 무관
    r, dp = arc_geometry(tgt, [96.0, 0.0, 3.0], 9.0, dphi, 0.5)           # 전진 (z 무시)
    assert r == 48.0 and abs(r * dp - 9.0 * dphi) < 1e-12                  # 호 길이 보존
    assert arc_geometry(tgt, [12.0, 0.0, 0.0], 9.0, dphi, 0.5) == (9.0, dphi)  # R ≤ 18 → c5
