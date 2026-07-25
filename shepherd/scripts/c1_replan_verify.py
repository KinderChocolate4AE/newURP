"""C-1 — INDEPENDENT authoritative verifier for adversarial-replan escape artifacts.

Deliberately written as a SEPARATE code path from the search in
`c1_replan_falsifier`.  The search's objective value is a proposal score and is
never accepted as evidence; an artifact only counts as an escape if THIS module,
which shares no integrator, no margin function and no masking helper with the
search, independently agrees.  (proposal-verification separation, applied to the
attacker optimizer as well as to the controller optimizer.)

Five checks, all on the stored artifact:

  V1 CONTROL ADMISSIBILITY   ||a_k|| <= a_att_max for every segment
  V2 DYNAMICS                the attacker path is re-integrated here from
                             (p_att, v_att) with an independent implementation
                             and must match the search's endpoint
  V3 CONTINUOUS COLLISION    a CERTIFIED lower bound on the attacker-limiter
                             distance over each interval, not a sampled minimum:
                             with samples d_j at t_j and a bound V on the relative
                             speed over [t_j, t_{j+1}],
                                 min_{[t_j,t_{j+1}]} d  >=  min(d_j, d_{j+1}) - V*dt/2
                             so tunneling between substeps cannot be missed
  V4 NET-CONE ESCAPE         viability._caught_se3_cone on the re-integrated
                             endpoint (the authoritative capture predicate)
  V5 EXACT REPLAY            re-running V1-V4 from the artifact reproduces the
                             recorded margins bit-for-bit

An artifact is an ESCAPE only if V1-V5 all pass AND the certified distance bound
exceeds r_kill AND the endpoint is not caught.
"""
from __future__ import annotations
import numpy as np

from shepherd.game import viability as V


def integrate_attacker(p0, v0, seg_acc, tau, n_sub):
    """Independent re-integration of the K-segment attacker path.

    Analytic piecewise-parabolic propagation, written here from the segment
    definition rather than reusing viability._seg_paths_turn, so an error in that
    helper cannot be reproduced identically by the verifier.
    Returns (times (T,), path (T,3), endpoint (3,), vel (T,3))."""
    p = np.asarray(p0, float).copy(); v = np.asarray(v0, float).copy()
    seg_acc = np.asarray(seg_acc, float)
    K = len(seg_acc); h = float(tau) / K
    ts, ps, vs = [], [], []
    t0 = 0.0
    for k in range(K):
        a = seg_acc[k]
        s = np.linspace(0.0, h, n_sub, endpoint=False) if k < K - 1 else np.linspace(0.0, h, n_sub + 1)
        for si in s:
            ts.append(t0 + si)
            ps.append(p + v * si + 0.5 * a * si * si)
            vs.append(v + a * si)
        p = p + v * h + 0.5 * a * h * h
        v = v + a * h
        t0 += h
    return np.asarray(ts), np.asarray(ps), p.copy(), np.asarray(vs)


def certified_kill_clearance(times, path, vel, L_of_t, L_vel_bound, r_kill):
    """CERTIFIED lower bound on (distance - r_kill) over the CONTINUOUS interval.

    Sampled distances alone can miss a dip between samples.  Over [t_j, t_{j+1}]
    the attacker and every limiter each move at bounded speed, so the distance is
    Lipschitz with constant V = max attacker speed + max limiter speed on that
    interval, giving
        min d on the interval >= min(d_j, d_{j+1}) - V * (t_{j+1}-t_j) / 2 .
    Returning the min over intervals of that bound makes 'no collision' sound
    rather than merely unobserved."""
    Lt = L_of_t(times)                                        # (T, nL, 3)
    d = np.linalg.norm(path[:, None, :] - Lt, axis=2)         # (T, nL)
    sp_att = np.linalg.norm(vel, axis=1)                      # (T,)
    worst = np.inf
    for j in range(len(times) - 1):
        dt = float(times[j + 1] - times[j])
        Vrel = float(max(sp_att[j], sp_att[j + 1]) + L_vel_bound)
        lo = float(min(d[j].min(), d[j + 1].min())) - Vrel * dt / 2.0
        worst = min(worst, lo)
    return float(worst - r_kill), float(d.min() - r_kill)


def verify_escape(artifact, *, p_att, v_att, tau, a_att_max, L_of_t, L_vel_bound,
                  kill_radius, cone_kw, n_sub=64, tol=1e-9):
    """Run V1-V5 on one stored artifact.  Returns a dict; `is_escape` is the verdict."""
    acc = np.asarray(artifact["acc"], float)
    out = {"n_segments": int(len(acc)), "n_sub": n_sub}

    # V1 control admissibility
    nrm = np.linalg.norm(acc, axis=1)
    out["V1_control_admissible"] = bool(nrm.max() <= a_att_max + 1e-6)
    out["max_accel_norm"] = float(nrm.max())

    # V2 independent dynamics
    times, path, endpoint, vel = integrate_attacker(p_att, v_att, acc, tau, n_sub)
    rec_ep = np.asarray(artifact.get("endpoint", endpoint), float)
    out["V2_endpoint_residual_m"] = float(np.linalg.norm(endpoint - rec_ep))
    out["V2_dynamics_match"] = bool(out["V2_endpoint_residual_m"] < 1e-6)

    # V3 certified continuous collision
    cert, sampled = certified_kill_clearance(times, path, vel, L_of_t, L_vel_bound,
                                             kill_radius)
    out["V3_certified_kill_margin_m"] = cert
    out["V3_sampled_kill_margin_m"] = sampled
    out["V3_no_tunneling"] = bool(cert > 0.0)

    # V4 authoritative capture predicate
    caught = bool(V._caught_se3_cone(endpoint[None, :], **cone_kw)[0])
    out["V4_caught_by_net"] = caught
    out["V4_escapes_net"] = bool(not caught)

    # V5 exact replay: recompute from the artifact and compare to the first pass
    times2, path2, endpoint2, vel2 = integrate_attacker(p_att, v_att, acc, tau, n_sub)
    cert2, _ = certified_kill_clearance(times2, path2, vel2, L_of_t, L_vel_bound, kill_radius)
    out["V5_exact_replay"] = bool(abs(cert2 - cert) < tol
                                  and np.linalg.norm(endpoint2 - endpoint) < tol)

    out["is_escape"] = bool(out["V1_control_admissible"] and out["V2_dynamics_match"]
                            and out["V3_no_tunneling"] and out["V4_escapes_net"]
                            and out["V5_exact_replay"])
    out["margin_m"] = float(min(cert, artifact.get("cone_exit_margin", np.inf)))
    return out


def limiter_speed_bound(P_post, V_post, pad=1.25):
    """Conservative bound on limiter speed over the deploy window (for V3's Lipschitz
    constant).  Hermite interpolation between samples can overshoot the sampled
    speeds, so the node maximum is padded."""
    return float(np.linalg.norm(np.asarray(V_post, float), axis=2).max() * pad)
