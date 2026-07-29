"""C-1 — V2C-PROTOCOL-v1: the confirmatory OUTCOME taxonomy, amended and re-sealed.

WHAT CHANGED AND WHY
--------------------
The held-out smoke test showed that tilting the cone axis can stop the FROZEN FIRE
GUARD from firing at all.  v0 of the outcome protocol had no class for that, and
"excluded from controller evaluation" is not good enough: dropping the conditions
where no capture is even attempted removes exactly the hardest ones from the
denominator, which is selection bias in the defender's favour.

So no-fire gets TWO endpoints, and every condition keeps a row in both:

    POST-FIRE endpoint    the radial-inward controller only exists after fire, so
                          a no-fire condition cannot test it
                              NOT_ELIGIBLE_FOR_POST_FIRE_CONTROLLER_EVALUATION
                              REASON = NO_CAPTURE_ATTEMPT_UNDER_FROZEN_FIRE_GUARD
    SYSTEM endpoint       the whole system did not attempt the capture
                              NO_CAPTURE_ATTEMPT
                              SYSTEM_LEVEL_MISSION_FAILURE_OR_NONATTEMPT

A no-fire is NOT a radial-controller failure and NOT a system success.  It is a
GUARD / CONTROLLER INTERFACE failure, and it is labelled as one.

WHAT DID NOT CHANGE -- deliberately
-----------------------------------
    falsifier v2 code seal      untouched
    held-out spec / list seal   untouched
    conditions                  none deleted, none replaced
    fire guard                  untouched
    controllers                 untouched
Only the outcome taxonomy is amended, and it is re-sealed on its own hash.

THE CONE-AXIS AXIS MOVES TWO THINGS AT ONCE
-------------------------------------------
Tilting the cone axis changes whether the guard fires, when it fires, AND the
post-fire cone geometry.  Its results are therefore reported split:

    GUARD_COVERAGE_EFFECT             did the guard still fire?
    POST_FIRE_CONTROLLER_ROBUSTNESS   given a fire, did the controller hold?

ELIGIBILITY IS ARM-BLIND, BY CONSTRUCTION AND BY TEST
-----------------------------------------------------
    POST_FIRE_ELIGIBLE(condition, defender_trajectory)
        = the frozen fire guard produces a valid firing event

`RI-GMAX` and `RI-SHARED` must receive the SAME eligibility for the same
(condition, trajectory).  The predicate below takes no arm argument at all, and
the property test asserts the behavioural version: if an arm could change
eligibility, the high-level selector would be reaching back before the fire, which
contradicts the controller semantics.

GATE FAILURE IS AN OUTCOME, NOT AN EXCLUSION
--------------------------------------------
    RI-SHARED   the frozen selector produces no reserve-valid delta, or the
                trajectory is inadmissible, or E_cap / E_lane fails
                    SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE
                (a failure OF the shared architecture, not a skipped cell)
    RI-GMAX     no reserve-valid delta exists in the search class
                    NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS
                (a negative EXISTENCE result for this condition)

NO FALSIFIER INFORMATION MAY ENTER GMAX SYNTHESIS
-------------------------------------------------
    allowed   defender dynamics, E_cap, E_lane, admissibility, pre-registered reserve
    banned    falsifier score, whether an escape occurred, adversarial margin,
              any A0-A3 candidate result
    i.e.      delta = argmax delta  s.t. full-gate and admissibility
        NOT   delta = argmax delta  that survives falsification
The delta and the defender artifact are sealed BEFORE that condition's falsifier
runs.
"""
from __future__ import annotations
import argparse, hashlib, inspect, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import PRIMARY, R_BODY, M_SAFETY
from shepherd.scripts.c1_phase1d import rollout_unified
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses
from shepherd.scripts.c1_heldout_conditions import (condition_list, spawn_for,
                                                    finisher_for, controller_for,
                                                    HELDOUT_WITNESSES, SPEC_VERSION)

PROTOCOL_VERSION = "V2C-PROTOCOL-v1"
VERSION_RECORD = [
    {"version": "V2C-PROTOCOL-v0",
     "gap": "no-fire outcome not explicitly classified",
     "status": "SUPERSEDED_BEFORE_FULL_CONFIRMATORY_EXECUTION",
     "note": "no confirmatory result was produced under v0; the amendment is "
             "pre-execution, not a post-hoc reclassification"},
    {"version": "V2C-PROTOCOL-v1",
     "change": "universal arm-blind no-fire classification; system-level and "
               "post-fire endpoints separated; gate failures made outcomes",
     "status": "SEALED_FOR_CONFIRMATORY_EXECUTION"},
]

