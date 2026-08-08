# 74 — PIVOT PROTOCOL r2 (전환 기록·봉인) — 2026-08-09

**r0 = 리뷰 10 이행. r1 = 리뷰 11 (A1~A8) 반영. r2 = 리뷰 12 (r1 심사) 의 논리 교정
5 + 2 반영. 이 문서는 Phase III 지도 셀을 **한 칸도 생성하지 않은 상태**에서 작성·
개정됐다 — 따라서 r2 의 교정은 골대 이동이 아니라 **결과 생성 전 논리 수정**이다
(감사 이력 = §0.1).**

**★ r1 최상위 정정: `2026-12-18` 은 URP 행정 마일스톤이며 연구의 종료선이 아니다.**
12/18 에는 "어디까지 완결해서 보고할지"만 정한다. 저널용 증거 bar (certificate ·
표본 수 · robustness) 는 기간과 무관하게 유지하며, 시간 때문에 C3/C5/certificate 를
잘라내지 않는다. 아래 게이트는 전부 **과학적 kill/branch 게이트**이고 시간 게이트가
아니다.

기준 커밋 = `a1a784e` (2026-08-09T01:56+09:00). 감사 장치 = §0.

---

## 0. 감사 가능성 (리뷰 11 A1 — CONDITIONAL 이행)

r0 의 "오늘 이후 생성된 지도만 Phase III" 는 **사람의 진술**이었다. r1 에서 다음 4 개를
추가한다.

1. **pivot manifest**: `shepherd/scripts/pivot_manifest.py` → `artifacts/
   pivot_lock_2026-08-09.json`. 내용 = docs/73·74·75 + 리뷰 프롬프트 2 건의 SHA-256
   (이들의 해시의 해시 = **`protocol_hash`**), 현재 commit, Phase I 계약·결과 기록,
   Phase II exploratory 산출물, judge/env/평가·판정 코드, **진행 중 9 런의 config·
   seed list·launcher 명령**, 분포·계약 해시.
2. **git tag** `PIVOT_LOCK_2026-08-09` (manifest 커밋 위에).
3. **외부 timestamp**: embargo 가능한 read-only 등록(OSF registration 등)으로
   같은 manifest 를 봉인한다. 즉시 공개하지 않아도 "이 시점에 이 계약이 존재했다"가
   나중에 검증된다.
4. **모든 Phase III 산출물에 스탬프 필수**:
   `protocol_hash · code_commit · judge_commit · scenario_manifest_hash ·
   map_spec_hash · generated_at`. 스탬프 없는 map artifact 는 **무효**로 취급한다.

**표현 규율**: 사람이 결과를 보지 않았다는 것은 암호학적으로 증명 불가하다.
따라서 다음 문구만 쓴다 (`verified unread` 금지):

> "Results had not been inspected for scientific decision-making as of the
> Phase-III lock."

**논문용 원문 (그대로 사용)**

> **Phase-transition provenance.** Before any Phase-III feasibility-map output was
> generated, we archived the Phase-I contract, Phase-II exploratory artifacts, all
> active training configurations, seed manifests, analysis code, and the Phase-III
> protocol in an immutable time-stamped registration. Every subsequent Phase-III
> artifact records the corresponding protocol hash and source-code revision.
> Phase-II outputs are retained solely as exploratory records and are not used for
> Phase-III confirmatory classification or hypothesis testing.

## 0.1 정정 이력 (r2 — 감사 이력)

| 판 | 날짜 | 계기 | 성격 |
|---|---|---|---|
| r0 | 2026-08-09 | 리뷰 10 판정 | 최초 봉인 |
| r1 | 2026-08-09 | 리뷰 11 (A1~A8) | 감사장치·정의 3층·Stage-2 규칙 교체 |
| **r2** | 2026-08-09 | 리뷰 12 (r1 심사) | **논리 오류 2 건 교정** (sandwich 혼합 · `W=∅` 해석) + 분류 상호배타화 + Δ 층별화 + Π escalation rule |

