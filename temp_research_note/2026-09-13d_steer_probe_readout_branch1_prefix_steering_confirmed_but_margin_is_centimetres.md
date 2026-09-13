# 2026-09-13d — steering probe 판독: **BRANCH 1**. prefix steering 확인 (제목의 "센티미터 여유" 는 **철회됨 — §3 정정 참조**)

> ## ⚠ [정정 2026-09-13, 같은 날 · 소급 삭제 없이 추가]
>
> **§3 의 "성공한 plan 들은 포획 경계 위에 정확히 걸쳐 있다" 는 결론은 철회한다.** 논리
> 오류다:
>
> `v_shot_worst` 는 **이진** 술어이고 (`1.0 iff EVERY feasible escape is caught`),
> **성공은 그 술어로 정의된다.** 따라서 성공한 46 판이 전부 1.0 인 것은 **동어반복**이며
> "얼마나 여유 있게 합격했는가" 에 대해 **아무 정보도 주지 않는다.** 모든 escape 가 네트
> 안쪽 1 m 에 있어도 1.0, 가장 바깥 것이 경계 안쪽 1 mm 여도 1.0 이다.
>
> 마찬가지로 $\lVert\Delta p_A(t_F^C)\rVert$ = 9.6 cm 는 **개입이 만든 변위**이지
> **포획 경계까지의 거리가 아니다.** branch 는 위치·속도·heading·이후 도달집합을 **동시에**
> 바꾸므로, 술어를 뒤집은 원인이 위치 10 cm 라고 단정할 수 없다.
>
> **살아남는 문장** (이것은 그대로 유효):
> > Centimeter-scale changes in the attacker's FIRE-time position, induced by early
> > limiter-command withdrawal, were sufficient to **coincide with** loss of the
> > authoritative capture condition.
>
> **죽는 문장**: "the capture margin was 9.6 cm" · "정밀 threading" · "경계에 얹는다".
>
> §1·§2·§4 의 prefix dependence 결과는 **영향받지 않는다** (개입 대비 결과만 쓴다).
> 실제 여유는 **docs/98 capture-margin audit** 이 signed geometric margin 으로 측정한다.

- **입력**: `artifacts/r2b/steer_probe/shard{00..07}.json` — 140/140, **제외 0**.
  세계 해시 단일 (`b0_v3 5e7b5b486b9d8a4a` · `r2b_b0 cba024d7ee3d9f61`).
  2,800 branch 전부 `prefix_parity_ok` · reference-clock 정합 · NaN 0.
- **판독기**: `shepherd/scripts/r2b_steer_readout.py` → `artifacts/r2b/steer_readout.json`
  + `figures/r2b_steer_f{1,2,3}_*.png`. 규칙은 docs/96 에서 **실행 전 봉인**.
- **지위**: descriptive causal-suffix analysis. CI·가설검정 없음. **necessity 아님**
  (재최적화 없음). B0 v3 불변.

---

## 1. 결과 — prefix-sufficiency ladder (primary = multi-dependent 46)

| 개입 | t_w (median) | S / L / P / T | **파괴율** | $\lVert\Delta p_A(t_F^C)\rVert$ median | auth 상실 |
|---|---|---|---|---|---|
| $W_0$ (= legacy hold 앵커) | 0 | 0 / 46 / 0 / 0 | **100.0%** | 0.098 m | 44 |
| $W_{0.25}$ | 3 | 1 / 44 / 1 / 0 | **97.8%** | 0.097 m | 44 |
| $W_{0.5}$ | 6 | 8 / 38 / 0 / 0 | **82.6%** | 0.092 m | 38 |
| $W_{0.75}$ | 9 | 27 / 19 / 0 / 0 | **41.3%** | 0.002 m | 15 |

대조군 (solo-sufficient 94): 같은 방향이나 훨씬 완만 — 53.2% → 42.6% → 22.3% → **14.9%**.

**prefix-sufficiency pattern (4-vector) 은 완전한 계단이다**:
`LLLL` 19 · `LLLS` 19 · `LLSS` 6 · `LSSS` 1 · `LPSS` 1. **비단조 0/46.**
즉 판마다 "어느 시점부터는 지령을 거둬도 된다"는 **경계가 하나씩** 있고, 그 경계가
서로 다를 뿐이다. (사전등록대로 $\rho^\ast$ 를 단일 지표로 쓰지 않고 4-vector 로 보고한다.)

**LOO $W_\rho^{(j)}$ 파괴율** — 네 limiter 모두 같은 방향으로 감쇠:

| ρ | limiter 0 / 1 / 2 / 3 |
|---|---|
| 0.00 | 0.61 / 0.54 / 0.57 / 0.70 |
| 0.25 | 0.39 / 0.46 / 0.52 / 0.59 |
| 0.50 | 0.26 / 0.24 / 0.30 / 0.35 |
| 0.75 | 0.07 / 0.09 / 0.07 / 0.07 |

특정 한 대가 아니라 **네 대 모두**, 그리고 **이른 구간에서만** 결과를 바꾼다.

## 2. 판정 — **BRANCH 1** (docs/96 §7)

> Under the sealed A2-reactive world and its fixed interaction semantics, withdrawing
> limiter acceleration commands from $t_\rho$ onward changed the reactive target's state
> at the original firing time $t_F^C$ and removed the capture-ready condition that the
> original plan had reached there (destroyed 98% at ρ=0.25, falling to 41% at ρ=0.75;
> 45/45 survivors show a non-zero attacker-state displacement at $t_F^C$).

