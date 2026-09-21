# 94 — B0 v3 world contract (**SEALED** — `b0_hash 5e7b5b486b9d8a4a`)

> **Amendment A1 (2026-09-22)**: [docs/108](108_b0v3_amendment_a1_illegal_engagement.md)
> — illegal engagement 정의를 실효 판정자(swept resolver)에 일치 (docs/103 U-11 근거,
> hash·구현·결과 무변경).

- **일자**: 2026-09-13 · **상태**: **SEALED (사용자 승인 2026-09-13)**.
  - **`b0_hash = 5e7b5b486b9d8a4a`** · exit **`B2_WORLD_CONTRACT_FROZEN`**
  - 기계 정본 = `artifacts/b0/b0_v3_world_contract.json` · 서술 정본 = 본 문서
  - 결재 **①~⑦** 전부 반영 · contract tests **12 passed** · 전체 regression **0 failed**
- **봉인 이후 규율**: world-contract 조항 · 격자 · 판정 규칙이 바뀌면 **v4 + 새 hash** 로
  가고 **기존 v3 결과와 pooling 금지**. 본 문서의 사후 편집은 오탈자·상호참조 수준으로
  제한한다 (내용 변경은 판올림). 봉인 전 협력 학습 실험 금지 조항은 이로써 해제되며,
  **다음 단계는 B2 scripted** — B0 를 더 만지지 않는다.
- **정본 관계**: docs/89 r4 **§5 체크리스트 13항의 이행 문서**. 봉인 시
  `artifacts/b0/b0_v3_world_contract.json` (schema `b0-v3-hybrid`) 로 해시 고정 —
  그 JSON 이 **기계 정본**, 본 문서가 **서술 정본**. exit = `B2_WORLD_CONTRACT_FROZEN`.
- **R2b B0 v2 (`b0_hash cba024d7ee3d9f61`) 와의 관계**: **supersede 아님**. R2b 는 종결된
  캠페인이고 그 계약은 그 캠페인의 봉인으로 남는다. v3 는 세계·좌표·판정·어휘 규율을
  **승계**하고 그 위에 hybrid mission semantics 를 얹는다.
- **입력**: docs/91 v2.1 §7 (시간 구조 재정의) · docs/92 §5 (층1 종료) ·
  `temp_research_note/2026-09-13_w2_code_audit_q1q3q4_*` ·
  `temp_research_note/2026-09-13_layer1_verdict_zero_clean_candidates_*` (후자가 supersede 판).
  본 초안의 모든 사실 진술은 W2 code audit 경로 재확인 (실험 0 · 서버 0).
- **작성 원칙**: 이 문서는 **세계가 코드에 실재하는 대로** 적는다. 희망 사양을 적고 나중에
  맞추는 문서가 아니다. 아직 없는 것은 "부재" 로 적고 층3 (W10+) 으로 넘긴다.

---

## §0. 결재 — ①~⑦ 전부 수령 (2026-09-13)

| # | 결재 사항 | 결정 | 반영 |
|---|---|---|---|
| **①** | resolution-tick precedence | **CAPTURE 우선 — 단 "현행이니까" 가 아니라 *sealed discrete-time tie rule* 로 명시** (연속시간 물리 순서 주장 없음) + `capture_penetration_same_tick` counter 상시 로그 | §2-12 ④ |
| **②** | boundary rule 의 seed 차원 | **per-seed 다수결 (3 seed → ≥2/3) ∧ global positive effect**. 전역 CI 는 seed 를 최상위 독립 단위로 보존하는 **seed-preserving hierarchical paired CI** — 3 cluster 이므로 정밀한 95% frequentist guarantee 로 말하지 않는다 | §2-11 |
| **③** | F1 freeze exception | **주석 수정 + docs/09 예외 등록**. 표현은 "byte 무변경" 이 아니라 **executable semantics unchanged / comment-only diff** | §2-2, §3 t7, §4 |

- **① 의 부수 규율**: 동시발생 빈도는 **로그하되 precedence 결정에 쓰지 않는다**. 빈도가
  크게 나오면 그때는 precedence 를 바꾸는 것이 아니라 **dt-sensitivity /
  continuous-event-resolution 문제로 robustness 단계에서 공격**한다.
- **② 가 ①안(seed-pooled 점추정)을 기각한 이유**: 세 seed 가 (+0.30, −0.02, −0.02) 여도
  평균은 양수라 "이 행 positive" 로 찍힌다 — **한 training seed 의 대성공이 두 seed 의
  실패를 덮는 구조**. MARL 에서 training stochasticity 는 우리가 일반화하려는 변동원
  자체이므로 이 masking 은 허용할 수 없다. 반대로 전 seed 통과 요구는 seed=3 에서 사실상
  worst-seed test 가 되어 진짜 효과를 버린다.

### 결재 ④⑤⑥⑦ (2026-09-13, 초안 검토 라운드)

| # | 사항 | 결정 |
|---|---|---|
| **④** | CWC 보상 supersede | **APPROVE** — docs/66 의 CWC = positive utility 비준은 **hybrid mission 에 한해 supersede**. CWC / illegal pre-net contact 는 clean capture reward 를 받지 않는다. 실제 `r_illegal` 수치는 **training contract** 에서 봉인 |
| **⑤** | `C_illegal` 이 즉시 terminal 인가 | **B = irreversible failure latch**. 최초 pre/pending contact 에서 `C_illegal = 1` 을 latch 하고 **science outcome 은 H_illegal 로 확정**. 물리 rollout 은 코드가 계속 굴리는 곳에서 계속 굴린다. **"terminal failure" 표현은 내린다** (§2-7) |
| **⑥** | hard `θ_fire` gate | **유지 — admissibility constraint 로 명시**. 학습되는 것은 *fixed admissible region 안에서의 firing timing* 이지 gate 자체가 아니다. gate conservatism 은 **forced-fire micro-arm** 으로 별도 측정 (§2-2) |

| **⑦** | 평가 격자 · G | **G = 14 (7 η × 2 λ, R2a Stage 3 구조 승계) · base 4 χ/row 대칭 support · n = 300/cell/seed · A2-nominal 단일 · censoring-triggered ±0.04 최대 2 회 확장** (§2-10a). λ=3.574 는 **유지 + scout provenance 명기** |

- **④ 의 경계**: B0 는 *semantics* 만 정한다 (CWC 는 성공이 아니다). 음수 보상의 **크기**는
  training contract 소관 — 두 문서의 역할을 섞지 않는다.
- **⑤ 가 A(즉시 terminal)를 택하지 않은 이유 = 코드 사실**: 현행 세계에서 pre/pending
  contact 의 종료 여부는 **영역에 따라 갈린다** (§2-7 표). A 를 택하면 wrapper 로 세계를
  바꾸는 것이고, 그러면 "실재하는 코드 그대로 적는다" 는 본 문서의 전제가 깨진다.
  B 는 **권위 술어 (누적 contact = ∅) 가 이미 하고 있는 일**이기도 하다.
- **⑥ 의 귀결 (어휘 금지)**: "learned controller 가 기존 gate 의 censoring 을 해소/회수한다"
  류 주장 **전면 폐기**. 이 세계에서 `v_shot_soft < θ_fire` 이면 정책이 FIRE 를 아무리 내도
  발사가 물리적으로 불가능하다.


---

## §1. 세계 선언 (world assumption)

### 1.1 fidelity · 좌표 (R2a/R2b 승계)

- **환경 fidelity FROZEN (reduced-order 3DOF)**: 지도는 `chi50 = F(eta, lam | M_3DOF, sealed world)`.
  6DOF transfer 는 **별도 transportability gate** (docs/93) 이며 이 캠페인의 일부가 아니다.
- **세계**: legacy 24 m 회랑 · A2-reactive 적대자 (jink 0.6 · route 0.5 · sense 30) ·
  capability-ratio family (μ, ν, κ, N pin) · 동일 judge/labels.
- **좌표**: χ = aτ₀²/2ρ · η = vτ₀/ρ · λ = R_max/ρ. THREAT bracket = a ∈ [11, 78] ·
  v ∈ [8, 30] (draw 계약) 이며 평가 격자는 **구현 공통 유효 부분격자 내부만** (§2-10).
