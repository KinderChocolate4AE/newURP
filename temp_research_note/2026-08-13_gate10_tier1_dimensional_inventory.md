# 2026-08-13 — 게이트 10 Tier 1 착수: 차원 knob 전수 인벤토리 (1차 정적 스캔) + 구현 계획

계약 = `docs/78` (선봉인, 2026-08-11). Tier 1 = 완전 상사 T1-L (길이×2)·T1-T (시간×2)
에서 상태별 |Δv_shot| ≤ 1e-6. 전제 = CRN 무차원화: **절대 단위로 뽑히거나 고정된
자유도가 하나라도 스케일에서 누락되면 그게 숨은 차원 상수** — 이 인벤토리가 T1
transform 이 스케일해야 할 전체 목록이다. (정적 스캔 1차 — 누락은 T1 실패로
드러나도록 설계돼 있으므로, 실패 시 이 표를 갱신하며 수정한다. 버그 수정은
docs/74 §7 위반 아님 — docs/78 §1 명시.)

## 길이 [m] — T1-L 에서 ×2

| knob | 값 | 위치 |
|---|---|---|
| physics.net_radius (ρ) | 1.77 | m4_config M4_OVERRIDES |
| physics.kill_radius | 0.75 (pilot 은 κ·ρ pin) | m4_config / coarse_pilot |
| viability.cone.range_max | 8.22 (ρ 연동 정의) | m4_config |
| spawn r_range | (250, 350) | scale_v2 THREAT_V3_SPAWN |
| standby R | (8, 16) | V3_STANDBY_R |
| attacker sense_range | (15, 45) | V3_SENSE_COMMON |
| sprint_range | (40, 80) | V3_SPRINT_RANGE |
| slowdown_width | (20, 40) | V3_SLOWDOWN_WIDTH |
| jink_terminal_r | 3.0 | AttackerSpec 기본값 |
| R_NK | 6.0 | coarse_pilot/adapter 상수 |
| asset/target·spawn dx 등 위치 | scenario | build_m4_env/lay |
| 센서 노이즈 σ (존재 시) | 확인 필요 | env 계측 경로 |

## 시간 [s] — T1-T 에서 ×2 (파생: 주파수는 ÷2)

| knob | 값 | 주의 |
|---|---|---|
| physics.tau_deploy | 0.30 | |
| physics.dt | m4_config | episode_len 은 스텝 수 (무차원) — dt×2 면 실시간 지평선 ×2 로 정합 |
| **jink_freq** | **1.5 Hz** | **시간⁻¹ 차원 — T1-T 에서 0.75 로 스케일 필수. 놓치기 가장 쉬운 항** |

## 속도·가속 — T1-L: v×2, a×2 / T1-T: v÷2, a÷4

| knob | 값 |
|---|---|
| physics.att_speed bracket | (8, 30) + pilot pin 19.0 |
| physics.a_att_max bracket | (11, 78) + pilot 은 chi 로 pin |
| 파생 ratio (a_lim/a_att=0.35, limiter_v/att_speed=1.0, adversary 1.5) | 무차원 ✓ 자동 |

## 무차원 (불변 확인만)

θ=0.9 · μ·ν·κ·χ (pin 식이 스케일된 절대값으로 재계산되는지 확인) · azimuth π/4 ·
jink_amp 0.6 (×a_lat ratio) · route_gain U[0.2,0.8] · witness 수 n=2000/n_segments/
n_dir/n_t · SHA 기반 u draw (무차원 [0,1) → lerp — **lerp 대역이 스케일되면 CRN 자동
충족**, 대역 누락이 곧 위반).

## 판정 세부 (docs/78 §1 승계 + 구현 결정 2건)

1. 상태 pairing = (ep, t) — 상사변환이 정확하면 궤적이 1:1 대응 (적분기
   scale-equivariance 는 T1 자체가 검증).
2. predicate boundary 규칙: |m| ≤ 1e-6 m 은 **기준계 단위** 기준 — T1-L 에서 교란계
   margin 은 ÷2 해서 비교 (무차원화해 비교, docs/78 의 "무차원 절대" 문구 준수).

## 구현 계획 (`shepherd/scripts/gate10_isopi.py`)

