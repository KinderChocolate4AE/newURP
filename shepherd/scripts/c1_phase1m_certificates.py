"""C-1 Phase 1M — the three mandated actions before mode analysis.

  M1  RE-ADJUDICATE the three Phase 1E optimizer-exploit witnesses with the SAME
      continuous minimum-distance adjudicator used for the other twelve, so the
      15-scenario statement rests on one verifier rather than two.

  M2  INTERVAL CERTIFICATE for the two smallest-margin counterexamples
      (BASE 2.8/0.30 C at 1.70 mm, BASE 5.0/1.00 P at 8.30 mm).  A companion-matrix
      eigensolve is a floating-point computation, so those two are re-decided by
      Bernstein convex-hull bounds with de Casteljau bisection and outward rounding
      (c1_interval_certificate) -- no root finding, valid under rounding.

  M3  PRE-REGISTER and FREEZE the escalation protocols, dormant.  D1 is fixed NOW,
      including its restart/population/iteration counts, so that seeing a future
      survivor cannot retro-tune it.  Margin strengthening and mode diversity are
      registered as SEPARATE protocols, not as survivor escalation.

Terminology fixed here (external review):
  * the root-finding adjudicator is NUMERICALLY_RESOLVED_CONTINUOUS_MINIMUM_DISTANCE,
    not "exact"
  * a margin above the 10 mm budget is CLEARANCE_ROBUST_TO_10MM_ADDITIVE_GEOMETRIC_ERROR,
    not "robust under model uncertainty" -- the budget covers additive geometric error
    only, not dynamics/tracking/cone/admissibility channels
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, N_LIM, R_BODY, M_SAFETY,
                                                PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0, knots_to_seq
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, seq_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_replan_falsifier import replan_search, kill_margin, cone_exit_margin
from shepherd.scripts import c1_replan_verify as RV
from shepherd.scripts.c1_exact_clearance import exact_min_clearance
from shepherd.scripts.c1_interval_certificate import certify_clearance
from shepherd.scripts.c1_phase1k_frozen_audit import FROZEN, E15_EXPLOIT
from shepherd.game import viability as V

BUDGET_M = 0.010          # additive GEOMETRIC error budget only

# ---------------------------------------------------------------- M3 frozen registry
ESCALATION_REGISTRY = {
    "D0": {"status": "EXECUTED_AND_FROZEN", "K": 4, "pop": 192, "iters": 14, "restarts": 2,
           "cert_seeds": FROZEN["cert_seeds"], "replan_seeds": FROZEN["replan_seeds_confirm"],
           "n_cert": FROZEN["n_cert"], "note": "results preserved verbatim; never overwritten"},
    "D1": {"status": "PRE_REGISTERED_DORMANT",
           "trigger": "auto-fires ONLY on a controller-scenario with ZERO verified escapes at D0",
           "invariants": ["controller artifact and all settings sealed BEFORE D0",
                          "no controller re-optimisation inside D1",
                          "verifier, objective and attacker dynamics unchanged from D0",
                          "D0 seeds/artifacts not reused as search state (reference column only)"],
           "K": 4, "pop": 192, "iters": 14,
           "restarts": 16, "replan_seeds": [64_000_201 + i for i in range(16)],
           "cert_seeds": FROZEN["cert_seeds"], "n_cert": FROZEN["n_cert"],
           "rationale": "restart diversity prioritised over population; counts fixed now so a "
                        "future survivor cannot retro-tune the stopping point",
           "outputs": ["SURVIVED_D0_AND_D1", "FALSIFIED_BY_ADVERSARIAL_REPLAN_D1"]},
    "D2": {"status": "PRE_REGISTERED_DORMANT",
           "trigger": "only on a D1 survivor",
           "note": "ATTACKER CLASS CHANGE, not a budget increase -- separate protocol version",
           "K": [6, 8], "containment_test_required": "K=4 trajectories must be exactly representable",
           "additions": ["alternative control basis", "direct collocation", "optimizer diversity"]},
    "D3": {"status": "PRE_REGISTERED_DORMANT", "trigger": "only on a D2 survivor",
           "additions": ["CMA-ES", "gradient refinement", "verified-artifact warm-start perturbation"]},
    "D0-MARGIN-STRENGTHENING": {
        "status": "PRE_REGISTERED_DORMANT", "kind": "NOT survivor escalation",
        "purpose": "find larger-margin counterexamples for already-falsified scenarios",
        "note": "cannot change any FALSIFIED verdict; only raises the strength label"},
    "D0-MODE-DIVERSITY": {
        "status": "PRE_REGISTERED_DORMANT", "kind": "NOT survivor escalation",
        "purpose": "enumerate independent escape basins for controller design",
        "note": "outputs are FIXED_CONDITION_CONTROLLER_DESIGN_DIAGNOSTIC; frequency claims "
                "forbidden (single reset, optimizer sampling is not an attacker distribution)"},
}


def exploit_rollout(pe, fin, rho0, tl, wname, sbase, RL, RB):
    from shepherd.scripts.c1_controller_gap import cem_O, ws1_best_simple, ws2_band_edge
    E = pe.ad.env
    spawn = make_spawn(rho0, tl * V_CLOSE)
    n_dep = int(round(E.tau_deploy / DT)); ctrl_len = int(round(tl / DT)) + n_dep + 2
    warm = (ws1_best_simple(pe, spawn, fin, RL, RB, 6) if wname == "WS1" else ws2_band_edge(spawn, 6))
    seed = 401_000_000 + int(rho0 * 100) * 1000 + int(tl * 100) + sbase
    _, kn = cem_O(pe, spawn, fin, RL, RB, warm, seed, ctrl_len, 20, 12, 6)
    seq = knots_to_seq(kn, ctrl_len)
    w = seq_ctrl(seq); w.log = list(seq)
    return rollout_unified(pe, spawn, w, fin, r_lane=RL, r_body=RB), seed


def adjudicate(pe, rec, max_audit=12):
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
            _, escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max, L_of_t=L_of_t,
                                    kill_radius=E.kill_radius, cone_kw=cone_kw, K=FROZEN["K"],
                                    pop=FROZEN["pop"], iters=FROZEN["iters"],
                                    seed=int(rs) + int(sd), warm=warm)
            raw += escs
    seen, uniq = set(), []
    for e in sorted(raw, key=lambda z: -z["score"]):
        key = tuple(np.round(np.asarray(e["acc"], float).ravel(), 6))
        if key not in seen:
            seen.add(key); uniq.append(e)
    audit = uniq[:max_audit]
    res = []
    for e in audit:
        v = RV.verify_escape(e, p_att=p_att, v_att=v_att, tau=tau, a_att_max=E.a_att_max,
                             L_of_t=L_of_t, L_vel_bound=Lvb, kill_radius=E.kill_radius,
                             cone_kw=cone_kw, n_sub=FROZEN["verifier_n_sub"])
        nr = exact_min_clearance(p_att, v_att, np.asarray(e["acc"], float), tau, L_of_t,
                                 N_LIM, DT, E.kill_radius)
        ok = (v["V1_control_admissible"] and v["V2_dynamics_match"] and v["V5_exact_replay"]
              and nr["verdict"] == "VERIFIED_COLLISION_FREE" and v["V4_escapes_net"])
        res.append({"numerically_resolved_margin_m": nr["exact_margin_m"],
                    "nr_verdict": nr["verdict"], "escapes_net": v["V4_escapes_net"],
                    "is_escape": bool(ok), "acc": e["acc"]})
    esc = [r for r in res if r["is_escape"]]
    best = max((r["numerically_resolved_margin_m"] for r in esc), default=None)
    return {"n_raw_claims": len(raw), "n_unique": len(uniq), "n_audited": len(audit),
            "n_verified_escape": len(esc),
            "n_verified_collision": sum(1 for r in res if r["nr_verdict"] == "VERIFIED_COLLISION"),
            "n_unresolved": sum(1 for r in res if r["nr_verdict"] == "UNRESOLVED_CONTINUOUS_CLEARANCE"),
            "best_numerically_resolved_margin_m": best,
            "verdict": "FALSIFIED_BY_ADVERSARIAL_REPLAN_D0" if esc else "SURVIVED_ADVERSARIAL_REPLAN_D0",
            "strength_label": (None if best is None else
                               ("CLEARANCE_ROBUST_TO_10MM_ADDITIVE_GEOMETRIC_ERROR" if best > BUDGET_M
                                else "FALSIFIED_BY_ADVERSARIAL_REPLAN_IN_NOMINAL_MODEL")),
            "top_escape_acc": (esc[0]["acc"] if esc else None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior", default="results/c1_corridor/c1_phase1l_exact_adjudication.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1m_certificates.json")
    a = ap.parse_args()
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY

    # ---- M1 : 1E exploit witnesses through the SAME adjudicator
    print("== M1: Phase 1E exploit witnesses re-adjudicated with the 1L verifier ==")
    m1 = []
    for rho0, tl, wname, sbase in E15_EXPLOIT:
        rec, seed = exploit_rollout(pe, fin, rho0, tl, wname, sbase, RL, RB)
        r = adjudicate(pe, rec)
        r.update({"tag": "EXPLOIT %.1f/%.2f %s" % (rho0, tl, wname), "cem_seed": seed,
                  "tier": rec["tier"]})
        m1.append(r)
        print("   %s | raw %5d unique %5d audited %2d | escape %2d collision %d unresolved %d "
              "| margin %s | %s (%s)"
              % (r["tag"], r["n_raw_claims"], r["n_unique"], r["n_audited"], r["n_verified_escape"],
                 r["n_verified_collision"], r["n_unresolved"],
                 ("%.5f m" % r["best_numerically_resolved_margin_m"])
                 if r["best_numerically_resolved_margin_m"] is not None else "n/a",
                 r["verdict"], r["strength_label"]), flush=True)

    # ---- M2 : interval certificates for the two smallest margins
    print("== M2: Bernstein interval certificates for the two smallest margins ==")
    prior = json.loads(pathlib.Path(a.prior).read_text())
    targets = sorted([r for r in prior["rows"] if r["best_exact_margin_m"] is not None],
                     key=lambda r: r["best_exact_margin_m"])[:2]
    m2 = []
    for row in targets:
        spec = row["tag"].split()[1]
        rho0, tl = [float(x) for x in spec.split("/")]
        arm = "C" if abs(rho0 - 2.8) < 1e-9 else "P"
        from shepherd.scripts.c1_phase1d import log_ctrl
        w = log_ctrl(make_contract() if arm == "C" else make_pd())
        rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)
        t = rec["_t_ref"]; o = np.asarray(rec["_obs"][t], float)
        P_post = np.asarray(rec["_lim"][t:], float); V_post = np.asarray(rec["_vel"][t:], float)
        L_of_t = lambda times: hermite_positions(P_post, V_post, np.asarray(times))[0]
        cand = [c for c in row["candidates"] if c["classification"] == "VERIFIED_COLLISION_FREE_ESCAPE"]
        acc = np.asarray(cand[0]["acc"], float)
        cert = certify_clearance(o[ATT_P0:ATT_P0 + 3], o[ATT_P0 + 3:ATT_P0 + 6], acc,
                                 float(E.tau_deploy), L_of_t, N_LIM, DT, E.kill_radius)
        rec_row = {"tag": row["tag"].strip(), "numerically_resolved_margin_m": row["best_exact_margin_m"],
                   **cert}
        m2.append(rec_row)
        print("   %-18s NR margin %.5f m -> %s | lower-bound d %s"
              % (rec_row["tag"], rec_row["numerically_resolved_margin_m"], cert["certificate"],
                 ("%.6f m" % cert["implied_min_distance_lower_bound_m"])
                 if "implied_min_distance_lower_bound_m" in cert else "n/a"), flush=True)

    out = {"meta": {"phase": "1M_certificates_and_registry",
                    "adjudicator": "NUMERICALLY_RESOLVED_CONTINUOUS_MINIMUM_DISTANCE "
                                   "(companion-matrix roots; NOT exact root isolation)",
                    "certificate": "Bernstein convex hull + de Casteljau bisection, outward-rounded",
                    "budget_m": BUDGET_M,
                    "budget_scope": "ADDITIVE GEOMETRIC error on the relative distance only; "
                                    "does NOT cover dynamics/tracking/Hermite-mismatch/cone/"
                                    "admissibility uncertainty channels",
                    "role": "FALSIFIER, not certifier"},
           "M1_exploit_readjudication": m1, "M2_interval_certificates": m2,
           "M3_escalation_registry": ESCALATION_REGISTRY}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("== M3: escalation registry frozen (D1/D2/D3 + MARGIN-STRENGTHENING + MODE-DIVERSITY), dormant ==")
    print("wrote", a.out, flush=True)


if __name__ == "__main__":
    main()
