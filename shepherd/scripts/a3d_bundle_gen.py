"""Phase 0-b (docs/09 (ss)): balanced dev/sealed gating bundles for A-3d.

External-review adoptions implemented here:
  * BALANCE   -- 30 episodes per witness speed {16, 20, 24} per stage
                 (pilot2's procedural draws were 34/19/27 at d1: overall
                 rates were hostage to strata luck);
  * DEV/SEALED-- two disjoint bundles. `dev` drives ladder gating and the
                 Phase-0c control calibration; `sealed` is committed now,
                 never rolled until the Phase-2 confirmatory adjudication
                 (adaptive-overfitting guard). Reset-seed ranges are
                 disjoint from each other and from every seed family used
                 so far (eval_seed0 5e5/1.5e6/2.5e6, witness search 100-109,
                 validation 200-209, phi Z_train 61-75, robust fresh 10);
  * MATERIALIZED SPAWNS -- episodes store the exact post-jitter spawn dict
                 (+ demo_accels for the demo control arm), so the bundle is
                 immune to later bank edits (bank v2 in Phase 0-d will
                 REPLACE the bank and both bundles get regenerated).

Reset seeds are contiguous per stage (seed0 + ep) so m3_eval_bundle can
replay any episode range verbatim. Per-stage sigma_pos comes from the run
config's sbe stages ((qq) fix).

Usage:
    python -m shepherd.scripts.a3d_bundle_gen \
        --config configs/m3a_a3d_pilot.yaml --out-dir results
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import yaml

SPEEDS = (16.0, 20.0, 24.0)
PER_SPEED = 30
VARIANTS = {"dev": {"rng_base": 71_000, "seed_base": 7_000_000},
            "sealed": {"rng_base": 93_000, "seed_base": 9_000_000},
            # 0-d SS8-1 (docs/18 RATIFIED): gain-tuning episodes ONLY.
            # Disjoint from dev (7.0M) / sealed (9.0M) / eval_seed0 families
            # (5e5, 1.5e6, 2.5e6) / oracle 31M; rng 81k family tops out at
            # 89_024 < the 90_000+7*ep random-arm family.
            "tune": {"rng_base": 81_000, "seed_base": 8_000_000}}
PURPOSES = {"dev": "ladder gating + Phase-0c calibration",
            "sealed": ("SEALED: Phase-2 confirmatory only "
                       "(docs/09 (ss)) -- do not roll before"),
            "tune": ("GAIN-TUNING ONLY (docs/18 SS5): PFC (c_p, c_d) "
                     "selection data; never used for admissibility "
                     "verdicts or exits")}


def _stage_sigmas(run_cfg: dict) -> dict:
    out = {}
    for st in run_cfg["curriculum"]["sbe"]["stages"]:
        if st.get("nominal") or int(st.get("k", 0)) == 0:
            continue
        out[st["name"]] = (int(st["k"]), float(st["sigma_pos"]))
    return out


def build_bundle(variant: str, bank: dict, stages: dict) -> dict:
    """Deterministic balanced bundle: per stage, per witness speed, PER_SPEED
    episodes = (entry pick, position jitter) drawn from one seeded rng."""
    spec = VARIANTS[variant]
    by_kv = {}
    for i, e in enumerate(bank["entries"]):
        by_kv.setdefault((int(e["k"]), float(e["spawn"]["att_speed"])),
                         []).append((i, e))
    out_stages = {}
    for name, (k, sigma) in sorted(stages.items()):
        eps = []
        for v in SPEEDS:
            group = by_kv[(k, v)]
            rng = np.random.default_rng(spec["rng_base"]
                                        + 1_000 * k + int(v))
            for _ in range(PER_SPEED):
                gi = int(rng.integers(len(group)))
                idx, e = group[gi]
                sp = e["spawn"]
                L = (np.asarray(sp["limiters"], float)
                     + rng.normal(0.0, sigma, (len(sp["limiters"]), 3)))
                ap = np.asarray(sp["att_p"], float) + rng.normal(0.0, sigma, 3)
                eps.append({
                    "witness": e["witness"], "entry_idx": idx,
                    "att_speed": v,
                    "spawn": {"limiters": L.tolist(),
                              "limiter_v": [list(map(float, r))
                                            for r in sp["limiter_v"]],
                              "att_p": ap.tolist(),
                              "att_v": list(map(float, sp["att_v"])),
                              "att_speed": v,
                              "src": f"bundle_{variant}_{name}"},
                    "demo_accels": e["demo_accels"]})
        base = spec["seed_base"] + 10_000 * k
        order = np.random.default_rng(spec["rng_base"] + 77 * k)
        perm = order.permutation(len(eps))        # interleave speed strata
        eps = [eps[int(i)] for i in perm]
        for i, ep in enumerate(eps):
            ep["ep"] = i
            ep["reset_seed"] = base + i
        out_stages[name] = {"k": k, "sigma_pos": sigma,
                            "seed0": base, "episodes": eps}
    return out_stages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--bank", default=None,
                    help="default: curriculum.sbe.bank from --config")
    ap.add_argument("--out-dir", default="results")
    ap.add_argument("--variants", nargs="+", default=["dev", "sealed"],
                    choices=sorted(VARIANTS))
    a = ap.parse_args()
    run_cfg = yaml.safe_load(open(a.config))
    bank_path = a.bank or run_cfg["curriculum"]["sbe"]["bank"]
    raw = pathlib.Path(bank_path).read_bytes()
    bank = json.loads(raw)
    stages = _stage_sigmas(run_cfg)
    for variant in a.variants:
        doc = {"meta": {"variant": variant, "config": a.config,
                        "bank": bank_path,
                        "bank_md5": hashlib.md5(raw).hexdigest(),
                        "per_speed": PER_SPEED, "speeds": list(SPEEDS),
                        "rng_base": VARIANTS[variant]["rng_base"],
                        "seed_base": VARIANTS[variant]["seed_base"],
                        "purpose": PURPOSES[variant]},
               "stages": build_bundle(variant, bank, stages)}
        out = pathlib.Path(a.out_dir) / f"a3d_bundle_{variant}.json"
        out.write_text(json.dumps(doc, indent=1))
        n = sum(len(s["episodes"]) for s in doc["stages"].values())
        print(f"{variant}: {out} stages={list(doc['stages'])} episodes={n}")


if __name__ == "__main__":
    main()
