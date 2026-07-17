# 18 — Phase 0-d 결정 5건: bank v2 생성식 — 옵션 비교·비준 체크 (v0.2, 2026-07-17 — 3자 검토 반영판, Hyunjun 최종 비준 대기)

> **성격**: 자기완결 비준 문서. v0.1(옵션 비교)에 대한 **3자 독립 검토(2026-07-17 접수)를 전 항목 판독·반영**한 개정판. 3자 판정 = 5슬롯 전부 "수정 승인"(0d-1 수정 A+C / 0d-2 조건부 A / 0d-3 수정 B / 0d-4 수정 B / 0d-5 수정 A). 우리 측 재검증에서 **리뷰어 지적 중 오류 0건**(§1.1 검증 노트) — 필수 정정 3건 및 수정 조건 전체를 아래에 반영했다. 남은 것은 Hyunjun 최종 비준(§10; 오픈 포인트 0d-3b 1건 포함). 정본 = `newURP/docs/18_a3d_bankv2_options.md`.
>
> **v0.1 → v0.2 변경 요지**: ① §1 k=1 오버슛 표 **2× 산술 오류 정정**(0.045–0.12 → 0.0225–0.06; 적분기 복제 시뮬로 전 k 재검증) ② 0d-3 = **2-게이트 오라클**로 개편(Gate A 특권 feasibility + Gate B 관측-실현성; "행동공간 동일 = 클래스 정합" 논리 철회) ③ **§8 실행 순서 교체**(v16 재리파인이 재생성 뒤에 있던 충돌 해소: 측정기 동결 → witness 동결 → 생성식 동결 → bank v2 **1회** 생성) ④ 0d-4 = 2단계 통계(gap point 조건 = 중복이라 삭제, 독립 검증의 LCB 조건으로 전환) ⑤ 0d-5 = 공통-σ 평가 grid(전 arm + learned policy) ⑥ 구조 지적 5건 채택(§8.5) ⑦ bank v2 정의 확장 = **action-necessary, forward-verified, observation-realizable predecessor synthesis**.
>
> **불변 규율(재확인)**: 판정 J·게이트 정의·평가 경로 동결 / 신규 개입 = 학습 스캐폴드 전용 / sealed 번들 불가침 / P0 = 학습 금지 / **재생성 1회 원칙** — admissibility 미달을 문턱·생성식의 반복 조정으로 구제하지 않는다(외부 리뷰 2026-07-16: "핀 수정 후 zero가 전 witness에서 높아진다면 문턱을 올려서 해결할 일이 아니다") / 하드 스톱·트립와이어 2026-08-31 불변 / 채택 결과는 **0-e 일괄 커밋에 사전등록 문구로 고정**(학습 착수 전, 결과 미견 상태).

## 0. 위치

- 0-c calibration 마감(09 (uu), `970b039`): bank v1 = 12셀 중 admissible 2(d1/v20·d3/v24), 실패 모드 3종(선점/관성 공짜/지터·개방루프 취약) → bank v2 재생성 필요 확정. 본 문서 = 재생성 전 고정할 결정 5건.
- v0.1 권고 패키지(0d-1 A+C / 0d-2 조건부 A / 0d-3 B / 0d-4 B / 0d-5 A)는 3자 검토에서 **방향 전부 승인**되었고, 각 슬롯에 수정 조건이 붙었다. 본 v0.2는 그 수정 조건을 사양 수준으로 반영한 **비준 대상 최종안**이다.
- 배경 수치·측정표·witness 정의는 v0.1 §0~§2와 동일(§2에 재수록). 3자 검토 전문 = `URP/a3d_0d_external_review_2026-07-17.md`(접수본).

## 1. bank v1 생성식 폐형식 (정정판)

리미터별 도착 프로파일: witness 슬롯 L*에 t=0, 속도≈0 도착. Δt=0.05, 적분기 v′=clip(v+aΔt), p′=p+v′Δt.
v0 ~ U[0.3,0.8]·(30·kΔt), 선형 감속 |a| = v0/(kΔt) ∈ [9,24](데모 상한 24 = 0.8·30), 도착 방향 = anchor(명목 링 자리)→L*, 콘 지터 ±15°.
스폰 오프셋 **R = v0Δt(k−1)/2**, zero-action(등속 coast) 시 t=0 오버슛 **O = v0Δt(k+1)/2**:

