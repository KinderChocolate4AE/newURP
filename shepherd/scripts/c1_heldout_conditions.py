"""C-1 — held-out EXTERNAL condition set: generated, sealed, not yet evaluated.

WHY EXTERNAL, AND WHY NOW
-------------------------
Every result so far sits under ONE attacker boundary condition and ONE net cone
geometry; only the defender trajectory varied.  Adding more defender trajectories
cannot widen that -- the shared attacker condition is the binding constraint.  So
the confirmatory campaign has to change the OUTSIDE, and the condition list has to
be fixed before any of it is scored, or the conditions become another tunable.

THE FIVE AXES
-------------
    attacker_lateral_offset_m   attacker spawn displaced off the boresight
    attacker_heading_deg        incoming velocity rotated
    attacker_speed_mps          closing speed scaled
    cone_axis_deg               finisher pointing tilted -> net cone axis moves
    reset_seed                  a different rollout realisation entirely

TWO SETS, NEVER MERGED
----------------------
    IN_DISTRIBUTION   small perturbations around nominal.  Asks: does the
                      controller generalise locally?
    STRESS            deliberately larger, aimed at the thin near-saturation
                      basin and the lane floor.  Asks: where does it break?
Merging them would let easy conditions dilute hard ones into one success rate.

OFAT IS NOT ENOUGH
------------------
One-factor-at-a-time misses interactions, and the escape basins here are thin
enough that interactions are exactly where the risk is.  Each set therefore
carries CROSSED conditions as well:

    lateral x heading      speed x cone orientation      reset x lateral

THE TWO ARMS ARE NOT THE SAME OBJECT
------------------------------------
    RI-SHARED-v1   a shared predictive selector.  It APPLIES to a new condition
                   unchanged -- controller, reserve, delta rule and PD gains all
                   frozen.  This is the thing being confirmed.
                       PRIMARY_CONFIRMATORY_CONTROLLER
    RI-GMAX        re-searches the maximum reserve-valid delta per condition.
                   Re-running that search on a new condition is not the same
                   controller generalising, it is a NEW synthesis for that
                   condition.
                       SCENARIO_CONDITIONED_EXISTENCE_REFERENCE
                   Allowed question:  does an admissible inward controller
                                      artifact EXIST here?
                   Not allowed:       does RI-GMAX generalise here?
Their results must never share a success-rate table.

REPORTING HIERARCHY
-------------------
    external condition
      └─ defender trajectory
          └─ controller arm
Several defender trajectories under one external condition are NOT independent
samples, so "M of N cells" alone is not a permitted summary.

WHAT THIS MODULE DOES AND DOES NOT DO
-------------------------------------
DOES    generate the condition list deterministically, hash it, and run a
        FEASIBILITY smoke test (does the rollout fire at all?).
DOES NOT evaluate any controller, run any falsifier, or produce any survival
        label.  The smoke test touches no controller and no attacker search.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, N_LIM, X_FIRE, V_CLOSE,
                                                THETA, R_BODY, M_SAFETY, PRIMARY)
from shepherd.scripts.c1_corridor_probe import make_finisher_fn
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_plant_bound import solve_witness_hold, solve_witness, make_lp_arm
from shepherd.scripts.c1_response_probe import make_contract, make_pd
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses

SPEC_VERSION = "HELDOUT-EXTERNAL-v1-2026-07-26"
NOMINAL = {"lateral_offset_m": 0.0, "heading_deg": 0.0, "speed_mps": V_CLOSE,
           "cone_axis_deg": 0.0, "reset_seed": 1100}

IN_DIST = {"lateral_offset_m": [0.25, -0.25, 0.50, -0.50],
           "heading_deg": [1.0, -1.0, 2.0, -2.0],
           "speed_mps": [18.0, 22.0],
           "cone_axis_deg": [0.5, -0.5, 1.0],
           "reset_seed": [1101, 1102, 1103]}
STRESS = {"lateral_offset_m": [1.5, -1.5, 3.0],
          "heading_deg": [6.0, -6.0, 10.0],
          "speed_mps": [14.0, 26.0, 30.0],
          "cone_axis_deg": [3.0, -3.0, 6.0],
          "reset_seed": [1201, 1202]}
CROSSES = [("lateral_offset_m", "heading_deg"),
           ("speed_mps", "cone_axis_deg"),
           ("reset_seed", "lateral_offset_m")]

# the defender trajectories carried into the held-out campaign: the 11 unresolved
# cells' witnesses, de-duplicated.  Frozen here so the trajectory set cannot be
# reshuffled after the fact either.
HELDOUT_WITNESSES = ["RH 2.8/0.15 f=2", "RH 3.2/0.25 f=5", "BASE 2.8/0.30 C",
                     "BASE 3.2/0.50 C", "BASE 3.2/0.70 P", "BASE 4.0/0.70 C",
                     "BASE 4.0/0.70 P", "BASE 5.0/1.00 P"]

ARM_ROLES = {
    "RI-SHARED-v1": {"role": "PRIMARY_CONFIRMATORY_CONTROLLER",
                     "application": "applied UNCHANGED — controller, lane reserve, "
                                    "delta-selection rule and PD gains all frozen",
                     "question": "does the shared selector generalise to this condition?"},
    "RI-GMAX": {"role": "SCENARIO_CONDITIONED_EXISTENCE_REFERENCE",
                "application": "delta is RE-SEARCHED per condition — a new synthesis, "
                               "not a generalisation",
                "question": "does an admissible inward controller artifact EXIST here?",
                "forbidden": "pooling its results with RI-SHARED in one success rate"}}

EXECUTION_ORDER = [
    "1  freeze falsifier v2 code, budget, score and seed derivation "
    "(c1_falsifier_v2_seal)",
    "2  freeze the held-out condition generator and list (this module)",
    "3  known counterexample 5x exact replay",
    "4  known counterexample 5x fresh-search blind rediscovery (detection "
    "diagnostic only — these five shaped v2, so rediscovery is NOT generality "
    "evidence)",
    "5  the 11 unresolved cells, fresh confirmatory seeds (V2C- stream)",
    "6  held-out RI-SHARED-v1, applied unchanged",
    "7  held-out RI-GMAX, re-synthesised per condition, reported separately",
    "8  only then may survival labels be issued",
]
RESULT_LABELS = {
    "escape": "CONFIRMATORY_ESCAPE_FOUND",
    "null": "NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2",
    "survival": "SURVIVED_FALSIFIER_V2 + UNDER_PRE_REGISTERED_HELD_OUT_CONDITIONS",
    "never": "no label in this campaign is a safety certification or a seal"}


def _rot(v, axis, deg):
    """Rodrigues rotation, deterministic."""
    v = np.asarray(v, float); k = np.asarray(axis, float)
    k = k / (np.linalg.norm(k) + 1e-15); th = np.radians(deg)
    return (v * np.cos(th) + np.cross(k, v) * np.sin(th)
            + k * np.dot(k, v) * (1.0 - np.cos(th)))


def condition_list():
    """Deterministic, ordered, hashable.  OFAT block then crossed block, per set."""
    out = []
    for set_name, axes in (("IN_DISTRIBUTION", IN_DIST), ("STRESS", STRESS)):
        for ax in sorted(axes):
            for v in axes[ax]:
                c = dict(NOMINAL); c[ax] = v
                out.append({"set": set_name, "kind": "OFAT", "varied": [ax], **c})
        for a1, a2 in CROSSES:
            for v1 in axes[a1]:
                for v2 in axes[a2]:
                    c = dict(NOMINAL); c[a1] = v1; c[a2] = v2
                    out.append({"set": set_name, "kind": "CROSSED",
                                "varied": [a1, a2], **c})
    for i, c in enumerate(out):
        c["condition_id"] = "%s-%04d" % (SPEC_VERSION, i)
    return out


def spawn_for(rho0, tl, cond):
    """Nominal spawn with the external condition applied to the ATTACKER only."""
    sp = make_spawn(rho0, tl * V_CLOSE)
    lat = float(cond["lateral_offset_m"])
    if lat:
        sp["att_p"] = np.asarray(sp["att_p"], float) + np.array([0.0, lat, 0.0])
    v = np.asarray(sp["att_v"], float)
    if cond["heading_deg"]:
        v = _rot(v, [0.0, 0.0, 1.0], float(cond["heading_deg"]))
    sp_speed = float(cond["speed_mps"])
    v = v / (np.linalg.norm(v) + 1e-15) * sp_speed
    sp["att_v"] = v
    return sp


def controller_for(kind, rho0, spec):
    """The witness's defender controller, unchanged from `rollout_for`."""
    if kind == "RH":
        s, _d, _m = solve_witness_hold(rho0, spec[1]); return log_ctrl(make_lp_arm(s))
    if kind == "MAXCLR":
        s, _m = solve_witness(rho0, spec[1]); return log_ctrl(make_lp_arm(s))
    if kind == "BASE":
        return log_ctrl(make_contract() if spec[1] == "C" else make_pd())
    raise ValueError(kind)


