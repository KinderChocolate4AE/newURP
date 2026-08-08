# 73 — 리뷰 10·11 판정 로그 (방향 전환 심사) + 이행 목록 — r1

**2026-08-09 · 요청 = `docs/review_prompt_design_map_pivot.md` (리뷰 10) +
`docs/review_prompt_blueprint.md` (리뷰 11) · 대상 = spine 교체 (학습 이득 증명 →
메커니즘 성립 조건). 결과 = **전환 조건부 승인 · 현 서술로는 불승인 → 조건 이행 후
재승인**. 반론 없이 전부 수용. r0 = 리뷰 10 만, **r1 = 리뷰 11 (A1~A8 + 청사진) 반영.**

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
Layer 1 V^rel_{<=N}(x)         static kill sphere 최대 N 개, 연속 admissible domain (oracle)
Layer 2 V^reach_{<=N}(x,T_s)   a_lim·v_lim·NK 존·충돌 제약 하 도달가능 center 만
Layer 3 L^ctrl_{<=N}(x0;pi_c)  반응형 attacker 포함 실제 closed-loop rollout (constructive)
FREE                   : V_0 >= theta
CERTIFIED SINGLE       : L_{<=1} >= theta
CERTIFIED COOP         : U_{<=1} < theta  AND  L_{<=N} >= theta
CERTIFIED INFEASIBLE-N : U_{<=N} < theta
AMBIGUOUS              : 그 외 (지도에 그린다 — 숨기지 않는다)
N_req = k              : U_{<=k-1} < theta <= L_{<=k} 일 때만 선언
Delta_coop,N = V_{<=N} - V_{<=1}      W_{2:N} = { x : 2 <= N_req(x) <= N }
```
`V^reach <= V^rel` 은 **고정 snapshot 에서만** 성립. closed-loop optimum 을 계산했다고
주장하지 않고 `L^ctrl` ↔ `U^rel` 의 gap 을 남는 대로 보고한다.

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
- **map**: 무차원 2~3 연속축 + N 이산곡선 + mobility 2~3 층 + 공격자 분포 적분.
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
- 유지 = C2 + C3(무차원 축) + C5 + **certificate 전 계층**. **넣지 않음** =
  optimal stopping · sensing-latency cooperation · multi-shot · 6DOF 재구축
  (= Paper 2~5, `docs/75_blueprint.md` §4).

## 9. 상위 발견의 재서술 (리뷰어 제안 채택)

> **기존 연구 설계가 '협력이 필요한 영역'을 실제 cooperative advantage 존재와
> 무관한 scalar kinematic proxy 로 정의하고 있었고, 그 결과 policy learning 전에
> 확인했어야 할 feasibility question 이 빠져 있었다.**

이것이 논문의 상위 주장이다. `[36,39]` · `N_req=1` · "병목은 tau·theta·cone" 을
확정 사실로 밀면 그 순간 전환이 goalpost moving 으로 보인다 — §2 의 하향 표현을
모든 산출물·발표에 적용한다.
