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

#### R2 세부 계약 (2026-08-06, 구현 전 추가 선언 — R1 V2 통과 후)

- **`SystemSpec.miss_terminates` 기본 `True`** (§2 선언 그대로) = 현행 동작.
  `False` 일 때만 아래가 활성화된다. env.py 는 동결 유지 — 종료 규칙 변경은
  래퍼(ModeSystemEnv)의 관할이다 (docs/29 §6 의 래퍼 존재 이유와 동일).
- **억제 판별**: inner 종료 ∧ `captured=False` ∧ `penetrated=False` ∧
  `fsm.state is SPENT` ⇒ spent-fail 종료 (env.py:356 의 유일한 잔여 원인).
  이때만 `terms` 를 전부 False 로 억제하고 `inner.agents` 를 복구한다.
  captured / penetrated / hard_kill 종료는 **절대 억제하지 않는다**.
- **절단 복구**: 억제 후 inner 는 `terminated_flag` 가 계속 True 라 자체 절단을
  내지 못한다 → 래퍼가 `_step_i >= episode_len` 에서 `truncs=True` 를 낸다.
  (동결 env 의 절단 의미와 동일 술어·동일 지평선.)
- **fire no-op**: FSM 의 SPENT 는 흡수 상태고 fire 는 이미 no-op
  (`finisher_fsm.py:113`) — 새 배선 없음, P81 이 성질만 검증.
- **provenance**: 억제 발생 시 `net_spent=True` + 전이 스텝에만
  `net_miss_handoff=True` 를 info 로 기록. **`NET_MISS_HANDOFF` 는 terminal
  집계 대상이 아니다.** `SPENT_FAIL` 라벨은 이 경로에선 더 이상 종료 라벨로
  나오지 않는다 (분석은 `net_spent` 로 "net spent before failure" 를 복원).
- **보상**: 억제된 스텝은 `done=False` 라 종말항이 붙지 않는다. 최종 실 종료
  (침투·절단·무력화)의 라벨로만 종말항이 1회 붙는다 — `SPENT_FAIL` 종말값이
  0 이었으므로 (docs/26 중립 선언) 기존 대역과 충돌 없음.
- **P81/P82 실현**: P81 = 강제 miss 픽스처에서 (기본값: miss 스텝 종료·라벨
  SPENT_FAIL) vs (`miss_terminates=False`: 에피소드 계속, `net_spent=True`,
  `wasted_fire=1`, fsm SPENT 유지, 최종 라벨 ∈ {PENETRATED, TRUNCATED,
  HARD_KILL}). P82 = R1+R2 동시 on 에서 종료 라벨이 침투·절단·무력화(포획
  포함)뿐임을 seed 스윕으로 확인.
- **V3 실현·판정 (결과 보기 전 고정)**: boxed 감사에 **F arm** (= 스크립트
  종료억제 **없이** `miss_terminates=False ∧ contact_resolver=True` 실 플래그만)
  추가. 판정: (a) miss 후 즉시 종료 0건 (b) 폴백 무력화 발생 (c) SPENT_FAIL
  종료 0건. 2차 기대: C2R (1.000 / 0.000) 과 ±0.15 — C2R 과 F 는 같은 물리에
  스캐폴드만 다르므로 크게 어긋나면 억제 구현 결함을 의심한다.
- **결과를 본 뒤 이 판정식을 바꾸지 않는다.**

#### V3 결과 (2026-08-06, boxed 17 판 — `results/boxed_arm_audit_v3.json`)

```
F   침투 0.000 · 하드킬/무력화 1.000 · 종료 스텝 17   (C2R 과 ±0.15 내 -- 2차 충족)
    net_spent_frac 0.000  ★ miss 가 한 판도 발생하지 않았다
```

