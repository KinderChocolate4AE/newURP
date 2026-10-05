# HANDOFF — FS1 학습 엔지니어링 전담 세션 (2026-10-05)

**역할**: FS1 (full-stack 공격·방어 동시학습) 의 **학습 설계 전담** — 보상·credit·탐색·PFSP·학습률·
batch 구조를 비판하고 대안을 제안한다. **1차 agenda = §9 (특히 arm B 보상 논쟁)**.
**산출물**: 설계 메모 (제안별로 ① 추가 손잡이 수 ② episode 당 보상 크기 예산 ③ 순환성 영향
④ 지지하는 주장 유형 을 명시, 우선순위 랭킹 + 위험). **구현·계약 반영은 main 세션이 한다** —
정본 파일 (shepherd/fs1/*, scripts/*, docs/123·124, artifacts/*manifest*) 수정 금지, 프로토타입은
scratch 에서만. 봉인 전 결과 주장 금지. 어휘: "cooperation" 금지 → limiter-control opportunity.

## 1. 물리 세계 (FS1, `shepherd/fs1/world.py` — B0 v3 물리 위 교전 래퍼)

- **cell r06c1** (χ 0.52, η 3.9, λ slice 0 — B2 경계 cell: scripted 대 scripted ≈ 50:50 이 되도록
  고른 곳): 공격자 a 20.45 m/s², v 순항 23.01 / 최대 34.52 m/s. 방어 (limiter 4 + finisher 1 동일
  기체급) a 7.16 m/s², v_max 23.01 m/s → **공격자가 가속 ~3배 우세** (μ=0.35, ν=1.0 conditioning).
- net: τ_deploy 0.3 s, ρ 1.77 m, cone R_max 8.22 m. 판정 = FIRE tick 에 동결되는 robust worst-case
  judge (v_shot_worst), soft 값 v_shot_soft 도 산출. **net 포획은 실측상 r_fire ≤ 12 m 에서만 성립.**
- kill chain / ROE: **6 m no-kinetic zone** (자산 주변 kinetic 금지). net 소진 (miss handoff) 후
  limiter kinetic = HARD_KILL (+0.5). **r3 "A안"**: net 소진 전 kinetic = K_FIRST 라벨, 보상 동일
  +0.5 (r2 까지는 −1 = H_ILLEGAL 이라 합법 kinetic 창이 ≈ 0 이었음).
- 배치: 공격자 = 자산 중심 고리 R∈[100,300] m 균등 방위, 자산 향해 순항. limiter = 자산 반경 2 m
  대칭 (전진 배치 금지 — 사용자 결정), finisher = 자산 위치. episode 800 step (40 s, dt 0.05).
- **FCS 분리** (r1): 정책 = 전술, FCS = 정밀 실행. finisher 행동 [위치목표 c³, r_fire∈[4,16] m, arm]
  — 포탑은 예측 net 중심 (속도 기반) 자동 추적, arm∧LOADED∧d≤r_fire 면 발사. limiter 행동
  [위치목표 c³, arm] — **arm → 기존 PN 종말유도로 인계** (그 step 은 위치목표 무시). 위치목표 =
  자산 + c·(80,80,10) m, 하위 PD (kp 8, kd 4). 관측 = 전 agent 공통 65-D (full obs), 공격자만 +z 8-D.
- 공격자 = 자산 homing autopilot (속도추종 K=4/s) + **학습 residual (|·|≤2·a_max 전권, 합산 clip)**.
  스킬 z: one-hot 8, 평균 4 s 재추출 — **r4 에서 다양성 패널티는 0 이지만 z 는 여전히 관측에 붙음**
  (vestigial — 점검 대상).

## 2. 실험 이력과 결과 (전부 cell r06c1)

| run | 핵심 변경 | 결과 |
|---|---|---|
| run0 (9.1e6) | per-step FIRE 확률, 공격자 직접 가속 | 성공 경험 0, FIRE 확률 붕괴 → **탐색 문제** |
| run1 (8.2e6) | FCS + autopilot/residual + 방어 BC | 방어 1~5%. limiter 무장 0 (BC 가 비무장 교육). 공격자 **미끼 전술 창발** (net 유도→회피→재진입) |
| run2 (1.6e7) | BC 에 fallback, station point, 팀별 lr | 사다리 41→67%. RL 공격자 상대 ≈0 → **ROE 가 mode 공간 폐쇄** |
| run3 (1.1e8 완주) | ROE A안, BC kinetic-first 30%, 방어2:공격1 | 중반 (it~119) 방어 0.40 peak + "12 m 전진 요격" 창발 → **군비 경쟁으로 소멸**, 최종 0.11 |
| **pilot 봉인 평가** | run3 최종 ckpt, 봉인 계약 | **FS1_NULL** (D_pool −27, D_ladder −171). **★천장: kfirst50(최강 scripted) 조차 전용 exploiter(1e7) 에 3/240 = 1.3%**, 학습 9/240. 기전 = 종말 5~10 m 1회 회피가 net 조준·PN·fallback 동시 무력화 |

버그 이력: 사다리 공격자 spec 이 r0~r3 전체에서 jink 0 변형이었음 (수정됨, `ladder_attacker`).
판정: 현 cell 은 **세계 구조상 닫힘** (scripted 도 붕괴) — 학습 method 문제와 분리됨.
방향: E3 = 방어 capability (μ, ν) 격자에서 열린 cell 을 찾고 (stage 1 천장 스캔), 열린 cell 에서
stage 2 = **arm A (r4 레시피) vs arm B (r5)** 비교. 정본 계약 초안 = docs/124.

## 3. 보상 설계 현황 (r4 기준, `world.py` + `train.py`)

**방어 (팀 공유 스칼라 — limiter·finisher 동일값)**:
NET_CAPTURE/CWC **+1** · HARD_KILL/K_FIRST **+0.5** · 침투/timeout **−1** · limiter 소모 −0.1 ·
net 발사 −0.05 · shaping = **−1e-5·d(finisher, 공격자)/step** (G&B λ_dist 비율 모사).
**공격**: 침투 +1, 무력화·timeout −1, potential-based Φ = −d_asset/100 (γΦ′−Φ, 최적정책 불변).
**r4 에서 제거**: 공격자 다양성 패널티 (r3: −5e-3·(1−q), 판별기 acc 0.16 ≈ 우연 0.125 →
**episode 당 ≈ −0.74 의 순수 step 비용으로 전락** — 종말 보상 ±1 급. 이 교훈이 모든 dense 항의
심사 기준: **episode 당 기대 크기 예산을 선언하고 ≤ 0.2 로 제한**).

## 4. 학습 스택 (`nets.py`, `train.py`)

- **MAPPO CTDE**: 방어 = limiter actor (4개 parameter sharing + one-hot id) + finisher actor +
  중앙 critic (관측 = 같은 65-D; **상대 행동은 critic 에 안 들어감** — G&B 와 차이). 공격 = actor +
  critic + 판별기 (r4: 감시용만). 256×2 ReLU, 연속 = Gaussian (state-indep log_std, clamp [−3,1]),
  이산 (arm/FIRE) = Bernoulli (초기 logit −5).
- **PPO**: clip 0.2, ent 0.01, vf 0.5, grad 0.5, epoch 5, mb 4096, γ 0.997, λ_GAE 0.95, adv 정규화,
  approx-KL > 1.5×0.03 이면 epoch 중단.
- **KL 목표 lr (r4 신규)**: 자기 iter 마다 max role-KL > 0.02 → lr/1.5, < 0.005 → ×1.5,
  [1e-5, 3e-4]. 시작 방어 3e-5 / 공격 1e-4 (run3: 양측 KL ≈ 0.002~0.005 로 문턱의 1/10 — 느림).
- **BC 초기화** (방어만, `bc.py`): scripted FCS 방어 (fin12+fallback, 30% kinetic-first@50 m) 모방
  3,000 ep + DART 실행노이즈 0.15, critic 은 같은 rollout 할인 return. INIT_LOG_STD: 방어 −2.0
  (위치목표 ≈ 11 m), 공격 −1.6. **교훈: BC 에 없는 행동은 탐색되지 않는다.**
- RunningNorm: batch Welford, **std 하한 1.0**, clip ±10 (BC 상수 채널 폭주 방지).
- batch: iter 당 49,152 step. **정본 = episode 완주 수집** / JAX = env 상주 + T-step 절단 +
  bootstrap — 이 차이가 (d) 쟁점 (아래 §7).

## 5. PFSP (G&B 이식, `train.py`)

교대 학습 **방어 2 iter : 공격 1 iter** (run2 에서 공격이 앞질러 도입). episode 마다 상대 1 고정:
50% 최신 / 50% PFSP, 우선순위 f(x) = (1−x)² + 1e-3 (x = 그 상대 대비 승률 EMA, α 0.05).
snapshot: (iter 승률 ≥ 0.6 ∧ 자기 iter ≥ 10) ∨ 자기 iter ≥ 20. 초기 pool: 공격 = 공칭 사다리 24
scripted + init / 방어 = scripted_fin12 + scripted_kfirst50 + init (빈 self-play 금지).
run3 최종 pool: 방어 75 / 공격 96. **`--exploit` 모드**: 고정 방어 1개 상대로 새 공격자만 학습
(평가 계약의 전용 exploiter 생성용, 1e7).

## 6. Gavin & Bronz 2026 학습 설계 (arXiv 2607.05939 — 우리의 직접 레시피 원천, 노트 10-04d)

| 항목 | G&B | 우리와의 차이 (학습 관점) |
|---|---|---|
| 세계 | 6DOF quad, CTBR 행동, 3 pursuer (rigid net) vs 1 evader, arena 32×32×16 m, ep 10 s, 충돌 포함 | 우리: 3DOF 질점 + FCS 전술 행동, 이종 역할, kill-chain/ROE 제약, 자산 고정 기하, **공격자 가속 3배 우세** (G&B 는 동일 기체 ≈ 대등) |
| pursuer 보상 | λ_catch 10 · λ_step 0.04 (빨리 잡기) · λ_collPE 0.1 · λ_collPP 10 · λ_dist 0.001 · λ_fail 30 · λ_cmd 2e-4 | 우리: 이벤트 ±1 급 + 미세 거리항만. **G&B 는 충돌·실패 패널티가 지배적 크기** |
| evader 보상 | 미러 + 경계 근접 지수 패널티 | 우리: potential-based 접근항 |
| MAPPO | **팀당 actor 1 (완전 공유)**, critic = global state + **상대 행동** | 우리: 역할별 actor, critic 에 상대 행동 없음 |
| PFSP | 별도 루프, 50/50, f=(1−x)², **성과 ρ_P = 1 − t/τ (graded, 포획 시간 반영)**, snapshot 문턱 미기재 | 우리: 승패 이진 EMA. **graded 성과 신호 채택 여부 = 논의 대상** |
| 예산 | **~5e9 step/측**, 1024 env, 3.5e5 sps (RTX4090, 5.5 h) | 우리 run3 = 1.1e8 (G&B 의 ~2%). JAX 완성 시 ~6e4 sps |
| 결과 | PFSP 88.4% (vs PFSP evader) · scripted APF 상대 88.1% · ablation: noSP 과적합, 단순 SP 49.4%, 속도명령 행동 22.5% ("행동 추상화가 기동성을 깎으면 진다") | — |

## 7. 실제로 학습이 뭘 배우는가 (pilot 진단 — 이 세션의 출발점)

- **limiter 의 기울기 경로 2개**: ① arm→PN→K_FIRST +0.5 (자기 행동과 상관 高 — 선명)
  ② 위치선정→finisher net +1 (팀 공유 스칼라라 counterfactual 신호 無 — 기울기 ≈ 0).
  → 결과: **spawn 즉시 전원 무장 + PN 추격-산개** 로 수렴 (목적함수의 정답). "조형" 은 한 번도
  목적에 들어간 적 없음 (spine B-5 의 E_req 목적은 FS1 에 미구현).
- finisher: r_fire 가 11.4 → 14.5 m 드리프트 (net 유효 ≤12 m 인데) — 거리 shaping·잡음 의심.
- 군비 경쟁 동역학: 닫힌 cell 에서 공격이 전부 이기기 시작하면 방어 advantage 가 전부 음수로
  동질화 → 구조 붕괴 (it 119 창발이 소멸). **열린 cell 에서의 안정화가 핵심 과제.**
- 공격자: 종말 1회 회피 (5~10 m) 로 수렴 — net 조준 (속도 기반 예측)·PN·fallback 동시 격파.
  run1 미끼 전술도 창발한 바 있음. 판별기 기반 다양성은 전 기간 무작동.

## 8. 평가·봉인 규율 (학습 제안이 지켜야 할 틀)

양성 주장 = 결과 전 봉인된 정본 평가로만 (D ≥ +24/240, D_pool·D_ex 양쪽, seed 2/3). 전용
exploiter = 같은 예산 1e7, 정본 `--exploit`. 판정 평가 환경 = server4 고정. pooling 금지.
JAX = 학습 가속 전용 — 현재 (d) 쟁점 (JAX 학습 공격자가 체계적으로 약함, p=0.0225; 분리 실험으로
PFSP 혼합 vs 절단 batch 원인 규명 중). dense 항 심사 기준 = **episode 당 크기 예산 선언 ≤ 0.2 +
추가 손잡이 수 + 순환성** (§9-1 참조).

## 9. ★ Agenda — 논의해야 할 열린 설계 질문 (우선순위 순)

1. **arm B (r5) 보상 — 미결 논쟁 (사용자 요청으로 이 세션에 회부)**. 후보:
   (a) 현 초안 = fire-tick 단일 보너스 r += κ·v_shot_soft (κ 0.2, env 비준 판정값, 손잡이 1) —
   modest 하지만 "발사 순간" 에만 신호, limiter 까지의 credit 은 여전히 팀 공유에 의존.
   (b) dense E_req 다항 (spine B-5 원안: w₁|v_⊥|²+w₂|λ̇|²+w₃(a_req)+w₄|Δp_net(τ)|²) —
   기각-보류됨 (순환성: 조형을 구매하면 조형 발견 주장 불가 + 손잡이 6개 + r3 교훈).
   (c) 추가 보상 없음 + 진단 로그만 (순수 창발 시험).
   (d) 제 3 안 — 예: viability 의 potential-based shaping (최적정책 불변성 확보 가능?),
   G&B 식 graded 성과 (포획 시간), 기타. **각 안을 ①~④ 기준으로 심사하고 추천안 제시.**
2. **credit 할당**: 팀 공유 스칼라 유지 vs 역할 분리 보상 vs counterfactual baseline (COMA-lite).
   limiter 간접 경로에 기울기를 흘리는 최소 개입은 무엇인가. (critic 에 상대 행동 추가 —
   G&B 방식 — 도 후보.)
3. **군비 경쟁 안정화**: 방어 peak→붕괴 (run3) 의 처방 — 상대 혼합 비율, pool 크기·에이징,
   graded PFSP 성과 신호 (G&B ρ=1−t/τ), 방어:공격 iter 비, 공격 lr 상한.
4. **arm 비트 설계**: arm → PN 인계는 그 step 정책 통제를 잃는 비가역성 경로 — spawn-arming 의
   구조적 원인. armed-step 비용 (−5e-4 안은 기각-보류), arm 해제 허용, gating 등.
5. **공격자 측**: 전권 residual (2·a_max) 적정성, vestigial 스킬 z 처리 (관측에서 제거?),
   PFSP 만으로 기동 다양성이 충분한가.
6. **batch 구조**: 절단+bootstrap 이 희소 종말 보상의 credit 에 주는 영향 ((d) 분리 실험 결과
   입수 후 — JAX 세션과 조율).
7. **exploiter 예산 비대칭**: 본 학습 1.1e8 vs exploiter 1e7 — 천장 측정의 보수성 평가.

## 10. 참조 (정본)

코드: `shepherd/fs1/{world,train,bc,nets,eval}.py` · 계약: docs/123 (§5~9), **docs/124 (E3 초안,
arm A/B)**, `artifacts/fs1/*manifest*.json` · 노트: 2026-10-04d (G&B), 10-04e (run 사슬),
10-04f (pilot 판독·천장), 10-05a (현황·E-사다리) · G&B 원문: arXiv 2607.05939.