| k (스테이지) | v0 범위 [m/s] | R 스폰 거리 [m] | O zero 오버슛 [m] |
|---|---|---|---|
| 1 (d1) | 0.45–1.2 | **0 (슬롯 위 스폰)** | **0.0225–0.06** (v0.1의 0.045–0.12는 2× 오류 — 정정) |
| 2 (d2) | 0.9–2.4 | 0.023–0.06 | 0.068–0.18 |
| 4 (d3) | 1.8–4.8 | 0.135–0.36 | 0.225–0.60 |
| 8 (d4) | 3.6–9.6 | 0.63–1.68 | 0.81–2.16 |

### 1.1 검증 노트 (v0.2)

- **적분기 복제 시뮬**(v′=v+aΔt; p′=p+v′Δt, 코드 명세 그대로)로 전 k×{v0 하한, 상한} 재검증: R·O 폐형식과 시뮬 정확 일치(오차 ≤1e-16), 데모 롤은 L* 도착·v_end≈0 확인. **k=1 표만 2× 오류였고 식 자체는 정확** — 3자 지적 그대로.
- 정정의 함의: d1의 zero 이동량이 절반 → 넓은 창(v24)에서 passive success 여지가 **더 크다** = d1/v24 구조 제외(C) 결론 강화(3자 판독과 합치).
- 잔여 확인 항목(0-d 구현 시): ① 폐형식 R·O **unit test**를 t-free 스위트에 추가 ② 실제 env 경로에서 teacher 판정 시점 수(스폰 obs 판정 + k회 스텝 = k+1개 판정 상태)를 **rollout trace로 대조**(bank 스크립트는 k회 이동으로 확인됨; env 측 counting이 다르면 식이 아니라 시간 인덱스 정의를 재기술).

구조적 함의(불변): ① k=1은 R≡0 — 선점은 draw 재추첨으로 구제 불능 ② O ∝ v0 — "운동량 축소"는 저k에서 공짜를 늘리는 방향이므로, 0d-1은 '축소'가 아닌 **사전 고정된 후보 grid에서의 재보정 + draw-필터**로 정의한다.

## 2. 0-c 측정표 (증거 원본 — dev 번들, 30판/셀, arrival_capture; v0.1 §2 동일)

全 arm은 teacher 동반(clean 판독 시 강제 발사): zero = 무행동 / random = ±30 균등 / brake = −30·unit(v) / **demo = 개방루프 재생**(k스텝 후 0). 번들은 스테이지 배정 σ 반영.

| 셀 | zero | random | brake | demo | 판정(v1 예시 규칙) |
|---|---|---|---|---|---|
| d1/v16 | .00 | .03 | .13 | .40 | fail(demo) |
| **d1/v20** | .00 | .10 | **.93** | .83 | **PASS** |
| d1/v24 | — | — | — | — | 선점(reset_clean .97) |
| d2/v16 | .03 | .00 | .00 | .13 | fail(demo) — 지터 취약 |
| d2/v20 | .00 | .03 | .37 | .53 | fail(demo) |
| d2/v24 | **.70** | .43 | .77 | .77 | fail(zero) — 관성 공짜 |
| d3/v16 | .00 | .00 | .00 | .13 | fail(demo) |
| d3/v20 | .00 | .00 | .00 | .47 | fail(demo) |
| **d3/v24** | .00 | .00 | .63 | **.80** | **PASS** |
| d4/v16 | .00 | .00 | .00 | .07 | fail(demo) |
| d4/v20 | .00 | .00 | .00 | .33 | fail(demo) |
| d4/v24 | .30 | .00 | .00 | .77 | fail(zero) — 관성 공짜 |

판독 요약: 관성 공짜 = k-비단조(v24: .70/.00/.30) / v16 전멸(demo≤.40) / v20 demo k-감쇠(.83→.33, 개방루프 교락) / brake 저k 강·고k 자멸 / 선점 = d1/v24. 재현성: 서버-샌드박스 겹침 12셀 정확 일치. 30판 이항 SE ≈ .073–.091.

