# 74 — PIVOT PROTOCOL (전환 기록·봉인) — 2026-08-09

**리뷰 10 (docs/73) 항목 1 의 이행. 이 문서는 지도 셀을 **한 칸이라도 더 보기 전에**
작성됐다. 목적은 chronology 를 숨기지 않고 못박는 것이다: Phase I 의 실패,
Phase II 의 post-hoc 진단, Phase III 의 사전등록 파라미터 연구를 서로 섞지 않는다.**

기준 커밋 = `a1a784e` (2026-08-09T01:56+09:00). 이 시점 이후의 모든 지도 산출물은
아래 §3~§4 계약 하에서 생성된다.

---

## 1. Phase I — 원 spine 과 그 결과 (변경 금지·소급 재해석 금지)

- **가설**: 동결된 TRAIN 위협 분포·동결 학습계약에서, 협력 shaping 을 학습한
  MARL 팀이 손설계 기준선보다 비파괴 net 포획률(p_net)을 높인다.
- **primary metric**: held-out **IID 10000..10299 (n=300) paired**, lexicographic
  Δ_net = p_net^MARL − p_net^scripted (docs/63 r2).
- **기준선**: hold(무개입) / bearing-aware arc scripted (TRAIN 선택 c5, p_net 0.110).
- **결과 (커밋된 사실)**:
  - LL (전부 학습) 무력화 **0/300** — SHAPING 0/164 · FREE 0/136.
  - LS (편대만 학습 + 발사 scripted) **49/300 = 0.163** — FREE 49/136 (0.36) ·
    **SHAPING 0/164**.
  - hold SHAPING 사전측정 **0/122**.
- **현재 진행 중이며 미열람인 것**: docs/71 r1 LS-COMMIT ABLATION 9 런
  (LS-live seeds 1..4 · LS-off seeds 0..4), primary = ablation IID 10300..10599
  paired Δ_shape, confirmatory seeds {1,2,3,4}, 판정식 two-sided 95% CI 하한 > 0,
  stop rule = 실패 시 본편 rescue 종료.
  **이 블록의 primary 식·대역·라벨·판정식은 이 전환으로 일절 변경하지 않는다.**
  완주 후 판정하고 **결과(특히 null)를 보고**한다. 그 판정은 `regime_of` 의
  기존 정의·기존 이름으로 수행된다.

## 2. Phase II — 전환 trigger (exploratory 로 봉인)

- **날짜**: 2026-08-09. **산출물**: `shepherd/scripts/shaping_ceiling.py`,
  `results/shaping_ceiling.json`, `results/shaping_ceiling.png` (커밋 `d090280`).
- **지위**: **탐색적 진단 (exploratory diagnostic)**. confirmatory 아님. 어떤
  판정에도 쓰지 않는다. 다음 한계를 그대로 기록한다:
  - seed 0, **a_att 당 에피소드 1 개**, hold 롤아웃의 **상위 3 스냅샷**만.
  - 배치 탐색 = **그리디 + 유한 후보 껍질** (160점, 조밀판 864점).
  - **limiter 도달가능성(a_lim)·no-kinetic 존 미요구** = teleporting 배치 =
    **relaxed static-placement** 문제. 실제 시스템 최적 `V_N^actual` 과 순서관계 없음.
  - reachable set 은 보수적 superset 이나 **유한 위트니스 표본**(2000).
  - judge 에 센서 잡음·지연 stochasticity 없음.
- **관측된 것 (하향된 표현으로만)**:
  - hold 는 a_att≈33 부근에서 발사 문턱을 하향 통과.
  - **문턱 교차가 관측된 이산 점** = a_att 36, 39 (연속 구간도, 실제 시스템
    feasibility band 도 아니다). 42 이상에서는 테스트된 탐색으로 교차 미발견.
  - 발견된 모든 교차는 **첫 번째 봉쇄 구**로 달성됐고 추가 구의 표본 이득 없음.
  - 후보 27배 조밀화(a_att 45)에서 0.774 → 0.846, 여전히 문턱 미달·k=3 포화 →
    **요격기 수 단독이 지배적 병목은 아닐 수 있다는 시사**.
