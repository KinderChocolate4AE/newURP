# 87 — 연구 상세 계획 (docs/86 §8 의 실행판, 2026-09-03)

> **작성 경위**: docs/86 §8 (Paper 1 질문 + 결과물 6종) 을 13-agent 워크플로로 확장 — repo 실측 (정본 plan·규율 docs·코드 인프라·results 재고·최근 노트) 5종 → 섹션 초안 5종 → 3중 적대 검증 (규율 감사·실현성·완결성) 49 finding (BLOCKER 4 · HIGH 14) 전부 반영한 종합본. **이 문서가 주차 달력의 단일 정본** — 다른 문서·노트의 일정 표기는 전부 이 달력의 파생.

---

## §0. 명명·전제 (계획 전체 적용)

**명명 매핑표 (3중 충돌 해소 — 무접두 "R1"~"R4" 사용 금지)**:

| 이 계획의 결과물 | docs/81 의 R1~R3 | docs/83 의 R3/R4 |
|---|---|---|
| **paper-R0** modality 분리 복원 · **paper-R1** 충분조건 (별칭 prop1) · **paper-R2a** π-grid · **paper-R2b** 협력 경계 · **paper-R3** 역할 귀속 · **paper-R4** 설계 사슬 | **repo-R1~R3** = repo 위생 pass (provenance / semantic rename / derived-assert) | **계약-R3/R4** = sham-net · 근접거리 측정 계약 |

- claim registry 행은 기존 **C0xx 연번 계속** (C044~). figure id 는 `paper-R2a-F1` 식.
- **"arXiv v0" (docs/81·84 어휘) = memory 앵커 (08-11) 의 "arXiv v1"** — 이하 v0 로 통일.
- 적대자 사다리는 코드 계보 (attacker_ladder.py) 정합인 **A-명명**: A1~A3 = 기존 scripted family, **A4 = RL 학습 공격자** (유일한 최적화 층, falsifier 규율 하). "L0~L4" 명명 폐기.
- **v0.7 게이트 처분표** (supersede 된 v0.7 의 열린 ledger 정리): T0 → **T0-lite 로 승계** (anchor 2점 수치 대조 표만, W5) / N3 (E_req w-fit) → **pivot 으로 소멸** / Δ4 (HAPPO vs MAPPO) → **B2 stop rule 통과 시 재결정** / Δ3 (B-6 selection) → **paper-R3 의 selection arm 으로 승계**. CLAUDE.md 의 "W5 self-play 사전 착수" 규칙은 **supersede 된 v0.5 좌표계의 유산 — 본 계획에서 무효**.
- **주간 예산 (정직 재표기 + 트랙 분리 규칙, 2026-09-03 개정)**: 총 10~14h. **연구 트랙(Track R) 보호 시간 = 주 5h 하한 — 문헌 집필 주간에도 삭감 금지** (시험 주만 예외). 문헌 트랙(Track W)은 **AI 초안 + 사용자 검증·승인의 timebox 3~5h** — 사용자가 문장을 처음부터 쓰지 않는다 (수치 대조·금지표현 확인·승인이 사용자 몫). 운영 오버헤드 1~2h. human lane 읽기는 소비처와 겹치면 1회로 계상 (예: 고전 유도 읽기 = Related Work 재료 — 같은 활동).
- 상시 규율: science ↔ hygiene 커밋 분리 · 과거 JSON 소급 수정/backfill 금지 (sidecar 만) · canonical proximity = `*_r4` 계열만 · `feasible` 3분법 (baseline-achievable / aiming-limited / kinematically infeasible) · "12군 완비"·"세계 최초"·"두 독립 계측 검증" 금지 · χ=1 / cone ceiling χ* / empirical 3수준 혼용 금지 · 결과 JSON `encoding="utf-8"` 명시 저장.

## §1. 질문과 결과물 (docs/86 §8 승계)

**Paper 1 의 질문**: 단독 net 포획이 물리적으로 성립하지 않는 위협 영역 (χ > χ*) 에서, 협력 조향은 성립 경계 자체를 어디까지 밀어낼 수 있는가 — 그 확장량은 어떤 무차원수의 법칙으로 정리되는가?

