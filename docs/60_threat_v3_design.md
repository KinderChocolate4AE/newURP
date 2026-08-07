# 60 — 위협 계약 v3 설계 r1 (조건부 비준 반영 · 배선 전 · 결과 없음)

**2026-08-07 · 결과를 보기 전에 쓴다. r0 = 초안 (커밋 94b786e), r1 = Hyunjun
조건부 비준 (2026-08-07, §8 판정표) 반영. 비준 전 금지 유지: limiter 학습 ·
oracle 확장 · r_nk 튜닝. 잔여 확정 항목은 §7.**

> **v3 의 목적은 공격자를 "더 어렵게" 만드는 것이 아니라, limiter 배치가
> attacker 행동을 실제로 변화시킬 수 있는 causal channel 을 추가하여 원래
> shepherding 질문을 처음으로 검정 가능하게 만드는 것이다.** (Hyunjun, 비준문)

---

## 0. 근거 — 왜 위협 계약이 다음 병목인가

스케일 v2 (docs/59) 가 무대를 만들었지만, 그 무대 위의 위협이 세 가지
결함으로 무대를 쓰지 못하게 한다. 결함 ↔ 실측 근거 ↔ 축이 1:1 이다:

| # | 현행 A2 의 결함 | 실측 근거 | v3 축 |
|---|---|---|---|
| 1 | **등속 순항** — `v_nominal` 복귀 P-drive 뿐. 능력 `adversary_v_max = 1.5×att_speed` 는 선언돼 있으나(`m4_config` CAPABILITY_RATIOS) 행동이 안 씀 | V4-800: 스케일 22배에도 hold 기저선 불변 (capture 15/침투 85) — 대응시간을 위협도 안 쓰고 방어도 안 씀 | (i) 종축 속도 프로파일 |
| 2 | **횡 무반응** — limiter 인지 채널이 접촉 반발(repel, `1.5×kill_radius = 1.125 m`)뿐 | P84: 0.75 m 밖 limiter 배치는 공격자 궤적에 인과효과 0 (42/42 bit 동일) → **현 계약에서 shepherding 검정 불가** | (ii) 횡 반응성 |
| 3 | **+x 고정 스폰** — x∈[290,310]·r_lat 5 원판. 스폰 축 = ring 축 = 회랑 축 전부 일치 | 구조상 자명. hidden +x assumption/overfitting 미검증 | (iii) world-frame 회전 랜덤화 |

부수 근거 (V5, docs/59 §3.2): ep94 무발사의 원인이 v_soft 천장 0.728 =
위협이 아니라 limiter 부동이었다 — 위협 v3 는 limiter 학습/스크립트 재개의
전제 조건이지 대체물이 아니다.

## 1. 경로 결정 — B 비준 (2026-08-07)

| 경로 | 내용 | 판정 |
|---|---|---|
| A | 주장 축소: 공격자 무반응 유지, interception/coverage 재스코프 | 기각 (B 실패 시 fallback 문장으로만 보존) |
| B | 반응형 attacker 계약: 축 (ii) 로 조작 가능 채널 개통 후 shepherding 검정 | **비준** |

**v3 는 기존 계약의 복구가 아니라 새 threat contract 다** — legacy A2 (docs/27
사다리) 는 보존되고, v3 는 그 위의 새 선언층이다 (NESTING 으로 A2 를 bit-exact
내포). 규율 유지: P88 통과 전엔 "shepherding" 을 핵심 주장으로 쓰지 않는다.

## 2. 축 (i) — 종축 속도 프로파일 (터미널 스프린트 · slowdown)

**원칙: 능력은 이미 선언됐고, 행동만 추가한다.** 새 물리 한계 없음 —
`adversary_v_max = 1.5×att_speed` (기 선언) · `a_att_max` 클램프 (기존) 안에서
참조 속도 `v_ref` 만 상태 의존으로 바뀐다. 구현 지점은 `_general_action` 의
전진항 하나: `a_fwd = fwd_gain × (v_ref − v_fwd) × fwd` 에서 `v_nominal → v_ref`.

