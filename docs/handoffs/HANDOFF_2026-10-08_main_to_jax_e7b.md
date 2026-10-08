# HANDOFF — main → JAX 세션: E7-b 생산 발사 (2026-10-08)

**E7-b addendum 봉인 완료 (`docs/129 §6`, manifest `65ef3b86715458fa`) + canonical 변형
랜딩 완료 (`ce04f1c`)** — 학습 발사를 지시한다. P-ρ2 는 사전 등록됨 (ρ* 2.813, 노트
10-08c — 무플래그).

## canonical 랜딩 요지 (미러 대상)

- `FS1Spec(tau_scale, theta_scale, aim)` 3 손잡이 (`shepherd/fs1/world.py`):
  ① τ = `physics.tau_deploy` **config 단일 소스** 배율 → env.tau_deploy + FSM dep 타이머
  동시 전파 (**risk① 해소 — 테스트 `test_tau_single_source_propagates_both` 가 증명**)
  ② θ = `inn.cone_half_angle` 배율 ③ aim="ma" = FCS `fcs()` 의 nc += ½·â·τ², â = 공격자
  속도 유한차분 (reset 시 None, a_att_max norm-clip) — witness/판정 불변, 조준점만.
- 기본값 (1.0/1.0/cv) = bit-exact no-op (테스트 4종 + 기존 eval 13종 green).

## 작업 (worktree `newURP-jax`)

1. **미러 + parity**: 기준 변형 (기본값) golden bit-동일 유지 + **비기본 1변형 f64
   spot-check** (설계 메모 §3 계획대로) + golden/manifest 재생성 1회. ma 는 nc 식 한 줄
   미러 (â 수치 경로 동일 — canonical fcs() 참조).
2. **변형별 BC 신규 생성** (canonical bc.py, 3000 eps — 구세계 BC 재사용 금지).
3. **학습 15 run**: 변형 5 {t0.7_h1.0_cv, t0.7_h1.5_cv, t0.5_h1.0_cv, t0.5_h1.5_cv,
   t0.5_h1.0_ma} × seed {0,1,2}, cell m0.35_n1, arm C-① 레시피 (r4p + 증류 fire head,
   라벨 불변), 1.1e8.
4. **judge exploiter**: run 당 1, 신세계 동결 방어 상대 1e7, **jseed 277000대**, 감사
   곡선 로그.
5. C-② 로그 유지. **보고**: pin + 산출 경로 + train-side (wr·NET 점유·감사 최종) →
   main 이 strip (pools 마지막 1개 truncate)·전송·정본 평가 (seed0 276000대 — 학습 사용
   금지).

## 함정 (불변)

양성 주장 금지 · 격리본 불사용 · GPU 는 **타 사용자 점유 확인 후** 빈 쪽만 사용
(10-08 현재 server6 GPU1 타 사용자 — nvidia-smi 선확인) · git 은 newURP-jax 만 ·
전송 후 개수 검증.
