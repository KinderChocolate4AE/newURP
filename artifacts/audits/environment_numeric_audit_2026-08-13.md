# 환경·시뮬레이터 수치 전수감사 (Environment Numeric Audit)

- **일자**: 2026-08-13 · branch `feat/scale-up-v2` · read-only (코드 수정 0건)
- **방법**: 5-트랙 병렬 감사 — (1) env/sim, (2) attacker/defender + observability, (3) certificate/judge, (4) 캠페인별 execution-path manifest, (5) docs/claims 커버리지. 실제 import/call graph 추적 (파일명 의존 없음).
- **범위**: env_sys / scale_v2 / spawn_rand / sim / env(frozen) / m4_config / attacker_ladder / adversary / baselines / mobile_finisher / roles / finisher_fsm / obs_threat / viability / fire_gate_calibration / measure_harness / judge_crosscheck / cert_unblockable / coarse_pilot / gate7\* / gate10 / gate11 / curve_sweep / scale_v2_baseline + results/\*.json 메타 + docs/40·42·45·46·47·72·74·77·78·79·80.
- **중복 방지**: 기존 audit 4종(claim_evidence / dead_code / reward_coma / RESET_WEEKLY)이 확정한 사실(계약 분리, dead flag 목록, retracted 잔재 docs/50:183)은 재유도하지 않고 인용만.

---

## A. Executive verdict

1. **KSAS 핵심 결론을 무효화하는 hidden numeric assumption은 발견되지 않았다.** a\* = 2ρ/τ² = 39.3 m/s² 사슬(τ=0.30 문헌 분해·선언적 하한, ρ=1.77 Xu 유도·낙관 상한 caveat 명시)과 aiming boundary 구조(ψ=4.26° → 25.8 vs 실측 23.8)는 감사를 통과한다. 단 두 선언 상수(τ 하한, ρ 상한)가 **같은 방향으로** χ를 밀어 경계의 물리적 위치를 움직인다는 점은 scope 문장으로 이미 draft에 존재한다.
2. 그러나 **인쇄 숫자 중 유일하게 citable provenance가 없는 값이 하나 있다**: threat bracket 상한 **78 m/s²** (draft 자체 체크리스트 ⟦78 출처 표기 확정⟧ open). 제출 전 인용 확정 또는 "선언"으로 명시 격하가 필요하다.
3. **가장 큰 provenance 균열은 아티팩트 기록 쪽이다**: (a) T1 reactive rerun JSON(`curve_*_reactive.json`)이 캠페인을 정의하는 두 값 `route_gain=0.5` / `sense_range=30.0`을 **메타에 기록하지 않는다** — 파일명과 daily note로만 구분 가능. (b) `scale_v2_baseline` 결과군은 하나의 contract 문자열("docs/59 V4") 아래 episode_len **400→480→800 3세대**가 혼재하며 JSON만으로 구분 불가.
4. **legacy(docs/45) ↔ rerun 병치는 attacker-only 비교가 아니다**: legacy 곡선은 구 `SystemSpec()` 종료 계약, rerun은 `ratified_system()` F-flags. "변경은 공격자 반응 항만"은 ratified 재기준선 대비만 참 (curve_sweep.py:145-147 자체 인지).
5. arXiv v0 확장 전 최우선 검증 항목은 **θ=0.9 regime mismatch**다: fire gate calibration이 M2 fixture(τ=0.4, ρ=2.0, point_mass, n=800 — ratified 2000 미만)에서 수행됐고, 그 숫자가 M4/Phase III 세계의 θ_S2 라벨 컷 + Gate 7 폐쇄 기준으로 재보정 없이 4중 역할을 수행한다. 라벨 유병률(FREE/INF/AMB)의 θ-sensitivity는 미시험.
6. B2 전 반드시 정리할 game-structure 가정: **sense_range는 attacker의 3개 관측 항 중 route 항 하나만 게이트**하고(repel·commit-bit는 비게이트), **commit 감지는 거리 무관 0-tick·무노이즈**이며, **T1의 route 항은 commit 후에도 꺼지지 않는다**(T0/T1의 post-commit 회피 강도 차이 = 사다리 축 오염). 여기에 기존 RESET audit의 train/eval 배선 격차(학습과 측정이 다른 세계)가 겹친다.
7. 코드-문서 불일치 잔재: m4_env.py:195 docstring의 a\*=44.4는 ρ=2.0 시절 stale(실제 39.3, 코드는 parametric); curve_sweep.py docstring 24.06/6.6%는 구 run(현행 23.82/7.5%).
8. 숫자 다수는 **preregistered scenario 선언**(docs/59·60·61·68·74·79)으로 잘 방어되어 있다 — "숫자가 많으니 임의적"이라는 판정은 성립하지 않는다. 문제는 소수의 미등록 literal(jink_freq 1.5 Hz, jink_amp 0.6, r_nk 6.0, c_lim 0.1)과 기록·복제 규율이다.

