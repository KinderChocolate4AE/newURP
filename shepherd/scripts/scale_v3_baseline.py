"""V6 — v3 nominal nested arm baseline (docs/60 §5 r4, 학습 없음 · sanity 전용).

    python -m shepherd.scripts.scale_v3_baseline --arm V3-FULL --eps 0 25 \
        --out results/v6_full_0_25.json

hold/clean · 각 arm n=100 · 수락대역 없음 · **성능 판정 아님**. 관측 항목
(a)~(f) 는 docs/60 §5 사전 선언. TRAIN 분포(docs/61) 범위를 이 결과로
튜닝하지 않는다 — sanity 전용. full sampler (fire=clean 이 v_shot 소비).
샤딩 = long-run 정책. torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import numpy as np

from shepherd.agents.attacker_ladder import _general_action
from shepherd.env_adv import attach_attacker
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.notify import ntfy
from shepherd.scale_v2 import V3_ARMS
from shepherd.scripts.mission_rollout import run_episode
from shepherd.scripts.threat_v3_gates import _base_env

__all__ = ["v6_episode", "v6"]


def v6_episode(arm_name: str, ep: int) -> dict:
    arm = V3_ARMS[arm_name]
    st = build_m4_env(
        0, ep,
        system=SystemSpec(enabled=True, contact_resolver=True,
                          miss_terminates=False, p_kill=1.0),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=arm["attacker"], spawn=arm["spawn"], standby=arm["standby"],
        extra_cfg=dict(arm["cfg"]))
    base = _base_env(st.env)
    spec = arm["attacker"]

    diags = []

    def instrumented(p_att, v_att, **kw):
        d = {}
        out = _general_action(spec, p_att, v_att, diag=d, **kw)
        d["z"] = float(p_att[2])
        diags.append(d)
        return out

    attach_attacker(base, instrumented,
                    phase=float(getattr(base, "_attacker_phase", 0.0)))
    r = run_episode(st.env, st.scn, st.lay, seed=ep,
                    limiter_mode="hold", fire_mode="clean")

    # --- 관측 항목 (docs/60 §5 (a)~(f)) -------------------------------------
    n = max(len(diags), 1)
    route_on = [d for d in diags if float(np.linalg.norm(d["route_req"])) > 0.0]
    route_z_dom = [d for d in route_on
                   if abs(d["route_req"][2])
                   > 0.7 * float(np.linalg.norm(d["route_req"]))]
    # (e) FULL 초기 재배치 기하비: 최악 호(pi) 이동시간 vs 실측 도달시간
    v_lim = float(base.backend.by_name(base.limiter_ids[0]).limits.v_max)
    r_standby = (float(np.linalg.norm(
        np.asarray(base.layout.limiter_p0[0], float)
        - np.asarray(base.layout.target, float))))
    t_redeploy = math.pi * r_standby / max(v_lim, 1e-9)
    t_arrival = r.steps * float(base.dt)

    return dict(
        episode=ep, arm=arm_name, label=r.label, steps=r.steps,
        fire_step=r.fire_step, wasted=r.wasted_fire,
        min_target_dist=round(r.min_target_dist, 2),
        route_active_frac=round(len(route_on) / n, 4),                  # (a)
        route_z_dominant_frac=round(len(route_z_dom) / max(len(route_on), 1), 4),
        z_max=round(float(max(abs(d["z"]) for d in diags)), 2),         # (b)
        clip_frac=round(float(np.mean([d["clipped"] for d in diags])), 4),  # (c)
        sprint_clip_frac=round(float(np.mean(
            [d["clipped"] for d in diags if d["d_asset"] <= 60.0] or [0.0])), 4),
        # (d) sprint/slowdown "실제 개입" = v_ref 가 v_nominal 에서 이탈한 스텝
        sprint_steps=sum(1 for d in diags
                         if d["v_ref"] > d["v_nominal"] + 1e-9),
        slowdown_steps=sum(1 for d in diags
                           if d["v_ref"] < d["v_nominal"] - 1e-9),
        redeploy_ratio=round(t_redeploy / max(t_arrival, 1e-9), 3),     # (e)
        max_speed_ratio=round(float(max(
            (d["speed"] / d["v_max"]) for d in diags if d["v_max"])), 4),
    )


def v6(arm_name: str, eps) -> list:
    rows = []
    for ep in eps:
        row = v6_episode(arm_name, ep)
        rows.append(row)
        print(f"{arm_name} ep{ep:>3}: {row['label']:>11} steps={row['steps']:>4} "
              f"route={row['route_active_frac']:.2f} "
              f"zdom={row['route_z_dominant_frac']:.2f} zmax={row['z_max']:>5} "
              f"clip={row['clip_frac']:.2f}", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser(description="V6 v3 nominal nested baseline")
    ap.add_argument("--arm", required=True, choices=sorted(V3_ARMS))
    ap.add_argument("--eps", type=int, nargs=2, default=[0, 100],
                    metavar=("A", "B"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = v6(a.arm, range(a.eps[0], a.eps[1]))
    labs = {}
    for r in rows:
        labs[r["label"]] = labs.get(r["label"], 0) + 1
    print(f"{a.arm} labels:", labs)
    out = a.out or f"results/v6_{a.arm.lower().replace('-', '_')}_{a.eps[0]}_{a.eps[1]}.json"
    p = pathlib.Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(dict(contract="docs/60 §5 V6 (r4)", arm=a.arm,
                                 labels=labs, records=rows),
                            indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {out}")
    ntfy(f"V6 {a.arm} [{a.eps[0]},{a.eps[1]}) done: {labs}", title="v6")


if __name__ == "__main__":
    main()
