"""E3b phase 1 판독 (manifest `scripts/fs1_e3b_manifest.py`): Q-A / Q-B 게이트.

    python scripts/fs1_e3b_readout.py --root artifacts/fs1/e3b/phase1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e3b_manifest import CELLS, EX_STEPS, MARGIN, N, load  # noqa: E402

STAGE1 = pathlib.Path("artifacts/fs1/e3/stage1/stage1_readout.json")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/e3b/phase1")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load()
    s1 = {c["cell"]: c for c in json.loads(STAGE1.read_text(encoding="utf-8"))["cells"]}
    out = {"manifest_hash": m["manifest_hash"], "cells": [], "invalid": []}
    for c in CELLS:
        d = root / c["cell"]
        try:
            s = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            out["invalid"].append(f"missing {c['cell']}")
            continue
        meta = s["meta"]
        if meta.get("manifest") != m["manifest_hash"] or abs(meta.get("mu", -1) - c["mu"]) > 1e-9:
            out["invalid"].append(f"meta {c['cell']}")
        cell = {(r["defender"], r["group"]): r for r in s["rows"]}
        rec = {"cell": c["cell"], "mu": c["mu"], "P_stage1": s1[c["cell"]]["ceiling_s"]}
        for fam, dfd in (("M1", "mix5050"), ("M2", "kfirst_rand")):
            r = cell.get((dfd, f"ex_{dfd}"))
            if r is None or r["n"] != N:
                out["invalid"].append(f"completion {c['cell']} {dfd}")
                continue
            rec[f"ceil_{fam}"] = r["defended"]
            log = d / f"exploit_{dfd}" / "log.jsonl"
            try:
                if json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])["total_steps"] < EX_STEPS:
                    out["invalid"].append(f"budget {c['cell']} {dfd}")
            except (FileNotFoundError, IndexError):
                out["invalid"].append(f"log {c['cell']} {dfd}")
        if "ceil_M1" in rec and "ceil_M2" in rec:
            rec["ceil_M"] = max(rec["ceil_M1"], rec["ceil_M2"])
            rec["QA_open"] = rec["ceil_M"] - rec["P_stage1"] >= MARGIN
            rec["cross"] = {f"{dfd}|{g}": r["defended"] for (dfd, g), r in cell.items()
                            if g.startswith("ex_") and g != f"ex_{dfd}"}
        out["cells"].append(rec)
    ok = [c for c in out["cells"] if "ceil_M" in c]
    if not out["invalid"] and len(ok) == len(CELLS):
        qa = {c["cell"]: bool(c["QA_open"]) for c in ok}
        by = {c["cell"]: c for c in ok}
        qb = {fam: by["m1.4_n1"][f"ceil_{fam}"] - by["m0.35_n1"][f"ceil_{fam}"] >= MARGIN
              for fam in ("M1", "M2")}
        out["QA"] = qa
        out["QB_mu_reopens"] = qb
        out["decision"] = ("E3B1_UNPREDICTABILITY_OPENS" if any(qa.values()) else
                           "E3B1_FLOOR_EVERYWHERE")
    else:
        out["decision"] = "INVALID_E3B1"
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
