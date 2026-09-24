"""CLBC1-F3: robust-ready BC for the Bernoulli FIRE head only.

    python -m scripts.b0_v3_capturer_clbc1_f3 --smoke --device cpu
    python -u -m scripts.b0_v3_capturer_clbc1_f3 --run --seed 0 --device cuda
    python -u -m scripts.b0_v3_capturer_clbc1_f3 --run --seed 1 --device cuda
    python -m scripts.b0_v3_capturer_clbc1_f3 --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

from scripts.b0_v3_capturer_clbc1 import (
    _episode_stats, _trace_policy, dataset_hash, pair_keys, scenario_plan, signature,
)
from scripts.b0_v3_capturer_clbc1_f2 import (
    F2, FireAuditEnv, reconstruct_clbc1, set_arm, summarize,
)
from scripts.b0_v3_capturer_clbc1_f3_manifest import ARMS, load as load_manifest
from scripts.b0_v3_capturer_f1 import component_hashes, require_cublas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1_f3"
EXEC_PATHS = (
    "shepherd",
    "scripts/b0_v3_capturer_clbc1_f3.py",
    "scripts/b0_v3_capturer_clbc1_f3_manifest.py",
    "scripts/b0_v3_capturer_clbc1_f2.py",
    "scripts/b0_v3_capturer_clbc1.py",
    "scripts/b0_v3_capturer_f1.py",
    "scripts/b0_v3_capturer_diagnostic.py",
    "artifacts/marl/b0_v3_capturer_clbc1_f3/manifest.json",
)
CONTROL, F3 = ARMS
PASS = "PASS_F3_TO_CAPTURER_ONLY_RL_CONTRACT_DRAFT"
STOP = "STOP_F3"
INVALID = "INVALID_F3"


def robust_label_from_obs(obs, trailing_features: int = 2) -> bool:
    """Exact observable robust predicate for the B0-v3 noiseless observation."""
    x = np.asarray(obs, dtype=np.float32).reshape(-1)
    k = int(trailing_features)
    if len(x) < 3 + k:
        raise ValueError("observation too short for viability triple")
    v_worst, p_feasible = float(x[-2 - k]), float(x[-1 - k])
    return bool(p_feasible > 0.0 and v_worst >= 1.0)


def _classification(head, runner, X: np.ndarray, y: np.ndarray, mask: np.ndarray) -> dict:
    import torch
    import torch.nn.functional as F
    xn = runner.norm.normalize(X[mask])
    yt = torch.as_tensor(y[mask, None], device=runner.tr.device)
    with torch.no_grad():
        logits = head(torch.as_tensor(xn, device=runner.tr.device))
        prob = torch.sigmoid(logits)
        pred = prob >= 0.5
        pos = yt > 0.5
        tp = int((pred & pos).sum().item())
        tn = int(((~pred) & (~pos)).sum().item())
        fp = int((pred & (~pos)).sum().item())
        fn = int(((~pred) & pos).sum().item())
        loss = float(F.binary_cross_entropy_with_logits(logits, yt).item())
    tpr = tp / (tp + fn) if tp + fn else None
    tnr = tn / (tn + fp) if tn + fp else None
    return {
        "n": int(mask.sum()), "positive": int(y[mask].sum()), "negative": int(mask.sum() - y[mask].sum()),
        "tp": tp, "tn": tn, "fp": fp, "fn": fn, "loss": loss,
        "tpr": tpr, "tnr": tnr, "fpr": None if tnr is None else 1.0 - tnr,
        "balanced_accuracy": None if tpr is None or tnr is None else 0.5 * (tpr + tnr),
        "prob_positive_mean": float(prob[pos].mean().item()) if bool(pos.any()) else None,
        "prob_negative_mean": float(prob[~pos].mean().item()) if bool((~pos).any()) else None,
    }


def train_fire_head(runner, data: dict, manifest: dict, seed: int, *, smoke=False) -> dict:
    import torch
    import torch.nn.functional as F
    X = np.asarray(data["X"], np.float32)
    y = np.asarray(data["robust"], np.float32)
    split = np.asarray(data["split"], np.uint8)
    soft = np.asarray(data["soft_candidate"], np.uint8) == 1
    train, val = split == 0, split == 1
    support = {"train_positive": int(y[train].sum()), "train_negative": int(train.sum() - y[train].sum()),
               "val_positive": int(y[val].sum()), "val_negative": int(val.sum() - y[val].sum()),
               "train_soft_negative": int((train & soft & (y == 0)).sum()),
               "val_soft_negative": int((val & soft & (y == 0)).sum())}
    if not smoke and any(v <= 0 for v in support.values()):
        raise SystemExit(f"F3 class-support failure: {support}")
    if not bool(train.any()):
        raise SystemExit("F3 collection has no training rows")

    tr = manifest["training"]
    steps = 4 if smoke else int(tr["steps"])
    batch = min(int(tr["batch"]), int(train.sum()))
    xn = runner.norm.normalize(X)
    xt = torch.as_tensor(xn, device=runner.tr.device)
    yt = torch.as_tensor(y[:, None], device=runner.tr.device)
    train_idx = np.flatnonzero(train)
    n_pos = float(y[train].sum())
    pos_weight = 1.0 if n_pos == 0 else float((train.sum() - n_pos) / n_pos)
    weight = torch.as_tensor([pos_weight], device=runner.tr.device)
    opt = torch.optim.Adam(runner.tr.fin_actor.fire_logit.parameters(), lr=float(tr["lr"]))
    rng = np.random.default_rng(int(seed) + 27301)
    index_hash = hashlib.sha256()
    losses = []
    for _ in range(steps):
        idx = rng.choice(train_idx, size=batch, replace=True)
        index_hash.update(np.ascontiguousarray(idx).tobytes())
        ti = torch.as_tensor(idx, device=runner.tr.device)
        loss = F.binary_cross_entropy_with_logits(
            runner.tr.fin_actor.fire_logit(xt[ti]), yt[ti], pos_weight=weight)
        opt.zero_grad(); loss.backward(); opt.step()
        value = float(loss.item())
        if not math.isfinite(value):
            raise FloatingPointError("non-finite F3 FIRE-head loss")
        losses.append(value)
    return {
        "steps": steps, "batch": batch, "lr": float(tr["lr"]), "pos_weight": pos_weight,
        "support": support, "minibatch_index_hash": index_hash.hexdigest()[:16],
        "last_loss": losses[-1], "min_loss": min(losses), "max_loss": max(losses),
        "fit": {"train": _classification(runner.tr.fin_actor.fire_logit, runner, X, y, train),
                "validation": _classification(runner.tr.fin_actor.fire_logit, runner, X, y, val)
                if bool(val.any()) else None,
                "validation_soft_gate": _classification(
                    runner.tr.fin_actor.fire_logit, runner, X, y,
                    val & (np.asarray(data["soft_candidate"], np.uint8) == 1))
                if bool((val & (np.asarray(data["soft_candidate"], np.uint8) == 1)).any()) else None},
    }


def _collection_policy(base_policy, runner, env, rows: list, meta: dict):
    fid = env.finisher_id

    def policy(obs, flags):
        acts = dict(base_policy(obs, flags))
        phase = str(getattr(env.fsm.state, "value", env.fsm.state))
        x = np.asarray(obs, np.float32)
        if phase == "LOADED" and bool(np.isfinite(x).all()):
            rows.append({**meta, "t": len(rows), "obs": x.copy(),
                         "robust": robust_label_from_obs(x),
                         "v_shot_soft": float(x[-5]), "v_shot_worst": float(x[-4]),
                         "p_feasible": float(x[-3]), "fsm": phase})
        fa = np.asarray(acts[fid], np.float32).copy()
        if fa.size < 5:
            raise RuntimeError("F3 collection expected padded finisher Box(5) action")
        fa[4] = 0.0
        acts[fid] = fa
        return acts
    return policy


def collect_dataset(runner, manifest: dict, b2: dict, seed: int, run_dir: Path,
                    *, smoke=False) -> tuple[dict, dict]:
    import torch
    from shepherd.m4_env import build_m4_env
    from shepherd.provenance import git_commit
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv

    spec = manifest["collection"]
    plan = scenario_plan(spec, b2, seed, n_cells=2 if smoke else None,
                         episodes_per_cell=1 if smoke else None)
    cells = {c["cell_id"]: c for c in b2["cells"]}
    base, rows = runner.policy_fn(deterministic=False), []
    for p in plan:
        sid = p["scenario_id"]
        chi, eta, kw = scenario_kwargs(b2, cells[p["cell_id"]], sid,
                                       seed0=spec["seed0"], seed_ns=spec["namespace"])
        if (chi, eta) != (p["chi"], p["eta"]):
            raise RuntimeError("F3 collection scenario plan mismatch")
        stack = build_m4_env(spec["seed0"], sid, **kw)
        env = B0V3CreditEnv(stack.env, runner.credit_spec)
        torch.manual_seed(p["torch_seed"])
        within = sid - int(p["cell_index"]) * int(spec["episodes_per_cell"])
        meta = {"cell_index": p["cell_index"], "scenario_id": sid,
                "split": 1 if within == int(spec["episodes_per_cell"]) - 1 else 0}
        run_episode(env, stack.scn, stack.lay, seed=p["env_seed"],
                    policy=_collection_policy(base, runner, env, rows, meta),
                    scripted_roles=("limiter",), limiter_mode="hold", fire_mode="never")
    if not rows:
        raise RuntimeError("F3 collection produced zero rows")
    arrays = {
        "X": np.asarray([r["obs"] for r in rows], np.float32),
        "robust": np.asarray([r["robust"] for r in rows], np.float32),
        "soft_candidate": np.asarray([r["v_shot_soft"] >= 0.9 for r in rows], np.uint8),
        "split": np.asarray([r["split"] for r in rows], np.uint8),
        "cell_index": np.asarray([r["cell_index"] for r in rows], np.int16),
        "scenario_id": np.asarray([r["scenario_id"] for r in rows], np.int32),
        "step": np.asarray([r["t"] for r in rows], np.int16),
    }
    receipt = {
        "schema": "b0-v3-capturer-clbc1-f3-collection-v1" + ("-smoke" if smoke else ""),
        "manifest_hash": manifest["manifest_hash"], "code_commit": git_commit(),
        "actor_seed": seed, "dataset_hash": dataset_hash(arrays),
        "n_rows": len(rows), "n_episodes": len(plan),
        "train_rows": int((arrays["split"] == 0).sum()),
        "validation_rows": int((arrays["split"] == 1).sum()),
        "train_positive": int(arrays["robust"][arrays["split"] == 0].sum()),
        "validation_positive": int(arrays["robust"][arrays["split"] == 1].sum()),
        "train_soft_negative": int(((arrays["split"] == 0) & (arrays["soft_candidate"] == 1)
                                    & (arrays["robust"] == 0)).sum()),
        "validation_soft_negative": int(((arrays["split"] == 1)
                                         & (arrays["soft_candidate"] == 1)
                                         & (arrays["robust"] == 0)).sum()),
        "scenario_signature": signature(plan),
        "fire_suppression": "collection only; sampled Bernoulli consumed then env FIRE bit set to 0",
        "rl_updates": 0,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(run_dir / "collection.npz", **arrays)
    (run_dir / "collection.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return arrays, receipt


def _load_collection(run_dir: Path, manifest: dict, seed: int) -> tuple[dict, dict]:
    from shepherd.provenance import git_commit
    receipt = json.loads((run_dir / "collection.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "collection.npz", allow_pickle=False) as z:
        arrays = {k: np.asarray(z[k]) for k in z.files}
    checks = {"manifest": receipt["manifest_hash"] == manifest["manifest_hash"],
              "commit": receipt["code_commit"] == git_commit(),
              "seed": int(receipt["actor_seed"]) == seed,
              "content": receipt["dataset_hash"] == dataset_hash(arrays)}
    if not all(checks.values()):
        raise SystemExit(f"F3 collection mismatch: {checks}")
    return arrays, receipt


def summarize_f3(records: list[dict]) -> dict:
    out = summarize(records)
    out["nonrobust_FIRE"] = out["accepted_FIRE"] - out["robust_ready_FIRE"]
    return out


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
            raise RuntimeError("F3 evaluation scenario plan mismatch")
        stack = build_m4_env(spec["seed0"], sid, **kw)
        env = FireAuditEnv(B0V3CreditEnv(stack.env, runner.credit_spec))
        torch.manual_seed(p["torch_seed"])
        rows: list[dict] = []
        result = run_episode(env, stack.scn, stack.lay, seed=p["env_seed"],
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
        rec = {**p, "bin": outcome_bin, "label": result.label, "outcome": result.outcome,
               "fire": event is not None, "fire_step": result.fire_step,
               "clean_crossings": result.clean_crossings,
               "H_illegal": outcome_bin == "H_illegal", "steps": result.steps,
               "accepted_fire_judge": event, **stats}
        records.append(rec)
        if (p["cell_id"], sid) in trace_keys:
            extra = kw.get("extra_cfg", {})
            trace = {"schema": "b0-v3-capturer-clbc1-f3-trace-v1", "arm": arm,
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
            (trace_dir / f"trace_{arm}_seed{seed}_{p['cell_id']}_sid{sid}.json").write_text(
                json.dumps(trace, ensure_ascii=False), encoding="utf-8")
        if len(records) % 70 == 0:
            print(f"{arm}/s{seed}: {len(records)}/{len(plan)}", flush=True)
    return records


def apply_gate(per_seed: dict, fits: dict, integrity: dict, seeds=(0, 1)) -> dict:
    if not all(bool(v) for v in integrity.values()):
        return {"decision": INVALID, "clauses": {}, "integrity": integrity}
    def gt(a, b):
        return a is not None and b is not None and math.isfinite(float(a)) \
            and math.isfinite(float(b)) and float(a) > float(b)

    def ge(a, b):
        return a is not None and b is not None and math.isfinite(float(a)) \
            and math.isfinite(float(b)) and float(a) >= float(b)

    clauses = {}
    for seed in seeds:
        c, f = per_seed[seed][CONTROL], per_seed[seed][F3]
        cv = fits[seed][CONTROL]["validation_soft_gate"]
        fv = fits[seed][F3]["validation_soft_gate"]
        clauses[f"seed{seed}_validation_balanced_accuracy_increase"] = gt(
            fv["balanced_accuracy"], cv["balanced_accuracy"])
        clauses[f"seed{seed}_validation_fpr_decrease"] = gt(cv["fpr"], fv["fpr"])
        clauses[f"seed{seed}_validation_tpr_not_decrease"] = ge(fv["tpr"], cv["tpr"])
        clauses[f"seed{seed}_N_increase"] = f["N"] > c["N"]
        clauses[f"seed{seed}_robust_FIRE_not_decrease"] = (
            f["robust_ready_FIRE"] >= c["robust_ready_FIRE"])
        clauses[f"seed{seed}_nonrobust_FIRE_decrease"] = f["nonrobust_FIRE"] < c["nonrobust_FIRE"]
        clauses[f"seed{seed}_SPENT_FAIL_decrease"] = f["SPENT_FAIL"] < c["SPENT_FAIL"]
        clauses[f"seed{seed}_FIRE_to_N_increase"] = gt(f["FIRE_to_N"], c["FIRE_to_N"])
        clauses[f"seed{seed}_crossing_not_decrease"] = (
            f["clean_crossing_episodes"] >= c["clean_crossing_episodes"])
    pooled_h = {arm: sum(per_seed[s][arm]["H_illegal"] for s in seeds) for arm in ARMS}
    clauses["both_arms_pooled_H_illegal_zero"] = all(v == 0 for v in pooled_h.values())
    return {"decision": PASS if all(clauses.values()) else STOP, "clauses": clauses,
            "pooled_H_illegal": pooled_h, "integrity": integrity}


def _prerequisites(manifest: dict) -> dict:
    pre = manifest["prerequisites"]
    files = {
        "pilot": ROOT / "artifacts/marl/b0_v3_pilot/readout.json",
        "f1": ROOT / "artifacts/marl/b0_v3_capturer_f1/readout.json",
        "clbc1": ROOT / "artifacts/marl/b0_v3_capturer_clbc1/readout.json",
        "f2": ROOT / pre["f2_readout"],
        "f2_manifest": ROOT / pre["f2_manifest"],
    }
    data = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in files.items()}
    checks = {
        "pilot_NO_SELECTION": data["pilot"].get("decision") == pre["pilot_decision_required"],
        "F1_STOP": data["f1"].get("decision") == pre["f1_decision_required"],
        "CLBC1_STOP": data["clbc1"].get("decision") == pre["clbc1_decision_required"],
        "F2_manifest": data["f2_manifest"].get("manifest_hash") == pre["f2_manifest_hash"],
        "F2_STOP": data["f2"].get("decision") == pre["f2_decision_required"],
        "F2_code": data["f2"].get("code_commit") == pre["f2_source_code_commit"],
    }
    if not all(checks.values()):
        raise SystemExit(f"F3 prerequisite failure: {checks}")
    return checks, data["f2_manifest"]


def run_seed(seed: int, device: str, *, smoke=False, out_root: Path = OUT) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import BC_FILE, load_bc
    from shepherd.scripts.b0_v3_pilot_manifest import load as load_pilot
    from shepherd.scripts.b2_manifest import load as load_b2
    from scripts.b0_v3_capturer_clbc1_manifest import load as load_clbc1

    manifest = load_manifest()
    cublas = require_cublas(device, manifest)
    if seed not in manifest["parent"]["actor_seeds"]:
        raise ValueError("seed outside sealed F3 manifest")
    dirty = git_dirty(EXEC_PATHS)
    if dirty and not smoke:
        raise SystemExit(f"dirty execution code; run refused: {dirty}")
    run_dir = out_root / ("smoke" if smoke else "") / f"seed{seed}"
    if not smoke and (run_dir / ".done").exists():
        raise SystemExit(f"completed run exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    prereq, f2_manifest = _prerequisites(manifest)
    pilot, b2, clbc1 = load_pilot(), load_b2(), load_clbc1()
    original, bc_meta = load_bc(BC_FILE, pilot)
    runners, parent_meta, parent_states = {}, {}, {}
    for arm in ARMS:
        runner, meta = reconstruct_clbc1(seed, device, original, pilot, b2, clbc1,
                                         f2_manifest, smoke=smoke)
        intervention = set_arm(runner, F2, f2_manifest)
        runners[arm], parent_meta[arm] = runner, {**meta, "f2_intervention": intervention}
        parent_states[arm] = component_hashes(runner)
    common_parent = parent_states[CONTROL] == parent_states[F3]
    expected_parent = manifest["prerequisites"]["f2_parent_state"][str(seed)]
    exact_parent = all(parent_states[a] == expected_parent for a in ARMS)
    if not smoke and not exact_parent:
        raise SystemExit(f"F3 exact F2 parent mismatch seed{seed}")

    cpath = run_dir / "collection.json"
    if not smoke and cpath.exists() and (run_dir / "collection.npz").exists():
        collection, receipt = _load_collection(run_dir, manifest, seed)
    else:
        collection, receipt = collect_dataset(runners[CONTROL], manifest, b2, seed,
                                               run_dir, smoke=smoke)

    before = {a: component_hashes(runners[a]) for a in ARMS}
    train_mask, val_mask = collection["split"] == 0, collection["split"] == 1
    fits = {CONTROL: {
        "train": _classification(runners[CONTROL].tr.fin_actor.fire_logit,
                                 runners[CONTROL], collection["X"], collection["robust"], train_mask),
        "validation": (_classification(runners[CONTROL].tr.fin_actor.fire_logit,
                                       runners[CONTROL], collection["X"], collection["robust"], val_mask)
                       if bool(val_mask.any()) else None),
        "validation_soft_gate": (_classification(
            runners[CONTROL].tr.fin_actor.fire_logit, runners[CONTROL], collection["X"],
            collection["robust"], val_mask & (collection["soft_candidate"] == 1))
            if bool((val_mask & (collection["soft_candidate"] == 1)).any()) else None)}}
    training = train_fire_head(runners[F3], collection, manifest, seed, smoke=smoke)
    fits[F3] = training["fit"]
    after = {a: component_hashes(runners[a]) for a in ARMS}
    fixed = ("lim_actor", "fin_mean", "fin_log_std", "critic", "obs_norm")
    fire_head_only = (before[CONTROL] == after[CONTROL]
                      and all(before[F3][k] == after[F3][k] for k in fixed)
                      and before[F3]["fin_fire_logit"] != after[F3]["fin_fire_logit"]
                      and all(after[CONTROL][k] == after[F3][k] for k in fixed))
    if not fire_head_only:
        raise SystemExit("F3 fire-head-only identity failed")

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
                raise SystemExit(f"F3 evaluation lineage mismatch for {arm}")
            records = payload["records"]
        else:
            records = evaluate(runners[arm], manifest, b2, plan, arm=arm, seed=seed,
                               trace_dir=run_dir / "traces")
            path.write_text(json.dumps({"manifest_hash": manifest["manifest_hash"],
                                        "code_commit": git_commit(), "actor_seed": seed,
                                        "arm": arm, "records": records}, ensure_ascii=False),
                            encoding="utf-8")
        if pair_keys(records) != pair_keys(plan):
            raise SystemExit(f"F3 pairing mismatch for {arm}")
        evaluations[arm] = {**summarize_f3(records), "records": records}

    fire_audit = all(bool(r["fire"]) == (r["accepted_fire_judge"] is not None)
                     for arm in ARMS for r in evaluations[arm]["records"])
    finite = all(math.isfinite(float(r[k]))
                 for arm in ARMS for r in evaluations[arm]["records"]
                 for k in ("mu_norm_mean", "ang_mean_teacher_deg_mean",
                           "ang_cmd_mean_deg_mean", "ang_att_teacher_deg_mean"))
    summary = {
        "schema": "b0-v3-capturer-clbc1-f3-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS", "scope": manifest["scope"], "actor_seed": seed,
        "provenance": {"manifest_hash": manifest["manifest_hash"],
                       "b0_v3_hash": b2["b0_v3_hash"],
                       "bc_dataset_hash": bc_meta["dataset_hash"], "code_commit": git_commit(),
                       "code_dirty_scoped": dirty, "cublas_workspace_config": cublas,
                       "device": device, "rl_updates": 0},
        "prerequisites": prereq, "parents": parent_meta,
        "identity": {"common_parent": common_parent,
                     "exact_f2_parent": exact_parent if not smoke else None,
                     "fire_head_only": fire_head_only,
                     "before": before, "after": after},
        "collection": receipt, "training": training, "teacher_fit": fits,
        "scenario_signature": {"plan": signature(plan),
                               **{a: signature(evaluations[a]["records"]) for a in ARMS}},
        "evaluation": evaluations, "authoritative_fire_logging": fire_audit,
        "finite": finite, "elapsed_s": round(time.time() - t0, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not smoke:
        (run_dir / ".done").write_text(json.dumps(
            {"manifest_hash": manifest["manifest_hash"],
             "code_commit": summary["provenance"]["code_commit"]}), encoding="utf-8")
    for arm in ARMS:
        block = evaluations[arm]
        print(f"{arm}/s{seed}: N={block['N']} robust={block['robust_ready_FIRE']} "
              f"nonrobust={block['nonrobust_FIRE']} FIRE={block['accepted_FIRE']} "
              f"spent={block['SPENT_FAIL']} cross={block['clean_crossing_episodes']}", flush=True)
    return summary


def readout(out_root: Path = OUT) -> dict:
    from shepherd.provenance import git_commit
    from shepherd.scripts.b2_manifest import load as load_b2
    manifest, b2 = load_manifest(), load_b2()
    seeds = tuple(manifest["parent"]["actor_seeds"])
    missing = [s for s in seeds if not ((out_root / f"seed{s}" / ".done").exists()
                                        and (out_root / f"seed{s}" / "summary.json").exists())]
    if missing:
        out = {"schema": "b0-v3-capturer-clbc1-f3-readout-v1", "status": "INCOMPLETE",
               "manifest_hash": manifest["manifest_hash"], "missing_seeds": missing,
               "decision": None}
        print(json.dumps(out, indent=2, ensure_ascii=False)); return out
    runs = {s: json.loads((out_root / f"seed{s}" / "summary.json").read_text(encoding="utf-8"))
            for s in seeds}
    commits = {r["provenance"]["code_commit"] for r in runs.values()}
    lineage = len(commits) == 1
    pairing = finite = completion = exact_parent = collection_ok = fire_only = fire_audit = budget = True
    per_seed, fits = {}, {}
    for seed, run in runs.items():
        p = run["provenance"]
        lineage &= (run["schema"] == "b0-v3-capturer-clbc1-f3-run-v1"
                    and run["status"] == "PASS" and run["actor_seed"] == seed
                    and p["manifest_hash"] == manifest["manifest_hash"]
                    and p["b0_v3_hash"] == manifest["prerequisites"]["b0_v3_hash"]
                    and not p["code_dirty_scoped"] and p["rl_updates"] == 0
                    and (not str(p["device"]).startswith("cuda")
                         or p["cublas_workspace_config"] in manifest["runtime"]["cublas_workspace_config"]))
        expected = pair_keys(scenario_plan(manifest["evaluation"], b2, seed))
        blocks = {}
        for arm in ARMS:
            records = run["evaluation"][arm]["records"]
            pairing &= pair_keys(records) == expected
            completion &= len(records) == manifest["evaluation"]["episodes_per_arm_per_seed"]
            blocks[arm] = summarize_f3(records)
        per_seed[seed], fits[seed] = blocks, run["teacher_fit"]
        exact_parent &= run["identity"]["exact_f2_parent"] is True
        fire_only &= bool(run["identity"]["common_parent"] and run["identity"]["fire_head_only"])
        fire_audit &= bool(run["authoritative_fire_logging"])
        finite &= bool(run["finite"])
        c = run["collection"]
        collection_ok &= (c["manifest_hash"] == manifest["manifest_hash"]
                          and c["n_episodes"] == manifest["collection"]["episodes_per_seed"]
                          and c["train_positive"] > 0 and c["validation_positive"] > 0
                          and c["train_soft_negative"] > 0
                          and c["validation_soft_negative"] > 0
                          and c["rl_updates"] == 0)
    budget &= (sum(per_seed[s][a]["n"] for s in seeds for a in ARMS)
               == manifest["evaluation"]["episodes_total"]
               and sum(runs[s]["collection"]["n_episodes"] for s in seeds)
               == manifest["collection"]["episodes_total"])
    integrity = {"lineage": bool(lineage), "pairing": bool(pairing), "finite": bool(finite),
                 "completion": bool(completion), "exact_parent": bool(exact_parent),
                 "collection": bool(collection_ok), "fire_head_only": bool(fire_only),
                 "authoritative_fire_logging": bool(fire_audit), "budget": bool(budget)}
    gate = apply_gate(per_seed, fits, integrity, seeds)
    out = {"schema": "b0-v3-capturer-clbc1-f3-readout-v1", "status": "COMPLETE",
           "manifest_hash": manifest["manifest_hash"], "scope": manifest["scope"],
           "integrity": integrity, "teacher_fit": fits, "per_seed": per_seed,
           "gate": gate, "decision": gate["decision"],
           "code_commit": next(iter(commits)) if len(commits) == 1 else sorted(commits),
           "readout_code_commit": git_commit()}
    (out_root / "readout.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False)); return out


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--readout", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args(argv)
    readout() if args.readout else run_seed(args.seed, args.device, smoke=args.smoke)


if __name__ == "__main__":
    main()
