"""C-1 escape geometry — WHERE do the surviving escapes go?

The plant LP (c1_plant_bound) constrains only the RADIAL subproblem: each limiter
contracts along its own current azimuth, so the four-limiter ring keeps whatever
azimuthal spacing it started with.  Whether that is a real limitation depends on
where the escapes that survive the ring actually leave.

For a given witness this script rebuilds the SAME reachable union the E1.5 judge
uses, applies the SAME time-aligned `actual` remask, and then decomposes the
surviving escapes (feasible AND NOT caught) by

  * azimuth  phi = atan2(z, y) of the escape endpoint about the engagement axis,
    referred to the four limiter azimuths -> "did it leave through a gap between
    limiters, or straight past the ring?"
  * radius   perp distance of the endpoint from the axis
  * axial    along-axis coordinate

and reports, per escape, the angular distance to the NEAREST limiter azimuth.
If escapes concentrate at the azimuthal midpoints between limiters, azimuthal
sealing is a live degree of freedom and a policy that redistributes limiters in
azimuth can buy capture that no radial schedule can.  If they are uniform in phi,
or concentrated ON the limiters, the residual is not azimuthal and an angular arm
would be wasted effort.

Diagnostic only.  No claim, no new judge.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, N_LIM, R_BODY, M_SAFETY,
                                                PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, block_times, _mask_moving
from shepherd.scripts.c1_plant_bound import solve_witness_hold, make_lp_arm
from shepherd.game import viability as V

APEX = np.array([2.0, 0.0, 0.0]); AXIS = np.array([1.0, 0.0, 0.0])


def azimuth(p):
    """phi about the engagement axis, in (-pi, pi]; the (y,z) plane is the correct one."""
    rr = np.asarray(p, float) - APEX
    return np.arctan2(rr[..., 2], rr[..., 1])


def analyse(pe, rec, *, n_cert, seed):
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]; fin9 = o[36:45]
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, fin9)
    u = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max, n=n_cert,
                                n_segments=max(int(E.n_segments), 2), seed=int(seed), **kw)

    def L_actual(times):
        pos, _ = hermite_positions(P_post, V_post, times)
        return pos

    masks = [_mask_moving(pb, L_actual, E.kill_radius, tau) for pb in u.path_blocks]
    feas = (np.concatenate(masks, axis=0) if masks else np.ones(u.n_total, bool)) & u.turn_feasible
    esc = feas & ~np.asarray(u.caught, bool)                 # feasible AND not caught
    ep = np.asarray(u.endpoints, float)

    lim_phi = np.sort(azimuth(P_post[0]))                     # limiter azimuths at fire
    out = {"n_feasible": int(feas.sum()), "n_escape": int(esc.sum()),
           "v_soft_actual": float((u.caught & feas).sum() / max(feas.sum(), 1)),
           "limiter_phi_deg": np.degrees(lim_phi).round(2).tolist(),
           "limiter_gap_deg": float(np.degrees(np.diff(np.concatenate(
               [lim_phi, [lim_phi[0] + 2 * np.pi]])).max()))}
    if not esc.any():
        out["note"] = "no surviving escape"
        return out
    pe_ = ep[esc]
    phi = azimuth(pe_)
    rr = pe_ - APEX
    out["escape_axial_m"] = {"min": float((rr @ AXIS).min()), "med": float(np.median(rr @ AXIS)),
                             "max": float((rr @ AXIS).max())}
    perp = np.linalg.norm(rr - (rr @ AXIS)[:, None] * AXIS[None, :], axis=1)
    out["escape_perp_m"] = {"min": float(perp.min()), "med": float(np.median(perp)),
                            "max": float(perp.max()), "frac_inside_ring": float((perp <= 2.6).mean())}
    # angular distance to the nearest limiter azimuth, in units of the half-gap
    def dphi(ph):
        return np.abs(((ph[:, None] - lim_phi[None, :]) + np.pi) % (2 * np.pi) - np.pi).min(axis=1)
    d = dphi(phi)
    half_gap = np.pi / N_LIM                                   # 45 deg for an even 4-ring
    # NULL CONTROL: the union's own azimuth distribution is not uniform, so the escape
    # skew is only meaningful against the ALL-FEASIBLE reference, not against U(0,1).
    d_all = dphi(azimuth(ep[feas]))
    out["null_all_feasible"] = {
        "n": int(feas.sum()), "med": float(np.median(d_all) / half_gap),
        "mean": float(d_all.mean() / half_gap),
        "frac_outer_half": float((d_all > half_gap / 2).mean()),
        "hist_5bin": np.histogram(d_all / half_gap, bins=5, range=(0.0, 1.0))[0].tolist()}
    out["escape_dphi_to_nearest_limiter_deg"] = {
        "min": float(np.degrees(d.min())), "med": float(np.degrees(np.median(d))),
        "max": float(np.degrees(d.max())), "mean": float(np.degrees(d.mean()))}
    out["escape_dphi_normalised"] = {   # 0 = on a limiter, 1 = exactly at a gap midpoint
        "med": float(np.median(d) / half_gap), "mean": float(d.mean() / half_gap),
        "frac_outer_half": float((d > half_gap / 2).mean())}
    # uniform-phi reference: for phi ~ U(-pi,pi] the normalised distance is ~U(0,1)
    out["uniform_reference"] = {"med": 0.5, "mean": 0.5, "frac_outer_half": 0.5}
    out["skew_vs_null"] = float(out["escape_dphi_normalised"]["frac_outer_half"]
                                - out["null_all_feasible"]["frac_outer_half"])
    hist, edges = np.histogram(d / half_gap, bins=5, range=(0.0, 1.0))
    out["dphi_hist_5bin_0on_limiter_1at_gap"] = hist.tolist()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-cert", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=77_000_001)
    ap.add_argument("--out", default="results/c1_corridor/c1_escape_geometry.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    cases = [("ARM_L certified", 5.0, 0.55, ("L", 10)),
             ("ARM_L certified", 3.2, 0.25, ("L", 5)),
             ("ARM_L rejected", 4.0, 0.35, ("L", 7)),
             ("ARM_L rejected", 3.2, 0.20, ("L", 4)),
             ("baseline", 5.0, 1.00, ("P", None)),
             ("baseline", 3.2, 0.50, ("C", None))]
    rows = []
    for tag, rho0, tl, (arm, f) in cases:
        if arm == "L":
            seq, d, m = solve_witness_hold(rho0, f)
            if seq is None:
                continue
            ctrl = make_lp_arm(seq)
        else:
            ctrl = make_contract() if arm == "C" else make_pd()
        w = log_ctrl(ctrl)
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        r = analyse(pe, rec, n_cert=a.n_cert, seed=a.seed)
        r.update({"tag": tag, "rho0": rho0, "T": tl, "arm": arm, "f": f, "tier": rec["tier"],
                  "max_angular_gap_deg_unified": rec["max_angular_gap_deg"]})
        rows.append(r)
        dn = r.get("escape_dphi_normalised")
        nu = r.get("null_all_feasible")
        if dn:
            print("  %-16s %.1f/%.2f %-2s tier %d | v_soft_act %.3f | escapes %4d/%4d | gap %.0f deg"
                  " | frac>0.5  esc %.2f  null %.2f  (skew %+.2f) | esc hist %s | null hist %s"
                  % (tag, rho0, tl, arm, r["tier"], r["v_soft_actual"], r["n_escape"],
                     r["n_feasible"], r["limiter_gap_deg"], dn["frac_outer_half"],
                     nu["frac_outer_half"], r["skew_vs_null"],
                     r["dphi_hist_5bin_0on_limiter_1at_gap"], nu["hist_5bin"]), flush=True)
        else:
            print("  %-16s %.1f/%.2f %-2s tier %d | v_soft_act %.3f | escapes %4d/%4d | gap %.0f deg"
                  " | NO SURVIVING ESCAPE"
                  % (tag, rho0, tl, arm, r["tier"], r["v_soft_actual"], r["n_escape"],
                     r["n_feasible"], r["limiter_gap_deg"]), flush=True)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps({"meta": {"n_cert": a.n_cert, "seed": a.seed,
        "note": "diagnostic only; same union + actual remask as c1_phase1e"}, "rows": rows},
        indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
