"""R2 net-miss handoff 테스트 P81~P82 (docs/54 §1·§6).

  P81  miss_terminates=False: net miss 가 종료가 아니라 mode transition 이 되고,
       SPENT_FAIL 은 라벨/종료로 더는 나오지 않으며 provenance 로 남는다   강제
  P82  R1+R2 동시 on 에서 종료가 침투·절단·무력화(포획 포함)뿐이다        강제

픽스처: v_soft >= theta_fire 첫 도달에 강제 발사 (clean 무관) -> 대부분 miss.
기본값 스캔으로 SPENT_FAIL seed 를 찾은 뒤 같은 seed 로 플래그를 켠다 (paired).
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.env_sys import ModeSystemEnv, SystemSpec
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import scripted_role_actions
from shepherd.train.make_env import make_train_env

SLOW_LIMITER = {"train.limits.limiter_v_max": 21.0}


def _wrapped(spec: SystemSpec, over=None):
    inner, scn, lay = make_train_env(as_config(over))
    return ModeSystemEnv(inner, lay, scn, spec), scn, lay


def _drive_fire_at_threshold(env, scn, lay, seed: int, mode: str = "intercept") -> dict:
    """v_soft 가 fire gate 를 처음 넘는 스텝에 무조건 발사 (miss 유도 픽스처)."""
    env.reset(seed=seed)
    fid = env.finisher_id
    out = dict(fire_step=None, handoff_step=None, end_step=None, steps=0,
               outcome=None, net_spent=False)
    fired = False
    for t in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        vf = env._vshot(env._p(att), env._v(att), [env._p(l) for l in lims],
                        fin, seed=0)
        acts = scripted_role_actions(env, scn, lay, limiter_mode=mode,
                                     fire_mode="never")
        if not fired and vf.v_shot_soft >= env.theta_fire:
            a = np.asarray(acts[fid], np.float32).copy()
            a[4] = 1.0
            acts[fid] = a
            fired = True
            out["fire_step"] = t
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, info = env.step(acts)
        out["steps"] = t + 1
        fi = info.get(fid) or next(iter(info.values()), {})
        if fi.get("net_miss_handoff"):
            out["handoff_step"] = t
        out["net_spent"] = bool(fi.get("net_spent", False))
        if term.get(fid):
            out["end_step"] = t
            out["outcome"] = ("HARD_KILL" if fi.get("hard_kill") else
                              "CAPTURED" if fi.get("captured") else
                              "PENETRATED" if fi.get("penetrated") else
                              "SPENT_FAIL")
            break
        if trunc.get(fid):
            out["end_step"] = t
            out["outcome"] = "TRUNCATED"
            break
    return out


def _find_miss_seed(max_seed: int = 12):
    """기본값(현행)에서 SPENT_FAIL 로 끝나는 seed 를 찾는다."""
    for seed in range(max_seed):
        env, scn, lay = _wrapped(SystemSpec(enabled=True), SLOW_LIMITER)
        r = _drive_fire_at_threshold(env, scn, lay, seed)
        if r["outcome"] == "SPENT_FAIL":
            return seed, r
    return None, None


# ------------------------------------------------------------------ P81 ---
def test_p81_miss_is_mode_transition_not_terminal():
    seed, base = _find_miss_seed()
    assert seed is not None, "SPENT_FAIL 픽스처를 찾지 못해 검정 불가"
    env, scn, lay = _wrapped(SystemSpec(enabled=True, miss_terminates=False),
                             SLOW_LIMITER)
    r = _drive_fire_at_threshold(env, scn, lay, seed)
    # 같은 물리: 전이는 기본값의 종료 스텝과 같은 스텝에서 일어난다
    assert r["handoff_step"] == base["end_step"], (r, base)
    # 에피소드가 계속된다
    assert r["steps"] > base["steps"], (r, base)
    # SPENT_FAIL 은 더 이상 종료 라벨이 아니다 -- provenance 로만 남는다
    assert r["outcome"] in ("PENETRATED", "TRUNCATED", "HARD_KILL"), r
    assert r["net_spent"] is True
    assert env.net_spent and env.net_spent_step == base["end_step"] + 1
    assert env.fsm.state.name == "SPENT" and env.fsm.wasted_fire == 1
    assert env.fsm.k == 0, "FALLBACK 에서 재장전은 범위 밖 (docs/54 §5)"


def test_p81_capture_termination_never_suppressed():
    """억제는 spent-fail 에만 건다 -- 포획/침투 종료는 그대로 종료다."""
    # 발사하지 않는 hold 기저선: 침투 또는 절단으로 끝나야 한다
    env, scn, lay = _wrapped(SystemSpec(enabled=True, miss_terminates=False),
                             SLOW_LIMITER)
    env.reset(seed=0)
    fid = env.finisher_id
    for t in range(int(lay.episode_len)):
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="never")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, info = env.step(acts)
        if term.get(fid):
            fi = info[fid]
            assert fi.get("penetrated") or fi.get("captured") or fi.get("hard_kill")
            assert not env.net_spent
            return
        if trunc.get(fid):
            return
    pytest.fail("종료도 절단도 없었다")


# ------------------------------------------------------------------ P82 ---
def test_p82_terminal_set_with_r1_and_r2():
    """R1+R2 on: 종료는 침투·절단·무력화(포획 포함)뿐. SPENT_FAIL 종료 0.

    docs/54 §6 P82 선언 그대로 -- 종료 **집합** 검정이다. "miss 후 폴백이 실제로
    무력화하는가" 의 e2e 증거는 사전등록된 V3 F-arm 감사가 담당한다 (플레인 env
    기하에선 접촉이 SPENT 해소보다 항상 먼저라 miss 표본이 안 생긴다 -- 실측).
    """
    allowed = {"PENETRATED", "TRUNCATED", "HARD_KILL", "CAPTURED"}
    for mode in ("hold", "ring", "intercept"):
        for seed in (0, 1):
            env, scn, lay = _wrapped(
                SystemSpec(enabled=True, miss_terminates=False,
                           contact_resolver=True, p_kill=1.0, r_nk=0.0),
                SLOW_LIMITER)
            r = _drive_fire_at_threshold(env, scn, lay, seed, mode=mode)
            assert r["outcome"] in allowed, f"{mode}/seed {seed}: {r}"
