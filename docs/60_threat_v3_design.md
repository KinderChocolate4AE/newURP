# 60 — 위협 계약 v3 설계 r3 (비준 완료 · 배선 개시)

**2026-08-07 · r0 = 초안 (94b786e) · r1 = 조건부 비준 반영 (4d87f53) ·
r2 = 분포 위협 구조 (ea77aed) · r3 = 최종 3수정 반영 후 **배선 승인**
(§8 r3 비준표): ① angular-gap 을 instantaneous transverse heuristic 으로
범위 제한 ② r_block 재사용 = nominal modeling choice 명시 ③ P91 을
backend 회전성(P91a)과 actual-v3 bearing sanity(P91b)로 분리.**

> **v3 의 목적은 공격자를 "더 어렵게" 만드는 것이 아니라, limiter 배치가
> attacker 행동을 실제로 변화시킬 수 있는 causal channel 을 추가하여 원래
> shepherding 질문을 처음으로 검정 가능하게 만드는 것이다.**

> **r2 추가 원칙: 공격자 설정을 하나의 정답으로 고르지 않는다. 공격자
> 불확실성을 문제의 일부로 정의하고, 그 분포에 대해 방어 정책이 일반화하는지
> 를 평가한다.** headline 은 "attacker setting X 에서 MARL 0.63" 이 아니라
> "hold/scripted vs MARL, across threat distribution" 이어야 한다.

---

## 0. 근거 — 왜 위협 계약이 다음 병목인가 (r0/r1 유지, 요약)

| # | 현행 A2 결함 | 실측 근거 | v3 축 |
|---|---|---|---|
| 1 | 등속 순항 (`v_nominal` 복귀 P-drive 뿐; 능력 1.5× 는 선언만) | V4-800: 스케일 22배에도 hold 기저선 불변 | (i) 종축 속도 프로파일 |
| 2 | 횡 무반응 (limiter 인지 = 접촉 repel 1.125 m 뿐) | P84: 0.75 m 밖 인과효과 0 (42/42) → shepherding 검정 불가 | (ii) 횡 반응성 |
| 3 | +x 고정 스폰 (스폰 축 = ring 축 = 회랑 축 일치) | 구조상 자명 | (iii) 방위 랜덤화 + standby |

## 0.5 임의값 처리 규율 (r2 — 계약 전체를 관통)

선언값을 0개로 만드는 것이 목표가 아니다. 방어할 것은 "이 값이 정답" 이
아니라 **"결론이 특정 임의값 하나에 의존하지 않는다"** 이다:

```
물리 앵커 있음            -> 고정
앵커 없음 + 문제 정의      -> 선언 + sensitivity (sweep)
앵커 없음 + 행동 모델      -> distribution / randomization
학습 가능한 전략           -> policy 에 넘긴다
```

## 1. 위협의 5층 구조 (r2 — 계약 검증과 학습 계약의 분리)

한꺼번에 8~10축을 랜덤화하면 학습 실패 시 MARL 약함/환경 분산/channel 부재를
구분할 수 없다. 따라서:

| 층 | 내용 | 용도 |
|---|---|---|
| **THREAT-v3-NOMINAL** | 대표점 attacker (§2~4 의 nominal 값) | **P87~P91 causal channel 검증 전용. 학습 금지** |
| **THREAT-v3-TRAIN** | 사전등록된 parameter distribution (θ_att ~ P_threat, 에피소드마다 draw) | 방어 MARL 학습. **범위는 docs/61 로 결과 전 동결** (착수 조건 = P88~P91 green) |
| **THREAT-v3-IID** | 같은 분포, held-out seed/draw | 분포 내 일반화 |
| **THREAT-v3-OOD** | 구조가 다른 공격자 (CPA avoidance · 다른 sprint 타이밍 · 다른 reaction gain) | 구조 일반화 — "scripted 취약점 암기" 반증 |
| **A4** | optimizer / self-play attacker | **최종 red-team falsifier 층. 주 학습 환경 금지** (non-stationarity·cycle·원인 식별 불가를 학습에 들이지 않는다) |

- §2~4 의 값들은 "정답값" 이 아니라 **manipulation-check 용 nominal point** 다.
- TRAIN 분포의 축 (예시 — 값 아님): 속도 전략 {sprint_range, slowdown_range,
  slowdown_frac} · 반응성 {route_gain, sense_range} · 능력 {a_att, v} (기존
  THREAT_BRACKET) · 초기조건 {spawn r, azimuth, R_standby jitter}.
