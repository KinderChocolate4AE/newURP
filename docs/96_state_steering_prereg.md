# 96 — Trajectory-level state steering probe 사전등록 (봉인 — 실행 전)

- **일자**: 2026-09-13 · **지위**: **sealed pre-run** (실행 전 커밋. docs/95 `4a86168` 선례).
- **분류**: **retrospective causal-suffix analysis on frozen artifacts** — 새 world 도 새
  campaign 도 아니다. B0 v3 (`5e7b5b486b9d8a4a`) 를 건드리지 않고 docs/89 달력도 재배치하지
  않는다. **B2 와 병렬 branch**.
- **지정 근거**: docs/95 §7.5 **BRANCH 2** 판정 (`71f35d3`, 판독문
  `temp_research_note/2026-09-13c_*`). 그 판정이 명시한 후속 카드가 본 문서다.
- **r1 amendment (2026-09-13, 실행 전 — 표현 4 종 lock)**: ① $t_\rho$ 를 **정수 산술**로
  고정 (float `round` 폐기 — ties-to-even 자유도 제거) + 개입이 **해당 스텝의 지령에 이미
  적용됨**을 명시 (§3.1) ② $\rho > 0$ 를 `hold` 라 부르지 않는다 — **$W_0$ 만이 legacy
  hold** (§2b) ③ **$\rho^\ast$ 단일 threshold 를 primary 로 쓰지 않는다**; 네 개입을 각각
  보고하고 비단조를 허용한다 (**prefix-sufficiency pattern**, §5) ④ **reference clock 을
  $t_F^C$ 로 고정** — branch 자신의 FIRE 로 시계를 갈아타지 않는다 (§5.0).
  **전부 researcher degrees of freedom 을 줄이는 방향이며, 결과를 본 뒤의 변경이 아니다**
  (probe 미실행).
- **선행 사실 (본 probe 의 전제, 이미 공표됨)**:
  - dep-probe: 46/140 이 **multi-dependent** — full joint plan 은 성공하나 단일 limiter 만
    남기면 실패.
  - geometry probe: 그 46 판에서 pre-fire ΔG_close ≈ 0 (98.0% 틱 구조적 비활성),
    **ΔV = 0 (median = max)**, **D_i = 0 (전 판 전 틱)**.
  - 즉 **"협력하려면 여러 대가 필요했다"** 와 **"그 여러 대가 FIRE 순간 아무것도 하고 있지
    않았다"** 가 동시에 참이다. 본 probe 는 그 사이의 missing causal link 를 측정한다.

- **질문 (하나)**:
  > **성공 C trajectory 의 limiter 지령을 시각 $t_\rho$ 부터 제거하면, 반응형 표적의
  > 미래 FIRE-state ($t_F^C$ 에서) 가 달라지고 그 결과 원래 capture-ready 였던 상태를
  > 잃는가?**

---

## §1. 왜 L1 이 이것을 볼 수 없었는가 (설계의 출발점)

env 의 `delta_headline` 과 `coma_D` 는 **현재 state 를 고정한 채 limiter 기하만 치환하는**
instantaneous counterfactual 이다 (`env.py` step: `vbase` = `layout.limiter_p0`,
`coma_D[i]` = limiter i 만 p0 로 치환). 그러므로

$$ D_i(t) = 0 \quad\not\Longrightarrow\quad \text{limiter } i \text{ 가 과거에 기여하지 않았다} $$

state steering 은 $x_t^{\rm coop} \neq x_t^{\rm hold}$ **자체가 효과**인데, instantaneous
counterfactual 은 이미 만들어진 $x_t^{\rm coop}$ 를 분모로 깔고 비교하므로 그 credit 을
구조적으로 볼 수 없다. docs/95 §4 [r1] 인과 범위 조항이 이미 이 한계를 선언해 두었다.

**본 probe 는 prefix 를 공유시킨 뒤 suffix 만 개입한다** — 그래서 divergence 가 전적으로
개입 이후의 limiter 제어에 귀속된다.

