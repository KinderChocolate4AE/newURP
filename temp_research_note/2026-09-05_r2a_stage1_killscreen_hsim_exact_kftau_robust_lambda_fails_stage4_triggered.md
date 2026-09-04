# 2026-09-05 — R2a Stage 1 kill screen: H-SIM 라벨-정확 (discordant 0/4,800) · k_f·τ 교란 robust · {λ,α} 교란 전 셀 FAIL (sign-일관) → Stage 4 직교 λ test 발동

지위: **falsification screen** (protocol `1496a4769876b438`, 대표성 주장 없음). 12,000 ep
(6셀 × 400 scenario × 5구현, scenario-paired CRN), HARD_KILL 0, sentinel 미발화.

## 판정 (paired CI95 ⊂ ±0.10 3분법, scenario-paired bootstrap B=4000)

| 팔 | 6셀 판정 | Δp̂ 범위 | discordant |
|---|---|---|---|
| R-tau-SIM / R-rho-SIM | 전 셀 PASS | 정확히 0 | **0 / 4,800** |
| R-tau-DOM (k_f·τ 1.20→1.80) | **전 셀 PASS** | −0.013 ~ +0.003 | 51 / 2,400 |
| R-rho-DOM (λ 4.64→3.57, α 12.2°→15.6°) | **전 셀 FAIL** | −0.39 ~ −0.20 (전부 음수) | 979 / 2,400 |

## 판독 3건

1. **H-SIM 은 라벨 수준까지 정확하다.** 상사변환 4,800 paired 에피소드에서 라벨 불일치 0.
   pathwise 8e-15 의 통계적 확장 — 경계 셀 한정 screen 수준에서 최강 형태의 지지.
2. **k_f·τ +50% 교란에 경계가 robust.** 궤적은 갈라지는데 (pathwise 5.6e-2) 라벨은 거의
   불변 — controller gain 축은 (χ,η) 지배를 위협하지 않는다. Stage 3 confirmatory 대상.
3. **{λ,α} 교란은 sign-일관 대실패.** cone 이 ρ 대비 짧아지자 포획이 전 셀에서 20~39%p
   급락. kill 조건 (sign 없는 산포) 아님 — **"sign-consistent |Δp|>0.20 → 승격 후보"**
   경로. 단 봉인 규칙: λ 자동 승격 금지 → **Stage 4 직교 λ test (λ·α 만 3레벨 × 경계
   6셀) 로 독립 효과 확인 후에만 (χ,η,λ) 재등록**. C045 는 PARTIAL_3D 후보로 이동.

## R-ref 경계 위치 정합 (Stage 0 frozen 재집계 vs 신규 seed 실측)

η=2.1: p(0.60)=0.502 (Stage 0 χ50 0.598) · η=3.0: p(0.56)=0.512 (0.552) · η=3.9:
p(0.54)=0.403 (0.541) — 서로 다른 seed·지터에서 경계 위치 일치. 사슬 전체의 교차 검증.

## n 재산정 (봉인 규칙: DOM 별도, SIM pooling 금지, 보수적 max)

R-tau-DOM worst q 0.048 → n 70 / R-rho-DOM worst q 0.497 → n 650 → **Stage 3 n = 650**.
(단 R-rho-DOM 은 screen 에서 이미 결정적 FAIL — Stage 3 등가성 대상은 사실상 R-tau-DOM,
n 봉인은 보수값 유지.)

## 다음

Stage 2 (R-ref full map 33,600 ep, 서버 ~2.6h 8샤드) + **Stage 4 발동** (조건 충족).
Stage 3 착수 전 잔여 = worst-case family exact rule 봉인 + repo-R1. 산출물 =
`artifacts/r2a/stage1_readout.json`, 판독기 = `r2a_stage1_readout.py`.
