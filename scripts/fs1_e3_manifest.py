"""Seal E3: 방어-가능 regime 지도 (capability-ratio 격자) — docs/124.

    python scripts/fs1_e3_manifest.py            # manifest 기록 (봉인 — stage 1 결과 보기 전)
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e3_regime_map_manifest.json"

GRID_MU = [0.35, 0.5, 0.7, 1.0, 1.4]
GRID_NU = [0.8, 1.0, 1.25]
N = 240
BAND = (48, 216)                 # stage 2 선정: ceiling_s ∈ [20%, 90%] — 하한 = 바닥 비교 배제,
                                 # 상한 = 포화 배제 + D ≥ +24 산술 가능성 (docs/124 §3)
MARGIN = 24
SEED0 = 263000
CELL_SEED_STRIDE = 1000          # cell (i_mu, i_nu) 의 seed0 = SEED0 + (i_mu*len(GRID_NU)+i_nu)*stride
EX_STEPS = 1e7
TRAIN_STEPS = 1.1e8
SEEDS_S2 = [0, 1, 2]
K_VIAB_B = 0.2
IMPL = {                          # 구현 고정 (사전 기입 — 실행 로그의 commit 과 대조)
    "canonical_world_mu_nu": "shepherd.fs1.world FS1Spec(mu, nu): a_def = mu*a_att, v_def = nu*v_att, attacker unchanged",
    "stage1_exploiters": ("JAX 0df35f3 (= sealed v2 e8806d9 semantics + mu/nu & scripted:fin12_fb CLI "
                          "plumbing only + golden regen; world r4 path bit-exact vs seal hash "
                          "14b9d56f20b1cfb9, 32/32 green), --stack r4 (pilot-comparable)"),
    "stage2_training": ("JAX 0df35f3 (32/32 parity incl. r4p/k_viab step-exact, mu-nu spot-check), "
                        "--stack r4p; arm B adds --k-viab 0.2"),
    "judgment_eval": "canonical shepherd.fs1.eval on server4 (i9-12900K), commit recorded in each summary meta.git",
}


def build() -> dict:
    cells = [{"cell": f"m{m:g}_n{n:g}", "mu": m, "nu": n} for m in GRID_MU for n in GRID_NU]
    body = {
        "schema": "fs1-e3-regime-map-manifest-v1.2",
        "status": "sealed before any stage-1 result (design doc: docs/124)",
        "revises": ("8ed5a8b42dd41448 (v1.2: training host server5 -> server5 OR server6, both RTX "
                    "4500 Ada; server6 gate passed — resolved world constants bit-exact vs server5 "
                    "(sha c3ef48a58aa37429), f32 paired McNemar all |z|<3 (worst 2.138), exploit "
                    "smoke 35-44k sps. Judgment evaluations unchanged on server4). Chain: v1.1 "
                    "8ed5a8b42dd41448 revised 97880faa933aca9c (v1 pinned a commit that cannot "
                    "execute the grid; v1.1 pinned verified 0df35f3; the 18:08 pre-signal partial "
                    "launch stays quarantined and uncounted)"),
        "design_doc": "docs/124_e3_regime_map_contract_draft.md",
        "questions": {
            "Q1": "where in the (mu, nu) defender-capability plane does the dedicated-exploiter ceiling of the best scripted defense open",
            "Q2": "in open cells, does co-trained defense beat the best scripted defense under the sealed D >= +24/240 rule, and does the arm-B objective change (fire-tick viability bonus) alter that",
        },
        "grid": {"mu": GRID_MU, "nu": GRID_NU, "cells": cells,
                 "rule": "defender-only conditioning; attacker = ratified threat of cell r06c1, fixed. mu=0.35, nu=1.0 reproduces the pilot world bit-exact (never pooled with pilot results)"},
        "prediction_non_gating": "ceiling_s is monotone non-decreasing in mu; the band crossing mu* lies in [0.5, 1.0] (terminal-dodge mechanism; to be contrasted with the E6 analytic bound)",
        "stage1": {
            "per_cell": ["dedicated exploiter vs kfirst50 and vs fin12_fb (1e7 steps each, exploit mode, sealed-v2 impl)",
                         f"canonical paired eval {N} eps per (defender, own exploiter); ceiling_s = max defended/{N}",
                         "diagnostic (report-only, all scripted, 96 eps each): limiter {hold, c5-arc, fwd-arc, kfirst50} x finisher fin12 vs nominal ladder — credit vs equilibrium vs no-opportunity reading per docs/124 D3",
                         "nominal-ladder sanity 96 eps + trajectory figures (viz-first)"],
            "selection": f"stage-2 cells = ALL cells with ceiling_s in [{BAND[0]}, {BAND[1]}] of {N}; none -> E3_BAND_EMPTY",
        },
        "stage2": {
            "arms": {"A": "r4' control: --stack r4p (potential dist shaping, obs t/T, PFSP f_var), k_viab 0",
                     "B": f"A + fire-tick viability bonus k_viab {K_VIAB_B} (non-potential; B-A reported as objective-change effect only)"},
            "per_cell": f"2 arms x seeds {SEEDS_S2}, budget {TRAIN_STEPS:.1e} env steps each, BC per seed (--stack r4p, arm B BC with --k-viab)",
            "evaluation": "eval-v1 procedure per arm-seed (dedicated exploiters 1e7, pool, nominal ladder, 240 eps paired) on server4; seed decision = v2-style rule (D_pool and D_ex >= +24, D_ladder NARROW modifier); arm confirmed on >= 2 of 3 seeds",
            "diagnostics_logged_not_paid": "fire-tick v_shot_soft and p_feasible logged for BOTH arms (emergence claims from arm A only)",
        },
        "verdicts": {
            "always": "E3_BOUNDARY_MAPPED (stage-1 heatmap)",
            "E3_LEARNING_OPENS": "some selected cell has a confirmed arm (A or B)",
            "E3_NO_ADVANTAGE_IN_BAND": "stage 2 ran, none confirmed",
            "E3_BAND_EMPTY": "no cell selected",
            "INVALID_E3": "lineage/completion/paired/budget violation (per-cell; an invalid cell is excluded and reported, never silently rerun)",
        },
        "evaluation_discipline": {
            "namespace": "fs1_e3_v1", "seed0": SEED0, "cell_seed_stride": CELL_SEED_STRIDE,
            "paired": "within a cell, every defender/arm sees identical episode seeds",
            "environment": ("judgment evaluations and canonical exploiter evals on server4; training "
                            "and exploiter training on JAX GPU — server5 or server6 (same model, "
                            "constants verified bit-exact; whichever frees first is valid)"),
            "pooling": "never pooled with B0 v3, pilot, or across cells; mu != 0.35 or nu != 1.0 cells are world variants outside B0 v3",
            "exploiter_budget": f"{EX_STEPS:.0e} fixed (pilot comparability); larger-budget exploiters are report-only",
        },
        "implementation": IMPL,
        "not_evidence_for": ["real-airframe representativeness", "net-spec axes (E7)", "6DOF/plant (E8)",
                             "Huh/G&B quantitative comparison", "cooperation vocabulary (use limiter-control opportunity)"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E3 manifest drift: {MANIFEST}")
    return data


def select_cells(ceilings: dict) -> list:
    """ceilings = {cell: ceiling_s (defended count / N 중 분자)} → stage-2 cell 목록 (규칙 §stage1)."""
    return [c for c, v in sorted(ceilings.items()) if BAND[0] <= v <= BAND[1]]


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    main()