- **철회된 문장** (docs/73 §2): "결정 대역 = [36,39]" · "협력의 marginal value 가
  기하적으로 존재하지 않는다" · "병목은 봉쇄 공급량이 아니다" · "그리디이므로
  달성가능 하한". 이후 산출물·발표에서 사용 금지.

## 3. Phase III — 새 가설과 지도 구성 계약 (결과 열람 전 고정)

### 3.1 정의 (동결 블록에는 소급 적용하지 않음)

```
V_0(x)              무개입 (standby hold) v_shot
V_1^*(x)            1 기 최적            ← 논문의 필수 대조군
V_N^*(x)            admissible N-agent 최적
FREE                V_0 >= theta
COOP DECISION BAND  V_0 < theta <= V_N^*
INFEASIBLE FOR N    V_N^* < theta   ← **certified upper bound 가 있을 때만** 이 이름
NO_SOLUTION_FOUND   상한 없이 못 찾은 경우 (기본 이름)
Delta_coop,N        V_N^* - V_1^*
W_{2:N}             { x : 2 <= N_req(x) <= N },  N_req = min{N>=0 : V_N^* >= theta}
```

`chi = a_att·tau^2/(2·rho_net)` = **free-capture analytic proxy** (필요조건 정의로
사용 금지). 포획면은 SE(3) 원뿔 + 축방향 밴드다.

### 3.2 축 (무차원. raw 6D Cartesian sweep 폐기)

핵심 연속축 = `chi`, `kappa = r_kill/rho_net`, `mu = a_lim/a_att` (필요시
`eta = v_att·tau/rho_net`), 이산 = `N`. 파라미터 분류:

| 분류 | 항목 |
|---|---|
| epistemic / hardware-dependent | `tau_sense`, `tau_decide`, `r_kill` 일부 |
| design / decision | `N`, `theta_fire` |
| environmental / aleatory | `a_att`, 공격자 기동 realization |
| physical geometry + model unc. | `rho_net`, 원뿔 기하 |
| interceptor capability / design | `mu = a_lim/a_att`, `v_lim/v_att` |

**구간의 출처는 결과와 독립으로 먼저 선언한다** (sensing/compute/deployment budget
근거). "돌려보니 좋았다" 로 범위를 정하지 않는다.

### 3.3 `v_shot` measure 고정 (착수 1 — 이것 없이는 지도를 쓰지 않는다)

2000 위트니스의 "비율"이 근사하는 measure 를 명시하고, witness allocation(단일
세그먼트 볼 / 경계구 / dogleg 의 혼합비) · 수렴(2k / 8k / 32k spot-check) ·
가중 민감도를 검증한다. 해석은 둘 중 **하나로 선언**한다:
- **(R) robust**: `v_shot` = 수치 coverage metric, `theta` = robustness acceptance
  threshold. (miss 확률·탄약 경제 주장 금지)
- **(P) probabilistic**: reachable uncertainty 에 실제 measure P 를 정의하여
  `v = P(X_tau in C | feasible)`. 이때만 theta 를 hit-confidence 와 연결.

현 단계 기본값 = **(R)**. `theta` 축은 "viability-envelope sensitivity" 로만 보고한다.

### 3.4 certificate 분리 (착수 2)

- **feasible 주장**: 실제 도달가능성을 만족하는 constructive configuration/controller
  로 `V_N^actual >= theta` 를 직접 보인다.
- **impossible 주장**: `V_N^actual <= V_N^relaxed <= U_N < theta` 형태의 상한.
  3층 순서: (A) 후보집합 내 **global optimum** (MILP/B&B — greedy 대체),
  (B) continuous placement **outer relaxation**, (C) 최저비용 certificate =
  **unblockable bad mass**: `v_max <= G/(G+U)`.
