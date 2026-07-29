"""C-1 Phase 1P step 3 — cluster-stratified continuous-clearance audit.

WHAT STEP 2 LEFT UNRESOLVED
---------------------------
Step 2 partitioned 43,777 escapes into KILL and CONE_LATERAL using SAMPLED margins:
`kill_margin` is a min over 24 substeps per attacker segment, not over continuous
time.  A path can clear every sample and still dip inside r_kill between two of
them.  So the mode occupancy of step 2 rests on a sampled quantity, and the honest
question is whether either mode survives continuous adjudication.

The two modes are NOT equally exposed, and the asymmetry is the point:

  KILL          kill_margin BINDS.  The binding quantity is exactly the one that is
                only sampled.  Maximum exposure -- if continuous adjudication is
                going to delete a mode, this is the one.
  CONE_LATERAL  cone_exit_margin binds and is an ENDPOINT property, already exact.
                But the artifact still needs kill_margin > 0 continuously, and here
                kill_margin > cone_exit_margin > 0, so there is slack.  Lower
                exposure -- but not zero, and it is measured rather than assumed.

STRATIFIED SAMPLING (pre-registered before any adjudication was run)
--------------------------------------------------------------------
Per witness, per mode:

    N_TIGHT  artifacts with the SMALLEST binding margin      (adversarial)
    N_SPREAD artifacts at evenly spaced margin quantiles      (representative)

Tightest-first is deliberate.  This is a falsifier, so the sample is chosen to
maximise the chance of finding a failure, not to look representative.  The spread
arm exists so that a null result cannot be dismissed as "you only looked at the
knife edge".

The adjudicator is `c1_exact_clearance.exact_min_clearance` -- degree-6 d^2, roots
of its degree-5 derivative.  Its verdicts are NUMERICALLY_RESOLVED, not interval
certificates; artifacts landing in UNRESOLVED_CONTINUOUS_CLEARANCE are reported as
unresolved and are NOT counted as either outcome.

WHAT A RESULT WOULD MEAN
------------------------
  both modes survive       step 2's two-mode structure stands at continuous time;
                           step 6's intersection constraint is confirmed.
  KILL collapses           the sampled margin was hiding collisions; the surviving
                           structure is single-mode and step 6 gets easier.
  CONE_LATERAL collapses   the angular mode is a sampling artefact; 1H goes back on
                           hold and the step-2 hold-release must be retracted.

All three are reportable.  The pre-registration exists so that whichever occurs,
it was named in advance.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_phase1p_diversity import (_env, witnesses, rollout_for,
                                                   DIV_BASE_SEEDS, DIAG)
from shepherd.scripts.c1_phase1p_modes import (_artifacts, classify, MODES,
                                               UNCERTAINTY_BUDGET_M)
from shepherd.scripts import c1_governance as G

N_TIGHT, N_SPREAD = 6, 6


def select(sc_mode, n_tight=N_TIGHT, n_spread=N_SPREAD):
    """Indices into the mode's artifacts: the tightest, then spread quantiles."""
    order = np.argsort(sc_mode)
    tight = list(order[:min(n_tight, len(order))])
    if len(order) > len(tight):
        rest = order[len(tight):]
        q = np.linspace(0, len(rest) - 1, min(n_spread, len(rest))).round().astype(int)
        spread = [int(rest[i]) for i in dict.fromkeys(q.tolist())]
    else:
        spread = []
    return [int(i) for i in tight], spread


