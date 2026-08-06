"""리뷰 3 반증 (B) — contact Pk sweep (docs/54 §3.2, 사전등록 후 실행).

`Pk=1` 무력화 1.000 은 semantics check 다. 여기서는 boxed 17판(F-arm 실 계약)
에서 Pk ∈ {0, .25, .5, .75, 1} × Bernoulli draw 를 스윕해 곡선의 지위로 낮춘다.

판정 (성능 대역 없음): (i) event 당 kill 빈도가 Pk 의 이항 CI95 안 (구현 sanity)
(ii) episode 무력화·침투 vs Pk 곡선 보고 -- 재시도 기회(첫 접촉 실패 후 추가
contact event)가 곡선을 Pk 위로 올리는지가 관심 축. contact-specific lethality
모형의 부재는 이 sweep 으로 해소되지 않는다 (리뷰 3 §4 기각 유지).
torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
import numpy as np

from shepherd.env_sys import SystemSpec
from shepherd.scripts.boxed_arm_audit import _run

__all__ = ["pk_sweep"]

EPISODES = (3, 12, 15, 17, 18, 19, 29, 30, 34, 41, 42, 44, 47, 49, 51, 52, 57)
PKS = (0.0, 0.25, 0.5, 0.75, 1.0)


def pk_sweep(seed0: int = 0) -> dict:
    out = {}
    for pk in PKS:
        # Pk 0/1 은 Bernoulli 가 단락되므로 draw 반복이 무의미 -> seed 1개
        seeds = (0,) if pk in (0.0, 1.0) else (0, 1, 2)
        rows = []
        for j in seeds:
            spec = SystemSpec(enabled=True, contact_resolver=True,
                              miss_terminates=False, p_kill=pk,
                              seed_ns=f"pk_sweep_{j}")
            for ep in EPISODES:
                r = _run(ep, "F", seed0, system=spec)
                rows.append({k: r[k] for k in
                             ("episode", "penetrated", "hard_kill",
                              "contact_events", "pk_fail", "kills",
                              "veto_events")} | {"bern_seed": j})
        n = len(rows)
        kills = sum(r["kills"] for r in rows)
        fails = sum(r["pk_fail"] for r in rows)
        events = kills + fails                      # 해소된 event (veto 제외)
        out[str(pk)] = {
            "n_runs": n,
            "neutralized": round(sum(r["hard_kill"] for r in rows) / n, 3),
            "penetrated": round(sum(r["penetrated"] for r in rows) / n, 3),
            "events_resolved": events,
            "event_kill_freq": round(kills / events, 3) if events else None,
            "mean_events_per_ep": round(events / n, 2),
            "veto_total": sum(r["veto_events"] for r in rows),
            "records": rows,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="리뷰3 (B) contact Pk sweep")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = pk_sweep()
    print(f"{'Pk':>5} {'무력화':>7} {'침투':>6} {'event/판':>8} {'event kill 빈도':>14}")
    for pk, v in r.items():
        ekf = "-" if v["event_kill_freq"] is None else f"{v['event_kill_freq']:.3f}"
        print(f"{pk:>5} {v['neutralized']:>7.3f} {v['penetrated']:>6.3f} "
              f"{v['mean_events_per_ep']:>8.2f} {ekf:>14}")
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
