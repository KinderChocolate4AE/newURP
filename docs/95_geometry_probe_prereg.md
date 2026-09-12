# 95 — Cooperative geometry probe 사전등록 (봉인 — 실행 전)

- **일자**: 2026-09-13 · **지위**: **sealed pre-run** (**r1 amendment 반영**, 140건 실행 전).
  실행 전 커밋 (dep-probe 선례 `29bc681`).
- **r1 amendment (2026-09-13, 실행 전)**: ① smoke 의 지위를 **wiring/parity 전용**으로 고정
  (결과 방향이 실행 여부를 gate 하지 않음) ② H1 의 **directional operationalization**
  (closure mask + 좌표계 + 고정 snapshot 시각) 추가 ③ "전체/모집단" 표현을 **prespecified
  analysis sample** 로 축소 ④ L1 의 인과 범위 명시 ⑤ n₊ 수치 규약 명시 ⑥ plan 영속화 필드
  목록 확정. **전부 researcher degrees of freedom 을 줄이는 방향이며, s=0 smoke 결과 때문에
  가설·지표를 바꾼 것이 아니다** (§6.5 참조 — s=0 은 이미 열람됐고 그 사실을 기록해 둔다).
- **분류**: **retrospective mechanism analysis on frozen artifacts** — 새 world 도, 새
  campaign 도 아니다. B0 v3 (`5e7b5b486b9d8a4a`) 를 건드리지 않고, docs/89 달력도
  재배치하지 않는다. **B2 와 병렬 branch**.
- **질문 (하나)**:
  > **C 가 성공하기 직전, hold 대비 어떤 escape direction 이 사라졌고, 그 사라짐에 몇 대의
  > limiter 가 동시에 기여했는가?**
- **현재 증거 지위 (정확히)**: `limiter-control opportunity exists` 보다 강한
  **constructive multi-agent-dependent capture witnesses exist** — C_N=1 은 봉인 search
  class 안의 성공 joint plan 에 대한 constructive witness 이고, dep-probe 의
  `multi_dependent = 32.9%` 는 그 성공들 중 상당수가 **동일 plan 에서 단일 limiter 만
  남기는 것으로 환원되지 않는다**는 추가 증거다. **재최적화가 없으므로 strong necessity 는
  아니다** (다른 단독 plan 이 성공할 수 있음).

---

## §1. 데이터 가용성 판정 (실행 전 확인 완료)

| 아티팩트 | 담긴 것 | 판정 |
|---|---|---|
| `artifacts/r2b/c_arm/shard*.json` | outcome 요약 (`label` · `C_N` · `fire_step` · `steps` · `n_contact` · `clean_crossings`) | **plan 미저장 · tickwise 미저장** |
| `artifacts/r2b/c_dep_probe/shard*.json` | label 계열 (`full/solo/loo`) | **plan 미저장** |
| `results/viz_r2b_c_pick{0,1,2}.json` | 대표 3 episode tickwise | **population claim 금지 — 예시 case study 전용** |

⇒ 경로 = **봉인 search 결정론 재실행 → plan 재현 → logging replay**. dep-probe 가 이미 쓰는
**replay-parity gate** 경로이므로 새 실험이 아니라 derived-data extraction 이다.

- **[결정] plan 을 이번에 반드시 영속화한다.** plan 은 4 limiter × K_SEG=4 × 3 성분 ≈ 48 개
  실수인데, 저장하지 않아서 **dep-probe 와 본 probe 가 각각 search 비용을 다시 냈다**.
  이번 산출물에 `plan` 을 싣고, 이후 mechanism/necessity 분석은 search 없이 replay 만 한다.
  **[r1] 영속화 필드 (확정)**: `s` · `solver_ns`/solver seed · search **code commit** ·
  `plan_kind` · 48-value `plan` · **plan hash** · `b0_hash` (B0 v3) · **R2b `b0_hash`** ·
  full replay `(label, fire_step, steps)` · **telemetry hash**. 이것이 있어야 다음
  necessity ablation 이 **search = 0, replay only** 로 간다.

---

## §1.5 [r1] smoke 의 지위 — **wiring/parity 전용, 방향 gate 아님**

> smoke (s=0, s=3 …) 는 **engineering smoke** 다. **H1/H2 신호가 0 이거나 기대와 반대로
> 나와도 140 건 full run 은 그대로 실행한다** — 그것도 결과이기 때문이다.

full-run **GO 조건은 결과 방향이 아니라 배선뿐**이다:

