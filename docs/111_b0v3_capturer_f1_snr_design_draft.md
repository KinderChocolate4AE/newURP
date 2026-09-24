# 111 — B0 v3 capturer F1 조준 SNR 수정 설계 초안

- **상태:** 결과 전 **봉인** (2026-09-24). 기계 정본 = `artifacts/marl/b0_v3_capturer_f1/manifest.json` (`manifest_hash` `aca08029be1a2fb9`, builder `scripts/b0_v3_capturer_f1_manifest.py`). 실행기 `scripts/b0_v3_capturer_f1.py`, 회귀검사 `tests/test_b0_v3_capturer_f1.py`. 문서와 manifest가 다르면 manifest가 우선한다. capturer-F1은 mode-switch Track B의 F1-E와 무관하다.
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

## 봉인 시 확정·처분 사항 (2026-09-24, 결과 전)

- **cosine 대조의 앵커 허용오차:** `diag.log`에 따르면 원 pilot과 진단의 CUDA 실행은 `CUBLAS_WORKSPACE_CONFIG` 없이 돌았다(결정론 경고 기록). 이번 실행은 그 설정을 요구하므로 bit 단위 드리프트가 생길 수 있다. 판정 규칙: `bc_init.json` 여섯 지표의 |Δ|가 모두 0이면 `exact-metric-match`, 모두 1e-6 미만이면 `metric-close(<1e-6)`, 그 밖은 `metric-mismatch`로 보고 full run을 중단한다. 1e-6 구간은 capturer 진단과 같은 기준이다. smoke에서는 판정을 보고만 하고 중단하지 않는다. CPU 결과는 원 CUDA 지표와 다를 수 있기 때문이다.
- **BC 재구성 단위:** `seed_everything(seed)` → `PilotRunner(pilot manifest, c0_base, seed)` → BC 초기화. cosine 대조는 `initialize_from_bc`를 직접 호출하고, F1은 `initialize_from_bc_f1`을 호출한다. F1 함수는 pilot 함수의 사본이며 조준 손실 줄만 다르다. 이는 AST 소스 diff 테스트로 고정한다.
- **동일성 검사 (위반 시 smoke·full 모두 중단):** BC 전 상태 hash(actor·critic·obs norm), FIRE head가 입력으로 받은 minibatch 열의 hash, BC 후 FIRE head·limiter·critic·log_std·obs norm의 bit 동일성, limiter mean 0, `log_std=-1`을 검사한다. 조준 head가 실제로 달라졌는지도 함께 확인한다.
- **smoke:** bc_seed 0, 첫 2 cell × 1 episode × 2 objective = 4 episode. 산출물은 `artifacts/marl/b0_v3_capturer_f1/smoke/`에 쓰고 gate에서 제외한다.
- **trace:** manifest에 고정한 네 scenario(`r00c1/0`, `r00c2/10`, `r07c1/140`, `r13c2/270`)의 평가 episode를 그대로 저장한다. 재실행하지 않으며 gate에서 제외한다. 렌더: `python -m scripts.render_capturer_traces artifacts/marl/b0_v3_capturer_f1/seed{0,1}/traces`.
- **RL:** optimizer update 0회. 테스트는 `MAPPOTrainer.update`, `M4Runner.update`, `M4Runner.collect_rollout`를 예외로 바꾼 상태에서 smoke 전 경로를 돌려 이를 확인한다.

### 서버 실행 순서

```bash
export CUBLAS_WORKSPACE_CONFIG=:4096:8
python -m scripts.b0_v3_capturer_f1 --smoke --device cuda     # 앵커 판정 확인 (mismatch면 멈추고 보고)
python -u -m scripts.b0_v3_capturer_f1 --run --bc-seed 0 --device cuda
python -u -m scripts.b0_v3_capturer_f1 --run --bc-seed 1 --device cuda
python -m scripts.b0_v3_capturer_f1 --readout
```

산출물: `seed{0,1}/summary.json`·`.done`·`traces/trace_*.json` (4 × 2 objective), `readout.json`. canonical 결과는 별도 harvest 커밋으로 분리한다.