- **분포 평가 지표 (결과 전 선언)**: mean 하나로 끝내지 않는다 —
  `E[J]` (mean net capture / total defense) **+ 하위 10% 분위 `Q_0.1(J)`
  (worst-decile penetration) + CVaR (limiter loss)**. 평균 80% 여도 특정
  parameter corner 에서 침투 100% 면 실패다.

경로 결정: **B 유지 (비준됨).** v3 는 복구가 아니라 새 threat contract 이며
legacy A2 를 NESTING 으로 bit-exact 내포한다.

## 2. 축 (i) — 종축 속도 프로파일 (nominal)

능력은 기 선언 (`adversary_v_max = 1.5×att_speed` · `a_att_max` 클램프),
행동만 추가. 구현 지점 = `_general_action` 전진항의 `v_nominal → v_ref` 치환.

| 필드 | 기본 (off) | nominal | 비고 |
|---|---|---|---|
| `sprint_range` | 0.0 | 60 m | `d_asset ≤ 60` 에서 `v_ref = sprint_frac × v_max_capability` |
| `sprint_frac` | 1.0 | 1.0 | TRAIN 분포 축 |
| `slowdown_range` | 0.0 | (90, 60) m | 저속 구간 |
| `slowdown_frac` | 1.0 | 0.5 | TRAIN 분포 축 |

**기전 주장 보류 (r1 유지)**: `v_shot` 도달집합은 가속 유계라 스프린트
가능성이 이미 샘플 안에 있다. 허용 문장 = *"60–90 m 저속 구간 후 terminal
acceleration 을 수행하는 비정상 종축 속도 프로파일"*. "gate 기만 / 창을
거짓으로 넓힘" 금지. bait 효과 주장은 별도 paired micro-test 사전등록으로.

### 2.2 ★ 가속도 budget 구성 계약 (r4 — P89 재비준 명문화)

> **Acceleration-budget composition:** longitudinal speed tracking, jink,
> and reactive routing share a single 3-D acceleration budget bounded by
> `a_att_max`. Component interactions caused by final norm clipping are
> therefore part of the threat contract, not treated as an implementation
> defect. `route_gain = 0.5` is retained as the NOMINAL manipulation-check
> value; realized route authority is reported separately from requested
> authority.

- 공격자 능력이 단일 `|a| ≤ a_att_max` 라면 종축 sprint 와 횡축
  회피가 **같은 actuator authority 를 경쟁하는 것이 물리적으로 맞다.**
  lateral budget 보장/route 우선권은 오히려 새 임의 설계 — 도입하지 않는다.
- **축 (i)·(ii) 의 independence 주장은 하지 않는다** (P89 saturation 실측:
  sprint 구간 clip 36% 평균·route authority 0.53 — §5.1).
- route_gain 을 지금 수치를 보고 내리는 것(예: 0.5→0.3)은 "포화를 덜 보이게
  하는 값" 으로의 사후 튜닝이라 금지. P88 이 0.5 에서 channel 을 열었고
  낮출 물리 앵커도 없다.

## 3. 축 (ii) — 횡 반응성: angular-gap 재정식화 (r2 — route_probe 소멸)

### 3.1 왜 probe-circle 을 버리는가

- r1 의 `route_probe = 5.0 m (= ring_radius)` 는 **임의값을 임의값에 앵커한
  순환** — 기각.
- "관측된 limiter 횡 분산으로 스케일링" 대안도 기각: attacker 의 perception
  geometry 가 defender 행동의 함수가 되면, MARL 이 shepherding 대신
  **attacker routing rule 의 스케일을 조작하는 exploit** 을 학습할 수 있다.
  상수가 없다고 더 자연스러운 모델이 아니다.
- 해법 = **파라미터 자체를 없앤다**: 원 위 후보점 16개 평가(legacy
  parametrization)를 버리고, "최대 간극으로 회피" 의미는 유지한 채 **각도
  공간에서 직접 widest gap 을 찾는다.**

### 3.2 angular-gap 알고리즘 — **instantaneous transverse angular-gap heuristic** (r3 범위 제한)