1. search 결정론 재현 성공 (`plan_kind == "accels"`)
2. replay parity — `(label, fire_step, steps)` 가 c_arm 기록과 일치
3. 재구성 full `v_shot_soft` == env `v_shot_soft`
4. 재구성 ΔV == env `delta_v_shot_headline`
5. **[r1]** closure-mask 항등식 `(N_close − N_open)/N_total == ΔG_close`
6. FIRE alignment 정상 · NaN/결측 telemetry 없음

이 6개가 통과하면 실행한다. **결과를 보고 지표를 고치고 싶어지면** 그 순간 본 문서를
development pilot 으로 **강등**하고 새 사전등록을 만든 뒤 이미 열람한 시나리오를
confirmatory 분석에서 제외해야 한다 (비용이 2~3 h 수준이므로 그럴 이유가 거의 없다).

## §2. 봉인 가설 3개 (신규 지표 fishing 금지)

**H1 — escape-channel closure**. hold 반사실 대비
**ΔG_close(t) = p_blocked^full(t) − p_blocked^hold(t) > 0** 이 형성되고, 특히 **FIRE 직전에
커지는가**.

> **raw `p_limiter_blocked` 를 G_close 라 부르지 않는다.** `p_feasible` 에는 표적 자신의
> turn-limit 등 **limiter 와 무관한 intrinsic infeasibility** 가 섞여 있다. 협력량은 반드시
> **hold 반사실과의 차분**이다.

### [r1] H1 의 directional operationalization — "**어느 방향이** 닫혔는가"

ΔG_close 는 **얼마나** 닫혔는지만 말한다. 방향을 말하려면 **같은 CRN witness j** 위에서:

- **newly blocked**: `M_close^(j) = T_j ∧ LF_hold^(j) ∧ ¬LF_full^(j)`
- **newly opened**: `M_open^(j) = T_j ∧ ¬LF_hold^(j) ∧ LF_full^(j)`

(`LF` = limiter-feasible per-witness mask, `T` = layout-independent turn-feasible mask.)

그러면 **항등식**이 성립한다 — scalar 와 angular figure 가 정확히 연결된다:

> **ΔG_close = (N_close − N_open) / N_total**

이 항등식은 **매 틱 기계 검증**한다 (§1.5 GO 조건 5).

**좌표계 (target-centered, 사전 고정)**: ê₁ = `unit(e_net)` (capture axis) ·
ê₂ = `unit(v_att − (v_att·ê₁)ê₁)` · ê₃ = ê₁ × ê₂. witness 방향은
`d_j = unit(endpoint_j − p_att)` 를 (θ = arccos(d·ê₁), φ = atan2(d·ê₃, d·ê₂)) 로 싣는다.
이 frame 이어야 "net axis 반대쪽 escape sector 가 닫혔다" 류 기하 해석이 가능하다.
(frame 재구성용으로 `e_fin` · `p_fin` · `v_att` 원시값도 함께 저장한다.)

**snapshot 시각 (사전 고정, fishing 방지)**: **ξ ∈ {−1.0, −0.5, 0}** — q_dec = 1/6 이므로
정확히 `fire_step − 6`, `− 3`, `fire_step`. 각 snapshot 에서 (θ, φ) 히스토그램으로
`M_close` · `M_open` · 분모(turn-feasible witness) 를 저장한다. 틱별 스칼라
(`N_close` · `N_open` · `N_total`) 는 **전 틱** 저장한다.

**H2 — capturability uplift**. **ΔV(t) = v_shot_soft^full − v_shot_soft^hold** 가 양으로
상승하며 실제 FIRE 상태가 authoritative capture condition 쪽으로 이동하는가.

> `delta_v_shot_headline` (= ΔV) 은 **mechanism proxy** 다. **authoritative predicate 는
> 여전히 `¬boxed_in ∧ v_shot_worst ≥ 1`** (FIRE 시점 동결) 이므로 `v_shot_worst` 와
> `boxed_in` 을 **항상 같이 그린다**. **"capture set 진입" 이라는 표현은 authoritative
> predicate 에만 쓴다.**

**H3 — distributed limiter contribution**. **D_i(t) = V_full(t) − V_{−i}(t)** (`coma_D`,
동일 accel 표본) 로, 성공 직전 **몇 대의 limiter 가 동시에 양의 marginal 을 갖는가**.

> **`ΔV − Σ_i D_i` 를 "synergy" 라 부르지 않는다.** D_i 는 full coalition 에서 하나씩 뺀
> marginal 이지 Shapley decomposition 이 아니다. 허용 어휘는 **non-additivity diagnostic**
> 까지.

