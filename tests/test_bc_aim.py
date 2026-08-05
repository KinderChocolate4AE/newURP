"""P64–P68: 조준 헤드 BC 배선 (docs/49 §5.1).

가장 중요한 것은 **P64** 다. 교사가 기준선과 다른 함수면 BC 는 기준선이 아닌
무언가를 가르치게 되고, 그러면 "조준을 회복했는가" 라는 질문 자체가 성립하지
않는다. docs/48 §3.1 의 한 곳 원칙이 여기에도 그대로 걸린다.
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.spawn_rand import SpawnSpec
from shepherd.train.bc_aim import (AIM_BC_MODES, collect_bc_dataset,
                                   teacher_axis)
from shepherd.scripts.mission_rollout import scripted_role_actions

KW = dict(system=SystemSpec(enabled=True),
          reward=RewardSpec(w_kill=0.5, enabled=True),
          attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
          spawn=SpawnSpec())


# ── P64: 교사는 기준선과 **같은 함수**여야 한다 ─────────────────────────────
def test_p64_teacher_axis_is_the_baseline_axis_bit_identical():
    st = build_m4_env(0, 0, **KW)
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=0)
    fid = env.finisher_id
    seen = 0
    for _ in range(30):
        want = scripted_role_actions(env, scn, lay, roles=("finisher",),
                                     limiter_mode="hold", fire_mode="clean")[fid]
        got = teacher_axis(env)
        assert np.array_equal(got, np.asarray(want, np.float32)[:3]), (got, want)
        assert abs(float(np.linalg.norm(got)) - 1.0) < 1e-5      # 단위벡터
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="never")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        seen += 1
        if (term and term.get(fid)) or (trunc and trunc.get(fid)):
            break
    assert seen >= 5


def test_p64b_axis_does_not_depend_on_the_fire_trigger():
    """축은 `clean_threshold_crossed` 와 무관하다 -- 발사 비트만 바뀐다."""
    st = build_m4_env(0, 0, **KW)
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=0)
    fid = env.finisher_id
    a0 = scripted_role_actions(env, scn, lay, roles=("finisher",),
                               fire_mode="clean", prev_clean=False)[fid]
    a1 = scripted_role_actions(env, scn, lay, roles=("finisher",),
                               fire_mode="clean", prev_clean=True)[fid]
    assert np.array_equal(a0[:3], a1[:3])          # 축 동일
    assert a0[4] != a1[4]                          # 발사 비트만 다르다
    assert np.array_equal(teacher_axis(env), np.asarray(a0, np.float32)[:3])


def test_p64c_dataset_pairs_obs_with_the_same_step_axis():
    """수집 데이터의 X/Y 가 **같은 시점**이어야 한다 (P63b 에서 배운 정렬 문제)."""
    d = collect_bc_dataset(episodes=6, seed0=0)
    assert d["X"].shape[0] == d["Y"].shape[0] == d["ep"].shape[0] > 30
    n = np.linalg.norm(d["Y"], axis=1)
    assert np.allclose(n, 1.0, atol=1e-5)          # 전부 단위벡터
    assert np.all(np.isfinite(d["X"]))
    assert AIM_BC_MODES == ("none", "warm", "aux")


# ── torch 구간 ──────────────────────────────────────────────────────────────
torch = pytest.importorskip("torch")

from shepherd.train.bc_aim import bc_cosine_loss, warmup_aim          # noqa: E402
from shepherd.train.mappo import MAPPOConfig, MAPPORollout, MAPPOTrainer  # noqa: E402
from shepherd.train.obs_norm import RunningNorm                        # noqa: E402

pytestmark_torch = pytest.mark.torch
OBS, N = 12, 3


def _cfg(**kw):
    base = dict(hidden_sizes=(16, 16), epochs=2, minibatch_size=8,
                rollout_steps=16, seed=0, device="cpu")
    base.update(kw)
    return MAPPOConfig.from_dict(base)


def _fill(trainer, size=16, bc=False):
    rng = np.random.default_rng(0)
    buf = MAPPORollout(size, trainer.obs_dim, trainer.n,
                       lim_dim=trainer.lim_dim, bc_dim=3 if bc else 0)
    for _ in range(size):
        obs = rng.normal(size=trainer.obs_dim).astype(np.float32)
        x_l = np.concatenate([np.tile(obs, (trainer.n, 1)),
                              np.eye(trainer.n, dtype=np.float32)], axis=1)
        raw_l, logp_l = trainer.lim_actor.act(torch.as_tensor(x_l))
        raw_f, logp_f = trainer.fin_actor.act(torch.as_tensor(obs[None, :]))
        raw_l, raw_f = raw_l.numpy(), raw_f[0].numpy()
        clip_l = raw_l.copy(); clip_l[:, :3] = np.clip(clip_l[:, :3], -1, 1)
        clip_f = raw_f.copy(); clip_f[:3] = np.clip(clip_f[:3], -1, 1)
        kw = {}
        if bc:
            v = rng.normal(size=3); kw["bc_target"] = (v / np.linalg.norm(v)).astype(np.float32)
        buf.add(**kw, obs=obs, lim_raw=raw_l, lim_clip=clip_l,
                lim_logp=logp_l.numpy(), fin_raw=raw_f, fin_clip=clip_f,
                fin_logp=float(logp_f[0].item()),
                rewards=float(rng.normal()), values=float(rng.normal()),
                next_values=float(rng.normal()), dones=float(rng.integers(0, 2)))
    return buf


@pytest.mark.torch
def test_p65_bc_lambda_defaults_off_and_is_bit_identical():
    assert MAPPOConfig.from_dict({}).bc_lambda == 0.0
    outs = []
    for extra in ({}, {"bc_lambda": 0.0}):
        torch.manual_seed(11)
        tr = MAPPOTrainer(OBS, N, _cfg(limiter_commit=True, **extra))
        s = tr.update(_fill(tr))
        outs.append([p.detach().clone() for p in tr.parameters()])
        assert "finisher/bc_cosine_loss" not in s
    assert all(torch.equal(a, b) for a, b in zip(*outs))
    # bc_dim=0 이면 배열 자체가 없다 (기존 호출부는 메모리도 그대로)
    assert MAPPORollout(4, OBS, N).bc_target is None


@pytest.mark.torch
def test_p65b_bc_lambda_requires_labels_and_a_live_finisher():
    torch.manual_seed(0)
    tr = MAPPOTrainer(OBS, N, _cfg(bc_lambda=0.1))
    with pytest.raises(ValueError, match="bc_target"):
        tr.update(_fill(tr, bc=False))
    torch.manual_seed(0)
    tr2 = MAPPOTrainer(OBS, N, _cfg(bc_lambda=0.1, freeze_finisher=True))
    with pytest.raises(ValueError):
        tr2.update(_fill(tr2, bc=True))


@pytest.mark.torch
def test_p65c_bc_term_pulls_the_aim_head_toward_the_teacher():
    """보조손실이 실제로 조준을 교사 쪽으로 당긴다 (음성 대조: lambda=0 은 안 당긴다)."""
    def _run(lam):
        torch.manual_seed(21)
        tr = MAPPOTrainer(OBS, N, _cfg(bc_lambda=lam, epochs=8))
        buf = _fill(tr, size=32, bc=True)
        obs = torch.as_tensor(buf.obs)
        tgt = torch.as_tensor(buf.bc_target)
        with torch.no_grad():
            before = float(bc_cosine_loss(tr.fin_actor.mean(obs), tgt))
        stats = tr.update(buf)
        with torch.no_grad():
            after = float(bc_cosine_loss(tr.fin_actor.mean(obs), tgt))
        return before, after, stats

    b0, a0, s0 = _run(0.0)
    b1, a1, s1 = _run(1.0)
    assert b0 == pytest.approx(b1)                 # 같은 시드 -> 같은 출발점
    assert a1 < b1 - 1e-4, (b1, a1)                # BC 가 당긴다
    assert a1 < a0                                 # lambda=0 보다 확실히 가깝다
    assert s1["finisher/bc_cosine_loss"] > 0.0 and s1["finisher/bc_lambda"] == 1.0


@pytest.mark.torch
def test_p66_warmup_moves_only_the_aim_head():
    """워밍업은 조준 헤드만 건드린다 -- 발사 헤드·log_std·크리틱·limiter 불변."""
    torch.manual_seed(5)
    tr = MAPPOTrainer(OBS, N, _cfg(limiter_commit=True))
    norm = RunningNorm(OBS)
    rng = np.random.default_rng(0)
    X = rng.normal(size=(256, OBS)).astype(np.float32)
    Y = rng.normal(size=(256, 3)); Y = (Y / np.linalg.norm(Y, axis=1, keepdims=True)).astype(np.float32)

    snap = lambda m: [p.detach().clone() for p in m.parameters()]  # noqa: E731
    b_mean, b_fire = snap(tr.fin_actor.mean), snap(tr.fin_actor.fire_logit)
    b_std = tr.fin_actor.log_std.detach().clone()
    b_crit, b_lim = snap(tr.critic), snap(tr.lim_actor)

    warmup_aim(tr.fin_actor, norm, X, Y, steps=30, seed=0)

    chg = lambda m, b: any(not torch.equal(a, c) for a, c in zip(snap(m), b))  # noqa: E731
    assert chg(tr.fin_actor.mean, b_mean), "조준 헤드가 안 움직였다"
    assert not chg(tr.fin_actor.fire_logit, b_fire), "발사 헤드가 움직였다"
    assert torch.equal(tr.fin_actor.log_std, b_std)
    assert not chg(tr.critic, b_crit) and not chg(tr.lim_actor, b_lim)


@pytest.mark.torch
def test_p67_warmup_reaches_the_teacher_on_real_data():
    """실제 궤적에서 워밍업이 교사 축에 근접한다 (docs/49 §1.1 의 상한 근처)."""
    st = build_m4_env(0, 0, **KW)
    obs_dim = st.env.observation_space(st.env.possible_agents[0]).shape[0]
    d = collect_bc_dataset(episodes=25, seed0=0)
    assert d["X"].shape[1] == obs_dim

    torch.manual_seed(0)
    tr = MAPPOTrainer(obs_dim, st.env.N, _cfg(limiter_commit=True))
    norm = RunningNorm(obs_dim)
    for x in d["X"]:
        norm.normalize(x, update=True)
    xn = torch.as_tensor(np.stack([norm.normalize(x) for x in d["X"]]))
    yt = torch.as_tensor(d["Y"])
    with torch.no_grad():
        before = float(bc_cosine_loss(tr.fin_actor.mean(xn), yt))

    out = warmup_aim(tr.fin_actor, norm, d["X"], d["Y"], steps=600, seed=0)
    assert out["train_cosine"] > 0.95, out
    assert out["train_angle_deg"] < 18.0, out
    assert (1.0 - out["train_cosine"]) < before      # 시작보다 확실히 좋아졌다


@pytest.mark.torch
def test_p68_aux_rollout_writes_unit_targets_every_step():
    """`aux` 팔의 롤아웃이 매 스텝 라벨을 쓴다 (빠진 행 = 조용히 0 을 가르침)."""
    import yaml

    from shepherd.scripts.train_m4 import M4Runner, build_specs, _add_args
    import argparse

    args = _add_args(argparse.ArgumentParser()).parse_args([])
    run_cfg = yaml.safe_load(open("configs/l2_mappo.yaml"))
    run_cfg["loop"]["rollout_env_steps"] = 24
    run_cfg["mappo"]["minibatch_size"] = 8
    runner = M4Runner(run_cfg, 0, "cpu", limiter_policy="hold",
                      finisher_policy="learned", aim_bc="aux",
                      **build_specs(args))
    assert runner.arm == "SL-BCa"
    assert runner.buf.bc_target is not None and runner.tr.cfg.bc_lambda > 0.0
    runner.collect_rollout()
    t = runner.buf.bc_target
    assert t.shape == (24, 3)
    n = np.linalg.norm(t, axis=1)
    assert np.allclose(n, 1.0, atol=1e-5), n        # 모든 행이 단위벡터
    stats = runner.update()
    assert "finisher/bc_cosine_loss" in stats
