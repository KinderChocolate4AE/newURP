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


# ---------------------------------------------------------------------------- #
# S14 — conservative EXTREME-POINT reachable set.
#
# The single-segment sampler above holds ONE constant accel over the whole tau,
# drawn uniform-IN-BALL. Two problems make it read OPTIMISTICALLY:
#   (a) Free double integrator: the single-segment ball IS the exact reachable
#       endpoint set (max displacement-from-coast over ||a||<=a_max is a_max*tau^2/2
#       in any direction). But uniform-in-ball UNDER-SAMPLES the boundary sphere
#       ||a||=a_max -- exactly where the escapes live (the pure-forward a_max
#       overshoot that exits the cone in m2_clean_viability_demo). Fix: SAMPLE THE
#       BOUNDARY directly.
#   (b) A discrete closed-loop attacker re-plans piecewise: it DODGES limiters
#       with a dogleg the single parabola can't trace, and (turn-limited) CURVES
#       past the single fixed omega*tau heading cone by re-pointing each step. Fix:
#       BANG-BANG doglegs + max-rate TURN-CURVE sequences that sweep the full
#       +-omega*tau envelope.
#
# Soundness: over-approximating the attacker's reachable set can only find MORE
# escapes, never falsely claim containment. Boundary points lie ON the true free
# ball (exact); each per-segment turn step respects the true per-step limit
# omega*(tau/K) (sound). The conservative set is the UNION of the verbatim
# single-segment block (so it is a guaranteed SUPERSET -> reachability never
# shrinks, v_shot_worst is monotone non-increasing) with these extreme-point
# blocks. n_segments=1 stays the bit-exact single-segment legacy path (default),
# so the frozen port fidelity is preserved.
#
# POST-REVIEW CAVEAT (2026-06-28). "Never falsely claim containment" holds for the
# continuous reachable SET. The IMPLEMENTATION evaluates a FINITE witness sample of
# it (B1 + boundary/dogleg extremes), so v_shot_worst==1 means "no SAMPLED witness
# escaped", NOT a certified containment bound -- an escape can hide between sampled
# boundary directions. Treat the union as an ADVERSARIAL extreme-point witness set
# that REDUCES (not eliminates) the single-sample optimism. For the point-mass
# sphere with no limiters, sphere_containment_certificate() gives the EXACT
# worst-case answer in closed form; prefer it for the worst-case gate.
# ---------------------------------------------------------------------------- #
def _extreme_dirs(n_dir=32, seed=0, e_att=None):
    """Unit directions covering the sphere for boundary / extreme-point sampling.

    Deterministic core: the six axis-aligned +-x,+-y,+-z plus (if given) the
    +-heading e_att -- so the pure-forward a_max boundary endpoint is ALWAYS
    present (the deterministic overshoot demonstration). Then a Fibonacci-sphere
    quasi-uniform grid and a few rng directions for off-axis coverage."""
    base = [[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.],
            [0., -1., 0.], [0., 0., 1.], [0., 0., -1.]]
    dirs = [np.asarray(b, float) for b in base]
    if e_att is not None:
        e = np.asarray(e_att, float)
        ne = np.linalg.norm(e)
        if ne > _EPS:
            e = e / ne
            dirs.append(e)
            dirs.append(-e)
    m = max(int(n_dir), 0)
    if m > 0:
        i = np.arange(m) + 0.5
        phi = np.arccos(1.0 - 2.0 * i / m)                  # Fibonacci sphere
        gold = np.pi * (1.0 + 5.0 ** 0.5)
        th = gold * i
        fib = np.stack([np.sin(phi) * np.cos(th),
                        np.sin(phi) * np.sin(th), np.cos(phi)], axis=1)
        dirs.extend(fib)
        rng = np.random.default_rng((int(seed), 0xB0DE))    # distinct stream
        rd = rng.normal(size=(m, 3))
        rd /= np.linalg.norm(rd, axis=1, keepdims=True) + _EPS
        dirs.extend(rd)
    D = np.asarray(dirs, float)
    D /= np.linalg.norm(D, axis=1, keepdims=True) + _EPS
    return D


def _boundary_accels(a_att_max, dirs):
    """Single-segment controls at the EXACT boundary ||a||=a_max of the free
    reachable ball (constant max-accel in each extreme direction), shaped (m,1,3)
    so they flow through the piecewise integrator as degenerate K=1 segments. For
    the free / point_mass / cone case (no turn limit) this is the workhorse: the
    pure-forward boundary endpoint IS the overshoot uniform-in-ball misses."""
    D = np.asarray(dirs, float)
    return (float(a_att_max) * D)[:, None, :]


