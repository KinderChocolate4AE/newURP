"""C-1 Phase 1P step 2 — escape MODE partition on decorrelated artifacts.

INPUT DISCIPLINE (the reason this could not have been run before step 1)
-----------------------------------------------------------------------
Step 1 established that witness-blind searches collide: policy collisions 1-28 and
warm-start collisions 14-36 across six seed offsets, never zero.  Clustering
witness-blind artifacts would therefore not measure how many escape modes the
system has -- it would measure the structure of the shared warm-start pool.  Every
artifact consumed here comes from `derive_seed(mode='diversity')` streams, which
produced zero policy and zero warm-start collisions across four base seeds.

PARTITION: DEFINITIONAL, NOT FITTED
-----------------------------------
No k, no distance metric, no fitted centroids -- so there is no free parameter to
tune toward a nicer-looking answer.  An escape requires BOTH

    kill_margin      > 0     never within r_kill of any limiter
    cone_exit_margin > 0     endpoint outside the SE(3) net cone

so the BINDING term -- the min, the one that nearly failed -- names the mechanism
that almost caught it.  `cone_exit_margin` is itself already a max of two
geometrically distinct escapes (`c1_replan_falsifier.cone_exit_margin`):

    lateral = (angle - theta_net) * |r|      through the cone WALL   (angular miss)
    axial   = max(range_min - ax, ax - rmax) beyond the range BAND   (range miss)

giving three mutually exclusive, exhaustive modes:

    KILL          kill_margin < cone_exit_margin
                  -> tightest constraint is limiter proximity; a RING-MOTION mode
    CONE_LATERAL  cone binds, lateral >= axial
                  -> exits through the cone wall; an ANGULAR/POINTING mode
    CONE_AXIAL    cone binds, axial > lateral
                  -> exits beyond the range band; a RANGE/FIRE-TIMING mode

WHY THIS PARTICULAR PARTITION IS THE USEFUL ONE
-----------------------------------------------
It maps one-to-one onto the controller degrees of freedom that step 6 must choose
between.  KILL-dominant would point at ring motion and timing; CONE_LATERAL at
pointing, which is exactly what the Phase 1H azimuthal sealing law addresses and
why 1H is on hold pending this measurement; CONE_AXIAL at range and fire timing.
A k-means over control vectors would not have said which knob to turn.

FORBIDDEN OUTPUT (carried from the ratified item-2 spec)
--------------------------------------------------------
NO FREQUENCY CLAIMS.  The count of artifacts in a mode is a function of the search
budget and of CEM's basin-of-attraction geometry, not of how often that mode occurs
in any population.  Occupancy is reported as OBSERVED / NOT OBSERVED at this
budget, plus margin ranges.  Counts are printed only as search-effort bookkeeping
and are labelled as such.  A mode seen once is established as existing; a mode seen
often is not thereby established as common.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_replan_falsifier import (replan_search, kill_margin,
                                                  cone_exit_margin, block_times)
from shepherd.scripts.c1_phase1k_frozen_audit import FROZEN
from shepherd.scripts.c1_phase1p_diversity import (_env, witnesses, rollout_for,
                                                   _div_seeds, DIV_BASE_SEEDS, DIAG)
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

MODES = ("KILL", "CONE_LATERAL", "CONE_AXIAL")


def cone_components(endpoints, *, net_apex, n_F, theta_net, range_min, range_max):
    """The two components cone_exit_margin maxes over, kept separate, plus the
    endpoint's position in the cone frame (axial, radius, half-angle)."""
    apex = np.asarray(net_apex, float)
    n = np.asarray(n_F, float); n = n / (np.linalg.norm(n) + 1e-12)
    r = np.asarray(endpoints, float) - apex[None, :]
    rn = np.linalg.norm(r, axis=1)
    ax = r @ n
    ang = np.arccos(np.clip(np.where(rn < 1e-12, 1.0, ax / (rn + 1e-12)), -1.0, 1.0))
    lateral = (ang - float(theta_net)) * rn
    rmax = np.inf if range_max is None else float(range_max)
    axial = np.maximum(float(range_min) - ax, ax - rmax)
    return lateral, axial, ax, rn, ang


