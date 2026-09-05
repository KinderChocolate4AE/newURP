"""paper-R2a Stage 4 (직교 lambda) 판정 + Stage 2 (R-ref full map) 집계.

    python -m shepherd.scripts.r2a_stage24_readout

Stage 4 준거 (protocol 59c4de1889ed72dc, 결과 열람 전 봉인):
  POSITIVE = 방향 (6셀 전부 paired CI95 상한 < 0, L2 vs L0) AND material (pooled
  |dp| >= 0.20) / secondary = dose ordering (pooled dp(L1) 이 0 과 dp(L2) 사이,
  비게이트) / 아니면 NEGATIVE (미해소 bundle — 자동 승격 금지).
Stage 2 (protocol 3bc9dba2fe01385f): 행별 chi50(eta) isotonic + boot CI — C044 입력.
torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.r2a_stage0 import chi50_isotonic          # noqa: E402

ART = ROOT / "artifacts/r2a"
B = 4000


def stage4() -> dict:
    by = {}                                    # {(cell, level): {s: capture}}
    for f in sorted((ART / "stage4").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["protocol_hash"] == "59c4de1889ed72dc"
        for r in s["records"]:
            by.setdefault((tuple(r["cell"]), r["level"]), {})[r["s"]] = \
                int(r["label"] == "NET_CAPTURE")
    cells = sorted({c for c, _ in by})
    rng = np.random.default_rng(0)
    out = {"protocol_hash": "59c4de1889ed72dc", "cells": {}, }
    pooled = {1: [], 2: []}
    direction_all = True
    print(f"{'cell':>12} {'p_L0':>6} {'p_L1':>6} {'p_L2':>6} {'dp_L2':>7} {'CI95(L2)':>18}  dir")
    for c in cells:
        ss = sorted(by[(c, 0)])
        l0 = np.array([by[(c, 0)][s] for s in ss])
        row = {"n": len(ss), "p_L0": float(l0.mean())}
        for lv in (1, 2):
            x = np.array([by[(c, lv)][s] for s in ss])
            d = x - l0
            idx = rng.integers(0, len(d), (B, len(d)))
            boots = d[idx].mean(axis=1)
            ci = [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))]
            row[f"L{lv}"] = {"p": float(x.mean()), "dp": float(d.mean()), "ci95": ci}
            pooled[lv].append(d)
        ok_dir = row["L2"]["ci95"][1] < 0.0
        direction_all &= ok_dir
        row["direction_ok"] = ok_dir
        out["cells"][str(c)] = row
        print(f"{str(c):>12} {row['p_L0']:>6.3f} {row['L1']['p']:>6.3f} {row['L2']['p']:>6.3f} "
              f"{row['L2']['dp']:>+7.3f} [{row['L2']['ci95'][0]:+.3f},{row['L2']['ci95'][1]:+.3f}]"
              f"  {'OK' if ok_dir else 'X'}")
    dp1 = float(np.concatenate(pooled[1]).mean())
    dp2 = float(np.concatenate(pooled[2]).mean())
    material = abs(dp2) >= 0.20
    dose = (dp2 < dp1 < 0.0) or (0.0 < dp1 < dp2)
    verdict = "POSITIVE" if direction_all and material else "NEGATIVE"
    out.update({"pooled_dp_L1": dp1, "pooled_dp_L2": dp2,
                "direction_all_cells": direction_all, "material_ge_0p20": material,
                "dose_ordering_secondary": dose, "verdict": verdict})
    print(f"\npooled dp: L1 {dp1:+.3f}  L2 {dp2:+.3f}")
    print(f"direction 6/6: {direction_all}  material |dp_L2|>=0.20: {material}  "
          f"dose ordering (secondary): {dose}")
    print(f"STAGE 4 VERDICT: {verdict}")
    (ART / "stage4_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def stage2() -> dict:
    rec = []
    for f in sorted((ART / "stage2").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["protocol_hash"] == "3bc9dba2fe01385f"
        rec += s["records"]
    chi = np.array([r["chi"] for r in rec])
    eta = np.array([r["eta"] for r in rec])
    y = np.array([int(r["label"] == "NET_CAPTURE") for r in rec], float)
    rng = np.random.default_rng(0)
    etas = sorted({r["cell"][1] for r in rec})
    out = {"protocol_hash": "3bc9dba2fe01385f", "n": len(rec), "rows": {}}
    print(f"\nStage 2 (R-ref full map, n={len(rec)}):")
    print(f"{'eta':>5} {'n':>5} {'p':>6} {'chi50':>7} {'CI95':>17}")
    for e in etas:
        m = np.abs(eta - e) <= 0.15 + 1e-9
        c50 = chi50_isotonic(chi[m], y[m])
        boots = []
        cm, ym = chi[m], y[m]
        for _ in range(500):
            i = rng.integers(0, len(cm), len(cm))
            boots.append(chi50_isotonic(cm[i], ym[i]))
        ok = np.asarray([b for b in boots if not np.isnan(b)])
        ci = [float(np.quantile(ok, 0.025)), float(np.quantile(ok, 0.975))]
        out["rows"][str(e)] = {"n": int(m.sum()), "p": float(y[m].mean()),
                               "chi50_isotonic": float(c50), "ci95": ci,
                               "censored": bool(np.isnan(c50))}
        print(f"{e:>5} {int(m.sum()):>5} {y[m].mean():>6.3f} {c50:>7.3f} "
              f"[{ci[0]:.3f},{ci[1]:.3f}]")
    st0 = json.loads((ART / "stage0_envelope.json").read_text(encoding="utf-8"))
    diffs = {e: out["rows"][e]["chi50_isotonic"] - st0["rows"][e]["chi50_isotonic"]
             for e in out["rows"] if e in st0["rows"]}
    out["chi50_minus_stage0"] = diffs
    print("chi50 - Stage0:", {k: round(v, 3) for k, v in diffs.items()})
    (ART / "stage2_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    stage4()
    stage2()
