"""E10 (docs/146) 발사 게이트: 기본값 no-op + robust 게이트의 차단·통과 의미론."""
import numpy as np
import pytest

from shepherd.fs1.world import FS1Env, FS1Spec


def _run(spec, seed, r_fire=16.0):
    """직진 공격자 (residual 0) × 상시 arm 방어. tick 별 (16 m 안 LOADED, 발사, 포획술어, k) 기록."""
    env = FS1Env(spec, seed=0)
    np.random.seed(seed)
    obs, _ = env.reset(seed=seed)
    inn = env.inner
    hl = {l: np.array([0, 0, 0, 0.0], np.float32) for l in env.limiter_ids}
    hl["finisher_0"] = np.array([0, 0, 0, r_fire, 1.0], np.float32)
    ticks, sig, done, label = [], [obs["finisher_0"].copy()], False, None
    while not done:
        _, fin, att = inn._states()
        want = inn.fsm.state.value == "LOADED" and np.linalg.norm(inn._p(att) - inn._p(fin)) <= 16.0
        k0, w0 = inn.fsm.k, inn.fsm.wasted_fire
        obs, _, done, info = env.step({**hl, "adversary_0": np.zeros(3, np.float32)})
        fi = info["finisher_0"]
        ticks.append(dict(want=bool(want), fire=bool(fi.get("fire_event")), rob=bool(inn._pending_capture),
                          k_same=inn.fsm.k == k0, w_same=inn.fsm.wasted_fire == w0,
                          loaded=inn.fsm.state.value == "LOADED"))
        sig.append(obs["finisher_0"].copy())
        label = fi.get("m4_outcome") or label
    return ticks, label, np.concatenate(sig)


def test_default_is_off_and_bit_identical():
    assert FS1Spec().fire_gate == "off"
    assert not hasattr(FS1Env(FS1Spec(), seed=0).inner, "fire_gate_robust")
    a, b = _run(FS1Spec(), 1), _run(FS1Spec(fire_gate="off"), 1)
    np.testing.assert_array_equal(a[2], b[2])
    assert a[1] == b[1]


def test_invalid_gate_value_rejected():
    with pytest.raises(AssertionError):
        FS1Env(FS1Spec(fire_gate="soft"), seed=0)


@pytest.mark.parametrize("ts", [1.0, 0.5])
def test_robust_gate_blocks_then_fires_only_on_capture_predicate(ts):
    off, lab_off, _ = _run(FS1Spec(tau_scale=ts), 1)
    rob, lab_rob, _ = _run(FS1Spec(tau_scale=ts, fire_gate="robust"), 1)
    # 게이트 없음: 16 m 진입 첫 tick 에 보장 아닌 발사 → 탄 낭비 (이 테스트가 게이트를 구별하는 근거)
    f_off = [t for t in off if t["fire"]]
    assert len(f_off) == 1 and not f_off[0]["rob"] and lab_off == "PENETRATED"
    # 게이트: 막힌 요청은 탄·낭비·상태 무변화, 통과한 발사는 전부 포획 술어 참
    blocked = [t for t in rob if t["want"] and not t["fire"]]
    assert blocked and all(t["k_same"] and t["w_same"] and t["loaded"] for t in blocked)
    f_rob = [t for t in rob if t["fire"]]
    assert len(f_rob) == 1 and f_rob[0]["rob"] and lab_rob == "NET_CAPTURE"


# ---- 라벨 의미 (docs/146 §4, manifest verdict) ---------------------------------
def _M():
    import pathlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
    import fs1_e10_manifest as M
    return M


def _net(M, per_point):
    """per_point = 점별 seed 5 개 포획 수 (χ 내림차순 g0, g1, g2)."""
    return {p["name"]: dict(zip(M.SEEDS, v)) for p, v in zip(M.POINTS, per_point)}


def test_e10_label_semantics_opens_and_order():
    M = _M()
    net = _net(M, [[5, 8, 3, 6, 4], [20, 25, 18, 30, 22], [40, 35, 29, 10, 50]])
    v = M.verdict(net, net)
    assert v["P-E10a"]["verdict"] == "GATE_OPENS" and v["P-E10a"]["n_open"] == 4
    assert v["P-E10b"]["verdict"] == "ORDER_SUPPORTED"
    assert v["P-E10c"]["verdict"] == "BUDGET_CONVERGED"            # 1e7 == 3e7 → d 0


