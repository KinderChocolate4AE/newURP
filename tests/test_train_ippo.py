"""Torch-required tests for the Phase 2B IPPO stack (mixed head + runner).

``importorskip`` keeps the torch-free CI green; the lab venv runs these.
Following the Phase-1 policy (tests/test_ppo_update.py) we assert structural
invariants, not single-update loss decrease.
"""
from __future__ import annotations

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from shepherd.train.ippo import MixedActorCritic, MixedPPOTrainer, limiter_inputs
from shepherd.train.ppo import PPOConfig, RolloutBuffer
from shepherd.scripts.train_ippo import (IPPORunner, eval_bundle, hold_bundle,
                                         make_scripted_ctx, scripted_bundle)

pytestmark = pytest.mark.torch

OBS, CONT = 12, 3


def _cfg(**kw):
    base = dict(hidden_sizes=(16, 16), epochs=2, minibatch_size=16,
                rollout_steps=32, seed=0, device="cpu")
    base.update(kw)
    return PPOConfig.from_dict(base)


# ------------------------------------------------------------- mixed head ---
def test_mixed_act_shapes_and_binary_fire():
    torch.manual_seed(0)
    ac = MixedActorCritic(OBS, CONT)
    obs = torch.randn(5, OBS)
    raw, logp, val = ac.act(obs)
    assert raw.shape == (5, CONT + 1) and logp.shape == (5,) and val.shape == (5,)
    fire = raw[:, -1]
    assert torch.all((fire == 0.0) | (fire == 1.0))


def test_mixed_deterministic_is_mean_and_thresholded_fire():
    torch.manual_seed(1)
    ac = MixedActorCritic(OBS, CONT)
    obs = torch.randn(3, OBS)
    r1, _, _ = ac.act(obs, deterministic=True)
    r2, _, _ = ac.act(obs, deterministic=True)
    assert torch.allclose(r1, r2)                       # no sampling noise
    with torch.no_grad():
        dist_g, dist_b = ac._dists(obs)
    assert torch.allclose(r1[:, :CONT], dist_g.mean)
    assert torch.equal(r1[:, CONT:], (dist_b.probs > 0.5).float())


def test_mixed_logprob_matches_manual_normal_plus_bernoulli():
    torch.manual_seed(2)
    ac = MixedActorCritic(OBS, CONT)
    obs = torch.randn(4, OBS)
    raw, logp_act, _ = ac.act(obs)
    logp_eval, entropy, _ = ac.evaluate(obs, raw)
    assert torch.allclose(logp_act, logp_eval, atol=1e-6)  # act/evaluate agree
    with torch.no_grad():
        dist_g, dist_b = ac._dists(obs)
        manual = (dist_g.log_prob(raw[:, :CONT]).sum(-1)
                  + dist_b.log_prob(raw[:, CONT:]).sum(-1))
        manual_ent = dist_g.entropy().sum(-1) + dist_b.entropy().sum(-1)
    assert torch.allclose(logp_eval, manual, atol=1e-6)
    assert torch.allclose(entropy, manual_ent, atol=1e-6)
    assert torch.all(entropy > 0)


def _fill_via_act(trainer, size):
    rng = np.random.default_rng(0)
    buf = RolloutBuffer(size, trainer.obs_dim, trainer.act_dim)
    for _ in range(size):
        obs = rng.normal(size=trainer.obs_dim).astype(np.float32)
        raw, logp, val = trainer.ac.act(torch.as_tensor(obs))
        raw = raw.numpy()
        env_a = raw.copy()
        env_a[:CONT] = np.clip(env_a[:CONT], -1, 1)
        buf.add(obs=obs, raw_action=raw, env_action=env_a,
                log_prob=float(logp.item()), value=float(val.item()),
                reward=float(rng.normal()),
                next_value=float(rng.normal()),
                done=float(rng.integers(0, 2)))
    return buf


def test_mixed_trainer_update_invariants():
    torch.manual_seed(3)
    tr = MixedPPOTrainer(OBS, CONT + 1, _cfg())
    before = [p.detach().clone() for p in tr.ac.parameters()]
    stats = tr.update(_fill_via_act(tr, 32))
    assert all(np.isfinite(v) for v in stats.values())
    assert stats["approx_kl"] >= -1e-6
    assert any(not torch.allclose(a, b)
               for a, b in zip(before, tr.ac.parameters()))


