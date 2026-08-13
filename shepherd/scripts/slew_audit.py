"""네트 지향 slew 구속 실측 — `attitude.omega_max` 가 실제로 구속되는가.

WHY
---
`docs/42 §4` 는 두 개의 omega 를 감사했다: 공격자(inert), limiter(1.9% 구속).
**네트 드론의 지향 slew 는 감사하지 않았다.** 그런데 M4 가 실제로 쓰는 판정은
`judge=se3_cone` 이고 (configs/m2_l2_train.yaml:36), 그 원뿔의 축은

    e_{t+1} <- slew(e_t, e_cmd, omega_max * dt)          (sim/analytic.py:130)

이므로 **lead 조준이 공짜가 아니라 rate-limited 행동**이다. `point_mass` judge 의
`net_center = p_att + v_att*tau` (완벽 lead) 에서 v0 이 상쇄되어 명제 N 이
`w = 0.5*a*tau^2` 로 떨어지는 것과 대조된다 -- 즉 **명제 N 은 "이미 정렬이 끝난"
특수해**이고, 원뿔 판정에는 두 번째 경계가 하나 더 있다:

    omega_req = v_perp / d      (표적을 따라가는 데 필요한 시선 각속도)
    psi                          (잔여 조준 오차) -> a*(psi) = 2 d (tan(theta) - psi) / tau^2

이 스크립트는 **모델을 바꾸지 않는다.** 기존 스택을 그대로 굴리면서 위 두 양의
실제 분포만 잰다. 브래킷 등방 가정 하의 해석적 추정치(55.7%)가 실제 롤아웃
(대부분 정면 접근)에서도 유지되는지 확인하는 것이 목적이다.

    측정 창: cone 밴드 안 (d <= range_max) 이면서 아직 발사 전인 스텝
             = "지금 쏠 수 있었을 수도 있는" 스텝

torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
from typing import Optional

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_config import M4_OVERRIDES, m4_config
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.spawn_rand import SpawnSpec

__all__ = ["aim_geometry", "audit_episode", "audit", "summarize"]


def _unit(v):
    n = float(np.linalg.norm(v))
    return (v / n) if n > 1e-9 else np.zeros_like(v)


def aim_geometry(p_att, v_att, p_fin, e_fin, *, tau: float, range_max: float):
    """★ ψ 의 **단일 정의원** (docs/83 §12A). 순수 함수 — 상태를 바꾸지 않는다.

    2026-08-13 추출: 수식은 `audit_episode` 안에 있던 것을 **그대로** 옮겼다
    (연산 순서까지 동일 -> float-exact). 목적은 metric 재정의가 아니라
    **측정기를 production rollout 에도 이식**하는 것이다 — 기존 audit 경로와
    E1b telemetry 경로가 같은 함수를 호출하게 만들어 "같은 ψ 냐" 문제를 없앤다.

    `d < 1e-6` 이면 `None` (측정 불가). 호출부의 기존 `continue` 의미를 보존한다.
    """
    p_att = np.asarray(p_att, float); v_att = np.asarray(v_att, float)
    p_fin = np.asarray(p_fin, float); e_fin = np.asarray(e_fin, float)
    # 조준해야 하는 점 = 표류점 (net 이 열리는 시각의 등속 예측 위치)
    p_coast = p_att + v_att * tau
    r_now, r_coast = p_att - p_fin, p_coast - p_fin
    d = float(np.linalg.norm(r_now))
    if d < 1e-6:
        return None
    u = r_now / d

    v_perp = float(np.linalg.norm(v_att - float(v_att @ u) * u))
    omega_req = v_perp / d
    e_hat = _unit(e_fin)
    psi = float(np.arccos(np.clip(e_hat @ _unit(r_coast), -1.0, 1.0)))
    # cone judge 의 밴드 검정과 동일한 정의: 축방향 좌표 (viability._caught_se3_cone)
    ax = float(r_coast @ e_hat)
    # 2026-08-13 추가(순수 additive — psi 정의·기존 필드 불변, REG-1 재확인됨):
    # 원뿔은 apex 에서 벌어지므로 유효 횡반경이 ax*tan(theta) 다. 그 검정을 소각
    # 근사 없이 하려면 **횡편차 자체**가 필요하다. ax = |r|cos(psi),
    # r_perp = |r|sin(psi) 이므로 r_perp = ax*tan(psi) 가 정확히 성립한다.
    r_perp = float(np.linalg.norm(r_coast - ax * e_hat))
    return dict(d=d, v_perp=v_perp, omega_req=omega_req, psi=psi,
                ax=ax, r_perp=r_perp, in_band=bool(0.0 <= ax <= range_max))


def audit_episode(env, scn, lay, *, seed: int, tau: float, range_max: float,
                  limiter_mode: str = "hold", max_steps: Optional[int] = None) -> dict:
    """한 에피소드에서 시선 기하만 기록한다. env.step 은 기존 경로 그대로.

    ★ 이 rollout 은 **발사가 없다** (`_zero_commit` + `clean_threshold_crossed=False`)
    -- docs/83 §12A.1. 따라서 여기서 나온 ψ 는 no-fire audit world 의 값이고,
    E1/E1b 의 ratified fire 세계 값과 직접 비교하지 않는다.
    """
    from shepherd.agents.baselines import scripted_finisher
    from shepherd.scripts.mission_rollout import _limiter_actions, _zero_commit

    env.reset(seed=seed)
    horizon = int(lay.episode_len if max_steps is None else max_steps)
    rows = []
    for t in range(horizon):
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        p_fin, e_fin = env._p(fin), env._e(fin)

        g = aim_geometry(p_att, v_att, p_fin, e_fin, tau=tau, range_max=range_max)
        if g is None:
            continue
        rows.append(dict(t=t, **g))

        acts = _limiter_actions(env, scn, lay, limiter_mode, lims, p_att, v_att)
        _zero_commit(acts)
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy, clean_threshold_crossed=False)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        terminated = bool(term[env.finisher_id]) if term else False
        truncated = bool(trunc[env.finisher_id]) if trunc else False
        if terminated or truncated:
            break
    return dict(rows=rows)


def audit(seed0: int, episodes: int, *, omega_max: float, tau: float,
          range_max: float, half_angle: float, limiter_mode: str = "hold",
          attacker: Optional[AttackerSpec] = None) -> dict:
    system, reward = SystemSpec(), RewardSpec()
    spec = attacker if attacker is not None else AttackerSpec()
    spawn = SpawnSpec()

    D, VP, OM, PSI, REG = [], [], [], [], []
    ep_min_psi, ep_any_window = [], []
    for ep in range(episodes):
        st = build_m4_env(seed0, ep, system=system, reward=reward,
                          attacker=spec, spawn=spawn)
        r = audit_episode(st.env, st.scn, st.lay, seed=seed0 + ep, tau=tau,
                          range_max=range_max, limiter_mode=limiter_mode)
        reg = regime_of(st.threat["a_att"], st.threat["tau"], st.threat["net_radius"])
        psis = []
        for row in r["rows"]:
            if not row["in_band"]:
                continue
            D.append(row["d"]); VP.append(row["v_perp"])
            OM.append(row["omega_req"]); PSI.append(row["psi"]); REG.append(reg)
            psis.append(row["psi"])
        ep_any_window.append(bool(psis))
        ep_min_psi.append(min(psis) if psis else float("nan"))
    return dict(d=np.array(D), v_perp=np.array(VP), omega_req=np.array(OM),
                psi=np.array(PSI), regime=np.array(REG),
                ep_min_psi=np.array(ep_min_psi), ep_any_window=np.array(ep_any_window),
                omega_max=omega_max, tau=tau, range_max=range_max,
                half_angle=half_angle, episodes=episodes)


def summarize(a: dict) -> dict:
    om, psi, vp, d = a["omega_req"], a["psi"], a["v_perp"], a["d"]
    n = len(om)
    if n == 0:
        return {"n": 0}
    om_max, tau, R, th = a["omega_max"], a["tau"], a["range_max"], a["half_angle"]
    tan_th = math.tan(th)

    def astar(p):
        return max(2.0 * R * (tan_th - p) / tau ** 2, 0.0)

    out = {
        "n_steps_in_band": int(n),
        "d": {"med": float(np.median(d)), "p95": float(np.percentile(d, 95))},
        "v_perp": {"med": float(np.median(vp)), "p95": float(np.percentile(vp, 95))},
        "omega_req": {"med": float(np.median(om)), "p95": float(np.percentile(om, 95))},
        "psi_rad": {"med": float(np.median(psi)), "p95": float(np.percentile(psi, 95))},
        "psi_deg": {"med": float(np.degrees(np.median(psi))),
                    "p95": float(np.degrees(np.percentile(psi, 95)))},
        "frac_omega_req_gt_max": float((om > om_max).mean()),
        "frac_rotation_gt_budget": float(((om * tau) > (om_max * tau)).mean()),
        "frac_psi_gt_cone": float((psi > th).mean()),
        "astar_at_psi_med": astar(float(np.median(psi))),
        "astar_at_psi_p95": astar(float(np.percentile(psi, 95))),
        "astar_at_psi_zero": astar(0.0),
    }
    mp = a["ep_min_psi"]; mp = mp[~np.isnan(mp)]
    if len(mp):
        out["episode_min_psi_deg"] = {"med": float(np.degrees(np.median(mp))),
                                      "p05": float(np.degrees(np.percentile(mp, 5))),
                                      "p95": float(np.degrees(np.percentile(mp, 95)))}
        out["frac_episodes_ever_aligned"] = float((mp <= th).mean())
    out["frac_episodes_with_window"] = float(a["ep_any_window"].mean())

    for reg in sorted(set(a["regime"].tolist())):
        m = a["regime"] == reg
        out[f"by_regime::{reg}"] = {
            "n": int(m.sum()),
            "omega_req_med": float(np.median(om[m])),
            "frac_omega_req_gt_max": float((om[m] > om_max).mean()),
            "psi_deg_med": float(np.degrees(np.median(psi[m]))),
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="네트 지향 slew 구속 실측 (모델 변경 없음)")
    ap.add_argument("--episodes", type=int, default=64)
    ap.add_argument("--seed", type=int, default=20260801)
    ap.add_argument("--limiter-mode", default="hold", choices=("hold", "ring", "intercept"))
    ap.add_argument("--omega-max", type=float, default=None)
    ap.add_argument("--level", default="A1", choices=("A1", "A2", "A3"))
    ap.add_argument("--jink-amp", type=float, default=0.0)
    ap.add_argument("--homing-gain", type=float, default=4.0)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    cfg = m4_config()
    om = args.omega_max if args.omega_max is not None else float(cfg["attitude"]["omega_max"])
    tau = float(cfg["physics"]["tau_deploy"])
    R = float(cfg["viability"]["cone"]["range_max"])
    th = float(cfg["viability"]["cone"]["half_angle"])

    spec = AttackerSpec(level=args.level, jink_amp=args.jink_amp,
                        homing_gain=args.homing_gain, seed=args.seed)
    a = audit(args.seed, args.episodes, omega_max=om, tau=tau, range_max=R,
              half_angle=th, limiter_mode=args.limiter_mode, attacker=spec)
    s = summarize(a)
    s["_attacker"] = {"level": args.level, "jink_amp": args.jink_amp,
                      "homing_gain": args.homing_gain}
    s["_declared"] = {"omega_max": om, "tau_deploy": tau, "cone.range_max": R,
                      "cone.half_angle": th, "limiter_mode": args.limiter_mode,
                      "judge": cfg["viability"]["judge"]}
    print(json.dumps(s, indent=2, ensure_ascii=False))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    return s


if __name__ == "__main__":
    main()
