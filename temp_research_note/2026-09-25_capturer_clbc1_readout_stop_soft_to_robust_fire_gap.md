# 2026-09-25 — capturer CLBC1 판독: STOP_CLBC1, mean drift는 줄었지만 soft crossing이 robust capture로 전환되지 않음

**봉인 판정:** manifest `ad79a6801c494c8d`의 gate를 그대로 적용한 결과는 **`STOP_CLBC1`**이다. seed0은 세 개의 효과 조항을 모두 통과했지만 seed1의 clean N이 replay 15, CLBC1 15로 같아 strict increase 조항을 통과하지 못했다. pooled H_illegal은 두 arm 모두 0이다. 이 사후 판독은 gate를 바꾸거나 새 promotion 근거를 만들지 않는다.

정본은 `artifacts/marl/b0_v3_capturer_clbc1/readout.json`, 사후 기제 집계는 `artifacts/marl/b0_v3_capturer_clbc1/posthoc_fire_conversion.json`이다. pre-result code는 `9a45102`, harvest는 `11e6961`이며 lineage와 scenario pairing은 전부 PASS다.

## 1. CLBC1이 고친 것

| seed | arm | clean N | crossing episode | FIRE | mean↔teacher 중앙값 |
|---|---|---:|---:|---:|---:|
| 0 | replay | 5 | 38 | 34 | 38.52° |
| 0 | CLBC1 | **18** | **77** | **68** | **4.82°** |
| 1 | replay | 15 | 45 | 40 | 35.26° |
| 1 | CLBC1 | **15** | **89** | **73** | **6.24°** |

한 번의 closed-loop 상태 수집과 교사 relabel은 목표대로 mean drift를 크게 줄였다. 두 seed 모두 crossing과 FIRE가 늘었고 H_illegal은 0이었다. 따라서 F1 뒤 남아 있던 off-manifold mean drift는 실제 병목 중 하나였다.

그러나 seed1에서 FIRE가 33회 늘었는데 N은 늘지 않았다. 전체 FIRE→N 전환율은 replay 15/40=37.5%, CLBC1 15/73=20.5%로 낮아졌다. paired 결과에서 **CLBC1만 발사한 44개**는 N 4개, SPENT_FAIL 40개였다. 반대로 replay만 발사한 11개는 N 1개, SPENT_FAIL 10개였다. CLBC1이 새로 연 교전 구간의 대부분은 한 발을 소비하고 실패했다.

seed0도 같은 방향이지만 전환율은 개선됐다. CLBC1만 발사한 43개는 N 10개, SPENT_FAIL 33개였고, 전체 FIRE→N은 5/34=14.7%에서 18/68=26.5%로 올랐다. 이 seed 간 차이가 strict N gate 실패의 직접 원인이다.

## 2. 코드 의미: soft gate와 실제 capture 판정은 다르다

`shepherd/env.py`에서 clean crossing과 FSM FIRE 허용은 `v_shot_soft >= theta_fire`를 사용한다(291~315행). 반면 FIRE 순간의 실제 capture 예약은 `not boxed_in and v_shot_worst >= 1`일 때만 참이 된다(316~323행). 예약된 hit/miss는 deploy와 lock 뒤 해소되고, miss는 `SPENT_FAIL`로 끝난다(327, 359~360행).

즉 crossing과 FIRE가 늘어도 `v_shot_worst`가 1이 되지 않으면 N은 늘지 않는다. 수확 레코드에서 모든 FIRE는 N 또는 SPENT_FAIL로 끝났다. seed1 CLBC1의 73회 FIRE 가운데 58회가 SPENT_FAIL이었다. 현재 데이터가 직접 지지하는 다음 병목은 **soft-gate 진입을 robust-ready shot으로 바꾸는 전환**이다. 정확한 원인이 잔여 표본 조준 노이즈, 자세 slew와 발사 시점의 결합, cone 경계 근처의 기하 중 무엇인지는 기존 trace만으로 분리되지 않는다.

## 3. 먼저 본 고정 trace 4쌍

- `r00c1/sid0`: replay는 무발사 PENETRATED. CLBC1은 t=20에서 자세 오차 3.26°, 관측 v_soft 0.972로 발사했지만 SPENT_FAIL. 발사 뒤 공격자 회피와 함께 mean·자세 오차가 급증하고 v_soft가 무너진다.
- `r00c2/sid10`, `r07c1/sid140`, `r13c2/sid270`: CLBC1 mean은 replay보다 교사축에 훨씬 가깝지만 실제 자세는 충분히 빨리 따라가지 못해 v_soft가 0.9에 못 미치고 모두 무발사 PENETRATED로 끝난다.

그림은 `artifacts/marl/b0_v3_capturer_clbc1/seed1/traces/trace_{replay,clbc1}_seed1_*.png`에 있다. 이 네 쌍은 선택된 성공 사례가 아니라 manifest에 미리 고정된 scenario다.

## 4. 사후 감사에서 찾은 진단 코드 결함

두 결함은 평가 결과나 gate를 바꾸지 않는 **trace/시각화 결함**이다.

1. renderer가 기존 trace의 `mode`만 읽어 CLBC1의 `arm` schema를 렌더하지 못했다. `mode → arm → trace` 순서로 읽도록 수정했다.
2. 세 capturer 진단기가 flat dotted `extra_cfg`를 nested dict처럼 읽어 cone 반각과 range를 `null`로 저장했다. 향후 trace는 `viability.cone.half_angle`과 `viability.cone.range_max`를 올바르게 기록하도록 수정했다. 이미 봉인된 JSON의 `null`은 사후에 값을 채워 넣지 않았다.

추가 한계가 있다. 기존 `at_fire`의 v_shot 값은 정책이 받은 pre-action observation이다. `env.step`은 다음 `step_seed`로 judge를 다시 계산한 뒤 FIRE와 capture를 판정하므로, 이 값은 실제 FIRE judge의 권위 있는 로그가 아니다. seed1 `sid43`은 관측 v_worst=1인데 SPENT_FAIL이라 이 차이가 실제로 드러난다. 따라서 기존 trace에서 개별 실패의 정확한 FIRE 순간 robust margin을 복원했다고 주장할 수 없다. 사후 JSON은 이 값을 `policy_input_*`로만 표기한다.

## 5. 해석과 다음 범위

- **확정:** CLBC1은 폐루프 mean drift를 줄였고 crossing을 늘렸다.
- **확정:** 봉인 gate는 seed1 N strict increase 실패로 STOP이다. capturer-only RL 계약, W6, PFSP는 열리지 않는다.
- **확정:** seed1의 새 FIRE 대부분은 SPENT_FAIL이며 soft crossing 증가가 robust capture 증가로 이어지지 않았다.
- **미구별:** residual action sampling, 자세 slew, FIRE timing, robust cone geometry의 상대 기여도.

다음 실험을 연다면 CLBC1을 승격하는 형태가 아니라, 새 namespace에서 한 요인만 비교하는 capturer 진단이어야 한다. 가장 작은 후보는 **CLBC1 aim을 고정한 채 aim 표본 표준편차만 낮추는 arm**이다. 대조와 후보 모두 FIRE head와 세계를 같게 두고, 새 trace에는 env가 FIRE를 실제 수락한 그 step의 `v_shot_soft`, `v_shot_worst`, `boxed_in`, 자세 오차를 기록해야 한다. 결과 전 manifest에 seed, 예산, 대조, `N/crossing/FIRE/SPENT_FAIL/H_illegal` 중단 규칙을 고정하기 전에는 실행하지 않는다.
