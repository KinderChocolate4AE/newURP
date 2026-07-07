"""P1 held-out CRN evaluation of a FIXED ckpt on the FROZEN M3a env (docs/11 SS2/SS4).

Same discipline as eval_heldout.py (docs/09 (p)): report metric = held-out CRN
seed set EVAL_SEED0=77M+i, disjoint from training seeds/evals for campaign
seeds 0..9; episode i is paired across arms/bundles. Differences:

  * env = M3ShapingEnv with FROZEN constants + judgment m3 params (stage=None;
    curriculum scaffolds NEVER touch this path);
  * m3 params come from the RUN config (--run-config) `m3:` block -- the same
    file that trained the ckpt, so the judged reward is the trained one;
  * per-episode records add the fire-chain decomposition (docs/11 SS3) +
    clean/capture fields consumed by the M3a gates (docs/11 SS4: Gate A =
    seed-cluster one-sided 95% lower bound of clean_cross_rate > 0; Gate B =
    capture existence).

CLI (server, torch venv):
  python -m shepherd.scripts.eval_heldout_m3 --bundle learned \
      --run-config configs/m3a_s1_scratch.yaml \
      --ckpt-dir results/m3a_playin/scratch/seed0 --tag best \
      --out results/m3a_heldout/scratch_seed0.json
  python -m shepherd.scripts.eval_heldout_m3 --bundle hold \
      --run-config configs/m3a_s1_scratch.yaml --out results/m3a_heldout/hold.json
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

from shepherd.train.make_env_m3 import (M3Adapter, m3_params_from_cfg,
                                        make_m3_train_env)

EVAL_SEED0 = 77_000_000          # pre-registered (P1); do not change mid-campaign
EPISODES = 200


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    except Exception:
        return "unknown"


def learned_fns(ckpt_dir: pathlib.Path, tag: str, device: str):
    """Deterministic policy fns from a saved MAPPO ckpt (+frozen obs norm).
    Identical to eval_heldout.learned_fns (same ckpt schema)."""
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


def run_episodes(env_cfg: dict, m3, bundle: str, episodes: int, eval_seed0: int,
                 lim_fn=None, fin_fn=None) -> list:
    """Per-episode records on the FROZEN M3 env, CRN seeds eval_seed0+i."""
    from shepherd.scripts.train_ippo import (hold_bundle, make_scripted_ctx,
                                             scripted_bundle)
    env, _, _ = make_m3_train_env(copy.deepcopy(env_cfg), m3, stage=None)
    ad = M3Adapter(env)
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
        ret = head = head_m3 = 0.0
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
            head_m3 += float(r.flags["headline_m3"])
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
            "headline_sum": float(head), "headline_m3_sum": float(head_m3),
            "clean": bool(clean),
            "wasted": float(r.flags["wasted_fire"]),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
            "truncated": bool(r.truncated),
            "fire_events": int(fire), "boxed_steps": int(boxed),
            "fire_chains": list(r.flags["fire_chains"]),
        })
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", choices=["learned", "scripted", "hold"],
                    required=True)
    ap.add_argument("--run-config", required=True,
                    help="m3a run YAML (m3: block + env_config pointer)")
    ap.add_argument("--ckpt-dir", default=None)
    ap.add_argument("--tag", default="best", choices=["best", "latest"])
    ap.add_argument("--episodes", type=int, default=EPISODES)
    ap.add_argument("--eval-seed0", type=int, default=EVAL_SEED0)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    run_cfg = yaml.safe_load(open(a.run_config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    meta = {"bundle": a.bundle, "episodes": a.episodes,
            "eval_seed0": a.eval_seed0, "git_head": _git_head(),
            "run_config": a.run_config, "env_config": run_cfg["env_config"],
            "m3": {k: getattr(m3, k) for k in
                   ("o_star", "sigma_g", "w_h", "w_g", "w_gf", "lam_cap",
                    "v_eff_mode")}}
    lim_fn = fin_fn = None
    if a.bundle == "learned":
        ckpt_dir = pathlib.Path(a.ckpt_dir)
        tag = a.tag
        if not (ckpt_dir / f"ckpt_mappo_{tag}.pt").exists():
            tag = "latest"
        lim_fn, fin_fn, m = learned_fns(ckpt_dir, tag, a.device)
        meta.update(m, tag=tag, tag_requested=a.tag, ckpt_dir=str(ckpt_dir))
    recs = run_episodes(env_cfg, m3, a.bundle, a.episodes, a.eval_seed0,
                        lim_fn, fin_fn)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": meta, "episodes": recs}))
    cleans = [r["clean"] for r in recs]
    caps = [r["captured"] for r in recs]
    print(f"[{a.bundle}] n={len(recs)} clean_cross_rate={np.mean(cleans):.4f} "
          f"capture_count={int(np.sum(caps))} "
          f"return_mean={np.mean([r['ret'] for r in recs]):+.3f} -> {out}")


if __name__ == "__main__":
    main()
