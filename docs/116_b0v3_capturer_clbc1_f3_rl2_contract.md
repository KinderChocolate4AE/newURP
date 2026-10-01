# B0 v3 capturer CLBC1-F3-RL2 계약

## 지위와 전제

[RL1](115_b0v3_capturer_clbc1_f3_rl1_contract.md)은 `STOP_RL1`로 봉인됐다
(manifest `8ea53634ec08e9d9`, 판독 `temp_research_note/2026-10-01`). 그 판정은
유지되며 재심하지 않는다. RL2는 RL1의 어떤 학습·평가 draw도 재사용하지 않는
**fresh namespace 독립 재현**이다. 기존 `NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`,
`STOP_F2`, `STOP_RL1` 판정은 전부 유지한다.

## 질문과 범위

봉인 F3 정책에서 robust FIRE head와 낮춘 조준 분산을 보존한 채 capturer 조준
mean(+critic)만 PPO로 갱신하면 clean N이 개선되는지 — RL1과 동일한 개입을,
조준 개입과 양립하는 gate 아래에서 독립 표본으로 재확인한다.

limiter는 모든 학습·평가에서 scripted hold다. 결과는 capturer 기제만 말하며
learned cooperation, learned limiter 성능, W6 진입 근거가 아니다. PASS가 열어주는
것은 "별도 봉인 후속" 자격뿐이고, W6 학습 계약 갱신은 그 후속에서 별도로
결정한다.

## Gate 교체의 사전 근거 (crossing 조항)

F3의 `crossing_not_decrease` 조항은 FIRE head 단독 개입에서 조준·궤적이 bit-동결
이므로 crossing 불변이 **identity 성질**이었고, N 증가를 "crossing 생성이 아닌
FIRE 선택 개선"으로 귀속하기 위한 장치였다. 조준 mean을 학습 대상으로 푸는 순간
궤적 변화는 처치 그 자체이므로, 같은 조항은 "궤적 분포 변화 금지"로 작동해
개입과 양립하지 않는다 (RL1 판독 노트 §해석 2).

따라서 RL2 gate는 다음만 요구한다 — seed별: **clean N 증가** · robust-ready FIRE
불감소 · nonrobust FIRE 불증가 · SPENT_FAIL 불증가 · FIRE→N 불감소; 전역: 양 arm
pooled `H_illegal` == 0. clean crossing의 episode 수·총횟수는 **기제 귀속용 보고
전용 진단**으로 readout에 남기되 gate에 넣지 않는다. 이 교체는 결과 열람 전에
본 계약으로 봉인하며, RL1 산출물에 소급 적용하지 않는다.

## 부모와 학습 경계 (RL1과 동일)

각 actor seed에서 F1, CLBC1, F2, F3를 봉인 데이터와 RNG로 재구성하고, 재구성
직후 모든 component hash가 수확된 F3 hash와 정확히 같아야 한다. 처리군
optimizer에는 `fin_actor.mean`과 central critic만 넣는다. `fin_actor.fire_logit`,
`fin_actor.log_std`, limiter actor, observation normalizer는 학습 전후 bit
identity를 요구한다. FIRE는 F3 Bernoulli head가 표본화하며 외부 강제가 없다.
hyperparameter는 RL1과 동일하게 고정한다 (별도 튜닝 없음).

## 봉인 예산

- 학습: `b0v3_capturer_clbc1_f3_rl2_train_v1`, seed0 **171000**
- actor seed 0·1, 각 32,768 env step, rollout 512, 64 update
- 평가: `b0v3_capturer_clbc1_f3_rl2_eval_v1`, seed0 **181000**
- 각 seed·arm별 28 cell × 10 episode, 총 1,120 episode
- 대조군: update 없는 F3 부모 / 처리군: aim mean + critic만 PPO 갱신
- RL1의 151000/161000 draw, pilot·F3의 280개 모두 재사용 금지

## 결과 전 판정

계보, pairing, 유한성, 완료, F3 부모 exact match, optimizer 구성, 동결 component
identity, **RL1 STOP acknowledgment**, 예산이 하나라도 어긋나면 `INVALID_RL2`.
gate 조항 전부 만족이면 `PASS_RL2_MECHANISM_ONLY`, 아니면 `STOP_RL2`.

PASS도 scripted-limiter 기제 실험의 성공만 뜻한다. manifest
`297d0e271393f388`.