## §2. [실행 전 발견] **K_SEG 경계는 분기점으로 쓸 수 없다** — 유효 plan 은 12 파라미터

본 설계의 1 차안은 CEM 의 `K_SEG=4` 세그먼트 경계를 분기점으로 쓰는 것이었다. **봉인 전
기계 확인 결과 그 설계는 무효다.**

policy 는 `seg = min(i·K_SEG // horizon, K_SEG−1)` 이고 `horizon = lay.episode_len = 160`
이므로 경계 스텝은 **40 / 80 / 120** 이다. 그런데 실제 에피소드 길이는 `steps` **16 ~ 58
(median 23)** 이고 — **140 판 중 139 판이 첫 경계(40) 이전에 종료**한다.

| 사실 | 값 |
|---|---|
| 경계 스텝 (k = 1, 2, 3) | 40 / 80 / 120 |
| `steps` min / median / max | 16 / 23 / 58 |
| `steps > 40` 인 판 | **1 / 140** |
| 세그먼트별 평균 \|plan\| | [2.788, 2.676, 2.648, 2.701] — **전 세그먼트 비영** |

⇒ 두 가지 귀결:

1. **분기 설계 교체 (필수)**: `t_k ∈ {40, 80, 120}` 에서의 개입은 139/140 판에서
   **bit-exact no-op** 이다. 세그먼트 경계는 분기 격자로 쓰지 않는다 (§3 의 새 격자).
2. **[부수 사실, 기록용] search space 는 48D 였으나 성공 궤적은 첫 세그먼트만 사용했다.**
   **realized** controller 는 사실상

   $$ a_i(t) = a_i^{(0)}, \qquad i = 1,\dots,4 $$

   — 즉 **4 개의 상수 가속도 벡터 (12-parameter joint plan)** 이고, limiter 궤적은 p0 에서
   출발하는 **포물선**이다. 성공한 "joint plan" 은 중간 기동 sequence 가 아니라 **초기부터
   서로 다른 방향으로 가속하는 네 limiter** 다. 이 사실은 mechanism 해석을 좁히므로 판독문에
   싣는다.

   > **[소급 수정 금지]** 과거 R2b 문서의 **"search space 가 48D 였다"** 는 서술은 **그대로
   > 참**이다. 그것을 "12D search 였다" 로 고쳐 쓰지 않는다. 허용되는 표현은
   > **"successful realized trajectories used only the first segment"** 뿐이다.
   > (본 probe 의 가설·지표도 바꾸지 않는다 — 분기 격자만 바꾼다.)

## §2b. 개입 정의 — **control withdrawal**

개입은 **plan 의 시간 suffix 를 0 으로 두는 것**이다. 세그먼트 인덱스가 아니라 **스텝**
단위로 자르므로, policy 를 "호출 인덱스 $i \ge t_\rho$ 이면 0 을 낸다" 로 감싼다 (plan 배열 자체는 불변).

| 기호 | 정의 |
|---|---|
| **$W_\rho$** — full withdrawal | $i \ge t_\rho$ 에서 **전 limiter 의 지령 가속도 0** |
| **$W_\rho^{(j)}$** — leave-one-out | $i \ge t_\rho$ 에서 **limiter j 만** 0, 나머지 3 대는 원안대로 |
| **reference** | 원본 plan (= c_arm 이 기록한 성공 판) |