**[r1] n₊ 수치 규약**: `n₊(t) = Σ_i 1[D_i(t) > tol]`, **tol = 1e-12** (그 이하는 0 으로
처리). **n₊ 와 D_i 의 크기를 항상 같이 보고**한다 — tiny positive 하나가 "meaningful
contributor" 로 과장되지 않도록.

---

## §3. 시간축 — FIRE **이전**이 중심

capture predicate 가 **FIRE 에서 동결**되므로 `t > t_FIRE` 의 limiter 기하는 **그 shot 의
포획 여부를 개선할 수 없다** (이후는 penetration race 에만 작용).

- **중심 window**: **ξ = (t − t_FIRE)/τ₀ ∈ [−2, 0]**. q_dec = 1/6 이므로 1 tick = ξ 0.1667,
  즉 **[−2, 0] = FIRE 직전 12 틱**.
- FIRE 이후 0.40 s (= (1+q_race)τ₀, 8 틱) 는 **별도 패널**이며 제목은 **post-fire race** —
  이 구간을 capture-set shaping 이라 부르지 않는다.

---

## §4. 분석 2층 — 섞지 않는다

| 층 | 비교 대상 | 강도 |
|---|---|---|
| **L1 within-C counterfactual (primary)** | **같은 C trajectory · 같은 tick · 같은 CRN** 에서 full vs all-hold(`vbase`) vs each-i-hold(`coma_D`) | trajectory divergence confound 거의 없음 — mechanism 판독의 정본 |
| | **[r1] 인과 범위**: L1 은 *realized C state* 에서 현재 limiter configuration 을 hold baseline configuration 과 비교하는 **instantaneous geometric counterfactual** 이다. "에피소드 시작부터 hold 였다면 표적이 어디 있었을지" 를 재구성하지 **않는다** → **instantaneous geometry attribution, not full-policy causal effect**. 후자는 L2 의 몫. | |
| **L2 paired trajectory (secondary)** | 같은 scenario 의 C success vs hold failure vs rule failure | 실제 state evolution 차이를 보여주나 **서로 다른 궤적**이라 인과 귀속은 L1 보다 약함 |

논문에서도 두 층을 **분리 보고**한다.

---

## §5. 산출 figure 4장 (사전 고정)

1. **FIRE-aligned time series** — ΔG_close · ΔV · (v_shot_worst − 1) 의 **prespecified
   geometry-probe sample of C successes** median/quantile, ξ ∈ [−2, 0]. ("전체 C-success"
   라고 쓰지 않는다 — 셀별 K=5 의 deterministic selected analysis set 이다.)
2. **Target-centered angular geometry** — FIRE 직전 몇 틱의 surviving escape directions +
   limiter bearings + net/capture direction. (협력 기하의 육안 증거 후보)
3. **Per-limiter contribution heatmap** — (normalized time × limiter) 의 `coma_D`.
4. **Mechanism vs difficulty** — η 에 따른 multi-dependent fraction · ΔG_close · pre-fire
   peak ΔV.

**서사 문장은 결과가 실제로 그렇게 나올 때만**: "표적이 더 빠른 regime 에서는 성공이 단순
pursuit 이 아니라 여러 limiter 가 동시에 escape set 을 제한하는 configuration 에 더
의존한다" — η 상승과 함께 multi-dependent 와 ΔG_close 가 **둘 다** 오를 때만 허용.

---

## §6. 구현 규약 (bit-identical 보장 + self-check)

- **rollout 무개조**: `run_episode(..., telemetry=[])` 의 기존 훅 (기본 None = 아무 일도
  안 함, REG-2 bit-identical) 으로 **이동 전** (p_att, v_att, p_lims) 를 받고,
  `env.step` 을 **기록 전용으로 wrap** 해 info 를 모은다 (`r2a_stage1._rollout_traj` 선례).
- **env 가 이미 주는 것** (재구현 금지): `delta_v_shot_headline` (= ΔV) · `coma_D[i]`
  (= D_i) · `p_limiter_blocked` · `p_feasible` · `v_shot_soft` · `v_shot_worst` ·
  `boxed_in` · `fire_event`.
- **env 가 안 주는 것 = hold 반사실의 `p_blocked`** → 같은 pre-move 상태에서 **동일
  step_seed** (`env._seed*100003 + (t+1)`) 로 union 을 만들고
  `eval_union_with_limiter_sets(union, [lim_pos, layout.limiter_p0], kill_radius)` 로 재구성.
