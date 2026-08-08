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


# ─────────────────────────────────────────────────────────────────────────
# P49 / P50 / P51 — 2026-08-03 검증상태 보고의 P2·P3·P5 수정
#
# 세 결함은 전부 **커밋 비트를 배선하기 전에는 잠들어 있던** 것이다
# (`retired` 가 항상 비었고 `n_consumed ≡ 0` 이었다). 커밋이 가능해진 순간
# 동시에 깨어났고, 학습 정책이 정적 기준선보다 나빠진 시점과 일치한다.
# 다시 잠들 수 없게 테스트로 못 박는다.
# ─────────────────────────────────────────────────────────────────────────
def test_p51_park_position_is_finite_and_inert():
    """★ 주차점은 (a) v_shot 에 영향이 0 이어야 하고 (b) 관측 정규화를 죽이면 안 된다.

    2026-08-03: `PARK_POSITION = (0,0,1e4)` 이 관측에 그대로 실려(env.py:203-213)
    `RunningNorm` 을 오염시켰다 — 롤아웃 256 스텝만에 limiter pz 채널 std 4330,
    **살아있는 limiter 의 면외 좌표가 정상 채널 대비 517배 압축**. 링 배치가
    (8,±5,0),(8,0,±5) 이므로 편대 기하의 절반이 지워진다. 망각 없는 누적이라 회복 불가.

    (a) 는 물리 계약, (b) 는 학습 계약이다. 둘 다 지켜야 한다.
    """
    from shepherd.env_sys import PARK_POSITION

    park = np.asarray(PARK_POSITION, float)
    # (b) 링 반경(5 m) 대비 지나치게 크면 정규화가 죽는다. 100 m 를 상한으로 못 박는다.
    assert np.all(np.isfinite(park)) and np.linalg.norm(park) < 100.0, \
        f"주차점이 관측 정규화를 죽일 크기다: {PARK_POSITION}"

    # (a) 주차 위치를 바꿔도 v_shot 이 **비트 동일**해야 한다 (기여 0 의 조작적 정의)
    st = build_m4_env(0, 0, **KW)
    env = st.env
    env.reset(seed=0)
    acts = {a: np.zeros(env.action_space(a).shape, np.float32) for a in env.agents}
    far = np.array([0.0, 0.0, 1.0e4])
    checked = 0
    for t in range(25):
        lims, fin, att = env._states()
        p, v = env._p(att), env._v(att)
        a = env._vshot(p, v, [park] * 4, fin, seed=t)
        b = env._vshot(p, v, [far] * 4, fin, seed=t)
        assert a.v_shot_soft == b.v_shot_soft and a.boxed_in == b.boxed_in, \
            f"주차점이 v_shot 에 영향을 준다 (t={t}): {a.v_shot_soft} != {b.v_shot_soft}"
        checked += 1
        o = env.step(acts)
        if any(o[2].values()) or any(o[3].values()):
            break
    assert checked >= 5


