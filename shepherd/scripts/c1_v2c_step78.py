"""C-1 — execution steps 7 and 8: frozen falsifier on the sealed artifacts, then report.

STEP 7   the SEALED falsifier v2, confirmatory (`V2C-`) seeds, run only on
         (condition, trajectory, arm) triples whose artifact was gate-valid and was
         hashed in step 6 BEFORE any attacker search touched it.

STEP 8   the hierarchy the review fixed:
             external condition -> defender trajectory -> controller arm
         IN_DISTRIBUTION and STRESS reported apart, never pooled.

PERMITTED LABELS -- and nothing else
    CONFIRMATORY_ESCAPE_FOUND
    NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2
    POST_FIRE_LANE_GATE_FAILURE
    POST_FIRE_FULL_GATE_CERTIFICATE

NOT ISSUED
    MISSION_SUCCESS · CAPTURE_SUCCESS · PENETRATION_PREVENTED · END_TO_END_ROBUST

"M of N" is written only alongside the condition layer.  The pairs are not
independent samples: several defender trajectories share one external condition,
and every condition in this campaign shares one attacker boundary condition.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import PRIMARY, R_BODY, M_SAFETY
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions
from shepherd.scripts.c1_phase1d import rollout_unified
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_heldout_conditions import (condition_list, spawn_for,
                                                    finisher_for, controller_for)
from shepherd.scripts.c1_falsifier_v2_seal import build as seal_build
from shepherd.scripts.c1_v2c_rediscovery import run_cell_confirmatory, CONFIRMATORY_PREFIX

PERMITTED = ["CONFIRMATORY_ESCAPE_FOUND", "NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2",
             "POST_FIRE_LANE_GATE_FAILURE", "POST_FIRE_FULL_GATE_CERTIFICATE"]
NOT_ISSUED = ["MISSION_SUCCESS", "CAPTURE_SUCCESS", "PENETRATION_PREVENTED",
              "END_TO_END_ROBUST"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", default="results/c1_corridor/c1_v2c_artifacts.json")
    ap.add_argument("--seal", default="results/c1_corridor/c1_falsifier_v2_seal.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_step78.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    W = {w[1]: w for w in witnesses()}
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    cmap = {c["condition_id"]: c for c in condition_list()}

    old = json.loads(pathlib.Path(a.seal).read_text()); now = seal_build()
    drift = [f for f in now["files"] if old["files"].get(f) != now["files"][f]]
    art = json.loads(pathlib.Path(a.artifacts).read_text())
    print("== execution steps 7 + 8 — frozen falsifier on SEALED artifacts ==")
    print("   seal: file_mismatch_count = %d  SEAL_INTACT = %s" % (len(drift), not drift))
    if drift:
        print("   REFUSING: falsifier seal drifted."); return 2

    jobs = [(r, arm) for r in art["rows"] if "error" not in r
            for arm in ("RI-SHARED-v1", "RI-GMAX") if r["arms"][arm]["gate_valid"]]
    print("   %d gate-valid (condition, trajectory, arm) triples\n" % len(jobs))

    rows = []
    for i, (r, arm) in enumerate(jobs):
        cid, tag = r["condition_id"], r["witness"]
        c = cmap[cid]; kind, _t, rho0, tl, spec_w = W[tag]
        dl = r["arms"][arm]["delta_m"]
        try:
            rec = rollout_unified(pe, spawn_for(rho0, tl, c),
                                  controller_for(kind, rho0, spec_w), finisher_for(c),
                                  r_lane=RL, r_body=RB, seed=int(c["reset_seed"]))
            t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
            pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
            P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
            kw = E._vshot_kwargs(pa, va, o[36:45])
            cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net",
                                       "range_min", "range_max")}
            P, Vv, _A, _b, _r = dynamic_inward(P0, Vp0, dl)
            L = lambda ts: hermite_positions(P, Vv, np.asarray(ts))[0]
            st = run_cell_confirmatory(E, pa, va, L, cone, float(E.tau_deploy),
                                       "%s|%s" % (cid, tag))
            esc = [s for s in st if s["is_escape"]]
            rows.append({"condition_id": cid, "set": r["set"], "witness": tag, "arm": arm,
                         "delta_m": dl, "artifact_hash": r["arms"][arm]["artifact_hash"],
                         "verdict": ("CONFIRMATORY_ESCAPE_FOUND" if esc
                                     else "NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2"),
                         "best_S_proxy_m": min(s["best_S_proxy_m"] for s in st),
                         "first_escape_stage": (esc[0]["stage"] if esc else None),
                         "escape_hashes": [s["attack_policy_hash"] for s in esc]})
        except Exception as ex:
            rows.append({"condition_id": cid, "set": r["set"], "witness": tag, "arm": arm,
                         "delta_m": dl, "verdict": "UNRESOLVED_OR_ABORT",
                         "error": "%s: %s" % (type(ex).__name__, ex)})
        if (i + 1) % 25 == 0:
            print("   %3d / %d" % (i + 1, len(jobs)), flush=True)

    # ---- step 8 ----------------------------------------------------------------
    print("\n== step 8 — condition -> trajectory -> arm, IN_DISTRIBUTION and STRESS apart ==")
    arm_set = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for r in rows:
        arm_set[r["set"]][r["arm"]][r["verdict"]] += 1
    for s in sorted(arm_set):
        print("\n   [%s]" % s)
        for arm in ("RI-SHARED-v1", "RI-GMAX"):
            c = arm_set[s][arm]
            n = sum(c.values())
            print("      %-14s triples %3d   escape %3d   no-escape %3d   abort %d"
                  % (arm, n, c["CONFIRMATORY_ESCAPE_FOUND"],
                     c["NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2"],
                     c["UNRESOLVED_OR_ABORT"]))
        cond = collections.defaultdict(list)
        for r in rows:
            if r["set"] == s:
                cond[r["condition_id"]].append(r)
        n_any = sum(1 for k in cond
                    if any(x["verdict"] == "CONFIRMATORY_ESCAPE_FOUND" for x in cond[k]))
        print("      conditions with >=1 escape: %d / %d  (conditions are the unit; "
              "trajectories within one condition are not independent)"
              % (n_any, len(cond)))

    gate_fail = art["status_counts"]
    print("\n   step 5/6 outcomes carried forward (not skips)")
    for arm in ("RI-SHARED-v1", "RI-GMAX"):
        for k, v in sorted(gate_fail.get(arm, {}).items()):
            if k != "GATE_VALID":
                print("      %-14s %-52s %d" % (arm, k, v))

    esc = [r for r in rows if r["verdict"] == "CONFIRMATORY_ESCAPE_FOUND"]
    S = np.asarray([r["best_S_proxy_m"] for r in rows if "error" not in r], float)
    print("\n   CONFIRMATORY_ESCAPE_FOUND  %d / %d triples" % (len(esc), len(rows)))
    print("   best S over triples: min %+.6f  median %+.6f  max %+.6f"
          % (S.min(), float(np.median(S)), S.max()))
    print("\n   CAMPAIGN STATUS: CLOSED — CERTIFICATE-LEVEL ONLY")
    print("   labels issued: %s" % PERMITTED)
    print("   NOT issued   : %s" % NOT_ISSUED)

    out = {"meta": {"script": "c1_v2c_step78", "execution_steps": [7, 8],
                    "seed_prefix": CONFIRMATORY_PREFIX, "seal_intact": not drift,
                    "artifacts_sealed_before_search": True,
                    "permitted_labels": PERMITTED, "not_issued": NOT_ISSUED,
                    "campaign_status": "CLOSED_CERTIFICATE_LEVEL_ONLY",
                    "counting_rule": "'M of N' only alongside the condition layer; "
                                     "trajectories within a condition are not "
                                     "independent, and every condition shares one "
                                     "attacker boundary condition",
                    "scope": "certificate-level. No mission-outcome claim: the eligible "
                             "branch is truncated at the deploy window"},
           "n_triples": len(rows), "n_escape": len(esc),
           "by_set_arm": {s: {a: dict(arm_set[s][a]) for a in arm_set[s]}
                          for s in arm_set},
           "step56_status_counts": gate_fail, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
