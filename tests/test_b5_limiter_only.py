"""b5 limiter-only 실험의 봉인·namespace·집계 회귀검사 (torch-free)."""
import json
import pathlib

from scripts.b5_limiter_only import _summary_rows
from scripts.b5_limiter_only_manifest import build

ROOT = pathlib.Path(__file__).resolve().parents[1]
PILOT_MANIFEST = ROOT / "artifacts" / "marl" / "b0_v3_pilot_manifest.json"


def test_manifest_build_is_deterministic_and_hashed():
    a, b = build(), build()
    assert a == b
    assert len(a["manifest_hash"]) == 16


def test_namespaces_are_disjoint_from_the_sealed_pilot():
    """pilot의 봉인 280사례·BC·학습 namespace를 재사용하지 않는다 (사후 승격 차단)."""
    pilot = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    b5 = build()
    pairs = [
        (pilot["initialization"]["seed0"], pilot["initialization"]["seed_ns"]),
        (pilot["training"]["seed0"], pilot["training"]["seed_ns"]),
        (pilot["evaluation"]["seed0"], pilot["evaluation"]["seed_ns"]),
        (b5["training"]["seed0"], b5["training"]["seed_ns"]),
        (b5["evaluation"]["seed0"], b5["evaluation"]["seed_ns"]),
    ]
    assert len({p[0] for p in pairs}) == 5      # seed0 전부 다름
    assert len({p[1] for p in pairs}) == 5      # seed_ns 전부 다름


def test_manifest_seals_interpretation_limits_before_results():
    m = build()
    assert m["scope"]["depends_on_scripted_launcher"] is True
    assert "learned cooperation" in m["scope"]["not_evidence_for"]
    assert "W6 entry" in m["scope"]["not_evidence_for"]
    assert m["readout"]["selection_threshold"] is None
    assert "no external forced fire" in m["scope"]["fire_rule"]
    assert "log-prob" in m["scope"]["log_prob_rule"]
    assert m["prerequisites"]["pilot_decision_required"] == "NO_SELECTION"


def test_summary_rows_counts_the_declared_metrics():
    rows = [
        {"bin": "N", "fire": True, "clean_crossings": 3},
        {"bin": "F_other", "fire": True, "clean_crossings": 0},
        {"bin": "H_illegal", "fire": False, "clean_crossings": 1},
        {"bin": "F_other", "fire": False, "clean_crossings": 0},
    ]
    s = _summary_rows(rows)
    assert s["n"] == 4
    assert s["counts"] == {"F_other": 2, "H_illegal": 1, "N": 1}
    assert s["p_N"] == 0.25 and s["p_H_illegal"] == 0.25
    assert s["p_FIRE"] == 0.5
    assert s["episodes_with_clean_crossing"] == 2
