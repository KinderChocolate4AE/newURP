"""Phase 0-d step-1 measurement instruments (docs/18 v0.2, RATIFIED
2026-07-17): Gate A PFC + Gate B reference-free controllers + closed forms.

Gate A -- PFC (privileged feasibility controller, docs/18 SS5; the arm
formerly sketched as "demo_cl"): closed-loop reference tracker

    a_i(t) = clip( a_demo_i(t) + Kp * (p_ref_i(t) - p_i(t))
                                + Kd * (v_ref_i(t) - v_i(t)) , |a| <= a_max )

with DIMENSIONLESS global gains Kp = c_p / T_k^2, Kd = c_d / T_k,
T_k = k * dt (one (c_p, c_d) pair across all k; per-cell tuning is
forbidden -- docs/18 SS5). The reference trajectory integrates the bank
entry's NOMINAL spawn through its demo accels, so the controller cancels
the bundle's position jitter (open-loop replay preserves it verbatim).
PRIVILEGED by construction: the reference (and its time index) is bank
metadata the actor observation never carries. This is a feasibility
*instrument* -- it must never be wired into a training reward/rollout.

Gate B -- observation-realizable, reference-free controllers (docs/18 SS5;
ratified status (ii): warned cells stay in the training bank but are
excluded from confirmatory method-competence claims). Constructors take NO
bank/demo/witness arguments -- they may read only obs-derivable signals:
own limiter pos/vel and the attacker block of the frozen 63-dim obs
(limiter i: obs[9i:9i+3] pos, obs[9i+3:9i+6] vel; attacker: pos
obs[9*N_max+9 : +3], vel obs[9*N_max+12 : +3]). The '3rd-party review's
"limiter-target relative" example is deliberately narrowed here: any
"target" must be derived from the ATTACKER state present in obs -- witness
slot coordinates would be privilege leakage (docs/18 SS9, partial-adopt).

Closed forms (docs/18 SS1; unit-tested in tests/test_a3d_pfc.py against an
integrator replication -- the k=1 2x table error class):

    R(v0, k) = v0 * dt * (k - 1) / 2     spawn offset from the witness slot
    O(v0, k) = v0 * dt * (k + 1) / 2     zero-action coast overshoot at t=0

Integrator semantics everywhere: v' = v + a*dt, THEN p' = p + v'*dt
(AnalyticBackend / a3d_sbe_bank.py). torch-free.
"""
from __future__ import annotations

from typing import Callable, List

import numpy as np

N_LIM = 4          # frozen layout (configs/m2_l2_train.yaml n_lim)
N_MAX = 4          # obs limiter slots (env.py N_max)
A_MAX = 30.0       # limiter accel budget (physics.a_lim_max)
ATT_P0 = 9 * N_MAX + 9        # attacker pos offset in the 63-dim obs
ATT_V0 = ATT_P0 + 3           # attacker vel offset


# ------------------------------------------------------------ closed forms --
def spawn_offset(v0: float, k: int, dt: float) -> float:
    """R = distance of the t-k spawn from the witness slot (docs/18 SS1)."""
    return float(v0) * float(dt) * (int(k) - 1) / 2.0


def zero_overshoot(v0: float, k: int, dt: float) -> float:
    """O = zero-action coast overshoot past the slot at t=0 (docs/18 SS1)."""
    return float(v0) * float(dt) * (int(k) + 1) / 2.0


def dimensionless_gains(c_p: float, c_d: float, k: int, dt: float):
    """Kp = c_p/T^2, Kd = c_d/T with T = k*dt (3rd-party adoption)."""
    T = int(k) * float(dt)
    if T <= 0:
        raise ValueError(f"k*dt must be positive (k={k}, dt={dt})")
    return float(c_p) / (T * T), float(c_d) / T


# ------------------------------------------------------- reference rollout --
def reference_rollout(p0, v0, accels, dt: float):
    """Integrate (p0, v0) through accels with the backend semantics.

    Returns (P, V): arrays of shape (k+1, N, 3) -- index t is the state
    AFTER t movement steps (t=0 is the spawn). No velocity clipping: bank
    admission condition 4 guarantees clip-free demo profiles."""
    p = np.asarray(p0, float).copy()
    v = np.asarray(v0, float).copy()
    a = np.asarray(accels, float)
    P, V = [p.copy()], [v.copy()]
    for t in range(len(a)):
        v = v + a[t] * dt
        p = p + v * dt
        P.append(p.copy())
        V.append(v.copy())
    return np.stack(P), np.stack(V)


