# 67 — 외부 리뷰 7 판정 로그 (P95 RED 재사전등록 3안) + 반영

**2026-08-08 · 프롬프트 = `review_prompt_p95_taxonomy.md` · 대상 = P95 RED
(f7a65c6) 재사전등록 3안. 반영 = docs/68 r0 (P95′ 재사전등록 초안, 비준 대기).**

---

## 1. 판정표 (리뷰어)

| 주장 | 판정 | 핵심 이유 |
|---|---|---|
| 1. 역전 = taxonomy/지표 결함, 기전 결함 아님 | **기각** | 총량 단조(508<771<1250)는 exposure duration × intensity 곱이라 "strong 이 진짜 더 반응적" 을 입증하지 못함. 세 진단(T_active/R_route/Σ)이 서로 다른 순서를 낸 것 자체가 **단일 scalar reactivity 라벨의 거부 증거** — 총량으로 기존 taxonomy 를 구제하면 사후 합리화 |
| 2. sprint 역전 = budget 경쟁 교락 | **조건부 유지** | 정합적이나 단독 원인 식별 아님 — **closed-loop state-selection** 대안 병존 (조기 반응 → 이후 상태 자체가 갈라져 CRN pairing 이 동일-상태 비교가 아니게 됨). 허용 문장 = "~와 정합적", "saturation 이 원인" 은 과함 |
| 3. 소급성 오염 프로토콜 | **조건부 유지** | **성능 안 봤다 ≠ 결과 안 봤다.** 새 taxonomy 는 "P95-failure-informed redesign" 으로 명기 (자연스러운 설계였다고 쓰기 금지). 격리: 기존 30판 diagnostic set 영구 봉인 · 새 namespace 1회 실행 · **재실패 시 재탐색 금지** (stop rule 이 신뢰성의 핵심) |
| 4. 3안 판정 | **(a) 기각 권고 / (b′) 수정 후 채택 / (c) 기각** | 아래 §2 |
| 5. 재실행 범위 | **조건부 유지** | P94 **유효 유지** (nominal 한정 증거 — "TRAIN 전역에서 channel 유의미" 로 확대 금지) · P92′ 필수 · P93′ 재실행 권장 (저비용 provenance) · docs/63 최종 동결은 TRAIN hash 확정 후 (rule family **초안은 병렬 작성 가능**, 튜닝·선택 실행은 금지) |

**총평 채택**: P95 RED 는 고칠 오류가 아니라 **gate 가 원래 taxonomy 의
의미론적 오류를 학습 전에 찾아낸 것**이다. 반증된 것은 "gain·sense 동시
증가 → per-active-step realized 도 정렬" 이라는 ordinal 의미론 하나 — 기전
(angular-gap channel)·onset 증가·authority 증가·총 개입 증가는 미반증.
근본 문제 = **"언제부터 반응하는가(onset)" 와 "얼마나 세게 미는가
(authority)" 를 한 축에 묶은 것.**

## 2. 3안 판정 상세

- **(a) 셀 경계 재조정 — 기각 권고.** 실패 모드: ① partial order 붕괴
  (strong 의 sense 를 낮추면 "strong" 의 의미 자체가 모호) ② speed-별
  역전을 쫓다 보면 **gate-passing parameter search** 로 전락 ③ shared
  budget + closed-loop feedback 이 원인이면 경계 이동으로 해결 보장 없음.
  "사전등록에 적힌 구제책" 이라는 사실만으로 정당화 불충분.
- **(b′) route_gain 단독 ordinal + sense nuisance — 채택 권고 (수정안).**
  세 안 중 **결과에 맞춰 숫자를 움직이는 정도가 최소**: gain 범위 불변 ·
  경계 탐색 없음 · 이미 단조인 지표 선택 없음. 바뀌는 것은 factorization
  (의미가 다른 두 변수를 한 축에 안 묶는다) 뿐. 실패 모드 4종 등재: ①
  sense coverage 가 9셀 보장에서 빠짐 → **sense draw 를 episode metadata
  에 전부 기록** + 후속 sensitivity 로 충분 ② gain↑→realized↑ 보장 없음 →
  **P95′ 반드시 필요** ③ naming creep — "strong reactive attacker" 금지,
  정확히 "high route-authority stratum under randomized sensing range" ④
  OOD-CORNER (gain 1.0·sense 60) = **joint OOD corner** 로 재명명 (arm 유지).
