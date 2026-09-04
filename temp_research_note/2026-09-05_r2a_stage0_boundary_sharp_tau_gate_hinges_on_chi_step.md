# 2026-09-05 — R2a Stage 0: 경계는 날카롭고 η 에 약하게 종속, τ_B 게이트는 χ-grid 간격에 걸려 있다 (0.375 / D-1)

지위: **exploratory / design data** (브리프 r3 §5 Stage 0). 동결 `curve_hold_reactive.json`
n=2,700 의 재집계 — 새 표본 없음, 라벨 불변. 증거 아님. 봉인 문서 미작성 (사용자 결정 대기).

## 산출물
- `shepherd/scripts/r2a_stage0.py` → `artifacts/r2a/stage0_envelope.json` (hash `2109ba5b23e745e9`, χ_step 0.04 기준)
- `shepherd/scripts/r2a_lattice.py` → `artifacts/r2a/lattice_r2a.json` (pre-seal, hash `444ce09488069cda`)
- `artifacts/r2a/stage0_rows.png` (viz-first: 행별 isotonic p(χ))
- `tests/test_r2a.py` 7종 (pin 왕복 · 브리프 §4.4 support 표 재현 · ledger SIM/DOM 검증 + 누수 거부 · 게이트 판정 · PAV · hash 안정)

## 행별 χ50(η) (isotonic primary, boot CI95 B=500, n≈220/행)

| η | n | p̄ | χ50 | CI95 | logistic χ50 | δχ50 (δp=0.10 역산) |
|---|---|---|---|---|---|---|
| 1.8 (off) | 221 | .23 | 0.610 | [.593,.621] | .622 | .012 |
| 2.1 | 222 | .20 | 0.598 | [.592,.699] | .621 | .013 |
| 2.4 | 221 | .21 | 0.650 | [.568,.666] | .628 | .013 |
| 2.7 | 195 | .16 | 0.653 | [.524,.664] | .595 | .018 |
| 3.0 | 226 | .19 | 0.552 | [.523,.606] | .576 | .013 |
| 3.3 | 229 | .18 | 0.569 | [.562,.614] | .576 | .010 |
| 3.6 | 225 | .17 | 0.520 | [.513,.557] | .540 | .012 |
| 3.9 | 216 | .12 | 0.541 | [.510,.581] | .542 | .009 |
| 4.2~4.8 (off) | ~210 | .11~.19 | 0.49~0.54 | | .51~.52 | |

pooled 1-D χ50 (isotonic) = 0.565 (기존 bin 기반 0.571 과 정합). censored 행 0, 단조성 flag 0.

## 판독 3건
1. **경계가 극히 날카롭다**: raw bin 에서 χ<0.49 → p≈1.0, [0.49,0.73] → ~0.5, χ>0.73 → 0. logistic 기울기 |dp/dχ|≈8~10 → δp=0.10 에 대응하는 δχ50 ≈ **0.01** (docs/87 의 0.05 보다 5배 엄격). §6.1 규칙대로면 역산값이 정본이 되는데, χ50 boot CI 반폭이 0.02~0.07 (n≈220) 이라 **0.01 등가성은 계획 n 으로 검정 불가** → §9 잔여 결정 (h / δχ50 절차) 은 "역산값 채택" 이 아니라 **판정 척도 자체를 재설계**해야 한다 (예: δχ50 을 CI 해상도에 묶거나 D_χ 판정을 밴드 기반으로).
2. **χ50(η) 는 η 에 약하게 단조 감소** (lattice 행 0.60→0.54, off-lattice 포함 0.61→0.49). 1-D 투영이 숨기던 η 종속이 존재하지만 폭 ~0.1 — "η GOVERNING" 은 경계 위치보다 **p 플라토 높이** 쪽 이야기일 수 있음 (η-tercile 결과와 정합). 확정은 Stage 2.
3. **τ_B 게이트가 χ-grid 간격에 걸려 있다** (envelope h ≥ χ_step, headroom = χ_step 규칙 때문):

| χ_step | 판정 |
|---|---|
| 0.02~0.04 | **τ_B = 0.375 SELECTED** (floor 후보만; 0.45/0.425/0.40 전부 탈락) |
| ≥0.05 | **D-1 NON_IDENTIFIABLE** (0.375 도 η≥3.0 행 탈락) |

χ_step 0.04 에서도 η=3.6 행의 여유는 0.003 (0.440 vs support 0.437) — bootstrap 한 번이면 뒤집힌다. 즉 legacy bracket 안에서 time-perturbation H-DOM 은 **잘해야 최약 교란 (τ_B/τ_ref=1.25) 만 marginal 하게 identifiable**.

## 코드 기본값 (봉인 아님 — 사용자 결정 후 확정)
- χ 격자 0.41…0.85 (12점, step 0.04) — 경계 [0.52,0.65] 를 걸치도록. 원안 "χ 12점 × bracket 전폭" 은 p≈0 플라토에 셀을 낭비하므로 폐기 권고.
- χ_step 0.04 근거 = boot CI 반폭 중앙값 ≈ 0.04 (경계 해상 척도). 게이트 통과를 위해 고른 값이 아님을 명시하되, 판정이 이 값에 걸려 있다는 사실은 봉인문에 그대로 기록.
- R-tau 계열은 χ=0.41~0.45 셀에서 a<11 (bracket 이탈, ledger `in_bracket=False`) — Stage 1/3 경계 셀은 공통 support 내부만.