r0·r1 의 manifest/tag 는 **삭제하지 않고 보존**한다. r2 의 `protocol_hash` 는 새로
계산되며(계약 파일 내용이 바뀌었으므로), Phase III 산출물은 r2 hash 를 싣는다.
**Phase III 지도 셀은 r0~r2 전 구간에서 한 칸도 생성되지 않았다** — 교정 대상은
결과가 아니라 계약의 논리였다.

## 1. Phase I — 원 spine 과 그 결과 (변경 금지·소급 재해석 금지)

- **가설**: 동결 TRAIN 위협 분포·동결 학습계약에서 협력 shaping 을 학습한 MARL 팀이
  손설계 기준선보다 비파괴 net 포획률을 높인다.
- **primary**: held-out **IID 10000..10299 (n=300) paired**, lexicographic
  Δ_net = p_net^MARL − p_net^scripted (docs/63 r2).
- **기준선**: hold / bearing-aware arc scripted (TRAIN 선택 c5, p_net 0.110).
- **결과(커밋된 사실)**: LL **0/300** (SHAPING 0/164 · FREE 0/136) ·
  LS **49/300 = 0.163** (FREE 49/136 = 0.36 · **SHAPING 0/164**) ·
  hold SHAPING 사전측정 **0/122**.
- **진행 중·미열람**: docs/71 r1 LS-COMMIT ABLATION 9 런. primary·대역·라벨·판정식
  **불변**, 기존 `regime_of` 로 완주·판정하고 **null 도 보고**한다.

## 2. Phase II — 전환 trigger (exploratory 로 봉인)

- 산출물: `shepherd/scripts/shaping_ceiling.py` · `results/shaping_ceiling.{json,png}`
  (커밋 `d090280`, 재생성 `ff9dfc7`). **status = EXPLORATORY DIAGNOSTIC**.
- **지위**: hypothesis generator **이상으로 사용 금지**. confirmatory 인용 금지.
- **자백된 한계 (r1 에서 2 건 추가 — 리뷰 11 A2 REJECT 이행)**

  | # | 편향 | 내용 |
  |---|---|---|
  | **B1 ★** | **counterfactual trajectory inconsistency** | 공격자는 **반응형**인데 hold 궤적으로 만든 상태 `x_t^hold` 에 limiter 를 teleport 했다. 실제로 그 위치에 limiter 가 있었다면 공격자는 **그 전에 이미 다른 궤적**을 탔다. reachability 무시보다 심각한 결함 — **attacker response causality 가 끊겨 있다.** |
  | **B2 ★** | **common-mode bias (같은 judge)** | Phase I 에서 문제가 된 reachable-set/judge 와 **같은 구현·같은 모델링 가정**을 공유한다. → Phase III 핵심 predicate (cone containment · witness killed/not · threshold feasibility) 는 **독립 구현 cross-check 필수**. |
  | B3 | snapshot 선택 편향 | top-`V_0` 는 cooperative synergy 가 큰 시각이 아니라 **finisher-alone 기하가 좋은 시각**을 고른다 |
  | B4 | 후보 껍질 제한 | 공격자 중심 1~4 m 껍질이 **future choke point** 를 배제할 수 있다 |
  | B5 | scripted aiming | favorable oracle 로 작동 |
  | B6 | max over time/snapshot | 그 자체가 optimistic selection |
  | B7 | witness family 구성비 | 결과를 만든다 (§3.3) |
  | B8 | 선언된 (τ, r_kill, θ) | Phase II 의 구조 자체를 만든다 |
  | B9 | 유한 위트니스·무잡음 judge | 2000 표본, judge 에 센서잡음·지연 없음 |
  | B10 | teleporting 배치 | 도달가능성·NK 존 미요구 = **relaxed static-placement** |

- **철회된 문장 4 건** (docs/73 §2): "결정 대역 [36,39]" · "협력 marginal value = 0" ·
  "병목은 공급 아님" · "그리디 = 달성가능 하한". 이후 산출물·발표에서 사용 금지.

