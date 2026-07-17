"""0-d SS8-1 gain-scan locks (docs/18 RATIFIED; docs/09 (zz)). torch-free.

Locks: (1) tune-variant reset seeds are disjoint from dev/sealed and the
known seed families; (2) the pre-registered selection rule (argmax ->
simpler -> neutral -> deterministic) as a pure function; (3) tune bundle
generation is deterministic; (4) the tuning-episode subset is the FIRST
--eps-per-cell per (stage, speed) by ep order.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from shepherd.scripts.a3d_bundle_gen import PER_SPEED, VARIANTS, SPEEDS
from shepherd.scripts.a3d_gain_scan import _eps_subset, select_gains

ROOT = pathlib.Path(__file__).resolve().parents[1]
BANK = ROOT / "results/a3d_sbe_bank.json"
KS = (1, 2, 4, 8)


def _seed_range(variant):
    base = VARIANTS[variant]["seed_base"]
    lo = base + 10_000 * min(KS)
    hi = base + 10_000 * max(KS) + 3 * PER_SPEED   # 90 eps per stage
    return lo, hi


def test_tune_seed_family_disjoint():
    ranges = {v: _seed_range(v) for v in ("dev", "sealed", "tune")}
    for a in ranges:
        for b in ranges:
            if a >= b:
                continue
            (lo1, hi1), (lo2, hi2) = ranges[a], ranges[b]
            assert hi1 < lo2 or hi2 < lo1, f"{a} overlaps {b}"
    lo, hi = ranges["tune"]
    # known families (a3d_bundle_gen docstring + history)
    for fam in (500_000 + 400, 1_500_000 + 400, 2_500_000 + 400,
                31_000_000, 61, 75, 100, 209, 90_000 + 7 * 119):
        assert not (lo <= fam <= hi)
    # rng streams: tune 81k family tops out below the 90k random-arm family
    rng_hi = VARIANTS["tune"]["rng_base"] + 1_000 * max(KS) + int(max(SPEEDS))
    assert rng_hi < 90_000
    assert VARIANTS["tune"]["rng_base"] > VARIANTS["dev"]["rng_base"] + 8_024


def test_select_gains_preregistered_rule():
    # argmax wins
    pooled = {(0.5, 0.5): {"arr": 10, "n": 120},
              (1.0, 1.0): {"arr": 30, "n": 120},
              (2.0, 2.0): {"arr": 20, "n": 120}}
    assert select_gains(pooled)["c_p"] == 1.0
    # tie -> smaller c_p + c_d
    pooled = {(2.0, 2.0): {"arr": 30, "n": 120},
              (0.5, 1.0): {"arr": 30, "n": 120}}
    c = select_gains(pooled)
    assert (c["c_p"], c["c_d"]) == (0.5, 1.0)
    # tie on sum -> closest to neutral (1,1)
    pooled = {(0.5, 2.0): {"arr": 30, "n": 120},
              (1.0, 1.5): {"arr": 30, "n": 120}}
    c = select_gains(pooled)
    assert (c["c_p"], c["c_d"]) == (1.0, 1.5)
    # full tie -> smaller c_p then c_d (deterministic)
    pooled = {(2.0, 0.5): {"arr": 30, "n": 120},
              (0.5, 2.0): {"arr": 30, "n": 120}}
    c = select_gains(pooled)
    assert (c["c_p"], c["c_d"]) == (0.5, 2.0)


def test_eps_subset_first_n_per_speed():
    eps = [{"ep": i, "att_speed": SPEEDS[i % 3], "x": i} for i in range(30)]
    sub = _eps_subset({"episodes": eps}, 2)
    assert len(sub) == 6
    for v in SPEEDS:
        got = [e["ep"] for e in sub if e["att_speed"] == v]
        want = sorted(e["ep"] for e in eps if e["att_speed"] == v)[:2]
        assert got == want


@pytest.mark.skipif(not BANK.exists(), reason="bank artifact not present")
def test_tune_bundle_deterministic():
    from shepherd.scripts.a3d_bundle_gen import build_bundle
    bank = json.loads(BANK.read_text())
    stages = {"d1": (1, 0.005), "d2": (2, 0.01)}
    a = build_bundle("tune", bank, stages)
    b = build_bundle("tune", bank, stages)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    # jitter differs from dev (different rng stream)
    d = build_bundle("dev", bank, stages)
    assert json.dumps(a["d1"]["episodes"][0]["spawn"]) != \
        json.dumps(d["d1"]["episodes"][0]["spawn"])
    assert a["d1"]["seed0"] == 8_010_000
