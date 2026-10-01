"""P2 limiter-only v2 실행기 (manifest = scripts/p2_limiter_manifest.py, docs/120).

b5 계보를 그대로 상속 (B5LimiterRunner + freeze_finisher + neutral init) 하고,
학습·평가 episode 에 선언된 공격자 mix (6 config) 를 dataclasses.replace 로 주입
한다. b5 와 다른 것은 공격자 축뿐이다 (단일축 규율).

서버 실행 순서:
    python -m scripts.p2_limiter --smoke                       # CPU 배선 검사
    python -m scripts.p2_limiter --controls                    # hold + c5 (6 config)
    python -m scripts.p2_limiter --run --seed 0 --device cuda  # (seed 1 동일)
    python -m scripts.p2_limiter --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
import pathlib
import time

import numpy as np

from scripts.p2_limiter_manifest import HIGH_COUPLING, MIX, load as load_p2_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p2_limiter"
EXEC_PATHS = ("shepherd", "scripts/p2_limiter.py", "scripts/p2_limiter_manifest.py",
              "scripts/b5_limiter_only.py", "artifacts/p2_limiter/manifest.json")
ARMS_SCRIPTED = ("hold", "c5")
POSITIVE, NULL, INVALID = "P2_POSITIVE", "P2_NULL", "INVALID_P2"


def mix_config(train_seed: int, ep_idx: int) -> dict:
    h = hashlib.sha256(f"p2-mix|{int(train_seed)}|{int(ep_idx)}".encode()).digest()
    return MIX[int.from_bytes(h[:8], "big") % len(MIX)]


def _prereq(manifest: dict) -> None:
    pre = manifest["prerequisites"]
    p1 = json.loads((ROOT / pre["p1_readout"]).read_text(encoding="utf-8"))
    row9 = json.loads((ROOT / pre["plant_precheck"]).read_text(encoding="utf-8"))
    checks = {
        "P1": p1.get("decision") == pre["p1_decision_required"],
        "P1_premise": (p1.get("p2_premise") or {}).get("classification")
        == pre["p1_premise_required"],
        "plant": (row9.get("judgment") or {}).get("verdict")
        == pre["plant_verdict_required"],
        "b5_closed": (ROOT / pre["b5_closed"]).exists(),
    }
    if not all(checks.values()):
        raise SystemExit(f"P2 prerequisite failure: {checks}")


def _check_clean(smoke: bool) -> None:
    from shepherd.provenance import git_dirty
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")


# -------------------------------------------------------------- evaluation ---
def _eval_arm(manifest: dict, b2: dict, config: dict, *, policy=None,
              scripted_roles=(), limiter_mode="hold", limiter_kw=None,
              credit_spec, torch_seeded=False, smoke=False) -> dict:
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells, scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    from shepherd.train.b0_v3_credit import B0V3CreditEnv

    ev = manifest["evaluation"]
    cells = boundary_cells(b2)[:2] if smoke else boundary_cells(b2)
    epc = 1 if smoke else int(ev["episodes_per_cell"])
    sealed_epc = int(ev["episodes_per_cell"])
    rows = []
    for ci, cell in enumerate(cells):
        for j in range(epc):
            sid = ci * sealed_epc + j
            chi, eta, kw = scenario_kwargs(b2, cell, sid, seed0=ev["seed0"],
                                           seed_ns=ev["namespace"])
            kw = dict(kw)
            kw["attacker"] = replace(kw["attacker"], **config["overrides"])
            stack = build_m4_env(ev["seed0"], sid, **kw)
            env = B0V3CreditEnv(stack.env, credit_spec)
            if torch_seeded:
                import torch
                torch.manual_seed(int(ev["seed0"]) + sid)
            r = run_episode(env, stack.scn, stack.lay, seed=int(ev["seed0"]) + sid,
                            policy=policy, scripted_roles=scripted_roles,
                            limiter_mode=limiter_mode, limiter_kw=limiter_kw,
                            fire_mode="clean")
            rows.append({"cell_id": cell["cell_id"], "scenario_id": sid,
                         "chi": chi, "eta": eta, "bin": partition_bin(r),
                         "fire": r.fire_step is not None,
                         "clean_crossings": int(r.clean_crossings),
                         "steps": int(r.steps)})
    counts = Counter(r["bin"] for r in rows)
    return {"config": config["label"], "n": len(rows),
            "counts": dict(sorted(counts.items())),
            "episodes_with_clean_crossing": sum(r["clean_crossings"] > 0
                                                for r in rows),
            "records": rows}


def run_controls(*, smoke=False) -> None:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    from shepherd.train.b0_v3_credit import B0V3CreditSpec
    manifest, b2 = load_p2_manifest(), load_b2_manifest()
    _prereq(manifest)
    _check_clean(smoke)
    hp = manifest["training"]["hyperparameters"]
    spec = B0V3CreditSpec(gamma=hp["gamma"], beta=hp["beta"],
                          r_clean=hp["r_clean"], r_illegal=hp["r_illegal"])
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    configs = MIX[:1] if smoke else MIX
    sub = "smoke/controls" if smoke else "controls"
    for config in configs:
        for arm in ARMS_SCRIPTED:
            path = OUT / sub / f"{config['label']}_{arm}.json"
            if path.exists() and not smoke:
                print(f"skip existing {config['label']}_{arm}", flush=True)
                continue
            out = _eval_arm(manifest, b2, config, credit_spec=spec, smoke=smoke,
                            limiter_mode=("hold" if arm == "hold" else "arc"),
                            limiter_kw=(None if arm == "hold" else c5))
            out.update({"schema": "p2-control-v1" + ("-smoke" if smoke else ""),
                        "arm": arm, "manifest_hash": manifest["manifest_hash"],
                        "code_commit": git_commit(),
                        "code_dirty_scoped": git_dirty(EXEC_PATHS)})
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            print(f"{config['label']}/{arm}: N={out['counts'].get('N', 0)}/{out['n']} "
                  f"H={out['counts'].get('H_illegal', 0)}", flush=True)


# ---------------------------------------------------------------- learned ----
def _make_p2_runner_cls():
    import scripts.b5_limiter_only as b5

    class P2Runner(b5._make_runner_cls()):
        """b5 learned-limiter runner + 선언된 공격자 mix 주입."""

        def _build_episode_stack(self):
            from shepherd.m4_env import build_m4_env
            from shepherd.scripts.b0_v3_mappo_pilot import (scenario_kwargs,
                                                            scheduled_cell)
            tr = self.b5_manifest["training"]
            cell, stratum = scheduled_cell(self.b2, self.seed, self._ep_idx)
            sid = self.seed * 1_000_000 + self._ep_idx
            chi, eta, kw = scenario_kwargs(self.b2, cell, sid,
                                           seed0=tr["seed0"], seed_ns=tr["seed_ns"])
            mix = mix_config(self.seed, self._ep_idx)
            kw = dict(kw)
            kw["attacker"] = replace(kw["attacker"], **mix["overrides"])
            self._current_cell = {"cell_id": cell["cell_id"], "row": cell["row"],
                                  "stratum": stratum, "chi": chi, "eta": eta,
                                  "mix": mix["label"]}
            return build_m4_env(tr["seed0"] + self.seed, self._ep_idx, **kw)

    return P2Runner


def _neutral_init_verified(runner) -> bool:
    import scripts.b5_limiter_only as b5_mod  # noqa: F401 (torch 로드 보장)
    from shepherd.scripts.b0_v3_mappo_pilot import _last_linear
    head = _last_linear(runner.tr.lim_actor.mean)
    return bool((head.weight == 0).all() and (head.bias == 0).all())


def run_seed(seed: int, device: str, *, smoke=False) -> dict:
    import torch
    from shepherd.notify import ntfy
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    from shepherd.scripts.train_ippo import seed_everything
    manifest, b2 = load_p2_manifest(), load_b2_manifest()
    _prereq(manifest)
    if seed not in manifest["training"]["seeds"]:
        raise ValueError("seed is outside the sealed manifest")
    _check_clean(smoke)

    runner_cls = _make_p2_runner_cls()
    seed_everything(int(seed))
    runner = runner_cls(manifest, b2, seed, device,
                        steps=128 if smoke else None,
                        rollout=128 if smoke else None)
    neutral = _neutral_init_verified(runner)
    fin_frozen = bool(runner.tr.cfg.freeze_finisher) and not any(
        p.requires_grad for p in runner.tr.fin_actor.parameters())
    if not smoke and not (neutral and fin_frozen):
        raise SystemExit(f"P2 setup check failed: neutral={neutral} "
                         f"finisher_frozen={fin_frozen}")
    run_dir = OUT / ("smoke/learned" if smoke else "learned") / f"seed{seed}"
    if not smoke and (run_dir / ".done").exists():
        raise SystemExit(f"completed run exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)

    tr_spec = manifest["training"]
    total_updates = int(runner.tr.cfg.total_timesteps // runner.rollout_env_steps)
    floor = float(tr_spec["hyperparameters"]["lr_anneal_floor"])
    lr0 = float(tr_spec["hyperparameters"]["lr"])
    logs, t0 = [], time.time()
    ntfy(f"p2-limiter s{seed} start ({total_updates} updates)", title="p2-lim")
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
        print(f"p2/s{seed}: update {update + 1}/{total_updates} "
              f"steps={runner.env_steps}", flush=True)

    configs = MIX[:1] if smoke else MIX
    evaluation = {}
    for config in configs:
        evaluation[config["label"]] = _eval_arm(
            manifest, b2, config, policy=runner.policy_fn(deterministic=False),
            scripted_roles=("finisher",), limiter_mode="hold",
            credit_spec=runner.credit_spec, torch_seeded=True, smoke=smoke)
        print(f"learned_s{seed}/{config['label']}: "
              f"N={evaluation[config['label']]['counts'].get('N', 0)}"
              f"/{evaluation[config['label']]['n']}", flush=True)
    summary = {
        "schema": "p2-limiter-run-v1" + ("-smoke" if smoke else ""),
        "manifest_hash": manifest["manifest_hash"],
        "b0_v3_hash": b2["b0_v3_hash"], "seed": seed, "device": device,
        "code_commit": git_commit(), "code_dirty_scoped": git_dirty(EXEC_PATHS),
        "setup": {"neutral_init_verified": neutral, "finisher_frozen": fin_frozen},
        "training": {"steps": runner.env_steps, "updates": total_updates,
                     "episodes": runner._ep_idx,
                     "mix_exposure": dict(Counter(
                         r.get("mix") for r in runner.ep_records if r.get("mix"))),
                     "credit_outcomes": dict(sorted(runner.credit_outcomes.items())),
                     "last_update": logs[-1]},
        "evaluation": evaluation,
        "elapsed_s": round(time.time() - t0, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if not smoke:
        (run_dir / ".done").write_text(json.dumps(
            {"manifest_hash": manifest["manifest_hash"],
             "code_commit": git_commit()}), encoding="utf-8")
    ntfy(f"p2-limiter s{seed} done", title="p2-lim")
    return summary


# ----------------------------------------------------------------- readout ---
def apply_gate(per_seed: dict, h_pooled: dict, integrity: dict,
               *, min_pooled_delta: int = 34) -> dict:
    if not all(bool(v) for v in integrity.values()):
        return {"decision": INVALID, "clauses": {}, "integrity": integrity}
    clauses = {}
    for seed, cfgs in per_seed.items():
        pooled = sum(c["learned"] - c["hold"] for c in cfgs.values())
        clauses[f"seed{seed}_pooled_delta_N_ge_{min_pooled_delta}"] = (
            pooled >= min_pooled_delta)
        for label in HIGH_COUPLING:
            clauses[f"seed{seed}_{label}_delta_N_nonneg"] = (
                cfgs[label]["learned"] - cfgs[label]["hold"] >= 0)
    clauses["pooled_H_illegal_zero_hold_and_learned"] = all(
        v == 0 for k, v in h_pooled.items() if k != "c5")
    return {"decision": POSITIVE if all(clauses.values()) else NULL,
            "clauses": clauses, "pooled_H_illegal": h_pooled,
            "integrity": integrity}


def readout() -> dict:
    from shepherd.provenance import git_commit
    manifest = load_p2_manifest()
    ev = manifest["evaluation"]
    expected_n = int(ev["episodes_per_config_per_arm"])
    controls, missing = {}, []
    for config in MIX:
        for arm in ARMS_SCRIPTED:
            p = OUT / "controls" / f"{config['label']}_{arm}.json"
            if p.exists():
                controls[(config["label"], arm)] = json.loads(
                    p.read_text(encoding="utf-8"))
            else:
                missing.append(f"{config['label']}_{arm}")
    learned = {}
    for seed in manifest["training"]["seeds"]:
        d = OUT / "learned" / f"seed{seed}"
        if (d / ".done").exists():
            learned[seed] = json.loads((d / "summary.json").read_text(
                encoding="utf-8"))
        else:
            missing.append(f"learned_seed{seed}")

    draws, draw_ok = {}, True
    payload_iter = ([(("ctrl",) + k, v) for k, v in controls.items()]
                    + [((f"s{s}", c), v) for s, summ in learned.items()
                       for c, v in summ["evaluation"].items()])
    for _key, pl in payload_iter:
        for r in pl["records"]:
            # scenario draw 는 config 와 무관하므로 (cell, sid) 가 전역 pairing key 다
            dk = (r["cell_id"], r["scenario_id"])
            val = (round(r["chi"], 12), round(r["eta"], 12))
            draw_ok &= draws.setdefault(dk, val) == val
    commits = ({pl["code_commit"] for pl in controls.values()}
               | {s["code_commit"] for s in learned.values()})
    integrity = {
        "completion": not missing,
        "budget": all(pl["n"] == expected_n for pl in controls.values())
        and all(e["n"] == expected_n for s in learned.values()
                for e in s["evaluation"].values()),
        "paired_draws": draw_ok,
        "lineage": len(commits) == 1
        and all(not pl["code_dirty_scoped"] for pl in controls.values())
        and all(not s["code_dirty_scoped"] for s in learned.values())
        and all(s["training"]["steps"] == manifest["training"]["total_env_steps"]
                for s in learned.values()),
        "neutral_init": all(s["setup"]["neutral_init_verified"]
                            for s in learned.values()),
        "finisher_frozen": all(s["setup"]["finisher_frozen"]
                               for s in learned.values()),
    }
    per_seed = {}
    for seed, summ in learned.items():
        per_seed[seed] = {c["label"]: {
            "hold": controls.get((c["label"], "hold"), {}).get(
                "counts", {}).get("N", 0),
            "c5": controls.get((c["label"], "c5"), {}).get(
                "counts", {}).get("N", 0),
            "learned": summ["evaluation"].get(c["label"], {}).get(
                "counts", {}).get("N", 0)}
            for c in MIX}
    h_pooled = {
        "hold": sum(controls.get((c["label"], "hold"), {}).get(
            "counts", {}).get("H_illegal", 0) for c in MIX),
        "c5": sum(controls.get((c["label"], "c5"), {}).get(
            "counts", {}).get("H_illegal", 0) for c in MIX),
        **{f"learned_s{s}": sum(e["counts"].get("H_illegal", 0)
                                for e in summ["evaluation"].values())
           for s, summ in learned.items()},
    }
    gate = apply_gate(per_seed, h_pooled, integrity)
    payload = {
        "schema": "p2-limiter-readout-v1",
        "manifest_hash": manifest["manifest_hash"],
        "code_commit": next(iter(commits)) if len(commits) == 1 else None,
        "current_code_commit": git_commit(),
        "decision": gate["decision"], "gate": gate, "missing": missing,
        "per_seed_per_config_N": {str(s): v for s, v in per_seed.items()},
        "scope": manifest["scope"], "promotion": manifest["promotion"],
    }
    (OUT / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("decision", "missing")},
                     ensure_ascii=False))
    print(json.dumps(gate["clauses"], indent=1, ensure_ascii=False))
    return payload


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
        run_controls(smoke=True)
        run_seed(0, "cpu", smoke=True)
    elif a.controls:
        run_controls()
    elif a.run:
        if a.seed is None:
            p.error("--run requires --seed")
        run_seed(a.seed, a.device)
    else:
        readout()


if __name__ == "__main__":
    main()
