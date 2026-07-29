"""비손실 포획 도달가능성 상한 — tau 축 위의 oracle (docs/30 §1).

질문 (docs/30)
-------------
**비손실 포획이 무엇에 의해서든 도달 가능한가?** 학습으로 답하면 서버 시간 + 수 주가
들지만, 포획이 **발사 시점에 동결**되므로(S5 robust judge) 오프라인으로 답할 수 있다:

    한 번의 롤아웃에서 매 스텝의 (v_shot_worst, boxed_in, p_feasible, 접촉) 을 기록하면
    **발사 타이밍 전 범위를 사후 평가**할 수 있다. 발사는 그 스텝 이전의 동역학을
    바꾸지 않으므로(공격자는 `committed` 비트에만 반응) 이 평가는 근사가 아니라 정확하다.

따라서 (tau x r_ring) 당 롤아웃 **하나**면 발사 타이밍 축이 공짜로 딸려온다.

종점 두 개 (docs/30 §1.2, 결과 보기 전 선언)
------------------------------------------
    frozen    (not boxed_in) and worst >= 1        <- env.py L319 규칙 그대로
    relaxed   worst >= 1 and contact == 0          <- 지금 선언한 이차 종점

`boxed_in` 제외는 M2 의 판단이었다(위협/접촉 구분자가 없던 시절). M4 는 접촉을 직접
관측하므로 둘 다 보고하고, **불일치 자체를 발견으로 기록**한다.

명제 N(b) 링 반경
----------------
docs/10 (b): 마스크를 `rho + (w - rho)/2` 에 두어 escape lobe 를 덮되 core 를 남긴다.
3D 로 올리면 core 는 반경 `delta = rho - max(0, r_kill - (w-rho)/2)` 의 **공**이고,
그 부피 분율은 `(delta/w)^3` 로 **세제곱으로 붕괴**한다 -- 1D 에서 1/12 이던 것이
3D 에서는 1e-4 규모가 된다. 따라서 `boxed_in`(= 샘플러의 n_feasible==0)이
**기하적 사실이 아니라 샘플링 분해능의 산물**일 수 있다. 이 스크립트가 그것도 검사한다.

라벨: SEARCH_CANDIDATE / FIXED_CONDITION / DISCOVERY·NON-EVIDENTIAL.
torch-free.
"""
from __future__ import annotations

import argparse
import math
from typing import Dict, List, Optional

import numpy as np

from shepherd.agents.baselines import scripted_finisher, scripted_shaping_limiter
from shepherd.params import as_config
from shepherd.train.make_env import make_train_env

__all__ = ["nb_ring_radius", "nb_core", "trace_episode", "oracle_scan"]


# ------------------------------------------------------------- 명제 N(b) ---
def nb_ring_radius(a_att, tau, rho):
    """docs/10 (b) 마스크 중심 반경 = rho + (w - rho)/2. w <= rho 면 shaping 불필요."""
    w = 0.5 * a_att * tau ** 2
    return (rho + (w - rho) / 2.0) if w > rho else rho


def nb_core(a_att, tau, rho, r_kill):
    """N(b) 가 남기는 core 반경 delta 와 3D 부피 분율 (delta/w)^3."""
    w = 0.5 * a_att * tau ** 2
    if w <= rho:
        return dict(w=w, delta=rho, frac=1.0, shaping_needed=False)
    delta = rho - max(0.0, r_kill - (w - rho) / 2.0)
    frac = (max(delta, 0.0) / w) ** 3 if w > 0 else 0.0
    return dict(w=w, delta=delta, frac=frac, shaping_needed=True)


# --------------------------------------------------------------- 롤아웃 ---
def trace_episode(env, scn, lay, *, r_ring, seed=0, horizon=None, mode="ring"):
    """발사하지 않고 끝까지 굴리며 매 스텝의 판정 재료를 기록한다."""
    env.reset(seed=seed)
    H = int(lay.episode_len if horizon is None else horizon)
    rec: List[dict] = []
    contact: set = set()
    for t in range(H):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        for i, s in enumerate(lims):
            if float(np.linalg.norm(p_att - env._p(s))) <= env.kill_radius:
                contact.add(i)
        if mode == "hold":
            acts = {lid: np.zeros(4, np.float32) for lid in env.limiter_ids}
        else:
            acts = {lid: scripted_shaping_limiter(
                        i, env.N, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                        tau=env.tau_deploy, a_max=scn.limiter.a_max,
                        r_ring=r_ring, dt=env.dt)
                    for i, lid in enumerate(env.limiter_ids)}
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy, clean_threshold_crossed=False)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, info = env.step(acts)
        fi = info[env.finisher_id]
        rec.append(dict(t=t, x=float(p_att[0]),
                        worst=float(fi["v_shot_worst"]), soft=float(fi["v_shot_soft"]),
                        boxed=bool(fi["boxed_in"]), pfeas=float(fi["p_feasible"]),
                        n_contact=len(contact)))
        if term[env.finisher_id] or trunc[env.finisher_id]:
            break
    return rec


