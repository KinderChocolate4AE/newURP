"""B2 scripted manifest 생성기 (docs/102 이행 — 실행기보다 **먼저**).

    python -m shepherd.scripts.b2_manifest      # artifacts/r2b/b2_scripted/manifest.json

**왜 manifest 가 먼저인가**: 실행기가 격자를 만들면 격자가 실행기의 자유도가 된다.
여기서 B0 v3 hash · docs/102 봉인 commit · 56 cell ID · arm 2 · scenario ID · seed
namespace 를 **파일로 못박고**, 실행기는 그것을 **소비만** 한다 (docs/102 §2 "cell ID 를
manifest 에 열거해 사후 선택 자유도를 0 으로 만든다").

격자는 하드코딩하지 않는다 — `artifacts/b0/b0_v3_world_contract.json` 의 `grid.rows`
에서 그대로 읽는다 (B0 v3 가 이미 R2a 산출물에서 유도해 봉인한 것). 재선택 금지 조항이
코드 구조로 강제된다.

**한 가지 상속 결정 (docs/102 가 명시하지 않은 것)**: 셀 안 scenario 추첨의 jitter.
R2a Stage1/Stage2 (chi50 의 출처) · R2b Phase 1 이 전부 `draw_cell_jitter` 로 셀 중심
둘레를 균일 추첨했고 (chi +-0.01 = lattice step 0.02 의 반폭, eta +-0.15), B2 는 그
격자 위에서 같은 estimand 를 재므로 같은 추첨 규약을 승계한다. **manifest 필드로
노출**하므로 (`crn.jitter`) 실행 전에 0 으로 봉인하고 싶으면 여기서 바꿔 다시 찍으면
된다 — 코드에 숨어 있지 않다. torch-free.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.provenance import git_commit                             # noqa: E402
from shepherd.scripts.r2a_stage1 import JITTER_CHI, JITTER_ETA         # noqa: E402

OUT_DIR = ROOT / "artifacts/r2b/b2_scripted"
MANIFEST = OUT_DIR / "manifest.json"
B0V3 = ROOT / "artifacts/b0/b0_v3_world_contract.json"

#: docs/102 봉인 commit (본문 f3f92c9 + r1 amendment b44ba42) — 실행 산출물이
#: "어느 사전등록 문안" 을 이행했는지 스스로 말하게 한다.
DOC = "docs/102_b2_scripted_prereg.md"
DOC_SEAL_COMMITS = ("f3f92c9", "b44ba42")

#: docs/102 §1. **limiter control 만 다르다** — 나머지는 전부 world 기본값.
ARMS = {
    "SOLO": {"limiter_mode": "hold", "limiter_kw": None,
             "basis": "B0 v3 B-arm 과 동일 의미 (hold_position_limiter = zeros(4))"},
    "RULE_COOP": {"limiter_mode": "arc",
                  "limiter_kw": {"r_d": 9.0, "dphi": math.pi / 6},
                  "basis": "docs/63 sect-7 SELECTED c5 — 이미 선택된 점 (새 자유도 0)"},
}

#: reference fallback (PN takeover) — **arm 이 아니다**. 양 arm 에서 동일하게 돌고
#: 기록만 한다 (docs/102 §1, docs/89 §10). ⚠ docs/102 는 이것을 "world 기본" 이라
#: 적었지만 env 에는 kill chain (contact -> veto -> Pk) 만 있었고 **조종 전환은
#: 미배선**이었다 — limiter 가 NET_SPENT 이후에도 arm 의 컨트롤러를 계속 썼다.
#: 여기서 처음 배선하며, 전환은 공용 rollout (`run_episode(kinetic_fallback=...)`)
#: 한 곳에만 있다. `baseline_commit=True` 는 B0 v3 의 kill chain 문안이 tau_kill
#: (= commit 경로에만 존재하는 지연) 을 명시한 데서 읽은 것이다 — KINETIC 단계
#: 한정이며 NET 단계 commit 은 계속 off.
FALLBACK = {
    "status": "NOT an arm — 기록만. P_U 는 primary pass 가 될 수 없다 (docs/102 §1)",
    "controller": "intercept",       # mission_rollout.intercept_limiter (교과서 lead-pursuit)
    "baseline_commit": True,
    "switch": "NET_SPENT 확정 다음 control tick (B0 v3 same_tick_precedence ③)",
    "wiring": "mission_rollout.run_episode(kinetic_fallback=...) — 양 arm 공통 경로",
    "open_item": "docs/102 는 fallback 을 'world 기본' 으로 전제했으나 실제로는 "
                 "미배선이었다. 이 필드가 그 배선의 유일한 정의원",
}

#: docs/102 §3 — B2 평가 CRN 은 MARL training seed 와 **섞지 않는다** (별도 namespace).
#: R2a `r2a_s1` / R2b `r2b_p1_v2` 와도 겹치지 않는 새 stream.
SEED_NS = "b2_scripted_v1"
SEED0 = 20_000
SEEDS = (0, 1, 2)                    # docs/102 §2.1 r1 amendment: eval seeds = 3
N_PER_CELL_PER_SEED = 300            # B0 v3 grid.n_per_cell_per_seed


def _cells(grid: dict) -> list:
    """B0 v3 `grid.rows` -> 56 cell. row 순서 · chi_base 순서를 그대로 쓴다."""
    cells = []
    for ri, row in enumerate(grid["rows"]):
        for ci, chi in enumerate(row["chi_base"]):
            cells.append({
                "cell_id": f"r{ri:02d}c{ci}",
                "row": ri, "lam_slice": row["lam_slice"], "lam": row["lam"],
                "R_max": row["R_max"], "eta": row["eta"], "chi": chi,
                # chi_base = {lo-0.04, lo, hi, hi+0.04}; 안쪽 두 점이 chi50 을
                # bracket 한다 = docs/102 §5.3 의 forced-fire boundary band.
                "chi_role": ("lo_out", "lo", "hi", "hi_out")[ci],
                "boundary_band": ci in (1, 2),
                "r2a_chi50": row["r2a_chi50"],
            })
    return cells


def build() -> dict:
    b0 = json.loads(B0V3.read_text(encoding="utf-8"))
    grid = b0["grid"]
    cells = _cells(grid)
    assert len(cells) == grid["G"] * grid["base_points_per_row"] == 56, len(cells)
    assert grid["n_per_cell_per_seed"] == N_PER_CELL_PER_SEED
    assert len(SEEDS) >= grid["seeds_min"]

    # scenario id 는 (cell, seed) 마다 **연속 블록**이다. 열거 대신 블록으로 적고
    # 전개된 id 열의 digest 를 함께 실어 실행기·판독기가 기계 대조한다.
    units, s = [], 0
    for c in cells:
        for sd in SEEDS:
            units.append({"cell_id": c["cell_id"], "seed": sd,
                          "s_lo": s, "s_hi": s + N_PER_CELL_PER_SEED})
            s += N_PER_CELL_PER_SEED
    ids_digest = hashlib.sha256(
        ",".join(str(i) for i in range(s)).encode()).hexdigest()[:16]

    m = {
        "schema": "b2-scripted-manifest-v1",
        "campaign": "B2 scripted baseline (SOLO vs RULE_COOP)",
        "prereg": {"doc": DOC, "seal_commits": list(DOC_SEAL_COMMITS),
                   "status": "sealed pre-run — arm/cell/CRN/forced-fire/metrics/"
                             "readout only"},
        "b0_v3_hash": b0["b0_hash"],
        "code_commit": git_commit(),
        "arms": ARMS,
        "common": {
            "fire_mode": "clean", "policy": None, "scripted_roles": [],
            "baseline_commit_net_phase": False,
            "note": "FIRE 경로 · attacker · world 는 양 arm 공통 — 실행기가 한 코드 "
                    "경로로 돌린다. NET 단계에서 limiter commit bit 는 off "
                    "(R2a/R2b 전 캠페인과 동일; 공짜 하드킬 금지)",
        },
        "fallback": FALLBACK,
        "grid_source": {"file": "artifacts/b0/b0_v3_world_contract.json",
                        "field": "grid.rows", "G": grid["G"],
                        "base_points_per_row": grid["base_points_per_row"],
                        "reselection": "FORBIDDEN — 이 manifest 가 유일한 격자 정의원"},
        "cells": cells,
        "crn": {
            "seed_ns": SEED_NS, "seed0": SEED0, "seeds": list(SEEDS),
            "n_per_cell_per_seed": N_PER_CELL_PER_SEED,
            "scenario_seed": "build_m4_env(seed0, s) · run_episode(seed=seed0 + s) "
                             "— 기존 SEED0 + s 규약 승계 (docs/102 §3)",
            "attacker_seed": "AttackerSpec(seed=0) + derive_phase(seed0, s) — resolve() "
                             "가 유일한 정의원 (arm 간 동일)",
            "evaluation_seed": "seeds = scenario 블록 index (학습 seed 아님 — B2 는 "
                               "scripted). MARL training seed 와 namespace 분리",
            "arm_pairing": "두 arm 이 같은 scenario id 열을 같은 순서로 소비 "
                           "(assert ids_solo == ids_rule + 초기 world-state hash 동일)",
            "jitter": {"chi": JITTER_CHI, "eta": JITTER_ETA,
                       "fn": "r2a_stage1.draw_cell_jitter(seed0, s, chi_c, eta_c, ns)",
                       "provenance": "R2a Stage1/2 (chi50 의 출처) · R2b Phase 1 과 "
                                     "동일 추첨 규약 승계. docs/102 는 명시하지 않았고 "
                                     "이 필드가 그 승계를 드러낸다"},
        },
        "units": units,
        "budget": {
            "scenarios": s, "episodes_primary": s * len(ARMS),
            "formula": f"{len(cells)} cell x {N_PER_CELL_PER_SEED} x {len(ARMS)} arm "
                       f"x {len(SEEDS)} seed = {s * len(ARMS):,} ep",
            "forced_fire": "별도 계정 (docs/102 §5.4) — 이 예산에 섞지 않는다",
        },
        "scenario_ids": {"rule": "units 의 [s_lo, s_hi) 연속 블록 · 전역 0..N-1",
                         "n": s, "digest": ids_digest},
        "outcome_fields": ["s", "arm", "cell_id", "seed", "chi", "eta", "fire",
                           "fire_step", "label", "bin", "steps", "hard_kill",
                           "veto_events", "n_contact"],
        "aggregation": "실행기는 집계하지 않는다 — raw outcome 만 저장하고 집계는 "
                       "b2_readout.py 에서만 (docs/102 §4 raw count identity)",
        "readout_scope": "B2 는 측정만. W5 stop rule 은 별도 봉인 규칙 (docs/102 §6)",
    }
    m["manifest_hash"] = hashlib.sha256(
        json.dumps(m, sort_keys=True, default=str).encode()).hexdigest()[:16]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    return m


def load() -> dict:
    """실행기·판독기의 단일 진입점. hash 를 되검증한다 (손편집 방지)."""
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    h = m.pop("manifest_hash")
    calc = hashlib.sha256(
        json.dumps(m, sort_keys=True, default=str).encode()).hexdigest()[:16]
    assert calc == h, f"manifest 가 손상됐다: {calc} != {h}"
    m["manifest_hash"] = h
    return m


if __name__ == "__main__":
    mf = build()
    print(f"manifest {mf['manifest_hash']}  b0_v3 {mf['b0_v3_hash']}  "
          f"cells {len(mf['cells'])}  units {len(mf['units'])}")
    print(f"  {mf['budget']['formula']}  (scenarios {mf['budget']['scenarios']:,})")
    print(f"  seed_ns {mf['crn']['seed_ns']}  seed0 {mf['crn']['seed0']}  "
          f"seeds {mf['crn']['seeds']}")
    print(f"  -> {MANIFEST.relative_to(ROOT)}")
