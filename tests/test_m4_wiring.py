"""P33–P36: M4 학습 배선 (docs/32 [D]).

torch 없이 검증 가능한 부분만 본다 -- 환경 조립 · 관측 폭 · regime 분류 ·
mission_rollout 의 policy 훅이 기본 경로를 바꾸지 않는지.
학습기 자체(train_m4.py)는 torch 가 필요하므로 서버 스모크에서 확인한다.
"""
from __future__ import annotations

from collections import Counter

import pathlib

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


# ─────────────────────────────────────────────────────────────────────────
# P46 / P47 — 2026-08-03 파일럿에서 드러난 평가 경로 결함
# ─────────────────────────────────────────────────────────────────────────
def _runner(seed=0, steps=1024):
    import yaml

    from shepherd.scripts.train_m4 import (M4Runner, build_parser_defaults,
                                           build_specs)
    d = build_parser_defaults()
    cfg = yaml.safe_load(open(pathlib.Path(d.config)))
    cfg["loop"]["total_env_steps"] = steps
    return M4Runner(cfg, seed, "cpu", **build_specs(d))


@pytest.mark.torch
def test_p46_policy_actions_match_the_env_action_boxes():
    """★ 정책이 내는 행동이 env Box 모양과 **정확히** 같아야 한다.

    2026-08-03: 안 같았다. 정책 출력은 LIVE 차원(limiter 3 / finisher 4)이고 env Box 는
    4 / 5 인데, 학습 롤아웃만 `adapter.step` 에서 패딩하고(adapter.py:90) 평가 경로
    `run_episode(policy=...)` 는 안 했다. finisher 의 발사 비트가 env idx4 대신
    idx3(예약 slew)으로 들어가 **발사가 env 에 한 번도 닿지 않았다.**

    증상은 조용했다 -- 예외가 아니라 `무력화 0.000 / 침투 1.000 / SPENT_FAIL 0` 이라
    "학습이 안 됐다"로 읽혔다. 파일럿 3런 15시간이 그렇게 갔다. 이 한 줄이면 잡혔다.
    """
    from shepherd.m4_env import build_m4_env
    from shepherd.train.action_dims import M4_LIVE_DIMS
    from shepherd.train.adapter import ShepherdAdapter

    r = _runner()
    st = build_m4_env(r.eval_seed0, 0, **r._m4)
    # 어댑터는 M4 프로파일이어야 한다 (결함 2). 기본 프로파일을 심으면 정책이 내는
    # 4 차원 limiter 행동과 패딩 기대치(3)가 갈라져 여기서 즉시 걸린다 -- 그 자체가
    # 이 배선의 방어선이다. P48 이 프로파일 정합을 따로 못박는다.
    r._adapter = ShepherdAdapter(st.env, M4_LIVE_DIMS)

    acts = r.policy_fn()(st.env.reset(seed=0)[0][r._adapter.limiter_ids[0]], {})
    assert set(acts) == set(r._adapter.limiter_ids) | {r._adapter.finisher_id}
    for aid, a in acts.items():
        want = st.env.action_space(aid).shape
        assert np.asarray(a).shape == want, f"{aid}: {np.asarray(a).shape} != {want}"

    # env 가 실제로 받아 주는가 (모양만 맞고 범위가 틀리면 여기서 걸린다)
    acts[st.env.adversary_id] = np.zeros(3, np.float32)
    st.env.step(acts)


@pytest.mark.torch
def test_p47_evaluation_is_sampled_but_reproducible():
    """평가는 표본추출이되 시드 고정으로 재현돼야 한다 (docs/47 평가 프로토콜).

    `deterministic=True` 는 이진 행동을 `probs > 0.5` 로 자른다. 발사·커밋은 에피소드당
    한 번 하는 행동이라 올바른 정책일수록 스텝당 확률이 낮고, 그 문턱은 그런 정책을
    **구조적으로** 버린다 (파일럿 s1 이 p=0.0002 를 배웠고 한 발도 못 쐈다).
    표본추출로 바꾸되 재현성은 `torch.manual_seed(eval_seed0)` 로 지킨다.
    """
    import inspect

    from shepherd.scripts.train_m4 import M4Runner

    src = inspect.getsource(M4Runner.evaluate)
    assert "torch.manual_seed(self.eval_seed0)" in src, "평가 시드 고정이 빠졌다"
    assert M4Runner.policy_fn.__defaults__ == (False,), \
        "policy_fn 기본이 결정론으로 되돌아갔다"

    r = _runner()
    a = r.evaluate(6)
    b = r.evaluate(6)
    assert a["counts"] == b["counts"], "같은 시드인데 평가가 재현되지 않는다"


