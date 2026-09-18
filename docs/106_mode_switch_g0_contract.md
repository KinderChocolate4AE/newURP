# 106 — mode-switch G0 결정 카드 (F1-E·D1 toy 공용 계약)

- **일자·상태:** 2026-09-18 · **r3** — [105 r4](105_mode_switch_execution_plan.md) §3의 D0 산출물.
  본 카드가 채워진 시점부터 아래 값은 "권장 출발점"이 아니라 **F1-E·D1의 한 버전으로
  고정된 결정**이다. 변경은 판올림하고 변경 전 산출물에 적용하지 않는다.
- **r3 개정 (8.22 m 의미 정정 + D2 거리 진단 추가; 물리값·포획 규칙 변경 없음):**
  1. "anchor 유효사거리 8.22 m" 표현 정정 — 8.22 m는 실측 최대 유효사거리가 아니라
     **`prototypes/net_forward` 시뮬의 전개 완료 시점(τ_flight 0.15 s) 계산상 중심
     병진**이다 (Xu baseline 45°/60 m/s/35 g, rho_air 1.513 보정 = m4_config
     `viability.cone.range_max`의 유도와 동일). **원논문(Drones 2025, 9:190)에는
     교전거리·사거리 수치 자체가 없다** (PDF 직접 확인; docs/34 §3.1·docs/39 §3 동지).
     따라서 active 구간의 net 운동·포획은 "확인된 전개 시점의 운동 상태에서 외삽"으로
     서술하고, 8.22 m에서 포획을 차단하는 규칙은 추가하지 않는다.
  2. §1.2에 D2 기술 진단 추가 — 첫 net 포획 시 **FIRE 시점 shooter 위치** 기준 중심
     이동거리 `d_cap`의 값·분포·`d_net_anchor = 8.22 m` 초과 비율. 물리 타당성
     진단이며 성공률·비용의 새 판정 기준이 아니다. `mode_switch.f1e.d_net_anchor` 등록.
- **r2 개정 (계약 모순 2건 해소; 기존 물리값 변경 없음):**
  1. §1.2 포획 가능 구간을 **전개 완료 후**로 고정 — r1의 "`t_FIRE < t ≤ t_spent`"
     표기가 `T_active`(전개 완료 후 유효시간) 정의와 모순이었다. deploying/active/spent
     전이·tick 경계 규약·전개 중 무포획을 명시.
  2. §1.2 발사 방향 `n̂`의 조준 규칙을 "식은 D2 script에 고정" 예고에서 **G0 계약으로
     격상** — 세 정책 공유 1차 lead + pure-pursuit fallback + 퇴화 시 사전 거부.
     신규 수치 guard `ε_aim`은 `mode_switch.f1e.aim_eps`로 등록.
- **r1 개정 (사용자 승인 4건 + provenance 교정):**
  1. kinetic = **근접 접촉 사건으로 효과를 판정하는 소모성 요격기** — 실제 기체
     충돌·ramming으로 부르지 않는다 (§1.1).
  2. 발사형 net = **이동하는 원판** — 중심까지의 구면 거리 판정 폐기, 원판 평면
     통과 판정으로 교체 (§1.2).
  3. **실제 안전 위반**과 **guard가 거부한 위법 명령 요청**을 별도 회계 (§1.8).
  4. F1-E attacker는 방어기 위치·속도에만 반응 — FIRE·mode·net phase 단서 차단을
     adapter 계약으로 구체화 (§1.7).
  - provenance 교정: `0.75 m`·`τ`·`R_net`의 원 출처와 "새 메커니즘에서의 의미"를
    분리 (§1.1, §1.2, §1.10). shooter/kinetic 초기 배치·paired scenario 규칙 고정 (§1.3).
- **권한 경계:** [89 r4](89_research_plan_r2_hybrid_marl.md)·[102](102_b2_scripted_prereg.md)의
  B0 v3/B2/stop rule 봉인은 건드리지 않는다. 본 카드는 `shepherd/mode_switch/*` 새
  namespace와 `shepherd/params.py`의 `mode_switch.*` 신규 키에만 권한을 가진다.
