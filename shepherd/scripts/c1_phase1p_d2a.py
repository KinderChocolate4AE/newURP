"""C-1 Phase 1P — D2a, the formal escalation: K=8 nested attacker class.

REGISTRY (Phase 1N, N4)
-----------------------
    D2a  PRE_REGISTERED_DORMANT   trigger: D1 survivor only
         K=8, NESTED (each K=4 interval halves)
         containment_test: MANDATORY
    D2b  K=6, NOT nested, exploratory only -- cannot support a survival claim

TWO GATES BEFORE ANY CELL RUNS
------------------------------
    c1_phase1p_d1_canary        -> D1_HARNESS_VALIDATED
        a null from a falsifier that cannot recognise a known escape is not evidence
    c1_phase1p_d2a_containment  -> D2A_CONTAINMENT_VERIFIED
        a wider class that cannot reproduce the narrower one's counterexamples is
        not an escalation

Both are READ and CHECKED here.  Missing or failing -> D2a refuses to run.

THE INCUMBENT SEEDING REQUIREMENT
---------------------------------
K=8 must not be allowed to look safer than K=4 merely because its search started
from scratch in a wider space.  So each cell's K=4 incumbent (the best control
its own D1 search converged on, recorded by `c1_phase1p_d1_diag`) is EMBEDDED and
used as the warm start of a dedicated block of launches.  `replan_search` puts the
warm vector in as member 0 of iteration 0, so the K=8 search provably starts no
worse than K=4 finished.  That is then asserted:

    best_objective_d2a >= k4_incumbent_objective - 1e-9

A violation is a pipeline defect, not a result, and the cell is flagged.

BUDGET -- FIXED NOW, BEFORE EXECUTION
-------------------------------------
The registry fixed D2a's K but not its counts, so they are fixed here in the same
spirit the registry stated for D1: "counts fixed now so a future survivor cannot
retro-tune the stopping point."

    K 8 · pop 384 · iters 14 · n_bank 20000
    48 bank-warm launches (16 restarts x 3 search_bank_seeds, D1's shape)
   + 8 incumbent-warm launches
   = 56 searches per cell
    pop doubles because the parameter dimension doubles (24 -> 48).

NOMENCLATURE (D1 diag): search_bank_seeds seed the reachable-accel bank;
replan_bank_seeds seed the CEM stream.  "cert seeds" is retired.

OUTPUT
------
    SURVIVED_D0_D1_D2A                   |  FALSIFIED_BY_ADVERSARIAL_REPLAN_D2A

Still scope-tagged, still not a seal:
    ATTACKER_CLASS K8_PIECEWISE_CONSTANT (nested over K4) · RESET_SCOPE FIXED_RESET_1100
    Class A only · 9 unique scenarios, not 15 independent samples
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG
from shepherd.scripts.c1_phase1p_modes import cone_components, classify
from shepherd.scripts.c1_phase1p_6a_dynamic import (dynamic_inward, admissibility, gate,
                                                    _ring_basis, LANE_RESERVE_M)
from shepherd.scripts.c1_phase1p_d0 import d0_seed
from shepherd.scripts.c1_phase1p_d2a_containment import embed
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

D2A = {"stage_id": "D2a", "K": 8, "pop": 384, "iters": 14, "n_bank": 20000,
       "restarts": 16, "n_search_bank_seeds": 3,
       "n_bank_warm_launches": 48, "n_incumbent_warm_launches": 8,
       "n_searches_per_cell": 56,
       "nesting": "NESTED over K=4: tau/8 halves tau/4",
       "counts_fixed_before_execution": True,
       "pop_rationale": "the parameter dimension doubles (24 -> 48), so pop doubles "
                        "from D1's 192",
       "d1_was": "48 searches/cell at K 4 / pop 192"}
SEARCH_BANK_IDS = (0, 1, 2)
INCUMBENT_IDS = tuple(range(D2A["n_incumbent_warm_launches"]))
N_VERIFY_HI, N_VERIFY_LO = 8, 8
MONOTONICITY_TOL_M = 1e-9

SCOPE = {"ATTACKER_CLASS": "K8_PIECEWISE_CONSTANT_NESTED_OVER_K4",
         "RESET_SCOPE": "FIXED_RESET_1100",
         "PROTOCOL": "D2A_NESTED_ESCALATION_V1",
         "SAMPLE_STRUCTURE": "controller artifacts over 9 UNIQUE scenarios — "
                             "not independent samples",
         "CLASS_SCOPE": "Class A only; Class B (MAXCLR) is a separate recovery track"}


def d2a_manifest(scenario_id):
    """Every stream this stage uses, derived from the one central seed function.
    scenario_id ALWAYS in (C-6); arm NEVER in (paired CRN across arms)."""
    sd = lambda role, r, b: d0_seed(stage_id="D2a", rng_role=role, scenario_id=scenario_id,
                                    reset_id=DIAG["reset"], attacker_class="K8-pwc",
                                    restart_id=r, base_seed=b)
    bank = [{"block": "bank_warm", "search_bank_seed_id": c, "restart": r,
             "warm": sd("warm_start", r, 2000 + c), "cem": sd("cem", r, 2000 + c)}
            for c in SEARCH_BANK_IDS for r in range(D2A["restarts"])]
    inc = [{"block": "incumbent_warm", "search_bank_seed_id": None, "restart": j,
            "warm": None, "cem": sd("cem_incumbent", j, 3000)}
           for j in INCUMBENT_IDS]
    return bank + inc


def d2a_search(E, pa, va, P, Vp, cone, tau, scenario_id, k4_incumbent):
    """K=8 CEM.  Bank-warm launches mirror D1's shape; incumbent-warm launches start
    from the embedded K=4 incumbent."""
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    K = D2A["K"]
    warm_inc = embed(k4_incumbent)
    accs, per_launch, bank_best = [], [], -np.inf
    best = {"score": -np.inf}
    for m in d2a_manifest(scenario_id):
        if m["block"] == "bank_warm":
            a1 = V.reachable_accels(E.a_att_max, D2A["n_bank"], int(m["warm"]))
            ee, tt, pp = V._seg_paths_turn(pa, va, np.repeat(a1[:, None, :], K, axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
            s1 = np.minimum(kill_margin(pp, L, E.kill_radius, tau),
                            cone_exit_margin(ee, **cone))
            j = int(np.argmax(s1)); bank_best = max(bank_best, float(s1[j]))
            warm = np.repeat(a1[j][None, :], K, axis=0)
        else:
            warm = warm_inc
        b, es = replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                              kill_radius=E.kill_radius, cone_kw=cone, K=K,
                              pop=D2A["pop"], iters=D2A["iters"], seed=int(m["cem"]),
                              warm=warm)
        accs.extend(e["acc"] for e in es)
        per_launch.append({"block": m["block"], "best_objective_m": float(b["score"])})
        if b["score"] > best["score"]:
            best = {"score": float(b["score"]), "kill_margin": float(b["kill_margin"]),
                    "cone_exit_margin": float(b["cone_exit_margin"]),
                    "acc": np.asarray(b["acc"], float), "block": m["block"]}

    adm = float(E.a_att_max - np.linalg.norm(best["acc"], axis=1).max())
    diag = {"best_search_objective_m": best["score"],
            "gap_to_candidate_threshold_m": float(-best["score"]),
            "best_admissibility_margin_mps2": adm,
            "best_kill_margin_proxy_m": best["kill_margin"],
            "best_cone_escape_proxy_m": best["cone_exit_margin"],
            "best_from_block": best["block"],
            "warm_start_bank_best_objective_m": float(bank_best),
            "per_launch_best_objective_m": per_launch}

    if not accs:
        return {"n_search_candidates": 0, "n_verified_escape": 0, "escapes": [], **diag}
    A = np.asarray(accs, float)
    ep, tf, pts = V._seg_paths_turn(pa, va, A, tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    km = kill_margin(pts, L, E.kill_radius, tau)
    lat, axi, _a, _r, _g = cone_components(ep, **cone)
    cm = np.maximum(lat, axi); keep = (np.minimum(km, cm) > 0) & tf
    if not keep.any():
        return {"n_search_candidates": len(accs), "n_verified_escape": 0,
                "escapes": [], **diag}
    A2, km2, cm2, lat2, axi2 = A[keep], km[keep], cm[keep], lat[keep], axi[keep]
    lab = classify(km2, cm2, lat2, axi2); sc = np.minimum(km2, cm2)
    order = np.argsort(sc)
    pick = list(order[::-1][:N_VERIFY_HI]) + list(order[:N_VERIFY_LO])
    esc = []
    for i in dict.fromkeys(int(x) for x in pick):
        rr = exact_min_clearance(pa, va, A2[i], tau, L, N_LIM, DT, E.kill_radius)
        if rr["verdict"] == "VERIFIED_COLLISION_FREE" and cm2[i] > 0:
            esc.append({"attack_policy_hash": G.attack_policy_hash(A2[i]),
                        "acc": A2[i].tolist(), "mode": str(lab[i]),
                        "continuous_kill_margin_m": float(rr["exact_margin_m"]),
                        "cone_exit_margin_m": float(cm2[i])})
    return {"n_search_candidates": len(accs), "n_verified_escape": len(esc),
            "escapes": esc, **diag}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d0", default="results/c1_corridor/c1_phase1p_d0.json")
    ap.add_argument("--d1", default="results/c1_corridor/c1_phase1p_d1.json")
    ap.add_argument("--diag", default="results/c1_corridor/c1_phase1p_d1_diag.json")
    ap.add_argument("--canary", default="results/c1_corridor/c1_phase1p_d1_canary.json")
    ap.add_argument("--containment",
                    default="results/c1_corridor/c1_phase1p_d2a_containment.json")
    ap.add_argument("--sealed", default="results/c1_corridor/c1_phase1p_6a_sealed_arms.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_d2a.json")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()

    can = json.loads(pathlib.Path(a.canary).read_text())
    con = json.loads(pathlib.Path(a.containment).read_text())
    print("== D2a — K=8 nested escalation ==")
    print("   gate  D1 canary      %s" % can["verdict"])
    print("   gate  D2a containment %s" % con["verdict"])
    if can["verdict"] != "D1_HARNESS_VALIDATED" or con["verdict"] != "D2A_CONTAINMENT_VERIFIED":
        print("\n   REFUSING TO RUN: a gate did not pass.")
        return 2

    d1 = json.loads(pathlib.Path(a.d1).read_text())
    diag = {(r["witness"], r["arm"]): r
            for r in json.loads(pathlib.Path(a.diag).read_text())["rows"]}
    sealed = json.loads(pathlib.Path(a.sealed).read_text())
    seal_hash = {(r["witness"], arm): r["arms"][arm]["artifact_hash"]
                 for r in sealed["rows"] for arm in ("RI-GMAX", "RI-SHARED")}
    cells = [r for r in d1["rows"] if r["verdict"] == "SURVIVED_D0_AND_D1"]
    print("   trigger: SURVIVED_D0_AND_D1 only    cells %d (GMAX %d + SHARED %d)"
          % (len(cells), sum(1 for c in cells if c["arm"] == "RI-GMAX"),
             sum(1 for c in cells if c["arm"] == "RI-SHARED")))
    print("   budget  K %d · pop %d · iters %d · %d bank-warm + %d incumbent-warm "
          "= %d searches/cell (D1 was %s)\n"
          % (D2A["K"], D2A["pop"], D2A["iters"], D2A["n_bank_warm_launches"],
             D2A["n_incumbent_warm_launches"], D2A["n_searches_per_cell"], D2A["d1_was"]))
    print("   %-22s %-10s %7s %8s %5s %12s %s"
          % ("scenario", "arm", "delta", "cands", "ver", "best obj", "verdict"))

    rows, aborted = [], []
    for c in cells:
        tag, arm, dl = c["witness"], c["arm"], c["selected_delta_m"]
        if seal_hash.get((tag, arm)) != c["sealed_artifact_hash"]:
            aborted.append({"witness": tag, "arm": arm,
                            "reason": "SEALED_ARTIFACT_HASH_MISMATCH"}); continue
        dg = diag.get((tag, arm))
        if dg is None or dg.get("k4_incumbent_acc") is None:
            aborted.append({"witness": tag, "arm": arm,
                            "reason": "NO_K4_INCUMBENT — mandated seeding unavailable"})
            print("   %-22s %-10s ABORTED: no K=4 incumbent to embed" % (tag, arm))
            continue
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        c0, e1, e2, nrm = _ring_basis(P0[0])
        P, Vv, Aa, _b, _r = dynamic_inward(P0, Vp0, dl)      # delta READ, never re-derived
        adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
        lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, o[36:45], P, Vv, cone, tau)

        inc = np.asarray(dg["k4_incumbent_acc"], float)
        res = d2a_search(E, pa, va, P, Vv, cone, tau, tag, inc)
        k4_obj = float(dg["best_search_objective_m"])
        mono = bool(res["best_search_objective_m"] >= k4_obj - MONOTONICITY_TOL_M)
        verdict = ("FALSIFIED_BY_ADVERSARIAL_REPLAN_D2A" if res["n_verified_escape"]
                   else "SURVIVED_D0_D1_D2A")
        rows.append({"witness": tag, "arm": arm, "selected_delta_m": dl,
                     "sealed_artifact_hash": c["sealed_artifact_hash"],
                     "artifact_hash_verified": True,
                     "k4_incumbent_hash": dg["k4_incumbent_hash"],
                     "k8_embedded_incumbent_hash": G.attack_policy_hash(embed(inc)),
                     "k4_incumbent_objective_m": k4_obj,
                     "nested_monotonicity_ok": mono,
                     "gate": {"lane_clearance_m": lc,
                              "lane_reserve_excess_m": (None if lc is None
                                                        else float(lc - LANE_RESERVE_M)),
                              "v_soft": v_r, "E_cap": e_cap},
                     "admissibility_still_holds": adm["DEFENDER_TRAJECTORY_ADMISSIBLE"],
                     "d2a": res, "verdict": verdict,
                     "seed_manifest_sha": hashlib.sha256(
                         json.dumps(d2a_manifest(tag), sort_keys=True).encode()
                     ).hexdigest()[:16]})
        print("   %-22s %-10s %7.3f %8d %5d %12.6f %s%s"
              % (tag, arm, dl, res["n_search_candidates"], res["n_verified_escape"],
                 res["best_search_objective_m"], verdict,
                 "" if mono else "  ** MONOTONICITY VIOLATION **"), flush=True)

    per_arm = {}
    for arm in ("RI-GMAX", "RI-SHARED"):
        sub = [r for r in rows if r["arm"] == arm]
        surv = [r["witness"] for r in sub if r["verdict"] == "SURVIVED_D0_D1_D2A"]
        per_arm[arm] = {"d2a_input": len(sub), "survived": len(surv),
                        "falsified": len(sub) - len(surv), "survivors": surv,
                        "unique_scenarios": len(set(surv))}
    bad = [r["witness"] + "/" + r["arm"] for r in rows if not r["nested_monotonicity_ok"]]
    new_attacks = [e for r in rows for e in r["d2a"]["escapes"]]
    gaps = np.asarray([r["d2a"]["gap_to_candidate_threshold_m"] for r in rows], float)

    print("\n   %-11s %-10s %-11s %-10s %s"
          % ("arm", "D2a input", "FALSIFIED", "SURVIVED", "unique scenarios"))
    for arm in ("RI-GMAX", "RI-SHARED"):
        p = per_arm[arm]
        print("   %-11s %-10d %-11d %-10d %d"
              % (arm, p["d2a_input"], p["falsified"], p["survived"], p["unique_scenarios"]))
    if len(gaps):
        print("\n   gap to threshold   min %.6f m   median %.6f m   max %.6f m"
              % (gaps.min(), np.median(gaps), gaps.max()))
    print("   nested monotonicity: %s"
          % ("all cells start no worse than their K=4 incumbent" if not bad
             else "VIOLATED in %s -- pipeline defect, not a result" % bad))
    print("   new escapes for the CEGIS attack set: %d" % len(new_attacks))
    if aborted:
        print("   ABORTED cells: %s" % aborted)

    out = {"meta": {"script": "c1_phase1p_d2a", "budget": D2A, "scope_tags": SCOPE,
                    "gates": {"d1_canary": can["verdict"], "d2a_containment": con["verdict"]},
                    "trigger": "auto-fires ONLY on SURVIVED_D0_AND_D1",
                    "invariants_enforced": {
                        "artifact_sealed_before_d0": "sealed artifact_hash re-read and "
                                                     "compared; mismatch aborts the cell",
                        "no_controller_reoptimisation": "delta READ from the D0 record",
                        "verifier_objective_dynamics_unchanged": "same exact_min_clearance, "
                                                                 "cone predicate and "
                                                                 "_seg_paths_turn",
                        "k4_incumbent_embedded": "each cell's K=4 incumbent is embedded and "
                                                 "warm-starts a dedicated launch block",
                        "nested_monotonicity_asserted":
                            "best_objective_d2a >= k4_incumbent_objective - 1e-9"},
                    "budget_phrasing": "D2a widens the attacker CLASS (K4 -> K8, nested) and "
                                       "raises launches to 56/cell; K8 contains K4",
                    "not_a_seal": True},
           "per_arm": per_arm, "aborted": aborted,
           "monotonicity_violations": bad,
           "gap_summary_m": ({"min": float(gaps.min()), "median": float(np.median(gaps)),
                              "max": float(gaps.max())} if len(gaps) else None),
           "cegis_new_attacks": new_attacks, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
