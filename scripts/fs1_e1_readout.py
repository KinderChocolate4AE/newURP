"""E1 전이 사다리 판독 (docs/134, manifest fs1_e1_manifest). ρ½ 맞춤·갈래 규칙은 manifest 상수만 쓴다.

    python scripts/fs1_e1_readout.py --root artifacts/fs1/e1
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_e1_manifest as M  # noqa: E402


def _logistic(x, L, U, k, m):
    return L + (U - L) / (1.0 + np.exp(-k * (x - m)))


def fit_rho_half(rho, y):
    """y = net/240 (slot 단위), x = log ρ. 4-모수 logistic 최소제곱 → (ρ½, L, U, k) 또는 None (맞춤 실패)."""
    from scipy.optimize import curve_fit
    x, y = np.log(np.asarray(rho, float)), np.asarray(y, float)
    lo, hi = M.FIT_BOUNDS["lower"], M.FIT_BOUNDS["upper"]
    p0 = [max(y.min(), 0.0), min(max(y.max(), 1e-3), 1.0), 5.0, float(np.log(np.median(rho)))]
    p0 = [float(np.clip(v, a + 1e-9, b - 1e-9)) for v, a, b in zip(p0, lo, hi)]
    try:
        p, _ = curve_fit(_logistic, x, y, p0=p0, bounds=(lo, hi), maxfev=20000)
    except RuntimeError:
        return None
    L, U, k, m = (float(v) for v in p)
    return {"rho_half": float(np.exp(m)), "L": L, "U": U, "k": k}


def rho_half_with_ci(points: dict, rng_seed=0):
    """points[ρ] = [seed 별 net/240] → 점추정 + 층화 bootstrap (ρ 점 안에서 seed 재표집) percentile CI."""
    rho = np.concatenate([[r] * len(v) for r, v in points.items()])
    y = np.concatenate([v for v in points.values()])
    full = fit_rho_half(rho, y)
    if full is None or full["U"] - full["L"] < M.MIN_STEP:
        return {"fit": full, "branch": "NO_TRANSITION"}
    rng, bs = np.random.default_rng(rng_seed), []
    for _ in range(M.N_BOOT):
        yy = np.concatenate([rng.choice(v, size=len(v), replace=True) for v in points.values()])
        f = fit_rho_half(rho, yy)
        if f is not None:
            bs.append(f["rho_half"])
    lo, hi = (float(np.percentile(bs, q)) for q in (2.5, 97.5))
    return {"fit": full, "ci95": [lo, hi], "n_boot_ok": len(bs), "branch": branch(lo, hi)}


def branch(lo, hi):
    a, b = M.BAND
    if hi < a:
        return "EARLY"
    if lo >= a and hi <= b:
        return "AT_BOUNDARY"
    if lo > b:
        return "LATE"
    return "UNDETERMINED"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="artifacts/fs1/e1")
    a = ap.parse_args()
    root, h = pathlib.Path(a.root), M.load()["manifest_hash"]
    out = {"manifest_hash": h}
    cells = {}
    for p in M.LADDER + M.PAIR:
        for s, sub in ((s, sub) for s in M.SEEDS for sub in ("eval_judge", "eval_judge_sto")):
            d = root / p["name"] / f"s{s}" / sub
            if not (d / "summary.json").exists():
                continue
            sm = json.loads((d / "summary.json").read_text(encoding="utf-8"))
            if sm["meta"]["manifest"] != h:
                raise ValueError(f"manifest mismatch {d}")
            eps = [json.loads(x) for x in (d / "episodes.jsonl").read_text(encoding="utf-8").splitlines()]
            for dn in ("learned_det", "learned_sto"):
                for g in {r["group"] for r in sm["rows"]}:
                    E = [e for e in eps if e["defender"] == dn and e["group"] == g]
                    if not E:
                        continue
                    cells[(p["name"], s, dn, g)] = {
                        "net": sum(e["label"] in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT") for e in E),
                        "rob_fire": sum(bool(e.get("rob_fire")) for e in E),
                        "rob_fire_pen": sum(bool(e.get("rob_fire")) and e["label"] == "PENETRATED" for e in E),
                        "n": len(E)}
    rho = {p["name"]: p["rho"] for p in M.LADDER + M.PAIR}
    J = M.JUDGMENT
    for key, metric in (("primary_net", "net"), ("secondary_rob_fire", "rob_fire")):
        pts = {}
        for p in M.LADDER:
            v = [cells[(p["name"], s, J["defender"], J["group"])][metric] / M.N for s in M.SEEDS
                 if (p["name"], s, J["defender"], J["group"]) in cells]
            if len(v) == len(M.SEEDS):
                pts[rho[p["name"]]] = np.array(v)
        out[key] = (rho_half_with_ci(pts) if len(pts) == len(M.LADDER) else {"branch": "INCOMPLETE"})
    b1, b2 = out["primary_net"]["branch"], out["secondary_rob_fire"]["branch"]
    out["verdict"] = {"branch": b1, "secondary": b2,
                      "discretization_sensitive": bool(b1 != b2 and "INCOMPLETE" not in (b1, b2))}
    pr = [cells.get((p["name"], s, J["defender"], J["group"]), {}).get("net") for p in M.PAIR for s in M.SEEDS]
    out["pair"] = {p["name"]: [cells.get((p["name"], s, J["defender"], J["group"]), {}).get("net") for s in M.SEEDS]
                   for p in M.PAIR} if any(x is not None for x in pr) else None
    out["cells"] = {"/".join(map(str, k)): v for k, v in cells.items()}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("primary_net", "secondary_rob_fire", "verdict", "pair")}, indent=1))


if __name__ == "__main__":
    main()
