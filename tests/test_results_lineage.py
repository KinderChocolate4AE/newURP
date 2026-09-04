"""results/ 캠페인 계보 라벨 가드 (results/README.md "캠페인 계보 라벨" 절).

모든 최상위 results/ 항목은 README 표의 정확히 한 캠페인 계보에 속해야 한다.
새 아티팩트가 미분류로 남으면 RED — README 표와 이 패턴 목록을 **같은 커밋**에서
갱신한다. 패턴 목록은 README 표의 기계 판독본이다 (둘이 어긋나면 README 가 정본).
"""
from __future__ import annotations

import fnmatch
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"

LINEAGE = {
    "RETIRED": [
        "m2_*", "ppo_toy", "spike_throughput",
        "ippo*", "coma_run*", "mappo_run*", "p1_eval",
        "c1_corridor",
        "a3*", "m3a_*", "_calib", "p4_probe", "bankv2_*",
        "snapshot_witness*", "witness_margin*", "temporal_support*",
    ],
    "LEGACY-REGIME": [
        "hold_baseline.json", "intercept_baseline.json",
        "curve_hold.json", "curve_intercept.json",
        "fire_audit_probe.json", "fire_gate_calibration.md",
        "boxed_arm_audit*", "contact_*", "coverage_*",
        "handoff_audit.json", "mobility_factorial.json",
        "pk_sweep_audit.json", "slew_counterfactual.json",
        "coupling_gate.json", "latest_start_sweep.json",
        "recoverability_probe.json", "p2prime_*", "prefire_*",
        "viz_trajectories*",
    ],
    "NEXT-BRANCH": [
        "scale_v2_baseline*", "threat_v3_*", "v6_*",
        "m4_v3_train*", "iid_abl", "viz_ls*", "viz_arc.json",
        "viz_hold.json", "arc_tuning_*", "shaping_ceiling*",
    ],
    "CANONICAL": [
        "phase3", "curve_hold_reactive*", "curve_intercept_reactive*",
        "e1*", "e2b_*", "e3_*", "e4*",
        "eta_sensitivity.json", "analytic_bands.json", "lead*",
        "viz_traj_t1_hk*", "viz_e4c_*", "viz_lead_compare.json",
    ],
    "META": ["README.md", ".gitkeep"],
}


def _buckets(name: str) -> list[str]:
    return [status for status, pats in LINEAGE.items()
            if any(fnmatch.fnmatch(name, p) for p in pats)]


def test_every_entry_classified():
    unclassified = [e.name for e in RESULTS.iterdir() if not _buckets(e.name)]
    assert not unclassified, (
        "미분류 results/ 항목 — results/README.md 캠페인 계보 표와 이 목록에 "
        f"추가할 것: {sorted(unclassified)}")


def test_no_ambiguous_entry():
    ambiguous = {e.name: b for e in RESULTS.iterdir()
                 if len(b := _buckets(e.name)) > 1}
    assert not ambiguous, f"두 계보에 겹치는 항목: {ambiguous}"


def test_patterns_not_dead():
    names = [e.name for e in RESULTS.iterdir()]
    dead = [p for pats in LINEAGE.values() for p in pats
            if not any(fnmatch.fnmatch(n, p) for n in names)]
    assert not dead, f"아무것도 매칭하지 않는 패턴 (오타 의심): {dead}"
