# 2026-09-06 — R2b Phase 1: **P1_NOT_POSITIVE** — rule-based intercept 협력은 net 경계를 밀지 못함 (전역 Δp_net −0.001); 저 η 에서 kinetic 1:1 치환 관측 → 봉인 3-way 규칙상 C arm 이 결정자

B0 v2 `cba024d7ee3d9f61` · fresh stream r2b_p1_v2 · 22,400 ep (28셀 × 400 paired) ·
code lineage 단일 1687fb6 · A-arm HARD_KILL 0 (계약 준수) · branch seal 선봉인 확인.

## 봉인 P1 규칙 기계 적용 (Δp_net 층)

- 행 양성 **5/14** (규칙 ≥12) · slice 별 {λ0: 2/7, λ2: 3/7} (규칙 ≥5/7) ·
  전역 paired Δp_net **−0.001**, CI95 [−0.004, +0.001] (규칙 하한 > 0) →
  **P1_NOT_POSITIVE** (3조건 전부 미충족).
- secondary Δp_U = +0.000 [−0.002, +0.002]. B-arm HARD_KILL 17건 (0.15%, 유효 terminal).
- phase2_trigger = False — rule-based arm 으로는 머니 피규어 없음.

## treatment 배선 검증 (판독 전 의무 — 버그 아님 확인)

- 기계적 차이 (fire_step/steps): **26.8%** scenario 에서 발생 — intercept 는 실제로
  세계를 바꾼다. 라벨 discordant 는 1.59% (178건) 인데 양방향 상쇄 → Δ≈0.
- A-arm vs R2a Stage 3 nominal: 평균 −0.002, max |0.060| (fresh stream 통계 정합)
  — cross-campaign 일관성 무료 확인.

## 분해가 보여준 것 (감사가 설계한 p_U = p_N + p_H 의 정확한 소비)

η=2.1 셀들: Δp_net −0.013~−0.018, p_H(B) +0.018~+0.025, Δp_U ≈ 0 —
**kinetic kill 이 net 포획을 거의 1:1 치환**. 느린 표적만 limiter 가 따라잡고
(ν=1.0 이라 동속 표적 추격 불가), 잡으면 net 대신 죽인다. "limiter cooperation 에는
capture-set shaping 과 direct kinetic interception 두 경쟁 경로가 공존" 의 첫 실측.

## 다음 (봉인 3-way 규칙)

B_N = null → **C arm 이 결정자**: C_N+ 면 "rule 이 exploitable cooperative geometry
를 실현 못 함 → learned/more expressive controller 동기" / C_N null 이면 봉인 문장
("No cooperative boundary gain was detected either with the rule-based controller or
by the sealed p2prime solver class at the tested lite search budget") — 양쪽 다 논문.
C = FULL_28x100 lite (branch seal, S_C = S_AB_v2[0:100], C_N = NET_CAPTURE 만 성공).
**C 러너 구축이 다음 작업** (p2prime CEM 기계를 R2b scenario 에 적응 — s0=0 full-
episode plan, 경량 클론 proxy + full-fidelity replay 판정, bit-parity smoke 필수).
