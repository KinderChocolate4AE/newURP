"""A-3e P1' core (docs/21 v0.3 FROZEN; docs/09 (kkk)). torch-free.

Everything judgment-relevant is HERE so it unit-tests without torch:
the 3-phase state machine, per-phase behaviour flags, paired-gate math
(bootstrap 777), selective-fire diagnostics, best-ckpt ordering, and the
d0/d1 spawn draws over the ADMISSIBLE bank subset.

FROZEN NUMBERS (docs/21 v0.3 SS4; changing any is a prereg violation):
  eval cadence 20,480 env steps; phase caps F0/L1/J1 = 6/8/8 evals
  (total cap 450,560); advance = metric > gate for 2 CONSECUTIVE evals;
  F0 exit metric = captured_rate >= 0.45 (A-3b R0 value, teacher-free,
  limiter HOLD); L1/J1 gate = paired Delta^ > 0.10 (vs the dev zero-cache,
  same episode IDs); J1 stall = bootstrap UCB95 < 0.05 for 3 consecutive
  evals (RECORDED ONLY -- no teacher re-entry, no backoff target).
  L1 cap miss => FAIL *without* unfreezing fire (stop rule 5).

Phase behaviour contract (docs/21 v0.3 SS4):
  F0: stage d0, limiter HOLD (env action = 0) + limiter actor FROZEN,
      teacher OFF, fire head TRAINS.
  L1: stage d1, fire head FROZEN + live fire = teacher gate, limiter TRAINS.
  J1: stage d1, teacher OFF permanently, fire UNFROZEN with a FRESH
      fire-head optimizer, limiter keeps training.
"""
from __future__ import annotations

import json
import pathlib
from typing import Dict, List, Optional

import numpy as np

CADENCE = 20_480
PHASE_MAX_EVALS = {"F0": 6, "L1": 8, "J1": 8}
TOTAL_CAP_STEPS = CADENCE * sum(PHASE_MAX_EVALS.values())        # 450,560
CONSEC = 2
F0_EXIT = 0.45                      # captured_rate (A-3b R0 ratified value)
DELTA_GATE = 0.10                   # L1/J1 paired-Delta advance gate
STALL_UCB, STALL_N = 0.05, 3        # J1 stall (recorded only)
BOOT_N, BOOT_SEED = 10_000, 777     # all analyses share rng 777 (no
                                    # independence claim -- docs/21 SS6)
D1_SIGMA = 0.005                    # frozen sigma ramp, stage d1

PHASE_FLAGS = {                     # (teacher, freeze_fin, freeze_lim, hold_lim)
    "F0": {"teacher": False, "freeze_fin": False,
           "freeze_lim": True, "hold_lim": True},
    "L1": {"teacher": True, "freeze_fin": True,
           "freeze_lim": False, "hold_lim": False},
    "J1": {"teacher": False, "freeze_fin": False,
           "freeze_lim": False, "hold_lim": False},
}


def paired_delta(pol: List[int], zero: List[int],
                 n_boot: int = BOOT_N, seed: int = BOOT_SEED) -> dict:
    """Episode-paired Delta^ + percentile bootstrap LCB/UCB95 (rng 777)."""
    p = np.asarray(pol, float)
    z = np.asarray(zero, float)
    assert p.shape == z.shape and len(p) > 0, "paired arms must align"
    d = p - z
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    return {"delta_hat": float(d.mean()),
            "lcb95": float(np.quantile(means, 0.05)),
            "ucb95": float(np.quantile(means, 0.95))}


def diagnostics(rows: List[dict]) -> dict:
    """Selective-fire diagnostics (docs/21 SS4, episode-level definitions):
    fired = n_fires > 0; clean-ep = the clean predicate held at any step."""
    def rate(sel, val):
        xs = [val(r) for r in rows if sel(r)]
        return float(np.mean(xs)) if xs else None
    return {
        "p_fire_given_clean": rate(lambda r: r["clean"],
                                   lambda r: r["n_fires"] > 0),
        "p_fire_given_nonclean": rate(lambda r: not r["clean"],
                                      lambda r: r["n_fires"] > 0),
        "p_capture_given_reset_nonclean": rate(
            lambda r: not r["reset_clean"], lambda r: r["captured"]),
    }