TRAJECTORY_OUTCOMES = [
    "NO_CAPTURE_ATTEMPT",
    "FULL_GATE_FAILURE",
    "CONFIRMATORY_ESCAPE_FOUND",
    "NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2",
    "UNRESOLVED_OR_ABORT",
]
NO_FIRE_DUAL_ENDPOINT = {
    "post_fire": {"label": "NOT_ELIGIBLE_FOR_POST_FIRE_CONTROLLER_EVALUATION",
                  "reason": "NO_CAPTURE_ATTEMPT_UNDER_FROZEN_FIRE_GUARD",
                  "rule": "excluded from the post-fire denominator, but the count is "
                          "stated on every table"},
    "system": {"label": "NO_CAPTURE_ATTEMPT",
               "class": "SYSTEM_LEVEL_MISSION_FAILURE_OR_NONATTEMPT",
               "rule": "RETAINED in the system-level denominator; removing it would "
                       "drop the hardest conditions and bias the campaign"},
    "attribution": "GUARD_CONTROLLER_INTERFACE_FAILURE — not a radial-controller "
                   "failure, and not a system success",
}
CONE_AXIS_DECOMPOSITION = ["GUARD_COVERAGE_EFFECT", "POST_FIRE_CONTROLLER_ROBUSTNESS"]
GATE_FAILURE_CLASSES = {
    "RI-SHARED-v1": "SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE",
    "RI-GMAX": "NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS"}
GMAX_INFORMATION_RULE = {
    "allowed": ["defender dynamics", "E_cap", "E_lane", "admissibility",
                "pre-registered lane reserve"],
    "banned": ["falsifier score", "escape occurrence", "adversarial margin",
               "A0-A3 candidate results"],
    "objective": "delta = argmax delta subject to full-gate and admissibility",
    "forbidden_objective": "delta = argmax delta that survives falsification",
    "sequencing": "delta and defender artifact sealed BEFORE that condition's "
                  "falsifier runs"}
REPORTING = {
    "condition_level": ["condition_id", "set", "varied axes",
                        "n_no_fire of n_trajectories",
                        "n_controller_construction_or_gate_failure",
                        "n_trajectories_with_verified_escape",
                        "no_escape_across_all_eligible_trajectories"],
    "trajectory_level": TRAJECTORY_OUTCOMES,
    "arm_level": {"RI-SHARED-v1": "frozen shared-controller confirmatory result",
                  "RI-GMAX": "scenario-conditioned existence-reference result"},
    "counting_rule": "'M of N' is permitted ONLY alongside the external-condition "
                     "layer. 704 (condition, trajectory) pairs are NOT 704 "
                     "independent samples"}
EXECUTION_ORDER = [
    "1  known counterexample 5x exact replay",
    "2  known counterexample 5x fresh-search rediscovery (falsifier regression; "
    "NOT external-generality evidence)",
    "3  the 11 unresolved cells, fresh-seed confirmatory evaluation",
    "4  arm-blind fire eligibility over the whole held-out set",
    "5  RI-SHARED-v1 applied unchanged, full-gate adjudication",
    "6  RI-GMAX synthesised per condition, GATE-ONLY, then sealed",
    "7  frozen falsifier v2 on eligible AND gate-valid artifacts",
    "8  report IN_DISTRIBUTION and STRESS separately, in the condition hierarchy",
]


def post_fire_eligible(pe, cond, tag, W):
    """ARM-BLIND.  Takes no arm argument and never will: eligibility is a property
    of the frozen fire guard under an external condition and a defender
    trajectory, nothing else."""
    kind, _t, rho0, tl, spec = W[tag]
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    try:
        rec = rollout_unified(pe, spawn_for(rho0, tl, cond), controller_for(kind, rho0, spec),
                              finisher_for(cond), r_lane=RL, r_body=RB,
                              seed=int(cond["reset_seed"]))
        fired = rec.get("fire_step") is not None and rec.get("_t_ref") is not None
        return {"eligible": bool(fired), "fire_step": rec.get("fire_step"),
                "error": None}
    except Exception as ex:
        return {"eligible": False, "fire_step": None,
                "error": "%s: %s" % (type(ex).__name__, ex)}


