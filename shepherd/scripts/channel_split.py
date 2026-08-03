"""limiter 방어가치의 **두 채널 분리 계측** — docs/45 §4 의 (다).

WHY
---
`docs/42 §6` 은 paired n=48 에서 hold 와 ring 이 48/48 동일 라벨이라고 기록했고,
그것을 "조향 효과 0" 으로 읽었다. `docs/45 §3` 의 실측은 그 해석을 뒤집는다:
같은 조건에서 ring 은 공격자 횡속도를 0.44 -> 7.27 m/s 로 **16배** 키운다.
궤적이 그만큼 다른데 결과가 같다는 것은 "아무 일도 못 한다" 가 아니라
**두 개의 반대 효과가 상쇄된다** 는 뜻이다.

    (i) 도달집합 차단   limiter 가 공격자의 가속 방향을 잘라낸다   -> 유리
                        (`viability._feasible_limiter`, kill_radius 로 판정)
    (ii) 조준 파괴      limiter 가 공격자를 옆으로 밀어 v_perp 를 만든다 -> 불리
                        (네트 지향축이 omega_max 로 rate-limited 이므로 psi 가 커진다)

이 파일은 두 채널을 **따로** 잰다. 그래야 (가)/(나) 를 근거로 고를 수 있다:

    (i) 이 0 에 가깝다면  -> 유리한 채널이 존재하지 않는다. (가)(반경 분리)가 선결조건
    (i) 이 유의하다면     -> 정책이 (i) 을 얻으면서 (ii) 를 피할 수 있는가가 학습 문제

측정 방법
---------
**채널 (i) — 동일상태 반사실.** 같은 (p_att, v_att, finisher 자세) 에서 v_shot 을
두 번 부른다. limiter 위치를 주는 호출과 `limiters=None` 호출. **같은 seed** 를 쓰므로
가속 표본이 공통난수(CRN)로 상쇄되고, 차이는 `_feasible_limiter` 의 기여 **그것 하나**다.

    d_cut = v_shot(with limiters) - v_shot(no limiters)      >= 0 이어야 정상

    주의: n_feasible == 0 이면 v_shot_soft 가 1.0 로 반환된다 (R4 봉쇄 신호이지
    깨끗한 발사해가 아니다). `boxed_in` 스텝은 분리해서 보고하고 d_cut 평균에서 뺀다.

**채널 (ii) — 짝지은 롤아웃.** 궤적 효과이므로 동일상태 반사실로는 잡히지 않는다.
같은 에피소드 seed 로 hold / ring 을 각각 굴리고 (위협 draw · 스폰 · 공격자 위상이
모두 동일) 같은 스텝 인덱스에서 psi 와 omega_req 를 비교한다.

모델·운용점은 **바꾸지 않는다.** 계측 전용.

torch-free.
"""
from __future__ import annotations

import argparse
import json
from typing import Optional

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_config import m4_config
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.spawn_rand import SpawnSpec

__all__ = ["split_episode", "run_split", "summarize_split"]


def _unit(v):
    n = float(np.linalg.norm(v))
    return (v / n) if n > 1e-9 else np.zeros_like(v)


