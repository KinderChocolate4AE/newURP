"""M4 시스템 레인 property 테스트 P6~P11 (docs/29 v3 §8 · §13.4).

강제(assert)와 보고(진단)를 의도적으로 구분한다 -- 강제하면 통과할 때까지 튜닝하게
되고 그것이 곧 착취다.

  P6   커밋 비트 0 -> ModeSystemEnv ≡ 동결 env, bit-identical        강제
  P7   Pk = 0     -> 하드킬 결코 성공 안 함 + limiter 순손실           강제
  P8   Pk = 1 ∧ 기하 충족 -> 반드시 HARD_KILL                         강제
  P9   소진 limiter 는 이후 shaping 에 기여하지 않는다                 강제
  P11  R_nk 안에서 HARD_KILL 이 결코 발생하지 않는다                   강제
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.agents.baselines import (hold_position_limiter, scripted_finisher,
                                       scripted_shaping_limiter)
from shepherd.env_sys import ModeSystemEnv, SystemSpec, PARK_POSITION
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import run_episode
from shepherd.train.make_env import make_train_env

HORIZON = 26

# 하드킬 검정용 능력 설정. 백엔드의 limiter v_max 가 권위 소스이므로 (docs/29 §12.4)
# layout 속성이 아니라 **config** 로 넣는다 -- 이전 판은 가짜 속성을 세팅해서
# intercept 정책이 80 m/s 를 쓰고 있었다(테스트가 코드보다 먼저 틀려 있던 사례).
SLOW_LIMITER = {"train.limits.limiter_v_max": 21.0}


def _pair(spec=None, **over):
    """(동결 env, 시스템 래퍼) 를 같은 config 로 두 개."""
    a, scn_a, lay_a = make_train_env(as_config(over or None))
    b, scn_b, lay_b = make_train_env(as_config(over or None))
    wrapped = ModeSystemEnv(b, lay_b, scn_b, spec or SystemSpec())
    return (a, scn_a, lay_a), (wrapped, scn_b, lay_b)


def _drive(env, scn, lay, *, steps=HORIZON, commit=0.0, mode="ring"):
    env.reset(seed=0)
    traj = []
    for _ in range(steps):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        traj.append((p_att.copy(), v_att.copy()))
        acts = {}
        for i, lid in enumerate(env.limiter_ids):
            if mode == "hold":
                base = hold_position_limiter()
            else:
                base = scripted_shaping_limiter(
                    i, env.N, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                    tau=env.tau_deploy, a_max=scn.limiter.a_max,
                    r_ring=lay.r_ring, dt=env.dt)
            acts[lid] = np.array([base[0], base[1], base[2], commit], np.float32)
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy, clean_threshold_crossed=False)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if term[env.finisher_id] or trunc[env.finisher_id]:
            break
    return traj


# ------------------------------------------------------------------ P6 ---
@pytest.mark.parametrize("spec,commit", [
    (SystemSpec(enabled=False), 1.0),        # 레인 자체를 끔
    (SystemSpec(enabled=True), 0.0),         # 켜지만 커밋 제안 없음
])
def test_p6_frozen_equivalence_bit_identical(spec, commit):
    """새 층이 기존 결과를 오염시키지 않음을 bit 수준에서 증명한다 (P1 과 같은 역할)."""
    (fz, s_a, l_a), (sy, s_b, l_b) = _pair(spec)
    ref = _drive(fz, s_a, l_a, commit=0.0)
    got = _drive(sy, s_b, l_b, commit=commit)
    assert len(ref) == len(got), f"길이 불일치 {len(ref)} != {len(got)}"
    for t, ((pr, vr), (pg, vg)) in enumerate(zip(ref, got)):
        assert np.array_equal(pr, pg), f"step {t} 위치 불일치"
        assert np.array_equal(vr, vg), f"step {t} 속도 불일치"


# ------------------------------------------------------------------ P7 ---
def test_p7_pk_zero_is_pure_loss():
    """Pk=0 이면 하드킬은 결코 성공하지 않고 limiter 는 소모된다."""
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    env = ModeSystemEnv(inner, lay, scn, SystemSpec(p_kill=0.0))
    r = run_episode(env, scn, lay, seed=0, limiter_mode="intercept", fire_mode="never")
    s = env.summary()
    assert r.label != "HARD_KILL", f"Pk=0 인데 하드킬 성공: {r.label}"
    assert s["KILL"] == 0, s
    assert s["committed"] > 0, "커밋 자체가 없어 검정 불가"
    assert s["consumed"] == s["committed"], f"소모되지 않음 (순손실이어야): {s}"


# ------------------------------------------------------------------ P8 ---
def test_p8_pk_one_geometric_must_kill():
    """Pk=1 이고 기하 조건을 만족한 커밋이 있으면 반드시 HARD_KILL."""
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    env = ModeSystemEnv(inner, lay, scn, SystemSpec(p_kill=1.0))
    r = run_episode(env, scn, lay, seed=0, limiter_mode="intercept", fire_mode="never")
    geo_ok = [c for c in env.commits if c.geometric_ok and c.outcome != "VETO_NO_KINETIC"]
    assert geo_ok, "기하 충족 커밋이 없어 검정 불가"
    assert r.label == "HARD_KILL", f"Pk=1 · 기하충족인데 {r.label}; {env.summary()}"
    assert env.summary()["PK_FAIL"] == 0


# ------------------------------------------------------------------ P9 ---
def test_p9_retired_limiter_does_not_shape():
    """소진 limiter 는 주차되어 이후 v_shot 에 기여하지 않는다."""
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    env = ModeSystemEnv(inner, lay, scn, SystemSpec(p_kill=0.0))   # 전부 실패·소진
    run_episode(env, scn, lay, seed=0, limiter_mode="intercept", fire_mode="never")
    assert env.retired, "소진된 limiter 가 없어 검정 불가"
    park = np.asarray(PARK_POSITION, float)
    for i in env.retired:
        p = env._p(env._states()[0][i])
        assert np.allclose(p, park), f"limiter {i} 미주차: {p}"
    # 주차 거리가 회랑 규모(<= ~30 m)를 압도해야 shaping 기여가 0 이다
    assert float(np.linalg.norm(park)) > 1e3


# ------------------------------------------------------------------ P11 ---
def test_p11_no_hard_kill_inside_no_kinetic_zone():
    """R_nk 안에서 해소된 커밋은 거부되고 limiter 도 소모되지 않는다."""
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    # R_nk 를 크게 잡아 전 구간을 no-kinetic 으로 만든다 -> 하드킬이 원천 봉쇄돼야
    env = ModeSystemEnv(inner, lay, scn, SystemSpec(p_kill=1.0, r_nk=100.0))
    r = run_episode(env, scn, lay, seed=0, limiter_mode="intercept", fire_mode="never")
    s = env.summary()
    assert r.label != "HARD_KILL", f"R_nk 안인데 하드킬 발생: {s}"
    assert s["KILL"] == 0, s
    assert s["VETO_NO_KINETIC"] > 0, f"거부 이벤트가 기록되지 않음: {s}"
    assert s["consumed"] == 0, f"거부인데 limiter 가 소모됨: {s}"


def test_p11_zone_boundary_reported(capsys):
    """R_nk 를 쓸면 하드킬 가능 구간이 어떻게 닫히는지 -- 보고만."""
    rows = []
    for r_nk in (0.0, 3.0, 6.0, 9.0, 12.0):
        inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
        env = ModeSystemEnv(inner, lay, scn, SystemSpec(p_kill=1.0, r_nk=r_nk))
        res = run_episode(env, scn, lay, seed=0, limiter_mode="intercept",
                          fire_mode="never")
        rows.append((r_nk, res.label, env.summary()))
    with capsys.disabled():
        print("\n[P11 보고] R_nk 스윕 (intercept arm, Pk=1)")
        for r_nk, lab, s in rows:
            print(f"    R_nk={r_nk:5.1f}  {lab:<12} KILL={s['KILL']} "
                  f"VETO={s['VETO_NO_KINETIC']} consumed={s['consumed']}")
    assert len(rows) == 5


# ------------------------------------------------------------ P13~P15 ---
# M4 보상 (docs/29 §15). 값을 하나 고르지 않고 w_kill 을 축으로 두는 것이 핵심이므로,
# 테스트는 "특정 값에서 잘 된다"가 아니라 **전 구간에서 순서가 유지된다**를 강제한다.
from shepherd.env_sys import RewardSpec  # noqa: E402


@pytest.mark.parametrize("w_kill", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_p13_reward_ordering_invariant(w_kill):
    """모든 w_kill 에서 NET_CAPTURE >= HARD_KILL > PENETRATED = TRUNCATED."""
    r = RewardSpec(w_kill=w_kill)
    net, hard = r.terminal("NET_CAPTURE"), r.terminal("HARD_KILL")
    pen, trunc = r.terminal("PENETRATED"), r.terminal("TRUNCATED")
    assert net >= hard, f"w_kill={w_kill}: 비손실이 파괴적보다 못하다"
    assert hard > pen, f"w_kill={w_kill}: 파괴적 성공이 침투보다 못하다"
    assert pen == trunc, "절단은 보상상 미격퇴(침투와 동일)로 선언됨"
    # limiter 를 전부 소모해도 하드킬이 침투보다 나아야 한다
    assert hard - r.c_lim * 4 > pen, f"w_kill={w_kill}: 소모 비용이 순서를 뒤집는다"


def test_p13b_spent_fail_is_neutral():
    """SPENT_FAIL 은 의미 감사 전까지 중립(0). 임의로 실패 처리하지 않는다."""
    assert RewardSpec(w_kill=0.5).terminal("SPENT_FAIL") == 0.0


def test_p14_reward_disabled_is_passthrough():
    """reward.enabled=False 면 보상이 동결 env 와 정확히 같아야 한다 (P6 연장)."""
    a, scn_a, lay_a = make_train_env(as_config())
    b, scn_b, lay_b = make_train_env(as_config())
    wrapped = ModeSystemEnv(b, lay_b, scn_b, SystemSpec(),
                            RewardSpec(enabled=False))
    a.reset(seed=0); wrapped.reset(seed=0)
    for _ in range(12):
        acts_a, acts_b = {}, {}
        for env, acts in ((a, acts_a), (wrapped, acts_b)):
            lims, fin, att = env._states()
            p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
            for i, lid in enumerate(env.limiter_ids):
                base = scripted_shaping_limiter(
                    i, env.N, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                    tau=env.tau_deploy, a_max=scn_a.limiter.a_max,
                    r_ring=lay_a.r_ring, dt=env.dt)
                acts[lid] = np.array([base[0], base[1], base[2], 0.0], np.float32)
            acts[env.finisher_id] = scripted_finisher(
                p_fin, p_att, v_att, tau=env.tau_deploy,
                clean_threshold_crossed=False)
            acts[env.adversary_id] = np.zeros(3, np.float32)
        _, ra, ta, ua, _ = a.step(acts_a)
        _, rb, tb, ub, _ = wrapped.step(acts_b)
        for k in ra:
            assert ra[k] == rb[k], f"보상 불일치 {k}: {ra[k]} != {rb[k]}"
        if ta[a.finisher_id] or ua[a.finisher_id]:
            break


def test_p15_reward_gradient_report(capsys):
    """w_kill 이 비손실/파괴적 보상 격차를 어떻게 움직이는지 -- 보고만."""
    rows = [(w, RewardSpec(w_kill=w).terminal("NET_CAPTURE"),
             RewardSpec(w_kill=w).terminal("HARD_KILL")) for w in
            (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
    with capsys.disabled():
        print("\n[P15 보고] w_kill -> 비손실 프리미엄")
        for w, n, h in rows:
            print(f"    w_kill={w:.1f}  NET={n:.2f}  HARD={h:.2f}  격차={n-h:.2f}")
    assert rows[0][1] - rows[0][2] == 0.0      # w_kill=0 -> 격차 없음
    assert rows[-1][1] - rows[-1][2] == 1.0    # w_kill=1 -> 최대 격차
