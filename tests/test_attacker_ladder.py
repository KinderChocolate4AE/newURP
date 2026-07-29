"""공격자 사다리 property 테스트 P1~P5 (docs/27 §5 · docs/28 §6).

이 테스트들은 **실험보다 먼저** 존재해야 한다 (claim governance: property test를
headline 실험보다 먼저). 강제(assert)와 보고(진단 출력)를 의도적으로 구분한다 --
강제하면 통과할 때까지 튜닝하게 되고 그게 곧 착취 방지 규칙 2 위반이다.

  P1   AdversaryLadderEnv(A1) ≡ frozen env, bit-identical      강제
  P1b  일반 구현(extras=0) ≡ A1 위임 경로                       강제
  P2   무방어 상대 전 층 침투율 = 1.0                            강제
  P3   층에 대한 침투율 단조성                                   보고만
  P4   lambda=0 vs lambda=REF 의 NET_CAPTURE 대조               조건부(포획 가능점 필요)
  P5   lambda=REF 에서의 접촉                                    보고만
"""
from __future__ import annotations

import numpy as np
import pytest

from dataclasses import replace
from shepherd.agents.attacker_ladder import (A1_SPEC, AttackerSpec, LAMBDA_PRESETS,
                                             derive_phase, is_a1_equivalent,
                                             make_attacker)
from shepherd.agents.baselines import hold_position_limiter, scripted_finisher
from shepherd.env_adv import attach_attacker, detach_attacker
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import run_episode
from shepherd.train.make_env import make_train_env

HORIZON = 26          # 침투까지 ~23 스텝. viability 샘플러가 느려 짧게 유지.


def _env(**over):
    return make_train_env(as_config(over or None))


def _drive(env, scn, lay, *, steps, attacker=None, phase=0.0, seed=0):
    """hold 방어로 고정 구동하고 공격자 궤적을 기록한다."""
    if attacker is not None:
        attach_attacker(env, attacker, phase=phase)
    else:
        detach_attacker(env)
    env.reset(seed=seed)
    traj = []
    for _ in range(steps):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        traj.append((p_att.copy(), v_att.copy()))
        acts = {lid: hold_position_limiter() for lid in env.limiter_ids}
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy, clean_threshold_crossed=False)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if term[env.finisher_id] or trunc[env.finisher_id]:
            break
    return traj


# ------------------------------------------------------------------ P1 ---
def test_p1_frozen_equivalence_bit_identical():
    """A1 을 주입한 프록시가 동결 경로와 bit-identical 이어야 한다.

    실패하면 사다리 전체가 무효다 (docs/27 §5: 진행 정지).
    """
    env_a, scn, lay = _env()
    ref = _drive(env_a, scn, lay, steps=HORIZON, attacker=None)

    env_b, scn_b, lay_b = _env()
    got = _drive(env_b, scn_b, lay_b, steps=HORIZON, attacker=make_attacker(A1_SPEC))

    assert len(ref) == len(got), f"길이 불일치 {len(ref)} != {len(got)}"
    for t, ((pr, vr), (pg, vg)) in enumerate(zip(ref, got)):
        assert np.array_equal(pr, pg), f"step {t} 위치 불일치: {pr} != {pg}"
        assert np.array_equal(vr, vg), f"step {t} 속도 불일치: {vr} != {vg}"


def test_p1_delegation_assert_mode():
    """assert_delegation=True 로 매 스텝 동결 출력과 대조해도 통과해야 한다."""
    env, scn, lay = _env()
    attach_attacker(env, make_attacker(A1_SPEC), phase=0.0)
    env.backend._assert_delegation = True
    _drive(env, scn, lay, steps=HORIZON, attacker=make_attacker(A1_SPEC))
    assert env.backend.n_override > 0, "프록시가 한 번도 개입하지 않았다"


