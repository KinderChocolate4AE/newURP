"""B0 v3 capturer-F1 BC-SNR 수정의 결과-맹검 manifest (torch-free; docs/111).

capturer-F1 은 mode-switch Track B 의 F1-E 와 무관하다.

질문 (기제 실험, BC-only): 봉인 BC dataset 에서 조준 손실을 cosine → 단위 교사축 MSE 로
바꾸면 (|μ|≈0.162 → ≈1, σ=e⁻¹ 고정), 새 paired scenario 에서 BC 직후 stochastic
capturer 가 clean crossing·clean N 을 더 자주 만드는가.

해석 한계를 manifest 자체에 봉인한다:
  - RL optimizer update 0회. selection/promote 의미 없음. W6 를 열지 않는다.
  - cosine 대조는 *재구성*이다 — pilot 은 BC 직후 checkpoint 를 저장하지 않았다.
    검증 앵커는 c0_base/seed{s}/bc_init.json 지표 6개뿐이다.
  - pilot 의 봉인 280사례 (61000) · b5 (71000) 를 재사용하지 않는다.

    python -m scripts.b0_v3_capturer_f1_manifest   # artifacts/marl/b0_v3_capturer_f1/manifest.json
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "marl" / "b0_v3_capturer_f1" / "manifest.json"
OBJECTIVES = ("cosine_control", "unit_axis_mse_f1")
BC_INIT_KEYS = ("loss", "axis_loss", "fire_loss", "mean_axis_cosine",
                "fire_tpr", "fire_tnr")


def build() -> dict:
    body = {
        "schema": "b0-v3-capturer-f1-manifest-v1",
        "status": "sealed pre-run; BC-only mechanism experiment",
        "design_doc": "docs/111_b0v3_capturer_f1_snr_design_draft.md",
        "not_related_to": "mode-switch Track B F1-E",
        "scope": {
            "question": ("does replacing the cosine aim loss with unit-teacher-axis "
                         "MSE make the post-BC stochastic capturer produce more "
                         "clean crossings and clean N on new paired scenarios"),
            "rl_updates": 0,
            "not_evidence_for": ["scientific significance", "candidate selection",
                                 "W6 entry", "learned cooperation"],
            "reconstruction": ("cosine control is a metric-anchored reconstruction, "
                               "not the (never-saved) original post-BC checkpoint"),
        },
        "prerequisites": {
            "b0_v3_hash": "5e7b5b486b9d8a4a",
            "pilot_manifest_hash": "ba64bc15fdbbd4f2",
            "pilot_readout": "artifacts/marl/b0_v3_pilot/readout.json",
            "pilot_decision_required": "NO_SELECTION",
            "bc_dataset": "artifacts/marl/b0_v3_pilot/bc_dataset.json",
            "bc_dataset_hash": "b48aad5eab4a92bd",
            "bc_code_tree": "dea5a7a357a090ed0db3106d96100d424cc8fc12",
        },
        "bc": {
            "objectives": {
                "cosine_control": {
                    "axis_loss": "mean(1 - cos(mu, teacher_axis))",
                    "implementation": ("shepherd.scripts.b0_v3_mappo_pilot."
                                       "initialize_from_bc (called directly)"),
                },
                "unit_axis_mse_f1": {
                    "axis_loss": ("F.mse_loss(mu, teacher_axis / "
                                  "||teacher_axis||.clamp_min(1e-9)) "
                                  "= mean(||mu - a_hat||^2 / 3)"),
                    "implementation": ("scripts.b0_v3_capturer_f1."
                                       "initialize_from_bc_f1 (pilot copy; only "
                                       "the axis-loss lines differ)"),
                },
            },
            "mu": "Gaussian mean before clipping",
            "actor_seeds": [0, 1],
            "runner": ("PilotRunner(pilot manifest, candidate c0_base, seed) after "
                       "seed_everything(seed) — the pilot run_combo call order"),
            "unchanged_from_pilot": {
                "bc_steps": 400, "bc_batch": 256, "bc_lr": 0.001, "optimizer": "Adam",
                "fire_loss": "class-balanced BCEWithLogits", "init_log_std": -1.0,
                "limiter": "final mean layer zeroed", "obs_norm": "RunningNorm.update(X)",
                "actor": "hidden [128,128], orthogonal init", "fire": "Bernoulli",
                "minibatch_rng": "np.random.default_rng(seed + 7301)",
                "action": "policy_fn padding and scaling",
            },
            "identity_checks": [
                "initial state hash (actors, critic, obs norm) equal across objectives",
                "minibatch sequence hash (fire-head inputs) equal across objectives",
                "post-BC fire head bit-identical across objectives",
                "post-BC limiter actor, critic, fin log_std, obs norm identical",
                "limiter final mean layer zero; fin log_std == -1",
            ],
            "anchor": {
                "objective": "cosine_control",
                "files": "artifacts/marl/b0_v3_pilot/c0_base/seed{seed}/bc_init.json",
                "keys": list(BC_INIT_KEYS),
                "tolerance_abs": 1e-6,
                "tiers": ["exact-metric-match", "metric-close(<1e-6)",
                          "metric-mismatch"],
                "rule": "full run stops on metric-mismatch; smoke reports only",
                "note": ("original pilot/diagnostic CUDA runs had no "
                         "CUBLAS_WORKSPACE_CONFIG (diag.log warning); this run "
                         "sets it, so bit-level drift is possible and is bounded "
                         "by the declared tolerance"),
            },
        },
        "evaluation": {
            "namespace": "b0v3_capturer_f1_eval_v1",
            "seed0": 81000,
            "cells": "28 boundary cells (chi_role lo/hi), b2 manifest order",
            "episodes_per_cell": 10,
            "episodes_per_objective_per_seed": 280,
            "episodes_total": 1120,
            "scenario_id": "cell_index * 10 + within_cell_index",
            "env_seed": "81000 + scenario_id",
            "torch_seed": "81000 + 1_000_000 * bc_seed + scenario_id",
            "paired": ("within a bc_seed both objectives consume identical "
                       "(cell_id, scenario_id, chi, eta, env_seed, torch_seed)"),
            "limiter": "scripted c5 (B2 RULE_COOP limiter_kw, arc)",
            "capturer": "BC actor stochastic Gaussian pointing + Bernoulli FIRE",
            "fire_rule": "no external forced fire; FSM gate decides",
            "credit": {"spec": "c0_base B0V3CreditSpec", "gamma": 0.99, "beta": 0.2,
                       "r_clean": 1.0, "r_illegal": -1.0,
                       "cuts": ["H_illegal", "NET_SPENT"]},
            "smoke": ("bc_seed 0, first 2 cells x 1 episode x 2 objectives = 4 "
                      "episodes; separate directory; excluded from the gate"),
        },
        "traces": {
            "scenarios": [["r00c1", 0], ["r00c2", 10], ["r07c1", 140],
                          ["r13c2", 270]],
            "source": "the same evaluation episodes, per bc_seed x objective",
            "gate": "excluded (diagnostic only)",
        },
        "gate": {
            "per_seed": ["F1 clean-crossing episodes > cosine_control",
                         "F1 clean N > cosine_control"],
            "pooled": ["F1 H_illegal <= cosine_control"],
            "integrity": ["lineage", "pairing", "finite", "completion"],
            "pass": "PASS_TO_SMALL_RL_CONTRACT",
            "fail": "STOP_F1",
            "meaning": ("eligibility to draft a separate small RL contract only; "
                        "not significance, selection, W6 entry or cooperation"),
        },
        "stop": [
            "B0 / BC dataset / manifest hash mismatch",
            "shepherd tree differs from BC metadata code_tree",
            "cosine control metric-mismatch against bc_init.json",
            "initial actor state or minibatch sequence differs across objectives",
            "fewer than 1120 canonical episodes",
            "pairing / scenario signature mismatch",
            "NaN / Inf",
            "CUDA run without CUBLAS_WORKSPACE_CONFIG in {:4096:8, :16:8}",
        ],
        "runtime": {"cublas_workspace_config": [":4096:8", ":16:8"],
                    "deterministic": "seed_everything (pilot setting)"},
        "promotion": "none; W6 remains closed",
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"capturer-F1 manifest drift: {MANIFEST}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(MANIFEST)


if __name__ == "__main__":
    main()
