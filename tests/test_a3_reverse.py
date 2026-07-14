"""A-3 L-reverse (docs/13 v0.1, R-1..R-5 ratified 2026-07-14; docs/09 (dd)).

Locks:
  * spawn bank: probe frame STRICT check, T0 loading, spawn_from determinism
    (sigma=0 reproduces the witness; rewind moves BACK along the approach);
  * reset_to: TRAIN-ONLY injection reproduces capture-grade viability at the
    injected state (R-1, env-level); finisher never moved;
  * eval isolation (R-5): held-out harness has no spawn path; the judgment
    bundle call is spawn-free by default;
  * Curriculum "reverse": overrides() always None (frozen constants + judgment
    m3); spawn()/eval_spawn_fn() stage semantics; advance/backoff/cap; R5 exit
    needs nominal stage AND held-out clean nonzero last-N;
  * configs: pilot vs warmref differ ONLY in warm_start (+wandb group).
torch-free.
"""
from __future__ import annotations

import copy
import inspect
import pathlib

import numpy as np
import pytest
import yaml

from shepherd.env_m3 import M3Params
from shepherd.train import spawn_bank as sb
from shepherd.train.make_env_m3 import Curriculum, M3Adapter, make_m3_train_env

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROBE_GLOB = str(ROOT / "results/p4_probe/probe_s*.json")
ENV_CFG = yaml.safe_load(open(ROOT / "configs/m2_l2_train.yaml"))
FROZEN = {"half_angle": 0.067, "theta_fire": 0.9, "sigma_g": 1.0, "w_g": 0.3}


def _m3():
    rw = ENV_CFG["reward"]
    return M3Params(l1=float(rw["lambda1"]), l2=float(rw["lambda2"]),
                    l3=float(rw["lambda3"]))


# --------------------------------------------------------------- spawn bank ---
def test_load_t0_capture_grade_only():
    states = sb.load_t0(PROBE_GLOB)
    assert len(states) >= 1
    for t0 in states:
        assert t0.worst >= 1.0 and t0.p_feas > 0.0
        assert np.asarray(t0.limiters, float).shape == (4, 3)


def test_frame_check_strict():
    sb.check_frame(ENV_CFG)                       # layout finisher_p0 == apex
    bad = copy.deepcopy(ENV_CFG)
    bad["train"]["layout"]["finisher_p0"] = [3.0, 0.0, 0.0]
    with pytest.raises(ValueError, match="apex"):
        sb.check_frame(bad)


def test_spawn_from_deterministic_and_rewind():
    t0 = sb.load_t0(PROBE_GLOB)[0]
    s = sb.spawn_from(t0)                         # sigma=0, no rng
    assert np.allclose(s["att_p"], [t0.x, 0, 0])
    assert np.allclose(s["att_v"], [-t0.v, 0, 0])
    assert np.allclose(s["limiters"], np.asarray(t0.limiters, float))
    r = sb.spawn_from(t0, rewind_dx=5.0)          # back along approach = +x
    assert np.allclose(r["att_p"], [t0.x + 5.0, 0, 0])
    assert np.allclose(r["att_v"], s["att_v"])
    rng1 = np.random.default_rng(7)
    rng2 = np.random.default_rng(7)
    j1 = sb.spawn_from(t0, rng1, sigma_pos=0.5, sigma_vel=0.05)
    j2 = sb.spawn_from(t0, rng2, sigma_pos=0.5, sigma_vel=0.05)
    assert np.allclose(j1["limiters"], j2["limiters"])
    assert np.allclose(j1["att_v"], j2["att_v"])
    assert not np.allclose(j1["limiters"], s["limiters"])


# ------------------------------------------------------------------ reset_to ---
def test_reset_to_reproduces_capture_grade_and_keeps_finisher():
    t0 = sb.load_t0(PROBE_GLOB)[0]
    env, _, _ = make_m3_train_env(copy.deepcopy(ENV_CFG), _m3(), stage=None)
    obs, _ = env.reset_to(sb.spawn_from(t0), seed=t0.union_seed)
    tail = np.asarray(obs[env.possible_agents[0]], float)[-3:]
    theta = float(ENV_CFG["fire_gate"]["theta_fire"])
    assert tail[0] >= theta and tail[2] > 0.0     # v_soft, p_feasible
    fin = env.backend.by_name(env.finisher_id)
    assert np.allclose(fin.p, ENV_CFG["train"]["layout"]["finisher_p0"])
    att = env.backend.by_name(env.adversary_id)
    assert np.allclose(att.p, [t0.x, 0, 0])
    bad = sb.spawn_from(t0)
    bad["limiters"] = np.zeros((2, 3))
    with pytest.raises(ValueError, match="shape"):
        env.reset_to(bad, seed=0)


