"""A-3e P1' SEALED HOLDOUT PILOT judgment (docs/21 v0.3.2 FROZEN;
docs/09 (kkk)/(mmm)/(ooo)). SERVER script (loads the 3 best ckpts). SINGLE
CONSUMPTION: policy, zero, and the v0.3.2 DIAGNOSTIC arms (brake, lam20)
all run together on the same episodes in this one invocation; the
consumption marker is written at the end and any later load is refused
(stop rule 8 -- no ckpt reselection, no fine-tune, no re-evaluation).

Verdict (P1' PASS, docs/19 v0.3 SS7 P1 rule -- UNCHANGED by v0.3.2): per
training seed s, Delta^_s = mean_e[ arrival(pi_s, e) - arrival(zero, e) ]
over the SEALED d1 episodes (120, paired). PASS <=> (>= 2 of 3 seeds with
Delta^ > 0.10) AND (all seeds Delta^ >= 0). Pooled numbers + per-seed
exact McNemar are DIAGNOSTIC ONLY. d0 episodes: policy captured_rate
recorded (diagnostic). DIAG_ARMS measure the RL-necessity bottleneck
(docs/20 SS6): they NEVER enter the verdict -- they let the readout
distinguish "beats zero" from "beats a simple controller".
This is holdout *pilot* evidence -- never population-confirmatory.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml

from shepherd.train import a3e as A

DELTA_GATE = A.DELTA_GATE                       # 0.10
DIAG_ARMS = ("brake", "lam20")                  # v0.3.2: recorded, non-verdict


def mcnemar_exact_onesided(b: int, c: int) -> float:
    """P(X >= b) for X ~ Binom(b + c, 0.5) -- seed-level AUX diagnostic."""
    n = b + c
    if n == 0:
        return 1.0
    from math import comb
    return float(sum(comb(n, i) for i in range(b, n + 1)) / 2.0 ** n)


def p1_pass_rule(deltas) -> dict:
    """Pure frozen rule: >=2/3 seeds > 0.10 AND all >= 0."""
    ds = [float(d) for d in deltas]
    n_hi = sum(1 for d in ds if d > DELTA_GATE)
    all_nonneg = all(d >= 0.0 for d in ds)
    return {"deltas": ds, "n_above_gate": n_hi,
            "all_nonneg": bool(all_nonneg),
            "PASS": bool(n_hi >= 2 and all_nonneg)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--sealed", default="results/a3e_bundle_sealed_v2d1.json")
    ap.add_argument("--ckpt-root", default="results/m3a_a3e_p1")
    ap.add_argument("--out", default="results/a3e_sealed_verdict.json")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    from shepherd.scripts.a3d_calibration import _lim_fn      # +torch stub
    from shepherd.scripts.a3e_bundle_gen import (load_bundle,
                                                 mark_sealed_consumed)
    from shepherd.scripts.eval_heldout_m3 import learned_fns
    from shepherd.scripts.train_m3a import m3_eval_bundle
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    from shepherd.train.phi_potential import teacher_fire
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    sealed = load_bundle(a.sealed, sealed_judgment=True)      # guarded
    d0 = sealed["stages"]["d0"]["episodes"]
    d1 = sealed["stages"]["d1"]["episodes"]

    def fin_teacher(obs, flags):
        return np.array([0, 0, 0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    def bundle_eval(lim_fn, fin_fn, eps):
        ev = m3_eval_bundle(env_cfg, m3, lim_fn, fin_fn, len(eps),
                            int(eps[0]["reset_seed"]), stage=None,
                            spawn_fn=lambda i, _e=eps: dict(_e[i]["spawn"]),
                            per_episode=True)
        return ev["per_episode"], ev

    lim_scale = np.full(3, 30.0, np.float32)
    axis_scale = np.ones(3, np.float32)
    # zero arm ONCE (shared same-episode baseline for every seed)
    zero_rows, _ = bundle_eval(_lim_fn("zero", {}), fin_teacher, d1)
    zero_arr = [int(r["arrival_capture"]) for r in zero_rows]
    # v0.3.2 diagnostic arms (policy-independent; NEVER in the verdict)
    from shepherd.train import pfc as pfc_mod
    diag = {}
    for arm in DIAG_ARMS:
        fn = (_lim_fn("brake", {}) if arm == "brake"
              else pfc_mod.make_lambda_brake_fn(float(arm[3:])))
        rows, _ = bundle_eval(fn, fin_teacher, d1)
        diag[arm] = {"arrival": float(np.mean(
            [r["arrival_capture"] for r in rows])),
            "per_episode": [int(r["arrival_capture"]) for r in rows]}
        print(f"diag {arm}: arrival={diag[arm]['arrival']:.3f}", flush=True)
    per_seed = {}
    for s in (0, 1, 2):
        lf, ff, meta = learned_fns(pathlib.Path(a.ckpt_root) / f"seed{s}",
                                   "best", a.device)
        lim = (lambda o, f, _lf=lf: _lf(o, f, lim_scale))
        fin = (lambda o, f, _ff=ff: _ff(o, f, axis_scale))
        rows, _ = bundle_eval(lim, fin, d1)             # policy fire (J1)
        pol = [int(r["arrival_capture"]) for r in rows]
        diffs = [p - z for p, z in zip(pol, zero_arr)]
        b = sum(1 for d in diffs if d > 0)
        c = sum(1 for d in diffs if d < 0)
        d0_rows, d0_ev = bundle_eval(lim, fin, d0)
        per_seed[s] = {"ckpt": meta,
                       "delta_hat": float(np.mean(diffs)),
                       "policy_arrival": float(np.mean(pol)),
                       "zero_arrival": float(np.mean(zero_arr)),
                       "policy_minus_brake": (float(np.mean(pol))
                                              - diag["brake"]["arrival"]),
                       "policy_minus_lam20": (float(np.mean(pol))
                                              - diag["lam20"]["arrival"]),
                       "mcnemar_b_c": [b, c],
                       "mcnemar_p_onesided": mcnemar_exact_onesided(b, c),
                       "d0_captured_rate": float(d0_ev["captured_rate"])}
        print(f"seed {s}: delta={per_seed[s]['delta_hat']:+.3f} "
              f"pol={per_seed[s]['policy_arrival']:.3f} "
              f"zero={per_seed[s]['zero_arrival']:.3f} "
              f"McNemar b/c={b}/{c}", flush=True)
    rule = p1_pass_rule([per_seed[s]["delta_hat"] for s in (0, 1, 2)])
    doc = {"meta": {"doc": "docs/21 v0.3.2 SS4",
                    "label": "sealed holdout pilot (NOT population-"
                             "confirmatory)",
                    "bundle": a.sealed, "episodes_d1": len(d1),
                    "delta_gate": DELTA_GATE,
                    "diag_arms_note": "brake/lam20 recorded for the "
                                      "RL-necessity readout; verdict uses "
                                      "policy vs zero ONLY (v0.3.2)"},
           "diagnostic_arms": diag,
           "per_seed": per_seed, "rule": rule,
           "verdict": "P1_PASS" if rule["PASS"] else "P1_FAIL"}
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=1))
    marker = mark_sealed_consumed(".", note=f"a3e P1' judgment -> {a.out}")
    print(f"VERDICT {doc['verdict']} {rule} -> {a.out}; sealed consumed "
          f"({marker})", flush=True)


if __name__ == "__main__":
    main()