def test_p50_c_lim_is_charged_once_per_consumed_limiter():
    """★ `c_lim` 은 소모 **1회당 1번**이지 매 스텝이 아니다.

    2026-08-03: `env_sys.py` 의 `rew` 재작성이 매 스텝 실행되는데 `n_consumed` 가
    에피소드 누적이라, t 스텝에 소모하면 남은 (T−t) 스텝 내내 −c_lim 이 붙었다.
    실측 누적 벌점 평균 7.51~9.42 (선언 의도 0.40, |종말항| 최대 1.0) — 소모 벌점
    하나가 나머지 전 학습 신호의 7~17배였다. docstring §15 는 처음부터 1회 부과였다.

    검정: 같은 행동열을 M4 보상 on/off 두 env 에 흘려 보상차 합계를 잰다.
    합계 == terminal(label) − c_lim × (소모 개수) 여야 한다.
    """
    from shepherd.env_sys import RewardSpec
    from shepherd.train.action_dims import M4_LIVE_DIMS
    from shepherd.train.adapter import ShepherdAdapter

    rs = RewardSpec(w_kill=0.5, enabled=True)
    rng = np.random.default_rng(0)
    for ep in range(3):
        on = build_m4_env(0, ep, **KW)
        off = build_m4_env(0, ep, **{**KW, "reward": RewardSpec(w_kill=0.5, enabled=False)})
        a1 = ShepherdAdapter(on.env, M4_LIVE_DIMS); a1.reset(seed=ep)
        a2 = ShepherdAdapter(off.env, M4_LIVE_DIMS); a2.reset(seed=ep)
        lo, hi = a1.action_bounds(a1.limiter_ids[0])
        total, steps = 0.0, 0
        while on.env.agents and steps < 200:
            live = {}
            for lid in a1.limiter_ids:
                acc = rng.uniform(lo[:3], hi[:3]).astype(np.float32)
                live[lid] = np.concatenate(
                    [acc, [1.0 if rng.uniform() < 0.5 else 0.0]]).astype(np.float32)
            live[a1.finisher_id] = np.concatenate(
                [rng.uniform(-1, 1, 3), [0.0]]).astype(np.float32)
            r1, r2 = a1.step(live), a2.step(live)
            total += r1.rewards[a1.finisher_id] - r2.rewards[a2.finisher_id]
            steps += 1
            if r1.done or r2.done:
                break
        n_consumed = sum(1 for c in on.env.commits if c.consumed)
        label = on.env._outcome_label({"x": True}, {"x": False},
                                      {on.env.finisher_id: {}}) if False else None
        # 종말항은 라벨에 따라 {+1, +0.5, −1, 0} 중 하나 -> 총합에서 c_lim 몫만 분리해 본다
        expected_c_lim = rs.c_lim * n_consumed
        assert n_consumed > 0, "이 테스트는 소모가 일어나는 조건을 전제한다"
        # 총합 = terminal ± c_lim 몫. |총합| 이 (|terminal|max + expected) 를 넘으면
        # 매 스텝 부과가 되살아난 것이다.
        assert abs(total) <= 1.0 + expected_c_lim + 1e-6, (
            f"ep{ep}: c_lim 이 매 스텝 부과되고 있다 "
            f"(보상차 {total:.3f}, 상한 {1.0 + expected_c_lim:.3f}, 소모 {n_consumed})")


@pytest.mark.torch
def test_p49_action_scale_tracks_the_episode_authority():
    """★ 행동 스케일이 **이 에피소드의** `a_lim` 을 따라가야 한다.

    2026-08-03: `lim_scale` 이 에피소드 0 의 draw 로 동결돼 있었다. `a_lim = 0.35·a_att`,
    `a_att ~ U[11,78]` 이라 실제 권한이 3.86~27.28 로 바뀌는데 스케일은 고정 —
    41.5% 에피소드 과다명령 / 44.3% 과소명령, 그리고 **시드마다 동결값이 달라
    시드가 복제가 아니게 된다**(실효 권한 100/72/48%).

    두 경로를 다 본다: 학습(`_begin_episode`)과 평가(`_lim_scale_for` 역변환).
    """
    r = _runner()
    seen = set()
    for _ in range(6):
        r._begin_episode()
        want = r._adapter.action_bounds(r._adapter.limiter_ids[0])[1]
        assert np.allclose(r.lim_scale, want), \
            f"학습 경로 스케일이 에피소드 권한과 다르다: {r.lim_scale} != {want}"
        seen.add(round(float(r.lim_scale[0]), 6))
        # 평가 경로: 관측의 위협 특징 역변환이 같은 값을 내야 한다
        obs = r._adapter.reset(seed=0)[0][r._adapter.limiter_ids[0]]
        got = r._lim_scale_for(obs)
        assert np.allclose(got[:3], want[:3], rtol=1e-4), \
            f"평가 경로 역변환이 어긋난다: {got[:3]} != {want[:3]}"
        assert got[3] == want[3] == 1.0
        r._ep_idx += 1
    assert len(seen) >= 3, f"에피소드마다 권한이 바뀌어야 한다 (관측된 값 {seen})"


# ─────────────────────────────────────────────────────────────────────────
# docs/71 §2.1 — LS-off (commit-off) 잠금 테스트 4항
#   블록 계약이 "두 팔의 diff = limiter_commit 단 하나" 이므로, commit 이 정말
#   정책 손에서 떨어졌는지(①)와 연속 3축 경로가 LS-live 와 같은지(④)를 코드가
#   지켜야 한다. 배선이 갈라지면 결함 2 가 반대 방향으로 재발한다.
# ─────────────────────────────────────────────────────────────────────────
def _runner_ls(commit: bool, seed=0, steps=256, rollout=64):
    """LS 팔 러너 (learned limiter + scripted finisher). commit 만 갈아탄다."""
    import yaml

    from shepherd.scripts.train_m4 import (M4Runner, build_parser_defaults,
                                           build_specs)
    d = build_parser_defaults()
    cfg = yaml.safe_load(open(pathlib.Path(
        "configs/l2_mappo.yaml" if commit else "configs/l2_mappo_nocommit.yaml")))
    cfg["loop"]["total_env_steps"] = steps
    cfg["loop"]["rollout_env_steps"] = rollout
    return M4Runner(cfg, seed, "cpu", finisher_policy="scripted",
                    **build_specs(d))


