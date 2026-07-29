"""C-1 — adversarial verification of the K=1 counterexamples found by FALSIFIER-v2 A0.

A search that finds what it was built to find is not evidence.  Before any of the
three new K=1 escapes is allowed to overturn a null, it has to survive being
attacked from the other direction.

FOUR CHECKS
-----------
  V1  independent code path
      each candidate is re-adjudicated by `c1_phase1p_d1_canary.replay`, which was
      written for a different purpose and does not share this module's scoring.
  V2  class membership
      re-expressed at K=1, 2, 4 and 8.  If the verdict is not identical at every K
      the attack is not the within-class object it is claimed to be.
  V3  saturation-shell characterisation
      every candidate sits at ||a|| = a_att_max to floating point.  The admissible
      set is closed, so that is legal -- but a counterexample that exists ONLY at
      the exact shell is a different (weaker) object from one that survives a
      finite magnitude interval.  The magnitude is scanned inward at fixed
      direction and the escape interval is measured, not assumed.
  V4  reachability by the legacy sampler
      `reachable_accels` draws uniform-in-VOLUME (mag = a_max * U^(1/3)), so the
      near-shell region is thin.  With the measured direction tolerance this gives
      the per-draw hit probability the legacy bank actually had -- the quantitative
      version of "D1 missed it".

DISTINCTNESS
------------
The A0 pool reports its top-48 refined candidates.  Those collapse to ONE distinct
attack per cell.  This module reports distinct attack hashes; "48 escapes" would be
the same counterexample counted 48 times.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_phase1p_diversity import _env
from shepherd.scripts.c1_phase1p_d1_canary import _ctx, replay
from shepherd.scripts.c1_phase1p_falsifier_v2_k1 import s_auth, ADM_TOL
from shepherd.scripts import c1_governance as G

MAG_SCAN_M = 0.20          # inward magnitude scan depth, m/s^2
MAG_STEPS = 401
DIR_TOL_TEST_DEG = (0.5, 0.2, 0.1, 0.05, 0.02, 0.01)


def k_expand(a, K):
    return np.repeat(np.asarray(a, float).reshape(1, 3), K, axis=0)


def magnitude_interval(E, pa, va, L, cone, tau, a):
    """V3 -- how far inward from the shell does the escape survive, at fixed direction?"""
    a = np.asarray(a, float); n0 = float(np.linalg.norm(a)); u = a / n0
    mags = np.linspace(n0 - MAG_SCAN_M, n0, MAG_STEPS)
    ok = []
    for m in mags:
        r = s_auth(E, pa, va, L, cone, tau, u * m)
        ok.append(bool(r["is_escape"]))
    ok = np.asarray(ok)
    if not ok.any():
        return {"escape_magnitude_interval_mps2": 0.0, "lowest_escaping_norm": None,
                "shell_only": True}
    lo = float(mags[np.argmax(ok)])
    return {"escape_magnitude_interval_mps2": float(n0 - lo),
            "lowest_escaping_norm": lo,
            "contiguous_from_shell": bool(ok[np.argmax(ok):].all()),
            "shell_only": bool(n0 - lo < 1e-6)}


def direction_tolerance(E, pa, va, L, cone, tau, a):
    """V4 input -- the angular half-width of the escape cone around this attack."""
    a = np.asarray(a, float); n0 = float(np.linalg.norm(a)); u = a / n0
    b = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(u, b); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    out = {}
    for dg in DIR_TOL_TEST_DEG:
        r = np.radians(dg)
        hits = 0
        for al, be in ((r, 0), (-r, 0), (0, r), (0, -r),
                       (r / 1.414, r / 1.414), (-r / 1.414, -r / 1.414)):
            v = u + al * e1 + be * e2
            v /= np.linalg.norm(v)
            if s_auth(E, pa, va, L, cone, tau, v * n0)["is_escape"]:
                hits += 1
        out["%.2fdeg" % dg] = "%d/6" % hits
        if hits == 6:
            out["largest_all_directions_deg"] = dg
            break
    return out


def hit_probability(theta_deg, n_shell_frac, n_bank, n_draws):
    """V4 -- P(a uniform-in-volume bank draw lands in the escape region), and the
    chance the legacy budget saw it at least once."""
    th = np.radians(theta_deg)
    solid_frac = (1.0 - np.cos(th)) / 2.0            # cap of half-angle th over sphere
    p_one = solid_frac * n_shell_frac
    p_draw = 1.0 - (1.0 - p_one) ** n_bank
    return {"solid_angle_fraction": float(solid_frac),
            "shell_magnitude_fraction": float(n_shell_frac),
            "p_single_sample": float(p_one),
            "p_at_least_one_per_bank_draw": float(p_draw),
            "p_at_least_once_in_budget": float(1.0 - (1.0 - p_draw) ** n_draws),
            "n_bank": n_bank, "n_draws": n_draws}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k1", default="results/c1_corridor/c1_phase1p_falsifier_v2_k1.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_v2k1_verify.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    k1 = json.loads(pathlib.Path(a.k1).read_text())

    print("== adversarial verification of the FALSIFIER-v2 A0 counterexamples ==")
    print("   a search that finds what it was built to find is not evidence\n")

    rows = []
    for r in k1["rows"]:
        if not r["n_k1_escapes"]:
            continue
        tag, arm, dl = r["witness"], r["arm"], r["selected_delta_m"]
        uniq = {}
        for e in r["k1_escapes"]:
            uniq.setdefault(e["attack_policy_hash"], e)
        pa, va, L, cone, tau = _ctx(pe, E, fin, tag, dl)
        print("   %-22s %-10s  %-18s  distinct attacks %d"
              % (tag, arm, r["bucket"], len(uniq)))
        for h, e in uniq.items():
            acc = np.asarray(e["acc_k1"], float)
            # V1 independent code path, V2 class membership
            per_k = {}
            for K in (1, 2, 4, 8):
                rr = replay(E, pa, va, L, cone, tau, k_expand(acc, K))
                per_k["K%d" % K] = {"verdict": rr["verdict"],
                                    "continuous_kill_margin_m":
                                        rr["continuous_kill_margin_m"],
                                    "cone_exit_margin_m": rr["cone_exit_margin_m"],
                                    "recognised_as_escape": rr["recognised_as_escape"]}
            v1 = bool(per_k["K1"]["recognised_as_escape"])
            v2 = bool(len({per_k[k]["verdict"] for k in per_k}) == 1
                      and all(per_k[k]["recognised_as_escape"] for k in per_k))
            mi = magnitude_interval(E, pa, va, L, cone, tau, acc)
            dt = direction_tolerance(E, pa, va, L, cone, tau, acc)
            th = dt.get("largest_all_directions_deg", min(DIR_TOL_TEST_DEG))
            n0 = float(np.linalg.norm(acc))
            lo = mi["lowest_escaping_norm"] or n0
            shell_frac = max((n0 ** 3 - lo ** 3) / (float(E.a_att_max) ** 3), 0.0)
            hp = hit_probability(th, shell_frac, 20000, 48)
            rows.append({"witness": tag, "arm": arm, "delta_m": dl,
                         "bucket": r["bucket"], "attack_policy_hash": h,
                         "acc_k1": acc.tolist(), "acc_norm_mps2": n0,
                         "V1_independent_path_escape": v1,
                         "V2_class_membership_identical": v2, "V2_per_K": per_k,
                         "V3_magnitude": mi, "V4_direction_tolerance": dt,
                         "V4_legacy_bank_hit_probability": hp})
            print("      %s  V1 %s  V2 %s  |a| %.4f  mag-interval %.4f m/s^2  "
                  "dir-tol %s  P(legacy budget saw it) %.4f"
                  % (h, "OK" if v1 else "FAIL", "OK" if v2 else "FAIL", n0,
                     mi["escape_magnitude_interval_mps2"],
                     dt.get("largest_all_directions_deg", "<%.2fdeg" % min(DIR_TOL_TEST_DEG)),
                     hp["p_at_least_once_in_budget"]), flush=True)

    ind = [r for r in rows if r["bucket"] == "INDEPENDENT_CELL"]
    ok = all(r["V1_independent_path_escape"] and r["V2_class_membership_identical"]
             for r in rows)
    print("\n   V1 independent path       %s" % ("PASS" if all(
        r["V1_independent_path_escape"] for r in rows) else "FAIL"))
    print("   V2 K=1/2/4/8 identical    %s" % ("PASS" if all(
        r["V2_class_membership_identical"] for r in rows) else "FAIL"))
    print("   distinct NEW counterexamples in independent cells: %d over %d cells"
          % (len(ind), len({(r['witness'], r['arm']) for r in ind})))

    out = {"meta": {"script": "c1_phase1p_v2k1_verify",
                    "role": "adversarial verification of A0 counterexamples; "
                            "changes no controller and no search",
                    "checks": {"V1": "re-adjudicated by the canary's independent replay",
                               "V2": "identical verdict at K=1,2,4,8",
                               "V3": "magnitude interval inward from the shell — a "
                                     "shell-only escape is a weaker object and is "
                                     "labelled as such",
                               "V4": "hit probability of the legacy uniform-in-volume "
                                     "bank, the quantitative form of 'D1 missed it'"},
                    "distinctness": "A0's top-48 pool collapses to ONE distinct attack "
                                    "per cell; distinct hashes are reported, not pool size"},
           "all_verified": ok,
           "n_distinct_new_counterexamples": len(ind),
           "cells_with_new_counterexample": sorted({r["witness"] + " / " + r["arm"]
                                                    for r in ind}),
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
