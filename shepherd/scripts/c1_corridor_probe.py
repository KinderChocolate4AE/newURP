"""C-1 -- nominal-to-shell corridor existence probe (DISCOVERY mode).

New axis (docs/09 (qqq-1) axis-1; doctrine docs/22 v0.2 SS0-1). NOT part of
the A-campaign; NOT a closing experiment -- a branching diagnostic that picks
the next development move and (on success) yields the long on-manifold
trajectories the d1 harvest structurally could not ((qqq) F_hist={2:195}).

v0.2 (2026-07-19): third-party review (docs/24) adopted -- full available
defender control (limiter accel + FINISHER POINTING; translation absent by S1
fixed-launcher design), tiered verdict (shell-reach vs capture), lexicographic
score, knot-parameterised hierarchical CEM, widened seed namespace, and a
snapshot-restore equivalence gate reusing the A-3e reset_to (pre-commit)
contract in place of the retracted "63-d obs = Markov-complete" claim.

Question:  under the FROZEN A2 closed-loop attacker + frozen judgment, does
any available defender control -- 4 limiter accel + finisher net-pointing,
with fire = the autonomous rule guard -- connect a NOMINAL reset to the
fire-eligible shell (v_soft >= theta AND p_feasible > 0) before penetration?

Defender control scope (review SS4): the M2/M3 finisher is a FIXED launcher
(configs finisher_a_max=1.0 "effectively stationary"; env commands a=0), so
"full defender control" here = {limiter accel x4, finisher net-pointing axis,
rule-guard fire}. Finisher TRANSLATION does not exist in this env by design
(S1) -- a scope limit stated with any negative result, NOT silently folded
into "physically infeasible". Finisher pointing DOES enter v_soft (se3_cone
n_F), so leaving it at [0,0,0] (passive hold) understates reachability; the
default finisher here actively points the net at the attacker.

Tiered verdict (review SS2/SS3, per rollout):
  SHELL_REACHED   reset-noneligible -> eligible (v_soft>=theta AND p_feas>0,
                  SAME timestep) BEFORE penetration        <- 1st constructive
  GUARD_FIRED     guard fired at an eligible state
  LOCAL_CAPTURE   arrival_capture after a guard fire
  MISSION_CAPTURE env-terminal capture
Existence claim ladder (campaign level, review SS2):
  E1 pointwise (>=1 nominal seed) / E2 family (one controller, many fresh
  resets) / E3 robust (nonzero basin under perturbation). A single find =
  E1 only ("nominal-to-shell connectivity constructively shown for at least
  one nominal init") -- NOT distribution-level solvability.
Non-find = NOT FOUND UNDER TESTED SOLVERS (never "absent": no infeasibility
certificate here) -> route to task-design sensitivity, not paper-closure.

Stages (--stage): baseline / corral / cem / robust (see docs/23 v0.2).

Frozen/held fixed: judgment J, eval env path, theta, guard predicate,
dynamics, action bounds, nominal reset distribution. No training, no sealed.

Seed ledger (WIDE bands, structurally non-colliding, locked in
tests/test_c1_corridor.py): reset 1100..1199 (search) / 1200..1299 (robust
fresh). rng: CEM 330_000_000 + reset_idx*10_000 + restart ; corral
331_000_000 ; robust 332_000_000 + ... -- disjoint by construction with
budget asserts. Legacy (qqq) nominal-probe 950..1049 and RT-2 212_121
untouched.

Torch-free (learned arms only behind --learned, server).
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib

import numpy as np
import yaml

from shepherd.train.pfc import make_att_pd_fn, make_lambda_brake_fn

N_LIM = 4
A_MAX = 30.0
FIN_P0 = 9 * 4                   # finisher block offset in 63-dim obs
ATT_P0, ATT_V0 = 45, 48          # attacker pos/vel offsets (pfc.py)
RESET_SEARCH0, RESET_SEARCH1 = 1100, 1199
RESET_ROBUST0, RESET_ROBUST1 = 1200, 1299
# --- WIDE rng namespaces (review SS9): base + reset_idx*stride + restart -----
RNG_CEM_BASE = 330_000_000
RNG_CEM_RESET_STRIDE = 10_000        # up to 10k restarts / reset before overlap
RNG_CORRAL_BASE = 331_000_000
RNG_ROBUST_BASE = 332_000_000
ATTPD_GRID = ((2.0, 3.0, 1.0), (4.0, 4.0, 1.0), (8.0, 6.0, 1.0))
NEAR_BAND = 0.05                 # near-shell: v_soft >= theta - NEAR_BAND
S_V = 0.1                        # joint-margin scale for (v_soft - theta)
S_P = 0.01                       # joint-margin scale for p_feas (review SS5.C)
SUSTAIN_MIN = 2                  # >=2 consecutive eligible steps = "sustained"

CORRAL_PATTERNS = ("ring4", "wall3_chase1", "press2_block2")


def cem_seed(reset_idx: int, restart: int) -> int:
    assert 0 <= restart < RNG_CEM_RESET_STRIDE, "restart exceeds reset stride"
    s = RNG_CEM_BASE + reset_idx * RNG_CEM_RESET_STRIDE + restart
    assert s < RNG_CORRAL_BASE, "CEM seed budget overran the corral namespace"
    return s


# ----------------------------------------------------------------- geometry --
def _basis(att_v: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Right-handed frame with e1 = attacker heading (fallback -x)."""
    n = float(np.linalg.norm(att_v))
    e1 = att_v / n if n > 1e-6 else np.array([-1.0, 0.0, 0.0])
    up = np.array([0.0, 0.0, 1.0])
    e2 = np.cross(e1, up)
    n2 = float(np.linalg.norm(e2))
    if n2 < 1e-6:                                   # heading ~ vertical
        e2 = np.cross(e1, np.array([0.0, 1.0, 0.0]))
        n2 = float(np.linalg.norm(e2))
    e2 = e2 / n2
    e3 = np.cross(e1, e2)
    return e1, e2, e3


