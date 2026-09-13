# 97 — A-family 범위 선언 + worst-case 평가 프로토콜 (**초안 — W3 전 봉인 대상**)

- **일자**: 2026-09-13 · **지위**: **draft**. docs/90 W2 Task 2 항목
  ("A-family 범위 선언 문서 초안" + "worst-case 평가 프로토콜 문안") 을 **한 문서**로 쓴다 —
  worst-case 탐색의 **탐색 공간이 곧 A-family** 이므로 두 문서로 나누면 정의가 갈라진다.
- **봉인 기한**: **W3 (9/22~9/28) 이전** — docs/89 §7 W10 arm 이 "프로토콜은 W3 전 사전
  선언" 을 명시. 봉인 = 사용자 결재 (Task lane 아님).
- **적용 대상**: **W10~W11 층3 frozen-policy robustness arm**. 학습은 여전히 scripted
  고정이며, 본 문서는 **학습된 π\* 를 평가하는 방법**만 정한다.
- **B0 v3 와의 관계**: B0 v3 (`5e7b5b486b9d8a4a`) 가 이미
  `grid.attacker_primary = "A2-nominal ONLY — primary claim is conditioned as
  chi50^net(eta, lambda | A2-nominal). A-family robustness is a separate layer-3 (W10)
  frozen-policy arm; pooling with primary is FORBIDDEN."` 로 못박았다. 본 문서는 그
  "separate layer-3 arm" 의 내용을 채우는 것이지 B0 를 건드리지 않는다.

---

## Part A — A-family 범위 선언

### §A.1 family 의 모집단

A-family = `shepherd/agents/attacker_ladder.AttackerSpec` 의 파라미터 공간 (사다리
A1 → A2 → A3, docs/27 · docs/28 · docs/60). **이번 학기 적대자 상한**이며 learned/PFSP
적대자는 본 family 밖이다 (Paper 1+ / Stage C).

### §A.2 봉인된 nominal 점 (A2-nominal) — 전 캠페인의 조건화 지점

`scenario_kwargs` 가 실제로 넘기는 값 (기계 확인, 2026-09-13):

| 필드 | 값 | | 필드 | 값 |
|---|---|---|---|---|
| `level` | **A2** | | `sprint_range` | 0.0 (off) |
| `lam_gain` | 1.0 | | `sprint_frac` | 1.0 |
| `lam_range` | 1.0 | | `slowdown_range` | (0.0, 0.0) (off) |
| `jink_amp` | **0.6** | | `slowdown_frac` | 1.0 |
| `jink_freq` | 1.5 Hz | | `sense_range` | **30.0 m** |
| `jink_terminal_r` | 3.0 m | | `bait_gain` | 0.0 (A3 off) |
| `route_gain` | **0.5** | | `bait_privileged` | False |
| `fwd_gain` | 4.0 /s | | `bait_threshold` / `bait_range` / `bait_enclosure_r` | 0.5 / (4,16) / 3.0 |
| `homing_gain` | 4.0 /s | | `seed` | 0 |

즉 현행 A2-nominal 은 **jink + angular-gap routing 이 켜진 A2**, v3 종축 프로파일은 전부
off, A3 baiting 도 off 다.

### §A.3 **3-class 분류** — 무엇을 탐색하고 무엇을 고정하는가

본 선언의 핵심. 판단 기준은 하나다: **그 perturbation 이 무차원 좌표 (χ, η, λ) 를
움직이는가.** 좌표를 움직이는 파라미터를 탐색하면 "더 강한 적대자" 와 "다른 격자점" 이
한 수치에 섞여 Δχ50 의 의미가 붕괴한다.

| Class | 파라미터 | 탐색 | 근거 |
|---|---|---|---|
| **I — behavioral (좌표 보존)** | `jink_amp` · `jink_freq` · `jink_terminal_r` · `route_gain` · `homing_gain` · `sense_range` | **✅ CEM 탐색 대상** | 고정 (χ, η, λ) 안에서 **어떻게 기동하는가**만 바꾼다. 능력 한계 (a_att_max, v) 불변 |
| **II — capability / 좌표 이동** | `fwd_gain` · `sprint_range` · `sprint_frac` · `slowdown_range` · `slowdown_frac` · `lam_range` | ❌ 고정 | 유효 속력·상호작용 반경을 바꿔 **격자점 자체를 옮긴다** (아래 §A.4) |
| **III — 탐색 부적격** | `seed` · `bait_privileged` · `level` label | ❌ 고정 | seed = CRN 영역 (적대자 능력 아님) · `bait_privileged` = `v_shot_soft` 직독 **특권 정보** (positive control 전용, 공정 비교 대상 아님) |

