"""A-3b forced-first-fire oracle (docs/13 SS9 T-1; docs/09 (hh); pre-pilot GATE).

Reviewer's top directive: before interpreting R0 as a representation test,
measure -- with forced fire, no learning -- whether the injected robust-bank
states actually support the terminal chain, and how the judged reward prices
firing vs dwelling.

Per witness x N fresh CRN seeds, two arms on the FROZEN composition root:

  FIRE  arm: fire_cmd = 1 EVERY step (limiters hold, finisher axis hold).
             The FSM commits on the first step whose fresh union sample has
             v_soft >= theta (R2 gate; sub-theta commands are ignored, not
             wasted). Records: commit step, at-commit v/o/boxed/clean (from
             the fire-chain record = pre-move injected-state judgment),
             captured/wasted at resolution, discounted return.
  DWELL arm: never fire; run to episode end. Records: discounted return,
             per-step shared-J rate, episode length, clean-cross-ever.

GATE (pre-registered, docs/09 (hh) T-1): fraction of FIRE episodes with a
step-1 commit that is clean >= 0.8, pooled over the bank. Below that, R0 is
not interpretable and the pilot must not launch.

Also reports step>=2 commits' clean rate (expected ~0: the attacker moves
0.8-1.2 m/step vs a 0.05-0.2 m window -- reviewer's narrowness point) and the
dwell-vs-fire discounted-return gap (T-2 annuity measurement; NOTE dwell here
uses HOLD limiters, so no blocking -- the annuity horizon is penetration-
bounded and the gap is a LOWER bound on the blocking exploit).

CLI (numpy-only; chunk with --witness / --n for 45s sandboxes):
  PYTHONPATH=. python3 -m shepherd.scripts.a3b_fire_oracle \
      --bank results/a3_robust_bank.json --n 100 --dwell-n 10 \
      --out results/a3b_fire_oracle.json
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib

import numpy as np
import yaml

from shepherd.env_m3 import M3Params
from shepherd.train.make_env_m3 import M3Adapter, make_m3_train_env
from shepherd.train.spawn_bank import load_t0, spawn_from

GAMMA = 0.99
SEED0 = 31_000_000          # oracle CRN base; disjoint from train/eval/heldout


def build(env_cfg):
    rw = env_cfg["reward"]
    m3 = M3Params(l1=float(rw["lambda1"]), l2=float(rw["lambda2"]),
                  l3=float(rw["lambda3"]))
    env, _, _ = make_m3_train_env(copy.deepcopy(env_cfg), m3, stage=None)
    return env, M3Adapter(env)


def rollout(env, ad, spawn, seed, fire: bool, gamma: float):
    obs, _ = ad.reset_to(spawn, seed=seed)
    tail0 = np.asarray(obs[env.possible_agents[0]], float)[-3:]
    lim_zero = {lid: np.zeros(3, np.float32) for lid in ad.limiter_ids}
    fin = np.array([0, 0, 0, 1.0 if fire else 0.0], np.float32)  # LIVE dims: axis3+fire
    ret = 0.0
    js = []
    steps = 0
    r = None
    while True:
        r = ad.step({**lim_zero, ad.finisher_id: fin})
        j = float(r.rewards[ad.finisher_id])
        ret += (gamma ** steps) * j
        js.append(j)
        steps += 1
        if r.done or steps >= 200:
            break
    chains = list(r.flags["fire_chains"])
    return {"reset_v": float(tail0[0]), "reset_pfeas": float(tail0[2]),
            "reset_clean": bool(tail0[0] >= 0.9 and tail0[2] > 0.0),
            "len": steps, "return_disc": float(ret),
            "j_per_step_mean": float(np.mean(js)) if js else 0.0,
            "clean_ever": bool(r.flags["clean_net_threshold_crossed"]
                               or any(c["clean"] for c in chains)),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
            "wasted": float(r.flags["wasted_fire"]),
            "chains": chains}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="results/a3_robust_bank.json")
    ap.add_argument("--env-config", default="configs/m2_l2_train.yaml")
    ap.add_argument("--witness", type=int, default=None)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--dwell-n", type=int, default=10)
    ap.add_argument("--seed0", type=int, default=SEED0)
    ap.add_argument("--gamma", type=float, default=GAMMA)
    ap.add_argument("--out", default="results/a3b_fire_oracle.json")
    a = ap.parse_args()
    env_cfg = yaml.safe_load(open(a.env_config))
    t0s = load_t0(a.bank)
    env, ad = build(env_cfg)
    out_p = pathlib.Path(a.out)
    report = (json.loads(out_p.read_text()) if out_p.exists()
              else {"meta": {"n": a.n, "dwell_n": a.dwell_n,
                             "seed0": a.seed0, "gamma": a.gamma,
                             "gate": "step1-commit AND clean >= 0.8 pooled"},
                    "witnesses": {}})
    idxs = range(len(t0s)) if a.witness is None else [a.witness]
    for i in idxs:
        t0 = t0s[i]
        sp = spawn_from(t0)
        F = [rollout(env, ad, sp, a.seed0 + i * 100_000 + k, True, a.gamma)
             for k in range(a.n)]
        D = [rollout(env, ad, sp, a.seed0 + i * 100_000 + k, False, a.gamma)
             for k in range(a.dwell_n)]
        com = [(r["chains"][0] if r["chains"] else None) for r in F]
        c1 = [c for c in com if c and c["fire_step"] == 1]
        c2 = [c for c in com if c and c["fire_step"] >= 2]
        row = {
            "src": t0.src,
            "reset_clean_rate": float(np.mean([r["reset_clean"] for r in F])),
            "commit_rate": float(np.mean([c is not None for c in com])),
            "commit_step1_rate": len(c1) / a.n,
            "step1_clean_rate": (float(np.mean([c["clean"] for c in c1]))
                                 if c1 else None),
            "step1_commit_and_clean_rate": (
                sum(1 for c in c1 if c["clean"]) / a.n),
            "step2plus_clean_rate": (float(np.mean([c["clean"] for c in c2]))
                                     if c2 else None),
            "n_step2plus": len(c2),
            "capture_rate": float(np.mean([r["captured"] for r in F])),
            "wasted_rate": float(np.mean([r["wasted"] > 0 for r in F])),
            "fire_return_disc_mean": float(np.mean([r["return_disc"]
                                                    for r in F])),
            "fire_len_mean": float(np.mean([r["len"] for r in F])),
            "dwell_return_disc_mean": float(np.mean([r["return_disc"]
                                                     for r in D])),
            "dwell_len_mean": float(np.mean([r["len"] for r in D])),
            "dwell_j_per_step": float(np.mean([r["j_per_step_mean"]
                                               for r in D])),
            "dwell_clean_ever_rate": float(np.mean([r["clean_ever"]
                                                    for r in D])),
        }
        report["witnesses"][t0.src] = row
        print(f"[{i}] {t0.src}: commit@1={row['commit_step1_rate']:.2f} "
              f"clean@1={row['step1_clean_rate']} "
              f"gate_metric={row['step1_commit_and_clean_rate']:.2f} "
              f"cap={row['capture_rate']:.2f} waste={row['wasted_rate']:.2f} "
              f"| ret fire={row['fire_return_disc_mean']:+.2f} "
              f"dwell={row['dwell_return_disc_mean']:+.2f}")
    rows = list(report["witnesses"].values())
    if rows:
        pooled = float(np.mean([r["step1_commit_and_clean_rate"]
                                for r in rows]))
        report["pooled_gate_metric"] = pooled
        report["gate_pass"] = bool(pooled >= 0.8)
        print(f"POOLED gate metric = {pooled:.3f} -> "
              f"{'PASS' if pooled >= 0.8 else 'FAIL'}")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, indent=1))
    print("->", out_p)


if __name__ == "__main__":
    main()
