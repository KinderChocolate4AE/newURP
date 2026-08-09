# 74 — PIVOT PROTOCOL r3.3 (전환 기록·봉인) — 2026-08-09

**r0 = 리뷰 10 이행 · r1 = 리뷰 11 (A1~A8) · r2 = 리뷰 12 (논리 오류 2 건) ·
r3 = 리뷰 13 의 blocker 5 + leak 6~14 · r3.2 = 리뷰 15 최종 체크리스트 11 항
(stride false-negative · Stage-2 θ 고정 · same-N matched · joint trajectory feasibility ·
cell = label prevalence · m 이중계산 제거 · Phase I 문구 정합) ·
**r3.3 = 협력 채널 scope 선언 (§3.0 신설) — docs/46 실측 채널 분해를 계약에 배선하고
모든 fixed-state 량이 *차단 채널* 량임을 명시**. 이 문서는 Phase III 지도 셀을
**한 칸도 생성하지 않은 상태**에서 작성·개정됐다 (`phase3_cells_generated_so_far = 0`).
따라서 r1~r3.3 의 교정은 골대 이동이 아니라 **결과 생성 전 계약 정의 작업**이다
(감사 이력 = §0.1).**

**★ 최상위 정정 (r1)**: `2026-12-18` 은 URP 행정 마일스톤이며 연구 종료선이 아니다.
저널 증거 bar 는 기간과 무관하게 유지하고, 시간 때문에 certificate·표본·robustness 를
잘라내지 않는다. 아래 게이트는 전부 **과학적 kill/branch 게이트**다.

---

## 0. 감사 가능성

1. **pivot manifest**: `shepherd/scripts/pivot_manifest.py` →
   `artifacts/pivot_lock_2026-08-09.json`. docs/73·74·75 + 리뷰 프롬프트의 SHA-256
   (해시들의 해시 = **`protocol_hash`**), commit, Phase I 계약·결과, Phase II
   exploratory 산출물, judge/env/평가·판정 코드, **진행 중 9 런의 config·seed·launcher**,
   분포·계약 해시, `revision`, `supersedes`, `phase3_cells_generated_so_far`.
2. **불변 태그 정책 (r3, 리뷰 13 항목 14)**: 태그는 **절대 이동시키지 않는다.**
   revision 별로 이름을 분리한다 — `PIVOT_LOCK_R2_2026-08-09`,
   `PIVOT_LOCK_R3_2026-08-09`, …
   **자백**: r1 단계에서 `PIVOT_LOCK_2026-08-09` 를 `git tag -f` 로 **한 번 이동**시켰다
   (`c6e8081` → `3aec425`, Phase III 셀 0 상태). 이후 이동 없음. 기존 두 태그
   (`PIVOT_LOCK_2026-08-09` → 3aec425, `…-09b` → 9134aa8) 는 legacy 로 보존하고
   r3 부터는 위 명명 규칙만 사용한다.
3. **외부 timestamp**: embargo 가능한 read-only 등록(OSF 등)으로 같은 manifest 봉인.
4. **모든 Phase III 산출물 스탬프 필수**: `protocol_hash · code_commit · judge_commit ·
   scenario_manifest_hash · map_spec_hash · lattice_hash · generated_at`.
   스탬프 없는 artifact 는 **무효**.

**표현 규율**: `verified unread` 금지 →
> "Results had not been inspected for scientific decision-making as of the
> Phase-III lock."

**논문용 원문**
> **Phase-transition provenance.** Before any Phase-III feasibility-map output was
> generated, we archived the Phase-I contract, Phase-II exploratory artifacts, all
> active training configurations, seed manifests, analysis code, and the Phase-III
> protocol in an immutable time-stamped registration. Every subsequent Phase-III
> artifact records the corresponding protocol hash and source-code revision.
> Phase-II outputs are retained solely as exploratory records and are not used for
> Phase-III confirmatory classification or hypothesis testing.

## 0.1 정정 이력

| 판 | 계기 | 성격 | protocol_hash |
|---|---|---|---|
| r0 | 리뷰 10 | 최초 봉인 | (manifest 이전) |
| r1 | 리뷰 11 A1~A8 | 감사장치 · 정의 층분리 · Stage-2 규칙 교체 | `ef9cd4781a095072` |
| r2 | 리뷰 12 | 논리 오류 2 (sandwich 혼합 · `W=∅` 해석) + 라벨 상호배타 + Δ 층별화 | `cb038ee2a2a05892` |
| **r3** | **리뷰 13** | **blocker 5 (L^reach 알고리즘 · C_N 집계 · not-boxed · lattice · interaction estimand) + leak 6~14** | (r3 manifest) |
| r3.2 | 리뷰 15 | 최종 체크리스트 11 항 (stride 금지 · θ_S2 고정 · same-N · joint feasibility · label prevalence · m=1) | `069cade39836cdd1` |
| **r3.3** | **자체 감사 (docs/76 선행연구 조사 중 docs/46 재발견)** | **협력 채널 scope 선언 §3.0 정밀화 — 측정된 채널 3 종 대장, fixed-state 량의 채널 귀속 명시, negative claim 에 채널 한정 강제, docs/46 §4.2 사전선언을 Stage-2 secondary 로 승계** | 아래 manifest |

r0~r3.2 의 manifest·태그는 삭제하지 않는다. **Phase III 셀은 전 구간에서 0 개.**

