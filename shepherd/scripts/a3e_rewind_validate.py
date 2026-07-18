"""rewind-v2 screen + independent validation + synthetic comparator
(docs/21 v0.3 SS5 FROZEN; docs/09 (kkk)/(mmm)). torch-free; SINGLE RUN each
(rewind-v2 one-shot principle -- no reselection/threshold change after).

SCREEN (--stage screen): per accepted candidate, paired RT-PFC/zero on the
EXACT snapshot (no jitter -- the bank v2 screen contract), reset seeds
750..769, PASS = rt >= 16/20 AND zero <= 4/20 AND reset_clean <= 4/20
(fail-fast). Output: results/a3e_rewind_bank.json (screened bank).

VALIDATE (--stage validate): per cell (witness, k), 4-condition independent
validation exactly as docs/19 v0.3 SS6 with RT-PFC in the Gate-A seat:
n=100/cell, seeds 800..899, allocation floor+remainder-to-front,
sigma-materialised (bundle mechanism; jitter rng 310_000+1000*k+v, one
stream per cell, allocation order; velocities exact), 12 arms recorded
(verdict = rt_pfc/zero only), bootstrap rng 777 sequential (primary
episode -> draw-cluster -> source-policy-cluster). PRIMARY hypothesis
verdict = k=2 POOLED (existing k2 cells, equal weight): all four
conditions on the pooled sets; per-cell = secondary. Gate B kept: gap>0.4
=> "privileged-feasible but hand-controller-hard". COMPARATOR: the
synthetic bank v2 k=2 draws (v16/v20/v24 d2) re-evaluated on the SAME
seeds/sigma with judgment arms (classic PFC/zero), jitter rng
320_000+1000*k+v -- descriptive only (fixed evaluation, not regeneration).
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml

from shepherd.scripts.a3d_bankv2_validate import (allocation, cell_verdict,
                                                  cluster_lcb, lcb_mean)
from shepherd.scripts.a3d_calibration import _lim_fn      # torch stub
from shepherd.scripts.a3d_sbe_bank_v2 import (PFC_MIN, RESETC_MAX, ZERO_MAX)
from shepherd.scripts.train_m3a import m3_eval_bundle
from shepherd.train import a3e as A
from shepherd.train import pfc as pfc_mod
from shepherd.train.make_env_m3 import m3_params_from_cfg
from shepherd.train.phi_potential import teacher_fire

GATEB = ("brake", "lam2", "lam5", "lam10", "lam20",
         "attpd_2_3", "attpd_4_4", "attpd_8_6")
ATTPD = {(2, 3): 1.0, (4, 4): 1.0, (8, 6): 1.0}
BOOT_SEED = 777


def _fin(theta):
    def fin(obs, flags):
        return np.array([0, 0, 0,
                         1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)
    return fin


def arm_fn(arm: str, cand: dict, reset_seed: int):
    """Rewind arm dispatcher: Gate-A seat = RT-PFC (recorded reference);
    demo = open-loop recorded accels; rest identical to bank v2 validate."""
    if arm == "rt_pfc":
        rec = cand["rec"]
        return A.make_rt_pfc_fn(rec["P"], rec["V"], rec["A"], dt=0.05)
    if arm == "demo":
        return _lim_fn("demo", {"demo_accels": cand["rec"]["A"]})
    if arm in ("zero", "brake"):
        return _lim_fn(arm, {})
    if arm == "random":
        return _lim_fn("random", {"ep": int(reset_seed)})
    if arm.startswith("lam"):
        return pfc_mod.make_lambda_brake_fn(float(arm[3:]))
    if arm.startswith("attpd_"):
        kp, kd = (int(x) for x in arm.split("_")[1:])
        return pfc_mod.make_att_pd_fn(kp=kp, kd=kd, d_lead=ATTPD[(kp, kd)])
    raise ValueError(arm)


def run_ep(env_cfg, m3, theta, lim_fn, spawn, seed):
    ev = m3_eval_bundle(env_cfg, m3, lim_fn, _fin(theta), 1, int(seed),
                        stage=None,
                        spawn_fn=lambda _i, sp=spawn: dict(sp),
                        per_episode=True)
    return ev["per_episode"][0]


# ------------------------------------------------------------------ screen
def screen_candidate(cand, env_cfg, m3, theta,
                     seeds=A.REWIND_SCREEN_SEEDS) -> dict:
    n = len(seeds)
    rt = zero = rc = used = 0
    for i, seed in enumerate(seeds):
        used = i + 1
        rp = run_ep(env_cfg, m3, theta,
                    arm_fn("rt_pfc", cand, seed), cand["snapshot"], seed)
        rt += int(rp["arrival_capture"])
        rc += int(rp["reset_clean"])
        rz = run_ep(env_cfg, m3, theta, arm_fn("zero", cand, seed),
                    cand["snapshot"], seed)
        zero += int(rz["arrival_capture"])
        if (zero > ZERO_MAX or rc > RESETC_MAX
                or (used - rt) > n - PFC_MIN):
            break
    ok = (rt >= PFC_MIN and zero <= ZERO_MAX and rc <= RESETC_MAX
          and used == n)
    return {"pass": bool(ok), "rt": rt, "zero": zero, "reset_clean": rc,
            "seeds_used": used}


# ---------------------------------------------------------------- validate
def materialize_cell(cands, k, v, seeds=A.REWIND_VAL_SEEDS,
                     jit_base=A.REWIND_JIT_BASE):
    sig = A.REWIND_SIGMA[int(k)]
    rng = np.random.default_rng(jit_base + 1_000 * int(k) + int(v))
    plan, j = [], 0
    for di, n_eps in enumerate(allocation(len(cands))):
        sp = cands[di]["snapshot"]
        for _ in range(n_eps):
            L = (np.asarray(sp["limiters"], float)
                 + rng.normal(0, sig, (len(sp["limiters"]), 3)))
            ap = np.asarray(sp["att_p"], float) + rng.normal(0, sig, 3)
            plan.append((di, int(seeds[j]),
                         {"limiters": L.tolist(),
                          "limiter_v": [list(map(float, r))
                                        for r in sp["limiter_v"]],
                          "att_p": ap.tolist(),
                          "att_v": list(map(float, sp["att_v"])),
                          "att_speed": float(sp["att_speed"]),
                          "src": f"rewind_val_k{k}_v{v}"}))
            j += 1
    return plan


def validate_cell(cands, k, v, env_cfg, m3, theta, arms, log=print) -> dict:
    plan = materialize_cell(cands, k, v)
    out = {}
    for arm in arms:
        rows = []
        for di, seed, spawn in plan:
            r = run_ep(env_cfg, m3, theta, arm_fn(arm, cands[di], seed),
                       spawn, seed)
            rows.append({"draw": di, "source": int(cands[di]["source"]),
                         "arrival": int(r["arrival_capture"]),
                         "reset_clean": int(r["reset_clean"])})
        out[arm] = rows
        log(f"    v{v}:k{k} arm {arm}: "
            f"{np.mean([x['arrival'] for x in rows]):.2f}", flush=True)
    return {"plan_draws": [p[0] for p in plan], "arms": out}


def judge_cell(raw, n_draws) -> dict:
    rate = {a: float(np.mean([r["arrival"] for r in rows]))
            for a, rows in raw["arms"].items()}
    resetc = float(np.mean([r["reset_clean"] for r in raw["arms"]["rt_pfc"]]))
    diffs = [p["arrival"] - z["arrival"] for p, z in
             zip(raw["arms"]["rt_pfc"], raw["arms"]["zero"])]
    rng = np.random.default_rng(BOOT_SEED)     # sequential: ep, draw, source
    lcb = lcb_mean(diffs, rng)
    by_draw = [[] for _ in range(n_draws)]
    for di, d in zip(raw["plan_draws"], diffs):
        by_draw[di].append(d)
    lcb_draw = cluster_lcb([g for g in by_draw if g], rng)
    srcs = sorted({r["source"] for r in raw["arms"]["rt_pfc"]})
    by_src = {s: [] for s in srcs}
    for r, d in zip(raw["arms"]["rt_pfc"], diffs):
        by_src[r["source"]].append(d)
    lcb_src = cluster_lcb([by_src[s] for s in srcs], rng)
    gb = {a: rate[a] for a in GATEB if a in rate}
    gb_best = max(gb.values()) if gb else None
    gap = rate["rt_pfc"] - gb_best if gb_best is not None else None
    return {"arrival": {a: round(x, 3) for a, x in rate.items()},
            "reset_clean": round(resetc, 3),
            "delta_hat": round(float(np.mean(diffs)), 3),
            "gap_lcb95": round(lcb, 4),
            "gap_lcb95_drawcluster": round(lcb_draw, 4),
            "gap_lcb95_sourcecluster": round(lcb_src, 4),
            "gateb_best": None if gb_best is None else round(gb_best, 3),
            "hand_controller_hard": (None if gap is None
                                     else bool(gap > 0.4)),
            "verdict": cell_verdict(resetc, rate["rt_pfc"], rate["zero"],
                                    lcb),
            "_diffs": diffs, "_rows": raw["arms"]}


def pooled_k2(cell_judgments: dict) -> dict:
    """PRIMARY (docs/21 SS5): equal-weight pool over existing k=2 cells."""
    k2 = {c: j for c, j in cell_judgments.items() if c.endswith(":k2")}
    if not k2:
        return {"exists": False, "adopted": False}
    diffs, rt, zero, rc = [], [], [], []
    for j in k2.values():
        diffs += j["_diffs"]
        rt += [r["arrival"] for r in j["_rows"]["rt_pfc"]]
        zero += [r["arrival"] for r in j["_rows"]["zero"]]
        rc += [r["reset_clean"] for r in j["_rows"]["rt_pfc"]]
    lcb = lcb_mean(diffs, np.random.default_rng(BOOT_SEED))
    v = cell_verdict(float(np.mean(rc)), float(np.mean(rt)),
                     float(np.mean(zero)), lcb)
    return {"exists": True, "cells": sorted(k2), "n": len(diffs),
            "rt_pfc": round(float(np.mean(rt)), 3),
            "zero": round(float(np.mean(zero)), 3),
            "reset_clean": round(float(np.mean(rc)), 3),
            "gap_lcb95": round(lcb, 4), "verdict": v,
            "adopted": bool(v["admissible"])}


def comparator_synthetic_k2(bank_path, env_cfg, m3, theta, log=print):
    """Fixed re-evaluation of the synthetic k=2 draws (judgment arms only)
    on the rewind seeds/sigma -- descriptive, never a verdict input."""
    bank = json.loads(pathlib.Path(bank_path).read_text())
    cells: dict = {}
    for e in bank["entries"]:
        if int(e["k"]) == 2:
            cells.setdefault(int(float(e["spawn"]["att_speed"])),
                             []).append(e)
    out = {}
    for v in sorted(cells):
        entries = cells[v]
        plan = []
        sig = A.REWIND_SIGMA[2]
        rng = np.random.default_rng(A.COMPARATOR_JIT_BASE + 2_000 + v)
        j = 0
        for di, n_eps in enumerate(allocation(len(entries))):
            sp = entries[di]["spawn"]
            for _ in range(n_eps):
                L = (np.asarray(sp["limiters"], float)
                     + rng.normal(0, sig, (len(sp["limiters"]), 3)))
                ap = np.asarray(sp["att_p"], float) + rng.normal(0, sig, 3)
                plan.append((di, int(A.REWIND_VAL_SEEDS[j]),
                             {"limiters": L.tolist(),
                              "limiter_v": [list(map(float, r))
                                            for r in sp["limiter_v"]],
                              "att_p": ap.tolist(),
                              "att_v": list(map(float, sp["att_v"])),
                              "att_speed": float(sp["att_speed"]),
                              "src": f"cmp_k2_v{v}"}))
                j += 1
        res = {}
        for arm in ("pfc", "zero"):
            rows = []
            for di, seed, spawn in plan:
                if arm == "pfc":
                    lim = pfc_mod.make_pfc_fn(entries[di]["spawn"],
                                              entries[di]["demo_accels"],
                                              0.05, 1.0, 0.5)
                else:
                    lim = _lim_fn("zero", {})
                r = run_ep(env_cfg, m3, theta, lim, spawn, seed)
                rows.append(int(r["arrival_capture"]))
            res[arm] = rows
            log(f"    cmp v{v} {arm}: {np.mean(rows):.2f}", flush=True)
        diffs = [p - z for p, z in zip(res["pfc"], res["zero"])]
        out[f"v{v}:k2"] = {"pfc": round(float(np.mean(res["pfc"])), 3),
                           "zero": round(float(np.mean(res["zero"])), 3),
                           "delta_hat": round(float(np.mean(diffs)), 3),
                           "gap_lcb95": round(lcb_mean(
                               diffs, np.random.default_rng(BOOT_SEED)), 4)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("screen", "validate"), required=True)
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--candidates",
                    default="results/a3e_rewind_candidates.json")
    ap.add_argument("--bank-out", default="results/a3e_rewind_bank.json")
    ap.add_argument("--out", default="results/a3e_rewind_validation.json")
    ap.add_argument("--synthetic-bank",
                    default="results/a3d_sbe_bank_v2.json")
    a = ap.parse_args()
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])

    if a.stage == "screen":
        cd = json.loads(pathlib.Path(a.candidates).read_text())
        if not cd["meta"].get("instrument_ok"):
            raise SystemExit("instrument_ok is false -- stop rule 6 (record "
                             "as measurement failure; no screening)")
        bank = {"meta": {"doc": "docs/21 v0.3 SS5",
                         "screen_seeds": list(A.REWIND_SCREEN_SEEDS),
                         "from": a.candidates}, "cells": {}}
        for cname, cell in cd["cells"].items():
            if cell["missing"]:
                bank["cells"][cname] = {"missing": True,
                                        "reason": cell["reason"]}
                continue
            acc = []
            for cand in cell["accepted"]:
                scr = screen_candidate(cand, env_cfg, m3, theta)
                cand["screen"] = scr
                print(f"  {cname} cand({cand['source']},"
                      f"{cand['reset_seed']}): {scr}", flush=True)
                if scr["pass"]:
                    acc.append(cand)
            bank["cells"][cname] = {
                "missing": len(acc) < A.MIN_ACCEPT,
                "reason": (None if len(acc) >= A.MIN_ACCEPT
                           else "screen_below_min"),
                "accepted": acc if len(acc) >= A.MIN_ACCEPT else [],
                "n_screened": len(cell["accepted"]), "n_pass": len(acc)}
        pathlib.Path(a.bank_out).write_text(json.dumps(bank, indent=1))
        print(f"wrote {a.bank_out}: "
              f"{[c for c, d in bank['cells'].items() if not d['missing']]}")
        return

    bank = json.loads(pathlib.Path(a.bank_out).read_text())
    arms = ("rt_pfc", "zero") + GATEB + ("random", "demo")
    judgments = {}
    for cname, cell in sorted(bank["cells"].items()):
        if cell.get("missing"):
            continue
        v = int(cname.split(":")[0][1:])
        k = int(cname.split(":k")[1])
        print(f"CELL {cname} ({len(cell['accepted'])} predecessors):",
              flush=True)
        raw = validate_cell(cell["accepted"], k, v, env_cfg, m3, theta, arms)
        judgments[cname] = judge_cell(raw, len(cell["accepted"]))
    pooled = pooled_k2(judgments)
    print("comparator (synthetic k=2, judgment arms):", flush=True)
    cmp_k2 = comparator_synthetic_k2(a.synthetic_bank, env_cfg, m3, theta)
    for j in judgments.values():                    # strip working arrays
        j.pop("_diffs", None)
        j.pop("_rows", None)
    doc = {"meta": {"doc": "docs/21 v0.3 SS5",
                    "seeds": [A.REWIND_VAL_SEEDS[0], A.REWIND_VAL_SEEDS[-1]],
                    "jit_base": A.REWIND_JIT_BASE,
                    "cmp_jit_base": A.COMPARATOR_JIT_BASE,
                    "boot": [10_000, BOOT_SEED]},
           "cells": judgments,
           "pooled_k2_primary": pooled,
           "comparator_synthetic_k2": cmp_k2,
           "hypothesis": ("ON_MANIFOLD_ADOPTED" if pooled.get("adopted")
                          else "REJECTED_TO_B")}
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=1))
    print(f"HYPOTHESIS {doc['hypothesis']} pooled={pooled} -> {a.out}",
          flush=True)


if __name__ == "__main__":
    main()