`AttackerSpec` 신규 필드 (전부 기본 off = A2 bit-exact, NESTING 규약):

| 필드 | 기본 | 선언값 | 판정 | 의미 |
|---|---|---|---|---|
| `sprint_range` | 0.0 (off) | 60 m | 승인 | `d_asset ≤ 60` 에서 `v_ref = sprint_frac × v_max_capability` |
| `sprint_frac` | 1.0 | 1.0 | 승인 (sweep 축) | 스프린트 참조속도의 능력 대비 비율 |
| `slowdown_range` | 0.0 (off) | (90, 60) m | 승인 (기전 주장 보류) | `d_asset ∈ (60, 90]` 에서 `v_ref = slowdown_frac × v_nominal` |
| `slowdown_frac` | 1.0 | 0.5 | 승인 | 저속 구간 참조속도 비율 |

60 m 근거: v2 발사 유효권(cone 상류 x≲32) + ring 50 을 포함하는 거리에서
전환이 일어나야 발사 gate 와 상호작용한다. 외부 앵커 없음 — 선언값 + sweep 축.
거리 트리거만 사용 (시간·난수 무관) → 결정론에 위상 유도 불필요.

### 2.1 ★ 기전 주장 보류 — "feint/bait" 서사 금지 (r1)

r0 의 "감속이 포획 창을 넓어 보이게 만들고 스프린트가 예측을 깨뜨린다" 는
**철회한다.** 코드 사실: `v_shot` 은 `reachable_accels` 로 **현재 속도 기준
가속 유계(a_att_max) τ-도달가능집합**을 평가한다 (`viability.py`) — 감속은
도달집합의 중심(v·τ 항)을 옮기지만, **이후 최대가속 스프린트 가능성은 이미
가속 샘플 안에 들어 있다.** 따라서 "gate 기만" 은 성립하지 않을 수 있고,
필드명도 `feint` 가 아니라 `slowdown` 으로 한다.

- 허용 문장: *"60–90 m 에서 의도적 저속 구간 후 terminal acceleration 을
  수행하는 비정상 종축 속도 프로파일을 추가한다."*
- 금지 문장: "fire guard 를 기만한다" · "포획 창을 거짓으로 넓힌다".
- bait 효과를 주장하려면 **별도 paired micro-test** (동일 state · slowdown
  on/off · fire timing · v_soft/v_worst · net miss 비교) 를 새 사전등록으로.

## 3. 축 (ii) — 횡 반응성 (limiter 회피)

**원칙: 기존 사다리 항을 재사용한다.** `_route_accel` (편대 최대간극 라우팅)
이 이미 구현·테스트돼 있고 (`route_gain=0` 으로 잠자는 중) P1b 충실성 하네스도
있다. 신규 컨트롤러를 쓰지 않는다. 부족분:

| 필드 | 기본 | 선언값 | 판정 | 의미 |
|---|---|---|---|---|
| `route_gain` | 0.0 (off) | 0.5 | **조건부** — P89 saturation audit 통과 후 확정 | 최대간극 방향 편향 크기 (×a_lat_max) |
| `sense_range` | ∞ | 30 m | 승인 | limiter 감지 반경. 선언값 (외부 앵커 없음) + sweep 축. 교전 반경(repel 1.125 m) 대비 ~27배로 "감지 > 교전" 의무 충족. 기존 무제한(전지 관측)을 자르는 필드 |
| `route_probe` | 2.0 | **5.0 m (절대값, 재선언)** | §3.1 — 재비준 대상 | 간극 평가 횡 변위 반경 |

### 3.1 ★ route_probe 재선언 (r1 — 코드 확인 완료)

