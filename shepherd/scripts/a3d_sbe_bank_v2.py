"""bank v2 generator: action-necessary, forward-verified predecessor
synthesis (docs/18 SS3/SS6 RATIFIED; docs/09 (ddd)).

GENERATION IS GATED BEHIND THE 0-e PRE-REGISTRATION COMMIT: this module is
committed and tested first (SS8-3 generator freeze), then run ONCE
(single-regeneration rule). A plumbing smoke on an information-free cell
(v16/d1, already known-pass from the (bbb) refine screen) is permitted;
its output is discarded.

Per (k, witness) cell of the FROZEN coverage matrix (embedded in
results/a3_robust_bank_v2.json meta):
  for each v0 candidate interval in V0_GRID (FIRST-FIT order, candidate 0 =
  the v1 distribution -- the (0d-1) tie-break "closest to v1" realized as
  try-order; argmax-over-candidates available via --v0-select argmax, the
  0-e commit fixes which rule is binding):
    draw up to ATTEMPT_CAP construction attempts (v1 synth_draw: closed-form
    decel arrival, cone +-15deg, |a|<=24, 4 construction gates) and pass
    each KEPT draw through the paired screen (frozen instruments, seeds
    400..419 -- generation band, disjoint from every prior family):
        PASS <=> pfc_succ >= 16/20 AND zero_succ <= 4/20
                 AND reset_clean <= 4/20        (early-abort fail-fast)
    stop at DRAWS_TARGET accepted; candidate succeeds if accepted >=
    MIN_ACCEPT. All candidates fail -> cell EXCLUDED (rule C).
Diagnostics recorded per cell (0d-1 condition 3 + en-route hypothesis):
  attempts, construction drops by reason, screen fails, accepted v0 stats,
  zero-arm captured-episode length histogram (fire ends the episode, so
  len ~ commit step -- the en-route detector for d4).

Draw rng: default_rng(47_000 + 1_000*k + int(v) + 100_000*cand_idx)
(fresh 47k band; deterministic, one stream per (cell, candidate)).
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
import yaml

from shepherd.scripts.a3d_calibration import _lim_fn        # torch stub side-effect
from shepherd.scripts.a3d_sbe_bank import (DT as BANK_DT, _ring, synth_draw)
from shepherd.scripts.train_m3a import m3_eval_bundle
from shepherd.train import pfc as pfc_mod
from shepherd.train.make_env_m3 import (Curriculum, frozen_constants,
                                        m3_params_from_cfg)
from shepherd.train.phi_potential import teacher_fire
from shepherd.train.spawn_bank import load_t0

SCREEN_SEEDS = tuple(range(400, 420))       # generation band (0-e ledger)
CP, CD = 1.0, 0.5                           # frozen gains ((zz))
PFC_MIN, ZERO_MAX, RESETC_MAX = 16, 4, 4    # /20
ATTEMPT_CAP = 48                            # per (cell, candidate)
DRAWS_TARGET, MIN_ACCEPT = 12, 8
V0_GRID = ((0.3, 0.8), (0.5, 0.8), (0.15, 0.5))   # candidate 0 = v1 dist
K_OF_STAGE = {"d1": 1, "d2": 2, "d3": 4, "d4": 8}


def paired_screen(entry, env_cfg, m3, stage, theta, seeds=SCREEN_SEEDS):
    """Draw-level paired PFC/zero screen (fail-fast). Also collects the
    zero-arm captured-episode lengths (en-route fire-time proxy)."""
    spawn = entry["spawn"]

    def fin_fn(obs, flags):
        return np.array([0, 0, 0, 1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    def run(lim_fn, seed):
        ev = m3_eval_bundle(env_cfg, m3, lim_fn, fin_fn, 1, int(seed),
                            stage=stage,
                            spawn_fn=lambda _i, sp=spawn: dict(sp),
                            per_episode=True)
        return ev["per_episode"][0]

    n = len(seeds)
    pfc_s = zero_s = rc = used = 0
    zero_cap_lens = []
    for i, seed in enumerate(seeds):
        used = i + 1
        rp = run(pfc_mod.make_pfc_fn(spawn, entry["demo_accels"],
                                     BANK_DT, CP, CD), seed)
        pfc_s += int(rp["arrival_capture"])
        rc += int(rp["reset_clean"])
        rz = run(_lim_fn("zero", entry, None), seed)
        if rz["captured"]:
            zero_cap_lens.append(int(rz["len"]))
        zero_s += int(rz["arrival_capture"])
        if (zero_s > ZERO_MAX or rc > RESETC_MAX
                or (used - pfc_s) > n - PFC_MIN):
            break
    ok = (pfc_s >= PFC_MIN and zero_s <= ZERO_MAX and rc <= RESETC_MAX
          and used == n)
    return {"pass": bool(ok), "pfc": pfc_s, "zero": zero_s,
            "reset_clean": rc, "seeds_used": used,
            "zero_cap_lens": zero_cap_lens}


def build_cell(t0, sname, k, env_cfg, m3, stage, theta,
               v0_grid=V0_GRID, select="first_fit", log=print):
    """One (witness, stage) cell -> (accepted_entries, report)."""
    anchors = _ring()
    Lstar = np.asarray(t0.limiters, float)
    v = float(t0.v)
    cand_reports = []
    winners = None, None                     # (cand_idx, accepted)
    for ci, v0_range in enumerate(v0_grid):
        rng = np.random.default_rng(47_000 + 1_000 * k + int(v)
                                    + 100_000 * ci)
        attempts, drops, screen_fail = 0, {}, 0
        accepted, zero_lens = [], []
        while attempts < ATTEMPT_CAP and len(accepted) < DRAWS_TARGET:
            attempts += 1
            entry, reason = synth_draw(t0, k, rng, anchors, Lstar,
                                       v0_range=tuple(v0_range))
            if entry is None or not entry["kept"]:
                drops[reason] = drops.get(reason, 0) + 1
                continue
            scr = paired_screen(entry, env_cfg, m3, stage, theta)
            zero_lens += scr.pop("zero_cap_lens")
            if scr["pass"]:
                entry["screen"] = scr
                entry["v0_candidate"] = ci
                accepted.append(entry)
            else:
                screen_fail += 1
        v0s = [float(np.linalg.norm(np.asarray(e["spawn"]["limiter_v"],
                                               float), axis=1).mean())
               for e in accepted]
        rep = {"candidate": ci, "v0_range": list(v0_range),
               "attempts": attempts, "construction_drops": drops,
               "screen_fail": screen_fail, "accepted": len(accepted),
               "accepted_v0_mean": (round(float(np.mean(v0s)), 3)
                                    if v0s else None),
               "zero_cap_len_hist": sorted(zero_lens),
               "pfc_mean": (round(float(np.mean(
                   [e["screen"]["pfc"] for e in accepted])) / 20, 3)
                   if accepted else None),
               "zero_mean": (round(float(np.mean(
                   [e["screen"]["zero"] for e in accepted])) / 20, 3)
                   if accepted else None)}
        cand_reports.append(rep)
        log(f"  {t0.src} {sname} cand{ci}{tuple(v0_range)}: "
            f"acc={len(accepted)}/{attempts} scr_fail={screen_fail} "
            f"drops={drops}")
        if len(accepted) >= MIN_ACCEPT:
            winners = ci, accepted
            if select == "first_fit":
                break
    ci, accepted = winners
    report = {"stage": sname, "witness": t0.src, "att_speed": float(t0.v),
              "k": k, "selected_candidate": ci,
              "excluded": ci is None, "candidates": cand_reports}
    return (accepted or []), report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--witness-bank", default="results/a3_robust_bank_v2.json")
    ap.add_argument("--out", default="results/a3d_sbe_bank_v2.json")
    ap.add_argument("--cells", nargs="+", default=None,
                    help="restrict to 'v16:d1'-style cells (smoke only)")
    ap.add_argument("--v0-select", choices=("first_fit", "argmax"),
                    default="first_fit")
    a = ap.parse_args()
    wb = json.loads(pathlib.Path(a.witness_bank).read_text())
    coverage = wb["witness_freeze"]["coverage_matrix"]
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    import copy
    cur = Curriculum(copy.deepcopy(run_cfg["curriculum"]),
                     frozen_constants(env_cfg, m3), env_cfg=env_cfg)
    n2i = {st["name"]: i for i, st in enumerate(cur.sbe_stages)}
    t0s = {f"v{int(t.v)}": t for t in load_t0(a.witness_bank)}
    entries, reports = [], []
    for wname, stages in coverage.items():
        for sname in stages:
            if a.cells and f"{wname}:{sname}" not in a.cells:
                continue
            cur.d_idx = n2i[sname]
            stage = cur.overrides(0)
            acc, rep = build_cell(t0s[wname], sname, K_OF_STAGE[sname],
                                  env_cfg, m3, stage, theta,
                                  select=a.v0_select)
            entries += acc
            reports.append(rep)
            print(f"CELL {wname}/{sname}: "
                  f"{'EXCLUDED' if rep['excluded'] else 'OK'} "
                  f"({len(acc)} entries)", flush=True)
    doc = {"meta": {"witness_bank": a.witness_bank,
                    "coverage": coverage, "screen_seeds": list(SCREEN_SEEDS),
                    "gains": [CP, CD], "attempt_cap": ATTEMPT_CAP,
                    "min_accept": MIN_ACCEPT, "v0_grid": [list(g) for g in
                                                          V0_GRID],
                    "v0_select": a.v0_select,
                    "note": "generation gated behind the 0-e commit; "
                            "cells filter = smoke only (output discarded)"},
           "reports": reports, "entries": entries}
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=1))
    n_ex = sum(1 for r in reports if r["excluded"])
    print(f"wrote {a.out}: cells={len(reports)} excluded={n_ex} "
          f"entries={len(entries)}")


if __name__ == "__main__":
    main()
