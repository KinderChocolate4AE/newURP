# 20 — A-3d 이후 재설계 분기 (v0.3, 2026-07-18 — §6 보강: 외부 리뷰(2차 채널) 반영 — Q-tier 필요선·제4병목(RL-필요성)·L1-실패 감사 목록·공격자 사다리 A0–A5)

> **성격**: bank v2 FAIL((iii)) 이후 "다음 사전등록으로 무엇을 올릴지"의 옵션 비교 문서. 선택된 노선은 별도 사전등록 문서로 새로 동결한다(0-e급 절차). **불변**: 판정 J·게이트 정의·평가 경로·seed 원장·재생성 1회 원칙(소진됨 — bank v2 재생성 불가)·학습 금지(새 사전등록 전)·하드 스톱/트립와이어 2026-08-31.

## 1. 증거 요약 (재설계 입력; 상세 = 09 (iii)·results/a3d_bank_v2_validation.json)

- **확립**: ① 전방 탐색 학습 3회 붕괴(A-1/2/3, NO_FIRE) ② robust witness 실존(v16/v20/v24) ③ action-necessary 전임자 구성 가능(생성 스크린 7/7, 81 draws) ④ **오라클 σ-강건 도달 한계 — k=1 가능(PFC .94–.95) / k≥2 불가(.61–.81 < .8)**, σ 램프(.005→.02)와 감쇠 동행 ⑤ action-necessity는 σ 하에서도 생존(paired Δ̂ .58–.91, p₀₁=0; 예외 v24/d2 zero .39) ⑥ obs-hard 경고는 d4 유일(gap .43) — k≤4는 obs-정보 부족이 벽이 아님.
- **near-miss**: v16/d2 PFC .79(1판 차 탈락, 규칙대로 제외·기록) — 어떤 재설계든 첫 회생 검증 대상.
- **핵심 해석(가설 명시)**: 폐형식 후방합성 스폰은 정지-구성·이력-무 상태(off-manifold) — σ 지터가 명목-참조로 상쇄 불가능한 성분(공격자 창 이동 포함)을 만들며 k≥2에서 도달성이 무너짐. **실궤적 유래 전임자(on-manifold)는 같은 σ에서 더 강건할 개연성** — 미검.

## 2. 옵션 A-3e — D1-한정 파일럿 + 성공 궤적 수확 → rewind-v2

- **내용**: admissible 2셀(v16/d1·v20/d1)로 **d1-only bank 동결** → d1-only dev/sealed 번들(19 v0.3 §8 순서·조성 규칙 그대로, matrix = {d1}) → **P1′**(3-seed scratch, V-5′ P1 규칙 재사용: ≥2/3 seed Δ̂>0.10 ∧ 전 seed Δ̂≥0, zero-캐시 paired exit) — 클레임 = **mechanistic·D1 한정**("k=1 재성형을 판정 J 그대로 학습 가능한가"; A-3b spawn-luck 천장의 직접 후속 질문) → 성공 시 학습 정책의 **성공 에피소드 t−k 실상태 스냅샷 수확**(속도·이력 보유 = on-manifold) → 4조건 validation 재적용으로 d2 전임자 재구축 = **rewind-v2**((hh) T-4 예약분 실행).
- **근거**: §1 ④+⑥ — 벽이 "구성 상태의 인공성"에 국한된다는 가설의 최소 비용 검증 경로. near-miss v16/d2가 첫 대상.
- **리스크**: (i) D1 학습이 spawn-luck 천장을 넘는 재성형을 실제로 못 배우면 수확 자체가 성립 안 함 → 즉시 B (ii) 수확 스냅샷도 4조건을 못 넘으면 on-manifold 가설 기각 → B의 증거 행이 하나 더 늘 뿐(손실 최소).
- **규모**: D1 파일럿 3-seed ≈ 반나절(서버) + 수확·validation ≈ 1일 + rewind-v2 생성·validation ≈ 1일 — 트립와이어 내 1사이클 + 여유.

## 3. 옵션 B — 벽 논문 프레이밍 조기 확정

