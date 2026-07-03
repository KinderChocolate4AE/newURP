"""Phase 2A DoD smoke (docs/09 SS5): random policy runs full episodes through
the trainer adapter NaN-free, with obs/action/reward/info wiring verified
(shapes, keys, credit split, reward signs, reserved-dim padding, CTDE state).

Notes vs the DoD text "full episode (episode_len=80)": under ANY weak policy
the scripted adversary penetrates the corridor in ~23 steps, so the natural
end is TERMINATION; the truncation branch is exercised explicitly with a
test-only episode_len override (cfg dict only -- the frozen YAML is untouched).
torch-free.
"""
from __future__ import annotations
import numpy as np
import yaml

from shepherd.train.make_env import make_train_env, pad_env_action
from shepherd.train.adapter import (ShepherdAdapter, collect_episode,
                                    random_policy, role_of)


def _adapter(episode_len=None):
    with open("configs/m2_l2_train.yaml") as f:
        cfg = yaml.safe_load(f)
    if episode_len is not None:            # test-only truncation probe
        cfg["train"]["episode_len"] = episode_len
    env, scn, lay = make_train_env(cfg)
    return ShepherdAdapter(env)


def test_smoke_full_episode_nofire():
    ad = _adapter()
    for seed in (0, 1):
        ep = collect_episode(ad, random_policy(np.random.default_rng(seed)), seed)
        T = ep.length
        assert T > 0 and (ep.terminated or ep.truncated)
        assert not (ep.terminated and ep.truncated)
        # shapes: obs/state have T+1 (terminal obs kept for GAE bootstrap)
        for a, o in ep.obs.items():
            assert o.shape == (T + 1, ad.obs_dim) and np.all(np.isfinite(o))
        assert ep.states.shape == (T + 1, ad.state_dim)
        assert np.all(np.isfinite(ep.states))
        assert ep.coma_D.shape == (T, len(ad.limiter_ids))
        assert ep.headline.shape == (T,)
        assert np.all(np.isfinite(ep.coma_D)) and np.all(np.isfinite(ep.headline))
        for a, acts in ep.actions.items():
            assert acts.shape == (T, ad.live_dim(a))
        # reward wiring: adversary = -J, limiter/finisher = +J (all equal)
        rf = ep.rewards[ad.finisher_id]
        for lid in ad.limiter_ids:
            assert np.array_equal(ep.rewards[lid], rf)
        assert np.array_equal(ep.rewards[ad.adversary_id], -rf)
        assert np.all(np.isfinite(rf))


def test_fire_spam_rejected_by_r2_gate():
    """fire_prob=1 spams the fire command every step, but the R2 gate (fire iff
    v_shot_soft >= theta_fire = 0.9) must REJECT all of them under a random
    policy (v_soft never gets near the gate on this corridor): no fire_event,
    magazine intact, zero wasted shots, FSM stays LOADED, episode ends
    penetrated. The actual commit chain (DEPLOYING->LOCKED->resolve) needs a
    shaping policy that lifts v_soft over the gate -- 2B+ territory."""
    ad = _adapter()
    ep = collect_episode(ad, random_policy(np.random.default_rng(3), fire_prob=1.0),
                         seed=3)
    assert ep.terminated and not ep.truncated
    assert ep.flags_last["fsm_state"] == "LOADED"
    assert int(ep.flags_last["k_remaining"]) == 1
    assert int(ep.flags_last["wasted_fire"]) == 0
    assert not ep.flags_last["fire_event"]
    assert bool(ep.flags_last["penetrated"])
    assert np.all(np.isfinite(ep.rewards[ad.finisher_id]))


def test_truncation_branch_with_short_horizon():
    ad = _adapter(episode_len=5)           # < ~23-step penetration time
    ep = collect_episode(ad, random_policy(np.random.default_rng(0)), seed=0)
    assert ep.length == 5 and ep.truncated and not ep.terminated


def test_shared_fullstate_obs_and_state_dim():
    """CTDE contract (docs/09 SS2): all agents see the SAME full-state obs."""
    ad = _adapter()
    obs, state = ad.reset(seed=0)
    ref = obs[ad.finisher_id]
    for a, o in obs.items():
        assert np.array_equal(o, ref)
    assert state.shape == (ad.state_dim,) == (9 * (len(ad.limiter_ids) + 2),)


def test_reserved_dim_padding_and_bounds():
    ad = _adapter()
    rng = np.random.default_rng(0)
    pol = random_policy(rng)
    obs, _ = ad.reset(seed=0)
    for a in ad.agent_ids:
        if a == ad.adversary_id:
            continue
        live = pol(a, obs[a], ad)
        low, high = ad.action_bounds(a)
        assert np.all(live >= low - 1e-6) and np.all(live <= high + 1e-6)
        padded = pad_env_action(a, live)
        space = ad.env.action_space(a)
        assert padded.shape == space.shape
        if role_of(a) in ("limiter", "finisher"):
            assert padded[3] == 0.0                      # reserved idx zeroed
        assert np.all(padded >= space.low - 1e-6)
        assert np.all(padded <= space.high + 1e-6)


def test_same_seed_reproducibility():
    ad = _adapter()
    e1 = collect_episode(ad, random_policy(np.random.default_rng(5)), seed=5)
    e2 = collect_episode(ad, random_policy(np.random.default_rng(5)), seed=5)
    assert e1.length == e2.length
    for a in e1.obs:
        assert np.array_equal(e1.obs[a], e2.obs[a])
    assert np.array_equal(e1.coma_D, e2.coma_D)
    assert np.array_equal(e1.states, e2.states)
