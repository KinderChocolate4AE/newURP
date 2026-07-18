"""A-3e freeze locks (docs/21 v0.3; docs/09 (kkk)). t-free.

Locks: (1) frozen numbers (cadence/caps/gates/total); (2) the 3-phase
machine's every transition incl. L1 fail-without-unfreeze and J1 stall
recording; (3) paired-delta rng-777 determinism; (4) selective-fire
diagnostics; (5) best-ckpt lexicographic order; (6) E-5 pledged test --
ALL spawn-jitter derivations enumerated pairwise-distinct + new reset-seed
bands disjoint from every legacy family; (7) spawner admissible filter and
draw determinism; (8) bundle composition/order/seed formula determinism;
(9) sealed guards x4 (content-keyed); (10) zero-cache pairing contract."""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from shepherd.train import a3e as A

BANK = pathlib.Path("results/a3d_sbe_bank_v2.json")
VAL = pathlib.Path("results/a3d_bank_v2_validation.json")
RB = pathlib.Path("results/a3_robust_bank_v2.json")
have_artifacts = BANK.exists() and VAL.exists() and RB.exists()


# ------------------------------------------------------------ frozen numbers
def test_frozen_numbers():
    assert A.CADENCE == 20_480
    assert A.PHASE_MAX_EVALS == {"F0": 6, "L1": 8, "J1": 8}
    assert A.TOTAL_CAP_STEPS == 450_560
    assert (A.CONSEC, A.F0_EXIT, A.DELTA_GATE) == (2, 0.45, 0.10)
    assert (A.STALL_UCB, A.STALL_N) == (0.05, 3)
    assert (A.BOOT_N, A.BOOT_SEED) == (10_000, 777)
    assert A.D1_SIGMA == 0.005


# ------------------------------------------------------------- phase machine
def _f0(x):
    return {"captured_rate": x}


def test_f0_advance_and_consec_reset():
    ph = A.A3EPhases()
    assert ph.on_eval(_f0(0.5)) is None
    assert ph.on_eval(_f0(0.1)) is None          # consec reset
    assert ph.on_eval(_f0(0.5)) is None
    assert ph.on_eval(_f0(0.45)) == "advance_L1"  # inclusive >= 0.45
    assert ph.phase == "L1" and ph.evals_in_phase == 0


def test_f0_fail_at_cap():
    ph = A.A3EPhases()
    for i in range(6):
        ev = ph.on_eval(_f0(0.2))
    assert ev == "fail" and ph.failed == "F0_fire_bootstrap"
    assert ph.on_eval(_f0(0.9)) is None          # terminal no-op


def test_l1_fail_without_unfreeze():
    ph = A.A3EPhases()
    ph.phase = "L1"
    for _ in range(8):
        ev = ph.on_eval({"delta_teacher": 0.05})
    assert ev == "fail" and ph.failed == "L1_limiter_shaping"
    assert ph.phase == "L1"                      # never reached J1


def test_l1_to_j1_and_exit():
    ph = A.A3EPhases()
    ph.phase = "L1"
    ph.on_eval({"delta_teacher": 0.2})
    assert ph.on_eval({"delta_teacher": 0.11}) == "advance_J1"
    assert ph.phase == "J1"
    ph.on_eval({"delta_free": 0.2, "ucb95": 0.5})
    assert ph.on_eval({"delta_free": 0.12, "ucb95": 0.5}) == "J1_exit"
    assert ph.passed_exit and not ph.failed


def test_j1_gate_strict_and_cap_and_stall():
    ph = A.A3EPhases()
    ph.phase = "J1"
    evs = []
    for _ in range(8):
        evs.append(ph.on_eval({"delta_free": 0.10, "ucb95": 0.01}))  # not >
    assert evs[-1] == "J1_cap" and not ph.passed_exit and not ph.failed
    assert any(h["event"] == "stall_recorded" for h in ph.history)


# ------------------------------------------------------- gate math and diags
def test_paired_delta_deterministic():
    pol = [1] * 60 + [0] * 60
    zero = [0] * 30 + [1] * 10 + [0] * 80
    a = A.paired_delta(pol, zero)
    b = A.paired_delta(pol, zero)
    assert a == b
    assert abs(a["delta_hat"] - (60 - 10) / 120) < 1e-12
    assert a["lcb95"] <= a["delta_hat"] <= a["ucb95"]