def best_ckpt_key(delta_free: float, p_fire_nonclean: Optional[float],
                  eval_idx: int) -> tuple:
    """max() over J1 eval candidates: dev Delta^free, then LOWER false fire,
    then EARLIER checkpoint (docs/21 SS4)."""
    pf = 1.0 if p_fire_nonclean is None else float(p_fire_nonclean)
    return (float(delta_free), -pf, -int(eval_idx))


class A3EPhases:
    """3-phase state machine. Feed one metrics dict per eval:
    F0 -> {'captured_rate': x}; L1 -> {'delta_teacher': x};
    J1 -> {'delta_free': x, 'ucb95': x}. Returns an event string or None.
    Terminal states: .failed (reason) or .passed_exit (J1 gate met)."""

    def __init__(self):
        self.phase = "F0"
        self.evals_in_phase = 0
        self.consec = 0
        self.stall = 0
        self.failed: Optional[str] = None
        self.passed_exit = False
        self.history: List[dict] = []

    def _log(self, event: str, **kw):
        self.history.append({"phase": self.phase,
                             "eval": self.evals_in_phase, "event": event,
                             **kw})

    def on_eval(self, metrics: Dict[str, float]) -> Optional[str]:
        if self.failed or self.passed_exit:
            return None
        self.evals_in_phase += 1
        if self.phase == "F0":
            ok = float(metrics["captured_rate"]) >= F0_EXIT
            self.consec = self.consec + 1 if ok else 0
            if self.consec >= CONSEC:
                self.phase, self.evals_in_phase, self.consec = "L1", 0, 0
                self._log("advance_L1")
                return "advance_L1"
            if self.evals_in_phase >= PHASE_MAX_EVALS["F0"]:
                self.failed = "F0_fire_bootstrap"
                self._log("fail", reason=self.failed)
                return "fail"
        elif self.phase == "L1":
            ok = float(metrics["delta_teacher"]) > DELTA_GATE
            self.consec = self.consec + 1 if ok else 0
            if self.consec >= CONSEC:
                # teacher released PERMANENTLY; fire unfreezes with a fresh
                # optimizer (caller acts on this event).
                self.phase, self.evals_in_phase, self.consec = "J1", 0, 0
                self._log("advance_J1_teacher_released")
                return "advance_J1"
            if self.evals_in_phase >= PHASE_MAX_EVALS["L1"]:
                self.failed = "L1_limiter_shaping"    # NO fire unfreeze
                self._log("fail", reason=self.failed)
                return "fail"
        else:                                          # J1
            ok = float(metrics["delta_free"]) > DELTA_GATE
            self.consec = self.consec + 1 if ok else 0
            if float(metrics.get("ucb95", 1.0)) < STALL_UCB:
                self.stall += 1
                if self.stall >= STALL_N:
                    self._log("stall_recorded")        # record only
            else:
                self.stall = 0
            if self.consec >= CONSEC:
                self.passed_exit = True
                self._log("J1_exit")
                return "J1_exit"
            if self.evals_in_phase >= PHASE_MAX_EVALS["J1"]:
                self._log("J1_cap")                    # sealed still judges
                return "J1_cap"
        return None

    def flags(self) -> dict:
        return dict(PHASE_FLAGS[self.phase])

    def state(self) -> dict:
        return {"phase": self.phase, "evals_in_phase": self.evals_in_phase,
                "consec": self.consec, "stall": self.stall,
                "failed": self.failed, "passed_exit": self.passed_exit}


