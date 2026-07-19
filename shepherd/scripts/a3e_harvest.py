"""A-3e trajectory harvest -> rewind-v2 candidates (docs/21 v0.3 SS5 FROZEN;
docs/09 (kkk)/(mmm)/(ppp)). SERVER script (loads ckpts; torch via learned_fns).

HYBRID amendment (docs/09 (ppp), DISCOVERY mode, disclosed): P1' FAIL'd on
the learned shot but the L1 shaping survived (hybrid sweep: guard converts
it to autonomous capture). Harvest therefore runs on the HYBRID chain:
learned limiter (per-seed hybrid-argmax tag, default j1_e1 -- the closest
surviving snapshot to L1-exit; the "best" tag is a J1-corroded selection,
obsolete under hybrid) + RULE GUARD fire (teacher_fire; == the terminal
guard, obs-only). The policy finisher is NOT used anywhere.

Per admissible d1 cell (v16, v20):
  spawns  = 50 sigma-materialised d1 spawns (jitter rng 300_000+1000*k+v,
            k=1, ONE stream per cell) SHARED by all 3 source policies (CRN);
            reset seeds 700..749; episode key = (cell, source, reset_seed).
  rollout = each source seed's limiter ckpt (--tag) + guard fire,
            deterministic, full state/action recording.
  success = arrival_capture AND the fire chain fired CLEAN.
  snapshot= t = F - k for k in {2,4,8} with t >= 1 (pre-commit by
            construction: commit == F; asserted). Stored state = limiter
            p/v + attacker p/v (the SPAWN-CONTRACT full state; finisher/FSM
            fresh by contract) + the recorded reference (P, V, A) to F.
  gates   = contract-matched RESTORE (open-loop recorded accels + teacher
            fire from reset_to: trajectory atol 1e-3 AND clean fire AND
            arrival_capture) -> RT-1 (RT-PFC exact replay identity) ->
            RT-2 (fixed perturbation set 8 x sigma 0.005, rng 212_121:
            pooled endpoint err ratio rt/open < 0.6). RT-1/RT-2 failures
            are INSTRUMENT failures (stop rule 6), never hypothesis data.
  dedup   = state-aware d^2 < 1 (taus .05/.25/.05/.25), same-(cell,k) pool.
  select  = source-balanced (quota 4, cap 6, >=2 sources else k MISSING).
Everything runs to completion BEFORE selection (no early stop, 3rd-party
4.4). Output: results/a3e_rewind_candidates.json (screen/validation is
a3e_rewind_validate.py). SINGLE RUN (rewind-v2 one-shot principle).
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml

from shepherd.train import a3e as A

N_PER_SOURCE = 50
SOURCES = (0, 1, 2)


def _traj_rollout(env_cfg, m3, spawn, seed, lim_fn, fin_fn,
                  record_steps: int):
    """Deterministic rollout with per-step limiter state/action recording
    for the first `record_steps` steps; runs to episode end."""
    from shepherd.train.make_env_m3 import M3Adapter, gating_env_for_spawn
    from shepherd.train.pfc import ATT_P0, ATT_V0
    env, _, _ = gating_env_for_spawn(env_cfg, m3, spawn, stage=None)
    ad = M3Adapter(env)
    obs_d, _ = ad.reset_to(dict(spawn), seed=int(seed))
    obs = obs_d[ad.limiter_ids[0]]
    n = len(ad.limiter_ids)

    def _snap_obs(o):
        return (np.stack([o[9 * i: 9 * i + 3] for i in range(n)]),
                np.stack([o[9 * i + 3: 9 * i + 6] for i in range(n)]),
                (o[ATT_P0:ATT_P0 + 3].tolist(), o[ATT_V0:ATT_V0 + 3].tolist()))

    p0, v0, a0 = _snap_obs(obs)
    P, V, ATT, Acts = [p0], [v0], [a0], []
    flags = {}
    t = 0
    while True:
        lim = lim_fn(obs, flags)
        live = {lid: np.asarray(lim[i], np.float32)
                for i, lid in enumerate(ad.limiter_ids)}
        live[ad.finisher_id] = np.asarray(fin_fn(obs, flags), np.float32)
        r = ad.step(live)
        obs = r.obs[ad.limiter_ids[0]]
        flags = r.flags
        t += 1
        if t <= record_steps:
            Acts.append(np.stack([np.asarray(lim[i], float)
                                  for i in range(n)]))
            pt, vt, at = _snap_obs(obs)
            P.append(pt)
            V.append(vt)
            ATT.append(at)
        if r.done:
            break
    chains = list(r.flags["fire_chains"])
    return {"P": P, "V": V, "A": Acts, "att": ATT, "steps": t,
            "flags": r.flags, "chains": chains,
            "captured": bool(r.flags["captured"])}


def _teacher_fin(theta):
    from shepherd.train.phi_potential import teacher_fire

    def fin(obs, flags):
        return np.array([0, 0, 0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)
    return fin


def _seq_lim(accels):
    """Open-loop scripted limiter accel sequence; zero-hold after."""
    seq = [np.asarray(a, np.float32) for a in accels]
    cnt = {"t": 0}

    def lim(obs, flags):
        t = cnt["t"]
        cnt["t"] += 1
        if t < len(seq):
            return [seq[t][i] for i in range(seq[t].shape[0])]
        return [np.zeros(3, np.float32) for _ in range(seq[0].shape[0])]
    return lim


def restore_and_rt_gates(cand, env_cfg, m3, theta) -> dict:
    """Contract-matched restore + RT-1 + RT-2 for ONE candidate."""
    snap, rec = cand["snapshot"], cand["rec"]
    k = len(rec["A"])
    spawn = {**snap, "src": "a3e_restore"}
    fin = _teacher_fin(theta)
    # ---- restore: open-loop recorded accels ------------------------------
    ro = _traj_rollout(env_cfg, m3, spawn, cand["reset_seed"],
                       _seq_lim(rec["A"]), fin, record_steps=k)
    P_rec = np.asarray(rec["P"], float)
    err_o = (float(np.max(np.linalg.norm(
        np.asarray(ro["P"][:k + 1], float) - P_rec, axis=-1)))
        if len(ro["P"]) >= k + 1 else float("inf"))
    clean_fire = any(c.get("clean") for c in ro["chains"])
    arr = bool(ro["captured"] and clean_fire)
    restore_ok = bool(err_o <= A.RESTORE_ATOL and arr)
    # ---- RT-1: RT-PFC exact replay identity ------------------------------
    rt_fn = A.make_rt_pfc_fn(rec["P"], rec["V"], rec["A"], dt=0.05)
    r1 = _traj_rollout(env_cfg, m3, spawn, cand["reset_seed"], rt_fn, fin,
                       record_steps=k)
    err_1 = (float(np.max(np.linalg.norm(
        np.asarray(r1["P"][:k + 1], float) - P_rec, axis=-1)))
        if len(r1["P"]) >= k + 1 else float("inf"))
    rt1_ok = bool(err_1 <= A.RESTORE_ATOL)
    # ---- RT-2: fixed perturbation set ------------------------------------
    rng = np.random.default_rng(A.RT2_RNG)
    errs_rt, errs_ol = [], []
    for _ in range(A.RT2_N):
        pert = dict(spawn)
        pert["limiters"] = (np.asarray(snap["limiters"], float)
                            + rng.normal(0, A.RT2_SIGMA, (P_rec.shape[1], 3))
                            ).tolist()
        pert["att_p"] = (np.asarray(snap["att_p"], float)
                         + rng.normal(0, A.RT2_SIGMA, 3)).tolist()
        for fn, sink in ((A.make_rt_pfc_fn(rec["P"], rec["V"], rec["A"],
                                           dt=0.05), errs_rt),
                         (_seq_lim(rec["A"]), errs_ol)):
            rr = _traj_rollout(env_cfg, m3, pert, cand["reset_seed"], fn,
                               fin, record_steps=k)
            end = (np.asarray(rr["P"][k], float)
                   if len(rr["P"]) > k else np.asarray(rr["P"][-1], float))
            sink.append(float(np.mean(np.linalg.norm(end - P_rec[k],
                                                     axis=-1))))
    return {"restore_ok": restore_ok, "restore_err": err_o,
            "restore_arrival": arr, "rt1_ok": rt1_ok, "rt1_err": err_1,
            "rt2_err_rt": float(np.mean(errs_rt)),
            "rt2_err_open": float(np.mean(errs_ol))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--ckpt-root", default="results/m3a_a3e_p1")
    ap.add_argument("--tag", default="j1_e1",
                    help="limiter ckpt tag (hybrid argmax; docs/09 (ppp))")
    ap.add_argument("--out", default="results/a3e_rewind_candidates.json")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    import shepherd.scripts.a3d_calibration as _torch_stub  # side-effect
    del _torch_stub
    from shepherd.scripts.eval_heldout_m3 import learned_fns
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    sp = A.A3ESpawner(run_cfg["a3e"]["robust_bank"], run_cfg["a3e"]["bank"],
                      run_cfg["a3e"]["validation"])
    cells: dict = {}
    for e in sp.d1:
        cells.setdefault(int(float(e["spawn"]["att_speed"])), []).append(e)

    lim_scale = np.full(3, 30.0, np.float32)      # limiter accel bound
    guard = _teacher_fin(theta)                   # HYBRID: rule guard fire
    policies = {}
    for s in SOURCES:
        lf, _ff, meta = learned_fns(pathlib.Path(a.ckpt_root) / f"seed{s}",
                                    a.tag, a.device)
        policies[s] = ((lambda o, f, _lf=lf: _lf(o, f, lim_scale)), meta)
        print(f"source {s} tag={a.tag}: {meta}", flush=True)

    all_cands = []
    stats = {"episodes": 0, "success": 0, "post_commit": 0,
             "F_hist": {}}                    # (ppp) discovery instrumentation
    for v in sorted(cells):
        jr = np.random.default_rng(A.HARVEST_JIT_BASE + 1_000 * 1 + v)
        spawns = []
        for j in range(N_PER_SOURCE):             # shared across sources
            e = cells[v][j % len(cells[v])]["spawn"]
            L = (np.asarray(e["limiters"], float)
                 + jr.normal(0, A.D1_SIGMA, (len(e["limiters"]), 3)))
            spawns.append({"limiters": L.tolist(),
                           "limiter_v": [list(map(float, r))
                                         for r in e["limiter_v"]],
                           "att_p": (np.asarray(e["att_p"], float)
                                     + jr.normal(0, A.D1_SIGMA, 3)).tolist(),
                           "att_v": list(map(float, e["att_v"])),
                           "att_speed": float(e["att_speed"]),
                           "src": "a3e_harvest"})
        for s in SOURCES:
            lf, _m = policies[s]
            for j, seed in enumerate(A.HARVEST_SEEDS):
                stats["episodes"] += 1
                r = _traj_rollout(env_cfg, m3, spawns[j], seed, lf, guard,
                                  record_steps=10_000)
                chains = r["chains"]
                clean_fire = any(c.get("clean") for c in chains)
                if not (r["captured"] and clean_fire and chains):
                    continue
                F = int(chains[0]["fire_step"])
                stats["success"] += 1
                stats["F_hist"][str(F)] = stats["F_hist"].get(str(F), 0) + 1
                for k, t in A.snapshot_times(F).items():
                    assert t < F                    # pre-commit (commit==F)
                    snap = {"limiters": np.asarray(r["P"][t]).tolist(),
                            "limiter_v": np.asarray(r["V"][t]).tolist(),
                            "att_p": None, "att_v": None}
                    # attacker p/v from the recorded obs row at t
                    snap["att_p"] = r["att"][t][0]
                    snap["att_v"] = r["att"][t][1]
                    all_cands.append({
                        "cell": f"v{v}", "k": k, "source": s,
                        "reset_seed": int(seed), "fire_step": F, "t": t,
                        "snapshot": {**snap,
                                     "att_speed": float(spawns[j]
                                                        ["att_speed"])},
                        "rec": {"P": np.asarray(r["P"][t:F + 1]).tolist(),
                                "V": np.asarray(r["V"][t:F + 1]).tolist(),
                                "A": np.asarray(r["A"][t:F]).tolist()}})
        print(f"cell v{v}: eps so far {stats['episodes']} "
              f"success {stats['success']} cands {len(all_cands)}",
              flush=True)

    # gates -> dedup -> selection (all AFTER full execution)
    gated, inst_fail = [], []
    for c in all_cands:
        g = restore_and_rt_gates(c, env_cfg, m3, theta)
        c["gates"] = g
        if not g["rt1_ok"]:
            inst_fail.append(("rt1", c["cell"], c["k"]))
        if g["restore_ok"] and g["rt1_ok"]:
            gated.append(c)
    rt2_rt = [c["gates"]["rt2_err_rt"] for c in gated]
    rt2_ol = [c["gates"]["rt2_err_open"] for c in gated]
    rt2_ratio = (float(np.mean(rt2_rt) / max(np.mean(rt2_ol), 1e-12))
                 if gated else None)
    instrument_ok = (not inst_fail) and (rt2_ratio is not None
                                         and rt2_ratio < A.RT2_RATIO)

    out = {"meta": {"doc": "docs/21 v0.3 SS5 + docs/09 (ppp) hybrid",
                    "tag": a.tag,
                    "fire": "rule guard (teacher_fire; hybrid)",
                    "n_per_source": N_PER_SOURCE,
                    "sources": list(SOURCES),
                    "jitter_base": A.HARVEST_JIT_BASE,
                    "seeds": [A.HARVEST_SEEDS[0], A.HARVEST_SEEDS[-1]],
                    "stats": stats, "rt2_ratio_pooled": rt2_ratio,
                    "instrument_ok": bool(instrument_ok),
                    "instrument_failures": inst_fail},
           "cells": {}}
    for v in sorted(cells):
        for k in A.REWIND_KS:
            pool = [c for c in gated
                    if c["cell"] == f"v{v}" and c["k"] == k]
            dd = A.dedup_candidates(pool)
            sel = A.select_source_balanced(dd)
            out["cells"][f"v{v}:k{k}"] = {
                "pool": len(pool), "deduped": len(dd), **sel}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    ks_ok = [c for c, d in out["cells"].items() if not d["missing"]]
    print(f"instrument_ok={instrument_ok} rt2_ratio={rt2_ratio} "
          f"cells_with_bank={ks_ok} -> {a.out}", flush=True)
    if not instrument_ok:
        print("INSTRUMENT FAILURE (stop rule 6): record + halt; do NOT "
              "proceed to screen/validation or tune gains.", flush=True)


if __name__ == "__main__":
    main()
