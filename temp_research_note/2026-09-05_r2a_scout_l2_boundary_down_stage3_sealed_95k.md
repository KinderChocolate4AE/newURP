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

## 후속 (감사 r4) — 실행 전 estimand 명확화 재봉인 `eb3a85e702020167` (구 11dbf6114425b49c)

- **2점 밴드 vs p_worst censoring 위험 해소**: primary 는 "nominal boundary-local
  p_worst" (전자). ① 3-D surface unlock 은 **A2-nom 팔의** χ50 확인만 지칭 ② p_worst
  는 nominal 밴드 셀의 **셀-국소 통계** ③ 한 행의 두 점 모두 p_worst<0.5 면 crossing
  censored → "local envelope displaced beyond the tested nominal boundary band" 로
  보고, **worst-case χ50 외삽·추정은 명시적 scope 밖**. 에피소드 0개 상태의 개정.
- **repo-R1 조건부 병행 승인 이행**: shard manifest 에 git code_commit + protocol
  hash 기록 (smoke 확인: d0eb0b0). repo-R1 실패 시 run 전체 quarantine + 새 lineage
  재실행 — "열어보고 고치기" 금지를 protocol 에 명문.

## 후속 2 — R2a sensitivity screen 설계 노트 (Stage 3 종료 후 별도 후속, 감사 승인 골격)

- 목표 단일: 현 (χ,η,λ) 경계를 δχ=0.05 이상 움직일 추가 conditioning 축 검출.
  Stage 3 primary 를 흔들지 않도록 **별도 캠페인** (R2a-P4 후보).
- 설계: 3-D boundary-local **paired OAT**, anchor 6개 = {λ0, λ2} × η {low, mid, high}
  (Stage 3 확정 셀에서 선정). 축당 θ⁻/θ⁰/θ⁺ **양방향** (λ 단방향 교훈), n=100,
  동일 CRN, baseline 공유 → 10축 기준 6×100×(1+2×10) = 12,600 ep (~1.5h 8샤드).
- 후보 우선순위 (감사): 높음 = κ · commit_threshold · sense_range/ρ · jink_freq·τ ·
  homing_gain·τ / 중간 = τ_lock/τ · τ_kill/τ · μ · ω_aim·τ · ω_slew·τ / 낮음 = spawn
  비 3종 · ν · controller ratio. **q_dec = positive control, k_f·τ = negative control**
  (신규 발견으로 세지 않음). 전부 무차원군으로 흔든다 (raw 금지).
- screen-in 규칙 (screening 이지 confirmatory 아님 — "민감하지 않음 증명" 금지):
  다수 anchor sign-consistent |Δp|≳0.10 / pooled 동방향 대효과 / |Δχ|≥0.05 이동 /
  일부 셀 gross |Δp|>0.20 → 승격 후보. 무검출 시 "tested local perturbation range 에서
  material sensitivity 미검출" 까지만.
- OAT 약점 = interaction: 1차에서 2~4축 생존 시 그 축들만 2×2 pairwise/소형
  fractional-factorial 2차. 순서: Stage 3 종료 → OAT screen → material 축 선별 →
  interaction probe → 필요시 R2a-P4 좌표 승격.