- **승계 어휘 규율 (위반 금지)**: R2b C arm = *search-based attainment benchmark* (upper
  bound 아님) · 사슬 칸 명칭 = **limiter-control opportunity** ("협력 효과" 금지) ·
  협력 necessity 미확립.

### 1.2 시간 구조 (docs/91 v2.1 §7 승계 — 이번 계약의 핵심 개정분)

**τ₀ 정의 (교체)**: τ₀ 는 generic system latency 가 아니라 **post-fire characteristic
delayed-effect scale** 이다. 표현 규칙 — *"τ₀ is implemented through both the fire-time
viability horizon and the delayed outcome-resolution timer"*. **"물리적으로 실현돼 있다"
단독 표현 금지** (net ballistic 적분으로 오독됨; 이 세계는 reduced-order).

| 양 | 값 (R-ref) | 지위 | 무차원군 |
|---|---|---|---|
| τ₀ ≡ τ_deploy | 0.30 s | governing scale | χ, η 의 τ |
| Δt_dec ≡ dt_phys | 0.05 s | **coupled 고정** (이번 학기 승인) | **q_dec = 1/6 (pinned conditioning)** |
| τ_lock | 0.10 s | outcome-application 지연 + 침투 race 창 | **q_race = 1/3 (contract-fixed ratio)** |
| τ_kill | 0.15 s | limiter kinetic commit 해소 지연 | **q_kill = 1/2 (contract-fixed ratio)** |
| W_net | ≡ τ_lock (상수) | **vacuous** — 포획 수명의 인과 채널 부재 (§2-4) | ω_net 승격 안 함 |

세 비율 전부 ledger 에서 **τ 와 co-scale** 되어 구조적으로 고정된다
(`r2a_lattice.py:119-133` `_inject`: `tau_lock = 0.10·s`, `tau_kill = 0.15·s`,
`dt = 0.05·s`, s = τ/τ_ref). 새 좌표가 아니라 **고정 conditioning** 이다.

> **τ₀ is NOT the total FIRE-to-terminal-resolution delay.** 분해하면 —
> τ₀ = viability / deployment scale (0.30 s) · q_race·τ₀ = 추가 application + race
> 지연 (0.10 s) · **총 pending 지속 = (1 + q_race)·τ₀ = 0.40 s**.
> "그래서 실제 latency 가 0.3 인가 0.4 인가" 라는 질문이 나오지 않도록 **세 값을 항상
> 함께** 적는다.

- **정본 claim 형식 (Paper 1 — 이 형식으로만)**:
  > For the sealed reduced-order world at fixed temporal-resolution conditioning
  > q_dec = 1/6 and fixed timer ratios (q_race = 1/3, q_kill = 1/2), the net-capture
  > boundary is characterized in (χ, η, λ).

  전 latency-scale collapse 의 강한 주장은 하지 않는다.
- **해석 금지 3종 (봉인)**: ① q_dec 1/6→1/12 의 χ50 ~+0.15 는 **temporal-resolution
  conditioning** — "decision cadence 의 인과 효과" 해석 금지 (cadence 와 수치 해상도가
  동시에 이동). ② **τ₀→0 은 singular instantaneous-effector limit** — smooth
  extrapolation 대상 아님, baseline 참조점으로만. ③ 관측 지연 성분은 존재하지 않으므로
  어떤 결과도 "sensing 성분 분해" 로 주장 금지.

### 1.3 관측 contract — noiseless · zero-latency

- defender 관측 (`_obs_vector`) 과 FIRE 판정 입력 (`v_shot_soft`, `boxed_in`) 은 **당 틱
  참값**에서 즉석 계산된다. buffer·필터·측정 나이·잡음 주입 코드가 **배선돼 있지 않다**
  (obs_threat · env_adv · env 전수 확인). 따라서 **t_obs ≡ t_fire** 이고 현행 세계에서
  **τ_real ≡ τ_deploy by construction**.
- 이것은 측정 결과가 아니라 **세계의 정의**다. σ̃_p · q_sense 는 층1 screen 후보가 아니라
  **구현 결정**이며 층3 (W10+ frozen-policy robustness) 으로 이월한다.
- 유일한 지연 채널은 적대자 쪽 A3-privileged `v_shot_soft` 1-step leak
  (`env_adv.py:142`, sealed A2 계약의 일부) — defender t_obs 정의와 무관.

### 1.4 층1 종료 조항 (docs/89 §5-10 이행)

> **Layer-1 physical/environment sensitivity audit completed with no clean executable
> perturbation candidate under the current simulator architecture. Candidate effects were
> either already promoted/pinned, absent from the implemented world, physically vacuous,
> or confounded by coupled temporal resolution. No additional physical coordinate was
> promoted before B0 v3.**

- 근거: #1 ω_net **vacuous** (§2-4) · #2a/2b noise/latency **미배선** (§1.3) · #4 actuator
  lag **노브 부재** (`sim/analytic.py:109-131`: 명령 가속 즉시 적용 — a_max clamp + v_max clip +
  heading slew 뿐, 1차 lag 없음) ·
  q_dec **기지 pinned** (재스크리닝 금지) · #3 latency-scale collapse **HOLD**
  (conceptually valid but currently confounded by q_dec–dt coupling; defer unless a
  q_dec-preserving implementation is available).
- **어휘 금지**: "추가 민감성 없음" · "robustness demonstrated" · "민감도 검증 완료".
  정확한 문장은 **"clean candidate 없음으로 pre-B0 sensitivity screen 종료"** 뿐이다.
- **귀결**: stratification/randomization 대상 파라미터에 **추가 변수 없음** — (χ, η, λ, A)
  네 축이 전부다 (§2-10).
- 민감도의 재등장 시점: **층2** = training hyperparameter (stop-rule PASS 후) /
  **층3** = frozen-policy robustness (W10+: noise · latency · actuator lag · speed
  mismatch · cone · airframe-consistent · 가능하면 decoupled q_dec). B0 **전**에
  noise/lag 를 구현해 screen 하는 것은 검정이 아니라 **모델 확장**이므로 하지 않는다.

### 1.5 기계 정본 = resolved-contract manifest

- 같은 실험 family 의 판별 기준은 entrypoint 가 아니라 **동일한 resolved world contract**
  (docs/65 §9). `m4_env.contract_manifest` (schema `resolved-contract-v1`) 가 system /
  reward / attacker / spawn / standby / extra_cfg (= physics.dt · tau_deploy · tau_lock
  포함) / episode_len / judge / n_segments 를 해시한다.
- **train · eval · sweep · scripted 의 manifest hash 는 동일해야 한다**
  (`manifest_mismatch(a, b) == []`). 유일한 예외 축은 봉인 시 `allow` 목록에 명시한다.
- 세계 flags = **비준 F-계약** `ratified_system()` = `SystemSpec(enabled=True,
  contact_resolver=True, miss_terminates=False)` + `capture_terminates=True` ·
  `tau_kill = q_kill·τ₀` · `p_kill = 1.0` · `r_nk = 6.0·r`.

---

## §2. 13항 체크리스트 (docs/89 r4 §5 번호 그대로)

### 2-1. NET_PRE / NET_PENDING / KINETIC 상태 정의

구현된 FSM (`game/finisher_fsm.py`) 에 대한 **매핑으로 정의한다** (새 상태 기계 신설 금지):

| mission mode m | FSM 상태 | 지속 |
|---|---|---|
| **NET_PRE** | `LOADED` ∧ k ≥ 1 | fire 까지 |
| **NET_PENDING** | `DEPLOYING` ∪ `LOCKED` | **τ_deploy + τ_lock = (1 + q_race)·τ₀ = 0.40 s** (8 틱) |
| **KINETIC** | `SPENT` 확정 **다음 control tick 부터** (§2-12 ③) | 종료까지 |

- **mission mode bit 은 이미 관측에 있다** — `env.py:210-212` 가 FSM 4상태 one-hot +
  `k_norm` + `fsm.timer` 를 obs 에 싣는다. **신규 배선 불요** (docs/89 §3.1 요구 충족).
  단 obs 의 one-hot 은 SPENT 진입 틱에 켜지고 mode KINETIC 은 그 다음 틱부터이므로,
  **정책이 행동하는 시점 기준으로는 정렬**된다 (obs 는 post-move 로 계산됨).
- K = 1 (단발). k ≥ 2 는 이번 학기 범위 밖 — 계약은 K=1 에서만 봉인된다.

### 2-2. FIRE transition (event)

