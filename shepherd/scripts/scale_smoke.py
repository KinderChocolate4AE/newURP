"""[E] 스케일 스모크 — 조밀항 vs 종말항 기여 실측 (docs/29 §15.3, docs/32 [E]).

조밀항은 스텝당 O(0.1~1) x 수십 스텝, 종말항은 1회다. 그대로면 종말 신호가 묻힌다.
**결과를 보기 전에** `terminal_scale` 을 정하고 그 값을 기록하는 것이 규율이다.

종말항의 크기는 이미 안다 -- `RewardSpec.terminal()` 이 반환하는 값은
|{0, b_net*(1-w_kill), b_net, c_pen, c_trunc}| 로 **0~1 범위의 상수**다.
따라서 실측해야 하는 것은 **에피소드당 sum|dense| 하나**뿐이고,
terminal_scale 은 그것과 같은 자릿수로 잡으면 된다.

  python -m shepherd.scripts.scale_smoke --episodes 24
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.spawn_rand import SpawnSpec
from shepherd.scripts.mission_rollout import _limiter_actions, _zero_commit
from shepherd.agents.baselines import scripted_finisher


def _episode(seed0, ep, w_kill, mode):
    """dense 만 켠 채(종말 off) 굴려 sum|dense| 와 라벨을 잰다."""
    kw = dict(system=SystemSpec(enabled=True),
              attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=seed0),
              spawn=SpawnSpec())
    st = build_m4_env(seed0, ep, reward=RewardSpec(
        w_kill=w_kill, enabled=True, terminal_scale=0.0, c_lim=0.0), **kw)
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    d_sum, n, label, prev_clean = 0.0, 0, "TRUNCATED", False
    for t in range(lay.episode_len):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        acts = _limiter_actions(env, scn, lay, mode, lims, p_att, v_att)
        # ★ 2026-08-03: 이 줄이 없었다. 커밋 비트(idx3)는 limiter 행동에 실려 있고
        #   `ring` 은 네 대 모두 1 을 내보낸다 -- 즉 여기만 `run_episode` 와 다른
        #   행동 분포로 돌고 있었다 (정정 3 의 수정이 이 경로에 안 들어감).
        #   재측정: ring sum|dense| 1.044 -> 1.328. 반올림 경계 3.16 미달이라
        #   terminal_scale = 1.0 선언은 불변 (docs/41). P40e 가 이 줄을 지킨다.
        _zero_commit(acts)
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy,
            clean_threshold_crossed=prev_clean)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, rew, te, tr, info = env.step(acts)
        fi = info[env.finisher_id]
        prev_clean = bool(fi.get("clean_net_threshold_crossed", False))
        d_sum += abs(float(rew[env.finisher_id]))
        n += 1
        if any(te.values()) or any(tr.values()):
            label = str(fi.get("m4_outcome") or "TRUNCATED")
            break
    return d_sum, n, label


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=24)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--w-kill", type=float, default=0.5)
    ap.add_argument("--modes", nargs="+", default=["hold", "ring"])
    a = ap.parse_args(argv)

    spec = RewardSpec(w_kill=a.w_kill)
    term_mags = {lab: abs(spec.terminal(lab))
                 for lab in ("NET_CAPTURE", "HARD_KILL", "PENETRATED",
                             "TRUNCATED", "SPENT_FAIL")}
    print("종말항 크기 (terminal_scale=1 기준, w_kill=%.2f):" % a.w_kill)
    print("  " + "  ".join(f"{k}={v:g}" for k, v in term_mags.items()))
    print(f"  -> |TERMINAL| 의 최대값 = {max(term_mags.values()):g}\n")

    for mode in a.modes:
        res = [_episode(a.seed0, ep, a.w_kill, mode) for ep in range(a.episodes)]
        d = np.array([r[0] for r in res]); n = np.array([r[1] for r in res])
        labs = [r[2] for r in res]
        print(f"[{mode}]  라벨 {dict(Counter(labs))}")
        print(f"        길이 평균 {n.mean():.1f}   sum|dense| 평균 {d.mean():8.3f} "
              f"중앙 {np.median(d):8.3f}  범위 [{d.min():.3f}, {d.max():.3f}]")
        print(f"        스텝당 |dense| 평균 {(d/np.maximum(n,1)).mean():.4f}")
        ratio = d.mean() / max(max(term_mags.values()), 1e-9)
        print(f"        같은 자릿수 terminal_scale ~= {ratio:.1f} "
              f"-> 10 의 거듭제곱 {10 ** round(np.log10(max(ratio, 1e-9))):g}\n")


if __name__ == "__main__":
    main()
