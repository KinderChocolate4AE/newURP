"""A-3d trainer pieces (docs/17 SS2-SS4, V-1..V-6; docs/09 (oo)). torch-free.

Locks: phi obs-parsing/determinism/beta; Wilson bounds; Curriculum sbe
(k-ladder LCB/UCB gate, spawn semantics incl. limiter_v & att_speed, D0
zero-vel witness draws, nominal None, cap freeze, overrides always None);
teacher_fire decision; a3d config sanity (Z_train disjoint from eval bands,
ladder monotone k, budget rule).
"""
from __future__ import annotations

import copy
import pathlib

import numpy as np
import pytest
import yaml

from shepherd.train import spawn_bank as sb
from shepherd.train.make_env_m3 import Curriculum
from shepherd.train.phi_potential import (PHI_SEEDS_AUDIT, PHI_SEEDS_TRAIN,
                                          parse_obs_kin, phi_value,
                                          wilson_lcb, wilson_ucb)

ROOT = pathlib.Path(__file__).resolve().parents[1]
FROZEN = {"half_angle": 0.067, "theta_fire": 0.9, "sigma_g": 1.0, "w_g": 0.3}
BANK = ROOT / "results/a3d_sbe_bank.json"
RBANK = ROOT / "results/a3_robust_bank.json"


def _witness_obs():
    t0 = sb.load_t0(str(RBANK))[0]
    sp = sb.spawn_from(t0)
    obs = np.zeros(9 * 4 + 9 + 9 + 6 + 3)
    for i in range(4):
        obs[9 * i: 9 * i + 3] = sp["limiters"][i]
    obs[45:48], obs[48:51] = sp["att_p"], sp["att_v"]
    obs[-3], obs[-1] = 1.0, 1e-3          # readout tail (clean)
    return obs, sp


# ------------------------------------------------------------------- phi ---
def test_phi_parse_and_determinism():
    obs, sp = _witness_obs()
    ap, av, lim = parse_obs_kin(obs)
    assert np.allclose(ap, sp["att_p"]) and np.allclose(av, sp["att_v"])
    assert np.allclose(lim, sp["limiters"])
    p1 = phi_value(obs, n=300)
    p2 = phi_value(obs, n=300)
    assert p1 == p2 and 0.0 <= p1 <= 1.0   # fixed bank -> deterministic
    far = obs.copy()
    far[0:3] += 50.0                       # degrade one limiter
    assert phi_value(far, n=300) <= p1


def test_phi_beta_penalizes_seed_variance():
    obs, _ = _witness_obs()
    p0 = phi_value(obs, n=300, beta=0.0)
    p2 = phi_value(obs, n=300, beta=2.0)
    assert p2 <= p0


def test_wilson_bounds():
    lcb, ucb = wilson_lcb(36, 80), wilson_ucb(36, 80)
    assert 0.0 < lcb < 36 / 80 < ucb < 1.0
    assert wilson_lcb(0, 80) <= 1e-12 and wilson_ucb(80, 80) >= 1.0 - 1e-9
    assert wilson_lcb(0, 0) == 0.0 and wilson_ucb(0, 0) == 1.0


def test_phi_seed_banks_disjoint_from_eval_bands():
    assert not (set(PHI_SEEDS_TRAIN) & set(PHI_SEEDS_AUDIT))
    for s in PHI_SEEDS_TRAIN + PHI_SEEDS_AUDIT:
        assert s < 1_000_000               # far from 77M/31M/41M bands


# -------------------------------------------------------------- teacher ---
def test_teacher_fire_decision():
    from shepherd.train.phi_potential import teacher_fire
    obs = np.zeros(72)
    obs[-3], obs[-1] = 0.95, 1e-3
    assert teacher_fire(obs, 0.9)
    obs[-3] = 0.85
    assert not teacher_fire(obs, 0.9)      # below theta
    obs[-3], obs[-1] = 0.95, 0.0
    assert not teacher_fire(obs, 0.9)      # boxed


