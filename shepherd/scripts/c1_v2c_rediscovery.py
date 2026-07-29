"""C-1 — execution step 2: BLIND rediscovery of the five known counterexamples.

WHAT THIS IS
------------
The frozen falsifier v2, run on the five cells that already have a verified
counterexample, with FRESH CONFIRMATORY SEEDS (`V2C-` stream) and with the known
counterexamples REMOVED from the seeding bank.  The question is only:

    can the frozen falsifier find them again without being told where they are?

WHAT THIS IS NOT
----------------
Evidence of external generality.  These five shaped v2's design, so re-finding
them is a REGRESSION test of detection power and nothing more.  A pass does not
transfer to the unresolved cells; a failure would invalidate the v2 nulls.

WHY THE STAGE LOOP IS RE-INSTANTIATED HERE
------------------------------------------
`c1_falsifier_v2.run_cell` hard-codes the development stream prefix `V2-`, and
that file is SEALED -- editing it to add a prefix argument would break the code
freeze for a bookkeeping reason.  So the search PRIMITIVES are imported from the
sealed module unchanged (`k1_search`, `refine`, `segment_descent`, `s_proxy`,
`s_auth`, `embed`, `temporal_starts`) together with the sealed budget constants,
and only the stage loop is re-expressed here with `stage_id="V2C-..."`.

The seal is verified at start-up, and the budget constants are read from the
sealed module rather than restated, so a drift in either shows up immediately.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_phase1p_d0 import d0_seed
from shepherd.scripts.c1_falsifier_v2 import (STAGES, TOP_M, GLOBAL_DIRS, MONO_TOL_M,
                                              s_proxy, s_auth, embed, temporal_starts,
                                              refine, segment_descent)
from shepherd.scripts.c1_phase1p_falsifier_v2_k1 import k1_search
from shepherd.scripts.c1_falsifier_v2_seal import build as seal_build
from shepherd.scripts import c1_governance as G

CONFIRMATORY_PREFIX = "V2C-"


def run_cell_confirmatory(E, pa, va, L, cone, tau, scenario_id):
    """A0..A3 with confirmatory seeds and an EMPTY known-escape bank."""
    bank, out, prev = [], [], np.inf
    for st in STAGES:
        K = st["K"]
        rng = np.random.default_rng(int(d0_seed(
            stage_id=CONFIRMATORY_PREFIX + st["id"], rng_role="refine",
            scenario_id=scenario_id, reset_id=DIAG["reset"],
            attacker_class="K%d-pwc" % K, restart_id=0, base_seed=7000)))
        if st["id"] == "A0":
            res = k1_search(E, pa, va, L, cone, tau)          # NO seed directions
            seeds = res["pool"][:, None, :]
            inc, best, best_a = refine(E, pa, va, L, cone, tau, seeds, K, rng)
        else:
            inherited = np.stack([embed(b, K) for b in bank
                                  if embed(b, K) is not None], axis=0)
            fresh = temporal_starts(K, float(E.a_att_max), GLOBAL_DIRS)
            inc_i, best_i, a_i = refine(E, pa, va, L, cone, tau, inherited, K, rng)
            inc_f, best_f, a_f = refine(E, pa, va, L, cone, tau, fresh, K,
                                        np.random.default_rng(int(d0_seed(
                                            stage_id=CONFIRMATORY_PREFIX + st["id"],
                                            rng_role="fresh", scenario_id=scenario_id,
                                            reset_id=DIAG["reset"],
                                            attacker_class="K%d-pwc" % K,
                                            restart_id=1, base_seed=7100))))
            if best_f < best_i:
                inc, best, best_a = inc_f, best_f, a_f
            else:
                inc, best, best_a = inc_i, best_i, a_i
        sd_a, sd_S = segment_descent(E, pa, va, L, cone, tau, best_a, K)
        if sd_S < best:
            best, best_a = sd_S, sd_a
            inc = np.concatenate([sd_a[None], inc[:TOP_M - 1]], axis=0)
        au = s_auth(E, pa, va, L, cone, tau, best_a)
        out.append({"stage": st["id"], "K": K, "best_S_proxy_m": best,
                    "authoritative": au, "is_escape": au["is_escape"],
                    "attack_policy_hash": G.attack_policy_hash(best_a),
                    "acc": np.asarray(best_a, float).tolist(),
                    "monotone_vs_previous": bool(best <= prev + MONO_TOL_M)})
        bank = bank + [inc[i] for i in range(min(TOP_M, len(inc)))]
        prev = min(prev, best)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", default="results/c1_corridor/c1_falsifier_v2_freeze.json")
    ap.add_argument("--seal", default="results/c1_corridor/c1_falsifier_v2_seal.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_rediscovery.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()

    old = json.loads(pathlib.Path(a.seal).read_text()); now = seal_build()
    drift = [f for f in now["files"] if old["files"].get(f) != now["files"][f]]
    print("== execution step 2 — BLIND rediscovery of the 5 known counterexamples ==")
    print("   seal check: file_mismatch_count = %d  SEAL_INTACT = %s"
          % (len(drift), not drift))
    if drift:
        print("   REFUSING: the falsifier seal has drifted %s" % drift); return 2
    print("   confirmatory stream prefix %s   known counterexamples NOT seeded"
          % CONFIRMATORY_PREFIX)
    print("   this is a DETECTION-POWER REGRESSION TEST, not external-generality "
          "evidence\n")

    fz = json.loads(pathlib.Path(a.freeze).read_text())
    cells = fz["falsified_cells"]
    d0 = json.loads(pathlib.Path("results/c1_corridor/c1_phase1p_d0.json").read_text())
    delta = {(r["witness"], r["arm"]): r["selected_delta_m"] for r in d0["rows"]}

    print("   %-22s %-10s %8s %11s %6s %s"
          % ("scenario", "arm", "delta", "best S", "esc", "first stage"))
    rows = []
    for c in cells:
        tag, arm = c["witness"], c["arm"]
        dl = delta[(tag, arm)]
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        P, Vv, _A, _b, _r = dynamic_inward(P0, Vp0, dl)
        L = lambda ts: hermite_positions(P, Vv, np.asarray(ts))[0]

        st = run_cell_confirmatory(E, pa, va, L, cone, tau, tag)
        esc = [s["stage"] for s in st if s["is_escape"]]
        rows.append({"witness": tag, "arm": arm, "delta_m": dl,
                     "originally_found_at": c["found_at"],
                     "rediscovered": bool(esc), "first_stage": (esc[0] if esc else None),
                     "best_S_proxy_m": min(s["best_S_proxy_m"] for s in st),
                     "stages": st})
        print("   %-22s %-10s %8.3f %11.6f %6s %s"
              % (tag, arm, dl, rows[-1]["best_S_proxy_m"],
                 "YES" if esc else "NO", esc[0] if esc else "-"), flush=True)

    n = sum(1 for r in rows if r["rediscovered"])
    print("\n   rediscovered %d / %d" % (n, len(rows)))
    verdict = ("V2_DETECTION_REGRESSION_PASS" if n == len(rows)
               else "V2_DETECTION_REGRESSION_FAIL")
    print("   VERDICT: %s" % verdict)
    if n < len(rows):
        print("   a falsifier that cannot re-find a counterexample it was built around "
              "cannot support ANY null; the v2 nulls go ON HOLD.")
    else:
        print("   NOTE: this licenses reading v2 nulls as diagnostics. It does NOT "
              "transfer to the\n         unresolved cells and is NOT external-generality "
              "evidence.")

    out = {"meta": {"script": "c1_v2c_rediscovery", "execution_step": 2,
                    "role": "detection-power REGRESSION test on the five cells that "
                            "shaped v2; not generality evidence",
                    "confirmatory_prefix": CONFIRMATORY_PREFIX,
                    "known_counterexamples_seeded": False,
                    "seal_checked": True, "seal_intact": not drift,
                    "why_stage_loop_reinstantiated":
                        "c1_falsifier_v2.run_cell hard-codes the V2- development "
                        "prefix and that file is sealed; the search primitives and "
                        "budget constants are imported unchanged and only the stage "
                        "loop is re-expressed with V2C- seeds"},
           "n_cells": len(rows), "n_rediscovered": n, "verdict": verdict, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if n == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
