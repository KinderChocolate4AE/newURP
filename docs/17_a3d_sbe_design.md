# 17 — A-3d 설계: 합성 후방 연장(SBE) 후진 커리큘럼 (v0.1 초안, 2026-07-15 — V-1~V-6 비준 대기)

> 입력: 09 (nn) G0 확정(r@2+ ≡ 0, 물리 지배) · (kk) R0 말단 습득 · (ll) 피드백 #9/#10(full-state rewind). 원칙 불변: 판정 경로·게이트 정의 불변, 신규 개입 전부 TRAIN 스캐폴드, 트립와이어 8/31.

## 0. 문제와 해법 한 단락

되감기의 부트스트랩: R0 성공 에피소드는 witness에서 **시작**하므로 t−k 접근 궤적이 없다. G0의 물리: 정지 리미터는 이동 창을 못 쫓는다 — 즉 **속도를 가진 채 도착 중인** 상태에서 스폰해야 한다. 해법 = **합성 후방 연장**: AnalyticBackend는 단순 적분기(v′=clip(v+aΔt), p′=p+v′Δt)라 후방 구성 상태열이 곧 유효한 전방 궤적이다(클립 여유 확보 시). witness 도착 조건을 만족하는 폐형식 도착 프로파일을 리미터마다 합성하면, **t−k 스폰에는 창 도달 행동 시퀀스가 구성상 존재**한다 — oracle이 죽인 회복 불가능성이 설계로 제거된다.

## 1. SBE 합성 절차 [V-1]