- **PARITY SELF-CHECK (필수)**: 재구성한 `ΔV = full.v_shot_soft − hold.v_shot_soft` 가
  env 의 `delta_v_shot_headline` 과 **일치해야** 한다. 불일치 = 반사실 재구성이 env 의 것이
  아님 → **그 판 폐기**. 이것이 H1 수치의 신뢰 근거다.
- **replay-parity gate (dep-probe 승계)**: 재현 replay 의 `(label, fire_step, steps)` 가
  c_arm shard 기록과 일치해야 진행.
- **dep-probe 층화 조인**: 각 시나리오 레코드에 dep-probe 의
  `multi_dependent` / `solo_any` / `loo_all` 을 s 로 조인해 싣는다 (§5 figure 4 의 층화
  축이 사전등록돼 있으므로 새 축이 아니다). **[r1] primary analysis stratum =
  multi-dependent cases within the prespecified dep-probe sample**; solo-sufficient 층은
  대조군이다. **32.9% 는 "of the dep-probe analysis sample" 로만 쓴다** — 전체 C-success
  population 의 비율처럼 표현 금지.
- **표본**: dep-probe 와 **동일 규칙** — 셀별 s 오름차순 `C_N==1 ∧ plan_kind=="accels"` 앞
  K=5 판, 최대 140. 같은 표본이어야 dep-probe 판정과 붙는다.

---

## §6.5 배선 검증 (smoke, 2026-09-13 — illustrative only)

`s = 0` (dep-probe 가 **solo-sufficient** 로 분류: `multi_dependent=0`, `solo_any=1`):

| t | ξ | ΔG_close | ΔV | v_worst | Σ D_i |
|---|---|---|---|---|---|
| 15~18 | −0.67…−0.17 | 0.0000 | 0.0000 | 0.000 | 0.0000 |
| **19** | **0.00 (FIRE)** | 0.0252 | 0.0000 | **1.000** | 0.0000 |
| 20 | +0.17 | 0.3315 | 0.0577 | 0.000 | 0.0577 |

- **counterfactual parity: 전 틱 OK** — 재구성한 full 이 env 값과 정확히 일치.
- 읽기: 이 판은 **FIRE 이전 협력 신호가 사실상 0** 이고 큰 ΔG_close 는 **post-fire** 에만
  나타난다 (이 shot 의 포획 여부를 바꿀 수 없는 구간). dep-probe 가 독립적으로
  solo-sufficient 로 분류한 판이라 **두 진단이 교차검증**된 셈이다.
- **n = 1 illustrative. 모집단 주장 아님.** 이 관찰로 §2 의 가설·지표를 바꾸지 않는다.

`s = 3` (dep-probe 가 **가장 강한 협력 판**으로 분류: `multi_dependent=1`, `solo_any=0`,
`n_solo_success=0` — 단일 limiter 만 남기면 4/4 전부 실패):

| t | ξ | ΔG_close | ΔV | v_worst | Σ D_i |
|---|---|---|---|---|---|
| 12~15 | −0.67…−0.17 | 0.0000 | 0.0000 | 0.000 | 0.0000 |
| **16** | **0.00 (FIRE)** | 0.0000 | 0.0000 | **1.000** | 0.0000 |

- **counterfactual parity: 전 틱 OK.** ΔV 는 **env 자신의 `delta_v_shot_headline`** 이므로
  probe 버그가 아니다 — 이 판에서 limiter 들의 실제 위치는 매 틱 **hold 위치와 정확히 같은**
  escape-blocking · viability 를 낸다.
- **그런데 dep-probe 는 같은 판에서 단일 limiter 로는 4/4 실패**라고 판정했다. 둘이 동시에
  참이려면 메커니즘이 **순간 기하가 아니라 궤적(state steering)** 에 있어야 한다 — 이 세계의
  적대자는 반응형 (A2 + kill-radius repel) 이라 limiter 는 *존재만으로* 표적 경로를 바꾸는데,
  **L1 은 상태를 고정하므로 구조적으로 그것을 볼 수 없다** (§4 [r1] 인과 범위 조항 그대로).
- **n = 2 illustrative.** §1.5 [r1] 규율에 따라 **이 방향성은 full run 을 gate 하지 않는다**.
  가설·지표 불변. H1/H2/H3 가 모집단 수준에서 null 이면 그것이 결과이며, 후속은 **별도
  사전등록의 trajectory-level 분석**이다 (본 문서에 추가하지 않는다).
