# 2026-10-04c — P1c 판독: STANDOFF_DOES_NOT_OPEN — 늘어난 접근거리를 c5 조형이 쓰지 않음 (layout-고정 스케일링 모형 한정)

## 봉인 판정

Manifest `6fc93fde71b38a30`, 실행 코드 `38e885d`, harvest `2ead989`.
**`COMPLETE_P1C` → `STANDOFF_DOES_NOT_OPEN`** (integrity 5/5 PASS — completion ·
budget · paired draws · lineage · power). 정본 = `artifacts/p1c_standoff/readout.json`.

- G(k) = N_c5 − N_hold (두 공격자 pooled, 560 ep/arm/scale): **G(1)=0, G(2)=+9, G(4)=+10**
- **G(4) − G(1) = +10 < +28** (사전 등록 문턱 +5%p) → DOES_NOT_OPEN.
- power gate: hold 평균 step 45.5 → 76.8 → 136.5 (k=1→2→4). 스케일링이 실제로
  접근을 늘렸으므로 검정력 0 (P1b 형) 무효가 아니다.

k 의 의미: 공격자 시작거리 `adversary_start_x` 와 `episode_len` 만 k 배
(시작 x ≈ 24 → 48 → 96 m). 방어 layout (limiter ring x=8, finisher x=2),
spawn jitter, χ/η 무차원화는 불변. k>1 은 B0 v3 밖 v4 pre-check 변형 — pooling 금지.

## 원자료 (N / 280)

| k | r05 hold | r05 c5 | r08 hold | r08 c5 | c5 H_illegal (r05+r08) |
|---|---|---|---|---|---|
| 1 | 136 | 141 | 89 | 84 | 15+25 = 40 |
| 2 | 137 | 154 | 94 | 86 | 0+3 = 3 (+H_fb 1) |
| 4 | 112 | 133 | 90 | 79 | 0+5 = 5 |

보고 전용 관찰 (gate 아님):
1. **G(4)=+10 의 대부분은 c5 상승이 아니라 hold 하락에서 나온다** (r05 hold
   136→112, c5 141→133 — 두 arm 모두 k=4 에서 떨어짐). 즉 "조형이 열렸다"가
   아니라 "기본선이 나빠졌다".
2. r08 (고결합) 은 모든 k 에서 c5 ≤ hold. P2 의 결합-의존 곡선 (r08_j0 +10) 과
   방향이 다르다 — P2 는 6-config mix 위 측정이라 직접 비교 금지, 기록만.
3. c5 의 H_illegal 이 k=1 의 40 → k≥2 의 3~5 로 급감. 긴 접근은 c5 의 **안전**은
   개선하나 포획은 개선하지 않는다.

## 궤적 (viz-first — 수치 전 확인)

뷰어: `viz/p1c_standoff_viewer.html` (생성기 `scripts/viz_p1c_standoff.py`,
rows 0/6/13 × 2 cell × 3 k × 2 공격자 × 2 arm = 72 ep). 재생일치 (steps·fire)
**70/72** — 불일치 2건은 모두 k=4 c5, cell r13c2 sid 270 (재생기 `_Driver` 의 arc
경로 차이로 추정, 미규명). 해당 2 ep 는 참고용, 수치 인용 금지.

핵심 관찰 (row 6, 양 공격자):
- **FIRE 위치는 k 와 무관하게 x≈12 근처로 같다.** 늘어난 거리는 방어자와 먼
  직선 비행으로 소비된다.
- **c5 limiter 궤적은 k=4 에서도 x∈[−10, 10] 에 머문다.** arc 규칙의 작동 영역이
  layout 에 묶여 있어, 공격자가 멀리서 오더라도 조형은 마지막 구간에서만 일어난다.
- 따라서 이 스케일링 모형에서 "standoff 증가" = "자유 접근 구간 증가" 이지
  "조형 활주로 증가" 가 아니다. 결과 변화 (hold 하락 등) 는 공격자가 spawn
  과도상태가 아닌 정상상태로 layout 에 도착하는 효과와 섞여 있다.

## 해석 (정직)

1. **계약 판정은 DOES_NOT_OPEN 이고 번복하지 않는다.** 선언된 스케일링 모형
   (layout 고정, 시작거리만 ×k) 과 시험 범위 (k≤4) 에서, 접근거리를 늘려도
   rule 조형 (c5) 의 이득은 사전 문턱만큼 열리지 않았다.
2. **기각되는 설명**: "P2_NULL·b5 null 의 원인은 공격자 접근거리가 짧아서다"
   (docs/121 동기). 접근거리를 4배로 늘려도 c5 이득이 열리지 않았다.
3. **기각되지 않은 것 (범위 밖)**: limiter 가 앞으로 나가 일찍 교전하는 세계
   (layout 자체를 스케일하거나 전진 배치) 에서의 조형 활주로. 궤적상 c5 는 늘어난
   거리를 쓰지 않았으므로 본 probe 는 그 질문을 시험하지 못했다. 이를 시험하려면
   새 계약이 필요하다 — 본 판정의 소급 확장 금지.

## 처분

- **B0 v4 결재안 작성하지 않음** (진입 조건 OPENS 미충족).
- limiter-learning 재개 조건 (P1c OPENS + B0 v4 봉인) 불충족 — **현 세계 종결 유지**.
- **Track B (docs/104 net–kinetic 전환, 실행계획 docs/105) 전면 이동.** 10/04 합의
  순서 (daily 2026-10-04b §5) 에서 ④ limiter 학습은 "P1c OPENS 시만" 이었으므로
  보류. 다음 = **F1-E D2** (limiter 없는 scripted 3정책, viz-first) → 학습 상위
  switch → PFSP gate. limiter 를 §3 세계에 다시 넣을 때는 위 "범위 밖" 질문
  (전진 교전 layout) 을 G0 수준에서 먼저 결정한다.
- 유지 판정 목록에 `STANDOFF_DOES_NOT_OPEN` 추가.
