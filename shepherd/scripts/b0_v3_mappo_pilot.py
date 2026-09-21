"""B0 v3 B-5 MAPPO hyperparameter pilot runner (docs/110)."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import pathlib
import time

import numpy as np
import torch
import torch.nn.functional as F

from shepherd.m4_env import build_m4_env
from shepherd.notify import ntfy, ntfy_enabled
from shepherd.provenance import git_commit, git_dirty
from shepherd.scripts.b0_v3_pilot_manifest import load as load_pilot_manifest
from shepherd.scripts.b2_manifest import load as load_b2_manifest
from shepherd.scripts.mission_rollout import (partition_bin, run_episode,
                                               scripted_role_actions)
from shepherd.scripts.r2a_stage1 import draw_cell_jitter, resolve
from shepherd.scripts.r2b_phase1 import _slices
from shepherd.scripts.train_ippo import seed_everything
from shepherd.scripts.train_m4 import M4Runner
from shepherd.train.b0_v3_credit import B0V3CreditEnv, B0V3CreditSpec

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "marl" / "b0_v3_pilot"
BC_FILE = OUT / "bc_dataset.npz"
BC_META = OUT / "bc_dataset.json"


def _u64(*parts) -> int:
    raw = "|".join(str(x) for x in parts).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def boundary_cells(b2: dict) -> list:
    return [c for c in b2["cells"] if c["chi_role"] in ("lo", "hi")]


def scheduled_cell(b2: dict, train_seed: int, episode: int) -> tuple[dict, str]:
    """70% frontier / 20% anchor / 10% uniform, with deterministic row coverage."""
    row = (int(episode) + 5 * int(train_seed)) % 14
    slot = int(episode) % 10
    rows = [c for c in b2["cells"] if int(c["row"]) == row]
    by_role = {c["chi_role"]: c for c in rows}
    bit = _u64("pilot-cell", train_seed, episode) % 2
    if slot < 7:
        return by_role[("lo", "hi")[bit]], "frontier"
    if slot < 9:
        return by_role[("lo_out", "hi_out")[bit]], "anchor"
    return rows[_u64("pilot-uniform", train_seed, episode) % len(rows)], "uniform"


def scenario_kwargs(b2: dict, cell: dict, scenario_id: int, *,
                    seed0: int, seed_ns: str) -> tuple[float, float, dict]:
    impl = _slices()[int(cell["lam_slice"])]
    jitter = b2["crn"]["jitter"]
    chi, eta = draw_cell_jitter(seed0, int(scenario_id), cell["chi"], cell["eta"],
                               ns=seed_ns, jc=jitter["chi"], je=jitter["eta"])
    return chi, eta, resolve(impl, chi, eta)


def make_run_cfg(manifest: dict, candidate: str, *, steps: int | None = None,
                 rollout: int | None = None, bc_steps: int | None = None) -> dict:
    tr, fixed = manifest["training"], manifest["training"]["fixed"]
    cand = manifest["candidates"][candidate]
    total = int(tr["total_env_steps"] if steps is None else steps)
    roll = int(tr["rollout_env_steps"] if rollout is None else rollout)
    if total % roll:
        raise ValueError("total_env_steps must be divisible by rollout_env_steps")
    return {
        "loop": {"total_env_steps": total, "rollout_env_steps": roll},
        "mappo": {
            "gamma": fixed["gamma"], "lam": fixed["gae_lambda"],
            "lr": cand["lr"], "epochs": fixed["epochs"],
            "minibatch_size": min(int(fixed["minibatch_size"]), roll),
            "clip_eps": fixed["clip_eps"],
            "ent_coef_limiter": fixed["ent_coef_limiter"],
            "ent_coef_finisher": cand["ent_coef_finisher"],
            "vf_coef": fixed["vf_coef"], "max_grad_norm": fixed["max_grad_norm"],
            "target_kl": fixed["target_kl"], "hidden_sizes": fixed["hidden_sizes"],
            "init_log_std": fixed["init_log_std"],
            "ortho_init": fixed["ortho_init"], "value_norm": fixed["value_norm"],
            "limiter_commit": False, "coma_mix": fixed["coma_mix"],
        },
        "bc_steps": int(manifest["initialization"]["bc_steps"]
                        if bc_steps is None else bc_steps),
    }


def _dataset_hash(arrays: dict[str, np.ndarray]) -> str:
    h = hashlib.sha256()
    for key in sorted(arrays):
        x = np.ascontiguousarray(arrays[key])
        h.update(key.encode())
        h.update(str(x.dtype).encode())
        h.update(str(x.shape).encode())
        h.update(x.tobytes())
    return h.hexdigest()[:16]


def prepare_bc(path: pathlib.Path = BC_FILE, *, smoke: bool = False) -> dict:
    manifest, b2 = load_pilot_manifest(), load_b2_manifest()
    if not smoke and git_dirty():
        raise SystemExit(f"dirty training code; BC preparation refused: {git_dirty()}")
    init = manifest["initialization"]
    cells = boundary_cells(b2)
    if smoke:
        # Easy inside anchors make the smoke deterministic and cheap; the real dataset
        # still uses all 28 sealed boundary cells.
        cells = [c for c in b2["cells"] if c["chi_role"] == "lo_out"][:4]
    max_attempts = int(init["max_attempts_per_cell"])
    seed0 = int(init["seed0"])
    ns = str(init["seed_ns"]) + ("_smoke" if smoke else "")
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]

    X, axis, fire, cell_ids = [], [], [], []
    outcomes, success_cells = Counter(), []
    for ci, cell in enumerate(cells):
        kept = False
        for attempt in range(max_attempts):
            sid = ci * max_attempts + attempt
            _, _, kw = scenario_kwargs(b2, cell, sid, seed0=seed0, seed_ns=ns)
            stack = build_m4_env(seed0, sid, **kw)
            env = B0V3CreditEnv(stack.env, B0V3CreditSpec(beta=0.0))
            obs, _ = env.reset(seed=seed0 + sid)
            prev_clean = False
            ex, ea, ef = [], [], []
            outcome = "TRUNCATED"
            for _ in range(int(stack.lay.episode_len)):
                acts = scripted_role_actions(
                    env, stack.scn, stack.lay, limiter_mode="arc",
                    limiter_kw=c5, fire_mode="clean", prev_clean=prev_clean)
                acts[env.adversary_id] = np.zeros(3, np.float32)
                fa = np.asarray(acts[env.finisher_id], np.float32)
                ex.append(np.asarray(obs[env.finisher_id], np.float32).copy())
                ea.append(fa[:3].copy())
                ef.append(float(fa[4] > 0.5))
                obs, _, terms, truncs, infos = env.step(acts)
                fi = infos[env.finisher_id]
                prev_clean = bool(fi.get("clean_net_threshold_crossed", False))
                if any(terms.values()) or any(truncs.values()):
                    outcome = str(fi["b0_rl_outcome"])
                    break
            outcomes[outcome] += 1
            if outcome == "N":
                X.extend(ex); axis.extend(ea); fire.extend(ef)
                cell_ids.extend([ci] * len(ex))
                success_cells.append(cell["cell_id"])
                kept = True
                break
        if smoke and kept:
            break

    by_slice = Counter(next(c["lam_slice"] for c in cells if c["cell_id"] == cid)
                       for cid in success_cells)
    min_cells = 1 if smoke else int(init["minimum_success_cells"])
    min_slice = 0 if smoke else int(init["minimum_success_cells_per_lambda_slice"])
    if len(success_cells) < min_cells or any(by_slice[s] < min_slice for s in (0, 2)):
        raise RuntimeError(f"BC coverage gate failed: cells={len(success_cells)}, slices={by_slice}")
    arrays = {
        "X": np.asarray(X, np.float32),
        "axis": np.asarray(axis, np.float32),
        "fire": np.asarray(fire, np.float32),
        "cell_index": np.asarray(cell_ids, np.int16),
    }
    if arrays["fire"].sum() <= 0:
        raise RuntimeError("BC dataset contains no positive fire labels")
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    meta = {
        "schema": "b0-v3-capturer-bc-v1" + ("-smoke" if smoke else ""),
        "manifest_hash": manifest["manifest_hash"],
        "b0_v3_hash": b2["b0_v3_hash"],
        "dataset_hash": _dataset_hash(arrays),
        "n_samples": int(len(arrays["X"])),
        "n_fire_positive": int(arrays["fire"].sum()),
        "success_cells": success_cells,
        "n_success_cells": len(success_cells),
        "success_cells_by_slice": {str(k): int(v) for k, v in sorted(by_slice.items())},
        "attempt_outcomes": dict(sorted(outcomes.items())),
        "excluded_outcomes": init["exclude"],
        "code_commit": git_commit(),
        "code_dirty_scoped": git_dirty(),
    }
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    return meta


def load_bc(path: pathlib.Path, manifest: dict) -> tuple[dict, dict]:
    meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if meta["manifest_hash"] != manifest["manifest_hash"]:
        raise ValueError("BC dataset manifest mismatch")
    with np.load(path) as z:
        arrays = {k: z[k] for k in z.files}
    if _dataset_hash(arrays) != meta["dataset_hash"]:
        raise ValueError("BC dataset hash mismatch")
    return arrays, meta


def _last_linear(module):
    return [m for m in module.modules() if isinstance(m, torch.nn.Linear)][-1]


def initialize_from_bc(runner, data: dict, manifest: dict, *, steps: int) -> dict:
    """Fit capturer pointing/fire only; limiter mean is exactly neutral at t=0."""
    torch.manual_seed(runner.seed)
    lim_head = _last_linear(runner.tr.lim_actor.mean)
    torch.nn.init.zeros_(lim_head.weight)
    torch.nn.init.zeros_(lim_head.bias)

    X = np.asarray(data["X"], np.float32)
    ya = np.asarray(data["axis"], np.float32)
    yf = np.asarray(data["fire"], np.float32).reshape(-1, 1)
    runner.norm.update(X)
    xn = runner.norm.normalize(X)
    dev = runner.tr.device
    xt = torch.as_tensor(xn, device=dev)
    at = torch.as_tensor(ya, device=dev)
    ft = torch.as_tensor(yf, device=dev)
    params = list(runner.tr.fin_actor.mean.parameters()) + \
        list(runner.tr.fin_actor.fire_logit.parameters())
    opt = torch.optim.Adam(params, lr=float(manifest["initialization"]["bc_lr"]))
    n_pos = max(float(yf.sum()), 1.0)
    pos_weight = torch.as_tensor([(len(yf) - n_pos) / n_pos], device=dev)
    rng = np.random.default_rng(runner.seed + 7301)
    batch = min(int(manifest["initialization"]["bc_batch"]), len(X))
    last = {}
    for _ in range(int(steps)):
        idx = torch.as_tensor(rng.integers(0, len(X), size=batch), device=dev)
        pred_axis = runner.tr.fin_actor.mean(xt[idx])
        pa = pred_axis / pred_axis.norm(dim=-1, keepdim=True).clamp_min(1e-9)
        ta = at[idx] / at[idx].norm(dim=-1, keepdim=True).clamp_min(1e-9)
        axis_loss = (1.0 - (pa * ta).sum(-1)).mean()
        logits = runner.tr.fin_actor.fire_logit(xt[idx])
        fire_loss = F.binary_cross_entropy_with_logits(
            logits, ft[idx], pos_weight=pos_weight)
        loss = axis_loss + fire_loss
        opt.zero_grad(); loss.backward(); opt.step()
        last = {"loss": float(loss.item()), "axis_loss": float(axis_loss.item()),
                "fire_loss": float(fire_loss.item())}
    with torch.no_grad():
        pred = runner.tr.fin_actor.mean(xt)
        cos = F.cosine_similarity(pred, at, dim=-1).mean().item()
        prob = torch.sigmoid(runner.tr.fin_actor.fire_logit(xt))
        yhat = prob >= 0.5
        pos = ft > 0.5
        tpr = (yhat[pos] == pos[pos]).float().mean().item()
        tnr = (yhat[~pos] == pos[~pos]).float().mean().item()
        limiter_zero = float(lim_head.weight.abs().max().item()) == 0.0 and \
            float(lim_head.bias.abs().max().item()) == 0.0
    return {**last, "steps": int(steps), "n_samples": len(X),
            "mean_axis_cosine": float(cos), "fire_tpr": float(tpr),
            "fire_tnr": float(tnr), "limiter_mean_zero": bool(limiter_zero)}


class PilotRunner(M4Runner):
    def __init__(self, manifest: dict, b2: dict, candidate: str, seed: int,
                 device: str, *, steps: int | None = None, rollout: int | None = None,
                 bc_steps: int | None = None):
        self.pilot_manifest = manifest
        self.b2 = b2
        self.candidate = candidate
        self.cell_counts = Counter()
        self.credit_outcomes = Counter()
        self._current_cell = None
        cfg = make_run_cfg(manifest, candidate, steps=steps, rollout=rollout,
                           bc_steps=bc_steps)
        first, _ = scheduled_cell(b2, seed, 0)
        _, _, kw = scenario_kwargs(
            b2, first, seed * 1_000_000,
            seed0=manifest["training"]["seed0"],
            seed_ns=manifest["training"]["seed_ns"])
        cand = manifest["candidates"][candidate]
        self.credit_spec = B0V3CreditSpec(
            gamma=cfg["mappo"]["gamma"], beta=cand["beta"],
            r_clean=manifest["training"]["fixed"]["r_clean"],
            r_illegal=manifest["training"]["fixed"]["r_illegal"])
        super().__init__(
            cfg, seed, device, system=kw["system"], reward=kw["reward"],
            attacker=kw["attacker"], spawn=kw["spawn"], extra_cfg=kw["extra_cfg"],
            randomize_threat=False, threat_obs=True,
            limiter_policy="learned", finisher_policy="learned", aim_bc="none")
        contract = {
            "schema": "b0-v3-mappo-pilot-run-v1",
            "manifest_hash": manifest["manifest_hash"],
            "b0_v3_hash": b2["b0_v3_hash"],
            "candidate": candidate, "seed": int(seed),
            "credit_hash": self.credit_spec.manifest()["credit_hash"],
        }
        raw = json.dumps(contract, sort_keys=True, separators=(",", ":"))
        self.contract = {**contract, "hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}
        self.bc_steps = cfg["bc_steps"]

    def _build_episode_stack(self):
        cell, stratum = scheduled_cell(self.b2, self.seed, self._ep_idx)
        sid = self.seed * 1_000_000 + self._ep_idx
        chi, eta, kw = scenario_kwargs(
            self.b2, cell, sid,
            seed0=self.pilot_manifest["training"]["seed0"],
            seed_ns=self.pilot_manifest["training"]["seed_ns"])
        self._current_cell = {"cell_id": cell["cell_id"], "row": cell["row"],
                              "stratum": stratum, "chi": chi, "eta": eta}
        return build_m4_env(self.pilot_manifest["training"]["seed0"] + self.seed,
                            self._ep_idx, **kw)

    def _wrap_episode_env(self, env):
        return B0V3CreditEnv(env, self.credit_spec)

    def _observe_step(self, result) -> None:
        super()._observe_step(result)
        if result.flags.get("b0_credit_cut"):
            self.credit_outcomes[str(result.flags["b0_rl_outcome"])] += 1

    def _finish_episode(self, result) -> None:
        super()._finish_episode(result)
        self.ep_records[-1].update(self._current_cell or {})
        self.ep_records[-1]["rl_outcome"] = result.flags.get("b0_rl_outcome")
        if self._current_cell:
            self.cell_counts[self._current_cell["cell_id"]] += 1


def evaluate(runner: PilotRunner, *, cells: list | None = None,
             episodes_per_cell: int | None = None) -> dict:
    manifest, b2 = runner.pilot_manifest, runner.b2
    ev = manifest["evaluation"]
    cells = boundary_cells(b2) if cells is None else cells
    n_pc = int(ev["episodes_per_cell"] if episodes_per_cell is None else episodes_per_cell)
    policy = runner.policy_fn(deterministic=False)
    records = []
    for ci, cell in enumerate(cells):
        for j in range(n_pc):
            sid = ci * n_pc + j
            chi, eta, kw = scenario_kwargs(
                b2, cell, sid, seed0=ev["seed0"], seed_ns=ev["seed_ns"])
            stack = build_m4_env(ev["seed0"], sid, **kw)
            env = B0V3CreditEnv(stack.env, runner.credit_spec)
            torch.manual_seed(int(ev["seed0"]) + sid)
            result = run_episode(env, stack.scn, stack.lay,
                                 seed=int(ev["seed0"]) + sid, policy=policy,
                                 fire_mode="never", baseline_commit=False)
            records.append({
                "cell_id": cell["cell_id"], "row": cell["row"],
                "chi": chi, "eta": eta, "scenario_id": sid,
                "bin": partition_bin(result), "label": result.label,
                "fire": result.fire_step is not None, "steps": result.steps,
            })
    counts = Counter(r["bin"] for r in records)
    n = len(records)
    return {
        "n": n, "counts": dict(sorted(counts.items())),
        "p_N": counts["N"] / n, "p_H_illegal": counts["H_illegal"] / n,
        "p_FIRE": sum(r["fire"] for r in records) / n,
        "records": records,
    }


def _prereq(manifest: dict) -> None:
    for rel in (manifest["prerequisites"]["w5_decision"],
                manifest["prerequisites"]["preflight"]):
        d = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        if d.get("status", d.get("decision")) != "PASS":
            raise SystemExit(f"prerequisite is not PASS: {rel}")


def run_combo(candidate: str, seed: int, device: str, *, bc_path: pathlib.Path = BC_FILE,
              out_root: pathlib.Path = OUT, resume: bool = False,
              smoke: bool = False) -> dict:
    manifest, b2 = load_pilot_manifest(), load_b2_manifest()
    _prereq(manifest)
    if candidate not in manifest["candidates"] or seed not in manifest["training"]["seeds"]:
        raise ValueError("candidate or seed is outside the sealed manifest")
    if not smoke and git_dirty():
        raise SystemExit(f"dirty training code; run refused: {git_dirty()}")
    data, bc_meta = load_bc(bc_path, manifest)
    if not smoke and (bc_meta.get("code_dirty_scoped")
                      or bc_meta.get("code_commit") != git_commit()):
        raise SystemExit("BC dataset was not prepared from this clean execution commit")
    steps = 128 if smoke else None
    rollout = 128 if smoke else None
    bc_steps = 20 if smoke else None
    runner = PilotRunner(manifest, b2, candidate, seed, device,
                         steps=steps, rollout=rollout, bc_steps=bc_steps)
    run_dir = out_root / candidate / f"seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    start_update = 0
    bc_init = None
    if resume:
        restored = runner.restore(run_dir)
        start_update = restored // runner.rollout_env_steps
        pilot_state = run_dir / "pilot_state.json"
        if restored and pilot_state.exists():
            saved = json.loads(pilot_state.read_text(encoding="utf-8"))
            runner.credit_outcomes.update(saved.get("credit_outcomes", {}))
            runner.cell_counts.update(saved.get("cell_exposure", {}))
    if start_update == 0:
        bc_init = initialize_from_bc(runner, data, manifest, steps=runner.bc_steps)
        (run_dir / "bc_init.json").write_text(
            json.dumps(bc_init, indent=2, ensure_ascii=False), encoding="utf-8")

    total_updates = int(runner.tr.cfg.total_timesteps // runner.rollout_env_steps)
    log_path = run_dir / "train_log.json"
    logs = []
    if resume and log_path.exists():
        logs = json.loads(log_path.read_text(encoding="utf-8"))
    t0 = time.time()
    ntfy(f"B0 pilot {candidate}/s{seed} start u={start_update}/{total_updates}",
         title="b0-pilot")
    for update in range(start_update, total_updates):
        floor = float(manifest["training"]["fixed"]["lr_anneal_floor"])
        frac = update / max(total_updates - 1, 1)
        lr0 = float(manifest["candidates"][candidate]["lr"])
        runner.tr.set_lr(lr0 * max(1.0 - frac, floor))
        runner.collect_rollout()
        stats = runner.update()
        if not all(np.isfinite(float(v)) for v in stats.values()):
            raise FloatingPointError(f"non-finite training stats at update {update}")
        logs.append({"update": update + 1, "env_steps": runner.env_steps,
                     "stats": {k: float(v) for k, v in stats.items()},
                     "rolling": runner.rolling()})
        every = 1 if smoke else int(manifest["training"]["checkpoint_every_updates"])
        if (update + 1) % every == 0 or update + 1 == total_updates:
            runner.save(run_dir)
            log_path.write_text(json.dumps(logs, ensure_ascii=False), encoding="utf-8")
            (run_dir / "pilot_state.json").write_text(json.dumps({
                "credit_outcomes": dict(runner.credit_outcomes),
                "cell_exposure": dict(runner.cell_counts),
            }, ensure_ascii=False), encoding="utf-8")

    eval_cells = boundary_cells(b2)[:2] if smoke else None
    evaluation = evaluate(runner, cells=eval_cells, episodes_per_cell=1 if smoke else None)
    evaluation.pop("records") if smoke else None
    summary = {
        "schema": "b0-v3-mappo-pilot-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS", "scope": "hyperparameter pilot; not main learning evidence",
        "manifest_hash": manifest["manifest_hash"], "b0_v3_hash": b2["b0_v3_hash"],
        "candidate": candidate, "seed": seed, "device": device,
        "code_commit": git_commit(), "code_dirty_scoped": git_dirty(),
        "resumed": bool(start_update), "bc_dataset_hash": bc_meta["dataset_hash"],
        "bc_init": bc_init or json.loads((run_dir / "bc_init.json").read_text()),
        "training": {"steps": runner.env_steps, "updates": total_updates,
                     "episodes": runner._ep_idx,
                     "credit_outcomes": dict(sorted(runner.credit_outcomes.items())),
                     "cell_exposure": dict(sorted(runner.cell_counts.items())),
                     "last_update": logs[-1]},
        "evaluation": evaluation,
        "elapsed_s": round(time.time() - t0, 2),
        "ntfy": ntfy_enabled(),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / ".done").write_text(json.dumps({"manifest_hash": manifest["manifest_hash"],
                                                "code_commit": git_commit()}),
                                    encoding="utf-8")
    ntfy(f"B0 pilot {candidate}/s{seed} done N={evaluation['p_N']:.3f} "
         f"H={evaluation['p_H_illegal']:.3f}", title="b0-pilot")
    return summary


def check(out_root: pathlib.Path = OUT) -> dict:
    manifest = load_pilot_manifest()
    missing, bad, commits, bc_hashes = [], [], set(), set()
    for cand in manifest["candidates"]:
        for seed in manifest["training"]["seeds"]:
            d = out_root / cand / f"seed{seed}"
            if not (d / "summary.json").exists() or not (d / ".done").exists():
                missing.append(f"{cand}/seed{seed}")
                continue
            s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
            commits.add(s.get("code_commit"))
            bc_hashes.add(s.get("bc_dataset_hash"))
            if (s.get("manifest_hash") != manifest["manifest_hash"]
                    or s.get("code_dirty_scoped") or s.get("status") != "PASS"):
                bad.append(f"{cand}/seed{seed}")
    result = {"pass": not missing and not bad and len(commits) == 1
              and len(bc_hashes) == 1,
              "missing": missing, "bad": bad, "code_commits": sorted(commits),
              "bc_dataset_hashes": sorted(bc_hashes)}
    return result


def select_candidate(summaries: dict, manifest: dict) -> dict:
    gate = manifest["selection"]["eligibility"]
    rows = []
    for cand in sorted(manifest["candidates"]):
        ss = summaries[cand]
        pn = [float(x["evaluation"]["p_N"]) for x in ss]
        ph = [float(x["evaluation"]["p_H_illegal"]) for x in ss]
        pf = [float(x["evaluation"]["p_FIRE"]) for x in ss]
        row = {"candidate": cand, "mean_p_N": float(np.mean(pn)),
               "mean_p_H_illegal": float(np.mean(ph)), "mean_p_FIRE": float(np.mean(pf)),
               "seed_p_N": pn, "p_N_range": float(max(pn) - min(pn))}
        row["eligible"] = bool(
            row["mean_p_H_illegal"] <= gate["mean_p_H_illegal_max"]
            and row["mean_p_FIRE"] >= gate["mean_p_FIRE_min"]
            and row["mean_p_N"] >= gate["mean_p_N_min"]
            and min(pn) >= gate["each_seed_p_N_min"])
        rows.append(row)
    eligible = [r for r in rows if r["eligible"]]
    if not eligible:
        return {"decision": "NO_SELECTION", "selected": None, "candidates": rows}

    best_p = max(r["mean_p_N"] for r in eligible)
    tied = [r for r in eligible if best_p - r["mean_p_N"] < 0.01]
    tied.sort(key=lambda r: (r["mean_p_H_illegal"], r["p_N_range"], r["candidate"]))
    return {"decision": "SELECT", "selected": tied[0]["candidate"],
            "candidates": rows}


def readout(out_root: pathlib.Path = OUT) -> dict:
    manifest = load_pilot_manifest()
    complete = check(out_root)
    if not complete["pass"]:
        raise SystemExit(f"pilot incomplete: {complete}")
    grouped = defaultdict(list)
    for cand in manifest["candidates"]:
        for seed in manifest["training"]["seeds"]:
            grouped[cand].append(json.loads(
                (out_root / cand / f"seed{seed}" / "summary.json").read_text(encoding="utf-8")))
    decision = select_candidate(grouped, manifest)
    out = {"schema": "b0-v3-mappo-pilot-readout-v1",
           "manifest_hash": manifest["manifest_hash"], "completion": complete, **decision}
    (out_root / "readout.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-bc", action="store_true")
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--readout", action="store_true")
    p.add_argument("--candidate", choices=tuple(load_pilot_manifest()["candidates"]))
    p.add_argument("--seed", type=int)
    p.add_argument("--device", default="cuda")
    p.add_argument("--resume", action="store_true")
    args = p.parse_args(argv)
    if args.prepare_bc:
        print(json.dumps(prepare_bc(), ensure_ascii=False))
    elif args.smoke:
        smoke_root = OUT / "smoke"
        smoke_bc = smoke_root / "bc_dataset.npz"
        print(json.dumps(prepare_bc(smoke_bc, smoke=True), ensure_ascii=False))
        print(json.dumps(run_combo("c0_base", 0, "cpu", bc_path=smoke_bc,
                                   out_root=smoke_root, smoke=True), ensure_ascii=False))
    elif args.run:
        if args.candidate is None or args.seed is None:
            p.error("--run requires --candidate and --seed")
        print(json.dumps(run_combo(args.candidate, args.seed, args.device,
                                   resume=args.resume), ensure_ascii=False))
    elif args.check:
        out = check(); print(json.dumps(out, ensure_ascii=False))
        raise SystemExit(0 if out["pass"] else 1)
    else:
        print(json.dumps(readout(), ensure_ascii=False))


if __name__ == "__main__":
    main()
