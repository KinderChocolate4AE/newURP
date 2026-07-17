"""v16 re-refine, ONE-SHOT (docs/09 (aaa) preregistered criteria; docs/18 SS4).

Stage 1 (probe protocol, unchanged): v=16 states from the P4 probe glob,
candidates = own + donor transplant (existing a3_robust_witness_probe
machinery, iters 120, rng(23), search 100-104 / validation 200-209).
KEEP ALL candidates with robust-clean val >= 0.9 (not just the best -- the
(aaa) multi-candidate selection rule needs them all).

Stage 2 (arrival-form paired screen -- the actual acceptance gate, NEW):
per candidate, synthesize k in {1,2} predecessor draws x12 with the UNCHANGED
bank-v1 formula (a3d_sbe_bank.synth_draw: cone +-15deg, v0 U[0.3,0.8],
|a|<=24, 4 construction gates). Per kept draw, paired episodes on reset
seeds 300..319 (20 CRN seeds, reserved band -- disjoint from every prior
family) with the FROZEN instruments (PFC (c_p,c_d)=(1.0,0.5); teacher):
    draw PASS  <=>  pfc_succ >= 16/20  AND  zero_succ <= 4/20
                    AND reset_clean <= 4/20   (non-clean-spawn razor)
    k PASS     <=>  passing draws >= 8/12
    candidate  <=>  k=1 PASS AND k=2 PASS   (coverage target d1-d2)
Early aborts (fail-fast, order-invariant): zero_succ > 4, reset_clean > 4,
or pfc_fail > 4 kill the draw immediately; k=2 skipped if k=1 already < 8/12.
Note: on EXACT (unjittered) spawns PFC == open-loop demo identically
(tests/test_a3d_pfc.py lock) -- the screen measures fresh-CRN feasibility;
sigma-robustness is the bundle/validation side's job.

Selection among passers ((aaa)): max robust val -> max min(k1,k2) passing
draws -> min refine step (deterministic). Failure of all candidates =
v16 DISCARD (negative result preserved; docs/12 SS6 row).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import types

import numpy as np
import yaml

from shepherd.scripts.a3_robust_witness_probe import (
    ACCEPT_MIN, SEARCH_SEEDS, VAL_SEEDS, refine_robust, stats, transplant,
    union_for)
from shepherd.scripts.a3d_sbe_bank import (DT as BANK_DT, _ring, synth_draw)
from shepherd.scripts.a3d_calibration import _lim_fn                # torch stub
from shepherd.scripts.train_m3a import m3_eval_bundle
from shepherd.train.make_env_m3 import (Curriculum, frozen_constants,
                                        m3_params_from_cfg)
from shepherd.train import pfc as pfc_mod
from shepherd.train.spawn_bank import load_t0
from shepherd.train.phi_potential import teacher_fire

SCREEN_SEEDS = tuple(range(300, 320))     # (aaa) reserved CRN band
CP, CD = 1.0, 0.5                         # frozen gains ((zz))
PFC_MIN, ZERO_MAX, RESETC_MAX = 16, 4, 4  # /20
DRAWS_PER_K, K_PASS_MIN = 12, 8
MAX_ATTEMPTS = 24                         # construction-gate redraw budget


def _stage_ctx(run_cfg, env_cfg, m3):
    import copy
    cur = Curriculum(copy.deepcopy(run_cfg["curriculum"]),
                     frozen_constants(env_cfg, m3), env_cfg=env_cfg)
    n2i = {st["name"]: i for i, st in enumerate(cur.sbe_stages)}
    def stage_for(name):
        cur.d_idx = n2i[name]
        return cur.overrides(0)
    return stage_for


def screen_draw(entry, k, env_cfg, m3, stage, theta):
    """Paired PFC/zero screen on one draw. Returns dict (aborts early)."""
    spawn = entry["spawn"]

    def fin_fn(obs, flags):
        return np.array([0, 0, 0, 1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    pfc_s = zero_s = rc = 0
    used = 0
    for i, seed in enumerate(SCREEN_SEEDS):
        used = i + 1
        pf = pfc_mod.make_pfc_fn(spawn, entry["demo_accels"], BANK_DT, CP, CD)
        ev = m3_eval_bundle(env_cfg, m3, pf, fin_fn, 1, int(seed), stage=stage,
                           spawn_fn=lambda _i, sp=spawn: dict(sp),
                           per_episode=True)
        r = ev["per_episode"][0]
        pfc_s += int(r["arrival_capture"])
        rc += int(r["reset_clean"])
        ez = m3_eval_bundle(env_cfg, m3,
                            _lim_fn("zero", entry, None), fin_fn, 1,
                            int(seed), stage=stage,
                            spawn_fn=lambda _i, sp=spawn: dict(sp),
                            per_episode=True)
        zero_s += int(ez["per_episode"][0]["arrival_capture"])
        n = len(SCREEN_SEEDS)
        if (zero_s > ZERO_MAX or rc > RESETC_MAX
                or (used - pfc_s) > n - PFC_MIN):     # pfc can't reach 16
            break
    ok = (pfc_s >= PFC_MIN and zero_s <= ZERO_MAX and rc <= RESETC_MAX
          and used == len(SCREEN_SEEDS))
    return {"pass": bool(ok), "pfc": pfc_s, "zero": zero_s,
            "reset_clean": rc, "seeds_used": used}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--probe-glob", default="results/p4_probe/probe_s*.json")
    ap.add_argument("--out", default="results/a3d_v16_refine.json")
    ap.add_argument("--iters", type=int, default=120)
    a = ap.parse_args()

    # ---- stage 1: probe protocol, v=16 only, keep all val>=0.9 -----------
    t0s = load_t0(a.probe_glob)
    donor = max(t0s, key=lambda t: (t.x, t.v))
    v16 = [t for t in t0s if float(t.v) == 16.0]
    rng = np.random.default_rng(23)
    cands = []
    for t0 in v16:
        us = [union_for(t0.x, t0.v, s) for s in SEARCH_SEEDS]
        uv = [union_for(t0.x, t0.v, s) for s in VAL_SEEDS]
        pool = [("own", np.asarray(t0.limiters, float))]
        if (t0.x, t0.v) != (donor.x, donor.v):
            pool.append(("transplant", transplant(donor, t0.x, t0.v)))
        for step, (src, L0) in enumerate(pool):
            L, search_cl = refine_robust(us, L0, rng, iters=a.iters)
            val_cl, val_cap, val_vmin = stats(uv, L)
            row = {"x": float(t0.x), "v": float(t0.v), "src": src,
                   "refine_step": step, "search": round(float(search_cl), 3),
                   "val": round(float(val_cl), 3),
                   "stage1_accept": bool(val_cl >= ACCEPT_MIN),
                   "limiters": L.tolist()}
            cands.append(row)
            print(f"stage1 {t0.src}/{src}: search={search_cl:.2f} "
                  f"val={val_cl:.2f} -> "
                  f"{'KEEP' if row['stage1_accept'] else 'drop'}", flush=True)
    keep = [c for c in cands if c["stage1_accept"]]

    # ---- stage 2: arrival-form paired screen ------------------------------
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    stage_for = _stage_ctx(run_cfg, env_cfg, m3)
    anchors = _ring()
    for c in keep:
        t0 = types.SimpleNamespace(x=c["x"], v=c["v"],
                                   union_seed=int(VAL_SEEDS[0]),
                                   src=f"v16_refine/{c['src']}")
        Lstar = np.asarray(c["limiters"], float)
        c["k_results"] = {}
        cand_ok = True
        for k, sname in ((1, "d1"), (2, "d2")):
            if not cand_ok:
                break
            drng = np.random.default_rng(23_000 + k)     # deterministic
            stage = stage_for(sname)
            draws, attempts, drops = [], 0, {}
            while len(draws) < DRAWS_PER_K and attempts < MAX_ATTEMPTS:
                attempts += 1
                entry, reason = synth_draw(t0, k, drng, anchors, Lstar)
                if entry is None or not entry["kept"]:
                    drops[reason] = drops.get(reason, 0) + 1
                    continue
                draws.append(entry)
            passing, details = 0, []
            for d_i, entry in enumerate(draws):
                res = screen_draw(entry, k, env_cfg, m3, stage, theta)
                details.append(res)
                passing += int(res["pass"])
                print(f"  {c['src']} k={k} draw{d_i}: {res}", flush=True)
                if passing >= K_PASS_MIN:
                    break                                # k already passed
                if passing + (len(draws) - 1 - d_i) < K_PASS_MIN:
                    break                                # k can't pass
            k_ok = passing >= K_PASS_MIN
            c["k_results"][f"k{k}"] = {
                "attempts": attempts, "kept_draws": len(draws),
                "construction_drops": drops, "passing": passing,
                "pass": bool(k_ok), "details": details}
            cand_ok = cand_ok and k_ok
        c["accept"] = bool(cand_ok and c["k_results"].get("k1", {}).get("pass")
                           and c["k_results"].get("k2", {}).get("pass"))

    # ---- selection rule ((aaa)) -------------------------------------------
    passers = [c for c in keep if c.get("accept")]
    chosen = None
    if passers:
        def rank(c):
            k1 = c["k_results"]["k1"]["passing"]
            k2 = c["k_results"]["k2"]["passing"]
            return (-c["val"], -min(k1, k2), c["refine_step"])
        chosen = sorted(passers, key=rank)[0]
    doc = {"meta": {"criteria": "docs/09 (aaa) preregistered; screen seeds "
                                "300-319; frozen gains (1.0, 0.5); "
                                "reset_clean razor operationalized as <=4/20 "
                                "(same as zero razor)",
                    "n_stage1": len(cands), "n_keep": len(keep),
                    "n_pass": len(passers)},
           "candidates": keep,
           "verdict": ("ACCEPT" if chosen else "DISCARD_V16"),
           "chosen": ({k: chosen[k] for k in
                       ("x", "v", "src", "val", "refine_step", "limiters")}
                      if chosen else None)}
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=1))
    print(f"VERDICT: {doc['verdict']} -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
