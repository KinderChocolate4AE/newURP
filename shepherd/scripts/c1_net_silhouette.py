"""C-1 G0/G1: grounded net DIRECTIONAL silhouette support vs corridor boxers
(docs/09 (aaaa); external review §8). Replaces the ad-hoc "2 m tube" of the
friendly-fire diagnostic with the ACTUAL deployed-net lateral reach from the
N1-grounded flexible-net model (prototypes/net_forward.py, Xu Drones 9:190).

For the deployed net snapshot (engage_dist) it computes the lateral support
perpendicular to the launch axis, by 30-deg azimuth sector (isotropy check),
and reports the effective radius vs travel distance (TEMPORAL = N1-flagged,
indicative only -- flat-init OVER-states early S_NP per docs/n1_net_grounding
D-notes). Then compares to the seed-1100 boxer off-axis distances.

Grounded facts used: net launched at the paper baseline (theta 45, v 60,
m 35 g); net_radius(equiv-area) ~ 2.0 m at engage; directional max reach and
travel profile are the new outputs. torch-free.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

sys.path.insert(0, "prototypes")
import net_forward as NF          # noqa: E402


def analyze(boxer_axial_offaxis, theta=45, v0=60, m_g=35):
    r = NF.simulate(theta_deg=theta, v0=v0, m_block=m_g / 1000.0)
    X = np.asarray(r["X_snapshot"], float)
    nhat = np.asarray(r["n_hat"], float); nhat = nhat / np.linalg.norm(nhat)
    c = X.mean(0)
    rel = X - c
    axial = rel @ nhat
    perp_vec = rel - np.outer(axial, nhat)
    perp = np.linalg.norm(perp_vec, axis=1)
    # azimuth sectors (isotropy)
    e = np.array([1., 0, 0]); u2 = e - (e @ nhat) * nhat
    if np.linalg.norm(u2) < 1e-6:
        u2 = np.array([0, 1., 0]) - (np.array([0, 1., 0]) @ nhat) * nhat
    u2 /= np.linalg.norm(u2); u3 = np.cross(nhat, u2)
    az = np.arctan2(perp_vec @ u3, perp_vec @ u2)
    sectors = {}
    for k in range(6):
        lo, hi = -np.pi + k * np.pi / 3, -np.pi + (k + 1) * np.pi / 3
        m = (az >= lo) & (az < hi)
        if m.any():
            sectors[f"{int(np.degrees(lo))}:{int(np.degrees(hi))}"] = float(perp[m].max())
    # temporal profile (FLAGGED)
    cum = np.asarray(r["cum_travel"]); snp = np.asarray(r["S_NP"])
    Req = np.sqrt(snp / np.pi)
    prof = {str(t): float(np.interp(t, cum, Req)) for t in (3, 5, 7, 10, 15, 20)
            if cum[-1] >= t}
    out = {"operating_point": r["operating_point"],
           "net_radius_equiv_engage": float(r["net_radius"]),
           "lateral_support": {"max": float(perp.max()),
                               "p95": float(np.quantile(perp, 0.95)),
                               "p50": float(np.median(perp)),
                               "mean": float(perp.mean())},
           "directional_sectors_max": sectors,
           "isotropy_note": "sectors ~2.09-2.24 -> near-isotropic, no thin escape dir",
           "Req_vs_travel_FLAGGED": prof,
           "temporal_caveat": "early S_NP over-stated by flat-init (n1 D-notes); "
                              "engage(20m) snapshot is the anchored value",
           "boxers": {}}
    Rmin = min(prof.values()) if prof else float(r["net_radius"])
    Rmax = float(perp.max())
    for name, d in boxer_axial_offaxis.items():
        out["boxers"][name] = {
            "off_axis_m": d,
            "inside_at_Rmin_grounded": bool(d < Rmin),   # smallest grounded reach
            "inside_at_Rmax_directional": bool(d < Rmax),
            "verdict": ("INSIDE" if d < Rmin else "borderline" if d < Rmax
                        else "clear")}
    n_inside_min = sum(1 for b in out["boxers"].values() if b["inside_at_Rmin_grounded"])
    n_inside_max = sum(1 for b in out["boxers"].values() if b["inside_at_Rmax_directional"])
    out["case"] = ("C_unsafe" if n_inside_max == len(boxer_axial_offaxis)
                   else "B_borderline" if n_inside_max else "A_clear")
    out["summary"] = (f"{n_inside_min}/{len(boxer_axial_offaxis)} boxers inside at "
                      f"Rmin={Rmin:.2f}m; {n_inside_max}/{len(boxer_axial_offaxis)} "
                      f"inside directional Rmax={Rmax:.2f}m -> {out['case']}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_net_silhouette.json")
    a = ap.parse_args()
    # seed 1100 boxer off-axis distances (from c1_friendly_fire dist_to_axis)
    boxers = {"L0": 1.82, "L1": 2.11, "L2": 1.94, "L3": 2.16}
    res = analyze(boxers)
    import pathlib
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    ls = res["lateral_support"]
    print(f"deployed net lateral support: max={ls['max']:.2f} p95={ls['p95']:.2f} "
          f"p50={ls['p50']:.2f} (equiv-area R={res['net_radius_equiv_engage']:.2f})")
    print(f"directional (near-isotropic): {res['isotropy_note']}")
    print(f"Req vs travel (FLAGGED): {res['Req_vs_travel_FLAGGED']}")
    for name, b in res["boxers"].items():
        print(f"  {name}: off-axis {b['off_axis_m']:.2f}m -> {b['verdict']}")
    print(f"VERDICT: {res['summary']}")


if __name__ == "__main__":
    main()
