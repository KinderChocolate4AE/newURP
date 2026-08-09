# 76 — 선행연구 조사 (Feasibility-First spine 기준) — v2, 2026-08-09

**대상 spine**: *Feasibility-First Design of Cooperative Single-Shot Counter-UAS
Interception under Deployment Latency* (docs/75 §0, docs/74 r3.2)

**조사 기준**: "MARL 방법론" 이 아니라 **산출물의 논리 구조**로 검색했다. 즉
`L^reach_{<=N,clean} <= V <= U^rel_{<=N}` sandwich · `U^rel_{<=1} < θ <= L^reach_{<=N}`
(협력 필요성 certificate) · 파라미터 셀별 `{FREE / SINGLE / COOP / INFEASIBLE / AMBIGUOUS}`
prevalence + boundary adaptive refinement · 유한 witness 표본의 coverage measure ·
무차원 collapse — 이 다섯 개가 검색축이다.

**v2 변경 (2026-08-09 2차 조사)**: v1 §7 에서 미조사로 남겼던 **OR / PSE (process systems
engineering) 축 — robust feasibility · feasible region DoE — 를 조사해 통합**했다.
결과로 **Tier 0 순위가 바뀌었다.** 우리와 가장 가까운 단일 문헌군은 SIVIA 가 아니라
**Grossmann 계열 flexibility/feasibility analysis** 다. 특히 **stochastic flexibility
(1990) 는 우리 `p_C(z)` 와 정의가 같다** — docs/74 §3.9b 의 "셀을 한 색으로 칠하지 않고
prevalence 로 보고" 결정은 36 년 된 표준의 재발명이다.

**핵심 결론 (v1 에서 유지·강화)**: 우리가 하려는 일의 **방법론적 조상은 counter-UAS/MARL
문헌에 없다.** 집합 역산 · 공정 flexibility 분석 · robust design solution space ·
level set estimation · sound HJ bound · parametric requirement mining 계열에 **거의 1:1
대응하는 구조**가 이미 있다. 지금까지 이걸 한 번도 인용하지 않았다 — 리뷰어가 먼저 찾으면
"새 프레임인 줄 알았는데 40년 된 기법의 재발명" 으로 읽힌다. 반대로 먼저 인용하면
**우리 논문의 정당성이 급상승한다** (검증된 기법을 적대적 게임 + 유한발수 요격에 최초 이식).

**검증 상태 표기**: ✅ = 서지 확인(URL/DOI 확인) · ⚠️ = 검색 스니펫 수준, 원문 미독 ·
❓ = 존재·내용은 확인, 권/호/페이지 등 세부는 기억 기반 → **인용 전 서지 재확인 필수**.
**⚠️/❓ 를 논문에 넣기 전 원문 정독 필수** (docs/73 §4 desk-reject 방어선 + Huh dwell
provenance 균열의 교훈).

---

## Tier 0 — 방법론적 쌍둥이 (도메인은 다르나 **산출물 구조가 동형**). 최우선.

이 티어가 이번 조사의 본론이다. 순서 = 우리와의 근접도 (v2 재정렬).

### 0-1. ★ Flexibility / Feasibility Analysis 계열 — Grossmann 학파 (1983~현재) ❓✅

우리 산출물과 **개념 하나하나가 대응**한다. 조사 전체에서 가장 가까운 단일 문헌군.

| 그쪽 개념 | 우리 개념 | 문헌 |
|---|---|---|
| **feasibility function** `ψ(d) = max_θ min_z max_j f_j(d,z,θ) <= 0` (max-min-max) | `U^rel_{<=N} < θ` 판정 = "어떤 배치로도 불가" | Halemane & Grossmann 1983, *AIChE J* ❓ |
| **flexibility index** `F` = 제약을 지킬 수 있는 최대 파라미터 편차 | certified envelope 의 크기 | Swaney & Grossmann 1985, *AIChE J* ❓ |
| **stochastic flexibility `SF`** = **feasible operation 을 유지할 확률** | **`p_C(z)` prevalence** (docs/74 §3.9b) | Straub & Grossmann 1990/1993, *Comput. Chem. Eng.* 17:339–354 ✅ |
| **surrogate-based feasibility analysis for black-box stochastic simulation (heteroscedastic noise)** | 우리 계산 상황 그 자체 (잡음 있는 시뮬레이터에서 feasible region 찾기) | Wang & Ierapetritou 2018, *J. Global Optim.* ✅ (10.1007/s10898-018-0615-4) |
| **design centering** = feasible region 안에 최대 내접 영역 / nominal 점 선택 | Stage-2 점 선택 (docs/74 §4.2) | Zhao et al. 2022, *CCE* "Novel formulations of flexibility index and design centering for design space definition" ✅ |
| flexibility index by **cylindrical algebraic decomposition** (exact) | exact solver 의 지위 문제 (docs/74 §3.6) | *CCE* 2020 ✅ |

- **같은 점**:
  - **"feasibility 를 성능과 분리해 먼저 묻는다"** 는 문제의식 자체가 이 학파의 정의다.
    docs/75 §0 "알고리즘 성능이 아니라 메커니즘이 성립하는가" 는 이 전통의 언어로
    그대로 번역된다.
  - `SF` = "제약을 만족할 확률" 은 **우리 `p_C(z)` 와 정의가 같다.** 우리가 리뷰 15
    항목 5 를 받아 "셀 하나에 한 색을 칠하지 않는다" 로 바꾼 것은 이 개념의 재발명이다.
  - Wang & Ierapetritou 2018 은 **black-box + 확률적 + 이분산 잡음** 시뮬레이터에서
    feasible region 을 추정한다 — 우리 계산 조건과 동일.
  - "feasibility test(가능한가) vs flexibility index(얼마나 여유 있나)" 의 2단 구분은
    우리 "certified label(라벨) vs `p_C`(유병률)" 2단 구분과 같은 구조.
