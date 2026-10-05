# 124 — E3: 방어-가능 regime 지도 (capability-ratio 격자) 계약 초안

- **일자**: 2026-10-05 · **상태**: **초안 (미봉인)** — 사용자 검토 후 stage 1 결과 보기 전 봉인
- **결정 근거**: run3 pilot = FS1_NULL + **천장 1.3%** (노트 2026-10-04f/2026-10-05a) — cell r06c1
  (μ=0.35, ν=1.0) 은 적응 공격자 앞에서 scripted·학습 공통 붕괴 = **세계 구조**. 학습 우위 질문은
  "이 cell 에서 되는가" 가 아니라 "**어느 방어 capability 에서 열리는가**" 로 바꿔야 한다 (게이트 A).
  이것이 원계획의 **Fig 5 (speed × maneuver heatmap, money figure)** 이다.
- **의존**: exploiter·co-training 물량은 JAX 전제 (봉인 v2 후). JAX 지연 시 축소 격자 정본 fallback (§7).

## 1. 질문 (사전 등록)

1. **Q1 (경계)**: 방어 capability 비율 (μ, ν) 평면에서, 최강 scripted 방어의 **전용-exploiter 천장**이
   열리는 경계는 어디인가.
2. **Q2 (학습 이득)**: 천장이 열린 cell 에서, r4 레시피 동시학습 방어가 최강 scripted 를
   봉인 기준 (D ≥ +24/240) 으로 이기는가.

## 2. 축과 격자 (물리 근거)

공격자 = 비준 위협 고정 (a_att 20.45 m/s², v 순항 23.01 / 최대 34.52 m/s — r06c1 resolve 값).
**방어자 capability 만 조건화** (코드의 `CAPABILITY_RATIOS` conditioning vector 그대로):

| 축 | 정의 | 격자 | 현 cell |
|---|---|---|---|
| **μ** (maneuver) | a_def / a_att (limiter·finisher 동일) | {0.35, 0.5, 0.7, 1.0, 1.4} (≈ ×√2 로그 간격) | 0.35 |
| **ν** (speed) | v_def / v_att,순항 | {0.8, 1.0, 1.25} | 1.0 |

15 cells (현 cell 포함 — pilot 과의 연속성 anchor, 단 **pooling 은 하지 않고** 재측정).
구현 = `physics.a_lim_max`/`finisher_a_max` = μ·a_att, `limiter_v_max`/`finisher_v_max` = ν·v_att
override 만 (FS1Spec 필드 추가, 기본값 = 현행 bit-identical). net 사양·배치·episode·ROE = FS1 r4 와 동일.
net/배치 축은 E7 (별도 계약) — 이 계약에서 움직이지 않는다.

**사전 등록 예측 (판정 비게이트, E6 연계)**: 천장은 μ 에 단조 증가하며, 경계 μ* 는 [0.5, 1.0] 구간.
근거 = 종말 회피 기전: 판정창 0.3 s 공격자 최대 이탈 0.92 m < ρ 1.77 m 이므로 성패는 발사 시점
조준 오차와 요격 수렴이고, 둘 다 가속비의 함수. E6 해석 (K1 손증명 라인) 이 μ* 를 독립 산출하면
empirical 경계와 대조한다 (논문 핵심 그림 후보).

## 3. 2-단계 설계

### Stage 1 — 천장 스캔 (전부 실행, 조건 없음)
cell 마다: scripted 방어 2종 {kfirst50, fin12_fb} 각각에 **전용 exploiter** (1e7 step, r4 exploit 모드)
학습 → 정본 평가 240판 (paired). **ceiling_s(cell) = max over scripted of defended/240.**
보고 추가: 공칭 사다리 vs scripted 96판 (포화 sanity), 궤적 그림 (viz-first).

### Stage 2 — 학습 이득 (조건부, 선정 규칙 사전 고정, **2-arm**)
**선정 규칙**: ceiling_s ∈ [48, 216]/240 (= 20%~90%) 인 **모든** cell — "열려 있되 자명하지 않음".
하한 20% = 바닥끼리 비교 배제 (pilot D_ex=+6 교훈; 표본 오차 ±5%p 상회). 상한 90% = 포화 배제 **및
산술 가능성 보장**: ceiling_s > 216 이면 학습이 240/240 이어도 D < +24 라 통과가 불가능하다.
cherry-pick 금지: 규칙에 맞는 cell 전부, 하나도 없으면 stage 2 생략.

각 선정 cell 에서 **두 arm** 을 같은 예산·같은 seed 로:
- **arm A (r4 레시피, 조형 없음 control)**: docs/123 §9 그대로 — G&B식 종말 보상 + 거리 shaping.
  (r4 단독 반복 계약 `a38993a8541264cd` 는 **미실행으로 보존** — pilot 의 천장 발견으로 닫힌 cell
  3-seed 반복의 정보 가치가 소멸 (2026-10-05 결정). manifest 는 기록으로 유지, seed 규칙은 여기로 승계.)
