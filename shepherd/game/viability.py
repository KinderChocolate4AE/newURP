"""Capture-viability v_shot (THE GOAL, sim-agnostic, pure numpy).

v_shot(x, u_limiters) = P[attacker still inside the net deployment volume at
t + tau_deploy | its best feasible escape], where cheap kamikaze limiters' kill-
radii impose a no-go that SHRINKS the attacker's tau-reachable set R_A. This is
the S8 shaping-as-lever core (channel (i) escape reachable-set compression).

Faithful numpy port of prototypes/reachset.py, extended with:
  - SE(3)-aware judge: net_radius SPHERE (point_mass) OR a finisher-pointing CONE
    (se3_cone: apex T_F, axis n_F = R_F.e_net, half-angle theta_net, axial band)
    -> S5 "can the finisher make a net volume in THAT attitude", not just "in range".
  - reduced-attitude attacker turn limit: anisotropic R_A via a heading cone of
    half-angle ~ omega_att_max * tau (turn_limited=False = the full ball / port path).
  - R4 boxed_in SPLIT: n_feasible==0 (limiter-blocked / boxed) is reported as a
    SEPARATE defence signal (p_limiter_blocked), NOT a clean net-shot threshold
    crossing. Do not count boxed_in as a clean capture.
  - shared-sample COMA hook: _v_shot_with_accels(accels, ...) evaluates a FIXED
    accel sample so commit-4 can reuse one sample across full + counterfactual
    rollouts for common-random-number exact differencing.

PORT FIDELITY: judge="point_mass" + attacker_turn_limited=False at seed=0
reproduces prototypes/reachset.py v_shot bit-for-bit (same RNG, same n_t=24
substep collision, same two-tier soft/worst output).

torch-free, backend-free, PettingZoo-free.

TODO(6-DOF): promote se3_cone to a full SE(3) reachable-set judge (attitude/rate
limits on the net axis); keep this interface sim-agnostic.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

_EPS = 1e-12


@dataclass(frozen=True)
class VShotResult:
    """Two-tier capture value + R4 limiter-block split.

    v_shot_soft       : mean(caught) among FEASIBLE escapes (prob. interpretation).
    v_shot_worst      : 1.0 iff EVERY feasible escape is caught (robust / worst-case).
    n_feasible        : # accel samples that survive the no-go (limiter + turn) filter.
    n_total           : # accel samples drawn.
    boxed_in          : n_feasible == 0 -> attacker has no feasible control. This is
                        a LIMITER-BLOCK / containment signal, NOT a clean net-shot.
    p_feasible        : n_feasible / n_total.
    p_limiter_blocked : 1 - p_feasible (no-go fraction; under turn-limit it also
                        includes maneuver-infeasible directions).
    judge             : "point_mass" | "se3_cone".
    seed              : RNG seed used for the accel sample.
    """
    v_shot_soft: float
    v_shot_worst: float
    n_feasible: int
    n_total: int
    boxed_in: bool
    p_feasible: float
    p_limiter_blocked: float
    judge: str
    seed: int


def reachable_accels(a_att_max, n=2000, seed=0):
    """Uniform-in-ball attacker accel samples (3D), zero-control at index 0.

    IDENTICAL RNG sequence to prototypes/reachset.py (default_rng(seed); normal
    directions; magnitude = a_att_max * uniform(0,1)**(1/3) for uniform-in-volume).
    Single-segment constant-accel reachable-set approximation over tau.
    """
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True) + _EPS
    mag = a_att_max * rng.uniform(0.0, 1.0, size=(n, 1)) ** (1.0 / 3.0)  # uniform-in-volume
    a = d * mag
    a[0] = 0.0
    return a


def _feasible_limiter(x0, v0, accels, tau, limiters, kill_radius, n_t=24):
    """Boolean mask: True iff the attacker parabola NEVER enters any limiter
    kill-radius over [0, tau] (n_t=24 substeps, matching the prototype)."""
    if limiters is None or kill_radius <= 0:
        return np.ones(len(accels), bool)
    L = np.asarray(limiters, float).reshape(-1, 3)
    if len(L) == 0:
        return np.ones(len(accels), bool)
    s = np.linspace(0.0, tau, n_t)                          # (n_t,)
    # pts: (n_accel, n_t, 3)
    pts = (x0[None, None, :]
           + v0[None, None, :] * s[None, :, None]
           + 0.5 * accels[:, None, :] * (s ** 2)[None, :, None])
    d = np.linalg.norm(pts[:, :, None, :] - L[None, None, :, :], axis=3)  # (n_accel,n_t,L)
    hits = (d <= kill_radius).any(axis=(1, 2))
    return ~hits


def _feasible_turn(accels, e_att, omega_att_max, tau):
    """Boolean mask for the reduced-attitude attacker turn limit: reject accel
    directions outside the cone of half-angle ~ omega_att_max*tau around heading
    e_att. Zero-control (||a||~0) is always feasible (straight-line)."""
    e = np.asarray(e_att, float)
    ne = np.linalg.norm(e)
    if ne < _EPS:
        return np.ones(len(accels), bool)
    e = e / ne
    half_angle = float(omega_att_max) * float(tau)
    norms = np.linalg.norm(accels, axis=1)
    cos_a = np.where(norms < _EPS, 1.0, (accels @ e) / (norms + _EPS))
    cos_a = np.clip(cos_a, -1.0, 1.0)
    ang = np.arccos(cos_a)
    feas = ang <= half_angle
    feas[norms < _EPS] = True                               # zero-control always allowed
    return feas


def _caught_point_mass(endpoints, net_center, net_radius):
    nc = np.asarray(net_center, float)
    return np.linalg.norm(endpoints - nc[None, :], axis=1) <= float(net_radius)


def _caught_se3_cone(endpoints, net_apex, n_F, theta_net, range_min, range_max):
    """Capture iff the endpoint lies inside the finisher net cone:
    apex T_F, axis n_F (= R_F.e_net), half-angle theta_net, axial band
    [range_min, range_max]. Zero/near-zero n_F is rejected (degenerate pointing).
    """
    apex = np.asarray(net_apex, float)
    n = np.asarray(n_F, float)
    nn = np.linalg.norm(n)
    if nn < _EPS:
        raise ValueError("se3_cone judge: net-pointing axis n_F is (near) zero "
                         "-> attitude undefined; reject this commit.")
    n = n / nn
    r = endpoints - apex[None, :]                            # apex -> endpoint
    rn = np.linalg.norm(r, axis=1)
    ax = r @ n                                               # axial coordinate along n_F
    if range_max is None:
        range_max = np.inf
    in_band = (ax >= float(range_min)) & (ax <= float(range_max))
    cos_a = np.where(rn < _EPS, 1.0, ax / (rn + _EPS))
    cos_a = np.clip(cos_a, -1.0, 1.0)
    ang = np.arccos(cos_a)
    in_cone = ang <= float(theta_net)
    at_apex = rn < _EPS                                      # endpoint at apex -> inside
    return (in_band & in_cone) | at_apex


def _v_shot_with_accels(accels, x_att, v_att, *, tau, judge="point_mass",
                        net_center=None, net_radius=None,
                        net_apex=None, n_F=None, theta_net=None,
                        range_min=0.0, range_max=None,
                        limiters=None, kill_radius=0.0,
                        attacker_turn_limited=False, omega_att_max=None, e_att=None,
                        seed=0):
    """Evaluate v_shot for a FIXED accel sample (COMA / CRN hook).

    Separating sample-draw from evaluation lets commit-4 reuse ONE accel sample
    across the full rollout and the per-limiter counterfactual so D_i differences
    exactly (common random numbers).
    """
    x_att = np.asarray(x_att, float)
    v_att = np.asarray(v_att, float)
    n_total = len(accels)
    endpoints = x_att[None, :] + v_att[None, :] * tau + 0.5 * accels * tau ** 2

    feasible = _feasible_limiter(x_att, v_att, accels, tau, limiters, kill_radius)
    if attacker_turn_limited:
        if omega_att_max is None:
            raise ValueError("attacker_turn_limited=True requires omega_att_max.")
        heading = v_att if e_att is None else e_att
        feasible = feasible & _feasible_turn(accels, heading, omega_att_max, tau)

    if judge == "point_mass":
        if net_center is None or net_radius is None:
            raise ValueError("judge='point_mass' requires net_center and net_radius.")
        caught = _caught_point_mass(endpoints, net_center, net_radius)
    elif judge == "se3_cone":
        if net_apex is None or n_F is None or theta_net is None:
            raise ValueError("judge='se3_cone' requires net_apex, n_F, theta_net.")
        caught = _caught_se3_cone(endpoints, net_apex, n_F, theta_net,
                                  range_min, range_max)
    else:
        raise ValueError(f"unknown judge {judge!r} (use 'point_mass' or 'se3_cone').")

    nf = int(feasible.sum())
    p_feasible = nf / n_total if n_total else 0.0
    if nf == 0:
        # R4: boxed-in / limiter-blocked. v_shot_soft=1.0 only for CONTINUITY of the
        # surrogate -- this is a CONTAINMENT signal, NOT a clean net-shot crossing.
        return VShotResult(v_shot_soft=1.0, v_shot_worst=1.0, n_feasible=0,
                           n_total=n_total, boxed_in=True, p_feasible=0.0,
                           p_limiter_blocked=1.0, judge=judge, seed=seed)
    fc = caught[feasible]
    return VShotResult(
        v_shot_soft=float(fc.mean()),
        v_shot_worst=(1.0 if fc.all() else 0.0),
        n_feasible=nf,
        n_total=n_total,
        boxed_in=False,
        p_feasible=float(p_feasible),
        p_limiter_blocked=float(1.0 - p_feasible),
        judge=judge,
        seed=seed,
    )


def v_shot(x_att, v_att, *, tau, a_att_max, judge="point_mass",
           net_center=None, net_radius=None,
           net_apex=None, n_F=None, theta_net=None, range_min=0.0, range_max=None,
           limiters=None, kill_radius=0.0,
           attacker_turn_limited=False, omega_att_max=None, e_att=None,
           n=2000, seed=0):
    """Per-shot capture value in [0,1] -> VShotResult.

    Draws the attacker reachable accel sample then delegates to
    _v_shot_with_accels. point_mass + attacker_turn_limited=False at a given seed
    reproduces prototypes/reachset.py exactly.
    """
    accels = reachable_accels(a_att_max, n, seed)
    return _v_shot_with_accels(
        accels, x_att, v_att, tau=tau, judge=judge,
        net_center=net_center, net_radius=net_radius,
        net_apex=net_apex, n_F=n_F, theta_net=theta_net,
        range_min=range_min, range_max=range_max,
        limiters=limiters, kill_radius=kill_radius,
        attacker_turn_limited=attacker_turn_limited,
        omega_att_max=omega_att_max, e_att=e_att, seed=seed,
    )