코드 의미 (`attacker_ladder.py _route_accel`): 후보 방위 16개를 공격자 횡단면
위 **반경 `route_probe × kill_radius` 의 원**에서 평가하고, 각 후보점—limiter
사영 간 최소거리를 점수로 최대간극 방향을 고른다. 즉 route_probe 는 **"어느
횡 변위 스케일에서 간극을 재는가"** 다.

현행 2.0 × 0.75 = **1.5 m 는 편대 횡 스케일(ring_radius 5 m)에 한참 못 미치는
legacy 스케일 산물**이다 — 1.5 m 원 위의 16점은 전부 편대 안쪽에 몰려 간극
판별력이 없다. 재선언 제안:

- **파라미터화 변경**: ×kill_radius (살상반경과 무관한 양이었다) → **절대
  미터**. route 는 한 번도 켜진 적 없어 어떤 결과도 이 필드에 의존하지 않음
  → 재파라미터화가 소급 변경이 아니다.
- **값 5.0 m = ring_radius** (편대 횡 스케일. 간극을 재는 자연 스케일은
  회피 대상 편대의 횡 크기다). 외부 앵커 없음 — 선언값 + sweep 축.

### 3.2 P88 — 방향성 manipulation gate (r1 강화)

r0 의 "궤적 발산" 만으로는 부족하다 — 버그로 항상 왼쪽으로 틀어도 통과한다.
**"반응함" 이 아니라 "유도 가능한 방향으로 반응함"** 을 확인한다:

```
P88-a  mirror: 좌우 대칭 limiter 배치 반전 -> attacker 횡 반응의 부호 반전
P88-b  direction: 반응 방향이 _route_accel 의 최대간극 방향과 일치
P88-c  sense_range 안·교전 밖 배치 변화 -> 궤적 변화 (기존 42/42 bit-동일의 역전)
P88-d  sense_range 밖 배치 변화 -> bit 동일 유지
P88-e  positive control (교전 안) 발산 유지 (검정력)
```

5개 전부 성립해야 (ii) 채널 개통 = **defender geometry → attacker action 의
방향성 있는 causal channel.** 이것이 shepherding 검정 가능성의 진짜 gate 이며,
여전히 필요조건이지 충분조건(유도 성공)이 아니다.

escalation (선언만): route 재사용이 P88/P90 을 못 넘으면 CPA 예측 기반 회피
항을 **새 사전등록으로** 설계한다. 이 문서 안에서 확장하지 않는다.

## 4. 축 (iii) — world-frame 회전 랜덤화 (r1 재명명)

### 4.1 의미의 정직화

r0 의 "방위 불확실성" 표현은 부정확하다 — azimuth ±45° 를 주면서 ring 을 그
방위에 회전 정렬하면 방어자가 방위 불확실성을 푸는 것이 아니라 **동일한 상대
교전 기하를 world-frame 회전에 걸쳐 평가**하는 것이다. 정확한 명명:

> **v3.0 = rotational randomization**: *탐지가 완료되어 접근 방위가 알려진
> 조건에서, 동일한 상대 교전 기하를 ±45° world-frame orientation 에 걸쳐
> 평가한다.* 가치 = x축에 숨은 버그·overfitting 제거 (rotational
> generalization). 방위 **불확실성** 을 푸는 것이 아님을 명시.

> **v3.1 (별도 사전등록)**: unknown bearing → detect → reconfigure —
> 재배치를 문제에 포함 (mode scheduling 의 자연 무대).

### 4.2 SpawnSpec 확장 (opt-in — enabled 규율 동일)

| 필드 | 기본 | 선언값 | 판정 | 의미 |
|---|---|---|---|---|
| `r_range` | None (off) | (250, 350) m | 승인 | 표적 중심 스폰 거리 브래킷 (균일) |
| `azimuth` | 0.0 (off) | ±π/4 | 승인 (v3.0 명명 조건) | 접근 방위각 섹터 (수평). ring 은 스폰 방위에 회전 정렬 |