def classify(km, cm, lateral, axial):
    """The definitional partition.  Exhaustive and mutually exclusive."""
    out = np.empty(len(km), dtype=object)
    cone_binds = cm <= km
    out[~cone_binds] = "KILL"
    out[cone_binds & (lateral >= axial)] = "CONE_LATERAL"
    out[cone_binds & (axial > lateral)] = "CONE_AXIAL"
    return out


def _artifacts(pe, E, rec, scenario_id, base_seeds):
    """Every VERIFIED escape artifact for one witness under decorrelated streams,
    with its margins re-derived through one code path.  Shared by scan_witness and
    robustness so the two can never diverge."""
    tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P = np.asarray(rec["_lim"][t:], float); Vp = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    cone_kw = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]

    accs = []
    for bs in base_seeds:
        for r in range(DIAG["restarts"]):
            sd_bank, sd_cem = _div_seeds(bs, scenario_id, "w:" + scenario_id, r)
            acc1 = V.reachable_accels(E.a_att_max, DIAG["n_bank"], int(sd_bank))
            ep1, tf1, pts1 = V._seg_paths_turn(p_att, v_att,
                                               np.repeat(acc1[:, None, :], DIAG["K"], axis=1),
                                               tau=tau, attacker_turn_limited=False,
                                               omega_att_max=None, e_att=None, n_t=24)
            sc1 = np.minimum(kill_margin(pts1, L, E.kill_radius, tau),
                             cone_exit_margin(ep1, **cone_kw))
            warm = np.repeat(acc1[int(np.argmax(sc1))][None, :], DIAG["K"], axis=0)
            _b, escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                     L_of_t=L, kill_radius=E.kill_radius, cone_kw=cone_kw,
                                     K=DIAG["K"], pop=DIAG["pop"], iters=DIAG["iters"],
                                     seed=int(sd_cem), warm=warm)
            accs.extend(e["acc"] for e in escs)
    if not accs:
        return None
    A = np.asarray(accs, float)
    ep, tf, pts = V._seg_paths_turn(p_att, v_att, A, tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    km = kill_margin(pts, L, E.kill_radius, tau)
    lat, axi, ax, rn, ang = cone_components(ep, **cone_kw)
    cm = np.maximum(lat, axi)
    keep = (np.minimum(km, cm) > 0) & tf              # re-verify: escapes only
    if not keep.any():
        return None
    return {"A": A[keep], "km": km[keep], "cm": cm[keep], "lat": lat[keep],
            "axi": axi[keep], "ax": ax[keep], "rn": rn[keep], "ang": ang[keep],
            "cone_kw": cone_kw, "n": int(keep.sum())}


def scan_witness(pe, E, rec, scenario_id, base_seeds):
    """Every escape found under decorrelated streams, classified."""
    d = _artifacts(pe, E, rec, scenario_id, base_seeds)
    if d is None:
        return None
    A, km, cm, lat, axi = d["A"], d["km"], d["cm"], d["lat"], d["axi"]
    ax, rn, ang, cone_kw, keep_n = d["ax"], d["rn"], d["ang"], d["cone_kw"], d["n"]
    lab = classify(km, cm, lat, axi)
    per = {}
    for m in MODES:
        s = (lab == m)
        if not s.any():
            per[m] = {"occupancy": "NOT_OBSERVED"}
            continue
        sc = np.minimum(km, cm)[s]
        j = int(np.argmin(sc))                        # tightest escape in this mode
        idx = np.flatnonzero(s)[j]
        per[m] = {"occupancy": "OBSERVED",
                  "n_artifacts_search_bookkeeping_only": int(s.sum()),
                  "binding_margin_m": {"min": float(sc.min()), "max": float(sc.max())},
                  "half_angle_deg": {"min": float(np.degrees(ang[s].min())),
                                     "max": float(np.degrees(ang[s].max()))},
                  "axial_m": {"min": float(ax[s].min()), "max": float(ax[s].max())},
                  "tightest": {"attack_policy_hash": G.attack_policy_hash(A[idx]),
                               "binding_margin_m": float(sc[j]),
                               "kill_margin_m": float(km[idx]),
                               "cone_exit_margin_m": float(cm[idx]),
                               "lateral_m": float(lat[idx]), "axial_m": float(axi[idx]),
                               "half_angle_deg": float(np.degrees(ang[idx])),
                               "saturated": bool((np.linalg.norm(A[idx], axis=1)
                                                  > 0.99 * E.a_att_max).all())}}
    return {"scenario_id": scenario_id, "n_escapes_total": keep_n,
            "theta_net_deg": float(np.degrees(cone_kw["theta_net"])),
            "range_band_m": [float(cone_kw["range_min"]),
                             float(cone_kw["range_max"]) if cone_kw["range_max"] is not None
                             else None],
            "modes": per}


UNCERTAINTY_BUDGET_M = 0.010          # same additive-geometric budget as 1L/1M


def robustness(pe, E, fin, ws):
    """Two ways this partition could be an artefact, both checked.

    (a) If |kill_margin - cone_exit_margin| were ~0 for most escapes, the label
        would be decided by floating-point noise rather than by which constraint
        actually binds.  Reported as the gap distribution.
    (b) The tightest artifacts sit far below the 10 mm additive-geometric budget,
        so occupancy must not rest on them.  Re-reported using only artifacts whose
        binding margin exceeds the budget.
    """
    tot = {m: 0 for m in MODES}; tot_b = dict(tot)
    wocc = {m: 0 for m in MODES}; wocc_b = dict(wocc)
    gaps, nw = [], 0
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        d = _artifacts(pe, E, rec, tag, DIV_BASE_SEEDS)
        if d is None:
            continue
        km, cm, lat, axi = d["km"], d["cm"], d["lat"], d["axi"]
        nw += 1
        lab = classify(km, cm, lat, axi); sc = np.minimum(km, cm)
        gaps.append(np.abs(km - cm)); big = sc > UNCERTAINTY_BUDGET_M
        for m in MODES:
            s = (lab == m)
            tot[m] += int(s.sum()); tot_b[m] += int((s & big).sum())
            wocc[m] += int(s.any()); wocc_b[m] += int((s & big).any())
    g = np.concatenate(gaps)
    pct = {str(q): float(np.percentile(g, q)) for q in (1, 5, 25, 50, 75, 95)}
    print("(a) |kill_margin - cone_exit_margin| over %d escape artifacts" % len(g))
    for q in (1, 5, 25, 50, 75, 95):
        print("    p%-3d %.6f m" % (q, pct[str(q)]))
    print("    gap < 1e-4 m (label could flip on noise): %.4f" % float((g < 1e-4).mean()))
    print("\n(b) occupancy, all artifacts -> artifacts above the %.0f mm budget"
          % (UNCERTAINTY_BUDGET_M * 1000))
    for m in MODES:
        print("    %-13s witnesses %2d/%d -> %2d/%d   artifacts %6d -> %6d"
              % (m, wocc[m], nw, wocc_b[m], nw, tot[m], tot_b[m]))
    return {"gap_percentiles_m": pct,
            "frac_gap_lt_1e-4": float((g < 1e-4).mean()),
            "frac_gap_lt_1e-3": float((g < 1e-3).mean()),
            "n_witnesses": nw, "budget_m": UNCERTAINTY_BUDGET_M,
            "witness_occupancy_all": wocc, "witness_occupancy_above_budget": wocc_b,
            "artifacts_all": tot, "artifacts_above_budget": tot_b,
            "note": "artifact counts are search-effort bookkeeping, NOT frequencies"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_modes.json")
    ap.add_argument("--robustness", action="store_true",
                    help="gap distribution + budget-restricted occupancy")
    a = ap.parse_args()
    if a.robustness:
        pe, E, fin = _env()
        r = robustness(pe, E, fin, witnesses())
        p = pathlib.Path("results/c1_corridor/c1_phase1p_modes_robustness.json")
        p.write_text(json.dumps(r, indent=1, default=float))
        print("\nwrote", p, flush=True)
        return 0
    pe, E, fin = _env()
    ws = witnesses()
    print("== escape MODE partition (decorrelated artifacts only) ==")
    print("   definitional partition, no k and no fitted centroids")
    print("   FREQUENCY CLAIMS ARE FORBIDDEN -- occupancy + margin ranges only\n")

    rows, t0 = [], time.time()
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        r = scan_witness(pe, E, rec, tag, DIV_BASE_SEEDS)
        if r is None:
            print("   %-22s no escape under the diagnostic budget" % tag, flush=True)
            continue
        r["class"] = kind
        rows.append(r)
        flags = "".join(m[0] if r["modes"][m]["occupancy"] == "OBSERVED" else "."
                        for m in ("KILL", "CONE_LATERAL", "CONE_AXIAL"))
        tight = min((r["modes"][m]["tightest"]["binding_margin_m"]
                     for m in MODES if r["modes"][m]["occupancy"] == "OBSERVED"),
                    default=float("nan"))
        print("   %-22s modes[K,L,A]=%s  escapes %5d  tightest %+.5f m"
              % (tag, flags, r["n_escapes_total"], tight), flush=True)

    # system-level occupancy: a mode EXISTS if any witness observed it
    sys_occ = {m: ("OBSERVED" if any(r["modes"][m]["occupancy"] == "OBSERVED" for r in rows)
                   else "NOT_OBSERVED") for m in MODES}
    witness_occ = {m: sum(1 for r in rows if r["modes"][m]["occupancy"] == "OBSERVED")
                   for m in MODES}
    tightest = {}
    for m in MODES:
        c = [(r["modes"][m]["tightest"]["binding_margin_m"], r["scenario_id"])
             for r in rows if r["modes"][m]["occupancy"] == "OBSERVED"]
        tightest[m] = ({"binding_margin_m": min(c)[0], "scenario_id": min(c)[1]}
                       if c else None)

    print("\n   system-level mode occupancy (existence, NOT frequency):")
    for m in MODES:
        t = tightest[m]
        print("     %-13s %-13s  witnesses %2d/%d  tightest %s"
              % (m, sys_occ[m], witness_occ[m], len(rows),
                 ("%+.5f m  (%s)" % (t["binding_margin_m"], t["scenario_id"])) if t else "-"))

    n_obs = sum(1 for m in MODES if sys_occ[m] == "OBSERVED")
    if n_obs == 1:
        implication = ("a SINGLE mode carries every observed escape -- step 6 has one "
                       "controller axis to target")
    elif n_obs == 0:
        implication = "no escape observed at this budget -- nothing to cluster"
    else:
        implication = ("%d distinct modes observed -- a controller closing only one of "
                       "them cannot seal, so step 6 must target the intersection" % n_obs)
    print("\n   implication for step 6: %s" % implication)

    out = {"meta": {"script": "c1_phase1p_modes",
                    "input": "decorrelated (derive_seed mode='diversity') artifacts ONLY",
                    "why": "witness-blind artifacts would measure the shared warm-start "
                           "pool, not the system's mode structure (see 1P step 1)",
                    "partition": "definitional (binding constraint x cone component); "
                                 "no k, no fitted centroids",
                    "modes": {"KILL": "limiter proximity binds -> ring-motion mode",
                              "CONE_LATERAL": "exits through the cone wall -> angular/"
                                              "pointing mode",
                              "CONE_AXIAL": "exits beyond the range band -> range/fire-"
                                            "timing mode"},
                    "forbidden": "NO FREQUENCY CLAIMS -- artifact counts reflect search "
                                 "budget and CEM basin geometry, not population rates. "
                                 "Counts are search-effort bookkeeping only.",
                    "diagnostic_budget": DIAG, "base_seeds": list(DIV_BASE_SEEDS),
                    "protocol": G.PROTOCOL_VERSION},
           "n_witnesses_with_escapes": len(rows),
           "system_mode_occupancy": sys_occ,
           "n_witnesses_observing_mode": witness_occ,
           "tightest_per_mode": tightest,
           "implication_for_step6": implication,
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