class A3ESpawner:
    """Train-rollout spawn draws over the ADMISSIBLE d1 subset (24 draws)
    and the two d1-admissible witnesses (d0 anchors). Deterministic given
    the caller's rng. Eval NEVER uses this (eval = dev bundle episodes)."""

    def __init__(self, robust_bank: str, bank: str, validation: str):
        from shepherd.train import spawn_bank as _sb
        self._sb = _sb
        val = json.loads(pathlib.Path(validation).read_text())
        adm = set(val["admissible_matrix"].get("d1", []))
        if not adm:
            raise ValueError("no admissible d1 cells in validation verdict")
        self.adm_speeds = sorted(float(v[1:]) for v in adm)      # [16, 20]
        t0s = _sb.load_t0(robust_bank)
        self.t0 = [t for t in t0s if float(t.v) in self.adm_speeds]
        if len(self.t0) != len(adm):
            raise ValueError("witness set does not match admissible cells")
        bk = json.loads(pathlib.Path(bank).read_text())
        self.d1 = [e for e in bk["entries"]
                   if int(e["k"]) == 1
                   and float(e["spawn"]["att_speed"]) in self.adm_speeds]
        if len(self.d1) != 12 * len(adm):
            raise ValueError(f"expected {12 * len(adm)} admissible d1 draws, "
                             f"got {len(self.d1)}")

    def d0_spawn(self, rng: np.random.Generator) -> dict:
        t0 = self.t0[int(rng.integers(len(self.t0)))]
        return self._sb.spawn_from(t0, rng, sigma_pos=0.0, sigma_vel=0.0)

    def d1_spawn(self, rng: np.random.Generator,
                 sigma: float = D1_SIGMA) -> dict:
        e = self.d1[int(rng.integers(len(self.d1)))]["spawn"]
        L = (np.asarray(e["limiters"], float)
             + rng.normal(0.0, sigma, (len(e["limiters"]), 3)))
        return {"limiters": L,
                "limiter_v": np.asarray(e["limiter_v"], float).copy(),
                "att_p": (np.asarray(e["att_p"], float)
                          + rng.normal(0.0, sigma, 3)),
                "att_v": np.asarray(e["att_v"], float).copy(),
                "att_speed": float(e["att_speed"]),
                "src": "a3e_d1"}

    def spawn(self, phase: str, rng: np.random.Generator) -> dict:
        return self.d0_spawn(rng) if phase == "F0" else self.d1_spawn(rng)


# ===================== harvest -> rewind-v2 (docs/21 v0.3 SS5) =============
HARVEST_SEEDS = tuple(range(700, 750))       # reset band, CRN across sources
HARVEST_JIT_BASE = 300_000                   # + 1000*k + v  (k=1 spawns)
REWIND_SCREEN_SEEDS = tuple(range(750, 770))
REWIND_VAL_SEEDS = tuple(range(800, 900))
REWIND_JIT_BASE = 310_000                    # + 1000*k + v  (validation)
COMPARATOR_JIT_BASE = 320_000                # + 1000*k + v  (synthetic k=2)
REWIND_KS = (2, 4, 8)
REWIND_SIGMA = {2: 0.01, 4: 0.015, 8: 0.02}  # frozen stage ramp d2/d3/d4
DEDUP_TAUS = (0.05, 0.25, 0.05, 0.25)        # (lim_p, lim_v, att_p, att_v)
QUOTA, QUOTA_CAP, MIN_SOURCES = 4, 6, 2      # per (cell, k) source balance
TARGET, MIN_ACCEPT = 12, 8
RESTORE_ATOL = 1e-3                          # contract-matched restore gate
RT2_SIGMA, RT2_N, RT2_RNG = 0.005, 8, 212_121   # RT-2 fixed perturbation set
RT2_RATIO = 0.6                              # rt endpoint err < 0.6 * open


def make_rt_pfc_fn(rec_p, rec_v, rec_a, dt: float, c_p: float = 1.0,
                   c_d: float = 0.5, a_max: float = 30.0):
    """RT-PFC (docs/21 v0.3 SS5): a_i(t) = clip_norm(a_rec(t)
    + Kp*(p_rec(t) - p_i) + Kd*(v_rec(t) - v_i)), Kp = c_p/T_k^2,
    Kd = c_d/T_k, T_k = k*dt with k = len(rec_a). t = 0 is the SNAPSHOT
    moment; a_rec(0) is the action executed right after it; after the
    reference is exhausted -> terminal hold at (p_rec[k], v=0) -- all
    identical to make_pfc_fn except the reference source (recorded
    trajectory instead of the closed-form demo)."""
    from shepherd.train.pfc import _clip_norm, _lim_pv, dimensionless_gains
    P = np.asarray(rec_p, float)             # (k+1, N, 3)
    V = np.asarray(rec_v, float)
    A = np.asarray(rec_a, float)             # (k,   N, 3)
    k = len(A)
    if k == 0 or P.shape[0] != k + 1 or V.shape != P.shape:
        raise ValueError("recorded reference must be (k+1) states + k accels")
    Kp, Kd = dimensionless_gains(c_p, c_d, k, dt)
    n_lim = P.shape[1]
    cnt = {"t": 0}

    def rt_pfc(obs, flags):
        t = cnt["t"]
        cnt["t"] += 1
        acts = []
        for i in range(n_lim):
            p, v = _lim_pv(obs, i)
            if t < k:
                a = A[t, i] + Kp * (P[t, i] - p) + Kd * (V[t, i] - v)
            else:                                   # terminal hold
                a = Kp * (P[k, i] - p) + Kd * (-v)
            acts.append(_clip_norm(a, a_max).astype(np.float32))
        return acts

    return rt_pfc


