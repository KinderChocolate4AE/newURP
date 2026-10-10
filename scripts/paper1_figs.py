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


# ---------------------------------------------------------------- 그림 4
def cross_audit():
    """계보별 교차 감사 행렬 (방어 정책 × 착취자 학습 상대), 값 = defended /240 의 seed·slot 목록.
    E7-c 는 교전 규칙·지표가 달라 별도 패널 (pooling 금지). E7-c 대각 = D_shot (assert)."""
    b, b2 = load("e7b/readout.json")["variants"], load("e7b2/readout.json")["variants"]
    c = load("e7c/readout.json")["slots"]
    S = lambda src, f: [f(s) for v in src.values() for s in v["seeds"].values()]
    C = lambda key: [s["cross"][key] for v in c.values() for s in v.values()]
    ab = {("det", "det"): S(b, lambda s: s["ceil_det"]), ("sto", "det"): S(b, lambda s: s["ceil_sto"]),
          ("sto", "sto"): S(b2, lambda s: s["ceil_sto"]), ("det", "sto"): S(b2, lambda s: s["det_vs_sto_exploiter"])}
    cc = {(d, e): C(f"learned_{d}_vs_ex_judge" + ("_sto" if e == "sto" else "")) for d in ("det", "sto")
          for e in ("det", "sto")}
    assert cc[("det", "det")] == [s["det"]["d_shot"] for v in c.values() for s in v.values()]
    return ab, cc


def fig4():
    ab, cc = cross_audit()
    fig, axs = plt.subplots(1, 2, figsize=(160 * MM, 64 * MM))
    for ax, m, lab in ((axs[0], ab, "(a) E7-b / E7-b$'$, ROE A (15 slots)"),
                       (axs[1], cc, "(b) E7-c, post-shot / inert (12 slots)")):
        med = np.array([[np.median(m[(d, e)]) for e in ("det", "sto")] for d in ("det", "sto")])
        ax.imshow(med, cmap="Greys", vmin=0, vmax=120)
        for i, d in enumerate(("det", "sto")):
            for j, e in enumerate(("det", "sto")):
                v = m[(d, e)]
                ax.text(j, i, f"{np.median(v):g}\n({min(v)}–{max(v)})", ha="center", va="center", fontsize=8,
                        color="white" if med[i, j] > 60 else "black", fontweight="bold" if i == j else "normal")
                if i == j:
                    ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="k", lw=1.6))
        ax.set_xticks([0, 1], ["det", "sto"])
        ax.set_yticks([0, 1], ["det", "sto"])
        ax.set_xlabel("exploiter trained against")
        ax.set_ylabel("defense policy evaluated")
        ax.set_title(lab, fontsize=7.5, loc="left")
        r = (np.median(m[("sto", "det")]) / np.median(m[("sto", "sto")]),
             np.median(m[("det", "sto")]) / np.median(m[("det", "det")]))
        ax.text(0.5, -0.42, f"mismatched / matched median: sto {r[0]:.2f}x, det {r[1]:.2f}x",
                transform=ax.transAxes, ha="center", fontsize=7)
        ax.tick_params(labelsize=7.5)
    fig.text(0.5, 0.005, "cells: defended /240, median (min–max); bold box = matched audit", ha="center", fontsize=7)
    fig.tight_layout(rect=(0, 0.05, 1, 1), w_pad=0.5)
    fig.savefig(OUT / "fig4_cross_audit.png")
    plt.close(fig)


# ---------------------------------------------------------------- F2 (τ, a) regime map — 해석판
# 위협 a = 노트 10-11b (사양 틸트각·추력비에서 도출). 실물 net 은 반각·사거리가 FS1 과 달라 경계 자체가 다르므로
# 이 그림에 올리지 않는다 (spine v3 §7-2).
THREAT_A = [("Mavic 3", 6.87), ("Phantom 4", 8.83), ("std quad", 17.4), ("racing FPV", 38.8), ("extreme racer", 117.0)]


