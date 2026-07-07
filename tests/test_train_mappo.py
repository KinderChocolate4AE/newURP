"""Torch-required tests for the Phase 2C MAPPO stack.

Same policy as the 2B tests: structural invariants, importorskip for the
torch-free CI, lab venv runs the lot.
"""
from __future__ import annotations

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from shepherd.train.mappo import (CentralCritic, GaussianActor, MAPPOConfig,
                                  MAPPORollout, MAPPOTrainer, MixedActor)
from shepherd.scripts.train_mappo import MAPPORunner, load_ippo_ref

pytestmark = pytest.mark.torch

OBS, N = 12, 3


def _cfg(**kw):
    base = dict(hidden_sizes=(16, 16), epochs=2, minibatch_size=8,
                rollout_steps=16, seed=0, device="cpu")
    base.update(kw)
    return MAPPOConfig.from_dict(base)


def test_actors_shapes_and_fire_binary():
    torch.manual_seed(0)
    lim = GaussianActor(OBS + N, 3)
    fin = MixedActor(OBS, 3)
    o_l = torch.randn(5, OBS + N)
    raw_l, logp_l = lim.act(o_l)
    assert raw_l.shape == (5, 3) and logp_l.shape == (5,)
    lp, ent = lim.evaluate(o_l, raw_l)
    assert torch.allclose(lp, logp_l, atol=1e-6) and torch.all(ent > 0)
    o_f = torch.randn(4, OBS)
    raw_f, logp_f = fin.act(o_f)
    assert raw_f.shape == (4, 4)
    fire = raw_f[:, -1]
    assert torch.all((fire == 0.0) | (fire == 1.0))
    lp_f, _ = fin.evaluate(o_f, raw_f)
    assert torch.allclose(lp_f, logp_f, atol=1e-6)


def test_ortho_init_head_gain():
    torch.manual_seed(1)
    a = GaussianActor(OBS, 3, ortho=True)
    b = GaussianActor(OBS, 3, ortho=False)
    last_a = [m for m in a.mean if isinstance(m, torch.nn.Linear)][-1]
    last_b = [m for m in b.mean if isinstance(m, torch.nn.Linear)][-1]
    # 0.01-gain policy head is ~100x smaller than the default init
    assert last_a.weight.abs().mean() < 0.1 * last_b.weight.abs().mean()
    assert torch.all(last_a.bias == 0)


def _fill(trainer, size):
    rng = np.random.default_rng(0)
    buf = MAPPORollout(size, trainer.obs_dim, trainer.n)
    for _ in range(size):
        obs = rng.normal(size=trainer.obs_dim).astype(np.float32)
        x_l = np.concatenate([np.tile(obs, (trainer.n, 1)),
                              np.eye(trainer.n, dtype=np.float32)], axis=1)
        raw_l, logp_l = trainer.lim_actor.act(torch.as_tensor(x_l))
        raw_f, logp_f = trainer.fin_actor.act(torch.as_tensor(obs[None, :]))
        raw_l, raw_f = raw_l.numpy(), raw_f[0].numpy()
        clip_f = raw_f.copy()
        clip_f[:3] = np.clip(clip_f[:3], -1, 1)
        buf.add(obs=obs, lim_raw=raw_l, lim_clip=np.clip(raw_l, -1, 1),
                lim_logp=logp_l.numpy(), fin_raw=raw_f, fin_clip=clip_f,
                fin_logp=float(logp_f[0].item()),
                rewards=float(rng.normal()), values=float(rng.normal()),
                next_values=float(rng.normal()),
                dones=float(rng.integers(0, 2)))
    return buf


def test_trainer_update_invariants_and_value_norm():
    torch.manual_seed(2)
    tr = MAPPOTrainer(OBS, N, _cfg(value_norm=True))
    before = [p.detach().clone() for p in tr.parameters()]
    stats = tr.update(_fill(tr, 16))
    assert all(np.isfinite(v) for v in stats.values())
    assert stats["limiter/approx_kl"] >= -1e-6
    assert stats["finisher/approx_kl"] >= -1e-6
    assert any(not torch.allclose(a, b)
               for a, b in zip(before, tr.parameters()))
    assert tr.value_norm is not None and tr.value_norm.count > 1
    # value_np returns DENORMALIZED (real-scale) values
    v = tr.value_np(np.zeros(OBS, np.float32))
    assert np.isfinite(v)


