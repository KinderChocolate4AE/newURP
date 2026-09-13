# 100 — `100-X` discrete-transition audit (봉인 — 실행 전)

- **일자**: 2026-09-13 · **지위**: **sealed pre-run**, 단 **증거 등급은 exploratory** 다.
- **⚠ 등급 세탁 금지**: 본 문서가 추적하는 가설은 `99-X` 가 **결과를 보고 생성한 post-hoc
  가설**이다. 규칙을 실행 전에 봉인하는 것은 **분석 자유도를 줄이기 위함**이지 증거를
  confirmatory 로 승격시키기 위함이 **아니다**. 판독문·논문에서 본 결과는
  **"99-X 가 생성한 mechanistic hypothesis 를 고정된 규칙으로 추적한 것"** 으로만 쓴다.
- **분류**: frozen-artifact 재현 + 진단. 새 world 없음. B0 v3 불변. B2 와 병렬.

## §0. 추적할 사슬 (이것이 전부)

$$ \text{same small geometric perturbation} \rightarrow \textbf{free-arc argmax switch}
   \rightarrow \text{A2 command jump} \rightarrow \text{attacker state divergence}
   \rightarrow \text{AUTH outcome divergence} $$

**핵심은 "다르다" 가 아니라 시간 순서다.** 따라서 세 first-event tick 을 잡고 그 **순서**를
본다 (§3).

## §1. 대상 · 그룹 (결과 후 재정의 금지)

- `W_{0.75}` **full withdrawal** branch, multi-dependent **46** 판.
- 그룹은 **`99-X` 산출물(`artifacts/r2b/noeffect_diag.json`)의 `s` 라벨을 그대로 승계**한다:
  **`RET_noeffect` 21 · `LOST` 15 · `RET_effect` 10**.
  > **본 audit 결과로 그룹을 다시 나누지 않는다.** 재정의하면 그 순간 순환논증이 된다.

## §2. switch 의 **물리적** 정의 (arc index 금지)

free arc 목록은 매 틱 재정렬·분할·병합되므로 **`arc_id` 비교는 실제 선택 변화를 뜻하지
않는다.** 선택된 **방향**으로 판정한다.

`_route_accel` 의 반환값은 `route_gain · a_lat_max · (cos m·û + sin m·ŵ)` 이므로
**선택 방향은 그 출력에서 그대로 나온다** — 재구현 없이:

$$ \hat d = \frac{a_{route}}{\lVert a_{route}\rVert}, \qquad
   \Delta\theta^\ast = \arccos(\hat d_{ref}\cdot\hat d_{br}) $$

$$ \boxed{\ \text{SWITCH}(t) \iff \Delta\theta^\ast(t) > \varepsilon_\theta = 0.05\ \text{rad}\ } $$

**ε_θ 근거**: 11 cm 의 limiter 이동이 ~8.5 m 거리에서 만드는 **연속적** bearing 표류는
≈ 0.013 rad 이고, `99-X` 가 $t_w\!+\!1$ 에서 실측한 방향차 median 은 **0.0010 rad** 이다.
0.05 rad 은 그 **50 배**이므로 연속 표류를 switch 로 오인하지 않는다. (제가 고른 값이며
실측 근거는 이 두 수치뿐이다. 결과가 이 값 근처에서 뒤집히면 판독문에 명시한다.)

**보조 기록 — 진짜 argmax flip 인지 보는 용도**: 매 틱 최광폭 gap $g_1$, 차광폭 $g_2$,
**argmax margin $\delta_g = g_1 - g_2$**. $g_1, g_2$ 는 재구현하되, 그 재구현이 고른
방향이 `_route_accel` 출력 방향과 **일치하는지 매 틱 기계 확인**한다 (불일치 = 재구현
drift → 그 판 폐기). *switch 판정 자체는 §2 의 원본-출력 기준만 쓴다.*

## §3. 세 first-event tick (실행 전 수치 고정)

$t > t_w$ 범위에서:

| 기호 | 정의 | 임계 |
|---|---|---|
| $t_{switch}$ | 선택 방향이 갈린 첫 틱 | $\Delta\theta^\ast > 0.05$ rad |
| $t_{cmd}$ | A2 회피지령이 점프한 첫 틱 | $\lVert a_{route}^{br} - a_{route}^{ref}\rVert > \varepsilon_a = 0.1\ \text{m/s}^2$ |
| $t_{amp}$ | 표적 상태 이탈이 선형 예측을 크게 넘은 첫 틱 | $\lVert\Delta p_A(t)\rVert > 10 \cdot \tfrac12\lvert\Delta a_0\rvert\,((t-t_w)\,\Delta t_{phys})^2$ |

- **ε_a 근거**: `99-X` 실측 첫 지령차 ~0.008 m/s² 의 **12 배**.
- **$\Delta a_0$** = $t_w\!+\!1$ 의 지령차 (선형 예측의 기준). 배수 **10** 은 선언값.
- 셋 다 없으면 `None` 으로 싣는다 (결측 아님 — "일어나지 않음").

**A2 의 limiter 의존 항은 route 뿐임을 확인한다**: A1 repel 은 `repel_margin·kill_radius
= 0.75 m` 안에서만 켜지고 본 구간 최근접 거리는 5~11 m 이며, `bait_gain = 0`, jink·homing
은 limiter 에 의존하지 않는다. **매 틱 최근접 거리 > 0.75 m 를 기계 확인**하고, 위반 판은
"route 만이 채널" 이라는 전제가 깨진 것이므로 표시한다.

## §4. 산출 · 비용

판당 **replay 2 회** (reference · `W_{0.75}`) — 46 판 × 2 ≈ **약 3 분, 로컬**.
매 틱 기록: 양쪽 $\hat d$ · $\Delta\theta^\ast$ · $g_1,g_2,\delta_g$ · $a_{route}$ 차 ·
$\Delta p_A,\Delta v_A,\Delta\hat v_A$ · 최근접 limiter 거리.
산출물 `artifacts/r2b/transition_audit.json`.

## §5. [실행 전 고정] 판독

**기대 형태** (맞으면 사슬이 성립):

| 그룹 | switch | switch 직전 $\delta_g$ | 증폭 |
|---|---|---|---|
| `RET_noeffect` | 거의 없음 | 큼 (argmax 여유) | ≈ 선형 |
| `LOST` | 다수 | ≈ 0 (비등) | 급증 |
| `RET_effect` | 다수 | ≈ 0 | 급증하나 AUTH 유지 |

**순서 판정**: $t_{switch} \le t_{cmd} \le t_{amp}$ 가 성립하는 판의 비율을 보고한다.
순서가 깨지면 사슬은 **기각**이다 (증폭이 switch 보다 먼저면 switch 는 원인이 아니다).

**허용 문장 (성립 시)**:

> Within the sealed A2-reactive world, a small limiter-geometry perturbation crossed a
> free-arc argmax separatrix, and the resulting discrete route-choice switch preceded the
> command jump and the attacker-state divergence.

**금지**:
- `LOST` 와 `RET_effect` 가 **둘 다** 증폭되면 **"switch 가 capture loss 를 결정한다" 고
  쓰지 않는다.** 그 경우 정확한 서술은 **switch → state divergence** 이고, capture 여부는
  그 divergence 가 capture 경계를 넘느냐가 정한다 (두 단계를 합치지 않는다).
- 일반화 금지: 이것은 **sealed scripted A2 의 argmax 불연속**에서 나온 메커니즘이며
  "민첩한 회피자 일반의 물리" 가 아니다. learned/PFSP attacker 에서 같은
  **behavioral decision-boundary exploitation** 이 나타나는지 확인하기 전까지
  일반성을 주장하지 않는다 (docs/97 후속 카드와 연결).
- 명칭은 **잠정**: *cooperative mode-switch steering* ·
  *trajectory steering through discrete evader route-choice transitions* — 결과 확인 후에만
  후보로 올린다.

## §6. 지위

- exploratory hypothesis-tracking. CI·가설검정 없음. necessity 아님.
- `96-BR1` · `98-B` · `99-P` 판정을 바꾸지 않는다.
- 상태 **R2-CAMPAIGN**.
