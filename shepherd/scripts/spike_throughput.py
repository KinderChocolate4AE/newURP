"""Phase 2A' -- v_shot throughput spike (docs/09 SS5, promoted 2026-07-03).

Measures, WITHOUT touching any frozen file (env.py / 03 / m2_l2_train.yaml /
exchange.py all diff 0):

  profile  : full env.step() timing + per-component decomposition of the
             viability hot path (union build B, per-layout eval E, post-move
             obs v_shot rebuild V2, wasted accels draw) + state-bank dump.
  sweep    : lever (1) n_samples sweep -- CRN-paired accuracy vs the n=2000
             reference at identical (state, step_seed): |dv_soft|, headline
             delta error, fire-gate (soft>=theta) / worst==1 agreement, coma_D
             sign agreement, per-n component timings.
  batched  : lever (5) shared-distance eval across the 6 per-step layouts
             (EXACT refactor candidate; measured read-only here).
  parallel : lever (3) process-parallel env scaling on this box (nproc-bound).
  report   : aggregate JSONs -> results/spike_throughput/spike_results.md with
             lever (2) coma_D cadence PROJECTIONS T(k,n) from measured B/E/V2
             and lab-server wallclock projections for 1e6 steps.

Accuracy caveat (recorded in the report): the state bank is the visitation
distribution of a no-fire random policy on the training corridor -- near-gate
(v_soft ~ theta_fire) density depends on that distribution; max-error rows
bound the gate-flip risk band.

Usage (each phase fits a sandbox bash timeout):
  python -m shepherd.scripts.spike_throughput --phase profile
  python -m shepherd.scripts.spike_throughput --phase sweep --n-list 2000,1000
  python -m shepherd.scripts.spike_throughput --phase sweep --n-list 500,250,125
  python -m shepherd.scripts.spike_throughput --phase batched
  python -m shepherd.scripts.spike_throughput --phase parallel
  python -m shepherd.scripts.spike_throughput --phase report
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np
import yaml

from shepherd.game import viability as V
from shepherd.train.make_env import make_train_env, pad_env_actions, live_action_dim

OUT_DIR = os.path.join("results", "spike_throughput")
CFG_PATH = os.path.join("configs", "m2_l2_train.yaml")
REF_N = 2000
THETA_FIRE = 0.9
N_LIMITERS = 4
BANK_STRIDE = 2          # bank subsample stride (random no-fire episode ~23 steps)
SWEEP_SEEDS = 3          # step_seed variants per state


def _load_cfg():
    with open(CFG_PATH) as f:
        return yaml.safe_load(f)


def _build_env(cfg):
    env, scn, lay = make_train_env(cfg)
    return env, scn, lay


def _random_live(env, rng, fire=False):
    live = {}
    for a in env.agents:
        d = live_action_dim(a)
        v = rng.uniform(-1.0, 1.0, d).astype(np.float32)
        if a.startswith(("limiter", "adversary")):
            v *= 30.0
        if a == "finisher_0":
            v[-1] = 1.0 if fire else 0.0
        live[a] = v
    return live


def _vshot_kwargs(env, fin_s9):
    # mirrors env._vshot_kwargs for the se3_cone judge (the training default)
    return dict(judge="se3_cone", net_apex=np.asarray(fin_s9, float)[0:3],
                n_F=np.asarray(fin_s9, float)[6:9], theta_net=env.cone_half_angle,
                range_min=env.cone_range_min, range_max=env.cone_range_max)


def phase_profile():
    """Full-step timing + component decomposition + state-bank dump."""
    cfg = _load_cfg()
    env, scn, lay = _build_env(cfg)
    obs, _ = env.reset(seed=0)
    rng = np.random.default_rng(0)

    bank, step_ts = [], []
    while env.agents:
        lims, fin, att = env._states()          # pre-move state, as step() sees it
        step_seed = env._seed * 100003 + (env._step_i + 1)
        bank.append(dict(
            step=env._step_i + 1, step_seed=step_seed,
            p_att=env._p(att).tolist(), v_att=env._v(att).tolist(),
            lim_pos=[env._p(s).tolist() for s in lims],
            fin_s9=np.asarray(fin, float).tolist()))
        t0 = time.perf_counter()
        obs, r, te, tr, inf = env.step(pad_env_actions(_random_live(env, rng)))
        step_ts.append(time.perf_counter() - t0)

    # --- component timings on a subsample of the bank, at the reference n ----
    sub = bank[::BANK_STRIDE]
    comp = dict(build=[], eval=[], vres2=[], draw=[])
    p0 = [list(map(float, p)) for p in lay.limiter_p0]
    for st in sub:
        p_att = np.asarray(st["p_att"]); v_att = np.asarray(st["v_att"])
        lim_pos = [np.asarray(p) for p in st["lim_pos"]]
        kw = _vshot_kwargs(env, st["fin_s9"])
        ss = st["step_seed"]

        t0 = time.perf_counter()
        V.reachable_accels(env.a_att_max, REF_N, ss)      # drawn-but-unused on union path
        comp["draw"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        union = V.build_reachable_union(p_att, v_att, tau=env.tau_deploy,
                                        a_att_max=env.a_att_max, n=REF_N,
                                        n_segments=env.n_segments, seed=ss, **kw)
        comp["build"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        V.eval_union_with_limiters(union, lim_pos, env.kill_radius)
        comp["eval"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        V.v_shot(p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
                 limiters=lim_pos, kill_radius=env.kill_radius, n=REF_N,
                 seed=ss, n_segments=env.n_segments, **kw)
        comp["vres2"].append(time.perf_counter() - t0)

    out = dict(
        n_steps=len(step_ts),
        step_ms=dict(mean=1e3 * float(np.mean(step_ts)),
                     median=1e3 * float(np.median(step_ts)),
                     p90=1e3 * float(np.percentile(step_ts, 90))),
        comp_ms={k: 1e3 * float(np.mean(v)) for k, v in comp.items()},
        n_bank=len(bank), n_sub=len(sub),
        note="per step: draw + build B + 6x eval E (vfull,vbase,4x coma) + vres2 (B+inline E)")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "state_bank.json"), "w") as f:
        json.dump(dict(bank=bank, limiter_p0=p0), f)
    with open(os.path.join(OUT_DIR, "profile.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


def phase_sweep(n_list):
    """CRN-paired accuracy + timing per n, against the n=2000 reference."""
    cfg = _load_cfg()
    env, scn, lay = _build_env(cfg)
    data = json.load(open(os.path.join(OUT_DIR, "state_bank.json")))
    sub = data["bank"][::BANK_STRIDE]
    p0 = [np.asarray(p) for p in data["limiter_p0"]]

    def eval_state(st, n, seed):
        p_att = np.asarray(st["p_att"]); v_att = np.asarray(st["v_att"])
        lim_pos = [np.asarray(p) for p in st["lim_pos"]]
        kw = _vshot_kwargs(env, st["fin_s9"])
        t0 = time.perf_counter()
        union = V.build_reachable_union(p_att, v_att, tau=env.tau_deploy,
                                        a_att_max=env.a_att_max, n=n,
                                        n_segments=env.n_segments, seed=seed, **kw)
        t_build = time.perf_counter() - t0
        t0 = time.perf_counter()
        vfull = V.eval_union_with_limiters(union, lim_pos, env.kill_radius)
        t_eval = time.perf_counter() - t0
        vbase = V.eval_union_with_limiters(union, p0, env.kill_radius)
        coma = []
        for i in range(N_LIMITERS):
            cf = list(lim_pos); cf[i] = p0[i]
            vcf = V.eval_union_with_limiters(union, cf, env.kill_radius)
            coma.append(vfull.v_shot_soft - vcf.v_shot_soft)
        return dict(soft=vfull.v_shot_soft, worst=vfull.v_shot_worst,
                    base=vbase.v_shot_soft, headline=vfull.v_shot_soft - vbase.v_shot_soft,
                    coma=coma, boxed=bool(vfull.boxed_in),
                    t_build=t_build, t_eval=t_eval)

    rows = []
    for n in n_list:
        for st in sub:
            for ds in range(SWEEP_SEEDS):
                seed = st["step_seed"] + ds * 7919
                ref = eval_state(st, REF_N, seed) if n != REF_N else None
                cur = eval_state(st, n, seed)
                if ref is None:
                    ref = cur
                rows.append(dict(
                    n=n, step=st["step"], dseed=ds,
                    soft=cur["soft"], ref_soft=ref["soft"],
                    err_soft=abs(cur["soft"] - ref["soft"]),
                    err_headline=abs(cur["headline"] - ref["headline"]),
                    gate_agree=int((cur["soft"] >= THETA_FIRE) == (ref["soft"] >= THETA_FIRE)),
                    worst_agree=int(cur["worst"] == ref["worst"]),
                    coma_sign_agree=float(np.mean([
                        int(np.sign(a) == np.sign(b)) if (abs(a) > 1e-9 or abs(b) > 1e-9) else 1
                        for a, b in zip(cur["coma"], ref["coma"])])),
                    coma_err=float(np.max([abs(a - b) for a, b in zip(cur["coma"], ref["coma"])])),
                    t_build=cur["t_build"], t_eval=cur["t_eval"]))
        print(f"n={n} done ({len(sub)} states x {SWEEP_SEEDS} seeds)")

    path = os.path.join(OUT_DIR, "sweep_rows.jsonl")
    with open(path, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print("appended", len(rows), "rows ->", path)


def phase_batched():
    """Lever (5): shared-distance batched eval across the 6 layouts.

    The 6 per-step layouts (vfull, vbase, 4x coma counterfactual) draw from only
    8 UNIQUE limiter positions (4 current + 4 hold_position baseline). Computing
    the per-witness hit mask against the 8 unique spheres ONCE and composing each
    layout as a boolean any() over its 4 columns is an EXACT refactor (identical
    masks, zero accuracy loss). Measured here read-only via ReachableUnion's
    public fields; adopting it needs an additive viability.py helper + an env.py
    call-site change (freeze decision -> docs/09 SS8).
    """
    cfg = _load_cfg()
    env, scn, lay = _build_env(cfg)
    data = json.load(open(os.path.join(OUT_DIR, "state_bank.json")))
    sub = data["bank"][::BANK_STRIDE]
    p0 = [np.asarray(p) for p in data["limiter_p0"]]
    kr = env.kill_radius

    t_sep, t_bat, mismatches = [], [], 0
    for st in sub:
        p_att = np.asarray(st["p_att"]); v_att = np.asarray(st["v_att"])
        lim_pos = [np.asarray(p) for p in st["lim_pos"]]
        kw = _vshot_kwargs(env, st["fin_s9"])
        union = V.build_reachable_union(p_att, v_att, tau=env.tau_deploy,
                                        a_att_max=env.a_att_max, n=REF_N,
                                        n_segments=env.n_segments,
                                        seed=st["step_seed"], **kw)
        layouts = [lim_pos, list(p0)]
        for i in range(N_LIMITERS):
            cf = list(lim_pos); cf[i] = p0[i]
            layouts.append(cf)

        t0 = time.perf_counter()
        sep = [V.eval_union_with_limiters(union, L, kr) for L in layouts]
        t_sep.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        uniq = np.asarray(list(lim_pos) + list(p0), float)      # (8,3) unique spheres
        hits = []                                                # per-witness x 8
        for pb in union.path_blocks:
            d = np.linalg.norm(pb[:, :, None, :] - uniq[None, None, :, :], axis=3)
            hits.append((d <= kr).any(axis=1))                   # (n_b, 8)
        hit = np.concatenate(hits, axis=0)                       # (M, 8)
        cols = [list(range(0, 4)), list(range(4, 8))]
        for i in range(N_LIMITERS):
            c = list(range(0, 4)); c[i] = 4 + i
            cols.append(c)
        bat = []
        for c in cols:
            feasible = ~hit[:, c].any(axis=1) & union.turn_feasible
            bat.append(V._assemble(feasible, union.caught, union.n_total,
                                   union.judge, union.seed))
        t_bat.append(time.perf_counter() - t0)

        for a, b in zip(sep, bat):
            if (a.v_shot_soft != b.v_shot_soft or a.v_shot_worst != b.v_shot_worst
                    or a.n_feasible != b.n_feasible or a.boxed_in != b.boxed_in):
                mismatches += 1
    out = dict(n_states=len(sub), mismatches=mismatches,
               sep_6eval_ms=1e3 * float(np.mean(t_sep)),
               batched_ms=1e3 * float(np.mean(t_bat)),
               speedup=float(np.mean(t_sep) / np.mean(t_bat)))
    with open(os.path.join(OUT_DIR, "batched.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


def phase_gate():
    """Near-gate accuracy: SYNTHESIZED states with ref v_soft in (0.5, 1.0).

    The random-policy bank never visits v_soft near theta_fire=0.9 (range ~[0,0.22]),
    so its gate-agreement stat is vacuous. Here we manufacture engagement states the
    way shaping is MEANT to produce them: attacker ball ahead of the cone apex with a
    tight limiter ring carving the escape lobes, grid-searched until the n=2000
    reference v_soft lands in bins across (0.5, 1.0). Then the CRN-paired n-sweep is
    repeated on those states -> gate flips measured WHERE THE GATE LIVES.
    """
    cfg = _load_cfg()
    env, scn, lay = _build_env(cfg)
    data = json.load(open(os.path.join(OUT_DIR, "state_bank.json")))
    fin_s9 = data["bank"][0]["fin_s9"]                      # apex + axis from episode
    apex = np.asarray(fin_s9, float)[0:3]
    axis = np.asarray(fin_s9, float)[6:9]
    axis = axis / np.linalg.norm(axis)
    kw = _vshot_kwargs(env, fin_s9)
    kr = env.kill_radius

    def mk_state(d, ring_r, ring_dx, v_along):
        p_att = apex + axis * d
        v_att = axis * v_along
        c_ball = p_att + v_att * env.tau_deploy             # reachable-ball center
        u = np.array([0.0, 1.0, 0.0]); w = np.array([0.0, 0.0, 1.0])
        ring = [c_ball + ring_dx * axis + ring_r * (np.cos(a) * u + np.sin(a) * w)
                for a in (0.0, np.pi / 2, np.pi, 3 * np.pi / 2)]
        return p_att, v_att, [np.asarray(p) for p in ring]

    # grid-search engagement states whose REF v_soft falls in the target bins
    bins = [(0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.0)]
    found = {b: [] for b in bins}
    grid_i = 0
    for d in (6.0, 9.0, 12.0, 16.0, 20.0):
        for ring_r in (2.2, 2.6, 3.0, 3.6):
            for ring_dx in (-1.0, 0.0, 1.5):
                for v_along in (-10.0, -20.0):
                    grid_i += 1
                    p_att, v_att, ring = mk_state(d, ring_r, ring_dx, v_along)
                    union = V.build_reachable_union(
                        p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
                        n=REF_N, n_segments=env.n_segments, seed=1000 + grid_i, **kw)
                    r = V.eval_union_with_limiters(union, ring, kr)
                    if r.boxed_in:
                        continue
                    for b in bins:
                        if b[0] <= r.v_shot_soft < b[1] and len(found[b]) < 3:
                            found[b].append(dict(d=d, ring_r=ring_r, ring_dx=ring_dx,
                                                 v_along=v_along, seed=1000 + grid_i,
                                                 ref_soft=r.v_shot_soft))
    states = [s for b in bins for s in found[b]]
    rows = []
    for s in states:
        p_att, v_att, ring = mk_state(s["d"], s["ring_r"], s["ring_dx"], s["v_along"])
        for n in (1000, 500, 250):
            for ds in range(SWEEP_SEEDS):
                seed = s["seed"] + ds * 7919
                ur = V.build_reachable_union(p_att, v_att, tau=env.tau_deploy,
                                             a_att_max=env.a_att_max, n=REF_N,
                                             n_segments=env.n_segments, seed=seed, **kw)
                rr = V.eval_union_with_limiters(ur, ring, kr)
                uc = V.build_reachable_union(p_att, v_att, tau=env.tau_deploy,
                                             a_att_max=env.a_att_max, n=n,
                                             n_segments=env.n_segments, seed=seed, **kw)
                rc = V.eval_union_with_limiters(uc, ring, kr)
                rows.append(dict(
                    n=n, ref_soft=rr.v_shot_soft, soft=rc.v_shot_soft,
                    err=abs(rc.v_shot_soft - rr.v_shot_soft),
                    gate_agree=int((rc.v_shot_soft >= THETA_FIRE) == (rr.v_shot_soft >= THETA_FIRE)),
                    worst_agree=int(rc.v_shot_worst == rr.v_shot_worst)))
    out = dict(n_states=len(states),
               state_softs=[round(s["ref_soft"], 3) for s in states],
               per_n={str(n): dict(
                   err_mean=float(np.mean([r["err"] for r in rows if r["n"] == n])),
                   err_max=float(np.max([r["err"] for r in rows if r["n"] == n])),
                   gate_agree=float(np.mean([r["gate_agree"] for r in rows if r["n"] == n])),
                   worst_agree=float(np.mean([r["worst_agree"] for r in rows if r["n"] == n])))
                   for n in (1000, 500, 250)})
    with open(os.path.join(OUT_DIR, "gate.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


def _worker(args):
    seed, n_steps = args
    cfg = _load_cfg()
    env, scn, lay = _build_env(cfg)
    env.reset(seed=seed)
    rng = np.random.default_rng(seed)
    t0 = time.perf_counter()
    k = 0
    while k < n_steps:
        if not env.agents:
            env.reset(seed=seed + k + 1)
        env.step(pad_env_actions(_random_live(env, rng)))
        k += 1
    return time.perf_counter() - t0


def phase_parallel():
    import multiprocessing as mp
    n_steps = 20
    t_serial = _worker((0, n_steps)) + _worker((1, n_steps))
    with mp.get_context("spawn").Pool(2) as pool:
        t0 = time.perf_counter()
        pool.map(_worker, [(0, n_steps), (1, n_steps)])
        t_par = time.perf_counter() - t0
    eff = t_serial / (2.0 * t_par)
    out = dict(nproc=os.cpu_count(), n_steps_each=n_steps,
               serial_s=t_serial, parallel_wall_s=t_par, efficiency_2way=eff)
    with open(os.path.join(OUT_DIR, "parallel.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


def phase_report():
    prof = json.load(open(os.path.join(OUT_DIR, "profile.json")))
    par = json.load(open(os.path.join(OUT_DIR, "parallel.json")))
    bat_path = os.path.join(OUT_DIR, "batched.json")
    bat = json.load(open(bat_path)) if os.path.exists(bat_path) else None
    gate_path = os.path.join(OUT_DIR, "gate.json")
    gate = json.load(open(gate_path)) if os.path.exists(gate_path) else None
    rows = [json.loads(l) for l in open(os.path.join(OUT_DIR, "sweep_rows.jsonl"))]
    ns = sorted({r["n"] for r in rows}, reverse=True)

    def agg(n):
        rs = [r for r in rows if r["n"] == n]
        B = 1e3 * float(np.mean([r["t_build"] for r in rs]))
        E = 1e3 * float(np.mean([r["t_eval"] for r in rs]))
        return dict(
            n=n, B_ms=B, E_ms=E,
            err_soft_mean=float(np.mean([r["err_soft"] for r in rs])),
            err_soft_max=float(np.max([r["err_soft"] for r in rs])),
            err_headline_max=float(np.max([r["err_headline"] for r in rs])),
            gate_agree=float(np.mean([r["gate_agree"] for r in rs])),
            worst_agree=float(np.mean([r["worst_agree"] for r in rs])),
            coma_sign=float(np.mean([r["coma_sign_agree"] for r in rs])),
            coma_err_max=float(np.max([r["coma_err"] for r in rs])))

    aggs = [agg(n) for n in ns]
    step_ms = prof["step_ms"]["mean"]
    fixed = step_ms - (prof["comp_ms"]["draw"] + prof["comp_ms"]["build"] * 2
                       + prof["comp_ms"]["eval"] * 6)  # vres2 ~= B + inline E

    E_ref = next(x for x in aggs if x["n"] == REF_N)["E_ms"] if any(
        x["n"] == REF_N for x in aggs) else None

    def T(n, k, obs_lite=False, batched=False):
        a = next(x for x in aggs if x["n"] == n)
        B, E = a["B_ms"], a["E_ms"]
        vres2 = (0.0 if obs_lite else B + E)
        if batched and bat and E_ref:
            evals = bat["batched_ms"] * (E / E_ref)   # batched cost ~ scales like E
        else:
            evals = (2 + N_LIMITERS / k) * E
        return max(fixed, 0.0) + B + evals + vres2

    lines = ["# Phase 2A' -- v_shot throughput spike results", "",
             f"baseline env.step (n=2000, k=1): mean {step_ms:.1f} ms "
             f"(median {prof['step_ms']['median']:.1f}, p90 {prof['step_ms']['p90']:.1f}); "
             f"fixed overhead (non-viability) ~{max(fixed,0):.1f} ms", "",
             "## lever 1 -- n_samples sweep (CRN-paired vs n=2000, same state+seed)", "",
             "| n | B ms | E ms | err_soft mean | err_soft max | headline err max | "
             "gate agree | worst agree | coma sign | coma err max |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for a in aggs:
        lines.append("| {n} | {B_ms:.1f} | {E_ms:.1f} | {err_soft_mean:.4f} | {err_soft_max:.4f} "
                     "| {err_headline_max:.4f} | {gate_agree:.3f} | {worst_agree:.3f} "
                     "| {coma_sign:.3f} | {coma_err_max:.4f} |".format(**a))
    lines += ["", "## lever 2 -- coma_D cadence projection T(n, k) [ms/step, single env]", "",
              "| n | k=1 | k=2 | k=4 | k=8 | k=4 + obs-lite |", "|---|---|---|---|---|---|"]
    for a in aggs:
        n = a["n"]
        lines.append(f"| {n} | " + " | ".join(f"{T(n,k):.1f}" for k in (1, 2, 4, 8))
                     + f" | {T(n,4,obs_lite=True):.1f} |")
    if gate:
        lines += ["", "## lever 1b -- NEAR-GATE accuracy (synthesized engaged states)", "",
                  f"{gate['n_states']} states with ref v_soft {gate['state_softs']} "
                  "(limiter ring carving escape lobes -- where shaping puts the system):", "",
                  "| n | err mean | err max | gate agree | worst agree |", "|---|---|---|---|---|"]
        for n, g in gate["per_n"].items():
            lines.append(f"| {n} | {g['err_mean']:.4f} | {g['err_max']:.4f} "
                         f"| {g['gate_agree']:.3f} | {g['worst_agree']:.3f} |")
        lines += ["", "READ: on ENGAGED states the n-cut error is ~5x the bank-state error",
                  "(n=500 err_max 0.19 > zero-waste band width 0.15; n=1000 err_max ~0.09).",
                  "n_samples reduction is NOT safe near the fire gate -> prefer the EXACT",
                  "levers (batched eval, obs-lite) and keep n=2000 for reward/gate paths;",
                  "n-cuts only for debug loops. Speed knee is ~n=500 anyway (extreme blocks",
                  "dominate E below that)."]
    if bat:
        lines += ["", "## lever 5 -- shared-distance batched eval (EXACT, needs env.py call-site)", "",
                  f"6x separate eval {bat['sep_6eval_ms']:.1f} ms -> batched "
                  f"{bat['batched_ms']:.1f} ms ({bat['speedup']:.1f}x), "
                  f"mismatches {bat['mismatches']}/{bat['n_states']} states "
                  "(0 = bit-identical VShotResults)."]
    lines += ["", "## lever 3 -- parallel envs", "",
              f"sandbox nproc={par['nproc']}: 2-way efficiency {par['efficiency_2way']:.2f} "
              f"(serial {par['serial_s']:.1f}s vs wall {par['parallel_wall_s']:.1f}s)", "",
              "| recipe | ms/step | steps/s 1 env | 1e6 steps, W workers (eff 0.85) |",
              "|---|---|---|---|"]
    recipes = [(2000, 1, False, False, "baseline"),
               (2000, 1, False, True, "n2000 batched (exact)"),
               (2000, 1, True, True, "n2000 batched obs-lite"),
               (1000, 4, False, False, "n1000 k4"),
               (500, 4, False, False, "n500 k4"),
               (500, 4, True, False, "n500 k4 obs-lite"),
               (500, 1, True, True, "n500 batched obs-lite"),
               (250, 4, True, False, "n250 k4 obs-lite")]
    for (n, k, ol, bt, tag) in recipes:
        if not any(a["n"] == n for a in aggs) or (bt and not bat):
            continue
        t = T(n, k, ol, batched=bt)
        sps = 1e3 / t
        w16 = 1e6 / (sps * 16 * 0.85) / 3600
        w32 = 1e6 / (sps * 32 * 0.85) / 3600
        lines.append(f"| {tag} | {t:.1f} | {sps:.1f} | 16w {w16:.2f} h / 32w {w32:.2f} h |")
    softs = [r["ref_soft"] for r in rows]
    lines += ["", f"state-bank v_soft range: [{min(softs):.3f}, {max(softs):.3f}] "
              f"(median {float(np.median(softs)):.3f}) -- near-gate coverage context."]
    lines += ["", "notes:",
              "- obs-lite = drop/reuse the post-move vres2 union rebuild (obs v-triple only;",
              "  needs an additive env.py param -> freeze decision, see docs/09 SS8).",
              "- coma cadence k needs an env-side skip (frozen env computes coma_D every step);",
              "  S8 only fixes the BASELINE, cadence is contract-legal per docs/09 SS5 2A'.",
              "- batched eval (lever 5) makes cadence mostly moot: all 6 layouts cost ~2 evals.",
              "- state bank = no-fire random-policy visitation on the training corridor;",
              "  gate-agreement stats inherit that distribution (near-gate density caveat).", ""]
    path = os.path.join(OUT_DIR, "spike_results.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["profile", "sweep", "batched", "gate", "parallel", "report"])
    ap.add_argument("--n-list", default="")
    args = ap.parse_args()
    if args.phase == "profile":
        phase_profile()
    elif args.phase == "sweep":
        phase_sweep([int(x) for x in args.n_list.split(",") if x])
    elif args.phase == "batched":
        phase_batched()
    elif args.phase == "gate":
        phase_gate()
    elif args.phase == "parallel":
        phase_parallel()
    else:
        phase_report()


if __name__ == "__main__":
    main()
