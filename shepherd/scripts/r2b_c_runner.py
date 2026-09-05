"""R2b C arm — sealed-budget search-based achievability benchmark (B0 v2 arms.C).

    python -m shepherd.scripts.r2b_c_runner --smoke                 # bit-parity + 결정론
    python -m shepherd.scripts.r2b_c_runner --smoke --solve         # + 비-S_C 1판 전체 배선
    python -m shepherd.scripts.r2b_c_runner --run --shard K --n-shards 8

계약 = B0 v2 cba024d7ee3d9f61 arms.C + branch seal f1bd9a459d97e693
(FULL_28x100 lite C). 정의: C_N(s)=1 iff **full-fidelity replay 라벨 == NET_CAPTURE**
(HARD_KILL·CAPTURE_WITH_CONTACT 불인정 — Phase 1 판독과 동일 판정층). C_U/C_H 는
같은 replay 라벨에서 secondary 로 유도. p_C_hat = 봉인 search 절차의 attainment
rate 이지 물리적 achievability 확률이 아니다 (B0 estimand 조항).

search 절차 (§7.1 lite budget, recoverability_probe 상수 재사용 — 복제 금지):
  s0 = 0 (에피소드 전체) · limiter 별 K_SEG=4 piecewise-constant 가속 plan ·
  CEM P=64 × I=2 × elite 16 × solver seed {0,1,2} = 384 rollouts/scenario ·
  구조 후보 {intercept, hold} 를 1세대에 포함 (rule-based arm 은 search class 의
  원소 — C 가 B 를 놓칠 수 없다) · rollout = 경량 클론 (viability.n_samples=16)
  proxy 선택 전용 · 최종 판정 = full-fidelity env 1회 replay 라벨만.
solver RNG = default_rng([20260906, seed, s]) — scenario CRN (SHA-256, r2b_p1_v2)
과 완전 분리. S_C = S_AB_v2[0:100] per cell (28×100 = 2,800). torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.mission_rollout import MissionResult, run_episode  # noqa: E402
from shepherd.scripts.r2b_phase1 import (                               # noqa: E402
    ART2, B0_HASH, N_AB, NS, SEED0, _b0, _cells, _slices, scenario_kwargs)
from shepherd.scripts.recoverability_probe import (                     # noqa: E402
    CLONE_N_SAMPLES, ELITE, ITERS, K_SEG, POP, SOLVER_SEEDS,
    _clip_ball, _sample_ball)

BRANCH_HASH = "f1bd9a459d97e693"
N_C = 100                                     # S_C = S_AB_v2[0:100] per cell
SOLVER_NS = 20260906                          # solver RNG 네임스페이스 (≠ scenario CRN)
OUT_DIR = ART2 / "c_arm"


def _assert_seals() -> None:
    b0 = _b0()
    br = json.loads((ART2 / "c_budget_branch.json").read_text(encoding="utf-8"))
    assert br["branch_hash"] == BRANCH_HASH
    assert b0["amendment_status"]["inherited_by_reference"]["c_budget_branch"] \
        == br["branch_hash"]
    assert br["selected_C_design"] == "FULL_28x100"


def sc_list() -> list:
    """S_C 전개: 셀 c 의 A/B stream 앞 100개 scenario id (nested prefix 규칙)."""
    return [c * N_AB + i for c in range(len(_cells())) for i in range(N_C)]


def _fresh(env) -> None:
    """rollout 간 fresh-build 상태 복원: _last_v_shot_soft 는 run_episode 가 env
    객체에 심는 유일한 cross-episode 상태 (env_adv 가 getattr(..., None) 으로
    읽으므로 None = 미존재와 동일). 나머지는 env.reset 이 재초기화 — smoke 의
    결정론 체크가 이 주장을 검증한다."""
    inner = env.inner if hasattr(env, "inner") else env
    if hasattr(inner, "_last_v_shot_soft"):
        inner._last_v_shot_soft = None


def _plan_policy(env, plan: np.ndarray, horizon: int):
    """(n_lim, K_SEG, 3) plan → run_episode policy 콜러블 (commit bit = 0)."""
    lim_ids = env.limiter_ids
    t = {"i": -1}

    def policy(obs, flags):
        t["i"] += 1
        seg = min(t["i"] * K_SEG // max(horizon, 1), K_SEG - 1)
        return {lid: np.array([*plan[i, seg], 0.0], np.float32)
                for i, lid in enumerate(lim_ids)}
    return policy


def _rollout(st, s: int, cand) -> MissionResult:
    """후보 1개 실행. run_episode 를 그대로 호출 (스텝 규약 복제 금지)."""
    _fresh(st.env)
    if cand[0] == "policy":
        return run_episode(st.env, st.scn, st.lay, seed=SEED0 + s,
                           limiter_mode=cand[1], fire_mode="clean")
    return run_episode(st.env, st.scn, st.lay, seed=SEED0 + s,
                       policy=_plan_policy(st.env, cand[1], int(st.lay.episode_len)),
                       scripted_roles=("finisher",), fire_mode="clean")


def _proxy_c(r: MissionResult) -> tuple:
    """C_N-지향 lexicographic (큰 쪽 우수): L1 NET_CAPTURE ≻ L2 capture(접촉 포함)
    ≻ L3 비침투 ≻ L4 clean crossing 수 ≻ L5 접촉 스텝 ↓. 후보 선택 전용 —
    판정은 full replay 라벨만 (P83g 분리 원칙 계승)."""
    return (int(r.label == "NET_CAPTURE"), int(r.outcome == "CAPTURED"),
            int(r.label != "PENETRATED"), int(r.clean_crossings),
            -int(r.contact_steps))


def solve_scenario(s: int, cells: list, sls: dict) -> dict:
    sl, chi_c, eta_c, chi, eta, kw = scenario_kwargs(s, cells, sls)
    kw_lite = dict(kw, extra_cfg=dict(kw["extra_cfg"],
                                      **{"viability.n_samples": CLONE_N_SAMPLES}))
    st = build_m4_env(SEED0, s, **kw_lite)          # 경량 클론 env 1개 재사용
    n_lim = len(st.env.limiter_ids)
    a_max = float(st.scn.limiter.a_max)
    structured = [("policy", "intercept"), ("policy", "hold")]
    best_score, best_plan, rollouts = None, None, 0
    for ss in SOLVER_SEEDS:
        rng = np.random.default_rng([SOLVER_NS, ss, s])
        mean = np.zeros((n_lim, K_SEG, 3))
        std = np.full((n_lim, K_SEG, 3), a_max / 2.0)
        for it in range(ITERS):
            cands = list(structured) if it == 0 else []
            n_rand = POP - len(cands)
            if it == 0:
                sam = _sample_ball(rng, (n_rand, n_lim, K_SEG, 3), a_max)
            else:
                sam = _clip_ball(mean[None] + std[None] * rng.normal(
                    size=(n_rand, n_lim, K_SEG, 3)), a_max)
            cands.extend(("accels", x) for x in sam)
            scored = []
            for c in cands:
                scored.append((_proxy_c(_rollout(st, s, c)), c))
                rollouts += 1
            scored.sort(key=lambda x: x[0], reverse=True)
            if best_score is None or scored[0][0] > best_score:
                best_score, best_plan = scored[0]
            elite = [c[1] for sc, c in scored[:ELITE] if c[0] == "accels"]
            if elite:
                e = np.stack(elite)
                mean, std = e.mean(axis=0), e.std(axis=0) + 1e-3

    stf = build_m4_env(SEED0, s, **kw)              # full-fidelity replay 판정
    r = _rollout(stf, s, best_plan)
    return {"s": s, "slice": sl, "cell": [chi_c, eta_c], "chi": chi, "eta": eta,
            "label": r.label, "C_N": int(r.label == "NET_CAPTURE"),
            "C_H": int(r.label == "HARD_KILL"),
            "C_U": int(r.label in ("NET_CAPTURE", "HARD_KILL")),
            "plan_kind": best_plan[0],
            "plan_mode": best_plan[1] if best_plan[0] == "policy" else None,
            "lite_proxy": [float(x) for x in best_score],
            "lite_no_solution": bool(best_score[0] < 1),
            "rollouts": rollouts, "fire_step": r.fire_step, "steps": r.steps,
            "n_contact": r.n_contact, "clean_crossings": r.clean_crossings}


# ------------------------------------------------------------------ shard ----
def run_shard(shard: int, n_shards: int = 8) -> dict:
    import subprocess
    from shepherd.notify import ntfy
    _assert_seals()
    cells, sls = _cells(), _slices()
    scs = sc_list()
    lo, hi = shard * len(scs) // n_shards, (shard + 1) * len(scs) // n_shards
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"shard{shard:02d}.json"
    code_commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    records = []
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev["b0_hash"] == B0_HASH and prev["branch_hash"] == BRANCH_HASH:
            records = prev["records"]

    def _save():
        path.write_text(json.dumps(
            {"shard": shard, "n_shards": n_shards, "sc_range": [lo, hi],
             "b0_hash": B0_HASH, "branch_hash": BRANCH_HASH,
             "code_commit": code_commit, "solver_ns": SOLVER_NS,
             "records": records}, ensure_ascii=False), encoding="utf-8")

    t0, n0 = time.time(), len(records)
    for k in range(lo + len(records), hi):
        records.append(solve_scenario(scs[k], cells, sls))
        _save()                                       # incremental (long-run 규율)
        if len(records) % 10 == 0 or k + 1 == hi:
            sps = (time.time() - t0) / (len(records) - n0)
            print(f"[r2b C shard {shard}] {len(records)}/{hi - lo}  "
                  f"({sps:.0f} s/solve)", flush=True)
    ntfy(f"r2b C shard {shard} done: {len(records)}/{hi - lo}")
    return {"n_done": len(records)}


# ------------------------------------------------------------------ smoke ----
def smoke(solve: bool = False) -> None:
    """서버 투입 전 필수 게이트 (결과 열람 아님 — 전부 배선 검증).

    1) bit-parity: scenario 재구성 → run_episode(hold/intercept) 라벨이 Phase 1
       v2 shard 기록과 일치 (scenario 구성 경로가 A/B stream 과 동일함을 증명).
    2) env-재사용 결정론: 경량 env 에서 hold → 임의 plan 2개 → hold 재실행이
       bit 동일 (_fresh 가 cross-episode 누출을 막음을 검증).
    3) plan-policy 배선: accels 후보가 정상 종료 라벨을 냄.
    4) --solve: 비-S_C scenario (셀 0 의 s=100) 로 solve_scenario 전체 1판.
    """
    _assert_seals()
    cells, sls = _cells(), _slices()
    stored = {}
    for f in sorted((ART2 / "phase1_v2").glob("shard*.json")):
        for r in json.loads(f.read_text(encoding="utf-8"))["records"]:
            stored[(r["s"], r["arm"])] = r
    probe_s = [0, 6 * N_AB + 3, 27 * N_AB + 99]       # 셀 0 / 6 / 27
    for s in probe_s:
        sl, chi_c, eta_c, chi, eta, kw = scenario_kwargs(s, cells, sls)
        for arm, mode in (("A", "hold"), ("B", "intercept")):
            st = build_m4_env(SEED0, s, **kw)
            r = run_episode(st.env, st.scn, st.lay, seed=SEED0 + s,
                            limiter_mode=mode, fire_mode="clean")
            ref = stored[(s, arm)]
            assert (r.label, r.fire_step, r.steps) == \
                (ref["label"], ref["fire_step"], ref["steps"]), \
                f"parity FAIL s={s} arm={arm}: {r.label} != {ref['label']}"
            assert abs(chi - ref["chi"]) < 1e-12 and abs(eta - ref["eta"]) < 1e-12
        print(f"[smoke] parity OK s={s}")

    s = probe_s[0]
    _, _, _, _, _, kw = scenario_kwargs(s, cells, sls)
    kw_lite = dict(kw, extra_cfg=dict(kw["extra_cfg"],
                                      **{"viability.n_samples": CLONE_N_SAMPLES}))
    st = build_m4_env(SEED0, s, **kw_lite)
    n_lim = len(st.env.limiter_ids)
    a_max = float(st.scn.limiter.a_max)
    r1 = _rollout(st, s, ("policy", "hold"))
    rng = np.random.default_rng([SOLVER_NS, 99, s])
    for plan in _sample_ball(rng, (2, n_lim, K_SEG, 3), a_max):
        rp = _rollout(st, s, ("accels", plan))
        assert rp.label in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL",
                            "PENETRATED", "SPENT_FAIL", "TRUNCATED")
    r2 = _rollout(st, s, ("policy", "hold"))
    key = lambda r: (r.label, r.steps, r.fire_step, r.clean_crossings,  # noqa: E731
                     r.contact_steps, round(r.min_target_dist, 9))
    assert key(r1) == key(r2), f"determinism FAIL: {key(r1)} != {key(r2)}"
    print(f"[smoke] env-reuse determinism OK (s={s}, {key(r1)[0]})"
          f" · plan-policy wiring OK")

    if solve:
        s_ns = N_C                                    # 셀 0 의 101번째 — S_C 밖
        t0 = time.time()
        rec = solve_scenario(s_ns, cells, sls)
        print(f"[smoke] full solve (non-S_C s={s_ns}, SMOKE ONLY — inference 제외): "
              f"{time.time() - t0:.0f}s, rollouts={rec['rollouts']}, "
              f"plan_kind={rec['plan_kind']}")
    print("[smoke] ALL PASS")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--solve", action="store_true", help="smoke 에 full solve 1판 포함")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    a = ap.parse_args(argv)
    if a.smoke:
        smoke(solve=a.solve)
    if a.run:
        run_shard(a.shard, a.n_shards)


if __name__ == "__main__":
    main()
