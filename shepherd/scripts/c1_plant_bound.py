"""C-1 Phase 1F — PLANT bound vs CONTROLLER bound (R-1 / R-2).

Why this exists
---------------
Phase 1B/1C measured the response envelope against the analytic bound

    T_LB(rho0) = 2*sqrt(|rho0 - rho*| / a_max)                       (rest-to-rest)

That bound charges the controller for arriving at rho* with ZERO radial speed.
The judge never asks for that.  It asks for

    E_cap  : one instant with v_soft >= theta and p_feas > 0   (static snapshot at fire)
    E_lane : perp >= r_net_dir + r_body + m_safety = 2.50 m for EVERY step of the
             deploy window [f, f+n_dep]

so a limiter may cross into the ratified band [2.55, 2.65] still moving inward,
provided the remaining authority arrests it above the 2.50 lane floor.  Using the
rest-to-rest bound as the denominator therefore OVERSTATES the plant limit and
UNDERSTATES the controller gap.

What this computes
------------------
(1) PLANT bound, exactly.  The radial subproblem is linear under the simulator's
    own integrator (semi-implicit Euler, shepherd/sim/analytic.py):

        v_{t+1} = v_t + a_t*dt ;   p_{t+1} = p_t + v_{t+1}*dt
    =>  rho_t   = rho0 + dt^2 * sum_{k<t} (t-k) * a_k                (linear in a)

    so "does ANY |a_t| <= a_max sequence satisfy band-at-f AND floor-on-window"
    is an LP.  Infeasible => a statement about the PLANT.  Feasible => every
    failure at that cell is a controller gap.

(2) WITNESS, played closed-loop.  The LP is re-solved with a max-min-clearance
    objective and the resulting per-step radial acceleration is commanded inside
    the FULL probe rollout (3-D limiters, real finisher fire trigger, real judge,
    exact replay).  Only a tier-4 there counts as a demonstration.

(3) KNOB scan.  At a cell that misses, the minimum single-knob change (a_max,
    rho0, band edge, lane floor) that restores feasibility.

Everything else is held at the ratified invariants: r_kill 2.6, r_net_dir 2.1,
r_body 0.2, m_safety 0.2, theta 0.9, reset seed 1100, exact replay.

Caveats
-------
* The LP abstracts the RADIAL subproblem only; angular sealing, axial station and
  attacker maneuver are carried by the closed-loop replay in (2), not by the LP.
* Capture eligibility is still the STATIC snapshot judge.  Confirmation under the
  E1.5 actual-trajectory judge is REQUIRED before any T*_plant is treated as
  certified.
* !! PHASE 1G RESULT (2026-07-25) !!  `solve_witness` (max-min-clearance) is
  UNDER-CONSTRAINED and its witnesses were FALSIFIED by that audit at every cell:
  maximising the minimum clearance rewards flying the ring OUTWARD after the fire
  instant, giving measured sup-displacement 1.9-2.3 m against the 0.26 m screen and
  actual-trajectory v_soft 0.02-0.04 versus static 0.98-1.00.  Same shape as the
  Phase 1E optimizer exploit.  Use `solve_witness_hold` for any capture claim;
  `solve_witness` is retained only to reproduce the 1F/1G record.
"""
from __future__ import annotations
import argparse, json, math, pathlib
import numpy as np
from scipy.optimize import linprog

from shepherd.scripts.c1_response_probe import (
    _load, _radial, ProbeEnv, make_spawn, make_finisher_fn, response_rollout,
    PRIMARY, THETA, R_BODY, M_SAFETY, X_RING, V_CLOSE, RHO_STAR)
from shepherd.scripts.c1_corridor_probe import _clip_norm, A_MAX, N_LIM

DT = 0.05
BAND_LO, BAND_HI = 2.55, 2.65          # ratified terminal band (c1_terminal_band_refine)
FLOOR = 2.50                           # E_lane threshold = r_net_dir + r_body + m_safety
N_DEP = 8                              # = int(round(tau_deploy/dt)) = round(0.4/0.05).
                                       # The judge checks E_lane on range(f, f+n_dep+1) =
                                       # f..f+8 -> 9 states spanning 8*dt = 0.40 s.  This
                                       # value was 9 through Phase 1F/1G, which constrained
                                       # f..f+9 = 0.45 s, i.e. ONE STEP MORE THAN THE JUDGE
                                       # (external review 2026-07-25, defect #2).  The error
                                       # was conservative -- it can only have made T* too
                                       # large and nominal look infeasible when it may not be.
R_KILL = 2.6                           # limiter kill radius (displacement screen base)
EPS_DISP = 0.10                        # c1_phase1e R3 screen: sup|L(s)-L(0)| <= EPS_DISP*r_kill
HOLD_RHO = 2.60


# ------------------------------------------------------------------ plant LP
def rho_row(t, H):
    """rho_t = rho0 + row @ a, with row = dt^2 * (t-k) for k < t."""
    r = np.zeros(H)
    for k in range(min(t, H)):
        r[k] = (t - k)
    return r * DT * DT


