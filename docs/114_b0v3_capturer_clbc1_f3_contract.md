# B0 v3 capturer CLBC1-F3 계약

## 질문

CLBC1로 mean drift를 줄이고 F2로 조준 표본 분산을 낮춘 상태에서, FIRE head만 robust-ready 표적으로 다시 지도학습하면 soft-only 발사를 줄이고 clean N을 늘릴 수 있는가?

기존 `NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`, `STOP_F2`는 유지한다. 이 실험에는 PPO update가 없으며 W6와 PFSP는 범위 밖이다.

## 데이터와 단일 요인

각 actor seed의 봉인 CLBC1 정책을 재구성하고 `log_std=(-2.3,-2.3,-2.3)`을 적용한다. 모든 component hash가 수확된 F2 정책과 정확히 같은지 검사한다.

별도 collection namespace에서 이 정책의 stochastic aim을 실행한다. 데이터 수집 중에만 정책이 낸 FIRE 비트를 0으로 바꿔, 조기 SPENT로 가려질 이후 상태도 수집한다. Bernoulli draw는 그대로 소비한다. 이 억제 행동은 PPO buffer, log-prob 또는 평가에 쓰이지 않는다.

현재 raw observation에는 noiseless·zero-latency `v_shot_worst`와 `p_feasible`이 있다. `p_feasible == 0`은 `boxed_in`과 동치이므로 교사 라벨은 다음과 같다.

```text
robust_ready = (p_feasible > 0) and (v_shot_worst >= 1)
```

F3 arm은 독립 MLP인 `fin_actor.fire_logit`만 fresh Adam으로 400 step 학습한다. control은 update하지 않는다. mean head, log std, limiter, critic, observation normalizer는 bit identity를 요구한다.

## 봉인 예산

- collection: `b0v3_capturer_clbc1_f3_collect_v1`, seed0 131000
- actor seed별 28 cell × 4 episode, 총 224 collection episode
- 각 cell의 0~2번 episode는 train, 3번은 validation
- evaluation: `b0v3_capturer_clbc1_f3_eval_v1`, seed0 141000
- actor seed 0·1, arm별 28 cell × 10 episode
- evaluation 총 1,120 episode
- limiter는 scripted hold, capturer는 stochastic learned policy

## 결과 전 gate

무결성, train/validation 양 class 존재, F2 parent exact match, FIRE-head-only identity가 모두 참이어야 한다.

각 actor seed에서 validation의 `v_shot_soft≥0.9` 상태만 떼어 F3 balanced accuracy가 control보다 높고, false-positive rate가 낮으며, true-positive rate가 낮아지지 않아야 한다. 전체 LOADED 상태의 fit도 기록하지만 gate에는 쓰지 않는다.

각 actor seed의 fresh paired evaluation에서 F3는 다음을 모두 만족해야 한다.

1. clean N 증가
2. robust-ready FIRE 비감소
3. nonrobust FIRE 감소
4. SPENT_FAIL 감소
5. FIRE-to-N 증가
6. clean crossing episode 비감소

두 arm의 pooled `H_illegal`은 0이어야 한다. 모두 통과하면 `PASS_F3_TO_CAPTURER_ONLY_RL_CONTRACT_DRAFT`, 하나라도 실패하면 `STOP_F3`, 무결성 실패는 `INVALID_F3`다. PASS도 별도 capturer-only RL 계약 초안 자격일 뿐 pilot 승격이나 learned cooperation 성과가 아니다.
