# 2026-09-14a — `101-A` 확정: **near-tie argmax separatrix**. 메커니즘이 정량적으로 닫혔다

- **지위**: exploratory (docs/101 규율). 규칙 봉인 `ff0a3ab`. 코드
  `shepherd/scripts/r2b_route_boundary_audit.py` → `artifacts/r2b/route_boundary_audit.json`.
- 그룹 `99-X` 동결 승계. **46/46 ok, 제외 0.**

## 0. GO gate — 새 규율의 첫 적용, 그리고 통과

$$ \bigl\lVert a_{route}^{\text{reconstructed}} - a_{route}^{\texttt{diag}} \bigr\rVert
   \;\le\; 10^{-9} \quad \text{전 tick · 양 궤적} $$

**최대 오차 `0.00e+00` — bit-exact.** 재구성이 시뮬레이터가 실제 쓴 값과 완전히 일치한다.

이것으로 `100-X` 의 실패 원인도 확정된다: 유일한 차이가 `fwd` 한 줄이었고
(`unit(v_att)` ← 잘못 / `unit(target − p_att, v_att)` ← 맞음), 그 한 줄을 고치니
오차가 **정확히 0** 이 됐다. **"내 코드 vs 내 코드" 가 아니라 authoritative 값과 대조하라**
는 규율이 첫 적용에서 값을 했다.

---

## 1. 판정 — **`101-A` (score-order crossing)**

| 그룹 | flip | 분기 | flip tick 에 `n_ahead` 변화 |
|---|---|---|---|
| `RET_noeffect` 21 | **0/21** | 101-N ×21 | 0/21 |
| **`LOST` 15** | **15/15** | **101-A ×15** | **0/15** |
| `RET_effect` 10 | 6/10 | 101-A ×6, 101-N ×4 | 0/10 |

`n_ahead` 와 `n_gaps` 가 **전 판에서 불변** → 후보 집합의 split/merge/생성/소멸이 없다.
**`101-B` (topology crossing) 은 기각**이고, 같은 후보들 사이의 **순위 교차**다.

## 2. 왜 뒤집혔나 — 숫자가 정확히 맞는다

**flip 직전 argmax margin** $\delta_g = g_1 - g_2$ (LOST):

$$ \text{median } 0.0208\ \text{rad}, \qquad \min 0.00037\ \text{rad} $$

**섭동이 만드는 각 변화**: limiter 가 ~11 cm 이동, 거리 ~8.5 m →

$$ 0.11 / 8.5 = 0.0129\ \text{rad} $$

**같은 크기다.** 최광폭과 차광폭 free arc 가 **섭동 스케일 이내로 비등**해 있었고,
11 cm 가 그 순위를 넘긴 것이다.

### 대조군이 이를 확정한다 (fire−1, 같은 tick)

| 그룹 | $\delta_g$ median | min | 섭동(0.0129 rad) 대비 |
|---|---|---|---|
| **`LOST`** | **0.0249** | **0.00195** | **~1.9 배** — 넘길 수 있다 |
| `RET_noeffect` | **0.0622** | **0.03575** | **~4.8 배** — 못 넘긴다 |
| `RET_effect` | 0.1252 | 0.0603 | ~9.7 배 |

**`RET_noeffect` 의 $\delta_g$ 최솟값(0.036)이 `LOST` 의 median(0.025)보다 크다.** 두 층이
겹치지 않는다. 같은 크기의 섭동을 받고도 한쪽만 뒤집히는 이유가 이것이다.

### 실제로 어떻게 생긴 상황인가 (LOST 예시 3판)

free arc 는 4 개, 각각 폭 ~1.4~1.5 rad. 그중 **최광폭 두 개의 폭 차이가 0.001~0.003 rad**:

| s | n_gaps | 선택 center (rad) | 선택 width | 선택 blocker 쌍 |
|---|---|---|---|---|
| 3 | 4 | 2.147 → **3.962** | 1.543 → 1.542 | [2,3] → [1,2] |
| 2803 | 4 | 0.788 → **4.078** | 1.407 → 1.400 | [0,3] → [1,2] |
| 4002 | 4 | 5.761 → **3.677** | 1.561 → 1.526 | [0,1] → [1,2] |

