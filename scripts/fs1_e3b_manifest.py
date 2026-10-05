"""Seal E3b phase 1: 방어 예측불가성 × μ 요인 분리 — docs/125.

    python scripts/fs1_e3b_manifest.py        # phase-1 manifest 기록 (결과 보기 전 봉인)
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e3b_phase1_manifest.json"

CELLS = [{"cell": "m0.35_n1", "mu": 0.35, "nu": 1.0},
         {"cell": "m0.7_n1", "mu": 0.7, "nu": 1.0},
         {"cell": "m1.4_n1", "mu": 1.4, "nu": 1.0}]
FAMILIES = {"M1": "mix5050", "M2": "kfirst_rand"}
N, MARGIN, EX_STEPS, SEED0, STRIDE = 240, 24, 1e7, 264000, 1000


def build() -> dict:
    body = {
        "schema": "fs1-e3b-phase1-manifest-v1",
        "status": "sealed before any phase-1 result (design doc: docs/125; motivated by the user correction in note 2026-10-06a section 4.3 r2)",
        "lineage": {"e3_manifest": "567ab158560bcfdf", "stage1_harvest": "d8f6b92",
                    "pure_baseline": "stage-1 ceilings reused for family P (same seeds/namespace lineage, no rerun)"},
        "questions": {
            "Q-A": "does episode-level unpredictability alone (no learning, no within-episode adaptation) open the dedicated-exploiter ceiling vs frozen pure scripted",
            "Q-B": "does the ceiling of non-frozen defenses open with mu (direct retest of the stage-1 mu conclusion, which was conditional on frozen pure scripted)",
        },
        "cells": CELLS, "families": FAMILIES,
        "defenses": {
            "M1 mix5050": "per-episode 50/50 draw {kfirst50, fin12_fb}; eval draw = episode-seed parity (exact 50/50, paired)",
            "M2 kfirst_rand": "kfirst arming radius ~ U[30, 70] m per episode",
            "P pure": "stage-1 kfirst50/fin12_fb ceilings reused (0-4/240)",
        },
        "exploiters": ("per cell x {M1, M2}: 1e7 steps, JAX 42f8835 (= 0df35f3 + canonical-mirrored "
                       "mix/rand exploit targets, trainer suite 15/15) --stack r4, "
                       "--exploit scripted:mix5050 / scripted:kfirst_rand (training opponent drawn "
                       "from the distribution every episode); overfit-speed reported from the "
                       "training-log win-rate trajectory (no extra runs). Launch precondition: "
                       "host synced to 42f8835 (REVISION check) + a 2-iter scripted:mix5050 dry-run "
                       "whose config/log is reported before the 6-run sweep (v1.1 lesson)"),
        "evaluation": {"n": N, "seed0": SEED0, "cell_seed_stride": STRIDE,
                       "cell_idx": "index in THIS manifest's cells list (0/1/2), not the stage-1 grid index",
                       "seed_offsets": {"mix5050": 300, "kfirst_rand": 400}, "paired": True,
                       "environment": "canonical eval on server4; training on server5/6 (E3 v1.2 terms)",
                       "report_extras": ["M1/M2 vs stage-1 ex_kfirst50/ex_fin12_fb (arithmetic lower-bound check, free)",
                                         "R1/R2 fire-tick logs", "trajectories (viz-first)"]},
        "gates": {
            "Q-A": f"per cell: max(ceil_M1, ceil_M2) - ceil_P_stage1 >= +{MARGIN}/{N} -> UNPREDICTABILITY_OPENS(cell)",
            "Q-B": f"within a family: ceil_M(m1.4_n1) - ceil_M(m0.35_n1) >= +{MARGIN} -> MU_REOPENS_UNDER_MIXTURE (m0.7_n1 monotone reported)",
            "invalid": "budget/completion/paired/manifest per cell -> excluded and reported",
        },
        "phase2": ("co-training (arm A r4' / arm B k_viab 0.2, 3 seeds, 1.1e8) sealed as a separate "
                   "addendum AFTER the phase-1 readout and BEFORE any phase-2 training; judgment "
                   "attackers are fresh held-out exploiters trained vs the finished frozen defense; "
                   "Q-C template: ceil_learned - max(ceil_M) >= +24, 2/3 seeds -> LEARNING_BEATS_MIXING. "
                   "If phase 1 is floor everywhere, phase 2 is held and the world-design axis (E7) is discussed"),
        "not_evidence_for": ["world ceiling claims (scripted-family ceilings only)",
                             "adaptivity-is-the-knob (hypothesis under test)",
                             "cooperation vocabulary (limiter-control opportunity)"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E3b phase-1 manifest drift: {MANIFEST}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    main()
