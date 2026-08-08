# 73 — 리뷰 10 판정 로그 (방향 전환 심사) + 즉시 이행 목록

**2026-08-09 · 요청 = `docs/review_prompt_design_map_pivot.md` · 대상 = spine 교체
(학습 이득 증명 → 메커니즘 성립 조건). 결과 = **전환은 조건부 승인, 현 서술로는
불승인**. 이 문서는 판정 원문 요지 + 우리 이행 결정을 기록한다. 반론 없이 전부 수용.**

## 1. 판정표

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| 1 | Q-A 축 교체 | **CONDITIONAL** | chronology 잠금 = `docs/74_pivot_protocol.md` (오늘 날짜) |
| 2 | F2 "협력 marginal value = 0" | **REJECT** | **철회.** 표현 하향 + `V_1^*` vs `V_N^*` 정의로 재설계 |
| 3 | 충분경계 upper certificate | **RATIFY (필수)** | 3층 계획 채택 (finite-witness exact → continuous outer relax → unblockable-mass) |
| 4 | Q-B 파라미터 축 승격 | **CONDITIONAL (거의 RATIFY)** | 파라미터를 4 종으로 **분류** + 구간 출처 사전 고정 |
| 5 | C5 재실행 | **CONDITIONAL** | adaptive two-stage + 결정론적 선택규칙 + **3 regime 동시** |
| 6 | F1 라벨 반전 | **REJECT — 현 regime 정의** | `0.5aτ²>ρ` 는 **proxy** 로 강등, regime 은 `V_0/V_N^*` 로 재정의 |
| 7 | θ_fire 축 | **CONDITIONAL** | miss-risk/탄약경제 주장 금지. "viability-envelope sensitivity" 로만 |
| 8 | 대안 프레임 | **RATIFY** | spine = *Feasibility-First Design of Cooperative Single-Shot Counter-UAS Interception under Deployment Latency* |
| 9 | Q1 증거 bar | **CONDITIONAL** | 3층(geometry certification / RL / robustness) 채택, 통계단위 = **episode** |
| 10 | 19주에 C1~C5 전폭 | **REJECT — 현 범위** | C2 + **축소** C3 + C5 유지, 나머지 spot-check/후속 |
| 11 | desk-reject 문장 | **RATIFY (실재 위험)** | §4 에 전문 인용, 19주 연구의 방어 목표로 등재 |

## 2. 즉시 철회하는 문장 3건 + 1 (오늘 기록에서 하향)

| 철회 | 대체 표현 |
|---|---|
| "결정 대역 = a_att ∈ [36, 39]" | "seed 0 의 선택된 스냅샷 · 테스트된 relaxed 탐색에서 **문턱 교차가 관측된 이산 점들**" (연속 구간도, 실제 시스템 feasibility band 도 아니다) |
| "N_req = 1 → 협력의 marginal value 가 기하적으로 존재하지 않는다" | "테스트된 relaxed 배치 탐색에서 발견된 모든 문턱 교차는 **첫 번째 봉쇄 구**로 달성됐고, 추가 구에서 표본 이득이 없었다" |
| "병목은 봉쇄 공급량이 아니다" | "후보 조밀화·구 추가가 빠르게 포화 → **요격기 수 단독이 지배적 병목은 아닐 수 있다**는 시사" |
| "그리디이므로 달성가능 하한" | "**relaxed static-placement 문제의 최적에 대한 하한**". 실제 시스템 최적 `V_N^actual` 과는 **순서관계 없음** (teleporting 배치가 1기에 유리하게 편향) |

또한 `N_req` 정의 오류 수정: `v_hold ≥ θ` 인 점(a_att 15/20/30)은 **N_req = 0** 이다.
정의는 `N_req = min{N ≥ 0 : V_N^* ≥ θ}`.

## 3. 채택하는 재정의 (새 연구에만 적용 — 동결 블록은 불변)

```
V_0(x)      = v_hold                         (무개입)
V_1^*(x)    = 1 기 최적                       ★ N=1 대조군이 논문의 핵심
V_N^*(x)    = admissible N-agent 전략의 최대
FREE                : V_0 >= theta
COOP DECISION BAND  : V_0 < theta <= V_N^*
INFEASIBLE FOR N    : V_N^* < theta   ← **certified upper bound 있을 때만** 이 이름
NO_SOLUTION_FOUND   : 상한 없이 못 찾은 경우 (기본값)
협력 가치           : Delta_coop,N = V_N^* - V_1^*
협력 유효 집합       : W_{2:N} = { x : 2 <= N_req(x) <= N }   (measure 0 이면 협력 무가치)
```

- `chi = a_att·tau^2 / (2·rho_net)` 은 **free-capture analytic proxy** 로 강등.
  **"필요 경계는 닫힌형 a* = 2rho/tau^2" 문장은 삭제**(포획면이 등방 볼이 아니라
  SE(3) 원뿔 + 축방향 밴드이므로 scalar 비교로 clean-fire 필요조건을 정의할 수 없다).
- 축은 raw 6 knob 대신 **무차원**: `chi`, `kappa = r_kill/rho`, `mu = a_lim/a_att`
  (필요시 `eta = v_att·tau/rho`). 6D Cartesian sweep 폐기.
