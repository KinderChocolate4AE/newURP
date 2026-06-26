"""Scripted policies + baselines for the M2 shaping env (pure numpy, no torch).

Exercised in M2/L1:
  - hold_position_limiter   : the FIXED u_L^0 baseline (limiter does nothing).
                              This is the headline + COMA counterfactual baseline.
  - scripted_shaping_limiter: drives limiter i onto its escape-ring slot on the
                              attacker's ACTIVE lateral escape route (channel (i)).
  - scripted_finisher       : point the net axis at the predicted attacker endpoint;
                              fire ONLY on a clean v_shot threshold crossing.

Stubs (declared for the exchange-frontier comparison, NOT exercised in M2):
  no_shaping / selection_only / buy_nets -> raise NotImplementedError (S9/M3).
"""
from __future__ import annotations
import numpy as np

_EPS = 1e-12


def _unit(v, fallback=None):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < _EPS:
        return np.zeros(3) if fallback is None else np.asarray(fallback, float)
    return v / n


def _perp_basis(axis):
    """Two unit vectors spanning the plane perpendicular to `axis`."""
    a = _unit(axis, [1.0, 0.0, 0.0])
    ref = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(a, ref), [0.0, 1.0, 0.0])
    w = _unit(np.cross(a, u), [0.0, 0.0, 1.0])
    return u, w


def hold_position_limiter():
    """u_L^0: no acceleration, hold heading. The fixed baseline action (Box(4))."""
    return np.zeros(4, dtype=np.float32)            # accel(3)=0, pressure(1)=0


def ring_slot(i, n_limiters, center, approach_dir, r_ring):
    """Slot for limiter i on the escape ring: a circle of radius r_ring in the
    plane perpendicular to the attacker's approach, centered at `center`."""
    u, w = _perp_basis(approach_dir)
    ang = 2.0 * np.pi * (i / max(n_limiters, 1))
    return np.asarray(center, float) + r_ring * (np.cos(ang) * u + np.sin(ang) * w)


def scripted_shaping_limiter(i, n_limiters, p_lim, v_lim, p_att, v_att, *, tau, a_max,
                             r_ring, dt, pressure=1.0, kp=8.0, kd=4.0):
    """Drive limiter i onto its slot on the predicted-ENDPOINT escape shell (where
    the lateral escapes land), closing channel (i). PD control (kd damps overshoot
    so the limiter SETTLES on the shell instead of orbiting). Returns a Box(4)
    action: accel(3) + kill-radius pressure(1)."""
    endpoint = np.asarray(p_att, float) + np.asarray(v_att, float) * tau
    slot = ring_slot(i, n_limiters, endpoint, v_att, r_ring)
    err = slot - np.asarray(p_lim, float)
    a_cmd = kp * err - kd * np.asarray(v_lim, float)        # PD toward the slot
    nrm = np.linalg.norm(a_cmd)
    if nrm > a_max and nrm > _EPS:
        a_cmd = a_cmd * (a_max / nrm)
    return np.array([a_cmd[0], a_cmd[1], a_cmd[2], float(pressure)], dtype=np.float32)


def scripted_finisher(p_fin, p_att, v_att, *, tau, clean_threshold_crossed):
    """Point the net axis at the predicted attacker endpoint; fire (logit>0.5)
    ONLY when the env reports a CLEAN v_shot threshold crossing. The FSM still
    enforces irreversibility + the single fire gate. Returns Box(5):
    net-axis target(3) + slew(1) + fire-logit(1)."""
    endpoint = np.asarray(p_att, float) + np.asarray(v_att, float) * tau
    axis = _unit(endpoint - np.asarray(p_fin, float), [1.0, 0.0, 0.0])
    fire_logit = 1.0 if clean_threshold_crossed else 0.0
    return np.array([axis[0], axis[1], axis[2], 1.0, fire_logit], dtype=np.float32)


# --- stubs (exchange-frontier comparison; NOT exercised in M2) --------------
def no_shaping(*a, **k):
    raise NotImplementedError("no_shaping is an S9/M3 exchange-frontier baseline (not M2).")


def selection_only(*a, **k):
    raise NotImplementedError("selection_only is an S9/M3 exchange-frontier baseline (not M2).")


def buy_nets(*a, **k):
    raise NotImplementedError("buy_nets is an S9/M3 exchange-frontier baseline (not M2).")
