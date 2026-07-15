# 16 — A-3c 설계: 회복가능성 oracle → 역할-분리 기전 실험 (v0.1, 2026-07-15 — U-1~U-7 비준)

> 입력: 09 (kk) 파일럿 PASS + (ll) 심층 피드백 판독(전문 = URP/gpt_deep_feedback_a3b_2026-07-15.md). 원칙 불변: 판정 경로·게이트 정의 불변, 신규 항 전부 TRAIN 스캐폴드, 트립와이어 8/31.

## 0. 확정 사실과 남은 질문

확정: 말단 발사는 학습됨(R0 3/3, 20k). 포획은 스폰-운 천장에 갇힘. 두 정책 모드 = 전역 fire-bias의 합리적 양극단(p* ≈ 0.13~0.16 vs 스테이지 prevalence). 인과 교착: 즉시-발사가 리미터 transition 삭제 ↔ 재성형 부재가 대기 가치 삭제.
남은 질문(순서대로): **Q1 비-clean 스폰은 물리적으로 회복 가능한가?** → Q2 회복 가능하다면, 올바른 인과 신호(교사-게이트 + ΔΦ)로 리미터가 재성형을 배우는가?

## 1. U-1 회복가능성 oracle (선행 게이트; 학습 아님)

- 도구: `shepherd/scripts/a3c_recoverability_oracle.py` — reset-nonclean 스폰(bank×σ, 자기-seed 판정)에서 리미터 상수-가속 후보 M개(|a|≤30)를 **순수 kinematics로 k스텝 전진**(무발사 구간 = 결정론; 공격자는 실제 scripted 정책) 후 종점 pre-move 상태에서 union 1회 평가 — recoverable@k(클린∧worst≥1), action volume, best Δv_soft, winner robust(fresh seeds 3).
- 물리 사전 계산: 리미터 정지 출발 변위 상한 = 3.75cm(1스텝)/15cm(2)/34cm(3) vs 공격자 0.8~1.2m/스텝 — **k≥2 회복은 "창 추적"이 아니라 "다음 위치의 창 예측 배치"여야 가능**.
- **스모크 (샌드박스, n=4 스폰·후보 12~20 — 참고치)**: x16v20, σ0.05 → r@1,2 = 0.00; σ0.02 → r@1 = 0.25(vol 0.05), r@2,3 = 0.00. 약한 탐색(상수 가속) 기준이므로 하한 추정.

**사전등록 분기 규칙 (정식 = 3 witness × σ{0.02,0.05,0.1} × 스폰 12 × 후보 32, k{1,2,3}):**
- **G1 (재성형 학습 가능)**: σ0.02 recoverable@≤2 ≥ 0.3 ∧ σ0.05 recoverable@≤3 ≥ 0.1 → §2 A-3c 학습 실험 진행 (스폰 = recoverable-필터 bank).
- **G0 (물리 지배)**: 위 미달 → position-noise 스폰에선 보상 설계 무관 재성형 불가(피드백 §3 해석 그대로) → §3 **A-3d 전환**: A-3c 학습 실험 생략, 궤적-되감기 설계로 직행. 오라클 결과 자체가 논문 진단 서사의 행("비-clean 지터 스폰의 단기 회복가능성 상한").

## 2. A-3c 학습 실험 (G1 시; U-2~U-7)

- **U-2 teacher-gated finisher (TRAIN 전용)**: reset-clean(obs[-3:] 판독) → 즉시 fire; Φ ≥ φ_fire 도달 → fire; 그 외 mask. fire-head는 freeze(학습 제외) → 재성형 확인 후 후속 런에서 unfreeze. frozen/heldout 판정은 learned policy 그대로(교사 미개입) — 본 실험의 판정 지표는 §U-4의 train-eval 분해.
- **U-3 리미터 보상** = r_team(J 불변) + α·r^Φ, r^Φ_t = γΦ(s_{t+1}) − Φ(s_t) (PBRS 차분형): Φ(s) = mean_z m_z − β·std_z, m_z = σ((v_soft^{(z)}−θ)/τ)·1[¬boxed], **고정 seed bank Z_train(|Z|=5, 학습·audit 분리)**, terminal Φ≔0, 스테이지 간 Φ 정의 불변. 시작값: α=0.5, β=1.0, τ=0.05 (비준 시 확정). U-3b(per-limiter 현재-상태 hold-차분 D^Φ) = phase 2 예약(비용 4×).
- **U-4 지표(분해 로깅)**: spawn_capture / **reshape_capture**(¬clean_reset ∧ clean_later ∧ captured) / missed_spawn_clean / false_fire / improved_nonclean(ΔΦ>0) / recoverable_reshape_capture. **성공 = P(capture | reset-nonclean, recoverable) LCB₉₅ > 0.**
- **U-5 게이트**: 고정 CRN bank 80~100판, LCB/UCB confidence 히스테리시스(전진 LCB>p_adv, 후퇴 UCB<p_back) — **명시적 사전등록 개정**(20판·단순 문턱의 오실레이션은 (kk) 실측).
- **U-6 진단 로깅(다음 런 공통 탑재)**: reset_clean per-episode, TPR/FPR = P(fire|reset-clean)/P(fire|reset-nonclean), fire-logit AUC(reset-clean·robust-clean), fire vs continuous PPO ratio 분리 로깅(joint-ratio clip 간섭 점검).
- **U-7 스코프**: 3-seed 기전 실험 → reshape_capture 발생 시에만 10-seed confirmatory.

## 3. A-3d 예비 설계 (G0 시 직행; 피드백 #10)

**full-state 궤적 되감기**: R0 정책(= 검증된 성공-포획 궤적 생성기, 파일럿 ckpt 3본)로 witness 스폰 rollout → 포획 성공 궤적의 t−k 스냅샷(리미터 **위치+속도**, 공격자 상태, FSM/시계 포함)을 뱅크로 → k를 1→2→4→…로 늘리며 후진. position-noise와 달리 리미터가 "창을 추적 중인" 동역학적 상태에서 출발 — 회복가능성이 구성상 보장(그 궤적이 실제로 포획에 도달했으므로). 구현 요건: reset_to 확장(리미터 속도 주입 — env_m3 이미 velocity 필드 오버라이드 가능, spawn dict에 limiter_v 추가) + rollout 스냅샷 수집기.

## 4. 클레임 경계 (피드백 §9 채택 — 집필 시 준수)

지지: privileged robust-스폰 말단 습득 · oracle→learned 연결 · position-noise 커리큘럼의 스폰-운 천장 · 모드 분기(전역 bias 양극단). 불지지: 능동 재성형 · nominal 포획 · 선택적 발사 classifier · robust 일반화 포획. "스폰-운 천장" 정식화 = episode-paired immediate-fire oracle 대비 excess capture CI.
