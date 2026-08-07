# 68 — TRAIN route-gain stratum taxonomy 재사전등록 (P95′) r1 — 비준·동결

**2026-08-08 · P95 RED (f7a65c6) 의 P95-failure-informed redesign. 리뷰 7
(docs/67) 의 (b′) 채택 권고 전문 반영. 학습 결과·성능 지표는 어느 시점에도
열람하지 않았다. r0 = 초안 → r1 = Hyunjun **조건부 비준의 수정 3건 이행 후
동결** (§5 비준표): ① P95′ 전 명칭 = **route-gain stratum** (route-authority
는 GREEN 후 결과 서술로만) ② GREEN/RED 해석 제한 (§2.1) ③ P93′ 필수.
숫자·범위·판정식·sample budget·stop rule 구조는 r0 그대로.**

★ **정직성 선언 (리뷰 7 §3)**: 이 재설계는 "원래부터 자연스러운 설계" 가
아니라 **실패한 P95 의 진단(T_active·Σ|realized|·regime 분해)에 의해
정보를 받은 수정**이다. 원 P95 RED 는 영구 보존하며 재해석하지 않는다
(negative preregistered result). 논문 한계절 문장 2개 = docs/67 §5 고정.

---

## 1. 무엇이 바뀌는가 (docs/61 대비 증분 — 그 외 전부 불변)

| 항목 | docs/61 (동결 유지) | 본 문서 (변경) |
|---|---|---|
| 층 A 정의 | (route_gain, sense_range) 결합 "반응성" | **route_gain 단독 = route-gain stratum** |
| sense_range | 층별 U[15,25]/[25,35]/[35,45] | **전 층 공통 nuisance U[15, 45] m** |
| 층 A 명칭 | weak/medium/strong reactivity | weak/medium/strong **route-gain stratum** (`reactivity` 폐기. ★ `route-authority` 는 P95′ 가 검증할 결론이므로 **GREEN 후 결과 서술에서만** 사용 — 이름에 결론 선취 금지. config/bin 이름은 끝까지 `route_gain`) |
| OOD-CORNER | "반응성 외삽" | **joint OOD corner** (gain·sense 동시 TRAIN support 밖) — arm 유지, 재명명만 |
| 그 외 | 층 B (속도 3종) · 능력 브래킷 · spawn · standby U[8,16] · episode_len_train 1100 · IID/OOD 구조 · endpoint | **전부 불변** |

route_gain 구간은 docs/61 값 그대로 (상향·경계 탐색 없음):

```
weak    route_gain ~ U[0.2, 0.4]
medium  route_gain ~ U[0.4, 0.6]
strong  route_gain ~ U[0.6, 0.8]
sense_range ~ U[15, 45]   (전 층 공통 draw — 9셀 sensing coverage 는 층
                           보장에서 빠짐. 대신 sense draw 를 에피소드
                           metadata 에 전부 기록, 후속 sensitivity 분석 몫)
```

명칭 규율 (naming creep 방지): "strong reactive attacker" 금지. P95′ 전
정확한 표기 = "high **route-gain** stratum under randomized sensing range".
GREEN 후에만 "realized route-authority ordering 이 확인됐다" 서술 가능.

## 2. P95′ — route-gain stratum ordinal validity gate (리뷰어 문구 기반)

> **P95′.** P95 RED 는 영구 보존하며 재해석하지 않는다. 실패 진단을
> 바탕으로 sensing onset 과 routing authority 를 단일 ordinal
> "reactivity" 축에서 분리한다. TRAIN 의 weak/medium/strong 층은
> route_gain 만으로 정의하고, sense_range ~ U[15,45] m 는 모든 층에
> 공통인 nuisance draw 로 둔다. Paired triplet 은 동일 sense_range 및
> 모든 비반응 축 draw 를 공유한다. 기존 P95 의 primary metric R_route 는
> 변경하지 않는다.

**primary (불변)**: R_route = (1/T_active) Σ_{t∈active} |a_route,realized(t)|.

**판정식 (결과 전 고정 — 기존 완화가 아니라 강화)**:

```
∀ s ∈ {cruise, sprint, sprint+slowdown}:
    mean(R_weak^s)   < mean(R_medium^s)   < mean(R_strong^s)
  ∧ median(R_weak^s) < median(R_medium^s) < median(R_strong^s)
```

**세 speed regime 전부** 성립해야 GREEN. realized/requested ·
T_active · Σ|realized| 는 diagnostic only — 판정 사용 금지. 인접 층
mean/median 차이와 episode-level ordering 비율은 **diagnostic 으로 의무
보고** (판정 미사용). CI/유의성 검정은 추가하지 않는다 — 이것은 population
inference 가 아니라 TRAIN bin 이름의 semantic sanity gate 다 (r1).

### 2.1 GREEN/RED 해석 제한 (r1 — 증거보다 강한 주장 금지)

> **GREEN**: 사전등록된 비중첩 confirmatory set 에서 route_gain strata 의
> realized R_route ordinal ordering 이 세 speed regime 모두에서 mean·median
> 기준으로 확인됨. 이는 해당 TRAIN taxonomy 의 semantic validity gate
> 통과이며, **route_gain 이 일반적으로 안정적인 realized-authority proxy
> 임을 증명하지 않는다.**
>
> **RED**: 사전등록된 confirmatory set 에서 ordinal validity 가 확립되지
> 않음. 결과의 원인이나 효과크기와 무관하게 **사전등록 stop rule 에 따라**
> weak/medium/strong ordinal terminology 를 폐기한다 (증명에 의한 결론이
> 아니라 사전등록된 연구 의사결정 규칙). P95″ 또는 추가 boundary/metric
> 탐색은 수행하지 않는다.

