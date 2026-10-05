# 2026-10-05a — pilot FS1_NULL + 천장 1.3% 확정 보고 · JAX (d) = 동등 아님 (봉인 v2 보류) · E-시리즈 증거 사다리 현황

10/04 노트 고정 (r4 준비분까지) 은 사용자 지시로 오늘 해제 — 이후 기록은 10/05 부터 달력대로.
10/04 에 이미 기록된 것: 평가 계약 v1/v2/r4 봉인·사다리 버그·r4 manifest r2 (server4 고정) =
daily 2026-10-04b §5, run3 pilot 판독 상세 = 2026-10-04f.

## 1. 오늘 확정된 사실

- **run3 pilot = FS1_NULL (v1·v2 일치, 무효 0)** (`d34a931`, 판독 노트 2026-10-04f):
  D_pool −27 · D_ex +6 · D_ladder −171. **천장 = kfirst50 조차 전용 exploiter (1e7) 에 3/240 (1.3%)**,
  학습 9/240. 기전 (궤적): 종말 5~10 m 1회 회피가 net 조준·K_FIRST PN·fallback 을 동시 무력화.
  판정 근거 재확인: 이것은 **학습 방법 문제가 아니라 세계 구조** — scripted 도 같이 붕괴했고,
  물리 (가속 20.5 vs 7.16 m/s², 2 m 출발 고리 + 6 m no-kinetic + net ≤12 m 유효) 가 세 경로를 닫음.
- **JAX (d) 판정 = 동등 아님** (사전 선언 기준 집행): kfirst50 상대 최종 공격자 침투율, 정본 5 seed
  평균 0.78 vs JAX 8 seed 평균 0.50, Mann-Whitney U=34 단측 p=0.0225 < 0.05 → **봉인 v2 보류**,
  seed 추가 재판정 금지 준수. JAX 공격자가 체계적으로 약함.
- 원인 조사 (JAX 트랙, 진행): ① ckpt wr/EMA 커리큘럼 비교 (읽기 전용) ② **분리 실험 승인** —
  exploit 모드 (상대 1 고정, PFSP 제거) 로 양 구현 5e6 × 2 seed (server5 CPU, ~1h).
  main 용의자 1순위 = **PFSP pick 빈도** (정본 = episode 당 추첨, JAX = iteration 당 1회 → 공격자
  batch 의 상대 다양성 급감; exploit 모드에선 이 차이가 소거되므로 분리 실험이 정확히 가름).
  2순위 = batch 절단+bootstrap 의 희소 종말 보상 credit 희석. 수정 후 (d) 재실험은 **새 기준
  선언 + 1회** 로만.

## 2. 제안 상태 (승인 대기)

- **r4 fallback**: 오늘 저녁까지 JAX (d) 미해결 시 r4 3 seed 를 정본으로 server4 밤새 (~12h).
  계약은 구현 중립이라 가능 — r4 가 JAX 디버깅의 인질이 되는 것 방지.
- **E3 regime 격자 계약 초안 착수** (r4 와 병행).

## 3. E-시리즈 증거 사다리 현황 (로드맵 대비)

| 단계 | 질문 | 현황 (2026-10-05) |
|---|---|---|
| **E0 계측 신뢰성** | 도구를 믿을 수 있나 | **부분 완료**: 정본 평가 파이프라인 시운전 통과 (pilot, 무효 0·paired·lineage OK). JAX parity (a)(b)(c) 통과·처리량 17배 — 단 **(d) 실패로 봉인 v2 보류**, exploiter 비교도 그 뒤로 |
| **E1 존재** (학습 > 최강 scripted) | 이 cell 에서 성립하나 | **pilot = NULL**. 천장 1.3% 가 보조 답: **이 cell 에선 존재 자체가 닫힘** (min-max ≈ 0 쪽 강한 증거). 공식 확정은 r4 3 seed |
| **E2 예산 스케일링** | null 이 예산 탓인가 | 미착수 (JAX 전제). 질문이 선명해짐: 1e9~5e9 로 올려도 전용 exploiter 상대 1~4% 가 안 움직이면 cell 탓 확정 |
| **E3 regime 지도** | 어느 기동성 비율·net 사양에서 방어가 열리나 | 미착수 → **최우선 승격** (게이트 A 사실상 발동). = 원계획 Fig 5 money figure. 계약 결과 전 봉인 필수 |
| **E4 메커니즘** | mode-rank reversal · viability 조형 | **부분 음성**: reversal 없음 (학습 K_FIRST 비율: 사다리 17.9% > 적응 9.8~14.3%), iter 119 "12 m 전진 요격" 창발은 최종 정책에서 소멸 (군비 경쟁 퇴화). viability 조형 측정은 양성 regime 확보 후 |
| **E5 귀속 ablation** | 역할/보상/PFSP 가 각각 뭘 기여하나 | 미착수 — E1 양성 조건부였으므로 **E3 의 양성 regime 발견 뒤로 이연** |
| **E6 해석 하한** | net 성립 영역의 조건식 | 미착수지만 **대상이 구체화됨**: 판정창 0.3 s 최대 이탈 0.92 m < ρ 1.77 m → 성패 = 발사 시점 조준 오차, 종말 회피가 그걸 깨는 조건. **K1 손증명 (≤10/31, 사용자 레인) 과 동일 수학으로 합류** |
| **E7 일반화** | held-out·N·net 사양 sweep | 미착수 (E3 이후) |
| **E8 충실도 이전** | 3DOF+ plant 에서 유지되나 | 미착수 (Phase 후반) |
| **게이트 A** | 천장·예산으로 노선 결정 | **절반 발동**: 천장은 측정됨 (≈0). 나머지 반쪽 = E2. 현 cell 학습 우위 주장은 접고, 공식 노선 판정은 r4 + E2 후 |