- **내용**: 트립와이어 전 조기 전환. 기여 = capture-unlock 벽의 다층 정량 규명(§1 사슬 + 오라클 σ-감쇠 + 2-게이트/4조건 방법론 자체). A-계열 전 산출물이 evidence로 편입(docs/12 §6 테이블 완결).
- **근거**: 증거 사슬이 이미 자기완결적; 잔여 6주를 집필·재현성 패키징에 전투입.
- **리스크**: "오라클 한계는 보였는데 학습 가능성(D1)은 미검"이 리뷰 공격면 — A-3e의 질문을 영구 미답으로 남김.

## 4. 옵션 C — 병행 (권고)

- A-3e를 **중간 게이트로 짧게 자름**: P1′ D1 게이트(위 §2) ~1주 내 판정 — 실패 즉시 B 전환(수확 단계 진입 금지). 성공 시 rewind-v2 진입하되 **8/31 하드 스톱 불변**(rewind-v2 d2 회생 실패 시점이 언제든 B).
- B 준비(아웃라인·그림 목록·§6 테이블 완결본)는 지금부터 병행 — 어느 분기로 끝나도 낭비 없음.

## 5. 결정 슬롯 (해소됨)

- **[R-1] 노선**: A-3e / B / C(병행) — **비준 = A-3e** (2026-07-18). [R-2] → docs/21로 동결(v0.3.1). [R-3] → 3자 1회 실시(조건부 승인 반영 완료).

## 6. 부록 — 도달 수준 사다리 L0~L5 + B 아웃라인 뼈대 (v0.2 추가; 2026-07-18 거시 평가 비준)

**사다리(목표선 캘리브레이션의 공용 좌표):**

| 수준 | 내용 | 상태 |
|---|---|---|
| **L0** | 비용-인지 협력 셰이핑 학습이 baseline 초과 (L2 캠페인: 3-seed DoD, mix 역-U ablation) | ✅ **달성** |
| **L1** | mechanistic 포획 학습 — action-necessary k=1 전임자에서 one-step 재성형 + 자율 발사 | **재성형 학습 ✅ 달성**(P1′ L1-phase: Δ^teacher +.79/+.80/+.93, cap .81/.82/.94 — 캠페인 최초 양성). 자율 발사는 **hybrid 재정의**(아래): learned trigger → rule-based guard, 가드 결합 dev 평가로 종결 판정 |
| **L2** | on-manifold 되감기로 k=2 회생 (rewind-v2 pooled ADOPTED) — **oracle-level**. 방법론 논문 척추는 추가로 **learned-policy level**(d2 학습 성공 = L3 진입) 요구(외부 리뷰 교정 — 자기기만 방지 명시) | **현 경로 닫힘**(합성 음성·근방 음성·d1-수확 = 구조적 생성 불가) — **on-manifold rewind 자체는 미판정**(장궤적 소스 부재; §6-보론-2) |
| **L3** | 재귀 사다리: d2 학습 → 재수확 → d3/d4 (learned-trajectory bootstrapping 완성형) | **현 경로 blocked — 일반 falsified 아님**(전제인 rewind 소스가 미확보 상태; §6-보론-2) |
| **L4** | nominal 스폰에서 유의미한 capture rate (원래 의미의 capture-unlock) | **미결 — 프레임 의존 + 접근 회랑 실존 미검**(09 (qqq)/(qqq-1): nominal 무발사 = d1-분포 정책의 transfer 실패 증거이지 회랑 부재 증거 아님) |
| **L5** | 랜덤화 공격자 일반화 | L4 이후 |

- **L4의 지위(명시)**: witness 자연 발생 ~10⁻³ 희소 + 판정 면도날(θ=0.9가 무-셰이핑 plateau 5/6 직상 + 2000-표본 MC CRN 민감성)은 **포획 물리의 정밀도 요구와 이진·MC 판정 설계가 결합해 형성된 난이도 — 두 요소의 상대 기여는 미분리**((qqq-1) 정정: 판정 탓 확정도, 자연법칙 수용도 아님). 동결 유지 하에서는 프레임 협상 과제 성격 병존. **후속 논문 질문으로 승격**: "판정 면도날(θ 스케줄·MC 표본·그물 반경)을 완화하면 사다리가 어디까지 자라는가". 단 **불가능 증명도 없음**: obs-전용 단순 컨트롤러(brake/λ-brake)가 k=2~4 일부 셀에서 .8+ 실측(bank v2 validation Gate B 데이터) = 중간-k 물리는 열려 있고, 미해결은 도달성 인증 계기와 커리큘럼.
- **목표선(외부 리뷰 교정 반영)**: 보고서/학위 필요선 = **이미 충족(L0 + 벽 규명)**. 단 **저널 기준으로는 L0+B도 질문 재정의 하에서만 성립**("희귀 terminal event를 가진 협력 MARL에서 surrogate shaping과 terminal feasibility가 왜 분리되는가" — 본 부록 B-아웃라인 1~3절의 프레이밍) — **capture-method 논문의 필요선은 미충족**이며 최소 L1 양성(또는 강하게 계기화된 L1 음성)이 필요. **이번 여름 = L1 확보(최소) → L2 시도(목표)**, L3 초입 = 보너스. P1′은 어느 결과든 논문을 강화(L1 성공 = 최초 양성 / 실패 = 오라클-가능·학습-불가 분리 증거).

