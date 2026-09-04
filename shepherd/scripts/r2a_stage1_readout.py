"""paper-R2a Stage 1 kill screen 판독 — paired 3분법 + DOM 별도 n 재산정.

    python -m shepherd.scripts.r2a_stage1_readout

봉인 준거 (protocol 1496a4769876b438): 셀 판정 = scenario-paired Δp 의 CI95 ⊂ ±delta_p
(0.10) → PASS / 걸침 → INCONCLUSIVE / 밖 → FAIL. n 재산정 = R-ref↔R-tau-DOM,
R-ref↔R-rho-DOM **별도** (SIM pooling 금지), 셀별 discordant 분산에서 "참 Δ=0 에서
기대 PASS ≥ 90%" n 을 보수적으로 (max) 역산. 지위 = falsification screen — 대표성
주장 없음. CI = scenario-paired bootstrap (percentile, B=4000). torch-free.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ART = ROOT / "artifacts/r2a"
DELTA_P = 0.10
B = 4000
IMPLS = ("R-ref", "R-tau-SIM", "R-rho-SIM", "R-tau-DOM", "R-rho-DOM")


def load() -> dict:
    """{(cell, impl): {scenario: capture}} — paired 정렬은 scenario id 로."""
    by = {}
    for f in sorted((ART / "stage1").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["protocol_hash"] == "1496a4769876b438"
        for r in s["records"]:
            assert r["label"] in ("NET_CAPTURE", "PENETRATED"), r   # HARD_KILL STOP 재확인
            by.setdefault((tuple(r["cell"]), r["impl"]), {})[r["s"]] = int(r["label"] == "NET_CAPTURE")
    return by


def paired_verdict(ref: np.ndarray, x: np.ndarray, rng) -> dict:
    d = x - ref
    dp = float(d.mean())
    n = len(d)
    idx = rng.integers(0, n, (B, n))
    boots = d[idx].mean(axis=1)
    lo, hi = float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))
    verdict = ("PASS" if -DELTA_P < lo and hi < DELTA_P
               else "FAIL" if lo >= DELTA_P or hi <= -DELTA_P else "INCONCLUSIVE")
    q = float((d != 0).mean())                      # discordant fraction
    return {"n": n, "dp": dp, "ci95": [lo, hi], "discordant": int((d != 0).sum()),
            "q": q, "verdict": verdict}


def n_for_expected_pass(q: float, target: float = 0.90) -> int:
    """참 Δ=0, sd = sqrt(q/n): PASS 확률 = 2Φ((δp−1.96σ)/σ)−1 ≥ target 인 최소 n."""
    from math import erf, sqrt
    if q == 0.0:
        return 1
    for n in range(50, 20001, 10):
        s = sqrt(q / n)
        if DELTA_P - 1.96 * s <= 0:
            continue
        p = erf((DELTA_P - 1.96 * s) / (s * sqrt(2)))
        if p >= target:
            return n
    return -1


def main() -> None:
    by = load()
    cells = sorted({c for c, _ in by})
    rng = np.random.default_rng(0)
    out = {"protocol_hash": "1496a4769876b438", "delta_p": DELTA_P, "B": B,
           "status": "falsification screen — no representativeness claim",
           "cells": {}, "n_recalc": {}}
    print(f"{'cell':>12} {'impl':>10} {'p':>6} {'dp':>7} {'CI95':>18} {'disc':>5}  verdict")
    for c in cells:
        ref_map = by[(c, "R-ref")]
        ss = sorted(ref_map)
        ref = np.array([ref_map[s] for s in ss])
        row = {"n": len(ss), "p_ref": float(ref.mean())}
        print(f"{str(c):>12} {'R-ref':>10} {ref.mean():>6.3f}")
        for im in IMPLS[1:]:
            x = np.array([by[(c, im)][s] for s in ss])
            v = paired_verdict(ref, x, rng)
            row[im] = v
            print(f"{'':>12} {im:>10} {x.mean():>6.3f} {v['dp']:>+7.3f} "
                  f"[{v['ci95'][0]:+.3f},{v['ci95'][1]:+.3f}] {v['discordant']:>5}  {v['verdict']}")
        out["cells"][str(c)] = row
    # ── n 재산정: DOM 별도, 셀 간 worst q (SIM 은 참고 출력만) ─────────────────
    for im in ("R-tau-DOM", "R-rho-DOM"):
        qs = {str(c): out["cells"][str(c)][im]["q"] for c in cells}
        worst = max(qs.values())
        out["n_recalc"][im] = {"q_by_cell": qs, "worst_q": worst,
                               "n_for_90pct_pass": n_for_expected_pass(worst)}
    out["n_recalc"]["stage3_n"] = max(v["n_for_90pct_pass"] for k, v in out["n_recalc"].items()
                                      if isinstance(v, dict))
    sim_disc = sum(out["cells"][str(c)][im]["discordant"]
                   for c in cells for im in ("R-tau-SIM", "R-rho-SIM"))
    out["sim_total_discordant"] = sim_disc
    (ART / "stage1_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nSIM total discordant (4,800 paired ep): {sim_disc}")
    for im in ("R-tau-DOM", "R-rho-DOM"):
        r = out["n_recalc"][im]
        print(f"n_recalc {im}: worst q {r['worst_q']:.3f} -> n {r['n_for_90pct_pass']}")
    print(f"Stage 3 n (conservative max): {out['n_recalc']['stage3_n']}")
    print(f"-> {ART / 'stage1_readout.json'}")


if __name__ == "__main__":
    main()
