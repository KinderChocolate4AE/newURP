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

## 6. 개정 r2 (2026-10-04, run1 진단 후 — 사용자 승인)

run1 (8.2×10⁶ step) 진단: 방어 승률 1~5% 정체. 궤적 = net 발사 유도 → 회피 → 재진입 침투
(공격자의 **미끼 전술 창발**), 그동안 limiter 무장 0.00 — kinetic fallback 미탐색 (BC 가
"limiter 비무장" 을 가르쳐 무장 확률 ≈ 0). 공격자 스타일 z 무시 (판별기 MSE 0.33 = 무작위).

| 변경 | 내용 | 근거 |
|---|---|---|
| **scripted/BC 방어에 kinetic fallback** | net 소진 (miss handoff) 후 limiter 무장 → FCS PN 인계 (= B0 v3 "NET_FAIL 후 PN takeover") | 사다리 상대 scripted+fallback 방어 40판 중 HARD_KILL 18, 침투 1 |
| **방어자 이동 = 위치 목표 (station point)** | 이동 3채널 c∈[−1,1]³ → 자산 + c·(80, 80, 10) m, 하위 PD (kp 8, kd 4) | 가속 행동은 탐색 노이즈가 적분 → limiter 산개 → fallback 이 결정적 23/24 vs 확률적 2/24. 위치 목표로 확률적 17/32 (결정적 31/32) |
| 탐색 std | lim·fin log_std −2.0 (위치목표 ≈ 11 m), att −1.6 | 확률적 BC 검증 최적 |
| 팀별 lr | 방어 3e-5, 공격 1e-4 | 방어 1e-4 에서 step 당 KL 0.1~0.3, 공격 3e-5 에서 KL 1e-4 (정체) |
| 다양성 | **패널티** −5e-3·clip(3·MSE, 0, 1) /step | 양수 보상은 episode 연장으로 긁기 가능; 1e-3 은 무시됨 |
| BC fit 스레드 | min(4, workers) | run1 BC fit 단일 코어 |

구조적 관찰: 곧장 들어오는 (homing+흔들림) 공격자는 net miss 후 0.5 s 안에 자산 도달 +
limiter 출발점 (2 m) 이 no-kinetic zone (6 m) 안 → fallback 불가. kinetic 으로 막으려면
**limiter 가 6 m 밖 공격 경로 위에 사전 배치** 돼야 한다 — failsafe·shaping 배치 학습의
구조적 동기.

## 7. 개정 r3 (2026-10-04, run2 진단 후 — 사용자 승인 "A안 + 추천 묶음")

run2 (1.6×10⁷ step) 진단: 학습은 됨 — 고정 사다리 상대 방어 승률 41% → 67% (확률적),
결정적 평가 net 포획 44/48 (scripted net 25/48, 보상 환산 학습 ≈ +40 vs scripted ≈ +36.5).
그러나 RL 공격자 상대 학습·scripted 방어 모두 ≈ 0/48. 원인 = ROE: net 은 16 m 에서 쏴도
0.4 s 판정 → 공격자 ≈ 7 m, no-kinetic zone 6 m → **합법 kinetic 시간창 ≈ 0**, 그리고
net 소진 전 kinetic = −1 → 회피 기동 공격자에게 방어 수단이 net 한 발뿐.
측정: scripted kinetic-first (공격자 50 m 안에서 무장) 는 사다리 31/32, 흔들리는 homing 32/32.

| 변경 | 내용 |
|---|---|
| **ROE A안** | net 소진 전 kinetic 무력화 = `K_FIRST`, 보상 +0.5 (fallback HARD_KILL 과 동일, `FS1Spec.r_kfirst=None`). 6 m no-kinetic zone 유지. H_illegal 사건은 `K_FIRST` 라벨로 계속 집계 |
| BC kinetic-first 혼합 | episode 30% 가 kinetic-first 변형 (`KFIRST_R=50 m`) — 탐색 출발점 |
| 초기 방어 pool | scripted net-first (`scripted_fin12`) + scripted kinetic-first (`scripted_kfirst50`) |
| 학습 균형 | 방어 2 iter : 공격 1 iter, 승률 snapshot 최소 간격 10 자기 iter (run2: pool 105 vs 10) |
| 다양성 재설계 | 이산 스킬 8 (one-hot), 평균 4 s 유지, 판별기 cross-entropy, 패널티 −5e-3·(1−q(z|s)) |
| mode 감시 | 로그 `labels_by_kind`: 상대 유형 (scripted / RL) 별 NET / K_FIRST / HARD_KILL / 침투 |

