# 118 — P1 공격자 사다리 설계 계약 (**봉인 2026-10-01** — manifest `4629158d387c938b`)

- **봉인**: 2026-10-01 사용자 승인 ("ㅇㅇ 봉인") — §6 의 결재 항목은 아래 **결재
  결과**로 확정. 정본 수치 = `artifacts/p1_ladder/manifest.json`
  (`scripts/p1_ladder_manifest.py`, hash `4629158d387c938b`, config 24종).
- **v1.1 pre-run 정정 (2026-10-01, 결과 0건 시점 — manifest `b2524bf5e860f14c` →
  `4629158d387c938b`)**: 초판의 P1b 전용 namespace (`p1b_plant_v1`/201000) 는
  "τ=0 baseline 을 P1a 와 공유(same draws)" 선언과 모순 (namespace 가 다르면 draw
  가 다름). P1b 를 P1a namespace (`p1_ladder_v1`/191000) 로 통일해 행별 Δχ50 이
  진짜 paired 가 되도록 정정. cell 서술도 "14행 × chi_role {lo, hi}" 로 교정.
- **봉인 시 §4 정정 (초안 대비)**: 초안의 "B2 경계 cell 재사용 부적합" 판단을
  철회한다 — B2 28-cell suite 는 14행 × 2 slice 구조로 **행별 χ50 추정을 이미
  지원**하며, config 간 paired 비교에는 공통 고정 cell 이 오히려 필요하다.
  경계 이동이 커서 χ50 이 행 범위를 벗어나면 censored 로 보고만 하고 외삽하지
  않는다. 10 ep/cell 은 지도 해상도이지 B2급 confirmatory 추정이 아니다.
- **봉인 시 §3 축소 (초안 대비)**: 종축 속도 프로파일 (sprint/slowdown) 변형은
  **후속 판올림으로 유보** — 오늘 기준 근거 있는 값이 없어 ungrounded constant
  봉인을 피한다 (Δ6 전례). bait_gain = 0.5 는 route 공칭과 동일 크기로 선언
  (신규 스케일 자유도 최소화).
- **일자**: 2026-10-01 · **상위**: docs/117 P1 · docs/89 r5 · **규율**: docs/80
  (T 표기 · 단일축 이동 · T2 역-허수아비 금지 · null 해석), docs/27 §4 (행동
  파라미터 선언 후 고정 — 최적화 금지).
- **발견 (설계 비용 절감)**: `shepherd/agents/attacker_ladder.py` 가 이미 T1-family
  이상의 축을 구현·테스트 완료 상태로 보유한다 — λ 프리셋 5종, jink, route_gain ×
  sense_range, v3 종축 속도 프로파일 (sprint/slowdown), A3 bait (fair/privileged),
  nesting bit-exact 규약. **P1a 는 새 공격자 코드 0 으로 격자 선언만으로 실행
  가능하다.** docs/80 의 "T2 미구현" 은 objective-식 T2 기준이며, 기존 축 조합이
  그보다 먼저 쓸 수 있는 선언된 다양성이다.

## 1. 질문

defender 를 완전 동결한 상태에서, 선언된 공격자 설정 격자가 clean N / 경계 지도를
**실제로 얼마나 움직이는가.** 이 지도는 ① foundation 논문의 "공격자 행동 수위" 축
자산, ② P2 limiter-only v2 의 대조 기준, ③ "b5 무신호 = 공격자 반응성 부족" 가설의
전제 검증 (공격자 축이 defender-frozen 결과를 거의 안 움직이면 P2 가설은 약해진다
— 그 측정 자체가 판독이다).

## 2. Defender (전 cell 동결)

- limiter: scripted **hold** (b5 대조와 동일 — H_illegal 0 구조).
- capturer: **scripted launcher** (b5 기준 140~148/280, FIRE 배선 단순).
  F3 keeper 의 투입 여부는 P2 계약에서 결정 — P1 지도는 P2 와 같은 구성이어야
  대조가 성립하므로, P2 가 F3 를 택하면 해당 cell 만 P1 추가 arm 으로 재측정.

## 3. 공격자 격자 (P1a — 전부 기존 `AttackerSpec` 축, 선언 후 고정)

| 축 | 값 (제안 — §6 결재) | 근거 |
|---|---|---|
| T1 family: `route_gain` | {0.2, 0.5, 0.8} | Phase III 분포 U[0.2,0.8] 의 3점 |
| T1 family: `sense_range` | {15, 30, ∞} m | docs/80 §2 종말-한정 ↔ 전구간 관측 — **pivot 가설의 핵심 변수** |
| λ (손실 회피) | LAM_REF, LAM_ANTIC (+ LAM_ZERO 음성 대조 1 slice) | 예견 회피 = 합리적 조종자, docs/28 |
| 지속 회피 | `jink_amp` {0, 0.6} | T0 legacy 값 재사용 |
| 종축 속도 | nominal + sprint 1 설정 + slowdown 1 설정 | v3 축, "기만" 주장 금지 (docs/60 §2.1) |
| A3 bait | fair 1 설정 (+ privileged 소수 cell = 상한 대조) | fair/privileged 분리 유지 (docs/27 §2.4) |

