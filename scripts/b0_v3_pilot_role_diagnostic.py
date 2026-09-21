"""Post-hoc role swap on the sealed B0 v3 pilot evaluation scenarios.

This lives outside ``shepherd`` so the pilot's sealed execution-code tree and
BC dataset provenance remain unchanged. It diagnoses a failed pilot; it does
not reopen candidate selection or create a new training result.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

import torch

from shepherd.m4_env import build_m4_env
from shepherd.provenance import git_commit, git_dirty
from shepherd.scripts.b0_v3_mappo_pilot import (
    OUT, PilotRunner, boundary_cells, scenario_kwargs,
)
from shepherd.scripts.b0_v3_pilot_manifest import load as load_manifest
from shepherd.scripts.b2_manifest import load as load_b2_manifest
from shepherd.scripts.mission_rollout import partition_bin, run_episode
from shepherd.train.b0_v3_credit import B0V3CreditEnv

ROOT = Path(__file__).resolve().parents[1]
MODES = (
    "scripted_both",
    "learned_limiter_scripted_finisher",
    "scripted_limiter_learned_finisher",
    "scripted_limiter_mean_axis",
)


def _shepherd_tree() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD:shepherd"], cwd=ROOT,
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def _summary(records: list[dict]) -> dict:
    counts = Counter(r["bin"] for r in records)
    n = len(records)
    return {
        "n": n,
        "counts": dict(sorted(counts.items())),
        "p_N": counts["N"] / n,
        "p_H_illegal": counts["H_illegal"] / n,
        "p_FIRE": sum(r["fire"] for r in records) / n,
        "episodes_with_clean_crossing": sum(r.get("clean_crossings", 0) > 0
                                             for r in records)
        if all("clean_crossings" in r for r in records) else None,
        "records": records,
    }


def _mean_axis_policy(runner: PilotRunner):
    """Keep stochastic fire and limiter samples; replace only the aim axis."""
    stochastic = runner.policy_fn(deterministic=False)
    mean = runner.policy_fn(deterministic=True)

    def policy(obs, flags):
        acts = stochastic(obs, flags)
        mean_acts = mean(obs, flags)
        fid = runner._adapter.finisher_id
        acts[fid] = acts[fid].copy()
        acts[fid][:3] = mean_acts[fid][:3]
        return acts

    return policy


def _cached_learned_both(summary: dict, cells: list, n_pc: int,
                         sealed_n_pc: int) -> dict:
    expected = {(c["cell_id"], ci * sealed_n_pc + j)
                for ci, c in enumerate(cells) for j in range(n_pc)}
    records = [r for r in summary["evaluation"]["records"]
               if (r["cell_id"], r["scenario_id"]) in expected]
    actual = {(r["cell_id"], r["scenario_id"]) for r in records}
    if actual != expected or len(records) != len(expected):
        raise ValueError("saved learned-both evaluation does not cover the diagnostic scenarios")
    return _summary(records)


def evaluate_mode(runner: PilotRunner, manifest: dict, b2: dict, mode: str,
                  *, cells: list, episodes_per_cell: int) -> dict:
    if mode not in MODES:
        raise ValueError(f"unknown role-swap mode: {mode}")
    learned = runner.policy_fn(deterministic=False)
    policies = {
        "scripted_both": (None, ()),
        "learned_limiter_scripted_finisher": (learned, ("finisher",)),
        "scripted_limiter_learned_finisher": (learned, ("limiter",)),
        "scripted_limiter_mean_axis": (_mean_axis_policy(runner), ("limiter",)),
    }
    policy, scripted_roles = policies[mode]
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    ev = manifest["evaluation"]
    sealed_n_pc = int(ev["episodes_per_cell"])
    rows = []
    for ci, cell in enumerate(cells):
        for j in range(episodes_per_cell):
            sid = ci * sealed_n_pc + j  # exact subset of the sealed 280 cases
            chi, eta, kw = scenario_kwargs(
                b2, cell, sid, seed0=ev["seed0"], seed_ns=ev["seed_ns"])
            stack = build_m4_env(ev["seed0"], sid, **kw)
            env = B0V3CreditEnv(stack.env, runner.credit_spec)
            torch.manual_seed(int(ev["seed0"]) + sid)
            result = run_episode(
                env, stack.scn, stack.lay, seed=int(ev["seed0"]) + sid,
                policy=policy, scripted_roles=scripted_roles,
                limiter_mode="arc", limiter_kw=c5, fire_mode="clean")
            rows.append({
                "cell_id": cell["cell_id"], "scenario_id": sid,
                "chi": chi, "eta": eta, "bin": partition_bin(result),
                "fire": result.fire_step is not None,
                "clean_crossings": result.clean_crossings,
                "steps": result.steps,
            })
        if (ci + 1) % 7 == 0:
            print(f"{mode}: {ci + 1}/{len(cells)} cells", flush=True)
    return _summary(rows)


def diagnose(candidate: str, seed: int, device: str, *, episodes_per_cell: int = 10,
             out: Path | None = None) -> dict:
    manifest, b2 = load_manifest(), load_b2_manifest()
    if candidate not in manifest["candidates"] or seed not in manifest["training"]["seeds"]:
        raise ValueError("candidate/seed is outside the sealed pilot")
    sealed_n_pc = int(manifest["evaluation"]["episodes_per_cell"])
    if not 1 <= episodes_per_cell <= sealed_n_pc:
        raise ValueError(f"episodes_per_cell must be in [1, {sealed_n_pc}]")
    target = out or OUT / f"role_swap_{candidate}_seed{seed}_e{episodes_per_cell}.json"
    if target.exists():
        raise FileExistsError(f"diagnostic output exists: {target}")
    dirty = git_dirty(("shepherd", "scripts/b0_v3_pilot_role_diagnostic.py"))
    if dirty:
        raise RuntimeError(f"diagnostic execution code is dirty: {dirty}")
    bc_meta = json.loads((OUT / "bc_dataset.json").read_text(encoding="utf-8"))
    if _shepherd_tree() != bc_meta["code_tree"]:
        raise RuntimeError("shepherd execution-code tree differs from sealed BC producer")
    readout = json.loads((OUT / "readout.json").read_text(encoding="utf-8"))
    if (readout["manifest_hash"] != manifest["manifest_hash"]
            or not readout["completion"]["pass"]
            or readout["decision"] != "NO_SELECTION"):
        raise RuntimeError("this post-hoc diagnostic requires the completed NO_SELECTION pilot")
    run_dir = OUT / candidate / f"seed{seed}"
    saved = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    marker = json.loads((run_dir / ".done").read_text(encoding="utf-8"))
    if (saved["manifest_hash"] != manifest["manifest_hash"]
            or saved["candidate"] != candidate or saved["seed"] != seed
            or saved["status"] != "PASS"
            or saved["bc_dataset_hash"] != bc_meta["dataset_hash"]
            or marker["code_commit"] != saved["code_commit"]):
        raise RuntimeError("saved pilot run lineage mismatch")

    runner = PilotRunner(manifest, b2, candidate, seed, device)
    restored = runner.restore(run_dir)
    if restored != manifest["training"]["total_env_steps"]:
        raise RuntimeError(f"checkpoint step mismatch: {restored}")
    checkpoint_sha256 = hashlib.sha256(
        (run_dir / "ckpt_mappo_latest.pt").read_bytes()).hexdigest()
    cells = boundary_cells(b2)
    results = {}
    for mode in MODES:
        results[mode] = evaluate_mode(runner, manifest, b2, mode,
                                      cells=cells, episodes_per_cell=episodes_per_cell)
        print(f"{mode}: N={results[mode]['p_N']:.3f} "
              f"FIRE={results[mode]['p_FIRE']:.3f} "
              f"H={results[mode]['p_H_illegal']:.3f}", flush=True)
    results["learned_both_saved"] = _cached_learned_both(
        saved, cells, episodes_per_cell, sealed_n_pc)

    report = {
        "schema": "b0-v3-pilot-role-swap-posthoc-v1",
        "scope": "post-hoc mechanism diagnostic; does not amend NO_SELECTION",
        "manifest_hash": manifest["manifest_hash"],
        "b0_v3_hash": b2["b0_v3_hash"],
        "candidate": candidate, "seed": seed,
        "training_code_commit": saved["code_commit"],
        "evaluator_commit": git_commit(),
        "shepherd_code_tree": _shepherd_tree(),
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_steps": restored,
        "episodes_per_cell": episodes_per_cell,
        "scenario_rule": "first j episodes per cell from sealed evaluation; sid=ci*10+j",
        "learned_both_source": "sealed pilot summary.json, no rerun",
        "modes": results,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved: {target}", flush=True)
    return report


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", default="c0_base")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", default="cuda")
    p.add_argument("--episodes-per-cell", type=int, default=10)
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    diagnose(a.candidate, a.seed, a.device,
             episodes_per_cell=a.episodes_per_cell, out=a.out)


if __name__ == "__main__":
    main()
