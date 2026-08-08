# 외부 리뷰 요청 11 — (A) 전환 봉인 문서 2 건 검증 + (B) 거대 청사진 요청

> **★ 답신 도착·반영 완료 (2026-08-09).** 판정 = 요청 A 는 A1 CONDITIONAL /
> **A2 REJECT(편향 2 건 누락)** / **A3 REJECT(선택규칙 미봉인)** / A4 CONDITIONAL /
> A5 RATIFY(조건) / A6 CONDITIONAL / A7 CONDITIONAL / A8 RATIFY.
> **최상위 정정: 12/18 은 URP 행정 마일스톤이지 연구 종료선이 아니다** — 시간 때문에
> C3/C5/certificate 를 자르지 않는다.
> 이행 = `docs/73` r1 (판정·철회·폐기) · `docs/74` r1 (봉인 전면 개정) ·
> **`docs/75_blueprint.md` (청사진 채택본)** · `shepherd/scripts/pivot_manifest.py`.
> 이 파일은 **요청 원문 보존용**이며 아래 내용은 답신 전 상태다 (§0 자원 제약의
> "19주" 표현도 원문 그대로 남긴다 — 답신이 그 전제를 기각했다).

> 그대로 붙여 넣어 쓴다. 리뷰어는 리포 접근이 없으므로 두 문서의 내용을 여기에
> 옮겨 담았다. 요청은 **두 가지**다: ① 봉인이 충분한지 구멍을 찾아라
> ② 그 위에 **19주판 + 5년판 청사진**을 설계해 달라.

당신은 직전 라운드(리뷰 10)에서 우리 방향 전환을 **"조건부 승인, 현 서술로는
불승인"** 으로 판정했다. 우리는 반론 없이 전부 수용하고 두 문서를 작성했다:
판정 로그(docs/73)와 **PIVOT PROTOCOL(docs/74)**. 오늘 이후의 지도 산출물은
docs/74 계약 하에서만 생성된다. 아래 §2~§3 이 그 내용이다.

---

## 0. 자원·제약 (청사진은 이 안에서 짜야 한다)

- **인력**: 학부 2학년 1명(주 연구자) + 코딩 보조 AI. 상시 지도교수 없음
  (희망 랩 컨펌 대기 중). 실험 실행·판단은 전부 1인.
- **계산**: 랩 서버 GPU 1~2 대(현재 MARL 9 런이 점유 중, tmux). CPU 진단은 로컬 가능.
  1 MARL 런 ≈ 수 시간~24 시간. 하드웨어 실험·비행시험 **불가**.
- **기간**: 오늘 2026-08-09. **URP 종료·보고서 마감 2026-12-18 (약 19 주).**
  중간 산출물: KSAS(국내 학회) **추계 초록** 마감 임박, arXiv v1 초안 12월.
- **코드 자산**: 3D 질점 시뮬(동결 계약 + resolved-contract hash), reachable-set
  viability 모듈(단일세그먼트 볼 / 경계구 / bang-bang dogleg union, SE(3) 원뿔
  judge), MAPPO(역할 동결·COMA 배선 존재, 계수 0), scripted 기준선(hold/arc),
  사전등록·해시·리뷰 로그 규율(리뷰 10 회), 테스트 560 개.
- **정직 규율(이미 걸려 있음)**: 진행 중 사전등록 블록의 primary·대역·라벨·판정식
  변경 금지. Phase I 실패 결과는 논문에 보고. chronology 은닉 금지.
- **목표**: Q1 저널 1 편 (IEEE T-AES 또는 Aerospace Science and Technology 급).
  주 연구자의 진로 = 로보틱스/RL 대학원.

## 1. 컨텍스트 압축 (자기완결)

무인기 last-mile 방어. 3D 질점, dt 0.05 s, 지평선 1100 스텝. 공격자 1기(반응형
scripted, `a_att ∈ [11,78] m/s²`, 속도 `[8,30] m/s`, 에피소드마다 균일 draw),
자폭 limiter 4기(`a_lim = 0.35·a_att`, `v_lim = 1.0·att_speed`, kill_radius 0.75 m),
net finisher 1기(그물 **1발**, 비파괴, 전개지연 **τ = 0.30 s = flight 0.15 +
sense 0.10 + decide 0.05**, 포획 판정 = SE(3) 원뿔 half-angle ≈ 12.1°,
축 밴드 [0, 8.22] m).

