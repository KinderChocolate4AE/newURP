# 73 — 리뷰 10·11·12·13 판정 로그 (방향 전환 심사) + 이행 목록 — r3

**2026-08-09 · 요청 = `docs/review_prompt_design_map_pivot.md` (리뷰 10) +
`docs/review_prompt_blueprint.md` (리뷰 11) · 대상 = spine 교체 (학습 이득 증명 →
메커니즘 성립 조건). 결과 = **전환 조건부 승인 · 현 서술로는 불승인 → 조건 이행 후
재승인**. 반론 없이 전부 수용. r0 = 리뷰 10 / r1 = 리뷰 11 (A1~A8 + 청사진) / r2 = 리뷰 12 의 수정 5+2 / **r3 = 리뷰 13 의 blocker 5 + protocol leak 6~14. 전부 지도 셀 생성 전 (Phase III 셀 0 개).**

**★ r1 최상위 정정 (리뷰 11)**: `2026-12-18` 은 **URP 행정 마일스톤이지 연구의
종료선이 아니다.** 12/18 에는 "어디까지 완결해 보고할지"만 정하고, 저널 증거 bar 는
기간과 무관하게 유지한다. **시간 때문에 C3/C5/certificate 를 잘라내지 않는다.**
r0 §8 의 "19주 축소 일정" 은 폐기하고 `docs/75_blueprint.md` 의 **과학적 게이트**로
대체한다.

## 1. 판정표

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| 1 | Q-A 축 교체 | **CONDITIONAL** | chronology 잠금 = `docs/74_pivot_protocol.md` (오늘 날짜) |
| 2 | F2 "협력 marginal value = 0" | **REJECT** | **철회.** 표현 하향 + `U_{<=1}` vs `L_{<=N}` bound 로 재설계 (r1) |
| 3 | 충분경계 upper certificate | **RATIFY (필수)** | r1: **싼 것부터** — unblockable bad mass → finite-candidate exact(MILP) → continuous outer relaxation → reachable constructive lower + 독립 judge cross-check |
| 4 | Q-B 파라미터 축 승격 | **CONDITIONAL (거의 RATIFY)** | 파라미터를 4 종으로 **분류** + 구간 출처 사전 고정 |
| 5 | C5 재실행 | **CONDITIONAL** | adaptive two-stage + 결정론적 선택규칙 + **3 regime 동시** |
| 6 | F1 라벨 반전 | **REJECT — 현 regime 정의** | `0.5aτ²>ρ` 는 **proxy** 로 강등, regime 은 `V_0` + `L/U` bound 로 재정의 |
| 7 | θ_fire 축 | **CONDITIONAL** | miss-risk/탄약경제 주장 금지. "viability-envelope sensitivity" 로만 |
| 8 | 대안 프레임 | **RATIFY** | spine = *Feasibility-First Design of Cooperative Single-Shot Counter-UAS Interception under Deployment Latency* |
| 9 | Q1 증거 bar | **CONDITIONAL** | 3층(geometry certification / RL / robustness) 채택, 통계단위 = **episode** |
| 10 | 19주에 C1~C5 전폭 | **REJECT — 현 범위** | r1 정정: 12/18 은 행정 마일스톤. **시간으로 자르지 않고** 과학 게이트로 진행 (docs/75). 넣지 않는 것 = Paper 2~5 주제뿐 |
| 11 | desk-reject 문장 | **RATIFY (실재 위험)** | §4 에 전문 인용, 연구 전체의 방어 목표로 등재 |

