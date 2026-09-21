"""B0 v3 MAPPO interface preflight: one rollout and one optimizer update.

This is wiring evidence, not a learning result or a hyperparameter comparison.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

import numpy as np

from shepherd.provenance import git_commit, git_dirty, world_hash
from shepherd.scripts.b2_manifest import load as load_b2_manifest
from shepherd.scripts.b2_run import scenario_kwargs
from shepherd.scripts.train_ippo import seed_everything
from shepherd.scripts.train_m4 import M4Runner
from shepherd.train.b0_v3_credit import B0V3CreditEnv, B0V3CreditSpec

ROOT = pathlib.Path(__file__).resolve().parents[2]
W5_PATH = ROOT / "artifacts" / "r2b" / "b2_scripted" / "w5_decision.json"
DEFAULT_OUT = ROOT / "artifacts" / "marl" / "b0_v3_mappo_preflight.json"
CELL_ID = "r03c1"


class PreflightRunner(M4Runner):
    def __init__(self, *args, credit_spec: B0V3CreditSpec, **kwargs):
        self.credit_spec = credit_spec
        self.credit_outcomes = Counter()
        super().__init__(*args, **kwargs)

    def _wrap_episode_env(self, env):
        return B0V3CreditEnv(env, self.credit_spec)

    def _observe_step(self, result) -> None:
        super()._observe_step(result)
        if result.flags.get("b0_credit_cut"):
            self.credit_outcomes[str(result.flags["b0_rl_outcome"])] += 1


def _source_s(manifest: dict, cell_id: str) -> int:
    return next(int(u["s_lo"]) for u in manifest["units"]
                if u["cell_id"] == cell_id)


def _run_cfg(steps: int) -> dict:
    if steps < 32:
        raise ValueError("steps must be at least 32")
    return {
        "loop": {"total_env_steps": steps, "rollout_env_steps": steps},
        "mappo": {
            "gamma": 0.99, "lam": 0.95, "lr": 3e-4,
            "epochs": 2, "minibatch_size": min(64, steps),
            "clip_eps": 0.2, "ent_coef_limiter": 0.0,
            "ent_coef_finisher": 0.003, "vf_coef": 0.5,
            "max_grad_norm": 0.5, "target_kl": 0.02,
            "hidden_sizes": [32, 32], "init_log_std": 0.0,
            "ortho_init": True, "value_norm": True,
            "limiter_commit": False, "coma_mix": 0.0,
        },
    }


def run(steps: int = 128, seed: int = 0) -> dict:
    w5 = json.loads(W5_PATH.read_text(encoding="utf-8"))
    if w5.get("decision") != "PASS" or not w5.get("validity", {}).get("pass"):
        raise SystemExit("W5 PASS artifact is absent or invalid; preflight refused")

    manifest = load_b2_manifest()
    cell = next(c for c in manifest["cells"] if c["cell_id"] == CELL_ID)
    source_s = _source_s(manifest, CELL_ID)
    chi, eta, kw = scenario_kwargs(manifest, cell, source_s)
    cfg = _run_cfg(int(steps))
    credit = B0V3CreditSpec(gamma=cfg["mappo"]["gamma"], beta=0.2)

    seed_everything(int(seed))
    runner = PreflightRunner(
        cfg, int(seed), "cpu", credit_spec=credit,
        system=kw["system"], reward=kw["reward"], attacker=kw["attacker"],
        spawn=kw["spawn"], extra_cfg=kw["extra_cfg"],
        randomize_threat=False, threat_obs=True,
        limiter_policy="learned", finisher_policy="learned", aim_bc="none")
    runner.collect_rollout()

    rewards = runner.buf.rewards.copy()
    dones = runner.buf.dones.copy()
    if not np.all(np.isfinite(rewards)):
        raise FloatingPointError("non-finite reward in rollout")
    stats = runner.update()
    if not all(np.isfinite(float(v)) for v in stats.values()):
        raise FloatingPointError("non-finite optimizer statistic")

    checks = {
        "w5_pass": True,
        "limiter_commit_head_absent": runner.tr.lim_dim == 3,
        "rollout_full": int(len(rewards)) == int(steps),
        "reward_finite": bool(np.all(np.isfinite(rewards))),
        "optimizer_stats_finite": True,
        "optimizer_update_exactly_one": True,
    }
    result = {
        "schema": "b0-v3-mappo-preflight-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "scope": "interface smoke only; not learning evidence",
        "code_commit": git_commit(),
        "code_dirty_scoped": git_dirty(),
        "w5_decision": str(W5_PATH.relative_to(ROOT)).replace("\\", "/"),
        "b0_v3_hash": manifest["b0_v3_hash"],
        "source_cell": {"cell_id": CELL_ID, "source_s": source_s,
                        "chi": chi, "eta": eta},
        "world_hash": world_hash(runner.contract),
        "credit": credit.manifest(),
        "run": {"seed": int(seed), "device": "cpu", "steps": int(steps),
                "updates": 1, "actor": "heterogeneous limiter/capturer",
                "limiter_commit": False},
        "observed": {
            "credit_cuts": int(dones.sum()),
            "credit_outcomes": dict(sorted(runner.credit_outcomes.items())),
            "reward_min": float(rewards.min()),
            "reward_max": float(rewards.max()),
            "completed_episodes": len(runner.ep_records),
            "optimizer": {k: float(v) for k, v in sorted(stats.items())},
        },
        "checks": checks,
    }
    if result["status"] != "PASS":
        raise RuntimeError(f"preflight failed: {checks}")
    return result


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=128)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)
    result = run(args.steps, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                           encoding="utf-8")
    print(f"{result['status']}: {args.output}")


if __name__ == "__main__":
    main()

