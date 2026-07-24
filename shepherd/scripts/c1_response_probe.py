"""C-1 Phase 1B — Response Envelope Probe (ratified spec 2026-07-22).

Measures the (rho0 initial radial spread) x (T_available response time) envelope
over which a role-agnostic limiter controller forms the deployment-safe kill-ring
(rho* = r_kill = 2.6) and fires Tier>=4 on exact replay, vs the analytic radial
rest-to-rest lower bound  T_radial_LB = 2*sqrt(|rho0-rho*|/a_max).

rho0 (initial spread) and rho* (terminal ring radius) are STRICTLY distinct.
Firing plane fixed x_fire ~ 14 m; D_lead = cue->firing-plane along-track distance;
T_available = D_lead / v_closing - tau_pipeline.

Arms (all role-agnostic; C/P use NO slot assignment -- each limiter contracts along
its own current radial direction to rho*):
  H  hold / coast            (reference: works only if rho0 ~ rho*)
  C  analytic contract+hold  (scheduled radial bang-bang to rho*, then PD hold)
  P  closed-loop PD           (PD to rho*-ring, radial-velocity damping)
  O  short-horizon optimizer  (CEM over limiter accel knots, role-agnostic)
MARL is NOT run here.  Sensor/visual, obs masking, curriculum = deferred (Phase 2).
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, _seq_lim, knots_to_seq,
                                                make_finisher_fn, _clip_norm, A_MAX, N_LIM, ATT_P0)
from shepherd.scripts.c1_g3_deploy import _perp_to_axis

RHO_STAR = 2.6            # terminal ring radius = r_kill (FIXED invariant)
X_FIRE = 14.0            # firing plane (attacker along-track position at fire)
X_RING = 8.0            # finisher-anchored ring axial position (nominal limiter x)
APEX = np.array([2.0, 0.0, 0.0]); AXIS = np.array([1.0, 0.0, 0.0])
V_CLOSE = 20.0; DT = 0.05
THETA = 0.9; R_BODY = 0.20; M_SAFETY = 0.20
PRIMARY = {"r_kill": 2.6, "r_net_dir": 2.1}
S_V, S_P = 0.1, 0.01
RNG = 400_000_000


def _radial(pos):
    """(axial along AXIS from APEX, perp radius) for a world position."""
    rr = np.asarray(pos, float) - APEX
    ax = float(rr @ AXIS); pv = rr - ax * AXIS
    return ax, float(np.linalg.norm(pv)), pv


def response_rollout(pe, spawn, ctrl_fn, fin, *, r_lane, r_body, seed=1100, trace=False):
    """Closed-loop reset_to rollout. Mirrors a1_rollout's tier logic exactly but drives
    the limiters with a closed-loop ctrl_fn(obs, flags) -> [accel3 x N_LIM]."""
    ad = pe.ad; E = ad.env; n_dep = int(round(E.tau_deploy / DT)); th = pe.theta
    obs_d, _ = ad.reset_to(dict(spawn), seed=int(seed)); obs = obs_d[ad.limiter_ids[0]]
    vs, pf, lim_hist, flags = [], [], [], {}
    fire_step = fin_apex = fin_axis = axial_len = pen_at = None
    steps = 0; captured = clean = False
    while True:
        vs.append(float(obs[-3])); pf.append(float(obs[-1]))
        lim_hist.append(np.stack([obs[9 * i:9 * i + 3] for i in range(N_LIM)]))
        lim = ctrl_fn(obs, flags)
        live = {lid: np.asarray(lim[i], np.float32) for i, lid in enumerate(ad.limiter_ids)}
        fa = fin(obs, flags); live[ad.finisher_id] = np.asarray(fa, np.float32)
        if fire_step is None and len(fa) >= 4 and fa[3] > 0.5:
            fire_step = steps; o = np.asarray(obs, float)
            fin_apex = o[36:39]; fin_axis = o[42:45]; fin_axis = fin_axis / (np.linalg.norm(fin_axis) + 1e-12)
            axial_len = float((o[ATT_P0:ATT_P0 + 3] - fin_apex) @ fin_axis)
        r = ad.step(live)
        if pen_at is None and bool(r.flags.get("penetrated")):
            pen_at = steps
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
    # terminal radial error / velocity at reference step
    t_ref = fire_step if fire_step is not None else (int(np.argmax(vs_a)) if len(vs_a) else 0)
    t_ref = min(t_ref, len(lim_hist) - 1)
    perps = [ _radial(lim_hist[t_ref][i])[1] for i in range(N_LIM) ]
    rad_err = float(np.mean([abs(p - RHO_STAR) for p in perps]))
    angs = []
    for i in range(N_LIM):
        _, _, pv = _radial(lim_hist[t_ref][i]); angs.append(float(np.arctan2(pv[1], pv[0])))
    a = np.sort(angs); gaps = np.diff(np.concatenate([a, [a[0] + 2 * np.pi]])); ang_gap = float(np.degrees(gaps.max()))
    rec = {"tier": tier, "fire_step": fire_step, "penetrated": bool(pen_at is not None),
           "capture_margin": (M_cap if np.isfinite(M_cap) else None),
           "clearance_margin": (m_clear if m_clear_def else None),
           "E_capture": E_cap, "E_lane": E_lane, "max_v_soft": float(vs_a[np.isfinite(vs_a)].max() if np.isfinite(vs_a).any() else 0.0),
           "terminal_radial_err": rad_err, "max_angular_gap_deg": ang_gap,
           "safe": bool(E_safe)}
    if trace: rec["trace"] = {"v_soft": [float(x) for x in vs], "lim": [h.tolist() for h in lim_hist]}
    return rec


# ---- role-agnostic controller arms (target = own current radial dir, rho* @ x=X_RING) ----
def _ring_target(p):
    """Ring point at x=X_RING, radius rho*, at limiter p's own current angle (role-agnostic)."""
    _, perp, pv = _radial(p)
    return np.array([X_RING, RHO_STAR * pv[1] / (perp + 1e-9), RHO_STAR * pv[2] / (perp + 1e-9)])