### 최종 판정 (3건 분리)

| 대상 | 판정 | 근거 요약 |
|---|---|---|
| **KSAS 2-page (feasibility/aiming boundary)** | **PASS WITH SCOPE CAVEATS** | 구조 무효화 발견 없음. 조건: §G의 5개 액션 (78 출처 / rerun 메타 / legacy-계약 caveat / pooled n 재확인 / stale docstring). 모두 서지·기록 수준, 실험 재설계 불요 |
| **arXiv v0 확장 계획** | **REQUIRES FIX BEFORE SUBMISSION** | θ=0.9 재보정 또는 라벨 θ-sensitivity 필수; jink_amp/jink_freq 등록+sensitivity 또는 nominal-fixed scope 공식화; ρ–R_max–θ_half 항등식 코드 강제; χ grid 상단 78.67 > bracket 78 정합; κ grid 확장(기지) |
| **B2/T_lead 설계** | **REQUIRES FIX BEFORE B2** | 설계 문서(docs/80)는 sense_range를 명시 변수로 봉인 — 그 부분은 통과. 그러나 commit-bit 전역 0-latency 채널, route 항 post-commit 비게이트, policy가 route_gain/sense_range 미관측(reward audit §7), train_m4/mission_eval 배선 격차(RESET audit)가 미해결 |

---

## B. Complete active-parameter table

행 형식: `ID | symbol | value | unit | category | file:line | active path | provenance | derived-from | in-params.py | status`. 전체 열거는 트랙별 원본 표를 통합. (provenance: ①문헌 ②장치설계 ③시나리오선언 ④튜닝/내부측정 ⑤편의 ⑥파생 / UNKNOWN)

### B.1 env_sys.py — ModeSystemEnv (모든 M4/v2/v3 게이트의 외피)

| ID | symbol | value | 비고 |
|---|---|---|---|
| ES01 | PARK_POSITION | (0,0,60) m | ⑥ 주석 내 2-부등식 유도. ARBITRARY-BUT-SCOPED |
| ES02 | tau_kill | 0.15 s | ① Pliska LiDAR 0.10 + decide 0.05. sweep {0.15,0.20}. JUSTIFIED |
| ES03 | p_kill | 1.0 | ③ Bernoulli 상한점, sweep 축 선언. DOCUMENTED |
| **ES04** | **r_nk** | **6.0 m** | **UNKNOWN 근거(파일 내 무근거, StandbySpec 인용은 순환). veto/kill 판정 직결. HIDDEN + CLAIM-CRITICAL** |
| ES05 | commit_threshold | 0.5 | ⑤ env fire 임계 0.5 미러. REDUNDANT |
| ES06 | r_commit/r_contact | None→kill_radius(0.75) | ⑥ 3-반경 1값 공유, 보정 명시 유보. SCOPED |
| ES07 | ratified_system flags | resolver=T, miss_term=F | ③ docs/53-54. scale_v2_baseline.py:26이 동일 계약 수기 중복 (drift 위험) |
| ES08–14 | RewardSpec | b_net 1.0 / w_kill 0.5 / c_pen·c_trunc 1.0 / **c_lim 0.1** / dense·terminal_scale 1.0 | w_kill sweep 축 선언. **c_lim=0.1 무근거 (hard-kill↔net 트레이드오프 가격). HIDDEN** |
| ES15–18 | n_kill=⌈τ_kill/dt⌉=3 / commit margin 식 / SHA256 Bernoulli / _EPS 1e-12 | — | ⑥/⑤ JUSTIFIED |

### B.2 scale_v2.py — v2/v3 계약 (현행 branch 주 계약)