관찰 (보고 전용, 2026-10-04 — JAX 세션 지적을 main 에서 재측정): scripted r_fire + fallback,
24판씩 (homing = RL 공격자 base, residual 0 / P1a 사다리). r_fire 12: 16/24 (전부 net, miss
handoff 0회) / **24/24 (HARD_KILL 14)** · 16: 0 / 2 · 24: 0 / 1 · 40: 4 (HARD_KILL만) / 7 ·
kfirst50: 24 / 24. → homing 상대로 pool `scripted_fin12` ≡ net-only (fallback 구조적 불가),
사다리 상대로는 fallback 유효. net 포획은 r_fire ≤ 12 m 에서만 성립 → "넓은 r_fire 로
net-후-kinetic" 은 K_FIRST 에 지배됨 (A안 근거 보강). 최강 scripted = kfirst50 (평가 계약 불변).

mode 퇴화 판정 기준 (보고): 직선·사다리 공격자에게도 K_FIRST 만 쓰면 퇴화 (net +1 기회를
버림). 기대 결과: 예측 가능한 공격자 → net-first, 회피 공격자 → K_FIRST (mode-rank reversal).

## 8. 평가 계약 v1 (봉인, run3 harvest 전 — 사용자 승인 2026-10-04)

manifest `artifacts/fs1/eval_v1_manifest.json` (`scripts/fs1_eval_manifest.py`, hash 는 파일 참조),
실행 `scripts/run_fs1_eval_server.sh`, 도구 `shepherd/fs1/eval.py`. §4 를 구체화한다.
봉인 시점까지 본 결과 = 학습 로그와 iter 119 임시 평가 (노트 2026-10-04e) 뿐.

| 항목 | 내용 |
|---|---|
| 정책 | 학습 run 의 **최종** ckpt (total_steps ≥ 1.1e8), iter 선택 없음. 판정 = `learned_det` (결정적), `learned_sto` 는 보고 |
| 기준선 | `fin12` (fallback 없음) · `fin12_fb` (= 학습 pool scripted_fin12) · `kfirst50` (= scripted_kfirst50) |
| 상대 | ladder (P1a 24 × 10) · pool (최종 공격 pool nn snapshot 8개 균등 × 30) · **ex_learned / ex_kfirst50** (각 방어 전용 fresh exploiter, 같은 예산 1e7 step, `train --exploit`) · rl_latest (보고만) |
| 표본 | 셀당 240, seed0 261000, 그룹 안 episode i 시드 = seed0+i (모든 방어 paired) |
| 판정 | D_pool = L − max scripted (pool), D_ex = L(ex_learned) − kfirst50(ex_kfirst50), 둘 다 **≥ +24 (+10%p)** → `FS1_POSITIVE`; 이때 D_ladder ≤ −24 면 `FS1_POSITIVE_NARROW` (적응형에서만 이득, 퇴화 경고). 아니면 `FS1_NULL` (해당 seed). 무효 조건 → `INVALID_FS1E` |
| 보고 (판정 외) | net / K_FIRST / fallback / 침투, 상대 유형별 K_FIRST 비율 (mode-rank reversal), 무장·발사 거리, 교차 exploiter, 궤적 그림 |
| 반복 | run3 = training seed 0 → 잠정. **확정 = seed {0,1,2} 중 ≥ 2 개 POSITIVE(또는 NARROW)** |

exploiter 공정성: 학습 방어 exploiter 는 판정 대상과 같은 결정적 정책을 상대로 학습한다.
