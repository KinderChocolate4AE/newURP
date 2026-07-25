"""Fig B rev.2 — bounds after the E1.5 authoritative judge (C-1 Phase 1G).

(a) required lead time T vs initial spread rho0, four curves:
      T_LB,rest    rest-to-rest analytic bound used in Phase 1B/1C
      T*_plant     Phase 1F LP witness, tier 4 under the STATIC snapshot judge
      T*_dyn       displacement-constrained witness that also CERTIFIES under the
                   actual-trajectory judge (LCB >= theta, n = 20,000 x 3 seeds)
      T*_simple    best ratified simple arm (H / C / P)
    Hollow markers on T*_plant mark the two cells the dynamic judge rejected.
    The band between T*_dyn and T*_simple is the surviving controller gap.
(b) actual-trajectory v_soft for every witness class, against theta = 0.9.
"""
from __future__ import annotations
import argparse, json, math, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C_OLD, C_STATIC, C_DYN, C_SIMPLE = "#3B5BDB", "#9C36B5", "#E8590C", "#099268"
INK, INK2, GRID, SURFACE = "#1f2328", "#57606a", "#e3e5e8", "#fcfcfb"
BAND_HI, A_MAX, THETA = 2.65, 30.0, 0.9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", default="results/c1_corridor/c1_plant_bound.json")
    ap.add_argument("--envelope", default="results/c1_corridor/c1_response_envelope_fine.json")
    ap.add_argument("--search", default="results/c1_corridor/c1_phase1g_search.json")
    ap.add_argument("--hold", default="results/c1_corridor/c1_phase1g_dynamic_judge.json")
    ap.add_argument("--maxclr", default="results/c1_corridor/c1_phase1g_maxclr_falsified.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1g_bounds.png")
    a = ap.parse_args()

    P = json.loads(pathlib.Path(a.plant).read_text())
    S = json.loads(pathlib.Path(a.search).read_text())
    H = json.loads(pathlib.Path(a.hold).read_text())
    M = json.loads(pathlib.Path(a.maxclr).read_text())
    E = json.loads(pathlib.Path(a.envelope).read_text())

    rho = sorted(float(k) for k in P["T_star_plant"])
    t_lb = [2 * math.sqrt(max(r - BAND_HI, 0) / A_MAX) for r in rho]
    t_plant = [P["T_star_plant"][str(r)]["T_star_plant"] for r in rho]
    t_dyn = [S["T_star_dyn"][str(r)] for r in rho]
    by = {}
    for c in E["cells"]:
        by.setdefault(c["rho0"], []).append(c)
    t_simple = [next((c["T_available"] for c in sorted(by[r], key=lambda x: x["T_available"])
                      if any(v["safe"] for v in c["arms"].values())), np.nan) for r in rho]
    rejected = [(r, tp) for r, tp, td in zip(rho, t_plant, t_dyn) if td is not None and td > tp]

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.6, 4.5), width_ratios=[1.5, 1],
                                 facecolor=SURFACE)
    for x in (ax, bx):
        x.set_facecolor(SURFACE)
        for s in ("top", "right"):
            x.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            x.spines[s].set_color(GRID)
        x.tick_params(colors=INK2, labelsize=9, length=3)

    # ---- (a) bounds -------------------------------------------------------------
    ax.fill_between(rho, t_dyn, t_simple, color=C_SIMPLE, alpha=0.12, lw=0, zorder=1)
    ax.plot(rho, t_lb, "--", color=C_OLD, lw=2, marker="s", ms=7, zorder=3,
            label=r"$T_{LB,rest}$   legacy rest-to-rest denominator (INVALIDATED)")
    ax.plot(rho, t_plant, ":", color=C_STATIC, lw=2, marker="D", ms=6, zorder=3,
            label=r"$T^*_{RH}$ (static-only, Phase 1F) — 2 cells later falsified")
    ax.plot(rho, t_dyn, color=C_DYN, lw=2.4, marker="o", ms=8, zorder=5,
            label=r"$T^*_{RH\text{-}remask,grid}$   sealed, fresh-seed confirmatory")
    ax.plot(rho, t_simple, color=C_SIMPLE, lw=2, marker="^", ms=8, zorder=4,
            label=r"$T^*_{simple}$   best ratified arm (H / C / P)")
    if rejected:
        ax.scatter([r for r, _ in rejected], [t for _, t in rejected], s=150,
                   facecolor=SURFACE, edgecolor=C_STATIC, lw=2, zorder=6)
        ax.annotate("rejected by the\ndynamic judge", xy=(rejected[0][0] - .03, rejected[0][1]),
                    xytext=(2.90, 0.315), color=C_STATIC, fontsize=8.5, linespacing=1.4,
                    ha="left", va="bottom",
                    arrowprops=dict(arrowstyle="-", color=C_STATIC, lw=1))
    ax.text(3.54, 0.435, "$\\Delta T_{RH\\!-\\!ref}$\n(reference gap,\nNOT a plant bound)", color=C_SIMPLE, fontsize=9.5,
            ha="center", va="center", style="italic", linespacing=1.35, zorder=7)
    ax.scatter([5.0], [0.50], s=120, facecolor="none", edgecolor=INK, lw=1.8, zorder=7)
    ax.annotate("nominal cue 10 m (T = 0.50 s)\nRH-remask reference first certifies at\n0.55 s (11 m). Global plant limit UNRESOLVED.",
                xy=(5.02, 0.478), xytext=(4.30, 0.115), color=INK, fontsize=8.5,
                linespacing=1.4, ha="left",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=1))
    ax.set_xlabel(r"initial radial spread  $\rho_0$  [m]", color=INK2, fontsize=9.5)
    ax.set_ylabel("required lead time  T  [s]      (cue distance = 20 m/s × T)",
                  color=INK2, fontsize=9.5)
    ax.set_title("(a)  restricted-class references after the authoritative-judge audit",
                 color=INK, fontsize=11, loc="left", pad=10)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0); ax.set_axisbelow(True)
    ax.set_xticks(rho); ax.set_xlim(2.6, 5.4); ax.set_ylim(0, 0.98)
    leg = ax.legend(frameon=False, fontsize=8.5, loc="upper left", handlelength=2.4, borderpad=0)
    for t in leg.get_texts():
        t.set_color(INK2)

    # ---- (b) actual-trajectory v_soft by witness class ---------------------------
    def acts(rows, pred):
        return [r["v_soft_actual"] for r in rows
                if r.get("v_soft_actual") is not None and pred(r)]
    groups = [
        ("legacy baseline\n(H/C/P, n=6)", acts(H["rows"], lambda r: r["src"] == "1B"), C_SIMPLE),
        ("Arm L  hold\ncertified (n=5)", acts(H["rows"], lambda r: r["src"] == "ARM_L"
                                              and "TIER4_DYNAMIC_REMASK" in r.get("labels", [])), C_DYN),
        ("Arm L  hold\nrejected (n=2)", acts(H["rows"], lambda r: r["src"] == "ARM_L"
                                             and "TIER4_DYNAMIC_REMASK" not in r.get("labels", [])), "#57606a"),
        ("Arm L  max-clr\n(1F, n=8)", acts(M["rows"], lambda r: True), C_STATIC),
    ]
    for i, (name, vals, col) in enumerate(groups):
        if not vals:
            continue
        bx.scatter(np.full(len(vals), i) + np.linspace(-.11, .11, len(vals)), vals,
                   s=52, color=col, zorder=4, edgecolor=SURFACE, lw=1.2)
        lab = ("%.2f–%.2f" % (min(vals), max(vals))) if len(vals) > 1 else ("%.2f" % vals[0])
        if min(vals) > THETA:
            bx.text(i, max(vals) + 0.055, lab, ha="center", va="bottom", color=INK, fontsize=8.5)
        else:
            bx.text(i, min(vals) - 0.055, lab, ha="center", va="top", color=INK, fontsize=8.5)
    bx.axhline(THETA, color=INK2, lw=1.4, ls="--", zorder=3)
    bx.text(3.42, THETA + 0.025, r"$\theta$ = 0.9", color=INK2, fontsize=9, ha="right")
    bx.set_xticks(range(len(groups)), [g[0] for g in groups], color=INK2, fontsize=8.5)
    bx.set_ylim(-0.12, 1.12); bx.set_xlim(-0.55, 3.55)
    bx.set_ylabel("actual-trajectory  $v_{soft}$", color=INK2, fontsize=9.5)
    bx.set_title("(b)  what survives the dynamic judge", color=INK, fontsize=11,
                 loc="left", pad=10)
    bx.grid(axis="y", color=GRID, lw=0.8, zorder=0); bx.set_axisbelow(True)

    fig.tight_layout()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=190, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