★ **명칭·주장 제한 (r3)**: 이 항은 현재 횡단면의 순간 기하만 본다 — limiter
가 2 m 앞이든 25 m 앞이든 lateral offset 이 같으면 같은 각도를 막는다
(sense_range 안에서 종축 거리 정보가 소거됨). 따라서 이것은 "physical
widest escape gap" 이 **아니며** 그렇게 부르지 않는다. 종축 기하까지 보는
판은 candidate 방향별 geometric CPA (`d_CPA(u,i) = min_τ |(p_i−p_A) −
v_test(u)·τ|`) 로 threat tube 겹침 각을 계산하는 것이나, 그건 controller
가 커지므로 **최소 causal channel** 목적의 nominal 에서는 채택하지 않는다
(P88/P90 실패 시의 escalation 경로로만, §3.3).

```
1. 감지: 전방(진행축 내적 > 0) ∧ 거리 ≤ sense_range 인 limiter 검출
2. 투영: 진행축에 수직인 횡단면으로 각 limiter 사영 -> 2D offset o_i
3. bearing: β_i = atan2(o_i)
4. blockage: limiter i 가 가리는 각도 구간 = [β_i − α_i, β_i + α_i],
   α_i = asin(min(1, r_block / |o_i|)),  |o_i| ≤ r_block 이면 α_i = π/2
   r_block = repel 반경 = repel_margin × lam_range × kill_radius
   ★ (r3) 이 재사용은 물리적 동일성 주장이 아니라 **신규 자유도를 추가하지
   않기 위한 nominal modeling choice 다.** repel 반경(반발 발동 거리)과
   threat footprint(위험 판단 반경)가 같아야 할 물리적 이유는 없다 --
   sense 30 m 로 감지하면서 1.125 m disk 만 피하는 모델임을 인지하고 쓴다.
   TRAIN/OOD 에서 별도 threat-footprint 모델이 필요할 수 있다 (분포 축 후보)
5. free sector: S¹ 에서 blockage 합집합의 여집합 중 최대 호(arc) 선택
6. 출력: a = route_gain × a_lat_max × (호 중점 방향 단위벡터)
```

거동 정의 (튜닝 아님 — jink_terminal_r 전례와 동일 지위로 선언 후 고정):
- 감지된 limiter 0 → 기여 0 (bit-exactness 경로).
- 전 원주 봉쇄 (free arc 없음) → 기여 0 (회피 불가 — repel 만 남음).
- 최대 호 동률 → 현재 횡속도 방향과 각도상 가까운 호 → ★ **세계 +z 선호**
  → mid 각 (결정론). 동률 인정 폭 = 1e-9 rad 양자화.
  ★ (P91b 교정 재선언, 2026-08-07): 초판의 "e1 폴백" (실구현 = 리스트 순서)
  은 **공면(z=0) 퇴화에서 mirror 비공변** — 전원이 평면에 있으면 ±z free arc
  가 반올림(1e-16)까지 동률인데 폴백이 y-mirror 에서 반대쪽 z 를 골랐다
  (P91b 1차 FAIL, mirror_dev 2.42 m @ 239 steps, 첫 분기 t=223 route z-성분
  ±21.96 — 본 단락이 1차 기록; 교정 후 재실행 = 8.95e-16 PASS).
  세계 +z 는 y-mirror·z-회전 양쪽 불변이라 공변 tie-break 다. route 는 어떤
  기존 결과에도 기여한 적 없어(항상 off) 소급 오염 없음. 1e-9 양자화는
  반올림 유사동률의 정확동률 승격용 수치 항 (물리 아님).
- 종말 게이트: `d_target ≤ jink_terminal_r` 에서 off (기존 규약 상속).
- 난수·시간 무관 (연속 계산, 16-방위 스캔 폐지) → 결정론.
- ★ (r4) **+z 선호의 결정론적 위쪽 편향 주의**: 공면 동률에서 공격자는
  항상 위로 간다 — MARL 이 "평면에서 막으면 무조건 위" 를 exploit 로 암기할
  수 있다. 대응: **TRAIN 에서 tie-break 를 랜덤화하지 않는다** (비정상성
  금지). 대신 **OOD 에 −z tie-break variant (또는 ±ε vertical bias) 를
  예약** (docs/61) — OOD 에서도 성능이 유지되면 3D geometry 를 배운 것이지
  +z 규칙 암기가 아니라는 증거가 된다.

**남는 파라미터 = `sense_range` · `route_gain` 둘뿐** (r_block 은 기존 선언량
합성). 해석: *"attacker 는 감지된 limiter 가 만드는 angular blockage 를 보고
가장 열린 방향으로 회피한다"* — limiter 가 움직이면 gap 이 바뀌고 attacker
방향이 바뀐다. 이것이 원하는 causal channel 이다.