## 3. Phase III — 정의·계약 (결과 열람 전 고정)

### 3.1–3.2 정의: 층 분리 + certified labels
(리뷰 11 A4 · **리뷰 12 항목 1·3·4**)

r0 의 `V_N^*` 는 (i) 정확히 N 기 사용을 강제해 단조성이 깨지고 (ii) snapshot relaxed
값을 episode-level actual 의 상한처럼 쓸 위험이 있었다 → r1 에서 층 분리. **r2 에서는
고정상태 sandwich 와 closed-loop 값을 명시적으로 분리하고**(항목 1), 라벨을
**상호배타**로 만들고(항목 3), `Delta_coop` 를 **층별로 쪼갠다**(항목 4).

```
Local fixed-state problem  (같은 고정 encounter state x 에서만 정의된다)
------------------------------------------------------------------------
V^rel_{<=N}(x)         최대 N 개 static kill sphere, 연속 admissible placement domain
                       어디든 (mechanism oracle)
V^reach_{<=N}(x,T_s)   최대 N 개 center 를 shaping horizon T_s 안에 a_lim · v_lim ·
                       NK 존 · 충돌 제약을 만족해 **도달 가능한 곳**으로 제한
L^reach_{<=N}(x,T_s)   명시적 실현가능 구성이 달성한 값 (constructive lower)
U^rel_{<=N}(x)         V^rel_{<=N}(x) 의 sound upper bound

  => 고정 상태 문제에서만:
     L^reach_{<=N} <= V^reach_{<=N} <= V^rel_{<=N} <= U^rel_{<=N}

Closed-loop problem   (별도 층 — 위 sandwich 와 섞지 않는다)
------------------------------------------------------------
L^ctrl_{<=N}(x0; pi_c) 반응형 attacker 가 있는 원 환경에서 명시적 controller 가
                       달성한 값. **L^ctrl 과 고정상태 relaxed 상한 사이의 순서관계는
                       주장하지 않는다.**

Certified labels  (상호배타 — Fig 6 에서 한 셀에 한 색)
-------------------------------------------------------
FREE                    : V_0 >= theta
CERTIFIED SINGLE-NEEDED : V_0 < theta <= L^reach_{<=1}
CERTIFIED COOP-NEEDED   : U^rel_{<=1} < theta <= L^reach_{<=N}
CERTIFIED INFEASIBLE-N  : U^rel_{<=N} < theta
AMBIGUOUS               : 그 외 (지도에 그린다 — 숨기지 않는다)

N_req = 0               : V_0 >= theta
N_req = k (k >= 1)      : U^rel_{<=k-1} < theta <= L^reach_{<=k}
그 외                   : **N_req = UNRESOLVED** (모든 상태에 N_req 가 존재하지 않는다)

층별 협력 이득 (하나의 Delta_coop 표기 금지)
--------------------------------------------
Delta^rel_N   = V^rel_{<=N}   - V^rel_{<=1}
Delta^reach_N = V^reach_{<=N} - V^reach_{<=1}
Delta^ctrl_N  = J(pi_N) - J(pi_1)   ← 특정 controller 간 **경험적 차이**일 뿐이며
                                      "optimal cooperative marginal value" 가 아니다
W_{2:N} = { x : N_req(x) in [2, N] }   (UNRESOLVED 는 포함하지 않는다)
```
**핵심 한 줄**: `U^rel_{<=1} < theta <= L^reach_{<=N}` — 왼쪽은 *1 기를 이상적으로
배치해도 안 된다* 는 상한 certificate, 오른쪽은 *실제 도달 가능한 N 기 배치가 된다* 는
constructive certificate. 이 둘이 함께 성립하면 "왜 N>1 인가" 가 증명된다.
메인 논문에서 `Delta_coop` 를 크게 밀지 않는다 — 이 한 줄이 더 직접적이다.