def corral_slots(params: dict) -> list[dict]:
    """Formation slots in the attacker frame (along/rad/psi). Roles per
    pattern (review SS4.2)."""
    p = params
    if p["pattern"] == "ring4":
        return [{"along": p["d_lead"], "rad": 1.0,
                 "psi": p["phi0"] + i * np.pi / 2.0} for i in range(4)]
    if p["pattern"] == "wall3_chase1":
        slots = [{"along": p["d_lead"], "rad": 1.0,
                  "psi": p["phi0"] + i * 2.0 * np.pi / 3.0} for i in range(3)]
        slots.append({"along": -p["d_back"], "rad": 0.0, "psi": 0.0})
        return slots
    if p["pattern"] == "press2_block2":
        return [{"along": p["d_lead"], "rad": 0.35, "psi": p["phi0"]},
                {"along": p["d_lead"], "rad": 0.35, "psi": p["phi0"] + np.pi},
                {"along": 0.0, "rad": 1.0, "psi": p["phi0"] + np.pi / 2.0},
                {"along": 0.0, "rad": 1.0, "psi": p["phi0"] - np.pi / 2.0}]
    raise ValueError(f"unknown pattern {p['pattern']}")


def make_corral_fn(params: dict):
    """(obs, flags) -> [accel3 x N_LIM]. Obs-only closed loop; radius shrinks
    R0->R1; limiter->slot = greedy nearest at t=0, then held. .state exposes
    the closure dict (review SS10.1: introspection instead of closure-cell)."""
    slots = corral_slots(params)
    st = {"t": 0, "perm": None}
    kp, kd = float(params["kp"]), float(params["kd"])
    vmatch = float(params["vmatch"])
    R0, R1 = float(params["R0"]), float(params["R1"])
    t0, tl = float(params["t_shrink0"]), max(float(params["shrink_len"]), 1.0)

    def fn(obs, flags):
        o = np.asarray(obs, float)
        att_p, att_v = o[ATT_P0:ATT_P0 + 3], o[ATT_V0:ATT_V0 + 3]
        e1, e2, e3 = _basis(att_v)
        frac = float(np.clip((st["t"] - t0) / tl, 0.0, 1.0))
        R = R0 + (R1 - R0) * frac
        tgts = [att_p + s["along"] * e1
                + R * s["rad"] * (np.cos(s["psi"]) * e2
                                  + np.sin(s["psi"]) * e3) for s in slots]
        P = [o[9 * i: 9 * i + 3] for i in range(N_LIM)]
        if st["perm"] is None:                       # greedy nearest, once
            free, perm = set(range(N_LIM)), [0] * N_LIM
            for i in range(N_LIM):
                j = min(free, key=lambda j: float(
                    np.linalg.norm(tgts[j] - P[i])))
                perm[i] = j
                free.discard(j)
            st["perm"] = perm
        st["t"] += 1
        acts = []
        for i in range(N_LIM):
            v = o[9 * i + 3: 9 * i + 6]
            a = kp * (tgts[st["perm"][i]] - P[i]) + kd * (vmatch * att_v - v)
            acts.append(_clip_norm(a, A_MAX).astype(np.float32))
        return acts

    fn.state = st
    return fn


def sample_corral_params(rng: np.random.Generator) -> dict:
    R0 = float(rng.uniform(0.5, 4.0))
    return {"pattern": CORRAL_PATTERNS[int(rng.integers(len(CORRAL_PATTERNS)))],
            "d_lead": float(rng.uniform(0.5, 8.0)),
            "d_back": float(rng.uniform(1.0, 6.0)),
            "R0": R0,
            "R1": float(rng.uniform(0.1, min(1.5, R0))),   # R1 <= R0 (shrink)
            "t_shrink0": float(rng.uniform(0.0, 15.0)),
            "shrink_len": float(rng.uniform(2.0, 25.0)),
            "phi0": float(rng.uniform(0.0, np.pi / 2.0)),
            "kp": float(np.exp(rng.uniform(np.log(1.0), np.log(12.0)))),
            "kd": float(np.exp(rng.uniform(np.log(0.5), np.log(8.0)))),
            "vmatch": float(rng.uniform(0.0, 1.0))}


# ------------------------------------------------------- limiter/finisher fns --
def _clip_norm(a: np.ndarray, a_max: float) -> np.ndarray:
    n = float(np.linalg.norm(a))
    return a * (a_max / n) if (n > a_max and n > 0.0) else a


def _seq_lim(accels):
    """Open-loop accel sequence (T, N_LIM, 3); zero-hold after exhaustion."""
    seq = np.asarray(accels, np.float32)
    st = {"t": 0}

    def fn(obs, flags):
        t = st["t"]
        st["t"] += 1
        if t < len(seq):
            return [seq[t, i] for i in range(N_LIM)]
        return [np.zeros(3, np.float32) for _ in range(N_LIM)]
    fn.seq = seq
    return fn


