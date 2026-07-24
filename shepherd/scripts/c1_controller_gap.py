"""C-1 Phase 1C — Arm O Controller-Gap Probe (ratified spec 2026-07-22).

Question: does slot-free role-agnostic trajectory optimization reach the deployment-safe
terminal SET with less response time than the fixed-formation baselines (H/C/P)?

Design invariants (spec):
- Verdict is the REAL judge (v_soft>=theta, p_feas>0, clearance>=0, no penetration) on
  exact replay — NOT membership of a rho=2.6 ring. Arm O never hard-targets rho=2.6.
- Analytic lower bound is SET-based: T_LB,set(rho0) = min over rho_T in safe set of
  2*sqrt(|rho0-rho_T|/a_max). Coarse safe band = [2.55, 2.65]; for rho0>2.65 the nearest
  safe radius is 2.65.
- Slot-free / role-agnostic: per-limiter free accel knots, no formation slot, no role.
- Lexicographic ranking (no unsafe Tier-2 preferred over Tier-4). Band = soft SEARCH
  guidance only (opt-in), never the verdict.
- Warm-start family: WS1 best simple-arm trajectory, WS2 band-edge contraction (terminal
  witness proxy), WS3 cold/random. Discovery = >=2/3 O runs Tier-4 safe (or 2 warm
  families), each exact-replay + fresh-CRN, positive cap & clr, no penetration.
- Metric = boundary shift vs simple baseline:  dT_gain=T_simple*-T_O*,
  dT_residual=T_O*-T_LB,set,  G_closure=dT_gain/(T_simple*-T_LB,set).
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (response_rollout, make_spawn, make_contract, make_pd,
    make_hold, _radial, THETA, N_LIM, R_BODY, M_SAFETY, PRIMARY, X_FIRE, V_CLOSE, RHO_STAR)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, knots_to_seq, A_MAX
from shepherd.scripts.c1_a1_connectivity import _override, a1_rollout

RHO_MIN, RHO_MAX = 2.55, 2.65       # coarse confirmed safe terminal interval
DT = 0.05


def T_LB_set(rho0):
    """Set-based ideal radial rest-to-rest lower bound to the NEAREST safe radius."""
    nearest = min(max(rho0, RHO_MIN), RHO_MAX)
    return 2.0 * np.sqrt(abs(rho0 - nearest) / A_MAX)


def _lex(rec, within):
    """Lexicographic sort key (higher=better): no-pen > E_cap > E_lane > Tier4 > within-score."""
    return (0 if rec["penetrated"] else 1, 1 if rec["E_capture"] else 0,
            1 if rec["E_lane"] else 0, 1 if rec["tier"] >= 4 else 0, within)


def _within(rec, knots):
    cap = rec["capture_margin"] if rec["capture_margin"] is not None else -1.0
    clr = rec["clearance_margin"] if rec["clearance_margin"] is not None else -3.0
    return cap + min(clr, 0.0) - 0.01 * float(np.mean(np.abs(knots)))


def _band_metrics(pe, spawn, knots, ctrl_len, fin, r_lane, r_body):
    """Exact-replay + trace-derived terminal diagnostics for the winning candidate."""
    rec = a1_rollout(pe, spawn, knots_to_seq(knots, ctrl_len), fin, r_lane=r_lane, r_body=r_body, trace=True)
    tr = rec.get("trace", {}); lim = np.asarray(tr.get("lim", []), float); vs = np.asarray(tr.get("v_soft", []), float)
    fs = rec["fire_step"]; t = fs if fs is not None else (int(np.argmax(vs)) if len(vs) else 0)
    rad_err = ang_gap = term_vel = band_cost = float("nan")
    if len(lim):
        t = min(t, len(lim) - 1)
        perps = [_radial(lim[t][i])[1] for i in range(N_LIM)]
        rad_err = float(np.mean([abs(p - RHO_STAR) for p in perps]))
        band_cost = float(np.sum([max(0.0, RHO_MIN - p) ** 2 + max(0.0, p - RHO_MAX) ** 2 for p in perps]))
        angs = [np.arctan2(_radial(lim[t][i])[2][2], _radial(lim[t][i])[2][1]) for i in range(N_LIM)]
        a = np.sort(angs); gaps = np.diff(np.concatenate([a, [a[0] + 2 * np.pi]])); ang_gap = float(np.degrees(gaps.max()))
        if t > 0:
            dv = (lim[t] - lim[t - 1]) / DT; term_vel = float(np.mean([np.linalg.norm(dv[i]) for i in range(N_LIM)]))
    rec["terminal_radial_err"] = rad_err; rec["max_angular_gap_deg"] = ang_gap
    rec["terminal_velocity"] = term_vel; rec["band_cost"] = band_cost
    rec["safe"] = bool(rec["tier"] >= 4 and not rec["penetrated"])
    return rec


# ---- warm-start family (slot-free) ----
def _log_wrap(inner):
    log = []
    def fn(obs, flags):
        a = inner(obs, flags); log.append(np.stack([np.asarray(x, float) for x in a])); return a
    fn.log = log; return fn

def ws1_best_simple(pe, spawn, fin, r_lane, r_body, K):
    """WS1: fit knots from the better of the C/P baseline trajectories at this cell."""
    best_log, bkey = None, None
    for mk in (make_contract, make_pd):
        w = _log_wrap(mk()); rec = response_rollout(pe, spawn, w, fin, r_lane=r_lane, r_body=r_body)
        key = (0 if rec["penetrated"] else 1, int(rec["E_capture"]), int(rec["E_lane"]), int(rec["safe"]))
        if bkey is None or key > bkey: bkey, best_log = key, w.log
    A = np.asarray(best_log, float)
    if len(A) == 0: return np.zeros((K, N_LIM, 3))
    idx = np.linspace(0, len(A) - 1, K).astype(int)
    return A[idx]

def ws2_band_edge(spawn, K, target=RHO_MAX):
    """WS2: bang-bang contraction of each limiter (own angle) to the near band edge."""
    L = spawn["limiters"]; kn = np.zeros((K, N_LIM, 3)); h = max(K // 2, 1)
    for i in range(N_LIM):
        _, perp, pv = _radial(L[i]); rad = pv / (perp + 1e-9); err = perp - target
        a = np.clip(abs(err) / ((h * DT) ** 2 + 1e-9), 0, A_MAX) * (1.0 if err > 0 else -1.0)
        for k in range(h): kn[k, i] = -a * rad
        for k in range(h, K): kn[k, i] = a * rad
    return kn


def cem_O(pe, spawn, fin, r_lane, r_body, warm, seed, ctrl_len, pop, iters, K=6):
    """Slot-free CEM over per-limiter accel knots. Lexicographic elite selection."""
    rng = np.random.default_rng(seed)
    mu = (np.asarray(warm, float).copy() if warm is not None else np.zeros((K, N_LIM, 3)))
    K = mu.shape[0]; sig = np.full((K, N_LIM, 3), 8.0)
    best, bkey = None, None
    for _ in range(iters):
        cand = np.clip(mu + sig * rng.standard_normal((pop, K, N_LIM, 3)), -A_MAX, A_MAX); cand[0] = mu
        keyed = []
        for c in range(pop):
            rec = a1_rollout(pe, spawn, knots_to_seq(cand[c], ctrl_len), fin, r_lane=r_lane, r_body=r_body)
            k = _lex(rec, _within(rec, cand[c])); keyed.append((k, c))
            if bkey is None or k > bkey: bkey, best = k, (rec, cand[c].copy())
        keyed.sort(key=lambda z: z[0], reverse=True); el = [z[1] for z in keyed[:max(2, pop // 4)]]
        mu = cand[el].mean(0); sig = cand[el].std(0) * 1.1 + 0.5
        if best[0]["tier"] >= 4 and not best[0]["penetrated"]: break
    return best  # (rec, knots)


def classify(rec, T_avail, T_lb):
    if rec.get("safe") or (rec["tier"] >= 4 and not rec["penetrated"]): return "OK", ""
    prim, sec = "UNCLASSIFIED", ""
    if T_avail < T_lb: prim = "KINEMATIC_NEGATIVE_MARGIN"
    elif rec["penetrated"]: prim = "PENETRATION"
    elif rec["fire_step"] is None:
        prim = "RADIAL_TOO_SLOW" if (rec.get("terminal_radial_err") or 9) > 0.4 else "CAPTURE_MARGIN_FAIL"
    elif rec.get("clearance_margin") is not None and rec["clearance_margin"] < 0:
        prim = "RADIAL_OVERSHOOT" if (rec.get("terminal_radial_err") or 9) < 0.4 else "CLEARANCE_VIOLATION"
    elif (rec.get("max_angular_gap_deg") or 0) > 150: prim = "ANGULAR_SEAL_FAILURE"
    if (rec.get("terminal_velocity") or 0) > 3.0: sec = "TERMINAL_RELATIVE_VELOCITY"
    elif (rec.get("max_angular_gap_deg") or 0) > 130: sec = "ANGULAR_SEAL_FAILURE"
    return prim, sec


def run_O_cell(pe, fin, rho0, tl, r_lane, r_body, *, pop, iters, K=6):
    """3 O runs (WS1+s0, WS2+s1, WS3+s2). Success = >=2 Tier-4 safe on exact + fresh CRN."""
    spawn = make_spawn(rho0, tl * V_CLOSE)
    n_dep = int(round(pe.ad.env.tau_deploy / DT)); ctrl_len = int(round(tl / DT)) + n_dep + 2
    warms = [("WS1", ws1_best_simple(pe, spawn, fin, r_lane, r_body, K), 700),
             ("WS2", ws2_band_edge(spawn, K), 701),
             ("WS3", None, 702)]  # WS3 cold + random via seed
    runs = []
    for wname, warm, sbase in warms:
        seed = 401_000_000 + int(rho0 * 100) * 1000 + int(tl * 100) + sbase
        rec, kn = cem_O(pe, spawn, fin, r_lane, r_body, warm, seed, ctrl_len, pop, iters, K)
        full = _band_metrics(pe, spawn, kn, ctrl_len, fin, r_lane, r_body)          # exact replay
        crn = a1_rollout(pe, spawn, knots_to_seq(kn, ctrl_len), fin, r_lane=r_lane, r_body=r_body, seed=1101)
        ok = bool(full["tier"] >= 4 and not full["penetrated"] and crn["tier"] >= 4 and not crn["penetrated"])
        prim, sec = classify(full, tl - 0.0, T_LB_set(rho0))
        runs.append({"warm": wname, "safe": ok, "tier": full["tier"], "cap": full["capture_margin"],
                     "clr": full["clearance_margin"], "term_vel": full["terminal_velocity"],
                     "ang_gap": full["max_angular_gap_deg"], "band_cost": full["band_cost"],
                     "crn_tier": crn["tier"], "primary_fail": prim, "secondary_fail": sec})
    n_safe = sum(r["safe"] for r in runs)
    return {"rho0": rho0, "T_lead": tl, "n_safe": n_safe, "O_success": n_safe >= 2, "runs": runs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="3.2:0.30,0.35,0.40,0.45,0.50;4.0:0.45,0.50,0.55,0.60,0.65,0.70;5.0:0.55,0.60,0.70,0.80,0.90,1.00",
                    help="rho0:T,T,...;rho0:T,... (boundary-adjacent fine grid)")
    ap.add_argument("--pop", type=int, default=20); ap.add_argument("--iters", type=int, default=12)
    ap.add_argument("--out", default="results/c1_corridor/c1_controller_gap.json")
    a = ap.parse_args()
    env_cfg, m3, theta = _load("configs/m3a_a3e_p1.yaml"); pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    cells = []
    for grp in a.cells.split(";"):
        r, ts = grp.split(":"); cells.append((float(r), [float(x) for x in ts.split(",")]))
    out = {"meta": {"phase": "1C_controller_gap", "rho_star": RHO_STAR, "safe_band": [RHO_MIN, RHO_MAX],
                    "a_max": A_MAX, "v_closing": V_CLOSE, "x_fire": X_FIRE, "reset_seed": 1100, "crn_seed": 1101,
                    "LB": "set-based: min_{rho_T in band} 2*sqrt(|rho0-rho_T|/a_max)"}, "cells": [], "gap": {}}
    for rho0, ts in cells:
        T_lb = float(T_LB_set(rho0)); T_O = None; per = []
        for tl in ts:
            r = run_O_cell(pe, fin, rho0, tl, RL, RB, pop=a.pop, iters=a.iters)
            per.append(r)
            if r["O_success"] and T_O is None: T_O = tl
            print("  rho0=%.1f T=%.2f -> O n_safe=%d/3 success=%s (%s)" % (
                rho0, tl, r["n_safe"], r["O_success"], ",".join(x["warm"] for x in r["runs"] if x["safe"]) or "-"), flush=True)
        out["cells"].append({"rho0": rho0, "T_LB_set": round(T_lb, 3), "T_O_star": T_O, "per_T": per})
        out["gap"][str(rho0)] = {"T_LB_set": round(T_lb, 3), "T_O_star": T_O}
        print("  >>> rho0=%.1f  T_O*=%s  T_LB,set=%.3f" % (rho0, T_O, T_lb), flush=True)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