def test_adapter_reset_to_passthrough():
    t0 = sb.load_t0(PROBE_GLOB)[0]
    env, _, _ = make_m3_train_env(copy.deepcopy(ENV_CFG), _m3(), stage=None)
    ad = M3Adapter(env)
    obs, state = ad.reset_to(sb.spawn_from(t0), seed=t0.union_seed)
    assert set(obs) == set(env.possible_agents)
    assert np.asarray(state, float).ndim == 1


# ------------------------------------------------------- eval isolation (R-5) ---
def test_heldout_harness_has_no_spawn_path():
    from shepherd.scripts import eval_heldout_m3
    src = inspect.getsource(eval_heldout_m3)
    assert "reset_to" not in src and "spawn" not in src


def test_eval_bundle_default_is_spawn_free():
    # source-text lock (train_m3a imports torch; keep this suite t-free):
    src = (ROOT / "shepherd/scripts/train_m3a.py").read_text(encoding="utf-8")
    assert "spawn_fn=None) -> dict:" in src        # default = spawn-free
    ev = src.split("def evaluate(")[1].split("def save(")[0]
    frozen_call = ev.split("frozen_ev = m3_eval_bundle(")[1].split(")")[0]
    assert "spawn_fn" not in frozen_call           # judgment bundle spawn-free


# ------------------------------------------------------- Curriculum: reverse ---
def _rv_cfg(**over):
    rv = {"probe_glob": PROBE_GLOB, "verify_t0": False,
          "stages": [
              {"name": "r1", "sigma_pos": 0.5, "sigma_vel": 0.05,
               "rewind_dx": 0.0, "exit_clean": 0.5},
              {"name": "r2", "sigma_pos": 1.0, "sigma_vel": 0.05,
               "rewind_dx": 0.0, "exit_clean": 0.3},
              {"name": "r3", "sigma_pos": 2.0, "sigma_vel": 0.05,
               "rewind_dx": 5.0, "exit_clean": 0.2},
              {"name": "r5", "nominal": True}],
          "advance_sustain": 2, "stall_evals": 3, "max_steps": 10_000}
    rv.update(over)
    return {"mode": "reverse", "reverse": rv,
            "s2_exit": {"heldout_clean_nonzero_last": 3}}


GOOD = {"clean_cross_rate": 1.0, "boxed_fire_rate": 0.0, "fire_rate": 1.0}
BAD = {"clean_cross_rate": 0.0, "boxed_fire_rate": 0.0, "fire_rate": 0.0}
FZ0 = {"clean_cross_rate": 0.0}


def test_reverse_overrides_always_none_and_spawn_semantics():
    cur = Curriculum(_rv_cfg(), dict(FROZEN))
    assert cur.stage == "s2" and cur.overrides(0) is None
    rng = np.random.default_rng(3)
    s = cur.spawn(rng)
    assert s is not None and s["limiters"].shape == (4, 3)
    fn = cur.eval_spawn_fn()
    a, b = fn(5), fn(5)                            # deterministic per episode
    assert np.allclose(a["limiters"], b["limiters"])
    cur.r_idx = len(cur.rv_stages) - 1             # nominal stage
    assert cur.spawn(rng) is None and cur.eval_spawn_fn() is None


def test_reverse_advance_backoff_cap():
    cur = Curriculum(_rv_cfg(), dict(FROZEN))
    for i in range(2):                             # sustain=2 -> advance to r2
        cur.on_eval(10 + i, dict(GOOD), dict(FZ0))
    assert cur.r_idx == 1
    for i in range(3):                             # stall 3 bad -> backoff
        cur.on_eval(20 + i, dict(BAD), dict(FZ0))
    assert cur.r_idx == 0
    assert any(h.get("event") == "backoff" for h in cur.history)
    cur2 = Curriculum(_rv_cfg(max_steps=50), dict(FROZEN))
    cur2.on_eval(100, dict(GOOD), dict(FZ0))       # beyond cap -> freeze
    assert cur2._capped
    for i in range(4):
        cur2.on_eval(110 + i, dict(GOOD), dict(FZ0))
    assert cur2.r_idx == 0
    d = cur2.describe()
    assert d["mode"] == "reverse" and d["capped"] is True and d["n_t0"] >= 1


