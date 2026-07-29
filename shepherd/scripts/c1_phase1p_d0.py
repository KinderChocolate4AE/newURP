"""C-1 Phase 1P — D0 on the sealed inward-offset arms.

PREFLIGHT (the review's four items, done here, no new science)
-------------------------------------------------------------
1.  LABELS.  The 9/10 and 7/10 from rung 1.5 are nulls at a small DIAGNOSTIC budget
    and must not be called "survived", which is a post-D0 word.  They are
    `DIAGNOSTIC_NULL_CANDIDATES`.  D0 input is therefore

        RI-GMAX    9 candidates
        RI-SHARED  7 candidates      (a subset of GMAX's scenarios)
        unique scenarios 9  |  arm-scenario evaluations 16

    The "20 arm-scenario" figure was the Class-A DISCOVERY table, not the D0 input.

2.  SEED NAMESPACE, CENTRALISED.  The witness-blind defect recurred because each new
    function assembled its own seed tuple.  Every stream in this module comes from
    ONE function with an explicit role, and the protocol version is bumped because
    the fix changed results:

        d0_seed(stage_id, rng_role, scenario_id, reset_id, attacker_class,
                restart_id, base_seed)

        scenario_id  ALWAYS in       arm  NEVER in (paired CRN across arms)
        stage_id     separates D0 / D1 / D2 streams
        rng_role     separates warm-start / CEM / verification streams

    The seed manifest actually used is written into the output, so "same scenario,
    different arms -> identical manifest" and "different scenarios -> different
    manifest" are checkable rather than asserted.

3.  TRACKING METRICS.  `max_tracking_error == delta` is an artefact of the reference
    stepping at the firing instant and says nothing about tracking quality, so the
    metrics the review asked for are recorded alongside it.

4.  `SHARED survives, GMAX falsified` IS NOT AUTOMATICALLY A BUG.  Gate-validity
    being an interval in delta does not make defence performance monotone in delta:
    a larger inward offset can open a gap elsewhere in the kill geometry, change the
    cone relation, increase saturation or lag.  That cell is labelled
    `NONMONOTONE_DEFENSE_RESPONSE_OR_SEARCH_VARIATION` and triggers an audit, never
    an automatic implementation-error verdict.

D0 BUDGET (pre-registered, strictly larger than the diagnostic)
---------------------------------------------------------------
    diagnostic   4 bank seeds x 2 restarts  =  8 searches
    D0           6 bank seeds x 2 restarts  = 12 searches, n_bank 20000,
                 pop 192, iters 14, K 4     (FROZEN per-search parameters)

Streams are disjoint from the diagnostic by construction (`stage_id="D0"`).

WHAT D0 SURVIVAL DOES AND DOES NOT MEAN
---------------------------------------
Survival is `SURVIVED_D0`, and the pre-registered dormant D1 fires automatically on
it.  It is not a seal, and for RI-GMAX in particular it must not be read as
practicality: that arm selects the largest reserve-valid offset, so it sits 0.3-2.4
mm above the reserve floor by construction -- `RESERVE_BOUNDARY_CONTROLLER`.
Tracking noise, actuator lag, jerk and slew limits, state-estimation error and model
mismatch are all unmodelled.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM, A_MAX
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG
from shepherd.scripts.c1_phase1p_modes import cone_components, classify, MODES
from shepherd.scripts.c1_phase1p_intervention import lane_clearance, LANE_MIN_M
from shepherd.scripts.c1_phase1p_6a_dynamic import (dynamic_inward, admissibility, gate,
                                                    _ring_basis, LANE_RESERVE_M, KP, KD)
from shepherd.scripts.c1_phase1p_6a_seal import saturation_metrics, offset_decomposition
from shepherd.scripts import c1_governance as G

D0_PROTOCOL = "c1-D0-inward-2026-07-25-v1"     # bumped: the seed fix changed results
D0 = {"stage_id": "D0", "n_bank": 20000, "bank_seeds": (1, 2, 3, 5, 8, 13),
      "restarts": 2, "K": 4, "pop": 192, "iters": 14, "base_seed": 7,
      "attacker_class": "K4-pwc", "reset_id": DIAG["reset"],
      "n_searches_per_cell": 12,
      "diagnostic_was": "4 bank seeds x 2 restarts = 8 searches"}
N_VERIFY_HI, N_VERIFY_LO = 6, 6


def d0_seed(*, stage_id, rng_role, scenario_id, reset_id, attacker_class,
            restart_id, base_seed, protocol=D0_PROTOCOL):
    """THE ONLY seed source in this module.  arm is deliberately absent."""
    h = hashlib.sha256()
    for part in (protocol, stage_id, rng_role, scenario_id, reset_id,
                 attacker_class, restart_id, base_seed):
        h.update(str(part).encode()); h.update(b"\x1f")
    return int(h.hexdigest()[:16], 16) & ((1 << 31) - 1)


def seed_manifest(scenario_id):
    return [{"bank_seed": bs, "restart": r,
             "warm": d0_seed(stage_id=D0["stage_id"], rng_role="warm_start",
                             scenario_id=scenario_id, reset_id=D0["reset_id"],
                             attacker_class=D0["attacker_class"], restart_id=r,
                             base_seed=bs),
             "cem": d0_seed(stage_id=D0["stage_id"], rng_role="cem",
                            scenario_id=scenario_id, reset_id=D0["reset_id"],
                            attacker_class=D0["attacker_class"], restart_id=r,
                            base_seed=bs)}
            for bs in D0["bank_seeds"] for r in range(D0["restarts"])]


def tracking_metrics(P, P0, delta, c0, e1, e2, n_dep):
    """`max_tracking_error == delta` is the reference step, not tracking quality."""
    def rad(X):
        Q = X - c0
        return np.hypot(Q @ e1, Q @ e2)
    rho = np.stack([rad(P[s]) for s in range(len(P))])
    rho_tgt = np.stack([rad(P0[s]) for s in range(len(P))]) - delta
    err = np.abs(rho - rho_tgt)
    dep = err[:min(n_dep + 1, len(err))]
    settle = None
    for s in range(len(err)):
        if err[s].max() <= 0.010:
            settle = float(s * DT); break
    return {"initial_reference_jump_m": float(err[0].max()),
            "max_tracking_error_m": float(err.max()),
            "max_tracking_error_after_first_control_step_m": float(err[1:].max())
            if len(err) > 1 else 0.0,
            "terminal_tracking_error_m": float(err[-1].max()),
            "rms_tracking_error_over_deployment_m": float(np.sqrt((dep ** 2).mean())),
            "settling_time_to_10mm_s": settle}


from shepherd.game import viability as V


def d0_search(E, pa, va, P, Vp, cone, tau, scenario_id):
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    accs = []
    for m in seed_manifest(scenario_id):
        a1 = V.reachable_accels(E.a_att_max, D0["n_bank"], int(m["warm"]))
        ee, tt, pp = V._seg_paths_turn(pa, va, np.repeat(a1[:, None, :], D0["K"], axis=1),
                                       tau=tau, attacker_turn_limited=False,
                                       omega_att_max=None, e_att=None, n_t=24)
        s1 = np.minimum(kill_margin(pp, L, E.kill_radius, tau),
                        cone_exit_margin(ee, **cone))
        warm = np.repeat(a1[int(np.argmax(s1))][None, :], D0["K"], axis=0)
        _b, es = replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                               kill_radius=E.kill_radius, cone_kw=cone, K=D0["K"],
                               pop=D0["pop"], iters=D0["iters"], seed=int(m["cem"]),
                               warm=warm)
        accs.extend(e["acc"] for e in es)
    if not accs:
        return {"n_search_candidates": 0, "n_verified_escape": 0, "escapes": [],
                "occupied_modes": []}
    A = np.asarray(accs, float)
    ep, tf, pts = V._seg_paths_turn(pa, va, A, tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    km = kill_margin(pts, L, E.kill_radius, tau)
    lat, axi, _a, _r, _g = cone_components(ep, **cone)
    cm = np.maximum(lat, axi); keep = (np.minimum(km, cm) > 0) & tf
    if not keep.any():
        return {"n_search_candidates": len(accs), "n_verified_escape": 0, "escapes": [],
                "occupied_modes": []}
    A2, km2, cm2, lat2, axi2 = A[keep], km[keep], cm[keep], lat[keep], axi[keep]
    lab = classify(km2, cm2, lat2, axi2); sc = np.minimum(km2, cm2)
    order = np.argsort(sc)
    pick = list(order[::-1][:N_VERIFY_HI]) + list(order[:N_VERIFY_LO])
    esc, occ = [], []
    for i in dict.fromkeys(int(x) for x in pick):
        rr = exact_min_clearance(pa, va, A2[i], tau, L, N_LIM, DT, E.kill_radius)
        ok = bool(rr["verdict"] == "VERIFIED_COLLISION_FREE" and cm2[i] > 0)
        if ok:
            esc.append({"attack_policy_hash": G.attack_policy_hash(A2[i]),
                        "acc": A2[i].tolist(), "mode": str(lab[i]),
                        "continuous_kill_margin_m": float(rr["exact_margin_m"]),
                        "cone_exit_margin_m": float(cm2[i])})
            if str(lab[i]) not in occ:
                occ.append(str(lab[i]))
    return {"n_search_candidates": len(accs), "n_verified_escape": len(esc),
            "escapes": esc, "occupied_modes": occ}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sealed", default="results/c1_corridor/c1_phase1p_6a_sealed_arms.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_d0.json")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()
    n_dep = int(round(float(E.tau_deploy) / DT))
    sealed = json.loads(pathlib.Path(a.sealed).read_text())
    by_tag = {r["witness"]: r for r in sealed["rows"]}

    cand = []
    for r in sealed["rows"]:
        if not r["failure_class"].startswith("A_"):
            continue
        for arm in ("RI-GMAX", "RI-SHARED"):
            s = r["arms"][arm]
            if s["diagnostic"]["label"] == "SURVIVED_DIAGNOSTIC_REPLAN":
                cand.append((r["witness"], arm, s["selected_delta_m"], s["artifact_hash"]))
    n_g = sum(1 for c in cand if c[1] == "RI-GMAX")
    n_s = len(cand) - n_g
    uniq = sorted({c[0] for c in cand})
    print("== D0 on the sealed inward-offset arms ==")
    print("   protocol %s" % D0_PROTOCOL)
    print("   DIAGNOSTIC_NULL_CANDIDATES  RI-GMAX %d  RI-SHARED %d" % (n_g, n_s))
    print("   unique scenarios %d   |   arm-scenario evaluations %d" % (len(uniq), len(cand)))
    print("   budget: %d bank seeds x %d restarts = %d searches (diagnostic was %s)\n"
          % (len(D0["bank_seeds"]), D0["restarts"], D0["n_searches_per_cell"],
             D0["diagnostic_was"]))

    rows = []
    for tag, arm, dl, ah in cand:
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        c0, e1, e2, nrm = _ring_basis(P0[0])
        P, Vv, Aa, _b, _r = dynamic_inward(P0, Vp0, dl)
        adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
        lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, o[36:45], P, Vv, cone, tau)
        res = d0_search(E, pa, va, P, Vv, cone, tau, tag)
        verdict = ("FALSIFIED_BY_ADVERSARIAL_REPLAN_D0" if res["n_verified_escape"]
                   else "SURVIVED_D0")
        rows.append({"witness": tag, "arm": arm, "selected_delta_m": dl,
                     "sealed_artifact_hash": ah,
                     "gate": {"lane_clearance_m": lc, "lane_reserve_excess_m":
                              (None if lc is None else float(lc - LANE_RESERVE_M)),
                              "v_soft": v_r, "E_cap": e_cap},
                     "admissibility": adm,
                     "saturation": saturation_metrics(Aa, n_dep),
                     "offset_decomposition": offset_decomposition(P, P0, dl, c0, e1, e2),
                     "tracking": tracking_metrics(P, P0, dl, c0, e1, e2, n_dep),
                     "d0": res, "verdict": verdict,
                     "seed_manifest_sha": hashlib.sha256(
                         json.dumps(seed_manifest(tag), sort_keys=True).encode()
                     ).hexdigest()[:16]})
        print("   %-22s %-10s d %.3f  cands %6d  verified %2d  -> %s"
              % (tag, arm, dl, res["n_search_candidates"], res["n_verified_escape"],
                 verdict), flush=True)

    per_arm = {}
    for arm in ("RI-GMAX", "RI-SHARED"):
        sub = [r for r in rows if r["arm"] == arm]
        surv = [r["witness"] for r in sub if r["verdict"] == "SURVIVED_D0"]
        per_arm[arm] = {"d0_input": len(sub), "survived_d0": len(surv),
                        "falsified_d0": len(sub) - len(surv), "survivors": surv}
    paired = []
    for w in uniq:
        g = next((r for r in rows if r["witness"] == w and r["arm"] == "RI-GMAX"), None)
        s = next((r for r in rows if r["witness"] == w and r["arm"] == "RI-SHARED"), None)
        if not (g and s):
            continue
        gv = g["verdict"] == "SURVIVED_D0"; sv = s["verdict"] == "SURVIVED_D0"
        cell = ("both_survived" if gv and sv else
                "gmax_only" if gv else
                "NONMONOTONE_DEFENSE_RESPONSE_OR_SEARCH_VARIATION" if sv else
                "both_falsified")
        paired.append({"witness": w, "gmax": g["verdict"], "shared": s["verdict"],
                       "cell": cell})
    new_attacks = [e for r in rows for e in r["d0"]["escapes"]]
    nonmono = [p for p in paired if p["cell"].startswith("NONMONOTONE")]

    print("\n   %-11s %-9s %-13s %-12s %s" % ("arm", "D0 input", "FALSIFIED_D0",
                                              "SURVIVED_D0", "-> D1 (auto)"))
    for arm in ("RI-GMAX", "RI-SHARED"):
        p = per_arm[arm]
        print("   %-11s %-9d %-13d %-12d %d" % (arm, p["d0_input"], p["falsified_d0"],
                                                p["survived_d0"], p["survived_d0"]))
    from collections import Counter
    print("\n   paired cells: %s" % dict(Counter(p["cell"] for p in paired)))
    if nonmono:
        print("   !! NONMONOTONE cells -> AUDIT trajectory/gate/seed parity; "
              "NOT an automatic implementation-error verdict: %s"
              % [p["witness"] for p in nonmono])
    print("   new escapes for the CEGIS attack set: %d" % len(new_attacks))
    print("\n   SURVIVED_D0 is not a seal. Dormant D1 fires automatically on it.")

    out = {"meta": {"script": "c1_phase1p_d0", "protocol": D0_PROTOCOL,
                    "budget": D0,
                    "labels": {"pre_D0": "DIAGNOSTIC_NULL_CANDIDATES (not 'survived')",
                               "post_D0": ["FALSIFIED_BY_ADVERSARIAL_REPLAN_D0",
                                           "SURVIVED_D0"],
                               "next": "dormant D1 fires automatically on SURVIVED_D0; "
                                       "SURVIVED_D0_AND_D1 -> D2a (K=8 nested)"},
                    "seed_rule": "d0_seed(stage_id, rng_role, scenario_id, reset_id, "
                                 "attacker_class, restart_id, base_seed) -- scenario ALWAYS "
                                 "in, arm NEVER in; one function is the only seed source",
                    "arm_status": {"RI-GMAX": ["SCENARIO_SPECIFIC_PREDICTIVE_INWARD_"
                                               "EXISTENCE_PROBE", "RESERVE_BOUNDARY_CONTROLLER"],
                                   "RI-SHARED": ["SHARED_PREDICTIVE_RADIAL_INWARD_SELECTOR"]},
                    "nonmonotone_note": "gate validity being an interval in delta does not make "
                                        "defence performance monotone in delta; a SHARED-only "
                                        "survival is an audit trigger, not an automatic bug",
                    "unmodelled": ["tracking noise", "actuator lag", "jerk / acceleration slew",
                                   "state-estimation error", "model mismatch"],
                    "version_history": {
                        "RI-SHARED-v0": {"seed": "witness-blind", "diagnostic": "6/10",
                                         "status": "INVALIDATED_FOR_D0_SELECTION"},
                        "RI-SHARED-v1": {"seed": "scenario-aware paired",
                                         "diagnostic": "7/10", "status": "SEALED_FOR_D0"}}},
           "d0_input": {"RI-GMAX": n_g, "RI-SHARED": n_s,
                        "unique_scenarios": len(uniq),
                        "arm_scenario_evaluations": len(cand)},
           "per_arm": per_arm, "paired": paired,
           "cegis_new_attacks": new_attacks, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
