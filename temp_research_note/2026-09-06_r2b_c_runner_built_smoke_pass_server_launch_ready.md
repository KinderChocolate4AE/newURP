# 2026-09-06 — R2b C arm 러너 구축 완료: bit-parity + 결정론 smoke PASS, 서버 투입 준비

구현 세션 (판정 없음 — C 결과는 아직 없다). B0 v2 `cba024d7ee3d9f61` arms.C +
branch seal `f1bd9a459d97e693` (FULL_28x100 lite) 의 기계 이행.

## 구현

- **`shepherd/scripts/r2b_c_runner.py`** (신규):
  - `solve_scenario`: s0=0 full-episode limiter plan (K_SEG=4 piecewise-constant),
    CEM P=64 × I=2 × elite16 × solver seed {0,1,2} = **384 lite rollouts/scenario**
    (§7.1 상수를 `recoverability_probe` 에서 import — 복제 없음, benchmark 비용
    기반과 동일). 구조 후보 {intercept, hold} 1세대 포함 → **rule-based B 는
    search class 의 원소** (C 가 B 를 구조적으로 놓칠 수 없음).
  - rollout = 경량 클론 env (viability.n_samples=16) 1개 재사용, proxy 선택 전용.
    **판정 = full-fidelity env 1회 replay 라벨만**: C_N = (label == NET_CAPTURE),
    CAPTURE_WITH_CONTACT·HARD_KILL 불인정 (Phase 1 판독과 동일 판정층). C_H/C_U
    같은 replay 에서 secondary.
  - proxy = C_N-지향 lexicographic: NET_CAPTURE ≻ capture(접촉 포함) ≻ 비침투 ≻
    clean crossings ≻ −contact_steps. 후보 선택 전용 (P83g 분리 계승).
  - solver RNG = `default_rng([20260906, seed, s])` — scenario CRN (SHA-256,
    ns r2b_p1_v2) 과 완전 분리.
  - S_C = 셀별 S_AB_v2[0:100] (28×100=2,800). 8샤드, scenario 당 incremental
    save, shard manifest 에 b0_hash + branch_hash + code_commit + solver_ns.
  - seal assert: branch_hash 일치 + B0 v2 의 inherited_by_reference 일치 +
    selected_C_design == FULL_28x100. q_dec=1/6 assert 는 scenario_kwargs 경유.
- **`r2b_phase1.py` 리팩토링** (행동 보존): slice 구현 2종 + scenario→kwargs
  구성을 `_slices()`/`scenario_kwargs()` 로 추출 — Phase 1 과 C 가 단일 정의원
  공유. tests/test_r2a.py 28 green 유지.
- rollout 은 `run_episode` 를 그대로 호출 (plan 은 policy 콜러블로 주입, finisher
  는 scripted_roles 로 유지) — 스텝 규약 복제 없음. env 재사용 시 유일한
  cross-episode 상태 `_last_v_shot_soft` 를 rollout 전 None 복원 (`_fresh`).

## Smoke (로컬, 전부 PASS)

1. **bit-parity**: scenario {0, 2403, 10899} (셀 0/6/27) 재구성 → hold/intercept
   라벨·fire_step·steps 가 Phase 1 v2 shard 기록과 정확 일치 + chi/eta CRN 일치.
   → C 의 scenario 구성 경로 = A/B stream 과 동일함이 기계 증명됨.
2. **env-재사용 결정론**: 경량 env 에서 hold → 임의 plan 2개 → hold 재실행
   bit 동일 (label/steps/fire_step/clean_crossings/contact_steps/min_dist).
3. **plan-policy 배선**: accels 후보 정상 종료.
4. **full solve 1판** (비-S_C scenario s=100, SMOKE ONLY — inference 제외):
   전체 CEM+replay 경로 무오류 — 336s/solve (로컬), rollouts=384 (봉인 예산
   정확 일치), plan_kind=accels. 서버 t_lite 89.6s 기준 T_proj 8.71h 불변.

## 서버 투입 (사용자 트랙)

서버 (/data/hjhong/l2/newURP, .venv-l2) 에서 순서대로:

```bash
# 0) pull 후 서버에서도 smoke 필수 (bit-parity 는 머신별 재확인)
python -m shepherd.scripts.r2b_c_runner --smoke
# 1) tmux 8샤드 (T_proj ≈ 8.7 h) + ntfy hj_URP_x7k2q9
for K in 0 1 2 3 4 5 6 7; do
  tmux new-session -d -s r2bc$K \
    "python -m shepherd.scripts.r2b_c_runner --run --shard $K --n-shards 8"
done
```

산출 = `artifacts/r2b/c_arm/shard00..07.json` (2,800 records). 중단 시 같은
명령 재실행 → shard 파일에서 resume.

## 다음 수

1. C 샤드 회수 → **C 판독기** (B0 v2 3-way 봉인 문장 기계 적용: (B_N, C_N) 표 +
   C_U/C_H secondary + p_C_hat estimand 문구) → R2b 종결 감사 브리프 (txt).
2. 대기열 불변: q_dec 1/12 mini-map → OAT screen → prop1 (K1 ≤10/31) → 6DOF gate.

## 주의 (열 때)

- C 결과 해석 재량 없음 — 3-way 문장은 B0 v2 readout_3cases 에 이미 봉인.
  C_N positive 라도 "upper bound" 어휘 금지 (retired), "search-based
  achievability benchmark" 만.
- 1판 smoke solve 는 비-S_C scenario — inference 에 절대 포함 금지.
