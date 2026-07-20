"""C-1 G3 deployment-aware corridor search (docs/09 (bbbb); external review
"G3 decision"). Extends the corridor CEM with a NET-LANE CLEARANCE term from
the grounded directional net reach ((aaaa)), searching for a compress->
release->fire->clear corridor that both reaches the fire-eligible shell AND
keeps friendly limiters out of the net's deployment lane.

Separated eligibility (review §5 -- existing capture predicate UNCHANGED):
  E_capture = 1[v_soft>=theta AND p_feas>0]            (existing; frozen)
  E_lane    = 1[m_clear>=0]                            (new safety)
  E_safe    = E_capture AND E_lane
where over the deployment window [t_f, t_f+n_dep]:
  m_clear = min_i,tau [ perp_to_axis(p_Li(tau)) - R_lane - r_body ]
with R_lane = the GROUNDED directional net reach (G2 default 2.24 m from
c1_net_silhouette; NOT the ad-hoc tube). Net axis/apex frozen at fire.

5-tier lexicographic verdict (review §10): 0 invalid / 1 capture-progress /
2 shell reached lane-unsafe (= seed 1100) / 3 lane-safe shell-not-reached /
4 safe-fire eligible / 5 deployment-safe autonomous capture. Constructive
positive = Tier>=4. Continuous M_capture / M_clear rank within tiers.

Envelope band (review §6): G2 grounded directional (primary, this default) /
G3 conservative = +body+buffer (soft/tag) / G1 optimistic early (tag; needs
human temporal grounding). Role-agnostic knot-CEM; warm-start from the E1
winner (kept as near-miss, review §9). torch-free (search = numpy+env).

Usage (server): python -m shepherd.scripts.c1_g3_deploy --stage search \
    --warm-cem results/c1_corridor/cem_warm/c1_cem.json --warm-seed 1100 \
    --draws 12 --knots 6 --pop 48 --iters 30 --out-dir results/c1_corridor/g3
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib

import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, _seq_lim,
                                                knots_to_seq, make_finisher_fn,
                                                make_lambda_brake_fn, _brake_fn,
                                                _zero_fn, A_MAX, N_LIM, S_V, S_P)

R_LANE_G2 = 2.24        # grounded directional net reach (max), docs/09 (aaaa)
R_BODY = 0.20           # limiter body/rotor clearance (PLACEHOLDER -- human-lane)
RNG_G3_BASE = 340_000_000
RNG_G3_STRIDE = 10_000


def g3_seed(reset_idx, restart):
    assert 0 <= restart < RNG_G3_STRIDE
    s = RNG_G3_BASE + reset_idx * RNG_G3_STRIDE + restart
    return s


def _perp_to_axis(p, apex, u):
    r = np.asarray(p, float) - apex
    ax = float(r @ u)
    perp = float(np.linalg.norm(r - ax * u))
    return ax, perp


def rollout_g3(pe: ProbeEnv, lim_fn, fin_fn, reset_seed, *,
               r_lane=R_LANE_G2, r_body=R_BODY, trace=False):
    """Corridor rollout + net-lane clearance over the deployment window.
    Verdict tiers 0-5. Net axis/apex frozen at the fire step."""
    ad = pe.ad
    E = ad.env
    dt = 0.05
    n_dep = int(round(E.tau_deploy / dt))
    th = pe.theta
    obs_d, _ = ad.reset(seed=int(reset_seed))
    obs = obs_d[ad.limiter_ids[0]]
    vs, pf, lim_hist, flags = [], [], [], {}
    fire_step = None
    fin_apex = fin_axis = axial_len = None
    steps = 0
    pen_at = None
    captured = clean = reset_elig = False
    reset_elig = bool(obs[-3] >= th and obs[-1] > 0.0)
    while True:
        v_soft, p_feas = float(obs[-3]), float(obs[-1])
        vs.append(v_soft); pf.append(p_feas)
        lim_hist.append(np.stack([obs[9 * i:9 * i + 3] for i in range(N_LIM)]))
        lim = lim_fn(obs, flags)
        live = {lid: np.asarray(lim[i], np.float32)
                for i, lid in enumerate(ad.limiter_ids)}
        fa = fin_fn(obs, flags)
        live[ad.finisher_id] = np.asarray(fa, np.float32)
        # detect fire (finisher live action fire bit) -> freeze net geometry
        if fire_step is None and len(fa) >= 4 and fa[3] > 0.5:
            fire_step = steps
            o = np.asarray(obs, float)
            fin_apex = o[36:39]
            fin_axis = o[42:45]; fin_axis = fin_axis / (np.linalg.norm(fin_axis) + 1e-12)
            axial_len = float((o[45:48] - fin_apex) @ fin_axis)
        r = ad.step(live)
        if pen_at is None and bool(r.flags.get("penetrated")):
            pen_at = steps
        obs = r.obs[ad.limiter_ids[0]]; flags = r.flags
        steps += 1
        if r.done or (fire_step is not None and steps > fire_step + n_dep + 1):
            captured = bool(r.flags.get("captured"))
            clean = bool(any(c.get("clean") for c in r.flags.get("fire_chains", [])))
            break
    # capture eligibility (existing predicate)
    vs_a, pf_a = np.asarray(vs), np.asarray(pf)
    el = np.isfinite(vs_a) & np.isfinite(pf_a) & (pf_a > 0) & (vs_a >= th)
    first_el = int(np.argmax(el)) if el.any() else None
    shell_reached = bool(el.any() and not reset_elig
                         and (pen_at is None or first_el < pen_at))
    if el.any():
        M_capture = float(np.max(np.minimum((vs_a[el] - th) / S_V, pf_a[el] / S_P)))
    else:
        M_capture = float("-inf")
    # lane clearance over deployment window (needs a fire + frozen net geom)
    m_clear = float("inf"); m_clear_defined = False
    if fire_step is not None and axial_len is not None:
        w = range(fire_step, min(fire_step + n_dep + 1, len(lim_hist)))
        cl = []
        for t in w:
            for i in range(N_LIM):
                ax, perp = _perp_to_axis(lim_hist[t][i], fin_apex, fin_axis)
                if 0.0 <= ax <= axial_len:
                    cl.append(perp - r_lane - r_body)
        if cl:
            m_clear = float(min(cl)); m_clear_defined = True
    E_capture = bool(shell_reached)
    E_lane = bool(m_clear_defined and m_clear >= 0.0)
    E_safe = bool(E_capture and E_lane)
    arrival = bool(captured and clean and not reset_elig)
    # tier
    if pen_at is not None and not shell_reached and not E_capture:
        tier = 0 if not el.any() else 1
    else:
        tier = 1
    if E_capture and not E_lane:
        tier = 2
    if E_lane and not E_capture:
        tier = 3
    if E_safe:
        tier = 4
    if E_safe and arrival:
        tier = 5
    rec = {"reset_seed": int(reset_seed), "len": steps, "fire_step": fire_step,
           "penetrated_at": pen_at, "E_capture": E_capture, "E_lane": E_lane,
           "E_safe": E_safe, "shell_reached": shell_reached,
           "arrival_capture": arrival, "captured": captured,
           "M_capture": M_capture,
           "m_clear": (m_clear if m_clear_defined else None),
           "tier": tier, "max_v_soft": float(vs_a[np.isfinite(vs_a)].max()
                                             if np.isfinite(vs_a).any() else 0.0)}
    if trace:
        rec["trace"] = {"v_soft": [float(x) for x in vs],
                        "p_feas": [float(x) for x in pf],
                        "lim": [h.tolist() for h in lim_hist]}
    return rec


def score_g3(rec):
    """Lexicographic key: tier, then M_clear (safe-fire depth) once eligible,
    then M_capture, then later penetration. Higher = better."""
    mc = rec["m_clear"]
    mc = mc if (mc is not None and np.isfinite(mc)) else -10.0
    mcap = rec["M_capture"] if np.isfinite(rec["M_capture"]) else -1.0
    pen = rec["penetrated_at"] if rec["penetrated_at"] is not None else rec["len"]
    return (rec["tier"], mcap + min(mc, 0.0), mcap, float(pen))


_TIER = 1e6


def score_g3_scalar(rec):
    v = score_g3(rec)
    s = 0.0
    for x in v:
        s = s * _TIER + float(np.clip(x, -_TIER / 2 + 1, _TIER / 2 - 1))
    return s


def cem_g3(pe, fin, reset_seed, rng, *, knots, t_open, pop, iters, elite_frac,
           sigma0, r_lane, r_body, warm=None):
    from shepherd.scripts.c1_corridor_probe import _fit_knots
    dim = (knots, N_LIM, 3)
    mu = np.zeros(dim) if warm is None else _fit_knots(knots_to_seq(warm, t_open)
                                                       if np.asarray(warm).ndim == 3
                                                       else warm, knots)
    sig = np.full(dim, float(sigma0))
    n_el = max(2, int(round(pop * elite_frac)))
    best = {"vec": None, "rec": None, "knots": None, "stop": "budget"}
    hist = []
    for it in range(iters):
        cands = np.clip(mu + sig * rng.standard_normal((pop,) + dim), -A_MAX, A_MAX)
        vecs, recs = [], []
        for c in range(pop):
            rec = rollout_g3(pe, _seq_lim(knots_to_seq(cands[c], t_open)), fin,
                             reset_seed, r_lane=r_lane, r_body=r_body)
            recs.append(rec); v = score_g3(rec); vecs.append(v)
            if best["vec"] is None or v > best["vec"]:
                best = {"vec": v, "rec": rec, "knots": cands[c].copy(),
                        "stop": best["stop"]}
        el = sorted(range(pop), key=lambda c: vecs[c])[-n_el:]
        mu = cands[el].mean(0); sig = cands[el].std(0) * 1.05 + 0.3
        hist.append({"iter": it, "best_tier": best["rec"]["tier"],
                     "n_tier4plus": int(sum(r["tier"] >= 4 for r in recs)),
                     "n_shell": int(sum(r["E_capture"] for r in recs))})
        if best["rec"]["tier"] >= 4:                       # safe-fire found
            best["stop"] = "safe_fire" if best["rec"]["tier"] == 4 else "safe_capture"
            break
    bk = best["knots"]
    return {"best_tier": best["rec"]["tier"] if best["rec"] else 0,
            "best_record": best["rec"], "early_stop": best["stop"],
            "best_knots": bk.tolist() if bk is not None else None,
            "best_acts": (knots_to_seq(bk, t_open).tolist() if bk is not None else None),
            "curve": hist}


def stage_search(a, out_dir):
    env_cfg, m3, theta = _load(a.config)
    pe = ProbeEnv(env_cfg, m3)
    fin = make_finisher_fn(theta)
    warm = None
    if a.warm_cem:
        w = json.loads(pathlib.Path(a.warm_cem).read_text())
        rec = next((x for x in w["draws"] if x["reset_seed"] == a.warm_seed
                    and x.get("best_knots")), None)
        if rec:
            warm = np.asarray(rec["best_knots"], float)
            print(f"[g3] warm-start from E1 winner seed {a.warm_seed} "
                  f"(kept as near-miss)", flush=True)
    results = []
    for j in range(a.draws):
        s = a.seed0 + j
        rng = np.random.default_rng(g3_seed(j, 0))
        res = cem_g3(pe, fin, s, rng, knots=a.knots, t_open=a.t_open, pop=a.pop,
                     iters=a.iters, elite_frac=a.elite_frac, sigma0=a.sigma0,
                     r_lane=a.r_lane, r_body=a.r_body, warm=warm)
        res["reset_seed"] = s
        b = res["best_record"] or {}
        results.append(res)
        print(f"[g3] seed {s}: stop={res['early_stop']} tier={b.get('tier')} "
              f"E_cap={b.get('E_capture')} E_lane={b.get('E_lane')} "
              f"m_clear={b.get('m_clear')} M_cap={b.get('M_capture'):.2f}", flush=True)
    out = {"meta": {"stage": "search", "r_lane": a.r_lane, "r_body": a.r_body,
                    "envelope": "G2_grounded_directional", "knots": a.knots,
                    "pop": a.pop, "iters": a.iters, "t_open": a.t_open,
                    "warm": a.warm_cem, "rng_base": RNG_G3_BASE,
                    "seeds": [a.seed0, a.seed0 + a.draws - 1],
                    "tiers": "0 invalid/1 progress/2 shell-unsafe/3 lane-safe-noshell/"
                             "4 safe-fire/5 safe-capture",
                    "caveat": "r_body PLACEHOLDER (human-lane); r_lane G2 grounded "
                              "directional max; temporal/tether unresolved"},
           "draws": results,
           "n_tier4plus": int(sum(1 for r in results
                                  if r["best_record"] and r["best_record"]["tier"] >= 4)),
           "best_tier": max((r["best_record"]["tier"] for r in results
                             if r["best_record"]), default=0)}
    p = out_dir / "c1_g3_search.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p}  best_tier={out['best_tier']}  "
          f"n_tier4plus={out['n_tier4plus']}", flush=True)


def stage_baseline(a, out_dir):
    """Verify the E1 winner lands at Tier 2 (shell reached, lane unsafe) under
    the G3 evaluator -- a wiring sanity check + the lexicographic anchor."""
    env_cfg, m3, theta = _load(a.config)
    pe = ProbeEnv(env_cfg, m3); fin = make_finisher_fn(theta)
    w = json.loads(pathlib.Path(a.warm_cem).read_text())
    rec = next(x for x in w["draws"] if x["reset_seed"] == a.warm_seed and x.get("best_acts"))
    r = rollout_g3(pe, _seq_lim(np.asarray(rec["best_acts"], float)), fin,
                   a.warm_seed, r_lane=a.r_lane, r_body=a.r_body)
    print(f"[g3-baseline] E1 winner seed {a.warm_seed}: tier={r['tier']} "
          f"E_cap={r['E_capture']} E_lane={r['E_lane']} m_clear={r['m_clear']} "
          f"(expect tier 2: shell reached, lane unsafe)")
    (out_dir).mkdir(parents=True, exist_ok=True)
    (out_dir / "c1_g3_baseline.json").write_text(json.dumps(r, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="search", choices=("search", "baseline"))
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--out-dir", default="results/c1_corridor/g3")
    ap.add_argument("--warm-cem", default="results/c1_corridor/cem_warm/c1_cem.json")
    ap.add_argument("--warm-seed", type=int, default=1100)
    ap.add_argument("--seed0", type=int, default=1100)
    ap.add_argument("--draws", type=int, default=12)
    ap.add_argument("--knots", type=int, default=6)
    ap.add_argument("--pop", type=int, default=48)
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--elite-frac", type=float, default=0.25)
    ap.add_argument("--sigma0", type=float, default=10.0)
    ap.add_argument("--t-open", type=int, default=32)
    ap.add_argument("--r-lane", type=float, default=R_LANE_G2)
    ap.add_argument("--r-body", type=float, default=R_BODY)
    a = ap.parse_args()
    out = pathlib.Path(a.out_dir)
    (stage_search if a.stage == "search" else stage_baseline)(a, out)


if __name__ == "__main__":
    main()
