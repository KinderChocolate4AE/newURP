"""A-3e DISCOVERY probe -- hybrid chain on TRUE NOMINAL mission resets.

Fork diagnostic for the (ppp) F=2 finding: the ratified rewind-v2 harvest
snapshots t = F - k (k in {2,4,8}, t >= 1), but the admissible cells are
d1-ONLY and a d1 spawn is BY CONSTRUCTION ~1 step before the witness --
the guard fires at F ~= 2, so the snapshot set is (near-)empty regardless
of policy quality. The only on-manifold source of long pre-fire tails is
success from DISTANT starts. This probe measures exactly that, with ZERO
scaffold: the hybrid chain (learned limiter + rule guard) on the frozen
judgment env's nominal resets (spawn_fn=None -- R-5 strict path).

Arms: learned seed 0/1/2 (--tag, default j1_e1 = hybrid argmax), brake+
guard, zero+guard. n=100/arm, reset seeds 950..1049 (fresh ledger band;
dev-side discovery, no sealed contact, no frozen thresholds). Readout per
arm: captured rate, fire-step distribution (= pre-fire tail length a
nominal success would donate to harvest), wasted, episode length.
DISCOVERY MODE: exploratory readout, recorded in full (docs/09 (ppp)).
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--ckpt-root", default="results/m3a_a3e_p1")
    ap.add_argument("--tag", default="j1_e1")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed0", type=int, default=950)
    ap.add_argument("--out", default="results/a3e_nominal_probe.json")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    from shepherd.scripts.a3d_calibration import _lim_fn      # +torch stub
    from shepherd.scripts.eval_heldout_m3 import learned_fns
    from shepherd.scripts.train_m3a import m3_eval_bundle
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    from shepherd.train.phi_potential import teacher_fire
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])

    def guard(obs, flags):                      # rule-based terminal guard
        return np.array([0, 0, 0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    lim_scale = np.full(3, 30.0, np.float32)
    arms = [("brake", _lim_fn("brake", {}))]
    for s in (0, 1, 2):
        root = pathlib.Path(a.ckpt_root) / f"seed{s}"
        if not (root / f"ckpt_mappo_{a.tag}.pt").exists():
            continue
        lf, _ff, meta = learned_fns(root, a.tag, a.device)
        arms.append((f"seed{s}:{a.tag}",
                     (lambda o, f, _lf=lf: _lf(o, f, lim_scale))))
    arms.append(("zero", _lim_fn("zero", {})))

    out = {"meta": {"doc": "docs/09 (ppp) fork diagnostic; discovery",
                    "spawns": "nominal (spawn_fn=None, frozen judgment env)",
                    "n": a.n, "seed0": a.seed0, "tag": a.tag},
           "arms": {}}
    for name, lim in arms:
        ev = m3_eval_bundle(env_cfg, m3, lim, guard, a.n, a.seed0,
                            stage=None, per_episode=True)
        fires = sorted(int(c["fire_step"]) for c in ev.get("fire_chains", []))
        rec = {"captured_rate": float(ev["captured_rate"]),
               "arrival_capture_rate": float(np.mean(
                   [int(r["arrival_capture"]) for r in ev["per_episode"]])),
               "fire_rate": float(ev["fire_rate"]),
               "n_fires": int(ev["n_fires"]),
               "wasted_mean": float(ev["wasted_mean"]),
               "len_mean": float(ev.get("len_mean", float("nan"))),
               "fire_steps": fires,
               "fire_step_ge9": int(sum(1 for f in fires if f >= 9)),
               "fire_step_ge3": int(sum(1 for f in fires if f >= 3))}
        out["arms"][name] = rec
        print(f"{name}: captured={rec['captured_rate']:.3f} "
              f"fires={rec['n_fires']} F>=3:{rec['fire_step_ge3']} "
              f"F>=9:{rec['fire_step_ge9']} wasted={rec['wasted_mean']:.2f} "
              f"len={rec['len_mean']:.0f}", flush=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"NOMINAL PROBE done -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