def test_reverse_exit_only_from_nominal_with_heldout():
    cur = Curriculum(_rv_cfg(), dict(FROZEN))
    # r1 -> r2 -> r3 -> r5(nominal): 2 good evals each
    for step in range(6):
        assert cur.on_eval(step, dict(GOOD), {"clean_cross_rate": 0.2}) is None
    assert cur.rv_stages[cur.r_idx].get("nominal")
    # heldout window: needs last-3 nonzero AFTER reaching nominal history
    assert cur.on_eval(10, dict(GOOD), {"clean_cross_rate": 0.2}) == "s3"
    assert cur.overrides(11) is None and cur.spawn(
        np.random.default_rng(0)) is None


def test_reverse_requires_nominal_terminal_stage():
    bad = _rv_cfg()
    bad["reverse"]["stages"] = bad["reverse"]["stages"][:-1]   # drop r5
    with pytest.raises(ValueError, match="nominal"):
        Curriculum(bad, dict(FROZEN))
    need_env = _rv_cfg(verify_t0=True)
    with pytest.raises(ValueError, match="env_cfg"):
        Curriculum(need_env, dict(FROZEN))


# ------------------------------------------------------------------- configs ---
def test_a3_configs_differ_only_in_warm_start():
    pilot = yaml.safe_load(open(ROOT / "configs/m3a_a3_pilot.yaml"))
    warm = yaml.safe_load(open(ROOT / "configs/m3a_a3_warmref.yaml"))
    assert pilot["warm_start"]["enabled"] is False
    assert warm["warm_start"]["enabled"] is True
    diff = [k for k in pilot if pilot[k] != warm.get(k)]
    assert set(diff) == {"warm_start", "wandb"}
    st = pilot["curriculum"]["reverse"]["stages"]
    assert st[-1].get("nominal") and len(st) == 5
    assert pilot["curriculum"]["mode"] == "reverse"
    assert pilot["m3"] == warm["m3"]               # judgment identical


# ----------------------------------------------------- A-3b (docs/13 SS8) ---
BANK = ROOT / "results/a3_robust_bank.json"


def test_robust_bank_loads_and_gates():
    if not BANK.exists():
        pytest.skip("robust bank not built yet")
    states = sb.load_t0(str(BANK))
    assert len(states) >= 3                        # R-6 target
    surv, report = sb.verify_t0(states, copy.deepcopy(ENV_CFG),
                                robust_seeds=tuple(range(7, 12)),
                                robust_min=0.8)
    assert len(surv) >= 2
    for r in report:
        assert r["robust_min"] == 0.8 and r["robust_clean_frac"] is not None


def test_verify_robust_gate_drops_fragile():
    states = sb.load_t0(PROBE_GLOB)                # old fragile bank
    surv, report = sb.verify_t0(states, copy.deepcopy(ENV_CFG),
                                robust_seeds=tuple(range(100, 105)),
                                robust_min=0.9)
    # (ff): 3/4 old witnesses are sample-fragile -> gate must drop some
    assert len(surv) < len(states)
    with pytest.raises(ValueError, match="robust_seeds"):
        sb.verify_t0(states, copy.deepcopy(ENV_CFG), robust_seeds=(),
                     robust_min=0.9)


def test_probe_transplant_math():
    from shepherd.scripts.a3_robust_witness_probe import transplant
    t0s = sb.load_t0(PROBE_GLOB)
    donor = max(t0s, key=lambda t: (t.x, t.v))     # x20v24
    L = transplant(donor, 16.0, 20.0)
    rel_d = np.asarray(donor.limiters, float) - [donor.x, 0, 0]
    rel_t = L - np.array([16.0, 0, 0])
    assert np.allclose(rel_t[:, 1:], rel_d[:, 1:])           # lateral kept
    assert np.allclose(rel_t[:, 0], rel_d[:, 0] * (20.0 / donor.v))


def test_a3b_config_ladder_sane():
    cfgp = ROOT / "configs/m3a_a3b_pilot.yaml"
    if not cfgp.exists():
        pytest.skip("a3b config not present")
    c = yaml.safe_load(open(cfgp))
    rv = c["curriculum"]["reverse"]
    st = rv["stages"]
    assert st[0]["sigma_pos"] == 0.0 and st[-1].get("nominal")
    sigs = [s["sigma_pos"] for s in st[:-1]]
    assert sigs == sorted(sigs)                    # monotone widening
    assert rv["verify_robust_min"] >= 0.9 and len(rv["verify_robust_seeds"]) >= 10
    assert rv["probe_glob"].endswith("a3_robust_bank.json")
