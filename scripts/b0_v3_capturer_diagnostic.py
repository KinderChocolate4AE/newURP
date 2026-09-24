"""Capturer bottleneck diagnostic on the sealed B0 v3 pilot (post-hoc).

Answers, mechanism-only (docs/110 NO_SELECTION is not amended):
  1. BC-직후 정책의 재구성 — 봉인 BC dataset + manifest seed에서 run_combo와 동일한
     호출 순서로 다시 만든다. **원본 BC-직후 checkpoint는 pilot이 저장하지 않았다**;
     검증 가능한 앵커는 run_dir의 bc_init.json 지표 6개뿐이므로, 재구성은 그 지표와의
     일치로만 등급을 매긴다 (exact-metric-match / approximate). 허위 "원본"을 만들지
     않는다.
  2. 교사 데이터 적합도 행렬 — {BC-직후 weights, 최종 weights} × {BC-시점 norm,
     최종 norm}. 최종 실패가 weight 변화인지 normalizer 통계 이동인지 분리한다.
     (BC 이후 RunningNorm은 on-policy 32,768 step으로 계속 갱신돼 BC 표본 597개의
     비중이 ~1.8%로 희석된다 — 같은 weight라도 입력 인코딩이 달라진다.)
  3. Paired on-policy 평가 — 봉인 평가 scenario(sid = ci*10+j, torch seed 61000+sid)
     의 재사용. **기제 진단 전용**이며 후보 재선택·문턱 변경에 쓰지 않는다.
  4. 시간축 trace — 관측·조준 mean/표본/실제 자세·교사축과의 각도·FIRE logit/확률/
     발사·v_shot triple·clean crossing·net phase를 스텝별 JSON으로 남긴다.
     렌더는 torch-free `scripts/render_capturer_traces.py`.

sealed tree 불변: 이 파일은 shepherd/ 밖에 있고, BC dataset lineage guard(load_bc의
code_tree 검사)가 실행 시점에 shepherd tree가 봉인 생산 코드와 같음을 강제한다.

실행 (랩 서버, torch venv):
    python -m scripts.b0_v3_capturer_diagnostic --candidate c0_base --seed 0 --device cuda
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from shepherd.m4_env import build_m4_env
from shepherd.provenance import git_commit, git_dirty
from shepherd.scripts.b0_v3_mappo_pilot import (BC_FILE, OUT, PilotRunner,
                                                boundary_cells,
                                                initialize_from_bc, load_bc,
                                                scenario_kwargs)
from shepherd.scripts.b0_v3_pilot_manifest import load as load_manifest
from shepherd.scripts.b2_manifest import load as load_b2_manifest
from shepherd.scripts.mission_rollout import partition_bin, run_episode
from shepherd.scripts.train_ippo import seed_everything
from shepherd.train.b0_v3_credit import B0V3CreditEnv
from shepherd.train.bc_aim import teacher_axis
from shepherd.train.obs_norm import RunningNorm
from scripts.b0_v3_pilot_role_diagnostic import _mean_axis_policy, _shepherd_tree

ROOT = Path(__file__).resolve().parents[1]
DIAG = OUT / "diagnostic"
EXEC_PATHS = ("shepherd", "scripts/b0_v3_capturer_diagnostic.py",
              "scripts/b0_v3_pilot_role_diagnostic.py")
# BC 성공 셀 중 slice/행이 갈리는 4곳; trace 기본값 (선언, 결과 무관).
TRACE_CELLS = ("r00c1", "r00c2", "r07c1", "r13c2")
BC_INIT_KEYS = ("loss", "axis_loss", "fire_loss", "mean_axis_cosine",
                "fire_tpr", "fire_tnr")


# ---------------------------------------------------------------- helpers ---
def _sd_hash(tr) -> str:
    h = hashlib.sha256()
    for name, module in (("lim", tr.lim_actor), ("fin", tr.fin_actor),
                         ("critic", tr.critic)):
        for k, v in sorted(module.state_dict().items()):
            h.update(f"{name}.{k}".encode())
            h.update(np.ascontiguousarray(v.detach().cpu().numpy()).tobytes())
    return h.hexdigest()[:16]


def _angle_deg(u, v) -> float:
    u = np.asarray(u, float).reshape(-1)
    v = np.asarray(v, float).reshape(-1)
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-12 or nv < 1e-12:
        return float("nan")
    c = float(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def _clone_norm(norm: RunningNorm) -> RunningNorm:
    out = RunningNorm(norm.dim)
    out.load_state_dict(norm.state_dict())
    return out


@contextmanager
def _swapped_norm(runner, norm: RunningNorm):
    """policy_fn 클로저는 self.norm을 호출 시점에 읽으므로 스왑이 곧 적용된다."""
    original = runner.norm
    runner.norm = norm
    try:
        yield
    finally:
        runner.norm = original


# ---------------------------------------------------------- reconstruction ---
def reconstruct_bc(manifest, b2, candidate: str, seed: int, device: str,
                   data: dict, *, bc_steps=None):
    """run_combo와 동일한 순서: seed_everything → PilotRunner → initialize_from_bc.

    이 사이에는 torch RNG 소비가 없으므로(모듈 생성은 PilotRunner 안, BC는 내부에서
    다시 torch.manual_seed) 같은 device에서는 pilot의 BC-직후 상태를 재생한다.
    """
    seed_everything(int(seed))
    runner = PilotRunner(manifest, b2, candidate, seed, device)
    metrics = initialize_from_bc(runner, data, manifest,
                                 steps=runner.bc_steps if bc_steps is None
                                 else int(bc_steps))
    return runner, metrics


def recon_report(manifest, b2, candidate, seed, device, data, saved_bc: dict) -> tuple:
    r1, m1 = reconstruct_bc(manifest, b2, candidate, seed, device, data)
    h1 = _sd_hash(r1.tr)
    r2, _ = reconstruct_bc(manifest, b2, candidate, seed, device, data)
    deterministic = h1 == _sd_hash(r2.tr)

    diffs = {k: {"recorded": float(saved_bc[k]), "reconstructed": float(m1[k]),
                 "abs_diff": abs(float(saved_bc[k]) - float(m1[k]))}
             for k in BC_INIT_KEYS}
    exact = all(d["abs_diff"] == 0.0 for d in diffs.values())
    close = all(d["abs_diff"] < 1e-6 for d in diffs.values())
    verdict = ("exact-metric-match" if exact
               else "metric-close(<1e-6)" if close else "metric-mismatch")
    report = {
        "original_bc_checkpoint": ("pilot이 BC-직후 checkpoint를 저장하지 않았다. "
                                   "bit-identical 원본은 존재하지 않으며, 아래 검증은 "
                                   "bc_init.json에 기록된 지표 6개와의 대조뿐이다"),
        "verdict": verdict,
        "bit_identical_claim": False,
        "metric_validation": diffs,
        "limiter_mean_zero": bool(m1["limiter_mean_zero"]),
        "double_reconstruction_identical": bool(deterministic),
        "state_hash": h1,
        "device": device,
        "torch_version": torch.__version__,
        "note": ("verdict가 exact/close가 아니면 이후의 모든 BC-직후 수치는 "
                 "approximate-reconstruction으로 읽는다 (원본 실행 device=cuda)"),
    }
    return r1, report


# ------------------------------------------------------------- teacher fit ---
def teacher_fit(tr, norm: RunningNorm, data: dict, device, *, mc_draws=64) -> dict:
    X = np.asarray(data["X"], np.float32)
    A = np.asarray(data["axis"], np.float32)
    yf = np.asarray(data["fire"], np.float32).reshape(-1, 1)
    xn = norm.normalize(X)
    with torch.no_grad():
        xt = torch.as_tensor(xn, device=device)
        mu = tr.fin_actor.mean(xt).cpu().numpy()
        logit = tr.fin_actor.fire_logit(xt).cpu().numpy()
        sigma = tr.fin_actor.log_std.clamp(-5.0, 2.0).exp().cpu().numpy()

    mu_n = mu / np.maximum(np.linalg.norm(mu, axis=1, keepdims=True), 1e-9)
    a_n = A / np.maximum(np.linalg.norm(A, axis=1, keepdims=True), 1e-9)
    cos = np.sum(mu_n * a_n, axis=1)
    ang = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
    mu_norm = np.linalg.norm(mu, axis=1)

    # 표본 조준의 기대 각오차: axis ~ N(mu, sigma^2). BC의 cosine 손실은 |mu|를
    # 키우지 않으므로 SNR = |mu|/sigma 가 표본 방향 오차를 지배한다.
    rng = np.random.default_rng(0)
    eps = rng.standard_normal((mc_draws, 3)).astype(np.float32) * sigma[None, :3]
    samp = mu[:, None, :] + eps[None, :, :]
    samp_n = samp / np.maximum(np.linalg.norm(samp, axis=2, keepdims=True), 1e-9)
    cos_s = np.clip(np.sum(samp_n * mu_n[:, None, :], axis=2), -1.0, 1.0)
    ang_s = np.degrees(np.arccos(cos_s))

    prob = 1.0 / (1.0 + np.exp(-logit))
    pos = yf.reshape(-1) > 0.5
    yhat = prob.reshape(-1) >= 0.5
    return {
        "n": int(len(X)),
        "mean_axis_cosine": float(cos.mean()),
        "axis_angle_deg_p50": float(np.percentile(ang, 50)),
        "axis_angle_deg_p90": float(np.percentile(ang, 90)),
        "mean_mu_norm": float(mu_norm.mean()),
        "p10_mu_norm": float(np.percentile(mu_norm, 10)),
        "sigma_axis": [float(s) for s in sigma[:3]],
        "sampled_axis_angle_to_mean_deg_p50": float(np.percentile(ang_s, 50)),
        "sampled_axis_angle_to_mean_deg_p90": float(np.percentile(ang_s, 90)),
        "fire_tpr": float((yhat[pos]).mean()) if pos.any() else float("nan"),
        "fire_tnr": float((~yhat[~pos]).mean()) if (~pos).any() else float("nan"),
        "fire_bce": float(F.binary_cross_entropy_with_logits(
            torch.as_tensor(logit), torch.as_tensor(yf)).item()),
    }


def norm_shift(norm_a: RunningNorm, norm_b: RunningNorm, X: np.ndarray,
               top_k: int = 8) -> dict:
    za = norm_a.normalize(X).astype(np.float64)
    zb = norm_b.normalize(X).astype(np.float64)
    d = np.abs(za - zb)
    per_dim = d.mean(axis=0)
    order = np.argsort(per_dim)[::-1][:top_k]
    return {
        "count_a": float(norm_a.count), "count_b": float(norm_b.count),
        "mean_abs_z_shift": float(per_dim.mean()),
        "max_abs_z_shift": float(d.max()),
        "top_shifted_dims": [{"dim": int(i), "mean_abs_shift": float(per_dim[i])}
                             for i in order],
    }


# ------------------------------------------------------------- paired eval ---
def _episode_env(manifest, b2, cell, sid, credit_spec):
    ev = manifest["evaluation"]
    chi, eta, kw = scenario_kwargs(b2, cell, sid, seed0=ev["seed0"],
                                   seed_ns=ev["seed_ns"])
    stack = build_m4_env(ev["seed0"], sid, **kw)
    extra = kw.get("extra_cfg", {})
    cone = {"half_angle": extra.get("viability.cone.half_angle"),
            "range_max": extra.get("viability.cone.range_max")}
    return chi, eta, stack, B0V3CreditEnv(stack.env, credit_spec), cone


def eval_mode(runner, manifest, b2, *, policy, scripted_roles, cells,
              episodes_per_cell: int, c5: dict) -> dict:
    ev = manifest["evaluation"]
    sealed_n_pc = int(ev["episodes_per_cell"])
    rows = []
    for ci, cell in enumerate(cells):
        for j in range(episodes_per_cell):
            sid = ci * sealed_n_pc + j       # 봉인 280의 정확한 부분집합
            chi, eta, stack, env, _ = _episode_env(
                manifest, b2, cell, sid, runner.credit_spec)
            torch.manual_seed(int(ev["seed0"]) + sid)
            if scripted_roles:
                r = run_episode(env, stack.scn, stack.lay,
                                seed=int(ev["seed0"]) + sid, policy=policy,
                                scripted_roles=scripted_roles,
                                limiter_mode="arc", limiter_kw=c5,
                                fire_mode="clean")
            else:  # pilot evaluate()와 동일 인자 (fire_mode는 policy 경로에서 관성)
                r = run_episode(env, stack.scn, stack.lay,
                                seed=int(ev["seed0"]) + sid, policy=policy,
                                fire_mode="never", baseline_commit=False)
            rows.append({"cell_id": cell["cell_id"], "scenario_id": sid,
                         "chi": chi, "eta": eta, "bin": partition_bin(r),
                         "fire": r.fire_step is not None,
                         "clean_crossings": r.clean_crossings,
                         "steps": r.steps})
    counts = Counter(r["bin"] for r in rows)
    n = len(rows)
    return {"n": n, "counts": dict(sorted(counts.items())),
            "p_N": counts["N"] / n, "p_H_illegal": counts["H_illegal"] / n,
            "p_FIRE": sum(r["fire"] for r in rows) / n,
            "episodes_with_clean_crossing": sum(r["clean_crossings"] > 0
                                                for r in rows),
            "records": rows}


def paired_eval(final_runner, recon_runner, manifest, b2, *, cells,
                episodes_per_cell: int) -> dict:
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    bc_norm = _clone_norm(recon_runner.norm)
    final_norm = _clone_norm(final_runner.norm)
    out = {}

    def run(name, runner, policy_builder, roles):
        out[name] = eval_mode(runner, manifest, b2, policy=policy_builder(),
                              scripted_roles=roles, cells=cells,
                              episodes_per_cell=episodes_per_cell, c5=c5)
        print(f"{name}: N={out[name]['counts'].get('N', 0)}/{out[name]['n']} "
              f"FIRE={round(out[name]['p_FIRE'] * out[name]['n'])} "
              f"cross={out[name]['episodes_with_clean_crossing']}", flush=True)

    run("final_scripted_limiter", final_runner,
        lambda: final_runner.policy_fn(deterministic=False), ("limiter",))
    run("bcrecon_scripted_limiter", recon_runner,
        lambda: recon_runner.policy_fn(deterministic=False), ("limiter",))
    run("bcrecon_scripted_limiter_mean_axis", recon_runner,
        lambda: _mean_axis_policy(recon_runner), ("limiter",))
    run("bcrecon_learned_limiter", recon_runner,
        lambda: recon_runner.policy_fn(deterministic=False), ())
    with _swapped_norm(final_runner, bc_norm):
        run("final_weights_bc_norm_scripted", final_runner,
            lambda: final_runner.policy_fn(deterministic=False), ("limiter",))
    with _swapped_norm(recon_runner, final_norm):
        run("bcrecon_weights_final_norm_scripted", recon_runner,
            lambda: recon_runner.policy_fn(deterministic=False), ("limiter",))
    return out


# ------------------------------------------------------------------ traces ---
def _tracing_policy(base_policy, runner, env, rows: list):
    """base_policy를 감싸 스텝별 진단을 기록한다. 추가 forward는 RNG를 소비하지
    않으므로(표본 없음) base_policy의 행동 스트림은 불변이다."""
    fid = env.finisher_id

    def policy(obs, flags):
        lims, fin, att = env._states()
        row = {
            "t": len(rows),
            "fsm": str(getattr(env.fsm.state, "value", env.fsm.state)),
            "p_att": env._p(att).tolist(), "v_att": env._v(att).tolist(),
            "p_fin": env._p(fin).tolist(), "e_fin": env._e(fin).tolist(),
            "p_lims": [env._p(s).tolist() for s in lims],
            "teacher_axis": teacher_axis(env).tolist(),
            "v_soft": float(np.asarray(obs).reshape(-1)[-5]),
            "v_worst": float(np.asarray(obs).reshape(-1)[-4]),
            "p_feasible": float(np.asarray(obs).reshape(-1)[-3]),
            "clean_prev": bool(flags.get("clean_net_threshold_crossed", False)),
            "fire_event_prev": bool(flags.get("fire_event", False)),
            "obs": [round(float(x), 6) for x in np.asarray(obs).reshape(-1)],
        }
        ta = np.asarray(row["teacher_axis"])
        row["ang_att_teacher_deg"] = _angle_deg(row["e_fin"], ta)
        acts = {}
        if base_policy is not None:
            acts = dict(base_policy(obs, flags))
            if runner is not None and fid in acts:
                nobs = runner.norm.normalize(np.asarray(obs, np.float32))
                with torch.no_grad():
                    t = torch.as_tensor(nobs[None, :], device=runner.tr.device)
                    mu = runner.tr.fin_actor.mean(t)[0].cpu().numpy()
                    logit = float(runner.tr.fin_actor.fire_logit(t)[0, 0].item())
                fa = np.asarray(acts[fid], np.float32)
                row.update({
                    "mu": mu.tolist(), "mu_norm": float(np.linalg.norm(mu)),
                    "fire_logit": logit,
                    "fire_prob": float(1.0 / (1.0 + np.exp(-logit))),
                    "cmd_axis": fa[:3].tolist(),
                    "fire_bit": float(fa[4]) if fa.shape[0] >= 5 else None,
                    "ang_mean_teacher_deg": _angle_deg(mu, ta),
                    "ang_cmd_teacher_deg": _angle_deg(fa[:3], ta),
                })
        rows.append(row)
        return acts

    return policy


def collect_traces(final_runner, recon_runner, manifest, b2, *, cells,
                   out_dir: Path) -> list:
    ev = manifest["evaluation"]
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    n_pc = int(ev["episodes_per_cell"])
    by_id = {c["cell_id"]: (ci, c) for ci, c in enumerate(boundary_cells(b2))}
    modes = (
        ("scripted_both", None, None, ("limiter", "finisher")),
        ("bcrecon_scripted_limiter", recon_runner,
         lambda r: r.policy_fn(deterministic=False), ("limiter",)),
        ("final_scripted_limiter", final_runner,
         lambda r: r.policy_fn(deterministic=False), ("limiter",)),
    )
    written = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for cell_id in cells:
        ci, cell = by_id[cell_id]
        sid = ci * n_pc  # j=0: 봉인 평가의 첫 scenario
        for name, runner, builder, roles in modes:
            spec = (recon_runner or final_runner).credit_spec
            chi, eta, stack, env, cone = _episode_env(manifest, b2, cell, sid, spec)
            torch.manual_seed(int(ev["seed0"]) + sid)
            rows: list = []
            base = builder(runner) if builder else None
            policy = _tracing_policy(base, runner, env, rows)
            r = run_episode(env, stack.scn, stack.lay,
                            seed=int(ev["seed0"]) + sid, policy=policy,
                            scripted_roles=roles, limiter_mode="arc",
                            limiter_kw=c5, fire_mode="clean")
            trace = {
                "schema": "b0-v3-capturer-trace-v1",
                "mode": name, "cell_id": cell_id, "scenario_id": sid,
                "chi": chi, "eta": eta,
                "cone_half_angle_rad": cone.get("half_angle"),
                "cone_range_max": cone.get("range_max"),
                "theta_fire": float(getattr(env, "theta_fire", 0.9)),
                "target": [float(x) for x in stack.lay.target],
                "result": {"bin": partition_bin(r), "label": r.label,
                           "outcome": r.outcome, "steps": r.steps,
                           "fire_step": r.fire_step,
                           "clean_crossings": r.clean_crossings,
                           "n_contact": r.n_contact},
                "steps": rows,
            }
            path = out_dir / f"trace_{name}_{cell_id}_sid{sid}.json"
            path.write_text(json.dumps(trace, ensure_ascii=False),
                            encoding="utf-8")
            written.append(str(path.relative_to(ROOT)))
            print(f"trace {name}/{cell_id}: {trace['result']['bin']} "
                  f"steps={r.steps} cross={r.clean_crossings}", flush=True)
    return written


# -------------------------------------------------------------------- main ---
def diagnose(candidate: str, seed: int, device: str, *,
             episodes_per_cell: int = 10, skip_eval=False, skip_traces=False,
             out: Path | None = None) -> dict:
    manifest, b2 = load_manifest(), load_b2_manifest()
    dirty = git_dirty(EXEC_PATHS)
    if dirty:
        raise RuntimeError(f"diagnostic execution code is dirty: {dirty}")
    data, bc_meta = load_bc(BC_FILE, manifest)   # code_tree 봉인 검사 포함
    if _shepherd_tree() != bc_meta["code_tree"]:
        raise RuntimeError("shepherd tree differs from sealed BC producer")
    readout = json.loads((OUT / "readout.json").read_text(encoding="utf-8"))
    if (readout["manifest_hash"] != manifest["manifest_hash"]
            or not readout["completion"]["pass"]
            or readout["decision"] != "NO_SELECTION"):
        raise RuntimeError("requires the completed NO_SELECTION pilot")
    run_dir = OUT / candidate / f"seed{seed}"
    saved = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if (saved["manifest_hash"] != manifest["manifest_hash"]
            or saved["bc_dataset_hash"] != bc_meta["dataset_hash"]):
        raise RuntimeError("saved pilot run lineage mismatch")
    target = out or DIAG / f"capturer_diag_{candidate}_s{seed}.json"
    if target.exists():
        raise FileExistsError(f"diagnostic output exists: {target}")

    # 1) BC-직후 재구성 (원본과의 대조는 bc_init.json 지표뿐 — 위 docstring)
    recon_runner, recon = recon_report(manifest, b2, candidate, seed, device,
                                       data, saved["bc_init"])
    DIAG.mkdir(parents=True, exist_ok=True)
    recon_ckpt = DIAG / f"bc_recon_{candidate}_s{seed}.pt"
    torch.save({"schema": "b0-v3-bc-reconstruction-v1",
                "status": "reconstruction; NOT the (never-saved) original",
                "verdict": recon["verdict"],
                "lim_actor": recon_runner.tr.lim_actor.state_dict(),
                "fin_actor": recon_runner.tr.fin_actor.state_dict(),
                "critic": recon_runner.tr.critic.state_dict(),
                "obs_norm": recon_runner.norm.state_dict()}, recon_ckpt)

    # 2) 최종 checkpoint 복원
    final_runner = PilotRunner(manifest, b2, candidate, seed, device)
    restored = final_runner.restore(run_dir)
    if restored != manifest["training"]["total_env_steps"]:
        raise RuntimeError(f"checkpoint step mismatch: {restored}")
    ckpt_sha = hashlib.sha256(
        (run_dir / "ckpt_mappo_latest.pt").read_bytes()).hexdigest()

    # 3) 교사 적합도 행렬 + normalizer 이동
    bc_norm = _clone_norm(recon_runner.norm)
    final_norm = _clone_norm(final_runner.norm)
    dev = final_runner.tr.device
    fit = {
        "bc_weights__bc_norm": teacher_fit(recon_runner.tr, bc_norm, data, dev),
        "bc_weights__final_norm": teacher_fit(recon_runner.tr, final_norm, data, dev),
        "final_weights__bc_norm": teacher_fit(final_runner.tr, bc_norm, data, dev),
        "final_weights__final_norm": teacher_fit(final_runner.tr, final_norm, data, dev),
    }
    shift = norm_shift(bc_norm, final_norm, np.asarray(data["X"], np.float32))

    # 4) paired on-policy 평가 (봉인 280 재사용 — 진단 전용)
    cells = boundary_cells(b2)
    evals = {} if skip_eval else paired_eval(final_runner, recon_runner,
                                             manifest, b2, cells=cells,
                                             episodes_per_cell=episodes_per_cell)
    cross = None
    rs_path = OUT / f"role_swap_{candidate}_seed{seed}_e10.json"
    if evals and rs_path.exists() and episodes_per_cell == 10:
        rs = json.loads(rs_path.read_text(encoding="utf-8"))
        want = rs["modes"]["scripted_limiter_learned_finisher"]["counts"]
        got = evals["final_scripted_limiter"]["counts"]
        cross = {"role_swap_counts": want, "this_run_counts": got,
                 "match": want == got}

    # 5) traces (viz-first: 판독은 그림 먼저)
    traces = [] if skip_traces else collect_traces(
        final_runner, recon_runner, manifest, b2, cells=list(TRACE_CELLS),
        out_dir=DIAG / "traces")

    report = {
        "schema": "b0-v3-capturer-diagnostic-v1",
        "scope": ("post-hoc mechanism diagnostic on the sealed pilot; "
                  "reuses the sealed 280 evaluation cases for diagnosis only; "
                  "does not amend NO_SELECTION or any threshold"),
        "manifest_hash": manifest["manifest_hash"],
        "b0_v3_hash": b2["b0_v3_hash"],
        "candidate": candidate, "seed": seed,
        "evaluator_commit": git_commit(),
        "shepherd_code_tree": _shepherd_tree(),
        "bc_dataset_hash": bc_meta["dataset_hash"],
        "checkpoint_sha256": ckpt_sha, "checkpoint_steps": restored,
        "reconstruction": recon,
        "reconstruction_ckpt": str(recon_ckpt.relative_to(ROOT)),
        "teacher_fit_matrix": fit,
        "norm_shift_on_teacher_states": shift,
        "paired_eval": evals,
        "role_swap_cross_check": cross,
        "traces": traces,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"saved: {target}", flush=True)
    return report


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", default="c0_base")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--device", default="cuda")
    p.add_argument("--episodes-per-cell", type=int, default=10)
    p.add_argument("--skip-eval", action="store_true")
    p.add_argument("--skip-traces", action="store_true")
    p.add_argument("--out", type=Path)
    a = p.parse_args(argv)
    diagnose(a.candidate, a.seed, a.device,
             episodes_per_cell=a.episodes_per_cell,
             skip_eval=a.skip_eval, skip_traces=a.skip_traces, out=a.out)


if __name__ == "__main__":
    main()