지평선 산술 (오류 18 규율 — 레지스트리 값으로 명시):
```
최악 도달시간 = r_max / att_speed 하한 = 350 / 8 = 43.75 s
slowdown 지연 = 30 m 구간 0.5×v 통과 -> 최대 +3.75 s
전개·lock 여유 = +1.25 s (docs/59 재래)
합계 48.75 s -> episode_len = 1000 (50 s)   ★ P90 통과 조건부 임시값 (§5)
```

### 4.3 P91 — rotation-equivariance 사전 검사 (r1 추가, 배선 전)

θ 만큼 spawn·formation·velocity 를 함께 회전 → 결과를 역회전하면 dynamics ·
viability 판정이 θ=0 과 동일해야 한다 (수치 허용오차 내). **깨지면 스폰 실험
전에 hidden +x assumption 부터 잡는다** — 싸고, 축 (iii) 전체의 전제다.

## 4.5 ★ nested arm 규율 (r1 추가 — 최중요 수정)

세 축을 한 번에 켜면 V6 하락의 원인 귀속이 불가능하다. **동일 seed nesting
으로 축별 attribution arm 을 보존한다**:

```
V3-C    = v2 + (ii) coupling only          <- causal channel 단독 효과
V3-CS   = V3-C + (i) speed profile
V3-FULL = V3-CS + (iii) rotation           <- 최종 학습 환경
```

- 최종 학습 환경은 V3-FULL 이어도 되지만 **축별 arm 은 반드시 남긴다.**
- ★ r0 의 "V6 하락 폭 = limiter 부동의 비용" 해석은 **철회** — v2→v3 하락은
  공격자를 세 축에서 바꾼 결과다. limiter 부동 비용은 나중에 **동일 V3-FULL
  위에서 static limiter vs active limiter 비교**로만 측정한다.

## 5. 검증 게이트 (결과 보기 전 선언)

```
P87  NESTING: 신규 필드 전부 기본값 -> A2(jink 0.6) 및 SCALE_V2_SPAWN 과
     bit 동일 (attacker action + spawn draw 양쪽. P1/P19 규약 동형)
P88  방향성 manipulation gate: §3.2 의 a~e 5개 전부 성립
P89  능력 준수 + saturation audit:
     (i)  전 스텝 |v_att| <= adversary_v_max · |a_cmd| <= a_att_max
     (ii) ★ 기록 의무 (clip 은 통과 증명이 아니다): raw pre-clip |a| ·
          clip 발생 스텝 비율 · requested vs realized route 성분 ·
          sprint 구간의 잔여 route authority.
          jink 0.6 + route 0.5 > 1 (×a_lat_max) 이므로 lateral 포화가
          구조적으로 가능 -- 포화가 광범위하면 (i)(ii) 는 독립 축이 아니며,
          route_gain 0.5 를 결과 전에 재비준한다 (값 인하 or accel budget
          composition 명시)
P90  침투 능력 보존: 사전등록 seed n=100 · defender 전원 제거 ->
     100/100 PENETRATED · TRUNCATED 0 · self-failure 0.
     - TRUNCATED 발생 시 "공격자가 강/약해졌다" 로 해석 금지 -- V6 전에
       horizon 계약을 재사전등록 (episode_len 1000 은 이 gate 조건부 임시값)
     - defender 부재라 route 는 자동 off -- 이 gate 는 (ii) 의 적대적
       유능성을 보지 못한다. 그건 P88 의 몫이다
P91  rotation-equivariance (§4.3): 배선 전 실행. 실패 시 축 (iii) 동결
V6   nested arm baseline (V3-C / V3-CS / V3-FULL · hold/clean · 동일 seed ·
     각 n=100): 수락대역 없음 -- 새 위협의 첫 측정. **descriptive baseline
     로만 사용** (arm 간 차분 = 각 축의 기여. "limiter 부동 비용" 해석 금지)
V7   뷰어 재생성 -> Hyunjun 육안 검사 (viz-first. 스프린트 전환점 · 저속
     구간 · 회피 기동 · 회전 배치가 육안으로 식별되는지) -- 승인 후에야
     v3 위 실험 사슬 (limiter 재학습 포함) 재개
```

