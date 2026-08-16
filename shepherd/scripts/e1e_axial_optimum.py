"""E1e — 보정 capture-bound 의 fresh confirmation (docs/83 §32 동결 프로토콜).

성격
----
E1d 의 D-a/D-b **재현이 아니다**. §28.3 에서 **결과를 본 뒤** 도출한 piecewise law

    s(ax) = min(ax*tan(theta), R_max - ax),      a*(ax) = 2*s(ax)/tau^2

자체를 미사용 seed 에서 시험한다. 예측은 단조 증가가 아니라 **inverted-U** 이고
내부 최적은 ax* = R_max/(1+tan(theta)) = 6.763546 m.

판별점 (§32.2)
--------------
  E-3 (ax 7.20) 이 유일한 미관측 판별 지점이다.
    기존 lateral-only 법칙:  a*(7.20) = 34.45  > a*(6.75) = 32.30   -> 증가
    보정 법칙            :  a*(7.20) = 22.67  < a*(6.75) = 32.30   -> 감소
  E-1(5.50) 은 두 법칙이 같은 값이라 판별력이 없고, E-4(7.90) 는 E1d 기관측.

Primary 는 a*_50 이 아니라 **shape** 이다 (E1d 에서 cross50=nan 전례, §32.3):
    H1  P_C(6.75) > P_C(5.50)
    H2  P_C(6.75) > P_C(7.90)
    H3  P_C(7.20) < P_C(6.75)      <- 기존 법칙은 반대를 예측

    python -m shepherd.scripts.e1e_axial_optimum --n 300 --out results/e1e.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import time
from typing import Optional

import numpy as np

from shepherd.m4_config import m4_config
from shepherd.scripts.curve_sweep import _cross50, bin_edges
from shepherd.scripts.e1d_commit_geom import _select_step, forced_pass, reference_pass
from shepherd.stats import wilson

__all__ = ["ARMS", "EP0", "a_star", "s_of_ax", "margin"]

#: fresh seed block (§32.2). 기존 캠페인 0.. / 10000.. / 30000..30299 과 미교차.
EP0 = 31000

#: (이름, target ax). 전 arm 공통: ideal aim (psi=0) · omega 기본값.
ARMS = (("E-1", 5.50), ("E-2", 6.75), ("E-3", 7.20), ("E-4", 7.90))

#: shape primary (§32.3). (라벨, 좌, 우, 방향) — 방향 +1 이면 좌 > 우 를 예측.
SHAPE = (("H1", "E-2", "E-1", +1),
         ("H2", "E-2", "E-4", +1),
         ("H3", "E-2", "E-3", +1))          # P_C(6.75) > P_C(7.20)


def s_of_ax(ax, *, tan_th: float, rmax: float):
    """지배 제약 여유 s = min(lateral, far-edge). 배열/스칼라 모두 허용."""
    ax = np.asarray(ax, float)
    return np.minimum(ax * tan_th, rmax - ax)


def a_star(ax, *, tan_th: float, rmax: float, tau: float):
    """보정 capture-bound a* = 2 s / tau^2."""
    return 2.0 * s_of_ax(ax, tan_th=tan_th, rmax=rmax) / tau ** 2


def margin(ax, a_att, *, tan_th: float, rmax: float, tau: float):
    """S1 (§32.5) episode-level 마진 m = a*(ax_realized) - a_att."""
    return a_star(ax, tan_th=tan_th, rmax=rmax, tau=tau) - np.asarray(a_att, float)


def _paired_ci(x: np.ndarray, y: np.ndarray, *, seed: int = 0, n_boot: int = 20000):
    """paired bootstrap (같은 에피소드) 로 mean(x) - mean(y) 의 CI95."""
    d = x.astype(float) - y.astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    lo, hi = np.percentile(d[idx].mean(1), [2.5, 97.5])
    return float(d.mean()), float(lo), float(hi)


def main() -> None:
    ap = argparse.ArgumentParser(description="E1e axial optimum (docs/83 §32)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--ep0", type=int, default=EP0)
    ap.add_argument("--out", default="results/e1e.json")
    a = ap.parse_args()

    cfg = m4_config()
    tau = float(cfg["physics"]["tau_deploy"])
    rmax = float(cfg["viability"]["cone"]["range_max"])
    th = float(cfg["viability"]["cone"]["half_angle"])
    rho = float(cfg["physics"]["net_radius"])
    tan_th = math.tan(th)
    ax_opt = rmax / (1.0 + tan_th)
    kw = dict(tan_th=tan_th, rmax=rmax, tau=tau)

    print(f"[E1e · docs/83 §32] n={a.n} · seeds {a.ep0}..{a.ep0+a.n-1} · "
          f"tau {tau} · R_max {rmax} · theta {math.degrees(th):.4f}deg · "
          f"tan {tan_th:.6f} · ax* {ax_opt:.6f}", flush=True)
    print("  동결 예측 a*: " + " · ".join(
        f"{nm}({tgt}) {float(a_star(tgt, **kw)):.2f}" for nm, tgt in ARMS), flush=True)

    # --- Pass 1 (4 arm 공유, §32.2 / 회귀 E-C) -----------------------------
    eps = list(range(a.ep0, a.ep0 + a.n))
    refs, sel, t0 = {}, {}, time.time()
    for i, ep in enumerate(eps):
        r = reference_pass(ep, tau, rmax)
        refs[ep] = r
        sel[ep] = {nm: _select_step(r, tgt) for nm, tgt in ARMS}
        if (i + 1) % 50 == 0 or i + 1 == a.n:
            el = time.time() - t0
            print(f"    [pass1] {i+1}/{a.n}  {el:6.1f}s "
                  f"(ETA {el/(i+1)*(a.n-i-1):5.0f}s)", flush=True)

    edges = bin_edges(11.0, 78.0, 2 * rho / tau ** 2, per_side=4)
    arms, cap_by_arm = {}, {}
    for nm, tgt in ARMS:
        rows, t1 = [], time.time()
        for i, ep in enumerate(eps):
            s = sel[ep][nm]
            if s is None:
                rows.append({"episode": ep, "step": None, "excluded": True,
                             "captured": False, "ax_realized": None})
                continue
            r = forced_pass(ep, s, ideal=True, omega=None, tau=tau, rmax=rmax)
            r["a_att"] = refs[ep]["a_att"]
            r["att_speed"] = refs[ep]["att_speed"]
            r["excluded"] = False
            rows.append(r)
            if (i + 1) % 50 == 0 or i + 1 == a.n:
                el = time.time() - t1
                print(f"    [{nm}] {i+1}/{a.n}  {el:6.1f}s "
                      f"(ETA {el/(i+1)*(a.n-i-1):5.0f}s)", flush=True)

        ok = [r for r in rows if not r["excluded"]]
        cap = np.array([bool(r["captured"]) for r in rows])       # 제외분은 False
        cap_by_arm[nm] = cap
        axs = np.array([r["ax_realized"] for r in ok if r["ax_realized"] is not None])
        psis = np.array([r["psi_at_commit"] for r in ok
                         if r.get("psi_at_commit") is not None])

        # S1: episode-level 마진 분류 (realized ax 사용, §32.5)
        m_ok = [r for r in ok if r["ax_realized"] is not None]
        mm = margin([r["ax_realized"] for r in m_ok],
                    [r["a_att"] for r in m_ok], **kw)
        cc = np.array([bool(r["captured"]) for r in m_ok])
        acc = float(((mm > 0) == cc).mean()) if len(cc) else float("nan")

        # S2: a*_50 (정의 불가면 nan -- E-4 는 그게 예측이다)
        aa = np.array([r["a_att"] for r in ok])
        p_bin, n_bin = [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel_b = (aa >= lo) & (aa < hi)
            n_bin.append(int(sel_b.sum()))
            p_bin.append(float(np.mean([r["captured"] for r, s_ in zip(ok, sel_b) if s_]))
                         if sel_b.sum() else float("nan"))
        c50 = _cross50(edges, p_bin)

        arms[nm] = {
            "target_ax": tgt, "n": len(rows), "n_excluded": int(sum(r["excluded"] for r in rows)),
            "n_fired": int(sum(1 for r in ok if r.get("fired"))),
            "p_capture": float(cap.mean()), "p_capture_wilson": list(wilson(int(cap.sum()), len(cap))),
            "ax_realized": {"med": float(np.median(axs)), "p25": float(np.percentile(axs, 25)),
                            "p75": float(np.percentile(axs, 75))} if axs.size else None,
            "psi_at_commit_deg": {"med": float(np.degrees(np.median(psis)))} if psis.size else None,
            "a_star_pred_nominal": float(a_star(tgt, **kw)),
            "a_star_pred_realized_med": float(np.median(a_star(axs, **kw))) if axs.size else None,
            "cross50": c50, "p": p_bin, "n_per_bin": n_bin,
            "margin_accuracy": acc, "margin_n": int(len(cc)),
            "records": rows,
        }
        A = arms[nm]
        print(f"\n  {nm} (ax {tgt}): 제외 {A['n_excluded']} 발사 {A['n_fired']}")
        print(f"    ax_realized med {A['ax_realized']['med']:.4f} · "
              f"psi med {A['psi_at_commit_deg']['med']:.4f}deg")
        print(f"    **P_C {A['p_capture']:.4f}** "
              f"{tuple(round(x,4) for x in A['p_capture_wilson'])} · "
              f"cross50 {c50} (예측 {A['a_star_pred_nominal']:.2f})")
        print(f"    S1 마진분류 정확도 {acc:.4f} (n={A['margin_n']})", flush=True)
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(
            json.dumps({"partial": True, "arms": {k: {kk: vv for kk, vv in v.items()
                                                      if kk != "records"}
                                                 for k, v in arms.items()}},
                       ensure_ascii=False, indent=1), encoding="utf-8")

    # --- Primary: shape (§32.3) --------------------------------------------
    print("\n" + "=" * 62)
    shape = {}
    for lab, L, Rr, sign in SHAPE:
        d, lo, hi = _paired_ci(cap_by_arm[L], cap_by_arm[Rr])
        holds = bool((lo > 0.0) if sign > 0 else (hi < 0.0))
        shape[lab] = {"left": L, "right": Rr, "delta": d, "ci95": [lo, hi], "holds": holds}
        print(f"  {lab}: P_C({L}) - P_C({Rr}) = {d:+.4f}  CI95 [{lo:+.4f}, {hi:+.4f}]  "
              f"-> {'HOLDS' if holds else 'fails'}")

    # --- 판정 (§32.4, 결과 전 동결) ----------------------------------------
    h1, h2, h3 = (shape["H1"]["holds"], shape["H2"]["holds"], shape["H3"]["holds"])
    mono = float(np.mean(cap_by_arm["E-4"])) >= float(np.mean(cap_by_arm["E-2"]))
    if h1 and h2 and h3:
        verdict = "E1e-A (보정 법칙 확인 — 사후 -> confirmatory 승격)"
    elif mono:
        verdict = "E1e-C (단조 증가 — 보정 법칙 반증, lateral-only 복권)"
    elif h1 and h2:
        verdict = "E1e-B (내부 최적 존재하나 위치/형태 오설정 — 승격 보류)"
    else:
        verdict = "E1e-D (INCONCLUSIVE)"
    print(f"\n★ 판정 (§32.4 동결): {verdict}")

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(
               stamp(artifact="e1e_axial_optimum"), prereg_doc="docs/83 §32 (E1e)",
               law="s(ax) = min(ax*tan(theta), R_max - ax); a* = 2 s / tau^2",
               ax_opt=ax_opt, tan_theta=tan_th, tau=tau, r_max=rmax,
               primary="shape (H1,H2,H3) -- a*_50 아님 (§32.3)",
               discriminator="E-3 (ax 7.20): lateral-only 는 증가, 보정 법칙은 감소",
               world="ratified + T1 + hold + forced commit only · ideal aim (psi=0)",
               fresh_seed_block=[a.ep0, a.ep0 + a.n - 1], n=a.n,
               caveat=("perfect aim 은 실현 불가능한 반사실이다. arm 별 포획률을 "
                       "시스템 성능으로 읽지 않는다. 이 법칙은 idealized "
                       "forced-commit terminal geometry 의 법칙일 뿐이다 (§32.7)")),
           "arms": {k: {kk: vv for kk, vv in v.items() if kk != "records"}
                    for k, v in arms.items()},
           "shape": shape, "verdict": verdict,
           "records": {k: v["records"] for k, v in arms.items()}}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    print(f"  -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
