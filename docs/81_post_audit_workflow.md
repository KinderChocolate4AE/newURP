# 81 — Post-Audit Master Workflow (수치감사 후속 실행 규율)

- **일자**: 2026-08-13 · 근거: `artifacts/audits/environment_numeric_audit_2026-08-13.md` (판정: KSAS PASS WITH SCOPE CAVEATS / arXiv REQUIRES FIX / B2 REQUIRES FIX)
- **성격**: 감사 결과에 대한 **대응 전략 봉인** — 무엇을 언제 고치고, 무엇을 절대 고치지 않는가.
- **감사 심각도 재해석**: "결과가 무너졌다"가 아니라 **"repo가 연구 결과보다 빨리 복잡해지기 시작했다"**. FATAL NOW 0건, a\*=2ρ/τ² 사슬 생존. 위험은 validity가 아니라 provenance·semantics·contract 혼재.

## 0. 3-선 분리 원칙 (최상위)

```
① KSAS   = 지금 있는 evidence 를 출판 (최소 수정 후 freeze)
② arXiv  = numeric-contract debt 청산 후 확장
③ B2~    = 새로운 game model revision (contract 봉인 전 실행 금지)
```

+ 보존 원칙: **historical preservation first, architectural cleanup second.**
+ 커밋 규율: behavior-changing commit 과 hygiene commit 을 **절대 같은 commit 에 섞지 않는다** (`chore:`/`refactor:`/`test:` vs `science:`).

## 1. 절대 금지 목록

1. **감사 보고서를 보고 "전부 config 로 옮기자" 식 대규모 refactor 착수** — legacy SystemSpec / ratified M4 / v2·v3 / Gate 7 / Gate 10·11 계약이 공존하는 지금 공통화 강행 = "과거 실험이 실제로 뭘 실행했는지"를 잃는다.
2. **과거 결과 JSON 덮어쓰기 / 소급 reinterpret** — metadata 부족은 sidecar manifest(`X.json` + `X.manifest.json`)로 보완.
3. **legacy config 를 최신 config 로 "정리"** — 오래된 결과는 오래된 세계의 결과.
4. **모든 literal 의 무조건 config 화** — audit table 분류를 그대로 사용: CLAIM-CRITICAL→explicit / SCENARIO→manifest / DERIVED→compute+assert / NUMERICAL→내부 상수 / DEAD→격리 후 제거.
5. **θ=0.9 를 결과 보고 예쁜 값으로 재선택** — sensitivity 먼저, 불안정 시 별도 calibration prereg.
6. **진행 중인 T1 rerun 의 `_save()`/behavior 중간 수정** — shard 간 schema 분기가 더 나쁘다. 종료 후 sidecar.

## 2. Phase 사슬 (exit gate 포함)

```
[P0 T1 rerun 완료] → [P1 KSAS freeze] → [P2 KSAS 제출]
──── publication freeze ────
→ [R1 provenance] → [R2 semantics] → [R3 derived/assert]
→ [A0 θ+jink validity] → [arXiv v0]
→ [B0 world contract 봉인] → [B2 scripted]
→ mechanism? ─ NO → MARL 중단, 물리/control 논문으로 정리
            └ YES → [T2 stress] → [MARL@T1] → [MARL@T2] → [AIAA] → [T3/T4] → [Journal]
```

### P0 — T1 rerun 그대로 종료
- scientific behavior 변경 0. 2700/2700 완료 → shard merge 검증 → **sidecar manifest** 생성 (git_commit / campaign_id / threat_class=T1 / level=A2 / route_gain=0.5 / sense_range=30.0 / limiter_mode=hold / τ=0.30 / ρ=1.77 / episode_len=160 / 종료계약 F-flags / seed·shard 범위).
- 숫자 판독은 docs/72 사전 수용 규칙 그대로.

### P1 — KSAS 결과선 동결
- T1 판독 3-case 만 허용:
  - **A** boundary+aiming 유지 → T1 을 primary lineage 로, T0 는 mechanism-isolation.
  - **B** capture 하락·boundary 유지 → "reactive avoidance reduced baseline attainability while the boundary remained approximately stable" (reactivity 일반화 금지).
  - **C** 구조 붕괴 → 그대로 수용, 3-구간/aiming headline 하향, analytic χ + T1 곡선 중심 축소. **T0 의 더 예쁜 숫자로 회귀 금지.**