### 1.1 리뷰 11 (봉인 검증 A1~A8) — 전부 수용

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| A1 | 봉인의 감사 가능성 | **CONDITIONAL** | pivot manifest + git tag + 외부 timestamp + 산출물 `protocol_hash` 스탬프. "verified unread" 금지 → "not inspected for scientific decision-making" (docs/74 §0, `shepherd/scripts/pivot_manifest.py`) |
| A2 | Phase II 한계 기재 | **REJECT (2 건 누락)** | **B1 counterfactual trajectory inconsistency** (반응형 공격자의 causality 절단) · **B2 common-mode bias** (같은 judge) 추가 + 독립 judge cross-check 필수 (docs/74 §2) |
| A3 | Stage-2 선택규칙 | **REJECT** | "band center" 폐기 → **certified opportunity 유병률 `p_C(z)` 의 LCB95 최대점**. primary 중복 해소(interaction 하나). eligible 점 없으면 **C5 협력 팔 미실시** (docs/74 §4) |
| A4 | `V_0/V_1^*/V_N^*` 정의 | **CONDITIONAL** | `<=N` 표기 + 3 층 분리 + bound 기반 분류 (§3, docs/74 §3.1~3.2) |
| A5 | measure (R) | **RATIFY (조건)** | θ 를 상수로 방어하지 않는다. 산출물 = `L/U` 연속 surface + θ ∈ {0.80…0.95} 슬라이스 (docs/74 §3.3) |
| A6 | 무차원 축 | **CONDITIONAL (아직 모른다)** | 후보 확장(`nu`,`lambda`,`R_standby/rho`,`R_detect/rho`,`D_asset/rho`,`alpha`) + **iso-Π collapse test** 를 그림으로 (docs/74 §3.6) |
| A7 | 표본 20~30 | **CONDITIONAL** | **replicate 를 줄이지 말고 cell 을 줄인다**: coarse 20~30 / boundary 60~100+ / Stage-2 3점 100~300 (docs/74 §3.5) |
| A8 | 동결 9 런 처리 | **RATIFY** | null 인용 원문 채택 — "**motivated, but does not validate**" · Phase III 는 "mechanism-consistent explanation" 까지만 (docs/74 §6) |

### 1.2 리뷰 12 (r1 심사) — CONDITIONAL → 5+2 수정 후 RATIFY. 전부 이행

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| 1 | §3 ↔ §5 의 `L<=V<=U` **모순** (snapshot certificate ↔ closed-loop 량을 한 sandwich 로 합침) | **REJECT (논리 오류)** | 고정상태 sandwich `L^reach <= V^reach <= V^rel <= U^rel` 와 `L^ctrl` 을 **분리**. 순서관계 주장 금지 (§3, §5, docs/74 §3.1, docs/75 §0) |
| 2 | `W_{2:N} = ∅` → negative result 직행 | **REJECT (논리 오류)** | **3 분기** (A single-agent sufficiency / B mechanism infeasibility / C unresolved gap). C 는 **결론 없음**. docs/74 반증조건 ① 소급 수정 (§5.1) |
| 3 | 라벨이 상호배타 아님 (`FREE` ↔ `CERTIFIED SINGLE` 중첩) | **REJECT** | `SINGLE-NEEDED` / `COOP-NEEDED` 로 재명명 + 상호배타 정의. `N_req` 는 닫히지 않으면 **UNRESOLVED** (모든 상태에 존재하지 않는다) |
| 4 | `Delta_coop` 가 어느 층의 이득인지 모호 | **REJECT** | 층별 표기 `Delta^rel_N` / `Delta^reach_N` / `Delta^ctrl_N (= J(pi_N)-J(pi_1), 경험적 차이)`. 메인 논문은 `U^rel_{<=1} < theta <= L^reach_{<=N}` 한 줄로 밀고 `Delta_coop` 를 앞세우지 않는다 |
| 5 | "필요시 eta" = 잔여 자유도 | **REJECT** | **deterministic escalation rule** (§3.1): candidate Π-set 사전 고정 · core `(chi,kappa,mu)` · tolerance 통과 시 채택 · 실패 시 `eta -> alpha -> lambda -> nu -> ...` 순서 고정 · 그래도 안 되면 "no low-dimensional collapse supported" |
| + | "certificate 전 계층 강제" | **수정 권고** | **certificate hierarchy** 로 (§8): 싼 sound bound 로 닫힌 셀엔 상위 solver 미적용, 셀별 사용 수준 공개 |
| + | Q1 bar 의 "mobility 2~3 층" | **수정 권고** | `mu` 가 이미 mobility 축 → 표현 폐기. core map = validated Π-space + discrete N, non-core 는 사전 지정값 고정 + matched slice (§7) |

