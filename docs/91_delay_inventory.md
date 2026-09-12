# 91 — 시간 구조 정본 v2.1 (B0 v3 선행 재료)

- **일자**: 2026-09-07 (v2 — 사용자 판정으로 전면 재구조화: "시간 지연을 더 정교하게
  분해하는 게 아니라 역할을 줄인다". v1 의 가산 분해 중심 인벤토리를 대체)
- **v2.1 (2026-09-13 — code audit Q1/Q3/Q4 반영, §7 신설)**: τ₀ 재정의 =
  **post-fire characteristic delayed-effect scale** (관측→판단 지연 구현상 0;
  fire-시점 viability horizon + 지연 outcome-resolution timer 의 두 기제) ·
  **q_race = τ_lock/τ₀ = 1/3 contract-fixed ratio** 도입 · W_net = vacuous
  판정 (ω_net 층1 제외) · τ₀→0 = singular instantaneous-effector limit ·
  정본 claim 형식 = "at fixed q_dec and fixed timer ratios, the boundary is
  characterized in (χ, η, λ)". 상세 §6·§7.
- **핵심 판정**: 시간에는 **세 종류만** 둔다 — τ (효과 지연) · Δt_dec (판단 주기) ·
  W_net (net 가용 수명). 이 셋은 서로의 구성성분이 아니다. T_valid 는 **파라미터로
  만들지 않는다** — NET_SPENT 는 이벤트다. [v2.1 주: W_net 은 현행 구현에서
  물리 채널 부재 (vacuous) 판정 — §6 Q3. 세-종류 원칙 자체는 유지하되 이번
  학기 실효 시간 구조 = τ₀ + 고정 비율 conditioning (q_dec, q_race).]

## 0. 이벤트 시간축 (정본)

```
[t_obs]        [t_fire]     [t_launch]      [t_eff]              [t_spent]
 FIRE 판단에    FIRE 명령  →  실제 사출  →  포획 가능 시작  →      net 소진
 사용된 최신                                    │                    │
 관측의 시각                                    │                    │
    └──────────────── τ ───────────────────────┘                    │
                                                └───── W_net ───────┘
   (decision opportunity 는 Δt_dec 간격으로 반복; dt_phys 는 그 아래 수치 적분 격자)
```

겹치는 구간 없음: t_obs →(τ)→ t_eff →(W_net)→ t_spent.

## 1. 세 가지 시간 (정의)

### τ₀ vs τ_real — characteristic scale 과 실현값의 분리 (승인 조건 ①, 2026-09-07)

- **τ₀** = B0 에서 **prescribe 하는 characteristic effect-latency scale** (scenario/world
  파라미터, nominal 0.30 s). **χ = aτ₀²/(2ρ), η = vτ₀/ρ, q_dec = Δt_dec/τ₀ 에는 항상
  τ₀ 만 사용** — governing coordinate 는 policy 행동에 의해 변하지 않아야 한다
  (endogeneity 차단: learned gate 의 발사 상태 선택으로 실현 지연이 달라져도 χ 는 불변).
- **τ_real** = t_eff − t_obs (**t_obs = 이번 FIRE 판단에 실제 사용된 최신 관측의 측정
  시각**). measurement age + processing + decision/action + trigger→launch + net
  비행·전개를 통째로 압축한 **실현 지연 — diagnostic/audit 량**으로 매 발사 기록.
  nominal simulation 은 τ_real ≈ τ₀ 가 되도록 설계, robustness 에서는 의도적으로
  어긋나게 할 수 있다.
- 무차원화 철학의 정확한 형태: "0.30 s 라는 측정값을 믿어서 쓰는 게 아니라, τ₀ 라는
  characteristic scale 을 **선언**하고 그 scale 에 대한 결과를 무차원화한다."

- **0.10+0.05+0.15 가산 분해는 이론에서 내린다** — "대표적 sensing/decision/deployment
  timescale 을 고려해 nominal τ₀ = 0.30 s 를 채택했다" 수준의 **engineering
  motivation** 으로만. 물리 주장은 τ 값 자체가 아니라 **χ ∝ aτ²/ρ scaling** 이다.
  (무차원화의 본래 목적: 특정 하드웨어 latency 에 결과를 묶지 않기.)
- **policy 의 WAIT 는 τ 가 아니다**: obs1→WAIT→obs2→WAIT→obs3→FIRE 면
  τ = t_eff − t_obs3. 기다리는 동안 새 관측이 계속 들어오므로, 의도적 대기는 policy
  behavior 이지 system latency 가 아니다. 이걸 분리하지 않으면 learned gate 가 오래
  기다릴수록 χ 자체가 변하는 오류가 생긴다.
- τ_trigger (t_launch − t_fire) 는 별도 좌표가 아니라 τ 내부 구성요소.

### Δt_dec — policy 판단 주기 (τ 의 부분이 아님)

Δt_dec = policy action 갱신 주기. "판단에 50 ms 가 걸린다" (latency) 와 "20 Hz 로
판단한다" (period) 는 다른 개념이므로 **τ_decide 라는 이름을 쓰지 않는다.**
conditioning: **q_dec = Δt_dec / τ₀** (= 1/6 현행 pin — 분모는 realized 가 아니라
contract 의 τ₀: episode 마다 출렁이지 않게). χ 에는 직접 안 들어간다.

### W_net — net 의 가용 수명 (T_valid 대체)

W_net = t_spent − t_eff. **포획 가능해진 뒤 capture-capable 상태가 유지되는 시간.**
τ 와 구간이 겹치지 않는다 (구 T_valid = 발사 원점이라 비행·전개가 τ 와 겹쳤음 — 폐기).

- **NET_SPENT 는 파라미터가 아니라 simulator 이벤트**: "이 net 으로는 더 이상 포획
  불가"라는 물리 상태 전이. 상태 머신은 NET_PENDING → {NET_CAPTURE | NET_SPENT} 로
  이벤트를 직접 소비하고, W_net 은 **사후 측정값** (일정하면 상수, 상태 의존이면 분포).
  고정 T_valid 를 world contract 의 knob 로 만들지 않는다.
- 무차원 후보: ω_net = W_net/τ₀ — **단 exogeneity 조건부 (승인 조건, 2026-09-07)**:
  ω_net 은 W_net 이 effector/world setting 으로 **외생적으로 제어 가능할 때만** governing
  후보다. t_eff·t_spent 가 발사각·표적 상태·pointing·발사 시점에 의존하면 W_net,real 은
  policy-dependent realized quantity 가 되어 좌표로 쓰면 endogeneity 문제 재발 (τ_real
  과 동일 논리). 그 경우: W_net,real = **audit/response diagnostic 로 강등**하고,
  sensitivity 는 W_net 자체가 아니라 **net persistence 를 결정하는 물리 파라미터를
  perturb** 해 W_net,real 의 반응을 본다. 판별은 W2 정독 (Q3).

## 1.5 T_coop — 협력 창 (effector 시간상수와 다른 종류, 2026-09-07 추가)

**정의**: 협력 창 = FIRE 이전에 path-limiter 의 **비접촉 기동**이 표적의 reachable set 을
변형해 (R_coop^τ ⊂ R_solo^τ), 이후 delayed net capture 의 viability 를 개선할 수 있는
**상태-시간 영역** C_coop. 특정 episode 가 그 영역에 머문 시간을 사후 측정한 것이
T_coop — **고정 상수로 선언하지 않는다** (η, λ, limiter 배치에 따라 다름).

- **"kinetic 으로 때릴 수 있는 시간"이 아니다** — FIRE 전 contact 는 illegal
  substitution. 협력의 수단은 요격이 아니라 reachable-set 변형.
- **FIRE 가 창을 닫는다**: COOPERATIVE SHAPING —FIRE→ DELAYED NET EFFECT →
  CAPTURE/SPENT. NET_SPENT 뒤의 KINETIC 은 협력 창의 연장이 아니라 별개 fallback
  objective.
- **세 시간척도의 골격**: T_coop (미래 상태를 만들 수 있는 시간) → τ (효과가 나타나기까지
  기다리는 시간) → W_net (효과 후 기회가 사는 시간). 이 상대 크기가 협력 가능성의 물리적
  골격. 비교 후보 비율 T_coop/T_L (limiter 특성 기동시간), T_coop/τ — **당장 좌표 승격
  금지, 존재 측정이 먼저.**

**cooperation null 의 2-Case 분해 (해석 층 — 봉인 어휘 위에 얹는 언어)**:

| Case | 상태 | 의미 |
|---|---|---|
| 1 | C_coop ≠ ∅ 인데 rule-based 가 활용 못 함 | controller 한계 — **MARL 최상의 명분** |
| 2 | C_coop 자체가 (시험 범위에서) 사실상 없음 — T_coop ≪ T_L | architecture/time-scale mismatch — 중요한 negative result (학습으로 못 고침) |

- **R2b C arm 이 이 분해의 기존 도구**: C_N 양성 = Case 1 방향 / C_N null = Case 2 정합
  (봉인 한정어 "tested lite search budget" 유지 — 부재의 증명 아님).
- **저비용 측정 (신규 캠페인 0)**: B2 의 단독/협력 paired CRN 궤적에서 ① 분기 시점
  (= limiter 인과 영향 시작) ② 분기 방향의 Φ margin 개선 여부를 사후 집계 → episode 별
  실효 협력 시간 분포. W4 B2 판독의 진단 항목.

## 2. 그 외 시간량의 지위

| 시간/파라미터 | 시작 → 종료 | 의미 | χ 에 들어감? |
|---|---|---|---|
| τ | FIRE 에 사용된 최신 관측 → capture-effective | end-to-end effect latency | **YES** |
| Δt_sense | 센서 샘플 → 다음 샘플 | sensing cadence (10 Hz LiDAR). "항상 100 ms 지연" 아님 — measurement age 는 0~Δt_sense 분포 | 직접 X (필요 시 q_sense = Δt_sense/τ conditioning — 이번 학기 도입 안 함) |
| Δt_dec | decision → 다음 decision | policy cadence | 직접 X (q_dec conditioning) |
| dt_phys | physics tick | 수치 적분·충돌/포획 predicate 해상도. **물리 latency 의미 부여 금지, dt_phys ∉ τ** | **NO** |
| τ_trigger | FIRE 명령 → 실제 사출 | launcher latency | τ 내부 |
| net 비행·전개 | 사출 → capture-effective | net 물리 지연 | τ 내부 |
| W_net | capture-effective → NET_SPENT | usable net lifetime | 별도 후보 (ω_net) |
| NET_SPENT | — | net capability 종료 **이벤트** | 파라미터 아님 |
| δ_switch | NET_SPENT → kinetic 활성 | mode 전환 지연 ∈ [0, Δt_dec] (다음 틱 규칙) | 과학 지표 무관 (NET_SPENT 에서 net-science trajectory 종료) — P_U 평가에만 유지 |

## 3. 시뮬레이터 coupling 문제 (B0 초안 결정 사항)

현행 구현은 **dt_phys = Δt_dec** (판단이 매 물리 틱). 그래서 q_dec 교란은 ① 행동 빈도
② 물리 적분 해상도 ③ predicate 샘플링 해상도를 **동시에** 움직인다 — τ 정의 문제가
아니라 시간축 coupling 문제.

- 이상 구조: dt_phys 고정 (예: 10 ms) + Δt_dec = k·dt_phys, 사이는 action hold.
- **이번 학기: coupled 유지 승인 (2026-09-07)** — dt_phys = Δt_dec = 0.05 s 를 고정
  contract 로 전 arm 동일 사용. 시간축 재건은 구현 영향 > 연구 질문 하나 + R2a/R2b
  연속성 비용.
- **해석 금지 caveat (봉인)**: q_dec 1/6→1/12 의 χ50 ~+0.15 는 cadence 와 수치 해상도가
  동시에 움직인 결과이므로 **"decision cadence 의 인과 효과"로 해석 금지** — 지위는
  **temporal-resolution conditioning** (민감하다는 관측만 유효, causal source unresolved).
  "더 자주 판단해서 좋아졌다" 류 문장은 decoupling probe 전까지 금지.

## 4. 시간 후보의 층1 분류 (승인 반영 — 서로 다른 질문을 맡는다)

| 양 | 지위 | 층1 취급 |
|---|---|---|
| **τ₀** | 기존 governing scale | 새 좌표 탐색 아님 — collapse 가설 검증 (R2a 로 tested domain 에서 답함) |
| **q_dec** | known pinned **temporal-resolution conditioning** (causal source unresolved — dt coupling) | **재스크리닝 안 함** — 1/6 pin + caveat + 1/12 mini-map 부록만 |
| **ω_net = W_net/τ₀** | 신규 residual-group 후보 — **W_net 의 exogeneity 확인 조건부** (상태 의존이면 diagnostic 강등, §1 참조) | exogenous 확인 시: 층1 스크리닝 — (χ,η,λ) 고정 residual 시험. 상태 의존 시: net persistence 물리 파라미터를 perturb 하고 W_net,real 반응 기록 |
| τ_real | diagnostic/audit | 좌표 아님 — 매 발사 기록, nominal 에서 ≈ τ₀ 확인 |

## 5. 문서 전파 규칙

- **KSAS (동결·제출 트랙)**: r5 의 가산 분해 서술은 소급 수정하지 않는다. **157 문장은
  검증 결과 특정형이라 산술적으로 옳음** ("비행시간 0.15 s **만** 계상하면 157 m/s²" —
  2ρ/0.15² = 157.3 ✓; "어느 성분 하나만 제거해도 157" 이라는 틀린 일반형 아님) —
  하한 채택의 민감도 논증으로 유효. arXiv 에서의 발전 문장: "earlier short-form
  treatment used a nominal additive latency budget; the subsequent formulation treats
  τ₀ as an end-to-end characteristic scale." 새 시간 구조는 **B0 v3 / MARL / arXiv
  이후 트랙부터** 적용.
- B0 v3 반영 (docs/89 §5-4 개정): NET_SPENT 이벤트 정의 · W_net 측정 규약 · τ 원점
  정의 (FIRE 에 사용된 최신 관측) · WAIT ≠ latency 규칙 · dt_phys/Δt_dec coupling 결정.
- 하드웨어 리그: τ (중 launch~deploy 성분) direct validation + **W_net 보조 앵커**.

## 6. W2 코드 정독 질문 (갱신)

- [x] Q1: τ 의 구현 — **판정 (2026-09-13 code audit)**: 관측→판정 지연 0 (당 틱
  참값, buffer/필터 없음 — t_obs ≡ t_fire) · 판정→효과 = 명시 FSM 타이머
  (DEPLOYING tau_deploy → LOCKED tau_lock) + **fire-시점 동결 worst-case
  predicate** (적용은 resolution 틱). τ_real ≡ tau_deploy by construction ·
  t_obs 로깅 trivially 가능 (CommitMeta.t_fire). **부수 발견 F2: tau_lock
  outcome-application 지연 동안 침투가 capture 를 선점하는 race** (B0 v3 §5-12
  명문화 대상) · F1: env.py L305 주석-코드 불일치 (동결 시점 — 주석만 낡음).
  #3 collapse probe = ~~진입 가능~~ → **HOLD (같은 날 2차 판정)**: τ₀ 교란이
  dt 고정 하에서 q_dec 를 1/4↔1/9 로 동반 이동 — 기실측 q_dec 민감 (+0.15) 과
  귀속 분리 불가 (confound blocker). 깨끗한 형태 = (τ₀, Δt_dec, τ_deploy,
  τ_lock) 동시 k배 similarity — dt_phys=Δt_dec coupling 으로 현 아키텍처
  불가. 상세 = temp_research_note/2026-09-13 audit + layer1_verdict 노트 2편.
  표현 정정: "τ₀ is implemented through both the fire-time viability horizon
  and the delayed outcome-resolution timer" (reduced-order — "물리 실현" 아님).
- [x] Q2: q_dec ↔ 판단 지연 — **해소 (09-07 판정)**: Δt_dec 는 period 이지 latency 가
  아니며 τ 의 구성성분으로 간주하지 않는다. q_dec = Δt_dec/τ conditioning. 가산 분해
  자체를 이론에서 내렸으므로 이중 계상 질문은 소멸. 남는 것 = §3 coupling caveat.
- [x] Q3: net lifecycle — **판정 (2026-09-13)**: NET_SPENT 이벤트 **실재·직접
  판독** (FSM SPENT + env_sys.net_spent/net_spent_step, deterministic — docs/89
  위험 2 해소, NET_PENDING ↔ DEPLOYING+LOCKED 매핑). 단 **W_net 은 §1 이분법의
  제3 결과 = vacuous**: 외생·상수 (= tau_lock) 이나 capture 가 fire 동결 단일
  predicate 라 "포획 가능 수명"의 인과 채널 자체가 없음 → **ω_net 층1 제외**
  (강등도 아니고 governing 도 아님 — 물리 부재; hybrid 가 net persistence 를
  구현하면 B0 v4 재료).
- [x] Q4: 센서 잡음·latency — **판정 (2026-09-13)**: 미배선 (defender obs·fire
  판정 전부 당 틱 참값; 유일 지연 채널 = attacker A3-privileged v_shot 1-step
  leak, sealed A2 일부). → #2a/2b 는 screen 아닌 구현 결정 — B0 v3 에
  "noiseless·zero-latency 관측 contract" 명문화 + 층3 (W10+) 이월.

## 7. v2.1 개념 정리 (2026-09-13 — code audit 반영, §1~§4 위에 얹는 정정 층)

**7.1 τ₀ 의 실체 (재정의)**: 구현상 관측→판단 지연 = 0 (t_obs ≡ t_fire) 이므로
τ₀ 는 "generic system latency" 가 아니라 **post-fire characteristic
delayed-effect scale** 이다. 두 기제로 구현된다 — ① fire-시점 worst-case
viability horizon (판정 기하의 지평 = τ_deploy = τ₀) ② 지연 outcome-resolution
timer (적용 = fire + τ_deploy + τ_lock). 표현 규칙: "τ₀ is implemented through
both the fire-time viability horizon and the delayed outcome-resolution
timer" — "물리 실현" 단독 표현 금지 (net ballistic 적분으로 오독).

**7.2 F2 race (신규 semantics)**: 동결된 capture 가 적용되기 전 pending 창
(τ_deploy + τ_lock) 동안 침투는 매 틱 살아 있다 — τ₀ 는 capture viability 와
event-order competition 양쪽에 작용한다. same-tick precedence (code-verified):
pending 창에서는 침투 자명 승 / **resolution 틱 동시 발생은 CAPTURE 우선**
(run_episode 라벨 사슬; sham-net 의 침투-우선 조항은 capture_terminates=False
전용). → B0 v3 §5-12 ④ 로 봉인 (유지/변경은 봉인 시 판정).

**7.3 무차원군 3개 (이번 학기 실효 시간 구조)**:
χ = aτ₀²/2ρ (governing) · **q_dec = Δt_dec/τ₀ = 1/6 (pinned conditioning)** ·
**q_race = τ_lock/τ₀ = 1/3 (ledger contract-fixed ratio — 새 좌표 아님)**.
q_dec 의 존재는 무차원화의 실패가 아니라 독립 시간척도가 (τ₀, Δt_dec) 둘임이
드러난 것 (Buckingham-Π 상 당연 잔존).

**7.4 정본 claim 형식 (Paper 1)**:
> For the sealed reduced-order world at fixed temporal-resolution
> conditioning q_dec = 1/6 and fixed timer ratios (q_race = 1/3), the
> net-capture boundary is characterized in (χ, η, λ).

전 latency-scale collapse (모든 scale 에서 동일 경계) 의 강한 주장은 하지
않는다 — 후속에서 q_dec·q_race 독립 sweep (decoupled dt 아키텍처 필요) 으로만.

**7.5 τ₀→0 은 singular limit**: 관측 지연이 이미 0 이므로 τ₀→0 은 "발사 즉시
효과 적용" — viability horizon·race·post-fire 회피가 전부 소멸하고 FIRE 가
instantaneous geometric capture test 로 퇴화. dt 고정 시 q_dec→∞. **smooth
extrapolation 대상 아님** — instantaneous-effector idealization 참조점으로만.

**7.6 #3 (latency-scale collapse probe) 지위**: conceptually valid but
currently confounded by q_dec–dt coupling — **defer unless a q_dec-preserving
implementation is available** (깨끗한 형태 = (τ₀, Δt_dec, τ_deploy, τ_lock)
동시 k배 similarity; dt_phys=Δt_dec coupling 이 차단). 층1 최종 판정 =
**no clean executable candidate** (docs/92 §5).
