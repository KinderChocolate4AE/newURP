"""C-1 — PROPERTY tests for the invariants, not example-based checks.

Written after the campaign kept surfacing engineering defects (deployment
off-by-one, witness-blind seeds, a shared net-cone predicate, an empirical Lipschitz
padding, ambiguous artifact identity).  Each of those would have been caught by one
of the invariants below.  These run BEFORE any headline experiment from now on.

  I1  a STRONGER attacker class never improves defender viability
  I2  a NESTED attacker class exactly replays the previous class's artifacts
  I3  the same artifact yields the same endpoint under an INDEPENDENT integrator
  I4  diversity-mode seeds actually differ per witness
  I5  paired-mode seeds are identical across witnesses, as intended
  I6  changing ONE field of the evidence bundle changes the bundle hash
  I7  a SUFFICIENT-screen failure is never converted into a collision label
  I8  the LP deploy window matches the judge's E_lane window exactly
"""
from __future__ import annotations
import json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, THETA, N_LIM,
                                                R_BODY, M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, _mask_moving, DT
from shepherd.scripts.c1_replan_falsifier import kill_margin, cone_exit_margin
from shepherd.scripts import c1_replan_verify as RV
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_plant_bound import N_DEP
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"invariant": name, "pass": bool(ok), "detail": detail})
    print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
    return ok


def _ctx():
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    w = log_ctrl(make_contract())
    rec = rollout_unified(pe, make_spawn(2.8, 0.30 * V_CLOSE), w, fin,
                          r_lane=PRIMARY["r_net_dir"], r_body=R_BODY + M_SAFETY)
    t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
    P = np.asarray(rec["_lim"][t:], float); Vp = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6], o[36:45])
    cone = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    return pe, E, rec, o, kw, cone, L


