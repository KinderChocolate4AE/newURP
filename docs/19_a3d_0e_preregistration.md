# 19 — A-3d Phase 0-e 사전등록 패키지 (v0.3, 2026-07-17 — **동결본**; 3자 검토 회신 반영·Hyunjun 비준 완료)

> **상태**: v0.2가 3자 검토를 받아 **조건부 승인**("수정 반영 후 bank v2 생성 승인", 접수본 = `URP/a3d_0e_external_review_2026-07-17.md`)을 얻었고, 체크리스트 15항 전부 + 잔여 자유도 11건을 본 v0.3에 반영했다(반영 대조표 = §12). Hyunjun 비준 2건: stage exit = 점추정 히스테리시스형(§7), 나머지 14항 = 리뷰어 권장안 일괄 수용. **본 커밋이 0-e 동결 커밋이다** — 이후 여기 적힌 수치·규칙·seed는 bank v2 생성/검증/학습 결과를 보고 변경하지 않는다.
>
> **불변 규율**: 판정 J·게이트 정의·평가 경로 동결 / 신규 개입 = 학습 스캐폴드 전용 / **재생성 1회 원칙**(admissibility 미달을 문턱·생성식 반복 조정으로 구제 금지 — 귀하의 2026-07-16 리뷰 문구 준수) / sealed 불가침 / P0 학습 금지 / 하드 스톱·트립와이어 2026-08-31 불변.

## 0. 확정 결정 요약

신규 결정 **[D-1]~[D-5] 5건**(그 외는 docs/18 v0.2 RATIFIED 사양의 수치 대입) — 3자 판정과 최종형: **[D-1]** 수정 승인 → 8멤버 유지 + attpd 완전 수식 동결(§4) + 경고 명칭 교정 / **[D-2]** 수정 승인 → **lexicographic first-fit**(target 12 우선 → min 8 fallback) + 생성 대역 420–439 교체(§5) / **[D-3]** 중요 수정 후 승인 → 4조건 판정(절대 feasibility·zero ceiling 복구 + paired gap LCB)(§6) / **[D-4]** V-5′ 수정 승인·exit 식 기각 후 대체 → primary = paired Δ LCB, McNemar 보조 격하, exit = zero-캐시 paired 전진(§7) / **[D-5]** 수정 승인 → 번들 생성을 validation·셀 제외 **이후**로 이동 + SHA-256 manifest(§8).

## 1. 최소 배경 (직전 리뷰와 동일 세팅 — 요약 재수록)

- **게임**: 방어 리미터 N=4(가속 제어, ‖a‖≤30) + 1회 발사 finisher + 스크립트 공격자(정속 직진 추격 + 반응 회피). clean = 발사 판정 게이트 v_soft ≥ θ=0.9 ∧ 실행가능성>0 (2000-표본 MC, CRN seed 의존 — "면도날" 술어). 판정 보상·게이트·평가 경로 = 동결.
- **SBE**: witness(clean 성립 종말 상태)에서 t−k(k∈{1,2,4,8} = 스테이지 d1..d4)로 폐형식 감속-도착 프로파일을 후방 합성해 스폰(속도 주입). Δt=0.05, v0 ~ U[0.3,0.8]·30kΔt, 콘 ±15°, 스폰 오프셋 R = v0Δt(k−1)/2, zero-coast 오버슛 O = v0Δt(k+1)/2 (귀하가 지적한 k=1 2× 표 오류는 정정·테스트 락).
- **witness 3가족**(공격자 속도) = v16 / v20 / v24, 각 1본. **bank v2의 정의(3자 충돌③ 채택 — Gate B가 경고형(ii)인 이상 observation-realizable을 정의의 필수조건으로 쓰지 않는다) = "action-necessary, forward-verified predecessor synthesis with an observation-controller realizability audit."**

## 2. 경위: bank v1이 죽고 v2가 필요해진 이유

0-c calibration(균형 dev 번들, 30판/셀, 4-arm, 전 항목 커밋 `970b039`) 결과 — **admissible 2/12**:

| 셀 | zero | random | brake | demo(개방루프) | 판정 |
|---|---|---|---|---|---|
| d1/v16 | .00 | .03 | .13 | .40 | fail |
| d1/v20 | .00 | .10 | .93 | .83 | **PASS** |
| d1/v24 | — | — | — | — | 선점(reset_clean .97) |
| d2/v16 | .03 | .00 | .00 | .13 | fail |
| d2/v20 | .00 | .03 | .37 | .53 | fail |
| d2/v24 | .70 | .43 | .77 | .77 | fail(zero) |
| d3/v16 | .00 | .00 | .00 | .13 | fail |
| d3/v20 | .00 | .00 | .00 | .47 | fail |
| d3/v24 | .00 | .00 | .63 | .80 | **PASS** |
| d4/v16 | .00 | .00 | .00 | .07 | fail |
| d4/v20 | .00 | .00 | .00 | .33 | fail |
| d4/v24 | .30 | .00 | .00 | .77 | fail(zero) |

실패 3모드 = **선점**(d1/v24: R≡0 구조로 스폰이 이미 clean) / **관성 공짜**(v24 zero k-비단조 .70/.00/.30) / **v16 전멸 + v20 개방루프 감쇠 교락**. 이에 대한 결정 5건(0d-1~5)을 귀하가 5/5 "수정 승인"했고 전 수정조건이 채택·비준됐다(docs/18 v0.2; 0d-3b = (ii): Gate B 경고 셀은 학습 bank 유지·confirmatory 클레임 제외). 본 문서는 그 비준 사양의 실행 결과(§3)와 잔여 수치 동결(§4~8)이다.

## 3. 비준 이후 실행 기록 (전부 커밋·재현 가능; 새 결정 없음 — 비준 사양의 기계적 이행)

### 3.1 측정기 구현 + 귀하의 필수 항목 이행 결과

- **PFC**(구 demo_cl; `shepherd/train/pfc.py`): a = clip(a_demo + K_p(p_ref−p) + K_d(v_ref−v), ‖a‖≤30), **무차원 게인** K_p = c_p/T_k², K_d = c_d/T_k (귀하 채택안). 참조 = bank 엔트리 **명목** 스폰의 데모 적분 — 동역학이 결정론이라 개방루프는 스폰 지터를 그대로 보존하고, PFC의 가치는 명목 참조 추적으로 그 지터를 상쇄하는 것(테스트 락: 무지터 시 PFC ≡ demo 항등 / σ0.02급 지터에서 endpoint 오차 < 0.6·|δ|).
- **귀하의 필수 정정 1 잔여 항목 이행**: ① 폐형식 R·O unit test 추가(k∈{1,2,4,8}×{v0 하한·상한} 적분기 복제와 정확 일치, k=1 정정값 명시 락) ② **zero-coast env rollout trace 대조 PASS** — 실제 env 경로에서 reset 후 k+2 스텝 전 구간 limiter 위치 == p₀+j·v₀·Δt (atol 5e-4) = "스폰→t=0 사이 정확히 k회 이동" 시간 인덱스 계약 실측 확인. **귀하의 "k+1회면 식 재기술" 분기는 불발**(bank 스크립트 k회 이동과 정합).
- Gate B 프로토타입(brake·λ-brake·attpd) = 생성자 시그니처 수준에서 특권 인자 금지(구조 락). 테스트 +17, 인접 회귀 66 green.

### 3.2 게인 스캔 → (c_p, c_d) = (1.0, 0.5) 동결

전용 tune 번들(신규 variant, reset seed 8.01M–8.08M — dev/sealed/전 역사 대역과 서로소, 테스트 락)에서 9 combo × 12셀 × 10판 = **1080판**. 선택 규칙(pooled argmax → tie: 단순 게인 → 중립 근접 → 결정론)은 **결과 판독 전에 커밋**(`24c3026`). pooled arrival:

| c_d\c_p | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| 0.5 | .458 | **.492** | .450 |
| 1.0 | .458 | .483 | .433 |
| 2.0 | .442 | .467 | .467 |

표면 평탄(.433–.492) = PFC 성공률이 게인이 아니라 셀 성질에 지배 — 계측기로서 바람직(튜닝-통과 공격면 없음). argmax = **(1.0, 0.5)**, tie-break 미발동.

### 3.3 dev 12셀 PFC 재평가 (frozen 게인, 30판/셀)

