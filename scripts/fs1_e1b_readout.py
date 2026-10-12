"""E1b 전이 구간 조밀화 판독 (docs/137, manifest fs1_e1b_manifest). 규칙은 manifest 함수·상수만 쓴다.

    python scripts/fs1_e1b_readout.py --root artifacts/fs1/e1b
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_e1b_manifest as M  # noqa: E402


def judge(per_point, rng_seed=0):
    """per_point = 5 개 (ρ 오름차순) seed 값 배열 → {point, share, final}."""
    meds = [float(np.median(v)) for v in per_point]
    point = M.onset_label(meds)
    if point == "NO_STEP":
        return {"medians": meds, "point": point, "final": point}
    rng, hits = np.random.default_rng(rng_seed), 0
    for _ in range(M.N_BOOT):
        hits += M.onset_label([float(np.median(rng.choice(v, len(v)))) for v in per_point]) == point
    share = hits / M.N_BOOT
    return {"medians": meds, "point": point, "share": share, "final": point if share >= M.SHARE else "UNRESOLVED"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="artifacts/fs1/e1b")
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
                c = cells.setdefault((p["name"], s, e["defender"], e["group"]), {"net": 0, "rob_fire": 0, "n": 0})
                c["n"] += 1
                c["net"] += e["label"] in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
                c["rob_fire"] += bool(e.get("rob_fire"))
    J = M.JUDGMENT
    get = lambda name, key: np.array([cells[(name, s, J["defender"], J["group"])][key] for s in M.SEEDS], float)
    out = {"manifest_hash": h}
    for key in ("net", "rob_fire"):
        out[key] = judge([get(p["name"], key) for p in M.POINTS])
    out["verdict"] = {"label": out["net"]["final"],
                      "conversion_sensitive": out["net"]["final"] != out["rob_fire"]["final"]}
    f, pp = out["net"]["medians"][0], out["net"]["medians"][-1]
    out["shape_normalized"] = [None if pp == f else (m - f) / (pp - f) for m in out["net"]["medians"]]
    out["conversion"] = {p["name"]: float(get(p["name"], "net").sum() / max(get(p["name"], "rob_fire").sum(), 1))
                         for p in M.POINTS}
    out["cells"] = {"/".join(map(str, k)): v for k, v in cells.items()}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "cells"}, indent=1))


if __name__ == "__main__":
    main()
