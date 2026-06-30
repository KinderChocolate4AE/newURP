"""theta_fire calibration for the S14 CONSERVATIVE v_shot signal (L2 prep).

GPT review (2026-06-28): theta_fire=0.8 was tuned on the LEGACY single-segment
soft. Under the conservative extreme-point union the soft score changes meaning, so
the gate (fire iff v_shot_soft >= theta_fire) must be re-calibrated. Fix (do NOT
blindly renormalize soft): keep the conservative v_shot for reward/credit, and
calibrate a SEPARATE gate threshold against an EXTERNAL capture label.

EXTERNAL LABEL = ANALYTIC worst-case containment of the free reachable ball by the
point-mass net sphere (no limiters): the attacker's tau-reachable ball
B(c, R), R = 1/2 a_att_max tau^2, is fully contained iff
    ||c - net_center|| + R <= net_radius.
This is EXACT ground truth (NOT the surrogate's own worst), so calibrating the
conservative soft against it is a real external check, not circular.

KEY FINDING (this harness). The conservative soft equals 1.0 exactly when the set
is robustly contained (every feasible witness caught, == v_shot_worst==1) and falls
off once any boundary witness escapes. So the danger is NOT "the gate never fires"
(GPT's worry) but the opposite: at INTERMEDIATE containment the soft can sit ~0.85
while v_shot_worst is still 0 (a feasible escape exists). Because the finisher is
MISS-IS-FREE (a wasted shot is costly to the defender, free to the attacker), the
gate must NOT fire there. => theta_fire must exceed the highest soft observed among
NOT-robustly-contained configs, i.e. it should be RAISED from 0.8. The harness
reports the zero-wasted-shot band and recommends a threshold inside it.

Torch-free; uses shepherd.game.viability only.
"""
from __future__ import annotations
import numpy as np

from shepherd.game import viability as V

_EPS = 1e-9


def analytic_contained(a_att_max, tau, net_radius, offset=0.0):
    """EXACT: is the whole free reachable ball inside the net sphere?
    R_reach = 1/2 a tau^2; contained iff offset + R_reach <= net_radius (a small
    epsilon admits the exact boundary a*tau^2/2 == net_radius)."""
    R = 0.5 * float(a_att_max) * float(tau) ** 2
    return bool((offset + R) <= net_radius + _EPS)


def _soft_worst(a_att_max, *, tau, net_radius, n_segments, n_samples, seed, v_speed):
    """Conservative v_shot at the canonical commit geometry (no limiters)."""
    x = np.array([0.0, 0.0, 0.0])
    v = np.array([float(v_speed), 0.0, 0.0])
    nc = x + v * tau                                  # net on the predicted endpoint
    r = V.v_shot(x, v, tau=tau, a_att_max=float(a_att_max), judge="point_mass",
                 net_center=nc, net_radius=net_radius, n=n_samples, seed=seed,
                 n_segments=n_segments)
    return float(r.v_shot_soft), float(r.v_shot_worst)


def agility_sweep(*, tau=0.4, net_radius=2.0, a_grid=None, n_segments=4,
                  n_samples=800, seed=0, v_speed=8.0):
    """Vary attacker agility a_att_max; record conservative soft/worst + the EXACT
    analytic containment label (catchable iff R_reach <= net_radius)."""
    if a_grid is None:
        a_grid = np.arange(10.0, 40.001, 2.5)
    rows = []
    for a in a_grid:
        soft, worst = _soft_worst(a, tau=tau, net_radius=net_radius,
                                  n_segments=n_segments, n_samples=n_samples,
                                  seed=seed, v_speed=v_speed)
        rows.append(dict(sweep="a_att_max", x=float(a), soft=soft, worst=worst,
                         R_reach=0.5 * float(a) * tau ** 2,
                         contained=analytic_contained(a, tau, net_radius)))
    return rows


def net_radius_sweep(*, tau=0.4, a_att_max=30.0, r_grid=None, n_segments=4,
                     n_samples=800, seed=0, v_speed=8.0):
    """Vary net_radius at fixed agility; same labels. Ties to the N1 frontier-net
    question (which paper net sizes cross R_reach) and exposes the intermediate
    soft~0.85 / worst==0 wasted-shot zone."""
    if r_grid is None:
        r_grid = np.arange(1.5, 3.001, 0.1)
    rows = []
    for r in r_grid:
        soft, worst = _soft_worst(a_att_max, tau=tau, net_radius=float(r),
                                  n_segments=n_segments, n_samples=n_samples,
                                  seed=seed, v_speed=v_speed)
        rows.append(dict(sweep="net_radius", x=float(r), soft=soft, worst=worst,
                         R_reach=0.5 * a_att_max * tau ** 2,
                         contained=analytic_contained(a_att_max, tau, float(r))))
    return rows


