"""(A) 학습 신호 regime 분해 — **SHAPING_NEEDED 에 gradient 가 존재하는가.**

WHY
---
`results/hold_baseline.json` (n=500): 무개입은 SHAPING_NEEDED 에서 **0/297**.
그 영역에서 학습 중에도 성공이 안 나오면 종말항은 항상 `-c_pen` 로 **상수**이고,
그러면 그 영역의 행동을 구분하는 gradient 가 존재하지 않는다. 남는 신호는 조밀항
하나뿐인데, [E] 스케일 스모크(docs/41)에서 `sum|dense|` **중앙값이 0.0** 이었다.

둘 다 참이면 정책은 SHAPING_NEEDED 에서 학습할 수 없고, 스윕은 "협력 순이득 없음"
을 돌려주되 그 이유가 *"협력이 불가능해서"* 가 아니라 *"크레딧 할당이 안 돼서"* 가
된다. **그런 부정 결과는 방어할 수 없다** -- "학습이 실패한 것이지 협력이 실패한
것이 아니다" 라는 반론에 답할 수 없기 때문이다.

그래서 스윕을 걸기 전에 잰다. **재는 것은 크기가 아니라 변동이다** -- 스텝마다
같은 값이 붙는 항은 정보가 0 이고 어드밴티지에서 상쇄된다. (첫 시도에서 실제로
`|보상|` 중앙값 1.6 이 나왔는데, 그건 `-c_lim * n_consumed` 상수였다.)

    J_env  (dv_shot + clean - waste - contact)  = **상태의존 조밀항**
           -> RewardSpec(enabled=False) 의 rew 가 정확히 이것이다
    M4 가 더하는 것: terminal (라벨 의존) + (-c_lim * n_consumed)  <- 후자는 상수

    핵심 통계 = **regime 안에서 에피소드 수익(return)이 갈라지는가**
                SHAPING_NEEDED 는 라벨이 전부 PENETRATED 이므로 종말항이 상수다.
                그러면 변동은 sum(J_env) 하나에서만 나온다.

**모델·운용점·보상을 바꾸지 않는다.** 계측 전용.

    python -m shepherd.scripts.signal_audit [--episodes 40] [--policy random]

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

__all__ = ["audit_signal", "summarize_signal"]

_SUCCESS = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL")


def _rand_actions(env, rng):
    """무작위 정책 -- 학습 초기의 탐색 분포를 근사한다."""
    acts = {}
    for a in env.agents:
        sp = env.action_space(a)
        lo = np.asarray(getattr(sp, "low", -np.ones(sp.shape)), np.float32)
        hi = np.asarray(getattr(sp, "high", np.ones(sp.shape)), np.float32)
        acts[a] = rng.uniform(lo, hi).astype(np.float32)
    return acts


def audit_signal(seed0: int, episodes: int, *, policy: str = "random",
                 limiter_mode: str = "hold") -> dict:
    """스텝별 조밀항 · 에피소드별 종말 라벨을 regime 별로 모은다."""
    from shepherd.agents.baselines import scripted_finisher
    from shepherd.scripts.mission_rollout import _limiter_actions, _zero_commit

    # ★ enabled=False 로 재야 `rew` 가 **순수 J_env** 다. M4 가 얹는 항(종말·소모)은
    #   라벨/상수이므로 아래에서 해석적으로 더한다. P40d 가 라벨 불변을 강제한다.
    system, reward = SystemSpec(), RewardSpec(w_kill=0.5, enabled=False)
    rs_declared = RewardSpec(w_kill=0.5, enabled=True)
    spec = AttackerSpec(level="A2", jink_amp=0.6, seed=0)
    spawn = SpawnSpec()
    rows, eps = [], []

    for ep in range(episodes):
        st = build_m4_env(seed0, ep, system=system, reward=reward,
                          attacker=spec, spawn=spawn)
        env, scn, lay = st.env, st.scn, st.lay
        reg = regime_of(st.threat["a_att"], st.threat["tau"], st.threat["net_radius"])
        rng = np.random.default_rng(seed0 * 7919 + ep)
        env.reset(seed=seed0 + ep)

        dense_sum, label, steps, n_consumed = [], None, 0, 0
        for t in range(int(lay.episode_len)):
            lims, fin, att = env._states()
            if policy == "random":
                acts = _rand_actions(env, rng)
            else:
                acts = _limiter_actions(env, scn, lay, limiter_mode, lims,
                                        env._p(att), env._v(att))
                _zero_commit(acts)
                acts[env.finisher_id] = scripted_finisher(
                    env._p(fin), env._p(att), env._v(att),
                    tau=env.tau_deploy, clean_threshold_crossed=False)
            acts[env.adversary_id] = np.zeros(3, np.float32)
            _, rew, term, trunc, info = env.step(acts)
            steps += 1

            # limiter 들의 조밀항 (종말 보너스가 붙기 전 크기를 보려면 마지막 스텝 제외)
            fi = info[env.finisher_id]
            done = (bool(term[env.finisher_id]) if term else False) or \
                   (bool(trunc[env.finisher_id]) if trunc else False)
            v = float(np.sum([float(rew[a]) for a in env.limiter_ids]))   # = sum_i J_env_i
            dense_sum.append(v)
            rows.append({"regime": reg, "t": t, "j_env": v})
            n_consumed = int(fi.get("n_retired", n_consumed) or n_consumed)
            if done:
                label = fi.get("m4_outcome")
                if label is None:                       # enabled=False -> 직접 판정
                    label = ("HARD_KILL" if fi.get("hard_kill") else
                             "NET_CAPTURE" if fi.get("captured") else
                             "PENETRATED" if fi.get("penetrated") else "SPENT_FAIL")
                break
        term = rs_declared.terminal_scale * rs_declared.terminal(label) if label else 0.0
        arr = np.asarray(dense_sum, float)
        eps.append({"regime": reg, "label": label, "steps": steps,
                    "j_env_sum": float(arr.sum()),
                    "j_env_nonzero_steps": int((np.abs(arr) > 1e-9).sum()),
                    "j_env_steps": int(arr.size),
                    "terminal": float(term) * len(env.limiter_ids),
                    "const_lim": -rs_declared.c_lim * n_consumed * len(env.limiter_ids),
                    "return": float(arr.sum()) + float(term) * len(env.limiter_ids)})
    return {"rows": rows, "episodes": eps, "policy": policy, "n": episodes}


def summarize_signal(a: dict) -> dict:
    out = {"policy": a["policy"], "episodes": a["n"]}
    rs = RewardSpec(w_kill=0.5, enabled=True)
    out["_reward"] = {"dense_scale": rs.dense_scale, "terminal_scale": rs.terminal_scale,
                      "terminal_success": rs.terminal("NET_CAPTURE"),
                      "terminal_penetrated": rs.terminal("PENETRATED")}
    for reg in sorted({e["regime"] for e in a["episodes"]}):
        E = [e for e in a["episodes"] if e["regime"] == reg]
        R = np.array([r["j_env"] for r in a["rows"] if r["regime"] == reg])
        n_steps = int(R.size)
        succ = sum(1 for e in E if e["label"] in _SUCCESS)
        labels = {}
        for e in E:
            labels[e["label"] or "TRUNCATED"] = labels.get(e["label"] or "TRUNCATED", 0) + 1
        out[reg] = {
            "episodes": len(E),
            "success_episodes": succ,
            "labels": labels,
            "j_env_steps": n_steps,
            "j_env_nonzero_frac": float((np.abs(R) > 1e-9).mean()) if n_steps else 0.0,
            "j_env_abs_median": float(np.median(np.abs(R))) if n_steps else 0.0,
            "j_env_abs_p99": float(np.percentile(np.abs(R), 99)) if n_steps else 0.0,
            "j_env_abs_max": float(np.abs(R).max()) if n_steps else 0.0,
            "j_env_sum_per_ep_median": float(np.median([e["j_env_sum"] for e in E])),
            # ★ 핵심: regime 안에서 에피소드 수익이 갈라지는가
            "return_mean": float(np.mean([e["return"] for e in E])),
            "return_std": float(np.std([e["return"] for e in E])),
            "return_min": float(np.min([e["return"] for e in E])),
            "return_max": float(np.max([e["return"] for e in E])),
            "terminal_magnitude": float(np.mean([abs(e["terminal"]) for e in E])),
        }
        # ★ 판정: 이 regime 에 **행동을 구분하는** 신호가 있는가.
        #   종말 라벨이 갈리거나, 아니면 수익 변동이 종말항 크기의 1% 이상이어야 한다.
        term_varies = 0 < succ < len(E)
        rel = (out[reg]["return_std"] / out[reg]["terminal_magnitude"]
               if out[reg]["terminal_magnitude"] > 0 else 0.0)
        out[reg]["return_std_over_terminal"] = float(rel)
        out[reg]["dense_informative"] = bool(rel > 0.01)
        out[reg]["terminal_varies"] = bool(term_varies)
        out[reg]["has_gradient"] = bool(term_varies or out[reg]["dense_informative"])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="학습 신호 regime 분해 (모델 변경 없음)")
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--policy", default="random", choices=("random", "scripted"))
    ap.add_argument("--limiter-mode", default="hold")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    cfg = m4_config()
    res = audit_signal(a.seed, a.episodes, policy=a.policy, limiter_mode=a.limiter_mode)
    s = summarize_signal(res)
    s["_declared"] = {"tau_deploy": cfg["physics"]["tau_deploy"],
                      "net_radius": cfg["physics"]["net_radius"]}
    print(json.dumps(s, indent=2, ensure_ascii=False))
    for reg in ("SHAPING_NEEDED", "FREE_CAPTURE"):
        if reg in s:
            v = s[reg]
            verdict = "신호 있음" if v["has_gradient"] else "★ 신호 없음 -- 학습 불가"
            print(f"\n>> {reg:16s} 종말 변동 {v['terminal_varies']}  "
                  f"수익 {v['return_mean']:.4f} +- {v['return_std']:.4f}  "
                  f"(종말항 대비 {100*v['return_std_over_terminal']:.2f}%)  -> {verdict}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    return s


if __name__ == "__main__":
    main()