# ----------------------------------------------------------------- P1b ---
def test_p1b_general_reproduces_a1():
    """일반 구현(extras=0, lambda=REF)이 A1 위임 경로와 수치적으로 같아야 한다.

    force_general=True 로 위임을 우회하므로 자명하지 않다.
    """
    deleg = make_attacker(A1_SPEC)
    gen = make_attacker(A1_SPEC, force_general=True)
    rng = np.random.default_rng(20260727)
    for _ in range(200):
        kw = dict(
            target=np.zeros(3), net_center=rng.normal(size=3) * 3.0,
            finisher_p=np.array([2.0, 0.0, 0.0]),
            limiters=rng.normal(size=(4, 3)) * 4.0,
            kill_radius=2.0, a_att_max=30.0, omega_att_max=8.0,
            v_nominal=20.0, dt=0.05, committed=bool(rng.integers(2)),
            repel_margin=1.0,
        )
        p = rng.normal(size=3) * 8.0
        v = rng.normal(size=3) * 10.0
        a = deleg(p, v, **kw)
        b = gen(p, v, t=0.0, phase=0.0, **kw)
        assert np.allclose(a["a"], b["a"], rtol=0, atol=1e-12), f"{a['a']} != {b['a']}"
        assert np.allclose(a["e_cmd"], b["e_cmd"], rtol=0, atol=1e-12)


def test_p1b_nesting_flags():
    assert is_a1_equivalent(A1_SPEC)
    assert is_a1_equivalent(AttackerSpec(level="A2"))           # extras 0 -> A1 등가
    assert not is_a1_equivalent(AttackerSpec(level="A2", jink_amp=0.3))
    assert not is_a1_equivalent(AttackerSpec(level="A2", route_gain=0.3))
    assert not is_a1_equivalent(AttackerSpec(lam_gain=0.0))     # lambda 변화도 비등가


# ------------------------------------------------------------------ P2 ---
@pytest.mark.parametrize("spec", [
    A1_SPEC,
    AttackerSpec(level="A2", jink_amp=0.35, route_gain=0.0, label="A2-jink"),
    AttackerSpec(level="A2", jink_amp=0.0, route_gain=0.4, label="A2-route"),
    AttackerSpec(level="A2", jink_amp=0.35, route_gain=0.4, label="A2"),
])
def test_p2_no_defense_always_penetrates(spec):
    """무방어(hold) 상대로는 어떤 층도 침투율 1.0 이어야 한다.

    공격자를 강하게 만들다가 실제로는 약하게 만드는(전진을 갉아먹는) 실수를 잡는
    핵심 안전장치. 값싸고 결정적이다.
    """
    env, scn, lay = _env()
    for ep in range(3):
        attach_attacker(env, make_attacker(spec), phase=derive_phase(spec.seed, ep))
        r = run_episode(env, scn, lay, seed=ep, limiter_mode="hold",
                        fire_mode="never", attacker_name=spec.name())
        assert r.outcome == "PENETRATED", (
            f"{spec.name()} ep{ep}: 무방어인데 {r.outcome} "
            f"(min_dist={r.min_target_dist:.2f}) -- 공격자 자해")


# ------------------------------------------------------------------ P3 ---
def test_p3_difficulty_monotonicity_report(capsys):
    """층이 올라갈수록 침투가 쉬워지는가 -- **보고만**, 강제하지 않는다.

    강제하면 통과할 때까지 튜닝하게 되고 그게 착취 방지 규칙 2 위반이다.
    실패하면 그 자체가 발견이다(회피가 방어자를 돕는 경우).
    """
    env, scn, lay = _env()
    specs = [A1_SPEC,
             AttackerSpec(level="A2", jink_amp=0.35, label="A2-jink"),
             AttackerSpec(level="A2", jink_amp=0.35, route_gain=0.4, label="A2")]
    rows = []
    for spec in specs:
        attach_attacker(env, make_attacker(spec), phase=derive_phase(spec.seed, 0))
        r = run_episode(env, scn, lay, seed=0, limiter_mode="ring", fire_mode="x_fire")
        rows.append((spec.name(), r.label, r.n_contact, r.steps, r.min_target_dist))
    with capsys.disabled():
        print("\n[P3 보고] 정적 ring 상대 (강제 아님)")
        for name, lab, c, st, d in rows:
            print(f"    {name:<38} {lab:<20} contact={c} steps={st} min_d={d:.2f}")
    assert len(rows) == len(specs)


