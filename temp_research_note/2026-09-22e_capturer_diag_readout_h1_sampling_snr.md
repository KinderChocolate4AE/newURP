# 2026-09-22 — capturer 진단 판독: BC-직후부터 on-policy 실패 (H1 확정), 주 기제 = 표본 조준 SNR

**판정:** RL은 작동하는 capturer를 파괴하지 않았다 — **파괴할 것이 처음부터 없었다.**
BC-직후 재구성 정책은 봉인 280사례에서 N 9/280으로 최종 checkpoint(14/280)와 같은
수준이다 (H2 기각). 조준을 policy mean으로 바꾸는 것만으로 N 9→**63**, clean crossing
25→**146**으로 회복되므로 주 병목은 **표본 조준 노이즈**다: BC의 cosine 손실은 조준
mean의 크기를 키우지 않아 |μ|=0.162 vs σ=e⁻¹≈0.368 (SNR≈0.44), 표본 명령이 mean에서
중앙값 **75.2°** 벗어난다. slew(ω=2 rad/s) 저역통과 후에도 자세 오차가 10~25°로 cone
반각(~12°) 위에 있어 v_shot_soft가 0에 붙고 gate가 열리지 않는다. `NO_SELECTION`과
모든 봉인 판정은 불변이다.

정본: [capturer_diag_c0_base_s0.json](../artifacts/marl/b0_v3_pilot/diagnostic/capturer_diag_c0_base_s0.json)
(+ traces/ 12쌍 JSON·PNG, diag.log). 도구·전제 = [22d](2026-09-22d_capturer_diag_tooling_bc_recon_pending_server.md).

## 1. 계보 유효성 (판독 전 확인)

- 재구성 verdict = **exact-metric-match** (cuda, bc_init.json 지표 6개 diff 전부 0,
  이중 재구성 bit-identical). 단 원본 BC-직후 checkpoint는 저장된 적 없으므로 이것은
  지표-앵커 검증이지 bit-원본 대조가 아니다 (22d 한계 유지).
- role-swap 교차검증: `final_scripted_limiter` counts {N 14, H_illegal 22, F_other 244}
  = 봉인 role-swap과 **정확히 일치** — 평가기 드리프트 없음.

## 2. paired 평가 (봉인 280, 기제 진단 전용)

| mode | N | FIRE | clean crossing | H_illegal |
|---|---:|---:|---:|---:|
| scripted both (참조, role-swap) | 148 | 279 | 280 | 20 |
| final + scripted c5 | 14 | 44 | 32 | 22 |
| **BC-직후 + scripted c5 (stochastic)** | **9** | 22 | 25 | 21 |
| **BC-직후 + scripted c5 (mean axis)** | **63** | 75 | **146** | 21 |
| BC-직후 + BC-init limiter (t=0 joint) | 8 | 19 | 21 | 0 |
| final weights + BC-시점 norm | 11 | 19 | 52 | 21 |
| BC weights + 최종 norm | 6 | 38 | 22 | 21 |

- t=0 joint 8/280 ≈ 훈련 로그의 rolling 5~6.7%와 정합 — 훈련은 시작부터 이 상태였다.
- mean-axis 63 vs scripted 148의 잔여 gap: trace에서 mean 방향은 교사궤도 위(t<20)
  에서는 1~5°지만 폐루프가 교사궤도를 떠나면(t>20) 15→130°로 발산 — **개방루프 BC의
  off-manifold 누적**이 2차 병목. (최종 checkpoint의 mean-axis는 11/280 — 회복 없음.)

## 3. 교사 적합도 행렬 — 세 기제의 분리

| weights × norm | mean cos (P50 각) | \|μ\| | 표본각 P50 | fire tpr/tnr |
|---|---|---:|---:|---|
| BC × BC | 0.9997 (1.0°) | 0.162 | 75.2° | 1.00 / 0.98 |
| BC × 최종 | 0.949 (11.2°) | 0.126 | 79.2° | 1.00 / **0.75** |
| 최종 × BC | 0.611 (28.3°) | 0.511 | 41.7° | 1.00 / 0.98 |
| 최종 × 최종 | 0.430 (34.7°) | 0.552 | 39.9° | 1.00 / 0.76 |

1. **주 기제 (표본 SNR)**: BC×BC에서 mean은 1.0°인데 표본은 75° — bc_init.json의
   cosine 0.9996은 폐루프 성능을 전혀 보증하지 않았다.
2. **부 기제 A (normalizer 이동, H3)**: 같은 BC weights가 최종 norm에서는 11.2°로
   틀어지고 fire tnr 0.98→0.75. 이동량 mean |Δz| 0.81, max 8.5; 최다 이동 dims
   14/32/11/15/29 = limiter 운동학 채널 (교사=c5 arc vs on-policy=neutral, 예상 정합).
3. **부 기제 B (RL 중 mean 방향 drift)**: 최종 weights는 어느 norm에서도 cos 0.43~0.61
   — RL 32,768 step 동안 mean 방향이 점진 열화했다. 단 이것은 실패의 **원인이 아니라
   방치된 부수 현상**이다 (성능이 시작부터 0 근처라 방향을 보존할 학습 신호가 없었음).

## 4. 이 판독이 여는 것 / 열지 않는 것

- **연다**: ① 원인 맞춤 최소 수정의 후보를 좁힘 — (F1) BC 조준 손실에 크기 항 추가
  (단위 교사축에 대한 MSE 회귀 → |μ|≈1, SNR ~2.7배) 또는 (F2) 조준 head
  `init_log_std` 하향 (−1 → 약 −2.3, σ≈0.1). **한 가지를 골라 별도 계약·새 평가
  namespace에 결과 전 봉인 후에만 실행** (docs/110 문턱·280사례 재사용 금지 불변).
  off-manifold 잔여 gap과 normalizer freeze는 그 다음 층위. ② b5 limiter-only 실험의
  실행 근거 확립 — capturer 병목이 확정됐으므로 scripted capturer 고정 arm이 의미 있음
  (22d의 봉인 manifest대로).
- **열지 않는다**: W6 본 학습, 후보 재선택, "협력 학습 가능" 주장. mean-axis 63/280은
  탐색 불가능한 결정론 조준의 사후 스위치이지 학습 결과가 아니다.

## 5. 다음 순서

1. b5 limiter-only 서버 실행 (smoke → controls → seed 0/1 → readout) — 22d runbook.
2. 조준 SNR 최소 수정 1건의 계약 초안 (F1 vs F2 선택 포함) — b5와 독립, 새 문서.
3. seed 1 / 타 candidate로의 일반화는 필요 시 같은 진단 도구로 (도구 인자만 변경).
