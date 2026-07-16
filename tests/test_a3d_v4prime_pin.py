"""V-4' gating train--gate parity pin (docs/09 (ss)). torch-free.

Locks: (1) gating_env_for_spawn pins the scripted-adversary speed to the
spawn's att_speed and asserts the readback; (2) spawns without the key
(D0 robust witnesses) build the nominal env; (3) the caller's env_cfg is
never mutated; (4) Curriculum sbe gating draws carry att_speed for k>0
stages and not for D0 -- the exact contract m3_eval_bundle relies on.
"""
from __future__ import annotations

import copy
import pathlib

import numpy as np
import yaml

from shepherd.train.make_env_m3 import (Curriculum, frozen_constants,
                                        gating_env_for_spawn,
                                        m3_params_from_cfg)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _cfgs():
    run_cfg = yaml.safe_load((ROOT / "configs/m3a_a3d_pilot.yaml").read_text())
    env_cfg = yaml.safe_load((ROOT / run_cfg["env_config"]).read_text())
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    return run_cfg, env_cfg, m3


def _cur(run_cfg, env_cfg, m3):
    return Curriculum(copy.deepcopy(run_cfg["curriculum"]),
                      frozen_constants(env_cfg, m3), env_cfg=env_cfg)


def test_pin_readback_all_witness_speeds():
    _, env_cfg, m3 = _cfgs()
    for v in (16.0, 20.0, 24.0):
        spawn = {"att_speed": v}
        env, _, _ = gating_env_for_spawn(env_cfg, m3, spawn)
        assert abs(float(env.v_nominal) - v) < 1e-12


def test_no_key_builds_nominal():
    _, env_cfg, m3 = _cfgs()
    nominal = float(env_cfg["physics"]["att_speed"])
    for spawn in (None, {"limiters": np.zeros((4, 3))}):
        env, _, _ = gating_env_for_spawn(env_cfg, m3, spawn)
        assert abs(float(env.v_nominal) - nominal) < 1e-12


def test_env_cfg_never_mutated():
    _, env_cfg, m3 = _cfgs()
    before = copy.deepcopy(env_cfg)
    gating_env_for_spawn(env_cfg, m3, {"att_speed": 24.0})
    assert env_cfg == before


def test_sbe_gating_draws_pin_contract():
    run_cfg, env_cfg, m3 = _cfgs()
    cur = _cur(run_cfg, env_cfg, m3)
    # D0 (k=0, robust witnesses): no att_speed key -> nominal env (t=0 fire).
    cur.d_idx = 0
    fn0 = cur.eval_spawn_fn()
    assert fn0 is not None
    for ep in range(4):
        assert "att_speed" not in fn0(ep)
    # k>0 stages: every draw carries a bank witness speed.
    for d_idx in (1, 2, 3, 4):
        cur.d_idx = d_idx
        fn = cur.eval_spawn_fn()
        for ep in range(6):
            sp = fn(ep)
            assert float(sp["att_speed"]) in (16.0, 20.0, 24.0)
            env, _, _ = gating_env_for_spawn(env_cfg, m3, sp)
            assert abs(float(env.v_nominal) - float(sp["att_speed"])) < 1e-12
