"""C-1 Move B -- capturability-PERSISTENCE counterfactual diagnostic (docs/09
(eeee); user directive 2026-07-21). History-dependent capture probe.

WHAT THIS IS NOT: it does NOT replace the Case-A instantaneous judge, and does
NOT touch E1. It is a COUNTERFACTUAL diagnostic evaluator. A new
history-dependent predicate is promoted to a formal-judge candidate ONLY if this
diagnostic comes back positive under the success gate below (user pt 7).

REFRAMED QUESTION (user): not "is the crowded eligible state captured in a
dynamic tube" but -- after the limiters START TO CLEAR the net lane (release),
does the attacker velocity/heading COMMITMENT built up by the prior shaping keep
capture achievable through the deployment window? The Case-A eligibility of seed
1100 is BOXING (p_feas collapses 0.97->1.6e-3 by t10; the net cone barely
matters). Boxing requires limiters IN the net lane => friendly-fire. The
history-dependent channel is the opposite: fire EARLIER, while limiters are still
spread (lane clearable), and let the committed velocity carry the attacker into
the sweeping net cone at the early crossing (net front reaches the attacker at
tau*~0.15 s, ~3 of 8 window steps -- so worst-case lateral evasion 1/2 a tau*^2
cannot clear the crossing-range cone).

EXPERIMENT (user spec):
 1. seed-1100 exact replay; save pre-fire snapshots t=6..10 + a replay manifest.
 2. per release time t_rel, run limiter BRANCHES: cem_tail / hold / radial /
    lateral_behind / greedy_clear.
 3. over the SAME deployment horizon, three evaluators:
      Case A      = the instantaneous judge (env v_soft, limiter-masked reachable
                    set at each step; static-cone endpoint at tau_deploy).
      Case B-phys = bounded-accel REACHABLE TUBE integrated from the release
                    (x_att, v_att), judged against the net_forward TIME-VARYING
                    swept cone, with the MOVING branch limiters applying the
                    kill-radius no-go per substep.
      Case B-A2   = the actual A2 scripted attacker's realized path (policy-
                    conditioned) under the same branch, same swept-cone judge.
 4. net envelope = net_forward swept cone (front = cum_travel(tau); grounded
    se3 cone half-angle, consistent with the env capture judge). Lane clearance
    uses the grounded directional reach R_LANE (G3 (aaaa)).
 5. per branch: p_cap_A, p_cap_B_phys, p_cap_B_A2, min friendly-clearance,
    safe-capture overlap duration, capture-margin persistence after release,
    penetration, fresh-CRN reproducibility.
 6. SUCCESS GATE: clearance>=0 AND Case-B capture>0 hold TOGETHER in the same
    branch/window (overlap>0). Case-B capture in the crowded state alone is NOT
    success (user pt 6).

READOUT (user):
  B-phys passes gate        -> strong history-dependent capture -> Move C
  only B-A2 passes gate     -> A2-specific dynamic commitment  -> Move C, limited generality
  neither / persistence < deployment time -> geometric wall supported -> Move A

Expression discipline (plan Section 18): never "impossible"; a negative is "tested
solvers found no release with simultaneous clear+capture / outside the tested
window". torch-free (numpy + env rollout).

Usage:  python -m shepherd.scripts.c1_persistence \
          --cem results/c1_corridor/cem_warm/c1_cem.json --seed 1100
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, _seq_lim,
                                                make_finisher_fn, A_MAX, N_LIM,
                                                ATT_P0, ATT_V0, FIN_P0)
from shepherd.scripts.c1_deconflict import make_arm

R_LANE = 2.24            # grounded directional net reach (G3 (aaaa)); friendly lane
R_BODY = 0.20            # limiter body/rotor clearance (PLACEHOLDER, human-lane)
RELEASE_TIMES = (6, 7, 8, 9, 10)
BRANCHES = ("cem_tail", "hold", "radial", "lateral_behind", "greedy_clear")
RNG_PERS_BASE = 360_000_000     # disjoint from CEM 330M / corral 331M / robust 332M / G3 340M
RNG_PERS_STRIDE = 100_000
DT_FINE = 0.01                  # capture-geometry sub-sampling (net front + attacker)


def pers_seed(t_rel: int, branch_idx: int, crn: int = 0) -> int:
    s = RNG_PERS_BASE + t_rel * RNG_PERS_STRIDE + branch_idx * 1000 + crn
    assert s < RNG_PERS_BASE + len(RELEASE_TIMES) * 11 * RNG_PERS_STRIDE
    return s


# --------------------------------------------------------------- net sweep ---
def net_sweep_profile(theta_deg=45, v0=60, m_g=35):
    """net_forward baseline swept profile: front axial travel and silhouette
    radius vs deployment time tau. Front = centroid cum_travel(tau). Silhouette
    radius r_sil(tau)=sqrt(S_NP/pi) is the deployed frontal reach (FLAGGED:
    flat-init over-states early S_NP, docs/n1) -- used ONLY as an optimistic
    capture-reach sensitivity, never for the primary (grounded-cone) judge.

    engage_dist = the travel at which net_radius is ANCHORED (N1 grounding). The
    net's reach BELOW engage_dist is the N1-flagged UNVALIDATED early-deployment
    regime -- the conservative capture bound requires the net-front travel at the
    capture instant to be >= engage_dist (net certified open)."""
    sys.path.insert(0, "prototypes")
    import net_forward as NF
    r = NF.simulate(theta_deg=theta_deg, v0=v0, m_block=m_g / 1000.0)
    t = np.asarray(r["t"], float)
    cum = np.asarray(r["cum_travel"], float)
    rad = np.sqrt(np.asarray(r["S_NP"], float) / np.pi)
    return {"t": t, "cum_travel": cum, "r_sil": rad,
            "net_radius_engage": float(r["net_radius"]),
            "engage_dist": float(getattr(NF, "ENGAGE_DIST", 20.0))}


def net_front(tau, prof):
    return float(np.interp(tau, prof["t"], prof["cum_travel"]))


def r_sil(tau, prof):
    return float(np.interp(tau, prof["t"], prof["r_sil"]))


# --------------------------------------------------------- branch limiters ---
def _greedy_clear(apex, u, axial_len):
    """Each limiter heads for the NEAREST exit of the net-lane tube
    ([0,axial_len] axial x R_LANE perp): radial-out, or axially past the apex /
    past the attacker, whichever exit is closest. Distinct from 'radial' (always
    perp) -- models the fastest physical lane vacate. obs-only, deterministic."""
    def arm(obs, flags):
        o = np.asarray(obs, float)
        acts = []
        for i in range(N_LIM):
            p = o[9 * i:9 * i + 3]
            r = p - apex
            ax = float(r @ u)
            perp_vec = r - ax * u
            perp = float(np.linalg.norm(perp_vec))
            perp_hat = perp_vec / (perp + 1e-9)
            d_rad = max(R_LANE - perp, 0.0)          # exit radially
            d_back = max(ax, 0.0)                     # exit behind apex
            d_fwd = max(axial_len - ax, 0.0)          # exit past attacker
            m = min(d_rad, d_back, d_fwd)
            if m == d_rad:
                d = perp_hat
            elif m == d_back:
                d = -u
            else:
                d = u
            acts.append((A_MAX * d).astype(np.float32))
        return acts
    return arm


def make_branch(kind, apex, u, axial_len, acts_cem, t_rel):
    """Return a lim_fn that plays the CEM tail for t<t_rel then the branch rule.
    cem_tail keeps the CEM open-loop tail throughout (no release)."""
    st = {"t": 0}
    if kind == "cem_tail":
        base = None
    elif kind == "greedy_clear":
        base = _greedy_clear(apex, u, axial_len)
    else:
        base = make_arm(kind, apex, u)               # hold / radial / lateral_behind

    def fn(obs, flags):
        t = st["t"]; st["t"] += 1
        if kind == "cem_tail" or t < t_rel:
            a = acts_cem[t] if t < len(acts_cem) else np.zeros((N_LIM, 3))
            return [np.asarray(a[i], np.float32) for i in range(N_LIM)]
        return base(obs, flags)
    return fn


# ------------------------------------------------------------- geometry -------
def _axial_perp(p, apex, u):
    r = np.asarray(p, float) - apex
    ax = float(r @ u)
    return ax, float(np.linalg.norm(r - ax * u))


def _swept_cone_capture(x0, v0, accels, apex, u, half, range_max, prof,
                        tau_grid, lim_win, dt, kill_radius, engage_dist):
    """History-dependent capture of a bounded-accel reachable tube against the
    net's swept cone, with MOVING limiter no-go.

    Per sample accel a: x(tau)=x0+v0 tau+1/2 a tau^2. Caught at the FIRST tau in
    the grid where (i) the net front cum_travel(tau) has reached the sample's
    axial range AND (ii) the sample sits inside the grounded se3 cone at that
    range (perp <= axial*tan(half), axial in [0,range_max]). Feasible iff over
    [0, capture-tau] the sample never enters a moving-limiter kill-radius
    (limiters linearly interpolated from the branch obs window). Boxed = all
    samples limiter-blocked (containment, not a clean net-shot).

    TWO bounds on the same capture (the load-bearing sensitivity):
      p_cap          OPTIMISTIC -- the cone model is trusted from launch (the net
                     is an effective catcher at ANY travel). Over-states capture in
                     the N1-flagged early-deployment regime.
      p_cap_engaged  CONSERVATIVE -- capture counts ONLY if the net-front travel at
                     the capture instant is >= engage_dist (net certified open).
    The truth is between; the gap IS the unvalidated net-temporal-deployment premise.

    Returns dict: p_cap, p_cap_engaged, p_feas, n_feas, boxed, caught mask,
    capture_tau + capture-travel per caught sample."""
    accels = np.asarray(accels, float)
    n = len(accels)
    tan_h = np.tan(half)
    caught = np.zeros(n, bool)
    caught_eng = np.zeros(n, bool)
    cap_tau = np.full(n, np.nan)
    cap_travel = np.full(n, np.nan)
    blocked = np.zeros(n, bool)
    for tau in tau_grid:
        x = x0[None, :] + v0[None, :] * tau + 0.5 * accels * tau ** 2   # (n,3)
        rel = x - apex[None, :]
        ax = rel @ u                                                    # (n,)
        perp = np.linalg.norm(rel - ax[:, None] * u[None, :], axis=1)
        front = net_front(tau, prof)
        # moving-limiter no-go at this tau (block feasibility going forward)
        k = tau / dt
        k0 = int(np.floor(k)); k1 = min(k0 + 1, len(lim_win) - 1)
        frac = k - k0
        L = (1 - frac) * lim_win[min(k0, len(lim_win) - 1)] + frac * lim_win[k1]  # (nlim,3)
        if kill_radius > 0:
            d = np.linalg.norm(x[:, None, :] - L[None, :, :], axis=2)   # (n,nlim)
            hit = (d <= kill_radius).any(axis=1) & ~caught & ~blocked
            blocked |= hit
        in_cone = (ax >= 0) & (ax <= range_max) & (perp <= ax * tan_h)
        reached = front >= ax                                           # net front at/past range
        newly = in_cone & reached & ~caught & ~blocked
        caught[newly] = True
        cap_tau[newly] = tau
        cap_travel[newly] = front
        caught_eng[newly] = front >= engage_dist                       # net certified open
    feasible = ~blocked
    nf = int(feasible.sum())
    p_cap = float(caught[feasible].mean()) if nf else 0.0
    p_cap_eng = float(caught_eng[feasible].mean()) if nf else 0.0
    ct = cap_travel[caught & feasible]
    return {"p_cap": p_cap, "p_cap_engaged": p_cap_eng, "p_feas": nf / n,
            "n_feas": nf, "boxed": bool(nf == 0), "caught": caught,
            "cap_tau": cap_tau,
            "median_capture_travel": float(np.median(ct)) if len(ct) else None}


def _realized_capture(att_win, apex, u, half, range_max, prof, dt, engage_dist):
    """Case B-A2: does the REALIZED attacker path (env obs over the window) enter
    the swept cone? Single policy-conditioned trajectory. Returns
    (caught_optimistic, caught_engaged, capture_tau)."""
    for k, p in enumerate(att_win):
        tau = k * dt
        ax, perp = _axial_perp(p, apex, u)
        front = net_front(tau, prof)
        if 0 <= ax <= range_max and perp <= ax * np.tan(half) and front >= ax:
            return 1, int(front >= engage_dist), tau
    return 0, 0, None


# ----------------------------------------------------------- one (t_rel,br) --
def eval_cell(pe, acts_cem, fin_theta, seed, t_rel, branch, branch_idx, prof,
              env, dt, n_dep, kill_radius, half, range_max, *, n_samp=2000):
    """Full metric bundle for one (release time, branch)."""
    engage_dist = prof["engage_dist"]
    # net geometry frozen at t_rel from an exact-replay pass
    base = pe.rollout(_seq_lim(acts_cem), make_finisher_fn(fin_theta), seed, trace=True)
    OBS = np.asarray(base["trace"]["obs"], float)
    o_r = OBS[min(t_rel, len(OBS) - 1)]
    apex = o_r[FIN_P0:FIN_P0 + 3].copy()
    u = o_r[42:45].copy(); u = u / (np.linalg.norm(u) + 1e-12)
    x_att0 = o_r[ATT_P0:ATT_P0 + 3].copy()
    v_att0 = o_r[ATT_V0:ATT_V0 + 3].copy()
    axial_len = float((x_att0 - apex) @ u)

    # branch rollout (CEM until t_rel, branch after) -- trace limiter+attacker path
    lim_fn = make_branch(branch, apex, u, axial_len, acts_cem, t_rel)
    br = pe.rollout(lim_fn, make_finisher_fn(fin_theta), seed, trace=True)
    BO = np.asarray(br["trace"]["obs"], float)
    vsoft = np.asarray(br["trace"]["v_soft"], float)
    pfeas = np.asarray(br["trace"]["p_feas"], float)
    w0, w1 = t_rel, min(t_rel + n_dep, len(BO) - 1)
    win = list(range(w0, w1 + 1))
    lim_win = np.stack([np.stack([BO[t][9 * i:9 * i + 3] for i in range(N_LIM)])
                        for t in win])                          # (W,nlim,3)
    att_win = np.stack([BO[t][ATT_P0:ATT_P0 + 3] for t in win])  # (W,3)

    # Case A: instantaneous judge at the release instant + trajectory over window
    p_cap_A = float(vsoft[t_rel]) if t_rel < len(vsoft) else 0.0
    eligible_A = bool(t_rel < len(vsoft) and vsoft[t_rel] >= fin_theta
                      and pfeas[t_rel] > 0.0)
    vsoft_win = [float(vsoft[t]) for t in win if t < len(vsoft)]

    # friendly clearance over the window (in-band limiters only, G3 convention)
    clear_t = []
    for k, t in enumerate(win):
        cl = np.inf
        for i in range(N_LIM):
            ax, perp = _axial_perp(lim_win[k][i], apex, u)
            if 0.0 <= ax <= axial_len:
                cl = min(cl, perp - R_LANE - R_BODY)
        clear_t.append(float(cl) if np.isfinite(cl) else np.inf)
    min_clear = float(min(clear_t))

    # Case B-phys reachable tube (grounded cone) + fresh-CRN repro
    tau_grid = np.arange(0.0, n_dep * dt + 1e-9, DT_FINE)
    from shepherd.game.viability import reachable_accels
    ac = reachable_accels(env.a_att_max, n_samp, pers_seed(t_rel, branch_idx, 0))
    B = _swept_cone_capture(x_att0, v_att0, ac, apex, u, half, range_max, prof,
                            tau_grid, lim_win, dt, kill_radius, engage_dist)
    ac2 = reachable_accels(env.a_att_max, n_samp, pers_seed(t_rel, branch_idx, 7))
    B2 = _swept_cone_capture(x_att0, v_att0, ac2, apex, u, half, range_max, prof,
                             tau_grid, lim_win, dt, kill_radius, engage_dist)
    crn_dp = abs(B["p_cap"] - B2["p_cap"])
    # NULL control: rotate v_att0 90 deg into the axis-perp plane (same speed) --
    # a NON-axis-committed attacker. If capture stays ~1 the metric is broken;
    # it should COLLAPSE, proving p_cap tracks the shaping's axis commitment.
    perp_dir = np.array([-u[1], u[0], 0.0]); nrm = np.linalg.norm(perp_dir)
    perp_dir = perp_dir / nrm if nrm > 1e-6 else np.array([0.0, 0.0, 1.0])
    v_null = float(np.linalg.norm(v_att0)) * perp_dir
    Bn = _swept_cone_capture(x_att0, v_null, ac, apex, u, half, range_max, prof,
                             tau_grid, lim_win, dt, kill_radius, engage_dist)

    # Case B-A2 realized path (optimistic + engaged)
    a2_caught, a2_eng, a2_tau = _realized_capture(att_win, apex, u, half,
                                                  range_max, prof, dt, engage_dist)

    # persistence: fire-DELAY sweep -- capture if the net is fired delta steps
    # after t_rel (limiters kept releasing). p_cap_B(delta) + clearance(delta).
    persistence = []
    for k, t in enumerate(win):
        xd = BO[t][ATT_P0:ATT_P0 + 3].copy()
        vd = BO[t][ATT_V0:ATT_V0 + 3].copy()
        lw = lim_win[k:]
        tg = np.arange(0.0, (len(lw) - 1) * dt + 1e-9, DT_FINE)
        acd = reachable_accels(env.a_att_max, n_samp, pers_seed(t_rel, branch_idx, 20 + k))
        Bd = _swept_cone_capture(xd, vd, acd, apex, u, half, range_max, prof,
                                 tg, lw, dt, kill_radius, engage_dist)
        persistence.append({"delay": k, "p_cap_B_phys": Bd["p_cap"],
                            "p_cap_engaged": Bd["p_cap_engaged"],
                            "p_feas": Bd["p_feas"], "clearance": clear_t[k],
                            "safe_opt": bool(clear_t[k] >= 0 and Bd["p_cap"] > 0),
                            "safe_eng": bool(clear_t[k] >= 0 and Bd["p_cap_engaged"] > 0)})
    overlap = int(sum(p["safe_opt"] for p in persistence))
    pers_alive = int(sum(1 for p in persistence if p["p_cap_B_phys"] > 0))

    # GATE = clearance MAINTAINED >=0 over the deployment window (min_clear>=0,
    # matching the G3 (bbbb) convention) AND Case-B capture>0. Split by the
    # net-temporal premise: optimistic (cone from launch) vs engaged (net open).
    gate_opt = bool(min_clear >= 0 and B["p_cap"] > 0)
    gate_eng = bool(min_clear >= 0 and B["p_cap_engaged"] > 0)
    return {
        "t_rel": t_rel, "branch": branch, "axial_len": axial_len,
        "att_offaxis0": float(_axial_perp(x_att0, apex, u)[1]),
        "att_speed0": float(np.linalg.norm(v_att0)),
        "p_cap_A": p_cap_A, "eligible_A": eligible_A, "vsoft_win": vsoft_win,
        "p_cap_B_phys": B["p_cap"], "p_cap_B_engaged": B["p_cap_engaged"],
        "p_cap_B_null": Bn["p_cap"], "median_capture_travel": B["median_capture_travel"],
        "p_feas_B": B["p_feas"], "boxed_B": B["boxed"],
        "p_cap_B_A2": float(a2_caught), "p_cap_B_A2_engaged": float(a2_eng),
        "a2_capture_tau": a2_tau,
        "min_friendly_clearance": min_clear, "clearance_t": clear_t,
        "safe_capture_overlap": overlap, "persistence_alive_steps": pers_alive,
        "persistence": persistence,
        "penetrated": bool(br["penetrated"]), "penetrated_at": br["penetrated_at"],
        "freshCRN_dpcap": float(crn_dp),
        "gate_B_phys_optimistic": gate_opt,
        "gate_B_phys_engaged": gate_eng,
        "gate_B_A2": bool(a2_caught and min_clear >= 0),
        "gate_B_A2_engaged": bool(a2_eng and min_clear >= 0),
    }


# ------------------------------------------------------------------ main -----
def run(cem_json, seed, cfg="configs/m3a_a3e_p1.yaml", n_samp=2000):
    env_cfg, m3, theta = _load(cfg)
    pe = ProbeEnv(env_cfg, m3)
    env = pe.ad.env
    dt = float(env_cfg.get("dt", 0.05))
    n_dep = int(round(env.tau_deploy / dt))
    kill_radius = float(getattr(env, "kill_radius", 2.0))
    half = float(env.cone_half_angle)
    range_max = float(getattr(env, "cone_range_max", 29.847))
    prof = net_sweep_profile()

    w = json.loads(pathlib.Path(cem_json).read_text())
    rec = next(x for x in w["draws"] if x["reset_seed"] == seed and x.get("best_acts"))
    acts = np.asarray(rec["best_acts"], float)

    # replay manifest + pre-fire snapshots t=6..10
    base = pe.rollout(_seq_lim(acts), make_finisher_fn(theta), seed, trace=True)
    OBS = np.asarray(base["trace"]["obs"], float)
    fire = base["fire_steps"][0] if base["fire_steps"] else base["first_eligible_step"]
    snaps = {}
    for t in RELEASE_TIMES:
        if t < len(OBS):
            o = OBS[t]
            snaps[str(t)] = {
                "limiters_p": [o[9 * i:9 * i + 3].tolist() for i in range(N_LIM)],
                "limiters_v": [o[9 * i + 3:9 * i + 6].tolist() for i in range(N_LIM)],
                "att_p": o[ATT_P0:ATT_P0 + 3].tolist(),
                "att_v": o[ATT_V0:ATT_V0 + 3].tolist(),
                "apex": o[FIN_P0:FIN_P0 + 3].tolist(), "nF": o[42:45].tolist(),
                "v_soft": float(base["trace"]["v_soft"][t]),
                "p_feas": float(base["trace"]["p_feas"][t])}
    manifest = {"seed": int(seed), "cem_json": cem_json,
                "acts_md5": hashlib.md5(acts.tobytes()).hexdigest(),
                "obs_md5": hashlib.md5(OBS.tobytes()).hexdigest(),
                "fire_step": int(fire) if fire is not None else None,
                "len": int(base["len"]), "n_dep": n_dep, "dt": dt,
                "env": {"tau_deploy": float(env.tau_deploy),
                        "a_att_max": float(env.a_att_max),
                        "kill_radius": kill_radius, "cone_half_angle": half,
                        "cone_range_max": range_max, "theta": theta,
                        "net_radius": float(getattr(env, "net_radius", 2.0))},
                "net_sweep": {"net_radius_engage": prof["net_radius_engage"],
                              "front@0.15s": net_front(0.15, prof),
                              "r_sil@0.15s": r_sil(0.15, prof),
                              "R_LANE": R_LANE, "R_BODY": R_BODY},
                "snapshots": snaps}

    grid = []
    for t_rel in RELEASE_TIMES:
        for bi, br in enumerate(BRANCHES):
            cell = eval_cell(pe, acts, theta, seed, t_rel, br, bi, prof, env, dt,
                             n_dep, kill_radius, half, range_max, n_samp=n_samp)
            grid.append(cell)

    # ---- readout (dual net-temporal bound) ----
    gate_opt = [c for c in grid if c["gate_B_phys_optimistic"]]
    gate_eng = [c for c in grid if c["gate_B_phys_engaged"]]
    gate_a2 = [c for c in grid if c["gate_B_A2_engaged"]]
    # null-control discrimination: axis-committed capture must beat the rotated null
    null_mean = float(np.mean([c["p_cap_B_null"] for c in grid]))
    cap_mean = float(np.mean([c["p_cap_B_phys"] for c in grid]))
    discriminates = bool(cap_mean - null_mean > 0.3)
    # travel at capture vs engage: is the capture in the unvalidated early regime?
    med_travels = [c["median_capture_travel"] for c in grid
                   if c["median_capture_travel"] is not None]
    med_capture_travel = float(np.median(med_travels)) if med_travels else None
    engage_dist = prof["engage_dist"]

    if gate_eng:
        verdict = "MOVE_C_B_PHYS"
        note = ("Case B-phys passes the gate even under the CONSERVATIVE net-open "
                "bound (capture at travel>=engage) -> history-dependent capture is "
                "grounded -> Move C (thicken the corridor).")
    elif gate_opt:
        verdict = "PREMISE_NET_TEMPORAL"
        note = ("Case B-phys passes the gate ONLY under the OPTIMISTIC bound (cone "
                f"trusted from launch); median capture travel ~{med_capture_travel} m "
                f"< engage {engage_dist} m, so capture falls in the N1-flagged "
                "UNVALIDATED early-deployment regime. The wall-vs-history-dependence "
                "question REDUCES to one premise: is the net an effective catcher "
                "before engage travel? NEXT = ground the net temporal/early-deployment "
                "reach (N1 temporal), NOT a blind Move C or Move A.")
    elif gate_a2:
        verdict = "MOVE_C_LIMITED_A2"
        note = ("only the realized A2 path passes (engaged) -> A2-specific dynamic "
                "commitment; generality limited -> Move C with a generality caveat.")
    else:
        verdict = "MOVE_A_GEOMETRIC_WALL"
        note = ("no tested release admits sustained clearance>=0 with Case-B capture "
                ">0 -> geometric wall supported -> Move A (net/kill co-design, eta>1).")
    if not discriminates:
        note += (f" WARNING: capture metric weakly discriminates (axis-committed "
                 f"{cap_mean:.2f} vs null {null_mean:.2f}); treat p_cap with caution.")

    out = {"meta": {"seed": int(seed), "release_times": list(RELEASE_TIMES),
                    "branches": list(BRANCHES), "n_samp": n_samp,
                    "rng_base": RNG_PERS_BASE, "R_LANE": R_LANE, "R_BODY": R_BODY,
                    "engage_dist": engage_dist,
                    "capture_judge": "grounded se3 cone (env cone_half_angle), SWEPT "
                    "(front=net_forward cum_travel); consistent with Case-A cone",
                    "gate": "min_friendly_clearance>=0 (sustained, G3 (bbbb) convention) "
                    "AND Case-B p_cap>0; optimistic=cone-from-launch, engaged=net travel"
                    ">=engage at capture",
                    "note_diagnostic": "does NOT replace Case-A judge or E1 (user pt7); "
                    "Case-B formalization only if gate passes under the engaged bound"},
           "manifest": manifest,
           "grid": grid,
           "readout": {"verdict": verdict, "note": note,
                       "n_gate_optimistic": len(gate_opt),
                       "n_gate_engaged": len(gate_eng),
                       "n_gate_A2_engaged": len(gate_a2),
                       "null_discriminates": discriminates,
                       "cap_mean": cap_mean, "null_mean": null_mean,
                       "median_capture_travel": med_capture_travel,
                       "engage_dist": engage_dist,
                       "gate_opt_cells": [(c["t_rel"], c["branch"]) for c in gate_opt],
                       "gate_eng_cells": [(c["t_rel"], c["branch"]) for c in gate_eng]}}
    return out


def _print(out):
    m = out["manifest"]
    print(f"seed {m['seed']} fire@{m['fire_step']} n_dep={m['n_dep']} "
          f"kill_r={m['env']['kill_radius']} cone_half={m['env']['cone_half_angle']:.3f} "
          f"R_LANE={m['net_sweep']['R_LANE']}")
    print(f"net front@0.15s={m['net_sweep']['front@0.15s']:.1f}m "
          f"r_sil@0.15s={m['net_sweep']['r_sil@0.15s']:.2f}m "
          f"net_radius_engage={m['net_sweep']['net_radius_engage']:.2f}")
    print(f"  engage_dist={out['meta']['engage_dist']}m  (capture below this = "
          f"UNVALIDATED early-deployment regime)")
    print(f"\n{'t_rel':>5} {'branch':<15} {'cA':>5} {'eligA':>5} {'cBopt':>6} "
          f"{'cBeng':>6} {'cBnull':>6} {'capTrv':>6} {'pfeasB':>6} {'minClr':>7} "
          f"{'gOpt':>5} {'gEng':>5} {'pen':>4}")
    for c in out["grid"]:
        mct = c["median_capture_travel"]
        print(f"{c['t_rel']:>5} {c['branch']:<15} {c['p_cap_A']:>5.2f} "
              f"{str(c['eligible_A'])[0]:>5} {c['p_cap_B_phys']:>6.3f} "
              f"{c['p_cap_B_engaged']:>6.3f} {c['p_cap_B_null']:>6.3f} "
              f"{(mct if mct is not None else float('nan')):>6.1f} "
              f"{c['p_feas_B']:>6.3f} {c['min_friendly_clearance']:>+7.2f} "
              f"{str(c['gate_B_phys_optimistic'])[0]:>5} "
              f"{str(c['gate_B_phys_engaged'])[0]:>5} {str(c['penetrated'])[0]:>4}")
    r = out["readout"]
    print(f"\nnull-control: axis-committed p_cap={r['cap_mean']:.3f} vs rotated-null "
          f"{r['null_mean']:.3f} -> discriminates={r['null_discriminates']}")
    print(f"median capture travel={r['median_capture_travel']} m  "
          f"engage_dist={r['engage_dist']} m")
    print(f"\nVERDICT: {r['verdict']}  (gate_optimistic={r['n_gate_optimistic']} "
          f"gate_engaged={r['n_gate_engaged']} gate_A2_eng={r['n_gate_A2_engaged']})")
    print(f"  {r['note']}")
    if r["gate_opt_cells"]:
        print(f"  gate (optimistic): {r['gate_opt_cells']}")
    if r["gate_eng_cells"]:
        print(f"  gate (engaged):    {r['gate_eng_cells']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cem", default="results/c1_corridor/cem_warm/c1_cem.json")
    ap.add_argument("--seed", type=int, default=1100)
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--out", default="results/c1_corridor/c1_persistence.json")
    ap.add_argument("--n-samp", type=int, default=2000)
    a = ap.parse_args()
    out = run(a.cem, a.seed, a.config, a.n_samp)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    _print(out)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
