"""C-1 Phase 1J — ADVERSARIAL_REPLAN_FALSIFIER.

Role, stated up front: this is a FALSIFIER, not a certifier.  A numerical search
that finds an escape proves the witness unsafe; failing to find one proves nothing
about safety.  Verdicts are therefore only ever

    FALSIFIED_BY_ADVERSARIAL_REPLAN     escape found, v_soft_replan < theta
    SURVIVED_ADVERSARIAL_REPLAN_SEARCH  no escape found by this search

and never ADVERSARIAL_DYNAMIC_CERTIFIED, which needs conservative completeness
(global optimality or a sound reachable-set over-approximation) that this does not
have.

What it does
------------
The E1.5 `actual` model REMASKS a fixed attacker path bank against the realised
limiter motion: the attacker never gets to re-choose its path knowing the ring
will move.  This script lets it.  The attacker control is K piecewise-constant
acceleration segments over [0, tau] with ||a|| <= a_att_max, built through the
SAME `viability._seg_paths_turn` the union itself uses, so the new paths are
structurally identical to the bank's dogleg block.

Path set (mandated containment):

    P_replan = P_fixed  UNION  P_optimized

so v_soft_replan <= v_soft_remask holds STRUCTURALLY.  If adding replanned paths
ever raises viability, that is an implementation error or a sample mismatch, and
the containment block below is written to catch exactly that.

Objective, aligned with the final judgment quantity (no distance/offset proxy):

    score(path) = min( kill_margin , cone_exit_margin )        [metres]
      kill_margin      = min over substeps s and limiters i of
                         ||p(s) - L_i(s)|| - r_kill            > 0 <=> path survives
      cone_exit_margin = max( lateral distance outside the net cone surface,
                              axial distance outside [range_min, range_max] )
                                                               > 0 <=> not caught

score > 0 is exactly "feasible AND not caught" — an escape — so the optimizer
cannot win by gaming a surrogate that is not the verdict.

Search and confirmation are separated for the ATTACKER too: escapes are found with
search restarts, the escape artifact is sealed, and the verdict is recomputed with
restart seeds never used in the search.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, R_BODY, M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import (judge_models, hermite_positions, block_times,
                                         _mask_moving, N_T, DT)
from shepherd.scripts.c1_plant_bound import solve_witness_hold, make_lp_arm, solve_witness
from shepherd.game import viability as V

SEARCH_REPLAN_SEEDS = (52_000_001, 52_000_002)      # find the escape
CONFIRM_REPLAN_SEEDS = (63_000_101, 63_000_102)     # never used in the search
CONFIRM_CERT_SEEDS = (91_000_101, 91_000_102, 91_000_103)


# ------------------------------------------------------------------ margins
def cone_exit_margin(endpoints, *, net_apex, n_F, theta_net, range_min, range_max):
    """Signed metres OUTSIDE the SE(3) net cone (>0 => not caught).

    Mirrors viability._caught_se3_cone exactly: caught iff axial in band AND
    half-angle <= theta_net.  Outside distance = max(lateral overshoot beyond the
    cone surface, axial overshoot beyond the band)."""
    apex = np.asarray(net_apex, float); n = np.asarray(n_F, float)
    n = n / (np.linalg.norm(n) + 1e-12)
    r = np.asarray(endpoints, float) - apex[None, :]
    rn = np.linalg.norm(r, axis=1)
    ax = r @ n
    ang = np.arccos(np.clip(np.where(rn < 1e-12, 1.0, ax / (rn + 1e-12)), -1.0, 1.0))
    lateral = (ang - float(theta_net)) * rn                      # >0 => outside the cone wall
    rmax = np.inf if range_max is None else float(range_max)
    axial = np.maximum(float(range_min) - ax, ax - rmax)         # >0 => outside the band
    m = np.maximum(lateral, axial)
    return np.where(rn < 1e-12, -np.inf, m)                      # at apex => always caught


def kill_margin(paths, L_of_t, kill_radius, tau):
    """min over substeps and limiters of (distance - r_kill); >0 => never killed."""
    n, T, _ = paths.shape
    Lt = L_of_t(block_times(T, tau))                             # (T, nL, 3)
    d = np.linalg.norm(paths[:, :, None, :] - Lt[None, :, :, :], axis=3)   # (n, T, nL)
    return d.min(axis=(1, 2)) - float(kill_radius)


# ------------------------------------------------------------------ replan CEM
def replan_search(x0, v0, *, tau, a_att_max, L_of_t, kill_radius, cone_kw,
                  K=4, pop=192, iters=14, elite=24, seed=0, warm=None):
    """CEM over K piecewise-constant attacker accelerations.  Maximises
    min(kill_margin, cone_exit_margin); >0 is an escape.  Returns the full
    population history's best plus every escape found."""
    rng = np.random.default_rng(seed)
    mu = np.zeros((K, 3)); sig = np.full((K, 3), a_att_max * 0.75)
    if warm is not None and len(warm):
        mu = np.asarray(warm, float).reshape(K, 3)
    best = {"score": -np.inf, "acc": None}
    escapes = []
    for it in range(iters):
        cand = rng.normal(mu[None], sig[None], size=(pop, K, 3))
        if warm is not None and it == 0:
            cand[0] = mu
        nrm = np.linalg.norm(cand, axis=2, keepdims=True)
        cand = np.where(nrm > a_att_max, cand * (a_att_max / (nrm + 1e-12)), cand)
        ep, tf, pts = V._seg_paths_turn(x0, v0, cand, tau=tau, attacker_turn_limited=False,
                                        omega_att_max=None, e_att=None, n_t=N_T)
        km = kill_margin(pts, L_of_t, kill_radius, tau)
        cm = cone_exit_margin(ep, **cone_kw)
        sc = np.minimum(km, cm)
        sc = np.where(tf, sc, -np.inf)
        for i in np.nonzero(sc > 0)[0]:
            escapes.append({"acc": cand[i].tolist(), "score": float(sc[i]),
                            "kill_margin": float(km[i]), "cone_exit_margin": float(cm[i]),
                            "endpoint": ep[i].tolist(), "iter": int(it)})
        j = int(np.argmax(sc))
        if sc[j] > best["score"]:
            best = {"score": float(sc[j]), "acc": cand[j].copy(),
                    "kill_margin": float(km[j]), "cone_exit_margin": float(cm[j])}
        idx = np.argsort(-sc)[:elite]
        mu = cand[idx].mean(axis=0); sig = cand[idx].std(axis=0) + 1e-3
    return best, escapes