발사 게이트: `v_shot ≥ θ_fire = 0.9`. `v_shot` = 공격자 τ-reachable **위트니스
2000개** 중 *feasible* 한 것에서 원뿔에 포획되는 **비율**. limiter kill 구를
지나는 회피 경로는 infeasible 로 빠진다 = **협력 shaping 의 유일한 물리 채널**.

**Phase I 결과(커밋된 사실)**: LL(전부 학습) 무력화 **0/300**. LS(편대만 학습 +
발사 scripted) **49/300 = 0.163**, FREE 49/136 · **SHAPING 0/164**. arc scripted
TRAIN p_net 0.110. hold SHAPING 사전측정 0/122. → **어떤 컨트롤러도 SHAPING 에서
한 번도 포획 못 함.** 그 병리를 겨냥한 사전등록 ablation 9 런이 **현재 학습 중,
미열람**(primary = ablation IID 대역 paired Δ p_net, confirmatory 시드 4, 판정식
two-sided 95% CI 하한 > 0, stop rule = 실패 시 본편 rescue 종료).

**Phase II(오늘) exploratory 진단**: 실제 judge 로 `a_att` 를 훑어 무개입 `V_0` 와
limiter kill 구를 **그리디 최적 배치**한 `G_k` 를 비교. 관측: `V_0` 는 a_att≈33
부근에서 문턱을 하향 통과. **문턱 교차가 관측된 이산 점 = 36, 39**. 42 이상에서는
테스트된 탐색으로 교차 미발견(45 에서 0.774, 후보 27배 조밀화 시 0.846, k=3 포화).
발견된 모든 교차는 **첫 봉쇄 구**로 달성. **한계**: seed 0 · a_att 당 에피소드 1 개 ·
상위 3 스냅샷 · 그리디 유한후보 · **도달가능성/NK 존 미요구(teleporting)** ·
유한 위트니스 · judge 에 잡음 없음.

**리뷰 10 판정 요약**: 전환 CONDITIONAL / "협력 marginal value = 0" **REJECT** /
충분경계 upper certificate **필수 RATIFY** / 파라미터 축 승격 CONDITIONAL(거의
RATIFY) / C5 재실행은 adaptive two-stage 로 CONDITIONAL / **regime 정의 REJECT** /
θ 축은 miss-risk 로 부르지 말 것 / 대안 spine RATIFY / Q1 bar 3 층 / 19주 전폭
REJECT(축소하면 가능) / desk-reject 문장 RATIFY.

## 2. docs/73 (판정 로그) 이행 내용

**철회한 문장 4 건 → 대체 표현**
1. "결정 대역 = a_att ∈ [36,39]" → "seed 0 의 선택된 스냅샷·테스트된 relaxed
   탐색에서 **문턱 교차가 관측된 이산 점들**" (연속 구간도, 실제 시스템
   feasibility band 도 아님)
2. "N_req = 1 → 협력의 marginal value 가 기하적으로 존재하지 않는다" → "테스트된
   relaxed 배치 탐색에서 발견된 모든 문턱 교차는 첫 봉쇄 구로 달성됐고 추가 구에서
   표본 이득이 없었다"
3. "병목은 봉쇄 공급량이 아니다" → "후보 조밀화·구 추가가 빠르게 포화 → 요격기 수
   단독이 지배적 병목은 아닐 수 있다는 시사"
4. "그리디이므로 달성가능 하한" → "**relaxed static-placement 문제 최적의 하한**.
   실제 시스템 최적 `V_N^actual` 과 순서관계 없음"

**정의 오류 수정**: `N_req = min{N ≥ 0 : V_N^* ≥ θ}`. `V_0 ≥ θ` 인 점은 **0**
(종전 1 로 표기 → 수정·코드 반영·검증 완료).

