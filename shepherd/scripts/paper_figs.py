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
    a = ap.parse_args(argv)
    d = pathlib.Path(a.outdir)
    f1 = fig1(_load(a.hold), _load(a.intercept), d / "f1_feasibility_modality")
    f2 = fig2(_load(a.e1c), _load(a.hold), d / "f2_fire_decomposition")
    _check(f1, f2)


if __name__ == "__main__":                                    # pragma: no cover
    main()
