"""Render the Move A0 boundary-probe figure (docs/09 (gggg)) from the JSON:
  (a) terminal co-design map: (r_kill x r_net_dir) grid, clearance margin shaded,
      eta=1 boundary, realizable region, safe cells, aperture-loss labels.
  (b) eta axis story: clearance margin vs eta (realizable vs diagnostic), the
      eta=1 crossing, capture-aperture cost, + the dynamic-G3 result (all fail).
Usage: python -m shepherd.scripts.c1_moveA0_plot"""
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
    ap.add_argument("--json", default="results/c1_corridor/c1_moveA0.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_moveA0.png")
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.json).read_text())
    g = d["geometry_grid"]; r = d["readout"]; dyn = d["dynamic_g3"]
    rks = sorted({c["r_kill"] for c in g})
    rns = sorted({c["r_net_dir"] for c in g}, reverse=True)   # wide->narrow left->right
    cell = {(c["r_kill"], c["r_net_dir"]): c for c in g}

    fig = plt.figure(figsize=(13.5, 5.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.28)

    # (a) grid map -----------------------------------------------------------
    ax = fig.add_subplot(gs[0, 0])
    Z = np.full((len(rks), len(rns)), np.nan)
    for i, rk in enumerate(rks):
        for j, rn in enumerate(rns):
            c = cell[(rk, rn)]
            Z[i, j] = c["clearance_margin"] if c["clearance_margin"] is not None else np.nan
    im = ax.imshow(Z, origin="lower", cmap="RdYlGn", vmin=-1.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(rns))); ax.set_xticklabels(rns)
    ax.set_yticks(range(len(rks))); ax.set_yticklabels(rks)
    ax.set_xlabel("r_net_dir  (m)   [→ more directional, more aperture loss]")
    ax.set_ylabel("r_kill_eff  (m)")
    for i, rk in enumerate(rks):
        for j, rn in enumerate(rns):
            c = cell[(rk, rn)]
            txt = f"η={c['eta']:.2f}"
            if c["safe_exists"]:
                txt += "\nSAFE"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7,
                    color=("k" if c["realizable"] else "#777"))
            if c["safe_exists"] and c["realizable"]:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False,
                                           edgecolor="#0b6", lw=3))
            if not c["realizable"]:
                ax.plot(j, i - 0.34, marker="x", color="#999", ms=5)
    # realizable region outline (r_kill<=2.6, r_net>=2.0)
    ri = [i for i, rk in enumerate(rks) if rk <= 2.6]
    rj = [j for j, rn in enumerate(rns) if rn >= 2.0]
    ax.add_patch(plt.Rectangle((min(rj) - 0.5, min(ri) - 0.5), len(rj), len(ri),
                               fill=False, edgecolor="#0057d9", lw=2, ls="--"))
    ax.text(min(rj) - 0.45, max(ri) + 0.30, "physically realizable", color="#0057d9",
            fontsize=8, fontweight="bold")
    plt.colorbar(im, ax=ax, label="clearance margin (m)  [green ≥0 lane-clear]", shrink=0.85)
    ax.set_title("(a) terminal co-design map (θ=0.9)  — green box = realizable & safe\n"
                 "eta = r_kill / (r_net_dir + r_body 0.2 + m_safety 0.2)", fontsize=9)

    # (b) eta axis + aperture cost + dynamic ---------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    for c in g:
        mk = "o" if c["realizable"] else "x"
        col = "#2e7d32" if c["safe_exists"] else "#b0b0b0"
        clr = c["clearance_margin"]
        if clr is None:
            clr = -1.05
        ax2.scatter(c["eta"], clr, c=col, marker=mk, s=60,
                    edgecolor=("#0b6" if (c["safe_exists"] and c["realizable"]) else "none"),
                    linewidth=1.6, zorder=3)
    ax2.axvline(1.0, color="#c62828", ls="--", lw=1.4)
    ax2.axhline(0.0, color="#2e7d32", ls=":", lw=1)
    ax2.text(1.01, -0.9, "η=1 boundary", color="#c62828", fontsize=8, rotation=90)
    ax2.set_xlabel("eta = r_kill / (r_net_dir + r_body + m_safety)")
    ax2.set_ylabel("clearance margin (m)")
    ax2.set_ylim(-1.15, 0.95); ax2.set_xlim(0.7, 1.42)
    ax2.set_title("(b) eta axis: clearance crosses 0 at η≈1\n"
                  "○ realizable  ✕ diagnostic  green=terminal-safe", fontsize=9)
    # aperture-loss annotation for the realizable-safe cells
    for c in g:
        if c["safe_exists"] and c["realizable"]:
            ax2.annotate(f"({c['r_kill']},{c['r_net_dir']})\napLoss {c['aperture_loss']*100:.0f}%"
                         f"  p_feas {c['p_feas']:.3f}", (c["eta"], c["clearance_margin"]),
                         textcoords="offset points", xytext=(-6, 10), fontsize=6.6,
                         color="#0b6")
    # dynamic G3 box
    lines = ["dynamic G3 (θ=0.9):"]
    for dd in dyn:
        wm = dd["warm"]["m_clear"]
        lines.append(f"  {dd['cell'][:9]} η{dd['eta']:.2f}: warm m_clr "
                     f"{wm:+.1f}, ring {'fires' if dd['standoff_ring']['fire_step'] else 'no-fire'}"
                     f" → tier {dd['standoff_ring']['best_tier']}")
    lines.append("→ all dynamic FAIL: barrier is trajectory-level")
    ax2.text(0.71, 0.9, "\n".join(lines), fontsize=6.6, va="top",
             bbox=dict(boxstyle="round", fc="#fff3e0", ec="#e65100", alpha=0.95))

    fig.suptitle(f"Move A0 physically-grounded boundary probe   VERDICT: {r['verdict']}",
                 fontsize=11, y=1.01)
    fig.savefig(a.out, dpi=130, bbox_inches="tight")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
