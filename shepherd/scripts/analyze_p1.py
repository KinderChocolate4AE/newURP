"""P1 paired analysis over held-out CRN evals (docs/09 (o)/(p); torch-free).

Inputs = JSONs written by shepherd.scripts.eval_heldout, named
``<arm>_seed<k>.json`` plus ``scripted.json`` / ``hold.json`` baselines,
all sharing one CRN episode seed set (episode i paired across files).

Statistics (pre-registered):
  * seed-cluster hierarchical bootstrap (resample train seeds with
    replacement, then episodes within each chosen seed), B=10000, rng(7);
  * per-arm GATE metric: one-sided 95% lower bound of the seed-clustered
    mean CRN margin (arm - baseline, episode-paired) must be > 0 for BOTH
    baselines -> L2 gate (D2-A) PASS;
  * arm comparison: paired seed diff (common train seeds) with the same
    bootstrap; CI containing 0 => report "no separation", NOT superiority;
  * mode label: blocking := truncated & ~penetrated & ~captured;
    a train seed "discovered" blocking iff blocking rate >= 0.5.

CLI:
  python -m shepherd.scripts.analyze_p1 --eval-dir results/p1_eval \
      --arms mappo_run2 coma_run2 --out results/p1_eval/p1_report
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import re
from typing import Dict, List

import numpy as np

B_BOOT = 10_000
RNG_SEED = 7


# ------------------------------------------------------------------ loading --
def load_eval_dir(eval_dir: str, arms: List[str]) -> tuple:
    """Returns (arm -> {train_seed -> [episode rec,...]}, baselines dict)."""
    by_arm: Dict[str, Dict[int, list]] = {a: {} for a in arms}
    for a in arms:
        for f in sorted(glob.glob(os.path.join(eval_dir, f"{a}_seed*.json"))):
            m = re.search(r"_seed(\d+)\.json$", f)
            if not m:
                continue
            by_arm[a][int(m.group(1))] = json.load(open(f))["episodes"]
    bases = {}
    for b in ("scripted", "hold"):
        p = os.path.join(eval_dir, f"{b}.json")
        if os.path.exists(p):
            bases[b] = json.load(open(p))["episodes"]
    return by_arm, bases


def check_crn(by_arm, bases) -> int:
    """All files must share episode count (CRN pairing by index)."""
    ns = {len(v) for arm in by_arm.values() for v in arm.values()}
    ns |= {len(v) for v in bases.values()}
    if len(ns) != 1:
        raise ValueError(f"episode counts differ across files: {sorted(ns)}")
    return ns.pop()


# ------------------------------------------------------------------- labels --
def is_blocking(rec: dict) -> bool:
    return bool(rec["truncated"]) and not rec["penetrated"] and not rec["captured"]


def seed_stats(recs: list, base_eps: Dict[str, list]) -> dict:
    rets = np.array([r["ret"] for r in recs], float)
    out = {
        "n": len(recs),
        "return_mean": float(rets.mean()),
        "headline_mean": float(np.mean([r["headline_sum"] for r in recs])),
        "cost_gap_mean": float(np.mean([r["headline_sum"] - r["ret"] for r in recs])),
        "len_mean": float(np.mean([r["len"] for r in recs])),
        "penetrated_rate": float(np.mean([r["penetrated"] for r in recs])),
        "captured_rate": float(np.mean([r["captured"] for r in recs])),
        "clean_cross_rate": float(np.mean([r["clean"] for r in recs])),
        "wasted_mean": float(np.mean([r["wasted"] for r in recs])),
        "fire_events_mean": float(np.mean([r["fire_events"] for r in recs])),
        "blocking_rate": float(np.mean([is_blocking(r) for r in recs])),
    }
    out["blocking_discovered"] = out["blocking_rate"] >= 0.5
    for name, beps in base_eps.items():
        d = rets - np.array([b["ret"] for b in beps], float)   # CRN pairing
        out[f"margin_{name}_mean"] = float(d.mean())
    return out


# --------------------------------------------------------------- bootstrap ---
def _seed_cluster_boot(per_seed_eps: Dict[int, np.ndarray], rng,
                       b: int = B_BOOT) -> np.ndarray:
    """Bootstrap dist of mean-over-seeds of mean-over-episodes."""
    seeds = sorted(per_seed_eps)
    k = len(seeds)
    stats = np.empty(b)
    for i in range(b):
        pick = rng.choice(k, size=k, replace=True)
        vals = []
        for j in pick:
            eps = per_seed_eps[seeds[j]]
            idx = rng.integers(0, len(eps), size=len(eps))
            vals.append(eps[idx].mean())
        stats[i] = float(np.mean(vals))
    return stats


def boot_summary(per_seed_eps: Dict[int, np.ndarray], rng) -> dict:
    point = float(np.mean([v.mean() for v in per_seed_eps.values()]))
    dist = _seed_cluster_boot(per_seed_eps, rng)
    return {"point": point,
            "ci95": [float(np.percentile(dist, 2.5)),
                     float(np.percentile(dist, 97.5))],
            "lower95_one_sided": float(np.percentile(dist, 5.0)),
            "n_seeds": len(per_seed_eps)}


# -------------------------------------------------------------------- main ---
def analyze(eval_dir: str, arms: List[str]) -> dict:
    by_arm, bases = load_eval_dir(eval_dir, arms)
    n_eps = check_crn(by_arm, bases)
    rng = np.random.default_rng(RNG_SEED)
    rep = {"episodes_per_file": n_eps, "arms": {}, "gate": {},
           "paired": {}, "pre_registered": {
               "B": B_BOOT, "rng_seed": RNG_SEED,
               "gate_rule": "one-sided 95% lower bound of seed-clustered "
                            "mean CRN margin > 0 vs BOTH baselines",
               "discovery_rule": "blocking_rate >= 0.5"}}
    for b, eps in bases.items():
        rep.setdefault("baselines", {})[b] = seed_stats(eps, {})

    for a in arms:
        seeds = by_arm[a]
        rep["arms"][a] = {"per_seed": {str(s): seed_stats(v, bases)
                                       for s, v in sorted(seeds.items())}}
        rep["arms"][a]["mode_discovery_rate"] = float(np.mean(
            [rep["arms"][a]["per_seed"][str(s)]["blocking_discovered"]
             for s in seeds])) if seeds else float("nan")
        rep["arms"][a]["return"] = boot_summary(
            {s: np.array([r["ret"] for r in v]) for s, v in seeds.items()}, rng)
        gate = {}
        for bname, beps in bases.items():
            bret = np.array([r["ret"] for r in beps])
            margins = {s: np.array([r["ret"] for r in v]) - bret
                       for s, v in seeds.items()}
            gate[bname] = boot_summary(margins, rng)
            gate[bname]["pass"] = gate[bname]["lower95_one_sided"] > 0.0
        rep["gate"][a] = {**gate,
                          "pass": all(g["pass"] for g in gate.values())}

    if len(arms) == 2:
        a1, a2 = arms
        common = sorted(set(by_arm[a1]) & set(by_arm[a2]))
        diffs = {s: (np.array([r["ret"] for r in by_arm[a1][s]])
                     - np.array([r["ret"] for r in by_arm[a2][s]]))
                 for s in common}                      # CRN + same train seed
        bs = boot_summary(diffs, rng) if common else {}
        rep["paired"][f"{a1}-minus-{a2}"] = {
            **bs, "common_seeds": common,
            "per_seed_diff": {str(s): float(d.mean())
                              for s, d in diffs.items()},
            "separated": bool(bs and (bs["ci95"][0] > 0 or bs["ci95"][1] < 0)),
        }
    return rep


def to_markdown(rep: dict, arms: List[str]) -> str:
    L = ["# P1 held-out paired report", ""]
    L.append(f"episodes/file={rep['episodes_per_file']}, "
             f"B={rep['pre_registered']['B']}, rng={rep['pre_registered']['rng_seed']}")
    for a in arms:
        A = rep["arms"][a]
        L += ["", f"## {a}  (mode discovery {A['mode_discovery_rate']:.0%}, "
              f"return {A['return']['point']:+.2f} "
              f"CI[{A['return']['ci95'][0]:+.2f},{A['return']['ci95'][1]:+.2f}])",
              "", "| seed | return | margin_scripted | margin_hold | cost_gap "
              "| blocking | clean | fire |",
              "|---|---|---|---|---|---|---|---|"]
        for s, st in A["per_seed"].items():
            L.append(f"| {s} | {st['return_mean']:+.2f} "
                     f"| {st.get('margin_scripted_mean', float('nan')):+.2f} "
                     f"| {st.get('margin_hold_mean', float('nan')):+.2f} "
                     f"| {st['cost_gap_mean']:+.2f} | {st['blocking_rate']:.2f} "
                     f"| {st['clean_cross_rate']:.2f} | {st['fire_events_mean']:.2f} |")
        g = rep["gate"][a]
        L.append(f"\n**gate: {'PASS' if g['pass'] else 'FAIL'}** "
                 + " / ".join(f"vs {b}: lower95={g[b]['lower95_one_sided']:+.2f}"
                              for b in g if isinstance(g[b], dict)))
    for k, p in rep["paired"].items():
        if p:
            L += ["", f"## paired {k}: {p['point']:+.2f} "
                  f"CI[{p['ci95'][0]:+.2f},{p['ci95'][1]:+.2f}] "
                  f"separated={p['separated']} per-seed="
                  + str(p["per_seed_diff"])]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--arms", nargs=2, required=True)
    ap.add_argument("--out", required=True, help="path prefix (.json/.md)")
    a = ap.parse_args()
    rep = analyze(a.eval_dir, a.arms)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(rep, indent=2))
    out.with_suffix(".md").write_text(to_markdown(rep, a.arms))
    print(to_markdown(rep, a.arms))


if __name__ == "__main__":
    main()