**A3 (`bait_gain` 계열) 취급**: `bait_gain` 은 Class I 로 **넣는다** (횡속도 억제는
좌표를 옮기지 않는 기동 선택이다). 단 반드시 `bait_privileged = False` 와 함께 —
**A3-fair 만 탐색하고 A3-privileged 는 탐색하지 않는다**.

### §A.4 Class II 를 뺀 이유 (기록 — 나중에 되묻지 않도록)

- `fwd_gain` 은 **R2a 의 시간 상사변환 주입점**이다. 건드리면 유효 τ 가 바뀌어 χ ∝ aτ²/ρ 가
  이동한다.
- `sprint_*` / `slowdown_*` 는 종축 참조속도를 바꾼다 → **η (표적 속력수) 이동**.
- `lam_range` 는 회피 크기가 아니라 **회피 반경**에 들어간다:
  `r_block = repel_margin · lam_range · kill_radius` (`attacker_ladder.py:194`).
  즉 **행동적 상호작용 범위 σ 를 옮긴다** — docs/95 §7.6 이 지적한 κ/σ 얽힘 축이 바로 이것.
- ⇒ 이들은 "더 나쁜 적대자" 가 아니라 **다른 세계**다. 탐색에 넣으면 CEM 이 가장 쉽게 찾는
  최적해가 "격자 밖으로 도망가기" 가 된다.

> **[범위 밖 — 후속 카드]** Class II 를 움직이는 **capability sweep** 은 정당한 별개
> 질문이지만, docs/92 의 (χ,η,λ) **고정 보정식**을 적용해 좌표를 되돌린 뒤에만 의미가 있다.
> 본 arm 에 넣지 않는다. κ = r_kill/ρ 와 σ = R_sense/ρ 의 **분리**도 그 카드에서 다룬다
> (docs/95 §7.6 다음 세계 카드).

### §A.5 탐색 구간 (Class I) — **[사용자 결재 필요]**

각 파라미터의 하한/상한. nominal 을 포함하고, 물리적으로 무의미한 영역은 배제한다.

| 파라미터 | nominal | 제안 구간 | 비고 |
|---|---|---|---|
| `jink_amp` | 0.6 | [0.0, 1.0] | × a_lat_max — 1.0 초과는 능력 초과 |
| `jink_freq` | 1.5 | [0.5, 3.0] Hz | 상한은 dt_phys = 0.05 s 의 Nyquist (10 Hz) 훨씬 아래 |
| `jink_terminal_r` | 3.0 | [0.0, 6.0] m | 0 = 끝까지 지그재그 (자해적) |
| `route_gain` | 0.5 | [0.0, 1.0] | × a_lat_max |
| `homing_gain` | 4.0 | [0.0, 8.0] /s | |
| `sense_range` | 30.0 | [10.0, 60.0] m | 관측 한계. inf 는 제외 (legacy 전지 관측) |
| `bait_gain` | 0.0 | [0.0, 1.0] | A3-fair 만 |

### §A.5.1 [2026-09-14 결재] **APPROVED AS PROPOSED** — 수치 변경 없음

위 7 개 구간은 **제안된 숫자 그대로 승인**됐다. 여기서 구간을 손대면 근거 없는 임의값을
하나 더 만드는 것이므로 조정하지 않는다. 아래 세 조항을 함께 박는다.

**(1) 이것은 discovery domain 이지 "타당성이 입증된 robustness range" 가 아니다.**
결과가 경계에 몰렸다고 **evaluation 을 보고 범위를 넓히거나 좁히지 않는다.** 확대가
필요하면 **새 카드**로 간다. (이 조항이 없으면 §B.3 의 discovery/evaluation 분리가
구간 선택을 통해 우회된다.)

**(2) `0` endpoint 는 내부 점이 아니라 `behavior-off boundary anchor` 다.**
`jink_amp=0` · `route_gain=0` · `homing_gain=0` · `jink_terminal_r=0` 은 같은 코드 경로를
쓰더라도 **특정 행동 채널을 사실상 제거**한다. 따라서 *"Class I 안에서 매끄럽게 약해진
정책"* 으로 해석하지 않는다. **0 은 구간에서 빼지 않는다** (capability envelope 의 끝점으로
유용하다). 다만 **CEM 이 정확히 0 경계에 붙으면 그 사실을 별도로 보고**한다.