판정식·선언값은 결과 후 불변경. 조정은 새 사전등록으로만.

## 6. 격리·배선 규율

- 브랜치 `feat/scale-up-v2` 유지. 배선 = `AttackerSpec`/`SpawnSpec` 필드
  추가 + `scale_v2.py` 에 `THREAT_V3_*` 선언 dict — 새 코드 경로 최소
  (§2 전진항 치환 · §3 기존 항 활성화 + 감지 클립 + probe 재파라미터화).
- legacy / v2 / v3 수치를 같은 표에 섞지 않는다 (P78 규율 동형).
- v3 확정(§7 잔여 폐기 + P87~P91 green) 전 금지 유지: limiter 학습 ·
  oracle 확장 · r_nk 튜닝.

## 7. 자유도 동결표 (r1 — 결과 전 전부 노출·동결)

r0 체크리스트는 route_gain·azimuth 등을 누락했다 (사전등록 시점 증명 결함).
**결과에 영향을 주는 모든 자유도**:

| # | 자유도 | 값 | 상태 |
|---|---|---|---|
| 1 | `sprint_range` | 60 m | 비준 |
| 2 | `sprint_frac` | 1.0 | 비준 (sweep 축) |
| 3 | `slowdown_range` | (90, 60) m | 비준 (기전 주장 보류, §2.1) |
| 4 | `slowdown_frac` | 0.5 | 비준 |
| 5 | `route_gain` | 0.5 | **조건부** — P89-(ii) saturation audit 후 확정 |
| 6 | `sense_range` | 30 m | 비준 (선언값 + sweep 축) |
| 7 | `route_probe` | 5.0 m (절대값 재파라미터화) | **재비준 대기** — §3.1 제안 |
| 8 | `r_range` | (250, 350) m | 비준 |
| 9 | `azimuth` | ±π/4 | 비준 (v3.0 = rotational randomization 명명 조건) |
| 10 | `episode_len` | 1000 | **임시** — P90 통과 조건부 |

배선 착수 조건: #7 재비준. #5·#10 은 배선 후 해당 gate 결과로 확정하되
**게이트 판정식 자체는 이 문서로 이미 동결**됐다.

## 8. 비준 로그 (2026-08-07 Hyunjun — 판정 원문 요지)

| 항목 | 판정 |
|---|---|
| 경로 B | 승인 |
| 축 (ii) reactive attacker | 승인 · 단 P88 을 방향성 gate 로 강화 (§3.2 반영) |
| 축 (i) sprint 60 m | 승인 (선언값) |
| 축 (i) slowdown (90,60)/0.5 | 승인 · "feint/bait" 기전 주장 보류 (§2.1 반영) |
| 축 (iii) ±45° + ring 회전 | 승인 · "rotational randomization" 재명명 (§4.1 반영) |
| sense_range 30 | 승인 · "보수적 시각 탐지거리" 표현 삭제 (반영) |
| r_range (250,350) | 승인 |
| episode_len 1000 | P90 통과 조건부 임시 비준 |
| route_gain 0.5 | saturation audit (P89-(ii)) 조건부 |
| route_probe | **비준 불가 → r1 에서 코드 확인 후 5.0 m 절대값 재선언 제안 (§3.1)** |
| V6 "limiter 부동 비용" 해석 | 철회 · nested arm descriptive baseline 로만 (§4.5 반영) |
| 추가 지시 | nested arm 보존 (§4.5) · P91 equivariance 사전 검사 (§4.3) · 자유도 전수 동결 (§7) |