| 셀 | zero | demo(OL) | **PFC** | screen(.8 point) |
|---|---|---|---|---|
| d1/v16 | .00 | .40 | .47 | fail |
| d1/v20 | .00 | .83 | **.93** | PASS |
| d1/v24 | .00 | — | .03 | 구조 선점 재확인 |
| d2/v16 | .03 | .13 | .10 | fail |
| d2/v20 | .00 | .53 | .63 | fail |
| d2/v24 | .70 | .77 | **.80** | PASS |
| d3/v16 | .00 | .13 | .17 | fail |
| d3/v20 | .00 | .47 | .40 | fail |
| d3/v24 | .00 | .80 | **.80** | PASS |
| d4/v16 | .00 | .07 | .07 | fail |
| d4/v20 | .00 | .33 | .37 | fail |
| d4/v24 | .30 | .77 | **.80** | PASS |

판독: ① v24 d2·d4가 폐루프에서 feasibility 진입(2→4셀; zero 공짜 .70/.30은 생성기 draw-필터 대상) ② **v20 감쇠의 교락 해소** — 지터-상쇄 PFC로도 d2 .63/d3 .40/d4 .37(개방루프 대비 +.10/−.07/+.04) = 감쇠의 주인은 개방루프 취약이 아니라 실질 난이도(공격자-반응 창 이동·MC 판정 잡음 — 명목-참조 추적으로 못 잡는 성분) ③ v16 전 셀 ≤ .47 → 비준 플로우대로 재리파인 트리거.

### 3.4 v16 재리파인 (1회 한정, 기준 = 탐색 전 커밋 `e537021`)

- 사전 고정 기준: 탐색 기계 = 기존 robust-witness probe 규약 그대로(1차 수락 = robust val ≥ 0.9, search/validation union seed 100–104/200–209 서로소) + **2차 수락(신규 관문) = 도착형 paired screen** — k∈{1,2} draws 각 12본(생성식 그대로), draw PASS = p̂_PFC ≥ 16/20 ∧ p̂_zero ≤ 4/20 ∧ reset_clean ≤ 4/20 (CRN seed 300–319, 신규 예약), k-PASS = ≥8/12, 채택 = k1 ∧ k2. 복수 후보 선택 규칙 결정론.
- 결과: **own**(기존 x12v16, val .90) = k1 0/12 탈락 — 전 draw pfc 8/13 abort(§3.3의 .47과 정합 = "얇은 창" 재확인) / **transplant**(도너 x20v24 패턴의 x-스케일 이식, 리파인 후 val 1.00) = **k1 8/8·k2 8/8, 전 통과 draw 20/20 PFC·0/20 zero·0/20 reset_clean** → 채택. 캐비앗: 원 뱅크가 얇은 own을 채택했던 것은 전체-스윕 공유 rng 스트림 하의 best-of 산물; 이번 v16-only 재실행(fresh rng(23), 결정론·문서화)에서 transplant가 1.00으로 리파인됨 — 기준 위반 없음.
- 해석: 재리파인의 목적("더 좋은 컨트롤러가 아니라 본질적으로 더 두꺼운 창을 찾는 탐색") 그대로 적중. 클레임 스코프는 비준대로 "v16에서 action-necessary predecessor 구성 가능"에 한정(가족 일반화 아님).

### 3.5 witness set·coverage 동결

- witness = {**v16: transplant**, v20: x16v20, v24: x20v24} → `results/a3_robust_bank_v2.json`(v1 파일 보존, x12v16 행만 교체). 교체 행은 **전 수치 독립 재계산**: val 1.00·cap 1.00·vmin 1.000, σ-베이스라인 {.02→.43, .05→.12, .1→.06, .2→.01, .5→0} — 기존 witness 대역(.02→.27–.42)과 동급 이상 = 창 두께 정상화.
- **coverage 목표(동결)**: v16 → d1·d2 / v20 → d1·d2(d2 = 저신뢰 표기, §3.3 PFC .63 — 미달 시 규칙 제외만) / v24 → d2·d3·d4; d1/v24 = C 구조 제외. 목표 = 의도 선언일 뿐, 판정은 §6 validation.

### 3.6 생성기 v2 구현 (동결 후보; 코드 = `shepherd/scripts/a3d_sbe_bank_v2.py`)