- (a) 공허 충족 (miss 0건) · (c) 충족 · 2차 충족.
- **(b) 는 이 표본에서 검정 불가.** boxed regime 에선 접촉 kill 이 net 해소
  (tau_deploy+tau_lock, 수 스텝)보다 항상 먼저 나서 net 이 SPENT 에 도달하지
  못한다 — 처치(miss→handoff)가 활성화되지 않는 arm 이다 (오류 2 자기 인지).
  P81 이 handoff **기제**를 단위 수준에서 강제하지만, env-faithful 한
  "miss 후 폴백 무력화" e2e 표본은 아직 없다.

#### V3b 사전등록 (2026-08-06, ★ 결과 보기 전 — miss 가 실재하는 표본에서 (b) 재검정)

- **도구**: `handoff_audit` — V2/V3 감사와 동일 스택(`_kw`: A2 jink 0.6 ·
  SpawnSpec · 위협 랜덤화) + `fire_mode="clean"` (hold/clean 기준선은 n=500 에서
  SPENT_FAIL 32/500 = miss 가 실재하는 유일한 확인 표본), n=100, seed0=0.
- **arm** (전부 `contact_resolver=True ∧ miss_terminates=False`):
  - `hold`      폴백 효과기 없음 (hold limiter 는 접촉·커밋 불가) → miss 후
                침투/절단 예측. handoff 가 **국면 전환**으로 작동하는지만 본다.
  - `intercept` 폴백 효과기 있음 (추격 → 접촉) → miss 후 무력화 표본 기대.
- **판정 (성능 대역 없음 — 기술 검증)**:
  (i) SPENT_FAIL 종료 라벨 0건
  (ii) `net_spent=True` 판 ≥ 1 (아니면 이 표본도 검정 불가로 기록)
  (iii) intercept 팔에서 `net_spent ∧ 무력화` ≥ 1 판 → **(b) 실증**
  (iv) hold 팔의 net_spent 판 결말 분해(침투/절단) 보고 — 무력화 요구 안 함
- **결과를 본 뒤 이 판정식을 바꾸지 않는다.**

#### V3b 결과 (2026-08-06 — `results/handoff_audit.json`, n=100×2)

```
hold       SPENT_FAIL종료 0 · net_spent 7 · miss후 무력화 0/7 (전부 침투)
intercept  SPENT_FAIL종료 0 · net_spent 7 · miss후 무력화 0/7 (전부 침투)
           (전체: NET_CAPTURE 16 · HARD_KILL 35 · PENETRATED 49)
```

- (i) ✓ (ii) ✓ — **국면 전환은 작동한다**: miss 7판이 즉시 종료 대신
  30여 스텝을 더 진행했고 SPENT_FAIL 종료는 0이다.
- (iv) hold miss판 7/7 침투 (예측대로 — 폴백 효과기 없음).
- **(iii) ✗ — miss 후 폴백 무력화 0/7.** 기전 (ep2 추적): miss 시점 limiter-
  공격자 간격 ~8–11 m, 공격자 궤적은 두 팔에서 동일(limiter 가 repel 반경
  1 m 밖 — 영향 0), intercept 폴백은 침투 시점까지 10.9→6.8 m 이 최선.
  즉 **꼬리 추격 기하** (docs/29 §12.2 "꼬리 추격 불가·선도 차단 가능" 정합).
- **증거 범위를 정확히 (리뷰 3 §5 반영 — "전술 난이도 신호" 표현 철회)**:
  R2 의 국면 전환 기제는 P81 + (ii) 로 검증됐다. 허용되는 문장은 이것뿐이다:

  > handoff transition 은 구현됐으나, 평가된 miss 7건에서 현재 scripted
  > controller 는 neutralization 을 만들지 못했다. 원인이 (i) miss-conditioned
  > state selection (미스가 나는 판 = 이미 불리한 조건부 분포) (ii) scripted
  > 폴백의 straw man 가능성 (두 arm 이 공격자 전이에 인과효과 0 = 실질 동일
  > 처치) (iii) 늦은 handoff 시점 (net 완전 실패 후에만 폴백 시작)
  > (iv) n=7 표본 (v) contact model/resolver 의미론 미검증 중 무엇인지는
  > **미판정**이다.

  판정 도구 = 2×2 counterfactual replay (handoff 시점 {miss, miss−5tick} ×
  controller {intercept, privileged MPC/oracle}) + recoverability curve.
  §4 의 3-way 로 이관하되, 이 replay 가 그보다 싸고 먼저다.

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