## 1. Phase I — 원 spine 과 결과 (변경 금지·소급 재해석 금지)

- 가설: 동결 TRAIN 분포·동결 학습계약에서 협력 shaping 학습 MARL 이 손설계 기준선보다
  비파괴 net 포획률을 높인다.
- primary: held-out **IID 10000..10299 (n=300) paired**, Δ_net (docs/63 r2).
- 기준선: hold / arc scripted (TRAIN 선택 c5, p_net 0.110).
- 결과: LL **0/300** (SHAPING 0/164 · FREE 0/136) · LS **49/300 = 0.163**
  (FREE 0.36 · **SHAPING 0/164**) · hold SHAPING **0/122**.
- 진행 중·미열람: docs/71 r1 ablation 9 런 — primary·대역·라벨·판정식 **불변**,
  기존 `regime_of` 로 완주·판정, **null 도 보고**.

## 2. Phase II — 전환 trigger (exploratory 봉인)

산출물 `shepherd/scripts/shaping_ceiling.py` · `results/shaping_ceiling.{json,png}`
(`status = EXPLORATORY DIAGNOSTIC`). **hypothesis generator 이상으로 사용 금지.**

| # | 편향 |
|---|---|
| **B1 ★** | **counterfactual trajectory inconsistency** — 반응형 공격자인데 hold 궤적의 `x_t` 에 limiter 를 teleport. 실제로 그 위치에 있었다면 공격자는 그 전에 다른 궤적을 탔다 (**attacker response causality 절단**) |
| **B2 ★** | **common-mode bias** — Phase I 과 같은 judge·같은 모델링 가정 → 독립 구현 cross-check 필수 (§3.7) |
| B3 | snapshot 선택 편향 (top-`V_0` = finisher-alone 기하가 좋은 시각) |
| B4 | 후보 껍질 제한 (future choke point 배제 가능) |
| B5 | scripted aiming = favorable oracle |
| B6 | max over time/snapshot = optimistic selection |
| B7 | witness family 구성비가 결과를 만든다 |
| B8 | 선언된 (τ, r_kill, θ) 가 구조를 만든다 |
| B9 | 유한 위트니스 (2000) · 무잡음 judge |
| B10 | teleporting 배치 = relaxed static-placement |

철회 문장 4 건 (docs/73 §2) 사용 금지.

---

# 3. Phase III — 정의·계약 (결과 열람 전 고정)

## 3.0 협력 채널 scope 선언 (셀 생성 전 고정 — docs/77 [B], r3.3 정밀화)

**r3.3 정정**: 이전 문구 "협력 채널은 **하나**" 는 부정확했다. 시스템에는 협력 채널이
**최소 셋** 있고 **셋 다 이미 계측됐다** (`docs/46_channel_split.md`, 2026-08-01,
`shepherd/scripts/channel_split.py`). 정확한 진술은 —

> **fixed-state certificate 는 정의상 채널 (i) 만 측정한다.**

이건 근사가 아니라 **항등식**이다. docs/46 의 채널 (i) 정의는 *"같은 상태·같은 CRN seed 에서
limiter 유/무로 `v_shot` 을 두 번 호출한 차이"* 이고, `V^rel_{<=N}(e,t) − V_0(e,t)` 는
**그것을 배치에 대해 최적화한 값**이다. 상태를 고정하는 순간 (ii)·(iii) 은 원리적으로
측정 불가능하다 — 둘 다 공격자가 시간에 걸쳐 반응해야 발생하는 효과이므로.

### 3.0.1 협력 채널 대장 (measured — docs/46)

| 채널 | 기전 | docs/46 실측 | 부호 | fixed-state (§3.3 sandwich) | 4B closed-loop | C5 MARL |
|---|---|---|---|---|---|---|
| **(i) 봉쇄 blockade** | kill-sphere 가 공격자 도달 가속집합에서 탈출 방향을 제거 | 선언 `r_kill=0.75` 에서 **Δbest = 0.0000** (차단률 중앙값 0) · `r_kill=3.0` hold 에서 **+0.0101** | + | **credit — 이것만** | credit | credit |
| **(ii) 횡압 lateral push** | 반응형 공격자가 옆으로 밀리며 `v⊥`·조준오차 증가 | `v⊥` 0.44→**7.27 m/s** · `ψ` 0.6°→**28°** · 평균 `v_shot` 0.394→**0.036** | **−** | **측정 불가** (상태 고정) | credit | credit |
| **(iii) 체류 dwell** | 공격자를 발사 밴드 안에 오래 붙잡음 | 밴드 체류 9→**55 스텝 (6배)** | + (원리상) | **측정 불가** (시간 고정) | credit | credit |
| (iv) 정보 information | 조준/감지 지연 단축 | **미구현** | — | 없음 | 없음 | 없음 (docs/75 §7 P4) |

**채널 (i) 은 단조롭지 않다**: 과봉쇄로 `n_feasible = 0` 이 되면 `boxed_in` 이 서고
`g_theta = 0` (clean fire 금지) 이다 (§3.2). 즉 containment 는 **의도적으로 성공으로
치지 않는다** — 이것도 scope 선언이며, 논문에 명시한다.

### 3.0.2 계약에 미치는 귀결 (4 항)

1. **sandwich 전체가 blockade-channel 량이다.** `V_0 · V^rel · V^reach ·
   L^reach_{<=N,clean} · U^rel` 은 전부 채널 (i) 에 대한 값이다.
