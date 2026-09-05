# 2026-09-05 — λ2 scout: 경계가 χ50 수준에서도 −0.04~−0.09 하향 확인 (무censoring) → Stage 3 최종 봉인 (95,200 ep)

## scout 판독 (fa3d149eb846c00d, 3,360 ep, exploratory — envelope hash `fc1927add6785a91`)

| η | χ50(λ0, Stage 2) | χ50(λ2, scout) | Δ |
|---|---|---|---|
| 2.1 | 0.605 | 0.545 | −.060 |
| 2.4 | 0.587 | 0.546 | −.041 |
| 2.7 | 0.577 | 0.501 | −.076 |
| 3.0 | 0.568 | 0.509 | −.059 |
| 3.3 | 0.542 | 0.476 | −.066 |
| 3.6 | 0.538 | 0.453 | −.085 |
| 3.9 | 0.525 | 0.439 | −.086 |

λ2 도 η 단조·무censoring. **λ 효과가 p 수준(-0.30)을 넘어 χ50 수준에서 평균 −0.067 —
δχ 0.05 초과.** (지위: scout 는 설계 데이터 — 이 표는 Stage 3 band 중심 산출용이고
confirmatory 수치는 Stage 3 가 다시 잰다.)

## Stage 3 최종 봉인 `11dbf6114425b49c` (P3 골격 b7b3f6440e5b83eb 이행)

- 2 slice × 7η × chi50 감싸는 micro-grid 2셀 = **28셀** (λ0 밴드 = Stage 2, λ2 밴드 = scout).
- 셀당 configs 5 = F_primary 4 (nom/J+/R+/J+R+) + **A1 anchor (min 불포함)**, 전부 한
  scenario 안 paired CRN (ns r2a_s3, seed0 3000). n=680 uniform.
- **등가성 팔 재실행 안 함** (봉인 문구): Stage 1 이 SIM (불일치 0/4,800 — n 추가가 정보
  0) 과 k_f·τ (q 0.048, n 70 이면 족함) 를 이미 confirmatory 정밀도로 닫음.
- 총 95,200 ep ≈ 직렬 39h → 8샤드 ~5h. HARD_KILL 전역 sentinel + q_dec assert.
- readout 전 의무 = **repo-R1** (protocol 에 명문). readout 계획: slice 별
  χ50_worst(η) 밴드 → "local 3-D surface" 어휘 unlock 판정 (P3 규칙) → C044/C045/C046.
