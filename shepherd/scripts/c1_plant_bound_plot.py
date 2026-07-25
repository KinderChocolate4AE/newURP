"""Fig B — plant bound vs controller bound (C-1 Phase 1F).

(a) required lead time T vs initial spread rho0, three curves:
      T_LB,rest   the rest-to-rest analytic bound used in Phase 1B/1C
      T*_plant    smallest T at which the LP witness reaches tier 4 in the FULL
                  closed-loop replay  (demonstrated, not analytic)
      T*_simple   smallest T at which any ratified simple arm (H/C/P) reaches tier 4
    The band between T*_plant and T*_simple is the controller gap.
(b) at the nominal cell (rho0 5.0, T 0.50) the plant optimum misses the lane floor
    by 12.5 mm; the minimal single-knob change that removes the miss.
"""
from __future__ import annotations
import argparse, json, math, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

C_OLD, C_PLANT, C_SIMPLE = "#3B5BDB", "#E8590C", "#099268"   # validated (dataviz, light)
INK, INK2, GRID = "#1f2328", "#57606a", "#e3e5e8"
SURFACE = "#fcfcfb"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plant", default="results/c1_corridor/c1_plant_bound.json")
    ap.add_argument("--envelope", default="results/c1_corridor/c1_response_envelope_fine.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_plant_bound.png")
    a = ap.parse_args()

    P = json.loads(pathlib.Path(a.plant).read_text())
    rho = sorted(float(k) for k in P["T_star_plant"])
    t_plant = [P["T_star_plant"][str(r)]["T_star_plant"] for r in rho]
    t_lb = [P["T_star_plant"][str(r)]["T_LB_rest"] for r in rho]

    E = json.loads(pathlib.Path(a.envelope).read_text())
    by = {}
    for c in E["cells"]:
        by.setdefault(c["rho0"], []).append(c)
    t_simple = []
    for r in rho:
        cs = sorted(by[r], key=lambda x: x["T_available"])
        t_simple.append(next((c["T_available"] for c in cs
                              if any(v["safe"] for v in c["arms"].values())), np.nan))

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.2, 4.3), width_ratios=[1.45, 1],
                                 facecolor=SURFACE)
    for x in (ax, bx):
        x.set_facecolor(SURFACE)
        for s in ("top", "right"):
            x.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            x.spines[s].set_color(GRID)
        x.tick_params(colors=INK2, labelsize=9, length=3)

    # ---- (a) required lead time -------------------------------------------------
    ax.fill_between(rho, t_plant, t_simple, color=C_SIMPLE, alpha=0.12, lw=0, zorder=1)
    ax.plot(rho, t_lb, "--", color=C_OLD, lw=2, marker="s", ms=7, zorder=3,
            label=r"$T_{LB,rest}$  analytic bound used in Phase 1B/1C")
    ax.plot(rho, t_plant, color=C_PLANT, lw=2, marker="o", ms=8, zorder=4,
            label=r"$T^*_{plant}$  LP witness, tier 4 in closed-loop replay")
    ax.plot(rho, t_simple, color=C_SIMPLE, lw=2, marker="^", ms=8, zorder=4,
            label=r"$T^*_{simple}$  best ratified arm (H / C / P)")

    # the old "lower bound" sits ABOVE the demonstrated plant bound at 3.2 and 4.0
    for r, lb, pl in zip(rho, t_lb, t_plant):
        if lb > pl + 1e-9:
            ax.annotate("", xy=(r, pl), xytext=(r, lb),
                        arrowprops=dict(arrowstyle="-|>", color=C_OLD, lw=1.4,
                                        shrinkA=3, shrinkB=3, alpha=.85), zorder=2)
    ax.text(3.34, 0.115, "old bound lies ABOVE the demonstrated\nplant  →  it is not a lower bound",
            color=C_OLD, fontsize=8.5, ha="left", va="bottom", linespacing=1.4)

    ax.scatter([5.0], [0.50], s=120, facecolor="none", edgecolor=INK, lw=1.8, zorder=6)
    ax.annotate("nominal (5.0, 0.50 s)\nplant optimum misses the\nlane floor by 12.5 mm",
                xy=(5.02, 0.485), xytext=(4.42, 0.245), color=INK, fontsize=8.5,
                linespacing=1.4, ha="left",
                arrowprops=dict(arrowstyle="-", color=INK2, lw=1))
    ax.text(3.62, 0.445, "controller gap", color=C_SIMPLE, fontsize=9.5,
            ha="center", va="center", style="italic", zorder=5)

    ax.set_xlabel(r"initial radial spread  $\rho_0$  [m]", color=INK2, fontsize=9.5)
    ax.set_ylabel("required lead time  T  [s]      (cue distance = 20 m/s × T)",
                  color=INK2, fontsize=9.5)
    ax.set_title("(a)  what the plant needs vs what the controllers need",
                 color=INK, fontsize=11, loc="left", pad=10)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xticks(rho); ax.set_xlim(2.6, 5.35); ax.set_ylim(0, 0.85)
    leg = ax.legend(frameon=False, fontsize=8.5, loc="upper left", labelcolor=INK2,
                    handlelength=2.2, borderpad=0)
    for t in leg.get_texts():
        t.set_color(INK2)

    # ---- (b) minimal single-knob change at the nominal cell ----------------------
    ks = P["knob_scan"]["knobs"]

    def first_ok(rows, key="m_star"):
        return next((r for r in rows if r[key] >= 0), None)

    items = [("limiter $a_{max}$", 30.0, first_ok(ks["a_max"])["value"], "m/s²"),
             (r"initial spread $\rho_0$", 5.0, first_ok(ks["rho0"])["value"], "m"),
             ("band upper edge", 2.65, first_ok(ks["band_hi"])["value"], "m"),
             ("lane floor", 2.50, first_ok(ks["lane_floor"])["value"], "m")]
    items = [(n, b, v, u, abs(v - b) / b * 100) for n, b, v, u in items]
    items.sort(key=lambda z: z[4])
    y = np.arange(len(items))
    bx.barh(y, [z[4] for z in items], height=0.5, color=C_PLANT, zorder=3)
    for i, (n, b, v, u, pct) in enumerate(items):
        bx.text(pct + 0.06, i, f"{b:g} → {v:g} {u}   ({pct:.1f} %)", va="center",
                color=INK, fontsize=8.8)
    bx.set_yticks(y, [z[0] for z in items], color=INK2)
    bx.invert_yaxis()
    bx.set_xlim(0, 2.7)
    bx.set_xlabel("relative change needed to remove the 12.5 mm miss  [%]",
                  color=INK2, fontsize=9.5)
    bx.set_title("(b)  nominal cell — minimal single-knob change",
                 color=INK, fontsize=11, loc="left", pad=10)
    bx.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    bx.set_axisbelow(True)
    bx.text(0.985, 0.965, "lead time alone: 0.50 → 0.55 s  (+10 %)",
            transform=bx.transAxes, color=INK2, fontsize=8.5, style="italic",
            ha="right", va="top")

    fig.tight_layout()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=190, facecolor=SURFACE)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