### 3.1 ★ V2 결과 (2026-08-06, boxed 17 판 — `results/boxed_arm_audit_v2.json`)

| arm | n | 접촉(endpoint) | 침투 | 무력화 | 종료 스텝 |
|---|---:|---:|---:|---:|---:|
| C1 종료 억제 | 17 | 0.706 | 0.941 | 0.000 | 25 |
| C2 프로토타입 | 17 | 0.706 | 0.235 | 0.706 | 24 |
| **C2R 실 R1 resolver** | 17 | 0.235* | **0.000** | **1.000** | 17 |

(*C2R 의 "접촉" 열은 endpoint 진단인데 resolver 가 그 전에 kill 해 낮게 찍힘)

**수락대역 밖이다**: |1.000−0.706| = 0.294 > 0.15, |0.000−0.235| = 0.235 > 0.15.
사전등록 규율대로 진행을 멈추고 선언된 축으로 분해했다:

```
NK veto        0 / 17 판  (접촉 시점 d_asset 전부 r_nk=6 밖)
Pk             0 실패     (p_kill=1)
swept 축       전량 설명:
  12 판  프로토타입과 동일 event, 동일 스텝(±1) kill
   5 판  swept 단독 검출 (ep 19·42·44·47·57) -- endpoint 는 스텝 사이
          통과를 놓쳤고 그 판들이 프로토타입의 침투 0.235 전부였다
```

kill event 의 `d_nom` 분포 = 0.056~0.748. 선분 근사 오차 상한
`a_rel·dt²/8 = (77.3+27.1)·0.05²/8 ≈ 0.033 m` 기준, 경계 여유(0.75−d_nom)가
그 안에 드는 kill 은 **2/17 (ep19 0.019 · ep47 0.013)** 뿐 -- 나머지 15 판은
근사에 강건하다. (역방향 오차도 동일 한계로 존재: 이산 격자 계약이므로
`d_cont >= d_sampled − 0.033` 까지만 주장한다, 오류 9 규율.)

**판정 (2026-08-06 외부 리뷰 3 반영, 두 줄로 분리 보고한다)**:

```
V2 primary numerical replication      FAIL   (대역 ±0.15 밖)
V2 preregistered mechanistic attribution  PASS   (swept 축 사건 단위 귀속)
```

C1 0.941 침투 → C2R 0.000, 무력화 0 → 1.000 -- resolver 부재가 병목이라는
docs/53 §4.5b 의 인과 방향은 유지되고, 초과분은 swept 가 endpoint 상위집합
(같은 event 는 같거나 이른 스텝에 검출 + 통과 5판 추가)이라는 **선언된 차이
축**으로 귀속된다. 대역·판정식은 사후 변경하지 않으며, "V2 통과" 라는 표현은
쓰지 않는다.

**contingency (리뷰 3 §2 요구)**: 무력화 +5 vs 침투 −4 의 잔여 1판 = **ep44**,
프로토타입에서 무력화도 침투도 아닌 무결말(지평선)이었다. 즉
`+5 무력화 = −4 침투 −1 무결말`, 누수 없음. swept-only 5판의 C2 결말 =
침투 4 (ep19·42·47·57) + 무결말 1 (ep44).

**잔여 caveat (리뷰 3)**: "같은 event ±1 스텝" 은 완전한 사건 동치가 아니다 --
1 tick 차이가 다른 terminal 과의 우선순위를 바꿀 수 있는 사례는 이 17판에선
관측되지 않았으나 일반 보장은 없다. 무력화 1.000 은 **`Pk=1` contact-event
semantics check** 이지 성능 추정치가 아니다 (Pk sweep = §3.2).