### 1.3 리뷰 13 (r2 심사) — CONDITIONAL → blocker 5 + leak 6~14 이행 후 RATIFY

| # | blocker | 판정 | 이행 (docs/74 r3) |
|---|---|---|---|
| 1 | `L^reach` 는 문서에만 있고 알고리즘은 `L^ctrl` 만 계산 | **치명적** | **4A/4B 분리** (§3.7): 4A = 고정 `(e,t)` 에서 `D_i^reach` 안의 배치로 **같은 witness set** 평가 → `L^reach_{<=N,clean}` (certificate) / 4B = 반응형 env rollout → `L^ctrl` (실현 검사, sandwich 에 넣지 않음). 시간축 `(x,T_s)` 폐기 → **reference encounter 시각 `(e,t)`** |
| 2 | `C_N(x)` 가 episode 인지 state 인지 불명 | **치명적** | state-level `C_N(e,t)` + **전 스텝 스캔**(사후 선택 금지) + **persistence m = ceil((tau_sense+tau_decide)/dt) = 3 tick** + `C_N^ep(e)` + `p_C(z)` = **prevalence under the pre-specified scenario distribution** (§4.1) |
| 3 | clean-fire 의 `not boxed-in` 이 certificate 에서 누락 | **치명적** | `g_theta = 1[v>=theta AND NOT boxed]`. **constructive lower 는 `g_theta=1` 배치만 유효**, upper 는 boxed 무시가 sound (비대칭 명시) (§3.2) |
| 4 | adaptive refinement <-> "pre-specified finite grid" 충돌 | **중대** | **master lattice `Z_master` 선봉인 + `lattice_hash`**. adaptive 는 "다음에 어느 master 점을 계산할지"만 (결정론 정책 4 단). Stage-2 점은 `Z_master` 안에서만 → compute allocation 허용 / hypothesis-space 생성 금지 (§3.8) |
| 5 | interaction 이 통계적 estimand 가 아님 | **중대** | comparator = **같은 N 기의 freeze 된 constructive controller `B_N`** (reachable 1-limiter 아님 — learning x team-size 혼합 방지). `delta_r = p_net^{MARL_N,r} - p_net^{B_N,r}`, **`Gamma = delta_COOP - (delta_FREE+delta_HARD)/2`**, 성공 = `LCB95(Gamma) > 0`. `N=1` 은 secondary mechanistic (§4.4) |

| leak | 이행 |
|---|---|
| 6 finite MILP 의 지위 | certificate hierarchy 에서 제외 → **solver/audit auxiliary**. "Failure to reach theta in the finite-candidate exact problem does not certify continuous-domain infeasibility" 등재 |
| 7 witness semantics | **path witness** (완전 궤적 + 종단 상태) → `B_j = gamma_j (+) Ball(r_kill)` 이 의미를 가짐. `v_shot` = feasible **path** witness 의 가중 coverage |
| 8 Pi 축 | **결과 보고 축 추가 폐기** → Buckingham-Pi 를 **분석적으로 먼저 완성**·전부 기록·2~3 개만 plotted·나머지 conditioning. iso-Pi = **reduction validation**. `lambda=L_axial/rho`·`R_standby/rho` 는 rho 변경 시 자동 변화 |
| 9 §7 <-> §3.9/§5-4 모순 | 반증조건 발동 = **현 Phase III 종료(falsified)** → 축·measure 변경은 **새 `Phase III-B` protocol 을 새 hash 로 사전등록** 후 재시작 (§5.1) |
| 10 `p_C` CI·eligibility | **Clopper-Pearson one-sided 95%**, 단위 = episode. eligible = `LCB95 > p_min = 0.05` **AND** 성공 episode >= 5. tie = lexicographic. eligible 없으면 **협력 C5 미실시** |
| 11 matched control metric | **normalized L_inf** 거리. FREE = 최근접 FREE 셀 / HARD = 최근접 `LOCAL-INFEASIBLE-N`. **AMBIGUOUS 를 HARD 로 쓰지 않는다** |
| 12 라벨 이름 | **`CERTIFIED LOCAL-SINGLE-NEEDED` / `LOCAL-COOP-NEEDED` / `LOCAL-INFEASIBLE-N`** (LOCAL 생략 금지). 용어 = **local certified cooperative opportunity** |
| 13 judge 일치 판정 | **boundary-aware**: signed margin `|m1-m2| <= eps` (1e-6 m / 1e-9). predicate 불일치는 `|m| <= eps` boundary case 에서만 허용, **boundary 에서 먼 불일치 1 건이면 지도 중단** |
| 14 태그 | **태그 이동 금지** → `PIVOT_LOCK_R2/R3_...` revision 명 분리. **자백: r1 에서 태그를 `-f` 로 한 번 이동시켰다** (`c6e8081`→`3aec425`, Phase III 셀 0) — 이후 없음 |

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

