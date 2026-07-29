"""C-1 Phase 1P step 4 — artifact-level intervention.

WHAT MAY BE CLAIMED HERE
------------------------
Exactly one thing per (artifact, intervention) pair:

    this intervention blocked this artifact.

Not "this intervention closes the mode", not "this degree of freedom is
sufficient", and above all not the intersection constraint -- the review retracted
that and it stays retracted until step 5's constrained replan measures mode
substitution.  An artifact that is blocked here may simply be replaced by a
neighbouring one when the attacker is allowed to re-optimise.

REPRESENTATIVES
---------------
The step-3.5 interval-certified set (74 artifacts).  Those are the artifacts that
currently carry claims, and each is CERTIFIED_COLLISION_FREE under the nominal
defender, so a post-intervention flip cannot be blamed on the baseline being
numerically shaky.

BLOCKING PREDICATE
------------------
An escape needs both terms positive, so

    blocked  <=>  NOT ( continuous_kill_margin > 0  AND  cone_exit_margin > 0 )

and the term that flipped is recorded, because "blocked via the kill term" and
"blocked via the cone term" are different facts and step 5 needs them apart.
The kill margin is recomputed with the CONTINUOUS adjudicator (`exact_min_clearance`),
not the 24-substep sample, since step 3.5 measured 23% of argmins to be interior.

THE INTERVENTIONS
-----------------
Each modifies the DEFENDER only; the attacker's K=4 acceleration plan is frozen
byte-for-byte.  Magnitudes are reported so that "minimal" is a measured property
rather than an adjective.

  NONE              identity.  MUST block 0 artifacts -- the harness sanity check.
  RING_FREEZE       limiters held at their fire-instant positions (velocities zeroed).
  RADIAL_HOLD       each limiter's radius frozen at its fire value; azimuth and z
                    evolve as recorded.
  TANGENTIAL_EQUAL  limiters redistributed to equal azimuthal spacing at the fire
                    instant, radius and z kept, then evolved by the recorded deltas.
  CONE_STEER_NOM    net axis rotated toward the attacker's ZERO-ACCELERATION
                    predicted endpoint.  Implementable: the defender can compute it
                    from the state it already observes.
  CONE_STEER_ORACLE net axis rotated toward THIS artifact's actual endpoint.  An
                    upper bound, not a policy -- it is told the answer.  Reported
                    separately and never counted as an implementable result.
  FIRE_SHIFT_PLUS1  deploy one step (dt) later: attacker state, limiter trajectory
                    and cone all taken at t_ref+1, same acceleration plan.
  FIRE_SHIFT_MINUS1 deploy one step earlier.
  AXIAL_TIGHTEN     range band narrowed by 10%.  NEGATIVE CONTROL: step 2 found
                    CONE_AXIAL unoccupied in 43,777 artifacts, so this should block
                    almost nothing.  If it blocks a lot, the harness is wrong.

SCOPE LIMIT, STATED UP FRONT
----------------------------
This step does NOT check whether the intervened defender still satisfies its own
capture certificate (E_cap / E_lane).  Freezing a ring or re-steering a net may
break the defender's own admissibility, and a "blocked" result obtained by an
inadmissible defender is worthless.  Admissibility is a step-6 gate; here it is an
explicit unknown, carried in the output as `defender_admissibility: NOT_CHECKED`.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIV_BASE_SEEDS
from shepherd.scripts.c1_phase1p_modes import _artifacts, classify, MODES, cone_components
from shepherd.scripts.c1_phase1p_stratified import select
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

INTERVENTIONS = ("NONE", "RING_FREEZE", "RADIAL_HOLD", "TANGENTIAL_EQUAL",
                 "CONE_STEER_NOM", "CONE_STEER_COVERAGE", "CONE_STEER_ORACLE",
                 "RING_FREEZE_PLUS_COVERAGE",
                 "FIRE_SHIFT_PLUS1", "FIRE_SHIFT_MINUS1", "AXIAL_TIGHTEN")
ORACLE = ("CONE_STEER_ORACLE",)          # never counted as implementable
CONTROL = ("NONE", "AXIAL_TIGHTEN")      # harness checks, not proposals
VACUOUS = ("CONE_STEER_NOM",)            # measured to be a no-op; see the module note
STEER_CAP_DEG = 10.0                     # cone steering is capped, not unlimited
AXIAL_TIGHTEN_FRAC = 0.10
N_COVERAGE = 4000                        # reachable-set sample for CONE_STEER_COVERAGE

# lane admissibility (frozen invariants), see c1_phase1d.rollout_unified
R_LANE, R_BODY_M, M_SAFETY_M = 2.1, 0.2, 0.2
LANE_MIN_M = R_LANE + R_BODY_M + M_SAFETY_M          # 2.50 m


def lane_clearance(P, cone, tau, dt=DT):
    """min over the deploy window of (perp distance to the net axis) - 2.50 m.
    >= 0 is E_lane.  Only limiters axially inside the net's reach are charged, which
    mirrors the judge's own `0 <= ax <= axial_len` gate."""
    apex = np.asarray(cone["net_apex"], float)
    u = np.asarray(cone["n_F"], float); u = u / (np.linalg.norm(u) + 1e-12)
    axial_len = float(cone["range_max"]) if cone["range_max"] is not None else np.inf
    n_dep = int(round(tau / dt))
    m = np.inf; seen = False
    for t in range(0, min(n_dep + 1, len(P))):
        r = np.asarray(P[t], float) - apex[None, :]
        ax = r @ u
        perp = np.linalg.norm(r - ax[:, None] * u[None, :], axis=1)
        sel = (ax >= 0.0) & (ax <= axial_len)
        if sel.any():
            m = min(m, float((perp[sel] - LANE_MIN_M).min())); seen = True
    return (float(m) if seen else None)


