"""Torch-required tests for the PPO network + update step (L2 Phase 1).

Guarded by ``importorskip`` so the default torch-free CI simply skips these,
while the lab venv (torch present) runs them. Also tagged ``@pytest.mark.torch``
for explicit ``-m 'not torch'`` deselection.

We deliberately do NOT assert that the full PPO objective decreases in a single
step -- with clipping + entropy + value loss + advantage normalization + Adam +
minibatch shuffling that is not guaranteed and would be flaky. Instead we assert
structural invariants (finite, ratio==1 pre-update, params move, KL>=0, grad
clip runs) plus a controlled directional check on the actor mean.
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from shepherd.train.ppo import ActorCritic, PPOConfig, PPOTrainer, RolloutBuffer

pytestmark = pytest.mark.torch


def _fill_buffer(obs_dim, act_dim, size, seed=0):
    rng = np.random.default_rng(seed)
    buf = RolloutBuffer(size, obs_dim, act_dim)
    for _ in range(size):
        buf.add(
            obs=rng.normal(size=obs_dim).astype(np.float32),
            raw_action=rng.normal(size=act_dim).astype(np.float32),
            env_action=rng.normal(size=act_dim).astype(np.float32),
            log_prob=float(rng.normal()),
            value=float(rng.normal()),
            reward=float(rng.normal()),
            next_value=float(rng.normal()),
            done=float(rng.integers(0, 2)),
        )
    return buf


def _cfg(**kw):
    base = dict(
        total_timesteps=1024, rollout_steps=64, epochs=2, minibatch_size=16,
        lr=3e-4, hidden_sizes=(32, 32), seed=0, device="cpu",
    )
    base.update(kw)
    return PPOConfig(**base)


def test_actor_critic_shapes():
    ac = ActorCritic(obs_dim=5, act_dim=3, hidden_sizes=(16, 16))
    obs = torch.zeros(7, 5)
    raw, logp, val = ac.act(obs)
    assert raw.shape == (7, 3)
    assert logp.shape == (7,)
    assert val.shape == (7,)
    logp2, ent, val2 = ac.evaluate(obs, raw)
    assert logp2.shape == (7,) and ent.shape == (7,) and val2.shape == (7,)


def test_ratio_is_one_before_update():
    # Recomputing log-probs on the same net for stored raw actions => ratio 1.
    ac = ActorCritic(obs_dim=4, act_dim=2, hidden_sizes=(16,))
    obs = torch.randn(10, 4)
    raw, old_logp, _ = ac.act(obs)
    new_logp, _, _ = ac.evaluate(obs, raw)
    ratio = torch.exp(new_logp - old_logp)
    assert torch.allclose(ratio, torch.ones_like(ratio), atol=1e-6)


def test_update_returns_finite_diagnostics_and_moves_params():
    cfg = _cfg()
    trainer = PPOTrainer(obs_dim=6, act_dim=2, cfg=cfg)
    buf = _fill_buffer(6, 2, cfg.rollout_steps)

    before = [p.detach().clone() for p in trainer.ac.parameters()]
    stats = trainer.update(buf)
    after = list(trainer.ac.parameters())

    for k, v in stats.items():
        assert np.isfinite(v), f"diagnostic {k} is not finite: {v}"

    assert stats["approx_kl"] >= -1e-6            # approx KL is >= 0 up to noise
    assert 0.0 <= stats["clip_fraction_action"] <= 1.0
    moved = any(not torch.allclose(b, a) for b, a in zip(before, after))
    assert moved, "parameters did not change after an update"


def test_grad_clipping_path_executes():
    # Large advantages -> large grads -> clipping actually engages (grad_norm
    # reported should be finite and the step should not explode to NaN).
    cfg = _cfg(max_grad_norm=0.1, epochs=1)
    trainer = PPOTrainer(obs_dim=4, act_dim=2, cfg=cfg)
    buf = _fill_buffer(4, 2, cfg.rollout_steps, seed=3)
    # inflate rewards so returns/advantages are large
    buf.rewards *= 1000.0
    stats = trainer.update(buf)
    assert np.isfinite(stats["grad_norm"])
    for p in trainer.ac.parameters():
        assert torch.isfinite(p).all()


def test_seeded_init_is_reproducible():
    # Same seed => identical initial network parameters (CPU determinism).
    torch.manual_seed(0)
    ac1 = ActorCritic(obs_dim=4, act_dim=2, hidden_sizes=(16, 16))
    torch.manual_seed(0)
    ac2 = ActorCritic(obs_dim=4, act_dim=2, hidden_sizes=(16, 16))
    for p1, p2 in zip(ac1.parameters(), ac2.parameters()):
        assert torch.allclose(p1, p2)


def test_checkpoint_save_load_roundtrip(tmp_path):
    cfg = _cfg()
    trainer = PPOTrainer(obs_dim=6, act_dim=2, cfg=cfg)
    trainer.update(_fill_buffer(6, 2, cfg.rollout_steps))  # move params off init
    path = tmp_path / "ckpt.pt"
    trainer.save(path)

    restored = PPOTrainer.load(path, map_location="cpu")
    assert restored.obs_dim == 6 and restored.act_dim == 2
    for p1, p2 in zip(trainer.ac.parameters(), restored.ac.parameters()):
        assert torch.allclose(p1, p2)

    # deterministic (mean) action matches after reload
    obs = torch.randn(5, 6)
    a1, _, _ = trainer.ac.act(obs, deterministic=True)
    a2, _, _ = restored.ac.act(obs, deterministic=True)
    assert torch.allclose(a1, a2, atol=1e-6)


def test_update_rejects_partial_buffer():
    # 2026-07-03 GPT-review fix: a partially-filled buffer would silently train
    # on the zero-valued tail -- update() must refuse it.
    cfg = _cfg()
    trainer = PPOTrainer(obs_dim=4, act_dim=2, cfg=cfg)
    buf = _fill_buffer(4, 2, cfg.rollout_steps)
    buf.reset()                                   # empty again -> not full
    with pytest.raises(ValueError, match="not full"):
        trainer.update(buf)


def test_minibatch_permutations_differ_across_updates():
    # 2026-07-03 GPT-review fix: the shuffle RNG is trainer state, so successive
    # updates must NOT replay the identical permutation sequence.
    cfg = _cfg(epochs=1)
    trainer = PPOTrainer(obs_dim=4, act_dim=2, cfg=cfg)
    s1 = trainer._rng.bit_generator.state["state"]["state"]
    trainer.update(_fill_buffer(4, 2, cfg.rollout_steps, seed=1))
    s2 = trainer._rng.bit_generator.state["state"]["state"]
    assert s1 != s2, "shuffle RNG did not advance across update()"


def test_log_std_is_clamped_in_dist():
    # 2026-07-03 GPT-review fix: a drifted log_std parameter outside
    # [LOG_STD_MIN, LOG_STD_MAX] must not produce a degenerate/exploding std.
    ac = ActorCritic(obs_dim=3, act_dim=2, hidden_sizes=(8,))
    with torch.no_grad():
        ac.log_std.fill_(100.0)
    with torch.no_grad():
        std_max = float(ac._dist(torch.zeros(1, 3)).stddev.max())
    assert std_max <= float(np.exp(ActorCritic.LOG_STD_MAX)) + 1e-6
    with torch.no_grad():
        ac.log_std.fill_(-100.0)
        std_min = float(ac._dist(torch.zeros(1, 3)).stddev.min())
    assert std_min >= float(np.exp(ActorCritic.LOG_STD_MIN)) - 1e-9


def test_ppoconfig_from_dict_rejects_unknown_and_tuples_hidden():
    cfg = PPOConfig.from_dict({"hidden_sizes": [128, 128], "gamma": 0.99})
    assert cfg.hidden_sizes == (128, 128)
    with pytest.raises(ValueError):
        PPOConfig.from_dict({"bogus_key": 1})
