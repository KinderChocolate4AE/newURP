"""R0 평가 반복성 판독 (docs/135, manifest fs1_r0_manifest).

    python scripts/fs1_r0_readout.py --root artifacts/fs1/r0
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_r0_manifest as M  # noqa: E402

GROUP = {"det": "ex_judge", "sto": "ex_judge_sto"}


def ratio_lower(mis, mat, rng):
    mis, mat = np.asarray(mis, float), np.asarray(mat, float)
    bs = [rng.choice(mis, len(mis)).mean() / max(rng.choice(mat, len(mat)).mean(), 1e-9) for _ in range(M.N_BOOT)]
    return float(mis.mean() / max(mat.mean(), 1e-9)), float(np.percentile(bs, 2.5))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="artifacts/fs1/r0")
    root = pathlib.Path(ap.parse_args().root)
    h = M.load()["manifest_hash"]
    out, lbs, rng = {"manifest_hash": h, "slots": {}}, [], np.random.default_rng(0)
    for sl in M.SLOTS:
        key = f"{sl['variant']}/s{sl['seed']}"
        vals = {}                                                    # (방어, 착취자) → env seed 별 방어 성공 수
        for ex in M.EXPLOITERS:
            for k in M.ENV_SEEDS:
                d = root / key / f"env{k}" / f"eval_{ex}"
                sm = json.loads((d / "summary.json").read_text(encoding="utf-8"))
                if sm["meta"]["manifest"] != h:
                    raise ValueError(f"manifest mismatch {d}")
                for r in sm["rows"]:                                 # 천장 = eval.summarize 의 defended (E7-b 와 같은 정의)
                    if r["group"] == GROUP[ex] and r["defender"] in ("learned_det", "learned_sto"):
                        vals.setdefault((r["defender"][8:], ex), [0] * len(M.ENV_SEEDS))[k] = r["defended"]
        cells = {}
        for (dn, ex), v in vals.items():
            sd, mean = float(np.std(v, ddof=1)), float(np.mean(v))
            cells[f"{dn}|{ex}"] = {"type": M.CELLS[(dn, ex)], "per_env_seed": v, "mean": mean, "sd": sd,
                                   "binomial_sd": float((M.N * (mean / M.N) * (1 - mean / M.N)) ** 0.5),
                                   "label": M.dispersion_label(sd, mean)}
        ratios = {}
        for dn, mat_ex, mis_ex in (("det", "det", "sto"), ("sto", "sto", "det")):
            r, lb = ratio_lower(vals[(dn, mis_ex)], vals[(dn, mat_ex)], rng)
            ratios[dn] = {"ratio": r, "lower95": lb}
            lbs.append(lb)
        out["slots"][key] = {"cells": cells, "ratios": ratios}
    out["inflation"] = M.inflation_label(lbs)
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
