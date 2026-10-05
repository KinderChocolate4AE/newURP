"""E3 stage 1 판독 (manifest v1.2 `scripts/fs1_e3_manifest.py`): ceiling 집계 + band 선정 + 진단.

    python scripts/fs1_e3_stage1_readout.py --root artifacts/fs1/e3/stage1

cell 디렉터리 구조 (run_fs1_e3_stage1_eval.sh 산출):
  <root>/<cell>/eval/summary.json        (kfirst50·fin12_fb × {ladder, ex_kfirst50, ex_fin12_fb}, 240)
  <root>/<cell>/diag/summary.json        (c5_fb·fwd_fb × ladder, 96)
  <root>/<cell>/exploit_<def>/log.jsonl  (JAX 학습 로그 사본 — budget 검증)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e3_manifest import BAND, EX_STEPS, GRID_MU, GRID_NU, N, load, select_cells  # noqa: E402


def _rows(p):
    s = json.loads(p.read_text(encoding="utf-8"))
    return s["meta"], {(r["defender"], r["group"]): r for r in s["rows"]}


def read_cell(d: pathlib.Path, mu: float, nu: float) -> dict:
    out = {"cell": d.name, "mu": mu, "nu": nu, "invalid": []}
    try:
        meta, cell = _rows(d / "eval" / "summary.json")
    except FileNotFoundError:
        out["invalid"].append("missing eval")
        return out
    if abs(meta.get("mu", -1) - mu) > 1e-9 or abs(meta.get("nu", -1) - nu) > 1e-9:
        out["invalid"].append("mu/nu mismatch")
    if meta.get("manifest") != load()["manifest_hash"]:
        out["invalid"].append("manifest")
    pairs = {"kfirst50": "ex_kfirst50", "fin12_fb": "ex_fin12_fb"}
    for dfd, ex in pairs.items():
        r = cell.get((dfd, ex))
        if r is None or r["n"] != N:
            out["invalid"].append(f"completion {dfd}x{ex}")
            continue
        out[f"ceiling_{dfd}"] = r["defended"]
        log = d / f"exploit_{dfd}" / "log.jsonl"
        try:
            last = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
            if last["total_steps"] < EX_STEPS:
                out["invalid"].append(f"budget {dfd}")
        except (FileNotFoundError, IndexError):
            out["invalid"].append(f"log {dfd}")
    if not out["invalid"]:
        out["ceiling_s"] = max(out["ceiling_kfirst50"], out["ceiling_fin12_fb"])
        out["ladder"] = {x: cell[(x, "ladder")]["defended"] for x in pairs if (x, "ladder") in cell}
        out["cross_ex"] = {f"{x}_vs_{e}": cell[(x, e)]["defended"]
                           for x in pairs for e in pairs.values() if (x, e) in cell and pairs[x] != e}
    try:
        _, diag = _rows(d / "diag" / "summary.json")
        out["diag_ladder"] = {x: diag[(x, "ladder")]["defended"] for x in ("c5_fb", "fwd_fb")
                              if (x, "ladder") in diag}
    except FileNotFoundError:
        out["diag_ladder"] = None                 # 보고 전용 — invalid 아님
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/e3/stage1")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    m = load()
    cells = [read_cell(root / c["cell"], c["mu"], c["nu"]) for c in m["grid"]["cells"]]
    ok = [c for c in cells if not c["invalid"]]
    ceil = {c["cell"]: c["ceiling_s"] for c in ok}
    sel = select_cells(ceil)
    # Fig 5 heatmap (ceiling_s / N, 행 = mu, 열 = nu)
    lines = ["| mu \\ nu | " + " | ".join(f"{n:g}" for n in GRID_NU) + " |",
             "|---" * (len(GRID_NU) + 1) + "|"]
    for mu in GRID_MU:
        row = [f"| {mu:g} "]
        for nu in GRID_NU:
            c = next((x for x in cells if x["mu"] == mu and x["nu"] == nu), None)
            v = (f"{c['ceiling_s'] / N:.0%}" + ("*" if c["cell"] in sel else "")
                 if c and not c["invalid"] else "INV")
            row.append(f"| {v} ")
        lines.append("".join(row) + "|")
    mono = all(a_ <= b_ + 12 for col in range(len(GRID_NU))
               for a_, b_ in zip([ceil.get(f"m{m_:g}_n{GRID_NU[col]:g}", 0) for m_ in GRID_MU][:-1],
                                 [ceil.get(f"m{m_:g}_n{GRID_NU[col]:g}", 0) for m_ in GRID_MU][1:])) \
        if len(ok) == len(cells) else None
    out = {"manifest_hash": m["manifest_hash"], "cells": cells, "selected": sel,
           "decision": ("E3_BAND_EMPTY" if ok and not sel else
                        "E3_BOUNDARY_MAPPED" if len(ok) == len(cells) else "PARTIAL/INVALID cells present"),
           "prediction_mu_monotone_within_noise": mono,
           "heatmap_markdown": "\n".join(lines)}
    (root / "stage1_readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(json.dumps({k: v for k, v in out.items() if k not in ("cells", "heatmap_markdown")}, indent=2))


if __name__ == "__main__":
    main()
