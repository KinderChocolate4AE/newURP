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

**⚠ 이 7 개 구간은 제가 정한 제안값입니다.** nominal 을 중심에 두고 능력 상한에서 자른
것이지 실측 근거가 있는 값이 아닙니다 — **봉인 전 결재 필요**.

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
- **[사용자 결재 필요]** population · iters · |D| · |S_disc| · |S_eval| — smoke 실측 후
  확정. 지금 숫자를 적지 않는다 (근거 없는 상수 금지).

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

### §B.7 지위 선언

- 층3 **frozen-policy robustness** — 학습 재실행 없음, B0 v3 불변.
- primary claim 과 **pooling 금지** (B0 v3 `attacker_primary` 조항).
- 본 arm 결과로 primary χ50 을 수정하지 않는다.

---

## 잔여 (봉인 전 결재 2 건)

1. **§A.5 Class I 7 개 탐색 구간** — 제안값이며 실측 근거 없음.
2. **§B.4 CEM 예산 5 수치** — smoke 실측 후 확정 (지금 적지 않음).

그 외 구조 (3-class 분류 · discovery/evaluation 분리 · seed 서로소 · 어휘 제한 ·
판독 3-분기) 는 docs/89 §7 · B0 v3 `attacker_primary` · docs/92 좌표 규율에서 **유도된
것**이라 새 자유도가 아니다.