def test_diagnostics():
    rows = [
        {"clean": True, "n_fires": 1, "reset_clean": False, "captured": True},
        {"clean": True, "n_fires": 0, "reset_clean": False,
         "captured": False},
        {"clean": False, "n_fires": 1, "reset_clean": False,
         "captured": False},
        {"clean": False, "n_fires": 0, "reset_clean": True, "captured": True},
    ]
    d = A.diagnostics(rows)
    assert d["p_fire_given_clean"] == 0.5
    assert d["p_fire_given_nonclean"] == 0.5
    assert abs(d["p_capture_given_reset_nonclean"] - 1 / 3) < 1e-12
    assert A.diagnostics([{"clean": True, "n_fires": 1, "reset_clean": True,
                           "captured": True}])[
        "p_capture_given_reset_nonclean"] is None


def test_best_ckpt_order():
    worse = A.best_ckpt_key(0.2, 0.1, 3)
    assert A.best_ckpt_key(0.3, 0.5, 9) > worse          # delta first
    assert A.best_ckpt_key(0.2, 0.05, 9) > worse         # then false fire
    assert A.best_ckpt_key(0.2, 0.1, 2) > worse          # then EARLIER
    assert A.best_ckpt_key(0.2, None, 1) < worse         # None -> worst pf


# ------------------------------------------------- E-5: derivations disjoint
def test_jitter_derivations_enumerated_disjoint():
    ks_bundle, vs = (0, 1, 2, 4, 8), (16, 20, 24)
    seen = {}

    def add(name, s):
        assert s not in seen, f"{name} collides with {seen.get(s)} at {s}"
        seen[s] = name

    for base, nm in ((71_000, "dev_v1"), (81_000, "tune"),
                     (93_000, "sealed_v1")):
        for k in ks_bundle:
            for v in vs:
                add(nm, base + 1_000 * k + v)
    for base, nm in ((75_000, "dev_v2d1"), (95_000, "sealed_v2d1")):
        for v in (16, 20):
            add(nm, base + 1_000 * 1 + v)
    cells = ((1, 16), (2, 16), (1, 20), (2, 20), (2, 24), (4, 24), (8, 24))
    for k, v in cells:
        add("bankv2_val", 76_000 + 1_000 * k + v)
    for v in (16, 20):
        add("harvest", 300_000 + 1_000 * 1 + v)
    for k in (2, 4, 8):
        for v in (16, 20):
            add("rewind_val", 310_000 + 1_000 * k + v)
    for v in (16, 20, 24):
        add("comparator", 320_000 + 1_000 * 2 + v)


def test_new_reset_bands_disjoint_from_legacy():
    new = (set(range(700, 750)) | set(range(750, 770))
           | set(range(800, 900))
           | {12_000_000 + i for i in range(40)}
           | {12_010_000 + i for i in range(120)}
           | {13_000_000 + i for i in range(40)}
           | {13_010_000 + i for i in range(120)})
    legacy = (set(range(300, 320)) | set(range(400, 420))
              | set(range(420, 440)) | set(range(600, 700))
              | {500_000, 1_500_000, 2_500_000, 31_000_000}
              | {7_000_000 + 10_000 * k + i for k in (0, 1, 2, 4, 8)
                 for i in range(400)}
              | {8_000_000 + 10_000 * k + i for k in (0, 1, 2, 4, 8)
                 for i in range(400)}
              | {9_000_000 + 10_000 * k + i for k in (0, 1, 2, 4, 8)
                 for i in range(400)})
    assert not (new & legacy)


# ------------------------------------------------------- spawner + bundles
@pytest.mark.skipif(not have_artifacts, reason="bank artifacts absent")
def test_spawner_admissible_and_deterministic():
    sp = A.A3ESpawner(str(RB), str(BANK), str(VAL))
    assert sorted(sp.adm_speeds) == [16.0, 20.0]
    assert len(sp.t0) == 2 and len(sp.d1) == 24
    s1 = sp.d1_spawn(np.random.default_rng(5))
    s2 = sp.d1_spawn(np.random.default_rng(5))
    assert json.dumps(np.asarray(s1["limiters"]).tolist()) == \
        json.dumps(np.asarray(s2["limiters"]).tolist())
    d0 = sp.d0_spawn(np.random.default_rng(3))
    # spawn_from contract: no limiter_v key => adapter resets limiter
    # velocities to zero (the established d0/A-3b R0 anchor semantics)
    assert "limiter_v" not in d0 and "limiters" in d0