- 제출 전 처리 = 감사 §G 5건뿐: ① 78 m/s² 출처 (미확보 시 "declared upper threat bracket" 격하) ② T1 manifest ③ legacy↔rerun 계약 caveat 1문장 ④ pooled 분모 재확인 ⑤ stale docstring 2건.
- **θ sensitivity·B2 observability·T2 는 KSAS blocker 아님.**

> **★ P1 개정 (2026-08-13, docs/83)** — 산출물 감사가 조준 병목의 **인과 귀속 반증**을 발견하여
> P1 의 범위가 확대됐다. 이 개정은 "순서 위반" 이 아니라 **P1 내부의 정정**이다 (동결 대상
> 숫자가 바뀌는 것이 아니라, 그 숫자에 붙은 *설명*이 틀렸던 경우).
>
> 추가된 것: **E1** (T1 ω=∞ paired 반사실, 1,000 판 — 인과 귀속 판정) · **E2** (전용 hard-kill
> pursuit baseline, 2,900 판 — modality gap 상단 곡선) · 문서 정정 3 건 (docs/45 DOWNGRADE
> 포인터 · registry C031 · docs/82 spine).
> 취소된 것: `SWEEP_AXES` 의 ω_max 3 점 sweep (ω=∞ 조차 0/500 flip 이므로 더 약한 중복 실험).
>
> ⇒ **P1 은 더 이상 순수 기록 단계가 아니다.** "실험은 KSAS 후" 라는 원 규율의 예외이며,
> 사유는 *현행 초안의 headline 문장이 반증된 인과 주장 위에 서 있기 때문*이다. 승인 주체는
> 사용자/지도교수. 그 외 항목(θ·jink·B2·T2)은 여전히 KSAS blocker 가 아니다.
- Exit: tag `ksas-2026-submission-freeze` — figure data / table / runtime config / 원고 / bib / JSON+manifest 동결.

### P2 — KSAS 2p 제출
- spine 좁게: τ → χ → aiming bottleneck → tested capture regimes.
- 제외: Gate 10 세부 / Gate 11 repair / B2 / MARL / T2 / Gate 7 certificate 기계장치. Gate 7 은 Discussion 1문장만 ("post-commit repositioning was too late in the registered 0.30-s window, motivating pre-commit shaping").
- claim 어휘: `feasible` 대신 **baseline-achievable / aiming-limited / kinematically infeasible**.

### R1 — repo sanity pass 1: provenance only (behavior 0 변화)
- 모든 신규 campaign 결과에 `contract_manifest` 자동 스탬프: git_commit / campaign_id / contract_revision / threat_class / resolved_config / derived_config / distribution_hash / code_schema_version. (m4_env.contract_manifest 기계 이미 존재 — 저장만 안 하고 있었음.)
- 목적: "파일명 보고 route_gain 추정" · "한 contract 문자열에 400/480/800 3세대" 재발 방지. **이게 repo sanity 개선의 80%.**
- historical artifact 는 sidecar 만. Exit: 기존 frozen output 대비 bit-exact regression.

### R2 — semantic renaming (값 변경 0)
- `theta` → `theta_fire_runtime` / `theta_s2_label` / `theta_gate7_close` — 값이 전부 0.9 여도 **이름은 분리**.
- A1/A2/A3 (code level) vs T0–T4 (threat class) 경계 명시 강화. Exit: regression exact.

### R3 — derived/invariant cleanup
- 원칙: **assert first → deduplicate later.** `assert |ρ − R_max·tan(α)| ≤ tol` 부터; 안정 확인 후에만 `alpha = atan(rho/R_max)` 단일 소스화.
- 대상: ramp reachability 3중 구현 / ρ·τ·R_NK 복사 (coarse_pilot:82,84) / r_lat↔ring_radius / standby R 2중.

### A0 — arXiv validity gate (여기부터 새 science, branch 분리)
- **5A θ=0.9 sensitivity (최우선)**: 기존 stored states offline relabel, θ∈{0.85,0.90,0.95} → FREE/INF/AMB 유병률 / Gate 7 close fraction / χ trend / headline flip 여부. stable → 0.9 nominal + appendix; unstable → 별도 calibration revision prereg (재선택 금지).
- **5B jink 등록**: A_jink=0.6, f_jink=1.5 Hz (f·τ=0.45 활성 무차원 좌표) — sensitivity or nominal-fixed scope 중 **명시적 선택**.
- **5C hygiene**: χ grid 78.67 vs bracket 78 / κ grid 확장 / r_nk=6 provenance / 항등식 / manifest.
- Exit 문장: "no known unresolved numeric-contract issue materially changes the claims presented in arXiv v0."

