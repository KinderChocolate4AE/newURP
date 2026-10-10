# 134 — E1 전이 사다리 계약: 등록 경계 ρ* 가 학습 net 포획의 시작점을 예측하는가 (+ tick 계단 쌍, + 조건부 E6)

- **일자**: 2026-10-11 · **봉인**: `scripts/fs1_e1_manifest.py` → `artifacts/fs1/e1_manifest.json` (상수·규칙의 단일 원천).
- **결재**: 사용자 2026-10-11 ("근거 최대 확보 후 집필 — 당장 시작"; 지도교수의 "10/26 이후" 시점 권고를 사용자가 대체).
  설계 = 지도교수 2026-10-11 2·3차 답변 (세 갈래 사전 등록, 평탄부 nuisance, net 지표, 2차 추정량, 계단 쌍, E6 조건부 arm).
- **gap**: docs/131 G7 (ρ 1.92–3.92 사이 학습 점 없음), G10 (창 4 step ↔ 천장 대응 미유도).
- **절단선 위치**: ② — 해석 경계와 학습 천장을 잇는 유일한 비동어반복 연결고리 (R-a 대응).

## 1. 설계

- **사다리 (τ 만 변경, θ₀, cv)**: ρ 1.92 / 2.30 / 2.66 / 2.93 / 3.42 / 3.92 / 7.69 (τ 0.300 … 0.150 s) × seed 5 = 35 slot,
  **전부 새 학습** (arm C-1 레시피, ROE A, m0.35_n1, 새 BC → 1.1e8 → det 착취자 1e7 → sto 착취자 1e7).
  E7-b 점은 이전 계보 — 재현 대상으로만 보고, 맞춤에 쓰지 않는다 (pooling 금지).
- **실현 전개 tick**: 6 6 6 5 5 5 3 (계단 τ 0.25 s = ρ 2.769, 등록 대역 안 — 지도교수 지적, main 검증).
- **tick 계단 쌍**: ρ 2.75 (6 tick) / 2.78 (5 tick) × seed 5 — ρ 1% 차, tick 만 다름 → 계단 효과 직접 측정.
- **판정 계열 (사전 선언)**: **det** (learned_det vs det 착취자) — E7-b 판정 계열·그림 2(b) 주 계열과 계보 연속.
  sto 계열은 보고용.
- **평가**: 240판, seed 330000 + idx·1000 (미사용 대역), `--env-seed 0` (docs/132 §5 발견), `rob_fire` 기록.

## 2. 지표

- 주: net (NET_CAPTURE + CAPTURE_WITH_CONTACT). 전체 방어 수는 보고만.
- 2차: rob_fire (첫 발사가 발사 순간 robust 였던 episode 수 = 포획 예정, tick 해소 경로 제거).
- 보고: robust 발사였으나 해소 전 침투한 수 · sto 계열 · 착취자 최종 관통률.

## 3. ρ½ 추정과 사전 판정

- 모형: y = L + (U − L)/(1 + exp(−k(log ρ − log ρ½))), y = slot 별 net/240, 35 slot 최소제곱 (경계는 manifest).
  평탄부 U·바닥 L 은 함께 추정하는 nuisance. 민감도: E7-b net_det 중앙값으로 평탄부 고정 시 ρ½ (보고만).
- CI: ρ 점 안에서 seed 를 재표집하는 층화 bootstrap 2000 회, percentile 95%.
- U − L < 4/240 또는 맞춤 실패 → `NO_TRANSITION`.
- **세 갈래 (CI 규칙)**: CI 전체 < 2.427 → `EARLY` (창이 존재만 하면 시작) / CI ⊂ [2.427, 2.813] → `AT_BOUNDARY`
  (ρ* 가 시작점 예측 — 가장 강함) / CI 전체 > 2.813 → `LATE` (경계는 필요조건일 뿐) / 걸치면 `UNDETERMINED`.
- 2차 지표의 갈래가 주 지표와 다르면 `DISCRETIZATION_SENSITIVE` — 갈래 주장 안 함.
- **검정력 메모 (봉인 전 합성 점검)**: 이 사다리·5 seed 에서 ρ½ 추정의 10–90% 폭 ≈ 0.3 (ρ 단위) 으로 대역 폭 0.39 와
  비슷하다 → `UNDETERMINED` 가 나올 가능성이 크다. 추정 자체는 치우침이 거의 없다 (30 반복 중앙값 오차 < 0.04).
  1.92 아래 점 추가는 폭을 10–20% 줄이지만 새 tick 계단 (7 tick) 을 만들어 넣지 않았다.

## 4. E6 조건부 arm (AMI 트리거, docs/132 §4)

- 조건: AMI det 계열 = `AMI_ADAPTIVE` 또는 `AMI_ATTACKER_NONADAPTIVE` 일 때만.
- 세계: FS1Spec 에 **새 a_scale 손잡이** (a_att × 0.49 = 10.02, ρ 3.925), μ' = 0.7143 (a_def 7.16 고정 — 절대 고정이 주 조건).
  기본값 1.0 비트 동일 테스트 + JAX parity 점검 후 생산.
- 예측: Λ = V²/(a·R_max) 가 두 배. seed 짝 d = net(e6) − net(r3.92): 중앙값 ≥ +8 그리고 5 중 4 양수 →
  `LAMBDA_RAISES_CEILING` / |중앙값| < 8 → `CEILING_COLLAPSES_IN_RHO` / ≤ −8 → `LAMBDA_LOWERS_CEILING` / 그 밖 `MIXED`.
- 이름 붙인 교란: K_HOME 비정규화 · 같은 1e7 예산에서 착취자 난이도 (최종 관통률 공변량) · A안 kinetic 경로 (net 지표만).

## 5. 생산 우선순위 (server4 GPU 1장, JAX learner)

① 사다리 det 경로 35 slot → ② 계단 쌍 10 → ③ E6 5 (트리거 시) → ④ sto 착취자. 착취자 jseed: det 300000 + idx·100 + seed,
sto 305000 + idx·100 + seed (E7-b/b′/c 대역과 분리). 예상 GPU 시간: E7-b 실적 (slot 당 약 40분) 기준 ① 약 1일.

## 6. 한계

1e7 착취자 조건부 · 단일 cell · τ 손잡이만 (다른 손잡이 방향의 천장 collapse 는 E6 한 점) · ρ* 는 E7-a 이후 등록이라
blind 아님 (단 천장 층에 대한 첫 등록 예측) · 세계 천장 아님.
