"""Toy-convergence runner for the from-scratch PPO core (L2 Phase 1).

Validates :mod:`shepherd.train.ppo` on a Gymnasium continuous-control toy env
(Pendulum-v1 by default; LunarLanderContinuous-v3 optional -- auto-skips if
box2d is absent). Uses a PLAIN env + manual reset loop: at a truncated step the
returned observation IS the true final observation, so bootstrapping
``V(final_obs)`` is unambiguous (verified against gymnasium 1.3.0 autoreset).

CLI (config/CLI driven -- nothing hardcoded, lab-portable):
    python -m shepherd.scripts.train_ppo_toy \
        --config configs/ppo_toy.yaml --seed 0 --device cpu \
        --output results/ppo_toy

Run several seeds for the DoD (>=3). Train (stochastic) and eval (deterministic
mean action) curves are saved separately under ``--output``.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random

import numpy as np
import torch
import yaml

from shepherd.train.ppo import PPOConfig, PPOTrainer, RolloutBuffer


def seed_everything(seed: int, deterministic: bool = True) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if deterministic:
        # CPU-deterministic reproducibility (CUDA is not bit-reproducible here).
        torch.use_deterministic_algorithms(True, warn_only=True)


def make_env(env_id: str):
    """Build the toy env; return None if an optional dependency is missing."""
    import gymnasium as gym

    try:
        return gym.make(env_id)
    except Exception as e:  # e.g. box2d not installed for LunarLander
        print(f"[skip] could not create env {env_id!r}: {type(e).__name__}: {e}")
        return None


@torch.no_grad()
def evaluate(trainer: PPOTrainer, env_id: str, episodes: int, seed: int) -> float:
    """Deterministic (mean-action) evaluation return, averaged over episodes."""
    env = make_env(env_id)
    if env is None:
        return float("nan")
    low = torch.as_tensor(env.action_space.low, device=trainer.device)
    high = torch.as_tensor(env.action_space.high, device=trainer.device)
    returns = []
    for ep in range(episodes):
        obs, _ = env.reset(seed=seed + 10_000 + ep)
        done = False
        ep_ret = 0.0
        while not done:
            obs_t = torch.as_tensor(obs, dtype=torch.float32, device=trainer.device)
            raw_action, _, _ = trainer.ac.act(obs_t, deterministic=True)
            env_action = torch.clamp(raw_action, low, high).cpu().numpy()
            obs, r, terminated, truncated, _ = env.step(env_action)
            ep_ret += float(r)
            done = terminated or truncated
        returns.append(ep_ret)
    env.close()
    return float(np.mean(returns))


def train(cfg: PPOConfig, env_id: str, eval_cfg: dict, out_dir: pathlib.Path) -> dict:
    seed_everything(cfg.seed)

    env = make_env(env_id)
    if env is None:
        return {"skipped": True, "env_id": env_id}

    obs_dim = int(np.prod(env.observation_space.shape))
    act_dim = int(np.prod(env.action_space.shape))
    low = torch.as_tensor(env.action_space.low, device=cfg.device)
    high = torch.as_tensor(env.action_space.high, device=cfg.device)

    trainer = PPOTrainer(obs_dim, act_dim, cfg)
    buf = RolloutBuffer(cfg.rollout_steps, obs_dim, act_dim)
    device = trainer.device

    train_curve, eval_curve = [], []
    ep_returns: list[float] = []
    ep_ret = 0.0

    obs, _ = env.reset(seed=cfg.seed)
    global_step = 0
    n_updates = max(1, cfg.total_timesteps // cfg.rollout_steps)

    for update in range(1, n_updates + 1):
        buf.reset()
        for _ in range(cfg.rollout_steps):
            obs_t = torch.as_tensor(obs, dtype=torch.float32, device=device)
            raw_action, log_prob, value = trainer.ac.act(obs_t)
            env_action = torch.clamp(raw_action, low, high).cpu().numpy()

            next_obs, reward, terminated, truncated, _ = env.step(env_action)
            done = bool(terminated or truncated)

            # Per-step bootstrap value (plain env => next_obs is the true final
            # obs on a truncated step).
            if terminated:
                next_value = 0.0
            else:  # truncated or continuing: bootstrap from next_obs
                with torch.no_grad():
                    nobs_t = torch.as_tensor(
                        next_obs, dtype=torch.float32, device=device
                    )
                    next_value = float(trainer.ac.value(nobs_t).item())

            buf.add(
                obs=obs,
                raw_action=raw_action.cpu().numpy(),
                env_action=env_action,
                log_prob=float(log_prob.item()),
                value=float(value.item()),
                reward=float(reward),
                next_value=next_value,
                done=float(done),
            )

            ep_ret += float(reward)
            global_step += 1
            if done:
                ep_returns.append(ep_ret)
                ep_ret = 0.0
                obs, _ = env.reset(seed=cfg.seed + global_step)
            else:
                obs = next_obs

        stats = trainer.update(buf)
        mean_train_ret = float(np.mean(ep_returns[-20:])) if ep_returns else float("nan")
        train_curve.append({"step": global_step, "mean_return": mean_train_ret})

        if update % int(eval_cfg.get("interval_updates", 5)) == 0 or update == n_updates:
            eval_ret = evaluate(
                trainer, env_id, int(eval_cfg.get("episodes", 10)), cfg.seed
            )
            eval_curve.append({"step": global_step, "eval_return": eval_ret})
            print(
                f"[{env_id} seed={cfg.seed}] upd {update}/{n_updates} "
                f"step={global_step} train_ret={mean_train_ret:.1f} "
                f"eval_ret={eval_ret:.1f} kl={stats['approx_kl']:.4f} "
                f"clipA={stats['clip_fraction_action']:.3f} log_std={stats['log_std']:.3f}"
            )

    env.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{env_id}_seed{cfg.seed}"
    (out_dir / f"train_curve_{tag}.json").write_text(json.dumps(train_curve, indent=2))
    (out_dir / f"eval_curve_{tag}.json").write_text(json.dumps(eval_curve, indent=2))

    # Save final weights (gitignored *.pt; reproducible from seed+config).
    ckpt_path = out_dir / f"ckpt_{tag}.pt"
    trainer.save(ckpt_path)

    final_eval = eval_curve[-1]["eval_return"] if eval_curve else float("nan")
    return {
        "skipped": False,
        "env_id": env_id,
        "seed": cfg.seed,
        "final_eval_return": final_eval,
        "ckpt": str(ckpt_path),
        "train_curve": train_curve,
        "eval_curve": eval_curve,
    }


def maybe_plot(results: list[dict], out_dir: pathlib.Path, env_id: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    for res in results:
        if res.get("skipped") or not res.get("eval_curve"):
            continue
        steps = [p["step"] for p in res["eval_curve"]]
        rets = [p["eval_return"] for p in res["eval_curve"]]
        ax.plot(steps, rets, marker="o", label=f"seed {res['seed']}")
    ax.set_xlabel("env steps")
    ax.set_ylabel("eval return (deterministic)")
    ax.set_title(f"From-scratch PPO -- {env_id}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / f"eval_curves_{env_id}.png", dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="From-scratch PPO toy convergence runner")
    ap.add_argument("--config", default="configs/ppo_toy.yaml")
    ap.add_argument("--seed", type=int, default=None, help="override config seed")
    ap.add_argument("--seeds", type=int, nargs="+", default=None,
                    help="run multiple seeds (overrides --seed)")
    ap.add_argument("--device", default=None, help="override config device")
    ap.add_argument("--env-id", default=None, help="override config env_id")
    ap.add_argument("--total-timesteps", type=int, default=None,
                    help="override for a quick smoke run")
    ap.add_argument("--output", default="results/ppo_toy")
    args = ap.parse_args()

    raw = yaml.safe_load(open(pathlib.Path(args.config)))
    env_id = args.env_id or raw.get("env_id", "Pendulum-v1")
    eval_cfg = raw.get("eval", {})
    base = dict(raw.get("ppo", {}))
    if args.device is not None:
        base["device"] = args.device
    if args.total_timesteps is not None:
        base["total_timesteps"] = args.total_timesteps

    if args.seeds is not None:
        seeds = args.seeds
    elif args.seed is not None:
        seeds = [args.seed]
    else:
        seeds = [base.get("seed", 0)]

    out_dir = pathlib.Path(args.output)
    results = []
    for s in seeds:
        cfg = PPOConfig.from_dict({**base, "seed": s})
        results.append(train(cfg, env_id, eval_cfg, out_dir))

    maybe_plot(results, out_dir, env_id)

    print("\n=== summary ===")
    for res in results:
        if res.get("skipped"):
            print(f"  {res['env_id']}: SKIPPED")
        else:
            print(f"  {res['env_id']} seed={res['seed']}: "
                  f"final_eval_return={res['final_eval_return']:.1f}")


if __name__ == "__main__":
    main()
