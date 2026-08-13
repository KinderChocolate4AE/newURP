"""E4-1c — uniform lead sweep (docs/83 §26 동결 프로토콜).

질문
----
  Does uniformly increasing prediction horizon improve physical interception under
  otherwise identical pursuit control?

  delta_i = delta (4 기 동일) 이므로 **temporal dispersion 이 구조적으로 0** 이고,
  변하는 것은 prediction horizon 하나뿐이다.

★ fresh seed block (§26.2)
  이 가설은 **E4-1b 결과를 본 뒤** 생겼다. 기존 E4-1b control 을 재사용해
  confirmatory 라 부르지 않고 **세 arm 모두 새 실행**, 미사용 대역 30000..30299.

Primary = paired P_HK (§26.3). 판정 U1~U4 는 §26.4 동결.

    python -m shepherd.scripts.e4c_uniform_lead --n 300 --out results/e4c_uniform.json

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

EP0 = 30000          # ★ fresh seed block (§26.2)
DELTAS = (0.0, 0.125, 0.25)
CAP = ("CAPTURED", "NET_CAPTURE", "CAPTURE_WITH_CONTACT")


def main() -> None:
    ap = argparse.ArgumentParser(description="E4-1c uniform lead (docs/83 §26)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--ep0", type=int, default=EP0)
    ap.add_argument("--out", default="results/e4c_uniform.json")
    a = ap.parse_args()
    print(f"[E4-1c · docs/83 §26] n={a.n} · delta={list(DELTAS)} · "
          f"fresh seeds {a.ep0}..{a.ep0+a.n-1}", flush=True)

    arms = {}
    for D in DELTAS:
        rows, t0 = [], time.time()
        for i in range(a.n):
            rows.append(episode_e4(a.ep0 + i, D, "uniform"))
            if (i + 1) % 50 == 0 or i + 1 == a.n:
                el = time.time() - t0
                print(f"    [d={D:.3f}] {i+1}/{a.n}  {el:6.1f}s "
                      f"(ETA {el/(i+1)*(a.n-i-1):5.0f}s)", flush=True)
        n = len(rows)
        hk = sum(1 for r in rows if r["label"] == "HARD_KILL")
        pen = sum(1 for r in rows if r["label"] == "PENETRATED")
        cap = sum(1 for r in rows if r["label"] in CAP)
        db = np.array([r["d_min_best"] for r in rows])
        arms[f"{D:.3f}"] = {
            "delta": D, "n": n, "p_hk": hk / n, "p_hk_wilson": list(wilson(hk, n)),
            "p_pen": pen / n, "p_net": cap / n,
            "p_reach": float((db <= R_CONTACT).mean()),
            "d_min_best_med": float(np.median(db)),
            "range_t_min_med": float(np.median([r["range_t_min"] for r in rows])),
            "clamp_episode_frac": sum(1 for r in rows if r["n_clamp"] > 0) / n,
            "records": rows}
        A = arms[f"{D:.3f}"]
        print(f"\n  delta={D:.3f}  **P_HK {A['p_hk']:.4f}** "
              f"{tuple(round(x,3) for x in A['p_hk_wilson'])} · net {A['p_net']:.4f} · "
              f"pen {A['p_pen']:.4f} · 접촉권 {A['p_reach']:.4f}")
        print(f"    d_min med {A['d_min_best_med']:.3f} · "
              f"range(t_min) med {A['range_t_min_med']:.3f} (dispersion 0 확인) · "
              f"clamp {A['clamp_episode_frac']:.3f}", flush=True)
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(
            json.dumps({"partial": True, "arms": arms}, ensure_ascii=False, indent=1),
            encoding="utf-8")

    # paired 비교 (전부 동일 CRN)
    rng = np.random.default_rng(0)
    hks = {k: np.array([r["label"] == "HARD_KILL" for r in v["records"]], float)
           for k, v in arms.items()}
    idx = rng.integers(0, a.n, size=(20000, a.n))
    paired = {}
    for x, y in (("0.000", "0.125"), ("0.000", "0.250"), ("0.125", "0.250")):
        d = hks[y] - hks[x]
        lo, hi = np.percentile((hks[y][idx] - hks[x][idx]).mean(1), [2.5, 97.5])
        paired[f"{y} vs {x}"] = {"d_p_hk": float(d.mean()),
                                 "ci95": [float(lo), float(hi)]}
        print(f"  paired {y} vs {x}: ΔP_HK {d.mean():+.4f} CI95 [{lo:+.4f}, {hi:+.4f}]",
              flush=True)

    p0, p1, p2 = (arms[f"{d:.3f}"]["p_hk"] for d in DELTAS)
    c1 = paired["0.125 vs 0.000"]["ci95"]; c2 = paired["0.250 vs 0.125"]["ci95"]
    u1 = c1[0] > 0
    verdict = ("U4 (세 arm 차이 없음 — E4-1b 의 0.363 은 campaign effect 가능)"
               if not u1 and paired["0.250 vs 0.000"]["ci95"][0] <= 0 <= paired["0.250 vs 0.000"]["ci95"][1]
               else "U2 (longer lead benefit: 0.25 > 0.125 > 0)" if u1 and c2[0] > 0
               else "U3 (intermediate optimum / over-leading)" if u1
               else "U1 부분 — 판정표 재확인 필요")
    print(f"\n★ 판정 (§26.4 동결): {verdict}", flush=True)

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(stamp(artifact="e4c_uniform_lead"),
                            prereg_doc="docs/83 §26 (E4-1c)", deltas=list(DELTAS),
                            fresh_seed_block=[a.ep0, a.ep0 + a.n - 1], n=a.n,
                            primary="paired P_HK",
                            note="delta_i uniform -> temporal dispersion 구조적 0"),
           "arms": {k: {kk: vv for kk, vv in v.items() if kk != "records"}
                    for k, v in arms.items()},
           "paired": paired, "verdict": verdict,
           "records": {k: v["records"] for k, v in arms.items()}}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    print(f"  -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
