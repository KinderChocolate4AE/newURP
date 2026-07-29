"""C-1 Phase 1P step 0a — find a NON-VACUOUS instance for invariant I1.

Why this exists
---------------
I1 asserts: a STRONGER attacker class never improves defender viability.  In the
Phase 1O suite the instance used was (rho0 2.8, tl 0.30, arm C), where

    v_fixed = v_union = 1.000

i.e. EVERY feasible attacker path in the sampled set was caught by the static
snapshot judge.  The inequality `v_union <= v_fixed` then holds for the trivial
reason that both sides are pinned at the ceiling.  A monotonicity bug -- an
enlarged attacker class that somehow *raises* measured viability -- could not be
detected by such an instance.  Phase 1O flagged this and deferred the fix.

This script does the deferred work: sweep the scenario grid, measure v_fixed
under the FIXED (Block-1) attacker class, and report the cells where
0 < v_fixed < 1.  Those cells have feasible-but-uncaught paths, so the union
class has genuine room to move the statistic in either direction and the
inequality becomes a real test.

Selection rule (fixed BEFORE looking at the numbers, so this is not a
post-hoc pick):
    among cells with v_fixed in (LO, HI), take the one with the LARGEST
    uncaught-but-feasible count n_gap = (feasible & ~caught).sum().
    Rationale: n_gap is the number of samples that a monotonicity violation
    could act on, so it is the instance's detection power.  Ties -> smallest
    rho0, then smallest tl, then arm C before P (deterministic).

Nothing here changes a verdict.  It changes which cell the property test runs on.
"""
from __future__ import annotations
import argparse, json, pathlib
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, R_BODY, M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, _mask_moving, DT
from shepherd.game import viability as V

# selection band, fixed in advance
LO, HI = 0.02, 0.98
N_FIXED = 4000          # same sample count the I1 instance uses
SEED_FIXED = 11         # same stream

# scenario grid: the D0 cells plus the neighbouring tl values, both arms
RHO0 = [2.8, 3.2, 4.0, 5.0]
TL = [0.15, 0.30, 0.40, 0.50, 0.55, 0.70, 0.85, 1.00]
ARMS = ["C", "P"]


def _env():
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"])
    return pe, E, make_finisher_fn(THETA)


def measure_cell(pe, E, fin, rho0, tl, arm, n=N_FIXED, seed=SEED_FIXED):
    """v_fixed under the Block-1 attacker class, plus the gap counts."""
    w = log_ctrl(make_contract() if arm == "C" else make_pd())
    rec = rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin,
                          r_lane=PRIMARY["r_net_dir"], r_body=R_BODY + M_SAFETY)
    t = rec.get("_t_ref")
    if t is None or rec.get("fire_step") is None:
        return None
    o = np.asarray(rec["_obs"][t], float)
    P = np.asarray(rec["_lim"][t:], float)
    Vp = np.asarray(rec["_vel"][t:], float)
    p_att = o[ATT_P0:ATT_P0 + 3]
    v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]
    u = V.build_reachable_union(p_att, v_att, tau=float(E.tau_deploy),
                                a_att_max=E.a_att_max, n=n,
                                n_segments=max(int(E.n_segments), 2), seed=seed, **kw)
    m0 = np.concatenate([_mask_moving(pb, L, E.kill_radius, float(E.tau_deploy))
                         for pb in u.path_blocks])
    feas = m0 & u.turn_feasible
    caught = np.asarray(u.caught, bool)
    n_feas = int(feas.sum())
    if n_feas == 0:
        return None
    n_caught = int((caught & feas).sum())
    return {"rho0": rho0, "tl": tl, "arm": arm, "fire_step": int(rec["fire_step"]),
            "n_feasible": n_feas, "n_caught": n_caught,
            "n_gap": n_feas - n_caught, "v_fixed": n_caught / n_feas}


def select(cells):
    """Apply the pre-registered selection rule."""
    band = [c for c in cells if LO < c["v_fixed"] < HI]
    if not band:
        return None, band
    band.sort(key=lambda c: (-c["n_gap"], c["rho0"], c["tl"], c["arm"]))
    return band[0], band


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_i1_instance.json")
    a = ap.parse_args()

    pe, E, fin = _env()
    cells, skipped = [], []
    for rho0 in RHO0:
        for tl in TL:
            for arm in ARMS:
                r = measure_cell(pe, E, fin, rho0, tl, arm)
                if r is None:
                    skipped.append({"rho0": rho0, "tl": tl, "arm": arm})
                    continue
                cells.append(r)
                print("  rho0 %.1f tl %.2f %s  v_fixed %.4f  (feas %5d, gap %5d)"
                      % (rho0, tl, arm, r["v_fixed"], r["n_feasible"], r["n_gap"]),
                      flush=True)

    chosen, band = select(cells)
    n_sat = sum(1 for c in cells if c["v_fixed"] >= 1.0 - 1e-12)
    print("\n  cells measured %d | skipped(no fire) %d | v_fixed==1 saturated %d | in band %d"
          % (len(cells), len(skipped), n_sat, len(band)))
    if chosen is None:
        print("  !! NO cell in the band -- I1 cannot be made non-vacuous on this grid.")
    else:
        print("  chosen: rho0 %.1f tl %.2f arm %s  v_fixed %.4f  n_gap %d"
              % (chosen["rho0"], chosen["tl"], chosen["arm"],
                 chosen["v_fixed"], chosen["n_gap"]))

    out = {"meta": {"script": "c1_phase1p_i1_instance", "purpose": "0a non-vacuous I1 instance",
                    "selection_rule": "max n_gap among %.2f < v_fixed < %.2f; ties -> rho0, tl, arm"
                                      % (LO, HI),
                    "n_samples": N_FIXED, "seed": SEED_FIXED, "reset": 1100},
           "n_cells": len(cells), "n_saturated": n_sat, "n_in_band": len(band),
           "chosen": chosen, "band": band, "cells": cells, "skipped": skipped}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote", p, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