- **다른 점 (= 우리 기여의 자리)**:
  - **적대자가 없다.** 공정 flexibility 는 `max_θ min_z` — θ 는 자연의 불확실성이고,
    제어변수 `z` 는 **사후에 자유롭게 조정 가능**하다. 우리는 `z` 가 **동역학·도달가능성·
    충돌·전개지연에 묶여 있고**, 상대가 반응한다. 즉 우리 inner problem 이 훨씬 나쁘다.
  - **하한이 constructive 여야 한다.** flexibility 문헌의 feasible 판정은 "제약 만족
    해가 존재한다" 로 끝나지만, 우리 `L^reach_{<=N,clean}` 은 **joint time-parameterized
    궤적 N 개를 실제로 구성**해야 인정된다(docs/74 §3.7 r3.2). 이건 그쪽에 없는 요구다.
  - **팀 크기 필요성** (`U^rel_{<=1} < θ <= L^reach_{<=N}`) 개념이 없다. 그쪽에 대응물이
    없는 유일한 우리 고유 축.
- **써먹는 법**:
  1. **§3 Feasibility formulation 을 이 어휘로 다시 쓴다.** "feasibility function /
     flexibility index / stochastic flexibility" 는 40 년 된 표준어다. 우리가 새로 만든
     것처럼 쓰면 손해다.
  2. **`p_C(z)` 를 `SF` 인용과 함께 도입** → docs/74 §3.9b 결정이 임의적 선택이 아니라
     표준 관행임을 즉시 보증. **가장 값싼 신뢰도 상승 지점 중 하나.**
  3. Wang & Ierapetritou 2018 은 **§4 의 계산 설계 근거** (잡음 있는 시뮬레이터에서
     feasible region 을 추정할 때의 표본/surrogate 전략).
  - ⚠️ 주의: 이 학파는 화학공학 저널에 있다. T-AES/AST 심사자는 모를 수 있으므로
    **"process systems engineering 에서 확립된 feasibility analysis 를 적대적 요격
    문제로 이식한다"** 라고 명시적으로 다리를 놓아야 한다. 그냥 인용만 하면 안 읽힌다.

### 0-2. Set Inversion via Interval Analysis (SIVIA) — Jaulin & Walter 1993, *Automatica* 29(4) ✅

- **하는 일**: 파라미터 박스를 재귀 이분(branch & bound)하면서 각 박스를
  **feasible / infeasible / indeterminate** 3분류. 해집합을 **inner 근사와 outer 근사
  사이에 bracket**. indeterminate 박스만 더 쪼갠다.
- **같은 점**:
  - 3분류 = 우리 `CERTIFIED-* / INFEASIBLE-N / AMBIGUOUS` 와 **정확히 같은 논리**.
  - inner/outer bracket = 우리 `L^reach <= ... <= U^rel` sandwich.
  - "indeterminate 박스만 refine" = docs/75 W12 **boundary adaptive refinement**.
  - "AMBIGUOUS 를 숨기지 않는다"(docs/75 §4 Fig 6) = SIVIA 가 indeterminate 층을
    항상 그리는 관행과 동일.
- **다른 점**:
  - SIVIA 는 **정적 비선형 방정식/부등식**의 해집합. 우리는 **적대적 상대가 반응하는
    동역학 게임** → interval contractor 로 못 닫는다.
  - SIVIA 의 bracket 은 **결정론적 구간연산**으로 sound. 우리 `U^rel` 은
    **낙관적 완화(optimistic relaxation)** 로 sound, `L^reach` 는 **constructive witness**
    로 sound → soundness 논증이 완전히 다르다.
  - SIVIA 는 셀에 단일 라벨(결정론). 우리는 **라벨 prevalence 벡터** — 확률이 한 겹 더.
- **써먹는 법**: §4 도입부에서 "우리 절차는 set-inversion 구조를 적대적 유한발수 요격
  문제로 이식한 것" 이라고 **명시적 위치잡기**. AMBIGUOUS 방어 시 "indeterminate layer 는
  이 계열의 표준 산출물" 로 인용 → "왜 결론 못 내는 셀을 그리냐" 공격 무력화.
- 관련 ⚠️: 구간해석으로 **viability kernel** 계산 (Springer 2018, *Interval Computing of
  the Viability Kernel with Application to Robotic Collision Avoidance*) — viability 언어와
  SIVIA 를 잇는 다리.

### 0-3. Computing Sound Lower and Upper Bounds on Hamilton-Jacobi Reach-Avoid Value Functions — arXiv 2511.15238 (2025) ✅(초록 확인)

- **하는 일**: 격자 HJ reachability 의 **이산화 오차를 인정**하고 값 함수에 대한
  **certified upper/lower bound** 계산. BRS 의 sound over-approximation + RAS 의 sound
  under-approximation. **분류가 안 된 셀만 분할하는 refinement.**
- **같은 점**: 우리 sandwich 의 **정확한 단일-에이전트 판**. "under-approx = 실현 가능
  보증 / over-approx = 불가능 보증" 의 비대칭도 docs/74 §3.2 (boxed 무시가 upper 에서
  sound) 와 같은 사고방식.
- **다른 점**: 단일 시스템. 멀티에이전트·팀 크기 필요성 없음. 격자 HJ 라 우리 상태차원
  (4 limiter + net-drone + attacker)에는 직접 적용 불가.
- **써먹는 법**: **방법론 인용 1순위 중 하나.** "HJ 로 하면 sound bound 가 원리상 가능하나
  차원의 저주로 우리 문제에선 불가 → 그래서 witness-coverage 기반 sound bound 쌍을
  설계했다" 는 논리 사슬을 이 논문 하나로 만든다.

### 0-4. ★ Level Set Estimation (LSE) — Gotovos·Casati·Hitz·Krause, IJCAI 2013 ✅ + 후속

- **하는 일**: 미지 함수 `f` 의 **`f >= h` 상위집합을 GP 신뢰구간으로 추정**. 각 점을
  **H (확실히 위) / L (확실히 아래) / U (미결정)** 로 분류하고, **U 를 줄이는 방향으로
  능동 표본**. **표본복잡도 보증** 있음. 원조는 straddle heuristic
  (Bryan et al. 2005 ❓): `1.96σ(x) − |μ(x) − h|` 최대화 = "경계 근처 + 불확실한 곳".
- **후속**: randomized straddle (arXiv 2408.03144) ✅ · **(ε,δ)-accurate LSE with a
  stopping criterion** (arXiv 2503.20272) ✅ · multiscale GP LSE ⚠️.