### 2.2 해석 한계 (사전 등재 — 실패 사유 아님)

sense draw 를 triplet 에서 공유해도 gain 이 다르면 몇 스텝 뒤 closed-loop
상태 자체가 갈라진다 — R_route 는 순수 actuator gain transfer 가 아니라
f(gain, clipping, closed-loop trajectory, encountered geometry) 다.
**이것이 gate 의 목적에 맞다**: 검증 대상은 "같은 상태에서 명령이 커지는가"
가 아니라 "실제 TRAIN closed-loop dynamics 안에서 이 gain bin 들을 ordinal
strata 로 불러도 되는가" 이므로 별도 micro-test 로 정제하지 않는다.

## 3. 실행 프로토콜 (confirmatory 1회)

- 기존 P95 30판 = **development/diagnostic set 영구 봉인** (재사용 금지).
- 새 namespace: `p95_route_authority_confirm` (SHA-256, 기존 draw 와 분리).
- base episode 0..29, **speed regime 사전 배정** (draw 가 아니라 배정 —
  regime 별 판정에 n=10 보장): `0..9 cruise · 10..19 sprint ·
  20..29 sprint+slowdown`. base 마다 weak/medium/strong 3 arm = 90 실행.
- 채널 = hold / fire=never (P95 동일 — 반응성 기하 관측).
- **1회 실행.** 금지: 부분 출력 보고 중단 · 특정 regime 재실행 · seed
  변경 재실행 · mean/median 중 하나만 채택 · 경계/sense 재조정 · 새 지표
  재판정. 예외 = 실행 인프라 오류: 결과 미열람 또는 output invalid 를
  증명하고 **동일 입력 bit-identical rerun** (별도 로그).
- **Stop rule (핵심)**: P95′ RED → **P95″ 를 만들지 않는다.** §2.1 의
  RED 해석 그대로 — ordinal terminology 폐기는 증명이 아니라 **사전등록된
  의사결정 규칙**의 발동이다. route_gain 구간을 design bins 로 둘지
  continuous nuisance 로 둘지는 별도 연구 결정. PASS 가 나올 때까지
  세 번째 taxonomy 를 찾지 않는다.

## 4. 배선 계획 + 재실행 게이트 (비준 후)

- `scale_v2.draw_threat_v3` v2: 셀 draw = 3(route-gain stratum)×3(속도) 유지,
  route_gain 만 층 사상 · sense_range 는 공통 U[15,45] key. metadata 에
  sense draw 기록. `reaction_stratum` 은 P95′ CRN 규약으로 갱신 (triplet
  동일 sense 공유). **분포 hash 갱신 + parity pin 동일 커밋 갱신**
  (test_contract_parity.V3_DIST_HASH_PIN — A4b 규율).
- **P92′** (필수): 결정론 · coverage (9셀 균등 유지) · 경계 전수 · nesting
  — 새 factorization 에서 재실행.
- **P93′** (**필수** — r1): 새 TRAIN hash 의 non-self-defeat certificate
  재확인 (50판 defender 제거 → 50/50 PENETRATED · TRUNCATED 0). 저비용.
- **P94 = 유효 유지** (nominal 한정 증거, taxonomy 와 독립). TRAIN 전역
  확대 인용 금지.
- 순서: **비준 → P92′ → P93′ → P95′ → TRAIN 분포 최종 동결/hash →
  docs/63 최종 동결** (rule family 초안은 병렬 작성 가능, 튜닝·선택 실행은
  TRAIN hash 확정 전 금지). ★ **P95′ 결과를 본 뒤 docs/63 rule family 를
  유리하게 바꾸는 것도 금지** (r1).

## 5. 비준표 (2026-08-08 Hyunjun — r1 로 동결)

```
[v] (b′) 채택: route_gain 단독 ordinal + sense 공통 nuisance      승인
[v] route_gain 구간 불변                                          승인 (사후 difficulty tuning 방지)
[v] sense_range U[15,45] 공통 + metadata 기록 의무                승인 (triplet 동일 draw 공유가 핵심)
[v] 기존 R_route 유지                                             강한 승인
[v] P95′ 판정식 (3 regime × mean·median — CI 추가 없음)           승인 (완화 아님·새 자유도 금지)
[v] 기존 P95 set 봉인 · 새 namespace/30 base · regime 10판 배정   승인
[v] confirmatory 1회 · P95″ 금지                                  강한 승인 (adaptive search 차단)
[v] P92′ 필수 · P93′ **필수** (r1 격상) · P94 유효 유지            승인
[v] OOD-CORNER = joint OOD corner 재명명                          승인
[v] 한계절 고정 문장 2개 (docs/67 §5)                             승인
```

r1 수정 3건 이행: ① 명칭 route-gain stratum (§1) ② GREEN/RED 해석 제한
(§2.1) ③ P93′ 필수 (§4). **비준 완료 — 구현 인가.**
