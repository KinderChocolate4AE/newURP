# 101 — Route-choice boundary audit 사전등록 (봉인 — 실행 전)

- **일자**: 2026-09-14 · **지위**: **sealed pre-run**, 증거 등급 **exploratory**
  (docs/100 과 같은 규율 — post-hoc 가설을 고정 규칙으로 추적하는 것이지 confirmatory 아님).
- **분기 라벨**: **`101-A`** (score-order crossing) · **`101-B`** (topology crossing) ·
  **`101-N`** (GO gate 실패 → 판독 금지).

> **[라벨 정정]** commit/jink audit (`3d1f5d6`) 을 문서 없이 "101-X" 로 불렀는데,
> `<doc number>-<branch>` 규약과 어긋난다 (docs/101 은 본 문서다). 앞으로 그 카드는
> **`CJ-audit (3d1f5d6)`** 로 인용한다. 과거 커밋·노트는 수정하지 않는다.

- **`100-X` 는 수정해 살리지 않는다.** 측정 버그로 **무효인 채 유지**하고, 본 문서가
  authoritative 경로로 **처음부터 다시** 묻는다.

- **질문 (하나)**:
  > **11 cm 수준의 limiter 궤적 차이가 왜 A2 의 route request 를 107° 뒤집었는가?**

---

## §1. 배경 (확정된 것만)

`CJ-audit` 이 env 자신의 `diag["route_req"]` 로 확인한 것:

- LOST **15/15** 에서 fire−1 에 route 방향 **1.87 rad (107°)** 전환, `d_a_route` 16.99,
  **residual 0.0024** (다른 항 기여 없음), `committed` 불일치 **0**.
- RET_noeffect 는 같은 틱에 flip **0/21**.
- 산술 폐합: 16.14 m/s² × 0.05 s = 0.807 m/s (관측 0.835) → 40.3 mm (관측 41.8 mm).

**미답**: 왜 그 전환이 일어났는가.

## §2. GO gate — **authoritative comparator** (본 규율의 첫 적용)

`100-X` 가 실패한 이유는 재구현을 **내 코드와** 대조했기 때문이다. 이번에는 재구성한
free-arc 계산이 **시뮬레이터가 실제 쓴 값**과 일치해야만 판독한다.

실제 경로와 **동일하게** ( `attacker_ladder._route_accel` / `_general_action` 그대로 ):

$$ \hat f = \operatorname{unit}(p_{target} - p_{att},\ \text{fallback}=v_{att}) $$

(`100-X` 는 여기서 $\operatorname{unit}(v_{att})$ 를 썼다 — 그 한 줄이 전부였다.)

$$ \boxed{\ \text{GO} \iff \bigl\lVert a_{route}^{\text{reconstructed}}
   - a_{route}^{\texttt{diag}} \bigr\rVert \le 10^{-9}\ \text{— 전 tick · 양 궤적}\ } $$

**하나라도 깨지면 그 판의 $\delta_g$ 판독을 금지**하고 제외 사유와 함께 보고한다.
(`repel_margin = 1.0` · `a_lat_max = adv_a_max` · `sense_range` 30 m — env 배선 그대로.)

## §3. 기록 — $\delta_g$ 만 남기지 않는다

divergence 직전 tick 을 중심으로, ref/branch **양쪽**에서 매 tick:

| 항목 | 이유 |
|---|---|
| 전 free-arc 의 `(width, center, left, right)` | 후보 집합 자체를 보존 |
| top-2 의 width $g_1, g_2$ · center 각 · endpoint | 순위 비교의 원자료 |
| $\delta_g = g_1 - g_2$ | near-tie 여부 |
| **선택된 arc 의 center** | 실제 출력과 연결 |
| **각 merged blocker 구간의 기여 limiter index** | gap 을 만든 **blocker pair** |
| `n_ahead` (전방·감지범위 내 limiter 수) | topology 변화의 가장 깨끗한 신호 |
| `n_gaps` | 후보 개수 |

