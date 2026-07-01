# PPO toy convergence (L2 Phase 1)

From-scratch single-agent PPO (`shepherd/train/ppo.py`, `shepherd/train/gae.py`)
validated on Pendulum-v1. This is the algorithmic foundation for the Phase-2
MAPPO/COMA trainer — no black-box RL library is used.

## Result (3 seeds, 300k env steps each)

| seed | final eval return (deterministic) |
|------|-----------------------------------|
| 0    | −131.4 |
| 1    | −185.8 |
| 2    | −156.4 |

Random baseline ≈ −1200…−1600. All seeds clear it by a wide margin, each passes
−300, and the eval curves rise monotonically (see `eval_curves_Pendulum-v1.png`).
Diagnostics behave: `approx_kl` ≈ 0.01, `clip_fraction_action` falls toward ~0.08
(policy stays in-bounds), `log_std` drops from 0 → ≈ −1.2 (policy sharpens).

DoD (`docs/09_learning_plan_log.md` §5) satisfied: return ≫ random + seed
reproducibility (seed 0 reproduced −131.4 across independent runs, CPU
deterministic mode).

## Reproduce

```bash
# 3 seeds, full run
python -m shepherd.scripts.train_ppo_toy --config configs/ppo_toy.yaml --seeds 0 1 2

# quick smoke
python -m shepherd.scripts.train_ppo_toy --config configs/ppo_toy.yaml --seed 0 \
    --total-timesteps 8192

# optional secondary env (needs box2d; auto-skips otherwise)
python -m shepherd.scripts.train_ppo_toy --config configs/ppo_toy.yaml \
    --env-id LunarLanderContinuous-v3 --seed 0
```

## Artifacts

- `train_curve_<env>_seed{k}.json` — stochastic rollout return vs step
- `eval_curve_<env>_seed{k}.json` — deterministic (mean-action) return vs step
- `eval_curves_<env>.png` — combined eval curves
- `ckpt_<env>_seed{k}.pt` — final weights + optimizer + config (**gitignored**;
  runs are reproducible from seed + config, so weights are not committed)