`fire_event ≡ (prev_state = LOADED) ∧ (state = DEPLOYING)` (`env.py:313`).

- 조건 = `fire_cmd = 1` ∧ `LOADED` ∧ **`v_shot_soft ≥ θ_fire`** — **단일 gate (R2) 가 FSM
  내부에서 강제**된다. DEPLOYING/LOCKED/SPENT 에서 fire 는 no-op → 이중 차감 불가.
- fire 시 `CommitMeta` (t_fire, p_F, v_F, e_net, **net_center**, v_shot_at_commit) **동결**.
  해소는 이 동결값에 대해서만 이뤄지고 live 기하를 재계산하지 않는다.
- **capture 값도 fire 틱에 동결**된다 (`env.py:316-320`):
  `_pending_capture = (¬boxed_in) ∧ (v_shot_worst ≥ 1.0)` — worst-case (robust) judge.
- **F1 (주석-코드 불일치, 행동 무관)**: `env.py:305-308` 주석은 "frozen at the
  DEPLOYING->LOCKED transition" 이라고 쓰여 있으나 **코드는 fire_event 에서 동결**한다.
  본 조항이 정본이고, **결재 ③ 에 따라 주석을 수정**한다 (docs/09 예외 등록 문안 = §4-2).

#### θ_fire 는 학습 대상이 아니라 **admissibility constraint** 다 (결재 ⑥ — 봉인 문안)

> **Learned fire timing subject to a fixed admissibility gate.** The Bernoulli fire head
> selects firing **timing within the fixed θ_fire-admissible region**; it does not learn
> the gate. In states with `v_shot_soft < θ_fire` a FIRE command is a **no-op** no matter
> what the policy outputs.

- 이것은 **이번 학기 scope 결정**이다 (gate 자체를 학습하려면 FSM semantics 를 바꿔야 하고,
  그것은 B0 v4 재료).
- **어휘 금지 (결재 ⑥)**: "learned controller 가 기존 gate 의 censoring 을 해소했다 /
  보수적이던 영역을 회수했다" 류 주장 **전면 폐기**. 이 세계에서 그 영역은 정책이 도달할 수
  없다.
- gate conservatism 이 궁금하면 그것은 학습 arm 이 아니라 **forced-fire micro-arm** 이
  답한다 (외부 강제 발사 = 평가/probe 전용, docs/89 §4 — 학습 경로 투입 금지).
- 따라서 Δχ50 판독 분해 (§2-11) 의 `P(FIRE|χ)` 는 "정책이 admissible 영역 **안에서** 언제
  쏘기로 했는가" 이지 gate 이동이 아니다.

### 2-3. NET_CAPTURE predicate

**NET_CAPTURE ≡ CAPTURED ∧ contact = ∅** (기존 정의 승계, `mission_rollout.py:384`).

- `CAPTURED ≡ resolved ∧ fsm.last_capture is True` (`env.py:322-324`) —
  `resolved` = LOCKED 타이머 만료 틱.
- `contact` = 에피소드 동안 attacker 가 **어느 limiter 의 kill_radius 안에 든 적이 있는가**
  (틱마다 이동 **전** 상태로 집계, `mission_rollout.py:316-320`).
- contact 가 하나라도 있으면 라벨은 `CAPTURE_WITH_CONTACT` — 본 계약에서 이는
  **H_illegal** 로 계수한다 (§2-7, §2-9). "clean" 은 contact = 0 을 뜻한다.

#### N 의 권위 술어와 **세 개의 비권위 사본** (2026-09-13 발견 — §0 ④)

코드에는 "포획 성공" 을 뜻하는 술어가 **네 개** 있고 서로 다르다. B0 v3 는 그중 하나만
과학 지표의 권위 술어로 인정하고 나머지 셋의 지위를 명시한다.

| # | 위치 | 하는 일 | B0 v3 지위 |
|---|---|---|---|
| **권위** | `mission_rollout` label (`:384`) | CAPTURED ∧ **에피소드 누적** contact = ∅ | **N 의 정의. R2a/R2b 가 쓴 술어** |
| 사본 1 | `env_sys._outcome_label` (`:605-618`) | 같은 precedence 사슬이지만 contact 을 **종료 tick 에서만** 검사 | **N 판정에 사용 금지** — 초기 접촉 후 종료 tick 에 떨어져 있으면 NET_CAPTURE 로 읽는다 |
| 사본 2 | `RewardSpec.terminal` (`:196-211`) | **CAPTURE_WITH_CONTACT 에 NET_CAPTURE 와 같은 +b_net** (docs/66 r1 Q1 비준) | **supersede 확정 (결재 ④)** — hybrid mission 에서 유지 불가 |
| 사본 3 | `m4_env.label_rates` (`:169-187`) | `p_net` = NET_CAPTURE **+** CAPTURE_WITH_CONTACT | legacy 2층 지표 — **B0 v3 과학 지표 아님** |

- **왜 blocker 인가**: 사본 2 를 그대로 두고 MARL 을 돌리면 **정책은 illegal
  substitution 에 clean capture 와 똑같은 보상을 받는다** — §3.2/§3.3 이 구조로 막으려던
  바로 그 실패 모드를 reward 가 사준다. docs/89 §4 의 `r_illegal < 0` 요구와 정면 충돌.
  **가정이 아니라 현재 배선이다**: `train_m4.py:504-507` 이 `RewardSpec(..., enabled=True)`
  로 학습 env 를 만들고 있으므로 이 terminal 은 지금도 살아 있다.
