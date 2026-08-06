"""P74–P77: `UnionTrace` — oracle 과 env 가 **같은 세계를 보는가** (docs/52 §8.0).

이 테스트가 통과하기 전에는 oracle 결과를 환경 결과로 부르지 않는다.
2026-08-06 에 실제로 밟은 함정이라 계약으로 박는다 -- 단계 2a 를 env 의
`n_segments=4` union 이 아니라 그 **prefix(Block 1)** 에서 돌려 놓고 환경
결과처럼 읽을 뻔했다.
"""
from __future__ import annotations

import numpy as np
import pytest

import shepherd.game.viability as V

TAU, A_ATT, KILL = 0.3, 44.0, 0.75
APEX, NF = np.array([2.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])
CONE, RMIN, RMAX = 0.2121, 0.0, 8.22


def _kw(limiters, *, n_segments=4, turn=False):
    return dict(tau=TAU, a_att_max=A_ATT, judge="se3_cone",
                net_center=None, net_radius=None, net_apex=APEX, n_F=NF,
                theta_net=CONE, range_min=RMIN, range_max=RMAX,
                limiters=limiters, kill_radius=KILL,
                attacker_turn_limited=turn, omega_att_max=(8.0 if turn else None),
                e_att=None, n=400, n_segments=n_segments, seed=0)


def _state(rng):
    return (rng.normal(scale=6.0, size=3) + np.array([10.0, 0.0, 0.0]),
            rng.normal(scale=8.0, size=3) + np.array([-20.0, 0.0, 0.0]))


# ── P74: 기본 호출이 비트 동일 ───────────────────────────────────────────────
@pytest.mark.parametrize("n_seg,turn", [(1, False), (4, False), (4, True)])
def test_p74_default_call_is_bit_identical(n_seg, turn):
    rng = np.random.default_rng(0)
    for _ in range(12):
        x, v = _state(rng)
        L = rng.normal(scale=5.0, size=(4, 3)) + np.array([8.0, 0.0, 0.0])
        for lim in (None, L):
            kw = _kw(lim, n_segments=n_seg, turn=turn)
            a = V._union_sets(x, v, **kw)
            b = V._union_sets(x, v, **kw, return_paths=True)
            assert len(a) == 3 and len(b) == 4
            for i in range(3):
                assert np.array_equal(a[i], b[i]), f"블록 {i} 불일치"


# ── P75: ★ 반환 path 로 feasible 을 재계산하면 원래와 같아야 한다 ────────────
def test_p75_recompute_feasible_from_returned_paths():
    """가장 강한 테스트 -- path 가 hit 판정에 쓰인 그 점인지."""
    rng = np.random.default_rng(1)
    checked = 0
    for _ in range(10):
        x, v = _state(rng)
        L = rng.normal(scale=4.0, size=(4, 3)) + np.array([8.0, 0.0, 0.0])
        _, feas, _, tr = V._union_sets(x, v, **_kw(L), return_paths=True)
        d = np.linalg.norm(tr.paths[:, :, None, :] - L[None, None, :, :], axis=3)
        hit = (d <= KILL).any(axis=(1, 2))
        assert np.array_equal(~hit, feas), "path 로 재계산한 feasible 이 다르다"
        checked += 1
    assert checked == 10


def test_p75b_padding_does_not_change_the_minimum():
    """패딩은 마지막 유효점 반복 -- 거리 최소화에 영향이 없어야 한다."""
    rng = np.random.default_rng(2)
    x, v = _state(rng)
    L = rng.normal(scale=4.0, size=(3, 3)) + np.array([8.0, 0.0, 0.0])
    _, _, _, tr = V._union_sets(x, v, **_kw(L), return_paths=True)
    for k in rng.choice(len(tr.paths), size=40, replace=False):
        n = int(tr.path_len[k])
        full = np.linalg.norm(tr.paths[k][:, None, :] - L[None, :, :], axis=2).min()
        real = np.linalg.norm(tr.paths[k][:n, None, :] - L[None, :, :], axis=2).min()
        assert full == pytest.approx(real)
        assert np.allclose(tr.paths[k][n - 1], tr.endpoints[k]), "종점 계약 위반"


# ── P76: Block 1 이 prefix 이고 legacy 와 동등 ──────────────────────────────
def test_p76_block1_is_the_legacy_single_segment_prefix():
    """union 의 Block 1 prefix 가 legacy 경로와 **표본별 비트 동일**함을 검증."""
    rng = np.random.default_rng(3)
    for _ in range(8):
        x, v = _state(rng)
        L = rng.normal(scale=5.0, size=(4, 3)) + np.array([8.0, 0.0, 0.0])
        ends, feas, caught, tr = V._union_sets(x, v, **_kw(L), return_paths=True)
        n1 = int((tr.block_id == 0).sum())
        assert (tr.block_id[:n1] == 0).all(), "Block 1 이 prefix 가 아니다"
        acc1 = V.reachable_accels(A_ATT, 400, 0)
        assert n1 == len(acc1)
        legacy = V._v_shot_with_accels(
            acc1, x, v, tau=TAU, judge="se3_cone", net_apex=APEX, n_F=NF,
            theta_net=CONE, range_min=RMIN, range_max=RMAX, limiters=L,
            kill_radius=KILL)
        f1 = V._feasible_limiter(x, v, acc1, TAU, L, KILL)
        assert np.array_equal(feas[:n1], f1)
        e1 = x[None, :] + v[None, :] * TAU + 0.5 * acc1 * TAU ** 2
        assert np.allclose(ends[:n1], e1)
        # (보조) prefix 가 붙어 있으므로 거의 자명하다. superset 성질의 핵심
        # 증명이 아니라 sanity check 다 -- 진짜 계약은 위의 표본별 비트 동일이다.
        assert feas.sum() >= f1.sum()
        assert legacy.n_total == n1


