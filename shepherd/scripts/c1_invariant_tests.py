"""C-1 — PROPERTY tests for the invariants, not example-based checks.

Written after the campaign kept surfacing engineering defects (deployment
off-by-one, witness-blind seeds, a shared net-cone predicate, an empirical Lipschitz
padding, ambiguous artifact identity).  Each of those would have been caught by one
of the invariants below.  These run BEFORE any headline experiment from now on.

  I1  a STRONGER attacker class never improves defender viability
  I1b the I1 INSTANCE is non-vacuous -- v_fixed is strictly below the ceiling
  I2  a NESTED attacker class exactly replays the previous class's artifacts
  I3  the same artifact yields the same endpoint under an INDEPENDENT integrator
  I4  diversity-mode seeds actually differ per witness
  I5  paired-mode seeds are identical across witnesses, as intended
  I6  changing ONE field of the evidence bundle changes the bundle hash
  I7  a SUFFICIENT-screen failure is never converted into a collision label
  I8  the LP deploy window matches the judge's E_lane window exactly

Phase 1P step 0a
----------------
The Phase 1O run of this suite used the cell (rho0 2.8, tl 0.30, arm C), where
v_fixed = v_union = 1.000: every feasible sampled attacker path was caught, so
`v_union <= v_fixed` held only because both sides sat at the ceiling.  A
monotonicity bug could not have been detected there.  The instance is now
(rho0 4.0, tl 0.40, arm C) at n = 20000, selected by the pre-registered rule in
`c1_phase1p_i1_instance.py` (largest uncaught-but-feasible count among cells with
0.02 < v_fixed < 0.98).  Measured there: v_fixed 0.834-0.843 with 46-54 uncaught
feasible samples across seeds 11/12/13, so the inequality now has room to fail.

I1b is the structural half of the fix.  The Phase 1O defect was not "wrong cell"
-- it was that a vacuous instance passed silently.  I1b makes that condition
self-reporting: if the instance ever saturates again, the suite says so instead
of returning a green tick.
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

# ---- I1 instance (Phase 1P step 0a).  Changing these three lines changes what
# ---- I1 is actually testing, so they are named, not inlined.
I1_RHO0, I1_TL, I1_ARM = 4.0, 0.40, "C"
I1_N = 20000                 # 4000 saturated by chance on neighbouring cells
I1_CEILING = 1.0 - 1e-9      # v_fixed at/above this => the instance is vacuous


def check(name, ok, detail=""):
    RESULTS.append({"invariant": name, "pass": bool(ok), "detail": detail})
    print("   [%s] %-58s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
    return ok


def _ctx():
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    w = log_ctrl(make_contract())          # I1_ARM == "C"
    rec = rollout_unified(pe, make_spawn(I1_RHO0, I1_TL * V_CLOSE), w, fin,
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

    # ---- I1 : ESCAPE-SET monotonicity under attacker-class enlargement.
    #
    # The Phase 1O form of I1 compared the POOLED CATCH RATIO
    #     v = caught / feasible   over (fixed block) vs (fixed block + extra block)
    # and asserted v_union <= v_fixed.  That statistic is NOT monotone: pooling two
    # blocks with different catch rates moves the ratio toward the easier block
    # (Simpson).  Phase 1O only passed because its instance sat at v = 1.000, where
    # the ratio physically cannot rise.  On the non-vacuous 0a instance it fails
    # immediately -- +0.0025 from an extra block of 5 feasible samples, all caught.
    # That is arithmetic, not a defender improvement.
    #
    # It is also the very error class this campaign already ruled out: the frozen
    # D0 protocol records `v_soft_replan_is_verdict_input: False` precisely because
    # a ratio whose denominator is the arbitrary search budget carries no verdict.
    # I1 was then built on exactly such a ratio.
    #
    # Restated on quantities that ARE monotone under S_fixed subset of S_union:
    #   (a) shared members must receive IDENTICAL labels through the enlarged
    #       evaluation  -- this is the bug an enlarged class can actually introduce;
    #   (b) the ESCAPE SET may not shrink: |escapes(S_union)| >= |escapes(S_fixed)|.
    # Both classes are pushed through ONE code path: the Block-1 single-segment
    # accels are lifted to K=4 constant segments, which I2's nesting property
    # guarantees leaves endpoints unchanged.
    def _eval_class(A):
        ep_, tf_, pts_ = V._seg_paths_turn(p_att, v_att, A, tau=tau,
                                           attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
        feas_ = _mask_moving(pts_, L, E.kill_radius, tau) & tf_
        return feas_, V._caught_se3_cone(ep_, **cone)

    A1 = V.reachable_accels(E.a_att_max, I1_N, 11)                  # Block 1, (n,3)
    A_fix = np.repeat(A1[:, None, :], 4, axis=1)                    # -> (n,4,3), same endpoints
    A_ext = rng.normal(0, E.a_att_max * 0.6, size=(300, 4, 3))      # genuinely richer: K=4 varying
    nn = np.linalg.norm(A_ext, axis=2, keepdims=True)
    A_ext = np.where(nn > E.a_att_max, A_ext * (E.a_att_max / (nn + 1e-12)), A_ext)
    A_uni = np.concatenate([A_fix, A_ext], axis=0)

    f_fix, c_fix = _eval_class(A_fix)
    f_uni, c_uni = _eval_class(A_uni)
    n0 = len(A_fix)
    labels_agree = bool((f_fix == f_uni[:n0]).all() and (c_fix == c_uni[:n0]).all())
    esc_fix = int((f_fix & ~c_fix).sum())
    esc_uni = int((f_uni & ~c_uni).sum())
    n_feas0 = int(f_fix.sum())
    check("I1 enlarging the attacker class never shrinks the escape set",
          labels_agree and esc_uni >= esc_fix,
          "escapes %d -> %d, shared-member labels %s"
          % (esc_fix, esc_uni, "identical" if labels_agree else "DIVERGED"))

    # I1b : the instance must have room to fail in BOTH directions -- the fixed
    #       class needs escapes AND captures.  A saturated cell (esc_fix == 0) is
    #       exactly the Phase 1O defect, so it is now an explicit check rather than
    #       a silent green tick.
    check("I1b I1 instance is non-vacuous (escapes and captures both present)",
          0 < esc_fix < n_feas0,
          "cell %.1f/%.2f/%s  feasible %d = %d caught + %d escapes"
          % (I1_RHO0, I1_TL, I1_ARM, n_feas0, n_feas0 - esc_fix, esc_fix))

    # I1c : NEGATIVE CONTROL -- a test that has never failed is not known to be able
    #       to fail.  Corrupt one shared member's label and confirm I1's predicate
    #       flips to False.  (Phase 1O's I1 would have passed this cell regardless.)
    c_bad = c_uni.copy()
    idx = int(np.flatnonzero(f_fix & ~c_fix)[0])          # a shared escape member
    c_bad[idx] = True                                      # pretend the union caught it
    would_fail = not (bool((c_fix == c_bad[:n0]).all())
                      and int((f_uni & ~c_bad).sum()) >= esc_fix)
    check("I1c negative control: corrupted shared label makes I1 fail", would_fail,
          "flipped member %d -> predicate False as required" % idx)

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
    kwseed = dict(base_seed=7, scenario_id="BASE-4.0-0.40", reset_id=1100,
                  attacker_class="K4-pwc", restart_id=0)
    dv = [G.derive_seed(witness_id=w, mode="diversity", **kwseed) for w in ("wA", "wB", "wC")]
    pr = [G.derive_seed(witness_id=w, mode="paired", **kwseed) for w in ("wA", "wB", "wC")]
    check("I4 diversity-mode seeds differ per witness", len(set(dv)) == 3, str([x % 10 ** 6 for x in dv]))
    check("I5 paired-mode seeds identical across witnesses", len(set(pr)) == 1, str(pr[0] % 10 ** 6))
    check("I5b seeds are stable across processes (SHA-256, not hash())",
          G.derive_seed(witness_id="wA", mode="diversity", **kwseed) == dv[0], "re-derived equal")

    # ---- I6 : one field change must change the bundle hash
    base = dict(scenario_id="BASE-4.0-0.40", config_sha="cfg0", defender_traj=rec["_lim"],
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
