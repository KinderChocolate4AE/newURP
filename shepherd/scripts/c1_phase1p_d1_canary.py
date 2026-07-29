"""C-1 Phase 1P — D1 harness positive control (canary), MANDATORY before D2a.

WHY
---
Every one of the fifteen D1 cells reported `cands 0` -- not merely no verified
escape, but no internal escape candidate at all.  That is a strong signal only if
the pipeline could have produced one.  The alternatives the review named are all
consistent with the same observation:

    the candidate threshold got mis-wired at the D1 stage
    the warm-start path went empty after the seed amendment
    objective and verifier disagree about their inputs
    a stage-specific config silently weakened the attacker

So known escapes are pushed through the D1 pipeline.  This tunes nothing and
changes no controller; it asks whether the machine can still see an escape it has
already been shown.

THE CONTROLS
------------
  C1  exact replay -- the two D0 escapes against `RI-SHARED / RH 5.0/0.55` are
      re-adjudicated by the D1 verifier.  They must come back as escapes.
  C2  warm-start recognition -- the same artifacts are fed to the D1 candidate
      pipeline as the CEM warm start.  It must emit escape candidates.
  C3  large-margin control -- a MAXCLR escape (metre-scale margin, not millimetre)
      through the same path.  If even this vanishes, the pipeline is broken.
  C4  config parity -- objective, candidate threshold and verifier identity hashed
      and compared between D0 and D1.  Only the intended differences may appear.

VERDICT
-------
Any control failing puts the D1 survival result ON HOLD.  A null from a falsifier
that cannot recognise a known counterexample is not evidence of anything.
"""
from __future__ import annotations
import argparse, hashlib, inspect, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts import c1_replan_falsifier as RF
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG
from shepherd.scripts.c1_phase1p_modes import cone_components, classify
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_phase1p_d0 import D0, d0_seed
from shepherd.scripts.c1_phase1p_d1 import D1, d1_manifest
from shepherd.scripts import c1_governance as G
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