def _bangbang_segments(a_att_max, dirs, n_segments, second_dirs=None):
    """K-segment max-magnitude (||a||=a_max) DOGLEG controls: the first ceil(K/2)
    segments along d1, the remainder along d2. A dogleg dodges a limiter the
    single parabola can't (lateral then forward) and curves when d1!=d2 -> it
    expands the feasible reachable set (sound: strictly more reachable points)."""
    D = np.asarray(dirs, float)
    if second_dirs is None:
        second_dirs = np.array([[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.],
                                [0., -1., 0.], [0., 0., 1.], [0., 0., -1.]], float)
    S = np.asarray(second_dirs, float)
    K = max(int(n_segments), 2)
    k1 = (K + 1) // 2
    if len(D) == 0 or len(S) == 0:
        return np.zeros((0, K, 3))
    controls = np.empty((len(D) * len(S), K, 3), float)
    idx = 0
    for d1 in D:
        for d2 in S:
            controls[idx, :k1] = a_att_max * d1
            controls[idx, k1:] = a_att_max * d2
            idx += 1
    return controls


def _turn_curve_segments(v0, omega, tau, a_att_max, n_segments, e_att=None,
                         n_azimuth=8, safety=0.999):
    """Max-rate turning sequences (turn-limited attacker only). Each segment's
    accel sits at the omega*h cone EDGE of the CURRENT heading -- it carries a
    component PERPENDICULAR to v that actually rotates the heading (accel purely
    along v only grows speed, never curves). Every segment stays within
    omega*h (= omega*tau/K) of its current heading, so it passes the per-segment
    turn check, yet the heading SWEEPS the full +-omega*tau envelope -- reaching
    endpoints the single fixed omega*tau cone rejects. Sound: each step respects
    the true per-step turn limit. Returns (n_azimuth, K, 3).

    HONEST CAVEAT (current model): _feasible_turn is an ACCEL-cone proxy (accel
    within omega*tau of the frozen heading), which already OVER-covers physical
    turning whenever a_max/speed < omega (accel-limited, not rate-limited). Under
    that proxy every curve endpoint lands INSIDE the single-segment turn-limited
    set, so this block is a sound no-op for capture today. It becomes load-bearing
    once _feasible_turn is replaced by a true turn-RATE-limited dynamics (the
    curve's velocity-rotation lateral term then escapes the accel cone)."""
    v0 = np.asarray(v0, float)
    K = int(n_segments)
    if K < 1:
        return np.zeros((0, 1, 3))
    h0 = np.asarray(e_att, float) if e_att is not None else v0
    nh = np.linalg.norm(h0)
    speed0 = np.linalg.norm(v0)
    if nh < _EPS or speed0 < _EPS:
        return np.zeros((0, K, 3))           # heading / speed undefined -> no curve
    h0 = h0 / nh
    h = float(tau) / K
    edge = float(omega) * h * float(safety)  # just inside the per-segment cone edge
    ca, sa = np.cos(edge), np.sin(edge)
    ref = np.array([1., 0., 0.]) if abs(h0[0]) < 0.9 else np.array([0., 1., 0.])
    u = ref - (ref @ h0) * h0
    u /= np.linalg.norm(u) + _EPS
    w = np.cross(h0, u)
    controls = np.empty((int(n_azimuth), K, 3), float)
    for k in range(int(n_azimuth)):
        phi = 2.0 * np.pi * k / int(n_azimuth)
        p0 = np.cos(phi) * u + np.sin(phi) * w               # fixed turn-plane perp
        v = v0.copy()
        for j in range(K):
            head = v / (np.linalg.norm(v) + _EPS)
            p = p0 - (p0 @ head) * head                      # perp within plane(head)
            pn = np.linalg.norm(p)
            if pn < _EPS:
                a = a_att_max * head                         # degenerate -> straight
            else:
                a = a_att_max * (ca * head + sa * (p / pn))  # at the cone edge
            controls[k, j] = a
            v = v + a * h
    return controls