def ring_frame(P0):
    """Centre and orthonormal in-plane axes of the limiter ring, derived FROM THE
    DATA rather than assumed.

    The first version of this hard-coded the (x, y) plane.  The ring actually lies
    in (y, z): at the fire instant the four limiters sit at x = 8.000 with a (y, z)
    radius of 2.650 and std 0.00000, while the (x, y) "radius" has std 0.704.
    Working in the wrong plane made RADIAL_HOLD and TANGENTIAL_EQUAL meaningless --
    the tell was a 14 m median displacement on a 2.65 m ring.  The frame is now
    recovered by SVD so the same code is correct for any ring orientation.
    """
    c = P0.mean(axis=0)
    Q = P0 - c
    _u, _s, Vt = np.linalg.svd(Q, full_matrices=False)
    return c, Vt[0], Vt[1]


def _cyl(P0):
    """(radius, azimuth, out-of-plane offset) in the ring's own frame."""
    c, e1, e2 = ring_frame(P0)
    Q = P0 - c
    a, b = Q @ e1, Q @ e2
    n = np.cross(e1, e2)
    return np.hypot(a, b), np.arctan2(b, a), Q @ n


def _rotate_toward(n, target_dir, cap_rad):
    n = n / (np.linalg.norm(n) + 1e-12)
    t = np.asarray(target_dir, float)
    t = t / (np.linalg.norm(t) + 1e-12)
    c = float(np.clip(n @ t, -1.0, 1.0))
    ang = float(np.arccos(c))
    if ang < 1e-12:
        return n.copy(), 0.0
    use = min(ang, cap_rad)
    axis = np.cross(n, t)
    na = np.linalg.norm(axis)
    if na < 1e-12:
        return n.copy(), 0.0
    axis = axis / na
    s, cc = np.sin(use), np.cos(use)                       # Rodrigues
    out = n * cc + np.cross(axis, n) * s + axis * (axis @ n) * (1 - cc)
    return out / (np.linalg.norm(out) + 1e-12), float(np.degrees(use))


