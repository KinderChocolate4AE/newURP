"""E7-b′ 판독 (manifest `fs1_e7_manifest.build_e7b2`): sto 감사 — docs/129 §8.

    python scripts/fs1_e7b2_readout.py --root artifacts/fs1/e7b2 --det artifacts/fs1/e7b/readout.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_manifest import B_CEIL_REF, B_EX_STEPS, B_MARGIN, B_N, B_SEEDS, B_VARIANTS, load_e7b2  # noqa: E402
from fs1_e7b_readout import _last_steps, _rank  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/e7b2")
    ap.add_argument("--det", default="artifacts/fs1/e7b/readout.json", help="E7-b det 판정 (paired 보고용)")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load_e7b2()
    det_ro = json.loads(pathlib.Path(a.det).read_text(encoding="utf-8"))["variants"]
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
                sto = rows[("learned_sto", "ex_judge_sto")]
                if sto["n"] != B_N:
                    raise ValueError("completion")
                el = [json.loads(x) for x in (d / "judge_exploiter_sto" / "log.jsonl")
                      .read_text(encoding="utf-8").strip().splitlines()]
                if el[-1]["total_steps"] < B_EX_STEPS:
                    raise ValueError("exploiter budget")
                det_e7b = det_ro.get(v["name"], {}).get("seeds", {}).get(str(s), {})
                seeds[s] = {"ceil_sto": sto["defended"], "net_sto": sto["net"],
                            "det_vs_sto_exploiter": rows.get(("learned_det", "ex_judge_sto"), {}).get("defended"),
                            "e7b_ceil_det": det_e7b.get("ceil_det"),
                            "penetration": round(float(np.mean([x["win_rate"] for x in el[-10:]])), 4),
                            "coop_sto": sto.get("coop"), "pass": sto["defended"] >= thr}
            except Exception as e:  # noqa: BLE001
                out["invalid"].append(f"{v['name']}/s{s}: {e}")
        n_pass = sum(1 for x in seeds.values() if x["pass"])
        out["variants"][v["name"]] = {
            "rho": v["rho"], "seeds": seeds, "n_pass": n_pass,
            "opens": len(seeds) == len(B_SEEDS) and n_pass >= 2,
            "ceil_sto_med": float(np.median([x["ceil_sto"] for x in seeds.values()])) if seeds else None}
    opened = [k for k, x in out["variants"].items() if x["opens"]]
    out["E7B2"] = "E7B2_OPENS" if opened else ("INVALID_E7B2" if out["invalid"] and not any(
        x["seeds"] for x in out["variants"].values()) else "E7B2_NULL")
    out["opened"] = opened
    ladder = [v["name"] for v in B_VARIANTS if v["aim"] == "cv"]
    med = [out["variants"][k]["ceil_sto_med"] for k in ladder]
    sp = None
    if all(x is not None for x in med):
        ms = _rank(med)
        sp = float(np.corrcoef(_rank([out["variants"][k]["rho"] for k in ladder]), ms)[0, 1]) if ms.std() > 0 else None
    out["P_rho3s"] = {"ladder": ladder, "seed_median_ceil_sto": med, "spearman": sp,
                      "verdict": None if sp is None else ("P_RHO3S_SUPPORTED" if sp >= 0.7 else "P_RHO3S_NOT_SUPPORTED")}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("E7B2", "opened", "P_rho3s", "invalid")}, indent=2))


if __name__ == "__main__":
    main()
