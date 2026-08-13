# 82 — 연구 계보·산출물·명제 종합 브리핑 (교수님/조교님 미팅용)

- **일자**: 2026-08-13 · HEAD 43acc39 · 용도: **논문 내용 합의 + 향후 계획 상담**
- **작성 방식**: 코드 전수감사(`artifacts/audits/environment_numeric_audit_2026-08-13.md`)에 이은 **산출물 감사** — docs 00→81 전체 + claim registry 30건 + 게이트 판정 전수 재구성.
- 이 문서는 요약본. 모든 주장의 정본은 각 표의 근거 열에 있는 문서.

---

## 0. 한 페이지 요약

**연구 질문 (처음부터 불변)**: 이종 다중 드론(저가 kamikaze limiter ×4 + 비파괴 그물 finisher ×1)이 협력 성형(shaping)으로 공격 드론을 **포획 가능한 상태로 유도**할 수 있는가.

**바뀐 것은 질문이 아니라 증거 형식** — 3번 진화:

```
① probe (N1: 기하 포획집합이 net 물리 하에서 실패하는 regime 실증)
② 학습 이득 증명 (MARL이 baseline을 넘는가) ← 3회 시도 모두 null
③ feasibility certificate map (협력이 성립하는 조건의 지도) ← 현재 spine
```

**현재 spine (2026-08-13 개정, docs/83)**:

> We characterize when **physical interception remains possible while delayed single-shot non-destructive capture has already collapsed**, and identify **deployment latency and residual aiming geometry** as the two principal terminal constraints observed in the tested configuration.

국문: 물리적 요격은 여전히 가능한데 지연을 갖는 단발 비파괴 포획은 이미 붕괴하는 영역을 규명하고, 그 두 종말 제약으로 전개 지연과 잔여 조준 기하를 제시한다. (구 spine "τ_deploy × 겨냥 각속도"는 §3(b) 정정으로 폐기 — ω_max는 원인이 아니었다.)

**오늘 기준 확정된 4대 결과**:
1. **운동학 경계** a\* = 2ρ/τ² = 39.3 m/s² — **낙관적 해석 외곽 경계**. 경계 위 포획 0/1,635(T0) · 0/1,598(T1) [실측] ★단 E1c(docs/83 §14): a≥32.2에서 **발사 자체가 0/350**이므로 이 zero들은 게이트 기권이며 **post-commit 실패의 독립 실증이 아니다**(censored)
2. **겨냥 경계가 먼저 온다** — 잔여 조준 오차 ψ=4.26°로 예측 25.8 vs 실측 교차 22.45, "consistent with" [실측]. ★단 **그 ψ의 원인은 미해결** — slew cap은 반사실로 배제됨 (docs/83)
3. **modality gap** — a≥39.3에서 net 포획 0/1,598인데 **물리 요격은 24.3%** 유지 [실측, 재분석]
4. **종말 봉쇄 불가 (①-B1)** — commit 후 0.30 s 창 내에서 limiter 4기로도 봉쇄 불가, ΔU≡0 / 600상태 [**인증** — 정수 산술 certificate]

⇒ 논리 귀결 둘: **(i) 요격 능력과 비파괴 포획 능력은 같지 않다** (3의 gap이 논문의 문제). **(ii) 유효한 협력은 commit 이전에 작동해야 한다** (4로부터) — 이것이 B2 이후의 연구 프로그램.

**★ 용어 규율 (docs/83 §23)**: `set inclusion`이 아니라 **modality separation / modality gap**. Level 1(성공곡선 regime 의존성 상이) 확립 · Level 2(net 붕괴 구간에서 물리 요격 존속) 강하게 지지 · **Level 3(동일 commit state에서 `z ∉ C_net ∧ z ∈ C_physical`) 미확립**. `C_net ⊊ C_physical`을 state-wise 명제로 쓰지 않는다. E3에서 CAPTURED 40건은 oracle 도달 가능 limiter가 0/4, 침투는 4/4 — **부분적으로 상보적인 operating regions**에 가깝다.

**★ 신규 (E4-1, docs/83 §21)**: 같은 물리·attacker·ring·PIP family에서 **timing target만** 바꿔 하드킬 0.190 → 0.253 (paired +0.063, CI [+0.017, +0.110]). ⇒ *"registered physical capability만으로 19%가 고정되는 것은 아니다."* 단 **기전 미확립** — 사전등록 mechanism endpoint가 양자화로 gate 미충족.

