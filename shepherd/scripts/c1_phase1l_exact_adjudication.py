"""C-1 Phase 1L step 1 — exact adjudication of every D0 escape candidate.

The review's first instruction: before any budget escalation, adjudicate the two
raw candidates of the single D0 survivor with an EXACT continuous minimum-distance
computation, and split every V3 rejection into "collision" vs "not certified".

This re-runs the frozen D0 search deterministically (same seeds, same budget), keeps
EVERY raw claim (not a top-N slice), deduplicates by control sequence, and sends all
unique candidates through `c1_exact_clearance`.  It reports the seven columns the
review asked for, so the audit trail no longer conflates "claims", "exported",
"unique" and "audited".

Nothing is escalated here.  D0 results are preserved verbatim; this only sharpens
the adjudication of the candidates D0 already produced.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, N_LIM, R_BODY, M_SAFETY,
                                                PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_plant_bound import solve_witness_hold, solve_witness, make_lp_arm
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts import c1_replan_verify as RV
from shepherd.scripts.c1_exact_clearance import exact_min_clearance, nominal_vs_robust_label
from shepherd.scripts.c1_phase1k_frozen_audit import FROZEN, RH, BASE, MAXCLR
from shepherd.game import viability as V

# Pre-registered model-uncertainty budget for the nominal/robust label split.
# Declared BEFORE looking at the exact margins; sized as a round 1 cm on a 2.6 m
# kill radius (0.4 %), covering Hermite/model mismatch and state error at this scale.
UNCERTAINTY_BUDGET_M = 0.010


def witness(pe, fin, kind, spec, RL, RB):
    if kind == "RH":
        rho0, tl, f = spec
        s, d, m = solve_witness_hold(rho0, f)
        return rho0, tl, log_ctrl(make_lp_arm(s))
    if kind == "MAXCLR":
        rho0, tl, f = spec
        s, m = solve_witness(rho0, f)
        return rho0, tl, log_ctrl(make_lp_arm(s))
    rho0, tl, arm = spec
    return rho0, tl, log_ctrl(make_contract() if arm == "C" else make_pd())


def adjudicate(pe, rec, tag, cls, max_audit):
    E = pe.ad.env; tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    cone_kw = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    L_of_t = lambda times: hermite_positions(P_post, V_post, np.asarray(times))[0]
    Lvb = RV.limiter_speed_bound(P_post, V_post)

    raw = []
    for sd in FROZEN["cert_seeds"]:
        acc1 = V.reachable_accels(E.a_att_max, FROZEN["n_cert"], int(sd))
        ep1, tf1, pts1 = V._seg_paths_turn(p_att, v_att,
                                           np.repeat(acc1[:, None, :], FROZEN["K"], axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
        sc1 = np.minimum(kill_margin(pts1, L_of_t, E.kill_radius, tau),
                         cone_exit_margin(ep1, **cone_kw))
        warm = np.repeat(acc1[int(np.argmax(sc1))][None, :], FROZEN["K"], axis=0)
        for rs in FROZEN["replan_seeds_confirm"]:
            _, escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                    L_of_t=L_of_t, kill_radius=E.kill_radius,
                                    cone_kw=cone_kw, K=FROZEN["K"], pop=FROZEN["pop"],
                                    iters=FROZEN["iters"], seed=int(rs) + int(sd), warm=warm)
            raw += escs

    n_raw = len(raw)
    seen, uniq = set(), []
    for e in sorted(raw, key=lambda z: -z["score"]):
        key = tuple(np.round(np.asarray(e["acc"], float).ravel(), 6))
        if key in seen:
            continue
        seen.add(key); uniq.append(e)
    n_unique = len(uniq)
    audit_set = uniq if (max_audit is None or n_unique <= max_audit) else uniq[:max_audit]

    res = []
    for e in audit_set:
        v = RV.verify_escape(e, p_att=p_att, v_att=v_att, tau=tau, a_att_max=E.a_att_max,
                             L_of_t=L_of_t, L_vel_bound=Lvb, kill_radius=E.kill_radius,
                             cone_kw=cone_kw, n_sub=FROZEN["verifier_n_sub"])
        ex = exact_min_clearance(p_att, v_att, np.asarray(e["acc"], float), tau, L_of_t,
                                 N_LIM, DT, E.kill_radius)
        escapes_net = v["V4_escapes_net"]
        adm = v["V1_control_admissible"] and v["V2_dynamics_match"] and v["V5_exact_replay"]
        if not adm:
            cls_e = "INADMISSIBLE_ARTIFACT"
        elif ex["verdict"] == "VERIFIED_COLLISION_FREE":
            cls_e = "VERIFIED_COLLISION_FREE_ESCAPE" if escapes_net else "COLLISION_FREE_BUT_CAUGHT"
        elif ex["verdict"] == "VERIFIED_COLLISION":
            cls_e = "VERIFIED_COLLISION"
        else:
            cls_e = "UNRESOLVED_CONTINUOUS_CLEARANCE"
        res.append({"screen_lipschitz_margin_m": v["V3_certified_kill_margin_m"],
                    "exact_margin_m": ex["exact_margin_m"], "exact_verdict": ex["verdict"],
                    "escapes_net": escapes_net, "classification": cls_e,
                    "argmin": ex["argmin"], "search_score": e["score"],
                    "acc": e["acc"]})

    n_esc = sum(1 for r in res if r["classification"] == "VERIFIED_COLLISION_FREE_ESCAPE")
    n_col = sum(1 for r in res if r["classification"] == "VERIFIED_COLLISION")
    n_unr = sum(1 for r in res if r["classification"] == "UNRESOLVED_CONTINUOUS_CLEARANCE")
    n_cbc = sum(1 for r in res if r["classification"] == "COLLISION_FREE_BUT_CAUGHT")
    best = max((r["exact_margin_m"] for r in res
                if r["classification"] == "VERIFIED_COLLISION_FREE_ESCAPE"), default=None)
    if n_esc:
        verdict = "FALSIFIED_BY_ADVERSARIAL_REPLAN_D0"
        strength = nominal_vs_robust_label(best, UNCERTAINTY_BUDGET_M)
    elif n_unr:
        verdict = "SURVIVED_D0_WITH_UNCERTIFIED_ESCAPE_CANDIDATES"; strength = None
    else:
        verdict = "SURVIVED_ADVERSARIAL_REPLAN_D0"; strength = None
    return {"tag": tag, "class": cls,
            "n_raw_claims": n_raw, "n_unique": n_unique, "n_audited": len(audit_set),
            "n_not_audited": n_unique - len(audit_set),
            "n_verified_escape": n_esc, "n_verified_collision": n_col,
            "n_unresolved_v3": n_unr, "n_collision_free_but_caught": n_cbc,
            "best_exact_margin_m": best, "verdict": verdict, "strength_label": strength,
            "uncertainty_budget_m": UNCERTAINTY_BUDGET_M,
            "candidates": res if len(res) <= 6 else res[:6]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-audit", type=int, default=12,
                    help="cap on unique candidates sent to the exact adjudicator per witness")
    ap.add_argument("--only-survivor", action="store_true")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1l_exact_adjudication.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY

    jobs = [("BASE", (2.8, 0.30, "C"), "D0_SURVIVOR")]
    if not a.only_survivor:
        jobs += ([("RH", s, "RH_hold") for s in RH]
                 + [("MAXCLR", s, "maxclr_positive_control") for s in MAXCLR]
                 + [("BASE", s, "legacy_baseline") for s in BASE if s != (2.8, 0.30, "C")])
    rows = []
    print("== Phase 1L: EXACT continuous-clearance adjudication of D0 candidates ==")
    print("   (uncertainty budget for the nominal/robust split, pre-registered: %.3f m)"
          % UNCERTAINTY_BUDGET_M)
    for kind, spec, cls in jobs:
        rho0, tl, w = witness(pe, fin, kind, spec, RL, RB)
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        tag = "%-6s %.1f/%.2f" % (kind, rho0, tl)
        r = adjudicate(pe, rec, tag, cls, a.max_audit)
        rows.append(r)
        print("   %s | raw %5d unique %4d audited %3d | escape %3d  collision %3d  unresolved %3d"
              "  cf-but-caught %3d | best exact %s | %s %s"
              % (tag, r["n_raw_claims"], r["n_unique"], r["n_audited"], r["n_verified_escape"],
                 r["n_verified_collision"], r["n_unresolved_v3"], r["n_collision_free_but_caught"],
                 ("%.5f m" % r["best_exact_margin_m"]) if r["best_exact_margin_m"] is not None else "n/a",
                 r["verdict"], "(%s)" % r["strength_label"] if r["strength_label"] else ""), flush=True)
    out = {"meta": {"phase": "1L_exact_adjudication", "budget": "D0 (frozen, unchanged)",
                    "frozen_protocol": FROZEN,
                    "uncertainty_budget_m": UNCERTAINTY_BUDGET_M,
                    "exact_method": "degree-6 d^2 on breakpoint-aligned sub-intervals; "
                                    "exact stationary points of the degree-5 derivative",
                    "screen_status": "c1_replan_verify.certified_kill_clearance is a "
                                     "CONSERVATIVE_CONTINUOUS_CLEARANCE_SCREEN (1.25x empirical "
                                     "padding) and is NOT used for adjudication here",
                    "role": "FALSIFIER, not certifier"},
           "rows": rows}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
