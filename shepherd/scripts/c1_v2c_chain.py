"""C-1 — the engagement chain, stage by stage, so the bottleneck is locatable.

WHY
---
"397 no-fire, 167 certificates, 0 captures" are three numbers from three different
places.  Put end to end they say something the separate numbers do not: where in
the chain the system stops.

    condition-trajectory pair
      -> fire eligibility            does the frozen guard fire at all?
        -> E_capture                 was there an eligible firing instant?
          -> E_lane                  was the deploy lane clear?
            -> full-gate certificate E_cap and E_lane and no penetration
              -> clean capture       tier 5

The last arrow is the one that never fires in this grid, and that is exactly why
`E_safe` must not be read as success.

SCOPE, STATED UP FRONT
----------------------
The eight defender trajectories here are the witnesses of the UNRESOLVED cells of
an escape-centred campaign.  `clean capture = 0` is therefore a property of THIS
sealed grid and its witness selection, not an operational capture rate and not a
statement about the system's capture ability in general.  What it does establish,
independently of selection, is that a full-gate certificate does not imply a
capture -- there are 167 certificates and 0 captures in the same data.

Nothing here changes any seal, controller, guard or predicate.
"""
from __future__ import annotations
import argparse, collections, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import PRIMARY, R_BODY, M_SAFETY
from shepherd.scripts.c1_phase1d import rollout_unified
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses
from shepherd.scripts.c1_heldout_conditions import (condition_list, spawn_for,
                                                    finisher_for, controller_for)

STAGES = ["PAIRS", "FIRE_ELIGIBLE", "E_CAPTURE", "E_LANE",
          "FULL_GATE_CERTIFICATE", "CLEAN_CAPTURE"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", default="results/c1_corridor/c1_v2c_endpoints.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_chain.json")
    a = ap.parse_args()
    pe, _E, _fin = _env(); t0 = time.time()
    W = {w[1]: w for w in witnesses()}
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    ep = json.loads(pathlib.Path(a.endpoints).read_text())
    cmap = {c["condition_id"]: c for c in condition_list()}

    targets = [(r["condition_id"], r["set"], tag)
               for r in ep["conditions"]
               for tag, v in r["per_trajectory"].items() if v["eligible"]]
    total_pairs = ep["endpoint_A"]["total_pairs"]
    print("== the engagement chain ==")
    print("   re-running the %d ELIGIBLE pairs only; no-fire pairs already accounted\n"
          % len(targets))

    rows = []
    for i, (cid, sset, tag) in enumerate(targets):
        c = cmap[cid]; kind, _t, rho0, tl, spec_w = W[tag]
        try:
            rec = rollout_unified(pe, spawn_for(rho0, tl, c),
                                  controller_for(kind, rho0, spec_w), finisher_for(c),
                                  r_lane=RL, r_body=RB, seed=int(c["reset_seed"]))
            rows.append({"condition_id": cid, "set": sset, "witness": tag,
                         "tier": rec.get("tier"),
                         "E_capture": bool(rec.get("E_capture")),
                         "E_lane": bool(rec.get("E_lane")),
                         "penetrated": bool(rec.get("penetrated")),
                         "full_gate_certificate": bool(rec.get("safe")),
                         "clean_capture": bool(rec.get("tier") == 5),
                         "capture_margin": rec.get("capture_margin"),
                         "clearance_margin": rec.get("clearance_margin"),
                         "max_v_soft": rec.get("max_v_soft"),
                         "terminal_radial_err": rec.get("terminal_radial_err")})
        except Exception as ex:
            rows.append({"condition_id": cid, "set": sset, "witness": tag,
                         "error": "%s: %s" % (type(ex).__name__, ex)})
        if (i + 1) % 50 == 0:
            print("   %3d / %d" % (i + 1, len(targets)), flush=True)

    ok = [r for r in rows if "error" not in r]
    chain = {"PAIRS": total_pairs, "FIRE_ELIGIBLE": len(targets),
             "E_CAPTURE": sum(1 for r in ok if r["E_capture"]),
             "E_LANE": sum(1 for r in ok if r["E_capture"] and r["E_lane"]),
             "FULL_GATE_CERTIFICATE": sum(1 for r in ok if r["full_gate_certificate"]),
             "CLEAN_CAPTURE": sum(1 for r in ok if r["clean_capture"])}
    print("\n   stage                          n      conditional on previous")
    prev = None
    for s in STAGES:
        n = chain[s]
        cond = "" if prev is None else "%6.1f%%" % (100.0 * n / prev if prev else 0.0)
        print("   %-28s %5d   %s" % (s, n, cond))
        prev = n

    by_set = {}
    for st in sorted({r["set"] for r in ok}):
        sub = [r for r in ok if r["set"] == st]
        by_set[st] = {"eligible": len(sub),
                      "E_lane": sum(1 for r in sub if r["E_capture"] and r["E_lane"]),
                      "full_gate": sum(1 for r in sub if r["full_gate_certificate"]),
                      "clean_capture": sum(1 for r in sub if r["clean_capture"])}
        print("      %-16s eligible %3d  lane-clear %3d  certificate %3d  capture %d"
              % (st, by_set[st]["eligible"], by_set[st]["E_lane"],
                 by_set[st]["full_gate"], by_set[st]["clean_capture"]))

    cm = [r["capture_margin"] for r in ok
          if r["full_gate_certificate"] and r["capture_margin"] is not None]
    if cm:
        cm = np.asarray(cm, float)
        print("\n   capture_margin among the %d certificates: min %.4f  median %.4f  "
              "max %.4f" % (len(cm), cm.min(), float(np.median(cm)), cm.max()))
    print("\n   the certificate -> capture arrow never fires in this grid; that is the "
          "direct\n   evidence that a full-gate certificate does not imply a capture.")
    print("   SCOPE: witness selection is escape-centred; do NOT read 0 captures as an "
          "operational capture rate.")

    out = {"meta": {"script": "c1_v2c_chain",
                    "role": "locate the bottleneck along the engagement chain; "
                            "changes no seal, controller, guard or predicate",
                    "scope_caveat": "the eight defender trajectories are the witnesses "
                                    "of an escape-centred campaign's unresolved cells; "
                                    "clean capture = 0 is a property of THIS sealed grid "
                                    "and its witness selection, not an operational rate",
                    "what_is_selection_independent":
                        "167 full-gate certificates and 0 clean captures in the SAME "
                        "data — a certificate does not imply a capture",
                    "forbidden_implication":
                        "NO_ESCAPE_FOUND and FULL_GATE_CERTIFICATE => MISSION_SUCCESS",
                    "controller_status": "CAPTURE_OPPORTUNITY_SHAPING_CONTROLLER — the "
                                         "evidence supports shaping capture-capable "
                                         "geometry, not producing captures",
                    "next_version_outcome_to_add": "CAPTURE_OPPORTUNITY_WITHOUT_CAPTURE"},
           "chain": chain, "by_set": by_set, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
