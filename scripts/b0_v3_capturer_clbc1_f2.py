"""CLBC1-F2: lower only capturer aim variance and evaluate on fresh pairs.

The sealed CLBC1 parent is reconstructed exactly.  This stage performs no new
gradient update and never overrides FIRE.

    python -m scripts.b0_v3_capturer_clbc1_f2 --smoke --device cpu
    python -u -m scripts.b0_v3_capturer_clbc1_f2 --run --seed 0 --device cuda
    python -u -m scripts.b0_v3_capturer_clbc1_f2 --run --seed 1 --device cuda
    python -m scripts.b0_v3_capturer_clbc1_f2 --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import numpy as np

from scripts.b0_v3_capturer_clbc1 import (
    _angle_deg, _episode_stats, _trace_policy, dataset_hash, pair_keys,
    scenario_plan, signature, summarize_records, train_aim,
)
from scripts.b0_v3_capturer_clbc1_f2_manifest import ARMS, load as load_manifest
from scripts.b0_v3_capturer_f1 import F1, component_hashes, reconstruct, require_cublas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1_f2"
CLBC1_OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1"
EXEC_PATHS = (
    "shepherd",
    "scripts/b0_v3_capturer_clbc1_f2.py",
    "scripts/b0_v3_capturer_clbc1_f2_manifest.py",
    "scripts/b0_v3_capturer_clbc1.py",
    "scripts/b0_v3_capturer_f1.py",
    "scripts/b0_v3_capturer_diagnostic.py",
    "artifacts/marl/b0_v3_capturer_clbc1_f2/manifest.json",
)
CONTROL, F2 = ARMS
PASS = "PASS_TO_CAPTURER_ONLY_RL_CONTRACT"
STOP = "STOP_F2"
INVALID = "INVALID_F2"


def _finite_median(values) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.median(vals)) if vals else None


def summarize(records: list[dict]) -> dict:
    out = summarize_records(records)
    events = [r["accepted_fire_judge"] for r in records
              if r.get("accepted_fire_judge") is not None]
    out.update({
        "SPENT_FAIL": sum(r["outcome"] == "SPENT_FAIL" for r in records),
        "accepted_FIRE": len(events),
        "robust_ready_FIRE": sum(bool(e["robust_ready"]) for e in events),
        "FIRE_to_N": out["N"] / len(events) if events else None,
        "accepted_fire_v_soft_median": _finite_median(e["v_shot_soft"] for e in events),
        "accepted_fire_attitude_deg_median": _finite_median(
            e["ang_att_teacher_deg"] for e in events),
    })
    return out


def apply_gate(per_seed: dict, integrity: dict, seeds=(0, 1)) -> dict:
    if not all(bool(v) for v in integrity.values()):
        return {"decision": INVALID, "clauses": {}, "integrity": integrity}
    clauses = {}
    for seed in seeds:
        control, f2 = per_seed[seed][CONTROL], per_seed[seed][F2]
        clauses[f"seed{seed}_sample_angle_decrease"] = (
            f2["sampled_to_mean_deg_median"] < control["sampled_to_mean_deg_median"])
        clauses[f"seed{seed}_robust_ready_FIRE_increase"] = (
            f2["robust_ready_FIRE"] > control["robust_ready_FIRE"])
        clauses[f"seed{seed}_N_increase"] = f2["N"] > control["N"]
        clauses[f"seed{seed}_SPENT_FAIL_not_increase"] = (
            f2["SPENT_FAIL"] <= control["SPENT_FAIL"])
        clauses[f"seed{seed}_crossing_not_decrease"] = (
            f2["clean_crossing_episodes"] >= control["clean_crossing_episodes"])
    pooled_h = {arm: sum(per_seed[s][arm]["H_illegal"] for s in seeds)
                for arm in ARMS}
    clauses["both_arms_pooled_H_illegal_zero"] = all(v == 0 for v in pooled_h.values())
    return {"decision": PASS if all(clauses.values()) else STOP,
            "clauses": clauses, "pooled_H_illegal": pooled_h,
            "integrity": integrity}


def _prerequisites(manifest: dict, pilot: dict, b2: dict, clbc1: dict) -> dict:
    pre = manifest["prerequisites"]
    pilot_readout = json.loads(
        (ROOT / "artifacts/marl/b0_v3_pilot/readout.json").read_text(encoding="utf-8"))
    f1_readout = json.loads(
        (ROOT / "artifacts/marl/b0_v3_capturer_f1/readout.json").read_text(encoding="utf-8"))
    clbc1_readout = json.loads((ROOT / pre["clbc1_readout"]).read_text(encoding="utf-8"))
    checks = {
        "b0_v3": b2["b0_v3_hash"] == pre["b0_v3_hash"],
        "pilot_NO_SELECTION": pilot_readout.get("decision") == pre["pilot_decision_required"],
        "F1_STOP": f1_readout.get("decision") == pre["f1_decision_required"],
        "CLBC1_manifest": clbc1["manifest_hash"] == pre["clbc1_manifest_hash"],
        "CLBC1_STOP": clbc1_readout.get("decision") == pre["clbc1_decision_required"],
    }
    bad = [k for k, value in checks.items() if not value]
    if bad:
        raise SystemExit(f"CLBC1-F2 prerequisite failure: {bad}")
    return checks


def _load_collection(seed: int, manifest: dict) -> tuple[dict, dict]:
    run_dir = CLBC1_OUT / f"seed{seed}"
    receipt = json.loads((run_dir / "collection.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "collection.npz", allow_pickle=False) as z:
        arrays = {key: np.asarray(z[key]) for key in z.files}
    pre = manifest["prerequisites"]
    expected = pre["collection_hashes"][str(seed)]
    checks = {
        "manifest": receipt["manifest_hash"] == pre["clbc1_manifest_hash"],
        "seed": int(receipt["actor_seed"]) == seed,
        "source_commit": receipt["code_commit"] == pre["clbc1_source_code_commit"],
        "receipt_hash": receipt["dataset_hash"] == expected,
        "content_hash": dataset_hash(arrays) == expected,
    }
    if not all(checks.values()):
        raise SystemExit(f"sealed CLBC1 collection mismatch: {checks}")
    return arrays, {"checks": checks, **receipt}


def reconstruct_clbc1(seed: int, device: str, original: dict, pilot: dict,
                      b2: dict, clbc1: dict, manifest: dict, *, smoke: bool):
    runner, f1_bc = reconstruct(F1, seed, device, original, pilot, b2)
    collected, receipt = _load_collection(seed, manifest)
    stats = train_aim(runner, original, collected, clbc1, seed, "clbc1",
                      steps=4 if smoke else int(clbc1["training"]["steps"]))
    actual = component_hashes(runner)
    expected = manifest["prerequisites"]["clbc1_parent_state"][str(seed)]
    exact = actual == expected
    if not smoke and not exact:
        raise SystemExit(f"CLBC1 parent hash mismatch seed{seed}: {actual} != {expected}")
    return runner, {
        "f1_bc_metrics": f1_bc["metrics"],
        "collection_hash": receipt["dataset_hash"],
        "reconstruction": stats,
        "actual_state": actual,
        "expected_state": expected,
        "exact_parent": exact if not smoke else None,
        "smoke_short_reconstruction": bool(smoke),
    }


def set_arm(runner, arm: str, manifest: dict) -> dict:
    import torch
    before = component_hashes(runner)
    value = float(manifest["arms"][arm]["aim_log_std"])
    with torch.no_grad():
        runner.tr.fin_actor.log_std.fill_(value)
    after = component_hashes(runner)
    unchanged = (all(before[k] == after[k] for k in before
                     if k not in ("fin_log_std", "all"))
                 and (arm != CONTROL or before == after))
    return {"arm": arm, "aim_log_std": value, "before": before, "after": after,
            "only_log_std_changed": bool(unchanged),
            "log_std_values": runner.tr.fin_actor.log_std.detach().cpu().tolist()}


class FireAuditEnv:
    """Delegating wrapper that records the exact judge returned by env.step."""

    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.events: list[dict] = []
        self.t = 0

    def reset(self, *args, **kwargs):
        self.events = []
        self.t = 0
        return self.wrapped.reset(*args, **kwargs)

    def step(self, actions):
        from shepherd.train.bc_aim import teacher_axis
        _, fin, _ = self.wrapped._states()
        teacher = teacher_axis(self.wrapped)
        attitude = np.asarray(self.wrapped._e(fin), float)
        command = np.asarray(actions.get(self.wrapped.finisher_id, np.zeros(5)), float)
        phase = str(getattr(self.wrapped.fsm.state, "value", self.wrapped.fsm.state))
        result = self.wrapped.step(actions)
        info = result[4][self.wrapped.finisher_id]
        if info.get("fire_event"):
            boxed = bool(info["boxed_in"])
            worst = float(info["v_shot_worst"])
            self.events.append({
                "t": self.t, "net_phase_before": phase,
                "v_shot_soft": float(info["v_shot_soft"]),
                "v_shot_worst": worst,
                "p_feasible": float(info["p_feasible"]),
                "boxed_in": boxed,
                "robust_ready": bool((not boxed) and worst >= 1.0),
                "fire_command": float(command[4]) if command.size >= 5 else None,
                "ang_att_teacher_deg": _angle_deg(attitude, teacher),
                "ang_cmd_teacher_deg": _angle_deg(command[:3], teacher),
            })
        self.t += 1
        return result

    def __getattr__(self, name):
        return getattr(self.__dict__["wrapped"], name)


def evaluate(runner, manifest: dict, b2: dict, plan: list[dict], *, arm: str,
             seed: int, trace_dir: Path) -> list[dict]:
    import torch
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv

    spec = manifest["evaluation"]
    cells = {cell["cell_id"]: cell for cell in b2["cells"]}
    trace_keys = {tuple(x) for x in manifest["traces"]["scenarios"]}
    base, records = runner.policy_fn(deterministic=False), []
    for p in plan:
        sid = p["scenario_id"]
        chi, eta, kw = scenario_kwargs(b2, cells[p["cell_id"]], sid,
                                       seed0=spec["seed0"], seed_ns=spec["namespace"])
        if (chi, eta) != (p["chi"], p["eta"]):
            raise RuntimeError("evaluation scenario plan mismatch")
        stack = build_m4_env(spec["seed0"], sid, **kw)
        env = FireAuditEnv(B0V3CreditEnv(stack.env, runner.credit_spec))
        torch.manual_seed(p["torch_seed"])
        rows: list[dict] = []
        result = run_episode(
            env, stack.scn, stack.lay, seed=p["env_seed"],
            policy=_trace_policy(base, runner, env, rows),
            scripted_roles=("limiter",), limiter_mode="hold", fire_mode="clean")
        if len(env.events) > 1:
            raise RuntimeError("finite-magazine evaluation produced multiple FIRE events")
        event = env.events[0] if env.events else None
        if (result.fire_step is None) != (event is None):
            raise RuntimeError("run_episode FIRE and authoritative audit disagree")
        stats = _episode_stats(rows, result.fire_step)
        stats["policy_input_at_fire"] = stats.pop("at_fire")
        outcome_bin = partition_bin(result)
        rec = {
            **p, "bin": outcome_bin, "label": result.label,
            "outcome": result.outcome, "fire": event is not None,
            "fire_step": result.fire_step, "clean_crossings": result.clean_crossings,
            "H_illegal": outcome_bin == "H_illegal", "steps": result.steps,
            "accepted_fire_judge": event, **stats,
        }
        records.append(rec)
        if (p["cell_id"], sid) in trace_keys:
            extra = kw.get("extra_cfg", {})
            trace = {
                "schema": "b0-v3-capturer-clbc1-f2-trace-v1", "arm": arm,
                "actor_seed": seed, "cell_id": p["cell_id"], "scenario_id": sid,
                "chi": chi, "eta": eta,
                "cone_half_angle_rad": extra.get("viability.cone.half_angle"),
                "cone_range_max": extra.get("viability.cone.range_max"),
                "theta_fire": float(getattr(env, "theta_fire", 0.9)),
                "target": [float(x) for x in stack.lay.target],
                "accepted_fire_judge": event,
                "result": {"bin": outcome_bin, "label": result.label,
                           "outcome": result.outcome, "steps": result.steps,
                           "fire_step": result.fire_step,
                           "clean_crossings": result.clean_crossings,
                           "n_contact": result.n_contact},
                "steps": rows,
            }
            trace_dir.mkdir(parents=True, exist_ok=True)
            (trace_dir / f"trace_{arm}_seed{seed}_{p['cell_id']}_sid{sid}.json").write_text(
                json.dumps(trace, ensure_ascii=False), encoding="utf-8")
        if len(records) % 70 == 0:
            print(f"{arm}/s{seed}: {len(records)}/{len(plan)}", flush=True)
    return records


def run_seed(seed: int, device: str, *, smoke=False, out_root: Path = OUT) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import BC_FILE, load_bc
    from shepherd.scripts.b0_v3_pilot_manifest import load as load_pilot
    from shepherd.scripts.b2_manifest import load as load_b2
    from scripts.b0_v3_capturer_clbc1_manifest import load as load_clbc1

    manifest = load_manifest()
    cublas = require_cublas(device, manifest)
    if seed not in manifest["parent"]["actor_seeds"]:
        raise ValueError("seed outside sealed manifest")
    dirty = git_dirty(EXEC_PATHS)
    if dirty and not smoke:
        raise SystemExit(f"dirty execution code; run refused: {dirty}")
    run_dir = out_root / ("smoke" if smoke else "") / f"seed{seed}"
    if not smoke and (run_dir / ".done").exists():
        raise SystemExit(f"completed run exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    pilot, b2, clbc1 = load_pilot(), load_b2(), load_clbc1()
    prereq = _prerequisites(manifest, pilot, b2, clbc1)
    original, bc_meta = load_bc(BC_FILE, pilot)

    runners, parents, interventions = {}, {}, {}
    for arm in ARMS:
        runner, parent = reconstruct_clbc1(
            seed, device, original, pilot, b2, clbc1, manifest, smoke=smoke)
        runners[arm], parents[arm] = runner, parent
        interventions[arm] = set_arm(runner, arm, manifest)

    parent_equal = parents[CONTROL]["actual_state"] == parents[F2]["actual_state"]
    fixed_keys = ("lim_actor", "fin_mean", "fin_fire_logit", "critic", "obs_norm")
    single_factor = (
        parent_equal
        and all(interventions[a]["only_log_std_changed"] for a in ARMS)
        and all(interventions[CONTROL]["after"][k] == interventions[F2]["after"][k]
                for k in fixed_keys)
        and interventions[CONTROL]["after"]["fin_log_std"]
            != interventions[F2]["after"]["fin_log_std"]
        and interventions[CONTROL]["log_std_values"] == [-1.0, -1.0, -1.0]
        and all(abs(x + 2.3) < 1e-6 for x in interventions[F2]["log_std_values"])
    )
    if not single_factor:
        raise SystemExit("CLBC1-F2 single-factor identity failed")

    plan = scenario_plan(manifest["evaluation"], b2, seed,
                         n_cells=2 if smoke else None,
                         episodes_per_cell=1 if smoke else None)
    evaluations = {}
    for arm in ARMS:
        path = run_dir / f"evaluation_{arm}.json"
        if not smoke and path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (payload["manifest_hash"] != manifest["manifest_hash"]
                    or payload["actor_seed"] != seed or payload["arm"] != arm
                    or payload["code_commit"] != git_commit()):
                raise SystemExit(f"evaluation checkpoint lineage mismatch for {arm}")
            records = payload["records"]
        else:
            records = evaluate(runners[arm], manifest, b2, plan, arm=arm, seed=seed,
                               trace_dir=run_dir / "traces")
            path.write_text(json.dumps({"manifest_hash": manifest["manifest_hash"],
                                        "code_commit": git_commit(),
                                        "actor_seed": seed, "arm": arm,
                                        "records": records}, ensure_ascii=False),
                            encoding="utf-8")
        if pair_keys(records) != pair_keys(plan):
            raise SystemExit(f"pairing mismatch for {arm}")
        evaluations[arm] = {**summarize(records), "records": records}

    fire_audit = all(
        (bool(r["fire"]) == (r["accepted_fire_judge"] is not None)
         and (r["accepted_fire_judge"] is None
              or r["accepted_fire_judge"]["net_phase_before"] == "LOADED"))
        for arm in ARMS for r in evaluations[arm]["records"])
    finite = all(
        math.isfinite(float(r[key]))
        for arm in ARMS for r in evaluations[arm]["records"]
        for key in ("mu_norm_mean", "ang_mean_teacher_deg_mean",
                    "ang_cmd_mean_deg_mean", "ang_att_teacher_deg_mean"))
    exact_parent = all(parents[a]["exact_parent"] is True for a in ARMS)
    summary = {
        "schema": "b0-v3-capturer-clbc1-f2-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS", "scope": manifest["scope"], "actor_seed": seed,
        "provenance": {"manifest_hash": manifest["manifest_hash"],
                       "b0_v3_hash": b2["b0_v3_hash"],
                       "bc_dataset_hash": bc_meta["dataset_hash"],
                       "code_commit": git_commit(), "code_dirty_scoped": dirty,
                       "cublas_workspace_config": cublas, "device": device,
                       "rl_updates": 0},
        "prerequisites": prereq, "parents": parents,
        "interventions": interventions,
        "identity": {"common_parent": parent_equal,
                     "exact_sealed_parent": bool(exact_parent),
                     "single_factor": bool(single_factor)},
        "scenario_signature": {"plan": signature(plan),
                               **{a: signature(evaluations[a]["records"])
                                  for a in ARMS}},
        "evaluation": evaluations,
        "authoritative_fire_logging": bool(fire_audit),
        "finite": bool(finite), "elapsed_s": round(time.time() - t0, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if not smoke:
        (run_dir / ".done").write_text(json.dumps(
            {"manifest_hash": manifest["manifest_hash"],
             "code_commit": summary["provenance"]["code_commit"]}), encoding="utf-8")
    for arm in ARMS:
        block = evaluations[arm]
        print(f"{arm}/s{seed}: N={block['N']} robust={block['robust_ready_FIRE']} "
              f"FIRE={block['FIRE_episodes']} spent={block['SPENT_FAIL']} "
              f"cross={block['clean_crossing_episodes']}", flush=True)
    return summary


def readout(out_root: Path = OUT) -> dict:
    from shepherd.provenance import git_commit
    from shepherd.scripts.b2_manifest import load as load_b2

    manifest, b2 = load_manifest(), load_b2()
    seeds = tuple(manifest["parent"]["actor_seeds"])
    missing = [s for s in seeds if not ((out_root / f"seed{s}" / ".done").exists()
                                        and (out_root / f"seed{s}" / "summary.json").exists())]
    if missing:
        out = {"schema": "b0-v3-capturer-clbc1-f2-readout-v1",
               "status": "INCOMPLETE", "manifest_hash": manifest["manifest_hash"],
               "missing_seeds": missing, "decision": None}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return out

    runs = {s: json.loads((out_root / f"seed{s}" / "summary.json")
                          .read_text(encoding="utf-8")) for s in seeds}
    commits = {r["provenance"]["code_commit"] for r in runs.values()}
    lineage = len(commits) == 1
    pairing = finite = completion = exact_parent = single_factor = fire_audit = budget = True
    per_seed = {}
    for seed, run in runs.items():
        p = run["provenance"]
        lineage &= (run["schema"] == "b0-v3-capturer-clbc1-f2-run-v1"
                    and run["status"] == "PASS" and run["actor_seed"] == seed
                    and p["manifest_hash"] == manifest["manifest_hash"]
                    and p["b0_v3_hash"] == manifest["prerequisites"]["b0_v3_hash"]
                    and not p["code_dirty_scoped"] and p["rl_updates"] == 0
                    and (not str(p["device"]).startswith("cuda")
                         or p["cublas_workspace_config"]
                         in manifest["runtime"]["cublas_workspace_config"]))
        expected = pair_keys(scenario_plan(manifest["evaluation"], b2, seed))
        blocks = {}
        for arm in ARMS:
            records = run["evaluation"][arm]["records"]
            pairing &= pair_keys(records) == expected
            completion &= len(records) == manifest["evaluation"]["episodes_per_arm_per_seed"]
            blocks[arm] = summarize(records)
        exact_parent &= bool(run["identity"]["exact_sealed_parent"])
        single_factor &= bool(run["identity"]["common_parent"]
                              and run["identity"]["single_factor"])
        fire_audit &= bool(run["authoritative_fire_logging"])
        finite &= bool(run["finite"])
        per_seed[seed] = blocks
    budget &= sum(per_seed[s][a]["n"] for s in seeds for a in ARMS) \
        == manifest["evaluation"]["episodes_total"]
    integrity = {"lineage": bool(lineage), "pairing": bool(pairing),
                 "finite": bool(finite), "completion": bool(completion),
                 "exact_parent": bool(exact_parent),
                 "single_factor": bool(single_factor),
                 "authoritative_fire_logging": bool(fire_audit),
                 "budget": bool(budget)}
    gate = apply_gate(per_seed, integrity, seeds)
    out = {"schema": "b0-v3-capturer-clbc1-f2-readout-v1",
           "status": "COMPLETE", "manifest_hash": manifest["manifest_hash"],
           "scope": manifest["scope"], "integrity": integrity,
           "per_seed": per_seed, "gate": gate, "decision": gate["decision"],
           "code_commit": next(iter(commits)) if len(commits) == 1 else sorted(commits),
           "readout_code_commit": git_commit()}
    (out_root / "readout.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return out


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--readout", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)
    if args.readout:
        readout()
    else:
        run_seed(args.seed, args.device, smoke=args.smoke)


if __name__ == "__main__":
    main()
