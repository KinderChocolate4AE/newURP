# 112 — B0 v3 capturer CLBC1 결과-맹검 계약

## 판정 질문

F1 capturer가 실제로 방문한 `LOADED` 상태를 한 번 수집해 기존 analytic teacher
axis로 relabel하면, 같은 횟수만큼 원 BC 자료를 더 학습한 replay보다 폐루프 조준
drift가 줄어드는가를 검사한다. 이는 BC-only 기제 실험이다. PPO/RL update는 0회다.

F1의 판정은 `STOP_F1`, pilot의 판정은 `NO_SELECTION`으로 유지한다. 기존 pilot
280개와 F1 1,120개 사례는 새 arm의 선택이나 평가에 재사용하지 않는다. Track B D1,
W6 3-seed campaign, PFSP와 무관하다.

기계 정본은 `artifacts/marl/b0_v3_capturer_clbc1/manifest.json`이다.

## 공통 부모와 수집

BC seed 0과 1마다 봉인 BC dataset에서 F1(unit teacher-axis MSE, 400 step)을 다시
만든다. harvested F1 지표와 절대오차 `1e-6` 안에서 맞아야 한다. replay와 CLBC1은
동일한 F1 weights, normalizer, limiter, critic, `log_std`에서 시작하며 추가 단계의
Adam 상태는 양쪽 모두 빈 상태다.

수집 namespace는 `b0v3_capturer_clbc1_collect_v1`, seed base는 91000이다. 각 seed에서
28 boundary cell을 한 번씩 실행한다. limiter는 hold, capturer는 stochastic Gaussian
aim과 Bernoulli FIRE를 그대로 쓴다. FIRE를 강제하거나 억제하지 않는다. outcome을 알기
전에 방문한 `LOADED` 상태를 모두 보존하며 성공·실패로 거르지 않는다. label은 기존
`shepherd.train.bc_aim.teacher_axis`를 직접 호출해 만든다.

## 한 요인 학습

두 arm 모두 추가 400 step, Adam `lr=1e-3`, batch 256이다.

- `replay`: original BC 128 + original BC 128
- `clbc1`: original BC 128 + closed-loop relabel 128

replacement sampling과 RNG `actor_seed + 17301`을 고정한다. 첫 original half의 index
stream은 두 arm에서 같아야 한다. `fin_actor.mean`만 optimizer에 넣는다. 현재
`MixedActor`의 mean과 FIRE는 공유 trunk 없는 독립 MLP이므로 FIRE head, `log_std`,
limiter, critic, normalizer가 bit-identical인지 검사한다.

## 새 paired 평가와 gate

평가 namespace는 `b0v3_capturer_clbc1_eval_v1`, seed base는 101000이다. 각 BC seed와
arm에서 28 cell × 10 = 280 episode, 총 1,120 episode다. limiter는 hold이며 같은 seed의
두 arm은 scenario와 환경 잡음을 공유한다. clean N, FIRE episode/command, clean crossing,
`H_illegal`, terminal outcome, 조준·자세 각도, mean norm/std, `v_shot_soft`, net phase를
기록한다.

계보·pairing·finite·completion·공통 부모·frozen state·예산 중 하나라도 깨지면
`INVALID_CLBC1`이다. 아래를 모두 만족할 때만
`PASS_TO_CAPTURER_ONLY_RL_CONTRACT`이다.

1. seed 0과 1 각각에서 CLBC1 clean crossing episode가 replay보다 많다.
2. seed 0과 1 각각에서 CLBC1 clean N이 replay보다 많다.
3. seed 0과 1 각각에서 self-trajectory episode-mean의 mean-to-teacher angle 중앙값이
   replay보다 작다.
4. 두 arm 모두 pooled `H_illegal=0`이다.

그 밖은 `STOP_CLBC1`이다. PASS도 작은 capturer-only RL 계약을 작성할 근거만 열며,
W6·candidate selection·learned cooperation 성과를 뜻하지 않는다.

## 서버 실행

```bash
export CUBLAS_WORKSPACE_CONFIG=:4096:8
python -m scripts.b0_v3_capturer_clbc1 --smoke --device cuda
python -u -m scripts.b0_v3_capturer_clbc1 --run --seed 0 --device cuda 2>&1 | tee artifacts/marl/b0_v3_capturer_clbc1/seed0.log
python -u -m scripts.b0_v3_capturer_clbc1 --run --seed 1 --device cuda 2>&1 | tee artifacts/marl/b0_v3_capturer_clbc1/seed1.log
python -m scripts.b0_v3_capturer_clbc1 --readout
```

seed 0과 1은 서로 다른 tmux session 또는 pane에서 병렬 실행할 수 있다. 각 실행은
독립된 `seed0/`, `seed1/` 아래에만 쓴다. `--readout`은 두 seed가 모두 끝나기 전에는
`INCOMPLETE`만 반환한다.
