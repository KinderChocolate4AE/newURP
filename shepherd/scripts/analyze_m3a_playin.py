"""M3a warm-vs-scratch play-in judgment (PRE-REGISTERED rule, docs/11 SS3).

Selection rule (ratified order; ties resolved per rule 4 "scratch preference"
to avoid inheriting the L2 boxed-basin bias):
  (1) higher mean S1 train-eval clean_cross_rate       (primary)
  (2) tie -> lower mean boxed_fire_rate
  (3) tie -> higher mean frozen-heldout clean_cross_rate (monitoring file,
      eval_heldout_m3 output, if provided)
  (4) no meaningful difference -> SCRATCH.
"Tie" = |diff| <= --tie-eps (default 0.02, pre-registered here; the reference
score clean + 0.5*cap - 0.5*boxed_fire - 0.2*boxed_dwell is printed as a
DIAGNOSTIC only, never the decision).

Inputs = the per-seed summary.json files written by train_m3a.py. The S1
train-eval numbers are taken from each summary's final_eval.train_eval
(S1-constants bundle; in s1_only mode the last-3 frozen means are ALSO S1-run
outputs -- both are printed).

CLI:
  python -m shepherd.scripts.analyze_m3a_playin \
      --warm results/m3a_playin/warm --scratch results/m3a_playin/scratch \
      [--heldout-warm results/m3a_heldout/warm_*.json ...] \
      [--heldout-scratch ...] --out results/m3a_playin/decision.json
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib

import numpy as np


def load_arm(root: str) -> list:
    outs = []
    for f in sorted(pathlib.Path(root).glob("seed*/summary.json")):
        outs.append(json.loads(f.read_text()))
    if not outs:
        raise SystemExit(f"no seed*/summary.json under {root}")
    return outs


def arm_stats(summaries: list) -> dict:
    def mean(key):
        return float(np.mean([s[key] for s in summaries]))
    tr = [s.get("final_eval", {}).get("train_eval", {}) for s in summaries]
    return {
        "seeds": [s["seed"] for s in summaries],
        "clean_cross_rate_last3": mean("clean_cross_rate_last3"),
        "boxed_fire_rate_last3": mean("boxed_fire_rate_last3"),
        "captured_rate_last3": mean("captured_rate_last3"),
        "sel_score_last3": mean("sel_score_last3"),
        "capture_count_total": int(sum(
            s["capture_count_train_total"] + s["capture_count_eval_total"]
            for s in summaries)),
        "train_eval_clean_final": float(np.mean(
            [t.get("clean_cross_rate", float("nan")) for t in tr])),
        "train_eval_boxed_fire_final": float(np.mean(
            [t.get("boxed_fire_rate", float("nan")) for t in tr])),
    }


def heldout_clean(patterns: list) -> float:
    if not patterns:
        return float("nan")
    vals = []
    for pat in patterns:
        for f in glob.glob(pat):
            d = json.loads(open(f).read())
            vals.append(float(np.mean([r["clean"] for r in d["episodes"]])))
    return float(np.mean(vals)) if vals else float("nan")


def decide_playin(W: dict, S: dict, eps: float):
    """PRE-REGISTERED selection rule (docs/11 SS3). Returns (winner, rule, steps).
    Rule 4 = ratified scratch preference on no meaningful difference."""
    steps = []
    d1 = W["clean_cross_rate_last3"] - S["clean_cross_rate_last3"]
    steps.append({"rule": 1, "metric": "clean_cross_rate_last3",
                  "warm": W["clean_cross_rate_last3"],
                  "scratch": S["clean_cross_rate_last3"], "diff": d1})
    if abs(d1) > eps:
        return ("warm" if d1 > 0 else "scratch"), 1, steps
    d2 = W["boxed_fire_rate_last3"] - S["boxed_fire_rate_last3"]
    steps.append({"rule": 2, "metric": "boxed_fire_rate_last3",
                  "warm": W["boxed_fire_rate_last3"],
                  "scratch": S["boxed_fire_rate_last3"], "diff": d2})
    if abs(d2) > eps:
        return ("warm" if d2 < 0 else "scratch"), 2, steps
    d3 = W["heldout_clean"] - S["heldout_clean"]
    steps.append({"rule": 3, "metric": "heldout_clean",
                  "warm": W["heldout_clean"],
                  "scratch": S["heldout_clean"], "diff": d3})
    if np.isfinite(d3) and abs(d3) > eps:
        return ("warm" if d3 > 0 else "scratch"), 3, steps
    return "scratch", 4, steps                   # ratified tie-break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warm", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--heldout-warm", nargs="*", default=[])
    ap.add_argument("--heldout-scratch", nargs="*", default=[])
    ap.add_argument("--tie-eps", type=float, default=0.02)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    W = arm_stats(load_arm(a.warm))
    S = arm_stats(load_arm(a.scratch))
    W["heldout_clean"] = heldout_clean(a.heldout_warm)
    S["heldout_clean"] = heldout_clean(a.heldout_scratch)

    winner, rule, steps = decide_playin(W, S, float(a.tie_eps))
    result = {"winner": winner, "decided_by_rule": rule, "tie_eps": float(a.tie_eps),
              "warm": W, "scratch": S, "steps": steps,
              "note": ("rule 4 = ratified scratch preference "
                       "(docs/11 SS3)" if rule == 4 else "")}
    print(json.dumps(result, indent=2))
    print(f"\n==> PLAY-IN WINNER: {winner.upper()} (rule {rule}; "
          f"diagnostic sel_score warm {W['sel_score_last3']:+.3f} vs "
          f"scratch {S['sel_score_last3']:+.3f})")
    if a.out:
        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