- **주장 한계:** 이 카드의 수치 다수는 pilot 임의값 또는 **원 출처와 다른 새 의미로
  재사용된 값**이다. 이 계약 아래의 모든 결과는
  [104 r6](104_next_direction_behavior_predictivity.md) 부록 B의 F1-E 행이 허용하는
  범위(소재 판정·궤적/first-hit 디버그)까지만 해석한다. F1-E 결과가 나오기 전에
  양성 결과·Q1 신규성을 확정하지 않는다.

## 1. 결정 표 (105 §3의 10행을 한 버전으로 고정)

### 1.1 kinetic mechanism

**근접 접촉 사건으로 효과를 판정하는 소모성 요격기(proximity-event consumable
interceptor) 한 종류.** 실제 기체 충돌·ramming·탄두 기폭으로 부르지 않는다.
projectile gun 등 다른 kinetic 유형과 혼합 금지 (104 §3.1).

| 항목 | 결정 | 출처·의미 구분 |
|---|---|---|
| 효과 판정 | attacker–interceptor swept-segment 최소거리 ≤ `r_K_contact = 0.75 m` 이면 **접촉 사건** 발생 | 값의 원 출처 = **docs/34 §6 A7 기하 유도** (표적 반치수 0.21 + 요격기 반치수 0.25 + 유도오차 0.10~0.40, [m4_config.py](../shepherd/m4_config.py) `physics.kill_radius` override) — **B0 v3 운용점 선언값이지 env_sys.py에 고정된 실측 충돌 반경이 아니다.** F1-E에서는 **효과 판정용 근접 반경**이라는 새 의미로 재사용 — 물리 충돌·실측 살상 효과로 해석 금지. sweep `{0.6, 0.75, 0.9}` (docs/34 기선언 승계) |
| neutralization | 접촉 사건에서 Bernoulli(`p_kill`). **`p_kill ∈ {0.7, 0.85, 1.0}` sweep 축** — 1.0 단일 봉인 금지 (105 §3) | SYNTHETIC_EXPLORATORY (외부 effect 근거 없음 — §1.10 한계) |
| platform loss | **효과 resolution**(성공·실패 무관) 시 interceptor 소모 = 허가된 sacrifice (`n_K,sac`) | 구현 정의. guard **거부만으로는 소모·손실이 발생하지 않는다** (아래 행) |
| guard 거부 2종 | (a) **사전 거부**: `KINETIC_COMMIT` 요청 시점에 NK-zone·소모 상태 등 위반이면 명령 자체를 거부 — 아무것도 소모되지 않고 `n_reject_commit` 카운트. (b) **효과 시점 거부**: commit 후 접촉 사건이 NK-zone 안에서 일어나면 효과 보류 — 미소모, `n_withhold_effect` 카운트, 재접촉 시 재평가 | [env_sys.py](../shepherd/env_sys.py) veto 의미론(기폭 보류, docs/29 §13) 재사용. **어느 쪽도 `K_illegal`·platform loss가 아니다** (§1.8) |
| time-to-go | point-mass 동역학에서 산출 (별도 해석식 없음) | 구현 정의 |
| 기동 상한 | `a_max = 15.413 m/s²`, `v_max = 25.946 m/s` — shooter와 동일 | [mobile_finisher.py:43-44](../shepherd/agents/mobile_finisher.py) MOBILE_A/V_MAX 재사용 · ASSUMED |

### 1.2 net mechanism — 이동하는 원판 (moving-disc surrogate)

**shooter가 projectile net 1발 발사.** tethered/carried net과 혼합 금지 (104 §5.3).
**net 중심까지의 구면 거리로 포획을 판정하지 않는다.**

- **launch state:** FIRE tick에 shooter 위치에서 net 중심 초기화. 발사 방향
  `n̂`은 아래 **조준 규칙**으로 FIRE tick 관측에서 결정론적으로 계산되며 —
  **원판 법선으로 FIRE 시 고정**, 이후 회전하지 않는다. 중심은 `v_net · n̂`
  등속 병진.