## 3. 0d-1 — v24 관성 공짜: **수정 A+C** (3자 승인 반영)

**확정 구조**: d1/v24 = **C 즉시 제외**(R≡0 구조 선점 — draw filtering으로 구제 불가, 3자 합치). d2·d4/v24 = **draw-level action-necessity 필터**(demo_cl 성공 ∧ zero 실패 ∧ reset 비-clean)로 1회 재생성 시도, 잔존 실패 셀 = C. B(기하·프로파일 개정)는 V-1 개정 재비준 조건의 에스컬레이션 예약.

**3자 수정 조건 채택 (v0.2 사양)**:

1. **v0 재보정의 사전 고정** — "calibration 보고 셀별 재보정"의 자유도를 제거: ⓐ 후보 = **유한 스케일-구간 grid ≤3개/셀**(상한 0.8 고정 = \|a\|≤24 예산 내; 목록은 0-e에 명기, bank 생성 전 동결) ⓑ 선택 목적함수 = **max(p̂_PFC − p̂_zero) s.t. p̂_PFC ≥ .8 ∧ p̂_zero ≤ .2**(스크린 seed에서) ⓒ tie-break = **v1 분포(U[0.3,0.8]) 최근접 후보** ⓓ 전 후보 실패 = 셀 제외(C).
2. **seed 분리** — construction/filter seed set과 post-selection **validation seed set 서로소**(lucky-seed rejection sampling 차단). 검증 판정은 validation seed에서만(0d-4의 2단계와 동일 기계).
3. **필터 전후 분포 보고 의무** — draw acceptance rate / v0·방향·위치·속도의 전후 분포 / accepted unique draw 수 / 데모 가속열 다양성. 최소 수록 draw 수 8/12 = **파일럿 운영 기준일 뿐, 가족 일반화 근거 아님**(§8.5-③).
4. zero-arm **발사 시점 히스토그램** 검증기 동승(d4 en-route 가설 판별; v0.1 제안 유지).

## 4. 0d-2 — v16 가족: **조건부 A** (3자 승인 반영)

**확정 구조**: 새 오라클(0d-3) 하에서 기존 v16 재평가 → 미달 시 **재리파인 1회** → 실패 시 즉시 B(폐기 + 스코프 문구). **위치는 bank v2 생성 전**(§8 순서 — 3자 필수 정정 ③).

**3자 수정 조건 채택**: ⓐ 탐색 예산·후보 공간·수락 기준을 탐색 **전** 고정(도착형 6조건 + coverage 목표) ⓑ acceptance/validation seed 분리 ⓒ **스테이지×witness 목표 coverage 매트릭스를 탐색 전에 동결** — 대표 k∈{1,2}로 선택하고 d3·d4 커버를 주장하는 것 금지; 목표 셀 미달분은 그 셀만 제외 ⓓ 1회 실패 = 폐기 ⓔ 기존 v16 실패 결과 = **negative result로 보존**(docs/12 §6 증거 테이블 행) ⓕ 성공해도 클레임은 "v16 가족 일반화"가 아니라 **"v16에서 action-necessary predecessor 구성 가능"**(witness 단수 스코프, §8.5-④).

## 5. 0d-3 — feasibility 오라클: **수정 B = 2-게이트** (3자 승인 반영)

v0.1의 "정책과 동일 행동공간이므로 클래스 정합" 논리는 **철회**한다(3자 지적 수용: 행동공간은 같아도 **정보공간이 다름** — 데모 궤적·참조 시점은 정책 obs에 없음). 개편:

- **Gate A — PFC(privileged feasibility controller, 구 demo_cl)**: a = clip(a_demo + K_p(p_demo−p) + K_d(v_demo−v), \|a\|≤30). 질문 = "제한 가속도 내 성공 궤적 존재?" **admissibility ⑤⑥의 feasibility 측정기 = Gate A**. 특권 참조(데모 궤적) 사용을 명시 — "oracle ceiling"이라 부르지 않는다(최적화된 상한 아님).
  - **게인 무차원화(3자 채택)**: K_p(k) = c_p/T_k², K_d(k) = c_d/T_k, T_k = kΔt. 전역 선택 대상은 **(c_p, c_d) 한 쌍**(k별 시간척도 자동 정합, 셀별 튜닝 금지). 후보 grid는 0-e에 사전 명기.
  - **게인 선택 편향 차단**: gain-tuning seed set을 admissibility 평가 seed와 **서로소**로 분리(스크린·검증 seed와도 서로소).