## 3.5 결정 (2026-10-05 오후, 사용자)

- **r4 단독 3-seed 반복 = 미실행 보존** (학습 0 step 상태에서의 집행 보류 — 봉인 위반 아님, P1d 전례).
  근거: pilot 천장 1.3% 로 닫힌 cell 반복의 정보 가치 소멸. manifest `a38993a8541264cd` 는 기록 유지,
  seed 규칙 (2/3) 은 E3 stage 2 로 승계. r4 레시피는 stage 2 의 **arm A (조형 없음 control)** 로 생존.
- **r5 = E_req 조형 (spine B-5 목적함수의 첫 구현)** 을 E3 stage 2 **arm B** 로 — 현 cell 에서 먼저
  돌리지 않는다 (닫힌 cell 의 오염된 음성 방지). 허용 = 비봉인 배관 smoke 1회 (궤적 확인만).
  설계 근거: FS1 r0~r4 보상엔 조형 목적이 전무 (팀 공유 스칼라 + K_FIRST 직접 경로가 limiter 를
  추격-산개로 수렴시킴 — pilot 의 메커니즘 음성은 상당 부분 설정 탓). 상세 = docs/124 §3.

## 3.6 (d) 경과 (10/05 오후 추가)

- **분리 실험 (exploit 모드, PFSP 제거) 완료 ~15:40**: 정본 95·96/96 vs JAX 92·89/96 침투 —
  양쪽 포화 근처, **학습기 코어 동등 → 범인 = PFSP/상대 혼합 동역학** (main 1순위 용의자 일치).
- JAX 처방 = **episodic 모드** (정본식 완주 batch). (d) 재실험 1회 GPU 실행 중 (5 seed 순차,
  ~17:10 완료 예상). p ≥ 0.05 → 봉인 v2 / p < 0.05 → fallback.
- **fallback 정정**: "정본 r4 밤샘" 은 철회된 참조 — r4 단독 반복은 미실행 보존 (§3.5).
  유효 fallback = **E3 stage 1 축소 격자 (3 cell) 정본 밤샘** (docs/124 §7).
- **r4 전 다듬기 등록 (JAX)**: episodic 모드의 가변 batch 크기 → PPO 마지막 minibatch jit
  재컴파일 오버헤드 (정확성 무관). 처방 후보 = 고정 shape pad+mask / drop-last.
  **순서: 봉인 v2 → 재컴파일 수정 → parity 재실행 → E3 봉인이 그 commit 을 고정** (해시 churn 방지).

## 3.7 학습 세션 핸드오프 처리 (10/05 저녁 — D1~D5 결정)

핸드오프 = `docs/handoffs/HANDOFF_2026-10-05b_learning_research_to_main.md` (딥서치 보고서 +
권고 패키지). **main 실측 확인**: F1 거리 shaping = **0.169/ep 평균, 최대 0.387** (예산 0.2 초과
가능, 학습 세션 개략 산수 적중) · F2 = 65-D 관측에 **시간 채널 없음** (선형 채널 0개).

| 결정 | 내용 |
|---|---|
| D1 | **potential 변환 채택** — 방어 거리 shaping 을 공격자 측과 같은 γΦ′−Φ 로 (손잡이 0). arm A 가 진짜 조형-중립이 됨 |
| D2 | **arm A = r4′ = r4 + {D1, 남은 시간 obs 1채널, PFSP f_var=x(1−x)}**. critic 공격자-행동 조건화·HAPPO 는 보류 (parity 재검증 비용 — stage 2 1차 후 재고). **stage 1 exploiter 는 r4′ 미적용** (pilot 천장과 비교 가능성 — 봉인 v2 구현 고정) |
| D3 | 진단 게이트 = **stage 1 안의 사전 등록 보고 항목** (별도 계약 아님, hard gate 아님): scripted limiter 4형 × fin12, 조형형 2종 (c5·fwd). credit vs 균형 vs opportunity 부재 판별용 |
| D4 | arm B 서술 수정 채택 — non-potential·최적정책 변경·**B−A = 목적함수 변경 효과로만 보고** 명기 + R1/R2 smoke·공통 로그 |
| D5 | JAX 에 F2 (done/bootstrap 의미론 + 절단 꼬리 손실 작음) 전달 |

기타: graded ρ 철회 수용 (실패 쪽 비등급 — 붕괴 구간에서 역효과) · Shapley/difference reward 는
**측정 도구로만** (E4 계약 후보, G&B 대비 방법론 차별점) · F3 (공격자 PBRS 첫 step telescoping)
기록용 · G&B 예산 ~5e9/측 재확정. 미확인 고전 인용은 논문 인용 전 재검증 필요 (보고서 표기).

## 4. 다음 (의존 순서)

JAX 분리 실험 결과 → (범인 확정 → 수정 → (d) 재실험 1회) → 봉인 v2 → r4 manifest 최종 개정
(JAX commit + parity hash + batch 구조 + 예산 + server4) → r4 BC → r4 3 seed → 확정 판정.
병행: E3 계약 초안 (승인 시). fallback: 저녁까지 미해결 시 r4 정본 밤새 (승인 시).
