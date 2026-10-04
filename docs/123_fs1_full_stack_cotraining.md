# 123 — FS1: full-stack 공격·방어 동시학습 (MAPPO + PFSP)

- **일자**: 2026-10-04 · **상태**: 탐색 (학습 단계 자유 수정; 양성 주장용 평가만 결과 전 봉인)
- **결정 근거 (사용자, 2026-10-04)**: scripted 규칙을 하나씩 쌓는 방식은 음성만 반복
  (P1c c5 = bearing-only 골키퍼, net 결정 전 limiter 부동). 이미 검증된 방법론을 통째로
  도입해 양성부터 내고, 그 다음 ablation. scripted 공격자 pool 은 한 전략에 과적합 →
  **동시학습 + PFSP** 필요 (Gavin & Bronz 2026 근거, 노트 2026-10-04d).
- **선행 판정은 번복하지 않는다** (P2_NULL, STANDOFF_DOES_NOT_OPEN 등). FS1 은 새 세계·새 계약.
  P1d (docs/122) 는 봉인하지 않고 보류 — fwd 규칙은 scripted 기준선으로만.

## 1. 세계 (`shepherd/fs1/world.py`)

| 항목 | 값 |
|---|---|
| 물리 | B0 v3 resolver, B2 경계 cell r06c1 (χ 0.52, η 3.9, λ slice 0): 공격자 23 m/s · 20.5 m/s², limiter·finisher 7.16 m/s² · 23 m/s, net τ 0.3 s · ρ 1.77 m · 콘 8.22 m, R_nk 6 m, kill chain·contact resolver·net-miss handoff (ratified) |
| 배치 | 공격자: 자산 중심 2D 고리 R∈[100, 300] m, 방위 균등, 자산 향해 순항. limiter 4: 반경 2 m 대칭 (위상 무작위). finisher: 자산 위치. **사전 전진 배치 없음** |
| episode | 800 step (40 s, dt 0.05) |
| 관측 | 전 agent 공통 65-D (운동학 + FSM + threat; v_shot 3채널 = 0). sense ∞ 대칭 |
| 행동 | limiter: 가속 3 + kinetic commit 1 · finisher: 조준 3 + slew 1 + FIRE 1 + **병진 가속 3** · 공격자: 가속 3 |
| env 플래그 | `lean` (viability 는 FIRE tick 에만 = gate·포획 판정) · **fire gate 제거** · finisher 학습 병진. 기본 off = 기존 bit-identical |
| 처리량 | 1,172 step/s/프로세스 (기존 26, ×45) |

## 2. 보상

- 방어 (팀 공유): NET_CAPTURE/CWC **+1**, 합법 HARD_KILL (net 소진 후) **+0.5**,
  **H_ILLEGAL (net 소진 전 kinetic 무력화) −1**, 침투·timeout **−1**, limiter 소모 −0.1,
  net 발사 −0.05.
- 공격: 침투 **+1**, 무력화·timeout **−1**.
- shaping: 방어 = G&B 식 거리 패널티 (finisher–공격자 거리 × 1e-5/m/step, G&B 의
  λ_dist/λ_catch 비율 맞춤). 공격 = **potential-based** Φ = −d_asset/100
  (γΦ(s′)−Φ(s), 최적정책 불변) — 1 m 반경 자산을 무작위 탐색으로 못 맞혀 신호가 0 이던
  문제 (smoke 2026-10-04: 초기 RL 공격자 전부 timeout) 해결용.

## 3. 학습 (`shepherd/fs1/`)

- **MAPPO (CTDE)**: 방어 팀 = limiter actor (parameter sharing + one-hot id) +
  finisher actor + 중앙 critic. 공격 = actor + critic. 256×2 ReLU (G&B).
- **PFSP (G&B 설정 그대로)**: 양 팀 별도 학습 단계 교대, 각자 frozen 정책 pool.
  episode 마다 상대 1개 고정: **50% 최신 / 50% PFSP** (우선순위 f(x)=(1−x)², x = 현재
  정책의 그 상대 상대 승률 EMA). snapshot: 현재 정책의 pool 상대 평균 승률 ≥ 0.6
  (G&B 문턱 미기재 → 선언값) 또는 20 iter 경과.