- 상한이 없는 셀은 `NO_SOLUTION_FOUND` 로만 표기한다.

### 3.5 표본·통계 (지도)

조건당 **독립 attacker realization 20~30**, 경계 adaptive refinement,
**통계단위 = episode** (위트니스를 독립표본으로 bootstrap 금지), 경계에도 bootstrap band.

## 4. Stage-2 (C5) confirmatory 계약 — 결과 열람 전 고정

> Stage-2 operating point will be selected **exclusively** from the completed
> geometric feasibility map using a **deterministic rule fixed before any Stage-2
> training result is observed**. Among certified feasible decision-band components,
> we choose the point maximizing the **minimum normalized distance to the necessity
> and sufficiency boundaries**; ties broken by (1) larger component measure,
> (2) smaller `chi`, (3) smaller `N_req`, all fixed prospectively. The training
> budget, seed list, evaluation-set generation, baselines, and the primary paired
> difference in net-capture probability remain identical to the original contract.

- **3 regime 동시 실행** (한 점만 돌리지 않는다): `FREE` / `decision band 내부` /
  `high-difficulty (certified INFEASIBLE 또는 NO_SOLUTION_FOUND)`.
- **primary 결과는 점수가 아니라 interaction**: *RL benefit 이 사전 예측된
  feasibility envelope 안에서만 출현하는가.*
- 점당 학습 시드 **5 최소** (8~10 권장), held-out 300 paired, 기준선 = hold ·
  arc scripted · MARL · **reachable 1-limiter** · oracle envelope.
- 통계: 시드 최상위 hierarchical CI + paired 차이 + effect size 95% CI,
  0 카운트는 binomial 상한 병기.

## 5. 반증 조건 (이것도 지금 고정)

1. 선언된 무차원 축 전 범위에서 `W_{2:N} = 공집합` → **협력 무가치**가 결론이고,
   논문은 requirements 가 아니라 **negative systems result** 가 된다
   ("single-shot 비파괴 포획에서 협력 interdiction 이 실질 이득을 갖는 조건이
   극도로 제한된다").
2. band 가 넓게 열린 셀에서도 학습 이득 0 → C2 는 필요조건만 주고 학습 계약이
   별도 병목 → 논문은 지도 + 학습가능성 분리 보고로 축소.
3. 조밀 후보·비근시안 최적화에서 `N_req >= 2` 가 나오면 Phase II 의 "모든 교차가
   1 기로 달성" 관측을 **철회**한다.
4. `v_shot` 이 witness allocation·해상도에 유의하게 의존하면 (§3.3 수렴 실패)
   지도 자체를 발표하지 않는다.

## 6. 논문 서술 규칙 (chronology 은닉 금지)

> Phase I: preregistered controller comparison produced null results.
> Phase II: post-hoc mechanism diagnosis identified a potential feasibility mismatch.
> Phase III: a prospectively specified parameter study tested that hypothesis.

- Phase I 의 원 가설·primary·결과를 논문에 **명시적으로** 보고한다.
- Phase II 는 exploratory 로 표기한다.
- "requirement" 표기는 hardware/context-of-use anchor 를 최소 1 개 확보한 뒤에만
  사용하고, 그 전에는 **design envelope / parametric requirement curve** 로 쓴다.
- spine (리뷰 10 §8 채택): *Feasibility-First Design of Cooperative Single-Shot
  Counter-UAS Interception under Deployment Latency*.

## 7. 이 문서 이후 금지 사항

- 지도 결과를 본 뒤 §3 정의·§3.2 축·§3.3 measure 선언·§4 선택규칙·§5 반증조건을
  변경하는 것.
- Phase II 산출물을 confirmatory 로 인용하는 것.
- docs/71 블록의 primary·대역·라벨·판정식 변경, 또는 그 결과를 Phase III 로
  재해석하는 것.
