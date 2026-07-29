"""C-1 Phase 1P step 6A — defender feasibility probe (rungs 0 and 1).

WHY THIS EXISTS AND WHAT CHANGED
--------------------------------
Steps 4 and 5 tested five hand-picked interventions and all five failed under
constrained replan.  The review's ruling was that this is a subset failure, not an
impossibility result, and that step 6 must become an EXISTENCE probe rather than a
minimisation.  Before opening a wide oracle it is worth asking the cheap question
first: what does the geometry actually permit?

RUNG 0 -- the geometry diagnostic
---------------------------------
Measured over the verified escape artifacts:

    attacker perpendicular distance to the net axis   0.00 - 0.59 m (median ~0.12)
    minimum distance from the attacker to any limiter 2.600 - 2.653 m
    limiter ring radius                               2.650 m
    r_kill                                            2.600 m
    lane floor (r_net_dir 2.1 + r_body 0.2 + m 0.2)   2.500 m

The escaping attacker flies essentially DOWN THE NET AXIS and rides exactly at the
kill boundary: the ring sits at 2.650 and r_kill is 2.600, so the attacker clears by
centimetres.  The lane floor is 2.500, which means there is a 0.15 m inward corridor
between where the ring is and how close it is allowed to get -- and the current
defender never uses it.  The whole system lives inside that 10-15 cm band.

RUNG 1 -- RADIAL_INWARD(delta)
------------------------------
A ONE-PARAMETER family: move every limiter radially inward by delta over the deploy
window, in the ring's own frame.  For each delta the FULL gate is enforced and the
attacker is re-optimised with the same decorrelated budget as step 5, every counted
escape re-adjudicated with the continuous adjudicator.

This is deliberately the smallest possible probe.  If a single scalar changes the
picture, the wide oracle does not need to be built to learn that the geometry is not
the obstacle.

WHAT A NULL HERE IS AND IS NOT
------------------------------
Zero verified escapes at this budget is
`NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET`, not a seal.  The ratified rule
stands: a falsifier that finds nothing proves nothing.  Confirmation needs the D0
budget and independent seeds, and that is the next step, not this one.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import (_env, witnesses, rollout_for,
                                                   _div_seeds, DIV_BASE_SEEDS, DIAG)
from shepherd.scripts.c1_phase1p_modes import cone_components, classify, MODES
from shepherd.scripts.c1_phase1p_intervention import ring_frame, lane_clearance, LANE_MIN_M
from shepherd.scripts.c1_phase1p_fullgate import vshot_static
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

DELTAS = (0.00, 0.05, 0.10, 0.15, 0.20)
ECAP_BAND = 0.0526                      # from step 5.5 calibration


def radial_inward(P0, Vp0, delta):
    """Move every limiter inward by `delta` in the ring's own frame."""
    c0, e1, e2 = ring_frame(P0[0]); nrm = np.cross(e1, e2)
    P = P0.copy()
    for s in range(len(P)):
        Q = P[s] - c0
        a_, b_, z_ = Q @ e1, Q @ e2, Q @ nrm
        rr = np.hypot(a_, b_)
        sc = np.maximum(rr - delta, 1e-9) / np.maximum(rr, 1e-9)
        P[s] = (c0 + (a_ * sc)[:, None] * e1 + (b_ * sc)[:, None] * e2
                + z_[:, None] * nrm)
    Vp = np.gradient(P, DT, axis=0) if len(P) > 2 else Vp0
    return P, Vp


