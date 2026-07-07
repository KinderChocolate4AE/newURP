"""P4 clean-condition probe (docs/09 (r); analysis lane, torch-free).

Question (4) of the review checklist: does a 4-limiter configuration exist,
under the FROZEN M2 constants, with v_shot_soft >= theta_fire(0.9) AND
NOT boxed (n_feasible > 0)?  I.e. is the clean-fire reachable set non-empty,
and how wide is it compared to the boxed basin next door (question (3))?

Method: frozen witness union (build_reachable_union, se3_cone judge, S14
n_segments=4) for representative corridor states; then (a) ring-geometry grid
sweeps, (b) random 12-dim limiter-placement search, (c) greedy Gaussian local
refinement of the best non-boxed configs. Pure numpy; run anywhere.

  PYTHONPATH=. python3 -m shepherd.scripts.p4_clean_probe \
      --out results/p4_probe/probe.json
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.game import viability as V

# frozen M2 constants (configs/m2_l2_train.yaml)
TAU = 0.4
A_ATT = 30.0
KILL_R = 2.0
THETA = 0.9
CONE = dict(judge="se3_cone", net_apex=[2.0, 0.0, 0.0], n_F=[1.0, 0.0, 0.0],
            theta_net=0.067, range_min=0.0, range_max=29.847)


def union_for(x, v, seed):
    return V.build_reachable_union([x, 0, 0], [-v, 0, 0], tau=TAU, a_att_max=A_ATT,
                                   n=2000, n_segments=4, seed=seed, **CONE)


def ev(u, L):
    r = V.eval_union_with_limiters(u, np.asarray(L, float), KILL_R)
    return r.v_shot_soft, r.v_shot_worst, r.boxed_in, r.p_feasible


def ring(x, v, rho, c, phase, n_ring=4, axial_split=0.0):
    """n_ring limiters on a circle radius rho, axial position c*(v*TAU) down the
    ballistic path (+optional alternating axial split)."""
    xm = np.array([x, 0, 0]) + np.array([-v, 0, 0]) * TAU * c
    out = []
    for k, a in enumerate(np.linspace(0, 2 * np.pi, n_ring, endpoint=False)):
        ax = xm + np.array([-1, 0, 0]) * (axial_split * (k % 2))
        out.append(ax + rho * np.array([0, np.cos(a + phase), np.sin(a + phase)]))
    return np.array(out)


def grid_stage(u, x, v):
    rows, best = [], None
    for c in (0.25, 0.5, 0.75, 1.0):
        for phase in (0.0, np.pi / 4):
            for rho in np.arange(1.0, 3.01, 0.05):
                s, w, b, pf = ev(u, ring(x, v, rho, c, phase))
                rows.append(dict(rho=round(float(rho), 3), c=c, phase=round(float(phase), 3),
                                 v_soft=s, worst=w, boxed=b, p_feas=pf))
                if not b and (best is None or s > best[0]):
                    best = (s, w, rho, c, phase)
    return rows, best


def random_stage(u, x, v, rng, n=1000):
    """Random 4-limiter placements in a cylinder around the ballistic path."""
    best = []
    for _ in range(n):
        ax = rng.uniform(0.0, v * TAU * 1.2, 4)                 # axial along path
        rad = rng.uniform(1.0, 4.0, 4)
        ang = rng.uniform(0, 2 * np.pi, 4)
        L = np.stack([np.array([x, 0, 0]) + np.array([-1, 0, 0]) * ax[i]
                      + rad[i] * np.array([0, np.cos(ang[i]), np.sin(ang[i])])
                      for i in range(4)])
        s, w, b, pf = ev(u, L)
        if not b:
            best.append((s, w, pf, L))
    best.sort(key=lambda t: -t[0])
    return best[:3]


def refine(u, seeds, rng, iters=150, sigma=0.15):
    out = []
    for s0, w0, pf0, L0 in seeds:
        s_best, w_best, pf_best, L_best = s0, w0, pf0, L0.copy()
        for _ in range(iters):
            L = L_best + rng.normal(0, sigma, L_best.shape)
            s, w, b, pf = ev(u, L)
            if not b and s > s_best:
                s_best, w_best, pf_best, L_best = s, w, pf, L
        out.append(dict(v_soft=s_best, worst=w_best, p_feas=pf_best,
                        limiters=L_best.tolist()))
    out.sort(key=lambda d: -d["v_soft"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/p4_probe/probe.json")
    ap.add_argument("--states", default="16:20,12:16,20:24")
    ap.add_argument("--seeds", default="0,1")
    a = ap.parse_args()
    rng = np.random.default_rng(11)
    report = {"theta_fire": THETA, "constants": {"tau": TAU, "a_att": A_ATT,
              "kill_radius": KILL_R, **{k: v for k, v in CONE.items() if k != "judge"}},
              "states": []}
    for st in a.states.split(","):
        x, v = (float(t) for t in st.split(":"))
        for seed in (int(s) for s in a.seeds.split(",")):
            u = union_for(x, v, seed)
            base = ev(u, np.zeros((0, 3)))
            grid, gbest = grid_stage(u, x, v)
            cand = random_stage(u, x, v, rng)
            ref = refine(u, cand, rng) if cand else []
            # clean window width from the finest grid family (c, phase of gbest)
            width = 0.0
            if gbest:
                fam = [r for r in grid if r["c"] == gbest[3] and r["phase"] == round(float(gbest[4]), 3)]
                width = 0.05 * sum(1 for r in fam if (not r["boxed"]) and r["v_soft"] >= THETA)
            top = ref[0] if ref else None
            report["states"].append(dict(
                x=x, v=v, union_seed=seed, n_witness=u.n_total,
                v_soft_unshaped=base[0],
                grid_best_nonboxed=dict(v_soft=gbest[0], worst=gbest[1], rho=float(gbest[2]),
                                        c=gbest[3], phase=float(gbest[4])) if gbest else None,
                grid_clean_window_width_m=width,
                refined_best=top,
                clean_exists=bool((gbest and gbest[0] >= THETA) or (top and top["v_soft"] >= THETA)),
                capture_grade_found=bool(top and top["worst"] >= 1.0 and top["v_soft"] >= THETA),
            ))
            r = report["states"][-1]
            print(f"x={x} v={v} seed={seed}: unshaped={r['v_soft_unshaped']:.3f} "
                  f"grid_best={gbest[0]:.3f}@rho{gbest[2]:.2f} "
                  f"refined_best={top['v_soft'] if top else float('nan'):.3f} "
                  f"clean_exists={r['clean_exists']} capture_grade={r['capture_grade_found']}")
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print("->", out)


if __name__ == "__main__":
    main()