def audit_witness(pe, E, rec, scenario_id):
    d = _artifacts(pe, E, rec, scenario_id, DIV_BASE_SEEDS)
    if d is None:
        return None
    tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P = np.asarray(rec["_lim"][t:], float); Vp = np.asarray(rec["_vel"][t:], float)
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]

    A, km, cm, lat, axi = d["A"], d["km"], d["cm"], d["lat"], d["axi"]
    lab = classify(km, cm, lat, axi); sc = np.minimum(km, cm)
    per = {}
    for m in MODES:
        s = np.flatnonzero(lab == m)
        if not len(s):
            per[m] = {"occupancy": "NOT_OBSERVED"}
            continue
        ti, si = select(sc[s])
        picks = [("tight", int(s[i])) for i in ti] + [("spread", int(s[i])) for i in si]
        rows, n_free, n_coll, n_unres = [], 0, 0, 0
        for arm, idx in picks:
            r = exact_min_clearance(p_att, v_att, A[idx], tau, L, N_LIM, DT,
                                    E.kill_radius)
            v = r["verdict"]
            n_free += v == "VERIFIED_COLLISION_FREE"
            n_coll += v == "VERIFIED_COLLISION"
            n_unres += v == "UNRESOLVED_CONTINUOUS_CLEARANCE"
            rows.append({"arm": arm, "attack_policy_hash": G.attack_policy_hash(A[idx]),
                         "sampled_binding_margin_m": float(sc[idx]),
                         "sampled_kill_margin_m": float(km[idx]),
                         "cone_exit_margin_m": float(cm[idx]),
                         "exact_kill_margin_m": float(r["exact_margin_m"]),
                         "sampling_optimism_m": float(km[idx] - r["exact_margin_m"]),
                         "verdict": v,
                         "still_escape": bool(v == "VERIFIED_COLLISION_FREE"
                                              and cm[idx] > 0),
                         "above_budget": bool(min(r["exact_margin_m"], cm[idx])
                                              > UNCERTAINTY_BUDGET_M)})
        opt = [x["sampling_optimism_m"] for x in rows]
        per[m] = {"occupancy": "OBSERVED", "n_pool": int(len(s)), "n_audited": len(rows),
                  "n_verified_collision_free": int(n_free),
                  "n_verified_collision": int(n_coll),
                  "n_unresolved": int(n_unres),
                  "n_still_escape": int(sum(x["still_escape"] for x in rows)),
                  "n_still_escape_above_budget": int(sum(x["above_budget"] and
                                                         x["still_escape"] for x in rows)),
                  "sampling_optimism_m": {"min": float(min(opt)), "max": float(max(opt)),
                                          "median": float(np.median(opt))},
                  "rows": rows}
    return {"scenario_id": scenario_id, "modes": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_stratified.json")
    a = ap.parse_args()
    pe, E, fin = _env()
    ws = witnesses()
    print("== cluster-stratified continuous-clearance audit ==")
    print("   adjudicator: exact_min_clearance (degree-6 d^2, NUMERICALLY_RESOLVED)")
    print("   per witness per mode: %d tightest + %d spread\n" % (N_TIGHT, N_SPREAD))

    rows, t0 = [], time.time()
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        r = audit_witness(pe, E, rec, tag)
        if r is None:
            continue
        r["class"] = kind; rows.append(r)
        bits = []
        for m in MODES:
            pm = r["modes"][m]
            if pm["occupancy"] != "OBSERVED":
                continue
            bits.append("%s %d/%d free%s" % (m[:4], pm["n_verified_collision_free"],
                                             pm["n_audited"],
                                             (" %dcoll" % pm["n_verified_collision"])
                                             if pm["n_verified_collision"] else ""))
        print("   %-22s %s" % (tag, " | ".join(bits)), flush=True)

    agg = {}
    for m in MODES:
        obs = [r["modes"][m] for r in rows if r["modes"][m]["occupancy"] == "OBSERVED"]
        if not obs:
            agg[m] = {"occupancy_after_audit": "NOT_OBSERVED"}
            continue
        na = sum(o["n_audited"] for o in obs)
        nf = sum(o["n_verified_collision_free"] for o in obs)
        nc = sum(o["n_verified_collision"] for o in obs)
        nu = sum(o["n_unresolved"] for o in obs)
        nse = sum(o["n_still_escape"] for o in obs)
        nsb = sum(o["n_still_escape_above_budget"] for o in obs)
        wsurv = sum(1 for o in obs if o["n_still_escape"] > 0)
        wsurvb = sum(1 for o in obs if o["n_still_escape_above_budget"] > 0)
        opt = [o["sampling_optimism_m"]["max"] for o in obs]
        agg[m] = {"occupancy_after_audit": "OBSERVED" if wsurv else "COLLAPSED",
                  "witnesses_observed": len(obs),
                  "witnesses_with_surviving_escape": wsurv,
                  "witnesses_with_surviving_escape_above_budget": wsurvb,
                  "n_audited": na, "n_verified_collision_free": nf,
                  "n_verified_collision": nc, "n_unresolved": nu,
                  "n_still_escape": nse, "n_still_escape_above_budget": nsb,
                  "worst_sampling_optimism_m": float(max(opt))}

    print("\n   after continuous adjudication:")
    for m in MODES:
        g = agg[m]
        if g["occupancy_after_audit"] == "NOT_OBSERVED":
            print("     %-13s NOT_OBSERVED (nothing to audit)" % m); continue
        print("     %-13s %-10s  witnesses w/ surviving escape %2d/%2d (above budget %2d)"
              % (m, g["occupancy_after_audit"], g["witnesses_with_surviving_escape"],
                 g["witnesses_observed"], g["witnesses_with_surviving_escape_above_budget"]))
        print("       %-11s audited %3d -> free %3d / collision %3d / unresolved %3d"
              % ("", g["n_audited"], g["n_verified_collision_free"],
                 g["n_verified_collision"], g["n_unresolved"]))
        print("       %-11s worst sampling optimism (sampled - exact) %.6f m"
              % ("", g["worst_sampling_optimism_m"]))

    surviving = [m for m in MODES if agg[m].get("occupancy_after_audit") == "OBSERVED"]
    if len(surviving) >= 2:
        implication = ("both modes survive continuous adjudication -- step 2's two-mode "
                       "structure stands, and step 6's intersection constraint is confirmed")
    elif len(surviving) == 1:
        implication = ("only %s survives -- the other mode was a sampling artefact; "
                       "step 6 targets a single axis" % surviving[0])
    else:
        implication = ("no mode survives at this sample -- continuous adjudication "
                       "deletes every audited escape; re-examine before proceeding")
    print("\n   implication: %s" % implication)
    if "CONE_LATERAL" not in surviving:
        print("   !! 1H hold-release from step 2 must be RETRACTED")

    out = {"meta": {"script": "c1_phase1p_stratified",
                    "adjudicator": "c1_exact_clearance.exact_min_clearance",
                    "strength": "NUMERICALLY_RESOLVED (not an interval certificate)",
                    "sampling": "per witness per mode: %d tightest (adversarial) + %d "
                                "spread quantiles (representative)" % (N_TIGHT, N_SPREAD),
                    "why_tightest_first": "this is a falsifier; the sample maximises the "
                                          "chance of finding a failure, not "
                                          "representativeness",
                    "exposure_asymmetry": {
                        "KILL": "binding term is the SAMPLED one -- maximum exposure",
                        "CONE_LATERAL": "binding term is an exact endpoint property; "
                                        "kill_margin has slack -- lower exposure, measured"},
                    "budget_m": UNCERTAINTY_BUDGET_M,
                    "diagnostic_budget": DIAG, "protocol": G.PROTOCOL_VERSION},
           "aggregate": agg, "implication": implication, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
