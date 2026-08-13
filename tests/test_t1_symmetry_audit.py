"""T1 세계의 x축 회전 대칭 감사 (docs/83 §31). **결과를 보지 않고** 하는 정적 계약 감사.

질문: defender ring 을 x 축 둘레로 R_x(phi) 회전했을 때
      F(R_x s, R_x a) == R_x F(s, a) 인가?

만족하면 phi_0 randomization (T1-R) 은 새로운 물리 조건이 아니라 **좌표계 relabeling**
이고 robustness 증거가 되지 않는다.

이 테스트는 현 세계의 **대칭군을 문서화**한다. 값이 바뀌면 T1-R 판정도 다시 해야 하므로
회귀로 고정한다.

    python -m pytest tests/test_t1_symmetry_audit.py -q

torch-free.
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import (AttackerSpec, _jink_accel, _route_accel,
                                             _unit)
from shepherd.scripts.mission_rollout import intercept_lead_time

TOL = 1e-9
PHIS = (0.3, 0.7854, 1.1, 2.0)
SPEC = AttackerSpec(level="A2", jink_amp=0.6, seed=0, route_gain=0.5, sense_range=30.0)


def Rx(phi: float) -> np.ndarray:
    c, s = np.cos(phi), np.sin(phi)
    return np.array([[1.0, 0, 0], [0, c, -s], [0, s, c]])


def _states(rng, n):
    for _ in range(n):
        p = rng.normal(0, 8, 3); p[0] = abs(p[0]) + 6.0
        v = rng.normal(0, 10, 3); v[0] = -abs(v[0]) - 8.0
        lims = rng.normal(0, 5, (4, 3)) + np.array([8.0, 0, 0])
        yield p, v, lims


# --- 정확히 공변인 축 --------------------------------------------------------
def test_pip_lead_time_is_equivariant():
    """limiter PIP 는 상대벡터 노름만 쓰므로 정확히 회전 공변."""
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(300):
        rel, v = rng.normal(0, 10, 3), rng.normal(0, 12, 3)
        for phi in PHIS:
            R = Rx(phi)
            a, b = intercept_lead_time(rel, v, 14.0), intercept_lead_time(R @ rel, R @ v, 14.0)
            assert (a is None) == (b is None)
            if a is not None:
                worst = max(worst, abs(a - b))
    assert worst < 1e-9, worst


def test_sense_predicate_is_equivariant():
    """감지는 3D 유클리드 거리 (수평 range 아님) -> 정확히 공변."""
    rng = np.random.default_rng(12)
    worst = 0.0
    for _ in range(300):
        p, c = rng.normal(0, 15, 3), rng.normal(0, 15, 3)
        for phi in PHIS:
            R = Rx(phi)
            worst = max(worst, abs(float(np.linalg.norm(c - p))
                                   - float(np.linalg.norm(R @ c - R @ p))))
    assert worst < 1e-9, worst


def test_dynamics_clamps_are_isotropic():
    """가속/속도 제한이 **노름 클램프**이고 중력·바닥·z 제약이 없음을 고정."""
    import inspect

    from shepherd.sim import analytic
    src = inspect.getsource(analytic)
    assert "a.limits.a_max / an" in src and "a.limits.v_max / sp" in src
    for banned in ("gravity", "9.81", "z_min", "altitude"):
        assert banned not in src, f"등방성 가정을 깨는 항 발견: {banned}"


# --- 점별로는 공변이 아니지만 **게이지**인 축 --------------------------------
def test_jink_is_pointwise_nonequivariant_but_gauge():
    """jink 는 점별 비공변 (basis 가 월드 z 에 고정) 이지만 **분포**는 회전 불변.

    `u = unit(fwd x z_hat)` 는 횡평면의 **임의 basis 선택**이고, 위상
    `psi ~ U[0, 2pi)` 가 균일하므로 jink 방향의 분포는 횡평면에서 균일하다.
    따라서 점별 위반은 gauge artifact 이지 물리적 비등방성이 아니다.
    """
    rng = np.random.default_rng(13)
    n_viol = 0
    n_tot = 0
    for p, v, lims in _states(rng, 100):
        fwd = _unit(v)
        kw = dict(a_lat_max=30.0, d_target=float(np.linalg.norm(p)), committed=False)
        for phi in PHIS:
            R = Rx(phi)
            a0 = _jink_accel(SPEC, fwd=fwd, t=0.35, phase=1.234, **kw)
            a1 = _jink_accel(SPEC, fwd=R @ fwd, t=0.35, phase=1.234, **kw)
            n_tot += 1
            if np.linalg.norm(a1 - R @ a0) > TOL:
                n_viol += 1
    # 점별로는 사실상 전부 깨진다 -- 이게 gauge 라는 증거 (§31.2)
    assert n_viol == n_tot, f"{n_viol}/{n_tot} — 점별 비공변성이 사라졌다면 §31 재검토"

    # 게이지임을 보이는 축: 위상 보정으로 정확히 되돌아오는가.
    # fwd = -x_hat 이면 basis 는 (u, w) = (y_hat, -z_hat) 이므로
    #     R_x(phi) d(ang) = d(ang - phi)
    # 즉 위상을 **-phi** 만큼 옮기면 정확히 복원된다. psi ~ U[0,2pi) 가 균일하므로
    # 이 이동은 분포를 바꾸지 않는다 -> 점별 위반은 gauge 다.
    fwd = np.array([-1.0, 0.0, 0.0])
    kw = dict(a_lat_max=30.0, d_target=20.0, committed=False)
    worst = 0.0
    for phi in PHIS:
        R = Rx(phi)
        a0 = _jink_accel(SPEC, fwd=fwd, t=0.35, phase=1.234, **kw)
        a1 = _jink_accel(SPEC, fwd=R @ fwd, t=0.35, phase=1.234 - phi, **kw)
        worst = max(worst, float(np.linalg.norm(a1 - R @ a0)))
    assert worst < 1e-9, f"위상 보정으로 복원되지 않는다 ({worst:.2e}) — gauge 가 아니다"


def test_spawn_lateral_offset_distribution_is_x_rotation_invariant():
    """스폰 계약이 R_x 불변 분포임을 고정: azimuth=0 · psi=0 · 횡오프셋 = y-z 균일 원반."""
    from shepherd.spawn_rand import SpawnSpec
    s = SpawnSpec()
    assert s.azimuth == 0.0, "접근 방위 섹터가 열리면 R_x 불변성 논증이 무효"
    assert s.psi == 0.0, "초기 속도 각오차가 열리면 재검토"
    assert s.r_lat > 0.0, "횡오프셋이 없으면 논증 불필요"


# --- 진짜 (그러나 측도-희소한) 비등방성 -------------------------------------
def test_route_tiebreak_is_the_only_real_x_anisotropy():
    """route 응답은 `세계 +z 선호` tie-break 에서만 비공변. 발생률이 희소함을 고정.

    코드 주석이 명시하듯 이 tie-break 는 **z-회전** 불변성을 위해 고른 것이다
    (attacker_ladder.py `_key`). T1-R 이 노리는 x-회전에서는 불변이 아니다.
    """
    rng = np.random.default_rng(7)
    n_viol = n_tot = 0
    for p, v, lims in _states(rng, 200):
        fwd = _unit(v)
        kw = dict(a_lat_max=30.0, d_target=float(np.linalg.norm(p)))
        for phi in PHIS:
            R = Rx(phi)
            a0 = _route_accel(SPEC, p_att=p, v_att=v, fwd=fwd, limiters=lims,
                              kill_radius=0.75, repel_margin=1.0, **kw)
            a1 = _route_accel(SPEC, p_att=R @ p, v_att=R @ v, fwd=R @ fwd,
                              limiters=(R @ lims.T).T, kill_radius=0.75,
                              repel_margin=1.0, **kw)
            n_tot += 1
            if np.linalg.norm(a1 - R @ a0) > TOL:
                n_viol += 1
    frac = n_viol / n_tot
    # 관측 1/800. 상한을 넉넉히 두되 "희소" 를 계약으로 고정한다.
    assert frac < 0.02, f"route 비공변 비율 {frac:.4f} — 더 이상 희소하지 않다. §31 재검토"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
