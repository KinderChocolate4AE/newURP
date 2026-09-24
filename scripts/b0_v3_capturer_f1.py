"""B0 v3 capturer-F1 BC-SNR 수정 실행기 (manifest = scripts/b0_v3_capturer_f1_manifest.py).

한 요인: BC 조준 손실 cosine → 단위 교사축 MSE. 두 objective 는 같은 BC seed 에서
같은 초기 actor·같은 minibatch 열을 소비하고, 새 평가 namespace (81000) 의 paired
280사례에서 BC 직후 그대로 (RL update 0회) scripted c5 limiter 와 함께 평가된다.

  - cosine 대조 = `initialize_from_bc` 직접 호출의 *재구성*. pilot 은 BC 직후
    checkpoint 를 저장하지 않았으므로 검증은 bc_init.json 지표 6개 대조뿐이다.
  - 교사 BC 적합도 (teacher_fit) 와 자기 궤적 성능 (self_trajectory) 은 별도 블록.
  - selection/promote 의미 없음; W6 는 닫혀 있다.

manifest·gate·pairing 경로는 torch-free (로컬 테스트). torch 는 실행 함수 안에서만
import 한다 — CUDA 실행은 그 전에 CUBLAS_WORKSPACE_CONFIG 를 fail-closed 로 검사한다.

    python -m scripts.b0_v3_capturer_f1 --smoke --device cpu
    export CUBLAS_WORKSPACE_CONFIG=:4096:8
    python -u -m scripts.b0_v3_capturer_f1 --run --bc-seed 0 --device cuda
    python -u -m scripts.b0_v3_capturer_f1 --run --bc-seed 1 --device cuda
    python -m scripts.b0_v3_capturer_f1 --readout
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
import pathlib
import time

import numpy as np

from scripts.b0_v3_capturer_f1_manifest import (BC_INIT_KEYS, OBJECTIVES,
                                                 load as load_f1_manifest)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "marl" / "b0_v3_capturer_f1"
PILOT_OUT = ROOT / "artifacts" / "marl" / "b0_v3_pilot"
EXEC_PATHS = ("shepherd", "scripts/b0_v3_capturer_f1.py",
              "scripts/b0_v3_capturer_f1_manifest.py",
              "scripts/b0_v3_capturer_diagnostic.py",
              "scripts/b0_v3_pilot_role_diagnostic.py",
              "artifacts/marl/b0_v3_capturer_f1/manifest.json")
CONTROL, F1 = OBJECTIVES
BC_CANDIDATE = "c0_base"            # bc_init.json 앵커가 있는 pilot run
PAIR_KEYS = ("cell_id", "scenario_id", "chi", "eta", "env_seed", "torch_seed")
PASS, STOP = "PASS_TO_SMALL_RL_CONTRACT", "STOP_F1"


# ------------------------------------------------------------ torch-free ---
def require_cublas(device: str, manifest: dict) -> str | None:
    """CUDA 실행은 결정론 CuBLAS 설정 없이는 거부한다 (torch 사용 전에 부른다)."""
    val = os.environ.get("CUBLAS_WORKSPACE_CONFIG")
    allowed = tuple(manifest["runtime"]["cublas_workspace_config"])
    if str(device).startswith("cuda") and val not in allowed:
        raise SystemExit(f"CUDA run requires CUBLAS_WORKSPACE_CONFIG in {allowed}; "
                         f"got {val!r}")
    return val


def _boundary_cells(b2: dict) -> list:
    # pilot boundary_cells 와 같은 한 줄 (그쪽은 torch 모듈) — 실행 시 대조한다.
    return [c for c in b2["cells"] if c["chi_role"] in ("lo", "hi")]


def scenario_plan(manifest: dict, b2: dict, bc_seed: int, *, n_cells=None,
                  episodes_per_cell=None) -> list:
    from shepherd.scripts.r2a_stage1 import draw_cell_jitter
    ev = manifest["evaluation"]
    seed0, n_pc = int(ev["seed0"]), int(ev["episodes_per_cell"])
    jitter = b2["crn"]["jitter"]
    cells = _boundary_cells(b2)[:n_cells]
    plan = []
    for ci, cell in enumerate(cells):
        for j in range(n_pc if episodes_per_cell is None else episodes_per_cell):
            sid = ci * n_pc + j
            chi, eta = draw_cell_jitter(seed0, sid, cell["chi"], cell["eta"],
                                        ns=ev["namespace"], jc=jitter["chi"],
                                        je=jitter["eta"])
            plan.append({"cell_id": cell["cell_id"], "cell_index": ci,
                         "scenario_id": sid, "chi": chi, "eta": eta,
                         "env_seed": seed0 + sid,
                         "torch_seed": seed0 + 1_000_000 * int(bc_seed) + sid})
    return plan


def pair_keys(rows: list) -> list:
    return [[r[k] for k in PAIR_KEYS] for r in rows]


def signature(rows: list) -> str:
    raw = json.dumps(pair_keys(rows), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def anchor_check(metrics: dict, saved: dict, tol: float) -> dict:
    diffs = {k: {"recorded": float(saved[k]), "reconstructed": float(metrics[k]),
                 "abs_diff": abs(float(saved[k]) - float(metrics[k]))}
             for k in BC_INIT_KEYS}
    exact = all(d["abs_diff"] == 0.0 for d in diffs.values())
    close = all(d["abs_diff"] < tol for d in diffs.values())
    return {"verdict": ("exact-metric-match" if exact else
                        f"metric-close(<{tol:g})" if close else "metric-mismatch"),
            "basis": "bc_init.json metrics only; original post-BC checkpoint "
                     "was never saved (metric-anchored reconstruction)",
            "metrics": diffs}


def count_block(records: list) -> dict:
    c = Counter(r["bin"] for r in records)
    return {"n": len(records), "counts": dict(sorted(c.items())),
            "N": c["N"], "H_illegal": c["H_illegal"],
            "FIRE": sum(bool(r["fire"]) for r in records),
            "clean_crossing_episodes": sum(r["clean_crossings"] > 0 for r in records),
            "clean_crossings_total": sum(int(r["clean_crossings"]) for r in records)}


def apply_gate(counts: dict, integrity: dict, seeds) -> dict:
    """counts[seed][objective] = count_block. 조항은 manifest gate 그대로."""
    clauses = {}
    for s in seeds:
        c, f = counts[s][CONTROL], counts[s][F1]
        clauses[f"seed{s}_clean_crossing_episodes_increase"] = \
            f["clean_crossing_episodes"] > c["clean_crossing_episodes"]
        clauses[f"seed{s}_clean_N_increase"] = f["N"] > c["N"]
    pooled = {o: sum(counts[s][o]["H_illegal"] for s in seeds) for o in OBJECTIVES}
    clauses["pooled_H_illegal_not_increased"] = pooled[F1] <= pooled[CONTROL]
    for k in ("lineage", "pairing", "finite", "completion"):
        clauses[k] = bool(integrity[k])
    return {"clauses": clauses, "pooled_H_illegal": pooled,
            "decision": PASS if all(clauses.values()) else STOP}


def discordance(ctrl: list, f1: list, pred) -> dict:
    out = Counter()
    for a, b in zip(ctrl, f1):
        sa, sb = pred(a), pred(b)
        out["both_success" if sa and sb else "f1_only" if sb else
            "control_only" if sa else "both_fail"] += 1
    return {k: out[k] for k in ("both_success", "f1_only", "control_only", "both_fail")}


def cell_signs(ctrl: list, f1: list) -> dict:
    d = defaultdict(lambda: [0, 0])
    for a, b in zip(ctrl, f1):
        d[a["cell_id"]][0] += int(b["bin"] == "N") - int(a["bin"] == "N")
        d[a["cell_id"]][1] += int(b["clean_crossings"] > 0) - int(a["clean_crossings"] > 0)

    def tally(i):
        v = [x[i] for x in d.values()]
        return {"pos": sum(x > 0 for x in v), "neg": sum(x < 0 for x in v),
                "zero": sum(x == 0 for x in v)}
    return {"delta_N": tally(0), "delta_crossing": tally(1),
            "per_cell": {k: {"dN": v[0], "dcross": v[1]} for k, v in sorted(d.items())}}


def _nan_stat(vals, fn):
    v = [float(x) for x in vals if x is not None and math.isfinite(float(x))]
    return float(fn(v)) if v else None


def angle_summary(records: list) -> dict:
    keys = ("mu_norm_mean", "ang_mean_teacher_deg_mean", "ang_cmd_teacher_deg_mean",
            "ang_att_teacher_deg_mean")
    return {f"{k}__median_over_episodes": _nan_stat([r.get(k) for r in records],
                                                    np.median) for k in keys}


# ------------------------------------------------------------ torch path ---
def unit_axis_mse(mu, teacher_axis):
    """F1 조준 손실 = mean(||μ − â||² / 3). μ 는 clipping 이전 Gaussian mean."""
    import torch.nn.functional as F
    target = teacher_axis / teacher_axis.norm(dim=-1, keepdim=True).clamp_min(1e-9)
    return F.mse_loss(mu, target)


def initialize_from_bc_f1(runner, data: dict, manifest: dict, *, steps: int) -> dict:
    """pilot `initialize_from_bc` 의 사본 — 조준 손실 줄만 다르다 (테스트가 강제)."""
    import torch
    import torch.nn.functional as F
    from shepherd.scripts.b0_v3_mappo_pilot import _last_linear
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
        axis_loss = unit_axis_mse(pred_axis, at[idx])
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


def _digest(tensors: dict) -> str:
    h = hashlib.sha256()
    for k, v in sorted(tensors.items()):
        h.update(k.encode())
        h.update(np.ascontiguousarray(v.detach().cpu().numpy()).tobytes())
    return h.hexdigest()[:16]


def component_hashes(runner) -> dict:
    tr = runner.tr
    out = {"lim_actor": _digest(tr.lim_actor.state_dict()),
           "fin_mean": _digest(tr.fin_actor.mean.state_dict()),
           "fin_fire_logit": _digest(tr.fin_actor.fire_logit.state_dict()),
           "fin_log_std": _digest({"log_std": tr.fin_actor.log_std}),
           "critic": _digest(tr.critic.state_dict()),
           "obs_norm": hashlib.sha256(json.dumps(
               runner.norm.state_dict(), sort_keys=True).encode()).hexdigest()[:16]}
    out["all"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:16]
    return out


def _params_finite(runner) -> bool:
    tr = runner.tr
    return all(bool(p.detach().isfinite().all())
               for m in (tr.lim_actor, tr.fin_actor, tr.critic) for p in m.parameters())


def reconstruct(objective: str, seed: int, device: str, data: dict,
                pilot_manifest: dict, b2: dict):
    """pilot run_combo 순서: seed_everything → PilotRunner → BC 초기화."""
    from shepherd.scripts.b0_v3_mappo_pilot import PilotRunner, initialize_from_bc
    from shepherd.scripts.train_ippo import seed_everything
    seed_everything(int(seed))
    runner = PilotRunner(pilot_manifest, b2, BC_CANDIDATE, seed, device)
    initial = component_hashes(runner)
    # fire head 는 매 step 정확히 xt[idx] 를 받는다 → 입력 해시 = 관측된 minibatch 열.
    h, calls = hashlib.sha256(), [0]

    def hook(_mod, inp):
        h.update(np.ascontiguousarray(inp[0].detach().cpu().numpy()).tobytes())
        calls[0] += 1
    handle = runner.tr.fin_actor.fire_logit.register_forward_pre_hook(hook)
    try:
        fn = initialize_from_bc if objective == CONTROL else initialize_from_bc_f1
        metrics = fn(runner, data, pilot_manifest, steps=runner.bc_steps)
    finally:
        handle.remove()
    return runner, {"metrics": metrics, "initial_state": initial,
                    "minibatch_sequence_hash": h.hexdigest()[:16],
                    "fire_head_forward_calls": calls[0],
                    "post_bc_state": component_hashes(runner)}


def identity_checks(runners: dict, bc: dict) -> dict:
    c, f = bc[CONTROL], bc[F1]
    pc, pf = c["post_bc_state"], f["post_bc_state"]
    return {
        "initial_state_equal": c["initial_state"] == f["initial_state"],
        "minibatch_sequence_equal": (c["minibatch_sequence_hash"]
                                     == f["minibatch_sequence_hash"]
                                     and c["fire_head_forward_calls"]
                                     == f["fire_head_forward_calls"]),
        "fire_head_bit_identical": pc["fin_fire_logit"] == pf["fin_fire_logit"],
        "limiter_actor_identical": pc["lim_actor"] == pf["lim_actor"],
        "critic_identical": pc["critic"] == pf["critic"],
        "fin_log_std_identical": pc["fin_log_std"] == pf["fin_log_std"],
        "obs_norm_identical": pc["obs_norm"] == pf["obs_norm"],
        "limiter_mean_zero": all(b["metrics"]["limiter_mean_zero"] for b in bc.values()),
        "fin_log_std_minus_one": all(
            bool((r.tr.fin_actor.log_std.detach() == -1.0).all())
            for r in runners.values()),
        "axis_head_differs": pc["fin_mean"] != pf["fin_mean"],
    }


def _episode_diag(rows: list, fire_step) -> dict:
    def mean(k):
        return _nan_stat([r.get(k) for r in rows], np.mean)
    at = rows[fire_step] if fire_step is not None and fire_step < len(rows) else None
    return {
        "mu_norm_mean": mean("mu_norm"),
        "ang_mean_teacher_deg_mean": mean("ang_mean_teacher_deg"),
        "ang_cmd_teacher_deg_mean": mean("ang_cmd_teacher_deg"),
        "ang_att_teacher_deg_mean": mean("ang_att_teacher_deg"),
        "v_shot_soft_max": _nan_stat([r["v_soft"] for r in rows], max),
        "net_phase_last": rows[-1]["fsm"] if rows else None,
        "at_fire": None if at is None else {
            "v_shot_soft": at["v_soft"], "v_shot_worst": at["v_worst"],
            "p_feasible": at["p_feasible"], "net_phase": at["fsm"],
            "ang_att_teacher_deg": at["ang_att_teacher_deg"],
            "fire_prob": at.get("fire_prob")},
    }


def evaluate(runner, manifest: dict, b2: dict, plan: list, *, objective: str,
             bc_seed: int, trace_dir: pathlib.Path | None) -> list:
    import torch
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv
    from scripts.b0_v3_capturer_diagnostic import _tracing_policy
    ev = manifest["evaluation"]
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    cells = {c["cell_id"]: c for c in b2["cells"]}
    trace_keys = {tuple(x) for x in manifest["traces"]["scenarios"]}
    base = runner.policy_fn(deterministic=False)
    records = []
    for p in plan:
        sid = p["scenario_id"]
        chi, eta, kw = scenario_kwargs(b2, cells[p["cell_id"]], sid,
                                       seed0=ev["seed0"], seed_ns=ev["namespace"])
        if (chi, eta) != (p["chi"], p["eta"]):
            raise RuntimeError(f"pairing: plan/scenario_kwargs mismatch at sid {sid}")
        stack = build_m4_env(ev["seed0"], sid, **kw)
        env = B0V3CreditEnv(stack.env, runner.credit_spec)
        torch.manual_seed(p["torch_seed"])
        rows: list = []
        r = run_episode(env, stack.scn, stack.lay, seed=p["env_seed"],
                        policy=_tracing_policy(base, runner, env, rows),
                        scripted_roles=("limiter",), limiter_mode="arc",
                        limiter_kw=c5, fire_mode="clean")
        b = partition_bin(r)
        records.append({**p, "bin": b, "label": r.label, "outcome": r.outcome,
                        "fire": r.fire_step is not None, "fire_step": r.fire_step,
                        "clean_crossings": r.clean_crossings,
                        "clean_crossing_episode": r.clean_crossings > 0,
                        "H_illegal": b == "H_illegal", "steps": r.steps,
                        **_episode_diag(rows, r.fire_step)})
        if trace_dir is not None and (p["cell_id"], sid) in trace_keys:
            extra = kw.get("extra_cfg", {})
            cone = {"half_angle": extra.get("viability.cone.half_angle"),
                    "range_max": extra.get("viability.cone.range_max")}
            trace = {
                "schema": "b0-v3-capturer-trace-v1",
                "mode": f"{objective}_bcseed{bc_seed}", "cell_id": p["cell_id"],
                "scenario_id": sid, "chi": chi, "eta": eta,
                "cone_half_angle_rad": cone.get("half_angle"),
                "cone_range_max": cone.get("range_max"),
                "theta_fire": float(getattr(env, "theta_fire", 0.9)),
                "target": [float(x) for x in stack.lay.target],
                "result": {"bin": b, "label": r.label, "outcome": r.outcome,
                           "steps": r.steps, "fire_step": r.fire_step,
                           "clean_crossings": r.clean_crossings,
                           "n_contact": r.n_contact},
                "steps": rows,
            }
            trace_dir.mkdir(parents=True, exist_ok=True)
            (trace_dir / f"trace_{trace['mode']}_{p['cell_id']}_sid{sid}.json"
             ).write_text(json.dumps(trace, ensure_ascii=False), encoding="utf-8")
        if len(records) % 70 == 0:
            print(f"{objective}/s{bc_seed}: {len(records)}/{len(plan)}", flush=True)
    return records


def _prereq(manifest: dict, pilot_manifest: dict, b2: dict) -> dict:
    pre = manifest["prerequisites"]
    readout = json.loads((ROOT / pre["pilot_readout"]).read_text(encoding="utf-8"))
    bc_meta = json.loads((ROOT / pre["bc_dataset"]).read_text(encoding="utf-8"))
    problems = [name for name, ok in (
        ("pilot decision", readout["decision"] == pre["pilot_decision_required"]
         and readout["completion"]["pass"]),
        ("pilot manifest hash", pilot_manifest["manifest_hash"]
         == pre["pilot_manifest_hash"] == readout["manifest_hash"]),
        ("b0 hash", b2["b0_v3_hash"] == pre["b0_v3_hash"]
         == pilot_manifest["prerequisites"]["b0_v3_hash"]),
        ("bc dataset hash", bc_meta["dataset_hash"] == pre["bc_dataset_hash"]),
        ("bc code tree", bc_meta["code_tree"] == pre["bc_code_tree"]),
        ("bc steps", pilot_manifest["initialization"]["bc_steps"]
         == manifest["bc"]["unchanged_from_pilot"]["bc_steps"]),
    ) if not ok]
    if problems:
        raise SystemExit(f"capturer-F1 prerequisite failure: {problems}")
    return bc_meta


def run_seed(bc_seed: int, device: str, *, smoke: bool = False,
             out_root: pathlib.Path = OUT) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_pilot_manifest import load as load_pilot_manifest
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest = load_f1_manifest()
    cublas = require_cublas(device, manifest)          # torch 사용 전
    pilot_manifest, b2 = load_pilot_manifest(), load_b2_manifest()
    if bc_seed not in manifest["bc"]["actor_seeds"]:
        raise ValueError("bc_seed is outside the sealed manifest")
    _prereq(manifest, pilot_manifest, b2)
    dirty = git_dirty(EXEC_PATHS)
    if dirty and not smoke:
        raise SystemExit(f"dirty execution code; run refused: {dirty}")
    run_dir = out_root / ("smoke" if smoke else "") / f"seed{bc_seed}"
    if not smoke and (run_dir / ".done").exists():
        raise SystemExit(f"completed run exists: {run_dir}")

    import torch
    from scripts.b0_v3_capturer_diagnostic import teacher_fit
    from shepherd.scripts.b0_v3_mappo_pilot import BC_FILE, boundary_cells, load_bc
    data, bc_meta = load_bc(BC_FILE, pilot_manifest)   # hash + code_tree 봉인 검사
    if (bc_meta["dataset_hash"] != manifest["prerequisites"]["bc_dataset_hash"]
            or bc_meta["code_tree"] != manifest["prerequisites"]["bc_code_tree"]):
        raise SystemExit("BC dataset lineage mismatch")
    if [c["cell_id"] for c in boundary_cells(b2)] != \
            [c["cell_id"] for c in _boundary_cells(b2)]:
        raise SystemExit("boundary cell order mismatch")
    t0 = time.time()

    # 1) BC — 두 objective, 같은 seed·초기 상태·minibatch 열
    runners, bc = {}, {}
    for obj in OBJECTIVES:
        runners[obj], bc[obj] = reconstruct(obj, bc_seed, device, data,
                                            pilot_manifest, b2)
    checks = identity_checks(runners, bc)
    if not all(checks.values()):
        raise SystemExit(f"one-factor identity broken: {checks}")
    anchor_spec = manifest["bc"]["anchor"]
    saved = json.loads((PILOT_OUT / BC_CANDIDATE / f"seed{bc_seed}" / "bc_init.json")
                       .read_text(encoding="utf-8"))
    anchor = anchor_check(bc[CONTROL]["metrics"], saved,
                          float(anchor_spec["tolerance_abs"]))
    print(f"anchor s{bc_seed}: {anchor['verdict']}", flush=True)
    if anchor["verdict"] == "metric-mismatch" and not smoke:
        raise SystemExit(f"cosine control does not match bc_init.json: {anchor}")
    spec = runners[CONTROL].credit_spec
    cred = manifest["evaluation"]["credit"]
    if ((spec.gamma, spec.beta, spec.r_clean, spec.r_illegal)
            != (cred["gamma"], cred["beta"], cred["r_clean"], cred["r_illegal"])
            or spec.manifest()["cuts"] != cred["cuts"]):
        raise SystemExit("credit spec differs from manifest")

    teacher = {obj: {"bc_metrics": bc[obj]["metrics"],
                     "fit_on_teacher_states": teacher_fit(
                         runners[obj].tr, runners[obj].norm, data,
                         runners[obj].tr.device),
                     "initial_state": bc[obj]["initial_state"],
                     "post_bc_state": bc[obj]["post_bc_state"],
                     "minibatch_sequence_hash": bc[obj]["minibatch_sequence_hash"]}
               for obj in OBJECTIVES}
    teacher[CONTROL]["anchor"] = anchor

    # 2) 자기 궤적 paired 평가 (BC 직후, RL update 없음)
    plan = scenario_plan(manifest, b2, bc_seed, n_cells=2 if smoke else None,
                         episodes_per_cell=1 if smoke else None)
    self_traj, sigs = {}, {}
    for obj in OBJECTIVES:
        recs = evaluate(runners[obj], manifest, b2, plan, objective=obj,
                        bc_seed=bc_seed, trace_dir=run_dir / "traces")
        if pair_keys(recs) != pair_keys(plan):
            raise SystemExit(f"pairing violated for {obj}")
        sigs[obj] = signature(recs)
        self_traj[obj] = {**count_block(recs), **angle_summary(recs), "records": recs}
        print(f"{obj}/s{bc_seed}: done n={len(recs)}", flush=True)

    finite = (all(_params_finite(r) for r in runners.values())
              and all(math.isfinite(float(bc[o]["metrics"][k]))
                      for o in OBJECTIVES for k in BC_INIT_KEYS)
              and all(r["mu_norm_mean"] is not None
                      for o in OBJECTIVES for r in self_traj[o]["records"]))
    if not finite:
        raise SystemExit("non-finite parameters, BC metrics or pointing means")

    summary = {
        "schema": "b0-v3-capturer-f1-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS",
        "scope": manifest["scope"],
        "bc_seed": bc_seed,
        "provenance": {
            "manifest_hash": manifest["manifest_hash"],
            "b0_v3_hash": b2["b0_v3_hash"],
            "bc_dataset_hash": bc_meta["dataset_hash"],
            "bc_code_tree": bc_meta["code_tree"],
            "code_commit": git_commit(), "code_dirty_scoped": dirty,
            "cublas_workspace_config": cublas,
            "torch_version": torch.__version__, "cuda_version": torch.version.cuda,
            "device": device,
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "deterministic_warn_only":
                torch.is_deterministic_algorithms_warn_only_enabled(),
            "rl_updates": 0,
        },
        "identity_checks": checks,
        "teacher_fit": teacher,
        "self_trajectory": self_traj,
        "scenario_signature": {"plan": signature(plan), **sigs},
        "finite": finite,
        "elapsed_s": round(time.time() - t0, 2),
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if not smoke:
        (run_dir / ".done").write_text(json.dumps(
            {"manifest_hash": manifest["manifest_hash"],
             "code_commit": summary["provenance"]["code_commit"]}), encoding="utf-8")
    for obj in OBJECTIVES:
        s = self_traj[obj]
        print(f"{obj}/s{bc_seed}: N={s['N']} cross={s['clean_crossing_episodes']} "
              f"FIRE={s['FIRE']} H={s['H_illegal']}", flush=True)
    return summary


# ----------------------------------------------------------------- readout ---
def readout(out_root: pathlib.Path = OUT) -> dict:
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_f1_manifest(), load_b2_manifest()
    seeds = manifest["bc"]["actor_seeds"]
    pre = manifest["prerequisites"]
    runs = {}
    for s in seeds:
        d = out_root / f"seed{s}"
        if not ((d / "summary.json").exists() and (d / ".done").exists()):
            raise SystemExit(f"missing run: {d}")
        runs[s] = json.loads((d / "summary.json").read_text(encoding="utf-8"))

    allowed = manifest["runtime"]["cublas_workspace_config"]
    lineage = len({r["provenance"]["code_commit"] for r in runs.values()}) == 1
    pairing, finite, n_total = True, True, 0
    for s, r in runs.items():
        pv = r["provenance"]
        lineage &= (r["schema"] == "b0-v3-capturer-f1-run-v1"
                    and r["status"] == "PASS" and r["bc_seed"] == s
                    and pv["manifest_hash"] == manifest["manifest_hash"]
                    and pv["b0_v3_hash"] == pre["b0_v3_hash"]
                    and pv["bc_dataset_hash"] == pre["bc_dataset_hash"]
                    and pv["bc_code_tree"] == pre["bc_code_tree"]
                    and not pv["code_dirty_scoped"] and pv["rl_updates"] == 0
                    and (not str(pv["device"]).startswith("cuda")
                         or pv["cublas_workspace_config"] in allowed)
                    and all(r["identity_checks"].values())
                    and r["teacher_fit"][CONTROL]["anchor"]["verdict"]
                    != "metric-mismatch")
        expected = pair_keys(scenario_plan(manifest, b2, s))
        for o in OBJECTIVES:
            recs = r["self_trajectory"][o]["records"]
            n_total += len(recs)
            pairing &= pair_keys(recs) == expected
            finite &= r["finite"] and all(
                x["mu_norm_mean"] is not None and math.isfinite(x["mu_norm_mean"])
                for x in recs)
    completion = n_total == manifest["evaluation"]["episodes_total"]
    integrity = {"lineage": bool(lineage), "pairing": bool(pairing),
                 "finite": bool(finite), "completion": bool(completion)}

    counts, per_seed = {}, {}
    for s, r in runs.items():
        recs = {o: r["self_trajectory"][o]["records"] for o in OBJECTIVES}
        counts[s] = {o: count_block(recs[o]) for o in OBJECTIVES}
        per_seed[f"seed{s}"] = {
            "self_trajectory": {o: {**counts[s][o], **angle_summary(recs[o])}
                                for o in OBJECTIVES},
            "teacher_fit": {o: {"bc_metrics": r["teacher_fit"][o]["bc_metrics"],
                                "fit_on_teacher_states":
                                    r["teacher_fit"][o]["fit_on_teacher_states"]}
                            for o in OBJECTIVES},
            "anchor_verdict": r["teacher_fit"][CONTROL]["anchor"]["verdict"],
            "paired_discordance": {
                "clean_N": discordance(recs[CONTROL], recs[F1],
                                       lambda x: x["bin"] == "N"),
                "clean_crossing_episode": discordance(
                    recs[CONTROL], recs[F1], lambda x: x["clean_crossings"] > 0)},
            "cell_signs": cell_signs(recs[CONTROL], recs[F1]),
        }
    gate = apply_gate(counts, integrity, seeds)
    out = {"schema": "b0-v3-capturer-f1-readout-v1",
           "manifest_hash": manifest["manifest_hash"], "scope": manifest["scope"],
           "integrity": integrity, "per_seed": per_seed, "gate": gate,
           "decision": gate["decision"], "promotion": manifest["promotion"]}
    (out_root / "readout.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"integrity": integrity, "gate": gate,
                      "promotion": out["promotion"]}, ensure_ascii=False, indent=2))
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--readout", action="store_true")
    p.add_argument("--bc-seed", type=int)
    p.add_argument("--device", default="cuda")
    a = p.parse_args(argv)
    if a.smoke:
        run_seed(0, a.device, smoke=True)
    elif a.run:
        if a.bc_seed is None:
            p.error("--run requires --bc-seed")
        run_seed(a.bc_seed, a.device)
    else:
        readout()


if __name__ == "__main__":
    main()
