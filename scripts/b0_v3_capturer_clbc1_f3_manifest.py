"""Seal CLBC1-F3 robust FIRE-head BC before collection and evaluation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1_f3" / "manifest.json"
ARMS = ("f2_control", "f3_robust_fire_bc")


def build() -> dict:
    body = {
        "schema": "b0-v3-capturer-clbc1-f3-manifest-v1",
        "status": "sealed pre-run; CLBC1+F2 robust FIRE-head BC diagnostic",
        "design_doc": "docs/114_b0v3_capturer_clbc1_f3_contract.md",
        "scope": {
            "question": ("with CLBC1 aim and F2 log_std fixed, does retraining only the "
                         "Bernoulli FIRE head on observation-realizable robust-ready labels "
                         "reduce nonrobust FIRE and increase clean N"),
            "rl_updates": 0,
            "not_evidence_for": ["scientific significance", "pilot selection",
                                 "W6 entry", "learned cooperation"],
            "prior_decisions_unchanged": ["NO_SELECTION", "STOP_F1", "STOP_CLBC1",
                                           "STOP_F2"],
        },
        "prerequisites": {
            "b0_v3_hash": "5e7b5b486b9d8a4a",
            "pilot_decision_required": "NO_SELECTION",
            "f1_decision_required": "STOP_F1",
            "clbc1_decision_required": "STOP_CLBC1",
            "f2_manifest": "artifacts/marl/b0_v3_capturer_clbc1_f2/manifest.json",
            "f2_manifest_hash": "567f134a862335ce",
            "f2_readout": "artifacts/marl/b0_v3_capturer_clbc1_f2/readout.json",
            "f2_decision_required": "STOP_F2",
            "f2_source_code_commit": "549a4fa",
            "f2_parent_state": {
                "0": {"lim_actor": "9a0883845677f930", "fin_mean": "267e5b409333bf9e",
                      "fin_fire_logit": "80e69a00972add08",
                      "fin_log_std": "8ccb527509c0022e", "critic": "1e1a657f3f42abb1",
                      "obs_norm": "a271b80685c8ec1c", "all": "bc3bd8b54156d604"},
                "1": {"lim_actor": "45f8b8f0e22143d4", "fin_mean": "6f26075e07355c22",
                      "fin_fire_logit": "5cfb779b11db5727",
                      "fin_log_std": "8ccb527509c0022e", "critic": "22b477760d907046",
                      "obs_norm": "a271b80685c8ec1c", "all": "d0aec2ae27911745"},
            },
        },
        "parent": {
            "policy": "exact sealed CLBC1 parent with aim log_std set to -2.3",
            "actor_seeds": [0, 1],
            "anchor": "all component hashes exactly match harvested F2 intervention state",
        },
        "collection": {
            "namespace": "b0v3_capturer_clbc1_f3_collect_v1",
            "seed0": 131000,
            "cells": "28 boundary cells (chi_role lo/hi), B2 manifest order",
            "episodes_per_cell": 4,
            "episodes_per_seed": 112,
            "episodes_total": 224,
            "policy": "stochastic CLBC1+F2 Gaussian aim; Bernoulli draw consumed",
            "limiter": "scripted hold",
            "collection_only_fire_suppression": ("set sampled FIRE bit to zero after policy "
                                                 "evaluation so pre-terminal states remain visible"),
            "on_policy_claim": False,
            "labels": ("current raw observation: p_feasible > 0 and v_shot_worst >= 1; "
                       "exactly equivalent to not boxed_in and v_shot_worst >= 1 in this world"),
            "decision_region": "v_shot_soft >= theta_fire (0.9), including boxed negatives",
            "split": "within-cell episodes 0,1,2 train; episode 3 validation",
            "keep": "all finite FSM=LOADED states; no terminal-outcome filter",
        },
        "training": {
            "control": "no update",
            "treatment": "fresh Adam on fin_actor.fire_logit only",
            "steps": 400,
            "batch": 256,
            "lr": 0.001,
            "loss": "BCEWithLogitsLoss with train-set neg/pos pos_weight",
            "rng": "np.random.default_rng(actor_seed + 27301)",
            "trainable": ["fin_actor.fire_logit"],
            "frozen_bit_identical": ["fin_actor.mean", "fin_actor.log_std", "lim_actor",
                                     "critic", "obs_norm"],
            "shared_trunk": False,
        },
        "arms": {
            "f2_control": "exact CLBC1+F2 parent, no new training",
            "f3_robust_fire_bc": "same parent, FIRE head-only robust-label BC",
            "single_factor": "only fin_actor.fire_logit parameters differ after training",
        },
        "evaluation": {
            "namespace": "b0v3_capturer_clbc1_f3_eval_v1",
            "seed0": 141000,
            "cells": "28 boundary cells (chi_role lo/hi), B2 manifest order",
            "episodes_per_cell": 10,
            "episodes_per_arm_per_seed": 280,
            "episodes_total": 1120,
            "scenario_id": "cell_index * 10 + within_cell_index",
            "env_seed": "141000 + scenario_id",
            "torch_seed": "141000 + 1_000_000 * actor_seed + scenario_id",
            "paired": "within actor seed, arms reset identical environment and torch seeds",
            "limiter": "scripted hold",
            "capturer": "stochastic Gaussian aim plus each arm's Bernoulli FIRE head",
            "fire_mode": "clean argument is inert on learned capturer path",
            "metrics": ["clean N", "FIRE", "robust-ready FIRE", "nonrobust FIRE",
                        "SPENT_FAIL", "FIRE-to-N", "clean crossing", "H_illegal"],
            "smoke": "seed 0, first 2 cells x 1 episode x 2 arms; gate excluded",
        },
        "traces": {
            "scenarios": [["r00c1", 0], ["r00c2", 10], ["r07c1", 140],
                          ["r13c2", 270]],
            "selection": "fixed before results; same evaluation episodes",
        },
        "gate": {
            "invalid": ["lineage", "pairing", "finite", "completion", "exact F2 parent",
                        "collection lineage and label support", "fire-head-only identity",
                        "authoritative FIRE logging", "budget"],
            "heldout_per_seed": ["on validation soft-gate states, F3 balanced accuracy > control",
                                 "on validation soft-gate states, F3 false-positive rate < control",
                                 "on validation soft-gate states, F3 true-positive rate >= control"],
            "evaluation_per_seed": ["F3 clean N > control",
                                    "F3 robust-ready FIRE >= control",
                                    "F3 nonrobust FIRE < control",
                                    "F3 SPENT_FAIL < control",
                                    "F3 FIRE-to-N > control",
                                    "F3 clean crossing episodes >= control"],
            "safety": "pooled H_illegal == 0 for both arms",
            "pass": "PASS_F3_TO_CAPTURER_ONLY_RL_CONTRACT_DRAFT",
            "fail": "STOP_F3",
            "invalid_decision": "INVALID_F3",
        },
        "stop": ["prerequisite mismatch", "namespace collision", "F2 parent hash mismatch",
                 "dirty execution code", "missing train or validation class support",
                 "single-factor mismatch", "non-finite value", "pairing mismatch",
                 "FIRE audit mismatch", "budget mismatch",
                 "CUDA run without CUBLAS_WORKSPACE_CONFIG in {:4096:8, :16:8}"],
        "runtime": {"cublas_workspace_config": [":4096:8", ":16:8"],
                    "deterministic": "seed_everything plus per-episode torch seed"},
        "promotion": ("none; PASS permits only a separately sealed capturer-only RL contract "
                      "draft; W6 and PFSP remain closed"),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if saved != build():
        raise ValueError(f"CLBC1-F3 manifest drift: {MANIFEST}")
    return saved


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    main()
