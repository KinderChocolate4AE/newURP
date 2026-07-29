"""C-1 Phase 1P — D1 per-cell search diagnostics (`cands 0` is a number, not a void).

WHY
---
D1 reported `cands 0` in all fifteen cells.  The canary
(`c1_phase1p_d1_canary`) has since shown the pipeline still recognises a known
escape and still emits candidates from one, so the null is a real signal.  But
`0` says nothing about HOW FAR the search got.  A search whose best objective
sat at -0.0004 m and one that sat at -1.9 m are the same integer and completely
different evidence.

So this pass re-runs the identical D1 launches and records, per cell:

    best_search_objective        max over launches of min(kill, cone) reached
    gap_to_candidate_threshold   how far short of the >0 escape threshold
    best_admissibility_margin    a_att_max - max_k ||a_k|| for that candidate
                                 (0 = the attacker was pinned at its limit)
    best_kill_margin_proxy       the kill term of that same candidate
    best_cone_escape_proxy       the cone term of that same candidate

"proxy" is deliberate: these are SAMPLED margins from the search objective, not
continuous-clearance adjudicated ones.  Nothing here is a verdict.

REPRODUCTION IS PART OF THE TEST
--------------------------------
The manifest, the bank draws and the CEM streams are the ones D1 used.  If the
recomputed `n_search_candidates` differs from the recorded D1 value for any
cell, that is a determinism failure and this module says so instead of quietly
reporting new numbers.

NOMENCLATURE
------------
The registry's "cert seeds" named two different streams at once.  Going forward:

    search_bank_seeds   seeds the 20000-point reachable-accel bank (warm start)
    replan_bank_seeds   seeds the CEM replan stream

`c1_phase1p_d1.py` keeps its executed key names (`n_cert_seeds`, `CERT_BANK_IDS`)
because it is an executed artifact and executed artifacts are not rewritten; the
mapping is recorded here and the new names are used from D2a on.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_phase1p_d1 import D1, d1_manifest
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

NOMENCLATURE = {"cert_seeds -> ": "split into two names",
                "search_bank_seeds": "seeds reachable_accels for the warm-start bank "
                                     "(rng_role='warm_start')",
                "replan_bank_seeds": "seeds the CEM replan stream (rng_role='cem')",
                "executed_module_keys_unchanged":
                    "c1_phase1p_d1.py retains n_cert_seeds / CERT_BANK_IDS as executed"}

SCOPE = {"ATTACKER_CLASS": "K4_PIECEWISE_CONSTANT",
         "RESET_SCOPE": "FIXED_RESET_1100",
         "PROTOCOL": "D1_SCENARIO_AWARE_SEED_AMENDMENT_V1",
         "SAMPLE_STRUCTURE": "15 controller artifacts over 9 UNIQUE scenarios — "
                             "not 15 independent samples",
         "CLASS_SCOPE": "Class A only; Class B (MAXCLR) is a separate recovery track"}

VERSION_RECORD = [
    {"version": "D1-v0", "seeding": "registry literal constants 64000201-16 / 91000101-3, "
                                    "witness-blind (pre-C-6)",
     "status": "NOT EXECUTED / INVALIDATED",
     "reason": "witness-blind streams hand every scenario the same attacker; this is the "
               "C-6 defect the campaign confirmed twice and hit a third time in replan_at"},
    {"version": "D1-v1", "seeding": "counts honoured exactly; seed VALUES derived from the "
                                    "central d0_seed with stage_id='D1'",
     "status": "EXECUTED",
     "phrasing": "counts-preserving corrective-amended D1"},
]


def cell_diagnostics(E, pa, va, P, Vp, cone, tau, scenario_id):
    """Re-run D1's launches for one cell, observing only."""
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    n_cand = 0
    bank_best = -np.inf
    best = {"score": -np.inf}
    per_launch = []
    for m in d1_manifest(scenario_id):
        a1 = V.reachable_accels(E.a_att_max, D1["n_bank"], int(m["warm"]))
        ee, tt, pp = V._seg_paths_turn(pa, va, np.repeat(a1[:, None, :], D1["K"], axis=1),
                                       tau=tau, attacker_turn_limited=False,
                                       omega_att_max=None, e_att=None, n_t=24)
        s1 = np.minimum(kill_margin(pp, L, E.kill_radius, tau),
                        cone_exit_margin(ee, **cone))
        j = int(np.argmax(s1))
        bank_best = max(bank_best, float(s1[j]))
        warm = np.repeat(a1[j][None, :], D1["K"], axis=0)
        b, es = replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                              kill_radius=E.kill_radius, cone_kw=cone, K=D1["K"],
                              pop=D1["pop"], iters=D1["iters"], seed=int(m["cem"]),
                              warm=warm)
        n_cand += len(es)
        per_launch.append(float(b["score"]))
        if b["score"] > best["score"]:
            best = {k: b[k] for k in ("score", "kill_margin", "cone_exit_margin")}
            best["acc"] = np.asarray(b["acc"], float)
    acc = best.get("acc")
    adm = (float(E.a_att_max - np.linalg.norm(acc, axis=1).max())
           if acc is not None else None)
    pl = np.asarray(per_launch, float)
    return {"n_search_candidates_recomputed": n_cand,
            # the K=4 incumbent this cell's search converged on.  D2a MUST embed it
            # into the K=8 initial population, otherwise K=8 could look "safer" than
            # K=4 purely because its search started from scratch in a wider space.
            "k4_incumbent_acc": acc.tolist() if acc is not None else None,
            "k4_incumbent_hash": (G.attack_policy_hash(acc) if acc is not None else None),
            "best_search_objective_m": float(best["score"]),
            "gap_to_candidate_threshold_m": float(-best["score"]),
            "best_admissibility_margin_mps2": adm,
            "best_kill_margin_proxy_m": float(best["kill_margin"]),
            "best_cone_escape_proxy_m": float(best["cone_exit_margin"]),
            "warm_start_bank_best_objective_m": float(bank_best),
            "per_launch_best_objective_m": {"n": int(pl.size),
                                            "max": float(pl.max()),
                                            "median": float(np.median(pl)),
                                            "min": float(pl.min())},
            "note": "sampled proxies from the search objective; NOT continuous-clearance "
                    "adjudicated and NOT a verdict"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d1", default="results/c1_corridor/c1_phase1p_d1.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_d1_diag.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d1 = json.loads(pathlib.Path(a.d1).read_text())

    print("== D1 per-cell search diagnostics ==")
    print("   `cands 0` is a number; this pass reports how far short the search fell")
    print("   scope: %s / %s / %s\n"
          % (SCOPE["ATTACKER_CLASS"], SCOPE["RESET_SCOPE"], SCOPE["PROTOCOL"]))
    print("   %-22s %-10s %7s %12s %12s %10s"
          % ("scenario", "arm", "delta", "best obj", "gap", "adm slack"))

    rows, mismatches = [], []
    for c in d1["rows"]:
        tag, arm, dl = c["witness"], c["arm"], c["selected_delta_m"]
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        P, Vv, _A, _b, _r = dynamic_inward(P0, Vp0, dl)
        d = cell_diagnostics(E, pa, va, P, Vv, cone, tau, tag)
        same = d["n_search_candidates_recomputed"] == c["d1"]["n_search_candidates"]
        if not same:
            mismatches.append({"witness": tag, "arm": arm,
                               "recorded": c["d1"]["n_search_candidates"],
                               "recomputed": d["n_search_candidates_recomputed"]})
        rows.append({"witness": tag, "arm": arm, "selected_delta_m": dl,
                     "verdict_recorded": c["verdict"],
                     "reproduces_d1_candidate_count": bool(same), **d})
        print("   %-22s %-10s %7.3f %12.6f %12.6f %10.4f"
              % (tag, arm, dl, d["best_search_objective_m"],
                 d["gap_to_candidate_threshold_m"],
                 d["best_admissibility_margin_mps2"]), flush=True)

    gaps = np.asarray([r["gap_to_candidate_threshold_m"] for r in rows], float)
    print("\n   gap to threshold   min %.6f m   median %.6f m   max %.6f m"
          % (gaps.min(), np.median(gaps), gaps.max()))
    print("   determinism: %s"
          % ("all %d cells reproduce D1's candidate count" % len(rows) if not mismatches
             else "MISMATCH %s" % mismatches))

    out = {"meta": {"script": "c1_phase1p_d1_diag",
                    "role": "observer only; re-runs D1's own launches and records how far "
                            "the search got. Changes no controller and no verdict",
                    "scope_tags": SCOPE, "nomenclature": NOMENCLATURE,
                    "version_record": VERSION_RECORD,
                    "budget_phrasing": "D1 is 4x D0's SEARCH LAUNCHES within the SAME K4 "
                                       "attacker class — not a stronger attacker",
                    "determinism_check": "recomputed candidate counts must equal D1's"},
           "determinism_ok": not mismatches, "mismatches": mismatches,
           "gap_summary_m": {"min": float(gaps.min()), "median": float(np.median(gaps)),
                             "max": float(gaps.max())},
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
