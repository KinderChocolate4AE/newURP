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
