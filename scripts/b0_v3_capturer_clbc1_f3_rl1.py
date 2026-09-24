"""Run the sealed small F3 capturer aim-only PPO experiment.

    python -m scripts.b0_v3_capturer_clbc1_f3_rl1 --smoke --device cpu
    python -u -m scripts.b0_v3_capturer_clbc1_f3_rl1 --run --seed 0 --device cuda
    python -u -m scripts.b0_v3_capturer_clbc1_f3_rl1 --run --seed 1 --device cuda
    python -m scripts.b0_v3_capturer_clbc1_f3_rl1 --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from scripts.b0_v3_capturer_clbc1 import (
    _episode_stats, _trace_policy, dataset_hash, pair_keys, scenario_plan, signature,
)
from scripts.b0_v3_capturer_clbc1_f2 import F2, FireAuditEnv, reconstruct_clbc1, set_arm
from scripts.b0_v3_capturer_clbc1_f3 import summarize_f3, train_fire_head
from scripts.b0_v3_capturer_clbc1_f3_rl1_manifest import ARMS, load as load_manifest
from scripts.b0_v3_capturer_f1 import component_hashes, require_cublas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1_f3_rl1"
F3_OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1_f3"
CONTROL, RL1 = ARMS
PASS, STOP, INVALID = "PASS_RL1_MECHANISM_ONLY", "STOP_RL1", "INVALID_RL1"
EXEC_PATHS = (
    "shepherd",
    "scripts/b0_v3_capturer_clbc1_f3_rl1.py",
    "scripts/b0_v3_capturer_clbc1_f3_rl1_manifest.py",
    "scripts/b0_v3_capturer_clbc1_f3.py",
    "scripts/b0_v3_capturer_clbc1_f2.py",
    "scripts/b0_v3_capturer_clbc1.py",
    "scripts/b0_v3_capturer_f1.py",
    "artifacts/marl/b0_v3_capturer_clbc1_f3_rl1/manifest.json",
)


class FrozenNorm:
    """Read-only view of a RunningNorm with the same serialized state."""

    def __init__(self, base):
        self.base = base

    def normalize(self, x, update: bool = False):
        return self.base.normalize(x, update=False)

    def state_dict(self):
        return self.base.state_dict()

    def load_state_dict(self, state):
        return self.base.load_state_dict(state)


def _json_hash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _value_norm_hash(runner) -> str | None:
    vn = runner.tr.value_norm
    return None if vn is None else _json_hash(vn.state_dict())


def _load_f3_collection(manifest: dict, seed: int) -> tuple[dict, dict]:
    pre = manifest["prerequisites"]
    run_dir = F3_OUT / f"seed{seed}"
    receipt = json.loads((run_dir / "collection.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "collection.npz", allow_pickle=False) as z:
        arrays = {k: np.asarray(z[k]) for k in z.files}
    checks = {
        "manifest": receipt["manifest_hash"] == pre["f3_manifest_hash"],
        "source_commit": receipt["code_commit"] == pre["f3_source_code_commit"],
        "seed": int(receipt["actor_seed"]) == int(seed),
        "receipt_hash": receipt["dataset_hash"] == pre["f3_collection_hashes"][str(seed)],
        "content_hash": dataset_hash(arrays) == pre["f3_collection_hashes"][str(seed)],
    }
    if not all(checks.values()):
        raise SystemExit(f"sealed F3 collection mismatch: {checks}")
    return arrays, {"checks": checks, **receipt}


def _prerequisites(manifest: dict) -> dict:
    pre = manifest["prerequisites"]
    f3_manifest = json.loads((ROOT / pre["f3_manifest"]).read_text(encoding="utf-8"))
    readout = json.loads((ROOT / pre["f3_readout"]).read_text(encoding="utf-8"))
    summaries = [json.loads((F3_OUT / f"seed{s}" / "summary.json").read_text(
        encoding="utf-8")) for s in manifest["training"]["actor_seeds"]]
    checks = {
        "F3_manifest": f3_manifest.get("manifest_hash") == pre["f3_manifest_hash"],
        "F3_PASS": readout.get("decision") == pre["f3_decision_required"],
        "F3_source": readout.get("code_commit") == pre["f3_source_code_commit"],
        "b0_v3": all(s["provenance"].get("b0_v3_hash") == pre["b0_v3_hash"]
                     for s in summaries),
        "F3_summary_source": all(s["provenance"].get("code_commit")
                                 == pre["f3_source_code_commit"] for s in summaries),
    }
    if not all(checks.values()):
        raise SystemExit(f"RL1 prerequisite failure: {checks}")
    return checks


def reconstruct_f3(seed: int, device: str, manifest: dict, *, smoke: bool = False):
    from shepherd.scripts.b0_v3_mappo_pilot import BC_FILE, load_bc
    from shepherd.scripts.b0_v3_pilot_manifest import load as load_pilot
    from shepherd.scripts.b2_manifest import load as load_b2
    from scripts.b0_v3_capturer_clbc1_manifest import load as load_clbc1
    from scripts.b0_v3_capturer_clbc1_f2_manifest import load as load_f2
    from scripts.b0_v3_capturer_clbc1_f3_manifest import load as load_f3

    pilot, b2, clbc1, f2, f3 = load_pilot(), load_b2(), load_clbc1(), load_f2(), load_f3()
    original, bc_meta = load_bc(BC_FILE, pilot)
    runner, lineage = reconstruct_clbc1(seed, device, original, pilot, b2, clbc1,
                                        f2, smoke=smoke)
    f2_intervention = set_arm(runner, F2, f2)
    collection, receipt = _load_f3_collection(manifest, seed)
    fire_training = train_fire_head(runner, collection, f3, seed, smoke=smoke)
    actual = component_hashes(runner)
    expected = manifest["prerequisites"]["f3_parent_state"][str(seed)]
    exact = actual == expected
    if not smoke and not exact:
        raise SystemExit(f"exact F3 parent mismatch seed{seed}: {actual} != {expected}")
    meta = {"bc_dataset_hash": bc_meta["dataset_hash"], "clbc1": lineage,
            "f2_intervention": f2_intervention, "f3_collection": receipt,
            "f3_training": fire_training, "actual_state": actual,
            "expected_state": expected, "exact_parent": exact if not smoke else None,
            "smoke_short_reconstruction": bool(smoke)}
    return runner, b2, meta


def _configure_rl1(runner, manifest: dict, seed: int, *, smoke: bool) -> dict:
    import torch
    from shepherd.train.mappo import MAPPORollout

    tr = manifest["training"]
    total = 128 if smoke else int(tr["total_env_steps"])
    rollout = 128 if smoke else int(tr["rollout_env_steps"])
    hp = tr["hyperparameters"]

    runner.pilot_manifest = copy.deepcopy(runner.pilot_manifest)
    runner.pilot_manifest["training"]["seed0"] = int(tr["seed0"])
    runner.pilot_manifest["training"]["seed_ns"] = tr["namespace"]
    runner.frozen_roles = ("limiter",)
    runner.limiter_policy = "hold"
    runner.limiter_mode = "hold"
    runner.tr.cfg.freeze_limiter = True
    runner.tr.cfg.freeze_finisher = False
    runner.tr.cfg.total_timesteps = total
    runner.tr.cfg.rollout_steps = rollout
    runner.tr.cfg.lr = float(hp["lr"])
    runner.tr.cfg.ent_coef_finisher = float(hp["ent_coef_finisher"])
    runner.rollout_env_steps = rollout
    runner.buf = MAPPORollout(rollout, runner.obs_dim, runner.n,
                              lim_dim=runner.tr.lim_dim)

    for p in runner.tr.lim_actor.parameters():
        p.requires_grad_(False)
    for p in runner.tr.fin_actor.fire_logit.parameters():
        p.requires_grad_(False)
    runner.tr.fin_actor.log_std.requires_grad_(False)
    for p in runner.tr.fin_actor.mean.parameters():
        p.requires_grad_(True)
    for p in runner.tr.critic.parameters():
        p.requires_grad_(True)
    trainable = list(runner.tr.fin_actor.mean.parameters()) + list(runner.tr.critic.parameters())
    runner.tr.optimizer = torch.optim.Adam(trainable, lr=float(hp["lr"]))
    runner.tr._rng = np.random.default_rng(int(tr["seed0"]) + int(seed))
    runner.norm = FrozenNorm(runner.norm)
    runner.base_seed = int(tr["seed0"]) + 1_000_000 * int(seed)
    runner.env_steps = 0
    runner._ep_idx = 0
    runner._adapter = None
    runner._obs = None
    runner.ep_records = []
    runner.cell_counts.clear()
    runner.credit_outcomes.clear()
    contract = {"schema": manifest["schema"], "manifest_hash": manifest["manifest_hash"],
                "b0_v3_hash": manifest["prerequisites"]["b0_v3_hash"],
                "actor_seed": int(seed)}
    runner.contract = {**contract, "hash": _json_hash(contract)}

    names = {id(p): n for n, p in (
        [(f"fin_actor.mean.{n}", p) for n, p in runner.tr.fin_actor.mean.named_parameters()]
        + [(f"critic.{n}", p) for n, p in runner.tr.critic.named_parameters()]
    )}
    optimizer_names = sorted(names[id(p)] for g in runner.tr.optimizer.param_groups
                             for p in g["params"])
    expected_names = sorted(names.values())
    return {"optimizer_names": optimizer_names, "expected_names": expected_names,
            "optimizer_exact": optimizer_names == expected_names,
            "total_env_steps": total, "rollout_env_steps": rollout,
            "updates": total // rollout}


def _evaluate(runner, manifest: dict, b2: dict, plan: list[dict], *, arm: str,
              seed: int, trace_dir: Path) -> list[dict]:
    import torch
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv

    spec = manifest["evaluation"]
    cells = {cell["cell_id"]: cell for cell in b2["cells"]}
    trace_keys = {tuple(x) for x in manifest["traces"]["scenarios"]}
    policy, records = runner.policy_fn(deterministic=False), []
    for p in plan:
        sid = p["scenario_id"]
        chi, eta, kw = scenario_kwargs(b2, cells[p["cell_id"]], sid,
                                       seed0=spec["seed0"], seed_ns=spec["namespace"])
        if (chi, eta) != (p["chi"], p["eta"]):
            raise RuntimeError("RL1 evaluation scenario plan mismatch")
        stack = build_m4_env(spec["seed0"], sid, **kw)
        env = FireAuditEnv(B0V3CreditEnv(stack.env, runner.credit_spec))
        torch.manual_seed(p["torch_seed"])
        rows: list[dict] = []
        result = run_episode(env, stack.scn, stack.lay, seed=p["env_seed"],
                             policy=_trace_policy(policy, runner, env, rows),
                             scripted_roles=("limiter",), limiter_mode="hold",
                             fire_mode="clean")
        if len(env.events) > 1:
            raise RuntimeError("finite-magazine evaluation produced multiple FIRE events")
        event = env.events[0] if env.events else None
        if (result.fire_step is None) != (event is None):
            raise RuntimeError("run_episode FIRE and authoritative audit disagree")
        stats = _episode_stats(rows, result.fire_step)
        stats["policy_input_at_fire"] = stats.pop("at_fire")
        outcome_bin = partition_bin(result)
        rec = {**p, "bin": outcome_bin, "label": result.label,
               "outcome": result.outcome, "fire": event is not None,
               "fire_step": result.fire_step, "clean_crossings": result.clean_crossings,
               "H_illegal": outcome_bin == "H_illegal", "steps": result.steps,
               "accepted_fire_judge": event, **stats}
        records.append(rec)
        if (p["cell_id"], sid) in trace_keys:
            extra = kw.get("extra_cfg", {})
            trace = {"schema": "b0-v3-capturer-clbc1-f3-rl1-trace-v1", "arm": arm,
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
                                "n_contact": result.n_contact}, "steps": rows}
            trace_dir.mkdir(parents=True, exist_ok=True)
            path = trace_dir / f"trace_{arm}_seed{seed}_{p['cell_id']}_sid{sid}.json"
            path.write_text(json.dumps(trace, ensure_ascii=False), encoding="utf-8")
        if len(records) % 70 == 0:
            print(f"{arm}/s{seed}: {len(records)}/{len(plan)}", flush=True)
    return records


def _save_progress(runner, path: Path, update: int) -> None:
    import torch
    payload = {
        "update": int(update), "env_steps": int(runner.env_steps),
        "episodes": int(runner._ep_idx),
        "fin_mean": runner.tr.fin_actor.mean.state_dict(),
        "critic": runner.tr.critic.state_dict(),
        "optimizer": runner.tr.optimizer.state_dict(),
        "value_norm": (None if runner.tr.value_norm is None
                       else runner.tr.value_norm.state_dict()),
        "minibatch_rng": runner.tr._rng.bit_generator.state,
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "cell_counts": dict(runner.cell_counts),
        "credit_outcomes": dict(runner.credit_outcomes),
    }
    torch.save(payload, path)


def _restore_progress(runner, path: Path) -> int:
    import torch
    payload = torch.load(path, map_location=runner.tr.device, weights_only=False)
    runner.tr.fin_actor.mean.load_state_dict(payload["fin_mean"])
    runner.tr.critic.load_state_dict(payload["critic"])
    runner.tr.optimizer.load_state_dict(payload["optimizer"])
    if runner.tr.value_norm is not None and payload["value_norm"] is not None:
        runner.tr.value_norm.load_state_dict(payload["value_norm"])
    runner.tr._rng.bit_generator.state = payload["minibatch_rng"]
    torch.set_rng_state(payload["torch_rng"].cpu())
    if runner.tr.device.type == "cuda" and payload["cuda_rng"] is not None:
        torch.cuda.set_rng_state_all([state.cpu() for state in payload["cuda_rng"]])
    runner.env_steps = int(payload["env_steps"])
    runner._ep_idx = int(payload["episodes"])
    runner.cell_counts.update(payload["cell_counts"])
    runner.credit_outcomes.update(payload["credit_outcomes"])
    runner._adapter = None
    runner._obs = None
    return int(payload["update"])


def apply_gate(per_seed: dict, integrity: dict, seeds=(0, 1)) -> dict:
    if not all(bool(v) for v in integrity.values()):
        return {"decision": INVALID, "clauses": {}, "integrity": integrity}

    def ge(a, b):
        return a is not None and b is not None and math.isfinite(float(a)) \
            and math.isfinite(float(b)) and float(a) >= float(b)

    clauses = {}
    for seed in seeds:
        control, rl1 = per_seed[seed][CONTROL], per_seed[seed][RL1]
        clauses[f"seed{seed}_N_increase"] = rl1["N"] > control["N"]
        clauses[f"seed{seed}_robust_FIRE_not_decrease"] = (
            rl1["robust_ready_FIRE"] >= control["robust_ready_FIRE"])
        clauses[f"seed{seed}_nonrobust_FIRE_not_increase"] = (
            rl1["nonrobust_FIRE"] <= control["nonrobust_FIRE"])
        clauses[f"seed{seed}_SPENT_FAIL_not_increase"] = (
            rl1["SPENT_FAIL"] <= control["SPENT_FAIL"])
        clauses[f"seed{seed}_FIRE_to_N_not_decrease"] = ge(
            rl1["FIRE_to_N"], control["FIRE_to_N"])
        clauses[f"seed{seed}_crossing_not_decrease"] = (
            rl1["clean_crossing_episodes"] >= control["clean_crossing_episodes"])
    pooled_h = {arm: sum(per_seed[s][arm]["H_illegal"] for s in seeds) for arm in ARMS}
    clauses["both_arms_pooled_H_illegal_zero"] = all(v == 0 for v in pooled_h.values())
    return {"decision": PASS if all(clauses.values()) else STOP, "clauses": clauses,
            "pooled_H_illegal": pooled_h, "integrity": integrity}


def run_seed(seed: int, device: str, *, smoke=False, resume=False,
             out_root: Path = OUT) -> dict:
    import torch
    from shepherd.provenance import git_commit, git_dirty

    manifest = load_manifest()
    cublas = require_cublas(device, manifest)
    if seed not in manifest["training"]["actor_seeds"]:
        raise ValueError("seed outside sealed RL1 manifest")
    dirty = git_dirty(EXEC_PATHS)
    if dirty and not smoke:
        raise SystemExit(f"dirty execution code; run refused: {dirty}")
    run_dir = out_root / ("smoke" if smoke else "") / f"seed{seed}"
    if not smoke and (run_dir / ".done").exists():
        raise SystemExit(f"completed RL1 run exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    progress_path = run_dir / "progress.pt"
    if not smoke and progress_path.exists() and not resume:
        raise SystemExit(f"partial RL1 run exists; use --resume: {run_dir}")
    t0 = time.time()

    prereq = _prerequisites(manifest)
    runner, b2, parent_meta = reconstruct_f3(seed, device, manifest, smoke=smoke)
    parent_state = component_hashes(runner)
    setup = _configure_rl1(runner, manifest, seed, smoke=smoke)
    setup["optimizer_exact"] = bool(setup["optimizer_exact"])
    setup["scripted_limiter"] = runner.frozen_roles == ("limiter",) \
        and bool(runner.tr.cfg.freeze_limiter)
    setup["fire_frozen"] = (not any(p.requires_grad
                                     for p in runner.tr.fin_actor.fire_logit.parameters()))
    setup["log_std_frozen"] = not runner.tr.fin_actor.log_std.requires_grad
    setup["obs_norm_frozen"] = isinstance(runner.norm, FrozenNorm)
    value_norm_before = _value_norm_hash(runner)

    plan = scenario_plan(manifest["evaluation"], b2, seed,
                         n_cells=2 if smoke else None,
                         episodes_per_cell=1 if smoke else None)
    evaluations, payloads = {}, {}
    control_path = run_dir / f"evaluation_{CONTROL}.json"
    if not smoke and control_path.exists():
        payloads[CONTROL] = json.loads(control_path.read_text(encoding="utf-8"))
        if (payloads[CONTROL]["manifest_hash"] != manifest["manifest_hash"]
                or payloads[CONTROL]["code_commit"] != git_commit()
                or payloads[CONTROL]["actor_seed"] != seed):
            raise SystemExit("RL1 control evaluation lineage mismatch")
        control_rows = payloads[CONTROL]["records"]
    else:
        control_rows = _evaluate(runner, manifest, b2, plan, arm=CONTROL, seed=seed,
                                 trace_dir=run_dir / "traces")
        payloads[CONTROL] = {"manifest_hash": manifest["manifest_hash"],
                             "code_commit": git_commit(), "actor_seed": seed,
                             "arm": CONTROL, "records": control_rows}
        control_path.write_text(json.dumps(payloads[CONTROL], ensure_ascii=False),
                                encoding="utf-8")
    evaluations[CONTROL] = summarize_f3(control_rows)
    # policy_fn lazily installs an evaluation adapter.  A training rollout uses
    # `_adapter is None` as its signal to create an episode and `_obs`; clear
    # the evaluation-only handle before the first rollout.
    runner._adapter = None
    runner._obs = None

    start_update = 0
    if resume:
        if not progress_path.exists():
            raise SystemExit(f"--resume requested but no progress checkpoint: {progress_path}")
        start_update = _restore_progress(runner, progress_path)
    else:
        torch.manual_seed(int(manifest["training"]["seed0"]) + int(seed))
        runner.tr._rng = np.random.default_rng(
            int(manifest["training"]["seed0"]) + int(seed))
    logs = []
    log_path = run_dir / "train_log.json"
    if resume and log_path.exists():
        logs = json.loads(log_path.read_text(encoding="utf-8"))
    total_updates = int(setup["updates"])
    for update in range(start_update, total_updates):
        floor = float(manifest["training"]["hyperparameters"]["lr_anneal_floor"])
        frac = update / max(total_updates - 1, 1)
        lr0 = float(manifest["training"]["hyperparameters"]["lr"])
        runner.tr.set_lr(lr0 * max(1.0 - frac, floor))
        runner.collect_rollout()
        stats = runner.update()
        if not all(math.isfinite(float(v)) for v in stats.values()):
            raise FloatingPointError(f"non-finite training stats at update {update}")
        logs.append({"update": update + 1, "env_steps": runner.env_steps,
                     "stats": {k: float(v) for k, v in stats.items()},
                     "rolling": runner.rolling()})
        every = 1 if smoke else int(manifest["training"]["checkpoint_every_updates"])
        if (update + 1) % every == 0 or update + 1 == total_updates:
            _save_progress(runner, progress_path, update + 1)
            log_path.write_text(json.dumps(logs, ensure_ascii=False), encoding="utf-8")
        print(f"rl1/s{seed}: update {update + 1}/{total_updates} "
              f"steps={runner.env_steps}", flush=True)

    after_state = component_hashes(runner)
    frozen = ("lim_actor", "fin_fire_logit", "fin_log_std", "obs_norm")
    frozen_exact = all(after_state[k] == parent_state[k] for k in frozen)
    trainable_changed = (after_state["fin_mean"] != parent_state["fin_mean"]
                         and after_state["critic"] != parent_state["critic"])
    if not frozen_exact:
        raise SystemExit(f"RL1 frozen component drift: {parent_state} -> {after_state}")
    if not trainable_changed:
        raise SystemExit("RL1 trainable components did not both change")

    treatment_rows = _evaluate(runner, manifest, b2, plan, arm=RL1, seed=seed,
                               trace_dir=run_dir / "traces")
    payloads[RL1] = {"manifest_hash": manifest["manifest_hash"],
                     "code_commit": git_commit(), "actor_seed": seed,
                     "arm": RL1, "records": treatment_rows}
    (run_dir / f"evaluation_{RL1}.json").write_text(
        json.dumps(payloads[RL1], ensure_ascii=False), encoding="utf-8")
    evaluations[RL1] = summarize_f3(treatment_rows)
    pairing = all(pair_keys(payloads[a]["records"]) == pair_keys(plan) for a in ARMS)
    fire_audit = all(bool(r["fire"]) == (r["accepted_fire_judge"] is not None)
                     for a in ARMS for r in payloads[a]["records"])
    finite = all(math.isfinite(float(r[k])) for a in ARMS for r in payloads[a]["records"]
                 for k in ("mu_norm_mean", "ang_mean_teacher_deg_mean",
                           "ang_cmd_mean_deg_mean", "ang_att_teacher_deg_mean"))
    runner.save(run_dir, "final")
    summary = {
        "schema": "b0-v3-capturer-clbc1-f3-rl1-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS", "scope": manifest["scope"], "actor_seed": seed,
        "provenance": {"manifest_hash": manifest["manifest_hash"],
                       "b0_v3_hash": manifest["prerequisites"]["b0_v3_hash"],
                       "code_commit": git_commit(), "code_dirty_scoped": dirty,
                       "cublas_workspace_config": cublas, "device": device,
                       "resumed_from_update": start_update},
        "prerequisites": prereq, "parent": parent_meta,
        "training": {"steps": runner.env_steps, "updates": total_updates,
                     "setup": setup, "credit_outcomes": dict(runner.credit_outcomes),
                     "cell_exposure": dict(runner.cell_counts),
                     "value_norm_before": value_norm_before,
                     "value_norm_after": _value_norm_hash(runner)},
        "identity": {"parent": parent_state, "after": after_state,
                     "exact_f3_parent": (None if smoke else
                                         parent_state == parent_meta["expected_state"]),
                     "frozen_exact": frozen_exact,
                     "trainable_changed": trainable_changed},
        "scenario_signature": {"plan": signature(plan),
                               **{a: signature(payloads[a]["records"]) for a in ARMS}},
        "evaluation": evaluations, "pairing": pairing,
        "authoritative_fire_logging": fire_audit, "finite": finite,
        "elapsed_s": round(time.time() - t0, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not smoke:
        (run_dir / ".done").write_text(json.dumps(
            {"manifest_hash": manifest["manifest_hash"],
             "code_commit": summary["provenance"]["code_commit"]}), encoding="utf-8")
    for arm in ARMS:
        block = evaluations[arm]
        print(f"{arm}/s{seed}: N={block['N']} FIRE={block['accepted_FIRE']} "
              f"robust={block['robust_ready_FIRE']} nonrobust={block['nonrobust_FIRE']} "
              f"spent={block['SPENT_FAIL']} cross={block['clean_crossing_episodes']}")
    return summary


def readout(out_root: Path = OUT) -> dict:
    from shepherd.provenance import git_commit
    manifest = load_manifest()
    seeds = manifest["training"]["actor_seeds"]
    runs = {s: json.loads((out_root / f"seed{s}" / "summary.json").read_text(
        encoding="utf-8")) for s in seeds}
    per_seed = {s: runs[s]["evaluation"] for s in seeds}
    commits = {runs[s]["provenance"]["code_commit"] for s in seeds}
    expected_n = int(manifest["evaluation"]["episodes_per_arm_per_seed"])
    integrity = {
        "lineage": (len(commits) == 1
                    and all(runs[s]["provenance"]["manifest_hash"]
                            == manifest["manifest_hash"] for s in seeds)
                    and all(not runs[s]["provenance"]["code_dirty_scoped"] for s in seeds)),
        "pairing": all(runs[s]["pairing"] and len(set(
            runs[s]["scenario_signature"].values())) == 1 for s in seeds),
        "finite": all(runs[s]["finite"] for s in seeds),
        "completion": all((out_root / f"seed{s}" / ".done").exists() for s in seeds),
        "exact_parent": all(runs[s]["identity"]["exact_f3_parent"] for s in seeds),
        "partial_optimizer": all(runs[s]["training"]["setup"]["optimizer_exact"]
                                 and runs[s]["training"]["setup"]["scripted_limiter"]
                                 and runs[s]["training"]["setup"]["fire_frozen"]
                                 and runs[s]["training"]["setup"]["log_std_frozen"]
                                 and runs[s]["training"]["setup"]["obs_norm_frozen"]
                                 for s in seeds),
        "frozen_identity": all(runs[s]["identity"]["frozen_exact"]
                               and runs[s]["identity"]["trainable_changed"] for s in seeds),
        "authoritative_fire_logging": all(runs[s]["authoritative_fire_logging"]
                                          for s in seeds),
        "budget": all(runs[s]["training"]["steps"] == manifest["training"]["total_env_steps"]
                      and all(runs[s]["evaluation"][a]["n"] == expected_n for a in ARMS)
                      for s in seeds),
    }
    gate = apply_gate(per_seed, integrity, seeds=seeds)
    payload = {"schema": "b0-v3-capturer-clbc1-f3-rl1-readout-v1",
               "manifest_hash": manifest["manifest_hash"],
               "code_commit": next(iter(commits)) if len(commits) == 1 else None,
               "current_code_commit": git_commit(), "decision": gate["decision"],
               "gate": gate, "per_seed": {str(s): per_seed[s] for s in seeds},
               "scope": manifest["scope"], "promotion": manifest["promotion"]}
    (out_root / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return payload


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--readout", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.readout:
        readout()
    else:
        run_seed(args.seed, args.device, smoke=args.smoke, resume=args.resume)


if __name__ == "__main__":
    main()
