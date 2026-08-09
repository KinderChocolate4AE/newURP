"""Phase III 게이트 1 — Buckingham-Π 전체 도출 + master lattice `Z_master` 선봉인.

    python -m shepherd.scripts.lattice_spec --out artifacts/phase3/lattice_spec.json

왜 (docs/74 r3.2 §3.8·§3.9)
---------------------------
- **`Z_master` 선봉인**: adaptive refinement 는 "다음에 **어느 master 점**을 계산할지"
  만 고른다. 격자 자체를 결과 보고 늘리면 hypothesis-space 를 결과로 만든 것이다.
  그래서 격자를 **지도 셀 0 개인 지금** 확정하고 `lattice_hash` 를 manifest 에 넣는다.
- **Π 는 결과 전에 분석적으로 전부 도출**한다. core = plotted axes 2~3 개,
  나머지는 **fixed conditioning variables**. iso-Π test 는 축 발견법이 아니라
  **reduction validation** 이다. 결과를 보고 축을 추가하지 않는다 — 필요하면
  현 Phase III 를 종료하고 Phase III-B 를 새 hash 로 시작한다.

무차원군 (질점 3D · 단발 net · 전개지연 tau · kill 구 · SE(3) 원뿔)
------------------------------------------------------------------
길이 스케일은 `rho_net`, 시간 스케일은 `tau` 로 잡는다.

    chi    = a_att * tau^2 / (2 * rho)      공격자 회피 변위 / net 반경   [core]
    kappa  = r_kill / rho                   봉쇄 도구 크기 / net 반경     [core]
    mu     = a_lim / a_att                  요격기 기동 비                [core]
    eta    = v_att * tau / rho              접근 변위 / net 반경
    nu     = v_lim / v_att                  속도 비
    lam    = L_axial / rho                  원뿔 축 밴드 / net 반경
    alpha  = cone half-angle                (그 자체로 무차원)
    sig_sb = R_standby / rho                초기 배치 반경 / net 반경
    sig_dt = R_detect / rho                 감지 반경 / net 반경
    sig_as = D_asset / rho                  자산까지 거리 / net 반경
    N      = limiter 수                     (이산)
    dt_tau = dt / tau                       **수치 검증수** (물리 파라미터 아님)

★ 주의 (docs/74 §3.9): `lam`, `sig_*` 는 절대값을 고정한 채 `rho` 를 바꾸면
**자동으로 변한다.** 따라서 core Π 만 같고 이들이 다른 두 시스템의 결과가 다른 것은
당연할 수 있다 — collapse 실패의 근거로 쓰기 전에 conditioning 변수를 먼저 확인한다.

torch-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np

from shepherd.m4_config import CAPABILITY_RATIOS, THREAT_BRACKET, m4_config
from shepherd.scripts.pivot_manifest import stamp

__all__ = ["PI_GROUPS", "CORE_AXES", "AXIS_GRID", "N_GRID_DISCRETE",
           "build_lattice", "nominal_pi"]

# ── Π 전체 목록 (결과 전 확정. 이후 추가 금지) ───────────────────────────────
PI_GROUPS = {
    "chi":    "a_att * tau^2 / (2 * rho_net)",
    "kappa":  "r_kill / rho_net",
    "mu":     "a_lim_max / a_att_max",
    "eta":    "att_speed * tau / rho_net",
    "nu":     "limiter_v_max / att_speed",
    "lam":    "cone_range_max / rho_net",
    "alpha":  "cone half-angle [rad]",
    "sig_sb": "R_standby / rho_net",
    "sig_dt": "sense_range / rho_net",
    "sig_as": "D_asset / rho_net",
    "N":      "number of limiters (discrete)",
    "dt_tau": "dt / tau  (numerical verification number, not a design parameter)",
}
CORE_AXES = ("chi", "kappa", "mu")          # plotted axes (2~3). 나머지는 conditioning

# 격자 (결과 전 확정). chi 는 proxy 경계 1.0 을 가로지르도록, kappa·mu 는 설계 범위.
AXIS_GRID = {
    "chi":   [round(x, 3) for x in np.linspace(0.40, 2.00, 17)],   # 0.1 간격
    "kappa": [round(x, 3) for x in np.linspace(0.20, 1.20, 11)],   # r_kill/rho
    "mu":    [round(x, 3) for x in np.linspace(0.20, 1.00, 9)],    # a_lim/a_att
}
N_GRID_DISCRETE = [0, 1, 2, 4, 6]

# escalation 순서 (collapse 실패 시 **conditioning 확인용**. 축 추가가 아니다)
CONDITIONING_ORDER = ("eta", "alpha", "lam", "nu", "sig_sb", "sig_dt", "sig_as")


def nominal_pi() -> dict:
    """현 동결 파라미터에서의 Π 값 (지도 원점 표식 · conditioning 기본값)."""
    cfg = m4_config()
    ph, vb = cfg["physics"], cfg["viability"]
    cone = vb["cone"]
    rho, tau = float(ph["net_radius"]), float(ph["tau_deploy"])
    a_lo, a_hi = THREAT_BRACKET["physics.a_att_max"]
    v_lo, v_hi = THREAT_BRACKET["physics.att_speed"]
    a_mid, v_mid = (a_lo + a_hi) / 2, (v_lo + v_hi) / 2
    mu = float(CAPABILITY_RATIOS["physics.a_lim_max"][1])
    nu = float(CAPABILITY_RATIOS["train.limits.limiter_v_max"][1])
    out = {
        "chi_at_bracket_mid": round(a_mid * tau ** 2 / (2 * rho), 4),
        "chi_bracket": [round(a_lo * tau ** 2 / (2 * rho), 4),
                        round(a_hi * tau ** 2 / (2 * rho), 4)],
        "kappa": round(float(ph["kill_radius"]) / rho, 4),
        "mu": round(mu, 4), "nu": round(nu, 4),
        "eta_at_bracket_mid": round(v_mid * tau / rho, 4),
        "lam": round(float(cone["range_max"]) / rho, 4),
        "alpha_rad": round(float(cone["half_angle"]), 4),
        "dt_tau": round(float(ph["dt"]) / tau, 4),   # 선언은 physics.dt 한 곳뿐 (P40)
        "rho_net": rho, "tau": tau,
    }
    return out


def build_lattice() -> dict:
    pts = []
    for chi in AXIS_GRID["chi"]:
        for kappa in AXIS_GRID["kappa"]:
            for mu in AXIS_GRID["mu"]:
                for N in N_GRID_DISCRETE:
                    pts.append({"chi": chi, "kappa": kappa, "mu": mu, "N": N})
    payload = {
        "schema": "z-master-v1",
        "core_axes": list(CORE_AXES),
        "axis_grid": AXIS_GRID,
        "N_grid": N_GRID_DISCRETE,
        "n_points": len(pts),
        "pi_groups": PI_GROUPS,
        "conditioning_order": list(CONDITIONING_ORDER),
        "conditioning_fixed_at": "nominal (see nominal_pi)",
        "nominal_pi": nominal_pi(),
        "rules": [
            "adaptive refinement selects WHICH master point to evaluate next; "
            "it never creates new points (docs/74 §3.8)",
            "Stage-2 operating points are chosen only from this lattice",
            "iso-Pi tests are reduction validation, not axis discovery (§3.9)",
            "adding an axis requires terminating Phase III and registering "
            "Phase III-B under a new protocol hash",
        ],
    }
    payload["lattice_hash"] = hashlib.sha256(
        json.dumps({k: payload[k] for k in
                    ("schema", "core_axes", "axis_grid", "N_grid", "pi_groups")},
                   sort_keys=True).encode()).hexdigest()[:16]
    return payload


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Z_master + Buckingham-Pi 선봉인")
    ap.add_argument("--out", default="artifacts/phase3/lattice_spec.json")
    a = ap.parse_args(argv)
    spec = build_lattice()
    spec.update(stamp(artifact="phase3_lattice_spec",
                      lattice_hash=spec["lattice_hash"]))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
    n = spec["nominal_pi"]
    print(f"lattice_hash = {spec['lattice_hash']}  points = {spec['n_points']} "
          f"(chi {len(AXIS_GRID['chi'])} x kappa {len(AXIS_GRID['kappa'])} "
          f"x mu {len(AXIS_GRID['mu'])} x N {len(N_GRID_DISCRETE)})")
    print(f"nominal: chi(bracket) {n['chi_bracket']} · kappa {n['kappa']} · mu {n['mu']} "
          f"· nu {n['nu']} · lam {n['lam']} · alpha {n['alpha_rad']} rad · dt/tau {n['dt_tau']}")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