def _caught_mask(endpoints, judge, *, net_center, net_radius,
                 net_apex, n_F, theta_net, range_min, range_max):
    """Dispatch the capture judge over a batch of endpoints (same semantics as
    _v_shot_with_accels, factored so the union path can reuse it)."""
    if judge == "point_mass":
        if net_center is None or net_radius is None:
            raise ValueError("judge='point_mass' requires net_center and net_radius.")
        return _caught_point_mass(endpoints, net_center, net_radius)
    if judge == "se3_cone":
        if net_apex is None or n_F is None or theta_net is None:
            raise ValueError("judge='se3_cone' requires net_apex, n_F, theta_net.")
        return _caught_se3_cone(endpoints, net_apex, n_F, theta_net, range_min, range_max)
    raise ValueError(f"unknown judge {judge!r} (use 'point_mass' or 'se3_cone').")


def _segments_endpoints_feasible(x0, v0, seg_accels, *, tau, limiters, kill_radius,
                                 attacker_turn_limited, omega_att_max, e_att, n_t=24):
    """Integrate piecewise-constant controls and return (endpoints, feasible).

    - Trajectory: K segments of length h=tau/K; within each, exact constant-accel
      kinematics, n_t substeps for the limiter no-go test on the ACTUAL dogleg
      path (not a single parabola) -> a dodge that the single segment can't make.
    - Turn limit: each segment's accel must lie within omega_att_max*h of the
      CURRENT heading (the evolving velocity; for segment 0, e_att if given). The
      heading rotates segment-to-segment, so the attacker can CURVE beyond the
      single fixed cone of half-angle omega_att_max*tau. Zero accel is always
      allowed (straight coast)."""
    seg_accels = np.asarray(seg_accels, float)
    n, K, _ = seg_accels.shape
    h = tau / K
    x = np.repeat(np.asarray(x0, float)[None, :], n, axis=0)
    v = np.repeat(np.asarray(v0, float)[None, :], n, axis=0)
    s = np.linspace(0.0, h, n_t)                                # within-segment substeps
    half = (float(omega_att_max) * h) if attacker_turn_limited else None
    feasible_turn = np.ones(n, bool)
    seg_pts = []
    for j in range(K):
        a = seg_accels[:, j, :]                                 # (n,3)
        if attacker_turn_limited:
            if omega_att_max is None:
                raise ValueError("attacker_turn_limited=True requires omega_att_max.")
            if j == 0 and e_att is not None:
                head = np.repeat(np.asarray(e_att, float)[None, :], n, axis=0)
            else:
                head = v
            an = np.linalg.norm(a, axis=1)
            hn = np.linalg.norm(head, axis=1)
            denom = an * hn
            cos_a = np.where(denom < _EPS, 1.0,
                             np.einsum("ij,ij->i", a, head) / (denom + _EPS))
            cos_a = np.clip(cos_a, -1.0, 1.0)
            ok = (np.arccos(cos_a) <= half) | (an < _EPS)       # zero-accel always feasible
            feasible_turn &= ok
        seg_pts.append(x[:, None, :] + v[:, None, :] * s[None, :, None]
                       + 0.5 * a[:, None, :] * (s ** 2)[None, :, None])
        x = x + v * h + 0.5 * a * h * h                         # advance to segment end
        v = v + a * h
    endpoints = x

    if limiters is None or kill_radius <= 0:
        feasible_lim = np.ones(n, bool)
    else:
        L = np.asarray(limiters, float).reshape(-1, 3)
        if len(L) == 0:
            feasible_lim = np.ones(n, bool)
        else:
            pts = np.concatenate(seg_pts, axis=1)               # (n, K*n_t, 3)
            d = np.linalg.norm(pts[:, :, None, :] - L[None, None, :, :], axis=3)
            feasible_lim = ~(d <= kill_radius).any(axis=(1, 2))
    return endpoints, feasible_lim & feasible_turn


def _assemble(feasible, caught, n_total, judge, seed):
    """Build a VShotResult from a feasible mask + caught mask (R4 boxed split)."""
    nf = int(feasible.sum())
    p_feasible = nf / n_total if n_total else 0.0
    if nf == 0:
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


