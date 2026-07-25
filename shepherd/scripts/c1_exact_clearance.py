"""C-1 — EXACT continuous minimum-distance adjudicator (Phase 1L step 1).

Replaces the Lipschitz screen in `c1_replan_verify.certified_kill_clearance`, whose
relative-speed bound used a 1.25x empirical padding on the limiter Hermite speed.
That padding is not a proof, so that routine is a CONSERVATIVE_CONTINUOUS_CLEARANCE_SCREEN,
not a certifier: it can only ever say "collision-free could not be certified".

Why an exact answer is available here
-------------------------------------
On any interval that contains no breakpoint of either body,

  * the attacker is a PARABOLA          p_a(t) = p + v t + a t^2 / 2      (degree 2)
  * the limiter is a CUBIC HERMITE      (degree 3, the judge's own model)

so the relative position r(t) = p_a(t) - L_i(t) is a vector CUBIC, and

      d^2(t) = || r(t) ||^2      is a scalar polynomial of degree 6.

Its stationary points are the real roots of a degree-5 polynomial, which are
obtained exactly (companion-matrix eigenvalues).  Evaluating d^2 at those roots
plus the two endpoints gives the TRUE minimum on the interval -- no sampling, no
Lipschitz slack, no padding.

Sub-intervals are cut at the UNION of both breakpoint sets (attacker segment
boundaries at multiples of tau/K, limiter Hermite nodes at multiples of dt), so the
polynomial assumption holds on every piece.  The cubic is recovered by exact
interpolation through four nodes of the interval, using the SAME position callables
the judge uses, so no coefficient algebra is re-derived (and cannot be re-derived
wrongly).

Three-way verdict (the review's required split)
-----------------------------------------------
    VERIFIED_COLLISION_FREE      d_min > r_kill + tol
    VERIFIED_COLLISION           d_min < r_kill - tol
    UNRESOLVED_CONTINUOUS_CLEARANCE   |d_min - r_kill| <= tol

`tol` is the numerical resolution of the root isolation, NOT a model-uncertainty
budget; those are separate and are applied at the labelling layer.
"""
from __future__ import annotations
import numpy as np

TOL_NUMERIC = 1e-9          # root-isolation / float resolution, metres
_W = np.array([0.0, 1.0 / 3.0, 2.0 / 3.0, 1.0])
_VAND = np.vander(_W, 4)    # columns: w^3, w^2, w, 1


def _fit_cubic(vals):
    """Exact cubic interpolation through the four nodes _W.  vals: (4, d) -> (4, d)
    coefficients in descending powers of w."""
    return np.linalg.solve(_VAND, vals)


def _poly_sq_sum(C):
    """d^2(w) = sum_dim ( C[:,k] . w )^2  for cubic coeffs C (4, d) -> degree-6 coeffs."""
    out = np.zeros(7)
    for k in range(C.shape[1]):
        out += np.convolve(C[:, k], C[:, k])
    return out


def min_distance_on_interval(pa_of_t, L_of_t, T0, T1, lim_idx):
    """True minimum ||p_a - L_i|| on [T0, T1] for limiter lim_idx."""
    t = T0 + _W * (T1 - T0)
    Pa = np.asarray(pa_of_t(t), float)                       # (4, 3)
    Pl = np.asarray(L_of_t(t), float)[:, lim_idx, :]         # (4, 3)
    C = _fit_cubic(Pa - Pl)                                  # (4, 3)
    q = _poly_sq_sum(C)                                      # degree 6, descending
    dq = np.polyder(q)                                       # degree 5
    cands = [0.0, 1.0]
    if np.any(np.abs(dq) > 0):
        r = np.roots(dq)
        for z in r:
            if abs(z.imag) < 1e-9 and -1e-12 <= z.real <= 1.0 + 1e-12:
                cands.append(float(np.clip(z.real, 0.0, 1.0)))
    vals = [float(np.polyval(q, w)) for w in cands]
    return float(np.sqrt(max(min(vals), 0.0)))


def exact_min_clearance(p0, v0, seg_acc, tau, L_of_t, n_lim, dt, r_kill,
                        tol=TOL_NUMERIC):
    """Exact min over the whole deploy window of (distance - r_kill), with verdict.

    p0, v0, seg_acc define the attacker; L_of_t is the authoritative limiter model.
    Breakpoints = attacker segment edges (tau/K) UNION limiter Hermite nodes (dt)."""
    seg_acc = np.asarray(seg_acc, float); K = len(seg_acc); h = float(tau) / K

    # attacker position as a function of GLOBAL time, evaluated exactly per segment
    def pa_of_t(ts):
        ts = np.atleast_1d(np.asarray(ts, float))
        out = np.empty((len(ts), 3))
        p = np.asarray(p0, float).copy(); v = np.asarray(v0, float).copy()
        starts = [(p.copy(), v.copy())]
        for k in range(K):                                   # segment initial states
            a = seg_acc[k]
            p = p + v * h + 0.5 * a * h * h
            v = v + a * h
            starts.append((p.copy(), v.copy()))
        for j, tt in enumerate(ts):
            k = min(int(np.floor(tt / h + 1e-12)), K - 1)
            pk, vk = starts[k]; s = tt - k * h
            out[j] = pk + vk * s + 0.5 * seg_acc[k] * s * s
        return out

    bps = sorted(set(np.round(np.concatenate([
        np.arange(K + 1) * h,
        np.arange(0, int(np.floor(tau / dt)) + 2) * dt]), 12)))
    bps = [b for b in bps if -1e-12 <= b <= tau + 1e-12]
    bps = [min(max(b, 0.0), tau) for b in bps]
    d_min = np.inf; where = None
    for j in range(len(bps) - 1):
        T0, T1 = bps[j], bps[j + 1]
        if T1 - T0 < 1e-12:
            continue
        for i in range(n_lim):
            d = min_distance_on_interval(pa_of_t, L_of_t, T0, T1, i)
            if d < d_min:
                d_min, where = d, {"t0": T0, "t1": T1, "limiter": i}
    margin = float(d_min - r_kill)
    if margin > tol:
        verdict = "VERIFIED_COLLISION_FREE"
    elif margin < -tol:
        verdict = "VERIFIED_COLLISION"
    else:
        verdict = "UNRESOLVED_CONTINUOUS_CLEARANCE"
    return {"d_min_m": float(d_min), "exact_margin_m": margin, "verdict": verdict,
            "argmin": where, "n_subintervals": len(bps) - 1,
            "method": "degree-6 d^2, exact stationary points of its degree-5 derivative",
            "tol_numeric_m": tol}


def nominal_vs_robust_label(exact_margin_m, uncertainty_budget_m):
    """Margin-aware falsification label (the review's defect #4).

    A counterexample whose clearance is smaller than the pre-registered model
    uncertainty budget is a NOMINAL-MODEL counterexample only."""
    if exact_margin_m is None:
        return None
    if exact_margin_m > uncertainty_budget_m:
        return "ROBUSTLY_FALSIFIED_UNDER_MODEL_UNCERTAINTY"
    return "FALSIFIED_BY_ADVERSARIAL_REPLAN_IN_NOMINAL_MODEL"