def solve_witness(rho0, f, n_dep=N_DEP, a_max=A_MAX, band=(BAND_LO, BAND_HI), floor=FLOOR):
    """max m  s.t. rho_f in band, rho_t - floor >= m on [f, f+n_dep], |a| <= a_max.

    Returns (a_seq, m_star) or (None, None) when the LP itself is infeasible.
    m_star < 0 => the PLANT cannot hold the lane for this (rho0, f); the magnitude
    is exactly how far short it is, in metres.
    """
    lo, hi = band
    H = f + n_dep
    A_ub, b_ub = [], []
    rf = np.concatenate([rho_row(f, H), [0.0]])
    A_ub.append(rf); b_ub.append(hi - rho0)               # rho_f <= band_hi
    A_ub.append(-rf); b_ub.append(rho0 - lo)              # rho_f >= band_lo
    for t in range(f, f + n_dep + 1):
        A_ub.append(np.concatenate([-rho_row(t, H), [1.0]])); b_ub.append(rho0 - floor)
    c = np.zeros(H + 1); c[-1] = -1.0
    res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                  bounds=[(-a_max, a_max)] * H + [(None, hi - floor)], method="highs")
    if res.status != 0:
        return None, None
    return res.x[:H], float(res.x[-1])


def solve_witness_hold(rho0, f, n_dep=N_DEP, a_max=A_MAX, band=(BAND_LO, BAND_HI),
                       floor=FLOOR, disp_cap=None):
    """HOLD variant (Phase 1G correction).

    `solve_witness` above is UNDER-CONSTRAINED: maximising the minimum clearance
    rewards flying the ring OUTWARD once the fire instant has passed, so its
    witnesses satisfy the static snapshot and then leave (measured sup-displacement
    1.9-2.3 m against the 0.26 m screen) — the same shape as the Phase 1E optimizer
    exploit.  Phase 1G falsified every one of them under the actual-trajectory judge.

    This variant adds the missing constraint: the ring must STAY where it fired.

        min d   s.t.  rho_f in band
                      rho_t >= floor                       for t in [f, f+n_dep]
                      |rho_t - rho_f| <= d <= disp_cap     for t in [f, f+n_dep]
                      |a_t| <= a_max

    disp_cap defaults to EPS_DISP * r_kill = 0.10 * 2.6 = 0.26 m, i.e. exactly the
    screen the audit applies.  Returns (a_seq, d_star, m_star).
    """
    lo, hi = band
    cap = float(EPS_DISP * R_KILL if disp_cap is None else disp_cap)
    H = f + n_dep
    rf = rho_row(f, H)
    A_ub, b_ub = [], []
    A_ub.append(np.concatenate([rf, [0.0]])); b_ub.append(hi - rho0)
    A_ub.append(np.concatenate([-rf, [0.0]])); b_ub.append(rho0 - lo)
    for t in range(f, f + n_dep + 1):
        rt = rho_row(t, H)
        A_ub.append(np.concatenate([-rt, [0.0]])); b_ub.append(rho0 - floor)   # rho_t >= floor
        A_ub.append(np.concatenate([rt - rf, [-1.0]])); b_ub.append(0.0)       # rho_t-rho_f <= d
        A_ub.append(np.concatenate([rf - rt, [-1.0]])); b_ub.append(0.0)       # rho_f-rho_t <= d
    c = np.zeros(H + 1); c[-1] = 1.0                                            # minimise d
    res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                  bounds=[(-a_max, a_max)] * H + [(0.0, cap)], method="highs")
    if res.status != 0:
        return None, None, None
    a_seq = res.x[:H]; d = float(res.x[-1])
    rhos = np.array([rho0 + rho_row(t, H) @ a_seq for t in range(f, f + n_dep + 1)])
    return a_seq, d, float(rhos.min() - floor)


# ------------------------------------------------------- arm L (LP witness)
def make_lp_arm(a_seq):
    """Command a_seq[t] along each limiter's OWN radial direction (role-agnostic),
    with the tangential damping the ratified arms use; PD hold once the seq ends."""
    st = {"t": 0}
    def fn(obs, flags):
        o = np.asarray(obs, float); acts = []
        t = st["t"]
        for i in range(N_LIM):
            p = o[9 * i:9 * i + 3]; v = o[9 * i + 3:9 * i + 6]
            _, perp, pv = _radial(p); rad_hat = pv / (perp + 1e-9)
            vr = float(v[1:] @ rad_hat[1:]) if perp > 1e-6 else 0.0
            if t < len(a_seq):
                a = a_seq[t] * rad_hat - 6.0 * (v - vr * rad_hat)
            else:
                tgt = np.array([X_RING, HOLD_RHO * pv[1] / (perp + 1e-9),
                                HOLD_RHO * pv[2] / (perp + 1e-9)])
                a = 25.0 * (tgt - p) + 8.0 * (-v)
            acts.append(_clip_norm(a, A_MAX).astype(np.float32))
        st["t"] += 1
        return acts
    return fn


