"""C-1 — FALSIFIER-v2: hierarchical A0 -> A1 -> A2 -> A3 with a cumulative bank.

THE ORDERING PRINCIPLE
----------------------
Solve the LOWEST-dimensional attacker class first and deterministically, then let
each wider class INHERIT everything the narrower one found.  The legacy falsifier
did the opposite -- it sampled K=4 vectors at random and hoped a K=1 attack would
fall out -- and it missed four within-class counterexamples that way.

    A0   K=1   deterministic direction grid x magnitude sweep + tangent refinement
    A1   K=2   inherits A0
    A2   K=4   inherits A0, A1
    A3   K=8   inherits A0, A1, A2

Since tau/K_n divides tau/K_m whenever K_m | K_n, every earlier attack is exactly
representable later by segment repetition.  That is what makes inheritance sound.

THE THREE INVARIANTS, ENFORCED NOT TRUSTED
------------------------------------------
  cumulative bank      B(A_n) is a superset of B(A_{n-1}) plus every verified
                       counterexample known at that point
  incumbent insertion  each stage's initial population CONTAINS the previous
                       stage's incumbents, embedded
  monotonicity         S*(A0) >= S*(A1) >= S*(A2) >= S*(A3)
                       (minimisation: wider classes may only go lower)
                       structurally guaranteed by insertion, then ASSERTED.  A
                       violation is a protocol defect, not a result.

SCORING -- one scalar, one boundary, one unit
---------------------------------------------
    S(a) = max( -kill_margin, -cone_exit_margin )   if ||a||_k <= a_att_max for all k
         = +inf                                      otherwise
    escape  <=>  S(a) < 0

Both terms are METRES with the same sign convention (>0 = escape-favourable):
  kill_margin      min over the deploy window of (distance to nearest limiter) - r_kill
  cone_exit_margin max(lateral, axial) outside distance from the SE(3) net cone,
                   where lateral = (half_angle - theta_net) * ||r||.  That is the
                   small-angle arc-length surrogate for the true perpendicular
                   distance ||r||*sin(half_angle - theta_net); the two differ by
                   O(dtheta^3), i.e. below 1e-7 relative at the angles in play.
                   Documented because a dimensionless residual inside this max
                   would reintroduce the units error the review flagged.

WHAT THIS MODULE IS NOT
-----------------------
A frozen confirmatory falsifier.  It was developed with four known misses in
hand, so its NULLS carry no strength.  Only its POSITIVE findings (verified
counterexamples) are evidence.  Freezing, re-seeding and held-out attacker
conditions come after.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import N_LIM
from shepherd.scripts.c1_corridor_probe import ATT_P0
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_replan_falsifier import kill_margin, cone_exit_margin
from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for, DIAG
from shepherd.scripts.c1_phase1p_modes import cone_components
from shepherd.scripts.c1_phase1p_6a_dynamic import dynamic_inward
from shepherd.scripts.c1_phase1p_d0 import d0_seed
from shepherd.scripts.c1_phase1p_falsifier_v2_k1 import k1_search, ADM_TOL
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

STAGES = [{"id": "A0", "K": 1}, {"id": "A1", "K": 2},
          {"id": "A2", "K": 4}, {"id": "A3", "K": 8}]
SCALES = [0.05, 0.01, 0.002, 0.0004]      # x a_att_max, multi-scale refinement
N_PER_SCALE = 96                           # draws per incumbent per scale
TOP_M = 24                                 # incumbents carried between scales/stages
MONO_TOL_M = 1e-12
ALIGN_K = 20                               # candidates entering the alignment audit
CHUNK = 16384
N_GLOBAL_DIRS = 64                         # coarse direction set for stage-K global starts


def _global_dirs(n):
    i = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)
    th = np.pi * (1.0 + 5.0 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi),
                     np.cos(phi)], axis=1)


GLOBAL_DIRS = _global_dirs(N_GLOBAL_DIRS)


def s_proxy(E, pa, va, L, cone, tau, A):
    """A is (n, K, 3).  Sampled-margin S."""
    A = np.asarray(A, float)
    out_S = np.empty(len(A)); out_km = np.empty(len(A)); out_cm = np.empty(len(A))
    for i in range(0, len(A), CHUNK):
        C = A[i:i + CHUNK]
        ep, tf, pts = V._seg_paths_turn(pa, va, C, tau=tau, attacker_turn_limited=False,
                                        omega_att_max=None, e_att=None, n_t=24)
        km = kill_margin(pts, L, E.kill_radius, tau)
        cm = cone_exit_margin(ep, **cone)
        ok = tf & (np.linalg.norm(C, axis=2).max(axis=1) <= float(E.a_att_max) + ADM_TOL)
        out_S[i:i + CHUNK] = np.where(ok, np.maximum(-km, -cm), np.inf)
        out_km[i:i + CHUNK] = km; out_cm[i:i + CHUNK] = cm
    return out_S, out_km, out_cm


def s_auth(E, pa, va, L, cone, tau, acc):
    """Authoritative S: continuous clearance for the kill term."""
    acc = np.asarray(acc, float)
    ep, tf, _p = V._seg_paths_turn(pa, va, acc[None], tau=tau, attacker_turn_limited=False,
                                   omega_att_max=None, e_att=None, n_t=24)
    lat, axi, _x, _r, _g = cone_components(ep, **cone)
    cm = float(max(lat[0], axi[0]))
    r = exact_min_clearance(pa, va, acc, tau, L, N_LIM, DT, E.kill_radius)
    ok = bool(tf[0] and np.linalg.norm(acc, axis=1).max() <= float(E.a_att_max) + ADM_TOL)
    S = (max(-float(r["exact_margin_m"]), -cm) if ok else float("inf"))
    return {"S_auth_m": S, "continuous_kill_margin_m": float(r["exact_margin_m"]),
            "cone_exit_margin_m": cm, "admissible": ok, "verdict": r["verdict"],
            "is_escape": bool(ok and S < 0.0
                              and r["verdict"] == "VERIFIED_COLLISION_FREE")}


def embed(acc, K):
    """Re-express a bank entry at segment count K.

    K_m | K   -> exact repetition (the nesting that makes inheritance sound).
    K | K_m   -> only legal if the entry is CONSTANT within each block of K_m/K
                 segments; then the reduction is exact too.  A D2a K=8 witness is
                 constant, so it reduces to K=2 without loss.
    otherwise -> None, and the caller counts the skip rather than silently
                 dropping or, worse, resampling it into something else.
    """
    a = np.asarray(acc, float)
    if a.ndim == 1:
        a = a[None, :]
    m = len(a)
    if K % m == 0:
        return np.repeat(a, K // m, axis=0)
    if m % K == 0:
        blk = a.reshape(K, m // K, 3)
        if np.abs(blk - blk[:, :1, :]).max() < 1e-12:
            return blk[:, 0, :]
    return None


def temporal_starts(K, a_max, U):
    """Stage-K global starts that do NOT descend from A0.

    Without these, A1..A3 only ever polish whatever A0 handed them, and a
    time-varying escape basin sitting away from A0's optimum would never be
    visited -- which would make "K=1 is enough" an artefact of the search order
    rather than an observation about the problem.  Every pattern here is
    deterministic and is generated fresh per stage.

        constant          the K=1 shape, re-derived independently
        single pulse      one saturated segment, the rest zero, at each index
        half / half       first half one way, second half the opposite
        alternating       sign flip every segment
        magnitude ramp    up and down
        two-phase         two DIFFERENT grid directions, switched at the midpoint
        rotating          direction swept through an angle across the window
    """
    U = np.asarray(U, float)
    out = []
    for u in U:
        for m in (1.0, 0.7):
            a = m * a_max * u
            if K == 1:
                out.append(a[None, :]); continue
            out.append(np.repeat(a[None, :], K, axis=0))
            for j in range(K):
                p = np.zeros((K, 3)); p[j] = a_max * u; out.append(p)
            h = np.zeros((K, 3)); h[:K // 2] = a; h[K // 2:] = -a
            out.append(h); out.append(-h)
            out.append(np.repeat(a[None, :], K, axis=0)
                       * ((-1.0) ** np.arange(K))[:, None])
            r = np.linspace(0.2, 1.0, K)[:, None] * (a_max * m) * u[None, :]
            out.append(r); out.append(r[::-1].copy())
    if K > 1:
        n = len(U)
        for i in range(n):                                  # two-phase, paired directions
            u1, u2 = U[i], U[(i + n // 3) % n]
            t = np.zeros((K, 3)); t[:K // 2] = a_max * u1; t[K // 2:] = a_max * u2
            out.append(t)
        b = np.array([0.0, 0.0, 1.0])
        for u in U:                                          # rotating direction sweep
            e1 = np.cross(u, b)
            if np.linalg.norm(e1) < 1e-9:
                e1 = np.cross(u, np.array([0.0, 1.0, 0.0]))
            e1 /= np.linalg.norm(e1)
            for tot in (np.radians(2.0), np.radians(10.0)):
                ang = np.linspace(-tot / 2, tot / 2, K)
                d = (np.cos(ang)[:, None] * u[None, :] + np.sin(ang)[:, None] * e1[None, :])
                d /= np.linalg.norm(d, axis=1, keepdims=True)
                out.append(a_max * d)
    return np.asarray(out, float)


def segment_descent(E, pa, va, L, cone, tau, a0, K, rounds=3):
    """Deterministic per-SEGMENT coordinate descent.

    The multi-scale Gaussian pass perturbs all 3K coordinates at once, which at
    K=8 almost never improves on an already-refined incumbent -- so the wider
    stages would inherit A0's optimum and add nothing.  This pass instead moves
    ONE segment at a time, which is exactly the freedom K>1 buys over K=1.
    """
    a = np.asarray(a0, float).copy()
    S = s_proxy(E, pa, va, L, cone, tau, a[None])[0][0]
    if K == 1:
        return a, float(S)
    amax = float(E.a_att_max)
    steps = np.array([0.3, 0.1, 0.03, 0.01, 0.003]) * amax
    axes = np.concatenate([np.eye(3), -np.eye(3)], axis=0)
    for _r in range(rounds):
        improved = False
        for k in range(K):
            cand = []
            for s in steps:
                for u in axes:
                    b = a.copy(); b[k] = b[k] + s * u
                    cand.append(b)
                b = a.copy(); n = np.linalg.norm(b[k])
                if n > 1e-9:
                    for f in (1.02, 0.98, 1.005, 0.995):
                        c = a.copy(); c[k] = b[k] * f
                        cand.append(c)
            C = clip_ball(np.asarray(cand, float), amax)
            Sc = s_proxy(E, pa, va, L, cone, tau, C)[0]
            j = int(np.argmin(Sc))
            if Sc[j] < S - 1e-15:
                a, S, improved = C[j].copy(), float(Sc[j]), True
        if not improved:
            break
    return a, float(S)


def clip_ball(A, a_max):
    n = np.linalg.norm(A, axis=2, keepdims=True)
    return np.where(n > a_max, A * (a_max / (n + 1e-15)), A)


def refine(E, pa, va, L, cone, tau, seeds, K, rng):
    """Multi-scale refinement.  Incumbents are re-inserted at every scale, so the
    running best can never degrade."""
    inc = np.asarray(seeds, float)
    S, _k, _c = s_proxy(E, pa, va, L, cone, tau, inc)
    o = np.argsort(S)[:TOP_M]
    inc, best = inc[o], float(S[o[0]])
    best_a = inc[0].copy()
    for sc in SCALES:
        sig = sc * float(E.a_att_max)
        draws = rng.normal(0.0, sig, size=(len(inc), N_PER_SCALE, K, 3))
        cand = clip_ball(inc[:, None, :, :] + draws, float(E.a_att_max)
                         ).reshape(-1, K, 3)
        pool = np.concatenate([inc, cand], axis=0)          # incumbents preserved
        Sp, _k, _c = s_proxy(E, pa, va, L, cone, tau, pool)
        o = np.argsort(Sp)[:TOP_M]
        inc = pool[o]
        if float(Sp[o[0]]) < best:
            best, best_a = float(Sp[o[0]]), pool[o[0]].copy()
    return inc, best, best_a


def alignment(E, pa, va, L, cone, tau, pool, S_proxy):
    """Property test 10 -- does the search proxy rank like the authoritative score?"""
    idx = np.argsort(S_proxy)[:ALIGN_K]
    auth = [s_auth(E, pa, va, L, cone, tau, pool[i]) for i in idx]
    Sa = np.asarray([a["S_auth_m"] for a in auth], float)
    order_auth = np.argsort(Sa)
    ov = {}
    for k in (1, 5, 10):
        ov["top%d_overlap" % k] = int(len(set(range(k)) & set(order_auth[:k].tolist())))
    return {"n_audited": int(len(idx)),
            "best_proxy_authoritative_S_m": float(Sa[0]),
            "best_authoritative_S_m": float(Sa[order_auth[0]]),
            "proxy_rank_of_best_authoritative": int(order_auth[0]) + 1,
            "authoritative_rank_of_best_proxy": int(np.where(order_auth == 0)[0][0]) + 1,
            "proxy_minus_authoritative_S_at_best_proxy_m":
                float(S_proxy[idx[0]] - Sa[0]),
            **ov}


def run_cell(E, pa, va, L, cone, tau, scenario_id, known_escapes):
    """A0 -> A3 with a cumulative bank.  Returns per-stage records."""
    bank = []                                    # list of (K,3) arrays, cumulative
    for e in known_escapes:                      # every verified counterexample known
        bank.append(np.asarray(e, float))
    out, prev_best = [], np.inf
    for st in STAGES:
        K = st["K"]
        rng = np.random.default_rng(int(d0_seed(
            stage_id="V2-" + st["id"], rng_role="refine", scenario_id=scenario_id,
            reset_id=DIAG["reset"], attacker_class="K%d-pwc" % K,
            restart_id=0, base_seed=7000)))
        skipped = 0
        if st["id"] == "A0":
            res = k1_search(E, pa, va, L, cone, tau,
                            seed_directions=[np.asarray(b, float)[0]
                                             / np.linalg.norm(np.asarray(b, float)[0])
                                             for b in bank] if bank else ())
            seeds = res["pool"][:, None, :]                  # (n,1,3)
            n_eval = res["n_candidates_evaluated"]
        else:
            em = [embed(b, K) for b in bank]
            skipped = sum(1 for x in em if x is None)
            inherited = np.stack([x for x in em if x is not None], axis=0)
            fresh = temporal_starts(K, float(E.a_att_max), GLOBAL_DIRS)
            seeds = np.concatenate([inherited, fresh], axis=0)
            n_eval = len(fresh)
        # provenance: did any INDEPENDENT temporal start beat the inherited optimum?
        #
        # It has to be refined-vs-refined.  A first attempt compared the RAW
        # independent starts against the already-refined inherited incumbent; the
        # raw starts were 55-82 mm worse, so global top-M selection discarded every
        # one of them before refinement and the test was vacuous.  Each branch now
        # gets its own multi-scale refinement budget and the comparison is made
        # after both have converged.
        prov = {}
        if st["id"] != "A0":
            inc_i, best_i, a_i = refine(E, pa, va, L, cone, tau, inherited, K, rng)
            inc_f, best_f, a_f = refine(E, pa, va, L, cone, tau, fresh, K,
                                        np.random.default_rng(int(d0_seed(
                                            stage_id="V2-" + st["id"], rng_role="fresh",
                                            scenario_id=scenario_id,
                                            reset_id=DIAG["reset"],
                                            attacker_class="K%d-pwc" % K,
                                            restart_id=1, base_seed=7100))))
            prov = {"n_independent_temporal_starts": int(len(fresh)),
                    "raw_best_independent_start_S_m":
                        float(s_proxy(E, pa, va, L, cone, tau, fresh)[0].min()),
                    "refined_inherited_S_m": best_i,
                    "refined_independent_S_m": best_f,
                    "independent_beats_inherited_after_refinement":
                        bool(best_f < best_i - 1e-15),
                    "comparison": "refined vs refined; each branch gets its own "
                                  "multi-scale budget"}
            if best_f < best_i:
                inc, best, best_a = inc_f, best_f, a_f
            else:
                inc, best, best_a = inc_i, best_i, a_i
            keep = min(TOP_M // 2, len(inc_f))
            inc = np.concatenate([inc[:TOP_M - keep], inc_f[:keep]], axis=0)
        else:
            inc, best, best_a = refine(E, pa, va, L, cone, tau, seeds, K, rng)
        # the freedom K>1 actually buys: move one segment at a time
        sd_a, sd_S = segment_descent(E, pa, va, L, cone, tau, best_a, K)
        if sd_S < best:
            best, best_a = sd_S, sd_a
            inc = np.concatenate([sd_a[None], inc[:TOP_M - 1]], axis=0)
        Sp, _k, _c = s_proxy(E, pa, va, L, cone, tau, inc)
        al = alignment(E, pa, va, L, cone, tau, inc, Sp)
        au = s_auth(E, pa, va, L, cone, tau, best_a)
        mono = bool(best <= prev_best + MONO_TOL_M)
        # cumulative bank grows; nothing is ever dropped
        bank = bank + [inc[i] for i in range(min(TOP_M, len(inc)))]
        out.append({"stage": st["id"], "K": K,
                    "n_bank_entries_not_representable": int(skipped),
                    "n_grid_or_fresh_candidates": int(n_eval),
                    "independent_start_provenance": prov,
                    "n_refine_candidates": int(len(inc) * N_PER_SCALE * len(SCALES)),
                    "bank_size_after": len(bank),
                    "best_S_proxy_m": best,
                    "best_authoritative": au,
                    "is_escape": au["is_escape"],
                    "attack_policy_hash": G.attack_policy_hash(best_a),
                    "monotone_vs_previous": mono,
                    "alignment": al})
        prev_best = min(prev_best, best)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2a", default="results/c1_corridor/c1_phase1p_d2a.json")
    ap.add_argument("--k1", default="results/c1_corridor/c1_phase1p_falsifier_v2_k1.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_falsifier_v2.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d2a = json.loads(pathlib.Path(a.d2a).read_text())
    k1j = json.loads(pathlib.Path(a.k1).read_text())

    known = {}
    for r in d2a["rows"]:
        for e in r["d2a"]["escapes"]:
            known.setdefault((r["witness"], r["arm"]), []).append(np.asarray(e["acc"], float))
    for r in k1j["rows"]:
        for e in r["k1_escapes"][:1]:
            known.setdefault((r["witness"], r["arm"]), []).append(
                np.asarray(e["acc_k1"], float)[None, :])

    print("== FALSIFIER-v2 — hierarchical A0..A3 with a cumulative bank ==")
    print("   S(a) = max(-kill, -cone) in METRES; escape <=> S<0; minimisation")
    print("   invariants: cumulative bank, incumbent insertion, "
          "S*(A0) >= S*(A1) >= S*(A2) >= S*(A3)\n")
    print("   %-22s %-10s %10s %10s %10s %10s %s"
          % ("scenario", "arm", "A0", "A1", "A2", "A3", "esc"))

    rows, mono_bad = [], []
    for r in d2a["rows"]:
        tag, arm, dl = r["witness"], r["arm"], r["selected_delta_m"]
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

        st = run_cell(E, pa, va, L, cone, tau, tag, known.get((tag, arm), []))
        esc = [s["stage"] for s in st if s["is_escape"]]
        bad = [s["stage"] for s in st if not s["monotone_vs_previous"]]
        if bad:
            mono_bad.append({"witness": tag, "arm": arm, "stages": bad})
        rows.append({"witness": tag, "arm": arm, "selected_delta_m": dl,
                     "d2a_verdict": r["verdict"],
                     "seeded_with_known_counterexamples": len(known.get((tag, arm), [])),
                     "stages": st,
                     "escape_stages": esc,
                     "verdict": ("FALSIFIED_BY_FALSIFIER_V2" if esc else
                                 "NO_ESCAPE_FOUND_BY_V2_DEVELOPMENT_BUILD")})
        print("   %-22s %-10s %10.6f %10.6f %10.6f %10.6f %s%s"
              % (tag, arm, st[0]["best_S_proxy_m"], st[1]["best_S_proxy_m"],
                 st[2]["best_S_proxy_m"], st[3]["best_S_proxy_m"],
                 ",".join(esc) if esc else "-",
                 "  ** MONOTONICITY VIOLATION %s **" % bad if bad else ""), flush=True)

    fal = [r for r in rows if r["escape_stages"]]
    seeded = {(r["witness"], r["arm"]) for r in rows
              if r["seeded_with_known_counterexamples"]}
    new = [r for r in fal if (r["witness"], r["arm"]) not in seeded]
    ov = {k: int(np.median([s["alignment"]["top5_overlap"]
                            for r in rows for s in r["stages"] if s["stage"] == k]))
          for k in ("A0", "A1", "A2", "A3")}
    print("\n   cells with an escape at some stage : %d / %d" % (len(fal), len(rows)))
    print("   of which NOT seeded with a known one: %d" % len(new))
    print("   monotonicity                        : %s"
          % ("all cells non-increasing across A0..A3" if not mono_bad
             else "VIOLATED %s" % mono_bad))
    print("   proxy/authoritative top-5 overlap   : %s (median of 5)" % ov)
    print("\n   NOTE: this is a DEVELOPMENT build. Its nulls carry no strength; only "
          "its verified counterexamples are evidence.")

    out = {"meta": {"script": "c1_falsifier_v2", "protocol": "FALSIFIER-v2",
                    "stages": STAGES, "scales_x_a_max": SCALES,
                    "n_per_scale": N_PER_SCALE, "top_m": TOP_M,
                    "status": "DEVELOPMENT_BUILD — developed with four known misses "
                              "in hand; nulls are not strength evidence",
                    "invariants": {
                        "cumulative_bank": "B(A_n) contains B(A_{n-1}) and every "
                                           "verified counterexample known at that point",
                        "incumbent_insertion": "each stage's initial population contains "
                                               "the previous stage's incumbents, embedded "
                                               "by exact segment repetition",
                        "monotonicity": "S*(A0) >= S*(A1) >= S*(A2) >= S*(A3), asserted"},
                    "units": "both terms of S are metres; cone lateral is the "
                             "small-angle arc-length surrogate (half_angle-theta)*||r||, "
                             "differing from ||r||*sin(.) by O(dtheta^3)",
                    "confirmation_still_required": [
                        "freeze code, score and budget",
                        "re-execute all cells with NEW search seeds",
                        "known escapes used only as regression canaries",
                        "held-out attacker initial conditions and cone geometry",
                        "only then re-issue controller survival labels"]},
           "monotonicity_violations": mono_bad,
           "n_cells_with_escape": len(fal),
           "n_cells_with_escape_not_seeded": len(new),
           "median_top5_overlap_by_stage": ov,
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if not mono_bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