| ID | symbol | value | 비고 |
|---|---|---|---|
| SV01 | adversary_start_x | 300 m | ③ docs/59 §1 (~10 s 응답시간). DOCUMENTED |
| SV02 | episode_len(v2) | 800 | ⑥ 310/8→40 s 산술. **단 results/…480_\* 의 480은 코드 어디에도 없음 → SUSPICIOUS** |
| SV03 | ring_center(v2) | (50,0,0) | ③ NK 밖·cone 상류. DOCUMENTED |
| SV04 | SCALE_V2_SPAWN.dx | 10 m | ⑥ ±0.5 s @20 m/s. JUSTIFIED |
| SV05 | A2_V4 jink_amp | 0.6 | ③ V4 선언 — **params.py 미등록, v3_distribution_hash 페이로드에도 없음** |
| SV06 | THREAT_V3_NOMINAL | sprint 60/1.0, slowdown (90,60)/0.5, route 0.5, sense 30 | ③ docs/60 §7 동결 조작점("정답값 아님"). CLAIM-CRITICAL (reactive rerun 세계 정의) |
| SV07 | THREAT_V3_SPAWN | dx0 / r U[250,350] / az π/4 | ③ docs/60 §4.2. DOCUMENTED |
| SV08/13 | standby R | 12 nominal / U[8,16] | ③ 제약: r_nk 6 밖 + 비중첩. DOCUMENTED |
| SV10 | route_gain 층화 | (0.2,0.4)(0.4,0.6)(0.6,0.8) | ③ docs/68 재예비등록(P95 RED 후). bin 경계 자체는 무앵커 → NEEDS-EXTERNAL-ANCHOR |
| SV11 | V3_SENSE_COMMON | (15,45) m | ③ nominal 30 ±50%, 앵커 없음. SCOPED |
| SV12 | sprint/slowdown TRAIN | (40,80)/(0.8,1.0)/(20,40)/(0.4,0.8) | ③ docs/61 §2. DOCUMENTED (외부앵커 없음) |
| SV14 | EPISODE_LEN_TRAIN | 1100 | ⑥ 52.5→55 s 산술. JUSTIFIED |
| SV15–18 | 3×3 층화, iid band 10000.., dist hash, V3_ARMS | — | ③/⑥/⑤ |

### B.3 spawn_rand.py

| ID | symbol | value | 비고 |
|---|---|---|---|
| SR01 | SpawnSpec.dx | 2.0 m | ⑥ ±0.1 s @20. JUSTIFIED |
| **SR02** | **SpawnSpec.r_lat** | **5.0 m** | **③ "= ring_radius" — 값 복사이지 코드 연결 아님. v2에서 ring이 x=50으로 이동해도 r_lat은 조용히 5.0. HIDDEN-UNDERDOC (기감사 계기 사례 확인)** |
| SR03–05 | psi 0 / speed_frac 0 / r_range None | — | ③ 의도적 off 축. 문서화됨 |
| SR06–09 | SHA256 u-derive / 면적균일 disc / cap 균일 / standby 2π/n quotient | — | ⑤/⑥ JUSTIFIED |

### B.4 sim/analytic.py (적분 백엔드)

| ID | symbol | value | 비고 |
|---|---|---|---|
| AN01 | omega_max 기본값 π | dataclass default | 합성 경로에서 DEAD (make_env가 항상 명시 전달) |
| AN03 | 적분 계약 | clamp a → v(clip) → p → slew(Rodrigues), substep 없음 | dt=0.05 (20 Hz). semi-implicit Euler. 문서화됨 |
| AN05 | ref-switch 0.9 | 수치 가드 | θ=0.9와 숫자 충돌(무관) — grep 위험만 |

### B.5 env.py (FROZEN — 그러나 모든 M4 스택의 내핵으로 ACTIVE)

params.py 레지스트리가 커버 (capture rule "(not boxed_in) ∧ v_shot_worst≥1.0 at fire", step_seed 100003, fire decode 0.5, dead: capture_thresh 0.95 / omega_att_max 8.0 vs backend 10.0). 신규 발견 1건:

| ID | symbol | value | 비고 |
|---|---|---|---|
| **EF02** | **Layout.r_ring default** | **2.2** | **레지스트리·YAML=2.1과 불일치하는 그림자 기본값. train 경로에선 항상 override되어 무해하나 bare Layout() 사용 시 발동. SUSPICIOUS** |

### B.6 m4_config.py — M4 운영점 (Phase III 실측 세계)

| ID | symbol | value | 비고 |
|---|---|---|---|
| M401 | episode_len | 160 | ④ TRUNCATED 수렴 연구. JUSTIFIED |
| M402 | tau_deploy | 0.30 = 0.15+0.10+0.05 | ① Xu Fig.6 0.13→0.15 + Pliska 10 Hz + dt. 선언적 하한. CLAIM-CRITICAL/JUSTIFIED |
| M403 | kill_radius | 0.75 | ⑥ 0.21+0.25+유도오차 중앙. sweep (0.6,0.75,0.9). JUSTIFIED |
| M404/405 | omega_max 2.0 / limiter_omega 2.5 | rad/s | ① Pliska. ring regime 44.8% binding. CLAIM-CRITICAL |
| M407–409 | cone R_max 8.22 / half 0.2121 / ρ 1.77 | — | ⑥ 8.22=τ_flight 이동거리; 0.2121=arctan(1.77/8.22) **하드코딩 literal(항등식 미강제)**; 1.77=1.997×0.888 낙관 상한 caveat 명시 |
| M410/411 | THREAT_BRACKET | a U[11,**78**] / v U[8,30] | 하한 ① Pliska. **상한 78 = docs/31 AI-extract DRAFT (최약 앵커, KSAS 인쇄) → NEEDS-EXTERNAL-ANCHOR**; 30 = 선언 |
| M412 | 능력비 | a_lim 0.35·a_att / v_lim 1.0 / adv_v 1.5 | 0.35·1.0 ① Pliska; **1.5 = legacy headroom 무앵커** |
| M413 | adversary_omega 10.0 유지 | — | ④ 4000 draw 0.0% binding 검증 (worst 9.75). JUSTIFIED |

