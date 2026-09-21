"""W5 MARL 진입 판정 — B2 측정과 분리된 연구 투자 gate (docs/107).

    python -m shepherd.scripts.b2_w5_decision

RULE_COOP 의 clean-net P(N)만으로 seed별 isotonic chi50을 구한다. PASS는
MAPPO hyperparameter pilot 착수만 허용하며 학습 성능이나 협력 우월성을 뜻하지
않는다. forced-fire는 원인 진단으로만 기록하고 primary와 합치지 않는다.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.b2_check import PRIMARY_DIR, check               # noqa: E402
from shepherd.scripts.b2_manifest import OUT_DIR, load                 # noqa: E402

READOUT = OUT_DIR / "readout.json"
FORCED_FIRE = OUT_DIR / "forced_fire_readout.json"
OUT = OUT_DIR / "w5_decision.json"

EXECUTION_COMMIT = "fd4eb19"
PRIMARY_ARM = "RULE_COOP"
MIN_SEEDS_PER_ROW = 2
MIN_ROWS = 12
MIN_ROWS_PER_SLICE = 5


def _pav_decreasing(y: np.ndarray) -> np.ndarray:
    """R2a ``pav_decreasing``와 같은 equal-weight PAV; SciPy import는 피한다."""
    values, weights, counts = [], [], []
    for value in y:
        values.append(float(value)); weights.append(1.0); counts.append(1)
        while len(values) > 1 and values[-2] < values[-1]:
            pooled = ((values[-2] * weights[-2] + values[-1] * weights[-1])
                      / (weights[-2] + weights[-1]))
            weights[-2] += weights[-1]
            counts[-2] += counts[-1]
            values.pop(); weights.pop(); counts.pop(); values[-1] = pooled
    return np.repeat(values, counts)


def _cross50(x: np.ndarray, p: np.ndarray) -> float:
    """R2a ``cross50``와 같은 비증가 0.5 crossing 선형보간."""
    if p[0] < 0.5 or p[-1] >= 0.5:
        return float("nan")
    i = int(np.argmax(p < 0.5))
    x0, x1, p0, p1 = x[i - 1], x[i], p[i - 1], p[i]
    return float(x0 + (x1 - x0) * (p0 - 0.5) / (p0 - p1)) if p0 != p1 else float(x1)


def _seed_crossing(cells: list[dict], readout: dict, arm: str, seed: int) -> dict:
    ordered = sorted(cells, key=lambda c: c["chi"])
    x = np.asarray([c["chi"] for c in ordered], dtype=float)
    rates = [readout["by_cell_arm_seed"][f"{c['cell_id']}|{arm}|{seed}"]
             for c in ordered]
    assert len({r["n"] for r in rates}) == 1, "equal-weight PAV requires equal cell counts"
    p = np.asarray([r["p_N"] for r in rates], dtype=float)
    fitted = _pav_decreasing(p)
    crossing = _cross50(x, fitted)
    estimable = bool(math.isfinite(crossing))
    return {
        "seed": seed,
        "chi": x.tolist(),
        "p_N_raw": p.tolist(),
        "p_N_isotonic": fitted.tolist(),
        "chi50": float(crossing) if estimable else None,
        "estimable": estimable,
    }


def frontier(m: dict, readout: dict, arm: str = PRIMARY_ARM) -> dict:
    by_row: dict[int, list[dict]] = {}
    for cell in m["cells"]:
        by_row.setdefault(cell["row"], []).append(cell)

    rows = []
    for row_id, cells in sorted(by_row.items()):
        seeds = [_seed_crossing(cells, readout, arm, seed)
                 for seed in m["crn"]["seeds"]]
        n_est = sum(s["estimable"] for s in seeds)
        c0 = cells[0]
        rows.append({
            "row": row_id,
            "lam_slice": c0["lam_slice"],
            "lam": c0["lam"],
            "eta": c0["eta"],
            "n_seed_estimable": n_est,
            "n_seed_total": len(seeds),
            "row_estimable": n_est >= MIN_SEEDS_PER_ROW,
            "seeds": seeds,
        })

    slice_counts = {}
    for sl in sorted({r["lam_slice"] for r in rows}):
        subset = [r for r in rows if r["lam_slice"] == sl]
        slice_counts[str(sl)] = {
            "row_estimable": sum(r["row_estimable"] for r in subset),
            "row_total": len(subset),
        }
    n_rows = sum(r["row_estimable"] for r in rows)
    return {
        "arm": arm,
        "rows": rows,
        "row_estimable": n_rows,
        "row_total": len(rows),
        "slice_counts": slice_counts,
        "any_censored": any(not s["estimable"] for r in rows for s in r["seeds"]),
    }


def coverage_pass(result: dict) -> bool:
    return (
        not result["any_censored"]
        and result["row_estimable"] >= MIN_ROWS
        and all(v["row_estimable"] >= MIN_ROWS_PER_SLICE
                for v in result["slice_counts"].values())
    )


def decide(readout_path: pathlib.Path = READOUT,
           forced_fire_path: pathlib.Path = FORCED_FIRE,
           out: pathlib.Path = OUT) -> dict:
    m = load()
    readout = json.loads(readout_path.read_text(encoding="utf-8"))
    forced = json.loads(forced_fire_path.read_text(encoding="utf-8"))

    checks = check(PRIMARY_DIR, EXECUTION_COMMIT)
    primary_valid = (
        all(ok for _, ok, _ in checks)
        and readout["manifest_hash"] == m["manifest_hash"]
        and readout["b0_v3_hash"] == m["b0_v3_hash"]
        and readout["arm_pairing_ok"]
        and readout["identity_ok_all"]
    )
    forced_valid = (
        forced["manifest_hash"] == m["manifest_hash"]
        and len(forced["shards"]) == 8
        and all(s["finished"] and s["code_commit"] == "fbe3f65"
                for s in forced["shards"])
        and forced["n_probed"] == forced["n_selected"] == 436
        and forced["n_forced_fired"] == 436
        and forced["pre_intervention_identical_all"]
    )
    prerequisites_valid = (
        primary_valid and forced_valid
        and (ROOT / "docs/108_b0v3_amendment_a1_illegal_engagement.md").exists()
    )
    rule = frontier(m, readout, PRIMARY_ARM)
    solo = frontier(m, readout, "SOLO")
    passes = prerequisites_valid and coverage_pass(rule)
    decision = ("PASS" if passes else
                ("UNDETERMINED" if not prerequisites_valid or rule["any_censored"]
                 else "FAIL"))

    result = {
        "schema": "b2-w5-decision-v1",
        "date": "2026-09-22",
        "decision": decision,
        "authorization": (
            "MAPPO hyperparameter pilot may start; W6 training contract must be sealed "
            "before main training"
            if passes else "No MAPPO optimizer update authorized"
        ),
        "meaning": (
            "The clean-net frontier is measurable in the current B0 v3 world. "
            "This does not establish learned performance, cooperative superiority, "
            "Q1 novelty, or physical validity."
        ),
        "inputs": {
            "manifest_hash": m["manifest_hash"],
            "b0_v3_hash": m["b0_v3_hash"],
            "primary_execution_commit": EXECUTION_COMMIT,
            "primary_readout": readout_path.relative_to(ROOT).as_posix(),
            "forced_fire_readout": forced_fire_path.relative_to(ROOT).as_posix(),
            "illegal_engagement_amendment": "docs/108_b0v3_amendment_a1_illegal_engagement.md",
        },
        "validity": {
            "pass": prerequisites_valid,
            "primary_pass": primary_valid,
            "forced_fire_pass": forced_valid,
            "server_replay_3_of_3": "manual record in a5355a7 and docs/108",
            "b2_check": [{"name": name, "pass": ok, "detail": detail}
                         for name, ok, detail in checks],
            "arm_pairing_ok": readout["arm_pairing_ok"],
            "identity_ok_all": readout["identity_ok_all"],
        },
        "thresholds": {
            "seed_estimable_per_row": f">={MIN_SEEDS_PER_ROW}/3",
            "rows": f">={MIN_ROWS}/14",
            "rows_per_slice": f">={MIN_ROWS_PER_SLICE}/7",
            "extension": "required only if the primary RULE_COOP crossing is censored",
        },
        "primary_frontier": rule,
        "secondary_solo_frontier": solo,
        "primary_diagnostics": {
            "p_N_solo": readout["overall"]["SOLO"]["p_N"],
            "p_N_rule": readout["overall"]["RULE_COOP"]["p_N"],
            "delta_p_N": (readout["overall"]["RULE_COOP"]["p_N"]
                          - readout["overall"]["SOLO"]["p_N"]),
            "p_H_illegal_rule": readout["overall"]["RULE_COOP"]["p_H_illegal"],
            "interpretation": "diagnostic only; RULE_COOP minus SOLO is not the W5 gate",
        },
        "forced_fire_diagnostic": {
            "pooled_with_primary": False,
            "n_probed": forced["n_probed"],
            "n_forced_fired": forced["n_forced_fired"],
            "pre_intervention_identical_all": forced["pre_intervention_identical_all"],
            "n_net_capture_after_force": forced["n_net_capture_after_force"],
            "recovery_rate_given_forced": forced["recovery_rate_given_forced"],
            "reading": "FIRE gate is not the main cause; failure is attainability/controller-limited",
        },
        "deferred_to_w6": (
            "Seal the BC/training contract before main training: pretrain the capturer/fire "
            "head only, start the limiter neutral, and exclude H_illegal episodes from "
            "positive demonstrations."
        ),
    }
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return result


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="W5 MAPPO-entry decision (docs/107)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    result = decide(out=pathlib.Path(args.out))
    f = result["primary_frontier"]
    slices = ", ".join(
        f"lambda{key}={value['row_estimable']}/{value['row_total']}"
        for key, value in f["slice_counts"].items()
    )
    print(f"{result['decision']} - rows {f['row_estimable']}/{f['row_total']} "
          f"({slices}), censored={f['any_censored']}")
    print(f"  forced-fire recovery "
          f"{result['forced_fire_diagnostic']['n_net_capture_after_force']}/"
          f"{result['forced_fire_diagnostic']['n_forced_fired']} (diagnostic only)")
    print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
