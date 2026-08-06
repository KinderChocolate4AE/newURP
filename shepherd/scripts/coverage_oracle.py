"""단계 2 — 동시 coverage 오라클 (docs/52 §8, 외부 리뷰 3 권고).

★ 성공 조건을 먼저 바로잡는다 (2026-08-06 확인)
-----------------------------------------------
"탈출구를 전부 막는다" 는 **성공이 아니다.** `viability._v_shot_with_accels`:

    feasible = limiter 에 막히지 않은 탈출 표본
    caught   = 그 표본의 종점이 finisher 원뿔 안
    n_feasible == 0  ->  boxed_in = True, **clean net-shot 아님** (R4 SPLIT)
    포획         = (not boxed_in) and v_shot_worst >= 1.0
                 = 살아남은 탈출이 **하나 이상** 있고 그것들이 **전부** 원뿔 안

즉 성형의 목표는 봉쇄가 아니라 **압축**이다:

    원뿔 **밖**으로 나가는 탈출(= bad)만 골라 막고,
    원뿔 **안**으로 가는 탈출(= good)은 **적어도 하나 남긴다.**

전부 막으면 `boxed_in` 이 되어 오히려 실패한다. 이 비대칭을 모르고
"uncaught = 0" 을 목적으로 잡으면 오라클이 틀린 문제를 푼다.

이 스크립트가 재는 것 — 필요조건
--------------------------------
각 후보 시각 t 에서

    N_bad(t)          원뿔 밖 탈출 표본 수
    N_bad_unreach(t)  그중 **어떤 limiter 도 도달할 수 없는** 것의 수
    N_good(t)         원뿔 안 탈출 표본 수

`N_bad_unreach > 0` 이면 그 시각에는 **어떤 배치로도** 압축이 불가능하다
(certified). `N_good == 0` 이어도 불가능하다 (남길 것이 없다).

둘 다 통과하는 시각이 있으면 **coverage 후보 시각**이다. 그때 실제로 4 기로
덮을 수 있는지(집합덮개)는 이 문서가 답하지 않는다 -- 그건 단계 2b 다.

도달 판정은 docs/52 와 **같은 낙관적 술어**를 쓴다 (같은 근사, 같은 방향).

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List

import numpy as np

import shepherd.game.viability as V
from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.scripts.contact_reachability import reach_radius
from shepherd.spawn_rand import SpawnSpec

__all__ = ["episode_coverage", "audit"]


def _kw() -> dict:
    return dict(system=SystemSpec(), reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def _paths(x0, v0, accels, tau, n_t=24):
    """탈출 표본 포물선 (n_accel, n_t, 3) -- `_feasible_limiter` 와 같은 이산화."""
    s = np.linspace(0.0, tau, n_t)
    return (np.asarray(x0)[None, None, :]
            + np.asarray(v0)[None, None, :] * s[None, :, None]
            + 0.5 * np.asarray(accels)[:, None, :] * (s ** 2)[None, :, None])


BLOCK_NAMES = {0: "single", 1: "boundary", 2: "dogleg", 3: "turn"}


def episode_coverage_union(seed0: int, ep: int, *, stride: int = 1) -> dict:
    """★ 2a-E, **union 기반** (docs/52 §8.7). 환경과 같은 탈출집합·같은 판정.

    `_union_sets(..., return_paths=True)` 로 env 와 **같은 코드 경로**에서
    표본·경로·caught 를 받는다 (P74~P77 가 동치를 강제).

    술어는 env-faithful 이다 -- limiter 는 발사 시점 **정적** 위치이고
    (docs/52 §5.3), 공격자 escape trajectory 의 **이산 경로점 전체**와 비교한다.
    """
    from shepherd.scripts.mission_rollout import scripted_role_actions

    st = build_m4_env(seed0, ep, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    a_max, v_max = float(scn.limiter.a_max), float(st.threat["v_lim"])
    dt, tau, r_shape = float(env.dt), float(env.tau_deploy), float(env.kill_radius)
    C0 = np.array([env._p(l) for l in env._states()[0]], float)
    V0 = np.array([env._v(l) for l in env._states()[0]], float)

    frames = []
    for _ in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        frames.append((env._p(att).copy(), env._v(att).copy(),
                       np.asarray(fin, float).copy()))
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="clean")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if (term and term.get(fid)) or (trunc and trunc.get(fid)):
            break

    best = None
    for k in range(0, len(frames), stride):
        p_att, v_att, fin9 = frames[k]
        kw = env._vshot_kwargs(p_att, v_att, fin9)
        # limiter 없이 -> 모든 탈출이 feasible. 그중 원뿔 밖이 막아야 할 bad
        _, feas, caught, tr = V._union_sets(
            p_att, v_att, tau=tau, a_att_max=env.a_att_max,
            limiters=None, kill_radius=r_shape,
            attacker_turn_limited=False, omega_att_max=None, e_att=None,
            n=env.n_samples, n_segments=env.n_segments, seed=0,
            net_center=None, net_radius=None, return_paths=True, **{
                kk: vv for kk, vv in kw.items() if kk != "judge"},
            judge=kw["judge"])
        bad = ~caught
        n_good, n_bad = int(caught.sum()), int(bad.sum())
        if n_good == 0 or n_bad == 0:
            continue
        tk = k * dt
        Ck = C0 + V0 * tk
        rk = reach_radius(tk, a_max, v_max)
        # 정적 위치 c_i ∈ ball(Ck[i], rk) 로 닿을 수 있는가
        d = np.linalg.norm(tr.paths[bad][:, :, None, :] - Ck[None, None, :, :],
                           axis=3).min(axis=(1, 2))
        cover = d <= rk + r_shape
        blk = tr.block_id[bad]
        per = {}
        for b in np.unique(tr.block_id):
            m = blk == b
            if not m.any():
                continue
            per[BLOCK_NAMES.get(int(b), str(b))] = {
                "n_bad": int(m.sum()), "coverable": int(cover[m].sum()),
                "unreachable": int((~cover[m]).sum()),
                "worst_slack": float((d[m] - rk - r_shape).max())}
        rec = {"t": k, "n_good": n_good, "n_bad": n_bad,
               "n_bad_unreach": int((~cover).sum()),
               "unreach_block1": int((~cover & (blk == 0)).sum()),
               "by_block": per, "feasible_now": bool((~cover).sum() == 0)}
        if best is None or rec["n_bad_unreach"] < best["n_bad_unreach"]:
            best = rec
    return {"episode": ep, "steps": len(frames),
            "regime": regime_of(st.threat["a_att"], st.threat["tau"],
                                st.threat["net_radius"]),
            "n_segments": int(env.n_segments), "best": best,
            "any_feasible_t": bool(best is not None and best["feasible_now"])}


def episode_coverage(seed0: int, ep: int, *, stride: int = 1) -> dict:
    """~~구 2a~~ INVALIDATED -- Block 1 만 쓴다 (docs/52 §4.2). 비교용으로만 남긴다."""
    from shepherd.scripts.mission_rollout import scripted_role_actions

    st = build_m4_env(seed0, ep, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    a_max, v_max = float(scn.limiter.a_max), float(st.threat["v_lim"])
    dt, tau, r_shape = float(env.dt), float(env.tau_deploy), float(env.kill_radius)

    lims0 = env._states()[0]
    C0 = np.array([env._p(l) for l in lims0], float)
    V0 = np.array([env._v(l) for l in lims0], float)

    # 궤적 기록 (hold -- docs/52 와 같은 낙관성)
    frames = []
    for _ in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        frames.append((env._p(att).copy(), env._v(att).copy(),
                       np.asarray(fin, float).copy()))
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="clean")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if (term and term.get(fid)) or (trunc and trunc.get(fid)):
            break

    accels = V.reachable_accels(env.a_att_max, n=env.n_samples, seed=0)
    best = None
    for k in range(0, len(frames), stride):
        p_att, v_att, fin9 = frames[k]
        # 종점이 원뿔 안인가 (limiter 와 무관)
        endpoints = p_att[None, :] + v_att[None, :] * tau + 0.5 * accels * tau ** 2
        caught = V._caught_se3_cone(endpoints, env._p(fin9), env._e(fin9),
                                    env.cone_half_angle, env.cone_range_min,
                                    env.cone_range_max)
        n_good = int(caught.sum())
        n_bad = int((~caught).sum())
        if n_good == 0:
            continue                       # 남길 것이 없다 -> 이 시각은 불가
        if n_bad == 0:
            rec = {"t": k, "n_good": n_good, "n_bad": 0, "n_bad_unreach": 0,
                   "feasible_now": True, "note": "이미 전부 원뿔 안"}
            best = rec if best is None else best
            continue
        # bad 표본 포물선에 **도달 가능한 limiter 가 있는가** (docs/52 술어)
        P = _paths(p_att, v_att, accels[~caught], tau)          # (n_bad, n_t, 3)
        tk = k * dt
        Ck = C0 + V0 * tk
        rk = reach_radius(tk, a_max, v_max)
        d = np.linalg.norm(P[:, :, None, :] - Ck[None, None, :, :], axis=3)
        reach_ok = (d.min(axis=(1, 2)) <= rk + r_shape)          # (n_bad,)
        n_unreach = int((~reach_ok).sum())
        rec = {"t": k, "n_good": n_good, "n_bad": n_bad,
               "n_bad_unreach": n_unreach, "feasible_now": bool(n_unreach == 0)}
        if best is None or (rec["n_bad_unreach"] < best["n_bad_unreach"]):
            best = rec
    return {"episode": ep, "steps": len(frames),
            "regime": regime_of(st.threat["a_att"], st.threat["tau"],
                                st.threat["net_radius"]),
            "n_samples": int(env.n_samples), "best": best,
            "any_feasible_t": bool(best is not None and best["feasible_now"])}


def audit(n: int = 60, seed0: int = 0, stride: int = 1, union: bool = True) -> dict:
    fn = episode_coverage_union if union else episode_coverage
    recs = [fn(seed0, ep, stride=stride) for ep in range(n)]
    out: Dict[str, dict] = {}
    for name in ("ALL", "SHAPING_NEEDED", "FREE_CAPTURE"):
        sel = [r for r in recs
               if name == "ALL" or r["regime"] == name]
        if not sel:
            continue
        ok = [r for r in sel if r["any_feasible_t"]]
        had_good = [r for r in sel if r["best"] is not None]
        unreach = [r["best"]["n_bad_unreach"] for r in had_good]
        nbad = [r["best"]["n_bad"] for r in had_good]
        out[name] = {
            "n": len(sel),
            "with_good_sample": len(had_good),
            "coverage_possible": len(ok),
            "frac": len(ok) / len(sel),
            "median_bad_unreach": float(np.median(unreach)) if unreach else float("nan"),
            "median_bad": float(np.median(nbad)) if nbad else float("nan"),
        }
    return {"objective": ("성형 = 봉쇄가 아니라 압축. 원뿔 밖 탈출(bad)만 막고 "
                          "원뿔 안 탈출(good)은 하나 이상 남긴다. 전부 막으면 "
                          "boxed_in 이 되어 포획이 아니다 (viability R4 SPLIT)"),
            "necessary_condition": ("N_good >= 1  AND  모든 bad 표본이 "
                                    "어떤 limiter 의 도달가능집합 + kill_radius 안"),
            "not_certified": ("4 기로 실제 덮을 수 있는지(집합덮개) / 시간 일관 궤적 / "
                              "반응형 A2 하 유지 -- 전부 미검증 (단계 2b~4)"),
            "by_regime": out, "records": recs}


def main() -> None:
    ap = argparse.ArgumentParser(description="동시 coverage 오라클 필요조건 (docs/52 §8)")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--block1", action="store_true",
                    help="구 Block1-only 경로 (INVALIDATED. 비교용)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    r = audit(args.n, args.seed0, args.stride, union=not args.block1)
    print("목표:", r["objective"])
    print("필요조건:", r["necessary_condition"], "\n")
    for k, v in r["by_regime"].items():
        print(f"  {k:15s} 2a 통과 {v['coverage_possible']:3d}/{v['n']:3d} = "
              f"{v['frac']:.3f}   (good 있는 판 {v['with_good_sample']})")
        print(f"  {'':15s} 최선 시각 bad 중앙 {v['median_bad']:.0f}, "
              f"도달불가 중앙 {v['median_bad_unreach']:.0f}")
    agg = {}
    for rec in r["records"]:
        b = rec.get("best") or {}
        for name, d in (b.get("by_block") or {}).items():
            a = agg.setdefault(name, [0, 0])
            a[0] += d["n_bad"]; a[1] += d["unreachable"]
    if agg:
        print("\n  블록별 (최선 시각 합산):")
        for name, (nb, un) in agg.items():
            print(f"    {name:10s} bad {nb:7d}  도달불가 {un:7d} "
                  f"({un / max(nb, 1):.3f})")
    print("\n★ 인증 안 된 것:", r["not_certified"])
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
