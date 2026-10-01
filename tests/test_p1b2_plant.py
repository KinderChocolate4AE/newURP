"""P1b-2 manifest seal + readout gate (power check, classification) tests."""
from __future__ import annotations

import json

import scripts.p1b2_plant as p1b2
from scripts.p1b2_plant_manifest import MANIFEST, TAUS, build


def test_manifest_is_sealed_and_bounded():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "b0d84cd58cc091f9"
    assert saved["arms"]["tau_a_over_tau0"] == [0.0, 0.1, 0.3] == TAUS
    assert saved["evaluation"]["namespace"] == "p1b2_plant_v1"
    assert saved["evaluation"]["seed0"] == 201000
    assert saved["evaluation"]["episodes_total"] == 840
    assert "power check" in saved["gate"]["invalid"][4]
    assert "vacuous" in saved["supersedes"]


def _arm(tau, bins, *, steps_shift=0, commit="abc1234"):
    records = [{"cell_id": f"r{i:02d}c1", "scenario_id": i, "row": i % 14,
                "chi_role": "lo", "chi": 0.5 + 0.01 * i, "eta": 1.0,
                "bin": b, "outcome": b, "fire": b == "N",
                "clean_crossings": 1, "steps": 50 + steps_shift}
               for i, b in enumerate(bins)]
    return {"schema": "p1-ladder-config-v1", "label": "c5_scripted",
            "tau_ratio": tau, "code_commit": commit, "code_dirty_scoped": [],
            "n": len(bins), "counts": {}, "episodes_with_clean_crossing": 0,
            "clean_crossings_total": len(bins), "records": records}


def test_readout_power_check_fails_closed_on_bitidentical_arms(tmp_path, monkeypatch):
    monkeypatch.setattr(p1b2, "OUT", tmp_path)
    monkeypatch.setattr(p1b2, "load_p1b2_manifest",
                        lambda: {**build(), "evaluation":
                                 {**build()["evaluation"], "episodes_per_arm": 4}})
    (tmp_path / "arms").mkdir()
    bins = ["N", "F_other", "N", "F_other"]
    for tau in TAUS:
        (tmp_path / "arms" / f"c5_scripted_{p1b2._tag(tau)}.json").write_text(
            json.dumps(_arm(tau, bins)), encoding="utf-8")
    got = p1b2.readout()
    assert got["decision"] == "INVALID_P1B2"            # 전 arm bit-identical = vacuous
    assert not got["integrity"]["power"]

    for tau in (0.1, 0.3):                              # tau arm 이 실제로 다르면 통과
        (tmp_path / "arms" / f"c5_scripted_{p1b2._tag(tau)}.json").write_text(
            json.dumps(_arm(tau, bins, steps_shift=1)), encoding="utf-8")
    got = p1b2.readout()
    assert got["decision"] == "COMPLETE_P1B2"
    assert got["classification"]["verdict"] in (
        "PM_ABSTRACTION_HOLDS_ON_TESTED_CELLS", "AIRFRAME_RESIDUAL_CANDIDATE")