**(3) CEM 좌표는 반드시 정규화한다.**

$$ z_i \in [0, 1] \quad\text{에서 탐색하고 각 실제 구간으로 affine mapping} $$

0–60 m · 0–8 /s · 0–1 이 **원 단위 그대로 같은 Gaussian 에 들어가면 구간 선택이 아니라
optimizer metric 이 결과를 지배한다.** 구현 시 이 정규화를 기계 확인한다.

**(4) `101-A` 를 보고 구간을 조정하지 않는다.** `route_gain` 주변을 촘촘하게 하거나
`sense_range` 를 5–15 m 로 좁히는 식의 수정은 **금지**다 — 방금 발견한 A2 메커니즘을 다음
discovery 설계에 되먹이는 것이고, 그러면 §B.8 transportability 시험의 **독립성이 약해진다**.

**해석 주의 — `sense_range`**: 10 m 로 줄이는 것이 "더 강한 공격자" 라는 뜻은 아닐 수 있다.
Class I 은 **동일 정책족의 capability/behavior variation** 이지 attacker-strength scalar 가
아니다. 결과를 하나의 강도 축으로 정렬하지 않는다 (§A.3~A.4 의 Class I/II 분리가 이를
보장한다).

---

## Part B — worst-case 평가 프로토콜

### §B.1 한 줄 정의

**frozen** π\* 에 대해 Class I 공간에서 CEM 으로 적대자를 탐색 (**discovery**) → 단일 e\*
선택 → **새 CRN 으로 재평가** (**evaluation**). discovery 와 evaluation 의 난수를 분리해
selection bias 를 차단한다.

### §B.2 절차 (봉인 대상)

1. **freeze**: π\* 는 W6~W9 학습 산출물. 본 arm 에서 **어떤 optimizer update 도 없다**.
2. **discovery**: 선언된 boundary-local 셀 집합 D 위에서 CEM 이 Class I 7-vector 를 탐색,
   목적함수 = **defender 성공률 최소화** (= P_U 최소화, B0 v3 의 성공 정의 그대로).
   - χ50 자체를 CEM 루프 안에서 추정하지 **않는다** (비용). χ50 은 evaluation 단계의 산출물.
3. **selection**: CEM 전 이력에서 목적함수 최악 1 점 = **e\***. (상위 k 평균 아님 — 단일 점)
4. **evaluation**: **discovery 와 서로소인 seed 집합**으로, **전 격자**에서 e\* 를 재평가 →
   Δχ50^robust. 이 값만 보고한다.
5. **대조**: 같은 fresh CRN 에서 A2-nominal 도 재평가 (nominal vs e\* 를 같은 난수 위에서).

### §B.3 seed 분리 규약 (기계 강제)

- discovery seed 집합 `S_disc` 와 evaluation seed 집합 `S_eval` 은 **서로소**여야 하고,
  코드가 `assert not (S_disc & S_eval)` 로 확인한다.
- e\* 선택에 evaluation 수치를 **일절 쓰지 않는다**. evaluation 을 본 뒤 e\* 를 바꾸면
  그 순간 본 프로토콜은 무효이며 새 사전등록이 필요하다.

### §B.4 예산 산정 — r4 교훈 반영

> CEM 예산은 **per-CEM-solve 실측** 으로 산정한다. R2b 의 branch estimator 가
> `elapsed / len(records)` 로 희석 추정해 **~4× 과소추정**한 전례가 있다 (docs/89 r4 c4).

- smoke 에서 **CEM 1 solve 의 벽시계 시간을 직접 측정**한 뒤 (셀당 1 회), 그 수치로
  D 의 크기와 population/iters 를 정한다.
- **[HOLD — 결재 보류]** population · iters · |D| · |S_disc| · |S_eval| — 지금 숫자를 적지
  않는다. **π\* 가 W6~W9 에 나온 뒤** per-CEM-solve 를 실측해 재상신한다.

### §B.4a [2026-09-14 추가] **knob-efficacy gate** — 예산보다 먼저

과학 결과를 보는 gate 가 **아니다**. 단 하나만 묻는다:

$$ \boxed{\ \text{이 knob 이 이 campaign support 에서 실제로 causal 하게 연결돼 있는가?}\ } $$

