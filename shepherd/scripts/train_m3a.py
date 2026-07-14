"""M3a capture-unlock trainer (docs/11 v0.2 SS2/SS3; play-in = 3+3 x S1 200k).

Recipe = the P1-confirmed main recipe (blended coma_mix 0.5, recipe-v2 loop)
on the M3a env variant (shepherd/env_m3.py). Mirrors the stabilized 2C/2D
runner (train_mappo.py): [-1,1] actions, obs RunningNorm, attacker-family
randomization (train only), LR anneal + floor, one central value stream,
one-step-shifted coma_D write-back.

What is NEW here (docs/11):
  * curriculum scaffolding (SS2): per-episode env rebuild applies the CURRENT
    stage constants (S1 wide-clean -> S2 linear restore -> S3 frozen) to the
    TRAIN env only. Stage exits are metric-gated (S1: train-eval clean_cross >
    0.2 sustained AND boxed_fire_rate < 0.5 AND fire_rate > 0; S2: ramp done
    AND frozen-heldout clean_cross nonzero in the last 3 evals). Mode
    "s1_only" pins S1 for the whole run (the o*-sweep / play-in mode).
  * EVAL = ALWAYS frozen constants + judgment m3 params (SS2). The runner also
    logs a train-eval (current-stage constants) bundle for the S1 exit
    condition and the o*-sweep scaffold-selection indicators; train-eval
    numbers are diagnostics, NEVER judgment.
  * fire-chain decomposition logging per eval episode (SS3): fire_chains
    records (v/v_eff/o/n_feasible/boxed/clean/captured/wasted at commit,
    fire_step, release_event_before_fire, boxed_dwell_before_fire,
    |ln o - ln o*|) are stored in eval_curve.json points.
  * warm-start arm (SS3): --config with warm_start.enabled loads the mix-0.5
    best checkpoint's actor/critic/value-norm weights + frozen obs-norm state
    into a FRESH trainer (fresh optimizer; obs_dim/n asserted equal -- the M3
    env keeps the 63-dim obs layout precisely for this). Play-in selection
    rule (1) clean_cross (2) boxed_fire lower (3) frozen-heldout clean
    (4) tie -> scratch is applied OFFLINE by analyze_m3a_playin.py.
  * best-sustained checkpoint = last-3 FROZEN-eval mean of the pre-registered
    reference score clean + 0.5*capture - 0.5*boxed_fire - 0.2*boxed_dwell_frac
    (docs/11 SS3). Selection metric only; report metric = P1 held-out harness
    on the fixed ckpt (eval_heldout_m3.py).
  * ntfy hook (best-effort, env NTFY_TOPIC): run start/end + stage transitions.

CLI:
    python -m shepherd.scripts.train_m3a --config configs/m3a_s1_scratch.yaml \
        --seed 0 --device cuda --output results/m3a_playin/scratch
    # o* sweep (S1-limited scaffold selection, docs/11 SS2):
    python -m shepherd.scripts.train_m3a --config configs/m3a_s1_scratch.yaml \
        --o-star 3e-4 --seed 0 --output results/m3a_ostar/3e-4
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import time
import urllib.request
from typing import Dict, List, Optional

import numpy as np
import torch
import yaml

from shepherd.env_m3 import M3Params
from shepherd.train.attacker_rand import sample_attacker_params
from shepherd.train.ippo import limiter_inputs
from shepherd.train.make_env_m3 import (Curriculum, M3Adapter,
                                        build_m3_attacker_env,
                                        frozen_constants, m3_params_from_cfg,
                                        make_m3_train_env)
from shepherd.train.mappo import MAPPOConfig, MAPPORollout, MAPPOTrainer
from shepherd.train.obs_norm import RunningNorm
from shepherd.scripts.train_ippo import (hold_bundle, make_scripted_ctx,
                                         scripted_bundle, seed_everything)


# ------------------------------------------------------------------ ntfy ---
def ntfy(msg: str) -> None:
    """Best-effort push (docs/11 SS3 'ntfy hook'). No-op unless NTFY_TOPIC set."""
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        return
    try:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}",
                                     data=msg.encode("utf-8"),
                                     headers={"Title": "m3a"}, method="POST")
        urllib.request.urlopen(req, timeout=3)
    except Exception:
        pass                                        # never fail training on push


# ------------------------------------------------------------ eval bundle ---
def m3_eval_bundle(env_cfg: dict, m3: M3Params, limiter_fn, finisher_fn,
                   episodes: int, seed0: int,
                   stage: Optional[Dict[str, float]] = None,
                   spawn_fn=None) -> dict:
    """Deterministic bundle eval on the M3 env (nominal attacker, fixed CRN
    seeds). stage=None -> FROZEN constants + judgment m3 (the ONLY numbers
    judgment may use, docs/11 SS2); stage=dict -> train-eval diagnostics.
    Records the full fire-chain decomposition per episode (docs/11 SS3).

    spawn_fn (A-3 L-reverse, docs/13): optional ep->spawn dict sampler for the
    TRAIN-EVAL gating bundle only -- the judgment/frozen bundle and every
    held-out harness call this with spawn_fn=None (R-5 STRICT)."""
    env, _, _ = make_m3_train_env(copy.deepcopy(env_cfg), m3, stage=stage)
    ad = M3Adapter(env)
    recs = []
    for ep in range(episodes):
        obs_d, _ = (ad.reset_to(spawn_fn(ep), seed=seed0 + ep)
                    if spawn_fn is not None else ad.reset(seed=seed0 + ep))
        obs = obs_d[ad.limiter_ids[0]]
        flags: Dict[str, object] = {}
        ret = head = head_m3 = rgeo = 0.0
        steps = boxed_steps = near_steps = 0
        clean = False
        while True:
            lim = limiter_fn(obs, flags)
            live = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.asarray(finisher_fn(obs, flags), np.float32)
            r = ad.step(live)
            ret += r.rewards[ad.finisher_id]
            head += r.headline
            head_m3 += float(r.flags["headline_m3"])
            rgeo += float(r.flags["r_geo_step"])
            clean = clean or bool(r.flags["clean_net_threshold_crossed"])
            boxed_steps += 1 if r.flags["boxed_in"] else 0
            od = float(r.flags["o_dist_log"])
            near_steps += 1 if (np.isfinite(od) and od <= 1.0) else 0
            flags = r.flags
            obs = r.obs[ad.limiter_ids[0]]
            steps += 1
            if r.done:
                break
        chains = list(r.flags["fire_chains"])
        recs.append({
            "ret": ret, "len": steps, "headline_sum": head,
            "headline_m3_sum": head_m3, "r_geo_step_sum": rgeo,
            "clean": clean, "wasted": float(r.flags["wasted_fire"]),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
            "boxed_frac": boxed_steps / max(steps, 1),
            "o_near_rate": near_steps / max(steps, 1),
            "fire_chains": chains,
        })
    return _aggregate_m3(recs, episodes)


def _aggregate_m3(recs: List[dict], episodes: int) -> dict:
    rets = np.array([x["ret"] for x in recs], float)
    chains = [c for x in recs for c in x["fire_chains"]]
    n_fires = len(chains)
    boxed_fires = sum(1 for c in chains if c["boxed"])
    od = [c["o_dist_log"] for c in chains
          if c["o_dist_log"] is not None and np.isfinite(c["o_dist_log"])]
    out = {
        "episodes": episodes,
        "return_mean": float(rets.mean()), "return_std": float(rets.std()),
        "len_mean": float(np.mean([x["len"] for x in recs])),
        "headline_sum_mean": float(np.mean([x["headline_sum"] for x in recs])),
        "headline_m3_sum_mean": float(np.mean([x["headline_m3_sum"] for x in recs])),
        "r_geo_step_sum_mean": float(np.mean([x["r_geo_step_sum"] for x in recs])),
        "wasted_mean": float(np.mean([x["wasted"] for x in recs])),
        "captured_rate": float(np.mean([x["captured"] for x in recs])),
        "capture_count": int(sum(x["captured"] for x in recs)),
        "penetrated_rate": float(np.mean([x["penetrated"] for x in recs])),
        "clean_cross_rate": float(np.mean([x["clean"] for x in recs])),
        "boxed_dwell_frac_mean": float(np.mean([x["boxed_frac"] for x in recs])),
        "o_near_rate_mean": float(np.mean([x["o_near_rate"] for x in recs])),
        "fire_rate": float(np.mean([len(x["fire_chains"]) > 0 for x in recs])),
        "n_fires": n_fires,
        "boxed_fire_rate": (boxed_fires / n_fires) if n_fires else 0.0,
        "release_before_fire_rate": (
            (sum(1 for c in chains if c["release_event_before_fire"]) / n_fires)
            if n_fires else 0.0),
        "boxed_dwell_before_fire_mean": (
            float(np.mean([c["boxed_dwell_before_fire"] for c in chains]))
            if n_fires else 0.0),
        "o_dist_log_at_fire_mean": (float(np.mean(od)) if od else float("nan")),
        "fire_chains": chains,
    }
    # pre-registered reference score (docs/11 SS3): boxed_dwell as ep fraction
    out["sel_score"] = (out["clean_cross_rate"] + 0.5 * out["captured_rate"]
                        - 0.5 * out["boxed_fire_rate"]
                        - 0.2 * out["boxed_dwell_frac_mean"])
    return out


# ----------------------------------------------------------------- runner ---
class M3ARunner:
    """MAPPO(coma_mix) rollout collection on the M3a env with curriculum-staged
    per-episode env rebuilds. Mirrors MAPPORunner (train_mappo.py)."""

    def __init__(self, env_cfg: dict, run_cfg: dict, seed: int, device: str):
        self.env_cfg = env_cfg
        loop = run_cfg["loop"]
        self.rollout_env_steps = int(loop["rollout_env_steps"])
        self.seed = int(seed)

        self.m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
        self.cur = Curriculum(run_cfg["curriculum"],
                              frozen_constants(env_cfg, self.m3),
                              env_cfg=env_cfg)

        env, _, _ = make_m3_train_env(copy.deepcopy(env_cfg), self.m3)
        ad = M3Adapter(env)
        self.n = len(ad.limiter_ids)
        self.obs_dim = ad.obs_dim
        lim_low, lim_high = ad.action_bounds(ad.limiter_ids[0])
        fin_low, fin_high = ad.action_bounds(ad.finisher_id)
        if not (np.allclose(lim_low, -lim_high) and np.allclose(fin_low[:3], -fin_high[:3])):
            raise ValueError("action Boxes are expected symmetric for [-1,1] scaling")
        self.lim_scale = lim_high.astype(np.float32)
        self.fin_axis_scale = fin_high[:3].astype(np.float32)

        self.norm = RunningNorm(self.obs_dim)
        total = int(loop["total_env_steps"])
        cfg = MAPPOConfig.from_dict({**run_cfg["mappo"], "seed": seed,
                                     "device": device,
                                     "rollout_steps": self.rollout_env_steps,
                                     "total_timesteps": total})
        self.tr = MAPPOTrainer(self.obs_dim, self.n, cfg)
        self.buf = MAPPORollout(self.rollout_env_steps, self.obs_dim, self.n)

        self.rand_cfg = run_cfg.get("randomize")
        self.rand_rng = np.random.default_rng(seed * 9973 + 17)
        self.base_seed = seed * 1_000_003 + 1
        self.eval_seed0 = seed * 1_000_003 + 500_000

        self.env_steps = 0
        self.capture_count_train = 0
        self.ep_records: List[dict] = []
        self._ep_idx = 0
        self._adapter: Optional[M3Adapter] = None
        self._obs: Optional[np.ndarray] = None
        self._ep: Dict[str, float] = {}

    # ------------------------------------------------------------ episodes ---
    def _begin_episode(self) -> None:
        params = sample_attacker_params(self.rand_cfg, self.rand_rng)
        stage = self.cur.overrides(self.env_steps)
        spawn = self.cur.spawn(self.rand_rng)      # A-3: None unless reverse
        env, _, _ = build_m3_attacker_env(self.env_cfg, self.m3, params,
                                          stage=stage)
        self._adapter = M3Adapter(env)
        seed = self.base_seed + self._ep_idx
        obs_d, _ = (self._adapter.reset_to(spawn, seed=seed)
                    if spawn is not None else self._adapter.reset(seed=seed))
        self._obs = obs_d[self._adapter.limiter_ids[0]]
        self._ep = {"ret": 0.0, "headline": 0.0, "headline_m3": 0.0,
                    "limiter_loss": 0.0, "coma_sum": 0.0, "fire_events": 0.0,
                    "steps": 0.0, "clean": 0.0, "boxed_steps": 0.0}
        self._ep_params = params
        self._ep_stage = self.cur.stage

    def _finish_episode(self, r) -> None:
        steps = max(self._ep["steps"], 1.0)
        chains = list(r.flags["fire_chains"])
        captured = bool(r.flags["captured"])
        self.capture_count_train += 1 if captured else 0
        self.ep_records.append({
            "ret": self._ep["ret"], "len": int(steps),
            "headline_sum": self._ep["headline"],
            "headline_m3_sum": self._ep["headline_m3"],
            "coma_D_mean": self._ep["coma_sum"] / steps,
            "limiter_loss_sum": self._ep["limiter_loss"],
            "fire_events": self._ep["fire_events"],
            "clean": bool(self._ep["clean"]),
            "boxed_frac": self._ep["boxed_steps"] / steps,
            "boxed_fires": sum(1 for c in chains if c["boxed"]),
            "wasted": float(r.flags["wasted_fire"]),
            "captured": captured,
            "penetrated": bool(r.flags["penetrated"]),
            "truncated": bool(r.truncated),
            "stage": self._ep_stage,
            "attacker_params": dict(self._ep_params),
        })
        if len(self.ep_records) > 500:
            del self.ep_records[:-500]
        self._ep_idx += 1

    # ------------------------------------------------------------- rollout ---
    def collect_rollout(self) -> None:
        if self._adapter is None:
            self._begin_episode()
        device = self.tr.device
        prev_row = None                        # one-step-shifted coma_D (2D)
        for _ in range(self.rollout_env_steps):
            ad = self._adapter
            obs = self._obs
            nobs = self.norm.normalize(obs, update=True)

            x_l = limiter_inputs(nobs, self.n)
            raw_l_t, logp_l = self.tr.lim_actor.act(
                torch.as_tensor(x_l, device=device))
            raw_l = raw_l_t.cpu().numpy()
            clip_l = np.clip(raw_l, -1.0, 1.0)

            raw_f_t, logp_f = self.tr.fin_actor.act(
                torch.as_tensor(nobs[None, :], device=device))
            raw_f = raw_f_t[0].cpu().numpy()
            clip_f = raw_f.copy()
            clip_f[:3] = np.clip(raw_f[:3], -1.0, 1.0)

            value = self.tr.value_np(nobs)

            live = {lid: (clip_l[i] * self.lim_scale).astype(np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.concatenate(
                [clip_f[:3] * self.fin_axis_scale, clip_f[3:]]).astype(np.float32)

            r = ad.step(live)
            next_obs = r.obs[ad.limiter_ids[0]]
            if r.terminated:
                next_value = 0.0
            else:
                next_value = self.tr.value_np(self.norm.normalize(next_obs))

            if prev_row is not None:           # shift-back D(s_t) -> a_{t-1}
                self.buf.coma_D[prev_row] = np.array(
                    [r.coma_D[lid] for lid in ad.limiter_ids], np.float32)
            prev_row = self.buf._i
            self.buf.add(obs=nobs, lim_raw=raw_l, lim_clip=clip_l,
                         lim_logp=logp_l.cpu().numpy(),
                         fin_raw=raw_f, fin_clip=clip_f,
                         fin_logp=float(logp_f[0].item()),
                         rewards=r.rewards[ad.finisher_id],
                         values=value, next_values=next_value,
                         dones=1.0 if r.done else 0.0)

            self._ep["ret"] += r.rewards[ad.finisher_id]
            self._ep["headline"] += r.headline
            self._ep["headline_m3"] += float(r.flags["headline_m3"])
            self._ep["limiter_loss"] += float(r.flags["limiter_loss"])
            self._ep["coma_sum"] += float(np.mean(list(r.coma_D.values())))
            self._ep["fire_events"] += 1.0 if r.flags["fire_event"] else 0.0
            self._ep["clean"] = max(self._ep["clean"],
                                    1.0 if r.flags["clean_net_threshold_crossed"] else 0.0)
            self._ep["boxed_steps"] += 1.0 if r.flags["boxed_in"] else 0.0
            self._ep["steps"] += 1.0
            self.env_steps += 1

            if r.done:
                self._finish_episode(r)
                self._begin_episode()
                prev_row = None
            else:
                self._obs = next_obs

    def update(self) -> Dict[str, float]:
        stats = self.tr.update(self.buf)
        self.buf.reset()
        return stats

    def rolling(self, k: int = 20) -> Dict[str, float]:
        recs = self.ep_records[-k:]
        if not recs:
            return {}
        return {
            "train/ep_return": float(np.mean([x["ret"] for x in recs])),
            "train/ep_len": float(np.mean([x["len"] for x in recs])),
            "train/headline_sum": float(np.mean([x["headline_sum"] for x in recs])),
            "train/headline_m3_sum": float(np.mean([x["headline_m3_sum"] for x in recs])),
            "train/coma_D_mean": float(np.mean([x["coma_D_mean"] for x in recs])),
            "train/limiter_loss_sum": float(np.mean([x["limiter_loss_sum"] for x in recs])),
            "train/fire_events": float(np.mean([x["fire_events"] for x in recs])),
            "train/wasted": float(np.mean([x["wasted"] for x in recs])),
            "train/captured_rate": float(np.mean([x["captured"] for x in recs])),
            "train/penetrated_rate": float(np.mean([x["penetrated"] for x in recs])),
            "train/clean_cross_rate": float(np.mean([x["clean"] for x in recs])),
            "train/boxed_frac": float(np.mean([x["boxed_frac"] for x in recs])),
        }

    # ----------------------------------------------------------- eval / io ---
    def learned_bundle(self):
        device = self.tr.device

        def limiter_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(limiter_inputs(nobs, self.n), device=device)
            raw, _ = self.tr.lim_actor.act(t, deterministic=True)
            return (np.clip(raw.cpu().numpy(), -1.0, 1.0)
                    * self.lim_scale).astype(np.float32)

        def finisher_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(nobs[None, :], device=device)
            raw, _ = self.tr.fin_actor.act(t, deterministic=True)
            raw = raw[0].cpu().numpy()
            axis = np.clip(raw[:3], -1.0, 1.0) * self.fin_axis_scale
            return np.concatenate([axis, raw[3:]]).astype(np.float32)

        return limiter_fn, finisher_fn

    def evaluate(self, episodes: int):
        """(frozen_ev, train_ev): judgment bundle on FROZEN constants + the
        current-stage diagnostic bundle (same object when stage is None)."""
        lim_fn, fin_fn = self.learned_bundle()
        frozen_ev = m3_eval_bundle(self.env_cfg, self.m3, lim_fn, fin_fn,
                                   episodes, self.eval_seed0, stage=None)
        stage = self.cur.overrides(self.env_steps)
        spawn_fn = self.cur.eval_spawn_fn()        # A-3: gating bundle spawns
        if stage is None and spawn_fn is None:
            return frozen_ev, frozen_ev
        train_ev = m3_eval_bundle(self.env_cfg, self.m3, lim_fn, fin_fn,
                                  episodes, self.eval_seed0, stage=stage,
                                  spawn_fn=spawn_fn)
        return frozen_ev, train_ev

    def save(self, out_dir: pathlib.Path, tag: str = "latest") -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.tr.save(out_dir / f"ckpt_mappo_{tag}.pt")
        (out_dir / f"obs_norm_{tag}.json").write_text(
            json.dumps(self.norm.state_dict()))
        (out_dir / f"run_state_{tag}.json").write_text(json.dumps({
            "env_steps": self.env_steps, "episodes": self._ep_idx,
            "seed": self.seed, "stage": self.cur.stage,
            "stage_history": self.cur.history,
            "capture_count_train": self.capture_count_train}))


# -------------------------------------------------------------- warm start ---
def load_warm(runner: M3ARunner, ckpt_dir: pathlib.Path, tag: str,
              device: str) -> dict:
    """Warm-start arm (docs/11 SS3): actor/critic/value-norm weights + FROZEN
    obs-norm state from a mix-0.5 L2 checkpoint into the fresh trainer.
    Optimizer stays FRESH (new reward landscape; documented decision).
    obs_dim/n_limiters must match exactly (the M3 env keeps the 63-dim obs)."""
    import hashlib
    ckpt_path = ckpt_dir / f"ckpt_mappo_{tag}.pt"
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    if int(ckpt["obs_dim"]) != runner.obs_dim or int(ckpt["n_limiters"]) != runner.n:
        raise ValueError(
            f"warm-start shape mismatch: ckpt (obs {ckpt['obs_dim']}, "
            f"n {ckpt['n_limiters']}) vs env (obs {runner.obs_dim}, n {runner.n})")
    runner.tr.lim_actor.load_state_dict(ckpt["lim_actor"])
    runner.tr.fin_actor.load_state_dict(ckpt["fin_actor"])
    runner.tr.critic.load_state_dict(ckpt["critic"])
    if ckpt.get("value_norm") is not None and runner.tr.value_norm is not None:
        runner.tr.value_norm.load_state_dict(ckpt["value_norm"])
    norm_path = ckpt_dir / f"obs_norm_{tag}.json"
    runner.norm.load_state_dict(json.loads(norm_path.read_text()))
    sha = hashlib.sha256(ckpt_path.read_bytes()).hexdigest()[:12]
    return {"warm_ckpt": str(ckpt_path), "warm_ckpt_sha256_12": sha,
            "warm_tag": tag, "optimizer": "fresh"}


# --------------------------------------------------------------------- main ---
def run_one(run_cfg: dict, env_cfg: dict, seed: int, device: str,
            out_root: pathlib.Path, use_wandb: bool) -> dict:
    seed_everything(seed)
    loop = run_cfg["loop"]
    total = int(loop["total_env_steps"])
    eval_every = int(loop["eval_interval_updates"])
    save_every = int(loop.get("save_interval_updates", eval_every))
    eval_eps = int(loop["eval_episodes"])
    anneal = str(loop.get("lr_anneal", "none")).lower()
    anneal_floor = float(loop.get("lr_anneal_floor", 0.0))
    out_dir = out_root / f"seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    runner = M3ARunner(env_cfg, run_cfg, seed, device)
    n_updates = max(1, total // runner.rollout_env_steps)

    ws = run_cfg.get("warm_start", {}) or {}
    arm = "warm" if bool(ws.get("enabled", False)) else "scratch"
    warm_meta = {}
    if arm == "warm":
        warm_meta = load_warm(runner, pathlib.Path(ws["ckpt_dir"]),
                              str(ws.get("tag", "best")), device)
        print(f"[warm] loaded {warm_meta['warm_ckpt']} "
              f"(sha {warm_meta['warm_ckpt_sha256_12']}, fresh optimizer)")

    wb = None
    if use_wandb:
        try:
            import wandb
            wcfg = run_cfg.get("wandb", {})
            wb = wandb.init(project=wcfg.get("project", "newurp-l2"),
                            group=wcfg.get("group", "m3a"),
                            name=f"m3a_{arm}_seed{seed}",
                            config={"seed": seed, "device": device, "arm": arm,
                                    "run_cfg": run_cfg})
        except Exception as e:
            print(f"[wandb disabled] {type(e).__name__}: {e}")
            wb = None

    # baselines on the FROZEN M3 env (judgment comparators)
    ctx = make_scripted_ctx(env_cfg)
    baselines = {
        "hold_position": m3_eval_bundle(env_cfg, runner.m3, *hold_bundle(ctx),
                                        episodes=eval_eps, seed0=runner.eval_seed0),
        "scripted_shaping": m3_eval_bundle(env_cfg, runner.m3, *scripted_bundle(ctx),
                                           episodes=eval_eps, seed0=runner.eval_seed0),
    }
    (out_dir / "baselines.json").write_text(json.dumps(baselines, indent=2))
    base_best = max(v["return_mean"] for v in baselines.values())
    for name, v in baselines.items():
        print(f"[baseline {name}] return={v['return_mean']:.3f}"
              f"+-{v['return_std']:.3f} clean={v['clean_cross_rate']:.2f} "
              f"captured={v['captured_rate']:.2f}")

    ntfy(f"m3a {arm} seed {seed}: START (o*={runner.m3.o_star:g}, "
         f"mode={runner.cur.mode}, total={total})")

    eval_curve, train_curve = [], []
    best3 = float("-inf")
    t0 = time.monotonic()
    for upd in range(1, n_updates + 1):
        lr_frac = 1.0
        if anneal == "linear":
            lr_frac = (anneal_floor + (1.0 - anneal_floor)
                       * (1.0 - (upd - 1) / n_updates))
            runner.tr.set_lr(runner.tr.cfg.lr * lr_frac)
        runner.collect_rollout()
        stats = runner.update()
        roll = runner.rolling()
        sps = runner.env_steps / max(time.monotonic() - t0, 1e-9)
        train_curve.append({"step": runner.env_steps, "stage": runner.cur.stage,
                            **{k: roll.get(k, float("nan")) for k in
                               ("train/ep_return", "train/captured_rate",
                                "train/clean_cross_rate", "train/boxed_frac",
                                "train/wasted")}})
        if wb:
            wb.log({**stats, **roll, "perf/env_steps_per_sec": sps,
                    "perf/lr_frac": lr_frac,
                    "curriculum/stage_idx": {"s1": 1, "s2": 2, "s3": 3}[runner.cur.stage]},
                   step=runner.env_steps)
        print(f"[seed {seed}|{arm}|{runner.cur.stage}] upd {upd}/{n_updates} "
              f"step={runner.env_steps} "
              f"ep_ret={roll.get('train/ep_return', float('nan')):.3f} "
              f"clean={roll.get('train/clean_cross_rate', float('nan')):.2f} "
              f"cap={roll.get('train/captured_rate', float('nan')):.2f} "
              f"kl_l={stats['limiter/approx_kl']:.4f} ev={stats['critic/explained_var']:.2f} "
              f"sps={sps:.1f}")

        if upd % eval_every == 0 or upd == n_updates:
            frozen_ev, train_ev = runner.evaluate(eval_eps)
            transition = runner.cur.on_eval(runner.env_steps, train_ev, frozen_ev)
            if transition:
                print(f"  [curriculum] -> {transition} at step {runner.env_steps}")
                ntfy(f"m3a {arm} seed {seed}: stage -> {transition} "
                     f"@ {runner.env_steps}")
            margin = frozen_ev["return_mean"] - base_best
            point = {"step": runner.env_steps, "stage": runner.cur.stage,
                     "cur": runner.cur.describe(),
                     "dod_margin": margin,
                     **{k: v for k, v in frozen_ev.items() if k != "fire_chains"},
                     "fire_chains": frozen_ev["fire_chains"],
                     "train_eval": {k: v for k, v in train_ev.items()
                                    if k != "fire_chains"}}
            eval_curve.append(point)
            roll3 = float(np.mean([p["sel_score"] for p in eval_curve[-3:]]))
            if roll3 > best3:
                best3 = roll3
                runner.save(out_dir, tag="best")
                (out_dir / "best.json").write_text(json.dumps(
                    {"step": runner.env_steps, "last3_sel_score": roll3,
                     "clean_cross_rate": frozen_ev["clean_cross_rate"],
                     "return_mean": frozen_ev["return_mean"]}))
            print(f"  [eval/frozen] ret={frozen_ev['return_mean']:.3f} "
                  f"clean={frozen_ev['clean_cross_rate']:.2f} "
                  f"cap={frozen_ev['captured_rate']:.2f}({frozen_ev['capture_count']}) "
                  f"fire={frozen_ev['fire_rate']:.2f} "
                  f"boxed_fire={frozen_ev['boxed_fire_rate']:.2f} "
                  f"score={frozen_ev['sel_score']:+.3f} margin={margin:+.3f}")
            if train_ev is not frozen_ev:
                print(f"  [eval/train-stage] clean={train_ev['clean_cross_rate']:.2f} "
                      f"fire={train_ev['fire_rate']:.2f} "
                      f"boxed_fire={train_ev['boxed_fire_rate']:.2f} "
                      f"o_near={train_ev['o_near_rate_mean']:.3f}")
            if wb:
                wb.log({**{f"eval/{k}": v for k, v in point.items()
                           if isinstance(v, (int, float))},
                        **{f"eval_train/{k}": v for k, v in point["train_eval"].items()
                           if isinstance(v, (int, float))}},
                       step=runner.env_steps)
            (out_dir / "eval_curve.json").write_text(json.dumps(eval_curve, indent=2))
            (out_dir / "train_curve.json").write_text(json.dumps(train_curve, indent=2))
        if upd % save_every == 0 or upd == n_updates:
            runner.save(out_dir, tag="latest")

    lastk = eval_curve[-3:]
    def _l3(key):
        return float(np.mean([p[key] for p in lastk])) if lastk else float("nan")
    summary = {
        "seed": seed, "arm": arm, "env_steps": runner.env_steps,
        "o_star": runner.m3.o_star, "curriculum_mode": runner.cur.mode,
        "stage_final": runner.cur.stage, "stage_history": runner.cur.history,
        "warm": warm_meta, "baselines": baselines,
        "final_eval": {k: v for k, v in (eval_curve[-1] if eval_curve else {}).items()
                       if k != "fire_chains"},
        "clean_cross_rate_last3": _l3("clean_cross_rate"),
        "captured_rate_last3": _l3("captured_rate"),
        "boxed_fire_rate_last3": _l3("boxed_fire_rate"),
        "sel_score_last3": _l3("sel_score"),
        "return_mean_last3": _l3("return_mean"),
        "dod_margin_last3": _l3("dod_margin"),
        "capture_count_eval_total": int(sum(p["capture_count"] for p in eval_curve)),
        "capture_count_train_total": runner.capture_count_train,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    ntfy(f"m3a {arm} seed {seed}: DONE clean_last3="
         f"{summary['clean_cross_rate_last3']:.3f} "
         f"cap_eval={summary['capture_count_eval_total']} "
         f"cap_train={summary['capture_count_train_total']} "
         f"score={summary['sel_score_last3']:+.3f}")
    if wb:
        wb.summary["clean_cross_rate_last3"] = summary["clean_cross_rate_last3"]
        wb.summary["sel_score_last3"] = summary["sel_score_last3"]
        wb.finish()
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description="M3a capture-unlock trainer (docs/11)")
    ap.add_argument("--config", default="configs/m3a_s1_scratch.yaml")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", type=int, nargs="+", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--output", default="results/m3a")
    ap.add_argument("--total-env-steps", type=int, default=None)
    ap.add_argument("--eval-episodes", type=int, default=None)
    ap.add_argument("--o-star", type=float, default=None,
                    help="S1-limited o* sweep override (scaffold selection "
                         "ONLY, docs/11 SS2; {3e-4, 1e-3, 3e-3})")
    ap.add_argument("--no-wandb", action="store_true")
    ap.add_argument("--no-randomize", action="store_true")
    args = ap.parse_args()

    run_cfg = yaml.safe_load(open(pathlib.Path(args.config)))
    env_cfg = yaml.safe_load(open(pathlib.Path(run_cfg["env_config"])))
    if args.total_env_steps is not None:
        run_cfg["loop"]["total_env_steps"] = args.total_env_steps
    if args.eval_episodes is not None:
        run_cfg["loop"]["eval_episodes"] = args.eval_episodes
    if args.o_star is not None:
        if str(run_cfg["curriculum"]["mode"]) != "s1_only":
            raise SystemExit("--o-star is S1-sweep only (docs/11 SS2): "
                             "curriculum.mode must be s1_only")
        run_cfg["m3"]["o_star"] = float(args.o_star)
    if args.no_randomize and run_cfg.get("randomize"):
        run_cfg["randomize"]["enabled"] = False
    use_wandb = (not args.no_wandb) and bool(
        run_cfg.get("wandb", {}).get("enabled", True))

    seeds = args.seeds if args.seeds is not None else [args.seed]
    out_root = pathlib.Path(args.output)
    results = [run_one(run_cfg, env_cfg, s, args.device, out_root, use_wandb)
               for s in seeds]

    print("\n=== m3a summary (last-3 frozen-eval means; judgment = P1 held-out"
          " harness on the fixed best ckpt, docs/11 SS4) ===")
    for res in results:
        print(f"  seed {res['seed']} [{res['arm']}]: "
              f"clean={res['clean_cross_rate_last3']:.3f} "
              f"cap_rate={res['captured_rate_last3']:.3f} "
              f"boxed_fire={res['boxed_fire_rate_last3']:.3f} "
              f"score={res['sel_score_last3']:+.3f} "
              f"cap_total(train+eval)={res['capture_count_train_total']}"
              f"+{res['capture_count_eval_total']}")


if __name__ == "__main__":
    main()