def probe_delta(pe, E, th, rec, tag, delta):
    t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
    pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
    P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(pa, va, o[36:45])
    cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    tau = float(E.tau_deploy)
    P, Vp = radial_inward(P0, Vp0, delta)
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    lc = lane_clearance(P, cone, tau)
    v_r, p_r, _n = vshot_static(pa, va, o[36:45], P[0], E)
    e_cap = ("FAIL" if p_r <= 0 else
             "PASS" if v_r - th > ECAP_BAND else
             "FAIL" if th - v_r > ECAP_BAND else "E_CAP_UNRESOLVED")
    accs = []
    for bs in DIV_BASE_SEEDS:
        for r in range(DIAG["restarts"]):
            sb, scem = _div_seeds(bs, tag, "w:" + tag, r)
            a1 = V.reachable_accels(E.a_att_max, DIAG["n_bank"], int(sb))
            ee, tt, pp = V._seg_paths_turn(pa, va,
                                           np.repeat(a1[:, None, :], DIAG["K"], axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
            s1 = np.minimum(kill_margin(pp, L, E.kill_radius, tau),
                            cone_exit_margin(ee, **cone))
            warm = np.repeat(a1[int(np.argmax(s1))][None, :], DIAG["K"], axis=0)
            _b, es = replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                                   kill_radius=E.kill_radius, cone_kw=cone,
                                   K=DIAG["K"], pop=DIAG["pop"], iters=DIAG["iters"],
                                   seed=int(scem), warm=warm)
            accs.extend(e["acc"] for e in es)
    n_ver, occ = 0, []
    if accs:
        A = np.asarray(accs, float)
        ep, tf, pts = V._seg_paths_turn(pa, va, A, tau=tau, attacker_turn_limited=False,
                                        omega_att_max=None, e_att=None, n_t=24)
        km = kill_margin(pts, L, E.kill_radius, tau)
        lat, axi, _a, _r, _g = cone_components(ep, **cone)
        cm = np.maximum(lat, axi); keep = (np.minimum(km, cm) > 0) & tf
        if keep.any():
            A2, km2, cm2, lat2, axi2 = A[keep], km[keep], cm[keep], lat[keep], axi[keep]
            lab = classify(km2, cm2, lat2, axi2); s2 = np.minimum(km2, cm2)
            pick = list(np.argsort(s2)[::-1][:4]) + list(np.argsort(s2)[:4])
            for i in dict.fromkeys(int(x) for x in pick):
                rr = exact_min_clearance(pa, va, A2[i], tau, L, N_LIM, DT, E.kill_radius)
                if rr["verdict"] == "VERIFIED_COLLISION_FREE" and cm2[i] > 0:
                    n_ver += 1
                    if str(lab[i]) not in occ:
                        occ.append(str(lab[i]))
    return {"witness": tag, "delta_m": delta, "lane_clearance_m": lc,
            "E_lane": (None if lc is None else bool(lc >= 0.0)),
            "v_soft_recon": v_r, "p_feas_recon": p_r, "E_cap": e_cap,
            "n_search_candidates": len(accs), "n_verified_escape": n_ver,
            "occupied_modes": occ,
            "outcome": ("REDISCOVERED" if n_ver else
                        "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_6a_radial_inward.json")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()
    print("== step 6A rung 1 — RADIAL_INWARD(delta) ==")
    print("   lane floor %.2f m | r_kill %.2f m | ring radius ~2.65 m -> ~0.15 m corridor"
          % (LANE_MIN_M, E.kill_radius))
    print("   full gate enforced; attacker re-optimised at the step-5 diagnostic budget\n")
    print("   %-22s %-6s %-10s %-8s %-7s %-7s %s"
          % ("witness", "delta", "lane", "v_soft", "E_cap", "cands", "verified"))
    rows = []
    for kind, tag, rho0, tl, spec in witnesses():
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        for dl in DELTAS:
            r = probe_delta(pe, E, th, rec, tag, dl)
            rows.append(r)
            print("   %-22s %-6.2f %+10.4f %-8.4f %-7s %-7d %d"
                  % (tag, dl, r["lane_clearance_m"], r["v_soft_recon"], r["E_cap"],
                     r["n_search_candidates"], r["n_verified_escape"]), flush=True)

    ws = list(dict.fromkeys(r["witness"] for r in rows))
    best = {}
    for w in ws:
        adm = [r for r in rows if r["witness"] == w and r["E_lane"] and r["E_cap"] != "FAIL"]
        best[w] = max(adm, key=lambda r: r["delta_m"]) if adm else None
    n_clear = sum(1 for w in ws if best[w] and best[w]["n_verified_escape"] == 0)
    n_base = sum(1 for w in ws
                 if [r for r in rows if r["witness"] == w and r["delta_m"] == 0.0][0]
                 ["n_verified_escape"] > 0)
    print("\n   largest E_lane-admissible, E_cap-valid delta per witness:")
    for w in ws:
        b = best[w]
        print("     %-22s delta %.2f  lane %+.4f  E_cap %-5s  verified escapes %d %s"
              % (w, b["delta_m"], b["lane_clearance_m"], b["E_cap"],
                 b["n_verified_escape"], "" if b["n_verified_escape"] else "<-- none"))
    print("\n   escapes at delta=0: %d/%d witnesses" % (n_base, len(ws)))
    print("   ZERO verified escapes at the largest admissible delta: %d/%d witnesses"
          % (n_clear, len(ws)))
    print("   NOTE: zero here is NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET, NOT a seal.")

    out = {"meta": {"script": "c1_phase1p_6a_probe", "step": "6A rung 1",
                    "family": "RADIAL_INWARD(delta) -- uniform inward shift in the ring frame",
                    "geometry": {"ring_radius_m": 2.65, "r_kill_m": float(E.kill_radius),
                                 "lane_floor_m": LANE_MIN_M,
                                 "inward_corridor_m": 2.65 - LANE_MIN_M,
                                 "attacker_perp_to_axis_m": "0.00-0.59 (median ~0.12) over "
                                                            "verified escapes"},
                    "full_gate": "E_cap (band %.4f) AND E_lane enforced" % ECAP_BAND,
                    "budget": {**DIAG, "base_seeds": list(DIV_BASE_SEEDS)},
                    "null_meaning": "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET -- a "
                                    "falsifier finding nothing proves nothing; D0 budget and "
                                    "independent seeds are required for any stronger claim",
                    "protocol": G.PROTOCOL_VERSION},
           "deltas": list(DELTAS),
           "n_witnesses": len(ws),
           "n_with_escapes_at_delta0": n_base,
           "n_clear_at_best_admissible_delta": n_clear,
           "best_admissible_per_witness": {w: best[w] for w in ws},
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