거의 같은 폭의 두 통로 중 하나를 고르는 상황에서, **11 cm 가 저울을 반대로 기울인다.**
선택 center 가 1.8~3.3 rad 점프하고 blocker 쌍이 바뀐다.

## 3. 완성된 사슬 (sealed A2 world 안에서)

$$ \text{limiter 지령 철회} \rightarrow \Delta p_L \approx 11\ \text{cm}
   \rightarrow \text{각 blocker span } \Delta \approx 0.013\ \text{rad} $$
$$ \rightarrow\ \boxed{\ \delta_g \approx 0.021\ \text{rad 의 near-tie 를 넘김}\ }
   \rightarrow \text{선택 arc 교체} \rightarrow \Delta\theta_{route} = 107° $$
$$ \rightarrow \Delta a_A \approx 16.1\ \text{m/s}^2\ (\text{1 tick})
   \rightarrow \Delta v_A \approx 0.84\ \text{m/s}
   \rightarrow \Delta p_A \approx 42\ \text{mm at } t_F^C
   \rightarrow \text{capture 술어 상실} $$

각 단계가 **앞 단계의 크기로부터 계산되고 관측과 맞는다**. 추상적 "증폭" 이 아니다.

## 4. 앞선 결과와의 정합

- `98-B` **평행이동으로 설명 안 됨** — 맞다. 원인은 회피 *통로 선택*의 교체이고 위치는 결과.
- `99-P` **속력이 층을 가름** — 맞다. 107° 전환이 속도 벡터를 통째로 바꾼다.
- `99-X` **입력 섭동은 세 그룹 동일** — 맞다. 갈리는 것은 **$\delta_g$ 가 섭동보다 작은가**.
- `CJ-audit` **residual ≈ 0** — 맞다. 전부 route 항이었다.

## 5. ⚠ 어휘 lock — 이것은 **A2 정책 구조에 의존하는** 메커니즘이다

- ❌ **physics-only cooperative geometry**
- ✅ **behavior-mediated cooperative geometry under sealed A2**

발견된 것은 "작은 연속 기하 변화가 scripted A2 의 **hard argmax** 를 넘겨 큰 상태 변화를
만든다" 이다. 구체적이지만 **적대자 정책의 이산 선택 구조에 얹혀 있다.**

**두 단계를 합치지 않는다**: boundary crossing ⇒ 큰 상태 이탈 은 말할 수 있으나,
큰 상태 이탈 ⇒ 항상 capture loss 는 아니다 — `RET_effect` 가 서 있는 반례다
(6/10 이 flip 했는데 capture 유지).

**일반성의 시험대**: learned/PFSP attacker 에서도 연속 섭동이 **behavioral decision
boundary 를 통해 확대**되는가, 아니면 A2 의 hard argmax 가 만든 **brittle artifact** 인가.
이것이 docs/97 의 PFSP 카드가 중요한 진짜 이유가 됐다.

## 6. 미확정

- `RET_effect` 10 판은 단일 설명으로 묶지 않는다 (flip 6, 미flip 4, `CJ-audit` 에서
  residual 이 컸다 — route 외 항이 관여).
- **왜 이 판들이 애초에 near-tie 였는가** — CEM 이 near-tie 구성을 *선호*한 것인지
  (그 근방이 제어하기 쉬우므로) 우연인지. 별도 카드.
- $\delta_g$ 를 직접 **설계 변수**로 쓸 수 있는가 (학습 신호 후보) — training contract 논의로.

## 7. 방법론

오늘의 GO gate 오차가 **정확히 0** 이었다는 것은, 어제의 세 오류(docs/98 · docs/99 ·
`100-X`)가 전부 **대조 기준을 authoritative 하게 잡지 않은 것** 하나였음을 확증한다.
규율이 작동했다: 재구현을 허용하되 **시뮬레이터가 실제 쓴 값과 대조**하고, 어긋나면
판독을 **금지**한다.