> **[r1 어휘 lock — 이 구별이 논문에서 중요하다]**
> $$ W_\rho \;=\; \textbf{zero-acceleration command withdrawal at } t_\rho $$
> **$\rho > 0$ 인 branch 를 `hold` 라 부르는 것은 금지**다. 지령이 0 이어도 이미
> $v_L(t_\rho) \neq 0$ 이므로 limiter 는 그 뒤 **coast** 한다 — 서 있는 것이 아니다.
> **오직 $W_0 \equiv$ legacy hold** 다 (초기 속도 0 · 초기 위치 `layout.limiter_p0` 이므로
> 전 구간 지령 0 = p0 정지 유지; 기계 확인 완료).
>
> 또한 $W_\rho$ 를 **L1 의 기하 baseline 과 혼동하지 않는다**: `env.py` 의 `vbase` /
> `coma_D` 는 limiter 를 `layout.limiter_p0` 로 **순간 치환(teleport)** 하는 **위치**
> 반사실이고, $W_\rho$ 는 **제어** 반사실이다. (codebase 의 `limiter_mode="hold"` 액션
> 자체는 zero-accel 이므로 $W_0$ 와 동치이지만, **위치 teleport 는 전혀 다른 대상**이다.)
> 산출물 필드명은 `withdraw_*`, 판독문에서 $W_\rho$ 를 "limiter 를 세웠다 / 제거했다" 로
> 서술하는 것은 **금지**.

- **[해석 한계 — 실행 전 명시]** 유효 plan 이 **상수 가속도**이므로 (§2),
  $v_L(t_\rho) \approx a_L t_\rho$ 가 이미 쌓여 있다. 즉 **늦은 $\rho$ 의 withdrawal 은
  본질적으로 약한 개입**이다 — 지령을 거둬도 limiter 는 coast 로 상당 거리를 계속 날아간다.
  따라서 **늦은 $\rho$ 의 null 은 "steering 없음" 의 강한 증거가 아니다**. 이 비대칭을
  §5 · §7 판정에 미리 반영한다.
- **부수 기록 필수**: `coast_disp_j` ($t_\rho$ 이후 limiter j 누적 변위) · `speed_j(t_\rho)`.
  이 수치 없이 withdrawal 결과를 해석하지 않는다.
- **$\rho = 0$ 앵커**: 전 구간 지령 0 = limiter 가 p0 에 정지 유지. **기계 확인 완료**:
  limiter 초기 속도 = 0, 초기 위치 = `layout.limiter_p0` → $W_0$ 는 native
  `limiter_mode="hold"` 와 **동치**다. 자기검증 앵커로 포함한다.

## §3. 분기 격자 (교체) + 공유 prefix

**분기 격자 = 원래 FIRE 시각의 분수** — 모든 판에서 정의되고 (`fire_step` 7 ~ 49),
에피소드 길이 편차에 영향받지 않는다.

### §3.1 [r1] $t_\rho$ 의 **정수** 정의 — off-by-one 자유도 0

float `round` 는 쓰지 않는다 (Python 의 ties-to-even 이 계약에 숨어 들어가고, 사후에 한 칸
옮길 여지가 생긴다). **정수 나눗셈**으로 고정한다:

$$ t_\rho = \left\lfloor \frac{n \cdot t_F^C}{d} \right\rfloor, \qquad
   (n, d) \in \{(0,1),\; (1,4),\; (1,2),\; (3,4)\} $$

코드 계약: `t_rho = (n * fire_step) // d` — 파이썬 정수 연산, 부동소수 미개입.

**개입 시점 규약 (명시)**: 코드베이스에서 **policy 호출 인덱스 = run_episode 루프 인덱스
= probe tick `t` = `fire_step` 의 척도**가 모두 일치한다 (`run_episode` 는 루프 인덱스 t 에서
policy 를 부르고 `env.step` 후 `fire_step = t` 를 기록하며, probe 의 wrapped step 은
증가 전 `_step_i` 를 읽는다). 그 위에서:

> **withdrawal 은 인덱스 $i \ge t_\rho$ 의 모든 policy 호출에 적용된다.** 즉 **스텝
> $t_\rho$ 의 지령은 이미 0** 이고, 원 plan 이 마지막으로 적용되는 스텝은 $t_\rho - 1$ 이다.
> 따라서 공유 prefix 는 **이동 전 상태 기준 $t \le t_\rho$** 에서 성립한다 (스텝 $t_\rho$ 의
> 행동은 아직 적용되지 않았으므로).

