"""C-1 Phase 1P step 3.5 — verifier cleanup before any intervention work.

External review, 2026-07-25, ruled step 3 "수정승인" and required five things be
settled BEFORE step 4.  This module does those five and nothing else.  No new
escape search, no verdict.

A1  THE INVARIANT.  The continuous minimum is taken over a superset of the sampled
    times, so m_continuous <= m_sampled must hold, i.e. m_sampled - m_continuous >= 0.
    Step 3 reported 39 artifacts with a negative difference.  Three causes are
    possible: floating-point noise, the two judges evaluating DIFFERENT
    trajectories, or the continuous solver missing a candidate.  Magnitude alone
    cannot separate them -- a real missed root could hide behind small numbers -- so
    all three are tested rather than assumed:

      (a) cross-path identity: evaluate the distance at every sampled timestamp
          through BOTH code paths and report the max discrepancy.  Rules out cause 2.
      (b) forced candidates: re-run the continuous solver with every sampled
          timestamp injected into the candidate set of its sub-interval, evaluated
          with the ACTUAL position callables rather than the fitted polynomial.
          This makes m_continuous <= m_sampled hold STRUCTURALLY.  Any gap between
          the shipped and forced solvers is a missed candidate.  Rules out cause 3.
      (c) whatever survives (a) and (b) is cause 1, and is reported with its
          distribution against a pre-registered tolerance.

A2  MODE RE-ASSIGNMENT.  Step 2's labels were computed from the SAMPLED kill margin.
    After continuous adjudication the binding term must be recomputed:

        binding = argmin(continuous_kill_margin, cone_lateral, cone_axial)

    and when the two smallest are within a pre-registered tie band the artifact is
    labelled MIXED_OR_BINDING_AMBIGUOUS rather than forced into a mode.

A3  INTERVAL CERTIFICATION.  The tightest KILL artifact sits at 1.08e-5 m.  A
    companion-matrix root is not a bounded-error object, so that margin cannot carry
    a VERIFIED_COLLISION_FREE claim on its own.  The pre-registered certification
    set (union, deduplicated) is:
      - each witness-mode's tightest artifact           (the existence evidence)
      - every artifact with binding margin < 0.5 mm
      - every artifact with a negative sampled-continuous difference
      - every artifact within the mode-boundary band
    Certifying all 209 is unnecessary; certifying the artifacts that carry claims
    is not.

A4  ARGMIN LOCATION.  Step 3 said "the minimum lands on grid points" on the strength
    of sampled and exact agreeing to seven decimals.  That does not follow -- a flat
    interior minimum produces the same agreement.  The argmin TIME is recorded
    directly, with its distance to the nearest attacker segment boundary (tau/K) and
    limiter Hermite node (dt), and the interior fraction is reported.

A5  SAMPLING ACCOUNTING.  12 witnesses x 2 occupied modes x (6+6) = 288 nominal, 209
    actual.  The shortfall is tabled per witness-mode rather than left to inference.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, block_times, DT, N_T
from shepherd.scripts.c1_exact_clearance import (exact_min_clearance, _fit_cubic,
                                                 _poly_sq_sum, _W, TOL_NUMERIC)
from shepherd.scripts.c1_phase1n_hardening import rational_certificate
from shepherd.scripts.c1_phase1p_diversity import (_env, witnesses, rollout_for,
                                                   DIV_BASE_SEEDS, DIAG)
from shepherd.scripts.c1_phase1p_modes import (_artifacts, classify, MODES,
                                               UNCERTAINTY_BUDGET_M)
from shepherd.scripts.c1_phase1p_stratified import select, N_TIGHT, N_SPREAD
from shepherd.scripts import c1_governance as G

# ---- pre-registered constants (fixed before the audit was run) ----
CERTIFIED_TOLERANCE_M = 1e-12      # A1: anything worse is a verifier mismatch, not noise
TIE_BAND_M = 1e-9                  # A2: two binding terms this close -> AMBIGUOUS
BOUNDARY_BAND_M = 1e-6             # A3: "near the mode boundary" for certification
SMALL_MARGIN_M = 5e-4              # A3: 0.5 mm
GRID_NEAR_M = 1e-9                 # A4: argmin counted as "on" a node within this


def _attacker_of(p0, v0, seg_acc, tau):
    seg_acc = np.asarray(seg_acc, float); K = len(seg_acc); h = float(tau) / K
    p = np.asarray(p0, float).copy(); v = np.asarray(v0, float).copy()
    starts = [(p.copy(), v.copy())]
    for k in range(K):
        a = seg_acc[k]; p = p + v * h + 0.5 * a * h * h; v = v + a * h
        starts.append((p.copy(), v.copy()))

    def pa_of_t(ts):
        ts = np.atleast_1d(np.asarray(ts, float))
        out = np.empty((len(ts), 3))
        for j, tt in enumerate(ts):
            k = min(int(np.floor(tt / h + 1e-12)), K - 1)
            pk, vk = starts[k]; s = tt - k * h
            out[j] = pk + vk * s + 0.5 * seg_acc[k] * s * s
        return out
    return pa_of_t, h, K


def _breakpoints(tau, h, K, dt):
    bps = sorted(set(np.round(np.concatenate([
        np.arange(K + 1) * h,
        np.arange(0, int(np.floor(tau / dt)) + 2) * dt]), 12)))
    bps = [min(max(b, 0.0), tau) for b in bps if -1e-12 <= b <= tau + 1e-12]
    return bps


def exact_min_clearance_forced(p0, v0, seg_acc, tau, L_of_t, n_lim, dt, r_kill,
                               forced_ts):
    """As exact_min_clearance, but every time in `forced_ts` that lands inside a
    sub-interval is added as a candidate and evaluated with the ACTUAL callables.
    Also returns the argmin TIME, not just the sub-interval."""
    pa_of_t, h, K = _attacker_of(p0, v0, seg_acc, tau)
    bps = _breakpoints(tau, h, K, dt)
    forced = np.asarray(forced_ts, float)
    d_min, t_min, i_min, src = np.inf, None, None, None
    n_forced_used = 0
    for j in range(len(bps) - 1):
        T0, T1 = bps[j], bps[j + 1]
        if T1 - T0 < 1e-12:
            continue
        t4 = T0 + _W * (T1 - T0)
        Pa4 = np.asarray(pa_of_t(t4), float)
        Pl4 = np.asarray(L_of_t(t4), float)
        inside = forced[(forced >= T0 - 1e-15) & (forced <= T1 + 1e-15)]
        if len(inside):
            Pa_f = np.asarray(pa_of_t(inside), float)
            Pl_f = np.asarray(L_of_t(inside), float)
            n_forced_used += len(inside)
        for i in range(n_lim):
            C = _fit_cubic(Pa4 - Pl4[:, i, :])
            q = _poly_sq_sum(C); dq = np.polyder(q)
            cands = [0.0, 1.0]
            if np.any(np.abs(dq) > 0):
                for z in np.roots(dq):
                    if abs(z.imag) < 1e-9 and -1e-12 <= z.real <= 1.0 + 1e-12:
                        cands.append(float(np.clip(z.real, 0.0, 1.0)))
            for w in cands:                                  # polynomial candidates
                dv = float(np.sqrt(max(float(np.polyval(q, w)), 0.0)))
                if dv < d_min:
                    d_min, t_min, i_min, src = dv, T0 + w * (T1 - T0), i, "poly"
            if len(inside):                                  # forced sampled times
                dvs = np.linalg.norm(Pa_f - Pl_f[:, i, :], axis=1)
                a = int(np.argmin(dvs))
                if float(dvs[a]) < d_min:
                    d_min, t_min, i_min, src = (float(dvs[a]), float(inside[a]), i,
                                                "forced_sample")
    return {"d_min_m": float(d_min), "exact_margin_m": float(d_min - r_kill),
            "argmin_t": float(t_min), "argmin_limiter": int(i_min),
            "argmin_source": src, "n_forced_candidates": int(n_forced_used),
            "h_attacker": float(h), "dt_limiter": float(dt)}


def cross_path_check(p0, v0, seg_acc, tau, L_of_t, sampled_pts, sampled_ts, n_lim):
    """Same distances, two code paths.  `sampled_pts` came from
    viability._seg_paths_turn; here they are rebuilt from the continuous callable."""
    pa_of_t, _h, _K = _attacker_of(p0, v0, seg_acc, tau)
    Pa = np.asarray(pa_of_t(sampled_ts), float)
    dpos = float(np.abs(Pa - np.asarray(sampled_pts, float)).max())
    Pl = np.asarray(L_of_t(np.asarray(sampled_ts)), float)
    d_cont = np.linalg.norm(Pa[:, None, :] - Pl, axis=2)
    d_samp = np.linalg.norm(np.asarray(sampled_pts, float)[:, None, :] - Pl, axis=2)
    return {"max_abs_position_diff_m": dpos,
            "max_abs_distance_diff_m": float(np.abs(d_cont - d_samp).max()),
            "min_distance_via_continuous_path_m": float(d_cont.min()),
            "min_distance_via_sampled_path_m": float(d_samp.min())}


def audit(pe, E, fin, ws, do_cert=True):
    tau = float(E.tau_deploy)
    rows, acct, cert_rows = [], [], []
    for kind, tag, rho0, tl, spec in ws:
        rec = rollout_for(pe, fin, kind, rho0, tl, spec)
        d = _artifacts(pe, E, rec, tag, DIV_BASE_SEEDS)
        if d is None:
            continue
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
        P = np.asarray(rec["_lim"][t:], float); Vp = np.asarray(rec["_vel"][t:], float)
        L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]

        A, km, cm, lat, axi = d["A"], d["km"], d["cm"], d["lat"], d["axi"]
        lab = classify(km, cm, lat, axi); sc = np.minimum(km, cm)
        from shepherd.game import viability as V
        for m in MODES:
            s = np.flatnonzero(lab == m)
            n_pool = int(len(s))
            if not n_pool:
                acct.append({"witness": tag, "mode": m, "n_pool": 0, "nominal": 0,
                             "selected": 0, "reason": "mode not observed"})
                continue
            ti, si = select(sc[s])
            picks = [("tight", int(s[i])) for i in ti] + [("spread", int(s[i])) for i in si]
            acct.append({"witness": tag, "mode": m, "n_pool": n_pool,
                         "nominal": N_TIGHT + N_SPREAD, "selected": len(picks),
                         "n_tight": len(ti), "n_spread": len(si),
                         "reason": ("pool smaller than 6+6; select() caps at pool size"
                                    if len(picks) < N_TIGHT + N_SPREAD else "full")})
            for arm, idx in picks:
                acc = A[idx]
                _ep, _tf, pts1 = V._seg_paths_turn(p_att, v_att, acc[None], tau=tau,
                                                   attacker_turn_limited=False,
                                                   omega_att_max=None, e_att=None,
                                                   n_t=N_T)
                ts = block_times(pts1.shape[1], tau)
                xp = cross_path_check(p_att, v_att, acc, tau, L, pts1[0], ts, N_LIM)
                shipped = exact_min_clearance(p_att, v_att, acc, tau, L, N_LIM, DT,
                                              E.kill_radius)
                forced = exact_min_clearance_forced(p_att, v_att, acc, tau, L, N_LIM,
                                                    DT, E.kill_radius, ts)
                m_samp = float(km[idx])
                gap_shipped = m_samp - shipped["exact_margin_m"]
                gap_forced = m_samp - forced["exact_margin_m"]
                missed = shipped["exact_margin_m"] - forced["exact_margin_m"]
                # A2 : re-assign using the CONTINUOUS kill margin.
                #
                # The review wrote the rule as argmin(kill, lateral, axial).  Taken
                # literally that is wrong in this codebase's sign convention:
                # `axial` is the signed distance OUTSIDE the range band, so it is
                # large and NEGATIVE whenever the endpoint is inside the band --
                # which it always is here -- and a 3-way argmin would label every
                # artifact CONE_AXIAL.  The escape condition is
                #     min( kill , max(lateral, axial) ) > 0
                # so the mode-deciding comparison is kill vs cone := max(lat, axi),
                # and WITHIN cone it is lateral vs axial by which attains the max.
                # That is `c1_phase1p_modes.classify` with the sampled kill margin
                # swapped for the continuous one, which is the intended semantics.
                k_exact = float(forced["exact_margin_m"])
                lat_i, axi_i = float(lat[idx]), float(axi[idx])
                cone_i = max(lat_i, axi_i)
                terms = {"KILL_continuous": k_exact, "CONE_max(lat,axi)": cone_i,
                         "lateral": lat_i, "axial": axi_i}
                gap_mode = abs(k_exact - cone_i)
                if gap_mode <= TIE_BAND_M:
                    exact_mode = "MIXED_OR_BINDING_AMBIGUOUS"
                elif k_exact < cone_i:
                    exact_mode = "KILL"
                else:
                    exact_mode = ("MIXED_OR_BINDING_AMBIGUOUS"
                                  if abs(lat_i - axi_i) <= TIE_BAND_M
                                  else ("CONE_LATERAL" if lat_i >= axi_i else "CONE_AXIAL"))
                # A4 : argmin location
                at = forced["argmin_t"]
                d_seg = float(min(abs(at - k * forced["h_attacker"])
                                  for k in range(int(round(tau / forced["h_attacker"])) + 1)))
                d_nod = float(min(abs(at - k * DT)
                                  for k in range(int(round(tau / DT)) + 1)))
                rows.append({
                    "witness": tag, "arm": arm, "sampled_mode": m,
                    "exact_mode": exact_mode,
                    "attack_policy_hash": G.attack_policy_hash(acc),
                    "m_sampled_kill_m": m_samp,
                    "m_continuous_shipped_m": float(shipped["exact_margin_m"]),
                    "m_continuous_forced_m": float(forced["exact_margin_m"]),
                    "gap_shipped_m": float(gap_shipped),
                    "gap_forced_m": float(gap_forced),
                    "shipped_minus_forced_m": float(missed),
                    "invariant_ok": bool(gap_forced >= -CERTIFIED_TOLERANCE_M),
                    "cross_path": xp,
                    "binding_terms_m": terms,
                    "binding_gap_m": float(gap_mode),
                    "argmin_t_s": at, "argmin_source": forced["argmin_source"],
                    "argmin_dist_to_attacker_boundary_s": d_seg,
                    "argmin_dist_to_hermite_node_s": d_nod,
                    "argmin_is_interior": bool(min(d_seg, d_nod) > GRID_NEAR_M),
                    "_acc": acc.tolist(), "_witness_ctx": tag})
    return rows, acct


def pick_for_certification(rows):
    """Pre-registered union, deduplicated by (witness, policy hash)."""
    sel, why = {}, {}
    best = {}
    for r in rows:
        k = (r["witness"], r["sampled_mode"])
        if k not in best or r["m_continuous_forced_m"] < best[k]["m_continuous_forced_m"]:
            best[k] = r
    for r in best.values():
        key = (r["witness"], r["attack_policy_hash"])
        sel[key] = r; why.setdefault(key, []).append("witness-mode existence evidence")
    for r in rows:
        key = (r["witness"], r["attack_policy_hash"])
        tags = []
        if min(r["m_continuous_forced_m"], max(r["binding_terms_m"]["lateral"], r["binding_terms_m"]["axial"])) < SMALL_MARGIN_M:
            tags.append("binding margin < 0.5 mm")
        if r["gap_shipped_m"] < 0:
            tags.append("negative sampled-continuous difference")
        if r["binding_gap_m"] < BOUNDARY_BAND_M:
            tags.append("within mode-boundary band")
        if tags:
            sel[key] = r; why.setdefault(key, []).extend(tags)
    return [(sel[k], sorted(set(why[k]))) for k in sel]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_verifier_audit.json")
    ap.add_argument("--no-cert", action="store_true")
    a = ap.parse_args()
    pe, E, fin = _env(); ws = witnesses(); t0 = time.time()
    print("== Phase 1P step 3.5 — verifier audit ==")
    print("   pre-registered: tol %.0e m | tie band %.0e m | boundary %.0e m | small %.0e m\n"
          % (CERTIFIED_TOLERANCE_M, TIE_BAND_M, BOUNDARY_BAND_M, SMALL_MARGIN_M))

    rows, acct = audit(pe, E, fin, ws)

    # ---- A1
    gs = np.array([r["gap_shipped_m"] for r in rows])
    gf = np.array([r["gap_forced_m"] for r in rows])
    mf = np.array([r["shipped_minus_forced_m"] for r in rows])
    xp_pos = max(r["cross_path"]["max_abs_position_diff_m"] for r in rows)
    xp_dst = max(r["cross_path"]["max_abs_distance_diff_m"] for r in rows)
    viol = [r for r in rows if not r["invariant_ok"]]
    print("A1  invariant  m_sampled - m_continuous >= -%.0e" % CERTIFIED_TOLERANCE_M)
    print("    cross-path max |position diff|  %.3e m   (cause 2: different trajectory)" % xp_pos)
    print("    cross-path max |distance diff|  %.3e m" % xp_dst)
    print("    shipped solver negatives  %d / %d   worst %.3e m" % (int((gs < 0).sum()), len(gs), gs.min()))
    print("    forced  solver negatives  %d / %d   worst %.3e m" % (int((gf < 0).sum()), len(gf), gf.min()))
    print("    shipped - forced (missed candidates)  max %.3e m, nonzero %d"
          % (mf.max(), int((np.abs(mf) > CERTIFIED_TOLERANCE_M).sum())))
    print("    VIOLATIONS beyond tolerance: %d %s" % (len(viol), "" if not viol else "<-- MISMATCH"))

    # ---- A2
    changed = [r for r in rows if r["exact_mode"] != r["sampled_mode"]]
    amb = [r for r in rows if r["exact_mode"] == "MIXED_OR_BINDING_AMBIGUOUS"]
    from collections import Counter
    cnt = Counter(r["exact_mode"] for r in rows)
    print("\nA2  mode re-assignment on continuous margins (tie band %.0e m)" % TIE_BAND_M)
    print("    label changes %d / %d | ambiguous %d" % (len(changed), len(rows), len(amb)))
    for k, v in sorted(cnt.items()):
        print("      %-28s %3d" % (k, v))
    wocc = {}
    for r in rows:
        wocc.setdefault(r["exact_mode"], set()).add(r["witness"])
    for k in sorted(wocc):
        print("      %-28s witnesses %2d" % (k, len(wocc[k])))

    # ---- A4
    interior = [r for r in rows if r["argmin_is_interior"]]
    from_forced = [r for r in rows if r["argmin_source"] == "forced_sample"]
    dseg = np.array([r["argmin_dist_to_attacker_boundary_s"] for r in rows])
    dnod = np.array([r["argmin_dist_to_hermite_node_s"] for r in rows])
    print("\nA4  argmin-time location (n=%d)" % len(rows))
    print("    on a grid node (<= %.0e s)      %d / %d" % (GRID_NEAR_M, len(rows) - len(interior), len(rows)))
    print("    interior                        %d / %d  (%.1f%%)"
          % (len(interior), len(rows), 100.0 * len(interior) / len(rows)))
    print("    dist to attacker boundary  median %.4e s   max %.4e s" % (np.median(dseg), dseg.max()))
    print("    dist to Hermite node       median %.4e s   max %.4e s" % (np.median(dnod), dnod.max()))
    print("    argmin found at a forced sampled time: %d" % len(from_forced))

    # ---- A5
    nominal = sum(x["nominal"] for x in acct)
    selected = sum(x["selected"] for x in acct)
    short = [x for x in acct if x["selected"] < x["nominal"]]
    print("\nA5  stratified sampling accounting")
    print("    nominal %d  ->  selected %d   (shortfall %d across %d witness-modes)"
          % (nominal, selected, nominal - selected, len(short)))
    for x in short:
        print("      %-22s %-13s pool %5d -> %2d selected (%s)"
              % (x["witness"], x["mode"], x["n_pool"], x["selected"], x["reason"]))

    # ---- A3
    cert = []
    if not a.no_cert:
        picks = pick_for_certification(rows)
        print("\nA3  interval certification of the pre-registered set (%d artifacts)" % len(picks))
        by_tag = {tag: (kind, rho0, tl, spec) for kind, tag, rho0, tl, spec in ws}
        for r, whys in picks:
            kind, rho0, tl, spec = by_tag[r["witness"]]
            rec = rollout_for(pe, fin, kind, rho0, tl, spec)
            t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
            p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
            P = np.asarray(rec["_lim"][t:], float); Vp = np.asarray(rec["_vel"][t:], float)
            L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
            rc = rational_certificate(p_att, v_att, np.asarray(r["_acc"], float),
                                      float(E.tau_deploy), L, N_LIM, DT, E.kill_radius)
            cert.append({"witness": r["witness"], "sampled_mode": r["sampled_mode"],
                         "exact_mode": r["exact_mode"],
                         "attack_policy_hash": r["attack_policy_hash"],
                         "selected_because": whys,
                         "m_continuous_forced_m": r["m_continuous_forced_m"],
                         "certificate": rc.get("certificate"),
                         "implied_margin_lower_bound_m": rc.get("implied_margin_lower_bound_m"),
                         "max_subdivision_depth": rc.get("max_subdivision_depth"),
                         "verifier_version": rc.get("verifier_version")})
            print("    %-22s %-13s %-28s %s"
                  % (r["witness"], r["sampled_mode"], rc.get("certificate"),
                     ("lb %+.6f m" % rc["implied_margin_lower_bound_m"])
                     if rc.get("implied_margin_lower_bound_m") is not None else ""), flush=True)
        ncf = sum(1 for c in cert if c["certificate"] == "CERTIFIED_COLLISION_FREE")
        print("    -> CERTIFIED_COLLISION_FREE %d / %d" % (ncf, len(cert)))

    for r in rows:
        r.pop("_acc", None); r.pop("_witness_ctx", None)
    out = {"meta": {"script": "c1_phase1p_verifier_audit",
                    "role": "step 3.5 verifier cleanup; no verdict, no new search",
                    "pre_registered": {"certified_tolerance_m": CERTIFIED_TOLERANCE_M,
                                       "tie_band_m": TIE_BAND_M,
                                       "boundary_band_m": BOUNDARY_BAND_M,
                                       "small_margin_m": SMALL_MARGIN_M,
                                       "grid_near_s": GRID_NEAR_M},
                    "protocol": G.PROTOCOL_VERSION},
           "A1_invariant": {"cross_path_max_position_diff_m": xp_pos,
                            "cross_path_max_distance_diff_m": xp_dst,
                            "shipped_negatives": int((gs < 0).sum()),
                            "shipped_worst_m": float(gs.min()),
                            "forced_negatives": int((gf < 0).sum()),
                            "forced_worst_m": float(gf.min()),
                            "shipped_minus_forced_max_m": float(mf.max()),
                            "missed_candidates_beyond_tol": int((np.abs(mf) > CERTIFIED_TOLERANCE_M).sum()),
                            "violations_beyond_tolerance": len(viol)},
           "A2_mode_reassignment": {"label_changes": len(changed),
                                    "ambiguous": len(amb),
                                    "counts": dict(cnt),
                                    "witnesses_per_exact_mode": {k: len(v) for k, v in wocc.items()}},
           "A4_argmin": {"n": len(rows), "on_grid_node": len(rows) - len(interior),
                         "interior": len(interior),
                         "median_dist_attacker_boundary_s": float(np.median(dseg)),
                         "median_dist_hermite_node_s": float(np.median(dnod)),
                         "argmin_at_forced_sample": len(from_forced)},
           "A5_sampling_accounting": {"nominal": nominal, "selected": selected,
                                      "shortfall": nominal - selected, "per_cell": acct},
           "A3_certificates": cert,
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