def apply_intervention(name, ctx, acc):
    """Return (L_of_t, cone_kw, p_att, v_att, magnitude_dict) after intervention."""
    P, Vp = ctx["P"].copy(), ctx["Vp"].copy()
    cone = dict(ctx["cone"])
    p_att, v_att = ctx["p_att"].copy(), ctx["v_att"].copy()
    mag = {}

    if name == "NONE":
        pass
    elif name == "RING_FREEZE":
        P = np.repeat(P[:1], len(P), axis=0); Vp = np.zeros_like(Vp)
        mag["max_limiter_displacement_from_nominal_m"] = float(
            np.linalg.norm(P - ctx["P"], axis=2).max())
    elif name == "RADIAL_HOLD":
        c0, e1, e2 = ring_frame(ctx["P"][0])
        r0, _, _ = _cyl(ctx["P"][0])
        nrm = np.cross(e1, e2)
        for k in range(len(P)):
            Q = P[k] - c0
            a, b, z = Q @ e1, Q @ e2, Q @ nrm
            rk = np.hypot(a, b) + 1e-12
            sc = r0 / rk
            P[k] = c0 + (a * sc)[:, None] * e1 + (b * sc)[:, None] * e2 + z[:, None] * nrm
        Vp = np.gradient(P, DT, axis=0) if len(P) > 2 else Vp
        mag["max_limiter_displacement_from_nominal_m"] = float(
            np.linalg.norm(P - ctx["P"], axis=2).max())
    elif name == "TANGENTIAL_EQUAL":
        # Equal azimuthal spacing at MINIMUM total rotation.  The first version of
        # this pinned the equalized grid to the first sorted limiter's angle, which
        # teleported limiters up to 16 m (median azimuth shift 236 deg) -- not an
        # intervention, a reconfiguration, and its 0/74 was uninformative.  The
        # offset is now chosen to minimise sum of squared angular displacement, in
        # sorted order (which is already the non-crossing matching).
        c0, e1, e2 = ring_frame(ctx["P"][0])
        nrm = np.cross(e1, e2)
        r0, phi0, z0 = _cyl(ctx["P"][0])
        n = len(phi0)
        order = np.argsort(phi0)
        step = 2 * np.pi / n
        base_pos = np.arange(n) * step
        resid = phi0[order] - base_pos                       # minimum-rotation offset
        off = float(np.angle(np.exp(1j * resid).mean()))
        tgt = np.empty_like(phi0)
        tgt[order] = base_pos + off
        dphi = np.angle(np.exp(1j * (tgt - phi0)))           # wrap to (-pi, pi]
        for k in range(len(P)):
            Q = P[k] - c0
            a, b, z = Q @ e1, Q @ e2, Q @ nrm
            rk = np.hypot(a, b); pk = np.arctan2(b, a) + dphi
            P[k] = (c0 + (rk * np.cos(pk))[:, None] * e1
                    + (rk * np.sin(pk))[:, None] * e2 + z[:, None] * nrm)
        Vp = np.gradient(P, DT, axis=0) if len(P) > 2 else Vp
        mag["max_azimuth_shift_deg"] = float(np.degrees(np.abs(dphi)).max())
        mag["max_limiter_displacement_from_nominal_m"] = float(
            np.linalg.norm(P - ctx["P"], axis=2).max())
    elif name == "RING_FREEZE_PLUS_COVERAGE":
        # The two interventions that cross modes, applied TOGETHER.  Applying each
        # alone and unioning the blocked sets is a different (and weaker) statement,
        # so the combination is evaluated as one defender rather than inferred.
        P = np.repeat(P[:1], len(P), axis=0); Vp = np.zeros_like(Vp)
        mag["max_limiter_displacement_from_nominal_m"] = float(
            np.linalg.norm(P - ctx["P"], axis=2).max())
        tau = ctx["tau"]
        L_tmp = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
        acc_bank = V.reachable_accels(ctx["E"].a_att_max, N_COVERAGE, 11)
        ep_b, _tfb, _ptb = V._seg_paths_turn(
            p_att, v_att, np.repeat(acc_bank[:, None, :], 4, axis=1), tau=tau,
            attacker_turn_limited=False, omega_att_max=None, e_att=None, n_t=24)
        out = cone_exit_margin(ep_b, **cone) > 0
        tgt_pt = ep_b[out].mean(axis=0) if out.any() else p_att + v_att * tau
        n_new, used = _rotate_toward(np.asarray(cone["n_F"], float),
                                     tgt_pt - np.asarray(cone["net_apex"], float),
                                     np.radians(STEER_CAP_DEG))
        cone["n_F"] = n_new
        mag["steer_deg"] = used; mag["n_uncovered_reachable"] = int(out.sum())
    elif name in ("CONE_STEER_NOM", "CONE_STEER_COVERAGE", "CONE_STEER_ORACLE"):
        tau = ctx["tau"]
        if name == "CONE_STEER_NOM":
            tgt_pt = p_att + v_att * tau                    # zero-accel prediction
        elif name == "CONE_STEER_COVERAGE":
            # Implementable and NOT a no-op: aim at the centroid of the reachable
            # endpoints that the cone currently FAILS to cover.  The defender can
            # compute this -- it already builds the reachable set for v_soft, and it
            # knows its own limiter trajectory.  No knowledge of the attacker's
            # actual plan is used.
            acc_bank = V.reachable_accels(ctx["E"].a_att_max, N_COVERAGE, 11)
            ep_b, _tfb, _ptb = V._seg_paths_turn(
                p_att, v_att, np.repeat(acc_bank[:, None, :], 4, axis=1), tau=tau,
                attacker_turn_limited=False, omega_att_max=None, e_att=None, n_t=24)
            out = cone_exit_margin(ep_b, **cone) > 0        # currently uncovered
            tgt_pt = ep_b[out].mean(axis=0) if out.any() else p_att + v_att * tau
            mag["n_uncovered_reachable"] = int(out.sum())
        else:
            ep, _tf, _pt = V._seg_paths_turn(p_att, v_att, acc[None], tau=tau,
                                             attacker_turn_limited=False,
                                             omega_att_max=None, e_att=None, n_t=24)
            tgt_pt = ep[0]
        n_new, used = _rotate_toward(np.asarray(cone["n_F"], float),
                                     tgt_pt - np.asarray(cone["net_apex"], float),
                                     np.radians(STEER_CAP_DEG))
        cone["n_F"] = n_new
        mag["steer_deg"] = used; mag["steer_cap_deg"] = STEER_CAP_DEG
    elif name in ("FIRE_SHIFT_PLUS1", "FIRE_SHIFT_MINUS1"):
        s = 1 if name.endswith("PLUS1") else -1
        t2 = ctx["t_ref"] + s
        if t2 < 0 or t2 >= len(ctx["obs_all"]) or t2 >= len(ctx["lim_all"]):
            return None
        o2 = np.asarray(ctx["obs_all"][t2], float)
        p_att = o2[ATT_P0:ATT_P0 + 3]; v_att = o2[ATT_P0 + 3:ATT_P0 + 6]
        P = np.asarray(ctx["lim_all"][t2:], float)
        Vp = np.asarray(ctx["vel_all"][t2:], float)
        kw = ctx["E"]._vshot_kwargs(p_att, v_att, o2[36:45])
        cone = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        mag["fire_shift_steps"] = s; mag["fire_shift_s"] = s * DT
    elif name == "AXIAL_TIGHTEN":
        lo, hi = float(cone["range_min"]), float(cone["range_max"])
        w = hi - lo
        cone["range_min"] = lo + AXIAL_TIGHTEN_FRAC * w / 2
        cone["range_max"] = hi - AXIAL_TIGHTEN_FRAC * w / 2
        mag["band_narrowed_m"] = float(AXIAL_TIGHTEN_FRAC * w)
    else:
        raise ValueError(name)

    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    return L, cone, p_att, v_att, mag, P