def make_hold():
    def fn(obs, flags): return [np.zeros(3, np.float32) for _ in range(N_LIM)]
    return fn

def make_pd(kp=25.0, kd=8.0):
    def fn(obs, flags):
        o = np.asarray(obs, float); acts = []
        for i in range(N_LIM):
            p = o[9 * i:9 * i + 3]; v = o[9 * i + 3:9 * i + 6]
            acts.append(_clip_norm(kp * (_ring_target(p) - p) + kd * (-v), A_MAX).astype(np.float32))
        return acts
    return fn

def make_contract(a_in=None):
    """Analytic: radial bang-bang inward to rho*, then PD hold. Role-agnostic."""
    st = {"t": 0}
    def fn(obs, flags):
        o = np.asarray(obs, float); acts = []
        for i in range(N_LIM):
            p = o[9 * i:9 * i + 3]; v = o[9 * i + 3:9 * i + 6]
            _, perp, pv = _radial(p); rad_hat = pv / (perp + 1e-9)
            err = perp - RHO_STAR                      # >0 need inward
            vr = float(v[1:] @ rad_hat[1:]) if perp > 1e-6 else 0.0
            # bang-bang: brake distance vr^2/(2 a). if remaining <= brake dist -> decel
            a_cmd = -A_MAX if err > (vr * vr) / (2 * A_MAX + 1e-9) else A_MAX
            a = a_cmd * rad_hat - 6.0 * (v - vr * rad_hat)   # radial bang-bang + tangential damping
            # near target -> PD hold
            if abs(err) < 0.15:
                tgt = np.array([X_RING, RHO_STAR * pv[1] / (perp + 1e-9), RHO_STAR * pv[2] / (perp + 1e-9)])
                a = 25.0 * (tgt - p) + 8.0 * (-v)
            acts.append(_clip_norm(a, A_MAX).astype(np.float32))
        st["t"] += 1
        return acts
    return fn


