"""docs/66 r1 — terminal truth table 행 단위 검정 (B4).

커버리지 매핑 (중복 작성 금지):
  행 2/3/4 (engagement 해소: KILL/PK_FAIL/NK veto)  = test_contact_resolver P79
  행 7/8   (R2 miss handoff + 이후 종료 집합)        = test_net_miss_handoff P81/P82
  여기      행 1·5·6·9·10·11·12 라벨 + 보상값 계약    (docs/66 §2·§3)

P80 선례대로 step() 이 쓰는 **실제 객체**(`_outcome_label` /
`RewardSpec.terminal`)를 직접 호출한다 -- 별도 공식 복제 금지 규율.
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.env_sys import ModeSystemEnv, RewardSpec, ratified_system
from shepherd.params import as_config
from shepherd.train.make_env import make_train_env

B_NET = RewardSpec().b_net


def _wrapped():
    inner, scn, lay = make_train_env(as_config())
    env = ModeSystemEnv(inner, lay, scn, ratified_system(),
                        RewardSpec(w_kill=0.5, enabled=True))
    env.reset(seed=0)
    return env


def _move_limiter(env, i: int, pos) -> None:
    ag = env.inner.backend.by_name(env.inner.limiter_ids[i])
    ag.p = np.asarray(pos, float).copy()
    ag.v = np.zeros(3)


def _att_pos(env):
    return env.inner._p(env.inner._states()[2])


def _label(env, *, captured=False, penetrated=False, trunc=False):
    fid = env.inner.finisher_id
    terms = {fid: not trunc}
    truncs = {fid: trunc}
    infos = {fid: {"captured": captured, "penetrated": penetrated}}
    return env._outcome_label(terms, truncs, infos)


# ---------------------------------------------------- 보상값 계약 (Q1 비준) ---
@pytest.mark.parametrize("w_kill", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_terminal_values_ratified(w_kill):
    """docs/66 §5 Q1: CWC = NET = +b_net. 순서 불변식은 CWC 포함으로 확장."""
    r = RewardSpec(w_kill=w_kill)
    net, cwc = r.terminal("NET_CAPTURE"), r.terminal("CAPTURE_WITH_CONTACT")
    hard = r.terminal("HARD_KILL")
    pen, trunc = r.terminal("PENETRATED"), r.terminal("TRUNCATED")
    assert cwc == net == r.b_net, "비준: 동일 nondestructive utility class"
    assert cwc > 0.0, "우연한 else=0 회귀 (감사 blocker 3 -- docs/66 이전 상태)"
    assert net >= hard > pen == trunc


# ----------------------------------------------------------- 라벨 행 검정 ---
def test_row1_net_capture_only():
    env = _wrapped()
    # 초기 배치는 접촉 밖이어야 픽스처가 성립한다 (ring 8m vs attacker 24m)
    assert all(float(np.linalg.norm(_att_pos(env) - env.inner._p(s)))
               > env.inner.kill_radius for s in env.inner._states()[0])
    assert _label(env, captured=True) == "NET_CAPTURE"


def test_row5_capture_with_terminal_proximity_pays_b_net():
    """행 5 -- 포획 종료 tick 에 limiter 순간 근접 -> CWC ∧ +b_net.

    docs/66 이전에는 이 라벨이 RewardSpec.terminal 의 else 로 떨어져 0 이었다.
    """
    env = _wrapped()
    _move_limiter(env, 0, _att_pos(env))
    lab = _label(env, captured=True)
    assert lab == "CAPTURE_WITH_CONTACT"
    assert env.reward_spec.terminal(lab) == B_NET


def test_row6_same_tick_kill_masks_capture():
    """행 6 -- 같은 tick capture+KILL -> HARD_KILL (discrete-event precedence
    convention. 50ms tick 내부의 물리 시간순서 주장이 아니다 -- docs/66 주 6)."""
    env = _wrapped()
    env.hard_kill = True
    lab = _label(env, captured=True)
    assert lab == "HARD_KILL"
    r = env.reward_spec
    assert r.terminal(lab) == r.b_net * (1.0 - r.w_kill)
    assert r.terminal(lab) < r.terminal("NET_CAPTURE"), \
        "NET_CAPTURE 로 계상하면 비손실 성과 과대계상 (비준 Q2)"


def test_rows_9_10_11_failure_labels():
    env = _wrapped()
    assert _label(env, penetrated=True) == "PENETRATED"
    assert _label(env, trunc=True) == "TRUNCATED"
    assert _label(env) == "SPENT_FAIL"
    r = env.reward_spec
    assert r.terminal("PENETRATED") == -r.c_pen
    assert r.terminal("TRUNCATED") == -r.c_trunc
    assert r.terminal("SPENT_FAIL") == 0.0


def test_row12_canonical_prior_proximity_then_clean_capture():
    """★ canonical regression (docs/66 행 12, B1 divergence 재현).

    step 10 근접 -> step 50 clean capture:
      - 이력 술어(had_prior_engagement, mission_rollout 의 에피소드 집합)  = True
      - 보상측 terminal-state 술어(종료 순간 근접)                        = False
      -> 보상 라벨 NET_CAPTURE / 지표 수식어 CWC. 두 라벨의 terminal 이
      같아야(+b_net) 이 divergence 가 학습 목표를 바꾸지 않는다 (비준 Q1·Q3).
    """
    env = _wrapped()
    p_att = _att_pos(env)

    # "step 10": limiter 0 이 kill_radius 안 -- mission_rollout.py:274 와 같은 술어
    _move_limiter(env, 0, p_att)
    lim0 = env.inner._p(env.inner._states()[0][0])
    had_prior_engagement = (
        float(np.linalg.norm(p_att - lim0)) <= env.inner.kill_radius)
    assert had_prior_engagement

    # "step 50": 접촉을 떠난 뒤 clean capture
    _move_limiter(env, 0, p_att + np.array([50.0, 0.0, 0.0]))
    lab = _label(env, captured=True)
    assert lab == "NET_CAPTURE", "보상측은 terminal-state 술어다 (docs/66 주 12)"

    # 지표측 규칙 (mission_rollout.py:338): CAPTURED ∧ 이력 집합 비어있지 않음
    metric_label = ("CAPTURE_WITH_CONTACT" if had_prior_engagement
                    else "NET_CAPTURE")
    assert metric_label == "CAPTURE_WITH_CONTACT"

    # divergence 는 보상에서 무해해야 한다 -- 이 등식이 깨지면 label 구현
    # 세부가 policy objective 를 바꾼다 (비준문 Q1 의 근거).
    r = env.reward_spec
    assert r.terminal(lab) == r.terminal(metric_label) == B_NET