**URP 보고서의 기본 골격 = paper-R2a regime map + paper-R1 (prop1)**. **paper-R2b/R3 는 stretch** — G3 (W8 말) 3조건 전부 통과 시에만 URP 에 IN (검증 finding: B0 봉인 11/7 이 가장 깨지기 쉬운 조건이므로 R2b-OUT 이 기본 시나리오이며, 그래도 보고서가 완결되도록 골격을 뒤집었다). paper-R4 는 재료 있을 때만 (G4).

## §2. 순서 사슬 (docs/81 — 개정 없이 위반 금지)

```
[오늘] KSAS 마감일 확인 → P1 freeze (tag ksas-2026-submission-freeze) → P2 제출
→ repo-R1~R3 pass → A0 gate (θ sensitivity 재실행 + jink scope + 5C hygiene + exit 문장)
→ arXiv v0 공개 (≤10월, 교수 컨펌 필수 불변)
→ B0 world-contract 봉인 → B2 scripted 협력 → stop rule → (통과 시에만) MARL/A4
```

- **A0 재정의 (검증 finding)**: frozen record 에 θ 판정용 연속량 (v_shot_soft) 이 없고 θ=0.9 는 런타임 발사 게이트이므로 **offline 재라벨 불가 → 신규 prereg 재실행 캠페인**: 3θ {0.85, 0.90, 0.95} × 2 arm × 2,700 = 16,200 ep ≈ 직렬 6.7 h (1.49 s/ep 실측) — 랩 서버 밤샘 1회. W1 에 30분 대안 확인 (소프트 점수 저장된 캘리브레이션 계열 캠페인 존재 시 원안 복귀). θ 불안정 시 재선택 금지 — 별도 calibration prereg 분기 (+2주 각오), 우회 서술로 공개 불가 (docs/81 개정 절차 없이는).
- **협력 실험 (paper-R2b/R3) 은 B0 봉인 이후만. A4 학습 실행은 B2 stop rule 통과 이후만** — "지금 사전 착수" 는 어떤 형태로도 금지 (BLOCKER 반영). 이번 학기 적대자 트랙 상한 = A-family 범위 선언 문서까지.

## §3. 타임라인 — 연구 트랙 (R) / 문헌 트랙 (W) 분리 (2026-09-03 개정, 단일 달력 정본)

> **분리 원칙**: 문헌 작성이 연구를 늦추는 구조를 끊는다. 두 트랙은 goal·게이트·주간 시간을 따로 갖고, 서로를 기다리지 않는다. **문헌이 연구를 막는 지점은 docs/81 사슬의 단 하나 — "arXiv 공개 → B0/B2 해금"** (§3C). R2a·prop1 은 이 사슬에 묶여 있지 않으므로 문헌 일정과 무관하게 자기 게이트로만 진행한다 (기존 계획이 R2a 를 W6 으로 미룬 것은 의존성이 아니라 시간 충돌이었다 — 실험은 서버가 돌리므로 충돌 자체가 허상). 문헌 트랙의 초안은 AI 가 쓰고 사용자는 검증·승인만 (timebox).

### §3A. Track R — 연구 (보호 시간 주 5h 하한, 문헌 주간에도 삭감 금지)

**Goal: ① R2a collapse 판정 (G3, ≤10/30) ② prop1 K1 (≤10/31)·K2 (≤11/15) ③ (조건부) R2b 1차 측정 ④ A-family 선언.**

