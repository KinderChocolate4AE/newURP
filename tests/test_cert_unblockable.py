"""게이트 6 soundness unit tests (docs/77 [D] — "soundness unit test 필수").

핵심 성질: v_max = G/(G+U) 는 admissible 배치 전체에 대한 **sound upper bound** —
어떤 배치도 v_max 를 초과하는 v_shot_soft 를 만들 수 없고(=false negative 불가),
U > 0 이면 boxed_in 도 불가능하다.
"""
import numpy as np
import pytest

from shepherd.scripts.cert_unblockable import unblockable_mass

R_KILL, R_NK = 0.75, 6.0
ASSET = np.zeros(3)


def _mass(paths, caught, tf=None):
    tf = np.ones(len(caught), bool) if tf is None else tf
    return unblockable_mass([paths], caught, tf,
                            asset=ASSET, r_nk=R_NK, r_kill=R_KILL)


def _path(*pts):
    return np.asarray(pts, float)[None, :, :]          # (1, T, 3)


def test_deep_inside_nk_is_unblockable():
    # 경로 전체가 자산에서 r_nk - r_kill 이내 -> tube ⊆ NK ball -> unblockable
    p = _path([0, 0, 1], [0, 0, 2], [0, 0, 5.24])
    m = _mass(p, caught=np.array([False]))
    assert m["U"] == 1 and m["G"] == 0 and m["v_max"] == 0.0
    assert not m["boxed_possible"]
    # 기하 검증: NK 밖 어떤 center 도 이 경로를 r_kill 안에 못 잡는다
    rng = np.random.default_rng(0)
    d = rng.normal(size=(2000, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    centers = d * (R_NK + rng.uniform(0, 3, size=(2000, 1)))    # 전부 NK 밖
    dist = np.linalg.norm(centers[:, None, :] - p[0][None, :, :], axis=2).min(axis=1)
    assert (dist > R_KILL).all()


def test_outside_nk_is_blockable():
    # NK 밖 경로 -> U=0. 단 G=0 이므로 상한은 0 (caught 가 없으면 clean shot 불가).
    p = _path([10, 0, 1], [12, 0, 1], [15, 0, 1])
    m = _mass(p, caught=np.array([False]))
    assert m["U"] == 0 and m["v_max"] == 0.0
    # 같은 경로라도 caught good 이 함께 있으면 U=0 -> 상한 1.0 (제거 낙관)
    p2 = np.concatenate([p, p], axis=0)
    m2 = _mass(p2, caught=np.array([False, True]))
    assert m2["U"] == 0 and m2["v_max"] == 1.0


def test_zero_caught_bounds_every_placement_at_zero():
    """G=0 이면 어떤 not-boxed 배치도 v=0 — 상한 0 의 soundness 직접 검증."""
    rng = np.random.default_rng(3)
    paths = rng.uniform(-20, 20, size=(30, 4, 3))
    caught = np.zeros(30, bool)
    m = _mass(paths, caught)
    assert m["v_max"] == 0.0
    for _ in range(50):
        d = rng.normal(size=(3, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        centers = d * (R_NK + rng.uniform(0.0, 15.0, size=(3, 1)))
        dist = np.linalg.norm(paths[:, :, None, :] - centers[None, None, :, :],
                              axis=3).min(axis=(1, 2))
        feasible = dist > R_KILL
        if feasible.sum() == 0:
            continue                                        # boxed -> g 제외 대상
        assert float(caught[feasible].mean()) == 0.0


def test_boundary_case_counts_as_blockable():
    # max|p - asset| = r_nk - r_kill 정확히 -> tube 가 NK 경계에 접함 (<= 이므로 U 에 포함)
    p = _path([R_NK - R_KILL, 0, 0])
    m = _mass(p, caught=np.array([False]))
    assert m["U"] == 1                                  # 선언된 부등호 (<=) 그대로


def test_caught_witness_never_counts_toward_U():
    p = _path([0, 0, 1])                                # NK 깊숙이, 그러나 caught
    m = _mass(p, caught=np.array([True]))
    assert m["U"] == 0 and m["G"] == 1 and m["v_max"] == 1.0


def test_turn_infeasible_excluded():
    p = _path([0, 0, 1])
    m = _mass(p, caught=np.array([False]), tf=np.array([False]))
    assert m["U"] == 0 and m["G"] == 0 and m["B"] == 0


def test_vmax_upper_bounds_every_admissible_placement():
    """무작위 witness 집합 + 무작위 admissible 배치 전수 대조: v <= v_max."""
    rng = np.random.default_rng(1)
    n_wit = 60
    # 절반은 NK 안 깊숙이(잠재 unblockable), 절반은 밖
    inner = rng.uniform(-3, 3, size=(n_wit // 2, 4, 3))
    outer = rng.uniform(7, 20, size=(n_wit - n_wit // 2, 4, 3))
    paths = np.concatenate([inner, outer], axis=0)      # (n_wit, 4, 3)
    caught = rng.random(n_wit) < 0.4
    m = _mass(paths, caught)
    assert m["U"] > 0, "테스트 전제: unblockable witness 가 실제로 존재해야 함"

    for trial in range(200):
        k = rng.integers(1, 5)
        d = rng.normal(size=(k, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        centers = d * (R_NK + rng.uniform(0.0, 10.0, size=(k, 1)))   # admissible (NK 밖)
        dist = np.linalg.norm(paths[:, :, None, :] - centers[None, None, :, :],
                              axis=3).min(axis=(1, 2))
        feasible = dist > R_KILL
        nf = int(feasible.sum())
        assert nf > 0, "U>0 이면 boxed 불가"
        v = float(caught[feasible].mean())
        assert v <= m["v_max"] + 1e-12, f"trial {trial}: v={v} > v_max={m['v_max']}"


def test_screen_zero_guarantees_below_theta():
    """screen=0 (v_max < theta) 이면 어떤 admissible 배치도 theta 미달 (C_N=0 보장)."""
    rng = np.random.default_rng(2)
    # good 1 : unblockable bad 9 -> v_max = 0.1 < 0.9
    paths = rng.uniform(-2.5, 2.5, size=(10, 3, 3))
    caught = np.zeros(10, bool)
    caught[0] = True
    m = _mass(paths, caught)
    assert m["U"] == 9 and m["v_max"] == pytest.approx(0.1)
    theta = 0.9
    assert m["v_max"] < theta                            # screen = 0
    for _ in range(100):
        d = rng.normal(size=(4, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
        centers = d * (R_NK + rng.uniform(0.0, 5.0, size=(4, 1)))
        dist = np.linalg.norm(paths[:, :, None, :] - centers[None, None, :, :],
                              axis=3).min(axis=(1, 2))
        feasible = dist > R_KILL
        assert feasible.sum() > 0
        assert float(caught[feasible].mean()) < theta