**$\delta_g$ 가 작지 않게 나올 가능성을 미리 인정한다.** 그 경우에도 107° 전환은 사실이며,
원인이 near-tie 가 아니라 **조합적 위상 변화**일 수 있다 (§4).

## §4. [실행 전 고정] 판독 2-분기 + null

divergence tick 에서 ref 와 branch 의 후보 집합을 비교한다.

**후보 대응 규칙 (사전 고정)**: `n_gaps` 가 같고, center 각으로 정렬해 일대일 대응시켰을 때
**최대 center 이동 ≤ 0.3 rad** 이면 "같은 후보 집합" 으로 본다. 그 외는 topology 변화.
> 0.3 rad 은 제가 고른 값이다. 근거는 11 cm 섭동이 ~8.5 m 에서 만드는 bearing 표류
> ≈ 0.013 rad 의 **20 배** 여유라는 것뿐이다. 결과가 이 값 근처에서 갈리면 명시한다.

| 분기 | 조건 | 결론 |
|---|---|---|
| **`101-A`** score-order crossing | 후보 집합 동일 **∧** top-2 순위가 뒤집힘 | **near-tie argmax separatrix** — 처음 상상한 그림. $\delta_g$ 가 작아야 정합 |
| **`101-B`** topology crossing | 후보 집합이 다름 (split / merge / 생성 / 소멸, 또는 `n_ahead` 변화) | **free-space topology transition** — 같은 후보의 순위 문제가 아니다 |
| **`101-N`** | GO gate 실패, 또는 divergence tick 에 flip 이 없음 | 판독 금지 / 해당 없음 |

**두 분기 모두 유효한 결과다.** `101-B` 가 나와도 "δ_g ≈ 0 이었다" 로 몰지 않는다.

## §5. 비교군 (동결 승계 — 재정의 금지)

`99-X` 의 **`LOST` 15 · `RET_effect` 10 · `RET_noeffect` 21**.
각 판의 **실제 route divergence 직전 tick** 을 중심으로 본다 (LOST 는 fire−1 이지만
`RET_effect` 는 fire−3 에 몰려 있어 판마다 다르다 — **판별은 각 판의 flip tick 기준**).

기대 형태 (맞으면 사슬이 닫힌다):

- `LOST`: 15/15 route discontinuity, 직전 tick 의 margin 또는 topology 가 민감
- `RET_noeffect`: 같은 크기 섭동에도 순위·위상 **유지**
- `RET_effect`: 일부 flip 하나 최종 capture 는 유지

## §6. 어휘 lock — **A2 validity 경고를 함께 보존한다**

지금 발견된 메커니즘이 "작은 연속 기하 변화가 scripted A2 의 **이산 route 선택 경계**를
넘겨 큰 상태 변화를 만든다" 라면, 이는 구체적인 동시에 **A2 정책 구조에 의존**한다.

- ❌ **physics-only cooperative geometry** 로 일반화 금지.
- ✅ **behavior-mediated cooperative geometry under sealed A2**.
- learned/PFSP attacker 에서도 연속 섭동이 **behavioral decision boundary 를 통해 확대**되는지,
  아니면 A2 의 hard argmax 가 만든 **brittle artifact** 인지가 일반성의 시험대다
  (docs/97 후속 카드와 연결).
- 두 단계를 합치지 않는다: **boundary crossing ⇒ 큰 상태 이탈** 은 말할 수 있어도
  **큰 상태 이탈 ⇒ 항상 capture loss** 는 아니다 (`RET_effect` 가 반례).

## §7. 지위

- exploratory. CI·가설검정 없음. necessity 아님. B0 v3 불변.
- `96-BR1` · `98-B` · `99-P` · `CJ-audit` 판정을 바꾸지 않는다.
- 산출물 `artifacts/r2b/route_boundary_audit.json` · 상태 **R2-CAMPAIGN**.
