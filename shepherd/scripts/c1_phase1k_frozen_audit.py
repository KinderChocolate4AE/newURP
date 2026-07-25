"""C-1 Phase 1K — FROZEN adversarial-replan audit protocol (step D of the ratified order).

Step order (external review, 2026-07-25):
    A implement falsifier            -> Phase 1J
    B containment / monotonicity / time-alignment  -> 1J + THIS FILE (V3 continuous)
    C re-audit RH / baseline / EXPLOIT witnesses   -> THIS FILE (adds the 1E exploit)
    D freeze the protocol and the replan budget    -> THIS FILE (the block below)
    E wide controller class search                 -> NOT STARTED (gated on D)

FROZEN PROTOCOL — changing any of these invalidates comparability and must be
recorded as a protocol revision, not a rerun.

    verdict rule       binary existence test.  An artifact that passes the
                       INDEPENDENT verifier (c1_replan_verify.V1-V5) is an escape;
                       one escape => FALSIFIED_BY_ADVERSARIAL_REPLAN.  Otherwise
                       SURVIVED_ADVERSARIAL_REPLAN_SEARCH (never "certified").
                       v_soft_replan is REPORTED but is NOT a verdict input: it is
                       (k0+k_new)/(n0+n_new) and therefore a function of the
                       arbitrary ratio (search budget)/(n_cert) -- Phase 1J measured
                       it flipping verdicts in BOTH directions across two budgets.
    replan budget      K = 4 segments, pop = 192, iters = 14, restarts = 2
    cert seeds         (91000101, 91000102, 91000103)      [sealed in Phase 1I]
    replan seeds       search (52000001, 52000002) | confirm (63000101, 63000102)
    n_cert             20000 per cert seed
    verifier substeps  n_sub = 64 per attacker segment, with a Lipschitz-certified
                       inter-sample bound (no tunneling can be missed)
    reset              1100 (single reset -- distribution-level claims not allowed)

Reported estimator split (external review, across-scramble limitation):
    (i)  stochastic attacker distribution estimate   -- Block-1 samples only
    (ii) deterministic adversarial witness bank      -- boundary/dogleg blocks,
                                                        as an EXISTENCE test, not
                                                        as probability mass
    (iii) union-based falsification result           -- the verdict
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, R_BODY, M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0, knots_to_seq
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl, seq_ctrl
from shepherd.scripts.c1_phase1e import judge_models, hermite_positions, _mask_moving, DT
from shepherd.scripts.c1_plant_bound import solve_witness_hold, solve_witness, make_lp_arm
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts import c1_replan_verify as RV
from shepherd.game import viability as V

FROZEN = {"verdict_rule": "binary existence test on INDEPENDENTLY verified escapes",
          "K": 4, "pop": 192, "iters": 14, "restarts": 2, "n_cert": 20000,
          "cert_seeds": [91000101, 91000102, 91000103],
          "replan_seeds_search": [52000001, 52000002],
          "replan_seeds_confirm": [63000101, 63000102],
          "verifier_n_sub": 64, "reset": 1100,
          "v_soft_replan_is_verdict_input": False}

RH = [(2.8, 0.15, 2), (3.2, 0.25, 5), (4.0, 0.40, 7), (5.0, 0.55, 10)]
BASE = [(2.8, 0.30, "C"), (3.2, 0.50, "C"), (3.2, 0.70, "P"),
        (4.0, 0.70, "C"), (4.0, 0.70, "P"), (5.0, 1.00, "P")]
MAXCLR = [(5.0, 0.55, 10), (4.0, 0.40, 7)]
# Phase 1E optimizer-exploit witnesses, reproduced with the Phase 1C CEM seeds
E15_EXPLOIT = [(3.2, 0.35, "WS1", 700), (3.2, 0.40, "WS1", 700), (4.0, 0.70, "WS2", 701)]


def witness_rollout(pe, fin, kind, spec, RL, RB):
    if kind == "RH":
        rho0, tl, f = spec
        s, d, m = solve_witness_hold(rho0, f)
        return rho0, tl, log_ctrl(make_lp_arm(s)), {"lp_d": round(d, 4)}
    if kind == "MAXCLR":
        rho0, tl, f = spec
        s, m = solve_witness(rho0, f)
        return rho0, tl, log_ctrl(make_lp_arm(s)), {}
    if kind == "BASE":
        rho0, tl, arm = spec
        return rho0, tl, log_ctrl(make_contract() if arm == "C" else make_pd()), {"arm": arm}
    if kind == "EXPLOIT":
        rho0, tl, wname, sbase = spec
        from shepherd.scripts.c1_controller_gap import cem_O, ws1_best_simple, ws2_band_edge
        E = pe.ad.env
        spawn = make_spawn(rho0, tl * V_CLOSE)
        n_dep = int(round(E.tau_deploy / DT)); ctrl_len = int(round(tl / DT)) + n_dep + 2
        warm = (ws1_best_simple(pe, spawn, fin, RL, RB, 6) if wname == "WS1"
                else ws2_band_edge(spawn, 6))
        seed = 401_000_000 + int(rho0 * 100) * 1000 + int(tl * 100) + sbase
        _, kn = cem_O(pe, spawn, fin, RL, RB, warm, seed, ctrl_len, 20, 12, 6)
        seq = knots_to_seq(kn, ctrl_len)
        w = seq_ctrl(seq); w.log = list(seq)
        return rho0, tl, w, {"cem_seed": seed, "note": "1E exploit, deterministic reproduction"}
    raise ValueError(kind)


def audit_one(pe, rec, tag, cls, extra):
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    cone_kw = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    L_of_t = lambda times: hermite_positions(P_post, V_post, np.asarray(times))[0]
    Lvb = RV.limiter_speed_bound(P_post, V_post)

    per_seed_fixed, verified, raw_escapes = [], [], 0
    det_exists = False       # (ii) deterministic bank existence test
    for sd in FROZEN["cert_seeds"]:
        u = V.build_reachable_union(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                    n=FROZEN["n_cert"],
                                    n_segments=max(int(E.n_segments), 2), seed=int(sd), **kw)
        masks = [_mask_moving(pb, L_of_t, E.kill_radius, tau) for pb in u.path_blocks]
        feas = np.concatenate(masks, axis=0) & u.turn_feasible
        caught = np.asarray(u.caught, bool)
        k0, n0 = int((caught & feas).sum()), int(feas.sum())
        per_seed_fixed.append(k0 / n0 if n0 else float("nan"))
        bs = list(u.block_sizes); e0 = bs[0]
        det_exists |= bool((feas[e0:] & ~caught[e0:]).any())     # (ii)

        acc1 = V.reachable_accels(E.a_att_max, FROZEN["n_cert"], int(sd))
        ep1, tf1, pts1 = V._seg_paths_turn(p_att, v_att,
                                           np.repeat(acc1[:, None, :], FROZEN["K"], axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
        sc1 = np.minimum(kill_margin(pts1, L_of_t, E.kill_radius, tau),
                         cone_exit_margin(ep1, **cone_kw))
        warm = np.repeat(acc1[int(np.argmax(sc1))][None, :], FROZEN["K"], axis=0)

        for rs in FROZEN["replan_seeds_confirm"]:
            best, escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                       L_of_t=L_of_t, kill_radius=E.kill_radius,
                                       cone_kw=cone_kw, K=FROZEN["K"], pop=FROZEN["pop"],
                                       iters=FROZEN["iters"], seed=int(rs) + int(sd), warm=warm)
            raw_escapes += len(escs)
            for e in sorted(escs, key=lambda z: -z["score"])[:5]:     # verify the top few
                v = RV.verify_escape(e, p_att=p_att, v_att=v_att, tau=tau,
                                     a_att_max=E.a_att_max, L_of_t=L_of_t,
                                     L_vel_bound=Lvb, kill_radius=E.kill_radius,
                                     cone_kw=cone_kw, n_sub=FROZEN["verifier_n_sub"])
                v.update({"cert_seed": int(sd), "replan_seed": int(rs),
                          "search_score": e["score"], "acc": e["acc"]})
                verified.append(v)

    conf = [v for v in verified if v["is_escape"]]
    row = {"tag": tag, "class": cls,
           "v_soft_fixed_path": float(np.mean(per_seed_fixed)),
           "raw_search_escapes": raw_escapes,
           "independently_verified_escapes": len(conf),
           "search_claimed_but_verifier_rejected": len(verified) - len(conf),
           "best_verified_certified_margin_m": (max(v["V3_certified_kill_margin_m"] for v in conf)
                                                if conf else None),
           "deterministic_bank_escape_exists": det_exists,
           "verifier_checks_all_pass": bool(all(v["V1_control_admissible"] and v["V2_dynamics_match"]
                                                and v["V5_exact_replay"] for v in verified)) if verified else None,
           "verdict": ("FALSIFIED_BY_ADVERSARIAL_REPLAN" if conf
                       else "SURVIVED_ADVERSARIAL_REPLAN_SEARCH"),
           "verified_sample": conf[:2]}
    row.update(extra)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1k_frozen_audit.json")
    ap.add_argument("--skip-exploit", action="store_true")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    rows = []
    print("== Phase 1K: FROZEN protocol audit (binary verdict, independent verifier) ==")
    jobs = ([("RH", s, "RH_hold") for s in RH]
            + [("MAXCLR", s, "maxclr_positive_control") for s in MAXCLR]
            + ([] if a.skip_exploit else [("EXPLOIT", s, "e15_optimizer_exploit") for s in E15_EXPLOIT])
            + [("BASE", s, "legacy_baseline") for s in BASE])
    for kind, spec, cls in jobs:
        rho0, tl, w, extra = witness_rollout(pe, fin, kind, spec, RL, RB)
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        tag = "%-7s %.1f/%.2f" % (kind, rho0, tl)
        r = audit_one(pe, rec, tag, cls, dict(extra, tier=rec["tier"]))
        rows.append(r)
        print("   %s tier %d | fixed %.4f | escapes raw %5d -> verified %3d (rejected %d) | "
              "cert-margin %s | det-bank escape %s | %s"
              % (tag, rec["tier"], r["v_soft_fixed_path"], r["raw_search_escapes"],
                 r["independently_verified_escapes"], r["search_claimed_but_verifier_rejected"],
                 ("%.4f m" % r["best_verified_certified_margin_m"]) if r["best_verified_certified_margin_m"] is not None else "n/a",
                 r["deterministic_bank_escape_exists"], r["verdict"]), flush=True)
    nf = sum(1 for r in rows if r["verdict"].startswith("FALSIFIED"))
    out = {"meta": {"phase": "1K_frozen_audit", "frozen_protocol": FROZEN,
                    "estimator_split": {
                        "i_stochastic": "Block-1 sample estimate (reported as v_soft_fixed_path)",
                        "ii_deterministic_bank": "boundary/dogleg blocks as an EXISTENCE test "
                                                 "(deterministic_bank_escape_exists), not probability mass",
                        "iii_union_falsification": "the binary verdict"},
                    "role": "FALSIFIER, not certifier"},
           "rows": rows, "summary": {"falsified": nf, "total": len(rows)}}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("   -> %d/%d FALSIFIED by independently verified escapes" % (nf, len(rows)))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
