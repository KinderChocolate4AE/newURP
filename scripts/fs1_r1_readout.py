"""R1 착취자 예산 민감도 판독 (docs/138, manifest fs1_r1_manifest).

    python scripts/fs1_r1_readout.py --root artifacts/fs1/r1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_r1_manifest as M  # noqa: E402


def row(root, sl, ex, h):
    d = root / sl["variant"] / f"s{sl['seed']}" / f"eval_{ex}"
    sm = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    if sm["meta"]["manifest"] != h:
        raise ValueError(f"manifest mismatch {d}")
    return {r["defender"]: {"defended": r["defended"], "net": r["net"]} for r in sm["rows"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="artifacts/fs1/r1")
    root = pathlib.Path(ap.parse_args().root)
    h = M.load()["manifest_hash"]
    slots = {}
    for sl in M.build()["slots"]:
        k = f"{sl['variant']}/s{sl['seed']}"
        slots[k] = {ex: row(root, sl, ex, h) for ex in ("b1", "b3", "orig", "b3_at1e7", "b3_at2e7")}
    det = lambda ex: [v[ex]["learned_det"]["defended"] for v in slots.values()]
    d = [a - b for a, b in zip(det("b1"), det("b3"))]
    out = {"manifest_hash": h, "d_b1_minus_b3": d, "label": M.budget_label(d),
           "median": {ex: float(np.median(det(ex))) for ex in ("b1", "b3", "orig", "b3_at1e7", "b3_at2e7")},
           "report_within_seed_budget_b3at1e7_minus_b3": [a - b for a, b in zip(det("b3_at1e7"), det("b3"))],
           "report_still_falling_b3at2e7_minus_b3": [a - b for a, b in zip(det("b3_at2e7"), det("b3"))],
           "report_exploiter_seed_scatter_b1_minus_b3at1e7": [a - b for a, b in zip(det("b1"), det("b3_at1e7"))],
           "seed_repro_abs_b1_vs_orig": [abs(a - b) for a, b in zip(det("b1"), det("orig"))], "slots": slots}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "slots"}, indent=1))


if __name__ == "__main__":
    main()
