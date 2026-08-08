"""SHAPING 결정적 대역 진단 — 발사게이트를 열려면 limiter 가 몇 기 필요한가.

**진단 전용. 학습·판정·사전등록과 무관하고 어떤 동결값도 바꾸지 않는다.**
docs/71 블록의 결과를 보기 전에 돌려도 안전하다 (IID 대역 접근 0, 학습 0).

묻는 것
-------
SHAPING_NEEDED (0.5·a_att·tau^2 > net_radius) 에서 hold·arc·LS·LL 전부
p_net = 0 이었다. 그것이 (i) 학습 실패인가 (ii) 현재 파라미터에서 애초에
발사게이트가 열리지 않는가?

`clean fire` 는 `v_shot_soft >= theta_fire(0.9)` 이고, `v_shot_soft` 는
공격자의 tau-reachable 위트니스 중 **feasible** 한 것들에서 포획되는 비율이다
(limiter 의 kill_radius 구가 escape 를 infeasible 로 만든다 = shaping 채널).
그래서 a_att 를 축으로:

    v_hold        limiter 를 standby 링에 둔 채 (무개입)
    v_greedy(k)   limiter k 기를 **최적 배치**했을 때 (그리디 = 달성가능 하한)
    N_req         v_greedy(k) >= 0.9 가 되는 최소 k  (선언값은 4 기)

를 잰다. `N_req(a_att) > 4` 인 구간 = **현재 구조에서 어떤 컨트롤러도 발사할
수 없는 영역** (그리디는 최적의 하한이므로 N_req 는 상한 추정 -- 정직한 방향:
"4 기로 된다"는 증명은 되고 "4 기로 안 된다"의 증명은 아니다).

기하는 실제 env 의 hold 롤아웃에서 **방어자에게 가장 유리한 순간**(v_hold 최대
스텝) 을 뽑아 쓴다 -- 즉 이 곡선은 낙관 쪽으로 기울어 있다. 배치에 물리적
도달가능성(a_lim = 0.35·a_att)은 **요구하지 않는다**: 순수 기하 천장이다.

    python -m shepherd.scripts.shaping_ceiling --out results/shaping_ceiling.json
    python -m shepherd.scripts.shaping_ceiling --plot results/shaping_ceiling.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.game import viability as V
from shepherd.m4_config import THREAT_BRACKET
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.scripts.mission_rollout import ROLES
from shepherd.spawn_rand import SpawnSpec
from shepherd.scripts.threat_v3_gates import _base_env

__all__ = ["A_ATT_GRID", "K_MAX", "candidates", "ceiling_at", "sweep"]

# a* = 2·rho/tau^2 = 39.3 을 가로지르도록 (브래킷 [11, 78] 안)
A_ATT_GRID = (30.0, 36.0, 39.0, 42.0, 45.0, 50.0, 55.0, 60.0, 70.0, 78.0)
K_MAX = 12                       # 선언값은 4 기 -- 12 까지 재서 필요량을 본다
N_CAND_DIRS = 32                 # 후보 방향 (Fibonacci 구면)
CAND_RADII = (1.0, 1.5, 2.2, 3.0, 4.0)      # 공격자 현재 위치로부터의 거리 [m]
TOP_K_STEPS = 3                  # 롤아웃에서 방어자에게 가장 유리한 스텝 수


def _fib_dirs(n: int) -> np.ndarray:
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    theta = np.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.sin(phi) * np.cos(theta),
                     np.sin(phi) * np.sin(theta), np.cos(phi)], axis=1)


def candidates(p_att: np.ndarray, kill_radius: float) -> np.ndarray:
    """공격자 주변 껍질들 위의 후보 배치점. kill 구가 t=0 을 덮으면 boxed_in
    (= clean fire 아님) 이 되므로 kill_radius 보다 먼 껍질만 쓴다."""
    dirs = _fib_dirs(N_CAND_DIRS)
    out = [p_att[None, :] + r * dirs for r in CAND_RADII if r > kill_radius + 0.1]
    return np.concatenate(out, axis=0)


def _score(res) -> float:
    """clean fire 관점의 점수. boxed_in 은 v_shot 1.0 이 되지만 clean 이 아니다
    (env.py:292) -- 천장을 부풀리지 않게 탈락시킨다."""
    if res.n_feasible == 0 or getattr(res, "boxed_in", False):
        return -1.0
    return float(res.v_shot_soft)


def _greedy(union, kill_radius: float, cands: np.ndarray, k_max: int):
    """k = 1..k_max 최적(그리디) 배치의 v_shot 궤적 + 선택 위치."""
    chosen: list = []
    traj = []
    for _ in range(k_max):
        sets = [chosen + [c] for c in cands]
        res = V.eval_union_with_limiter_sets(union, sets, kill_radius)
        scores = np.array([_score(r) for r in res])
        j = int(np.argmax(scores))
        if scores[j] <= 0.0:                  # 더 넣으면 전부 boxed_in -> 중단
            break
        chosen.append(cands[j])
        traj.append(float(scores[j]))
    return traj, np.asarray(chosen)


def _hold_snapshots(a_att: float, seed: int, episode: int, max_steps: int):
    """고정 a_att 에서 hold 롤아웃 (전 역할 스크립트, **미발사**).

    finisher 는 스크립트로 **조준한다** -- cone judge 는 finisher 자세에 의존하므로
    제로 액션(무조준)으로 굴리면 기하가 무의미해진다. `fire_mode="never"` 로 두어
    접근 전 구간의 기하를 다 본다.
    """
    from shepherd.scripts.mission_rollout import scripted_role_actions

    st = build_m4_env(
        seed, episode, system=ratified_system(),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=seed),
        spawn=SpawnSpec(), randomize_threat=False,
        extra_cfg={"physics.a_att_max": float(a_att)})
    env, base = st.env, _base_env(st.env)
    env.reset(seed=seed)
    snaps = []
    for _ in range(max_steps):
        lims, fin, att = base._states()
        snaps.append(dict(p_att=base._p(att).copy(), v_att=base._v(att).copy(),
                          fin=np.asarray(fin, float).copy(),
                          lim=[base._p(s).copy() for s in lims]))
        acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                     limiter_mode="hold", fire_mode="never",
                                     prev_clean=False, states=(lims, fin, att))
        _, _, te, tr, _ = env.step(acts)
        if any(te.values()) or any(tr.values()):
            break
    return base, st, snaps


def _union_at(base, s):
    kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
    return V.build_reachable_union(
        s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
        n=base.n_samples, n_segments=base.n_segments, seed=0, **kw)


def ceiling_at(a_att: float, *, seed: int = 0, episode: int = 0,
               max_steps: int = 400, k_max: int = K_MAX, stride: int = 2,
               log=print) -> dict:
    """한 a_att 의 기하 천장. 방어자에게 가장 유리한 상위 스텝들에서 최대.

    v_hold 는 greedy 와 **같은 union·같은 위트니스**에서 계산한다 (관측 벡터를
    읽지 않는다 -- threat_obs 가 꼬리에 2차원을 붙여 인덱스가 밀린다).
    """
    base, st, snaps = _hold_snapshots(a_att, seed, episode, max_steps)
    idx = list(range(0, len(snaps), max(1, stride)))
    scored = []
    for i in idx:
        u = _union_at(base, snaps[i])
        scored.append((_score(V.eval_union_with_limiters(
            u, snaps[i]["lim"], base.kill_radius)), i))
    scored.sort(reverse=True)
    best = None
    for v_hold, i in scored[:TOP_K_STEPS]:
        s = snaps[i]
        union = _union_at(base, s)
        traj, chosen = _greedy(union, base.kill_radius,
                              candidates(s["p_att"], base.kill_radius), k_max)
        n_req = next((j + 1 for j, v in enumerate(traj) if v >= base.theta_fire), None)
        cand = dict(
            step=i, v_hold=v_hold, v_greedy=traj,
            v_greedy_k4=(traj[3] if len(traj) >= 4 else (traj[-1] if traj else None)),
            v_greedy_max=(max(traj) if traj else None),
            n_req=n_req,
            chosen_r_from_att=[round(float(np.linalg.norm(c - s["p_att"])), 2)
                               for c in chosen],
            chosen_d_from_asset=[round(float(np.linalg.norm(
                c - np.asarray(base.layout.target, float))), 2) for c in chosen],
            d_att_asset=round(float(np.linalg.norm(
                s["p_att"] - np.asarray(base.layout.target, float))), 2))
        if best is None or (cand["v_greedy_max"] or -1) > (best["v_greedy_max"] or -1):
            best = cand
        if log:
            log(f"  a_att={a_att:>5.1f} step{i:>4} v_hold={v_hold:.3f} "
                f"-> k4 {cand['v_greedy_k4']} max {cand['v_greedy_max']} "
                f"N_req={n_req}", flush=True)
    rho, tau = base.net_radius, base.tau_deploy
    return dict(a_att=a_att, regime=regime_of(a_att, tau, rho),
                r_escape=round(0.5 * a_att * tau ** 2, 3),
                theta_fire=base.theta_fire, kill_radius=base.kill_radius,
                net_radius=rho, tau=tau, judge=base.judge,
                n_segments=base.n_segments, **best)


def sweep(grid=A_ATT_GRID, **kw) -> dict:
    rows = [ceiling_at(a, **kw) for a in grid]
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    decisive = [r["a_att"] for r in rows
                if r["v_hold"] < r["theta_fire"]
                and (r["v_greedy_k4"] or 0) >= r["theta_fire"]]
    return dict(
        contract_doc="진단 전용 (판정·사전등록 무관). SHAPING 결정적 대역 존재 여부",
        note=("v_greedy 는 그리디 최적배치 = 달성가능 하한. 배치 도달가능성"
              "(a_lim=0.35·a_att)·NK 존 제약을 걸지 않은 낙관 천장이다. "
              "따라서 'N_req<=4 면 기하적으로 가능' 은 성립하고 "
              "'N_req>4 면 불가능' 은 강한 시사이지 증명이 아니다."),
        bracket=[lo, hi], a_star=round(2 * rows[0]["net_radius"]
                                       / rows[0]["tau"] ** 2, 2),
        declared_n_limiters=4,
        decisive_band_a_att=decisive, rows=rows)


def _plot(path: str, out_png: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    rows = d["rows"]
    a = [r["a_att"] for r in rows]
    th = rows[0]["theta_fire"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))

    ax[0].axhline(th, color="k", ls="--", lw=1, label=f"fire gate $\theta$={th}")
    ax[0].plot(a, [r["v_hold"] for r in rows], "o-", label="hold (no shaping)")
    ax[0].plot(a, [r["v_greedy_k4"] for r in rows], "s-",
               label="optimal 4 limiters (declared N)")
    ax[0].plot(a, [r["v_greedy_max"] for r in rows], "^-",
               label=f"optimal up to {K_MAX} limiters")
    ax[0].axvline(d["a_star"], color="r", ls=":", lw=1,
                  label=f"a* = {d['a_star']} (SHAPING boundary)")
    ax[0].set_xlabel("a_att [m/s^2]"); ax[0].set_ylabel("v_shot_soft")
    ax[0].set_ylim(0, 1.02); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)

    nreq = [(r["n_req"] if r["n_req"] else np.nan) for r in rows]
    ax[1].plot(a, nreq, "o-", color="C3")
    ax[1].axhline(4, color="k", ls="--", lw=1, label="declared N = 4")
    ax[1].axvline(d["a_star"], color="r", ls=":", lw=1)
    ax[1].set_xlabel("a_att [m/s^2]")
    ax[1].set_ylabel(f"N_req to open the gate (>{K_MAX} = nan)")
    ax[1].legend(fontsize=7); ax[1].grid(alpha=.3)
    fig.suptitle("Shaping-decisive band: geometric ceiling (optimistic)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    print(f"-> {out_png}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="SHAPING 기하 천장 진단")
    ap.add_argument("--out", default="results/shaping_ceiling.json")
    ap.add_argument("--plot", default=None, help="JSON 을 읽어 그림만 그린다")
    ap.add_argument("--out-png", default="results/shaping_ceiling.png")
    ap.add_argument("--a-att", type=float, nargs="*", default=None)
    ap.add_argument("--k-max", type=int, default=K_MAX)
    # 후보 집합은 천장 값에 실제로 영향을 준다 (조밀하게 하면 올라간다) --
    # 그래서 인자로 받고 산출물에 기록한다. 값 하나만 보고 "구조적" 이라고
    # 말하지 않기 위한 최소 장치.
    ap.add_argument("--cand-dirs", type=int, default=None)
    ap.add_argument("--cand-radii", type=float, nargs="*", default=None)
    ap.add_argument("--top-k-steps", type=int, default=None)
    a = ap.parse_args(argv)

    if a.plot:
        _plot(a.plot, a.out_png)
        return
    global N_CAND_DIRS, CAND_RADII, TOP_K_STEPS
    if a.cand_dirs is not None:
        N_CAND_DIRS = int(a.cand_dirs)
    if a.cand_radii:
        CAND_RADII = tuple(a.cand_radii)
    if a.top_k_steps is not None:
        TOP_K_STEPS = int(a.top_k_steps)
    out = sweep(tuple(a.a_att) if a.a_att else A_ATT_GRID, k_max=a.k_max)
    out["probe_cfg"] = dict(cand_dirs=N_CAND_DIRS, cand_radii=list(CAND_RADII),
                            n_candidates=len(CAND_RADII) * N_CAND_DIRS,
                            top_k_steps=TOP_K_STEPS, k_max=int(a.k_max))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float),
                 encoding="utf-8")
    print(f"\na* = {out['a_star']}  결정적 대역(4기로 게이트 개방) = "
          f"{out['decisive_band_a_att'] or '없음'}")
    for r in out["rows"]:
        print(f"  a_att={r['a_att']:>5.1f} {r['regime']:>14} r_esc={r['r_escape']:.2f} "
              f"v_hold={r['v_hold']:.3f} k4={r['v_greedy_k4']} "
              f"max={r['v_greedy_max']} N_req={r['n_req']}")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
