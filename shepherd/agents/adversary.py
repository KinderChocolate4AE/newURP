"""Reactive, goal-constrained, evasive adversary (scripted M2 keystone attacker).

Closed-loop, state-consuming: a forward drive toward the protected point, a
bounded lateral dodge away from the predicted net center / finisher line, and a
HARD repulsion out of the kamikaze limiter kill-radii. The lateral reaction is
amplified once the finisher's commit bit flips (react_on_commit) -- this is the
deploy-delay reachable-set escape attempt (S8 channel (i)), NOT a strategic
signaling response (S4): the attacker just sees a physical commitment.

No loiter / bait / self-play / deception here (that richer adversary = S13,
deferred). Pure numpy; imports nothing from torch / pettingzoo / a backend.
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


def scripted_adversary_action(p_att, v_att, *, target, net_center, finisher_p,
                              limiters, kill_radius, a_att_max, omega_att_max,
                              v_nominal, dt, committed=False, react_on_commit=True,
                              a_lat_max=None, repel_margin=1.5):
    """Return {"a": accel(3), "e_cmd": heading(3)} for the scripted attacker.

    - forward: P-drive of velocity toward v_nominal * dir(target).
    - dodge:   lateral accel (|.| <= a_lat_max) away from the net center,
               perpendicular to the approach, amplified after commit.
    - repel:   hard push out of any limiter kill-radius (within repel_margin*kr).
    - clamp:   |a| <= a_att_max; heading turn <= omega_att_max*dt (slew enforced
               by the backend; e_cmd is the desired heading).
    """
    p_att = np.asarray(p_att, float)
    v_att = np.asarray(v_att, float)
    if a_lat_max is None:
        a_lat_max = a_att_max
    fwd = _unit(target - p_att, v_att)

    # forward drive: regulate ONLY the forward speed component (do NOT cancel
    # lateral velocity -- that would kill the dodge). P-control along fwd.
    v_fwd = float(v_att @ fwd)
    a_fwd = 4.0 * (v_nominal - v_fwd) * fwd

    # lateral dodge: perpendicular-to-approach component pointing away from net center
    to_net = _unit(net_center - p_att, fwd)
    off = (p_att - net_center)
    lateral = off - (off @ to_net) * to_net          # component perpendicular to net line
    dodge_dir = _unit(lateral, _unit(np.cross(fwd, [0, 0, 1.0]), [0, 1.0, 0]))
    # Proactive lateral dodge fires only AFTER the finisher commits (the deploy-delay
    # escape attempt). Before commit the attacker flies straight in (still repelled
    # from kill-radii) -- this keeps the at-commit reachable-set geometry clean.
    amp = 1.8 if (committed and react_on_commit) else 0.0
    a_dodge = amp * a_lat_max * dodge_dir

    # hard repulsion out of limiter kill-radii
    a_rep = np.zeros(3)
    if limiters is not None and kill_radius > 0:
        L = np.asarray(limiters, float).reshape(-1, 3)
        for c in L:
            d = p_att - c
            dist = np.linalg.norm(d)
            if dist <= repel_margin * kill_radius:
                strength = (repel_margin * kill_radius - dist) / (repel_margin * kill_radius)
                a_rep += a_att_max * (1.0 + strength) * _unit(d, fwd)

    a_cmd = a_fwd + a_dodge + a_rep
    nrm = np.linalg.norm(a_cmd)
    if nrm > a_att_max and nrm > _EPS:
        a_cmd = a_cmd * (a_att_max / nrm)

    e_cmd = _unit(v_att + a_cmd * dt, fwd)
    return {"a": a_cmd, "e_cmd": e_cmd}