- **같은 점**:
  - **H/L/U 3분류 = 우리 CERTIFIED / INFEASIBLE / AMBIGUOUS 의 통계적 쌍둥이.**
    SIVIA 가 결정론 버전이면 LSE 는 확률 버전이고, **우리 문제는 확률 버전에 속한다**
    (시뮬레이터가 확률적이므로).
  - "미결정 영역에 표본을 몰아넣는다" = docs/75 W12 boundary adaptive refinement.
  - `θ` 라는 명시적 임계값 위의 상위집합 추정 = 우리 `v_shot >= θ` 그 자체.
- **다른 점**:
  - LSE 는 **GP 사전분포**를 깔고 그 위에서 신뢰구간을 만든다 → 보증이 GP 가정에 의존.
    우리는 **certificate 를 물리/기하로 sound 하게** 만들고 통계는 episode 표본에만
    쓴다. 이 차이는 **우리 쪽이 강한 지점**이므로 명시할 것.
  - LSE 에는 "몇 개의 에이전트가 필요한가" 축이 없다.
- **써먹는 법 — 이건 인용이 아니라 실제 gap 이다**:
  > **docs/75 W12 (boundary adaptive refinement) 에 종료조건이 없다.**
  > "경계 근접 셀 replication 60~100+" 만 있고 *언제 멈추는가* 가 프로토콜에 없다.
  > (ε,δ)-accurate LSE 의 stopping criterion 은 `Z_master` 사전봉인과 충돌하지 않는다
  > (어느 master 점을 언제까지 평가할지의 규칙일 뿐, hypothesis space 를 만들지 않는다).
  > **docs/74 §3.8 에 결정론적 종료규칙으로 추가할 것.** 지금 상태면 "경계를 얼마나
  > 갈아야 충분한가" 가 결과를 보고 결정되는 자유도로 남는다 — §7 금지사항 위반 소지.

### 0-5. Computing Solution Spaces for Robust Design — Zimmermann & von Hoessle 2013, *IJNME* 94(3):290–307 ✅

- **하는 일**: 고차원 비선형 시스템에서 **요구성능을 만족하는 설계 파라미터 박스
  (solution space)** 를 계산. "최적 한 점"이 아니라 **영역**을 산출.
- **같은 점**: docs/75 §6 "Certified design envelope 가 논문 본체" 와 목적이 같다.
  "성능 최적점은 solution box 안에 없다(robustness ↔ optimality 상충)" 은 우리
  "MARL 이 이기는 논문에 대한 미련 폐기"(docs/73 §6-3) 와 같은 철학.
- **다른 점**: 상대가 없다. 우리 solution space 는 **min-max 구조** 안에서 정의되고
  하한이 상대의 반응을 뚫고 실현되어야 한다(4A joint feasibility).
- **써먹는 법**: T-AES 프레이밍에서 **"systems design" 어휘를 빌려온다.**
  "model-conditional design envelope"(docs/73 §6.2)를 이 계열 용어로 번역하면 리뷰어가
  곧바로 알아듣는다. 0-1 (Grossmann) 과 같이 인용해 "설계 영역 산출" 계보를 만든다.

### 0-6. ★ Probabilistic Design Space (QbD / ICH Q8 계열) — Bano et al. 2018 *AIChE J* ✅ 외 ⚠️

- **하는 일**: 제약 제조 공정에서 **"품질 규격을 만족한다는 보증(assurance)을 제공할 수
  있는 운전변수 영역"** 을 **Bayesian posterior predictive 확률**로 정의. 확률 임계값
  이상인 입력 조합의 부분집합을 design space 로 삼는다.