2. **`L^reach` 는 협력 가치의 보수적 하한이다.** (ii)·(iii) 을 credit 하지 않으므로
   실제 시스템이 달성 가능한 값보다 낮다 → **COOP certificate
   `U^rel_{<=1} < θ <= L^reach_{<=N,clean}` 는 그대로 sound 하며 오히려 강해진다.**
3. **`U^rel_{<=N} < θ` 는 closed-loop 불가능을 함의하지 않는다.** 채널 (i) 에 대한
   상한일 뿐이다. → `LOCAL` 한정이 필요한 **두 번째 이유**이며, 여기에 **채널 한정**도
   필요하다 (§3.4·§5·§6·§7).
4. **`L^ctrl < L^reach` 가 정상적으로 발생할 수 있다.** 채널 (ii) 가 실측 음수이므로
   (i)+(ii)+(iii) 의 합이 (i) 단독보다 나쁠 수 있다. 이것이 §3.3 "순서관계 주장 금지" 의
   **물리적 근거**다 (종전엔 규칙으로만 선언했다).

### 3.0.3 사전 예측 (셀 생성 전 기록 — 사후 합리화 방지)

docs/46 은 채널 (i) 이 `r_kill≈0.75` 에서 0, `≈3.0` 에서 발현된다고 계측했다.
`kappa = r_kill/rho` 가 core 축이므로 **지도는 `kappa` 축을 따라 구조를 가질 것으로
예측한다** — 낮은 `kappa` 에서 `p_INF` 지배, 높은 `kappa` 에서 `p_COOP`/`p_SINGLE` 출현.
이 예측이 빗나가도 정의·축·판정식은 바꾸지 않는다 (§7). **채널이 켜지는 `kappa` 좌표가
곧 kill radius 에 대한 model-conditional design requirement curve 다.**

### 3.0.4 읽는 법 (강제)

COOP 셀 부재는 **"협력이 불가능하다" 가 아니라 "차단 채널에서 협력이 certifiably
필요한 영역이 없다"** 로만 읽는다. 채널이 셋인 것은 결과가 아니라 **시스템의 사실**이고,
certificate 가 하나만 보는 것은 **scope 선언**이다. (결과 후에 붙이면 변명이 된다 —
셀 생성 전에 넣는다.)

부분 실증 가능 범위: `kappa` 가 core 축이므로 **"채널을 강화해도 안 열린다"** 는 보일 수
있다 — 채널의 *종류*가 아니라 *세기*에 대한 강건성이다. 채널 *종류*에 대한 일반화는
**할 수 없다**.

## 3.1 reference encounter 와 시간축 (blocker 1·2 — `T_s` 모호성 제거)

지도의 모든 fixed-state 량은 **reference rollout 의 시각**으로 정의한다.

```
reference controller pi_ref = hold  (결정론적·비학습. 사전 고정)
reference episode      e ~ D_z^ref  (파라미터 점 z 의 시나리오 분포)
decision window        T_eval(e) = reset 부터 종료까지의 **모든** 스텝
                       (top-V_0 등 어떤 사후 선택도 금지 — B3/B6 대응)
limiter admissible set D_i^reach(e,t) = { limiter i 의 초기 상태에서 시각 t 까지
                       실제 동역학(a_lim, v_lim, NK 존, 충돌 제약)으로 도달 가능한 center }
witness set            reference rollout 의 시각 t 상태 x_t 에서 생성
```

해석: *"이 reference encounter 가 이 상태에 도달한 시각까지 limiter 가 물리적으로 그
위치에 갈 수 있었다고 가정하면, 그 고정 기하에서 N 기가 충분한가?"* — attacker
counterfactual reaction 이 제거된 **local mechanism certificate** 이지만 시간적으로는
일관된다. `(x, T_s)` 표기는 폐기하고 `(e, t)` 를 쓴다.

**compute 절감 규율 (r3.2 — false negative 불가 screening)**: stride 스캔은
**금지**한다 (`m` tick 짜리 기회를 통째로 놓칠 수 있다). 대신:

```
모든 step t in T_eval(e) 에서  **cheap sound screen** 을 계산한다:
    screen(e,t) = 1[ U^cheap_{<=N}(e,t) >= theta ]
    U^cheap = unblockable-bad-mass 상한 (§3.6-1) = V^rel_{<=N} 의 sound upper bound
  screen = 0  =>  V^rel_{<=N} < theta  =>  L^reach <= V^reach <= V^rel < theta
                  =>  C_N(e,t) = 0 이 **보장**된다 (false negative 불가)
비싼 계산(L^reach / U^rel / solver)은 screen = 1 인 step + 그 ±10 tick 이웃에만 적용
```
즉 **필요조건 스크린은 전 스텝**, 비싼 계산만 선별 — 계산 배분이며 선택 가설을
만들지 않는다.

## 3.2 clean-fire predicate 를 certificate 안에 넣는다 (blocker 3)

원 시스템의 게이트는 `v_shot >= theta` **AND `not boxed_in`** 이었다. r2 까지의
certificate 는 비율만 봤다 — 구를 많이 놓아 bad witness 를 지우면 비율은 오르지만
boxed 상태가 되어 **실제 clean fire 가 금지될 수 있다.**

```
g_theta(x, P) = 1[ v_shot(x, P) >= theta  AND  NOT boxed(x, P) ]
```

