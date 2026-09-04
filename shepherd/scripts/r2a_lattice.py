"""paper-R2a lattice — 격자·구현 5종·support·tau_B 선택 게이트·ledger (봉인 정본).

    python -m shepherd.scripts.r2a_lattice --stage0 artifacts/r2a/stage0_envelope.json

설계 브리프 = docs/review_prompt_r2a_parameterization.txt (r3 + r4 부록 §10). 이 모듈은
**에피소드 데이터를 읽지 않는다** — Stage 0 산출물 (envelope + hash) 만 받아 봉인에 넣는다.

r4 (2026-09-05, Stage 0 판독 반영):
  C. delta_p 와 delta_chi 는 **별도 estimand** — slope 연동 역산 폐기. delta_chi 는 "R2b
     하류 regime 분류를 바꾸지 않는 최대 경계 이동" 으로 정의 (0.05). boundary 측정용
     micro-grid (chi50±W, step 0.02) 를 full-map grid (step 0.04) 와 분리 — chi50 정밀도가
     map 간격에 묶이지 않고, tau_B 게이트도 map 간격에 걸리지 않는다.
  B. 계약 2종 분리 (별도 hash, pooling 금지):
     R2a-L  legacy a∈[11,78]  — R-ref full map + legacy 내부 최대 교란 (tau 0.375) 방향 확인
     R2a-P  pin-확장 a∈[a_min,78] — strict similarity/robustness 식별용, tau_B 0.45 복구.
            a_min 은 후보 {7, 6} 중 support buffer H ≥ max(delta_chi, 2·step_micro) = 0.05
            를 만족하는 최대값으로 기계 선택 (Stage 0 기준 6; 7 은 H 0.043 reject).
     a<11 은 위협 대표성 주장이 아니라 공통 무차원 support 를 위한 controlled perturbation.
  ledger: 무차원군 (tau_lock/tau, tau_kill/tau, omega·tau, dx/rho, r_lat/rho, x0/rho, kappa,
     dt/tau, k_f·tau, lam, alpha) 을 **주입 차원값에서 계산**해 SIM 전부 invariant /
     DOM target 만 이동을 assert. R-tau-DOM target = {k_f·tau} 가 비지 않음을 보장.

좌표: chi = a·tau²/(2rho), eta = v·tau/rho (lattice_spec.PI_GROUPS 와 동일 정의).
세계 = legacy 24 m 회랑, rho_ref 1.77 / tau_ref 0.30. torch-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib

from shepherd.m4_config import THREAT_BRACKET, m4_config

__all__ = ["CONTRACTS", "CHI_GRID", "ETA_GRID", "DELTA_P", "DELTA_CHI", "W_BOUNDARY",
           "CHI_STEP_BOUNDARY", "chi_eta", "dims_from", "support", "common_support",
           "impls", "micro_grid", "select_tau_b", "ledger", "build_lattice"]

# ── 기준 차원값 (동결 m4_config 와 일치해야 한다 — build 시 assert) ────────────
RHO_REF, TAU_REF, DT_REF = 1.77, 0.30, 0.05
K_F_REF = 4.0                       # adversary.fwd_gain [1/s] (params.py:272)
R_MAX_REF = 8.22                    # viability.cone.range_max [m]
A_BR, V_BR = THREAT_BRACKET["physics.a_att_max"], THREAT_BRACKET["physics.att_speed"]
RHO_B = 2.30
TAU_B_FLOOR_RATIO = 1.25

# ── full-map 격자 (Stage 2, R-ref): chi 12 × eta 7 ─────────────────────────────
CHI_STEP, ETA_STEP = 0.04, 0.30
CHI_GRID = [round(0.41 + CHI_STEP * i, 3) for i in range(12)]   # 0.41 … 0.85
ETA_GRID = [round(2.1 + ETA_STEP * i, 3) for i in range(7)]     # 2.1 … 3.9

# ── boundary micro-grid (Stage 1/3): chi50^(0)(eta) ± W, step 0.02 (11점) ───────
W_BOUNDARY, CHI_STEP_BOUNDARY = 0.10, 0.02

# ── 판정 margin (r4-C: 별도 estimand) ───────────────────────────────────────────
DELTA_P = 0.10      # probability robustness: paired CI95(Δp) ⊂ ±delta_p
DELTA_CHI = 0.05    # boundary displacement that would change downstream R2b regime assignment

# ── support buffer 기준 (r4-B'): envelope+headroom 바깥에 FAIL 도 관측 가능한 여유 ─
H_SUPPORT_MIN = max(DELTA_CHI, 2 * CHI_STEP_BOUNDARY)          # = 0.05
A_MIN_CANDIDATES_P = (7.0, 6.0)   # 사전 후보 (내림차순 = 최소 확장 우선)

# ── 계약 2종 (r4-B). a_min 만 다르다; v bracket 은 공통 ─────────────────────────
CONTRACTS = {
    "R2a-L": {"a_min_candidates": (A_BR[0],),
              "role": "legacy threat regime; R-ref full map + directional check at the "
                      "largest legacy-admissible tau (not confirmatory)",
              "tau_candidates": (0.45, 0.425, 0.40, 0.375)},
    "R2a-P": {"a_min_candidates": A_MIN_CANDIDATES_P,
              "role": "pin-extension for similarity/robustness identification; not pooled "
                      "with R2a-L; no threat-prevalence claim. a_min = largest candidate whose "
                      "support buffer H >= H_SUPPORT_MIN at its selected tau_B",
              "tau_candidates": (0.45, 0.425, 0.40, 0.375)},
}
DELTA_CHI_RATIONALE = ("R2b places boundary-adjacent chi coordinates ~0.1 apart; a chi50 shift "
                       "larger than 0.05 re-assigns a treatment's regime. NOT slope-derived "
                       "(Stage 0 showed a step-like transition, which makes slope-linked "
                       "delta_chi ~0.01 and untestable at planned n).")


def chi_eta(a: float, v: float, tau: float, rho: float) -> tuple[float, float]:
    return a * tau * tau / (2.0 * rho), v * tau / rho


def dims_from(chi: float, eta: float, tau: float, rho: float) -> tuple[float, float]:
    """(chi, eta) → (a, v). chi_eta 의 역함수 (paired CRN 의 차원값 역산)."""
    return chi * 2.0 * rho / (tau * tau), eta * rho / tau


def support(tau: float, rho: float, a_min: float = A_BR[0]) -> dict:
    """bracket a∈[a_min, 78], v∈[8,30] 유지 시 구현의 (chi, eta) 유효 support."""
    c_lo, e_lo = chi_eta(a_min, V_BR[0], tau, rho)
    c_hi, e_hi = chi_eta(A_BR[1], V_BR[1], tau, rho)
    return {"chi": [c_lo, c_hi], "eta": [e_lo, e_hi]}


def common_support(*sups: dict) -> dict:
    return {k: [max(s[k][0] for s in sups), min(s[k][1] for s in sups)]
            for k in ("chi", "eta")}


def impls(tau_b: float) -> dict:
    """구현 5종 (브리프 §4.1). SIM = 전 차원변수 co-scale, DOM = target 만 이동.
    R_max: SIM-rho 는 co-scale, DOM-rho 는 기준값 유지 (→ lam, alpha 이동)."""
    r = RHO_B / RHO_REF
    return {
        "R-ref":     dict(tier="A", tau=TAU_REF, rho=RHO_REF, k_f=K_F_REF, R_max=R_MAX_REF, target=[]),
        "R-tau-SIM": dict(tier="A", tau=tau_b, rho=RHO_REF, k_f=K_F_REF * TAU_REF / tau_b,
                          R_max=R_MAX_REF, target=[]),
        "R-rho-SIM": dict(tier="A", tau=TAU_REF, rho=RHO_B, k_f=K_F_REF, R_max=R_MAX_REF * r, target=[]),
        "R-tau-DOM": dict(tier="B", tau=tau_b, rho=RHO_REF, k_f=K_F_REF, R_max=R_MAX_REF,
                          target=["k_f_tau"]),
        "R-rho-DOM": dict(tier="B", tau=TAU_REF, rho=RHO_B, k_f=K_F_REF, R_max=R_MAX_REF,
                          target=["alpha", "lam"]),
    }


def _inject(im: dict) -> dict:
    """하네스에 주입해야 하는 차원값 전부 (a=6~7 hidden-branch 감사에서 드러난 시간·길이
    상수 포함). target 외 항목은 SIM/DOM 공통 co-scale — 하나라도 빠지면 미등록 pi 누수."""
    s, r = im["tau"] / TAU_REF, im["rho"] / RHO_REF
    return {"dt": DT_REF * s, "tau_lock": 0.10 * s, "tau_kill": 0.15 * s,
            "omega_aim": 3.14159 / s, "omega_att_slew": 8.0 / s, "k_f": im["k_f"],
            "R_max": im["R_max"], "spawn_dx": 2.0 * r, "spawn_r_lat": 5.0 * r,
            "adversary_start_x": 24.0 * r, "kill_radius": 0.75 * r}


def _pins(im: dict) -> dict:
    """구현의 무차원군 — **주입 차원값에서 계산**하므로 ledger 의 invariance assert 가
    "원시값을 같이 바꿨다" 가 아니라 "무차원량이 실제로 불변" 임을 직접 검사한다.
    mu, nu 는 CAPABILITY_RATIOS 로 구조적 고정 (a_att, att_speed 비례)."""
    j, tau, rho = _inject(im), im["tau"], im["rho"]
    lam = j["R_max"] / rho
    return {"lam": lam, "alpha": math.atan(1.0 / lam), "k_f_tau": j["k_f"] * tau,
            "dt_tau": j["dt"] / tau, "tau_lock_tau": j["tau_lock"] / tau,
            "tau_kill_tau": j["tau_kill"] / tau, "omega_aim_tau": j["omega_aim"] * tau,
            "omega_slew_tau": j["omega_att_slew"] * tau, "dx_rho": j["spawn_dx"] / rho,
            "r_lat_rho": j["spawn_r_lat"] / rho, "x0_rho": j["adversary_start_x"] / rho,
            "kappa": j["kill_radius"] / rho}


def micro_grid(chi50: float) -> list[float]:
    """boundary micro-grid: Stage 0 chi50 을 0.01 로 반올림한 중심 ± W, step 0.02 (11점)."""
    c = round(chi50, 2)
    n = int(round(W_BOUNDARY / CHI_STEP_BOUNDARY))
    return [round(c + CHI_STEP_BOUNDARY * i, 3) for i in range(-n, n + 1)]


def select_tau_b(envelope: dict, a_min: float, candidates=(0.45, 0.425, 0.40, 0.375),
                 headroom: float = CHI_STEP_BOUNDARY) -> dict:
    """브리프 §4.4 게이트 (r4: headroom = boundary step, map 간격과 무관).
    envelope = {eta: [chi_lo, chi_hi]} = micro-grid 범위 (censored 행 제외). 규칙:
    envelope 전체 + headroom 이 R-ref/R-tau/R-rho 공통 support 내부인 **가장 큰** tau_B.
    전부 실패 → D-1 (NON_IDENTIFIABLE within this contract)."""
    rows = {float(k): v for k, v in envelope.items()}
    trace = []
    for tb in candidates:
        assert tb / TAU_REF >= TAU_B_FLOOR_RATIO - 1e-12, tb
        cs = common_support(support(TAU_REF, RHO_REF, a_min), support(tb, RHO_REF, a_min),
                            support(TAU_REF, RHO_B, a_min))
        bad = sorted(e for e, (lo, hi) in rows.items()
                     if not (cs["eta"][0] <= e <= cs["eta"][1]
                             and lo - headroom >= cs["chi"][0]
                             and hi + headroom <= cs["chi"][1]))
        trace.append({"tau_B": tb, "common_support": cs, "rows_failing": bad,
                      "min_margin_chi": min((lo - headroom - cs["chi"][0] for lo, _ in rows.values()),
                                            default=float("nan"))})
        if rows and not bad:
            return {"tau_B": tb, "verdict": "SELECTED", "trace": trace}
    return {"tau_B": None, "verdict": "D-1 NON_IDENTIFIABLE", "trace": trace}


def select_a_min(envelope: dict, candidates, tau_candidates) -> dict:
    """r4-B': 후보 중 **가장 큰** a_min (최소 확장) 으로서, 그 a_min 에서 선택된 tau_B 의
    support buffer H = min_eta (B_lo − headroom − chi_min,common) 가 H_SUPPORT_MIN 이상인
    것. 근거: equivalence margin 크기만큼의 buffer 가 있어야 PASS 뿐 아니라 FAIL 도
    censoring 없이 관측된다. 전부 실패 → 마지막 후보로 D-1 경로."""
    trace = []
    for am in candidates:
        g = select_tau_b(envelope, am, tau_candidates)
        H = next((t["min_margin_chi"] for t in g["trace"] if t["tau_B"] == g["tau_B"]),
                 float("nan"))
        ok = g["tau_B"] is not None and H >= H_SUPPORT_MIN
        trace.append({"a_min": am, "tau_B": g["tau_B"], "H_support": H, "accept": ok})
        if ok:
            return {"a_min": am, "gate": g, "H_support": H, "trace": trace}
    return {"a_min": candidates[-1], "gate": select_tau_b(envelope, candidates[-1], tau_candidates),
            "H_support": trace[-1]["H_support"], "trace": trace}


def ledger(tau_b: float, a_min: float, cells: list[tuple[float, float]]) -> list[dict]:
    """구현 × 셀당 1행 (§4.3). 자동 검증: SIM 행은 전 pi invariant, DOM 행은 target 만
    이동 — R-tau-DOM 이 SIM 으로 새는 누수 (dt·k_f 항등식) 의 방어선."""
    ims = impls(tau_b)
    ref = _pins(ims["R-ref"])
    rows = []
    for name, im in ims.items():
        pi = _pins(im)
        moved = sorted(k for k in pi if abs(pi[k] - ref[k]) > 1e-9)
        assert moved == im["target"], (name, moved, im["target"])
        inject = _inject(im)
        for chi, eta in cells:
            a, v = dims_from(chi, eta, im["tau"], im["rho"])
            rows.append({"impl": name, "tier": im["tier"], "chi": chi, "eta": eta,
                         "a_att": a, "att_speed": v, "tau": im["tau"], "rho": im["rho"],
                         "inject": inject, "pi": pi, "target": im["target"],
                         "in_bracket": a_min <= a <= A_BR[1] and V_BR[0] <= v <= V_BR[1]})
    return rows


def build_lattice(stage0_path: pathlib.Path, contract: str) -> dict:
    cfg = m4_config()
    assert (cfg["physics"]["net_radius"], cfg["physics"]["tau_deploy"],
            cfg["physics"]["dt"], cfg["viability"]["cone"]["range_max"]) == \
        (RHO_REF, TAU_REF, DT_REF, R_MAX_REF)
    ct = CONTRACTS[contract]
    st0 = json.loads(stage0_path.read_text(encoding="utf-8"))
    sel = select_a_min(st0["envelope"], ct["a_min_candidates"], ct["tau_candidates"])
    a_min, gate = sel["a_min"], sel["gate"]
    ct = dict(ct, a_min=a_min)
    tb = gate["tau_B"]
    if tb is None and contract == "R2a-L":
        # legacy 내부 방향 확인은 floor 후보로 강행 (confirmatory 아님) — 탈락 행은 기록
        tb, gate["directional_only"] = ct["tau_candidates"][-1], True
    boundary_cells = [(c, float(e)) for e, (lo, hi) in st0["envelope"].items()
                      for c in micro_grid((lo + hi) / 2)]
    map_cells = [(c, e) for c in CHI_GRID for e in ETA_GRID]
    payload = {
        "schema": "r2a-lattice-v2", "contract": contract, "a_min": ct["a_min"], "role": ct["role"],
        "world": "legacy 24 m corridor; threat A1; fixed capability-ratio family (mu, nu pinned)",
        "pooling": "R2a-L and R2a-P are separate estimates; never pooled",
        "map_grid": {"chi": CHI_GRID, "eta": ETA_GRID, "chi_step": CHI_STEP, "eta_step": ETA_STEP,
                     "stage": 2, "impl": "R-ref only"},
        "boundary_grid": {"per_eta": {e: micro_grid((lo + hi) / 2) for e, (lo, hi) in st0["envelope"].items()},
                          "W": W_BOUNDARY, "chi_step": CHI_STEP_BOUNDARY, "stage": [1, 3]},
        "a_min_selection": {"candidates": list(ct["a_min_candidates"]), "H_support_min": H_SUPPORT_MIN,
                            "rule": "largest a_min with H_support >= max(delta_chi, 2*chi_step_boundary)",
                            "H_support": sel["H_support"], "trace": sel["trace"]},
        "margins": {"delta_p": DELTA_P, "delta_chi": DELTA_CHI, "delta_chi_rationale": DELTA_CHI_RATIONALE,
                    "rule": "cell: paired CI95(dp) in ±delta_p (PASS/INCONCLUSIVE/FAIL); global: "
                            "D_chi simultaneous band upper <= delta_chi over usable (uncensored) eta rows"},
        "ref": {"rho": RHO_REF, "tau": TAU_REF, "dt": DT_REF, "k_f": K_F_REF, "R_max": R_MAX_REF,
                "bracket_a": [ct["a_min"], A_BR[1]], "bracket_v": list(V_BR)},
        "tau_B_gate": gate, "tau_B": tb, "rho_B": RHO_B,
        "stage0_hash": st0["hash"],
        "stage0_status": "exploratory/design data — not evidence; hash sealed here",
        "impls": impls(tb),
        "estimand": "hold-arm net capture p on (chi, eta); mu, nu fixed = capability-ratio family map",
        "vocab": {"H-SIM": "consistent with dimensional similarity",
                  "H-DOM": "boundary robust to the declared perturbations"},
        "registry": {"C044": "chi50(eta) + simultaneous band",
                     "C045": ["PASS_2D", "PARTIAL_3D", "FAIL", "NON_IDENTIFIABLE"],
                     "C046": "provenance + legacy corridor / A1 / capability-ratio caveat"},
    }
    payload["lattice_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    payload["ledger"] = ledger(tb, ct["a_min"], boundary_cells + map_cells)
    return payload


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage0", default="artifacts/r2a/stage0_envelope.json")
    ap.add_argument("--outdir", default="artifacts/r2a")
    a = ap.parse_args(argv)
    for name in CONTRACTS:
        lat = build_lattice(pathlib.Path(a.stage0), name)
        p = pathlib.Path(a.outdir) / f"lattice_{name.replace('-', '_')}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(lat, indent=1, ensure_ascii=False), encoding="utf-8")
        g = lat["tau_B_gate"]
        print(f"[{name}] a_min {lat['a_min']}  lattice_hash {lat['lattice_hash']}  "
              f"tau_B {lat['tau_B']}  {g['verdict']}  H_support {lat['a_min_selection']['H_support']:+.3f}"
              f"{'  (directional only)' if g.get('directional_only') else ''}")
        for t in lat["a_min_selection"]["trace"]:
            print(f"    a_min {t['a_min']}: tau_B {t['tau_B']} H {t['H_support']:+.3f} "
                  f"{'ACCEPT' if t['accept'] else 'reject'}")
        for t in g["trace"]:
            cs = t["common_support"]
            print(f"    tau_B {t['tau_B']}: common chi [{cs['chi'][0]:.3f},{cs['chi'][1]:.3f}] "
                  f"eta [{cs['eta'][0]:.3f},{cs['eta'][1]:.3f}]  min margin {t['min_margin_chi']:+.3f}"
                  f"  failing eta rows {t['rows_failing']}")
        print(f"    -> {p}")


if __name__ == "__main__":
    main()
