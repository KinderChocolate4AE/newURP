"""E2 = AMI 판독 (docs/132, manifest fs1_ami_manifest). 판정 규칙은 manifest 상수만 쓴다.

    python scripts/fs1_ami_readout.py --root artifacts/fs1/ami
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_ami_manifest as M  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = {"det": ("e7b", "net_det"), "sto": ("e7b2", "net_sto")}
IV = ["out0", "in0", "zfix", "lat0"]


def cell(d: pathlib.Path, h: str) -> dict:
    s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
    if s["meta"]["manifest"] != h or s["meta"].get("env_seed") != M.ENV_SEED:
        raise ValueError(f"manifest/env_seed mismatch: {d}")
    r = s["rows"][0]
    eps = [json.loads(x) for x in (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines()]
    if r["n"] != M.N or len(eps) != M.N:
        raise ValueError(f"incomplete: {d}")
    return {"net": r["net"], "defended": r["defended"], "k_first": r["k_first"],
            "fallback": r["fallback"], "pen": r["penetrated"],
            "occ_eps": sum(e.get("n_rob", 0) > 0 for e in eps),
            "rob_ticks": sum(e.get("n_rob", 0) for e in eps),
            "fire_eps": sum(e["n_fire"] > 0 for e in eps)}


def line_verdict(slots: dict) -> dict:
    """slots[(var, seed)][arm] = cell → 게이트 (manifest 상수)."""
    keys = sorted(slots)
    D = {a: np.array([slots[k][a]["net"] - slots[k]["base"]["net"] for k in keys], float)
         for a in M.ARMS if a != "base"}
    med = {a: float(np.median(v)) for a, v in D.items()}
    lift = {a: bool(med[a] >= M.LIFT_MED and int((D[a] > 0).sum()) >= M.LIFT_POS) for a in IV}
    seg = {}
    for S in ("out", "in"):
        if lift[f"{S}0"]:
            rec = float(np.median(D[f"{S}0"] - D[f"shuf_{S}"]))
            seg[S] = {"recovered_gap_med": rec,
                      "label": "ADAPTIVE" if rec >= M.ADAPT_FRAC * med[f"{S}0"] else "ENERGY"}
    if any(v["label"] == "ADAPTIVE" for v in seg.values()):
        branch = "AMI_ADAPTIVE"
    elif any(lift.values()):
        branch = "AMI_ATTACKER_NONADAPTIVE"
    else:
        branch = "AMI_NOT_ATTACKER"
    return {"delta_med": med, "delta_pos": {a: int((v > 0).sum()) for a, v in D.items()},
            "lift": lift, "segments": seg, "branch": branch,
            "dose": {"in_half_med": med["in_half"], "in0_med": med["in0"]}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="artifacts/fs1/ami")
    a = ap.parse_args()
    root, h = pathlib.Path(a.root), M.load()["manifest_hash"]
    out = {"manifest_hash": h, "lines": {}}
    for ln in M.LINES:
        slots = {(v["name"], s): {arm: cell(root / ln / v["name"] / f"s{s}" / arm, h) for arm in M.ARMS}
                 for v in M.B_VARIANTS for s in M.B_SEEDS}
        exp, key = REF[ln]
        ref = json.loads((ROOT / "artifacts" / "fs1" / exp / "readout.json").read_text(encoding="utf-8"))
        ref_med = float(np.median([sd[key] for v in ref["variants"].values() for sd in v["seeds"].values()]))
        base_med = float(np.median([c["base"]["net"] for c in slots.values()]))
        repro_ok = abs(base_med - ref_med) <= M.REPRO_TOL
        res = {"repro": {"base_net_med": base_med, "ref_net_med": ref_med, "ok": repro_ok}}
        res.update(line_verdict(slots) if repro_ok else {"branch": "INVALID_REPRO"})
        res["per_arm_totals"] = {arm: {k: int(sum(c[arm][k] for c in slots.values()))
                                       for k in slots[next(iter(slots))][arm]} for arm in M.ARMS}
        res["slots"] = {f"{k[0]}/s{k[1]}": v for k, v in slots.items()}
        out["lines"][ln] = res
        print(f"[{ln}] repro base {base_med} vs ref {ref_med} -> {res['branch']}")
        if repro_ok:
            for arm in M.ARMS[1:]:
                print(f"  {arm:9s} dmed {res['delta_med'][arm]:+6.1f}  pos {res['delta_pos'][arm]:2d}/15"
                      f"  lift {res['lift'].get(arm, '-')}")
            print("  segments", res["segments"])
    d, s = out["lines"]["det"]["branch"], out["lines"]["sto"]["branch"]
    out["verdict"] = {"judgment_det": d, "replication_sto": s, "agree": d == s,
                      "e6_trigger": d in ("AMI_ADAPTIVE", "AMI_ATTACKER_NONADAPTIVE")}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("verdict", out["verdict"])


if __name__ == "__main__":
    main()
