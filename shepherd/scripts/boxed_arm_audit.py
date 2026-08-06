"""boxed_in 3-arm 감사 (docs/53 §4.5). 판정표는 **실행 전에** 고정돼 있다.

A / B  현행 코드 무수정 -- 구현 감사
C1/C2  격리된 counterfactual -- **본선 환경 변경이 아니다**

    A   발사 안 함, 커밋 안 함, 현행대로
    B   즉시 발사, 현행대로            -> SPENT_FAIL 즉시 종료 예상
    C1  발사하되 **종료만 억제**       -> 즉시 종료가 주 비정합인가
    C2  C1 + 접촉 resolver (인라인 프로토타입: endpoint·즉시 무력화)
    C2R C1 + **실 R1 resolver** (env_sys, swept + NK veto + Pk) -- V2 검증
        (docs/54 §3 V2. 수락대역·차이 축은 결과 전 docs/54 §1 에 고정)
    F   **실 계약 그대로** (contact_resolver=True ∧ miss_terminates=False,
        스크립트 종료억제·spec 스왑 없음) -- V3 검증 (docs/54 §1 R2 세부)

C1 과 C2 를 섞지 않는다 -- 섞으면 handoff 효과와 resolver 효과가 안 갈린다.
torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
from typing import Dict, List
import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import ModeSystemEnv, RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.spawn_rand import SpawnSpec

__all__ = ["arm_audit"]

ARMS = ("A", "B", "C1", "C2", "C2R", "F")


def _sysenv(env) -> ModeSystemEnv:
    """래퍼 사슬(ThreatObsEnv 등)에서 ModeSystemEnv 를 찾는다."""
    e = env
    while not isinstance(e, ModeSystemEnv):
        e = e.inner
    return e


def _kw(system: SystemSpec | None = None):
    return dict(system=system or SystemSpec(enabled=True),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def _run(ep: int, arm: str, seed0: int = 0, limiter_mode: str = "intercept",
         system: SystemSpec | None = None) -> dict:
    """boxed_in 첫 발생 시점에서 분기. 그 전까지는 모든 arm 이 동일하다."""
    from shepherd.scripts.mission_rollout import scripted_role_actions

    if system is None:
        system = (SystemSpec(enabled=True, contact_resolver=True,
                             miss_terminates=False) if arm == "F" else None)
    st = build_m4_env(seed0, ep, **_kw(system))
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    kr = float(env.kill_radius)
    branched = False
    out = {"episode": ep, "arm": arm, "boxed_step": None, "contact": False,
           "contact_step": None, "min_dist_after": np.inf, "fired": False,
           "penetrated": False, "terminated_step": None, "boxed_steps": 0,
           "neutralized_by": None, "steps": 0}

    for t in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        p_att = env._p(att)
        vf = env._vshot(p_att, env._v(att), [env._p(l) for l in lims], fin, seed=0)
        if vf.boxed_in:
            out["boxed_steps"] += 1
            if out["boxed_step"] is None:
                out["boxed_step"] = t
                branched = True
                if arm == "C2R":
                    # ★ 분기 시점부터 실 R1 resolver 활성 (프로토타입과 동일 시점).
                    #   격리 counterfactual -- 본선은 기본 off 그대로다.
                    se = _sysenv(env)
                    se.spec = SystemSpec(enabled=True, contact_resolver=True)
        acts = scripted_role_actions(env, scn, lay, limiter_mode=limiter_mode,
                                     fire_mode="never")
        # 분기: 발사 비트만 조작. limiter 제어는 전 arm 동일
        if branched and arm in ("B", "C1", "C2", "C2R", "F") and not out["fired"]:
            a = np.asarray(acts[fid], np.float32).copy()
            if len(a) >= 5:
                a[4] = 1.0
                acts[fid] = a
                out["fired"] = True
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        out["steps"] = t + 1

        if branched:
            l2, _, a2 = env._states()
            d = min(float(np.linalg.norm(env._p(a2) - env._p(l))) for l in l2)
            out["min_dist_after"] = min(out["min_dist_after"], d)
            if d <= kr and not out["contact"]:
                out["contact"] = True
                out["contact_step"] = t
                if arm == "C2":          # ★ 접촉 resolver prototype
                    out["neutralized_by"] = "contact_resolver"
                    break
            if arm == "C2R" and getattr(env, "hard_kill", False):
                # ★ 실 resolver 가 KILL -- 프로토타입의 break 와 동일 지점
                out["neutralized_by"] = "env_contact_resolver"
                out["terminated_step"] = t
                break

        done = bool((term and term.get(fid)) or (trunc and trunc.get(fid)))
        if done:
            out["terminated_step"] = t
            if arm in ("C1", "C2", "C2R"):
                # ★ 종료 억제 (격리 counterfactual). 계속 굴린다
                if env.fsm.state.name == "SPENT":
                    continue
            break
    l2, _, a2 = env._states()
    out["penetrated"] = bool(np.linalg.norm(env._p(a2) - np.asarray(lay.target, float))
                             <= lay.target_radius)
    out["min_dist_after"] = (None if not np.isfinite(out["min_dist_after"])
                             else round(float(out["min_dist_after"]), 3))
    out["hard_kill"] = bool(getattr(env, "hard_kill", False))
    if arm in ("C2R", "F"):               # 수락대역 이탈 시 분해용 (docs/54 §1)
        se = _sysenv(env)
        s = se.summary()
        out["veto_events"] = int(se.veto_events)
        out["contact_events"] = int(s["contact_events"])
        out["pk_fail"] = int(s["PK_FAIL"])
        out["kills"] = int(s["KILL"])
    if arm == "F":                        # V3: 실 계약의 handoff provenance
        se = _sysenv(env)
        out["net_spent"] = bool(se.net_spent)
        out["handoff_step"] = se.net_spent_step
        if out["hard_kill"]:
            out["neutralized_by"] = "env_contact_resolver"
    return out


def arm_audit(n: int = 60, seed0: int = 0) -> dict:
    recs: List[dict] = []
    for ep in range(n):
        a = _run(ep, "A", seed0)
        if a["boxed_step"] is None:
            continue
        recs.append(a)
        for arm in ("B", "C1", "C2", "C2R", "F"):
            recs.append(_run(ep, arm, seed0))
        if sum(1 for r in recs if r["arm"] == "A") >= 20:
            break
    by = {}
    for arm in ARMS:
        g = [r for r in recs if r["arm"] == arm]
        if not g:
            continue
        by[arm] = {
            "n": len(g),
            "contact_frac": round(float(np.mean([r["contact"] for r in g])), 3),
            "penetrated_frac": round(float(np.mean([r["penetrated"] for r in g])), 3),
            "hard_kill_frac": round(float(np.mean([r["hard_kill"] for r in g])), 3),
            "neutralized_frac": round(float(np.mean(
                [r["neutralized_by"] is not None for r in g])), 3),
            "median_min_dist": float(np.median(
                [r["min_dist_after"] for r in g if r["min_dist_after"] is not None])),
            "median_term_step": (float(np.median([r["terminated_step"] for r in g
                                                  if r["terminated_step"] is not None]))
                                 if any(r["terminated_step"] is not None for r in g)
                                 else None),
        }
        if arm == "F":                       # V3 판정용 (docs/54 §1 R2 세부)
            by[arm]["net_spent_frac"] = round(float(np.mean(
                [bool(r.get("net_spent")) for r in g])), 3)
            by[arm]["spent_then_neutralized_frac"] = round(float(np.mean(
                [bool(r.get("net_spent")) and r.get("neutralized_by") is not None
                 for r in g])), 3)
    return {"contract": "A/B 현행 무수정 · C1/C2 격리 counterfactual (docs/53 §4.5)",
            "by_arm": by, "records": recs}


def main() -> None:
    ap = argparse.ArgumentParser(description="boxed_in 3-arm 감사 (docs/53 §4.5)")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = arm_audit(a.n)
    print(r["contract"], "\n")
    print(f"  {'arm':4s} {'n':>3s} {'접촉':>6s} {'침투':>6s} {'하드킬':>7s} "
          f"{'무력화':>7s} {'최소거리':>8s} {'종료스텝':>8s}")
    for arm, v in r["by_arm"].items():
        ts = "-" if v["median_term_step"] is None else f"{v['median_term_step']:.0f}"
        print(f"  {arm:4s} {v['n']:3d} {v['contact_frac']:6.3f} {v['penetrated_frac']:6.3f} "
              f"{v['hard_kill_frac']:7.3f} {v['neutralized_frac']:7.3f} "
              f"{v['median_min_dist']:8.3f} {ts:>8s}")
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