# ------------------------------------------------------------------ per-witness audit
def audit(pe, rec, *, n_cert, cert_seeds, replan_seeds, K, pop, iters, tag):
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    cone_kw = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}

    def L_actual(times):
        return hermite_positions(P_post, V_post, times)[0]

    out = {"tag": tag, "replan_seeds": list(replan_seeds), "K": K, "pop": pop, "iters": iters}
    per_seed_fixed, per_seed_replan, all_esc = [], [], []
    n_added_total = 0
    for sd in cert_seeds:
        u = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max, n=n_cert,
                                    n_segments=max(int(E.n_segments), 2), seed=int(sd), **kw)
        masks = [_mask_moving(pb, L_actual, E.kill_radius, tau) for pb in u.path_blocks]
        feas0 = np.concatenate(masks, axis=0) & u.turn_feasible
        caught0 = np.asarray(u.caught, bool)
        k0, n0 = int((caught0 & feas0).sum()), int(feas0.sum())
        per_seed_fixed.append(k0 / n0 if n0 else float("nan"))

        # warm start: the bank's own best single-segment accel, broadcast to K segments
        acc1 = V.reachable_accels(E.a_att_max, n_cert, int(sd))
        ep1, tf1, pts1 = V._seg_paths_turn(p_att, v_att,
                                           np.repeat(acc1[:, None, :], K, axis=1), tau=tau,
                                           attacker_turn_limited=False, omega_att_max=None,
                                           e_att=None, n_t=N_T)
        sc1 = np.minimum(kill_margin(pts1, L_actual, E.kill_radius, tau),
                         cone_exit_margin(ep1, **cone_kw))
        warm = np.repeat(acc1[int(np.argmax(sc1))][None, :], K, axis=0)

        esc_acc = []
        for rs in replan_seeds:
            best, escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                       L_of_t=L_actual, kill_radius=E.kill_radius,
                                       cone_kw=cone_kw, K=K, pop=pop, iters=iters,
                                       seed=int(rs) + int(sd), warm=warm)
            all_esc.append({"cert_seed": int(sd), "replan_seed": int(rs),
                            "best_score": best["score"],
                            "n_escapes": len(escs),
                            "top": sorted(escs, key=lambda z: -z["score"])[:3]})
            esc_acc += [e["acc"] for e in escs]

        if esc_acc:
            A = np.asarray(esc_acc, float)
            ep2, tf2, pts2 = V._seg_paths_turn(p_att, v_att, A, tau=tau,
                                               attacker_turn_limited=False, omega_att_max=None,
                                               e_att=None, n_t=N_T)
            feas2 = _mask_moving(pts2, L_actual, E.kill_radius, tau) & tf2
            caught2 = V._caught_se3_cone(ep2, **cone_kw)
            k1 = k0 + int((caught2 & feas2).sum()); n1 = n0 + int(feas2.sum())
            n_added_total += int(feas2.sum())
        else:
            k1, n1 = k0, n0
        per_seed_replan.append(k1 / n1 if n1 else float("nan"))

    vf = float(np.mean(per_seed_fixed)); vr = float(np.mean(per_seed_replan))
    out.update({"v_soft_fixed_path": vf, "v_soft_replan": vr,
                "per_seed_fixed": per_seed_fixed, "per_seed_replan": per_seed_replan,
                "n_replan_paths_added_feasible": n_added_total,
                "monotone_ok": bool(vr <= vf + 1e-12),
                "escape_found": bool(any(e["n_escapes"] > 0 for e in all_esc)),
                "best_score_m": max(e["best_score"] for e in all_esc) if all_esc else None,
                "searches": all_esc})
    return out