| 주차 | Track R 작업 | human lane (연구분) |
|---|---|---|
| **W2** 9/15~9/21 | **H-4** (랩 서버 접속·seeds/m4_pilot — sweep 서버 가용 확인 겸용) + **A-family 범위 선언 문서** (A0 jink scope 의무 겸용) | 차원해석 (W1 시작분 계속) |
| **W3** 9/22~9/28 (추석) | **paper-R2a lattice 선봉인** (AI 초안 + 승인 ~1h, §4 스펙 — 순수 문서라 감량 주에 적합) + **Stage 0** (frozen 2,700 재집계, 0비용, 로컬) | MBT 2005 (정의부 + framing 3문장) |
| **W4** 9/29~10/5 | **실행기 조립** (r2a_grid.py + RED-first 테스트) + **Stage 1 착수** (선행: repo-R1 ✓ W2 · lattice 봉인 ✓ W3 · H-4 ✓): 구현 3종 궤적 육안검사 (viz-first) → spot-check 6셀 (서버 밤샘) + **m4_env 포획 판정부 정독 2h** (prop1 Lemma 2 선행) | prop1 가정 세트 초안 |
| **W5** 10/6~10/12 | **Stage 1 kill 판정 (금)** → 통과 시 **Stage 2 투입** (서버 ~21h, 자동) + prop1 **Lemma 1 손증명** | Ames tutorial §II–III |
| **W6** 10/13~10/19 | Stage 2 완료 → **Stage 3 투입** (경계 밴드 + family worst-case) + prop1 Lemma 2/3 + 정리문 v0 | 2509.08460·2507.10249 문법 노트 |
| **W7** 10/20~10/26 (중간고사) | 서버 자동 진행 — 모니터만. Stage 6 cleanup (조건부) | 읽기만 |
| **W8** 10/27~11/2 | **Stage 2/3 판독 — collapse 판정 → G3 (≤10/30, R2b in/out)** + **prop1 K1 (≤10/31)**: 정리문 + Lemma 1–2 손증명 + **B0 봉인 반나절 스파이크** (G3 조건 ③ 재료) | R2a 판독을 상사성 언어로 (안목 노트) |
| **W9** 11/3~11/9 | **G3-IN**: B0 봉인 완결 (하드라인 11/7, R2b 세계 선언 §7) → B2 착수. **G3-OUT**: prop1 Arm A 검증 (~25분 실행) 전진 | prop1 h(x) 구성 연습 |
| **W10** 11/10~11/16 | B2 + **stop rule 판정 (금 1회)** + oracle-lite 상한 arm (§7) + **prop1 K2 (≤11/15)**: Arm A 종결 또는 informal 강등 | MARL 기초 |
| **W11** 11/17~11/23 | **G3-IN**: paper-R2b 머니 피규어 1차 + paper-R3 selection arm (R2b positive 조건부). paper-R4 재료 수집 | MARL 계속 |
| **W12** 11/24~11/30 | **G4 (연구분): 보고서에 들어갈 과학 결과 확정** — 이후 신규 실험 금지. paper-R4 조건부 | novelty 한 문장 최종화 |

이후 (W13~W15) Track R 은 신규 판정 없음 — 결과는 Track W 의 보고서로 넘어간다.

### §3B. Track W — 문헌 (AI 초안 + 사용자 검증 timebox 3~5h/주; 있는 결과만 쓴다, 연구를 기다리게 하지 않는다)

**Goal: ① KSAS 제출 (9월 초) + 발표 ② arXiv v0 공개 (10월 중순 사수) ③ URP 보고서 + AIAA abstract (12/18).**

| 주차 | Track W 작업 |
|---|---|
| **W0** 9/3~9/7 | **① KSAS 마감일·개최일·발표형식 공식 확인 (오늘 즉시** — 마감 <9/8 이면 축약 경로: 오타 + freeze tag + 제출, registry 는 제출 후**)** ② A0 대안 30분 확인 ③ 교수 미팅 요청 발송 |
| **W1** 9/8~9/14 | KSAS 형식 마감 (오타 · ver6 숫자 T0-legacy 대조 · 분량 · registry C041/C042/C043 3값 · PUB-01 · **freeze tag**) → 제출 (P2) → **G1** |
| **W2** 9/15~9/21 | **repo-R1~R3 pass** + F-1 (AST 수리) — 사슬 위생 (arXiv 선행 의무) + **A0 재실행 캠페인** (스크립트 AI + 서버 밤샘 1회 — arXiv 게이트용 사슬 실험) |
| **W3** 9/22~9/28 | **A0 판독 + exit 문장 (하드라인 9/28)** + docs/84 개정안 3건 묶음 (turn-limited·BMD·η-tercile) + 교수 미팅 ① 확정 (fallback = 서면 비준: 개정안 1단락 + 질문 ≤3) |
| **W4** 9/29~10/5 | **arXiv 집필 1/2** (AI 초안: Results·Feasibility 역순 / 사용자: 수치 검증) + **교수 미팅 ① (scope 컨펌 ≤10/3)** → docs/84 append 커밋 + endorsement 확인 |
| **W5** 10/6~10/12 | **arXiv 집필 2/2** (Intro/Related 20~30편 — 고전 유도 읽기와 동일 활동으로 계상) + 수치 대조표 + 금지표현·용어 grep + T0-lite anchor 대조표 + 재현 패키지 → **초고 교수 송부 (≤10/10)** |
| **W6** 10/13~10/19 | **교수 미팅 ② (원고 컨펌) → G2 → arXiv v0 공개 (10월 사수)** — §3C: 이 시점에 B0/B2 해금 |
| **W7~W11** | 휴지 (KSAS 발표 예외: **개최 주 −2주에 발표자료 + 리허설 삽입, 그 주 양 트랙 감량**) |
| **W12** 11/24~11/30 | **G4 (문헌분): 보고서 scope lock** (Track R 의 W12 확정 결과만 수록) + URP 제출 요건 공식 확인 |
| **W13** 12/1~12/7 | 보고서 80% 선완성 (AI 초안 + 검증) + AIAA abstract 초안 + 교수 미팅 ④ |
| **W14** 12/8~12/14 (기말) | 기계적 마무리만 (조판·서지·재렌더). 신규 판정 금지 |
| **W15** 12/15~12/18 | **제출 (12/18)** |