**현재 위치**: T1 반응형 재실행 완료·Case B 판정(경계 유지, attainability 0.83→0.76) → **KSAS 2p 동결 직전(P1)**. 수치 전수감사 통과(PASS with scope caveats, FATAL 0건).

**오늘 미팅에서 합의 요청 3건** (상세 §5): ① KSAS Case B 스파인 + 잔여 4건 처리로 제출 동결 ② arXiv 10월 초중 일정 + θ-sensitivity 처리 방식 ③ B2 진입 조건(공격자 관측 모델 선택 + MARL kill criterion).

---

## 1. 연구 계보 — 7단계 피봇 연대기

| 단계 | 기간 | 내용 | 트리거 | 다음으로 승계된 것 |
|---|---|---|---|---|
| **0. pre-newURP** | ~06-24 | 구 URP "Dynamic Capture Viability Shaping" + N1 probe (Huh 2026 기하 포획집합 C_0가 net 물리 하에서 조용히 실패하는 regime 실증) + WarSim SE3 | — | net 물리 앵커(τ_deploy·ρ, Xu 2025), "포획집합의 성립 조건"이라는 질문 자체 |
| **1. 방향전환** | 06-24~26 | headline 교체: capturability 제조 → **교환-경제 lever로서의 협력 shaping**. 게임 정식화 S1~S8 비준·동결 (v_shot 정의 포함) | novelty 적대 감사 (EN 5각도 + 경제학 3각도) | env 계약·v_shot·S1~S8 전부 현재까지 유효 |
| **2. M2 빌드 + L2 MARL** | 06-말~07-09 | shepherd env 구현 + MAPPO/COMA 직접 구현. **L2 게이트 PASS** (baseline 대비 paired margin +10~+16) | BUILD-first 선언 (docs/04) | env·MARL 스택. 남은 벽 = clean 포획 0회 |
| **3. M3/A-캠페인** | 07-07~18 | capture-unlock 공략 사다리 (커리큘럼→후진→합성 전임자). **전부 FAIL** (M3a 본선, bank v2 k≥2) | M3a FAIL | "말단 발사는 학습됨, 진입이 안 됨" 진단 → 다음 피봇의 증거 |
| **4. 독트린 피봇** | 07-19 | **hybrid 아키텍처 비준**: MARL은 협력 성형만, 종말 발사는 규칙 기반 가드. learned-fire 계열 중단 — 그 실패가 hybrid 선택의 근거 | A-캠페인 누적 null | 현행 아키텍처. M3b(교환 frontier)는 park |
| **5. M4 + 앵커링** | 07-27~08-03 | 비손실 격추 스파인, 모드 시스템(연속 제어 + 비가역 방아쇠), **파라미터 앵커 대공세** (Xu·Pliska, 62개 전수) — 게이트가 학습 **전에** 깨진 전제 3개 적발 | 논문-우선 원칙 | 현행 운용점 (τ=0.30, ρ=1.77, ω=2.0) |
| **6. 부정 결과 누적 + 2대 발견** | 08-04~08 | 역할분리 2×2: **학습(LL 0.072)이 무개입(SS 0.182)을 못 넘음**, 원인=조준(BC 매개 확인). ★**스케일 결함 발견**(legacy 스폰 21~25 m는 비준된 적 없는 세습 → v2 300 m 재스코프) ★**위협 v3**(기존 A2에선 limiter의 인과효과가 0이었음을 실증 → angular-gap 반응 채널 개통, P94 GREEN) | 궤적 뷰어 육안 검사 | 현행 v2/v3 계약. 기존 결과는 "legacy regime"으로 재스코프(폐기 아님) |
| **7. Phase III (현행)** | 08-09~ | **spine 교체**: 학습 이득 증명 → **feasibility certificate map**. 계약 봉인(지도 셀 0개 상태에서), 게이트 시리즈 가동. MARL은 폐기 아닌 **후순위** (COOP 셀 실재 시에만) | 리뷰 10~15 심사 (조건부 승인) | 현재 |