`chi = a_att·tau^2/(2·rho_net)` 은 **free-capture analytic proxy** (필요조건 정의 금지).

### 3.3 measure (리뷰 11 A5 — RATIFY, 단 θ 를 상수로 취급 금지)

- `v_shot` 은 **(R) robust coverage metric** 으로 선언한다. probability 로 부르지 않는다
  (위트니스가 명시된 분포의 IID 표본이 아니다).
- **θ 를 방어하지 않는다.** 핵심 산출물은 binary map 이 아니라 **연속 surface**
  `L^reach_{<=N}(z)`, `U^rel_{<=N}(z)` 이고, θ ∈ {0.80, 0.85, 0.90, 0.925, 0.95} **슬라이스**로
  대역이 어떻게 변하는지 보고한다. θ = robustness acceptance level.
- 검증 필수: witness family 구성비(단일세그먼트 볼 / 경계구 / dogleg) 명시 ·
  **수렴 2k → 8k → 32k** · allocation 민감도 · 동일 snapshot paired 비교.
- `delta_t = dt/tau` 는 물리 파라미터가 아니라 **numerical verification number** 로
  따로 확인한다.

### 3.4 certificate — **hierarchy (싼 것부터, 닫힌 셀엔 상위 단계 미적용)**

r2: 모든 셀에 모든 certificate 를 강제하지 않는다. 낮은 비용의 sound bound 로 분류가
닫히면 거기서 멈추고, **셀별로 사용한 certificate 수준을 지도·metadata 에 공개**한다.


1. **unblockable bad mass (최저비용)**: bad witness `j` 의 blocker tube
   `B_j = gamma_j (+) Ball(r_kill)` 이 admissible domain `D` 와 교집합이 없으면 어떤
   배치로도 못 지운다. 그 총 mass `U` 와 captured-good mass `G` 로
   `v_max <= G/(G+U)`. 이 값이 θ 미만이면 즉시 certificate.
2. **finite-candidate exact**: 후보집합 안에서 **global optimum** (greedy 아님).
   ratio 를 threshold-feasibility 로 변환: 분모 > 0 에서
   `v >= theta  <=>  sum_j w_j (c_j - theta) y_j >= 0`. `sum_i z_i <= N` 과 survivor
   관계를 이진 제약으로 → MILP/B&B, θ 에 대해 bisection.
   **동일 candidate-cover signature 위트니스를 묶어 압축**(32k 는 solver 투입 전 필수).
3. **continuous outer relaxation**: center domain 을 voxel/cell 로 쪼개고
   `A^outer_{jq} = 1 if C_q ∩ B_j != empty` (한 cell 이 서로 다른 위치에서 tube 를
   건드려도 "한 center 로 둘 다 봉쇄 가능"으로 과도 인정 = 낙관) + good witness 는
   절대 안 지워진다고 추가 낙관 → `U_{<=N} = G / (G + B - B_removable,N)`.
   cell refinement 로 optimism 이 줄어드는 구조라 **certificate convergence figure** 가 나온다.
4. **reachable constructive lower**: 최적 controller 가 아니라 **하나의 구성적 증인**.
   escape path → blocking tube 후보 → limiter 별 도달가능성 검사 → agent-candidate
   bipartite assignment → threshold-feasibility 로 target 선택 → bang-bang/PD 추종 →
   5~10 tick replan → **반응형 attacker 가 있는 실제 env rollout** → 실제 judge 가
   `v >= theta` 를 내면 `L^ctrl` 성립.
   **★ 이것이 MARL 보다 먼저다. scripted constructive controller 가 못 만드는
   cooperative opportunity 를 RL 에게 만들라고 요구하지 않는다.**
5. **독립 judge cross-check** (B2 대응): cone containment · witness killed/not ·
   threshold feasibility 를 독립 구현으로 재계산. 불일치 > 1e-3 이면 지도 중단·버그 감사.

### 3.5 표본 정책 (리뷰 11 A7 — replicate 를 줄이지 말고 cell 을 줄인다)

