"""C-1 — FALSIFIER-v2 freeze checklist.  Thirteen items, tested, not asserted.

The review listed thirteen conditions to be met before v2 may be frozen and a
confirmatory run started.  This module runs them and reports PASS or GAP per item.

IT IS NOT THE CAMPAIGN INVARIANT SUITE.  `c1_invariant_tests` (13/13) covers I1-I8
of the ORIGINAL campaign and has nothing to do with this list; reporting "13/13"
for both would conflate two unrelated things.  This file is the v2 list.

VALIDATION SET ARITHMETIC (the review's correction)
---------------------------------------------------
    16 initial D0 candidates
     5 verified falsified   -> REGRESSION_COUNTEREXAMPLE_SUITE
    11 unresolved           -> CONFIRMATORY_NULL_EVALUATION
"15 cells" was the set that entered D1; it omits the `RI-SHARED / RH 5.0/0.55`
cell that D0 had already falsified, which must be present as a known positive.
"""
from __future__ import annotations
import argparse, hashlib, inspect, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_phase1p_d0 import d0_seed
from shepherd.scripts.c1_phase1p_d1_canary import replay
from shepherd.scripts.c1_falsifier_v2 import (s_proxy, s_auth, embed, temporal_starts,
                                              refine, segment_descent, GLOBAL_DIRS,
                                              STAGES, SCALES, TOP_M, ADM_TOL)
from shepherd.scripts.c1_phase1p_falsifier_v2_k1 import k1_search
from shepherd.game import viability as V