## 사용자 결정 필요 (봉인 전)
A. χ_step 0.04 + τ_B 0.375 로 진행 (marginal identifiability 를 봉인문에 명기) vs
B. D-1 발동: 저가속 pin-확장 (a<11) 캠페인을 신규 hash 로 분리 선언 — τ_B 0.45 등 강한 교란 회복.
C. δχ50 판정 척도 재설계 (판독 1).
+ SIM co-scale 하네스 실현성 (dt=τ_B/6=0.0625, k_f=1.20/0.375=3.2 s⁻¹ 주입 가능 여부) 은 미검증 — Stage 1 착수 시 ledger 로.

## 후속 (같은 날) — 사용자 결정 = **B + C**, 코드·브리프 r4 §10 반영

- **C**: δp=0.10 / δχ=0.05 별도 estimand (δχ 근거 = R2b regime 분류 보존, slope 역산 폐기 → 진단 전용). boundary micro-grid (χ50⁽⁰⁾±0.08, step 0.02, 9점) 를 map grid (0.41…0.85 step 0.04) 와 분리. envelope = χ50 ± 0.08 고정. 게이트 headroom = 0.02 (map 간격 무관).
- **B**: 계약 2종 별도 hash, pooling 금지.

| 계약 | a bracket | τ_B | 게이트 | η=3.6 여유 | hash |
|---|---|---|---|---|---|
| R2a-L | [11,78] | 0.375 | D-1 (η=3.6 탈락) → **directional only** | −0.017 | `5b65b6961a063d7f` |
| R2a-P | [7,78] | **0.45** | SELECTED (전 행) | +0.020 | `06f90452655573f8` |

Stage 0 hash `97bd934f96af8e62` (envelope 규칙 변경으로 갱신). 테스트 14/14 (test_r2a 9 + lineage/hygiene).
a_min 7 은 사용자 제안값; 여유 +0.020 이 부족하다고 판단되면 a_min 6 (χ_min 0.343, 여유 +0.077) 이 다음 후보 — 봉인 전 결정.
미커밋. 다음 = 봉인 커밋 (hash 2종 + Stage 0) → Stage 1 (repo-R1 + H-4 랩서버 선행).

## 후속 2 — a_min^P = 6 (support buffer 사전규칙 H ≥ 0.05) + W 0.10 + hidden-branch 감사 통과

- 규칙 `select_a_min`: 후보 {7, 6} 중 H_support = min_η(B_lo − 0.02 − χ_min) ≥ max(δχ, 2·0.02) = 0.05 인 최대 a_min. W=0.10 기준 7 → H 0.000 reject, **6 → H 0.057 accept**.
- micro-grid ±0.10 step 0.02 (11점). Stage 0 hash 갱신 (W 변경).
- a∈[6,7] 감사: A1 항 전부 a 비례, hold arm 은 limiter 가속 0·finisher 정지, a_lim 은 commit margin 에 선형, slew 8/10 rad/s 는 a/v<1 이라 무관 → **branch 없음**. 부산물 = 시간·길이 상수 인벤토리 (tau_lock 0.10, tau_kill 0.15, omega_aim 3.14, slew 8.0, spawn 2.0/5.0/24, kill_radius 0.75) → ledger `inject` 필드. Stage 1 하네스 주입 실현성 검증 대상.
- 사용자: 위 두 조건 충족 시 **Stage 1 착수 승인**. 선행 = 봉인 커밋 → repo-R1 → H-4 랩서버.

## 후속 3 — 감사 r2 (조건부 승인) 반영: A2-reactive 재봉인 + blocker 3건 닫음

- **provenance**: 1차 = 생성 커밋 43acc39 동봉 sidecar manifest (route 0.5 · sense 30 · run commit edf34d9 — r1 의 "문서-추정" 은 과소평가, 기계 sidecar 였음). 2차 = exact replay 60판 (경계 밴드): 후보 60/60 · 대조 54/60 (판별 6판 전부 후보 승) · 결정론·draw bit-exact → **CONFIRMED**. 재봉인은 이 verdict 를 assert.
- **ledger 확장**: inject 22종 (layout 7 추가) · runtime_norm 7종 /ρ 전 구현 invariant (DOM 예외 없음, 누수 거부 테스트) · CONDITIONING_VECTOR (무차원 행동·판정 상수 + jink 2π 규약) · EPS_AUDIT (runtime 은 _EPS 1e-12, inert) · "μ inert" 삭제 (motion-inert / decision-active, conditioning ratio 유지).
- **어휘·게이트**: 전역 어휘 "…conditional on the sealed A2-reactive evasion behavior vector". 순위 주장 → a priori sensitivity candidates 강등. STAGE1_GATES = pathwise-first + HARD_KILL STOP (분모 삭제·재코딩 금지) + viz-first.
- **새 hash (v3)**: Stage 0 `4c26cf1a2a4d9ab8` / R2a-L `da36d96eb5bceddc` / R2a-P `3aa3adef77420d12`. 구 hash 3종은 SUPERSEDES 로 lineage 보존. envelope·게이트 수치 불변. docs/87 §4 A1→A2 개정 (날짜 명기). 테스트 19/19.
