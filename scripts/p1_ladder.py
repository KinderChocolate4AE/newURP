"""P1 attacker-ladder defender-frozen map + P1b plant-swap pre-check 실행기.

manifest = scripts/p1_ladder_manifest.py (docs/118, hash 는 manifest.json 이 정본).
defender 는 전 config 동결: scripted hold limiter + scripted launcher. 공격자만
suite 공칭 AttackerSpec 에 선언된 override 를 dataclasses.replace 로 적용한다.

    python -m scripts.p1_ladder --smoke                 # CPU 배선 검사
    python -m scripts.p1_ladder --run                   # P1a 전 config (서버)
    python -m scripts.p1_ladder --run --shard 0/4       # config 단위 샤딩
    python -m scripts.p1_ladder --p1b                   # plant-swap pre-check
    python -m scripts.p1_ladder --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import json
import math
import pathlib

import numpy as np

from scripts.p1_ladder_manifest import load as load_p1_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p1_ladder"
EXEC_PATHS = ("shepherd", "scripts/p1_ladder.py", "scripts/p1_ladder_manifest.py",
              "artifacts/p1_ladder/manifest.json")
NOMINAL = "t1f_r05_s30_ref"          # P1b 의 tau=0 baseline (동일 draw)


def _overrides(config: dict) -> dict:
    return {k: (float("inf") if v == "inf" else v)
            for k, v in config["overrides"].items()}


class PlantLagEnv:
    """defender 병진 a_cmd 1차 지연 (docs/93 옵션 1, docs/118 §6-4).

    limiter accel 에만 적용한다 — capturer 병진은 `FinisherSpec.a_max=0.0` 기본에서
    `mobile_finisher_accel` 이 정확히 zeros(3) 이므로 (env.py P69 주석) lag 가
    자명하게 0 이다. 그 전제를 assert 로 고정한다. 공격자 plant 불변 (단일축 규율).
    이산화는 exact exponential: a += (1 - exp(-dt/tau_a)) * (a_cmd - a).
    """

    def __init__(self, env, tau_ratio: float):
        a_max = float(getattr(env.sc.finisher, "a_max", 0.0))
        if a_max != 0.0:
            raise SystemExit(f"P1b premise violated: finisher a_max={a_max} != 0")
        self.env = env
        self.tau_a = float(tau_ratio) * float(env.tau_deploy)
        self._alpha = 1.0 - math.exp(-float(env.dt) / self.tau_a)
        self._lag: dict = {}

    def reset(self, *a, **kw):
        self._lag.clear()
        return self.env.reset(*a, **kw)

    def step(self, actions):
        acts = dict(actions)
        for lid in self.env.limiter_ids:
            la = np.array(acts.get(lid, np.zeros(4)), float, copy=True)
            prev = self._lag.get(lid)
            if prev is None:
                prev = np.zeros(3)
            a = prev + self._alpha * (la[:3] - prev)
            self._lag[lid] = a
            la[:3] = a
            acts[lid] = la
        return self.env.step(acts)

    def __getattr__(self, name):
        return getattr(self.env, name)


def _cells(b2: dict, *, smoke: bool) -> list:
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    cells = boundary_cells(b2)
    return cells[:2] if smoke else cells


def _run_config(manifest: dict, b2: dict, label: str, overrides: dict, *,
                tau_ratio: float | None = None, smoke: bool = False,
                limiter_mode: str = "hold", limiter_kw: dict | None = None,
                cells: list | None = None) -> dict:
    from shepherd.m4_env import build_m4_env
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs
    from shepherd.scripts.mission_rollout import partition_bin, run_episode

    ev = manifest["evaluation"]
    if cells is None:
        cells = _cells(b2, smoke=smoke)
    epc = 1 if smoke else int(ev["episodes_per_cell"])
    sealed_epc = int(ev["episodes_per_cell"])
    rows = []
    for ci, cell in enumerate(cells):
        for j in range(epc):
            sid = ci * sealed_epc + j
            chi, eta, kw = scenario_kwargs(b2, cell, sid, seed0=ev["seed0"],
                                           seed_ns=ev["namespace"])
            kw = dict(kw)
            kw["attacker"] = replace(kw["attacker"], **overrides)
            stack = build_m4_env(ev["seed0"], sid, **kw)
            env = stack.env if tau_ratio is None else PlantLagEnv(stack.env, tau_ratio)
            r = run_episode(env, stack.scn, stack.lay, seed=int(ev["seed0"]) + sid,
                            policy=None, limiter_mode=limiter_mode,
                            limiter_kw=limiter_kw, fire_mode="clean")
            rows.append({"cell_id": cell["cell_id"], "row": int(cell["row"]),
                         "chi_role": cell["chi_role"], "scenario_id": sid,
                         "chi": chi, "eta": eta, "bin": partition_bin(r),
                         "outcome": r.outcome, "fire": r.fire_step is not None,
                         "clean_crossings": int(r.clean_crossings),
                         "steps": int(r.steps)})
    counts = Counter(r["bin"] for r in rows)
    return {
        "schema": "p1-ladder-config-v1" + ("-smoke" if smoke else ""),
        "manifest_hash": manifest["manifest_hash"], "label": label,
        "tau_ratio": tau_ratio, "overrides": {k: ("inf" if v == float("inf") else v)
                                              for k, v in overrides.items()},
        "code_commit": git_commit(), "code_dirty_scoped": git_dirty(EXEC_PATHS),
        "n": len(rows), "counts": dict(sorted(counts.items())),
        "episodes_with_clean_crossing": sum(r["clean_crossings"] > 0 for r in rows),
        "clean_crossings_total": sum(r["clean_crossings"] for r in rows),
        "records": rows,
    }


def _write(out: dict, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    tau = out["tau_ratio"]
    tag = out["label"] if tau is None else f"{out['label']}@tau{tau}"
    print(f"{tag}: N={out['counts'].get('N', 0)}/{out['n']} "
          f"cross={out['episodes_with_clean_crossing']} "
          f"H={out['counts'].get('H_illegal', 0)}", flush=True)


def _check_clean(smoke: bool) -> None:
    from shepherd.provenance import git_dirty
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")


def run_p1a(*, shard: str | None = None, smoke: bool = False) -> None:
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_p1_manifest(), load_b2_manifest()
    _check_clean(smoke)
    configs = manifest["attacker"]["configs"]
    if smoke:
        configs = [c for c in configs if c["label"] in (NOMINAL, "a1_pure")]
    if shard:
        k, n = (int(x) for x in shard.split("/"))
        configs = configs[k::n]
    sub = "smoke" if smoke else "configs"
    for c in configs:
        path = OUT / sub / f"{c['label']}.json"
        if path.exists() and not smoke:
            print(f"skip existing {c['label']}", flush=True)
            continue
        _write(_run_config(manifest, b2, c["label"], _overrides(c), smoke=smoke), path)


def run_p1b(*, smoke: bool = False) -> None:
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_p1_manifest(), load_b2_manifest()
    _check_clean(smoke)
    nominal = next(c for c in manifest["attacker"]["configs"]
                   if c["label"] == NOMINAL)
    taus = manifest["p1b_plant_swap"]["tau_a_over_tau0"]
    if smoke:
        taus = taus[:1]
    sub = "smoke" if smoke else "p1b"
    for tau in taus:
        tag = f"tau{str(tau).replace('.', 'p')}"
        path = OUT / sub / f"{NOMINAL}_{tag}.json"
        if path.exists() and not smoke:
            print(f"skip existing {tag}", flush=True)
            continue
        out = _run_config(manifest, b2, NOMINAL, _overrides(nominal),
                          tau_ratio=float(tau), smoke=smoke)
        _write(out, path)


def _chi50_by_row(records: list[dict]) -> dict:
    from shepherd.scripts.r2a_stage0 import chi50_isotonic
    rows = {}
    for r in records:
        rows.setdefault(r["row"], []).append(r)
    out = {}
    for row, rs in sorted(rows.items()):
        chi = np.array([r["chi"] for r in rs], float)
        y = np.array([1.0 if r["bin"] == "N" else 0.0 for r in rs], float)
        c = chi50_isotonic(chi, y)
        out[str(row)] = None if math.isnan(c) else float(c)   # None = censored
    return out


def readout() -> dict:
    from shepherd.provenance import git_commit
    manifest = load_p1_manifest()
    configs = manifest["attacker"]["configs"]
    expected_n = int(manifest["evaluation"]["episodes_per_config"])
    payloads, missing = {}, []
    for c in configs:
        p = OUT / "configs" / f"{c['label']}.json"
        if p.exists():
            payloads[c["label"]] = json.loads(p.read_text(encoding="utf-8"))
        else:
            missing.append(c["label"])
    taus = manifest["p1b_plant_swap"]["tau_a_over_tau0"]
    p1b = {}
    for tau in taus:
        p = OUT / "p1b" / f"{NOMINAL}_tau{str(tau).replace('.', 'p')}.json"
        if p.exists():
            p1b[str(tau)] = json.loads(p.read_text(encoding="utf-8"))
        else:
            missing.append(f"p1b@{tau}")

    draws = {}
    draw_ok = True
    for pl in list(payloads.values()) + list(p1b.values()):
        for r in pl["records"]:
            key = (r["cell_id"], r["scenario_id"])
            val = (round(r["chi"], 12), round(r["eta"], 12))
            draw_ok &= draws.setdefault(key, val) == val
    commits = {pl["code_commit"] for pl in list(payloads.values()) + list(p1b.values())}
    integrity = {
        "completion": not missing,
        "budget": all(pl["n"] == expected_n for pl in payloads.values())
        and all(pl["n"] == expected_n for pl in p1b.values()),
        "paired_draws": draw_ok,
        "lineage": len(commits) == 1 and all(
            not pl["code_dirty_scoped"]
            for pl in list(payloads.values()) + list(p1b.values())),
    }
    decision = (manifest["gate"]["complete"] if all(integrity.values())
                else manifest["gate"]["invalid_decision"])

    summary = {label: {k: pl[k] for k in ("counts", "episodes_with_clean_crossing",
                                          "clean_crossings_total")}
               for label, pl in payloads.items()}
    chi50 = {label: _chi50_by_row(pl["records"]) for label, pl in payloads.items()}
    chi50_p1b = {tau: _chi50_by_row(pl["records"]) for tau, pl in p1b.items()}

    main_n = {c["label"]: payloads[c["label"]]["counts"].get("N", 0)
              for c in configs if c["group"] == "main" and c["label"] in payloads}
    premise = None
    if main_n and not missing:
        spread = max(main_n.values()) - min(main_n.values())
        premise = {"spread": spread, "threshold": 28,
                   "classification": ("P2_PREMISE_SUPPORTED" if spread >= 28
                                      else "P2_PREMISE_WEAK"),
                   "main_grid_N": dict(sorted(main_n.items()))}

    delta = {}
    base = chi50.get(NOMINAL, {})
    for tau, rows in chi50_p1b.items():
        delta[tau] = {row: (None if base.get(row) is None or rows.get(row) is None
                            else float(rows[row] - base[row]))
                      for row in base}
    payload = {
        "schema": "p1-ladder-readout-v1",
        "manifest_hash": manifest["manifest_hash"],
        "code_commit": next(iter(commits)) if len(commits) == 1 else None,
        "current_code_commit": git_commit(),
        "decision": decision, "integrity": integrity, "missing": missing,
        "summary": summary, "chi50_by_row": chi50,
        "p2_premise": premise,
        "p1b": {"chi50_by_row": chi50_p1b, "delta_chi50_vs_nominal": delta,
                "delta_chi_threshold": 0.03},
        "scope": manifest["scope"], "promotion": manifest["promotion"],
    }
    (OUT / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("decision", "integrity", "missing",
                                              "p2_premise")},
                     indent=2, ensure_ascii=False))
    return payload


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--p1b", action="store_true")
    group.add_argument("--readout", action="store_true")
    parser.add_argument("--shard", default=None)
    args = parser.parse_args(argv)
    if args.readout:
        readout()
    elif args.p1b:
        run_p1b()
    elif args.smoke:
        run_p1a(smoke=True)
        run_p1b(smoke=True)
    else:
        run_p1a(shard=args.shard)


if __name__ == "__main__":
    main()