**리미터 (폐형식 감속-도착)**: witness 위치 L*_i에 t=0, 속도≈0으로 도착. 도착 방향 u_i = unit(L*_i − anchor_i), **anchor = 명목 링 자리**(중심 [8,0,0]·r5의 대응 슬롯) — k가 클수록 t−k 위치가 명목 분포 쪽으로 후퇴 → **R6 리미터-갭(리뷰 리스크 #1)과 속도 문제를 한 기제로 동시 해소**. 속도 v0 ~ U[0.3, 0.8]·(30·kΔt) (가속 여유 |a| = v0/(kΔt) ≤ 24 < 30), 선형 감속: t−k 위치 = L*_i − u_i·v0·Δt·(k+1)/2, t−k 속도 = v0·u_i. 데모 가속열 저장(진단용 — 정책 모방 강제 아님).
**공격자 (역외삽 + 전방 재검증 슈팅)**: t−k ≈ [x* + v*·kΔt, 0, 0], v = [−v*,0,0]. 전제 = **att_speed를 witness v로 핀**(P-드라이브 정속 직진; 스폰 시임이 params 오버라이드) + 도착 구간에서 repel 비발동(리미터-공격자 거리 > kill·margin 사전 검사, 위반 시 u_i 오프축 재추첨). 실제 scripted 함수로 k스텝 전방 롤 → t=0 오차 tol(위치 5cm·속도 2%) 미달 시 1D 슈팅 보정.
**검증 게이트 (bank 수록 조건)**: ① 전방 롤 재현 tol 통과 ② t=0 상태 clean(witness seed) ③ robust ≥ 0.9 (fresh 10 seeds — witness와 동일 기준) ④ 데모 전 구간 |a|·|v| 클립 무접촉. 전멸 시 설계 무효 기록.

## 2. 뱅크·커리큘럼 [V-2]

- 도구 `a3d_sbe_bank.py`: robust witness 3본 × 도착 draw 12(방향 지터 ±15°·v0 표본) × k ∈ {1,2,4,8} → 검증 통과분 수록(`results/a3d_sbe_bank.json`, 스폰 dict = limiters p **+ limiter_v** + att p/v + att_speed 핀 + 데모).
- R-사다리(mode reverse 재사용): **D0(k=0 = A-3b R0 재현, 회귀 앵커)** → D1(k=1) → D2(k=2) → D3(k=4) → D4(k=8) → D5(nominal). 스폰 지터 σ_pos 0.02 고정(회복 껍질 내).
- exit(captured_rate, T-2a 유지): D0 0.45 / D1 0.40 / D2 0.30 / D3 0.20 / D4 0.10 / D5 = frozen-heldout clean 비영 3연속. k>0 스폰은 reset 시점 대체로 비-clean(창 형성 전) → captured = **도착-포획(arrival capture)** = 재성형 등가물의 1차 실증.
- 게이트 기계 [U-5 이식]: 고정 CRN bank 80판, **LCB/UCB confidence 히스테리시스**(전진 LCB95 > exit·후퇴 UCB95 < exit−0.05·그 외 유지), cap 360k·total 520k("최소소요×1.2" 룰 준수: 6 스테이지 × 지속2 × 20480 ≈ 246k).

## 3. 학습 구성 [V-3·V-4]

- **teacher-gated finisher (U-2 이식)**: obs[-3:] 판독 clean → fire, 아니면 mask; fire-head freeze. 후속(D-사다리 통과 후) unfreeze 런에서 발사 학습 재결합. frozen/heldout 판정 = learned policy 그대로.
- **리미터 보상 (U-3 이식)**: r_team(판정 J 불변) + α·[γΦ(s′) − Φ(s)], Φ = mean_z σ((v_z−θ)/τ)·1[¬boxed] − β·std_z, Z_train 고정 5 seeds(audit 분리), terminal Φ≔0. 시작값 α 0.5·β 1.0·τ 0.05.
- **V-4 공격자 스코프**: 스캐폴드 스테이지(D0~D4)는 att_speed = witness v 핀 + 여타 가족 파라미터(adv_a_max·ω)는 랜덤화 유지; D5(nominal)는 가족 랜덤화 전체 복원. eval 전 경로 nominal 불변.
- arm: scratch 3-seed (+ A-3b best ckpt warm 1-seed 참고런, 선택 금지).

## 4. 지표·진단 [V-5]

- U-4 분해 이식: spawn_capture / **arrival_capture**(reset 비-clean ∧ 이후 clean ∧ captured — A-3d의 주지표) / missed / false_fire / improved(ΔΦ>0). 성공 = **P(arrival_capture | k≥1 스폰) LCB95 > 0** (무행동·무도착 기준선 ≈ 0이므로 어떤 유의 발생도 학습 증거).
- U-6 로깅 일괄(TPR/FPR·fire-logit AUC·fire vs cont ratio 분리) + 도착 추적 오차(데모 대비, 진단 전용).

## 5. 리스크 (자가 신고)

① 합성 도착 프로파일 ≠ 자연 접근 분포(off-manifold) — 방향·속도 draw 다양화 + RL 자유도(모방 강제 없음)로 완화, 잔여는 D5 전이가 판정 ② 도착 중 repel 간섭 — V-1 사전 검사로 스크리닝 ③ obs-norm privileged drift(기지 캐비앗) ④ k=8(0.4s)도 명목 에피소드 규모엔 미달 — 단 anchor-방향 후퇴가 위치 갭을 좁힘 ⑤ teacher-gate 하 fire-head 미학습 상태로 D5 진입 시 발사 재붕괴 가능 — unfreeze 런을 별도 스테이지로.

## 6. 비준 체크리스트 (V-슬롯)

- [ ] **V-1** SBE 합성 절차(도착 폐형식·anchor=명목 링·공격자 슈팅 tol·검증 4조건)
- [ ] **V-2** D-사다리 {0,1,2,4,8,nominal}·exit 값·confidence 게이트(80판·LCB/UCB)·예산 360k/520k
- [ ] **V-3** teacher-gate + ΔΦ 파라미터(α0.5/β1.0/τ0.05/|Z|5)
- [ ] **V-4** att_speed 핀 스코프(D0~D4 한정, D5 복원)
- [ ] **V-5** arrival_capture 주지표 + LCB>0 성공 기준
- [ ] **V-6** 스코프: bank 생성·검증 → scratch 3-seed 기전 실험(+warm 참고 1) → 성공 시 unfreeze 런 → confirmatory