**계보의 요점 (교수님께 한 문단)**: MARL null 3회는 실패담이 아니라 **탐침**이었다 — ① 학습이 못 넘는 이유가 조준 축임을 특정했고(②의 겨냥 경계 발견으로 이어짐), ② limiter가 공격자에 인과효과 0인 위협 모델로는 shepherding이 애초에 검정 불가능함을 적발했으며(위협 v3), ③ "협력이 이득인가"를 묻기 전에 "협력이 성립하는 영역이 존재하는가"를 물어야 함을 강제했다(Phase III). 질문의 격이 한 단계 내려간 게 아니라, **증거의 격이 세 단계 올라갔다** (probe → 실측 → certificate).

### 게이트 현황판 (Phase III 과학 게이트)

| 게이트 | 질문 | 판정 |
|---|---|---|
| 1 | Π-격자 선봉인 (8,415점, hash 고정) | ✅ |
| 2·3 | v_shot 측정 수렴 + 할당 민감도 | ✅ PASS |
| 6 | unblockable bad-mass 싼 상한 | ✅ (117/123 셀 상한 0) |
| 7 | 종말 봉쇄 상한 U^rel | r1 실패 보존 → r2 수리 → **PASS = ①-B1 인증** |
| 9 | 독립 judge 교차검증 | ✅ (30.8만 witness 불일치 0) |
| 10 | 무차원 상사성 (iso-Π) | L-상사 bit-exact PASS · T-상사 실패 보존 → 원인 특정 |
| 11 | 숨은 시간상수(k_f) 승격 무결성 | ✅ PASS (S-T 6/6 exact) |

실패를 지운 게이트가 하나도 없음 — r1 실패는 전부 보존 후 수리 기록. 이것이 이 repo의 방법론적 정체성.

---

## 2. 산출물 지도 (evidence 등급별)

| 등급 | 산출물 | 규모 |
|---|---|---|
| **CERTIFIED** (정수/구간 산술, 반증 탐색 통과) | Gate 7 ①-B1 (ΔU≡0, 600상태, 20셀 전역) · Gate 6 상한 · Gate 9 judge 일치 · Gate 10/11 상사성 | results/phase3/\*, protocol_hash 스탬프 |
| **MEASURED** (n≥1,000 실측) | T0 곡선 n=2,700 · **T1 곡선 n=2,700 ×2모드 (Case B)** · 경계 위 0/1,635·0/1,598 · 역할분리 2×2 (n=300×4) · IID paired 평가 | results/curve_\*, m4_roles |
| **PILOT** (n<100, 방향성) | P94 route 채널 (n=50 paired, 46/50 발산) · coarse pilot 40셀×20ep (χ 경계 0.8↔1.2) · pre-fire 목격자 1/7 | results/threat_v3_p94 등 |
| **ANALYTIC** (유도) | 명제 N (χ>1 필요조건, 1D 스케치 — **미비준 draft**) · a\*(ψ) 겨냥 경계식 · sandwich L≤V≤U | docs/10, 45, 74 |
| **DECLARED** (선언·사전등록) | 운용점 8건 · 위협 v3 분포 · TRAIN 분포 동결 · scripted baseline 동결 · adversary ladder T0~T4 | docs/40, 60, 61, 63, 80 |
| **감사 산출물** | claim-evidence(30건) · dead-code(104행) · reward 의존성 · RESET 종합 · **환경 수치 전수감사(08-13)** | artifacts/audits/ ×5 |
| **RETRACTED** (철회 보존) | "하드킬 도피" · "shaping 구조적 무력" · "0.033 오차 상계" (3건, 전부 철회 기록 보존) | claim registry |

claim registry 총계: **ACTIVE 19 · DOWNGRADED 5 · RETRACTED 3 · PENDING 2** (+gap 5 중 3 해소).

---

## 3. 명제 분석 — headline 8건의 증거 사다리와 허용 표현