def split_episode(env, scn, lay, *, seed: int, limiter_mode: str, tau: float,
                  range_max: float, max_steps: Optional[int] = None) -> list:
    """스텝별 (i) 반사실 이득 + (ii) 조준 기하. env.step 은 기존 경로 그대로."""
    from shepherd.agents.baselines import scripted_finisher
    from shepherd.scripts.mission_rollout import _limiter_actions, _zero_commit

    env.reset(seed=seed)
    horizon = int(lay.episode_len if max_steps is None else max_steps)
    rows = []
    for t in range(horizon):
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        p_fin, e_fin = env._p(fin), env._e(fin)
        L = [env._p(s) for s in lims]

        # ---- 채널 (i): 동일상태 반사실. 같은 seed = 공통난수 ------------------
        s_step = int(seed) * 100003 + t          # 결정론적, 두 호출이 공유
        vs_with = env._vshot(p_att, v_att, L, fin, seed=s_step)
        vs_free = env._vshot(p_att, v_att, None, fin, seed=s_step)

        # ---- 채널 (ii): 조준 기하 (docs/45 §2 와 동일 정의) -------------------
        p_coast = p_att + v_att * tau
        r_now, r_coast = p_att - p_fin, p_coast - p_fin
        d = float(np.linalg.norm(r_now))
        if d < 1e-6:
            break
        u = r_now / d
        e_hat = _unit(e_fin)
        v_perp = float(np.linalg.norm(v_att - float(v_att @ u) * u))
        psi = float(np.arccos(np.clip(e_hat @ _unit(r_coast), -1.0, 1.0)))
        ax = float(r_coast @ e_hat)

        rows.append(dict(
            t=t, d=d, v_perp=v_perp, omega_req=v_perp / d, psi=psi, ax=ax,
            in_band=bool(0.0 <= ax <= range_max),
            vs_with=float(vs_with.v_shot_soft), vs_free=float(vs_free.v_shot_soft),
            worst_with=float(vs_with.v_shot_worst), worst_free=float(vs_free.v_shot_worst),
            boxed=bool(vs_with.boxed_in), p_feas=float(vs_with.p_feasible),
        ))

        acts = _limiter_actions(env, scn, lay, limiter_mode, lims, p_att, v_att)
        _zero_commit(acts)
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy, clean_threshold_crossed=False)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if (bool(term[env.finisher_id]) if term else False) or \
           (bool(trunc[env.finisher_id]) if trunc else False):
            break
    return rows


def run_split(seed0: int, episodes: int, *, tau: float, range_max: float,
              attacker: Optional[AttackerSpec] = None,
              system: Optional[SystemSpec] = None,
              reward: Optional[RewardSpec] = None,
              spawn: Optional[SpawnSpec] = None,
              randomize_threat: bool = True,
              modes=("hold", "ring")) -> dict:
    """짝지은 롤아웃. **모드 간에 seed·위협 draw·스폰·공격자 위상이 모두 같다.**"""
    system = SystemSpec() if system is None else system
    reward = RewardSpec() if reward is None else reward
    spec = attacker if attacker is not None else AttackerSpec()
    spawn = SpawnSpec() if spawn is None else spawn

    per_mode = {m: [] for m in modes}
    regimes = []
    for ep in range(episodes):
        for m in modes:
            st = build_m4_env(seed0, ep, system=system, reward=reward,
                              attacker=spec, spawn=spawn,
                              randomize_threat=randomize_threat)
            rows = split_episode(st.env, st.scn, st.lay, seed=seed0 + ep,
                                 limiter_mode=m, tau=tau, range_max=range_max)
            per_mode[m].append(rows)
        regimes.append(regime_of(st.threat["a_att"], st.threat["tau"],
                                 st.threat["net_radius"]))
    return dict(per_mode=per_mode, regimes=regimes, episodes=episodes,
                tau=tau, range_max=range_max)


def _flat(eps, band_only=True):
    out = []
    for rows in eps:
        for r in rows:
            if band_only and not r["in_band"]:
                continue
            out.append(r)
    return out


