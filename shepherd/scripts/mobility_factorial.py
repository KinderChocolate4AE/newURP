"""포획기 이동성 요인 실험 — 실행·집계 (docs/51).

묻는 것 (docs/51 §0)
--------------------
docs/48 §12 의 인과 사슬(조준 결손 -> 발사 기회 상실 -> 하드킬 도피)이
**설계 산물일 위험**을 잰다. 포획기가 고정이라 조준 오차를 병진으로 흡수할
자유도가 없고, 그래서 작은 각오차가 곧바로 임무 실패로 증폭된다.

    ★ 1차   해석적 조준에서, 이동이 SHAPING 구간 포획률을 올리는가 (셀3 − 셀1)

학습 조준 칸(셀 2·4)은 **1차가 아니다** -- 정책이 `p_fin` 상수인 관측에서
학습했으므로 포획기가 움직이면 분포 밖이다 (docs/51 §3.2).

읽는 법 (docs/51 §3.3, 비대칭)
-----------------------------
    셀3 > 셀1   강하다 -- 최적도 아닌 제어기로도 나왔다
    셀3 ≈ 셀1   약하다 -- "이동 이득의 하한이 0 근처" 로만 적는다

paired CRN: 두 셀이 같은 `(seed0, ep)` 로 env 를 만들고 같은 시드로 굴린다.
`mission_eval(mobility=...)` 인자 하나만 다르다.

사용
----
    python -m shepherd.scripts.mobility_factorial --n 500
    python -m shepherd.scripts.mobility_factorial --n 500 --out results/mobility.json

torch 를 쓰지 않는다 (해석적 셀만 돌린다).
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List, Optional

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.agents.mobile_finisher import (MOBILE_A_MAX, SLEW_UNLIMITED,
                                            apply_mobility)
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_env import build_m4_env, mission_eval
from shepherd.spawn_rand import SpawnSpec
from shepherd.stats import wilson

__all__ = ["run_cell", "paired_compare", "travel_stats", "SHAPE", "SUCCESS"]

SHAPE = "SHAPING_NEEDED"
#   ★ **비손실 포획** 라벨 (docs/51 §3.1 의 1차 지표). `HARD_KILL` 은 무력화지만
#   비손실이 아니므로 **뺀다** -- 논문의 스파인이 비손실이다.
#   2026-08-05: 처음에 여기에 없는 이름("CAPTURED","NEUTRALIZED")을 적어 두는
#   바람에 모든 칸이 0 으로 나왔다. 라벨을 상수로 적는 순간 오타가 조용한 0 이
#   되므로, 아래 `_check_labels` 가 실제 LABELS 와 대조한다.
SUCCESS = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
DESTRUCTIVE = ("HARD_KILL",)


def _check_labels() -> None:
    from shepherd.scripts.mission_rollout import LABELS
    unknown = (set(SUCCESS) | set(DESTRUCTIVE)) - set(LABELS)
    if unknown:
        raise ValueError(f"LABELS 에 없는 이름: {sorted(unknown)} (실제 {LABELS})")


def _kw(attacker: Optional[AttackerSpec] = None) -> dict:
    # docs/65 A2 — 비준 계약으로 파생. docs/51 의 factorial 결과는 legacy
    # 구계약 실측 (재실행 수치와 병치 시 한정 병기).
    #
    # attacker=None 이면 T0 (route_gain 0 · sense_range inf) — docs/51 결과와
    # bit-exact. docs/83 E1 은 T1 (route_gain 0.5 · sense_range 30.0) 을
    # 명시적으로 넘겨서 돈다 (curve_sweep.py:144-152 와 같은 규율).
    return dict(system=ratified_system(),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=attacker or AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def run_cell(n: int, seed0: int = 0, *, mobility: float = 0.0,
             omega_max: Optional[float] = None,
             limiter_mode: str = "hold",
             attacker: Optional[AttackerSpec] = None) -> dict:
    """한 칸. `mobility=0, omega_max=None, attacker=None` 이면 기존 기저선과
    bit-identical (P72)."""
    _check_labels()
    recs: List[dict] = []
    r = mission_eval(seed0, n, limiter_mode=limiter_mode, records=recs,
                     mobility=mobility, omega_max=omega_max, **_kw(attacker))
    # ★ 자기 점검: 라벨로 센 성공 수가 요약 통계와 맞는가. 안 맞으면 라벨
    #   집합이 틀린 것이고, 그건 조용한 0 으로 나타난다 (2026-08-05 실제 사고).
    k_lab = sum(1 for d in recs if d["label"] in SUCCESS)
    k_sum = int(round(r["neutralized_rate"] * n * r["nondestructive_frac"]))
    if abs(k_lab - k_sum) > 1:
        raise ValueError(f"라벨 집계 불일치: SUCCESS 로 {k_lab}, 요약으로 {k_sum}. "
                         f"SUCCESS={SUCCESS} 가 틀렸을 가능성이 높다")
    return {"mobility": float(mobility), "omega_max": omega_max,
            "limiter_mode": limiter_mode,
            "n": n, "seed0": seed0, "summary": r, "records": recs,
            "k_nondestructive": k_lab}


# ── paired 분석 ─────────────────────────────────────────────────────────────
def _succ_by_ep(cell: dict, regime: Optional[str] = None) -> Dict[int, int]:
    return {int(d["episode"]): int(d["label"] in SUCCESS)
            for d in cell["records"] if regime is None or d["regime"] == regime}


def paired_compare(fixed: dict, mobile: dict, regime: Optional[str] = SHAPE,
                   boot: int = 20000, seed: int = 0) -> dict:
    """짝지어진 차이. 에피소드가 **같은 초기조건**이므로 짝을 지을 수 있다.

    풀링 Wilson 을 차이에 그대로 쓰지 않는다 -- 두 표본이 독립이 아니다.
    부트스트랩은 에피소드 단위로 **쌍을 통째로** 재표집한다.
    """
    a, b = _succ_by_ep(fixed, regime), _succ_by_ep(mobile, regime)
    eps = sorted(set(a) & set(b))
    if not eps:
        raise ValueError(f"짝지을 에피소드가 없다 (regime={regime})")
    x = np.array([a[e] for e in eps], int)
    y = np.array([b[e] for e in eps], int)
    # McNemar 칸: 이동이 구제한 판 / 이동이 망친 판
    n01 = int(np.sum((x == 0) & (y == 1)))      # 고정 실패 -> 이동 성공  = R_move
    n10 = int(np.sum((x == 1) & (y == 0)))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(eps), size=(boot, len(eps)))
    d = (y[idx].mean(1) - x[idx].mean(1))
    lo, hi = np.percentile(d, [2.5, 97.5])
    kx, ky = int(x.sum()), int(y.sum())
    return {"regime": regime or "ALL", "n_paired": len(eps),
            "fixed_k": kx, "fixed_rate": kx / len(eps),
            "fixed_wilson": wilson(kx, len(eps)),
            "mobile_k": ky, "mobile_rate": ky / len(eps),
            "mobile_wilson": wilson(ky, len(eps)),
            "diff": ky / len(eps) - kx / len(eps),
            "diff_ci95": [float(lo), float(hi)],
            "rescued_n01": n01, "broken_n10": n10,
            "R_move": n01 / len(eps),
            # ★ docs/51 §3.1 통과선: paired 차이의 95 % 하한 > 0
            "passes": bool(lo > 0.0)}


def travel_stats(n: int = 50, seed0: int = 0,
                 mobility: float = MOBILE_A_MAX) -> dict:
    """포획기 이동거리 (docs/51 §2.1 -- 목줄이 없으므로 **반드시 보고**한다).

    포획기가 편대 없이 혼자 요격해 버리는 체제면 그건 "이동이 성형 문제를
    무의미하게 만든다" 는 별개의 발견이고, 이동거리로만 드러난다.
    """
    from shepherd.scripts.mission_rollout import scripted_role_actions

    tot, mx = [], []
    for ep in range(n):
        st = build_m4_env(seed0, ep, **_kw())
        env, scn, lay = st.env, st.scn, st.lay
        if mobility > 0.0:
            apply_mobility(env, a_max=mobility)
        env.reset(seed=seed0 + ep)
        fid = env.finisher_id
        p0 = env._p(env._states()[1]).copy()
        prev, d = p0.copy(), 0.0
        for _ in range(int(lay.episode_len)):
            acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                         fire_mode="clean")
            acts[env.adversary_id] = np.zeros(3, np.float32)
            _, _, term, trunc, _ = env.step(acts)
            p = env._p(env._states()[1])
            d += float(np.linalg.norm(p - prev))
            prev = p.copy()
            if (term and term.get(fid)) or (trunc and trunc.get(fid)):
                break
        tot.append(d)
        mx.append(float(np.linalg.norm(prev - p0)))
    return {"n": n, "path_len_mean": float(np.mean(tot)),
            "path_len_p90": float(np.percentile(tot, 90)),
            "net_displacement_mean": float(np.mean(mx)),
            "net_displacement_max": float(np.max(mx))}


# ── docs/83 E1 — T1 주입 + 필수 manifest ────────────────────────────────────
#: docs/83 을 동결한 커밋. 결과가 사전등록보다 앞서 보이지 않도록 아티팩트에 싣는다.
PREREG_COMMIT = "eea71806828fed02e9670e4fcab2c8d0099c906f"


def _threat_class(args) -> str:
    """docs/80 명명. route_gain>0 이면 T1(reactive-local), 아니면 T0."""
    return "T1" if float(args.route_gain) > 0.0 else "T0"


def _attacker_from_args(args) -> AttackerSpec:
    return AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                        route_gain=float(args.route_gain),
                        sense_range=float(args.sense_range))


def _manifest(args) -> dict:
    """docs/83 freeze stamp 가 의무화한 필드. 파일명·노트가 아니라 **아티팩트
    자체**로 세계를 재구성할 수 있어야 한다 (수치감사 §G-② 재발 방지)."""
    from shepherd.m4_config import m4_config
    from shepherd.scripts.pivot_manifest import stamp

    cfg = m4_config()
    ph, cone = cfg["physics"], cfg["viability"]["cone"]
    sysspec = ratified_system()
    return dict(
        stamp(artifact="docs83_E1_slew_counterfactual"),
        prereg_commit=PREREG_COMMIT,
        prereg_doc="docs/83_aiming_attribution_correction_prereg.md §4 (E1)",
        threat_class=_threat_class(args),
        attacker=dict(level="A2", jink_amp=0.6, seed=0,
                      route_gain=float(args.route_gain),
                      sense_range=float(args.sense_range)),
        limiter_mode="hold",
        contract=dict(enabled=sysspec.enabled,
                      contact_resolver=sysspec.contact_resolver,
                      miss_terminates=sysspec.miss_terminates,
                      p_kill=sysspec.p_kill, tau_kill=sysspec.tau_kill,
                      r_nk=sysspec.r_nk),
        finisher_mobility=0.0 if args.fixed_only else [0.0, args.a_max],
        omega_max_arms=[float(cfg["attitude"]["omega_max"]), SLEW_UNLIMITED],
        n=args.n, seed0=args.seed0,
        crn_episode_range=[args.seed0, args.seed0 + args.n - 1],
        geometry=dict(rho=ph["net_radius"], tau=ph["tau_deploy"],
                      cone_range_max=cone["range_max"],
                      cone_half_angle=cone["half_angle"],
                      kill_radius=ph["kill_radius"], dt=ph["dt"],
                      episode_len=cfg["train"]["episode_len"]),
    )


def _slew_counterfactual(args) -> None:
    """★ {고정,이동} x {omega 2.0, inf}. 같은 CRN 이므로 네 칸이 전부 짝지어진다.

    두 질문을 동시에 닫는다 (docs/51 §9):
      1. 이동 악화가 슬루 제한 때문인가   -> 이동 쪽이 무한 슬루에서 회복되는가
      2. ★ 고정 조건에서도 슬루가 병목인가 -> 고정 쪽이 무한 슬루에서 오르는가
    2 가 크면 docs/48 사슬이 통째로 놓친 축이다 -- 조준 *방향* 만 봤고 *속도* 는
    안 봤다.
    """
    att = _attacker_from_args(args)
    grid = [("고정·ω2.0", 0.0, None), ("고정·ω∞", 0.0, SLEW_UNLIMITED),
            ("이동·ω2.0", args.a_max, None), ("이동·ω∞", args.a_max, SLEW_UNLIMITED)]
    if args.fixed_only:          # docs/83 E1 = 고정 2 칸만 (사전등록 범위 그대로)
        grid = grid[:2]
    print(f"[슬루 반사실] n={args.n} paired CRN, a_max={args.a_max:.3f}, "
          f"ω∞={SLEW_UNLIMITED:g}, threat={_threat_class(args)} "
          f"(route_gain={args.route_gain}, sense_range={args.sense_range})")
    cells, out = {}, {}
    for name, mob, om in grid:
        c = cells[name] = run_cell(args.n, args.seed0, mobility=mob, omega_max=om,
                                   attacker=att)
        sm = c["summary"]; reg = sm["by_regime"].get(SHAPE, {})
        out[name] = sm
        print(f"  {name:10s} 전체 {sm['neutralized_rate']:.4f}  비손실 "
              f"{sm['nondestructive_frac']:.3f}  {SHAPE} "
              f"{reg.get('neutralized_rate', float('nan')):.4f} (n={reg.get('n', 0)})")

    print("\n  paired 비교 (기준 -> 대상):")
    pairs = [("고정·ω2.0", "고정·ω∞", "★ 슬루가 고정 조건의 병목인가"),
             ("이동·ω2.0", "이동·ω∞", "슬루가 이동 악화의 매개인가"),
             ("고정·ω2.0", "이동·ω2.0", "(재확인) 현재 ω 에서 이동 효과"),
             ("고정·ω∞", "이동·ω∞", "무한 슬루에서도 이동이 해로운가")]
    pairs = [p for p in pairs if p[0] in cells and p[1] in cells]
    res = {}
    for a, b, why in pairs:
        for reg in (SHAPE, None):
            p = paired_compare(cells[a], cells[b], regime=reg)
            res[f"{a} -> {b} [{p['regime']}]"] = p
            if reg == SHAPE:
                print(f"  {a:10s} -> {b:10s} {p['regime']:15s} "
                      f"{p['fixed_rate']:.4f} -> {p['mobile_rate']:.4f} "
                      f"({p['diff']:+.4f}) 구제 {p['rescued_n01']:3d} / 망침 "
                      f"{p['broken_n10']:3d}   {why}")
            else:
                print(f"  {'':10s}    {'':10s} {'ALL':15s} "
                      f"{p['fixed_rate']:.4f} -> {p['mobile_rate']:.4f} "
                      f"({p['diff']:+.4f}) 구제 {p['rescued_n01']:3d} / 망침 "
                      f"{p['broken_n10']:3d}")
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(
            {"declared": {"n": args.n, "a_max": args.a_max,
                          "omega_unlimited": SLEW_UNLIMITED},
             "manifest": _manifest(args),
             "cells": out, "paired": res}, indent=2, ensure_ascii=False),
            encoding="utf-8")
        print(f"  -> {args.out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="포획기 이동성 요인 실험 (docs/51)")
    ap.add_argument("--n", type=int, default=500, help="셀당 평가 판수")
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--a-max", type=float, default=MOBILE_A_MAX,
                    help="이동 셀의 병진 가속 상한 (docs/51 §2.1 선언값)")
    ap.add_argument("--travel-n", type=int, default=50)
    ap.add_argument("--slew-counterfactual", action="store_true",
                    help="{고정,이동} x {omega_max=2.0, inf} 4칸 (docs/51 §9). "
                         "이동 악화가 슬루 제한 때문인지, 그리고 고정 조건에서도 "
                         "슬루가 병목인지를 같은 CRN 으로 가른다")
    # docs/83 E1: 기본값 (0.0, inf) = T0 이므로 기존 결과는 bit-exact 재현된다.
    ap.add_argument("--route-gain", type=float, default=0.0,
                    help="공격자 angular-gap 횡편향 이득. T1 = 0.5 (docs/80 §2)")
    ap.add_argument("--sense-range", type=float, default=float("inf"),
                    help="공격자 limiter 감지 반경 [m]. T1 = 30.0")
    ap.add_argument("--fixed-only", action="store_true",
                    help="고정 finisher 2 칸만 (docs/83 E1 사전등록 범위)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.slew_counterfactual:
        return _slew_counterfactual(args)
    print(f"[이동성] 해석적 조준 x {{고정, 이동}}  n={args.n} paired CRN  "
          f"a_max={args.a_max:.3f}")
    cells = {}
    for name, mob in (("cell1_fixed", 0.0), ("cell3_mobile", args.a_max)):
        cells[name] = run_cell(args.n, args.seed0, mobility=mob)
        s = cells[name]["summary"]
        reg = s["by_regime"].get(SHAPE, {})
        print(f"  {name:13s} 전체무력화 {s['neutralized_rate']:.3f}  "
              f"비손실 {s['nondestructive_frac']:.3f}  "
              f"{SHAPE} {reg.get('neutralized_rate', float('nan')):.4f} "
              f"(n={reg.get('n', 0)})")

    out = {"declared": {"a_max": args.a_max, "n": args.n, "seed0": args.seed0,
                        "primary": f"{SHAPE} paired diff 95% lower > 0"},
           "cells": {k: v["summary"] for k, v in cells.items()},
           "paired": {}, "travel": travel_stats(args.travel_n, args.seed0,
                                                args.a_max)}
    for reg in (SHAPE, None):
        p = paired_compare(cells["cell1_fixed"], cells["cell3_mobile"], regime=reg)
        out["paired"][p["regime"]] = p
        star = "★ " if reg == SHAPE else "  "
        print(f"{star}{p['regime']:16s} 고정 {p['fixed_rate']:.4f} -> 이동 "
              f"{p['mobile_rate']:.4f}  차이 {p['diff']:+.4f} "
              f"CI95 [{p['diff_ci95'][0]:+.4f}, {p['diff_ci95'][1]:+.4f}]  "
              f"{'통과' if p['passes'] else '미달'}  "
              f"(구제 {p['rescued_n01']} / 망침 {p['broken_n10']}, n={p['n_paired']})")
    t = out["travel"]
    print(f"  이동거리 평균 {t['path_len_mean']:.2f} (p90 {t['path_len_p90']:.2f}), "
          f"순변위 평균 {t['net_displacement_mean']:.2f} 최대 {t['net_displacement_max']:.2f}")

    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
