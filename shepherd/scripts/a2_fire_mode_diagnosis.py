"""A-campaign Step 0: failure-mode diagnosis of the M3a full staged run (docs/12 SS2).

Reads the (y) artifacts -- NO training, NO torch, NO env import:

  * held-out endpoint JSONs (eval_heldout_m3 output, one per seed):
      results/m3a_heldout/m3a_full_seed*.json
  * (optional) training eval curves (train_m3a output, one per seed):
      results/m3a_full/seed*/eval_curve.json

Question (docs/09 (y), pre-registered BEFORE data contact -- docs/12 SS2):
did clean collapse into NO_FIRE (policy stops firing under the narrow cone),
BOXED_FIRE (policy still fires but from the boxed basin, L2 inheritance), or
CLEAN_MISS (fires mostly unboxed but below theta / capture-miss)?

  fire_ep_frac < FIRE_EP_MIN (0.05)          -> NO_FIRE
  elif boxed_at_fire >= BOXED_AT_FIRE_MIN (0.5) -> BOXED_FIRE
  else                                        -> CLEAN_MISS
  consensus = same mode in >= CONSENSUS_FRAC (0.7) of seeds, else MIXED
  branch map (docs/12 SS4): NO_FIRE->NF, BOXED_FIRE->BF, CLEAN_MISS->CM

Curves add S2 collapse localization: first sustained s2 eval point with
train-eval clean_cross_rate < CLEAN_DEAD (0.1), reported as ramp fraction and
implied (half_angle, theta_fire) via the ratified linear restore (S1 0.20/0.8
-> frozen 0.067/0.9 over s2_steps=150k, configs/m3a_full_staged.yaml).
Caveats: s2 entry is taken from the first eval point labelled 's2' (eval
cadence ~20k steps, and the transition eval itself ran at the OLD constants),
so implied widths are approximate to one eval interval -- diagnostic only.

CLI (server, any venv with numpy; TMPDIR=/data recommended, (y) ops caveat):
  python -m shepherd.scripts.a2_fire_mode_diagnosis \
      --heldout-glob 'results/m3a_heldout/m3a_full_seed*.json' \
      --curves-glob 'results/m3a_full/seed*/eval_curve.json' \
      --out results/m3a_heldout/a2_fire_mode.json
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
import pathlib
import re
import subprocess

import numpy as np

# --- pre-registered thresholds (docs/12 SS2; committed before data contact) --
FIRE_EP_MIN = 0.05        # below this fraction of fire-episodes -> NO_FIRE
BOXED_AT_FIRE_MIN = 0.5   # at/above this fraction of boxed fires -> BOXED_FIRE
CONSENSUS_FRAC = 0.7      # seed-mode agreement needed to avoid MIXED
CLEAN_DEAD = 0.1          # train-eval clean below this = dead (collapse point)
BRANCH = {"NO_FIRE": "NF", "BOXED_FIRE": "BF", "CLEAN_MISS": "CM"}
# ratified S2 linear-restore endpoints (docs/11 SS2 / m3a_full_staged.yaml)
S1_CONST = {"half_angle": 0.20, "theta_fire": 0.8}
FROZEN_CONST = {"half_angle": 0.067, "theta_fire": 0.9}
S2_STEPS = 150_000


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def _seed_of(path: str):
    m = re.search(r"seed(\d+)", pathlib.Path(path).as_posix())
    return int(m.group(1)) if m else None


def classify(s: dict) -> str:
    if s["fire_ep_frac"] < FIRE_EP_MIN:
        return "NO_FIRE"
    if s["boxed_at_fire"] >= BOXED_AT_FIRE_MIN:
        return "BOXED_FIRE"
    return "CLEAN_MISS"


def heldout_stats(path: str) -> dict:
    d = json.loads(pathlib.Path(path).read_text())
    eps = d["episodes"]
    chains = [c for r in eps for c in r.get("fire_chains", [])]
    n, nf = len(eps), len(chains)

    def cfrac(key):
        return float(np.mean([bool(c.get(key)) for c in chains])) if nf else 0.0

    o_pos = [c["o"] for c in chains if c.get("o", 0.0) > 0.0]
    odl = [c["o_dist_log"] for c in chains
           if c.get("o_dist_log") is not None and np.isfinite(c["o_dist_log"])]
    s = {
        "n_episodes": n,
        "fire_ep_frac": float(np.mean([r["fire_events"] > 0 for r in eps])),
        "fires_total": nf,
        "boxed_at_fire": cfrac("boxed"),
        "clean_at_fire": cfrac("clean"),
        "release_before_fire": cfrac("release_event_before_fire"),
        "captured_at_fire": cfrac("captured"),
        "wasted_at_fire": cfrac("wasted"),
        "clean_cross_rate": float(np.mean([r["clean"] for r in eps])),
        "captured_total": int(np.sum([bool(r["captured"]) for r in eps])),
        "wasted_rate": float(np.mean([r["wasted"] for r in eps])),
        "penetrated_rate": float(np.mean([r["penetrated"] for r in eps])),
        "boxed_dwell_frac": float(np.mean(
            [r["boxed_steps"] / max(r["len"], 1) for r in eps])),
        "len_mean": float(np.mean([r["len"] for r in eps])),
        "ret_mean": float(np.mean([r["ret"] for r in eps])),
        "fire_step_mean": (float(np.mean([c["fire_step"] for c in chains]))
                           if nf else None),
        "boxed_dwell_before_fire_mean": (
            float(np.mean([c["boxed_dwell_before_fire"] for c in chains]))
            if nf else None),
        "o_zero_at_fire_frac": (float(np.mean(
            [c.get("o", 0.0) <= 0.0 for c in chains])) if nf else None),
        "o_at_fire_median": float(np.median(o_pos)) if o_pos else None,
        "o_dist_log_median": float(np.median(odl)) if odl else None,
        "meta_tag": d.get("meta", {}).get("tag"),
    }
    s["mode"] = classify(s)
    return s


def _ramp_frac(step, s2_entry) -> float:
    return float(np.clip((step - s2_entry) / S2_STEPS, 0.0, 1.0))


def _implied(frac: float) -> dict:
    return {k: round(S1_CONST[k] + frac * (FROZEN_CONST[k] - S1_CONST[k]), 4)
            for k in S1_CONST}


def curve_stats(path: str) -> dict:
    pts = json.loads(pathlib.Path(path).read_text())
    te = lambda p: p.get("train_eval", {})  # noqa: E731
    s1 = [p for p in pts if p.get("stage") == "s1"]
    s2plus = [p for p in pts if p.get("stage") in ("s2", "s3")]
    out = {"n_points": len(pts),
           "s1_last_train_clean": (te(s1[-1]).get("clean_cross_rate")
                                   if s1 else None),
           "s2_entry_step": s2plus[0]["step"] if s2plus else None,
           "final_stage": pts[-1].get("stage") if pts else None,
           "final_frozen_clean": (pts[-1].get("clean_cross_rate")
                                  if pts else None),
           "final_frozen_fire_rate": (pts[-1].get("fire_rate")
                                      if pts else None)}
    if not s2plus:
        out["collapse"] = None
        return out
    entry = out["s2_entry_step"]
    collapse = None
    last_alive = None
    for i, p in enumerate(s2plus):
        clean = te(p).get("clean_cross_rate")
        if clean is None:
            continue
        if clean >= CLEAN_DEAD:
            last_alive = p
            continue
        nxt = te(s2plus[i + 1]).get("clean_cross_rate") \
            if i + 1 < len(s2plus) else None
        if nxt is None or nxt < CLEAN_DEAD:          # sustained death
            collapse = p
            break
    if collapse is None:
        out["collapse"] = None
    else:
        f = _ramp_frac(collapse["step"], entry)
        out["collapse"] = {
            "step": collapse["step"], "ramp_frac": round(f, 3),
            "implied": _implied(f),
            "train_clean": te(collapse).get("clean_cross_rate"),
            "train_fire_rate": te(collapse).get("fire_rate"),
            "train_boxed_fire_rate": te(collapse).get("boxed_fire_rate"),
        }
        if last_alive is not None:
            fa = _ramp_frac(last_alive["step"], entry)
            out["collapse"]["last_alive"] = {
                "step": last_alive["step"], "ramp_frac": round(fa, 3),
                "implied": _implied(fa),
                "train_clean": te(last_alive).get("clean_cross_rate"),
                "train_fire_rate": te(last_alive).get("fire_rate"),
                "train_boxed_fire_rate": te(last_alive).get("boxed_fire_rate"),
            }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout-glob", required=True)
    ap.add_argument("--curves-glob", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    hpaths = sorted(globmod.glob(a.heldout_glob))
    if not hpaths:
        raise SystemExit(f"no held-out JSONs match {a.heldout_glob!r}")
    per_seed = {}
    for p in hpaths:
        sd = _seed_of(p)
        per_seed[str(sd)] = {**heldout_stats(p), "path": p}

    curves = {}
    if a.curves_glob:
        for p in sorted(globmod.glob(a.curves_glob)):
            sd = _seed_of(p)
            try:
                curves[str(sd)] = {**curve_stats(p), "path": p}
            except Exception as e:                    # diagnostic-only input
                curves[str(sd)] = {"path": p, "error": repr(e)}

    modes = [s["mode"] for s in per_seed.values()]
    counts = {m: modes.count(m)
              for m in ("NO_FIRE", "BOXED_FIRE", "CLEAN_MISS")}
    pooled_mode = max(counts, key=lambda m: counts[m])
    consensus = counts[pooled_mode] >= CONSENSUS_FRAC * len(modes)
    all_chains_boxed = [s["boxed_at_fire"] for s in per_seed.values()
                        if s["fires_total"] > 0]
    verdict = {
        "per_seed_modes": {k: v["mode"] for k, v in sorted(
            per_seed.items(), key=lambda kv: int(kv[0]))},
        "counts": counts,
        "pooled_mode": pooled_mode,
        "consensus": bool(consensus),
        "verdict": pooled_mode if consensus else f"MIXED(primary={pooled_mode})",
        "branch": BRANCH[pooled_mode],
        "pooled_fire_ep_frac": float(np.mean(
            [s["fire_ep_frac"] for s in per_seed.values()])),
        "pooled_boxed_at_fire_firing_seeds": (
            float(np.mean(all_chains_boxed)) if all_chains_boxed else None),
    }
    coll = [c["collapse"] for c in curves.values()
            if isinstance(c, dict) and c.get("collapse")]
    if coll:
        fr = [c["ramp_frac"] for c in coll]
        verdict["collapse_ramp_frac_median"] = float(np.median(fr))
        verdict["collapse_implied_median"] = _implied(float(np.median(fr)))

    out = {"meta": {"git_head": _git_head(),
                    "thresholds": {"FIRE_EP_MIN": FIRE_EP_MIN,
                                   "BOXED_AT_FIRE_MIN": BOXED_AT_FIRE_MIN,
                                   "CONSENSUS_FRAC": CONSENSUS_FRAC,
                                   "CLEAN_DEAD": CLEAN_DEAD,
                                   "S2_STEPS": S2_STEPS},
                    "heldout_glob": a.heldout_glob,
                    "curves_glob": a.curves_glob},
           "per_seed": per_seed, "curves": curves, "verdict": verdict}
    op = pathlib.Path(a.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1))

    print(f"{'seed':>4} {'mode':>10} {'fireEp':>7} {'boxed@F':>8} "
          f"{'clean@F':>8} {'rel<F':>6} {'dwell':>6} {'ret':>7}")
    for k, s in sorted(per_seed.items(), key=lambda kv: int(kv[0])):
        print(f"{k:>4} {s['mode']:>10} {s['fire_ep_frac']:7.3f} "
              f"{s['boxed_at_fire']:8.3f} {s['clean_at_fire']:8.3f} "
              f"{s['release_before_fire']:6.2f} {s['boxed_dwell_frac']:6.2f} "
              f"{s['ret_mean']:+7.2f}")
    print(f"verdict={verdict['verdict']} branch={verdict['branch']} "
          f"counts={counts}")
    if coll:
        print(f"S2 collapse ramp_frac median={verdict['collapse_ramp_frac_median']:.2f} "
              f"implied={verdict['collapse_implied_median']} -> {op}")


if __name__ == "__main__":
    main()
