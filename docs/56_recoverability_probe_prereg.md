# 56 — miss 7판 recoverability probe 사전등록 (2×2 + 별도 switch arm)

**2026-08-06 · 결과를 보기 전에 쓴다. 리뷰 3 후속 계약 2건(early-prep 의미 분리 ·
closed-loop 재실행) 반영. 실행은 다음 세션.**

---

## 0. 질문

V3b 에서 scripted 폴백의 miss 후 무력화가 0/7 이었다 (docs/54). 이 probe 는
그 원인을 분해한다:

> 폴백이 실패한 이유가 (전환 자체가 불가능해서)인가, (miss 확인 후에야 움직여
> 너무 늦어서)인가, (controller 가 약해서)인가?

**결과는 성공률 추정이 아니라 7개 저장 상태에 대한 반증 probe 다.**

## 1. ★ 용어 계약 — "miss−5" 는 조기 handoff 가 아니다

```
T0        기존 계약: net miss 확인(handoff step) 뒤 fallback controller 시작
T−5 prep  handoff step − 5 tick 부터 limiter fallback controller 활성.
          finisher 의 원래 net 발사 결정은 유지 (이미 발사돼 net 은 비행 중).
          = "fallback 선행 준비 / 병렬 pre-positioning". 조기 handoff 아님.
T−5 switch (별도 arm, 2×2 밖) net 전략 자체를 포기하고 destructive 로 완전
          전환. 비손실 기회를 희생하는 다른 정책이므로 2×2 에 섞지 않는다.
```

첫 실행은 **2×2 (T0 / T−5 prep × controller 2종)** 만. T−5 switch 는 2×2
판독 후 별도 사전등록.

## 2. ★ closed-loop 재실행 계약 (고정 궤적 재생 금지)

공격자는 반응형이다. 개입 후 공격자 궤적은 바뀌어야 한다.

```
허용   같은 seed 로 결정론적 재실행 -> branch step 에서 limiter 제어만 전환
       -> 이후 attacker·defender 모두 closed-loop 로 계속 (V2/V3 감사와 동일
       CRN-branch 패턴. 상태 직렬화 불필요 — 재실행이 곧 checkpoint)
금지   원래 miss 에피소드의 공격자 궤적을 고정 + limiter 만 새 controller 로
       이동 (기하적 counterfactual 일 뿐 reactive A2 recoverability 검증 아님)
```

## 3. Arm (2×2)

| arm | 준비 시작 | controller |
|---|---|---|
| T0-INT | 실제 miss 직후 (handoff step) | 기존 intercept |
| T0-ORC | 실제 miss 직후 | privileged oracle/MPC |
| TP-INT | handoff step − 5 부터 병렬 준비 | 기존 intercept |
| TP-ORC | handoff step − 5 부터 병렬 준비 | privileged oracle/MPC |

공통 조건 (전 arm 동일):

- 대상 = V3b hold/clean 의 miss 7판: **ep 2 · 26 · 35 · 46 · 76 · 95 · 98**
  (handoff step 21·21·24·23·21·16·22, `results/handoff_audit.json`)
- `Pk = 1` — **"deterministic lethality 아래의 recoverability upper-bound
  probe"** 로 명시한다. lethality 질문이 아니라 기하 질문이다.
- 동일 contact resolver · 동일 no-kinetic veto · 동일 limiter 소모 계약
  (`contact_resolver=True, miss_terminates=False`)
- net 발사는 원래 규칙(clean) 유지. T−5 시점은 발사 후·해소 전 구간임을
  실측으로 확인해 기록한다 (아니면 그 판은 별도 표기).

## 4. 기록 지표 (판 단위)

```
net capture 여부 · (새) miss 발생 여부와 시각 · contact neutralization ·
commit hard-kill · penetration · 최초 contact 까지 시간 ·
개입 시점의 자산까지 남은 거리 · limiter 별 최소거리와 접촉 순서 ·
limiter 소모 수 · 원래 miss 상태가 개입 후에도 miss 로 남는지
```

★ **분리 라벨**: T−5 prep 개입으로 net 이 맞아 버리면 "fallback 성공"으로
세지 않고 `EARLY_PREP_NET_CAPTURE` 로 분리한다 — limiter 의 조기 움직임이
net 기하까지 바꿨다는 뜻이다.

## 5. privileged controller 자격 (이름만 oracle 인 휴리스틱 금지)

최소 요건 (전부):

- 짧은 horizon 에서 limiter 가속열을 **직접 최적화** (후보열 shooting 가능)
- **attacker 반응을 rollout 에 포함** (cloned env closed-loop)
- 목적함수 = contact/commit 도달 또는 penetration 방지
- backend dynamics 와 action bound 를 정확히 사용 (semi-implicit Euler,
  a_max/v_max clip — `analytic.py:109` 그대로)
- 실패는 `NO_SOLUTION_WITHIN_BUDGET` 으로 기록. **oracle 실패를 물리적
  불가능으로 읽지 않는다** (오류 13 동형).

budget·horizon 등 상수는 구현 시 **실행 전에** 이 문서에 추가 선언한다.

## 6. 해석표 (결과 보기 전 고정)

| 결과 | 허용되는 해석 |
|---|---|
| T0-ORC 0/7 · TP-ORC 성공 | handoff 가 아니라 **시점**이 병목 |
| T0-ORC 성공 · T0-INT 실패 | 기존 fallback controller 가 약함 |
| TP-INT 도 성공 | 값싼 pre-positioning 만으로 회복 가능 |
| 개입 후 net capture 증가 | fallback 뿐 아니라 shaping/net 기하가 바뀜 (`EARLY_PREP_NET_CAPTURE`) |
| 전 arm 실패 | **해당 7개 상태에서** recoverability 결손 증거 강화 (일반화 금지) |
| 일부만 성공 | 상태별 recoverability 이질적 — 단일 "mode change 가능/불가능" 결론 금지 |

## 7. 실행 전 체크리스트

```
[ ] 전체 회귀 + legacy baseline (hold n=500) 비트 동일 재확인
      (반경 키 추가 뒤 — 직렬화·config 경로 회귀 방지)
[ ] privileged controller 구현 + 자격 요건 자기검사 + budget 상수 선언
[ ] T−5 가 발사 후 구간인지 7판 실측
[ ] 2×2 실행 → §6 해석표로만 판독
[ ] (그 뒤) T−5 switch 별도 사전등록
```