- **조준 규칙 (세 정책 공유 · G0 고정):** [105 §6](105_mode_switch_execution_plan.md)의
  세 정책 모두 같은 규칙을 쓴다. 입력은 FIRE tick의 관측(§1.6 참값)
  `r = p_att − p_shooter`, `u = v_att`와 레지스트리 `v_net`뿐이다.
  1. **퇴화:** `‖r‖ ≤ ε_aim`이면 조준 방향이 정의되지 않는다 — commit guard가
     `NET_COMMIT`을 **사전 거부** (`n_reject_commit` 계상, cartridge 미소모, §1.8 회계).
  2. **1차 lead 해:** `a = ‖u‖² − v_net²`, `b = 2 r·u`, `c = ‖r‖²`의
     `a t² + b t + c = 0`에서 **양의 실근 중 최소** `t*` (수치 안정형 근의 공식;
     `a = 0`이면 1차식 `t* = −c/b`, `b < 0`일 때만 유효). 해가 있으면 조준점
     `q = p_att + u·t*`, `n̂ = (q − p_shooter)/‖q − p_shooter‖`
     (분모 ≤ `ε_aim`이면 해 없음으로 처리).
  3. **fallback (해 없음):** pure pursuit `n̂ = r/‖r‖`.
  - 계약 상한에서는 `‖u‖ ≤ 20 < v_net = 55`라 `a < 0`이고 양의 해가 항상 존재한다 —
    fallback은 `v_net = 20` sweep에서만 실효.
  - **금지:** 미래 참값·attacker latent type·counterfactual/사후 성공 결과를 조준
    입력으로 쓰지 않는다 (등속 외삽은 FIRE tick 관측만의 함수다). **첫 결과를 본 뒤
    조준식을 튜닝하지 않는다** — 변경은 판올림 + 변경 전 산출물 비적용 규칙만 따른다.
- **개구:** `R(t) = R_net · min(1, (t − t_FIRE)/τ_aperture)` — 전개 중 선형 ramp.
  **deploying 구간의 `R(t)`는 net 상태(§1.6 phase 관측·시각화)만 나타내며, 그
  구간에서 capture는 발생하지 않는다.**
- **phase 전이·포획 가능 구간:** `t_deploy_done = t_FIRE + τ_aperture`,
  `t_spent = t_deploy_done + T_active`.
  - deploying: `t_FIRE ≤ t < t_deploy_done` — **포획 불가.**
  - active(포획 가능): **`t_deploy_done ≤ t < t_spent`** (좌폐우개) —
    `T_active`(전개 완료 후 유효시간) 정의와 일치.
  - spent: `t ≥ t_spent`.
  - 계약 dt 0.05에서 두 경계는 tick 격자 위에 떨어진다 (τ_aperture = 3 tick,
    T_active = 6 tick); 경계 tick의 소속은 위 좌폐우개 규약이 정한다.
- **포획 판정:** **표적의 상대 궤적이 움직이는 원판 평면을 통과**하고, 보간한
  통과 시각 `t_cross`가 **active 구간 `[t_deploy_done, t_spent)` 안**이며,
  **통과점의 반경 방향 거리 ≤ `R(t_cross)`** 일 때만 capture — active 구간에서는
  전개가 끝나 `R(t_cross) = R_net`(상수)이다. tick 사이 통과도 검사한다:
  원판 좌표계에서 축방향 좌표의 부호가 tick 사이에 바뀌면 통과 시각을 보간해
  판정한다 (tunneling 금지). **`t_cross`가 deploying 구간이면 반경 조건과 무관하게
  capture가 아니며**, net은 소모되지 않고 아래 spent 규칙만 따른다.
- **tick 경계 사건 순서:** 한 tick의 step 순서는 105 §5(관측 → 유도·mode 요청 →
  commit guard → 적분 → swept 접촉·breach·unsafe 판정 → first-hit → 소모/기록)를
  따른다. FIRE tick의 적분 구간부터 통과 검사를 시작하되 `τ_aperture > 0`이므로
  FIRE 직후 tick들의 통과는 deploying에 떨어져 capture가 될 수 없다. phase 소속은
  tick 라벨이 아니라 **연속 시각(보간 `t_cross`)이 어느 구간에 속하는지**로 판정한다.
- **spent 규칙 (첫 pilot):** 조기 miss 추정으로 `NET_SPENT`를 만들지 않는다.
  개구 밖 통과·미통과와 무관하게, 포획하지 못한 net은 **`t_spent` 만료 시에만**
  spent 처리한다.
- **대리모형 한계:** 원판·등속·법선 고정은 **F1-E 대리모형**이다. 실제 net
  전개·감속·얽힘·형상의 검증이라는 주장은 금지한다 (Han 2026의 전개–충돌–얽힘
  sequence 검증과 무관). anchor가 근거하는 구간은 **전개 완료 시점까지**(계산 병진
  ≈ 8.2 m)뿐이므로, **전개 완료 이후의 net 운동·포획은 확인된 전개 시점의 운동
  상태에서 외삽**한 것이다 — 등속 유지는 그 외삽의 낙관 대리다.
