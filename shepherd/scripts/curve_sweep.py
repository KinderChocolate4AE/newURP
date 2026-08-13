"""포획 확률 곡선 — x = 공격자 최대 기동 가속도, y = 막아낼 확률.

WHY
---
`by_regime` 은 경계를 **2칸**으로만 본다 (`FREE_CAPTURE` / `SHAPING_NEEDED`).
그러면 "경계 위 0%" 는 보이지만 **경계 아래에서 이미 무너지고 있다**는 것은 안 보인다.
`a_att` 를 연속축으로 두고 판을 묶으면 그게 보이고, 실제로 보였다 (docs/45 §9):

    붕괴 50% 교차 = 24.06        a* = 2 rho / tau^2 = 39.33
    slew_audit 이 잰 잔여 조준각 psi = 4.26 deg 를 일반형에 넣으면 25.75
    -> 서로를 보지 않고 잰 두 값이 6.6 % 안에서 만난다 = **두 번째 경계의 검증**

**이 곡선은 손튜닝 기준선의 것이지 학습 정책의 것이 아니다.** 경계 위 0 % 는
시스템 성능이 아니라 **문제 정의**다. 인용할 때 이 구분을 지우지 않는다.

주의 — 계측 조합 (정정 8)
    커밋 비트는 limiter 행동 벡터(idx3)에 실려 있고 `hold_position_limiter()` 는
    그 자리를 0 으로 둔다. 그래서 `mode="hold" + baseline_commit=True` 는
    **hold 와 완전히 같다**. intercept 기준선 재현 조합은 `intercept + commit` 이다.

    python -m shepherd.scripts.curve_sweep --mode hold --episodes 1500 \
        --out results/curve_hold.json
    python -m shepherd.scripts.curve_sweep --summarize results/curve_hold.json

`OMP_NUM_THREADS=1` 로 띄울 것 — 코어가 적으면 BLAS 스레드 경합으로 5배 느려진다(실측).
100판마다 원자적 체크포인트를 쓰고, 같은 파일로 다시 부르면 이어서 돈다.
torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_config import THREAT_BRACKET, m4_config
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.spawn_rand import SpawnSpec
from shepherd.stats import Z_TWO_SIDED_95
from shepherd.stats import wilson as _wilson

__all__ = ["MODES", "wilson", "bin_edges", "run_curve", "summarize_curve",
           "summarize_bands", "a_star", "a_star_psi", "PSI_MED_DEG",
           "band_of", "BANDS"]

MODES = ("hold", "ring", "intercept")
_CAPTURE = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
_NEUTRALIZED = _CAPTURE + ("HARD_KILL",)

# ===========================================================================
# BAND_AIM -- **결과를 보기 전에 선언한다** (docs/47 §4.4).
#
# `by_regime` 은 `a*` 하나로만 가른다. 그런데 곡선을 그려 보니 손튜닝 기준선은
# `a*` 훨씬 앞에서 무너지고(50% 교차 24.07), 그 사이 구간은 **물리적으로는 포획이
# 가능한데(w <= rho) 손튜닝이 4% 밖에 못 잡는** 곳이다. 학습이 이길 여지가 존재함이
# 사전 실측으로 확인된 유일한 구간이므로 이름을 붙여 **함께 보고**한다.
#
# ★ 1차 판정식(docs/47 §4.3)에는 들어가지 않는다. 판정식을 결과 뒤에 바꾸면
#   소급 변경이다. 이건 보고 축일 뿐이다.
#
# 경계값 `PSI_MED_DEG` 는 slew_audit 실측치이며 학습 결과와 무관하게 이미 고정됐다.
# ===========================================================================
PSI_MED_DEG = 4.26      # slew_audit: A2 jink 0.6 · hold · FREE_CAPTURE 구간 중앙값


def _band_bounds(cfg: Optional[dict] = None) -> Tuple[float, float]:
    cfg = cfg or m4_config()
    tau = float(cfg["physics"]["tau_deploy"])
    cone = cfg["viability"]["cone"]
    lo = a_star_psi(math.radians(PSI_MED_DEG),
                    range_max=float(cone["range_max"]),
                    half_angle=float(cone["half_angle"]), tau=tau)
    return lo, a_star(float(cfg["physics"]["net_radius"]), tau)


BANDS = ("EASY", "BAND_AIM", "SHAPING_NEEDED")


def band_of(a_att: float, cfg: Optional[dict] = None) -> str:
    """`a*` 한 칸이 아니라 **세 칸**으로 가른다.

        EASY            a < a*(psi_med)   -- 손튜닝으로도 잡힌다
        BAND_AIM        그 사이           -- 물리는 허용, 손튜닝이 못 잡는다
        SHAPING_NEEDED  a >= a*           -- 네트로는 원리적으로 불가능

    가장 위 칸의 이름은 `regime_of` 와 **일부러 같게** 둔다: 같은 경계이고,
    두 이름이 갈리면 표에서 서로 다른 것으로 읽힌다.
    """
    lo, hi = _band_bounds(cfg)
    a = float(a_att)
    return "EASY" if a < lo else ("BAND_AIM" if a < hi else "SHAPING_NEEDED")


# --------------------------------------------------------------------- 경계식
def a_star(net_radius: float, tau: float) -> float:
    """명제 N — `w = 0.5*a*tau^2 = rho` 인 지점. **psi = 0 (완벽 정렬) 단면.**"""
    return 2.0 * float(net_radius) / float(tau) ** 2


def a_star_psi(psi_rad: float, *, range_max: float, half_angle: float,
               tau: float) -> float:
    """잔여 조준각 `psi` 를 넣은 일반형 (docs/45 §4).

        a*(psi) = 2 * d * (tan(theta) - psi) / tau^2

    `psi = 0` 이면 `d * tan(theta) = rho` 이므로 `a_star()` 와 같아진다.
    """
    return 2.0 * float(range_max) * (math.tan(float(half_angle)) - float(psi_rad)) \
        / float(tau) ** 2


# ----------------------------------------------------------------------- 통계
def wilson(k: int, n: int, z: float = Z_TWO_SIDED_95) -> Tuple[float, float, float]:
    """`(점추정, 하한, 상한)`. 구간 자체는 `shepherd.stats.wilson` 이 유일한 정의다.

    여기만 3-튜플인 이유: 이 모듈은 구간과 점추정을 항상 같이 쓴다. **`n<=0` 이면
    `(0, 0, 0)`** -- 표본이 없는 칸을 표에 0 으로 찍기 위한 것이고, `stats.wilson`
    의 `(0, 1)`(정보 없음)과는 **일부러 다른 계약**이다. 바꾸면 빈 밴드의 상한이
    0 에서 1 로 튄다.
    """
    if n <= 0:
        return 0.0, 0.0, 0.0
    lo, hi = _wilson(k, n, z)
    return k / n, lo, hi


def bin_edges(lo: float, hi: float, boundary: float, per_side: int = 4) -> List[float]:
    """**경계가 격자선 위에 정확히 놓이도록** 좌우를 따로 나눈다.

    균등 격자를 쓰면 경계가 칸 안에 묻혀 "경계 위 0%" 가 희석된다.
    """
    if not lo < boundary < hi:
        raise ValueError(f"boundary {boundary} 가 [{lo}, {hi}] 안에 없다")
    left = [lo + (boundary - lo) * i / per_side for i in range(per_side)]
    right = [boundary + (hi - boundary) * i / per_side for i in range(per_side)]
    return left + right + [hi]


# ----------------------------------------------------------------------- 계측
def _default_kw(w_kill: float, level: str, jink: float,
                route_gain: float = 0.0, sense_range: float = float("inf"),
                capture_terminates: bool = True) -> dict:
    # docs/65 A2 — 학습·평가·스윕과 같은 비준 계약. docs/45 의 곡선(50% 교차
    # 24.06 등)은 legacy 구계약 실측이므로 재실행 수치와 병치할 때 한정 병기.
    #
    # route_gain/sense_range (2026-08-13 추가): 공격자를 **반응형**으로 만드는
    # 유일한 항 — 감지 반경 안의 limiter 위치를 보고 가장 넓은 각도 틈으로
    # 횡가속을 편향한다 (docs/60 §3.2). **기본값 (0.0, inf) = legacy 비반응형
    # 그대로라 기존 곡선은 bit-exact 재현된다.** 반응형 재실행은 등록된 v3
    # nominal 값 (route_gain 0.5, sense_range 30.0) 을 명시적으로 넘겨서 한다.
    # capture_terminates (R3, docs/83 §10.2): 기본 True = 현행. False 는 E2-B
    # sham-net 반사실 전용 -- 성공한 net capture 의 **종료만** 억제하고 commit ·
    # 공격자 응답 · SPENT/K=0 · 하드킬 · 침투 · 절단은 보존한다.
    return dict(system=ratified_system(capture_terminates=capture_terminates),
                reward=RewardSpec(w_kill=w_kill, enabled=True),
                attacker=AttackerSpec(level=level, jink_amp=jink, seed=0,
                                      route_gain=route_gain,
                                      sense_range=sense_range),
                spawn=SpawnSpec())


def run_curve(seed0: int, episodes: int, *, mode: str = "hold",
              w_kill: float = 0.5, level: str = "A2", jink: float = 0.6,
              route_gain: float = 0.0, sense_range: float = float("inf"),
              capture_terminates: bool = True,
              out: Optional[str] = None, checkpoint_every: int = 100,
              log: Optional[Callable[[str], None]] = None) -> dict:
    """판마다 위협 draw + 라벨을 기록한다.

    `mission_eval(seed0, episodes)` 의 본문과 **동일한 draw** 를 쓴다
    (`build_m4_env(seed0, ep)` + `run_episode(seed=seed0+ep)`). 다만 체크포인트를
    쓰기 위해 루프를 여기서 돈다.
    """
    from shepherd.scripts.mission_rollout import run_episode

    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; allowed: {MODES}")
    commit = (mode == "intercept")     # ★ 정정 8 -- 모듈 독스트링 참조
    kw = _default_kw(w_kill, level, jink, route_gain, sense_range,
                     capture_terminates)

    records: List[dict] = []
    if out and os.path.exists(out):                       # 이어 돌기
        with open(out, encoding="utf-8") as f:
            prev = json.load(f)
        if prev.get("mode") == mode and prev.get("seed0") == seed0:
            records = prev["records"]
            if any(r["episode"] != i for i, r in enumerate(records)):
                raise ValueError(f"{out}: 체크포인트 에피소드 인덱스가 불연속이다")

    def _save(done: int) -> None:
        if not out:
            return
        payload = {"mode": mode, "seed0": seed0, "n_done": done,
                   "n_target": episodes, "baseline_commit": commit,
                   "w_kill": w_kill, "level": level, "jink_amp": jink,
                   # ★ 수치감사 §G-② 대응: 캠페인을 정의하는 값은 아티팩트 자체에
                   #   남긴다 (파일명·노트로만 구분하던 사고 재발 방지).
                   "route_gain": route_gain, "sense_range": sense_range,
                   "capture_terminates": capture_terminates,
                   "records": records}
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, out)                              # 원자적 — 반쪽 파일 금지

    for ep in range(len(records), episodes):
        st = build_m4_env(seed0, ep, **kw)
        r = run_episode(st.env, st.scn, st.lay, seed=seed0 + ep,
                        limiter_mode=mode, fire_mode="clean",
                        policy=None, baseline_commit=commit)
        records.append({
            "episode": ep, "label": r.label,
            "regime": regime_of(st.threat["a_att"], st.threat["tau"],
                                st.threat["net_radius"]),
            "a_att": st.threat["a_att"], "att_speed": st.threat["att_speed"],
            "net_radius": st.threat["net_radius"], "tau": st.threat["tau"]})
        if (ep + 1) % checkpoint_every == 0 or ep + 1 == episodes:
            _save(ep + 1)
            if log:
                log(f"[{mode}] {ep + 1}/{episodes}")
    return {"mode": mode, "seed0": seed0, "n_done": len(records),
            "n_target": episodes, "baseline_commit": commit,
            "w_kill": w_kill, "level": level, "jink_amp": jink,
            "records": records}


# ----------------------------------------------------------------------- 집계
def summarize_bands(records: Sequence[dict], cfg: Optional[dict] = None) -> dict:
    """판별 기록을 **세 칸**으로 집계한다 (docs/47 §4.4).

    `mission_eval(records=...)` 가 뱉는 리스트를 그대로 먹는다. 학습 런의
    `summary.json` 과 손튜닝 기준선이 **같은 함수**로 집계되도록 여기 한 곳에만 둔다 --
    두 곳에 복사하면 경계값이 갈라지고, 그러면 비교 자체가 무의미해진다.
    """
    cfg = cfg or m4_config()
    out: Dict[str, dict] = {}
    for name in BANDS:
        sel = [r for r in records if band_of(r["a_att"], cfg) == name]
        n = len(sel)
        kc = sum(1 for r in sel if r["label"] in _CAPTURE)
        kn = sum(1 for r in sel if r["label"] in _NEUTRALIZED)
        pc, lc, hc = wilson(kc, n)
        pn, ln, hn = wilson(kn, n)
        out[name] = {"n": n,
                     "net_capture": {"k": kc, "p": pc, "lo": lc, "hi": hc},
                     "neutralized": {"k": kn, "p": pn, "lo": ln, "hi": hn},
                     "nondestructive_frac": (kc / kn) if kn else None}
    lo, hi = _band_bounds(cfg)
    out["_bounds"] = {"psi_med_deg": PSI_MED_DEG, "band_aim_lo": lo,
                      "band_aim_hi": hi}
    return out


def _cross50(xs: Sequence[float], ps: Sequence[float]) -> float:
    """확률이 0.5 를 아래로 가르는 지점 (선형보간). 없으면 NaN."""
    for i in range(len(ps) - 1):
        if ps[i] >= 0.5 > ps[i + 1]:
            return xs[i] + (xs[i + 1] - xs[i]) * (ps[i] - 0.5) / (ps[i] - ps[i + 1])
    return float("nan")


def summarize_curve(data: dict, *, per_side: int = 4,
                    cfg: Optional[dict] = None) -> dict:
    """구간별 Wilson 구간 + 50% 교차점 + 두 경계값."""
    cfg = cfg or m4_config()
    rec = data["records"]
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    rho = float(cfg["physics"]["net_radius"])
    tau = float(cfg["physics"]["tau_deploy"])
    astar = a_star(rho, tau)
    edges = bin_edges(float(lo), float(hi), astar, per_side)

    out_bins, xs, ps_cap = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = [r for r in rec
               if a <= r["a_att"] < b or (b == edges[-1] and r["a_att"] == b)]
        n = len(sel)
        kc = sum(1 for r in sel if r["label"] in _CAPTURE)
        kn = sum(1 for r in sel if r["label"] in _NEUTRALIZED)
        pc, lc, hc = wilson(kc, n)
        pn, ln, hn = wilson(kn, n)
        mid = (a + b) / 2.0
        out_bins.append({"lo": a, "hi": b, "mid": mid, "n": n,
                         "net_capture": {"k": kc, "p": pc, "lo": lc, "hi": hc},
                         "neutralized": {"k": kn, "p": pn, "lo": ln, "hi": hn}})
        xs.append(mid); ps_cap.append(pc)

    above = [b for b in out_bins if b["lo"] >= astar - 1e-9]
    n_above = sum(b["n"] for b in above)
    k_above = sum(b["net_capture"]["k"] for b in above)
    _, _, hi_above = wilson(k_above, n_above)

    by_band = summarize_bands(rec, cfg)          # 판마다 직접 센다 (구간 격자와 독립)

    return {
        "mode": data["mode"], "n": len(rec),
        "level": data.get("level"), "jink_amp": data.get("jink_amp"),
        "a_star": astar,
        "psi_med_deg": PSI_MED_DEG,
        "band_bounds": list(_band_bounds(cfg)),
        "by_band": by_band,
        "bins": out_bins,
        "cross50_net_capture": _cross50(xs, ps_cap),
        "above_a_star": {"n": n_above, "net_capture_k": k_above,
                         "wilson_hi": hi_above},
        "_declared": {"net_radius": rho, "tau_deploy": tau,
                      "range_max": float(cfg["viability"]["cone"]["range_max"]),
                      "half_angle": float(cfg["viability"]["cone"]["half_angle"]),
                      "a_att_bracket": [float(lo), float(hi)]},
        "_caveat": "손튜닝 기준선의 곡선이다. 학습 정책의 성능이 아니다.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="포획 확률 곡선 (모델 변경 없음)")
    ap.add_argument("--mode", default="hold", choices=MODES)
    ap.add_argument("--episodes", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--w-kill", type=float, default=0.5)
    ap.add_argument("--level", default="A2", choices=("A1", "A2", "A3"))
    ap.add_argument("--jink-amp", type=float, default=0.6)
    ap.add_argument("--route-gain", type=float, default=0.0,
                    help="반응형 회피 이득 (0 = legacy 비반응형, v3 nominal 0.5)")
    ap.add_argument("--sense-range", type=float, default=float("inf"),
                    help="limiter 감지 반경 m (inf = legacy, v3 nominal 30.0)")
    ap.add_argument("--sham-net", action="store_true",
                    help="R3 capture_terminates=False (docs/83 §10.2 E2-B 전용). "
                         "성공한 net capture 의 종료만 억제한다")
    ap.add_argument("--out", default=None, help="체크포인트 겸 결과 (절대경로 권장)")
    ap.add_argument("--summarize", default=None, metavar="JSON",
                    help="계측 없이 기존 파일만 집계")
    ap.add_argument("--psi-deg", type=float, default=None,
                    help="slew_audit 이 잰 잔여 조준각. 주면 a*(psi) 를 함께 낸다")
    a = ap.parse_args(argv)

    if a.summarize:
        with open(a.summarize, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = run_curve(a.seed, a.episodes, mode=a.mode, w_kill=a.w_kill,
                         level=a.level, jink=a.jink_amp,
                         route_gain=a.route_gain, sense_range=a.sense_range,
                         capture_terminates=not a.sham_net,
                         out=a.out, log=lambda m: print(m, flush=True))

    s = summarize_curve(data)
    if a.psi_deg is not None:
        d = s["_declared"]
        s["a_star_psi"] = {
            "psi_deg": a.psi_deg,
            "value": a_star_psi(math.radians(a.psi_deg),
                                range_max=d["range_max"],
                                half_angle=d["half_angle"], tau=d["tau_deploy"])}
    print(json.dumps(s, indent=2, ensure_ascii=False))

    print(f"\n>> {s['mode']}  n={s['n']}   a* = {s['a_star']:.2f}")
    for b in s["bins"]:
        c = b["net_capture"]
        print(f"   a in [{b['lo']:5.1f}, {b['hi']:5.1f})  n={b['n']:4d}  "
              f"네트포획 {c['p']:.3f} [{c['lo']:.3f}, {c['hi']:.3f}]")
    print(f"   50% 교차 = {s['cross50_net_capture']:.2f}")
    ab = s["above_a_star"]
    print(f"   경계 위: 네트 포획 {ab['net_capture_k']}/{ab['n']}  "
          f"(Wilson 상한 {ab['wilson_hi']:.4f})")
    lo_b, hi_b = s["band_bounds"]
    print(f"\n   세 칸 (BAND_AIM = [{lo_b:.1f}, {hi_b:.1f}), psi_med={s['psi_med_deg']}deg)")
    for name in ("EASY", "BAND_AIM", "SHAPING_NEEDED"):
        b = s["by_band"][name]
        c, k = b["net_capture"], b["neutralized"]
        print(f"     {name:15s} n={b['n']:4d}  네트포획 {c['p']:.3f} "
              f"[{c['lo']:.3f}, {c['hi']:.3f}]   무력화 {k['p']:.3f}")
    if "a_star_psi" in s:
        v = s["a_star_psi"]
        print(f"   a*(psi={v['psi_deg']}deg) = {v['value']:.2f}   "
              f"(관측 50% 교차와 편차 "
              f"{100 * abs(s['cross50_net_capture'] - v['value']) / v['value']:.1f} %)")
    print("   ※ 손튜닝 기준선의 곡선이다. 학습 정책의 성능이 아니다.")
    return s


if __name__ == "__main__":                                   # pragma: no cover
    main()
