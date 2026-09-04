"""Paper figures — the two that carry the result set (English, print/grayscale-safe).

    F1  feasibility bounds + modality separation on the chi-section  (money figure)
        (a) hold arm: measured rule-based lower bound vs U = 1[chi<1] upper bound,
            three regions (baseline-achievable / aiming-limited / kinematically-infeasible)
        (b) intercept arm: net capture vs any neutralization -- the modality gap
    F2  fire decomposition (E1c, EXPLORATORY): p_fire and p_capture|fire
        -> why the zeros above the boundary are CENSORED, not a post-commit test

Aggregation is NOT re-derived here: bins / Wilson / band bounds / 50 % crossing all
come from `curve_sweep.summarize_curve`, so the figure cannot drift from the tables.
Numbers printed in docs/82 §3 and the Case B note are asserted at the bottom -- if a
contract or a result file changes, this script fails instead of drawing a stale claim.

    python -m shepherd.scripts.paper_figs                    # -> figures/*.png|.pdf

Naming discipline (docs/82 §3, docs/83): "consistent with" not "verified";
region names fixed; "finite slew binds first" is NOT claimed anywhere here.
torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402

from shepherd.scripts.curve_sweep import (PSI_MED_DEG, a_star_psi,  # noqa: E402
                                          summarize_curve)
# cone 여유 법칙은 e1e 가 단일 정의원이다 -- 여기서 다시 구현하지 않는다
# (docs/85 R-001/R-012 의 이중 구현 사고 재발 방지). 기본 규약 = inscribed(sin).
from shepherd.scripts.e1e_axial_optimum import (a_star as cone_a_star,  # noqa: E402
                                                ax_optimum, s_of_ax)

# two hues + redundant marker/linestyle so the panels survive B&W print and CVD
INK = "#111111"
C_NET = "#1F5FA9"       # dark in grayscale
C_NEU = "#D97706"       # light in grayscale
MUTED = "#6B7280"
BAND_FILL = ("#F3F4F6", "#FFF7ED", "#EEF2F7")

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9.5, "axes.titlesize": 10,
    "axes.edgecolor": "#9CA3AF", "axes.linewidth": 0.8,
    "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "axes.unicode_minus": False, "legend.frameon": False, "legend.fontsize": 8.3,
})


def _load(p: str) -> dict:
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def _chi(a: float, tau: float, rho: float) -> float:
    """chi = a tau^2 / (2 rho) -- the same algebra as `a_star` inverted."""
    return a * tau ** 2 / (2.0 * rho)


REGION_KEY = ("I  baseline-achievable   II  aiming-limited   "
              "III  kinematically-infeasible")


def _regions(ax, x_lo: float, x_aim: float, x_inf: float, x_hi: float, *,
             labels: bool) -> None:
    """Three declared regions (docs/82 §3(c)). Numerals inside, names in the caption
    -- spelling them out at the top collides with the physical-units axis."""
    for (lo, hi), fill, name in zip(((x_lo, x_aim), (x_aim, x_inf), (x_inf, x_hi)),
                                    BAND_FILL, ("I", "II", "III")):
        ax.axvspan(lo, hi, color=fill, zorder=0)
        if labels:
            ax.text((lo + hi) / 2, 0.90, name, ha="center", va="center",
                    fontsize=9.5, color=MUTED, style="italic",
                    transform=ax.get_xaxis_transform())
    ax.axvline(x_aim, color=MUTED, ls=(0, (4, 3)), lw=0.9, zorder=1)
    ax.axvline(x_inf, color=INK, ls="-", lw=1.0, zorder=1)


def _second_axis(ax, tau: float, rho: float) -> None:
    """Top axis = the same quantity in physical units (not a second measure)."""
    top = ax.secondary_xaxis("top", functions=(lambda c: c * 2 * rho / tau ** 2,
                                               lambda a: _chi(a, tau, rho)))
    top.set_xlabel(r"$a_{att}$  [m/s$^2$]", labelpad=3)
    top.tick_params(labelsize=8.2)


def _errbars(ax, xs, ps, los, his, *, color, marker, ls, label, fill=True):
    # clamp: the Wilson interval is not centred on p, so p can sit a hair outside it
    ax.errorbar(xs, ps, yerr=[[max(p - l, 0.0) for p, l in zip(ps, los)],
                              [max(h - p, 0.0) for p, h in zip(ps, his)]],
                fmt=marker, ls=ls, lw=1.3, ms=5.2, color=color,
                mfc=color if fill else "white", mew=1.3, capsize=2.4,
                elinewidth=0.9, label=label, zorder=4)


def fig1(hold: dict, itc: dict, out: pathlib.Path) -> dict:
    sh, si = summarize_curve(hold), summarize_curve(itc)
    d = sh["_declared"]
    tau, rho = d["tau_deploy"], d["net_radius"]
    a_lo, a_hi = d["a_att_bracket"]
    a_aim = a_star_psi(math.radians(PSI_MED_DEG), range_max=d["range_max"],
                       half_angle=d["half_angle"], tau=tau)
    x_lo, x_hi = _chi(a_lo, tau, rho), _chi(a_hi, tau, rho)
    x_aim, x_cross = _chi(a_aim, tau, rho), _chi(sh["cross50_net_capture"], tau, rho)

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharey=True)

    # ---- (a) the sandwich: measured lower bound vs single-shot upper bound
    ax = axes[0]
    _regions(ax, x_lo, x_aim, 1.0, x_hi, labels=True)
    ax.step([x_lo, 1.0, 1.0, x_hi], [1, 1, 0, 0], where="post", color=INK,
            ls=(0, (6, 2)), lw=1.4, zorder=3,
            label=r"upper bound $U=\mathbf{1}[\chi<1]$"
                  "\n(single-shot necessary condition)")
    xs = [_chi(b["mid"], tau, rho) for b in sh["bins"]]
    c = [b["net_capture"] for b in sh["bins"]]
    _errbars(ax, xs, [b["p"] for b in c], [b["lo"] for b in c], [b["hi"] for b in c],
             color=C_NET, marker="o", ls="-",
             label="measured lower bound $L$: net capture,\nrule-based baseline"
                   f" (n={sh['n']:,}, Wilson 95 %)")
    ax.plot([x_cross], [0.5], marker="v", ms=6, color=C_NET, mfc="white", mew=1.3,
            zorder=5)
    ax.annotate(f"50 % crossing  $\\chi$={x_cross:.2f}\n({sh['cross50_net_capture']:.1f}"
                r" m/s$^2$)", xy=(x_cross, 0.5), xytext=(x_lo + 0.04, 0.34),
                fontsize=8.0, color=C_NET, va="center", ha="left",
                arrowprops=dict(arrowstyle="-", color=C_NET, lw=0.8))
    ax.annotate(f"$a^*(\\psi={PSI_MED_DEG}^\\circ)$ = {a_aim:.1f}"
                r" m/s$^2$" + f"\n$\\chi$={x_aim:.2f}  (dev. "
                f"{100 * abs(sh['cross50_net_capture'] - a_aim) / a_aim:.1f} %)",
                xy=(x_aim, 0.08), xytext=(x_aim + 0.06, 0.13), fontsize=8.0,
                color=MUTED, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_title("(a) feasibility bounds on the $\\chi$-section", loc="left", pad=20)
    ax.set_ylabel("probability per episode")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.74))

    # ---- (b) modality separation, same episodes (intercept arm)
    ax = axes[1]
    _regions(ax, x_lo, x_aim, 1.0, x_hi, labels=True)
    xs = [_chi(b["mid"], tau, rho) for b in si["bins"]]
    for key, color, marker, ls, lab, fill in (
            ("neutralized", C_NEU, "s", (0, (5, 2)),
             "any neutralization (net capture or hard kill)", False),
            ("net_capture", C_NET, "o", "-", "net capture (non-destructive)", True)):
        b = [x[key] for x in si["bins"]]
        _errbars(ax, xs, [q["p"] for q in b], [q["lo"] for q in b],
                 [q["hi"] for q in b], color=color, marker=marker, ls=ls,
                 label=lab, fill=fill)
    band = si["by_band"]
    for name, x_at in (("BAND_AIM", (x_aim + 1.0) / 2), ("SHAPING_NEEDED", 1.42)):
        pn, pc = band[name]["neutralized"]["p"], band[name]["net_capture"]["p"]
        ax.annotate("", xy=(x_at, pn), xytext=(x_at, pc),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
        ax.text(x_at + 0.03, (pn + pc) / 2, f"{pn:.3f}\nvs {pc:.3f}", fontsize=8.0,
                va="center", color=INK)
    ax.set_title(f"(b) modality separation, same episodes (n={si['n']:,})",
                 loc="left", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.80))

    for ax in axes:
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(-0.04, 1.06)
        ax.set_xlabel(r"deployment-delay evasion number  $\chi = a_{att}\tau^2/2\rho$")
        ax.grid(axis="y", color="#E5E7EB", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        _second_axis(ax, tau, rho)

    fig.tight_layout(w_pad=1.6, rect=(0, 0.045, 1, 1))
    fig.text(0.5, 0.012, "regions:   " + REGION_KEY, ha="center", fontsize=8.2,
             color=MUTED)
    _save(fig, out)
    return {"hold": sh, "intercept": si, "a_aim": a_aim}



# ---------------------------------------------------------------- KSAS F1 ----
# r6 (2026-08-28). 본문이 39.3 -> 31.8 두 경계 한 축으로 정리됐으므로 그림도
# 그 둘만 남긴다. 뺀 것: 25.8 사전분할 점선(본문에서 삭제) · observed 50 % ·
# 구간 음영/로마숫자 · 브래킷 앵커 라벨 · U 계단 · 그림 내 각주(캡션으로 이관).
# 크기: 1 단 폭(8.5 cm ≈ 3.35 in)에 1:1 로 앉도록 3.4 x 2.7 in.
#   -> 축소 없이 들어가므로 인쇄 시 글자가 작아지지 않는다 (ver3-1 의 문제).

def fig1_ksas(hold: dict, out: pathlib.Path) -> dict:
    """KSAS Fig. 1 — 두 해석적 상계와 폐루프 달성 곡선."""
    sh = summarize_curve(hold)
    d = sh["_declared"]
    tau, rho = d["tau_deploy"], d["net_radius"]
    a_lo, a_hi = d["a_att_bracket"]
    r_max, half = d["range_max"], d["half_angle"]
    x_opt = ax_optimum(theta=half, rmax=r_max)
    a_geom = float(cone_a_star(x_opt, theta=half, rmax=r_max, tau=tau))
    a_rho = 2.0 * rho / tau ** 2
    x_geom = _chi(a_geom, tau, rho)
    x_lo, x_hi = _chi(a_lo, tau, rho), _chi(a_hi, tau, rho)

    with plt.rc_context({"font.size": 7.6, "axes.labelsize": 7.8,
                         "legend.fontsize": 6.9, "xtick.labelsize": 7.0,
                         "ytick.labelsize": 7.0}):
        fig, ax = plt.subplots(figsize=(3.4, 2.7))

        ax.axvline(x_geom, color=INK, ls="-", lw=1.3, zorder=3)
        ax.axvline(1.0, color=INK, ls=(0, (5, 2)), lw=1.3, zorder=3)
        # 두 라벨은 파선(chi=1) 오른쪽 빈 영역에 쌓는다. 선 위에 얹으면 글자가
        # 가려지므로 흰 bbox 도 함께 준다 (인쇄본에서 실제로 겹쳤던 부분).
        lab = dict(fontsize=6.9, color=INK, va="center", ha="left",
                   bbox=dict(facecolor="white", edgecolor="none", pad=1.0),
                   arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
        ax.annotate(f"finite-cone\n{a_geom:.1f} m/s$^2$", xy=(x_geom, 0.42),
                    xytext=(1.16, 0.56), **lab)
        ax.annotate(f"loose outer\n{a_rho:.1f} m/s$^2$", xy=(1.0, 0.16),
                    xytext=(1.16, 0.26), **lab)

        xs = [_chi(b["mid"], tau, rho) for b in sh["bins"]]
        c = [b["net_capture"] for b in sh["bins"]]
        _errbars(ax, xs, [b["p"] for b in c], [b["lo"] for b in c],
                 [b["hi"] for b in c], color=C_NET, marker="o", ls="-",
                 label=f"net capture (n={sh['n']:,}, Wilson 95 %)")

        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(-0.04, 1.06)
        ax.set_xticks([x_lo, x_geom, 1.0, 1.5, x_hi])
        ax.set_xticklabels([f"{x_lo:.2f}", f"{x_geom:.3f}", "1.00", "1.50",
                            f"{x_hi:.2f}"])
        ax.set_xlabel(r"$\chi = a_{att}\tau^2/2\rho$")
        ax.set_ylabel("net capture probability")
        ax.grid(axis="y", color="#E5E7EB", lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        ax.legend(loc="upper right", bbox_to_anchor=(1.005, 1.0), frameon=True,
                  facecolor="white", edgecolor="none", framealpha=1.0,
                  borderpad=0.3, handlelength=1.8)
        _second_axis(ax, tau, rho)
        fig.tight_layout(pad=0.35)
        _save(fig, out)
    return {"hold": sh, "x_geom": x_geom, "a_geom": a_geom}


def fig2_ksas(hold: dict, out: pathlib.Path) -> dict:
    """KSAS Fig. 2 — tau–a* 해석 경계 + 기준 지연에서의 폐루프 달성점.

    곡선 = 해석식이라 모든 tau 에서 유효 (loose outer 2 rho/tau^2 = 식 (3),
    finite-cone 2 s_max/tau^2 = 식 (5)). 마커 = tau=0.30 s 한 점에서만 잰
    폐루프 실측이므로 곡선으로 잇지 않는다. 범례는 이름만 — 수치(39.3/31.8/
    31.2/22.5)는 본문·캡션 담당 (사용자 확정 2026-09-04, 캡션 B안).
    """
    sh = summarize_curve(hold)
    d = sh["_declared"]
    tau, rho = d["tau_deploy"], d["net_radius"]
    x_opt = ax_optimum(theta=d["half_angle"], rmax=d["range_max"])
    a1 = float(cone_a_star(x_opt, theta=d["half_angle"], rmax=d["range_max"],
                           tau=1.0))                      # = 2 s_max
    cross50 = sh["cross50_net_capture"]
    a_cap = max(r["a_att"] for r in hold["records"]
                if r["label"] in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT"))

    # frozen 수치 (KSAS 본문과 동일 계보) — drift 시 그리지 않고 죽는다
    frozen = {"a_geom": (a1 / tau ** 2, 31.8),
              "a_loose": (2 * rho / tau ** 2, 39.33),
              "cross50": (cross50, 22.45), "max_cap": (a_cap, 31.2)}
    for k, (got, want) in frozen.items():
        assert abs(got - want) <= abs(want) * 0.01, f"{k}: {got} != {want} (frozen)"

    taus = [0.15 + 0.45 * i / 399 for i in range(400)]
    geom = [a1 / t ** 2 for t in taus]
    loose = [2.0 * rho / t ** 2 for t in taus]

    # 작은 지면 대비 큰 글자 (반 컬럼 축소 인쇄에서도 읽히는 판형)
    rc = {"font.size": 9.5, "axes.labelsize": 10.5, "legend.fontsize": 9.0,
          "xtick.labelsize": 9.5, "ytick.labelsize": 9.5}
    with plt.rc_context(rc):
        fig, ax = plt.subplots(figsize=(3.4, 2.7))
        ax.fill_between(taus, 0, [min(g, 80.0) for g in geom],
                        color="#EEF2F7", zorder=0)
        # legend 순서 = 기준선 위에서의 상하 순서 (39.3 > 31.8 > 31.2 > 22.5)
        ax.plot(taus, loose, color=INK, lw=1.3, ls=(0, (5, 2)), zorder=3,
                label="loose outer")
        ax.plot(taus, geom, color=INK, lw=1.5, zorder=3, label="finite-cone")
        ax.axvline(tau, color=MUTED, ls=(0, (1, 2)), lw=1.1, zorder=2)
        ax.text(tau, 81.5, "baseline 0.30 s", ha="center", va="bottom",
                fontsize=8.8, color=MUTED)
        ax.text(0.185, 5.5, "capture feasible", fontsize=8.8, color=MUTED,
                style="italic", ha="left")
        ax.plot([tau], [a_cap], marker="*", ms=10.5, color=C_NET, mec=C_NET,
                ls="none", zorder=5, label="max captured")
        ax.plot([tau], [cross50], marker="o", ms=6.0, color=C_NET, mfc="white",
                mew=1.5, ls="none", zorder=5, label="50 % crossing")

        ax.set_xlim(0.15, 0.60)
        ax.set_ylim(0, 80)
        ax.set_xticks([0.2, 0.3, 0.4, 0.5, 0.6])
        ax.set_yticks([0, 20, 40, 60, 80])
        ax.set_xlabel(r"capture delay $\tau$  [s]")
        ax.set_ylabel(r"$a_{att}$  [m/s$^2$]")
        ax.grid(axis="y", color="#E5E7EB", lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        ax.legend(loc="upper right", frameon=True, facecolor="white",
                  edgecolor="none", framealpha=1.0, borderpad=0.3,
                  handlelength=1.9, labelspacing=0.4, handletextpad=0.6)
        fig.tight_layout(pad=0.35)
        _save(fig, out)
    return {k: v[0] for k, v in frozen.items()}


def fig2(e1c: dict, hold: dict, out: pathlib.Path) -> dict:
    """E1c: the eligibility/conditional split -- the censoring caveat, drawn."""
    g = e1c["manifest"]["geometry"]
    tau, rho = g["tau"], g["rho"]
    sh = summarize_curve(hold)
    a_lo, a_hi = sh["_declared"]["a_att_bracket"]
    x_lo, x_hi = _chi(a_lo, tau, rho), _chi(a_hi, tau, rho)

    fig, ax = plt.subplots(figsize=(5.4, 3.9))
    bins = e1c["bins"]
    xs = [_chi((b["lo"] + b["hi"]) / 2, tau, rho) for b in bins]
    fired = [b for b in bins if b["n_fired"] > 0]
    # threshold from the episodes themselves (docs/83 §14: largest firing a_att = 32.15,
    # nothing released above it) -- not from a bin edge, which would drop one episode
    A_DRY = 32.2                     # published threshold (docs/83 §14) -- "fire 0/350"
    a_fire_max = max(r["a_att"] for r in e1c["records"] if r["fired"])
    assert a_fire_max < A_DRY, f"a shot was released at {a_fire_max} >= {A_DRY}"
    n_dry = sum(1 for r in e1c["records"] if r["a_att"] >= A_DRY)
    x_dry = _chi(A_DRY, tau, rho)

    ax.axvspan(x_dry, x_hi, color="#F3F4F6", zorder=0)
    ax.text((x_dry + x_hi) / 2, 0.52,
            f"no shot released\n0/{n_dry} episodes\n(zeros above are"
            "\n$\\bf{censored}$, not a\npost-commit test)",
            ha="center", va="center", fontsize=8.2, color=MUTED)
    ax.axvline(1.0, color=INK, lw=1.0, zorder=1)
    ax.text(1.02, 0.97, r"$\chi=1$", ha="left", va="top", fontsize=8.2, color=MUTED,
            transform=ax.get_xaxis_transform())

    _errbars(ax, xs, [b["p_fire"] for b in bins],
             [b["p_fire_wilson"][0] for b in bins], [b["p_fire_wilson"][1] for b in bins],
             color=C_NET, marker="o", ls="-", label="fire eligibility  $P$(shot released)")
    _errbars(ax, [_chi((b["lo"] + b["hi"]) / 2, tau, rho) for b in fired],
             [b["p_capture_given_fire"] for b in fired],
             [b["p_capture_given_fire_wilson"][0] for b in fired],
             [b["p_capture_given_fire_wilson"][1] for b in fired],
             color=C_NEU, marker="s", ls=(0, (5, 2)), fill=False,
             label="conditional success  $P$(capture | shot released)")

    t = e1c["totals"]
    ax.set_title("fire decomposition  (E1c, exploratory diagnostic;\n"
                 f"T1 · n={t['n']}, {t['n_fired']} released, {t['n_captured']} captured)",
                 loc="left", pad=22)
    ax.set_xlabel(r"deployment-delay evasion number  $\chi = a_{att}\tau^2/2\rho$")
    ax.set_ylabel("probability")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(-0.04, 1.06)
    ax.grid(axis="y", color="#E5E7EB", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.27))   # below the x-label
    _second_axis(ax, tau, rho)

    fig.tight_layout()
    _save(fig, out)
    return {"x_dry": x_dry, "n_dry": n_dry}


def _save(fig, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):                       # png for docx, pdf for LaTeX
        fig.savefig(out.with_suffix("." + ext), dpi=300, bbox_inches="tight",
                    facecolor="white")
        print(f"wrote {out.with_suffix('.' + ext)}")
    plt.close(fig)


def _check(f1: dict, f2: dict) -> None:
    """Frozen numbers (docs/82 §3, Case B note, docs/83 §14). Drift -> fail loudly."""
    sh, si = f1["hold"], f1["intercept"]
    got = {
        "hold.easy": sh["by_band"]["EASY"]["net_capture"]["p"],
        "hold.aim": sh["by_band"]["BAND_AIM"]["net_capture"]["p"],
        "hold.cross50": sh["cross50_net_capture"],
        "hold.above_k": sh["above_a_star"]["net_capture_k"],
        "hold.above_n": sh["above_a_star"]["n"],
        "itc.aim.net": si["by_band"]["BAND_AIM"]["net_capture"]["p"],
        "itc.aim.neu": si["by_band"]["BAND_AIM"]["neutralized"]["p"],
        "itc.inf.neu": si["by_band"]["SHAPING_NEEDED"]["neutralized"]["p"],
        "a_aim": f1["a_aim"],
        "e1c.n_dry": f2["n_dry"],
    }
    want = {"hold.easy": 0.763, "hold.aim": 0.016, "hold.cross50": 22.45,
            "hold.above_k": 0, "hold.above_n": 1598, "itc.aim.net": 0.006,
            "itc.aim.neu": 0.240, "itc.inf.neu": 0.243, "a_aim": 25.75,
            "e1c.n_dry": 350}
    for k, w in want.items():
        tol = 0 if isinstance(w, int) else max(abs(w) * 0.01, 5e-4)
        assert abs(got[k] - w) <= tol, f"{k}: {got[k]} != {w} (frozen)"
    print("checks ok  " + "  ".join(f"{k}={got[k]}" for k in want))


def main(argv=None):
    ap = argparse.ArgumentParser(description="paper figures F1/F2")
    ap.add_argument("--hold", default="results/curve_hold_reactive.json")
    ap.add_argument("--intercept", default="results/curve_intercept_reactive.json")
    ap.add_argument("--e1c", default="results/e1c_fire_decomp.json")
    ap.add_argument("--outdir", default="figures")
    # 전체 재렌더는 matplotlib 판본 차이만으로도 기존 f1/f2 의 바이트를 바꾼다
    # (실측 2026-08-26, mpl 3.11: PNG +30 KB, 내용 동일). 한 장만 손볼 때
    # 나머지 추적 아티팩트를 건드리지 않도록 --only 를 둔다.
    ap.add_argument("--only", choices=("all", "ksas", "ksas2"), default="all",
                    help="ksas = KSAS Fig.1 만, ksas2 = KSAS Fig.2 만 렌더 "
                         "(둘 다 f1/f2 재렌더 안 함)")
    a = ap.parse_args(argv)
    d = pathlib.Path(a.outdir)
    if a.only == "ksas":
        fig1_ksas(_load(a.hold), d / "f1_ksas_feasibility")
        return
    if a.only == "ksas2":
        fig2_ksas(_load(a.hold), d / "f2_ksas_tau_boundary")
        return
    f1 = fig1(_load(a.hold), _load(a.intercept), d / "f1_feasibility_modality")
    fig1_ksas(_load(a.hold), d / "f1_ksas_feasibility")
    fig2_ksas(_load(a.hold), d / "f2_ksas_tau_boundary")
    f2 = fig2(_load(a.e1c), _load(a.hold), d / "f2_fire_decomposition")
    _check(f1, f2)


if __name__ == "__main__":                                    # pragma: no cover
    main()
