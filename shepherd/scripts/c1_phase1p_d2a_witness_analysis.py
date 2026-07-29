"""C-1 Phase 1P — what the single D2a escape actually is.

THE OBSERVATION THAT FORCES THIS
--------------------------------
D2a falsified exactly one cell, `RH 5.0/0.55 f=10 / RI-GMAX` (delta 0.135), and
the witness it returned has ALL EIGHT SEGMENTS EQUAL.  A control that is constant
over the whole deploy window is representable at K=4 -- indeed at K=1.  So the
naive reading, "the wider K=8 class was needed to break this controller", is
almost certainly false and must be tested rather than assumed.

WHAT THIS MODULE ESTABLISHES
----------------------------
  A  class membership
     the witness re-expressed at K=1, K=2, K=4 and K=8 must give the SAME verdict.
     If it does, the attack lies inside the K=4 class D1 already searched.
  B  provenance inside D2a
     `replan_search` installs the warm-start vector as member 0 of iteration 0, so
     a raw bank draw can win outright.  This checks whether the escape equals the
     bank argmax of some D2a launch -- i.e. whether CEM contributed anything.
  C  what D1 saw
     D1's own 48 bank draws for the same cell are regenerated and searched for
     their nearest neighbour to the escape direction.  Two very different
     conclusions are possible and the data decides:
        near neighbour with a NEGATIVE score  -> the escape set is tiny and both
                                                 nulls are seed-fragile
        no near neighbour at all              -> D1 simply never sampled there

WHY IT MATTERS
--------------
If A and B hold, then D2a did not demonstrate that K=8 beats a K=4-robust
controller.  It demonstrated that the D1 null on that cell was a SEARCH MISS
inside D1's own attacker class -- which is a statement about the falsifier, and it
weakens every other null at the same knife edge.  Reporting this as "the wider
class broke it" would be wrong in the defender's favour.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_replan_falsifier import kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_phase1p_d1 import D1, d1_manifest
from shepherd.scripts.c1_phase1p_d2a import D2A, d2a_manifest
from shepherd.scripts.c1_phase1p_d1_canary import _ctx, replay
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

NEAR_DEG = 5.0


def reexpress(acc, K):
    """The same control signal at a different segment count.  Only defined when the
    witness is constant (which is exactly the case under test)."""
    a = np.asarray(acc, float)
    return np.repeat(a[:1], K, axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2a", default="results/c1_corridor/c1_phase1p_d2a.json")
    ap.add_argument("--out",
                    default="results/c1_corridor/c1_phase1p_d2a_witness_analysis.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d2a = json.loads(pathlib.Path(a.d2a).read_text())
    fal = [r for r in d2a["rows"] if r["verdict"] == "FALSIFIED_BY_ADVERSARIAL_REPLAN_D2A"]
    if not fal:
        print("no D2a falsification to analyse"); return 0

    out_rows = []
    for r in fal:
        tag, arm, dl = r["witness"], r["arm"], r["selected_delta_m"]
        e = r["d2a"]["escapes"][0]
        acc8 = np.asarray(e["acc"], float)
        const = bool(np.all(np.abs(acc8 - acc8[0]) < 1e-12))
        print("== D2a witness analysis: %s / %s  delta %.3f ==" % (tag, arm, dl))
        print("   witness hash %s   mode %s   continuous margin %+.6f m"
              % (e["attack_policy_hash"], e["mode"], e["continuous_kill_margin_m"]))
        print("   all eight segments equal: %s   ||a|| = %.4f (a_max %.1f)"
              % (const, float(np.linalg.norm(acc8[0])), E.a_att_max))

        pa, va, L, cone, tau = _ctx(pe, E, fin, tag, dl)

        # ---- A  class membership
        A_res = {}
        for K in (1, 2, 4, 8):
            rr = replay(E, pa, va, L, cone, tau, reexpress(acc8, K))
            A_res["K%d" % K] = {"verdict": rr["verdict"],
                                "continuous_kill_margin_m": rr["continuous_kill_margin_m"],
                                "cone_exit_margin_m": rr["cone_exit_margin_m"],
                                "recognised_as_escape": rr["recognised_as_escape"]}
            print("   A  re-expressed at K=%d -> %-24s margin %+.6f  escape %s"
                  % (K, rr["verdict"], rr["continuous_kill_margin_m"],
                     rr["recognised_as_escape"]))
        inside_k4 = bool(const and A_res["K4"]["recognised_as_escape"])

        # ---- B  provenance: is it a raw D2a bank argmax?
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        P, Vv, _A, _b, _r = dynamic_inward(P0, Vp0, dl)
        Lf = lambda ts: hermite_positions(P, Vv, np.asarray(ts))[0]
        hit = None
        for m in d2a_manifest(tag):
            if m["block"] != "bank_warm":
                continue
            a1 = V.reachable_accels(E.a_att_max, D2A["n_bank"], int(m["warm"]))
            ee, tt, pp = V._seg_paths_turn(pa, va, np.repeat(a1[:, None, :], D2A["K"], axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
            s1 = np.minimum(kill_margin(pp, Lf, E.kill_radius, tau),
                            cone_exit_margin(ee, **cone))
            j = int(np.argmax(s1))
            if np.abs(a1[j] - acc8[0]).max() < 1e-12:
                hit = {"search_bank_seed_id": m["search_bank_seed_id"],
                       "restart": m["restart"], "bank_argmax_score_m": float(s1[j])}
                break
        print("   B  equals a D2a bank argmax: %s" % (hit if hit else "NO"))

        # ---- C  what D1's own draws contained
        u = acc8[0] / np.linalg.norm(acc8[0])
        best_ang, best_sc, n_near, near_best_sc = 180.0, None, 0, -np.inf
        for m in d1_manifest(tag):
            a1 = V.reachable_accels(E.a_att_max, D1["n_bank"], int(m["warm"]))
            nrm = np.linalg.norm(a1, axis=1) + 1e-12
            cosang = np.clip(a1 @ u / nrm, -1.0, 1.0)
            ang = np.degrees(np.arccos(cosang))
            near = ang <= NEAR_DEG
            if near.any():
                ee, tt, pp = V._seg_paths_turn(pa, va,
                                               np.repeat(a1[near][:, None, :], D1["K"], axis=1),
                                               tau=tau, attacker_turn_limited=False,
                                               omega_att_max=None, e_att=None, n_t=24)
                sc = np.minimum(kill_margin(pp, Lf, E.kill_radius, tau),
                                cone_exit_margin(ee, **cone))
                n_near += int(near.sum()); near_best_sc = max(near_best_sc, float(sc.max()))
            k = int(np.argmin(ang))
            if ang[k] < best_ang:
                ee, tt, pp = V._seg_paths_turn(pa, va,
                                               np.repeat(a1[k][None, None, :], D1["K"], axis=1),
                                               tau=tau, attacker_turn_limited=False,
                                               omega_att_max=None, e_att=None, n_t=24)
                sc = np.minimum(kill_margin(pp, Lf, E.kill_radius, tau),
                                cone_exit_margin(ee, **cone))
                best_ang, best_sc = float(ang[k]), float(sc[0])
        print("   C  D1's nearest bank sample: %.3f deg away, score %+.6f m"
              % (best_ang, best_sc))
        print("      D1 samples within %.1f deg: %d   best score there %+.6f m"
              % (NEAR_DEG, n_near, near_best_sc if n_near else float("nan")))

        interp = ("SEARCH_MISS_INSIDE_K4_CLASS" if inside_k4
                  else "REQUIRES_WIDER_THAN_K4_CLASS")
        out_rows.append({
            "witness": tag, "arm": arm, "delta_m": dl,
            "escape_hash": e["attack_policy_hash"], "mode": e["mode"],
            "continuous_kill_margin_m": e["continuous_kill_margin_m"],
            "all_segments_equal": const,
            "acc_norm_mps2": float(np.linalg.norm(acc8[0])),
            "a_att_max_mps2": float(E.a_att_max),
            "A_class_membership": A_res, "A_inside_k4_class": inside_k4,
            "B_equals_d2a_bank_argmax": hit,
            "B_cem_contributed": hit is None,
            "C_d1_nearest_sample_deg": best_ang,
            "C_d1_nearest_sample_score_m": best_sc,
            "C_d1_samples_within_%.0fdeg" % NEAR_DEG: n_near,
            "C_d1_best_score_within_band_m": (near_best_sc if n_near else None),
            "interpretation": interp})

    ok_all = all(r["A_inside_k4_class"] for r in out_rows)
    print("\n   interpretation: %s"
          % ("the D2a escape lies INSIDE the K=4 class D1 already searched -> the D1 "
             "null on that cell was a SEARCH MISS, not evidence of K=4 robustness"
             if ok_all else
             "at least one escape genuinely needs a class wider than K=4"))

    out = {"meta": {"script": "c1_phase1p_d2a_witness_analysis",
                    "role": "adjudicates what the D2a escape means; no controller changes",
                    "tests": {"A": "class membership by re-expression at K=1,2,4,8",
                              "B": "provenance: raw bank argmax vs CEM refinement",
                              "C": "what D1's own 48 bank draws contained near it"},
                    "near_band_deg": NEAR_DEG},
           "all_escapes_inside_k4_class": ok_all, "rows": out_rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
