"""Phase III 착수 1 — `v_shot` measure 검증 하네스 (docs/75 게이트 2·3).

    python -m shepherd.scripts.measure_harness --episodes 20 --out results/phase3/measure_harness.json
    python -m shepherd.scripts.measure_harness --episodes 3 --n-grid 2000 8000   # 빠른 스모크

무엇을 재는가 (docs/74 r3.2 §3.5)
---------------------------------
`v_shot` 은 **(R) robust coverage metric** — 공격자의 tau-reachable **path witness**
중 feasible 한 것에서 포획되는 가중 비율이다. 확률이 아니다. 이 값이 **표본 구성에
휘둘리면** 그 위에 세운 theta·라벨·지도·requirement 가 전부 sampling artifact 다.
그래서 지도 셀을 만들기 전에 두 게이트를 통과해야 한다:

  게이트 2 (수렴)      n = 2k -> 8k -> 32k 에서 8k->32k 변화가
                       **median <= 0.02 · 95% <= 0.05**. 초과 시 **지도 중단**.
  게이트 3 (allocation) witness family 구성비를 바꿨을 때 주요 score 변화가
                       **<= 0.05**. 초과 시 **현 R-map protocol 종료**
                       (P/set-based 는 Phase III-B 새 hash).

witness family (`build_reachable_union` 블록 순서 그대로)
  B1 single-segment 볼   크기 = `n`         (난수, seed 의존)
  B2 boundary sphere     크기 = |dirs|      (결정론 + n_dir)
  B3 bang-bang dogleg    크기 = f(|dirs|, n_segments)
  => allocation 조작 = `n` (랜덤 블록) 대 `n_dir`(결정론 블록) 의 비를 바꾸는 것.

추적 score (모두 같은 (e,t) 에서 paired)
  V_hold     limiter 가 실제 위치(무개입 standby)에 있을 때의 v_shot   = 지도의 V_0
  V_nolim    limiter 가 없을 때 (봉쇄 0) 의 v_shot
  V_probe    ★ **결정론적 probe 배치**(공격자 주변 고정 오프셋 N 개)에서의 v_shot.
             hold/nolim 만 보면 `n_t`(경로 서브스텝)·dogleg family 가 **봉쇄 판정에만**
             쓰이므로 아무것도 안 막는 상태에서 변이가 공허하게 0 이 된다 —
             지도가 실제로 쓰는 것은 "구가 막는" 영역이므로 거기서 검증해야 한다.
             (2026-08-09 1 차 실행에서 seg_1·substep_2x 가 정확히 0.0000 으로 나온
              원인이 이것이었다. probe 는 지도 셀이 아니라 measure 검증용 고정 배치다.)
  g_hold     clean-fire 판정 1[V_hold >= theta AND not boxed]  -> **결정 뒤집힘률**
             (지도가 실제로 쓰는 것은 실수값이 아니라 이 이진 판정이다)

통계 단위 = **episode** (path witness 를 독립표본으로 bootstrap 하지 않는다).
에피소드마다 |delta| 를 평균한 뒤 그 분포의 median/95% 를 본다.

★ 산출물은 `pivot_manifest.stamp()` 로 provenance 를 싣는다 (스탬프 없으면 무효).
torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.game import viability as V
from shepherd.m4_env import build_m4_env
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

__all__ = ["N_GRID", "ALLOC_VARIANTS", "GATE2", "GATE3", "collect_states",
           "scores_at", "run_harness"]

# ── 사전 선언 (결과 보기 전 고정) ────────────────────────────────────────────
N_GRID = (2000, 8000, 32000)          # 게이트 2 수렴 축 (B1 블록 크기)
N_DIR_DEFAULT = 32
STATE_STRIDE = 25                     # 하네스 전용 상태 표집 (지도의 T_eval 아님)
THETA = 0.90                          # theta_S2 (docs/74 §4.1) — 결정 뒤집힘 판정용
GATE2 = {"median": 0.02, "p95": 0.05}         # 8k -> 32k 허용 변화
GATE3 = {"max_shift": 0.05}                   # allocation 변경 허용 변화

# ★ informative subset (결과 보기 전 선언). 접근 초반의 원거리 상태는 어떤 설정에서도
#   v_shot 이 정확히 0 이라 자명하게 일치한다 -- 그런 상태를 통계에 넣으면 게이트가
#   **공짜로 통과**한다(위험한 방향). 그래서 판정은 "metric 이 실제로 정보를 갖는"
#   상태에서 한다: 어떤 설정에서든 0 < v < 1 인 상태.
#   전체 상태 통계도 함께 보고한다 (숨기지 않는다).
INFORMATIVE_EPS = 1e-9

# allocation 변이: 랜덤 블록(n) 대 결정론 블록(n_dir) 의 비를 흔든다.
# 기준(base)은 n = 8000, n_dir = 32. 변이는 **같은 (e,t)** 에서 paired 로 비교한다.
ALLOC_VARIANTS = {
    "base":        dict(n=8000, n_dir=32, n_segments=4, n_t=24),
    "dirs_half":   dict(n=8000, n_dir=16, n_segments=4, n_t=24),
    "dirs_double": dict(n=8000, n_dir=64, n_segments=4, n_t=24),
    "seg_1":       dict(n=8000, n_dir=32, n_segments=1, n_t=24),   # dogleg 블록 제거
    "substep_2x":  dict(n=8000, n_dir=32, n_segments=4, n_t=48),   # 경로 이산화
    "seed_shift":  dict(n=8000, n_dir=32, n_segments=4, n_t=24, seed_off=101),
}


# probe 배치 (결정론·선언) — **부분 봉쇄**가 목표다.
#   시도 1) 공격자 중심 정사면체(1.2*rho): 진행방향과 어긋나 경로 튜브를 못 지남
#           -> blocked 0% (변이가 공허해짐)
#   시도 2) 공칭 경로 위 정확히: 전부 막아 boxed_in -> v_shot 1.0 인공값
#   채택)   공칭 경로에서 **옆으로 1.2*r_kill** 띄운 4 점 -> blocked 평균 0.59,
#           테스트 상태 100% 가 partial(0.02~0.98). 두 집합(caught/uncaught) 모두 비자명.
PROBE_FRACS = (0.6, 1.0)                 # tau 대비 시각 분할
PROBE_LATERAL_OVER_RKILL = 1.2


def _frame(v):
    """진행방향 e 와 그에 수직인 단위벡터 하나."""
    v = np.asarray(v, float)
    n = float(np.linalg.norm(v))
    e = v / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])
    a = np.array([0.0, 0.0, 1.0]) if abs(e[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    p1 = np.cross(e, a)
    return e, p1 / np.linalg.norm(p1)


def probe_placement(base, s, k: int = 4):
    """공칭 경로 옆 `1.2*r_kill` 의 4 점 (부분 봉쇄). 지도 셀이 아니라 measure 검증용."""
    _, p1 = _frame(s["v_att"])
    off = PROBE_LATERAL_OVER_RKILL * float(base.kill_radius)
    tau = float(base.tau_deploy)
    pts = [s["p_att"] + s["v_att"] * (tau * f) + off * d
           for f in PROBE_FRACS for d in (p1, -p1)]
    return pts[:k]


def _world_kw() -> dict:
    """하네스 상태 풀의 세계 = **계약 세계** (v3 TRAIN layer draw).

    레거시 점 스펙(episode_len 160)이 아니라 Phase I 이 실제로 돈 세계에서 measure 를
    검증한다 -- 쓰지 않는 세계에서 수렴을 보이는 것은 의미가 없다. IID 대역은
    건드리지 않는다 (train 대역만).
    """
    return dict(system=ratified_system(),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                threat_layer="train")


def collect_states(episodes, stride: int = STATE_STRIDE, max_steps: int = 1200,
                   log=None):
    """reference controller(hold)로 굴려 (episode, t, 상태) 를 stride 로 모은다.

    finisher 는 스크립트로 **조준**하되 발사는 안 한다 (cone judge 가 자세에 의존).
    """
    out = []
    for ep in episodes:
        st = build_m4_env(0, ep, **_world_kw())
        env, base = st.env, _base_env(st.env)
        env.reset(seed=ep)
        for t in range(max_steps):
            lims, fin, att = base._states()
            if t % stride == 0:
                out.append(dict(ep=int(ep), t=int(t),
                                p_att=base._p(att).copy(), v_att=base._v(att).copy(),
                                fin=np.asarray(fin, float).copy(),
                                lim=[base._p(s).copy() for s in lims]))
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        if log:
            log(f"  ep{ep}: {sum(1 for s in out if s['ep'] == ep)} states", flush=True)
    return out


def scores_at(base, s, *, n, n_dir, n_segments, n_t, seed_off=0) -> dict:
    """한 (e,t) 에서 V_hold / V_nolim / g_hold + family 구성비."""
    kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
    union = V.build_reachable_union(
        s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
        n=int(n), n_segments=int(n_segments), n_dir=int(n_dir), n_t=int(n_t),
        seed=int(s["t"]) + int(seed_off), **kw)
    r_hold = V.eval_union_with_limiters(union, s["lim"], base.kill_radius)
    r_free = V.eval_union_with_limiters(union, [], base.kill_radius)
    r_prb = V.eval_union_with_limiters(union, probe_placement(base, s),
                                       base.kill_radius)
    boxed = bool(getattr(r_hold, "boxed_in", False)) or r_hold.n_feasible == 0
    boxed_p = bool(getattr(r_prb, "boxed_in", False)) or r_prb.n_feasible == 0
    return dict(
        V_hold=float(r_hold.v_shot_soft), V_nolim=float(r_free.v_shot_soft),
        V_probe=float(r_prb.v_shot_soft),
        blocked_frac_probe=float(1.0 - r_prb.n_feasible / max(union.n_total, 1)),
        g_hold=int((r_hold.v_shot_soft >= THETA) and not boxed),
        g_probe=int((r_prb.v_shot_soft >= THETA) and not boxed_p),
        n_total=int(union.n_total), block_sizes=list(union.block_sizes))


def _informative(rows) -> bool:
    """0 < v < 1 인 값이 하나라도 있으면 informative (선언된 규칙)."""
    for r in rows:
        for f in ("V_hold", "V_nolim", "V_probe"):
            v = r[f]
            if INFORMATIVE_EPS < v < 1.0 - INFORMATIVE_EPS:
                return True
    return False


def _per_episode(diffs: dict) -> dict:
    """episode 단위 집계 (위트니스·상태를 독립표본으로 취급하지 않는다)."""
    per_ep = np.array([np.mean(v) for v in diffs.values()], float)
    return {"n_episodes": int(len(per_ep)),
            "median": float(np.median(per_ep)),
            "p95": float(np.percentile(per_ep, 95)),
            "max": float(per_ep.max()) if len(per_ep) else float("nan")}


def run_harness(episodes, *, n_grid=N_GRID, stride=STATE_STRIDE, log=print) -> dict:
    states = collect_states(episodes, stride=stride, log=log)
    base = _base_env(build_m4_env(0, int(episodes[0]), **_world_kw()).env)
    if log:
        log(f"states = {len(states)} (episodes {len(episodes)}, stride {stride})")

    # ── 게이트 2: n 수렴 ─────────────────────────────────────────────────────
    vals = {n: [] for n in n_grid}
    for i, s in enumerate(states):
        for n in n_grid:
            vals[n].append(scores_at(base, s, n=n, n_dir=N_DIR_DEFAULT,
                                     n_segments=4, n_t=24))
        if log and (i + 1) % 10 == 0:
            log(f"  convergence {i+1}/{len(states)}", flush=True)

    # informative 판정 (선언된 규칙) -- 게이트는 이 부분집합에서, 전체도 병기
    info = [ _informative([vals[n][k] for n in n_grid]) for k in range(len(states)) ]
    idx_info = [k for k, ok in enumerate(info) if ok]
    if log:
        log(f"informative states = {len(idx_info)}/{len(states)} "
            f"({len(idx_info)/max(len(states),1):.1%})")

    def diff_by_ep(a_key, b_key, field, only=None):
        d: dict = {}
        for k, s in enumerate(states):
            if only is not None and k not in only:
                continue
            d.setdefault(s["ep"], []).append(
                abs(vals[a_key][k][field] - vals[b_key][k][field]))
        return d

    conv, conv_all = {}, {}
    hi, mid = n_grid[-1], n_grid[-2] if len(n_grid) >= 2 else n_grid[-1]
    lo = n_grid[0]
    S = set(idx_info)
    for field in ("V_hold", "V_nolim", "V_probe"):
        conv[f"{field}|{mid}->{hi}"] = _per_episode(diff_by_ep(mid, hi, field, S))
        conv[f"{field}|{lo}->{mid}"] = _per_episode(diff_by_ep(lo, mid, field, S))
        conv_all[f"{field}|{mid}->{hi}"] = _per_episode(diff_by_ep(mid, hi, field))
    flips = sum(vals[mid][k]["g_hold"] != vals[hi][k]["g_hold"] for k in idx_info)
    conv["g_flip_rate|%d->%d" % (mid, hi)] = flips / max(len(idx_info), 1)
    # 판정은 V_hold 와 **V_probe 둘 다** 통과해야 한다 (봉쇄 비활성/활성 양쪽)
    g2 = conv.get(f"V_hold|{mid}->{hi}", {})
    g2p = conv.get(f"V_probe|{mid}->{hi}", {})
    gate2_pass = bool(g2 and g2p
                      and max(g2["median"], g2p["median"]) <= GATE2["median"]
                      and max(g2["p95"], g2p["p95"]) <= GATE2["p95"])

    # ── 게이트 3: allocation 민감도 ──────────────────────────────────────────
    alloc = {}
    base_scores = None
    for name, cfg in ALLOC_VARIANTS.items():
        sc = [scores_at(base, s, **cfg) for s in states]
        if name == "base":
            base_scores = sc
            alloc[name] = {"family_shares": _shares(sc[0]), "shift": None}
            continue
        d, dp = {}, {}
        for k in idx_info:                    # informative 부분집합에서 판정
            d.setdefault(states[k]["ep"], []).append(
                abs(sc[k]["V_hold"] - base_scores[k]["V_hold"]))
            dp.setdefault(states[k]["ep"], []).append(
                abs(sc[k]["V_probe"] - base_scores[k]["V_probe"]))
        flip = sum(sc[k]["g_hold"] != base_scores[k]["g_hold"] for k in idx_info)
        flip_p = sum(sc[k]["g_probe"] != base_scores[k]["g_probe"] for k in idx_info)
        alloc[name] = {"family_shares": _shares(sc[0]),
                       "shift_V_hold": _per_episode(d),
                       "shift_V_probe": _per_episode(dp),     # ★ 봉쇄 활성 영역
                       "g_flip_rate": flip / max(len(idx_info), 1),
                       "g_probe_flip_rate": flip_p / max(len(idx_info), 1)}
        if log:
            a_ = alloc[name]
            log(f"  alloc {name}: hold p95 {a_['shift_V_hold']['p95']:.4f} · "
                f"probe p95 {a_['shift_V_probe']['p95']:.4f} · "
                f"flip {a_['g_flip_rate']:.3f}/{a_['g_probe_flip_rate']:.3f}", flush=True)
    worst = max((max(v["shift_V_hold"]["p95"], v["shift_V_probe"]["p95"])
                 for k, v in alloc.items() if k != "base"), default=float("nan"))
    gate3_pass = bool(worst <= GATE3["max_shift"])

    return dict(
        contract_doc="docs/74 r3.2 §3.5 · docs/75 게이트 2·3 (measure validation)",
        measure_interpretation="(R) robust coverage metric over path witnesses -- not a probability",
        theta=THETA, n_grid=list(n_grid), state_stride=stride,
        episodes=[int(e) for e in episodes], n_states=len(states),
        n_informative=len(idx_info),
        informative_rule="0 < v_shot < 1 in any n-setting (declared before running)",
        gate2={"criterion": GATE2, "result": conv,
               "result_all_states": conv_all, "pass": gate2_pass},
        gate3={"criterion": GATE3, "variants": alloc, "worst_p95": worst,
               "pass": gate3_pass},
        verdict=("PASS -- 지도 생성 가능" if (gate2_pass and gate3_pass) else
                 "FAIL -- 지도 중단 (docs/74 §5-4 / docs/75 게이트 2·3)"),
        **stamp(artifact="phase3_measure_harness"))


def _shares(sc: dict) -> dict:
    bs = sc["block_sizes"]
    tot = max(sum(bs), 1)
    names = ["B1_ball", "B2_boundary", "B3_dogleg", "B4_turn"][:len(bs)]
    return {n: {"n": int(b), "share": round(b / tot, 4)} for n, b in zip(names, bs)}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Phase III measure 검증 하네스")
    ap.add_argument("--episodes", type=int, default=20, help="reference 에피소드 수")
    ap.add_argument("--ep0", type=int, default=0)
    ap.add_argument("--stride", type=int, default=STATE_STRIDE)
    ap.add_argument("--n-grid", type=int, nargs="*", default=list(N_GRID))
    ap.add_argument("--out", default="results/phase3/measure_harness.json")
    a = ap.parse_args(argv)

    out = run_harness(range(a.ep0, a.ep0 + a.episodes), n_grid=tuple(a.n_grid),
                      stride=a.stride)
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    g2 = out["gate2"]["result"]
    key = [k for k in g2 if k.startswith("V_hold|") and "->" in k][0]
    print(f"\n[게이트 2] {key}: median {g2[key]['median']:.4f} · p95 {g2[key]['p95']:.4f} "
          f"-> {'PASS' if out['gate2']['pass'] else 'FAIL'}")
    gp = out["gate2"]["result"].get(f"V_probe|8000->32000")
    if gp:
        print(f"[게이트 2] V_probe (봉쇄 활성): median {gp['median']:.4f} · p95 {gp['p95']:.4f}")
    print(f"[게이트 3] worst p95 shift (hold·probe 중 최대) {out['gate3']['worst_p95']:.4f} "
          f"-> {'PASS' if out['gate3']['pass'] else 'FAIL'}")
    print(out["verdict"])
    print(f"-> {p}")


if __name__ == "__main__":
    main()