| # | 명제 | 증거 강도 | 허용 최대 표현 (등록済 상한) | 미결 리스크 |
|---|---|---|---|---|
| (a) | **χ>1 운동학 불성립** (a≥39.3 → 포획 불가) | ANALYTIC + **CENSORED MEASURED** | "analytic outer bound 위에서 포획이 관측되지 않았다. **단 게이트가 그 구간에서 발사하지 않았으므로 post-commit 실패의 독립 검정이 아니다**" | ★E1c: a≥32.2 발사 0/350 → 기존 "0/1598이 경계를 실측 검증" 서술은 **금지**(registry C032). 명제 N은 스케치·미비준; τ 하한·ρ 상한이 같은 방향으로 경계 이동 |
| (a′) | **실질 전이의 기전** (22–32 붕괴) | **EXPLORATORY diagnostic** | "**진단 분해**: 표적 기동성이 커질수록 발사 자격이 붕괴하고, 발사된 shot 중 조건부 포획 성공률도 동시에 하락한다(경우 ③). 실현된 발사 기하가 공칭 최대-footprint 기하보다 상당히 좁으나, **그 인과적 역할은 아직 exploratory**" | ax≈6.4(공칭 8.22)·slack 1.103 → 2·slack/τ²=24.5 vs 관측 22.4–22.9. 기하가 발사 조건부라 순환성 있음. 확인엔 E1d(forced-commit) 필요 |
| (b) | **겨냥 경계가 운동학 경계보다 먼저** | MEASURED (기전 귀속은 **DOWNGRADED**) | "residual aiming error가 더 이른 실질 경계와 결부된다" + 편차 **12.4%** 병기. **"finite slew binds first" 금지** | ★ ψ의 원인 미해결. ω=∞ paired 반사실이 0/500 flip → slew cap은 원인 아님 (docs/83, registry C031). 남은 후보 = 예측 오차 / 발사거리 기하 |
| (b′) | **modality gap** — regime 수준 (Level 1·2 확립 / **Level 3 미확립**) | MEASURED (**E2-B로 확정**) | "동일 commit 응답을 유지한 채 net을 경쟁 종말사건에서 제거해도 물리 요격 발생률은 불변" — 두 modality의 유능 구간이 **부분 상보적**(저-a는 net 0.717, 고-a는 HK 0.243) | ★E2-B: Δ_comp = **정확히 0** (n01=n10=0, 426건 중 전환 0). ~~"24.3%는 경쟁위험 때문에 하한"~~ **반증됨** — censoring 없음, 보정 불필요 |
| (c) | **3-구간 구조** (baseline-achievable / aiming-limited / kinematically-infeasible) | MEASURED (T0+T1 각 n=2,700) | 구간명 위 3종만 ("성립/EASY" 금지) | Case B로 생존 확인済 (0.763 / 0.016 / 0) |
| (d) | **종말 봉쇄 불가 ①-B1** | **CERTIFIED** | "registered fixed-state static-blockade 모델·0.30 s 창·검정 상태분포 내에서, limiter 4기로도 회복 불가" — 한정어 3종 필수 | 없음 (가장 강한 사슬). "협력 불가 일반화" 금지 |
| (e) | **pre-commit shaping 필요성** | DECLARED + PILOT 목격자 1건 | "①-B1이 pre-commit 개입을 **동기화**한다" (필요성 '증명' 아님) | ①-B2 미확정 — B2 실험이 바로 이것 |
| (f) | **route 채널 인과 실존** (P94) | PILOT (n=50) | "채널이 존재하고 측정 가능" — 학습이 이를 **쓰는지는** 미검정 | MARL 재개의 전제이지 근거 아님 |
| (g) | **반응형 T1이 경계를 파괴하지 않음** | MEASURED — **Case B 봉인** (08-13) | "reactive avoidance reduced baseline attainability (0.83→0.76) while the boundary remained approximately stable" — "반응성 무관/결정적" 양쪽 금지 | T1 = 단일 구성(0.5, 30 m)이지 family 아님; Phase III 스케일에선 terminal-only reactive |
| (i) | **all-chase가 pathwise 요격 기회를 못 쓴다** (E3) | MEASURED (hindsight oracle) | "There is substantial unused pathwise interception opportunity, but the baseline concentrates those opportunities into a single temporal layer." | P(oracle≤0.75)=0.883 vs 실측 0.043 · E[가능 limiter]=2.84/4 · range(t_min) 0.125 s(93.7%가 0.3 s 내). **금지**: "causal policy가 성공한다"/"학습이 필요"/"capability 부족" — realized path 한정 |
| (j) | **timing만 바꿔도 하드킬이 오른다** (E4-1) | outcome MEASURED / **기전 UNRESOLVED** | "registered physical capability만으로 19%가 고정되는 것은 아니다" — 0.190→0.253 (paired +0.063, CI [+0.017,+0.110]) | 동결 mechanism endpoint가 양자화로 gate 미충족(자기신고). Δ=0.25는 clamp 98%라 격리. **금지**: "S2"/"temporal staggering 성공"/dose-response |
| (h) | **MARL null** (LL 0/300 등) | MEASURED (등록된 해석 동결) | "사전등록 우월성 주장을 지지하지 않았다"; Phase III는 이 null의 "mechanism-consistent explanation" — **원인 증명 아님** | 학습이 hold를 못 넘은 원인은 조준 축으로 특정(C003)·BC로 매개 확인(C004) |