| 필드 | 기본 (off) | nominal | 비고 |
|---|---|---|---|
| `route_gain` | 0.0 | 0.5 | P89 saturation audit 조건부 (r1 유지) |
| `sense_range` | ∞ | 30 m | "감지 > 교전(1.125 m)" 의무 표현. TRAIN 분포 축 |
| ~~`route_probe`~~ | — | **소멸** | probe-circle parametrization 제거 |

구 `_route_accel` 은 어떤 결과에도 기여한 적 없다 (route_gain 항상 0) —
교체는 소급 변경이 아니다. P1b(A1 충실성) 하네스는 유지되고, angular-gap
항은 신규 단위 테스트를 받는다.

### 3.3 P88 — 방향성 manipulation gate (r1 유지, nominal 에서 실행)

```
P88-a  mirror: 좌우 대칭 limiter 배치 반전 -> attacker 횡 반응 부호 반전
P88-b  direction: 반응 방향이 angular-gap 최대 호 방향과 일치
P88-c  sense_range 안·교전 밖 배치 변화 -> 궤적 변화 (42/42 bit-동일의 역전)
P88-d  sense_range 밖 -> bit 동일
P88-e  positive control (교전 안) 발산 (검정력)
```

escalation: angular-gap 이 P88/P90 을 못 넘으면 CPA 예측 기반 회피를 **새
사전등록으로** (이 문서 안에서 확장 금지).

## 4. 축 (iii) — 방위 랜덤화 + bearing-독립 symmetric standby (r2 전면 교체)

### 4.1 ring-회전 정렬 폐기

r1 의 "ring 을 스폰 방위에 회전 정렬" 은 **문제를 너무 많이 풀어준
초기조건**이다 — 상대기하가 사실상 항상 같아져, 검증되는 것은 "+x 전용
코드가 world frame 회전에도 도는가" (rotation generalization) 뿐이고 "방위
불확실 위협에 방어측이 대응 가능한가" 가 아니다. 2단계로 분리한다:

```
1. standby geometry        공격자를 보기 전 배치 -- attacker bearing 과 독립
2. threat-relative formation  bearing 관측 후 만들 상태 -- ★ policy 의 몫
```

ring-회전 정렬은 2 를 환경이 대신 해주는 것이었다. 폐기.

### 4.2 standby 계약

- **배치**: limiter 4기를 자산 중심 4방위 대칭으로 —
  `p_i(0) = R_standby × [cos(φ₀ + iπ/2), sin(φ₀ + iπ/2), 0]`, i = 0..3.
- **`φ₀ ~ U[0, π/2)` 에피소드마다 랜덤** (SHA-256 규약) — 특정 world axis
  편향 제거. 4기 정사각 대칭이라 φ₀ ≡ φ₀+π/2 이므로 독립 기하는 [0, π/2)
  뿐 — full 2π 로 뽑지 않는다 (r3).
- **`R_standby` nominal = 12 m** (선언값: Hyunjun 예시대역 8~16 의 중앙.
  구속조건 = r_nk 6 밖 + 4기 비중첩. 원점 몰아넣기는 기각 — NK fallback 기하
  왜곡·초기 겹침·전원 외곽 출동의 불필요한 불리). TRAIN 분포에서 jitter
  (예: U[8,16]) — nominal 검증은 한 점으로.
- **탐지 가정 (명시)**: *"episode 시작 시 threat bearing/state 는 이미 탐지된
  것으로 가정한다. 단 limiter 초기배치는 bearing-independent standby 다."*
  → detection uncertainty 는 제외, bearing 대응/redeployment 는 포함.
  unknown bearing → detection → reconfiguration 은 v3.1 (별도 사전등록).
- **스폰**: `r_range (250, 350)` · `azimuth ±π/4` (r1 비준값 유지).
- ring_center/ring_radius 는 v3 arm 에서 **standby 초기조건으로 강등** —
  논문에서 중요한 것은 5 m/12 m 가 아니라 "다양한 bearing 에서 동일 standby
  로부터 유효한 방어 기하를 만들어 내는가". initialization sensitivity 는
  후속 (nominal 확인 후 TRAIN 에 jitter).
- 파생 검증 항목 (docs/59 재래): finisher (2,0,0) 고정 + slew 2.0 rad/s 의
  ±45° 방위 추종 가능성. hold/COMA 기저선은 standby 위치로 재정의 —
  **COMA cf = layout.limiter_p0 의존 감사는 P51 재검토와 묶어 MARL 재개 전
  필수** (ring 의존은 초기조건이 아니라 학습 신호 기준점이므로).

