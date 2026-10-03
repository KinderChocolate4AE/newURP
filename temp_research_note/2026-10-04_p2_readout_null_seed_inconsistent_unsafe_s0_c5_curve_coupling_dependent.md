# 2026-10-04 — P2 판독: P2_NULL — seed 불일치 + s0 안전 위반; 단 c5 곡선은 결합-의존 조형 가치를 보여줌

## 봉인 판정

Manifest `8ba6d0df420d6631`, 실행 코드 `b5e39ab`, harvest `df42a39`.
**`P2_NULL`** (integrity 6/6 PASS — neutral init·finisher freeze 검증 포함).
실패 조항: ① seed0 pooled ΔN = +7 < +34 ② seed0 고결합 m_r08_j06 ΔN = −1
③ pooled H_illegal ≠ 0 (learned_s0 = 20, learned_s1 = 1; hold 0).
정본 = `artifacts/p2_limiter/readout.json`.

## 결과 (paired 280 ep/config, 4 arm)

pooled ΔN vs hold: **c5 +21 (H 98) · learned_s0 +7 (H 20) · learned_s1 +39 (H 1)**.

config 별 Δ(c5−hold): −5, +6, +1, **+12** (r05_j06), **+10** (r08_j0), −3 —
**rule 조형의 이득이 결합 이득 (route·jink) 과 함께 커지는 방향성**이 보인다
(보고 전용, 사전 등록 gate 아님). learned seed1 도 유사 패턴 (+13, +9, +9, +7)
이나 seed0 이 이를 재현하지 못했고, seed0 은 비인가 engagement 20건을 만드는
배치로 수렴했다.

## 해석 (정직)

1. **계약 판정은 NULL 이고 번복하지 않는다.** b5 (−1/+5) 와 합치면: 현 세계
   스케일에서 limiter-only 학습은 4배 예산·결합 이득 강화에도 **seed 일관 +
   안전 유지 조건을 만족하는 개선을 보여주지 못했다.**
2. 단 manifest 의 봉인 해석문 ("insensitive to attacker coupling") 은 데이터보다
   강하다 — **조형 가치 자체는 결합-의존이 관측된다 (c5 곡선, learned s1)**.
   정확한 기록: "조형 가치는 결합과 함께 커지지만, 현 스케일에서 학습이 그것을
   rule 이상으로·안전하게·seed-일관되게 회수하지 못한다." 이 곡선이 foundation
   그림 (공격자 행동 수위 → 조형 가치) 의 1차 측정이다.
3. **학습이 안 되는 이유 후보**는 열려 있다: 짧은 standoff (조형 활주로 cm 단위,
   09-13d) 가 유력 — P1c 가 정확히 이것을 잰다. 즉 P2_NULL 은 "limiter 학습 영구
   폐기" 가 아니라 "현 세계에서의 폐기 + 세계 축 (standoff) 검증으로 이관" 이다.

## 처분 (docs/117 출구 + 수순)

- **PFSP (P3) 닫힘** — P2 양성 조건 미충족 (docs/117 명시 조건).
- **limiter-learning 라인은 현 세계에서 종결.** 재개 조건 = P1c 가
  `STANDOFF_OPENS_SHAPING` 을 보이고 B0 v4 세계가 봉인된 뒤, 새 계약으로만.
- **중심 이동**: docs/104 Track B (net–kinetic mode 전환) + P1c standoff probe
  (docs/121 결재 대기). 달력상 오늘은 W4 말 — r5 가 W6~W9 에 배치했던 P1→P2 를
  5주 선행 완료한 상태라 buffer 가 크다.
- foundation 자산 확보: P1a 공격자 지도 + P2 의 4-arm × 6-config 곡선 + 궤적
  뷰어 (144 ep) — 보고서 learning-layer 절의 재료가 이미 갖춰졌다.