### 핵심 명제 원문 요지 (미팅 참조용)

- **명제 N** (docs/10, draft): w = ½aτ² > ρ (즉 χ>1)이면 게이트를 어떻게 놓아도 무-shaping 방어 가치 = 0 — "실패는 게이트가 아니라 구조". 2-limiter lobe-마스킹이 clean 포획 강제. **비준 대기 항목**: A3 bang-bang 가정, A4 escort/corridor 변형 선택, 논문 배치(본문 명제 vs 부록).
- **겨냥 경계** (docs/45): a\*(ψ) = 2d(tanθ−ψ)/τ². lead 조준은 공짜가 아니라 slew-제한 행동이라는 재해석이 출발점.
- **Gate 7 ①-B1** (docs/79 r2): 정확 문구 — *"Within the registered fixed-state static-blockade model, up to four path-limiters cannot recover net-capture feasibility in the high-chi regime over the tested attacker-induced state distribution."*

### 대표 금지/허용 표현 (전체 표는 claim audit §10-11)

| 금지 | 허용 |
|---|---|
| "협력이 불가능" | "정적 봉쇄 **채널로는** 국소 발사조건 확립 불가" (+LOCAL, +상태분포 한정) |
| "χ가 지배 파라미터" | "지배 좌표 중 하나" |
| "두 독립 계측 일치로 검증" | "consistent with" + 12.4% 병기 |
| "반응성은 영향 없다" | "검정한 angular-gap 반응 모드는 이 구성에서 경계를 유의하게 이동시키지 않았다" |
| "반응형 위협 **family**" | "angular-gap reactive **configuration** (단일점)" |
| "null의 원인이 증명됨" | "mechanism-consistent explanation" |

---

## 4. 논문 라인 현황

### KSAS 2026 추계 2p — **실험 완료, 본문 정정 대기** (P1)
- **스파인 (개정)**: modality gap — 요격 가능 ≠ 비파괴 포획 가능. **T1까지만** (ladder 규율).
- **T1 재실행 Case B**: T1 primary lineage, T0는 mechanism-isolation. attainability 0.763 / crossing 22.45 / ψ 불변 / 경계 위 0.
- **수치 전수감사: PASS WITH SCOPE CAVEATS** (FATAL 0).
- **08-13 실험 6건 완료** (전부 사전등록·봉인): E1(INCONCLUSIVE) · E1b(분기 B) · E1c(경우 ③) · E2-B(Δ_comp=0) · 리드타임(가설 기각) · E3(controller-limited) · E4-1(outcome POSITIVE/기전 UNRESOLVED).

**제출 전 남은 것 — 이것만 하면 freeze**

| # | 항목 | 성격 |
|---|---|---|
| 1 | **78 m/s² 출처** 확정 or "declared upper threat bracket" 격하 | 서지 (교수님 확인 요청) |
| 2 | legacy↔rerun 계약 차이 caveat 1문장 | 기록 |
| 3 | pooled 분모 재확인 (1,635 / 518 / 904) | 기록 |
| 4 | stale docstring 2건 (a\*=44.4→39.3, 24.06→22.45) | 기록 |
| **5** | **★ 본문 정정 6곳** (오늘 발생) | 아래 |

**본문 정정 6곳** (docs/83 근거):
1. spine 문장 → modality gap (§12A·§23)
2. *"finite slew binds first"* **삭제** — ω=∞ 반사실 0/500 flip (§2, C031)
3. *"0/1598이 경계를 실측 검증"* → **censoring 문구** (§14.2, C032)
4. **ψ lineage caveat** — 4.26°는 no-fire audit world 값, 곡선과 lineage 다름 (§12A.3)
5. modality gap을 **Level 1/2/3**로 표기, `C_net ⊊ C_physical` state-wise 서술 금지 (§23, C036)
6. 3구간 이름 = baseline-achievable / aiming-limited / kinematically-infeasible

