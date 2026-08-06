"""2b witness **여유 감사** — 같은 env·같은 union·같은 시드 (docs/52 §8.1c).

왜 표본 수·시드부터 안 바꾸나
-----------------------------
표본 수나 시드를 바꾸면 **탈출집합 자체가 달라진다.** 그건 동일 환경의 witness
검증이 아니라 **이산화·모델 민감도 감사**이고 별도 단계다 (§8.1d).

먼저 물을 것은 *"현행 env 계약 안에서 이 witness 가 기하적으로 얼마나 여유
있는가"* 다. `n_feasible = 26` 이 1 보다 낫다는 신호이긴 해도 **강건성 지표가
아니다** -- 26 개가 전부 좁은 군집에 경계로부터 1 mm 떨어져 있을 수도 있다.

재는 것
-------
    m_bad  = min_{b∈B}  max_i ( r_kill − d_bi )        > 0 이면 모든 bad 가 그만큼 덮임
    m_good = max_{g∈G_surv} min_i ( d_gi − r_kill )    > 0 이면 good 이 그만큼 떨어져 생존

    m_bad  ≈ 0 -> bad 하나가 경계에 걸려 있다
    m_good ≈ 0 -> 조금만 움직여도 boxed-in

    + limiter 별 도달집합 경계까지의 여유
    + 국소 perturbation (0.01 / 0.05 / 0.10 / 0.25 m) -> 실패를 **두 종류로 분리**
        uncovered_bad : 덜 막아서 실패 (v_worst < 1)
        boxed_in      : 너무 막아서 실패
    + 발사 시각 t−1 / t / t+1 재replay (**재최적화 없이**)

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
from shepherd.m4_env import build_m4_env
from shepherd.scripts.contact_reachability import reach_radius
from shepherd.spawn_rand import SpawnSpec

__all__ = ["margin_audit"]

RADII = (0.01, 0.05, 0.10, 0.25)
N_PERTURB = 600


def _kw() -> dict:
    return dict(system=SystemSpec(), reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def _classify(vf, theta_fire: float) -> str:
    if vf.boxed_in:
        return "boxed_in"
    if vf.v_shot_worst >= 1.0 and vf.v_shot_soft >= theta_fire:
        return "clean"
    return "uncovered_bad"


def margin_audit(seed0: int, ep: int, fire_step: int, L: np.ndarray,
                 *, n_perturb: int = N_PERTURB, seed: int = 0) -> dict:
    from shepherd.scripts.mission_rollout import scripted_role_actions

    rng = np.random.default_rng(seed)
    st = build_m4_env(seed0, ep, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    a_max, v_max = float(scn.limiter.a_max), float(st.threat["v_lim"])
    dt, tau, r_kill = float(env.dt), float(env.tau_deploy), float(env.kill_radius)
    C0 = np.array([env._p(l) for l in env._states()[0]], float)
    V0 = np.array([env._v(l) for l in env._states()[0]], float)
    L = np.asarray(L, float)

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

    p_att, v_att, fin9 = frames[fire_step]
    kw = env._vshot_kwargs(p_att, v_att, fin9)
    _, _, caught, tr = V._union_sets(
        p_att, v_att, tau=tau, a_att_max=env.a_att_max, limiters=None,
        kill_radius=r_kill, attacker_turn_limited=False, omega_att_max=None,
        e_att=None, n=env.n_samples, n_segments=env.n_segments, seed=0,
        net_center=None, net_radius=None, return_paths=True, **kw)
    bad, good = ~caught, caught

    # 표본 x limiter 최소거리
    d = np.linalg.norm(tr.paths[:, :, None, :] - L[None, None, :, :],
                       axis=3).min(axis=1)                       # (n_samp, n_lim)
    blocked = (d <= r_kill).any(axis=1)
    surv_good = good & ~blocked

    m_bad = float(np.min(np.max(r_kill - d[bad], axis=1))) if bad.any() else float("nan")
    m_good = (float(np.max(np.min(d[surv_good] - r_kill, axis=1)))
              if surv_good.any() else float("nan"))
    tk = fire_step * dt
    slack = (reach_radius(tk, a_max, v_max)
             - np.linalg.norm(L - (C0 + V0 * tk), axis=1))

    base = env._vshot(p_att, v_att, L, fin9, seed=0)
    out = {"episode": ep, "fire_step": fire_step,
           "n_bad": int(bad.sum()), "n_good": int(good.sum()),
           "n_surviving_good": int(surv_good.sum()),
           "m_bad": m_bad, "m_good": m_good,
           "reach_slack": [float(x) for x in slack],
           "base": {"class": _classify(base, env.theta_fire),
                    "n_feasible": int(base.n_feasible),
                    "v_worst": float(base.v_shot_worst),
                    "v_soft": float(base.v_shot_soft)},
           "perturbation": {}, "fire_step_shift": {}}

    for r in RADII:
        cnt = {"clean": 0, "uncovered_bad": 0, "boxed_in": 0}
        for _ in range(n_perturb):
            u = rng.normal(size=L.shape)
            u /= np.linalg.norm(u, axis=1, keepdims=True)
            Lp = L + u * (r * rng.random((len(L), 1)) ** (1.0 / 3.0))
            cnt[_classify(env._vshot(p_att, v_att, Lp, fin9, seed=0),
                          env.theta_fire)] += 1
        out["perturbation"][f"{r:.2f}"] = {k: v / n_perturb for k, v in cnt.items()}

    for ds in (-1, 0, +1):                     # ★ 재최적화 없이 그대로 replay
        j = fire_step + ds
        if 0 <= j < len(frames):
            pa, va, f9 = frames[j]
            vf = env._vshot(pa, va, L, f9, seed=0)
            out["fire_step_shift"][str(ds)] = {
                "class": _classify(vf, env.theta_fire),
                "n_feasible": int(vf.n_feasible),
                "v_worst": float(vf.v_shot_worst)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="2b witness 여유 감사 (docs/52 §8.1c)")
    ap.add_argument("--witness", default="results/snapshot_witness.json")
    ap.add_argument("--n-perturb", type=int, default=N_PERTURB)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    w = json.load(open(args.witness))
    res = []
    for rec in w["records"]:
        if not rec.get("found"):
            continue
        r = margin_audit(0, rec["episode"], rec["fire_step"],
                         np.array(rec["limiter_positions"]),
                         n_perturb=args.n_perturb)
        res.append(r)
        print(f"ep{r['episode']} t={r['fire_step']}  n_feasible={r['base']['n_feasible']}"
              f"  생존good={r['n_surviving_good']}")
        print(f"   m_bad {r['m_bad']:+.4f}   m_good {r['m_good']:+.4f}   "
              f"reach_slack {[round(x, 2) for x in r['reach_slack']]}")
        for rad, c in r["perturbation"].items():
            print(f"   ±{rad}m  clean {c['clean']:.3f}  "
                  f"덜막음 {c['uncovered_bad']:.3f}  너무막음 {c['boxed_in']:.3f}")
        sh = "  ".join("t{:+d}={}({})".format(int(k), v["class"], v["n_feasible"])
                       for k, v in r["fire_step_shift"].items())
        print(f"   발사시각 이동: {sh}")
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