def _union_sets(x_att, v_att, *, tau, a_att_max, judge,
                net_center, net_radius, net_apex, n_F, theta_net,
                range_min, range_max, limiters, kill_radius,
                attacker_turn_limited, omega_att_max, e_att,
                n, n_segments, seed, n_dir=32):
    """Build the conservative UNION reachable set as (endpoints, feasible, caught).

    Block 1 is the VERBATIM single-segment uniform-in-ball reachable set (same math
    as _v_shot_with_accels) -- concatenated first, so the union is a guaranteed
    SUPERSET of the legacy set and v_shot_worst is monotone non-increasing.

    The extreme-point blocks then EXPOSE the escapes uniform-in-ball misses:
      - boundary spheres (||a||=a_max): the pure-forward overshoot workhorse,
      - bang-bang doglegs: dodge a limiter / curve when the two legs differ,
      - max-rate turn curves (turn-limited only): sweep the +-omega*tau envelope.
    Each extreme block is integrated through _segments_endpoints_feasible and the
    whole stack is judged with _caught_mask. Factored out of
    _v_shot_multiseg_union so tests can assert the subset relationship directly."""
    x_att = np.asarray(x_att, float)
    v_att = np.asarray(v_att, float)
    heading = v_att if e_att is None else np.asarray(e_att, float)

    # --- Block 1: verbatim single-segment uniform-in-ball (superset guarantee) ---
    accels1 = reachable_accels(a_att_max, n, seed)
    end1 = x_att[None, :] + v_att[None, :] * tau + 0.5 * accels1 * tau ** 2
    feas1 = _feasible_limiter(x_att, v_att, accels1, tau, limiters, kill_radius)
    if attacker_turn_limited:
        if omega_att_max is None:
            raise ValueError("attacker_turn_limited=True requires omega_att_max.")
        feas1 = feas1 & _feasible_turn(accels1, heading, omega_att_max, tau)
    end_blocks = [end1]
    feas_blocks = [feas1]

    dirs = _extreme_dirs(n_dir=n_dir, seed=seed, e_att=heading)

    def _add(seg_accels):
        if len(seg_accels) == 0:
            return
        ep, fe = _segments_endpoints_feasible(
            x_att, v_att, seg_accels, tau=tau, limiters=limiters, kill_radius=kill_radius,
            attacker_turn_limited=attacker_turn_limited, omega_att_max=omega_att_max,
            e_att=e_att)
        end_blocks.append(ep)
        feas_blocks.append(fe)

    _add(_boundary_accels(a_att_max, dirs))                  # boundary spheres (K=1)
    _add(_bangbang_segments(a_att_max, dirs, n_segments))    # doglegs
    if attacker_turn_limited:                                # max-rate turn curves
        _add(_turn_curve_segments(v_att, omega_att_max, tau, a_att_max, n_segments,
                                  e_att=e_att))

    endpoints = np.concatenate(end_blocks, axis=0)
    feasible = np.concatenate(feas_blocks, axis=0)
    caught = _caught_mask(endpoints, judge, net_center=net_center, net_radius=net_radius,
                          net_apex=net_apex, n_F=n_F, theta_net=theta_net,
                          range_min=range_min, range_max=range_max)
    return endpoints, feasible, caught


def _v_shot_multiseg_union(x_att, v_att, *, tau, a_att_max, judge,
                           net_center, net_radius, net_apex, n_F, theta_net,
                           range_min, range_max, limiters, kill_radius,
                           attacker_turn_limited, omega_att_max, e_att,
                           n, n_segments, seed):
    """v_shot over the conservative extreme-point union (see _union_sets). The
    union contains the single-segment feasible endpoints verbatim, so the feasible
    reachable set is a guaranteed superset: reachability does not shrink and
    v_shot_worst is conservatively non-increasing vs n_segments=1."""
    endpoints, feasible, caught = _union_sets(
        x_att, v_att, tau=tau, a_att_max=a_att_max, judge=judge,
        net_center=net_center, net_radius=net_radius, net_apex=net_apex, n_F=n_F,
        theta_net=theta_net, range_min=range_min, range_max=range_max,
        limiters=limiters, kill_radius=kill_radius,
        attacker_turn_limited=attacker_turn_limited, omega_att_max=omega_att_max,
        e_att=e_att, n=n, n_segments=n_segments, seed=seed)
    return _assemble(feasible, caught, len(endpoints), judge, seed)