| 대상 | 독립 realization |
|---|---|
| coarse cells | 20~30 |
| boundary candidate cells | **순차 60~100+** |
| Stage-2 최종 3 점 | **100~300** geometry realization |
| MARL 평가 | 기존대로 수백 paired episodes |

full Cartesian grid 금지 → **adaptive boundary refinement**. **통계단위 = episode**
(위트니스 2000 을 독립표본으로 bootstrap = pseudoreplication). CPU geometry 는 GPU
학습과 병렬화한다.

### 3.6 무차원 축 (리뷰 11 A6 — CONDITIONAL: 아직 모른다)

핵심 후보: `chi = a_att·tau^2/(2·rho)`, `eta = v_att·tau/rho`, `kappa = r_kill/rho`,
`mu = a_lim/a_att`. **추가 후보(미검증)**: `nu = v_lim/v_att`,
`lambda = L_axial/rho`, `R_standby/rho`, `R_detect/rho`, `D_asset/rho`,
cone half-angle `alpha` (그 자체로 무차원), 공격자 회피 gain 의 무차원화.

**어떤 수가 핵심 축이라고 먼저 믿지 않는다** → **iso-Π collapse test**: 서로 다른
차원 파라미터 조합 두 개가 같은 (chi, kappa, mu, eta) 를 갖도록 만들고 `V` 를 비교.
같은 Π 인데 결과가 허용오차 밖으로 다르면 **빠진 무차원 수가 있다** → 축 추가.
이 실험은 그림으로 낸다.

## 4. Stage-2 (C5) confirmatory 계약 — r1 전면 교체 (리뷰 11 A3 REJECT 이행)

r0 의 "결정 대역 중앙 + minimum normalized distance" 는 잔여 자유도가 많았고(정규화
metric · interpolated vs grid boundary · CI 선택 · 비연결 성분 · 연속축과 이산 N 의
혼합 거리 · 성분 measure 계산), 게다가 **primary 가 두 개**였다(Phase I 지표 유지 ↔
interaction). r1 은 다음으로 대체한다.

**certified multi-agent opportunity** — episode `x` 에 대해
```
C_N(x) = 1[ U_{<=1}(x) < theta  AND  L_{<=N}(x) >= theta ]
p_C(z) = P( C_N(X) = 1 | z )        (파라미터 점 z 에서의 유병률)
z_B    = argmax_z  LCB95{ p_C(z) }  (사전 지정 단측 95% 하한)
```

> The Stage-2 cooperative operating point is selected from the pre-specified finite
> parameter grid before any Stage-2 learning result is observed. For each grid point
> z, we estimate the prevalence of certified cooperative opportunities,
> p_C(z) = P[U_{<=1}(X) < theta <= L_{<=N}(X) | z]. The cooperative test point is the
> grid point maximizing the pre-specified one-sided 95% lower confidence bound of
> p_C(z). All parameter coordinates used for matching are normalized by the
> pre-specified domain endpoints. Ties are resolved lexicographically in the order
> (chi, kappa, mu, eta, N). No interpolation, axis reweighting, or post-hoc boundary
> modification is permitted. **If no grid point satisfies the pre-specified
> certification criterion, the cooperative Stage-2 learning experiment is not
> conducted.**

- 마지막 문장이 핵심이다: **협력 필요 셀이 없는데 억지로 C5 를 돌리지 않는다.**
- **대조점**: FREE / high-difficulty 는 같은 nuisance 변수에서 **가장 가까운 matched
  control** 로 잡는다 (3 regime 동시).
- **primary 는 하나다**: Stage-2 의 primary contrast = **interaction** (RL benefit 이
  사전 예측된 certified band 안에서만 출현하는가). Phase I 의 평가 계약(대역 생성 ·
  paired 구조 · p_net 정의)은 유지하되, Phase III 의 hypothesis test 는 Stage-2 자신의
  primary 로 새로 사전등록한다 — **두 개를 동시에 primary 라 부르지 않는다.**
