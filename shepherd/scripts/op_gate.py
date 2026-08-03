"""운용점 적형성 게이트 — 선언 후, 학습 전에 반드시 돌린다.

무엇을 보는가: **무개입(hold) 대비 조향(ring/intercept)의 차이.**
hold 가 이미 다 잡으면 조향 문제 자체가 없는 것이고, 학습을 돌릴 이유가 없다.
명제 N(docs/10)의 운용 버전이다: w = 0.5*a*tau^2 <= rho 이면 조향의 방어가치는 0.

**결과가 나쁘다고 값을 되돌리지 않는다.** 되돌리면 결과를 보고 물리를 고치는 것이다.
게이트는 "선언이 시나리오를 깨뜨렸는가"를 보는 것이지 좋은 값을 찾는 도구가 아니다.

2026-08-01 확장 (docs/46)
-------------------------
임무 결과만 보면 "조향 이득 0" 으로 읽히지만, 그건 **두 개의 반대 효과가 상쇄된
결과**였다. 그래서 게이트가 두 채널을 **따로** 보고한다:

    채널 (i)  도달집합 차단   Δbest = best v_shot(limiter 있음) - (limiter 제거)   유리
    채널 (ii) 조준 파괴       psi · omega_req = v_perp/d                            불리

판정식 (docs/46 §4.2, 결과 보기 전 선언):

    어떤 배치가 hold 대비 **최선 v_shot 과 평균 v_shot 을 둘 다** 개선하지 못하면
    그 배치의 협력은 **순이득이 없다**. ring 이 그 예다.

  python -m shepherd.scripts.op_gate [--n 12] [--nc 8] [--no-channels]
"""
from __future__ import annotations

import argparse
from collections import Counter

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_config import m4_config, THREAT_BRACKET
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.spawn_rand import SpawnSpec
from shepherd.scripts.channel_split import run_split, summarize_split
from shepherd.scripts.mission_rollout import run_episode, summarize

# ★ 게이트는 **학습에 쓸 스택 그대로** 돌려야 한다. 기본 env 만 돌리면
#   하드킬 방아쇠 · no-kinetic zone · 공격자 사다리가 빠져 실제와 다른 것을 잰다.
M4KW = dict(system=SystemSpec(enabled=True),
            reward=RewardSpec(w_kill=0.5, enabled=True),
            attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
            spawn=SpawnSpec())


_NEUT = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL")


def gate(tag, randomize, n):
    """임무 수준 게이트.

    **판정은 무력화율로 한다.** `interdiction_rate = 1 - PENETRATED` 는 SPENT_FAIL
    (탄 소진·미무력화)과 TRUNCATED(우측 절단)를 성공으로 세므로 부풀려진다
    -- docs/40 §8.2 에서 이미 지적한 결함이고, `mission_eval` 은 이미 분해해서 낸다.
    게이트만 옛 정의를 쓰고 있었다. 옛 값도 **함께** 찍어 비교 가능하게 남긴다.
    (이 정정은 게이트를 더 엄격하게 만든다 = 우리에게 불리한 방향.)
    """
    print(f"\n===== {tag} =====")
    out = {}
    for mode in ("hold", "ring", "intercept"):
        res = []
        for ep in range(n):
            st = build_m4_env(0, ep, randomize_threat=randomize, **M4KW)
            env, scn, lay = st.env, st.scn, st.lay
            res.append(run_episode(env, scn, lay, seed=ep, limiter_mode=mode,
                                   fire_mode="clean"))
        s = dict(summarize(res))
        cnt = Counter(r.label for r in res)
        s["neutralized_rate"] = sum(cnt[k] for k in _NEUT) / max(len(res), 1)
        out[mode] = s
        print(f"  {mode:9s} {dict(cnt)}")
        print(f"            무력화 {s['neutralized_rate']:.2f}  (옛 '저지' {s['interdiction_rate']:.2f})"
              f"  비손실 {s['nondestructive_frac']:.2f}"
              f"  접촉 {s['mean_contact']:.2f}  최소거리 {s['mean_min_dist']:.2f}"
              f"  발사 {sum(1 for r in res if r.fire_step is not None)}")
    lift = out["ring"]["neutralized_rate"] - out["hold"]["neutralized_rate"]
    lift_old = out["ring"]["interdiction_rate"] - out["hold"]["interdiction_rate"]
    print(f"\n  >> 조향 이득 (ring - hold) = {lift:+.2f} 무력화 기준"
          f"   / {lift_old:+.2f} 옛 '저지' 기준")
    if out["hold"]["neutralized_rate"] >= 0.99:
        print("  >> ★ 게이트 실패: 무개입이 이미 전부 무력화한다 -- 조향 문제가 없다")
    elif abs(lift) < 0.05:
        print("  >> ★ 게이트 실패: 조향이 무의미하다")
    else:
        print("  >> 게이트 통과: 조향에 여지가 있다")
    if abs(lift) < 0.05 <= abs(lift_old):
        print("  >> (옛 정의로는 통과였다 -- SPENT_FAIL 을 성공으로 세던 부풀림)")
    return out


