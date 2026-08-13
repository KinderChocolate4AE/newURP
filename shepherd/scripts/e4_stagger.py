"""E4-1 — temporal stagger only (docs/83 §20 동결 프로토콜).

질문 (좁게)
-----------
  Does temporal staggering alone recover interception opportunity when spatial
  deployment, vehicle capability, attacker model, and pursuit geometry are held fixed?

지역수비 전체 구현이 **아니다**. 오직 `동시 4 대 추격 -> 시간층이 분리된 4 대 추격`.

개입 (§20.3)
-----------
  aim_i = p_att + v_att * max(0, t_lead + delta_i)     (t_lead = 기존 해석해)
  delta_i in { -D, -D/3, +D/3, +D },  D in {0, 0.125, 0.25} s

  ★ Amendment A: 음의 lead time 은 공격자의 **과거** 위치를 겨냥하게 되므로 0 clamp.
     arm 마다 clamp 비율(episode / limiter 수준)을 **반드시 보고**한다. 잦으면
     "대칭적 temporal staggering" 이 아니라 **horizon staggering with a zero lower
     bound** 로 표기한다.
  ★ Amendment B: delta 를 limiter ID 에 고정하면 **공간 역할까지 동시에 추가**되어
     temporal-only 실험이 아니게 된다. 24 개 permutation 을 episode index 로 순환하고
     (`PERMS[ep % 24]`), **같은 episode 에서 모든 D arm 이 동일 permutation** 을 쓴다.
     따라서 arm 사이에 변하는 것은 amplitude D 하나뿐이다.

Primary 는 **mechanism** (range(t_min)) 이지 HK 가 아니다 (§20.4) -- 실패 시
S1(구현 실패)과 S3(구현됐으나 무효)를 가르기 위함.

    python -m shepherd.scripts.e4_stagger --n 300 --out results/e4_stagger.json

torch-free.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
from typing import List

import numpy as np

from shepherd.scripts.dump_trajectory import _build_t1
from shepherd.scripts.mission_rollout import intercept_lead_time
from shepherd.scripts.recoverability_probe import _Driver
from shepherd.stats import wilson

__all__ = ["PERMS", "deltas_for", "episode_e4"]

R_CONTACT = 0.75
#: 24 개 permutation — 결과와 무관하게 사전 고정 (§20 Amendment B)
PERMS = list(itertools.permutations(range(4)))
assert len(PERMS) == 24


def deltas_for(ep: int, D: float, design: str = "sym") -> List[float]:
    """episode 별 balanced permutation 으로 timing slot 을 배정.

    design="sym"     : {-D, -D/3, +D/3, +D}          (E4-1, §20)
    design="diverse" : {0, D/3, 2D/3, D}             (E4-1b, §24 — clamp 구조적 불가)
    design="control" : {D/2, D/2, D/2, D/2}          (E4-1b matched mean)
    design="uniform" : {D, D, D, D}                  (E4-1c §26 — dispersion 구조적 0)
    """
    if design == "uniform":
        return [D] * 4
    if design == "control":
        return [D / 2.0] * 4
    base = ([0.0, D / 3.0, 2 * D / 3.0, D] if design == "diverse"
            else [-D, -D / 3.0, +D / 3.0, +D])
    perm = PERMS[ep % len(PERMS)]
    return [base[perm[i]] for i in range(4)]


def episode_e4(ep: int, D: float, design: str = "sym") -> dict:
    env, scn, lay = _build_t1(ep)
    d = _Driver(env, scn, lay, ep)
    se = d.se
    dt = float(env.dt)
    n_lim = len(env.limiter_ids)
    dl = deltas_for(ep, D, design)
    v_lim = float(env.backend.by_name(env.limiter_ids[0]).limits.v_max)

    # R4 (docs/83 §29): 근접거리는 _Driver 의 권위 측정(d.d_min/d.t_min)을 읽는다.
    # 자체 거리 루프 금지 -- 소진 limiter 주차 좌표를 잡아 접촉 스텝이 소실됐다.
    hk_step = None
    n_clamp = 0                      # limiter-step 단위 clamp 횟수
    n_steps_seen = 0
    for t in range(int(lay.episode_len)):
        lims, _, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        # clamp 진단 — 동일 helper 재사용 (로직 복제 아님)
        for i in range(n_lim):
            tl = intercept_lead_time(p_att - env._p(lims[i]), v_att, v_lim)
            base = tl if tl is not None else float(se.spec.tau_kill)
            if base + dl[i] < 0.0:
                n_clamp += 1
        n_steps_seen += n_lim

        fi = d.step(limiter_mode="intercept", baseline_commit=True,
                    limiter_kw={"lead_deltas": dl})
        if hk_step is None and bool(fi.get("hard_kill", False)):
            hk_step = t
        if d.done:
            break

    dmin, tmin = d.d_min, d.t_min          # R4 권위 측정
    tmin_s = tmin * dt
    return {"episode": ep, "D": D, "design": design, "label": d.label,
            "a_att": float(env.a_att_max), "att_speed": float(env.v_nominal),
            "deltas": [round(x, 4) for x in dl],
            "d_min": [round(float(x), 3) for x in dmin],
            "t_min": [round(float(x), 3) for x in tmin_s],
            "d_min_best": round(float(dmin.min()), 3),
            "range_t_min": round(float(tmin_s.max() - tmin_s.min()), 3),
            "std_t_min": round(float(np.std(tmin_s)), 3),
            "hk_step": hk_step,
            "n_committed": sum(1 for r in se.commits if r.source == "commit"),
            "n_clamp": n_clamp, "n_lim_steps": n_steps_seen,
            "clamp_frac": round(n_clamp / max(n_steps_seen, 1), 4)}


def main() -> None:
    ap = argparse.ArgumentParser(description="E4-1 temporal stagger (docs/83 §20)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--deltas", type=float, nargs="*", default=[0.0, 0.125, 0.25])
    ap.add_argument("--out", default="results/e4_stagger.json")
    a = ap.parse_args()
    print(f"[E4-1 · docs/83 §20] n={a.n} · D={a.deltas} · 세계 = E2-A 동일", flush=True)

    import time
    arms = {}
    for D in a.deltas:
        rows, t0 = [], time.time()
        for ep in range(a.n):
            rows.append(episode_e4(ep, D))
            if (ep + 1) % 50 == 0 or ep + 1 == a.n:
                el = time.time() - t0
                print(f"    [D={D:.3f}] {ep+1}/{a.n}  {el:6.1f}s "
                      f"(ETA {el/(ep+1)*(a.n-ep-1):5.0f}s)", flush=True)
        n = len(rows)
        rt = np.array([r["range_t_min"] for r in rows])
        hk = sum(1 for r in rows if r["label"] == "HARD_KILL")
        pen = sum(1 for r in rows if r["label"] == "PENETRATED")
        cap = sum(1 for r in rows if r["label"] in ("CAPTURED", "NET_CAPTURE",
                                                    "CAPTURE_WITH_CONTACT"))
        dbest = np.array([r["d_min_best"] for r in rows])
        reach = int((dbest <= R_CONTACT).sum())
        ep_clamp = sum(1 for r in rows if r["n_clamp"] > 0)
        arms[f"{D:.3f}"] = {
            "D": D, "n": n,
            "range_t_min_med": float(np.median(rt)),
            "range_t_min_p25": float(np.percentile(rt, 25)),
            "range_t_min_p75": float(np.percentile(rt, 75)),
            "p_hk": hk / n, "p_hk_wilson": list(wilson(hk, n)),
            "p_pen": pen / n, "p_net": cap / n,
            "p_reach": reach / n, "p_reach_wilson": list(wilson(reach, n)),
            "d_min_best_med": float(np.median(dbest)),
            # Amendment A 보고 의무
            "clamp_episode_frac": ep_clamp / n,
            "clamp_limiterstep_frac": float(np.mean([r["clamp_frac"] for r in rows])),
            "records": rows,
        }
        A = arms[f"{D:.3f}"]
        print(f"\n  D={D:.3f}  ★range(t_min) med {A['range_t_min_med']:.3f}s "
              f"[{A['range_t_min_p25']:.3f},{A['range_t_min_p75']:.3f}]")
        print(f"    HK {hk/n:.3f} {tuple(round(x,3) for x in A['p_hk_wilson'])} · "
              f"net {cap/n:.3f} · pen {pen/n:.3f} · "
              f"접촉권 {reach/n:.3f} · d_min med {A['d_min_best_med']:.3f}")
        print(f"    clamp: episode {A['clamp_episode_frac']:.3f} · "
              f"limiter-step {A['clamp_limiterstep_frac']:.4f}", flush=True)
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(
            json.dumps({"partial": True, "arms": arms}, ensure_ascii=False, indent=1),
            encoding="utf-8")

    # paired 비교 (baseline D=0 대비)
    base = arms.get("0.000")
    paired = {}
    if base is not None:
        b_rt = np.array([r["range_t_min"] for r in base["records"]])
        b_hk = np.array([1 if r["label"] == "HARD_KILL" else 0
                         for r in base["records"]])
        rng = np.random.default_rng(0)
        for k, A in arms.items():
            if k == "0.000":
                continue
            rt = np.array([r["range_t_min"] for r in A["records"]])
            hk = np.array([1 if r["label"] == "HARD_KILL" else 0 for r in A["records"]])
            idx = rng.integers(0, len(rt), size=(20000, len(rt)))
            d1 = rt - b_rt
            lo1, hi1 = np.percentile(np.median(d1[idx], axis=1), [2.5, 97.5])
            d2 = hk - b_hk
            lo2, hi2 = np.percentile((hk[idx] - b_hk[idx]).mean(1), [2.5, 97.5])
            paired[k] = {"d_range_t_min_med": float(np.median(d1)),
                         "d_range_t_min_ci95": [float(lo1), float(hi1)],
                         "d_p_hk": float(hk.mean() - b_hk.mean()),
                         "d_p_hk_ci95": [float(lo2), float(hi2)]}
            print(f"\n  paired D={k} vs 0: Δrange(t_min) med "
                  f"{np.median(d1):+.3f}s CI95 [{lo1:+.3f},{hi1:+.3f}] · "
                  f"ΔP_HK {hk.mean()-b_hk.mean():+.4f} CI95 [{lo2:+.4f},{hi2:+.4f}]",
                  flush=True)

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(
               stamp(artifact="e4_stagger"), prereg_doc="docs/83 §20 (E4-1)",
               intervention="aim_i = p_att + v_att*max(0, t_lead + delta_i)",
               deltas_rule="{-D,-D/3,+D/3,+D}, balanced permutation PERMS[ep%24]; "
                           "same permutation across D arms (Amendment B)",
               clamp_rule="max(0, t_lead+delta) (Amendment A); clamp fractions reported",
               primary="mechanism = range(t_min); HK is secondary (§20.4)",
               world="curve_sweep/E2-A 동일 (ratified + T1 + intercept + commit)",
               n=a.n, deltas=a.deltas, r_contact=R_CONTACT),
           "arms": arms, "paired_vs_baseline": paired}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")
    print(f"\n  -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
