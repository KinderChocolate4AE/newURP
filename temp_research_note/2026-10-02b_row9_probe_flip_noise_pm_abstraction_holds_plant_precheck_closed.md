# 2026-10-02b — row-9 확인 probe: FLIP_NOISE — PM 추상화 전 행 유지, plant pre-check 종결

## 봉인 판정

Manifest `98bf85915d0762c3`, 실행 코드 `30502c0`, harvest `74440e1`.
**`COMPLETE_ROW9`** (integrity 5/5, power check 20/55 record 상이) →
사전 등록 판정 = **`ROW9_FLIP_NOISE`**: 100 ep/cell (10× 표본) 에서 row 9 의
Δχ50 = 0.000 (τ0.1) / +0.0020 (τ0.3) — 문턱 0.03 의 1/15 이하.
정본 = `artifacts/p1b2_row9/readout.json`.

## 종합 — plant-swap pre-check (docs/93 → docs/118 P1b → P1b-2 → row-9) 종결

- P1b-2 의 `AIRFRAME_RESIDUAL_CANDIDATE` (row 9, −0.036) 는 **지도 해상도의 단일
  episode flip** 이었음이 확정 (2026-10-02 노트의 가설 그대로).
- 최종 문장: **검사한 전 행·τ_a/τ₀ ≤ 0.3 범위에서, 1차 defender 가속 지연은
  c5-arc 세계의 χ50 경계를 δ_χ = 0.03 이상 움직이지 않는다** (나머지 행
  |Δ| ≤ 0.005). docs/93 §4 의 "collapse 가 transport 됨 (강한 결과)" 분기.
- 한정 (정직): tested cells·declared lag 모델·scripted defender 한정. 6DOF
  일반 주장 아님. 학습된 π* 에 대한 동일 검사는 W10 층3 그대로 유지.
- **P2 학습의 point-mass 세계 선언은 깨끗해졌다** — 주석 없이 진행 가능.
- 부수 관찰: row 9 는 H_illegal 이 유난히 높은 행 (36~39/200 ≈ 18% vs 전체
  ~7%) — c5 의 비인가 engagement 경향이 row 의존적이라는 서술적 기록만 남김.

## 다음

P2 limiter-only v2 계약 초안 (docs/120) — 공격자 mix 는 P1a 지도 기반.