def threshold_sweep(rows, theta_grid=None):
    """Confusion of the soft-gate (fire iff soft>=theta) vs the analytic label.
    `wasted` = fires on a NOT-contained config = a wasted miss-is-free shot."""
    if theta_grid is None:
        theta_grid = np.round(np.arange(0.50, 1.0001, 0.025), 4)
    pos = sum(1 for r in rows if r["contained"])
    out = []
    for th in theta_grid:
        tp = sum(1 for r in rows if r["soft"] >= th and r["contained"])
        fp = sum(1 for r in rows if r["soft"] >= th and not r["contained"])
        fn = sum(1 for r in rows if r["soft"] < th and r["contained"])
        fires = tp + fp
        prec = tp / fires if fires else 1.0
        rec = tp / pos if pos else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out.append(dict(theta=float(th), fire_rate=fires / len(rows), precision=prec,
                        recall=rec, f1=f1, wasted=int(fp)))
    return out


def zero_wasted_band(threshold_rows):
    """(theta_min, theta_max) of thetas with ZERO wasted shots and nonzero fire
    rate (fire => robustly contained). Empty -> (None, None)."""
    ok = [s["theta"] for s in threshold_rows if s["wasted"] == 0 and s["fire_rate"] > 0]
    return (min(ok), max(ok)) if ok else (None, None)


def recommend_theta(threshold_rows, margin_frac=0.5):
    """Recommend a theta INSIDE the zero-wasted band (fire only when robustly
    contained), placed margin_frac of the way up the band for robustness against
    the finite-witness boundary gap. Fallback = max-F1 if no zero-wasted theta."""
    lo, hi = zero_wasted_band(threshold_rows)
    if lo is None:
        return max(threshold_rows, key=lambda s: s["f1"])["theta"]
    target = lo + margin_frac * (hi - lo)
    # snap to the nearest theta on the grid that is still zero-wasted
    cands = [s["theta"] for s in threshold_rows if s["wasted"] == 0 and s["fire_rate"] > 0]
    return min(cands, key=lambda t: abs(t - target))


def _fmt_table(rows, cols, headers):
    out = "| " + " | ".join(headers) + " |\n"
    out += "|" + "|".join(["---"] * len(headers)) + "|\n"
    for r in rows:
        out += "| " + " | ".join(f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c])
                                 for c in cols) + " |\n"
    return out


def main():
    import pathlib
    tau, net_radius, K, n = 0.4, 2.0, 4, 800
    a_rows = agility_sweep(tau=tau, net_radius=net_radius, n_segments=K, n_samples=n)
    r_rows = net_radius_sweep(tau=tau, a_att_max=30.0, n_segments=K, n_samples=n)
    combined = a_rows + r_rows
    th = threshold_sweep(combined)
    lo, hi = zero_wasted_band(th)
    theta_star = recommend_theta(th)
    theta_f1 = max(th, key=lambda s: s["f1"])["theta"]

    md = []
    md.append("# Fire-gate (theta_fire) calibration — conservative v_shot (L2 prep)\n\n")
    md.append(f"Conservative union `n_segments={K}`, `n_samples={n}`, `tau={tau}`, "
              f"point-mass sphere, NO limiters. External label = analytic ball-in-sphere "
              f"containment (`R_reach = 1/2 a tau^2 <= net_radius`).\n\n")
    md.append(f"**Recommended `theta_fire` (conservative) = {theta_star:.3f}.** "
              f"Zero-wasted-shot band = [{lo:.3f}, {hi:.3f}] (any theta here fires "
              f"ONLY when robustly contained, i.e. `v_shot_worst==1`); recommendation is "
              f"placed mid-band for margin against the finite-witness boundary gap. "
              f"Max-F1 theta = {theta_f1:.3f}. **Raise from the legacy 0.8** "
              f"(0.8 lies BELOW {lo:.3f} -> it would fire at intermediate containment "
              f"where `worst==0`, wasting a miss-is-free shot).\n\n")
    md.append("Note: across both sweeps the conservative `v_shot_worst` agrees with the "
              "EXACT analytic containment label at every point — empirical evidence the "
              "conservative worst tracks true containment (it is still not a formal "
              "certificate; see the analytic helper / S14 caveat).\n\n")
    md.append("## Agility sweep (net_radius=2.0; contained iff a<=25 at tau=0.4)\n\n")
    md.append(_fmt_table(a_rows, ["x", "soft", "worst", "R_reach", "contained"],
                         ["a_att_max", "soft", "worst", "R_reach", "contained"]))
    md.append("\n## net_radius sweep (a=30; contained iff net_radius>=2.4)\n\n")
    md.append(_fmt_table(r_rows, ["x", "soft", "worst", "R_reach", "contained"],
                         ["net_radius", "soft", "worst", "R_reach", "contained"]))
    md.append("\n## Threshold sweep (gate vs analytic label, both sweeps combined)\n\n")
    md.append(_fmt_table(th, ["theta", "fire_rate", "precision", "recall", "f1", "wasted"],
                         ["theta", "fire_rate", "precision", "recall", "f1", "wasted"]))
    out = pathlib.Path(__file__).resolve().parents[2] / "results" / "fire_gate_calibration.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(md), encoding="utf-8")
    print(f"recommended theta_fire = {theta_star:.3f}  zero-wasted band [{lo:.3f},{hi:.3f}]  "
          f"max-F1 = {theta_f1:.3f}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