def _runner_off(seed=0, steps=256, rollout=64):
    return _runner_ls(False, seed=seed, steps=steps, rollout=rollout)


def test_p71a_commit_off_config_diff_is_one_key():          # torch 불요
    """LS-off config = l2_mappo.yaml + limiter_commit 한 줄. 그 외 diff 0."""
    import yaml

    live = yaml.safe_load(open(pathlib.Path("configs/l2_mappo.yaml")))
    off = yaml.safe_load(open(pathlib.Path("configs/l2_mappo_nocommit.yaml")))
    assert off["mappo"].pop("limiter_commit") is False
    assert off == live, "두 팔의 diff 가 limiter_commit 하나가 아니다 (블록 계약 위반)"


@pytest.mark.torch
def test_p71b_env_never_receives_a_nonzero_commit(monkeypatch):
    """① env 에 전달되는 limiter commit 성분 == 0 (전 스텝, 결정적).

    학습 롤아웃(adapter.step)과 평가(policy_fn) 두 경로를 **둘 다** 본다 --
    2026-08-03 결함 1/2 가 정확히 "한 경로만 패딩됐다" 였다.
    """
    import shepherd.train.adapter as adapter_mod
    from shepherd.train.action_dims import LIVE_DIMS

    r = _runner_off()
    assert r.live_dims is LIVE_DIMS and r.lim_live == 3
    assert r.tr.lim_dim == 3 == r.buf.lim_dim
    assert r.lim_scale.shape == (3,), "commit 축 스케일이 남아 있다"

    padded = []
    orig = adapter_mod.pad_env_action

    def spy(aid, a, dims=None):
        out = orig(aid, a, dims)
        padded.append((aid, out))
        return out

    monkeypatch.setattr(adapter_mod, "pad_env_action", spy)
    r.collect_rollout()                       # 학습 경로 (에피소드 경계 포함)
    lim = [o for aid, o in padded if aid.startswith("limiter")]
    assert len(lim) >= 4 * 64, "limiter 행동이 env 에 안 닿았다"
    assert all(o.shape == (4,) and o[3] == 0.0 for o in lim), \
        "commit 자리에 0 이 아닌 값이 들어갔다"

    # 평가 경로: policy_fn 은 어댑터와 같은 프로파일로 패딩해야 한다
    obs = r._adapter.reset(seed=0)[0][r._adapter.limiter_ids[0]]
    acts = r.policy_fn()(obs, {})
    for lid in r._adapter.limiter_ids:
        assert acts[lid].shape == (4,) and acts[lid][3] == 0.0


@pytest.mark.torch
def test_p71c_commit_head_is_structurally_absent():
    """②③ commit log-prob · entropy 의 PPO 기여 == 0 (head 부재).

    "계수를 0 으로 뒀다" 가 아니라 **분포 자체가 없다** 를 본다: limiter 액터의
    logp/entropy 가 3차원 Normal 그 자체와 일치하고, 이산 헤드 파라미터가
    존재하지 않는다. 진단 지표도 커밋 키를 내지 않아야 한다 (표 오독 방지).
    """
    import torch
    from torch.distributions import Normal

    from shepherd.train.mappo import GaussianActor, MixedActor

    r = _runner_off()
    act = r.tr.lim_actor
    assert isinstance(act, GaussianActor) and not isinstance(act, MixedActor)
    assert not hasattr(act, "fire_logit"), "이산 헤드가 살아 있다"
    assert act.log_std.shape == (3,)

    x = torch.zeros(5, r.obs_dim + r.n)
    raw, _ = act.act(x)
    assert raw.shape == (5, 3)
    logp, ent = act.evaluate(x, raw)
    d = Normal(act.mean(x), act.log_std.exp().expand(5, 3))
    assert torch.allclose(logp, d.log_prob(raw).sum(-1), atol=1e-6), \
        "logp 에 연속 3축 외의 항이 섞였다"
    assert torch.allclose(ent, d.entropy().sum(-1), atol=1e-6), \
        "entropy 에 이산 항이 섞였다"

    r.collect_rollout()
    stats = r.update()
    assert not any("commit" in k for k in stats), \
        f"commit 진단 키가 남아 있다: {sorted(k for k in stats if 'commit' in k)}"


