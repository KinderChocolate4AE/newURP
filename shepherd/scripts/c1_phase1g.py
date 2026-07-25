"""C-1 Phase 1G — Arm L (plant witness) under the E1.5 authoritative judge.

Phase 1F produced T*_plant by playing an LP plant-witness through the closed-loop
probe.  Those numbers rest on the STATIC snapshot capture judge, which Phase 1E
showed to be exploitable.  Before T*_plant can be used as a baseline it has to
survive the same audit that falsified the Phase 1C optimizer candidates.

This script reuses c1_phase1e's machinery UNCHANGED — judge_models (static /
cv_swept / actual on one shared reachable union, n_cert x 3 scrambled seeds,
Wilson one-sided LCB), clearance_dense (point-to-segment, dense Hermite substeps),
displacement_sup (measured sup-displacement screen), make_labels — and drives it
with:

  * ARM_L witnesses at every T*_plant cell, plus the nominal miss cell and one
    robustness point;
  * the SIX legacy baseline witnesses re-run through the identical pipeline as a
    reproduction control (they scored actual v_soft 0.988-0.995, LCB 0.969-0.977
    in Phase 1E; anything else means the pipeline drifted, not that Arm L failed).

Arm L is also parity-checked: response_rollout (Phase 1F path) vs rollout_unified
(the E0-verified path) must agree on PARITY_FIELDS, so the audit judges the same
trajectory Phase 1F claimed.

Caveat carried from 1E, unchanged: `actual` remasks a FIXED attacker path bank
against the realised limiter motion.  Adversarial replan is still not implemented,
so a pass here is TIER4_DYNAMIC_REMASK, not a full dynamic certificate.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
    response_rollout, THETA, N_LIM, R_BODY, M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl, PARITY_FIELDS
from shepherd.scripts.c1_phase1e import (judge_models, clearance_dense, displacement_sup,
    make_labels, _hash, _git, CERT_SEEDS, EPS_DISP, SUBSTEPS, N_CERT)
from shepherd.scripts.c1_plant_bound import solve_witness, solve_witness_hold, make_lp_arm

# (rho0, T, fire-step target, why)
ARM_L_WITNESSES = [
    # T*_dyn winners from c1_phase1g_search (hold LP, all fire steps tried)
    (2.8, 0.15, 2, "T*_dyn"),
    (3.2, 0.25, 5, "T*_dyn"),
    (4.0, 0.40, 7, "T*_dyn"),
    (5.0, 0.55, 10, "T*_dyn  <- headline: simple arms need 0.75"),
    # cells that the static judge accepted and the dynamic judge must reject
    (3.2, 0.20, 4, "1F T*_plant, dynamically falsified (LP d* = 0.05)"),
    (4.0, 0.35, 7, "1F T*_plant, dynamically falsified (LP d* = 0.05)"),
    (5.0, 0.60, 11, "robustness point above T*_dyn"),
    (5.0, 0.50, 9, "nominal cell (hold LP INFEASIBLE; maxclr LP m* = -0.0125 m)"),
]
# Phase 1E control set — must reproduce LEGACY_BASELINE_WITNESSES_DYNAMIC_REMASK_CONSISTENT
BASE_WITNESSES = [(2.8, 0.30, "C"), (3.2, 0.50, "C"), (3.2, 0.70, "P"),
                  (4.0, 0.70, "C"), (4.0, 0.70, "P"), (5.0, 1.00, "P")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-cert", type=int, default=N_CERT)
    ap.add_argument("--variant", default="hold", choices=("hold", "maxclr"),
                    help="hold = displacement-constrained LP (Phase 1G correction); "
                         "maxclr = the original 1F max-min-clearance LP (falsified)")
    ap.add_argument("--skip-baseline", action="store_true")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1g_dynamic_judge.json")
    ap.add_argument("--artifacts", default="results/c1_corridor/witness_artifacts_1g")
    a = ap.parse_args()

    env_cfg, m3, _theta = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"]); fin = make_finisher_fn(THETA)
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    art_dir = pathlib.Path(a.artifacts); art_dir.mkdir(parents=True, exist_ok=True)
    commit = _git("git rev-parse --short HEAD")
    cfg_hash = hashlib.sha256(pathlib.Path("configs/m3a_a3e_p1.yaml").read_bytes()).hexdigest()[:16]
    rows = []

    def record(tag, rho0, tl, arm, rec, actions, spawn, extra=None):
        jm = judge_models(pe, rec, n_cert=a.n_cert)
        clr = clearance_dense(pe, rec, r_lane=RL, r_body=RB)
        disp = displacement_sup(pe, rec)
        labs = make_labels(rec, jm, clr, disp)
        art = {"tag": tag, "rho0": rho0, "T": tl, "arm": arm, "commit": commit,
               "config_sha": cfg_hash, "reset_seed": 1100, "cert_seeds": list(CERT_SEEDS),
               "n_cert": a.n_cert,
               "spawn": {k: np.asarray(v).tolist() for k, v in spawn.items()},
               "actions": np.asarray(actions, float).tolist(),
               "traj_sha": _hash(rec["_lim"]), "action_sha": _hash(actions),
               "judges": jm, "clearance_dense": clr, "displacement": disp, "labels": labs}
        if extra: art.update(extra)
        (art_dir / ("%s_%s_%.1f_%.2f.json" % (tag, arm.replace("-", ""), rho0, tl))).write_text(
            json.dumps(art, indent=1, default=float))
        rows.append({"src": tag, "rho0": rho0, "T": tl, "arm": arm, "tier": rec["tier"],
                     "legacy_clr": rec["clearance_margin"], "dense_clr": clr["m_clear_dense"],
                     "sup_disp": disp["sup_disp"], "disp_limit": disp["limit"],
                     "v_fire_max": disp["v_fire_max"],
                     "v_soft_static": jm["static"]["v_soft"], "v_soft_cv": jm["cv_swept"]["v_soft"],
                     "v_soft_actual": jm["actual"]["v_soft"],
                     "lcb_actual": jm["actual"]["v_soft_lcb"],
                     "n_feas_static": jm["static"]["n_feasible"],
                     "n_feas_actual": jm["actual"]["n_feasible"],
                     "certifies_actual": jm["actual"]["certifies"], "labels": labs})
        print("  %-5s %.1f/%.2f %-6s tier %d | v_soft st %.3f cv %.3f act %.3f (LCB %.3f, n_feas %d)"
              " | disp %.3f/%.2f | clr %s -> %s | %s" % (
              tag, rho0, tl, arm, rec["tier"],
              jm["static"]["v_soft"] if jm["static"]["v_soft"] is not None else -1,
              jm["cv_swept"]["v_soft"] if jm["cv_swept"]["v_soft"] is not None else -1,
              jm["actual"]["v_soft"] if jm["actual"]["v_soft"] is not None else -1,
              jm["actual"]["v_soft_lcb"], jm["actual"]["n_feasible"],
              disp["sup_disp"], disp["limit"],
              ("%+.3f" % rec["clearance_margin"]) if rec["clearance_margin"] is not None else "n/a",
              ("%+.3f" % clr["m_clear_dense"]) if clr["m_clear_dense"] is not None else "n/a",
              ",".join(labs)), flush=True)

    print("== Phase 1G: Arm L (plant witness) under the E1.5 authoritative judge ==", flush=True)
    parity = []
    for rho0, tl, f, why in ARM_L_WITNESSES:
        if a.variant == "hold":
            seq, d_star, m = solve_witness_hold(rho0, f)
        else:
            seq, m = solve_witness(rho0, f); d_star = None
        if seq is None:
            print("  rho0=%.1f T=%.2f f=%2d : LP INFEASIBLE (%s)" % (rho0, tl, f, a.variant))
            rows.append({"src": "ARM_L", "rho0": rho0, "T": tl, "arm": "L(f=%d)" % f,
                         "variant": a.variant, "lp": "INFEASIBLE"})
            continue
        spawn = make_spawn(rho0, tl * V_CLOSE)
        # parity: Phase 1F path vs the E0-verified unified path, same controller
        rec_1f = response_rollout(pe, spawn, make_lp_arm(seq), fin, r_lane=RL, r_body=RB)
        w = log_ctrl(make_lp_arm(seq))
        rec = rollout_unified(pe, spawn, w, fin, r_lane=RL, r_body=RB)
        mism = [k for k in PARITY_FIELDS
                if k != "max_angular_gap_deg" and not (
                    rec_1f[k] == rec[k] or
                    (isinstance(rec_1f[k], float) and isinstance(rec[k], float)
                     and abs(rec_1f[k] - rec[k]) < 1e-12))]
        parity.append({"rho0": rho0, "T": tl, "f": f, "mismatch": mism})
        record("ARM_L", rho0, tl, "L%s(f=%d)" % (a.variant[0].upper(), f), rec, np.asarray(w.log, float), spawn,
               extra={"lp_variant": a.variant, "lp_min_clearance": round(m, 4),
                      "lp_max_deviation": (round(d_star, 4) if d_star is not None else None),
                      "f_target": f, "why": why,
                      "a_seq_lp": [round(float(x), 3) for x in seq],
                      "path_parity_mismatch": mism})

    if not a.skip_baseline:
        print("== control: Phase 1E legacy baseline witnesses, identical pipeline ==", flush=True)
        for rho0, tl, arm in BASE_WITNESSES:
            spawn = make_spawn(rho0, tl * V_CLOSE)
            w = log_ctrl(make_contract() if arm == "C" else make_pd())
            rec = rollout_unified(pe, spawn, w, fin, r_lane=RL, r_body=RB)
            record("1B", rho0, tl, arm, rec, np.asarray(w.log, float), spawn)

    out = {"meta": {"phase": "1G_arm_L_dynamic_judge", "lp_variant": a.variant, "commit": commit, "config_sha": cfg_hash,
                    "n_cert": a.n_cert, "cert_seeds": list(CERT_SEEDS), "theta": pe.theta,
                    "eps_disp": EPS_DISP, "substeps": SUBSTEPS,
                    "models": "static | cv_swept | actual (fixed-path REMASK; no adversarial replan)",
                    "caveat": "a pass is TIER4_DYNAMIC_REMASK, not a full dynamic certificate; "
                              "the attacker sample bank is not replanned against moving limiters"},
           "path_parity": parity, "rows": rows}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, default=float))
    print("wrote", a.out, "and", str(art_dir), flush=True)


if __name__ == "__main__":
    main()
