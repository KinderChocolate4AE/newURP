"""E7-b 판독 (manifest `fs1_e7_manifest.build_e7b` v1.1): E7_OPENS · P-ρ3 · P-②c — docs/129 §6·§7.1.

    python scripts/fs1_e7b_readout.py --root artifacts/fs1/e7b
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_manifest import (B_CEIL_REF, B_EX_STEPS, B_MARGIN, B_N, B_SEEDS, B_TRAIN_STEPS,  # noqa: E402
                             B_VARIANTS, load_e7b)

P2C_A, P2C_B, FLOOR = "t0.7_h1.0_cv", "t0.5_h1.5_cv", 0.01


def _last_steps(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8").strip().splitlines()[-1])["total_steps"]


def _rank(x):
    x = np.asarray(x, float)
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    i = 0
    while i < len(x):                       # 동점 평균 rank
        j = i
        while j + 1 < len(x) and x[order[j + 1]] == x[order[i]]:
            j += 1
        r[order[i:j + 1]] = 0.5 * (i + j)
        i = j + 1
    return r


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/e7b")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load_e7b()
    thr = B_CEIL_REF + B_MARGIN
    out = {"manifest_hash": m["manifest_hash"], "thr": thr, "variants": {}, "invalid": []}
    for v in B_VARIANTS:
        seeds = {}
        for s in B_SEEDS:
            d = root / v["name"] / f"s{s}"
            try:
                sm = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
                meta = sm["meta"]
                if meta.get("manifest") != m["manifest_hash"]:
                    raise ValueError("manifest")
                if (meta.get("tau_scale"), meta.get("theta_scale"), meta.get("aim")) != \
                        (v["tau_scale"], v["theta_scale"], v["aim"]):
                    raise ValueError("variant flags")
                rows = {(r["defender"], r["group"]): r for r in sm["rows"]}
                det = rows[("learned_det", "ex_judge")]
                if det["n"] != B_N:
                    raise ValueError("completion")
                if _last_steps(d / "log.jsonl") < B_TRAIN_STEPS:
                    raise ValueError("train budget")
                if _last_steps(d / "judge_exploiter" / "log.jsonl") < B_EX_STEPS:
                    raise ValueError("judge budget")
                ref = {k: rows.get((k, "ex_judge"), {}).get("defended")
                       for k in ("learned_sto", "fin12_fb", "kfirst50")}
                seeds[s] = {"ceil_det": det["defended"], "net_det": det["net"],
                            "ceil_sto": ref["learned_sto"], "fin12_fb_ref": ref["fin12_fb"],
                            "kfirst50_ref": ref["kfirst50"], "coop_det": det.get("coop"),
                            "v_fire_med": det.get("v_fire_median"), "pass": det["defended"] >= thr}
            except Exception as e:  # noqa: BLE001 — slot 단위 격리·보고
                out["invalid"].append(f"{v['name']}/s{s}: {e}")
        n_pass = sum(1 for x in seeds.values() if x["pass"])
        out["variants"][v["name"]] = {"rho": v["rho"], "seeds": seeds, "n_pass": n_pass,
                                      "opens": len(seeds) == len(B_SEEDS) and n_pass >= 2,
                                      "ceil_det_med": (float(np.median([x["ceil_det"] for x in seeds.values()]))
                                                       if seeds else None)}
    opened = [k for k, x in out["variants"].items() if x["opens"]]
    out["E7"] = "E7_OPENS" if opened else ("INVALID_E7B" if out["invalid"] and not any(
        x["seeds"] for x in out["variants"].values()) else "E7B_NULL")
    out["opened"] = opened

    ladder = [v["name"] for v in B_VARIANTS if v["aim"] == "cv"]
    med = [out["variants"][k]["ceil_det_med"] for k in ladder]
    if all(x is not None for x in med):
        rs, ms = _rank([out["variants"][k]["rho"] for k in ladder]), _rank(med)
        sp = float(np.corrcoef(rs, ms)[0, 1]) if ms.std() > 0 else None
    else:
        sp = None
    out["P_rho3"] = {"ladder": ladder, "seed_median_ceil_det": med, "spearman": sp,
                     "verdict": (None if sp is None else
                                 "P_RHO3_SUPPORTED" if sp >= 0.7 else "P_RHO3_NOT_SUPPORTED")}

    va, vb = out["variants"][P2C_A]["seeds"], out["variants"][P2C_B]["seeds"]
    common = [s for s in B_SEEDS if s in va and s in vb and va[s]["coop_det"] and vb[s]["coop_det"]]

    def pooled(vs):
        nw = sum(vs[s]["coop_det"]["n_win"] for s in common)
        return sum(vs[s]["coop_det"]["n_C"] for s in common) / nw if nw else 0.0
    ca, cb = pooled(va), pooled(vb)
    wins = sum(1 for s in common if va[s]["coop_det"]["C"] > vb[s]["coop_det"]["C"])
    out["P_2c"] = {"pair": [P2C_A, P2C_B], "pooled_C": [round(ca, 5), round(cb, 5)],
                   "seed_wins": wins, "n_seeds": len(common),
                   "verdict": ("UNDECIDABLE_LOW_SIGNAL" if ca < FLOOR and cb < FLOOR else
                               "P_2C_SUPPORTED" if len(common) == len(B_SEEDS) and wins >= 2
                               else "P_2C_NOT_SUPPORTED")}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("E7", "opened", "P_rho3", "P_2c", "invalid")}, indent=2))


if __name__ == "__main__":
    main()