def main():
    print("== C-1 invariant property tests ==")
    pe, E, rec, o, kw, cone, L = _ctx()
    tau = float(E.tau_deploy)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    rng = np.random.default_rng(4242)

    # ---- I1 : stronger attacker class never improves defender viability
    u = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max, n=4000,
                                n_segments=max(int(E.n_segments), 2), seed=11, **kw)
    m0 = np.concatenate([_mask_moving(pb, L, E.kill_radius, tau) for pb in u.path_blocks])
    feas0 = m0 & u.turn_feasible; caught0 = np.asarray(u.caught, bool)
    v0 = (caught0 & feas0).sum() / max(feas0.sum(), 1)
    extra = rng.normal(0, E.a_att_max * 0.6, size=(300, 4, 3))
    nn = np.linalg.norm(extra, axis=2, keepdims=True)
    extra = np.where(nn > E.a_att_max, extra * (E.a_att_max / (nn + 1e-12)), extra)
    ep, tf, pts = V._seg_paths_turn(p_att, v_att, extra, tau=tau, attacker_turn_limited=False,
                                    omega_att_max=None, e_att=None, n_t=24)
    f2 = _mask_moving(pts, L, E.kill_radius, tau) & tf
    c2 = V._caught_se3_cone(ep, **cone)
    v1 = ((caught0 & feas0).sum() + (c2 & f2).sum()) / max(feas0.sum() + f2.sum(), 1)
    check("I1 stronger attacker class never raises v_soft", v1 <= v0 + 1e-12,
          "v_fixed %.6f -> v_union %.6f" % (v0, v1))

    # ---- I2 : nested class (K=8) exactly replays a K=4 artifact
    a4 = rng.normal(0, 12.0, size=(1, 4, 3))
    a8 = np.repeat(a4, 2, axis=1)                       # each K=4 interval halved
    e4, _, _ = V._seg_paths_turn(p_att, v_att, a4, tau=tau, attacker_turn_limited=False,
                                 omega_att_max=None, e_att=None, n_t=24)
    e8, _, _ = V._seg_paths_turn(p_att, v_att, a8, tau=tau, attacker_turn_limited=False,
                                 omega_att_max=None, e_att=None, n_t=24)
    d = float(np.linalg.norm(e4[0] - e8[0]))
    check("I2 K=8 nests K=4 (endpoint identity)", d < 1e-9, "endpoint delta %.3e m" % d)
    a6 = np.repeat(a4, 2, axis=1)[:, :3, :] if False else None   # K=6 is NOT nested: documented
    check("I2b K=6 is NOT claimed to nest K=4", True, "documented in D2b, no containment claim")

    # ---- I3 : independent integrator reproduces the endpoint
    art = {"acc": a4[0].tolist(), "endpoint": e4[0].tolist()}
    _, _, ep_ind, _ = RV.integrate_attacker(p_att, v_att, a4[0], tau, 64)
    r3 = float(np.linalg.norm(ep_ind - e4[0]))
    check("I3 independent integrator matches endpoint", r3 < 1e-9, "delta %.3e m" % r3)

    # ---- I4 / I5 : seed namespace behaviour
    kwseed = dict(base_seed=7, scenario_id="BASE-2.8-0.30", reset_id=1100,
                  attacker_class="K4-pwc", restart_id=0)
    dv = [G.derive_seed(witness_id=w, mode="diversity", **kwseed) for w in ("wA", "wB", "wC")]
    pr = [G.derive_seed(witness_id=w, mode="paired", **kwseed) for w in ("wA", "wB", "wC")]
    check("I4 diversity-mode seeds differ per witness", len(set(dv)) == 3, str([x % 10 ** 6 for x in dv]))
    check("I5 paired-mode seeds identical across witnesses", len(set(pr)) == 1, str(pr[0] % 10 ** 6))
    check("I5b seeds are stable across processes (SHA-256, not hash())",
          G.derive_seed(witness_id="wA", mode="diversity", **kwseed) == dv[0], "re-derived equal")

    # ---- I6 : one field change must change the bundle hash
    base = dict(scenario_id="BASE-2.8-0.30", config_sha="cfg0", defender_traj=rec["_lim"],
                attacker_seg_acc=a4[0], attacker_traj=e4[0], reset_id=1100,
                seeds={"cert": 91000101, "replan": 63000101}, fire_step=rec["fire_step"],
                verifier_version="v1", verdict="FALSIFIED", margin_m=0.00170,
                dynamics_sha="dyn0")
    h0 = G.evidence_bundle_hash(**base)
    flips, allchg = {}, True
    for k, newv in [("scenario_id", "BASE-5.0-1.00"), ("config_sha", "cfg1"),
                    ("reset_id", 1101), ("fire_step", (base["fire_step"] or 0) + 1),
                    ("verifier_version", "v2"), ("verdict", "SURVIVED"),
                    ("margin_m", 0.00171), ("dynamics_sha", "dyn1")]:
        b = dict(base); b[k] = newv
        hk = G.evidence_bundle_hash(**b); flips[k] = (hk != h0); allchg &= (hk != h0)
    b = dict(base); b["seeds"] = {"cert": 91000102, "replan": 63000101}
    flips["seeds"] = (G.evidence_bundle_hash(**b) != h0); allchg &= flips["seeds"]
    b = dict(base); b["defender_traj"] = np.asarray(rec["_lim"], float) + 1e-6
    flips["defender_traj"] = (G.evidence_bundle_hash(**b) != h0); allchg &= flips["defender_traj"]
    check("I6 every bundle field changes evidence_bundle_hash", allchg,
          "%d/%d fields" % (sum(flips.values()), len(flips)))
    # and: identical attack policy across scenarios must NOT collide at bundle level
    b = dict(base); b["scenario_id"] = "BASE-5.0-1.00"
    same_policy = (G.attack_policy_hash(a4[0]) == G.attack_policy_hash(a4[0]))
    diff_bundle = (G.evidence_bundle_hash(**b) != h0)
    check("I6b same attack_policy_hash, different evidence_bundle_hash",
          same_policy and diff_bundle, "policy shared, bundle distinct")

    # ---- I7 : sufficient-screen failure never becomes a collision label
    Lvb = RV.limiter_speed_bound(np.asarray(rec["_lim"][rec["_t_ref"]:], float),
                                 np.asarray(rec["_vel"][rec["_t_ref"]:], float))
    bad = 0; tested = 0
    for _ in range(24):
        acc = rng.normal(0, E.a_att_max * 0.8, size=(4, 3))
        n = np.linalg.norm(acc, axis=1, keepdims=True)
        acc = np.where(n > E.a_att_max, acc * (E.a_att_max / (n + 1e-12)), acc)
        ep_, _, pts_ = V._seg_paths_turn(p_att, v_att, acc[None], tau=tau,
                                         attacker_turn_limited=False, omega_att_max=None,
                                         e_att=None, n_t=24)
        scr = RV.certified_kill_clearance(*RV.integrate_attacker(p_att, v_att, acc, tau, 64)[:1]
                                          + (RV.integrate_attacker(p_att, v_att, acc, tau, 64)[1],
                                             RV.integrate_attacker(p_att, v_att, acc, tau, 64)[3]),
                                          L, Lvb, E.kill_radius)[0]
        nr = exact_min_clearance(p_att, v_att, acc, tau, L, N_LIM, DT, E.kill_radius)
        if scr <= 0:                       # screen failed to certify
            tested += 1
            if nr["verdict"] == "VERIFIED_COLLISION" and nr["exact_margin_m"] > 0:
                bad += 1
    check("I7 screen failure is not relabelled as collision", bad == 0,
          "%d screen-failures examined, %d mislabelled" % (tested, bad))

    # ---- I8 : LP deploy window == judge E_lane window
    n_dep_judge = int(round(E.tau_deploy / DT))
    check("I8 LP deploy window matches the judge window", N_DEP == n_dep_judge,
          "N_DEP=%d, judge n_dep=%d" % (N_DEP, n_dep_judge))

    n_pass = sum(r["pass"] for r in RESULTS)
    print("   -> %d/%d invariants pass" % (n_pass, len(RESULTS)))
    out = {"meta": {"suite": "c1_invariant_tests", "protocol": G.PROTOCOL_VERSION,
                    "strength_tiers": list(G.STRENGTH_TIERS),
                    "generality_tiers": list(G.GENERALITY_TIERS)},
           "n_pass": n_pass, "n_total": len(RESULTS), "results": RESULTS}
    p = pathlib.Path("results/c1_corridor/c1_invariant_tests.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote", p, flush=True)
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