**채택한 재정의 (새 연구에만, 동결 블록 불변)**
```
V_0(x)  무개입 | V_1^*(x) 1기 최적(필수 대조군) | V_N^*(x) N기 최적
FREE               : V_0 >= theta
COOP DECISION BAND : V_0 < theta <= V_N^*
INFEASIBLE FOR N   : V_N^* < theta   ← certified upper bound 가 있을 때만 이 이름
NO_SOLUTION_FOUND  : 상한 없이 못 찾은 경우 (기본값)
Delta_coop,N = V_N^* - V_1^*     W_{2:N} = { x : 2 <= N_req(x) <= N }
```
`chi = a_att·tau^2/(2·rho_net)` 은 **free-capture analytic proxy** 로 강등.
"필요 경계는 닫힌형" 주장 **삭제**(포획면이 등방 볼이 아니라 SE(3) 원뿔+축밴드).
축은 raw 6 knob 대신 무차원 `chi`, `kappa = r_kill/rho`, `mu = a_lim/a_att`
(필요시 `eta = v_att·tau/rho`) + 이산 `N`. 6D Cartesian sweep 폐기.

**폐기 3**: regime 이름(`SHAPING_NEEDED`/`FREE_CAPTURE`, 새 연구에서) · 6 raw
파라미터 대규모 sweep · "MARL 이 이기는 논문"에 대한 미련(MARL = mechanism
validation instrument).

**수용한 Q1 bar**: 조건당 독립 realization 20~30 · **통계단위 = episode**(위트니스
bootstrap 금지) · witness 수렴 2k/8k/32k · 가중 민감도 · greedy ↔ global/upper-bound
solver 비교 · relaxed ↔ reachable 분리 · C5 는 3 regime × 시드 5 최소 · 기준선에
**reachable 1-limiter** 필수 · 시드 최상위 hierarchical CI · 0 카운트 binomial 상한 ·
대표점 latency jitter/센서잡음/actuator lag spot-check.

## 3. docs/74 PIVOT PROTOCOL (요지 — 지도 셀을 더 보기 전에 작성)

**Phase I** 원 가설·primary(held-out IID 300 paired)·기준선·결과·**진행 중 블록의
미열람 상태**를 기록하고 그 primary·대역·라벨·판정식 불변을 선언. 완주 후 판정,
**null 도 보고**.

**Phase II** 오늘 진단을 **exploratory 로 봉인**(§1 의 한계 6 항을 그대로 기재).
어떤 판정에도 인용 금지. 철회 문장 4 건 사용 금지.

**Phase III** 지도 계약을 결과 열람 전 고정:
- **v_shot measure 고정 (착수 1)**: 위트니스 구성비·수렴(2k/8k/32k)·가중 민감도
  검증. 해석은 **(R) robust** = 수치 coverage metric + θ = robustness acceptance
  threshold, 또는 **(P) probabilistic** = reachable uncertainty 에 measure P 정의
  후 `v = P(X_tau ∈ C | feasible)` 중 하나로 선언. **현 기본값 = (R)**,
  θ 축은 "viability-envelope sensitivity" 로만 보고.
- **certificate 분리 (착수 2)**: feasible 주장은 도달가능 constructive 구성으로
  `V_N^actual ≥ θ`. impossible 주장은 `V_N^actual ≤ V_N^relaxed ≤ U_N < θ`.
  3층: (A) 후보집합 내 global optimum(MILP/B&B) (B) continuous outer relaxation
  (C) 최저비용 = **unblockable bad mass** `v_max ≤ G/(G+U)`. 상한 없으면
  `NO_SOLUTION_FOUND`.
- 표본: 조건당 20~30 독립 realization, 경계 adaptive refinement, 통계단위=episode.

**Stage-2 (C5) confirmatory 계약 (원문 고정)**
> Stage-2 operating point will be selected exclusively from the completed geometric
> feasibility map using a deterministic rule fixed before any Stage-2 training
> result is observed. Among certified feasible decision-band components, we choose
> the point maximizing the minimum normalized distance to the necessity and
> sufficiency boundaries; ties broken by (1) larger component measure, (2) smaller
> chi, (3) smaller N_req, all fixed prospectively. The training budget, seed list,
> evaluation-set generation, baselines, and the primary paired difference in
> net-capture probability remain identical to the original contract.

+ **3 regime 동시**(FREE / band 내부 / high-difficulty), 점당 시드 5 최소(8~10 권장),
기준선 = hold · arc scripted · MARL · **reachable 1-limiter** · oracle envelope.
**primary 결과는 점수가 아니라 interaction** (RL benefit 이 사전 예측된 envelope
안에서만 출현하는가).