각 판의 $t_\rho$ 와 대응 $\xi = (t_\rho - t_F^C)/\tau_0$ 를 레코드에 **함께 싣는다**
(docs/95 의 시간축과 붙이기 위해). $\rho = 0$ 은 §2b 의 $W_0$ 앵커다.

`plan` 은 불변이고 policy 만 $i \ge t_\rho$ 에서 0 을 내므로:

$$ x^{\rm full}(t) = x^{W_\rho}(t) \quad \forall\, t \le t_\rho \qquad (\text{이동 전 상태 기준}) $$

가 **bit-exact** 로 성립해야 한다. 또한 step seed 는
`env._seed·100003 + step_i` 로 **plan 과 무관**하므로 scripted A2 의 난수 stream 이 두
궤적에서 정렬된다 (CRN).

- **GO 조건 (배선)**: ① 봉인 plan replay 가 c_arm 의 `(label, fire_step, steps)` 재현
  ② `plan_hash` 가 geom_probe 기록과 일치 ③ 전 branch 에서 $t \le t_\rho$ 의 전 에이전트
  (p, v) 가 reference 와 **bit-exact** 일치 ④ $W_0$ 이 native `limiter_mode="hold"` 궤적과 일치
  ⑤ NaN/결측 없음. 이 5 개가 통과하면 실행한다. **결과 방향은 실행을 gate 하지 않는다**
  (docs/95 §1.5 규율 승계).

## §4. 표본 — search = 0

- **primary stratum**: geom_probe 46 **multi-dependent** 판.
- **secondary**: 94 solo-sufficient 판 (대조군).
- **합계 140** — docs/95 와 **동일 표본**이어야 세 진단이 같은 판 위에서 붙는다.
- **search 비용 0**: `scenario_kwargs(s, cells, sls)` 가 env 를 재구성하고 plan 은
  `artifacts/r2b/geom_probe/shard*.json` 에 **이미 영속화**돼 있다 (docs/95 §1 의 결정이
  여기서 회수된다). CEM 재실행 없음.
- **판당 replay 수** = 1 (parity) + 4 ρ × (1 full + 4 LOO) = **21**. 전체 2,940
  full-fidelity replay. **실측 비용은 smoke 에서 측정**하고 그 수치로 샤딩한다 (지금
  추정치를 적지 않는다). ρ = 0 의 LOO 4 종은 dep-probe 의 solo/LOO 와 개념이 겹치지만
  **다른 개입** (dep-probe 는 plan row 를 0 으로, 본 probe 는 시간 suffix 를 0 으로) 이므로
  중복이 아니라 **교차검증 앵커**다 — ρ=0 에서는 두 정의가 일치해야 하고, 이를 기계 확인한다.

## §5. 봉인 지표

### §5.0 [r1] **Reference clock = $t_F^C$ — 고정**

비교 시각은 **언제나 원본 C 의 FIRE 시각 $t_F^C$** 다. branch 가 자기만의 FIRE 를 내더라도
**그쪽으로 시계를 갈아타지 않는다**. 이유: 시계를 branch 의 FIRE 로 옮기면 "언제 쏘았는가"의
변화와 "표적 상태가 어떻게 달라졌는가"가 한 수치에 섞여 state steering 질문이 흐려진다.

branch 가 $t_F^C$ 이전에 종결하면 그것을 **별도 outcome 범주로 기록**하고 (P/T),
상태 지표는 결측으로 둔다. branch 의 새 FIRE 시각은 **부수 기록**으로만 싣는다
(`branch_fire_step`) — 판정에 쓰지 않는다.

### 주 outcome — 원래 FIRE 시각 $t_F^C$ 에서의 상태 차이

branch 가 $t_F^C$ 까지 생존하면 **그 동일 시각에서**:

$$ \Delta p_A = \lVert p_A^{W}(t_F^C) - p_A^{C}(t_F^C) \rVert,\quad
   \Delta v_A = \lVert v_A^{W}(t_F^C) - v_A^{C}(t_F^C) \rVert $$

$$ \Delta \hat v_A = \arccos\!\big(\hat v_A^{W} \cdot \hat v_A^{C}\big)\Big|_{t_F^C}
   \quad (\text{heading 편차}) $$

$$ \Delta v_{\rm worst}(t_F^C) = v_{\rm worst}^{W} - v_{\rm worst}^{C},\qquad
   \Delta \mathrm{boxed\_in}(t_F^C) $$

**핵심 질문의 형식**: 원래 $t_F^C$ 에서 authoritative predicate
(`¬boxed_in ∧ v_shot_worst ≥ 1`) 가 **C 에서는 참인데 W 에서는 거짓**이 되는가.

### 종결 outcome (사전 정의된 4 범주 — 사후 분류 금지)

| 범주 | 정의 |
|---|---|
| **S** survived-and-captured | branch 도 `NET_CAPTURE` |
| **L** lost-capture | branch 가 $t_F^C$ 까지 살아있으나 authoritative predicate 상실, 최종 라벨 ≠ `NET_CAPTURE` |
| **P** early-penetration | $t_F^C$ 이전에 `PENETRATED` |
| **T** early-terminated | $t_F^C$ 이전에 그 외 사유로 종료 |

**P·T 는 결측이 아니라 정당한 결과**다 — "제어를 거두니 표적이 그전에 뚫었다"는 그 자체로
steering 증거다. 단 P·T 에서는 $\Delta p_A(t_F^C)$ 가 정의되지 않으므로 상태 지표는
**결측으로 싣고 비율 통계에만 쓴다**.

### [r1] **prefix-sufficiency pattern** — $\rho^\ast$ 단일 threshold 폐기

$$ \text{보고 단위} = \big(\,W_0,\; W_{.25},\; W_{.5},\; W_{.75}\,\big)
   \text{ 네 개입의 결과 벡터} $$

> **$\rho^\ast = \max\{\rho : W_\rho \text{ 가 파괴}\}$ 같은 단일 threshold 를 primary 로
> 쓰지 않는다.** 적대자가 **반응형**이므로 $\rho$ 에 대한 단조성이 보장되지 않는다 —
> $W_{.25}$ 는 실패, $W_{.5}$ 는 성공, $W_{.75}$ 는 다시 실패가 **정상적으로 가능**하다.
> 네 개입을 **각각** 보고하고, 그 형태를 **prefix-sufficiency pattern** 이라 부른다.
> 비단조 패턴은 이상신호가 아니라 기록 대상이다.
>
> **$\rho^\ast$ 를 causal onset time 으로 해석하는 것은 금지.** "이 시점부터 limiter 가
> 중요해졌다" 류 서술을 쓰지 않는다.

허용되는 강한 주장은 하나다: **작은 $\rho$ 에서 withdrawal 만으로도 $t_F^C$ 의 미래 상태가
달라진다** → state steering evidence.

**§2b 의 비대칭 재확인**: 상수 가속도 plan 이라 $v_L(t_\rho) \approx a_L t_\rho$ 가 이미
쌓여 있다. 그러므로 **early withdrawal 에서 효과가 사라지면 steering 의 강한 증거**지만,
**late withdrawal 에서 효과가 유지된다고 해서 "late interval 은 중요하지 않았다" 거나
"steering 이 없다" 고 할 수 없다** — earlier prefix 가 이미 위치·속도를 만들어 놓았기
때문이다.

### 보조 — per-limiter steering credit

$W_\rho^{(j)}$ 의 파괴 여부로 **어느 limiter 의 미래 제어가 결과를 바꾸는가**를 본다.
dep-probe 의 solo/LOO (**전 구간** 제거) 와 달리 본 지표는 **시각별**이다.

