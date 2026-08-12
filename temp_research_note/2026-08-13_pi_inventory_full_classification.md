# 2026-08-13 — Π (무차원수) 전수 분류: 등록 12군 + 미등록군 3건 + 동결 생성기군

"conditioning 7군" 은 `lattice_spec.CONDITIONING_ORDER` 로, **등록 Π 의 부분집합**이다.
이 노트가 전체 분류의 정본 reference.

## A. 등록 Π = 12군 (`lattice_spec.PI_GROUPS`, 결과 전 확정·추가 금지)

| # | Π | 정의 | 역할 | 게이트 10 부류 |
|---|---|---|---|---|
| 1 | **chi** | a_att·τ²/(2ρ) | core 축 | — (축) |
| 2 | **kappa** | r_kill/ρ | core 축 | — (축) |
| 3 | **mu** | a_lim,max/a_att,max | core 축 | — (축) |
| 4 | eta | att_speed·τ/ρ | conditioning | **Z** (상태 ‖v‖) |
| 5 | nu | limiter_v_max/att_speed | conditioning | **P** (L1/LN reachability) |
| 6 | lam | cone_range_max/ρ | conditioning | **P** (judge) |
| 7 | alpha | cone 반각 [rad] | conditioning | **P** (judge) |
| 8 | sig_sb | R_standby/ρ | conditioning | **Z** (limiter 위치) |
| 9 | sig_dt | sense_range/ρ | conditioning | **G** (생성기 전용 → 게이트 11) |
| 10 | sig_as | D_asset/ρ (→ R_NK) | conditioning | **P** (admissibility) |
| 11 | N | limiter 수 (이산) | core 동반 | — (이산 축) |
| 12 | dt_tau | dt/τ | 수치 검증수 (설계변수 아님) | — |

= core 3 + conditioning 7 + 이산 1 + 수치 1.

## B. 차원 파라미터 전수 (Buckingham 계산 근거)

**길이 [L]** (22): ρ · r_kill · cone.range_max · range_min · spawn(r_range lo/hi, dx,
**r_lat**) · standby R · sense_range · sprint_range · slowdown_range(2) ·
jink_terminal_r · bait_range(2) · R_NK · layout(target, ring_center, ring_radius,
adversary_start_x, finisher_p0, target_radius, r_ring, x_fire)
**시간 [T]** (2): τ_deploy · dt
**시간⁻¹ [1/T]** (7): jink_freq · homing_gain · **fwd_gain(4.0, 하드코딩)** ·
attitude.omega_max · limiter_omega · adversary_omega · omega_att_max(dead)
**속도 [L/T]** (3): att_speed · limiter_v_max · adversary_v_max
**가속 [L/T²]** (2): a_att_max · a_lim_max

**표현 정정 (2026-08-13, Tier 2 이후)**: raw dimensional inventory 는 36개이고
차원행렬만 기준으로 하면 **최대 약 34개의 Π-coordinate 후보**가 생기지만,
**구조적·대수적 의존성을 제거하면 실제 독립군 수는 더 작다**. "34개의 독립
무차원군이 존재한다" 는 과한 표현이다 — 실증 사례: `ρ = R_max·tan(α)` (Tier 2 가
적발), dead parameter (omega_att_max), 고정 controller 비, 파생량.
등록 12군은 그 중 **지도 위에서 변화시키기로 선언한 것**이고, 나머지는 nominal
동결 (= scope 한정)이거나 certificate 입력이 아니다.

## C. Certificate C(z;θ) 만 보면 등록 목록이 거의 완비

C 에 실제로 들어가는 차원량: τ · a_att · a_lim · ‖v‖ · v_lim · range_max ·
range_min · kill_radius · R_NK · ρ · 상태 길이(‖p−apex‖, limiter 위치) ·
T_reach(하한 reachability 지평선) = 12개 → **10 독립군**.
등록 대응: chi · kappa · mu · eta · nu · lam · alpha · sig_sb · sig_as · **T_reach/τ**.
즉 마지막 하나를 빼면 정확히 일치한다.

## D. 미등록 군 3건 (게이트 10 이 실제로 적발한 것)

| 군 | 정의 | 어디 | 지위 |
|---|---|---|---|
| **k_f·τ** | fwd_gain·τ_deploy = 4.0 s⁻¹ × τ | attacker_ladder.py:377 하드코딩 | **T1-T.system FAIL 의 원인.** 생성기측. 게이트 11 에서 explicit param 승격 후 재검증 |
| **r_lat/ρ** | SpawnSpec.r_lat(5.0 m)/ρ | spawn 횡원판 반경 | T1-L 스모크가 적발 → 스케일 대상 추가로 해소. 생성기측 |
| **T_reach/τ** | (t·dt)/τ | coarse_pilot `_assignable` 의 하한 reachability 지평선 | **certificate 측 미등록**. 상수 아님(에피소드 내 변함) ⇒ 파라미터가 아니라 **정규화 상태 좌표 목록에서 빠진 항목**. 상사변환에는 정합(양 변환에서 T/τ 불변 확인) 이나, "지도는 (chi,kappa,mu,N)의 함수" 주장에는 별도 caveat 필요 |

## E. 동결 무차원군 (등록도 시험도 안 된 것 — scope 한정으로 명시해야)

**생성기 행동비**: jink_amp 0.6 · **jink_freq·τ** · **homing_gain·τ** · route_gain
U[0.2,0.8] · lam_gain 1.0 · lam_range 1.0 · repel_margin 1.0 · sprint_frac ·
slowdown_frac · bait_gain/threshold/enclosure_r · psi · speed_frac · azimuth π/4
**판정·수치**: θ=0.9 · witness (n=2000, n_segments=4, n_dir=32, n_t=24) · eps 1e-6 ·
episode_len(스텝수)
**기하비**: ring_radius/ρ · x_fire/ρ · adversary_start_x/ρ · target_radius/ρ 등
layout 파생비 — spawn/standby 는 등록됐지만 **layout 기하비는 미등록·동결**.

## F. 결론 (표현 규율)

- "7군" 은 conditioning 부분집합. 등록 Π = **12** (단 alpha/lam 중복 발견 ⇒ 실질
  자유도는 더 적다 — scale ρ_eff + shape).
- 후보 상한 ~34, **실제 독립군 수는 그보다 작다** (구조 의존성 제거 후).
- **지도 주장 (Tier 2 r3 반영 정본, r4 전까지)**: core 좌표가 primary 축이지만
  **core-only 충분성은 미해결**. 확인된 것 = σ_as 는 U_cheap 의 governing 좌표 ·
  nu/sig_sb 는 이 regime 에서 inactive·non-identifiable · cone 매개변수화는 중복
  (scale–shape 분리 필요). 미등록 Π 는 전부 nominal 동결.
- 미등록 3건은 숨기지 않고 명시: k_f·τ (게이트 11 대상) · r_lat/ρ (해소) ·
  **T_reach/τ** — 상사성 위반은 아니나 (β 변환에서 비 유지), L1/LN 의 **effective
  state coordinate** 라 "동일 chi 에서 L_N 이 하나의 map surface 를 이룬다" 류
  진술에 caveat 필요. 정규화 상태좌표 목록에 `T̃_reach = T_reach/τ` 로 명시하고,
  축 sweep 은 별도 사전등록 (r4 범위 밖).
