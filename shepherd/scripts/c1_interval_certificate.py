"""C-1 — Bernstein interval CERTIFICATE for continuous clearance.

`c1_exact_clearance` resolves the minimum distance by finding the real roots of the
degree-5 derivative with a companion-matrix eigensolve.  That is a floating-point
numerical root computation, not exact root isolation, so its output is a
NUMERICALLY_RESOLVED result, not a proof.  This module supplies the proof for the
cases where it matters -- the counterexamples whose clearance margin is small enough
that rounding could conceivably matter.

Method (no root finding at all)
-------------------------------
On a sub-interval the squared distance is a degree-6 polynomial q(w), w in [0,1].
Writing q in the BERNSTEIN basis,

    q(w) = sum_i b_i B_i^n(w),      b_i = sum_{j<=i} [C(i,j)/C(n,j)] a_j

the convex-hull property gives

    min_i b_i  <=  min_{[0,1]} q(w)  <=  min(q(0), q(1)) .

So `min_i b_i > r_kill^2` CERTIFIES collision-free on that sub-interval, and a
sampled value below r_kill^2 CERTIFIES a collision.  Neither conclusion depends on
locating a root.  When the bracket is inconclusive the interval is bisected with de
Casteljau subdivision, which converges quadratically in the interval width, and the
recursion is repeated until one side decides or the depth cap is reached.

Floating point is handled by OUTWARD rounding: every Bernstein bound is slackened by
an explicit error allowance derived from the coefficient magnitudes and the machine
epsilon, so the reported certificate stays valid under rounding.
"""
from __future__ import annotations
import numpy as np
from math import comb

EPS = np.finfo(float).eps


def power_to_bernstein(a_asc):
    """Bernstein coefficients of p(w) = sum_j a_asc[j] w^j on [0,1] (degree n)."""
    n = len(a_asc) - 1
    b = np.empty(n + 1)
    for i in range(n + 1):
        s = 0.0
        for j in range(i + 1):
            s += comb(i, j) / comb(n, j) * a_asc[j]
        b[i] = s
    return b


def _outward(b, a_asc, k=8.0):
    """Conservative float-error allowance for the basis change (outward rounding)."""
    scale = float(np.abs(a_asc).sum()) + float(np.abs(b).max()) + 1.0
    return k * (len(a_asc) ** 2) * EPS * scale


def _subdivide(a_asc, lo, hi):
    """Split the polynomial (power basis on the parent interval, argument already
    normalised to [0,1]) into the two halves' power coefficients."""
    # p(w) on [lo,hi] -> two children by substituting w = lo + (hi-lo)*u, then halving
    n = len(a_asc) - 1
    mid = 0.5 * (lo + hi)

    def restrict(l, h):
        # coefficients of p(l + (h-l) u) in u, exact polynomial composition
        out = np.zeros(n + 1)
        for j in range(n + 1):
            if a_asc[j] == 0.0:
                continue
            # (l + (h-l)u)^j expanded
            for m in range(j + 1):
                out[m] += a_asc[j] * comb(j, m) * (l ** (j - m)) * ((h - l) ** m)
        return out
    return restrict(lo, mid), restrict(mid, hi)


def certify_interval(a_asc, thresh, max_depth=28):
    """Certify sign of  p(w) - thresh  on [0,1].

    Returns one of 'CERTIFIED_ABOVE' (p > thresh everywhere -> collision-free),
    'CERTIFIED_BELOW' (p < thresh somewhere -> collision), or 'INCONCLUSIVE',
    together with the certified lower bound achieved."""
    stack = [(np.array(a_asc, float), 0.0, 1.0, 0)]
    glb = np.inf
    while stack:
        coeff, lo, hi, depth = stack.pop()
        b = power_to_bernstein(coeff)
        err = _outward(b, coeff)
        lower = float(b.min()) - err
        # a sampled value strictly below the threshold is an immediate collision
        for u in (0.0, 0.5, 1.0):
            val = float(np.polyval(coeff[::-1], u))
            if val + err < thresh:
                return "CERTIFIED_BELOW", val - thresh
        if lower >= thresh:
            glb = min(glb, lower)
            continue
        if depth >= max_depth:
            return "INCONCLUSIVE", lower - thresh
        left, right = _subdivide(coeff, 0.0, 1.0)
        stack.append((left, lo, 0.5 * (lo + hi), depth + 1))
        stack.append((right, 0.5 * (lo + hi), hi, depth + 1))
    return "CERTIFIED_ABOVE", (glb - thresh if np.isfinite(glb) else np.inf)


def certify_clearance(p0, v0, seg_acc, tau, L_of_t, n_lim, dt, r_kill, max_depth=28):
    """Interval certificate that the attacker stays strictly outside every kill sphere.

    Same breakpoint-aligned decomposition as c1_exact_clearance, but each piece is
    decided by Bernstein bounds instead of root finding."""
    from shepherd.scripts.c1_exact_clearance import _fit_cubic, _poly_sq_sum, _W
    seg_acc = np.asarray(seg_acc, float); K = len(seg_acc); h = float(tau) / K

    p = np.asarray(p0, float).copy(); v = np.asarray(v0, float).copy()
    starts = [(p.copy(), v.copy())]
    for k in range(K):
        a = seg_acc[k]
        p = p + v * h + 0.5 * a * h * h; v = v + a * h
        starts.append((p.copy(), v.copy()))

    def pa_of_t(ts):
        ts = np.atleast_1d(np.asarray(ts, float))
        out = np.empty((len(ts), 3))
        for j, tt in enumerate(ts):
            k = min(int(np.floor(tt / h + 1e-12)), K - 1)
            pk, vk = starts[k]; s = tt - k * h
            out[j] = pk + vk * s + 0.5 * seg_acc[k] * s * s
        return out

    bps = sorted(set(np.round(np.concatenate([
        np.arange(K + 1) * h, np.arange(0, int(np.floor(tau / dt)) + 2) * dt]), 12)))
    bps = [min(max(b, 0.0), tau) for b in bps if -1e-12 <= b <= tau + 1e-12]

    worst = np.inf; verdicts = set()
    for j in range(len(bps) - 1):
        T0, T1 = bps[j], bps[j + 1]
        if T1 - T0 < 1e-12:
            continue
        t = T0 + _W * (T1 - T0)
        Pa = pa_of_t(t); Pl = np.asarray(L_of_t(t), float)
        for i in range(n_lim):
            C = _fit_cubic(Pa - Pl[:, i, :])
            q_desc = _poly_sq_sum(C)                       # degree 6, descending
            a_asc = q_desc[::-1].copy()
            vd, bound = certify_interval(a_asc, r_kill * r_kill, max_depth=max_depth)
            verdicts.add(vd)
            if vd == "CERTIFIED_BELOW":
                return {"certificate": "CERTIFIED_COLLISION", "bound_d2_minus_r2": bound,
                        "at": {"t0": T0, "t1": T1, "limiter": i}}
            worst = min(worst, bound)
    if "INCONCLUSIVE" in verdicts:
        return {"certificate": "INCONCLUSIVE", "bound_d2_minus_r2": float(worst)}
    return {"certificate": "CERTIFIED_COLLISION_FREE", "bound_d2_minus_r2": float(worst),
            "implied_min_distance_lower_bound_m": float(np.sqrt(max(worst + r_kill * r_kill, 0.0))),
            "method": "Bernstein convex-hull bound + de Casteljau bisection, outward-rounded"}