def test_e10_label_semantics_null_and_order_fail():
    M = _M()
    # 낮은 χ 에서 seed 2 개만 문턱 이상 → NULL (3 필요). 28 은 문턱 미달 (29 는 통과 — 경계)
    v = M.verdict(_net(M, [[5] * 5, [10] * 5, [29, 29, 28, 28, 0]]), _net(M, [[5] * 5, [10] * 5, [29, 29, 28, 28, 0]]))
    assert v["P-E10a"]["verdict"] == "GATE_NULL" and v["P-E10a"]["n_open"] == 2
    # 단조지만 양 끝 차 12 < 13 → 순서 미지지 / 13 이면 지지 (경계)
    assert M.verdict(_net(M, [[10] * 5, [15] * 5, [22] * 5]), _net(M, [[10] * 5, [15] * 5, [22] * 5]))["P-E10b"]["verdict"] == "ORDER_NOT_SUPPORTED"
    assert M.verdict(_net(M, [[10] * 5, [15] * 5, [23] * 5]), _net(M, [[10] * 5, [15] * 5, [23] * 5]))["P-E10b"]["verdict"] == "ORDER_SUPPORTED"
    # 가운데가 꺼지면 (비단조) 끝 차가 커도 미지지
    assert M.verdict(_net(M, [[10] * 5, [5] * 5, [60] * 5]), _net(M, [[10] * 5, [5] * 5, [60] * 5]))["P-E10b"]["verdict"] == "ORDER_NOT_SUPPORTED"
    # 열렸지만 순서는 미지지일 수 있다 (두 판정은 독립): 기준 그물도 높으면
    v = M.verdict(_net(M, [[50] * 5, [50] * 5, [55] * 5]), _net(M, [[50] * 5, [50] * 5, [55] * 5]))
    assert v["P-E10a"]["verdict"] == "GATE_OPENS" and v["P-E10b"]["verdict"] == "ORDER_NOT_SUPPORTED"


def test_e10_label_semantics_budget():
    M = _M()
    net3 = _net(M, [[5] * 5, [20] * 5, [40] * 5])
    up = {n: {s: x + 6 for s, x in d.items()} for n, d in net3.items()}      # 1e7 스냅샷이 전부 +6 → 예산 키우면 하락
    assert M.verdict(net3, up)["P-E10c"]["verdict"] == "BUDGET_UNDERTRAINED"
    near = {n: {s: x + 3 for s, x in d.items()} for n, d in net3.items()}    # |중앙값| 3 < 4
    assert M.verdict(net3, near)["P-E10c"]["verdict"] == "BUDGET_CONVERGED"
    down = {n: {s: x - 6 for s, x in d.items()} for n, d in net3.items()}    # 예산 키우면 상승 (반대 방향) → MIXED
    assert M.verdict(net3, down)["P-E10c"]["verdict"] == "BUDGET_MIXED"


def test_e10_points_exact_ticks_and_chi():
    M = _M()
    assert [p["deploy_ticks"] for p in M.POINTS] == [6, 4, 3]
    assert [p["chi"] for p in M.POINTS] == pytest.approx([0.52, 0.2311, 0.13], abs=5e-4)
    assert all(p["fire_gate"] == "robust" for p in M.POINTS)


def test_gate_ignores_r_fire_action():
    """게이트 아래에서는 r_fire 행동이 무효 (16 m 안에서 항상 요청) — BC 교사의 12 m 가 기준 그물을 깎지 않게.
    게이트 없음은 r_fire 를 그대로 따른다 (4 m: 13 m 대의 발사 없음)."""
    wide, lab_w, _ = _run(FS1Spec(fire_gate="robust"), 1, r_fire=16.0)
    tiny, lab_t, _ = _run(FS1Spec(fire_gate="robust"), 1, r_fire=4.0)
    assert [t["fire"] for t in wide] == [t["fire"] for t in tiny] and lab_w == lab_t == "NET_CAPTURE"
    off12, _, _ = _run(FS1Spec(), 1, r_fire=12.0)
    off16, _, _ = _run(FS1Spec(), 1, r_fire=16.0)
    first = lambda ts: next(i for i, t in enumerate(ts) if t["fire"])
    assert first(off12) > first(off16)                 # 게이트 없음: 발사 거리 행동이 발사 시점을 바꾼다