# ------------------------------------------------------------------ P5 ---
def test_p5_contact_vs_lambda_report(capsys):
    """lambda 별 접촉 수 -- **보고만**.

    docs/28 은 'lambda=REF 에서 접촉 ≈ 0' 을 기대했지만, 링이 능동적으로 파고들면
    반발이 a_att_max 로 상한이라 회피가 불가능하다. 접촉은 공격자의 겁만이 아니라
    **방어자의 공격성**이 만든다 -- 그래서 강제하지 않는다.
    """
    env, scn, lay = _env()
    rows = []
    for name in ("LAM_ZERO", "LAM_LOW", "LAM_MID", "LAM_REF", "LAM_ANTIC"):
        g, rg = LAMBDA_PRESETS[name]
        spec = AttackerSpec(level="A1", lam_gain=g, lam_range=rg, label=name)
        attach_attacker(env, make_attacker(spec), phase=0.0)
        r = run_episode(env, scn, lay, seed=0, limiter_mode="ring", fire_mode="x_fire")
        rows.append((name, g, rg, r.label, r.n_contact, r.contact_steps, r.steps))
    with capsys.disabled():
        print("\n[P5 보고] lambda x 접촉 (정적 ring)")
        for name, g, rg, lab, c, cs, st in rows:
            print(f"    {name:<10} gain={g:<5} range={rg:<4} {lab:<20} "
                  f"contact={c} steps_in_radius={cs} steps={st}")
    assert len(rows) == 5


# ------------------------------------------------------------------ P4 ---
def test_p4_lambda_zero_control():
    """lambda=0 에서 NET_CAPTURE 가 유지되면 조향이 아니라 물리적 차단이다.

    현 운용점에서는 **어떤 arm 도 NET_CAPTURE 를 내지 못하므로** 이 대조가 아직
    성립하지 않는다. 포획 가능 운용점이 발견된 뒤 강제로 승격한다 (docs/28 §6).
    """
    env, scn, lay = _env()
    out = {}
    for name in ("LAM_ZERO", "LAM_REF"):
        g, rg = LAMBDA_PRESETS[name]
        spec = AttackerSpec(level="A1", lam_gain=g, lam_range=rg, label=name)
        attach_attacker(env, make_attacker(spec), phase=0.0)
        r = run_episode(env, scn, lay, seed=0, limiter_mode="ring", fire_mode="x_fire")
        out[name] = r
    if out["LAM_REF"].label != "NET_CAPTURE":
        pytest.skip(
            "포획 가능 운용점 미발견 -- lambda=REF 에서도 NET_CAPTURE 가 없어 "
            f"대조 불가 (REF={out['LAM_REF'].label}, ZERO={out['LAM_ZERO'].label}). "
            "docs/28 §6 P4 는 포획 가능점 발견 후 강제로 승격한다.")
    assert out["LAM_ZERO"].label != "NET_CAPTURE", (
        "lambda=0(위협 무시)에서도 비손실 포획이 성립 -- 조향이 아니라 물리적 차단. "
        "C1 기전 주장 철회 대상.")


# ------------------------------------------------------------ P16~P18 ---
# A3 발사 유도 (docs/27 §2.4). K=1 에서 발사를 뽑아내고 회피하면 그 뒤는 무방비이므로
# 유일한 지배 전략이다. A1 단독 보고가 리젝 사유인 것과 같은 이유로 A3 는 필수다.

A3_FAIR = AttackerSpec(level="A3", jink_amp=0.35, route_gain=0.4,
                       bait_gain=0.6, label="A3-fair")
A3_PRIV = AttackerSpec(level="A3", jink_amp=0.35, route_gain=0.4,
                       bait_gain=0.6, bait_privileged=True, label="A3-priv")