- **(c) primary 재정의 — 기각.** "The authors replaced a preregistered
  failed metric with a post hoc metric already known to produce the
  desired ordering." — 반박 불가 공격. 총량은 강도가 아니라 exposure×
  response 지표. 공통 15 m 창도 진입 상태 자체가 달라 동일-상태 비교 아님.

## 3. P95′ (재사전등록 골자 — docs/68 r0 에 전문)

- **P95 RED 는 영구 보존·재해석 금지** (negative preregistered result).
- taxonomy: weak/medium/strong = **route-authority stratum** (gain
  U[0.2,0.4]/U[0.4,0.6]/U[0.6,0.8] 그대로), `reactivity` 명칭 폐기.
  sense_range ~ U[15,45] 전 층 공통 nuisance (paired triplet 은 동일
  sense draw 공유). primary R_route **변경 없음**.
- **판정식 (기존보다 강한 gate — 완화 아님)**: 세 speed regime
  (cruise/sprint/sprint+slowdown) **각각에서** mean 과 median 둘 다
  weak<medium<strong. 나머지 지표는 diagnostic only.
- 프로토콜: namespace `p95_route_authority_confirm` · base 0..29 (regime
  10판씩 사전 배정) · triplet 90 실행 · **confirmatory 1회** (부분 열람
  중단·regime 별 재실행·seed 변경·지표 재선택·경계/sense 재조정 전부
  금지; 인프라 오류만 bit-identical rerun + 별도 로그).
- **Stop rule**: P95′ RED → P95″ 금지. ordinal terminology 폐기, route_gain
  구간은 design bins 또는 continuous nuisance 처리 — 별도 연구 결정으로.

## 4. 순서 (재확정)

```
docs/68 재사전등록 비준 (Hyunjun)
  → P92′ (새 factorization: 결정론/coverage/경계/nesting + 새 분포 hash)
  → P93′ (새 TRAIN hash 의 non-self-defeat certificate — 저비용)
  → P95′ (1회, stop rule)
  → TRAIN 분포 최종 동결/hash
  → docs/63 scripted baseline 최종 동결 (rule family 초안은 병렬 가능)
  → baseline 튜닝/실행 → MARL
```

## 5. 논문 한계절 고정 문장 (리뷰어 초안 그대로 — 영문 유지)

> The original preregistered reactivity taxonomy failed its monotonic
> realized-response gate; although no mission-performance outcomes were
> inspected and the revised route-authority taxonomy was confirmed once on
> a disjoint episode set, the decision to separate sensing range from
> routing gain was informed by diagnostics from that failed gate and
> therefore remains a data-informed modeling revision.

> The failed P95 result is retained as a negative preregistered result
> and was not reclassified as a pass.

## 6. 허용/금지 문장 (즉시 발효)

- 금지: "strong reactive attacker" (naming creep) · "saturation 이 역전의
  원인" (단독 원인 미식별) · "P95′ 통과 = 원 P95 해소" (별개 gate) ·
  P94 를 TRAIN 분포 전역 근거로 확대.
- 허용: "sprint 계열 역전은 shared budget 경쟁 및 closed-loop state
  divergence 와 정합적" · "P94 = nominal 에서의 naturally expressed
  causal channel (taxonomy 와 독립)".

---

*비준 대기 (Hyunjun): docs/68 r0 전문 — (b′) 채택 · P95′ 판정식(3-regime
전부) · 프로토콜/stop rule · P92′/P93′ 재실행 · OOD-CORNER 재명명.
비준 전 (b′) 구현 금지.*