- 합성 폐형식 = v1 그대로(구성 게이트 4종 포함; v1 코드에 v0_range 파라미터만 추가, 기본값 바이트-보존 = 재생성 회귀 green). **draw-level paired screen 내장**(수록 관문): seed 400–419, PASS = 위 §3.4와 동일 3면도날. 시도 상한 48/셀·목표 12·최소 수록 8. 셀별 분포 보고(시도/수락/드랍 사유/수락 v0 통계) + **zero 포획-에피소드 len 히스토그램**(발사 = 종결이므로 len ≈ 커밋 시점 — d4 "en-route 공짜" 가설 판별용). 필터-로직 유닛 테스트 +7(가짜 synth/screen 주입).
- 플러밍 스모크(정보-무해 셀 v16/d1 — §3.4에서 이미 전판 통과가 알려진 셀; 산출 폐기): 12/12 시도 전부 수락·드랍 0·스크린 실패 0, pfc_mean .95 — **400–419 대역에서 300–319 결과 재현 = 스크린의 CRN-밴드 민감성 없음**(해당 셀 한정). 비용 실측 ~2.5–3분/수락 draw → 7셀 생성 ≈ 4–7h(셀별 독립 rng라 셀-병렬 안전).
- 정직 노트: **정확(무지터) 스폰에서 screen의 PFC ≡ 개방루프 demo**(보정항 0 — §3.1 항등 락). 즉 screen이 재는 것은 fresh-CRN feasibility이고, σ-강건성·폐루프 가치는 §6 validation(σ 물질화)에서 실측된다.

## 4. [D-1] Gate B family 확정 (8멤버, 이후 변경 금지) — 완전 수식 동결

전 멤버의 구현 = `shepherd/train/pfc.py`(커밋 `715ab70`, 생성·validation 결과 전 동결; 시그니처 수준 특권-인자 금지 테스트 락). 아래 수식이 코드와 1:1이며, **코드가 정본이고 본 절은 그 재기술이다** — 3자 지적("validation 결과를 본 뒤 구현을 해석적으로 바꿀 여지")은 이 재기술 + 기커밋으로 봉인.

- **공통 규약(전 멤버)**: 입력 = **비정규화 raw obs**(계측 하네스는 학습용 normalizer를 통과하지 않음; frozen 63-dim: limiter i pos = obs[9i:9i+3]·vel = obs[9i+3:9i+6], attacker pos = obs[45:48]·vel = obs[48:51]) — 좌표계 = env 절대 프레임. saturation = **norm 클립**(성분별 아님): a←a·min(1, 30/‖a‖). 매 스텝 현재 obs로 재계산(내부 상태·시간 인덱스 없음). agent 구분 = own-limiter 인덱스 i뿐(target assignment 없음).
- ① **brake**: a_i = clip_norm(−30·unit(v_i)); ‖v_i‖ ≤ 1e-9이면 a_i = 0.
- ② **λ-brake**: a_i = clip_norm(−λ·v_i), λ ∈ {2, 5, 10, 20} — 시정수 1/λ ∈ {0.5, 0.2, 0.1, 0.05}s가 사다리 호라이즌 T_k ∈ {0.05..0.4}s를 커버.
- ③ **attpd**: 단일 공통 타깃 **tgt = att_p + d_lead·unit(att_v)**(‖att_v‖ ≤ 1e-9이면 리드 항 0 → tgt = att_p; 부호 = 공격자 진행 방향 앞쪽), **a_i = clip_norm(k_p·(tgt − p_i) − k_d·v_i)** — v_target ≡ 0(타깃점 정지 랑데부; 전 limiter 동일 타깃). (k_p, k_d, d_lead) ∈ {(2,3,1.0), (4,4,1.0), (8,6,1.0)} — 근사 임계감쇠(ζ≈1), √k_p ∈ {1.4, 2, 2.8} rad/s. 게인 = **차원 상수**(k는 bank 메타데이터라 obs에 없음 → 무차원 T_k 스케일링은 Gate B에 구조적으로 불가능 — 특권 차단의 일부).
- 운용: 전 셀 기록 의무(GateB_best + PFC와의 격차), 경고 문턱 = **PFC − GateB_best > 0.4**. **명칭 교정(3자 채택): "obs-hard" → "hand-controller realizability warning"** — 이 문턱은 "사전등록된 8개 수동 컨트롤러가 PFC를 못 따라감"만 의미하며 actor-observation 표현 불가능성을 증명하지 않는다(family 불완전성). 산출 JSON의 `obs_hard` 키는 legacy 이름으로 유지하되 의미는 본 정의를 따른다. 지위 = 비준 (ii): 경고 셀은 학습 bank 유지·confirmatory 클레임 제외 — 셀에서 정책이 실패해도 observation insufficiency로 즉단 금지. 멤버 추가·게인 변경 금지.