> **어휘 lock**: $W_\rho^{(j)}$ 가 파괴적이어도 "limiter j 가 필수" 라 쓰지 않는다.
> **재최적화가 없으므로 necessity 가 아니다** — 다른 plan 이 성공할 수 있다. 허용 어휘는
> **"이 봉인 plan 안에서 limiter j 의 $t_\rho$ 이후 지령이 capture 결과를 바꿨다"** 까지.

## §6. figure 3 장 (사전 고정)

1. **Outcome ladder** — ρ (0 / .25 / .5 / .75) × 결과 범주 (S/L/P/T) 누적 막대,
   primary / control 층 분리.
2. **State divergence vs branch time** — $\Delta p_A(t_F^C)$ · $\Delta v_{\rm worst}(t_F^C)$
   의 ρ 별 분포 (S·L 판만; P·T 는 별도 카운트로 표기). `coast_disp` 를 2 차 축으로 부기.
3. **Per-limiter × branch-time destruction map** — $W_\rho^{(j)}$ 파괴율 히트맵
   (4 limiter × 4 ρ).

**세 figure 모두 ρ 축을 추세선으로 잇지 않는다** — 비단조가 정상이므로 (§5), 점/셀로만
표시한다.

## §7. 판독 3-분기 + 허용 문장 (실행 전 고정)

| 분기 | 조건 | 결론 | 다음 카드 |
|---|---|---|---|
| **1** | **작은 ρ** 의 withdrawal 만으로도 $t_F^C$ 의 상태가 달라지고 (큰 $\Delta p_A$ · $\Delta\hat v_A$) 파괴가 발생 (L/P/T) | **trajectory-mediated steering 이 메커니즘** | 그 steering 의 정형화 + reward 감사 |
| **2** | 어느 ρ 에서도 파괴가 거의 없다 (대부분 S) | 봉인 plan 의 시간 suffix 제어가 결과를 바꾸지 않는다 → **dep-probe 의 multi-dependence 는 초기 배치 효과이거나 search artifact** | 배치-only 개입 · search artifact 검사 |
| **3** | 파괴가 **$\rho$ 와 무관하게 (작은 ρ 포함) 균일**하고 docs/95 의 순간 기하도 null | 순간 기하도 prefix steering 도 아닌 **제 3 경로** | FIRE timing · hard-kill commit · capturer alignment · 종축 상태 |

> **분기 2 의 해석 주의 (§2b 승계)**: 유효 plan 이 상수 가속도라 **ρ > 0 의 개입은 본질적으로
> 약하다** (limiter 가 coast 로 계속 전진). 따라서 분기 2 는 "steering 이 없다" 가 아니라
> **"지령 철회로는 결과가 바뀌지 않는다"** 까지만 말한다. 그 경우 다음 개입은 지령 철회가
> 아니라 **배치 / 초기조건** 쪽이어야 한다.

**허용 문장 (분기 1 일 때, 이 형식으로만)**:

> Under the sealed A2-reactive world and its fixed interaction semantics, withdrawing
> limiter acceleration commands from $t_\rho$ onward changed the reactive target's
> state at the original firing time $t_F^C$ and removed the capture-ready condition
> that the original plan had reached there.

**금지 문장**:
- "cooperation works by physically herding realistic attackers" (docs/95 §7.6 금지어 승계).
- "limiter j is necessary" — 재최적화 없음 (§5 어휘 lock).
- W 를 "limiter 를 정지시켰다 / 제거했다" 로 서술 (§2b 어휘 lock — 지령 철회이지 제동이 아니다).
- **결과가 나오기 전에** 이 현상에 이름을 붙이는 것. 후보 명칭 (*cooperative capture-state
  steering* · *trajectory-mediated capture-set shaping*) 은 **분기 1 이 성립할 때만**
  채택 후보로 올린다 — 지금 채택하지 않는다.

## §8. Modeling caveat — 승계 (docs/95 §7.6)

