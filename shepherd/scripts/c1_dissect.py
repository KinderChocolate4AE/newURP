"""C-1 corridor dissection (③-lite; docs/25). Reusable — feeds the bank
builder parameterization now and the ③-full bank clustering later.

Given a stored winning trace (obs+acts), decompose the corridor into:
  * per-step feasible-set shrink (p_feas) vs cone-alignment (v_soft)
  * per-limiter accel in the attacker frame (radial toward att / tangential)
  * ROLE attribution by drop-one at the eligible step: who boxes (Δp_feas on
    removal) vs who shapes the residual sliver into the net cone (Δv_soft)
  * phase segmentation (compress -> brake-and-shape) from the radial sign flip
  * corral-winner comparison (symmetric press = jumps over the clean window)

Verdict for seed 1100 (2026-07-19, docs/09 (xxx)): 3 boxers + 1 shaper,
2-phase; corral never threads the v_soft>=theta AND p_feas>0 window.

torch-free. Usage:
  python -m shepherd.scripts.c1_dissect --cem results/c1_corridor/cem_warm/c1_cem.json \
      --seed 1100 --corral results/c1_corridor/c1_corral.json
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, make_corral_fn,
                                                make_finisher_fn)
from shepherd.game import viability as V


def _frame(o):
    o = np.asarray(o, float)
    lp = [o[9 * i:9 * i + 3] for i in range(4)]
    lv = [o[9 * i + 3:9 * i + 6] for i in range(4)]
    return lp, lv, o[36:45], o[45:48], o[48:51]      # lims, fin, p_att, v_att


def dissect(cem_json, seed, corral_json=None, cfg="configs/m3a_a3e_p1.yaml"):
    env_cfg, m3, theta = _load(cfg)
    pe = ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    d = json.load(open(cem_json))
    tr = next(r["best_trace"] for r in d["draws"]
              if r["reset_seed"] == seed and r.get("best_trace"))
    OBS = np.asarray(tr["obs"], float)
    ACT = np.asarray(tr["acts"], float)
    vs = np.asarray(tr["v_soft"])
    pf = np.asarray(tr["p_feas"])
    elig = [t for t in range(len(vs)) if vs[t] >= theta and pf[t] > 0]
    out = {"seed": seed, "theta": theta, "kill_radius": E.kill_radius,
           "cone_half_angle": E.cone_half_angle, "len": len(OBS),
           "eligible_steps": elig, "timeline": [], "phase": {}, "roles": {},
           "corral_cmp": None}

    # --- timeline: feasible-shrink vs cone-alignment -------------------------
    for t in range(len(OBS)):
        lp, lv, fin, pa, va = _frame(OBS[t])
        out["timeline"].append({
            "t": t, "v_soft": float(vs[t]), "p_feas": float(pf[t]),
            "n_feasible": int(round(pf[t] * E.n_samples)),
            "att_x": float(pa[0]), "att_speed": float(np.linalg.norm(va)),
            "dist": [float(np.linalg.norm(lp[i] - pa)) for i in range(4)]})

    # --- per-limiter radial/tangential accel (attacker frame) ----------------
    def decomp(t):
        lp, lv, fin, pa, va = _frame(OBS[t])
        rows = []
        for i in range(4):
            r = lp[i] - pa
            rn = r / (np.linalg.norm(r) + 1e-9)
            rad = float(ACT[t, i] @ rn)
            tan = float(np.linalg.norm(ACT[t, i] - rad * rn))
            rows.append({"lim": i, "radial": rad, "tangential": tan,
                         "mag": float(np.linalg.norm(ACT[t, i]))})
        return rows

    # phase segmentation: mean boxer radial sign per step (flip = compress->brake)
    radial_sign = []
    for t in range(len(ACT)):
        rows = decomp(t)
        radial_sign.append(float(np.mean([r["radial"] for r in rows])))
    flip = next((t for t in range(1, len(radial_sign))
                 if radial_sign[t - 1] > 0 and radial_sign[t] < 0), None)
    out["phase"] = {"radial_sign_per_step": [round(x, 1) for x in radial_sign],
                    "compress_to_brake_flip_step": flip,
                    "decomp_at_flip": decomp(flip) if flip is not None else None,
                    "decomp_pre_flip": decomp(flip - 1) if flip else None}

    # --- role attribution: drop-one at the eligible step ---------------------
    if elig:
        te = elig[0]
        lp, lv, fin, pa, va = _frame(OBS[te])
        kw = E._vshot_kwargs(pa, va, fin)
        sd = seed * 100003 + te
        union = V.build_reachable_union(pa, va, tau=E.tau_deploy,
                                        a_att_max=E.a_att_max, n=E.n_samples,
                                        n_segments=E.n_segments, seed=sd, **kw)
        full = V.eval_union_with_limiters(union, lp, E.kill_radius)
        roles = {"eligible_step": te, "all4": {
            "p_feas": float(full.p_feasible), "v_soft": float(full.v_shot_soft)}}
        per = []
        for i in range(4):
            others = [lp[j] for j in range(4) if j != i]
            r = V.eval_union_with_limiters(union, others, E.kill_radius)
            per.append({"drop": i,
                        "p_feas": float(r.p_feasible),
                        "d_p_feas": float(r.p_feasible - full.p_feasible),
                        "v_soft": float(r.v_shot_soft)})
        # boxer = large +Δp_feas on removal (compresses the reachable set);
        # shaper = tiny Δp_feas but removing it still drops v_soft (it aligns the
        # residual sliver into the net cone rather than doing bulk boxing).
        for x in per:
            v_drop = full.v_shot_soft - x["v_soft"]
            x["v_soft_drop_on_remove"] = float(v_drop)
            x["role"] = ("boxer" if x["d_p_feas"] > 0.02
                         else "shaper" if v_drop > 0.2
                         else "minor")
        roles["drop_one"] = per
        out["roles"] = roles

    # --- corral-winner comparison --------------------------------------------
    if corral_json:
        c = json.load(open(corral_json))
        best = max(c["top"], key=lambda t: t["full"]["summary"]["score_mean"])
        fin_fn = make_finisher_fn(theta, "point_at_attacker")
        rc = pe.rollout(make_corral_fn(best["params"]), fin_fn, seed, trace=True)
        cvs = np.asarray(rc["trace"]["v_soft"])
        cpf = np.asarray(rc["trace"]["p_feas"])
        celig = [t for t in range(len(cvs)) if cvs[t] >= theta and cpf[t] > 0]
        out["corral_cmp"] = {
            "cfg_idx": best["cfg_idx"], "pattern": best["params"]["pattern"],
            "eligible_steps": celig,
            "max_v_soft": float(cvs.max()),
            "p_feas_when_v_high": [round(float(cpf[t]), 4)
                                   for t in range(len(cvs)) if cvs[t] >= theta],
            "note": ("symmetric press: p_feas high while v_soft low, then jumps "
                     "to boxed (v_soft 1, p_feas 0) -- never threads clean window"
                     if not celig else "corral also reaches clean window")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cem", default="results/c1_corridor/cem_warm/c1_cem.json")
    ap.add_argument("--seed", type=int, default=1100)
    ap.add_argument("--corral", default="results/c1_corridor/c1_corral.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_dissect_seed.json")
    a = ap.parse_args()
    res = dissect(a.cem, a.seed, a.corral)
    import pathlib
    pathlib.Path(a.out.replace("seed", str(a.seed))).write_text(
        json.dumps(res, indent=1))
    # human summary
    r = res["roles"]
    print(f"seed {a.seed}: eligible={res['eligible_steps']} "
          f"compress->brake flip @ t={res['phase']['compress_to_brake_flip_step']}")
    if r:
        print(f" roles (drop-one @ t={r['eligible_step']}, all4 "
              f"p_feas={r['all4']['p_feas']:.4f} v_soft={r['all4']['v_soft']:.3f}):")
        for x in r["drop_one"]:
            print(f"  L{x['drop']}: Δp_feas={x['d_p_feas']:+.4f} "
                  f"v_soft_on_drop={x['v_soft']:.3f} -> {x['role'].upper()}")
    if res["corral_cmp"]:
        cc = res["corral_cmp"]
        print(f" corral cfg#{cc['cfg_idx']} {cc['pattern']}: eligible={cc['eligible_steps']} "
              f"(max v_soft={cc['max_v_soft']:.2f}) -> {cc['note']}")


if __name__ == "__main__":
    main()
