# 2026-09-24b — capturer-F1 BC-SNR 봉인 (결과 전), 서버 실행 대기

**판정:** 결과를 보기 전에 봉인했다. 봉인 대상은 manifest `aca08029be1a2fb9`, 실행기, 테스트다. RL update는 0회이고, 이번 결과는 selection에 쓰지 않으며 W6는 닫혀 있다. capturer-F1은 mode-switch Track B의 F1-E와 무관하다.

- 한 요인: BC 조준 손실 `mean(1−cos(μ,â))`를 `F.mse_loss(μ, â)`로 바꾼다. F1 BC 함수는 pilot `initialize_from_bc`의 사본이고, AST diff 테스트가 조준 손실 줄 외의 차이를 막는다.
- 동일성: 두 objective에서 BC 전 상태 hash, FIRE head 입력 minibatch hash, BC 후 FIRE head·limiter·critic·log_std·obs norm이 같아야 하며 어긋나면 중단한다. smoke 테스트는 CPU에서 PASS했다(`.venv` torch 2.12.1+cpu). 이 테스트는 결과 수치를 판독하지 않는다.
- 평가: namespace는 `b0v3_capturer_f1_eval_v1`/81000이다. 28 cell × 10 episode × 2 objective × 2 seed로 총 1,120 episode를 돌린다. limiter는 scripted c5, capturer는 stochastic 조준에 Bernoulli FIRE를 쓴다.
- 계약과 원자료의 충돌: 원 pilot과 진단은 `CUBLAS_WORKSPACE_CONFIG` 없이 돌았다(`diag.log` 경고). 이번 실행은 이 설정을 요구하므로 앵커 허용오차를 결과 전에 정했다. 여섯 지표의 |Δ|가 1e-6 미만이면 통과, 아니면 중단이다. 상세는 docs/111 끝 절에 있다.
- 다음: 서버에서 cuda smoke로 앵커 판정을 먼저 확인하고, seed 0과 1을 순차 실행한 뒤 readout을 만든다. 결과는 별도 harvest 커밋으로 올린다.
