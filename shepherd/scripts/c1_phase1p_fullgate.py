"""C-1 Phase 1P step 5.5 — full-gate re-evaluation of every intervention.

WHY THIS BLOCKS STEP 6
----------------------
Steps 4 and 5 checked E_lane after each intervention and left E_cap unchecked.  That
makes every arm's reading incomplete in both directions:

  * an intervention that REDUCED escapes may simply have destroyed the defender's
    own certifiable firing state, in which case it defended nothing;
  * an intervention whose escapes were REDISCOVERED may have had no valid capture
    state to begin with, which is a more basic failure than "the same mode came
    back".

So `FIRE_SHIFT_PLUS1`'s three NOT_REDISCOVERED witnesses must not be counted as any
defensive effect until E_cap is shown to hold there.  That is the review's ruling
and it is what this module settles.

CLASSIFICATION (pre-registered, from the review)
------------------------------------------------
    INVALID_INTERVENTION_ECAP_FAIL       capture state destroyed
    INVALID_INTERVENTION_ELANE_FAIL      lane clearance destroyed
    VALID_INTERVENTION_REPLAN_FALSIFIED  gate holds, escapes rediscovered
    VALID_INTERVENTION_NOT_REDISCOVERED  gate holds, none found at this budget

plus E_CAP_UNRESOLVED for the calibration band described below, because a
two-way verdict on a reconstructed quantity would overstate what is known.

THE RECONSTRUCTION PROBLEM, STATED HONESTLY
-------------------------------------------
E_cap needs v_soft and p_feas under the INTERVENED geometry.  The environment
reports them for the nominal defender only (obs[-3], obs[-1]); they cannot be read
off for a counterfactual, so they must be recomputed.  Recomputation with the
static fire-instant snapshot at n = 2000, seed 0 reproduces the environment's own
numbers closely but NOT exactly: on the calibration set, v_soft matches to the
sample and p_feas differs by one or two samples out of the union's 2500.

That residual is measured here, per witness, and carried as a BAND.  E_cap is
reported three ways -- PASS / FAIL / E_CAP_UNRESOLVED -- with UNRESOLVED covering
verdicts that fall inside the band.  Calling a reconstructed 0.899 a FAIL against
theta = 0.9 would be exactly the kind of precision this campaign has been
retracting.

The band is a property of the harness, not of the arms: it is computed from the
NONE arm against the environment's own reported values, so fixing it before
looking at arm results is not a post-hoc choice.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for
from shepherd.scripts.c1_phase1p_intervention import apply_intervention, lane_clearance
from shepherd.scripts.c1_phase1p_replan import ARMS
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

VSHOT_N, VSHOT_SEED, VSHOT_NSEG = 2000, 0, 1     # calibrated against the env's own values
BAND_FLOOR = 0.02                                 # never claim tighter than this


def vshot_static(p_att, v_att, obs_pointing, P_fire, E, cone_override=None):
    """v_soft / p_feas on the STATIC fire-instant snapshot -- the form E_cap uses."""
    kw = E._vshot_kwargs(p_att, v_att, obs_pointing)
    if cone_override is not None:
        kw = dict(kw); kw.update(cone_override)
    u = V.build_reachable_union(p_att, v_att, tau=float(E.tau_deploy),
                                a_att_max=E.a_att_max, n=VSHOT_N,
                                n_segments=VSHOT_NSEG, seed=VSHOT_SEED, **kw)
    r = V.eval_union_with_limiters(u, np.asarray(P_fire, float), E.kill_radius)
    return float(r.v_shot_soft), float(r.p_feasible), int(r.n_total)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_fullgate.json")
    ap.add_argument("--replan", default="results/c1_corridor/c1_phase1p_replan.json")
    a = ap.parse_args()
    pe, E, fin = _env(); ws = witnesses(); th = pe.theta; t0 = time.time()
    prior = json.loads(pathlib.Path(a.replan).read_text())
    prior_by = {r["witness"]: r["arms"] for r in prior["rows"]}

    from shepherd.train.phi_potential import teacher_fire

    print("== step 5.5 — full-gate (E_cap AND E_lane) re-evaluation ==")
    print("   theta = %.2f | v_shot reconstruction: static snapshot, n=%d seed=%d n_seg=%d\n"
          % (th, VSHOT_N, VSHOT_SEED, VSHOT_NSEG))

    # ---- calibration: reconstruction vs the environment's own numbers, NONE arm
    cal = []
    ctxs = {}
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        kw = E._vshot_kwargs(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6], o[36:45])
        ctxs[tag] = {"P": np.asarray(rec["_lim"][t:], float),
                     "Vp": np.asarray(rec["_vel"][t:], float),
                     "cone": {k: kw[k] for k in ("net_apex", "n_F", "theta_net",
                                                 "range_min", "range_max")},
                     "p_att": o[ATT_P0:ATT_P0 + 3], "v_att": o[ATT_P0 + 3:ATT_P0 + 6],
                     "tau": float(E.tau_deploy), "t_ref": t, "E": E, "tag": tag,
                     "obs_all": rec["_obs"], "lim_all": rec["_lim"], "vel_all": rec["_vel"],
                     "pointing": o[36:45]}
        v_r, p_r, n_tot = vshot_static(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6],
                                       o[36:45], rec["_lim"][t], E)
        cal.append({"witness": tag, "env_v_soft": float(o[-3]), "env_p_feas": float(o[-1]),
                    "recon_v_soft": v_r, "recon_p_feas": p_r, "union_n_total": n_tot,
                    "dv": v_r - float(o[-3]), "dp": p_r - float(o[-1])})
    band = max(BAND_FLOOR, max(abs(c["dv"]) for c in cal))
    print("   calibration (NONE arm, reconstruction vs environment):")
    print("     max |dv| %.5f   max |dp| %.5f   union n_total %d"
          % (max(abs(c["dv"]) for c in cal), max(abs(c["dp"]) for c in cal),
             cal[0]["union_n_total"]))
    print("     -> E_cap band = %.4f (max(|dv|, floor %.2f)); verdicts inside it are "
          "E_CAP_UNRESOLVED\n" % (band, BAND_FLOOR))

    rows = []
    for kind, tag, rho0, tl, spec in ws:
        ctx = ctxs[tag]
        per = {}
        for arm in ARMS:
            got = apply_intervention(arm, ctx, np.zeros((4, 3)))
            if got is None:
                per[arm] = {"classification": "NOT_APPLICABLE"}
                continue
            L, cone, pa, va, mag, Pnew = got
            lc = lane_clearance(Pnew, cone, ctx["tau"])
            e_lane = (None if lc is None else bool(lc >= 0.0))
            # fire-rule validity: the env's own teacher_fire on the arm's fire step
            t2 = ctx["t_ref"] + (1 if arm == "FIRE_SHIFT_PLUS1" else
                                 -1 if arm == "FIRE_SHIFT_MINUS1" else 0)
            o2 = np.asarray(ctx["obs_all"][t2], float)
            fire_valid = bool(teacher_fire(o2, th))
            pointing = o2[36:45] if t2 != ctx["t_ref"] else ctx["pointing"]
            v_r, p_r, _n = vshot_static(pa, va, pointing, Pnew[0], E,
                                        cone_override={"n_F": cone["n_F"]})
            if p_r <= 0:
                e_cap = "FAIL"
            elif v_r - th > band:
                e_cap = "PASS"
            elif th - v_r > band:
                e_cap = "FAIL"
            else:
                e_cap = "E_CAP_UNRESOLVED"
            prev = prior_by.get(tag, {}).get(arm, {})
            outcome = prev.get("outcome", "?")
            occ = prev.get("occupied_modes", [])
            if e_cap == "FAIL":
                cls = "INVALID_INTERVENTION_ECAP_FAIL"
            elif e_lane is False:
                cls = "INVALID_INTERVENTION_ELANE_FAIL"
            elif e_cap == "E_CAP_UNRESOLVED":
                cls = "E_CAP_UNRESOLVED"
            elif outcome == "REDISCOVERED":
                cls = "VALID_INTERVENTION_REPLAN_FALSIFIED"
            elif outcome.startswith("NOT_REDISCOVERED"):
                cls = "VALID_INTERVENTION_NOT_REDISCOVERED"
            else:
                cls = "UNKNOWN_PRIOR_OUTCOME"
            per[arm] = {"E_cap_after_intervention": e_cap,
                        "v_soft_recon": v_r, "p_feas_recon": p_r,
                        "E_lane_after_intervention": e_lane,
                        "lane_clearance_m": lc, "fire_step_valid": fire_valid,
                        "fire_step_used": int(t2),
                        "replan_outcome": outcome,
                        "escape_mode_if_full_gate_valid": (occ if cls.startswith("VALID")
                                                           else None),
                        "classification": cls}
        rows.append({"witness": tag, "class": kind, "arms": per})
        print("   %-22s %s" % (tag, "  ".join(
            "%s:%s" % (a_[:4], per[a_]["classification"].replace("INVALID_INTERVENTION_", "!")
                       .replace("VALID_INTERVENTION_", "").replace("REPLAN_FALSIFIED", "FALS")
                       .replace("NOT_REDISCOVERED", "NOTRED")) for a_ in ARMS)), flush=True)

    from collections import Counter
    agg = {}
    for arm in ARMS:
        c = Counter(r["arms"][arm]["classification"] for r in rows)
        agg[arm] = dict(c)
    print("\n   classification per arm:")
    for arm in ARMS:
        print("     %-27s %s" % (arm, ", ".join("%s %d" % (k, v)
                                                for k, v in sorted(agg[arm].items()))))

    fs = agg.get("FIRE_SHIFT_PLUS1", {})
    n_valid_notred = fs.get("VALID_INTERVENTION_NOT_REDISCOVERED", 0)
    print("\n   FIRE_SHIFT_PLUS1 -- step 5 reported 3 NOT_REDISCOVERED; after the full gate "
          "%d remain countable" % n_valid_notred)

    labels = ["TESTED_STATIC_INTERVENTIONS_INSUFFICIENT_UNDER_CONSTRAINED_REPLAN",
              "MODE_SUBSTITUTION_NOT_OBSERVED",
              "TESTED_INTERVENTIONS_FAILED_TO_CLOSE_SOURCE_MODES",
              "JOINT_FREEDOM_NECESSITY_UNRESOLVED",
              "ARTIFACT_BLOCK_RATE_NOT_CONTROLLER_EVIDENCE",
              "FIRE_TIMING_SIGNAL_PROVISIONAL"]
    withheld = ["INTERSECTION_CONSTRAINT_REFUTED", "CURRENT_CONTROL_FREEDOMS_IMPOSSIBLE"]
    print("\n   ratified labels: %s" % ", ".join(labels))
    print("   withheld:        %s" % ", ".join(withheld))

    out = {"meta": {"script": "c1_phase1p_fullgate", "step": 5.5,
                    "theta": th,
                    "vshot_reconstruction": {"n": VSHOT_N, "seed": VSHOT_SEED,
                                             "n_segments": VSHOT_NSEG,
                                             "form": "static fire-instant snapshot"},
                    "calibration_band": band, "band_floor": BAND_FLOOR,
                    "band_rationale": "the environment reports v_soft/p_feas for the nominal "
                                      "defender only; counterfactual values must be "
                                      "recomputed, and the residual against the env's own "
                                      "numbers is carried as a band rather than ignored",
                    "classification": ["INVALID_INTERVENTION_ECAP_FAIL",
                                       "INVALID_INTERVENTION_ELANE_FAIL",
                                       "E_CAP_UNRESOLVED",
                                       "VALID_INTERVENTION_REPLAN_FALSIFIED",
                                       "VALID_INTERVENTION_NOT_REDISCOVERED"],
                    "ratified_labels": labels, "withheld_labels": withheld,
                    "protocol": G.PROTOCOL_VERSION},
           "calibration": cal, "aggregate": agg, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
