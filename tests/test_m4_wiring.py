"""P33–P36: M4 학습 배선 (docs/32 [D]).

torch 없이 검증 가능한 부분만 본다 -- 환경 조립 · 관측 폭 · regime 분류 ·
mission_rollout 의 policy 훅이 기본 경로를 바꾸지 않는지.
학습기 자체(train_m4.py)는 torch 가 필요하므로 서버 스모크에서 확인한다.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_config import THREAT_BRACKET, m4_config
from shepherd.m4_env import build_m4_env, mission_eval, regime_of
from shepherd.obs_threat import threat_features
from shepherd.spawn_rand import SpawnSpec

KW = dict(system=SystemSpec(enabled=True),
          reward=RewardSpec(w_kill=0.5, enabled=True),
          attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
          spawn=SpawnSpec())


def test_p33_stack_builds_and_steps():
    st = build_m4_env(0, 0, **KW)
    env = st.env
    a0 = env.possible_agents[0]
    obs, _ = env.reset(seed=0)
    acts = {aid: np.zeros(env.action_space(aid).shape, np.float32) for aid in env.agents}
    for _ in range(5):
        o, r, te, tr, info = env.step(acts)
    assert o[a0].shape == obs[a0].shape
    # M4 info 가 실제로 주입되는가
    fi = info[env.finisher_id]
    for k in ("m4_outcome", "hard_kill", "n_committed", "veto_events"):
        assert k in fi


def test_p34_threat_obs_width_and_ablation():
    """위협 관측은 정확히 2차원을 더하고, ablation 은 원폭을 유지한다."""
    on = build_m4_env(0, 0, threat_obs=True, **KW).env
    off = build_m4_env(0, 0, threat_obs=False, **KW).env
    a0 = on.possible_agents[0]
    d_on = on.observation_space(a0).shape[0]
    d_off = off.observation_space(a0).shape[0]
    assert d_on - d_off == len(THREAT_BRACKET) == 2
    # state() 도 같이 확장 (CTDE 일관성)
    on.reset(seed=0); off.reset(seed=0)
    assert on.state().shape[0] - off.state().shape[0] == 2
    # 관측 뒤 2차원이 실제 위협 특징인가
    obs, _ = on.reset(seed=0)
    st = build_m4_env(0, 0, threat_obs=True, **KW)
    want = threat_features((st.threat["a_att"], st.threat["att_speed"]),
                           (THREAT_BRACKET["physics.a_att_max"],
                            THREAT_BRACKET["physics.att_speed"]))
    assert np.allclose(obs[a0][-2:], want, atol=1e-6)
    assert np.all(np.abs(obs[a0][-2:]) <= 1.0 + 1e-6)      # 브래킷 안이면 [-1,1]


def test_p35_regime_split_is_balanced():
    """★ 랜덤화가 두 regime 을 모두 만들어내야 한다 (docs/40 §8.1)."""
    regs = []
    for ep in range(60):
        st = build_m4_env(0, ep, **KW)
        regs.append(regime_of(st.threat["a_att"], st.threat["tau"],
                              st.threat["net_radius"]))
    c = Counter(regs)
    assert set(c) == {"FREE_CAPTURE", "SHAPING_NEEDED"}, f"한 regime 뿐: {c}"
    frac = c["SHAPING_NEEDED"] / len(regs)
    assert 0.2 < frac < 0.8, f"regime 이 한쪽으로 쏠린다: {frac:.2f}"


def test_p35b_regime_boundary_matches_proposition_N():
    cfg = m4_config()
    tau, rho = cfg["physics"]["tau_deploy"], cfg["physics"]["net_radius"]
    a_star = 2 * rho / tau ** 2
    assert regime_of(a_star * 0.99, tau, rho) == "FREE_CAPTURE"
    assert regime_of(a_star * 1.01, tau, rho) == "SHAPING_NEEDED"


def test_p36_policy_hook_is_a_no_op_when_absent():
    """★ mission_rollout 에 policy 를 안 주면 기존 경로와 완전히 같아야 한다."""
    from shepherd.scripts.mission_rollout import run_episode

    def roll():
        st = build_m4_env(0, 3, **KW)
        return run_episode(st.env, st.scn, st.lay, seed=3,
                           limiter_mode="ring", fire_mode="clean")

    a, b = roll(), roll()
    assert a.label == b.label and a.steps == b.steps
    assert a.min_target_dist == b.min_target_dist
    assert a.contact_steps == b.contact_steps


def test_p36b_policy_hook_runs():
    """policy 를 주면 그 행동이 실제로 쓰인다."""
    from shepherd.scripts.mission_rollout import run_episode

    st = build_m4_env(0, 3, **KW)
    env = st.env
    calls = {"n": 0}

    def policy(obs, flags):
        calls["n"] += 1
        acts = {lid: np.zeros(env.action_space(lid).shape, np.float32)
                for lid in env.limiter_ids}
        acts[env.finisher_id] = np.zeros(env.action_space(env.finisher_id).shape,
                                         np.float32)
        return acts

    r = run_episode(env, st.scn, st.lay, seed=3, policy=policy)
    assert calls["n"] == r.steps > 0
    assert r.fire_step is None          # 발사 로짓 0 -> 절대 안 쏜다


def test_p37_mission_eval_shape():
    """2층 지표가 regime 별로 쪼개져 나오는가."""
    out = mission_eval(0, 6, limiter_mode="ring", **KW)
    for k in ("penetrated_rate", "neutralized_rate", "spent_fail_rate",
              "truncated_rate", "nondestructive_frac", "by_regime"):
        assert k in out
    # interdiction = 1 - penetrated 를 그대로 쓰지 않는다는 것이 요점
    assert out["neutralized_rate"] + out["penetrated_rate"] \
        + out["spent_fail_rate"] + out["truncated_rate"] == pytest.approx(1.0)
    assert set(out["by_regime"]) <= {"FREE_CAPTURE", "SHAPING_NEEDED"}


# ------------------------------------------------- P40 선언값 그림자 금지 --
def test_p40_trainer_defaults_match_declaration():
    """CLI 기본값이 선언(SystemSpec)을 조용히 덮어쓰지 않는다.

    2026-08-01: `--tau-kill` 기본이 0.1 로 하드코딩돼 있어 docs/42 에서 0.15 로
    재선언한 값을 스윕 내내 덮어쓸 뻔했다. 선언은 한 군데여야 한다.
    """
    from shepherd.env_sys import SystemSpec
    from shepherd.scripts.train_m4 import build_parser_defaults, build_specs

    d = SystemSpec()
    args = build_parser_defaults()
    specs = build_specs(args)
    assert specs["system"].tau_kill == d.tau_kill
    assert specs["system"].p_kill == d.p_kill
    assert specs["system"].r_nk == d.r_nk


def test_p40b_explicit_flag_still_overrides():
    """축을 명시하면 그대로 먹는다 (sweep 축 {0.15, 0.20})."""
    from shepherd.scripts.train_m4 import build_parser_defaults, build_specs
    args = build_parser_defaults()
    args.tau_kill = 0.20
    assert build_specs(args)["system"].tau_kill == 0.20


def test_p40c_reward_defaults_match_declaration():
    """RewardSpec 도 같은 규율. 2026-08-01: 정반대 방향으로 갈라져 있었다.

    `terminal_scale` 은 docs/41 [E] 스모크에서 1.0 으로 선언됐는데 dataclass 기본이
    10.0 으로 남아 CLI 만 1.0 을 들고 있었다. 즉 `RewardSpec()` 을 직접 만드는 모든
    호출부(계측 스크립트·게이트)가 선언 이전 값을 받고 있었다.
    """
    from shepherd.env_sys import RewardSpec
    from shepherd.scripts.train_m4 import build_parser_defaults, build_specs

    d = RewardSpec()
    specs = build_specs(build_parser_defaults())
    assert specs["reward"].terminal_scale == d.terminal_scale
    assert specs["reward"].dense_scale == d.dense_scale
    assert specs["reward"].enabled is True, "학습기는 M4 보상을 켜야 한다"
    assert d.terminal_scale == 1.0, "docs/41 [E] 선언값"


def test_p40d_reward_enabled_does_not_change_labels():
    """`RewardSpec.enabled` 는 보상만 바꾼다 -- 임무 라벨(=기저선)에 영향이 없어야 한다.

    기저선(results/hold_baseline.json)이 enabled=False 로 측정됐어도 유효함을 강제한다.
    """
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.m4_env import mission_eval
    from shepherd.spawn_rand import SpawnSpec

    kw = dict(system=SystemSpec(),
              attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
              spawn=SpawnSpec(), limiter_mode="hold")
    off = mission_eval(0, 12, reward=RewardSpec(w_kill=0.5, enabled=False), **kw)
    on = mission_eval(0, 12, reward=RewardSpec(w_kill=0.5, enabled=True), **kw)
    assert off["counts"] == on["counts"]
    assert off["by_regime"] == on["by_regime"]


def test_p40e_scale_smoke_runs_the_same_baseline_as_run_episode():
    """★ [E] 스케일 스모크가 `run_episode` 와 **같은 행동 분포**로 도는가.

    2026-08-03: 안 돌고 있었다. 커밋 비트는 limiter 행동 벡터 idx3 에 실려 있고
    `run_episode` 는 `_zero_commit` 으로 눌러 두는데(정정 3 의 수정), `scale_smoke.
    _episode` 는 그 수정을 못 받았다. `ring` 이 네 대 모두 idx3=1 을 내보내므로
    [E] 의 ring 은 게이트·기저선의 ring 과 다른 것이었다 (sum|dense| 1.044 vs 1.328).

    선언값은 안 바뀌었다 -- 반올림 경계 3.16 에 한참 못 미친다. 그래도 "같은
    기준선이라고 주장하는 두 함수가 다르게 돈다"는 것 자체가 정정 3·6·8 과 같은
    부류라 여기 못 박는다.
    """
    from shepherd.scripts import scale_smoke as ss
    from shepherd.scripts.mission_rollout import _limiter_actions

    # (1) 가드가 **실제 경로에서 실행**되는가 (소스에만 있는 게 아니라)
    calls = []
    orig = ss._zero_commit
    ss._zero_commit = lambda acts: (calls.append(1), orig(acts))[1]
    try:
        ss._episode(0, 0, 0.5, "ring")
    finally:
        ss._zero_commit = orig
    assert calls, "_episode 가 커밋 비트를 누르지 않는다"

    # (2) 가드가 **필요한가** -- ring 이 정말 1 을 내보내는지. 이게 0 이 되면
    #     (1) 은 통과하면서 무의미해지므로 같이 고정한다.
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.m4_env import build_m4_env
    from shepherd.spawn_rand import SpawnSpec

    st = build_m4_env(0, 0, system=SystemSpec(), reward=RewardSpec(w_kill=0.5),
                      attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                      spawn=SpawnSpec())
    st.env.reset(seed=0)
    lims, _, att = st.env._states()
    acts = _limiter_actions(st.env, st.scn, st.lay, "ring", lims,
                            st.env._p(att), st.env._v(att))
    assert all(float(v[3]) == 1.0 for v in acts.values()), \
        "ring 이 더 이상 커밋 비트를 안 싣는다 -- 가드가 무의미해졌으니 재검토"

    orig(acts)
    assert all(float(v[3]) == 0.0 for v in acts.values())
