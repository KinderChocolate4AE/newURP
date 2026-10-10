"""Seal E4 = ρ-collapse probe — docs/133. 격자 (GRID) 와 사전 예측의 단일 원천.

    python scripts/fs1_e4_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/e4_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e4_manifest.json"

# FS1 상수 (artifacts/fs1/e7a/probe.json consts — 판독에서 일치 assert)
TAU0, TH0, RMAX, A0, DT, V_BAR = 0.3, 0.21209009342092547, 8.22, 20.453333333333333, 0.05, 23.01
RHO_B = RMAX * math.tan(TH0) / (0.5 * A0 * TAU0 ** 2)           # 1.9231
K15 = math.tan(1.5 * TH0) / math.tan(TH0)                          # θ 1.5× 의 tan 배율 (ρ 2.94)


def _th(s):          # tanθ 를 s 배 하는 θ 배율
    return math.atan(math.tan(TH0) * s) / TH0


def _g(name, fam, ts=1.0, hs=1.0, as_=1.0, rs=1.0):
    return {"name": name, "family": fam, "ts": ts, "hs": hs, "as": as_, "rs": rs}


# ρ 배율 m 을 각 계열로 만든다: τ → ts = m^-1/2, a → as = 1/m, θ → tanθ×m, R → rs = m
GRID = [_g("t1.0_h1.0_cv", "base"),
        # ρ ≈ 1.335 (×1/1.44)
        _g("tau_1.2", "tau", ts=1.2), _g("th_x0.694", "theta", hs=_th(1 / 1.44)), _g("R_x0.694", "R", rs=1 / 1.44),
        # ρ ≈ 2.94 (×K15)
        _g("tau_m2.94", "tau", ts=K15 ** -0.5), _g("a_m2.94", "a", as_=1 / K15), _g("t1.0_h1.5_cv", "theta", hs=1.5),
        _g("R_m2.94", "R", rs=K15),
        # ρ ≈ 3.92 (×1/0.49)
        _g("t0.7_h1.0_cv", "tau", ts=0.7), _g("a_m3.92", "a", as_=0.49), _g("th_x2.04", "theta", hs=_th(1 / 0.49)),
        # ρ ≈ 7.69 (×4)
        _g("t0.5_h1.0_cv", "tau", ts=0.5), _g("a_m7.69", "a", as_=0.25), _g("th_x4", "theta", hs=_th(4.0)),
        # ρ₀ 근방 (a↑ 방향, 지도교수 권고) 과 ρ < ρ₀ 매칭 (×1/1.69 → ρ 1.138 < ρ₀ 1.238)
        _g("a_25", "a", as_=25 / A0), _g("a_30", "a", as_=30 / A0),
        _g("tau_1.3", "tau", ts=1.3), _g("a_m1.14", "a", as_=1.69), _g("R_m1.14", "R", rs=1 / 1.69)]
GROUPS = {"1.335": ["tau_1.2", "th_x0.694", "R_x0.694"],
          "2.94": ["tau_m2.94", "a_m2.94", "t1.0_h1.5_cv", "R_m2.94"],
          "3.92": ["t0.7_h1.0_cv", "a_m3.92", "th_x2.04"],
          "7.69": ["t0.5_h1.0_cv", "a_m7.69", "th_x4"],
          "1.14": ["tau_1.3", "a_m1.14", "R_m1.14"]}
SUB_RHO0 = ["tau_1.3", "a_m1.14", "R_m1.14"]
DIRECTION = {"2.94": ("a_m2.94", "tau_m2.94"), "3.92": ("a_m3.92", "t0.7_h1.0_cv"),
             "7.69": ("a_m7.69", "t0.5_h1.0_cv")}
SPREAD_TICKS = 1.5       # 1 tick + 정수 중앙값 반올림 허용 (R 계열 N∞ 4.2 → 기준 tick 환산 최대 ~1.34; 봉인 전 합성 점검)


def rho(g):
    th = TH0 * g["hs"]
    return RMAX * g["rs"] * math.tan(th) / (0.5 * A0 * g["as"] * (TAU0 * g["ts"]) ** 2)


def rho0(g):
    th = TH0 * g["hs"]
    return 1 / math.cos(th) + math.tan(th)


def n_inf(g):
    return RMAX * g["rs"] / (V_BAR * DT)


def build() -> dict:
    grid = [{**g, "rho": round(rho(g), 4), "rho0": round(rho0(g), 4), "n_inf": round(n_inf(g), 4),
             "R_max": round(RMAX * g["rs"], 3), "a_att": round(A0 * g["as"], 3),
             "tau": round(TAU0 * g["ts"], 4), "theta_deg": round(math.degrees(TH0 * g["hs"]), 3)} for g in GRID]
    body = {
        "schema": "fs1-e4-manifest-v1",
        "status": ("sealed 2026-10-11 BEFORE any E4 run (contract: docs/133; user 'start now' 2026-10-11; "
                   "design = advisor 2026-10-11 Q4: matched-rho points + rho0-neighbourhood points, "
                   "normalized collapse coordinates, separate direction prediction, judge-leniency read)"),
        "lineage": {"protocol": "E7-a (fs1_e7_manifest e7a 3a8c066156b6972e): m0.35_n1, 4 old-world adapted "
                                "attackers x 24 eps, SEED0 268000, no-fire, slew-simulated aim, window = "
                                "LOADED and d <= 16 m; + --coop (limiter-free judge recompute)",
                    "p_rho2": "rho0 = sec+tan, N = N_inf (1 - rho0/rho)+, N_inf = R_max/(V dt), V = 23.01"},
        "question": ("is the probe window governed by rho along ALL four knob directions (tau, a, theta, "
                     "R_max) or only along tau/theta (where every prior point came from)"),
        "grid": grid, "groups": GROUPS, "aim": "cv only",
        "knob_semantics": ("tau, theta: net-side judge arguments (as E7-a). a: the judge's ASSUMED attacker "
                           "capability only — the flying attacker keeps a = 20.45 (old-world adapted). R: "
                           "judge range_max; R <= 12.6 m keeps the 16 m window cut non-binding (R family "
                           "stops at rho 2.94 for that reason)"),
        "metric": ("window = per-episode robust ticks (limiters present, E7-a metric); variant value = "
                   "median over the 4 slot medians. nu = window / N_inf(variant)"),
        "predictions": {
            "P-E4a collapse": (f"per group: residual r = nu_obs - (1 - rho0(theta)/rho)+; spread "
                               f"(max r - min r) x N_inf(base) <= {SPREAD_TICKS} tick -> group collapses. "
                               "All 5 groups -> COLLAPSE_SUPPORTED; >= 3 -> COLLAPSE_PARTIAL; else "
                               "COLLAPSE_NOT_SUPPORTED. Departing family and sign reported"),
            "P-E4b direction": ("at rho 2.94 / 3.92 / 7.69: window(a family) >= window(tau family) on >= 2 "
                                "of 3 -> SUPPORTED (slew load a*tau ~ sqrt(a) at equal a*tau^2; lead v*tau "
                                "unchanged in the a family)"),
            "P-E4c judge leniency": ("sub-rho0 points (tau_1.3, a_m1.14, R_m1.14; rho 1.138 < 1.238): "
                                     "LIMITER-FREE robust ticks (rbf) total = 0 -> JUDGE_CONSERVATIVE_AT_"
                                     "BOUNDARY; > 0 -> JUDGE_LENIENT with the share of window ticks "
                                     "(finite-witness approximation; K1 A1 direction). Limiter-present ticks "
                                     "reported separately (limiter closure is not leniency)"),
            "report": "rho0-neighbourhood a_25 / a_30 / tau_1.2 vs N_pred; all residuals",
        },
        "consequence": ("COLLAPSE_SUPPORTED -> 'rho governs the probe window along tau, a, theta, R (first "
                        "order)'; otherwise the governing claim is restricted to the collapsing families. "
                        "JUDGE_LENIENT -> the 'guaranteed-capture lower bound' wording becomes 'under the "
                        "finite-witness judge' with the measured leniency (advisor 2026-10-11)"),
        "not_evidence_for": ["threat-class behavior (a family = judge assumption only)", "learned ceilings",
                             "blind prediction (rho0/N formula registered after E7-a)"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E4 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for g in build()["grid"]:
        print(f"{g['name']:13s} {g['family']:5s} rho {g['rho']:7.3f} rho0 {g['rho0']:.3f} "
              f"tau {g['tau']} th {g['theta_deg']} a {g['a_att']} R {g['R_max']}")
    print(MANIFEST, build()["manifest_hash"])
