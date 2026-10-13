"""Seal R1 = 착취자 예산 민감도 (증거 1-1) — docs/138.

    python scripts/fs1_r1_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/r1_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_manifest import B_SEED0, B_SEEDS, B_STRIDE, B_VARIANTS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "r1_manifest.json"

BUDGETS = {"b1": 1e7, "b3": 3e7}              # 새 착취자 (scratch, 새 seed) — b1 은 원래 예산의 재학습, b3 는 3 배
B3_SNAPS = {"b3_at1e7": 1e7, "b3_at2e7": 2e7}  # v1.1: b3 run 안의 중간 체크포인트 (보고 전용)
JSEED = {"b1": 320000, "b3": 325000}          # + variant_idx*100 + seed (E7 277000·E1 300000/305000·E1b 310000 대역과 분리)
N = 240
MARGIN = 4                                    # 판 수 (/240)
POS = 10                                      # 15 slot 중


def budget_label(d) -> str:
    """d = slot 별 [ceil(b1) − ceil(b3)] (양수 = 더 학습한 착취자가 천장을 더 끌어내림). 의미 테스트: tests/test_fs1_eval.py."""
    s = sorted(d); med = s[len(s) // 2]
    if med >= MARGIN and sum(x > 0 for x in d) >= POS:
        return "BUDGET_UNDERTRAINED"            # 1e7 천장은 낙관치
    if abs(med) < MARGIN:
        return "BUDGET_CONVERGED"               # 1e7 → 3e7 에서 천장이 거의 안 움직임
    return "BUDGET_MIXED"


def build() -> dict:
    body = {
        "schema": "fs1-r1-manifest-v1.1",
        "amendment_v1_1": ("2026-10-13, advisor review, BEFORE any R1 production: b3 run saves snapshots at the first "
                           "checkpoint after 1e7 and 2e7 env steps (b3_at1e7, b3_at2e7) and they are evaluated as REPORT "
                           "lines (b3@1e7 vs b3@3e7 = within-seed budget effect; b1 vs b3@1e7 = exploiter-seed scatter at "
                           "equal budget; b3@2e7 -> 3e7 still falling = reported as 'not converged by 3e7' even under "
                           "CONVERGED). Judgment rule (b1 vs b3) unchanged. Meaning of CONVERGED and interpretation "
                           "pre-written (see rule.meaning)"),
        "status": ("sealed 2026-10-13 BEFORE any R1 production (contract docs/138; user 2026-10-13 'evidence collection "
                   "tonight'). Motivation: the night sandbox (exploratory, outside contracts) found 800 -> 2400 it red "
                   "teams cut the headline a lot; our ceilings rest on a fixed 1e7 exploiter"),
        "question": "does a 3x longer dedicated exploiter pull the E7-b matched-audit ceiling down, i.e. is 1e7 converged",
        "slots": [{"variant": v["name"], "seed": s, "tau_scale": v["tau_scale"], "theta_scale": v["theta_scale"],
                   "aim": v["aim"], "eval_seed": B_SEED0 + i * B_STRIDE, "idx": i}
                  for i, v in enumerate(B_VARIANTS) for s in B_SEEDS],
        "source": "server4 /data/hjhong/fs1jax/e7b/<variant>/s<seed>/ckpt.pt (E7-b frozen defense, no retraining)",
        "production": {"exploiters": {k: f"det exploiter vs frozen learned_det, scratch, total-steps {v:.0e}, "
                                         f"jseed {JSEED[k]} + idx*100 + seed" for k, v in BUDGETS.items()},
                       "recipe": "identical to the E7-b det exploiter except budget and jseed (--exploit ckpt --stack r4p + "
                                 "world flags of the variant)", "slots": 15, "runs": 30},
        "evaluation": {"n": N, "seed0": "E7-b eval band (276000 + idx*1000)", "env_seed": 0,
                       "defenders": ["learned_det (judgment)", "learned_sto (report)"],
                       "exploiters": "b1, b3 (new) + b3_at1e7, b3_at2e7 snapshots (report) + original E7-b 1e7 exploiter re-evaluated with --env-seed 0 (report)",
                       "metric": "defended (eval.summarize; same ceiling definition as E7-b) + net (report)"},
        "rule": {"d": "per slot d = ceil(b1) - ceil(b3), learned_det",
                 "labels": f"BUDGET_UNDERTRAINED: median d >= {MARGIN} and >= {POS}/15 slots d > 0; BUDGET_CONVERGED: "
                           f"|median d| < {MARGIN}; else BUDGET_MIXED",
                 "report": ["plateau median ceiling at b1 / b3 / original", "seed reproducibility |ceil(b1) - ceil(orig)|",
                            "exploiter final penetration (train log) per budget",
                            "b3_at1e7 / b3_at2e7 snapshots: within-seed budget curve (report only)"],
                 "meaning": ("CONVERGED = budget effect below ~4/240 (1.7 pp) given median SE ~2 — not a proof of "
                             "convergence. UNDERTRAINED = all ceilings so far are upper estimates of performance against "
                             "stronger red teams; the H1 plateau '~8%' becomes '<= ~8%' (direction of the story kept: the "
                             "adaptive evader sets the ceiling; only the number goes down)")},
        "power_memo": ("R0: per-slot env-seed SD <= binomial (~4/240 at p ~ .09); a paired b1-b3 difference has SD ~ 6 "
                       "incl. exploiter-seed scatter -> median of 15 has SE ~ 2; threshold 4 ~ 2 SE"),
        "pre_seal_checks": ["label semantics unit test tests/test_fs1_eval.py::test_r1_label_semantics",
                            "measurement window: episode outcomes only"],
        "not_evidence_for": ["convergence beyond 3e7", "other lineages", "re-judging any sealed verdict"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"R1 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(MANIFEST, build()["manifest_hash"])
