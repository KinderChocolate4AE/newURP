"""A-3d scaffold-integrity control: null-policy baselines on the SBE gating
bundles (docs/09 (rr), 2026-07-16).

Measures what docs/17 SS4 only asserted. The V-5 rule was justified with
"no-action / no-arrival baseline ~ 0, so any significant arrival_capture is
learning evidence". That premise is FALSE for k>=2: SBE spawns inject
limiter_v (docs/17 SS1), so a ZERO-ACTION limiter coasts through the witness
window on inertia and the teacher fires -- construction-made captures.
Measured here (episodes matched 1:1 to the seed-0 gating bundle):

    d1 zero-action  arrival_capture  1/80  (Wilson LCB95 0.003)
    d2 zero-action  arrival_capture 19/80  (Wilson LCB95 0.169)  <- passes V-5
    d3 zero-action  arrival_capture 15/80  (Wilson LCB95 0.126)  <- passes V-5

Consequently V-5 must be adjudicated as a PAIRED CONTRAST against this
control (V-5' pending ratification), never as an absolute LCB. Run this on
every campaign whose spawns carry state the policy did not earn.

Usage (server or sandbox; eval path is torch-free):
    python -m shepherd.scripts.a3d_null_baseline \
        --config configs/m3a_a3d_pilot.yaml --episodes 80 \
        --eval-seed0 500000 --out results/a3d_null_baseline.json

Episode i of stage d reproduces gating-bundle episode i exactly:
reset seed = eval_seed0 + i, spawn = Curriculum.eval_spawn_fn()(i)
(deterministic in (d_idx, i); independent of the run seed). per-episode
0/1 vectors are stored so a paired (same-episode) contrast against any
policy evaluated on the same bundle needs no re-run.

Torch note: train_m3a imports torch at module level but m3_eval_bundle
itself is torch-free; on a torch-less interpreter a permissive stub is
installed (never activates where torch exists).
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
import types

import numpy as np
import yaml

try:  # sandbox verification without torch (see module docstring)
    import torch  # noqa: F401
except ModuleNotFoundError:
    class _Base:
        def __init__(self, *a, **k): pass
        def __call__(self, *a, **k): return _Base()
        def __getattr__(self, n): return _Base()

    class _Mod(types.ModuleType):
        def __getattr__(self, n): return type(n, (_Base,), {})

    for _n in ("torch", "torch.nn", "torch.nn.functional", "torch.optim",
               "torch.distributions"):
        sys.modules[_n] = _Mod(_n)
    for _p, _c in (("torch", "nn"), ("torch", "optim"),
                   ("torch", "distributions"), ("torch.nn", "functional")):
        setattr(sys.modules[_p], _c, sys.modules[_p + "." + _c])

from shepherd.scripts.train_m3a import m3_eval_bundle              # noqa: E402
from shepherd.train.make_env_m3 import (Curriculum,                # noqa: E402
                                        frozen_constants,
                                        m3_params_from_cfg)
from shepherd.train.phi_potential import (teacher_fire,            # noqa: E402
                                          wilson_lcb)

RAND_SEED_BASE = 90000          # uniform arm: rng = default_rng(BASE + 7*ep)


def _find_n_limiters(cfg: dict, default: int = 4) -> int:
    stack = [cfg]
    while stack:
        d = stack.pop()
        if isinstance(d, dict):
            if "n_limiters" in d:
                return int(d["n_limiters"])
            stack.extend(d.values())
    return default


def run(config: str, stages: list, arms: list, episodes: int,
        eval_seed0: int, out: str) -> dict:
    run_cfg = yaml.safe_load(open(config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    cur = Curriculum(copy.deepcopy(run_cfg["curriculum"]),
                     frozen_constants(env_cfg, m3), env_cfg=env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    n_lim = _find_n_limiters(env_cfg)
    name2idx = {st["name"]: i for i, st in enumerate(cur.sbe_stages)}

    def fin_fn(obs, flags):                       # the run's teacher gauge
        return np.array([0.0, 0.0, 0.0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    def zero_lim(obs, flags):
        return [np.zeros(3, np.float32) for _ in range(n_lim)]

    results = []
    for sname in stages:
        cur.d_idx = name2idx[sname]
        st = cur.sbe_stages[cur.d_idx]
        spawn_fn = cur.eval_spawn_fn()
        stage = cur.overrides(0)
        for arm in arms:
            per = {k: [] for k in ("arrival_capture", "captured",
                                   "spawn_capture", "reset_clean", "clean")}
            for ep in range(episodes):
                if arm == "zero_action":
                    lim_fn = zero_lim
                elif arm == "uniform_random":
                    rng = np.random.default_rng(RAND_SEED_BASE + 7 * ep)
                    lim_fn = (lambda o, f, rng=rng:
                              [(rng.uniform(-1, 1, 3) * 30.0)
                               .astype(np.float32) for _ in range(n_lim)])
                else:
                    raise ValueError(f"unknown arm '{arm}'")
                ev = m3_eval_bundle(env_cfg, m3, lim_fn, fin_fn, 1,
                                    eval_seed0 + ep, stage=stage,
                                    spawn_fn=lambda _e, ep=ep: spawn_fn(ep))
                per["arrival_capture"].append(int(ev["arrival_capture_rate"]))
                per["captured"].append(int(ev["captured_rate"]))
                per["spawn_capture"].append(int(ev["spawn_capture_rate"]))
                per["reset_clean"].append(int(ev["reset_clean_rate"]))
                per["clean"].append(int(ev["clean_cross_rate"]))
            n = episodes
            ka = sum(per["arrival_capture"])
            rec = {"stage": sname, "k": int(st["k"]), "arm": arm, "n": n,
                   "arrival_capture": ka / n,
                   "arrival_capture_lcb95": wilson_lcb(ka, n, 1.645),
                   "captured": sum(per["captured"]) / n,
                   "spawn_capture": sum(per["spawn_capture"]) / n,
                   "reset_clean": sum(per["reset_clean"]) / n,
                   "clean_cross": sum(per["clean"]) / n,
                   "per_ep": per}
            results.append(rec)
            print(f"{sname} k={st['k']} {arm:>15} n={n} "
                  f"arr={rec['arrival_capture']:.3f} "
                  f"(LCB95 {rec['arrival_capture_lcb95']:.3f}) "
                  f"cap={rec['captured']:.3f} "
                  f"reset_clean={rec['reset_clean']:.3f}", flush=True)
    doc = {"meta": {"config": config, "eval_seed0": eval_seed0,
                    "episodes": episodes,
                    "harness": "m3_eval_bundle + Curriculum.eval_spawn_fn "
                               "(gating bundle, teacher finisher)",
                    "uniform_arm_rng": f"default_rng({RAND_SEED_BASE}+7*ep)",
                    "purpose": "A-3d scaffold-integrity control "
                               "(docs/09 (rr); V-5' paired contrast)"},
           "arms": results}
    if out:
        pathlib.Path(out).write_text(json.dumps(doc, indent=1))
        print(f"wrote {out}")
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--stages", nargs="+", default=["d1", "d2", "d3"])
    ap.add_argument("--arms", nargs="+",
                    default=["zero_action", "uniform_random"])
    ap.add_argument("--episodes", type=int, default=80)
    ap.add_argument("--eval-seed0", type=int, default=500000)
    ap.add_argument("--out", default="results/a3d_null_baseline.json")
    a = ap.parse_args()
    run(a.config, a.stages, a.arms, a.episodes, a.eval_seed0, a.out)


if __name__ == "__main__":
    main()
