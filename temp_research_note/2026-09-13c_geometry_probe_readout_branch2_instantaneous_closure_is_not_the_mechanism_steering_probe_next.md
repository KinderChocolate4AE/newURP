# 2026-09-13c — geometry probe 판독: **BRANCH 2**. 순간 escape-channel closure 는 메커니즘이 아니다 → 다음은 trajectory-level steering probe

- **입력**: `artifacts/r2b/geom_probe/shard{00..07}.json` — 140/140, `cf_parity_ok` 전건 true,
  **제외 0건**. 전 레코드 `b0_v3_hash = 5e7b5b486b9d8a4a` · `r2b_b0_hash = cba024d7ee3d9f61`.
- **판독기**: `shepherd/scripts/r2b_geom_readout.py` (신규) → `artifacts/r2b/geom_readout.json`
  + `figures/r2b_geom_f{1..4}_*.png`. 판정 규칙은 docs/95 에서 **실행 전 봉인**됨 — 이 판독은
  적용이지 선택이 아니다.
- **지위**: descriptive mechanism analysis (docs/95 §7). CI·가설검정 없음. **necessity 아님**.
  B0 v3 조항 변경 없음.

---

## 1. 표본

| | n | pre-fire 틱 (ξ ∈ [−2, 0]) |
|---|---|---|
| **multi-dependent (primary)** | **46** | 555 |
| solo-sufficient (대조군) | 94 | 1170 |
| 합계 | 140 | — |

층화는 dep-probe 라벨 `s` 조인 (사전등록된 축). 비율은 **"of the geometry-probe analysis
sample"** — 셀별 K=5 의 deterministic selected set 이지 전체 C-success population 이 아니다.

## 2. H1 — escape-channel closure: **구조적으로 비활성**

> **H1 은 pre-fire 틱의 98.0% 에서 구조적으로 비활성이었다** (canonical test:
> `n_block_full == 0 ∧ n_block_hold == 0`; 보조 기하형 `min_dist > kill_radius + χρ` 로는
> **100.0%**). multi-dependent 층 555 틱 기준. — 이 수치 없이 "협력적 escape closure 가
> 없었다" 고 쓰지 않는다 (docs/95 §6.5 [r1.1] 필수 문장 형식).

- 대조군(solo)도 같다: 98.3% (기하형 99.7%).
- **newly opened (`n_open`) 은 전 표본 0** — 항등식 `ΔG_close = (N_close − N_open)/N_total`
  이 매 틱 기계 검증된 상태에서, 닫힘도 열림도 거의 없다.
- ΔG_close 의 median·IQR 은 **pre-fire 전 구간에서 정확히 0** (Fig 1 상단).

### 잔여 4건 — 있긴 있었다, 그러나 맞물리지 않았다

pre-fire 에 `n_close > 0` 이 한 틱이라도 있는 판은 **4/46** (solo 는 11/94). 전부 **마지막
1~3 틱** (k ∈ [−3, 0]) 에 몰려 있다.

| s | η | hit 틱 | max ΔG_close | closure 틱의 ΔV |
|---|---|---|---|---|
| 3609 | 2.74 | 1/13 (k=0) | +0.0180 | 0.0 |
| 1205 | 1.98 | 4/13 (k=−3…0) | +0.0188 | −0.0017, −0.0067, −0.0006, 0.0 |
| **1600** | 2.47 | 3/13 (k=−2…0) | **+0.4137** | −0.0033, 0.0, 0.0 |
| 1200 | 1.95 | 3/13 (k=−2…0) | +0.0168 | −0.0004, −0.0006, 0.0 |

**closure 가 capturability proxy 를 양으로 움직인 판 = 0/4.** 가장 큰 closure (s=1600,
ΔG +0.41) 에서 ΔV 는 **정확히 0** 이고, ΔV 가 0 이 아닌 곳은 **전부 음수**다. branch 1 은
"closure 반복 **∧** authoritative 진입과 맞물림" 을 요구하므로 (§7.5), 이 **정확한 0** 으로
임계치 없이 탈락한다 — 발명한 cutoff 로 떨어뜨린 것이 아니다.

## 3. H2 — capturability uplift: **null**

- multi 층 pre-fire **peak ΔV 의 median = 0.0000, max = 0.0000**. 46판 중 ΔV 가 0 이 아닌
  판은 3건이고 전부 **음수** 방향이다.
- authoritative predicate (`¬boxed_in ∧ v_shot_worst ≥ 1`, FIRE 시점 동결): **46/46 성립**
  — 당연하다, FIRE 가 그 조건에서 난다. Fig 1 하단이 보여주는 것은 **점진적 접근이 아니라
  마지막 1~2 틱의 계단**이다. 즉 포획은 일어나지만 limiter 배치가 hold 대비 그 진입을
  앞당긴 흔적이 없다.

