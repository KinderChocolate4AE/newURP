"""Render the N1 temporal-grounding figure (docs/09 (ffff)) from the JSON:
  (a) R_geom vs capture-effective bands (lower/nominal/upper) vs travel, with the
      committed-attacker requirement R_req(tau) band -- the lower band dips BELOW
      R_req at the crossing = premise not resolved at the grounded bound.
  (b) net coherence vs travel (folding, anisotropy, axial depth) -- coherent, but
      on the UNPHYSICAL flat-init mesh.
Usage: python -m shepherd.scripts.n1_temporal_plot"""
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
    ap.add_argument("--json", default="results/c1_corridor/n1_temporal.json")
    ap.add_argument("--out", default="results/c1_corridor/n1_temporal.png")
    a = ap.parse_args()
    d = json.loads(pathlib.Path(a.json).read_text())
    S = d["snapshots"]; meta = d["meta"]
    tr = np.array([r["cum_travel"] for r in S])
    tau = np.array([r["tau"] for r in S])
    engage = meta["engage_dist"]; xstar = 10.0

    def rreq(t, unc):
        return meta["att_offset0"] + abs(meta["att_vperp"]) * t \
            + 0.5 * meta["a_att_max"] * t ** 2 + unc
    req_lo = rreq(tau, 0.20); req_hi = rreq(tau, 0.50); req_nom = rreq(tau, 0.35)

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))

    # (a) reach bands vs requirement -----------------------------------------
    ax.fill_between(tr, [r["R_lower"] for r in S], [r["R_upper"] for r in S],
                    color="#bbdefb", alpha=0.6, label="R_cap band (lower–upper)")
    ax.plot(tr, [r["R_geom"] for r in S], "-", color="#90a4ae", lw=1.4,
            label="R_geom (flat-init silhouette)")
    ax.plot(tr, [r["R_upper"] for r in S], "--", color="#1976d2", lw=1,
            label="upper = flat-init silhouette")
    ax.plot(tr, [r["R_nominal"] for r in S], "-o", color="#1565c0", ms=4,
            label="nominal = connected inradius (flat IC)")
    ax.plot(tr, [r["R_lower"] for r in S], "-o", color="#0d47a1", ms=4, lw=2,
            label="lower = folded-opening (GROUNDED)")
    ax.fill_between(tr, req_lo, req_hi, color="#ffcdd2", alpha=0.7)
    ax.plot(tr, req_nom, "-", color="#c62828", lw=2, label="R_req(τ) committed attacker")
    ax.axvline(xstar, color="#333", ls=":", lw=1)
    ax.axvline(engage, color="#2e7d32", ls="--", lw=1.2)
    ax.text(engage + 0.2, 0.2, "engage 20 m\n(Xu-anchored)", color="#2e7d32", fontsize=7.5)
    ax.text(xstar + 0.2, 3.0, "crossing\nτ*≈0.19 s", color="#333", fontsize=7.5)
    # mark the decisive gap
    rl = float(np.interp(xstar, tr, [r["R_lower"] for r in S]))
    rq = float(np.interp(xstar, tr, req_nom))
    ax.annotate("", xy=(xstar, rl), xytext=(xstar, rq),
                arrowprops=dict(arrowstyle="<->", color="#b71c1c", lw=1.5))
    ax.text(xstar - 3.7, (rl + rq) / 2, f"lower {rl:.2f}\n< R_req {rq:.2f}\n(FAILS)",
            color="#b71c1c", fontsize=7.5)
    ax.set_xlabel("net-front travel  (m)"); ax.set_ylabel("radius  (m)")
    ax.set_ylim(0, 3.2); ax.set_xlim(4, 21)
    ax.set_title("(a) capture-effective reach vs committed-attacker requirement", fontsize=9.5)
    ax.legend(fontsize=6.6, loc="upper right", framealpha=0.92)

    # (b) coherence -----------------------------------------------------------
    ax2.plot(tr, [r["folding_ratio"] for r in S], "-o", color="#6a1b9a", ms=4,
             label="folding ratio (cellsum/silhouette)")
    ax2.plot(tr, [r["anisotropy"] for r in S], "-s", color="#00838f", ms=4,
             label="anisotropy (max/min sector)")
    ax2.plot(tr, [r["axial_depth"] for r in S], "-^", color="#ef6c00", ms=4,
             label="axial depth (m)")
    ax2.axhline(1.0, color="#999", lw=0.7, ls=":")
    ax2.axvline(xstar, color="#333", ls=":", lw=1)
    ax2.set_xlabel("net-front travel  (m)"); ax2.set_ylabel("value")
    ax2.set_ylim(0, 3.4); ax2.set_xlim(4, 21)
    ax2.set_title("(b) net coherence — flat-init mesh stays coherent\n"
                  "(folding≈1) BUT the flat launch IC is unphysical", fontsize=9.5)
    ax2.legend(fontsize=7, loc="upper left")

    fig.suptitle(f"N1 temporal grounding (seed 1100 crossing)   VERDICT: {d['verdict']}",
                 fontsize=11, y=1.01)
    fig.tight_layout()
    fig.savefig(a.out, dpi=130, bbox_inches="tight")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
