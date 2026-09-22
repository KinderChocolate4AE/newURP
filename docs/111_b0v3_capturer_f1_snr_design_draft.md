# 111 — B0 v3 capturer F1 조준 SNR 수정 설계 초안

- **상태:** 결과 전 설계 초안. 이 문서만으로 F1 실행을 허용하지 않는다. 실행 전 별도 기계 manifest와 구현·회귀검사를 대조해 봉인한다.
- **세계:** B0 v3 `5e7b5b486b9d8a4a`, 기존 B2 boundary cell 정의와 봉인 BC dataset `b48aad5eab4a92bd`를 읽기 전용으로 사용한다.
- **근거:** `temp_research_note/2026-09-22e_capturer_diag_readout_h1_sampling_snr.md`, `artifacts/marl/b0_v3_pilot/diagnostic/capturer_diag_c0_base_s0.json`. c0/seed0 재구성 BC 직후 stochastic N 9/280, mean-axis N 63/280; 교사 상태에서 mean 크기 0.162, 조준 표준편차 0.368, 표본각 중앙값 75.2°. 이 280사례는 기제 진단에만 쓴다.
- **질문:** BC 평균 조준 벡터의 크기를 교사 단위축에 맞추면, *새* paired scenario에서 BC 직후 stochastic capturer가 clean crossing과 clean N을 더 자주 만드는가?

## F1 한 요인

기존 BC의 조준 손실 `mean(1 − cos(μ, â))`을 아래 손실로 **교체**한다.

```text
â = teacher_axis / ||teacher_axis||
L_axis = mean(||μ(obs) − â||² / 3)
L_total = L_axis + 기존 class-balanced BCEWithLogits(FIRE)
```

`μ`는 actor의 Gaussian mean을 *clipping 이전*에 읽는다. 교사축의 각 성분은 [-1,1]이고 단위 길이이다. MSE의 방향·크기 최적점은 `μ=â`이다. 별도 크기 가중치나 두 번째 조준 손실을 추가하지 않는다. BC step 400, batch 256, Adam lr 0.001, BC dataset, actor 구조·초기 seed, FIRE head 손실·표본 방식, capturer `log_std=-1`, limiter neutral 초기화, 정규화 초기화는 원 pilot과 같다. `shepherd/` 봉인 코드와 기존 pilot manifest·checkpoint를 수정하지 않고, 별도 `scripts/` 실행기로 분리한다.

F2 (`init_log_std=-2.3`)는 이 실험에 포함하지 않는다. 현재 `MAPPOConfig.init_log_std`는 limiter와 capturer 양쪽 actor에 전달되므로 전역값만 바꾸면 한 요인 비교가 아니다. BC mean 크기를 0.162로 남기면 표준편차 0.1에서도 축별 SNR은 약 1.62다. F1의 목표 mean 크기 1·표준편차 0.368이면 약 2.72다. 이는 설계상 비율이며 성능 예측치는 아니다.

## 결과 전에 기계 manifest에 고정할 계약안

| 항목 | 제안 고정값 |
|---|---|
| namespace | 산출물 `artifacts/marl/b0_v3_capturer_f1/`; 평가 `b0v3_capturer_f1_eval_v1`, `seed0=81000` (pilot 61000·b5 71000과 분리) |
| 학습 단위 | actor 초기 seed 0·1 각각에서 기존 cosine BC 대조와 F1 BC를 같은 dataset·400 step·동일 미니배치 RNG로 재구성. 원본 BC 직후 checkpoint라고 부르지 않는다. 대조의 `bc_init.json` 지표 대조에 실패하면 중단 |
| 평가 예산 | B2 boundary 28 cell × cell당 10개 = 정책당 280 episode; 2 BC seed × 2 BC objective = **총 1,120 episode**. smoke는 seed0의 첫 2 cell × 1개 × 2 objective = 4 episode, 성능 판정에서 제외 |
| paired 단위 | `(cell_id, scenario_id, χ, η)`와 env seed를 두 objective에서 일치. torch 표본 seed는 `81000 + 1,000,000×bc_seed + scenario_id`; 같은 bc_seed의 두 objective가 동일 표본 stream을 쓴다 |
| limiter·FIRE | 두 objective 모두 scripted c5 limiter 고정. capturer는 각 BC actor의 stochastic Gaussian 조준 + Bernoulli FIRE; 외부 강제 FIRE 없음. `B0V3CreditEnv`의 H_illegal/NET_SPENT cut 유지 |
| 일차 지표 | episode당 clean crossing 발생 여부와 clean N (`partition_bin`)의 paired 차이. 두 seed를 각각 표시 |
| 함께 보고 | FIRE, H_illegal, `|μ|`, 교사축에 대한 mean·표본각, 실제 자세 오차, 발사 직전 net phase. 교사 궤적 BC 손실과 자기 궤적 성능은 별도 표 |
| 중단 | dataset·세계 hash/대조 BC 지표 불일치, 1,120 episode 미완주, 비유한값, pairing 위반 시 해당 산출물 INVALID. 새 결과를 본 뒤 예산·문턱을 바꾸지 않는다 |
| 다음 단계 판정 | **두 BC seed 각각에서 F1의 clean crossing episode 수와 clean N 수가 대조보다 모두 증가**하고, pooled H_illegal 수가 대조보다 증가하지 않을 때만 별도 *소규모 RL 계약을 작성할 자격*을 준다. 그 밖에는 F1을 중단한다. 이 조건은 과학적 유의성·W6 진입·후보 선정 문턱이 아니다 |

본 단계에는 RL optimizer update가 없다. 따라서 정규화 이동과 off-manifold 잔여 gap은 F1 BC 직후 결과와 trace에서 관측하되 함께 수정하지 않는다. F1이 위 좁은 gate를 통과해도 RL 예산·초기 norm 처리·중단 규칙은 **새 계약**으로 결과 전에 정한다. 기존 pilot의 280사례, 선택 문턱, `NO_SELECTION`, B2 primary, W6/PFSP 지위는 불변이다.

## 구현·검사 순서

1. 이 초안의 값을 기계 manifest에 옮기고 builder 출력과 파일의 동치를 검사한다. 실행 시 manifest hash, B0 hash, BC dataset hash, code commit과 dirty status를 남긴다.
2. pilot BC 경로의 호출 순서·RNG·정규화·FIRE 손실을 재사용 또는 동치 검사한다. 바뀌는 계산이 `L_axis` 한 줄임을 회귀검사로 고정하고, seed0 대조가 저장된 `bc_init.json`의 여섯 지표와 정확히 일치하는지 확인한다.
3. 새 namespace smoke에서 action padding·Bernoulli FIRE·paired scenario signature·credit cut을 검사한다.
4. 전체 1,120 episode 평가 후 그림과 paired 사건을 먼저 확인하고, 위 gate를 그대로 적용한다. 수치가 좋아도 F1을 학습된 협력 성과로 승격하지 않는다.