- **Gate B — 관측-실현성(reference-free) 컨트롤러**: 정책 obs로 도출 가능한 정보만 사용 — 데모 궤적·draw ID·witness 라벨·참조 시점 **사용 금지**. 컨트롤러 family(사전 고정): ① 기존 brake(−a_max·unit(v)) ② λ-brake(a = −λv, λ 유한 grid) ③ obs-유도 타깃 유도 1종(**공격자-상대 기하로만** 타깃 도출 — 3자 예시의 "limiter–목표 상대"에서 '목표'가 witness 슬롯 좌표라면 그 자체가 특권이므로, obs에 실재하는 공격자 상태 기반으로 한정). **전 셀 기록 의무**: GateB_best 성공률 + PFC와의 격차. 격차 > 사전등록 문턱 → **"physically-feasible but observation-hard" 경고 플래그**.
  - **오픈 포인트 0d-3b (Hyunjun 결정)**: Gate B의 지위 — (i) **기록+경고 전용**(3자 본문 문면: "0.8 요구 아님, 격차 시 경고") vs (ii) **경고 셀은 confirmatory 클레임에서 제외**(training bank에는 유지) vs (iii) 하드 admissibility 게이트. 권고 = **(ii)**: §8.5-②의 2-tier 클레임 구조와 정합(mechanistic 학습 증거는 유지하되 method-competence 클레임 대상에서 제외), (i)보다 강하고 (iii)처럼 커버리지를 즉사시키지 않음.
- 개방루프 demo는 **진단 열로 병기**(리그 연속성·감쇠 교락 데이터). admissibility "demo" 정의 변경(개방루프→Gate A)은 0-e 사전등록에 명시(리뷰의 demo≥.8 예시가 개방루프 전제로 읽혔음을 함께 기록).

## 6. 0d-4 — admissibility 수치·표본: **수정 B = 2단계 통계** (3자 승인 반영)

v0.1 안의 통계 결함 2건 정정(3자 지적, 우리 재검증 합치):

- **gap≥.4 point 조건 = 중복 삭제**: demo≥.8 ∧ zero≤.2 (point)면 자동으로 gap≥.6. gap 조건은 point가 아니라 **독립 검증의 신뢰구간 조건**으로 이동.
- **n=20 point는 인증이 아님**: CP 단측 95% 상계 — 4/20 → **.401** / 0/20 → .139 / 1/20 → .216; 16/20 하계 → .599 (전부 재계산 확인). n=20으로 ".8/.2 검증됨" 서술 금지.

**확정 2단계 절차**:

1. **draw-level engineering screen** (생성기 내장): n=20 CRN seeds, **paired**(같은 ep·같은 CRN), point 기준 p̂_PFC ≥ .8 ∧ p̂_zero ≤ .2 ∧ reset 비-clean. 지위 = 스크리닝(통계 인증 아님·보고서에 그렇게 서술).
2. **cell-level 독립 검증**: 서로소 validation seed에서 **n=100/셀**(3자 허용 범위 60–100의 상단; 비용 무시 가능), 판정 = **LCB95(p_PFC − p_zero) > ε, ε=.4**(paired). 파워 재확인: demo .83/zero .05에서 LCB≈.69, demo .80/zero .15에서 ≈.56 — ε=.4는 건강 셀에 여유, 경계 셀에 유효 변별.
   - v0.1의 "경계 셀 ±0.07 → 60판 증량" 규칙은 **2단계 설계로 대체**(폐기 아님 — superseded 기록).
3. **추론 단위 분리 명시**: admissibility = bank 셀 성질 → episode 단위 추론 가능. 학습 정책 비교(V-5′·P1/P2) = **training seed 단위**. 두 통계 혼합 금지.

