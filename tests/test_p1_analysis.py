"""P1 analysis unit tests (torch-free): pairing, bootstrap, labels, gate.

Synthetic CRN eval files with a KNOWN planted effect; no env / torch needed.
"""
import json

import numpy as np
import pytest

from shepherd.scripts.analyze_p1 import (analyze, boot_summary, check_crn,
                                         is_blocking, load_eval_dir,
                                         seed_stats, to_markdown)


def _rec(ret, truncated=True, penetrated=False, captured=False, ep=0):
    return {"ep": ep, "ret": float(ret), "len": 80 if truncated else 23,
            "headline_sum": float(ret) + 1.5, "clean": False, "wasted": 0.0,
            "captured": captured, "penetrated": penetrated,
            "truncated": truncated, "fire_events": 0, "boxed_steps": 0}


def _write(path, recs):
    path.write_text(json.dumps({"meta": {}, "episodes": recs}))


@pytest.fixture()
def eval_dir(tmp_path):
    rng = np.random.default_rng(0)
    base = [ _rec(3.0 + rng.normal(0, 0.1), truncated=False, penetrated=True,
                  ep=i) for i in range(40) ]
    _write(tmp_path / "scripted.json", base)
    _write(tmp_path / "hold.json",
           [ _rec(0.5 + rng.normal(0, 0.1), truncated=False, penetrated=True,
                  ep=i) for i in range(40) ])
    for s in range(3):                       # armA: baseline + 5 (blocking)
        _write(tmp_path / f"armA_seed{s}.json",
               [ _rec(base[i]["ret"] + 5.0 + rng.normal(0, 0.1), ep=i)
                 for i in range(40) ])
    for s in range(3):                       # armB: baseline + 1 (shaping)
        _write(tmp_path / f"armB_seed{s}.json",
               [ _rec(base[i]["ret"] + 1.0 + rng.normal(0, 0.1),
                      truncated=False, penetrated=True, ep=i)
                 for i in range(40) ])
    return tmp_path


def test_blocking_label():
    assert is_blocking(_rec(1.0, truncated=True))
    assert not is_blocking(_rec(1.0, truncated=False, penetrated=True))
    assert not is_blocking(_rec(1.0, truncated=True, captured=True))


def test_crn_mismatch_raises(eval_dir):
    _write(eval_dir / "armA_seed9.json", [_rec(1.0, ep=0)])   # 1 != 40
    by_arm, bases = load_eval_dir(str(eval_dir), ["armA", "armB"])
    with pytest.raises(ValueError):
        check_crn(by_arm, bases)


def test_seed_stats_margins_and_cost_gap(eval_dir):
    by_arm, bases = load_eval_dir(str(eval_dir), ["armA", "armB"])
    st = seed_stats(by_arm["armA"][0], bases)
    assert st["margin_scripted_mean"] == pytest.approx(5.0, abs=0.15)
    assert st["cost_gap_mean"] == pytest.approx(1.5, abs=1e-6)
    assert st["blocking_rate"] == 1.0 and st["blocking_discovered"]


def test_boot_summary_recovers_point():
    rng = np.random.default_rng(1)
    eps = {s: np.full(30, 2.0) + rng.normal(0, 0.01, 30) for s in range(4)}
    b = boot_summary(eps, rng)
    assert b["point"] == pytest.approx(2.0, abs=0.02)
    assert b["ci95"][0] <= b["point"] <= b["ci95"][1]
    assert b["lower95_one_sided"] >= b["ci95"][0]


def test_analyze_gate_and_paired(eval_dir):
    rep = analyze(str(eval_dir), ["armA", "armB"])
    assert rep["gate"]["armA"]["pass"] is True
    assert rep["gate"]["armA"]["scripted"]["lower95_one_sided"] > 4.0
    assert rep["gate"]["armB"]["pass"] is True          # +1 vs scripted, CRN-paired
    assert rep["arms"]["armA"]["mode_discovery_rate"] == 1.0
    assert rep["arms"]["armB"]["mode_discovery_rate"] == 0.0
    p = rep["paired"]["armA-minus-armB"]
    assert p["point"] == pytest.approx(4.0, abs=0.2)
    assert p["separated"] is True and p["common_seeds"] == [0, 1, 2]
    md = to_markdown(rep, ["armA", "armB"])
    assert "gate: PASS" in md and "paired armA-minus-armB" in md


def test_paired_no_separation(tmp_path):
    rng = np.random.default_rng(2)
    base = [_rec(3.0, truncated=False, penetrated=True, ep=i) for i in range(30)]
    _write(tmp_path / "scripted.json", base)
    for arm in ("armA", "armB"):
        for s in range(3):
            _write(tmp_path / f"{arm}_seed{s}.json",
                   [ _rec(4.0 + rng.normal(0, 1.0), ep=i) for i in range(30) ])
    rep = analyze(str(tmp_path), ["armA", "armB"])
    assert rep["paired"]["armA-minus-armB"]["separated"] is False