def figF2():
    fig, ax = plt.subplots(figsize=(160 * MM, 100 * MM))
    fig.subplots_adjust(left=0.09, right=0.83, top=0.86, bottom=0.11)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(0.05, 1.5); ax.set_ylim(3, 200)
    taus = np.geomspace(0.05, 1.5, 300)
    rt = RMAX * np.tan(TH)                                   # FS1 net 반폭 (R_max tanθ)
    a_at = lambda rho, t: 2 * rt / (rho * t ** 2)            # iso-ρ: a = 2 R tanθ / (ρ τ²)

    def label(rho, t, txt, **kw):                            # 선 위 라벨 (화면 기울기에 맞춘 각도)
        p1, p2 = ax.transData.transform([(t, a_at(rho, t)), (t * 1.2, a_at(rho, t * 1.2))])
        ang = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
        ax.text(t, a_at(rho, t) * 1.07, txt, rotation=ang, rotation_mode="anchor", fontsize=6.5, **kw)

    ax.fill_between(taus, a_at(rho0(TH), taus), 1e4, fc="0.82", ec="none", zorder=0)
    ax.plot(taus, a_at(rho0(TH), taus), "k-", lw=1.8, zorder=3)
    label(rho0(TH), 0.34, rf"$\rho_0$ = {rho0(TH):.2f} (window opens)")
    for V, ls, t in ((15.0, (0, (1, 1.5)), 0.5), (V_BAR, "--", 0.105), (35.0, "-.", 0.07)):
        rs = rho0(TH) / (1 - 4 * DT * V / RMAX)
        ax.plot(taus, a_at(rs, taus), ls=ls, color="k", lw=0.9, zorder=3)
        label(rs, t, rf"$\rho^*$ = {rs:.2f} (0.2 s window, V {V:g} m/s)")
    ax.text(1.4, 150, r"$\rho<\rho_0$: no guaranteed-capture instant (model)", ha="right", fontsize=7)
    # FS1 τ 사다리의 측정 점 (a = 20.45 한 줄) — 천장 숫자는 실측 점 옆에만
    e7b = load("e7b/readout.json")["variants"]
    armc = [s["ceil_det"] for s in load("armc1/readout.json")["cells"]["m0.35_n1"]["seeds"].values()]
    pts = [(TAU, f"{min(armc)}–{max(armc)}"), (0.7 * TAU, f"{e7b['t0.7_h1.0_cv']['ceil_det_med']:g}"),
           (0.5 * TAU, f"{e7b['t0.5_h1.0_cv']['ceil_det_med']:g}")]
    for t, c in pts:
        ax.plot(t, AATT, "o", ms=5.5, mfc="k", mec="k", zorder=5)
        ax.text(t, AATT * 1.18, c, fontsize=7, ha="center", zorder=6,
                bbox=dict(fc="white", ec="none", pad=0.5))
    ax.text(0.155, 32, "matched-audit det ceiling /240\n(1e7 exploiter; measured at a = 20.45 only)",
            fontsize=6.3, ha="left", color="0.2", bbox=dict(fc="white", ec="none", pad=0.8))
    ax.annotate("", xy=(TAU - 0.15, AATT * 0.80), xytext=(TAU, AATT * 0.80),
                arrowprops=dict(arrowstyle="-|>", lw=0.8, color="0.3"))
    ax.text(0.21, AATT * 0.74, r"evader reaction delay $\tau_r$ 0.15 s", fontsize=6.3, ha="center", va="top", bbox=dict(fc="white", ec="none", pad=0.5),
            color="0.3")
    for lab, a in THREAT_A:                                  # 위협 등급 a (오른쪽 눈금)
        ax.plot([1.35, 1.5], [a, a], "k-", lw=1.4)
        ax.text(1.6, a, f"{lab} ({a:g})", fontsize=6.3, va="center")
    ax.set_xlabel(r"net deployment time $\tau$ [s]")
    ax.set_ylabel(r"threat acceleration $a$ [m/s$^2$]")
    ax.set_xticks([0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0], ["0.05", "0.1", "0.15", "0.2", "0.3", "0.5", "1"])
    ax.set_yticks([3, 5, 10, 20, 50, 100, 200], ["3", "5", "10", "20", "50", "100", "200"])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.text(0.052, 3.25, rf"net geometry fixed at FS1 ($R_{{\max}}$ {RMAX} m, $\theta$ {np.degrees(TH):.1f}°); "
            r"lines = analytic window boundaries", fontsize=6.2, color="0.25")
    ax.tick_params(labelsize=7)
    fig.savefig(OUT / "figF2_regime_map.png")
    plt.close(fig)