def test_p16_a3_nesting_to_a2():
    """A3(bait_gain=0) 은 A2 와 궤적이 정확히 같아야 한다 (단조성)."""
    a2 = AttackerSpec(level="A2", jink_amp=0.35, route_gain=0.4)
    a3 = replace(a2, level="A3", bait_gain=0.0)
    env_a, scn_a, lay_a = _env()
    env_b, scn_b, lay_b = _env()
    ta = _drive(env_a, scn_a, lay_a, steps=HORIZON, attacker=make_attacker(a2))
    tb = _drive(env_b, scn_b, lay_b, steps=HORIZON, attacker=make_attacker(a3))
    assert len(ta) == len(tb)
    for t, ((pa, va), (pb, vb)) in enumerate(zip(ta, tb)):
        assert np.array_equal(pa, pb), f"step {t} A3(bait=0) != A2"
        assert np.array_equal(va, vb)


@pytest.mark.parametrize("spec", [A3_FAIR, A3_PRIV])
def test_p17_a3_no_defense_always_penetrates(spec):
    """P2 확장 — A3 도 무방어 상대로는 반드시 침투해야 한다(자해 금지)."""
    env, scn, lay = _env()
    for ep in range(2):
        attach_attacker(env, make_attacker(spec), phase=derive_phase(spec.seed, ep))
        r = run_episode(env, scn, lay, seed=ep, limiter_mode="hold",
                        fire_mode="never", attacker_name=spec.name())
        assert r.outcome == "PENETRATED", (
            f"{spec.name()} ep{ep}: 무방어인데 {r.outcome} "
            f"(min_dist={r.min_target_dist:.2f}) -- 공격자 자해")


def test_p18_bait_effect_report(capsys):
    """베이팅 기전을 **직접** 잰다 -- 보고만.

    처음엔 x_fire 트리거로 재려 했으나 그건 위치 고정이라 유도에 반응하지 않는다.
    베이팅은 **상태 의존 발사**에만 의미가 있으므로, 발사 정책과 무관하게 기전 자체를
    재는 것이 옳다: **공격자가 스스로를 얼마나 포획 가능해 보이게 만드는가**
    = 커밋 전 `v_shot_soft` 의 최대치와 임계 초과 스텝 수.

    강제하지 않는 이유: A3 가 더 유도하도록 파라미터를 조이면 그 순간 착취 방지
    규칙 2 위반이다. 효과가 없으면 그것이 결과다
    (= "현실 공격자는 발사 조건을 추정하지 못한다").
    """
    from shepherd.agents.baselines import scripted_shaping_limiter
    rows = []
    for spec in (AttackerSpec(level="A2", jink_amp=0.35, route_gain=0.4, label="A2"),
                 A3_FAIR, A3_PRIV):
        env, scn, lay = _env()
        attach_attacker(env, make_attacker(spec), phase=derive_phase(spec.seed, 0))
        env.reset(seed=0)
        soft, n_thr = [], 0
        for _ in range(HORIZON):
            lims, fin, att = env._states()
            p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
            acts = {lid: scripted_shaping_limiter(
                        i, env.N, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                        tau=env.tau_deploy, a_max=scn.limiter.a_max,
                        r_ring=lay.r_ring, dt=env.dt)
                    for i, lid in enumerate(env.limiter_ids)}
            acts[env.finisher_id] = scripted_finisher(
                p_fin, p_att, v_att, tau=env.tau_deploy,
                clean_threshold_crossed=False)
            acts[env.adversary_id] = np.zeros(3, np.float32)
            _, _, term, trunc, info = env.step(acts)
            fi = info[env.finisher_id]
            env._last_v_shot_soft = float(fi["v_shot_soft"])
            soft.append(float(fi["v_shot_soft"]))
            n_thr += int(fi["v_shot_soft"] >= 0.9)
            if term[env.finisher_id] or trunc[env.finisher_id]:
                break
        rows.append((spec.name(), max(soft), float(np.mean(soft)), n_thr, len(soft)))
    with capsys.disabled():
        print("\n[P18 보고] 베이팅 기전 — 스스로를 얼마나 포획 가능해 보이게 하는가")
        for name, mx, mean, n_thr, n in rows:
            print(f"    {name:<10} max_v_soft={mx:.3f}  mean={mean:.3f}  "
                  f"steps>=0.9: {n_thr}/{n}")
    assert len(rows) == 3
