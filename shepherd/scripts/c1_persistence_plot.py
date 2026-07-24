"""Render the C-1 persistence diagnostic (docs/09 (eeee)) figures from the JSON:
  (a) capture-clearance Pareto (per release x branch; optimistic vs engaged bound)
  (b) capture-margin persistence curve after release (fire-delay sweep)
  (c) median capture travel vs the net engage anchor (the net-temporal premise)
Usage: python -m shepherd.scripts.c1_persistence_plot"""
from __future__ import annotations

import argparse
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="results/c1_corridor/c1_persistence.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_persistence.png")
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.json).read_text())
    g = d["grid"]; r = d["readout"]; engage = d["meta"]["engage_dist"]
    rels = d["meta"]["release_times"]
    cmap = plt.get_cmap("viridis")
    col = {t: cmap(i / max(len(rels) - 1, 1)) for i, t in enumerate(rels)}

    fig = plt.figure(figsize=(15, 4.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.15, 0.9], wspace=0.32)

    # (a) capture-clearance Pareto -------------------------------------------
    axp = fig.add_subplot(gs[0, 0])
    axp.axvspan(0, 3.2, color="#e8f5e9", zorder=0)
    axp.axvline(0, color="#2e7d32", lw=1.2, ls="--", zorder=1)
    for c in g:
        t = c["t_rel"]; x = c["min_friendly_clearance"]
        # optimistic capture (cone-from-launch)
        axp.scatter(x, c["p_cap_B_phys"], s=70, color=col[t],
                    edgecolor=("k" if c["gate_B_phys_optimistic"] else "none"),
                    linewidth=1.6, zorder=3)
        # engaged bound (net certified open) -> sits at 0
        axp.scatter(x, c["p_cap_B_engaged"], s=26, color=col[t], marker="v",
                    alpha=0.55, zorder=2)
    axp.set_xlim(-2.4, 1.3); axp.set_ylim(-0.08, 1.12)
    axp.set_xlabel("min friendly-lane clearance  (m)   [≥0 = lane clear]")
    axp.set_ylabel("Case-B capture  p_cap")
    axp.set_title("(a) capture–clearance Pareto\n○ optimistic (cone from launch)  "
                  "▽ engaged (net open)", fontsize=9)
    axp.text(-2.3, 0.10, "engaged bound → 0  (capture below engage travel)",
             color="#555", fontsize=7)
    axp.text(-2.3, 0.80, "black ring = passes gate\n(clearance≥0 ∧ capture>0)",
             fontsize=7)
    handles = [plt.Line2D([0], [0], marker="o", color="w",
                          markerfacecolor=col[t], markersize=8, label=f"t_rel={t}")
               for t in rels]
    axp.legend(handles=handles, fontsize=7, loc="upper right", framealpha=0.9)

    # (b) persistence curve ---------------------------------------------------
    axc = fig.add_subplot(gs[0, 1])
    gate_cells = [tuple(x) for x in r["gate_opt_cells"]] or [(6, "greedy_clear")]
    shown = 0
    for c in g:
        if (c["t_rel"], c["branch"]) in gate_cells and shown < 4:
            pers = c["persistence"]
            dl = [p["delay"] for p in pers]
            axc.plot(dl, [p["p_cap_B_phys"] for p in pers], "-o", color=col[c["t_rel"]],
                     label=f"t{c['t_rel']} {c['branch']}", ms=4)
            shown += 1
    axc.axhline(0, color="k", lw=0.6)
    axc.set_xlabel("fire delay after release  (deployment steps, ×0.05 s)")
    axc.set_ylabel("optimistic capture  p_cap(delay)")
    axc.set_ylim(-0.05, 1.08)
    axc.set_title("(b) capture-margin persistence after release\n"
                  "(engaged bound flat at 0 for all)", fontsize=9)
    axc.legend(fontsize=6.5, loc="lower left")
    axc.text(0.3, 0.12, "velocity-commitment\nwindow ≈ 0.3 s", fontsize=7.5, color="#333")

    # (c) capture travel vs engage (the premise) ------------------------------
    axt = fig.add_subplot(gs[0, 2])
    seen = {}
    for c in g:
        seen.setdefault(c["t_rel"], c["median_capture_travel"])
    xs = list(seen.keys()); ys = [seen[t] for t in xs]
    axt.bar([str(t) for t in xs], ys, color=[col[t] for t in xs])
    axt.axhline(engage, color="#c62828", lw=1.6, ls="--")
    axt.text(-0.4, engage + 0.4, f"engage anchor {engage:.0f} m\n(net N1-validated)",
             color="#c62828", fontsize=7.5)
    axt.set_ylim(0, engage + 6)
    axt.set_xlabel("release time t_rel")
    axt.set_ylabel("median capture travel  (m)")
    axt.set_title("(c) the net-temporal premise\ncapture ≈10 m ≪ engage 20 m", fontsize=9)

    fig.suptitle(f"C-1 Move B — capturability-persistence diagnostic (seed "
                 f"{d['manifest']['seed']})   VERDICT: {r['verdict']}",
                 fontsize=11, y=1.02)
    fig.savefig(a.out, dpi=130, bbox_inches="tight")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
