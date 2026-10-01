# 117 — Pivot: capturer 체인 동결 → 공격자 사다리 강화 → limiter-only 학습 v2 → (조건부) PFSP

- **일자**: 2026-10-01 · **상태**: 사용자 승인 (2026-10-01, "재설계 생략 + 이 수순") —
  docs/89 r5 판올림의 실행 상세. 개별 실험은 여전히 각자의 결과 전 봉인 계약을 요구한다.
- **권한**: 본 문서는 W6~W9의 작업 배분을 바꾼다 (docs/89 r5). B0 v3 세계 계약
  (`5e7b5b486b9d8a4a`), docs/80 adversary ladder, docs/102 B2, 기존 STOP/NO_SELECTION
  판정은 변경하지 않는다.

## 1. 결정과 근거

**결정 1 — capturer 체인 동결 (재설계 생략).** F1→CLBC1→F2→F3→RL1→RL2 체인은
F3 (robust FIRE head BC) 를 keeper 로 종결한다. 근거:

| 증거 | 결과 |
|---|---|
| forced-fire (9/22) | gate 제거 436발 → 회복 0. 병목은 발사 결정이 아님 |
| F3 (9/25) | robust FIRE head 로 FIRE→N ≈ 1.0 — gate 기반 자동 발사가 반복 승자 |
| RL1/RL2 (10/1) | 조준 PPO: N +15/+13 재현, 단 추가 위반 = 전부 경계 draw flip (사후 감사) |
| RL2 posthoc (10/1) | 유일한 interior 발사(sid5, soft≈1·worst=0)는 control 공통 = F3 head 기존 성질 |

잔여 margin 최적화는 발사 ~100건당 3~4건의 경계 flip 영역으로, critical path 밖이다.
F3 keeper 기록에는 sid5 성질 (soft/worst 괴리 상태에서 soft 추종 발사) 을 포함한다.

**결정 2 — pivot 가설.** b5 limiter-only (9/24) 의 "일관된 이득 없음" (−1/+5 N) 에
대한 대안 설명: **공격자가 충분히 반응하지 않는 세계에서는 limiter 조형이 만들 수
있는 것 자체가 적다.** 현 T1 은 단일 반응 모드 + **종말-한정 반응** (docs/80 §2 —
접근 구간에서 방어자 미관측) 이므로, 접근 구간 shaping 은 무반응 공격자를 상대한다.
이 가설은 결과가 아니라 **검증 대상**이다: 공격자 축을 강화한 뒤 같은 limiter-only
실험에서 학습 신호가 나타나는지로 판정한다.

**결정 3 — PFSP 는 조건부.** Gavin & Bronz 가 검증한 PFSP 는 agile evader 위에서의
방법론이다. 반응형 공격자 pool 없이 PFSP 를 열지 않는다 (빈 self-play 금지).
docs/89 의 Stage C·W18~19 배치를 당기는 결정은 P2 양성 후에만 재판정한다.

## 2. 수순 (단일축 이동 규율 — docs/80 §4 준수)

```
(D_frozen, T1 단일점)  → P1: (D_frozen, T1-family + T2)   ← 공격자 축만 이동
                       → P2: (D_learned-limiter, T1f+T2)   ← 방어자 축만 이동
                       → P3: (D, T4 PFSP) — P2 양성 시에만 재판정
```

### P1 — 공격자 사다리 강화 (defender 완전 동결: scripted hold limiter + scripted/F3 capturer)

1. **T1 family 화**: `route_gain`·`sense_range` 단일점 → 선언된 분포/격자 ensemble.
   `sense_range` 는 docs/80 §2 의 지적대로 명시적 실험 변수 (종말-한정 ↔ 전구간
   관측 포함). 이것으로 "tested local reactive threat **family**" 표현 자격 확보.
2. **T2 구현**: docs/80 §3 봉인 원칙 그대로 — 공격자 자신의 합리적 objective
   (`J_asset-progress + J_threat-avoidance + J_smoothness`, 물리 제약 준수).
   certificate 를 알고 피하는 항 금지 (oracle adversary 금지). 역할 비공개 유지.
3. **산출물**: defender 동결 상태의 (T0, T1 단일점, T1 family, T2) × 경계 지도 —
   이것 자체가 foundation 논문의 "공격자 행동 수위" 축 자산이다. baseline 수치는
   P2 의 대조 기준이 된다.

### P2 — limiter-only 학습 v2 (공격자 = P1 에서 동결한 mix, capturer = scripted/F3 고정)

- b5 의 재설계판: 동일 질문 ("limiter 학습이 hold 를 일관되게 개선하는가") 을
  반응형 공격자 mix 위에서 다시 묻는다. b5 와의 차이는 **공격자 축뿐** —
  가설 검증이 깨끗하게 분리된다.
- 결과 전 봉인 계약 필수: arm (hold / c5 / learned), seed, 예산, 평가 cell ×
  attacker mix, strict gate, 새 namespace. c5 의 H_illegal 전례 (15건) 를 고려해
  pooled H_illegal 조항 유지.
- **판정 분기**: 양성 → P3 재판정 + W10 robustness 로 연결. 무신호 → "반응성
  부족" 가설 기각 기록 (이것도 foundation 논문의 결과다 — limiter 조형 가치가
  공격자 수위에 둔감하다는 측정) 후 docs/104 Track B 로 중심 이동.

### P3 — PFSP (조건부, 별도 판올림)

P2 양성 + 공격자 pool (T1f/T2 + 필요시 T3) 확보 후에만. 그 시점에 docs/89 의
W18~19 항목 당김 여부를 별도 판올림으로 결정한다.

## 3. 어휘·판정 규율 (불변)

- "cooperation" 금지 — limiter-control opportunity (r2b closure 어휘).
- `NO_SELECTION`, `STOP_F1/CLBC1/F2/RL1/RL2`, b5 종결 전부 유지. P2 는 b5 의
  승격이 아니라 새 계약이다.
- 모든 실험: 결과 전 manifest 봉인 + fresh namespace + 판독 노트. gate 를 결과
  후에 바꾸지 않는다 (RL1→RL2 전례: 교체는 새 계약으로만).
- T2 null 이 나와도 "reactivity does not matter" 로 읽지 않는다 (docs/80 §6).

## 4. docs/89 r5 와의 관계

- W6~W9 "층2 고정 → CTDE-MAPPO 본 학습 (B-3/B-4/B-5 joint)" → **P1 → P2 로 대체**.
  joint 3-arm MAPPO 는 P2 양성 시 후속 판올림에서 복귀 검토 (NO_SELECTION 이
  유지되는 한 어차피 닫혀 있던 경로다).
- G3 (R2a, ≤10/30) · K1 (prop1, ≤10/31) · W10 robustness · G4 (W12) · W13~15
  보고서 일정 불변. P1/P2 는 이 데드라인과 병렬 트랙이다.
- stop rule PASS (9/22) 의 효력 범위는 "MAPPO 설정 pilot 투자 허용" — P2 의
  limiter-only PPO 는 그 범위 안에서 집행하되 자체 계약으로 봉인한다.
