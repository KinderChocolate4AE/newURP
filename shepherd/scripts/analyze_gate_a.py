"""M3a Gate-A / Gate-B judgment over held-out CRN evals (docs/11 SS4; torch-free).

Inputs = JSONs written by shepherd.scripts.eval_heldout_m3, named
``<arm>_seed<k>.json`` (learned bundles), all sharing one CRN episode seed set
(EVAL_SEED0=77M+i, episode i paired across seeds).

Pre-registered (mirrors analyze_p1 machinery, docs/09 (p)):
  * seed-cluster hierarchical bootstrap (resample train seeds w/ replacement,
    then episodes within each), B=10000, rng(7);
  * Gate A (clean unlock): one-sided 95% lower bound of the seed-clustered mean
    clean_cross_rate must be > 0;
  * Gate B (capture existence): total capture_count > 0 (existence label only);
  * Strong pass: capture in >=2 train seeds OR mean capture_rate >= 0.01;
  * Paper-grade: one-sided 95% lower bound of seed-clustered mean capture_rate > 0.

CLI:
  python -m shepherd.scripts.analyze_gate_a \
      --eval-dir results/m3a_heldout --arm m3a_full --out results/m3a_heldout/gate_a
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import re
from typing import Dict

import numpy as np

B_BOOT = 10_000
RNG_SEED = 7


def load_arm(eval_dir: str, arm: str) -> Dict[int, list]:
    by_seed: Dict[int, list] = {}
    for f in sorted(glob.glob(os.path.join(eval_dir, f"{arm}_seed*.json"))):
        m = re.search(r"_seed(\d+)\.json$", f)
        if not m:
            continue
        by_seed[int(m.group(1))] = json.load(open(f))["episodes"]
    if not by_seed:
        raise SystemExit(f"no {arm}_seed*.json under {eval_dir}")
    return by_seed


def _seed_cluster_boot(per_seed: Dict[int, np.ndarray], rng, b: int = B_BOOT) -> np.ndarray:
    """Bootstrap dist of mean-over-seeds of mean-over-episodes (binary rates ok)."""
    seeds = sorted(per_seed)
    k = len(seeds)
    stats = np.empty(b)
    for i in range(b):
        pick = rng.choice(k, size=k, replace=True)
        vals = []
        for j in pick:
            eps = per_seed[seeds[j]]
            idx = rng.integers(0, len(eps), size=len(eps))
            vals.append(eps[idx].mean())
        stats[i] = float(np.mean(vals))
    return stats


def boot_summary(per_seed: Dict[int, np.ndarray], rng) -> dict:
    point = float(np.mean([v.mean() for v in per_seed.values()]))
    dist = _seed_cluster_boot(per_seed, rng)
    return {"point": point,
            "ci95": [float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5))],
            "lower95_one_sided": float(np.percentile(dist, 5.0)),
            "n_seeds": len(per_seed)}


def analyze(eval_dir: str, arm: str) -> dict:
    by_seed = load_arm(eval_dir, arm)
    ns = {len(v) for v in by_seed.values()}
    if len(ns) != 1:
        raise ValueError(f"episode counts differ across seeds: {sorted(ns)}")
    rng = np.random.default_rng(RNG_SEED)
    clean = {s: np.array([bool(r["clean"]) for r in v], float)
             for s, v in by_seed.items()}
    cap = {s: np.array([bool(r["captured"]) for r in v], float)
           for s, v in by_seed.items()}
    cap_count = {s: int(v.sum()) for s, v in cap.items()}
    gate_a = boot_summary(clean, rng)
    gate_a["pass"] = gate_a["lower95_one_sided"] > 0.0
    cap_boot = boot_summary(cap, rng)
    total_cap = int(sum(cap_count.values()))
    seeds_with_cap = int(sum(1 for c in cap_count.values() if c > 0))
    mean_cap_rate = float(np.mean([v.mean() for v in cap.values()]))
    return {
        "arm": arm, "episodes_per_seed": ns.pop(), "seeds": sorted(by_seed),
        "pre_registered": {
            "B": B_BOOT, "rng_seed": RNG_SEED,
            "gate_a": "one-sided 95% lower bound of seed-clustered mean clean_cross_rate > 0",
            "gate_b": "total capture_count > 0 (existence)",
            "strong": "capture in >=2 seeds OR mean capture_rate >= 0.01",
            "paper_grade": "one-sided 95% lower bound of seed-clustered mean capture_rate > 0"},
        "gate_a_clean": gate_a,
        "gate_b_capture_existence": {
            "total_capture_count": total_cap,
            "seeds_with_capture": seeds_with_cap,
            "per_seed_count": {str(s): c for s, c in cap_count.items()},
            "pass": total_cap > 0},
        "capture_rate_boot": cap_boot,
        "strong_pass": bool(seeds_with_cap >= 2 or mean_cap_rate >= 0.01),
        "paper_grade_pass": bool(cap_boot["lower95_one_sided"] > 0.0),
    }


def to_markdown(rep: dict) -> str:
    ga, gb, cr = (rep["gate_a_clean"], rep["gate_b_capture_existence"],
                  rep["capture_rate_boot"])
    L = [f"# M3a gates -- {rep['arm']} (seeds {rep['seeds']}, "
         f"{rep['episodes_per_seed']} eps/seed, B={rep['pre_registered']['B']}, "
         f"rng={rep['pre_registered']['rng_seed']})", ""]
    L.append(f"**Gate A (clean unlock): {'PASS' if ga['pass'] else 'FAIL'}** -- "
             f"clean_cross_rate point={ga['point']:.4f}, one-sided 95% "
             f"lower={ga['lower95_one_sided']:.4f}, "
             f"CI[{ga['ci95'][0]:.4f},{ga['ci95'][1]:.4f}]")
    L += ["", f"**Gate B (capture existence): {'PASS' if gb['pass'] else 'FAIL'}** -- "
          f"total captures={gb['total_capture_count']} across "
          f"{gb['seeds_with_capture']} seed(s); per-seed={gb['per_seed_count']}"]
    L += ["", f"Strong pass: {rep['strong_pass']} | Paper-grade: "
          f"{rep['paper_grade_pass']} (capture_rate point={cr['point']:.4f}, "
          f"lower95={cr['lower95_one_sided']:.4f})"]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--arm", required=True, help="filename prefix, e.g. m3a_full")
    ap.add_argument("--out", required=True, help="path prefix (.json/.md)")
    a = ap.parse_args()
    rep = analyze(a.eval_dir, a.arm)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(rep, indent=2))
    out.with_suffix(".md").write_text(to_markdown(rep))
    print(to_markdown(rep))


if __name__ == "__main__":
    main()
