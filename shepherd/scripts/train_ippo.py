"""Phase 2B IPPO runner on the frozen shepherd env (docs/09 SS5 Phase 2B).

Independent PPO, decentralized critics -- limiter = ONE parameter-shared
Phase-1 ``PPOTrainer`` (+ one-hot agent id), finisher = ``MixedPPOTrainer``
(Gaussian net-axis + Bernoulli fire head). No central critic; ``env.state()``
is deliberately unconsumed (2C). Design decisions recorded in docs/09 SS8.

CLI (config/CLI driven; lab-portable, nothing hardcoded):
    python -m shepherd.scripts.train_ippo --config configs/l2_ippo.yaml \
        --seed 0 --device cuda --output results/ippo

2B specifics implemented here:
  * obs running-normalizer (docs/09 SS7.1) -- updated once per env step on the
    shared full-state obs; frozen during eval; checkpointed alongside weights.
  * policies act in NORMALIZED [-1, 1] space; this runner scales to the env
    Box bounds (see shepherd/train/ippo.py module docstring for why).
  * gamma/lam are RESET for the 80-step corridor via configs/l2_ippo.yaml
    (Pendulum's gamma=0.9 was a toy tuning; docs/09 SS7.1).
  * per-episode scripted-attacker FAMILY randomization (docs/09 SS7 item (c)
    step 1) -- TRAIN only; eval always runs the nominal ratified env so the
    baseline comparison stays apples-to-apples.
  * eval compares the learned bundle vs the hold_position and scripted-shaping
    baselines on the SAME eval seeds (2B DoD: significant exceedance).
  * wandb logging from 2B on (optional + offline-friendly: on the lab nodes
    keep ``export WANDB_MODE=offline``); JSON curves are always written.

Global seeding is runner-owned (shepherd/train/ppo.py contract): this module's
``seed_everything`` replicates train_ppo_toy's. Reproducibility is CPU-only;
CUDA runs reproduce only approximately (docs/09 SS7.1).
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import random
import time
from typing import Callable, Dict, List, Optional

import numpy as np
import torch
import yaml

from shepherd.agents import baselines as B
from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.attacker_rand import build_attacker_env, sample_attacker_params
from shepherd.train.ippo import MixedPPOTrainer, limiter_inputs
from shepherd.train.make_env import make_train_env
from shepherd.train.obs_norm import RunningNorm
from shepherd.train.ppo import PPOConfig, PPOTrainer, RolloutBuffer


def seed_everything(seed: int, deterministic: bool = True) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if deterministic:
        torch.use_deterministic_algorithms(True, warn_only=True)


# --------------------------------------------------------------- obs slices ---
def _pv(obs: np.ndarray, slot: int):
    """(position, velocity) of kinematic slot ``slot`` in the 9-per-agent obs
    layout [limiter_0..N-1, finisher (slot N), adversary (slot N+1)]."""
    o = np.asarray(obs, dtype=float)
    b = 9 * slot
    return o[b : b + 3], o[b + 3 : b + 6]


# ---------------------------------------------------------- policy bundles ---
# A bundle is (limiter_fn, finisher_fn):
#   limiter_fn(obs, flags)  -> (N, 3)  live limiter actions (env units)
#   finisher_fn(obs, flags) -> (4,)    live finisher action [axis(3), fire]
# ``flags`` is the previous StepResult.flags dict ({} on the first step).
def make_scripted_ctx(env_cfg: dict) -> dict:
    return {
        "n": int(env_cfg["scenario"]["n_limiters"]),
        "tau": float(env_cfg["physics"]["tau_deploy"]),
        "a_max": float(env_cfg["physics"]["a_lim_max"]),
        "dt": float(env_cfg["physics"]["dt"]),
        "r_ring": float(env_cfg["train"]["layout"]["r_ring"]),
    }


def hold_bundle(ctx: dict):
    def limiter_fn(obs, flags):
        return np.zeros((ctx["n"], 3), dtype=np.float32)

    return limiter_fn, scripted_finisher_fn(ctx)


def scripted_bundle(ctx: dict):
    n = ctx["n"]

    def limiter_fn(obs, flags):
        p_att, v_att = _pv(obs, n + 1)
        acts = []
        for i in range(n):
            p_lim, v_lim = _pv(obs, i)
            box4 = B.scripted_shaping_limiter(
                i, n, p_lim, v_lim, p_att, v_att,
                tau=ctx["tau"], a_max=ctx["a_max"], r_ring=ctx["r_ring"],
                dt=ctx["dt"])
            acts.append(box4[:3])
        return np.asarray(acts, dtype=np.float32)

    return limiter_fn, scripted_finisher_fn(ctx)


def scripted_finisher_fn(ctx: dict) -> Callable:
    n = ctx["n"]

    def finisher_fn(obs, flags):
        p_fin, _ = _pv(obs, n)
        p_att, v_att = _pv(obs, n + 1)
        box5 = B.scripted_finisher(
            p_fin, p_att, v_att, tau=ctx["tau"],
            clean_threshold_crossed=bool(
                flags.get("clean_net_threshold_crossed", False)))
        return box5[[0, 1, 2, 4]].astype(np.float32)   # live dims (slew reserved)

    return finisher_fn


def eval_bundle(env_cfg: dict, limiter_fn: Callable, finisher_fn: Callable,
                episodes: int, seed0: int) -> dict:
    """Deterministic bundle evaluation on the NOMINAL ratified env (no attacker
    randomization) with fixed seeds -- comparable across bundles."""
    env, _, _ = make_train_env(copy.deepcopy(env_cfg))
    ad = ShepherdAdapter(env)
    recs = []
    for ep in range(episodes):
        obs_d, _ = ad.reset(seed=seed0 + ep)
        obs = obs_d[ad.limiter_ids[0]]
        flags: Dict[str, object] = {}
        ret = head = 0.0
        steps = 0
        clean = False
        while True:
            lim = limiter_fn(obs, flags)
            live = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.asarray(finisher_fn(obs, flags), np.float32)
            r = ad.step(live)
            ret += r.rewards[ad.finisher_id]
            head += r.headline
            clean = clean or bool(r.flags["clean_net_threshold_crossed"])
            flags = r.flags
            obs = r.obs[ad.limiter_ids[0]]
            steps += 1
            if r.done:
                break
        recs.append({
            "ret": ret, "len": steps, "headline_sum": head, "clean": clean,
            "wasted": float(r.flags["wasted_fire"]),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
        })
    rets = np.array([x["ret"] for x in recs], dtype=float)
    return {
        "episodes": episodes,
        "return_mean": float(rets.mean()),
        "return_std": float(rets.std()),
        "len_mean": float(np.mean([x["len"] for x in recs])),
        "headline_sum_mean": float(np.mean([x["headline_sum"] for x in recs])),
        "wasted_mean": float(np.mean([x["wasted"] for x in recs])),
        "captured_rate": float(np.mean([x["captured"] for x in recs])),
        "penetrated_rate": float(np.mean([x["penetrated"] for x in recs])),
        "clean_cross_rate": float(np.mean([x["clean"] for x in recs])),
    }


# --------------------------------------------------------------- the runner ---
class IPPORunner:
    """Owns the two role learners, the obs normalizer, the per-episode attacker
    family randomization, and rollout collection into the two buffers."""

    def __init__(self, env_cfg: dict, run_cfg: dict, seed: int, device: str):
        self.env_cfg = env_cfg
        loop = run_cfg["loop"]
        self.rollout_env_steps = int(loop["rollout_env_steps"])
        self.seed = int(seed)

        # dims / bounds from a throwaway nominal env
        env, _, _ = make_train_env(copy.deepcopy(env_cfg))
        ad = ShepherdAdapter(env)
        self.n = len(ad.limiter_ids)
        self.obs_dim = ad.obs_dim
        lim_low, lim_high = ad.action_bounds(ad.limiter_ids[0])
        fin_low, fin_high = ad.action_bounds(ad.finisher_id)
        if not (np.allclose(lim_low, -lim_high) and np.allclose(fin_low[:3], -fin_high[:3])):
            raise ValueError("action Boxes are expected symmetric for [-1,1] scaling")
        self.lim_scale = lim_high.astype(np.float32)          # (3,) == a_lim_max
        self.fin_axis_scale = fin_high[:3].astype(np.float32)  # (3,) == 1.0

        self.norm = RunningNorm(self.obs_dim)

        total = int(loop["total_env_steps"])
        cfg_l = PPOConfig.from_dict({**run_cfg["ppo_limiter"], "seed": seed,
                                     "device": device,
                                     "rollout_steps": self.rollout_env_steps * self.n,
                                     "total_timesteps": total * self.n})
        cfg_f = PPOConfig.from_dict({**run_cfg["ppo_finisher"], "seed": seed + 1,
                                     "device": device,
                                     "rollout_steps": self.rollout_env_steps,
                                     "total_timesteps": total})
        self.lim_tr = PPOTrainer(self.obs_dim + self.n, 3, cfg_l)
        self.fin_tr = MixedPPOTrainer(self.obs_dim, 4, cfg_f)
        self.buf_l = RolloutBuffer(self.rollout_env_steps * self.n,
                                   self.obs_dim + self.n, 3)
        self.buf_f = RolloutBuffer(self.rollout_env_steps, self.obs_dim, 4)

        self.rand_cfg = run_cfg.get("randomize")
        self.rand_rng = np.random.default_rng(seed * 9973 + 17)  # family stream
        self.base_seed = seed * 1_000_003 + 1                    # train episode seeds
        self.eval_seed0 = seed * 1_000_003 + 500_000             # disjoint eval seeds

        self.env_steps = 0
        self.ep_records: List[dict] = []
        self._ep_idx = 0
        self._adapter: Optional[ShepherdAdapter] = None
        self._obs: Optional[np.ndarray] = None
        self._ep: Dict[str, float] = {}

    # ------------------------------------------------------------ episodes ---
    def _begin_episode(self) -> None:
        params = sample_attacker_params(self.rand_cfg, self.rand_rng)
        env, _, _ = build_attacker_env(self.env_cfg, params)
        self._adapter = ShepherdAdapter(env)
        obs_d, _ = self._adapter.reset(seed=self.base_seed + self._ep_idx)
        self._obs = obs_d[self._adapter.limiter_ids[0]]
        self._ep = {"ret": 0.0, "headline": 0.0, "limiter_loss": 0.0,
                    "coma_sum": 0.0, "fire_events": 0.0, "steps": 0.0,
                    "clean": 0.0}
        self._ep_params = params

    def _finish_episode(self, r) -> None:
        steps = max(self._ep["steps"], 1.0)
        self.ep_records.append({
            "ret": self._ep["ret"], "len": int(steps),
            "headline_sum": self._ep["headline"],
            "coma_D_mean": self._ep["coma_sum"] / steps,
            "limiter_loss_sum": self._ep["limiter_loss"],
            "fire_events": self._ep["fire_events"],
            "clean": bool(self._ep["clean"]),
            "wasted": float(r.flags["wasted_fire"]),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
            "truncated": bool(r.truncated),
            "attacker_params": dict(self._ep_params),
        })
        if len(self.ep_records) > 500:
            del self.ep_records[:-500]
        self._ep_idx += 1

    # ------------------------------------------------------------- rollout ---
    def collect_rollout(self) -> None:
        if self._adapter is None:
            self._begin_episode()
        device = self.lim_tr.device
        for _ in range(self.rollout_env_steps):
            ad = self._adapter
            obs = self._obs
            nobs = self.norm.normalize(obs, update=True)

            x_l = limiter_inputs(nobs, self.n)                     # (N, obs+N)
            t_l = torch.as_tensor(x_l, device=device)
            raw_l_t, logp_l, val_l = self.lim_tr.ac.act(t_l)
            raw_l = raw_l_t.cpu().numpy()
            clip_l = np.clip(raw_l, -1.0, 1.0)

            t_f = torch.as_tensor(nobs[None, :], device=device)
            raw_f_t, logp_f, val_f = self.fin_tr.ac.act(t_f)
            raw_f = raw_f_t[0].cpu().numpy()
            clip_f = raw_f.copy()
            clip_f[:3] = np.clip(raw_f[:3], -1.0, 1.0)             # fire untouched

            live = {lid: (clip_l[i] * self.lim_scale).astype(np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.concatenate(
                [clip_f[:3] * self.fin_axis_scale, clip_f[3:]]).astype(np.float32)

            r = ad.step(live)
            next_obs = r.obs[ad.limiter_ids[0]]

            if r.terminated:                       # true terminal: bootstrap 0
                nv_l = np.zeros(self.n, dtype=np.float64)
                nv_f = 0.0
            else:                                  # truncation OR continuing:
                nnobs = self.norm.normalize(next_obs)   # V(final_obs)/V(next_obs)
                with torch.no_grad():
                    nv_l = self.lim_tr.ac.value(
                        torch.as_tensor(limiter_inputs(nnobs, self.n),
                                        device=device)).cpu().numpy()
                    nv_f = float(self.fin_tr.ac.value(
                        torch.as_tensor(nnobs[None, :], device=device))[0].item())

            done = 1.0 if r.done else 0.0
            for i, lid in enumerate(ad.limiter_ids):
                self.buf_l.add(obs=x_l[i], raw_action=raw_l[i], env_action=clip_l[i],
                               log_prob=float(logp_l[i].item()),
                               value=float(val_l[i].item()),
                               reward=r.rewards[lid],
                               next_value=float(nv_l[i]), done=done)
            self.buf_f.add(obs=nobs, raw_action=raw_f, env_action=clip_f,
                           log_prob=float(logp_f[0].item()),
                           value=float(val_f[0].item()),
                           reward=r.rewards[ad.finisher_id],
                           next_value=nv_f, done=done)

            self._ep["ret"] += r.rewards[ad.finisher_id]
            self._ep["headline"] += r.headline
            self._ep["limiter_loss"] += float(r.flags["limiter_loss"])
            self._ep["coma_sum"] += float(np.mean(list(r.coma_D.values())))
            self._ep["fire_events"] += 1.0 if r.flags["fire_event"] else 0.0
            self._ep["clean"] = max(self._ep["clean"],
                                    1.0 if r.flags["clean_net_threshold_crossed"] else 0.0)
            self._ep["steps"] += 1.0
            self.env_steps += 1

            if r.done:
                self._finish_episode(r)
                self._begin_episode()
            else:
                self._obs = next_obs

    def update(self) -> Dict[str, float]:
        s_l = self.lim_tr.update(self.buf_l)
        s_f = self.fin_tr.update(self.buf_f)
        self.buf_l.reset()
        self.buf_f.reset()
        out = {f"limiter/{k}": v for k, v in s_l.items()}
        out.update({f"finisher/{k}": v for k, v in s_f.items()})
        return out

    def rolling(self, k: int = 20) -> Dict[str, float]:
        recs = self.ep_records[-k:]
        if not recs:
            return {}
        return {
            "train/ep_return": float(np.mean([x["ret"] for x in recs])),
            "train/ep_len": float(np.mean([x["len"] for x in recs])),
            "train/headline_sum": float(np.mean([x["headline_sum"] for x in recs])),
            "train/coma_D_mean": float(np.mean([x["coma_D_mean"] for x in recs])),
            "train/limiter_loss_sum": float(np.mean([x["limiter_loss_sum"] for x in recs])),
            "train/fire_events": float(np.mean([x["fire_events"] for x in recs])),
            "train/wasted": float(np.mean([x["wasted"] for x in recs])),
            "train/captured_rate": float(np.mean([x["captured"] for x in recs])),
            "train/penetrated_rate": float(np.mean([x["penetrated"] for x in recs])),
            "train/clean_cross_rate": float(np.mean([x["clean"] for x in recs])),
        }

    # ----------------------------------------------------------- eval / io ---
    def learned_bundle(self):
        device = self.lim_tr.device

        def limiter_fn(obs, flags):
            nobs = self.norm.normalize(obs)                 # frozen stats
            t = torch.as_tensor(limiter_inputs(nobs, self.n), device=device)
            raw, _, _ = self.lim_tr.ac.act(t, deterministic=True)
            return (np.clip(raw.cpu().numpy(), -1.0, 1.0)
                    * self.lim_scale).astype(np.float32)

        def finisher_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(nobs[None, :], device=device)
            raw, _, _ = self.fin_tr.ac.act(t, deterministic=True)
            raw = raw[0].cpu().numpy()
            axis = np.clip(raw[:3], -1.0, 1.0) * self.fin_axis_scale
            return np.concatenate([axis, raw[3:]]).astype(np.float32)

        return limiter_fn, finisher_fn

    def evaluate(self, episodes: int) -> dict:
        lim_fn, fin_fn = self.learned_bundle()
        return eval_bundle(self.env_cfg, lim_fn, fin_fn, episodes, self.eval_seed0)

    def save(self, out_dir: pathlib.Path, tag: str = "latest") -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.lim_tr.save(out_dir / f"ckpt_limiter_{tag}.pt")
        self.fin_tr.save(out_dir / f"ckpt_finisher_{tag}.pt")
        (out_dir / f"obs_norm_{tag}.json").write_text(
            json.dumps(self.norm.state_dict()))
        (out_dir / f"run_state_{tag}.json").write_text(json.dumps({
            "env_steps": self.env_steps, "episodes": self._ep_idx,
            "seed": self.seed}))


# --------------------------------------------------------------------- main ---
def run_one(run_cfg: dict, env_cfg: dict, seed: int, device: str,
            out_root: pathlib.Path, use_wandb: bool) -> dict:
    seed_everything(seed)
    loop = run_cfg["loop"]
    total = int(loop["total_env_steps"])
    eval_every = int(loop["eval_interval_updates"])
    save_every = int(loop.get("save_interval_updates", eval_every))
    eval_eps = int(loop["eval_episodes"])
    # 2B stabilization (docs/09 SS8): "linear" anneals both roles' LR to 0 over
    # the run -- late-training policy drift shrinks so the policy freezes into
    # one behavior basin instead of oscillating between them.
    anneal = str(loop.get("lr_anneal", "none")).lower()
    out_dir = out_root / f"seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    runner = IPPORunner(env_cfg, run_cfg, seed, device)
    n_updates = max(1, total // runner.rollout_env_steps)

    wb = None
    if use_wandb:
        try:
            import wandb
            wcfg = run_cfg.get("wandb", {})
            wb = wandb.init(project=wcfg.get("project", "newurp-l2"),
                            group=wcfg.get("group", "phase2b-ippo"),
                            name=f"ippo_seed{seed}",
                            config={"seed": seed, "device": device,
                                    "run_cfg": run_cfg})
        except Exception as e:                        # offline node / not installed
            print(f"[wandb disabled] {type(e).__name__}: {e}")
            wb = None

    # scripted baselines on the SAME eval seeds (2B DoD comparators)
    ctx = make_scripted_ctx(env_cfg)
    baselines = {
        "hold_position": eval_bundle(env_cfg, *hold_bundle(ctx),
                                     episodes=eval_eps, seed0=runner.eval_seed0),
        "scripted_shaping": eval_bundle(env_cfg, *scripted_bundle(ctx),
                                        episodes=eval_eps, seed0=runner.eval_seed0),
    }
    (out_dir / "baselines.json").write_text(json.dumps(baselines, indent=2))
    base_best = max(v["return_mean"] for v in baselines.values())
    for name, v in baselines.items():
        print(f"[baseline {name}] return={v['return_mean']:.3f}"
              f"+-{v['return_std']:.3f} captured={v['captured_rate']:.2f}"
              f" wasted={v['wasted_mean']:.2f} clean={v['clean_cross_rate']:.2f}")
    if wb:
        wb.summary["baseline_hold_return"] = baselines["hold_position"]["return_mean"]
        wb.summary["baseline_scripted_return"] = baselines["scripted_shaping"]["return_mean"]

    eval_curve, train_curve = [], []
    t0 = time.monotonic()
    for upd in range(1, n_updates + 1):
        lr_frac = 1.0
        if anneal == "linear":
            lr_frac = 1.0 - (upd - 1) / n_updates
            runner.lim_tr.set_lr(runner.lim_tr.cfg.lr * lr_frac)
            runner.fin_tr.set_lr(runner.fin_tr.cfg.lr * lr_frac)
        runner.collect_rollout()
        stats = runner.update()
        roll = runner.rolling()
        sps = runner.env_steps / max(time.monotonic() - t0, 1e-9)
        train_curve.append({"step": runner.env_steps,
                            **{k: roll.get(k, float("nan")) for k in
                               ("train/ep_return", "train/captured_rate",
                                "train/penetrated_rate", "train/wasted")}})
        if wb:
            wb.log({**stats, **roll, "perf/env_steps_per_sec": sps,
                    "perf/lr_frac": lr_frac},
                   step=runner.env_steps)
        print(f"[seed {seed}] upd {upd}/{n_updates} step={runner.env_steps} "
              f"ep_ret={roll.get('train/ep_return', float('nan')):.3f} "
              f"cap={roll.get('train/captured_rate', float('nan')):.2f} "
              f"kl_l={stats['limiter/approx_kl']:.4f} "
              f"kl_f={stats['finisher/approx_kl']:.4f} sps={sps:.1f}")

        if upd % eval_every == 0 or upd == n_updates:
            ev = runner.evaluate(eval_eps)
            margin = ev["return_mean"] - base_best
            eval_curve.append({"step": runner.env_steps, **ev,
                               "dod_margin": margin})
            print(f"  [eval] return={ev['return_mean']:.3f}+-{ev['return_std']:.3f} "
                  f"captured={ev['captured_rate']:.2f} wasted={ev['wasted_mean']:.2f} "
                  f"clean={ev['clean_cross_rate']:.2f} DoD_margin={margin:+.3f}")
            if wb:
                wb.log({f"eval/{k}": v for k, v in ev.items()
                        if isinstance(v, (int, float))} |
                       {"eval/dod_margin": margin}, step=runner.env_steps)
            (out_dir / "eval_curve.json").write_text(json.dumps(eval_curve, indent=2))
            (out_dir / "train_curve.json").write_text(json.dumps(train_curve, indent=2))
        if upd % save_every == 0 or upd == n_updates:
            runner.save(out_dir, tag="latest")

    final = eval_curve[-1] if eval_curve else {}
    # Judgment metric = mean of the LAST 3 evals, not the final snapshot: a
    # single deterministic eval point is hostage to PPO policy oscillation
    # (2B run 1, seed 0 -- docs/09 SS8). NaN-safe on short smoke runs.
    lastk = eval_curve[-3:]
    margin_last3 = (float(np.mean([p["dod_margin"] for p in lastk]))
                    if lastk else float("nan"))
    return_last3 = (float(np.mean([p["return_mean"] for p in lastk]))
                    if lastk else float("nan"))
    summary = {"seed": seed, "env_steps": runner.env_steps,
               "final_eval": final, "baselines": baselines,
               "dod_margin": final.get("dod_margin", float("nan")),
               "dod_margin_last3": margin_last3,
               "return_mean_last3": return_last3}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    maybe_plot(eval_curve, baselines, out_dir)
    if wb:
        wb.summary["final_eval_return"] = final.get("return_mean", float("nan"))
        wb.summary["dod_margin"] = final.get("dod_margin", float("nan"))
        wb.finish()
    return summary


def maybe_plot(eval_curve: list, baselines: dict, out_dir: pathlib.Path) -> None:
    if not eval_curve:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    steps = [p["step"] for p in eval_curve]
    ax.plot(steps, [p["return_mean"] for p in eval_curve], marker="o",
            label="IPPO (deterministic eval)")
    for name, v in baselines.items():
        ax.axhline(v["return_mean"], linestyle="--", alpha=0.7, label=name)
    ax.set_xlabel("env steps")
    ax.set_ylabel("eval return (J sum, nominal env)")
    ax.set_title("Phase 2B IPPO vs scripted baselines")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "eval_curves.png", dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 2B IPPO trainer (shepherd env)")
    ap.add_argument("--config", default="configs/l2_ippo.yaml")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="run multiple seeds sequentially (overrides --seed)")
    ap.add_argument("--device", default="cpu", help="cpu | cuda")
    ap.add_argument("--output", default="results/ippo")
    ap.add_argument("--total-env-steps", type=int, default=None,
                    help="override loop.total_env_steps (smoke runs)")
    ap.add_argument("--eval-episodes", type=int, default=None)
    ap.add_argument("--no-wandb", action="store_true")
    ap.add_argument("--no-randomize", action="store_true",
                    help="debug: disable attacker-family randomization")
    args = ap.parse_args()

    run_cfg = yaml.safe_load(open(pathlib.Path(args.config)))
    env_cfg = yaml.safe_load(open(pathlib.Path(run_cfg["env_config"])))
    if args.total_env_steps is not None:
        run_cfg["loop"]["total_env_steps"] = args.total_env_steps
    if args.eval_episodes is not None:
        run_cfg["loop"]["eval_episodes"] = args.eval_episodes
    if args.no_randomize and run_cfg.get("randomize"):
        run_cfg["randomize"]["enabled"] = False
    use_wandb = (not args.no_wandb) and bool(
        run_cfg.get("wandb", {}).get("enabled", True))

    seeds = args.seeds if args.seeds is not None else [args.seed]
    out_root = pathlib.Path(args.output)
    results = [run_one(run_cfg, env_cfg, s, args.device, out_root, use_wandb)
               for s in seeds]

    print("\n=== Phase 2B summary (DoD metric: LAST-3-EVAL MEAN margin > 0) ===")
    for res in results:
        fe = res["final_eval"]
        print(f"  seed {res['seed']}: last3_return="
              f"{res['return_mean_last3']:.3f} "
              f"last3_margin={res['dod_margin_last3']:+.3f} "
              f"(final point {res['dod_margin']:+.3f}) "
              f"captured={fe.get('captured_rate', float('nan')):.2f}")


if __name__ == "__main__":
    main()