- 점당 학습 시드 **8~10 권장(5 최소)**, held-out 수백 paired, 기준선 = hold ·
  arc scripted(historical) · MARL · **reachable 1-limiter(필수)** · oracle `U_{<=N}` envelope.
- 통계: 시드 최상위 hierarchical CI · paired 차이 · effect size 95% CI ·
  0 카운트 binomial 상한 병기 · 지도 경계에도 bootstrap band.

## 5. 반증 조건 (branch, kill 아님)

1. 선언 범위 전역에서 `W_{2:N} = ∅` → **곧바로 negative systems result 가 아니다**
   (r2, 리뷰 12 항목 2). 세 경우로 분기하고 **해당 bound 가 직접 지지하는 주장만** 한다:
   **(A) single-agent sufficiency** (`V_0 < theta <= L^reach_{<=1}` 지배 + coop 셀 부재)
   → "no certified need for multi-agent interdiction" ·
   **(B) mechanism infeasibility** (`U^rel_{<=N} < theta` 광범위) → "even N cooperative
   limiters cannot establish the firing condition" (A 와 다른 결론) ·
   **(C) unresolved certificate gap** (AMBIGUOUS 다수) → **결론 없음, negative claim
   금지**. A 또는 B 에서만 negative-result 논문(*Limits of Cooperative Threat-Space
   Shaping ...*)으로 분기하고 C5 협력 팔을 취소한다.
2. band 는 열리는데 MARL 이득 0 → `physical feasibility != learnability` 로 분리 보고.
   constructive controller 가 band 에서 성공하면 그것이 결과다 → Paper 2 로.
3. exact/reachable 에서 `N_req >= 2` → Phase II 의 "모든 교차가 1 기" 관측 **철회**
   (호재: `U_{<=1} < theta <= L_{<=2}` 가 진짜 cooperative necessity 를 준다).
4. `v_shot` 이 witness allocation/해상도에 유의 의존 → **지도 즉시 중단**.
   (P) branch (실제 reachable uncertainty 분포 정의) 또는 set-based branch
   (fraction 폐기 → worst-case containment / quantile radius / support-function score).
   이 경우 기존 θ map 은 사용하지 않는다.

## 6. 논문 서술 규칙 (chronology 은닉 금지)

> Phase I: preregistered controller comparison produced null results.
> Phase II: post-hoc mechanism diagnosis identified a potential feasibility mismatch.
> Phase III: a prospectively specified parameter study tested that hypothesis.

**Phase I null 인용 원문 (리뷰 11 A8 RATIFY — 그대로 사용)**

> Under the original preregistered nominal contract, the intervention failed to
> produce a statistically supported improvement in the prespecified shaping-regime
> net-capture rate. This null result is retained as a confirmatory result of Phase I.
> It **motivated, but does not validate**, the subsequent feasibility analysis, whose
> definitions and hypotheses were specified prospectively after the Phase-I contract
> had been locked.

Phase III 가 성공해도 "Phase I null 의 원인이 feasibility mismatch 였음이 증명됐다"로
쓰지 않는다. 정확히는 **"Phase III offers a mechanism-consistent explanation of the
Phase-I null."**

"requirement" 표기는 hardware/context-of-use anchor 확보 후에만. 그 전에는
**model-conditional design envelope / parametric requirement curve**.
spine = *Feasibility-First Design of Cooperative Single-Shot Counter-UAS
Interception under Deployment Latency*.

## 7. 이후 금지 사항

- 지도 결과를 본 뒤 §3 정의·§3.6 축·§3.3 measure 선언·§4 선택규칙·§5 반증조건 변경.
- Phase II 산출물을 confirmatory 로 인용.
- docs/71 블록의 primary·대역·라벨·판정식 변경, 또는 그 결과를 Phase III 로 재해석.
- `protocol_hash` 스탬프 없는 Phase III 산출물을 결과로 사용.
- 시간(12/18) 을 이유로 certificate·표본 수·robustness bar 를 낮추는 것.