**반증조건 4**: ① 전 범위에서 `W_{2:N} = ∅` → negative systems result
② band 열린 셀에서도 학습 이득 0 → 지도 + 학습가능성 분리 보고로 축소
③ 조밀·비근시안 최적화에서 `N_req ≥ 2` → Phase II 관측 철회
④ `v_shot` 이 witness allocation/해상도에 유의 의존 → **지도 자체를 발표하지 않음**.

**논문 서술 규칙**: Phase I(null) → Phase II(post-hoc 진단) → Phase III(사전명세
파라미터 연구) 를 본문에 명시. "requirement" 는 hardware/context anchor 확보 후에만,
그 전엔 **design envelope / parametric requirement curve**.
spine = *Feasibility-First Design of Cooperative Single-Shot Counter-UAS
Interception under Deployment Latency*.

**이후 금지**: 지도 결과를 본 뒤 정의·축·measure 선언·선택규칙·반증조건 변경 /
Phase II 를 confirmatory 로 인용 / 동결 블록 재해석.

---

# 요청 A — 봉인 검증 (구멍 찾기)

각 항목에 **판정(ratify / conditional / reject) + 근거 + 수정 요구**를 달라.

**A1.** docs/74 가 goalpost-moving 방어로 **충분**한가? 빠진 봉인 항목이 있는가
(예: Phase II 산출물의 해시·타임스탬프 공개 범위, 미열람 상태의 검증 가능성,
"오늘 이후 생성" 을 제3자가 확인할 수 있는 장치)?

**A2.** Phase II 한계 기재가 충분한가? 우리가 아직 자백하지 않은 편향이 있는가?

**A3.** **Stage-2 선택규칙에 남은 researcher degrees of freedom** 을 지목해 달라.
"minimum normalized distance" 의 정규화·경계 불확실성·비연결 성분·다축 동시일 때의
모호성 — 우리 문구로 닫히는가? 닫히지 않으면 대체 문구를 써 달라.

**A4.** 재정의(`V_0/V_1^*/V_N^*`, `Delta_coop`, `W_{2:N}`, `N_req`) 에 논리적 결함이
있는가? `V_N^*` 의 "admissible N-agent 전략" 을 실제로 계산 가능한 형태로 좁히는
정의를 제안해 달라 (도달가능성 제약을 어디까지 넣어야 실제 시스템 주장을 할 수
있는가 — 예: 시각 t 에서의 도달집합 제약, open-loop vs closed-loop, 공격자 반응 포함 여부).

**A5.** measure 해석을 **(R)** 로 선언하는 것으로 Q1 을 통과할 수 있는가, 아니면
**(P)** 가 불가피한가? (R) 로 갈 때 θ = 0.9 라는 **특정 값**의 자의성은 어떻게 방어하는가?

**A6.** 무차원 축 선택(`chi`, `kappa`, `mu`, `eta`) 이 이 시스템의 메커니즘을
실제로 collapse 시키는가? 빠진 무차원 수가 있는가 (원뿔 half-angle, 축밴드/ρ 비,
standby 반경/교전거리, 공격자 반응 gain 등)?

**A7.** 표본 요구(조건당 20~30, 통계단위=episode)와 **1 인·19 주·GPU 1~2 대**
제약이 양립하는가? 양립하지 않으면 어디를 줄이는 것이 통계적으로 가장 덜 아픈가?

**A8.** 동결 블록 처리(기존 정의로 완주·판정·보고, 재정의는 소급 없음)가 적절한가?
9 런 결과가 null 일 때 그것을 Phase III 논문에서 **어떻게 인용**해야 정직한가?

---

# 요청 B — 거대 청사진 (이게 본 요청이다)

우리는 지금 "다음 실험"이 아니라 **연구 전체의 지도**가 필요하다. 아래 두 층을
**구체적으로** 설계해 달라. 추상적 조언이 아니라 **주차·산출물·게이트·그림 목록**
수준으로 원한다.

## B1. 19주판 (2026-08-09 → 12-18, Q1 투고 초안까지)

1. **주차별 계획**: 각 주의 산출물 1~2 개와 **kill/continue 게이트 조건**.
   게이트는 "무엇을 보면 이 경로를 버리는가" 를 숫자로.
