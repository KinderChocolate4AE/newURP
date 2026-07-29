"""C-1 — why the 118 unresolved no-fire outcomes are unresolved.

WHY THIS EXISTS
---------------
Endpoint C left 118 of the 397 no-fire pairs as
`SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED`, and 95 of them are in STRESS.  Leaving
that as a bare count invites the reader to assume either that STRESS failures are
being under-counted or that the cases are genuinely undecidable.  Neither should
be assumed; the reason is recorded.

WHAT IS AND IS NOT BEING DONE
-----------------------------
NOT a new adjudication rule.  No unresolved case is reclassified as success or
failure here.  The three-way mission split from V2C-PROTOCOL-v2 is untouched.
This module only re-runs those 118 pairs and reports, from state the rollout
already records, WHY neither `penetrated` nor `safe` was set:

    HORIZON_ENDED_BEFORE_PENETRATION_OR_SAFE
        the episode ended with the attacker still short of the asset plane —
        a right-censored mission outcome
    TERMINATION_STATE_AMBIGUOUS
        the attacker passed the asset plane without the penetration flag being
        set: the outcome is decided but the recorded flags do not decide it
    ROLLOUT_OR_FLAG_ERROR
        the rollout raised
    OTHER
        none of the above

THE BOUNDS -- AND A NAMING CORRECTION
------------------------------------
An earlier readout called 39.6%-56.4% "the system-level failure rate bound".  That
was wrong.  It bounds only the NO-ENGAGEMENT BRANCH; the 307 post-fire pairs are
still unadjudicated and can add failures of their own.

    CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND   279 / 704 = 39.6%
    NO_ENGAGEMENT_BRANCH_FAILURE_BOUND     [279, 397] / 704 = [39.6%, 56.4%]
    TOTAL_SYSTEM_FAILURE_BOUND             [39.6%, 100%]   <- uninformative upper end
                                           until steps 5-7 adjudicate the 307

All figures are descriptive statistics of a designed condition set, not operational
probabilities.

AND A SECOND CORRECTION: `MISSION_SUCCESS_WITHOUT_CAPTURE = 0` IS VACUOUS
------------------------------------------------------------------------
    E_safe = E_cap and E_lane and not penetrated,   E_cap = any eligible fire instant
With no firing event E_cap is False, so E_safe is False BY CONSTRUCTION.  The frozen
success predicate therefore CANNOT report a success that did not involve a capture,
and "0 successes without capture among no-fire pairs" is guaranteed by the
definition rather than observed.  The honest label is

    SUCCESS_WITHOUT_CAPTURE_NOT_DETECTABLE_BY_FROZEN_PREDICATE

The empirical cross-check is consistent: safe=True occurs 167 times among the 307
eligible pairs and 0 times among the 397 no-fire pairs.  What may still be said is
weaker and is stated instead: there is no positive evidence the threat was
resolved, because every censored case ended with the attacker still closing.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import PRIMARY, R_BODY, M_SAFETY, X_FIRE
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1d import rollout_unified
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses
from shepherd.scripts.c1_heldout_conditions import (condition_list, spawn_for,
                                                    finisher_for, controller_for)

X_ASSET = 0.0          # the protected plane the attacker is closing on (x decreasing)
REASONS = ["HORIZON_ENDED_BEFORE_PENETRATION_OR_SAFE", "TERMINATION_STATE_AMBIGUOUS",
           "ROLLOUT_OR_FLAG_ERROR", "OTHER"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", default="results/c1_corridor/c1_v2c_endpoints.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_unresolved.json")
    a = ap.parse_args()
    pe, _E, _fin = _env(); t0 = time.time()
    W = {w[1]: w for w in witnesses()}
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    ep = json.loads(pathlib.Path(a.endpoints).read_text())
    cmap = {c["condition_id"]: c for c in condition_list()}

    targets = [(r["condition_id"], r["set"], tag)
               for r in ep["conditions"]
               for tag, v in r["per_trajectory"].items()
               if (not v["eligible"]
                   and v["mission_outcome"] == "SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED")]
    print("== why the %d unresolved no-fire outcomes are unresolved ==" % len(targets))
    print("   NOT a new adjudication rule — nothing is reclassified as success or "
          "failure\n")

    rows = []
    for i, (cid, sset, tag) in enumerate(targets):
        c = cmap[cid]
        kind, _t, rho0, tl, spec_w = W[tag]
        try:
            rec = rollout_unified(pe, spawn_for(rho0, tl, c),
                                  controller_for(kind, rho0, spec_w), finisher_for(c),
                                  r_lane=RL, r_body=RB, seed=int(c["reset_seed"]))
            obs = np.asarray(rec["_obs"], float)
            xt = float(obs[-1][ATT_P0]) if len(obs) else float("nan")
            vt = obs[-1][ATT_P0 + 3:ATT_P0 + 6] if len(obs) else np.full(3, np.nan)
            steps = int(rec.get("steps", 0))
            # projected closing time along the asset direction, not distance/nominal speed.
            # r_hat points from the attacker to the asset plane along -x.
            d = xt - X_ASSET
            closing = float(-vt[0])                     # >0 means closing on the plane
            tau_close = (d / closing) if closing > 1e-6 else None
            reason = ("TERMINATION_STATE_AMBIGUOUS" if xt <= X_ASSET
                      else "HORIZON_ENDED_BEFORE_PENETRATION_OR_SAFE")
            rows.append({"condition_id": cid, "set": sset, "witness": tag,
                         "reason": reason, "steps": steps,
                         "attacker_terminal_x_m": xt,
                         "distance_to_asset_plane_m": d,
                         "attacker_terminal_velocity_x_mps": float(vt[0]),
                         "attacker_terminal_speed_mps": float(np.linalg.norm(vt)),
                         "projected_closing_time_s": tau_close,
                         "tier": rec.get("tier"), "penetrated": bool(rec.get("penetrated")),
                         "safe": bool(rec.get("safe"))})
        except Exception as ex:
            rows.append({"condition_id": cid, "set": sset, "witness": tag,
                         "reason": "ROLLOUT_OR_FLAG_ERROR",
                         "error": "%s: %s" % (type(ex).__name__, ex)})
        if (i + 1) % 25 == 0:
            print("   %3d / %d" % (i + 1, len(targets)), flush=True)

    by = collections.Counter(r["reason"] for r in rows)
    by_set = collections.defaultdict(collections.Counter)
    for r in rows:
        by_set[r["set"]][r["reason"]] += 1
    print("\n   reason breakdown")
    for k in REASONS:
        if by[k]:
            print("      %-42s %4d" % (k, by[k]))
    for s in sorted(by_set):
        print("      %-16s %s" % (s, dict(by_set[s])))

    xs = [r["distance_to_asset_plane_m"] for r in rows
          if r.get("distance_to_asset_plane_m") is not None]
    ts = [r["projected_closing_time_s"] for r in rows
          if r.get("projected_closing_time_s") is not None]
    n_not_closing = sum(1 for r in rows
                        if r.get("projected_closing_time_s") is None
                        and r["reason"] != "ROLLOUT_OR_FLAG_ERROR")
    if xs:
        xs = np.asarray(xs, float)
        print("\n   attacker distance to the asset plane at episode end (m): "
              "min %.2f  median %.2f  max %.2f" % (xs.min(), float(np.median(xs)), xs.max()))
    if ts:
        ts = np.asarray(ts, float)
        print("   PROJECTED closing time tau = d / max(eps, -r_hat . v_rel)  (s): "
              "min %.3f  median %.3f  max %.3f" % (ts.min(), float(np.median(ts)), ts.max()))
        print("   not closing on the asset plane at episode end: %d" % n_not_closing)
        print("   this is a DIAGNOSTIC timescale from the terminal state; it does not "
              "model\n   post-horizon guidance, acceleration changes or re-engagement")

    tot = ep["endpoint_A"]["total_pairs"]
    conf = ep["endpoint_C_no_fire_mission"]["overall"]["MISSION_FAILURE_NO_ENGAGEMENT"]
    unres = len(targets)
    # ---- CORRECTED bound naming.  39.6-56.4% bounds the NO-ENGAGEMENT BRANCH only;
    # the post-fire branch (307 pairs) is unadjudicated, so the TOTAL system bound is
    # still [39.6%, 100%].  Calling 56.4% the total upper bound was wrong.
    print("\n   CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND      %d / %d = %.1f%%"
          % (conf, tot, 100.0 * conf / tot))
    print("   NO_ENGAGEMENT_BRANCH_FAILURE_BOUND        [%d, %d] / %d = [%.1f%%, %.1f%%]"
          % (conf, conf + unres, tot, 100.0 * conf / tot, 100.0 * (conf + unres) / tot))
    print("   TOTAL_SYSTEM_FAILURE_BOUND                [%d, %d] / %d = [%.1f%%, 100.0%%]"
          % (conf, tot, tot, 100.0 * conf / tot))
    print("      the total upper bound is uninformative until the %d post-fire pairs "
          "are adjudicated" % ep["endpoint_A"]["post_fire_eligible"])
    print("      all figures are descriptive statistics of a DESIGNED condition set, "
          "not operational probabilities")

    out = {"meta": {"script": "c1_v2c_unresolved",
                    "role": "explain the unresolved bucket; reclassifies nothing",
                    "reasons": REASONS,
                    "asset_plane_x_m": X_ASSET,
                    "rule": "attacker terminal x <= asset plane -> the outcome is "
                            "decided but the recorded flags do not decide it "
                            "(AMBIGUOUS); otherwise the episode ended with the "
                            "attacker still short of it (right-censored)",
                    "bound_semantics": "sealed-grid descriptive bound, NOT an "
                                       "operational failure probability"},
           "n_unresolved": unres,
           "reason_counts": dict(by),
           "reason_counts_by_set": {s: dict(by_set[s]) for s in by_set},
           "bounds": {
               "CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND":
                   {"n": conf, "of": tot, "pct": round(100.0 * conf / tot, 1)},
               "NO_ENGAGEMENT_BRANCH_FAILURE_BOUND":
                   {"lo_n": conf, "hi_n": conf + unres, "of": tot,
                    "lo_pct": round(100.0 * conf / tot, 1),
                    "hi_pct": round(100.0 * (conf + unres) / tot, 1),
                    "note": "bounds the NO-ENGAGEMENT branch only"},
               "TOTAL_SYSTEM_FAILURE_BOUND":
                   {"lo_pct": round(100.0 * conf / tot, 1), "hi_pct": 100.0,
                    "note": "the post-fire branch is unadjudicated; naming 56.4%% the "
                            "total upper bound was an error, corrected here"}},
           "success_predicate_analysis": {
               "definition": "E_safe = E_cap and E_lane and not penetrated; "
                             "E_cap = any eligible fire instant",
               "consequence": "with no firing event E_cap is False, so E_safe is False "
                              "BY CONSTRUCTION",
               "therefore": "MISSION_SUCCESS_WITHOUT_CAPTURE = 0 among no-fire pairs is "
                            "DEFINITIONALLY GUARANTEED and carries no information",
               "correct_label": "SUCCESS_WITHOUT_CAPTURE_NOT_DETECTABLE_BY_FROZEN_PREDICATE",
               "empirical_check": "safe=True occurs 167 times among the 307 eligible "
                                  "pairs and 0 times among the 397 no-fire pairs, "
                                  "consistent with the structural argument",
               "what_may_still_be_said": "no positive evidence that the threat was "
                                         "resolved: every censored case ended with the "
                                         "attacker still closing on the asset plane"},
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
