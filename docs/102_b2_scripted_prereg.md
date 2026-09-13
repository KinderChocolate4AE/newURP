# 102 — B2 scripted baseline 사전등록 (봉인 — 실행 전)

- **일자**: 2026-09-14 · **지위**: **sealed pre-run**. docs/89 **W4** 항목의 이행.
- **역할 한정**: 본 문서는 **W4 scripted baseline 을 봉인**하는 데까지다. **W5 stop rule 을
  여기로 끌어오지 않는다.** B2 는 W5 가 소비할 **net-side evidence 를 생산**한다.
- **불변 조항 승계**: B0 v3 (`5e7b5b486b9d8a4a`) 를 건드리지 않는다. 새 과학 질문을 추가하지
  않는다 — arm · cell · CRN · forced-fire · metrics · readout 만 닫는다.

---

## §1. Arm 축 — **2 arm**, fallback 은 arm 이 아니라 지표

`reference fallback` 은 B0 v3 `mission.kinetic_fallback` 이 **world 의 일부**로 못박은
scripted PN takeover 다. docs/89 §10 도 "B2 에서 **secondary system metric 으로 기록만**"
이라 한다. 따라서 arm 축이 아니다.

| | **SOLO** | **RULE_COOP** |
|---|---|---|
| limiter control | `limiter_mode="hold"` (= `hold_position_limiter()` = `zeros(4)`, zero-accel) | `limiter_mode="arc"` + `limiter_kw = {r_d: 9.0, dphi: π/6}` |
| 근거 | B0 v3 B-arm 과 동일 의미 | **docs/63 §7 SELECTED c5** — 이미 선택된 점을 그대로 가져온다 (새 자유도 0) |

**둘 사이에 같은 것 (전부 동일해야 한다)**:

| 축 | 값 |
|---|---|
| world / 계약 | B0 v3 `5e7b5b486b9d8a4a` · resolved-contract manifest 해시 동일 |
| attacker | **A2-nominal** (docs/97 §A.2 봉인 점) |
| FIRE admissibility | `fire_cmd == 1 ∧ v_shot_soft ≥ θ_fire` — **고정 게이트** (B0 v3 `mission.fire_transition`) |
| PN fallback | on (world 기본) — 양 arm 에서 동일하게 작동, **기록만** |
| cell 집합 · n | §2 |
| CRN | §3 |
| finisher / pointing / 제어기 | 불변 |

⇒ **오직 limiter control 만 다르다.**

> **`intercept` 를 넣지 않는 이유 (기록)**: R2b 에서 이미 rule arm 계열의 null 을 알고 있다.
> 지금 `arc + intercept` 를 같이 넣으면 *"알고 있는 controller 성능을 근거로 baseline
> family 를 확장했다"* 는 공격 여지가 생긴다. arc c5 는 **이전 선택점을 그대로** 가져오는
> 것이라 깨끗하다. 또한 B2 의 목적은 *"scripted cooperative baseline 하나를 고정하고 MARL
> 진입 여부를 판단"* 이지 *"여러 heuristic 중 좋은 것 찾기"* 가 아니다.

> **재확인**: `reference fallback` 의 $P_U$ 가 아무리 좋아도 **primary pass 가 될 수 없다**.
> MARL 진입 사유는 learned shaping 의 **net frontier 개선 여지**이지 $P_U$ 가 아니다
> (docs/89 §10).

## §2. Cell 집합 — **B0 v3 격자를 그대로 참조** (새로 고르지 않는다)

B0 v3 `grid` 가 이미 기계 규칙을 봉인했다. **재선택 금지**:

- `G = 14` 행 — 한 행 = 하나의 (η, λ) 쌍
- 행·slice 당 `chi_lo`/`chi_hi` = 그 slice 의 χ50 을 **bracket 하는 micro-grid(0.02) 두 점**
- `base_rule` = `{chi_lo − 0.04, chi_lo, chi_hi, chi_hi + 0.04}` → 행당 4 점
- `n_per_cell_per_seed = 300` · **A2-nominal only**
- censoring 유발 시 `±0.04` 확장 (방향당 최대 2회) — **봉인 규칙이므로 그대로 승계**

⇒ 기본 **14 × 4 = 56 cell**. `S_C` (R2b secondary replay set) 와 **혼합 금지**.
실행 시 **cell ID 를 manifest 에 열거**해 사후 선택 자유도를 0 으로 만든다.

### §2.1 [r1 amendment 2026-09-14, 실행 전] **eval seed = 3** — 예산 확정

초안이 `n_per_cell_per_seed = 300` 만 인용하고 **seed 수를 명시하지 않았다.** 그 상태로는
33,600 (seed 1 가정) 과 100,800 (seed 3) 이 둘 다 읽혀 blocker 다. **문서가 답을 준다**:

- B0 v3 `grid.seeds_min = 3`
- §2 가 승계한 **censoring 확장 규칙이 `arm × seed` 단위**다 — *"ANY arm × seed 의
  isotonic fit 이 censored 면 그 행을 ALL arms × ALL seeds 에 동일 CRN 으로 확장"*
