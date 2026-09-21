# 109 — B0 v3 MAPPO pilot preflight 계약 (r1)

- **선행 gate**: docs/107 W5 PASS
- **목적**: B0 v3와 기존 MAPPO core 사이의 reward·termination·action 배선을 실제
  한 번의 optimizer update로 검사한다.
- **지위**: interface smoke다. 학습 성능, hyperparameter 우열, 협력 효과의 증거가 아니다.

## 1. 감사 결론

기존 `train_m4.py`를 그대로 쓰면 B0 v3 학습 계약과 맞지 않는다.

1. 구형 `RewardSpec`은 dense reward와 kinetic 결과를 포함한다.
2. 물리 환경은 `NET_SPENT` 뒤의 fallback을 계속 적분하므로 rollout credit도 계속된다.
3. 기존 potential은 구형 세계 상수에 묶여 있다.
4. 기존 limiter commit head를 켜면 NET 단계에 kinetic action authority가 생긴다.
5. 현재 actor는 limiter와 capturer가 분리된 B-5형이다. B-3/B-4의 role-conditioned
   shared actor는 아직 없다.
6. 기존 core는 저장소 자체 구현이다. docs/89의 "검증된 공개 MAPPO reference" 조건은
   본 학습 전까지 별도로 해소해야 한다.

따라서 기존 학습 명령을 B0 v3 본 학습에 재사용하지 않는다.

## 2. 이번 preflight의 고정 계약

- task reward: clean `NET_CAPTURE`만 `+1`; 그 밖의 정상 실패는 `0`.
- 비인가 kinetic engagement: `-1` 후 credit 종료.
- `NET_SPENT`: 물리 환경은 그대로 두고 RL view만 즉시 종료.
- same-tick precedence: engagement가 capture·`NET_SPENT`보다 우선한다.
- PBRS: `Phi = clip(v_shot_soft,0,1)` if `p_feasible>0`, 아니면 `0`;
  terminal `Phi=0`, `beta=0.2`, `gamma=0.99`.
- limiter action: 기동 3축만 사용하고 commit head는 만들지 않는다.
- actor: 현 코드가 지원하는 heterogeneous limiter/capturer actor만 검사한다.
- world: B2 정본 manifest의 `r03c1` 한 셀. 이는 차원·배선 검사용이며 pilot sampling
  distribution을 정한 것이 아니다.
- 계산: CPU 128 step rollout 1회, optimizer update 정확히 1회.

`B0V3CreditEnv`는 내부 world를 수정하지 않고 reward·termination view만 덮는다.
내부의 post-`NET_SPENT` fallback은 평가에서 계속 사용할 수 있다.

## 3. PASS 조건

1. docs/107의 기계 판정 산출물이 PASS다.
2. limiter commit head가 없다(`lim_dim=3`).
3. 128개 rollout row가 모두 채워지고 reward가 유한하다.
4. MAPPO optimizer update 1회가 끝나며 모든 통계가 유한하다.

정본 실행:

```bash
python -m shepherd.scripts.b0_v3_mappo_preflight
```

산출물: `artifacts/marl/b0_v3_mappo_preflight.json`.

## 4. preflight 뒤에도 남는 W6 항목

- training cell sampler와 별도 seed namespace
- pilot hyperparameter 후보·예산·선택 규칙
- 고정 evaluation grid와 checkpoint 선택 규칙
- capturer/fire BC 및 limiter neutral initialization
- B-3/B-4 role-conditioned shared actor 구현 여부
- 공개 MAPPO reference 채택 또는 자체 core 허용 근거
- 본 3-seed campaign 중단 규칙과 실패 판정

이 항목을 W6 training contract로 봉인하기 전에는 본 학습을 시작하지 않는다.

