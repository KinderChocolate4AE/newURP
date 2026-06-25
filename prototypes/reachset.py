"""Attacker tau-reachable set + per-shot capture value v_shot  (newURP M2, S8 core).

Shaping-as-lever (scaffold S8): when the net-capturer commits at t, the attacker
— observing the commit (S4) — tries to ESCAPE the net's capture volume during the
deploy delay tau using its bounded-accel maneuver, while AVOIDING the kamikaze
path-limiters' explosive kill-radii (a no-go constraint). v_shot = P[attacker
still inside net volume at t+tau | best feasible escape]. Cheap limiters SHRINK
the attacker's feasible reachable set R_A; blocking escape directions drives R_A
into the net volume N -> v_shot up. Channel (a) escape-volume-shrink (NOT
'depletion' — attacker has only bounded accel; limiters constrain by no-go).

Pure numpy (no torch). Net volume geometry matches effectors.NetProjectile.
Physics params (tau, a_att_max, kill_radius, net geometry) are INJECTED.
"""
from __future__ import annotations
import numpy as np


def reachable_accels(a_att_max, n=2000, seed=0):
    """Uniform samples of attacker accel in the ball ||a|| <= a_att_max (3D).
    Includes the zero (straight-line) control. Single-segment constant-accel
    reachable-set approximation over tau."""
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-12
    mag = a_att_max * rng.uniform(0.0, 1.0, size=(n, 1)) ** (1.0 / 3.0)  # uniform-in-volume
    a = d * mag
    a[0] = 0.0
    return a


def _hits_limiter(x0, v0, a, tau, limiters, kill_radius, n_t=24):
    """True if the attacker parabola enters ANY limiter kill-radius over [0,tau]."""
    s = np.linspace(0.0, tau, n_t)[:, None]
    pts = x0[None, :] + v0[None, :] * s + 0.5 * a[None, :] * s ** 2   # (n_t,3)
    d = np.linalg.norm(pts[:, None, :] - limiters[None, :, :], axis=2)  # (n_t,L)
    return bool((d <= kill_radius).any())


def v_shot(x_att, v_att, *, tau, a_att_max, net_center, net_radius,
           limiters=None, kill_radius=0.0, n=2000, seed=0):
    """Per-shot capture value in [0,1].
    Returns v_shot_soft (frac of FEASIBLE reachable endpoints caught by the net)
    and v_shot_worst (1 iff NO feasible escape exists), plus diagnostics."""
    x_att = np.asarray(x_att, float); v_att = np.asarray(v_att, float)
    net_center = np.asarray(net_center, float)
    accels = reachable_accels(a_att_max, n, seed)
    endpoints = x_att[None, :] + v_att[None, :] * tau + 0.5 * accels * tau ** 2

    if limiters is not None and len(np.atleast_2d(limiters)) > 0 and kill_radius > 0:
        L = np.asarray(limiters, float).reshape(-1, 3)
        feasible = np.array([not _hits_limiter(x_att, v_att, a, tau, L, kill_radius)
                             for a in accels])
    else:
        feasible = np.ones(len(accels), bool)

    caught = np.linalg.norm(endpoints - net_center[None, :], axis=1) <= net_radius
    nf = int(feasible.sum())
    if nf == 0:
        return dict(v_shot_soft=1.0, v_shot_worst=1.0, n_feasible=0,
                    note="attacker boxed in (no feasible control)")
    fc = caught[feasible]
    return dict(v_shot_soft=float(fc.mean()),
                v_shot_worst=(1.0 if fc.all() else 0.0),
                n_feasible=nf, n_total=len(accels))


if __name__ == "__main__":
    # M2 early-sanity: does cheap-limiter shaping MOVE v_shot? (S8 lever test)
    tau, a_max = 0.4, 30.0
    x = np.array([0., 0., 0.]); v = np.array([20., 0., 0.])
    nc = x + v * tau                      # net aimed at straight-line predicted pos
    nr = 1.5                              # net radius < reachable radius (0.5*a*tau^2=2.4) -> escapes exist
    kr = 2.0                              # kamikaze kill-radius
    mid = x + v * (tau * 0.55)

    def ring(dirs):
        return np.array([mid + np.array(d) for d in dirs])

    scenarios = {
        "0 limiters": None,
        "2 (±y)":      ring([[0, 3.5, 0], [0, -3.5, 0]]),
        "4 (±y,±z)":   ring([[0, 3.5, 0], [0, -3.5, 0], [0, 0, 3.5], [0, 0, -3.5]]),
        "6 (+±y,±z,+x)": ring([[0,3.5,0],[0,-3.5,0],[0,0,3.5],[0,0,-3.5],[4.0,2.5,0],[4.0,-2.5,0]]),
    }
    print(f"tau={tau} a_att_max={a_max} reach_R={0.5*a_max*tau**2:.2f}m net_r={nr} kill_r={kr}")
    print(f"{'scenario':16s} {'v_shot_soft':>11s} {'v_shot_worst':>12s} {'n_feasible':>11s}")
    for name, lim in scenarios.items():
        r = v_shot(x, v, tau=tau, a_att_max=a_max, net_center=nc, net_radius=nr,
                   limiters=lim, kill_radius=kr)
        print(f"{name:16s} {r['v_shot_soft']:>11.3f} {r['v_shot_worst']:>12.0f} {r.get('n_feasible',''):>11}")
