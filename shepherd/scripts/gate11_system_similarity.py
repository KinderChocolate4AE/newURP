"""Phase III 게이트 11 — closed-loop (scripted) system similarity 복원·검증.

    python -m shepherd.scripts.gate11_system_similarity --run \
        --out results/phase3/gate11_system.json

배경 (docs/78 r2 addendum §A · docs/77 III-D)
---------------------------------------------
게이트 10 Tier 1 이 **T1-T.system FAIL** 을 냈고 원인은 동결 scripted attacker 의
하드코딩 전진 P-게인 `a_fwd = 4.0·(v_ref − v_fwd)` — 숨은 무차원군 **k_f·τ** 다.
게이트 11 은 이를 explicit dimensional parameter 로 승격한 뒤 full-system 상사성을
다시 falsify 한다. **게이트 10 의 T1-T.system FAIL 은 삭제하지 않고 보존한다**
(이 게이트는 그 실패의 수리 기록이지 은폐가 아니다).

절차 (docs/77 III-D 순서 그대로 — 결과 열람 전 고정)
----------------------------------------------------
1. **baseline regression** — 리터럴 4.0 → 모듈 상수 `attacker_ladder.FWD_GAIN`
   (기본값 동일). 승격 전후 거동이 bit-exact 인지 확인.
   ✅ 실행 완료 (2026-08-13): `results/phase3/gate11_baseline_regression.json`
   — 게이트 10 --tier1 재실행이 **전 수치 동일** (T1L dev 0.0 / T1T dev
   5.50e-01·8.08e-02·4.57e-01·8.68e-01·2.91e-01·1.86e+00, mask_mis 8·10·7·12·15·12).
2. **S-L regression** (α=2, β=1) — 길이 상사 exact PASS 유지 확인.
   FWD_GAIN 은 [1/T] 이라 β=1 에서 불변 ⇒ 결과가 게이트 10 T1-L 과 같아야 한다.
3. **S-T full-system falsification** (α=1, β=2) — `FWD_GAIN' = FWD_GAIN/β` 를
   적용하고 전 항목 비교: normalized state · engaged mask · witness mask ·
   boxed · v_shot. 판정 bar 는 docs/78 §1 승계 (|Δv_shot| ≤ 1e-6, 상태 dev ≤ 1e-6,
   predicate 불일치 0).
4. 또 다른 hidden 상수가 나오면 **FAIL 을 누적 기록**하고 동일 절차
   (식별 → explicit parameterization → 새 revision → 재시험) 를 반복한다.
   결과를 좋게 만드는 튜닝이 아니라 **dimensional consistency repair** 다.

주의: 상사성 "보장" 이라 쓰지 않는다 — 유한 시험이므로
*"tested transformations and registered parameter ranges 에서 검증됐다"* 까지.
Level 2 (registered scripted encounter similarity) 가 이 게이트의 목표이며,
Level 3 (learned-policy) 는 범위 밖 (후속 robustness).

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import shepherd.agents.attacker_ladder as AL
from shepherd.scale_v2 import draw_threat_v3
from shepherd.scripts.gate10_isopi import (
    EPISODES, TOL_V, Z_POINTS, _resolved_base_layout, build_world, compare,
    run_world)
from shepherd.scripts.measure_harness import _lattice_hash
from shepherd.scripts.pivot_manifest import stamp

TRANSFORMS_G11 = {"S-L": (2.0, 1.0), "S-T": (1.0, 2.0)}


def run_world_scaled(st, z, alpha, beta, **kw):
    """스케일된 계의 rollout — FWD_GAIN [1/T] 을 1/beta 로 스케일해 적용."""
    old = AL.FWD_GAIN
    AL.FWD_GAIN = old / beta
    try:
        return run_world(st, z, alpha, beta, **kw)
    finally:
        AL.FWD_GAIN = old


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Gate 11 system similarity")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", default="results/phase3/gate11_system.json")
    a = ap.parse_args(argv)
    if not a.run:
        ap.error("--run 필요")

    base_lay = _resolved_base_layout(draw_threat_v3(0, 0, "train")["cfg"])
    results, all_pass = [], True
    for name, (alpha, beta) in TRANSFORMS_G11.items():
        for z in Z_POINTS:
            for ep in EPISODES:
                stA = build_world(z, ep, 1.0, 1.0, base_lay)
                stB = build_world(z, ep, alpha, beta, base_lay)
                rA = run_world(stA, z, 1.0, 1.0)                  # base: FWD_GAIN 원값
                rB = run_world_scaled(stB, z, alpha, beta)        # scaled: /beta
                c = compare(rA, rB)
                c.update(transform=name, z=z, ep=int(ep),
                         fwd_gain_base=AL.FWD_GAIN,
                         fwd_gain_scaled=AL.FWD_GAIN / beta)
                results.append(c)
                all_pass &= c["pass"]
                print(f"{name} chi {z['chi']} ep {ep}: steps {c['n_steps_base']} "
                      f"eng {c['n_engaged']} | state_dev {c['max_state_dev']:.2e} "
                      f"dv {c['max_dv']:.2e} mask_mis {c['mask_mismatch']} "
                      f"eng_mis {c['engaged_mismatch']} -> "
                      f"{'PASS' if c['pass'] else 'FAIL'}", flush=True)

    print("GATE11:", "PASS" if all_pass else "FAIL")
    out = dict(
        contract_doc="docs/78 r2 addendum §A · docs/77 III-D (게이트 11)",
        note=("게이트 10 의 T1-T.system FAIL 은 보존된다. 이 게이트는 그 실패의 "
              "dimensional-consistency repair 기록이다. 상사성 '보장' 이 아니라 "
              "tested transformations · registered ranges 에서의 검증."),
        step1_baseline_regression="results/phase3/gate11_baseline_regression.json (bit-exact)",
        transforms={k: list(v) for k, v in TRANSFORMS_G11.items()},
        z_points=Z_POINTS, episodes=list(EPISODES), tol_v=TOL_V,
        results=results, gate11_pass=bool(all_pass),
        **stamp(artifact="phase3_gate11_system", lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