1. `T1_L(cfg, spec)` / `T1_T(cfg, spec)` — 위 표의 전 knob 을 스케일한 (extra_cfg,
   AttackerSpec) 쌍 생성. coarse_pilot `_cell_world` 경로 재사용 + override 주입.
2. 기준계·변환계를 **같은 seed/episode** 로 rollout → (ep,t) pairing → 상태별
   v_shot (hold V0) + predicate (caught/blocked/boxed) 비교.
3. 산출물: per-state Δ 분포 + max|Δ| + boundary-외 predicate 불일치 수 (0 필수)
   → `results/phase3/gate10_tier1.json` (스탬프 + docs/78 해시).
4. Tier 1 PASS 후 Tier 2 (7 group × 3 chi × 20 ep, CRN paired — 서버 샤딩).

## (같은 날 2차 — dimensional audit 완료. 이 표를 구현 입력표로 동결)

**변환 공식 (코드 주석 첫머리에 명시)**: 길이 α, 시간 β ⇒ x'=αx, t'=βt,
v'=(α/β)v, a'=(α/β²)a, f'=f/β, ω'=ω/β. T1-L = (α,β)=(2,1) · T1-T = (1,2).

1. **dt — 확정**: physics.dt = 0.05 s (m4_config). T1-T 에서 **dt'=β·dt**, step
   count (episode_len 160/1100 등) 는 무차원이라 불변 → 물리 지평선이 β배로 정합.
   τ/dt = 6 (τ 가 dt 격자 위) 은 두 변환 모두에서 보존 ✓. **pairing 의 t = step
   index** (coarse_pilot 루프 인덱스 — artifact 에 step_idx 로 명시). attacker
   내부 dt 사용 1건 (`a_cmd * dt`) 은 cfg dt 를 받아 자동 스케일 ✓.
2. **noise — 본 파이프라인에 가산 센서 노이즈 없음** (env 계측 경로 deterministic;
   grep 결과 noise 언급은 CRN 주석뿐). 난수는 전부 SHA-u latent × 대역 lerp
   (시나리오) + seeded witness 표본 (∝ a_max) — **대역 endpoint 를 스케일하면 CRN
   자동 충족**. rejection/clip 형 draw 없음 확인. 원칙 명문화: "same seed" 가
   아니라 **same latent (ep, draw-index)** — pairing mismatch 시 첫 용의자.
3. **judge eps — 전부 numerical guard 로 분류 (스케일 금지)**: viability `_EPS =
   1e-12` 의 전 용례 = 정규화 분모 가드·zero-벡터 판정·containment tie-break.
   물리 tolerance 아님. 1e-6 판정 bar 대비 6자릿수 아래라 스케일 불변으로 둬도
   T1 에 영향 없음. "차원량 + dimensionless-looking 상수" 형 위험 패턴은 발견 0
   (sphere_containment 의 `net_radius + _EPS` 1건도 1e-12 급 tie-break — guard 분류).
4. **각속도 [1/T] — 인벤토리 추가 (audit 의 최대 수확)**: attitude.omega_max = 2.0
   rad/s (net 지향 slew) · train.limits.limiter_omega = 2.5 · adversary_omega ·
   AttackerSpec omega_att_max (params registry 상 dead-param 표기 — witness
   turn-curve 에 attacker_turn_limited 로 들어가는지 구현 시 1줄 확인). T1-T 에서
   전부 ÷β. jink_freq 와 함께 시간축 변환의 최다 실패 후보군.
5. **route_gain 등 무차원 gain 은 불변** (a_lat_max 만 스케일 — gain×a_lat 구조 확인).
6. **디버깅 진단 저장 의무**: PASS 기준은 봉인된 |Δv_shot|≤1e-6 그대로 두고,
   보조로 normalized state (p/ρ, v·τ/ρ, a·τ²/ρ) · witness count · G/B ·
   normalized margin (m/ρ) 을 저장 — 실패 시 state-generation vs judge 를 즉시
   분리. boundary predicate 비교는 무차원 margin 으로.

**실패 처리 순서 (선언)**: Δv_shot 실패 → normalized state 비교 → witness 비교 →
judge 비교 순으로 localization. T1 실패 자체는 나쁜 결과 아님 (숨은 차원 상수
폭로가 존재 이유) — 단 위 1–4 는 이미 알고 닫은 상태로 구현에 진입한다.