def v_shot(x_att, v_att, *, tau, a_att_max, judge="point_mass",
           net_center=None, net_radius=None,
           net_apex=None, n_F=None, theta_net=None, range_min=0.0, range_max=None,
           limiters=None, kill_radius=0.0,
           attacker_turn_limited=False, omega_att_max=None, e_att=None,
           n=2000, seed=0, n_segments=1):
    """Per-shot capture value in [0,1] -> VShotResult.

    Draws the attacker reachable accel sample then delegates to
    _v_shot_with_accels. point_mass + attacker_turn_limited=False at a given seed
    reproduces prototypes/reachset.py exactly.

    n_segments (S14): 1 (default) = single constant-accel uniform-in-ball reachable
    set, BIT-EXACT with the frozen prototype (the legacy surrogate). n_segments>1 =
    conservative EXTREME-POINT reachable set -- the verbatim single-segment block
    UNIONED with boundary spheres (||a||=a_max overshoot), bang-bang doglegs, and
    (turn-limited) max-rate turn curves that sweep the +-omega*tau envelope. This
    is an over-approximation of the discrete closed-loop attacker (NOT just more MC
    samples): the feasible reachable set is a guaranteed superset, so v_shot stops
    under-bounding (v_shot_worst is conservatively non-increasing) and is the
    trustworthy capture signal. Keep 1 only to reproduce the legacy surrogate. NOTE (post-review): the
    union is a FINITE witness set, so worst==1 is not a formal containment
    certificate (see sphere_containment_certificate for the exact sphere bound).
    """
    if n_segments is None or int(n_segments) <= 1:
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
    return _v_shot_multiseg_union(
        x_att, v_att, tau=tau, a_att_max=a_att_max, judge=judge,
        net_center=net_center, net_radius=net_radius,
        net_apex=net_apex, n_F=n_F, theta_net=theta_net,
        range_min=range_min, range_max=range_max,
        limiters=limiters, kill_radius=kill_radius,
        attacker_turn_limited=attacker_turn_limited,
        omega_att_max=omega_att_max, e_att=e_att,
        n=n, n_segments=int(n_segments), seed=seed,
    )


# ---------------------------------------------------------------------------- #
# S14 / L2 -- PRECOMPUTED reachable UNION (build once, evaluate many layouts).
#
# The union's endpoints, per-witness trajectory, judge result (caught) and turn
# feasibility are ALL independent of the limiter layout (they depend only on the
# attacker state, the net/finisher pose and the seed). ONLY the limiter no-go
# feasibility depends on the layout. build_reachable_union() does the layout-
# independent work ONCE; eval_union_with_limiters() applies one layout's limiter
# mask. The env uses this for the headline + per-limiter COMA counterfactuals so all
# N+2 evaluations share ONE union -> common-random-numbers is MANIFEST (identical
# endpoints + caught; only the feasibility mask differs) and ~(N+2)x cheaper.
#
# eval_union_with_limiters(build_reachable_union(...), limiters, kr) is numerically
# IDENTICAL to v_shot(..., n_segments=K) (locked by tests/test_union_equiv).
# ---------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ReachableUnion:
    endpoints: object          # (M,3) all witness endpoints (B1 + extreme blocks)
    caught: object             # (M,) judge result (layout-independent)
    turn_feasible: object      # (M,) turn-limit mask (layout-independent)
    path_blocks: tuple         # per-block (n_b, T_b, 3) trajectory substeps
    block_sizes: tuple         # per-block witness counts (concat order == endpoints)
    n_total: int
    judge: str
    seed: int


def _single_seg_paths(x0, v0, accels, tau, n_t=24):
    """Parabola substeps for the single-segment block (matches _feasible_limiter)."""
    s = np.linspace(0.0, tau, n_t)
    return (x0[None, None, :] + v0[None, None, :] * s[None, :, None]
            + 0.5 * accels[:, None, :] * (s ** 2)[None, :, None])      # (n, n_t, 3)