# ------------------------------------------------------- Curriculum: sbe ---
def _sbe_cfg(**over):
    sc = {"bank": str(BANK), "robust_bank": str(RBANK), "sigma_pos": 0.02,
          "stages": [{"name": "d0", "k": 0, "exit": 0.45},
                     {"name": "d1", "k": 1, "exit": 0.40},
                     {"name": "d2", "k": 2, "exit": 0.30},
                     {"name": "d5", "nominal": True}],
          "gate": {"episodes": 80, "z": 1.645, "backoff_margin": 0.05},
          "max_steps": 10_000}
    sc.update(over)
    return {"mode": "sbe", "sbe": sc,
            "s2_exit": {"heldout_clean_nonzero_last": 3}}


FZ0 = {"clean_cross_rate": 0.0}


def _ev(cap, n=80):
    return {"captured_rate": cap, "episodes": n, "clean_cross_rate": cap,
            "boxed_fire_rate": 0.0, "fire_rate": 1.0}


def test_sbe_requires_bank_and_nominal():
    if not BANK.exists():
        pytest.skip("SBE bank not built")
    cur = Curriculum(_sbe_cfg(), dict(FROZEN))
    assert cur.stage == "s2" and cur.overrides(0) is None
    bad = _sbe_cfg()
    bad["sbe"]["stages"] = bad["sbe"]["stages"][:-1]
    with pytest.raises(ValueError, match="nominal"):
        Curriculum(bad, dict(FROZEN))


def test_sbe_spawn_semantics():
    if not BANK.exists():
        pytest.skip("SBE bank not built")
    cur = Curriculum(_sbe_cfg(), dict(FROZEN))
    rng = np.random.default_rng(3)
    s0 = cur.spawn(rng)                    # d0 -> witness, zero limiter vel
    assert s0 is not None and "limiter_v" not in s0
    cur.d_idx = 1                          # d1 -> bank entry with velocities
    s1 = cur.spawn(rng)
    assert np.asarray(s1["limiter_v"]).shape == (4, 3)
    assert float(np.linalg.norm(s1["limiter_v"])) > 0.0
    assert "att_speed" in s1 and s1["att_speed"] in (16.0, 20.0, 24.0)
    fn = cur.eval_spawn_fn()
    a, b = fn(7), fn(7)                    # deterministic per episode
    assert np.allclose(a["limiters"], b["limiters"])
    cur.d_idx = len(cur.sbe_stages) - 1    # nominal
    assert cur.spawn(rng) is None and cur.eval_spawn_fn() is None


def test_sbe_gate_advance_backoff_cap():
    if not BANK.exists():
        pytest.skip("SBE bank not built")
    cur = Curriculum(_sbe_cfg(), dict(FROZEN))
    cur.on_eval(10, _ev(0.60), dict(FZ0))  # LCB(48/80)=~.51 > .45 -> advance
    assert cur.d_idx == 1
    cur.on_eval(20, _ev(0.10), dict(FZ0))  # UCB(8/80)=~.17 < .40-.05 -> back
    assert cur.d_idx == 0
    cur.on_eval(30, _ev(0.46), dict(FZ0))  # LCB(37/80)=~.37 < .45 -> hold
    assert cur.d_idx == 0
    assert any(h.get("event") == "backoff" for h in cur.history)
    cur2 = Curriculum(_sbe_cfg(max_steps=50), dict(FROZEN))
    cur2.on_eval(100, _ev(0.9), dict(FZ0))
    assert cur2._capped and cur2.d_idx == 0
    d = cur2.describe()
    assert d["mode"] == "sbe" and d["capped"] and d["gate_episodes"] == 80


def test_a3d_config_sane():
    cfgp = ROOT / "configs/m3a_a3d_pilot.yaml"
    if not cfgp.exists():
        pytest.skip("a3d config absent")
    c = yaml.safe_load(open(cfgp))
    assert c["a3d"]["teacher_gate"] and c["a3d"]["freeze_finisher"]
    assert tuple(c["a3d"]["phi"]["seeds"]) == PHI_SEEDS_TRAIN
    st = c["curriculum"]["sbe"]["stages"]
    ks = [s["k"] for s in st[:-1]]
    assert ks == sorted(ks) and st[-1]["nominal"] and st[0]["k"] == 0
    exits = [s["exit"] for s in st[:-1]]
    assert exits == sorted(exits, reverse=True)
    assert c["curriculum"]["sbe"]["max_steps"] >= 6 * 2 * 20480  # budget rule
    assert c["m3"] == yaml.safe_load(
        open(ROOT / "configs/m3a_a3b_pilot.yaml"))["m3"]   # judgment identical