## 5. [D-2] v0 후보 선택 = **lexicographic first-fit** (3자 수정안 채택, 구속)

- 후보 grid(셀 공통) = {U[0.3,0.8](= v1 분포), U[0.5,0.8], U[0.15,0.5]}, try-순서 고정(후보 0 = v1 분포 = "v1 최근접 tie-break"의 try-순서 실현). **구속 규칙**: ① try-순서대로 실행, **목표 12 draws를 달성하는 첫 후보를 즉시 채택**(이후 후보 미실행) ② 전 후보가 12 미달이면 **최소 수록 8 이상인 가장 앞 후보** ③ 전부 8 미달 = 셀 제외(rule C). — 구 규칙("첫 ≥8 즉시 채택")은 8-draw 한계 후보가 12-draw 안정 후보를 차단하는 support-diversity 손실이 있어 기각(3자 지적 수용). argmax 모드는 **비구속 진단 전용**으로만 잔존.
- **후보별 rng(3자 요구 명시)**: draw stream = `default_rng(47_000 + 1_000·k + int(v) + 100_000·ci)` — (cell, candidate)당 **독립 스트림**(후보 간 CRN 아님; attempt는 스트림 내 순차 소비). screen reset seed = **420–439 고정 20판**(candidate·draw 무관 동일 = draw 간 CRN).
- **생성 screen 대역 교체(3자 충돌④ 수용)**: **420–439 신규**(전 가족 서로소, 테스트 락). 구 400–419는 스모크(v16/d1)에서 결과를 관측했으므로 **smoke-only 대역으로 은퇴**(부분 unblinding 해소; 스모크 결과는 여전히 폐기·비인용). 근거였던 "정보-무해" 항변은 철회하고 대역 교체로 대체.

## 6. [D-3] admissibility 독립 validation (3자 "중요 수정" 반영 — 4조건 판정)

- **validation 세트**: 생성·수록된 각 셀에서 **에피소드 100판** — bank v2 draw에서 **스테이지 σ를 물질화**(번들과 동일 기제; 지터 rng base 76,000)한 스폰 + reset seed **600–699**(신규 예약, 전 대역 서로소). σ 물질화이므로 여기서는 PFC ≠ demo(폐루프 가치·σ-강건성이 실측됨). **outcome = `arrival_capture`**(도착-포획; reset-clean 포획은 feasibility에 불산입 — 3자 요구 명시), 짝지음 = 동일 (draw, seed, 물질화 스폰)에서 PFC/zero 양팔 실행.
- **draw 배정(3자 수정 채택 — 쉬운 draw 과대표집 차단)**: 수록 draw n_d개(8–12)에 **균등 배정**: 각 draw ⌊100/n_d⌋판 + 잔여 (100 mod n_d)판은 **draw index 오름차순**으로 1판씩 추가(기계적 tie-break). seed 매핑 = 600부터 draw index 순 블록 배정(결정론). 지터 rng = `default_rng(76_000 + 1_000·k + int(v))` 셀당 1스트림, 배정 순서대로 순차 소비(양팔 공유 = 짝지음 유지).
- **판정(전부 충족해야 수록; 하나라도 미달 = C 제외) — 3자 4조건 채택(기존 6조건의 절대 feasibility·zero ceiling 복구)**:
  - **A. 비선점**: p̂(reset_clean) ≤ 0.2
  - **B. feasibility**: p̂(arrival_PFC) ≥ 0.8
  - **C. action-necessity**: p̂(arrival_zero) ≤ 0.2
  - **D. 통계 headroom**: **LCB95(paired Δ = PFC − zero) > ε = 0.4** — percentile 단측 부트스트랩 10,000회·rng 777(**primary = episode-level** paired bootstrap; **sensitivity = draw-cluster bootstrap**(draw 복원추출 후 소속 에피소드) 병기 보고, 판정은 primary).
  - gap LCB 단독이면 (PFC, zero) = (.55, .05) 같은 저-feasibility 셀이 "큰 상대 개선"만으로 생존 — v0.2의 조건 축소는 기존 비준 6조건과 충돌이었음(3자 지적 정당, 철회).