- **D2 거리 진단 (기술 항목):** D2 산출물에 net capture 사례마다
  `d_cap = ‖p_net(t_cross) − p_shooter(t_FIRE)‖` (등속 대리모형에서
  `= v_net·(t_cross − t_FIRE)`)를 기록하고, 분포(min/중앙값/max)와
  **`d_cap > d_net_anchor = 8.22 m` 비율**을 보고한다. 기준점은 **FIRE 시점
  shooter 위치로 고정** — FIRE 후 이동한 현재 shooter 위치가 아니다.
  기본값에서 active 구간의 `d_cap` 가능 구간은 `55·[0.15, 0.45) = [8.25, 24.75)` m,
  `v_net = 20` sweep에서는 `20·[0.15, 0.45) = [3.0, 9.0)` m — **선언된 등속
  대리모형의 산술이지 실물 net 유효사거리 측정이 아니다.** `d_net_anchor`는
  net_forward baseline의 전개 완료 시점 계산 병진(위 r3 개정 1)이지 실측
  유효사거리가 아니므로, 이 진단은 "포획이 anchor 구간 밖 외삽 영역에서 얼마나
  일어나는가"를 보이는 **물리 타당성 진단**이다 — 성공률·비용의 새 판정 기준이
  아니며, `d_net_anchor`에서 포획을 차단하지 않는다.

| 값 | 결정 | 출처·의미 구분 |
|---|---|---|
| `τ_aperture = 0.15 s` | 전개 ramp 시간 | 원 출처 = [m4_config.py](../shepherd/m4_config.py) `TAU_DECOMPOSITION.tau_flight` (Xu Fig.6 개방 0.13 s + dt 격자, DERIVED). **주의**: params 기본 `tau_deploy=0.4`(ASSUMED)와 B0 v3 override `0.30`(flight+sense+decide 분해)은 **commit→판정 지연**이라는 다른 의미다. F1-E는 관측 무지연 계약(§1.6)이라 sense/decide 0.15 s가 접히지 않는다 — **그만큼 B0 v3 대비 낙관**. in-flight ramp라는 새 의미는 미검증 — sensitivity 축 |
| `R_net = 1.77 m` | full-aperture 반경 | 원 출처 = docs/42 A3 (Xu 등가면적 1.997 × 내접비 0.888, 낙관 상한 caveat 승계, B0 v3 운용점). **이동 원판이라는 새 메커니즘의 물리 검증이 아니다.** sweep `{1.77, 2.0}` (2.0 = 구 등가면적점) |
| `v_net = 55 m/s` | 중심 등속 | 원 출처 = net_forward baseline 병진 8.22 m / 0.15 s ([m4_config.py](../shepherd/m4_config.py) range_max 근거). **등속 유지는 발사 후 감속을 무시한 낙관 대리** — 실제 net은 개방 후 급감속. sweep `{20, 55}` |
| `T_active = 0.3 s` | full-aperture 후 유효시간 | SYNTHETIC_EXPLORATORY. 등속 가정 하 active 종료까지 중심 이동 = 55·0.45 = 24.75 m — **anchor(전개 완료 시점 계산 병진 ≈ 8.2 m)가 근거하는 구간을 크게 넘는 외삽 낙관.** sensitivity 축 |
| `ε_aim = 1e-6 m` | 조준 규칙 퇴화 guard (`‖r‖`·`n̂` 분모 판정) | SYNTHETIC_EXPLORATORY — 수치 guard 임의값, 물리 의미 없음. `mode_switch.f1e.aim_eps` |
| `d_net_anchor = 8.22 m` | D2 거리 진단 기준선 (포획 차단 아님) | 원 출처 = `prototypes/net_forward` baseline 중심 병진 @ τ_flight 0.15 s (DERIVED; m4_config `viability.cone.range_max`와 동일 수치·동일 유도). **실측 최대 유효사거리 아님 — 원논문에 사거리 수치 없음.** rho_air 1.225~2.0 sweep에서 8.34~8.04 (±2%, docs/42) |

### 1.3 자산·초기 배치·paired scenario