def knots_to_seq(knots: np.ndarray, t_open: int) -> np.ndarray:
    """Expand K piecewise-constant knots (K, N_LIM, 3) to (t_open, N_LIM, 3)
    -- the low-dim CEM parameterisation (review SS6)."""
    knots = np.asarray(knots, float)
    K = len(knots)
    idx = np.minimum((np.arange(t_open) * K) // max(t_open, 1), K - 1)
    return knots[idx]


def make_finisher_fn(theta: float, mode: str = "point_at_attacker",
                     d_lead: float = 0.0):
    """Rule-guard fire + net POINTING (review SS4). Returns live finisher
    action [ax, ay, az, fire] (pad inserts slot 3 = reserved slew).

    mode="point_at_attacker": aim n_F from the finisher apex at the attacker
    (obs-derivable; opens the pointing DOF that enters v_soft via se3_cone).
    mode="hold": axis [0,0,0] -> backend keeps the default pointing (ablation,
    == the pre-v0.2 behaviour)."""
    from shepherd.train.phi_potential import teacher_fire

    def fin(obs, flags):
        o = np.asarray(obs, float)
        fire = 1.0 if teacher_fire(o, theta) else 0.0
        if mode == "hold":
            axis = np.zeros(3)
        else:
            fin_p, att_p = o[FIN_P0:FIN_P0 + 3], o[ATT_P0:ATT_P0 + 3]
            att_v = o[ATT_V0:ATT_V0 + 3]
            aim = (att_p + d_lead * att_v) - fin_p
            n = float(np.linalg.norm(aim))
            axis = aim / n if n > 1e-6 else np.zeros(3)
        return np.array([axis[0], axis[1], axis[2], fire], np.float32)

    fin.mode = mode
    return fin


# ------------------------------------------------------------------ rollout --
class ProbeEnv:
    """One frozen-judgment env (m3_eval_bundle path) + margin-traced rollout."""

    def __init__(self, env_cfg: dict, m3, attacker_params: dict | None = None):
        from shepherd.train.make_env_m3 import (M3Adapter,
                                                build_m3_attacker_env,
                                                make_m3_train_env)
        if attacker_params:
            env, _, _ = build_m3_attacker_env(copy.deepcopy(env_cfg), m3,
                                              attacker_params, stage=None)
        else:
            env, _, _ = make_m3_train_env(copy.deepcopy(env_cfg), m3,
                                          stage=None)
        self.ad = M3Adapter(env)
        self.theta = float(self.ad.env.theta_fire)

    def rollout(self, lim_fn, fin_fn, reset_seed: int, *,
                trace: bool = False, act_noise: float = 0.0,
                noise_rng: np.random.Generator | None = None,
                spawn: dict | None = None) -> dict:
        """spawn=None -> reset() (nominal); spawn=dict -> reset_to() (A-3
        TRAIN-ONLY restore path, used ONLY by the snapshot-equivalence gate,
        never by the existence arms)."""
        ad = self.ad
        if spawn is None:
            obs_d, _ = ad.reset(seed=int(reset_seed))
        else:
            obs_d, _ = ad.reset_to(dict(spawn), seed=int(reset_seed))
        obs = obs_d[ad.limiter_ids[0]]
        th = self.theta
        vs, pf, acts_log, obs_log = [], [], [], []
        first_elig = None
        elig_run = elig_run_max = 0
        pen_at = None
        steps = 0
        flags: dict = {}
        while True:
            v_soft, p_feas = float(obs[-3]), float(obs[-1])
            vs.append(v_soft)
            pf.append(p_feas)
            elig_now = (np.isfinite(v_soft) and np.isfinite(p_feas)
                        and v_soft >= th and p_feas > 0.0)
            if elig_now:
                elig_run += 1
                elig_run_max = max(elig_run_max, elig_run)
                if first_elig is None:
                    first_elig = steps
            else:
                elig_run = 0
            lim = lim_fn(obs, flags)
            if act_noise > 0.0 and noise_rng is not None:
                lim = [np.clip(np.asarray(a, float)
                               + noise_rng.normal(0.0, act_noise, 3),
                               -A_MAX, A_MAX).astype(np.float32) for a in lim]
            if trace:
                obs_log.append(np.asarray(obs, float).tolist())
                acts_log.append(np.stack([np.asarray(a, float)
                                          for a in lim]).tolist())
            live = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.asarray(fin_fn(obs, flags), np.float32)
            r = ad.step(live)
            if pen_at is None and bool(r.flags.get("penetrated")):
                pen_at = steps
            obs = r.obs[ad.limiter_ids[0]]
            flags = r.flags
            steps += 1
            if r.done:
                break
        chains = list(r.flags["fire_chains"])
        vs_arr, pf_arr = np.asarray(vs), np.asarray(pf)
        fin_mask = np.isfinite(vs_arr) & np.isfinite(pf_arr)
        elig_mask = fin_mask & (pf_arr > 0.0) & (vs_arr >= th)
        pf_pos = fin_mask & (pf_arr > 0.0)
        over_th = fin_mask & (vs_arr >= th)
        # scale-normalised joint margin, only where BOTH hold (review SS5.C)
        if elig_mask.any():
            jm = np.minimum((vs_arr[elig_mask] - th) / S_V,
                            pf_arr[elig_mask] / S_P)
            m_joint = float(jm.max())
        else:
            m_joint = float("-inf")
        reset_elig = bool(fin_mask[0] and vs[0] >= th and pf[0] > 0.0)
        shell_reached = bool(first_elig is not None
                             and not reset_elig
                             and (pen_at is None or first_elig < pen_at))
        guard_fired = len(chains) > 0
        arrival_capture = bool(r.flags["captured"]
                               and any(c.get("clean") for c in chains)
                               and not reset_elig)
        rec = {"reset_seed": int(reset_seed), "len": steps,
               "captured": bool(r.flags["captured"]),
               "penetrated": bool(r.flags["penetrated"]),
               "penetrated_at": pen_at,
               "wasted": float(r.flags["wasted_fire"]),
               "n_fires": len(chains),
               "fire_steps": [int(c["fire_step"]) for c in chains
                              if c.get("fire_step") is not None],
               "clean_fire": bool(any(c.get("clean") for c in chains)),
               # margins (review SS5): M_v, M_p, M_joint + raw + max_v_soft
               "max_v_soft": float(vs_arr[fin_mask].max()
                                   if fin_mask.any() else 0.0),
               "M_v_given_pfeas": float(vs_arr[pf_pos].max()
                                        if pf_pos.any() else 0.0),
               "M_p_given_vsoft": float(pf_arr[over_th].max()
                                        if over_th.any() else 0.0),
               "M_joint": m_joint,
               "max_p_feas": float(pf_arr[fin_mask].max()
                                   if fin_mask.any() else 0.0),
               "near_dwell": int(np.sum(fin_mask & (pf_arr > 0.0)
                                        & (vs_arr >= th - NEAR_BAND))),
               "boxed_shell_steps": int(np.sum(fin_mask & (pf_arr <= 0.0)
                                               & (vs_arr >= th))),
               "eligible_dwell": int(elig_mask.sum()),
               "eligible_run_max": int(elig_run_max),
               "sustained": bool(elig_run_max >= SUSTAIN_MIN),
               "single_frame_only": bool(0 < elig_run_max < SUSTAIN_MIN),
               "eligible": first_elig is not None,
               "first_eligible_step": first_elig,
               "reset_clean": reset_elig,
               # tiered verdict (review SS2/SS3)
               "SHELL_REACHED": shell_reached,
               "GUARD_FIRED": guard_fired,
               "LOCAL_CAPTURE": arrival_capture,
               "MISSION_CAPTURE": bool(r.flags["captured"]),
               "arrival_capture": arrival_capture}
        if trace:
            rec["trace"] = {"obs": obs_log, "acts": acts_log,
                            "v_soft": [float(x) for x in vs],
                            "p_feas": [float(x) for x in pf]}
        return rec


# --------------------------------------------------------- score (SS7 lexi) --
_TIER = 1_000.0        # inter-tier separation >> any intra-tier contribution


def score_vector(rec: dict) -> tuple:
    """Lexicographic key (review SS7), most significant first:
    capture > shell-eligible > joint margin > eligible dwell > delay/non-pen
    > -control-effort-proxy. Boxed over-compression scores strictly below any
    clean eligible state (smoke-verified failure mode, reset 1100 t20-22)."""
    jm = rec["M_joint"] if np.isfinite(rec["M_joint"]) else -1.0
    return (float(rec["LOCAL_CAPTURE"]),
            float(rec["SHELL_REACHED"] or rec["eligible"]),
            jm,
            float(rec["eligible_dwell"]),
            float(rec["penetrated_at"] if rec["penetrated_at"] is not None
                  else rec["len"]),        # later/never penetration is better
            -0.0)                          # effort slot (kept 0; logged in rec)


def score(rec: dict) -> float:
    """Flat lexicographic scalar for optimiser guidance ONLY (never verdict J;
    verdict = SHELL_REACHED). Tiers separated by _TIER so no lower tier can
    overturn a higher one within realistic ranges."""
    v = score_vector(rec)
    s = 0.0
    for x in v:
        s = s * _TIER + float(np.clip(x, -_TIER / 2 + 1, _TIER / 2 - 1))
    return s


def _summ(recs: list[dict]) -> dict:
    def _m(key):
        return float(np.mean([r[key] for r in recs]))
    mv = np.asarray([r["max_v_soft"] for r in recs], float)
    return {"n": len(recs),
            "shell_reached_rate": _m("SHELL_REACHED"),
            "n_shell_reached": int(sum(r["SHELL_REACHED"] for r in recs)),
            "guard_fired_rate": _m("GUARD_FIRED"),
            "local_capture_rate": _m("LOCAL_CAPTURE"),
            "mission_capture_rate": _m("MISSION_CAPTURE"),
            "eligible_rate": _m("eligible"),
            "n_eligible": int(sum(r["eligible"] for r in recs)),
            "sustained_rate": _m("sustained"),
            "single_frame_rate": _m("single_frame_only"),
            "M_v_given_pfeas_mean": _m("M_v_given_pfeas"),
            "M_v_given_pfeas_max": float(max(r["M_v_given_pfeas"]
                                             for r in recs)),
            "M_p_given_vsoft_max": float(max(r["M_p_given_vsoft"]
                                             for r in recs)),
            "M_joint_max": float(max((r["M_joint"] for r in recs
                                      if np.isfinite(r["M_joint"])),
                                     default=float("-inf"))),
            "max_v_soft_mean": float(mv.mean()),
            "max_v_soft_max": float(mv.max()),
            "boxed_shell_rate": _m("boxed_shell_steps"),
            "penetrated_rate": _m("penetrated"),
            "wasted_mean": _m("wasted"),
            "len_mean": _m("len"),
            "first_eligible_steps": sorted(
                int(r["first_eligible_step"]) for r in recs
                if r["first_eligible_step"] is not None),
            "score_mean": float(np.mean([score(r) for r in recs]))}


# -------------------------------------------------------------------- arms --
def _zero_fn(obs, flags):
    return [np.zeros(3, np.float32) for _ in range(N_LIM)]


def _brake_fn(obs, flags):
    o = np.asarray(obs, float)
    acts = []
    for i in range(N_LIM):
        v = o[9 * i + 3: 9 * i + 6]
        n = float(np.linalg.norm(v))
        acts.append((-A_MAX * v / n if n > 1e-6
                     else np.zeros(3)).astype(np.float32))
    return acts


def baseline_arms(learned: bool, ckpt_root: str, tag: str, device: str):
    arms = [("zero", lambda: _zero_fn),
            ("brake", lambda: _brake_fn),
            ("lam20", lambda: make_lambda_brake_fn(20.0))]
    for kp, kd, dl in ATTPD_GRID:
        arms.append((f"attpd_{int(kp)}_{int(kd)}",
                     lambda kp=kp, kd=kd, dl=dl: make_att_pd_fn(kp, kd, dl)))
    if learned:                                     # torch, server only
        from shepherd.scripts.eval_heldout_m3 import learned_fns
        lim_scale = np.full(3, A_MAX, np.float32)
        for s in (0, 1, 2):
            root = pathlib.Path(ckpt_root) / f"seed{s}"
            if not (root / f"ckpt_mappo_{tag}.pt").exists():
                continue
            lf, _ff, _meta = learned_fns(root, tag, device)
            arms.append((f"learned_s{s}:{tag}",
                         lambda _lf=lf: (lambda o, f:
                                         _lf(o, f, lim_scale))))
    return arms


# --------------------------------------------------------------------- CEM --
def cem_optimise(pe: ProbeEnv, fin, reset_seed: int, rng: np.random.Generator,
                 *, knots: int, t_open: int, pop: int, iters: int,
                 elite_frac: float, sigma0: float,
                 warm: np.ndarray | None = None) -> dict:
    """Knot-parameterised CEM (review SS6): optimise (knots, N_LIM, 3) control
    points (dim = knots*12, e.g. 5 -> 60), expand piecewise-constant to
    t_open. Deterministic rollout given reset_seed => a real optimisation.
    Early-stop on SHELL_REACHED (1st constructive proof); best = argmax
    score_vector so the returned acts ARE the best candidate (review SS10.4)."""
    dim = (knots, N_LIM, 3)
    mu = np.zeros(dim) if warm is None else _fit_knots(warm, knots)
    sig = np.full(dim, float(sigma0))
    n_el = max(2, int(round(pop * elite_frac)))
    best = {"vec": None, "rec": None, "knots": None, "stop": "budget"}
    hist = []
    for it in range(iters):
        cands = np.clip(mu + sig * rng.standard_normal((pop,) + dim),
                        -A_MAX, A_MAX)
        vecs, recs = [], []
        for c in range(pop):
            seq = knots_to_seq(cands[c], t_open)
            rec = pe.rollout(_seq_lim(seq), fin, reset_seed)
            recs.append(rec)
            v = score_vector(rec)
            vecs.append(v)
            if best["vec"] is None or v > best["vec"]:
                best = {"vec": v, "rec": rec, "knots": cands[c].copy(),
                        "stop": best["stop"]}
        order = sorted(range(pop), key=lambda c: vecs[c])
        el = order[-n_el:]
        mu = cands[el].mean(axis=0)
        sig = cands[el].std(axis=0) * 1.05 + 0.3     # floor: keep exploring
        hist.append({"iter": it,
                     "best_score": float(score(recs[order[-1]])),
                     "n_shell": int(sum(r["SHELL_REACHED"] for r in recs)),
                     "n_elig": int(sum(r["eligible"] for r in recs))})
        if best["rec"] is not None and best["rec"]["SHELL_REACHED"]:
            best["stop"] = ("capture" if best["rec"]["LOCAL_CAPTURE"]
                            else "shell_reached")
            break
    best_seq = (knots_to_seq(best["knots"], t_open)
                if best["knots"] is not None else None)
    return {"best_score": float(score(best["rec"])) if best["rec"] else -1e18,
            "best_record": best["rec"],
            "best_knots": (best["knots"].tolist()
                           if best["knots"] is not None else None),
            "best_acts": best_seq.tolist() if best_seq is not None else None,
            "early_stop_reason": best["stop"], "curve": hist}


def _fit_knots(seq: np.ndarray, knots: int) -> np.ndarray:
    """Average an action sequence into `knots` piecewise-constant blocks
    (corral warm-start -> knot space, review SS6 CEM-2)."""
    seq = np.asarray(seq, float)
    T = len(seq)
    out = np.zeros((knots, N_LIM, 3))
    for kk in range(knots):
        lo, hi = kk * T // knots, max((kk + 1) * T // knots, kk * T // knots + 1)
        out[kk] = seq[lo:hi].mean(axis=0) if hi > lo else seq[min(lo, T - 1)]
    return out


# ---------------------------------------------------- snapshot restore gate --
def snapshot_restore_check(pe: ProbeEnv, lim_fn_factory, fin, reset_seed: int,
                           t_snap: int, theta: float) -> dict:
    """Two-tier reproducibility (review SS8), replacing the retracted
    "63-d obs = Markov-complete" claim:

    tier 1  exact replay from the reset seed (deterministic) -- always valid.
    tier 2  reset_to restore of the PRE-COMMIT state at t_snap (limiter p/v +
            attacker p/v; finisher/FSM fresh -- the A-3e (kkk) contract) then
            continue: does the continuation trace match the original tail?
            Valid ONLY pre-commit (no guard fire at/before t_snap); asserted.
    Returns per-tier max position error over the compared window."""
    ad = pe.ad
    base = pe.rollout(lim_fn_factory(), fin, reset_seed, trace=True)
    tr = base["trace"]
    # tier 1: exact replay of the recorded actions from seed
    rep = pe.rollout(_seq_lim(np.asarray(tr["acts"], float)), fin, reset_seed,
                     trace=True)
    o0 = np.asarray(tr["obs"], float)
    o1 = np.asarray(rep["trace"]["obs"], float)
    n = min(len(o0), len(o1))
    limp = lambda o: o[:, :9 * N_LIM].reshape(len(o), N_LIM, 9)[:, :, :3]
    err_replay = float(np.max(np.linalg.norm(limp(o0[:n]) - limp(o1[:n]),
                                             axis=-1)))
    out = {"reset_seed": reset_seed, "t_snap": t_snap,
           "tier1_exact_replay_err": err_replay, "tier2": None}
    # tier 2: pre-commit reset_to restore + continuation
    fired_before = any(fs <= t_snap for fs in base["fire_steps"])
    if fired_before or t_snap >= len(tr["obs"]) - 1:
        out["tier2"] = {"applicable": False,
                        "reason": "post-commit or t_snap past trace end"}
        return out
    o_s = np.asarray(tr["obs"][t_snap], float)
    spawn = {"limiters": o_s[:9 * N_LIM].reshape(N_LIM, 9)[:, :3],
             "limiter_v": o_s[:9 * N_LIM].reshape(N_LIM, 9)[:, 3:6],
             "att_p": o_s[ATT_P0:ATT_P0 + 3], "att_v": o_s[ATT_V0:ATT_V0 + 3]}
    tail_acts = np.asarray(tr["acts"][t_snap:], float)
    cont = pe.rollout(_seq_lim(tail_acts), fin, reset_seed, trace=True,
                      spawn=spawn)
    oc = np.asarray(cont["trace"]["obs"], float)
    m = min(len(oc), len(o0) - t_snap)
    err_restore = float(np.max(np.linalg.norm(
        limp(o0[t_snap:t_snap + m]) - limp(oc[:m]), axis=-1)))
    out["tier2"] = {"applicable": True, "restore_err": err_restore,
                    "compared_steps": int(m),
                    "note": "pre-commit contract (A-3e (kkk)); finisher/FSM "
                            "fresh -- valid because attacker is pre-commit "
                            "memoryless given obs state"}
    return out


# ------------------------------------------------------------------- stages --
def _load(cfg_path: str):
    run_cfg = yaml.safe_load(open(cfg_path))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    return env_cfg, m3, theta


def _archive(recs_by_arm: dict, top: int) -> list[dict]:
    flat = [(arm, r) for arm, rs in recs_by_arm.items() for r in rs]
    keep = [(a, r) for a, r in flat if r["SHELL_REACHED"]]
    rest = sorted((x for x in flat if not x[1]["SHELL_REACHED"]),
                  key=lambda x: score_vector(x[1]), reverse=True)
    keep += rest[: max(0, top - len(keep))]
    return [{"arm": a, "reset_seed": r["reset_seed"],
             "shell_reached": r["SHELL_REACHED"],
             "M_joint": (r["M_joint"] if np.isfinite(r["M_joint"]) else None),
             "max_v_soft": r["max_v_soft"]} for a, r in keep]


def stage_baseline(a, out_dir: pathlib.Path):
    env_cfg, m3, theta = _load(a.config)
    pe = ProbeEnv(env_cfg, m3)
    fin = make_finisher_fn(theta, a.finisher, a.fin_lead)
    seeds = list(range(a.seed0, a.seed0 + a.n))
    out = {"meta": {"stage": "baseline", "seeds": [seeds[0], seeds[-1]],
                    "theta": theta, "near_band": NEAR_BAND,
                    "finisher": a.finisher, "fin_lead": a.fin_lead,
                    "scope": "limiter accel x4 + finisher pointing "
                             "(translation absent: S1 fixed launcher)",
                    "doc": "C-1 v0.2 discovery; docs/09 (ttt)"},
           "arms": {}}
    per_arm = {}
    for name, mk in baseline_arms(a.learned, a.ckpt_root, a.tag, a.device):
        recs = [pe.rollout(mk(), fin, s) for s in seeds]
        per_arm[name] = recs
        out["arms"][name] = {"summary": _summ(recs), "episodes": recs}
        s = out["arms"][name]["summary"]
        print(f"[baseline] {name}: shell={s['n_shell_reached']}/{s['n']} "
              f"cap={s['local_capture_rate']:.3f} "
              f"Mv|pf={s['M_v_given_pfeas_max']:.3f} "
              f"Mjoint={s['M_joint_max']:.2f} maxV={s['max_v_soft_max']:.3f} "
              f"boxed={s['boxed_shell_rate']:.2f} len={s['len_mean']:.0f}",
              flush=True)
    out["archive_index"] = _archive(per_arm, a.archive_top)
    _write(out_dir / "c1_baseline.json", out)


def stage_corral(a, out_dir: pathlib.Path):
    env_cfg, m3, theta = _load(a.config)
    pe = ProbeEnv(env_cfg, m3)
    fin = make_finisher_fn(theta, a.finisher, a.fin_lead)
    rng = np.random.default_rng(RNG_CORRAL_BASE)
    cfgs = [sample_corral_params(rng) for _ in range(a.n_cfg)]
    screen_seeds = list(range(a.seed0, a.seed0 + a.screen_draws))
    scored = []
    for ci, p in enumerate(cfgs):
        recs = [pe.rollout(make_corral_fn(p), fin, s) for s in screen_seeds]
        scored.append({"cfg_idx": ci, "params": p, "screen": _summ(recs),
                       "screen_score": float(np.mean([score(r)
                                                      for r in recs]))})
        if (ci + 1) % 20 == 0:
            print(f"[corral] screened {ci + 1}/{a.n_cfg}", flush=True)
    scored.sort(key=lambda x: x["screen_score"], reverse=True)
    top = scored[: a.top_k]
    full_seeds = list(range(a.seed0, a.seed0 + a.n))
    for t in top:
        recs = [pe.rollout(make_corral_fn(t["params"]), fin, s)
                for s in full_seeds]
        t["full"] = {"summary": _summ(recs), "episodes": recs}
        s = t["full"]["summary"]
        print(f"[corral] top cfg#{t['cfg_idx']} {t['params']['pattern']}: "
              f"shell={s['n_shell_reached']}/{s['n']} "
              f"cap={s['local_capture_rate']:.3f} "
              f"Mjoint={s['M_joint_max']:.2f} boxed={s['boxed_shell_rate']:.2f}",
              flush=True)
    out = {"meta": {"stage": "corral", "rng": RNG_CORRAL_BASE, "n_cfg": a.n_cfg,
                    "screen_seeds": [screen_seeds[0], screen_seeds[-1]],
                    "full_seeds": [full_seeds[0], full_seeds[-1]],
                    "finisher": a.finisher, "theta": theta},
           "screen_ranking": [{k: v for k, v in s.items() if k != "full"}
                              for s in scored],
           "top": top}
    _write(out_dir / "c1_corral.json", out)


def stage_cem(a, out_dir: pathlib.Path):
    env_cfg, m3, theta = _load(a.config)
    pe = ProbeEnv(env_cfg, m3)
    fin = make_finisher_fn(theta, a.finisher, a.fin_lead)
    warm_by_seed = {}
    if a.warm_from:
        w = json.loads(pathlib.Path(a.warm_from).read_text())
        best = max(w["top"], key=lambda t: t["full"]["summary"]["score_mean"])
        p = best["params"]
        for s in range(a.seed0, a.seed0 + a.draws):
            rec = pe.rollout(make_corral_fn(p), fin, s, trace=True)
            warm_by_seed[s] = np.asarray(rec["trace"]["acts"], float)
        print(f"[cem] warm start from corral cfg#{best['cfg_idx']} "
              f"({best['params']['pattern']})", flush=True)
    results = []
    for j in range(a.draws):
        s = a.seed0 + j
        rng = np.random.default_rng(cem_seed(j, 0))
        res = cem_optimise(pe, fin, s, rng, knots=a.knots, t_open=a.t_open,
                           pop=a.pop, iters=a.iters, elite_frac=a.elite_frac,
                           sigma0=a.sigma0, warm=warm_by_seed.get(s))
        res["reset_seed"] = s
        b = res["best_record"] or {}
        if b and (b["SHELL_REACHED"] or a.trace_all):
            tr = pe.rollout(_seq_lim(np.asarray(res["best_acts"])), fin, s,
                            trace=True)
            res["best_trace"] = tr["trace"]
            res["replay_shell_reached"] = tr["SHELL_REACHED"]   # SS10.4
        results.append(res)
        print(f"[cem] seed {s}: stop={res['early_stop_reason']} "
              f"shell={b.get('SHELL_REACHED')} cap={b.get('LOCAL_CAPTURE')} "
              f"Mjoint={b.get('M_joint', float('nan')):.2f} "
              f"maxV={b.get('max_v_soft', float('nan')):.3f}", flush=True)
    out = {"meta": {"stage": "cem", "rng_base": RNG_CEM_BASE,
                    "seeds": [a.seed0, a.seed0 + a.draws - 1],
                    "knots": a.knots, "pop": a.pop, "iters": a.iters,
                    "t_open": a.t_open, "sigma0": a.sigma0,
                    "warm_from": a.warm_from, "finisher": a.finisher,
                    "theta": theta},
           "draws": results,
           "n_shell_reached_draws": int(sum(
               1 for r in results
               if r["best_record"] and r["best_record"]["SHELL_REACHED"]))}
    _write(out_dir / "c1_cem.json", out)


def stage_robust(a, out_dir: pathlib.Path):
    env_cfg, m3, theta = _load(a.config)
    fin = make_finisher_fn(theta, a.finisher, a.fin_lead)
    out = {"meta": {"stage": "robust", "theta": theta, "finisher": a.finisher,
                    "rng_base": RNG_ROBUST_BASE,
                    "tiers": "R1 exact / R2 local basin / R3 attacker / "
                             "R4 feedback realizability"},
           "corral_fresh": None, "cem": []}
    if a.corral_from and pathlib.Path(a.corral_from).exists():
        w = json.loads(pathlib.Path(a.corral_from).read_text())
        best = max(w["top"], key=lambda t: t["full"]["summary"]["score_mean"])
        pe = ProbeEnv(env_cfg, m3)
        seeds = list(range(RESET_ROBUST0, RESET_ROBUST0 + a.robust_n))
        recs = [pe.rollout(make_corral_fn(best["params"]), fin, s)
                for s in seeds]                       # E2: family, fresh band
        out["corral_fresh"] = {"cfg_idx": best["cfg_idx"],
                               "params": best["params"],
                               "fresh_band": [seeds[0], seeds[-1]],
                               "summary": _summ(recs)}
        s = out["corral_fresh"]["summary"]
        print(f"[robust] corral fresh band (E2): "
              f"shell={s['n_shell_reached']}/{s['n']}", flush=True)
    if a.cem_from and pathlib.Path(a.cem_from).exists():
        w = json.loads(pathlib.Path(a.cem_from).read_text())
        winners = [d for d in w["draws"]
                   if d["best_record"] and d["best_record"]["SHELL_REACHED"]]
        pe0 = ProbeEnv(env_cfg, m3)
        pe_att = {v: ProbeEnv(env_cfg, m3, {"att_speed": v})
                  for v in a.att_speeds}
        for wi, d in enumerate(winners):
            acts = np.asarray(d["best_acts"], float)
            s = int(d["reset_seed"])
            row = {"reset_seed": s}
            # R1 exact replay
            r1 = pe0.rollout(_seq_lim(acts), fin, s)
            row["R1_exact"] = {"shell_reached": r1["SHELL_REACHED"],
                               "M_joint": (r1["M_joint"]
                                           if np.isfinite(r1["M_joint"])
                                           else None)}
            # R2 local basin: action noise
            row["R2_action_noise"] = {}
            for eps in a.act_noise:
                rng = np.random.default_rng(RNG_ROBUST_BASE + 10_000 * wi
                                            + int(eps * 100))
                reps = [pe0.rollout(_seq_lim(acts), fin, s, act_noise=eps,
                                    noise_rng=rng) for _ in range(a.reps)]
                row["R2_action_noise"][str(eps)] = _summ(reps)
            # R3 attacker-speed variants (same reset)
            row["R3_attacker"] = {}
            for v, pv in pe_att.items():
                rec = pv.rollout(_seq_lim(acts), fin, s)
                row["R3_attacker"][str(v)] = {
                    "shell_reached": rec["SHELL_REACHED"],
                    "M_joint": (rec["M_joint"] if np.isfinite(rec["M_joint"])
                                else None)}
            # R4 feedback realizability: PD tracking the recorded reference
            row["R4_feedback"] = _r4_feedback(pe0, acts, fin, s, a)
            out["cem"].append(row)
            print(f"[robust] cem seed {s}: R1 shell={r1['SHELL_REACHED']} "
                  f"R4 shell={row['R4_feedback']['shell_reached']}", flush=True)
    _write(out_dir / "c1_robust.json", out)


def _r4_feedback(pe, acts, fin, reset_seed, a):
    """R4 (review SS11): does a simple obs-only PD tracker of the recorded
    reference positions preserve shell-reach? Open-loop success is a valid
    existence proof but a curriculum seed needs a small feedback basin."""
    ref = pe.rollout(_seq_lim(acts), fin, reset_seed, trace=True)
    P_ref = np.asarray(ref["trace"]["obs"], float)[:, :9 * N_LIM]
    P_ref = P_ref.reshape(len(P_ref), N_LIM, 9)[:, :, :3]
    V_ref = np.asarray(ref["trace"]["obs"], float)[:, :9 * N_LIM]
    V_ref = V_ref.reshape(len(V_ref), N_LIM, 9)[:, :, 3:6]
    st = {"t": 0}
    kp, kd = float(a.r4_kp), float(a.r4_kd)

    def track(obs, flags):
        o = np.asarray(obs, float)
        t = min(st["t"], len(P_ref) - 1)
        st["t"] += 1
        acts_out = []
        for i in range(N_LIM):
            p, v = o[9 * i:9 * i + 3], o[9 * i + 3:9 * i + 6]
            acc = kp * (P_ref[t, i] - p) + kd * (V_ref[t, i] - v)
            acts_out.append(_clip_norm(acc, A_MAX).astype(np.float32))
        return acts_out

    rec = pe.rollout(track, fin, reset_seed)
    return {"shell_reached": rec["SHELL_REACHED"], "kp": kp, "kd": kd,
            "M_joint": rec["M_joint"] if np.isfinite(rec["M_joint"]) else None}


def _write(path: pathlib.Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))
    print(f"wrote {path}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stage", required=True,
                    choices=("baseline", "corral", "cem", "robust"))
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--out-dir", default="results/c1_corridor")
    ap.add_argument("--seed0", type=int, default=RESET_SEARCH0)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--archive-top", type=int, default=20)
    ap.add_argument("--finisher", default="point_at_attacker",
                    choices=("point_at_attacker", "hold"))
    ap.add_argument("--fin-lead", type=float, default=0.0)
    # baseline learned arms (server)
    ap.add_argument("--learned", action="store_true")
    ap.add_argument("--ckpt-root", default="results/m3a_a3e_p1")
    ap.add_argument("--tag", default="j1_e1")
    ap.add_argument("--device", default="cpu")
    # corral
    ap.add_argument("--n-cfg", type=int, default=160)
    ap.add_argument("--screen-draws", type=int, default=10)
    ap.add_argument("--top-k", type=int, default=5)
    # cem (knot-parameterised)
    ap.add_argument("--draws", type=int, default=10)
    ap.add_argument("--knots", type=int, default=5)
    ap.add_argument("--pop", type=int, default=40)
    ap.add_argument("--iters", type=int, default=20)
    ap.add_argument("--elite-frac", type=float, default=0.25)
    ap.add_argument("--sigma0", type=float, default=10.0)
    ap.add_argument("--t-open", type=int, default=24)
    ap.add_argument("--warm-from", default="")
    ap.add_argument("--trace-all", action="store_true")
    # robust
    ap.add_argument("--corral-from",
                    default="results/c1_corridor/c1_corral.json")
    ap.add_argument("--cem-from", default="results/c1_corridor/c1_cem.json")
    ap.add_argument("--robust-n", type=int, default=50)
    ap.add_argument("--reps", type=int, default=8)
    ap.add_argument("--act-noise", type=float, nargs="*", default=[0.5, 1.0])
    ap.add_argument("--att-speeds", type=float, nargs="*", default=[18.0, 22.0])
    ap.add_argument("--r4-kp", type=float, default=8.0)
    ap.add_argument("--r4-kd", type=float, default=4.0)
    a = ap.parse_args()
    out_dir = pathlib.Path(a.out_dir)
    {"baseline": stage_baseline, "corral": stage_corral,
     "cem": stage_cem, "robust": stage_robust}[a.stage](a, out_dir)


if __name__ == "__main__":
    main()
