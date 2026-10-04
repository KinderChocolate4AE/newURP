# 2026-10-04d — Gavin & Bronz 레시피 정리: PFSP 동시학습은 근거 있음, 단 우리 학습 예산은 그들의 ~1/40,000 (env 26 step/s)

출처: T. Gavin & M. Bronz, "Intercepting an Agile Target with Net-Carrying Drones
using Competitive Multi-Agent Reinforcement Learning", 2026, arXiv 2607.05939
(HTML 판 직접 읽음, 2026-10-04). "미기재"는 본문에 값이 없다는 뜻.

## 1. 레시피

| 항목 | 내용 |
|---|---|
| 시뮬 | 6DOF quadrotor, **CTBR** (collective thrust + body rates) 행동, JAX jit + 병렬, 충돌 (기체·arena·net) 포함. dt 미기재 |
| 교전 | 3 pursuer (기체 하부 rigid net) vs 1 evader. arena 32×32×16 m, evader 는 12×12×6 m 안. 초기 위치 arena 내 균등 무작위. episode 10 s |
| 관측 | body-frame 속도 + 회전행렬 9 + 타 agent 상대 위치·속도 (body frame) + 고도·경계 ray 거리. evader 도 같은 구조 |
| 행동 | 양측 동일 CTBR, Gaussian + tanh squash |
| 보상 (pursuer) | r_catch − r_step − r_coll(P,E) − r_coll(P,P) − r_fail − r_cmd − r_dist; λ_catch 10, λ_step 0.04, λ_collPE 0.1, λ_collPP 10, λ_dist 0.001, λ_fail 30, λ_cmd 2e-4. 사실상 이벤트 보상 + 미세 거리 shaping |
| 보상 (evader) | −r_catch + r_step − r_coll − r_fail − r_cmd − r_bnd (경계 근접 지수 패널티) |
| MAPPO | CTDE, **팀당 actor 1개 (같은 팀 parameter sharing)**, critic 은 global state + 상대 행동. 256×2 ReLU MLP. lr·γ·λ·clip·batch·epoch·entropy **미기재** |
| PFSP | 양 팀이 **별도 루프**에서 학습하며 각자 과거 frozen 정책 pool 을 키운다. episode 마다 상대 1개를 frozen 으로 고정. **50% 최신 상대 / 50% PFSP 분포**. 성능 ρ_P = 1 − t/τ (포획), 0 (pursuer 추락 또는 회피 성공), 1 (evader 추락); ρ_E = 1 − ρ_P. 우선순위 **f(x) = (1 − x)²** (어려운 상대 집중). snapshot = 현재 정책이 pool 전체 상대로 성능 문턱 초과 시 (문턱값 미기재). pool 최대 크기 미기재. scripted warm-start 언급 없음 |
| 예산 | **~5×10⁹ env step / 측 (총 ~10¹⁰)**, 1024 병렬 env, **~3.5×10⁵ step/s**, RTX 4090 1장, **5.5 h** |

## 2. 결과

- PFSP-CTBR pursuer: 포획률 **88.4%** (vs PFSP evader), **88.1%** (vs scripted APF evader),
  평균 포획시간 3.71 s, pursuer 추락 7.7%. PFSP evader 의 회피율 3.4%.
- 기준선 (vs APF evader): FRPN 55.0%, APF 46.8%, FRPN+APF 71.9%.
- ablation:
  - **noSP** (고정 상대): "결정론적 훈련 상대에 과적합" (수치는 Table II, 재확인 필요).
  - **SP** (우선순위 없는 self-play): vs PFSP evader **49.4%**.
  - **PFSP-vel** (속도 명령 행동): vs PFSP evader **22.5%** → "속도 제어는 기동성을
    제약, CTBR 이 더 안전하고 강건".
- 창발 행동: 첫 시도는 한 대가 빠르게, 두 대는 느리게 접근해 실패 시 2차 시도 /
  포위 / 경계로 몰기 / 실패 후 빠른 회복. 실기 전이 없음 (향후 과제).

## 3. 우리 질문에 대한 함의

1. **"scripted pool 은 한 전략에 과적합 → 동시학습 + PFSP 필요" (사용자 주장)** — 논문이
   직접 지지한다. noSP 과적합, SP 49.4% vs PFSP 88.4%. 그리고 PFSP 로 학습한 pursuer 가
   scripted evader 에도 88.1% 로 강하다 (강건성이 양방향).
2. **"그대로 쓰려면 6DOF 부터"** — 판단 보류 (Claude 의견): CTBR ablation 이 보인 것은
   "6DOF 가 필요하다" 가 아니라 **"행동 추상화가 상대 대비 기동성을 깎으면 진다"** 다
   (같은 6DOF 안에서 속도 명령 vs CTBR 비교). 우리 PM 가속 행동은 제어기 지연이
   없는 가속 수준 명령이고 양측이 같은 추상화를 쓴다. 6DOF 는 PFSP 도입의 전제가
   아니라 fidelity 층 (2026-09-07 결정: 6DOF gate → airframe-consistent 3DOF+ frozen-
   policy plant-swap) 으로 보는 편이 일관된다. 최종 결정은 사용자.
3. **★ 예산 격차가 가장 큰 발견**:
   - P2 limiter 학습 = **131,072 env step / seed**. G&B = ~5×10⁹ / 측 → **~40,000배**.
   - 우리 env 실측 (2026-10-04, 단일 프로세스 scripted rollout): **26 step/s**
     (k=1·k=4 동일). G&B 의 ~1/13,000. 64 프로세스 병렬로도 ~1.7×10³ step/s →
     5×10⁹ step 은 ~35 일, 10⁸ step 도 ~16 시간.
   - 따라서 b5·P2·RL1/RL2 의 학습 null 은 **방법 문제가 아니라 예산 부족일 가능성**을
     배제할 수 없다 (판정은 번복하지 않음 — 해석의 대안 가설로 기록).
   - self-play 는 단일측 학습보다 표본을 더 먹는다. **env 처리량이 PFSP 의 선결 조건.**
4. 참고 자산: `shepherd/scale_v2.py` (docs/59) 에 이미 장거리 overlay 존재 —
   start_x 300 m, episode_len 800, **ring_center 50 m (전진 배치)**. k=4 대신 후보.

## 4. 다음

1. env step 프로파일 (26 step/s 의 병목) → 배치화/JAX 재작성 범위 결정. 목표 ≥10⁵ step/s.
2. 공격자 RL agent 화 (행동 = 방어자와 같은 PM 가속) + PFSP 루프 (논문 설정 그대로:
   별도 루프, episode 별 frozen 상대, 50/50, f=(1−x)², pool snapshot).
3. 방어자: 팀당 parameter sharing 은 이종 역할 (limiter vs finisher) 이라 역할별 actor
   (현 mappo.py 구조) 유지.