### 4.3 P91a · P91b (r3 분리 — finisher 고정과의 충돌 해소)

r2 의 P91 은 "무엇을 회전하는가" 가 미명시였다. finisher 는 (2,0,0) 위치
고정인데 접근 방위가 ±45° 랜덤이므로, finisher 를 회전에서 빼면 viability
가 θ 에 따라 달라지는 것이 **버그가 아니라 실제 v3 문제의 성질**이다. 분리:

```
P91a  backend rotational covariance: target-relative 전체 장면(공격자·
      limiter·finisher·velocity)을 함께 θ 회전 -> 역회전시 dynamics·
      evaluator 동일. 순수 backend isotropy 검사 -- 실패 = hidden +x bug
      -> 축 (iii) 동결
P91b  actual-v3 bearing sanity: finisher 는 계약대로 (2,0,0) 고정 ·
      standby 는 bearing-독립 · spawn bearing 만 ±θ mirror -> 사전 정의한
      대칭(공격자 궤적·scripted 대응의 mirror 관계)만 검사. viability 의
      θ 의존은 실패가 아니라 기록 대상 (finisher 방위 추종의 실측 자료)
```

## 4.5 nested arm 규율 (r1 유지 + r2 주석)

```
V3-C    = v2 + (ii) angular-gap coupling      <- causal channel 단독
V3-CS   = V3-C + (i) speed profile
V3-FULL = V3-CS + (iii) azimuth + standby     <- 최종 학습 무대 (단 학습은
                                                 TRAIN 분포로, nominal 아님)
```

- 동일 seed nesting. V6 는 descriptive baseline 로만.
- ★ r2 주석: V3-CS → V3-FULL 은 위협(방위)과 방어 초기기하(standby)가 **함께**
  바뀌는 문제 재정의 단계다 — 순수 위협-축 delta 가 아니므로 arm 간 차분을
  위협 효과로 귀속하지 않는다 (descriptive).
- "limiter 부동 비용" 해석 금지 유지 — 동일 V3-FULL 위 static vs active
  limiter 비교로만.

## 5. 검증 게이트 (결과 보기 전 선언 — 전부 NOMINAL 에서)

```
P87   NESTING: 신규 필드 전부 기본값 -> A2(jink 0.6)·SCALE_V2_SPAWN 과 bit
      동일 (attacker action + spawn draw + standby off 경로)
P88   방향성 manipulation gate (§3.3 a~e 전부)
P89   능력 준수 + saturation audit (r1 유지: raw pre-clip·clip 비율·
      requested vs realized route 성분·sprint 구간 route authority 기록.
      광범위 포화 -> route_gain 재비준)
P90   침투 능력 보존: 사전등록 seed n=100 · defender 전원 제거 ->
      100/100 PENETRATED · TRUNCATED 0 · self-failure 0.
      TRUNCATED 발생 -> 해석 금지, V6 전 horizon 재사전등록
      (episode_len 1000 은 이 gate 조건부 임시값)
P91a  backend rotational covariance (§4.3 -- finisher 포함 전체 회전)
P91b  actual-v3 bearing sanity (§4.3 -- finisher 고정, mirror 대칭만)
V6    nested arm baseline (V3-C/CS/FULL · hold=standby/clean · 동일 seed ·
      각 n=100) -- 수락대역 없음, descriptive
V7    뷰어 재생성 -> Hyunjun 육안 (standby 4방위·bearing 대응·저속 구간·
      스프린트 전환·angular-gap 회피가 육안 식별되는지)
```

### 5.1 ★ 게이트 결과 (2026-08-07 — `results/threat_v3_*.json`, 스크립트 커밋 abc56db 는 결과 전)