MODES = ("hold", "ring", "intercept")


def channel_gate(n, randomize):
    """docs/46 §4.2 — 두 채널을 따로 재고 선언된 판정식을 적용한다."""
    cfg = m4_config()
    print(f"\n===== 채널 분해 (docs/46) · 위협 {'랜덤화' if randomize else '고정'} · n={n} =====")
    res = run_split(0, n, tau=float(cfg["physics"]["tau_deploy"]),
                    range_max=float(cfg["viability"]["cone"]["range_max"]),
                    randomize_threat=randomize, modes=MODES, **M4KW)
    s = summarize_split(res, omega_max=float(cfg["attitude"]["omega_max"]))
    print(f"  {'배치':<10}{'채널(i) Δv_shot':>16}{'최선 v_shot':>12}{'평균 v_shot':>12}"
          f"{'v⊥ 중앙':>10}{'ω>ωmax':>9}{'ψ 중앙':>9}")
    ref = s.get("hold", {})
    for m in MODES:
        x = s.get(m, {})
        if not x.get("n_steps_in_band"):
            print(f"  {m:<10}  (밴드 진입 없음)")
            continue
        print(f"  {m:<10}{x['ch_i_d_vshot_soft_mean']:>16.5f}"
              f"{x['best_vshot_with_limiters_med']:>12.4f}"
              f"{x['mean_vshot_with_limiters_med']:>12.4f}"
              f"{x['ch_ii_v_perp_med']:>10.2f}"
              f"{100*x['ch_ii_frac_omega_gt_max']:>8.1f}%{x['ch_ii_psi_deg_med']:>9.1f}")
    print()
    for m in MODES:
        if m == "hold":
            continue
        x = s.get(m, {})
        if not (x.get("n_steps_in_band") and ref.get("n_steps_in_band")):
            continue
        db = x["best_vshot_with_limiters_med"] - ref["best_vshot_with_limiters_med"]
        dm = x["mean_vshot_with_limiters_med"] - ref["mean_vshot_with_limiters_med"]
        ok = (db > 1e-6) and (dm > 1e-6)
        print(f"  >> {m:9s} vs hold : 최선 {db:+.4f}  평균 {dm:+.4f}  -> "
              + ("순이득 있음" if ok else "★ 순이득 없음 (선언 판정식)"))
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--nc", type=int, default=8, help="채널 분해 에피소드 수 (비쌈)")
    ap.add_argument("--no-channels", action="store_true")
    a = ap.parse_args(argv)
    cfg = m4_config()
    tau, rho = cfg["physics"]["tau_deploy"], cfg["physics"]["net_radius"]
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    a_star = 2 * rho / tau ** 2
    print(f"명제 N 사전점검: tau={tau} rho={rho}  ->  a* = {a_star:.1f} m/s^2")
    print(f"  브래킷 [{lo:g}, {hi:g}] "
          + ("가로지름 OK -- 두 regime 이 한 축에" if lo < a_star < hi
             else "★ 안 가로지름: 한 regime 뿐이라 조향 축이 생기지 않는다"))
    print(f"  tau_kill = {M4KW['system'].tau_kill}  kill_radius = {cfg['physics']['kill_radius']}")
    gate("M4 스택 · 위협 고정", False, a.n)
    gate("M4 스택 · 위협 랜덤화", True, a.n)
    if not a.no_channels:
        channel_gate(a.nc, True)


if __name__ == "__main__":
    main()
