"""Seal P1b-2: plant-swap pre-check on a maneuvering defender (docs/118 승계 소계약).

P1b (hold limiter) 는 a_cmd ≡ 0 이라 검정력 0 으로 무효였다 (2026-10-01e).
P1b-2 는 docs/93 §5 원문대로 **B2 rule-based (c5 arc) limiter** 에 1차 가속 지연을
걸어 행별 paired Δχ50 을 잰다. P2 학습 착수 전 완료 조건을 승계한다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "p1b2_plant" / "manifest.json"
TAUS = [0.0, 0.1, 0.3]


def build() -> dict:
    body = {
        "schema": "p1b2-plant-swap-manifest-v1",
        "status": "sealed pre-run; plant-swap pre-check on a maneuvering scripted defender",
        "design_doc": "docs/118_p1_attacker_ladder_design_contract_draft.md",
        "supersedes": ("P1b of manifest 4629158d387c938b — recorded vacuous "
                       "(zero power under the hold limiter, note 2026-10-01e); "
                       "its delta-chi50 numbers must not be cited"),
        "scope": {
            "question": ("does a first-order defender accel lag (tau_a = ratio x "
                         "tau_deploy) move the per-row chi50 boundary of the c5 arc "
                         "limiter + scripted launcher world by more than "
                         "delta_chi = 0.03"),
            "not_evidence_for": ["learned anything", "P2 outcomes", "6DOF fidelity"],
            "blocking": "P2 training may not start before this readout exists",
        },
        "defender": {
            "limiter": "scripted c5 arc (B2 RULE_COOP limiter_kw, cited from the "
                       "sealed B2 manifest at run time)",
            "capturer": "scripted launcher (FinisherSpec.a_max == 0 asserted)",
        },
        "attacker": {"base": "suite nominal", "overrides":
                     {"route_gain": 0.5, "sense_range": 30.0}},
        "plant": ("first-order accel lag on limiter translational a_cmd only "
                  "(exact exponential discretization); attacker plant unchanged"),
        "arms": {"tau_a_over_tau0": TAUS,
                 "baseline": "tau = 0.0 is its own arm in the same namespace "
                             "(the c5 world differs from P1a hold, so P1a rows are "
                             "not reused)"},
        "evaluation": {
            "namespace": "p1b2_plant_v1",
            "seed0": 201000,
            "cells": "28 boundary cells (B2 manifest order)",
            "episodes_per_cell": 10,
            "episodes_per_arm": 280,
            "episodes_total": 280 * len(TAUS),
            "paired": "all arms share identical (seed0, namespace, scenario_id) draws",
        },
        "gate": {
            "invalid": ["lineage", "completion", "budget", "paired draws",
                        "power check: each tau > 0 arm must differ from the tau = 0 "
                        "arm in at least one paired episode record — bit-identical "
                        "arms mean the lag was vacuous again"],
            "complete": "COMPLETE_P1B2",
            "invalid_decision": "INVALID_P1B2",
            "classification": ("pre-registered readout, not a gate: all non-censored "
                               "paired |delta chi50| < 0.03 for both taus -> "
                               "PM_ABSTRACTION_HOLDS_ON_TESTED_CELLS; any row >= 0.03 "
                               "-> AIRFRAME_RESIDUAL_CANDIDATE (both publishable, "
                               "docs/93 section 4)"),
        },
        "promotion": "none; the readout feeds the P2 contract's world declaration only.",
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if saved != build():
        raise ValueError(f"P1b-2 manifest drift: {MANIFEST}")
    return saved


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    main()
