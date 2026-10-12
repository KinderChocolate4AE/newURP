"""Seal R0 = 평가 반복성 (측정 잡음 바닥) — docs/135.

    python scripts/fs1_r0_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/r0_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_manifest import B_SEED0, B_STRIDE, B_VARIANTS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "r0_manifest.json"


def _slot(var, seed, why):
    i = [v["name"] for v in B_VARIANTS].index(var)
    v = B_VARIANTS[i]
    return {"variant": var, "seed": seed, "why": why, "tau_scale": v["tau_scale"], "theta_scale": v["theta_scale"],
            "aim": v["aim"], "eval_seed": B_SEED0 + i * B_STRIDE}


# 선택 규칙 (봉인 전 고정): E7-b det 정합 천장 (ceil_det) 이 15 slot 중앙값 21 에 가장 가까운 slot (동점 = manifest 순서
# 첫째) = 평탄부 / ceil_det 최소 slot = 낮은 천장. 값은 기존 E7-b readout (재판정 아님).
SLOTS = [_slot("t0.5_h1.0_cv", 0, "plateau: ceil_det 21 = median of 15 (first in manifest order among ties)"),
         _slot("t0.7_h1.0_cv", 1, "low ceiling: min ceil_det 7")]
EXPLOITERS = {"det": "judge_exploiter", "sto": "judge_exploiter_sto"}
ENV_SEEDS = list(range(8))
N = 240
OVERDISP = 1.5          # env-seed SD > 1.5 × 이항 SD → OVERDISPERSED
RATIO_FLOOR = 1.5       # 불일치/정합 비율의 bootstrap 95% 하한이 이보다 커야 '잡음을 넘는 과대평가'
N_BOOT = 2000
# 각 평가 1회 = 한 착취자 상대로 learned_det·learned_sto 둘 다 → 정합/불일치 칸
CELLS = {("det", "det"): "matched", ("sto", "sto"): "matched", ("det", "sto"): "mismatched",
         ("sto", "det"): "mismatched"}          # (방어, 착취자 학습 상대)


def dispersion_label(sd_env, mean, n=N):
    p = min(max(mean / n, 1e-9), 1 - 1e-9)
    return "R0_BINOMIAL" if sd_env <= OVERDISP * (n * p * (1 - p)) ** 0.5 else "R0_OVERDISPERSED"


def inflation_label(lower_bounds) -> str:
    """lower_bounds = 4 칸 (2 slot × 방어 2 줄) 의 불일치/정합 비율 bootstrap 95% 하한."""
    k = sum(lb > RATIO_FLOOR for lb in lower_bounds)
    return "INFLATION_EXCEEDS_NOISE" if k == len(lower_bounds) else ("INFLATION_PARTIAL" if k else
                                                                     "INFLATION_WITHIN_NOISE")


def build() -> dict:
    body = {
        "schema": "fs1-r0-manifest-v1",
        "status": ("sealed 2026-10-12 BEFORE any R0 evaluation (contract docs/135; user approval 10-12; design = "
                   "advisor 10-12 sketch). The only new contract allowed before 10/26 by the advisor rule"),
        "question": ("with frozen defense and frozen exploiter, how much does the canonical 240-episode ceiling move "
                     "when only the environment seed changes, and does the cross-audit inflation (mismatched / "
                     "matched, 2.6-3.8x) exceed that noise"),
        "finding_behind": ("10-12: with --env-seed fixed a re-run is byte-identical, so repeatability must be "
                           "measured by varying the env seed (worker env RNG leaks into the m4 stack); initial "
                           "states (--seed band) stay fixed"),
        "slots": SLOTS, "exploiters": EXPLOITERS, "env_seeds": ENV_SEEDS, "n": N,
        "source": "server4 /data/hjhong/fs1jax/e7b/<variant>/s<seed> (E7-b / E7-b' checkpoints, no retraining)",
        "evaluation": ("python -m shepherd.fs1.eval run, defenders learned_det learned_sto, one run per (slot, "
                       "exploiter, env seed) = 32 runs, flags as the E7-b runner (incl. --coop-window) plus --env-seed k"),
        "cells": {f"{d}|{e}": t for (d, e), t in CELLS.items()},
        "labels": {
            "dispersion (per slot x cell)": f"SD over env seeds <= {OVERDISP} x binomial SD -> R0_BINOMIAL else "
                                            "R0_OVERDISPERSED",
            "inflation": (f"ratio = mean(mismatched)/mean(matched) per (slot, defense line); stratified bootstrap "
                          f"over env seeds (numerator and denominator resampled independently), {N_BOOT} reps, rng 0; "
                          f"95% lower bound > {RATIO_FLOOR} in all 4 -> INFLATION_EXCEEDS_NOISE, in 1-3 -> "
                          "INFLATION_PARTIAL, in 0 -> INFLATION_WITHIN_NOISE")},
        "power_memo": ("advisor: matched p ~ .08 -> binomial SD ~4.2/240, mismatched p ~ .25 -> ~6.7; a ~40 "
                       "difference is ~5 sigma; the risk is overdispersion"),
        "use": ("one sentence in the evaluation-method section next to 2.6-3.8x and next to borderline verdicts; "
                "NO re-judgment of any sealed verdict"),
        "pre_seal_checks": ["label semantics unit test tests/test_fs1_eval.py::test_r0_label_semantics",
                            "measurement window: episode outcomes only (defended count; coop-window kept on only to match E7-b)"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"R0 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for s in SLOTS:
        print(s)
    print(MANIFEST, build()["manifest_hash"])
