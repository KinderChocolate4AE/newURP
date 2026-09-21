"""B-5 한정 limiter-only 실험 실행기 (manifest = scripts/b5_limiter_only_manifest.py).

Arm: learned limiter + **scripted clean-fire capturer** (freeze_finisher — scripted
행동은 어떤 policy log-prob에도 들어가지 않는다). 대조: hold limiter, c5 limiter
(둘 다 scripted capturer, 학습 없음). 세 arm은 같은 세계·paired scenario를 소비한다.

이 실험의 정책은 scripted launcher에 의존한다. learned cooperation 성과로 승격하지
않으며, pilot의 봉인 280사례·선택 문턱을 재사용하지 않는다 (새 eval namespace 71000).

서버 실행 순서:
    python -m scripts.b5_limiter_only --smoke                       # CPU 배선 검사
    python -m scripts.b5_limiter_only --controls                    # scripted 두 arm
    python -m scripts.b5_limiter_only --run --seed 0 --device cuda  # (seed 1 동일)
    python -m scripts.b5_limiter_only --readout
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import pathlib
import time

import numpy as np

from scripts.b5_limiter_only_manifest import load as load_b5_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "marl" / "b5_limiter_only"
EXEC_PATHS = ("shepherd", "scripts/b5_limiter_only.py",
              "scripts/b5_limiter_only_manifest.py")


def _prereq(manifest: dict) -> None:
    pre = manifest["prerequisites"]
    readout = json.loads((ROOT / pre["pilot_readout"]).read_text(encoding="utf-8"))
    if readout["decision"] != pre["pilot_decision_required"]:
        raise SystemExit("prerequisite pilot readout is not NO_SELECTION")
    if not (ROOT / pre["role_swap"]).exists():
        raise SystemExit("role-swap diagnostic artifact missing")


def _make_runner_cls():
    """torch·학습 스택은 여기서만 import — manifest/CLI 경로는 torch-free."""
    import torch
    from shepherd.scripts.b0_v3_mappo_pilot import (_last_linear, scenario_kwargs,
                                                    scheduled_cell)
    from shepherd.scripts.train_m4 import M4Runner
    from shepherd.train.b0_v3_credit import B0V3CreditSpec

    class B5LimiterRunner(M4Runner):
        """learned limiter + scripted clean-fire capturer (arm LS)."""

        def __init__(self, manifest: dict, b2: dict, seed: int, device: str, *,
                     steps=None, rollout=None):
            self.b5_manifest = manifest
            self.b2 = b2
            self.cell_counts = Counter()
            self.credit_outcomes = Counter()
            self._current_cell = None
            tr = manifest["training"]
            hp = tr["hyperparameters"]
            total = int(tr["total_env_steps"] if steps is None else steps)
            roll = int(tr["rollout_env_steps"] if rollout is None else rollout)
            if total % roll:
                raise ValueError("total_env_steps must divide by rollout")
            cfg = {
                "loop": {"total_env_steps": total, "rollout_env_steps": roll},
                "mappo": {
                    "gamma": hp["gamma"], "lam": hp["gae_lambda"],
                    "lr": hp["lr"], "epochs": hp["epochs"],
                    "minibatch_size": min(int(hp["minibatch_size"]), roll),
                    "clip_eps": hp["clip_eps"],
                    "ent_coef_limiter": hp["ent_coef_limiter"],
                    "ent_coef_finisher": hp["ent_coef_finisher"],
                    "vf_coef": hp["vf_coef"],
                    "max_grad_norm": hp["max_grad_norm"],
                    "target_kl": hp["target_kl"],
                    "hidden_sizes": hp["hidden_sizes"],
                    "init_log_std": hp["init_log_std"],
                    "ortho_init": hp["ortho_init"],
                    "value_norm": hp["value_norm"],
                    "limiter_commit": False,        # kinetic commit head 금지
                    "coma_mix": hp["coma_mix"],
                },
            }
            first, _ = scheduled_cell(b2, seed, 0)
            _, _, kw = scenario_kwargs(b2, first, seed * 1_000_000,
                                       seed0=tr["seed0"], seed_ns=tr["seed_ns"])
            self.credit_spec = B0V3CreditSpec(
                gamma=hp["gamma"], beta=hp["beta"],
                r_clean=hp["r_clean"], r_illegal=hp["r_illegal"])
            super().__init__(cfg, seed, device, system=kw["system"],
                             reward=kw["reward"], attacker=kw["attacker"],
                             spawn=kw["spawn"], extra_cfg=kw["extra_cfg"],
                             randomize_threat=False, threat_obs=True,
                             limiter_policy="learned",
                             finisher_policy="scripted", aim_bc="none")
            assert self.tr.cfg.freeze_finisher and not self.tr.cfg.freeze_limiter
            # limiter neutral init — pilot과 동일 규약 (마지막 mean layer 0).
            head = _last_linear(self.tr.lim_actor.mean)
            torch.nn.init.zeros_(head.weight)
            torch.nn.init.zeros_(head.bias)
            torch.manual_seed(seed)                 # 선언된 학습 시작 RNG

        def _build_episode_stack(self):
            from shepherd.m4_env import build_m4_env
            tr = self.b5_manifest["training"]
            cell, stratum = scheduled_cell(self.b2, self.seed, self._ep_idx)
            sid = self.seed * 1_000_000 + self._ep_idx
            chi, eta, kw = scenario_kwargs(self.b2, cell, sid,
                                           seed0=tr["seed0"],
                                           seed_ns=tr["seed_ns"])
            self._current_cell = {"cell_id": cell["cell_id"],
                                  "row": cell["row"], "stratum": stratum,
                                  "chi": chi, "eta": eta}
            return build_m4_env(tr["seed0"] + self.seed, self._ep_idx, **kw)

        def _wrap_episode_env(self, env):
            from shepherd.train.b0_v3_credit import B0V3CreditEnv
            return B0V3CreditEnv(env, self.credit_spec)

        def _observe_step(self, result) -> None:
            super()._observe_step(result)
            if result.flags.get("b0_credit_cut"):
                self.credit_outcomes[str(result.flags["b0_rl_outcome"])] += 1

        def _finish_episode(self, result) -> None:
            super()._finish_episode(result)
            self.ep_records[-1].update(self._current_cell or {})
            self.ep_records[-1]["rl_outcome"] = result.flags.get("b0_rl_outcome")
            if self._current_cell:
                self.cell_counts[self._current_cell["cell_id"]] += 1

    return B5LimiterRunner


# -------------------------------------------------------------- evaluation ---
def _eval_scenarios(manifest, b2, cells, episodes_per_cell):
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    ev = manifest["evaluation"]
    sealed_n_pc = int(ev["episodes_per_cell"])
    for ci, cell in enumerate(cells):
        for j in range(episodes_per_cell):
            sid = ci * sealed_n_pc + j
            chi, eta, kw = scenario_kwargs(b2, cell, sid, seed0=ev["seed0"],
                                           seed_ns=ev["seed_ns"])
            yield cell, sid, chi, eta, kw


def _summary_rows(rows):
    counts = Counter(r["bin"] for r in rows)
    n = len(rows)
    return {"n": n, "counts": dict(sorted(counts.items())),
            "p_N": counts["N"] / n, "p_H_illegal": counts["H_illegal"] / n,
            "p_FIRE": sum(r["fire"] for r in rows) / n,
            "episodes_with_clean_crossing": sum(r["clean_crossings"] > 0
                                                for r in rows),
            "records": rows}


def _run_arm(manifest, b2, *, policy=None, scripted_roles=(),
             limiter_mode="hold", limiter_kw=None, cells, episodes_per_cell,
             credit_spec, torch_seeded=False):
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv
    ev = manifest["evaluation"]
    rows = []
    for cell, sid, chi, eta, kw in _eval_scenarios(manifest, b2, cells,
                                                   episodes_per_cell):
        stack = build_m4_env(ev["seed0"], sid, **kw)
        env = B0V3CreditEnv(stack.env, credit_spec)
        if torch_seeded:
            import torch
            torch.manual_seed(int(ev["seed0"]) + sid)
        r = run_episode(env, stack.scn, stack.lay,
                        seed=int(ev["seed0"]) + sid, policy=policy,
                        scripted_roles=scripted_roles,
                        limiter_mode=limiter_mode, limiter_kw=limiter_kw,
                        fire_mode="clean")
        rows.append({"cell_id": cell["cell_id"], "scenario_id": sid,
                     "chi": chi, "eta": eta, "bin": partition_bin(r),
                     "fire": r.fire_step is not None,
                     "clean_crossings": r.clean_crossings, "steps": r.steps})
    return _summary_rows(rows)


def run_controls(*, smoke=False) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    from shepherd.train.b0_v3_credit import B0V3CreditSpec
    manifest, b2 = load_b5_manifest(), load_b2_manifest()
    _prereq(manifest)
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")
    hp = manifest["training"]["hyperparameters"]
    spec = B0V3CreditSpec(gamma=hp["gamma"], beta=hp["beta"],
                          r_clean=hp["r_clean"], r_illegal=hp["r_illegal"])
    cells = boundary_cells(b2)[:2] if smoke else boundary_cells(b2)
    epc = 1 if smoke else int(manifest["evaluation"]["episodes_per_cell"])
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    arms = {
        "hold_limiter": _run_arm(manifest, b2, limiter_mode="hold",
                                 cells=cells, episodes_per_cell=epc,
                                 credit_spec=spec),
        "c5_limiter": _run_arm(manifest, b2, limiter_mode="arc",
                               limiter_kw=c5, cells=cells,
                               episodes_per_cell=epc, credit_spec=spec),
    }
    out = {
        "schema": "b5-limiter-only-controls-v1" + ("-smoke" if smoke else ""),
        "manifest_hash": manifest["manifest_hash"],
        "b0_v3_hash": b2["b0_v3_hash"],
        "code_commit": git_commit(), "code_dirty_scoped": git_dirty(EXEC_PATHS),
        "arms": arms,
    }
    path = OUT / ("smoke" if smoke else "") / "controls.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    for name, s in arms.items():
        print(f"{name}: N={s['counts'].get('N', 0)}/{s['n']} "
              f"cross={s['episodes_with_clean_crossing']} "
              f"H={s['counts'].get('H_illegal', 0)}", flush=True)
    return out


def run_seed(seed: int, device: str, *, smoke=False) -> dict:
    import torch
    from shepherd.notify import ntfy
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    from shepherd.scripts.train_ippo import seed_everything
    manifest, b2 = load_b5_manifest(), load_b2_manifest()
    _prereq(manifest)
    if seed not in manifest["training"]["seeds"]:
        raise ValueError("seed is outside the sealed manifest")
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")

    runner_cls = _make_runner_cls()
    seed_everything(int(seed))
    runner = runner_cls(manifest, b2, seed, device,
                        steps=128 if smoke else None,
                        rollout=128 if smoke else None)
    run_dir = OUT / ("smoke" if smoke else "learned") / f"seed{seed}"
    if not smoke and (run_dir / ".done").exists():
        raise SystemExit(f"completed run exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    tr_spec = manifest["training"]
    total_updates = int(runner.tr.cfg.total_timesteps // runner.rollout_env_steps)
    floor = float(tr_spec["hyperparameters"]["lr_anneal_floor"])
    lr0 = float(tr_spec["hyperparameters"]["lr"])
    logs, t0 = [], time.time()
    ntfy(f"b5-limiter s{seed} start ({total_updates} updates)", title="b5-lim")
    for update in range(total_updates):
        runner.tr.set_lr(lr0 * max(1.0 - update / max(total_updates - 1, 1), floor))
        runner.collect_rollout()
        stats = runner.update()
        if not all(np.isfinite(float(v)) for v in stats.values()):
            raise FloatingPointError(f"non-finite training stats at {update}")
        logs.append({"update": update + 1, "env_steps": runner.env_steps,
                     "stats": {k: float(v) for k, v in stats.items()},
                     "rolling": runner.rolling()})
        every = 1 if smoke else int(tr_spec["checkpoint_every_updates"])
        if (update + 1) % every == 0 or update + 1 == total_updates:
            runner.save(run_dir)
            (run_dir / "train_log.json").write_text(
                json.dumps(logs, ensure_ascii=False), encoding="utf-8")

    cells = boundary_cells(b2)[:2] if smoke else boundary_cells(b2)
    epc = 1 if smoke else int(manifest["evaluation"]["episodes_per_cell"])
    evaluation = _run_arm(
        manifest, b2, policy=runner.policy_fn(deterministic=False),
        scripted_roles=("finisher",), limiter_mode="hold", cells=cells,
        episodes_per_cell=epc, credit_spec=runner.credit_spec,
        torch_seeded=True)
    summary = {
        "schema": "b5-limiter-only-run-v1" + ("-smoke" if smoke else ""),
        "status": "PASS",
        "scope": "mechanism experiment; policy depends on the scripted "
                 "launcher; not learned-cooperation evidence",
        "manifest_hash": manifest["manifest_hash"],
        "b0_v3_hash": b2["b0_v3_hash"],
        "arm": runner.arm, "seed": seed, "device": device,
        "code_commit": git_commit(), "code_dirty_scoped": git_dirty(EXEC_PATHS),
        "training": {"steps": runner.env_steps, "updates": total_updates,
                     "episodes": runner._ep_idx,
                     "credit_outcomes": dict(sorted(runner.credit_outcomes.items())),
                     "cell_exposure": dict(sorted(runner.cell_counts.items())),
                     "last_update": logs[-1]},
        "evaluation": evaluation,
        "elapsed_s": round(time.time() - t0, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / ".done").write_text(json.dumps(
        {"manifest_hash": manifest["manifest_hash"],
         "code_commit": git_commit()}), encoding="utf-8")
    ntfy(f"b5-limiter s{seed} done N={evaluation['p_N']:.3f}", title="b5-lim")
    return summary


# ----------------------------------------------------------------- readout ---
def readout() -> dict:
    manifest = load_b5_manifest()
    controls = json.loads((OUT / "controls.json").read_text(encoding="utf-8"))
    if controls["manifest_hash"] != manifest["manifest_hash"]:
        raise SystemExit("controls manifest mismatch")
    arms = {k: v for k, v in controls["arms"].items()}
    learned = {}
    for seed in manifest["training"]["seeds"]:
        d = OUT / "learned" / f"seed{seed}"
        if not (d / ".done").exists():
            raise SystemExit(f"missing learned run: {d}")
        s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        if (s["manifest_hash"] != manifest["manifest_hash"]
                or s["schema"] != "b5-limiter-only-run-v1"
                or s["training"]["steps"] != manifest["training"]["total_env_steps"]):
            raise SystemExit(f"learned run lineage mismatch: {d}")
        learned[f"learned_seed{seed}"] = s["evaluation"]

    def _by_cell(summary):
        cell_n = defaultdict(int)
        for r in summary["records"]:
            cell_n[r["cell_id"]] += int(r["bin"] == "N")
        return cell_n

    paired = {}
    for name, ev in learned.items():
        ln = _by_cell(ev)
        for ctrl in ("hold_limiter", "c5_limiter"):
            cn = _by_cell(arms[ctrl])
            diff = {c: ln[c] - cn[c] for c in cn}
            paired[f"{name}_vs_{ctrl}"] = {
                "cells_pos": sum(v > 0 for v in diff.values()),
                "cells_neg": sum(v < 0 for v in diff.values()),
                "cells_zero": sum(v == 0 for v in diff.values()),
                "delta_N_total": int(sum(diff.values())),
            }
    strip = {k: {kk: vv for kk, vv in v.items() if kk != "records"}
             for k, v in {**arms, **learned}.items()}
    out = {"schema": "b5-limiter-only-readout-v1",
           "manifest_hash": manifest["manifest_hash"],
           "scope": manifest["scope"],
           "arms": strip, "paired_delta_N": paired,
           "promotion": manifest["readout"]["promotion"]}
    (OUT / "readout.json").write_text(json.dumps(out, indent=2,
                                                 ensure_ascii=False),
                                      encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "arms"},
                     ensure_ascii=False, indent=2))
    return out


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--controls", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--readout", action="store_true")
    p.add_argument("--seed", type=int)
    p.add_argument("--device", default="cuda")
    a = p.parse_args(argv)
    if a.smoke:
        print(json.dumps(run_controls(smoke=True), ensure_ascii=False)[:400])
        print(json.dumps(run_seed(0, "cpu", smoke=True),
                         ensure_ascii=False)[:400])
    elif a.controls:
        run_controls()
    elif a.run:
        if a.seed is None:
            p.error("--run requires --seed")
        print(json.dumps(run_seed(a.seed, a.device), ensure_ascii=False)[:400])
    else:
        readout()


if __name__ == "__main__":
    main()
