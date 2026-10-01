"""Seal the P1 attacker-ladder defender-frozen map (docs/118)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "p1_ladder" / "manifest.json"

# 공칭 = B2/B0 suite 의 resolve() 공격자 (A2, jink 0.6, route 0.5, 주입 sense_range).
# 각 config 는 그 공칭 spec 에 dataclasses.replace 로 적용할 override 만 선언한다.
_LAM = {"ref": {}, "antic": {"lam_gain": 1.0, "lam_range": 2.5},
        "zero": {"lam_gain": 0.0, "lam_range": 1.0}}


def _grid() -> list[dict]:
    configs = []
    for rg, rtag in ((0.2, "r02"), (0.5, "r05"), (0.8, "r08")):
        for sr, stag in ((15.0, "s15"), (30.0, "s30"), (float("inf"), "sinf")):
            for lam in ("ref", "antic"):
                configs.append({"label": f"t1f_{rtag}_{stag}_{lam}", "group": "main",
                                "overrides": {"route_gain": rg, "sense_range": sr,
                                              **_LAM[lam]}})
    rep = {"route_gain": 0.5, "sense_range": 30.0}
    configs += [
        {"label": "t0_route0", "group": "anchor",
         "overrides": {"route_gain": 0.0}},                    # docs/80 T0 (jink 유지)
        {"label": "a1_pure", "group": "anchor",
         "overrides": {"route_gain": 0.0, "jink_amp": 0.0, "sense_range": float("inf")}},
        {"label": "depth_jink0", "group": "depth",
         "overrides": {**rep, "jink_amp": 0.0}},
        {"label": "depth_lam_zero", "group": "depth",
         "overrides": {**rep, **_LAM["zero"]}},                # 음성 대조 (가미카제)
        {"label": "depth_bait_fair", "group": "depth",
         "overrides": {**rep, "bait_gain": 0.5}},              # route 공칭과 동일 크기
        {"label": "depth_bait_priv", "group": "depth",
         "overrides": {**rep, "bait_gain": 0.5, "bait_privileged": True}},
    ]
    return configs


def build() -> dict:
    configs = _grid()
    body = {
        "schema": "p1-attacker-ladder-manifest-v1",
        "status": "sealed pre-run; defender-frozen attacker-ladder map + plant-swap pre-check",
        "design_doc": "docs/118_p1_attacker_ladder_design_contract_draft.md",
        "scope": {
            "question": ("with the defender fully frozen, how much does the declared "
                         "attacker configuration grid move clean N and per-row chi50 "
                         "on the common 28-cell suite"),
            "purpose": ["foundation behavior-level axis asset",
                        "P2 limiter-only v2 control baseline",
                        "P2 premise check (does the attacker axis move outcomes at all)"],
            "not_evidence_for": ["learned anything", "cooperation", "W6 entry",
                                 "T2 objective-based attacker (deferred)"],
            "naming": "T-ladder labels in outputs; code level A1/A2 never used in prose",
            "prior_decisions_unchanged": ["NO_SELECTION", "STOP_F1", "STOP_CLBC1",
                                           "STOP_F2", "STOP_RL1", "STOP_RL2",
                                           "b5 closed"],
        },
        "defender": {
            "limiter": "scripted hold (frozen)",
            "capturer": "scripted launcher (frozen); F3 arm deferred to the P2 contract",
        },
        "attacker": {
            "base": ("the suite-resolved AttackerSpec (A2 level, jink 0.6, route 0.5, "
                     "injected sense_range) — each config applies dataclasses.replace "
                     "with its declared overrides only"),
            "configs": [{**c, "overrides": {k: ("inf" if v == float("inf") else v)
                                            for k, v in c["overrides"].items()}}
                        for c in configs],
            "n_configs": len(configs),
            "declared_then_frozen": ("no attacker parameter is tuned against results "
                                     "(docs/27 rule 2); speed-profile variants deferred "
                                     "to a later amendment — no grounded values today"),
        },
        "evaluation": {
            "namespace": "p1_ladder_v1",
            "seed0": 191000,
            "cells": "28 boundary cells (B2 manifest order; 14 rows x chi_role {lo, hi})",
            "episodes_per_cell": 10,
            "episodes_per_config": 280,
            "episodes_total_p1a": 280 * len(configs),
            "paired": ("all configs share identical (seed0, namespace, scenario_id) "
                       "draws; attacker overrides do not touch scenario randomization"),
            "readout": ["clean N", "FIRE", "SPENT_FAIL", "H_illegal",
                        "clean crossing episodes/total", "per-row chi50 with censoring "
                        "reported, never extrapolated"],
            "resolution_caveat": ("10 ep/cell chi50 is directional map resolution, not "
                                  "B2-grade confirmatory estimation"),
        },
        "amendments": [
            "v1.1 (2026-10-01, pre-run — no results existed): p1b namespace unified "
            "with p1a (p1_ladder_v1/191000) so the tau=0 baseline truly shares draws "
            "with t1f_r05_s30_ref; the originally declared p1b_plant_v1/201000 would "
            "have broken the paired delta-chi50 readout. Cell description corrected "
            "to '14 rows x chi_role {lo, hi}'.",
        ],
        "p1b_plant_swap": {
            "namespace": "p1_ladder_v1",
            "seed0": 191000,
            "plant": ("docs/93 option 1: first-order accel lag tau_a*da/dt = a_cmd - a "
                      "on defender translational a_cmd only (limiter and capturer); "
                      "attacker plant unchanged (single-axis discipline)"),
            "tau_a_over_tau0": [0.1, 0.3],
            "tau0": "per-cell tau_deploy (im['tau'])",
            "attacker_config": "suite nominal (= t1f_r05_s30_ref)",
            "baseline": ("tau_a = 0 is p1a t1f_r05_s30_ref itself — identical "
                         "(seed0, namespace, scenario_id) draws, so per-row "
                         "delta chi50 is paired"),
            "episodes": 280 * 2,
            "readout": ("delta chi50^AF per row vs delta_chi = 0.03 (docs/92/93); "
                        "both outcomes publishable; completes before any P2 training"),
            "probe_caveat": "two-point tau grid is probe resolution, not a physics estimate",
        },
        "gate": {
            "invalid": ["lineage", "completion (every config x cell x episode)",
                        "finite", "paired draw identity across configs", "budget"],
            "complete": "COMPLETE_P1",
            "invalid_decision": "INVALID_P1",
            "no_performance_gate": "map-making, not hypothesis testing",
            "p2_premise_readout": ("pre-registered classification, not a gate: "
                                   "P2_PREMISE_SUPPORTED if max-min clean N across the "
                                   "18 main-grid configs >= 28/280, else "
                                   "P2_PREMISE_WEAK; sense_range effect reported as "
                                   "secondary descriptor"),
        },
        "stop": ["namespace collision", "dirty execution code", "non-finite value",
                 "draw mismatch across configs", "budget mismatch"],
        "runtime": {"deterministic": "seed_everything + declared namespace seeds",
                    "sharding": "per-config server shards allowed (long-run policy)"},
        "promotion": ("none; COMPLETE_P1 feeds the P2 contract draft and the foundation "
                      "behavior axis. It does not open training."),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if saved != build():
        raise ValueError(f"P1 manifest drift: {MANIFEST}")
    return saved


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    main()
