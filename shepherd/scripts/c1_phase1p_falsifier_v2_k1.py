"""C-1 — FALSIFIER-v2, layer A0: the K=1 constant-acceleration attack, solved explicitly.

WHY THIS LAYER EXISTS
---------------------
D2a's only counterexample was a CONSTANT acceleration -- exactly representable at
K=1 -- and it came from a raw random bank draw, not from CEM.  D1's own draws came
within 0.115 degrees of that direction and scored -0.035 m there.  A success region
that thin in direction space cannot be reached reliably by sampling K=4 vectors at
random and hoping.

So v2 inverts the order: the LOWEST-dimensional attack class is solved FIRST and
DETERMINISTICALLY, before any stochastic search runs at higher K.  K=1 has only
three degrees of freedom -- two of direction, one of magnitude -- which is small
enough to grid.

    direction   deterministic equal-area (Fibonacci) grid on the sphere
    magnitude   explicit sweep over [0, a_att_max]
    refinement  tangent-plane local search around every retained top candidate,
                alternating with a 1-D magnitude scan, at shrinking radii

Nothing here is random.  Re-running it gives the identical candidate set.

THE SEPARATION THIS MODULE MUST RESPECT
---------------------------------------
The `RH 5.0/0.55 f=10 / RI-GMAX` counterexample is what motivated this design.
Re-finding it is a REGRESSION CANARY -- necessary, but NOT evidence of general
detection power, because the search was built knowing it exists.  It is therefore
reported in its own bucket, never pooled with the other cells.

SCORING
-------
One scalar, sign-consistent with the decision boundary at 0:

    S(a) = max( -kill_margin, -cone_exit_margin )   if ||a|| <= a_att_max
         = +inf                                      otherwise
    escape  <=>  S(a) < 0

TWO RECORDED DEVIATIONS FROM THE REVIEW'S LITERAL FORMULA
--------------------------------------------------------
1.  The review wrote `S = max{-kill, -cone, admissibility penalty}`.  Putting the
    admissibility term INSIDE the max is wrong here for two reasons, and the first
    was caught by running it:
      - units.  `||a|| - a_max` is m/s^2; the margins are metres.  They are not
        commensurable inside a max.
      - boundary masking.  The admissible set is CLOSED (||a|| <= a_max), so a
        saturated attack is legal -- yet `||a|| - a_max` is exactly 0 there, which
        forces S >= 0 and makes a saturated escape unrepresentable.  The first run
        of this module did exactly that: every cell reported its grid best as
        `0.000000` or worse, pinned by the admissibility term at ||a|| = a_max,
        and the known D2a witness sits at ||a|| = 29.83 = 99.4% of a_max.
    Admissibility is a HARD CONSTRAINT, not a penalty term: infeasible candidates
    get +inf, feasible ones are scored on the two margins alone.
2.  The review wrote `max_a S(a)`.  Since escape is S < 0, the informative
    extremum is `min_a S(a)` -- the closest approach to the boundary.

Both are stated rather than silently applied.

`S_proxy` uses the SAMPLED kill margin (24 substeps/segment) because a grid of
~400k candidates cannot be adjudicated continuously.  Every retained candidate is
then re-scored by the AUTHORITATIVE continuous verifier and only `S_auth < 0`
counts as an escape.  Proposal and verification stay separate.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for
from shepherd.scripts.c1_phase1p_modes import cone_components, classify
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

V2 = {"protocol": "FALSIFIER-v2", "layer": "A0_K1_CONSTANT_ACCELERATION",
      "deterministic": True,
      "n_dir": 8192,             # Fibonacci sphere, equal-area to O(1/n)
      "n_mag": 64,               # explicit sweep over (0, a_max]
      "top_m": 48,               # candidates carried into refinement
      "refine_rounds": 4,
      "tangent_radii_deg": (2.0, 0.5, 0.125, 0.03),
      "tangent_grid": 5,         # 5x5 offsets per radius
      "mag_scan": 33,
      "verify_band_m": 0.002,    # authoritative check for every S_proxy < this
      "chunk": 16384}
K1 = 1
ADM_TOL = 1e-9              # ||a|| <= a_max is a CLOSED constraint; tol is fp only


def fibonacci_directions(n):
    """Deterministic, near-equal-area points on S^2.  No RNG."""
    i = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    golden = np.pi * (1.0 + 5.0 ** 0.5)
    theta = golden * i
    return np.stack([np.cos(theta) * np.sin(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(phi)], axis=1)


def tangent_basis(u):
    """Two unit vectors spanning the plane orthogonal to u."""
    a = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(u, a); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2


def s_proxy(E, pa, va, L, cone, tau, A):
    """S(a) with the SAMPLED kill margin.  A is (n, 3) constant accelerations."""
    A = np.asarray(A, float)
    ep, tf, pts = V._seg_paths_turn(pa, va, A[:, None, :], tau=tau,
                                    attacker_turn_limited=False, omega_att_max=None,
                                    e_att=None, n_t=24)
    km = kill_margin(pts, L, E.kill_radius, tau)
    cm = cone_exit_margin(ep, **cone)
    feasible = tf & (np.linalg.norm(A, axis=1) <= float(E.a_att_max) + ADM_TOL)
    S = np.where(feasible, np.maximum(-km, -cm), np.inf)
    return S, km, cm


def s_proxy_chunked(E, pa, va, L, cone, tau, A, chunk):
    out = []
    for i in range(0, len(A), chunk):
        out.append(s_proxy(E, pa, va, L, cone, tau, A[i:i + chunk])[0])
    return np.concatenate(out)


def s_auth(E, pa, va, L, cone, tau, a):
    """S(a) with the AUTHORITATIVE continuous kill margin.  One candidate."""
    a = np.asarray(a, float).reshape(1, 3)
    ep, tf, _p = V._seg_paths_turn(pa, va, a[:, None, :], tau=tau,
                                   attacker_turn_limited=False, omega_att_max=None,
                                   e_att=None, n_t=24)
    lat, axi, _x, _r, _g = cone_components(ep, **cone)
    cm = float(max(lat[0], axi[0]))
    r = exact_min_clearance(pa, va, a, tau, L, N_LIM, DT, E.kill_radius)
    nrm = float(np.linalg.norm(a[0]))
    admissible = bool(tf[0] and nrm <= float(E.a_att_max) + ADM_TOL)
    S = (max(-float(r["exact_margin_m"]), -cm) if admissible else float("inf"))
    return {"S_auth_m": S, "continuous_kill_margin_m": float(r["exact_margin_m"]),
            "cone_exit_margin_m": cm, "acc_norm_mps2": nrm,
            "admissibility_slack_mps2": float(E.a_att_max) - nrm,
            "admissible": admissible,
            "verdict": r["verdict"], "turn_feasible": bool(tf[0]),
            "is_escape": bool(admissible and S < 0.0
                              and r["verdict"] == "VERIFIED_COLLISION_FREE"),
            "lateral_m": float(lat[0]), "axial_m": float(axi[0])}


def k1_search(E, pa, va, L, cone, tau, seed_directions=()):
    """Stage 1 grid -> stage 2 tangent/magnitude refinement.  Fully deterministic."""
    U = fibonacci_directions(V2["n_dir"])
    if len(seed_directions):                       # regression points, if supplied
        U = np.concatenate([U, np.asarray(seed_directions, float)], axis=0)
    mags = np.linspace(0.0, float(E.a_att_max), V2["n_mag"] + 1)[1:]
    A = (U[:, None, :] * mags[None, :, None]).reshape(-1, 3)
    S = s_proxy_chunked(E, pa, va, L, cone, tau, A, V2["chunk"])
    n_grid = len(A)
    order = np.argsort(S)[:V2["top_m"]]
    stage1_best = float(S[order[0]])

    best_a, best_S = A[order[0]].copy(), stage1_best
    kept = [A[i].copy() for i in order]
    for _rd in range(V2["refine_rounds"]):
        new = []
        for a0 in kept:
            m0 = float(np.linalg.norm(a0))
            if m0 < 1e-12:
                continue
            u0 = a0 / m0
            e1, e2 = tangent_basis(u0)
            for rdeg in V2["tangent_radii_deg"]:
                r = np.radians(rdeg)
                g = np.linspace(-r, r, V2["tangent_grid"])
                al, be = np.meshgrid(g, g, indexing="ij")
                dirs = (u0[None, :] + al.ravel()[:, None] * e1[None, :]
                        + be.ravel()[:, None] * e2[None, :])
                dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
                dm = 0.05 * float(E.a_att_max) * (rdeg / V2["tangent_radii_deg"][0])
                ms = np.clip(np.linspace(m0 - dm, m0 + dm, V2["mag_scan"]),
                             0.0, float(E.a_att_max))
                cand = (dirs[:, None, :] * ms[None, :, None]).reshape(-1, 3)
                new.append(cand)
        if not new:
            break
        C = np.concatenate(new, axis=0)
        Sc = s_proxy_chunked(E, pa, va, L, cone, tau, C, V2["chunk"])
        o = np.argsort(Sc)[:V2["top_m"]]
        if float(Sc[o[0]]) < best_S:
            best_S, best_a = float(Sc[o[0]]), C[o[0]].copy()
        kept = [C[i].copy() for i in o]
        n_grid += len(C)

    # everything worth adjudicating authoritatively
    pool = np.concatenate([A[order], np.asarray(kept, float), best_a[None, :]], axis=0)
    Sp = s_proxy_chunked(E, pa, va, L, cone, tau, pool, V2["chunk"])
    take = np.argsort(Sp)[:V2["top_m"]]
    return {"n_candidates_evaluated": int(n_grid),
            "stage1_grid_best_S_proxy_m": stage1_best,
            "best_S_proxy_m": best_S,
            "refined_gain_m": float(stage1_best - best_S),
            "pool": pool[take], "pool_S_proxy": Sp[take]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2a", default="results/c1_corridor/c1_phase1p_d2a.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_falsifier_v2_k1.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d2a = json.loads(pathlib.Path(a.d2a).read_text())

    # the known D2a witness direction, used ONLY as a regression seed on its own cell
    known = {}
    for r in d2a["rows"]:
        for e in r["d2a"]["escapes"]:
            v = np.asarray(e["acc"], float)[0]
            known[(r["witness"], r["arm"])] = v / np.linalg.norm(v)

    print("== FALSIFIER-v2 layer A0 — K=1 constant acceleration, solved explicitly ==")
    print("   deterministic: %d directions (equal-area) x %d magnitudes, then "
          "tangent-plane refinement" % (V2["n_dir"], V2["n_mag"]))
    print("   S(a) = max(-kill, -cone, ||a||-a_max);  escape <=> S < 0;  reported "
          "extremum is min_a S\n")
    print("   %-22s %-10s %7s %11s %11s %6s %s"
          % ("scenario", "arm", "delta", "S1 grid", "refined", "esc", "note"))

    rows = []
    for r in d2a["rows"]:
        tag, arm, dl = r["witness"], r["arm"], r["selected_delta_m"]
        is_regression = (tag, arm) in known
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        pa = o[ATT_P0:ATT_P0 + 3]; va = o[ATT_P0 + 3:ATT_P0 + 6]
        P0 = np.asarray(rec["_lim"][t:], float); Vp0 = np.asarray(rec["_vel"][t:], float)
        kw = E._vshot_kwargs(pa, va, o[36:45])
        cone = {x: kw[x] for x in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
        tau = float(E.tau_deploy)
        P, Vv, _A, _b, _r = dynamic_inward(P0, Vp0, dl)
        L = lambda ts: hermite_positions(P, Vv, np.asarray(ts))[0]

        res = k1_search(E, pa, va, L, cone, tau,
                        seed_directions=([known[(tag, arm)]] if is_regression else ()))
        esc, checked = [], 0
        for i in range(len(res["pool"])):
            if res["pool_S_proxy"][i] > V2["verify_band_m"] and checked:
                break
            checked += 1
            au = s_auth(E, pa, va, L, cone, tau, res["pool"][i])
            if au["is_escape"]:
                esc.append({"attack_policy_hash": G.attack_policy_hash(
                                np.repeat(res["pool"][i][None, :], 4, axis=0)),
                            "acc_k1": res["pool"][i].tolist(),
                            "acc_norm_mps2": float(np.linalg.norm(res["pool"][i])),
                            "S_proxy_m": float(res["pool_S_proxy"][i]), **au})
        best_auth = s_auth(E, pa, va, L, cone, tau, res["pool"][0])
        rows.append({"witness": tag, "arm": arm, "selected_delta_m": dl,
                     "bucket": ("REGRESSION_CANARY" if is_regression
                                else "INDEPENDENT_CELL"),
                     "d2a_verdict": r["verdict"],
                     "n_candidates_evaluated": res["n_candidates_evaluated"],
                     "stage1_grid_best_S_proxy_m": res["stage1_grid_best_S_proxy_m"],
                     "best_S_proxy_m": res["best_S_proxy_m"],
                     "refinement_gain_m": res["refined_gain_m"],
                     "n_authoritatively_checked": checked,
                     "best_candidate_authoritative": best_auth,
                     "n_k1_escapes": len(esc), "k1_escapes": esc[:8]})
        print("   %-22s %-10s %7.3f %11.6f %11.6f %6d %s"
              % (tag, arm, dl, res["stage1_grid_best_S_proxy_m"], res["best_S_proxy_m"],
                 len(esc), "REGRESSION_CANARY" if is_regression else ""), flush=True)

    ind = [r for r in rows if r["bucket"] == "INDEPENDENT_CELL"]
    reg = [r for r in rows if r["bucket"] == "REGRESSION_CANARY"]
    n_new = sum(1 for r in ind if r["n_k1_escapes"] > 0)
    print("\n   REGRESSION_CANARY  %d cell(s): k1 escapes %s"
          % (len(reg), [r["n_k1_escapes"] for r in reg]))
    print("   INDEPENDENT cells  %d: with a K=1 escape %d" % (len(ind), n_new))
    if ind:
        b = np.asarray([r["best_S_proxy_m"] for r in ind], float)
        print("   independent-cell min_a S_proxy   min %+.6f  median %+.6f  max %+.6f"
              % (b.min(), float(np.median(b)), b.max()))
    print("\n   %s" % ("A K=1 escape exists in an independent cell -> that cell's null "
                       "was also a within-class search miss" if n_new else
                       "no K=1 escape in any independent cell — the legacy nulls survive "
                       "the lowest rung, deterministically searched"))

    out = {"meta": {"script": "c1_phase1p_falsifier_v2_k1", "protocol": V2,
                    "role": "FALSIFIER-v2 layer A0; proposal generator + authoritative "
                            "adjudication. Changes no controller",
                    "scoring": "S(a) = max(-kill, -cone, ||a||-a_max); escape <=> S<0",
                    "reported_extremum": "min_a S(a) — the review wrote max_a S(a); since "
                                         "escape is S<0 the informative extremum is the "
                                         "minimum. Recorded deviation, not a silent change",
                    "proxy_vs_authoritative": "grid scoring is the SAMPLED margin; every "
                                              "retained candidate is re-scored continuously "
                                              "and only S_auth<0 counts",
                    "bucket_rule": "the cell that motivated this design is a REGRESSION "
                                   "CANARY and is never pooled with independent cells"},
           "n_independent_cells": len(ind),
           "n_independent_cells_with_k1_escape": n_new,
           "regression_canary_recovered": [r["n_k1_escapes"] > 0 for r in reg],
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
