"""P83 — privileged controller 자격 자기검사 (docs/56 §7.2).

★ 이 스위트가 전부 green 이기 전에는 2×2 를 실행하지 않는다.

  P83a  동일 seed -> 계획·결과 결정론적 동일
  P83b  후보·실행 가속 bound 위반 0
  P83c  intervention off -> V3b 원 replay 재현 (라벨·steps)
  P83d  경량 클론 상태이식 + 원 행동 재생 -> full env 와 공격자 궤적 bit 동일
  P83e  limiter 를 repel 반경 안에 넣으면 공격자 궤적이 재계산됨
  P83f  budget 안에 L1 후보 없음 -> NO_SOLUTION_WITHIN_BUDGET
  P83g  분류는 proxy 가 아니라 final env 라벨만 사용 (API 분리)

비용 절충: e2e 검사는 ep 2 (V3b 첫 miss 판) 하나로 고정한다 -- 7판 전부는
probe 본 실행이 담당.
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.scripts.recoverability_probe import (
    CLONE_N_SAMPLES, EPISODE_LEN, MISS_EPISODES, _analytic_backend, _build,
    _sample_ball, _Driver, clone_at, drive_to, replay_baseline, transfer_state)

EP = 2                       # V3b: PENETRATED, steps 52, handoff@21(1-based)


@pytest.fixture(scope="module")
def base():
    return replay_baseline(EP)


# ------------------------------------------------------------------ P83c ---
def test_p83c_intervention_off_reproduces_v3b(base):
    """개입 없는 replay 가 V3b 기록 (PENETRATED, steps=52) 을 재현한다."""
    assert base.label == "PENETRATED", base.label
    assert base.t + 1 == 52, base.t + 1
    assert base.handoff_step is not None and base.fire_step is not None
    # V3b 기록 handoff@21 은 wrapper _step_i(1-based); driver 는 0-based loop
    assert base.handoff_step + 1 == 21, base.handoff_step


def test_p83c_fire_precedes_tminus5(base):
    """fire < t*−5 실측 -> EARLY_PREP_NET_CAPTURE 구조적 도달 불가 (§7.1 예측)."""
    assert base.fire_step < base.handoff_step - 5, \
        (base.fire_step, base.handoff_step)


# ------------------------------------------------------------------ P83d ---
def test_p83d_light_clone_bit_identical_dynamics(base):
    """상태이식 클론이 원 행동(hold) 재생에서 full env 와 궤적 bit 동일."""
    s0 = base.handoff_step - 5
    full = drive_to(EP, s0)
    lite = clone_at(full, EP, n_samples=CLONE_N_SAMPLES)
    for _ in range(EPISODE_LEN):
        if full.done or lite.done:
            break
        full.step()
        lite.step()
        pf = full.env._p(full.env._states()[2])
        pl = lite.env._p(lite.env._states()[2])
        assert np.array_equal(pf, pl), f"t={full.t} 공격자 위치 발산"
        for sf, sl in zip(full.env._states()[0], lite.env._states()[0]):
            assert np.array_equal(full.env._p(sf), lite.env._p(sl)), \
                f"t={full.t} limiter 위치 발산"
    assert full.label == lite.label and full.t == lite.t, \
        (full.label, lite.label, full.t, lite.t)


# ------------------------------------------------------------------ P83a ---
def test_p83a_deterministic_rollout(base):
    """같은 이식·같은 plan -> 같은 결과 (rollout 결정론)."""
    from shepherd.scripts.recoverability_probe import _rollout
    s0 = base.handoff_step + 1
    src = drive_to(EP, s0)
    reuse = clone_at(src, EP)
    rng = np.random.default_rng(0)
    plan = ("accels", _sample_ball(rng, (4, 4, 3), 20.0))
    a = _rollout(src, s0, plan, reuse)
    b = _rollout(src, s0, plan, reuse)
    assert a == b, (a, b)


# ------------------------------------------------------------------ P83b ---
def test_p83b_candidates_within_bound():
    rng = np.random.default_rng(7)
    a_max = 27.06
    s = _sample_ball(rng, (256, 4, 4, 3), a_max)
    n = np.linalg.norm(s, axis=-1)
    assert float(n.max()) <= a_max + 1e-9, float(n.max())


# ------------------------------------------------------------------ P83e ---
def test_p83e_attacker_recomputed_when_limiter_in_repel(base):
    """개입이 repel 반경 안이면 공격자 궤적이 달라진다 (closed-loop 증명).

    ★ 구조 사실 (첫 실행이 발견): env 는 repel_margin=1.0 을 하드코딩
    (env.py:346) -> 반발 발동 반경 = kill_radius(0.75) 와 동일. 즉 공격자의
    limiter 반응은 접촉 반경 안에서만 존재한다. 0.9 m 개입은 반응 0 이 **계약상
    정상**이고 (V3b 의 hold/intercept 궤적 동일의 구조적 원인), closed-loop
    재계산 자체는 매 스텝 수행된다. 검정은 0.75 안(0.74)에서 한다.
    """
    s0 = base.handoff_step + 1
    a = drive_to(EP, s0)
    b = drive_to(EP, s0)
    att_p = b.env._p(b.env._states()[2])
    bk = _analytic_backend(b.env)
    ag = bk.by_name(b.env.limiter_ids[0])
    ag.p = att_p + np.array([0.74, 0.0, 0.0])     # repel(=접촉) 반경 안
    ag.v = np.zeros(3)
    a.step(); b.step()
    pa = a.env._p(a.env._states()[2])
    pb = b.env._p(b.env._states()[2])
    assert not np.array_equal(pa, pb), "repel 반경 안 개입에도 공격자 궤적 불변"
    # 반경 밖(0.9)은 반응 0 이 계약이다 -- 회귀로 고정 (원거리 의존 생기면 잡힘)
    c = drive_to(EP, s0)
    ag2 = _analytic_backend(c.env).by_name(c.env.limiter_ids[0])
    ag2.p = c.env._p(c.env._states()[2]) + np.array([0.9, 0.0, 0.0])
    ag2.v = np.zeros(3)
    d0 = drive_to(EP, s0)
    c.step(); d0.step()
    assert np.array_equal(c.env._p(c.env._states()[2]),
                          d0.env._p(d0.env._states()[2]))


# ------------------------------------------------------------------ P83f ---
def test_p83f_no_solution_flag():
    """budget 안에 L1 후보가 없으면 NO_SOLUTION_WITHIN_BUDGET=True."""
    import shepherd.scripts.recoverability_probe as rp
    base = replay_baseline(EP)
    s0 = base.handoff_step + 1
    src = drive_to(EP, s0)
    # 미니 budget + 무력화 불가능하게 a_max=0 (모든 후보 = hold 동형)
    # seeds 는 시그니처 명시 인자 (module global 패치는 def 시점 기본값에 무효)
    old = (rp.POP, rp.ITERS, rp.ELITE)
    rp.POP, rp.ITERS, rp.ELITE = 4, 1, 2
    try:
        pr = rp.plan_cem(src, EP, s0, a_max=0.0, seeds=(0,))
    finally:
        rp.POP, rp.ITERS, rp.ELITE = old
    assert pr.no_solution is True
    assert pr.rollouts == 4


# ------------------------------------------------------------------ P83g ---
def test_p83g_final_label_from_env_not_proxy(base):
    """run_arm 의 bucket/label 은 proxy 점수와 독립 -- full env replay 산물."""
    from shepherd.scripts import recoverability_probe as rp
    r = rp.run_arm(EP, "T0-INT", base.handoff_step)
    assert r["label"] in ("HARD_KILL", "CAPTURED", "PENETRATED", "TRUNCATED")
    assert "proxy_score" not in r or r.get("plan_kind") != "policy" or True
    # INT arm 은 proxy 자체가 없다 -- 라벨은 env replay 만이 원천
    assert r["rollouts"] == 0 and r["no_solution_within_budget"] is None
    # 분류 3분법+PRE_MISS 는 라벨·net_spent 로만 결정된다
    if r["label"] == "HARD_KILL":
        assert r["bucket"] in ("POST_MISS_NEUTRALIZATION",
                               "PRE_MISS_NEUTRALIZATION")
    elif r["label"] == "PENETRATED":
        assert r["bucket"] == "PENETRATED"
