"""P1b-2 실행기: c5 arc limiter 세계의 plant-swap pre-check.

manifest = scripts/p1b2_plant_manifest.py. 평가 루프는 p1_ladder._run_config 를
재사용한다 (limiter_mode="arc" + B2 RULE_COOP limiter_kw, PlantLagEnv 동일).

    python -m scripts.p1b2_plant --smoke
    python -m scripts.p1b2_plant --run
    python -m scripts.p1b2_plant --readout
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import numpy as np

from scripts.p1_ladder import _chi50_by_row, _run_config, _write
from scripts.p1b2_plant_manifest import TAUS, load as load_p1b2_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p1b2_plant"
EXEC_PATHS = ("shepherd", "scripts/p1_ladder.py", "scripts/p1b2_plant.py",
              "scripts/p1b2_plant_manifest.py", "artifacts/p1b2_plant/manifest.json")
LABEL = "c5_scripted"


def _tag(tau: float) -> str:
    return f"tau{str(tau).replace('.', 'p')}"


def run(*, smoke: bool = False) -> None:
    from shepherd.provenance import git_dirty
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_p1b2_manifest(), load_b2_manifest()
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    overrides = dict(manifest["attacker"]["overrides"])
    taus = TAUS[:2] if smoke else TAUS
    sub = "smoke" if smoke else "arms"
    for tau in taus:
        path = OUT / sub / f"{LABEL}_{_tag(tau)}.json"
        if path.exists() and not smoke:
            print(f"skip existing {_tag(tau)}", flush=True)
            continue
        out = _run_config(manifest, b2, LABEL, overrides,
                          tau_ratio=(None if tau == 0.0 else float(tau)),
                          smoke=smoke, limiter_mode="arc", limiter_kw=c5)
        out["tau_ratio"] = float(tau)        # baseline 0.0 도 명시 기록
        _write(out, path)


def readout() -> dict:
    from shepherd.provenance import git_commit
    manifest = load_p1b2_manifest()
    expected_n = int(manifest["evaluation"]["episodes_per_arm"])
    arms, missing = {}, []
    for tau in TAUS:
        p = OUT / "arms" / f"{LABEL}_{_tag(tau)}.json"
        if p.exists():
            arms[str(tau)] = json.loads(p.read_text(encoding="utf-8"))
        else:
            missing.append(_tag(tau))

    draws, draw_ok = {}, True
    for pl in arms.values():
        for r in pl["records"]:
            key = (r["cell_id"], r["scenario_id"])
            val = (round(r["chi"], 12), round(r["eta"], 12))
            draw_ok &= draws.setdefault(key, val) == val

    def _sig(pl):
        return {(r["cell_id"], r["scenario_id"]):
                (r["bin"], r["steps"], r["clean_crossings"]) for r in pl["records"]}

    power = {}
    if "0.0" in arms:
        base_sig = _sig(arms["0.0"])
        for tau, pl in arms.items():
            if tau == "0.0":
                continue
            diff = sum(v != base_sig.get(k) for k, v in _sig(pl).items())
            power[tau] = {"paired_records_differing_from_tau0": diff,
                          "nonvacuous": diff > 0}
    commits = {pl["code_commit"] for pl in arms.values()}
    integrity = {
        "completion": not missing,
        "budget": all(pl["n"] == expected_n for pl in arms.values()),
        "paired_draws": draw_ok,
        "lineage": len(commits) == 1 and all(not pl["code_dirty_scoped"]
                                             for pl in arms.values()),
        "power": bool(power) and all(p["nonvacuous"] for p in power.values()),
    }
    decision = (manifest["gate"]["complete"] if all(integrity.values())
                else manifest["gate"]["invalid_decision"])

    chi50 = {tau: _chi50_by_row(pl["records"]) for tau, pl in arms.items()}
    base = chi50.get("0.0", {})
    delta, classification = {}, None
    if decision == "COMPLETE_P1B2":
        worst = 0.0
        for tau in ("0.1", "0.3"):
            delta[tau] = {}
            for row, b in base.items():
                v = chi50.get(tau, {}).get(row)
                d = None if (b is None or v is None) else float(v - b)
                delta[tau][row] = d
                if d is not None:
                    worst = max(worst, abs(d))
        classification = {"max_abs_delta_chi50": worst, "threshold": 0.03,
                          "verdict": ("PM_ABSTRACTION_HOLDS_ON_TESTED_CELLS"
                                      if worst < 0.03 else
                                      "AIRFRAME_RESIDUAL_CANDIDATE")}
    payload = {
        "schema": "p1b2-plant-readout-v1",
        "manifest_hash": manifest["manifest_hash"],
        "code_commit": next(iter(commits)) if len(commits) == 1 else None,
        "current_code_commit": git_commit(),
        "decision": decision, "integrity": integrity, "missing": missing,
        "power_check": power,
        "summary": {tau: {k: pl[k] for k in ("counts", "episodes_with_clean_crossing",
                                             "clean_crossings_total")}
                    for tau, pl in arms.items()},
        "chi50_by_row": chi50, "delta_chi50_vs_tau0": delta,
        "classification": classification,
        "scope": manifest["scope"], "promotion": manifest["promotion"],
    }
    (OUT / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("decision", "integrity",
                                              "power_check", "classification")},
                     indent=2, ensure_ascii=False))
    return payload


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--readout", action="store_true")
    args = parser.parse_args(argv)
    if args.readout:
        readout()
    else:
        run(smoke=args.smoke)


if __name__ == "__main__":
    main()
