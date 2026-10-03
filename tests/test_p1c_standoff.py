"""P1c manifest seal tests."""
from __future__ import annotations

import json

from scripts.p1c_standoff import _overrides
from scripts.p1c_standoff_manifest import ATTACKERS, MANIFEST, SCALES, build


def test_manifest_is_sealed_fresh_and_bounded():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "6fc93fde71b38a30"
    assert saved["world_variants"]["scales"] == [1, 2, 4] == SCALES
    assert saved["evaluation"]["namespace"] == "p1c_standoff_v1"
    assert saved["evaluation"]["seed0"] == 241000
    assert saved["evaluation"]["episodes_total"] == 3360
    assert "OUTSIDE the sealed B0 v3 contract" in saved["world_variants"]["rule"]
    assert "power" in saved["gate"]["invalid"][4]
    assert all(a["overrides"]["sense_range"] == "inf" for a in ATTACKERS)


def test_overrides_restore_inf():
    assert _overrides(ATTACKERS[0]) == {"route_gain": 0.5,
                                        "sense_range": float("inf")}
