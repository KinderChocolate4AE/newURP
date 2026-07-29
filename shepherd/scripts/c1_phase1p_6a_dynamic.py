"""C-1 Phase 1P step 6A rung 1.5 — is the inward shift a TRAJECTORY or an ORACLE?

THE ANSWER, UP FRONT: THE RUNG-1 PROBE WAS AN ORACLE
----------------------------------------------------
`c1_phase1p_6a_probe.radial_inward` shifted EVERY limiter position, including the
one at the fire instant, inward by delta:

    L_delta(t) = L(t) - delta * e_rho(t)        for every t in the window, t=0 included

and re-derived velocities by finite differences of the shifted path.  The transition
from the true pre-fire trajectory into the shifted one was never simulated.  At the
fire instant the limiter simply IS delta metres closer than it actually was.  That
is case A in the review's split: a geometric oracle, not a controller.  The rung-1
result therefore supports only

    RADIAL_INWARD_GEOMETRIC_ORACLE

and the earlier framing is downgraded accordingly.  This module measures that
discontinuity explicitly rather than asserting it, and then builds the dynamic
version.

THE DYNAMIC VERSION
-------------------
`RADIAL_INWARD_DYNAMIC(delta)` starts from the TRUE fire-instant position and
velocity and adds a radial correction to the NOMINAL acceleration, clipping the
total to the actuator bound:

    a_nom[s] = (v[s+1] - v[s]) / dt                        recovered from the rollout
    a_cmd[s] = clip( a_nom[s] + (kp*(rho_tgt - rho) - kd*rho_dot) * (-e_rho), A_MAX )
    v[s+1]   = v[s] + a_cmd[s]*dt                          the simulator's own
    p[s+1]   = p[s] + v[s+1]*dt                            semi-implicit Euler

So the intervention is "the nominal controller plus a bounded radial correction",
which is a controller-shaped object.  Admissibility is then CHECKED, not assumed:

    POSITION_CONTINUITY_PASS        p[0] equals the true fire-instant position
    VELOCITY_CONTINUITY_PASS        v[0] equals the true fire-instant velocity
    ACCELERATION_BOUND_PASS         |a_cmd| <= A_MAX at every step
    INTER_LIMITER_COLLISION_FREE    pairwise separation stays above 2*r_body
    DEFENDER_TRAJECTORY_ADMISSIBLE  all four, plus E_cap and E_lane

SHARED SELECTION RULE, NOT A PER-WITNESS TABLE
----------------------------------------------
Rung 1 chose delta per witness by reading each one's gate slack, which is not a
controller -- it is twelve hand-tuned numbers.  The rule here is pre-registered,
identical for every scenario, and computed from state the defender already has:

    delta_cmd = clip( lane_clearance_at_fire - LANE_RESERVE , 0 , DELTA_MAX )

No witness name and no escape result enters it.  LANE_RESERVE is a lane-specific
uncertainty allowance: the 10 mm budget from 1L/1M covers ATTACKER-LIMITER relative
distance and must not be silently reused here, so it is pre-registered separately.

FINE SWEEP
----------
Rung 1 used a 0.05 m grid, so "largest admissible delta" may have been a grid
artefact rather than a real boundary.  `BASE 3.2/0.50 C` (+0.0352 m of nominal lane
margin) and `BASE 4.0/0.70 C` (+0.0250 m at delta=0.05) must not be called
"radial-inward resistant" until a fine sweep has run.  The grid here is 0.005 m.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM, A_MAX, R_BODY
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import (_env, witnesses, rollout_for,
                                                   _div_seeds, DIV_BASE_SEEDS, DIAG)
from shepherd.scripts.c1_phase1p_modes import cone_components, classify, MODES
from shepherd.scripts.c1_phase1p_intervention import ring_frame, lane_clearance, LANE_MIN_M
from shepherd.scripts.c1_phase1p_6a_probe import radial_inward, ECAP_BAND
from shepherd.scripts.c1_phase1p_fullgate import vshot_static
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

# ---- pre-registered (fixed before the sweep was run) ----
DELTA_GRID = np.round(np.arange(0.0, 0.2001, 0.005), 4)
DELTA_MAX = 0.20
LANE_RESERVE_M = 0.010        # LANE-specific; NOT the 1L/1M attacker-limiter budget
KP, KD = 100.0, 20.0          # omega ~ 10 rad/s, omega*dt = 0.5 (see dynamic_inward)
MIN_LIMITER_SEP_M = 2.0 * R_BODY


def _ring_basis(P_fire):
    c0, e1, e2 = ring_frame(P_fire)
    return c0, e1, e2, np.cross(e1, e2)


def dynamic_inward(P0, Vp0, delta, n_steps=None):
    """Nominal acceleration + bounded radial correction toward the nominal path
    SHIFTED inward by `delta`, integrated with the simulator's own semi-implicit
    Euler from the TRUE fire-instant state.

    Two bugs in the first version, both caught by the review's mandated delta=0
    residual check and recorded here rather than quietly fixed:

    (1) the target was a CONSTANT radius rho0 - delta, so delta = 0 was not the
        identity -- it was a radial HOLD that fought the nominal motion.  The
        measured "re-integration residual" of 2.325 m was that hold, not an
        integration mismatch.  The target is now the nominal path shifted inward,
        so at delta = 0 the tracking error is identically zero and the family
        reduces to the nominal trajectory exactly.
    (2) KP = 400 at dt = 0.05 gives KP*dt^2 = 1.0, which is at the stability edge
        and chattered against the A_MAX clip.  Gains are now KP = 100, KD = 20
        (omega ~ 10 rad/s, omega*dt = 0.5).

    The plant convention was checked, not assumed: with the logged velocities,
    p[t+1] = p[t] + v[t+1]*dt reproduces the logged positions to 0.000000 m, while
    explicit Euler is off by 0.075 m and trapezoid by 0.0375 m.  Semi-implicit it is.
    """
    P0 = np.asarray(P0, float); Vp0 = np.asarray(Vp0, float)
    n = len(P0) if n_steps is None else min(n_steps, len(P0))
    c0, e1, e2, nrm = _ring_basis(P0[0])
    a_nom = np.zeros_like(P0)
    a_nom[:-1] = (Vp0[1:] - Vp0[:-1]) / DT
    a_nom[-1] = a_nom[-2] if len(P0) > 1 else 0.0

    # target = nominal path pushed inward by delta, in the ring frame
    def _rad(X):
        Q = X - c0
        a_, b_ = Q @ e1, Q @ e2
        rho = np.hypot(a_, b_)
        er = ((a_ / (rho + 1e-12))[:, None] * e1 + (b_ / (rho + 1e-12))[:, None] * e2)
        return rho, er
    rho_nom = np.stack([_rad(P0[s])[0] for s in range(len(P0))])
    rho_tgt_traj = np.maximum(rho_nom - delta, 1e-6)

    P = np.zeros((n, P0.shape[1], 3)); Vv = np.zeros_like(P); A = np.zeros_like(P)
    P[0] = P0[0].copy(); Vv[0] = Vp0[0].copy()               # exact continuity
    for s in range(n - 1):
        rho, er = _rad(P[s])
        rho_dot = np.einsum("ij,ij->i", Vv[s], er)
        rho_nom_dot = np.einsum("ij,ij->i", Vp0[s], er)
        u_r = KP * (rho_tgt_traj[s] - rho) + KD * (rho_nom_dot - rho_dot)
        a_cmd = a_nom[s] + u_r[:, None] * er
        nrmv = np.linalg.norm(a_cmd, axis=1, keepdims=True)
        a_cmd = np.where(nrmv > A_MAX, a_cmd * (A_MAX / (nrmv + 1e-12)), a_cmd)
        A[s] = a_cmd
        Vv[s + 1] = Vv[s] + a_cmd * DT
        P[s + 1] = P[s] + Vv[s + 1] * DT
    A[n - 1] = A[n - 2] if n > 1 else 0.0
    return P, Vv, A, (c0, e1, e2, nrm), rho_nom[0]


def admissibility(P, Vv, A, P0, Vp0, c0, e1, e2):
    """The four checks the review requires, each reported separately."""
    pos_ok = bool(np.allclose(P[0], P0[0], atol=1e-12))
    vel_ok = bool(np.allclose(Vv[0], Vp0[0], atol=1e-12))
    a_max_used = float(np.linalg.norm(A, axis=2).max())
    acc_ok = bool(a_max_used <= A_MAX + 1e-9)
    sep = np.inf
    for s in range(len(P)):
        d = np.linalg.norm(P[s][:, None, :] - P[s][None, :, :], axis=2)
        np.fill_diagonal(d, np.inf)
        sep = min(sep, float(d.min()))
    col_ok = bool(sep > MIN_LIMITER_SEP_M)
    Q = P[-1] - c0
    achieved = float(np.hypot((P0[0] - c0) @ e1, (P0[0] - c0) @ e2).mean()
                     - np.hypot(Q @ e1, Q @ e2).mean())
    return {"POSITION_CONTINUITY_PASS": pos_ok, "VELOCITY_CONTINUITY_PASS": vel_ok,
            "ACCELERATION_BOUND_PASS": acc_ok, "max_accel_used": a_max_used,
            "INTER_LIMITER_COLLISION_FREE": col_ok, "min_limiter_separation_m": sep,
            "achieved_inward_m": achieved,
            "DEFENDER_TRAJECTORY_ADMISSIBLE": bool(pos_ok and vel_ok and acc_ok and col_ok)}


def gate(pe, E, th, pa, va, pointing, P, Vp, cone, tau):
    lc = lane_clearance(P, cone, tau)
    v_r, p_r, _n = vshot_static(pa, va, pointing, P[0], E)
    e_cap = ("FAIL" if p_r <= 0 else "PASS" if v_r - th > ECAP_BAND
             else "FAIL" if th - v_r > ECAP_BAND else "E_CAP_UNRESOLVED")
    return lc, v_r, p_r, e_cap


def replan_at(pe, E, pa, va, P, Vp, cone, tau, scenario_id=None):
    """Re-optimise the attacker against a given defender trajectory.

    `scenario_id` MUST be threaded through.  The first version hard-coded the
    literal "shared" as the scenario, so every witness drew the SAME attacker
    stream -- exactly the witness-blind seeding that C-6 confirmed makes search
    diversity unmeasurable, reintroduced in a new function.  The arm name is still
    excluded (arms must face common random numbers for a paired comparison), but
    the scenario is not.
    """
    if scenario_id is None:
        raise ValueError("scenario_id is required; witness-blind streams are the C-6 defect")
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    accs = []
    for bs in DIV_BASE_SEEDS:
        for r in range(DIAG["restarts"]):
            sb, scem = _div_seeds(bs, scenario_id, "w:" + scenario_id, r)
            a1 = V.reachable_accels(E.a_att_max, DIAG["n_bank"], int(sb))
            ee, tt, pp = V._seg_paths_turn(pa, va,
                                           np.repeat(a1[:, None, :], DIAG["K"], axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
            s1 = np.minimum(kill_margin(pp, L, E.kill_radius, tau),
                            cone_exit_margin(ee, **cone))
            warm = np.repeat(a1[int(np.argmax(s1))][None, :], DIAG["K"], axis=0)
            _b, es = replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                                   kill_radius=E.kill_radius, cone_kw=cone, K=DIAG["K"],
                                   pop=DIAG["pop"], iters=DIAG["iters"],
                                   seed=int(scem), warm=warm)
            accs.extend(e["acc"] for e in es)
    n_ver = 0
    if accs:
        Aa = np.asarray(accs, float)
        ep, tf, pts = V._seg_paths_turn(pa, va, Aa, tau=tau, attacker_turn_limited=False,
                                        omega_att_max=None, e_att=None, n_t=24)
        km = kill_margin(pts, L, E.kill_radius, tau)
        lat, axi, _a, _r, _g = cone_components(ep, **cone)
        cm = np.maximum(lat, axi); keep = (np.minimum(km, cm) > 0) & tf
        if keep.any():
            A2, km2, cm2 = Aa[keep], km[keep], cm[keep]
            s2 = np.minimum(km2, cm2)
            pick = list(np.argsort(s2)[::-1][:4]) + list(np.argsort(s2)[:4])
            for i in dict.fromkeys(int(x) for x in pick):
                rr = exact_min_clearance(pa, va, A2[i], tau, L, N_LIM, DT, E.kill_radius)
                if rr["verdict"] == "VERIFIED_COLLISION_FREE" and cm2[i] > 0:
                    n_ver += 1
    return len(accs), n_ver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_6a_dynamic.json")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()
    print("== 6A rung 1.5 — oracle vs dynamic trajectory, fine delta sweep ==")
    print("   grid %.3f m | DELTA_MAX %.2f | LANE_RESERVE %.3f m | A_MAX %.1f m/s^2\n"
          % (DELTA_GRID[1], DELTA_MAX, LANE_RESERVE_M, A_MAX))

    rows = []
    for kind, tag, rho0_, tl, spec in witnesses():
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        c0, e1, e2, nrm = _ring_basis(P0[0])

        # --- (1) classify the rung-1 oracle: measure its fire-instant discontinuity
        Po, Vo = radial_inward(P0, Vp0, 0.05)
        disc_p = float(np.linalg.norm(Po[0] - P0[0], axis=1).max())
        disc_v = float(np.linalg.norm(Vo[0] - Vp0[0], axis=1).max())

        # --- (1b) RE-INTEGRATION RESIDUAL.  At delta = 0 the dynamic family should
        #          reproduce the recorded trajectory exactly.  It cannot: a_nom is
        #          recovered by finite differences of the logged velocities and then
        #          re-integrated, so a residual remains.  Any lane margin smaller than
        #          this residual is a statement about the re-integration, not about the
        #          intervention -- so it is measured before anything is read off.
        P_z, V_z, A_z, _bz, _rz = dynamic_inward(P0, Vp0, 0.0)
        reint_p = float(np.linalg.norm(P_z - P0[:len(P_z)], axis=2).max())
        reint_v = float(np.linalg.norm(V_z - Vp0[:len(V_z)], axis=2).max())

        # --- (2) fine sweep on the DYNAMIC family: gate + admissibility only
        sweep = []
        for dl in DELTA_GRID:
            P, Vv, Aa, _b, _r0 = dynamic_inward(P0, Vp0, float(dl))
            adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
            lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, o[36:45], P, Vv, cone, tau)
            ok = bool(adm["DEFENDER_TRAJECTORY_ADMISSIBLE"] and lc is not None
                      and lc >= 0.0 and e_cap != "FAIL")
            sweep.append({"delta_m": float(dl), "lane_clearance_m": lc,
                          "v_soft": v_r, "E_cap": e_cap, "gate_valid": ok, **adm})
        valid = [s for s in sweep if s["gate_valid"]]
        d_max = max((s["delta_m"] for s in valid), default=0.0)

        # --- (3) the SHARED rule, computed from state only
        lc0 = sweep[0]["lane_clearance_m"] or 0.0
        d_rule_raw = float(np.clip(lc0 - LANE_RESERVE_M, 0.0, DELTA_MAX))
        # The rule returns a CONTINUOUS value that the grid never evaluated, so it can
        # land on a gate-invalid delta.  The first version guarded only against d_max,
        # which is a grid point, and let three witnesses through with a NEGATIVE lane
        # margin.  Snap down to the largest gate-valid grid delta at or below the raw
        # rule value, and report both.
        cand = [x["delta_m"] for x in sweep if x["gate_valid"] and x["delta_m"] <= d_rule_raw]
        d_rule = float(max(cand)) if cand else 0.0

        res = {}
        for name, dl in (("gate_max", d_max), ("shared_rule", d_rule)):
            P, Vv, Aa, _b, _r0 = dynamic_inward(P0, Vp0, dl)
            adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
            lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, o[36:45], P, Vv, cone, tau)
            nc, nv = replan_at(pe, E, pa, va, P, Vv, cone, tau, scenario_id=tag)
            res[name] = {"delta_m": dl, "lane_clearance_m": lc, "v_soft": v_r,
                         "E_cap": e_cap, "n_candidates": nc, "n_verified_escape": nv,
                         **adm,
                         "outcome": ("REDISCOVERED" if nv else
                                     "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET")}
        cls = "B_GROSS_RADIAL_DISPLACEMENT" if kind == "MAXCLR" else "A_NEAR_TERMINAL_RAZOR_GAP"
        rows.append({"witness": tag, "class": kind, "failure_class": cls,
                     "oracle_discontinuity": {"position_m": disc_p, "velocity_mps": disc_v},
                     "reintegration_residual": {"position_m": reint_p,
                                                "velocity_mps": reint_v},
                     "nominal_lane_clearance_m": lc0,
                     "shared_rule_delta_raw_m": d_rule_raw,
                     "gate_valid_delta_max_m": d_max,
                     "shared_rule_delta_m": d_rule,
                     "sweep": sweep, "at": res})
        r = res["shared_rule"]; g = res["gate_max"]
        print("   %-22s %s  lane0 %+.4f  d_max %.3f  d_rule %.3f | rule: adm %s lane %+.4f esc %d "
              "| max: esc %d  a_max %.1f"
              % (tag, cls[0], lc0, d_max, d_rule,
                 "Y" if r["DEFENDER_TRAJECTORY_ADMISSIBLE"] else "N",
                 r["lane_clearance_m"], r["n_verified_escape"], g["n_verified_escape"],
                 g["max_accel_used"]), flush=True)

    A_cls = [r for r in rows if r["failure_class"].startswith("A_")]
    B_cls = [r for r in rows if r["failure_class"].startswith("B_")]
    n_rule_null = sum(1 for r in A_cls if r["at"]["shared_rule"]["n_verified_escape"] == 0)
    n_max_null = sum(1 for r in A_cls if r["at"]["gate_max"]["n_verified_escape"] == 0)
    disc = max(r["oracle_discontinuity"]["position_m"] for r in rows)
    reint = max(r["reintegration_residual"]["position_m"] for r in rows)
    print("\n   delta=0 RE-INTEGRATION residual: max %.5f m position, %.5f m/s velocity"
          % (reint, max(r["reintegration_residual"]["velocity_mps"] for r in rows)))
    print("   -> any lane margin below this is a statement about re-integration, "
          "not about the intervention")
    print("\n   rung-1 oracle fire-instant position discontinuity: max %.4f m  -> case A confirmed"
          % disc)
    print("   Class A (near-terminal razor gap) %d | Class B (gross displacement) %d"
          % (len(A_cls), len(B_cls)))
    print("   Class A nulls: shared rule %d/%d | gate-max %d/%d"
          % (n_rule_null, len(A_cls), n_max_null, len(A_cls)))
    print("   knife-edge check (lane margin at the tested delta):")
    for r in rows:
        m = r["at"]["shared_rule"]["lane_clearance_m"]
        if m is not None and m < 0.005:
            print("     %-22s %+0.4f m  <-- knife edge" % (r["witness"], m))

    out = {"meta": {"script": "c1_phase1p_6a_dynamic", "step": "6A rung 1.5",
                    "rung1_classification": "RADIAL_INWARD_GEOMETRIC_ORACLE -- the rung-1 "
                                            "family shifted the fire-instant position too, so "
                                            "the transition was never simulated (case A)",
                    "dynamic_family": "nominal acceleration + bounded radial correction, "
                                      "semi-implicit Euler from the TRUE fire-instant state",
                    "admissibility_fields": ["POSITION_CONTINUITY_PASS",
                                             "VELOCITY_CONTINUITY_PASS",
                                             "ACCELERATION_BOUND_PASS",
                                             "INTER_LIMITER_COLLISION_FREE",
                                             "DEFENDER_TRAJECTORY_ADMISSIBLE"],
                    "shared_rule": "delta = clip(lane_clearance_at_fire - LANE_RESERVE, 0, "
                                   "DELTA_MAX); no witness name and no escape result enters it",
                    "lane_reserve_m": LANE_RESERVE_M,
                    "lane_reserve_note": "LANE-specific; the 10 mm budget from 1L/1M covers "
                                         "ATTACKER-LIMITER relative distance and is not reused",
                    "rule_snapping": "the rule value is continuous; it is snapped DOWN to the "
                                     "largest gate-valid grid delta at or below it, because the "
                                     "raw value can land on an unevaluated and gate-invalid delta",
                    "delta_grid_m": float(DELTA_GRID[1]), "delta_max_m": DELTA_MAX,
                    "gains": {"kp": KP, "kd": KD}, "a_max": A_MAX,
                    "failure_classes": {"A_NEAR_TERMINAL_RAZOR_GAP": "cm-scale leak at the "
                                                                     "terminal ring",
                                        "B_GROSS_RADIAL_DISPLACEMENT": "max-clearance exploit; "
                                                                       "ring far outside"},
                    "null_meaning": "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET, not a seal",
                    "protocol": G.PROTOCOL_VERSION},
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
