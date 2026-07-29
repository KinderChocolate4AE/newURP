"""C-1 Phase 1P step 6A — seal the two inward-offset arms before D0.

THE SPLIT THE REVIEW REQUIRES
-----------------------------
Rung 1.5 produced two results that answer different questions and must not be
mixed:

  RI-GMAX    scenario-specific reserve-valid offset, chosen per scenario by the
             discovery sweep.  Status: a scenario-specific EXISTENCE probe.  It is
             a real trajectory (dynamics, continuity, actuator bound all checked),
             but it is not one controller -- it is one number per scenario.
  RI-SHARED  a single offset-selection rule applied identically everywhere.
             Status: a candidate SHARED controller architecture.

D0 gets both, as separate arms, so its outcome is readable:

    GMAX survives, SHARED fails  -> inward motion works, the selector is too weak
    both survive                 -> strong candidate for the shared architecture
    both fail                    -> the inward tracking class itself is insufficient
    GMAX fails                   -> the diagnostic nulls were a search-budget artefact

WHAT THIS CONTROLLER ACTUALLY IS
--------------------------------
Two layers, and the earlier "just a constant scalar, not a controller" was too
modest while "a controller" alone would be too generous:

    high level   a scalar inward offset fixed BEFORE the firing instant
    low level    a bounded PD feedback tracking the inward-shifted nominal
                 trajectory from the true firing state

Correct description: a scenario-conditioned scalar inward offset tracked by a
bounded low-level feedback controller.  It does not react to the attacker's state.

AND THE SELECTOR USES FORWARD SIMULATION
----------------------------------------
"Snap to the largest reserve-valid grid delta" needs to know which deltas are
reserve-valid, which needs the deployment window simulated forward.  That is not a
reactive rule, so it is named for what it is:

    PREDICTIVE_RADIAL_INWARD_SELECTOR

Forward simulation is declared part of the controller, not hidden in the harness.

RESERVE IS IN THE GATE, NOT APPLIED AFTERWARDS
----------------------------------------------
    RESERVE_VALID  =  E_cap  AND  m_lane >= 0.010 m  AND  defender admissible

so the selected offset is `delta_max_reserve`, not "the largest delta with
non-negative lane margin".  On the current numbers this changes little, but a
protocol that only becomes strict when it matters is not a protocol.

THE VALID SET NEED NOT BE AN INTERVAL
-------------------------------------
PD saturation and trajectory geometry can make mid-range deltas fail while larger
ones pass, so `delta_max` would be a misleading name for a disconnected set.  The
full valid grid, its contiguous runs, which run the selection sits in, and the gate
state 5 mm either side of the selection are all recorded.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM, A_MAX
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG, DIV_BASE_SEEDS
from shepherd.scripts.c1_phase1p_intervention import ring_frame, lane_clearance, LANE_MIN_M
from shepherd.scripts.c1_phase1p_6a_dynamic import (dynamic_inward, admissibility, gate,
                                                    replan_at, DELTA_GRID, DELTA_MAX,
                                                    LANE_RESERVE_M, KP, KD, _ring_basis)
from shepherd.scripts import c1_governance as G

SEAL_VERSION = "c1-6A-arms-2026-07-25"
NEIGHBOUR_M = 0.005


def saturation_metrics(A, n_dep):
    """How much actuator headroom is left, not just whether the bound was met."""
    mag = np.linalg.norm(A, axis=2)
    sat = mag >= A_MAX * (1.0 - 1e-9)
    frac = float(sat.mean())
    run = best = 0
    for s in range(sat.shape[0]):
        if sat[s].any():
            run += 1; best = max(best, run)
        else:
            run = 0
    in_dep = bool(sat[:min(n_dep + 1, len(sat))].any())
    return {"max_accel": float(mag.max()), "saturation_time_fraction": frac,
            "max_contiguous_saturated_steps": int(best),
            "saturated_during_deployment": in_dep,
            "grade": ("DYNAMICALLY_ADMISSIBLE_AT_ACCELERATION_LIMIT" if frac > 0 else
                      "DYNAMICALLY_ADMISSIBLE_WITH_CONTROL_RESERVE")}


def offset_decomposition(P, P0, delta, c0, e1, e2):
    """delta alone is ambiguous, so the four quantities the review separated are all
    reported.  Reporting only the absolute displacement UNDER-states the controller:
    the nominal ring drifts outward, so holding it nearly still is already a large
    effect relative to nominal.

      reference_offset            rho_nom - rho_target            (= delta)
      absolute_radial_displacement rho_act(end) - rho_act(fire)   physical motion
      achieved_offset_from_nominal rho_nom(end) - rho_act(end)    the CAUSAL effect
      terminal_tracking_error      rho_act(end) - rho_target(end)
      max_tracking_error           max over the window
    """
    def rad(X):
        Q = X - c0
        return np.hypot(Q @ e1, Q @ e2)
    rho = np.stack([rad(P[s]) for s in range(len(P))])
    rho_nom = np.stack([rad(P0[s]) for s in range(len(P))])
    rho_tgt = rho_nom - delta
    return {"reference_offset_m": float(delta),
            "absolute_radial_displacement_m": float((rho[-1] - rho[0]).mean()),
            "achieved_offset_from_nominal_m": float((rho_nom[-1] - rho[-1]).mean()),
            "terminal_tracking_error_m": float((rho[-1] - rho_tgt[-1]).mean()),
            "max_tracking_error_m": float(np.abs(rho - rho_tgt).max()),
            "nominal_radial_drift_m": float((rho_nom[-1] - rho_nom[0]).mean()),
            "note": "max_tracking_error equals delta because the REFERENCE steps at the "
                    "firing instant; position and velocity stay continuous but the "
                    "reference and the commanded acceleration do not"}


def tracking_error(P, P0, delta, c0, e1, e2):
    return offset_decomposition(P, P0, delta, c0, e1, e2)["max_tracking_error_m"]


def contiguous(valid_deltas, grid_step):
    runs, cur = [], []
    for d in valid_deltas:
        if cur and abs(d - cur[-1] - grid_step) > 1e-9:
            runs.append((cur[0], cur[-1])); cur = []
        cur.append(d)
    if cur:
        runs.append((cur[0], cur[-1]))
    return [[float(a), float(b)] for a, b in runs]


def artifact_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     default=float).encode()).hexdigest()[:24]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_6a_sealed_arms.json")
    ap.add_argument("--trace", default="BASE 3.2/0.50 C")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()
    n_dep = int(round(float(E.tau_deploy) / DT))
    step = float(DELTA_GRID[1] - DELTA_GRID[0])
    print("== 6A — seal RI-GMAX and RI-SHARED before D0 ==")
    print("   RESERVE_VALID = E_cap AND m_lane >= %.3f m AND defender admissible"
          % LANE_RESERVE_M)
    print("   grid %.3f m | selector = PREDICTIVE_RADIAL_INWARD_SELECTOR (forward sim "
          "is part of the controller)\n" % step)

    rows, trace = [], None
    for kind, tag, rho0_, tl, spec in witnesses():
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        c0, e1, e2, nrm = _ring_basis(P0[0])

        sweep = []
        for dl in DELTA_GRID:
            P, Vv, Aa, _b, _r = dynamic_inward(P0, Vp0, float(dl))
            adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
            lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, o[36:45], P, Vv, cone, tau)
            sat = saturation_metrics(Aa, n_dep)
            rv = bool(adm["DEFENDER_TRAJECTORY_ADMISSIBLE"] and lc is not None
                      and lc >= LANE_RESERVE_M and e_cap != "FAIL")
            sweep.append({"delta_m": float(dl), "lane_clearance_m": lc, "v_soft": v_r,
                          "E_cap": e_cap, "RESERVE_VALID": rv,
                          "tracking_error_m": tracking_error(P, P0, float(dl), c0, e1, e2),
                          **sat})
        valid = [s["delta_m"] for s in sweep if s["RESERVE_VALID"]]
        runs = contiguous(valid, step)
        lc0 = sweep[0]["lane_clearance_m"] or 0.0
        d_gmax = float(max(valid)) if valid else 0.0
        d_raw = float(np.clip(lc0 - LANE_RESERVE_M, 0.0, DELTA_MAX))
        cand = [d for d in valid if d <= d_raw]
        d_shared = float(max(cand)) if cand else 0.0

        arms = {}
        for arm, dl in (("RI-GMAX", d_gmax), ("RI-SHARED", d_shared)):
            P, Vv, Aa, _b, _r = dynamic_inward(P0, Vp0, dl)
            adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
            lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, o[36:45], P, Vv, cone, tau)
            sat = saturation_metrics(Aa, n_dep)
            nc, nv = replan_at(pe, E, pa, va, P, Vv, cone, tau, scenario_id=tag)
            nb = {}
            for off in (-NEIGHBOUR_M, +NEIGHBOUR_M):
                d2 = round(dl + off, 4)
                m = [s for s in sweep if abs(s["delta_m"] - d2) < 1e-9]
                nb["%+.3f" % off] = (m[0]["RESERVE_VALID"] if m else None)
            _hit = [r for r in runs if r[0] - 1e-9 <= dl <= r[1] + 1e-9]
            in_run = _hit[0] if _hit else None
            sealed = {"arm": arm, "protocol": G.PROTOCOL_VERSION,
                      "seal_version": SEAL_VERSION, "witness": tag,
                      "selected_delta_m": dl,
                      "selection_rule": ("largest RESERVE_VALID tested delta"
                                         if arm == "RI-GMAX" else
                                         "clip(lane_clearance_at_fire - %.3f, 0, %.2f) "
                                         "snapped down to the largest RESERVE_VALID grid "
                                         "delta" % (LANE_RESERVE_M, DELTA_MAX)),
                      "shared_rule_raw_delta_m": (d_raw if arm == "RI-SHARED" else None),
                      "pd_gains": {"kp": KP, "kd": KD}, "dt": DT, "a_max": A_MAX,
                      "reference": "nominal limiter trajectory shifted inward by delta, "
                                   "ring frame recovered by SVD",
                      "lane_reserve_m": LANE_RESERVE_M,
                      "gate": {"lane_clearance_m": lc, "v_soft": v_r, "p_feas": p_r,
                               "E_cap": e_cap, "RESERVE_VALID": bool(
                                   lc is not None and lc >= LANE_RESERVE_M
                                   and e_cap != "FAIL"
                                   and adm["DEFENDER_TRAJECTORY_ADMISSIBLE"])},
                      "admissibility": adm, "saturation": sat,
                      "offset_decomposition": offset_decomposition(P, P0, dl, c0, e1, e2),
                      "lane_reserve_excess_m": (None if lc is None
                                                else float(lc - LANE_RESERVE_M)),
                      "unmodelled_limits": ["acceleration slew rate", "actuator lag",
                                            "jerk bound", "low-level sample delay",
                                            "tracking noise"],
                      "arm_status": ("SCENARIO_SPECIFIC_PREDICTIVE_INWARD_EXISTENCE_PROBE"
                                     if arm == "RI-GMAX" else
                                     "SHARED_PREDICTIVE_RADIAL_INWARD_SELECTOR"),
                      "valid_set": {"grid_step_m": step, "n_valid": len(valid),
                                    "contiguous_runs": runs,
                                    "selection_in_run": in_run,
                                    "neighbour_reserve_valid": nb},
                      "defender_trajectory_sha": G.attack_policy_hash(P),
                      "defender_velocity_sha": G.attack_policy_hash(Vv),
                      "reset_id": DIAG["reset"], "verifier_version": "c1_exact_clearance+cone",
                      "diagnostic_budget": {**DIAG, "base_seeds": list(DIV_BASE_SEEDS)}}
            sealed["artifact_hash"] = artifact_hash(sealed)
            sealed["diagnostic"] = {
                "n_search_candidates": nc, "n_verified_escape": nv,
                "label": ("REDISCOVERED_AT_DIAGNOSTIC_BUDGET" if nv
                          else "SURVIVED_DIAGNOSTIC_REPLAN")}
            arms[arm] = sealed
            if tag == a.trace and arm == "RI-GMAX":
                rho = lambda X: np.hypot((X - c0) @ e1, (X - c0) @ e2)
                trace = {"witness": tag, "delta_m": dl,
                         "note": "lane margin at fire is %.4f m yet delta %.3f m is "
                                 "RESERVE_VALID -- the limiter tracks a shifted NOMINAL "
                                 "path, and the nominal path itself moves away from the "
                                 "lane during the window" % (lc0, dl),
                         "per_step": [{"step": s, "t_s": s * DT,
                                       "rho_nominal_m": [float(x) for x in rho(P0[s])],
                                       "rho_target_m": [float(x - dl) for x in rho(P0[s])],
                                       "rho_actual_m": [float(x) for x in rho(P[s])],
                                       "lane_margin_m": lane_clearance(P[:s + 1], cone, tau),
                                       "cmd_accel_norm": [float(x) for x in
                                                          np.linalg.norm(Aa[s], axis=1)]}
                                      for s in range(len(P))]}
        cls = "B_GROSS_RADIAL_DISPLACEMENT" if kind == "MAXCLR" else "A_NEAR_TERMINAL_RAZOR_GAP"
        rows.append({"witness": tag, "class": kind, "failure_class": cls,
                     "nominal_lane_clearance_m": lc0, "sweep": sweep,
                     "reserve_valid_deltas": valid, "contiguous_runs": runs,
                     "arms": arms})
        g, sh = arms["RI-GMAX"], arms["RI-SHARED"]
        print("   %-22s %s runs %-22s | GMAX d %.3f esc %-2d %s | SHARED d %.3f esc %-2d %s"
              % (tag, cls[0], str(runs)[:22], g["selected_delta_m"],
                 g["diagnostic"]["n_verified_escape"], g["saturation"]["grade"][-14:],
                 sh["selected_delta_m"], sh["diagnostic"]["n_verified_escape"],
                 sh["saturation"]["grade"][-14:]), flush=True)

    A_rows = [r for r in rows if r["failure_class"].startswith("A_")]
    summary = {}
    for arm in ("RI-GMAX", "RI-SHARED"):
        surv = [r["witness"] for r in A_rows
                if r["arms"][arm]["diagnostic"]["label"] == "SURVIVED_DIAGNOSTIC_REPLAN"]
        res = [r["witness"] for r in A_rows if r["arms"][arm]["gate"]["RESERVE_VALID"]]
        sat = [r["witness"] for r in A_rows
               if r["arms"][arm]["saturation"]["saturation_time_fraction"] > 0]
        summary[arm] = {"class_A_total": len(A_rows), "reserve_valid": len(res),
                        "survived_diagnostic_replan": surv, "n_survived": len(surv),
                        "at_acceleration_limit": sat}
    noncontig = [r["witness"] for r in rows if len(r["contiguous_runs"]) > 1]
    print("\n   Class A %d | Class B %d" % (len(A_rows), len(rows) - len(A_rows)))
    for arm in ("RI-GMAX", "RI-SHARED"):
        s = summary[arm]
        print("   %-10s D0 candidates %d/%d  | at acceleration limit: %d"
              % (arm, s["n_survived"], s["class_A_total"], len(s["at_acceleration_limit"])))
    print("   non-contiguous RESERVE_VALID sets: %d %s" % (len(noncontig), noncontig))

    out = {"meta": {"script": "c1_phase1p_6a_seal", "seal_version": SEAL_VERSION,
                    "protocol": G.PROTOCOL_VERSION,
                    "arms": {"RI-GMAX": "scenario-specific reserve-valid offset; a "
                                        "scenario-specific EXISTENCE probe, not one controller",
                             "RI-SHARED": "one selection rule everywhere; a candidate SHARED "
                                          "controller architecture"},
                    "controller": "a scenario-conditioned scalar inward offset tracked by a "
                                  "bounded low-level PD feedback controller; it does NOT react "
                                  "to the attacker's state",
                    "selector": "PREDICTIVE_RADIAL_INWARD_SELECTOR -- forward simulation of the "
                                "deployment window is part of the controller, not the harness",
                    "reserve_valid": "E_cap AND m_lane >= %.3f m AND defender admissible"
                                     % LANE_RESERVE_M,
                    "valid_set_note": "the RESERVE_VALID set is not assumed to be an interval; "
                                      "contiguous runs, the run containing the selection, and "
                                      "the gate state +-5 mm are all recorded",
                    "labels": {"diagnostic": "SURVIVED_DIAGNOSTIC_REPLAN is NOT a seal; "
                                             "D0 -> D1 (auto on D0 survival) -> D2a follow",
                               "grades": ["DYNAMICALLY_ADMISSIBLE_WITH_CONTROL_RESERVE",
                                          "DYNAMICALLY_ADMISSIBLE_AT_ACCELERATION_LIMIT"]},
                    "d0_rule": "selected delta and every sealed field are FROZEN; changing them "
                               "after seeing D0 is a protocol revision, not a rerun"},
           "summary": summary, "non_contiguous_valid_sets": noncontig,
           "trace_" + a.trace.replace(" ", "_").replace("/", "_"): trace,
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