### §3C. 트랙 간 동기화 지점 (이 4개 외에 서로 기다리지 않는다)

1. **repo-R1 (W, W2) → R2a Stage 1 가능** — 신규 캠페인의 manifest 스탬프 선행 (provenance 규율).
2. **arXiv v0 공개 (W, W6) → B0/B2 해금** — docs/81 사슬. **문헌이 연구를 막는 유일한 지점**: 교수 컨펌 지연으로 공개가 밀리면 B0/B2 만 같이 밀리고, R2a·prop1 은 계속 간다 (G3-OUT 대비 골격이 이미 R2a+prop1 이므로 보고서 무손상).
3. **Track R 의 W12 확정 결과 → 보고서 scope lock (W, W12)** — 문헌은 확정된 것만 쓴다. 미확정 결과를 기다리며 집필을 미루지 않는다.
4. **KSAS 발표 주간** — 개최 주 −2주 규칙, 양 트랙 공통 감량.

prop1·arXiv 의 자체 달력은 없다 — K1/K2 = §3A 의 W8/W10, arXiv 일정 = §3B 가 유일 정의.

## §4. paper-R2a — Buckingham-π grid (상세)

**주장 (사전 선언)**: "단독 (hold arm) net 포획률 p 는, 선언된 conditioning π 를 고정하면, 차원 변수에 오직 (χ, η) 를 통해서만 의존한다." 대상 세계 = **legacy 24 m 회랑 한정** (frozen curve 계약과 동일 — scale_v2 수치와 같은 곡선·같은 주장 혼합 금지).

- **π 후보군**: `lattice_spec.py` 등록 12군이 정본 ("12 registered groups" 표현만). plotted = χ, η. 제3 후보 = λ = R_max/ρ (α 와 연동 — 단일 "cone geometry" 축, Stage 4 조건부). conditioning pin = κ, μ, ν, N (CAPABILITY_RATIOS 연동), dt/τ. 미등록 3군 처리 선언: k_f·τ = τ 구현에서 재스케일 pin / r_lat/ρ = 값 선언 후 pin / T_reach/τ = derived 로 정리.
- **적대자 = ~~A1 단일~~ → A2-reactive 단일 (grid 전면; 2026-09-05 D-2 개정 — Stage 0 원천 `curve_hold_reactive.json` 이 A2-reactive (jink 0.6 · route 0.5 · sense 30, sidecar manifest + exact replay 검증) 이므로 confirmatory world 를 설계 데이터의 세계와 정합. 근거·감사 = `docs/review_prompt_r2a_pins_evasion.txt`)** — family worst-case 는 **Stage 3 경계 밴드 셀 (~15개) 에만** 적용 (+18,000 ep, 직렬 +7.5h). 이 결정은 lattice 봉인 문서와 §5 적대자 트랙에 동일 문구로 기재 (상호 모순 해소).
- **Stage 구성** (앵커 1.49 s/ep, 안전계수 ×1.5, 랩 서버 tmux+ntfy+100ep 체크포인트, `--cells` 샤딩):
  - **Stage 0** (W5, 0비용, 로컬): frozen curve 2,700판 (χ,η) 2D bin 재집계.
  - **Stage 1** (W6, kill test): 구현 3종 × 경계 걸침 6셀 × n=400 = 7,200 ep ≈ 4.5h. **spot-check 셀은 봉인 격자 위의 점만** (η∈{2.1, 3.9} — 격자 밖 점 금지) **그리고 전 구현 공통 유효 bracket 내부만**.
  - **Stage 2** (W7, 본 grid): χ 12점 × η 7점 × A1 × n=400 = 33,600 ep ≈ 21h (8샤드 ~2.6h).
  - **Stage 3** (W7~8): 경계 밴드 셀 × 구현 2종 + family worst-case = ~30,000 ep.
  - **Stage 4** (조건부): λ 3레벨 × 경계 6셀.
