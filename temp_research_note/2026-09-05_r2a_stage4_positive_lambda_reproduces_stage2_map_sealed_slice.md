# 2026-09-05 — Stage 4 POSITIVE: Stage 1 의 {λ,α} 효과가 독립 교란만으로 재현 (dose-ordered) → (χ,η,λ) 재등록 경로 확정 · Stage 2 full map = λ=4.644 기준 slice 완성

## Stage 4 (protocol 59c4de1889ed72dc, 7,200 ep, 판정 규칙 사전 봉인)

| cell | p(λ4.64) | p(λ4.11) | p(λ3.57) | Δp(L2) CI95 |
|---|---|---|---|---|
| (0.54, 3.0) | .630 | .453 | .265 | [−.420, −.312] |
| (0.54, 3.9) | .395 | .270 | .075 | [−.370, −.270] |
| (0.56, 3.0) | .515 | .347 | .175 | [−.393, −.290] |
| (0.56, 3.9) | .325 | .200 | .052 | [−.320, −.228] |
| (0.58, 2.1) | .672 | .535 | .390 | [−.347, −.217] |
| (0.60, 2.1) | .517 | .410 | .280 | [−.297, −.175] |

- **방향 6/6** (전 셀 CI 상한 < 0) ✓ · **material** pooled Δp(L2) = −0.303 ≥ 0.20 ✓ →
  **POSITIVE**. secondary dose ordering 도 성립: pooled Δp(L1) = −0.140 이 정확히 중간
  (λ 에 거의 선형 — 교차검증으로서 매우 강함).
- Stage 1 R-rho-DOM 의 −0.20~−0.39 가 ρ·스폰·σ 동시-변경 없이 **{λ,α} 단독으로 재현**됐다.
  cone 기하 (λ = R_max/ρ) 는 (χ,η) 로 흡수되지 않는 제3의 governing 좌표다.
- 봉인 규칙 이행: λ 승격은 이제 자동이 아니라 **입증됨** → (χ,η,λ) 재등록 경로, C045 후보
  = PARTIAL_3D (등록은 Stage 3 confirmatory 후).

## Stage 2 (protocol 3bc9dba2fe01385f, 33,600 ep — λ=4.644 기준 slice)

χ50(η) isotonic (행별 n=4,800): 2.1→0.605 · 2.4→0.587 · 2.7→0.577 · 3.0→0.568 ·
3.3→0.542 · 3.6→0.538 · 3.9→0.525. **η 에 단조 감소, 폭 0.08** — Stage 0 의 "약한 감소"
가 촘촘한 n 에서 깨끗한 단조로 확정. Stage 0 대비 차이는 대부분 |Δ|≤0.03, η=2.4/2.7 의
−0.06~−0.08 은 Stage 0 해당 행의 넓은 CI (n≈200, [0.52,0.67]) 안 — 정합.

## 이 캠페인의 현재 그림

p = p(χ, η, λ | sealed A2-reactive vector, q_dec 1/6, capability family). SIM 상사는
라벨-정확 (Stage 1), k_f·τ +50% 는 시험 범위 내 robust, λ 는 governing (Δχ50 환산은
Stage 3 재설계에서). Stage 2 지도는 3-D 표면의 λ=4.644 slice.

## 다음 (설계 결정 필요 — 결과 열람 후이므로 재등록은 새 hash)

1. **(χ,η,λ) 재등록**: 새 3-D lattice hash. R2b 의 2-D 좌표 잠금은 자동 무효 (봉인 규칙).
2. **Stage 3 재설계**: 경계 밴드를 어느 λ slice 에서 검사할지 (λ0 단독 vs λ0+λ2 2-slice)
   + worst-case family exact rule + n=650 재검토 — 봉인 전 감사 1회 권장.
3. repo-R1 (여전히 미실시) — Stage 3 confirmatory 전 필수.
산출물: stage4_readout.json · stage2_readout.json · 판독기 r2a_stage24_readout.py.


## 정정 + 후속 봉인 (같은 날, 감사 r2)

- **정정 1**: "Stage 0 대비 대부분 |Δ|≤0.03" → 5/7 행 ≤0.03, η 2.4/2.7 은 −0.064/−0.076
  (넓은 Stage 0 CI 와 양립). CI 겹침 ≠ 점추정 일치.
- **정정 2**: "λ 에 거의 선형" → "approximately intermediate response" (3점).
- **claim 상한**: 3-D 식별 완료 아님 — λ=4.644 의 2-D 경계 slice + λ 민감도의 독립 확인
  까지. "local 3-D boundary surface" 는 λ2 경계곡선 후 unlock.
- **재등록**: R2a-P3 `d9d93e20d76859a8` (λ = 단일 cone DOF, 2-D 잠금 해제, n3=680 =
  max(650, Stage 4 실측 worst q 0.522 재추정), family envelope 규칙, 계층 계획).
- **λ2 scout 봉인**: `fa3d149eb846c00d` (exploratory, 3,360 ep). F 4종은 봉인 전 확인 대기.