def test_mixed_trainer_checkpoint_roundtrip(tmp_path):
    torch.manual_seed(4)
    tr = MixedPPOTrainer(OBS, CONT + 1, _cfg())
    tr.update(_fill_via_act(tr, 32))
    path = tmp_path / "fin.pt"
    tr.save(path)
    tr2 = MixedPPOTrainer.load(path)
    assert isinstance(tr2.ac, MixedActorCritic)
    obs = torch.randn(6, OBS)
    r1, _, v1 = tr.ac.act(obs, deterministic=True)
    r2, _, v2 = tr2.ac.act(obs, deterministic=True)
    assert torch.allclose(r1, r2) and torch.allclose(v1, v2)


def test_target_kl_early_stop():
    torch.manual_seed(6)
    # huge lr + tiny target_kl -> first epoch exceeds -> remaining skipped
    tr = MixedPPOTrainer(OBS, CONT + 1, _cfg(lr=1e-2, target_kl=1e-6, epochs=5))
    stats = tr.update(_fill_via_act(tr, 32))
    assert 1.0 <= stats["epochs_ran"] <= 2.0
    # default (None) keeps Phase-1 behavior: all epochs run
    tr2 = MixedPPOTrainer(OBS, CONT + 1, _cfg(epochs=3))
    s2 = tr2.update(_fill_via_act(tr2, 32))
    assert s2["epochs_ran"] == 3.0


def test_set_lr_hook():
    tr = MixedPPOTrainer(OBS, CONT + 1, _cfg(lr=3e-4))
    tr.set_lr(1.5e-4)
    assert tr.optimizer.param_groups[0]["lr"] == pytest.approx(1.5e-4)
    assert tr.cfg.lr == pytest.approx(3e-4)            # base rate untouched


def test_limiter_inputs_onehot():
    x = limiter_inputs(np.arange(5, dtype=np.float32), 3)
    assert x.shape == (3, 8)
    assert np.allclose(x[:, :5], np.arange(5, dtype=np.float32))
    assert np.allclose(x[:, 5:], np.eye(3))


# ------------------------------------------------------- runner smoke (env) ---
def _run_cfg(rollout=8):
    return {
        "loop": {"total_env_steps": rollout, "rollout_env_steps": rollout,
                 "eval_interval_updates": 1, "eval_episodes": 1},
        "ppo_limiter": dict(hidden_sizes=[16, 16], epochs=2, minibatch_size=16,
                            gamma=0.99, lam=0.95),
        "ppo_finisher": dict(hidden_sizes=[16, 16], epochs=2, minibatch_size=8,
                             gamma=0.99, lam=0.95),
        "randomize": {"enabled": True, "att_speed": [16.0, 24.0],
                      "adversary_start_x": [20.0, 28.0],
                      "adversary_omega": [8.0, 12.0],
                      "adv_a_max": [21.0, 30.0]},
    }


def _env_cfg():
    with open("configs/m2_l2_train.yaml") as f:
        return yaml.safe_load(f)


def test_runner_collect_update_smoke():
    torch.manual_seed(5)
    runner = IPPORunner(_env_cfg(), _run_cfg(rollout=8), seed=0, device="cpu")
    runner.collect_rollout()
    assert runner.env_steps == 8
    assert runner.buf_l.full and runner.buf_f.full
    # fire dim stored as exact {0,1}
    fire = runner.buf_f.raw_actions[:, -1]
    assert np.all((fire == 0.0) | (fire == 1.0))
    assert np.all(np.isfinite(runner.buf_l.obs))
    stats = runner.update()
    assert all(np.isfinite(v) for v in stats.values())
    assert not runner.buf_l.full                       # buffers cycled
    # normalizer saw exactly the collected env steps
    assert runner.norm.count == pytest.approx(8, abs=1e-2)


def test_eval_bundles_smoke():
    env_cfg = _env_cfg()
    ctx = make_scripted_ctx(env_cfg)
    for bundle in (hold_bundle(ctx), scripted_bundle(ctx)):
        res = eval_bundle(env_cfg, *bundle, episodes=1, seed0=123)
        assert np.isfinite(res["return_mean"])
        assert 0.0 <= res["captured_rate"] <= 1.0
        assert res["len_mean"] >= 1