- **constructive lower 는 반드시 `g_theta = 1` 인 배치에서만 유효**:
  `L^reach_{<=N,clean}(e,t)` = 도달가능 배치 중 **not boxed** 를 만족하는 것에서 얻은
  최대 coverage.
- **upper certificate 는 boxed 제약을 무시(완화)해도 sound**: boxing 을 허용하는 것은
  방어측에 더 유리한 relaxation 이므로 `U^rel_{<=N} < theta` 면 clean 제약을 넣어도
  당연히 불가능하다. **이 비대칭을 명시한다.**

## 3.3 층 분리와 sandwich (r2 유지 + r3 정밀화)

```
Local fixed-state problem  (동일 (e,t) 에서만 정의)
--------------------------------------------------
V^rel_{<=N}(e,t)          최대 N 개 static kill sphere, 연속 admissible domain D 어디든
V^reach_{<=N}(e,t)        center 를 D_i^reach(e,t) 로 제한
L^reach_{<=N,clean}(e,t)  명시적 실현가능 배치 + g_theta=1 이 달성한 값 (constructive)
U^rel_{<=N}(e,t)          V^rel 의 sound upper bound (boxed 무시 = 낙관 relaxation)

  => 고정 상태 문제 안에서만:
     L^reach_{<=N,clean} <= V^reach_{<=N} <= V^rel_{<=N} <= U^rel_{<=N}

Closed-loop problem  (별도 층 — 위 sandwich 와 섞지 않는다)
----------------------------------------------------------
L^ctrl_{<=N}(x0; pi_c)    반응형 attacker 가 있는 원 환경에서 명시적 controller 가
                          달성한 값. **U^rel 과의 순서관계 주장 금지.**
```

**채널 귀속 (r3.3 — §3.0.2)**: 위 fixed-state 량 `V_0 · V^rel · V^reach · L^reach · U^rel`
은 **전부 채널 (i) 봉쇄** 에 대한 값이다. `L^ctrl` 만이 (i)+(ii)+(iii) 을 함께 반영한다.
docs/46 이 채널 (ii) 를 **음수**로 실측했으므로 `L^ctrl < L^reach` 는 정상적으로 발생할 수
있다 — 이것이 두 층을 하나의 sandwich 로 섞지 않는 **물리적 근거**다 (종전엔 규칙으로만
선언했다). `L^ctrl < L^reach` 관측을 `L^reach` 계산의 버그 신호로 읽지 않는다.

## 3.4 라벨 (상호배타 · **LOCAL** 명시 — leak 12 · **채널 상속** r3.3)

```
FREE                            : V_0 >= theta
CERTIFIED LOCAL-SINGLE-NEEDED   : V_0 < theta <= L^reach_{<=1,clean}
CERTIFIED LOCAL-COOP-NEEDED     : U^rel_{<=1} < theta <= L^reach_{<=N,clean}
CERTIFIED LOCAL-INFEASIBLE-N    : U^rel_{<=N} < theta
AMBIGUOUS                       : 그 외 (지도에 그린다)

N_req = 0          : V_0 >= theta
N_req = k (k>=1)   : U^rel_{<=k-1} < theta <= L^reach_{<=k,clean}
그 외              : **UNRESOLVED** (모든 상태에 N_req 가 존재하지 않는다)

Delta^rel_N = V^rel_{<=N} - V^rel_{<=1}     Delta^reach_N = V^reach_{<=N} - V^reach_{<=1}
Delta^ctrl_N = J(pi_N) - J(pi_1)   ← 특정 controller 간 경험적 차이 (optimal 아님)
W_{2:N} = { (e,t) : N_req in [2,N] }   (UNRESOLVED 불포함)
```

**LOCAL 을 붙이는 이유**: `U^rel_{<=1}(e,t) < theta` 는 *"이 상태의 static shaping
문제를 1 기로 못 푼다"* 이고, *"어떤 1-agent closed-loop 정책도 이 에피소드를 못 푼다"*
가 아니다. 이 구분이 논문의 핵심 방어선이다.

**채널 상속 (r3.3 — 라벨 이름을 늘리지 않는 대신 강제 규칙으로 둔다)**: 위 라벨은 전부
§3.0 의 **채널 (i) 봉쇄 scope** 를 상속한다. 라벨을 **산문으로 옮기는 순간 채널 한정을
반드시 함께 쓴다.**

```
LOCAL-INFEASIBLE-N  를 문장으로 쓸 때:
  ✅ "even N cooperative limiters cannot establish the local firing condition
      **via the static blockade channel**"
  ❌ "N 기로는 불가능하다"            (채널·상태 한정 둘 다 누락)
  ❌ "협력이 불가능하다"               (금지 — §7)
```

**명명 결정 기록**: `LOCAL-BLOCKADE-INFEASIBLE-N` 으로 개명하는 안을 검토했으나
**기각**했다 — 이름 길이와 문서·코드 교차참조 churn 대비 이득이 작다. 대신 (a) 정의부
§3.0, (b) 이 상속 규칙, (c) §5 분기 문구, (d) §6 서술 규칙, (e) §7 금지문장의 **다섯
군데에 중복 배치**해 한 곳이 조용히 실패해도 남게 했다 (r2 패치가 조용히 실패한 전례 —
docs/73 §1.4 항목 7).