# ─────────────────────────────────────────────────────────────────────────
# P48 — 2026-08-03 결함 2: 커밋 비트가 정책 손에 있는가
#
# 결함 1(P46)과 같은 부류의 네 번째 사례다: **미사용으로 문서화된 슬롯을 새 기능이
# 재사용했는데 소비자 한 곳이 안 따라왔다.** docs/29 §3.1 은 limiter Box(4) idx 3 을
# 커밋 비트로 선언했지만 `action_dims.LIVE_DIMS` 는 M4 이전 주석 그대로 그 자리를
# RESERVED 로 두고 있었고, `pad_env_action` 이 거기에 0 을 넣었다. 결과:
# **정책은 커밋을 켤 수단이 없었다** -- 학습 중에도, 평가에서도.
#
# 이것이 스윕의 주축을 죽인다. `w_kill` 은 종말 보상에만 들어가고
# (HARD_KILL = b_net·(1−w_kill)) 하드킬이 불가능하면 도달 불가능한 결과의 보상만
# 바꾼다 -- 5×5×2 스윕에서 `w_kill` 축 전체가 불활성이고 2차 지표는 자명하게 1.00.
# 파일럿 3런의 `shape_hk = 0` 은 탐색 실패가 아니라 이것이다.
#
# 그래서 문서가 아니라 테스트로 못 박는다.
# ─────────────────────────────────────────────────────────────────────────
def test_p48a_commit_bit_survives_padding_and_reaches_the_env():
    """★ 정책이 켠 커밋 비트가 env 의 방아쇠까지 **살아서** 도착해야 한다.

    torch 없이 검증한다 -- 배선의 핵심은 액터가 아니라 프로파일과 패딩이다.
    기본 프로파일로 같은 행동을 보내면 커밋이 **사라진다**는 것도 같이 확인한다
    (그게 결함 2 의 정확한 형태이므로, 대조 없이 통과하면 의미가 없다).
    """
    from shepherd.train.action_dims import (LIVE_DIMS, M4_LIVE_DIMS,
                                            pad_env_action)
    from shepherd.train.adapter import ShepherdAdapter

    st = build_m4_env(0, 0, **KW)
    env = st.env
    assert env.spec.enabled, "M4 방아쇠가 꺼져 있으면 이 테스트는 무의미하다"

    ad = ShepherdAdapter(env, M4_LIVE_DIMS)
    assert ad.live_dim(ad.limiter_ids[0]) == 4, "M4 프로파일에서 limiter live = 4"

    # 커밋 비트만 1, 나머지 0. 어댑터 패딩을 거쳐 env 로 들어간다.
    ad.reset(seed=0)
    live = {lid: np.array([0., 0., 0., 1.], np.float32) for lid in ad.limiter_ids}
    live[ad.finisher_id] = np.zeros(4, np.float32)
    ad.step(live)
    assert len(env.commits) == len(ad.limiter_ids), \
        f"커밋 제안이 env 에 도착하지 않았다 (commits={len(env.commits)})"

    # 대조: 기본 프로파일은 idx 3 을 0 으로 덮는다 = 결함 2 의 형태
    st2 = build_m4_env(0, 0, **KW)
    ad2 = ShepherdAdapter(st2.env)                    # 기본 프로파일
    assert ad2.live_dim(ad2.limiter_ids[0]) == 3
    ad2.reset(seed=0)
    ad2.step({**{lid: np.zeros(3, np.float32) for lid in ad2.limiter_ids},
              ad2.finisher_id: np.zeros(4, np.float32)})
    assert len(st2.env.commits) == 0, \
        "기본 프로파일에서 커밋이 걸렸다 -- 대조가 성립하지 않는다"

    # 그리고 패딩 자체의 대수적 형태
    a = np.array([1., 2., 3., 1.], np.float32)
    assert pad_env_action("limiter_0", a, M4_LIVE_DIMS)[3] == 1.0
    assert pad_env_action("limiter_0", a[:3], LIVE_DIMS)[3] == 0.0


