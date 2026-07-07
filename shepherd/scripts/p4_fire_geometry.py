"""P4 server lane: fire-moment geometry of the learned fire-mode policies.

Evidence-lock experiment (docs/09 (s)/(t); NO new training): roll the four
fire-mode policies (mappo_run2/coma_run2 x seed 7/8, best ckpt) on the nominal
frozen env, and at each fire_event record where the policy sits relative to
the boxed basin and the razor-thin clean window found by p4_clean_probe:

  * env-side flags at the gating step: v_soft / v_worst / p_feasible / boxed /
    clean (these are the exact values the FSM gate saw);
  * geometry snapshot from the PRE-MOVE state (limiters, finisher, attacker);
  * radial perturbation sweep: push all limiters radially AWAY from the
    attacker ballistic axis by delta (m) and re-evaluate the frozen union ->
    delta_to_unboxed and delta_to_clean (signed distances to each boundary).

Expected (P4 story): boxed at delta=0, unboxed only after +O(10cm), clean at
most a hairline beyond -- "the learned fire-mode sits inside the adjacent
boxed basin, not near the clean window."

  .venv-l2/bin/python -m shepherd.scripts.p4_fire_geometry \
      --ckpt-dir results/coma_run2/seed7 --episodes 10 \
      --out results/p4_probe/fire_geom_coma_seed7.json
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib

import numpy as np
import yaml

from shepherd.game import viability as V
from shepherd.scripts.eval_heldout import learned_fns
from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.make_env import make_train_env

EVAL_SEED0 = 85_000_000          # fresh CRN stream (disjoint from train/P1)
DELTAS = np.round(np.arange(-0.20, 1.001, 0.05), 3)

# frozen M2 constants (configs/m2_l2_train.yaml) -- keep in sync with p4_clean_probe
TAU, A_ATT, KILL_R, THETA = 0.4, 30.0, 2.0, 0.9
CONE_HALF, RANGE_MIN, RANGE_MAX = 0.067, 0.0, 29.847


def _split(state):
    s = np.asarray(state, float)
    lims = [s[9 * i:9 * i + 3] for i in range(4)]
    fin_p, fin_e = s[36:39], s[42:45]
    att_p, att_v = s[45:48], s[48:51]
    return np.array(lims), fin_p, fin_e, att_p, att_v


def _radial_push(lims, att_p, att_v, delta):
    """Move each limiter radially away from the attacker ballistic axis."""
    d = att_v / max(np.linalg.norm(att_v), 1e-9)
    out = []
    for L in lims:
        rel = L - att_p
        rad = rel - (rel @ d) * d
        rn = np.linalg.norm(rad)
        r_hat = rad / rn if rn > 1e-9 else np.zeros(3)
        out.append(L + delta * r_hat)
    return np.array(out)


def _eval_geom(lims, fin_p, fin_e, att_p, att_v, seed=0):
    u = V.build_reachable_union(att_p, att_v, tau=TAU, a_att_max=A_ATT,
                                judge="se3_cone", net_apex=fin_p, n_F=fin_e,
                                theta_net=CONE_HALF, range_min=RANGE_MIN,
                                range_max=RANGE_MAX, n=2000, n_segments=4, seed=seed)
    r = V.eval_union_with_limiters(u, lims, KILL_R)
    clean = (not r.boxed_in) and r.v_shot_soft >= THETA
    return dict(v_soft=r.v_shot_soft, worst=r.v_shot_worst, boxed=r.boxed_in,
                p_feas=r.p_feasible, n_open=int(r.n_feasible), clean=clean)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt-dir", required=True)
    ap.add_argument("--tag", default="best")
    ap.add_argument("--env-config", default="configs/m2_l2_train.yaml")
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    env_cfg = yaml.safe_load(open(a.env_config))
    lim_fn, fin_fn, meta = learned_fns(pathlib.Path(a.ckpt_dir), a.tag, a.device)
    env, _, _ = make_train_env(copy.deepcopy(env_cfg))
    ad = ShepherdAdapter(env)
    lim_hi = ad.action_bounds(ad.limiter_ids[0])[1].astype(np.float32)
    fin_hi = ad.action_bounds(ad.finisher_id)[1][:3].astype(np.float32)

    events = []
    for ep in range(a.episodes):
        obs_d, _ = ad.reset(seed=EVAL_SEED0 + ep)
        obs = obs_d[ad.limiter_ids[0]]
        prev_state = ad.env.state()
        flags = {}
        for t in range(200):
            lim = lim_fn(obs, flags, lim_hi)
            fin = fin_fn(obs, flags, fin_hi)
            live = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.asarray(fin, np.float32)
            r = ad.step(live)
            if r.flags.get("fire_event"):
                lims, fin_p, fin_e, att_p, att_v = _split(prev_state)
                sweep = {}
                for dlt in DELTAS:
                    sweep[float(dlt)] = _eval_geom(
                        _radial_push(lims, att_p, att_v, dlt),
                        fin_p, fin_e, att_p, att_v)
                base = sweep[0.0]
                unbox = [d for d, s in sweep.items() if not s["boxed"]]
                cleans = [d for d, s in sweep.items() if s["clean"]]
                events.append(dict(
                    episode=ep, t=t,
                    env_flags=dict(v_soft=float(r.flags["v_shot_soft"]),
                                   worst=float(r.flags["v_shot_worst"]),
                                   p_feas=float(r.flags["p_feasible"]),
                                   boxed=bool(r.flags["boxed_in"]),
                                   clean=bool(r.flags["clean_net_threshold_crossed"])),
                    recomputed_at_delta0=base,
                    delta_to_unboxed=(min(unbox) if unbox else None),
                    delta_to_clean=(min(cleans) if cleans else None),
                    sweep={str(k): v for k, v in sweep.items()},
                    geometry=dict(limiters=lims.tolist(), fin_p=fin_p.tolist(),
                                  fin_e=fin_e.tolist(), att_p=att_p.tolist(),
                                  att_v=att_v.tolist()),
                ))
                e = events[-1]
                print(f"[ep {ep} t={t}] gate: v={e['env_flags']['v_soft']:.3f} "
                      f"boxed={e['env_flags']['boxed']} clean={e['env_flags']['clean']} | "
                      f"delta0: boxed={base['boxed']} n_open={base['n_open']} | "
                      f"d_unbox={e['delta_to_unboxed']} d_clean={e['delta_to_clean']}")
            prev_state = ad.env.state()
            obs = r.obs[ad.limiter_ids[0]]
            flags = r.flags
            if r.done:
                break
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": {**meta, "episodes": a.episodes,
                                        "eval_seed0": EVAL_SEED0},
                               "fire_events": events}))
    n_boxed = sum(1 for e in events if e["recomputed_at_delta0"]["boxed"])
    print(f"fire events: {len(events)} | boxed at delta=0: {n_boxed} "
          f"| -> {out}")


if __name__ == "__main__":
    main()
