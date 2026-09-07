"""R2b C arm 판독 — B0 v2 (cba024d7ee3d9f61) 3-way 봉인 문장의 기계 적용.

    python -m shepherd.scripts.r2b_c_readout

**봉인 선언 (2026-09-07, C shard 로컬 회수·열람 전 커밋)**: C-positivity 규칙은
P1-positive 규칙 (B0 v2 estimands.p1_positive_rule) 의 **기계적 이식**이며 새
수치 상수를 도입하지 않는다. primary contrast = paired Δp_CA = p_C_N − p_A_N
(S_C 위, A = phase1_v2 hold 기록, 동일 scenario 쌍):

  C_POSITIVE iff  (i) 14행 (slice×eta) 중 ≥12행 점추정 > 0
             AND (ii) 각 λ slice 에서 ≥5/7 행 양수
             AND (iii) 전역 paired CI95 하한 > 0 (셀-층화 scenario bootstrap
                       B=4000, seed 0 — P1 판독과 동일 절차)

3-way 문장 = B0 v2 readout_3cases 의 해당 key 를 **그대로 인용** (B verdict 는
p1_readout.json 에서 읽음 — P1_NOT_POSITIVE 확정). C_N = replay 라벨
NET_CAPTURE 만 (B0 C_arm_semantics); C_U/C_H secondary. p_C_hat 은 봉인 search
절차의 attainment rate 이지 물리적 achievability 확률이 아니다. per-scenario
C_N ≥ B_N 비보장 (유한예산 search) — C<B 셀은 이상신호가 아니다. torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
ART2 = ROOT / "artifacts/r2b"
B = 4000
B0_HASH = "cba024d7ee3d9f61"
BRANCH_HASH = "f1bd9a459d97e693"
ETAS = (2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9)


def _load() -> tuple:
    b0 = json.loads((ART2 / "b0_world_contract.json").read_text(encoding="utf-8"))
    br = json.loads((ART2 / "c_budget_branch.json").read_text(encoding="utf-8"))
    p1 = json.loads((ART2 / "p1_readout.json").read_text(encoding="utf-8"))
    assert b0["b0_hash"] == B0_HASH and br["branch_hash"] == BRANCH_HASH
    assert p1["b0_hash"] == B0_HASH

    crecs = []
    for f in sorted((ART2 / "c_arm").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["b0_hash"] == B0_HASH and s["branch_hash"] == BRANCH_HASH
        crecs += s["records"]
    ids = [r["s"] for r in crecs]
    assert len(ids) == 2800 and len(set(ids)) == 2800, f"S_C 불완전: {len(ids)}"

    ab = {}                                       # {(s, arm) -> label}, S_C 만
    sc = set(ids)
    for f in sorted((ART2 / "phase1_v2").glob("shard*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["b0_hash"] == B0_HASH
        for r in s["records"]:
            if r["s"] in sc:
                ab[(r["s"], r["arm"])] = r["label"]
    assert len(ab) == 5600
    return b0, p1, crecs, ab


def main() -> None:
    b0, p1, crecs, ab = _load()
    b_verdict = p1["p1_rule"]["verdict"]

    # {(slice, cell) -> [(s, a_n, b_n, c_n, c_h) ...]}
    by = {}
    for r in crecs:
        key = (r["slice"], tuple(r["cell"]))
        a_n = int(ab[(r["s"], "A")] == "NET_CAPTURE")
        b_n = int(ab[(r["s"], "B")] == "NET_CAPTURE")
        by.setdefault(key, []).append((r["s"], a_n, b_n, r["C_N"], r["C_H"]))
    cells = sorted(by)
    assert len(cells) == 28 and all(len(v) == 100 for v in by.values())

    out = {"b0_hash": B0_HASH, "branch_hash": BRANCH_HASH, "B": B,
           "rule": "C_POSITIVE iff rows>=12/14 AND per-slice>=5/7 AND paired "
                   "CI95 lower > 0 on d_CA_net (mechanical transfer of "
                   "p1_positive_rule; sealed pre-viewing 2026-09-07)",
           "cells": {}}
    dca_all, dcb_all, dcaU_all = [], [], []
    print(f"{'cell':>14} {'pA_N':>6} {'pB_N':>6} {'pC_N':>6} {'dCA':>7} {'dCB':>7} "
          f"{'pC_H':>6} {'nosol':>6}")
    nosol = {r["s"]: r["lite_no_solution"] for r in crecs}
    kind = {r["s"]: (r["plan_mode"] or r["plan_kind"]) for r in crecs}
    for key in cells:
        v = sorted(by[key])
        aN = np.array([x[1] for x in v], float)
        bN = np.array([x[2] for x in v], float)
        cN = np.array([x[3] for x in v], float)
        cH = np.array([x[4] for x in v], float)
        dCA, dCB = cN - aN, cN - bN
        aU = np.array([int(ab[(x[0], "A")] in ("NET_CAPTURE", "HARD_KILL")) for x in v], float)
        cU = cN + cH                              # 상호배타 terminal
        dca_all.append(dCA); dcb_all.append(dCB); dcaU_all.append(cU - aU)
        ns = float(np.mean([nosol[x[0]] for x in v]))
        out["cells"][f"{key[0]}|{key[1][0]},{key[1][1]}"] = {
            "n": len(v), "p_A_net": float(aN.mean()), "p_B_net": float(bN.mean()),
            "p_C_net": float(cN.mean()), "p_C_hard": float(cH.mean()),
            "d_CA_net": float(dCA.mean()), "d_CB_net": float(dCB.mean()),
            "lite_no_solution_rate": ns,
            "plan_kinds": {k: sum(1 for x in v if kind[x[0]] == k)
                           for k in set(kind[x[0]] for x in v)}}
        print(f"{str(key):>14} {aN.mean():>6.3f} {bN.mean():>6.3f} {cN.mean():>6.3f} "
              f"{dCA.mean():>+7.3f} {dCB.mean():>+7.3f} {cH.mean():>6.3f} {ns:>6.2f}")

    # ── 14행 (slice, eta): 두 셀 pooled — P1 판독과 동일 행 구성 ────────────────
    rows = {}
    for sl in (0, 2):
        for eta in ETAS:
            ks = [k for k in cells if k[0] == sl and abs(k[1][1] - eta) < 1e-9]
            d = np.concatenate([np.array([x[3] - x[1] for x in sorted(by[k])], float)
                                for k in ks])
            rows[f"{sl}|{eta}"] = {"d_CA_net": float(d.mean()),
                                   "positive": bool(d.mean() > 0)}
    out["rows"] = rows

    # ── 봉인 C 규칙 (P1 규칙 기계 이식) ────────────────────────────────────────
    rng = np.random.default_rng(0)
    pos = sum(r["positive"] for r in rows.values())
    per_slice = {sl: sum(r["positive"] for k, r in rows.items()
                         if k.startswith(f"{sl}|")) for sl in (0, 2)}
    idxs = [rng.integers(0, len(d), (B, len(d))) for d in dca_all]
    boots = np.mean([d[i].mean(axis=1) for d, i in zip(dca_all, idxs)], axis=0)
    ci = [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))]
    g = float(np.mean([d.mean() for d in dca_all]))
    c_pos = (pos >= 12) and all(v >= 5 for v in per_slice.values()) and ci[0] > 0
    c_verdict = "C_POSITIVE" if c_pos else "C_NULL"

    gB = float(np.mean([d.mean() for d in dcb_all]))
    bootsU = np.mean([d[i].mean(axis=1) for d, i in zip(dcaU_all, idxs)], axis=0)
    ciU = [float(np.quantile(bootsU, .025)), float(np.quantile(bootsU, .975))]

    # ── 3-way 봉인 문장 (B0 v2 readout_3cases 원문 인용) ──────────────────────
    # B verdict 는 p1_readout 에서 확정·공표됨 — 다른 값이면 lineage 손상 신호.
    assert b_verdict == "P1_NOT_POSITIVE", f"unexpected B verdict: {b_verdict}"
    key3 = "B_null_C_pos" if c_pos else "B_null_C_null"
    out.update({
        "c_rule": {"rows_positive": [pos, 14], "per_slice_positive": per_slice,
                   "global_d_CA_net": g, "global_ci95": ci, "verdict": c_verdict},
        "vs_B_descriptive": {"global_d_CB_net": gB},
        "secondary_U": {"global_d_CA_U": float(np.mean([d.mean() for d in dcaU_all])),
                        "global_ci95": ciU},
        "b_verdict": b_verdict,
        "three_way": {"key": key3, "sealed_sentence": b0["readout_3cases"][key3]},
    })
    (ART2 / "c_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nC rule: rows+ {pos}/14  slice+ {per_slice}  global dCA {g:+.3f} "
          f"CI [{ci[0]:+.3f},{ci[1]:+.3f}]  -> {c_verdict}")
    print(f"vs B (descriptive): global dCB {gB:+.3f}   "
          f"secondary dU_CA {out['secondary_U']['global_d_CA_U']:+.3f} "
          f"CI [{ciU[0]:+.3f},{ciU[1]:+.3f}]")
    print(f"3-way [{key3}]: {out['three_way']['sealed_sentence']}")


if __name__ == "__main__":
    main()
