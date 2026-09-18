"""동결 곡선을 **해석적 경계**로 재집계 (KSAS 본문 §3 수치의 단일 산지).

    python -m shepherd.scripts.analytic_bands [--out results/analytic_bands.json]

종전 본문은 사전 선언 분할값 25.8 m/s^2 (잔여 조준각 중앙값 유래) 로 구간을
갈랐다. 그 값은 인과 경계가 아니고 논문의 두 해석적 경계(rho 기반 39.33,
유한 원뿔 31.77)와 무관해 독자에게 세 번째 경계처럼 읽혔다. 여기서는 **논문이
유도한 두 경계로만** 자른다:

    a_att < a_geom            유한 원뿔 상계 아래
    a_geom <= a_att < a_rho   두 상계 사이
    a_att >= a_rho            rho 기반 필요조건 밖

**재집계다. 새 표본이 아니다.** 라벨/시드/롤아웃은 동결본 그대로이고 경계만
바꾼다. 경계는 e1e 정본 법칙(기본 규약 inscribed)에서 유도하므로 본문 식 (4)(5)
와 자동으로 일치한다 -- 여기서 상수를 다시 쓰지 않는다.

검열(censoring) 주의: 등록 발사 게이트는 a_att >= 32.2 에서 발사를 내지 않는다
(E1c). 따라서 중간 구간의 0 은 **부분 검열**이고 (일부는 발사 가능 구간),
a_att >= a_rho 의 0 은 전량 검열이다. 이 분해도 함께 낸다.
torch-free.
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_config import m4_config                              # noqa: E402
from shepherd.scripts.e1e_axial_optimum import a_star, ax_optimum     # noqa: E402
from shepherd.stats import wilson                                     # noqa: E402

ARMS = {"hold": "results/curve_hold_reactive.json",
        "intercept": "results/curve_intercept_reactive.json"}
A_DRY = 32.2          # 발사 게이트가 침묵하는 하한 (E1c, docs/83 §14)


def bounds() -> dict:
    c = m4_config()
    th = float(c["viability"]["cone"]["half_angle"])
    rmax = float(c["viability"]["cone"]["range_max"])
    tau = float(c["physics"]["tau_deploy"])
    rho = float(c["physics"]["net_radius"])
    x_opt = ax_optimum(theta=th, rmax=rmax)
    return {"a_geom": float(a_star(x_opt, theta=th, rmax=rmax, tau=tau)),
            "a_rho": 2.0 * rho / tau ** 2, "tau": tau, "rho": rho,
            "ax_optimum": x_opt}


def _rows(p: pathlib.Path) -> list[dict]:
    return json.loads(io.open(p, encoding="utf-8", errors="replace").read())["records"]


def run(root: pathlib.Path) -> dict:
    b = bounds()
    g, r = b["a_geom"], b["a_rho"]
    out: dict = {"note": "re-aggregation of frozen curves by analytic bounds; "
                         "no new samples", "bounds": b, "a_dry": A_DRY, "arms": {}}
    for arm, rel in ARMS.items():
        rows = _rows(root / rel)
        bands = [("below_cone", lambda a: a < g),
                 ("between", lambda a: g <= a < r),
                 ("above_rho", lambda a: a >= r)]
        res = {}
        for nm, sel in bands:
            S = [x for x in rows if sel(x["a_att"])]
            k = sum(1 for x in S if x["label"] == "NET_CAPTURE")
            hk = sum(1 for x in S if x["label"] == "HARD_KILL")
            lo, hi = wilson(k, len(S))
            # 검열 분해: 발사 게이트가 살아 있는 부분집합
            live = [x for x in S if x["a_att"] < A_DRY]
            res[nm] = {"n": len(S), "net_capture": k, "p_net": k / len(S),
                       "wilson95": [lo, hi], "neutralized": (k + hk) / len(S),
                       "n_uncensored": len(live),
                       "net_capture_uncensored": sum(
                           1 for x in live if x["label"] == "NET_CAPTURE")}
        caps = [x["a_att"] for x in rows if x["label"] == "NET_CAPTURE"]
        res["max_a_att_with_capture"] = max(caps) if caps else None
        out["arms"][arm] = res
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/analytic_bands.json")
    a = ap.parse_args()
    res = run(ROOT)
    (ROOT / a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    b = res["bounds"]
    print(f"a_geom={b['a_geom']:.4f}  a_rho={b['a_rho']:.4f}")
    for arm, d in res["arms"].items():
        print(f"[{arm}] 포획 최대 a_att = {d['max_a_att_with_capture']:.3f}")
        for nm in ("below_cone", "between", "above_rho"):
            v = d[nm]
            print(f"   {nm:11s} net {v['net_capture']:4d}/{v['n']:4d}"
                  f" = {v['p_net']:.4f}  CI[{v['wilson95'][0]:.3f},"
                  f"{v['wilson95'][1]:.3f}]  무력화 {v['neutralized']:.4f}"
                  f"  (비검열 {v['net_capture_uncensored']}/{v['n_uncensored']})")
    print("->", a.out)


if __name__ == "__main__":
    main()
