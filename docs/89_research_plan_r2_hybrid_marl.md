# 89 — 연구 상세 계획 r4: Hybrid Mission Formulation + MARL 통합 전면 개정판

- **일자**: 2026-09-07 (r3 — r2 blocker 2건 해소 확인 후 신규 blocker 1건 (shared actor ×
  staged freeze 구조 모순 → mixed-role BC 로 교체) + 정합성 5건 수정) · **상태**:
  **봉인 (2026-09-07 사용자 승인·봉인 선언)** — 이후 달력·게이트·학습 스펙 변경은
  판올림 (r4+) 으로만. 교수 인지 = W2 미팅 ① 안건 (docs/90).
- **r4 (2026-09-07 저녁 — 진행 체크 + R2b 종결 반영. 달력·게이트·학습 스펙 구조 무변경,
  추가 주석·체크만)**:
  ① **W1 핵심 항목 선행 완료** (W1 시작 전, ~1주 선행 — 여유는 W7 buffer 보험으로):
  R2b C arm 실행+판독+종결감사 2회+등록 ✅ · docs/89 봉인 ✅.
  ② **R2b 종결 결과**: C_POSITIVE (Δp_CA_net +0.370 [+0.353, +0.388], 14/14 행,
  양 slice 7/7) · 3-way = B_null_C_pos · **C047~C049 등록 완료** · 정본 =
  `docs/review_prompt_r2b_closure.txt` **r4** (2회 감사 반영).
  ③ **어휘 규율 (감사 Q2 — 위반 금지)**: "cooperation-is-meaningless is rejected" ·
  "exploitable cooperative geometry" 폐기. 사슬 칸 명칭 = **limiter-control
  opportunity** ("협력 효과" 금지). C = "search-based attainment benchmark"
  (upper bound 아님). 협력 necessity 는 미확립 (조건부 카드 = necessity ablation).
  ④ §5 체크리스트 **13항 추가** (R_rec 봉인). ⑤ §7 W10 CEM budget 산정 교훈 (c4)
  주석. 상세 근거 = closure 브리프 r4 §9~§10 + memory `r2b-closure-vocabulary-path`.
- **r5 (2026-10-01 — 사용자 승인 "재설계 생략 + 이 수순". W6~W9 작업 배분 판올림,
  게이트·데드라인 구조 불변)**: ① capturer 체인 (F1→RL2) 동결 — F3 keeper
  (STOP_RL2 + 사후 감사: 추가 위반 전부 경계 draw flip). ② W6~W9 의 "층2 고정 →
  CTDE-MAPPO 본 학습 (B-3/B-4/B-5 joint)" 을 **P1 공격자 사다리 강화 (T1 family +
  T2, defender 동결) → P2 limiter-only 학습 v2** 로 대체. joint 3-arm 은 P2 양성 시
  후속 판올림에서 복귀 검토. ③ PFSP (T4) 는 P2 양성 후 별도 판올림으로만
  (빈 self-play 금지). ④ G3 (≤10/30) · K1 (≤10/31) · W10 · G4 · W13~15 불변.
  실행 상세·규율 = **docs/117** (단일축 이동·어휘·결과 전 봉인 불변).
- **봉인 후 텍스트 정오 (2026-09-07, 사용자 지시 — 설계 변경 없음)**: §5-4 NET_FAIL
  표기를 §3.1 의 좁힌 관계 (NET_SPENT ⇒ NET_FAIL_shot) 와 정합 · §6 τ → τ₀ ·
  §12 위험표 11 → 12항 · §7 W10 어휘 제한 (전역 worst-case 단정 금지).
- **정본 관계**: 본 문서가 **docs/87 §3 달력·§5 적대자 트랙 + docs/88 전체를 supersede** 하는
  주차 달력·학습 스펙의 단일 정본. docs/87 의 §0 명명·§4 R2a 스펙(완료·봉인 결과로 승계)·
  §6 arXiv scope 는 유지 참조. docs/81 순서 사슬은 88 개정(arXiv 후순위)을 승계.
- **작성 경위**: ① docs/88 crunch (arXiv 후순위 + MARL 학기 내 진입, 09-05) ② R2a core
  캠페인 종결 (C044~C046 등록 가능 상태 [r4: 등록 완료]) ③ R2b Phase 1 P1_NOT_POSITIVE + kinetic substitution
  실측 (09-06) ④ 외부 MARL 학습 설계 자문 2건 (max-performance 자문 + hybrid mission 재정의)
  에 대한 사용자 판정 (09-07, "거의 전부 수용 + scripted fallback + NET_FAIL RL-credit 종료")
  ⑤ 민감도 프로브 3층 타이밍 규율 수용.

---

## §0. 전제 (87 §0 승계 + 개정분)

- 명명·규율은 docs/87 §0 그대로 (paper- 접두, C0xx 연번, science/hygiene 커밋 분리,
  소급 수정 금지, 금지표현, viz-first, 결과 JSON utf-8).
