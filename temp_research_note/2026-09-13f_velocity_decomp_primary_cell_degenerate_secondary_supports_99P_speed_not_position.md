# 2026-09-13f — velocity decomposition: **주력 셀이 퇴화**, 보조 셀이 **99-P (속력)** 를 지지. 위치는 층을 못 가른다

- **입력**: steer probe 저장분만. **재실행 0.** 규칙은 docs/99 에서 **계산 전 봉인**
  (`7d7bf2b`). 코드 `shepherd/scripts/r2b_velocity_decomp.py` →
  `artifacts/r2b/velocity_decomp.json`.
- **표본**: multi-dependent 46. 자기검증 ($\Delta v_\parallel^2 + \Delta v_\perp^2 =
  \lVert\Delta v\rVert^2$) **전건 통과, skip 0**.
- **지위**: descriptive **association**. 같은 개입이 네 성분을 동시에 움직이므로
  **어느 성분도 "원인" 이라 쓰지 않는다** (docs/99 §5).

---

## 1. ⚠ 봉인된 주력 셀 ρ=0.75 는 **퇴화했다**

| ρ=0.75 (LOST 15 / RET 31) | lost | retained | ratio |
|---|---|---|---|
| `abs_ds` | 0.1052 | 0.0003 | **320.8** |
| `dtheta` | 0.0397 | 0.0002 | 248.3 |
| `abs_dv_par` | 0.0723 | 0.0003 | 220.4 |
| `dv_perp` | 0.8299 | 0.0029 | 286.3 |
| `dp_norm` (통제) | 0.0418 | 0.0002 | **184.6** |

**네 성분과 통제변수가 한꺼번에 184~321 배로 부푼다.** 원인은 분모다 —
**RETAINED 31 건 중 68% 가 $\lVert\Delta p\rVert < 1$ mm**, 즉 **개입이 표적에 사실상
아무 일도 하지 않은 판**이다. 그 층에서는 "어느 성분이 큰가" 가 아니라 "아무것도 안
변했다" 가 답이므로, 비율 비교가 **어느 성분이 층을 가르는지 말할 수 없다.**

⇒ 봉인 규칙은 이 셀에서 `99-P` 를 냈지만 **그 판정은 채택하지 않는다.**

> **[부수 사실]** ρ=0.75 에서 철회가 자주 아무 효과도 없다 (RETAINED 의 68%).
>
> **⚠ [정정 — 같은 날, 99-X 진단 결과]** 여기서 제가 "limiter 의 영향 창이 FIRE 전에
> 이미 닫힌다" 고 적었던 것은 **틀렸다**. 99-X 가 첫 인과 차이를 직접 재보니 세 그룹
> 모두 **동일한 크기의 섭동**이 표적에 전달된다 (t_w+1 에서 A2 지령 차 ~0.008 m/s²).
> 창은 닫히지 않는다 — 갈리는 것은 그 섭동이 **증폭되는가** 여부다
> (무효과군 1.0× vs 나머지 270~330×). 상세 = `2026-09-13g` · `99-X`.

## 2. 보조 셀 ρ=0.5 가 정보를 가진 셀이다

LOST 38 / RET 8, RETAINED 중 null-effect 는 **1/8 뿐** — 양 층 모두 실제로 움직였다.

| ρ=0.5 | lost | retained | ratio |
|---|---|---|---|
| **`abs_ds`** (속력) | 0.1366 | 0.0068 | **20.07** |
| **`abs_dv_par`** (진행축 성분) | 0.0794 | 0.0066 | **11.96** |
| `dtheta` (heading) | 0.0552 | 0.0137 | 4.04 |
| `dv_perp` (횡성분) | 1.1271 | 0.2968 | 3.80 |
| **`dp_norm` (통제)** | 0.0725 | **0.0954** | **0.76** |

**통제변수가 결정적이다.** 위치 변위는 층을 가르지 **못한다** — 오히려 **RETAINED 쪽이
더 크다** (95.4 mm vs 72.5 mm). 반면 속력 변화는 **20 배** 차이가 난다.