def build(pe_cfg="configs/m3a_a3e_p1.yaml"):
    env_cfg, m3, _t = _load(pe_cfg)
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"])
    return pe, make_finisher_fn(THETA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-cert", type=int, default=20000)
    ap.add_argument("--K", type=int, default=4)
    ap.add_argument("--pop", type=int, default=192)
    ap.add_argument("--iters", type=int, default=14)
    ap.add_argument("--out", default="results/c1_corridor/c1_replan_falsifier.json")
    a = ap.parse_args()
    pe, fin = build(); E = pe.ad.env
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    theta = pe.theta

    # scenario-level witnesses (pre-fire histories differ even where the post-fire
    # certification state coincides -- see the review's correction on effective n)
    RH = [(2.8, 0.15, 2), (3.2, 0.25, 5), (4.0, 0.40, 7), (5.0, 0.55, 10)]
    BASE = [(2.8, 0.30, "C"), (3.2, 0.50, "C"), (3.2, 0.70, "P"),
            (4.0, 0.70, "C"), (4.0, 0.70, "P"), (5.0, 1.00, "P")]
    MAXCLR = [(5.0, 0.55, 10), (4.0, 0.40, 7)]      # positive control: already remask-falsified

    rows, containment = [], []
    print("== Phase 1J: ADVERSARIAL_REPLAN_FALSIFIER (K=%d, pop=%d, iters=%d) ==" % (a.K, a.pop, a.iters))

    def run(tag, rec, extra=None):
        r = audit(pe, rec, n_cert=a.n_cert, cert_seeds=CONFIRM_CERT_SEEDS,
                  replan_seeds=CONFIRM_REPLAN_SEEDS, K=a.K, pop=a.pop, iters=a.iters, tag=tag)
        # containment #1: fixed-path-only reproduction of the E1.5 `actual` model
        jm = judge_models(pe, rec, n_cert=a.n_cert, seeds=CONFIRM_CERT_SEEDS)
        r["e15_actual_v_soft"] = jm["actual"]["v_soft"]
        r["containment_fixed_path_exact"] = bool(
            abs(r["v_soft_fixed_path"] - float(np.mean(jm["actual"]["per_seed_v_soft"]))) < 1e-12)
        r["verdict"] = ("FALSIFIED_BY_ADVERSARIAL_REPLAN" if r["v_soft_replan"] < theta
                        else "SURVIVED_ADVERSARIAL_REPLAN_SEARCH")
        if extra: r.update(extra)
        rows.append(r)
        containment.append({"tag": tag, "fixed_path_exact": r["containment_fixed_path_exact"],
                            "monotone": r["monotone_ok"]})
        print("   %-28s fixed %.4f -> replan %.4f | escapes %s (best %s m, +%d feasible paths) | "
              "containment exact=%s monotone=%s | %s"
              % (tag, r["v_soft_fixed_path"], r["v_soft_replan"],
                 "YES" if r["escape_found"] else "no",
                 ("%.3f" % r["best_score_m"]) if r["best_score_m"] is not None else "n/a",
                 r["n_replan_paths_added_feasible"],
                 r["containment_fixed_path_exact"], r["monotone_ok"], r["verdict"]), flush=True)

    for rho0, tl, f in RH:
        s, d, m = solve_witness_hold(rho0, f)
        w = log_ctrl(make_lp_arm(s))
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        run("RH  %.1f/%.2f f=%d" % (rho0, tl, f), rec, {"class": "RH_hold", "lp_d": round(d, 4)})

    for rho0, tl, f in MAXCLR:
        s, m = solve_witness(rho0, f)
        w = log_ctrl(make_lp_arm(s))
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        run("MAXCLR(ctrl) %.1f/%.2f" % (rho0, tl), rec, {"class": "maxclr_positive_control"})

    for rho0, tl, arm in BASE:
        w = log_ctrl(make_contract() if arm == "C" else make_pd())
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        run("BASE %.1f/%.2f %s" % (rho0, tl, arm), rec, {"class": "legacy_baseline"})

    out = {"meta": {"phase": "1J_adversarial_replan_falsifier", "role": "FALSIFIER, not certifier",
                    "theta": theta, "n_cert": a.n_cert, "K": a.K, "pop": a.pop, "iters": a.iters,
                    "cert_seeds": list(CONFIRM_CERT_SEEDS),
                    "replan_seeds_confirm": list(CONFIRM_REPLAN_SEEDS),
                    "replan_seeds_search": list(SEARCH_REPLAN_SEEDS),
                    "path_set": "P_replan = P_fixed UNION P_optimized (containment mandated)",
                    "objective": "max min(kill_margin, cone_exit_margin) in metres; >0 == escape",
                    "caveat": "no escape found != safe. Verdicts are FALSIFIED_BY_ADVERSARIAL_REPLAN "
                              "or SURVIVED_ADVERSARIAL_REPLAN_SEARCH only; "
                              "ADVERSARIAL_DYNAMIC_CERTIFIED requires conservative completeness."},
           "containment": containment, "rows": rows}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    n_fals = sum(1 for r in rows if r["verdict"].startswith("FALSIFIED"))
    print("   -> %d/%d FALSIFIED, containment exact %d/%d, monotone %d/%d"
          % (n_fals, len(rows), sum(c["fixed_path_exact"] for c in containment), len(containment),
             sum(c["monotone"] for c in containment), len(containment)))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
