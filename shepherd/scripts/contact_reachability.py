"""M4 성형 **접촉** 도달성 감사 — 필요조건 검사 (docs/52).

★ 이 스크립트가 인증하지 않는 것
--------------------------------
NET_CAPTURE 의 실행 가능성을 인증하지 **않는다.** 네 limiter 가 동시에 모든
탈출 표본을 폐쇄할 수 있는지도 묻지 않는다. 검사하는 것은 오직

    "적어도 한 limiter 가 성형 영향관에 물리적으로 도달할 수 있는가"

라는 **필요조건**이다. 통과해도 임무 성공은 따로 물어야 한다 (docs/52 §6).

왜 닫힌 형식으로 되는가
----------------------
성형 전이법칙이 단순 거리 판정이기 때문이다 (`viability._feasible_limiter`):

    탈출 표본 포물선이 [0, tau] 동안 어떤 limiter 의 kill_radius 안에 들어가면
    그 표본을 제거. -> **영향 반경 = kill_radius, limiter 위치만 사용.**

따라서 최적화 없이 도달가능집합과의 거리만으로 상한을 잰다.

    c_i(t) = p_i(0) + v_i(0)·t                     도달가능구 중심
    r_i(t) = ½ a_max t²            (a_max·t <= v_max)
           = v_max·t − v_max²/(2 a_max)   (그 뒤, 속도 상한 반영)

    m_e = min over t, i, s in [t, t+tau] of
              ( |p_att(s) − c_i(t)| − r_i(t) − r_shape )

    m_e <= 0  -> 접촉 가능        m_e > 0 -> 이 근사 아래 접촉 불가

낙관성 (docs/52 §5 — 반드시 같이 읽을 것)
----------------------------------------
1. `p_att` 는 **hold** 궤적이다. 실제로 쫓아가면 반응형 A2 는 회피한다.
2. ★ 시각 t 의 도달집합을 구간 [t, t+tau] **전체**와 비교한다. 즉 limiter 가
   t 에 도착한 뒤 tau 동안 그 자리에서 영향을 준다고 보는 셈이다. 정확한
   조건은 같은 절대시각 s 에서 `p_lim(s) ∈ R_i(s)` 인지다. **이건 정확한
   동역학 인증이 아니라 낙관적 필요조건 검사다.**
3. 접촉 != 성공. 성공은 `v_shot_worst >= 1.0` 즉 **모든** 탈출 표본 폐쇄다.

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.spawn_rand import SpawnSpec

__all__ = ["reach_radius", "episode_margin", "audit"]


def _kw() -> dict:
    return dict(system=SystemSpec(), reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def reach_radius(t: float, a_max: float, v_max: float) -> float:
    """2중적분기 도달 반경. **속도 상한을 반영한 piecewise** 식이다.

    단순 `½ a t²` 만 쓰면 속도 상한 도달 이후 도달집합을 과대평가한다
    (리뷰 3 §2 지적). 가속 구간과 등속 구간을 나눈다.
    """
    t, a_max, v_max = float(t), float(a_max), float(v_max)
    if a_max <= 0.0:
        return 0.0
    t_sat = v_max / a_max
    if t <= t_sat:
        return 0.5 * a_max * t * t
    return v_max * t - 0.5 * v_max * v_max / a_max


def episode_margin(seed0: int, ep: int) -> dict:
    """한 판의 접촉 여유 `m_e`. <= 0 이면 접촉 가능."""
    from shepherd.scripts.mission_rollout import scripted_role_actions

    st = build_m4_env(seed0, ep, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    a_max = float(scn.limiter.a_max)
    v_max = float(st.threat["v_lim"])
    dt, tau, r_shape = float(env.dt), float(env.tau_deploy), float(env.kill_radius)

    lims0 = env._states()[0]
    C0 = np.array([env._p(l) for l in lims0], float)
    V0 = np.array([env._v(l) for l in lims0], float)

    path: List[np.ndarray] = []
    for _ in range(int(lay.episode_len)):
        path.append(env._p(env._states()[2]).copy())
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="clean")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if (term and term.get(fid)) or (trunc and trunc.get(fid)):
            break
    P = np.asarray(path, float)
    n_tau = max(1, int(round(tau / dt)))

    m_e, t_star = np.inf, -1
    for k in range(len(P)):
        tk = k * dt
        C = C0 + V0 * tk
        r = reach_radius(tk, a_max, v_max)
        seg = P[k:k + n_tau + 1]
        d = float(np.linalg.norm(C[:, None, :] - seg[None, :, :], axis=2).min())
        v = d - r - r_shape
        if v < m_e:
            m_e, t_star = v, k
    return {"episode": ep, "margin": float(m_e), "t_star": int(t_star),
            "steps": int(len(P)),
            "regime": regime_of(st.threat["a_att"], st.threat["tau"],
                                st.threat["net_radius"]),
            "a_att": float(st.threat["a_att"]), "a_lim": float(st.threat["a_lim"]),
            "a_max_used": a_max, "v_max_used": v_max, "r_shape": r_shape}


def audit(n: int = 200, seed0: int = 0) -> dict:
    recs = [episode_margin(seed0, ep) for ep in range(n)]
    m = np.array([r["margin"] for r in recs])
    reach = m <= 0.0
    out: Dict[str, dict] = {}
    for name, mask in (("ALL", np.ones(len(m), bool)),
                       ("SHAPING_NEEDED",
                        np.array([r["regime"] == "SHAPING_NEEDED" for r in recs])),
                       ("FREE_CAPTURE",
                        np.array([r["regime"] == "FREE_CAPTURE" for r in recs]))):
        if not mask.any():
            continue
        out[name] = {"n": int(mask.sum()), "reachable": int(reach[mask].sum()),
                     "frac": float(reach[mask].mean()),
                     "margin_median": float(np.median(m[mask])),
                     "margin_p10": float(np.percentile(m[mask], 10)),
                     "margin_min": float(m[mask].min()),
                     "a_lim_median": float(np.median([r["a_lim"] for r, k
                                                      in zip(recs, mask) if k]))}
    return {"predicate": ("m_e = min_{t,i,s in [t,t+tau]} (|p_att(s) - c_i(t)| "
                          "- r_i(t) - r_shape);  m_e <= 0 => 접촉 가능"),
            "shaping_law": ("viability._feasible_limiter: 탈출 포물선이 [0,tau] 동안 "
                            "limiter 의 kill_radius 안에 들어가면 표본 제거. "
                            "영향 반경 = kill_radius, limiter 위치만 사용"),
            "not_certified": ("NET_CAPTURE 실행가능성 / 네 limiter 동시 coverage / "
                              "반응형 A2 하 유지 — 전부 미검증"),
            "optimism": ["p_att 는 hold 궤적 (비반응)",
                         "시각 t 의 도달집합을 [t, t+tau] 전체와 비교 (낙관적)",
                         "접촉 != 성공 (성공은 모든 탈출 표본 폐쇄)"],
            "by_regime": out, "records": recs}


def main() -> None:
    ap = argparse.ArgumentParser(description="성형 접촉 도달성 감사 (docs/52)")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    r = audit(args.n, args.seed0)
    print("성형 영향법칙:", r["shaping_law"])
    print("술어:", r["predicate"])
    for k, v in r["by_regime"].items():
        print(f"  {k:15s} 접촉가능 {v['reachable']:3d}/{v['n']:3d} = {v['frac']:.3f}  "
              f"m_e 중앙 {v['margin_median']:+.2f} p10 {v['margin_p10']:+.2f} "
              f"최소 {v['margin_min']:+.2f}  (a_lim 중앙 {v['a_lim_median']:.2f})")
    print("★ 인증 안 된 것:", r["not_certified"])
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