각 Class I 파라미터를 **min / nominal / max** 로 두고, 사전 선언된 smoke state 집합 중
**적어도 하나**에서 시뮬레이터가 실제 쓴 attacker 출력이 달라지는지 본다:
`a_final` · route request · jink/homing 관련 diag · sensing-active 술어.

> **오늘의 규율 적용**: 비교는 **재구현 값이 아니라 시뮬레이터 `diag`** 와 한다.

**사전 규칙 (결과 성능을 보고 고르는 것이 아니다 — 배선 확인이다)**:

- min/nom/max **어디에서도** 출력이 한 번도 안 바뀌는 knob → **nominal 고정 후 CEM
  차원에서 제거**. 완전히 flat 한 차원은 exploration budget 만 먹는다.
- 한 번이라도 바뀌면 → **그대로 유지**.

### §B.4b [2026-09-14 결과] knob-efficacy gate 실행 — **CEM 차원 7 → 5**

`shepherd/scripts/r2b_knob_efficacy.py` → `artifacts/r2b/knob_efficacy.json`.
smoke state = geom_probe 표본 `s` 오름차순 앞 5 판 (사전 선언, 결정론적). nominal replay
parity 5/5. 비교는 시뮬레이터 `diag` 와만 했다.

| knob | nominal | z_nom | 판정 |
|---|---|---|---|
| `jink_amp` | 0.6 | 0.600 | **KEEP** |
| `jink_freq` | 1.5 | 0.400 | **KEEP** |
| `route_gain` | 0.5 | 0.500 | **KEEP** |
| `homing_gain` | 4.0 | 0.500 | **KEEP** |
| `sense_range` | 30.0 | 0.400 | **KEEP** |
| `jink_terminal_r` | 3.0 | 0.500 | **DROP** (사전 지목 적중) |
| `bait_gain` | 0.0 | 0.000 | **DROP** |

⇒ **CEM 탐색 차원 = 5.** 제거된 둘은 nominal 고정.

**`bait_gain` DROP 의 의미 — 범위 축소로 기록한다.** 사전 지목은 `jink_terminal_r` 뿐이었고
`bait_gain` 은 예상 밖이다. 원인은 사거리가 아니다 — attacker-finisher 거리가
`bait_range`(4~16 m) 안에 든 tick 이 **63%** 다. `bait_gain` 은 **활성화 게이트
(`readiness > bait_threshold = 0.5`) 가 열린 뒤에야 곱해지는 배율**인데, gain 을 0 → 1 로
올려도 5 판 전 구간에서 출력이 **비트 단위로 불변**이었다 ⇒ **bait 항이 한 번도 활성화되지
않는다.**

> **귀결**: 본 campaign support 에서 **A3-fair 축은 `bait_gain` 만으로는 탐색 불가능**하다.
> 활성화를 열려면 `bait_threshold` / `bait_range` / `bait_enclosure_r` 를 건드려야 하는데
> 이들은 Class I 에 넣지 않았다. 따라서 §A.1 이 "A1 → A3" 를 A-family 로 선언했음에도
> **본 arm 의 실효 탐색 공간은 A2 행동축 5 개**다. 이는 선택이 아니라 **support 의 한계**이며
> 그대로 보고한다. A3 를 실제로 시험하려면 **별도 카드**가 필요하다 (활성화 파라미터를
> Class I 로 승격할지부터 판단해야 하고, 그건 §A.3 의 좌표 판정을 다시 거쳐야 한다).

**사전 지목**: `jink_terminal_r` 이 7 개 중 **가장 inert 할 위험이 크다** — `101` 계열
표본에서 3 m 게이트가 **한 번도 활성화되지 않았다** ($d_{target}$ 최소 ~12.9 m, 3 m 도달
0/36). 이 지목은 규칙을 바꾸지 않는다 (사후 해석 방지용 사전 기록).

### §B.5 어휘 제한 (docs/89 §7 승계 — 위반 시 논문 문장 무효)

유한 search budget 이므로:

- **금지**: "worst-case", "the worst attacker", "최악의 적대자" 단정.
- **허용**: **"sealed-budget CEM adversarial search"** · **"worst found within the
  declared A-family search"** · "declared Class I behavioral space".
- 산출물 필드명도 `worst_found_*` 로 쓴다 (`worst_case_*` 금지).

### §B.6 판독 (사전 고정)