**Q-tier 필요선(외부 리뷰 채택; 목표 배분의 공용 기준):**

| 티어 | 필요선 |
|---|---|
| URP 보고서 | 현 확보분으로 충족(셰이핑 학습·벽 규명·방법론 체인) |
| 워크샵/진단 논문 | **teacher-free autonomous hybrid capture**(k=1 — MARL shaping + autonomous rule guard, zero 대비 paired>0.10, ≥3 seeds; learned fire는 필요조건 아님, (qqq-1) 갱신) **또는** 강하게 계기화된 L1 실패(오라클·단순컨트롤러 성공 ∧ zero 실패 ∧ 배선·탐색 감사 통과 ∧ 정책만 실패) |
| Q2 방법론 | **L2 oracle + learned 양쪽**: MARL shaping + autonomous guard로 k=1 성공 + rewind k=2가 동일 σ·판정에서 synthetic 대비 우월(comparator) + **rewind k=2에서 learned shaping 학습 성공**((qqq-1) hybrid 기준) + 5–10 seeds + held-out + on-manifold ablation |
| Q1 | + 일반성(L3 재귀 확장 or 다른 attacker family/환경/강한 baseline/다중 witness; nominal 필수는 아님 — "여러 조건에서 synthetic은 실패, trajectory-유래는 일관 확장"이면 성립 가능) |

- **L1 실패 시 1차 감사 체크리스트(사전 등재 — 실패 '해석'의 순서 규정이지 실패 런의 구제가 아님)**: L1은 자재 여유상 "넘을 수 있어야 하는" 과제이므로, FAIL 시 분기 결정 전에 다음을 감사한다: ① PBRS(Φ)와 paired-Δ 목표의 정렬 ② shared limiter actor의 역할 분화(에이전트별 행동 분산·one-hot 의존) ③ action 스케일/해상도 ④ teacher→free 전환 역학(optimizer 상태·분포 이동) ⑤ obs/action 배선 스모크 ⑥ exploration(log_std·엔트로피 궤적). 감사 결과 = 분기 결정의 입력(구현 결함 발견 = "측정기/구현 실패" 계열로 기록, 신규 사전등록 실험의 근거).
- **제4병목 — RL-필요성(외부 리뷰 채택, 병목 목록에 정식 등재)**: bank v2 validation에서 obs-전용 단순 컨트롤러가 d1 brake .85/.79·lam20 .89/.84 — **정책이 zero만 이기고 이 선 아래면 "학습 가능성 증거 ≠ RL-필요성 증거"**("단순 감쇠 컨트롤러로 되는 문제에 왜 MAPPO인가" 공격면). 대응: sealed judgment에 brake·lam20 진단 arm 기록(docs/21 v0.3.2), 논문 클레임 트리에 정책 vs 단순 컨트롤러 비교 보고 의무. RL-방법 클레임 조건 = 유의 우월 or 역할 분화/강건성/긴 horizon 우월 증거; 미달 시 논문 중심 = predecessor construction·failure diagnostics(현 B-아웃라인과 합치). 현 단계 MAPPO 정당화 = 적과의 전략 게임이 아니라 **방어측 4+1 이종 협력**(중앙 critic·joint credit)임을 명시.

**공격자 사다리 A0–A5(외부 리뷰 채택; 현재 위치와 후속 로드맵):**