- **docs/66 r1 Q1 이 전이되지 않는 이유**: 그 비준의 기준은 **파괴성** ("CWC 에 파괴 혼입
  경로 없음 → nondestructive utility class 로 동등") 이었다. hybrid mission 의 기준은
  파괴성이 아니라 **doctrine** (net 실패 전의 kinetic 접촉 = illegal substitution) 이다.
  기준이 다르므로 옛 비준이 자동 승계되지 않는다 — **명시적 supersede 가 필요**하다.
- **도달 경로 (이론이 아니라 실재)**: F-계약 `p_kill = 1.0` 에서 접촉은 보통 즉시
  HARD_KILL 이 되지만, **no-kinetic zone (`d_asset ≤ r_nk`) 안의 접촉은 veto** 되어
  limiter 도 소모되지 않고 kill 도 나지 않는다 (`env_sys.py:461-465`). 그 뒤 포획이
  성립하면 권위 술어는 CWC, 사본 1 은 NET_CAPTURE 로 갈린다. **vetoed contact 도
  doctrine 위반이므로 B0 v3 에서는 H_illegal 이다** (kill 이 없었다는 것과 무관).
- **결재 ④ 반영**: ① N 의 권위 술어 = 누적 contact 판 하나로 고정 ② 사본 2 는 hybrid
  mission 에 한해 supersede (실제 `r_illegal` 수치는 **training contract** 에서 봉인)
  ③ 사본 1·3 은 계약에 "비권위" 로 명기하고 과학 표에 절대 쓰지 않는다.

### 2-4. NET_SPENT · W_net · τ 원점 · coupling caveat

- **NET_SPENT 는 실재하며 직접 읽는다** (docs/89 위험표 2번 **해소**): FSM `SPENT`
  (deterministic 상태 전이) + `env_sys.net_spent` / `net_spent_step`
  (`env_sys.py:398-416`). **신규 predictive 판정기 제작 없음** — 고정 `T_valid` 를 world
  contract 파라미터로 만들지 않는다는 원칙 그대로.
- **표기 관계 (좁힘)**: NET_FAIL 은 호환용 outcome/event 이름이며 **정상적 미포획
  shot-exhaustion 경로에서 NET_SPENT 로 trigger** 된다 (NET_SPENT ⇒ NET_FAIL_shot).
  illegal contact · crash · out-of-bounds 는 NET_SPENT 가 아니라 H_illegal / F_other
  경로다 — **모든 실패 ≡ NET_SPENT 아님**.
- **W_net 측정 규약 → vacuous 판정으로 대체**: 포획은 **fire 시점 동결 단일 predicate**
  이므로 "t_eff 이후 포획 가능 상태가 유지되는 시간" 이라는 물리가 **이 세계에 없다**.
  t_eff → t_spent 간격은 τ_lock 상수이지만 그 동안 유지되는 것은 포획 능력이 아니라
  **outcome 적용 대기 + 침투 race** 뿐이다. 따라서 **ω_net = W_net/τ₀ 는 governing
  후보에서 제외**하고 상수값만 기록한다. net persistence 물리를 새로 구현하면 그때
  **B0 v4 재료**.
- **τ 원점**: t_obs = FIRE 판단에 실제 사용된 최신 관측 시각. 이 세계에서는 t_obs ≡ t_fire
  (§1.3) → τ_real ≡ τ_deploy. **policy 의 의도적 WAIT 는 τ 가 아니다** — 기다린 시간은
  latency 에 산입되지 않는다 (§3 t6 가 이것을 잠근다).
- **coupling caveat (봉인)**: dt_phys = Δt_dec = 0.05 s coupled 고정. q_dec 교란은 행동
  빈도 · 물리 적분 해상도 · predicate 샘플링 해상도를 동시에 움직이므로 §1.2 해석 금지
  ① 이 그대로 적용된다.

### 2-5. NET_FAIL 후 물리 episode continuation

- **비준 F-계약이 이미 이 세계다**: `miss_terminates=False` 가 **spent-fail 종료만**
  억제하고 (`env_sys.py:398-416`) 에피소드를 계속 굴린다. captured · penetrated ·
  hard_kill 종료는 **절대 억제하지 않는다**. 지평선 절단은 래퍼가 낸다.
- 첫 억제 시점에 `net_spent = True`, `net_spent_step = _step_i` 가 **한 번만** 기록된다 →
  이것이 KINETIC 전환의 기계적 원점이다.
- 이후 limiter 는 scripted PN fallback 이 takeover 한다 (§2-8).

### 2-6. NET_FAIL 에서의 RL-credit termination

> **NET_FAIL 은 물리 mission 의 종료가 아니라 RL credit 의 종료다.**

- **MAPPO rollout / GAE / return 은 NET_FAIL 에서 terminal 처리 (cut)**. "kinetic reward 0"
  만으로는 부족하다 — discount · time penalty · value bootstrap 이 앞단 return 으로 새는
  경로를 차단해야 한다.
- **구현 규칙**: training wrapper 가 `net_spent` 를 terminal 로 반환하고 **즉시 reset**.
  PN fallback continuation 은 **system-evaluation path / sidecar 에서만** 같은 상태를 받아
  계속 실행한다 (training vector env 안에서 물리 episode 를 끝까지 유지하지 않는다).
- **중요 (구현 함정)**: 이 cut 을 `SystemSpec(miss_terminates=True)` 로 구현하면 **안 된다**
  — system flag 가 달라져 train/eval manifest hash 가 갈리고 §1.5 parity 가 깨진다
  (`manifest_mismatch` = `["system.miss_terminates"]`). cut 은 **training wrapper 계층**에서
  하고 world flags 는 F-계약 그대로 둔다. §3 t8 이 이것을 잠근다.
- **fire action 의 학습 신호**: fire action 의 policy gradient 에는 **NET_FAIL 이전의
  net-task return 만** 사용한다. post-fail kinetic outcome 은 reward/value target 에
  포함하지 않는다.

### 2-7. phase 별 contact semantics (C_illegal 정의)

- **contact 술어** (단일 정의원): 틱마다 이동 **전** 상태에서 `‖p_att − p_lim_i‖ ≤
  kill_radius` (`env.py:360` 의 `limiter_loss` 와 동일 술어).
- **C_illegal ≡ contact ∧ m ∈ {NET_PRE, NET_PENDING}** → **irreversible failure latch**
  (결재 ⑤). 최초 성립 시 `C_illegal = 1` 을 latch 하고, **그 뒤에 무슨 일이 일어나도
  science outcome 은 H_illegal 로 확정**된다. 명시적 음수 terminal reward `r_illegal < 0`
  (크기 규칙은 training contract 에서 봉인: `|r_illegal| >` 남은 episode 에서 절약 가능한
  최대 time-penalty 합 — "어차피 못 잡으니 충돌로 빨리 끝내자" 가 유리해지지 않게).

#### ⑤ latch 문안 + 왜 "terminal failure" 가 아닌가 (코드 사실)

> **Irreversible illegal-substitution latch.** The first body contact occurring in
> NET_PRE or NET_PENDING sets `C_illegal = 1`. The episode's science outcome is
> **H_illegal** regardless of any subsequent capture, and no later capture may be
> restored as success or reward. The physical rollout continues wherever the implemented
> world continues it — the latch is an **outcome/credit rule, not a termination rule**.

현행 세계에서 pre/pending contact 의 **종료 여부는 영역에 따라 갈린다**
(`env_sys._resolve_contacts`) — 그래서 계약이 "즉시 terminal" 이라고 적으면 거짓이 된다:

| 조건 | 코드 거동 | 종료? |
|---|---|---|
| `d_asset > r_nk` (NK zone 밖) | 소모·retire → Bernoulli(`p_kill`=1.0) → `KILL` → `hard_kill=True` | **종료 (HARD_KILL)** |
| `d_asset ≤ r_nk` (NK zone 안) | **`VETO_NO_KINETIC`** — 기폭 보류, limiter 미소모, 재접촉 시 재평가 | **종료 안 함** → 이후 capture 가능 → CWC |

- **용어 주의 (docs/57 감사 판정 B)**: 여기서 "contact" 는 물리 충돌이 아니라 **근접
  kinetic engagement opportunity** 다 (kill_radius = 폭발형 요격의 실행 반경). NK veto 는
  **기폭 보류**이지 접촉 부재가 아니다 — 그래서 doctrine 위반으로 latch 하는 것이 맞다.
- **latch 는 새 구현이 거의 필요 없다**: 권위 술어 (§2-3) 의 **에피소드 누적 contact = ∅**
  가 이미 정확히 이 latch 다. 필요한 것은 ① 그 집합을 **phase 로 조건화**하고 ② 4분류
  집계기가 latch 를 읽게 하는 것뿐.
- **legitimate ≡ contact ∧ m = KINETIC** → 페널티가 아니라 kinetic success predicate 의
  일부 (§2-8).
- **정합 확인**: N 은 해소 틱에서만 성립하고 그 틱에 에피소드가 끝나므로 N 과 KINETIC 은
  시간상 상호배타다. 따라서 현행 "에피소드 전체 contact 집합" 은 N 라벨에 대해서는
  phase-scoped 정의와 **동치**다. 그러나 **H_illegal vs H_fb 계수는 접촉 틱의 mode 로
  갈린다** — 이 구분은 §2-12 ③ off-by-one 규칙과 함께 집계기에서 구현해야 한다.

### 2-8. KINETIC fallback controller 와 success predicate

- 이번 학기 KINETIC = **scripted PN fallback** (환경 takeover). π_kin 학습 · staged
  failure-state training · joint hybrid fine-tuning 은 **이연**.
- 호칭 = **reference fallback (baseline fallback)**. "보수적 하한" 표현은 learned kinetic 이
  PN 을 일관되게 상회함을 보인 뒤에만 격상한다.
- **kinetic 성립 사슬** (`env_sys.py:453-475`, 신설 없음): commit → **τ_kill (= q_kill·τ₀
  = 3 틱) 지연** → **no-kinetic zone 거부권** (해소 시점 `d_asset ≤ r_nk` → `VETO_NO_KINETIC`,
  limiter 미소모) → 기하 검사 (`GEOM_FAIL`) → **Bernoulli(p_kill = 1.0)** → `KILL` ⇒
  `hard_kill = True` ⇒ 종료.
- **success predicate**: `H_fb ≡ HARD_KILL ∧ (hard_kill 성립 틱의 m = KINETIC)`.
  같은 사슬이 m ∈ {NET_PRE, NET_PENDING} 에서 성립하면 **H_illegal** 이다 — 같은 물리,
  다른 계수.

### 2-9. 과학 / 시스템 지표 계수 규약 분리

**Outcome 4분류 (상호배타 · 완전 partition — episode 당 정확히 1 bin)**:
**N** = clean net capture / **H_fb** = post-NET_FAIL legitimate kinetic neutralization /
**H_illegal** = NET_PRE·NET_PENDING 중 kinetic contact / **F_other** = timeout · crash ·
out-of-bounds 등 기타 실패.

| 층 | 정의 | 계수 규약 |
|---|---|---|
| **과학** | χ50^net(η, λ) | N = 1 / H_illegal = 0 / **H_fb = 0** / 기권 = 0 (**censoring 보정 금지** — 안 쏜 것은 실패) |
| **시스템** | **P_U = P_N + P_{H_fb}** (H_illegal 불포함) | legitimate fallback 만 성공 포함. P(KIN\|NET_FAIL) 은 reference fallback 값으로 보고 |
| **safety** | P_{H_illegal} | 별도 doctrine-violation rate (성공 지표 아님) |

- **기존 `HARD_KILL` 계수는 반드시 phase 로 분리 재집계**한다 — H_illegal 이 시스템 성공으로
  새면 substitution 을 다시 사게 된다.
- **CWC 보상 supersede (결재 ④, 봉인 문안)**:
  > For the hybrid mission, the ratified `CAPTURE_WITH_CONTACT = +b_net` terminal
  > (docs/66 r1 Q1) is **superseded**. CWC and any illegal pre-net contact receive no
  > clean-capture reward; the magnitude of `r_illegal` is sealed in the training contract.
- **P_{H_illegal} 의 진단 분해 (의무)**: 같은 H_illegal 이라도 **① 실제 KILL 로 끝난 것**과
  **② NK veto 로 기폭이 보류된 것** (`veto_events`) 은 운용상 전혀 다른 사건이다. 합산
  비율만 보고하지 말고 **둘로 쪼개 기록**한다 — doctrine-violation rate 의 해석이 달라진다.
- gate 의 shot-quality 모델 P(capture|fire) 추정은 **별도 문제** (forced-exploration fire
  잔존 확률 or randomized probe + propensity weighting) — 과학 지표와 혼용 금지.
- 학습 objective 로 두 층을 **합산 금지**.

### 2-10. THREAT bracket · 유효 부분격자 · stratification 목록

- THREAT bracket = a ∈ [11, 78] · v ∈ [8, 30] (draw 계약). 평가 격자 셀은 **전 구현 공통
  유효 부분격자 내부**로 제한한다 (docs/87 §4 규율 승계). bracket 밖 pin 이 필요해지면
  "본 캠페인은 pin 계약이며 범위 X 를 새로 선언한다" 를 **결과 열람 전** 봉인 문서에 명시.
  "bracket 이탈 없음 assert" 문구는 폐기됐다.
- **stratification / randomization 대상 = (χ, η, λ, A) 뿐** — §1.4 층1 종료 조항에 의해
  **추가 물리 좌표 없음**. 이 목록은 봉인으로 닫히며, 결과를 본 뒤 축을 추가하지 않는다.
- 평가 격자 (고정 (χ, η, λ, A) grid + paired CRN) 의 **구체 셀 목록은 봉인 payload 의
  일부**이며, 학습 arm 실행 **전에** 확정한다. 훈련 sampler 분포와 **완전 분리**.
- **평가 집합은 둘이다 (봉인)**:
  | 집합 | 용도 | 규칙 |
  |---|---|---|
  | **primary grid** — 신규 고정 (χ, η, λ, A) 격자 | §2-11 "경계를 밀었다" 판정 | 봉인 payload |
  | **secondary = R2b exact `S_C` replay set** | **R_rec 전용** (§2-13) + C benchmark 직접 연결 | R2b 봉인 (`b0_hash cba024d7ee3d9f61`) 의 S_C 를 그대로 재생 — 새로 뽑지 않는다 |

  비용이 작고 (S_C = 셀당 100 시나리오) C arm 과 직접 연결되므로 논문에서도 유용하다.
  두 집합의 수치를 **섞어서 보고하지 않는다**.
- actor 에 scripted attacker ID (A1/A2/A3) **미제공** (전 arm).

#### 2-10a. 후보 평가 격자 (**제안 — 봉인 전 확정 필요**)

R2a Stage 3 구조를 그대로 승계한다. **재구성이 아니라 인용**이다 —
`artifacts/r2a/stage3_protocol.json` 의 `cells_rule` 이 이미
*"per eta row and slice: two micro-grid (0.02) points bracketing that slice's chi50"*,
즉 **nearest inside + nearest outside** 다.

- **행 정의**: (η, λ) 하나가 한 행. η ∈ {2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9} (7) ×
  λ ∈ {**4.644** (slice 0), **3.574** (slice 2)} (2) → **G = 14** — R2b 판정 형식
  (12/14 · 5/7) 을 **수치까지 그대로** 재사용할 수 있다.

| λ | η | R2a χ50 | nearest inside | nearest outside | outer anchor 1 | outer anchor 2 | a 범위 (in…OA2) | v | bracket 유효 |
|---|---|---|---|---|---|---|---|---|---|
| 4.644 | 2.1 | 0.6049 | 0.60 | 0.62 | 0.66 | 0.70 | 23.6…27.5 | 12.39 | ✅ |
| 4.644 | 2.4 | 0.5867 | 0.58 | 0.60 | 0.64 | 0.68 | 22.8…26.7 | 14.16 | ✅ |
| 4.644 | 2.7 | 0.5769 | 0.56 | 0.58 | 0.62 | 0.66 | 22.0…26.0 | 15.93 | ✅ |
| 4.644 | 3.0 | 0.5680 | 0.56 | 0.58 | 0.62 | 0.66 | 22.0…26.0 | 17.70 | ✅ |
| 4.644 | 3.3 | 0.5417 | 0.54 | 0.56 | 0.60 | 0.64 | 21.2…25.2 | 19.47 | ✅ |
| 4.644 | 3.6 | 0.5382 | 0.52 | 0.54 | 0.58 | 0.62 | 20.5…24.4 | 21.24 | ✅ |
| 4.644 | 3.9 | 0.5250 | 0.52 | 0.54 | 0.58 | 0.62 | 20.5…24.4 | 23.01 | ✅ |
| 3.574 | 2.1 | 0.5445 | 0.54 | 0.56 | 0.60 | 0.64 | 21.2…25.2 | 12.39 | ✅ |
| 3.574 | 2.4 | 0.5460 | 0.54 | 0.56 | 0.60 | 0.64 | 21.2…25.2 | 14.16 | ✅ |
| 3.574 | 2.7 | 0.5014 | 0.50 | 0.52 | 0.56 | 0.60 | 19.7…23.6 | 15.93 | ✅ |
| 3.574 | 3.0 | 0.5092 | 0.50 | 0.52 | 0.56 | 0.60 | 19.7…23.6 | 17.70 | ✅ |
| 3.574 | 3.3 | 0.4763 | 0.46 | 0.48 | 0.52 | 0.56 | 18.1…22.0 | 19.47 | ✅ |
| 3.574 | 3.6 | 0.4529 | 0.44 | 0.46 | 0.50 | 0.54 | 17.3…21.2 | 21.24 | ✅ |
| 3.574 | 3.9 | 0.4394 | 0.42 | 0.44 | 0.48 | 0.52 | 16.5…20.5 | 23.01 | ✅ |

(inside/outside 방향: χ = aτ₀²/2ρ 이므로 **χ↑ = 공격자 기동성↑ = 포획 난이도↑** → χ50
**아래**가 inside. χ50 출처: λ=4.644 는 `stage2_readout` (n=4800, confirmatory),
λ=3.574 는 `scout_l2_envelope` (n=480, **exploratory scout**).)

**격자 설계에서 확인된 사실 4가지**

1. **χ50 는 14 행 어디에서도 0.02 격자 위에 놓이지 않는다 (0/14)** — 리뷰의 우려가 실측으로
   확인됐다. 따라서 "χ50 자체를 셀로" 는 불가능하고 **nearest inside / nearest outside** 가
   유일하게 기계적·재현 가능한 규칙이다 (그리고 그것이 이미 R2a 가 한 일이다).
2. **THREAT bracket 은 이 구간에서 구속하지 않는다**: a ∈ [16.5, 27.5] vs 허용 [11, 78],
   v ∈ [12.4, 23.0] vs [8, 30]. χ50+0.10 까지 밀어도 여유가 크다 → **공통 유효 부분격자는
   outer anchor 를 제약하지 않는다**. (구속은 bracket 이 아니라 예산이다.)
3. **2점 bracket 은 이동을 *탐지* 할 수는 있어도 *측정* 할 수 없다.** 학습 arm 이 경계를
   0.02 넘게 밀면 두 셀이 모두 inside (p̂→1) 가 되어 **χ50^learned 가 격자 위에서 censored**
   된다. Δχ50 이 estimand 인 이상 **outer anchor 는 선택이 아니라 필수**다.
4. **역방향도 같다**: docs/89 는 **B-3 (geometric objective) 이 illegal substitution 으로
   붕괴할 수 있다**고 명시한다. 그 경우 χ50^B-3 가 격자 **아래로** 벗어나 역시 censored →
   reward 축 Δχ50 (B-3 vs B-4) 가 보고 불가. **inner anchor 1점**을 대칭으로 둔다.

#### 확정 사양 (**결재 ⑦ — 2026-09-13**)

> **G = 14 · base 4 χ points/row · n = 300 / cell / seed**

| 축 | 값 |
|---|---|
| 행 | λ ∈ {4.644, 3.574} × η ∈ {2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9} = **14** |
| base χ (행마다) | **{χ_lo − 0.04, χ_lo, χ_hi, χ_hi + 0.04}** — χ_lo/χ_hi 는 위 표의 nearest inside/outside (R2a protocol 그대로) |
| n | **300 / cell / seed** |
| arms × seeds | 3 × 3, **paired CRN** |
| **A** | **A2-nominal 단일** |
| secondary | R2b exact `S_C` replay (R_rec 전용, §2-13) — primary 와 **혼합 금지** |

- **왜 5점이 아니라 4점인가**: χ50 이 lo/hi 사이에 있으므로 4점은 중심 기준 ≈
  **{−0.05, −0.01, +0.01, +0.05} 의 대칭 support** 가 된다. 반면 바깥쪽에 한 점을 더 얹은
  5점 안은 **positive shift 쪽에 설계를 기울이는 것** — "학습은 좋아질 것" 이라는 기대를
  평가 설계에 심는 셈이다. B-3 붕괴 가능성을 이미 인정한 이상 대칭이 맞다. 범위 부족은
  점을 미리 더 두는 것이 아니라 **확장 규칙**으로 푼다.
- **왜 n = 300 인가**: 다섯 번째 점보다 **각 seed 의 χ50 추정 정밀도**를 올리는 편이
  seed-majority 판정 (§2-11) 에 더 값어치 있다. Δχ50 이 primary estimand 가 된 이상
  200 보다 300 이 안정적인 절충.
- **A2-nominal 단일의 대가 (반드시 조건화)**: primary claim 은
  **χ50^net(η, λ | A2-nominal)** 로 쓴다. A-family robustness 는 **W10 frozen-policy
  arm (층3)** 으로 분리하며 **primary 와 pooling 금지**.

#### Boundary-extension rule (**봉인 문안 — censoring 만이 trigger**)

> **Boundary-extension rule.** Base grid 는 4 점/row. 한 **arm × seed** 의 isotonic fit
> 에서 p = 0.5 crossing 이 sampled range **밖으로 censored** 되면, 그 방향으로 **2 lattice
> steps = 0.04** 확장한다 (R2a 규칙과 동일 단위). 확장 셀은 비교 가능성을 위해 해당 row 의
> **모든 arm × 모든 seed** 에 **동일 CRN** 으로 추가한다. 한 방향 **최대 2 회** 확장 후에도
> censored 이면 더 추격하지 않고 **one-sided bound 로 보고**한다.

- upper: `hi+0.04 → hi+0.08 → hi+0.12` / lower: `lo−0.04 → lo−0.08 → lo−0.12`.
- **trigger 는 오직 censoring 이다** — "효과가 커 보여서" 확장하는 것은 **adaptive
  cherry-picking** 이므로 금지. 이 한 문장이 확장 규칙을 사전등록으로 만든다.
- **한 arm × seed 라도 censored 이면 row 전체를 확장**한다. seed 별 χ50 을 판정에 쓰는데
  한 seed 의 경계가 잘려 있으면 seed-majority 자체가 불완전해지기 때문.

#### λ = 3.574 앵커의 지위 (**결재 ⑦-b — 유지, provenance 명기**)

> λ = 3.574 base grid centering uses the **pre-existing exploratory scout estimate**; all
> learned-arm comparisons on this grid are **fresh confirmatory evaluations**. The scout
> estimate is **not itself re-promoted as confirmatory evidence**.

두 slice 모두 유지한다 (강등하면 λ 축 주장이 사라진다). scout 앵커가 다소 어긋나 있어도
**확장 규칙이 경계 잘림 위험을 흡수**한다. 표의 provenance 차이 (n=4800 confirmatory vs
n=480 exploratory) 는 그대로 남긴다.

#### 예산 (앵커 1.49 s/ep)

| 구성 | episodes | serial | 8-shard |
|---|---|---|---|
| **base** (14 × 4 × 3 arm × 3 seed × 300) | **151,200** | **62.6 h** | **7.8 h** |
| 확장 1 step (전 14 row 가정) | +37,800 | +15.6 h | +2.0 h |
| worst case (양방향 2 회 전 row) | 302,400 | 125.2 h | 15.7 h |
| secondary `S_C` replay (R_rec) | 25,200 | 10.4 h | 1.3 h |

실현 예상 = base + 일부 row 1 step ≈ **170 k ep ≈ 70 h serial (≈ 9 h / 8 shard)**.

### 2-11. "경계를 밀었다" 판정 규칙 (행 / slice / 전역 3조건)

R2b P1 규칙의 **형식을 승계**한다 (수치는 격자 확정 시 채우고 봉인):

> 격자가 G 행 (η × χ 밴드) × 2 λ slice 일 때 —
> ① **행**: ≥ ⌈6G/7⌉ 행에서 paired Δ 의 점추정이 양 ∧
> ② **slice**: 각 λ slice 안에서 ≥ ⌈5·(G/2)/7⌉ 행이 양 ∧
> ③ **전역**: equal-weight global paired Δ 의 **CI95 하한 > 0** (scenario-paired
> bootstrap, B = 4000).
> (R2b 는 G = 14 에서 ①12/14 ②5/7 ③CI 로 실행됐다.)

- **Δ 의 정의**: 같은 (χ, η, λ) 셀 · 같은 CRN scenario · 같은 success semantics
  (**N only**) 에서의 arm 간 차이. reward 축 = B-3 vs B-4, role 축 = B-4 vs B-5.
- **조건화 (결재 ⑦)**: primary 는 A2-nominal 단일이므로 claim 은 항상
  **χ50^net(η, λ | A2-nominal)** 로 쓴다. A-family robustness 는 **층3 (W10) frontier
  frozen-policy arm** 으로 분리하며 primary 와 **pooling 금지**.
- **행 = (η, λ) 하나**, G = 14 (§2-10a). 따라서 ①②의 수치는 R2b 와 동일하게
  **12/14 · 각 slice 5/7** 이 된다.

#### Seed-robust boundary-shift rule (§0 결재 ② — 봉인 문안)

> 각 (η, λ) 행/slice 의 **positive 판정은 arm 당 독립 학습 seed 들의 다수결** (3 seed 면
> **≥ 2/3**) 을 요구한다. 각 seed **내부**에서는 고정 evaluation grid 와 paired CRN 으로
> **동일한 estimand** 를 계산한다. 전역 효과의 uncertainty 는 **seed 를 독립 반복 단위로
> 보존하는 paired hierarchical/clustered procedure** 로 계산한다. **개별 seed 별 값은 전부
> 보고한다.**

최종 판정 = **행/slice seed-majority ∧ global positive effect**.

**연산 순서 (봉인 — 중첩 해소)**: slice 단계에서 seed 다수결을 **다시** 하지 않는다.
seed 다수결은 **행 단계에서 한 번만** 적용하고, slice/전역 gate 는 그 결과 flag 위에서 센다.

1. **seed 별**로 scenario-paired **행 Δ** 를 계산한다 (같은 셀 · 같은 CRN · N only).
2. 한 행이 **≥ 2/3 seed 에서 Δ > 0** 이면 그 행을 **`row-positive`** 로 flag 한다.
3. 이 **seed-robust `row-positive` flag** 위에서 ①행 (⌈6G/7⌉) · ②slice (각 λ slice 안
   ⌈5·(G/2)/7⌉) gate 를 센다.
4. **전역 효과는 별도로** seed-preserving hierarchical paired summary 로 낸다 (③).

- **CI 의 지위 (봉인 caveat)**: cluster 가 3 개뿐이라 asymptotic calibration 이 약하다.
  **"seed-preserving hierarchical paired CI"** 라 부르고, 정밀한 95% frequentist
  guarantee 처럼 서술하지 않는다. 전역 CI 는 **보조 증거**이며 실제 robustness 는
  **2/3 seed consistency + effect size + paired scenario evidence 의 결합**으로 읽는다.
- ①안 (seed-pooled 점추정으로 행/slice 판정) 은 **기각** — 기각 사유는 §0 참조.
- **판독 분해 상시 로그**: 셀별 `P(FIRE|χ)` 와 `P(N|FIRE, χ)` 를 전 arm 기록 — Δχ50 이
  shaping 개선인지 발사 판단 개선인지 분해 (χ50 은 controller+gate 체계의 달성 경계).
- 이 규칙은 **학습 결과 열람 전** 봉인된다. 사후 수정 금지.

### 2-12. same-tick event precedence

| # | 동시 발생 | 판정 | 근거 |
|---|---|---|---|
| ① | **raw CAPTURED resolution** ∧ body contact | **H_illegal 우선** | clean capture 정의 = contact 0 이므로 capture 실패. ("NET_CAPTURE ∧ contact" 는 정의상 동시 참이 불가능한 표현이라 폐기 — 판정 대상은 **라벨 이전의 해소 event** 다) |
| ② | NET_SPENT ∧ 같은 틱 capture | **N 우선** | 해소 틱의 capture 는 성립한 포획 |
| ③ | NET_SPENT 확정 틱의 limiter contact | **KINETIC 은 다음 control tick 부터** | 마지막 유효 틱 contact 이 legitimate 으로 오분류되는 off-by-one 차단 (δ_switch 는 과학 지표 무관, P_U 에만 존재) |
| **④** | **capture 해소 ∧ 침투 동시** | **CAPTURE 우선 — sealed discrete-time tie rule** (§0 결재 ①) | `mission_rollout.py:361-372` 라벨 사슬 `hard_kill → captured → penetrated`; probe `_Driver` 동일 순서 |

**④ 의 세계 사실 (F2 race — 결재와 무관하게 참)**: capture 는 fire 에서 동결되지만 적용은
τ_deploy + τ_lock 뒤 해소 틱이다. 그 **pending 창 동안 `penetrated` 는 매 틱 검사**되고
`captured` 는 구조적으로 False 이므로 **침투가 자명하게 이긴다**. 즉 τ₀ 는 capture viability
와 **event-order competition** 양쪽에 작용한다 (docs/91 v2.1 §7.2). ④ 는 그 창의 **마지막
틱** 에서의 동률 처리만 정한다.

#### ④ 봉인 문안 (결재 ① — 이 문장으로 계약에 박는다)

> **Same-tick capture–penetration precedence.** During NET_PENDING, penetration occurring
> **before** the capture-resolution tick terminates the episode as PENETRATED. If the
> delayed capture resolves on the **same discrete tick** on which the penetration
> predicate becomes true, **CAPTURE takes precedence**. This is a **sealed discrete-time
> tie rule**; it does **not** claim continuous-time physical ordering.

- **동시발생 counter (의무)**: `capture_penetration_same_tick` 를 상시 로그한다.
  **이 빈도로 precedence 를 결정하지 않는다** (봉인은 지금 끝났다). 나중에 빈도가 크게
  나오면 그때 할 일은 규칙을 바꾸는 것이 아니라 **dt-sensitivity /
  continuous-event-resolution 문제로 층3 robustness 에서 공격**하는 것이다.
- 참고: `hard_kill` 이 사슬 최상단이므로 hard_kill ∧ captured 동시 = HARD_KILL 이며, 이는
  ① (NET_PENDING 중 contact → H_illegal) 과 정합한다.
- `env_sys` 의 "침투 우선" 조항은 **sham-net (`capture_terminates=False`) 전용**이며 본
  세계와 무관하다 (`env_sys.py:417-437`). 본 세계는 `capture_terminates=True`.

### 2-13. 학습 평가 부가 지표 R_rec (r4 봉인 승계)

**R_rec = (p_learned − p_A) / (p_C − p_A)** — 같은 S_C · 같은 world · 같은 success
semantics (**NET_CAPTURE only**) 에서만 정의된다.

- p_C 는 **upper bound 가 아니므로** R_rec > 1 이 가능하다 —
  **"fraction of upper bound recovered" 명명 금지**.
- 판정 규칙 (§2-11) 과 **별개의 descriptive 부가 지표**다. 게이트에 넣지 않는다.
- **계산 가능 조건 (봉인 — 초안 검토 라운드 지적)**: R_rec 은 **같은 S_C** 에서만 정의되는데
  §2-10 의 평가 격자는 새로 정한다 → 그대로 두면 **R_rec 은 계산 불가능**하다. 따라서
  **R2b 의 exact S_C 를 secondary fixed replay set 으로 유지**하고 학습 정책을 거기서도
  평가한다 (§2-10). primary grid 와 **분리된 집합**이며, R_rec 은 **이 집합에서만** 보고한다.
  primary grid 수치로 R_rec 을 계산하는 것은 금지.

---

## §3. Contract tests (봉인 동반 — sensitivity test 아님)

목적은 "B0 world 가 **코드에 실재하는지**" 확인이다. 서버 campaign 을 대체하는 것이 아니라,
**서버 campaign 이 필요 없는 종류의 확인**이다. 전부 로컬 · 초 단위.

| # | 테스트 | 잠그는 것 | 비고 |
|---|---|---|---|
| t1 | `q_dec = dt/τ_deploy = 1/6` | §1.2 pinned conditioning | 기존 assert (`r2a_stage1.py:329`) 를 **manifest 수준으로 승격** |
| t2 | `q_race = τ_lock/τ_deploy = 1/3` ∧ `q_kill = τ_kill/τ_deploy = 1/2` | §1.2 contract-fixed ratios | manifest `extra_cfg` 에서 직접 읽는다 |
| t3 | true-state observation contract | §1.3 noiseless · zero-latency | 같은 상태 → 같은 obs · obs 가 참값과 일치 · 잡음/지연 키 부재 |
| t4 | NET_SPENT path | §2-4, §2-5 | FSM SPENT ⇒ `net_spent=True` ∧ `net_spent_step` 기록 ∧ F-계약에서 **미종료** |
| t5 | same-tick precedence | §2-12 ④ 봉인 문안 | 해소 틱 capture+침투 동시 구성 → 라벨 = CAPTURED 고정 |
| t6 | **WAIT ≠ τ** | §2-4 τ 원점 | 발사를 k 틱 늦춰도 t_fire→해소 간격은 τ_deploy+τ_lock 불변 |
| t7 | F1 hygiene | §2-2 주석-코드 정합 | 결재 ③: **comment-only diff** 확인 + 기존 regression/gate green |
| t8 | **train/eval manifest parity** | §1.5 · §2-6 구현 함정 | RL-credit cut 이 world flags 를 바꾸지 않음 (`manifest_mismatch == []`) |
| **t9** | **θ_fire = admissibility constraint** (결재 ⑥) | §2-2 | gate 아래에서 FIRE 는 **no-op** — fire_event 없음 · k 불변 · LOADED 유지 |
| **t10** | **pre-net contact 의 영역 의존 종료** (결재 ⑤ 근거 표) | §2-7 | NK 안 → `VETO_NO_KINETIC`·미소모·미종료 / NK 밖 → `KILL`·소모·`hard_kill` |

**구현 완료 (2026-09-13)** = `tests/test_b0_v3_contract.py` — **12 passed / 8.2 s**
(torch-free, 캠페인 세계 R-ref τ=0.30·dt=0.05 에서 실행. M2 기본값 세계가 아니다).

실측된 세계 (t4/t6 의 비-공허성 증거, force_commit 강제 발사 · hold limiter):

| 구성 | fire | spent | handoff | end | label | steps |
|---|---|---|---|---|---|---|
| F-계약, `force_commit_step=1` | 0 | **8** | 8 | 46 | PENETRATED | 47 |
| F-계약, `force_commit_step=5` | 4 | **12** | 12 | 48 | PENETRATED | 49 |
| legacy (`miss_terminates=True`) | 0 | 8 | — | **8** | **SPENT_FAIL** | 9 |

- **pending 창 = 8 틱** = (τ_deploy + τ_lock)/dt = (0.30+0.10)/0.05 — §2-1 의 수치가
  실측으로 확인됨. 발사를 4 틱 늦춰도 간격은 8 틱 불변 (**WAIT ≠ τ**).
- F-계약은 소진 스텝에서 종료하지 않고 47~49 스텝까지 계속된다 (§2-5 continuation 실재).
- **t7 (F1) 완료**: `env.py` 주석 수정 — `git diff` 상 **non-comment 변경 줄 0** 확인
  (comment-only diff) ✅ · docs/09 §13 에 **비준 예외 2** 등록 ✅ · **전체 regression** ✅
  (아래).
- **전체 regression (결재 ③ 둘째 검증) — 0 failed**: 봉인 직전 단일 완전 실행
  **770 passed · 65 skipped · 0 failed** (29.5 분). skip 수는 torch 가용성에 따른 기지
  변동 (conftest 가 설명하는 stub 경로; 로컬은 torch 미설치 모드).
  그 전 실행에서 유일한 실패였던 `test_results_lineage.py::test_every_entry_classified`
  는 봉인 전에 **해소**됐다 (→ 재실행 64 passed).
  - 그 실패는 **이번 세션과 무관한 기존 RED** 였다: `results/viz_r2b_c_pick{0,1,2}.json`
    이 커밋 **cd74b63 (2026-09-07)** 에서 `results/README.md` 계보 표 갱신 없이 들어왔다
    (가드가 설계대로 작동). 조치 = **`R2-CAMPAIGN` 상태 신설 + `viz_r2b_*` 행 추가**
    (README + 테스트 패턴 동시). **기존 4종에 넣지 않은 이유**: RETIRED/LEGACY-REGIME 은
    사실과 다르고, NEXT-BRANCH 는 "confirmatory 사용 금지" 를 달고 있어 C047~C049 의
    지위와 충돌하며, CANONICAL 은 정의가 v0 (Phase III) 라인이다 — 표가 R2 캠페인보다
    먼저 쓰여 생긴 빈칸이었다. **한 줄 metadata 가 아니라 상태 어휘 추가**이므로 되돌리기
    쉬운 형태로 최소 변경했다.
  - 리팩터를 직접 덮는 `test_rollout_core_parity` · `test_terminal_truth_table` 는 **PASS**.
  - 1차 실행이 `-x` 로 lineage 에서 멈춰 19 파일이 미실행이었고, 별도 실행으로 채웠다.
- **부수 정리 (t5 가 요구한 최소 변경)**: 라벨 사슬이 `mission_rollout.run_episode` 와
  `recoverability_probe._Driver` 에 **복제**돼 있었다 → `mission_rollout.terminal_label(fi)`
  **단일 정의원**으로 추출하고 두 호출부를 모두 경유시켰다 (bit-identical). 복제가 남아
  있으면 §2-12 ④ 를 봉인해도 한쪽만 바뀌는 사고가 가능하다.

---

## §4. 봉인 절차

1. ~~§0 결재 ①②③ 수령~~ → **완료 (2026-09-13)**, 본 문서에 반영됨.
2. §3 contract tests 작성 → 전부 PASS (실패 시 **봉인 연기** — 세계 서술이 틀린 것이므로
   문서를 고친다, 테스트를 고치지 않는다).

   **2-2. F1 hygiene (결재 ③) — docs/09 예외 등록 문안**:
   > `env.py` L305–308 comment-only hygiene correction: capture predicate is frozen at
   > FIRE, not at DEPLOYING→LOCKED. **No executable code or runtime semantics changed**;
   > frozen-file exception recorded under docs/09.

   동반 검증 딱 2개: ① diff 가 **comment-only** 인지 확인 ② 기존 regression/gate 전부 green.
   ("byte 단위 코드 무변경" 이 아니라 **executable semantics unchanged** 로 기록한다.)
3. **[봉인 전 남은 유일한 설계 작업]** §2-10 평가 격자 셀 목록 · §2-11 G 값 확정 →
   payload 에 삽입. 재료 = R2a 경계 (η 별 χ50) + 공통 유효 부분격자 + λ 2 slice + A.
   **학습 arm 실행 전에** 확정돼야 하며, 이것만 정해지면 봉인 payload 가 닫힌다.
4. ✅ `shepherd/scripts/b0_v3.py` → `artifacts/b0/b0_v3_world_contract.json` 생성 완료.
   - **`b0_hash` = `5e7b5b486b9d8a4a`** · exit = `B2_WORLD_CONTRACT_FROZEN`
   - 승계 해시: `lattice_R2a_P3 b7b3f6440e5b83eb` · `stage3_protocol eb3a85e702020167` ·
     `r2b_b0_v2 cba024d7ee3d9f61`
   - 격자는 **하드코딩이 아니라 R2a 산출물에서 유도**된다 (provenance 사슬 유지).
     `t0` 이 재생성 가능성 + 해시 + bracket 성질 (lo < χ50 ≤ hi, 14/14) 을 잠근다.
   - base episodes = 14 × 4 × 300 × 3 arm × 3 seed = **151,200**
5. 봉인 후 변경은 **판올림 (v4)** 으로만. 봉인 뒤 W4 B2 scripted 착수.

**현재 상태**: 1 ✅ (결재 **①~⑦**) · 2 ✅ (contract tests **12 passed** · 전체 regression
**0 failed**) · 2-2 ✅ (comment-only diff + docs/09 등록) · 3 ✅ (평가 격자 · G 확정, §2-10a) ·
4 ✅ (**payload `5e7b5b486b9d8a4a`**) · **남은 것 = 5 사용자 봉인 승인 하나**.

> **봉인 선언 (2026-09-13)**: 후보 payload `5e7b5b486b9d8a4a` 가 사용자 승인으로 봉인됐다.
> 봉인 직전 기계 체크 8종 전부 통과 — ① `b0_v3.py` 재실행 시 **byte-identical** 재생성
> ② contract tests 12/12 ③ 전체 regression 0 failed ④ bracket `lo < χ50 ≤ hi` **14/14**
> ⑤ base cells **56 = 14×4, 중복 0** ⑥ G=14 · row gate 12/14 · slice gate 5/7 직렬화 확인
> ⑦ A2-nominal primary / exact `S_C` secondary 분리 확인 ⑧ extension rule + 방향당 최대
> 2 회 직렬화 확인.
>
> **claim registry (C0xx) 등재는 사용자 트랙**이다 (docs/89 말미 규율). 본 봉인은 *계약*
> 이지 *claim* 이 아니므로 자동 등재하지 않았다 — 별도 항목이 필요하면 연번을 지정해 달라.

**심야 졸속 봉인 금지** (late-seal 감사 지적 이력). 봉인은 결재 · 테스트 · 격자 셋이 다
갖춰진 세션에서만.

---

## §5. 이 계약이 **하지 않는** 것 (명시적 비-조항)

- **6DOF / 실기 transportability 주장 없음** — docs/93 의 별도 gate.
- **모든 latency scale 에서의 경계 collapse 주장 없음** — §1.2 정본 claim 형식이 상한이다.
- **decision cadence 의 인과 주장 없음** — q_dec 는 conditioning 이다.
- **net persistence (포획 수명) 물리 없음** — W_net 은 vacuous (§2-4). 구현하면 B0 v4.
- **관측 잡음 · 지연 · actuator lag 없음** — 부재이며, 층3 에서 nominal **밖**의 흔들림으로
  측정한다 (nominal 정의에 넣지 않는다).
- **협력 necessity 주장 없음** — R2b 는 limiter-control opportunity 의 존재만 보였다.
- **learned kinetic 없음** — KINETIC 은 scripted reference fallback (§2-8).
- **learned firing gate 없음** — θ_fire 는 고정 admissibility constraint 이고 학습되는 것은
  그 안에서의 timing 뿐이다 (§2-2, 결재 ⑥). gate censoring 회수 주장 금지.
- **illegal contact 이후의 구제 없음** — `C_illegal` latch 이후의 어떤 capture 도 성공/보상으로
  복원되지 않는다 (§2-7, 결재 ⑤).
- **두 평가 집합의 혼합 없음** — primary grid 수치와 R2b `S_C` replay 수치를 섞어 보고하지
  않는다 (§2-10). R_rec 은 후자에서만 (§2-13).
