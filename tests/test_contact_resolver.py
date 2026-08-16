"""R1 접촉 event resolver 테스트 P78~P80 (docs/54 §1·§6).

  P78  contact_resolver=False(기본) -> 기존 경로와 bit-identical          강제
  P79  swept 검출·경계 <=·소모·NK veto 가 커밋 경로와 동일하게 걸린다     강제
  P80  접촉 시에만 발동 + event 중복 방지 (pending/retired 제외,
       terminal success 1회, veto 는 미소모·재평가 가능)                  강제

P80 의 중복 방지는 e2e 로 결정적으로 만들기 어려워 `_resolve_contacts` 를
직접 호출한다 -- step() 이 쓰는 바로 그 객체다 (별도 공식 복제 금지 규율).
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.env_sys import (CommitRecord, ModeSystemEnv, SystemSpec,
                              _seg_min_dist, commit_margin)
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import run_episode
from shepherd.train.make_env import make_train_env

SLOW_LIMITER = {"train.limits.limiter_v_max": 21.0}   # test_mode_system 과 동일


def _wrapped(spec: SystemSpec, over=None):
    inner, scn, lay = make_train_env(as_config(over))
    return ModeSystemEnv(inner, lay, scn, spec), scn, lay


# ------------------------------------------------------------------ P78 ---
@pytest.mark.parametrize("mode", ["hold", "intercept"])
def test_p78_default_off_bit_identical(mode):
    """기본값(contact_resolver=False)에서 라벨·종료 스텝·결과가 동결 env 와 동일."""
    frozen, s_a, l_a = make_train_env(as_config(SLOW_LIMITER))
    sys_env, s_b, l_b = _wrapped(SystemSpec(enabled=True, contact_resolver=False),
                                 SLOW_LIMITER)
    for seed in (0, 1, 2):
        ra = run_episode(frozen, s_a, l_a, seed=seed, limiter_mode=mode,
                         fire_mode="clean")
        rb = run_episode(sys_env, s_b, l_b, seed=seed, limiter_mode=mode,
                         fire_mode="clean")
        assert (ra.label, ra.outcome, ra.steps) == (rb.label, rb.outcome, rb.steps), \
            f"seed {seed}: {ra.label}/{ra.steps} != {rb.label}/{rb.steps}"
        assert ra.min_target_dist == rb.min_target_dist, f"seed {seed} 상태 발산"
    assert sys_env.summary()["contact_events"] == 0


# ------------------------------------------------------------------ P79 ---
def test_p79_swept_beats_endpoint():
    """step 양 끝은 반경 밖, 중간 통과 -> endpoint 검사였으면 놓쳤을 사례."""
    r0 = np.array([-2.0, 0.3, 0.0])          # |r0| ≈ 2.02
    r1 = np.array([+2.0, 0.3, 0.0])          # |r1| ≈ 2.02, 선분 최소거리 0.3
    assert min(np.linalg.norm(r0), np.linalg.norm(r1)) > 0.75   # endpoint 는 못 봄
    assert _seg_min_dist(r0, r1) == pytest.approx(0.3)
    assert _seg_min_dist(r0, r1) <= 0.75


def test_p79_boundary_inclusive():
    """경계 규약: d_min == r_contact 는 접촉이다 (<=, docs/54 §1)."""
    env, scn, lay = _wrapped(SystemSpec(enabled=True, contact_resolver=True,
                                        p_kill=1.0))
    env.reset(seed=0)
    r = float(env.inner.kill_radius)
    lim = np.zeros(3)
    p_att = np.array([r, 0.0, 0.0])          # 정확히 반경 위, 정지
    ev = env._resolve_contacts(p_att, [lim], p_att, [lim], d_asset=1e9)
    assert len(ev) == 1 and ev[0].outcome == "KILL", ev
    assert ev[0].d_nom == pytest.approx(r)


def test_p79_contact_kills_and_consumes():
    """실 접촉 -> event 발생, limiter 소모·retire, 라벨 HARD_KILL (신설 라벨 없음)."""
    env, scn, lay = _wrapped(SystemSpec(enabled=True, contact_resolver=True,
                                        p_kill=1.0, r_nk=0.0), SLOW_LIMITER)
    res = run_episode(env, scn, lay, seed=0, limiter_mode="intercept",
                      fire_mode="never")
    s = env.summary()
    assert s["contact_events"] > 0, "접촉 자체가 없어 검정 불가"
    assert s["committed"] == 0, "커밋 없이 접촉만으로 발동해야 하는 픽스처"
    assert res.label == "HARD_KILL", f"{res.label}; {s}"
    assert env.retired, "KILL 인데 limiter 미소모"
    kills = [r for r in env.commits if r.outcome == "KILL"]
    assert kills and all(r.source == "contact" for r in kills)


def test_p79_no_kinetic_veto_applies_to_contact():
    """NK zone 전역 -> 접촉해도 무력화 없음, limiter 미소모, veto 기록 (P11 동형)."""
    env, scn, lay = _wrapped(SystemSpec(enabled=True, contact_resolver=True,
                                        p_kill=1.0, r_nk=100.0), SLOW_LIMITER)
    res = run_episode(env, scn, lay, seed=0, limiter_mode="intercept",
                      fire_mode="never")
    s = env.summary()
    assert s["contact_events"] > 0, "접촉 자체가 없어 검정 불가"
    assert res.label != "HARD_KILL", s
    assert s["KILL"] == 0 and s["consumed"] == 0, s
    assert s["VETO_NO_KINETIC"] > 0 and not env.retired, s


def test_p79_pk_zero_is_pure_loss_on_contact():
    """Pk=0: 접촉은 limiter 를 소모하되 결코 무력화하지 않는다 (P7 동형)."""
    env, scn, lay = _wrapped(SystemSpec(enabled=True, contact_resolver=True,
                                        p_kill=0.0, r_nk=0.0), SLOW_LIMITER)
    res = run_episode(env, scn, lay, seed=0, limiter_mode="intercept",
                      fire_mode="never")
    s = env.summary()
    assert s["contact_events"] > 0, "접촉 자체가 없어 검정 불가"
    assert res.label != "HARD_KILL" and s["KILL"] == 0, s
    assert s["PK_FAIL"] > 0 and s["consumed"] == s["PK_FAIL"], s


# ------------------------------------------------------------------ P80 ---
def _fresh(spec=None):
    env, _, _ = _wrapped(spec or SystemSpec(enabled=True, contact_resolver=True,
                                            p_kill=1.0))
    env.reset(seed=0)
    return env


FAR = np.array([50.0, 50.0, 0.0])


def test_p80_no_contact_no_event():
    """반경 밖이면 boxed 여부와 무관하게 아무 일도 없다 (resolver 는 거리만 본다)."""
    env = _fresh()
    ev = env._resolve_contacts(FAR, [np.zeros(3)], FAR, [np.zeros(3)], d_asset=1e9)
    assert ev == [] and not env.retired and not env.hard_kill
    assert env.summary()["contact_events"] == 0


def test_p80_pending_commit_excluded():
    """커밋 대기 limiter 는 접촉 검사 제외 -- 같은 스텝 이중 소모 금지."""
    env = _fresh()
    env.pending[0] = CommitRecord(0, 1, 3, 0.0, 0.75, True)
    ev = env._resolve_contacts(np.zeros(3), [np.zeros(3)], np.zeros(3),
                               [np.zeros(3)], d_asset=1e9)
    assert ev == [], "pending limiter 가 접촉으로 중복 소모됐다"


def test_p80_retired_excluded():
    env = _fresh()
    env.retired.add(0)
    ev = env._resolve_contacts(np.zeros(3), [np.zeros(3)], np.zeros(3),
                               [np.zeros(3)], d_asset=1e9)
    assert ev == []


def test_p80_single_terminal_success():
    """두 limiter 동시 접촉 + Pk=1 -> KILL 은 1회, 잔여 접촉 미평가."""
    env = _fresh()
    lims = [np.zeros(3), np.zeros(3)]
    ev = env._resolve_contacts(np.zeros(3), lims, np.zeros(3), lims, d_asset=1e9)
    assert len(ev) == 1 and ev[0].outcome == "KILL" and env.hard_kill
    assert env.retired == {0}, "KILL 후 두 번째 limiter 까지 소모됐다"


def test_p80_veto_not_consumed_then_reevaluated():
    """veto 는 미소모 -- 이후 NK zone 밖 재접촉이면 정상 해소된다."""
    env = _fresh()
    ev1 = env._resolve_contacts(np.zeros(3), [np.zeros(3)], np.zeros(3),
                                [np.zeros(3)], d_asset=0.0)     # zone 안 -> veto
    assert ev1[0].outcome == "VETO_NO_KINETIC" and not ev1[0].consumed
    assert not env.retired and not env.hard_kill
    ev2 = env._resolve_contacts(np.zeros(3), [np.zeros(3)], np.zeros(3),
                                [np.zeros(3)], d_asset=1e9)     # zone 밖 -> 해소
    assert ev2[0].outcome == "KILL" and env.hard_kill


# ------------------------------------------- 반경 3종 키 분리 (리뷰 3) ---
def test_radius_keys_default_to_kill_radius():
    """r_commit/r_contact 기본 None -> 기존 kill_radius 와 동일 값 (배선만 분리)."""
    env, scn, lay = _wrapped(SystemSpec(enabled=True), SLOW_LIMITER)
    res = run_episode(env, scn, lay, seed=0, limiter_mode="intercept",
                      fire_mode="never", baseline_commit=True)
    # R-001: 기대값도 단일 정의원에서 뽑는다 (별도 공식 복제 금지 규율).
    margin_expect = commit_margin(env.spec, kill_radius=env.inner.kill_radius,
                                  a_lim_max=env.a_lim_max,
                                  a_att_max=env.inner.a_att_max)
    assert env.commits, "커밋이 없어 검정 불가"
    assert env.commits[0].margin == pytest.approx(margin_expect)


def test_radius_keys_independent():
    """r_commit 은 커밋 margin 만, r_contact 은 접촉 판정만 움직인다."""
    env, _, _ = _wrapped(SystemSpec(enabled=True, contact_resolver=True,
                                    p_kill=1.0, r_contact=0.3))
    env.reset(seed=0)
    at = np.array([0.5, 0.0, 0.0])           # 0.75 안 / 0.3 밖
    assert env._resolve_contacts(at, [np.zeros(3)], at, [np.zeros(3)], 1e9) == []
    at2 = np.array([0.25, 0.0, 0.0])         # 0.3 안
    ev = env._resolve_contacts(at2, [np.zeros(3)], at2, [np.zeros(3)], 1e9)
    assert len(ev) == 1 and ev[0].margin == pytest.approx(0.3)
    # r_shape (viability) 는 두 키와 무관 -- 동결 env 소관
    env2, scn2, lay2 = _wrapped(SystemSpec(enabled=True, r_commit=2.0,
                                           r_contact=0.1), SLOW_LIMITER)
    env3, _, _ = _wrapped(SystemSpec(enabled=True), SLOW_LIMITER)
    env2.reset(seed=0); env3.reset(seed=0)
    lims, fin, att = env2._states()
    a = env2._vshot(env2._p(att), env2._v(att), [env2._p(l) for l in lims], fin, seed=0)
    lims3, fin3, att3 = env3._states()
    b = env3._vshot(env3._p(att3), env3._v(att3), [env3._p(l) for l in lims3], fin3, seed=0)
    assert a.v_shot_soft == b.v_shot_soft and a.boxed_in == b.boxed_in