def test_target_kl_early_stop_mappo():
    torch.manual_seed(3)
    tr = MAPPOTrainer(OBS, N, _cfg(lr=1e-2, target_kl=1e-7, epochs=5))
    stats = tr.update(_fill(tr, 16))
    assert 1.0 <= stats["epochs_ran"] <= 2.0
    tr2 = MAPPOTrainer(OBS, N, _cfg(target_kl=None, epochs=3))
    assert tr2.update(_fill(tr2, 16))["epochs_ran"] == 3.0


def test_checkpoint_roundtrip(tmp_path):
    torch.manual_seed(4)
    tr = MAPPOTrainer(OBS, N, _cfg())
    tr.update(_fill(tr, 16))
    path = tmp_path / "mappo.pt"
    tr.save(path)
    tr2 = MAPPOTrainer.load(path)
    obs = torch.randn(6, OBS + N)
    r1, _ = tr.lim_actor.act(obs, deterministic=True)
    r2, _ = tr2.lim_actor.act(obs, deterministic=True)
    assert torch.allclose(r1, r2)
    x = np.random.default_rng(5).normal(size=OBS).astype(np.float32)
    assert tr.value_np(x) == pytest.approx(tr2.value_np(x), abs=1e-5)


def test_load_ippo_ref(tmp_path):
    import json
    (tmp_path / "seed0").mkdir()
    (tmp_path / "seed0" / "summary.json").write_text(
        json.dumps({"seed": 0, "return_mean_last3": 5.0}))
    (tmp_path / "seed1").mkdir()
    (tmp_path / "seed1" / "summary.json").write_text(
        json.dumps({"seed": 1, "return_mean_last3": 7.0}))
    ref = load_ippo_ref(str(tmp_path))
    assert ref["mean"] == pytest.approx(6.0)
    assert load_ippo_ref(str(tmp_path / "nope")) is None
    assert load_ippo_ref(None) is None


def _run_cfg(rollout=8):
    return {
        "loop": {"total_env_steps": rollout, "rollout_env_steps": rollout,
                 "eval_interval_updates": 1, "eval_episodes": 1},
        "mappo": dict(hidden_sizes=[16, 16], epochs=2, minibatch_size=4,
                      gamma=0.99, lam=0.95),
        "randomize": {"enabled": True, "att_speed": [16.0, 24.0],
                      "adversary_start_x": [20.0, 28.0],
                      "adversary_omega": [8.0, 12.0],
                      "adv_a_max": [21.0, 30.0]},
    }


def test_runner_collect_update_smoke():
    torch.manual_seed(6)
    with open("configs/m2_l2_train.yaml") as f:
        env_cfg = yaml.safe_load(f)
    runner = MAPPORunner(env_cfg, _run_cfg(rollout=8), seed=0, device="cpu")
    runner.collect_rollout()
    assert runner.env_steps == 8 and runner.buf.full
    fire = runner.buf.fin_raw[:, -1]
    assert np.all((fire == 0.0) | (fire == 1.0))
    assert np.all(np.isfinite(runner.buf.obs))
    stats = runner.update()
    assert all(np.isfinite(v) for v in stats.values())
    assert not runner.buf.full
    assert runner.norm.count == pytest.approx(8, abs=1e-2)


# ----------------------------------------------------------- Phase 2D: COMA ---
def test_coma_advantages_math():
    from shepherd.train.mappo import coma_advantages
    # gamma=0 -> purely myopic: advantages == the D stream itself
    D = np.array([[1.0], [2.0], [3.0]])
    dones = np.array([0.0, 0.0, 1.0])
    adv0 = coma_advantages(D, dones, gamma=0.0, lam=0.95)
    assert np.allclose(adv0, D)
    # gamma=1, lam=1 -> forward sums within the episode, reset at done
    D2 = np.array([[1.0], [1.0], [1.0], [5.0]])
    dones2 = np.array([0.0, 0.0, 1.0, 1.0])
    adv1 = coma_advantages(D2, dones2, gamma=1.0, lam=1.0)
    assert np.allclose(adv1[:, 0], [3.0, 2.0, 1.0, 5.0])