### B.7 Attacker (attacker_ladder / adversary) — 상세는 트랙 2 원표, 요지

| ID | symbol | value | 비고 |
|---|---|---|---|
| ATT-01 | FWD_GAIN (k_f) | 4.0 s⁻¹ | ④ 등록済(TUNED). Gate 11에서 k_f·τ 승격으로 해소된 기감사 사례 |
| **ATT-06** | **jink_freq** | **1.5 Hz** | **UNKNOWN provenance. τ_deploy 0.30 s 대비 회피 시간척도(f·τ=0.45). 미등록. CLAIM-CRITICAL** |
| **ATT-07** | **jink_terminal_r** | **3.0 m** | 3 m 내 모든 회피 off (jink+route 공통 게이트). P2 실패 후 도입 선언은 있으나 값 자체 무앵커·미sweep. 라벨 플립 가능 |
| ATT-05/V3-01 | jink_amp | 0.6 (A2_V4) | ③ docs/60 동결이나 **params.py·dist-hash 미등록**. 최다 사용 attacker 수치 |
| ATT-08/14 | route_gain 0.5 / sense_range 30 | T1 구성 | ③ docs/60 #5/#6 + docs/80. KSAS rerun 정의값. sense는 **route 항만** 게이트 |
| ATT-15–19 | bait 계열 (0.5 / (4,16) m / 3×r_kill) | A3 전용 | 캠페인 미사용(test only). bait_range는 실제 fire geometry(8.22) 미추종. INACTIVE |
| ADV-02 | dodge_amp | 1.8×a_lat | ④ 등록済. commit 후에만 활성 |
| ADV-04 | repel 형태 (1+strength) | 접촉 시 2배 | 구조 선택 무명명. HIDDEN(minor — 접촉거리 한정) |
| ADV-06 | react_on_commit | True | ③ S8 채널(i). **0-tick·전역·무노이즈 — B2 구조 가정** |

### B.8 Defender / FSM / obs

| ID | symbol | value | 비고 |
|---|---|---|---|
| BAS-04/05 | limiter kp 8.0 / kd 4.0 | ④ L1 demo 등록済 | arc_redeploy가 재튜닝 없이 재사용(docs/63 선언) |
| BAS-06 | pressure idx3=1.0 | RESERVED | **M4에서 commit bit로 재해석 — _zero_commit 없이 재사용 시 step-1 전원-commit 함정 (rollout_gif 기지 버그)** |
| ROL-02 | FireGate default θ 0.8 | legacy | bare 생성 시 band 이하 게이트. rollout_gif 라벨 stale (기지) |
| MOB-02/03 | MOBILE_A/V_MAX | 15.413… / 25.945… | **16자리 하드코딩 float가 "시나리오 값과 동일" 주장 — 재계산 없음, M4 draw에선 거짓. SUSPICIOUS (docs/51 진단 전용이라 격리됨)** |
| FSM | fire iff v_soft≥θ_fire ∧ cmd, τ_lock 0.1, K=1, miss 회계 | — | R1/R2/S3 설계핀. JUSTIFIED |
| OBS-02 | 위협 분류 오차 0 (oracle) | ③ | 방어자 유리 한정 — 논문 명시 의무 선언済 |

### B.9 Certificate / judge (viability + gates)

