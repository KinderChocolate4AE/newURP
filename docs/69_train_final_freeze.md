# 69 — 결정 A (무명 design bins) + TRAIN 분포 최종 동결

**2026-08-08 · Hyunjun 결정 (P95′ RED stop rule 트랙의 별도 연구 결정).
결정 = **A: 무명 design bins 유지** — 분포·draw·hash 불변, ordinal claim 만
폐기. B (continuous 화) 는 기각: 세 bin 이 등폭·등확률이라 **marginal
route_gain 분포는 이미 정확히 U[0.2, 0.8]** — B 로 바꿔도 population 분포는
같고 finite-sample stratification·hash·provenance 만 흔든다 (이득 < 비용).**

---

## 1. 명칭 규율 (즉시 발효)

`weak / medium / strong` **완전 폐기.** 새 표기:

```
G1: route_gain ∈ U[0.2, 0.4]
G2: route_gain ∈ U[0.4, 0.6]
G3: route_gain ∈ U[0.6, 0.8]      (각 1/3 등확률 — gain-bin 1/2/3)
```

이 셋의 지위 = **route_gain support 의 balanced sampling strata** 뿐이다.

- 금지: "weak/strong attacker" · "strong route-authority" ·
  "higher-reactivity cell" · "G3 가 G2 보다 실제로 더 강하게 반응한다" ·
  "realized reactivity increases across bins".
- 허용: *"route_gain was sampled through three equal-width design strata
  solely to guarantee balanced coverage of the preregistered [0.2, 0.8]
  support."* + *"strata are not interpreted as an ordinal
  realized-response taxonomy."*
- ★ **코드 내부 키는 legacy identifier 로 유지** (`V3_TRAIN_GAIN` 의
  weak/medium/strong, cell 라벨, 기록 JSON): 이 키들이 분포 hash 입력에
  포함돼 리네임 = hash 변경 = 동결 위반이다. C4 (contact→engagement)
  선례와 동일하게 **코드 심볼 = compatibility name / 서술·보고·논문 =
  G1/G2/G3** 로 분리한다. 매핑은 `scale_v2.GAIN_BIN_NAMES` 한 곳.

## 2. P95 / P95′ 최종 지위 (영구 보존 — 재해석 금지)

- **P95 RED**: route_gain+sense_range 결합 reactivity taxonomy 의 ordinal
  validity 미확립 (results/threat_v3_p95.json, f7a65c6).
- **P95′ RED**: sense 를 공통 nuisance 로 분리해도 route_gain strata 의
  realized R_route ordering 이 3 speed regime × mean·median 에서 미성립
  (results/threat_v3_p95prime.json, c2f4957).
- **여기서 끝**: P95″ 없음 · 새 metric 없음 · boundary/route_gain 조정
  없음 · 추가 taxonomy 탐색 없음.
- cruise 단조 / sprint 계열 불안정은 **diagnostic observation** 으로 가치
  있으나, 최종 claim 은 "shared-budget closed-loop dynamics 에서 route_gain
  strata 의 ordinal realized-response validity 는 confirmatory gate 에서
  확립되지 않았다" 까지. "안정적 ordinal proxy 가 아니다" 는 결과와
  정합적인 해석으로만 (증명된 결론 아님).

## 3. 9셀 구조 유지 (재해석)

9셀 = **3 gain sampling strata × 3 speed regimes** ("3단계 반응성 × 3단계
속도전략" 아님). 셀별 결과 의무 공개 유지. worst-cell penetration 도 유효
— 셀 간 ordinal 관계를 전제하지 않는 지표다. 서술 예: ~~"strong 셀이
예상외로 나빴다"~~ → "G3 × sprint 셀이 가장 높은 penetration 을 보였다".

## 4. 게이트 지위 + TRAIN 최종 동결

| 게이트 | 지위 |
|---|---|
| P92′ | **유효 유지 — 재실행 없음** (A 는 draw/분포 불변) |
| P93′ | **유효 유지 — 재실행 없음** (같은 TRAIN hash) |
| P94 | **유효 유지** — nominal route ON/OFF causal 증거, taxonomy 실패와 무관. TRAIN 전역 확대 금지 유지 |
| P95/P95′ | RED 영구 보존 (§2) |

> ★ **TRAIN DISTRIBUTION FINAL FREEZE**
> hash = `efeffcbf2e24d807` (scale_v2.v3_distribution_hash, parity pin =
> tests/test_contract_parity.V3_DIST_HASH_PIN). draw 코드 변경 없음.
> 이후 변경은 어떤 것이든 새 사전등록 + 새 리뷰 사이클로만.

## 5. 논문 서술 (숨기지 않는다)

> "우리는 원래 3단계 reactivity taxonomy 를 주장했으나 사전등록 gate 에서
> 실패했고, 결과를 보고 다른 metric 으로 PASS 시키지 않았다. 한 번의
> confirmatory redesign 에서도 ordinal validity 가 확립되지 않아 사전등록
> stop rule 에 따라 ordinal interpretation 을 폐기했다. 원래의 gain
> support 와 sampling 분포는 그대로 유지하고, 세 구간은 coverage 를 위한
> design strata 로만 사용했다."

+ docs/67 §5 한계절 고정 문장 2개 병기. 이것은 실패한 gate 의 우회가
아니라 **gate 결과가 논문의 주장 강도를 낮춘 사례**다.

## 6. 실행 큐 (결정 A 이후)

1. ~~A 채택 decision 기록~~ (본 문서)
2. ~~명칭 규율~~ (§1; scale_v2.GAIN_BIN_NAMES + claim scan 패턴 추가)
3. ~~P95/P95′ RED 영구 보존~~ (§2)
4. ~~TRAIN final freeze~~ (§4)
5. ~~P92′/P93′ 재실행 안 함~~ (§4)
6. **docs/63 scripted baseline 설계·비준·freeze** ← 다음
7. fresh MARL smoke (G1/G2 manifest) → 8. hold vs scripted vs MARL →
9. static/active attribution → 10. IID → OOD-CPA 중심 → A4
