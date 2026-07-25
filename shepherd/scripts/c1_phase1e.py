"""C-1 Phase 1E — E1.5 authoritative-side judge audit (external review 2026-07-24).

Implements the reviewer's mandated corrections before any optimization arm:

 (R1) THREE limiter-motion models evaluated on ONE shared reachable union (CRN):
        static      : limiters frozen at the fire instant          (legacy judge)
        cv_swept    : limiters extrapolated at constant velocity   (E1 audit)
        actual      : the REALIZED closed-loop limiter trajectory over
                      [t_fire, t_fire+tau], Hermite-interpolated onto each path
                      block's own time grid                        (E1.5)
      All three are TIME-ALIGNED (attacker substep s compared against limiter
      position at the SAME s) and are *fixed-path remasking* audits: the attacker
      sample bank is NOT replanned against moving limiters.  ==> the `actual`
      model is NOT a full dynamic certificate; adversarial replan is still open.

 (R2) MC uncertainty is reported, not hidden.  v_soft is a conditional proportion
      over n_feasible samples (n_feasible ~ 8 at n=2000 -> useless).  Certification
      uses n_cert samples x several scrambled seeds and a one-sided Wilson LCB.

 (R3) The V-a velocity screen is replaced by the MEASURED displacement
      sup_s ||L(s) - L(0)|| over [t_fire, t_fire+tau].  (1/2 a_max tau^2 = 2.4 m
      at a_max=30, tau=0.4, so a fire-instant velocity bound cannot imply
      static-judge validity.)

 (R4) Lane clearance recomputed without the two known defects:
        - axial-window dropout (limiters with ax outside [0, axial_len] were
          simply not counted)  -> point-to-SEGMENT distance instead
        - step-sampled minimum (tunneling between 0.05 s samples)
          -> dense Hermite substeps

 (R5) Full witness artifacts are stored (action sequence, reset state, seeds,
      commit/config/trajectory hashes, all judge outputs).

Labels emitted per witness:
    TIER4_GEOM                 legacy geometric tier 4
    TIER4_SWEPT_CONSISTENT     + cv_swept still certifies
    TIER4_DYNAMIC_REMASK       + actual-trajectory remask still certifies
    JUDGE_MODEL_SENSITIVE      models disagree -> unresolved (neither safe nor unsafe)
    MC_UNCERTIFIED             v_soft LCB < theta at the tested sample size
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, subprocess
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd, make_hold,
    THETA, N_LIM, R_BODY, M_SAFETY, PRIMARY, V_CLOSE, DT)
from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, make_finisher_fn,
    knots_to_seq, A_MAX, ATT_P0)
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl, seq_ctrl
from shepherd.game import viability as V

EPS_DISP = 0.10                    # allowed sup-displacement over tau, as a fraction of r_kill
N_T = 24                           # viability substeps per segment
N_CERT = 20000                     # certification-grade MC sample count
CERT_SEEDS = (77_000_001, 77_000_002, 77_000_003)
Z_ONE_SIDED_95 = 1.645
SUBSTEPS = 8                       # clearance substeps per env dt


# ---------------------------------------------------------------- statistics
def wilson(k, n, z=Z_ONE_SIDED_95):
    """(lower, upper) Wilson score interval for a binomial proportion."""
    if n <= 0: return (0.0, 1.0)
    p = k / n; d = 1.0 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (float(max(0.0, c - h)), float(min(1.0, c + h)))


# ---------------------------------------------------------------- trajectory interpolation
def hermite_positions(P, Vel, times, dt=DT):
    """Cubic Hermite interpolation of limiter positions.
    P, Vel: (S, N, 3) samples at k*dt (k = 0..S-1, k=0 == fire instant).
    times : (T,) query times in [0, (S-1)*dt] (clamped; linear extrapolation past the end).
    -> (T, N, 3), plus a flag telling whether extrapolation was needed."""
    P = np.asarray(P, float); Vel = np.asarray(Vel, float)
    S = len(P); t_max = (S - 1) * dt
    times = np.asarray(times, float)
    extrap = bool(times.max() > t_max + 1e-12)
    out = np.empty((len(times), P.shape[1], 3))
    for j, t in enumerate(times):
        if t >= t_max:                                   # constant-velocity extension
            out[j] = P[-1] + Vel[-1] * (t - t_max); continue
        k = min(int(t / dt), S - 2); u = (t - k * dt) / dt
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u
        h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        out[j] = h00 * P[k] + h10 * dt * Vel[k] + h01 * P[k + 1] + h11 * dt * Vel[k + 1]
    return out, extrap


def block_times(T_b, tau):
    """Global time stamps of a union path block (K segments x N_T substeps on [0, tau/K])."""
    if T_b == N_T: return np.linspace(0.0, tau, N_T)
    K = int(round(T_b / N_T)); h = tau / K
    return np.concatenate([j * h + np.linspace(0.0, h, N_T) for j in range(K)])


# ---------------------------------------------------------------- the three judges
def _mask_moving(paths, L_of_t, kill_radius, tau):
    """Time-aligned no-go mask: attacker witness path vs limiter positions at the SAME
    substep time.  L_of_t(times) -> (T, nL, 3)."""
    n, T, _ = paths.shape
    Lt = L_of_t(block_times(T, tau))                     # (T, nL, 3)
    d = np.linalg.norm(paths[:, :, None, :] - Lt[None, :, :, :], axis=3)
    return ~(d <= kill_radius).any(axis=(1, 2))


def judge_models(pe, rec, *, n_cert=N_CERT, seeds=CERT_SEEDS):
    """static / cv_swept / actual on the SAME union, at certification sample size."""
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]; fin9 = o[36:45]
    L0 = np.asarray(rec["_lim"][t], float); V0 = np.asarray(rec["_vel"][t], float)
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, fin9)

    def L_static(times): return np.repeat(L0[None, :, :], len(times), axis=0)
    def L_cv(times): return L0[None, :, :] + V0[None, :, :] * np.asarray(times)[:, None, None]
    extrap_flag = {"v": False}
    def L_actual(times):
        pos, ex = hermite_positions(P_post, V_post, times)
        extrap_flag["v"] = extrap_flag["v"] or ex
        return pos

    models = {"static": L_static, "cv_swept": L_cv, "actual": L_actual}
    acc = {m: {"caught": 0, "feas": 0, "total": 0, "vs": [], "pf": []} for m in models}
    for sd in seeds:
        u = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                    n=n_cert, n_segments=max(int(E.n_segments), 2),
                                    seed=int(sd), **kw)
        for m, Lf in models.items():
            masks = [_mask_moving(pb, Lf, E.kill_radius, tau) for pb in u.path_blocks]
            feas = (np.concatenate(masks, axis=0) if masks else np.ones(u.n_total, bool)) & u.turn_feasible
            k_f = int(feas.sum()); k_c = int((u.caught & feas).sum())
            acc[m]["caught"] += k_c; acc[m]["feas"] += k_f; acc[m]["total"] += u.n_total
            acc[m]["vs"].append(k_c / k_f if k_f else float("nan"))
            acc[m]["pf"].append(k_f / u.n_total)
    out = {}
    for m, a in acc.items():
        vs_lo, vs_hi = wilson(a["caught"], a["feas"])
        pf_lo, pf_hi = wilson(a["feas"], a["total"])
        out[m] = {"v_soft": (a["caught"] / a["feas"] if a["feas"] else None),
                  "v_soft_lcb": vs_lo, "v_soft_ucb": vs_hi,
                  "n_feasible": a["feas"], "n_total": a["total"],
                  "p_feas": a["feas"] / a["total"], "p_feas_lcb": pf_lo, "p_feas_ucb": pf_hi,
                  "per_seed_v_soft": a["vs"], "per_seed_p_feas": a["pf"],
                  "certifies": bool(a["feas"] > 0 and vs_lo >= pe.theta),
                  "certifies_point": bool(a["feas"] > 0 and (a["caught"] / max(a["feas"], 1)) >= pe.theta)}
    out["_actual_extrapolated"] = extrap_flag["v"]
    out["_n_cert"] = n_cert; out["_seeds"] = list(seeds)
    return out


# ---------------------------------------------------------------- clearance (R4)
def clearance_dense(pe, rec, *, r_lane, r_body, substeps=SUBSTEPS):
    """Lane clearance without the axial-window dropout and without step-sampling
    tunneling: point-to-SEGMENT distance on a dense Hermite time grid."""
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    if rec["fire_step"] is None or rec["_fin_axis"] is None:
        return {"m_clear_dense": None, "defined": False}
    apex = np.asarray(rec["_fin_apex"], float); ax_hat = np.asarray(rec["_fin_axis"], float)
    seg_len = float(rec["_axial_len"])
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    n_dep = int(round(tau / DT))
    times = np.linspace(0.0, n_dep * DT, n_dep * substeps + 1)
    pos, extrap = hermite_positions(P_post, V_post, times)                 # (T,N,3)
    rr = pos - apex[None, None, :]
    ax = rr @ ax_hat                                                        # (T,N)
    ax_c = np.clip(ax, 0.0, max(seg_len, 0.0))
    closest = apex[None, None, :] + ax_c[:, :, None] * ax_hat[None, None, :]
    d = np.linalg.norm(pos - closest, axis=2)                               # (T,N)
    m = float((d - r_lane - r_body).min())
    idx = np.unravel_index(np.argmin(d - r_lane - r_body), d.shape)
    return {"m_clear_dense": m, "defined": True, "extrapolated": bool(extrap),
            "argmin_time": float(times[idx[0]]), "argmin_limiter": int(idx[1]),
            "axial_at_min": float(ax[idx]), "axial_len": seg_len,
            "outside_axial_window": bool(ax[idx] < 0.0 or ax[idx] > seg_len),
            "substep_dt": float(times[1] - times[0])}


# ---------------------------------------------------------------- displacement (R3)
def displacement_sup(pe, rec):
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    times = np.linspace(0.0, tau, 8 * int(round(tau / DT)) + 1)
    pos, extrap = hermite_positions(P_post, V_post, times)
    disp = np.linalg.norm(pos - pos[0][None, :, :], axis=2).max()
    v0 = np.linalg.norm(V_post[0], axis=1).max()
    return {"sup_disp": float(disp), "limit": float(EPS_DISP * E.kill_radius),
            "pass": bool(disp <= EPS_DISP * E.kill_radius),
            "v_fire_max": float(v0),
            "v_only_screen_pass": bool(v0 * tau <= EPS_DISP * E.kill_radius),
            "worst_case_bound_if_max_accel": float(v0 * tau + 0.5 * A_MAX * tau ** 2),
            "extrapolated": bool(extrap)}


# ---------------------------------------------------------------- labels + artifacts
def make_labels(rec, jm, clr, disp):
    geom = bool(rec["tier"] >= 4 and not rec["penetrated"])
    labs = []
    if geom: labs.append("TIER4_GEOM")
    cert = {m: jm[m]["certifies"] for m in ("static", "cv_swept", "actual")}
    pt = {m: jm[m]["certifies_point"] for m in ("static", "cv_swept", "actual")}
    if geom and pt["cv_swept"]: labs.append("TIER4_SWEPT_CONSISTENT")
    if geom and pt["actual"]: labs.append("TIER4_DYNAMIC_REMASK")
    if len(set(pt.values())) > 1: labs.append("JUDGE_MODEL_SENSITIVE")
    # MC uncertainty is a statement about the AUTHORITATIVE-SIDE model only:
    # point estimate certifies but the one-sided LCB does not.
    if geom and pt["actual"] and not cert["actual"]: labs.append("MC_UNCERTIFIED")
    if geom and not pt["actual"]: labs.append("FALSIFIED_UNDER_ACTUAL_TRAJECTORY_JUDGE")
    if clr["defined"] and clr["m_clear_dense"] is not None and clr["m_clear_dense"] < 0:
        labs.append("LANE_CLEARANCE_FAILS_DENSE")
    if not disp["pass"]: labs.append("STATIC_JUDGE_DISPLACEMENT_SCREEN_FAIL")
    return labs


def _hash(a): return hashlib.sha256(np.asarray(a, float).round(9).tobytes()).hexdigest()[:16]


def _git(cmd, default="?"):
    try: return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception: return default


# ---------------------------------------------------------------- driver
BASE_WITNESSES = [(2.8, 0.30, "C"), (3.2, 0.50, "C"), (3.2, 0.70, "P"),
                  (4.0, 0.70, "C"), (4.0, 0.70, "P"), (5.0, 1.00, "P")]
O_WITNESSES = [(3.2, 0.35, "WS1", 700), (3.2, 0.40, "WS1", 700), (4.0, 0.70, "WS2", 701)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-cert", type=int, default=N_CERT)
    ap.add_argument("--out", default="results/c1_corridor/c1_dynamic_judge.json")
    ap.add_argument("--artifacts", default="results/c1_corridor/witness_artifacts")
    a = ap.parse_args()
    env_cfg, m3, theta = _load("configs/m3a_a3e_p1.yaml"); pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    art_dir = pathlib.Path(a.artifacts); art_dir.mkdir(parents=True, exist_ok=True)
    commit = _git("git rev-parse --short HEAD")
    cfg_hash = hashlib.sha256(pathlib.Path("configs/m3a_a3e_p1.yaml").read_bytes()).hexdigest()[:16]
    rows = []

    def record(tag, rho0, tl, arm, rec, actions, spawn, extra=None):
        jm = judge_models(pe, rec, n_cert=a.n_cert)
        clr = clearance_dense(pe, rec, r_lane=RL, r_body=RB)
        disp = displacement_sup(pe, rec)
        labs = make_labels(rec, jm, clr, disp)
        art = {"tag": tag, "rho0": rho0, "T": tl, "arm": arm, "commit": commit,
               "config_sha": cfg_hash, "reset_seed": 1100, "crn_seed": 1101,
               "cert_seeds": list(CERT_SEEDS), "n_cert": a.n_cert,
               "spawn": {k: np.asarray(v).tolist() for k, v in spawn.items()},
               "actions": np.asarray(actions, float).tolist(),
               "traj_sha": _hash(rec["_lim"]), "action_sha": _hash(actions),
               "judges": jm, "clearance_dense": clr, "displacement": disp, "labels": labs}
        if extra: art.update(extra)
        (art_dir / ("%s_%s_%.1f_%.2f.json" % (tag, arm.replace("-", ""), rho0, tl))).write_text(
            json.dumps(art, indent=1, default=float))
        row = {"src": tag, "rho0": rho0, "T": tl, "arm": arm, "tier": rec["tier"],
               "legacy_clr": rec["clearance_margin"], "dense_clr": clr["m_clear_dense"],
               "clr_outside_axial": clr.get("outside_axial_window"),
               "sup_disp": disp["sup_disp"], "v_fire_max": disp["v_fire_max"],
               "v_soft_static": jm["static"]["v_soft"], "v_soft_cv": jm["cv_swept"]["v_soft"],
               "v_soft_actual": jm["actual"]["v_soft"],
               "lcb_static": jm["static"]["v_soft_lcb"], "lcb_cv": jm["cv_swept"]["v_soft_lcb"],
               "lcb_actual": jm["actual"]["v_soft_lcb"],
               "n_feas_static": jm["static"]["n_feasible"], "n_feas_actual": jm["actual"]["n_feasible"],
               "labels": labs}
        rows.append(row)
        print("  %s %.1f/%.2f %-7s | v_soft st %.3f cv %.3f act %.3f (LCB act %.3f, n_feas %d)"
              " | disp %.2f/%.2f | clr %.3f->%.3f | %s" % (
              tag, rho0, tl, arm, jm["static"]["v_soft"] or -1, jm["cv_swept"]["v_soft"] or -1,
              jm["actual"]["v_soft"] or -1, jm["actual"]["v_soft_lcb"], jm["actual"]["n_feasible"],
              disp["sup_disp"], disp["limit"], rec["clearance_margin"] or float("nan"),
              clr["m_clear_dense"] if clr["m_clear_dense"] is not None else float("nan"),
              ",".join(labs)), flush=True)

    print("== E1.5: three motion models, certification MC, dense clearance ==", flush=True)
    for rho0, tl, arm in BASE_WITNESSES:
        spawn = make_spawn(rho0, tl * V_CLOSE)
        w = log_ctrl(make_contract() if arm == "C" else make_pd())
        rec = rollout_unified(pe, spawn, w, fin, r_lane=RL, r_body=RB)
        record("1B", rho0, tl, arm, rec, np.asarray(w.log, float), spawn)

    from shepherd.scripts.c1_controller_gap import cem_O, ws1_best_simple, ws2_band_edge
    for rho0, tl, wname, sbase in O_WITNESSES:
        spawn = make_spawn(rho0, tl * V_CLOSE)
        n_dep = int(round(E.tau_deploy / DT)); ctrl_len = int(round(tl / DT)) + n_dep + 2
        warm = (ws1_best_simple(pe, spawn, fin, RL, RB, 6) if wname == "WS1" else ws2_band_edge(spawn, 6))
        seed = 401_000_000 + int(rho0 * 100) * 1000 + int(tl * 100) + sbase
        _, kn = cem_O(pe, spawn, fin, RL, RB, warm, seed, ctrl_len, 20, 12, 6)
        seq = knots_to_seq(kn, ctrl_len)
        rec = rollout_unified(pe, spawn, seq_ctrl(seq), fin, r_lane=RL, r_body=RB)
        record("1C", rho0, tl, "O-" + wname, rec, seq, spawn,
               extra={"knots": np.asarray(kn, float).tolist(), "cem_seed": seed,
                      "ctrl_len": ctrl_len, "note": "re-derived with the Phase 1C CEM seed "
                      "(original artifact was not stored); deterministic reproduction, "
                      "NOT an exact replay of the archived witness"})

    out = {"meta": {"phase": "1E_dynamic_judge_audit", "commit": commit, "config_sha": cfg_hash,
                    "n_cert": a.n_cert, "cert_seeds": list(CERT_SEEDS), "theta": pe.theta,
                    "eps_disp": EPS_DISP, "substeps": SUBSTEPS,
                    "models": "static | cv_swept | actual (fixed-path REMASK; no adversarial replan)",
                    "caveat": "the attacker sample bank is not replanned against moving limiters; "
                              "`actual` is an authoritative-side remask, not a full dynamic certificate"},
           "rows": rows}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, "and", str(art_dir), flush=True)


if __name__ == "__main__":
    main()