- **같은 점 — 문장 수준에서 일치**:
  > *"design space 는 규격 충족에 대한 assurance 를 제공할 수 있는 영역이며,
  > 이 assurance 는 결정론적이지 않고 **확률적으로 진술되어야 한다**."*
  >
  > 이건 docs/73 §6.2 자기기만 2번 ("무차원 지도가 나오면 그 자체로 requirement 가
  > 아니다") 과 docs/74 §6 ("requirement 는 anchor 확보 후에만") 의 **규제과학 버전**이다.
  - 확률 임계값 위에서 영역을 정의 = 우리 `LCB95(p_C) > p_min = 0.05` eligibility.
- **다른 점**: 적대자·동역학 없음. 그리고 그쪽은 **규제기관이 인정하는 anchor(실제 공정
  데이터)** 가 있다 — 우리에겐 없다(docs/75 §9). 이 비대칭을 정직하게 쓸 것.
- **써먹는 법**: **"requirement 가 아니라 model-conditional design envelope" 선언의
  최강 방어 인용.** 규제과학에서 확률적 design space 가 표준이라는 사실은,
  우리가 결정론적 requirement 를 주장하지 않는 것이 **회피가 아니라 규범 준수**임을
  보여준다. docs/73 §4 desk-reject 문장 대응축 (iv) 에 직접 투입.

### 0-7. Parametric STL / Requirement Mining — Asarin·Donzé·Maler·Ničković (RV 2011) + Jin·Donzé·Deshmukh·Seshia + ParetoLib 2.0 ⚠️

- **하는 일**: 명세의 상수를 파라미터로 두고 **명세가 만족되는 파라미터 영역
  (validity domain)** 을 합성. counterexample-guided refine.
- **같은 점**: "θ 를 상수로 방어하지 않고 슬라이스로 보고"(docs/74 §3.5)와 발상이 동일.
  `L(z)`, `U(z)` 연속 surface = validity domain 의 정량판.
- **다른 점**: PSTL 은 **관측 trace 로부터 사후 mining**. 우리는 **사전등록된 격자 위
  prospective 계산**(docs/74 §3.8 `Z_master` + `lattice_hash`) → 검정 자유도가 구조적으로
  다르다. **이 차이가 우리 쪽 강점이므로 명시적으로 대비할 것.**
- **써먹는 법**: "requirement 를 데이터에서 캐는 것" vs "requirement 후보 영역을 사전에
  봉인하고 certificate 로 닫는 것" 의 구분 → docs/74 §7 금지사항의 학술적 근거.

### 0-8. Three-Valued Abstraction / Model Checking (true·false·unknown + refinement) ⚠️

- **같은 점**: **"모르면 모른다고 판정하고 refine 한다"** 의 형식적 원형.
  docs/73 §5.1 분기 ①-C ("AMBIGUOUS 다수면 negative claim 금지") 는 three-valued
  semantics 의 규율 그 자체.
- **다른 점**: 이산 전이 시스템. 우리는 연속 파라미터 + 확률 prevalence.
- **써먹는 법**: 1~2 편이면 충분. "결론 없음" 을 **연구 실패가 아니라 정식 verdict** 로
  만드는 데 쓴다 — 우리 프로토콜의 가장 취약한 사회적 지점이다.

### 0-9. Robust Optimization + Infeasibility Certificate (OR 정통) ✅

- **Ben-Tal & Nemirovski robust counterpart** (1998~2002; 단행본 *Robust Optimization*,
  Princeton 2009): 불확실성 집합 **전체에 대해 feasible 함이 보장되는** 해. 타원형
  불확실성 집합이면 tractable convex 로 환원.
- **Farkas' lemma / 쌍대성 기반 infeasibility certificate**: `Av <= b` 가 불가능함을
  **`λ >= 0, λᵀA = 0, λᵀb < 0` 인 λ 하나로 증명**. LP 솔버가 실제로 내놓는 산출물.
- **같은 점**:
  - **"불가능성은 증거(certificate)로 증명한다"** 가 OR 의 표준. 우리 `U^rel_{<=N} < θ`
    는 정확히 **infeasibility certificate** 다. → **용어를 이쪽에 맞추면 소통비용이
    크게 준다.** 지금 우리는 "upper certificate" 라는 자체 용어를 쓰고 있다.
  - "완화 문제가 불가능하면 원문제도 불가능" 이라는 논증 형식(docs/74 §3.2 의 비대칭)이
    바로 relaxation-based infeasibility proof 의 표준 형태.
- **다른 점 — 혼동 주의**:
  - robust counterpart 는 **worst-case 에 대해 feasible** 을 요구하는 **보수적** 개념.
    우리 `U^rel` 은 반대로 **방어측에 유리한 낙관적 완화**다. 둘을 같은 단어로 쓰면 안 된다.
    논문에서 **"optimistic relaxation yielding an infeasibility certificate"** 로 못박을 것.
  - Farkas 는 볼록/선형 구조가 필요. 우리 문제엔 직접 적용 불가 → 우리 certificate 가
    **왜 다른 방식이어야 하는지**를 설명하는 데 쓴다.
- **써먹는 법**: §4 첫 문단에서 용어 정렬 1회. `U^rel < θ` 를 "infeasibility certificate"
  로 부르고 Farkas 를 각주로 → OR/제어 독자 양쪽에 동시에 통한다.

### 0-10. Feasible Region DoE — 능동표본 / 통계적 판정 ✅⚠️

| 문헌 | 내용 | 우리와의 관계 |
|---|---|---|
| **Batur & Kim 2010, *ACM TOMACS*** ✅ | 다중 확률제약 하에서 **어떤 시스템이 feasible 인지 정해진 오류확률로 판정**하는 ranking & selection 절차 | **셀별 라벨 판정의 정통 조상.** 우리는 표본수(20~30)를 손으로 정했는데, 이쪽은 **요구 판정신뢰도에서 표본수를 유도**한다 → docs/74 §3.10 표본정책 근거 강화 경로 |
| Indifference-zone relaxation for finding feasible systems (arXiv 2509.04514) ⚠️ | IZ 완화판 | 경계 근접 셀에서 "구분 불가" 를 정식 처리 = AMBIGUOUS 의 R&S 판 |
| Adaptive sampling with **automatic stopping** for feasible region identification (*Eng. with Computers* 2021) ✅ | 공학설계 feasible region 능동표본 + **정지규칙** | 0-4 와 함께 **W12 종료조건 부재** 를 메우는 후보 |
| Bayesian active learning for feasible region identification (*J. Intell. Manuf.* 2025) ✅ | 탐색/활용 trade-off | 경계 refinement 예산 배분 |
| Constrained BO / FuRBO (arXiv 2506.14619) ⚠️, Constraint Active Search (arXiv 2602.15595) ⚠️ | feasible 영역이 작고 불규칙할 때의 탐색 | 우리 COOP 셀이 희소할 경우의 탐색 전략 참고 |

- **공통 차이점**: 전부 **최적화를 위한 feasible 영역 탐색**이다. 우리는 최적화가 목적이
  아니라 **영역의 존재/부재 자체가 결론**이다. 그래서 그쪽은 AMBIGUOUS 를 없앨 대상으로
  보지만 **우리는 AMBIGUOUS 를 보고 대상으로 삼는다**(docs/75 §4). 이 차이를 §4 에 한 줄.
- **써먹는 법**: Batur & Kim 만 정면 인용, 나머지는 묶어서 1문장.

---

## Tier 1 — 문제 구조가 같은 것 (협력 요격 · N 의 필요성)

### 1-1. Multiplayer Reach-Avoid Games via Pairwise Outcomes — Chen, Zhou, Tomlin, *IEEE TAC* 62(3):1451–1457, 2017 ✅

- **하는 일**: N_A vs N_D reach-avoid 게임을 1:1 HJ 결과로 분해 → **최대 매칭**으로 합쳐
  **수비팀 성능 보증**을 준다.
- **같은 점**: 4A 의 "agent-candidate bipartite assignment"(docs/74 §3.7)와 동일 도구.
  전체 게임은 못 풀지만 **보증 가능한 하한을 구성적으로 만든다**는 전략이 같다.
- **다른 점**: 이들의 보증은 "capture" 라는 이진 사건. 우리는 **coverage measure
  `v_shot >= θ` + not boxed** 게이트 → 매칭만으로 안 닫히고 threshold-feasibility 가 한 겹
  더 필요. 또 우리는 **팀 크기 필요성**(N=1 로 불가 증명)까지 요구한다.
- **써먹는 법**: `L^reach` 알고리즘의 직계 조상으로 인용. 우리 기여 = "pairwise 분해 +
  threshold coverage + deployment latency" 확장.
- 후속 ⚠️: MISOCP reach-avoid (Lorenzetti et al. CDC 2018), 2 attackers vs 1 defender + MIP
  (arXiv 2309.13155), 3D heterogeneous matching (arXiv 1909.11881), **defender-side
  information delay** (arXiv 2606.24542 — 지연을 게임에 넣은 최신, 우리 τ 와 가장 가까움).

### 1-2. Perimeter Defense Games — Shishika & Kumar (arXiv 1909.03989; review: GameSec 2020) ✅

- **하는 일**: 침입자-방어자 reach-avoid. **"한 대로는 못 잡는 침입자를 두 대가 팀을 이뤄
  잡는 cooperative maneuver"** 를 해석적으로 유도하고 팀 전략에 쓴다.
- **같은 점**: **우리 핵심 한 줄 `U^rel_{<=1} < θ <= L^reach_{<=N}` 의 해석적 선례.**
  "협력이 왜 필요한가" 를 알고리즘 성능이 아니라 **구조적 불가능/가능 대비**로 답한다.
- **다른 점**: (i) 협력 필요성이 **닫힌 형태로 증명**되고 우리는 **수치 certificate**.
  (ii) perimeter 라는 강한 기하 제약 vs 우리 자유공간 + 원뿔 발사조건.
  (iii) **전개 지연(τ)·유한 1발 없음.**
- **써먹는 법**: **§1 Introduction 정당화 인용 1순위.** "협력 필요성을 certificate 로
  묻는다" 가 허공에서 나온 질문이 아님을 보여준다. 동시에 "단일 기하·즉시 포획 가정이라
  우리 문제로 이전 불가" 를 한 문장으로 붙인다.

### 1-3. StringNet Herding — Chipade & Panagou, *Frontiers in Robotics and AI* 8:640446 (2021), 3D 확장 arXiv 2007.04406 ✅

- **하는 일**: 방어자들이 **string barrier 로 닫힌 대형**을 만들어 적 군집을 포위·유도.
  **"공격자 초기 위치가 어떤 조건을 만족하면 방어자가 제때 대형을 갖춘다"** 는 보증.
- **같은 점**: 물리적 봉쇄 + **초기조건에 대한 충분조건**. 우리 `L^reach` 의 정신
  (구성적 증인 + 도달가능성 검사)과 같다. 이전 spine (CLAUDE.md A.2 축 A herding) 의 직계.
- **다른 점**: barrier 가 **연속적으로 유지**되는 메커니즘 → 우리처럼 **한 순간의
  발사조건**(single-shot θ gate)을 넘길 필요가 없다. 지연도 없다. 그리고 **불가능
  certificate(upper bound)를 만들지 않는다** — 조건이 안 맞으면 보증이 없을 뿐, "어떤
  배치로도 불가" 를 증명하지 않는다. **여기가 우리 빈칸.**
- **써먹는 법**: "충분조건만 있는 문헌 vs 필요조건(불가능)까지 닫는 우리" 대비의 대표 사례.

### 1-4. Intercepting an Agile Target with Net-Carrying Drones using Competitive MARL — Gavin & Bronz, ICUAS 2026 (arXiv 2607.05939) ✅

- **동시기 최근접 응용 prior.** 그물 탑재 드론 팀 + MAPPO + Prioritized Fictitious
  Self-Play, CTBR 저수준 제어, 고충실도 시뮬.
- **같은 점**: 문제 설정(그물·팀·회피 표적·MARL·self-play)이 우리 Phase I 과 거의 같다.
  **우리가 Phase I 에서 쓰려던 그 논문이 이미 나왔다고 봐야 한다.**
- **다른 점 (= 우리 생존 근거)**: **feasibility/capture-region 분석이 없다.** catch rate ·
  time-to-capture · crash rate 라는 **성능 지표만** 보고. 전개 지연, 발사조건, "협력이
  필요한 영역이 존재하는가" 는 다루지 않는다.
  → **우리 pivot 이 옳았다는 외부 증거.** 성능 경쟁을 계속했으면 정면 충돌해 졌을 가능성.
- **써먹는 법**: §2 Problem & provenance 에서 "이 라인의 최신 결과조차 성능 지표만
  보고하며 메커니즘이 성립하는 영역을 특정하지 않는다" 로 **우리 질문의 공백을 증명**.
  ⚠️ **원문 정독 필수** (net 전개 모델 유무, 팀 크기가 초록에 없다).

### 1-5. Counter-UAS MARL 일반 계열 ⚠️

- Huh et al. 2026, *Machines* 14(4):413 (**본디 pursuit-evasion MARL / detectable region
  논문이며 net-capture 논문이 아니다** — CLAUDE.md A.11 provenance 균열 유지),
  MAGNET, AirSim MAPPO counter-drone swarm (*Eng. Proc.* 2026), 요격 우선순위 RL
  (arXiv 2508.00641), 다중 로그드론 요격 MARL (IEEE 2023).
- **공통점**: 전부 **알고리즘 성능 비교**. **공통 결함**: 문제가 애초에 풀리는 영역인지
  묻지 않고, 실패를 보고하지 않는다.
- **써먹는 법**: 한 문단으로 묶어 인용 → "이 문헌군 전체가 feasibility 를 전제한다" 가
  우리 gap statement. 개별로 파고들 가치는 낮다.

### 1-6. 조합적 pursuit-evasion 의 "몇 명이 필요한가" 정리 ⚠️

- 다각형 환경 완전가시 추격에서 **3 pursuers always suffice, sometimes necessary**
  (Bhadauria·Klein·Isler·Suri 계열), genus g 곡면에서 4g+4 등.
- **같은 점**: **팀 크기의 필요·충분을 정리로 답한다** — 우리 `N_req` 의 이상적 형태.
- **다른 점**: 이산 기하·동일 속도·즉시 포획. 동역학·지연·발사조건 없음. 우리는 정리를
  못 만드니 **certificate 로 대체**한다 — 이 대체의 정당화가 §4 의 역할.
- **써먹는 법**: "`N_req` 는 이 분야의 정통 질문이다" 를 1문장 근거로.

### 1-7. Target-Attacker-Defender / 능동 표적 방어 — Garcia·Casbeer·Pachter (JOTA 2021 등) ✅

- **같은 점**: **escape region / 생존 보장 영역** 이라는 산출물 형태. 초기 상태 집합을
  결과로 내놓는다는 점에서 우리 envelope 와 동류.
- **다른 점**: 2~3 플레이어 해석해. 유한발수·coverage measure·팀 크기 필요성 없음.
- **써먹는 법**: 항공우주 독자에게 "상태공간을 영역으로 분류하는 것은 이 분야 표준
  산출물" 임을 보증하는 배경 인용.

---

## Tier 2 — 발사조건(θ gate)의 조상: Engagement Zone / Capturability

우리 `g_θ(x,P) = 1[v_shot >= θ AND NOT boxed]` 는 이 문헌군의 **협력·다중 에이전트 판**이다.
현재 docs 어디에도 이 연결이 안 적혀 있다. **가장 값싼 신뢰도 상승 지점.**

### 2-1. Basic Engagement Zones — Von Moll & Weintraub, *JAIS* 21(10), 2024 (arXiv 2311.06165) ✅

- EZ 의 **형식적 정의**를 세우고 pursuit/turret 모델의 기본 EZ 유도. aspect angle,
  속도·사거리 능력차의 기하.
- **같은 점**: "발사하면 잡을 수 있는가" 를 **상태공간 영역**으로 정의. 우리 θ gate 와
  같은 대상.
- **다른 점**: **1 대 1**, 회피자 관점(피하려고 계산), 지연 없음, 확률 없음.
- **써먹는 법**: `v_shot >= θ` 를 소개할 때 **"EZ 의 measure-valued·협력 확장"** 으로
  정의하면 항공우주 리뷰어에게 즉시 정당화된다. **이 한 줄이 desk-reject 방어에 크다.**

### 2-2. Engagement Zones for a Turn Constrained Pursuer (arXiv 2502.00364) / Probabilistic Weapon Engagement Zones (arXiv 2512.06130, AIAA SciTech 2026) ✅

- 선회율 제한 pursuer 의 EZ 해석해 → 파라미터 불확실성(위치·헤딩·속도·사거리·선회율)
  하에서 **확률적 EZ**. Monte Carlo / 선형화 / 2차근사 / NN 회귀 4종 비교.
- **같은 점**: **확정적 EZ → 확률적 EZ 이행**이 우리 `V_0` → `p_C(z)` prevalence 전환과
  같은 동기. 불확실성 전파법 비교 = 우리 witness 수렴 하네스의 대응물.
- **다른 점**: 여전히 단일 pursuer, 회피자 편, 협력 없음, 임계 θ 개념 없음.
- **써먹는 법**: docs/75 W2 `v_shot` 수렴 하네스 설계 시 **4종 전파법 비교 프로토콜 참고**.
  그리고 "확률적 EZ 는 이미 표준" → `p_C` 의 언어적 정당화 (0-1 SF · 0-6 QbD 와 3중 보강).

### 2-3. Interception-Driven Inverse Reachability for Engagement Zone Construction — Stagg·Peterson·Von Moll·Weintraub (arXiv 2607.03554, 2026-07) ✅

- 관측된 요격 사건들로부터 **pursuer 발사 위치 집합을 역산** → EZ 구성. 확률 확장 +
  희생 에이전트 기반 정보수집 계획.
- **같은 점**: reachability 로 **집합을 산출물로** 내놓고 worst-case 해석을 붙인다.
- **다른 점**: **방향이 반대**(관측→발사원 역추정). 단일 pursuer. 경쟁 관계 아님.
- **써먹는 법**: "EZ 를 reachability 로 구성하는 흐름이 2026 현재 활발" 의 최신성 근거.

### 2-4. Capturability Analysis (PN/TPN/RTPN 계열) ⚠️

- 유도법칙별 **capture region 의 필요조건·충분조건**을 부등식 해석으로 유도. 기동 제한
  표적, 가속도 상한, 허용 miss distance 하의 3D capture region.
- **같은 점**: **"충분조건-but-not-necessary" 를 명시하는 관행**이 우리 lower/upper
  비대칭 규율(docs/74 §3.2)과 정확히 같다. 항공우주 심사자가 이 언어에 익숙하다.
- **다른 점**: 단일 요격체 + 폐형 유도법칙 + 점 포획. 우리는 팀·그물·유한발수.
- **써먹는 법**: §3 의 sound/necessary/sufficient 어휘를 이 관행에 맞추면 "heuristic 을
  certificate 라 부른다" 공격을 미리 막는다. AST/JGCD 투고 시 필수 배경.

---

## Tier 3 — certificate/bound 를 실제로 계산하는 기법 (§4 도구 상자)

| # | 문헌 | 우리 어디에 | 같은 점 | 다른 점 |
|---|---|---|---|---|
| 3-1 | **Viability theory** — Aubin; Aubin·Bayen·Saint-Pierre *Viability Theory: New Directions* ✅ | 용어 전체 (`viability`) | viability kernel = "계속 가능한 상태집합". feasibility envelope 의 정통 어휘 | 무한지평 불변성이 목표. 우리는 **한 순간의 발사조건** → capture basin 쪽에 가깝다. 격자 알고리즘 보증이 유한해상도에선 점근적일 뿐 (우리 AMBIGUOUS 의 이론적 이유) |
| 3-2 | **Scenario approach** — Campi & Garatti (SIAM J. Optim. 2008; sampling-and-discarding 2011) ✅ | W2~W3 `v_shot` 수렴·allocation 민감도 | 유한 표본으로 **비점근적 확률 feasibility 보증**. 표본수 ↔ 위험도 ↔ 압축크기 | 볼록 프로그램 전제. 우리 witness 는 i.i.d. 가 아니라 **설계된 family allocation** → 그대로 적용 불가. **그러나 "2000 위트니스가 무엇을 보증하는가" 에 답할 정공법. 우선 검토.** |
| 3-3 | **Conformal prediction 기반 FRS coverage** (arXiv 2507.22389 등) ⚠️ | witness coverage 의 통계적 보증 대안 | 예측 궤적 집합의 **ground-truth 포함 확률 보정** | 예측기 기반, 적대 최적화 없음 |
| 3-4 | **Submodular max coverage + greedy 1−1/e** (Nemhauser 1978) / **network interdiction** (unreactive Markovian evaders, arXiv 0903.0173) ✅ | W5 greedy↔global audit | blocking 선택이 submodular 면 **greedy 가 (1−1/e) 보증** → "greedy 포화" 주장의 정량 근거 | 우리 목적함수는 **분수형** `G/(G+B)` + not-boxed 제약 → submodular 성립 **미검증**. 성립하면 W5 audit 이 반쯤 공짜, 아니면 MILP 필요. **착수 전 판정** |
| 3-5 | **Active learning / adaptive limit-state sampling** (AK-MCS, EGRA, adaptive boundary sampling) ⚠️ | W12 boundary refinement | "경계에 표본을 몰되 전역 coverage 유지" 의 성숙한 통계 문헌 | 신뢰성공학은 실패확률 추정이 목표, 우리는 **라벨 경계 확정**. `Z_master` 사전봉인이 이쪽 알고리즘 대부분과 충돌 → 차용은 "다음에 어느 master 점" 규칙에만 (0-4·0-10 과 함께 볼 것) |
| 3-6 | **Buckingham-Π / dimensionless transfer** (dimensionless MPC, arXiv 2512.08667) ⚠️ | W1 Π 도출, W10 iso-Π collapse | 무차원군으로 등가류를 묶어 결과를 이전 | 그쪽은 상사가 정확히 성립하는 물리계. 우리 collapse 는 **검증해야 할 가설**(docs/74 §3.9) — 흐리면 안 된다 |
| 3-7 | **HJ / DDE 의 over·under approximation** (arXiv 1812.11718 등) ⚠️ | 상·하한 논증 형식 | sound 양방향 근사의 표준 형식 | 지연미분방정식 대상. 우리 τ 는 **이산 커밋 지연**이라 직접 적용 아님 |

---

## Tier 4 — 방법론·규율 (§2 provenance, §9 Discussion)

| # | 문헌 | 왜 필요한가 |
|---|---|---|
| 4-1 | Henderson et al. 2018 *Deep RL that Matters* / Agarwal et al. 2021 *Deep RL at the Edge of the Statistical Precipice* ✅ | Phase I null 을 **"시드 운" 으로 치부당하지 않기 위한** 통계 규율 근거. 우리 hierarchical bootstrap·시드 8~10·LCB95 는 이 관행을 넘어선다 → 그렇게 주장할 근거 |
| 4-2 | ML/RL 사전등록(preregistration) 논의 ⚠️ | docs/74 §0 pivot manifest + `protocol_hash` 의 학술적 정당화. **"ML 에는 사전등록 관행이 사실상 없다"** 는 지적이 있으므로 우리가 하면 **novelty 로 팔 수 있다** |
| 4-3 | *How Exploration Breaks Cooperation in Shared-Policy MARL* (arXiv 2601.05509) ⚠️ | "협력이 필요한 상태공간을 애초에 방문하지 못한다" — **feasibility 와 learnability 를 분리해야 하는 이유의 학습측 증거.** docs/75 §3 분기 ② 의 직접 근거 |
| 4-4 | *Interpretable Failure Analysis in MARL* (arXiv 2602.08104) ⚠️ | 실패 원인 분해 문헌. 자기기만 감시 1번(docs/73 §6.2)의 반대편 — "certificate 만으론 Phase I 실패 원인이 안 밝혀진다" 를 인용으로 지탱 |
| 4-5 | Safe MARL: shielding (arXiv 2101.11196) / decentralized neural barrier certificates (Qin et al., arXiv 2101.05436) ✅ | **P2 (certificate-guided cooperative control) 의 선행연구.** 지금 논문엔 안 쓰지만 docs/75 §7 의 P2 가 허공이 아님을 보이는 데 필요 |
| 4-6 | ODD / operational design domain, ML 항공제품 ODD 특성화 (AIAA SciTech 2023 등) ⚠️ | docs/75 §8 "context of use" 를 **인증 문헌 표준 용어**로 번역. T-AES 심사자에게 "requirement 아님" 선언이 회피가 아니라 규범 준수로 읽히게 만든다 (0-6 QbD 와 쌍) |
| 4-7 | 우주 debris tethered-net 전개 동역학 (*Acta Astronautica*; *JSR* 모델 검증) / 다중 UAV tethered net 포획 (arXiv 2506.03297) ⚠️ | **τ(전개 지연)·r_kill 의 물리 anchor 후보.** docs/73 §4 desk-reject 대응축 (iv) — "kill radius 와 latency 를 저자가 골랐다" 공격을 막을 **유일한 실물 근거원**. 우주쪽 net 문헌이 검증된 전개시간 모델을 갖고 있다 |
| **4-7a ★ τ anchor 확보 (2026-08-09, docs/77 [B]2)** | Huang, He, Li et al., *Nonlinear Dynamic Modeling of a Tether-net System for Space Debris Capture* (arXiv 2207.14420, 2022) ✅ **원문 PDF 정독 (§3.4 Fig 9·10)** | **검증된 전개시간 수치**: 20 m 급 육각 net (변 L=10 m), 코너질량 6×5 kg 을 20 m/s·θ=45° 사출 시 **spread area 최대 도달 ≈0.75–0.9 s** (θ=60° ≈0.6 s · θ=30° ≈1.2–1.5 s, Fig 9b). DDG 모델, catenary 해석해와 일치 검증 (Fig 7b). → **τ=0.30 s 는 "20 m 급이 0.6–1.5 s" 라는 문헌 상한 + 소형(m 급) net 의 사이즈/속도 스케일 논거로 bracket [O(0.1), 1.5] s 안**. 한계 정직 기재: (i) 우주 무중력·드론 도메인 아님, (ii) Shan·Guo·Gill 2017 (*Acta Astr.* 132:293–302) 의 parameter sweep 은 서지만 확인, 수치 미정독 (paywall) — 인용 시 재확인. C-UAS sense→decide 8–15 s 급 수치는 **바깥 루프** (탐지→교전 개시) 라 τ_deploy 와 다른 량 — 혼용 금지 |

---

## 5. 정리 — 우리가 실제로 서 있는 빈칸 (v2 갱신)

네 문헌군이 **각자 일부씩** 갖고 있고, 넷의 교집합이 비어 있다.

```
(A) certified feasibility set 계열              [Tier 0-2,0-3,0-5,0-8]
    : inner/outer bracket + indeterminate + refinement     ✅ 있음
    : 적대적 상대 없음, 팀 크기 필요성 없음

(A') OR/PSE feasibility·flexibility 계열         [Tier 0-1,0-4,0-6,0-9,0-10]  ← v2 추가
    : feasibility test / flexibility index / **stochastic flexibility = 확률적 feasibility**
    : black-box 잡음 시뮬레이터용 surrogate 절차 · 통계적 판정 · 정지규칙   ✅ 있음
    : **적대자 없음** (inner 문제가 자유로운 recourse), **하한이 constructive 일 필요 없음**,
      팀 크기 필요성 없음

(B) 협력 요격 / reach-avoid 게임 계열            [Tier 1]
    : 팀 크기·협력 필요성  ✅ 있음 (닫힌형, 단순 기하)
    : 불가능(upper) certificate 를 안 만든다, 전개지연·유한 1발 없음

(C) engagement zone / capturability 계열         [Tier 2]
    : 발사조건을 상태공간 영역으로  ✅ 있음
    : 1 대 1, 회피자 관점, 협력 없음
```

**우리 = A' 의 개념틀 × A 의 bracket 계산 구조 × B 의 협력 필요성 질문 × C 의 발사조건**,
여기에 **deployment latency τ 와 single-shot 제약**. 이 조합의 선행연구는 조사 범위에서
**발견되지 않았다.** (⚠️ negative 진술 — Tier 0 원문 정독 후 재확인 필요.)

한 문장으로:
> *공정 flexibility 문헌은 상대가 없는 설계 문제에서 "제약을 만족할 확률" 을 계산하고,
> 협력 요격 문헌은 성능을 비교하며, engagement-zone 문헌은 1 대 1 이다.
> 어떤 문헌도 **"협력 요격 메커니즘이 필요한 파라미터 영역이 존재하는가" 를 상·하한
> certificate 로 묻지 않았다.***

**v2 의 태도 변화**: v1 은 "우리가 새 프레임을 만들었다" 에 가까웠다. v2 는 **"확립된
feasibility analysis 를 적대적·유한발수·다중에이전트 요격 문제로 이식하고, 그 과정에서
constructive 하한과 팀 크기 필요성 certificate 를 추가한다"** 가 정확한 자기서술이다.
**후자가 훨씬 강하고 훨씬 방어하기 쉽다.**

## 6. 즉시 할 일 (v2 우선순위)

1. **★ Tier 0-1 (Grossmann flexibility 계열) 원문 정독 3편**: Halemane & Grossmann 1983 ·
   Straub & Grossmann 1990 (stochastic flexibility) · Wang & Ierapetritou 2018.
   → **§3 Feasibility formulation 을 이 어휘로 다시 쓴다.** `p_C(z)` 를 `SF` 인용과 함께
   도입. 착수 전 완료. **이번 조사에서 ROI 가 가장 큰 항목.**
2. **★ W12 종료조건 부재를 메운다 (실제 프로토콜 gap)** — 0-4 (ε,δ)-accurate LSE +
   0-10 (automatic stopping) 을 참고해 **boundary refinement 정지규칙을 docs/74 §3.8 에
   결정론적으로 추가**. 지금은 "얼마나 갈아야 충분한가" 가 결과를 보고 정해지는 자유도로
   남아 있어 §7 금지사항 위반 소지가 있다. **셀 생성 전에 봉인해야 한다.**
3. **Tier 0-2 (SIVIA) · 0-3 (sound HJ bounds) · 0-5 (Zimmermann) 정독** → §4
   Certification algorithms 위치잡기.
4. **Tier 1-4 (Gavin & Bronz, arXiv 2607.05939) 원문 정독.** 팀 크기·net 전개 모델·보고
   지표를 확인하고 gap statement 를 **그 논문을 직접 지목해** 확정. 동시기 최근접이므로
   잘못 요약하면 심사에서 치명적.
5. **용어 정렬 1회 (0-9)**: `U^rel < θ` 를 **"infeasibility certificate (via optimistic
   relaxation)"** 로 못박고 robust counterpart 와의 혼동을 명시적으로 차단.
