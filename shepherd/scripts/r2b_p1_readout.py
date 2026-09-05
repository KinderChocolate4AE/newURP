"""R2b Phase 1 v2 판독 — B0 v2 (cba024d7ee3d9f61) 봉인 규칙의 기계 적용.

    python -m shepherd.scripts.r2b_p1_readout

층위 (B0 v2 competing_risk_semantics): primary Δp_net (HARD_KILL = net 실패) /
secondary Δp_U (neutralization, p_U = p_N + p_H) / p_H 보고. P1-positive 규칙
(Δp_net 층): 14행 중 ≥12행 점추정 > 0 AND 각 λ slice ≥5/7 AND 전역 paired CI95
하한 > 0 (셀-층화 scenario bootstrap B=4000). readout 은 branch seal 존재를 assert.
displacement 3-경우 분류는 행별 (양쪽 셀 p_B_net vs 0.5). torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
ART2 = ROOT / "artifacts/r2b"
B = 4000


def main() -> None:
    br = json.loads((ART2 / "c_budget_branch.json").read_text(encoding="utf-8"))
    b0 = json.loads((ART2 / "b0_world_contract.json").read_text(encoding="utf-8"))
    assert b0["b0_hash"] == "cba024d7ee3d9f61" and br["threshold_hours"] == 14.0

    recs = []
    for f in sorted((ART2 / "phase1_v2").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["b0_hash"] == b0["b0_hash"]
        recs += s["records"]
    assert len(recs) == 22400

    # {(slice, cell) -> {arm -> {s -> label}}}
    by = {}
    for r in recs:
        by.setdefault((r["slice"], tuple(r["cell"])), {}).setdefault(
            r["arm"], {})[r["s"]] = r["label"]
    cells = sorted(by)
    rng = np.random.default_rng(0)

    def layers(labels: np.ndarray):
        n = (labels == "NET_CAPTURE").astype(float)
        h = (labels == "HARD_KILL").astype(float)
        return n, h, n + h

    out = {"b0_hash": b0["b0_hash"], "branch_hash": br["branch_hash"], "B": B,
           "cells": {}, "rows": {}}
    dnet_all, du_all = [], []                     # 셀-층화 bootstrap 용
    print(f"{'cell':>14} {'pA_N':>6} {'pB_N':>6} {'dN':>7} {'pA_H':>6} {'pB_H':>6} {'dU':>7}")
    for key in cells:
        ss = sorted(by[key]["A"])
        la = np.array([by[key]["A"][s] for s in ss])
        lb = np.array([by[key]["B"][s] for s in ss])
        aN, aH, aU = layers(la)
        bN, bH, bU = layers(lb)
        dN, dU = bN - aN, bU - aU
        dnet_all.append(dN); du_all.append(dU)
        out["cells"][f"{key[0]}|{key[1][0]},{key[1][1]}"] = {
            "n": len(ss),
            "A": {"p_net": float(aN.mean()), "p_hard": float(aH.mean()), "p_U": float(aU.mean())},
            "B": {"p_net": float(bN.mean()), "p_hard": float(bH.mean()), "p_U": float(bU.mean())},
            "d_net": float(dN.mean()), "d_U": float(dU.mean())}
        print(f"{str(key):>14} {aN.mean():>6.3f} {bN.mean():>6.3f} {dN.mean():>+7.3f} "
              f"{aH.mean():>6.3f} {bH.mean():>6.3f} {dU.mean():>+7.3f}")

    # ── 행 (slice, eta) 14개: 두 셀 pooled ─────────────────────────────────────
    rows = {}
    for sl in (0, 2):
        for eta in (2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9):
            ks = [k for k in cells if k[0] == sl and abs(k[1][1] - eta) < 1e-9]
            dN = np.concatenate([np.array([int(by[k]["B"][s] == "NET_CAPTURE") -
                                           int(by[k]["A"][s] == "NET_CAPTURE")
                                           for s in sorted(by[k]["A"])]) for k in ks])
            pB = [out["cells"][f"{k[0]}|{k[1][0]},{k[1][1]}"]["B"]["p_net"] for k in ks]
            disp = ("right_displaced" if all(p > 0.5 for p in pB)
                    else "left_case" if all(p < 0.5 for p in pB) else "in_band")
            rows[f"{sl}|{eta}"] = {"d_net": float(dN.mean()), "positive": bool(dN.mean() > 0),
                                   "pB_net_cells": [round(p, 3) for p in pB],
                                   "displacement": disp}
    out["rows"] = rows

    # ── 봉인 P1 규칙 (Δp_net 층) ───────────────────────────────────────────────
    pos = sum(r["positive"] for r in rows.values())
    per_slice = {sl: sum(r["positive"] for k, r in rows.items() if k.startswith(f"{sl}|"))
                 for sl in (0, 2)}
    idxs = [rng.integers(0, len(d), (B, len(d))) for d in dnet_all]
    boots = np.mean([d[i].mean(axis=1) for d, i in zip(dnet_all, idxs)], axis=0)
    ci = [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))]
    g = float(np.mean([d.mean() for d in dnet_all]))
    p1 = (pos >= 12) and all(v >= 5 for v in per_slice.values()) and ci[0] > 0
    bootsU = np.mean([d[i].mean(axis=1) for d, i in zip(du_all, idxs)], axis=0)
    ciU = [float(np.quantile(bootsU, .025)), float(np.quantile(bootsU, .975))]
    disp_rows = [k for k, r in rows.items() if r["displacement"] == "right_displaced"]
    out.update({
        "p1_rule": {"rows_positive": [pos, 14], "per_slice_positive": per_slice,
                    "global_d_net": g, "global_ci95": ci,
                    "verdict": "P1_POSITIVE" if p1 else "P1_NOT_POSITIVE"},
        "secondary_U": {"global_d_U": float(np.mean([d.mean() for d in du_all])),
                        "global_ci95": ciU},
        "hard_kill": {"B_total": int(sum((np.array([by[k]["B"][s] for s in sorted(by[k]["B"])]) == "HARD_KILL").sum() for k in cells)),
                      "A_total": 0},
        "displacement_rows_right": disp_rows,
        "phase2_trigger": bool(p1 and disp_rows),
    })
    (ART2 / "p1_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nP1 rule: rows+ {pos}/14  slice+ {per_slice}  global dN {g:+.3f} "
          f"CI [{ci[0]:+.3f},{ci[1]:+.3f}]  -> {out['p1_rule']['verdict']}")
    print(f"secondary dU {out['secondary_U']['global_d_U']:+.3f} CI "
          f"[{ciU[0]:+.3f},{ciU[1]:+.3f}]   B-arm HARD_KILL {out['hard_kill']['B_total']}")
    print(f"right-displaced rows: {len(disp_rows)}  phase2_trigger: {out['phase2_trigger']}")


if __name__ == "__main__":
    main()