| 단계 | 공격자 | 지위 |
|---|---|---|
| A0 | 정속 직선 | — |
| A1 | 사전 회피 궤적 | — |
| A2 | **현재**: 상태 반응형(목표 지향 + 국소 회피/반발 + commit-반응 회피 강화 + 에피소드별 가족 랜덤화) | P1′·rewind 검증에 적정(실패 원인 분리) |
| A3 | receding-horizon **cost-aware MPC**(J_A = 타격 + 방어 비용 강요 − 피포획) | **후속 캠페인 1수** — "fixed-script exploit" 비판 방어, 방법론 논문 강화 |
| A4 | learned adversarial attacker | Q1급; 기존 **exploiter probe** 계획(방어자 freeze + adversary 학습)과 정렬 |
| A5 | population/self-play | 최종 단계(비정상성 관리 필요) |

- 원칙: **이번 캠페인은 A2 고정**(공격자 = 동결 env 계약의 일부; 지금 A3+를 넣으면 실패 원인이 술어 면도날/학습 설계/적 적응 중 어디인지 분리 불능 — 외부 리뷰도 동의). 순서 = A2에서 L1·L2 개통 → 단순 컨트롤러 대비 확인 → A3 MPC → A4/A5. "적응 공격자에 대한 방어" 클레임은 A3+ 이후에만.

**§6-보론 (2026-07-19, P1′ 판독 후 비준) — hybrid 아키텍처 + 스캐폴드 레벨 재정의 + 2-모드 연구 프로토콜:**

- **P1′ 판독 요지**: F0 1.00 ×3 / **L1 = 캠페인 최초 재성형 학습**(위 표) / J1 = 전 seed cap 0 즉사 — 기전: F0(d0 = reset-clean)가 가르친 것은 조건부 발사가 아니라 **always-fire 습관**이고, 단발·발사=종결 구조에서 v_soft≥θ 첫 표본(p_feas 미성립)에 조기 커밋 → 성공 중이던 shaping 궤적을 정책 스스로 전부 삭제(seeds 0/2; seed 1은 무발사 진동 = 반대 어트랙터). **재성형 실패가 아니라 learned one-shot trigger 결합 방식의 실패.**
- **hybrid 아키텍처 결정**: 최종 구조 = **MARL cooperative shaping + rule-based autonomous terminal guard**(fire ⇔ v_soft≥θ ∧ p_feas>0; obs-전용 — v_soft=obs[−3], p_feas=obs[−1] = 동결 관측 계약 내 자율. 실계 이식 캐비앗: 두 값의 onboard 추정기 필요 — 별도 명시). 근거: 본질적 학습 대상 = 4기 협력 셰이핑이고, 단발 비가역 종말 행동은 검증 가능한 가드가 시스템적으로 자연스러움. **learned-fire 실패는 폐기물이 아니라 hybrid 선택의 근거 증거**(clean-only bootstrap → always-fire bias / one-shot false positive의 궤적 삭제 / continuous 협력 + irreversible binary의 동시 PPO 불안정). 중단: F0 커리큘럼 단계 유지·fire-head 반복 튜닝·distill 필수화("궁금하면 부가 진단"으로만).
- **스캐폴드 6-레벨 재정의(레벨 3 교정)**: 1 Scaffold feasibility(oracle/teacher 하 성공 가능) → 2 Scaffold learnability(해당 분포에서 셰이핑 학습) **[P1′ L1로 달성]** → **3 Autonomous scaffold replacement**(특권 개입을 "learned로 대체"가 아니라 **실구현 가능한 자율 메커니즘으로 대체** — rule guard 포함) → 4 Horizon extension(rewind) → 5 Nominal transfer → 6 Mission success. 각 스캐폴드는 도입 이유 + **제거(대체) 조건** 명부 의무 — 제거되지 않는 스캐폴드는 방법이 아니라 새 문제 정의.
- **2-모드 연구 프로토콜(방법 전환 비준)**: **Discovery**(핵심 가설 직접 시험·1–3 seeds·dev-only·짧은 로그·치명 자유도만 고정) / **Confirmation**(양성 신호 후에만 동결·통계·sealed·감사). Discovery에서도 지키는 최소선 = 판정 J·평가 경로 동결, sealed류 1회 소진, seed 대장 비재사용, 증거 테이블 기록. 모든 계획 말미 의무 질문 = **"이 실험이 통과하면 원래 문제 해결력이 무엇만큼 느는가."**
- **클레임 사다리(갱신)**: ① 확보 — "MARL 리미터 정책이 action-necessary 전임자에서 행동-유발 국소 capturability 셰이핑을 학습한다"(L1) ② 가드 평가 성공 시 — "학습된 협력 셰이핑은 검증된 terminal guard와 결합해 자율 포획으로 전환된다"(end-to-end 국소 포획 양성) ③ rewind k=2 성공 시 — "실궤적 유래 전임자가 폐형식 합성보다 강건한 커리큘럼 기질이다"(Paper A 척추). shot의 learned/rule 여부는 핵심 기여와 무관 — 역할 분담(MARL = 협력 셰이핑 / guard = 비가역 종말 행동)이 오히려 선명.