6. **Tier 2-1 (Basic Engagement Zones) 를 docs/74 §3.2 에 배선.** `g_θ` 정의 옆에
   "EZ 의 measure-valued 협력 확장" 한 줄 → 서지 1개로 desk-reject 방어선 (i) 강화.
7. **Tier 3-4 submodularity 판정** — `v = G/(G+B)` + not-boxed 에서 blocking center 선택이
   submodular 인가. 성립 시 W5 greedy↔global audit 비용 급감. **W4/W5 착수 전.**
8. **Tier 0-10 (Batur & Kim) 로 표본정책 근거 강화** — docs/74 §3.10 의 20~30 / 60~100+ 를
   "요구 판정신뢰도에서 유도된 값" 으로 승격할 수 있는지 검토. (불가하면 현행 유지 +
   근거를 정직하게 "관행" 이라고 쓸 것.)
9. **Tier 3-2 (scenario approach) 적용 가능성 판정** — witness 표본이 무엇을 보증하는지에
   답할 정공법. 비적용이면 **왜 비적용인지**를 논문에 쓴다(docs/73 §5-1).
10. ~~**Tier 4-7 (net 전개 동역학) 에서 τ anchor 1 개 확보 시도.**~~ ✅ **완료
    (2026-08-09, docs/77 [B]2 로 우선순위 2 승격 후 이행)** — Tier 4-7a 참조.
    τ=0.30 s 가 문헌 bracket [O(0.1), 1.5] s 안. `chi` 축이 "저자가 고른 값" →
    "문헌 bracket 내 값" 으로 승격. desk-reject 문장(docs/73 §4)의 (iv) 축 부분 방어.

