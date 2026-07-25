"""C-1 Phase 1D — E0 (path unification + baseline containment / resolution) and
E1 (Tier4_viable gate + witness rescore).   Plan: URP/c1_phase1d_plan_2026-07-24.md

E0  1. rollout_unified = ONE rollout/judge path for baseline (closed-loop) AND
       open-loop sequences, with (a) the angular gap measured in the correct
       (y,z) plane, (b) limiter velocity read from obs (not finite differences).
       Parity-checked field-by-field against c1_response_probe.response_rollout.
    2. Containment / resolution: replay the C/P baseline action log at
       K in {6,12,16,H} and compare state trajectory, fire step, tier, capture
       margin, clearance margin, terminal velocity, exact replay, fresh CRN.
       Gate: K=H must reproduce the baseline exactly. No optimization before this.

E1  Tier4_viable = Tier4_geom
      /\ (V-a) ||v_lim||*tau_deploy <= eps*r_kill                      (eps=0.1)
      /\ (V-b) |v_soft_swept - v_soft_static| <= delta                (delta=0.05)
      /\ (V-c) m_stop = m_clear - max(0,v_in)^2/(2 a_max) >= 0
    (V-b) is an AUDIT-ONLY recomputation: the frozen judge treats limiters as
    STATIC points over tau (viability._feasible_limiter / _limiter_mask_from_paths),
    so a fast-moving ring gets a mis-placed no-go volume.  Here the SAME reachable
    union is re-evaluated with limiters swept at their measured velocity.
    env.py / frozen blobs are NOT touched.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (response_rollout, make_spawn, make_contract,
    make_pd, make_hold, _radial, THETA, N_LIM, R_BODY, M_SAFETY, PRIMARY, X_FIRE, V_CLOSE,
    RHO_STAR, S_V, S_P, DT)
from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, make_finisher_fn,
    knots_to_seq, A_MAX, ATT_P0)
from shepherd.scripts.c1_a1_connectivity import _override, a1_rollout
from shepherd.scripts.c1_g3_deploy import _perp_to_axis
from shepherd.game import viability as V

EPS_JUDGE = 0.10          # (V-a) allowed limiter displacement over tau, as a fraction of r_kill
DELTA_VS = 0.05           # (V-b) allowed static-vs-swept v_soft discrepancy
AUDIT_SEED = 1100         # fixed seed for the static/swept comparison (CRN: same union)
N_T = 24                  # viability substep count (matches _single_seg_paths/_seg_paths_turn)


# ------------------------------------------------------------------ E0: unified rollout
def seq_ctrl(seq):
    """Time-indexed OPEN-LOOP controller with the closed-loop calling convention,
    so that open-loop replay and closed-loop baselines share one rollout path."""
    seq = np.asarray(seq, float); st = {"t": 0}
    def fn(obs, flags):
        t = st["t"]; st["t"] += 1
        if t < len(seq): return [seq[t, i].astype(np.float32) for i in range(N_LIM)]
        return [np.zeros(3, np.float32) for _ in range(N_LIM)]
    fn.seq = seq
    return fn


def log_ctrl(inner):
    """Wrap a controller so the realized action sequence is recorded (full resolution)."""
    log = []
    def fn(obs, flags):
        a = inner(obs, flags); log.append(np.stack([np.asarray(x, float) for x in a])); return a
    fn.log = log
    return fn


def rollout_unified(pe, spawn, ctrl_fn, fin, *, r_lane, r_body, seed=1100):
    """Single rollout + judge path.  Tier logic identical to response_rollout /
    a1_rollout; adds obs-derived limiter velocity, the correct (y,z) angular gap,
    and the fire-instant state needed by the E1 audit."""
    ad = pe.ad; E = ad.env; n_dep = int(round(E.tau_deploy / DT)); th = pe.theta
    obs_d, _ = ad.reset_to(dict(spawn), seed=int(seed)); obs = obs_d[ad.limiter_ids[0]]
    vs, pf, lim_hist, vel_hist, obs_log, flags = [], [], [], [], [], {}
    fire_step = fin_apex = fin_axis = axial_len = pen_at = None
    steps = 0; captured = clean = False
    while True:
        o = np.asarray(obs, float)
        vs.append(float(o[-3])); pf.append(float(o[-1]))
        lim_hist.append(np.stack([o[9 * i:9 * i + 3] for i in range(N_LIM)]))
        vel_hist.append(np.stack([o[9 * i + 3:9 * i + 6] for i in range(N_LIM)]))
        obs_log.append(o)
        lim = ctrl_fn(obs, flags)
        live = {lid: np.asarray(lim[i], np.float32) for i, lid in enumerate(ad.limiter_ids)}
        fa = fin(obs, flags); live[ad.finisher_id] = np.asarray(fa, np.float32)
        if fire_step is None and len(fa) >= 4 and fa[3] > 0.5:
            fire_step = steps
            fin_apex = o[36:39]; fin_axis = o[42:45]
            fin_axis = fin_axis / (np.linalg.norm(fin_axis) + 1e-12)
            axial_len = float((o[ATT_P0:ATT_P0 + 3] - fin_apex) @ fin_axis)
        r = ad.step(live)
        if pen_at is None and bool(r.flags.get("penetrated")): pen_at = steps
        obs = r.obs[ad.limiter_ids[0]]; flags = r.flags; steps += 1
        if r.done or (fire_step is not None and steps > fire_step + n_dep + 1):
            captured = bool(r.flags.get("captured"))
            clean = bool(any(c.get("clean") for c in r.flags.get("fire_chains", []))); break
    vs_a, pf_a = np.asarray(vs), np.asarray(pf)
    el = np.isfinite(vs_a) & np.isfinite(pf_a) & (pf_a > 0) & (vs_a >= th)
    M_cap = (float(np.max(np.minimum((vs_a[el] - th) / S_V, pf_a[el] / S_P))) if el.any() else float("-inf"))
    m_clear = float("inf"); m_clear_def = False
    if fire_step is not None and axial_len is not None:
        for t in range(fire_step, min(fire_step + n_dep + 1, len(lim_hist))):
            for i in range(N_LIM):
                ax, perp = _perp_to_axis(lim_hist[t][i], fin_apex, fin_axis)
                if 0.0 <= ax <= axial_len:
                    m_clear = min(m_clear, perp - r_lane - r_body); m_clear_def = True
    E_cap = bool(el.any()); E_lane = bool(m_clear_def and m_clear >= 0.0)
    E_safe = bool(E_cap and E_lane and pen_at is None)
    tier = 0
    if el.any(): tier = 1
    if E_cap and not E_lane: tier = 2
    if E_lane and not E_cap: tier = 3
    if E_safe: tier = 4
    if E_safe and captured and clean: tier = 5
    t_ref = fire_step if fire_step is not None else (int(np.argmax(vs_a)) if len(vs_a) else 0)
    t_ref = min(t_ref, len(lim_hist) - 1)
    perps = [_radial(lim_hist[t_ref][i])[1] for i in range(N_LIM)]
    rad_err = float(np.mean([abs(p - RHO_STAR) for p in perps]))
    # CORRECT plane: the perpendicular component lives in (y,z); pv[0] is ~0 by
    # construction, so response_rollout's arctan2(pv[1], pv[0]) is degenerate.
    angs = [float(np.arctan2(_radial(lim_hist[t_ref][i])[2][2], _radial(lim_hist[t_ref][i])[2][1]))
            for i in range(N_LIM)]
    a_s = np.sort(angs); gaps = np.diff(np.concatenate([a_s, [a_s[0] + 2 * np.pi]]))
    ang_gap = float(np.degrees(gaps.max()))
    v_ref = vel_hist[t_ref]
    return {"tier": tier, "fire_step": fire_step, "penetrated": bool(pen_at is not None),
            "capture_margin": (M_cap if np.isfinite(M_cap) else None),
            "clearance_margin": (m_clear if m_clear_def else None),
            "E_capture": E_cap, "E_lane": E_lane,
            "max_v_soft": float(vs_a[np.isfinite(vs_a)].max() if np.isfinite(vs_a).any() else 0.0),
            "terminal_radial_err": rad_err, "max_angular_gap_deg": ang_gap,
            "terminal_velocity": float(np.mean([np.linalg.norm(v_ref[i]) for i in range(N_LIM)])),
            "terminal_velocity_max": float(np.max([np.linalg.norm(v_ref[i]) for i in range(N_LIM)])),
            "safe": bool(E_safe), "steps": steps,
            "_t_ref": t_ref, "_lim": np.asarray(lim_hist), "_vel": np.asarray(vel_hist),
            "_obs": np.asarray(obs_log), "_fin_apex": fin_apex, "_fin_axis": fin_axis,
            "_axial_len": axial_len}


PARITY_FIELDS = ("tier", "fire_step", "penetrated", "capture_margin", "clearance_margin",
                 "E_capture", "E_lane", "max_v_soft", "terminal_radial_err", "safe")


def _cmp(a, b, tol=1e-12):
    if a is None or b is None: return a is None and b is None
    if isinstance(a, bool) or isinstance(a, (int, np.integer)): return a == b
    return abs(float(a) - float(b)) <= tol


# ------------------------------------------------------------------ E1: viability audit
def _block_times(T_b, tau):
    """Global time stamps for a union path block (mirrors _single_seg_paths and
    _seg_paths_turn: K segments x N_T substeps, each spanning [0, tau/K])."""
    if T_b == N_T: return np.linspace(0.0, tau, N_T)
    K = int(round(T_b / N_T)); h = tau / K
    return np.concatenate([j * h + np.linspace(0.0, h, N_T) for j in range(K)])


def _mask_swept(paths, L0, VL, kill_radius, tau):
    """_limiter_mask_from_paths with limiters SWEPT at constant velocity."""
    n, T, _ = paths.shape
    s = _block_times(T, tau)
    Lt = L0[None, :, :] + VL[None, :, :] * s[:, None, None]        # (T, nL, 3)
    d = np.linalg.norm(paths[:, :, None, :] - Lt[None, :, :, :], axis=3)
    return ~(d <= kill_radius).any(axis=(1, 2))


def viability_audit(pe, rec, *, r_lane, r_body):
    """(V-a)(V-b)(V-c) on the fire-instant state of a rollout record."""
    E = pe.ad.env
    out = {"applicable": rec["fire_step"] is not None}
    t = rec["_t_ref"]
    L0 = np.asarray(rec["_lim"][t], float); VL = np.asarray(rec["_vel"][t], float)
    tau = float(E.tau_deploy)
    speeds = np.linalg.norm(VL, axis=1)
    out["v_lim_max"] = float(speeds.max()); out["v_lim_mean"] = float(speeds.mean())
    out["disp_over_tau"] = float(speeds.max() * tau)
    out["Va_limit"] = float(EPS_JUDGE * E.kill_radius)
    out["Va_pass"] = bool(out["disp_over_tau"] <= out["Va_limit"])

    # (V-b) static vs swept v_soft on the SAME reachable union (CRN)
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]; fin9 = o[36:45]
    kw = E._vshot_kwargs(p_att, v_att, fin9)
    union = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                    n=E.n_samples, n_segments=max(int(E.n_segments), 2),
                                    seed=AUDIT_SEED, **kw)
    stat = V.eval_union_with_limiters(union, L0, E.kill_radius)
    masks = [_mask_swept(pb, L0, VL, E.kill_radius, tau) for pb in union.path_blocks]
    lim_feas = np.concatenate(masks, axis=0) if masks else np.ones(union.n_total, bool)
    swept = V._assemble(lim_feas & union.turn_feasible, union.caught, union.n_total,
                        union.judge, union.seed)
    out["v_soft_static"] = float(stat.v_shot_soft); out["v_soft_swept"] = float(swept.v_shot_soft)
    out["p_feas_static"] = float(stat.p_feasible); out["p_feas_swept"] = float(swept.p_feasible)
    out["dv_soft"] = float(abs(swept.v_shot_soft - stat.v_shot_soft))
    out["Vb_pass"] = bool(out["dv_soft"] <= DELTA_VS
                          and swept.v_shot_soft >= pe.theta and swept.p_feasible > 0.0)

    # (V-c) inward stopping margin in the CLEARANCE frame (finisher axis)
    m_clear = rec["clearance_margin"]
    if m_clear is None or rec["_fin_axis"] is None:
        out["Vc_pass"] = False; out["m_stop"] = None; out["v_in"] = None
    else:
        apex = np.asarray(rec["_fin_apex"], float); ax = np.asarray(rec["_fin_axis"], float)
        v_in = 0.0
        for i in range(N_LIM):
            rr = L0[i] - apex; perp_vec = rr - (rr @ ax) * ax
            n_perp = np.linalg.norm(perp_vec)
            if n_perp < 1e-9: continue
            rad_hat = perp_vec / n_perp
            v_in = max(v_in, float(-(VL[i] @ rad_hat)))       # >0 = moving INTO the lane
        out["v_in"] = float(v_in)
        out["m_stop"] = float(m_clear - max(0.0, v_in) ** 2 / (2.0 * A_MAX))
        out["Vc_pass"] = bool(out["m_stop"] >= 0.0)
    geom = bool(rec["tier"] >= 4 and not rec["penetrated"])
    out["tier4_geom"] = geom
    out["tier4_viable"] = bool(geom and out["Va_pass"] and out["Vb_pass"] and out["Vc_pass"])
    return out


# ------------------------------------------------------------------ drivers
def e0_cells():
    return [(3.2, 0.50, "C"), (4.0, 0.70, "C"), (4.0, 0.70, "P"), (5.0, 1.00, "P")]


def run_e0(pe, fin, RL, RB, ks=(6, 12, 16), out=None):
    res = {"meta": {"eps_judge": EPS_JUDGE, "delta_vs": DELTA_VS, "Ks": list(ks) + ["H"]},
           "parity": [], "containment": []}
    for rho0, tl, arm in e0_cells():
        spawn = make_spawn(rho0, tl * V_CLOSE)
        mk = make_contract if arm == "C" else make_pd
        # --- 1. path parity: rollout_unified vs response_rollout (same closed loop)
        old = response_rollout(pe, spawn, mk(), fin, r_lane=RL, r_body=RB)
        w = log_ctrl(mk()); new = rollout_unified(pe, spawn, w, fin, r_lane=RL, r_body=RB)
        diffs = [f for f in PARITY_FIELDS if not _cmp(old[f], new[f])]
        res["parity"].append({"rho0": rho0, "T": tl, "arm": arm, "match": not diffs,
                              "mismatched": diffs,
                              "angular_old": old["max_angular_gap_deg"],
                              "angular_new": round(new["max_angular_gap_deg"], 1)})
        print("  parity %.1f/%.2f %s -> %s%s" % (rho0, tl, arm,
              "MATCH" if not diffs else "MISMATCH ", diffs or ""), flush=True)
        A = np.asarray(w.log, float)                     # full-resolution baseline actions
        H = len(A)
        base_traj = new["_lim"]
        crn_base = rollout_unified(pe, spawn, log_ctrl(mk()), fin, r_lane=RL, r_body=RB, seed=1101)
        row = {"rho0": rho0, "T": tl, "arm": arm, "H": H,
               "baseline": {k: new[k] for k in PARITY_FIELDS},
               "baseline_term_v": new["terminal_velocity"], "baseline_crn_tier": crn_base["tier"],
               "replays": []}
        # --- 2. containment / resolution
        for K in list(ks) + [H]:
            if K >= H:
                seq = A; label = "H"
            else:
                seq = knots_to_seq(A[np.linspace(0, H - 1, K).astype(int)], H); label = str(K)
            rep = rollout_unified(pe, spawn, seq_ctrl(seq), fin, r_lane=RL, r_body=RB)
            crn = rollout_unified(pe, spawn, seq_ctrl(seq), fin, r_lane=RL, r_body=RB, seed=1101)
            n = min(len(base_traj), len(rep["_lim"]))
            l2 = float(np.sqrt(((base_traj[:n] - rep["_lim"][:n]) ** 2).sum(axis=2).mean()))
            same = ([f for f in PARITY_FIELDS if not _cmp(new[f], rep[f], 1e-9)] == []
                    and _cmp(new["terminal_velocity"], rep["terminal_velocity"], 1e-9)
                    and crn["tier"] == crn_base["tier"])
            rep_row = {"K": label, "traj_l2": l2, "exact": bool(same and l2 <= 1e-9),
                       "tier": rep["tier"], "fire_step": rep["fire_step"], "safe": rep["safe"],
                       "cap": rep["capture_margin"], "clr": rep["clearance_margin"],
                       "term_v": rep["terminal_velocity"], "crn_tier": crn["tier"],
                       "mismatched": [f for f in PARITY_FIELDS if not _cmp(new[f], rep[f], 1e-9)]}
            row["replays"].append(rep_row)
            print("    K=%-3s l2=%.3e tier=%d(base %d) safe=%s exact=%s" % (
                label, l2, rep["tier"], new["tier"], rep["safe"], rep_row["exact"]), flush=True)
        res["containment"].append(row)
    if out:
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(out).write_text(json.dumps(res, indent=1, default=float))
        print("wrote", out, flush=True)
    return res


def run_e1(pe, fin, RL, RB, out=None):
    """Rescore the archived Tier-4 witnesses under Tier4_viable.
    Baselines: rerun the arm (deterministic).  Arm O: re-derive the CEM knots with
    the SAME seeds as Phase 1C (deterministic) for the three Tier-4 witnesses."""
    from shepherd.scripts.c1_controller_gap import cem_O, ws1_best_simple, ws2_band_edge, T_LB_set
    rows = []
    base = [(2.8, 0.30, "C"), (3.2, 0.50, "C"), (3.2, 0.70, "P"), (4.0, 0.70, "C"),
            (4.0, 0.70, "P"), (5.0, 1.00, "P")]
    for rho0, tl, arm in base:
        spawn = make_spawn(rho0, tl * V_CLOSE)
        mk = make_contract if arm == "C" else make_pd
        rec = rollout_unified(pe, spawn, mk(), fin, r_lane=RL, r_body=RB)
        aud = viability_audit(pe, rec, r_lane=RL, r_body=RB)
        rows.append({"src": "1B", "rho0": rho0, "T": tl, "arm": arm, "tier": rec["tier"],
                     "cap": rec["capture_margin"], "clr": rec["clearance_margin"],
                     "term_v": rec["terminal_velocity"], **aud})
        print("  1B %.1f/%.2f %s geom=%s viable=%s (v_lim %.2f, dv_soft %.3f, m_stop %s)" % (
            rho0, tl, arm, aud["tier4_geom"], aud["tier4_viable"], aud["v_lim_max"],
            aud["dv_soft"], None if aud["m_stop"] is None else round(aud["m_stop"], 3)), flush=True)
    O = [(3.2, 0.35, "WS1", 700), (3.2, 0.40, "WS1", 700), (4.0, 0.70, "WS2", 701)]
    for rho0, tl, wname, sbase in O:
        spawn = make_spawn(rho0, tl * V_CLOSE)
        n_dep = int(round(pe.ad.env.tau_deploy / DT)); ctrl_len = int(round(tl / DT)) + n_dep + 2
        warm = (ws1_best_simple(pe, spawn, fin, RL, RB, 6) if wname == "WS1"
                else ws2_band_edge(spawn, 6))
        seed = 401_000_000 + int(rho0 * 100) * 1000 + int(tl * 100) + sbase
        _, kn = cem_O(pe, spawn, fin, RL, RB, warm, seed, ctrl_len, 20, 12, 6)
        rec = rollout_unified(pe, spawn, seq_ctrl(knots_to_seq(kn, ctrl_len)), fin, r_lane=RL, r_body=RB)
        aud = viability_audit(pe, rec, r_lane=RL, r_body=RB)
        rows.append({"src": "1C", "rho0": rho0, "T": tl, "arm": "O-" + wname, "tier": rec["tier"],
                     "cap": rec["capture_margin"], "clr": rec["clearance_margin"],
                     "term_v": rec["terminal_velocity"], **aud})
        print("  1C %.1f/%.2f O-%s geom=%s viable=%s (v_lim %.2f, dv_soft %.3f, m_stop %s)" % (
            rho0, tl, wname, aud["tier4_geom"], aud["tier4_viable"], aud["v_lim_max"],
            aud["dv_soft"], None if aud["m_stop"] is None else round(aud["m_stop"], 3)), flush=True)
    res = {"meta": {"eps_judge": EPS_JUDGE, "delta_vs": DELTA_VS, "audit_seed": AUDIT_SEED,
                    "gate": "Tier4_viable = geom & Va(displacement) & Vb(swept v_soft) & Vc(m_stop)"},
           "rows": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]}
    if out:
        pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(out).write_text(json.dumps(res, indent=1, default=float))
        print("wrote", out, flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="E0,E1")
    ap.add_argument("--out-e0", default="results/c1_corridor/c1_containment.json")
    ap.add_argument("--out-e1", default="results/c1_corridor/c1_viable_rescore.json")
    a = ap.parse_args()
    env_cfg, m3, theta = _load("configs/m3a_a3e_p1.yaml"); pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    st = a.stage.split(",")
    if "E0" in st:
        print("== E0: path parity + baseline containment / resolution =="); run_e0(pe, fin, RL, RB, out=a.out_e0)
    if "E1" in st:
        print("== E1: Tier4_viable rescore =="); run_e1(pe, fin, RL, RB, out=a.out_e1)


if __name__ == "__main__":
    main()