| ID | symbol | value | 비고 |
|---|---|---|---|
| V02 | n_samples 2000 | ③ 2A' spike (n=500 unsafe 0.190) | JUSTIFIED |
| V05/07/13/14 | n_t 24 / n_dir 32 / n_azimuth 8 / turn_safety 0.999 | ⑤ 등록済 | finite-witness caveat 명시. gate-2/3 섭동으로 부분 방어 |
| V16 | capture cutoff worst≥1.0 | ④ S5 | CLAIM-CRITICAL |
| **P01/F09** | **θ_fire = 0.9** | **③ CALIBRATED — 단 M2 fixture(τ 0.4, ρ 2.0, point_mass, n=800, v_speed 8.0)에서. M4/θ_S2/Gate7로 무재보정 이월. F05/F06(n=800, v=8.0)은 자체 무근거** |
| H01 | THETA(θ_S2) 0.90 | ④ docs/74 §4.1 | θ_fire와 수치 동일·역할 상이 (4중 역할: fire/θ_S2/Gate7 9/10/label) |
| H03/04 | Gate2/3 bar 0.02/0.05 | ④ 선언 | 유도 없음 — Gate10 Tier2 bar로 재사용. SCOPED |
| H08–10 | probe (0.6,1.0)·1.2r_kill·k=4 | ⑤ | **2회 실패 후 채택(선언은 정직) — after-preview. coarse_pilot 구성 후보에 전파** |
| U01–04 | D=R³∖Ball(6.0), tube-in-NK, v_max=G/(G+U), G=0→0 | ② | 건전 방향 문서화. CLAIM-CRITICAL/JUSTIFIED |
| G01–03 | Gate7 Fraction(9,10) 정수 산술, NODE_CAP 2e5, d_max_outer | ②/④ | r2 반례탐색済. JUSTIFIED |
| C01–03 | **coarse_pilot RHO/TAU/R_NK 하드코딩 복사** | ② | **gate7 adapter·f0a가 원본 아닌 복사본 import — 분기 위험** |
| C05 | κ grid max 1.1 < κ\*≈1.69 | ④ | "κ 무감도" claim은 pre-onset 한정으로 이미 정정 (docs/77 [E]) |
| C10/C12 | pre-screen 도달식 / 라벨 컷 (V0≥0.9 FREE 등) | ② / ④ docs/74 §3.4 | F-0a false-INF 0/210 감사済. CLAIM-CRITICAL |
| C15 | ramp 도달식 3중 구현 | ② | contact_reachability / coarse_pilot / gate7 — 현재 대수 동일, 편집 시 탈동기 위험 |

---

## C. Hidden / arbitrary constants — 중요도순 RED FLAG 등급

**FATAL NOW: 없음.** (현행 핵심 결론을 무효화하는 항목 미발견)

### FIX BEFORE KSAS (전부 서지·기록 수준 — §G와 동일)

| # | 항목 | 위치 | 이유 |
|---|---|---|---|
| K1 | **78 m/s² 출처 확정 또는 "선언" 격하** | m4_config.py:182; draft §2.1/§3 | 인쇄 숫자 중 유일 무인용. draft 자체 open 항목 |
| K2 | **rerun JSON에 route_gain/sense_range 기록** | curve_sweep.py:191-194 `_save` | T1/T0 아티팩트 구분 불가. 진행 중(500/2700)이므로 지금 고치면 최종본에 반영 가능 — 단 본 감사는 read-only이므로 별도 승인 후 |
| K3 | **legacy↔rerun 병치 caveat** | draft §2 각주 | SystemSpec 구계약 vs ratified F-flags — attacker-only 비교 아님 |
| K4 | pooled n 재확인 (1,635 / 518 / 904) | docs/45:251,286 | draft 자체 플래그 "제출 전 재확인" |
| K5 | stale 상수 2건 정리 | m4_env.py:195 (a\*=44.4→39.3); curve_sweep.py docstring (24.06→23.82) | 인용 사고 방지 |

### FIX BEFORE arXiv

| # | 항목 | 이유 |
|---|---|---|
| A1 | **θ=0.9 재보정 or 라벨 유병률 θ-sensitivity {0.85, 0.90, 0.95}** | M2 fixture 보정값의 M4 4중 역할. zero-waste band는 cone judge 하에서 미재유도. calibration n=800 < ratified 2000 |
| A2 | **jink_amp 0.6 / jink_freq 1.5 Hz 등록 + sensitivity or nominal-fixed scope 공식화** | 회피 진폭·시간척도(f·τ) — 경계 위치에 직접 작용, provenance 없음 |
| A3 | ρ = R_max·tan(θ_half) **항등식 assert** + coarse_pilot RHO/TAU/R_NK 복사 단일화 + ramp 식 단일화 | 수동 유지 중인 파생 관계 3건 |
| A4 | χ grid 상단 78.67 > bracket 78 정합 | Π-grid가 등록 위협 bracket을 초과 |
| A5 | κ grid 확장 (≤1.1 → κ\*≈1.69 포함) | 기지(sealed) — Phase III-B |
| A6 | r_nk=6.0 근거 문서화 (docs/57 소급 or 재선언) | INF 도메인 정의 경계 |
| A7 | scale_v2 계열 결과 meta에 resolved config(m4_env.contract_manifest) 스탬프 | episode_len 3세대 혼재 재발 방지 |

### DOCUMENT ONLY (scope 문장으로 충분)

sense_range의 단일-항 게이팅(R1) · commit 0-latency 전역 채널(R2) · jink_terminal_r=3.0(R3) · c_lim=0.1 · 방어자 전지(全知)+오차 0 분류기(R8, 이미 선언済) · MOBILE_\* 하드코딩 float(진단 전용 격리) · Layout.r_ring 2.2 그림자 · 480-step run 기록 부재 · adv_v_max 1.5× legacy headroom · repel (1+strength) 형태.