- 파워 스케치(n=100): (.85,.05) → LCB ≈ .71 / (.80,.15) → ≈ .56 / (.70,.20) → ≈ .40 경계. **전제 명시(3자 요구)**: 위 수치는 zero-success ⊂ PFC-success인 **nested-success 근사**(p₀₁ ≈ 0)이며, Var(D) = p₁₀+p₀₁−(p₁₀−p₀₁)²이므로 양방향 discordance(p₀₁↑)가 있으면 실제 LCB는 더 낮아진다. 미달 셀 = C 제외, **이후 생성식·문턱 재조정 금지.** 진단 arms(zero/random/brake/demo-open/Gate B 8종)는 기록 의무·판정 불참. 추론 단위: admissibility = episode / 학습 판정 = training seed(혼합 금지).

## 7. [D-4] V-5′ 최종형 + 스테이지 exit (3자: V-5′ 수정 승인·exit 식 기각 후 대체 — 반영)

- **V-5′ primary(단일화, 3자 채택)**: 동일 에피소드 paired contrast D_e = arr_π(e) − arr₀(e), **δ_min = 0.10**. **P1(3-seed mechanistic pilot) 통과 규칙** = ① 3 seed 중 **≥2 seed에서 seed별 Δ̂ > 0.10** ∧ ② 나머지 seed도 Δ̂ ≥ 0 ③ pooled episode 결과는 진단 전용 ④ 클레임 = "pilot evidence"로 제한(모집단 CI 주장 금지). **P2(10-seed confirmatory)** = **seed-계층(hierarchical) 부트스트랩**(training seed 복원추출 → seed 내 episode pair 복원추출, 10k·rng 777): **LCB95(E_seed[Δ]) > 0.10** 단일 primary. **exact McNemar(단측)는 seed별 보조 진단으로 격하**(H₀:Δ=0 검정이라 δ_min을 직접 검정하지 못함 — 3자 지적 수용; "McNemar 유의 + δ" 병렬 표기는 폐기). 무행동 컨트롤 = 상설 무결성 게이트, competence 리그 분리 보고, 2-tier 클레임 유지, 8항 사전 체크리스트, 하드 스톱 불변.
- **스테이지 exit(구 exit_d = UCB95(zero_d)+δ_min은 기각·폐기 — absolute 문턱 회귀 + dev/validation zero 불일치)**: **paired 전진 규칙(Hyunjun 비준 = 점추정 히스테리시스형)**. dev-v2 번들 생성 직후 스테이지별 **zero-arm outcome을 episode ID 단위로 1회 계산·캐시**(정책-무관, 학습 중 재실행 불요). 매 게이트 eval(스테이지 에피소드 n≈80)에서 동일 episode ID로 Δ̂_d = mean(arr_π − arr₀): **전진 = Δ̂_d > 0.10을 2-eval 연속 충족 / 후퇴 = UCB95(Δ_d) < 0.05**(에피소드 부트스트랩 10k·rng 777) **∧ stall 3-eval**(기존 백오프 cadence 유지). δ_stage = δ_min = 0.10 공용. 부록 A는 validation 수치의 기록 대입만 남는다(exit 산식 입력으로는 미사용).
- **지위 구분(3자 요구)**: dev-v2 게이트 성적 = **development 결과**(반복 평가 = 정책 선택에 사용된 데이터) / sealed-v2 = **confirmatory 결과**. 논문 클레임은 후자에서만.

## 8. [D-5] 번들 계획 (3자 순서 교정 반영)

