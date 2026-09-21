"""B-5 한정 limiter-only 실험의 결과-맹검 manifest (torch-free).

목적 (기제 실험): capturer를 **작동하는 scripted launcher로 고정**했을 때 limiter
학습이 clean N을 움직이는가. role-swap(2026-09-22)이 가리킨 "learned limiter 156 vs
scripted c5 148"은 정본 없는 사후 관찰이었다 — 여기서 새 평가 namespace로 재측정한다.

해석 한계를 manifest 자체에 봉인한다:
  - 이 실험의 정책은 scripted launcher에 의존한다. learned cooperation·frontier
    확장·B-5 본 성과로 승격하지 않는다.
  - scripted capturer의 행동은 finisher actor의 PPO log-prob로 채점되지 않는다
    (freeze_finisher: actor 손실 제외 + no_grad; 행동은 rollout에서 스크립트로 교체).
  - 외부 강제 FIRE 없음: 발사는 B2와 동일한 clean-crossing 규칙(fire_mode="clean")
    이며 FSM gate가 최종 판정한다.
  - pilot의 봉인 280사례·선택 문턱을 재사용하지 않는다 (새 seed namespace).
  - W6 본 학습 gate를 열지 않는다.

    python -m scripts.b5_limiter_only_manifest   # artifacts/marl/b5_limiter_only/manifest.json
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "marl" / "b5_limiter_only" / "manifest.json"


def build() -> dict:
    body = {
        "schema": "b5-limiter-only-manifest-v1",
        "status": "sealed pre-run; mechanism experiment only",
        "scope": {
            "question": ("does limiter learning move clean N when the capturer "
                         "is the functioning scripted clean-fire launcher"),
            "depends_on_scripted_launcher": True,
            "not_evidence_for": ["learned cooperation", "frontier extension",
                                 "B-5 main campaign", "W6 entry"],
            "fire_rule": "scripted clean-crossing proposal; FSM gate decides; "
                         "no external forced fire in training or evaluation",
            "log_prob_rule": ("scripted capturer actions never enter any policy "
                              "log-prob; finisher actor frozen (no_grad, loss "
                              "coefficient 0)"),
        },
        "prerequisites": {
            "pilot_readout": "artifacts/marl/b0_v3_pilot/readout.json",
            "pilot_decision_required": "NO_SELECTION",
            "role_swap": "artifacts/marl/b0_v3_pilot/role_swap_c0_base_seed0_e10.json",
            "b0_v3_hash": "5e7b5b486b9d8a4a",
        },
        "arms": {
            "learned_limiter": {
                "limiter": "learned (MAPPO), final mean layer zeroed at t=0, "
                           "stochastic exploration retained, no commit head",
                "capturer": "scripted clean-fire (B2 rule)",
                "trained": True,
            },
            "hold_limiter": {"limiter": "hold (zeros)", "capturer":
                             "scripted clean-fire", "trained": False},
            "c5_limiter": {"limiter": "arc c5 (B2 RULE_COOP kw)", "capturer":
                           "scripted clean-fire", "trained": False},
        },
        "training": {
            "seeds": [0, 1],
            "total_env_steps": 32768,
            "rollout_env_steps": 512,
            "updates": 64,
            "checkpoint_every_updates": 8,
            "seed0": 53000,
            "seed_ns": "b5lim_train_v1",
            "sampler": "identical 70/20/10 row schedule as the pilot "
                       "(scheduled_cell), new jitter namespace",
            "hyperparameters": {
                "note": ("pilot ended NO_SELECTION, so no candidate is blessed; "
                         "these are pre-declared defaults (= c0_base values), "
                         "not winners"),
                "lr": 0.0003, "ent_coef_finisher": 0.003, "beta": 0.2,
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
        "evaluation": {
            "cells": "28 boundary cells (c1,c2)",
            "episodes_per_cell": 10,
            "seed0": 71000,
            "seed_ns": "b5lim_eval_v1",
            "policy": "stochastic with per-episode fixed torch seed; scripted "
                      "arms consume no torch randomness",
            "paired": "all three arms consume the identical (cell, sid, chi, "
                      "eta) stream and episode seeds",
            "metrics": ["clean N (partition_bin)", "FIRE", "clean crossing",
                        "H_illegal"],
            "credit_cut": ["H_illegal", "NET_SPENT"],
        },
        "readout": {
            "rule": ("descriptive only, pre-registered: per-arm counts of "
                     "N/FIRE/crossing/H_illegal, and per-cell paired "
                     "delta(N) sign counts for learned-vs-hold and "
                     "learned-vs-c5, per seed"),
            "selection_threshold": None,
            "promotion": "none; regardless of outcome this does not open W6",
            "stop": "budget exhaustion; abort on NaN/Inf training stats",
        },
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"b5 limiter-only manifest drift: {MANIFEST}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(MANIFEST)


if __name__ == "__main__":
    main()
