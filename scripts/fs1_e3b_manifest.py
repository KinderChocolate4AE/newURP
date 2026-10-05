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


# ---------------------------------------------------------------- phase 2 ---
MANIFEST_P2 = ROOT / "artifacts" / "fs1" / "e3b_phase2_manifest.json"
P2_CELLS = [{"cell": "m0.35_n1", "mu": 0.35, "nu": 1.0, "ceil_ref": 5},
            {"cell": "m1.4_n1", "mu": 1.4, "nu": 1.0, "ceil_ref": 5}]
P2_SEEDS = [0, 1, 2]
P2_TRAIN_STEPS = 1.1e8


def build_p2() -> dict:
    body = {
        "schema": "fs1-e3b-phase2-addendum-v1",
        "status": ("sealed after the phase-1 readout (FLOOR_EVERYWHERE) and the 1.5a occupancy "
                   "probe (report-only: robust capture-ok steps exist in 18-22/24 episodes vs every "
                   "adapted exploiter, window 1-4 steps), before any phase-2 training (user approval)"),
        "lineage": {"phase1": build()["manifest_hash"], "occupancy": "artifacts/fs1/e3b/occupancy.json (9275722)",
                    "held_clause": "phase-1 floor held phase 2; re-opened by user decision with absolute criteria"},
        "question": ("Q-C: can co-trained defense (frozen at the final checkpoint) exceed every "
                     "scripted-family ceiling against a fresh dedicated exploiter — i.e., does "
                     "within-episode state-adaptive behavior do what capability (mu-nu), episode-level "
                     "unpredictability, and fixed fire rules could not"),
        "cells": P2_CELLS,
        "production": {
            "bc": ("canonical shepherd.fs1.bc at f525da0+: --stack r4p [--k-viab 0.2 for arm B] "
                   "--mu <mu> --nu <nu> --seed <seed> --episodes 3000, server6 CPU"),
            "train": ("JAX 42f8835 semantics (execution tree 180b0ef = 42f8835 jax-code-identical + "
                      "canonical merge; REVISION recorded): --stack r4p --mu --nu --seed <seed> "
                      f"--init <bc> --total-steps {P2_TRAIN_STEPS:.1e}; arm A = no k_viab, "
                      "arm B = --k-viab 0.2"),
            "paths": "/data1/hjhong/fs1jax/e3b/phase2/<cell>/arm{A,B}/s<seed>/{bc/, ckpt.pt, log.jsonl, config.json}",
            "seeds": {"bc_and_train": P2_SEEDS},
        },
        "judgment": {
            "exploiter": ("per (cell, arm, seed): fresh dedicated exploiter vs the frozen learned_det "
                          "defense — JAX --exploit <ckpt> --stack r4p --mu --nu, 1e7 steps, "
                          "seed = 271000 + cell_idx*1000 + {armA:0, armB:100} + seed"),
            "eval": ("canonical eval on server4, 240 eps paired, --stack r4p --mu --nu, "
                     "cell eval seed0 = 270000 + cell_idx*1000 (identical across arms/seeds); "
                     "learned_sto, R1/R2 fire-tick logs and trajectories reported"),
            "criterion": ("LEARNING_OPENS(cell, arm) if ceil_learned_det >= ceil_ref(cell) + 24 "
                          "(ceil_ref = max over P/M1/M2 phase-1 ceilings, recorded above) on >= 2 of 3 "
                          "seeds. Arms judged separately; B - A reported as objective-change effect only "
                          "(never as emergence). Overall: E3B2_LEARNING_OPENS if any (cell, arm) "
                          "confirmed, else E3B2_NULL. INVALID_E3B2 per budget/completion/paired/"
                          "manifest/BC-lineage violation (cell excluded and reported)"),
        },
        "discipline": "judgment on server4; no pooling with pilot/stage1/phase1; emergence claims from arm A logs only; quarantine rules and launch preconditions (REVISION check + dry-run report) as before",
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_p2() -> dict:
    data = json.loads(MANIFEST_P2.read_text(encoding="utf-8"))
    if data != build_p2():
        raise ValueError(f"E3b phase-2 manifest drift: {MANIFEST_P2}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    for path, body in ((MANIFEST, build()), (MANIFEST_P2, build_p2())):
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path} {body['manifest_hash']}")


if __name__ == "__main__":
    main()
