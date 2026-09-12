# 2026-09-13 — W2 코드 정독 Q1·Q3·Q4 판정: 층1 screen 이 후보 1개(#3)로 수렴 + tau_lock race 발견

docs/91 §6 정독 질문의 code audit (실험 0, 서버 0). 추적 경로: `game/finisher_fsm.py`
전문 · `env.py` step/L232-359 · `env_sys.py` L390-449 · `sim/analytic.py` L60-131 ·
`r2a_lattice` ledger · obs 경로 grep (obs_threat/env_adv/env).

## Q1 — τ 의 구현 기제: 명시 FSM 타이머 + fire-시점 동결 predicate

- **관측→판정 지연 = 0**: fire 판정 입력 (v_shot_soft·boxed_in) 은 당 틱 참값
  상태에서 즉석 계산 (env.py L240-292). buffer·필터·측정 나이 없음. **t_obs ≡
  t_fire.** k_f 는 attacker 컨트롤러 게인이지 defender 관측 필터 아님.
- **판정→효과**: LOADED --fire--> DEPLOYING(tau_deploy) --> LOCKED(tau_lock) -->
  resolution. capture predicate 는 **fire 순간 동결** (worst-case judge:
  v_shot_worst≥1 ∧ ¬boxed_in, net_center·pose 동결 — env.py L315-320,
  CommitMeta). 판정 기하의 지평 = tau_deploy = τ₀ (viability tau) — **χ ∝ aτ²/ρ
  의 τ 는 물리적으로 실현돼 있다.** outcome 적용 = fire + tau_deploy + tau_lock.
- learned gate 의 t_obs 로깅: obs 가 당 틱 상태이므로 trivially 가능
  (CommitMeta.t_fire 이미 기록). 현행 세계에서 **τ_real ≡ tau_deploy by
  construction** (관측 지연 0).
- **F1 (주석-코드 불일치, 행동 무관)**: env.py L305-308 주석은 "frozen at the
  DEPLOYING->LOCKED transition" 이라 하나 코드는 fire_event 에서 동결.
  rollout_gif 의 "FROZEN at fire (S5)" 가 정본 의미 — 주석만 낡음. sealed world
  무변경 원칙상 수정은 B0 v3 시점 hygiene 커밋으로.
- **F2 (tau_lock race — 신규 발견)**: capture 는 fire 에서 동결되지만 적용은
  tau_deploy+tau_lock 뒤 resolution 틱. 그 사이 **penetrated 는 매 틱 체크**
  (L354) 되므로 _pending_capture=True 라도 침투가 선점하면 라벨 = PENETRATED.
  tau_lock (= 0.10·s, ledger 에서 tau 와 co-scale, tau_lock/τ₀ = 1/3 pinned) 은
  "포획 능력 수명"이 아니라 **outcome-application 지연 + 침투 race 창**.
  → B0 v3 §5-12 event-precedence 계열에 명문화 필요.

### #3 (latency-scale collapse) 관문 판정 = **진입 가능**

시뮬레이터에 움직일 수 있는 실제 delay mechanism 이 존재한다 — tau_deploy 는
FSM 타이머 + viability 지평 + finisher 조준 lead 로 물리 실현돼 있어, k배 교란
+ (a→a/k², v→v/k) 보정은 진짜 물리 변화다 (라벨 변경 아님). **screen 설계 규칙
2건**: ① tau_lock 은 ledger 무차원군 (tau_lock/tau) 대로 **co-scale 유지** —
아니면 F2 race 창이 좌표 밖에서 따로 움직여 confound. ② 관측 지연 성분은
존재하지 않으므로 이 probe 가 움직이는 것은 effect-latency (deploy 사슬) 뿐 —
"sensing 성분 분해"는 주장 불가.

## Q3 — NET_SPENT 실재 / W_net 은 물리적으로 공허 → ω_net 후보 제외

