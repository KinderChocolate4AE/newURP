# 66 — terminal-event precedence truth table (B1 trace + B3, r1 비준)

**2026-08-08 · docs/65 사다리 [3]~[4]. B1(semantics trace) = 완료,
B3(truth table) = **r1 비준 완료** (§5 비준문). Q1/Q2/Q4 PASS ·
Q3 CONDITIONAL PASS(명칭/지위 분리 — 본 r1 에 반영, 조건 충족).
[4] 게이트 통과 — 다음 = B2(명시 분기) → B4(행 단위 테스트) → full
regression. reward-weight 튜닝·기타 계약 변경 비인가.
코드 앵커 기준 = 5d1a3b6 (contract parity 복구 후).**

---

## 1. B1 — CAPTURE_WITH_CONTACT 를 만드는 것 (trace 결과)

### 1.1 술어가 **두 개** 존재한다 (신규 발견)

| 측 | 위치 | CWC 술어 |
|---|---|---|
| **보상** (terminal 라벨) | env_sys.py:468 `_outcome_label` | capture 종료 tick 에 **그 순간** ∃ limiter: ‖p_att − p_lim‖ ≤ kill_radius (park 된 limiter 는 60 m 밖이라 자동 제외) |
| **지표** (canonical 라벨) | mission_rollout.py:257,273,338 | outcome CAPTURED ∧ **에피소드 중 한 번이라도** 접촉했던 limiter 집합 ≠ ∅ |

즉 "스텝 10에 스치고 스텝 50에 깨끗이 포획" 이면 **지표 = CWC, 보상 라벨 =
NET_CAPTURE(+1.0)** 로 갈라진다. 반대 방향(보상 CWC ∧ 지표 NET)은 불가능
(순간 접촉 ⊂ 에피소드 접촉).

### 1.2 tick 내 처리 순서 (env_sys.step, 코드 확정)

```
§2  커밋 등록 (정책 커밋 비트)
§3  동결 env 한 스텝 (captured / penetrated / FSM SPENT / 지평선)
§3b R2 handoff -- spent-fail 종료만 억제 (captured/penetrated/hard_kill 은 절대 억제 안 함)
§4  만료 커밋 해소: NK VETO(미소모) → GEOM_FAIL / Bernoulli(Pk) → KILL / PK_FAIL (소모)
§4b R1 접촉 해소 (pending·retired 제외, hard_kill 후 skip): VETO / KILL / PK_FAIL. 즉시 해소
§5  소모 limiter park (0,0,60)
§6  hard_kill → 전원 종료 강제
§6b 라벨: HARD_KILL > captured(순간 근접 → CWC/NET) > PENETRATED > TRUNCATED > SPENT_FAIL
```

### 1.3 비준 분기 기준(docs/65 §3) 대입 — 판정

1. **"net 성공 + engagement geometry 동반, kinetic 미발생"** — **CWC 는 정확히
   이것이다.** 같은 tick 에 파괴적 kill 이 실제로 발생하면(§4/§4b KILL)
   §6b 순서가 **항상 HARD_KILL 로 라벨**하므로, CWC 라벨에 destructive
   neutralization 이 섞여 들어올 경로가 코드상 없다.
2. **"destructive 발생인데 CWC 로 명명"** — **발생하지 않음** (위 순서 보장).
   단 역방향 masking 이 존재한다: capture 와 KILL 이 같은 tick 이면 포획
   성공이 HARD_KILL 로 덮인다 (§3 표 행 6 — 비준 확인 필요).
3. **"NK veto + capture 중첩"** — 발생하며 CWC 를 만든다: veto 는 미소모라
   limiter 가 공격자 곁에 남고, 그 상태에서 포획되면 순간 근접이 참.
   kinetic 은 보류됐으므로 **nondestructive 가 맞다.**

**결론 (B1)**: CWC = nondestructive capture 이며, 비준 원칙에 따라
`R_terminal(CWC) = R_terminal(NET_CAPTURE) = +b_net` 이 정당하다 (분기 1).
추가로, (a) 채택 시 §1.1 의 두-술어 divergence 는 **보상 측에서는 무해화**
된다 (어느 술어든 +b_net 동일) — 지표 측 순도 수식어(NET vs CWC)로만 남는다.

## 2. B3 — terminal-event precedence truth table (초안, 비준 대상)

전제: F-계약 (R1 on · R2 on), Pk 는 선언 축. "engagement" = R1 swept 접촉
event (구 명칭 contact). 라벨 열은 §1.2 순서의 결과다.

| # | tick 조합 | 처리 | final label | terminal 보상 (제안) | limiter 소모 | net |
|---|---|---|---|---|---|---|
| 1 | net capture only | §3 captured → §6b | NET_CAPTURE | +b_net | 0 | spent |
| 2 | engagement only · NK 밖 · Pk 성공 | §4b KILL → hard_kill | HARD_KILL | +b_net(1−w_kill) | 1 | 불변 |
| 3 | engagement only · NK 밖 · Pk 실패 | PK_FAIL 소모·park, 계속 | (종료 아님) | 없음 · c_lim 증분 −0.1 | 1 | 불변 |
| 4 | engagement · NK 안 | VETO 미소모, 계속 | (종료 아님) | 없음 (dense −λ3 재계수만) | 0 | 불변 |
| 5 | net capture + 순간 근접 (veto 잔류 등) | §3 captured ∧ §6b 근접 | **CAPTURE_WITH_CONTACT** | **+b_net (제안 = NET 동일; 현행 0.0 은 우연한 else)** | 조건부 | spent |
| 6 | net capture + engagement KILL **같은 tick** | §6 hard_kill 우선 | HARD_KILL | +b_net(1−w_kill) | 1 | spent | 
| 7 | net miss (R2) | §3b spent-fail 종료 억제, handoff | (종료 아님) `net_spent=True` | 없음 · dense −λ2 1회 (miss 무벌점 아님) | 0 | spent |
| 8 | miss 후 later engagement | 행 2/3/4 와 동일 | (해당 행) | (해당 행) | | spent |
| 9 | SPENT_FAIL 종료 (R2 off 세계 한정 / R2 on 은 행 7 로 대체) | §3 | SPENT_FAIL | 0.0 (선언 중립, docs/26) | — | spent |
| 10 | penetration | §3 | PENETRATED | −c_pen | — | — |
| 11 | truncation (지평선) | §3/§3b | TRUNCATED | −c_trunc (보상) / 지표 우측절단 (선언 분리) | — | — |
| 12 | **과거-접촉 후 clean capture** (PK_FAIL park 등) | §6b 순간 근접 거짓 | 보상 라벨 NET_CAPTURE / **지표 라벨 CWC** | +b_net (제안 후 값 동일 → 무해) | 이력 1 | spent |

