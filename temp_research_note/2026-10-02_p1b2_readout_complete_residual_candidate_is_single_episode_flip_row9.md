# 2026-10-02 — P1b-2 판독: COMPLETE, AIRFRAME_RESIDUAL_CANDIDATE — 단 그 후보는 row 9 의 단일 episode flip

## 봉인 판정

Manifest `b0d84cd58cc091f9`, 실행 코드 `5c73054`, harvest `d3ab79f`.
**`COMPLETE_P1B2`** (integrity 5/5 — **power check 통과**: τ0.1 에서 paired record
20건, τ0.3 에서 57건이 τ=0 과 실제로 달라짐. P1b 의 vacuity 는 재발하지 않았다).
사전 등록 분류 = **`AIRFRAME_RESIDUAL_CANDIDATE`** (max |Δχ50| = 0.036 ≥ 0.03).
정본 = `artifacts/p1b2_plant/readout.json`.

## 결과 (c5 arc limiter + scripted launcher, 280 ep/arm, paired)

| arm | N | H_illegal | crossings_total |
|---|---:|---:|---:|
| τ = 0 | 152 | 20 | 983 |
| τ = 0.1 | 149 | 22 | 983 |
| τ = 0.3 | 143 | 20 | 1013 |

- 방향: lag ↑ → N 완만히 감소 (152→149→143) — 가속 지연이 방어를 약화시키는
  물리적으로 그럴듯한 방향. c5 의 H_illegal ~20/280 은 b5 (15) · B2 RULE (5.6%)
  와 정합.
- 행별 Δχ50: row 9 (−0.036, 양 τ 동일) 하나를 제외하면 전부 |Δ| ≤ 0.005.

## 후보의 실체 — 단일 episode flip

row 9 의 episode 단위 대조 (20 ep): χ=0.5141 의 **1개 episode 만** N → F_other 로
flip (τ0.1·τ0.3 동일), 나머지 19개 bit-identical. isotonic + 선형보간에서 경계
바로 위 1 episode flip 이 crossing 을 정확히 0.036 움직인다. 즉 이 "residual
candidate" 는 **측정된 경계 이동이 아니라 선언된 지도 해상도 (10 ep/cell) 에서의
최소 단위 이벤트**다. 사전 등록 분류를 번복하지 않는다 — candidate 는 말 그대로
후보이며, 해상도 캐비앗은 manifest 에 선언돼 있었다.

## 처분 선택지 (사용자 결정)

- **(a) row 9 한정 확인 probe** (권장): row 9 의 2 cell × 100 ep × 3 arm = 600 ep,
  fresh namespace 소계약. Δχ50(row 9) 이 유지되면 진짜 residual 후보로 승격,
  1-flip 노이즈면 전 행 |Δ| < 0.005 로 **PM_ABSTRACTION_HOLDS** 로 정리. 서버
  수 분 거리.
- **(b) candidate 그대로 동결**: P2 세계 선언에 "row 9 후보 — W10 층3 에서
  B2급 표본으로 재확인" 으로 주석만 달고 P2 진행. blocking 조건 ("readout 존재")
  은 이미 충족이라 계약상 P2 착수 가능.

어느 쪽이든 P2 는 point-mass 세계로 진행 (후보 1행이 전 지도를 흔들지 않음);
차이는 주석의 강도뿐이다.
