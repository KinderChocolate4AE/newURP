# 2026-08-13b — T1 재실행 판독: **Case B** — 반응성이 baseline attainability 를 낮췄으나 경계는 대략 유지

계약: docs/72 사전 수용 규칙 + docs/80 §6 null 조항 + docs/81 P0/P1.
산출물: `results/curve_hold_reactive.json` + **sidecar** `.manifest.json` (P0 이행).
intercept arm (`curve_intercept_reactive`) 은 실행 중 — 이 노트는 hold arm 판독.

## 1. T0(legacy) vs T1(반응형) 대조

| 지표 | T0 legacy | **T1 반응형** | 변화 |
|---|---|---|---|
| EASY / baseline-achievable | 0.83 (253/304) | **0.763** (450/590) [0.727, 0.795] | **−0.07** |
| BAND_AIM / aiming-limited | 1.0 % (3/518) | **1.56 %** (8/512) [0.008, 0.031] | ≈ 동급 (CI 중첩) |
| SHAPING / kinematically infeasible | 0/904 | **0/1598** (Wilson 상한 0.0024) | 0 유지, **상한 더 조임** |
| 50 % 교차 | 23.8 | **22.45** | −1.35 (−5.7 %) |
| 잔여 조준각 ψ 중앙값 | 4.26° | **4.26°** | **불변** |
| a\*(ψ) 예측 | 25.8 | 25.63 | ≈ 불변 |
| 예측 vs 관측 편차 | 7.5 % | **12.4 %** | 악화 |

## 2. 판정 = docs/81 P1 **Case B**

> *"reactive avoidance reduced baseline attainability while the boundary
> remained approximately stable."*

근거: (i) 3-구간 구조 **생존** (0.76 / 0.016 / 0) — 구조 붕괴(Case C) 아님.
(ii) 포획률은 내려갔으나 경계 위치 이동은 −5.7 % 로 작다. (iii) **기전 지표
ψ 가 정확히 불변(4.26°)** — 반응성이 겨냥 병목의 물리를 바꾸지 않았다.

이 조합의 해석: **반응 회피는 "얼마나 잡히는가" 를 낮추지만 "왜 못 잡는가"
(유한 slew) 는 바꾸지 않는다** — controller performance 와 physical bottleneck 이
분리되어 보인 것. 이것이 이번 재실행의 가장 유용한 소득이다.

### 수용 규칙 대조 (docs/72, 실행 전 고정)
- "3-구간 흐려지면 claim 하향" → **해당 없음** (구조 유지).
- "0.83 이 크게 떨어지면 '성립' 대신 baseline-achievable" → 0.763 은 **큰 하락
  아님**. 단 **개명은 그대로 적용** (리뷰어 권고는 하락 여부와 무관).
- "23.8↔25.8 일치가 사라지면 겨냥 병목 headline 폐기" → **사라지지 않음** (12.4 %).
  다만 **7.5 % → 12.4 % 로 약해졌으므로 표현을 한 단계 더 낮춘다**: "검증" 금지,
  **"consistent with"** 유지 + **편차 12.4 % 를 그대로 병기**. headline 은 숫자
  일치가 아니라 *"실용 경계가 운동학적 χ=1 앞에서 먼저 나타난다"*.
- **T0 의 더 예쁜 숫자로 회귀 금지** (P1 Case C 조항이지만 B 에도 적용) — primary
  lineage 는 **T1**, T0 는 mechanism-isolation 으로 강등.

## 3. null 해석 함정 재확인 (docs/80 §6)

포획률이 내려갔으므로 "reactivity does not matter" 문제는 발생하지 않았다. 반대로
**"reactivity matters a lot" 로 과대 해석하는 것도 금지** — EASY 0.83→0.763 은
CI 폭(±0.035)의 2배 수준이고, 이 하락의 원인이 반응성인지 표본 구성 차이인지는
분리 계측하지 않았다 (T0 n=304 vs T1 n=590 으로 대역 분모도 다르다).
허용 문장: *"under the tested angular-gap reactive configuration, baseline
attainability in the low-χ regime decreased from 0.83 to 0.76 while the boundary
location and the residual aiming angle were essentially unchanged."*

## 4. 스코프 문구 (본문 반영 대상)

- 위협: **"tested local reactive threat model / angular-gap reactive configuration"**
  (family 금지 — 단일 점 `route_gain=0.5, sense_range=30`).
- 방어 기준선: **`limiter_mode='hold'` — limiter 가 정지한 구성에서 net 드론 단독**.
  "협력 방어의 성능" 오독 방지용 1문장 필수.
- 감지 반경: 회랑 전장 24 m < 30 m ⇒ 교전 내내 반응 활성 (제약 아님).
- 계보: T0 곡선과 **수치 혼합 금지**, T1 이 primary.

## 4.5 intercept arm (물리 요격 허용 구성) — 완료

| 구간 | T1 net 포획 | T1 **무력화** (net + hard-kill) | T0 참조 |
|---|---|---|---|
| baseline-achievable | 0.717 [0.679, 0.752] | **0.780** | — |
| aiming-limited | **0.006** (3/512) | **0.240** | net 0/226 · 무력화 15.5 % |
| kinematically infeasible | 0/1598 | **0.243** | — |

- **논문의 핵심 대비가 T1 에서 더 선명해졌다**: aiming-limited 구간에서
  **net 포획 0.6 % vs 물리 요격 포함 무력화 24.0 %** (T0 는 0 % vs 15.5 %).
  ⇒ *"간극은 표적에 도달하지 못해서가 아니라 **비파괴 조건(겨냥)** 에서 생긴다"*
  는 §2.3 의 주장이 반응형 위협에서 **더 큰 격차로** 재현됐다. 40배 차이.
- kinematically infeasible 구간에서도 무력화 24.3 % — 즉 **χ≥1 은 "못 맞힌다"가
  아니라 "비파괴로 못 잡는다"** 임이 명확해졌다 (도달 자체는 가능).
- 50 % 교차 21.44 (hold 22.45 보다 더 왼쪽), ψ 예측과의 편차 16.3 %.
  **판정에는 hold arm 을 쓴다** (net 포획 곡선이 논문의 주 지표).
- manifest: `results/curve_intercept_reactive.manifest.json` ✅

## 5. 다음 (docs/81 사슬)

P0 **완료** (hold + intercept + 양쪽 sidecar manifest).
P1 KSAS freeze 5건: ① 78 m/s² 출처 (미확보 시 "declared upper threat bracket" 격하)
② manifest ✅(hold) ③ legacy↔rerun 계약 caveat 1문장 ④ pooled 분모 재확인
⑤ stale docstring 2건 — 특히 `curve_sweep.py` 상단 "50% 교차 24.06 / 6.6 %" 는
**T0 수치**이므로 T1 값과 병기 표기 필요.