```
P87   PASS  배선 전 커밋 golden (attacker 300점 + spawn 10 draw) bit 동일
P88   PASS  7/7 · a~e 전부 (mirror 부호반전 · angular-gap 방향 일치 ·
      sense 안 발산 · sense 밖 bit-동일 · positive control 즉시 발산/종료)
      -> "defender geometry -> attacker action" 방향성 causal channel 개통.
      shepherding 검정 가능성의 필요조건 확보 (충분조건 아님 -- 유도 성공 별도)
P89   capability PASS (전 스텝 |v|/v_max <= 1.0000 · |a| 클립 준수).
      ★ saturation 보고 (n=20): 전체 clip 7.5% 평균 (max 23.6%) · sprint
      구간 clip 36.1% 평균 (max 76%) · route authority (realized/requested)
      0.53. "광범위" 임계는 사전등록되지 않았음 -- route_gain 0.5 확정/인하는
      Hyunjun 재비준 사항 (r1 조건). 관찰: sprint 구간에서 종축 P-drive 가
      lateral budget 을 잠식 -- 축 (i)·(ii) 는 sprint 구간에서 부분 경합
P90   PASS  100/100 PENETRATED · TRUNCATED 0 · self-failure 0 (최장 847
      스텝 < 1000) -> episode_len 1000 확정 (#10 조건 해소)
P91a  PASS  4/4 (ep 0,1 × θ 0.7,2.4) dyn_dev ~1e-13 · v_shot_dev 0.000
      -> hidden +x assumption 없음 (evaluator 포함)
P91b  1차 FAIL (mirror_dev 2.42 m) -> 원인 = 공면 퇴화 tie-break 비공변
      (§3.2 교정 재선언: 세계 +z 선호 + 1e-9 양자화) -> 재실행 PASS
      (mirror_dev 8.95e-16). 게이트가 설계 목적대로 대칭 결함을 사전 검출
```

★ 이후 순서 (r4 개정 — V6/V7 을 docs/61 앞으로): P87~P91 은 계약 correctness
검증이지 nominal behavioral sanity 가 아니다. NOMINAL 이 실제로 어떤
상태분포를 만드는지 한 번도 보지 않고 TRAIN 범위를 동결할 수 없다:

```
1. P89 재비준 [완료 r4] -- route_gain 0.5 확정 + §2.2 budget 계약
2. V6 nominal nested baseline (학습 없음 · C/CS/FULL 각 n=100 · hold/clean)
   관측 항목 (사전 선언 -- 성능 판정 아님·수락대역 없음):
     (a) route 활성 빈도 (스텝 비율)   (b) vertical escape 빈도·크기 (|z|)
     (c) saturation 분포              (d) sprint/slowdown 실제 발생 여부
     (e) FULL 초기 재배치의 물리 가능성 (t_redeploy vs t_arrival 기하비)
     (f) trivial self-defeat 부재 (라벨 분포)
3. V7 뷰어 -- 특히 "평면 봉쇄 -> over-the-top escape" 실존 확인 (Hyunjun)
4. docs/61 THREAT_V3_TRAIN_DISTRIBUTION 사전등록 -- ★ V6 결과로 범위를
   튜닝하지 않는다. V6 는 계약이 의도대로 작동하는지 sanity 전용이고,
   TRAIN 범위는 물리/설계 불확실성 근거로만 정한다 (데이터 의존 금지).
   축별 범위 + IID held-out + OOD (구조 변형 + ★ −z tie-break variant)
   + 평가지표 E[J]/Q_0.1/CVaR 판정식, 학습 결과 전 동결
5. 그 뒤에만 MARL
```

★ (r3 유지) docs/61 규율: parameter-wise independent uniform box 하나로
끝내지 않는다 — 축별 stratification (예: weak/medium/strong reactivity ×
speed profile) 으로 coverage 를 보장한 뒤 내부 jitter.

### 5.2 ★ V6 결과 (2026-08-07 — 서버 12샤드, `results/v6_*.json`, 커밋 33165ed)

**descriptive 전용 (수락대역 없음 · arm 간 차분 귀속 금지 · TRAIN 범위 튜닝
금지).** 라벨: V3-C 85 침투/15 포획 · V3-CS 87/13 · V3-FULL 87/13
(비교 맥락: v2 V4-800 무반응 공격자 = 85/15).

| 항목 | 관측 | sanity 판독 |
|---|---|---|
| (a) route 활성 | 3 arm 전부 100/100 판, 스텝 11~17% | 채널이 매 판 살아있음 |
| (b) vertical escape | z-지배 비율 C 0.55 / CS 0.51 / **FULL 0.81** · z_max 평균 4.0~9.1 m (최대 22.6) | 실재 — 수평 standby 는 평면 봉쇄 시 위 탈출이 지배. V7 육안 확인 대상 |
| (c) saturation | FULL sprint 구간 clip 평균 0.39 (일부 판 1.00) | P89 정합 — §2.2 budget 계약 범위 |
| (d) 속도 프로파일 | sprint/slowdown 개입: C 0/100 · CS/FULL 100/100 (판당 57~67 스텝) | nesting 설계대로 동작 |
| (e) FULL 재배치 기하 | redeploy_ratio 평균 0.115 (최대 0.143) | 방위 대응 재배치 물리적으로 여유 |
| (f) self-defeat | max\|v\|/v_max=1.0000 · fire 18~24/100 · min_d 평균 1.0~1.4 m | 없음 — 능력 준수·위협 유지 |