# ---------------------------------------------------------------- 그림 4 (spine v3) ρ별 분해 — 사후 기술 통계
def decomposition():
    """E7-b (결정적) / E7-b′ (확률적) 평가 기록: slot 별 (창이 생긴 판, 창 뒤 발사한 판, net 포획 판).
    창 = LOADED ∧ d ≤ 16 m 에서 robust tick ≥ 1 (n_rob, 발사 전까지만 셈) → 창 뒤 발사 = 창이 먼저 생긴 판에서의 발사."""
    import glob
    import pathlib
    net = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
    out = {}
    for line, exp, dn, g in (("det", "e7b", "learned_det", "ex_judge"), ("sto", "e7b2", "learned_sto", "ex_judge_sto")):
        rho = {v: x["rho"] for v, x in load(f"{exp}/readout.json")["variants"].items()}
        for f in sorted(glob.glob(str(A / exp / "*" / "s*" / "eval" / "episodes.jsonl"))):
            p = pathlib.Path(f)
            var = p.parents[2].name
            E = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
            d = [e for e in E if e["defender"] == dn and e["group"] == g]
            w = [e for e in d if e["n_rob"] > 0]
            out.setdefault((line, var, rho[var]), []).append(
                (len(w), sum(e["n_fire"] > 0 for e in w), sum(e["label"] in net for e in d),
                 sum(e["label"] in net for e in d if e["n_rob"] == 0)))   # 마지막 = 창 기록 밖 포획 (경계 사례)
    return out


def fig4dec():
    dec = decomposition()
    n_out = {ln: sum(v[3] for k, vs in dec.items() if k[0] == ln for v in vs) for ln in ("det", "sto")}
    fig, axs = plt.subplots(1, 2, figsize=(160 * MM, 68 * MM), sharey=True)
    styles = [("window occurred", "0.85", None), ("fired after a window", "0.55", None), ("net capture", "0.15", None)]
    for ax, line, ttl in ((axs[0], "det", "(a) deterministic defense vs its exploiter"),
                          (axs[1], "sto", "(b) stochastic defense vs its exploiter")):
        keys = sorted((k for k in dec if k[0] == line), key=lambda k: (k[2], k[1]))
        xs = np.arange(len(keys) + 1)
        ax.bar(0, 0, color="white")
        ax.text(0, 8, "ρ 1.92\npending\n(transition\nladder)", ha="center", va="bottom", fontsize=6, color="0.35")
        for i, k in enumerate(keys, start=1):
            vals = np.array(dec[k])                              # seed × 3
            for j, (lab, fc, _) in enumerate(styles):
                x = i + (j - 1) * 0.27
                ax.bar(x, np.median(vals[:, j]), width=0.25, fc=fc, ec="k", lw=0.5, label=lab if i == 1 else None)
                ax.plot([x] * len(vals), vals[:, j], "k.", ms=2.5)
        ax.set_xticks(xs, ["1.92"] + [f"{k[2]:.2f}" + ("\nma" if k[1].endswith("ma") else "") for k in keys], fontsize=6.5)
        ax.set_xlabel(r"$\rho$ (variant)")
        ax.set_title(ttl, fontsize=7, loc="left")
        ax.tick_params(labelsize=7)
    axs[0].set_ylabel("episodes /240 (median, dots = seeds)")
    axs[1].legend(fontsize=6.3, loc="upper right", frameon=False)
    fig.text(0.5, 0.005, "post-hoc descriptive counts from the matched-audit evaluation logs (1e7 exploiter); "
             f"not a pre-registered verdict.\nCaptures with no recorded window: det {n_out['det']}, sto {n_out['sto']} "
             "(window counted only while loaded and within 16 m)", ha="center", fontsize=5.8, color="0.3")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "fig_decomposition.png")
    plt.close(fig)

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig1()
    fig2()
    fig4()
    figF2()
    fig4dec()
    print("wrote", *sorted(p.name for p in OUT.glob("*.png")))
