"""E1e 법칙 정정 재계산 — 동결 레코드 위에서 두 규약을 대조한다.

    python -m shepherd.scripts.e1e_law_recompute [--out results/e1e_law_recompute.json]

**새 표본이 아니다. 재실행도 아니다.** `results/e1e.json` 이 이미 담고 있는
에피소드 레코드(ax_realized · a_att · captured)만 읽어, 사후 계산 항목
(a* 예측 · S1 마진 분류 · S2 비율)을 정정 규약으로 다시 낸다. 롤아웃은 env 의
`viability._caught_se3_cone` 이 하고 이 법칙을 쓰지 않으므로, 같은 시드 재실행은
bit-identical 레코드를 낼 뿐이다 -- 그래서 재실행이 아니라 재계산이 맞다.

정정 사유는 결과와 무관한 **기하 도출 오류**다 (`e1e_axial_optimum` 의 규약 주석
참조): 포획영역은 볼록이고 도달집합은 등방 구이므로 s 는 내접구 반경이며, 축 위의
점에서 원뿔 측면까지의 수직거리는 ax*sin(theta) 다. ax*tan(theta) 는 축에 수직인
반폭이라 등방 구에 맞지 않는다.

원 아티팩트는 **덮지 않는다** (docs/81 §1-2 소급 수정 금지). 사전등록 판정은
그대로 유효하며 -- 판별 가설 H3 는 far-edge 가 binding 이라 두 규약에서 동일하다 --
이 산출물은 그 위에 얹는 정정 기록이다.
torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_config import m4_config                              # noqa: E402
from shepherd.scripts.e1e_axial_optimum import (ARMS, a_star,         # noqa: E402
                                                ax_optimum, margin, s_of_ax)

CONVENTIONS = ("tan", "inscribed")          # 동결 · 정본


def _geom():
    cfg = m4_config()
    return dict(theta=float(cfg["viability"]["cone"]["half_angle"]),
                rmax=float(cfg["viability"]["cone"]["range_max"]),
                tau=float(cfg["physics"]["tau_deploy"]),
                rho=float(cfg["physics"]["net_radius"]))


def recompute(src: pathlib.Path) -> dict:
    g = _geom()
    theta, rmax, tau, rho = g["theta"], g["rmax"], g["tau"], g["rho"]
    d = json.loads(src.read_text(encoding="utf-8", errors="replace"))
    frozen = {a["target_ax"]: a for a in d["arms"]} if isinstance(d["arms"], list) \
        else {v["target_ax"]: v for v in d["arms"].values()}

    out: dict = {"note": "post-hoc recomputation of frozen E1e records; no new samples",
                 "source": str(src.as_posix()), "geometry": g, "conventions": {}}
    for cv in CONVENTIONS:
        kw = dict(theta=theta, rmax=rmax, tau=tau, convention=cv)
        x_opt = ax_optimum(theta=theta, rmax=rmax, convention=cv)
        s_max = float(s_of_ax(x_opt, theta=theta, rmax=rmax, convention=cv))
        arms, ratios = {}, []
        for nm, tgt in ARMS:
            ok = [r for r in d["records"][nm]
                  if not r["excluded"] and r["ax_realized"] is not None]
            m = margin([r["ax_realized"] for r in ok],
                       [r["a_att"] for r in ok], **kw)
            cap = np.array([bool(r["captured"]) for r in ok])
            pred = float(a_star(tgt, **kw))
            c50 = frozen[tgt].get("cross50")          # 측정값 -- 규약 무관, 불변
            # E-4 는 cross50 정의 불가(nan)이고 **그것이 사전등록 예측**이다.
            # nan 은 JSON 표준이 아니므로 None 으로 눕히고 비율에서 제외한다.
            if c50 is None or c50 != c50:
                c50, ratio = None, None
            else:
                ratio = c50 / pred
                ratios.append(ratio)
            row = {"target_ax": tgt, "n": len(ok), "a_star_pred_nominal": pred,
                   "margin_accuracy": float(((m > 0) == cap).mean()),
                   "cross50": c50, "ratio_cross50_over_pred": ratio}
            arms[nm] = row
        out["conventions"][cv] = {
            "ax_optimum": x_opt, "s_max": s_max, "s_max_over_rho": s_max / rho,
            "a_star_geom": 2.0 * s_max / tau ** 2,
            "chi_star_geom": s_max / rho,
            "arms": arms,
            "s2_ratio_mean": float(np.mean(ratios)),
            "s2_ratio_sd": float(np.std(ratios, ddof=1)),
            "s1_min_accuracy": min(v["margin_accuracy"] for v in arms.values()),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="results/e1e.json")
    ap.add_argument("--out", default="results/e1e_law_recompute.json")
    a = ap.parse_args()
    res = recompute(ROOT / a.src)
    (ROOT / a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    for cv, c in res["conventions"].items():
        print(f"[{cv:9s}] ax*={c['ax_optimum']:.4f}  s_max={c['s_max']:.4f}"
              f" = {c['s_max_over_rho']:.4f} rho  a*_geom={c['a_star_geom']:.2f}"
              f"  chi*={c['chi_star_geom']:.4f}")
        for nm, r in c["arms"].items():
            print(f"    {nm} ax={r['target_ax']:<5} pred={r['a_star_pred_nominal']:6.2f}"
                  f"  S1={r['margin_accuracy']:.4f}"
                  f"  ratio={r['ratio_cross50_over_pred'] if r['ratio_cross50_over_pred'] is None else round(r['ratio_cross50_over_pred'], 4)}")
        print(f"    S1 min={c['s1_min_accuracy']:.4f} (사전등록 수락 >=0.95)"
              f"   S2 {c['s2_ratio_mean']:.4f} +- {c['s2_ratio_sd']:.4f}")
    print("->", a.out)


if __name__ == "__main__":
    main()