**★ r1 교체 (리뷰 11 A4)**: 단일 `V_N^*` 폐기 → **"최대 N" 표기 + 3 층 분리**.
정확히 N 기 강제는 단조성을 깨고, snapshot relaxed 값을 episode-level actual 의 상한으로
쓸 수 없다 (limiter 가 공격자 궤적을 바꾼다). 상세 = `docs/74` §3.1~3.2.

```
Local fixed-state problem  (같은 고정 encounter state x 에서만 정의된다)
------------------------------------------------------------------------
V^rel_{<=N}(x)         최대 N 개 static kill sphere, 연속 admissible placement domain
                       어디든 (mechanism oracle)
V^reach_{<=N}(e,t)     center 를 D_i^reach(e,t) (reference encounter 시각 t 까지
                       실제 동역학·NK·충돌 제약으로 도달 가능한 집합) 로 제한
L^reach_{<=N,clean}(e,t) 도달가능 + **not boxed** 배치가 달성한 값 (constructive)
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
FREE                          : V_0 >= theta
CERTIFIED LOCAL-SINGLE-NEEDED : V_0 < theta <= L^reach_{<=1,clean}
CERTIFIED LOCAL-COOP-NEEDED   : U^rel_{<=1} < theta <= L^reach_{<=N,clean}
CERTIFIED LOCAL-INFEASIBLE-N  : U^rel_{<=N} < theta
AMBIGUOUS               : 그 외 (지도에 그린다 — 숨기지 않는다)

N_req = 0               : V_0 >= theta
N_req = k (k >= 1)      : U^rel_{<=k-1} < theta <= L^reach_{<=k,clean}
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

- `chi = a_att·tau^2 / (2·rho_net)` 은 **free-capture analytic proxy** 로 강등.
  **"필요 경계는 닫힌형 a* = 2rho/tau^2" 문장은 삭제**(포획면이 등방 볼이 아니라
  SE(3) 원뿔 + 축방향 밴드이므로 scalar 비교로 clean-fire 필요조건을 정의할 수 없다).
- 축: raw 6 knob 대신 **무차원**. core = `chi`, `kappa = r_kill/rho`,
  `mu = a_lim/a_att`. 확장은 §3.1 의 **escalation rule** 로만 (임의 추가 금지).
  6D Cartesian sweep 폐기.

### 3.1 무차원 축 escalation rule (r2 추가)

**★ 리뷰 12 항목 5 (deterministic escalation rule)**: "필요시 eta" 같은 표현은
결과를 본 뒤 축을 하나씩 늘리는 자유도를 남긴다. 다음을 **결과 전에 고정**한다.

1. **candidate Π-set 고정**: `{chi, kappa, mu, eta, nu, lambda, sigma_standby,
   sigma_detect, sigma_asset, alpha}` (+ 수치검증용 `delta_t = dt/tau`).
2. **core hypothesis = `(chi, kappa, mu)`** 로 고정.
3. iso-Π validation 이 **사전 지정 tolerance** 를 통과하면 그 축약을 채택.
4. 실패하면 **미리 정한 순서**로 conditioning variable 을 하나씩 추가:
   `eta -> alpha -> lambda -> nu -> sigma_standby -> sigma_detect -> sigma_asset`.
5. 그래도 collapse 가 안 되면 결론 = **"no low-dimensional collapse supported"**
   (축을 계속 늘려 억지로 맞추지 않는다).
- **★ 동결 경계**: 진행 중인 docs/71 ablation 은 `regime_of` (기존 정의·기존 이름)
  로 계속 판정한다. 위 재정의는 **새 연구의 언어**이고 동결 블록에 소급 적용하지
  않는다 (그렇게 하면 primary 를 결과 후 바꾸는 것이 된다).

## 4. 방어 목표 (desk-reject 문장 — 원문)

> "The manuscript retrospectively recasts a failed MARL study as a systems-design
> result, but its claimed viability boundaries and requirements are properties of
> an unvalidated simulator whose decisive latency, kill radius, firing threshold,
> and threat capability were chosen by the authors rather than grounded in a
> physical context of use."

이 문장을 막는 것이 이 연구 라인 전체의 정의다 (기간 무관). 대응 축: (i) `v_shot` measure 정의·수렴,
(ii) upper/lower certificate 분리, (iii) 파라미터 분류 + 구간 출처 사전 고정,
(iv) hardware/context anchor 1 개 (없으면 "requirement" 대신 **design envelope /
parametric requirement curve** 로 표기), (v) latency/noise spot-check.

## 5. 즉시 착수 3 (리뷰 10 지정 · 리뷰 11 이 순위를 재확인)

**리뷰 11 "만약 하나만 고른다면"**: `L_{<=N}(x) <= V_{<=N}(x) <= U_{<=N}(x)` 를 실제
코드로 계산해 **FREE / SINGLE / CERTIFIED COOP / INFEASIBLE / AMBIGUOUS** 를 구분하는
**certificate-backed feasibility envelope**. 특히 `U_{<=1} < theta <= L_{<=N}` 셀이
**실재하는지**. 있으면 "왜 multi-agent 인가"가 처음으로 성립하고, 없으면 "이 메커니즘에서
왜 multi-agent 가 불필요한가"라는 negative result 가 성립한다 — **어느 쪽이든 연구가 산다.**


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

### 6.1 리뷰 11 추가 sunk-cost (버릴 것)

4. **"2000 witness" 에 대한 애착** — 물리 상수가 아니다. 수렴이 8k/32k 를 요구하면 바꾼다
   (손실 = 기존 수치 비교성, 이득 = metric credibility).
5. **arc scripted 를 "강한 baseline" 으로 계속 키우는 일** — Phase I historical
   comparator 로 충분. 새 기준선은 `N=0`, `N=1`, constructive `N`, oracle `U_{<=N}`.
6. **COMA 배선을 "있으니 언젠가 쓴다"** — 계수 0 인 채로 두는 것은 sunk-cost invitation.
   새 hypothesis 가 credit assignment 를 요구할 때만 켠다.
7. **dense `Delta v_shot` reward 를 불변 과학객체로 취급** — Phase I historical
   contract 안에서만 불변이다. metric 자체가 Phase III 에서 수정될 수 있다.
8. **`a_att ~ U[11,78]` 를 세계의 위협분포처럼 취급** — 한 scenario distribution 일 뿐.
   envelope 논문에서는 uniform draw 보다 **conditional curve** 가 먼저다.

### 6.2 리뷰 11 이 지적한 우리의 자기기만 2 건 (등재)

1. **"certificate 만 잘 만들면 Phase I 실패 원인이 밝혀진다"** — 아니다. certificate 는
   특정 mechanism 의 feasibility 구조만 밝힌다. Phase I 실패는 feasibility · exploration ·
   credit assignment · reward · architecture 가 **동시에** 원인일 수 있다.
2. **"무차원 지도가 나오면 그 자체로 systems requirement"** — 아니다. 실물 anchor 없이는
   **model-conditional design envelope** 다. 이 구분을 끝까지 지키면 논문이 더 강해진다.

## 7. Q1 증거 bar (수용 요약 — 상세는 리뷰 원문)

- **geometry**: a_att 당 1 에피소드 금지 → 조건당 **20~30 독립 realization**,
  경계 adaptive refinement, witness 수렴(2k/8k/32k spot-check), 가중 민감도,
  greedy ↔ global/upper-bound solver 비교, relaxed ↔ reachable 분리.
  **통계단위 = episode** (위트니스 2000 을 독립표본으로 bootstrap = pseudoreplication).
- **map**: **core map = validated low-dimensional Π-space + discrete N**.
  non-core dimensionless group 은 사전 지정 값으로 고정하고 matched collapse /
  robustness slice 로만 검사한다 (`mu` 가 이미 mobility/capability 축이므로 "mobility
  2~3 층" 이라는 별도 표현은 폐기 — r2). 공격자 분포 적분 포함.
- **learning (C5)**: FREE / band 내부 / high-difficulty 3 regime, 점당 **시드 5 최소**
  (8~10 권장), held-out 300 paired, 기준선 = hold · arc scripted · MARL ·
  **reachable 1-limiter** · oracle envelope. 4기 협력 주장에는 **N=1 대조군 필수**.
- **통계**: 시드 최상위 hierarchical CI, paired 차이, effect size + 95% CI,
  0 카운트는 binomial 상한 병기, 지도 경계에도 bootstrap band.
- **realism**: 대표 3 regime × 2~3 점에서 delay jitter · sensing noise · actuator lag
  spot-check (주인공이 tau 인데 judge 에 stochasticity 가 없으면 반드시 찔린다).

## 8. 일정 — r1: 시간 게이트 폐기, 과학적 게이트로 대체

r0 의 "19주 축소판" 은 **폐기**한다 (리뷰 11: 12/18 은 행정 마일스톤). 주차별 산출물과
**kill/branch 게이트**는 `docs/75_blueprint.md` §1 에 있고, 각 게이트는 시간이 아니라
숫자(수렴폭·불일치율·certificate coverage·`W_{2:N}` 존재 여부)로 발동한다.

- 12/18 에 제출하는 것 = URP 보고서 + arXiv snapshot. **미완 부분은 미완으로 명시**하고
  이후 지속한다.
- 저널 투고 시점은 증거 bar 충족 시점에 따른다 (12/18 과 무관).
- 유지 = C2 + C3(무차원 축) + C5 + **certificate hierarchy** (r2 정정: "전 계층
  강제" 폐기). 모든 셀에 모든 certificate 를 강제하지 않는다 — **싼 sound bound 로
  분류가 닫히는 셀에는 상위 solver/relaxation 을 적용하지 않고**, 어떤 certificate
  수준을 썼는지 셀별로 지도·metadata 에 공개한다. (예: unblockable bad mass 만으로
  `U^rel_{<=4} < 0.82 < 0.90` 이 나온 셀에 continuous B&B 를 돌리는 것은 과학적 가치가
  거의 없다.) **넣지 않음** = optimal stopping · sensing-latency cooperation ·
  multi-shot · 6DOF 재구축 (= Paper 2~5, `docs/75_blueprint.md` §4).

## 9. 상위 발견의 재서술 (리뷰어 제안 채택)

> **기존 연구 설계가 '협력이 필요한 영역'을 실제 cooperative advantage 존재와
> 무관한 scalar kinematic proxy 로 정의하고 있었고, 그 결과 policy learning 전에
> 확인했어야 할 feasibility question 이 빠져 있었다.**

이것이 논문의 상위 주장이다. `[36,39]` · `N_req=1` · "병목은 tau·theta·cone" 을
확정 사실로 밀면 그 순간 전환이 goalpost moving 으로 보인다 — §2 의 하향 표현을
모든 산출물·발표에 적용한다.

**★ r2 (리뷰 12) — 두 문장을 절대 합치지 않는다**:
- "기존 설계에 feasibility question 이 빠져 있었다" = **지금 확정 가능한
  methodological finding.**
- "그 feasibility question 이 Phase I 실패를 설명한다" = **아직 hypothesis.**