현 scripted A2 는 회피 기하의 척도가 수비측 `kill_radius` 에 묶여 있다
(`attacker_ladder.py:194`; docs/60 §3.2 가 nominal modeling choice 로 선언). 따라서

$$ \text{state steering exists in A2} \;\neq\; \text{realistic adversary would be steered identically} $$

- 본 probe 는 **"이 세계에서 정말 state trajectory 를 바꿨는가"** 라는 유효한 질문에 답한다.
  그 답을 현실 적대자로 일반화하지 않는다.
- **B0 를 재개봉하지 않는다.** 이 조항은 해석을 좁히는 것이지 세계 변경이 아니다.
- 후속 PFSP world 에서 **κ = r_kill/ρ (defender capability, attacker 관측 입력 금지)** 와
  **σ = R_sense/ρ (행동적 상호작용 범위)** 를 분리한다 (다음 세계 카드).

## §9. 지위 선언 (사후 상향 금지)

- **descriptive causal-suffix analysis**. CI·가설검정 규칙을 두지 않는다 (docs/95 §7 승계).
- **necessity 가 아니다** — 재최적화 없음. N_L ablation / strong necessity 는 별도 카드.
- 본 probe 결과로 B0 v3 조항을 바꾸지 않는다. 바꿔야 하면 **v4 + 새 hash**.
- 산출물 = `artifacts/r2b/steer_probe/` · 상태 = **R2-CAMPAIGN**.
- **결과를 보고 지표를 고치고 싶어지면** 본 문서를 development pilot 으로 강등하고 새
  사전등록을 만든 뒤 이미 열람한 시나리오를 confirmatory 분석에서 제외한다.

## §10. 선행 사전등록과의 관계 (deviation 승계)

docs/95 §4 의 **L2 paired trajectory (secondary) 는 실행되지 않았고 본 문서가 이를 대체**한다
(`geom_readout.json.deviations` 에 기록됨). L2 의 약점 — 서로 다른 궤적이라 인과 귀속이 약함 —
을 본 설계의 **공유 prefix + 동일 시각 비교**가 정면으로 고친다. docs/95 는 봉인 문서이므로
수정하지 않는다.

## §11. training contract 와의 연결 (봉인 전 검토 항목)

geometry probe 가 모집단 수준에서 확인한 것: **성공한 multi-dependent plan 46/46 이 pre-fire
구간에서 `delta_headline` 을 전혀 움직이지 않았다** (peak ΔV median = max = 0). M2 dense
reward 가 바로 그 양 위에 서 있다.

⇒ **training contract 봉인 (W6 전) 에서 `delta_headline` / `coma_D` 기반 dense shaping 을
무검토로 승계하지 않는다.** 본 probe 가 분기 1 을 내면, reward 가 그 메커니즘을 **볼 수
있는지**를 감사한 뒤 봉인한다. B2 scripted 는 이와 무관하게 docs/89 달력대로 진행한다.

## §12. 실행 런북 (랩서버 — 로컬 금지)

```bash
cd /data/hjhong/l2/newURP && source .venv-l2/bin/activate
git pull                                        # 본 사전등록 커밋 포함
export NTFY_TOPIC=hj_URP_x7k2q9

# 0) 서버 smoke 필수 — GO 조건 5 개 + 판당 replay 실측 비용
python -m shepherd.scripts.r2b_steer_probe --smoke

# 1) 샤드마다 **독립** tmux 세션 (샤드 수는 smoke 실측으로 결정)
for K in 0 1 2 3 4 5 6 7; do
  tmux new-session -d -s steer$K "python -m shepherd.scripts.r2b_steer_probe --run --shard $K --n-shards 8"
done
tmux ls
```

- 중단 시 같은 명령 재실행 → shard 파일에서 resume (`b0_v3_hash` 일치할 때만 이어붙는다).
- **산출물은 서버가 커밋** (로컬에서 `git add artifacts/r2b/steer_probe/` 금지 — c_arm /
  dep-probe pull 충돌 선례).