| 분기 | 조건 | 의미 |
|---|---|---|
| **1** | nominal Δχ50 > 0 **이고** e\* 에서도 Δχ50 > 0 | 학습 이득이 선언된 behavioral 공간 전반에 유지 |
| **2** | nominal Δχ50 > 0 **인데** e\* 에서 Δχ50 ≈ 0 | **self-play 필요성의 실측 동기** (docs/89 §11 Paper 1 서사) — 부정 결과가 아니라 다음 단계의 근거 |
| **3** | nominal 에서도 Δχ50 ≈ 0 | 본 arm 이전의 문제 — 학습 판독으로 되돌아간다 |

**분기 2 는 실패가 아니다.** 그것이 이 arm 을 만든 이유다.

### §B.8 [2026-09-14 추가] PFSP 의 역할이 바뀌었다 — **mechanism transportability test**

`101-A` (`d9329be`) 가 sealed A2 에서 메커니즘을 끝까지 닫았다:

$$ 11\,\text{cm} \rightarrow 0.013\,\text{rad} \rightarrow
   \delta_g \approx 0.021\,\text{rad 의 near-tie 교차} \rightarrow 107°\ \text{route 전환}
   \rightarrow 16.1\,\text{m/s}^2 \rightarrow 0.84\,\text{m/s} \rightarrow 42\,\text{mm}
   \rightarrow \text{capture 상실} $$

이 메커니즘은 **A2 의 hard argmax 에 얹혀 있다** — physics-only 가 아니다. 그래서
learned/PFSP 적대자의 질문이 날카로워졌다. 예전에는 막연히 *"scripted 보다 강한 적대자를
쓰자"* 였는데, 지금은:

$$ \boxed{\ \text{A2 hard-argmax boundary exploitation 이 learned/adaptive attacker 에서도
   나타나는가?}\ } $$

⇒ **PFSP 는 단순 난이도 상승이 아니라 메커니즘의 이식 가능성 시험(transportability test)**
이다. 두 갈래 모두 의미가 있다:

| 결과 | 의미 |
|---|---|
| learned attacker 에서도 연속 섭동이 **자기 decision boundary** 를 통해 확대됨 | 메커니즘이 정책 종류를 넘어 성립 — 주장 범위가 넓어진다 |
| 나타나지 않음 | `101-A` 는 **A2 argmax 의 brittleness artifact** — 주장을 A2 조건부로 영구 한정 |

**본 문서의 Class I/II 분류가 이 시험의 전제다** (§A.3~A.4): 좌표를 움직이는 축을 탐색에서
빼두어야 "적대자가 더 강해졌다" 와 "다른 세계로 갔다" 가 섞이지 않는다.

> **[DEFERRED — reviewer-defense card]** *CEM enrichment near A2 route-choice boundaries*.
> 질문: $P(\text{near-tie} \mid C\text{-success})$ 가 baseline / random / rule 성공 상태보다
> **높은가** (CEM 이 A2 의 불연속을 *찾아간* 것인가, 우연인가).
> **현재 critical path 아님** — `101-A` 의 메커니즘 존재 주장에 필요하지 않다.
> 용도: A2-specific exploitation 진단 · PFSP 결과 해석 보조 · 심사자가 "CEM 이 scripted
> discontinuity 만 exploit 한 것 아닌가" 라고 물을 때 수행.

### §B.7 지위 선언

- 층3 **frozen-policy robustness** — 학습 재실행 없음, B0 v3 불변.
- primary claim 과 **pooling 금지** (B0 v3 `attacker_primary` 조항).
- 본 arm 결과로 primary χ50 을 수정하지 않는다.

---

## 잔여 (결재 현황 2026-09-14)

1. **§A.5 Class I 7 개 탐색 구간** — ✅ **APPROVED AS PROPOSED** (수치 변경 없음).
   운영 조항 4 개 §A.5.1 에 등재 (discovery domain · 0 = behavior-off anchor ·
   좌표 정규화 · 101-A 되먹임 금지).
2. **§B.4 CEM 예산 5 수치** — ⏸ **HOLD**. π\* 가 없으므로 per-solve 실측이 불가능하다.
   선행 = **§B.4a knob-efficacy gate** (정책 불요, 지금 실행 가능) → W6~W9 뒤 예산 재상신.

그 외 구조 (3-class 분류 · discovery/evaluation 분리 · seed 서로소 · 어휘 제한 ·
판독 3-분기) 는 docs/89 §7 · B0 v3 `attacker_primary` · docs/92 좌표 규율에서 **유도된
것**이라 새 자유도가 아니다.
