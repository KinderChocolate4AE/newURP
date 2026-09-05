"""paper-R2a Stage 3 confirmatory 판독 (protocol eb3a85e702020167, estimand_clarified 준수).

    python -m shepherd.scripts.r2a_stage3_readout

순서 (봉인): (a) A2-nom 팔만으로 slice 별 nominal chi50(eta) — 3-D surface unlock 판정
(b) 셀-국소 p_worst,A2 = min over F_primary (bootstrap 매 resample 재최소화; 행 양쪽
censored 면 "displaced beyond band" 보고, 외삽 금지) (c) A1 anchor 방향 통계
(d) slice 간 D_chi 서술적 보고. torch-free.
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
FAM = ("A2-nom", "A2-J+", "A2-R+", "A2-J+R+")


def load():
    recs = []
    for f in sorted((ART / "stage3").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["protocol_hash"] == "eb3a85e702020167"
        recs += s["records"]
    return recs


def main() -> None:
    gate = json.loads((ART / "repo_r1_manifest.json").read_text(encoding="utf-8"))
    assert gate["verdict"] == "PASS", "repo-R1 미통과 — readout 금지 (run_lineage)"
    recs = load()
    etas = (2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9)
    rng = np.random.default_rng(0)
    out = {"protocol_hash": "eb3a85e702020167", "B": B,
           "nominal_surface": {}, "envelope": {}, "anchor": {}, "d_chi": {}}

    # ── (a) nominal chi50(eta, slice) — A2-nom 팔만 ─────────────────────────
    print("(a) nominal chi50 (A2-nom arm only)")
    unlock = {0: True, 2: True}
    for sl in (0, 2):
        rows = {}
        for e in etas:
            sel = [r for r in recs if r["slice"] == sl and r["config"] == "A2-nom"
                   and abs(r["eta"] - e) <= 0.15 + 1e-9]
            chi = np.array([r["chi"] for r in sel])
            y = np.array([int(r["label"] == "NET_CAPTURE") for r in sel], float)
            c50 = chi50_isotonic(chi, y)
            boots = []
            for _ in range(500):
                i = rng.integers(0, len(chi), len(chi))
                boots.append(chi50_isotonic(chi[i], y[i]))
            ok = np.asarray([b for b in boots if not np.isnan(b)])
            ci = [float(np.quantile(ok, .025)), float(np.quantile(ok, .975))] if len(ok) > 20 else None
            cens = bool(np.isnan(c50))
            unlock[sl] &= not cens
            rows[str(e)] = {"n": len(sel), "p": float(y.mean()), "chi50": float(c50),
                            "ci95": ci, "censored": cens,
                            "boot_censored_frac": float(np.isnan(boots).mean())}
            print(f"  sl{sl} eta {e}: n {len(sel)} p {y.mean():.3f} chi50 "
                  f"{c50 if not cens else float('nan'):.3f} "
                  f"{'CENSORED' if cens else '[%.3f,%.3f]' % tuple(ci)}")
        out["nominal_surface"][str(sl)] = rows
    out["surface_unlock"] = {"lam0_all_rows": unlock[0], "lam2_all_rows": unlock[2],
                             "verdict": "UNLOCKED" if unlock[0] and unlock[2] else "NOT_UNLOCKED"}

    # ── (d) D_chi 서술적 ─────────────────────────────────────────────────────
    dchis = {}
    for e in etas:
        a = out["nominal_surface"]["0"][str(e)]
        b = out["nominal_surface"]["2"][str(e)]
        if not a["censored"] and not b["censored"]:
            dchis[str(e)] = round(b["chi50"] - a["chi50"], 4)
    out["d_chi"] = {"per_eta": dchis,
                    "max_abs": max(abs(v) for v in dchis.values()) if dchis else None,
                    "status": "descriptive (slice separation), not an equivalence verdict"}

    # ── (b) 셀-국소 envelope + (c) anchor ───────────────────────────────────
    print("(b/c) cell-local p_worst (min over F_primary, bootstrap re-min) + A1 anchor")
    cells = sorted({(r["slice"], tuple(r["cell"])) for r in recs})
    disp = {0: [], 2: []}
    for sl, cell in cells:
        by = {}
        for r in recs:
            if r["slice"] == sl and tuple(r["cell"]) == cell:
                by.setdefault(r["config"], {})[r["s"]] = int(r["label"] == "NET_CAPTURE")
        ss = sorted(by["A2-nom"])
        M = np.array([[by[f][s] for s in ss] for f in FAM])          # 4 x n
        p_f = M.mean(axis=1)
        idx = rng.integers(0, M.shape[1], (B, M.shape[1]))
        boots = M[:, idx].mean(axis=2).min(axis=0)                   # 재최소화 per resample
        ci = [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))]
        argmin_frac = {FAM[k]: float((M[:, idx].mean(axis=2).argmin(axis=0) == k).mean())
                       for k in range(len(FAM))}
        a1 = np.array([by["A1-anchor"][s] for s in ss])
        nom = M[0]
        key = f"{sl}|{cell[0]},{cell[1]}"
        out["envelope"][key] = {
            "n": len(ss), "p_family": {f: float(p) for f, p in zip(FAM, p_f)},
            "p_worst": float(p_f.min()), "p_worst_ci95": ci,
            "argmin_family_frac": argmin_frac,
            "below_half": bool(p_f.min() < 0.5)}
        out["anchor"][key] = {"p_A1": float(a1.mean()),
                              "anchor_minus_nom": float(a1.mean() - nom.mean())}
        print(f"  sl{sl} {cell}: " +
              " ".join(f"{f.split('-')[1]}:{p:.3f}" for f, p in zip(FAM, p_f)) +
              f"  worst {p_f.min():.3f} [{ci[0]:.3f},{ci[1]:.3f}]  A1 {a1.mean():.3f}")
    # 행별 displaced 판정 (양쪽 셀 모두 p_worst<0.5)
    for sl in (0, 2):
        for e in etas:
            ks = [k for k in out["envelope"] if k.startswith(f"{sl}|") and
                  abs(float(k.split(",")[1]) - e) < 1e-9]
            if ks and all(out["envelope"][k]["below_half"] for k in ks):
                disp[sl].append(e)
    out["envelope_displaced_rows"] = {
        "lam0": disp[0], "lam2": disp[2],
        "meaning": "local envelope displaced beyond the tested nominal boundary band — "
                   "worst-case chi50 NOT estimated (sealed: out of scope)"}

    (ART / "stage3_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nsurface unlock: {out['surface_unlock']['verdict']}")
    print(f"D_chi per eta: {dchis}")
    print(f"displaced rows lam0 {disp[0]}  lam2 {disp[2]}")
    print(f"-> {ART / 'stage3_readout.json'}")


if __name__ == "__main__":
    main()
