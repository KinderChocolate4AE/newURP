# 2026-10-01c — RL2 사후 감사: PPO가 추가한 nonrobust 발사는 전부 draw flip, 유일한 interior 사례는 control에도 동일 존재

## 지위

읽기 전용 사후 감사다 (`scripts/b0_v3_capturer_clbc1_f3_rl2_posthoc.py`, 정본
`artifacts/marl/b0_v3_capturer_clbc1_f3_rl2/posthoc_fire_discipline_readout.json`,
lineage/pairing valid). **`STOP_RL2`와 gate는 불변**이며, 이 감사는 2026-10-01b
노트 §해석 3의 "분포 이동" 문구를 정밀화할 뿐이다. 새 실험·새 promotion 없음.

## 분류 결과 (nonrobust accepted FIRE 전수)

| seed | arm | draw flip | interior | 비고 |
|---|---|---:|---:|---|
| 0 | control | 0 | 1 | sid5 (r00c1, t=19) |
| 0 | aim PPO | 3 | 1 | interior = **같은 sid5, 같은 t=19** |
| 1 | control | 0 | 0 | |
| 1 | aim PPO | 1 | 0 | |

- **draw flip** = 정책 입력 관측은 `v_shot_worst=1`(robust)인데 같은 step의
  authoritative judge 재표본이 0 — `shepherd/env.py`의 알려진 MC witness 재표본화
  성질로, F3 잔여 3건과 동일 기제다.
- **interior** = 정책 입력부터 `v_shot_worst=0`인데 발사. seed0 sid5 한 건뿐이며
  `v_shot_soft ≈ 0.90~0.999` / `v_shot_worst = 0.0` 상태에서 동결 F3 head가 쏜
  사례다. **control과 PPO 양쪽에서 같은 scenario·같은 step에 발생**하므로 paired
  비교에서 상쇄되고, 조준 개입이 만든 것이 아니라 fresh eval draw가 노출한
  **F3 head의 기존 성질**(soft 매우 높음 + worst 0인 상태에서 발사)이다.
- 모든 arm에서 SPENT_FAIL scenario 집합 == nonrobust FIRE scenario 집합 (정확히
  일치). 즉 RL2의 SPENT·FIRE→N 조항 실패는 nonrobust 발사와 동일 사건의 다른
  표현이다.

## 정밀화된 결론

1. **조준 PPO가 '추가'한 규율 위반(+3/+1)은 전부 draw flip이다.** 내부 위반
   추가는 0건. 따라서 "규율 침식"의 실체는 정책이 robust 경계 **바로 위** 상태
   (유한 MC witness가 draw에 따라 갈리는 영역)로 분포를 더 밀었다는 것이지,
   명백히 nonrobust인 상태에서 쏘도록 바뀐 것이 아니다.
2. 다만 draw-flip 빈도 증가 자체가 경계 근접의 실측 신호이므로, RL2 gate의
   엄격 부등호가 이를 STOP으로 판정한 것은 계약대로이며 번복하지 않는다.
3. **F3 head의 신규 발견 성질**: fresh draw에서 soft≈1·worst=0 상태에 발사하는
   사례가 양 arm 공통 1건 존재 (F3 원 평가에서는 미노출). F3를 keeper로 쓸 때
   이 성질을 기록에 포함해야 한다 — head는 soft/worst 괴리가 큰 희귀 상태에서
   soft 신호를 따른다.

## 다음

체인 처분 결정(동결 vs 규율-보존형 재설계)은 사용자 몫. 이 감사로 (a) 동결 시
기록 문구는 "조준 PPO는 N을 늘리고, 추가 위반은 경계 draw flip에 한정"으로
정밀화되고, (c) 재설계를 택할 경우 표적은 FIRE head가 아니라 **경계 근접 상태의
가치 추정** (예: robust margin을 보상/관측에 노출) 쪽임이 좁혀졌다.