def test_p48b_default_profile_is_untouched():
    """M2/M3 는 이 변경에 **닿지 않아야** 한다 (LIVE_DIMS 는 전역이다)."""
    from shepherd.train.action_dims import LIVE_DIMS, M4_LIVE_DIMS, live_action_dim

    assert LIVE_DIMS["limiter"] == (4, (0, 1, 2)), "기본 프로파일이 오염됐다"
    assert M4_LIVE_DIMS["limiter"] == (4, (0, 1, 2, 3))
    # 나머지 역할은 두 프로파일에서 동일해야 한다 (role_of 가 기본 맵으로 검증한다)
    assert set(LIVE_DIMS) == set(M4_LIVE_DIMS)
    for role in ("finisher", "adversary"):
        assert LIVE_DIMS[role] == M4_LIVE_DIMS[role]
    # dims 인자를 안 주면 기존 동작 그대로
    assert live_action_dim("limiter_0") == 3
    assert live_action_dim("limiter_0", M4_LIVE_DIMS) == 4


@pytest.mark.torch
def test_p48c_trainer_actor_matches_the_profile():
    """액터 구조 · 버퍼 폭 · 스케일이 한 몸으로 움직여야 한다.

    폭이 갈라지면 조용히 틀린 차원을 학습하게 되므로 **큰 소리로** 죽어야 한다.
    """
    import torch

    from shepherd.train.mappo import (GaussianActor, MAPPOConfig, MAPPORollout,
                                      MAPPOTrainer, MixedActor)

    # 기본(M2/M3): Gaussian 3 차원
    base = MAPPOTrainer(8, 2, MAPPOConfig(hidden_sizes=(8, 8)))
    assert isinstance(base.lim_actor, GaussianActor) and base.lim_dim == 3
    assert MAPPOConfig().limiter_commit is False, "기본이 커밋 ON 으로 뒤집혔다"

    # M4: Mixed(연속 3 + Bernoulli 1)
    m4 = MAPPOTrainer(8, 2, MAPPOConfig(hidden_sizes=(8, 8), limiter_commit=True))
    assert isinstance(m4.lim_actor, MixedActor) and m4.lim_dim == 4
    raw, logp = m4.lim_actor.act(torch.zeros(2, 8 + 2))
    assert raw.shape == (2, 4) and logp.shape == (2,)
    assert set(np.unique(raw[:, 3].numpy())) <= {0.0, 1.0}, "커밋 비트가 {0,1} 이 아니다"

    # 폭 불일치는 조용히 지나가지 않는다
    bad = MAPPORollout(4, 8, 2, lim_dim=3)
    bad._i = bad.size
    with pytest.raises(ValueError, match="lim_dim"):
        m4.update(bad)


@pytest.mark.torch
def test_p48d_m4_runner_is_wired_end_to_end():
    """러너 조립 -> 롤아웃 -> 갱신까지 커밋 차원이 한 폭으로 흐르는가."""
    from shepherd.train.action_dims import M4_LIVE_DIMS

    r = _runner(steps=256)
    assert r.tr.cfg.limiter_commit is True, "M4 기본은 커밋 live 다"
    assert r.tr.lim_dim == 4 == r.buf.lim_dim
    assert r.lim_scale.shape == (4,) and np.isclose(r.lim_scale[3], 1.0), \
        "커밋 비트 스케일은 1.0 이어야 env 의 commit_threshold=0.5 와 맞물린다"

    r.collect_rollout()
    assert r._adapter.live_dims is M4_LIVE_DIMS, "롤아웃 어댑터가 기본 프로파일이다"
    assert r.buf.lim_raw.shape[-1] == 4
    # 커밋 비트는 클립되지 않고 {0,1} 그대로 저장돼야 한다 (finisher 발사와 같은 규약)
    bits = r.buf.lim_raw[..., 3]
    assert set(np.unique(bits)) <= {0.0, 1.0}
    assert np.allclose(r.buf.lim_clip[..., 3], bits)

    stats = r.update()
    assert "limiter/commit_rate" in stats, "커밋 진단 지표가 빠졌다"
    assert 0.0 <= stats["limiter/commit_rate"] <= 1.0
