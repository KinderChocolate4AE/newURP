# 54 — 계약 개정 사전등록: 접촉 resolver · handoff · 인증/임무가치 분리

**2026-08-06 · 결과를 보기 전에 쓴다. `docs/09:1687` 동결 계약의 개정안.**

---

## 0. 개정 근거 — **학습 편의가 아니라 구현 비정합**

동결 계약(`docs/09:1687`)은 *"학습 편의로 미변경"* 이다. 이 개정의 근거는
학습 성능이 아니라 **구현이 비준된 설계를 따르지 않는다**는 것이고, 셋 다
코드로 확인됐다 (docs/53).

| # | 비정합 | 근거 | 지위 |
|---|---|---|---|
| 1 | **접촉 event resolver 부재** | `env_sys.py:239` — 하드킬은 접촉이 아니라 **커밋 비트**로만 발동. 공격자가 `kill_radius` 를 통과해도 아무 일 없음 | 비준 설계 대비 **구현 비정합** (docs/29 §1.1) |
| 2 | **net miss 즉시 종료** | `env.py:356` `spent_fail` 이 종료 조건 | 비준 설계 대비 **구현 비정합** (docs/29 "2모드+1핸드오프") |
| 3 | `v_soft` 비확률성 | `_assemble` 의 union 은 블록별 밀도 상이·확률질량 가중 없음 | **지표 의미 불일치** (포획확률로 *쓸 때* 오류) |

### 0.1 ★ 우선순위가 실측으로 뒤집혔다 (docs/53 §4.5b)

boxed 상태 17 판 3-arm 감사:

```
A  현행·무발사        접촉 0.765  침투 1.000       <- 접촉해도 아무 일 없음
C1 종료만 억제        침투 0.941                    <- 거의 안 바뀐다
C2 + 접촉 resolver    침투 0.235  무력화 0.706      <- 여기서 회복
```

**따라서 #1(접촉 resolver)이 #2(handoff)보다 먼저다.** handoff 만 넣으면
폴백이 여전히 커밋 비트에 의존해 작동하지 않는다.

---

## 1. 개정 항목 (선언)

### R1 — 접촉 event resolver ★ 최우선

```
공격자와 limiter 의 거리가 kill_radius 이하가 되면 **무력화 event** 를 발생시킨다.
```

선언값 (결과 보기 전 고정, 스윕하지 않는다):

```
판정        d(p_att, p_lim_i) <= kill_radius     (기존 kill_radius 재사용, 새 값 없음)
해소        기존 커밋 경로와 **같은 확률 모형** (Bernoulli Pk, no-kinetic 거부권)
            -- 새 성공 경로를 만드는 게 아니라 **발동 조건만** 커밋 -> 접촉으로 확장
limiter     소모된다 (기존 커밋과 동일). retired 처리도 동일
라벨        HARD_KILL (신설하지 않는다)
```

**`boxed_in` 을 성공으로 재라벨링하지 않는다.** 무력화는 **실제 접촉 event 가
발생했을 때만** 채점한다 (docs/53 §4.5 규율).

#### R1 세부 계약 (2026-08-06, 구현 전 추가 선언)

- **검출은 swept 다.** 상대 선분 `r0 = p_att(t)−p_lim(t)`, `r1 = p_att(t+1)−p_lim(t+1)`
  의 원점 최소거리 `d_min <= r_contact` (경계 **포함**). endpoint 만 보면 한 스텝
  안의 통과를 놓친다. 백엔드 적분은 등가속(곡선 경로)이므로 선분 검사는 **근사**다
  — 이산 격자 계약(오류 9)과 같은 지위로 명시한다: env-faithful 하되 연속시간
  안전성을 자동 주장하지 않는다.
- **반경 이름 분리**: `SystemSpec.r_contact`, 기본 `None` → `inner.kill_radius`
  재사용. **새 값은 만들지 않는다** (위 선언 유지). 이름만 분리해 shaping /
  commit / contact 의미가 조용히 함께 바뀌는 것을 막는다.
- **해소 시점 = 접촉 스텝 즉시** (`tau_kill` 지연 없음). 지연은 예측 요격의
  sense+decide 모형이고, 접촉은 그 요격이 **이미 일어난** 사건이다.
- **해소 사슬은 커밋 경로와 동일**: NK veto(해소 시점 `d_asset <= r_nk`, limiter
  **미소모**, 이후 재접촉 시 재평가) → 소모·retire → `Bernoulli(Pk)` →
  KILL / PK_FAIL. 기하 검사는 없다 — 접촉 자체가 기하다.
- **event 우선순위·중복 방지** (P80):
  1. 같은 스텝에서 **커밋 해소가 먼저**, 접촉은 그다음. `pending` limiter 는
     접촉 검사에서 **제외** — 커밋은 바로 그 접촉의 예측이므로 이중 소모 금지.
  2. `retired` limiter 제외.
  3. KILL 1회 후 잔여 접촉 미평가 — 공격자 terminal success 는 1회.
  4. 라벨 우선순위는 기존 동결 규약 그대로 (`_outcome_label` / mission_rollout):
     HARD_KILL > CAPTURE > PENETRATED. 변경하지 않는다.
- **provenance**: `CommitRecord.source = "commit" | "contact"`. 라벨은 HARD_KILL
  재사용(신설 없음), 분석은 `source` 로 분리한다.
- **V2 실현·수락대역 (결과 보기 전 고정)**: `boxed_arm_audit` 에 **C2R arm**
  (= C1 종료억제 + **실 resolver**, 프로토타입 인라인 resolver 미사용) 추가.
  동일 boxed 17판에서
  `|무력화 − 0.706| <= 0.15 ∧ |침투 − 0.235| <= 0.15`.
  이탈 시 (NK veto 수 · swept 추가 검출 수 · Pk) 로 분해해 원인 귀속 전 진행
  금지. **프로토타입과의 선언된 차이**: endpoint→swept, 즉시 무력화→NK veto+Pk
  경유 — 차이가 이 두 축으로 설명되면 방향 재현으로 인정한다.
