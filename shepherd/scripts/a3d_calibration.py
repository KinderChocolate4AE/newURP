"""Phase 0-c (docs/09 (ss)): control-arm calibration on a balanced bundle.

Arms (no learning; teacher finisher everywhere):
  zero    -- integrity null (no limiter action)
  random  -- uniform +-30 accel (rng = default_rng(90000 + 7*ep), the (rr)
             convention)
  brake   -- -30 * unit(v_i) read from obs (station-keeping heuristic; the
             competence line trained policies must beat)
  demo    -- open-loop replay of the episode's bank demo_accels, zeros after
             arrival (constructive ceiling, measured WITH the teacher)

Purpose: measure per-(stage x witness-speed) floors/ceilings on the PINNED
balanced dev bundle -> bank-admissibility verdicts (demo high / zero low /
gap wide) and exit derivation, all BEFORE any training run (pre-registration
order). The sealed bundle must NOT be rolled here.

Resumable: appends one JSON line per episode to --progress; safe to re-run
until "ALL DONE". --finalize aggregates progress into --out with per-cell
admissibility columns. --max-seconds bounds a single invocation (sandbox).

Usage:
    python -m shepherd.scripts.a3d_calibration --bundle results/a3d_bundle_dev.json \
        --arms zero brake demo random --max-seconds 3000
    python -m shepherd.scripts.a3d_calibration --finalize \
        --out results/a3d_calibration_dev.json
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import time

import numpy as np
import yaml

try:  # torch-less sandbox: m3_eval_bundle's module imports torch (stub ok)
    import torch  # noqa: F401
except ModuleNotFoundError:
    import sys
    import types

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

from shepherd.scripts.train_m3a import m3_eval_bundle                # noqa: E402
from shepherd.train.make_env_m3 import m3_params_from_cfg            # noqa: E402
from shepherd.train.phi_potential import teacher_fire, wilson_lcb    # noqa: E402

N_LIM = 4
ARMS = ("zero", "random", "brake", "demo")


def _lim_fn(arm: str, episode: dict):
    """Per-episode limiter policy closure (fresh per episode)."""
    if arm == "zero":
        return lambda o, f: [np.zeros(3, np.float32) for _ in range(N_LIM)]
    if arm == "random":
        rng = np.random.default_rng(90_000 + 7 * int(episode["ep"]))
        return (lambda o, f, rng=rng:
                [(rng.uniform(-1, 1, 3) * 30.0).astype(np.float32)
                 for _ in range(N_LIM)])
    if arm == "brake":
        def brake(o, f):
            o = np.asarray(o, float)
            acts = []
            for i in range(N_LIM):
                v = o[9 * i + 3: 9 * i + 6]
                n = np.linalg.norm(v)
                acts.append((-30.0 * v / n if n > 1e-6
                             else np.zeros(3)).astype(np.float32))
            return acts
        return brake
    if arm == "demo":
        da = np.asarray(episode["demo_accels"], float)   # (k, N_LIM, 3)
        cnt = {"t": 0}

        def demo(o, f, da=da, cnt=cnt):
            t = cnt["t"]
            cnt["t"] += 1
            if t < len(da):
                return [da[t, i].astype(np.float32) for i in range(N_LIM)]
            return [np.zeros(3, np.float32) for _ in range(N_LIM)]
        return demo
    raise ValueError(arm)


def _done(progress: pathlib.Path):
    have = set()
    if progress.exists():
        for ln in progress.read_text().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                continue
            have.add((r["stage"], r["arm"], int(r["ep"])))
    return have


def run(args):
    bundle = json.loads(pathlib.Path(args.bundle).read_text())
    assert bundle["meta"]["variant"] != "sealed" or args.allow_sealed, \
        "SEALED bundle: Phase-2 confirmatory only (docs/09 (ss))"
    run_cfg = yaml.safe_load(open(args.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])

    def fin_fn(obs, flags):
        return np.array([0.0, 0.0, 0.0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    progress = pathlib.Path(args.progress)
    progress.parent.mkdir(parents=True, exist_ok=True)
    have = _done(progress)
    t0, n_new = time.time(), 0
    stage_cfg = run_cfg["curriculum"]["sbe"]["stages"]
    stage_over = {st["name"]: st for st in stage_cfg}
    from shepherd.train.make_env_m3 import Curriculum, frozen_constants
    import copy as _copy
    cur = Curriculum(_copy.deepcopy(run_cfg["curriculum"]),
                     frozen_constants(env_cfg, m3), env_cfg=env_cfg)
    name2idx = {st["name"]: i for i, st in enumerate(cur.sbe_stages)}
    for sname in args.stages:
        st = bundle["stages"][sname]
        cur.d_idx = name2idx[sname]
        stage = cur.overrides(0)          # same stage constants as the run
        eps = st["episodes"]
        for arm in args.arms:
            for e in eps:
                key = (sname, arm, int(e["ep"]))
                if key in have:
                    continue
                if time.time() - t0 > args.max_seconds:
                    print(f"BUDGET stop; new={n_new}")
                    return
                ev = m3_eval_bundle(
                    env_cfg, m3, _lim_fn(arm, e), fin_fn, 1,
                    int(e["reset_seed"]), stage=stage,
                    spawn_fn=lambda _i, sp=e["spawn"]: dict(sp),
                    per_episode=True)
                r = ev["per_episode"][0]
                rec = {"stage": sname, "arm": arm, "ep": int(e["ep"]),
                       "witness": e["witness"],
                       "att_speed": float(e["att_speed"]),
                       **{k: r[k] for k in
                          ("captured", "clean", "reset_clean",
                           "arrival_capture", "spawn_capture", "len",
                           "n_fires")},
                       "parity": ev.get("gating_parity")}
                with progress.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                n_new += 1
    print(f"ALL DONE; new={n_new}")


def finalize(args):
    rows = [json.loads(l) for l in
            pathlib.Path(args.progress).read_text().splitlines() if l.strip()]
    cells = {}
    for r in rows:
        cells.setdefault((r["stage"], r["att_speed"], r["arm"]),
                         []).append(r)
    table = []
    for (sname, v, arm), rs in sorted(cells.items()):
        n = len(rs)
        cap = sum(x["captured"] for x in rs)
        arr = sum(x["arrival_capture"] for x in rs)
        table.append({"stage": sname, "att_speed": v, "arm": arm, "n": n,
                      "captured": cap / n, "arrival_capture": arr / n,
                      "arrival_lcb95": wilson_lcb(arr, n, 1.645),
                      "reset_clean": sum(x["reset_clean"] for x in rs) / n,
                      "len_mean": sum(x["len"] for x in rs) / n,
                      "per_ep_arrival": [int(x["arrival_capture"])
                                         for x in sorted(rs,
                                                         key=lambda y: y["ep"])]})
    adm = []
    idx = {(t["stage"], t["att_speed"], t["arm"]): t for t in table}
    for (sname, v) in sorted({(t["stage"], t["att_speed"]) for t in table}):
        d = idx.get((sname, v, "demo"))
        z = idx.get((sname, v, "zero"))
        if d is None or z is None:
            continue
        adm.append({"stage": sname, "att_speed": v,
                    "demo": d["arrival_capture"], "zero": z["arrival_capture"],
                    "gap": d["arrival_capture"] - z["arrival_capture"],
                    "admissible_example_rule":
                        bool(d["arrival_capture"] >= 0.8
                             and z["arrival_capture"] <= 0.2
                             and d["arrival_capture"]
                             - z["arrival_capture"] >= 0.4)})
    doc = {"meta": {"progress": args.progress, "n_rows": len(rows),
                    "note": "admissibility rule numbers are the review's "
                            "EXAMPLE values; final numbers are fixed in the "
                            "Phase 0-e pre-registration commit"},
           "cells": table, "admissibility": adm}
    pathlib.Path(args.out).write_text(json.dumps(doc, indent=1))
    print(f"wrote {args.out}: cells={len(table)} adm_rows={len(adm)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--bundle", default="results/a3d_bundle_dev.json")
    ap.add_argument("--arms", nargs="+", default=list(ARMS))
    ap.add_argument("--stages", nargs="+", default=["d1", "d2", "d3", "d4"])
    ap.add_argument("--progress",
                    default="results/_calib/a3d_calibration_progress.jsonl")
    ap.add_argument("--out", default="results/a3d_calibration_dev.json")
    ap.add_argument("--max-seconds", type=float, default=1e9)
    ap.add_argument("--allow-sealed", action="store_true")
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args()
    if a.finalize:
        finalize(a)
    else:
        run(a)


if __name__ == "__main__":
    main()