### LATER ROBUSTNESS

n_dir=32 witness 밀도 · probe placement (after-preview) · V3 bracket endpoint (sense (15,45), sprint/slowdown, gain bin 경계) · dodge_amp 1.8 · Gate2/3 bar 0.02/0.05 유도.

### Sensitivity 우선순위 (§11 규칙 적용)

- **HIGH impact × HIGH uncertainty → 최우선 sensitivity**: θ=0.9 (라벨 측), jink_freq·τ, jink_amp, r_nk(라벨·veto 측).
- **HIGH × LOW → provenance/문서화**: τ=0.30, ρ=1.77, a\* 대수, kill_radius 0.75, ω_max 2.0 (전부 caveat 존재 — 유지).
- **LOW × HIGH → scope caveat**: bait 계열(비활성), V3 nuisance endpoint, c_lim.
- **LOW × LOW → 동결**: eps류, seed 규약, PARK_POSITION.

KSAS 마감 전 **필수 sensitivity 실험은 없다** — K1~K5는 전부 서지/기록 작업이다. θ·jink sensitivity는 arXiv 게이트.

---

## D. Derived / redundant — 독립 knob로 착각 금지 목록

**Primitive set (M4 활성)**: S_NP 12.54 m²(Xu) · inradius ratio 0.888(측정) · τ_flight 0.15 · τ_sense 0.10 · τ_decide 0.05 · dt 0.05 · a bracket (11,78) · v bracket (8,30) · 능력비 (0.35, 1.0, 1.5) · kill_radius 0.75 · ω_max 2.0 · θ=0.9 · r_nk 6.0 · 배치 기하(300, (50,0,0), R_standby, r_lat 5) · attacker 거동 (jink 0.6/1.5 Hz/3.0 m, route 0.5, sense 30, k_f 4.0, dodge 1.8).

**Derived (독립 아님)**:
- ρ 1.77 = √(12.54/π)·0.888; R_max 8.22 = f(τ_flight); **half_angle 0.2121 = arctan(ρ/R_max) — literal 저장, 미강제**
- a\* 39.33 = 2ρ/τ²; χ·κ·μ·η·ν·λ 등 Π 12종; x_fire 16 = R_max + v·τ + 2 (반올림)
- episode_len 800/1000/1100 = 이동시간 산술; n_kill 3 = τ_kill/dt; c_fire = θ·B; homing_gain = FWD_GAIN 상속(신규 DOF 0 선언)
- M2 세대: 0.067 = arctan(1.998/29.8) — **레지스트리 등록값(2.0/29.847)과 다른 입력 사용** (문서 불일치, M4에선 비활성)

**중복 정의(값-복사, 코드 비연결)**: ρ/τ/r_nk (m4_config·env_sys ↔ coarse_pilot:82,84 ↔ gate7/f0a가 복사본 import) · r_lat 5.0 ↔ ring_radius 5.0 · θ 0.9 4중 역할 · commit_threshold 0.5 ↔ fire decode 0.5 · standby R 12 2중 정의 · ratified flags ↔ scale_v2_baseline 수기 · ramp 도달식 3중 구현 · omega_att_max 8.0 3중(전부 DEAD, 실제 10.0) · repel_margin 1.0 3중(함수 default 1.5는 사문).

---

## E. Cross-campaign contract matrix

C1=T0 legacy curve · C2=T1 reactive rerun · C3=coarse pilot · C4=Gate7 · C5=Gate10/11 · C6=scale_v2 baseline.