- **⚠ THREAT_BRACKET 정합 (검증 finding — 수치 확인됨)**: a∈[11,78]·v∈[8,30] 는 draw 계약. 구현별 pin 은 이 bracket 을 이탈한다 (R-tau: χ<0.65 영역 전부 a<11 / R-rho: χ>1.5 에서 a>78, η>3.9 에서 v>30). **lattice 봉인 문서에 구현별 유효 (χ,η) 부분격자를 계산·명기하고**, Stage 1/3 셀은 전 구현 공통 부분격자 내부로 제한. bracket 밖 pin 이 필요해지면 "본 캠페인은 pin 계약이며 범위 X 를 새로 선언한다" 를 결과 열람 전 봉인 문서에 명시 (draw 계약과 구분). "bracket 이탈 없음 assert" 문구 폐기.
- **구현 3종**: R-ref (τ0.30, ρ1.77) / R-tau (τ0.45 — dt·k_f 재스케일 pin, T_reach/τ 교란) / R-rho (ρ2.30 — half_angle 연동 재계산, κ pin, λ·σ_* 교란). Tier A = 완전 상사 1셀 (sanity — 실패 시 하네스 버그, 중단) / Tier B = 부분 구현 (진짜 collapse test — "그 교란에도 경계가 둔감하다" 가 과학적 주장).
- **viz-first (프로토콜 명문화)**: Stage 1 착수 시 구현 3종 × 2~3 에피소드 **궤적 육안검사가 collapse 수치 판독의 선행 조건**. Tier A 실패 시에도 수치 재실행 전 궤적 먼저. (스케일 결함 6주 미발견의 교훈이 겨누는 지점이 정확히 여기다.)
- **collapse 판정 (단일 정의원 = `r2a_lattice.py` 가 생성·hash 하는 `artifacts/r2a/lattice_r2a.json` — 이중 정의 금지, G3 는 이 기준을 인용만)**: ① 셀: Newcombe 95% CI 가 0 포함 or |Δp̂|≤0.10 → PASS ② 전역: Tier B ≥80% PASS 그리고 |Δχ₅₀|≤0.05 (bootstrap CI) ③ 실패 시 CONDITIONING_ORDER 진단 먼저 — sign-consistent |Δp|>0.20 인 교란 π 를 승격 후보로. 어휘: "consistent with (χ,η) dominance" 만.
- **수락/kill**: 성공 → R2b 좌표 잠금. 부분 성공 → (χ,η,λ) 3축 재등록 (새 hash). kill (χ 단조 경계 부재 / 지배 π 격리 불가 / sign 없는 |Δp|>0.3 산포) → π-축소 실패를 그대로 보고, R2b 는 차원 좌표 + 동결 세계로 후퇴. **null 도 결과** — "π 로 안 닫히는 잔여 차원변수" 지도가 보고서 finding.
- **코드** (신규 실코드는 실행기 1개): `r2a_lattice.py` (~60줄, 봉인) → `tests/test_r2a.py` (RED-first: pin 왕복 bit-exact · co-scale 후 pin π 불변 · 판정 함수 · hash 안정성) → `r2a_grid.py` (~150줄, coarse_pilot pin 공식 + att_speed=η·ρ/τ + 체크포인트/샤딩) → `r2a_collapse.py` (~80줄, Wilson/summarize_curve 는 curve_sweep 에서 import) → `paper_figs.py` 확장 (F1 regime map — frozen 오버레이는 "별도 계약 자료, 정합 확인용, 수치 주장 불포함" 캡션 + 회색 반투명, 또는 부록 분리 / F2 collapse plot).
- registry: C044 (경계 위치 χ₅₀(η)+CI) · C045 (collapse 판정) · C046 (provenance + legacy 한정 caveat).

## §5. 적대자 트랙 (이번 학기 상한 = 선언 문서)