def arm_optimizer(pe, spawn, fin, r_lane, r_body, seed, *, pop=16, iters=10, t_open=18, knots=6):
    """Arm O: role-agnostic CEM over limiter accel knots via a1_rollout (open-loop seq)."""
    from shepherd.scripts.c1_a1_connectivity import a1_rollout
    rng = np.random.default_rng(seed)
    mu = np.zeros((knots, N_LIM, 3)); sig = np.full((knots, N_LIM, 3), 8.0); best = None; bsc = -1e9
    def scr(r):
        cm = r["capture_margin"] if r["capture_margin"] is not None else -1.0
        cl = r["clearance_margin"] if r["clearance_margin"] is not None else -3.0
        return r["tier"] * 100 + cm + min(cl, 0.0) - 5 * r["penetrated"]
    for _ in range(iters):
        cand = np.clip(mu + sig * rng.standard_normal((pop, knots, N_LIM, 3)), -A_MAX, A_MAX); cand[0] = mu
        scs = np.empty(pop)
        for c in range(pop):
            r = a1_rollout(pe, spawn, knots_to_seq(cand[c], t_open), fin, r_lane=r_lane, r_body=r_body)
            s = scr(r); scs[c] = s
            if s > bsc: bsc = s; best = (r, cand[c].copy())
        elg = np.argsort(scs)[-max(2, pop // 4):]; mu = cand[elg].mean(0); sig = cand[elg].std(0) * 1.1 + 0.5
        if best[0]["tier"] >= 4: break
    return best[0]


def make_spawn(rho0, D_lead, angles=None, axial=None):
    """Limiters at radius rho0 (own angles) at x=X_RING; attacker D_lead ahead of firing plane."""
    if angles is None: angles = np.array([np.pi / 2 * k for k in range(N_LIM)]) + 0.4
    if axial is None: axial = np.full(N_LIM, X_RING)
    L = np.array([[axial[i], rho0 * np.cos(angles[i]), rho0 * np.sin(angles[i])] for i in range(N_LIM)])
    att = np.array([X_FIRE + D_lead, 0.0, 0.0])
    return {"limiters": L, "limiter_v": np.zeros((N_LIM, 3)), "att_p": att, "att_v": np.array([-V_CLOSE, 0, 0])}


def classify(rec, T_avail, T_lb):
    if T_avail < T_lb: return "KINEMATIC_NEGATIVE_MARGIN"
    if rec["penetrated"]: return "PENETRATION"
    if rec["safe"]: return "OK"
    if rec["fire_step"] is not None and rec["clearance_margin"] is not None and rec["clearance_margin"] < 0:
        return "RADIAL_OVERSHOOT" if rec["terminal_radial_err"] < 0.5 else "CLEARANCE_VIOLATION"
    if rec["fire_step"] is None and rec["terminal_radial_err"] > 0.5: return "RADIAL_TOO_SLOW"
    if rec["max_angular_gap_deg"] > 150: return "ANGULAR_GAP"
    if not rec["E_capture"]: return "CAPTURE_MARGIN_FAIL"
    return "UNCLASSIFIED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rho0", default="2.8,3.2,4.0,5.0")
    ap.add_argument("--tlead", default="0.2,0.3,0.4,0.5,0.7,1.0")
    ap.add_argument("--tau", type=float, default=0.0, help="pipeline latency (scalar, sensitivity)")
    ap.add_argument("--arms", default="H,C,P,O")
    ap.add_argument("--pop", type=int, default=16); ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--out", default="results/c1_corridor/c1_response_envelope.json")
    a = ap.parse_args()
    env_cfg, m3, theta = _load("configs/m3a_a3e_p1.yaml"); pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    from shepherd.scripts.c1_a1_connectivity import _override
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    r_lane = PRIMARY["r_net_dir"]; r_body = R_BODY + M_SAFETY
    rho0s = [float(x) for x in a.rho0.split(",")]; tleads = [float(x) for x in a.tlead.split(",")]
    arms = a.arms.split(",")
    out = {"meta": {"phase": "1B_response_envelope", "rho_star": RHO_STAR, "x_fire": X_FIRE,
                    "v_closing": V_CLOSE, "a_max": A_MAX, "tau_pipeline": a.tau, "reset_seed": 1100,
                    "invariants": {"r_kill": 2.6, "r_net_dir": 2.1, "eta": 2.6 / 2.5, "theta": 0.9},
                    "analytic_LB": "T=2*sqrt(|rho0-rho_star|/a_max)"}, "cells": []}
    for rho0 in rho0s:
        T_lb = 2.0 * np.sqrt(abs(rho0 - RHO_STAR) / A_MAX)
        for tl in tleads:
            D_lead = tl * V_CLOSE; T_avail = D_lead / V_CLOSE - a.tau
            spawn = make_spawn(rho0, D_lead)
            cell = {"rho0": rho0, "T_lead": tl, "D_lead": D_lead, "T_available": round(T_avail, 3),
                    "T_radial_LB": round(float(T_lb), 3), "arms": {}}
            for arm in arms:
                if arm == "H": rec = response_rollout(pe, spawn, make_hold(), fin, r_lane=r_lane, r_body=r_body)
                elif arm == "C": rec = response_rollout(pe, spawn, make_contract(), fin, r_lane=r_lane, r_body=r_body)
                elif arm == "P": rec = response_rollout(pe, spawn, make_pd(), fin, r_lane=r_lane, r_body=r_body)
                elif arm == "O": rec = arm_optimizer(pe, spawn, fin, r_lane, r_body, RNG + int(rho0 * 100) * 100 + int(tl * 100), pop=a.pop, iters=a.iters)
                else: continue
                fm = classify(rec, T_avail, float(T_lb))
                cell["arms"][arm] = {"tier": rec["tier"], "safe": rec["safe"], "capture_margin": rec["capture_margin"],
                                     "clearance_margin": rec["clearance_margin"], "terminal_radial_err": round(rec["terminal_radial_err"], 3),
                                     "max_angular_gap_deg": round(rec["max_angular_gap_deg"], 1), "fire_step": rec["fire_step"],
                                     "penetrated": rec["penetrated"], "failure_mode": fm, "exact_replay": True}
                print("  rho0=%.1f Tlead=%.2f Tavail=%.2f LB=%.2f arm=%s -> tier=%d safe=%s fm=%s" % (
                    rho0, tl, T_avail, T_lb, arm, rec["tier"], rec["safe"], fm), flush=True)
            out["cells"].append(cell)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