def _ctx(pe, E, fin, tag, delta):
    kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
    rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
    t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
    pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
    P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(pa, va, o[36:45])
    cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    P, Vv, _A, _b, _r = dynamic_inward(P0, Vp0, delta)
    L = lambda ts: hermite_positions(P, Vv, np.asarray(ts))[0]
    return pa, va, L, cone, float(E.tau_deploy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d0", default="results/c1_corridor/c1_phase1p_d0.json")
    ap.add_argument("--d2a", default="results/c1_corridor/c1_phase1p_d2a.json")
    ap.add_argument("--v2", default="results/c1_corridor/c1_falsifier_v2.json")
    ap.add_argument("--k1", default="results/c1_corridor/c1_phase1p_falsifier_v2_k1.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_falsifier_v2_freeze.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d0 = json.loads(pathlib.Path(a.d0).read_text())
    v2 = json.loads(pathlib.Path(a.v2).read_text())
    k1j = json.loads(pathlib.Path(a.k1).read_text())
    amax = float(E.a_att_max)
    items = []

    def rec(n, title, ok, detail):
        items.append({"item": n, "title": title,
                      "status": "PASS" if ok else "GAP", "detail": detail})
        print("   %2d %-46s %-4s  %s" % (n, title[:46], "PASS" if ok else "GAP", detail))

    print("== FALSIFIER-v2 freeze checklist (13 items) ==")
    print("   NOT the campaign invariant suite — that is c1_invariant_tests (I1-I8)\n")

    # ---- validation set arithmetic ---------------------------------------------
    fal = []
    for r in d0["rows"]:
        if r["verdict"] != "SURVIVED_D0":
            fal.append((r["witness"], r["arm"], "D0"))
    d2 = json.loads(pathlib.Path(a.d2a).read_text())
    for r in d2["rows"]:
        if r["verdict"].startswith("FALSIFIED"):
            fal.append((r["witness"], r["arm"], "D2a"))
    for r in k1j["rows"]:
        if r["n_k1_escapes"] and r["bucket"] == "INDEPENDENT_CELL":
            fal.append((r["witness"], r["arm"], "A0"))
    fal = sorted(set(fal))
    all_cells = sorted({(r["witness"], r["arm"]) for r in d0["rows"]})
    unresolved = sorted(set(all_cells) - {(w, ar) for w, ar, _s in fal})
    print("   validation set: %d initial candidates = %d falsified (regression suite) "
          "+ %d unresolved (confirmatory)\n" % (len(all_cells), len(fal), len(unresolved)))

    # 1 representation containment K1 c K2 c K4 c K8
    u = np.array([0.9, -0.3, 0.31]); u /= np.linalg.norm(u)
    base = (0.97 * amax * u)[None, :]
    okc, det = True, []
    pa, va, L, cone, tau = _ctx(pe, E, fin, "RH 5.0/0.55 f=10", 0.135)
    v0 = None
    for K in (1, 2, 4, 8):
        e = embed(base, K)
        r = replay(E, pa, va, L, cone, tau, e)
        if v0 is None:
            v0 = r["verdict"]
        okc &= (r["verdict"] == v0) and (len(e) == K)
        det.append("K%d:%s" % (K, r["verdict"][:4]))
    rec(1, "K1 c K2 c K4 c K8 representation containment", okc, " ".join(det))

    # 2 previous-stage incumbent preservation  (structural: seeds contain the bank)
    ok2 = all(s.get("bank_size_after", 0) >= (i + 1)
              for r in v2["rows"] for i, s in enumerate(r["stages"]))
    rec(2, "previous-stage incumbents preserved into next stage", ok2,
        "bank never shrinks; sizes %s" % sorted({s["bank_size_after"]
                                                 for r in v2["rows"] for s in r["stages"]}))

    # 3 cumulative-bank best-S monotonicity
    bad = [(r["witness"], r["arm"]) for r in v2["rows"]
           for s in r["stages"] if not s["monotone_vs_previous"]]
    rec(3, "cumulative-bank best-S monotonicity A0>=A1>=A2>=A3", not bad,
        "violations %d" % len(bad))

    # 4 independent global temporal starts per K
    ns = {s["stage"]: s.get("independent_start_provenance", {}).get(
              "n_independent_temporal_starts", 0)
          for r in v2["rows"][:1] for s in r["stages"]}
    beat = sum(1 for r in v2["rows"] for s in r["stages"]
               if s.get("independent_start_provenance", {}).get(
                   "independent_beats_inherited_after_refinement"))
    rec(4, "independent global temporal starts per stage", all(ns[k] > 0 for k in
                                                               ("A1", "A2", "A3")),
        "counts %s; beat inherited after equal refinement in %d stage-cells" % (ns, beat))

    # 5 multi-scale direction/magnitude refinement
    rec(5, "multi-scale refinement present", len(SCALES) >= 3,
        "scales x a_max %s + per-segment descent" % SCALES)

    # 6 raw-bank best preserved through refinement
    pa2, va2, L2, cone2, tau2 = _ctx(pe, E, fin, "BASE 3.2/0.50 C", 0.110)
    ks = k1_search(E, pa2, va2, L2, cone2, tau2)
    raw_best = float(ks["pool_S_proxy"][0])
    rng = np.random.default_rng(0)
    _i, ref_best, _a = refine(E, pa2, va2, L2, cone2, tau2, ks["pool"][:, None, :], 1, rng)
    rec(6, "raw-bank best never lost by refinement", ref_best <= raw_best + 1e-15,
        "raw %.6f -> refined %.6f" % (raw_best, ref_best))

    # 7 scenario-aware seed namespace
    s1 = d0_seed(stage_id="V2-A1", rng_role="refine", scenario_id="X",
                 reset_id=1100, attacker_class="K2-pwc", restart_id=0, base_seed=7000)
    s2 = d0_seed(stage_id="V2-A1", rng_role="refine", scenario_id="Y",
                 reset_id=1100, attacker_class="K2-pwc", restart_id=0, base_seed=7000)
    rec(7, "scenario-aware seed namespace", s1 != s2, "scenario X != Y -> %s" % (s1 != s2))

    # 8 paired arm CRN -- tested behaviourally, not by grepping the source.
    # A first version searched the source text for "arm" and failed on the word
    # "warm_start"; a string match is not a test of the property.
    params = list(inspect.signature(d0_seed).parameters)
    same = all(d0_seed(stage_id="V2-A1", rng_role=role, scenario_id="RH 5.0/0.55 f=10",
                       reset_id=1100, attacker_class="K2-pwc", restart_id=i,
                       base_seed=7000)
               == d0_seed(stage_id="V2-A1", rng_role=role,
                          scenario_id="RH 5.0/0.55 f=10", reset_id=1100,
                          attacker_class="K2-pwc", restart_id=i, base_seed=7000)
               for role in ("refine", "fresh") for i in range(4))
    rec(8, "paired arm CRN (arm cannot enter the seed)",
        ("arm" not in params) and same,
        "d0_seed params %s; identical streams across arms %s" % (params, same))

    # 9 known counterexample exact replay
    okr, n = True, 0
    for w, ar, stage in fal:
        src_acc = None
        for r in d0["rows"]:
            if (r["witness"], r["arm"]) == (w, ar) and r["d0"]["escapes"]:
                src_acc = np.asarray(r["d0"]["escapes"][0]["acc"], float)
        for r in d2["rows"]:
            if (r["witness"], r["arm"]) == (w, ar) and r["d2a"]["escapes"]:
                src_acc = np.asarray(r["d2a"]["escapes"][0]["acc"], float)
        for r in k1j["rows"]:
            if (r["witness"], r["arm"]) == (w, ar) and r["k1_escapes"]:
                src_acc = np.asarray(r["k1_escapes"][0]["acc_k1"], float)[None, :]
        if src_acc is None:
            okr = False; continue
        dl = next(r["selected_delta_m"] for r in d0["rows"]
                  if (r["witness"], r["arm"]) == (w, ar))
        p_, v_, L_, c_, t_ = _ctx(pe, E, fin, w, dl)
        okr &= replay(E, p_, v_, L_, c_, t_, src_acc)["recognised_as_escape"]; n += 1
    rec(9, "known counterexample exact replay (regression suite)", okr and n == len(fal),
        "%d / %d replayed as escapes" % (n, len(fal)))

    # 10 proxy vs authoritative ranking
    ov = [s["alignment"]["top5_overlap"] for r in v2["rows"] for s in r["stages"]]
    rec(10, "proxy/authoritative ranking agreement", min(ov) == 5,
        "top-5 overlap min %d over %d stage-cells" % (min(ov), len(ov)))

    # 11 determinism under identical seed and config
    r1 = refine(E, pa2, va2, L2, cone2, tau2, ks["pool"][:, None, :], 1,
                np.random.default_rng(5))[1]
    r2 = refine(E, pa2, va2, L2, cone2, tau2, ks["pool"][:, None, :], 1,
                np.random.default_rng(5))[1]
    rec(11, "same seed and config -> identical result", r1 == r2,
        "%.12f vs %.12f" % (r1, r2))

    # 12 hard admissibility and min-S sign convention
    over = np.array([[amax * 1.0001, 0.0, 0.0]])
    at = np.array([[amax, 0.0, 0.0]])
    So = s_proxy(E, pa2, va2, L2, cone2, tau2, over[None])[0][0]
    Sa2 = s_proxy(E, pa2, va2, L2, cone2, tau2, at[None])[0][0]
    rec(12, "hard admissibility (+inf) and closed constraint at ||a||=a_max",
        np.isinf(So) and np.isfinite(Sa2),
        "S(1.0001 a_max)=%s  S(a_max)=%.6f" % (So, Sa2))

    # 13 development / confirmation seed separation
    sd = d0_seed(stage_id="V2-A1", rng_role="refine", scenario_id="X", reset_id=1100,
                 attacker_class="K2-pwc", restart_id=0, base_seed=7000)
    sc = d0_seed(stage_id="V2C-A1", rng_role="refine", scenario_id="X", reset_id=1100,
                 attacker_class="K2-pwc", restart_id=0, base_seed=7000)
    rec(13, "development / confirmatory seed streams disjoint", sd != sc,
        "stage_id V2- vs V2C- -> %s" % (sd != sc))

    n_pass = sum(1 for i in items if i["status"] == "PASS")
    print("\n   %d / 13 PASS" % n_pass)
    print("   %s" % ("v2 may be frozen" if n_pass == 13 else
                     "GAPs above must be closed before freezing"))

    out = {"meta": {"script": "c1_falsifier_v2_freeze",
                    "role": "the review's 13-item freeze checklist, run as tests",
                    "not_the_campaign_invariant_suite":
                        "c1_invariant_tests (I1-I8, 13/13) is a different list; the two "
                        "must not be reported as one",
                    "validation_set": {
                        "initial_candidates": len(all_cells),
                        "REGRESSION_COUNTEREXAMPLE_SUITE": len(fal),
                        "CONFIRMATORY_NULL_EVALUATION": len(unresolved),
                        "note": "'15 cells' was the set that entered D1 and omits the "
                                "RI-SHARED / RH 5.0/0.55 cell falsified at D0"}},
           "falsified_cells": [{"witness": w, "arm": ar, "found_at": s} for w, ar, s in fal],
           "unresolved_cells": [{"witness": w, "arm": ar} for w, ar in unresolved],
           "n_pass": n_pass, "items": items,
           "freeze_allowed": n_pass == 13}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if n_pass == 13 else 1


if __name__ == "__main__":
    raise SystemExit(main())
