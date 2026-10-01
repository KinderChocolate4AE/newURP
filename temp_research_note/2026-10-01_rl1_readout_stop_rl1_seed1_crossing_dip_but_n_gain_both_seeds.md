# 2026-10-01 — CLBC1-F3-RL1 판독: STOP_RL1 (seed1 crossing −6), 단 N 순증은 양 seed 실재

## 봉인 판정

Manifest `8ea53634ec08e9d9`, 실행 코드 `430756e`, harvest `b7fdb97`의 결과는 **`STOP_RL1`**이다. integrity 9항목(lineage, pairing, finite, completion, exact F3 parent, partial optimizer, frozen identity, authoritative FIRE logging, budget)은 전부 PASS다. gate 13개 조항 중 `seed1_crossing_not_decrease` 하나만 실패했다 (224 → 218).

기존 `NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`, `STOP_F2`는 그대로 유지한다. docs/115 계약에 STOP 후속 경로는 정의돼 있지 않으므로, 어떤 후속도 새 계약과 새 namespace 봉인이 필요하다.

## 결과

| seed | arm | N | FIRE | robust | nonrobust | SPENT | FIRE→N | crossing ep | H_illegal |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | F3 frozen control | 80 | 80 | 80 | 0 | 0 | 1.000 | 194 | 0 |
| 0 | F3 aim PPO | **113** | 113 | 113 | 0 | 0 | 1.000 | **232** | 0 |
| 1 | F3 frozen control | 96 | 99 | 96 | 3 | 3 | 0.970 | 224 | 0 |
| 1 | F3 aim PPO | **109** | 112 | 109 | 3 | 3 | 0.973 | **218** | 0 |

## 해석

1. **기제 신호는 양성이다.** 조준 mean + critic만 풀었는데 양 seed에서 clean N이 +33/+13 올랐고, F3의 robust FIRE 성질(FIRE→N ≈ 1.0, nonrobust·SPENT 불변, pooled H_illegal 0)은 bit-frozen head 그대로 보존됐다. RL 갱신이 FIRE 규율을 깨지 않으면서 조준 기제만으로 N을 회수할 수 있음을 보였다.
2. **실패 조항은 crossing episode 수 하나다.** seed1에서 학습된 조준이 궤적을 바꿔 crossing episode 6개를 잃었다. 같은 seed에서 crossing 총횟수는 392 → 414로 늘었다(episode 단위만 감소). seed0는 episode 단위도 +38. F3에서는 조준 동결이라 crossing 불변이 자명했으나, 조준을 학습 대상으로 푸는 순간 이 조항은 사실상 "궤적 분포 변화 금지"로 작동한다. 조항 자체가 RL1의 개입(조준 변경)과 양립하기 어려운 설계였는지는 후속 계약 설계 시 판단할 문제이며, 이번 봉인 결과를 소급 재해석하지 않는다.
3. **teacher 이탈.** 학습 후 `mean_to_teacher_deg_median`이 5.51→8.82 (seed0), 6.76→10.36 (seed1)으로 커졌는데 N은 올랐다. PPO가 BC teacher와 다른 조준해를 찾았다는 뜻으로, teacher 추종 오차는 이후 성능 proxy로 쓰지 않는다.
4. **성능 맥락.** N 109~113/280은 scripted launcher 148/280의 약 3/4까지 회복. 단 scripted hold limiter 의존은 그대로이며 learned cooperation·W6 근거가 아니다 (readout scope 명시).

## 다음 단계

STOP이므로 docs/115 하에서 허용된 후속은 없다. 선택지는 사용자 결정 사항:
- crossing 조항을 조준-개입과 양립하는 형태(예: crossing 총횟수 기준 또는 N 분해 조건)로 재설계한 **RL2 새 계약** 봉인, 또는
- capturer 체인은 여기서 동결하고 주 달력(B2 이후 경로)으로 복귀.