- `boundary_rule.row` = **">= 2/3 seeds 에서 paired Δ > 0"**, `decisions.2_seed_rule` =
  per-seed majority, `boundary_rule.rejected` = **seed-pooled point estimate 금지**
- docs/89 평가 조항: *"B2 와 동일 world contract. **seed ≥ 3**"*

⇒ **seed = 1 이면 승계한 확장 규칙도 row gate 도 정의되지 않는다.** 따라서:

$$ oxed{\ 	ext{eval seeds} = 3\ } \qquad
   56 	imes 300 	imes 2\ 	ext{arm} 	imes 3\ 	ext{seed} = \mathbf{100{,}800}\ 	ext{ep} $$

paired Δ 는 **cell × seed 단위**로 `RULE_COOP − SOLO` 를 잡는다 (seed pooling 금지).

## §3. CRN / seed 계약

- 두 arm 은 **같은 scenario 집합과 같은 seed** 를 소비한다 (paired).
  scenario seed 규약은 기존 `SEED0 + s` 를 승계한다.
- manifest 에 명시: `scenario seed` · `attacker seed` · `evaluation seed` · `arm pairing`.
- **기계 강제**: 두 arm 의 scenario ID 열이 **정확히 같고 같은 순서**여야 한다
  (`assert ids_solo == ids_rule`).
- **B2 evaluation seed 는 향후 MARL training seed 와 섞지 않는다** — B2 는 `seed_ns`
  별도 namespace 를 쓰고 manifest 에 기록한다.

## §4. Outcome partition — B0 v3 정의를 **재정의하지 않는다**

B0 v3 `metrics.partition`: **에피소드당 정확히 한 bin**

$$ N \ \mid\ H_{fb} \ \mid\ H_{illegal} \ \mid\ F_{other} $$

(N = clean net capture · H_fb = post-NET_FAIL legitimate kinetic · H_illegal = NET_PRE /
NET_PENDING 중 kinetic contact · F_other = timeout·crash·out-of-bounds 등)

**항상 함께 출력**한다:

$$ P(N),\quad P(FIRE),\quad P(N \mid FIRE),\quad P(H_{illegal}),\quad P_U = P_N + P_{H_{fb}} $$

- **NO FIRE = net failure.** 기권은 실패다. **censoring 보정 금지** (B0 v3 §과학 층).
- **일관성 검사 (raw count identity)**: $P(N) = P(FIRE)\cdot P(N \mid FIRE)$ — 확률이 아니라
  **원 카운트**로 확인한다.
- 셀별 $P(FIRE \mid \chi)$ 와 $P(N \mid FIRE, \chi)$ 를 **전 arm 상시 기록** (docs/89 §214).

## §5. forced-fire micro-arm — **diagnostic only**

> $$ \boxed{\ \text{diagnostic intervention only — primary scripted 비교와 pooling 금지}\ } $$

네 번째 "성능 arm" 이 아니다. 묻는 질문은 **하나**로 제한한다:

> **낮은 $P(N)$ 이 FIRE gate censoring 때문인가, FIRE 이후 attainability 때문인가?**

### §5.1 기제 — `SystemSpec.force_commit_step` (docs/83 §15, 기본 off)

그 스텝에서 **발사 자격 술어를 정확히 1발 우회**한다 (`do(F=1)`). θ_fire 를 영구히 0 으로
두지 않고 **그 한 스텝만 교체 후 복원**하며 `fire_cmd` 도 함께 세운다. 나머지 파라미터 불변.

⇒ 제거되는 것은 **오직** $v_{shot,soft} \ge \theta_{fire}$ **admissibility gate** 뿐이다.
trajectory · 제어기 · attacker · NET predicate 는 건드리지 않는다.

**필수 조항 2 개**:

1. **`perfect_aim_at_commit = False`** — pointing 을 바꾸면 gate diagnostic 이 아니게 된다
   (docs/89 W4 "pointing/제어기 불변").
2. **`_step_i` 는 1-based** — `step()` 진입 시 먼저 증가하므로 0-based 루프 인덱스 `t` 에
   대해 `force_commit_step = t + 1` 이다. **0-based 를 그대로 넣으면 한 스텝 일찍 발동**하며
   회귀 D-B/D-C 가 실제로 이것을 잡았다 (`e1d_commit_geom.py:116` 주석).

### §5.2 발사 시점 선택 — **완전히 기계적** (e1d 2-pass 규약 승계)

> **금지**: "trajectory 를 보고 capture 가 좋아 보이는 순간 발사". $v_{shot,soft}$ 최대
> 시점도 **금지** — 그것이 바로 게이트가 재는 양이다.

`e1d_commit_geom.forced_pass` 의 2-pass 구조를 그대로 쓴다:

- **Pass 1 (reference)**: 해당 arm 의 원 실행. 매 틱 **축방향 좌표**
  $a(t) = (p_{att}(t) - \text{apex}) \cdot \hat n_F$ 를 기록.