def evaluate(ctx, acc, L, cone, p_att, v_att, E):
    tau = ctx["tau"]
    ep, tf, _pt = V._seg_paths_turn(p_att, v_att, acc[None], tau=tau,
                                    attacker_turn_limited=False, omega_att_max=None,
                                    e_att=None, n_t=24)
    r = exact_min_clearance(p_att, v_att, acc, tau, L, N_LIM, DT, E.kill_radius)
    km = float(r["exact_margin_m"])
    lat, axi, _ax, _rn, _ang = cone_components(ep, **cone)
    cm = float(max(lat[0], axi[0]))
    escape = bool(km > 0 and cm > 0 and bool(tf[0]))
    if escape:
        flip = None
    elif km <= 0 and cm <= 0:
        flip = "BOTH"
    elif km <= 0:
        flip = "KILL_TERM"
    elif cm <= 0:
        flip = "CONE_TERM"
    else:
        flip = "TURN_INFEASIBLE"
    return {"kill_margin_m": km, "cone_exit_margin_m": cm,
            "lateral_m": float(lat[0]), "axial_m": float(axi[0]),
            "still_escape": escape, "blocked": not escape, "blocked_via": flip,
            "clearance_verdict": r["verdict"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_intervention.json")
    ap.add_argument("--audit", default="results/c1_corridor/c1_phase1p_verifier_audit.json")
    a = ap.parse_args()
    pe, E, fin = _env(); ws = witnesses(); t0 = time.time()
    certified = json.loads(pathlib.Path(a.audit).read_text())["A3_certificates"]
    want = {(c["witness"], c["attack_policy_hash"]) for c in certified
            if c["certificate"] == "CERTIFIED_COLLISION_FREE"}
    print("== step 4 — artifact-level intervention ==")
    print("   representatives: %d interval-certified artifacts" % len(want))
    print("   claim permitted: 'this intervention blocked this artifact' -- nothing more\n")

    rows = []
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        d = _artifacts(pe, E, rec, tag, DIV_BASE_SEEDS)
        if d is None:
            continue
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        kw = E._vshot_kwargs(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6], o[36:45])
        ctx = {"P": np.asarray(rec["_lim"][t:], float),
               "Vp": np.asarray(rec["_vel"][t:], float),
               "cone": {k: kw[k] for k in ("net_apex", "n_F", "theta_net",
                                           "range_min", "range_max")},
               "p_att": o[ATT_P0:ATT_P0 + 3], "v_att": o[ATT_P0 + 3:ATT_P0 + 6],
               "tau": float(E.tau_deploy), "t_ref": t, "E": E,
               "obs_all": rec["_obs"], "lim_all": rec["_lim"], "vel_all": rec["_vel"]}
        A, km, cm, lat, axi = d["A"], d["km"], d["cm"], d["lat"], d["axi"]
        lab = classify(km, cm, lat, axi)
        for i in range(len(A)):
            h = G.attack_policy_hash(A[i])
            if (tag, h) not in want:
                continue
            res = {}
            for name in INTERVENTIONS:
                got = apply_intervention(name, ctx, A[i])
                if got is None:
                    res[name] = {"status": "NOT_APPLICABLE"}
                    continue
                L, cone, pa, va, mag, Pnew = got
                ev = evaluate(ctx, A[i], L, cone, pa, va, E)
                ev["magnitude"] = mag
                lc = lane_clearance(Pnew, cone, ctx["tau"])
                ev["lane_clearance_m"] = lc
                ev["defender_E_lane"] = (None if lc is None else bool(lc >= 0.0))
                res[name] = ev
            rows.append({"witness": tag, "mode": str(lab[i]),
                         "attack_policy_hash": h,
                         "nominal_kill_margin_m": float(km[i]),
                         "nominal_cone_exit_margin_m": float(cm[i]),
                         "interventions": res})
            want.discard((tag, h))

    if rows and rows[0]["interventions"]["NONE"]["blocked"]:
        print("   !! sanity check FAILED: identity intervention blocked an artifact")

    agg = {}
    for name in INTERVENTIONS:
        ok = [r for r in rows if r["interventions"][name].get("status") != "NOT_APPLICABLE"]
        nb = sum(1 for r in ok if r["interventions"][name]["blocked"])
        adm = [r for r in ok if r["interventions"][name].get("defender_E_lane") is not False]
        nb_adm = sum(1 for r in adm if r["interventions"][name]["blocked"])
        n_inadm = len(ok) - len(adm)
        via = {}
        for r in ok:
            v = r["interventions"][name].get("blocked_via")
            if v:
                via[v] = via.get(v, 0) + 1
        per_mode = {}
        for m in ("KILL", "CONE_LATERAL"):
            sub = [r for r in ok if r["mode"] == m]
            per_mode[m] = {"n": len(sub),
                           "blocked": sum(1 for r in sub if r["interventions"][name]["blocked"])}
        agg[name] = {"n_applicable": len(ok), "n_blocked": nb,
                     "n_E_lane_violating": n_inadm,
                     "n_blocked_admissible_only": nb_adm,
                     "blocked_via": via, "per_mode": per_mode,
                     "kind": ("ORACLE_UPPER_BOUND" if name in ORACLE else
                              "HARNESS_CONTROL" if name in CONTROL else "IMPLEMENTABLE")}

    print("   %-19s %-19s %7s  %7s  %3s  %-11s %s"
          % ("intervention", "kind", "blocked", "adm-only", "!lane", "K / L", "via"))
    for name in INTERVENTIONS:
        g = agg[name]
        pm = g["per_mode"]
        print("   %-19s %-19s %3d/%-3d  %3d/%-3d  %3d  %2d/%-2d %2d/%-2d  %s"
              % (name, g["kind"], g["n_blocked"], g["n_applicable"],
                 g["n_blocked_admissible_only"], g["n_applicable"] - g["n_E_lane_violating"],
                 g["n_E_lane_violating"],
                 pm["KILL"]["blocked"], pm["KILL"]["n"],
                 pm["CONE_LATERAL"]["blocked"], pm["CONE_LATERAL"]["n"],
                 g["blocked_via"] if g["blocked_via"] else ""))

    impl = {k: v for k, v in agg.items() if v["kind"] == "IMPLEMENTABLE"}
    best = (max(impl.items(), key=lambda kv: kv[1]["n_blocked_admissible_only"])
            if impl else None)
    note = ("no implementable intervention blocked anything" if not best or not best[1]["n_blocked_admissible_only"]
            else "most-blocking implementable intervention, E_lane-admissible cases only: "
                 "%s (%d/%d) -- this says it blocked THOSE artifacts, not that it closes the mode"
                 % (best[0], best[1]["n_blocked_admissible_only"],
                    best[1]["n_applicable"] - best[1]["n_E_lane_violating"]))
    print("\n   %s" % note)
    if agg["NONE"]["n_blocked"] == 0:
        print("   sanity: identity blocked 0/%d as required" % agg["NONE"]["n_applicable"])
    if agg["AXIAL_TIGHTEN"]["n_blocked"] > 0.2 * max(agg["AXIAL_TIGHTEN"]["n_applicable"], 1):
        print("   !! negative control AXIAL_TIGHTEN blocked a lot -- check the harness")

    out = {"meta": {"script": "c1_phase1p_intervention", "step": 4,
                    "claim_permitted": "this intervention blocked this artifact",
                    "claim_forbidden": ["this intervention closes the mode",
                                        "this degree of freedom is sufficient",
                                        "the intersection constraint"],
                    "representatives": "step-3.5 interval-certified set",
                    "blocking_predicate": "NOT(continuous_kill_margin>0 AND cone_exit_margin>0)",
                    "kill_margin_source": "exact_min_clearance (continuous), not the 24-substep sample",
                    "defender_admissibility": "E_lane IS checked per intervention (lane_clearance >= 0, "
                                              "min 2.50 m over the deploy window). E_cap is NOT re-checked: "
                                              "it depends on the finisher chain, not on geometry alone. "
                                              "A block obtained by an E_lane-violating defender is reported "
                                              "as INADMISSIBLE and must not be counted.",
                    "steer_cap_deg": STEER_CAP_DEG,
                    "axial_tighten_frac": AXIAL_TIGHTEN_FRAC,
                    "protocol": G.PROTOCOL_VERSION},
           "n_representatives": len(rows), "aggregate": agg, "note": note, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
