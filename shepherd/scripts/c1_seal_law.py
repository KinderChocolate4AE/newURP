"""C-1 — the AZIMUTHAL SEALING LAW, derived and measured.

Derivation
----------
N limiters sit on a circle of radius rho about the engagement axis, each carrying a
kill sphere of radius r_kill.  For an azimuthal gap of width dphi between two
adjacent limiters, the worst-covered point on the circle is the gap midpoint; its
chord distance to each bounding limiter is

        chord = 2 * rho * sin(dphi / 4)

(the midpoint is dphi/2 away in azimuth from each neighbour, and a central angle a
subtends a chord 2*rho*sin(a/2)).  The union of kill spheres therefore closes the
gap iff chord <= r_kill, i.e.

        SEAL  <=>  dphi_max  <=  4 * arcsin( r_kill / (2 * rho) )           (*)

Two immediate consequences:

  * at the ratified terminal ring rho* = r_kill = 2.6 the bound is EXACTLY 120 deg,
    so any arrangement of >= 3 limiters with no gap above 120 deg seals — azimuthal
    distribution is nearly free at the terminal, which is why the 4-limiter 90 deg
    ring never showed an azimuthal residual;
  * during the dive the bound TIGHTENS with rho.  At rho0 = 5.0 it is 60.3 deg,
    while an even 4-ring has 90 deg, so the ring is azimuthally OPEN for the whole
    transit until rho <= r_kill / (2 sin(pi/N)) = 3.40 m (N=4).

That transit window — not the terminal — is where an angular degree of freedom can
buy anything.  This script prints (*) and then MEASURES the pass/fail boundary by
sweeping the largest azimuthal gap at fixed rho0/T with the Arm L hold witness, and
judging with the E1.5 actual-trajectory model.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, THETA, N_LIM, R_BODY,
                                                M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import judge_models, N_CERT
from shepherd.scripts.c1_plant_bound import solve_witness_hold, make_lp_arm


def dphi_max_allowed(rho, r_kill):
    """(*)  the largest azimuthal gap the kill-sphere union still closes, in degrees."""
    x = r_kill / (2.0 * rho)
    return 180.0 if x >= 1.0 else float(np.degrees(4.0 * np.arcsin(x)))


def rho_seal(dphi_deg, r_kill):
    """Largest rho at which a gap of dphi_deg is still sealed."""
    s = 2.0 * np.sin(np.radians(dphi_deg) / 4.0)
    return float("inf") if s <= 0 else r_kill / s


def angles_with_gap(gap_deg, n=N_LIM, phi0=0.4):
    """n azimuths whose LARGEST gap is exactly gap_deg (the rest split evenly)."""
    g = np.radians(gap_deg); rest = (2 * np.pi - g) / (n - 1)
    return phi0 + np.arange(n) * rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rho0", type=float, default=5.0)
    ap.add_argument("--tlead", type=float, default=0.55)
    ap.add_argument("--fire", type=int, default=10)
    ap.add_argument("--gaps", default="90,105,115,120,125,135,150")
    ap.add_argument("--n-cert", type=int, default=N_CERT)
    ap.add_argument("--out", default="results/c1_corridor/c1_seal_law.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    rk = float(E.kill_radius)

    pred = {("%.2f" % r): round(dphi_max_allowed(r, rk), 2)
            for r in (2.55, 2.60, 2.65, 3.00, 3.20, 3.40, 4.00, 5.00)}
    even = 360.0 / N_LIM
    rho_open = rho_seal(even, rk)
    print("SEAL LAW   dphi_max <= 4*arcsin(r_kill/(2*rho)),  r_kill = %.2f, N = %d" % (rk, N_LIM))
    for r, v in pred.items():
        print("   rho = %s  ->  dphi_max_allowed = %6.2f deg" % (r, v))
    print("   even %d-ring gap = %.1f deg  ->  sealed only for rho <= %.3f m"
          % (N_LIM, even, rho_open))

    seq, d_star, m_star = solve_witness_hold(a.rho0, a.fire)
    assert seq is not None, "hold LP infeasible at the chosen cell"
    rows = []
    print("MEASURED   rho0 %.1f  T %.2f  f %d  (Arm L hold, actual-trajectory judge, n=%d x 3)"
          % (a.rho0, a.tlead, a.fire, a.n_cert))
    for g in [float(x) for x in a.gaps.split(",")]:
        sp = make_spawn(a.rho0, a.tlead * V_CLOSE, angles=angles_with_gap(g))
        w = log_ctrl(make_lp_arm(seq))
        rec = rollout_unified(pe, sp, w, fin, r_lane=RL, r_body=RB)
        jm = judge_models(pe, rec, n_cert=a.n_cert)
        ok = bool(rec["tier"] >= 4 and jm["actual"]["certifies"])
        rows.append({"dphi_max_deg": g, "tier": rec["tier"],
                     "angular_gap_recorded": rec["max_angular_gap_deg"],
                     "v_soft_static": jm["static"]["v_soft"],
                     "v_soft_actual": jm["actual"]["v_soft"],
                     "lcb_actual": jm["actual"]["v_soft_lcb"],
                     "n_feas_actual": jm["actual"]["n_feasible"], "sealed": ok})
        print("   dphi_max = %5.1f deg -> tier %d | actual v_soft %.3f  LCB %.3f -> %s"
              % (g, rec["tier"], jm["actual"]["v_soft"] if jm["actual"]["v_soft"] is not None else -1,
                 jm["actual"]["v_soft_lcb"], "SEALED" if ok else "FAIL"), flush=True)

    passed = [r["dphi_max_deg"] for r in rows if r["sealed"]]
    failed = [r["dphi_max_deg"] for r in rows if not r["sealed"]]
    bracket = [max(passed) if passed else None, min(failed) if failed else None]
    print("   measured boundary in (%s, %s] deg   vs predicted %.1f deg at the band top (2.65)"
          % (bracket[0], bracket[1], dphi_max_allowed(2.65, rk)))

    out = {"meta": {"phase": "1H_seal_law", "r_kill": rk, "N_LIM": N_LIM,
                    "law": "dphi_max <= 4*arcsin(r_kill/(2*rho))",
                    "cell": {"rho0": a.rho0, "T": a.tlead, "f": a.fire,
                             "lp_d_star": d_star, "lp_min_clearance": m_star},
                    "n_cert": a.n_cert,
                    "note": "measurement uses the Arm L hold witness and the E1.5 actual model"},
           "predicted_dphi_max_allowed_deg": pred,
           "even_ring_open_above_rho": rho_open,
           "measured": rows,
           "measured_boundary_deg": bracket,
           "predicted_at_band_top_deg": dphi_max_allowed(2.65, rk)}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