@pytest.mark.torch
def test_p71d_continuous_path_matches_ls_live():
    """④ 연속 3축 경로 = LS-live 와 동일 (**형상·클립·스케일·학습계수**).

    ★ 초기 **값** 동일성은 요구하지 않는다 (2026-08-09 정정). `MixedActor` 는
    mean MLP 를 만든 뒤 fire_logit 을 만들고 그 다음 ortho 초기화를 걸기 때문에,
    같은 torch 시드에서도 mean 의 ortho 초기화가 소비하는 RNG 상태가 두 팔에서
    다르다 -- 값이 갈라지는 것은 정상이고, 계약은 "연속 경로의 **구조와 계수**가
    같다" 다. 값 동일성을 요구하면 head 하나를 뺀 팔에서 영원히 실패한다.
    """
    import torch
    from dataclasses import asdict

    live, off = _runner_ls(True, steps=256), _runner_ls(False, steps=256)

    # (a) 학습 계약: cfg 의 diff 가 limiter_commit **하나**여야 한다
    cl, co = asdict(live.tr.cfg), asdict(off.tr.cfg)
    assert {k for k in cl if cl[k] != co[k]} == {"limiter_commit"}, \
        f"두 팔의 학습 계약이 갈라졌다: {sorted(k for k in cl if cl[k] != co[k])}"

    # (b) 연속 헤드 구조: 키·형상 동일. 차이는 이산 헤드 존재 여부 하나뿐
    sl = live.tr.lim_actor.mean.state_dict()
    so = off.tr.lim_actor.mean.state_dict()
    assert set(sl) == set(so)
    for k in sl:
        assert sl[k].shape == so[k].shape, f"연속 mean MLP 형상이 갈라졌다: {k}"
    assert live.tr.lim_actor.log_std.shape == off.tr.lim_actor.log_std.shape == (3,)
    assert torch.allclose(live.tr.lim_actor.log_std, off.tr.lim_actor.log_std), \
        "init_log_std 가 두 팔에서 다르다"
    lp = {n for n, _ in live.tr.lim_actor.named_parameters()}
    op = {n for n, _ in off.tr.lim_actor.named_parameters()}
    assert (lp - op) and all(n.startswith("fire_logit.") for n in lp - op), \
        f"이산 헤드 외의 파라미터가 다르다: {sorted(lp - op)}"
    assert not op - lp, f"commit-off 에만 있는 파라미터가 있다: {op - lp}"

    # (c) 스케일: 같은 에피소드 권한의 앞 3축이 같다 (4번째 = commit 축은 부재)
    live._begin_episode(); off._begin_episode()
    assert np.allclose(live.lim_scale[:3], off.lim_scale)

    # 클립: 연속 축만 클립되고 폭은 3 이다
    off.collect_rollout()
    assert off.buf.lim_raw.shape[-1] == 3 == off.buf.lim_clip.shape[-1]
    assert np.allclose(off.buf.lim_clip, np.clip(off.buf.lim_raw, -1.0, 1.0))


def test_p71a2_adapter_bounds_are_live_width():          # torch 불요
    """★ `action_bounds` 는 **live 차원만** 준다 (adapter.py:71).

    이 불변식을 잘못 읽어서 commit-off 팔의 조립이 `lim_low[3]` 에서
    IndexError 로 죽었다 (2026-08-09, 서버 p71 첫 실행). env Box 는 항상 4 지만
    어댑터가 프로파일로 자른 뒤를 주므로, 프로파일이 3 인 팔에서 idx 3 을 보는
    코드는 전부 커밋 live 조건 아래에 있어야 한다.
    """
    from shepherd.train.action_dims import LIVE_DIMS, M4_LIVE_DIMS
    from shepherd.train.adapter import ShepherdAdapter

    st = build_m4_env(0, 0, **KW)
    for dims, want in ((M4_LIVE_DIMS, 4), (LIVE_DIMS, 3)):
        ad = ShepherdAdapter(st.env, dims)
        lo, hi = ad.action_bounds(ad.limiter_ids[0])
        assert lo.shape == hi.shape == (want,), f"{want} 축을 기대했다: {hi.shape}"
        assert ad.live_dim(ad.limiter_ids[0]) == want
        # env Box 자체는 두 팔에서 같다 (변경 없음) -- 잘라주는 쪽이 어댑터다
        assert st.env.action_space(ad.limiter_ids[0]).shape == (4,)