→ sanity 전 항목 이상 없음. 다음 = V7 뷰어 (Hyunjun 육안 — 특히 (b) 의
"평면 봉쇄 → over-the-top escape" 실존 확인) → docs/61.

### 5.3 ★ V7 육안 판독 (2026-08-07 — Hyunjun, artifact 0a31f6b9)

```
①  ★ (b) 해석 정정: ep1 의 vertical move 는 "route 가 위로 탈출" 이 아니라
   net 회피 후 관성으로 뒤로 밀리며 위로 뜬 것. 실제 회피는 jink (옆 jitter)
   가 우연히 맞은 것으로 판독. -> §5.2 (b) 의 "z-지배 0.81" 은 route 가
   z 를 **요청**한다는 수치이지, 침투 성공의 실현 기전이 route 의 z 선택
   이라는 증거가 아니다. route 의 인과 기여 귀속은 paired ablation
   (동일 seed·route on/off) 로만 가능 -- 미실시, 필요 시 별도 사전등록.
   (뷰어가 수치 해석을 이김 -- viz-first 재확인)
②  standby 4방위·방위 스폰 = 의도대로 (승인)
③  스프린트 전환 궤적 식별됨 (승인)
④  angular-gap 기동: nominal 에서 육안상 미세 -- hold limiter 4기의
   blockage 반각이 asin(0.75/d) 로 수 도(°) 수준이라 정면과 몇 도 차이의
   편향임. 설계와 일치 (§3.2 instantaneous heuristic 의 예상 거동)
뷰어 개선 반영 (같은 artifact 재게시): fit-to-screen (뷰포트 상한·중앙
정렬) + 궤적 속도 색상 (파랑 느림 -> 주황 빠름, 범례)
```

주의 재확인 (r4 §3.2 와 연결): 현 nominal 의 "미세 요동" 인상은 설계된
모습이다 — jink 변위 진폭 ≈ 0.6·a_att/(2πf)² ≈ 0.07~0.53 m (브래킷별),
homing 4.0 이 횡속도를 즉시 감쇠, 종말 3 m 게이트에서 회피 off. 반응성의
"크기" 자체가 TRAIN 분포 축이다 — nominal 하나의 인상으로 위협 강도를
논하지 않는다.

판정식·선언값은 결과 후 불변경. 조정은 새 사전등록으로만.

## 6. 격리·배선 규율

- 브랜치 `feat/scale-up-v2`. 배선 = AttackerSpec/SpawnSpec 필드 추가 +
  `_route_accel` angular-gap 교체 + standby layout + `scale_v2.py` 선언 dict.
- legacy / v2 / v3 수치 같은 표 금지 (P78 동형).
- v3 확정 전 금지 유지: limiter 학습 · oracle 확장 · r_nk 튜닝.

## 7. 자유도 동결표 r2 (NOMINAL — 결과 전 전부 노출·동결)

| # | 자유도 | nominal | 상태 |
|---|---|---|---|
| 1 | `sprint_range` | 60 m | 비준 (TRAIN 분포 축) |
| 2 | `sprint_frac` | 1.0 | 비준 (TRAIN 분포 축) |
| 3 | `slowdown_range` | (90, 60) m | 비준 (기전 주장 보류) |
| 4 | `slowdown_frac` | 0.5 | 비준 (TRAIN 분포 축) |
| 5 | `route_gain` | 0.5 | **비준 확정 (r4)** — §2.2 budget 계약으로 명문화, 인하 금지 |
| 6 | `sense_range` | 30 m | 비준 (TRAIN 분포 축) |
| 7 | ~~`route_probe`~~ | 소멸 | **비준 (r3 조건 이행)** — instantaneous heuristic 명칭 제한 + r_block 의미 제한 (§3.2) |
| 8 | `r_range` | (250, 350) m | 비준 |
| 9 | `azimuth` | ±π/4 | 비준 |
| 10 | `episode_len` | 1000 | 임시 (P90 조건부) |
| 11 | `R_standby` | 12 m | **비준** (nominal point 한정 — 최적/현실값 주장 아님) |
| 12 | `φ₀` | ~ U[0, π/2) 에피소드 랜덤 (SHA-256) | **비준** (r3: 대칭 몫으로 축소) |
| 13 | standby 4방위 대칭 + 탐지 가정 문구 | §4.2 | **비준** |

