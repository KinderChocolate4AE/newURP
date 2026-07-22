"""C-1 A1 Dynamic Connectivity Probe (docs/09 (hhhh) PENDING; user directive
2026-07-21). Follows Move A0 (A0_TERMINAL_FEASIBLE_DYNAMIC_UNSOLVED): the A0
static-safe witness is treated as a POSITION-ONLY result; A1 asks whether that
safe-fire terminal is a real DYNAMIC state (A1a) and whether it BACKWARD-connects
to a nominal reset (A1b), under real dynamics + the frozen A2 closed loop --
BEFORE any MARL. A0 opened a legitimate terminal target for a connectivity test,
not a training permit.

Primary cell   r_kill 2.6 / r_net_dir 2.1 / theta 0.9 (fixed).
Secondary cell r_kill 2.6 / r_net_dir 2.0.

Full-state construction (A1a pt2): the pre-commit A-3e reset_to contract restores
limiter p/v + attacker p/v; the A2 attacker is memoryless GIVEN obs pre-commit, so
the restored full state is valid as long as we stay pre-commit up to the tested
step. Grounded lane clearance (swept net directional reach) + moving-limiter no-go
+ penetration are the real quantities; A1b auxiliary costs are search guidance
only, never the verdict.

Verdict quantities everywhere: capture margin (v_soft>=theta AND p_feas>0),
grounded lane clearance>=0, no penetration -- confirmed on EXACT REPLAY. torch-free.

RESULTS (2026-07-21, pre-container-reclaim):
  A1a = A1A_DYNAMICALLY_CONNECTED (both cells): terminal viable tier 4
        (cap 0.52, clr +0.1/+0.2, no penetration) AND all predecessors k=1..4
        connect (coast, matched AND unmatched velocity). The A0 witness is a real
        dynamic state, NOT positional-only. A0's dynamic failure was purely about
        REACHING it from nominal.
  A1b = PRELIMINARY only (not completed): standoff corrals from nominal reach
        <= tier 1 (ring4 too sparse to box; press2_block2 boxes v_soft~1 but never
        fires lane-safe). Bounded 2-arm CEM (U/S) did not connect at small budget;
        cause = no eligible fire (p_feas=0 over-box) + radial off-band. NEEDS a
        proper run.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, _seq_lim,
                                                knots_to_seq, make_finisher_fn,
                                                A_MAX, N_LIM, ATT_P0, ATT_V0)
from shepherd.scripts.c1_g3_deploy import _perp_to_axis
from shepherd.game.viability import v_shot  # noqa: F401  (parity import)

PRIMARY = {"r_kill": 2.6, "r_net_dir": 2.1}
SECONDARY = {"r_kill": 2.6, "r_net_dir": 2.0}
THETA = 0.9
R_BODY = 0.20
M_SAFETY = 0.20
R_NET0 = 2.24
S_V, S_P = 0.1, 0.01
RNG_A1_BASE = 380_000_000
DT = 0.05


def _override(E, r_kill, r_net_dir):
    kr0, ch0 = E.kill_radius, E.cone_half_angle
    E.kill_radius = r_kill
    E.cone_half_angle = ch0 * (r_net_dir / R_NET0)
    return kr0, ch0


def a1_rollout(pe, spawn, lim_seq, fin, *, r_lane, r_body, seed=1100, trace=False):
    """reset_to(spawn) then run the open-loop limiter accel sequence + rule-guard
    finisher under real dynamics + A2 closed loop. Grounded lane clearance over the
    deployment window (net geom frozen at fire), capture margin, penetration,
    5-tier. Mirrors rollout_g3 but from a restored full state."""
    ad = pe.ad
    E = ad.env
    n_dep = int(round(E.tau_deploy / DT))
    th = pe.theta
    obs_d, _ = ad.reset_to(dict(spawn), seed=int(seed))
    obs = obs_d[ad.limiter_ids[0]]
    seqfn = _seq_lim(lim_seq)
    vs, pf, lim_hist, flags = [], [], [], {}
    fire_step = fin_apex = fin_axis = axial_len = None
    pen_at = None
    steps = 0
    captured = clean = False
    reset_elig = bool(obs[-3] >= th and obs[-1] > 0.0)
    obs_log = []
    while True:
        v_soft, p_feas = float(obs[-3]), float(obs[-1])
        vs.append(v_soft); pf.append(p_feas)
        lim_hist.append(np.stack([obs[9 * i:9 * i + 3] for i in range(N_LIM)]))
        if trace:
            obs_log.append(np.asarray(obs, float).tolist())
        lim = seqfn(obs, flags)
        live = {lid: np.asarray(lim[i], np.float32) for i, lid in enumerate(ad.limiter_ids)}
        fa = fin(obs, flags)
        live[ad.finisher_id] = np.asarray(fa, np.float32)
        if fire_step is None and len(fa) >= 4 and fa[3] > 0.5:
            fire_step = steps
            o = np.asarray(obs, float)
            fin_apex = o[36:39]
            fin_axis = o[42:45]; fin_axis = fin_axis / (np.linalg.norm(fin_axis) + 1e-12)
            axial_len = float((o[ATT_P0:ATT_P0 + 3] - fin_apex) @ fin_axis)
        r = ad.step(live)
        if pen_at is None and bool(r.flags.get("penetrated")):
            pen_at = steps
        obs = r.obs[ad.limiter_ids[0]]; flags = r.flags
        steps += 1
        if r.done or (fire_step is not None and steps > fire_step + n_dep + 1):
            captured = bool(r.flags.get("captured"))
            clean = bool(any(c.get("clean") for c in r.flags.get("fire_chains", [])))
            break
    vs_a, pf_a = np.asarray(vs), np.asarray(pf)
    el = np.isfinite(vs_a) & np.isfinite(pf_a) & (pf_a > 0) & (vs_a >= th)
    M_cap = (float(np.max(np.minimum((vs_a[el] - th) / S_V, pf_a[el] / S_P)))
             if el.any() else float("-inf"))
    m_clear = float("inf"); m_clear_def = False
    if fire_step is not None and axial_len is not None:
        for t in range(fire_step, min(fire_step + n_dep + 1, len(lim_hist))):
            for i in range(N_LIM):
                ax, perp = _perp_to_axis(lim_hist[t][i], fin_apex, fin_axis)
                if 0.0 <= ax <= axial_len:
                    m_clear = min(m_clear, perp - r_lane - r_body); m_clear_def = True
    E_capture = bool(el.any())
    E_lane = bool(m_clear_def and m_clear >= 0.0)
    E_safe = bool(E_capture and E_lane and pen_at is None)
    arrival = bool(captured and clean)
    tier = 0
    if el.any():
        tier = 1
    if E_capture and not E_lane:
        tier = 2
    if E_lane and not E_capture:
        tier = 3
    if E_safe:
        tier = 4
    if E_safe and arrival:
        tier = 5
    rec = {"len": steps, "fire_step": fire_step, "penetrated_at": pen_at,
           "E_capture": E_capture, "E_lane": E_lane, "E_safe": E_safe,
           "capture_margin": (M_cap if np.isfinite(M_cap) else None),
           "clearance_margin": (m_clear if m_clear_def else None),
           "penetrated": bool(pen_at is not None), "tier": tier,
           "max_v_soft": float(vs_a[np.isfinite(vs_a)].max() if np.isfinite(vs_a).any() else 0.0)}
    if trace:
        rec["trace"] = {"obs": obs_log, "v_soft": [float(x) for x in vs],
                        "p_feas": [float(x) for x in pf],
                        "lim": [h.tolist() for h in lim_hist]}
    return rec


def _zero_seq(k):
    return np.zeros((max(k, 1), N_LIM, 3), np.float32)


def _sc(rec):
    cm = rec["capture_margin"] if rec.get("capture_margin") is not None else -1.0
    cl = rec["clearance_margin"] if rec.get("clearance_margin") is not None else -3.0
    return cm + min(cl, 0.0)


def terminal_viability(pe, E, P, att_p, att_v, cell):
    """A1a step 1-2: is the A0 witness a viable DYNAMIC fire state? reset_to the box
    (zero velocity, holding) + attacker fixture state, fire, and check grounded
    clearance>=0, capture>0, no penetration on exact replay."""
    r_lane = cell["r_net_dir"]
    spawn = {"limiters": np.asarray(P, float), "limiter_v": np.zeros((N_LIM, 3)),
             "att_p": np.asarray(att_p, float), "att_v": np.asarray(att_v, float)}
    fin = make_finisher_fn(THETA)
    rec = a1_rollout(pe, spawn, _zero_seq(6), fin, r_lane=r_lane, r_body=R_BODY + M_SAFETY,
                     trace=True)
    return {"hold": {"tier": rec["tier"], "capture_margin": rec["capture_margin"],
                     "clearance_margin": rec["clearance_margin"],
                     "penetrated": rec["penetrated"], "fire_step": rec["fire_step"]},
            "viable": bool(rec["tier"] >= 4), "trace": rec.get("trace")}


def a1a_predecessor(pe, E, P, att_p, att_v, cell, k, rng, *, pop=24, iters=10, knots=3,
                    match_vel=True):
    """A1a step 3: does a PREDECESSOR k steps back flow into the safe-fire terminal
    under real dynamics + A2? Predecessor = box shifted to the attacker's k-step-back
    position. match_vel=True -> limiter velocity matched to the attacker (tracking
    neighborhood; coast is a near-trivial connect). match_vel=False -> ZERO limiter
    velocity (unmatched): the CEM must actively accelerate to catch + box the moving
    attacker. CEM a short accel control to arrive at safe-fire (tier>=4), grounded
    clearance>=0, no penetration; verify on exact replay. Short-circuits when the
    coast baseline already connects (tier>=4)."""
    r_lane = cell["r_net_dir"]
    n_dep = int(round(E.tau_deploy / DT))
    att_p_pred = att_p - att_v * k * DT
    P_pred = np.asarray(P, float) + (att_p_pred - att_p)
    vel = np.tile(att_v, (N_LIM, 1)) if match_vel else np.zeros((N_LIM, 3))
    spawn = {"limiters": P_pred, "limiter_v": vel, "att_p": att_p_pred, "att_v": att_v}
    fin = make_finisher_fn(THETA)
    H = k + n_dep + 2
    base = a1_rollout(pe, spawn, _zero_seq(H), fin, r_lane=r_lane, r_body=R_BODY + M_SAFETY,
                      trace=True)
    if base["tier"] >= 4:                                # coast already connects -> no CEM
        return {"k": k, "match_vel": match_vel, "coast_tier": base["tier"],
                "best_tier": base["tier"], "capture_margin": base["capture_margin"],
                "clearance_margin": base["clearance_margin"], "penetrated": base["penetrated"],
                "fire_step": base["fire_step"], "safe": True,
                "best_knots": np.zeros((knots, N_LIM, 3)).tolist(), "H": H,
                "trace": base.get("trace")}
    best = {"tier": base["tier"], "rec": base, "knots": np.zeros((knots, N_LIM, 3))}
    mu = np.zeros((knots, N_LIM, 3)); sig = np.full((knots, N_LIM, 3), 8.0)
    n_el = max(2, pop // 4)
    for _ in range(iters):
        cand = np.clip(mu + sig * rng.standard_normal((pop, knots, N_LIM, 3)), -A_MAX, A_MAX)
        cand[0] = 0.0
        tiers = np.empty(pop)
        for c in range(pop):
            rec = a1_rollout(pe, spawn, knots_to_seq(cand[c], H), fin,
                             r_lane=r_lane, r_body=R_BODY + M_SAFETY)
            cm = rec["capture_margin"] if rec["capture_margin"] is not None else -1.0
            cl = rec["clearance_margin"] if rec["clearance_margin"] is not None else -3.0
            tiers[c] = rec["tier"] * 100 + cm + min(cl, 0.0) - 5 * rec["penetrated"]
            if rec["tier"] > best["tier"] or (rec["tier"] == best["tier"]
                                              and cm + min(cl, 0) > _sc(best["rec"])):
                best = {"tier": rec["tier"], "rec": rec, "knots": cand[c].copy()}
        el = np.argsort(tiers)[-n_el:]
        mu = cand[el].mean(0); sig = cand[el].std(0) * 1.1 + 0.4
        if best["tier"] >= 4:
            break
    rep = a1_rollout(pe, spawn, knots_to_seq(best["knots"], H), fin,
                     r_lane=r_lane, r_body=R_BODY + M_SAFETY, trace=True)
    return {"k": k, "match_vel": match_vel, "coast_tier": base["tier"],
            "best_tier": rep["tier"], "capture_margin": rep["capture_margin"],
            "clearance_margin": rep["clearance_margin"], "penetrated": rep["penetrated"],
            "fire_step": rep["fire_step"],
            "safe": bool(rep["tier"] >= 4 and not rep["penetrated"]),
            "best_knots": best["knots"].tolist(), "H": H, "trace": rep.get("trace")}


def a1a(pe, E, P, att_p, att_v, cell):
    """A1a = terminal viability + predecessor connectivity (k=1..4, matched AND
    unmatched velocity). PASS if the terminal is viable AND at least one k connects
    on exact replay; else TERMINAL_POSITIONAL_ONLY."""
    kr0, ch0 = _override(E, cell["r_kill"], cell["r_net_dir"])
    tv = terminal_viability(pe, E, P, att_p, att_v, cell)
    preds = []
    winner = None                      # prefer a GENUINELY-controlled (unmatched) connect
    matched_winner = None
    for k in (1, 2, 3, 4):
        for mv in (False, True):
            rng = np.random.default_rng(RNG_A1_BASE + int(cell["r_net_dir"] * 100) * 1000
                                        + k * 10 + int(mv))
            pr = a1a_predecessor(pe, E, P, att_p, att_v, cell, k, rng, match_vel=mv)
            preds.append({kk: pr[kk] for kk in pr if kk != "trace"})
            print(f"  [A1a pred] cell({cell['r_kill']},{cell['r_net_dir']}) k={k} "
                  f"match_vel={mv}: coast={pr['coast_tier']} best={pr['best_tier']} "
                  f"cap={pr['capture_margin']} clr={pr['clearance_margin']} "
                  f"pen={pr['penetrated']} safe={pr['safe']}", flush=True)
            if pr["safe"]:
                if not mv and winner is None:
                    winner = pr
                elif mv and matched_winner is None:
                    matched_winner = pr
    if winner is None:
        winner = matched_winner
    E.kill_radius, E.cone_half_angle = kr0, ch0
    if tv["viable"] and winner is not None:
        verdict = "A1A_DYNAMICALLY_CONNECTED"
    elif tv["viable"]:
        verdict = "TERMINAL_POSITIONAL_ONLY"
    else:
        verdict = "TERMINAL_NOT_VIABLE"
    return {"cell": cell, "terminal_viability": tv["hold"], "viable": tv["viable"],
            "predecessors": preds, "verdict": verdict,
            "winner": ({k: winner[k] for k in winner if k != "trace"} if winner else None),
            "winner_trace": (winner.get("trace") if winner else None),
            "viability_trace": tv.get("trace")}


# ---------------------------------------------------------------- A1b --------
def _traj_metrics(pe, acts, fin, cell, seed=1100):
    """Grounded verdict quantities + auxiliary diagnostics for a nominal-reset
    trajectory (real dynamics + A2). Uses rollout_g3 (reset-based) under the current
    override. Returns tier + failure-cause diagnostics."""
    from shepherd.scripts.c1_g3_deploy import rollout_g3
    r = rollout_g3(pe, _seq_lim(acts), fin, seed, r_lane=cell["r_net_dir"],
                   r_body=R_BODY + M_SAFETY, trace=True)
    tr = r.get("trace", {})
    lim = np.asarray(tr.get("lim", []), float)
    vs = np.asarray(tr.get("v_soft", []), float)
    apex = np.array([2.0, 0.0, 0.0]); axis = np.array([1.0, 0.0, 0.0])
    radial_dev = ang_gap = np.nan
    if len(lim):
        t_ref = r["fire_step"] if r["fire_step"] is not None else (int(np.argmax(vs)) if len(vs) else 0)
        t_ref = min(t_ref, len(lim) - 1)
        perps, angs = [], []
        for i in range(N_LIM):
            rr = lim[t_ref][i] - apex; ax = float(rr @ axis); pv = rr - ax * axis
            perps.append(float(np.linalg.norm(pv)))
            angs.append(float(np.arctan2(pv[2], pv[1])))
        radial_dev = float(np.mean([abs(p - cell["r_kill"]) for p in perps]))
        a = np.sort(angs); gaps = np.diff(np.concatenate([a, [a[0] + 2 * np.pi]]))
        ang_gap = float(np.degrees(gaps.max()))
    return {"tier": r["tier"], "E_capture": r["E_capture"], "E_lane": r["E_lane"],
            "E_safe": r["E_safe"], "capture_margin": (r["M_capture"]
            if np.isfinite(r["M_capture"]) else None), "clearance_margin": r["m_clear"],
            "penetrated_at": r["penetrated_at"], "fire_step": r["fire_step"],
            "max_v_soft": r["max_v_soft"], "radial_dev": radial_dev,
            "max_angular_gap_deg": ang_gap}


def _aux_cost(m, cell):
    """Search-guidance auxiliary cost (arm S), NEVER the verdict: pull toward the
    standoff band (perp~r_kill), angular sealing (small max gap), and firing."""
    rd = m["radial_dev"] if not np.isnan(m["radial_dev"]) else 3.0
    ag = m["max_angular_gap_deg"] if not np.isnan(m["max_angular_gap_deg"]) else 360.0
    no_fire = 1.0 if m["fire_step"] is None else 0.0
    return 1.0 * rd + 0.01 * ag + 2.0 * no_fire


def a1b_arm(pe, E, cell, warm_knots, rng, *, arm, pop=8, iters=4, t_open=14, knots=6):
    """One A1b solver arm from the NOMINAL reset. U = plain tier score; S = tier +
    auxiliary guidance. Verdict = tier>=4 on exact replay (real quantities only)."""
    fin = make_finisher_fn(THETA)
    mu = (np.asarray(warm_knots, float) if warm_knots is not None
          else np.zeros((knots, N_LIM, 3)))
    knots = mu.shape[0]
    sig = np.full((knots, N_LIM, 3), 8.0)
    best = {"tier": -1, "m": None, "knots": mu.copy()}
    for _ in range(iters):
        cand = np.clip(mu + sig * rng.standard_normal((pop, knots, N_LIM, 3)), -A_MAX, A_MAX)
        cand[0] = mu
        score = np.empty(pop)
        for c in range(pop):
            m = _traj_metrics(pe, knots_to_seq(cand[c], t_open), fin, cell)
            cm = m["capture_margin"] if m["capture_margin"] is not None else -1.0
            cl = m["clearance_margin"] if m["clearance_margin"] is not None else -3.0
            base = m["tier"] * 100 + cm + min(cl, 0.0)
            score[c] = base - (_aux_cost(m, cell) if arm == "S" else 0.0)
            if m["tier"] > best["tier"] or (m["tier"] == best["tier"] and cm + min(cl, 0)
                                            > _sc({"capture_margin": best["m"]["capture_margin"]
                                                   if best["m"] else None,
                                                   "clearance_margin": best["m"]["clearance_margin"]
                                                   if best["m"] else None})):
                best = {"tier": m["tier"], "m": m, "knots": cand[c].copy()}
        el = np.argsort(score)[-max(2, pop // 4):]
        mu = cand[el].mean(0); sig = cand[el].std(0) * 1.1 + 0.5
        if best["tier"] >= 4:
            break
    m = _traj_metrics(pe, knots_to_seq(best["knots"], t_open), fin, cell)   # exact replay
    return {"arm": arm, "tier": m["tier"], "E_capture": m["E_capture"],
            "E_lane": m["E_lane"], "E_safe": m["E_safe"],
            "capture_margin": m["capture_margin"], "clearance_margin": m["clearance_margin"],
            "penetrated_at": m["penetrated_at"], "fire_step": m["fire_step"],
            "max_v_soft": m["max_v_soft"], "radial_dev": m["radial_dev"],
            "max_angular_gap_deg": m["max_angular_gap_deg"],
            "safe": bool(m["tier"] >= 4 and m["penetrated_at"] is None)}


def _decompose(res):
    """On failure, decompose the cause from the best arm's diagnostics."""
    causes = []
    if res["fire_step"] is None:
        if (res["max_v_soft"] or 0) < THETA:
            causes.append("angular/radial: never boxed to v_soft>=theta (no eligible fire)")
        else:
            causes.append("timing: v_soft>=theta reached but guard never fired eligible "
                          "(p_feas=0 over-box, or not simultaneous)")
    else:
        if res["E_capture"] and not res["E_lane"]:
            causes.append("post-fire: eligible fire but lane clearance<0 (limiters in net lane)")
        if res["penetrated_at"] is not None:
            causes.append(f"timing: penetration at step {res['penetrated_at']}")
    if res["radial_dev"] and res["radial_dev"] > 0.5:
        causes.append(f"radial: mean |perp - r_kill| = {res['radial_dev']:.2f} m (off the band)")
    if res["max_angular_gap_deg"] and res["max_angular_gap_deg"] > 130:
        causes.append(f"angular: max gap {res['max_angular_gap_deg']:.0f} deg (unsealed escape)")
    return causes or ["unclassified"]


