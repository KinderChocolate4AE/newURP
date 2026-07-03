"""Torch-free unit tests for the PPO advantage core (L2 Phase 1).

These exercise the numerically load-bearing logic -- GAE bootstrapping under
termination vs truncation, and advantage normalization -- with numpy only, so
they run in the existing torch-free CI suite. The truncation test is the key
guard for the shepherd env, whose dominant terminal is truncation at 80 steps.
"""

import numpy as np

from shepherd.train.gae import compute_gae, normalize_advantages


def _mc_discounted_return(rewards, gamma):
    """Reference: sum_{k>=t} gamma^{k-t} r_k for a single terminated episode."""
    T = len(rewards)
    out = np.zeros(T)
    running = 0.0
    for t in range(T - 1, -1, -1):
        running = rewards[t] + gamma * running
        out[t] = running
    return out


def test_lam_zero_matches_td_residual():
    # With lam=0, advantage_t collapses to the one-step TD residual.
    T = 6
    rng = np.random.default_rng(0)
    rewards = rng.normal(size=T)
    values = rng.normal(size=T)
    next_values = rng.normal(size=T)
    dones = np.zeros(T)
    gamma = 0.95

    adv, ret = compute_gae(rewards, values, next_values, dones, gamma, lam=0.0)

    expected_delta = rewards + gamma * next_values - values
    np.testing.assert_allclose(adv, expected_delta, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(ret, expected_delta + values, rtol=1e-12, atol=1e-12)


def test_lam_one_matches_discounted_return_when_terminated():
    # lam=1 on a single episode that TRULY terminates at the end => returns are
    # the plain Monte-Carlo discounted returns (values telescope out).
    T = 5
    rng = np.random.default_rng(1)
    rewards = rng.normal(size=T)
    values = rng.normal(size=T)
    next_values = np.zeros(T)          # terminated: no bootstrap anywhere...
    next_values[:-1] = values[1:]      # ...except the natural V(s_{t+1}) chaining
    # Standard GAE bookkeeping: next_values[t] = V(s_{t+1}) for t<T-1, and 0 at
    # the terminal step. dones only set at the terminal step.
    dones = np.zeros(T)
    dones[-1] = 1.0
    gamma = 0.9

    adv, ret = compute_gae(rewards, values, next_values, dones, gamma, lam=1.0)

    np.testing.assert_allclose(
        ret, _mc_discounted_return(rewards, gamma), rtol=1e-10, atol=1e-10
    )


def test_truncated_uses_bootstrap_value():
    # A mid-rollout truncation must bootstrap from V(final_obs), NOT 0 and NOT
    # V(reset_obs). We check the truncated step's advantage uses the supplied
    # next_value, and that the GAE recursion does not cross the boundary.
    T = 4
    rewards = np.array([1.0, 1.0, 1.0, 1.0])
    values = np.array([0.5, 0.5, 0.5, 0.5])
    gamma, lam = 0.99, 0.95

    v_final = 7.0        # value of the true final observation at truncation
    v_reset = -3.0       # value of the (wrong) post-reset observation

    # step 1 (index 1) is a truncation boundary.
    next_values = np.array([values[1], v_final, values[3], 0.0])
    dones = np.array([0.0, 1.0, 0.0, 0.0])  # boundary at index 1

    adv, _ = compute_gae(rewards, values, next_values, dones, gamma, lam)

    # The truncated step's advantage is exactly its TD residual (recursion is
    # cut *after* it by dones, and it is the last step of its sub-episode here).
    expected_trunc = rewards[1] + gamma * v_final - values[1]
    np.testing.assert_allclose(adv[1], expected_trunc, rtol=1e-12, atol=1e-12)

    # Sanity: had we (wrongly) bootstrapped from the reset obs, adv[1] would
    # differ -- confirm the function is genuinely using v_final.
    wrong = np.array([values[1], v_reset, values[3], 0.0])
    adv_wrong, _ = compute_gae(rewards, values, wrong, dones, gamma, lam)
    assert not np.isclose(adv[1], adv_wrong[1])

    # The boundary must stop advantage from leaking backward: step 0's advantage
    # must not depend on anything at/after the boundary.
    adv0_only = compute_gae(
        rewards[:1], values[:1], np.array([values[1]]), np.array([1.0]),
        gamma, lam,
    )[0][0]
    # step 0 with dones[0]=0 still chains into step 1; instead verify the cut by
    # perturbing a post-boundary reward and checking step 0 is unaffected.
    rewards2 = rewards.copy()
    rewards2[2] += 100.0
    adv2, _ = compute_gae(rewards2, values, next_values, dones, gamma, lam)
    np.testing.assert_allclose(adv[0], adv2[0], rtol=1e-12, atol=1e-12)


def test_terminated_bootstrap_is_zero():
    # A true termination bootstraps from 0 regardless of any later values.
    rewards = np.array([2.0])
    values = np.array([1.0])
    next_values = np.array([0.0])
    dones = np.array([1.0])
    adv, ret = compute_gae(rewards, values, next_values, dones, gamma=0.99, lam=0.95)
    np.testing.assert_allclose(adv[0], 2.0 - 1.0)  # r - V, no bootstrap
    np.testing.assert_allclose(ret[0], 2.0)


def test_normalize_advantages_mean0_std1():
    rng = np.random.default_rng(2)
    adv = rng.normal(loc=5.0, scale=3.0, size=257)
    out = normalize_advantages(adv)
    assert abs(out.mean()) < 1e-9
    assert abs(out.std() - 1.0) < 1e-6


def test_compute_gae_shape_validation():
    import pytest

    with pytest.raises(ValueError):
        compute_gae(
            np.zeros(3), np.zeros(4), np.zeros(3), np.zeros(3), 0.99, 0.95
        )


def test_compute_gae_input_validation():
    # 2026-07-03 GPT-review hardening: rewards 1-D, gamma/lam in [0,1], dones 0/1.
    import pytest

    ok = (np.zeros(3), np.zeros(3), np.zeros(3), np.zeros(3))
    with pytest.raises(ValueError, match="rewards must be 1-D"):
        compute_gae(np.zeros((3, 1)), *ok[1:], 0.99, 0.95)
    with pytest.raises(ValueError, match="gamma"):
        compute_gae(*ok, 1.5, 0.95)
    with pytest.raises(ValueError, match="lam"):
        compute_gae(*ok, 0.99, -0.1)
    with pytest.raises(ValueError, match="dones"):
        compute_gae(np.zeros(3), np.zeros(3), np.zeros(3),
                    np.array([0.0, 2.0, 0.0]), 0.99, 0.95)