**§2b 비대칭이 이번엔 결론을 강화한다**: 걱정했던 것은 "늦은 ρ 의 null 이 약한 증거"라는
쪽이었는데, 실제로 나온 것은 **이른 ρ 에서의 파괴**다 — 사전등록이 "강한 증거" 라고 미리
지정한 방향이다.

**coast 로 설명되지 않는다**: 개입 후 limiter 최대 변위 median 이 전 ρ 에서 **1 m 미만**
(0.46 / 0.67 / 0.53 m). "지령을 거둬도 멀리 날아가서 효과가 남았다" 는 설명은 성립하지 않는다.

## 3. ⚠ [철회됨] 여유가 센티미터라는 해석 — 아래는 오류이며 기록으로만 남긴다

| 척도 | 값 |
|---|---|
| reference `v_worst` at $t_F^C$ | **46/46 전부 정확히 1.0** (술어 통과 최소값) |
| `v_worst` 가 취하는 값 | **{0.0, 1.0} 이진** |
| ρ=0.25 의 $\lVert\Delta p_A\rVert$ | median **0.096 m** · 36% 가 **5 cm 미만** · 98% 가 `kill_radius`(0.75 m) 미만 |
| auth 상실 vs 유지 (ρ=0.75) | dp median **0.042 m** vs **0.0002 m** |

⇒ 성공한 plan 들은 **포획 경계 위에 정확히 걸쳐 있다**. 방향은 옳다 (변위가 클수록 술어를
잃는다) 지만 **크기는 수 센티미터**다.

> **따라서 허용되는 서술은 "limiter 가 표적을 멀리 몰았다" 가 아니다.**
> 정확한 서술: **봉인된 plan 은 표적을 포획 술어의 경계에 정확히 얹고, 그 직전 구간의
> limiter 지령이 바로 그 얹기를 수행한다. 수 센티미터가 어긋나면 술어가 뒤집힌다.**
> — steering 은 맞되 **bulk herding 이 아니라 threading** 이다.

이것은 CEM 이 capture 를 최적화한 결과와 정합적이다: 탐색이 **가능성의 가장자리**를 찾아낸
것이고, 그래서 geometry probe 에서 surrogate 가 움직이지 않았다.

## 4. 세 probe 가 하나로 맞물린다

| probe | 결과 |
|---|---|
| dep-probe | 46/140 이 **multi-limiter dependent** |
| geometry probe (docs/95) | pre-fire 순간 채널 **98.0% 비활성**, ΔV = 0, $D_i$ = 0 |
| **steer probe (본 판독)** | **이른 지령 철회가 결과를 파괴**, ρ 에 대해 단조, 비단조 0/46 |

메커니즘: **limiter 지령이 표적 궤적을 빚어 발사 순간 그 상태가 빠듯한 포획 조건 안에
들어오게 한다.** 순간 기하 차단이 아니고, 그래서 instantaneous counterfactual (`coma_D`,
`delta_headline`) 이 구조적으로 보지 못한다.

**어휘 (docs/96 §7 금지어 준수)**: "cooperation works by physically herding realistic
attackers" 는 쓰지 않는다. 후보 명칭 (*cooperative capture-state steering* ·
*trajectory-mediated capture-set shaping*) 은 분기 1 성립으로 **채택 후보 자격만** 얻었다.
실제 채택은 **docs/98 margin audit 이후** — 그 전에는 *positional threading* 계열의
명칭을 쓰지 않는다.

## 5. training contract — HOLD 를 **경고로 격상**

geometry probe 가 "성공 plan 46/46 이 `delta_headline` 을 전혀 안 움직였다" 를 보였고,
본 probe 가 "그 plan 들의 이른 구간 지령이 실제로 결과를 결정한다" 를 보였다. 둘을 합치면:

> The legacy **instantaneous** dense signal is empirically **blind to the observed
> trajectory-mediated dependence** in the preregistered multi-dependent sample.

⇒ W6 전 training contract 봉인에서 `delta_headline` / `coma_D` 기반 dense shaping 을
**무검토 승계 금지**. 의심의 핵심은 계수 크기가 아니라 **credit assignment 의 causal
horizon** 이다 — 같은 현재 상태에서의 순간 반사실은 이미 누적되어 만들어진 x_A(t) 를
고정하므로 과거 기여가 사라진다. 따라서 **계수를 키우는 방식으로 해결하지 않는다.**
대안 후보는 state-progress / future-value 계열의 potential Φ(x_t) — 단 **docs/98 이후**에
설계한다.

## 6. 미실시 / 범위 밖

- **necessity 아님** — 재최적화 없음. LOO 가 파괴적이어도 "limiter j 필수" 라 쓰지 않는다.
- 대조군에 대한 관찰 (판정 미사용, 기록만): solo-sufficient 94 판 중 **44 판은 $W_0$
  (전 구간 지령 0) 에서도 포획**된다 — 그 판들은 "한 대면 충분" 이 아니라 **limiter 가
  사실상 무관**했다는 뜻이다. 층 이름이 오도할 수 있으므로 향후 문서에서 주의.
- A2 의 `kill_radius` 결합 caveat 승계 (docs/96 §8) — 본 결과를 현실 적대자로 일반화하지
  않는다.
- 다음 자연스러운 질문 = **왜 경계에 걸치는가** (CEM 이 가장자리를 찾는 것인지, 세계가
  그렇게 생긴 것인지). 별도 카드.
