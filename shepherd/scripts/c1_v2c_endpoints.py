"""C-1 — V2C-PROTOCOL-v2: three endpoints, and no-fire is not automatically a failure.

WHAT v1 GOT WRONG
-----------------
v1 classified every no-fire as `SYSTEM_LEVEL_MISSION_FAILURE_OR_NONATTEMPT`.  That
conflates two different things.  `NO_CAPTURE_ATTEMPT` is an observation -- the
frozen guard produced no firing event.  Whether that is a MISSION failure depends
on what the attacker then did, which v1 never looked at.

    no fire  +  attacker penetrated          -> MISSION_FAILURE_NO_ENGAGEMENT
    no fire  +  attacker contained anyway    -> MISSION_SUCCESS_WITHOUT_CAPTURE
    no fire  +  outcome not evaluable        -> SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED

The default mechanical label is therefore
    NO_CAPTURE_ATTEMPT + FIRE_GUARD_COVERAGE_FAILURE
`GUARD_CONTROLLER_INTERFACE_FAILURE` stays as the ARCHITECTURE reading, not as the
mechanical cause.

v1's eligibility numbers are untouched: the predicate did not change, and this
module re-derives them rather than copying, so a drift would show.

THREE ENDPOINTS
---------------
    A  guard coverage        does the frozen guard start a capture attempt?
    B  conditional post-fire  given a fire, does the controller hold?   [steps 5-7]
    C  end-to-end mission     did the system achieve the mission?
A and C are produced here.  B needs the controller runs and is not touched.

MAIN EFFECTS AND INTERACTIONS ARE SEPARATED
-------------------------------------------
The v1 readout printed no-fire counts grouped by "varied axis", which double-counts
every crossed condition into both of its axes.  That number cannot be read as a
causal contribution.  Here:
    main effect    OFAT rows only, per axis and per value
    interaction    CROSSED rows only, reported as its own table
and no combined "x% of failures were caused by lateral" statement is produced.

RATE SEMANTICS
--------------
307/704 is a PAIR-WEIGHTED ELIGIBILITY RATE ON A SEALED GRID.  It is not an
operational firing probability, and the module says so in its own output so the
number cannot travel without the caveat.
"""
from __future__ import annotations
import argparse, collections, hashlib, inspect, json, pathlib, time

from shepherd.scripts.c1_response_probe import PRIMARY, R_BODY, M_SAFETY
from shepherd.scripts.c1_phase1d import rollout_unified
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses
from shepherd.scripts.c1_heldout_conditions import (condition_list, spawn_for,
                                                    finisher_for, controller_for,
                                                    HELDOUT_WITNESSES)

PROTOCOL_VERSION = "V2C-PROTOCOL-v2"
VERSION_RECORD = [
    {"version": "V2C-PROTOCOL-v1",
     "gap": "every no-fire was labelled a system-level mission failure or nonattempt, "
            "without checking what the attacker actually did",
     "status": "SUPERSEDED_BEFORE_CONTROLLER_EXECUTION",
     "preserved": "its arm-blind eligibility result is unchanged and re-derived here"},
    {"version": "V2C-PROTOCOL-v2",
     "change": "no-fire default label is NO_CAPTURE_ATTEMPT + FIRE_GUARD_COVERAGE_FAILURE; "
               "mission outcome split three ways; endpoints A/B/C separated; main "
               "effects (OFAT) and interactions (CROSSED) reported apart",
     "status": "SEALED_FOR_CONFIRMATORY_EXECUTION"},
]

NO_FIRE_LABELS = {
    "mechanical": ["NO_CAPTURE_ATTEMPT", "FIRE_GUARD_COVERAGE_FAILURE"],
    "architecture_reading": "GUARD_CONTROLLER_INTERFACE_FAILURE",
    "not_automatic": "NO_CAPTURE_ATTEMPT does NOT by itself imply MISSION_FAILURE"}
MISSION_CLASSES = ["MISSION_FAILURE_NO_ENGAGEMENT",
                   "MISSION_SUCCESS_WITHOUT_CAPTURE",
                   "SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED"]
COVERAGE_CLASSES = {"ZERO_GUARD_COVERAGE": "0/8 trajectories eligible",
                    "PARTIAL_GUARD_COVERAGE": "1-7/8 eligible",
                    "FULL_GUARD_COVERAGE": "8/8 eligible"}
RATE_SEMANTICS = ("pair-weighted eligibility rate on the sealed held-out grid; "
                  "NOT an operational firing probability")