## 7. 0d-5 — 스테이지 σ 정책: **수정 A** (3자 승인 반영)

- training ramp **유지**: d0 0.0 / d1 .005 / d2 .01 / d3 .015 / d4 .02 (d4 = robust-마진 계측지 유지).
- **k–σ 교락 제거(3자 채택)**: 스테이지 상승 시 k와 σ가 동시에 오르므로, 성능 감소의 원인(호라이즌 vs 지터)을 분리하려면 **공통-σ 평가축**이 필요. 최종 평가 grid: 전 스테이지 × **{배정 σ, 공통 σ=.005}** 최소 2조건(여유 시 σ∈{0, .005, .02} factorial), 적용 대상 = **전 arm**(zero/random/brake/demo-open/PFC/Gate B) **+ learned policy**(P1부터 동일 grid).
- 사전등록 문구: σ-스윕 = **진단 전용** — 결과를 보고 셀별 training σ나 admissibility σ를 사후 선택하지 않는다.

## 8. 최종 실행 순서 (3자 필수 정정 ③ 반영 — v0.1 §8 대체)

1. **측정기·평가축 동결**: PFC(무차원 게인 grid·선택 규칙·tuning seed) + Gate B family + 0d-5 σ ramp·공통-σ 평가 grid + seed 대장(전 세트 서로소: gain-tuning / screen / validation / dev / sealed / 역사 seed족).
2. **witness set 동결**: 기존 v16을 새 오라클로 재평가 → 필요 시 사전등록 예산으로 재리파인 1회 → 실패 시 v16 제외. **스테이지×witness 목표 coverage 매트릭스 동결.**
3. **생성식 동결**: v0 후보 grid·draw 필터(6조건 paired screen)·acceptance seed·validation seed·최소 unique draw 수·C 폴백 규칙. → **0-e 사전등록 일괄 커밋**(여기까지 전부, bank 생성 전).
4. **bank v2 단 1회 생성**: 필터링 + 전방 재검증 + action-necessity 검증 + 필터 전후 분포 기록(§3-3) + zero 발사시점 히스토그램.
5. **번들 v2 생성**: 0-b 번들은 bank v1 스폰을 물질화했으므로 재사용 불가 — **sealed-v1은 삭제·덮어쓰기 없이 "구조 변경으로 폐기" 기록**, bank v2 동결 후 dev-v2/sealed-v2 생성, **sealed-v2 해시 기록**, Phase 2 전 롤 금지.
6. **독립 calibration·admissibility 판정**: 6 arm(zero/random/brake/demo-open/PFC/Gate B) × 12셀 × validation n=100. 실패 셀 = C 제외. **이 시점 이후 생성식 재조정 금지**(하드 스톱 규율 연동).
7. **V-5′·exit·δ_min 동결 → P1 학습 착수**(exit = paired action-induced arrival, 값은 6단계 calibration에서 유도·선등록).

## 8.5 구조 지적 채택 5건 (3자)

1. **necessity ≠ realizability**: PFC 성공+zero 실패 = "특권 컨트롤러가 행동하면 성공"까지만. obs-conditioned 공유 정책의 실현 가능성은 별도 — Gate B로 계측(§5). bank v2 정의 = **action-necessary, forward-verified, observation-realizable predecessor synthesis**(realizable의 강도 = 0d-3b).
2. **2-tier 클레임 구조**: brake가 강한 셀(d1/v20 brake .93 > demo .83)을 제외하지 않는다(baseline 맞춤 cherry-picking 금지). 판정 분리 — **mechanistic success** = policy > zero(paired) / **method competence** = policy ≥ brake 경쟁. 논문 정식 클레임에는 후자 필요. 하드 스톱의 brake 조건과 정합.
3. **암기(over-narrowing) 진단**: 필터 후 unique draw 수·acceptance ratio 보고 + **held-out draw 성능**·**unseen CRN 성능** 분리 평가(A-3 CRN-면도날 이력 연동).
4. **witness 단수 스코프**: 속도당 witness 1본 → 결과는 "해당 terminal witness에 대한" 것. 클레임 = "predecessor-construction feasibility"로 한정. **속도별 복수 witness / held-out terminal geometry = P2·논문 단계 요건으로 등재**(지금 스코프 확장 안 함).
5. **teacher MC-spike 진단**: 판정 계약 불변, 보조 지표 로깅 — fire 시점 **robust-clean fraction**(fresh seed bank) + clean 지속시간. "정책이 만든 robust 기하 vs 판정 잡음 스파이크" 해석 보호.