def best_over_timing(rec):
    """발사 타이밍 전 범위에 대해 두 종점을 사후 평가한다 (S5: 판정은 발사 시점 동결)."""
    frozen = [r for r in rec if (not r["boxed"]) and r["worst"] >= 1.0]
    relaxed = [r for r in rec if r["worst"] >= 1.0 and r["n_contact"] == 0]
    return dict(
        frozen_ok=bool(frozen), relaxed_ok=bool(relaxed),
        frozen_t=frozen[0]["t"] if frozen else None,
        relaxed_t=relaxed[0]["t"] if relaxed else None,
        max_worst=max((r["worst"] for r in rec), default=0.0),
        max_pfeas_at_worst1=max((r["pfeas"] for r in rec if r["worst"] >= 1.0),
                                default=0.0),
        n_worst1=sum(1 for r in rec if r["worst"] >= 1.0),
        n_worst1_unboxed=sum(1 for r in rec if r["worst"] >= 1.0 and not r["boxed"]),
        min_contact_at_worst1=min((r["n_contact"] for r in rec if r["worst"] >= 1.0),
                                  default=None),
    )


def oracle_scan(tau, *, a_att=30.0, rho=2.0, r_kill=2.0, n_samples=2000,
                r_rings=None, seed=0):
    """한 tau 에서 링 반경 족을 훑어 두 종점의 도달가능성 상한을 낸다."""
    core = nb_core(a_att, tau, rho, r_kill)
    r_nb = nb_ring_radius(a_att, tau, rho)
    grid = r_rings if r_rings is not None else sorted(
        {round(x, 2) for x in [r_nb, r_nb - 0.2, r_nb + 0.2, 2.1, 2.5, 3.0, 3.5, 4.0]}
        if r_nb > 0 else [2.1])
    out = []
    for rr in grid:
        env, scn, lay = make_train_env(as_config({
            "physics.tau_deploy": float(tau),
            "physics.a_att_max": float(a_att),
            "viability.n_samples": int(n_samples),
        }))
        rec = trace_episode(env, scn, lay, r_ring=float(rr), seed=seed)
        b = best_over_timing(rec)
        b.update(r_ring=float(rr), tau=float(tau), a_att=float(a_att))
        out.append(b)
    return dict(tau=tau, a_att=a_att, r_nb=r_nb, core=core, cells=out,
                frozen_ok=any(c["frozen_ok"] for c in out),
                relaxed_ok=any(c["relaxed_ok"] for c in out))


def main(argv=None):
    ap = argparse.ArgumentParser(description="tau 축 위의 비손실 도달가능성 상한")
    ap.add_argument("--a-att", type=float, default=30.0)
    ap.add_argument("--n-samples", type=int, default=2000)
    ap.add_argument("--taus", type=float, nargs="*",
                    default=[0.15, 0.20, 0.25, 0.30, 0.35, 0.40])
    args = ap.parse_args(argv)

    print(f"# ORACLE_RING_FAMILY_UPPER_BOUND   a_att={args.a_att}  "
          f"n_samples={args.n_samples}")
    print("# SEARCH_CANDIDATE / FIXED_CONDITION / NON-EVIDENTIAL")
    print("# 종점 2개: frozen=(not boxed) and worst>=1  |  relaxed=worst>=1 and contact==0\n")
    print(f"{'tau':>5} {'w':>6} {'r_nb':>5} {'core d':>7} {'(d/w)^3':>9} | "
          f"{'frozen':>7} {'relaxed':>8} | {'max_worst':>9} {'n_w1':>5} {'n_w1_unbox':>10}")
    print("-" * 92)
    for tau in args.taus:
        res = oracle_scan(tau, a_att=args.a_att, n_samples=args.n_samples)
        c = res["core"]
        best = max(res["cells"], key=lambda z: (z["frozen_ok"], z["relaxed_ok"],
                                                z["max_worst"]))
        print(f"{tau:5.2f} {c['w']:6.2f} {res['r_nb']:5.2f} {c['delta']:7.3f} "
              f"{c['frac']:9.2e} | {str(res['frozen_ok']):>7} {str(res['relaxed_ok']):>8} | "
              f"{best['max_worst']:9.3f} {best['n_worst1']:5d} {best['n_worst1_unboxed']:10d}")
    return 0


if __name__ == "__main__":
    main()