**§6-보론-2 (2026-07-19 판독; 동일자 3자 정정 (qqq-1) 반영) — 현행 horizon-extension 경로 닫힘 + 미검 명제 분리:**

- **경로별 상태(정확 표기)**: ① synthetic k≥2 predecessor(A-3d 폐형식) = **음성**(σ-validation 전멸) ② witness 근방 2-step recoverability(A-3c U-1) = **음성**(r@2+ ≡ 0) ③ d1-궤적 rewind k=2(A-3e 수확) = **구조적 생성 불가·미판정** — F_hist={2:195}: d1 궤적에 d2 구성용 과거 이력 자체가 부재. **가설 기각이 아니라 실험 식별 불능**(on-manifold rewind는 검정되지 않음) ④ nominal→shell 접근 회랑 = **미검** — nominal 0/500 무발사는 d1-분포 학습 정책의 nominal transfer 실패 증거이지 회랑 부재 증거 아님 ⑤ 재귀 ladder = **현 경로 blocked, 일반 falsified 아님**.
- **종합(채택 문구)**: "현행 synthetic 및 d1-수확 기반 horizon-extension 경로는 닫혔으나, nominal 접근 회랑과 더 긴 실궤적 기반 predecessor의 실존은 미검이다." 세 결과는 동일 가설의 독립 3검정이 아니라 **분석·합성·학습 경로에서 각각 확인된 세 종류의 horizon-extension 장애**(서로 다른 명제의 측정 — "3중 독립 증거" 표현 철회).
- **연구축 2분리((qqq-1))**: **축1 = A2 하 접근 회랑 실존 검사** — trajectory optimization / MPC oracle / scripted corral / direct shooting(회랑을 확인하는 도구들). **축2 = 강한 공격자 하 MARL 필요성** — A3 cost-aware MPC → A4 exploiter → self-play(회랑 도구 아님 — 난도 상승축). A3를 회랑 질문과 같은 선택지로 배치하지 않는다.
- **후보 경로(방향 결정 슬롯, 09 (qqq)/(qqq-1))**: ① 축1 회랑 실존 프로브(discovery) ② 축2 껍질 재무장(A3/4+1) ③ B-fork(공통 fallback). 어느 경로든 자산 불변: L1 재성형 + hybrid Level-3 자율화 + 세 종류 장애의 특성화(장애 각각의 명제 구분이 곧 논문의 정직성).

**B 아웃라인 뼈대(사다리가 곧 논문 구조; 병행 준비 조항의 실체):**

1. 문제 정식화(양치기 last-mile C-UAS) + **L0 결과**(셰이핑 학습·mix ablation·비용-실명).
2. capture-unlock 시도의 체계적 실패 연대기 — A-1~A-3d 각각의 기전 규명(docs/12 §6 증거 테이블 = 본문 표).
3. **벽의 정량화**: 면도날 술어(공간 0.05–0.2 m × CRN 이중 면도날; 명제 N plateau-θ 구조) + **오라클 σ-감쇠 곡선**(bank v2 validation 7셀 표 — 특권 컨트롤러도 k≥2 불가) + obs-컨트롤러 대비(Gate B 8종 데이터: 일부 셀 .8+ = 물리 개방성).
4. **방법론 기여**: 사전등록 2-게이트 파이프라인 — action-necessity draw-필터, 4조건 독립 validation, 측정기-실패/가설-실패 분리(RT 게이트), 감사 가능한 3자 검토 체인.
5. **[P1′/rewind 결과 슬롯]**: L1·L2 결과 대입 — 양성이면 "학습 가능성의 경계", 음성이면 "학습역학 분리 증거" + synthetic-vs-rewind comparator 그림.
6. 시사점·후속: L4 승격 질문(판정 완화 스케줄), C-UAS 설계 시사(발사 게이트의 노이즈 민감성).