def _seg_paths_turn(x0, v0, seg_accels, *, tau, attacker_turn_limited,
                    omega_att_max, e_att, n_t=24):
    """Layout-INDEPENDENT half of _segments_endpoints_feasible: endpoints, turn
    feasibility, and the trajectory substep points (for a later limiter test). No
    limiter logic here (so the result can be reused across layouts)."""
    seg_accels = np.asarray(seg_accels, float)
    n, K, _ = seg_accels.shape
    h = tau / K
    x = np.repeat(np.asarray(x0, float)[None, :], n, axis=0)
    v = np.repeat(np.asarray(v0, float)[None, :], n, axis=0)
    s = np.linspace(0.0, h, n_t)
    half = (float(omega_att_max) * h) if attacker_turn_limited else None
    feasible_turn = np.ones(n, bool)
    seg_pts = []
    for j in range(K):
        a = seg_accels[:, j, :]
        if attacker_turn_limited:
            if omega_att_max is None:
                raise ValueError("attacker_turn_limited=True requires omega_att_max.")
            head = (np.repeat(np.asarray(e_att, float)[None, :], n, axis=0)
                    if (j == 0 and e_att is not None) else v)
            an = np.linalg.norm(a, axis=1)
            hn = np.linalg.norm(head, axis=1)
            denom = an * hn
            cos_a = np.where(denom < _EPS, 1.0,
                             np.einsum("ij,ij->i", a, head) / (denom + _EPS))
            cos_a = np.clip(cos_a, -1.0, 1.0)
            feasible_turn &= (np.arccos(cos_a) <= half) | (an < _EPS)
        seg_pts.append(x[:, None, :] + v[:, None, :] * s[None, :, None]
                       + 0.5 * a[:, None, :] * (s ** 2)[None, :, None])
        x = x + v * h + 0.5 * a * h * h
        v = v + a * h
    paths = np.concatenate(seg_pts, axis=1)                # (n, K*n_t, 3)
    return x, feasible_turn, paths


def _limiter_mask_from_paths(paths, limiters, kill_radius):
    """True iff the trajectory NEVER enters any limiter kill-radius (identical no-go
    semantics to _feasible_limiter / _segments_endpoints_feasible)."""
    n = paths.shape[0]
    if limiters is None or kill_radius <= 0:
        return np.ones(n, bool)
    L = np.asarray(limiters, float).reshape(-1, 3)
    if len(L) == 0:
        return np.ones(n, bool)
    d = np.linalg.norm(paths[:, :, None, :] - L[None, None, :, :], axis=3)
    return ~(d <= kill_radius).any(axis=(1, 2))


def build_reachable_union(x_att, v_att, *, tau, a_att_max, judge,
                          net_center=None, net_radius=None, net_apex=None, n_F=None,
                          theta_net=None, range_min=0.0, range_max=None,
                          attacker_turn_limited=False, omega_att_max=None, e_att=None,
                          n=2000, n_segments=4, seed=0, n_dir=32, n_t=24):
    """Build the layout-INDEPENDENT conservative union ONCE. Mirrors _union_sets'
    block order EXACTLY (B1, boundary, bang-bang, [turn-curve]) so that
    eval_union_with_limiters(build_reachable_union(...), limiters, kr) ==
    v_shot(..., n_segments=n_segments)."""
    x_att = np.asarray(x_att, float)
    v_att = np.asarray(v_att, float)
    heading = v_att if e_att is None else np.asarray(e_att, float)
    blocks_end, blocks_turn, blocks_paths = [], [], []

    accels1 = reachable_accels(a_att_max, n, seed)            # Block 1 (verbatim)
    end1 = x_att[None, :] + v_att[None, :] * tau + 0.5 * accels1 * tau ** 2
    turn1 = (_feasible_turn(accels1, heading, omega_att_max, tau)
             if attacker_turn_limited else np.ones(len(accels1), bool))
    blocks_end.append(end1)
    blocks_turn.append(turn1)
    blocks_paths.append(_single_seg_paths(x_att, v_att, accels1, tau, n_t=n_t))

    dirs = _extreme_dirs(n_dir=n_dir, seed=seed, e_att=heading)

    def _add(seg_accels):
        if len(seg_accels) == 0:
            return
        ep, tf, pp = _seg_paths_turn(x_att, v_att, seg_accels, tau=tau,
                                     attacker_turn_limited=attacker_turn_limited,
                                     omega_att_max=omega_att_max, e_att=e_att, n_t=n_t)
        blocks_end.append(ep)
        blocks_turn.append(tf)
        blocks_paths.append(pp)

    _add(_boundary_accels(a_att_max, dirs))
    _add(_bangbang_segments(a_att_max, dirs, n_segments))
    if attacker_turn_limited:
        _add(_turn_curve_segments(v_att, omega_att_max, tau, a_att_max, n_segments,
                                  e_att=e_att))

    endpoints = np.concatenate(blocks_end, axis=0)
    turn_feasible = np.concatenate(blocks_turn, axis=0)
    caught = _caught_mask(endpoints, judge, net_center=net_center, net_radius=net_radius,
                          net_apex=net_apex, n_F=n_F, theta_net=theta_net,
                          range_min=range_min, range_max=range_max)
    return ReachableUnion(endpoints=endpoints, caught=caught, turn_feasible=turn_feasible,
                          path_blocks=tuple(blocks_paths),
                          block_sizes=tuple(len(b) for b in blocks_end),
                          n_total=int(len(endpoints)), judge=judge, seed=seed)


