"""C-1 Phase 1I — external-review defect response (2026-07-25).

Runs the four checks the reviewer's "자기신고에 없는 추가 결함" list requires, plus a
properly sealed confirmatory certification.  Nothing here defends the previous
numbers; every block is written to be able to overturn them.

  #2  DEPLOY-WINDOW OFF-BY-ONE.  The judge checks E_lane on range(f, f+n_dep+1)
      with n_dep = int(round(tau/dt)) = 8 -> f..f+8, nine states, 0.40 s.  Phase
      1F/1G's LP used N_DEP = 9 -> f..f+9, 0.45 s: one step MORE than the judge.
      Now fixed to 8.  This block re-derives every affected number under both
      windows so the delta is on the record rather than asserted.

  #3  SELECTION BIAS.  T* was found by sweeping 14 T x 3 fire steps and reporting
      the LCB of the first pass, on the SAME cert seeds.  That LCB is not a 95 %
      confirmatory certificate.  This block SEALS the winning (rho0, T, f, a_seq)
      and re-evaluates ONCE on cert seeds never used in the search.

  #4  WILSON VALIDITY.  The reachable union is Block-1 (stochastic accel samples)
      UNIONED with deterministic boundary/dogleg blocks, and the three "scrambled"
      seeds are POOLED -- so the deterministic witnesses are counted three times
      with identical outcomes.  This block measures the composition of the FEASIBLE
      subset (the denominator of v_soft) and reports the across-scramble estimator
      the reviewer prefers alongside the pooled Wilson LCB.

  #1  FIXED-RAY LINEARITY.  rho_t = rho0 + dt^2 sum (t-k) a_k holds only if each
      limiter stays on a non-rotating radial ray with no tangential/axial motion.
      This block measures the realised azimuth drift and the LP-vs-simulator rho
      residual, so the modelling gap is a number instead of an assumption.

  #7  CONTROLLER CHARACTER.  Arm L feeds a fixed radial acceleration schedule but
      recomputes the radial direction and damps tangential velocity from the live
      observation.  It is neither pure open-loop nor a feedback policy; this block
      states which parts are which.
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
from shepherd.scripts.c1_phase1e import (judge_models, clearance_dense, displacement_sup,
                                         make_labels, hermite_positions, _mask_moving,
                                         CERT_SEEDS, wilson)
from shepherd.scripts.c1_plant_bound import (solve_witness_hold, make_lp_arm, rho_row,
                                             DT, N_DEP, BAND_LO, BAND_HI, FLOOR)
from shepherd.game import viability as V

SEARCH_SEEDS = CERT_SEEDS                              # used to FIND the witness
CONFIRM_SEEDS = (91_000_101, 91_000_102, 91_000_103)   # never used in the search
T_ONE_SIDED_95_DF2 = 2.9200                            # t_{0.95, 2}
APEX = np.array([2.0, 0.0, 0.0]); AXIS = np.array([1.0, 0.0, 0.0])


def azimuth(p):
    rr = np.asarray(p, float) - APEX
    return np.arctan2(rr[..., 2], rr[..., 1])


def across_scramble_lcb(per_seed):
    """Reviewer-preferred estimator: treat each independent scramble as ONE draw.
    One-sided 95 % t-LCB on the mean of 3 scramble estimates (2 df)."""
    v = np.asarray([x for x in per_seed if np.isfinite(x)], float)
    if len(v) < 2:
        return {"mean": float(v[0]) if len(v) else None, "lcb": None, "n_scrambles": len(v)}
    m = float(v.mean()); s = float(v.std(ddof=1))
    return {"mean": m, "sd": s, "n_scrambles": int(len(v)),
            "lcb": float(m - T_ONE_SIDED_95_DF2 * s / np.sqrt(len(v)))}


# --------------------------------------------------------------- #4 union composition
def union_composition(pe, rec, *, n_cert, seed):
    """How much of the FEASIBLE set (the v_soft denominator) is deterministic?"""
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    u = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max, n=n_cert,
                                n_segments=max(int(E.n_segments), 2), seed=int(seed), **kw)

    def L_actual(times):
        return hermite_positions(P_post, V_post, times)[0]

    masks = [_mask_moving(pb, L_actual, E.kill_radius, tau) for pb in u.path_blocks]
    feas = np.concatenate(masks, axis=0) & u.turn_feasible
    bs = list(u.block_sizes); edges = np.cumsum([0] + bs)
    per_block = [int(feas[edges[i]:edges[i + 1]].sum()) for i in range(len(bs))]
    n_f = int(feas.sum())
    return {"n_total": int(u.n_total), "block_sizes": [int(b) for b in bs],
            "stochastic_share_of_union": float(bs[0] / u.n_total),
            "feasible_per_block": per_block, "n_feasible": n_f,
            "deterministic_share_of_feasible": float(sum(per_block[1:]) / max(n_f, 1)),
            "note": "blocks 2.. are deterministic; pooling 3 seeds counts them 3x with "
                    "identical outcomes, so the pooled Wilson n is inflated and correlated"}


# --------------------------------------------------------------- #1/#7 fixed-ray check
def fixed_ray_residual(rec, a_seq, f):
    """Realised rho vs the LP's fixed-ray prediction, plus azimuth drift."""
    lim = np.asarray(rec["_lim"], float)                 # (T, N, 3)
    vel = np.asarray(rec["_vel"], float)
    rr = lim - APEX[None, None, :]
    ax = rr @ AXIS
    perp_vec = rr - ax[:, :, None] * AXIS[None, None, :]
    rho = np.linalg.norm(perp_vec, axis=2)               # (T, N)
    phi = np.arctan2(perp_vec[:, :, 2], perp_vec[:, :, 1])
    H = len(a_seq)
    n_steps = min(len(rho), H + 1)
    pred = np.array([rho[0].mean() + rho_row(t, H) @ a_seq for t in range(n_steps)])
    resid = pred - rho[:n_steps].mean(axis=1)
    dphi = np.degrees(np.abs(((phi[:n_steps] - phi[0][None, :]) + np.pi) % (2 * np.pi) - np.pi))
    # tangential / axial velocity share of the commanded budget
    rad_hat = perp_vec / (rho[:, :, None] + 1e-12)
    v_rad = (vel[:, :, 1:] * rad_hat[:, :, 1:]).sum(axis=2)
    v_tan = np.linalg.norm(vel[:, :, 1:] - v_rad[:, :, None] * rad_hat[:, :, 1:], axis=2)
    v_ax = np.abs(vel[:, :, 0])
    return {"lp_rho_residual_m": {"max_abs": float(np.abs(resid).max()),
                                  "at_fire": float(resid[min(f, n_steps - 1)]),
                                  "rms": float(np.sqrt((resid ** 2).mean()))},
            "azimuth_drift_deg": {"max": float(dphi.max()), "at_fire": float(dphi[min(f, n_steps - 1)].max())},
            "tangential_speed_ms": {"max": float(v_tan[:n_steps].max())},
            "axial_speed_ms": {"max": float(v_ax[:n_steps].max())},
            "controller_character": "radial magnitude = OPEN-LOOP schedule a_seq[t]; "
                                    "radial DIRECTION and tangential damping = feedback on the "
                                    "live observation; therefore neither pure open-loop replay "
                                    "nor a disturbance-robust feedback certificate"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rho0", default="2.8,3.2,4.0,5.0")
    ap.add_argument("--tlead", default="0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75,0.80")
    ap.add_argument("--search-ncert", type=int, default=2000)
    ap.add_argument("--confirm-ncert", type=int, default=20000)
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1i_audit_response.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    n_dep_judge = int(round(E.tau_deploy / DT))
    out = {"meta": {"phase": "1I_audit_response", "n_dep_judge": n_dep_judge, "N_DEP_lp": N_DEP,
                    "search_seeds": list(SEARCH_SEEDS), "confirm_seeds": list(CONFIRM_SEEDS),
                    "search_ncert": a.search_ncert, "confirm_ncert": a.confirm_ncert,
                    "theta": pe.theta}}

    # ---- #2 off-by-one: both windows, side by side ---------------------------
    print("== #2 deploy-window off-by-one: LP feasibility under n_dep 8 (judge) vs 9 (1F/1G) ==")
    ob = []
    for rho0 in [float(x) for x in a.rho0.split(",")]:
        for tl in [float(x) for x in a.tlead.split(",")]:
            fmax = int(round(tl / DT))
            r = {"rho0": rho0, "T": tl}
            for nd in (8, 9):
                best = None
                for f in range(max(1, fmax - 2), fmax + 1):
                    s, d, m = solve_witness_hold(rho0, f, n_dep=nd)
                    if s is not None and (best is None or d < best[0]):
                        best = (d, f)
                r["nd%d" % nd] = None if best is None else {"d_star": round(best[0], 4), "f": best[1]}
            r["differs"] = (r["nd8"] is None) != (r["nd9"] is None)
            ob.append(r)
    n_diff = sum(1 for r in ob if r["differs"])
    out["offbyone"] = {"cells": ob, "n_feasibility_flips": n_diff,
                       "verdict": ("CONFIRMED_AND_FIXED; no feasibility flip at this grid"
                                   if n_diff == 0 else "CONFIRMED_AND_FIXED; %d cells flip" % n_diff)}
    print("   feasibility flips between the two windows: %d / %d cells" % (n_diff, len(ob)))

    # ---- search on SEARCH_SEEDS, then seal -----------------------------------
    print("== search (SEARCH_SEEDS, n=%d) -> seal -> confirmatory (CONFIRM_SEEDS, n=%d) =="
          % (a.search_ncert, a.confirm_ncert))
    sealed, rows = {}, []
    for rho0 in [float(x) for x in a.rho0.split(",")]:
        found = None
        for tl in [float(x) for x in a.tlead.split(",")]:
            fmax = int(round(tl / DT))
            cands = []
            for f in range(max(1, fmax - 2), fmax + 1):
                s, d, m = solve_witness_hold(rho0, f)
                if s is not None:
                    cands.append((d, f, s))
            cands.sort(key=lambda z: z[0])
            for d, f, s in cands:
                w = log_ctrl(make_lp_arm(s))
                rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
                jm = judge_models(pe, rec, n_cert=a.search_ncert, seeds=SEARCH_SEEDS)
                if rec["tier"] >= 4 and jm["actual"]["certifies_point"]:
                    found = (tl, f, d, s)
                    break
            if found:
                break
        if not found:
            print("   rho0=%.1f : no witness found" % rho0); continue
        tl, f, d, s = found
        sealed[str(rho0)] = {"T": tl, "f": f, "lp_d_star": round(d, 4),
                             "a_seq": [round(float(x), 4) for x in s], "n_dep": N_DEP}

        # ---- CONFIRMATORY: fresh seeds, single evaluation, no further search ----
        w = log_ctrl(make_lp_arm(s))
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        jm = judge_models(pe, rec, n_cert=a.confirm_ncert, seeds=CONFIRM_SEEDS)
        clr = clearance_dense(pe, rec, r_lane=RL, r_body=RB)
        disp = displacement_sup(pe, rec)
        labs = make_labels(rec, jm, clr, disp)
        comp = union_composition(pe, rec, n_cert=a.confirm_ncert, seed=CONFIRM_SEEDS[0])
        ray = fixed_ray_residual(rec, s, f)
        acr = across_scramble_lcb(jm["actual"]["per_seed_v_soft"])
        row = {"rho0": rho0, "T": tl, "f": f, "lp_d_star": round(d, 4), "tier": rec["tier"],
               "sup_disp": disp["sup_disp"], "dense_clr": clr["m_clear_dense"],
               "v_soft_actual_confirm": jm["actual"]["v_soft"],
               "wilson_lcb_pooled": jm["actual"]["v_soft_lcb"],
               "per_seed_v_soft": jm["actual"]["per_seed_v_soft"],
               "across_scramble": acr,
               "n_feas_confirm": jm["actual"]["n_feasible"],
               "certifies_pooled_wilson": jm["actual"]["certifies"],
               "certifies_across_scramble": bool(acr["lcb"] is not None and acr["lcb"] >= pe.theta),
               "union_composition": comp, "fixed_ray": ray, "labels": labs}
        rows.append(row)
        print("   rho0=%.1f T=%.2f f=%2d | confirm v_soft %.4f | Wilson LCB %.4f | across-scramble "
              "mean %.4f sd %.4f LCB %s | n_feas %d | det share of feasible %.1f%% | "
              "LP rho resid max %.4f m | azim drift max %.2f deg"
              % (rho0, tl, f, jm["actual"]["v_soft"], jm["actual"]["v_soft_lcb"], acr["mean"],
                 acr.get("sd", float("nan")),
                 ("%.4f" % acr["lcb"]) if acr["lcb"] is not None else "n/a",
                 jm["actual"]["n_feasible"], 100 * comp["deterministic_share_of_feasible"],
                 ray["lp_rho_residual_m"]["max_abs"], ray["azimuth_drift_deg"]["max"]), flush=True)

    out["sealed_witnesses"] = sealed
    out["confirmatory"] = rows
    out["T_star_RH_remask_grid"] = {k: v["T"] for k, v in sealed.items()}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
