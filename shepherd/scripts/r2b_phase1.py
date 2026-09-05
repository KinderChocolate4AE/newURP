"""R2b Phase 1 — server benchmark · C-budget branch seal · A/B paired runner.

    python -m shepherd.scripts.r2b_phase1 --benchmark          # 서버: full/lite 실측
    python -m shepherd.scripts.r2b_phase1 --seal-branch        # T_proj 분기 기계 봉인
    python -m shepherd.scripts.r2b_phase1 --run --shard K --n-shards 8   # A/B 22,400 ep

계약 = B0 v2 cba024d7ee3d9f61 (B2_WORLD_CONTRACT_FROZEN; v1 e3fd7800003d34e1 supersede). 실행 순서 강제:
benchmark → branch seal → Phase 1 → (판독기가 branch seal 존재를 assert) → C.
단일 treatment 조항: A/B 는 **동일한 resolve() kwargs** 로 env 를 짓고 limiter_mode
문자열("hold"/"intercept") 만 다르다 — 러너가 kwargs 동일성을 기계 assert.
B0 v2: HARD_KILL STOP 은 **arm A 한정** (hold 에선 계약 위반 신호); arm B 의
HARD_KILL 은 유효 competing terminal 로 기록된다 (2-layer 판독: Δp_net primary /
Δp_neutralization secondary / p_hard 보고).
7C: fire_step·steps 를 기록 (descriptive only — inference/게이트 사용 금지;
intercept limiter 는 설계상 step 0 부터 반응). torch-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.mission_rollout import run_episode                # noqa: E402
from shepherd.scripts.r2a_lattice import impls                          # noqa: E402
from shepherd.scripts.r2a_stage1 import _lattice, draw_cell_jitter, resolve  # noqa: E402

ART2 = ROOT / "artifacts/r2b"
B0_HASH = "cba024d7ee3d9f61"            # B0 v2 (arm-A-only STOP, 2-layer estimand)
SEED0, NS = 7000, "r2b_p1_v2"     # v2: fresh stream (v1 289 scenarios quarantined)
N_AB, N_SHARD_DEFAULT = 400, 8
THRESHOLD_H = 14.0


def _b0() -> dict:
    b0 = json.loads((ART2 / "b0_world_contract.json").read_text(encoding="utf-8"))
    assert b0["b0_hash"] == B0_HASH
    return b0


def _cells() -> list:
    s3 = json.loads((ROOT / "artifacts/r2a/stage3_protocol.json").read_text(encoding="utf-8"))
    return [tuple(c) for c in s3["cells"]]                  # [(slice, chi_c, eta), ...] 28개


def _slices() -> dict:
    """λ slice 구현 2종 — Phase 1 A/B 와 C arm 의 단일 정의원."""
    lat = _lattice()
    return {0: impls(lat["tau_B"])["R-ref"],
            2: dict(impls(lat["tau_B"])["R-ref"], R_max=8.22 * 1.77 / 2.30,
                    target=["alpha", "lam"])}


def scenario_kwargs(s: int, cells: list, sls: dict) -> tuple:
    """scenario id → (slice, cell, chi, eta, build kwargs). q_dec 게이트 포함."""
    sl, chi_c, eta_c = cells[s // N_AB]
    chi, eta = draw_cell_jitter(SEED0, s, chi_c, eta_c, ns=NS)
    kw = resolve(sls[sl], chi, eta)
    q = kw["extra_cfg"]["physics.dt"] / kw["extra_cfg"]["physics.tau_deploy"]
    assert abs(q - 1.0 / 6.0) < 1e-12
    return sl, chi_c, eta_c, chi, eta, kw


def benchmark(eps=(2, 26, 35)) -> dict:
    """서버용: full (run_p2prime) / lite (run_probe, §7.1 상수) sec/solve 실측.
    구 MISS_EPISODES 만 사용 — 신규 R2b seed 무접촉."""
    from shepherd.scripts.recoverability_probe import run_p2prime, run_probe
    out = {"episodes": list(eps), "b0_hash": B0_HASH}
    for name, fn in (("full", run_p2prime), ("lite", run_probe)):
        ts = []
        n_solves = []
        for ep in eps:
            t0 = time.time()
            r = fn(episodes=(ep,))
            dt = time.time() - t0
            k = max(len(r.get("records", [])), 1)
            ts.append(dt / k)
            n_solves.append(k)
            print(f"[bench {name}] ep {ep}: {dt:.0f}s / {k} solves = {dt / k:.0f} s/solve",
                  flush=True)
        out[name] = {"sec_per_solve_mean": sum(ts) / len(ts),
                     "sec_per_solve_max": max(ts), "solves_per_ep": n_solves,
                     "method": "elapsed / len(records) per episode"}
    (ART2 / "oracle_server_benchmark.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def seal_branch(n_shard: int = N_SHARD_DEFAULT) -> dict:
    """분기 기계 봉인 — P1 readout 전 필수 (B0 순서 조항). 감사 지정 필드 전부 기록."""
    import subprocess
    bm = json.loads((ART2 / "oracle_server_benchmark.json").read_text(encoding="utf-8"))
    t_lite = bm["lite"]["sec_per_solve_mean"]
    t_proj_h = 2800 * t_lite / n_shard / 3600
    full = t_proj_h <= THRESHOLD_H
    branch = {
        "b0_hash": B0_HASH,
        "code_commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
        "benchmark_cases": bm["episodes"],
        "t_lite_mean": t_lite, "t_lite_max": bm["lite"]["sec_per_solve_max"],
        "t_full_mean": bm["full"]["sec_per_solve_mean"],
        "n_shard": n_shard, "T_proj_hours": round(t_proj_h, 2),
        "threshold_hours": THRESHOLD_H,
        "selected_C_design": ("FULL_28x100" if full else "SENTINEL_6x50"),
        "S_C_rule": ("S_C = S_AB[0:100] per cell (all 28 cells)" if full else
                     "S_C = S_AB[0:50] per sentinel cell (eta {2.1, 3.0, 3.9} x lam "
                     "{0, 2}, band cell nearest chi50) — mechanical truncation of the "
                     "same nested prefix rule"),
        "decision_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "note": "sealed BEFORE any Phase 1 readout; the readout asserts this file",
    }
    branch["branch_hash"] = hashlib.sha256(
        json.dumps(branch, sort_keys=True).encode()).hexdigest()[:16]
    (ART2 / "c_budget_branch.json").write_text(
        json.dumps(branch, indent=1, ensure_ascii=False), encoding="utf-8")
    return branch


def run_shard(shard: int, n_shards: int = N_SHARD_DEFAULT) -> dict:
    """A/B paired 러너: scenario 당 A(hold)·B(intercept) — 같은 resolve kwargs,
    limiter_mode 만 다름 (단일 treatment 기계 검증)."""
    import subprocess
    _b0()
    cells = _cells()
    slices = _slices()
    total = len(cells) * N_AB
    lo, hi = shard * total // n_shards, (shard + 1) * total // n_shards
    out_dir = ART2 / "phase1_v2"; out_dir.mkdir(parents=True, exist_ok=True)
    sentinel = out_dir / "HARD_KILL_STOP"
    path = out_dir / f"shard{shard:02d}.json"
    code_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    records = []
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev["b0_hash"] == B0_HASH:
            records = prev["records"]

    def _save(stopped=False):
        path.write_text(json.dumps(
            {"shard": shard, "n_shards": n_shards, "scenario_range": [lo, hi],
             "b0_hash": B0_HASH, "code_commit": code_commit,
             "stopped_by_sentinel": stopped, "records": records},
            ensure_ascii=False), encoding="utf-8")

    for s in range(lo + len(records) // 2, hi):
        if sentinel.exists():
            _save(stopped=True)
            return {"n_done": len(records), "stopped": True}
        sl, chi_c, eta_c, chi, eta, kw = scenario_kwargs(s, cells, slices)
        kw_b = resolve(slices[sl], chi, eta)
        assert kw["extra_cfg"] == kw_b["extra_cfg"] and kw["attacker"] == kw_b["attacker"] \
            and kw["spawn"] == kw_b["spawn"]              # 단일 treatment: kwargs 동일
        for arm, mode in (("A", "hold"), ("B", "intercept")):
            st = build_m4_env(SEED0, s, **(kw if arm == "A" else kw_b))
            r = run_episode(st.env, st.scn, st.lay, seed=SEED0 + s,
                            limiter_mode=mode, fire_mode="clean", policy=None,
                            baseline_commit=False)
            records.append({"s": s, "arm": arm, "slice": sl, "cell": [chi_c, eta_c],
                            "chi": chi, "eta": eta, "label": r.label,
                            "fire_step": r.fire_step, "steps": r.steps})  # 7C descriptive
            # B0 v2 competing-risk semantics: arm B 의 HARD_KILL 은 유효 terminal
            # (treatment 의 downstream consequence — 기록만). STOP 은 arm A 한정.
            if r.label == "HARD_KILL" and arm == "A":
                sentinel.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(sentinel, "x", encoding="utf-8") as f:
                        json.dump({"shard": shard, "scenario": s, "arm": arm}, f)
                except FileExistsError:
                    pass
                _save(stopped=True)
                raise SystemExit(f"HARD_KILL STOP: r2b shard {shard} scenario {s}")
        if (s - lo + 1) % 50 == 0 or s + 1 == hi:
            _save()
            print(f"[r2b shard {shard}] {s - lo + 1}/{hi - lo} scenarios", flush=True)
    _save()
    return {"n_done": len(records), "stopped": False}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--seal-branch", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=N_SHARD_DEFAULT)
    a = ap.parse_args(argv)
    if a.benchmark:
        bm = benchmark()
        print(f"full mean {bm['full']['sec_per_solve_mean']:.0f}s  "
              f"lite mean {bm['lite']['sec_per_solve_mean']:.0f}s "
              f"(max {bm['lite']['sec_per_solve_max']:.0f}s)")
    if a.seal_branch:
        br = seal_branch(a.n_shards)
        print(f"branch sealed {br['branch_hash']}  T_proj {br['T_proj_hours']} h  "
              f"-> {br['selected_C_design']}")
    if a.run:
        run_shard(a.shard, a.n_shards)


if __name__ == "__main__":
    main()