### arXiv v0 spine
- Part I capture feasibility (τ·χ·T1 empirical·aiming·Gate 10 multi-coordinate caveat) / Part II why terminal cooperation is too late (Gate 7: "terminal blockade cannot substitute for pre-commit shaping under the registered model and sampled states") / Part III consequence: **useful cooperation must act before commit.**
- **B2 결과를 기다리지 않는다** — arXiv v0 의 역할은 "왜 B2 인가"까지. T2 robustness 는 v0.1/v1 로 미뤄도 됨.

### B0 — B2 world-contract revision (코드보다 문서 먼저)
- **7A observability contract**: attacker(무엇을·언제·거리·role·velocity·noise·latency) / defender(full state? oracle 분류? latency?) 표로 봉인.
- **7B commit 채널 3택**: ① global instantaneous commit-bit(현행) ② sense-gated ③ delayed/noisy — "무엇이 현실적인가"가 아니라 **어떤 model 을 시험하는가**를 먼저 결정.
- **7C 시간 분해**: T_lead 단일축이 아니라 t_detect 도입 → T_pre = t_detect − t_shaping,start / T_react = t_commit − t_detect 분리.
- **7D route post-commit semantics**: 유지(명시) or 변경(새 계약) — **결과 보고 선택 금지.**
- **7E train/eval parity = absolute blocker**: train_m4/mission_eval 배선 격차(RESET audit) 해소 전 learned arm 금지.
- Exit: `B2_WORLD_CONTRACT_FROZEN`.

### B2 — scripted mechanism test (MARL 금지)
- defender scripted, threat T1 동결. factorial: H0(hold/hold) · P(preposition/freeze) · R(hold/reactive) · PR(preposition/reactive).
- primary endpoint = commit-state distribution shift Pr(z_commit ∈ C_feasible) (capture rate 는 secondary). prepositioning vs interactive shaping **분리**가 목적.
- **Stop rule**: T1 scripted 에서 favorable shift 없음 → MARL 진행 금지.

### T2 → MARL → AIAA → Journal
- T2 (J_A = w_p·progress + w_r·threat + w_s·smooth, scripted): B2 mechanism-positive 시에만. 단일축 이동 (D1,T1)→(D1,T2). 질문 = "defender 가 T1 angular-gap grammar 를 exploit 한 것인가".
- MARL: (D_scripted,T1)→(D_MARL,T1)→(D_MARL,T2). **두 축 동시 이동 금지.**
- AIAA 최소 package: feasibility map + T1 검증 + Gate 7 + B2 scripted 존재증명 + T2 robustness + MARL vs scripted + ladder statement.
- Journal: T3(MPC)/T4(self-play) + defender×T0..T4 matrix — 목표는 전승이 아니라 "mechanism 이 어느 sophistication 까지 유지되는가".

## 3. Branch 전략

```
main
├── paper/ksas-2026          (제출 후 frozen)
├── infra/repro-manifest     (R1: schema / R2: naming / R3: asserts)
├── science/arxiv-v0         (θ·jink·Gate7 통합)
├── science/b2-contract      (observability + commit semantics)
├── science/b2-scripted
├── science/t2-robustness
└── science/marl
```

## 4. 위험도 요약 (감사 대응 관점)

| 축 | 위험 | 대응 phase |
|---|---|---|
| Scientific validity | 낮음 (KSAS 생존) | P1 5건만 |
| Reproducibility/provenance | 중간 | R1 (manifest = 80%) |
| arXiv claim integrity | 중간~높음, 수정 저렴 | A0 (θ sensitivity) |
| B2/game validity | **높음** | B0 봉인 전 실행 금지 |
| Repo maintainability | **개입 마지막 적기** — B2+MARL+T2/T3 이후엔 훨씬 어려움 | R1→R2→R3 순서 준수 |

## 5. 이 문서의 지위

- 이 워크플로우는 감사 발견의 **경계 선언**이다: 어떤 변경이 역사-보존용 cleanup 이고(R1~R3), 어디부터가 새로운 scientific model revision 인가(A0, B0 이후).
- 순서 의존성 위반(예: KSAS 전 refactor, contract 봉인 전 B2, parity 전 MARL)은 본 문서 개정 없이 금지.

---
*연관: 감사 = artifacts/audits/environment_numeric_audit_2026-08-13.md · 수용규칙 = docs/72 · 계약 = docs/74 · workflow = docs/77 · Gate7 = docs/79 · ladder = docs/80 · 배선격차 = artifacts/audits/RESET_WEEKLY_AUDIT_SUMMARY.md*
