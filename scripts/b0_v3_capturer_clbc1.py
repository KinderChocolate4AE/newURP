"""One-round closed-loop BC aggregation for the B0 v3 F1 capturer.

This is a BC-only mechanism experiment.  It reconstructs F1, collects its own
LOADED-state trajectory under a hold limiter, then compares equal-budget replay
against a fixed 50/50 original/closed-loop minibatch.  PPO is never called.

    python -m scripts.b0_v3_capturer_clbc1 --smoke --device cpu
    python -u -m scripts.b0_v3_capturer_clbc1 --run --seed 0 --device cuda
    python -u -m scripts.b0_v3_capturer_clbc1 --run --seed 1 --device cuda
    python -m scripts.b0_v3_capturer_clbc1 --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import pathlib
import time

import numpy as np

from scripts.b0_v3_capturer_clbc1_manifest import ARMS, load as load_manifest
from scripts.b0_v3_capturer_f1 import (F1, component_hashes, reconstruct,
                                        require_cublas, unit_axis_mse)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_clbc1"
F1_OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_f1"
EXEC_PATHS = ("shepherd", "scripts/b0_v3_capturer_clbc1.py",
              "scripts/b0_v3_capturer_clbc1_manifest.py",
              "scripts/b0_v3_capturer_f1.py",
              "scripts/b0_v3_capturer_f1_manifest.py",
              "scripts/b0_v3_capturer_diagnostic.py",
              "artifacts/marl/b0_v3_capturer_clbc1/manifest.json")
PAIR_KEYS = ("cell_id", "scenario_id", "chi", "eta", "env_seed", "torch_seed")
PASS = "PASS_TO_CAPTURER_ONLY_RL_CONTRACT"
STOP = "STOP_CLBC1"
INVALID = "INVALID_CLBC1"


# ----------------------------------------------------------- torch-free ---
def _boundary_cells(b2: dict) -> list:
    return [c for c in b2["cells"] if c["chi_role"] in ("lo", "hi")]


def scenario_plan(spec: dict, b2: dict, actor_seed: int, *, n_cells=None,
                  episodes_per_cell=None) -> list[dict]:
    """Create collection/evaluation plans without depending on an arm."""
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    sealed_n = int(spec["episodes_per_cell"])
    n = sealed_n if episodes_per_cell is None else int(episodes_per_cell)
    cells = _boundary_cells(b2)[:n_cells]
    out = []
    for ci, cell in enumerate(cells):
        for j in range(n):
            sid = ci * sealed_n + j
            chi, eta, _ = scenario_kwargs(b2, cell, sid, seed0=int(spec["seed0"]),
                                           seed_ns=spec["namespace"])
            out.append({"cell_id": cell["cell_id"], "cell_index": ci,
                        "scenario_id": sid, "chi": chi, "eta": eta,
                        "env_seed": int(spec["seed0"]) + sid,
                        "torch_seed": int(spec["seed0"])
                                      + 1_000_000 * int(actor_seed) + sid})
    return out


def pair_keys(rows: list[dict]) -> list[list]:
    return [[r[k] for k in PAIR_KEYS] for r in rows]


def signature(rows: list[dict]) -> str:
    raw = json.dumps(pair_keys(rows), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def dataset_hash(arrays: dict[str, np.ndarray]) -> str:
    h = hashlib.sha256()
    for key in sorted(arrays):
        x = np.ascontiguousarray(arrays[key])
        h.update(key.encode()); h.update(str(x.dtype).encode())
        h.update(str(x.shape).encode()); h.update(x.tobytes())
    return h.hexdigest()[:16]


def eligible_collection_state(fsm, teacher) -> bool:
    phase = str(getattr(fsm, "value", fsm))
    a = np.asarray(teacher, dtype=np.float32)
    return phase == "LOADED" and a.shape == (3,) and bool(np.isfinite(a).all()) \
        and float(np.linalg.norm(a)) > 1e-9


def _angle_deg(a, b) -> float:
    x, y = np.asarray(a, float), np.asarray(b, float)
    nx, ny = np.linalg.norm(x), np.linalg.norm(y)
    if nx <= 1e-12 or ny <= 1e-12:
        return float("nan")
    return float(np.degrees(np.arccos(np.clip(float(x @ y) / (nx * ny), -1.0, 1.0))))


def _finite_median(values) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.median(vals)) if vals else None


def summarize_records(records: list[dict]) -> dict:
    counts = Counter(r["bin"] for r in records)
    outcomes = Counter(r["outcome"] for r in records)
    return {
        "n": len(records), "counts": dict(sorted(counts.items())),
        "terminal_outcomes": dict(sorted(outcomes.items())),
        "N": counts["N"], "H_illegal": counts["H_illegal"],
        "FIRE_episodes": sum(bool(r["fire"]) for r in records),
        "FIRE_commands": sum(int(r["fire_commands"]) for r in records),
        "clean_crossing_episodes": sum(int(r["clean_crossings"] > 0) for r in records),
        "clean_crossings_total": sum(int(r["clean_crossings"]) for r in records),
        "mean_to_teacher_deg_median": _finite_median(
            r.get("ang_mean_teacher_deg_mean") for r in records),
        "sampled_to_mean_deg_median": _finite_median(
            r.get("ang_cmd_mean_deg_mean") for r in records),
        "attitude_to_teacher_deg_median": _finite_median(
            r.get("ang_att_teacher_deg_mean") for r in records),
        "mean_norm_median": _finite_median(r.get("mu_norm_mean") for r in records),
        "v_shot_soft_max_median": _finite_median(r.get("v_shot_soft_max")
                                                   for r in records),
    }


def apply_gate(per_seed: dict, integrity: dict, seeds=(0, 1)) -> dict:
    if not all(bool(v) for v in integrity.values()):
        return {"decision": INVALID, "clauses": {}, "integrity": integrity}
    clauses = {}
    for seed in seeds:
        replay, agg = per_seed[seed]["replay"], per_seed[seed]["clbc1"]
        clauses[f"seed{seed}_crossing_increase"] = (
            agg["clean_crossing_episodes"] > replay["clean_crossing_episodes"])
        clauses[f"seed{seed}_N_increase"] = agg["N"] > replay["N"]
        am, rm = agg["mean_to_teacher_deg_median"], replay["mean_to_teacher_deg_median"]
        clauses[f"seed{seed}_mean_angle_decrease"] = (
            am is not None and rm is not None and am < rm)
    pooled_h = {arm: sum(per_seed[s][arm]["H_illegal"] for s in seeds)
                for arm in ARMS}
    clauses["both_arms_pooled_H_illegal_zero"] = all(v == 0 for v in pooled_h.values())
    return {"decision": PASS if all(clauses.values()) else STOP,
            "clauses": clauses, "pooled_H_illegal": pooled_h,
            "integrity": integrity}


# --------------------------------------------------------------- setup ---
def _prereq(manifest: dict, pilot_manifest: dict, b2: dict) -> dict:
    pre = manifest["prerequisites"]
    pilot = json.loads((ROOT / pre["pilot_readout"]).read_text(encoding="utf-8"))
    bc_meta = json.loads((ROOT / pre["bc_dataset"]).read_text(encoding="utf-8"))
    f1m = json.loads((ROOT / pre["f1_manifest"]).read_text(encoding="utf-8"))
    f1r = json.loads((ROOT / pre["f1_readout"]).read_text(encoding="utf-8"))
    checks = {
        "pilot_NO_SELECTION": pilot.get("decision") == pre["pilot_decision_required"],
        "pilot_manifest": pilot_manifest["manifest_hash"] == pre["pilot_manifest_hash"],
        "b0_v3": b2["b0_v3_hash"] == pre["b0_v3_hash"],
        "bc_dataset": bc_meta.get("dataset_hash") == pre["bc_dataset_hash"],
        "bc_code_tree": bc_meta.get("code_tree") == pre["bc_code_tree"],
        "f1_manifest": f1m.get("manifest_hash") == pre["f1_manifest_hash"],
        "f1_STOP": f1r.get("decision") == pre["f1_decision_required"],
    }
    bad = [k for k, v in checks.items() if not v]
    if bad:
        raise SystemExit(f"CLBC1 prerequisite failure: {bad}")
    return bc_meta


def _f1_anchor(metrics: dict, seed: int, tol: float) -> dict:
    canonical = json.loads((F1_OUT / f"seed{seed}" / "summary.json")
                           .read_text(encoding="utf-8"))
    saved = canonical["teacher_fit"][F1]["bc_metrics"]
    keys = ("loss", "axis_loss", "fire_loss", "mean_axis_cosine",
            "fire_tpr", "fire_tnr")
    diffs = {k: abs(float(metrics[k]) - float(saved[k])) for k in keys}
    exact = all(v == 0.0 for v in diffs.values())
    close = all(v < tol for v in diffs.values())
    return {"verdict": "exact-metric-match" if exact else
            f"metric-close(<{tol:g})" if close else "metric-mismatch",
            "abs_diff": diffs}


# ------------------------------------------------------------- tracing ---
def _trace_policy(base_policy, runner, env, rows: list, *, collect=False,
                  episode_meta=None, exclusions=None):
    """Trace policy decisions; collection happens before the outcome is known."""
    import torch
    from shepherd.train.bc_aim import teacher_axis
    fid = env.finisher_id
    sigma = runner.tr.fin_actor.log_std.detach().clamp(-5.0, 2.0).exp().cpu().numpy()

    def policy(obs, flags):
        lims, fin, att = env._states()
        ta = teacher_axis(env)
        nobs = runner.norm.normalize(np.asarray(obs, np.float32))
        with torch.no_grad():
            t = torch.as_tensor(nobs[None, :], device=runner.tr.device)
            mu = runner.tr.fin_actor.mean(t)[0].cpu().numpy()
            logit = float(runner.tr.fin_actor.fire_logit(t)[0, 0].item())
        acts = dict(base_policy(obs, flags))
        fa = np.asarray(acts[fid], np.float32)
        phase = str(getattr(env.fsm.state, "value", env.fsm.state))
        row = {
            "t": len(rows), "fsm": phase,
            "p_att": env._p(att).tolist(), "v_att": env._v(att).tolist(),
            "p_fin": env._p(fin).tolist(), "e_fin": env._e(fin).tolist(),
            "p_lims": [env._p(x).tolist() for x in lims],
            "teacher_axis": np.asarray(ta, float).tolist(),
            "mu": mu.tolist(), "mu_norm": float(np.linalg.norm(mu)),
            "sigma": sigma.tolist(), "fire_logit": logit,
            "fire_prob": float(1.0 / (1.0 + np.exp(-logit))),
            "cmd_axis": fa[:3].tolist(),
            "fire_bit": float(fa[4]) if len(fa) >= 5 else None,
            "ang_mean_teacher_deg": _angle_deg(mu, ta),
            "ang_cmd_teacher_deg": _angle_deg(fa[:3], ta),
            "ang_cmd_mean_deg": _angle_deg(fa[:3], mu),
            "ang_att_teacher_deg": _angle_deg(env._e(fin), ta),
            "v_soft": float(np.asarray(obs).reshape(-1)[-5]),
            "v_worst": float(np.asarray(obs).reshape(-1)[-4]),
            "p_feasible": float(np.asarray(obs).reshape(-1)[-3]),
            "clean_prev": bool(flags.get("clean_net_threshold_crossed", False)),
            "fire_event_prev": bool(flags.get("fire_event", False)),
        }
        if collect:
            if eligible_collection_state(env.fsm.state, ta):
                row["obs"] = np.asarray(obs, np.float32).tolist()
                row.update(episode_meta or {})
                rows.append(row)
            else:
                key = "nonfinite_teacher" if not np.isfinite(ta).all() else "non_loaded"
                exclusions[key] += 1
        else:
            rows.append(row)
        return acts
    return policy


def _episode_stats(rows: list, fire_step) -> dict:
    def mean(key):
        vals = [float(r[key]) for r in rows if math.isfinite(float(r[key]))]
        return float(np.mean(vals)) if vals else None
    at = rows[fire_step] if fire_step is not None and fire_step < len(rows) else None
    return {
        "mu_norm_mean": mean("mu_norm"),
        "ang_mean_teacher_deg_mean": mean("ang_mean_teacher_deg"),
        "ang_cmd_teacher_deg_mean": mean("ang_cmd_teacher_deg"),
        "ang_cmd_mean_deg_mean": mean("ang_cmd_mean_deg"),
        "ang_att_teacher_deg_mean": mean("ang_att_teacher_deg"),
        "v_shot_soft_max": max((r["v_soft"] for r in rows), default=None),
        "net_phase_last": rows[-1]["fsm"] if rows else None,
        "fire_commands": sum(float(r.get("fire_bit") or 0.0) >= 0.5 for r in rows),
        "at_fire": None if at is None else {
            "v_shot_soft": at["v_soft"], "v_shot_worst": at["v_worst"],
            "p_feasible": at["p_feasible"], "net_phase": at["fsm"],
            "fire_prob": at["fire_prob"],
            "ang_att_teacher_deg": at["ang_att_teacher_deg"],
        },
    }


# ------------------------------------------------------------ collection ---
def collect_dataset(runner, manifest: dict, b2: dict, seed: int, run_dir: pathlib.Path,
                    *, smoke=False) -> tuple[dict, dict]:
    import torch
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv
    from shepherd.provenance import git_commit
    spec = manifest["collection"]
    plan = scenario_plan(spec, b2, seed, n_cells=2 if smoke else None,
                         episodes_per_cell=1)
    all_rows, episodes, exclusions = [], [], Counter()
    base = runner.policy_fn(deterministic=False)
    cells = {c["cell_id"]: c for c in b2["cells"]}
    for p in plan:
        sid = p["scenario_id"]
        chi, eta, kw = scenario_kwargs(b2, cells[p["cell_id"]], sid,
                                       seed0=spec["seed0"], seed_ns=spec["namespace"])
        if (chi, eta) != (p["chi"], p["eta"]):
            raise RuntimeError("collection scenario plan mismatch")
        stack = build_m4_env(spec["seed0"], sid, **kw)
        env = B0V3CreditEnv(stack.env, runner.credit_spec)
        torch.manual_seed(p["torch_seed"])
        rows = []
        meta = {k: p[k] for k in ("cell_id", "cell_index", "scenario_id")}
        result = run_episode(
            env, stack.scn, stack.lay, seed=p["env_seed"],
            policy=_trace_policy(base, runner, env, rows, collect=True,
                                 episode_meta=meta, exclusions=exclusions),
            scripted_roles=("limiter",), limiter_mode="hold", fire_mode="clean")
        terminal = {"bin": partition_bin(result), "outcome": result.outcome,
                    "label": result.label, "fire_step": result.fire_step,
                    "clean_crossings": result.clean_crossings}
        for row in rows:
            row.update(terminal)
        all_rows.extend(rows)
        episodes.append({**p, **terminal, "kept_rows": len(rows)})
    if not all_rows:
        raise RuntimeError("closed-loop collection produced zero eligible rows")
    arrays = {
        "X": np.asarray([r["obs"] for r in all_rows], np.float32),
        "axis": np.asarray([r["teacher_axis"] for r in all_rows], np.float32),
        "cell_index": np.asarray([r["cell_index"] for r in all_rows], np.int16),
        "scenario_id": np.asarray([r["scenario_id"] for r in all_rows], np.int32),
        "step": np.asarray([r["t"] for r in all_rows], np.int16),
    }
    arrays["axis"] /= np.maximum(np.linalg.norm(arrays["axis"], axis=1,
                                                  keepdims=True), 1e-9)
    dh = dataset_hash(arrays)
    receipt = {
        "schema": "b0-v3-capturer-clbc1-collection-v1" + ("-smoke" if smoke else ""),
        "manifest_hash": manifest["manifest_hash"], "actor_seed": seed,
        "code_commit": git_commit(),
        "dataset_hash": dh, "n_rows": len(all_rows), "n_episodes": len(plan),
        "cell_coverage": len({r["cell_id"] for r in all_rows}),
        "exclusions": dict(sorted(exclusions.items())),
        "outcomes": dict(sorted(Counter(e["bin"] for e in episodes).items())),
        "scenario_signature": signature(plan), "episodes": episodes,
        "selection": "all eligible rows collected before terminal outcome was known",
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(run_dir / "collection.npz", **arrays)
    (run_dir / "collection.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "collection_records.json").write_text(
        json.dumps(all_rows, ensure_ascii=False), encoding="utf-8")
    return arrays, receipt


def load_collection(run_dir: pathlib.Path, manifest: dict, seed: int) -> tuple[dict, dict]:
    from shepherd.provenance import git_commit
    receipt = json.loads((run_dir / "collection.json").read_text(encoding="utf-8"))
    with np.load(run_dir / "collection.npz", allow_pickle=False) as z:
        arrays = {k: np.asarray(z[k]) for k in z.files}
    if (receipt["manifest_hash"] != manifest["manifest_hash"]
            or receipt["actor_seed"] != seed
            or receipt["code_commit"] != git_commit()
            or receipt["dataset_hash"] != dataset_hash(arrays)):
        raise SystemExit("collection receipt/hash mismatch")
    return arrays, receipt


# -------------------------------------------------------------- training ---
def _optimizer_initial_signature(opt) -> str:
    state = opt.state_dict()
    serial = {"state": state["state"], "param_groups": [
        {k: v for k, v in g.items() if k != "params"} for g in state["param_groups"]]}
    return hashlib.sha256(json.dumps(serial, sort_keys=True).encode()).hexdigest()[:16]


def train_aim(runner, original: dict, collected: dict, manifest: dict, seed: int,
              arm: str, *, steps=None) -> dict:
    import torch
    if arm not in ARMS:
        raise ValueError(arm)
    tr = manifest["training"]
    n_steps = int(tr["steps"] if steps is None else steps)
    half = int(tr["half_batch"])
    xo = runner.norm.normalize(np.asarray(original["X"], np.float32))
    ao = np.asarray(original["axis"], np.float32)
    xn = runner.norm.normalize(np.asarray(collected["X"], np.float32))
    an = np.asarray(collected["axis"], np.float32)
    dev = runner.tr.device
    xo_t, ao_t = torch.as_tensor(xo, device=dev), torch.as_tensor(ao, device=dev)
    xn_t, an_t = torch.as_tensor(xn, device=dev), torch.as_tensor(an, device=dev)
    params = list(runner.tr.fin_actor.mean.parameters())
    opt = torch.optim.Adam(params, lr=float(tr["lr"]))
    initial_optimizer = _optimizer_initial_signature(opt)
    rng = np.random.default_rng(int(seed) + 17301)
    old_a_hash, second_hash = hashlib.sha256(), hashlib.sha256()
    losses = []
    for _ in range(n_steps):
        ia = rng.integers(0, len(xo), size=half)
        ib = rng.integers(0, len(xo) if arm == "replay" else len(xn), size=half)
        old_a_hash.update(np.ascontiguousarray(ia).tobytes())
        second_hash.update(np.ascontiguousarray(ib).tobytes())
        ia_t = torch.as_tensor(ia, device=dev)
        ib_t = torch.as_tensor(ib, device=dev)
        xb = torch.cat([xo_t[ia_t], xo_t[ib_t] if arm == "replay" else xn_t[ib_t]])
        ab = torch.cat([ao_t[ia_t], ao_t[ib_t] if arm == "replay" else an_t[ib_t]])
        loss = unit_axis_mse(runner.tr.fin_actor.mean(xb), ab)
        opt.zero_grad(); loss.backward(); opt.step()
        value = float(loss.item())
        if not math.isfinite(value):
            raise FloatingPointError(f"non-finite {arm} loss")
        losses.append(value)
    return {
        "arm": arm, "steps": n_steps, "batch": 2 * half,
        "old_rows_per_batch": (2 * half if arm == "replay" else half),
        "closed_loop_rows_per_batch": (0 if arm == "replay" else half),
        "replacement_sampling": True, "lr": float(tr["lr"]),
        "optimizer_initial_signature": initial_optimizer,
        "first_half_original_index_hash": old_a_hash.hexdigest()[:16],
        "second_half_index_hash": second_hash.hexdigest()[:16],
        "last_loss": losses[-1], "min_loss": min(losses), "max_loss": max(losses),
    }


def _frozen_equal(before: dict, after: dict) -> bool:
    return all(before[k] == after[k] for k in
               ("lim_actor", "fin_fire_logit", "fin_log_std", "critic", "obs_norm"))


# ------------------------------------------------------------ evaluation ---
def evaluate(runner, manifest: dict, b2: dict, plan: list[dict], *, arm: str,
             seed: int, trace_dir: pathlib.Path) -> list[dict]:
    import torch
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv
    spec = manifest["evaluation"]
    cells = {c["cell_id"]: c for c in b2["cells"]}
    trace_keys = {tuple(x) for x in manifest["traces"]["scenarios"]}
    base, records = runner.policy_fn(deterministic=False), []
    for p in plan:
        sid = p["scenario_id"]
        chi, eta, kw = scenario_kwargs(b2, cells[p["cell_id"]], sid,
                                       seed0=spec["seed0"], seed_ns=spec["namespace"])
        if (chi, eta) != (p["chi"], p["eta"]):
            raise RuntimeError("evaluation scenario plan mismatch")
        stack = build_m4_env(spec["seed0"], sid, **kw)
        env = B0V3CreditEnv(stack.env, runner.credit_spec)
        torch.manual_seed(p["torch_seed"])
        rows = []
        result = run_episode(
            env, stack.scn, stack.lay, seed=p["env_seed"],
            policy=_trace_policy(base, runner, env, rows),
            scripted_roles=("limiter",), limiter_mode="hold", fire_mode="clean")
        b = partition_bin(result)
        rec = {**p, "bin": b, "label": result.label, "outcome": result.outcome,
               "fire": result.fire_step is not None, "fire_step": result.fire_step,
               "clean_crossings": result.clean_crossings,
               "H_illegal": b == "H_illegal", "steps": result.steps,
               **_episode_stats(rows, result.fire_step)}
        records.append(rec)
        if (p["cell_id"], sid) in trace_keys:
            cone = kw.get("extra_cfg", {}).get("viability", {}).get("cone", {})
            trace = {
                "schema": "b0-v3-capturer-clbc1-trace-v1", "arm": arm,
                "actor_seed": seed, "cell_id": p["cell_id"], "scenario_id": sid,
                "chi": chi, "eta": eta, "cone_half_angle_rad": cone.get("half_angle"),
                "cone_range_max": cone.get("range_max"),
                "theta_fire": float(getattr(env, "theta_fire", 0.9)),
                "target": [float(x) for x in stack.lay.target],
                "result": {"bin": b, "label": result.label,
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


# ---------------------------------------------------------------- run ---
def run_seed(seed: int, device: str, *, smoke=False, out_root: pathlib.Path = OUT) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from scripts.b0_v3_capturer_diagnostic import teacher_fit
    from shepherd.scripts.b0_v3_mappo_pilot import BC_FILE, load_bc
    from shepherd.scripts.b0_v3_pilot_manifest import load as load_pilot_manifest
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
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

    pilot, b2 = load_pilot_manifest(), load_b2_manifest()
    _prereq(manifest, pilot, b2)
    original, bc_meta = load_bc(BC_FILE, pilot)
    parent, parent_bc = reconstruct(F1, seed, device, original, pilot, b2)
    anchor = _f1_anchor(parent_bc["metrics"], seed,
                        float(manifest["parent"]["anchor_tolerance_abs"]))
    if anchor["verdict"] == "metric-mismatch":
        raise SystemExit(f"F1 parent anchor mismatch: {anchor}")
    parent_hash = component_hashes(parent)

    if (not smoke and (run_dir / "collection.json").exists()
            and (run_dir / "collection.npz").exists()):
        collected, collection = load_collection(run_dir, manifest, seed)
    else:
        collected, collection = collect_dataset(parent, manifest, b2, seed, run_dir,
                                                 smoke=smoke)

    runners, training, parents, frozen = {}, {}, {}, {}
    added_steps = 4 if smoke else int(manifest["training"]["steps"])
    ckpt_path = run_dir / "trained_arms.pt"
    train_path = run_dir / "training.json"
    if not smoke and ckpt_path.exists() and train_path.exists():
        import torch
        saved = torch.load(ckpt_path, map_location=device, weights_only=True)
        training = json.loads(train_path.read_text(encoding="utf-8"))
        if (training["manifest_hash"] != manifest["manifest_hash"]
                or training["collection_hash"] != collection["dataset_hash"]
                or training["code_commit"] != git_commit()):
            raise SystemExit("training checkpoint lineage mismatch")
        for arm in ARMS:
            runners[arm], bc = reconstruct(F1, seed, device, original, pilot, b2)
            parents[arm] = component_hashes(runners[arm])
            runners[arm].tr.fin_actor.mean.load_state_dict(saved[arm])
            if component_hashes(runners[arm]) != training["arms"][arm]["post_state"]:
                raise SystemExit(f"training checkpoint state mismatch for {arm}")
            frozen[arm] = training["arms"][arm]["frozen_state_bit_identical"]
    else:
        from scripts.b0_v3_capturer_diagnostic import teacher_fit
        arms_payload = {}
        optimizer_sigs = []
        for arm in ARMS:
            runners[arm], bc = reconstruct(F1, seed, device, original, pilot, b2)
            before = component_hashes(runners[arm]); parents[arm] = before
            stats = train_aim(runners[arm], original, collected, manifest, seed, arm,
                              steps=added_steps)
            after = component_hashes(runners[arm])
            stats["frozen_state_bit_identical"] = _frozen_equal(before, after)
            stats["aim_head_changed"] = before["fin_mean"] != after["fin_mean"]
            stats["teacher_fit_after"] = teacher_fit(
                runners[arm].tr, runners[arm].norm, original,
                runners[arm].tr.device)
            stats["post_state"] = after
            arms_payload[arm] = stats
            optimizer_sigs.append(stats["optimizer_initial_signature"])
        training = {
            "schema": "b0-v3-capturer-clbc1-training-v1" + ("-smoke" if smoke else ""),
            "manifest_hash": manifest["manifest_hash"],
            "collection_hash": collection["dataset_hash"], "actor_seed": seed,
            "code_commit": git_commit(),
            "common_parent_equal": (parents["replay"] == parents["clbc1"]
                                    == parent_hash),
            "optimizer_initial_state_equal": len(set(optimizer_sigs)) == 1,
            "first_half_original_sequence_equal": (
                arms_payload["replay"]["first_half_original_index_hash"]
                == arms_payload["clbc1"]["first_half_original_index_hash"]),
            "arms": arms_payload,
        }
        import torch
        torch.save({arm: runners[arm].tr.fin_actor.mean.state_dict() for arm in ARMS},
                   ckpt_path)
        train_path.write_text(json.dumps(training, indent=2, ensure_ascii=False),
                              encoding="utf-8")
        frozen = {arm: training["arms"][arm]["frozen_state_bit_identical"]
                  for arm in ARMS}

    if not (training["common_parent_equal"]
            and training["optimizer_initial_state_equal"]
            and training["first_half_original_sequence_equal"]
            and all(frozen.values())):
        raise SystemExit(f"single-factor identity failed: {training}")

    plan = scenario_plan(manifest["evaluation"], b2, seed,
                         n_cells=2 if smoke else None,
                         episodes_per_cell=1 if smoke else None)
    evaluations = {}
    for arm in ARMS:
        ep_path = run_dir / f"evaluation_{arm}.json"
        if not smoke and ep_path.exists():
            saved_eval = json.loads(ep_path.read_text(encoding="utf-8"))
            if (saved_eval["manifest_hash"] != manifest["manifest_hash"]
                    or saved_eval["actor_seed"] != seed
                    or saved_eval["arm"] != arm
                    or saved_eval["code_commit"] != git_commit()):
                raise SystemExit(f"evaluation checkpoint lineage mismatch for {arm}")
            records = saved_eval["records"]
        else:
            records = evaluate(runners[arm], manifest, b2, plan, arm=arm, seed=seed,
                               trace_dir=run_dir / "traces")
            ep_path.write_text(json.dumps({"manifest_hash": manifest["manifest_hash"],
                                           "code_commit": git_commit(),
                                           "actor_seed": seed, "arm": arm,
                                           "records": records}, ensure_ascii=False),
                               encoding="utf-8")
        if pair_keys(records) != pair_keys(plan):
            raise SystemExit(f"pairing mismatch for {arm}")
        evaluations[arm] = {**summarize_records(records), "records": records}

    finite_fields = ("mu_norm_mean", "ang_mean_teacher_deg_mean",
                     "ang_cmd_mean_deg_mean", "ang_att_teacher_deg_mean")
    finite = (all(all(bool(p.detach().isfinite().all())
                      for p in r.tr.fin_actor.mean.parameters())
                  for r in runners.values())
              and all(rec[k] is not None and math.isfinite(float(rec[k]))
                      for arm in ARMS for rec in evaluations[arm]["records"]
                      for k in finite_fields)
              and all(np.isfinite(x).all() for x in collected.values()))
    summary = {
        "schema": "b0-v3-capturer-clbc1-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS", "scope": manifest["scope"], "actor_seed": seed,
        "provenance": {
            "manifest_hash": manifest["manifest_hash"],
            "b0_v3_hash": b2["b0_v3_hash"],
            "bc_dataset_hash": bc_meta["dataset_hash"],
            "bc_code_tree": bc_meta["code_tree"],
            "f1_manifest_hash": manifest["prerequisites"]["f1_manifest_hash"],
            "code_commit": git_commit(), "code_dirty_scoped": dirty,
            "cublas_workspace_config": cublas, "device": device, "rl_updates": 0,
        },
        "f1_parent_anchor": anchor, "parent_state": parent_hash,
        "collection": collection, "training": training,
        "scenario_signature": {"plan": signature(plan),
                               **{a: signature(evaluations[a]["records"])
                                  for a in ARMS}},
        "evaluation": evaluations, "finite": bool(finite),
        "elapsed_s": round(time.time() - t0, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if not smoke:
        (run_dir / ".done").write_text(json.dumps(
            {"manifest_hash": manifest["manifest_hash"],
             "code_commit": summary["provenance"]["code_commit"]}), encoding="utf-8")
    for arm in ARMS:
        e = evaluations[arm]
        print(f"{arm}/s{seed}: N={e['N']} cross={e['clean_crossing_episodes']} "
              f"FIRE={e['FIRE_episodes']} H={e['H_illegal']}", flush=True)
    return summary


# --------------------------------------------------------------- readout ---
def readout(out_root: pathlib.Path = OUT) -> dict:
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_manifest(), load_b2_manifest()
    seeds = manifest["parent"]["actor_seeds"]
    missing = [s for s in seeds if not ((out_root / f"seed{s}" / ".done").exists()
                                        and (out_root / f"seed{s}" / "summary.json").exists())]
    if missing:
        out = {"schema": "b0-v3-capturer-clbc1-readout-v1",
               "status": "INCOMPLETE", "manifest_hash": manifest["manifest_hash"],
               "missing_seeds": missing, "decision": None}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return out
    runs = {s: json.loads((out_root / f"seed{s}" / "summary.json")
                          .read_text(encoding="utf-8")) for s in seeds}
    lineage = len({r["provenance"]["code_commit"] for r in runs.values()}) == 1
    pairing, finite, completion, common_parent, frozen, budget = True, True, True, True, True, True
    per_seed = {}
    for seed, run in runs.items():
        pv = run["provenance"]
        lineage &= (run["schema"] == "b0-v3-capturer-clbc1-run-v1"
                    and run["status"] == "PASS"
                    and run["actor_seed"] == seed
                    and pv["manifest_hash"] == manifest["manifest_hash"]
                    and pv["b0_v3_hash"] == manifest["prerequisites"]["b0_v3_hash"]
                    and pv["bc_dataset_hash"] == manifest["prerequisites"]["bc_dataset_hash"]
                    and pv["bc_code_tree"] == manifest["prerequisites"]["bc_code_tree"]
                    and not pv["code_dirty_scoped"] and pv["rl_updates"] == 0
                    and (not str(pv["device"]).startswith("cuda")
                         or pv["cublas_workspace_config"]
                         in manifest["runtime"]["cublas_workspace_config"])
                    and run["f1_parent_anchor"]["verdict"] != "metric-mismatch")
        expected = pair_keys(scenario_plan(manifest["evaluation"], b2, seed))
        blocks = {}
        for arm in ARMS:
            records = run["evaluation"][arm]["records"]
            pairing &= pair_keys(records) == expected
            completion &= len(records) == manifest["evaluation"]["episodes_per_arm_per_seed"]
            blocks[arm] = summarize_records(records)
        common_parent &= run["training"]["common_parent_equal"] \
            and run["training"]["optimizer_initial_state_equal"]
        frozen &= all(run["training"]["arms"][a]["frozen_state_bit_identical"]
                      for a in ARMS)
        budget &= all(run["training"]["arms"][a]["steps"]
                      == manifest["training"]["steps"] for a in ARMS)
        half = manifest["training"]["half_batch"]
        budget &= (run["training"]["arms"]["replay"]["old_rows_per_batch"] == 2 * half
                   and run["training"]["arms"]["replay"]["closed_loop_rows_per_batch"] == 0
                   and run["training"]["arms"]["clbc1"]["old_rows_per_batch"] == half
                   and run["training"]["arms"]["clbc1"]["closed_loop_rows_per_batch"] == half
                   and run["training"]["first_half_original_sequence_equal"])
        budget &= (run["collection"]["n_episodes"]
                   == manifest["collection"]["episodes_per_seed"]
                   and run["collection"]["cell_coverage"] == 28)
        finite &= bool(run["finite"])
        per_seed[seed] = blocks
    completion &= sum(per_seed[s][a]["n"] for s in seeds for a in ARMS) \
        == manifest["evaluation"]["episodes_total"]
    integrity = {"lineage": bool(lineage), "pairing": bool(pairing),
                 "finite": bool(finite), "completion": bool(completion),
                 "common_parent": bool(common_parent), "frozen_state": bool(frozen),
                 "budget": bool(budget)}
    gate = apply_gate(per_seed, integrity, seeds)
    out = {"schema": "b0-v3-capturer-clbc1-readout-v1", "status": "COMPLETE",
           "manifest_hash": manifest["manifest_hash"], "scope": manifest["scope"],
           "integrity": integrity,
           "per_seed": {f"seed{s}": per_seed[s] for s in seeds},
           "gate": gate, "decision": gate["decision"],
           "promotion": manifest["promotion"]}
    (out_root / "readout.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"integrity": integrity, "gate": gate,
                      "promotion": out["promotion"]}, indent=2, ensure_ascii=False))
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--readout", action="store_true")
    p.add_argument("--seed", type=int)
    p.add_argument("--device", default="cuda")
    a = p.parse_args(argv)
    if a.smoke:
        run_seed(0, a.device, smoke=True)
    elif a.run:
        if a.seed is None:
            p.error("--run requires --seed")
        run_seed(a.seed, a.device)
    else:
        readout()


if __name__ == "__main__":
    main()