**핵심 한 줄**: `U^rel_{<=1} < theta <= L^reach_{<=N,clean}` — 왼쪽은 1 기를 이상적으로
배치해도 안 된다는 상한 certificate, 오른쪽은 실제 도달 가능하고 clean 한 N 기 배치가
된다는 constructive certificate. 메인 논문은 이 한 줄로 "왜 N>1 인가" 를 답하고
`Delta_coop` 를 앞세우지 않는다.

## 3.5 measure (R) 와 **path witness** (leak 7)

- **witness = 완전한 admissible trajectory 표본 + 종단 상태 (path witness).**
  endpoint 만으로 정의하면 `B_j = gamma_j (+) Ball(r_kill)` 이 의미를 잃는다 (같은
  endpoint 로 가는 다른 경로가 남는다). `v_shot` = **feasible path witness 의 가중
  coverage 비율**로 부른다.
- `v_shot` 은 **(R) robust coverage metric**. probability 라 부르지 않는다.
- **θ 를 상수로 방어하지 않는다**: 핵심 산출물은 연속 surface
  `L^reach_{<=N,clean}(z)`, `U^rel_{<=N}(z)` 이고 θ ∈ {0.80, 0.85, 0.90, 0.925, 0.95}
  슬라이스로 보고한다. θ = robustness acceptance level.
- 검증: witness family 구성비 명시 · 수렴 **2k → 8k → 32k** · allocation 민감도 ·
  동일 (e,t) paired 비교 · `delta_t = dt/tau` 는 **수치 검증수**로 별도 확인.

## 3.6 certificate hierarchy 와 solver 의 지위 (leak 6)

**계층 (싼 것부터, 닫힌 셀엔 상위 단계 미적용, 셀별 사용 수준 공개)**

1. **unblockable bad mass (upper, 최저비용)**: `B_j ∩ D = ∅` 인 bad path witness 의
   mass `U`, captured-good mass `G` → `v_max <= G/(G+U)`.
2. **continuous outer relaxation (upper)**: center domain 을 cell `C_q` 로 분할,
   낙관 incidence `A^outer_{jq} = 1 if C_q ∩ B_j != ∅` + good witness 불멸 가정 →
   `U^rel_{<=N} = G/(G + B - B_removable,N)`. cell refinement 로 optimism 감소 →
   **certificate convergence figure**.
3. **reachable constructive lower (lower, 4A)** — §3.7.
4. **closed-loop realizability (4B)** — §3.7. certificate 아님.

**finite-candidate exact MILP 는 continuous upper certificate 가 아니다** (leak 6).
후보집합 `C ⊂ D` 이면 `V^rel_{C,<=N} <= V^rel_{D,<=N}` 이므로:
> **Failure to reach θ in the finite-candidate exact problem does not certify
> continuous-domain infeasibility.**

MILP 의 역할 = Phase II greedy audit · candidate discretization audit · relaxed
constructive search · continuous solver warm start. **solver/audit auxiliary** 로
분류하고 certificate hierarchy 에 넣지 않는다. (θ 이상을 달성하면 그것은 relaxed
문제의 **lower** bound 로 유효하다.)

## 3.7 4A/4B 분리 (blocker 1)

**4A — fixed-state reachable constructive lower (certificate)**
```
for each (e,t):
  D_i^reach(e,t) 계산 (실제 동역학·NK·충돌)
  후보 = 예측 escape path 의 blocking tube ∩ D_i^reach
  agent-candidate bipartite assignment → threshold-feasibility 로 center 선택
  **같은 고정 witness set** 에서 v_shot 평가 + not boxed 확인
  ★ **joint trajectory feasibility 검증 (r3.2 — 필수)**: 선택된 center 들에 대해
    **시간 매개화된 limiter 궤적 N 개를 실제로 구성**하고, 전 시간구간에서
    가속·속도 상한 · NK 존 · **limiter-limiter pairwise 충돌**을 **동시에** 만족해야만
    constructive witness 로 인정한다. (개별 도달가능성 `D_i^reach` 의 곱집합은
    joint feasibility 를 보장하지 않는다 — 이걸 빼면 `L^reach` 가 sound lower bound 가
    아니다.)
  성공 시  L^reach_{<=N,clean}(e,t) >= theta
           (= sandwich 의 **constructive lower bound** 이며 동시에
            cooperative-necessity certificate 의 **오른쪽 항**)
```
**4B — closed-loop realizability (external check, certificate 아님)**
```
같은 constructive rule 을 반응형 env 에서 rollout (bang-bang/PD 추종, 5~10 tick replan)
실제 judge 가 clean fire 를 내면  L^ctrl_{<=N}(x0; pi_c)
```
4A 가 certificate 이고 4B 는 실현 검사다. **4B 값을 sandwich 에 넣지 않는다.**
★ 4A·4B 는 MARL 보다 **먼저** 한다. constructive controller 가 못 만드는 협력 기회를
RL 에게 만들라고 요구하지 않는다.

**독립 judge cross-check (B2, leak 13 — boundary-aware)**: cone containment ·
witness kill · threshold feasibility 를 독립 구현으로 재계산하고 **signed geometric
margin** `m` 을 비교한다. 판정: `|m_1 - m_2| <= eps` (eps = 1e-6 m, 무차원량은 1e-9).
predicate 불일치는 **적어도 한 구현이 `|m| <= eps` 인 boundary case 에서만** 허용하고,
**boundary 에서 먼 곳의 불일치가 1 건이라도 있으면 지도 중단·버그 감사.**