- **★ 동결 경계**: 진행 중인 docs/71 ablation 은 `regime_of` (기존 정의·기존 이름)
  로 계속 판정한다. 위 재정의는 **새 연구의 언어**이고 동결 블록에 소급 적용하지
  않는다 (그렇게 하면 primary 를 결과 후 바꾸는 것이 된다).

## 4. 방어 목표 (desk-reject 문장 — 원문)

> "The manuscript retrospectively recasts a failed MARL study as a systems-design
> result, but its claimed viability boundaries and requirements are properties of
> an unvalidated simulator whose decisive latency, kill radius, firing threshold,
> and threat capability were chosen by the authors rather than grounded in a
> physical context of use."

이 문장을 막는 것이 남은 19주의 정의다. 대응 축: (i) `v_shot` measure 정의·수렴,
(ii) upper/lower certificate 분리, (iii) 파라미터 분류 + 구간 출처 사전 고정,
(iv) hardware/context anchor 1 개 (없으면 "requirement" 대신 **design envelope /
parametric requirement curve** 로 표기), (v) latency/noise spot-check.

## 5. 즉시 착수 3 (리뷰어 지정 순서 그대로)

1. **`v_shot` measure 고정** — 2000 위트니스 "비율"이 어떤 measure 를 근사하는지
   정의하고 witness allocation·수렴(2k/8k/32k)·sampling-family 가중 민감도를 검증.
   이게 없으면 theta·band·requirement 전부 sampling artifact 공격 대상.
2. **regime 재정의 + certificate 분리 + N=1 대조군 승격** (§3). relaxed oracle 과
   reachable-system feasibility 를 절대 섞지 않는다.
3. **pivot protocol 잠금** — 오늘 결과를 exploratory 로 봉인, 지도 구성·범위·
   C5 선택규칙·inside/outside 대조·반증조건을 **결과 보기 전에** 고정.
   → `docs/74_pivot_protocol.md`

## 6. 폐기 3

1. `SHAPING_NEEDED` / `FREE_CAPTURE` 라는 **이름** (새 연구에서. 데이터가 정의를
   반증했다 — 동결 블록의 코드 라벨은 그대로 둔다).
2. 6 raw 파라미터 대규모 Cartesian sweep → 무차원 2~3 축.
3. **"MARL 이 이기는 논문"에 대한 미련.** MARL 은 이제 **mechanism validation
   instrument** 이고, 논문의 독립변수는 알고리즘이 아니라 feasibility 구조다.

## 7. Q1 증거 bar (수용 요약 — 상세는 리뷰 원문)

- **geometry**: a_att 당 1 에피소드 금지 → 조건당 **20~30 독립 realization**,
  경계 adaptive refinement, witness 수렴(2k/8k/32k spot-check), 가중 민감도,
  greedy ↔ global/upper-bound solver 비교, relaxed ↔ reachable 분리.
  **통계단위 = episode** (위트니스 2000 을 독립표본으로 bootstrap = pseudoreplication).
- **map**: 무차원 2~3 연속축 + N 이산곡선 + mobility 2~3 층 + 공격자 분포 적분.
- **learning (C5)**: FREE / band 내부 / high-difficulty 3 regime, 점당 **시드 5 최소**
  (8~10 권장), held-out 300 paired, 기준선 = hold · arc scripted · MARL ·
  **reachable 1-limiter** · oracle envelope. 4기 협력 주장에는 **N=1 대조군 필수**.
- **통계**: 시드 최상위 hierarchical CI, paired 차이, effect size + 95% CI,
  0 카운트는 binomial 상한 병기, 지도 경계에도 bootstrap band.
- **realism**: 대표 3 regime × 2~3 점에서 delay jitter · sensing noise · actuator lag
  spot-check (주인공이 tau 인데 judge 에 stochasticity 가 없으면 반드시 찔린다).

## 8. 일정 (리뷰어 상한 그대로 채택)

| 주 | 내용 |
|---|---|
| 1~2 | 정의 교체 + witness measure/수렴 + optimization·certificate |
| 3~6 | map + 수렴 + 경계 불확실성 |
| 7 | C5 규칙·시드·해시 **freeze** |
| 8~11 | C5 학습·평가 |
| 12~14 | robustness spot-check |
| 15~19 | 논문·보고서 |

유지 = C2 + 축소 C3 + C5. spot-check = 6DOF/noise/hardware. **넣지 않음** =
optimal stopping · sensing-latency cooperation · multi-shot (= paper 2).

## 9. 상위 발견의 재서술 (리뷰어 제안 채택)

> **기존 연구 설계가 '협력이 필요한 영역'을 실제 cooperative advantage 존재와
> 무관한 scalar kinematic proxy 로 정의하고 있었고, 그 결과 policy learning 전에
> 확인했어야 할 feasibility question 이 빠져 있었다.**

이것이 논문의 상위 주장이다. `[36,39]` · `N_req=1` · "병목은 tau·theta·cone" 을
확정 사실로 밀면 그 순간 전환이 goalpost moving 으로 보인다 — §2 의 하향 표현을
모든 산출물·발표에 적용한다.
