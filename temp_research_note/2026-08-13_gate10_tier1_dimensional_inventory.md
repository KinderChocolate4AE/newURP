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

미해결 확인 항목 (구현 중 코드로 확정): 센서 노이즈/계측 지연의 절대 단위 여부 ·
lite_sim 적분기의 dt 스케일 정합 · judge 내부의 절대 eps 상수 유무.
