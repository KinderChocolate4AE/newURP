"""A-3b robust-witness probe (docs/13 v0.3 SS8 R-6; docs/09 (ff); analysis lane).

The (ff) discovery: the clean predicate is razor-thin in the CRN-sample
dimension -- P4 witnesses were capture-grade under their OWN union seed only
(fresh-seed clean freq 1/8..8/8). This probe rebuilds the spawn bank against a
ROBUST objective: greedy Gaussian refinement of the 4-limiter placement whose
objective is the mean clean indicator over SEARCH union seeds, then validated
on DISJOINT validation seeds (CRN hygiene: search 100..104, validate 200..209;
acceptance = validation robust_clean_frac >= 0.9).

Cost trick: for fixed (x, v) the reachable union depends only on the seed, so
unions are built ONCE per seed and every candidate is scored with the cheap
eval_union_with_limiters call -- refinement is ~1000 evals, not ~1000 builds.

Candidates per (x, v) condition: (a) the original P4 witness, (b) the
transplant of the most robust known pattern (attacker-relative, x-scaled by
v'/v). Output = probe-schema-compatible bank (spawn_bank.load_t0 reads it
directly) + per-sigma spawn-clean baselines for the A-3b ladder's
RELATIVE exit thresholds (R-7).

CLI (numpy-only; chunk with --state for 45s sandboxes):
  PYTHONPATH=. python3 -m shepherd.scripts.a3_robust_witness_probe \
      --probe-glob 'results/p4_probe/probe_s*.json' \
      --out results/a3_robust_bank.json [--state 0] [--iters 120]
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.game import viability as V
from shepherd.train.spawn_bank import APEX, N_F, T0State, load_t0

# frozen M2 constants (configs/m2_l2_train.yaml; identical to p4_clean_probe)
TAU = 0.4
A_ATT = 30.0
KILL_R = 2.0
THETA = 0.9
CONE = dict(judge="se3_cone", net_apex=list(APEX), n_F=list(N_F),
            theta_net=0.067, range_min=0.0, range_max=29.847)
SEARCH_SEEDS = tuple(range(100, 105))     # refinement objective (5)
VAL_SEEDS = tuple(range(200, 210))        # disjoint validation (10)
ACCEPT_MIN = 0.9                          # R-6 bank threshold (ratified)
SIGMAS = (0.02, 0.05, 0.1, 0.2, 0.5)      # A-3b ladder baselines (R-7)


def union_for(x, v, seed):
    return V.build_reachable_union([x, 0, 0], [-v, 0, 0], tau=TAU,
                                   a_att_max=A_ATT, n=2000, n_segments=4,
                                   seed=seed, **CONE)


def stats(unions, L):
    """clean/capture-grade fractions + margins of a limiter set over unions."""
    L = np.asarray(L, float)
    cl = cap = 0
    vmin = 1.0
    for u in unions:
        r = V.eval_union_with_limiters(u, L, KILL_R)
        c = (not r.boxed_in) and (r.v_shot_soft >= THETA)
        cl += int(c)
        cap += int(c and r.v_shot_worst >= 1.0)
        vmin = min(vmin, r.v_shot_soft)
    n = len(unions)
    return cl / n, cap / n, vmin


def refine_robust(unions, L0, rng, iters=120):
    """Greedy Gaussian ascent on (clean_frac, min v_soft) over cached unions."""
    best = np.asarray(L0, float).copy()
    b_cl, b_cap, b_vm = stats(unions, best)
    for it in range(iters):
        sig = 0.15 if it < iters // 2 else 0.05
        cand = best + rng.normal(0.0, sig, best.shape)
        c_cl, c_cap, c_vm = stats(unions, cand)
        if (c_cl, c_vm) > (b_cl, b_vm):
            best, b_cl, b_cap, b_vm = cand, c_cl, c_cap, c_vm
    return best, b_cl


def transplant(t0_from: T0State, x: float, v: float) -> np.ndarray:
    """Attacker-relative pattern transfer, x-offset scaled by speed ratio."""
    L = np.asarray(t0_from.limiters, float)
    rel = L - np.array([t0_from.x, 0.0, 0.0])
    rel[:, 0] *= (v / t0_from.v)
    return np.array([x, 0.0, 0.0]) + rel


def sigma_baselines(unions_val, L, rng, n_draws=20):
    """Per-sigma spawn-clean baseline (R-7 relative exits): jittered limiter
    sets scored on validation unions (position jitter only -- attacker jitter
    shifts the union and is second-order for the baseline's purpose)."""
    out = {}
    for sig in SIGMAS:
        ok = 0
        for _ in range(n_draws):
            cl, _, _ = stats(unions_val[:5], L + rng.normal(0, sig, L.shape))
            ok += cl
        out[str(sig)] = round(ok / n_draws, 3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-glob", default="results/p4_probe/probe_s*.json")
    ap.add_argument("--out", default="results/a3_robust_bank.json")
    ap.add_argument("--state", type=int, default=None,
                    help="process one witness index (45s chunking); merge on rerun")
    ap.add_argument("--iters", type=int, default=120)
    a = ap.parse_args()
    t0s = load_t0(a.probe_glob)
    donor = max(t0s, key=lambda t: (t.x, t.v))       # x20v24u0 = known-robust
    rng = np.random.default_rng(23)
    out_p = pathlib.Path(a.out)
    bank = (json.loads(out_p.read_text()) if out_p.exists()
            else {"theta_fire": THETA,
                  "constants": {"tau": TAU, "a_att": A_ATT,
                                "kill_radius": KILL_R,
                                **{k: v for k, v in CONE.items()
                                   if k != "judge"}},
                  "seeds": {"search": list(SEARCH_SEEDS),
                            "validate": list(VAL_SEEDS)},
                  "accept_min": ACCEPT_MIN, "states": []})
    idxs = range(len(t0s)) if a.state is None else [a.state]
    for i in idxs:
        t0 = t0s[i]
        us = [union_for(t0.x, t0.v, s) for s in SEARCH_SEEDS]
        uv = [union_for(t0.x, t0.v, s) for s in VAL_SEEDS]
        cands = [("own", np.asarray(t0.limiters, float))]
        if (t0.x, t0.v) != (donor.x, donor.v):
            cands.append(("transplant", transplant(donor, t0.x, t0.v)))
        best_L, best_val, best_src = None, -1.0, None
        for src, L0 in cands:
            L, search_cl = refine_robust(us, L0, rng, iters=a.iters)
            val_cl, val_cap, val_vmin = stats(uv, L)
            if val_cl > best_val:
                best_L, best_val, best_src = L, val_cl, src
                best_cap, best_vmin, best_search = val_cap, val_vmin, search_cl
        accepted = bool(best_val >= ACCEPT_MIN)
        row = {"x": t0.x, "v": t0.v, "union_seed": int(VAL_SEEDS[0]),
               "src": t0.src, "candidate": best_src,
               "search_clean_frac": round(float(best_search), 3),
               "robust_clean_frac": round(float(best_val), 3),
               "robust_capture_frac": round(float(best_cap), 3),
               "v_soft_min_val": round(float(best_vmin), 3),
               "capture_grade_found": accepted,
               "refined_best": {"limiters": best_L.tolist(),
                                "v_soft": float(best_vmin), "worst": 1.0,
                                "p_feas": 1e-3} if accepted else None,
               "sigma_baselines": (sigma_baselines(uv, best_L, rng)
                                   if accepted else None)}
        bank["states"] = [s for s in bank["states"]
                          if not (s["x"] == t0.x and s["v"] == t0.v
                                  and s["src"] == t0.src)] + [row]
        print(f"[{i}] {t0.src}: cand={best_src} search={best_search:.2f} "
              f"VAL={best_val:.2f} cap={best_cap:.2f} vmin={best_vmin:.2f} "
              f"-> {'ACCEPT' if accepted else 'reject'}")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(bank, indent=1))
    acc = sum(1 for s in bank["states"] if s["capture_grade_found"])
    print(f"bank: {acc} accepted / {len(bank['states'])} states -> {out_p}")


if __name__ == "__main__":
    main()