Gate 7은 본문 제외, Discussion 1문장만.

### arXiv v0 — 10월 초중 목표 (가속 결정 08-11)
- 3부 구성: **I** feasibility (τ·χ·T1 실측·aiming·다좌표 caveat) / **II** why terminal cooperation is too late (Gate 7) / **III** ⇒ 협력은 commit 전에 작동해야 한다. **B2 결과를 기다리지 않음** — v0의 역할은 "왜 B2인가"까지.
- 선결 debt (감사 지정): θ=0.9 sensitivity(offline relabel, 저비용) · jink 상수 등록 · 파생 항등식 assert · grid 정합.

### 중장기 (AIAA → journal)
- AIAA 최소 패키지: 지도 + T1 검증 + Gate 7 + **B2 scripted 성형 존재증명** + T2 robustness + MARL vs scripted.
- Journal: T3(MPC)/T4(self-play) + defender×T0..T4 matrix — "mechanism이 어느 sophistication까지 유지되는가".
- MARL 재개 조건: B2 scripted에서 commit-state 분포의 유리한 이동이 실재할 때만. **없으면 물리/제어 논문으로 종결** (stop rule).

---

## 5. 미팅 합의 요청 항목 (우선순위순)

### A. KSAS (최우선 — 8/15 이후 바로 제출 준비)
0. **★ spine 교체 + 인과 정정 3건 승인 (최우선)** — 오늘 실험 6건이 **인과 주장 4개를 내렸습니다.** ㉠ *"유한 조준 각속도가 먼저 구속"* 철회 (ω=∞ 반사실 0/500 flip) ㉡ *"0/1598이 경계를 실측 검증"* → censoring (a≥32.2 발사 0/350) ㉢ *"짧은 교전이 하드킬을 억제"* 기각 (리드타임 2배에도 HK 평평). 그 대신 spine을 **modality gap**으로 올림. **본문 §2.2–2.3 상당 부분 재작성이 필요합니다** (정정 6곳, §4 참조).
1. **Case B 스파인 승인** — T1 primary·T0 강등, attainability 0.763, 겨냥 headline은 *"consistent with"* + 편차 **12.4%** 병기. T0의 더 좋은 숫자로 회귀하지 않는 규율 확인.
2. **78 m/s² 상한 출처** — 5-inch FPV급 가속 상한의 citable 문헌을 아시는지. **인쇄 숫자 중 유일하게 무인용**입니다. 없으면 *"declared upper threat bracket"* 으로 격하해서 인쇄.
3. **저자·순서·과제 표기 + 마감 확인** (8/29 가정) — docs/72의 "교수님 상의" 플래그 그대로.
4. **modality gap을 어느 level로 인쇄할지** — Level 1·2는 확립, **Level 3(state-wise `C_net ⊊ C_physical`)는 미확립**. 본문에서 포함관계로 쓰지 않고 *"modality separation"* 으로 쓰는 데 동의하시는지.

### B. arXiv (방향 합의)
4. **일정**: 10월 초중 가속안 유지 여부. KSAS 동결 → repo 정리(R1~R3) → arXiv 순서(docs/81) 승인.
5. **θ=0.9 처리**: 4중 역할(발사 게이트/라벨/Gate 7/θ_S2) + M2 시절 보정. 제안 = 기존 상태 offline relabel로 θ∈{0.85, 0.90, 0.95} sensitivity → 안정 시 0.9 유지 + 부록. (결과 보고 재선택은 하지 않음.)
6. **jink 상수(0.6, 1.5 Hz)**: sensitivity 축으로 올릴지, nominal-fixed scope로 명시할지.