- **arXiv 후순위** (memory anchor 09-05): B0/B2 선행조건에서 arXiv 공개 제거, repo-R1~R3 만.
- **주간 예산**: Track R 보호 하한 **8h/주** (crunch 승인), Track W 1~2h (KSAS 이후),
  총 13~17h. 시험 주 (W7 중간·W14 기말) 감량 불변.
- **v0.7 처분표 승계**: HAPPO = stop rule 통과 후 재결정 (본 계획 §9 이연 슬롯).

## §1. 질문과 결과물 (개정)

**Paper 1 질문 (2층 분리)**:
- **과학 주장 (primary)**: 협력 조향(학습)이 **clean net capture 의 성립 경계
  χ50^net(η, λ) 를 rule-based 대비 얼마나 확장하는가** — Δχ50^net(η, λ).
- **시스템 주장 (secondary)**: reference kinetic fallback 을 포함한 전체 무력화 확률
  P_U = P_N + P_{H_fb} 는 어디까지 도달하는가 (H_illegal 불포함 — §3.4).

**URP 보고서 골격**: R2a regime map + prop1 (기본, G3-OUT 에도 무손상) + MARL 3-arm 비교
(stop rule 통과 조건부, 신청서 최소 성공 기준 회수). R2b 판독 (P1 null + C arm) 은 학습
동기 서사로 IN. **[r4 ✅ C arm 완료: P1 null + C_POSITIVE — 동기 서사 정본 문장 =
closure r4 §10.1 / C049 ("R2b separated controller failure from opportunity
absence..."), "cooperative geometry" 계열 어휘 금지]**

**학습 arm 3개 (ablation 설계 불변, 88 §5 승계)**: B-3 (geometric objective, homo) /
B-4 (viability objective, homo) / B-5 (viability + hetero). reward 축 = B-3vsB-4,
role 축 = B-4vsB-5. 시간 압박 시 B-4 의 **추가** seed 부터 감량 — **모든 arm 최소
3 seed 유지** (arm 삭제 금지).

## §2. 순서 사슬 (88 개정 승계)

```
KSAS 제출 → repo-R1~R3 → ┬→ A0 재실행 → (교수 컨펌) arXiv v0        [문헌 트랙, 후순위]
                          └→ 민감도 screen → B0 v3 봉인 → B2 scripted
                             → stop rule → MARL (CTDE-MAPPO)          [연구 트랙]
```

불변 조항: B0 v3 봉인 전 협력 학습 실험 금지 · stop rule 통과 전 MARL 학습 실행 금지 ·
PFSP/self-play 이번 학기 제외 · 교수 컨펌 필수 · 30분+ 실험은 랩 서버.

## §3. Hybrid Mission Formulation (신규 — 이번 개정의 핵심)

### §3.1 상태 머신 (상태와 이벤트 분리)

```
NET_PRE --FIRE(event)--> NET_PENDING --> { NET_CAPTURE (terminal)
                                         | NET_FAIL --> KINETIC --> NEUTRALIZE / TIMEOUT }
```

- NET_PRE 에서 limiter 의 행동 = capture-set shaping. observation 에 **mission mode bit**
  m ∈ {NET_PRE, NET_PENDING, KINETIC} 명시 제공.
- **NET_FAIL 판정의 정본 = NET_SPENT 물리 이벤트 (시간 구조 v2, 2026-09-07 판정 —
  상세 docs/91)**: "이 net 으로는 더 이상 포획 불가"라는 simulator 의 net active/spent
  상태 전이를 직접 읽는다. **고정 T_valid 를 world contract 파라미터로 만들지 않는다**
  — W_net = t_spent − t_eff (포획 유효 시작 → 소진) 는 **사후 측정값** (상수면 상수,
  상태 의존이면 분포). **표기 관계 (좁힘, 2026-09-07)**: NET_FAIL 은 호환용 outcome/event
  이름이며, **정상적 미포획 shot-exhaustion 경로에서 NET_SPENT 발생으로 trigger 된다**
  (NET_SPENT ⇒ NET_FAIL_shot). illegal contact·crash·out-of-bounds 등 다른 실패는
  NET_SPENT 가 아니라 H_illegal/F_other 경로 — 모든 실패 ≡ NET_SPENT 아님.
  deterministic · controller-independent · policy 조작 불가. **신규 predictive geometry
  판정기 제작 금지** (기존 물리 상태 읽기는 무충돌).
- **시간 3분법 + τ₀/τ_real 분리 (docs/91 v2, 승인 2026-09-07)**: **τ₀** = B0 가
  prescribe 하는 characteristic effect-latency scale (nominal 0.30 s) — **χ = aτ₀²/2ρ,
  η = vτ₀/ρ, q_dec = Δt_dec/τ₀ 에는 항상 τ₀ 만** (governing coordinate 의 endogeneity
  차단: 발사 상태에 따라 실현 지연이 달라져도 χ 불변). **τ_real** = t_eff − t_obs
  (FIRE 판단에 쓰인 최신 관측 원점) 는 **diagnostic/audit 량** — 매 발사 기록, nominal
  에서 ≈ τ₀ 설계. 가산 분해 0.10+0.05+0.15 는 engineering motivation 으로 강등.
  **Δt_dec** = policy 판단 주기 (τ_decide 명칭 금지) / **W_net** = net 가용 수명
  (ω_net = W_net/τ₀ 는 **W_net 의 exogeneity 확인 조건부 governing 후보** — 상태
  의존이면 diagnostic 강등, docs/91 §1 규칙; 판별 = W2 정독 Q3). **policy 의 의도적 WAIT 는 τ 가 아니다** — τ_real 원점은
  항상 발사 판단에 쓰인 최신 관측. dt_phys 는 수치 해상도일 뿐 물리 지연 아님 —
  **이번 학기 dt_phys = Δt_dec = 0.05 s coupled 고정 승인** + **해석 금지 caveat**:
  q_dec 1/6→1/12 의 +0.15 는 temporal-resolution conditioning (cadence 와 해상도 동시
  이동) — "decision cadence 의 인과 효과" 해석은 decoupling probe 전까지 금지.
- **하드웨어 리그 지위**: τ 성분 (launch~deploy) direct validation + W_net 보조 앵커 —
  external validation 일 뿐, primary campaign 값 소급 수정 금지 (어긋나면 B0 v4 재료).

### §3.2 Kinetic 의 지위: 금지가 아니라 fallback mode

- **illegal substitution**: contact ∧ m ∈ {NET_PRE, NET_PENDING} → severe failure
  (C_illegal). R2b P1 에서 실측된 substitution 은 전부 이 유형 — P1 null 판독 유지.
- **legitimate fallback**: NET_FAIL 이후 KINETIC mode 의 contact 는 페널티가 아니라
  kinetic success predicate 의 일부.
- **이번 학기 KINETIC = scripted PN fallback** (환경 takeover). π_kin 학습·staged
  failure-state training·joint hybrid fine-tuning 은 §9 이연. 이 fallback 은
  **reference fallback (baseline fallback)** 으로 부른다 — "보수적 하한" 표현은
  learned kinetic 이 PN 을 일관되게 상회함을 보인 뒤에만 격상.

### §3.3 RL credit 경계 (핵심 규칙)

> **NET_FAIL 은 물리 mission 의 종료가 아니라 RL credit 의 종료다.**

- 물리 mission 은 NET_FAIL 이후에도 계속되는 것으로 정의 (PN fallback, system metric).
- **MAPPO rollout/GAE/return 은 NET_FAIL 에서 terminal 처리 (cut)** — "kinetic reward 0"
  만으로는 부족 (discount·time penalty·value bootstrap 이 앞단 return 에 새는 경로 차단).
- **구현 규칙**: training wrapper 에서는 NET_FAIL 을 terminal 로 반환하고 **즉시 reset**
  한다. PN fallback continuation 은 **system-evaluation path/sidecar 에서만** 같은
  NET_FAIL state 를 받아 계속 실행한다 — training vector env 안에서 물리 episode 를
  끝까지 유지하지 않는다 (구현 비용·모호성 제거).
- **fire action 의 학습 신호 규칙**: fire action 의 policy gradient 에는 **NET_FAIL 이전의
  net-task return 만** 사용하고, post-fail kinetic outcome 은 reward/value target 에
  포함하지 않는다. (개념적으로는 Q^net 최적화지만, 별도 Q estimator 를 구현하지 않으므로
  스펙은 return 규칙으로만 명시.)
- lexicographic 원칙: **kinetic 성과는 KINETIC state 에서만 rewardable** — scripted
  fallback 이므로 이번 학기는 자동 충족.

### §3.4 지표 2층 (학습 objective 로 합산 금지)

**Outcome 4분류 (상호배타·완전 partition — episode 당 정확히 1 bin)**: **N** = clean net
capture / **H_fb** = post-NET_FAIL legitimate kinetic neutralization / **H_illegal** =
NET_PRE·NET_PENDING 중 kinetic contact / **F_other** = timeout·crash·out-of-bounds 등
기타 실패. 기존 HARD_KILL 계수가 H_illegal 을 포함한다면 반드시 분리 재집계 — H_illegal
이 시스템 성공으로 새면 substitution 을 다시 사게 된다.

| 층 | 정의 | 계수 규약 |
|---|---|---|
| **과학** | χ50^net(η, λ) | N = 1 / H_illegal = 0 / **H_fb = 0** / 기권 = 0 (**censoring 보정 금지** — 안 쏜 것은 실패) |
| **시스템** | **P_U = P_N + P_{H_fb}** (H_illegal 불포함) | legitimate fallback 만 성공 포함. P(KIN\|NET_FAIL) 은 reference fallback 값으로 보고 |
| **safety** | P_{H_illegal} | 별도 doctrine-violation rate 로 보고 (성공 지표 아님) |

- gate 의 shot-quality 모델 P(capture|fire) 추정은 별도 문제 (forced-exploration fire
  잔존 확률 or randomized probe + propensity weighting) — 과학 지표와 혼용 금지.

## §4. MAPPO 학습 스펙 (확정 — 88 §5 대체)

- **정책 구조 — arm 별로 다르다 (ablation validity 필수 조건)**:

  | arm | actor 구조 |
  |---|---|
  | B-3 / B-4 (**homo**) | **단일 shared actor** π_shared(a\|o, role token) — limiter·capturer 가 같은 네트워크를 공유하고 역할 전용 파라미터 없음. 행동 공간 비대칭 (limiter 기동 vs capturer pointing+fire) 은 **union action space + role mask** 로 처리. "homo" 의 정의 = 이 파라미터 공유 구조 |
  | B-5 (**hetero**) | shared limiter actor **π_L** (limiter 간 공유) + **완전 별도 capturer actor π_C** (pointing + Bernoulli fire head) |

  role 축 ablation (B-4 vs B-5) 의 조작 변수 = **정책 수준 역할 분리** (shared+token →
  separate) 하나뿐이어야 한다. **critic · task-success/termination semantics · sampler ·
  initialization protocol 은 3 arm 공통. reward objective 는 arm 정의에 따름** (B-3
  geometric / B-4·B-5 viability — 이것이 reward 축). actor 에 scripted attacker ID
  (A1/A2/A3) 미제공 (전 arm).
- **critic**: centralized, privileged state 허용 — (χ, η, λ) 셀 좌표 · gate/net state ·
  cone margin · 표적 simulator state. role-conditioned value head 허용.
- **reward (B-4/B-5)**: task = 1[clean NET_CAPTURE] 단일 + **viability shaping 은
  potential difference (PBRS)** r^shape = β[γΦ(s') − Φ(s)].
  **Φ = f(analytic cone/viability margins) — bounded/normalized scalar, 함수 형태는
  training contract 에서 확정** (s(x_c)·cone margin 등이 재료; 결합 형태 미정).
  **empirical χ50 을 Φ/reward 에 사용 금지**. **Φ(s_terminal) = 0** — NET_CAPTURE ·
  NET_FAIL · illegal contact · timeout 전부 (terminal potential 로 인한 종료 보상 오염
  차단). β 는 frontier 도달 기반 stage-wise annealing (최종 fine-tune 은 거의 순수 task
  reward).
  hacking 감시 4종 로그 의무: Φ↑ vs p_net / P(fire|Φ high) / P(capture|Φ high, fire) /
  p_contact 동반 상승 여부.
- **B-3 는 geometric objective (proximity 계열) 유지** — ablation 대조군이므로 §4 의
  proximity 제거 규칙 적용 대상 아님. B-3 가 illegal substitution 으로 붕괴하면 그것이
  reward 축 ablation 의 예상 결과 (finding 으로 기록).
- **contact 처리**: C_illegal (§3.2) = **terminal failure (mission semantics, B0) +
  명시적 음수 terminal reward r_illegal < 0 (training contract 봉인)**. 크기 규칙:
  **|r_illegal| > 남은 episode 에서 절약 가능한 최대 time-penalty 합** — "어차피 못
  잡으니 충돌로 빨리 끝내자" 는 intentional early-contact termination 이 유리해지지
  않게. CMDP/Lagrangian (MACPO 계열) 은 이것으로 부족할 때만 승격 (§9).
- **time penalty 약하게** — 경계가 목표이므로 조기 사출 유도 금지.
- **경계 objective 는 reward multiplier 가 아니라 scenario sampler 로 구현**:
  (η, λ, A) stratify + 최소 coverage 강제, χ 만 adaptive. anchor / frontier
  (p̂ 0.2~0.7, inside–outside sandwich) / exploration 혼합. probe grid 갱신은 수 epoch
  마다 소규모 (서버 예산 내).
- **arm 간 curriculum fairness — 공통 cell schedule**: sampler state 를 arm 별 p̂ 로
  각자 적응시키지 않는다. rule-based frontier + pooled probe 기준으로 **epoch 별 cell
  distribution 하나를 만들어 세 arm 이 같은 분포를 소비** — 아니면 "reward-only
  controlled ablation" 주장이 training exposure 차이로 무너진다. arm 별 realized cell
  distribution 은 전부 기록.
- **bootstrap = common mixed-role BC initialization → joint RL** (희소 보상 대책):
  rule-based trajectories (limiter 행동 + capturer pointing/fire 포함) 로 **mixed-role
  BC dataset 하나**를 만들고, B-3/B-4 의 π_shared 와 B-5 의 (π_L, π_C) 를 **동일 행동
  데이터에 맞춰 initialization** 한 뒤 joint RL. architecture 만 다르고 초기 behavioral
  target 은 동일. **staged freeze (capturer freeze → limiter 학습) 는 채택하지 않는다**
  — B-3/B-4 의 shared actor 에서는 limiter gradient 가 shared trunk 를 바꾸는 순간
  capturer 행동도 바뀌어 freeze 가 구조적으로 불가능 (output row freeze 로도 해결 안 됨).
  **arm 간 초기조건 공통 봉인 (training contract)**: 동일 BC dataset · 동일 BC
  epochs/stopping condition 을 3 arm 에 사용.
- **fire 탐색은 policy 분포 내부로 (판정 2026-09-07)**: wrapper 외부 ε-강제발사는
  behavior 분포와 log π_θ 가 어긋나 PPO on-policy 가정을 깨므로 학습에서 금지 —
  p_fire = ε + (1−2ε)σ(z) 형태로 분포 자체에 최소 확률을 넣고 그 log-prob 를 학습에
  쓰거나, fire head entropy bonus. **외부 forced-fire 는 평가/probe 전용.** ε/entropy
  값은 training contract 항목.
- **판독 분해 로그 상시**: 셀별 P(FIRE|χ) 와 P(N|FIRE, χ) 를 전 arm 기록 — Δχ50 이
  shaping 개선인지 발사 판단 개선인지 분해 (χ50 은 controller+gate 체계의 달성 경계).
- **평가**: adaptive 훈련 분포와 완전 분리된 **고정 (χ, η, λ, A) grid + paired CRN**,
  B2 와 동일 world contract. seed ≥ 3. "경계를 밀었다" 최소 기준은 B0 v3 에 사전 봉인
  (paired Δ 의 CI + 셀 다수결 — R2b P1 규칙 형식 승계).
- 구현: 검증된 공개 MAPPO 레퍼런스 + env wrap. 자체 구현 금지.

## §5. B0 v3 계약 체크리스트 (W2 초안 → W3 봉인 — 하나라도 누락 시 봉인 금지)

1. NET_PRE / NET_PENDING / KINETIC 상태 정의
2. FIRE transition (event) 정의
3. NET_CAPTURE predicate (기존 NET_CAPTURE = CAPTURED ∧ contact=0 승계)
4. **정상적 미포획 shot-exhaustion 경로의 NET_FAIL 은 NET_SPENT 물리 이벤트로
   trigger** (NET_SPENT ⇒ NET_FAIL_shot, §3.1 표기 관계 — illegal contact·crash 등
   다른 실패는 H_illegal/F_other 경로. simulator net active/spent 상태 직접 소비 —
   고정 T_valid 파라미터 없음) + **W_net 측정 규약** (t_spent − t_eff, 상수성/분포 기록)
   + **τ 원점 정의** (FIRE 판단에 사용된 최신 관측; WAIT ≠ latency) + dt_phys/Δt_dec
   coupling caveat (§3.1 · docs/91)
5. NET_FAIL 후 물리 episode continuation (PN fallback takeover)
6. **NET_FAIL 에서의 RL-credit termination** (rollout/GAE cut 규칙)
7. phase 별 contact semantics (C_illegal 정의)
8. KINETIC fallback controller (PN, reference fallback) 와 success predicate
9. 과학/시스템 지표 계수 규약 분리 (§3.4 표 그대로)
10. THREAT bracket·유효 부분격자 (87 §4 규율 승계) + 민감도 screen 결과에 따른
    stratification/randomization 대상 파라미터 목록 (§6)
11. "경계를 밀었다" 판정 규칙 (행/slice/전역 3조건 형식)
12. **same-tick event precedence**: ① NET_CAPTURE 와 body contact 가 같은 tick →
    **H_illegal 우선** (clean capture 정의 = contact 0 이므로 capture 실패) ②
    NET_SPENT 와 같은 tick 의 capture → **N 우선** ③ NET_SPENT 확정 **다음 control
    tick 부터** KINETIC 전환 (마지막 유효 tick 의 limiter contact 가 legitimate 으로
    오분류되는 off-by-one 차단; δ_switch 는 과학 지표 무관, P_U 에만 존재)
13. **[r4 추가] 학습 평가 부가 지표 R_rec 봉인**: search-benchmark recovery
    R_rec = (p_learned − p_A)/(p_C − p_A) — 같은 S_C · 같은 world · 같은 success
    semantics (NET_CAPTURE only) 에서만 정의. p_C 는 upper bound 아니므로
    R_rec > 1 가능 — "fraction of upper bound recovered" 명명 금지 (closure r4
    §10.3). 판정 규칙 (항목 11) 과 별개의 descriptive 부가 지표.

부속: **training contract** (B0 와 별도 문서, W6 본 학습 착수 전 봉인) — Φ 함수 형태 ·
공통 cell schedule 규칙 · mixed-role BC dataset + BC epochs/stopping 공통 초기조건 ·
r_illegal 계수 (크기 규칙 포함) · **fire 최소 확률 ε / entropy bonus (policy 분포 내부
구현)** · 층2 hyperparameter 확정값.

## §6. 민감도 프로브 3층 규율 (신규)

> **학습 전 sensitivity = 문제 정의 / 학습 후 sensitivity = robustness 검증.** 섞지 않는다.

| 층 | 시점 | 대상 | 판독 좌표 |
|---|---|---|---|
| **1. 물리·환경** | **W1~W2, B0 v3 봉인 전** | 후보 nuisance ζ (latency 성분, cone 파라미터, sensor 등) | 평균 성공률이 아니라 **Δχ50(η, λ; ζ)** — 경계 이동. nominal χ50 주변 **micro-grid 만** (전체 맵 재실행 금지). OAT 단일점 금지 — η {저·중·고} × 주요 λ slice 에서 반복해 ∂χ50/∂ζ 의 (η,λ) 의존성 확인 |
| **2. 학습 hyperparameter** | W4~W5 준비만, **pilot 실행은 stop rule PASS 직후 (W5 금~W6 초)** — PASS 전 MAPPO optimizer update 0회, **W6 본 학습 전 고정** | lr, entropy, β(PBRS), clip, GAE λ, sampler 비율 | "training hyperparameter pilot" 으로만 지칭 (system sensitivity 아님). 본 3-seed 결과 후 재조정 금지 (selection bias) |
| **3. frozen-policy robustness** | **W10+** | latency·noise·가속 교란·speed mismatch·cone 변형·actuator lag | π* freeze 후 Δχ50^robust(ζ) — nominal contract 밖 외삽 내성. 본 claim 정의 불변 |

- 층 1 절차: 후보 목록 (W1) → rule-based cheap screen (W1~W2) → 효과 큰 후보만
  boundary-local confirmatory micro-grid (W2 후반) → **승격 기준 = effect-size gate**
  (|Δχ50| > δ_χ — 통계 유의성 아님; δ_χ 는 기존 R2a boundary resolution 규칙 재사용,
  screen 착수 전 봉인) → 승격 변수만 B0 v3 stratification/randomization 대상 → 봉인 (W3).
- **coordinate-preserving perturbation 규칙**: 후보 ζ 가 이미 governing coordinate 의
  구성변수이면 (τ₀, ρ, v, a_att 등 — χ = a·τ₀²/2ρ, η = v·τ₀/ρ 에 들어가는 양) 단순 OAT 는
  probe 가 아니다 (χ, η 가 같이 움직임). **residual sensitivity 는 (χ, η, λ) = const 가
  되도록 다른 차원량을 보정한 perturbation 으로만 시험** — governing coordinate 의
  완전성 검증이 목적.
- **W3 봉인 이후 신규 물리 파라미터 탐색·regime 정의·coordinate 승격 금지** — 늦게
  발견되면 층 3 robustness study 로만. **단 하나의 예외**: B0 validity 를 깨는 구현
  오류/fatal confound/누락 변수 발견 시 primary campaign 즉시 중단 → B0 버전 상향
  재봉인 (구/신 B0 결과 **pooling 금지**). 봉인을 이유로 오류를 무시하지 않는다.

## §7. 달력 (Track R — 단일 정본, 88 §2 대체)

| 주차 | 작업 | 게이트 |
|---|---|---|
| **W1** 9/8~9/14 | KSAS 형식 마감 + 제출 (Track W 불변) · **R2b C arm 서버 실행 + 판독** (3-way 규칙 종결 — 학습 동기 서사 확정) **[r4 ✅ 9/7 조기 완료 — C_POSITIVE·B_null_C_pos, 종결감사 2회, C047~C049 등록, viz-first PASS]** · **민감도 층1 후보 목록** [r4: docs/92 초안 존재 — 확정 잔여] · docs/89 봉인 (사용자 승인) **[r4 ✅ 9/7]** → W1 잔여 = KSAS 마감 + 층1 목록 확정; 여력 시 W2 의 B0 v3 초안 선행 가능 | G1 (KSAS) |
| **W2** 9/15~9/21 | repo-R1~R3 + H-4 (랩서버·torch venv) · **B0 v3 계약 초안 (§5 체크리스트 12항)** · **층1 cheap screen → confirmatory micro-grid** · A-family 범위 선언 문서 | |
| **W3** 9/22~9/28 (추석) | 층1 판독 → 승격 파라미터 확정 → **B0 v3 봉인** · A0 재실행 캠페인 서버 밤샘 (arXiv 트랙, 병행) | **B0 v3** |
| **W4** 9/29~10/5 | **B2 scripted 실행 + 판독** (hybrid 세계에서 단독/rule-협력/reference-fallback arm — 저비용) + **forced-fire micro-arm** (경계 밴드 셀 한정 — pointing/제어기 불변, **사전 봉인된 단일 firing-time intervention 만**으로 gate 만 제거: χ50 을 게이트 경계 vs 발사 조건부 포획 경계로 분해) · env Gym-wrap + interface smoke (optimizer update 0회) | |
| **W5** 10/6~10/12 | **B2 stop rule 판정 (금)** → 통과 시 MAPPO 착수 결재 · hyperparameter pilot (층2) 준비, **실행은 PASS 직후 개시** (랩서버) | **stop rule** |
| **W6~W9** 10/13~11/9 | 층2 고정 (W6 초) → **CTDE-MAPPO 본 학습** (B-3/B-4/B-5 × seed≥3, §4 mixed-role BC init → joint RL) · prop1 K1 (≤10/31) · R2a G3 판정 (≤10/30, 선행분 조기 가능) · W7 중간고사 주 감량 | G3 · K1 |
| **W10~W11** 11/10~11/23 | 학습 판독 + scripted 대조 (paired CRN 고정 grid) · **층3 frozen-policy robustness sweep** · **A-family parameter worst-case 평가 arm** (frozen policy 에 대해 CEM 으로 최악 파라미터 탐색 → e* 선택 → **fresh CRN 재평가** — discovery/evaluation 분리로 selection bias 차단; 프로토콜은 **W3 전 사전 선언**, 학습은 여전히 scripted 고정. **어휘 제한**: 유한 search budget 이므로 논문에서 "worst-case" 단정 금지 — "sealed-budget CEM adversarial search" / "worst found within the declared A-family search" 만) [r4: CEM 예산 산정은 **per-CEM-solve 실측** 기준 — R2b branch estimator 가 elapsed/len(records) 희석으로 ~4× 과소추정한 교훈 (closure r4 c4)] · prop1 K2 (≤11/15) · 하드웨어 실측 세션 1회 → 연구노트 · (조건부) **공사 학술대회 발표자료** (개최 11/25, −2주 규칙 — 붙임 규정·중복투고 확인 선행) | K2 |
| **W12** 11/24~11/30 | **G4: 과학 결과 확정** — 이후 신규 실험 금지 · 신청서 산출물 5종 역매핑 표 · (조건부) 공사 학술대회 발표 (11/25 수) | G4 |
| **W13~W15** ~12/18 | URP 최종보고서 (영문) + 정산서 + 연구노트 제출 · arXiv 는 결과 반영해 재개 | 12/18 |

**stop rule 실패 시** (88 승계): MARL 미진입. W6~W9 는 prop1 Arm A + design requirement
curve 로 전환, 보고서는 "학습 비교는 scripted 존재증명 부재로 게이트 차단" 정면 서술.

Track W (문헌): KSAS 발표 (개최 주 −2주 감량 규칙) · arXiv 후순위 트랙 (A0 → 교수 컨펌
→ 공개, 연구 트랙 비차단) · 보고서 W13 80% 선완성 — docs/87 §3B 리듬 승계.

## §8. 논문 주장 구조 (upgrade 기록 — 집필 시 사용)

- primary: Δχ50^net(η, λ) response surface. 요약 scalar 필요 시 integrated frontier gain
  G = ∫ w(η,λ)[χ50^RL − χ50^B] dηdλ (부가 지표).
- secondary: P_U (reference fallback 포함) — "협력 shaping 이 clean-net 경계를 Δ만큼
  확장했다" 와 "fallback 포함 전체 무력화 확률 X" 를 **두 문장으로 분리** 서술.
- **용어 주의 (집필 시)**: B-3/B-4 의 "homo" 는 물리적 동일 역할이 아니라 **parameter
  sharing** 의 뜻 (role token + action mask 로 역할 차이는 이미 입력/행동 의미론에 존재).
  논문에서는 "homogeneous vs heterogeneous agents" 대신 **"shared role-conditioned
  policy vs role-separated policies"** 로 표기.
- novelty 후보: **phase-dependent heterogeneous role** — 같은 물리 agent 의 objective 가
  mission phase 에 따라 "잡지 않는 것이 최선 → 직접 잡는 것이 최선" 으로 반전되는 hybrid
  mission formulation (Gavin & Bronz 류 고정 목적 pursuer 와의 차별점).
- 기존 R2b P1 null 은 "illegal pre-net kinetic substitution 실측" 으로 재명명되어 hybrid
  formulation 의 실증 동기가 된다 (negative result 유지 + 설계 정당화).
- **cooperation null 해석의 2-Case 어휘 (docs/91 §1.5)**: Case 1 = 협력 창 (C_coop) 존재
  + controller 미활용 (→ MARL 명분) / Case 2 = 창 자체의 부재 정합 (time-scale mismatch
  — 학습으로 못 고치는 negative result). **C arm 판독이 이 분해의 도구** (C_N 양성 =
  Case 1 / C_N null = Case 2 정합, 봉인 한정어 유지). 봉인 어휘를 대체하지 않는 해석 층.
  **[r4 판독 반영: C_N 양성 — Case 1 방향. 단 종결감사 (closure r4 §9.2) 하향 적용:
  확립된 것은 "limiter-control opportunity 존재 + 해당 rule 미활용" 까지이며
  "협력 창 (C_coop) 존재" 단정 금지 — multi-limiter 상호의존성 미분해 (c8). '협력 창'
  은 집필 가설 명칭으로만, necessity 주장 금지. gain attribution 은 accels-best class
  99.2% (descriptive).]**
- 협력 창 재정의 (집필용): "FIRE 이전에 path-limiter 의 비접촉 기동이 표적 reachable
  set 을 변형해 delayed net capture 의 viability 를 개선할 수 있는 상태-시간 영역" —
  "포획 직전 좁은 시간창" 서술 폐기. 세 시간척도 T_coop → τ → W_net 의 상대 크기가
  협력 가능성의 물리적 골격.

## §9. 이연 슬롯 (이번 학기 금지 — 슬롯 명기)

| 항목 | 슬롯 |
|---|---|
| learned π_kin · staged failure-state training · joint hybrid-policy fine-tune | W18+ / Paper 1 "hybrid mission policy" 후속 트랙 |
| HAPPO performance challenger | stop rule 통과 후 재결정 (v0.7 처분표 승계) |
| parametric adversary **학습 co-adaptation** (Stage B 훈련 사용) → learned evader league + PFSP (Stage C) | W18~19 보강 → Paper 1+. **단 frozen-policy 에 대한 A-family parameter worst-case 평가는 W10 robustness arm 으로 승격** (§7 — 프로토콜 W3 전 선언, discovery/eval CRN 분리). nominal Δχ50 > 0 인데 worst-A Δχ50 ≈ 0 이면 그것이 self-play 필요성의 실측 동기 (Paper 1 서사) |
| 2-D opponent × frontier matchmaking P(e,c) · χ50^robust lower-envelope | Paper 1 claim 구조 |
| MACPO / MAPPO-Lagrangian (contact CMDP) | C_illegal severe-failure 로 부족할 때만 승격 |
| COMA 류 counterfactual critic · entity encoder/attention pooling | 성능 plateau 이후 2차 |

## §10. 게이트 (87 §8 승계 + 개정)

- **G1 [W]** (W1): KSAS 제출 (불변).
- **B0 v3** (W3): §5 체크리스트 12항 완결 + 층1 민감도 판독 반영 — 누락 시 봉인 연기
  (봉인 연기 = W4 B2 도 연기, 뒤 일정 1주 슬립까지는 W7 buffer 로 흡수).
- **stop rule [R]** (W5 금): B2 scripted 존재증명 + R2b C arm 판독 인용 **[r4: C arm
  판독 확보 ✅ — C_POSITIVE (C048) 인용 준비 완료, 두 입력 중 하나 조기 충족]**. **판정 근거는
  net 쪽 지표만** — reference fallback 은 B2 에서 secondary system metric 으로 기록만
  하며 stop-rule pass/fail 에 사용 금지 (MARL 진입 사유 = learned shaping 의 net frontier
  개선 여지이지 P_U 가 아님). 실패 → §7 전환.
- **G3 [R]** (≤10/30): R2a collapse 판정 (봉인 기준 인용만 — 선행 캠페인 완료로 조기 가능).
- **G4 [R+W]** (W12 초): 과학 결과 확정 + 보고서 scope lock.

## §11. 하드웨어 (88 §4 승계 — 사슬 밖 별도 트랙)

벤치탑 전개지연 리그 (~15~25만, 11/18 한) · Crazyflie 2.1+ (~60~70만, **10/18 한 —
다음 주 발주 필요**) · 절차 = 교수 미팅 안건 → 법인카드 → W10~11 실측 세션 증적.
전개지연 리그 실측은 **τ 성분 (launch~deploy) 의 direct external validation + W_net
에 대한 보조 물리 앵커** (리그는 전체 가용 수명을 직접 재지 않는다; primary campaign
값 소급 수정 금지, §3.1) — 구매 명분에는 "deployment delay sensitivity 실측 앵커
(external validation)" 로 명기.

## §12. 위험 top 5 (개정)

| # | 위험 | 완화 |
|---|---|---|
| 1 | **B0 v3 봉인 지연** (hybrid 계약 12항이 87 대비 무거움) | W2 에 계약 초안을 문서 작업으로 선행 (서버 불요) · §5 체크리스트로 누락 방지 · 1주 슬립은 W7 흡수 |
| 2 | **NET_SPENT 이벤트가 simulator 에 명시적으로 없을 가능성** (발사 시점 기하 판정 구현이면 이벤트 자체를 새로 정의해야 함) | W2 정독 Q3 로 선확인 (docs/91) — 없으면 net 모델에서 소진 조건을 유도해 이벤트로 추가 (deterministic·상태 기반, 예측 판정기 아님) |
| 3 | **학습이 W6~W9 에 안 끝남** | common mixed-role BC initialization → joint RL 로 희소 보상 완화 · B-4 seed 감량 순서 · stop rule 실패 시 전환 경로 사전 선언 |
| 4 | **substitution 형태 변형** ("일부러 miss → fallback") | 구조적 차단: scripted fallback + NET_FAIL RL-credit cut (§3.3) — reward 튜닝 아닌 구조로 해결 |
| 5 | 랩서버/torch 병목 · 학기 부하 | H-4 W2 선확인 · 주 8h 보호 + 시험 주 감량 · 공사 학술대회는 조건부 (붙임 규정 미확인 시 미출품) |

---

*갱신은 금요일 감사 세션에서 판정형 기록과 함께. registry 등록 (C044~ 이후 연번)·seal
행위·docs/81 개정 append 는 사용자 트랙.*
