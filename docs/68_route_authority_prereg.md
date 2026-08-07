# 68 — TRAIN route-authority taxonomy 재사전등록 (P95′) r0 — 비준 대기

**2026-08-08 · P95 RED (f7a65c6) 의 P95-failure-informed redesign. 리뷰 7
(docs/67) 의 (b′) 채택 권고를 전문 반영. 학습 결과·성능 지표는 어느 시점에도
열람하지 않았다. r0 = 초안 (Hyunjun 비준 대기) — 비준 전 구현 금지.**

★ **정직성 선언 (리뷰 7 §3)**: 이 재설계는 "원래부터 자연스러운 설계" 가
아니라 **실패한 P95 의 진단(T_active·Σ|realized|·regime 분해)에 의해
정보를 받은 수정**이다. 원 P95 RED 는 영구 보존하며 재해석하지 않는다
(negative preregistered result). 논문 한계절 문장 2개 = docs/67 §5 고정.

---

## 1. 무엇이 바뀌는가 (docs/61 대비 증분 — 그 외 전부 불변)

| 항목 | docs/61 (동결 유지) | 본 문서 (변경) |
|---|---|---|
| 층 A 정의 | (route_gain, sense_range) 결합 "반응성" | **route_gain 단독 = route-authority stratum** |
| sense_range | 층별 U[15,25]/[25,35]/[35,45] | **전 층 공통 nuisance U[15, 45] m** |
| 층 A 명칭 | weak/medium/strong reactivity | weak/medium/strong **route-authority** (`reactivity` 폐기) |
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

명칭 규율 (naming creep 방지): "strong reactive attacker" 금지. 정확한
표기 = "high route-authority stratum under randomized sensing range".

## 2. P95′ — route-authority ordinal validity gate (리뷰어 문구 기반)

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
T_active · Σ|realized| 는 diagnostic only — 판정 사용 금지.

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
- **Stop rule (핵심)**: P95′ RED → **P95″ 를 만들지 않는다.** 결론 =
  "route_gain 조차 closed-loop dynamics 아래 realized authority 의 안정적
  ordinal proxy 가 아니다" → ordinal terminology 폐기, route_gain 구간을
  design bins 로 둘지 continuous nuisance 로 둘지는 **별도 연구 결정**.
  PASS 가 나올 때까지 세 번째 taxonomy 를 찾지 않는다.

## 4. 배선 계획 + 재실행 게이트 (비준 후)

- `scale_v2.draw_threat_v3` v2: 셀 draw = 3(route-authority)×3(속도) 유지,
  route_gain 만 층 사상 · sense_range 는 공통 U[15,45] key. metadata 에
  sense draw 기록. `reaction_stratum` 은 P95′ CRN 규약으로 갱신 (triplet
  동일 sense 공유). **분포 hash 갱신 + parity pin 동일 커밋 갱신**
  (test_contract_parity.V3_DIST_HASH_PIN — A4b 규율).
- **P92′** (필수): 결정론 · coverage (9셀 균등 유지) · 경계 전수 · nesting
  — 새 factorization 에서 재실행.
- **P93′** (권장·저비용): 새 TRAIN hash 의 non-self-defeat certificate
  (50판 defender 제거 → 50/50 PENETRATED · TRUNCATED 0).
- **P94 = 유효 유지** (nominal 한정 증거, taxonomy 와 독립). TRAIN 전역
  확대 인용 금지.
- 순서: **비준 → P92′ → P93′ → P95′ → TRAIN 분포 최종 동결/hash →
  docs/63 최종 동결** (rule family 초안은 병렬 작성 가능, 튜닝·선택 실행은
  TRAIN hash 확정 전 금지).

## 5. 비준표 (r0 — Hyunjun 대기)

```
[ ] (b′) 채택: route-authority 단독 ordinal + sense 공통 nuisance
[ ] route_gain 구간 불변 (U[0.2,0.4]/[0.4,0.6]/[0.6,0.8])
[ ] sense_range U[15,45] 공통 + metadata 기록 의무
[ ] P95′ 판정식 (3 regime × mean·median 전부 — 강화 gate)
[ ] 실행 프로토콜 (봉인·새 namespace·regime 사전 배정·1회·금지 목록)
[ ] Stop rule (RED → P95″ 금지, ordinal 폐기 트랙)
[ ] P92′ 필수 · P93′ 재실행 · P94 유효 유지 (nominal 한정)
[ ] OOD-CORNER = joint OOD corner 재명명
[ ] 한계절 고정 문장 2개 (docs/67 §5)
```
