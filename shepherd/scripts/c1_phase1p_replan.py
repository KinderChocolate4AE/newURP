"""C-1 Phase 1P step 5 — basin-level constrained replan.

THE QUESTION STEP 4 COULD NOT ANSWER
------------------------------------
Step 4 froze the attacker's plan and asked whether an intervention broke it.  That
only ever established a local fact about specific artifacts.  Here the intervention
is FIXED and the attacker is allowed to re-optimise against it.  Three outcomes,
named before the run:

  REDISCOVERED       verified escapes exist under the intervention -> the
                     intervention is insufficient, whatever it blocked in step 4
  NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET
                     no verified escape at THIS budget.  Not "sealed" -- a
                     falsifier that finds nothing proves nothing, and this budget is
                     the diagnostic one, smaller than D0's
  MODE_SUBSTITUTION  the mode that the intervention closed is gone, and a DIFFERENT
                     mode is occupied.  This is the measurement the intersection
                     constraint actually depends on

MODE SUBSTITUTION IS THE POINT
------------------------------
Step 4 measured that ring intervention blocks CONE_LATERAL artifacts through the
kill term, and that cone steering blocks KILL artifacts through the cone term --
the two modes are not separated by controller axis.  But blocking a frozen plan is
not closing a mode.  If, under RING_FREEZE, the re-optimised attacker abandons KILL
and comes back through CONE_LATERAL, then the ring axis alone cannot seal and the
cone axis is genuinely needed.  If instead both modes stay occupied, the
intervention is simply too weak and nothing about necessity follows.

VERIFICATION, NOT SEARCH SCORE
------------------------------
The CEM's own score is a proposal, never evidence -- the ratified
proposal-verification separation.  Every escape counted here is re-adjudicated with
the CONTINUOUS clearance adjudicator against the intervened defender.  Occupancy is
therefore backed by verified artifacts, not by optimizer claims.

NO FREQUENCY CLAIMS
-------------------
Carried forward from step 2.  Artifact counts reflect search budget and CEM basin
geometry.  Occupancy is reported as OBSERVED / NOT_OBSERVED; counts appear only as
search-effort bookkeeping and are labelled as such.

A PREDICTION UNDER TEST
-----------------------
Step 4 recorded FIRE_SHIFT_PLUS1 as the highest blocker (71/74) but argued it
measures the artifact's timing brittleness rather than providing a defence, since
an attacker that observes the fire instant simply re-solves.  That is a falsifiable
prediction and FIRE_SHIFT_PLUS1 is included here to test it.  If its escapes are
rediscovered as readily as the nominal ones, the prediction holds; if not, step 4's
interpretation was wrong and is retracted.
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
from shepherd.scripts.c1_phase1p_intervention import apply_intervention, lane_clearance
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

ARMS = ("NONE", "RING_FREEZE", "CONE_STEER_COVERAGE",
        "RING_FREEZE_PLUS_COVERAGE", "FIRE_SHIFT_PLUS1")
N_VERIFY_HI, N_VERIFY_LO = 4, 4          # per witness-arm-mode: best-scoring + tightest


def _verify_pick(scores, n_hi=N_VERIFY_HI, n_lo=N_VERIFY_LO):
    """Indices to adjudicate: the highest scores (existence evidence, most likely
    genuine) plus the lowest (the adversarial edge).  Pre-registered so the sample
    cannot be widened after seeing a null."""
    order = np.argsort(scores)
    lo = list(order[:min(n_lo, len(order))])
    hi = list(order[::-1][:min(n_hi, len(order))])
    return [int(i) for i in dict.fromkeys(hi + lo)]


def search_under(ctx, arm, E):
    """Re-optimise the attacker against the INTERVENED defender."""
    got = apply_intervention(arm, ctx, np.zeros((4, 3)))
    if got is None:
        return None
    L, cone, p_att, v_att, mag, Pnew = got
    lc = lane_clearance(Pnew, cone, ctx["tau"])
    tau = ctx["tau"]
    accs = []
    for bs in DIV_BASE_SEEDS:
        for r in range(DIAG["restarts"]):
            # COMMON RANDOM NUMBERS ACROSS ARMS.  The first version of this put the
            # arm name into the seed, so every arm drew a DIFFERENT attacker stream
            # and any arm-vs-NONE difference confounded the intervention effect with
            # search noise -- which showed up immediately as spurious MODE_WIDENED
            # cases.  That is precisely the paired/diversity distinction built in
            # step 1, applied to the wrong axis.  The stream now depends on the
            # witness only, so the arms face the identical attacker draw.
            sd_bank, sd_cem = _div_seeds(bs, ctx["tag"], "w:" + ctx["tag"], r)
            acc1 = V.reachable_accels(E.a_att_max, DIAG["n_bank"], int(sd_bank))
            ep1, tf1, pts1 = V._seg_paths_turn(
                p_att, v_att, np.repeat(acc1[:, None, :], DIAG["K"], axis=1), tau=tau,
                attacker_turn_limited=False, omega_att_max=None, e_att=None, n_t=24)
            sc1 = np.minimum(kill_margin(pts1, L, E.kill_radius, tau),
                             cone_exit_margin(ep1, **cone))
            warm = np.repeat(acc1[int(np.argmax(sc1))][None, :], DIAG["K"], axis=0)
            _b, escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                     L_of_t=L, kill_radius=E.kill_radius, cone_kw=cone,
                                     K=DIAG["K"], pop=DIAG["pop"], iters=DIAG["iters"],
                                     seed=int(sd_cem), warm=warm)
            accs.extend(e["acc"] for e in escs)
    out = {"arm": arm, "lane_clearance_m": lc,
           "defender_E_lane": (None if lc is None else bool(lc >= 0.0)),
           "magnitude": mag, "n_search_candidates": len(accs)}
    if not accs:
        out["modes"] = {m: {"occupancy": "NOT_OBSERVED"} for m in MODES}
        out["outcome"] = "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET"
        return out
    A = np.asarray(accs, float)
    ep, tf, pts = V._seg_paths_turn(p_att, v_att, A, tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    km = kill_margin(pts, L, E.kill_radius, tau)
    lat, axi, _ax, _rn, _ang = cone_components(ep, **cone)
    cm = np.maximum(lat, axi)
    keep = (np.minimum(km, cm) > 0) & tf
    if not keep.any():
        out["modes"] = {m: {"occupancy": "NOT_OBSERVED"} for m in MODES}
        out["outcome"] = "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET"
        return out
    A, km, cm, lat, axi = A[keep], km[keep], cm[keep], lat[keep], axi[keep]
    lab = classify(km, cm, lat, axi); sc = np.minimum(km, cm)

    modes = {}
    for m in MODES:
        s = np.flatnonzero(lab == m)
        if not len(s):
            modes[m] = {"occupancy": "NOT_OBSERVED"}
            continue
        picks = [int(s[i]) for i in _verify_pick(sc[s])]
        rows, n_ok = [], 0
        for idx in picks:
            r = exact_min_clearance(p_att, v_att, A[idx], tau, L, N_LIM, DT, E.kill_radius)
            ok = bool(r["verdict"] == "VERIFIED_COLLISION_FREE" and cm[idx] > 0)
            n_ok += ok
            rows.append({"attack_policy_hash": G.attack_policy_hash(A[idx]),
                         "sampled_binding_margin_m": float(sc[idx]),
                         "continuous_kill_margin_m": float(r["exact_margin_m"]),
                         "cone_exit_margin_m": float(cm[idx]),
                         "verdict": r["verdict"], "verified_escape": ok})
        modes[m] = {"occupancy": "OBSERVED" if n_ok else "NOT_OBSERVED",
                    "n_candidates_search_bookkeeping_only": int(len(s)),
                    "n_adjudicated": len(picks), "n_verified_escape": n_ok,
                    "rows": rows}
    out["modes"] = modes
    occ = [m for m in MODES if modes[m]["occupancy"] == "OBSERVED"]
    out["occupied_modes"] = occ
    out["outcome"] = ("REDISCOVERED" if occ
                      else "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_replan.json")
    a = ap.parse_args()
    pe, E, fin = _env(); ws = witnesses(); t0 = time.time()
    print("== step 5 — basin-level constrained replan ==")
    print("   attacker re-optimises against each FIXED intervention")
    print("   escapes counted only after CONTINUOUS re-adjudication (search score is a proposal)")
    print("   budget: bank %d x restarts %d x base seeds %d (diagnostic, NOT D0)\n"
          % (DIAG["n_bank"], DIAG["restarts"], len(DIV_BASE_SEEDS)))

    rows = []
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        kw = E._vshot_kwargs(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6], o[36:45])
        ctx = {"P": np.asarray(rec["_lim"][t:], float),
               "Vp": np.asarray(rec["_vel"][t:], float),
               "cone": {k: kw[k] for k in ("net_apex", "n_F", "theta_net",
                                           "range_min", "range_max")},
               "p_att": o[ATT_P0:ATT_P0 + 3], "v_att": o[ATT_P0 + 3:ATT_P0 + 6],
               "tau": float(E.tau_deploy), "t_ref": t, "E": E, "tag": tag,
               "obs_all": rec["_obs"], "lim_all": rec["_lim"], "vel_all": rec["_vel"]}
        per = {}
        for arm in ARMS:
            r = search_under(ctx, arm, E)
            if r is None:
                per[arm] = {"outcome": "NOT_APPLICABLE"}
                continue
            per[arm] = r
        bits = []
        for arm in ARMS:
            p = per[arm]
            occ = p.get("occupied_modes", [])
            bits.append("%s:%s" % (arm[:4], "".join(m[0] for m in occ) if occ else "-"))
        print("   %-22s %s" % (tag, "  ".join(bits)), flush=True)
        rows.append({"witness": tag, "class": kind, "arms": per})

    # ---- aggregate: occupancy per arm, and substitution relative to NONE
    agg = {}
    for arm in ARMS:
        ok = [r for r in rows if r["arms"][arm].get("outcome") != "NOT_APPLICABLE"]
        occ = {m: sum(1 for r in ok if r["arms"][arm]["modes"][m]["occupancy"] == "OBSERVED")
               for m in MODES}
        nre = sum(1 for r in ok if r["arms"][arm]["outcome"].startswith("NOT_REDISCOVERED"))
        agg[arm] = {"n_witnesses": len(ok), "mode_occupancy_witnesses": occ,
                    "n_not_rediscovered": nre,
                    "n_rediscovered": len(ok) - nre}

    subs = []
    for r in rows:
        base = r["arms"]["NONE"]
        for arm in ARMS[1:]:
            p = r["arms"][arm]
            if p.get("outcome") == "NOT_APPLICABLE":
                continue
            b = {m for m in MODES if base["modes"][m]["occupancy"] == "OBSERVED"}
            n = {m for m in MODES if p["modes"][m]["occupancy"] == "OBSERVED"}
            if b and not n:
                kind_ = "ALL_MODES_CLOSED_AT_THIS_BUDGET"
            elif b - n and n:
                kind_ = "MODE_SUBSTITUTION" if (n - b) else "MODE_NARROWED"
            elif n == b:
                kind_ = "UNCHANGED"
            else:
                kind_ = "MODE_WIDENED"
            subs.append({"witness": r["witness"], "arm": arm,
                         "modes_before": sorted(b), "modes_after": sorted(n),
                         "classification": kind_})

    print("\n   per-arm outcome (witnesses):")
    print("   %-27s %-9s %-13s %s" % ("arm", "redisc.", "not-redisc.", "mode occupancy (KILL / CONE_LATERAL / CONE_AXIAL)"))
    for arm in ARMS:
        g = agg[arm]; o = g["mode_occupancy_witnesses"]
        print("   %-27s %2d/%-6d %2d/%-11d %2d / %2d / %2d"
              % (arm, g["n_rediscovered"], g["n_witnesses"], g["n_not_rediscovered"],
                 g["n_witnesses"], o["KILL"], o["CONE_LATERAL"], o["CONE_AXIAL"]))

    from collections import Counter
    cc = Counter((s["arm"], s["classification"]) for s in subs)
    print("\n   substitution relative to NONE:")
    for arm in ARMS[1:]:
        line = ", ".join("%s %d" % (k[1], v) for k, v in sorted(cc.items()) if k[0] == arm)
        print("     %-27s %s" % (arm, line if line else "-"))

    n_sub = sum(1 for s in subs if s["classification"] == "MODE_SUBSTITUTION")
    if n_sub:
        verdict = ("MODE_SUBSTITUTION OBSERVED in %d witness-arm cases -- a controller "
                   "closing one axis is answered on another" % n_sub)
    elif any(agg[a]["n_not_rediscovered"] for a in ARMS[1:]):
        verdict = ("no substitution; some arms reached NOT_REDISCOVERED at this budget -- "
                   "not a seal, a null result under a diagnostic budget")
    else:
        verdict = ("no substitution and everything rediscovered -- the interventions are "
                   "simply insufficient, and nothing about joint necessity follows")
    print("\n   verdict: %s" % verdict)

    out = {"meta": {"script": "c1_phase1p_replan", "step": 5,
                    "outcomes": ["REDISCOVERED",
                                 "NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET",
                                 "MODE_SUBSTITUTION"],
                    "verification": "every counted escape re-adjudicated with "
                                    "exact_min_clearance against the intervened defender; "
                                    "CEM score is a proposal, never evidence",
                    "verify_sample": "per witness-arm-mode: %d highest-score + %d tightest, "
                                     "pre-registered" % (N_VERIFY_HI, N_VERIFY_LO),
                    "budget": {**DIAG, "base_seeds": list(DIV_BASE_SEEDS)},
                    "seeding": "COMMON RANDOM NUMBERS across arms -- the attacker stream depends "
                               "on the witness only, so arm-vs-NONE differences are the "
                               "intervention effect and not search noise",
                    "forbidden": "NO FREQUENCY CLAIMS -- occupancy only; counts are "
                                 "search-effort bookkeeping",
                    "not_a_seal": "NOT_REDISCOVERED is a null result at a diagnostic budget "
                                  "smaller than D0's, never a safety claim",
                    "protocol": G.PROTOCOL_VERSION},
           "aggregate": agg, "substitution": subs, "verdict": verdict, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
