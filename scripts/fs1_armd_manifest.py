"""Seal arm D canonical eval: 이력 조건화 + 확률 정책 — docs/128.

    python scripts/fs1_armd_manifest.py      # manifest 기록 (정본 평가 결과 보기 전 봉인)
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "armd_manifest.json"

CELLS = [{"cell": "m0.35_n1", "mu": 0.35, "nu": 1.0, "ceil_ref": 5},
         {"cell": "m1.4_n1", "mu": 1.4, "nu": 1.0, "ceil_ref": 5}]
SEEDS = [0, 1, 2]
N, MARGIN, TRAIN_STEPS, EX_STEPS = 240, 24, 1.1e8, 1e7
SEED0, STRIDE = 274000, 1000
DEF_STACK = 4
AUDIT_THR, AUDIT_WINDOW = 0.90, 10


def build_armd() -> dict:
    body = {
        "schema": "fs1-armd-manifest-v1",
        "status": ("sealed before any canonical eval result (contract: docs/128). HONESTY FLAG: "
                   "the D-i inputs (exploiter training audit curves) already exist and their "
                   "finals were reported by the JAX lane (5x .99, 1x .93) before this seal — "
                   "D-i is therefore effectively known; it is still read out ONLY through the "
                   "estimator declared here. D-ii (canonical ceilings) is unseen"),
        "lineage": {"contract": "docs/128", "armc1": "1173759cf5e4854b (ARMC1_NULL — detection "
                    "ok, window generation is the bottleneck)",
                    "jax_pin": "b3031ed (35/35 green; fixed semantics = k=4 latest-first "
                    "tile-init, BC first-layer transplant with start-tick BC-equivalence test, "
                    "audit exploiter trained vs sto)"},
        "question": ("Q-D: does history conditioning (defense obs frame stack k=4) + stochastic-"
                     "policy judgment defeat the co-adapted exploiter's frozen-determinism "
                     "exploit — (i) softening the audit signature, (ii) restoring window "
                     "generation / opening the ceiling"),
        "judgment_defender": ("learned_sto — PRE-DECLARED JUDGMENT-MODEL CHANGE, this contract "
                              "only (docs/128 §1): the mechanism under test is unpredictability, "
                              "so a determinized readout removes the mechanism itself. "
                              "learned_det reported. No pooling with det-judged experiments"),
        "production": {
            "defense": ("JAX b3031ed: arm C-1 recipe (r4p + distilled fire head, docs/127 label "
                        f"unchanged) + defense obs frame stack k={DEF_STACK} (latest-first, "
                        "tile-init), 264-D input, 1.1e8, seeds 0/1/2"),
            "exploiter": "fresh dedicated exploiter vs the FROZEN STOCHASTIC defense, 1e7, "
                         "jseed 275000-band, audit curve logged",
            "paths": "/data1/hjhong/fs1jax/e3b/armd/<cell>/s<seed>/{ckpt.pt, judge_exploiter/}",
            "transfer": "strip = {teams, it, total_steps} + pools/pool_snaps last-1 truncate "
                        "(armc1 precedent), count-verified both ends",
        },
        "evaluation": {"n": N, "seed0": SEED0, "cell_seed_stride": STRIDE, "paired": True,
                       "stack": "r4p", "def_stack": DEF_STACK, "groups": "none",
                       "defenders": ["learned_sto (judgment)", "learned_det (report)"],
                       "mirror": ("canonical eval frame-stack mirror = shepherd.fs1.eval "
                                  "--def-stack 4 (latest-first, tile-init — same declared "
                                  "semantics as the JAX pin); smoke on one slot before launch"),
                       "environment": "server4 (.venv-l2); seed band 274000+ never used in "
                                      "training/labeling",
                       "report_extras": ["fired-ep count / robust-fire conversion / window "
                                         "occurrence (reference comparison to armc1 under the "
                                         "same threshold family only — no pooling)",
                                         "trajectories --traj 2 (viz-first)"]},
        "gates": {
            "D-i": (f"audit softening: mean of the LAST {AUDIT_WINDOW} win_rate entries of "
                    f"judge_exploiter/log.jsonl <= {AUDIT_THR} on >= 2 of 3 seeds, per cell "
                    "-> AUDIT_SOFTENED(cell)"),
            "D-ii": (f"ceiling: ceil_learned_sto >= ceil_ref + {MARGIN} = 29/{N} on >= 2 of 3 "
                     "seeds, per cell -> ARMD_OPENS(cell)"),
            "decision": ("any cell D-ii -> ARMD_OPENS; else any cell D-i -> ARMD_AUDIT_ONLY; "
                         "else ARMD_NULL. INVALID per budget/completion/paired/manifest "
                         "violation (cell excluded and reported)"),
        },
        "not_evidence_for": ["emergence (history conditioning is a design prescription)",
                             "cooperation vocabulary (limiter-control opportunity)",
                             "pooling with armc1/phase2/P0 numbers"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_armd() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build_armd():
        raise ValueError(f"arm D manifest drift: {MANIFEST}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    body = build_armd()
    MANIFEST.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{MANIFEST} {body['manifest_hash']}")


if __name__ == "__main__":
    main()