def finisher_for(cond):
    """Cone axis axis: tilt the finisher's aim, which moves n_F and so the cone."""
    base = make_finisher_fn(THETA)
    deg = float(cond["cone_axis_deg"])
    if deg == 0.0:
        return base

    def fin(obs, flags):
        a = np.asarray(base(obs, flags), float).copy()
        ax = a[:3]
        if np.linalg.norm(ax) > 1e-9:
            a[:3] = _rot(ax, [0.0, 0.0, 1.0], deg)
        return a.astype(np.float32)
    return fin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_heldout_conditions.json")
    ap.add_argument("--smoke", type=int, default=6,
                    help="feasibility smoke test on N conditions (no controller run)")
    a = ap.parse_args()
    t0 = time.time()
    conds = condition_list()
    spec = {"spec_version": SPEC_VERSION, "nominal": NOMINAL,
            "in_distribution_axes": IN_DIST, "stress_axes": STRESS,
            "crosses": CROSSES, "witnesses": HELDOUT_WITNESSES}
    spec_hash = hashlib.sha256(
        json.dumps(spec, sort_keys=True, default=str).encode()).hexdigest()
    list_hash = hashlib.sha256(
        json.dumps(conds, sort_keys=True, default=str).encode()).hexdigest()

    n_in = sum(1 for c in conds if c["set"] == "IN_DISTRIBUTION")
    n_st = len(conds) - n_in
    print("== held-out EXTERNAL condition set — generated and sealed, NOT evaluated ==")
    print("   axes: lateral offset · heading · speed · cone axis · reset")
    print("   IN_DISTRIBUTION %3d   STRESS %3d   total %3d conditions"
          % (n_in, n_st, len(conds)))
    print("   x %d defender trajectories = %d (condition, trajectory) pairs per arm"
          % (len(HELDOUT_WITNESSES), len(conds) * len(HELDOUT_WITNESSES)))
    print("   spec hash %s\n   list hash %s\n" % (spec_hash[:32], list_hash[:32]))

    smoke = []
    if a.smoke:
        pe, E, _fin = _env()
        RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
        W = {w[1]: w for w in witnesses()}
        pick = ([c for c in conds if c["set"] == "IN_DISTRIBUTION"][:a.smoke // 2]
                + [c for c in conds if c["set"] == "STRESS"][:a.smoke - a.smoke // 2])
        print("   feasibility smoke test — rollout validity only, NO controller, "
              "NO attacker search")
        for c in pick:
            for tag in (HELDOUT_WITNESSES[0], HELDOUT_WITNESSES[2]):
                kind, _t, rho0, tl, spec_w = W[tag]
                try:
                    rec = rollout_unified(pe, spawn_for(rho0, tl, c),
                                          controller_for(kind, rho0, spec_w),
                                          finisher_for(c), r_lane=RL, r_body=RB,
                                          seed=int(c["reset_seed"]))
                    ok = (rec.get("fire_step") is not None
                          and rec.get("_t_ref") is not None)
                    smoke.append({"condition_id": c["condition_id"], "set": c["set"],
                                  "varied": c["varied"], "witness": tag,
                                  "rollout_valid": bool(ok),
                                  "fire_step": rec.get("fire_step")})
                except Exception as ex:                 # recorded, never swallowed
                    smoke.append({"condition_id": c["condition_id"], "set": c["set"],
                                  "varied": c["varied"], "witness": tag,
                                  "rollout_valid": False,
                                  "error": "%s: %s" % (type(ex).__name__, ex)})
                s0 = smoke[-1]
                print("      %-8s %-22s %-15s %s"
                      % (s0["condition_id"][-4:], tag, "/".join(s0["varied"]),
                         "OK fire_step=%s" % s0.get("fire_step") if s0["rollout_valid"]
                         else "NO FIRE " + s0.get("error", "")), flush=True)
        nv = sum(1 for s0 in smoke if s0["rollout_valid"])
        print("\n   smoke: %d / %d (condition, trajectory) probes produced a valid "
              "firing rollout" % (nv, len(smoke)))
        print("   a condition that never fires is not a defect — it is a condition "
              "where no capture attempt occurs, and is recorded as such")

    out = {"meta": {"script": "c1_heldout_conditions",
                    "status": "SEALED_BEFORE_EVALUATION",
                    "spec_version": SPEC_VERSION,
                    "spec_hash": spec_hash, "condition_list_hash": list_hash,
                    "does_not": "evaluate any controller, run any falsifier, or "
                                "produce any survival label",
                    "arm_roles": ARM_ROLES,
                    "reporting_hierarchy": ["external condition", "defender trajectory",
                                            "controller arm"],
                    "reporting_rule": "several defender trajectories under one external "
                                      "condition are NOT independent samples; 'M of N "
                                      "cells' alone is not a permitted summary",
                    "sets_never_merged": ["IN_DISTRIBUTION", "STRESS"],
                    "execution_order": EXECUTION_ORDER,
                    "result_labels": RESULT_LABELS,
                    "CONFIRMATORY_EVALUATION_FREEZE":
                        "COMPLETE once this list and the v2 code seal are both in place"},
           "n_conditions": len(conds),
           "n_in_distribution": n_in, "n_stress": n_st,
           "n_defender_trajectories": len(HELDOUT_WITNESSES),
           "spec": spec, "conditions": conds, "feasibility_smoke": smoke}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
