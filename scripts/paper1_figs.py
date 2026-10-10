"""Paper 1 v0 그림 1·2 재현 스크립트 (docs/131 §2).

그림 1 = 해석 도식 (데이터 없음, 상수는 E7-a probe.json consts).
그림 2 = (a) 프로브 창 관측 (E7-a3 overlay) + 해석 곡선 N(ρ; θ) / (b) 정합 감사 천장 (A안 계보만:
arm C-① det, E7-b det, E7-b′ sto). E7-c 는 넣지 않는다 (교전 규칙·지표가 다른 계보). 점 사이 보간선 없음.

실행: .venv/Scripts/python scripts/paper1_figs.py  →  artifacts/paper1/fig1_concept.png, fig2_money.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon, Wedge

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "artifacts" / "fs1"
OUT = ROOT / "artifacts" / "paper1"
MM = 1 / 25.4
plt.rcParams.update({"font.size": 8, "axes.linewidth": 0.6, "lines.linewidth": 1.0,
                     "savefig.dpi": 300, "font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans"})


def load(p):
    return json.loads((A / p).read_text(encoding="utf-8"))


K = load("e7a/probe.json")["consts"]
OV = load("e7a3/overlay.json")
TAU, TH, RMAX, AATT, DT = K["tau0"], K["theta0"], K["range_max"], K["a_att"], K["dt"]
R_ESC = 0.5 * AATT * TAU**2
D_MIN, D_MAX = R_ESC / np.sin(TH), RMAX - R_ESC
RHO = RMAX * np.tan(TH) / R_ESC
V_BAR, N_INF = OV["V_bar"], OV["N_inf"]


def rho0(th):
    return 1 / np.cos(th) + np.tan(th)


def rho_star(th, k=4.0):
    return rho0(th) / (1 - k * DT * V_BAR / RMAX)


# 자기 점검: 그림이 쓰는 상수 = 봉인 산출물의 값
_v = OV["variants"]["t1.0_h1.0_cv"]
assert abs(RHO - 1.923) < 1e-3 and abs(R_ESC - 0.920) < 1e-3
assert abs(D_MIN - _v["D_min"]) < 1e-3 and abs(D_MAX - _v["D_max"]) < 1e-3
assert abs(rho0(TH) - _v["rho0"]) < 1e-4 and abs(rho_star(TH) - _v["rho_star"]) < 1e-4
assert abs(rho_star(1.5 * TH) - OV["variants"]["t1.0_h1.5_cv"]["rho_star"]) < 1e-4
assert abs(N_INF - RMAX / (V_BAR * DT)) < 1e-3
assert abs(rho_star(TH, 3.5) - 2.427) < 1e-3  # 등록 불확실 대역 하단 (노트 10-08c)
RS_BAND = (rho_star(TH, 3.5), rho_star(TH))   # ρ* 대역 (θ₀): [3.5dt, 4dt]


# ---------------------------------------------------------------- 그림 1
def fig1():
    fig, ax = plt.subplots(figsize=(160 * MM, 62 * MM))
    th_deg = np.degrees(TH)
    # net 콘 (사거리 R_max)
    ax.add_patch(Wedge((0, 0), RMAX, -th_deg, th_deg, fc="0.93", ec="k", lw=0.8))
    # robust 영역: r 만큼 침식된 콘 = 꼭짓점 D_min, 같은 반각, 반경 R_max − r 구로 절단
    # 침식 콘 상측 경계 (꼭짓점 (D_MIN,0), 반각 TH) 와 반경 D_MAX 원의 교점은 수치로
    t_hit = np.linspace(0, D_MAX, 2000)
    px, py = D_MIN + t_hit * np.cos(TH), t_hit * np.sin(TH)
    k = np.argmax(np.hypot(px, py) > D_MAX)
    ex, ey = px[k], py[k]
    arc_a = np.linspace(-np.arctan2(ey, ex), np.arctan2(ey, ex), 40)
    poly = [(D_MIN, 0), (ex, -ey)] + list(zip(D_MAX * np.cos(arc_a), D_MAX * np.sin(arc_a))) + [(ex, ey)]
    ax.add_patch(Polygon(poly, closed=True, fc="0.78", ec="k", lw=0.6, hatch="////"))
    # 공격자 p, 속도, 조준점 c, 탈출 구
    c = np.array([5.8, 0.25])
    vdir = np.array([-np.cos(np.radians(6)), -np.sin(np.radians(6))])
    p = c - vdir * V_BAR * TAU
    ax.add_patch(Circle(c, R_ESC, fill=False, ec="k", lw=1.0, ls="--", zorder=4))
    ax.plot(*c, "k+", ms=7, mew=1.2, zorder=5)
    ax.plot(*p, "k^", ms=7, zorder=5)
    ax.annotate("", xy=c, xytext=p,
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color="k", shrinkA=5, shrinkB=0), zorder=5)
    ax.text(*(p + [0, 0.45]), r"attacker $p$", ha="center", fontsize=8)
    ax.text(*((p + c) / 2 + [0, 0.32]), r"$v\,\tau$", ha="center", fontsize=8)
    ax.text(c[0], c[1] - R_ESC - 0.38, r"aim $c=p+v\tau$", ha="center", fontsize=8, zorder=6,
            bbox=dict(fc="white", ec="none", pad=0.5))
    # 탈출 반경 r
    ax.plot([c[0], c[0] + R_ESC * np.cos(np.radians(50))], [c[1], c[1] + R_ESC * np.sin(np.radians(50))],
            "k-", lw=0.7, zorder=5)
    ax.text(c[0] + 0.55, c[1] + 0.95, r"$r=\frac{1}{2}a\tau^2$", fontsize=8, zorder=6)
    # 발사기, 반각, 사거리
    ax.plot(0, 0, "ks", ms=6)
    ax.text(-0.15, -0.55, "net launcher", ha="center", fontsize=7.5)
    ax.add_patch(Wedge((0, 0), 2.2, 0, th_deg, fill=False, ec="k", lw=0.6))
    ax.text(2.35, 0.17, r"$\theta$", fontsize=8.5)
    ax.plot([0, RMAX * np.cos(TH)], [0, 0], "k:", lw=0.6)
    ax.annotate("", xy=(RMAX * np.cos(TH + 0.02), RMAX * np.sin(TH + 0.02)), xytext=(0, 0),
                arrowprops=dict(arrowstyle="<->", lw=0.6, shrinkA=0, shrinkB=0))
    ax.text(3.6, 1.15, r"$R_{\max}$", fontsize=8.5, rotation=th_deg)
    # 축 위 껍질 [D_min, D_max]
    yb = -2.35
    for x, lab in ((D_MIN, r"$D_{\min}=r/\sin\theta$"), (D_MAX, r"$D_{\max}=R_{\max}-r$")):
        ax.plot([x, x], [yb, -0.05], "-", lw=0.4, color="0.4")
        ax.text(x, yb - 0.32, lab, ha="center", fontsize=7.5)
    ax.annotate("", xy=(D_MAX, yb + 0.15), xytext=(D_MIN, yb + 0.15),
                arrowprops=dict(arrowstyle="<->", lw=0.7, shrinkA=0, shrinkB=0))
    ax.text((D_MIN + D_MAX) / 2, yb + 0.3, "robust aim set (hatched)", ha="center", fontsize=7.5)
    ax.text(10.2, -1.75,
            r"$\rho=\dfrac{R_{\max}\tan\theta}{r}$" + "\n"
            + rf"$\rho_0=\sec\theta+\tan\theta$" + "\n"
            + rf"here: $\rho={RHO:.2f}$, $\rho_0={rho0(TH):.2f}$",
            fontsize=8, va="center", bbox=dict(fc="white", ec="k", lw=0.5, pad=3))
    ax.text(-0.8, -2.2, rf"$\tau={TAU}$ s, $\theta={np.degrees(TH):.1f}$°, $R_{{\max}}={RMAX}$ m" + "\n"
            rf"$a={AATT:.1f}$ m/s$^2$, $r={R_ESC:.2f}$ m", ha="left", va="center", fontsize=7, color="0.25")
    ax.set_aspect("equal")
    ax.set_xlim(-0.9, 13.5)
    ax.set_ylim(-3.0, 2.15)
    ax.set_xlabel("downrange [m]")
    ax.set_ylabel("cross-range [m]")
    ax.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig1_concept.png")
    plt.close(fig)


# ---------------------------------------------------------------- 그림 2
def jit(x, k):
    return x * (1 + 0.022 * k)  # 로그 x 에서 같은 ρ 점을 좌우로 벌림 (값 변경 없음, 표시만)


def fig2():
    fig, (aa, ab) = plt.subplots(2, 1, figsize=(160 * MM, 150 * MM), sharex=True,
                                 gridspec_kw=dict(height_ratios=[1, 1], hspace=0.08))
    xs = np.geomspace(1.0, 14, 400)
    for ax in (aa, ab):  # 두 패널을 관통하는 ρ* 대역 (θ₀)
        ax.axvspan(*RS_BAND, fc="0.86", ec="none", zorder=0)
    ab.text(np.sqrt(RS_BAND[0] * RS_BAND[1]), 46, r"$\rho^*$ band" + "\n" + r"($\theta_0$)", ha="center",
            va="top", fontsize=6.5, color="0.2", bbox=dict(fc="white", ec="none", pad=0.6))
    ths ={"h1.0": (TH, "-", r"$\theta_0$", "o"), "h1.5": (1.5 * TH, "--", r"$1.5\,\theta_0$", "s")}

    # (a) 회색: E7-a, E7-a′ (같은 프로토콜 반복 측정)
    for src, mk in (("e7a/probe.json", "x"), ("e7a2/probe.json", "+")):
        d = load(src)
        for vn, w in d["variant_window_med"].items():
            aa.plot(jit(d["rho"][vn], -2.6 if vn.endswith("cv") else 2.6), w, mk, color="0.65", ms=4, mew=0.7,
                    zorder=2)
    for h, (th, ls, lab, mk) in ths.items():
        n = np.clip(N_INF * (1 - rho0(th) / xs), 0, None)
        aa.plot(xs, n, ls, color="k", lw=1.0, zorder=3)
        aa.axvline(rho0(th), color="0.35", ls=":", lw=0.8)
        aa.axvline(rho_star(th), color="0.35", ls="-." if h == "h1.0" else (0, (5, 2, 1, 2, 1, 2)), lw=0.8)
        for vn, v in OV["variants"].items():
            if h not in vn:
                continue
            cv = vn.endswith("cv")
            aa.plot(jit(v["rho"], -1 if cv else 1), v["cond_window_med"], mk, ms=6, mew=1.0, mec="k",
                    mfc="k" if cv else "white", zorder=5)
    aa.axhline(4, color="k", lw=0.6, ls=(0, (1, 1.5)))
    aa.text(13.6, 4.12, "4 steps", ha="right", va="bottom", fontsize=7)
    aa.text(13.6, N_INF * (1 - rho0(TH) / 13.6) + 0.15, r"$N(\rho;\theta_0)$", ha="right", va="bottom", fontsize=7.5)
    aa.text(13.6, N_INF * (1 - rho0(1.5 * TH) / 13.6) - 0.2, r"$N(\rho;1.5\theta_0)$", ha="right", va="top",
            fontsize=7.5)
    for th, nm in ((TH, r"\theta_0"), (1.5 * TH, r"1.5\theta_0")):
        aa.text(rho0(th) * 1.012, 6.85 if th == TH else 6.35, rf"$\rho_0({nm})$", fontsize=6.8, va="top")
        aa.text(rho_star(th) * 1.012, 6.85 if th == TH else 6.35, rf"$\rho^*({nm})$", fontsize=6.8, va="top")
    aa.set_ylim(0, 7.2)
    aa.set_ylabel("robust window (median, steps)")
    h_ = [plt.Line2D([], [], ls="", marker="o", mfc="k", mec="k", label=r"cv, $\theta_0$"),
          plt.Line2D([], [], ls="", marker="o", mfc="white", mec="k", label=r"ma, $\theta_0$"),
          plt.Line2D([], [], ls="", marker="s", mfc="k", mec="k", label=r"cv, $1.5\theta_0$"),
          plt.Line2D([], [], ls="", marker="s", mfc="white", mec="k", label=r"ma, $1.5\theta_0$"),
          plt.Line2D([], [], ls="", marker="x", color="0.65", label="E7-a (repeat)"),
          plt.Line2D([], [], ls="", marker="+", color="0.65", label="E7-a$'$ (repeat)"),
          plt.Line2D([], [], ls="-", color="k", label=r"$N(\rho;\theta_0)$, upper bound ($\delta=0$)"),
          plt.Line2D([], [], ls="--", color="k", label=r"$N(\rho;1.5\theta_0)$, upper bound")]
    aa.legend(handles=h_, loc="lower right", fontsize=6.5, frameon=True,
              framealpha=1, edgecolor="0.7", ncol=1)
    aa.text(0.01, 0.97, "(a)", transform=aa.transAxes, fontsize=9, fontweight="bold", va="top")

    # (b) 정합 감사 천장 (A안 계보) — seed 점 + 중앙값 막대, 보간선 없음
    armc = load("armc1/readout.json")["cells"]["m0.35_n1"]["seeds"]
    series = [  # (점 목록 [(ρ, [seed 값])], 마커, 채움, 좌우 오프셋)
        ("arm C-1, det", [(RHO, [s["ceil_det"] for s in armc.values()])], "D", "k", 0),
    ]
    e7b, e7b2 = load("e7b/readout.json")["variants"], load("e7b2/readout.json")["variants"]
    for nm, src, key, fill, off in (("E7-b, det", e7b, "ceil_det", "k", -1), ("E7-b$'$, sto", e7b2, "ceil_sto",
                                                                              "white", 1)):
        for ma in (False, True):
            pts = [(v["rho"], [s[key] for s in v["seeds"].values()]) for vn, v in src.items()
                   if vn.endswith("ma") == ma]
            series.append((nm + (", ma" if ma else ""), pts, "^" if ma else "o", fill, off + (1.6 if ma else 0)
                           * np.sign(off)))
    for nm, pts, mk, fill, off in series:
        for rho, vals in pts:
            x = jit(rho, off)
            for i, s in enumerate(vals):
                ab.plot(x * (1 + 0.004 * (i - 1)), s, mk, ms=3.6, mew=0.7, mec="k", mfc=fill, zorder=4)
            med = float(np.median(vals))
            ab.plot([x / 1.012, x * 1.012], [med, med], "k-", lw=1.6, zorder=5)
    # 평탄부 띠: 계약별 (pooling 금지) — 같은 계약 안 ρ ≥ 3.92 seed 값 전부의 중앙값·IQR, 기술 통계만
    x_pl, pl_handles = (3.6, 13.5), []
    for src, key, kw, lab in ((e7b, "ceil_det", dict(fc="0.75", ec="none", alpha=0.45), "E7-b det"),
                              (e7b2, "ceil_sto", dict(fc="none", ec="0.45", hatch="\\\\\\\\", lw=0), "E7-b$'$ sto")):
        vals = [s[key] for v in src.values() for s in v["seeds"].values()]
        q1, med, q3 = np.percentile(vals, [25, 50, 75])
        ab.fill_between(x_pl, q1, q3, zorder=1, **kw)
        ab.plot(x_pl, [med, med], color="0.3", lw=0.8, ls=(0, (4, 2)), zorder=2)
        pl_handles.append(matplotlib.patches.Patch(**kw, label=f"{lab}, ρ≥3.92: median {med:g}, IQR {q1:g}–{q3:g}"))
    ab.axhline(29, color="k", lw=0.7, ls="--")
    ab.text(1.03, 29.6, "gate 29/240", fontsize=7)
    ab.axvspan(RHO * 1.07, 3.925 / 1.07, fc="none", ec="0.6", hatch="..", lw=0)
    ab.text(np.sqrt(RHO * 3.925), 38, "no trained\npoints\n(this lineage)", ha="center", va="top",
            fontsize=6.8, color="0.3", bbox=dict(fc="white", ec="none", pad=0.6))
    ab.set_ylim(0, 60)
    ab.set_ylabel("matched-audit ceiling [/240]")
    sec = ab.secondary_yaxis("right", functions=(lambda y: y / 2.4, lambda p: p * 2.4))
    sec.set_ylabel("[%]")
    sec.tick_params(labelsize=7)
    hb = [plt.Line2D([], [], ls="", marker="D", mfc="k", mec="k", ms=4, label=r"arm C-1, det ($\rho$ 1.92)"),
          plt.Line2D([], [], ls="", marker="o", mfc="k", mec="k", ms=4, label="E7-b, det"),
          plt.Line2D([], [], ls="", marker="^", mfc="k", mec="k", ms=4, label="E7-b, det, ma"),
          plt.Line2D([], [], ls="", marker="o", mfc="white", mec="k", ms=4, label=r"E7-b$'$, sto"),
          plt.Line2D([], [], ls="", marker="^", mfc="white", mec="k", ms=4, label=r"E7-b$'$, sto, ma"),
          plt.Line2D([], [], ls="-", color="k", lw=1.6, label="median of 3 seeds")] + pl_handles
    ab.legend(handles=hb, loc="upper right", fontsize=6.5, ncol=3, frameon=True, framealpha=1, edgecolor="0.7")
    ab.text(0.01, 0.97, "(b)", transform=ab.transAxes, fontsize=9, fontweight="bold", va="top")

    ab.set_xscale("log")
    ticks = [1.24, 1.92, 2.94, 3.92, 6.0, 7.69, 11.8]
    ab.set_xticks(ticks)
    ab.set_xticklabels([f"{t:g}" for t in ticks])
    ab.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ab.set_xlim(1.0, 14)
    ab.set_xlabel(r"$\rho = R_{\max}\tan\theta\,/\,(\frac{1}{2}a\tau^2)$  (log scale)")
    for ax in (aa, ab):
        ax.tick_params(labelsize=7)
        ax.spines["top"].set_visible(False)
    aa.spines["right"].set_visible(False)
    fig.subplots_adjust(left=0.085, right=0.92, top=0.985, bottom=0.075)
    fig.savefig(OUT / "fig2_money.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    print("wrote", OUT / "fig1_concept.png", OUT / "fig2_money.png")