def _radial_angular(lim, t_ref, cell):
    """Radial-band deviation + max angular gap of the limiter ring at t_ref (mirrors
    _traj_metrics; apex/axis frozen at the corridor mouth). Diagnostic only."""
    lim = np.asarray(lim, float)
    if not len(lim):
        return float("nan"), float("nan")
    apex = np.array([2.0, 0.0, 0.0]); axis = np.array([1.0, 0.0, 0.0])
    t_ref = min(int(t_ref), len(lim) - 1)
    perps, angs = [], []
    for i in range(N_LIM):
        rr = lim[t_ref][i] - apex; ax = float(rr @ axis); pv = rr - ax * axis
        perps.append(float(np.linalg.norm(pv))); angs.append(float(np.arctan2(pv[2], pv[1])))
    radial_dev = float(np.mean([abs(p - cell["r_kill"]) for p in perps]))
    a = np.sort(angs); gaps = np.diff(np.concatenate([a, [a[0] + 2 * np.pi]]))
    return radial_dev, float(np.degrees(gaps.max()))


def _ladder_rung_cem(pe, spawn, ctrl_len, cell, rng, *, pop, iters, knots=6, warm=None):
    """One backward-ladder rung: CEM a limiter accel (K knots over ctrl_len steps =
    H_back + n_dep + 2, so the limiters have time to contract-and-intercept AND deploy)
    from the reset_to(spawn) start to a Tier>=4 safe fire on exact replay (a1_rollout,
    real dynamics + A2). warm = previous rung's knots (curriculum warm-start). Returns
    the exact-replay diagnostics + the winning knots for the next rung."""
    r_lane = cell["r_net_dir"]
    fin = make_finisher_fn(THETA)
    mu = (np.asarray(warm, float).copy() if warm is not None
          else np.zeros((knots, N_LIM, 3)))
    knots = mu.shape[0]
    sig = np.full((knots, N_LIM, 3), 8.0)
    n_el = max(2, pop // 4)
    best = {"tier": -1, "rec": None, "knots": mu.copy()}
    for _ in range(iters):
        cand = np.clip(mu + sig * rng.standard_normal((pop, knots, N_LIM, 3)), -A_MAX, A_MAX)
        cand[0] = mu                                     # keep the warm/mean seed
        tiers = np.empty(pop)
        for c in range(pop):
            rec = a1_rollout(pe, spawn, knots_to_seq(cand[c], ctrl_len), fin,
                             r_lane=r_lane, r_body=R_BODY + M_SAFETY)
            cm = rec["capture_margin"] if rec["capture_margin"] is not None else -1.0
            cl = rec["clearance_margin"] if rec["clearance_margin"] is not None else -3.0
            tiers[c] = rec["tier"] * 100 + cm + min(cl, 0.0) - 5 * rec["penetrated"]
            if rec["tier"] > best["tier"] or (rec["tier"] == best["tier"]
                                              and cm + min(cl, 0) > _sc(best["rec"] or {})):
                best = {"tier": rec["tier"], "rec": rec, "knots": cand[c].copy()}
        el = np.argsort(tiers)[-n_el:]
        mu = cand[el].mean(0); sig = cand[el].std(0) * 1.1 + 0.4
        if best["tier"] >= 4:
            break
    rep = a1_rollout(pe, spawn, knots_to_seq(best["knots"], ctrl_len), fin,
                     r_lane=r_lane, r_body=R_BODY + M_SAFETY, trace=True)
    tr = rep.get("trace", {})
    vs = np.asarray(tr.get("v_soft", []), float)
    t_ref = (rep["fire_step"] if rep["fire_step"] is not None
             else (int(np.argmax(vs)) if len(vs) else 0))
    rad, ang = _radial_angular(tr.get("lim", []), t_ref, cell)
    return {"tier": rep["tier"], "capture_margin": rep["capture_margin"],
            "clearance_margin": rep["clearance_margin"], "penetrated_at": rep["penetrated_at"],
            "fire_step": rep["fire_step"], "max_v_soft": rep["max_v_soft"],
            "E_capture": rep["E_capture"], "E_lane": rep["E_lane"],
            "radial_dev": rad, "max_angular_gap_deg": ang,
            "safe": bool(rep["tier"] >= 4 and rep["penetrated_at"] is None),
            "_knots": best["knots"]}


def a1b_ladder(pe, E, cell, P, att_p_term, att_v, *, pop, iters, horizons):
    """Backward horizon ladder. Each rung resets (reset_to) to a limiter start that
    interpolates from the BOXED predecessor (spread_frac f=0: the box formation shifted
    to the attacker's H-step-back position -- the a1a-trivial connect) to the NOMINAL
    deployment spread (f=1: limiters at the seed-1100 launch spread), at an increasing
    horizon H. f ramps with the rung, so the last rung is the full nominal problem via
    reset_to. CEM each rung, warm-starting from the previous. The FIRST rung that fails
    Tier>=4 isolates the horizon/spread where the nominal connect breaks.

    Diagnostic localizer only: the flat 2-arm a1b (rollout_g3 nominal reset) stays the
    authoritative connect verdict; reset_to injects synthetic spread starts here, which
    rollout_g3 cannot."""
    kr0, ch0 = _override(E, cell["r_kill"], cell["r_net_dir"])
    P = np.asarray(P, float)
    att_p_term = np.asarray(att_p_term, float); att_v = np.asarray(att_v, float)
    obs_d, _ = pe.ad.reset(seed=1100)                    # nominal deployment spread target
    obs = np.asarray(obs_d[pe.ad.limiter_ids[0]], float)
    L_nom = np.stack([obs[9 * i:9 * i + 3] for i in range(N_LIM)])
    V_nom = np.stack([obs[9 * i + 3:9 * i + 6] for i in range(N_LIM)])
    n_dep = int(round(E.tau_deploy / DT))
    horizons = list(horizons)
    R = len(horizons)
    warm = None; rungs = []; break_at = None
    for r, H in enumerate(horizons):
        f = (r / (R - 1)) if R > 1 else 1.0
        att_p_r = att_p_term - att_v * H * DT             # attacker H steps back
        P_pred = P + (att_p_r - att_p_term)               # box formation, shifted back
        L_start = (1.0 - f) * P_pred + f * L_nom          # box -> nominal spread
        V_start = f * V_nom                               # 0 (boxed) -> nominal vel
        spawn = {"limiters": L_start, "limiter_v": V_start,
                 "att_p": att_p_r, "att_v": att_v}
        rng = np.random.default_rng(RNG_A1_BASE + 900_000
                                    + int(cell["r_net_dir"] * 100) * 100 + r)
        ctrl_len = H + n_dep + 2                          # approach H + deploy/fire n_dep
        res = _ladder_rung_cem(pe, spawn, ctrl_len, cell, rng, pop=pop, iters=iters, warm=warm)
        warm = res.pop("_knots")
        res.update({"rung": r, "H": H, "spread_frac": round(f, 3),
                    "att_x": float(att_p_r[0])})
        rungs.append(res)
        print(f"  [A1b ladder r{r}] H={H} f={f:.2f} att_x={att_p_r[0]:.0f}: "
              f"tier={res['tier']} cap={res['capture_margin']} clr={res['clearance_margin']} "
              f"fire={res['fire_step']} radDev={res['radial_dev']:.2f} "
              f"safe={res['safe']}", flush=True)
        if not res["safe"] and break_at is None:
            break_at = {"rung": r, "H": H, "spread_frac": round(f, 3),
                        "att_x": float(att_p_r[0]), "causes": _decompose(res)}
    E.kill_radius, E.cone_half_angle = kr0, ch0
    return {"rungs": rungs, "break_at": break_at, "connected_all_rungs": break_at is None,
            "horizons": horizons,
            "note": ("f=0 boxed predecessor (a1a-trivial) -> f=1 nominal deployment spread; "
                     "first failing rung localizes the backward horizon/spread of the "
                     "barrier. Flat 2-arm a1b (rollout_g3) is the authoritative nominal "
                     "verdict; ladder uses reset_to synthetic spreads as a diagnostic.")}


def a1b(pe, E, cell, P=None, att_p=None, att_v=None, *, pop=24, iters=15, t_open=18,
        ladder=False, horizons=(2, 4, 6, 8, 10)):
    """A1b backward continuation from NOMINAL, warm-started NOT from the E1 crowd but
    from a standoff-boxing approach, two arms U/S. Discovery = one nominal-seed
    Tier>=4 exact replay -> only then open bank/BC/curriculum/MARL. Optional backward
    horizon ladder (needs P/att_p/att_v) localizes where the connect breaks."""
    from shepherd.scripts.c1_corridor_probe import make_corral_fn, _fit_knots
    kr0, ch0 = _override(E, cell["r_kill"], cell["r_net_dir"])
    fin = make_finisher_fn(THETA)
    warm_p = {"pattern": "press2_block2", "d_lead": 0.0, "d_back": 1.0,
              "R0": cell["r_kill"], "R1": cell["r_kill"], "t_shrink0": 0.0,
              "shrink_len": 1.0, "phi0": 0.0, "kp": 8.0, "kd": 5.0, "vmatch": 1.0}
    wrec = pe.rollout(make_corral_fn(warm_p), fin, 1100, trace=True)
    warm_knots = _fit_knots(np.asarray(wrec["trace"]["acts"], float), 6)
    arms = []
    for arm in ("U", "S"):
        rng = np.random.default_rng(RNG_A1_BASE + 700_000 + int(cell["r_net_dir"] * 100)
                                    + (0 if arm == "U" else 1))
        a = a1b_arm(pe, E, cell, warm_knots, rng, arm=arm,
                    pop=pop, iters=iters, t_open=t_open)
        arms.append(a)
        print(f"  [A1b arm {arm}] cell({cell['r_kill']},{cell['r_net_dir']}): tier={a['tier']} "
              f"E_cap={a['E_capture']} E_lane={a['E_lane']} cap={a['capture_margin']} "
              f"clr={a['clearance_margin']} fire={a['fire_step']} radDev={a['radial_dev']:.2f} "
              f"angGap={a['max_angular_gap_deg']:.0f} safe={a['safe']}", flush=True)
    E.kill_radius, E.cone_half_angle = kr0, ch0
    best = max(arms, key=lambda x: x["tier"])
    if best["safe"]:
        verdict = "A1B_CONNECTED_TO_NOMINAL"
        note = ("a role-agnostic search (warm-started from the standoff terminal, NOT the "
                "E1 crowd) connects the nominal reset to a Tier>=4 safe fire on exact "
                "replay -> NOW open corridor bank / BC / backward curriculum / MARL.")
        causes = []
    else:
        verdict = "A1B_NOT_CONNECTED_AT_BUDGET"
        causes = _decompose(best)
        note = ("no arm reaches Tier>=4 from nominal at this search budget -> the global "
                "connect is the hard part (A1a local viability holds). Failure decomposed "
                "below; the backward curriculum + MARL is the justified next step, but is "
                "NOT opened until a Tier>=4 exact replay appears (user gate).")
    out = {"cell": cell, "arms": arms, "verdict": verdict, "note": note,
           "failure_causes": causes, "warm": "press2_block2 standoff (not E1 crowd)",
           "budget": {"pop": pop, "iters": iters, "t_open": t_open}}
    if ladder and P is not None:
        print(f"  [A1b ladder] cell({cell['r_kill']},{cell['r_net_dir']}) "
              f"horizons={list(horizons)}")
        out["ladder"] = a1b_ladder(pe, E, cell, P, att_p, att_v,
                                   pop=pop, iters=iters, horizons=horizons)
        ba = out["ladder"]["break_at"]
        out["ladder_summary"] = ("all rungs connected" if ba is None
                                 else f"breaks at rung {ba['rung']} (H={ba['H']}, "
                                      f"f={ba['spread_frac']}, att_x={ba['att_x']:.0f})")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="a1a", choices=("a1a", "a1b", "both"))
    ap.add_argument("--a0", default="results/c1_corridor/c1_moveA0.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_a1.json")
    ap.add_argument("--pop", type=int, default=24, help="CEM population (a1b arms + ladder)")
    ap.add_argument("--iters", type=int, default=15, help="CEM iterations")
    ap.add_argument("--t_open", type=int, default=18, help="a1b control horizon (steps, ~16-24)")
    ap.add_argument("--ladder", action="store_true",
                    help="run the backward horizon ladder diagnostic (a1b)")
    ap.add_argument("--horizons", default="2,4,6,8,10",
                    help="comma-separated ladder rung horizons (steps back from terminal)")
    a = ap.parse_args()
    env_cfg, m3, theta = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    d = json.load(open(a.a0))
    fix = json.load(open("/tmp/c1_fire_fixture.json"))
    att_p = np.asarray(fix["att_p"], float); att_v = np.asarray(fix["att_v"], float)
    out = {"meta": {"primary": PRIMARY, "secondary": SECONDARY, "theta": THETA,
                    "r_body": R_BODY, "m_safety": M_SAFETY, "rng_base": RNG_A1_BASE,
                    "carried_verdict": "A0_TERMINAL_FEASIBLE_DYNAMIC_UNSOLVED",
                    "note": "reset_to = pre-commit A-3e restore (A2 memoryless given obs "
                    "pre-commit); verdict on exact replay: capture>0, grounded lane "
                    "clearance>=0, no penetration",
                    "a1b_run": {"pop": a.pop, "iters": a.iters, "t_open": a.t_open,
                                "ladder": a.ladder, "horizons": a.horizons}},
           "cells": []}
    for cell in (PRIMARY, SECONDARY):
        c0 = next(c for c in d["geometry_grid"]
                  if c["r_kill"] == cell["r_kill"] and c["r_net_dir"] == cell["r_net_dir"])
        P = np.asarray(c0["active_limiter_geometry"], float)
        entry = {"cell": cell}
        if a.stage in ("a1a", "both"):
            print(f"=== A1a cell ({cell['r_kill']},{cell['r_net_dir']}) ===")
            res = a1a(pe, E, P, att_p, att_v, cell)
            h = res["terminal_viability"]
            print(f"  viability: viable={res['viable']} tier={h['tier']} cap={h['capture_margin']} "
                  f"clr={h['clearance_margin']} pen={h['penetrated']}  VERDICT: {res['verdict']}")
            entry["a1a"] = res
        if a.stage in ("a1b", "both"):
            print(f"=== A1b cell ({cell['r_kill']},{cell['r_net_dir']}) ===")
            hz = tuple(int(x) for x in a.horizons.split(",") if x.strip())
            b = a1b(pe, E, cell, P, att_p, att_v, pop=a.pop, iters=a.iters,
                    t_open=a.t_open, ladder=a.ladder, horizons=hz)
            print(f"  VERDICT: {b['verdict']}  causes={b['failure_causes']}"
                  + (f"  | ladder: {b.get('ladder_summary', '')}" if a.ladder else ""))
            entry["a1b"] = b
        out["cells"].append(entry)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
