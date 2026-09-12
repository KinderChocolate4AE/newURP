# 92 — 층1 민감도 후보 목록 (W1 산출물 — screen 사전 재료)

- **일자**: 2026-09-07 (r4 — **δ_χ = 0.03 봉인 (사용자 APPROVE)** + §3 진입 규칙
  수치 확정 (near-threshold 분기 = 6/6 동일 부호 ∧ ≥4/6 |Δ| ≥ 0.02) + grid 문구
  교체. r3 — 도출 §4 · 해석 톤 조정. r2 — noise/latency 분리 · 무차원 규칙 · τ₀
  residual mechanism 재정의 · 2-stage 규칙) · **지위**: **δ_χ + §3 진입 규칙 = 봉인
  (2026-09-07)** — 이후 screen 결과를 보고 threshold·entry rule 수정 금지.
  cheap-screen 실행 설계는 별도 (W2).
- **목적 (한 문장)**: 변수를 많이 찾는 게 아니라 — **(χ, η, λ) 로 설명되지 않는
  residual physics 가 있는가** 를 B0 v3 봉인 전에 마지막으로 싸게 공격하는 것.
- **규율 (docs/89 §6 승계)**: 판독 좌표 = **Δχ50(η, λ; ζ)** — 평균 성공률 아님.
  nominal χ50 경계 주변 **micro-grid 만** (전체 맵 재실행 금지 — R2a Stage 2/3 경계
  밴드 셀 재사용). **한 점짜리 OAT 금지** — η {저·중·고} × 주요 λ slice 반복.
  승격 = effect-size gate (|Δχ50| > δ_χ), 통계 유의성 아님.
- **세계**: rule-based (B0 v2 세계, hold/협력 arm), 학습 무관. 승격 변수만 B0 v3
  stratification/randomization 대상.

## 0. R2a 가 이미 소진한 축 — 재스크리닝 금지

| 축 | 기존 결과 | 처분 |
|---|---|---|
| ρ-DOM (λ 계열) | Stage 1 R-rho-DOM 6/6 FAIL → Stage 4 → Stage 3 → **λ 좌표 승격** (C045) | 좌표가 됨 — nuisance 아님 |
| k_f·τ (controller gain) | Stage 1 +50% 교란, 6 경계 셀 δp = 0.10 내 robust (S2) | 저순위 유지 (§2-5) — δp 좌표 결과라 χ50-이동 좌표로는 미측정이나, 방향 증거 있음 |
| SIM (차원 재스케일) | S1 pathwise 8e-15 · 0/4,800 label | 종결 |
| q_dec | 1/6→1/12 χ50 ~+0.15 실측 — 단 dt 결합 (temporal-resolution conditioning) | **재스크리닝 안 함** — pin + 해석 금지 caveat + 1/12 mini-map 부록만 (docs/91 §4) |
| evasion (jink·route·dodge) | S4 local 2×2 family envelope displaced (C046) | 층1 아님 — **A-family 범위 선언 트랙** (W2 문서)으로 분리 |

## 1. 좌표 정의와 coordinate-preserving 보정식

좌표 (r2a_lattice 정본): **χ = a·τ₀²/(2ρ) · η = v·τ₀/ρ · λ = R_max/ρ**
(α = arctan(1/λ) 대수 종속 — 별도 축 아님).

구성변수 (τ₀, ρ, v, a, R_max) 의 단순 OAT 는 좌표 자체를 움직이므로 probe 가
아니다 (docs/89 §6). **residual 시험**: 아래 보정으로 (χ, η, λ) = const 를 유지한
채 물리 실현만 바꾼다. **해석 규칙 (r3 톤 조정)**: |Δχ50| > δ_χ 면 숨은 residual
physics 후보. |Δχ50| ≤ δ_χ 는 **효과의 부재나 "좌표가 이 변수를 흡수한다"가 아니라**
— "tested domain 과 현재 resolution 에서 δ_χ 를 넘는 residual boundary shift 를
검출하지 못했다"로만 해석한다. 좌표 완전성은 이런 결과가 누적되며 지지되는 상위
해석이지, 단일 probe 나 δ_χ 하나가 증명하는 성질이 아니다.

| 교란 | (χ, η, λ) 고정 보정 |
|---|---|
| τ₀ → k·τ₀ | a → a/k² · v → v/k (ρ, R_max 불변) |
| ρ → k·ρ | a → k·a · v → k·v · R_max → k·R_max |
| a → k·a | τ₀ → τ₀/√k (동시에 v → v·√k 로 η 복원) 또는 ρ → k·ρ 경로 사용 |
| v → k·v | τ₀ → τ₀/k + a → a·k² (χ 복원) — 실질적으로 τ₀ 행과 동일 사슬 |
| R_max → k·R_max 단독 | 보정 불가 — 이것은 λ 이동 (좌표 내부), residual probe 아님 |