### C. B2 / 향후 프로그램 (설계 상담)
7. **공격자 commit 관측 모델 3택**: ① 전역 즉시 감지(현행) ② 센싱 게이트 ③ 지연/노이즈 — "무엇이 현실적인가"가 아니라 "어떤 모델을 시험하는가"의 선택. T_lead 효과와 직접 합성되므로 실험 전 결정 필요.
8. **MARL kill criterion 승인**: B2 scripted (H0/P/R/PR factorial, endpoint = commit-상태 분포 이동)에서 이동 부재 시 MARL 중단·물리/제어 논문으로 종결 — 이 stop rule을 사전 승인받고 싶음.
9. **T1의 시간적 한계를 설계 변수로**: Phase III 스케일에서 T1은 terminal-only reactive (sense 15~45 m ≪ 접근 250~350 m). B2에서 sense_range를 명시 축으로 + T_lead를 T_pre/T_react로 분해하는 설계에 대한 의견.
10. **명제 N 비준**: A3/A4 가정 선택과 논문 내 배치 (본문 명제 vs 부록 스케치) — 07-03부터 open.

---

## 6. 리스크 정직 신고 (미팅에서 먼저 말할 것)

0. **★ 08-01 인과 주장을 08-13에 스스로 철회함** — "겨냥 각속도가 먼저 구속한다"는 docs/45의 결론을, 같은 repo가 08-05에 이미 갖고 있던 반사실(ω=∞에서 0/500 flip)로 반증. 두 문서가 8일간 연결되지 않았던 것이 실책이고, 산출물 감사에서 잡혔습니다. 원문은 보존하고 DOWNGRADE를 얹었습니다 (docs/45 상단, registry C031).
1. **MARL 성과는 아직 null** — 학습이 hold 기준선을 넘은 적 없음 (LL 0/300). 현재 논문 라인은 이 null을 전제로 설계됨 (feasibility-first). "MARL 논문"이 아니라 "협력 성립 조건 논문"임을 명확히.
2. **T1은 단일 구성점** — 반응형 위협 "일반"에 대한 주장 불가. T2~T4는 미구현.
3. **명제 N은 미비준 스케치** — 인쇄 시 명제 격이 아니라 유도 스케치 격.
4. **θ=0.9·jink 상수의 sensitivity 미시험** — arXiv 전 해소 예정 (계획 있음).
5. **기존 legacy 결과는 재스코프됨** — 스케일 결함 발견(08-07)으로 "legacy small-scale regime" 한정. 발견 경위(궤적 육안 검사)와 재스코프 규율 자체가 방법론적 자산.

---

## 부록 A. 용어 해설 (10개만 — 전체는 계보 조사 원문)

| 용어 | 뜻 |
|---|---|
| limiter / finisher | 저가 자폭 성형 드론 ×4 / 비파괴 그물 발사 드론 ×1 (탄수 1, 비가역) |
| v_shot | per-shot 포획가치: 공격자(t+τ)가 net 전개 볼륨에 들 확률 대용량 — 발사 게이트·certificate 공통 측정량 |
| χ, κ, μ | a·τ²/(2ρ) 회피변위/net반경 · r_kill/ρ · 가속비 — 지도 core 3축 |
| τ_deploy = 0.30 s | 발사 결정~net 유효까지 (0.15 비행 + 0.10 감지 + 0.05 판단; 문헌 앵커, 하한 선언) |
| ρ = 1.77 m | 유효 net 반경 (Xu 2025 등가면적 × 내접비, 낙관 상한 선언) |
| FREE/SINGLE/COOP/INF/AMB | 셀 certificate 5-라벨 (무개입 성공 / 1기 필요 / 협력 필요 / N기로도 불가 / 미해결) |
| T0~T4 | 위협 사다리: 무반응 / 국소반응(현행 KSAS) / 연속반응 / MPC / 학습 — 정보구조 순서, 난이도 단조 아님 |
| ①-B1 / ①-B2 | 종말 봉쇄 불가(인증됨) / pre-commit 성형 불가(미확정 — B2가 검정) |
| B2, T_lead | 다음 게임 모델 개정: commit 전 성형 리드타임을 명시 변수로 |
| Gate N | 과학적 kill/branch 게이트 (시간 게이트 아님) — 실패는 보존 후 수리 |

## 부록 B. 정본 문서 포인터

계보 = docs/00·01·22·59·73~75 · 정식화 = docs/03·10·74 · 위협 = docs/60·61·80 · 게이트 = docs/75·77·78·79 · KSAS = docs/72(ksas)·45·42 · 감사 = artifacts/audits/ ×5 · 향후 순서 = docs/81.