def _clip_norm(a: np.ndarray, a_max: float) -> np.ndarray:
    n = float(np.linalg.norm(a))
    if n > a_max and n > 0.0:
        return a * (a_max / n)
    return a


def _lim_pv(obs, i: int):
    o = np.asarray(obs, float)
    return o[9 * i: 9 * i + 3], o[9 * i + 3: 9 * i + 6]


# ------------------------------------------------------------- Gate A: PFC --
def make_pfc_fn(nominal_spawn: dict, demo_accels, dt: float,
                c_p: float, c_d: float, a_max: float = A_MAX,
                n_lim: int = N_LIM) -> Callable:
    """Per-episode PFC closure for the calibration harness ((obs, flags) ->
    [accel3 x n_lim]).

    nominal_spawn = the BANK entry's spawn (un-jittered limiters +
    limiter_v); demo_accels = (k, n_lim, 3). The internal step counter is
    reference time (privileged). After the reference is exhausted the
    controller holds the terminal reference (arrival point, zero velocity).
    """
    da = np.asarray(demo_accels, float)
    k = len(da)
    if k == 0:
        raise ValueError("empty demo_accels (k=0 has no arrival reference)")
    Kp, Kd = dimensionless_gains(c_p, c_d, k, dt)
    P_ref, V_ref = reference_rollout(nominal_spawn["limiters"],
                                     nominal_spawn["limiter_v"], da, dt)
    cnt = {"t": 0}

    def pfc(obs, flags, da=da, P_ref=P_ref, V_ref=V_ref, cnt=cnt) \
            -> List[np.ndarray]:
        t = cnt["t"]
        cnt["t"] += 1
        acts = []
        for i in range(n_lim):
            p, v = _lim_pv(obs, i)
            if t < k:
                a = (da[t, i]
                     + Kp * (P_ref[t, i] - p) + Kd * (V_ref[t, i] - v))
            else:                                   # terminal hold at slot
                a = Kp * (P_ref[k, i] - p) + Kd * (-v)
            acts.append(_clip_norm(a, a_max).astype(np.float32))
        return acts

    return pfc


# --------------------------------------------- Gate B: reference-free arms --
def make_lambda_brake_fn(lam: float, a_max: float = A_MAX,
                         n_lim: int = N_LIM) -> Callable:
    """a_i = -lam * v_i (norm-clipped). Obs-only; no bank arguments."""
    lam = float(lam)

    def lam_brake(obs, flags) -> List[np.ndarray]:
        acts = []
        for i in range(n_lim):
            _, v = _lim_pv(obs, i)
            acts.append(_clip_norm(-lam * v, a_max).astype(np.float32))
        return acts

    return lam_brake


def make_att_pd_fn(kp: float, kd: float, d_lead: float,
                   a_max: float = A_MAX, n_lim: int = N_LIM,
                   n_max: int = N_MAX) -> Callable:
    """PD toward an ATTACKER-derived lead point (obs-only; docs/18 SS5).

    target = att_p + d_lead * unit(att_v); a_i = kp*(target - p_i) - kd*v_i,
    norm-clipped. Gains here are plain dimensional constants from a small
    preregistered grid (k is bank metadata the obs does not carry, so the
    dimensionless T_k scaling is NOT available to Gate B by construction).
    """
    ap0, av0 = 9 * n_max + 9, 9 * n_max + 12

    def att_pd(obs, flags) -> List[np.ndarray]:
        o = np.asarray(obs, float)
        att_p, att_v = o[ap0:ap0 + 3], o[av0:av0 + 3]
        nv = float(np.linalg.norm(att_v))
        tgt = att_p + (att_v / nv * d_lead if nv > 1e-9 else 0.0)
        acts = []
        for i in range(n_lim):
            p, v = _lim_pv(obs, i)
            acts.append(_clip_norm(kp * (tgt - p) - kd * v,
                                   a_max).astype(np.float32))
        return acts

    return att_pd


# ------------------------------------------------------------ bank helpers --
def nominal_from_bank(bank: dict, entry_idx: int) -> dict:
    """Bundle episodes carry entry_idx = index into bank['entries']
    (a3d_bundle_gen.build_bundle enumerates the bank in file order)."""
    return bank["entries"][int(entry_idx)]
