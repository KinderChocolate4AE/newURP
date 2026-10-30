"""Seal E9 = 비이상성 접힘 프로브 — docs/144. 격자·참조 셀·판정 규칙의 단일 원천.

    python scripts/fs1_e9_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/e9_manifest.json)

질문: 추적 지연 L 과 조준 오차 δ 를 χ 에 '보수적으로 접어 넣을' 수 있는가 —
  χ_eff = a(τ+L)² / (2·R·tan(θ−δ)),  χ*_geom(θ−δ).
비이상 셀의 창이 같은 χ_eff 의 이상 참조 셀 (a 배율 / θ 축소) 창보다 작지 않으면 접힘이 보수적이다.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_e4_manifest as E4  # noqa: E402  (FS1 상수·ρ·ρ₀·N∞ 정의를 그대로 승계)

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e9_manifest.json"

# 기준점 = E4 τ 계열 이름 그대로 (rollout 이 E4 와 같으므로 rb 배열 bit-동일이 wiring 검사)
BASES = {"t1.0_h1.0_cv": 1.0, "tau_m2.94": E4.K15 ** -0.5, "t0.7_h1.0_cv": 0.7, "t0.5_h1.0_cv": 0.5}
LAGS = (1, 2)                 # tick (dt 0.05 s) → L 0.05, 0.10 s
DELTAS = (0.02, 0.05)         # rad (1.15°, 2.86°; θ0 = 12.15°)
COMBO = (1, 0.02)             # 결합 1점 (L 0.05 s + δ 0.02 rad)
TOL_TICKS = 1.5               # E4 SPREAD_TICKS 승계 (1 tick + 정수 중앙값 반올림)
E9_SEED = 290000              # δ 방향 φ 전용 RNG (rollout 의 전역 np.random 과 분리)


def _cell(name, fam, base, ts, lag=0, delta=0.0):
    """비이상 셀 + 그 참조 셀 (같은 χ_eff 를 이상 판정 인자로: a 배율 = ((τ+L)/τ)², θ 배율 = (θ0−δ)/θ0)."""
    tau = E4.TAU0 * ts
    as_ = ((tau + lag * E4.DT) / tau) ** 2
    hs = (E4.TH0 - delta) / E4.TH0
    ref = {"name": f"{name}_ref", "family": "ref", "base": base, "ts": ts, "hs": hs, "as": as_, "rs": 1.0,
           "lag": 0, "delta": 0.0, "ref": None}
    cell = {"name": name, "family": fam, "base": base, "ts": ts, "hs": 1.0, "as": 1.0, "rs": 1.0,
            "lag": lag, "delta": delta, "ref": ref["name"]}
    return [cell, ref]


def grid() -> list:
    g = []
    for b, ts in BASES.items():
        g.append({"name": b, "family": "base", "base": b, "ts": ts, "hs": 1.0, "as": 1.0, "rs": 1.0,
                  "lag": 0, "delta": 0.0, "ref": None})
        for k in LAGS:
            g += _cell(f"{b}_L{k}", "L", b, ts, lag=k)
        for d in DELTAS:
            g += _cell(f"{b}_d{d}", "d", b, ts, delta=d)
        g += _cell(f"{b}_L{COMBO[0]}d{COMBO[1]}", "Ld", b, ts, lag=COMBO[0], delta=COMBO[1])
    return g


GRID = grid()
FAMILIES = ("L", "d", "Ld")


def chi_eff(c) -> float:
    """비이상 셀의 χ_eff = 1/ρ(참조 셀). 기준점은 χ 그대로."""
    tau, L = E4.TAU0 * c["ts"], c["lag"] * E4.DT
    th = E4.TH0 - c["delta"]
    return 0.5 * E4.A0 * (tau + L) ** 2 / (E4.RMAX * math.tan(th))


def verdict(win: dict) -> dict:
    """win[name] = 변형 창 (4 slot 중앙값의 중앙값, E4 지표). 셀 통과 = 창(비이상) ≥ 창(참조) − TOL.
    정보 셀 = 둘 중 하나라도 창 ≥ 1. 가족 판정: 정보 셀 < 절반 → FOLD_UNDECIDABLE_FLOOR,
    정보 셀 전부 통과 → FOLD_CONSERVATIVE, 하나라도 실패 → FOLD_BREAKS."""
    out = {}
    for fam in FAMILIES:
        cells = [x for x in GRID if x["family"] == fam]
        rows, n_inf, fails = {}, 0, []
        for c in cells:
            w, wr = float(win[c["name"]]), float(win[c["ref"]])
            info = max(w, wr) >= 1.0
            ok = w >= wr - TOL_TICKS - 1e-9
            n_inf += info
            if info and not ok:
                fails.append(c["name"])
            rows[c["name"]] = {"chi_eff": round(chi_eff(c), 4), "window": w, "window_ref": wr,
                               "gap": w - wr, "informative": info, "pass": ok,
                               "window_base": float(win[c["base"]])}
        lab = ("FOLD_UNDECIDABLE_FLOOR" if n_inf < math.ceil(len(cells) / 2) else
               "FOLD_BREAKS" if fails else "FOLD_CONSERVATIVE")
        out[fam] = {"cells": rows, "n_informative": n_inf, "failing": fails, "verdict": lab}
    return out


def build() -> dict:
    body = {
        "schema": "fs1-e9-manifest-v1",
        "status": ("sealed 2026-10-31 BEFORE any E9 run (contract docs/144; user approval of the non-ideality "
                   "probe 2026-10-20, 'start' 2026-10-31). Design origin: advisor draft docs/141 §5 (2a); "
                   "changed before seal: tau_r axis removed (judge-level tau_r == a-scale (1-tau_r/tau)^2, "
                   "already covered by E4 a family), judgment = fold-conservativeness vs matched ideal "
                   "reference cells instead of Spearman ordering"),
        "lineage": {"protocol": "E4 (docs/133, manifest d41bfc2693d8f8c7) rollout unchanged: m0.35_n1, 4 old-world "
                                "adapted attackers x 24 eps, SEED0 268000, no-fire, slew-simulated cv aim, window = "
                                "LOADED and d <= 16 m",
                    "wiring": "base variants keep E4 names; their rb rows must equal artifacts/fs1/e4/rows.npz "
                              "bit-exact, else the run is void (not a result)"},
        "question": ("can tracking latency L and boresight aim error delta be folded conservatively into chi: "
                     "chi_eff = a (tau+L)^2 / (2 R tan(theta-delta)), chi*_geom(theta-delta)"),
        "knob_semantics": {
            "L": ("aim point from the attacker state L ago, latency-compensated: nc = p(t-L) + v(t-L)(tau+L); "
                  "turret slews toward it; judge uses the TRUE current state and true tau, a, theta"),
            "delta": ("judge cone axis = slewed axis rotated by delta toward a per-episode random direction "
                      f"phi ~ U[0, 2pi) (rng seed [{E9_SEED}, ep]); slew itself unbiased"),
            "ref": ("ideal cell at the same chi_eff: judge a x ((tau+L)/tau)^2 and/or theta x (theta0-delta)/theta0, "
                    "fresh aim, no offset"),
            "worst_case_argument": ("stale-state deviation <= a L (tau + L/2) so required radius <= a (tau+L)^2 / 2; "
                                    "an offset cone of half-angle theta contains the coaxial cone theta-delta. "
                                    "Both make the reference a lower bound -> predicted gap >= 0"),
        },
        "grid": [{**c, "chi_eff": round(chi_eff(c), 4), "rho_nominal": round(E4.rho(c), 4)} for c in GRID],
        "metric": "window = per-episode robust ticks (limiters present); variant value = median of 4 slot medians",
        "predictions": {
            "P-E9 fold": (f"per family (L, d, Ld): cell passes if window >= window_ref - {TOL_TICKS} tick; "
                          "informative cell = max(window, window_ref) >= 1; informative < half of cells -> "
                          "FOLD_UNDECIDABLE_FLOOR; all informative pass -> FOLD_CONSERVATIVE; else FOLD_BREAKS "
                          "(failing cells listed)"),
            "expected": "FOLD_CONSERVATIVE with gap >= 0 (worst-case argument)",
            "report_only": ["gap distribution (size of conservatism)", "monotonicity in L, delta within each base",
                            "E4 formula N_pred at chi_eff"],
        },
        "consequence": {
            "L and d FOLD_CONSERVATIVE": ("real-system chi map (URP direction A) folds sensor latency and aim error "
                                          "into one chi_eff axis as a conservative design rule (probe layer)"),
            "FOLD_BREAKS": ("that non-ideality stays a separate axis on the map; the fold rule under-predicts "
                            "degradation there -> URP limitations + new governing-variable note"),
            "FOLD_UNDECIDABLE_FLOOR": "fold rule stays an analytic worst-case derivation only",
        },
        "tau_r_analytic": ("judge-level evader reaction delay tau_r: reachable displacement = a (tau - tau_r)^2 / 2 "
                           "== a-scale (1 - tau_r/tau)^2; E4 a family (0.654, 0.49, 0.25 == tau_r ~0.057, 0.09, "
                           "0.15 s at tau 0.3) already collapsed with the tau family (4=4, 4=4, 4 vs 5) -> no run"),
        "not_evidence_for": ["learned ceilings", "behavioral reaction to launch (learning layer)",
                             "full FCS error models (aim path only)", "seed sensitivity (single seed set, paired "
                                                                         "with E4)"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E9 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in build()["grid"]:
        print(f"{c['name']:22s} {c['family']:4s} chi_eff {c['chi_eff']:.3f} ts {c['ts']:.3f} hs {c['hs']:.3f} "
              f"as {c['as']:.3f} lag {c['lag']} delta {c['delta']}")
    print(MANIFEST, build()["manifest_hash"])