- 전체 조합 폭발 금지: **주 격자 = T1 family × λ (3×3×2 = 18 설정)**, 심화 축
  (jink·속도·bait) 은 주 격자의 대표점 {route 0.5, sense 30} 위에 **단일축 변형**
  으로만 얹는다 (각 +2~4 설정). 총 ≤ 28 설정 목표.
- 명칭: 산출물·논문 표기는 **T-사다리** (T1 단일점 / T1-family / T1+축명).
  코드 `level` 의 A1~A3 과 혼용 금지 (docs/80 ★).

## 4. 평가·예산 (제안 — §6 결재)

- cell: B2 경계 cell 재사용이 아니라 **χ 격자 슬라이스** (공격자가 바뀌면 경계가
  이동하므로 고정 경계 cell 은 지도 목적에 부적합). 슬라이스 수·episode 수는
  B2 예산 산정 방식을 승계해 결재.
- 서버 샤딩 (long-run policy) · 새 namespace (`p1_ladder_v1`) · CRN: 설정 간
  paired 비교를 위해 scenario/seed 공유.
- 완결성 gate 만 둔다 (계보·완주·finite·budget — INVALID 조건). 성능 PASS/STOP
  gate 는 없다 — **이것은 지도 제작이지 가설 검정이 아니다.** 단 P2 전제 판독
  기준 (공격자 축 효과의 사전 문턱) 은 §6 에서 결재해 결과 열람 전 봉인.

## 5. P1b 부속 — scripted plant-swap pre-check (docs/93 §5 저비용 선행판)

- **옵션 1 채택 제안**: 1차 가속 지연 τ_a·ȧ = a_cmd − a (defender 측만; 공격자
  plant 불변 — 단일축 규율). 삽입점 = `env.py` step 의 defender `a_cmd` → backend
  적분 직전 (limiter accel(3) · capturer 가속 공통 경로).
- 무차원 τ_a/τ₀ 2~3 값 (docs/92 §1 규칙) × 경계 cell 소수 spot-check.
- 판독: Δχ50^AF vs δ_χ = 0.03 (docs/93 §4 — 양쪽 다 논문이 되는 구조).
  **P2 학습 착수 전 완료**가 목적 — 점질량 세계에서의 학습 투자 타당성 측정.

## 6. 결재 결과 (2026-10-01 봉인 — manifest 가 정본)

1. **격자**: 주 격자 18 (route {0.2, 0.5, 0.8} × sense {15, 30, ∞} × λ {REF, ANTIC})
   + anchor 2 (T0 route=0 · A1 pure) + depth 4 (jink0 ablation · LAM_ZERO 음성 대조 ·
   bait fair 0.5 · bait privileged 0.5) = **24 config**. 속도 프로파일 유보.
2. **예산**: 공통 28-cell suite × 10 ep = config 당 280, P1a 총 6,720 + P1b 560.
   전 config 동일 (seed0 191000, `p1_ladder_v1`) draw 공유 = paired CRN.
3. **P2 전제 판독 (사전 등록, gate 아님)**: 주 격자 18 config 의 clean N 최대−최소
   ≥ 28/280 → `P2_PREMISE_SUPPORTED`, 미만 → `P2_PREMISE_WEAK`. sense_range 효과는
   보조 서술자.
4. **P1b**: docs/93 옵션 1 (1차 가속 지연, defender 병진 a_cmd 한정, 공격자 불변 —
   capturer 병진은 `FinisherSpec.a_max=0` 기본에서 정확히 0 이므로 limiter lag 가
   계약을 정확히 구현; 실행기가 a_max==0 을 assert). τ_a/τ₀ ∈ {0.1, 0.3} (τ₀ =
   cell 의 tau_deploy), 공칭 공격자, **P1a 와 동일 namespace/draw** (v1.1) — τ=0
   baseline = `t1f_r05_s30_ref` 그 자체. 판독 = 행별 paired Δχ50^AF vs δ_χ = 0.03.
   **P2 학습 착수 전 완료.**
5. **capturer = scripted launcher 고정** 승인. F3 arm 은 P2 계약에서.

## 7. 실행 전 잔여

- 실행 스크립트 + manifest 정합 테스트 (결과 전 커밋) → smoke → 서버 샤딩 실행
  → harvest → 판독 노트. gate 는 완결성만 (`COMPLETE_P1` / `INVALID_P1`).
