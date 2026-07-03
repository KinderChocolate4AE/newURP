"""Attacker-family randomization tests (L2 Phase 2B; torch-free).

Checks the sampling contract and -- critically -- the frozen-contract hygiene:
the loaded frozen-YAML dict is never mutated, and the v_shot surrogate
authority (env.a_att_max) never moves even when the scripted actual agility
(env.adv_a_max) is randomized.
"""
from __future__ import annotations

import copy

import numpy as np
import pytest
import yaml

from shepherd.train.attacker_rand import (RAND_KEYS, build_attacker_env,
                                          sample_attacker_params)

RAND_CFG = {
    "enabled": True,
    "att_speed": [16.0, 24.0],
    "adversary_start_x": [20.0, 28.0],
    "adversary_omega": [8.0, 12.0],
    "adv_a_max": [21.0, 30.0],
}


def _env_cfg():
    with open("configs/m2_l2_train.yaml") as f:
        return yaml.safe_load(f)


def test_disabled_returns_empty():
    rng = np.random.default_rng(0)
    assert sample_attacker_params(None, rng) == {}
    assert sample_attacker_params({"enabled": False, "att_speed": [1, 2]}, rng) == {}


def test_sampling_ranges_and_determinism():
    draws = [sample_attacker_params(RAND_CFG, np.random.default_rng(7))
             for _ in range(2)]
    assert draws[0] == draws[1]                       # same rng seed -> same draw
    rng = np.random.default_rng(3)
    for _ in range(50):
        p = sample_attacker_params(RAND_CFG, rng)
        assert set(p) == set(RAND_KEYS)
        for k in RAND_KEYS:
            lo, hi = RAND_CFG[k]
            assert lo <= p[k] <= hi


def test_bad_configs_raise():
    rng = np.random.default_rng(0)
    with pytest.raises(KeyError):
        sample_attacker_params({"enabled": True, "atk_speed": [1, 2]}, rng)
    with pytest.raises(ValueError):
        sample_attacker_params({"enabled": True, "att_speed": [24, 16]}, rng)
    with pytest.raises(ValueError):                   # backend-clamp guard
        sample_attacker_params({"enabled": True, "adv_a_max": [31.0, 35.0]}, rng)


def test_build_applies_family_draw_and_keeps_frozen_cfg_intact():
    env_cfg = _env_cfg()
    snapshot = copy.deepcopy(env_cfg)
    params = {"att_speed": 17.5, "adversary_start_x": 26.0,
              "adversary_omega": 9.0, "adv_a_max": 25.0}
    env, scn, lay = build_attacker_env(env_cfg, params)

    assert env_cfg == snapshot                        # source dict never mutated
    assert env.v_nominal == pytest.approx(17.5)       # scripted forward drive
    assert scn.adversary.speed == pytest.approx(17.5)
    assert lay.adversary_p0[0] == pytest.approx(26.0)  # spawn depth
    assert lay.adversary_v0[0] == pytest.approx(-17.5)  # spawn speed follows
    assert env.adv_a_max == pytest.approx(25.0)       # actual scripted agility
    # the SURROGATE authority is untouched (theta_fire calibration protected)
    assert env.a_att_max == pytest.approx(30.0)


def test_build_nominal_when_no_params():
    env_cfg = _env_cfg()
    env, scn, lay = build_attacker_env(env_cfg, {})
    assert env.v_nominal == pytest.approx(20.0)
    assert env.adv_a_max == pytest.approx(30.0)
    assert lay.adversary_p0[0] == pytest.approx(24.0)
