# 98 — Capture-margin audit 사전등록 (봉인 — 실행 전)

- **일자**: 2026-09-13 · **지위**: **sealed pre-run** (docs/95 `4a86168` · docs/96 `144ab3d` 선례).
- **분류**: **frozen FIRE state 의 기하 판독**. 새 rollout 도, 새 개입도, 새 world 도 없다.
  B0 v3 (`5e7b5b486b9d8a4a`) 불변. B2 와 병렬.
- **발단 (정정에서 태어난 카드)**: `2026-09-13d` 판독문이 *"성공 plan 은 포획 경계에 걸쳐
  있다"* 고 적었는데 **논리 오류**였다 — `v_shot_worst` 는 **이진** 술어이고 성공이 그
  술어로 **정의**되므로, 46/46 이 1.0 인 것은 **동어반복**이지 여유의 증거가 아니다.
  그 문장은 철회됐고, 본 문서가 **여유를 실제로 측정**한다.

- **질문 (하나)**:
  > **성공한 FIRE state 들은 authoritative capture set 의 내부에 넉넉히 있는가, 아니면
  > 실제 기하 경계 근처에 몰려 있는가?**

---

## §1. 무엇이 아직 안 밝혀졌는가 (범위 고정)

| 확정됨 (steer probe) | 미확정 (본 audit) |
|---|---|
| 이른 limiter 지령 철회가 결과를 파괴 (98% → 41%, 비단조 0/46) | 그 성공들이 **얼마나 빠듯하게** 성공했는가 |
| 의존이 **궤적 매개**이며 near-FIRE 순간 기여는 0 | 술어를 뒤집은 것이 **위치**인지 **속도·heading 을 통한 도달집합 변화**인지 |

$\lVert\Delta p_A(t_F^C)\rVert$ = 9.6 cm 는 **개입이 만든 변위**이지 경계까지의 거리가
아니다. branch 는 위치·속도·heading·이후 도달집합을 **동시에** 바꾼다.

## §2. 지표 — signed geometric margin

현행 judge 는 **`se3_cone`** (기계 확인): 수용 영역
$\mathcal N$ = 원뿔(apex $T_F$, 축 $n_F$, 반각 $\theta_{net}$) $\cap$ 축방향 밴드
$[\,r_{min},\, r_{max}\,]$ — `viability._caught_se3_cone` 그대로.

feasible escape witness $y_j$ 에 대해 ($r_j = y_j - T_F$, $a_j = r_j\!\cdot\! n_F$,
$\alpha_j = \arccos(a_j/\lVert r_j\rVert)$):

$$ m^{lat}_j = \lVert r_j \rVert \sin(\theta_{net} - \alpha_j), \qquad
   m^{ax}_j  = \min(a_j - r_{min},\; r_{max} - a_j) $$

$$ s_j = \min(m^{lat}_j,\; m^{ax}_j), \qquad
   \boxed{\; m_{cap} = \min_j s_j \;} $$

- $m_{cap} > 0$: 모든 feasible escape 가 **안쪽**. 그 값이 곧 여유 (미터).
- $m_{cap} = 0$: 실제 기하 경계.
- $m_{cap} < 0$: 적어도 하나가 밖 (성공 판에서는 나오지 않아야 한다 — **자기검증**).

**성분을 보존한다**: $m^{lat}$ 과 $m^{ax}$ 를 따로 싣고, argmin 에서 **어느 제약이
binding 인지** (`lateral` / `axial`) 를 기록한다. 하나의 스칼라로 뭉개지 않는다.

**predicate 재구현 금지**: 같은 `net_apex` · `n_F` · `theta_net` · `range_*` 를 env 경로에서
받아 쓰고, **부호만** `_caught_se3_cone` 의 참/거짓과 일치하는지 매 witness 확인한다
(`sign(s_j) > 0 ⟺ caught_j`). 불일치 = margin 정의가 judge 와 다른 것이므로 그 판 폐기.

## §3. 표본 · 비용

- **primary**: multi-dependent **46** 판의 reference FIRE state. **secondary**: 나머지 94.
- 판당 **reference replay 1 회** (봉인 plan, search 0) → $t_F^C$ 틱에서 union 재구성 →
  witness 별 $s_j$. 실측 ~1.7 s/replay 이므로 140 판 ≈ **4 분, 로컬 가능** (랩서버 불요).

## §4. [실행 전 고정] 판독 3-분기

| 분기 | 조건 | 결론 | 다음 |
|---|---|---|---|
| **A** | $m_{cap}$ 분포가 **cm 급** | **precision capture-state threading** — "threading" 어휘 채택 가능 | reward 가 그 여유를 분해할 수 있는지 감사 |
| **B** | $m_{cap}$ 이 **넉넉한데** withdrawal 이 술어를 뒤집었다 | 본질은 위치가 아니라 **속도·heading → 도달집합** 변화. **state steering, not positional threading** | 무엇이 도달집합을 바꾸는지 |
| **C** | binding witness 가 **0 근처에 몰림** | CEM 이 물리가 아니라 **judge 의 유한 witness / 이산화 가장자리**를 exploit 했을 가능성 | **최우선 조사** — 사실이면 논문 톤 전면 수정 |

**분기 C 는 나쁜 소식이 아니라 반드시 알아야 하는 것**이다. 그래서 먼저 뽑는다.

## §5. [필수] 유한 witness caveat — 측정의 방향성

코드 주석이 이미 선언한다: `v_shot_worst == 1` 은 **"no SAMPLED witness escapes"** 다
(`viability.py` L235 부근). 따라서 표본 위에서 잰 $m_{cap}$ 은

$$ m_{cap}^{\text{sampled}} \;\ge\; m_{cap}^{\text{true}} $$

즉 **여유를 과대평가한다** (min 을 부분집합 위에서 잡으므로). 그러므로:

- **분기 A ("여유가 작다") 는 이 편향에 대해 안전하다** — 과대평가된 값조차 작다면 진짜 작다.
- **분기 B ("여유가 크다") 는 안전하지 않다** — 샘플링이 최악 방향을 놓쳤을 수 있다.
  B 가 나오면 witness 수를 늘려 **재확인**해야 하며, 그 재확인 전에는 B 를 확정하지 않는다.

이 비대칭을 판정문에 **반드시 함께 적는다.**

**부수 기록**: `n_feasible` · binding witness 의 block id 와 방향이
`_extreme_dirs` 의 결정론적 축(±x/±y/±z, ±heading)인지 여부 — 분기 C 의 직접 증거.

## §6. 어휘 lock

- $m_{cap}$ 을 "capture probability" 로 환산하지 않는다.
- **분기 A 확정 전에는 "threading" · "경계에 얹는다" 계열 표현 금지** (철회된 문장이 바로
  그것이다).
- "the capture margin was X cm" 는 $m_{cap}$ **에만** 쓰고, $\Delta p_A$ 에는 절대 쓰지 않는다.
- 유한 witness caveat (§5) 없이 분기 B 를 서술하지 않는다.

## §7. 지위 선언

- descriptive geometry read. CI·가설검정 없음.
- 본 audit 결과로 B0 v3 · docs/96 판정(BRANCH 1)을 바꾸지 않는다 — **그 판정은 개입 대비
  결과로만 서 있고 여유와 무관하다.**
- 산출물 `artifacts/r2b/margin_audit.json` · 상태 **R2-CAMPAIGN**.
