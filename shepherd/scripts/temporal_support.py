"""시각별 재최적화 support — clean corridor 가 **이동하는가** (docs/52 §8.1e).

왜 필요한가
----------
§8.1c 의 "고정 배치 기준 1 tick" 은 다음 둘을 **구분하지 못한다**:

    (1) clean snapshot 자체가 실제로 50 ms 만 존재한다
    (2) clean snapshot 은 여러 tick 존재하지만 **최적 배치가 이동한다**

(2) 라면 단계 3 의 문제는 *"한 순간을 정확히 맞히기"* 가 아니라
**움직이는 수 cm 폭 corridor 를 추종하기** 가 된다. 해석이 크게 달라진다.

두 종류를 분리해서 푼다
----------------------
    A. 독립 재최적화     각 tick 을 서로 독립적으로 -> "각 tick 에 존재하는가"
    B. continuation      t* 에서 출발해 warm start + trust region 으로 바깥으로
                         -> "해들이 하나의 가지로 이어지는가"

    A 는 여러 tick 성공인데 B 가 끊기면 -> snapshot 은 존재하나 서로 다른
    basin 이거나 급격히 이동한다.

★ trust region 은 **동역학 증명이 아니다** -- 움직이는 배치 가지를 추적하기
위한 수치 장치일 뿐이다. snapshot 에는 limiter 속도 상태가 없으므로 인접
두 위치가 각각 도달 가능해도 **서로 연결 가능하다는 보장은 없다.**

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List, Optional

import numpy as np

import shepherd.game.viability as V
from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.scripts.contact_reachability import reach_radius
from shepherd.scripts.selective_snapshot_oracle import (N_BEAM, N_CAND,
                                                        N_GOOD_TRY, SEARCH_BAD,
                                                        SEARCH_STEP,
                                                        _beam_cover,
                                                        _candidates, _min_dist)
from shepherd.spawn_rand import SpawnSpec

__all__ = ["temporal_support"]

ROBUST_LEVELS = (0.0, 0.01, 0.02)


def _kw() -> dict:
    return dict(system=SystemSpec(), reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def _solve_tick(env, p_att, v_att, fin9, Ck, rk, r_kill, rng,
                warm: Optional[np.ndarray] = None,
                trust: float = 0.6) -> dict:
    """한 tick 의 snapshot 최적화. `warm` 이 있으면 그 주변으로 후보를 제한."""
    kw = env._vshot_kwargs(p_att, v_att, fin9)
    _, _, caught, tr = V._union_sets(
        p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
        limiters=None, kill_radius=r_kill, attacker_turn_limited=False,
        omega_att_max=None, e_att=None, n=env.n_samples,
        n_segments=env.n_segments, seed=0, net_center=None, net_radius=None,
        return_paths=True, **kw)
    bad, good = ~caught, caught
    if not bad.any() or not good.any():
        return {"status": "no_split", "n_bad": int(bad.sum()),
                "n_good": int(good.sum())}
    n_lim = len(Ck)
    Pb_all, Pg_all = tr.paths[bad], tr.paths[good]
    bi = rng.choice(len(Pb_all), size=min(SEARCH_BAD, len(Pb_all)), replace=False)
    gi = rng.choice(len(Pg_all), size=min(SEARCH_BAD // 2, len(Pg_all)), replace=False)
    Pb, Pg = Pb_all[bi][:, ::SEARCH_STEP], Pg_all[gi][:, ::SEARCH_STEP]

    cand = []
    for i in range(n_lim):
        c = _candidates(Ck[i], rk, Pb, None, rng, n=N_CAND)
        if warm is not None:                    # continuation: trust region
            c = np.concatenate([c, warm[i][None, :]], axis=0)
            c = c[np.linalg.norm(c - warm[i], axis=1) <= trust]
            if len(c) == 0:
                c = warm[i][None, :]
        cand.append(c)
    covb = [_min_dist(Pb, None, cand[i]) <= r_kill for i in range(n_lim)]
    killg = [_min_dist(Pg, None, cand[i]) <= r_kill for i in range(n_lim)]
    clear = np.min([killg[i].mean(axis=0) for i in range(n_lim)], axis=0)

    best = {"status": "no_witness", "n_bad": int(bad.sum()),
            "n_good": int(good.sum()), "uncovered": None}
    for g in np.argsort(clear)[:N_GOOD_TRY]:
        keep = [~killg[i][:, g] for i in range(n_lim)]
        if any(k.sum() == 0 for k in keep):
            continue
        pick, cov = _beam_cover([covb[i][keep[i]] for i in range(n_lim)],
                                len(Pb), width=N_BEAM)
        unc = int((~cov).sum())
        L = np.array([cand[i][np.nonzero(keep[i])[0][pick[i]]]
                      if pick[i] is not None else Ck[i] for i in range(n_lim)])
        if best["uncovered"] is None or unc < best["uncovered"]:
            best["uncovered"] = unc
        if unc:
            continue
        vf = env._vshot(p_att, v_att, L, fin9, seed=0)
        if vf.boxed_in or vf.v_shot_worst < 1.0 or vf.v_shot_soft < env.theta_fire:
            best["status"] = "boxed" if vf.boxed_in else "uncovered_exact"
            continue
        d = np.linalg.norm(tr.paths[:, :, None, :] - L[None, None, :, :],
                           axis=3).min(axis=1)
        sg = good & ~(d <= r_kill).any(axis=1)
        mb = float(np.min(np.max(r_kill - d[bad], axis=1)))
        mg = float(np.max(np.min(d[sg] - r_kill, axis=1))) if sg.any() else -np.inf
        return {"status": "clean", "n_bad": int(bad.sum()), "n_good": int(good.sum()),
                "uncovered": 0, "m_bad": mb, "m_good": mg,
                "m_sel": float(min(mb, mg)), "n_feasible": int(vf.n_feasible),
                "limiters": L.tolist(),
                "reach_slack": [float(x) for x in rk - np.linalg.norm(L - Ck, axis=1)]}
    return best


def temporal_support(seed0: int, ep: int, t_star: int, *, half: int = 6,
                     seed: int = 0) -> dict:
    from shepherd.scripts.mission_rollout import scripted_role_actions

    st = build_m4_env(seed0, ep, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    a_max, v_max = float(scn.limiter.a_max), float(st.threat["v_lim"])
    dt, r_kill = float(env.dt), float(env.kill_radius)
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

    ts = [t for t in range(t_star - half, t_star + half + 1) if 0 <= t < len(frames)]

    def _ck(t):
        return C0 + V0 * (t * dt), reach_radius(t * dt, a_max, v_max)

    # ── A. 독립 재최적화 ────────────────────────────────────────────────────
    indep = {}
    for t in ts:
        Ck, rk = _ck(t)
        indep[t] = _solve_tick(env, *frames[t], Ck, rk, r_kill,
                               np.random.default_rng(seed + t))

    # ── B. continuation (t* 에서 양방향 warm start) ─────────────────────────
    cont = {}
    # ★ t* 가 아니라 **가장 강건한 clean tick** 에서 출발한다. t* 고정이면
    #   그 tick 이 (시드 차이로) 실패했을 때 continuation 이 통째로 안 돈다
    #   -- 2026-08-06 실제로 밟음.
    cl = [(t, r) for t, r in indep.items() if r.get("status") == "clean"]
    if cl:
        t_seed, base = max(cl, key=lambda z: z[1].get("m_sel", -1e9))
        t_star = t_seed
        cont[t_star] = {**base, "warm_start": "independent(best m_sel)"}
        for direction in (+1, -1):
            warm = np.array(base["limiters"])
            t = t_star + direction
            while t in ts:
                Ck, rk = _ck(t)
                r = _solve_tick(env, *frames[t], Ck, rk, r_kill,
                                np.random.default_rng(seed + 1000 + t), warm=warm)
                cont[t] = {**r, "warm_start": f"cont{direction:+d}"}
                if r.get("status") != "clean":
                    break
                warm = np.array(r["limiters"])
                t += direction

    clean_t = sorted(t for t, r in indep.items() if r.get("status") == "clean")
    runs, cur = [], []
    for t in clean_t:
        if cur and t == cur[-1] + 1:
            cur.append(t)
        else:
            runs.append(cur); cur = [t]
    runs.append(cur)
    longest = max((len(r) for r in runs if r), default=0)

    robust = {f"m_sel>={lv}": sorted(t for t in clean_t
                                     if indep[t].get("m_sel", -1) >= lv)
              for lv in ROBUST_LEVELS}
    drift = {}
    for t in clean_t:
        if t + 1 in clean_t:
            a = np.array(indep[t]["limiters"]); b = np.array(indep[t + 1]["limiters"])
            drift[f"{t}->{t+1}"] = [round(float(x), 3)
                                    for x in np.linalg.norm(b - a, axis=1)]
    return {"episode": ep, "t_star": t_star, "ticks": ts,
            "independent": {str(k): v for k, v in indep.items()},
            "continuation": {str(k): v for k, v in cont.items()},
            "exact_support": clean_t,
            "contiguous_support_ticks": longest,
            "contiguous_support_s": round(longest * dt, 3),
            "robust_support": robust,
            "adjacent_drift_m": drift,
            "note": ("trust region 은 동역학 증명이 아니라 가지 추적용 수치 장치. "
                     "인접 두 위치가 각각 도달 가능해도 연결 가능 보장 없음")}


def main() -> None:
    ap = argparse.ArgumentParser(description="시각별 재최적화 support (docs/52 §8.1e)")
    ap.add_argument("--episode", type=int, required=True)
    ap.add_argument("--t-star", type=int, required=True)
    ap.add_argument("--half", type=int, default=6)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    r = temporal_support(0, args.episode, args.t_star, half=args.half)
    print(f"ep{r['episode']}  t*={r['t_star']}  창 {r['ticks'][0]}..{r['ticks'][-1]}")
    print(f"\n  {'t':>3} {'A(독립)':>16} {'m_sel':>8} {'n_feas':>7} | {'B(continuation)':>16}")
    for t in r["ticks"]:
        a = r["independent"][str(t)]
        b = r["continuation"].get(str(t), {})
        ms = a.get("m_sel")
        print(f"  {t:3d} {a['status']:>16} "
              f"{(f'{ms:+.4f}' if ms is not None else '-'):>8} "
              f"{a.get('n_feasible','-'):>7} | {b.get('status','-'):>16}")
    print(f"\n  exact support: {r['exact_support']}")
    print(f"  최장 연속: {r['contiguous_support_ticks']} tick = {r['contiguous_support_s']} s")
    for k, v in r["robust_support"].items():
        print(f"  robust {k:14s} {len(v)} tick  {v}")
    if r["adjacent_drift_m"]:
        print("  인접 tick 배치 이동량 [m]:")
        for k, v in r["adjacent_drift_m"].items():
            print(f"    {k}: {v}")
    print("  ★", r["note"])
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