**남는 것**: 프로토타입의 0.706/0.235 는 endpoint 검출의 산물이었다 -- 실 계약
(swept) 아래 boxed 상태의 실측 무력화는 이보다 높다. 이 수치를 boxed 상태
일반의 포획확률로 읽지 않는다 (17 판·intercept arm·A2 단일 공격자·Pk=1).

### 3.2 리뷰 3 반증 실험 사전등록 (2026-08-06, ★ 결과 보기 전)

**(A) 실 궤적 접촉 검증** — chord 는 근사다. 17 kill event 스텝에서 backend 의
실제 step 내부 상대 궤적 최소거리를 직접 계산한다.

- 재구성: `a_rel = (v_rel(t+1) − v_rel(t)) / dt` (구분 상수 가속 가정),
  `r(s) = r0 + v_rel(t)·s + ½·a_rel·s²`, `s ∈ [0, dt]` 를 밀집 표본으로 최소화.
- **모형 자기검사를 먼저 통과해야 한다**: `|r(dt) − r1| < 1e−6` (재구성이
  backend 적분과 일치하는가). 불일치면 결과를 쓰지 않고 적분 방식을 먼저 밝힌다.
- 판정: 각 kill 의 실 최소거리 `d_exact` 보고. `d_exact > r_contact` 인 event
  수 = **chord false positive 수**. 사전 기대 = 경계 여유 < 0.033 인 2건(ep19·
  ep47)만 위험. **3건 이상이면 "15/17 강건" 주장을 철회**하고 swept 귀속을
  재작성한다. 판정식은 결과 후 불변경.

**(A) 결과 (2026-08-06 — `results/contact_exact_audit.json`)**:

- 모형 자기검사 1차 **FAIL** 2회 -- 둘 다 사전등록 경로대로 원인을 먼저 밝혔다:
  ① 주차(stage 5)가 event 직후 소진 limiter 를 PARK 로 옮겨 post 상태가 오염
  (스냅샷을 resolver 호출 시점으로 이동해 해소) ② 잔여 오차 max 0.107 ≈
  ½·a_rel·dt² = **backend 적분기가 semi-implicit Euler** (`analytic.py:123-129`,
  `v_new = v + a·dt` → `p += v_new·dt`)라서 등가속 이차 재구성과 끝점이 원리적
  으로 불일치.
- **적분기 확정의 귀결**: backend 의 step 변위는 `v_new` 선형 -- **chord 가
  이 이산 map 의 정확한(끝점 오차 0) 선형 임베딩**이고, 이차 재구성은 "물리적
  평활화" 대안이다. 표본 간 거동은 미정의(오류 9)이므로 어느 쪽도 "참 궤적"
  이 아니며, 둘의 차이(실측 최대 ±0.076)가 보간 모호성의 크기다.
- 이차 평활화 기준 `d_exact > 0.75` = **ep19 단 1건** (chord 0.731 / quadratic
  0.758 -- 경계 ±0.01 애매). ep47 은 잔존(0.716). 사전등록 철회 조건(3건 이상)
  **미달** → 판정: **16/17 kill 이 두 보간 모두에서 접촉으로 강건**, ep19 는
  경계-모호로 재분류 (종전 "2/17 위험" 중 1건 해소·1건 유지).
- chord 오차 상한 0.033 논법은 **철회한다** -- 그 유도는 "정확한 이차 궤적의
  끝점" 가정에 의존하는데 적분기가 그 가정을 만족하지 않는다 (리뷰 3 §3 의
  조건 1 위반 확인). 대체 근거 = 위의 두-보간 직접 비교.

**(B) Pk sweep** — `Pk=1` 무력화 1.000 을 semantics check 에서 곡선의 한 점으로.

- boxed 17판 × `Pk ∈ {0, 0.25, 0.5, 0.75, 1.0}` × Bernoulli seed 3종
  (`seed_ns` 변경으로 독립 draw). F-arm 설정(실 계약 두 플래그 on).