- **A1~A3 (scripted family)**: 코드 완비 (`attacker_ladder.py` + `AttackerSpec` + `LAMBDA_PRESETS`), 신규는 **범위 선언 문서** (W2, A0 jink scope 겸용) + worst-case 집계 스크립트 ~50줄뿐. **grid 적용은 §4 결정대로 Stage 3 경계 밴드만.**
- **A4 (RL 학습 공격자)**: 관측·행동·보상 3종 신규 선언 + torch/랩 서버 필요. **B2 stop rule 통과 이전 학습 실행 0회** (docs/81). 이번 학기는 **준비 문서 (선언 3종 + 어댑터 골격 코드, 학습 run 없음) 까지만 — 그것도 W10 timebox**. 본 실행·self-play (S13/post-L2)·PFSP 전부 arXiv v1 이후.
- 주장 강도 사다리 (논문 문장): A1 단독 → "선언 후 고정된 family worst-case" (반론 8할 차단, **이번 학기 도달점**) → A4 (예산 X exploit 하한) → co-adapted (Paper 1+).
- held-out: family 중 학습 미사용 spec 예약 (v0.7 D.3.2 승계).

## §6. arXiv v0 (10월 공개)

- **scope = docs/84 동결 9-절 그대로.** paper-R0 (modality 복원 — 0.240 vs 0.006) 는 scope 안이자 **의무** (첫 그림 = modality curves 동결). χ 문단 scope 안.
- **개정 3건 묶음** (원문 무수정, 날짜 박힌 append 블록 + 교수 비준 1회 — W3 작성, W4 미팅 ① 비준 후 커밋): ① turn-limited 소단락 (frozen artifact 재판독 한정, v_crit≈8.14, §7 Robustness) ② BMD launch-envelope Remark 1문단 (§4 Feasibility 내 — Related Work 소절 신설 금지) ③ η-tercile 값의 Results 승격 (C043 등록 선행; 부결 시 "0.763 은 η 에 주변화" 각주 1문장까지만).
- **v0/v1 경계 규칙 한 줄**: frozen artifact 의 재판독·재집계까지만 v0 — 신규 rollout 1판이라도 필요하면 v1/병렬 branch. paper-R1·R2a sweep·R2b·A4 전부 v0 밖. **v0 방어선**: paper-R0 + χ/χ* + 폐루프 attainability + E2-B/E1e 만으로 spine 완결 — 공개 지연의 정당 사유는 A0 실패·교수 컨펌 불발뿐.
- 영문 품질: χ 정의 문단 = 인용 자산 (자립 문단·one-sided 명문·0.808 inscribed + 0.823 각주·국문 확정→영문→백번역 대조). "capture-latency evasion number" 유일 명칭. 원고용 영문 금지표현 checklist 별도 1파일 (hygiene 스캔은 .py 만 커버하므로).
- 제목 후보: ① *Physical Interception Does Not Imply Capturability: …* ② *A Capture-Latency Evasion Number for Aerial Net Capture: …* ③ *When Can a Net Catch a Drone? …* (철자 최종 확인 — KSAS 오타 교훈).

## §7. paper-R2b/R3 최소 사전등록 (G3-IN 시 즉시 실행 가능하게)

- **세계 선언 (B0 봉인 문서 첫 절)**: R2b = **legacy regime 한정 1차 측정** (R2a 와 좌표·regime 동일성). scale_v2 확장은 별도 캠페인. **단독/협력 경계는 동일 세계·동일 적대자·동일 판정** — B0 exit 조건에 명기.
- **최소 설계**: R2a 확정 경계 셀 6개 × {단독, rule-based 협력 (curve_intercept 하한 재사용)} × n=400 = 4,800 ep ≈ 직렬 2h.
- **oracle-lite 상한 arm (null 2분기 판정용 — v0.7 Δ3/B-6 승계)**: 경계 6~10셀 × n≥100 으로 p2prime solver 확장 (기존 n=7 은 통계 불가). 판정문 사전 등록: "oracle 도 못 밀면 진짜 null ('협력 대신 τ 단축') / oracle 은 미는데 scripted 가 못 밀면 방법 문제 (Paper 1 에서 학습 협력으로)". **양쪽 다 논문이다.**
- **paper-R3**: 이종 vs 동종 rule-based + **selection-only arm** (조향 없이 할당만 — "selection 으로 충분하지 않냐" 차단). R2b positive 조건부.
- Δ_coop(Π) = P_coop − P_single 층은 docs/84 §7 대로 신규 작업 — 기존 재료 재구축 금지.
- **[2026-09-05 amendment — append-only]** §7 execution design superseded by **B0 seal `e3fd7800003d34e1`** (`artifacts/r2b/b0_world_contract.json`; 사유 = C045 PARTIAL_3D 로 2-D 좌표 잠금 무효 + "oracle 상한" 어휘 폐기 → sealed-budget optimization achievability benchmark 로 재정의). historical text retained; 승계 원칙 (동일 세계·적대자·판정, 단독 arm 신규 실측, null 2분기 격하 어휘, 머니 피규어 정의) 은 B0 에 명기.