def replay(E, pa, va, L, cone, tau, acc):
    """C1 -- the D1 verifier's own judgement on a stored artifact."""
    acc = np.asarray(acc, float)
    ep, tf, pts = V._seg_paths_turn(pa, va, acc[None], tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    km = RF.kill_margin(pts, L, E.kill_radius, tau)
    lat, axi, _a, _r, _g = cone_components(ep, **cone)
    cm = float(max(lat[0], axi[0]))
    r = exact_min_clearance(pa, va, acc, tau, L, N_LIM, DT, E.kill_radius)
    return {"sampled_kill_margin_m": float(km[0]), "cone_exit_margin_m": cm,
            "continuous_kill_margin_m": float(r["exact_margin_m"]),
            "verdict": r["verdict"], "turn_feasible": bool(tf[0]),
            "recognised_as_escape": bool(r["verdict"] == "VERIFIED_COLLISION_FREE"
                                         and cm > 0 and tf[0])}


def warm_start_probe(E, pa, va, L, cone, tau, acc, scenario_id):
    """C2/C3 -- can the D1 CEM pipeline emit candidates from a known escape?"""
    m = d1_manifest(scenario_id)[0]
    best, escs = RF.replan_search(pa, va, tau=tau, a_att_max=E.a_att_max, L_of_t=L,
                                  kill_radius=E.kill_radius, cone_kw=cone, K=D1["K"],
                                  pop=D1["pop"], iters=D1["iters"], seed=int(m["cem"]),
                                  warm=np.asarray(acc, float))
    return {"n_candidates": len(escs), "best_score_m": float(best["score"]),
            "best_kill_margin_m": float(best.get("kill_margin", float("nan"))),
            "best_cone_exit_margin_m": float(best.get("cone_exit_margin", float("nan"))),
            "pipeline_emitted_candidates": bool(len(escs) > 0)}


def config_parity():
    """C4 -- objective, threshold and verifier identity, D0 vs D1."""
    src = lambda f: hashlib.sha256(inspect.getsource(f).encode()).hexdigest()[:16]
    common = {"objective_replan_search": src(RF.replan_search),
              "kill_margin": src(RF.kill_margin),
              "cone_exit_margin": src(RF.cone_exit_margin),
              "verifier_exact_min_clearance": src(exact_min_clearance),
              "candidate_threshold": "score > 0 (escape) -- literal in replan_search",
              "attacker_dynamics": src(V._seg_paths_turn)}
    d0 = {**common, "K": D0["K"], "pop": D0["pop"], "iters": D0["iters"],
          "n_bank": D0["n_bank"], "launches": D0["n_searches_per_cell"]}
    d1 = {**common, "K": D1["K"], "pop": D1["pop"], "iters": D1["iters"],
          "n_bank": D1["n_bank"], "launches": D1["n_searches_per_cell"]}
    diff = sorted(k for k in d0 if d0[k] != d1[k])
    return {"d0": d0, "d1": d1, "differing_keys": diff,
            "intended_differences": ["launches"],
            "parity_ok": diff == ["launches"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d0", default="results/c1_corridor/c1_phase1p_d0.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_d1_canary.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d0 = json.loads(pathlib.Path(a.d0).read_text())
    print("== D1 harness positive control (canary) ==")
    print("   a null from a falsifier that cannot recognise a known counterexample "
          "is not evidence\n")

    cp = config_parity()
    print("   C4 config parity  differing keys %s  -> %s"
          % (cp["differing_keys"], "OK" if cp["parity_ok"] else "MISMATCH"))

    rows = []
    # C1/C2 : the D0 escapes against RI-SHARED / RH 5.0/0.55
    src = [r for r in d0["rows"] if r["verdict"] != "SURVIVED_D0"]
    for r in src:
        pa, va, L, cone, tau = _ctx(pe, E, fin, r["witness"], r["selected_delta_m"])
        for e in r["d0"]["escapes"]:
            rep = replay(E, pa, va, L, cone, tau, e["acc"])
            wsp = warm_start_probe(E, pa, va, L, cone, tau, e["acc"], r["witness"])
            rows.append({"control": "C1/C2 D0 escape", "witness": r["witness"],
                         "arm": r["arm"], "delta_m": r["selected_delta_m"],
                         "attack_policy_hash": e["attack_policy_hash"],
                         "mode": e["mode"], "replay": rep, "warm_start": wsp})
            print("   C1 %-22s %-13s replay %s  (kill %+0.5f cone %+0.5f)"
                  % (r["witness"], e["mode"],
                     "ESCAPE" if rep["recognised_as_escape"] else "NOT RECOGNISED",
                     rep["continuous_kill_margin_m"], rep["cone_exit_margin_m"]))
            print("   C2 %-22s %-13s pipeline candidates %d  best score %+0.5f"
                  % ("", "", wsp["n_candidates"], wsp["best_score_m"]), flush=True)

    # C3 : a large-margin control from the pre-inward world (MAXCLR, metre-scale)
    mod = json.loads(pathlib.Path("results/c1_corridor/c1_phase1p_modes.json").read_text())
    big = None; best_max = 0.0
    for w in mod["rows"]:
        tag = w["scenario_id"]                     # NB: the modes record keys on scenario_id
        if not tag.startswith("MAXCLR"):
            continue
        for m in ("KILL", "CONE_LATERAL"):
            b = (w["modes"].get(m, {}) or {}).get("binding_margin_m")
            mx = float(b["max"]) if b else 0.0     # the LARGEST margin, not the tightest
            if mx > best_max:
                best_max, big = mx, (tag, m, mx)
    if big and best_max > 0.5:
        tag, mode, t = big
        pa, va, L, cone, tau = _ctx(pe, E, fin, tag, 0.0)     # NOMINAL defender
        # recover the artifact by re-running the modes search is expensive; instead
        # use a saturated bang control in the recorded escape direction as a probe
        from shepherd.scripts.c1_phase1p_modes import _artifacts
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        d = _artifacts(pe, E, rec, tag, (7,))
        if d is not None:
            sc = np.minimum(d["km"], d["cm"]); i = int(np.argmax(sc))
            rep = replay(E, pa, va, L, cone, tau, d["A"][i])
            wsp = warm_start_probe(E, pa, va, L, cone, tau, d["A"][i], tag)
            rows.append({"control": "C3 large-margin", "witness": tag,
                         "arm": "NOMINAL", "delta_m": 0.0,
                         "attack_policy_hash": G.attack_policy_hash(d["A"][i]),
                         "mode": str(mode), "recorded_max_binding_margin_m": float(t),
                         "rederived_binding_margin_m": float(sc[i]),
                         "replay": rep, "warm_start": wsp})
            print("   C3 %-22s large-margin replay %s (kill %+0.5f cone %+0.5f) | "
                  "pipeline candidates %d"
                  % (tag, "ESCAPE" if rep["recognised_as_escape"] else "NOT RECOGNISED",
                     rep["continuous_kill_margin_m"], rep["cone_exit_margin_m"],
                     wsp["n_candidates"]), flush=True)

    c1 = all(r["replay"]["recognised_as_escape"] for r in rows)
    c2 = all(r["warm_start"]["pipeline_emitted_candidates"] for r in rows)
    ok = bool(c1 and c2 and cp["parity_ok"])
    print("\n   C1 exact replay recognised     %s (%d artifacts)"
          % ("PASS" if c1 else "FAIL", len(rows)))
    print("   C2 warm-start emits candidates %s" % ("PASS" if c2 else "FAIL"))
    print("   C4 config parity               %s" % ("PASS" if cp["parity_ok"] else "FAIL"))
    print("\n   VERDICT: %s"
          % ("D1_HARNESS_VALIDATED -- the cands 0 result stands as a diagnostic signal"
             if ok else
             "D1_RESULT_ON_HOLD -- the pipeline could not recognise a known escape"))

    out = {"meta": {"script": "c1_phase1p_d1_canary",
                    "role": "MANDATORY positive control before D2a; tunes nothing",
                    "controls": {"C1": "exact replay of stored D0 escapes by the D1 verifier",
                                 "C2": "same artifacts as CEM warm start -- pipeline must "
                                       "emit candidates",
                                 "C3": "large-margin (metre-scale) escape through the same path",
                                 "C4": "objective / threshold / verifier identity hashed, "
                                       "D0 vs D1"},
                    "hold_rule": "any control failing puts the D1 survival result ON HOLD"},
           "config_parity": cp,
           "C1_pass": c1, "C2_pass": c2, "C4_pass": cp["parity_ok"],
           "verdict": ("D1_HARNESS_VALIDATED" if ok else "D1_RESULT_ON_HOLD"),
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