## 3.8 파라미터 격자 (blocker 4 — master lattice 선봉인)

- 결과 전에 **master lattice `Z_master`** 를 충분히 조밀하게 생성하고 **hash 를
  manifest 에 포함** (`lattice_hash`). 모든 점을 계산할 필요는 없다.
- adaptive 알고리즘은 **`Z_master` 중 어느 점을 다음에 평가할지만** 고른다
  (결정론적 정책): ① coarse subset 평가 → ② 서로 다른 certified label 이 인접한 edge
  식별 → ③ 그 edge 의 master-neighbor/midpoint 평가 → ④ CI 폭 또는 cell diameter 가
  사전 threshold 이하가 될 때까지 반복.
- **Stage-2 점은 `Z_master` 안에서만** 고른다.
  → adaptive **compute allocation** 은 허용, adaptive **hypothesis-space 생성** 은 금지.

## 3.9 무차원화 (leak 8 — 축 발견 금지, reduction validation 만)

**"결과 보고 축 추가" 를 폐기한다.** 순서:
1. governing equation·기하에서 **전체 dimensionless group 을 분석적으로 도출**
   (Buckingham-Π 완성) 후 **전부 기록**.
2. 그중 **2~3 개만 plotted axes** (core), 나머지는 **fixed conditioning variables**.
3. iso-Π test 는 **축 발견법이 아니라 reduction validation**.

주의: `lambda = L_axial/rho`, `R_standby/rho` 등은 절대값을 고정한 채 `rho` 를 바꾸면
**자동으로 변한다.** 따라서 `(chi,kappa,mu,eta)` 만 같고 `lambda` 가 다른 두 시스템의
결과가 다른 것은 **당연할 수 있다** — collapse 실패의 근거로 쓰기 전에 conditioning
변수를 먼저 확인한다.

## 3.9b parameter cell 은 **단일 라벨이 아니다** (r3.2, 리뷰 15 항목 5)

state-level 라벨은 상호배타지만, 한 파라미터 점 `z` 에서는 20~300 개 독립 episode 가
서로 다른 라벨을 낸다. 따라서 **셀 하나를 한 색으로 칠하는 규칙을 두지 않는다.**

```
각 z 에서 보고하는 것 = 라벨 **prevalence 벡터**
    p_FREE(z), p_SINGLE(z), p_COOP(z) (= p_C), p_INF(z), p_AMB(z)
핵심 surface = **p_C(z)** 와 **p_AMB(z)** (둘을 나란히 보고한다)
```
> **State-level labels are mutually exclusive; parameter cells report their prevalence
> under `D_z^ref`, not a single categorical truth label.**

Fig 6 은 `p_C` surface + `p_AMB` surface (또는 stacked prevalence) 로 그리고, 단일
카테고리 지도로 그리지 않는다. 분기 판정(§5)도 prevalence 로 한다.

## 3.10 표본 정책

| 대상 | 독립 realization |
|---|---|
| coarse cells | 20~30 |
| boundary candidate cells | 순차 60~100+ |
| Stage-2 최종 3 점 | 100~300 |
| MARL 평가 | 수백 paired episodes |

**통계단위 = episode** (path witness 를 독립표본으로 bootstrap 금지). CPU geometry 는
GPU 학습과 병렬.

---

# 4. Stage-2 (C5) confirmatory 계약 — r3 완성

## 4.1 state → episode 집계 (blocker 2)

```
C_N(e,t)   = 1[ U^rel_{<=1}(e,t) < theta_S2 <= L^reach_{<=N,clean}(e,t) ]  (state level)
persistence: **m = 1** (= 존재). r3 의 m=3 은 **폐기**한다 — 근거 확인 결과
             `tau = 0.30` 은 **"커밋에서 포획 판정까지의 지연"** 이고 분해가
             flight 0.15 + **sense 0.10 + decide 0.05** 이므로 sense/decide latency 가
             **이미 reachable-set horizon 안에 있다**. 여기에 0.15 s persistence 를
             더 요구하면 **latency 이중계산**이다 (m4_config.M4_PROVENANCE 원문 확인).
C_N^ep(e)  = 1  iff  T_eval(e) 안에서 C_N(e,t)=1 인 step 이 **하나 이상** 존재
p_C(z)     = P_{D_z^ref}( C_N^ep(E) = 1 )
secondary  : opportunity **dwell-time 분포** (연속 성립 tick 수) — 기술 통계로 보고하며
             판정에 쓰지 않는다
```
`p_C` 는 **prevalence under the pre-specified scenario distribution** 이며 실세계
encounter probability 가 아니다.

**★ Stage-2 문턱 고정 (r3.2)**: `theta_S2 = 0.90` — 원 시스템 동결값이다.
`C_N`·`p_C`·`z_B`·matched control **전부 이 하나의 θ 로만** 계산한다.
θ ∈ {0.80, 0.85, 0.925, 0.95} 슬라이스는 **sensitivity 보고 전용이며 Stage-2 점 선택·
라벨 판정에 사용 금지** (지도를 본 뒤 협력 영역이 가장 큰 θ 를 고르는 자유도 제거).

## 4.2 eligibility 와 점 선택 (leak 10)

