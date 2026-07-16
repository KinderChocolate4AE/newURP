"""Phase 0-b bundles (docs/09 (ss)). torch-free.

Locks: balanced strata (30 x {16,20,24} per stage); dev/sealed reset-seed
disjointness (and from historical seed families); deterministic regeneration;
materialized spawn schema consumable by the V-4' pin path; jitter respects
the per-stage sigma_pos (its scale, not exact draws).
"""
from __future__ import annotations

import collections
import json
import pathlib

import numpy as np
import yaml

from shepherd.scripts.a3d_bundle_gen import (PER_SPEED, SPEEDS, VARIANTS,
                                             _stage_sigmas, build_bundle)
from shepherd.train.make_env_m3 import (gating_env_for_spawn,
                                        m3_params_from_cfg)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEV = ROOT / "results/a3d_bundle_dev.json"
SEALED = ROOT / "results/a3d_bundle_sealed.json"


def _load(p):
    return json.loads(p.read_text())


def test_balance_and_sizes():
    for path in (DEV, SEALED):
        doc = _load(path)
        assert set(doc["stages"]) == {"d1", "d2", "d3", "d4"}
        for st in doc["stages"].values():
            eps = st["episodes"]
            assert len(eps) == PER_SPEED * len(SPEEDS)
            c = collections.Counter(e["att_speed"] for e in eps)
            assert all(c[v] == PER_SPEED for v in SPEEDS)


def test_seed_disjointness_and_contiguity():
    dev, sealed = _load(DEV), _load(SEALED)
    d_seeds, s_seeds = set(), set()
    for doc, acc in ((dev, d_seeds), (sealed, s_seeds)):
        for st in doc["stages"].values():
            seeds = [e["reset_seed"] for e in st["episodes"]]
            assert seeds == list(range(st["seed0"],
                                       st["seed0"] + len(seeds)))
            acc.update(seeds)
    assert not (d_seeds & s_seeds)
    historical = set(range(500000, 500080)) | set(range(1500003, 1500083)) \
        | set(range(2500006, 2500086)) | set(range(100, 110)) \
        | set(range(200, 210)) | set(range(61, 76))
    assert not ((d_seeds | s_seeds) & historical)


def test_deterministic_regeneration():
    run_cfg = yaml.safe_load((ROOT / "configs/m3a_a3d_pilot.yaml").read_text())
    bank = json.loads(
        (ROOT / run_cfg["curriculum"]["sbe"]["bank"]).read_text())
    stages = _stage_sigmas(run_cfg)
    again = build_bundle("dev", bank, stages)
    assert json.dumps(again, sort_keys=True) == json.dumps(
        _load(DEV)["stages"], sort_keys=True)


def test_spawn_schema_and_pin_consumable():
    doc = _load(DEV)
    run_cfg = yaml.safe_load((ROOT / "configs/m3a_a3d_pilot.yaml").read_text())
    env_cfg = yaml.safe_load((ROOT / run_cfg["env_config"]).read_text())
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    e = doc["stages"]["d2"]["episodes"][0]
    sp = e["spawn"]
    for k in ("limiters", "limiter_v", "att_p", "att_v", "att_speed"):
        assert k in sp
    assert np.asarray(sp["limiters"]).shape == (4, 3)
    assert np.asarray(e["demo_accels"]).shape[1:] == (4, 3)
    env, _, _ = gating_env_for_spawn(env_cfg, m3, sp)
    assert abs(float(env.v_nominal) - float(sp["att_speed"])) < 1e-12


def test_jitter_scale_matches_stage_sigma():
    run_cfg = yaml.safe_load((ROOT / "configs/m3a_a3d_pilot.yaml").read_text())
    bank = json.loads(
        (ROOT / run_cfg["curriculum"]["sbe"]["bank"]).read_text())
    doc = _load(DEV)
    for sname, st in doc["stages"].items():
        sig = float(st["sigma_pos"])
        devs = []
        for e in st["episodes"]:
            base = np.asarray(bank["entries"][e["entry_idx"]]
                              ["spawn"]["limiters"], float)
            devs.append(np.abs(np.asarray(e["spawn"]["limiters"]) - base))
        d = np.concatenate([x.ravel() for x in devs])
        assert d.max() < 6.0 * sig + 1e-12
        assert 0.4 * sig < d.std() < 1.6 * sig