def snapshot_times(fire_step: int, ks=REWIND_KS) -> Dict[int, int]:
    """t = F - k for the ks that exist (t >= 1: t=0 is the d1 spawn itself,
    already banked). All are pre-commit by construction (commit == F);
    asserted at harvest."""
    return {k: fire_step - k for k in ks if fire_step - k >= 1}


def state_dist2(a: dict, b: dict, taus=DEDUP_TAUS) -> float:
    """State-aware normalized squared distance (docs/21 v0.3 SS5). No
    permutation minimization: limiter index = fixed role/obs slot."""
    tp, tv, tap, tav = taus
    d = 0.0
    d += float(np.sum((np.asarray(a["limiters"], float)
                       - np.asarray(b["limiters"], float)) ** 2)) / tp ** 2
    d += float(np.sum((np.asarray(a["limiter_v"], float)
                       - np.asarray(b["limiter_v"], float)) ** 2)) / tv ** 2
    d += float(np.sum((np.asarray(a["att_p"], float)
                       - np.asarray(b["att_p"], float)) ** 2)) / tap ** 2
    d += float(np.sum((np.asarray(a["att_v"], float)
                       - np.asarray(b["att_v"], float)) ** 2)) / tav ** 2
    return d


def cand_sort_key(c: dict) -> tuple:
    """Deterministic candidate order: (cell, source, reset_seed, fire_step)."""
    return (str(c["cell"]), int(c["source"]), int(c["reset_seed"]),
            int(c["fire_step"]))


def dedup_candidates(cands: List[dict], taus=DEDUP_TAUS) -> List[dict]:
    """Merge d^2 < 1 within the SAME (cell, k) pool; representative = the
    lexicographically earliest (cand_sort_key). Input order irrelevant."""
    out: List[dict] = []
    for c in sorted(cands, key=cand_sort_key):
        if any(state_dist2(c["snapshot"], kept["snapshot"], taus) < 1.0
               for kept in out):
            continue
        out.append(c)
    return out


def select_source_balanced(cands: List[dict], target: int = TARGET,
                           min_accept: int = MIN_ACCEPT, quota: int = QUOTA,
                           cap: int = QUOTA_CAP,
                           min_sources: int = MIN_SOURCES) -> dict:
    """Per-(cell, k) selection (docs/21 v0.3 SS5): base quota per source in
    source order, then deficit filled lexicographically subject to the
    single-source cap; k is MISSING unless >= min_accept accepted AND
    >= min_sources sources contribute."""
    by_src: Dict[int, List[dict]] = {}
    for c in sorted(cands, key=cand_sort_key):
        by_src.setdefault(int(c["source"]), []).append(c)
    picked: List[dict] = []
    counts: Dict[int, int] = {s: 0 for s in by_src}
    for s in sorted(by_src):                     # base quota
        take = by_src[s][:quota]
        picked += take
        counts[s] = len(take)
    for c in sorted(cands, key=cand_sort_key):   # deficit fill
        if len(picked) >= target:
            break
        s = int(c["source"])
        if c in picked or counts[s] >= cap:
            continue
        picked.append(c)
        counts[s] += 1
    picked = sorted(picked, key=cand_sort_key)[:target]
    srcs = {int(c["source"]) for c in picked}
    ok = len(picked) >= min_accept and len(srcs) >= min_sources
    return {"accepted": picked if ok else [],
            "missing": not ok,
            "reason": (None if ok else
                       ("sources<2" if len(srcs) < min_sources
                        else "below_min_accept")),
            "n_candidates": len(cands), "per_source": counts}
