"""C-1 Phase 1P — D1, the pre-registered dormant escalation.

TRIGGER AND INVARIANTS (from the Phase 1M escalation registry, unchanged)
------------------------------------------------------------------------
D1 auto-fires ONLY on a controller-scenario with ZERO verified escapes at D0.  Its
invariants, all enforced and checked here rather than trusted:

    controller artifact and all settings sealed BEFORE D0
        -> the sealed artifact_hash from 6A is re-read and compared; a mismatch
           aborts the cell instead of silently re-deriving
    no controller re-optimisation inside D1
        -> delta is READ from the D0 record.  Nothing in this module can change it
    verifier, objective and attacker dynamics unchanged
        -> the same exact_min_clearance / cone predicate / _seg_paths_turn as D0

BUDGET
------
The registry fixed the COUNTS: K 4, pop 192, iters 14, restarts 16, 3 cert seeds,
n_cert 20000 -- 48 searches per cell, four times D0's 12.  "counts fixed now so a
future survivor cannot retro-tune the stopping point" is the registry's own wording.

SEED VALUES ARE DERIVED, NOT COPIED
-----------------------------------
The registry also listed literal seed constants (64000201-16, 91000101-3).  Those
predate C-6 and are witness-blind: reusing them verbatim would hand every scenario
the same attacker stream, which is the defect this campaign confirmed twice and hit
again in `replan_at` last round.  So the registry's COUNTS are honoured exactly and
the seed VALUES come from the same central function D0 used, with `stage_id="D1"`
so the streams are disjoint from D0's.  This is a deliberate, recorded deviation
from the literal registry text in favour of its intent.

OUTPUTS
-------
    SURVIVED_D0_AND_D1                  -> eligible for D2a (K=8 nested)
    FALSIFIED_BY_ADVERSARIAL_REPLAN_D1  -> escapes join the CEGIS attack set

Neither is a seal.
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
from shepherd.scripts.c1_phase1p_intervention import lane_clearance, LANE_MIN_M
from shepherd.scripts.c1_phase1p_6a_dynamic import (dynamic_inward, admissibility, gate,
                                                    _ring_basis, LANE_RESERVE_M)
from shepherd.scripts.c1_phase1p_d0 import d0_seed, D0_PROTOCOL
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

D1 = {"stage_id": "D1", "K": 4, "pop": 192, "iters": 14,
      "restarts": 16, "n_cert_seeds": 3, "n_bank": 20000,
      "n_searches_per_cell": 48,
      "registry_counts": "K 4 / pop 192 / iters 14 / restarts 16 / cert seeds 3 / n_cert 20000",
      "d0_was": "6 bank seeds x 2 restarts = 12 searches",
      "seed_deviation": "registry seed CONSTANTS (64000201-16, 91000101-3) are witness-blind "
                        "and predate C-6; the COUNTS are honoured exactly, the VALUES are "
                        "derived from the central d0_seed with stage_id='D1'"}
N_VERIFY_HI, N_VERIFY_LO = 8, 8
CERT_BANK_IDS = (0, 1, 2)


def d1_manifest(scenario_id):
    return [{"cert_id": c, "restart": r,
             "warm": d0_seed(stage_id="D1", rng_role="warm_start", scenario_id=scenario_id,
                             reset_id=DIAG["reset"], attacker_class="K4-pwc",
                             restart_id=r, base_seed=1000 + c),
             "cem": d0_seed(stage_id="D1", rng_role="cem", scenario_id=scenario_id,
                            reset_id=DIAG["reset"], attacker_class="K4-pwc",
                            restart_id=r, base_seed=1000 + c)}
            for c in CERT_BANK_IDS for r in range(D1["restarts"])]


def d1_search(E, pa, va, P, Vp, cone, tau, scenario_id):
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    accs = []
    for m in d1_manifest(scenario_id):
        a1 = V.reachable_accels(E.a_att_max, D1["n_bank"], int(m["warm"]))
        ee, tt, pp = V._seg_paths_turn(pa, va, np.repeat(a1[:, None, :], D1["K"], axis=1),
                                       tau=tau, attacker_turn_limited=False,
                                       omega_att_max=None, e_att=None, n_t=24)
        s1 = np.minimum(kill_margin(pp, L, E.kill_radius, tau),
                        cone_exit_margin(ee, **cone))
        warm = np.repeat(a1[int(np.argmax(s1))][None, :], D1["K"], axis=0)
        _b, es = replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                               kill_radius=E.kill_radius, cone_kw=cone, K=D1["K"],
                               pop=D1["pop"], iters=D1["iters"], seed=int(m["cem"]),
                               warm=warm)
        accs.extend(e["acc"] for e in es)
    if not accs:
        return {"n_search_candidates": 0, "n_verified_escape": 0, "escapes": []}
    A = np.asarray(accs, float)
    ep, tf, pts = V._seg_paths_turn(pa, va, A, tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    km = kill_margin(pts, L, E.kill_radius, tau)
    lat, axi, _a, _r, _g = cone_components(ep, **cone)
    cm = np.maximum(lat, axi); keep = (np.minimum(km, cm) > 0) & tf
    if not keep.any():
        return {"n_search_candidates": len(accs), "n_verified_escape": 0, "escapes": []}
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
    return {"n_search_candidates": len(accs), "n_verified_escape": len(esc), "escapes": esc}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d0", default="results/c1_corridor/c1_phase1p_d0.json")
    ap.add_argument("--sealed", default="results/c1_corridor/c1_phase1p_6a_sealed_arms.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_d1.json")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()
    d0 = json.loads(pathlib.Path(a.d0).read_text())
    sealed = json.loads(pathlib.Path(a.sealed).read_text())
    seal_hash = {(r["witness"], arm): r["arms"][arm]["artifact_hash"]
                 for r in sealed["rows"] for arm in ("RI-GMAX", "RI-SHARED")}
    cells = [r for r in d0["rows"] if r["verdict"] == "SURVIVED_D0"]

    print("== D1 — pre-registered dormant escalation ==")
    print("   trigger: SURVIVED_D0 only    cells %d (GMAX %d + SHARED %d)"
          % (len(cells), sum(1 for c in cells if c["arm"] == "RI-GMAX"),
             sum(1 for c in cells if c["arm"] == "RI-SHARED")))
    print("   budget %s = %d searches/cell (D0 was %s)"
          % (D1["registry_counts"], D1["n_searches_per_cell"], D1["d0_was"]))
    print("   seeds derived centrally with stage_id='D1' (registry constants are "
          "witness-blind; counts honoured, values derived)\n")

    rows, aborted = [], []
    for c in cells:
        tag, arm, dl = c["witness"], c["arm"], c["selected_delta_m"]
        if seal_hash.get((tag, arm)) != c["sealed_artifact_hash"]:
            aborted.append({"witness": tag, "arm": arm,
                            "reason": "SEALED_ARTIFACT_HASH_MISMATCH"})
            print("   %-22s %-10s ABORTED: sealed artifact hash mismatch" % (tag, arm))
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
        res = d1_search(E, pa, va, P, Vv, cone, tau, tag)
        verdict = ("FALSIFIED_BY_ADVERSARIAL_REPLAN_D1" if res["n_verified_escape"]
                   else "SURVIVED_D0_AND_D1")
        rows.append({"witness": tag, "arm": arm, "selected_delta_m": dl,
                     "sealed_artifact_hash": c["sealed_artifact_hash"],
                     "artifact_hash_verified": True,
                     "gate": {"lane_clearance_m": lc,
                              "lane_reserve_excess_m": (None if lc is None
                                                        else float(lc - LANE_RESERVE_M)),
                              "v_soft": v_r, "E_cap": e_cap},
                     "admissibility_still_holds": adm["DEFENDER_TRAJECTORY_ADMISSIBLE"],
                     "d1": res, "verdict": verdict,
                     "seed_manifest_sha": hashlib.sha256(
                         json.dumps(d1_manifest(tag), sort_keys=True).encode()
                     ).hexdigest()[:16]})
        print("   %-22s %-10s d %.3f  cands %7d  verified %2d  -> %s"
              % (tag, arm, dl, res["n_search_candidates"], res["n_verified_escape"],
                 verdict), flush=True)

    per_arm = {}
    for arm in ("RI-GMAX", "RI-SHARED"):
        sub = [r for r in rows if r["arm"] == arm]
        surv = [r["witness"] for r in sub if r["verdict"] == "SURVIVED_D0_AND_D1"]
        per_arm[arm] = {"d1_input": len(sub), "survived_d0_and_d1": len(surv),
                        "falsified_d1": len(sub) - len(surv), "survivors": surv,
                        "d2a_eligible": len(surv)}
    new_attacks = [e for r in rows for e in r["d1"]["escapes"]]
    print("\n   %-11s %-9s %-14s %-20s %s"
          % ("arm", "D1 input", "FALSIFIED_D1", "SURVIVED_D0_AND_D1", "-> D2a"))
    for arm in ("RI-GMAX", "RI-SHARED"):
        p = per_arm[arm]
        print("   %-11s %-9d %-14d %-20d %d"
              % (arm, p["d1_input"], p["falsified_d1"], p["survived_d0_and_d1"],
                 p["d2a_eligible"]))
    print("\n   new escapes for the CEGIS attack set: %d" % len(new_attacks))
    if aborted:
        print("   ABORTED cells: %s" % aborted)
    print("   SURVIVED_D0_AND_D1 is still not a seal; D2a (K=8 nested) is next.")

    out = {"meta": {"script": "c1_phase1p_d1", "protocol": D0_PROTOCOL, "budget": D1,
                    "trigger": "auto-fires ONLY on SURVIVED_D0",
                    "invariants_enforced": {
                        "artifact_sealed_before_d0": "sealed artifact_hash re-read from 6A and "
                                                     "compared; mismatch aborts the cell",
                        "no_controller_reoptimisation": "delta is READ from the D0 record",
                        "verifier_objective_dynamics_unchanged": "same exact_min_clearance, "
                                                                 "cone predicate and "
                                                                 "_seg_paths_turn as D0"},
                    "outputs": ["SURVIVED_D0_AND_D1", "FALSIFIED_BY_ADVERSARIAL_REPLAN_D1"],
                    "not_a_seal": True},
           "per_arm": per_arm, "aborted": aborted,
           "cegis_new_attacks": new_attacks, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