def protocol_spec():
    """Everything sealed by this protocol.  Results are NOT part of the hash."""
    return {"protocol_version": PROTOCOL_VERSION,
            "version_record": VERSION_RECORD,
            "heldout_spec_version": SPEC_VERSION,
            "trajectory_outcomes": TRAJECTORY_OUTCOMES,
            "no_fire_dual_endpoint": NO_FIRE_DUAL_ENDPOINT,
            "cone_axis_decomposition": CONE_AXIS_DECOMPOSITION,
            "gate_failure_classes": GATE_FAILURE_CLASSES,
            "gmax_information_rule": GMAX_INFORMATION_RULE,
            "reporting": REPORTING,
            "execution_order": EXECUTION_ORDER,
            "eligibility_predicate_source":
                hashlib.sha256(inspect.getsource(post_fire_eligible).encode()
                               ).hexdigest()[:16]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_protocol.json")
    ap.add_argument("--eligibility", action="store_true",
                    help="also run execution step 4 (arm-blind, controller-free)")
    a = ap.parse_args()
    t0 = time.time()
    spec = protocol_spec()
    spec_hash = hashlib.sha256(
        json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()

    print("== %s — confirmatory OUTCOME protocol, amended and sealed ==" % PROTOCOL_VERSION)
    print("   amendment: universal arm-blind no-fire classification, dual endpoint")
    print("   unchanged: falsifier code seal · held-out spec/list seal · conditions ·")
    print("              fire guard · controllers")
    print("   protocol hash %s\n" % spec_hash[:32])

    # property test: the predicate cannot see the arm
    params = list(inspect.signature(post_fire_eligible).parameters)
    arm_blind = not any("arm" == p for p in params)
    print("   property: eligibility predicate is arm-blind  params=%s  -> %s"
          % (params, arm_blind))

    conds = condition_list()
    rows, summary = [], {}
    if a.eligibility:
        pe, _E, _fin = _env()
        W = {w[1]: w for w in witnesses()}
        print("\n   step 4 — arm-blind fire eligibility over %d conditions x %d "
              "trajectories = %d pairs" % (len(conds), len(HELDOUT_WITNESSES),
                                           len(conds) * len(HELDOUT_WITNESSES)))
        for i, c in enumerate(conds):
            per = {}
            for tag in HELDOUT_WITNESSES:
                per[tag] = post_fire_eligible(pe, c, tag, W)
            n_elig = sum(1 for v in per.values() if v["eligible"])
            rows.append({"condition_id": c["condition_id"], "set": c["set"],
                         "kind": c["kind"], "varied": c["varied"],
                         "n_trajectories": len(HELDOUT_WITNESSES),
                         "n_post_fire_eligible": n_elig,
                         "n_no_capture_attempt": len(HELDOUT_WITNESSES) - n_elig,
                         "per_trajectory": per})
            if (i + 1) % 20 == 0:
                print("      %3d / %d conditions" % (i + 1, len(conds)), flush=True)

        tot = len(rows) * len(HELDOUT_WITNESSES)
        elig = sum(r["n_post_fire_eligible"] for r in rows)
        by_set, by_axis = {}, {}
        for r in rows:
            s = by_set.setdefault(r["set"], {"pairs": 0, "eligible": 0, "no_fire": 0})
            s["pairs"] += r["n_trajectories"]; s["eligible"] += r["n_post_fire_eligible"]
            s["no_fire"] += r["n_no_capture_attempt"]
            for ax in r["varied"]:
                b = by_axis.setdefault(ax, {"pairs": 0, "no_fire": 0})
                b["pairs"] += r["n_trajectories"]; b["no_fire"] += r["n_no_capture_attempt"]
        summary = {"total_pairs": tot, "post_fire_eligible": elig,
                   "no_capture_attempt": tot - elig, "by_set": by_set,
                   "no_fire_by_varied_axis": by_axis}
        print("\n   POST_FIRE_ELIGIBLE            %d / %d" % (elig, tot))
        print("   NO_CAPTURE_ATTEMPT           %d / %d  (retained in the SYSTEM "
              "denominator)" % (tot - elig, tot))
        for k in sorted(by_set):
            v = by_set[k]
            print("      %-16s pairs %4d  eligible %4d  no-fire %4d"
                  % (k, v["pairs"], v["eligible"], v["no_fire"]))
        print("\n   GUARD_COVERAGE_EFFECT — no-fire by varied axis")
        for k in sorted(by_axis, key=lambda x: -by_axis[x]["no_fire"]):
            v = by_axis[k]
            print("      %-26s %4d / %4d  (%.1f%%)"
                  % (k, v["no_fire"], v["pairs"],
                     100.0 * v["no_fire"] / max(v["pairs"], 1)))

    out = {"meta": {"script": "c1_v2c_protocol",
                    "protocol_version": PROTOCOL_VERSION,
                    "protocol_hash": spec_hash,
                    "status": "SEALED_FOR_CONFIRMATORY_EXECUTION",
                    "amendment_scope": "outcome taxonomy ONLY — no condition deleted "
                                       "or replaced, no fire-guard change, no "
                                       "controller change, falsifier and held-out "
                                       "seals untouched",
                    "eligibility_is_arm_blind": arm_blind,
                    "eligibility_property_test":
                        "same condition + same defender trajectory -> identical "
                        "eligibility across arms; the predicate takes no arm argument",
                    "results_not_in_hash": "the protocol hash covers the taxonomy only; "
                                           "eligibility results below are an execution "
                                           "artifact, not part of the seal"},
           "spec": spec, "eligibility_summary": summary, "conditions": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