CLASS_C = {"name": "PRE_FIRE_GUARD_COVERAGE_FAILURE",
           "relation": "a third failure class alongside Class A (near-terminal razor "
                       "gap) and Class B (gross radial displacement)",
           "not_fixable_by": "the radial-inward controller — it does not exist "
                             "before the fire",
           "future_degrees_of_freedom_NOT_TOUCHED_IN_THIS_CAMPAIGN": [
               "lateral-aware fire guard",
               "consistency between cone axis and the firing predicate",
               "fire timing / coverage redesign",
               "joint guard + post-fire controller design",
               "pre-fire shepherding to bring the attacker inside guard coverage"]}


def mission_outcome(rec):
    """Endpoint C for a no-fire pair.  Reads the rollout's own flags; invents nothing."""
    pen = bool(rec.get("penetrated"))
    safe = bool(rec.get("safe"))
    if pen:
        return "MISSION_FAILURE_NO_ENGAGEMENT"
    if safe:
        return "MISSION_SUCCESS_WITHOUT_CAPTURE"
    return "SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", default="results/c1_corridor/c1_v2c_protocol.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_endpoints.json")
    a = ap.parse_args()
    pe, _E, _fin = _env(); t0 = time.time()
    W = {w[1]: w for w in witnesses()}
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    conds = condition_list()
    spec = {"protocol_version": PROTOCOL_VERSION, "version_record": VERSION_RECORD,
            "no_fire_labels": NO_FIRE_LABELS, "mission_classes": MISSION_CLASSES,
            "coverage_classes": COVERAGE_CLASSES, "rate_semantics": RATE_SEMANTICS,
            "class_C": CLASS_C,
            "mission_outcome_source": hashlib.sha256(
                inspect.getsource(mission_outcome).encode()).hexdigest()[:16]}
    spec_hash = hashlib.sha256(
        json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()

    print("== %s — endpoints A and C ==" % PROTOCOL_VERSION)
    print("   no-fire default label: NO_CAPTURE_ATTEMPT + FIRE_GUARD_COVERAGE_FAILURE")
    print("   mission outcome is checked, not assumed")
    print("   protocol hash %s\n" % spec_hash[:32])

    rows = []
    for i, c in enumerate(conds):
        per = {}
        for tag in HELDOUT_WITNESSES:
            kind, _t, rho0, tl, spec_w = W[tag]
            try:
                rec = rollout_unified(pe, spawn_for(rho0, tl, c),
                                      controller_for(kind, rho0, spec_w),
                                      finisher_for(c), r_lane=RL, r_body=RB,
                                      seed=int(c["reset_seed"]))
                elig = (rec.get("fire_step") is not None
                        and rec.get("_t_ref") is not None)
                per[tag] = {"eligible": bool(elig), "fire_step": rec.get("fire_step"),
                            "tier": rec.get("tier"), "penetrated": bool(rec.get("penetrated")),
                            "safe": bool(rec.get("safe")),
                            "mission_outcome": (None if elig else mission_outcome(rec))}
            except Exception as ex:
                per[tag] = {"eligible": False, "fire_step": None, "tier": None,
                            "penetrated": None, "safe": None,
                            "mission_outcome": "SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED",
                            "error": "%s: %s" % (type(ex).__name__, ex)}
        n_e = sum(1 for v in per.values() if v["eligible"])
        cov = ("ZERO_GUARD_COVERAGE" if n_e == 0
               else "FULL_GUARD_COVERAGE" if n_e == len(HELDOUT_WITNESSES)
               else "PARTIAL_GUARD_COVERAGE")
        rows.append({"condition_id": c["condition_id"], "set": c["set"], "kind": c["kind"],
                     "varied": c["varied"],
                     "values": {k: c[k] for k in c["varied"]},
                     "n_post_fire_eligible": n_e,
                     "n_no_capture_attempt": len(HELDOUT_WITNESSES) - n_e,
                     "guard_coverage_class": cov, "per_trajectory": per})
        if (i + 1) % 20 == 0:
            print("   %3d / %d conditions" % (i + 1, len(conds)), flush=True)

    tot = len(rows) * len(HELDOUT_WITNESSES)
    elig = sum(r["n_post_fire_eligible"] for r in rows)
    # endpoint A -- re-derived, then compared with v1
    v1 = json.loads(pathlib.Path(a.v1).read_text())
    v1_elig = v1["eligibility_summary"]["post_fire_eligible"]
    print("\n   ENDPOINT A — guard coverage")
    print("      POST_FIRE_ELIGIBLE  %d / %d   (%s)" % (elig, tot, RATE_SEMANTICS))
    print("      NO_CAPTURE_ATTEMPT  %d / %d" % (tot - elig, tot))
    print("      v1 re-derivation check: v1=%d  v2=%d  %s"
          % (v1_elig, elig, "MATCH" if v1_elig == elig else "DRIFT"))

    cov = collections.defaultdict(collections.Counter)
    for r in rows:
        cov[r["set"]][r["guard_coverage_class"]] += 1
    print("\n   condition-level coverage (the headline 397/704 hides this)")
    print("      %-16s %6s %8s %6s" % ("set", "0/8", "1-7/8", "8/8"))
    for s in sorted(cov):
        k = cov[s]
        print("      %-16s %6d %8d %6d"
              % (s, k["ZERO_GUARD_COVERAGE"], k["PARTIAL_GUARD_COVERAGE"],
                 k["FULL_GUARD_COVERAGE"]))

    mis = collections.Counter()
    mis_by_set = collections.defaultdict(collections.Counter)
    for r in rows:
        for v in r["per_trajectory"].values():
            if not v["eligible"]:
                mis[v["mission_outcome"]] += 1
                mis_by_set[r["set"]][v["mission_outcome"]] += 1
    print("\n   ENDPOINT C — what happened in the %d no-fire pairs" % (tot - elig))
    for k in MISSION_CLASSES:
        print("      %-38s %4d" % (k, mis[k]))
    for s in sorted(mis_by_set):
        print("      %-16s %s" % (s, dict(mis_by_set[s])))

    # main effects: OFAT rows only
    main = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for r in rows:
        if r["kind"] != "OFAT":
            continue
        ax = r["varied"][0]; val = r["values"][ax]
        m = main[ax][val]
        m[0] += r["n_no_capture_attempt"]; m[1] += len(HELDOUT_WITNESSES)
    print("\n   MAIN EFFECTS (OFAT rows only — crossed rows are NOT pooled in here)")
    for ax in sorted(main):
        vals = ", ".join("%s:%d/%d" % (v, main[ax][v][0], main[ax][v][1])
                         for v in sorted(main[ax], key=float))
        print("      %-20s %s" % (ax, vals))

    inter = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["kind"] != "CROSSED":
            continue
        k = " x ".join(r["varied"])
        inter[k][0] += r["n_no_capture_attempt"]; inter[k][1] += len(HELDOUT_WITNESSES)
    print("\n   INTERACTIONS (CROSSED rows only, reported separately)")
    for k in sorted(inter):
        print("      %-34s %4d / %4d" % (k, inter[k][0], inter[k][1]))

    print("\n   NOTE: no statement of the form 'x%% of failures were caused by <axis>' "
          "is produced.\n         Grouped axis rates double-count crossed conditions.")

    out = {"meta": {"script": "c1_v2c_endpoints", "protocol_version": PROTOCOL_VERSION,
                    "protocol_hash": spec_hash,
                    "status": "SEALED_FOR_CONFIRMATORY_EXECUTION",
                    "supersedes": "V2C-PROTOCOL-v1 (no-fire mission classification)",
                    "endpoint_A_rate_semantics": RATE_SEMANTICS,
                    "endpoint_B": "conditional post-fire controller result — steps 5-7, "
                                  "NOT produced here",
                    "conditional_reporting_rule":
                        "post-fire results are conditional on a self-selected eligible "
                        "subset; in STRESS only a minority of sealed pairs reach the "
                        "controller at all. Arm-vs-arm comparison WITHIN eligible pairs "
                        "is fair because eligibility is arm-blind; generalising the "
                        "eligible subset to all conditions is not",
                    "no_causal_attribution_from_grouped_rates": True},
           "spec": spec,
           "endpoint_A": {"total_pairs": tot, "post_fire_eligible": elig,
                          "no_capture_attempt": tot - elig,
                          "v1_rederivation_match": bool(v1_elig == elig),
                          "condition_coverage_classes":
                              {s: dict(cov[s]) for s in cov}},
           "endpoint_C_no_fire_mission": {"overall": dict(mis),
                                          "by_set": {s: dict(mis_by_set[s])
                                                     for s in mis_by_set}},
           "main_effects_ofat_only": {ax: {str(v): main[ax][v] for v in main[ax]}
                                      for ax in main},
           "interactions_crossed_only": {k: inter[k] for k in inter},
           "conditions": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