def summarize_split(res: dict, omega_max: float) -> dict:
    out = {"episodes": res["episodes"]}
    for m, eps in res["per_mode"].items():
        rows = _flat(eps)
        if not rows:
            out[m] = {"n": 0}
            continue
        boxed = np.array([r["boxed"] for r in rows])
        dsoft = np.array([r["vs_with"] - r["vs_free"] for r in rows])
        dworst = np.array([r["worst_with"] - r["worst_free"] for r in rows])
        pblk = np.array([1.0 - r["p_feas"] for r in rows])
        psi = np.array([r["psi"] for r in rows])
        om = np.array([r["omega_req"] for r in rows])
        vp = np.array([r["v_perp"] for r in rows])
        ok = ~boxed
        # 에피소드별 최선의 발사해 (실제로 쏠 수 있었던 최댓값)
        best_with, best_free, min_psi, mean_with = [], [], [], []
        for e in eps:
            rr = [r for r in e if r["in_band"] and not r["boxed"]]
            if not rr:
                continue
            best_with.append(max(r["vs_with"] for r in rr))
            best_free.append(max(r["vs_free"] for r in rr))
            mean_with.append(float(np.mean([r["vs_with"] for r in rr])))
            min_psi.append(min(r["psi"] for r in rr))
        out[m] = {
            "n_steps_in_band": int(len(rows)),
            "frac_boxed_in": float(boxed.mean()),
            # --- 채널 (i) ---
            "ch_i_blocked_frac_med": float(np.median(pblk)),
            "ch_i_blocked_frac_max": float(pblk.max()),
            "ch_i_d_vshot_soft_mean": float(dsoft[ok].mean()) if ok.any() else 0.0,
            "ch_i_d_vshot_soft_max": float(dsoft[ok].max()) if ok.any() else 0.0,
            "ch_i_d_vshot_worst_sum": float(dworst[ok].sum()) if ok.any() else 0.0,
            "ch_i_steps_with_gain": int((dsoft[ok] > 1e-9).sum()) if ok.any() else 0,
            # --- 채널 (ii) ---
            "ch_ii_v_perp_med": float(np.median(vp)),
            "ch_ii_omega_req_med": float(np.median(om)),
            "ch_ii_frac_omega_gt_max": float((om > omega_max).mean()),
            "ch_ii_psi_deg_med": float(np.degrees(np.median(psi))),
            # --- 순효과 대리 ---
            "best_vshot_with_limiters_med": float(np.median(best_with)) if best_with else None,
            "mean_vshot_with_limiters_med": float(np.median(mean_with)) if mean_with else None,
            "best_vshot_no_limiters_med": float(np.median(best_free)) if best_free else None,
            "episode_min_psi_deg_med": float(np.degrees(np.median(min_psi))) if min_psi else None,
        }
    if set(res["per_mode"]) >= {"hold", "ring"}:
        h, r = out.get("hold", {}), out.get("ring", {})
        if h.get("n_steps_in_band") and r.get("n_steps_in_band"):
            out["ring_minus_hold"] = {
                "ch_i_blocked_frac_med": r["ch_i_blocked_frac_med"] - h["ch_i_blocked_frac_med"],
                "ch_i_d_vshot_soft_mean": r["ch_i_d_vshot_soft_mean"] - h["ch_i_d_vshot_soft_mean"],
                "ch_ii_v_perp_med": r["ch_ii_v_perp_med"] - h["ch_ii_v_perp_med"],
                "ch_ii_psi_deg_med": r["ch_ii_psi_deg_med"] - h["ch_ii_psi_deg_med"],
                "ch_ii_frac_omega_gt_max": r["ch_ii_frac_omega_gt_max"] - h["ch_ii_frac_omega_gt_max"],
            }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="limiter 두 채널 분리 계측 (모델 변경 없음)")
    ap.add_argument("--episodes", type=int, default=48)
    ap.add_argument("--seed", type=int, default=20260801)
    ap.add_argument("--level", default="A1", choices=("A1", "A2", "A3"))
    ap.add_argument("--jink-amp", type=float, default=0.0)
    ap.add_argument("--kill-radius", type=float, default=None,
                    help="반사실 실험용. 주면 extra override 로 넣는다 (선언 아님)")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    extra = {} if args.kill_radius is None else {"physics.kill_radius": args.kill_radius}
    cfg = m4_config(extra)
    tau = float(cfg["physics"]["tau_deploy"])
    R = float(cfg["viability"]["cone"]["range_max"])
    om = float(cfg["attitude"]["omega_max"])

    if extra:
        import shepherd.m4_env as m4e
        _orig = m4e.m4_episode_config

        def _patched(seed, ep, ex=None):
            merged = dict(extra); merged.update(ex or {})
            return _orig(seed, ep, merged)
        m4e.m4_episode_config = _patched
    try:
        res = run_split(args.seed, args.episodes, tau=tau, range_max=R,
                        attacker=AttackerSpec(level=args.level,
                                              jink_amp=args.jink_amp, seed=args.seed))
    finally:
        if extra:
            m4e.m4_episode_config = _orig

    s = summarize_split(res, omega_max=om)
    s["_declared"] = {"omega_max": om, "tau_deploy": tau, "cone.range_max": R,
                      "kill_radius": float(cfg["physics"]["kill_radius"]),
                      "judge": cfg["viability"]["judge"],
                      "attacker": {"level": args.level, "jink_amp": args.jink_amp}}
    print(json.dumps(s, indent=2, ensure_ascii=False))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    return s


if __name__ == "__main__":
    main()
