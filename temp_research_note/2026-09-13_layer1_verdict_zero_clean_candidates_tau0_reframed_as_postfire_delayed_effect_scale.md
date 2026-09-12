# 2026-09-13 — 층1 최종 판정: clean executable candidate 0 (#3 HOLD — q_dec confound blocker) + τ₀ 개념 재정의 (post-fire delayed-effect scale, q_race 도입)

같은 날 code audit 노트 (커밋 bd77fac) 의 "#3 진입 가능" 판정을 **사용자 검토가
뒤집음** — 소급 수정 대신 본 노트가 supersede 한다. 서버 screen 실행 HOLD 확정.

## 1. #3 blocker: q_dec confound (분리 불가)

τ₀→kτ₀ 에 dt(=Δt_dec)=0.05 고정이면 q_dec 가 함께 움직인다:
k=2/3 → q_dec=1/4 · nominal 1/6 · k=3/2 → 1/9. 그런데 q_dec 1/6→1/12 에서
χ50 ~+0.15 민감이 **이미 실측**돼 있다 (temporal-resolution conditioning,
causal source unresolved). 따라서 #3 에서 Δχ50 이 나와도 "collapse 붕괴" vs
"conditioning 변화"를 분리할 수 없다 — **blocker**. 깨끗한 #3 의 조건 =
(τ₀, Δt_dec, τ_deploy, τ_lock) 동시 k배 + (a→a/k², v→v/k) 의 완전 similarity
transform 인데, 현행 dt_phys=Δt_dec coupling 때문에 Δt_dec co-scale 이 수치
해상도까지 움직인다 → **현 아키텍처에서 원천적으로 불가**.

## 2. 층1 최종 판정 (2026-09-13)

> **Layer-1 screen: no clean executable candidate after code audit.**

#1 ω_net vacuous · #2a/2b 미배선 (구현 결정) · #4 노브 부재 · q_dec known
pinned (재스크리닝 금지) · **#3 conceptually valid but currently confounded by
q_dec–dt coupling; defer unless a q_dec-preserving implementation is
available**. 억지로 하나 남겨 돌리는 것보다 0 으로 닫는 것이 과학적 —
층1 의 목적은 실행이 아니라 숨은 축 탐지였고, 탐지 결과가 "현 아키텍처에서
분리 가능한 잔여 축 없음"이다. **층1 screen 생략 권고** (최종 비준 = B0 v3
봉인 시).

## 3. F2 의 승격: τ₀ 는 두 채널을 가진다

- **Channel A (viability horizon)**: fire 순간 worst-case judge 가 τ₀ 지평의
  회피 가능성을 동결.
- **Channel B (outcome race)**: 동결된 capture 가 τ_deploy+τ_lock 뒤 적용될
  때까지 침투가 선점 가능.
- **same-tick precedence 판정 (code-verified 2026-09-13)**: pending 창
  (resolution 이전 틱) 에서는 침투가 자명하게 이김 (captured 구조적 False) —
  race 의 실체. **resolution 틱 동시 발생은 CAPTURE 우선** (run_episode
  L361-369 라벨 사슬 hard_kill→captured→penetrated; probe _Driver 동일 순서).
  env_sys 의 "침투 우선" 조항은 sham-net (capture_terminates=False) 전용 —
  본 세계 무관. → **B0 v3 §5-12 에 ④ 로 명문화** (현행 유지/변경은 봉인 시
  판정; outcome label 을 바꿀 수 있어 blocker 급 사전 결정 사항).
- Q1 표현 정정 (감사 하향): "χ 의 τ 는 물리적으로 실현돼 있다" → **"τ₀ is
  implemented through both the fire-time viability horizon and the delayed
  outcome-resolution timer"** (reduced-order — net ballistic 적분 아님).

## 4. 시간 구조 개념 정리 (docs/91 v2.1 로 반영)

- **τ₀ 재정의**: "generic system latency" 가 아니라 **post-fire characteristic
  delayed-effect scale** (관측→판단 지연은 구현상 0 — t_obs ≡ t_fire).
- **q_dec 는 실패가 아니라 독립 무차원군의 발견**: 시간척도가 (τ₀, Δt_dec)
  둘이면 Buckingham-Π 상 Δt_dec/τ₀ 가 남는 게 당연 — τ₀ 하나로 시간 구조가
  collapse 하지 않았다는 사실이 드러난 것.
- **q_race = τ_lock/τ₀ = 1/3 (ledger contract-fixed ratio)** — 새 좌표가
  아니라 고정 conditioning. (q_deploy = τ_deploy/τ₀ = 1 은 정의상 고정.)
- **정본 claim 형식**: "For the sealed reduced-order world at fixed
  q_dec = 1/6 and fixed timer ratios (q_race), the net-capture boundary is
  characterized in (χ, η, λ)." — 전 latency-scale collapse 의 강한 주장은
  후속 (q_dec·q_race 독립 sweep, decoupled 아키텍처) 으로 이연.
- **τ₀→0 은 singular limit**: 관측 지연이 이미 0 이므로 τ₀→0 은 "발사 즉시
  효과 적용 → viability horizon·race·post-fire 회피 전부 소멸"의
  **instantaneous-effector idealization**. q_dec→∞ (dt 고정 시). smooth
  extrapolation 대상 아님 — baseline 참조점으로만.

## 5. B0 v3 입력 (확정 목록 — 초안 작업의 재료)

1. NET_SPENT = FSM/env_sys 상태 전이 직접 소비 (§5-4, 확인됨).
2. §5-12 ④: capture-resolution ∧ penetration same-tick = N 우선 (현행) —
   유지/변경 봉인 판정 + pending-창 race 는 세계 사실로 명기.
3. 관측 contract: noiseless · zero-latency (t_obs ≡ t_fire) 명문화.
4. 시간 conditioning 봉인: q_dec = 1/6 pinned + q_race = 1/3 contract-fixed
   + claim 형식 (위 §4) + τ₀→0 singular 주의.
5. τ₀ 정의문 교체: post-fire delayed-effect scale (two mechanisms).
6. 층1 결과 조항: "no clean executable candidate — screen 생략, stratification
   추가 변수 없음" (§5-10).
7. hygiene (봉인 시점): env.py L305 주석 수정 (F1).

## 6. 이번 정독의 순가치 (한 줄)

> screen 하나를 만든 게 아니라 confounded screen 을 제거했고, τ₀ 가 단순
> latency scalar 가 아니라 **viability horizon + event-race scale** 임을
> 밝혔다 — 6DOF/실기 transportability (docs/93) 에서 더 중요해질 사실.
