"""P69–P73: 포획기 이동성 배선 (docs/51 §5.1).

가장 중요한 것은 **P69** 다. 기본값(`a_max = 0`)에서 이 배선이 생기기 전과
비트 동일해야, 지금까지 난 25 런과 기저선이 그대로 유효하다. 그리고 **P70b** --
이동성은 세 곳(명령·백엔드 가속·백엔드 속도)에 걸려 있고, 하나만 풀면 조용히
목이 졸린다. 2026-08-05 에 실제로 밟은 함정이라 테스트로 박아 둔다.
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.agents.mobile_finisher import (MOBILE_A_MAX, MOBILE_V_MAX,
                                             apply_mobility,
                                             mobile_finisher_accel)
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env, mission_eval
from shepherd.scripts.mission_rollout import scripted_role_actions
from shepherd.spawn_rand import SpawnSpec

KW = dict(system=SystemSpec(), reward=RewardSpec(w_kill=0.5, enabled=True),
          attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
          spawn=SpawnSpec())


def _roll(mobile: bool, seed: int = 0, steps: int = 120):
    st = build_m4_env(0, seed, **KW)
    env, scn, lay = st.env, st.scn, st.lay
    if mobile:
        apply_mobility(env)
    env.reset(seed=seed)
    fid = env.finisher_id
    p0 = env._p(env._states()[1]).copy()
    trail, accels = [p0.copy()], []
    for _ in range(min(steps, int(lay.episode_len))):
        pre = env._states()
        a_cmd = mobile_finisher_accel(
            env._p(pre[1]), env._v(pre[1]), env._p(pre[2]), env._v(pre[2]),
            tau=env.tau_deploy, a_max=getattr(env.sc.finisher, "a_max", 0.0))
        accels.append(float(np.linalg.norm(a_cmd)))
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="clean")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        trail.append(env._p(env._states()[1]).copy())
        if (term and term.get(fid)) or (trunc and trunc.get(fid)):
            break
    return np.array(trail), np.array(accels)


# ── P69: 기본값은 고정. 이 배선 이전과 동일 ─────────────────────────────────
def test_p69_default_is_a_stationary_finisher():
    from shepherd.game.roles import FinisherSpec
    assert FinisherSpec.a_max == 0.0, "기본값이 0 이 아니면 기존 결과가 전부 흔들린다"
    st = build_m4_env(0, 0, **KW)
    assert st.env.sc.finisher.a_max == 0.0
    trail, acc = _roll(mobile=False)
    assert np.allclose(trail, trail[0]), "고정인데 움직였다"
    assert np.all(acc == 0.0), "고정인데 병진 명령이 0 이 아니다"


def test_p69b_mission_eval_default_is_bit_identical():
    """`mobility` 인자가 생기기 전 호출과 같은 결과여야 한다."""
    a = mission_eval(0, 12, limiter_mode="hold", **KW)
    b = mission_eval(0, 12, limiter_mode="hold", mobility=0.0, **KW)
    assert a == b


# ── P70: 켜면 실제로 움직이고 상한을 지킨다 ─────────────────────────────────
def test_p70_mobility_actually_moves_and_respects_a_max():
    trail, acc = _roll(mobile=True)
    disp = float(np.linalg.norm(trail[-1] - trail[0]))
    assert disp > 0.5, f"이동을 켰는데 거의 안 움직였다 ({disp:.4f})"
    assert acc.max() <= MOBILE_A_MAX + 1e-6, f"가속 상한 위반 {acc.max()}"
    # 방향 보존: 상한에 걸린 스텝은 정확히 a_max 여야 한다 (성분별 클립이 아님)
    at_cap = acc[acc > MOBILE_A_MAX - 1e-6]
    assert np.allclose(at_cap, MOBILE_A_MAX, atol=1e-6)


def test_p70b_backend_clamps_are_released_together():
    """★ 이동성은 세 곳에 걸려 있다 -- 하나만 풀면 조용히 목이 졸린다.

    2026-08-05: `env.py` 의 병진 명령만 풀고 돌렸더니 60 스텝에 0.40 밖에 못
    움직였다. 백엔드가 `KinematicLimits(1.0, 1.0, ...)` 로 따로 묶고 있었다.
    """
    st = build_m4_env(0, 0, **KW)
    env = st.env
    fin = [a for a in env.backend.agents if a.role == "finisher"][0]
    assert fin.limits.a_max < MOBILE_A_MAX, "전제가 바뀌었다 (백엔드 기본이 이미 큼)"

    info = apply_mobility(env)
    assert env.sc.finisher.a_max == pytest.approx(MOBILE_A_MAX)      # 명령
    assert fin.limits.a_max >= MOBILE_A_MAX                          # 백엔드 가속
    assert fin.limits.v_max >= MOBILE_V_MAX                          # 백엔드 속도
    assert info["backend_a_max"] >= info["a_max"]

    # 명령만 풀고 백엔드를 안 풀면 실제로 목이 졸린다 -- 그 사실 자체를 박아 둔다
    st2 = build_m4_env(0, 0, **KW)
    st2.env.sc.__dict__["finisher"] = dataclasses.replace(
        st2.env.sc.finisher, a_max=MOBILE_A_MAX)          # 명령만
    st2.env.reset(seed=0)
    p0 = st2.env._p(st2.env._states()[1]).copy()
    for _ in range(60):
        acts = scripted_role_actions(st2.env, st2.scn, st2.lay,
                                     limiter_mode="hold", fire_mode="clean")
        acts[st2.env.adversary_id] = np.zeros(3, np.float32)
        st2.env.step(acts)
    throttled = float(np.linalg.norm(st2.env._p(st2.env._states()[1]) - p0))
    full, _ = _roll(mobile=True, steps=60)
    assert throttled < float(np.linalg.norm(full[-1] - full[0])) / 2.0, \
        "백엔드 클램프가 실제로는 안 물리고 있다 -- 이 테스트의 전제가 깨졌다"


# ── P71: 특권 정보 없음 ─────────────────────────────────────────────────────
def test_p71_controller_uses_only_observable_quantities():
    """제어기 입력(p_fin, v_fin, p_att, v_att)이 전부 관측 벡터에 있다."""
    st = build_m4_env(0, 0, **KW)
    env = st.env
    obs, _ = env.reset(seed=0)
    o = np.asarray(obs[env.finisher_id], float)
    lims, fin, att = env._states()
    for name, want in (("p_fin", env._p(fin)), ("v_fin", env._v(fin)),
                       ("p_att", env._p(att)), ("v_att", env._v(att))):
        hit = any(np.allclose(o[i:i + 3], want, atol=1e-5)
                  for i in range(len(o) - 2))
        assert hit, f"{name} 가 관측에 없다 -> 특권 정보다"


def test_p71b_controller_is_a_pure_function():
    """같은 입력 -> 같은 출력. 내부 상태가 없다."""
    rng = np.random.default_rng(0)
    for _ in range(20):
        args = [rng.normal(size=3) for _ in range(4)]
        a = mobile_finisher_accel(*args, tau=0.3, a_max=MOBILE_A_MAX)
        b = mobile_finisher_accel(*args, tau=0.3, a_max=MOBILE_A_MAX)
        assert np.array_equal(a, b)
    z = mobile_finisher_accel(*[rng.normal(size=3) for _ in range(4)],
                              tau=0.3, a_max=0.0)
    assert np.array_equal(z, np.zeros(3, np.float32))


# ── P72/P73: 회귀 방어와 paired CRN ─────────────────────────────────────────
def test_p72_fixed_cell_matches_the_existing_baseline_path():
    """셀 1 은 기존 `hold` 기저선과 **같은 구성**이다 (docs/51 §4 회귀 검사)."""
    from shepherd.scripts.mobility_factorial import run_cell
    from shepherd.scripts.sweep_m4 import measure_baseline

    cell = run_cell(24, 0, mobility=0.0)["summary"]
    base = measure_baseline(24, 0, mode="hold")
    assert cell["neutralized_rate"] == base["neutralized_rate"]
    assert cell["counts"] == base["counts"]
    for reg, v in base["by_regime"].items():
        assert cell["by_regime"][reg]["n"] == v["n"]


def test_p73_cells_are_paired_on_the_same_initial_conditions():
    """네 칸이 같은 (seed0, ep) 초기조건을 본다 -- 짝을 지을 수 있어야 한다."""
    from shepherd.scripts.mobility_factorial import paired_compare, run_cell

    fixed = run_cell(24, 0, mobility=0.0)
    mobile = run_cell(24, 0, mobility=MOBILE_A_MAX)
    fr = {d["episode"]: d for d in fixed["records"]}
    mr = {d["episode"]: d for d in mobile["records"]}
    assert set(fr) == set(mr)
    for e in fr:                     # 초기조건은 이동성과 무관해야 한다
        for k in ("regime", "a_att", "att_speed", "net_radius", "tau"):
            assert fr[e][k] == mr[e][k], f"ep{e} 의 {k} 가 다르다 -> paired 아님"
    p = paired_compare(fixed, mobile, regime=None)
    assert p["n_paired"] == 24
    assert 0.0 <= p["R_move"] <= 1.0


def test_p73b_success_labels_exist_and_agree_with_the_summary():
    """라벨 오타가 조용한 0 이 되는 것을 막는다 (2026-08-05 실제 사고)."""
    from shepherd.scripts.mission_rollout import LABELS
    from shepherd.scripts.mobility_factorial import (DESTRUCTIVE, SUCCESS,
                                                     run_cell)
    assert set(SUCCESS) | set(DESTRUCTIVE) <= set(LABELS)
    c = run_cell(24, 0, mobility=0.0)          # run_cell 이 자기 점검을 한다
    assert c["k_nondestructive"] == sum(
        1 for d in c["records"] if d["label"] in SUCCESS)