attacker 1 · mobile net shooter 1 · kinetic interceptor 1. **limiter 없음** (105 §3 —
104 §3의 장기 확장 세계와 다르다).

| 항목 | 결정 | 출처 |
|---|---|---|
| 보호 자산 | 원점, breach 반경 `1.0 m` | train.layout.target/target_radius 재사용 · ASSUMED |
| shooter spawn | `(8, +3, 0) m`, 초기속도 0 | 전방 8 m = train.layout.ring_center 관례 재사용; 횡 ±3 m = **탐색용 가정** (SYNTHETIC_EXPLORATORY) |
| kinetic spawn | `(8, −3, 0) m`, 초기속도 0 | 동일 (대칭 배치, 탐색용 가정) |
| attacker spawn | 거리 `r₀ ~ U[20, 28] m`, 방위각 `ψ ~ U[−30°, +30°]` (x축 기준, z=0 평면), 초기속도 20 m/s 자산 방향 | 24 m 점값(train.layout) 대신 구간 randomize — 구간은 SYNTHETIC_EXPLORATORY |
| paired 생성 규칙 | scenario ID → SHA-256 결정론 draw ([m4_config.py](../shepherd/m4_config.py) `draw_threat` 관례). **세 정책(105 §6)은 같은 scenario ID의 같은 exogenous draw(초기상태·attacker seed)를 공유** (CRN) | 구현 정의 |
| attacker 상한 | `v = 20 m/s`, `a = 30 m/s²` | physics.att_speed/a_att_max 재사용 · ASSUMED |
| shooter/kinetic 상한 | §1.1과 동일 (둘 다 MOBILE_A/V_MAX) | 재사용 · ASSUMED |

**단일 배치 결론 금지:** 위 배치는 한 개의 탐색 배치다. 후속 sensitivity 축으로
(i) 방어기 전방 이격·횡 오프셋, (ii) 동일지점 vs 분산 배치, (iii) attacker 방위각
범위 확대를 명시해 두고, F1-E 첫 그림은 이 한 배치에서 **소재 판정만** 한다.

### 1.4 탄약·재고

net cartridge 1발 · interceptor 1대 · **episode reset** (raid 없음 — E2 주장 금지, 104 §3.5).
`NET_COMMIT`은 FIRE tick에 cartridge 즉시 소모. interceptor는 §1.1 규칙으로 소모
(guard 거부·효과 보류는 미소모). net 실패(SPENT) 후 kinetic이 남아 있고 ROE 허용 시
fallback 가능. **kinetic commit 후 net 복귀 금지** (104 §3.2 규칙 5) — 따라서
kinetic-first에는 net fallback이 없다 (105 §6의 비대칭, 숨기지 않고 보고).
동일 tick 이중 commit 금지 (규칙 6).

### 1.5 행동·권한

- mode action: `WAIT/SHAPE`, `NET_COMMIT`, `KINETIC_COMMIT` — 매 tick 선택 가능.
- 최초 mode 전환 기한: 명시적 deadline 없음 — timeout·ROE 폐쇄가 사실상의 기한.
- post-commit fallback 권한: 세 정책(105 §6) 모두 동일한 world 전이를 따른다 —
  net 실패 확정 후 kinetic만 가능, kinetic 후 net 불가.
- commit guard: 소모된 효과기 재commit 거부, NK-zone 내 kinetic commit 사전 거부,
  조준 퇴화(§1.2 조준 규칙 1) NET_COMMIT 사전 거부 — 거부는 §1.8의 요청 카운터로만 기록.

### 1.6 관측 (정책 측)

- 정책 입력: 전 기체 위치·속도 참값 + net phase(`ready/deploying/active/spent`) +
  잔여 inventory. **무잡음·무지연** (F1-E 한정).
- 누설 금지: attacker latent type·미래 결과·counterfactual 성공 여부.

### 1.7 공격자 — adapter 계약과 cue 차단

- 1차 후보: 기존 A2 계열([attacker_ladder.py](../shepherd/agents/attacker_ladder.py))을
  adapter로 재사용. kinetic interceptor를 `limiters` 입력의 1행으로 매핑.
- **입력 제한 (승인 결정 4):** attacker 입력은 **방어기·자산의 위치·속도(및 자기 상태·
  시간)만.** FIRE 여부, mode commit, net phase, net 실위치 단서를 제공하지 않는다.
