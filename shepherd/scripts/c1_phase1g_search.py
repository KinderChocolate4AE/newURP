"""C-1 Phase 1G search — T*_dyn, the lead time at which the plant witness survives
the E1.5 actual-trajectory judge.

Phase 1F's T*_plant was certified only by the STATIC snapshot judge.  Phase 1G
falsified the max-min-clearance witnesses outright, and showed that even the
displacement-constrained (`hold`) witnesses fail at some cells: an LP deviation of
5 cm inside the deploy window already drops actual v_soft from ~0.98 to ~0.64.

So the honest bound is not "smallest T where the LP is feasible" but

    T*_dyn(rho0) = smallest T at which the hold-LP witness, played closed-loop,
                   is tier 4 AND certifies under the `actual` model.

This sweeps T upward per rho0, picks the fire step with the smallest LP deviation
d*, and judges.  Search runs at a reduced sample count; the winners are re-certified
at n=20,000 x 3 seeds by c1_phase1g.py.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, THETA, R_BODY, M_SAFETY,
                                                PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import judge_models, clearance_dense, displacement_sup, make_labels
from shepherd.scripts.c1_plant_bound import solve_witness_hold, make_lp_arm, DT, N_DEP


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rho0", default="2.8,3.2,4.0,5.0")
    ap.add_argument("--tlead", default="0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75,0.80")
    ap.add_argument("--n-cert", type=int, default=2000)
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1g_search.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    out = {"meta": {"phase": "1G_search_T_dyn", "n_cert": a.n_cert, "theta": pe.theta,
                    "criterion": "tier 4 AND actual-model point estimate >= theta",
                    "lp": "solve_witness_hold (displacement-constrained)"},
           "cells": [], "T_star_dyn": {}}
    for rho0 in [float(x) for x in a.rho0.split(",")]:
        star = None
        for tl in [float(x) for x in a.tlead.split(",")]:
            fmax = int(round(tl / DT))
            cands = []
            for f in range(max(1, fmax - 2), fmax + 1):
                seq, d, m = solve_witness_hold(rho0, f)
                if seq is not None:
                    cands.append((d, f, seq, m))
            if not cands:
                print("  rho0=%.2f T=%.2f : LP infeasible (all f)" % (rho0, tl), flush=True)
                out["cells"].append({"rho0": rho0, "T": tl, "lp": "INFEASIBLE"})
                continue
            # evaluate EVERY feasible fire step, not just the smallest-deviation one:
            # d* alone does not predict the outcome (a small-d* witness can fire too
            # late and be penetrated), so the cell is only rejected when all f fail.
            cands.sort(key=lambda z: z[0])
            cell_ok = False
            for d, f, seq, m in cands:
                w = log_ctrl(make_lp_arm(seq))
                spawn = make_spawn(rho0, tl * V_CLOSE)
                rec = rollout_unified(pe, spawn, w, fin, r_lane=RL, r_body=RB)
                jm = judge_models(pe, rec, n_cert=a.n_cert)
                clr = clearance_dense(pe, rec, r_lane=RL, r_body=RB)
                disp = displacement_sup(pe, rec)
                labs = make_labels(rec, jm, clr, disp)
                ok = bool(rec["tier"] >= 4 and jm["actual"]["certifies_point"])
                out["cells"].append({"rho0": rho0, "T": tl, "f": f, "lp_d": round(d, 4),
                                     "lp_min_clr": round(m, 4), "tier": rec["tier"],
                                     "sup_disp": disp["sup_disp"],
                                     "v_soft_static": jm["static"]["v_soft"],
                                     "v_soft_actual": jm["actual"]["v_soft"],
                                     "lcb_actual": jm["actual"]["v_soft_lcb"],
                                     "n_feas_actual": jm["actual"]["n_feasible"],
                                     "dynamic_ok": ok, "labels": labs})
                print("  rho0=%.2f T=%.2f f=%2d d*=%.3f | tier %d disp %.3f | v_soft st %.3f act %.3f "
                      "(LCB %.3f, n_feas %d) -> %s" % (
                      rho0, tl, f, d, rec["tier"], disp["sup_disp"],
                      jm["static"]["v_soft"] if jm["static"]["v_soft"] is not None else -1,
                      jm["actual"]["v_soft"] if jm["actual"]["v_soft"] is not None else -1,
                      jm["actual"]["v_soft_lcb"], jm["actual"]["n_feasible"],
                      "DYNAMIC OK" if ok else "falsified"), flush=True)
                if ok:
                    cell_ok = True
                    out.setdefault("winners", {})[str(rho0)] = {"T": tl, "f": f, "lp_d": round(d, 4)}
                    break
            if cell_ok and star is None:
                star = tl
                break
        out["T_star_dyn"][str(rho0)] = star
        print("  => rho0=%.2f  T*_dyn = %s" % (rho0, star), flush=True)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