- **[r1.1 확인] 그 0 은 기하학적으로 강제된 것**: 같은 판에서 plan 은 비자명하고
  (`max|a| = 7.9`, limiter 가 p0 대비 1.14 → 2.82 m 이동) angular 분해도 비-퇴화
  (denominator 2504 witness) 인데 **`N_close = N_open = 0` (세 snapshot 전부)**.
  최근접 limiter 거리가 **8.67 → 5.13 m** 이고 `kill_radius` 0.75 m · χρ ≈ 1 m 이므로
  **그 구간에서는 어떤 배치로도 escape direction 을 막을 수 없다.** H1 채널이 구조적으로
  비활성인 상태에서 나온 0 이다 (측정 실패 아님).
- **[별도 카드로 기록] 학습 설계 함의 (가설 수준)**: M2 dense reward 가 `delta_headline`
  위에 서 있는데 성공한 협력 plan 들이 그 양을 **전혀 움직이지 않았다**. surrogate 위에
  세운 shaping 이 이런 해를 찾지 못할 수 있다 → **training contract 검토 항목**.
  (CEM 은 capture 를 최적화했지 surrogate 를 최적화하지 않았다는 점이 이 관찰의 전제다.)

### [r1.1] H1 채널 활성도 validity 스칼라 (실행 전 추가)

smoke s=3 에서 ΔG_close·N_close·N_open 이 **전부 정확히 0** 인데, 원인이 측정이 아니라
**기하**임이 드러났다: 그 구간 limiter 최근접 거리 **5.1~8.7 m** vs `kill_radius` 0.75 m,
표적 τ₀-도달집합 반경 χρ ≈ 1 m. **어떤 배치로도 escape direction 을 막을 수 없는 상태**다.

null 을 해석하려면 **"측정된 0"** 과 **"채널이 구조적으로 비활성이라 나온 0"** 을 구분해야
하므로 틱마다 다음 3 개를 기록한다: `min_dist_att_lim` · `max_lim_disp` (p0 기준 변위,
plan 이 비자명함의 증거) · `kill_radius`.

> **이 필드들은 H1 을 양(陽)으로 만들 수 없다** — 가설·지표·판정 규칙 불변이고, null 의
> **해석 범위만** 좁힌다 (denominator 를 적는 것과 같은 성격). 그래서 실행 전 추가가
> researcher DoF 를 늘리지 않는다.

판독문 필수 문장 형식: "H1 은 전체 틱의 N% 에서 **구조적으로 비활성** 이었다
(min_dist > kill_radius + χρ)" — 이 수치 없이 "협력적 escape closure 가 없었다" 고 쓰지
않는다.

## §6.8 실행 런북 (랩서버 — 로컬 금지)

- **비용 실측**: 시나리오당 **10 분+** (search 재실행 384 rollout 이 지배). 140 건 로컬
  직렬 = 20 h+ → **30분+ 실험은 랩서버** 규율 대상.
- **실행** (dep-probe 와 동일 규약: 연속 샤드 · incremental 저장 · resume · ntfy):

  ```bash
  tmux new -s geom
  for k in 0 1 2 3 4 5 6 7; do
    python -m shepherd.scripts.r2b_geom_probe --run --shard $k --n-shards 8       > /data/geom_shard$k.log 2>&1 &
  done; wait
  ```

  예상 **2~3 h** (8 샤드 병렬, dep-probe 와 같은 규모). 중단 시 같은 명령으로 **resume**
  (`b0_hash` + `b0_v3_hash` 가 같을 때만 이어붙인다).
- **산출물**: `artifacts/r2b/geom_probe/shard{00..07}.json` — **서버가 커밋**
  (c_arm pull 충돌 재발 방지 규율).
- **판독 전 확인**: 전 레코드 `cf_parity_ok == true` (GO 조건 3~5 의 런타임 판). 하나라도
  false 면 그 판을 제외하고 제외 사유·건수를 판독문에 명시한다.

## §7. 지위 선언 (사후 상향 금지)

- 본 probe 는 **descriptive mechanism analysis** 다. CI·가설검정 규칙을 두지 않는다.
- **necessity 가 아니다** (재최적화 없음). N_L ablation / 재최적화는 **별도 카드**.
- 본 probe 결과로 B0 v3 조항을 바꾸지 않는다. 바꿔야 하면 **v4 + 새 hash**.
- 산출물은 `artifacts/r2b/geom_probe/` · 상태 = **R2-CAMPAIGN** (lineage 는 evidence grade
  가 아님 — results/README 세탁 방지 조항).