| parameter | C1 | C2 | C3 | C4 | C5 | C6 | safe to compare? |
|---|---|---|---|---|---|---|---|
| spawn | 24±2, r_lat 5 | 동일 (CRN 짝) | r U[250,350], az±45° | =C3 | =C3 (×α) | 300±10, r_lat 5 | **C1↔C2 YES (paired)**; 그 외 NO (24 m vs 300 m regime) |
| sense_range | ∞ | 30 (복도<30 ⇒ 사실상 ∞) | U[15,45] (terminal-only) | =C3 | =C3 | ∞ | **NO — 동명 3-의미** (무제한/비구속점/구속 분포) |
| attacker 반응 | T0 | T1 점(0.5) | T1 분포 U[0.2,0.8] | =C3 | =C3 | T0 | **NO** T-급 간; C2↔C3도 NO (점 vs 분포, docs/80 §2) |
| limiter mode | hold/intercept | 동일 | hold, fire never | 동일 | 동일 | hold, clean | C1↔C2 YES; C3–C5는 capture-blind probe |
| τ_deploy | 0.30 | 0.30 | 0.30 | 0.30(=T) | 0.30·β | 0.30 | **YES** |
| net 기하 | ρ1.77/8.22/0.2121 | 동일 | 동일 | 동일 | ×α | 동일 | **YES** |
| 속도 클램프 | 비율 draw | 동일 | v 19 핀 | =C3 | ×(α/β) | =C1 | C1/C2/C6 YES; C3–C5는 nominal-slice |
| a_att | U[11,78] | 동일 draw | χ·39.33 ∈[15.7,**78.7**] | 부분 | χ{0.8,1.6} | U[11,78] | C1↔C2↔C6 YES; C3 상단 bracket 초과 flag |
| judge | runtime θ_fire 0.9 | 동일 | offline union θ_S2 0.9 | byte-identical union | 동일 | runtime | 내부 동일 — 단 θ 두 상수는 의미 상이 |
| dt / horizon | 0.05 / 160 | 0.05 / 160 | 0.05 / 1100 | 1100 | ·β / 1100 | 0.05 / **400→480→800** | horizon **NO** (5종+3세대 혼재) |
| 종료 계약 | **legacy SystemSpec()** | ratified | ratified | ratified | ratified | ratified | **C1 vs 전부 NO** |

**계약 혼합 위험 요지**: ① sense_range 동명 3-의미 ② route_gain 점/분포 (보고명 G1/G2/G3 규율) ③ episode_len 계열 (C6 한 contract 문자열에 3세대) ④ att_speed draw/핀 ⑤ θ 0.9 이중 의미 ⑥ legacy 종료 계약 유일 생존 아티팩트 = docs/45 곡선 ⑦ χ grid vs bracket 끝점.

---

## F. Claim-impact matrix

KSAS 태그: 각 활성 수치의 분류 (§8).

**KSAS-CRITICAL** (analytic/boundary 직결): τ=0.30(+분해 0.15/0.10/0.05) · ρ=1.77(+0.888) · a bracket [11,**78**] · ω_max 2.0 / limiter 2.5 · ψ=4.26°(측정) · θ_fire 0.9 · capture rule worst≥1.0 · jink 0.6/1.5 Hz(곡선 세계 정의) · route 0.5/sense 30(rerun 세계 정의) · limiter_mode hold · spawn 24±2/r_lat 5 · H=160 · 종료 계약 flag.
**KSAS-SENSITIVITY**: w_kill 0.5 · kill_radius 0.75 · jink_terminal_r 3.0 · 능력비 1.5×.
**KSAS-SCOPE-ONLY**: bin 경계·PSI_MED 단일조건 · dt · seed 규약.
**KSAS-IRRELEVANT**: v3 분포 전체(C3–C5 전용) · r_nk(곡선 캠페인의 capture 라벨엔 비관여, veto 회계에만) · bait · M3/PPO 블록 · c1_\* 유산.

5-claim × 지지 실험 (docs 트랙 확정):

| claim | 정의 doc | 지지 | 이 감사의 영향 |
|---|---|---|---|
| 1. capture feasibility map | draft §2.2-2.3; docs/74/75/77 | legacy curve n=2700 + coarse pilot [E] + Gate10/11 | θ-sensitivity 미시험(A1); κ grid pre-onset 한정(기정정); χ 좌표 claim은 "one governing coordinate"로 이미 강등 |
| 2. aiming bottleneck | docs/45 | ψ=4.26→25.8 vs 23.8 (7.5%) | 구조 통과. rerun 생존 조건 pre-registered (docs/72) |
| 3. terminal-blockade INF | docs/79 r2 | Gate7 정수산술 certified (ΔU≡0, 600 states) | 통과 — 가장 강한 사슬. scope 문장 유지 |
| 4. pre-commit shaping 필요성 | Gate7 note §3.5 | ①-B1에서 논리 귀결; ①-B2 미실험 | 통과 (MARL null과 짝짓기 금지 규율 유지) |
| 5. B2/game-layer | docs/80 §7 | P94 GREEN(채널 존재); T_lead 미실행 | §I 선결 조건 |

---

## G. Pre-KSAS actions (최대 5 — 전부 기록/서지 수준, 실험 불요)

1. **78 m/s² 인용 확정** 또는 "assumed upper bracket (declared)"로 명시 격하 — draft ⟦⟧ 해소.
2. **`curve_sweep._save`에 route_gain/sense_range 추가** (1줄) + 이미 저장된 snapshot은 daily note에 CLI 명령 고정 기록. rerun 완료(2700/2700) 전 반영이 이상적. *(read-only 감사 범위 밖 — 별도 실행 승인 필요)*
3. **draft에 legacy↔rerun 계약 차이 1문장**: "legacy 곡선은 구 종료 계약(SystemSpec) 하 실측 — 반응형 rerun과의 델타는 attacker 항 + 계약 항 합성" (curve_sweep.py:145-147 문구 재사용).
4. **pooled 분모 재확인** (1,635 / 518 / 904) — draft 자체 체크리스트 이행.
5. **stale 숫자 2건 정정** — m4_env.py:195 docstring 44.4→39.3(코드는 무변경, 주석만), curve_sweep.py docstring 24.06→23.82. *(주석 수정도 감사 범위 밖 — RECOMMENDED ACTION으로만)*