## 9. 채택 매트릭스 (3자 검토 → v0.2 반영 대장)

| # | 항목(3자) | 판정 | 반영 위치 |
|---|---|---|---|
| 필수-1 | k=1 오버슛 2× 오류 | **채택**(시뮬 확인) | §1 표 정정 + §1.1(unit test·trace = 0-d 구현 항목) |
| 필수-2 | demo_cl ≠ 정책 실현성 | **채택** | §5 2-게이트(Gate B 신설), §8.5-① 정의 확장 |
| 필수-3 | §8 순서 충돌(v16 뒤늦음) | **채택** | §8 교체(witness 동결 → 생성 1회) |
| 0d-1-1~3 | v0 grid 사전고정·seed 분리·분포 보고 | **채택** | §3 |
| 0d-2 | coverage 매트릭스·1회·negative 보존·스코프 | **채택** | §4 |
| 0d-3 | 게인 무차원화·tuning seed 분리·용어(PFC) | **채택** | §5 |
| 0d-3 | Gate B 예시 "limiter–목표 상대" | **부분 채택** | '목표'가 witness 슬롯이면 특권 누출 → obs-유도(공격자-상대) 타깃으로 한정(§5) |
| 0d-4 | gap 중복·n=20 비인증·2단계·CI 전환 | **채택**(수치 재계산 합치) | §6 (경계 증량 규칙은 superseded) |
| 0d-5 | 공통-σ 평가(전 arm+learned) | **채택** | §7 |
| 순서-5 | sealed-v1 폐기 기록·sealed-v2 해시 | **채택** | §8-5 |
| 구조-1~5 | realizability·2-tier·암기·witness 스코프·teacher spike | **채택** | §8.5 |

기각 항목 없음. 미세 보정 1건(Gate B 타깃 정보원 한정)은 3자 취지(특권 차단)를 강화하는 방향.

## 10. 비준 체크 (Hyunjun 최종)

3자 판정은 기입 완료. Hyunjun 비준으로 확정되며, 확정본은 0-e 커밋에 사전등록으로 수록(docs/09 (xx)로 기록).

| 슬롯 | 결정 | 3자 판정 | Hyunjun 비준 |
|---|---|---|---|
| 0d-1 | v24: A+C(§3 사양) | 수정 A+C 승인 | [ ] |
| 0d-2 | v16: 조건부 A(§4 사양) | 조건부 A 승인 | [ ] |
| 0d-3 | 오라클: 2-게이트 B(§5 사양) | 수정 B 승인 | [ ] |
| **0d-3b** | **Gate B 지위: (i) 기록·경고 / (ii) confirmatory 클레임 제외 / (iii) 하드 게이트 — 권고 (ii)** | (문면 = i, 총평 = 정의 포함) | [ ] i [ ] ii [ ] iii |
| 0d-4 | 수치·표본: 2단계(§6 사양; screen 20 → validation 100·LCB95(Δ)>.4) | 수정 B 승인 | [ ] |
| 0d-5 | σ: ramp 유지 + 공통-σ 평가 grid(§7 사양) | 수정 A 승인 | [ ] |

- 관련 경로: 생성기 `shepherd/scripts/a3d_sbe_bank.py` / 번들 `a3d_bundle_gen.py` / calibration `a3d_calibration.py` / 컨트롤 `a3d_null_baseline.py` / 결과 `results/a3d_calibration_dev.json`·`results/a3d_bundle_{dev,sealed}.json`·`results/a3d_sbe_bank.json` / 설계 `docs/17` / 리뷰 v0.1분 `URP/a3d_pilot2_external_review_2026-07-16.md`·본 검토 접수본 `URP/a3d_0d_external_review_2026-07-17.md`.
