"""P1b-2 row-9 확인 probe 실행기 (manifest = scripts/p1b2_row9_manifest.py).

    python -m scripts.p1b2_row9 --smoke
    python -m scripts.p1b2_row9 --run
    python -m scripts.p1b2_row9 --readout
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from scripts.p1_ladder import _chi50_by_row, _run_config, _write
from scripts.p1b2_row9_manifest import TAUS, load as load_row9_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p1b2_row9"
EXEC_PATHS = ("shepherd", "scripts/p1_ladder.py", "scripts/p1b2_row9.py",
              "scripts/p1b2_row9_manifest.py", "artifacts/p1b2_row9/manifest.json")
LABEL = "c5_scripted_row9"
ATTACKER_OVERRIDES = {"route_gain": 0.5, "sense_range": 30.0}


def _tag(tau: float) -> str:
    return f"tau{str(tau).replace('.', 'p')}"


def _row9_cells(b2: dict) -> list:
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    cells = [c for c in boundary_cells(b2) if int(c["row"]) == 9]
    if len(cells) != 2:
        raise SystemExit(f"expected 2 row-9 boundary cells, got {len(cells)}")
    return cells


def run(*, smoke: bool = False) -> None:
    from shepherd.provenance import git_dirty
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_row9_manifest(), load_b2_manifest()
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    cells = _row9_cells(b2)
    taus = TAUS[:2] if smoke else TAUS
    sub = "smoke" if smoke else "arms"
    for tau in taus:
        path = OUT / sub / f"{LABEL}_{_tag(tau)}.json"
        if path.exists() and not smoke:
            print(f"skip existing {_tag(tau)}", flush=True)
            continue
        out = _run_config(manifest, b2, LABEL, dict(ATTACKER_OVERRIDES),
                          tau_ratio=(None if tau == 0.0 else float(tau)),
                          smoke=smoke, limiter_mode="arc", limiter_kw=c5,
                          cells=cells)
        out["tau_ratio"] = float(tau)
        _write(out, path)


def readout() -> dict:
    from shepherd.provenance import git_commit
    manifest = load_row9_manifest()
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
            if tau != "0.0":
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

    chi50 = {tau: _chi50_by_row(pl["records"]).get("9") for tau, pl in arms.items()}
    judgment = None
    if decision == "COMPLETE_ROW9":
        base = chi50.get("0.0")
        deltas = {tau: (None if base is None or chi50.get(tau) is None
                        else float(chi50[tau] - base))
                  for tau in ("0.1", "0.3")}
        finite = [abs(d) for d in deltas.values() if d is not None]
        judgment = {"chi50_row9": chi50, "delta_vs_tau0": deltas,
                    "threshold": 0.03,
                    "verdict": (None if len(finite) < 2 else
                                "ROW9_FLIP_NOISE" if max(finite) < 0.03
                                else "ROW9_RESIDUAL_DIRECTIONAL"),
                    "censoring_note": ("verdict None = chi50 censored in some arm; "
                                       "report, do not extrapolate")}
    payload = {
        "schema": "p1b2-row9-readout-v1",
        "manifest_hash": manifest["manifest_hash"],
        "code_commit": next(iter(commits)) if len(commits) == 1 else None,
        "current_code_commit": git_commit(),
        "decision": decision, "integrity": integrity, "missing": missing,
        "power_check": power,
        "summary": {tau: pl["counts"] for tau, pl in arms.items()},
        "judgment": judgment,
        "scope": manifest["scope"], "promotion": manifest["promotion"],
    }
    (OUT / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("decision", "integrity",
                                              "power_check", "judgment")},
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