def eval_union_with_limiters(union, limiters, kill_radius):
    """Apply a limiter layout to a prebuilt ReachableUnion -> VShotResult. Only the
    limiter no-go depends on the layout; endpoints/caught/turn are reused. Numerically
    identical to v_shot(..., n_segments=K) for the same inputs."""
    masks = [_limiter_mask_from_paths(pb, limiters, kill_radius)
             for pb in union.path_blocks]
    limiter_feasible = (np.concatenate(masks, axis=0) if masks
                        else np.ones(union.n_total, bool))
    feasible = limiter_feasible & union.turn_feasible
    return _assemble(feasible, union.caught, union.n_total, union.judge, union.seed)

def eval_union_with_limiter_sets(union, limiter_sets, kill_radius):
    """Batched eval_union_with_limiters over MULTIPLE limiter layouts at once.

    2A batched shared-distance eval (docs/09 SS5 Phase 2A / SS8 2026-07-03 (d),
    ratified): the env's per-step layouts (full, hold_position baseline, N COMA
    counterfactuals) draw from a small pool of UNIQUE limiter positions (<= 2N).
    Compute each unique sphere's per-witness hit mask ONCE per path block, then
    compose every layout as a boolean any() over its column subset.

    NUMERICALLY IDENTICAL to calling eval_union_with_limiters(union, L, kr) per
    layout (same subtraction/norm per (witness, substep, position); locked by
    tests/test_batched_eval.py; 2A' spike pre-verified 0/12 state mismatches),
    ~2.4x cheaper for the M2 six-layout step. Returns [VShotResult] in order.
    """
    sets_arr = []
    for L in limiter_sets:
        if L is None:
            sets_arr.append(np.zeros((0, 3)))
        else:
            sets_arr.append(np.asarray(L, float).reshape(-1, 3))

    ones = np.ones(union.n_total, bool)
    if kill_radius <= 0 or all(len(L) == 0 for L in sets_arr):
        return [_assemble(ones & union.turn_feasible, union.caught,
                          union.n_total, union.judge, union.seed)
                for _ in sets_arr]

    uniq_rows, uniq_index, cols = [], {}, []
    for L in sets_arr:
        c = []
        for row in L:
            key = row.tobytes()
            if key not in uniq_index:
                uniq_index[key] = len(uniq_rows)
                uniq_rows.append(row)
            c.append(uniq_index[key])
        cols.append(sorted(set(c)))
    uniq = np.asarray(uniq_rows, float)                          # (U, 3)

    hit_blocks = []
    for pb in union.path_blocks:
        d = np.linalg.norm(pb[:, :, None, :] - uniq[None, None, :, :], axis=3)
        hit_blocks.append((d <= kill_radius).any(axis=1))        # (n_b, U)
    hit = np.concatenate(hit_blocks, axis=0)                     # (M, U)

    out = []
    for c in cols:
        feasible_lim = ones if not c else ~hit[:, c].any(axis=1)
        out.append(_assemble(feasible_lim & union.turn_feasible, union.caught,
                             union.n_total, union.judge, union.seed))
    return out


def sphere_containment_certificate(x_att, v_att, *, tau, a_att_max, net_center,
                                   net_radius):
    """EXACT worst-case containment for the point-mass sphere, NO limiters / no turn
    limit (post-review fix: replace finite-witness worst-counting with a closed-form
    certificate where the reachable set is the full ball). The free tau-reachable set
    is B(c, R), c = x + v*tau, R = 1/2 a_att_max tau^2; it is wholly inside the net
    sphere iff ||c - net_center|| + R <= net_radius. Returns True => certified
    contained (v_shot_worst must be 1); False => a reachable point provably escapes."""
    c = np.asarray(x_att, float) + np.asarray(v_att, float) * tau
    R = 0.5 * float(a_att_max) * tau ** 2
    off = float(np.linalg.norm(c - np.asarray(net_center, float)))
    return bool(off + R <= net_radius + _EPS)