def test_coma_mix_zero_is_exact_2c():
    # with coma_mix=0 the coma_D contents must be COMPLETELY ignored.
    # ROOT CAUSE of the original deterministic failure (server 2026-07-07,
    # identical values across runs -- NOT thread jitter): _fill samples actions
    # through the torch GLOBAL rng, so buf_b's fill started from the state
    # buf_a's fill left behind -> different raw actions/logps (obs are
    # numpy-sourced, so the old obs-only precondition passed misleadingly).
    # Fix: re-seed before EACH fill and assert the action blocks match too.
    # The mix=0 short-circuit in MAPPOTrainer.update (`if cfg.coma_mix > 0.0`)
    # is itself exact; single-thread pin kept for reduction determinism.
    torch.set_num_threads(1)
    torch.manual_seed(7)
    tr_a = MAPPOTrainer(OBS, N, _cfg(coma_mix=0.0))
    torch.manual_seed(7)
    tr_b = MAPPOTrainer(OBS, N, _cfg(coma_mix=0.0))
    torch.manual_seed(11)
    buf_a = _fill(tr_a, 16)
    torch.manual_seed(11)
    buf_b = _fill(tr_b, 16)
    assert np.allclose(buf_a.obs, buf_b.obs)           # identical rollouts
    assert np.allclose(buf_a.lim_raw, buf_b.lim_raw)   # identical ACTIONS
    assert np.allclose(buf_a.lim_logp, buf_b.lim_logp)
    assert np.allclose(buf_a.fin_raw, buf_b.fin_raw)
    buf_b.coma_D[:] = 123.456                          # garbage coma values
    sa, sb = tr_a.update(buf_a), tr_b.update(buf_b)
    for k in sa:
        assert sa[k] == pytest.approx(sb[k], abs=1e-7), k
    assert "limiter/coma_D_raw_mean" not in sa


def test_coma_mix_changes_limiter_gradient_only_path():
    torch.manual_seed(8)
    tr = MAPPOTrainer(OBS, N, _cfg(coma_mix=1.0))
    buf = _fill(tr, 16)
    buf.coma_D[:] = np.random.default_rng(0).normal(
        size=buf.coma_D.shape).astype(np.float32)
    stats = tr.update(buf)
    assert "limiter/coma_D_raw_mean" in stats
    assert all(np.isfinite(v) for v in stats.values())


def test_rollout_reset_zeroes_coma():
    buf = MAPPORollout(4, OBS, N)
    buf.coma_D[:] = 9.9
    buf.reset()
    assert np.all(buf.coma_D == 0.0)


def test_runner_coma_writeback_smoke():
    torch.manual_seed(9)
    with open("configs/m2_l2_train.yaml") as f:
        env_cfg = yaml.safe_load(f)
    # ENGAGEMENT-FORCING overrides (test-only): in the nominal corridor the
    # ring sits 5 m off-axis with kill_radius 2 m, so a RANDOM policy's
    # limiters never gate the on-axis attacker tube and the analytic D is
    # EXACTLY 0.0 at any horizon (spawn layout == hold => D==0; the original
    # rollout=8 -- and any rollout -- could not satisfy the assert; caught on
    # first server execution 2026-07-07). Shrinking the ring onto the axis and
    # spawning at the engagement edge makes masks bite while random drift
    # separates full from hold_position: numpy replica of this setup yields
    # nonzero D on 21/64 steps (|D|max 1.0, first at step 44).
    env_cfg["train"]["layout"]["ring_radius"] = 1.5
    env_cfg["train"]["layout"]["adversary_start_x"] = 14.0
    cfg = _run_cfg(rollout=64)
    cfg["randomize"]["enabled"] = False        # deterministic geometry
    cfg["mappo"]["coma_mix"] = 1.0
    runner = MAPPORunner(env_cfg, cfg, seed=0, device="cpu")
    runner.collect_rollout()
    # write-back happened: at least one non-tail row carries a D vector
    assert np.any(runner.buf.coma_D != 0.0)
    stats = runner.update()
    assert "limiter/coma_D_raw_mean" in stats
    assert all(np.isfinite(v) for v in stats.values())
