"""R2b plan-level multi-limiter dependence probe (closure 브리프 r4 §10.4 카드 이행).

    python -m shepherd.scripts.r2b_c_dep_probe --smoke            # s=2001 배선 검증
    python -m shepherd.scripts.r2b_c_dep_probe --run --shard K --n-shards 8

**지위 (봉인 선언 — 실행 전 커밋)**: descriptive diagnostic. reoptimization 이 없으므로
**necessity ablation 이 아니다** — "이 particular successful plan 이 여러 limiter 의
동시 행동에 의존했는가"의 witness 만 산출한다 ("single-limiter 로는 불가능" 증명 불가:
다른 단독 plan 이 성공할 수 있음). 협력 어휘 복권과는 별개 (그건 별도 봉인 캠페인).

표본 규칙 (deterministic, 커밋된 c_arm shard 에서만): 셀별 s 오름차순으로
**C_N==1 ∧ plan_kind=="accels" 인 앞 K=5 판** (부족 셀은 있는 만큼) — 최대 140.

판당 절차: 봉인 search 결정론 재실행으로 plan 재현 → full-fidelity replay 가 shard
기록과 (label, fire_step, steps) 일치해야 진행 (**replay-parity gate**) → 변형 replay
9종 전부 full-fidelity: full(=parity) · solo_j (row j 만 유지, 나머지 0 = hold) ×4 ·
loo_j (row j 만 0) ×4. 성공 = NET_CAPTURE 만.

판정 어휘 (사전 선언): scenario 별
  solo_any  = ∃j: solo_j == NET_CAPTURE   → "solo-sufficient witness"
  loo_all   = ∀j: loo_j == NET_CAPTURE    → 단일 제거에 강건
  **multi_dependent witness** = (full == NET_CAPTURE) ∧ ¬solo_any
집계는 비율 보고만 (통계 규칙·CI 없음 — descriptive). torch-free.
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

from shepherd.provenance import git_commit              # noqa: E402
from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.r2b_c_runner import (                             # noqa: E402
    ART2, B0_HASH, BRANCH_HASH, SEED0, _rollout, search_plan)
from shepherd.scripts.r2b_phase1 import _cells, _slices                 # noqa: E402

K_PER_CELL = 5
OUT_DIR = ART2 / "c_dep_probe"


def sample() -> list:
    """봉인 표본 규칙: 셀별 C_N==1 ∧ accels 앞 K=5 (s 오름차순)."""
    recs = {}
    for f in sorted((ART2 / "c_arm").glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["b0_hash"] == B0_HASH and d["branch_hash"] == BRANCH_HASH
        for r in d["records"]:
            recs[r["s"]] = r
    by_cell = {}
    for s in sorted(recs):
        r = recs[s]
        if r["C_N"] == 1 and r["plan_kind"] == "accels":
            k = (r["slice"], tuple(r["cell"]))
            if len(by_cell.setdefault(k, [])) < K_PER_CELL:
                by_cell[k].append(s)
    return sorted(ss for v in by_cell.values() for ss in v), recs


def probe_scenario(s: int, rec: dict, cells: list, sls: dict) -> dict:
    meta, best_plan, _score, _n = search_plan(s, cells, sls)
    assert best_plan[0] == "accels", f"s={s}: 재현 plan 이 accels 아님 ({best_plan[0]})"
    kw = meta[5]
    plan = best_plan[1]
    n_lim = plan.shape[0]

    def replay(p):
        return _rollout(build_m4_env(SEED0, s, **kw), s, ("accels", p))

    r_full = replay(plan)
    assert (r_full.label, r_full.fire_step, r_full.steps) == \
        (rec["label"], rec["fire_step"], rec["steps"]), \
        f"parity FAIL s={s}: {(r_full.label, r_full.fire_step, r_full.steps)}"

    solo, loo = [], []
    for j in range(n_lim):
        p_solo = np.zeros_like(plan); p_solo[j] = plan[j]
        p_loo = plan.copy(); p_loo[j] = 0.0
        solo.append(replay(p_solo).label)
        loo.append(replay(p_loo).label)
    solo_n = [int(x == "NET_CAPTURE") for x in solo]
    loo_n = [int(x == "NET_CAPTURE") for x in loo]
    return {"s": s, "slice": rec["slice"], "cell": rec["cell"],
            "full_label": r_full.label,
            "solo_labels": solo, "loo_labels": loo,
            "solo_any": int(any(solo_n)), "loo_all": int(all(loo_n)),
            "multi_dependent": int(not any(solo_n)),
            "n_solo_success": sum(solo_n), "n_loo_success": sum(loo_n)}


def run_shard(shard: int, n_shards: int = 8) -> None:
    from shepherd.notify import ntfy
    cells, sls = _cells(), _slices()
    scs, recs = sample()
    lo, hi = shard * len(scs) // n_shards, (shard + 1) * len(scs) // n_shards
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"shard{shard:02d}.json"
    code_commit = git_commit()
    records = []
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev["b0_hash"] == B0_HASH:
            records = prev["records"]

    def _save():
        path.write_text(json.dumps(
            {"shard": shard, "n_shards": n_shards, "sample_size": len(scs),
             "k_per_cell": K_PER_CELL, "b0_hash": B0_HASH,
             "branch_hash": BRANCH_HASH, "code_commit": code_commit,
             "records": records}, ensure_ascii=False), encoding="utf-8")

    t0 = time.time()
    for k in range(lo + len(records), hi):
        s = scs[k]
        records.append(probe_scenario(s, recs[s], cells, sls))
        _save()
        print(f"[dep shard {shard}] {len(records)}/{hi - lo}  "
              f"({(time.time() - t0) / (len(records)) :.0f} s/scn)", flush=True)
    ntfy(f"r2b dep-probe shard {shard} done: {len(records)}/{hi - lo}")


def smoke() -> None:
    """s=2001 (viz 로 이미 공개된 C 성공판) 배선 검증 — parity gate + 9 replay."""
    cells, sls = _cells(), _slices()
    scs, recs = sample()
    assert 2001 in scs, "표본 규칙 확인 실패: s=2001 미포함"
    print(f"[smoke] sample = {len(scs)} scenarios "
          f"(rule: C_N=1 ∧ accels, K={K_PER_CELL}/cell)")
    r = probe_scenario(2001, recs[2001], cells, sls)
    print(f"[smoke] s=2001 parity OK · solo={r['solo_labels']} · "
          f"loo={r['loo_labels']} · multi_dependent={r['multi_dependent']}")
    print("[smoke] ALL PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    a = ap.parse_args()
    if a.smoke:
        smoke()
    if a.run:
        run_shard(a.shard, a.n_shards)


if __name__ == "__main__":
    main()
