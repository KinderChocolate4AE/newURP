"""arm C-1 판독 (manifest `fs1_armc1_manifest.build_armc1`): ARMC1_OPENS 게이트 — docs/127.

    python scripts/fs1_armc1_readout.py --root artifacts/fs1/armc1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_armc1_manifest import CELLS, SEEDS, MARGIN, N, TRAIN_STEPS, EX_STEPS, load_armc1  # noqa: E402


def _steps(log):
    return json.loads(pathlib.Path(log).read_text(encoding="utf-8").strip().splitlines()[-1])["total_steps"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/armc1")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load_armc1()
    out = {"manifest_hash": m["manifest_hash"], "cells": {}, "invalid": []}
    opened = []
    for c in CELLS:
        thr = c["ceil_ref"] + MARGIN
        seeds = {}
        for s in SEEDS:
            d = root / c["cell"] / f"s{s}"
            try:
                sm = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
                rows = {(r["defender"], r["group"]): r for r in sm["rows"]}
                det = rows[("learned_det", "ex_judge")]
                if sm["meta"].get("manifest") != m["manifest_hash"] or det["n"] != N:
                    raise ValueError("meta/completion")
                if _steps(d / "log.jsonl") < TRAIN_STEPS:
                    raise ValueError("train budget")
                if _steps(d / "judge_exploiter" / "log.jsonl") < EX_STEPS:
                    raise ValueError("judge budget")
                seeds[s] = {"ceil_det": det["defended"],
                            "ceil_sto": rows.get(("learned_sto", "ex_judge"), {}).get("defended"),
                            "v_fire_med": det.get("v_fire_median"),
                            "pass": det["defended"] >= thr}
            except Exception as e:  # noqa: BLE001 — cell 단위 격리·보고
                out["invalid"].append(f"{c['cell']}/s{s}: {e}")
        n_pass = sum(1 for v in seeds.values() if v.get("pass"))
        out["cells"][c["cell"]] = {"thr": thr, "seeds": seeds, "n_pass": n_pass,
                                   "opens": len(seeds) == len(SEEDS) and n_pass >= 2}
        if out["cells"][c["cell"]]["opens"]:
            opened.append(c["cell"])
    out["decision"] = ("ARMC1_OPENS" if opened else
                       "INVALID_ARMC1" if out["invalid"] and not opened else "ARMC1_NULL")
    out["opened"] = opened
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
