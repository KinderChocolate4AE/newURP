"""C-1 Phase 1F R-2 axis-3: a_max sweep at a fixed (rho0, T_available) cell.

Patches BOTH layers so the sweep is physically consistent:
  1. script-level A_MAX  -> controller command magnitude (contract bang-bang, PD clip)
  2. backend KinematicLimits.a_max for role=="limiter" -> actual actuation clamp
     (shepherd/sim/analytic.py:120).  Attacker a_att_max is NOT touched.

Everything else (seed 1100, r_kill 2.6, r_net_dir 2.1, theta 0.9, judge) unchanged.
"""
from __future__ import annotations
import argparse, dataclasses, json, pathlib
import numpy as np

import shepherd.scripts.c1_corridor_probe as ccp
import shepherd.scripts.c1_response_probe as crp
from shepherd.sim.analytic import KinematicLimits

BAND_HI = 2.65  # set-based LB uses the upper edge of the ratified safe band


def build(a_max: float):
    """Fresh ProbeEnv with limiter a_max overridden at both layers."""
    ccp.A_MAX = float(a_max)
    crp.A_MAX = float(a_max)
    env_cfg, m3, _theta = crp._load("configs/m3a_a3e_p1.yaml")
    pe = crp.ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    from shepherd.scripts.c1_a1_connectivity import _override
    _override(E, crp.PRIMARY["r_kill"], crp.PRIMARY["r_net_dir"])
    n_patched = 0
    for ag in E.backend.agents:
        if ag.role == "limiter":
            ag.limits = dataclasses.replace(ag.limits, a_max=float(a_max))
            n_patched += 1
    assert n_patched == crp.N_LIM, f"patched {n_patched} limiters, expected {crp.N_LIM}"
    # sanity: attacker untouched
    adv = [a for a in E.backend.agents if a.role == "adversary"][0]
    return pe, crp.make_finisher_fn(crp.THETA), float(adv.limits.a_max)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--amax", default="30,32,34,36,38,40,42,45")
    ap.add_argument("--rho0", type=float, default=5.0)
    ap.add_argument("--tlead", type=float, default=0.5)
    ap.add_argument("--arms", default="H,C,P")
    ap.add_argument("--out", default="/tmp/r12/runC_amax.json")
    a = ap.parse_args()

    r_lane = crp.PRIMARY["r_net_dir"]; r_body = crp.R_BODY + crp.M_SAFETY
    D_lead = a.tlead * crp.V_CLOSE
    out = {"meta": {"phase": "R2_axis3_amax", "rho0": a.rho0, "T_lead": a.tlead,
                    "D_lead": D_lead, "rho_star": crp.RHO_STAR, "band_hi": BAND_HI,
                    "reset_seed": 1100, "note": "limiter a_max patched at script+backend; "
                                                "attacker a_att_max held at config value"},
           "cells": []}
    for am in [float(x) for x in a.amax.split(",")]:
        pe, fin, adv_amax = build(am)
        spawn = crp.make_spawn(a.rho0, D_lead)
        T_lb_pt = 2.0 * np.sqrt(abs(a.rho0 - crp.RHO_STAR) / am)
        T_lb_set = 2.0 * np.sqrt(max(a.rho0 - BAND_HI, 0.0) / am)
        cell = {"a_max": am, "adv_a_att_max": adv_amax, "T_available": a.tlead,
                "T_LB_point": round(float(T_lb_pt), 4), "T_LB_set": round(float(T_lb_set), 4),
                "margin_set": round(float(a.tlead - T_lb_set), 4), "arms": {}}
        for arm in a.arms.split(","):
            ctrl = {"H": crp.make_hold, "C": crp.make_contract, "P": crp.make_pd}[arm]()
            rec = crp.response_rollout(pe, spawn, ctrl, fin, r_lane=r_lane, r_body=r_body)
            cell["arms"][arm] = {"tier": rec["tier"], "safe": rec["safe"],
                                 "capture_margin": rec["capture_margin"],
                                 "clearance_margin": rec["clearance_margin"],
                                 "terminal_radial_err": round(rec["terminal_radial_err"], 4),
                                 "fire_step": rec["fire_step"], "penetrated": rec["penetrated"],
                                 "failure_mode": crp.classify(rec, a.tlead, float(T_lb_pt))}
            print("  a_max=%5.1f LBset=%.3f margin=%+.3f arm=%s -> tier=%d safe=%s err=%.3f fm=%s"
                  % (am, T_lb_set, a.tlead - T_lb_set, arm, rec["tier"], rec["safe"],
                     rec["terminal_radial_err"], cell["arms"][arm]["failure_mode"]), flush=True)
        out["cells"].append(cell)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
