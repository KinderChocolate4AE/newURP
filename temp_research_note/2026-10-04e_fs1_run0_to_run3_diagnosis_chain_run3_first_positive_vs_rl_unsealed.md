# 2026-10-04e — FS1 run0→run3 진단 사슬: 탐색·ROE 병목을 순서대로 풀어 run3 에서 첫 양성 신호 (RL 공격자 상대 학습 9/48 > scripted 5/48, 미봉인)

정본 설계 = docs/123 (§5 r1 · §6 r2 · §7 r3). 근거 레시피 = 노트 2026-10-04d.
**이 노트의 수치는 학습 중 로그·임시 평가값 — 양성 주장은 봉인된 평가 계약으로만.**

## 1. 진단 사슬

| run | 설계 | 예산 | 관찰 | 진단 → 다음 개정 |
|---|---|---|---|---|
| run0 | r0 (per-step FIRE, RL 공격자 가속 직접) | 9.1e6 | 양측 성공 경험 0. FIRE 확률 0.7%→0.01% 붕괴, RL 공격자 1 m 자산 미적중 | 예산이 아니라 **탐색** 문제 → r1 FCS 분리 + homing autopilot + 방어 BC |
| run1 | r1 | 8.2e6 | 방어 1~5% 정체. limiter 무장 0.00. 공격자 **미끼 전술 창발** (net 발사 유도→회피→재진입). 스타일 z 무시 | BC 가 "비무장" 을 가르쳐 kinetic fallback 미탐색 → r2 fallback BC + station point + 팀별 lr |
| run2 | r2 | 1.6e7 | 사다리 상대 41→67% (학습 확인), 결정적 net 포획 44/48 vs scripted 25/48. **RL 공격자 상대 학습·scripted 모두 ≈0/48** | **ROE**: net 0.4 s 판정 + 6 m no-kinetic zone → 합법 fallback 창 ≈ 0, net 전 kinetic = −1 → r3 ROE A안 |
| run3 | r3 (K_FIRST +0.5, BC kinetic-first 30% @50 m, 방어 2:공격 1, snapshot 최소 간격 10, 이산 스킬 8) | 1.1e8 목표 (진행 중) | 아래 §2 | — |

일반화된 교훈 (운영 메모와 중복 기록):
- BC 에 없는 행동은 탐색되지 않는다 (fallback, kinetic-first 모두 BC 혼합으로 해결).
- 가속 행동은 탐색 노이즈가 적분돼 산개 → 위치 목표 (station point) + PD.
- ROE 가 mode 공간을 닫으면 학습으로 못 연다 — 보상 구조부터 확인.

## 2. run3 중간 관찰 (iter ~119 기준)

- **경쟁 균형**: 방어 승률 33→43%, 공격 46~69% (run2 는 공격 90%+). pool 7 (방어) / 28 (공격).
- **mode 분화 초기 신호**: RL 공격자 상대 K_FIRST 가 net 의 2~3배, scripted 상대 ≈ 1:1.
  이후 군비 경쟁으로 RL 상대 K_FIRST 705→346 감소, net 으로 이동 — 아직 흔들림.
- **결정적 평가 (iter 119, 임시 스크립트)**:
  - RL 공격자 상대: 학습 9/48 (확률적 16/48) vs scripted 5/48 → **학습 > scripted**.
  - 사다리 상대: scripted 48/48 > 학습 33/48 — 학습이 fallback 을 버리고 net·K_FIRST 반반.
- **창발**: limiter 가 약 12 m 전진해 6 m zone 밖에서 kinetic 요격.
- **실패 양상**: 무장이 너무 이르다 (100 m+) → PN 이 못 따라잡음 (limiter 7 m/s² < 공격자
  20 m/s²). scripted kinetic-first 의 성공 조건은 50 m 무장.
- **다양성 미작동**: 판별기 정확도 ≈ 0.15 (우연 0.125).

## 3. 남은 약점 / 판독 시 확인할 것

1. 사다리 상대 퇴보 (48 → 33): 예측 가능한 공격자에게 fallback 을 버림. docs/123 §7 의
   mode 퇴화 기준 (직선·사다리에도 K_FIRST 만 → 퇴화) 으로 판정.
2. 무장 시점이 너무 이름 — 학습이 50 m 근방으로 수렴하는지 궤적으로 확인.
3. 다양성 판별기 무력 → 공격자 기동 variation 은 PFSP pool 다양성에만 의존.
4. 단일 seed. P2 seed 불일치 NULL 전례 → 양성이면 seed 2~3개 반복 필수.
5. 평가 상대 "최신 RL" 은 학습 상대와 겹친다 → 봉인 계약에 held-out fresh exploiter 필요.

> **정정 (10-05)**: 이 노트의 "사다리" (run1~3 pool·BC, iter 119 사다리 평가) 는 전부 **jink 0
> 변형 사다리** (FS1 ladder spec 버그 — docs/123 §8.1). P1a 공칭 사다리 수치가 아니다.

## 4. 다음

평가 스크립트 repo 편입 (`shepherd/fs1/eval.py`) → 평가 계약 봉인 (run3 harvest 전) →
harvest pull → viz-first → 봉인 계약 판독 → 노트.
