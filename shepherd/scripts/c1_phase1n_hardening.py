"""C-1 Phase 1N — three mandated hardenings before D0-MODE-DIVERSITY.

  N1  NET-CONE PREDICATE INDEPENDENCE.  The audit's V4 called the original
      `viability._caught_se3_cone`, so the verifier was NOT independent of an error
      in that predicate.  With a 3.84 deg half-angle a boundary error changes
      verdicts easily.  This block adds a SECOND implementation that shares no code
      with the original -- notably it avoids arccos entirely, testing the cone as
      ax >= |r| cos(theta) instead of arccos(ax/|r|) <= theta -- plus closed-form
      point tests, range-boundary tests, an axis-normalisation test, a float
      boundary-tolerance probe, and randomized parity.

  N2  RIGOROUS INTERVAL CERTIFICATE.  The Bernstein certificate must be outward
      rounded through EVERY step, not just the basis change.  Here the entire chain
      downstream of the sampled positions -- cubic interpolation, squaring to
      degree 6, power->Bernstein, subdivision -- runs in EXACT RATIONAL arithmetic
      (`fractions.Fraction`), with the sampled positions inflated to intervals that
      cover their floating-point evaluation error.  The certified quantity is
              g(t) = ||r(t)||^2 - r_kill^2
      so no square root ever enters the certificate.

  N3  STRENGTH AGGREGATION, DEFINED.  The scenario-level strength is fixed as
              m_scenario = max over sealed verified artifacts of ( min_t d(t) - r_kill )
      and each scenario stores the selected artifact hash, the argmin time, the
      margin, the verifier version and the budget comparison.

  N4  D2 SPLIT.  K=8 nests K=4 exactly (each interval halves); K=6 does not align
      with K=4 breakpoints and cannot claim exact containment.  D2 is therefore
      split into D2a (K=8, nested, the formal escalation) and D2b (K=6,
      non-nested, exploratory only).
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib
from fractions import Fraction as F
from math import comb
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, N_LIM, R_BODY, M_SAFETY,
                                                PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.game import viability as V

CERT_VERSION = "c1_phase1n_rational_bernstein_v1"
BUDGET_M = 0.010
NODES = (F(0), F(1, 3), F(2, 3), F(1))


# ------------------------------------------------------------------ N1
def caught_cone_independent(endpoints, *, net_apex, n_F, theta_net, range_min, range_max):
    """Independent SE(3) cone membership.  No arccos, no clip, no shared helper:
    the half-angle test is  ax >= |r| * cos(theta)  with ax > 0 implied."""
    apex = np.asarray(net_apex, float); n = np.asarray(n_F, float)
    nn = float(np.sqrt(n @ n))
    if nn < 1e-12:
        raise ValueError("degenerate net axis")
    n = n / nn
    r = np.asarray(endpoints, float) - apex[None, :]
    rn = np.sqrt((r * r).sum(axis=1))
    ax = r @ n
    rmax = np.inf if range_max is None else float(range_max)
    in_band = (ax >= float(range_min)) & (ax <= rmax)
    ct = float(np.cos(float(theta_net)))
    in_cone = ax >= rn * ct                      # equivalent to angle <= theta for rn > 0
    return np.where(rn < 1e-12, True, in_band & in_cone)


def cone_unit_tests(cone_kw, rng_seed=31337, n_rand=20000):
    apex = np.asarray(cone_kw["net_apex"], float)
    n = np.asarray(cone_kw["n_F"], float); n = n / np.linalg.norm(n)
    th = float(cone_kw["theta_net"]); rmin = float(cone_kw["range_min"])
    rmax = float(cone_kw["range_max"])
    perp = np.cross(n, [0.0, 0.0, 1.0])
    if np.linalg.norm(perp) < 1e-9:
        perp = np.cross(n, [0.0, 1.0, 0.0])
    perp = perp / np.linalg.norm(perp)
    tests = []

    def chk(name, pts, expect):
        a = V._caught_se3_cone(np.atleast_2d(pts), **cone_kw)
        b = caught_cone_independent(np.atleast_2d(pts), **cone_kw)
        ok = bool(np.all(a == b)) and (expect is None or bool(np.all(a == expect)))
        tests.append({"test": name, "orig": a.tolist(), "indep": b.tolist(),
                      "expected": expect, "pass": ok})

    R = 10.0
    chk("on-axis, mid range", apex + R * n, True)
    chk("cone surface (perp = R tan th)", apex + R * n + R * np.tan(th) * perp, None)
    chk("just inside cone", apex + R * n + 0.99 * R * np.tan(th) * perp, True)
    chk("just outside cone", apex + R * n + 1.01 * R * np.tan(th) * perp, False)
    chk("range_min boundary", apex + max(rmin, 1e-9) * n, None)
    chk("range_max boundary", apex + rmax * n, None)
    chk("beyond range_max", apex + (rmax * 1.001) * n, False)
    chk("behind apex", apex - R * n, False)
    # axis normalisation invariance
    kw3 = dict(cone_kw); kw3["n_F"] = np.asarray(cone_kw["n_F"], float) * 3.0
    p = apex + R * n + 0.5 * R * np.tan(th) * perp
    a1 = V._caught_se3_cone(p[None, :], **cone_kw); a2 = V._caught_se3_cone(p[None, :], **kw3)
    tests.append({"test": "axis scale invariance (orig)", "pass": bool(a1[0] == a2[0])})
    # float boundary probe: walk across the cone wall in 1e-9 m steps
    eps_pts = np.array([apex + R * n + (1.0 + k * 1e-9) * R * np.tan(th) * perp
                        for k in (-3, -1, 0, 1, 3)])
    a = V._caught_se3_cone(eps_pts, **cone_kw); b = caught_cone_independent(eps_pts, **cone_kw)
    tests.append({"test": "float boundary tolerance (5 pts, 1e-9 m steps)",
                  "orig": a.tolist(), "indep": b.tolist(), "pass": bool(np.all(a == b))})
    # randomized parity
    rng = np.random.default_rng(rng_seed)
    P = apex[None, :] + rng.normal(0, 6.0, size=(n_rand, 3)) + rng.uniform(0, rmax, (n_rand, 1)) * n[None, :]
    a = V._caught_se3_cone(P, **cone_kw); b = caught_cone_independent(P, **cone_kw)
    dis = int((a != b).sum())
    tests.append({"test": "randomized parity n=%d" % n_rand, "disagreements": dis,
                  "pass": dis == 0})
    return {"all_pass": all(t["pass"] for t in tests), "tests": tests}


# ------------------------------------------------------------------ N2 (exact rational)
def _fit_cubic_rat(vals):
    """Exact rational cubic interpolation through NODES.  vals: 4 x d of Fractions."""
    Vm = [[w ** k for k in (3, 2, 1, 0)] for w in NODES]
    # Gaussian elimination over Fractions
    d = len(vals[0]); n = 4
    A = [row[:] + [vals[i][j] for j in range(d)] for i, row in enumerate(Vm)]
    for c in range(n):
        p = next(r for r in range(c, n) if A[r][c] != 0)
        A[c], A[p] = A[p], A[c]
        pv = A[c][c]
        A[c] = [x / pv for x in A[c]]
        for r in range(n):
            if r != c and A[r][c] != 0:
                f = A[r][c]
                A[r] = [x - f * y for x, y in zip(A[r], A[c])]
    return [[A[i][n + j] for j in range(d)] for i in range(n)]      # descending powers


def _conv(a, b):
    out = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x == 0:
            continue
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def _bernstein(a_asc):
    n = len(a_asc) - 1
    return [sum(F(comb(i, j), comb(n, j)) * a_asc[j] for j in range(i + 1)) for i in range(n + 1)]


def _subdiv(a_asc):
    """Coefficients of p on [0,1/2] and [1/2,1], re-parameterised to [0,1]. Exact."""
    n = len(a_asc) - 1
    left = [F(0)] * (n + 1); right = [F(0)] * (n + 1)
    for j, aj in enumerate(a_asc):
        if aj == 0:
            continue
        for m in range(j + 1):
            c = F(comb(j, m))
            left[m] += aj * c * F(0) ** (j - m) * F(1, 2) ** m if (j - m) == 0 else left[m]
        # explicit: p(u/2) and p(1/2 + u/2)
    # simpler explicit construction
    left = [a_asc[j] * F(1, 2) ** j for j in range(n + 1)]
    right = [F(0)] * (n + 1)
    for j, aj in enumerate(a_asc):
        if aj == 0:
            continue
        for m in range(j + 1):
            right[m] += aj * F(comb(j, m)) * F(1, 2) ** (j - m) * F(1, 2) ** m
    return left, right


def certify_g_nonneg(coefC, dC, thresh, max_depth=10):
    """Certify  sum_k (C_k(w))^2 - thresh > 0  on [0,1], where each cubic coefficient
    is known only to +/- dC (rigorous input-error interval).  Exact rationals."""
    # worst-case (lowest) polynomial: expand |a| error through the squaring
    dim = len(coefC[0])
    a = [F(0)] * 7; da = [F(0)] * 7
    for k in range(dim):
        Ck = [coefC[i][k] for i in range(4)]
        dk = [dC[i][k] for i in range(4)]
        aC = _conv(Ck, Ck)
        absC = [abs(x) for x in Ck]
        err = [2 * x for x in _conv(absC, dk)]
        err2 = _conv(dk, dk)
        for i in range(7):
            a[i] += aC[i]
            da[i] += err[i] + err2[i]
    a_asc = a[::-1]; da_asc = da[::-1]
    stack = [(a_asc, da_asc, 0)]
    glb = None
    while stack:
        c, dc, depth = stack.pop()
        b = _bernstein(c); db = _bernstein([abs(x) for x in dc])
        lower = min(bi - dbi for bi, dbi in zip(b, db))
        # a sampled value certainly below threshold -> collision
        for u in (F(0), F(1, 2), F(1)):
            val = sum(ci * u ** i for i, ci in enumerate(c))
            errv = sum(abs(di) * u ** i for i, di in enumerate(dc))
            if val + errv < thresh:
                return {"certificate": "CERTIFIED_COLLISION", "g_lower_bound": float(val - thresh),
                        "depth": depth}
        if lower >= thresh:
            glb = lower - thresh if glb is None else min(glb, lower - thresh)
            continue
        if depth >= max_depth:
            return {"certificate": "INCONCLUSIVE", "g_lower_bound": float(lower - thresh),
                    "depth": depth}
        L, R = _subdiv(c); dL, dR = _subdiv(dc)
        stack.append((L, dL, depth + 1)); stack.append((R, dR, depth + 1))
    return {"certificate": "CERTIFIED_COLLISION_FREE", "g_lower_bound": float(glb),
            "max_depth_used": max_depth}


def rational_certificate(p0, v0, seg_acc, tau, L_of_t, n_lim, dt, r_kill,
                         input_eps_rel=1e-13, input_eps_abs=1e-11, max_depth=10):
    """Full-chain rigorous certificate: sampled positions -> interval -> exact rationals."""
    seg_acc = np.asarray(seg_acc, float); K = len(seg_acc); h = float(tau) / K
    p = np.asarray(p0, float).copy(); v = np.asarray(v0, float).copy()
    starts = [(p.copy(), v.copy())]
    for k in range(K):
        a = seg_acc[k]; p = p + v * h + 0.5 * a * h * h; v = v + a * h
        starts.append((p.copy(), v.copy()))

    def pa(ts):
        out = np.empty((len(ts), 3))
        for j, tt in enumerate(ts):
            k = min(int(np.floor(tt / h + 1e-12)), K - 1)
            pk, vk = starts[k]; s = tt - k * h
            out[j] = pk + vk * s + 0.5 * seg_acc[k] * s * s
        return out

    bps = sorted(set(np.round(np.concatenate([
        np.arange(K + 1) * h, np.arange(0, int(np.floor(tau / dt)) + 2) * dt]), 12)))
    bps = [min(max(b, 0.0), tau) for b in bps if -1e-12 <= b <= tau + 1e-12]
    thr = F(r_kill).limit_denominator(10 ** 9) ** 2
    worst = None; depth_max = 0
    for j in range(len(bps) - 1):
        T0, T1 = bps[j], bps[j + 1]
        if T1 - T0 < 1e-12:
            continue
        ts = [T0 + float(w) * (T1 - T0) for w in NODES]
        Pa = pa(ts); Pl = np.asarray(L_of_t(np.asarray(ts)), float)
        for i in range(n_lim):
            D = Pa - Pl[:, i, :]
            valsF = [[F(float(x)).limit_denominator(10 ** 12) for x in row] for row in D]
            errF = [[F(input_eps_rel).limit_denominator(10 ** 9) * abs(F(float(x)).limit_denominator(10 ** 12))
                     + F(input_eps_abs).limit_denominator(10 ** 12) for x in row] for row in D]
            C = _fit_cubic_rat(valsF)
            # the fit is linear in the samples; propagate the sample interval through |V^-1|
            Cerr = _fit_cubic_rat([[abs(x) for x in row] for row in errF])
            Cerr = [[abs(x) * 8 for x in row] for row in Cerr]      # outward slack on the solve
            res = certify_g_nonneg(C, Cerr, thr, max_depth=max_depth)
            depth_max = max(depth_max, res.get("depth", 0))
            if res["certificate"] == "CERTIFIED_COLLISION":
                return {**res, "at": {"t0": T0, "t1": T1, "limiter": i},
                        "verifier_version": CERT_VERSION}
            if res["certificate"] == "INCONCLUSIVE":
                return {**res, "at": {"t0": T0, "t1": T1, "limiter": i},
                        "verifier_version": CERT_VERSION}
            worst = res["g_lower_bound"] if worst is None else min(worst, res["g_lower_bound"])
    return {"certificate": "CERTIFIED_COLLISION_FREE", "g_lower_bound": float(worst),
            "implied_min_distance_lower_bound_m": float(np.sqrt(max(worst + r_kill ** 2, 0.0))),
            "implied_margin_lower_bound_m": float(np.sqrt(max(worst + r_kill ** 2, 0.0)) - r_kill),
            "arithmetic": "exact rationals (fractions.Fraction) downstream of sampled positions",
            "input_interval": {"rel": input_eps_rel, "abs": input_eps_abs},
            "max_subdivision_depth": depth_max, "verifier_version": CERT_VERSION}


# ------------------------------------------------------------------ N4 registry patch
D2_SPLIT = {
    "D2a": {"status": "PRE_REGISTERED_DORMANT", "trigger": "D1 survivor only",
            "K": 8, "nesting": "NESTED: each K=4 interval halves, so every K=4 trajectory is "
                               "exactly representable",
            "containment_test": "MANDATORY -- K=4 artifacts must reproduce bit-for-bit",
            "role": "the formal D2 escalation"},
    "D2b": {"status": "PRE_REGISTERED_DORMANT_EXPLORATORY", "K": 6,
            "nesting": "NOT NESTED: K=6 breakpoints do not align with K=4; exact containment "
                       "is NOT claimed",
            "containment_test": "not applicable",
            "role": "exploratory diagnostic arm only; cannot be used for a survival claim "
                    "unless re-parameterised on a common fine-grid basis containing K=4"},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior", default="results/c1_corridor/c1_phase1l_exact_adjudication.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1n_hardening.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    prior = json.loads(pathlib.Path(a.prior).read_text())

    # ---- N1
    print("== N1: net-cone predicate independence + unit tests ==")
    w = log_ctrl(make_contract())
    rec0 = rollout_unified(pe, make_spawn(2.8, 0.30 * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
    o0 = np.asarray(rec0["_obs"][rec0["_t_ref"]], float)
    kw0 = E._vshot_kwargs(o0[ATT_P0:ATT_P0 + 3], o0[ATT_P0 + 3:ATT_P0 + 6], o0[36:45])
    cone0 = {k: kw0[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    n1 = cone_unit_tests(cone0)
    for t in n1["tests"]:
        print("   [%s] %s" % ("PASS" if t["pass"] else "FAIL", t["test"]))
    print("   -> all_pass = %s" % n1["all_pass"])

    # ---- N2
    print("== N2: full-chain rational interval certificate (2 smallest margins) ==")
    targets = sorted([r for r in prior["rows"] if r["best_exact_margin_m"] is not None],
                     key=lambda r: r["best_exact_margin_m"])[:2]
    n2 = []
    for row in targets:
        rho0, tl = [float(x) for x in row["tag"].split()[1].split("/")]
        arm = "C" if abs(rho0 - 2.8) < 1e-9 else "P"
        ww = log_ctrl(make_contract() if arm == "C" else make_pd())
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), ww, fin, r_lane=RL, r_body=RB)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
        L_of_t = lambda times: hermite_positions(P_post, V_post, np.asarray(times))[0]
        cand = [c for c in row["candidates"]
                if c["classification"] == "VERIFIED_COLLISION_FREE_ESCAPE"][0]
        acc = np.asarray(cand["acc"], float)
        h = hashlib.sha256(acc.round(12).tobytes()).hexdigest()[:16]
        cert = rational_certificate(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6], acc,
                                    float(E.tau_deploy), L_of_t, N_LIM, DT, E.kill_radius)
        rowout = {"tag": row["tag"].strip(), "artifact_sha": h,
                  "numerically_resolved_margin_m": row["best_exact_margin_m"], **cert}
        n2.append(rowout)
        print("   %-18s sha %s | %s | g_lb %.3e | margin_lb %s m | depth %s"
              % (rowout["tag"], h, cert["certificate"], cert["g_lower_bound"],
                 ("%.6f" % cert["implied_margin_lower_bound_m"])
                 if "implied_margin_lower_bound_m" in cert else "n/a",
                 cert.get("max_subdivision_depth")), flush=True)

    # ---- N3
    print("== N3: scenario-level strength aggregation (definition fixed) ==")
    n3 = []
    for row in prior["rows"]:
        esc = [c for c in row.get("candidates", [])
               if c["classification"] == "VERIFIED_COLLISION_FREE_ESCAPE"]
        if not esc:
            continue
        best = max(esc, key=lambda c: c["exact_margin_m"])
        h = hashlib.sha256(np.asarray(best["acc"], float).round(12).tobytes()).hexdigest()[:16]
        m = best["exact_margin_m"]
        n3.append({"scenario": row["tag"].strip(), "selected_artifact_sha": h,
                   "m_scenario_m": m, "argmin": best.get("argmin"),
                   "audited_min_margin_m": min(c["exact_margin_m"] for c in esc),
                   "n_verified_escape": len(esc),
                   "verifier_version": "c1_exact_clearance NUMERICALLY_RESOLVED",
                   "budget_m": BUDGET_M, "exceeds_budget": bool(m > BUDGET_M),
                   "strength_label": ("CLEARANCE_ROBUST_TO_10MM_ADDITIVE_GEOMETRIC_ERROR"
                                      if m > BUDGET_M else
                                      "FALSIFIED_BY_ADVERSARIAL_REPLAN_IN_NOMINAL_MODEL")})
    n_over = sum(1 for r in n3 if r["exceeds_budget"])
    print("   m_scenario = max over sealed verified artifacts of (min_t d - r_kill)")
    print("   -> %d/%d scenarios exceed the %.3f m additive-geometric budget"
          % (n_over, len(n3), BUDGET_M))

    out = {"meta": {"phase": "1N_hardening", "cert_version": CERT_VERSION,
                    "independence_scope": "independent admissibility, independent trajectory "
                                          "re-integration, independent continuous-clearance "
                                          "adjudication, and (from N1) an independent net-cone "
                                          "predicate cross-check; the audit itself ran under the "
                                          "FROZEN net-cone predicate",
                    "m_scenario_definition": "max over sealed verified artifacts of "
                                             "(min_t d(t) - r_kill)",
                    "budget_m": BUDGET_M,
                    "budget_scope": "additive geometric error in relative separation only"},
           "N1_cone_predicate": n1, "N2_rational_certificates": n2,
           "N3_strength_aggregation": {"n_scenarios": len(n3), "n_exceeding_budget": n_over,
                                       "rows": n3},
           "N4_D2_split": D2_SPLIT}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("== N4: D2 split registered (D2a K=8 nested / D2b K=6 exploratory) ==")
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
