"""arm D 판독 (manifest `fs1_armd_manifest.build_armd`): D-i 감사 완화 + D-ii 천장 — docs/128.

    python scripts/fs1_armd_readout.py --root artifacts/fs1/armd
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_armd_manifest import (AUDIT_THR, AUDIT_WINDOW, CELLS, EX_STEPS, MARGIN, N, SEEDS,
                               TRAIN_STEPS, load_armd)  # noqa: E402


def _log_lines(path):
    return [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").strip().splitlines()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/armd")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load_armd()
    out = {"manifest_hash": m["manifest_hash"], "cells": {}, "invalid": []}
    opened, softened = [], []
    for c in CELLS:
        thr = c["ceil_ref"] + MARGIN
        seeds = {}
        for s in SEEDS:
            d = root / c["cell"] / f"s{s}"
            try:
                sm = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
                rows = {(r["defender"], r["group"]): r for r in sm["rows"]}
                sto = rows[("learned_sto", "ex_judge")]
                if sm["meta"].get("manifest") != m["manifest_hash"] or sto["n"] != N:
                    raise ValueError("meta/completion")
                jl = _log_lines(d / "log.jsonl")
                if jl[-1]["total_steps"] < TRAIN_STEPS:
                    raise ValueError("train budget")
                el = _log_lines(d / "judge_exploiter" / "log.jsonl")
                if el[-1]["total_steps"] < EX_STEPS:
                    raise ValueError("judge budget")
                audit = float(np.mean([x["win_rate"] for x in el[-AUDIT_WINDOW:]]))
                seeds[s] = {"ceil_sto": sto["defended"],
                            "ceil_det": rows.get(("learned_det", "ex_judge"), {}).get("defended"),
                            "audit_final": round(audit, 4),
                            "v_fire_med": sto.get("v_fire_median"),
                            "pass_ii": sto["defended"] >= thr,
                            "pass_i": audit <= AUDIT_THR}
            except Exception as e:  # noqa: BLE001 — cell 단위 격리·보고
                out["invalid"].append(f"{c['cell']}/s{s}: {e}")
        n_i = sum(1 for v in seeds.values() if v.get("pass_i"))
        n_ii = sum(1 for v in seeds.values() if v.get("pass_ii"))
        full = len(seeds) == len(SEEDS)
        out["cells"][c["cell"]] = {"thr": thr, "seeds": seeds,
                                   "audit_softened": full and n_i >= 2,
                                   "opens": full and n_ii >= 2}
        if out["cells"][c["cell"]]["opens"]:
            opened.append(c["cell"])
        if out["cells"][c["cell"]]["audit_softened"]:
            softened.append(c["cell"])
    out["decision"] = ("ARMD_OPENS" if opened else "ARMD_AUDIT_ONLY" if softened else
                       "INVALID_ARMD" if out["invalid"] and not (opened or softened) and
                       not any(c["seeds"] for c in out["cells"].values()) else "ARMD_NULL")
    out["opened"], out["audit_softened"] = opened, softened
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