주 6 (**r1 비준**): capture 가 destructive 로 masked 되는 유일한 행. 현행
유지 — 1차 endpoint 가 NET_CAPTURE 이므로 동시 사건을 NET 우선으로 하면
nondestructive 성과를 과대계상할 위험이 있다. **단, 이것은 discrete-event
precedence convention 이다 — 50 ms tick 내부에서 destructive neutralization
이 net capture 보다 물리적으로 먼저 일어났다는 주장이 아니며, 물리
시간순서 주장으로 확장 금지.**

주 12 (**r1 비준, Q3 조건 반영**): 두 술어는 서로 다른 질문이므로 통일하지
않는다 — reward 측 = **terminal-state property** (종료 순간 근접) / 지표 측
= **trajectory-history purity qualifier** (에피소드 중 engagement 이력).
단 **같은 terminal label 이름을 공유하지 않는다**: terminal/reward 어휘는
`NET_CAPTURE`/`CAPTURE_WITH_CONTACT`(same-tick qualifier), 지표 측 이력
술어는 분석 수식어 **`had_prior_engagement`** (또는
`capture_with_prior_engagement`) 로 표기·문서화한다. mission_rollout 의
집합 술어는 terminal label 이 아니라 **episode-history 분석 수식어**다 —
CONTACT_NEUTRALIZATION(G03)과 같은 semantic debt 재발 방지.

## 3. B2 구현 스펙 (비준 후 그대로 반영)

`RewardSpec.terminal` (env_sys.py:174) 에 명시 분기 1줄:

```python
if label in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT"):   # 비준: 동일 utility class
    return self.b_net
```

+ docstring 의 TERMINAL 표에 CWC 행 추가 (우연한 else 경유 제거). 순서
불변식은 `NET_CAPTURE = CWC > HARD_KILL > PENETRATED = TRUNCATED` 로 갱신.

## 4. B4 — executable test 목록 (비준 완료, 구현 대기)

1. terminal truth table 행 1·2·5·6·9·10·11 의 라벨·보상 일치 (합성 상태 유닛).
2. 행 5: veto 잔류 + capture → CWC ∧ terminal == b_net.
3. 행 6: 같은 tick KILL+captured → HARD_KILL (masking 계약 고정,
   NET_CAPTURE 계상 금지).
4. ★ 행 12 canonical regression: **"step 10 proximity → step 50 clean
   capture"** → terminal reward +b_net ∧ 분석 수식어
   had_prior_engagement=True (이번 B1 divergence 를 정확히 재현하는 고정
   테스트).
5. engagement + NK veto + later capture → nondestructive utility ∧
   had_prior_engagement=True.
6. net miss + R2 handoff + later engagement KILL → HARD_KILL.
7. net miss + 회복 없음 + penetration → PENETRATED.
8. 순서 불변식 재검 (기존 테스트 갱신: CWC = NET 동등,
   NET = CWC > HARD_KILL > PENETRATED = TRUNCATED).

## 5. 비준문 (Hyunjun, 2026-08-08 — 원문 고정)

```text
§5 RATIFICATION — 2026-08-08

Q1 PASS:
CAPTURE_WITH_CONTACT terminal utility is assigned to the
nondestructive-capture class:
R_terminal(CWC) = R_terminal(NET_CAPTURE) = +b_net.

Q2 PASS:
Same-tick capture + destructive KILL retains existing HARD_KILL
precedence. This is a discrete-event precedence convention and
does not assert sub-step physical temporal ordering.

Q3 CONDITIONAL PASS:
Reward-side terminal proximity predicate and episode-history
capture-purity predicate remain intentionally distinct.
The history predicate must be represented/documented as an
analysis qualifier, not as the same terminal-label semantics.

Q4 PASS:
After Q3 semantic/name separation is reflected in docs/66,
proceed B2 → B4. No reward-weight tuning or other contract
change is authorized.
```

Q3 조건(명칭/지위 분리)은 본 r1 의 §2 주 12 로 반영 완료 — [4] 게이트 통과.
진행 순서 고정: **B2 (명시 branch, 우연한 else=0 제거 — 큰 refactor 금지)
→ B4 (§4 행 단위 테스트) → full regression.**

---

*B5(limiter 이중 벌점 trace)는 Task 2 감사 §6 에 이미 기록돼 있다 — c_lim
(이벤트 1회, env_sys:379-385) + λ3(상태 재계수, env.py:360, R1 on 시 NK-안
veto 잔류 구간만 지속). 값 튜닝 없음. 추가 발견 없으면 그 기록이 B5 완료다.*