- 기록: episode 무력화·침투 · **event 수준** (episode 당 contact event 수,
  event 당 kill 빈도) · limiter 소모 · veto.
- 판정 (성능 대역 없음): (i) event 당 kill 빈도가 Pk 의 이항 CI95 안 (구현
  sanity) (ii) episode 무력화·침투 vs Pk 곡선 보고 -- **재시도 기회**(첫 접촉
  실패 후 추가 contact event)가 곡선을 Pk 보다 위로 올리는지가 관심 축.
- contact-specific lethality 모형이 없다는 한계는 그대로다: 이 sweep 은
  "Pk 가 얼마든 계약이 일관되게 작동한다" 와 frontier 의 Pk 민감도를 줄 뿐,
  실제 관통 접촉의 Pk 값을 정하지 않는다 (리뷰 3 §4 기각 유지).
- 판정식은 결과 후 불변경.

**(B) 결과 (2026-08-06 — `results/pk_sweep_audit.json`, boxed 17판 F-arm)**:

| Pk | 무력화 | 침투 | event/판 | event kill 빈도 | 이항 CI95 |
|---:|---:|---:|---:|---:|---|
| 0.00 | 0.000 | 1.000 | 2.24 | 0.000 | 단락 PASS |
| 0.25 | 0.373 | 0.627 | 1.86 | 0.200 (19/95) | [.163, .337] PASS |
| 0.50 | 0.608 | 0.392 | 1.51 | 0.403 (31/77) | [.388, .612] PASS |
| 0.75 | 0.882 | 0.118 | 1.25 | 0.703 (45/64) | [.644, .856] PASS |
| 1.00 | 1.000 | 0.000 | 1.00 | 1.000 | 단락 PASS |

- (i) **PASS** 전 구간 -- event 수준 kill 빈도가 Pk 이항 CI95 안 (구현 sanity.
  Pk=0.5 는 하한 인접 0.403 vs 0.388). Pk=0 에서 무력화 0·소모 전량 = P7 의
  episode 판.
- (ii) **재시도 효과 확인** -- episode 무력화가 모든 중간 Pk 에서 단일 event
  Pk 를 상회 (+0.12~0.13). Pk 가 낮을수록 event/판 이 2.24 까지 증가 = 실패한
  limiter 소모 후에도 잔여 limiter 접촉 기회가 곡선을 올린다. boxed 상태의
  frontier 는 Pk 에 민감하되 Pk 그 자체보다 완만하게 저하한다 -- **평가된
  17판·intercept·A2 한정**, lethality 모형 부재 caveat 불변.

---

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
[x] R1 배선 + P78~P80 (2026-08-06. env_sys.py contact_resolver 기본 off,
      tests/test_contact_resolver.py 12건 + 기존 P6~P15 전부 green.
      P78 hold n=500: 변경 전/후 JSON **비트 동일** (NET_CAPTURE 0.182
      = docs/48 SS 재현 anchor 포함))
[x] V2 검증 (§3.1 -- 대역 밖, swept 축으로 전량 귀속, 방향 재현 인정)
[x] R2 배선 + P81~P82 (2026-08-06. miss_terminates 기본 True=현행,
      tests/test_net_miss_handoff.py 4건 + 전체 회귀 474 passed / 0 failed)
[x] V3 (F arm: (a)(c)·2차 충족, (b) boxed 표본 검정 불가 -- miss 미발생)
[x] V3b (§1 R2 세부: (i)(ii)(iv) 충족 -- 국면 전환 작동. (iii) 0/7 --
      scripted 폴백 무력화 미실증, 꼬리 추격 기하. oracle 3-way 로 이관)
[ ] R3·R4 (지표 분리·frontier 집계)
[ ] 3-way 비교 (§4) -- ★ 첫 질문 후보: miss 시점 상태에서 폴백 요격의
      도달 가능 상한 (V3b (iii) 의 미판정을 정면으로 묻는다)
```