- **초기 pool**: 공격 = P1a 사다리 scripted 24 config + 무작위 초기 RL. 방어 = scripted
  (finisher 고정·12 m 발사, limiter hold) + 무작위 초기 RL. **빈 self-play 방지** (docs/117).
- 롤아웃: 서버 24 코어 multiprocessing, 워커당 env 배치.

## 4. 평가 (양성 판정 — 학습 후 별도 봉인)

- 대상: 최종 방어 정책 vs (a) 학습에 쓰지 않은 held-out 공격자 (fresh exploiter 포함),
  (b) scripted 기준선 방어 (hold / c5 / fwd + 고정 finisher).
- 지표: 보호율 (net + 합법 kinetic), net 비율, H_illegal, 침투. 행동 분석: mode 선택
  (즉시 net / 지연 / kinetic fallback) 과 limiter 배치 — viz-first.
- 계약은 학습 곡선 확인 후 작성·봉인한다 (결과 보기 전).

## 5. 개정 r1 (2026-10-04, run0 실패 진단 후 — 사용자 승인)

run0 (9.1×10⁶ step) 진단: 양측 성공 경험 0 → 신호 0. finisher FIRE 확률 붕괴 (0.7% → 0.01%),
RL 공격자는 1 m 자산을 탐색 노이즈 (~15 m/s²) 때문에 못 맞힘. 예산 문제가 아니라 탐색 문제.

| 변경 | 내용 | 근거 |
|---|---|---|
| **사격통제 분리 (FCS)** | 정책 = 전술, FCS = 정밀 실행. finisher 행동 `[가속3, r_fire∈[4,16] m, arm]` — 포탑 자동 추적, arm∧LOADED∧d≤r_fire 면 발사. limiter 행동 `[가속3, arm]` — arm 이면 기존 PN 종말유도 + commit_margin 기하 충족 시 commit | 확률적 per-step 발사는 hazard 누적으로 30 m 밖 조기 발사 (BC 검증), 조준 수 도 오차로 net 반경 이탈. "즉시 vs 지연" 은 arm 시점·r_fire 선택으로 학습 대상 유지 |
| **공격자 autopilot + 전권 residual** | 가속 = 자산 homing (속도추종 K=4/s) + residual (\|·\| ≤ 2·a_max, 합 clip a_max) | residual 0 = 침투 보장, 잠시 homing 을 완전히 덮어쓴 이탈·baiting 가능 |
| **기동 다양성 (DIAYN 식)** | 스타일 z∈U[−1,1]³, episode 시작 + 평균 2 s 간격 재추출, 공격자 관측에만. 판별기가 LOS 좌표계 속도·가속에서 z 예측 → 공격자 보상 +1e-3·(1−3·MSE) | 사용자 요구: 장기적으로 유도되지만 잠시 벗어나는 randomized 회피 기동의 variation |
| **방어자 BC 초기화** | scripted FCS 방어 (정지·무장·r_fire 12 m) 모방 + DART 실행노이즈 (0.3·a_max) | 첫 iter 부터 포획 경험. 공격자는 BC 불필요 (autopilot) |
| **PPO 안정화** | target-KL 0.03 조기종료, lr 1e-4, 탐색 std (fin 0.37, lim 0.37, att 0.2) 선언값 | 좁은 BC 정책에서 Adam 초기 step 이 logp 를 수십 nat 이동 (ratio 1e-21) |
| RunningNorm std 하한 1.0 | 데이터에서 상수였던 채널의 폭주 방지 | BC rollout OOD 폭주 |

관찰 (보고 전용): homing 공격자에 8 m/s² 무작위 흔들림만 더해도 scripted net 방어 포획
19/30 → 3/30 — 속도 기반 net 중심 예측이 무력화. 다양한 회피 기동이 방어 학습의 실질 압력.
