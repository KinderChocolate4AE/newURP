"""P1 ladder manifest seal tests."""
from __future__ import annotations

import json

from scripts.p1_ladder_manifest import MANIFEST, build


def test_manifest_is_sealed_and_bounded():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "4629158d387c938b"
    configs = saved["attacker"]["configs"]
    assert len(configs) == saved["attacker"]["n_configs"] == 24
    assert sum(c["group"] == "main" for c in configs) == 18
    assert sum(c["group"] == "anchor" for c in configs) == 2
    assert sum(c["group"] == "depth" for c in configs) == 4
    labels = [c["label"] for c in configs]
    assert len(set(labels)) == 24
    assert saved["evaluation"]["seed0"] == 191000
    assert saved["p1b_plant_swap"]["seed0"] == 191000      # v1.1: p1a 와 draw 공유
    assert saved["p1b_plant_swap"]["namespace"] == saved["evaluation"]["namespace"]
    assert saved["amendments"]
    assert saved["evaluation"]["episodes_total_p1a"] == 24 * 280
    assert saved["p1b_plant_swap"]["tau_a_over_tau0"] == [0.1, 0.3]
    assert "no_performance_gate" in saved["gate"]
    assert "STOP_RL2" in saved["scope"]["prior_decisions_unchanged"]


def test_namespaces_are_fresh():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    used = {20000, 53000, 71000, 81000, 91000, 101000, 121000, 131000, 141000,
            151000, 161000, 171000, 181000}
    assert saved["evaluation"]["seed0"] not in used
    assert saved["evaluation"]["namespace"] == "p1_ladder_v1"


def test_grid_overrides_are_declared_relative_to_suite_nominal():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_label = {c["label"]: c["overrides"] for c in saved["attacker"]["configs"]}
    assert by_label["t1f_r05_s30_ref"] == {"route_gain": 0.5, "sense_range": 30.0}
    assert by_label["t1f_r08_sinf_antic"] == {"route_gain": 0.8, "sense_range": "inf",
                                              "lam_gain": 1.0, "lam_range": 2.5}
    assert by_label["t0_route0"] == {"route_gain": 0.0}
    assert by_label["depth_lam_zero"]["lam_gain"] == 0.0
    assert by_label["depth_bait_priv"]["bait_privileged"] is True
    assert all("sprint_range" not in o and "slowdown_range" not in o
               for o in by_label.values())