주의: residual 시험은 H-SIM (비례 co-scale) 과 다르다 — SIM 은 전부 같이 움직였고,
여기는 **한 차원량만 어긋나게** 하고 좌표를 복원한다 (R2a Stage 1 DOM 프로브의
잔여 축 확장에 해당).

**무차원 parameterization 규칙 (r2 신규)**: nuisance 후보는 가능하면 raw 차원값이
아니라 **무차원 group 으로 정의해 perturb** 한다 — 예: σ̃_p = σ_p/ρ ·
q_sense = δ_sense/τ₀ · τ_act/τ₀ · ω_max·τ₀. raw 값 (예: σ_p = 0.2 m 고정) 을 전
셀에 동일 주입하면 ρ·τ₀ 가 다른 slice 에서 물리적 상대 교란이 달라져 숨은 scale
을 다시 만든다. 무차원 group 이어야 다른 (ρ, τ₀) slice 에서도 "같은 perturbation"
이라 말할 수 있다.

## 2. 후보 목록 (우선순위순)

| # | 후보 ζ | 유형 | 근거 / 기존 결과 | 선행 조건 | 우선순위 |
|---|---|---|---|---|---|
| 1 | **ω_net = W_net/τ₀** (net 가용 수명) | 신규 governing 후보 | 유일한 신규 좌표 후보 (docs/91 §4) | **W2 정독 Q3** — W_net exogeneity. 상태 의존이면 diagnostic 강등 → 대신 net persistence 물리 파라미터 perturb | **높음** |
| 2a | 센서 **잡음** (amplitude) — σ̃_p = σ_p/ρ | nuisance | noise 가 observation 에 실제 들어가는지 미확인. latency (#2b) 와 **별도 행** — 묶으면 결과가 나와도 noise 탓인지 delay 탓인지 못 읽는다 | **W2 정독 Q4 (code audit — 실험 아님)**: noise 주입 경로 확인. 없으면 screen 아니라 구현 결정 | **높음** (Q4 통과 조건부) |
| 2b | 센서 **관측 latency** (시간) — q_sense = δ_sense/τ₀ | nuisance | latency 가 관측에 배선되는지 자체가 미확인 (T1 sense 성분) | 동일 Q4 code audit — 배선 존재 시에만 별도 후보 승격 | **높음** (Q4 통과 조건부) |
| 3 | **latency-scale collapse residual**: world 의 **실제 effect-latency mechanism 을 k배** 변화 + a → a/k²·v → v/k 보정으로 (χ,η) 유지 + **audit 로 τ_real ≈ k·τ₀ 실현 확인**. 질문 = 같은 (χ,η,λ) 의 물리적으로 다른 latency-scale 두 시스템이 같은 경계를 보이는가 | 좌표 완전성 (collapse test) | χ 의 τ² 의존이 유일 경로인지 — collapse 가설 잔여 검증 (docs/91 §4: 신규 탐색 아님). **config 의 tau0 숫자만 바꾸는 것은 좌표 라벨 변경이지 실험이 아님 — 금지** | **W2 정독 Q1** — 시뮬레이터에 움직일 수 있는 실제 delay mechanism 존재 확인. **구현 불가 시 이번 cheap screen 에서 제외** | 중간 (Q1 조건부) |
| 4 | actuator lag — τ_act/τ₀ | nuisance | 미측정 — 구동기 1차 지연은 k_f 와 물리적으로 별개 채널**인지 코드에서 먼저 확인** | 구현에 lag 노브 존재 + k_f 와의 채널 독립성 code 확인 | 중간 |
| 5 | k_f·τ 의 χ50-좌표 재확인 | nuisance | S2 robust (단 δp 좌표) | screen 이 아니라 **확증 micro-grid 단계에서만** 재측정 후보 | 낮음 |
| 6 | capturer slew — ω_max·τ₀ | nuisance | C031: ω 2.0→∞ paired 반사실 0/500 flip (hold·T0 한정) | hold-arm 밖 일반화 필요 시에만 | 낮음 |
| 7 | viability.n_samples · dt_phys | numerical | 판정/적분 해상도 — 물리 아님. dt 는 q_dec coupling 봉인 (docs/91 §3) | n_samples 는 수렴 체크 1회로 대체 | 낮음 (screen 대상 아님) |
| 8 | spawn/초기 기하 randomization 폭 | 설계 항목 | docs/37 계열 — nuisance 라기보다 B0 층화 설계 | B0 v3 §5-10 에서 직접 결정 | screen 불요 |

- τ_real 은 후보가 아니다 — audit 로그 (매 발사 기록, docs/91 §4).
- 원뿔 파라미터 (R_max, α, ρ) 는 전부 (χ, λ) 에 흡수 — 별도 후보 없음. 원뿔에서
  남는 것은 판정 해상도 (#7) 뿐.

## 3. screen → confirmatory 2-stage 진입 규칙 (**봉인 — 2026-09-07 사용자 승인**)

screen 은 6 strata (η {저·중·고} × λ 2 slice) 를 낸다. strata 별 threshold 를
사후에 유리하게 읽는 것을 막기 위해 진입 규칙을 사전 선언한다:

- **Stage 1 (cheap screen — false negative 최소화, 느슨) — 봉인 규칙 (2026-09-07)**:
  다음 중 하나면 해당 후보 confirmatory micro-grid 진입 —
  - **A (clear effect)**: 6 strata 중 **≥ 2개에서 |Δχ50| > 0.03** (= δ_χ).
  - **B (coherent near-threshold)**: 6 strata 의 signed Δχ50 이 **전부 동일 부호**
    ∧ **≥ 4/6 에서 |Δχ50| ≥ 0.02**. 0.02 는 새 효과 문턱이 아니라 **micro-grid
    한 step 수준의 coherent signal 을 cheap screen 에서 버리지 않기 위한 진입
    기준** — 최종 승격 threshold 는 여전히 0.03, 진위 판정은 confirmatory paired
    design + CI. (예: (+.024, +.026, +.023, +.025, +.022, +.027) 은 B 진입 /
    (+.024, +.003, +.007, +.001, +.005, +.009) 는 동일 부호여도 미진입.)

  방향은 strata 별 전부 기록.
- **Stage 2 (confirmatory — 엄격)**: 최종 B0 승격 판정은 **confirmatory 격자의
  사전 규칙으로만** — 효과 크기 + 방향 일관성 + uncertainty (CI) 를 함께 요구
  (격자 설계 시 별도 봉인). screen 결과는 최종 승격의 근거로 쓰지 않는다.
- **역할 분리 (r3)**: δ_χ 는 "얼마나 커야 신경 쓸 것인가"만 정의한다 — "그 효과가
  진짜인가"는 confirmatory paired design 과 CI 의 몫이다. δ_χ 하나로 screen →
  최종 승격을 결정하지 않는다.
- A·B 모두 미충족 (예: 1/6 만 통과, 방향 비일관) → 미진입 (기록만).
- **봉인 상태**: 이 규칙 세트는 δ_χ = 0.03 과 함께 2026-09-07 봉인됨 — screen 결과를
  본 뒤 threshold·entry rule 수정 금지.

## 4. δ_χ 도출 (**δ_χ = 0.03 봉인 — 2026-09-07 사용자 APPROVE**)

**정의**: δ_χ = **practically resolvable boundary-shift threshold** — 현재 경계
측정계가 실질적으로 구분할 가치가 있다고 사전에 인정하는 최소 경계 이동량.
통계 유의성 문턱이 아니고, 좌표 완전성의 증명 장치도 아니다 (§1 해석 규칙).

**측정계 3수치 (2026-09-07, 원자료에서 직접 계산 — artifacts/r2a/)**:

| 량 | 값 | 출처 |
|---|---|---|
| χ50 CI 반폭 (bootstrap 95%) | Stage 3 (n=1,360/행): 0.0042~0.0144, 중앙값 0.0083 · Stage 2 (n=4,800/행): 최대 0.0190 | stage3_readout.json 14행 · stage2_readout.json 7행 |
| 독립 재현 편차 (repeatability envelope) | λ0 (Stage3↔Stage2): max \|Δ\| = 0.0138 · λ2 (Stage3↔scout n=480): max \|Δ\| = **0.0170** | 동일 readout + scout_l2_envelope.json |
| χ 격자 해상도 | Stage 2 전체 lattice step = 0.04 · **Stage 3 경계 밴드 micro-grid step = 0.02** (cells_rule 명문; χ50 자체는 isotonic 보간이라 sub-step 추정 — 재현 편차 ≤ 0.017 < 0.02 가 실증) | stage2/stage3_protocol.json |

**Anchor**: 양성 = λ slice 분리 **0.052~0.077** (독립 확인된 최소 governing-scale
shift ≈ 0.05). 음성 = 재현 envelope 0.017. **q_dec +0.15 는 threshold sanity check
로만** — dt coupling caveat 가 있어 물리적 governing-effect benchmark 로 쓰지 않는다.

**후보 (기계 산출)**:

| 후보 | 값 | 유도 | 평가 |
|---|---|---|---|
| **A (우선)** | **0.03** | engineering resolution — 0.017 < 0.03 < 0.052, micro-grid step 의 1.5배 | envelope 를 명확히 상회 (1.76×), 최소 실질 효과의 0.58× — 설명 간단, grid 와 무모순 |
| B | 0.034 | 2 × max 재현 편차 (0.017) | 유효하나 "2배"의 근거가 임의적 — 정교해 보일 뿐 더 객관적이지 않음 |
| C | 0.04 | 2 × micro-grid step (= Stage 2 lattice step) | 보수적 — 단 양성 anchor (0.052) 와의 여유가 얇아 governing 급 효과를 놓칠 위험 |

**봉인 문안 (확정, 2026-09-07)**:

> **Practical boundary-shift threshold.** δ_χ 는 통계적 유의성 기준이 아니라 현재
> 경계 측정계에서 실질적으로 구분할 최소 효과 크기로 사전 정의한다. 값은 반복 측정
> 편차 (≤ 0.017), χ50 추정 불확실성 (CI 반폭 ≤ 0.019), 경계 격자 해상도 (micro-grid
> 0.02) 를 바탕으로 **δ_χ = 0.03** 으로 정한다 — observed repeatability envelope 를
> 명확히 상회하면서, 이미 독립적으로 확인된 최소 governing-scale shift (≈ 0.05,
> λ slice 분리) 보다 작도록 사전 설정한 값이다. |Δχ50| ≤ δ_χ 는 효과의 부재를
> 뜻하지 않으며, tested domain 에서 δ_χ 이상의 residual shift 가 검출되지 않았다는
> 뜻으로만 해석한다. 부대 조건: **screen grid 가 δ_χ 보다 충분히 조밀하도록
> Δχ ≤ 0.02 를 유지한다** — isotonic 보간으로 δ_χ 가 grid step 의 정수배일 필요는
> 없으며, 요구 사항은 screen discretization 이 practical-effect threshold 보다
> 거칠지 않은 것이다. δ_χ 는 effect-size relevance gate 이며, statistical truth
> criterion 도 coordinate-completeness proof 도 아니다.

## 5. 다음 단계 (이 문서 밖)

1. ~~δ_χ = 0.03 봉인 승인~~ — **완료 (2026-09-07)**. W1 δ_χ 작업 종결.
2. ~~W2 정독 Q1·Q3·Q4 (docs/91 §6) → #1 (Q3) · #2a/#2b (Q4) · #3 (Q1) 의 지위
   확정~~ — **완료 (2026-09-13 code audit; 상세 = docs/91 §6 + temp_research_note
   2026-09-13 노트)**. 지위 확정 결과:
   - **#1 ω_net 제외** (vacuous — capture 가 fire 동결 단일 predicate 라 포획
     수명의 인과 채널 부재; W_net = tau_lock 상수는 outcome-application 지연일 뿐)
   - **#2a/2b 제외** (noise·latency 미배선 — 구현 결정으로 재분류, B0 v3 에
     noiseless·zero-latency contract 명문화 + 층3 W10+ 이월)
   - **#3 HOLD (같은 날 2차 판정으로 정정 — 초판 "진입" 을 뒤집음)**:
     **conceptually valid but currently confounded by q_dec–dt coupling;
     defer unless a q_dec-preserving implementation is available.** τ₀→kτ₀
     에 dt 고정이면 q_dec 가 1/4↔1/6↔1/9 로 함께 움직이는데 q_dec 민감
     (1/6→1/12 에서 +0.15) 이 기실측이라 Δχ50 의 귀속 분리 불가 (blocker).
     깨끗한 형태 = (τ₀, Δt_dec, τ_deploy, τ_lock) 동시 k배 similarity
     transform — 현행 dt_phys=Δt_dec coupling 으로 원천 불가.
   - **#4 제외** (backend 에 1차 lag 노브 부재 — 즉시 가속 적용, 층3 이월)
   - #5~#8 불변 (#5 는 confirmatory 단계 전용 유지).
3. ~~cheap screen 실행~~ → **층1 최종 판정 (2026-09-13): no clean executable
   candidate after code audit — screen 생략 권고** (억지 실행보다 0 으로 닫는
   것이 정당; 최종 비준 = B0 v3 봉인 시 §5-10 "stratification 추가 변수 없음"
   조항으로). 시간 구조 재정의 (τ₀ = post-fire delayed-effect scale ·
   q_race = τ_lock/τ₀ contract-fixed · claim 형식 "at fixed q_dec and fixed
   timer ratios") 는 docs/91 v2.1 + 판정 노트
   temp_research_note/2026-09-13_layer1_verdict_* 참조.
