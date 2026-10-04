"""P1d 전진 교전 limiter 활주로 probe 실행기 (manifest = scripts/p1d_runway_manifest.py).

세계 변형은 P1c 와 동일 (`scripts.p1c_standoff._build_scaled` 재사용). 추가 arm
`fwd` = c5 kw + rho (중점 screen). episode 별 excursion (limiter 평균 수평 반경의
최대값) 을 telemetry 로 기록해 mechanism gate 에 쓴다.

    python -m scripts.p1d_runway --smoke
    python -m scripts.p1d_runway --run [--shard K/N]
    python -m scripts.p1d_runway --readout
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import pathlib

import numpy as np

from scripts.p1c_standoff import _build_scaled, _overrides
from scripts.p1d_runway_manifest import (ARMS, ATTACKERS, EXCURSION_MIN_M, RHO,
                                         SCALES, load as load_p1d_manifest)

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p1d_runway"
EXEC_PATHS = ("shepherd", "scripts/p1c_standoff.py", "scripts/p1d_runway.py",
              "scripts/p1d_runway_manifest.py", "artifacts/p1d_runway/manifest.json")
THRESHOLD = 28


def _limiter(arm: str, c5: dict):
    if arm == "hold":
        return "hold", None
    return "arc", (dict(c5) if arm == "c5" else {**c5, "rho": RHO})


def _excursion(tel: list, target) -> float:
    tgt = np.asarray(target, float)[:2]
    return float(max(np.mean([np.linalg.norm(np.asarray(p, float)[:2] - tgt)
                              for p in row["p_lims"]]) for row in tel))


def _run_arm(manifest, b2, *, scale, att, arm, c5, smoke) -> dict:
    from shepherd.provenance import git_commit, git_dirty
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    from shepherd.scripts.mission_rollout import partition_bin, run_episode
    ev = manifest["evaluation"]
    cells = boundary_cells(b2)[:2] if smoke else boundary_cells(b2)
    epc = 1 if smoke else int(ev["episodes_per_cell"])
    sealed_epc = int(ev["episodes_per_cell"])
    att_ov = _overrides(att)
    mode, kw = _limiter(arm, c5)
    rows = []
    for ci, cell in enumerate(cells):
        for j in range(epc):
            sid = ci * sealed_epc + j
            chi, eta, stack = _build_scaled(ev, b2, cell, sid, att_ov, scale)
            tel: list = []
            r = run_episode(stack.env, stack.scn, stack.lay,
                            seed=int(ev["seed0"]) + sid, policy=None,
                            limiter_mode=mode, limiter_kw=kw, fire_mode="clean",
                            telemetry=tel)
            rows.append({"cell_id": cell["cell_id"], "scenario_id": sid,
                         "chi": chi, "eta": eta, "bin": partition_bin(r),
                         "fire": r.fire_step is not None,
                         "clean_crossings": int(r.clean_crossings),
                         "steps": int(r.steps),
                         "excursion": round(_excursion(tel, stack.lay.target), 3)})
    counts = Counter(r["bin"] for r in rows)
    return {"schema": "p1d-runway-arm-v1" + ("-smoke" if smoke else ""),
            "manifest_hash": manifest["manifest_hash"],
            "scale": scale, "attacker": att["label"], "arm": arm,
            "code_commit": git_commit(), "code_dirty_scoped": git_dirty(EXEC_PATHS),
            "n": len(rows), "counts": dict(sorted(counts.items())),
            "mean_steps": round(float(np.mean([r["steps"] for r in rows])), 2),
            "mean_excursion": round(float(np.mean([r["excursion"] for r in rows])), 3),
            "records": rows}


def run(*, shard: str | None = None, smoke: bool = False) -> None:
    from shepherd.provenance import git_dirty
    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    manifest, b2 = load_p1d_manifest(), load_b2_manifest()
    if not smoke and git_dirty(EXEC_PATHS):
        raise SystemExit(f"dirty execution code: {git_dirty(EXEC_PATHS)}")
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]
    jobs = [(k, att) for k in SCALES for att in ATTACKERS]
    if smoke:
        jobs = [(1, ATTACKERS[0]), (4, ATTACKERS[0])]
    if shard:
        i, n = (int(x) for x in shard.split("/"))
        jobs = jobs[i::n]
    sub = "smoke" if smoke else "arms"
    for k, att in jobs:
        for arm in ARMS:
            path = OUT / sub / f"k{k}_{att['label']}_{arm}.json"
            if path.exists() and not smoke:
                print(f"skip existing k{k}_{att['label']}_{arm}", flush=True)
                continue
            out = _run_arm(manifest, b2, scale=k, att=att, arm=arm, c5=c5, smoke=smoke)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
            # smoke 는 mechanism 만 본다 (결과 bin 은 출력하지 않음 — 봉인 전 결과 엿보기 금지)
            print(f"k{k}/{att['label']}/{arm}: n={out['n']} steps={out['mean_steps']} "
                  f"excursion={out['mean_excursion']}"
                  + ("" if smoke else f" N={out['counts'].get('N', 0)}"
                     f" H={out['counts'].get('H_illegal', 0)}"), flush=True)


def _sum(arms, k, arm, key):
    return sum(pl["counts"].get(key, 0) for (kk, a, ar), pl in arms.items()
               if kk == k and ar == arm)


def readout() -> dict:
    from shepherd.provenance import git_commit
    manifest = load_p1d_manifest()
    expected_n = int(manifest["evaluation"]["episodes_per_arm_per_scale_per_attacker"])
    arms, missing = {}, []
    for k in SCALES:
        for att in ATTACKERS:
            for arm in ARMS:
                p = OUT / "arms" / f"k{k}_{att['label']}_{arm}.json"
                if p.exists():
                    arms[(k, att["label"], arm)] = json.loads(p.read_text(encoding="utf-8"))
                else:
                    missing.append(f"k{k}_{att['label']}_{arm}")

    draws, draw_ok = {}, True
    for pl in arms.values():
        for r in pl["records"]:
            val = (round(r["chi"], 12), round(r["eta"], 12))
            draw_ok &= draws.setdefault((r["cell_id"], r["scenario_id"]), val) == val
    commits = {pl["code_commit"] for pl in arms.values()}

    def _mean(k, arm, key):
        v = [pl[key] for (kk, a, ar), pl in arms.items() if kk == k and ar == arm]
        return float(np.mean(v)) if v else None

    hold_steps = {k: _mean(k, "hold", "mean_steps") for k in SCALES}
    excursion = {f"k{k}_{arm}": _mean(k, arm, "mean_excursion")
                 for k in SCALES for arm in ARMS}
    fwd4 = excursion["k4_fwd"]
    integrity = {
        "completion": not missing,
        "budget": all(pl["n"] == expected_n for pl in arms.values()),
        "paired_draws": draw_ok,
        "lineage": len(commits) == 1 and all(not pl["code_dirty_scoped"]
                                             for pl in arms.values()),
        "power_steps_increase": (None not in (hold_steps[1], hold_steps[4])
                                 and hold_steps[4] > hold_steps[1]),
        "mechanism_excursion": fwd4 is not None and fwd4 >= EXCURSION_MIN_M,
    }
    decision = (manifest["gate"]["complete"] if all(integrity.values())
                else manifest["gate"]["invalid_decision"])

    D = {str(k): _sum(arms, k, "fwd", "N") - _sum(arms, k, "c5", "N") for k in SCALES}
    vs_hold = {str(k): _sum(arms, k, "fwd", "N") - _sum(arms, k, "hold", "N")
               for k in SCALES}
    classification = None
    if decision == "COMPLETE_P1D":
        delta = D["4"] - D["1"]
        dH = _sum(arms, 4, "fwd", "H_illegal") - _sum(arms, 4, "c5", "H_illegal")
        verdict = ("RUNWAY_DOES_NOT_OPEN" if delta < THRESHOLD
                   else "RUNWAY_GAIN_UNSAFE" if dH >= THRESHOLD
                   else "RUNWAY_OPENS_SHAPING")
        classification = {"D_fwd_minus_c5_pooled_560": D, "D4_minus_D1": delta,
                          "dH_illegal_k4_fwd_minus_c5": dH, "threshold": THRESHOLD,
                          "verdict": verdict,
                          "scope_note": "tested rule, rho, range and scaling model only"}
    payload = {
        "schema": "p1d-runway-readout-v1",
        "manifest_hash": manifest["manifest_hash"],
        "code_commit": next(iter(commits)) if len(commits) == 1 else None,
        "current_code_commit": git_commit(),
        "decision": decision, "integrity": integrity, "missing": missing,
        "per_arm": {f"k{k}_{a}_{arm}": {kk: pl[kk] for kk in
                    ("counts", "mean_steps", "mean_excursion")}
                    for (k, a, arm), pl in sorted(arms.items())},
        "hold_mean_steps_by_scale": hold_steps,
        "mean_excursion_by_scale_arm": excursion,
        "fwd_minus_hold_pooled_560": vs_hold,
        "classification": classification,
        "scope": manifest["scope"], "promotion": manifest["promotion"],
    }
    (OUT / "readout.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("decision", "integrity", "classification")},
                     indent=2, ensure_ascii=False))
    return payload


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--readout", action="store_true")
    ap.add_argument("--shard", default=None, help="K/N over (scale, attacker) jobs")
    a = ap.parse_args(argv)
    if a.readout:
        readout()
    else:
        run(shard=a.shard, smoke=a.smoke)


if __name__ == "__main__":
    main()