- **P78 실현**: 기본값(`contact_resolver=False`)에서 새 분기는 실행 자체가 안
  된다(구조적 동일) + 회귀 테스트로 궤적·보상·종료를 비트 대조. hold n=500
  재현은 V2 감사와 같은 세션에서 1회 실행해 기록한다.
- **결과를 본 뒤 이 판정식·대역을 바꾸지 않는다.**

### R2 — `NET_MISS` 를 mode transition 으로

```
NET_CAPTURE  -> 성공 종료
NET_MISS     -> FALLBACK_MODE (에피소드 계속) -> R1 접촉 / 커밋 하드킬 / 침투
```

`SPENT_FAIL` 은 **라벨로 유지**하되 종료 조건에서 뺀다. 종료는 침투·절단·무력화.

### R3 — robust-clean 인증과 임무 성공의 분리

```
v_shot_worst == 1        지위 변경: 유일 성공 술어  ->  robust-clean **인증 플래그**
NET_CAPTURE              실제 포획 event
BOXED                    관측·인증 플래그로만. 그 자체로 성공/실패 아님
```

임무 보상은 결과 기반:

```
R = R_net·1[NET_CAPTURE] + R_hk·1[HARD_KILL] − c_lim·N_lost − c_pen·1[PENETRATED]
```

`w_kill` 은 `R_net` 대 `R_hk` 의 비를 정하는 **기존 축을 그대로** 쓴다.

### R4 — frontier 평가

단일 성공률 대신 **동시 보고**:

```
비손실 포획률 · 전체 무력화율 · 하드킬 전환율 · limiter 손실 · 침투율 ·
net 사용률 · wasted fire · handoff 성공률 · robust-clean 인증률
```

---

## 2. ★ 회귀 방어 — 기본값은 **현행과 비트 동일**

```
SystemSpec.contact_resolver   기본 False   -> R1 off
SystemSpec.miss_terminates    기본 True    -> R2 off  (현행 동작)
```

두 플래그가 기본값이면 **기존 25 런·모든 기저선·docs/48~52 의 수치가 그대로
재현돼야 한다.** 이걸 P78 이 강제한다. 개정판 결과는 플래그를 켠 **새 대역**
으로만 보고하고, 기존 수치와 같은 표에 섞지 않는다.

---

## 3. 판정 (선언)

개정 자체는 "성능이 오르는가" 로 판정하지 않는다 -- **비정합 해소가 목적**이다.
검증은 다음 셋이다.

```
V1  기본값에서 기존 결과 비트 재현                      (P78)
V2  R1 on 에서 docs/53 §4.5b 의 C2 수치가 재현되는가
      boxed 17 판에서 무력화 ~0.706 · 침투 ~0.235
V3  R2 on 에서 net miss 뒤 에피소드가 계속되고 폴백이 발동하는가
```

**성능 비교는 그다음이고, §4 의 3-way 없이는 "물리 한계" 라고 쓰지 않는다.**

## 4. 개정 뒤 첫 실험 — oracle / scripted / RL 3-way

같은 목적함수(R3)에서 셋을 비교한다:

```
trajectory optimization / MPC oracle   상한
strong scripted controller             손설계 기준
learned policy                         측정 대상
```

오라클과 RL 이 붙으면 그 부근이 환경의 물리적 frontier, 벌어지면 알고리즘
격차다. 이 비교가 **"학습이 어디까지 가능한가" 의 유일한 정직한 형태**다.

---

## 5. 무엇을 답하지 못하는가

- **R1 의 확률 모형은 커밋 경로에서 빌려 온 것**이다. 접촉 무력화의 실제 Pk 가
  커밋 무력화와 같다는 근거는 없다. 새 자유도를 안 만들려고 재사용했을 뿐이고,
  이 선택 자체가 한계다.
- **R2 는 폴백을 "계속 진행" 으로만 정의**한다. 재장전·2 차 방어선·자산 회피는
  범위 밖이다.
- **`v_soft` 비확률성(#3)은 이 개정으로 안 고쳐진다.** R3 가 지표를 분리할 뿐,
  `v_soft` 를 확률로 만들려면 공격자 정책 rollout 기반 추정이 따로 필요하다.
- docs/52 의 knife-edge 는 **개정 전 계약에서의 robust-clean certificate 측정**
  이다. 개정 뒤 frontier 와 같은 표에 올리지 않는다.

---

## 6. 테스트 (짜기 전에 선언)

```
P78  두 플래그 기본값에서 기존 경로와 **비트 동일** (hold 기저선 n=500 재현 포함)
P79  R1 on: 접촉이 실제로 event 를 만들고, limiter 가 소모되며,
     no-kinetic 거부권이 접촉 경로에도 동일하게 걸린다
P80  R1 은 **접촉 시에만** 발동한다 -- boxed_in 이 True 라도 실제 접촉이 없으면
     아무 일도 일어나지 않는다 (★ 재라벨링 방지)
P81  R2 on: net miss 뒤 에피소드가 계속되고 SPENT_FAIL 이 라벨로만 남는다
P82  R1·R2 조합에서 종료 조건이 침투·절단·무력화 셋뿐이다
```

---

## 7. 다음

```
[ ] R1 배선 + P78~P80
[ ] V2 검증 (C2 수치 재현)
[ ] R2 배선 + P81~P82
[ ] R3·R4 (지표 분리·frontier 집계)
[ ] 3-way 비교 (§4)
```
