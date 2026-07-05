"""P1 held-out CRN evaluation of a FIXED checkpoint (docs/09 (o)/(p)).

Separates the *training selection metric* (last-3 / best-sustained, used only
to pick the checkpoint) from the *report metric*: a held-out common-random-
number (CRN) eval seed set never used during training. Episode i uses env
seed ``eval_seed0 + i`` for EVERY bundle/arm/train-seed, so episodes are
paired across arms and against baselines (peer-review Major 2 / Q1 fix).

Held-out guarantee: training evals use seed*1_000_003+500_000 (< 1e7 for
seeds 0..9) and training episodes use seed*1_000_003+1+ep; the default
eval_seed0=77_000_000 is disjoint from both for all campaign seeds.

CLI (server, torch venv):
  python -m shepherd.scripts.eval_heldout --bundle learned \
      --ckpt-dir results/coma_run2/seed0 --tag best \
      --out results/p1_eval/coma_run2_seed0.json
  python -m shepherd.scripts.eval_heldout --bundle scripted \
      --out results/p1_eval/scripted.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import subprocess

import numpy as np
import yaml

from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.make_env import make_train_env

EVAL_SEED0 = 77_000_000          # pre-registered; do not change mid-campaign
EPISODES = 200


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def learned_fns(ckpt_dir: pathlib.Path, tag: str, device: str):
    """Deterministic policy fns from a saved MAPPO ckpt (+frozen obs norm)."""
    import torch
    from shepherd.train.ippo import limiter_inputs
    from shepherd.train.mappo import MAPPOTrainer
    from shepherd.train.obs_norm import RunningNorm

    ckpt = ckpt_dir / f"ckpt_mappo_{tag}.pt"
    tr = MAPPOTrainer.load(ckpt, map_location=device)
    norm = RunningNorm(tr.obs_dim)
    norm.load_state_dict(json.loads(
        (ckpt_dir / f"obs_norm_{tag}.json").read_text()))
    sha = hashlib.sha256(ckpt.read_bytes()).hexdigest()[:12]

    def limiter_fn(obs, flags, _scale):
        nobs = norm.normalize(obs)
        t = torch.as_tensor(limiter_inputs(nobs, tr.n), device=tr.device)
        raw, _ = tr.lim_actor.act(t, deterministic=True)
        return (np.clip(raw.cpu().numpy(), -1.0, 1.0) * _scale).astype(np.float32)

    def finisher_fn(obs, flags, _axis_scale):
        nobs = norm.normalize(obs)
        t = torch.as_tensor(nobs[None, :], device=tr.device)
        raw, _ = tr.fin_actor.act(t, deterministic=True)
        raw = raw[0].cpu().numpy()
        axis = np.clip(raw[:3], -1.0, 1.0) * _axis_scale
        return np.concatenate([axis, raw[3:]]).astype(np.float32)

    return limiter_fn, finisher_fn, {"ckpt": str(ckpt), "ckpt_sha256_12": sha}


def run_episodes(env_cfg: dict, bundle: str, episodes: int, eval_seed0: int,
                 lim_fn=None, fin_fn=None) -> list:
    """Per-episode records on the NOMINAL env, CRN seeds eval_seed0+i."""
    from shepherd.scripts.train_ippo import (hold_bundle, make_scripted_ctx,
                                             scripted_bundle)
    env, _, _ = make_train_env(copy.deepcopy(env_cfg))
    ad = ShepherdAdapter(env)
    lim_low, lim_high = ad.action_bounds(ad.limiter_ids[0])
    fin_low, fin_high = ad.action_bounds(ad.finisher_id)
    if bundle in ("scripted", "hold"):
        ctx = make_scripted_ctx(env_cfg)
        base_lim, base_fin = (scripted_bundle(ctx) if bundle == "scripted"
                              else hold_bundle(ctx))
    recs = []
    for ep in range(episodes):
        obs_d, _ = ad.reset(seed=eval_seed0 + ep)
        obs = obs_d[ad.limiter_ids[0]]
        flags = {}
        ret = head = 0.0
        steps = fire = boxed = 0
        clean = False
        while True:
            if bundle == "learned":
                lim = lim_fn(obs, flags, lim_high.astype(np.float32))
                fin = fin_fn(obs, flags, fin_high[:3].astype(np.float32))
            else:
                lim = base_lim(obs, flags)
                fin = base_fin(obs, flags)
            live = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.asarray(fin, np.float32)
            r = ad.step(live)
            ret += r.rewards[ad.finisher_id]
            head += r.headline
            clean = clean or bool(r.flags["clean_net_threshold_crossed"])
            fire += 1 if r.flags.get("fire_event") else 0
            boxed += 1 if r.flags.get("boxed_in") else 0
            flags = r.flags
            obs = r.obs[ad.limiter_ids[0]]
            steps += 1
            if r.done:
                break
        recs.append({
            "ep": ep, "ret": float(ret), "len": int(steps),
            "headline_sum": float(head), "clean": bool(clean),
            "wasted": float(r.flags["wasted_fire"]),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
            "truncated": bool(r.truncated),
            "fire_events": int(fire), "boxed_steps": int(boxed),
        })
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", choices=["learned", "scripted", "hold"],
                    required=True)
    ap.add_argument("--ckpt-dir", default=None)
    ap.add_argument("--tag", default="best", choices=["best", "latest"])
    ap.add_argument("--env-config", default="configs/m2_l2_train.yaml")
    ap.add_argument("--episodes", type=int, default=EPISODES)
    ap.add_argument("--eval-seed0", type=int, default=EVAL_SEED0)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    env_cfg = yaml.safe_load(open(a.env_config))
    meta = {"bundle": a.bundle, "episodes": a.episodes,
            "eval_seed0": a.eval_seed0, "git_head": _git_head(),
            "env_config": a.env_config}
    lim_fn = fin_fn = None
    if a.bundle == "learned":
        ckpt_dir = pathlib.Path(a.ckpt_dir)
        tag = a.tag
        if not (ckpt_dir / f"ckpt_mappo_{tag}.pt").exists():
            tag = "latest"                      # fallback, recorded in meta
        lim_fn, fin_fn, m = learned_fns(ckpt_dir, tag, a.device)
        meta.update(m, tag=tag, tag_requested=a.tag,
                    ckpt_dir=str(ckpt_dir))
    recs = run_episodes(env_cfg, a.bundle, a.episodes, a.eval_seed0,
                        lim_fn, fin_fn)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "episodes": recs}))
    rets = [r["ret"] for r in recs]
    print(f"[{a.bundle}] n={len(recs)} return_mean={np.mean(rets):+.3f} "
          f"+-{np.std(rets):.3f} -> {out}")


if __name__ == "__main__":
    main()