⇒ **`99-P` (speed / timing steering) 를 지지**한다. 그리고 이것은 `98-B` 의
*"position translation alone is insufficient"* 와 **같은 방향에서 독립적으로** 나온다:
98-B 는 $\Delta p$ 와 $m_{cap}$ 비교로, 여기서는 $\Delta p$ 가 층을 못 가른다는 사실로.

ρ=0.25 는 `99-N` 이 나왔으나 **RETAINED n=1** 이라 판독 불가 (기록만).

## 3. [DEVIATION] 사전등록 대비

> **preregistered primary cell (ρ=0.75) was degenerate; the reading is taken from the
> secondary cell (ρ=0.5).**

docs/99 §3 은 ρ=0.75 를 주력으로 지정했다. 그 지정 근거("15 잃고 31 유지하니 timing 고정한
채 비교 가능")는 **RETAINED 층의 대부분이 무효과 판이라는 사실을 몰랐기 때문**에 성립하지
않았다. 봉인 문서는 **수정하지 않고** 여기 기록한다.

**규칙 설계 결함 (2 연속)** — 정직하게 남긴다:

| 문서 | 결함 |
|---|---|
| docs/98 | 크기 판정(<10cm 과반)에 **메커니즘 결론을 직접 묶음**. 비교 대상 $\Delta p$ 가 규칙에 없었다 |
| docs/99 | median **비율**을 쓰면서 **분모가 0 에 붙는 경우의 가드가 없었다** |

공통 패턴: **분모·비교 기준을 규칙 안에 넣지 않았다.** 다음 사전등록부터 비율·임계
지표를 쓸 때 (i) 분모의 퇴화 조건 (ii) 통제변수를 **규칙 본문에** 함께 박는다.

퇴화 진단(`frac_null_effect`)은 결과를 본 뒤 코드에 추가했으나 **분기 키를 바꾸지 않는
주석 전용**이며, 그 사실을 코드 주석과 docstring 에 명시했다.

## 4. 지금 말할 수 있는 것

**확정 (변동 없음)**

- `96-BR1` 이른 지령 철회가 포획을 파괴한다. `98-B` 여유는 실재(~11 cm)하고 표본 인공물이
  아니다. **position translation alone is insufficient.**

**본 분해가 더한 것 (보조 셀, n_ret=8 — 작다)**

> **AUTH-LOST records are distinguished primarily by a change in attacker SPEED
> ($\lvert\Delta s\rvert$ ratio 20.1, $\lvert\Delta v_\parallel\rvert$ 12.0), while
> FIRE-time position displacement does not separate the strata at all (ratio 0.76).**

즉 방향(heading·횡성분, 4 배 내외)보다 **종축 속력**이 훨씬 강하게 갈린다.

**여전히 아님**

- "속력 변화가 포획 상실을 **야기했다**" — 연관이지 인과 아님 (동시 변화).
- "도달집합의 **모양**이 바뀌었다" — 본 문서가 재지 않았다.
- `99-P` **확정 선언** — 주력 셀 퇴화 + 보조 셀 n_ret=8. **잠정**으로만.

## 5. training contract 함의 (더 구체화)

메커니즘이 **표적의 종축 속력**과 얽혀 있다면, 이는 "언제 도달하는가" = **timing** 이다.
그런데 현행 dense 신호는 **현재 상태를 고정한 순간 반사실**이라 timing 을 구조적으로 못
본다. potential $\Phi(x_t)$ 후보는 **표적의 도달 timing 대비 capturer 준비 상태**를 보는
쪽이 자연스럽다 — 단 §4 의 "아님" 항목이 풀린 뒤 설계한다.

## 6. 다음 카드 후보

1. **RETAINED 무효과 판의 정체** — ρ=0.75 에서 왜 철회가 아무 일도 안 하는가
   (limiter 가 이미 `sense_range` 밖인가?). 재실행 0, steer probe 의 `p_lims_at_tw` 로 확인 가능.
2. 도달집합 모양 직접 비교 (reference vs branch union) — 재실행 필요, 비용 중간.
3. docs/97 결재 · repo-R2/R3.
