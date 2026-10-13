"""가정 민감도 수치 검증 (증거 0-1 ~ 0-3) — 계약 아님 (학습 없는 해석 검증, 허용치 사전 기재).

정본 판정 함수 (viability.v_shot, se3_cone, n_segments 4, 표본 2000) 로 "보장 포획 순간이 존재하는 최대 위협 가속" a* 를 찾아
해석식과 비교한다. 발사기는 원점, 도달 구 중심은 x 축 위 거리 x (x 를 격자로 훑어 하나라도 보장이면 '존재'), 경로 제한 기체 없음.

  기준      a*0 = 2 ρ χ*_geom / τ²,  ρ = R tanθ,  χ*_geom = cosθ/(1+sinθ)
  0-2 반응 지연 τ_r : 회피자는 처음 τ_r 동안 기동을 바꾸지 못함 (등속) → 도달 구 반경 ½a(τ−τ_r)²  → a* = a*0 [τ/(τ−τ_r)]²
  0-1 추적 지연 L   : 방어는 L 만큼 오래된 위치·속도만 앎 → 마지막 관측에서 τ+L 동안의 도달 구 (중심 p + v(τ+L), 반경 ½a(τ+L)²)
                      → a* = a*0 [τ/(τ+L)]²
  0-3 조준 오차 δ   : 발사축이 도달 구 중심 방향에서 δ 만큼 어긋남 → 옆면 조건 x sin(θ−δ) ≥ w → χ*_geom(δ) = 1/[tanθ(1 + 1/sin(θ−δ))]
                      (해석식은 사거리 끝을 R − x ≥ w 로 둔다; 판정은 축 방향 평면 x cosδ + w ≤ R 이라 δ > 0 에서 판정 쪽이 약간 관대할 수 있음)

**사전 허용치 (실행 전 기재, 2026-10-13)**: 모든 경우 |a*_수치 − a*_해석| / a*_해석 ≤ 0.02 이면 PASS. 부호를 함께 보고한다.
주의: 0-1·0-2 의 수치 판정은 같은 판정 함수에 바뀐 시간 지평을 넣은 것이라, 식의 기하 (도달 구 ⊂ 원뿔, 다구간 기동 포함) 를 검증하지
지연 모형 자체의 현실성을 검증하지 않는다.

    .venv/Scripts/python scripts/paper1_assumption_check.py   → artifacts/paper1/assumption_check.json
"""
from __future__ import annotations

import json
import pathlib

import numpy as np

from shepherd.game import viability as V

ROOT = pathlib.Path(__file__).resolve().parents[1]
TAU, TH, R = 0.3, 0.21209009342092547, 8.22
RHO_W = R * np.tan(TH)
CHI0 = np.cos(TH) / (1 + np.sin(TH))
A0 = 2 * RHO_W * CHI0 / TAU ** 2
TOL = 0.02
XS = np.linspace(0.3, R, 240)                     # 발사기–도달 구 중심 거리 격자


def robust_exists(a, tau_eff, delta):
    """어떤 거리 x 에서든 보장 포획이면 True. 정지 표적 (v = 0) — 도달 구 중심이 곧 현재 위치 (경계는 v 와 무관)."""
    n_f = np.array([np.cos(delta), np.sin(delta), 0.0])
    for x in XS:
        r = V.v_shot(np.array([x, 0.0, 0.0]), np.zeros(3), tau=tau_eff, a_att_max=a, judge="se3_cone",
                     net_apex=np.zeros(3), n_F=n_f, theta_net=TH, range_min=0.0, range_max=R,
                     n=2000, seed=0, n_segments=4)
        if r.v_shot_worst == 1.0:
            return True
    return False


def a_star(tau_eff, delta=0.0):
    lo, hi = 0.5, 400.0                               # lo 는 보장 존재, hi 는 부재
    for _ in range(22):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if robust_exists(mid, tau_eff, delta) else (lo, mid)
    return 0.5 * (lo + hi)


def main():
    cases = [("base", 0.0, 0.0, 0.0, A0)]
    cases += [("reaction", tr, 0.0, 0.0, A0 * (TAU / (TAU - tr)) ** 2) for tr in (0.05, 0.10, 0.15)]
    cases += [("tracking", 0.0, L, 0.0, A0 * (TAU / (TAU + L)) ** 2) for L in (0.05, 0.10, 0.15)]
    for deg in (1, 2, 3, 5, 8):
        d = np.radians(deg)
        chi = 1 / (np.tan(TH) * (1 + 1 / np.sin(TH - d)))
        cases.append(("aim", 0.0, 0.0, deg, 2 * RHO_W * chi / TAU ** 2))
    rows = []
    for kind, tr, L, deg, ana in cases:
        num = a_star(TAU - tr + L, np.radians(deg))
        rel = (num - ana) / ana
        rows.append({"kind": kind, "tau_r": tr, "L": L, "delta_deg": deg, "analytic": round(float(ana), 3),
                     "numeric": round(float(num), 3), "rel_err": round(float(rel), 5), "pass": bool(abs(rel) <= TOL)})
        print(rows[-1], flush=True)
    out = {"tolerance": f"|rel err| <= {TOL}, registered before run", "verdict": "PASS" if all(r["pass"] for r in rows)
           else "FAIL", "max_abs_rel_err": max(abs(r["rel_err"]) for r in rows), "rows": rows}
    (ROOT / "artifacts" / "paper1" / "assumption_check.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(out["verdict"], out["max_abs_rel_err"])


if __name__ == "__main__":
    main()
