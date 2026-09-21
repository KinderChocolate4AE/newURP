# 110 — B0 v3 MAPPO hyperparameter pilot 계약 (r1, 실행 전 봉인)

- **선행조건**: docs/107 W5 PASS, docs/109 preflight PASS
- **기계 정본**: `artifacts/marl/b0_v3_pilot_manifest.json`
  (`manifest_hash = ba64bc15fdbbd4f2`)
- **범위**: B-5형 이종 actor의 저비용 설정 선택
- **금지 해석**: 학습 성공, 협력 우월, frontier 확장, Q1 신규성의 증거로 사용하지 않는다.

## 1. 이번에 답하는 질문

본 campaign 전에 사용할 `learning rate × capturer entropy × PBRS beta` 조합을 고른다.
reward·actor·sampler·평가 grid를 함께 바꾸지 않는다. B-3/B-4 shared actor는 아직
구현되지 않았으므로 pilot 대상이 아니다.

기존 저장소의 MAPPO core를 pilot에만 사용한다. 이 core는 이전 L2 학습에서 다수 seed와
회귀검사를 통과했지만 공개 reference 구현은 아니다. docs/89의 “검증된 공개 MAPPO
reference” 조건은 아직 미충족이다. 따라서 pilot PASS만으로 본 3-seed campaign을 열지
않으며, W6 본학습 계약에서 다음 둘 중 하나를 명시해야 한다.

1. 공개 reference로 옮겨 같은 preflight·pilot 선택을 재확인한다.
2. 기존 core 사용을 정식 amendment로 승인하고 공개 reference와 작은 교차검증을 한다.

시간과 현재 코드 자산을 고려하면 2번을 추천한다.

## 2. 공통 초기화

무작위 capturer로 시작하면 설정 차이보다 우연한 조준 성공을 비교하게 된다. 다음 초기화를
모든 candidate·seed에 공통으로 적용한다.

- B2의 28개 boundary cell에서 c5 limiter와 clean-fire capturer를 실행한다.
- clean `N`으로 끝난 에피소드만 보존한다. `H_illegal`을 포함한 실패는 전부 제외한다.
- capturer의 pointing mean과 fire logit만 400 step BC한다.
- limiter는 마지막 mean layer를 정확히 0으로 만들고 RL에서 공동 학습한다.
- limiter의 stochastic exploration은 유지하며 kinetic commit head는 만들지 않는다.
- dataset은 한 번만 만들고 hash를 모든 run이 공유한다.

각 cell에서 성공 1개를 최대 6회 찾는다. 28개 중 20개 이상, 각 lambda slice에서 8개
이상을 확보하지 못하면 BC 준비가 FAIL이며 pilot을 시작하지 않는다.

## 3. 학습 분포와 예산

각 seed에서 모든 candidate가 같은 episode-index cell sequence를 소비한다.

| 구분 | 비율 | cell |
|---|---:|---|
| frontier | 70% | c1 또는 c2 |
| anchor | 20% | c0 또는 c3 |
| uniform | 10% | 해당 row의 c0~c3 |

row는 `(episode + 5×seed) mod 14`로 순환한다. sampler는 pilot에서 적응하지 않는다.
candidate마다 32,768 env step, rollout 512, seed 2개를 사용한다. 총 8 run이다.
에피소드 길이는 정책마다 다를 수 있으므로 동일 seed의 cell 순서는 같아도 고정 step
예산에서 소비한 episode 수와 실현 cell 빈도는 달라질 수 있다. 이를 run별로 전부 기록한다.

| ID | learning rate | capturer entropy | PBRS beta |
|---|---:|---:|---:|
| c0_base | 3e-4 | 0.003 | 0.2 |
| c1_entropy | 3e-4 | 0.01 | 0.2 |
| c2_low_lr | 1e-4 | 0.01 | 0.2 |
| c3_no_pbrs | 3e-4 | 0.01 | 0.0 |

gamma 0.99, GAE lambda 0.95, clip 0.2, epoch 5, hidden 128×128,
`init_log_std=-1`, value normalization과 orthogonal initialization은 공통이다.

## 4. 평가와 선택

훈련과 분리한 namespace에서 28 boundary cell × 10 episode = seed당 280 episode를
평가한다. policy는 학습 분포와 같은 stochastic policy를 쓰되 episode마다 torch seed를
고정한다. `H_illegal` 또는 `NET_SPENT`에서 credit/evaluation을 끝내며 kinetic fallback은
pilot 선택값에 합치지 않는다.

candidate 자격 조건:

- 두 seed 평균 `P(H_illegal) ≤ 0.0563`
- 두 seed 평균 `P(FIRE) ≥ 0.20`
- 두 seed 평균 `P(N) ≥ 0.10`
- 각 seed `P(N) ≥ 0.05`
- NaN·Inf·미완주 없음

`0.0563`은 B2 RULE_COOP의 탐색 기준이며 보편적 안전 허용치가 아니다. 자격 candidate
중 평균 `P(N)` 최대를 고른다. 차이가 0.01 미만이면 `P(H_illegal)`, seed 간 `P(N)`
range, candidate ID 순으로 고른다. 아무 candidate도 자격을 얻지 못하면
`NO_SELECTION`으로 끝내고 본학습을 열지 않는다.

## 5. 실행

먼저 공통 BC dataset을 한 번 만든다.

```bash
python -m shepherd.scripts.b0_v3_mappo_pilot --prepare-bc
```

그 뒤 8개 run을 병렬 실행한다.

```bash
for c in c0_base c1_entropy c2_low_lr c3_no_pbrs; do
  for s in 0 1; do
    tmux new-session -d -s "b0_${c}_${s}" -c "$PWD" \
      "python -u -m shepherd.scripts.b0_v3_mappo_pilot --run --candidate $c --seed $s --device cuda > artifacts/marl/b0_v3_pilot/${c}_seed${s}.log 2>&1"
  done
done
```

완료 후:

```bash
python -m shepherd.scripts.b0_v3_mappo_pilot --check
python -m shepherd.scripts.b0_v3_mappo_pilot --readout
```

`NTFY_TOPIC`이 설정돼 있으면 시작·완료 알림을 보낸다. checkpoint는 8 update마다 저장되며
중단 run은 같은 명령에 `--resume`을 붙여 이어갈 수 있다. resume은 bit-identical 재현이
아니며 summary에 표시된다.
BC dataset은 현재 commit의 `shepherd` 코드 tree hash와 배열 hash를 함께 기록하고,
run마다 이를 확인한다. 산출물만 커밋하여 HEAD가 바뀌어도 코드 tree가 같으면 동일한
dataset을 소비할 수 있다.

## 6. pilot 뒤 남는 gate

pilot이 candidate 하나를 선택해도 본학습 전에는 다음이 남는다.

- 공개 MAPPO reference 조건의 처분
- B-3/B-4 role-conditioned shared actor
- 세 arm 공통 initialization의 architecture parity
- 본학습 seed·checkpoint·frontier CI·중단 규칙
- PBRS beta stage-wise annealing과 네 가지 reward-hacking 진단