- **dev-v1·sealed-v1 = 구조 변경으로 폐기 기록**(bank v1 스폰 물질화본; 파일 보존·삭제 금지, 이후 어떤 판정에도 미사용). tune 번들 = 게인 선정 전용 소임 종료.
- **생성 순서(구속; 3자 지적 — validation 전 sealed 생성은 제외 셀 혼입 → sealed 단일생성 원칙과 충돌)**: ① bank v2 후보 생성 → ② §6 독립 validation → ③ 미달 셀 C 제외 → ④ **최종 admissible cell matrix 동결** → ⑤ 그 후 **dev-v2 = {rng 75,000, seed 12.0M} / sealed-v2 = {rng 95,000, seed 13.0M}** 생성(균형 물질화, 전 대역 서로소) → ⑥ manifest·해시 기록. sealed-v2 = P2 확증 전 롤 금지(러너 거부 유지).
- **번들 조성 동결(3자 요구 항목)**: 스테이지별 총판수 = admissible 셀 균등 분할(잔여는 witness 속도 오름차순 셀에 1판씩) / 셀 내 draw 배정 = §6과 동일한 균등+index-순 잔여 규칙, **비복원 순환**(draw index 순 라운드로빈) / witness weighting = 균등(속도별 prior 없음) / episode reset seed = base(12.0M/13.0M)+순번, 지터 rng = variant rng(75k/95k) 순차 소비 / **excluded 셀 = 번들에 부재가 정상 — 러너는 번들 셀 ⊆ admissible matrix를 assert**(위반 = 즉시 abort) / zero-캐시 매핑 = episode ID(번들 내 일련번호) 기준 1:1.
- **스테이지 최소 셀 규칙(3자 권장 채택)**: admissible 셀 **0개 스테이지 = 해당 스테이지와 이후 진행 중단** / **1개 = mechanistic pilot만 허용·family claim 금지** / 2개 이상 = 정상. **사전 인지 명시: coverage 목표상 d3·d4는 애초 1셀(v24)이므로 통과해도 family claim 불가** — P1이 D1→D2 한정인 이유와 정합. **coverage minimum(bank 성패 기준) = d1·d2에 각 ≥1 admissible 셀** — 미달이면 bank v2 실패 선언(재생성 1회 원칙 하 캠페인 재설계로 이행; 문턱 완화 구제 금지). PFC-validation 미달의 처리 = 셀 제외뿐(whole-bank 실패는 위 minimum으로만 판정).
- **manifest = SHA-256**(md5 병기 가능하나 판정 기준은 SHA-256; 3자 채택): 대상 = 번들 파일·bank v2 파일·최종 cell matrix·생성기 커밋 해시·config·seed 대장·PFC 게인·Gate B 사양(§4)·validation verdict 파일. **sealed 불가침 테스트 확장(P1 전 커밋)**: 러너의 sealed 경로 직접 입력 거부 + symlink/복사-개명 우회 + `--force`류 플래그 부재 + metadata-only 변조 검출(SHA-256 대조) 각각 테스트로 잠금.

## 9. σ 평가 grid + seed 대장

- **σ(0d-5 비준 이행)**: 학습 램프 불변(d0 0 / d1 .005 / d2 .01 / d3 .015 / d4 .02). 최종 평가 = 전 스테이지 × **{배정σ, 공통 0.005}** 필수 [+ {0, .02} 여유 시], 전 arm + learned policy. 진단 전용(사후 σ 선택 금지). d4 = robust-마진 계측지.
- **seed 대장 — namespace별 재편(3자 자유도⑪ 수용; 소비 RNG가 다른 namespace 간 수치 중복은 무해하나 이하로 구분 표기한다)**:
  - **train_seed**(학습 프로세스 시드): 0–9.
  - **geometry_MC_union_seed**(clean 판정 2000-표본 MC union 빌드): 7–16(robust 게이트)·100–104(witness 탐색)·200–209(witness 검증) — train_seed와 수치 겹침(7–9)은 namespace 상이로 무해(전자는 torch/env 학습 스트림, 후자는 viability union 빌드 시드).
  - **episode_reset_seed**: 300–319(재리파인 screen)·**400–419(smoke-only로 은퇴)**·**420–439(생성 screen [신규])**·**600–699(validation [신규])**·500k/1.5M/2.5M(eval 가족)·7.0M(dev-v1)·8.0M(tune)·9.0M(sealed-v1)·**12.0M(dev-v2)·13.0M(sealed-v2) [신규]**·31M(fire-oracle).
  - **jitter_rng**: 71k/93k(v1 번들)·81k(tune)·**75k(dev-v2)·95k(sealed-v2)·76k대(validation; §6 파생식) [신규]**.
  - **draw/탐색 rng**: 23(probe·리파인)·23k+k(재리파인 draw)·**47k대(생성 draw; §5 파생식)**.
  - **arm rng**: 90k+7·ep(random arm — 정의 동결: **성분별 U[−1,1]³ × 30, norm 클립 없음**(코드 그대로; ‖a‖ 최대 30√3 큐브 분포) — 3자 자유도⑨ 명시).
  - **bootstrap_rng**: 777(episode·draw-cluster·seed-계층 전부).
