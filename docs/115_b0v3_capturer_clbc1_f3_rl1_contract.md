# B0 v3 capturer CLBC1-F3-RL1 계약

## 질문과 범위

봉인 F3 정책에서 robust FIRE head와 낮춘 조준 분산을 그대로 보존한 채 capturer의
조준 mean만 PPO로 갱신하면 폐루프 조준 오차와 clean N이 개선되는지 확인한다.
critic은 PPO 학습에 필요하므로 함께 갱신한다.

limiter는 모든 학습·평가에서 scripted hold다. 따라서 결과는 capturer 기제만 말하며
learned cooperation, learned limiter 성능, W6 진입 근거가 아니다. 기존
`NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`, `STOP_F2` 판정은 유지한다.

## 부모와 학습 경계

각 actor seed에서 F1, CLBC1, F2, F3를 봉인 데이터와 RNG로 재구성한다. 재구성 직후
모든 component hash가 수확된 F3 hash와 정확히 같아야 한다.

처리군 optimizer에는 `fin_actor.mean`과 central critic 파라미터만 넣는다.
`fin_actor.fire_logit`, `fin_actor.log_std`, limiter actor, observation normalizer는
학습 전후 bit identity를 요구한다. critic의 value normalizer는 critic과 함께
갱신한다. FIRE는 F3 Bernoulli head가 표본화하며 외부 규칙으로 강제하지 않는다.
scripted limiter 행동은 환경에만 들어가고 limiter PPO loss는 0이며 optimizer에도
limiter 파라미터가 없다.

## 봉인 예산

- 학습: `b0v3_capturer_clbc1_f3_rl1_train_v1`, seed0 151000
- actor seed 0·1, 각 32,768 env step, rollout 512, 64 update
- 평가: `b0v3_capturer_clbc1_f3_rl1_eval_v1`, seed0 161000
- 각 seed·arm별 28 cell × 10 episode, 총 1,120 episode
- 대조군: update 없는 F3 부모
- 처리군: F3 부모에서 aim mean과 critic만 PPO 갱신

평가는 기존 pilot 또는 F3의 280개를 재사용하지 않는다. 같은 actor seed 안에서 두
arm은 동일한 scenario와 episode별 torch seed를 사용한다.

## 결과 전 판정

계보, pairing, 유한성, 완료, F3 부모 exact match, optimizer 구성, 동결 component
identity, 예산이 하나라도 어긋나면 `INVALID_RL1`이다.

각 seed에서 처리군은 대조군보다 clean N이 많아야 한다. robust-ready FIRE와 clean
crossing, FIRE-to-N은 감소하지 않아야 하고 nonrobust FIRE와 SPENT_FAIL은 증가하지
않아야 한다. 양 arm의 pooled `H_illegal`은 0이어야 한다. 전부 만족하면
`PASS_RL1_MECHANISM_ONLY`, 아니면 `STOP_RL1`이다.

PASS도 작은 scripted-limiter 기제 실험의 성공만 뜻한다. 후속 성능 비교가 필요하면
새 계약과 새 평가 namespace를 다시 봉인한다.