## 4. H3 — distributed contribution: **완전 null**

- `n_plus` (D_i > 1e-12 인 limiter 수) 가 **46판 전부, pre-fire 전 틱에서 0**.
  히스토그램 `[46, 0, 0, 0, 0]` (pre-fire max 기준과 FIRE 시점 기준 모두).
- `max Σ_i D_i (pre-fire) = 0.00e+00`. Fig 3 은 정의상 전면 0 — 판정 근거가 아니라 기록용.
- 어휘 규율: D_i 는 marginal 이지 Shapley 가 아니므로 이 null 을 "synergy 없음" 이라
  쓰지 않는다. **non-additivity diagnostic 이 잴 것이 없었다**가 정확하다.

## 5. Fig 2 가 보여주는 기하 (육안 증거)

생존 escape direction 은 세 snapshot 모두 **net axis 반대쪽 (θ ≈ 150~180°) 의 좁은 cone,
φ ≈ 0** 에 몰려 있다. denom 115,184 witness 중 close 는 ξ=−1.0 에서 **0**, ξ=−0.5 에서 **17**,
FIRE 시점에 **1,133 (≈1.0%)**. open 은 전부 0. **표적이 도망갈 방향은 FIRE 직전까지
거의 그대로 열려 있었다.**

## 6. Fig 4 — 난이도와의 해리 (dissociation)

η 가 오르면 multi-dependent 비율은 **0.25 → 0.50** (η=3.6) 으로 오르는데, median pre-fire
peak ΔG_close 와 ΔV 는 **전 η 에서 평평하게 0** 이다.

⇒ docs/95 §5 의 서사 문장 — "η 상승과 함께 multi-dependent 와 ΔG_close 가 **둘 다** 오를
때만 허용" — 은 **사용 불가**. 쓰지 않는다. 대신 이 해리 자체가 branch 2 의 서명이다:
**어려워질수록 여러 limiter 에 의존하지만, 그 의존은 순간 기하 채널을 통과하지 않는다.**

## 7. 판정 — **BRANCH 2** (docs/95 §7.5)

> Under the sealed A2-reactive world and its fixed interaction semantics,
> multi-agent-dependent successful plans were **not generally explained by
> instantaneous limiter-induced escape-channel closure near FIRE**. H1 was
> structurally inactive in **98.0%** of pre-fire ticks (`n_block_full == 0` and
> `n_block_hold == 0`). Newly blocked escape directions appeared before FIRE in only
> **4/46** records of the multi-dependent stratum, confined to the final ticks, and in
> **none** of them did that closure coincide with a positive move of the capturability
> proxy.

두 진단이 서로를 버틴다: dep-probe 는 같은 46 판을 **단일 limiter 로 환원 불가**로 분류했고,
본 probe 는 그 판들의 **순간 기하가 hold 와 사실상 동일**하다고 말한다. 둘이 동시에 참이려면
메커니즘은 **궤적(state steering)** 에 있어야 한다 — L1 은 상태를 고정하므로 구조적으로 그것을
볼 수 없다 (§4 [r1] 인과 범위 조항).

**금지어 재확인**: "therefore cooperation works by physically herding realistic attackers" —
쓰지 않는다. §7.6 의 modeling caveat (A2 의 회피 기하 척도가 수비측 `kill_radius` 에 묶여
있음) 가 조건으로 붙지 않은 일반화는 금지.

## 8. 다음 카드

1. **trajectory-level state steering probe 사전등록** (별도 문서 — 본 probe 에 끼워넣지
   않는다). 본 판정이 지정한 후속.
2. **학습 설계 함의 (가설 수준, docs/95 §6.5 의 별도 카드가 모집단에서 확인됨)**: M2 dense
   reward 가 `delta_headline` 위에 서 있는데, 성공한 협력 plan **46/46 이 그 양을 pre-fire
   구간에서 전혀 움직이지 않았다** (peak ΔV median = max = 0). surrogate 위에 세운 shaping 이
   이런 해를 찾지 못할 수 있다 → **training contract 봉인 (W6 전) 의 검토 항목**.
   전제: CEM 은 capture 를 최적화했지 surrogate 를 최적화하지 않았다.
3. B2 scripted (docs/89 달력 W4) 는 이 판정과 독립으로 진행.

## 9. 미실시 / 범위 밖

- **necessity 아님** — 재최적화 없음. 다른 단독 plan 이 성공할 수 있다. N_L ablation /
  strong necessity 는 별도 카드.
- L2 paired trajectory 층은 본 판독에 넣지 않았다 (사전등록상 secondary, 그리고 branch 2 의
  후속이 바로 궤적 층이므로 steering probe 에서 제대로 설계한다).
- solo 층 잔여 closure 11/94 중 1건은 ΔV 가 양으로 움직였다 — 대조군이므로 판정에 쓰지
  않고 기록만 한다.