**배선 승인 (r3).** 잔여 조건부 = #5 (P89 audit) · #10 (P90).

## 8. 비준 로그

**r1 (2026-08-07 1차)**: 경로 B 승인 · P88 방향성 강화 · sprint/slowdown
승인 (기전 보류) · sense_range 30 승인 · r_range 승인 · episode_len P90
조건부 · route_gain P89 조건부 · route_probe 비준 불가 · "limiter 부동 비용"
철회 · nested arm/P91/자유도 동결 지시.

**r2 (2026-08-07 2차)**:
| 지시 | 반영 |
|---|---|
| 위협 = 분포 (설정값 고르기 금지). NOMINAL/TRAIN/IID/OOD/A4 5층 | §1 |
| nominal ≠ 정답값 (manipulation-check 대표점) | §1·§7 |
| 지금 전부 랜덤화 금지 — 계약 검증(nominal)과 학습 계약(분포) 분리 | §1·§5 |
| TRAIN 분포는 별도 사전등록 (범위 결과 전 동결) | §5 (docs/61) |
| 평가 = mean + Q_0.1 + CVaR | §1 |
| self-play(A4) = red-team falsifier 층, 주 학습 환경 금지 | §1 |
| route_probe 5.0 도 spread-기반도 기각 → angular-gap 무상수 재정식화 설계 | §3 |
| spread-기반 기각 사유 = perception geometry 가 defender 함수화 → exploit | §3.1 |
| ring-회전 정렬 폐기 → bearing-독립 symmetric standby (원점 몰기 기각) | §4 |
| 탐지 가정 명시 (bearing 은 관측됨, standby 는 bearing-독립) | §4.2 |
| ring_radius = standby 초기조건으로 강등 · COMA cf 의존 감사 = P51 과 묶음 | §4.2 |
| P91b bearing-response mirror 추가 | §4.3 |
| 임의값 처리 4단계 규율 | §0.5 |

**r3 (2026-08-07 3차 — 배선 승인)**:
| 항목 | 판정 | 반영 |
|---|---|---|
| 분포 구조 (5층) · nominal/train 분리 · bearing-독립 standby | 방향 비준 | — |
| #7 angular-gap | 조건부 승인 → 이행 | instantaneous transverse heuristic 명칭 제한 + 종축 소거 caveat + CPA escalation 명시 (§3.2) |
| r_block = repel 재사용 | 의미 제한 | 물리 동일성 아님 · nominal modeling choice · TRAIN/OOD 별도 footprint 후보 (§3.2) |
| P91 | 수정 후 승인 | P91a (finisher 포함 전체 회전 = backend isotropy) / P91b (finisher 고정 · mirror 대칭만) 분리 (§4.3) |
| #11 R_standby 12 | 승인 (nominal point 한정) | §7 |
| #12 φ₀ | 승인 · U[0,π/2) 권장 채택 | §4.2 |
| #13 standby 계약 | 승인 | — |
| docs/61 예약 | independent uniform box 단독 금지 · stratification | §5 |

**r4 (2026-08-07 4차 — P89 재비준 + 순서 개정)**:
| 항목 | 판정 | 반영 |
|---|---|---|
| P89 | route_gain 0.5 **확정** — 단일 3D 가속도 budget 공유를 의도된 계약으로 명문화 (수치 보고 후 인하 = 사후 튜닝 금지) | §2.2 |
| 축 (i)·(ii) independence | **기각** — saturation 은 계약의 일부, 결함 아님 | §2.2 |
| +z tie-break | NOMINAL 유지 · TRAIN 랜덤화 금지 · OOD 에 −z/±ε variant 예약 | §3.2·§5 |
| standby | 유지 (구/사면체 금지) — vertical escape 는 MARL 의 3D 협력 시험대 | §4.2 |
| V3-CS→FULL 차분 | descriptive 재강조 (초기거리·orientation·수직 coverage·역할 난도 동시 변화) | §4.5 |
| 순서 | V6/V7 을 docs/61 앞으로 · TRAIN 범위는 V6 결과 비의존 | §5 |