## §8. 게이트 (전부 사전 선언 — 판정은 금요일 감사, 판정형 제목 기록. [W] = 문헌 트랙, [R] = 연구 트랙)

- **G1 [W] (W1 말)**: KSAS 제출. PASS = 오타 + 최신 freeze 숫자 + 분량 + tag. 마감 <9/8 발견 시 W0 축약 경로.
- **G2 [W] (W6, arXiv 공개)**: PASS 4조건 — ① A0 exit 문장 ② docs/84 동결 scope (개정은 비준분만) ③ Ablation A gap 수치 정합 ④ **교수 컨펌 — 어떤 경로에서도 생략 불가 (불변)**. scoop 대응은 scope 최소본 준비 + **컨펌 fast-track 요청** (자료 1p + 질문 ≤3) 까지 — 컨펌 없는 공개 없음. 컨펌 자체가 불가하면 공개 연기 + scoop 리스크를 교수에 서면 보고 (앵커 결정 갱신은 교수 합의로만).
- **G3 [R] (W8 말, ≤10/30 — 핵심 분기, M1.2 상당. G2 지연과 무관하게 진행)**: paper-R2b IN 조건 3개 전부 — ① collapse 성립 (**판정 기준 = r2a lattice 봉인 문서 인용**) ② 지배 π 식별 + 경계 안정 ③ B0 봉인 11/7 완결 가능 (W8 스파이크 실측 근거). 하나라도 실패 → R2b/R3 는 arXiv v1 이후 이월, 보고서 = R2a + prop1 (기본 골격 그대로). KILL 아님 — collapse 붕괴 자체가 finding.
- **G4 [R+W] (W12 초)**: 보고서 scope lock + B2 stop rule 결과 인용 (판정 자체는 W10 금요일 1회). stop rule 실패 → MARL 전면 중단 + null 서사 (§7 oracle-lite 2분기 판정문으로).

## §9. Human lane (docs/86 §8 4과목 — 소비처와 시점 결속)

| 과목 | 주차 | 목표 (축소 명시) | 소비처 |
|---|---|---|---|
| 3 차원해석 | W1~W3 | Buckingham 원전 + Barenblatt 발췌 — "registered groups" 규율의 이론 근거 | R2a 착수 (W6) 전 완료 |
| 1 HJI/CBF | W2~W6 | MBT 2005 는 **BRS/viability 정의부 + framing 3문장** / Ames §II–III / 2509.08460·2507.10249 문법 노트 | prop1 을 내 손으로 (W4 착수 — 증명 본체는 초등 부등식이라 공부가 전제 아님, 서술 언어·리뷰어 방어용 병렬) |
| 2 고전 유도 | W4~W5, W7 | Zarchan 발췌 (PN/ZEM/launch envelope) → GCP → **Gavin & Bronz 한 줄까지** | arXiv Related Work + "BMD 는 옛날부터" 선제 방어 |
| 4 MARL | W10~W11 | MAPPO → HAPPO → PFSP — **감사할 수 있는 수준** (구현 아님) | stop rule 통과 시 Paper 1 |

병행 리듬 (docs/86 §7 주간화): 상시 3스레드 (코딩·글·읽기) / 30~45분 stuck → 종류 전환 / 아침 승리 조건 1개 + 무서운 것 오전 / **월~목 빌더 · 금요일 감사의 날** (게이트 판정·registry·판정형 노트 일괄) / 헤밍웨이 스톱 (마지막 10분 = 내일 첫 30분 한 줄) / stuck (c)형 (내가 못 답함) 은 금요일 모아 교수·TA 메일 즉시.

