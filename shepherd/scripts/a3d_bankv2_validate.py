"""SS6 [D-3] admissibility independent validation (docs/19 v0.3 FROZEN;
docs/09 (ggg)/(hhh)). Committed BEFORE any validation result is read.

Per (witness, k) cell of results/a3d_sbe_bank_v2.json (accepted draws only):

  EPISODES: 100 per cell. Draw allocation = floor(100/n_d) each + 1 extra
  for the first (100 mod n_d) draws IN DRAW-INDEX ORDER (mechanical
  tie-break; 3rd-party adoption). Reset seeds 600..699 assigned in that
  same order (draw 0's block first). SPAWNS: sigma-MATERIALIZED with the
  bundle mechanism verbatim (a3d_bundle_gen.build_bundle):
      L' = L + N(0, sigma, (n_lim, 3));  att_p' = att_p + N(0, sigma, 3);
      velocities exact -- sigma = stage sigma_pos from the run config.
  Jitter stream = default_rng(76_000 + 1_000*k + int(v)), ONE per cell,
  consumed sequentially in allocation order; both arms share the
  materialized spawn + reset seed (paired; PFC reference stays NOMINAL,
  so closed-loop value under jitter is what gets measured).

  ARMS (12; all recorded): judgment = pfc, zero. Gate B family (8, docs/19
  SS4) = brake, lam{2,5,10,20}, attpd{(2,3,1.0),(4,4,1.0),(8,6,1.0)}.
  diagnostics = random (rng 90_000 + 7*reset_seed), demo (open loop).
  Gate B / diagnostics never enter the verdict.

  VERDICT (outcome = arrival_capture; ALL FOUR required, else rule-C
  exclusion; regeneration/threshold tuning forbidden):
      A  p(reset_clean)      <= 0.2          (PFC-arm episodes)
      B  p(arrival_pfc)      >= 0.8
      C  p(arrival_zero)     <= 0.2
      D  LCB95(paired Delta = pfc - zero) > 0.4
  D = one-sided percentile bootstrap, 10,000 resamples, rng 777 --
  PRIMARY = episode-level; SENSITIVITY = draw-cluster bootstrap (draws
  resampled with replacement, reported only). One default_rng(777) is
  consumed sequentially: primary first, then cluster (preregistered).

  BANK VERDICT: coverage minimum = d1 AND d2 each keep >= 1 admissible
  cell, else the bank FAILS. Stages with 1 admissible cell = mechanistic
  pilot only (no family claim; d3/d4 are 1-cell by coverage design).
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml

from shepherd.scripts.a3d_bundle_gen import _stage_sigmas
from shepherd.scripts.a3d_calibration import _lim_fn        # torch stub side-effect
from shepherd.scripts.a3d_sbe_bank import DT as BANK_DT
from shepherd.scripts.train_m3a import m3_eval_bundle
from shepherd.train import pfc as pfc_mod
from shepherd.train.make_env_m3 import (Curriculum, frozen_constants,
                                        m3_params_from_cfg)
from shepherd.train.phi_potential import teacher_fire

VAL_SEEDS = tuple(range(600, 700))          # validation band (0-e ledger)
JITTER_BASE = 76_000                        # validation jitter namespace
EPS_PER_CELL = 100
BOOT_N, BOOT_SEED = 10_000, 777
P_RESETC_MAX, P_PFC_MIN, P_ZERO_MAX, GAP_EPS = 0.2, 0.8, 0.2, 0.4
CP, CD = 1.0, 0.5                           # frozen gains ((zz))
LAMBDAS = (2, 5, 10, 20)
ATTPD_GRID = ((2, 3, 1.0), (4, 4, 1.0), (8, 6, 1.0))
GATEB = (("brake",) + tuple(f"lam{g}" for g in LAMBDAS)
         + tuple(f"attpd_{a}_{b}" for a, b, _ in ATTPD_GRID))
K_TO_STAGE = {1: "d1", 2: "d2", 4: "d3", 8: "d4"}


def allocation(n_draws: int, total: int = EPS_PER_CELL):
    """floor(total/n) per draw + 1 extra for the first total%n draws."""
    base, rem = divmod(total, int(n_draws))
    return [base + (1 if i < rem else 0) for i in range(int(n_draws))]


def lcb_mean(diffs, rng, n_boot: int = BOOT_N, q: float = 0.05) -> float:
    """One-sided percentile bootstrap LCB of the mean (primary, episode)."""
    d = np.asarray(diffs, float)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    return float(np.quantile(d[idx].mean(axis=1), q))


def cluster_lcb(diffs_by_draw, rng, n_boot: int = BOOT_N,
                q: float = 0.05) -> float:
    """Draw-cluster bootstrap LCB (sensitivity only, never the verdict)."""
    groups = [np.asarray(g, float) for g in diffs_by_draw]
    m = len(groups)
    means = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, m, size=m)
        means[b] = float(np.concatenate([groups[int(i)] for i in pick]).mean())
    return float(np.quantile(means, q))


def cell_verdict(resetc: float, p_pfc: float, p_zero: float,
                 gap_lcb: float) -> dict:
    """Pure 4-condition verdict (docs/19 v0.3 SS6; inclusive thresholds)."""
    a = resetc <= P_RESETC_MAX
    b = p_pfc >= P_PFC_MIN
    c = p_zero <= P_ZERO_MAX
    d = gap_lcb > GAP_EPS
    return {"A_no_preempt": bool(a), "B_feasibility": bool(b),
            "C_action_necessity": bool(c), "D_gap_lcb": bool(d),
            "admissible": bool(a and b and c and d)}


def arm_fn(arm: str, entry: dict, reset_seed: int):
    """Fresh per-episode policy closure. pfc reference = NOMINAL bank spawn
    (jitter cancellation is the measured quantity); no arm sees the
    materialized spawn as an argument."""
    if arm == "pfc":
        return pfc_mod.make_pfc_fn(entry["spawn"], entry["demo_accels"],
                                   BANK_DT, CP, CD)
    if arm in ("zero", "brake"):
        return _lim_fn(arm, {})
    if arm == "random":
        return _lim_fn("random", {"ep": int(reset_seed)})
    if arm == "demo":
        return _lim_fn("demo", {"demo_accels": entry["demo_accels"]})
    if arm.startswith("lam"):
        return pfc_mod.make_lambda_brake_fn(float(arm[3:]))
    if arm.startswith("attpd_"):
        kp, kd = (int(x) for x in arm.split("_")[1:])
        dl = {(a, b): c for a, b, c in ATTPD_GRID}[(kp, kd)]
        return pfc_mod.make_att_pd_fn(kp=kp, kd=kd, d_lead=dl)
    raise ValueError(arm)


def materialize(entries, k: int, v: float, sigma: float,
                seeds=VAL_SEEDS, total: int = EPS_PER_CELL):
    """Cell plan: [(draw_idx, reset_seed, materialized spawn) x total] in
    allocation order; one jitter stream per cell (bundle mechanism)."""
    rng = np.random.default_rng(JITTER_BASE + 1_000 * k + int(v))
    plan, j = [], 0
    for di, n_eps in enumerate(allocation(len(entries), total)):
        sp = entries[di]["spawn"]
        for _ in range(n_eps):
            L = (np.asarray(sp["limiters"], float)
                 + rng.normal(0.0, sigma, (len(sp["limiters"]), 3)))
            ap = np.asarray(sp["att_p"], float) + rng.normal(0.0, sigma, 3)
            plan.append((di, int(seeds[j]),
                         {"limiters": L.tolist(),
                          "limiter_v": [list(map(float, r))
                                        for r in sp["limiter_v"]],
                          "att_p": ap.tolist(),
                          "att_v": list(map(float, sp["att_v"])),
                          "att_speed": float(v),
                          "src": f"val_{K_TO_STAGE[k]}_v{int(v)}"}))
            j += 1
    assert j == total
    return plan


def run_cell(entries, k, v, sigma, env_cfg, m3, stage, theta,
             arms, eval_fn=None, log=print):
    """All arms over the cell's 100 materialized episodes -> raw outcomes."""
    def fin_fn(obs, flags):
        return np.array([0, 0, 0, 1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    def default_eval(lim_fn, spawn, seed):
        ev = m3_eval_bundle(env_cfg, m3, lim_fn, fin_fn, 1, int(seed),
                            stage=stage,
                            spawn_fn=lambda _i, sp=spawn: dict(sp),
                            per_episode=True)
        return ev["per_episode"][0]

    ev = eval_fn or default_eval
    plan = materialize(entries, k, v, sigma)
    out = {}
    for arm in arms:
        rows = []
        for di, seed, spawn in plan:
            r = ev(arm_fn(arm, entries[di], seed), spawn, seed)
            rows.append({"draw": di, "seed": seed,
                         "arrival": int(r["arrival_capture"]),
                         "reset_clean": int(r["reset_clean"]),
                         "captured": int(bool(r.get("captured", 0))),
                         "len": int(r.get("len", -1))})
        out[arm] = rows
        log(f"    arm {arm}: arrival={np.mean([x['arrival'] for x in rows]):.2f}",
            flush=True)
    return plan, out


def judge_cell(entries, plan, out) -> dict:
    """Frozen statistics + 4-condition verdict from raw arm outcomes."""
    rate = {a: float(np.mean([r["arrival"] for r in rows]))
            for a, rows in out.items()}
    resetc = float(np.mean([r["reset_clean"] for r in out["pfc"]]))
    resetc_zero = float(np.mean([r["reset_clean"] for r in out["zero"]]))
    diffs = [p["arrival"] - z["arrival"]
             for p, z in zip(out["pfc"], out["zero"])]
    rng = np.random.default_rng(BOOT_SEED)          # sequential: primary, cluster
    gap_lcb = lcb_mean(diffs, rng)
    by_draw = [[] for _ in entries]
    for (di, _s, _sp), d in zip(plan, diffs):
        by_draw[di].append(d)
    gap_lcb_cluster = cluster_lcb(by_draw, rng)
    gb = {a: rate[a] for a in GATEB if a in rate}
    gateb_best = max(gb.values()) if gb else None
    gap_gb = (rate["pfc"] - gateb_best) if gateb_best is not None else None
    verdict = cell_verdict(resetc, rate["pfc"], rate["zero"], gap_lcb)
    n01 = sum(1 for d in diffs if d < 0)            # zero-only success
    return {"n_draws": len(entries), "allocation": allocation(len(entries)),
            "arrival": {a: round(r, 3) for a, r in rate.items()},
            "reset_clean": round(resetc, 3),
            "reset_clean_zero_arm": round(resetc_zero, 3),
            "delta_hat": round(float(np.mean(diffs)), 3),
            "gap_lcb95": round(gap_lcb, 4),
            "gap_lcb95_drawcluster": round(gap_lcb_cluster, 4),
            "discordant_p01": round(n01 / len(diffs), 3),
            "gateb_best": (round(gateb_best, 3)
                           if gateb_best is not None else None),
            "gateb_by_arm": {a: round(r, 3) for a, r in gb.items()},
            "pfc_gateb_gap": (round(gap_gb, 3) if gap_gb is not None
                              else None),
            "hand_controller_warning": (bool(gap_gb > 0.4)
                                        if gap_gb is not None else None),
            "verdict": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--bank", default="results/a3d_sbe_bank_v2.json")
    ap.add_argument("--out", default="results/a3d_bank_v2_validation.json")
    a = ap.parse_args()
    bank = json.loads(pathlib.Path(a.bank).read_text())
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    sigmas = {name: sg for name, (_k, sg) in _stage_sigmas(run_cfg).items()}
    import copy
    cur = Curriculum(copy.deepcopy(run_cfg["curriculum"]),
                     frozen_constants(env_cfg, m3), env_cfg=env_cfg)
    n2i = {st["name"]: i for i, st in enumerate(cur.sbe_stages)}

    cells = {}                                       # (witness, k) -> entries
    for e in bank["entries"]:
        cells.setdefault((e["witness"], int(e["k"])), []).append(e)
    arms = ("pfc", "zero") + GATEB + ("random", "demo")
    reports, matrix = {}, {}
    for (wname, k), entries in sorted(cells.items(),
                                      key=lambda kv: (kv[0][1], kv[0][0])):
        v = float(entries[0]["spawn"]["att_speed"])
        sname = K_TO_STAGE[k]
        cur.d_idx = n2i[sname]
        stage = cur.overrides(0)
        print(f"CELL v{int(v)}/{sname} ({len(entries)} draws, "
              f"sigma={sigmas[sname]}):", flush=True)
        plan, out = run_cell(entries, k, v, sigmas[sname], env_cfg, m3,
                             stage, theta, arms)
        rep = judge_cell(entries, plan, out)
        rep.update({"witness": wname, "stage": sname, "k": k,
                    "att_speed": v, "sigma_pos": sigmas[sname]})
        reports[f"v{int(v)}:{sname}"] = rep
        if rep["verdict"]["admissible"]:
            matrix.setdefault(sname, []).append(f"v{int(v)}")
        print(f"  -> {rep['verdict']} gap_lcb={rep['gap_lcb95']}", flush=True)

    cov_ok = bool(matrix.get("d1") and matrix.get("d2"))
    single = [s for s, cs in matrix.items() if len(cs) == 1]
    doc = {"meta": {"bank": a.bank, "seeds": [VAL_SEEDS[0], VAL_SEEDS[-1]],
                    "jitter_base": JITTER_BASE, "eps_per_cell": EPS_PER_CELL,
                    "boot": [BOOT_N, BOOT_SEED], "gains": [CP, CD],
                    "thresholds": {"reset_clean": P_RESETC_MAX,
                                   "pfc": P_PFC_MIN, "zero": P_ZERO_MAX,
                                   "gap_eps": GAP_EPS},
                    "gateb": list(GATEB),
                    "note": "docs/19 v0.3 SS6 frozen; committed before any "
                            "validation result was read; verdict arms = "
                            "pfc/zero only"},
           "cells": reports,
           "admissible_matrix": {s: sorted(cs) for s, cs in matrix.items()},
           "mechanistic_only_stages": sorted(single),
           "coverage_minimum_ok": cov_ok,
           "bank_verdict": "PASS" if cov_ok else "FAIL"}
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=1))
    print(f"BANK {doc['bank_verdict']}: matrix={doc['admissible_matrix']} "
          f"-> {a.out}", flush=True)


if __name__ == "__main__":
    main()