- **teacher clean 판정 보조 진단(3자 자유도⑩ 채택, 비구속 기록 의무)**: P1부터 발사 시점마다 fresh-seed robust-clean fraction·clean persistence(직전 연속 clean 스텝 수)·v_soft 마진을 로깅 — 판정은 동결(single-CRN spike 수확 여부의 사후 감식용).

## 10. 자기신고

① 작성자 = 설계·실행 참여자(이해충돌). ② §3의 dev/tune 수치는 30·10판 point(SE .07–.15) — 워크플로 라우팅용이며 구속 판정은 §6 validation. ③ v24 3셀의 PFC .80은 문턱 정확 접촉 — validation에서 흔들릴 수 있고, draw-필터가 모집단을 바꾸므로 그대로 이월되지 않음. ④ screen의 PFC ≡ demo 항등(무지터; §3.6) — screen 명칭에 오해 소지가 있어 명시. ⑤ (bbb) 재리파인의 rng 스트림 차이(§3.4 캐비앗). ⑥ 스모크(v16/d1)가 400–419 대역 결과를 관측한 문제 = **해당 대역 은퇴 + 생성 대역 420–439 교체로 해소**(§5; 3자 처방 채택). ⑦ Gate B 멤버 수치(λ·PD 게인)는 제어이론적 스팬 논리로 선정했으나 실측 근거는 없음 — validation에서 처음 측정됨.

## 11. 검토 이력 + 확정 실행 순서

- **검토 이력**: v0.1(결정 슬롯) → v0.2(자기완결 3자 검토판) → 3자 회신 1회(조건부 승인: "수정 반영 후 bank v2 생성 승인"; D-1 수정승인·D-2 수정승인·D-3 중요수정후승인·D-4 V-5′수정승인/exit기각·D-5 수정승인 + 충돌 4·잔여 자유도 11·체크리스트 15) → **v0.3 = 전 항목 반영 + Hyunjun 비준(exit = 점추정 히스테리시스형, 나머지 일괄 수용) = 0-e 동결.** 추가 검토 라운드 없음(리뷰어 조건부 승인 취지).
- **확정 실행 순서**: 본 동결 커밋 → **bank v2 1회 생성**(seeds 420–439, lexicographic first-fit, ≈4–7h, 셀-병렬 허용) → **§6 validation**(n=100/셀, 4조건) → C-제외 → **admissible matrix 동결** → 부록 A(validation 수치 기록 대입) → **dev-v2/sealed-v2 생성 + SHA-256 manifest** → zero-캐시 → P1(3-seed, D1→D2 한정, §7 규칙). 학습 금지는 P1 개시 시점까지 유지.

## 12. 3자 체크리스트 15항 반영 대조표

| # | 요구 | 반영 |
|---|---|---|
| 1 | attpd 수식·클리핑·타깃 동결 | §4 (코드 `715ab70` 재기술) |
| 2 | first-fit = target 12 → min 8 | §5 + 생성기 패치·테스트 락 |
| 3 | 생성 seed 미사용 대역 교체 | §5 420–439 (400–419 은퇴) |
| 4 | outcome = arrival_capture 명시 | §6 |
| 5 | PFC≥.8 / zero≤.2 / reset_clean≤.2 복구 | §6 A–C |
| 6 | paired gap LCB>0.4 유지 | §6 D |
| 7 | 100판 draw 균등 배정 | §6 배정식 |
| 8 | 파워 스케치 nested-success 전제 | §6 |
| 9 | P1/P2 판정 분리 | §7 |
| 10 | McNemar 보조 격하·primary = Δ CI | §7 |
| 11 | stage exit = 직접 paired | §7 (비준 (ii)형) |
| 12 | matrix 동결 후 dev/sealed 생성 | §8 순서 |
| 13 | 셀 weighting·0/1-cell 규칙 | §8 |
| 14 | seed namespace 정리 | §9 |
| 15 | sealed manifest SHA-256 | §8 |