- **NET_SPENT 이벤트 = 실재·직접 판독 가능**: FSM SPENT (deterministic 상태
  전이) + env_sys.net_spent/net_spent_step (miss_terminates=False 세계에서
  spent-fail 종료 억제 + handoff 전이 스텝 기록, L399-416). 예측 판정기 신규
  제작 불요. **docs/89 위험표 2번 해소.** NET_PENDING ↔ DEPLOYING+LOCKED 자연
  매핑 — B0 v3 §5-1/4 충족 경로 확인.
- 그러나 **W_net (capture-capable lifetime) 은 현행 물리에 존재하지 않는다**:
  포획은 fire 동결 단일 predicate 라 "t_eff 이후 포획 가능 상태가 유지되는
  시간"이란 것이 없다. t_eff→t_spent 간격은 tau_lock 상수이지만 그 동안 포획
  능력이 지속되는 게 아니라 outcome 적용 대기 + race 만 있다 (F2).
- **ω_net 판별 = docs/91 이분법의 제3 결과**: W_net 은 외생·상수 (강등 사유인
  상태 의존이 아님) 이지만 **인과 채널이 없어 vacuous** — governing 후보로
  무의미. **층1 screen 제외.** net persistence 물리를 hybrid 에서 새로 구현하지
  않는 한 죽은 후보 (구현하면 그때 B0 v4 재료). tau_lock 의 race 효과는 ω_net
  이 아니라 τ-사슬 잔여로 #3 에서 co-scale 로 흡수.

## Q4 — 센서 잡음·latency: 미배선 → #2a/#2b screen 제외

- defender 관측 (_obs_vector)·fire 판정 입력 모두 당 틱 참값. noise/sigma/
  latency 주입 코드 없음 (obs_threat·env_adv·env 전수 grep). σ̃_p·q_sense 는
  screen 후보가 아니라 **구현 결정** — docs/92 #2a/2b 의 조건문 그대로 발동.
  → B0 v3 에 "이번 학기 관측 = noiseless·zero-latency contract" 명문화 + 층3
  robustness (W10+) 로 이월.
- 참고: 유일한 지연 채널 = attacker 쪽 A3-privileged v_shot_soft 1-step leak
  (env_adv L142, sealed A2 계약 일부) — defender t_obs 정의와 무관.

## #4 (actuator lag) — 노브 부재 → screen 제외

AnalyticBackend.step: 명령 가속 즉시 적용 (a_max clamp + v_max clip + heading
slew 만, L109-131). 1차 lag 부재 → perturb 할 물리가 없다. 층3 이월 (구현 시).

## 층1 목록 순효과 (docs/92 §2 지위 확정)

| # | 후보 | 판정 |
|---|---|---|
| 1 | ω_net | **제외** — vacuous (인과 채널 부재) |
| 2a/2b | noise/latency | **제외** — 미배선 (구현 결정, 층3 이월) |
| 3 | latency-scale collapse | **진입** — 유일한 실행 후보 (tau_lock co-scale 규칙) |
| 4 | actuator lag | **제외** — 노브 부재 |
| 5~8 | (원래 confirmatory 전용/낮음/불요) | 불변 |

**⇒ W2 cheap screen = #3 단일 후보**: tau_deploy k배 {예: 2/3, 3/2} ×
(a→a/k², v→v/k, tau_lock co-scale) × 6 strata (η 3 × λ 2) × 경계 밴드
micro-grid (step ≤ 0.02). §3 봉인 진입 규칙 (A/B) 그대로 적용. 예상 비용:
R2a micro-grid 급 (서버 하룻밤 이하) — screen 실행 설계는 별도 문서로 (W2).

## B0 v3 로 넘어가는 것

§5-4 (NET_SPENT = FSM/env_sys 상태 전이 직접 소비 — 확인됨) · §5-12 에 F2
race 명문화 (capture-적용 vs 침투 선점 순서) · 관측 contract (noiseless·
zero-latency) 명시 · F1 주석 수정은 hygiene 커밋으로.