## §10. 교수 인터랙션 (미팅마다 그림 1장 + 질문 ≤3)

| 시점 | 안건 | 자료 |
|---|---|---|
| W2 (9월 중순) | KSAS 제출 보고 + 사사/저자 상의 + **P-5/spine 승인을 advisor 레벨로 명시 격상** (현재 TA 지지만 기록됨) | ver6 + 변경 요약 1p |
| **W4 (≤10/3) — 미팅 ①** | arXiv scope 컨펌 + **개정 3건 비준** + "Ablation A gap" 게이트의 현 frame 재해석 1줄 (0.240 vs 0.006 으로 충족 간주 여부) + 공개 범위 (코드/시드) | v0 draft 골격 + scope 표 1p + gap 수치 + 개정안 |
| **W6 (≤10/15) — 미팅 ②** | 원고 컨펌 = G2 ④ | 완성 초고 + 수치 대조표 |
| W9 (11월 초) — 미팅 ③ | R2a 판정 보고 + R2b in/out 권고 + B0/B2 착수 승인 + **R2a 결과의 공개 경로 결정** (v0 개정판 appendix vs 별도 short note vs Paper 1 보류 — 원칙 5 타임스탬프) | regime map 1장 + G3 판정문 0.5p |
| W13 (12월 초) — 미팅 ④ | 보고서 초안 + AIAA abstract + Phase 2 (Paper 1-J: TAES 1순위/AST 2순위) 상의 | 초안 2종 |

## §11. 위험 top 5

| # | 위험 | 완화 |
|---|---|---|
| 1 | **Scoop** (Gavin & Bronz 계열이 강체 net 에 τ 를 붙이면 우리 N1) | 10월 공개 사수 — 단 **교수 컨펌은 불변 게이트**: scope 최소본 + fast-track 요청으로 컨펌을 앞당기는 방향만 |
| 2 | **A0 θ 불안정** → arXiv 정체 | W2 재실행 캠페인으로 전진 배치 (밤샘 1회). 불안정 → calibration prereg 분기 + docs/81 append 개정 블록 절차 (우회 서술 금지) |
| 3 | **B0 봉인 지연** → R2b OUT | 기본 골격이 이미 R2a+prop1 (R2b 는 stretch) — OUT 이 나도 보고서 무손상. §7 최소 설계 사전등록으로 IN 시 2h 내 실행 |
| 4 | **랩 서버/torch 병목** | R2a 는 torch-free (로컬 fallback 가능). W2 H-4 에서 서버 가용 선확인. A4 는 학기 밖 — 서버 선점 낭비 금지 |
| 5 | **학기 부하·심리 소모** | 주 10~14h 총예산 (오버헤드 포함 정직 계상) + W7/W14 buffer + §9 리듬 + 보고서 W13 80% 선완성 |

## §12. 감사 반영 기록

13-agent 워크플로의 3중 검증 (규율·실현성·완결성) 49 finding 처리: BLOCKER 4 (self-play 사전 착수 삭제 · G2 교수 컨펌 불변화 · 달력 단일화 · KSAS 마감일 W0 승격) 및 HIGH 14 (A0 재실행 재정의 · THREAT_BRACKET 부분격자 · grid 적대자 단일화 · R2b stretch 격하 + 최소 사전등록 · oracle-lite arm · arXiv 집필 2주 확대 · scope 컨펌 전진 · viz-first 명문화 · L1 선언 문서 배치 · KSAS 발표 규칙 등) 전부 본문 반영. MEDIUM/LOW 는 명명 단일화 (paper- 접두 + C0xx 연번) · 판정 단일 정의원 · docs/85 잔여 배치 (F-1/H-4/Stage 6) · T0-lite 승계 · selection arm · 재현 패키지 · endorsement 전진 · 주간 예산 재표기 · prop1 어휘 한정어 등으로 반영. 원 초안·finding 전문은 세션 워크플로 기록 (journal) 에 보존.

---

*정본 관계: 이 문서의 달력·게이트가 docs/86 §8 을 실행 수준으로 구체화한 것. docs/81 순서 사슬·docs/84 동결 scope 와 충돌 시 그 문서들이 우선하며, 본 계획은 그 안에서 움직인다. 갱신은 금요일 감사 세션에서 판정형 기록과 함께.*
