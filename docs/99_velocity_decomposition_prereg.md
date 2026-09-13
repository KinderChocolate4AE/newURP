# 99 — Velocity-state decomposition 사전등록 (봉인 — 계산 전)

- **일자**: 2026-09-13 · **지위**: **sealed pre-run**. **재실행 0** — steer probe 가 이미
  저장한 $t_F^C$ 스냅샷만 쓴다 (`delta_at_ref_fire.ref.v_att` / `.branch.v_att`).
  재실행이 없을수록 "계산 먼저, 규칙 나중" 의 유혹이 크므로 **규칙을 먼저 봉인**한다.
- **분류**: frozen artifact 재분석. 새 world·개입·rollout 없음. B0 v3 불변. B2 와 병렬.

---

## §0. [프로젝트 규약] cross-document branch 참조

분기 라벨이 문서마다 겹쳐 혼동이 실제로 발생했다 (95/96 은 1·2·3, 98 은 A·B·C).
**문서 내부 라벨은 그대로 두고**, 문서를 넘나드는 참조에서는 다음을 **정본 표기**로 쓴다:

$$ \texttt{<doc number>-<branch label>} $$

예: `95-BR2` · `96-BR1` · `98-B`. 용례 —

> `96-BR1` established prefix-dependent steering; `98-B` rejected the near-boundary
> explanation.

**본 문서부터 적용**한다. 과거 문서는 소급 수정하지 않는다.

## §1. 무엇이 아직 증명되지 않았는가

`98-B` 로 확정된 것은 **하나뿐**이다:

> **position translation alone is insufficient to explain the predicate loss.**

$\Delta p \le m_{cap}$ 인 판에서도 authoritative 조건이 96% 뒤집혔다는 관찰이 그 근거다
(post-hoc). 그러나 branch 는 $t_F^C$ 에서 **위치·속력·진행방향·capturer 상대기하**를
동시에 바꾸므로, **속도·heading 이 원인이라는 것은 가장 유력한 후보일 뿐 미증명**이다.
본 문서가 그 성분을 분리한다.

## §2. 봉인 지표 — 4 성분 (raw $\lVert\Delta v\rVert$ 하나로 뭉개지 않는다)

reference 속도 $v^C$, branch 속도 $v^W$ (둘 다 $t_F^C$ 의 이동 전 상태):

$$ \Delta s = \lVert v^W \rVert - \lVert v^C \rVert
   \qquad\text{(속력 변화, 부호 유지)} $$

$$ \Delta\theta = \arccos\frac{v^W\!\cdot v^C}{\lVert v^W\rVert\,\lVert v^C\rVert}
   \qquad\text{(heading 변화)} $$

$$ \Delta v_\parallel = (v^W - v^C)\cdot\hat v^C, \qquad
   \Delta v_\perp = \bigl\lVert (v^W - v^C) - \Delta v_\parallel\,\hat v^C \bigr\rVert $$

**퇴화 처리 (사전 고정)**: $\lVert v^C\rVert$ 또는 $\lVert v^W\rVert < 10^{-9}$ 이면
$\Delta\theta$ 를 결측으로 싣고 비율 통계에서 제외한다 (0 으로 채우지 않는다).

**자기검증**: $\Delta v_\parallel^2 + \Delta v_\perp^2 = \lVert\Delta v\rVert^2$ 가
저장된 `dv_norm` 과 일치해야 한다 (tol 1e-9). 불일치 = 분해 오류 → 그 판 폐기.

## §3. 층화 — **AUTH-LOST vs AUTH-RETAINED** 가 본론

$\rho$ 별 median 만 보지 않는다. 각 $\rho$ 에서 **개입 시점을 고정한 채**
$t_F^C$ 에서 authoritative 조건 (`¬boxed_in ∧ v_shot_worst ≥ 1`) 을

- **LOST** (`d_v_worst < 0`) vs **RETAINED**

로 나누고, 네 성분 + $\lVert\Delta p\rVert$ 의 분포를 **두 층에서 비교**한다.

> **$\rho = 0.75$ 가 주력 셀이다.** 같은 개입에서 15 건이 잃고 31 건이 유지하므로,
> **개입 timing 이 동일한 상태에서 무엇이 갈랐는지**를 직접 볼 수 있다. 나머지 $\rho$ 는
> 보조 (파괴율이 너무 높아 층이 한쪽으로 쏠린다).

$t_F^C$ 에 도달하지 못한 판 (P/T) 은 $\Delta$ 가 정의되지 않으므로 **건수만** 싣는다.

## §4. [실행 전 고정] 판독 3-분기

기준은 **AUTH-LOST 층에서 무엇이 RETAINED 층보다 큰가** (ρ=0.75 주력):

| 분기 | 조건 | 결론 |
|---|---|---|
| **99-P** | $\lvert\Delta v_\parallel\rvert$ 가 지배적으로 분리 | **speed / timing steering** — 표적이 언제 도달하는가를 바꾼다 |
| **99-D** | $\Delta\theta$ · $\Delta v_\perp$ 가 지배적으로 분리 | **directional steering** — 표적이 어디를 향하는가를 바꾼다 |
| **99-N** | 네 성분 모두 두 층을 가르지 못함 | 표적 속도만으로 불충분 → **capturer 상대기하 / pointing state** 를 봐야 한다 |

**"지배적으로 분리" 의 기계 판정**: 두 층의 median 비 $r = \mathrm{med}_{LOST} /
\mathrm{med}_{RET}$ 를 네 성분에 대해 계산하고, **가장 큰 $r$ 을 갖는 성분**이 분기를
정한다. 단 **최대 $r < 1.5$ 이면 99-N** (어느 것도 층을 가르지 못한 것으로 본다).
$\lVert\Delta p\rVert$ 도 같은 방식으로 계산해 **대조**로 싣는다 — 위치가 함께 크면
"속도가 갈랐다" 는 결론이 약해지므로 반드시 같이 본다.

> 1.5 는 **제가 정한 수치**다. 근거는 "층을 가른다고 말하려면 최소한 median 이 1.5 배는
> 차이나야 한다" 는 관례적 판단뿐이고 실측 근거가 없다. 결과가 이 값 근처에서 뒤집히면
> **그 사실을 판독문에 명시**하고 분기를 확정하지 않는다.

## §5. 어휘 lock

- 본 분해는 **연관(association)** 이다. $\Delta\theta$ 가 크게 갈린다고 해서
  "heading 변화가 포획 상실을 **야기했다**" 고 쓰지 않는다 — 같은 개입이 네 성분을
  동시에 움직이므로 성분 간 인과 분리는 본 설계로 불가능하다.
- 허용: **"AUTH-LOST records are distinguished primarily by X"**.
- 금지: `99-N` 이 아닌 한 "velocity alone explains it" · 그리고 어느 분기에서도
  "reachable-set shape change is caused by …" (도달집합 모양은 본 문서가 재지 않는다).
- `98-B` 의 한 문장은 그대로 유효하며 본 문서가 그것을 약화시키지 않는다.

## §6. 지위

- descriptive association analysis. CI·가설검정 없음. necessity 아님.
- 산출물 `artifacts/r2b/velocity_decomp.json` · 상태 **R2-CAMPAIGN**.
- 본 결과로 `96-BR1` · `98-B` 판정을 바꾸지 않는다.