def build_probe():
    env_cfg, m3, _theta = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    from shepherd.scripts.c1_a1_connectivity import _override
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"])
    return pe, make_finisher_fn(THETA)


def run_cell(pe, fin, rho0, tl, f, n_dep=N_DEP, a_max=A_MAX):
    """LP witness at fire step f, played through the real closed-loop rollout."""
    seq, m = solve_witness(rho0, f, n_dep, a_max)
    if seq is None:
        return {"rho0": rho0, "T_available": tl, "f_target": f, "lp": "INFEASIBLE"}
    rec = response_rollout(pe, make_spawn(rho0, tl * V_CLOSE), make_lp_arm(seq), fin,
                           r_lane=PRIMARY["r_net_dir"], r_body=R_BODY + M_SAFETY)
    return {"rho0": rho0, "T_available": tl, "f_target": f,
            "lp_min_clearance": round(m, 4), "a_seq": [round(float(x), 3) for x in seq],
            "tier": rec["tier"], "safe": rec["safe"], "E_capture": rec["E_capture"],
            "E_lane": rec["E_lane"], "capture_margin": rec["capture_margin"],
            "clearance_margin": rec["clearance_margin"], "fire_step": rec["fire_step"],
            "penetrated": rec["penetrated"],
            "terminal_radial_err": round(rec["terminal_radial_err"], 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rho0", default="2.8,3.2,4.0,5.0")
    ap.add_argument("--tlead", default="0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75")
    ap.add_argument("--ndep", type=int, default=N_DEP)
    ap.add_argument("--knobscan", default="5.0:0.50", help="rho0:T cell for the minimal-change scan")
    ap.add_argument("--out", default="results/c1_corridor/c1_plant_bound.json")
    a = ap.parse_args()
    pe, fin = build_probe()
    out = {"meta": {"phase": "1F_plant_bound", "dt": DT, "band": [BAND_LO, BAND_HI],
                    "floor": FLOOR, "n_dep": a.ndep, "a_max": A_MAX, "reset_seed": 1100,
                    "invariants": {"r_kill": 2.6, "r_net_dir": 2.1, "r_body": R_BODY,
                                   "m_safety": M_SAFETY, "theta": THETA},
                    "note": "T*_plant = smallest T at which the LP witness reaches tier 4 "
                            "in the FULL closed-loop replay (not an analytic bound)"},
           "cells": [], "T_star_plant": {}, "knob_scan": {}}

    for rho0 in [float(x) for x in a.rho0.split(",")]:
        star = None
        for tl in [float(x) for x in a.tlead.split(",")]:
            fmax = int(round(tl / DT))
            for f in range(max(1, fmax - 2), fmax + 1):
                r = run_cell(pe, fin, rho0, tl, f, a.ndep)
                out["cells"].append(r)
                print("  rho0=%.2f T=%.2f f=%2d | m*=%s -> tier=%s safe=%s clr=%s fire=%s pen=%s"
                      % (rho0, tl, f, r.get("lp_min_clearance"), r.get("tier"), r.get("safe"),
                         r.get("clearance_margin"), r.get("fire_step"), r.get("penetrated")),
                      flush=True)
                if r.get("safe") and star is None:
                    star = tl
            if star is not None:
                break
        lb_rest = 2 * math.sqrt(max(rho0 - BAND_HI, 0) / A_MAX)
        out["T_star_plant"][str(rho0)] = {"T_star_plant": star, "T_LB_rest": round(lb_rest, 4)}
        print("  => rho0=%.2f  T*_plant=%s  (rest-to-rest LB was %.3f)" % (rho0, star, lb_rest))

    # ---- minimal single-knob change at the miss cell
    kr, kt = a.knobscan.split(":"); kr = float(kr); kt = float(kt)
    kf = int(round(kt / DT)) - 1
    base = solve_witness(kr, kf)[1]
    scan = {"cell": {"rho0": kr, "T": kt, "f": kf}, "baseline_m_star": round(base, 4), "knobs": {}}
    scan["knobs"]["a_max"] = [{"value": v, "m_star": round(solve_witness(kr, kf, a_max=v)[1], 4)}
                              for v in [30.0, 30.5, 31.0, 32.0, 34.0, 36.0]]
    scan["knobs"]["rho0"] = [{"value": v, "m_star": round(solve_witness(v, kf)[1], 4)}
                             for v in [5.0, 4.95, 4.9, 4.8, 4.7]]
    scan["knobs"]["band_hi"] = [{"value": v, "m_star": round(solve_witness(kr, kf, band=(BAND_LO, v))[1], 4)}
                                for v in [2.65, 2.66, 2.67, 2.70, 2.75]]
    scan["knobs"]["lane_floor"] = [{"value": v, "m_star": round(solve_witness(kr, kf, floor=v)[1], 4)}
                                   for v in [2.50, 2.495, 2.49, 2.485, 2.48, 2.45]]
    out["knob_scan"] = scan
    print("  knob scan @ rho0=%.2f T=%.2f f=%d : baseline m*=%+.4f m" % (kr, kt, kf, base))

    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
