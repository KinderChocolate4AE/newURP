"""C-1 — execution step 3: the 11 unresolved cells under the frozen falsifier, fresh seeds.

The eleven cells that no search has yet falsified, re-run with the SEALED falsifier
v2 and CONFIRMATORY (`V2C-`) seeds -- streams disjoint from every development run.

Step 2 (blind rediscovery, 5/5 at A0) is the precondition: a falsifier that could
not re-find a known counterexample could not support a null here either.  It
passed, so a null in this module is readable as a diagnostic.  It is still not a
safety claim and still not external generality -- these eleven sit under the same
single attacker boundary condition as everything else in this campaign.

Permitted outputs, and nothing beyond them:

    CONFIRMATORY_ESCAPE_FOUND
    NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_falsifier_v2_seal import build as seal_build
from shepherd.scripts.c1_v2c_rediscovery import run_cell_confirmatory, CONFIRMATORY_PREFIX


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", default="results/c1_corridor/c1_falsifier_v2_freeze.json")
    ap.add_argument("--seal", default="results/c1_corridor/c1_falsifier_v2_seal.json")
    ap.add_argument("--redis", default="results/c1_corridor/c1_v2c_rediscovery.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_step3.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()

    old = json.loads(pathlib.Path(a.seal).read_text()); now = seal_build()
    drift = [f for f in now["files"] if old["files"].get(f) != now["files"][f]]
    rd = json.loads(pathlib.Path(a.redis).read_text())
    print("== execution step 3 — the 11 unresolved cells, frozen falsifier, %s seeds =="
          % CONFIRMATORY_PREFIX)
    print("   seal: file_mismatch_count = %d  SEAL_INTACT = %s" % (len(drift), not drift))
    print("   step 2 precondition: %s (%d/%d)"
          % (rd["verdict"], rd["n_rediscovered"], rd["n_cells"]))
    if drift or rd["verdict"] != "V2_DETECTION_REGRESSION_PASS":
        print("\n   REFUSING TO RUN: precondition not met."); return 2

    fz = json.loads(pathlib.Path(a.freeze).read_text())
    unres = fz["unresolved_cells"]
    d0 = json.loads(pathlib.Path("results/c1_corridor/c1_phase1p_d0.json").read_text())
    delta = {(r["witness"], r["arm"]): r["selected_delta_m"] for r in d0["rows"]}
    print("\n   %-22s %-10s %8s %11s %s"
          % ("scenario", "arm", "delta", "best S", "verdict"))

    rows = []
    for c in unres:
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
        esc = [s for s in st if s["is_escape"]]
        v = ("CONFIRMATORY_ESCAPE_FOUND" if esc
             else "NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2")
        best = min(s["best_S_proxy_m"] for s in st)
        rows.append({"witness": tag, "arm": arm, "delta_m": dl, "verdict": v,
                     "best_S_proxy_m": best,
                     "first_escape_stage": (esc[0]["stage"] if esc else None),
                     "escapes": [{"stage": s["stage"], "hash": s["attack_policy_hash"],
                                  "S_auth_m": s["authoritative"]["S_auth_m"],
                                  "acc": s["acc"]} for s in esc],
                     "stages": st})
        print("   %-22s %-10s %8.3f %11.6f %s"
              % (tag, arm, dl, best, v), flush=True)

    n_esc = sum(1 for r in rows if r["verdict"] == "CONFIRMATORY_ESCAPE_FOUND")
    gaps = np.asarray([r["best_S_proxy_m"] for r in rows], float)
    print("\n   CONFIRMATORY_ESCAPE_FOUND                 %d / %d" % (n_esc, len(rows)))
    print("   NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2 %d / %d" % (len(rows) - n_esc,
                                                                    len(rows)))
    print("   best S over the 11 cells: min %+.6f  median %+.6f  max %+.6f"
          % (gaps.min(), float(np.median(gaps)), gaps.max()))
    print("\n   SCOPE: single attacker boundary condition, single cone geometry, "
          "fixed reset 1100.\n          Certificate-level only. No mission claim.")

    out = {"meta": {"script": "c1_v2c_step3", "execution_step": 3,
                    "seed_prefix": CONFIRMATORY_PREFIX, "seal_intact": not drift,
                    "precondition": rd["verdict"],
                    "permitted_labels": ["CONFIRMATORY_ESCAPE_FOUND",
                                         "NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2"],
                    "scope": "single attacker boundary condition and cone geometry, "
                             "fixed reset 1100; certificate-level only",
                    "not_claimed": ["MISSION_SUCCESS", "CAPTURE_SUCCESS",
                                    "PENETRATION_PREVENTED", "END_TO_END_ROBUST"]},
           "n_cells": len(rows), "n_escape_found": n_esc, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
