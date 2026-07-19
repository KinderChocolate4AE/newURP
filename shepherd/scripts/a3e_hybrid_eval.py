"""DISCOVERY sprint Arm A — hybrid architecture evaluation (docs/09 (ooo);
docs/20 v0.3 SS6). SERVER script (loads P1' J1 checkpoints). DISCOVERY
MODE: dev bundle only, no sealed contact, no new frozen thresholds --
results are exploratory readouts, recorded in full.

Question: does the LEARNED cooperative shaping (the L1 result: Delta^teacher
+.79/+.80/+.93) survive as an END-TO-END autonomous capture chain when the
teacher scaffold is replaced by the RULE-BASED TERMINAL GUARD?

  guard(obs) = fire iff v_soft >= theta AND p_feas > 0
             = teacher_fire(obs, theta)  -- obs-only (v_soft = obs[-3],
               p_feas = obs[-1], both part of the frozen 63-dim observation
               contract). Reframed from "training scaffold" to "system
               component": autonomous within the sim observability
               contract. (Real-world caveat, docs/09 (ooo): deployment
               needs an onboard estimator for these two quantities.)

Per (seed, ckpt tag): limiter policy from the ckpt + guard fire, evaluated
on the dev d1 bundle (120 eps, paired vs the embedded zero-cache) and the
dev d0 bundle (40 eps). Sweeping tags j1_e1..j1_e8 also measures how much
J1's broken-fire training DEGRADED the limiter policy after L1 (j1_e1 =
closest surviving snapshot to L1-exit; no L1-end ckpt was saved -- gap
noted). Records the sprint's mandatory readouts: paired Delta, wasted-fire
rate, P(fire|clean), P(fire|nonclean), fire-moment v_soft / feasibility.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml

from shepherd.train import a3e as A

TAGS_DEFAULT = tuple(f"j1_e{i}" for i in range(1, 9)) + ("best",)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--ckpt-root", default="results/m3a_a3e_p1")
    ap.add_argument("--dev-bundle",
                    default="results/a3e_bundle_dev_v2d1.json")
    ap.add_argument("--tags", nargs="+", default=list(TAGS_DEFAULT))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--out", default="results/a3e_hybrid_eval.json")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    import shepherd.scripts.a3d_calibration as _torch_stub  # side-effect
    del _torch_stub
    from shepherd.scripts.a3e_bundle_gen import load_bundle
    from shepherd.scripts.eval_heldout_m3 import learned_fns
    from shepherd.scripts.train_m3a import m3_eval_bundle
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    from shepherd.train.phi_potential import teacher_fire
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    dev = load_bundle(a.dev_bundle)
    d0 = dev["stages"]["d0"]["episodes"]
    d1 = dev["stages"]["d1"]["episodes"]
    zero_arr = [int(e["zero_arrival"]) for e in d1]

    def guard_fin(obs, flags):                  # rule-based terminal guard
        return np.array([0, 0, 0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    def bundle_eval(lim_fn, eps):
        ev = m3_eval_bundle(env_cfg, m3, lim_fn, guard_fin, len(eps),
                            int(eps[0]["reset_seed"]), stage=None,
                            spawn_fn=lambda i, _e=eps: dict(_e[i]["spawn"]),
                            per_episode=True)
        return ev

    lim_scale = np.full(3, 30.0, np.float32)
    out = {"meta": {"doc": "docs/09 (ooo) discovery Arm A",
                    "guard": "fire iff v_soft>=theta AND p_feas>0 "
                             "(obs-only; == teacher_fire)",
                    "dev_zero_rate": float(np.mean(zero_arr)),
                    "note": "dev = development data; exploratory readout"},
           "cells": {}}
    for s in a.seeds:
        for tag in a.tags:
            ckpt = pathlib.Path(a.ckpt_root) / f"seed{s}" / \
                f"ckpt_mappo_{tag}.pt"
            if not ckpt.exists():
                continue
            lf, _ff, meta = learned_fns(pathlib.Path(a.ckpt_root)
                                        / f"seed{s}", tag, a.device)
            lim = (lambda o, f, _lf=lf: _lf(o, f, lim_scale))
            ev = bundle_eval(lim, d1)
            rows = ev["per_episode"]
            pol = [int(r["arrival_capture"]) for r in rows]
            pd = A.paired_delta(pol, zero_arr)
            diag = A.diagnostics(rows)
            chains = ev.get("fire_chains", [])
            ev0 = bundle_eval(lim, d0)
            rec = {"ckpt_sha": meta["ckpt_sha256_12"],
                   "d1_arrival": float(np.mean(pol)),
                   **pd, "diag": diag,
                   "wasted_mean": float(ev["wasted_mean"]),
                   "fire_rate": float(ev["fire_rate"]),
                   "n_fires": int(ev["n_fires"]),
                   "fire_v_soft_mean": (float(np.mean(
                       [c["v_soft"] for c in chains])) if chains else None),
                   "fire_clean_frac": (float(np.mean(
                       [bool(c["clean"]) for c in chains]))
                       if chains else None),
                   "fire_feasible_frac": (float(np.mean(
                       [c["n_feasible"] > 0 for c in chains]))
                       if chains else None),
                   "d0_captured": float(ev0["captured_rate"])}
            out["cells"][f"seed{s}:{tag}"] = rec
            print(f"seed{s} {tag}: d1={rec['d1_arrival']:.3f} "
                  f"delta={rec['delta_hat']:+.3f} (lcb {rec['lcb95']:+.3f}) "
                  f"wasted={rec['wasted_mean']:.2f} "
                  f"pfnc={diag['p_fire_given_nonclean']} "
                  f"fire_clean={rec['fire_clean_frac']} "
                  f"d0={rec['d0_captured']:.2f}", flush=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    best = max(out["cells"].items(),
               key=lambda kv: kv[1]["delta_hat"], default=(None, None))
    print(f"BEST {best[0]}: {None if best[1] is None else best[1]['delta_hat']}"
          f" -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
