"""C-1 — execution steps 5 and 6: build and SEAL the held-out controller artifacts.

STEP 5 -- RI-SHARED-v1, applied UNCHANGED
    the frozen shared rule, re-evaluated on each held-out condition:
        d_raw    = clip(lane_clearance(delta=0) - LANE_RESERVE, 0, DELTA_MAX)
        d_shared = max{ delta in RESERVE_VALID : delta <= d_raw }
    Nothing about the rule, the reserve, the grid or the PD gains is re-tuned.
    If it yields no reserve-valid delta the cell is an OUTCOME, not a skip:
        SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE

STEP 6 -- RI-GMAX, re-synthesised per condition, GATE ONLY
        d_gmax = max{ delta in RESERVE_VALID }
    RESERVE_VALID uses ONLY defender dynamics, admissibility, E_cap, E_lane and the
    pre-registered lane reserve.  No falsifier score, no escape outcome, no
    adversarial margin, no A0-A3 result enters the choice.  If none exists:
        NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS

SEALING ORDER
    Both artifacts are hashed and written HERE, before step 7 runs any attacker
    search on them.  That is what stops the synthesis from drifting toward
    "whatever survives falsification".

This module runs NO falsifier and issues NO survival label.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import PRIMARY, R_BODY, M_SAFETY
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1d import rollout_unified
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses
from shepherd.scripts.c1_phase1p_6a_dynamic import (DELTA_GRID, DELTA_MAX, LANE_RESERVE_M,
                                                    dynamic_inward, admissibility, gate,
                                                    _ring_basis)
from shepherd.scripts.c1_heldout_conditions import (condition_list, spawn_for,
                                                    finisher_for, controller_for)

STEP = float(DELTA_GRID[1] - DELTA_GRID[0])


def synthesise(pe, E, th, pa, va, pointing, P0, Vp0, cone, tau):
    """The frozen gate-only sweep.  Returns both arms' deltas and the sweep."""
    c0, e1, e2, _n = _ring_basis(P0[0])
    sweep = []
    for dl in DELTA_GRID:
        P, Vv, Aa, _b, _r = dynamic_inward(P0, Vp0, float(dl))
        adm = admissibility(P, Vv, Aa, P0, Vp0, c0, e1, e2)
        lc, v_r, p_r, e_cap = gate(pe, E, th, pa, va, pointing, P, Vv, cone, tau)
        rv = bool(adm["DEFENDER_TRAJECTORY_ADMISSIBLE"] and lc is not None
                  and lc >= LANE_RESERVE_M and e_cap != "FAIL")
        sweep.append({"delta_m": float(dl), "lane_clearance_m": lc, "v_soft": v_r,
                      "E_cap": e_cap, "RESERVE_VALID": rv,
                      "admissible": bool(adm["DEFENDER_TRAJECTORY_ADMISSIBLE"])})
    valid = [s["delta_m"] for s in sweep if s["RESERVE_VALID"]]
    lc0 = sweep[0]["lane_clearance_m"] or 0.0
    d_gmax = (float(max(valid)) if valid else None)
    d_raw = float(np.clip(lc0 - LANE_RESERVE_M, 0.0, DELTA_MAX))
    cand = [d for d in valid if d <= d_raw]
    d_shared = (float(max(cand)) if cand else None)
    return {"sweep": sweep, "n_reserve_valid": len(valid),
            "lane_clearance_at_zero_m": lc0, "d_raw_m": d_raw,
            "RI-GMAX": d_gmax, "RI-SHARED-v1": d_shared}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoints", default="results/c1_corridor/c1_v2c_endpoints.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_v2c_artifacts.json")
    a = ap.parse_args()
    pe, E, fin = _env(); th = pe.theta; t0 = time.time()
    W = {w[1]: w for w in witnesses()}
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    ep = json.loads(pathlib.Path(a.endpoints).read_text())
    cmap = {c["condition_id"]: c for c in condition_list()}

    targets = [(r["condition_id"], r["set"], tag)
               for r in ep["conditions"]
               for tag, v in r["per_trajectory"].items() if v["eligible"]]
    print("== execution steps 5 + 6 — build and SEAL held-out controller artifacts ==")
    print("   %d eligible (condition, trajectory) pairs; gate-only synthesis, "
          "NO falsifier here" % len(targets))
    print("   grid %.3f m | lane reserve %.3f m | delta_max %.3f\n"
          % (STEP, LANE_RESERVE_M, DELTA_MAX))

    rows = []
    for i, (cid, sset, tag) in enumerate(targets):
        c = cmap[cid]; kind, _t, rho0, tl, spec_w = W[tag]
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
            syn = synthesise(pe, E, th, pa, va, o[36:45], P0, Vp0, cone,
                             float(E.tau_deploy))
            arms = {}
            for arm, key, fail in (("RI-SHARED-v1", "RI-SHARED-v1",
                                    "SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE"),
                                   ("RI-GMAX", "RI-GMAX",
                                    "NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS")):
                dl = syn[key]
                if dl is None:
                    arms[arm] = {"delta_m": None, "status": fail,
                                 "gate_valid": False}
                    continue
                s = next(x for x in syn["sweep"] if abs(x["delta_m"] - dl) < 1e-12)
                arms[arm] = {"delta_m": dl, "status": "GATE_VALID", "gate_valid": True,
                             "lane_clearance_m": s["lane_clearance_m"],
                             "lane_reserve_excess_m": (None if s["lane_clearance_m"] is None
                                                       else s["lane_clearance_m"]
                                                       - LANE_RESERVE_M),
                             "v_soft": s["v_soft"], "E_cap": s["E_cap"],
                             "artifact_hash": hashlib.sha256(json.dumps(
                                 {"condition": cid, "witness": tag, "arm": arm,
                                  "delta_m": dl}, sort_keys=True).encode()
                             ).hexdigest()[:16]}
            rows.append({"condition_id": cid, "set": sset, "witness": tag,
                         "n_reserve_valid_deltas": syn["n_reserve_valid"],
                         "lane_clearance_at_zero_m": syn["lane_clearance_at_zero_m"],
                         "d_raw_m": syn["d_raw_m"], "arms": arms})
        except Exception as ex:
            rows.append({"condition_id": cid, "set": sset, "witness": tag,
                         "error": "%s: %s" % (type(ex).__name__, ex)})
        if (i + 1) % 40 == 0:
            print("   %3d / %d" % (i + 1, len(targets)), flush=True)

    ok = [r for r in rows if "error" not in r]
    st = collections.defaultdict(collections.Counter)
    for r in ok:
        for arm, v in r["arms"].items():
            st[arm][v["status"]] += 1
    print("\n   arm                     GATE_VALID   construction/gate failure")
    for arm in ("RI-SHARED-v1", "RI-GMAX"):
        c = st[arm]
        fail = sum(v for k, v in c.items() if k != "GATE_VALID")
        print("   %-22s %10d   %d" % (arm, c["GATE_VALID"], fail))
    by_set = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for r in ok:
        for arm, v in r["arms"].items():
            by_set[r["set"]][arm][v["status"]] += 1
    for s in sorted(by_set):
        print("      %-16s %s" % (s, {a: dict(by_set[s][a]) for a in by_set[s]}))

    for arm in ("RI-SHARED-v1", "RI-GMAX"):
        d = [r["arms"][arm]["delta_m"] for r in ok if r["arms"][arm]["gate_valid"]]
        e = [r["arms"][arm]["lane_reserve_excess_m"] for r in ok
             if r["arms"][arm]["gate_valid"]
             and r["arms"][arm]["lane_reserve_excess_m"] is not None]
        if d:
            print("   %-22s delta  min %.3f median %.3f max %.3f | reserve excess "
                  "min %.4f median %.4f" % (arm, min(d), float(np.median(d)), max(d),
                                            min(e), float(np.median(e))))

    out = {"meta": {"script": "c1_v2c_step56", "execution_steps": [5, 6],
                    "runs_no_falsifier": True, "issues_no_survival_label": True,
                    "shared_rule": "d_raw = clip(lane_clearance(0) - reserve, 0, "
                                   "DELTA_MAX); d_shared = max{RESERVE_VALID <= d_raw}",
                    "gmax_rule": "d_gmax = max{RESERVE_VALID}",
                    "information_rule": "RESERVE_VALID uses only defender dynamics, "
                                        "admissibility, E_cap, E_lane and the "
                                        "pre-registered reserve; no falsifier "
                                        "information enters the choice",
                    "sealing_order": "artifacts hashed and written BEFORE step 7",
                    "failure_is_an_outcome": {
                        "RI-SHARED-v1": "SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE",
                        "RI-GMAX": "NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS"}},
           "n_pairs": len(rows), "status_counts": {a: dict(st[a]) for a in st},
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
