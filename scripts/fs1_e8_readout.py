"""E8 고정 χ 공격자 가속 스윕 판독 (docs/139, manifest fs1_e8_manifest).

    python scripts/fs1_e8_readout.py --root artifacts/fs1/e8
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_e8_manifest as M  # noqa: E402

NET = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")


def slope_ci(per_point, la, rng_seed=0):
    """per_point[i] = seed 별 net 배열, la[i] = ln(a_scale). OLS 기울기 + 층화 bootstrap percentile 95%."""
    def beta(vals):
        x = np.concatenate([[l] * len(v) for l, v in zip(la, vals)]); y = np.concatenate(vals)
        return float(np.polyfit(x, y, 1)[0])
    rng = np.random.default_rng(rng_seed)
    bs = [beta([rng.choice(v, len(v)) for v in per_point]) for _ in range(M.N_BOOT)]
    return beta(per_point), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="artifacts/fs1/e8")
    root = pathlib.Path(ap.parse_args().root)
    h = M.load()["manifest_hash"]
    cells = {}
    for p in M.POINTS:
        for s in M.SEEDS:
            d = root / p["name"] / f"s{s}" / "eval_judge"
            sm = json.loads((d / "summary.json").read_text(encoding="utf-8"))
            if sm["meta"]["manifest"] != h:
                raise ValueError(f"manifest mismatch {d}")
            for x in (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
                e = json.loads(x)
                c = cells.setdefault(f"{p['name']}/{s}/{e['defender']}/{e['group']}", {"net": 0, "rob_fire": 0, "n": 0})
                c["n"] += 1; c["net"] += e["label"] in NET; c["rob_fire"] += bool(e.get("rob_fire"))
    per = [np.array([cells[f"{p['name']}/{s}/learned_det/ex_judge"]["net"] for s in M.SEEDS], float) for p in M.POINTS]
    la = [float(np.log(p["a_scale"])) for p in M.POINTS]
    b, lo, hi = slope_ci(per, la)
    out = {"manifest_hash": h, "beta": b, "ci95": [lo, hi], "label": M.slope_label(lo, hi),
           "median_net": {p["name"]: float(np.median(v)) for p, v in zip(M.POINTS, per)}, "cells": cells}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "cells"}, indent=1))


if __name__ == "__main__":
    main()
