# 2026-10-01d — capturer 체인 동결 + pivot 승인: docs/117 신설, docs/89 r5 판올림

## 결정 (사용자 승인, 2026-10-01 "재설계 생략 + 이 수순")

1. **capturer 체인 (F1→CLBC1→F2→F3→RL1→RL2) 동결.** 규율-보존형 재설계는
   착수하지 않는다. keeper = **F3** (robust FIRE head BC, FIRE→N ≈ 1.0, N 79~96/280
   ≈ scripted launcher 의 55~65%). keeper 기록에 sid5 성질 포함 (soft≈1·worst=0
   상태에서 soft 추종 발사 — fresh draw 에서 노출된 head 의 기존 성질).
2. **W6~W9 재배치 (docs/89 r5)**: joint 3-arm CTDE-MAPPO → **P1 공격자 사다리 강화
   (T1 family + T2 구현, defender 완전 동결) → P2 limiter-only 학습 v2 (반응형
   공격자 mix 위에서 b5 질문 재실험)**. 상세 = `docs/117`.
3. **PFSP (T4) 는 조건부** — P2 양성 + 공격자 pool 확보 후 별도 판올림. 빈
   self-play 금지.

## pivot 가설 (검증 대상이지 결론 아님)

b5 (9/24) 의 limiter 학습 무신호는 limiter 조형 가치의 부재가 아니라 **공격자
반응성 부족** (T1 = 단일 모드 + 종말-한정 관측) 때문일 수 있다. P1 에서 공격자
축만 올리고 P2 에서 같은 질문을 다시 물어 분리 검증한다. P2 무신호면 가설을
기각하고 그 자체를 foundation 결과 ("limiter 조형 가치가 공격자 수위에 둔감") 로
기록한 뒤 docs/104 Track B 로 중심 이동.

## 불변 사항

- B0 v3 `5e7b5b486b9d8a4a` · docs/80 사다리 (T2 설계 원칙 §3, 단일축 이동 §4,
  null 해석 §6) · `NO_SELECTION` · 전 STOP 판정 · b5 종결.
- G3 ≤10/30 · K1 ≤10/31 · W10 · G4 (W12) · 보고서 W13~15.
- 어휘: "cooperation" 금지 (limiter-control opportunity).

## 다음 작업 (의존 순서)

1. P1 설계 계약: T1 family 분포 (route_gain × sense_range 격자, 전구간 관측 포함)
   + T2 objective 가중 (w_p, w_r, w_s) + 평가 cell — 결과 전 봉인.
2. T2 구현 (docs/80 §3 금지 조항 준수) + defender-frozen 경계 지도.
3. P2 limiter-only v2 계약 (공격자 mix 동결 후).
4. 병렬: G3·K1 트랙 착수 (10월 말 데드라인).