```
CI       = Clopper-Pearson **one-sided 95% lower bound**, 단위 = episode
eligible : LCB95^CP( p_C(z) ) > p_min = 0.05   AND   관측 성공 episode 수 >= 5
z_B      = argmax_{z in Z_master, eligible} LCB95^CP( p_C(z) )
tie      = lexicographic (chi, kappa, mu, eta, N)
```
> **If no grid point satisfies the eligibility criterion, the cooperative Stage-2
> learning experiment is not conducted.** (억지로 돌리지 않는다.)

## 4.3 matched controls (leak 11)

```
**동일 N · 동일 θ 강제 (r3.2)**: `N_FREE = N_HARD = N_B` 이고 세 regime 모두
`theta_S2 = 0.90`. 그래야 `Gamma` 에 **team-size-dependent learnability** 가 섞이지 않는다.
거리 최소화는 **같은 N 부분집합 안에서만** 수행한다.

d(z, z_B) = max_k | (z_k - z_B,k) / (z_k,max - z_k,min) |   (normalized L_inf,
            k 는 연속 Π 좌표만 — N 은 거리에 넣지 않고 **동일값으로 고정**)
FREE control = { z : N = N_B, 라벨 prevalence 상 FREE 지배 } 중 d 최소
HARD control = { z : N = N_B, LOCAL-INFEASIBLE-N 지배 } 중 d 최소
tie = lexicographic (chi, kappa, mu, eta)
```
**AMBIGUOUS 를 high-difficulty control 로 쓰지 않는다.**

## 4.4 primary estimand (blocker 5)

**comparator 는 reachable 1-limiter 가 아니다** (그러면 learning effect 와 team-size
effect 가 섞인다). `N=1` 은 **mechanism necessity control** 이고, RL 이득의 비교 대상은
**같은 N 기의 비학습 controller** = §3.7 의 constructive controller 를 **freeze** 한
`B_N` 이다.

```
regime r in {COOP, FREE, HARD}
delta_r = p_net^{MARL_N, r} - p_net^{B_N, r}
Gamma   = delta_COOP - ( delta_FREE + delta_HARD ) / 2          ← primary estimand
primary success : LCB95( Gamma ) > 0
                  (training seed 최상위 hierarchical bootstrap, nested paired episode,
                   B = 10000, rng = 7)
secondary (mechanistic) : p_net^{N} - p_net^{1}    (N=1 대조)
```
점당 학습 시드 **8~10 권장 (5 최소)**, held-out 수백 paired, 기준선 = hold ·
arc scripted(historical) · `B_N` · **reachable 1-limiter** · oracle `U^rel` envelope.
0 카운트는 binomial 상한 병기. 지도 경계에도 bootstrap band.

**secondary (channel) — docs/46 §4.2 사전선언 승계 (r3.3)**

docs/46 §4.2 는 **결과를 보기 전에** 학습 목표와 실패 기준을 선언해 두었다. 그 선언을
Phase III Stage-2 의 **기전 secondary** 로 그대로 승계한다 (재선언이 아니라 승계 —
원문 날짜 2026-08-01).

```
ch_i (e,t)  = v_shot(with limiters) - v_shot(no limiters)     동일 (e,t) · 동일 CRN seed
              (= 채널 (i) 봉쇄 이득. shepherd/scripts/channel_split.py 의 d_cut)
              boxed_in 스텝은 평균에서 제외한다 (docs/46 §1 규율).
ch_ii       = psi (finisher 조준 오차) · v_perp — 짝지은 롤아웃에서 hold 대비
              (= 채널 (ii) 횡압 손실)
dwell       = 발사 밴드 내 체류 스텝 수                        (= 채널 (iii))

보고 형식   세 값을 regime 별로 **함께** 보고한다. 협력 이득의 부호가 어느 채널에서
            왔는지 분해되지 않으면 Gamma 의 해석이 불가능하다.
```
> **판정 사용 금지**: 위 세 값은 **기술 통계·기전 해석 전용**이며 primary `Gamma` 판정에
> 넣지 않는다. docs/46 §4.2 의 "hold 대비 최선·평균을 둘 다 개선 못하면 협력 순이득
> 없음" 기준은 **`v_shot` 위에서 선언된 docs/46 의 기준**이고, Phase III primary 는
> `p_net` 위의 `Gamma` 다. **두 기준을 합치거나 유리한 쪽을 골라 쓰지 않는다.**

**primary 는 하나다** (`Gamma`). Phase I 의 평가 계약(대역 생성·paired 구조·p_net
정의)은 유지하되 Phase III 의 hypothesis test 는 이 estimand 다.

---

# 5. 반증 조건 (branch, kill 아님)

1. `W_{2:N} = ∅` → **negative 직행 금지.** 세 갈래로 분기하고 **해당 bound 가 직접
   지지하는 주장만** 한다:
   **(A) single-agent sufficiency** (`V_0 < theta <= L^reach_{<=1,clean}` 지배 + coop
   셀 부재) → "no certified need for multi-agent interdiction" ·
   **(B) local mechanism infeasibility** (`U^rel_{<=N} < theta` 광범위) → "even N
   cooperative limiters cannot establish the local firing condition **via the static
   blockade channel**" (**채널 한정 필수 — r3.3 §3.0.2-3.** 이 한정을 빼면 docs/46 이
   실측한 채널 (ii)·(iii) 의 존재와 **우리 자신의 자료가 모순된다**) ·
   **(C) unresolved certificate gap** (AMBIGUOUS 다수) → **결론 없음, negative claim
   금지.** A/B 에서만 negative-result 논문으로 분기하고 협력 C5 를 취소한다.
