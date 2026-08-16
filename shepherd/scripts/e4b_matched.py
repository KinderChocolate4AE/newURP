"""E4-1b — matched-mean temporal dispersion (docs/83 §24 동결 프로토콜).

질문
----
  **평균 lead 는 같은데 시간 분산만 늘리면 physical interception 이 올라가는가?**

설계 (§24.2) — same mean lead, different temporal dispersion
    D = 0.25
    control : delta_i = D/2 = 0.125            (4 기 동일)
    diverse : delta_i in {0, D/3, 2D/3, D}     (평균 0.125 로 **동일**)
  모든 delta >= 0 이므로 zero-horizon clamp 가 **구조적으로 발생하지 않는다**
  (그래도 계수해 0 임을 확인). diverse 배정은 balanced permutation PERMS[ep%24].

Primary (§24.3) — 양자화 대응
    E[ range(t_min)_diverse - range(t_min)_control ]   ★ paired **MEAN** (초)
  §21.3 에서 paired median 이 양자화로 0 이 나온 설계 결함의 직접 대응.
  Secondary: P(dRange>0)/P(=0)/P(<0). Outcome: dP_HK. Tertiary: dP_net.

판정 M1~M4 는 §24.4 에 동결. 결과를 보고 바꾸지 않는다.

    python -m shepherd.scripts.e4b_matched --n 300 --out results/e4b_matched_r4.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np

from shepherd.scripts.e4_stagger import R_CONTACT, episode_e4
from shepherd.stats import wilson

D_FIXED = 0.25
CAP = ("CAPTURED", "NET_CAPTURE", "CAPTURE_WITH_CONTACT")


def _arm(n: int, design: str) -> list:
    rows, t0 = [], time.time()
    for ep in range(n):
        rows.append(episode_e4(ep, D_FIXED, design))
        if (ep + 1) % 50 == 0 or ep + 1 == n:
            el = time.time() - t0
            print(f"    [{design}] {ep+1}/{n}  {el:6.1f}s "
                  f"(ETA {el/(ep+1)*(n-ep-1):5.0f}s)", flush=True)
    return rows


def _summ(rows: list) -> dict:
    n = len(rows)
    rt = np.array([r["range_t_min"] for r in rows])
    hk = sum(1 for r in rows if r["label"] == "HARD_KILL")
    cap = sum(1 for r in rows if r["label"] in CAP)
    pen = sum(1 for r in rows if r["label"] == "PENETRATED")
    db = np.array([r["d_min_best"] for r in rows])
    return {"n": n, "range_t_min_mean": float(rt.mean()),
            "range_t_min_med": float(np.median(rt)),
            "p_hk": hk / n, "p_hk_wilson": list(wilson(hk, n)),
            "p_net": cap / n, "p_pen": pen / n,
            "p_reach": float((db <= R_CONTACT).mean()),
            "d_min_best_med": float(np.median(db)),
            "clamp_episode_frac": sum(1 for r in rows if r["n_clamp"] > 0) / n,
            "records": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="E4-1b matched-mean (docs/83 §24)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default="results/e4b_matched_r4.json")
    a = ap.parse_args()
    print(f"[E4-1b · docs/83 §24] n={a.n} · D={D_FIXED} · "
          f"control δ=0.125 vs diverse {{0,D/3,2D/3,D}} (평균 동일)", flush=True)

    arms = {d: _summ(_arm(a.n, d)) for d in ("control", "diverse")}
    C, V = arms["control"], arms["diverse"]

    rc = np.array([r["range_t_min"] for r in C["records"]])
    rv = np.array([r["range_t_min"] for r in V["records"]])
    hc = np.array([r["label"] == "HARD_KILL" for r in C["records"]], float)
    hv = np.array([r["label"] == "HARD_KILL" for r in V["records"]], float)
    nc = np.array([r["label"] in CAP for r in C["records"]], float)
    nv = np.array([r["label"] in CAP for r in V["records"]], float)

    rng = np.random.default_rng(0)
    idx = rng.integers(0, a.n, size=(20000, a.n))
    d_rt = rv - rc
    lo1, hi1 = np.percentile((rv[idx] - rc[idx]).mean(1), [2.5, 97.5])   # ★ MEAN
    lo2, hi2 = np.percentile((hv[idx] - hc[idx]).mean(1), [2.5, 97.5])
    lo3, hi3 = np.percentile((nv[idx] - nc[idx]).mean(1), [2.5, 97.5])

    print(f"\n=== Primary (§24.3) — paired MEAN ===")
    print(f"  range(t_min)  control {rc.mean():.4f}s -> diverse {rv.mean():.4f}s")
    print(f"  Δ(mean) = {d_rt.mean():+.4f} s   CI95 [{lo1:+.4f}, {hi1:+.4f}]")
    print(f"  secondary: >0 {np.mean(d_rt>0):.3f} · =0 {np.mean(d_rt==0):.3f} · "
          f"<0 {np.mean(d_rt<0):.3f}")
    print(f"\n=== Outcome ===")
    print(f"  P_HK  {hc.mean():.4f} -> {hv.mean():.4f} · Δ {hv.mean()-hc.mean():+.4f} "
          f"CI95 [{lo2:+.4f}, {hi2:+.4f}]")
    print(f"  P_net {nc.mean():.4f} -> {nv.mean():.4f} · Δ {nv.mean()-nc.mean():+.4f} "
          f"CI95 [{lo3:+.4f}, {hi3:+.4f}]")
    print(f"  clamp: control {C['clamp_episode_frac']:.3f} · "
          f"diverse {V['clamp_episode_frac']:.3f}  (§24.2: 구조적으로 0 이어야)")

    m1 = lo1 > 0 and lo2 > 0
    m3 = lo1 <= 0 <= hi1
    m4 = lo1 > 0 and hi2 < 0
    verdict = ("M1 (temporal layering = causal mechanism 확립)" if m1 else
               "M3 (개입이 dispersion 을 못 만듦 — 구현/파라미터 실패)" if m3 else
               "M4 (dispersion ↑ 이나 HK 악화)" if m4 else
               "M2 (dispersion ↑ 이나 성능 이득 미확립 -> E4-2)")
    print(f"\n★ 판정 (§24.4 동결): {verdict}", flush=True)

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(stamp(artifact="e4b_matched"),
                            prereg_doc="docs/83 §24 (E4-1b)", D=D_FIXED, n=a.n,
                            primary="paired MEAN of range(t_min) diverse-control",
                            world="E2-A 동일 (ratified + T1 + intercept + commit)"),
           "arms": {k: {kk: vv for kk, vv in v.items() if kk != "records"}
                    for k, v in arms.items()},
           "primary": {"d_range_mean": float(d_rt.mean()),
                       "d_range_ci95": [float(lo1), float(hi1)],
                       "frac_gt0": float(np.mean(d_rt > 0)),
                       "frac_eq0": float(np.mean(d_rt == 0)),
                       "frac_lt0": float(np.mean(d_rt < 0))},
           "outcome": {"d_p_hk": float(hv.mean() - hc.mean()),
                       "d_p_hk_ci95": [float(lo2), float(hi2)],
                       "d_p_net": float(nv.mean() - nc.mean()),
                       "d_p_net_ci95": [float(lo3), float(hi3)]},
           "verdict": verdict,
           "records": {k: v["records"] for k, v in arms.items()}}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {p}", flush=True)


if __name__ == "__main__":
    main()