- **차단의 구체 조건** — `react_on_commit=False`만으로는 불충분하다:
  - `committed=False` 고정. A2의 `committed`는 dodge뿐 아니라
    **jink(`_jink_accel`)·bait(`_bait_accel`)의 게이트**에도 들어간다
    ([attacker_ladder.py:168](../shepherd/agents/attacker_ladder.py#L168),
    [324](../shepherd/agents/attacker_ladder.py#L324),
    [400](../shepherd/agents/attacker_ladder.py#L400)) — 어느 항으로도 FIRE/commit
    정보가 새어서는 안 된다.
  - `net_center` 입력은 **FIRE 상태와 무관한 운동학 예측식**(shooter 위치·속도만의
    함수)으로 고정한다. FIRE 후 실제 net 위치를 넣으면 간접 누설이다.
  - `v_shot_soft`는 전달하지 않는다 (privileged bait 경로 차단).
- **D2 검사 (105 §7 연동):** FIRE 여부만 다르고 공격자·방어자 운동학, 시간, 난수
  상태가 같은 쌍에서 **공격자 행동(가속 명령)이 동일**해야 한다. net 상태나 파생
  입력을 통한 간접 누설도 같은 검사의 대상이다. 방어기 기동 변화에 대한 반응
  검사(paired 계측)는 이와 **별도로** 유지한다.
- 1대 입력에서 route/bait law가 퇴화하면 그 사실을 기록하고 별도 반응 모델 교체를
  명시한다. 퇴화 상태의 사례는 "반응형 공격자"로 세지 않는다. cue 반응이 없으므로
  F1-E 결과로 "적응형 cue 대응"을 주장하지 않는다.

### 1.8 보호·안전 — first-hit 분류와 요청 회계의 분리

104 §4.2의 배타적 first-hit outcome `{N_safe, K_safe, B, K_illegal, C_unsafe, L_unauth, O_timeout}`.

- **회계 분리 (승인 결정 3):**
  - **실제 위반 outcome**: `K_illegal`(NK-zone 내 kinetic 효과 발생),
    `C_unsafe`, `L_unauth` — first-hit 분류로만 기록.
  - **거부된 명령 요청**: `n_reject_commit`(사전 거부), `n_withhold_effect`
    (효과 시점 보류) — **별도 카운터**로 기록. 거부·보류는 outcome이 아니며
    플랫폼 손실·`K_illegal`을 발생시키지 않는다.
- **구조적 사실 (정직 명시):** 본 계약의 F1-E에서 `K_illegal`은 guard의 사전
  거부 + 효과 시점 보류가 **구조적으로 차단**하므로 도달 불가다. `C_unsafe`는
  방어기·지형 충돌 물리가 없어, `L_unauth`는 추락·비허가 손실 기제가 없어
  **발생 기제 미구현**이다. 따라서 `P_unsafe ≤ β`는 자명하게 충족되며, 이를
  근거로 **안전 우위·"동일 안전 문턱 하 최저비용" 실증을 주장하지 않는다.**
  첫 그림은 보호 outcome, 자원 벡터, 거부/보류 요청률을 **기술적으로 보고**한다.
  수치를 채우기 위해 근거 없는 위해 사건을 새로 만들지 않는다.
- **no-kill zone:** 자산 중심 반경 `r_nk = 6.0 m` — [env_sys.py:93](../shepherd/env_sys.py)
  재사용 (ASSUMED, 외부 ROE 검증 아님 — 104 부록 B).
- **same-tick 우선순위 (보수 규칙, 105 §5):** 한 tick에 복수 조건 성립 시
  `K_illegal > C_unsafe > L_unauth > B > N_safe > K_safe` 순으로 정확히 하나만 판정.
  위반·breach가 성공에 항상 우선한다. breach 이후의 neutralization은 성공으로
  재집계하지 않는다. (앞 두 위반은 F1-E에서 구조적 0이지만 순위는 계약으로 봉인.)
- **timeout:** `T_H = 8.0 s` (160 tick, dt 0.05) — SYNTHETIC_EXPLORATORY.
  종료 시 미판정이면 `O_timeout`.

### 1.9 비용

- 정규화 `c_N = 1` (net cartridge 1발 = 1).
- sacrificial 결정론이므로 104 §4.3 허용에 따라 kinetic 운용비+허가 손실을 단일
  비용비 `ρ_K = (c_K^op + c_P,K^sac)/c_N`로 합침. **sweep `ρ_K ∈ {0.5, 1, 2, 4, 8}`** —
  SYNTHETIC_EXPLORATORY.
- `L_unauth`는 F1-E에서 발생 기제가 없다 (§1.8) — 카운터 자리만 두고 비용 합산 없음.
  시간·에너지 비용 항은 F1-E에서 off, `T`는 기록만.
- **비용을 outcome penalty로 reward에 섞지 않는다.** 보호·안전은 문턱, 비용은 그 안의
  비교 (104 §4.2). 원화·달러 환산 주장 금지 (104 §5.5).

### 1.10 출처 요약 — 원 출처 vs 새 메커니즘 검증

| 값 | 원 출처 (숫자의 출신) | F1-E에서의 의미 | 새 메커니즘 검증 |
|---|---|---|---|
| `r_K_contact 0.75` | docs/34 §6 A7 기하 유도 (m4_config override; env_sys 고정 실측 아님) | 근접 효과판정 반경 (충돌·살상 아님) | 미검증 — sweep 0.6/0.75/0.9 |
| `τ_aperture 0.15` | m4 TAU_DECOMPOSITION tau_flight (Xu Fig.6, DERIVED) | in-flight 개구 ramp (B0 v3 tau 0.30·params 0.4와 **다른 의미**) | 미검증 — sense/decide 미포함 낙관 |
| `R_net 1.77` | docs/42 A3 (Xu 등가면적 × 내접비, 낙관 상한) | 이동 원판 개구 반경 | 미검증 — sweep 1.77/2.0 |
| `v_net 55` | net_forward baseline 병진 8.22 m / 0.15 s | 등속 원판 병진 (감속 무시 낙관) | 미검증 — sweep 20/55 |
| `d_net_anchor 8.22` | net_forward 전개 완료 시점(τ_flight 0.15 s) 계산 병진 (DERIVED — 원논문에 사거리 수치 없음) | D2 거리 진단 기준선 | 진단 전용 — 포획 차단·성공/비용 판정 아님 |
| `T_active 0.3` · `T_H 8.0` · `p_kill`·`ρ_K` sweep · 배치·spawn 구간 · `ε_aim 1e-6` | 없음 (pilot 임의) | SYNTHETIC_EXPLORATORY | 미검증 |
| dt 0.05 · attacker 20/30 · target_radius 1.0 · r_nk 6.0 · MOBILE_A/V_MAX | repo 기존 fixture (ASSUMED) | 동일 의미 재사용 | 원 계약의 미검증 상태 승계 |
| **의도적으로 열어 둔 불확실성** | kinetic effect model 전체(외부 자료 없음) · net 전개/감속/얽힘(원판 대리) · 안전 위반 기제(구조적 0) · 단일 배치 | → 결론은 "선언된 simulation plant와 효과범위 안의 비용 비교"로 한정 | — |

## 2. 레지스트리 규약

- **D1 toy** = `mode_switch.toy.*` — 소비 코드가 있으므로(`toy_dp.default_params`,
  실행 스크립트) `wired=registry-direct`.
- **F1-E** = `mode_switch.f1e.*` — **아직 소비 코드가 없다** (D2 미구현). 따라서
  `wired=doc-only`로 등록하고, **D2 구현 시 실제 소비 경로에 맞춰
  `registry-direct`로 갱신**하는 것을 D2 완료 조건에 포함한다.
- 임의 pilot 값은 status `SYNTHETIC_EXPLORATORY`, 재사용·유도 값은 숫자의 출신에
  맞는 기존 status(ASSUMED/DERIVED)를 쓰고 `source`에 원 출처를, `note`에 새
  의미·미검증 범위를 적는다.
- 실행 manifest는 레지스트리 resolved 값을 스냅샷할 뿐 별도 태그 체계를 만들지 않는다.

## 3. D1 toy 계수의 지위

D1 finite DP의 branch prior·cue likelihood·mode별 성공/안전 계수는 **전부 toy 예시값**
(SYNTHETIC_EXPLORATORY)이며 §1의 물리값과 수치적으로 연결되지 않는다. D1은 104 T2의
정책군·정보구조(양화 순서) 검산까지만 쓴다 (105 §4.2). toy에서 양성 reversal이 나와도
G2 통과 증거가 아니다.