2. band 는 열리는데 MARL 이득 0 (`LCB95(Gamma) <= 0`) → `local feasibility !=
   learnability` 로 분리 보고. `B_N` 이 band 에서 성공하면 그것이 결과 → Paper 2.
3. exact/reachable 에서 `N_req >= 2` → Phase II 의 "모든 교차가 1 기" 관측 **철회**
   (호재: 진짜 cooperative necessity).
4. `v_shot` 이 witness allocation/해상도에 유의 의존 → **지도 즉시 중단.**

## 5.1 branch 는 protocol 수정이 아니라 **새 protocol** (leak 9)

§7 은 "결과를 본 뒤 축·measure 변경 금지" 인데 §3.9/§5-4 는 변경을 요구한다 — 모순을
다음으로 해소한다:

> 반증조건이 발동하면 **현 Phase III 는 종료(falsified)** 이고, 축·measure·정의를 바꾼
> 후속 연구는 **새 `Phase III-B` protocol 을 새 `protocol_hash` 로 사전등록한 뒤**
> 다시 시작한다. **현 protocol 을 수정해 계속 이어가지 않는다.**

# 6. 논문 서술 규칙

> Phase I: preregistered controller comparison produced null results.
> Phase II: post-hoc mechanism diagnosis identified a potential feasibility mismatch.
> Phase III: a prospectively specified parameter study tested that hypothesis.

**Phase I 결과 인용 원문** (r3.2: primary 는 **overall paired Δ_net** 이지
shaping-regime rate 가 아니다 — 종전 문구가 틀렸다. 또한 LL 은 기준선보다 나빴으므로
"null" 보다 **"did not support the preregistered superiority claim"** 이 정확하다)
> Under the original preregistered nominal contract, the intervention **did not
> support the preregistered superiority claim on the prespecified paired net-capture
> endpoint** (held-out IID set, lexicographic criteria; docs/63 r2). This outcome is
> retained as a confirmatory result of Phase I.
> It **motivated, but does not validate**, the subsequent feasibility analysis, whose
> definitions and hypotheses were specified prospectively after the Phase-I contract
> had been locked.

Phase III 성공 시에도 "Phase I null 의 원인이 증명됐다" 로 쓰지 않는다 →
**"Phase III offers a mechanism-consistent explanation of the Phase-I null."**
용어는 **local certified cooperative opportunity** 를 쓴다 (LOCAL 생략 금지).
"requirement" 는 hardware/context anchor 확보 후에만, 그 전엔 **model-conditional
design envelope / parametric requirement curve**.

**채널 서술 규칙 (r3.3)**: 논문은 **협력 채널 분해를 방어가 아니라 기여로** 제시한다.

> We decompose cooperative influence on the firing condition into a **static blockade
> channel**, a **lateral-push channel** that degrades the shooter's aim, and a **dwell
> channel**, and we measure all three (docs/46). The fixed-state certificate is exact
> for the blockade channel and, by construction, blind to the other two. Consequently
> our constructive lower bound is **conservative** with respect to cooperative value,
> while our upper certificate bounds **only** the blockade channel.

`certificate 가 채널 하나만 본다` 는 사실을 **먼저 우리가** 말한다. 리뷰어가 먼저
말하면 한계이고, 우리가 먼저 말하면 설계다.

spine = *Feasibility-First Design of Cooperative Single-Shot Counter-UAS
Interception under Deployment Latency*.

# 7. 이후 금지 사항

- 지도 결과를 본 뒤 §3 정의 · §3.8 lattice · §3.9 축 · §3.5 measure 선언 ·
  §4 선택규칙·estimand · §5 반증조건을 **수정**하는 것. (변경이 필요하면 §5.1 대로
  **새 protocol** 을 등록한다.)
- Phase II 산출물을 confirmatory 로 인용.
- docs/71 블록의 primary·대역·라벨·판정식 변경, 또는 그 결과를 Phase III 로 재해석.
- `protocol_hash`·`lattice_hash` 스탬프 없는 Phase III 산출물을 결과로 사용.
- **감사 태그 이동** (§0 항목 2).
- 시간(12/18) 을 이유로 certificate·표본 수·robustness bar 를 낮추는 것.
- `L^ctrl` 을 fixed-state sandwich 에 넣는 것 / `L^reach` 를 closed-loop rollout 으로
  대체하는 것 (blocker 1 재발).
- **채널 한정 없이 negative claim 을 하는 것 (r3.3)**. 금지 문장 —
  "협력이 불가능하다" · "N 기로는 불가능하다" · "cooperation provides no advantage" ·
  "협력 채널은 하나뿐이다". `U^rel_{<=N} < theta` 가 지지하는 것은 **차단 채널에 한한
  local 불가능**뿐이다 (§3.0.2-3 · §3.4 · §5-1B).
- **`L^ctrl < L^reach` 관측을 `L^reach` 의 버그로 처리하는 것** — 채널 (ii) 가 음수인
  이상 정상 현상이다 (§3.3 채널 귀속).
- docs/46 §4.2 의 `v_shot` 기준과 Phase III 의 `p_net` 기준 `Gamma` 를 **합치거나
  유리한 쪽을 골라 쓰는 것** (§4.4 secondary(channel)).
