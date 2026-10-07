"""E3b phase 2 판독 (manifest `fs1_e3b_manifest.build_p2`): LEARNING_OPENS 게이트.

    python scripts/fs1_e3b_p2_readout.py --root artifacts/fs1/e3b/phase2
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e3b_manifest import P2_CELLS, P2_SEEDS, P2_TRAIN_STEPS, load_p2  # noqa: E402

MARGIN, N, EX_STEPS = 24, 240, 1e7


def _steps(log):
    return json.loads(pathlib.Path(log).read_text(encoding="utf-8").strip().splitlines()[-1])["total_steps"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/e3b/phase2")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load_p2()
    out = {"manifest_hash": m["manifest_hash"], "cells": {}, "invalid": []}
    opened = []
    for c in P2_CELLS:
        thr = c["ceil_ref"] + MARGIN
        cell_out = {}
        for arm in ("armA", "armB"):
            seeds = {}
            for s in P2_SEEDS:
                d = root / c["cell"] / arm / f"s{s}"
                try:
                    sm = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
                    rows = {(r["defender"], r["group"]): r for r in sm["rows"]}
                    det = rows[("learned_det", "ex_judge")]
                    if sm["meta"].get("manifest") != m["manifest_hash"] or det["n"] != N:
                        raise ValueError("meta/completion")
                    if _steps(d / "log.jsonl") < P2_TRAIN_STEPS:
                        raise ValueError("train budget")
                    if _steps(d / "judge_exploiter" / "log.jsonl") < EX_STEPS:
                        raise ValueError("judge budget")
                    seeds[s] = {"ceil_det": det["defended"],
                                "ceil_sto": rows.get(("learned_sto", "ex_judge"), {}).get("defended"),
                                "v_fire_med": det.get("v_fire_median"),
                                "pass": det["defended"] >= thr}
                except Exception as e:  # noqa: BLE001 — cell 단위 격리·보고
                    out["invalid"].append(f"{c['cell']}/{arm}/s{s}: {e}")
            n_pass = sum(1 for v in seeds.values() if v.get("pass"))
            cell_out[arm] = {"thr": thr, "seeds": seeds, "n_pass": n_pass,
                             "opens": len(seeds) == len(P2_SEEDS) and n_pass >= 2}
            if cell_out[arm]["opens"]:
                opened.append(f"{c['cell']}/{arm}")
        if {"armA", "armB"} <= set(cell_out):
            ok = all(len(cell_out[x]["seeds"]) == len(P2_SEEDS) for x in ("armA", "armB"))
            cell_out["B_minus_A_det"] = ([cell_out["armB"]["seeds"][s]["ceil_det"]
                                          - cell_out["armA"]["seeds"][s]["ceil_det"]
                                          for s in P2_SEEDS] if ok else None)   # 목적함수 변경 효과 (보고)
        out["cells"][c["cell"]] = cell_out
    out["decision"] = ("E3B2_LEARNING_OPENS" if opened else
                       "INVALID_E3B2" if out["invalid"] and not opened else "E3B2_NULL")
    out["opened"] = opened
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