- **선택**: $t^\ast = \arg\min_t \lvert a(t) - a_{target} \rvert$, **동률이면 가장 이른 t**.
  $a_{target} = (\text{range\_min} + \text{range\_max}) / 2$ — 봉인된 cone band 의 중점이다
  (새 상수 아님).
- **Pass 2 (forced)**: **같은 CRN** 재생 + `force_commit_step = t^\ast + 1` +
  **`fire_mode="never"`** — 게이트 우회가 **유일한 발사 경로**임을 보장한다.

> $a_{target}$ 를 band 중점으로 둔 것은 제 선택이며, 봉인된 cone 파라미터에서 유도했을 뿐
> 실측 근거는 없다. **결과를 보고 바꾸지 않는다.**

### §5.3 대상 cell — 미리 잠근다

"boundary band" 를 말로 두지 않는다. B0 v3 base_rule 의 **안쪽 두 점** `{chi_lo, chi_hi}`
가 정의상 χ50 을 bracket 하므로 그것이 boundary band 다:

$$ \mathcal{G}_{ff} = \{\,(\text{row}, \chi) : \chi \in \{\chi_{lo}, \chi_{hi}\}\,\}
   \qquad 14 \times 2 = 28\ \text{cell} $$

### §5.4 예산 — primary 와 **별도 계정**

forced-fire 를 100,800 에 섞지 않는다. manifest 에 **별도 계정**으로 적는다.

- **표본 (기계 규칙)**: §5.3 의 28 cell 에서 **`FIRE = 0` 으로 끝난 전 에피소드**.
  "흥미로운 판" 을 고르는 것이 아니라 **censoring 질문의 정의상 대상 전체**다.
  ⇒ primary run **이후**에 돌린다 (그 결과가 표본을 정한다 — 선택이 아니라 정의).
- **비용**: 선택된 에피소드당 **replay 2 회** (pass 1 축좌표 기록 + pass 2 강제발사).
  pass 1 을 primary 산출물에서 재사용하지 않는 이유 = 100,800 판의 per-tick 축좌표를
  저장하지 않기 때문이며, 재실행이 **동일 CRN 을 구조적으로 보장**한다 (GO smoke 6 이 검증).
- **상한**: $2 	imes 28 	imes 300 	imes 3 = 50{,}400$ ep-equivalent (전 판이 no-fire 인
  극단). **실제 비용 = 2 × (해당 28 cell 의 no-fire 에피소드 수)** — manifest 에 실측 기록.

### §5.5 판독 (이 조합만 본다)

| 관측 | 읽기 |
|---|---|
| $P(FIRE)$ 매우 낮음 **∧** forced-fire 가 net capture 를 회복 | **gate-limited** |
| $P(FIRE)$ 는 나오는데 $P(N\mid FIRE)$ 낮음 | **attainability / controller-limited** |
| forced-fire 해도 실패 | gate 가 핵심 원인 **아님** |

## §6. B2 판독 규칙 — W5 stop rule 과 **분리**

> B2 scripted 결과는 **arm 별 · 셀별 net metrics 를 기술**하며, fallback $P_U$ 는
> **secondary system metric** 이다. **B2 자체에서 MARL continuation/termination 을 결과 후
> 결정하지 않는다.** W5 stop rule 은 **별도 봉인 규칙**을 적용한다.

즉 **B2 readout = 무엇을 측정하고 비교할지**, **W5 = 그 결과로 연구를 계속할지**. 섞지 않는다.

## §7. GO smoke — 본 실행 전 필수

1. **B0 v3 계약 테스트** `tests/test_b0_v3_contract.py` 전건 pass (B0 v3 `gates` 가
   "any B2 / MARL run 전" 으로 이미 의무화).
2. **manifest parity** — 두 arm 의 resolved-contract manifest 가 limiter arm flag 외
   전 필드 동일 (B0 v3 `machine_assert` 승계).
3. **CRN 동일** — 두 arm 이 같은 scenario ID 열을 같은 순서로 소비.
4. **partition 합 = 1** — 에피소드당 정확히 한 bin, 합이 총 에피소드 수와 일치.
5. **raw count identity** — $N_{count} = FIRE_{count} \times (N\mid FIRE)_{rate}$ 가
   반올림 오차 없이 성립.
6. **forced-fire 는 지정 tick 의 게이트만 바꾼다** — $t < t^\ast$ 의 pre-intervention
   trajectory 가 pass 1 과 **bit-identical**.
7. **`H_illegal` latch · fallback semantics 가 B0 와 동일**.

> **오늘의 규율 (2026-09-14)**: 6·7 의 대조는 **우리 재구현이 아니라 simulator 의
> authoritative trace** 와 한다. `100-X` 가 자기 코드끼리 비교해 버그를 놓친 전례가 있다.

## §8. 지위

- scripted baseline 측정. **learned arm 없음** (B0 v3 불변 조항: stop rule 통과 전 MARL 금지).
- 산출물 `artifacts/r2b/b2_scripted/` · 상태 **R2-CAMPAIGN**.
- 본 문서는 arm·cell·CRN·forced-fire·metrics·readout 만 정한다. 새 과학 질문 추가 금지.
