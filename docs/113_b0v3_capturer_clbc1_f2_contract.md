# B0 v3 capturer CLBC1-F2 계약

## 질문

CLBC1이 폐루프 mean drift를 줄인 뒤에도 남은 Gaussian 조준 표본 오차가 soft crossing을 robust capture로 전환하지 못하게 하는가?

이 실험은 CLBC1의 사후 승격이 아니다. 기존 `NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`은 유지한다. PPO update는 0회이며 W6와 PFSP는 범위 밖이다.

## 단일 요인

각 actor seed의 봉인 CLBC1 정책을 F1 checkpoint와 봉인 collection으로 재구성하고 모든 component hash가 수확된 CLBC1 parent와 정확히 같은지 확인한다.

- control: capturer Gaussian aim `log_std=(-1,-1,-1)`
- F2: capturer Gaussian aim `log_std=(-2.3,-2.3,-2.3)`

세 연속 차원은 모두 조준축이다. FIRE는 별도 Bernoulli head다. mean head, FIRE head, limiter, critic, observation normalizer, 세계와 시나리오는 두 arm에서 같다. 외부 FIRE 강제나 scripted capturer는 사용하지 않는다.

## 평가 봉인

- namespace: `b0v3_capturer_clbc1_f2_eval_v1`
- seed0: 121000
- actor seed: 0, 1
- 각 seed·arm: B2 boundary 28 cell × 10 episode = 280
- 총 예산: 1,120 episode
- limiter: scripted hold
- 두 arm은 같은 scenario, environment seed, torch seed를 사용한다.

정책 입력 observation에 든 v_shot 값과 별도로, `env.step`이 FIRE를 실제 수락한 step의 `v_shot_soft`, `v_shot_worst`, `p_feasible`, `boxed_in`, 자세·명령 각도를 기록한다. `robust_ready = not boxed_in and v_shot_worst >= 1`이다.

## 결과 전 gate

무결성 항목이 모두 참이어야 한다. 각 seed에서 F2가 다음을 모두 만족해야 한다.

1. sampled-to-mean episode 중앙값 감소
2. robust-ready FIRE 증가
3. clean N 증가
4. SPENT_FAIL 비증가
5. clean crossing episode 비감소

두 arm 모두 pooled H_illegal은 0이어야 한다. 모두 통과하면 `PASS_TO_CAPTURER_ONLY_RL_CONTRACT`, 하나라도 실패하면 `STOP_F2`, 무결성 실패는 `INVALID_F2`다. PASS도 작은 capturer-only RL 계약 작성 자격일 뿐 학습 성과나 W6 진입 판정이 아니다.