## H. Pre-arXiv actions

§C의 A1~A7. 핵심 순서: **A1 θ-sensitivity** (기존 rollout 재라벨링으로 가능 — coarse pilot 라벨은 offline union이라 θ∈{0.85,0.90,0.95} 재계산이 저비용) → A2 jink 등록+sweep → A3 항등식/복제 단일화 (기계적) → A4/A5 grid 정합 → A6 r_nk 문서 → A7 manifest 스탬프.

## I. B2/game-layer actions

1. **commit-bit 채널 계약 결정**: 0-tick 전역 감지 유지(선언) vs sense_range 게이트 vs 지연 τ_react 도입 — T_lead 효과가 이 채널과 합성되므로 실험 전 명문화 필수.
2. **route 항 post-commit 게이트 결정** (attacker_ladder.py:199-202): 현행은 T1이 commit 후에도 route 유지 → T0/T1의 post-commit 회피 강도 차이 = 단일축 규율(docs/80 §4) 위반 소지. 유지한다면 선언.
3. **train_m4/mission_eval 배선 격차 해소** (RESET audit 5-blocker) — 학습·측정 세계 일치 전 learned-B2 arm 금지.
4. sense_range를 B2 명시 변수로 (docs/80 봉인済) + policy 관측 여부 결정 (현행 미관측 — implicit randomization caveat).
5. B2 실행 세계(24 m 복도 vs 250-350 m) 및 route_gain 점/분포 선택 고정 — 동명이의 혼합 방지 (§E 규율).

---

## 부록: Observability 타임라인 (§7 — 트랙 2 전문 요약)

| 단계 | Attacker 정보 | Defender 정보 |
|---|---|---|
| spawn | 자기 full state + 표적 + **전 limiter 위치(role 구분됨)** + finisher 위치 + commit bit. route 항만 sense_range 게이트 (KSAS: 복도<30 ⇒ t=0부터 활성; Phase III: 접근 200-300 m 동안 비활성) | **전 에이전트 full state 무제한·무지연·무노이즈** + certificate 3종 + (M4) 오차 0 위협 분류 |
| detection | 이벤트 없음 — 유일 경계: d(limiter)≤sense_range → route on | 항상 전지 |
| shaping | route(T1)/repel(접촉)/jink(open-loop 0.6·1.5 Hz)/homing(4.0)/속도 프로파일 | limiter PD(8/4) 또는 policy; fire gate 폐쇄(θ 0.9) |
| commit | **같은 tick** dodge 1.8 on, jink off, **route는 계속** | FSM DEPLOYING; CommitMeta 동결 (deploy는 동결 메타 대비 해결) |
| deploy (0.30 s) | 동결된 net_center 예측 대비 회피 지속 | 결정 없음 |
| capture | miss 시 SPENT(K=1) 상대 | capture = (¬boxed) ∧ worst≥1.0 at fire |

양측 모두 **센서 모델 부재** — 모든 "관측" 서술은 기하 게이트의 별칭. 문서의 detection 서사와 코드의 대응은 이 표가 기준.

---

## 미등록 활성 무차원군 (§6 — 등록 Π 12종 외)

Gate 10/11이 이미 포획·해소: k_f·τ (승격済) · r_lat/ρ (스케일링 반영済) · T̃_reach=T_reach/τ (caveat 별도 prereg). **잔여 활성-미등록**: f_jink·τ = 0.45 · A_jink = jink_amp(이미 무차원, 미등록) · r_jt/ρ = 3.0/1.77 ≈ 1.69 (jink_terminal_r — 우연히 κ\*와 같은 자릿수, 무관) · r_nk/ρ ≈ 3.39 (sig_as 정의에 흡수 예정 여부 확인 필요) · dodge 1.8 · route 0.5 (이미 무차원, nominal 동결 선언). "미등록 = 결함"이 아님 — 전부 nominal-fixed scope로 처리 가능하나, A2 액션에서 jink 2종은 등록 권고.

---

*감사 방법 각주: 5 병렬 subagent (env/sim · agents/observability · certificate · execution-path · docs/claims), 각각 독립 file:line 인용. 코드·문서 수정 0. 본 보고서의 모든 RECOMMENDED ACTION은 제안일 뿐 미실행.*