## 7. 조사의 한계 (정직 기재)

- 전부 **웹 검색 스니펫 + 초록 수준**이다. ✅ 는 서지 확인일 뿐 **본문 정독이 아니다.**
  ❓ 는 권/호/페이지가 기억 기반이므로 **인용 전 반드시 서지 재확인.**
- "선행연구 없음"(§5)은 **검색축 5개 · 총 10 라운드 범위 안에서의 부재**다. 특히
  방산 회색문헌(AFRL/ADD 기술보고서), 한국어 문헌, 2026 하반기 미공개 preprint 는
  조사 범위 밖.
- **v1 에서 미조사로 남겼던 OR/PSE 축(robust feasibility · feasible region DoE)은
  v2 에서 조사 완료** — 그리고 그것이 조사 전체에서 가장 큰 수확이었다. 이는
  **"검색축을 하나 빠뜨리면 가장 가까운 선행연구를 통째로 놓친다"** 는 증거이므로,
  아래 남은 축도 언젠가 열어야 한다.
- **남은 미조사 축**: (i) semi-infinite programming 의 feasible parameter set 세부,
  (ii) EDA/회로 yield·design centering 원문 계보, (iii) 군사 OR 의 weapon-target
  effectiveness / measure of effectiveness 문헌, (iv) 신뢰성공학 stress-strength
  interference, (v) 경제학·게임이론의 implementability/feasibility 개념.
  (i)~(iii) 이 다음 우선순위.