2. **기술 부품 목록**: 각 부품의 최소 스펙 · 예상 난이도(1인 기준 일수) ·
   실패 시 대체안. 최소 다음을 포함해 판단해 달라:
   - `v_shot` measure 검증 하네스 (구성비·수렴·가중 민감도)
   - 후보집합 내 **global optimum** solver (MILP/B&B) — 규모 추정과 현실성
   - **continuous outer relaxation** 상한 — 실제로 구현 가능한 형태 제안
   - **unblockable bad mass** certificate — 가장 싼 경로라 했는데, 구체 알고리즘
   - **reachable-constrained** `V_N^actual` 하한 (constructive controller)
   - 지도 생성 파이프라인(무차원 축 × 20~30 realization × 경계 refinement)
   - C5 학습 3 regime × 시드 5~10
   - robustness spot-check (jitter/노이즈/actuator lag)
3. **논문 1 편의 구조**: 섹션 구성 + **필수 그림·표 목록**(각 그림이 어떤 반박을
   막는지 명시) + 최소 결과 집합. 그림은 6~8 장 이내로 골라 달라.
4. **투고 전략**: T-AES vs AST vs 대안. 각각의 심사 성향에 맞춘 프레이밍 차이.
   12/18 시점에 **초안**만 가능하다면 투고 시점은 언제로 잡아야 하는가.
5. **KSAS 추계 초록**(마감 임박, 1~2 페이지): 지금 확정된 것만으로 쓸 수 있는
   초록의 내용은 무엇인가? Phase II 를 넣어도 되는가, 아니면 Phase I null +
   문제 제기만으로 쓰는 것이 안전한가?
6. **분기 트리**: 반증조건 ①~④ 각각이 발동했을 때의 **대체 산출물**(무엇을 쓰고,
   어느 급 저널로 가고, 무엇을 잘라내는가).

## B2. 5년판 (2026 겨울 → 대학원)

1. **논문 라인**: Paper 1(feasibility envelope) 이후 Paper 2 · Paper 3 의 주제를
   **선행 종속성**과 함께. 각 논문이 독립적으로 서는 최소 기여는 무엇인가.
   후속 후보로 우리가 들고 있는 것: (α) 발사 정책을 기대효용 optimal stopping 으로
   재정식화 (β) 협력의 대상을 회피집합 봉쇄에서 **탐지·조준 지연 단축**으로 이동
   (γ) multi-shot/reload 로 K=1 전제 완화 (δ) SE(3)/6DOF·하드웨어 전이.
   순서와 취사선택을 지정해 달라.
2. **자산 축적 전략**: 시뮬레이터·certificate 도구·벤치마크 계약 중 무엇을
   **공개 자산**으로 키워야 인용·후속에 유리한가? (코드 공개는 가능)
3. **하드웨어 전이 시점**: 언제부터 실기가 필요한가, 그 전에 시뮬만으로 갈 수 있는
   최대 거리는 어디인가.
4. **커리어 정합**: 학부 2학년 → 대학원(로보틱스/RL) 경로에서 이 라인이
   **주는 것**과 **주지 못하는 것**. 이 라인만 파는 것이 위험한가? 병행해야 할
   역량·산출물이 있는가.
5. **가장 큰 장기 리스크**와 그 조기경보 지표.

## B3. 우리가 하지 말아야 할 것

sunk cost 로 붙잡고 있을 위험이 큰 항목을 **이름으로** 지목해 달라 (기존 코드·
기존 프레임·기존 baseline·기존 지표 중). 버릴 때의 손실도 함께.

---

## 산출 형식 요청

1. 요청 A: 항목별 판정 + 수정 문구(가능하면 그대로 쓸 수 있는 영문 원문).
2. 요청 B1: **주차 표**(주 / 산출물 / 게이트) + 부품 표(스펙 / 일수 / 대체안) +
   그림 목록(그림 / 막는 반박) + 분기 트리.
3. 요청 B2: 논문 라인 표(논문 / 기여 / 선행조건 / 예상 venue / 시점).
4. 마지막에 **"만약 하나만 고른다면"** — 19주에 단 하나의 산출물만 만들 수 있다면
   무엇을 만들어야 하는가.

칭찬·요약 반복은 필요 없다. 우리가 과대주장하거나 자기기만하고 있는 지점을
계속 지적해 달라.
