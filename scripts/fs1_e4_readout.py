"""E4 = ρ-collapse 판독 (docs/133, manifest fs1_e4_manifest). 판정 규칙은 manifest 상수만 쓴다.

    python scripts/fs1_e4_readout.py --dir artifacts/fs1/e4
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_e4_manifest as M  # noqa: E402

SLOTS = ("ex_kfirst50", "ex_fin12_fb", "ex_mix5050", "ex_kfirst_rand")


def verdict(win: dict, rbf_ticks: dict, rb_ticks: dict, n_ticks: int) -> dict:
    """win[name] = 변형 창 (4 slot 중앙값의 중앙값), rbf/rb_ticks[name] = limiter 무/유 robust tick 합."""
    g = {x["name"]: x for x in M.GRID}
    n_base = M.n_inf(g["t1.0_h1.0_cv"])
    res = {}
    for vn, x in g.items():
        pred = max(0.0, 1 - M.rho0(x) / M.rho(x))
        nu = win[vn] / M.n_inf(x)
        res[vn] = {"family": x["family"], "rho": round(M.rho(x), 3), "window": win[vn],
                   "nu": round(nu, 4), "nu_pred": round(pred, 4), "resid": round(nu - pred, 4),
                   "N_pred": round(pred * M.n_inf(x), 3)}
    groups = {}
    for k, names in M.GROUPS.items():
        r = [res[n]["resid"] for n in names]
        spread = (max(r) - min(r)) * n_base
        lo, hi = min(names, key=lambda n: res[n]["resid"]), max(names, key=lambda n: res[n]["resid"])
        groups[k] = {"spread_ticks": round(spread, 3), "collapses": bool(spread <= M.SPREAD_TICKS + 1e-9),
                     "lowest": lo, "highest": hi}
    nc = sum(v["collapses"] for v in groups.values())
    p_a = ("COLLAPSE_SUPPORTED" if nc == len(groups) else
           "COLLAPSE_PARTIAL" if nc >= 3 else "COLLAPSE_NOT_SUPPORTED")
    dirs = {k: bool(win[a] >= win[t]) for k, (a, t) in M.DIRECTION.items()}
    p_b = "SUPPORTED" if sum(dirs.values()) >= 2 else "NOT_SUPPORTED"
    lenient = {n: int(rbf_ticks[n]) for n in M.SUB_RHO0}
    p_c = ("JUDGE_CONSERVATIVE_AT_BOUNDARY" if sum(lenient.values()) == 0 else "JUDGE_LENIENT")
    return {"variants": res, "P-E4a": {"groups": groups, "n_collapse": nc, "verdict": p_a},
            "P-E4b": {"by_rho": dirs, "verdict": p_b},
            "P-E4c": {"limiter_free_robust_ticks": lenient,
                      "share_of_window_ticks": {n: round(v / max(n_ticks, 1), 6) for n, v in lenient.items()},
                      "limiter_present_robust_ticks": {n: int(rb_ticks[n]) for n in M.SUB_RHO0},
                      "verdict": p_c}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/fs1/e4")
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    h = M.load()["manifest_hash"]
    probe = json.loads((d / "probe.json").read_text(encoding="utf-8"))
    k = probe["consts"]
    assert abs(k["tau0"] - M.TAU0) < 1e-12 and abs(k["theta0"] - M.TH0) < 1e-12
    assert abs(k["range_max"] - M.RMAX) < 1e-9 and abs(k["a_att"] - M.A0) < 1e-6 and abs(k["dt"] - M.DT) < 1e-12
    npz = dict(np.load(d / "rows.npz"))
    tick = lambda vn, suf: int(sum(npz[f"{s}.{vn}.{suf}"].astype(bool).sum() for s in SLOTS))
    names = [x["name"] for x in M.GRID]
    n_ticks = int(sum(len(npz[f"{s}.ep"]) for s in SLOTS))
    out = {"manifest_hash": h, **verdict(probe["variant_window_med"], {n: tick(n, "rbf") for n in names},
                                         {n: tick(n, "rb") for n in names}, n_ticks), "n_window_ticks": n_ticks}
    (d / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for vn, v in out["variants"].items():
        print(f"{vn:13s} {v['family']:5s} rho {v['rho']:6.3f} win {v['window']:4.1f} N_pred {v['N_pred']:5.2f} "
              f"resid {v['resid']:+.3f}")
    for key in ("P-E4a", "P-E4b", "P-E4c"):
        print(key, json.dumps(out[key]))


if __name__ == "__main__":
    main()
