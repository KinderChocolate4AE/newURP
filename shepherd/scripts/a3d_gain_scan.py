"""Phase 0-d SS8-1 (docs/18 RATIFIED 2026-07-17): PFC gain scan.

Selects the single global dimensionless gain pair (c_p, c_d) for the Gate A
privileged feasibility controller on the GAIN-TUNING bundle (variant
"tune", a3d_bundle_gen.py) -- episodes whose reset seeds are disjoint from
dev/sealed/admissibility seed families, so gain selection never touches
admissibility data (docs/18 SS5 selection-bias guard).

PRE-REGISTERED SELECTION RULE (fixed here, before any scan result is read;
the frozen pair is restated in the Phase 0-e commit):
  1. metric   = pooled arrival_capture count over ALL tuning episodes run
                (12 (stage x speed) cells x --eps-per-cell, teacher-coupled
                -- the instrument's actual use-case, MC judgment noise
                included);
  2. argmax over the finite grid (default {0.5, 1, 2} x {0.5, 1, 2});
  3. tie -> smaller c_p + c_d (least aggressive correction);
  4. tie -> smaller |c_p - 1| + |c_d - 1| (closest to neutral);
  5. tie -> smaller c_p, then smaller c_d (deterministic).
Adequacy, not optimality: any near-max pair is acceptable -- the binding
admissibility numbers come later from independent validation seeds, so
selection noise here cannot bias the verdicts.

Resumable like a3d_calibration (JSONL progress; rerun until ALL DONE).

Usage:
    python -m shepherd.scripts.a3d_bundle_gen --variants tune
    python -m shepherd.scripts.a3d_gain_scan --max-seconds 500   # repeat
    python -m shepherd.scripts.a3d_gain_scan --finalize
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np
import yaml

from shepherd.scripts.a3d_calibration import (_lim_fn, _done)  # stubs torch
from shepherd.scripts.a3d_sbe_bank import DT as BANK_DT
from shepherd.scripts.train_m3a import m3_eval_bundle
from shepherd.train.make_env_m3 import m3_params_from_cfg
from shepherd.train.phi_potential import teacher_fire

GRID_DEFAULT = (0.5, 1.0, 2.0)


def combo_key(cp: float, cd: float) -> str:
    return f"cp{cp:g}_cd{cd:g}"


def select_gains(pooled: dict) -> dict:
    """PRE-REGISTERED rule (docstring items 2-5). pooled maps
    (cp, cd) -> {"arr": int, "n": int}. Pure function (unit-tested)."""
    def rank(item):
        (cp, cd), agg = item
        return (-agg["arr"],                    # 2. argmax pooled count
                cp + cd,                        # 3. least aggressive
                abs(cp - 1.0) + abs(cd - 1.0),  # 4. closest to neutral
                cp, cd)                         # 5. deterministic
    best = sorted(pooled.items(), key=rank)[0]
    (cp, cd), agg = best
    return {"c_p": cp, "c_d": cd, "arr": agg["arr"], "n": agg["n"],
            "rate": agg["arr"] / max(agg["n"], 1)}


def _eps_subset(stage: dict, per_cell: int):
    """First --eps-per-cell episodes per (stage, att_speed), by ep order
    (deterministic preregistered subset of the tune bundle)."""
    by_v = {}
    for e in sorted(stage["episodes"], key=lambda x: int(x["ep"])):
        b = by_v.setdefault(float(e["att_speed"]), [])
        if len(b) < per_cell:
            b.append(e)
    return [e for v in sorted(by_v) for e in by_v[v]]


def run(args):
    bundle = json.loads(pathlib.Path(args.bundle).read_text())
    assert bundle["meta"]["variant"] == "tune", \
        "gain scan runs on the TUNE bundle only (docs/18 SS5)"
    run_cfg = yaml.safe_load(open(args.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    bank = json.loads(pathlib.Path(args.bank).read_text())

    def fin_fn(obs, flags):
        return np.array([0.0, 0.0, 0.0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    progress = pathlib.Path(args.progress)
    progress.parent.mkdir(parents=True, exist_ok=True)
    have = _done(progress)          # keys (stage, arm=combo_key, ep)
    from shepherd.train.make_env_m3 import Curriculum, frozen_constants
    import copy as _copy
    cur = Curriculum(_copy.deepcopy(run_cfg["curriculum"]),
                     frozen_constants(env_cfg, m3), env_cfg=env_cfg)
    name2idx = {st["name"]: i for i, st in enumerate(cur.sbe_stages)}
    grid = [(cp, cd) for cp in args.grid_cp for cd in args.grid_cd]
    t0, n_new = time.time(), 0
    for sname in args.stages:
        st = bundle["stages"][sname]
        cur.d_idx = name2idx[sname]
        stage = cur.overrides(0)
        eps = _eps_subset(st, args.eps_per_cell)
        for (cp, cd) in grid:
            ck = combo_key(cp, cd)
            ctx = {"bank": bank, "dt": BANK_DT, "k": int(st["k"]),
                   "cp": cp, "cd": cd, "gb_kp": 0.0, "gb_kd": 0.0,
                   "gb_dlead": 0.0}
            for e in eps:
                key = (sname, ck, int(e["ep"]))
                if key in have:
                    continue
                if time.time() - t0 > args.max_seconds:
                    print(f"BUDGET stop; new={n_new}")
                    return
                ev = m3_eval_bundle(
                    env_cfg, m3, _lim_fn("pfc", e, ctx), fin_fn, 1,
                    int(e["reset_seed"]), stage=stage,
                    spawn_fn=lambda _i, sp=e["spawn"]: dict(sp),
                    per_episode=True)
                r = ev["per_episode"][0]
                rec = {"stage": sname, "arm": ck, "ep": int(e["ep"]),
                       "cp": cp, "cd": cd,
                       "att_speed": float(e["att_speed"]),
                       "arrival_capture": r["arrival_capture"],
                       "captured": r["captured"],
                       "reset_clean": r["reset_clean"], "len": r["len"],
                       "n_fires": r["n_fires"]}
                with progress.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                n_new += 1
    print(f"ALL DONE; new={n_new}")


def finalize(args):
    rows = [json.loads(l) for l in
            pathlib.Path(args.progress).read_text().splitlines()
            if l.strip()]
    pooled, cells = {}, {}
    for r in rows:
        k = (float(r["cp"]), float(r["cd"]))
        agg = pooled.setdefault(k, {"arr": 0, "n": 0})
        agg["arr"] += int(r["arrival_capture"])
        agg["n"] += 1
        ck = cells.setdefault((r["arm"], r["stage"], r["att_speed"]),
                              {"arr": 0, "n": 0})
        ck["arr"] += int(r["arrival_capture"])
        ck["n"] += 1
    chosen = select_gains(pooled)
    doc = {"meta": {"note": "pre-registered selection rule in module "
                            "docstring; TUNE bundle only -- adequacy not "
                            "optimality; frozen pair restated in the "
                            "Phase 0-e commit", "n_rows": len(rows)},
           "pooled": [{"cp": cp, "cd": cd, **agg}
                      for (cp, cd), agg in sorted(pooled.items())],
           "cells": [{"combo": a, "stage": s, "att_speed": v, **agg}
                     for (a, s, v), agg in sorted(cells.items())],
           "chosen": chosen}
    pathlib.Path(args.out).write_text(json.dumps(doc, indent=1))
    print(f"wrote {args.out}; chosen = {chosen}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--bundle", default="results/a3d_bundle_tune.json")
    ap.add_argument("--bank", default="results/a3d_sbe_bank.json")
    ap.add_argument("--stages", nargs="+", default=["d1", "d2", "d3", "d4"])
    ap.add_argument("--grid-cp", nargs="+", type=float,
                    default=list(GRID_DEFAULT))
    ap.add_argument("--grid-cd", nargs="+", type=float,
                    default=list(GRID_DEFAULT))
    ap.add_argument("--eps-per-cell", type=int, default=10)
    ap.add_argument("--progress",
                    default="results/_calib/a3d_gain_scan_progress.jsonl")
    ap.add_argument("--out", default="results/a3d_gain_scan.json")
    ap.add_argument("--max-seconds", type=float, default=1e9)
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args()
    if a.finalize:
        finalize(a)
    else:
        run(a)


if __name__ == "__main__":
    main()