@pytest.mark.skipif(not have_artifacts, reason="bank artifacts absent")
def test_bundle_composition_and_determinism():
    from shepherd.scripts import a3e_bundle_gen as G
    sp = A.A3ESpawner(str(RB), str(BANK), str(VAL))
    b1 = G.build_bundle("dev_v2d1", sp)
    b2 = G.build_bundle("dev_v2d1", sp)
    assert json.dumps(b1, sort_keys=True) == json.dumps(b2, sort_keys=True)
    d0 = b1["stages"]["d0"]["episodes"]
    d1 = b1["stages"]["d1"]["episodes"]
    assert len(d0) == 40 and len(d1) == 120
    assert [e["reset_seed"] for e in d0] == \
        [12_000_000 + i for i in range(40)]
    assert [e["reset_seed"] for e in d1] == \
        [12_010_000 + i for i in range(120)]
    assert [e["cell"] for e in d1] == ["v16"] * 60 + ["v20"] * 60
    assert [e["draw_idx"] for e in d1[:10]] == [0] * 5 + [1] * 5
    sealed = G.build_bundle("sealed_v2d1", sp)
    assert sealed["meta"]["sealed"] is True
    assert [e["reset_seed"] for e in
            sealed["stages"]["d0"]["episodes"][:2]] == [13_000_000,
                                                        13_000_001]
    # same draws, different jitter stream -> spawns must differ from dev
    assert (d1[0]["spawn"]["limiters"]
            != sealed["stages"]["d1"]["episodes"][0]["spawn"]["limiters"])


# ------------------------------------------------------------- sealed guards
def _mini_bundle(tmp, sealed, with_manifest=True, tamper=False):
    from shepherd.scripts import a3e_bundle_gen as G
    doc = {"meta": {"variant": "x", "sealed": sealed},
           "stages": {"d0": {"episodes": []}, "d1": {"episodes": []}}}
    p = tmp / "b.json"
    man = G.write_with_manifest(doc, p, {}) if with_manifest else None
    if not with_manifest:
        p.write_text(json.dumps(doc))
    if tamper:
        p.write_text(p.read_text() + " ")
    return p, man


def test_guard_sealed_refused_by_default(tmp_path):
    from shepherd.scripts import a3e_bundle_gen as G
    p, _ = _mini_bundle(tmp_path, sealed=True)
    with pytest.raises(PermissionError):
        G.load_bundle(str(p))


def test_guard_copy_rename_still_refused(tmp_path):
    from shepherd.scripts import a3e_bundle_gen as G
    p, _ = _mini_bundle(tmp_path, sealed=True)
    cp = tmp_path / "innocent_dev_name.json"
    cp.write_text(p.read_text())               # copy w/o manifest
    with pytest.raises(PermissionError):
        G.load_bundle(str(cp), sealed_judgment=False)
    with pytest.raises(PermissionError):       # even judgment needs manifest
        G.load_bundle(str(cp), sealed_judgment=True)


def test_guard_tamper_detected(tmp_path):
    from shepherd.scripts import a3e_bundle_gen as G
    p, _ = _mini_bundle(tmp_path, sealed=False, tamper=True)
    with pytest.raises(PermissionError):
        G.load_bundle(str(p))


def test_guard_single_consumption(tmp_path):
    from shepherd.scripts import a3e_bundle_gen as G
    p, _ = _mini_bundle(tmp_path, sealed=True)
    (tmp_path / "results").mkdir()
    assert G.load_bundle(str(p), sealed_judgment=True,
                         repo_root=str(tmp_path))["meta"]["sealed"]
    G.mark_sealed_consumed(str(tmp_path), note="test")
    with pytest.raises(PermissionError):
        G.load_bundle(str(p), sealed_judgment=True, repo_root=str(tmp_path))


# ---------------------------------------------------------- zero-cache lock
def test_zero_cache_pairing_contract(monkeypatch):
    from shepherd.scripts import a3e_bundle_gen as G
    import shepherd.scripts.a3d_calibration  # noqa: F401  torch stub first
    import shepherd.scripts.train_m3a as T
    calls = []

    def fake_eval(env_cfg, m3, lim_fn, fin_fn, episodes, seed0, stage=None,
                  per_episode=False, spawn_fn=None):
        calls.append((seed0, json.dumps(spawn_fn(0), sort_keys=True)))
        return {"per_episode": [{"arrival_capture": seed0 % 2 == 0,
                                 "reset_clean": False}]}

    monkeypatch.setattr(T, "m3_eval_bundle", fake_eval)
    bundle = {"meta": {}, "stages": {"d1": {"episodes": [
        {"ep": i, "reset_seed": 100 + i, "spawn": {"x": i}}
        for i in range(3)]}}}
    G.attach_zero_cache(bundle, {}, None, 0.9, log=lambda *a, **k: None)
    eps = bundle["stages"]["d1"]["episodes"]
    assert [c[0] for c in calls] == [100, 101, 102]      # exact seeds
    assert [json.loads(c[1])["x"] for c in calls] == [0, 1, 2]   # own spawn
    assert [e["zero_arrival"] for e in eps] == [True, False, True]
    assert bundle["meta"]["zero_cache"]["stage"] == "d1"
