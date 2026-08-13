"""리드타임 진단 — 스폰 거리를 **T1 가시성 안에서만** 늘려 물리 요격이 회복되는가.

증거 등급: **EXPLORATORY / post-result diagnostic.** E2-B(등록된 근접 세계)를
덮어쓰지 않는다. 별도 질문이다:

    E2-B          : registered short-range world 에서의 modality gap
    본 진단        : does added lead time recover physical interception?

★ confound 제거 방식 (2026-08-13 재설계)
-----------------------------------------
T1 의 route 항은 `sense_range` 안의 limiter 만 본다. 등록값 30 m 를 그대로 두고
스폰을 늘리면 **대응시간 증가**와 **공격자가 초반에 방어자를 못 보는 세계로의
전환**이 섞인다 (실측: start_x=36 에서 전-limiter 가시 비율이 0.72 로 깨졌다).

경계 근처에서 조심스럽게 도는 대신 **sense 를 아예 무제한으로 고정**한다.
그러면 arm 사이에서 변하는 것은 **리드타임 하나뿐**이다.

  ⇒ 본 진단의 공격자는 **등록된 T1 점(route 0.5 / sense 30) 이 아니다.**
     "T1-route with unlimited sensing" 이라는 **진단 변형**이며, 결과를 등록된
     T1 수치와 나란히 놓지 않는다.

지평선도 구속되지 않게 arm 마다 늘린다 (episode_len 이 binding 하면 TRUNCATED 가
리드타임 효과를 가린다). 최소 v=8 m/s 기준 도달시간 + 여유 2 s.

계측 (docs/83 §14 이후 시각 진단에서 요청된 4 종):
  1. T_HK        시작~하드킬 시간
  2. t_course    limiter 가 실제 요격 코스를 형성하기 시작하는 시점
                 (LOS rate |lam_dot| 이 낮아지면서 거리도 줄어드는 첫 스텝 = 정측방위)
  3. closest     최근접 거리 (contact miss distance) 와 그 시각
  4. 순서        침투가 먼저인가, limiter 가 늦게 도착하는가

    python -m shepherd.scripts.lead_time_diag --n 300 --out results/lead_time_diag.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
from typing import List, Optional

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_config import m4_config
from shepherd.m4_env import build_m4_env
from shepherd.scripts.recoverability_probe import _Driver, _sysenv
from shepherd.spawn_rand import SpawnSpec
from shepherd.stats import wilson

__all__ = ["run_arm", "episode_metrics"]

SENSE = float("inf")  # ★ 무제한 — 가시성을 교란에서 제거 (등록 T1 아님)
SENSE_REGISTERED = 30.0   # 등록 T1 값 (가시성 진단 보고용)
V_MIN = 8.0           # THREAT_BRACKET 하한 — 지평선 산정 기준
ROUTE = 0.5
LOS_RATE_LOW = 0.15   # rad/s. 정측방위(constant bearing) 근사 판정 문턱 (진단용)


def _build(ep: int, start_x: float):
    return build_m4_env(
        0, ep,
        system=ratified_system(),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                              route_gain=ROUTE, sense_range=SENSE),
        spawn=SpawnSpec(),
        extra_cfg={"train.layout.adversary_start_x": float(start_x),
                   # 지평선이 구속하면 TRUNCATED 가 리드타임 효과를 가린다.
                   "train.episode_len": _horizon(start_x)})


def _horizon(start_x: float, dt: float = 0.05, margin_s: float = 2.0) -> int:
    """최저 속도 공격자가 도달하고도 남을 만큼 (arm 마다 비구속으로)."""
    return int(math.ceil((start_x / V_MIN + margin_s) / dt))


def episode_metrics(ep: int, start_x: float) -> dict:
    st = _build(ep, start_x)
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    se = d.se
    dt = float(env.dt)
    r_contact = float(se.spec.r_contact if se.spec.r_contact is not None
                      else env.kill_radius)

    # t=0 가시성: sense_range 안의 limiter 수 (confound monitor)
    lims0, _, att0 = env._states()
    p0 = env._p(att0)
    sep0 = [float(np.linalg.norm(p0 - env._p(s))) for s in lims0]
    # 무제한 sense 이므로 실제 가시성은 항상 전부. 등록 T1(30 m) 이었다면
    # 몇 기가 보였을지를 **참고로만** 기록한다 (해석에 쓰지 않는다).
    vis0 = sum(1 for s in sep0 if s <= SENSE_REGISTERED)

    hk_step = None
    t_course = None
    best = (float("inf"), None)      # (최근접 거리, 스텝)
    prev = None
    for t in range(int(lay.episode_len)):
        fi = d.step(limiter_mode="intercept", baseline_commit=True)
        lims2, _, att2 = env._states()
        p_att, v_att = env._p(att2), env._v(att2)
        # 살아있는 limiter 중 최근접
        cand = [(float(np.linalg.norm(p_att - env._p(lims2[i]))), i)
                for i in range(len(lims2)) if i not in se.retired]
        if cand:
            dmin, imin = min(cand)
            if dmin < best[0]:
                best = (dmin, t)
            # LOS rate: 최근접 limiter 기준 시선각속도
            rel = p_att - env._p(lims2[imin])
            rv = v_att - env._v(lims2[imin])
            rn = float(np.linalg.norm(rel))
            if rn > 1e-6:
                u = rel / rn
                lam = float(np.linalg.norm(rv - float(rv @ u) * u)) / rn
                closing = (prev is not None and rn < prev)
                if t_course is None and closing and lam < LOS_RATE_LOW:
                    t_course = t
            prev = rn
        if hk_step is None and bool(fi.get("hard_kill", False)):
            hk_step = t
        if d.done:
            break

    term = d.t
    return {"episode": ep, "start_x": float(start_x), "label": d.label,
            "a_att": float(env.a_att_max), "att_speed": float(env.v_nominal),
            "T_terminal": round(term * dt, 3),
            "T_HK": None if hk_step is None else round(hk_step * dt, 3),
            "t_course": None if t_course is None else round(t_course * dt, 3),
            "closest": round(best[0], 3),
            "t_closest": None if best[1] is None else round(best[1] * dt, 3),
            "miss_vs_contact": round(best[0] - r_contact, 3),
            "closest_after_terminal": bool(best[1] is not None and best[1] >= term),
            "sep0_min": round(min(sep0), 2), "sep0_max": round(max(sep0), 2),
            "vis0_if_registered": vis0, "n_lim": len(sep0),
            "horizon_s": round(_horizon(start_x) * dt, 2)}


def run_arm(n: int, start_x: float, *, every: int = 25) -> List[dict]:
    """진행 로그 포함 (장기런 정책: flush 하는 진행 로그 + arm 별 incremental 저장)."""
    import time
    rows, t0 = [], time.time()
    for ep in range(n):
        rows.append(episode_metrics(ep, start_x))
        if (ep + 1) % every == 0 or ep + 1 == n:
            el = time.time() - t0
            hk = sum(1 for r in rows if r["label"] == "HARD_KILL")
            print(f"    [x={start_x:.0f}] {ep+1}/{n}  {el:6.1f}s  "
                  f"({el/(ep+1):.2f} s/ep, ETA {el/(ep+1)*(n-ep-1):5.0f}s)  "
                  f"HK {hk/(ep+1):.3f}", flush=True)
    return rows


def _stat(v):
    v = [x for x in v if x is not None]
    if not v:
        return None
    a = np.array(v, float)
    return {"n": len(v), "med": round(float(np.median(a)), 3),
            "p25": round(float(np.percentile(a, 25)), 3),
            "p75": round(float(np.percentile(a, 75)), 3)}


def main() -> None:
    ap = argparse.ArgumentParser(description="리드타임 진단 (exploratory)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--start-x", type=float, nargs="*",
                    default=[24.0, 36.0, 48.0, 60.0])
    ap.add_argument("--out", default="results/lead_time_diag.json")
    a = ap.parse_args()

    base = float(m4_config()["train"]["layout"]["adversary_start_x"])
    print(f"[리드타임 진단 · EXPLORATORY] n={a.n}/arm · T1(route {ROUTE}, sense {SENSE}) "
          f"· intercept + commit · 기준 start_x={base}", flush=True)
    arms = {}
    p_out = pathlib.Path(a.out)
    p_out.parent.mkdir(parents=True, exist_ok=True)
    for X in a.start_x:
        rows = run_arm(a.n, X)
        n = len(rows)
        hk = sum(1 for r in rows if r["label"] == "HARD_KILL")
        # ★ _Driver.label 은 "CAPTURED" 를 쓴다 (mission_rollout 의 NET_CAPTURE 와
        #   어휘가 다르다). 처음에 이걸 놓쳐 net 이 전부 0 으로 나왔다.
        nc = sum(1 for r in rows
                 if r["label"] in ("CAPTURED", "NET_CAPTURE", "CAPTURE_WITH_CONTACT"))
        pen = sum(1 for r in rows if r["label"] == "PENETRATED")
        wl, wh = wilson(hk, n)
        trunc = sum(1 for r in rows if r["label"] == "TRUNCATED")
        vis_full = sum(1 for r in rows if r["vis0_if_registered"] == r["n_lim"])
        arms[str(X)] = {
            "start_x": X, "n": n,
            "p_hk": hk / n, "p_hk_wilson": [wl, wh],
            "p_net": nc / n, "p_pen": pen / n, "p_trunc": trunc / n,
            "horizon_s": rows[0]["horizon_s"],
            "T_terminal": _stat([r["T_terminal"] for r in rows]),
            "T_HK": _stat([r["T_HK"] for r in rows]),
            "t_course": _stat([r["t_course"] for r in rows]),
            "closest": _stat([r["closest"] for r in rows]),
            "t_closest": _stat([r["t_closest"] for r in rows]),
            "n_course_formed": sum(1 for r in rows if r["t_course"] is not None),
            "n_closest_after_term": sum(1 for r in rows if r["closest_after_terminal"]),
            # ★ confound monitor
            "vis0_full_frac_if_registered": vis_full / n,
            "sep0_min": _stat([r["sep0_min"] for r in rows]),
            "sep0_max": _stat([r["sep0_max"] for r in rows]),
            "records": rows,
        }
        A = arms[str(X)]
        print(f"\n  start_x={X:5.1f}  HK {hk/n:.3f} [{wl:.3f},{wh:.3f}] · net {nc/n:.3f} "
              f"· pen {pen/n:.3f}", flush=True)
        print(f"    T_terminal med {A['T_terminal']['med']:.2f}s · "
              f"T_HK med {A['T_HK']['med'] if A['T_HK'] else float('nan')} · "
              f"코스형성 {A['n_course_formed']}/{n}"
              + (f" (t_course med {A['t_course']['med']:.2f}s)" if A['t_course'] else ""))
        print(f"    최근접 med {A['closest']['med']:.2f} m (t {A['t_closest']['med']:.2f}s) "
              f"· 접촉반경 0.75")
        print(f"    지평선 {A['horizon_s']:.1f}s · TRUNCATED {trunc/n:.3f} · "
              f"초기 이격 max med {A['sep0_max']['med']:.1f} m")
        print(f"    (참고) 등록 T1 sense=30 이었다면 전-limiter 가시 비율 "
              f"{vis_full/n:.3f} — 본 진단은 무제한이라 해석에 쓰지 않음", flush=True)
        # arm 완료마다 부분 저장 (중단 내성)
        p_out.write_text(json.dumps({"partial": True, "done_arms": list(arms),
                                     "arms": arms}, ensure_ascii=False, indent=1),
                         encoding="utf-8")

    out = {"declared": {"n": a.n, "start_x": a.start_x, "sense_range": SENSE,
                        "route_gain": ROUTE, "limiter_mode": "intercept",
                        "baseline_commit": True,
                        "evidence_grade": "EXPLORATORY / post-result diagnostic — "
                                          "E2-B 를 덮어쓰지 않는다",
                        "confound_handling": "sense 를 무제한으로 고정해 가시성을 "
                                             "교란에서 제거했다. 따라서 공격자는 등록 T1 "
                                             "점이 아니라 'T1-route with unlimited "
                                             "sensing' 진단 변형이며, 등록 T1 수치와 "
                                             "나란히 놓지 않는다. 지평선은 arm 마다 "
                                             "비구속으로 늘렸다"},
           "arms": arms}
    from shepherd.scripts.pivot_manifest import stamp
    out["manifest"] = stamp(artifact="lead_time_diag_EXPLORATORY")
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  -> {p}")


if __name__ == "__main__":
    main()
