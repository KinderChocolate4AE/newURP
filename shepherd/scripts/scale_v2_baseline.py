"""V4 — 스케일 v2 첫 baseline (docs/59 §3, 수락대역 없음 · 새 regime 첫 측정).

hold/clean · F-flags · Pk=1 · n=100. --eps 샤딩 가능 (long-run policy).
torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
from typing import List

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.scale_v2 import SCALE_V2_CFG, SCALE_V2_SPAWN
from shepherd.scripts.boxed_arm_audit import _sysenv
from shepherd.scripts.mission_rollout import run_episode

__all__ = ["baseline"]


def baseline(eps) -> List[dict]:
    rows = []
    for ep in eps:
        st = build_m4_env(
            0, ep,
            system=SystemSpec(enabled=True, contact_resolver=True,
                              miss_terminates=False, p_kill=1.0),
            reward=RewardSpec(w_kill=0.5, enabled=True),
            attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
            spawn=SCALE_V2_SPAWN, extra_cfg=dict(SCALE_V2_CFG))
        r = run_episode(st.env, st.scn, st.lay, seed=ep,
                        limiter_mode="hold", fire_mode="clean")
        se = _sysenv(st.env)
        rows.append(dict(episode=ep, label=r.label, steps=r.steps,
                         fire_step=r.fire_step, wasted=r.wasted_fire,
                         net_spent=bool(se.net_spent),
                         min_target_dist=round(r.min_target_dist, 2)))
        print(f"ep{ep:>3}: {r.label:>11} steps={r.steps:>3} fire@{r.fire_step} "
              f"min_d={r.min_target_dist:.1f}", flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="scale v2 baseline (docs/59 V4)")
    ap.add_argument("--eps", type=int, nargs=2, default=[0, 100],
                    metavar=("A", "B"), help="에피소드 range [A, B)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = baseline(range(a.eps[0], a.eps[1]))
    labs = {}
    for r in rows:
        labs[r["label"]] = labs.get(r["label"], 0) + 1
    print("labels:", labs)
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(dict(contract="docs/59 V4", records=rows),
                                indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
