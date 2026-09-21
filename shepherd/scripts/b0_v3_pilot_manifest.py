"""Sealed, result-blind manifest for the B0 v3 B-5 MAPPO hyperparameter pilot."""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "artifacts" / "marl" / "b0_v3_pilot_manifest.json"


def build() -> dict:
    body = {
        "schema": "b0-v3-mappo-pilot-manifest-v1",
        "status": "sealed pre-run; exploratory hyperparameter selection only",
        "prerequisites": {
            "w5_decision": "artifacts/r2b/b2_scripted/w5_decision.json",
            "w5_required": "PASS",
            "preflight": "artifacts/marl/b0_v3_mappo_preflight.json",
            "preflight_required": "PASS",
            "b0_v3_hash": "5e7b5b486b9d8a4a",
        },
        "actor": {
            "arm": "B-5 pilot only",
            "structure": "shared limiter actor + separate capturer actor",
            "limiter_commit": False,
            "attacker": "A2-nominal scripted",
            "claim_scope": "no performance or cooperation claim",
        },
        "initialization": {
            "dataset": "clean N episodes only from scripted c5 + clean-fire",
            "cells": "28 boundary cells (c1,c2)",
            "target_successes_per_cell": 1,
            "max_attempts_per_cell": 6,
            "minimum_success_cells": 20,
            "minimum_success_cells_per_lambda_slice": 8,
            "exclude": ["H_illegal", "NET_SPENT", "PENETRATED", "TRUNCATED"],
            "trained_heads": ["capturer pointing mean", "capturer fire logit"],
            "limiter": "final mean layer zeroed; stochastic exploration retained",
            "bc_steps": 400,
            "bc_lr": 0.001,
            "bc_batch": 256,
            "axis_loss_weight": 1.0,
            "fire_loss_weight": 1.0,
            "fire_loss": "class-balanced BCEWithLogits",
            "seed0": 41000,
            "seed_ns": "b0v3_mappo_pilot_bc_v1",
        },
        "training": {
            "seeds": [0, 1],
            "total_env_steps": 32768,
            "rollout_env_steps": 512,
            "updates": 64,
            "checkpoint_every_updates": 8,
            "seed0": 51000,
            "seed_ns": "b0v3_mappo_pilot_train_v1",
            "sampler": {
                "adaptive": False,
                "block": 10,
                "frontier_slots": 7,
                "anchor_slots": 2,
                "uniform_slots": 1,
                "row_schedule": "(episode + 5*seed) mod 14",
                "note": "same ordered cell schedule for every candidate at a given seed",
            },
            "fixed": {
                "gamma": 0.99, "gae_lambda": 0.95, "clip_eps": 0.2,
                "epochs": 5, "minibatch_size": 128,
                "vf_coef": 0.5, "max_grad_norm": 0.5, "target_kl": 0.02,
                "hidden_sizes": [128, 128], "init_log_std": -1.0,
                "ortho_init": True, "value_norm": True,
                "ent_coef_limiter": 0.0, "coma_mix": 0.0,
                "lr_anneal": "linear", "lr_anneal_floor": 0.1,
                "r_clean": 1.0, "r_illegal": -1.0,
            },
        },
        "candidates": {
            "c0_base": {"lr": 0.0003, "ent_coef_finisher": 0.003, "beta": 0.2},
            "c1_entropy": {"lr": 0.0003, "ent_coef_finisher": 0.01, "beta": 0.2},
            "c2_low_lr": {"lr": 0.0001, "ent_coef_finisher": 0.01, "beta": 0.2},
            "c3_no_pbrs": {"lr": 0.0003, "ent_coef_finisher": 0.01, "beta": 0.0},
        },
        "evaluation": {
            "cells": "28 boundary cells (c1,c2)",
            "episodes_per_cell": 10,
            "seed0": 61000,
            "seed_ns": "b0v3_mappo_pilot_eval_v1",
            "policy": "stochastic policy with per-episode fixed torch seed",
            "credit_cut": ["H_illegal", "NET_SPENT"],
            "pooling": "candidate summaries pool two pilot seeds; raw per-seed retained",
        },
        "selection": {
            "eligibility": {
                "mean_p_H_illegal_max": 0.0563,
                "mean_p_FIRE_min": 0.20,
                "mean_p_N_min": 0.10,
                "each_seed_p_N_min": 0.05,
                "finite_training": True,
            },
            "ranking": [
                "maximum mean p_N among eligible candidates",
                "if |delta p_N| < 0.01, lower mean p_H_illegal",
                "then lower across-seed p_N range",
                "then lexical candidate id",
            ],
            "if_none_eligible": "NO_SELECTION; do not open main 3-seed training",
            "reference_note": "0.0563 is the B2 RULE_COOP exploratory rate, not a universal safety limit",
        },
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = build()
    if data != expected:
        raise ValueError(f"pilot manifest drift: {MANIFEST}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(MANIFEST)


if __name__ == "__main__":
    main()

