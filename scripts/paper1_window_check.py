"""층 2 (실용 창) 수치 검증 — spine v6 §0.6 (가)–(다). 계약 아님 (학습 없는 해석 검증, 지도교수 10-12 조건: 허용치 사전 기재).

정본 판정 함수 (viability.v_shot, se3_cone, n_segments 4, 표본 2000 — FS1 env 와 같은 설정) 로, 등속 직선 접근하는 공격자의
보장 포획 구간 길이를 재서 해석식과 비교한다. 이상 조준 (δ = 0): net 축 = 발사기 → 도달 구 중심 p + vτ. 경로 제한 기체 없음.

  (나)·(다) 해석식 (첫 통과 구간): b < D_min → [√(D_max² − b²) − √(D_min² − b²)] / V,  D_min ≤ b < D_max → 2√(D_max² − b²) / V,
  D_min = w/sinθ, D_max = R − w, b = 조준점 경로와 발사기의 최근접 거리.

**사전 허용치 (실행 전 기재, 2026-10-12)**: |측정 − 해석| ≤ max(0.02 × 해석, 0.05 s) 를 모든 경우에서 만족하면 PASS.
유한 표본 판정은 경계에서 보수적이라 측정 ≤ 해석 쪽 한방향 오차를 예상하고 부호를 함께 보고한다.

    .venv/Scripts/python scripts/paper1_window_check.py   → artifacts/paper1/window_check.json
"""
from __future__ import annotations

import json
import pathlib

import numpy as np

from shepherd.game import viability as V

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAU, TH, R = 0.3, 0.21209009342092547, 8.22              # E7-a probe consts (FS1 기준 net)
RHO_W = R * np.tan(TH)                                   # 반폭 1.77 m (KSAS ρ)
CHIS = (0.10, 0.25, 0.40, 0.52, 0.70)
SPEEDS = (15.0, 23.01, 35.0)
B_FRAC = (0.0, 0.25, 0.5, 0.75, 1.0)
TOL_REL, TOL_ABS = 0.02, 0.05                            # 사전 허용치


def robust(c, vel, a):
    """조준점 c (= p + vτ) 에서 발사하면 보장 포획인가 (worst == 1)."""
    x = c - vel * TAU
    n_f = c / np.linalg.norm(c)
    r = V.v_shot(x, vel, tau=TAU, a_att_max=a, judge="se3_cone", net_apex=np.zeros(3), n_F=n_f, theta_net=TH,
                 range_min=0.0, range_max=R, n=2000, seed=0, n_segments=4)
    return r.v_shot_worst == 1.0


def analytic(b, vs, w):
    dmin, dmax = w / np.sin(TH), R - w
    if b >= dmax or dmin >= dmax:
        return 0.0
    if b < dmin:
        return (np.sqrt(dmax ** 2 - b ** 2) - np.sqrt(dmin ** 2 - b ** 2)) / vs
    return 2 * np.sqrt(dmax ** 2 - b ** 2) / vs


def measured(b, vs, a):
    """조준점이 (b, y) 에서 y 방향 −vs 로 움직임. 첫 보장 구간의 길이 (거친 격자 0.004 s + 경계 이분법 1e-4 s)."""
    vel = np.array([0.0, -vs, 0.0])
    y0 = R + 1.0
    c_at = lambda t: np.array([b, y0 - vs * t, 0.0])
    t_end = (y0 + R) / vs
    ts = np.arange(0.0, t_end, 0.004)
    flags = [robust(c_at(t), vel, a) if np.linalg.norm(c_at(t)) > 1e-6 else False for t in ts]
    if not any(flags):
        return 0.0
    i0 = flags.index(True)
    i1 = next((i for i in range(i0, len(flags)) if not flags[i]), len(flags))

    def edge(lo, hi, want_robust_at_hi):
        for _ in range(16):
            mid = 0.5 * (lo + hi)
            if robust(c_at(mid), vel, a) == want_robust_at_hi:
                hi = mid
            else:
                lo = mid
        return 0.5 * (lo + hi)
    t_in = edge(ts[i0 - 1] if i0 else 0.0, ts[i0], True)
    t_out = edge(ts[i1 - 1], ts[i1], False) if i1 < len(ts) else ts[-1]
    return float(t_out - t_in)


def main():
    rows = []
    for chi in CHIS:
        a = chi * 2 * RHO_W / TAU ** 2
        w = 0.5 * a * TAU ** 2
        for vs in SPEEDS:
            for bf in B_FRAC:
                b = bf * (R - w)
                ta, tm = analytic(b, vs, w), measured(b, vs, a)
                tol = max(TOL_REL * ta, TOL_ABS)
                rows.append({"chi": chi, "V": vs, "b_frac_Dmax": bf, "b": round(b, 4), "analytic_s": round(ta, 5),
                             "measured_s": round(tm, 5), "err_s": round(tm - ta, 5), "tol_s": round(tol, 5),
                             "pass": abs(tm - ta) <= tol})
                print(rows[-1])
    out = {"tolerance": f"|measured - analytic| <= max({TOL_REL} x analytic, {TOL_ABS} s), registered before run",
           "verdict": "PASS" if all(r["pass"] for r in rows) else "FAIL", "n": len(rows),
           "max_abs_err_s": max(abs(r["err_s"]) for r in rows),
           "sign": {"measured<analytic": sum(r["err_s"] < 0 for r in rows), "measured>analytic": sum(r["err_s"] > 0 for r in rows)},
           "rows": rows}
    (ROOT / "artifacts" / "paper1" / "window_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(out["verdict"], out["max_abs_err_s"], out["sign"])


if __name__ == "__main__":
    main()