# ── P77: 경계·극단 사례에서 v_shot 이 trace 와 일치 ─────────────────────────
def test_p77_boxed_and_clean_cases_agree():
    rng = np.random.default_rng(4)
    seen = {"boxed": 0, "clean": 0, "mixed": 0}
    for _ in range(60):
        x, v = _state(rng)
        L = rng.normal(scale=3.0, size=(4, 3)) + x[None, :]   # 공격자 근처 -> boxed 유도
        kw = _kw(L)
        ends, feas, caught, tr = V._union_sets(x, v, **kw, return_paths=True)
        r = V._assemble(feas, caught, len(feas), "se3_cone", 0)
        if r.boxed_in:
            assert feas.sum() == 0
            seen["boxed"] += 1
        else:
            fc = caught[feas]
            assert r.v_shot_soft == pytest.approx(float(fc.mean()))
            assert r.v_shot_worst == (1.0 if fc.all() else 0.0)
            seen["clean" if fc.all() else "mixed"] += 1
    assert seen["boxed"] > 0 and (seen["mixed"] + seen["clean"]) > 0


def test_p77b_exact_kill_radius_boundary_uses_le():
    """`<=` 규약 -- 정확히 kill_radius 면 **제거**된다.

    ★ 판정은 `s = linspace(0, tau, 24)` 격자 위에서만 이뤄진다. 격자 밖 점을
    기준으로 시험하면 실패한다 (2026-08-06 실제로 밟음). 여기서는 **격자점**을
    쓴다 -- 이 사실 자체가 계약이므로 테스트로 박아 둔다.
    """
    x = np.array([10.0, 0.0, 0.0]); v = np.array([-20.0, 0.0, 0.0])
    acc = np.zeros((1, 3))
    s_grid = np.linspace(0.0, TAU, 24)
    on = x + v * s_grid[11]                       # 격자 위의 점
    for eps, want_feasible in ((-1e-9, False), (0.0, False), (+1e-6, True)):
        L = np.array([on + np.array([0.0, KILL + eps, 0.0])])
        f = V._feasible_limiter(x, v, acc, TAU, L, KILL)
        assert bool(f[0]) is want_feasible, (eps, f)


def test_p77c_discretization_error_is_bounded_not_zero():
    """★ 24 점 격자는 연속시간 접촉을 **보장하지 않는다.** 상계만 있다.

    2026-08-06 정정: 처음에 "격자 간격 절반 < kill_radius 이므로 위음성이
    구조적으로 없다" 고 적었는데 **틀렸다.** 연속 경로가 구를 얕게 스치면
    양옆 격자점이 모두 반경 밖일 수 있다. 보장되는 것은

        d_continuous_min  >=  d_sampled_min − δ,      δ = 인접 표본 최대 이동량/2

    뿐이다. 즉 `d_sampled_min > kill_radius + δ` 일 때만 연속시간 미접촉을
    단언할 수 있고, 살짝 넘는 구간은 위음성이 가능하다.

    **환경 계약은 어차피 격자점 판정**이므로 env-faithful 2a 에는 영향이 없다
    (docs/52 §5.3 -- 환경 술어와 물리 감사 술어의 분리).
    """
    x = np.array([10.0, 0.0, 0.0]); v = np.array([-26.0, 0.0, 0.0])
    s_grid = np.linspace(0.0, TAU, 24)
    delta = float(np.linalg.norm(v) * (s_grid[1] - s_grid[0])) / 2.0
    acc = np.zeros((1, 3))

    # (a) 격자 **사이**에 정확히 놓으면 이 경우엔 잡힌다 (delta < KILL 이므로)
    mid = x + v * (0.5 * (s_grid[11] + s_grid[12]))
    assert not bool(V._feasible_limiter(x, v, acc, TAU, np.array([mid]), KILL)[0])

    # (b) ★ 그러나 얕게 스치면 놓친다 -- 위음성이 **실재**함을 박아 둔다
    off = np.array([0.0, np.sqrt(max(KILL**2 - (delta * 0.98)**2, 0.0)) + 1e-3, 0.0])
    graze = x + v * (0.5 * (s_grid[11] + s_grid[12])) + off
    miss = bool(V._feasible_limiter(x, v, acc, TAU, np.array([graze]), KILL)[0])
    seg = x[None, :] + v[None, :] * np.linspace(s_grid[11], s_grid[12], 200)[:, None]
    cont = float(np.linalg.norm(seg - graze, axis=1).min())
    assert cont <= KILL and miss, ("연속으로는 닿는데 격자로는 놓치는 사례가 "
                                   "재현되지 않았다", cont, miss)

    # (c) 상계: 격자 최소거리가 KILL + delta 를 넘으면 연속시간에서도 미접촉
    far = x + v * s_grid[11] + np.array([0.0, KILL + delta + 0.05, 0.0])
    assert bool(V._feasible_limiter(x, v, acc, TAU, np.array([far]), KILL)[0])
