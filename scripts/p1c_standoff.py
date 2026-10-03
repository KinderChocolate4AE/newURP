"""P1c standoff probe 실행기 (manifest = scripts/p1c_standoff_manifest.py).

k > 1 세계는 B0 v3 밖의 v4 pre-check 변형: adversary_start_x 와 episode_len 만
k 배 (episode_len 기준값은 같은 (cell, sid) 의 k=1 빌드에서 직접 읽음 — 추측
금지), spawn jitter·방어 layout·χ/η 무차원화는 불변.

    python -m scripts.p1c_standoff --smoke
    python -m scripts.p1c_standoff --run [--shard K/N]   # (scale, attacker) 단위 샤딩
    python -m scripts.p1c_standoff --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import json
import pathlib

import numpy as np

from scripts.p1c_standoff_manifest import (ARMS, ATTACKERS, SCALES,
                                           load as load_p1c_manifest)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p1c_standoff"
EXEC_PATHS = ("shepherd", "scripts/p1c_standoff.py",
              "scripts/p1c_standoff_manifest.py",
              "artifacts/p1c_standoff/manifest.json")
START_KEY = "train.layout.adversary_start_x"
LEN_KEY = "train.episode_len"


def _overrides(att: dict) -> dict:
    return {k: (float("inf") if v == "inf" else v)
            for k, v in att["overrides"].items()}


def _build_scaled(ev: dict, b2: dict, cell: dict, sid: int, att_ov: dict, k: int):
    """k=1 빌드로 기준 episode_len 을 읽고, k>1 이면 layout 만 스케일해 재빌드."""
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    chi, eta, kw = scenario_kwargs(b2, cell, sid, seed0=ev["seed0"],
                                   seed_ns=ev["namespace"])
    kw = dict(kw)
    kw["attacker"] = replace(kw["attacker"], **att_ov)
    base = build_m4_env(ev["seed0"], sid, **kw)
    if k == 1:
        return chi, eta, base
    extra = dict(kw["extra_cfg"])
    extra[START_KEY] = float(extra[START_KEY]) * k
    extra[LEN_KEY] = int(base.lay.episode_len) * k
    kw["extra_cfg"] = extra
    return chi, eta, build_m4_env(ev["seed0"], sid, **kw)


def _run_arm(manifest: dict, b2: dict, *, scale: int, att: dict, arm: str,
             limiter_kw, smoke: bool) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    ev = manifest["evaluation"]
    cells = boundary_cells(b2)[:2] if smoke else boundary_cells(b2)
    epc = 1 if smoke else int(ev["episodes_per_cell"])
    sealed_epc = int(ev["episodes_per_cell"])
    att_ov = _overrides(att)
    rows = []
    for ci, cell in enumerate(cells):
        for j in range(epc):
            sid = ci * sealed_epc + j
            chi, eta, stack = _build_scaled(ev, b2, cell, sid, att_ov, scale)
            r = run_episode(stack.env, stack.scn, stack.lay,
                            seed=int(ev["seed0"]) + sid, policy=None,
                            limiter_mode=("hold" if arm == "hold" else "arc"),
                            limiter_kw=limiter_kw, fire_mode="clean")
            rows.append({"cell_id": cell["cell_id"], "scenario_id": sid,
                         "chi": chi, "eta": eta, "bin": partition_bin(r),
                         "fire": r.fire_step is not None,
                         "clean_crossings": int(r.clean_crossings),
                         "steps": int(r.steps)})
    counts = Counter(r["bin"] for r in rows)
    return {"schema": "p1c-standoff-arm-v1" + ("-smoke" if smoke else ""),
            "manifest_hash": manifest["manifest_hash"],
            "scale": scale, "attacker": att["label"], "arm": arm,
            "code_commit": git_commit(), "code_dirty_scoped": git_dirty(EXEC_PATHS),
            "n": len(rows), "counts": dict(sorted(counts.items())),
            "mean_steps": round(float(np.mean([r["steps"] for r in rows])), 2),
            "records": rows}


def run(*, shard: str | None = None, smoke: bool = False) -> None:
    from shepherd.provenance import git_dirty
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_p1c_manifest(), load_b2_manifest()
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    jobs = [(k, att) for k in SCALES for att in ATTACKERS]
    if smoke:
        jobs = [(1, ATTACKERS[0]), (4, ATTACKERS[0])]
    if shard:
        i, n = (int(x) for x in shard.split("/"))
        jobs = jobs[i::n]
    sub = "smoke" if smoke else "arms"
    for k, att in jobs:
        for arm in ARMS:
            path = OUT / sub / f"k{k}_{att['label']}_{arm}.json"
            if path.exists() and not smoke:
                print(f"skip existing k{k}_{att['label']}_{arm}", flush=True)
                continue
            out = _run_arm(manifest, b2, scale=k, att=att, arm=arm,
                           limiter_kw=(None if arm == "hold" else c5), smoke=smoke)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            print(f"k{k}/{att['label']}/{arm}: N={out['counts'].get('N', 0)}"
                  f"/{out['n']} H={out['counts'].get('H_illegal', 0)} "
                  f"steps={out['mean_steps']}", flush=True)


def readout() -> dict:
    from shepherd.provenance import git_commit
    manifest = load_p1c_manifest()
    expected_n = int(manifest["evaluation"]["episodes_per_arm_per_scale_per_attacker"])
    arms, missing = {}, []
    for k in SCALES:
        for att in ATTACKERS:
            for arm in ARMS:
                p = OUT / "arms" / f"k{k}_{att['label']}_{arm}.json"
                if p.exists():
                    arms[(k, att["label"], arm)] = json.loads(
                        p.read_text(encoding="utf-8"))
                else:
                    missing.append(f"k{k}_{att['label']}_{arm}")

    draws, draw_ok = {}, True
    for pl in arms.values():
        for r in pl["records"]:
            dk = (r["cell_id"], r["scenario_id"])
            val = (round(r["chi"], 12), round(r["eta"], 12))
            draw_ok &= draws.setdefault(dk, val) == val
    commits = {pl["code_commit"] for pl in arms.values()}
    hold_steps = {k: float(np.mean([pl["mean_steps"] for (kk, a, arm), pl
                                    in arms.items()
                                    if kk == k and arm == "hold"]) or 0)
                  for k in SCALES if any(kk == k for kk, _, _ in arms)}
    integrity = {
        "completion": not missing,
        "budget": all(pl["n"] == expected_n for pl in arms.values()),
        "paired_draws": draw_ok,
        "lineage": len(commits) == 1 and all(not pl["code_dirty_scoped"]
                                             for pl in arms.values()),
        "power_steps_increase": (1 in hold_steps and 4 in hold_steps
                                 and hold_steps[4] > hold_steps[1]),
    }
    decision = (manifest["gate"]["complete"] if all(integrity.values())
                else manifest["gate"]["invalid_decision"])

    def _N(k, arm):
        return sum(pl["counts"].get("N", 0) for (kk, a, ar), pl in arms.items()
                   if kk == k and ar == arm)

    gaps = {str(k): _N(k, "c5") - _N(k, "hold") for k in SCALES
            if any(kk == k for kk, _, _ in arms)}
    classification = None
    if decision == "COMPLETE_P1C":
        delta = gaps["4"] - gaps["1"]
        classification = {
            "G_by_scale_pooled_560": gaps, "G4_minus_G1": delta, "threshold": 28,
            "verdict": ("STANDOFF_OPENS_SHAPING" if delta >= 28
                        else "STANDOFF_DOES_NOT_OPEN"),
            "scope_note": "tested range and declared scaling model only",
        }
    payload = {
        "schema": "p1c-standoff-readout-v1",
        "manifest_hash": manifest["manifest_hash"],
        "code_commit": next(iter(commits)) if len(commits) == 1 else None,
        "current_code_commit": git_commit(),
        "decision": decision, "integrity": integrity, "missing": missing,
        "per_arm": {f"k{k}_{a}_{arm}": {kk: pl[kk] for kk in
                    ("counts", "mean_steps")}
                    for (k, a, arm), pl in sorted(arms.items())},
        "hold_mean_steps_by_scale": hold_steps,
        "classification": classification,
        "scope": manifest["scope"], "promotion": manifest["promotion"],
    }
    (OUT / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("decision", "integrity",
                                              "classification")},
                     indent=2, ensure_ascii=False))
    return payload


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--readout", action="store_true")
    ap.add_argument("--shard", default=None)
    a = ap.parse_args(argv)
    if a.readout:
        readout()
    else:
        run(shard=a.shard, smoke=a.smoke)


if __name__ == "__main__":
    main()