- **arm B (r5 = A + fire-tick viability 보너스, 단일 손잡이)**: 팀 보상에 **net 발사 tick 한 번만**
  r += κ·v_shot_soft (κ = 0.2). proxy 를 새로 만들지 않고 **env 의 비준된 포획 판정값** (B0 v3,
  lean 모드가 FIRE tick 에만 계산) 을 그대로 쓴다. 발사 ≈ 1회/episode 라 구조적으로 ≤ κ —
  종말 보상 ±1 압도 불가 (r3 다양성 패널티 −0.74/ep 교훈). dense E_req 다항 보상 (수제 proxy +
  가중 3 + β + arm 패널티) 은 **기각-보류**: 조형을 구매하면 메커니즘 주장이 순환하고 손잡이 6개
  (2026-10-05 검토). arm B 로도 기울기 부재가 입증될 때만 별도 계약으로 재고.
  봉인 전 현 cell **배관 smoke 1회** (비봉인, 보고용): κ 항 배선 + 행동 변화 궤적 확인만.
- **메커니즘 지표는 보상이 아니라 로그**: 발사 시점 v_shot_soft·E_req proxy·공격자 |v_⊥|/λ̇ 를
  **양 arm 공통 진단 로그**로 기록. arm A 에서의 자발 창발 = 순수 발견 주장 (E4 ①),
  arm B − A 결과 차 = 보상 설계 효과 주장 — 두 주장을 분리 (측정은 공짜, 구매는 안 함).

각 arm **3 seed** (1.1e8, JAX) + 봉인 평가 (eval v1 절차 + 공칭 사다리) → arm 판정 = seed 별 v2 판정
2/3 확정. **arm B − arm A 가 귀속 (강한 결과 ②) 의 1차 증거** — 같은 cell·같은 seed paired.

## 4. 판정 (사전 등록)

| 결과 | 조건 |
|---|---|
| `E3_BOUNDARY_MAPPED` | stage 1 완료 (항상 — 기술 기록, Fig 5 heatmap 산출) |
| `E3_LEARNING_OPENS` | stage 2 선정 cell 중 ≥ 1 개가 2/3 seed POSITIVE(또는 NARROW) |
| `E3_NO_ADVANTAGE_IN_BAND` | stage 2 실행됐으나 위 미달 |
| `E3_BAND_EMPTY` | 선정 cell 0 개 (격자 전체가 닫힘 또는 포화) |
| `INVALID_E3` | lineage/completion/paired/budget 위반 |

## 5. 평가·재현 규율

- namespace `fs1_e3_v1`, seed0 263000 (cell 별 offset 사전 표). paired: cell 안에서 모든 방어가
  같은 시드. **판정 평가 환경 = server4** (r4 manifest r2 조항 승계).
- exploiter 예산 = 1e7 고정 (pilot 과 비교 가능성). 큰 예산 exploiter 는 보고용 별도.
- **pooling 금지**: B0 v3·pilot·r4 와 결과 합산 금지. μ≠0.35 cell 은 B0 v3 밖 세계 변형임을 명시.
- exploiter·학습 구현 = 봉인 v2 JAX (commit + parity hash 를 봉인 시 기입). 판정 평가 = 정본.

## 6. not_evidence_for

실제 기체 성능비 대표성 (격자는 conditioning 이지 특정 기체 아님) · net/배치 축 (E7) ·
6DOF/plant (E8) · Huh/G&B 정량 비교 (별도) · "협력" 어휘 금지 유지 (limiter-control opportunity).

## 7. 예산·fallback

- Stage 1: 30 exploiter 학습 (3e8 step, JAX GPU 수십 분~수 시간) + 평가 15×~10 분 (server4 CPU).
- Stage 2: 선정 n cell × **2 arm** × 3 seed × 35 분 (JAX). n ≤ 4 가정 시 ≤ 14 h.
- JAX 지연 fallback: stage 1 을 축소 격자 μ×ν = {0.35, 0.7, 1.4}×{1.0} 3 cell 로 정본 밤새 —
  축소분도 같은 선정 규칙·판정을 쓰되 `E3_BOUNDARY_MAPPED(reduced)` 로 표기.

## 8. 봉인 절차

사용자 검토 → `scripts/fs1_e3_manifest.py` (build/load/sha256[:16] 관례) 작성 →
**stage 1 결과 보기 전** manifest 봉인 → 실행. 격자·선정 규칙·문턱의 사후 변경 금지
(변경 = v2 + 새 hash + 기존 결과와 pooling 금지).
