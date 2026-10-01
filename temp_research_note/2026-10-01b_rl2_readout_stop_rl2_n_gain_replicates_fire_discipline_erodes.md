# 2026-10-01b — CLBC1-F3-RL2 판독: STOP_RL2 — N 이득은 재현, FIRE 규율 보존은 실패

## 봉인 판정

Manifest `297d0e271393f388`, 실행 코드 `84b4517`, harvest `b685f1e`의 결과는
**`STOP_RL2`**다. integrity 10항목(RL1 STOP acknowledgment 포함)은 전부 PASS.
실패 조항은 양 seed 공통 3종 — `nonrobust_FIRE_not_increase`,
`SPENT_FAIL_not_increase`, `FIRE_to_N_not_decrease`. 기존 `NO_SELECTION`,
`STOP_F1`, `STOP_CLBC1`, `STOP_F2`, `STOP_RL1`은 유지한다.

## 결과 (fresh namespace 171000/181000, RL1 draw 재사용 없음)

| seed | arm | N | FIRE | robust | nonrobust | SPENT | FIRE→N | crossing ep / total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | control | 79 | 80 | 79 | 1 | 1 | 0.988 | 195 / 299 |
| 0 | aim PPO | **94** | 98 | 94 | **4** | **4** | **0.959** | 183 / 312 |
| 1 | control | 96 | 96 | 96 | 0 | 0 | 1.000 | 207 / 367 |
| 1 | aim PPO | **109** | 110 | 109 | **1** | **1** | **0.991** | 227 / 399 |

## 해석

1. **조준 기제의 N 이득은 독립 표본에서 재현됐다** (+15/+13; RL1 +33/+13과 방향
   일치). control 수치도 RL1 fresh control과 정합(79↔80, 96↔96)해 평가 배선의
   이상 징후는 없다.
2. **RL1을 세운 crossing은 이번 비게이트 진단에서 혼재** — seed0 episode −12
   (total +13), seed1 episode +20 (total +32). RL1의 seed1 −6이 체계적 침식이
   아니었음을 시사하지만, 진단일 뿐 판정에 쓰지 않는다.
3. **실패의 실체: 동결된 FIRE head 아래의 분포 이동.** head는 bit-identical인데
   nonrobust FIRE·SPENT가 +3/+1씩 늘었다. 조준 mean 학습이 FIRE head가 보는
   상태 분포를 judge 경계 쪽으로 이동시켜, v_worst witness가 뒤집히는 상태에서의
   발사가 생긴다. RL1 평가 draw에서는 이 수치가 우연히 동률(3→3, 0→0)이었고
   fresh draw에서 노출됐다. 규모는 발사 ~100건당 3~4건이다.
4. **정직한 결론:** 조준-only PPO는 clean N을 늘리지만 robust FIRE 규율을 공짜로
   보존하지 않는다. "aim만 풀면 규율은 자동 유지"라는 RL1/RL2 공통 가설은 이
   계약의 엄격 부등호 기준에서 2회 연속 기각됐다.

## 다음 단계 (사용자 결정)

연속 2 STOP이므로 같은 개입의 3차 재시도는 gate-shopping 위험이 있어 권장하지
않는다. 선택지:

- **(a) capturer 체인 동결** — 확보 자산으로 마감: F3(robust FIRE head BC)가
  keeper, 조준 PPO는 "N↑·규율 소폭 침식" 기록으로 남김. W6 학습 계약 결정은
  F3 초기화 기준으로 진행.
- **(b) 기제 후속 1건** — nonrobust 증가분이 전부 judge 경계 flip인지 traces/
  evaluation 기록으로 사후 감사(posthoc, 새 실험 아님). 결과에 따라 (a)의
  기록 문구만 정밀화.
- **(c) 규율-보존형 개입 재설계** — 예: FIRE-gated aim 학습(robust 상태에서만
  credit) 같은 다른 개입의 새 계약. 이는 재시도가 아니라 다른 처치이며, 착수
  전 W6 일정(10/13)과의 우선순위 판단 필요.
