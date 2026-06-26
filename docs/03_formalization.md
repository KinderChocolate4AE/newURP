# newURP_M1_formalization_scaffold (v3 — S1–S8 RATIFIED 2026-06-26)  [CURRENT]

> S1–S8 = Hyunjun 비준·동결 (2026-06-26). strawman→결정 완료. 변경은 §F kill-switch가 M2에서 발화할 때만.
> 정식화 코어 소유 = Hyunjun. AI = 구현·scaffold·디버그 보조.
> **규율(과검증 교훈)**: 동결된 S1–S8로 M2 build 즉시 진입. OPTIONAL(S10–S14)은 *필요할 때만*. **S9는 OPTIONAL 아님 → M3-reserved economic validation**(§G).
> **6-DOF 2층위**: 정식화 = SE(3)-aware deploy viability(S2/S5/S8). M2 build = reduced-attitude pointing + angular-rate limit(full 6DOF aero 모델 회피). Later = full 6DOF dynamics + deploy-aware judge.

## A. must-distinguish 대조 시트 (선택이 이 축 벗어나면 seam 이탈)
| 선례 | 그들이 하는 것 | 우리가 다른 축 |
|---|---|---|
| **Atkinson & Kress 2025** (Oper.Res. 73(4):1767, 10.1287/opre.2024.1025) | 유한 hard+soft, leakers vs 요격소모 **efficient frontier**, shoot-look-shoot | frontier를 **mobile shaping**으로 *움직임*; 비파괴 net; MARL |
| Von Moll turret+defender 2025 (arXiv:2509.09777) | 이종팀, 적을 turret 도달집합으로; HJI | net 전개 viability(각도 아님); 학습; 유한·miss-free |
| Chen luring 2024 (Astrodynamics 8(4):675) | inducer 유인→teammate 요격 | 비파괴 finite; MARL; 목적=교환비 |
| StringNet 2021 (Front.Robot.AI 8:640446) | 대형 장벽 봉쇄 | 발사형 유한 net; 목적=경제 |
| **Liu 2025** (multi-UAV-tethered netted system, arXiv:2506.03297) | **tethered 연속 그물** 포획; vision estimation + MBD dynamics + MAPPO; 비협조 표적 | **발사형 유한 net-shot** + deploy-delay **shot-value shaping** + 교환경제; tether·연속그물 아님 ← *가장 가까운 신규 위협* |
| WTA/salvo (Manne'58·Hughes'95·Armstrong'14) | 고정 사수 배분·타이밍 | maneuver-shaping이 lever; 비파괴 |
| 狼群 2021 (智能系统 16(1):125, 10.11992/tis.202007043) | 이종역할+비용, 규칙·kinetic | MARL; 비파괴; 비용=교환비 |
| sequential-intruders (arXiv:2212.06628) | 재사용 point-capture | 유한·비가역·비파괴 |

> **인용 위생 (검증 2026-06-26)**: "MARL 다중드론 pursuit + limited-FOV + physical dynamics"는 *붐비는 작업군* — 한 편으로 뭉뚱그리지 말고 군으로 인용(예: arXiv:2409.15866 physical-constraint multi-UAV PE DRL; IEEE/CAA JAS limited-visual-field MUV-PE). **"Huh 2026" = 실재 prior** (Huh·Lim·Jang·Byun·Yu·Nam, *Machines* 14(4):413; 구 capture-set plan의 B-3 baseline, geometric MARL pursuit) — 정확히 인용하되 이 한 편으로 작업군 전체를 대표시키지 말 것. **"Jia 2026 counter-drone GAT+MAPPO" = 코퍼스에 없음·미확인 → 확인 전 인용 금지.** UAV Hunter(*Drones* 2024, 8(10):573) = "net-capture UAV 존재" 배경 인용만.

## B. 핵심 슬롯 (S1–S8) — RATIFIED 2026-06-26

**S1 플레이어&소모성** · [결정]: N limiter + **1 SE(3) finisher** + 적 1; M2는 단일 적. **binding 자원 = finisher net K-shot.** limiter는 kamikaze/kill-radius 가질 수 있으나 *소모성 미사일 아님* → **cost-bearing shaping pressure**(reachable-set 압축); limiter 손실 = cost term.
- 정본 문장: *"Limiters may carry a terminal kill-radius and incur loss cost, but the binding scarce resource in the M1/M2 formalization is the finisher's finite net-shot. Limiter actions are modeled primarily as mobile constraints that compress or bias the attacker's deploy-delay reachable set."*

**S2 상태** · [결정]: x = {p_i, v_i, R_i, ω_i}_def,att + {k, τ_deploy, τ_lock}. finisher 필수: p_F, v_F, R_F, ω_F, **n_F = R_F·e_net** (net-pointing axis). 적 내부 mode는 M2 state에 넣지 않음(scripted label로 관리).
- 6-DOF 2층위: 정식화 = finisher SE(3) pose + body-rate; M2 build = reduced-attitude pointing + angular-rate limit.

**S3 액션** · [결정]: limiter = continuous setpoint/accel (+ terminal kill-radius pressure). finisher = **fire∈{0,1} 비가역**, 발사 후 τ_deploy 전개지연 + τ_lock 잠금. attacker = bounded accel/heading. **M2엔 discrete {feint, penetrate} 안 줌** → S10/S13.

**S4 정보구조** · [결정]: M2 = **CTDE full-state 학습 + decentralized/local 실행**. fire = **물리적 commitment**(deploy-delay reachable-set 유발)로 처리, **signaling/baiting equilibrium으로 해석 안 함** → S11 분리.
- 정본 문장: *"We do not model signaling equilibria in M1/M2. The firing event is treated as a physical commitment that induces a deploy-delay reachable-set problem, not a strategic communication channel."*

**S5 per-shot value** · [결정]: **novelty = v_shot 자체 아님 → Δv_shape = v_shot(x, u_L, u_F) − v_shot(x, u_L^0, u_F)** (limiter 기여).
- 6-DOF: **v_shot = P[ x_A(t+τ) ∈ N(T_F(t+τ), n_F(t+τ), τ_deploy) ]**, T_F ∈ SE(3); deploy volume N은 finisher 위치+자세+pointing axis+deploy delay+angular-rate 제약으로 결정 (= "적이 range 안" 이 아니라 "finisher가 그 자세로 net volume을 만들 수 있나").
- robust: **1[ Π_p R_A,SE(3)^br(x, τ | u_L) ⊆ N(T_F, n_F) ]**.

**S6 목적함수** · [결정] **(2층 — 핵심)**:
1. **M2 = local shot-value shaping만.** J_M2 = Δv_shot + λ1·1[v_shot ≥ θ_fire] − λ2·wasted_fire − λ3·limiter_loss. success signal = (Δv_shot > 0) ∧ (threshold crossing) ∧ (wasted shots 안 늘어남).
2. **economic frontier / exchange-ratio는 M2에서 주장 금지** → **S9 sequential raid(M>1 또는 K binding)에서만 선언**(M3).
- fire rule = threshold: **fire iff B_capture·v_shot(x) − c_fire ≥ V_continue(x, k) − V_continue(x, k−1)**.

**S7 해 개념** · [결정]: **closed-form differential-game value 주장 금지.** learned heterogeneous shaping policy + reachable-set-grounded analytic surrogate + (capacity × 속도/기동비) **empirical viable envelope**. 차분게임 value = 대조군 인용만.

**S8 shaping-as-lever (THE 코어)** · [결정]: 채널 **3개만** 유지 —
- ① **escape reachable-set compression** (최강; **kamikaze kill-radius가 이 채널**)
- ② **net-volume alignment / cone coverage** (anisotropic net)
- ③ **threshold-based ammo preservation** (fire iff v_shot ≥ V(x,k) − V(x,k−1))
- **폐기: "적 depletion"** (적 소모자원 없으면 무효; bounded accel만이면 순간 reachability 변화일 뿐).
- 신용할당: **COMA difference-reward** D_i = v_shot(u_i, u_-i) − v_shot(u_i^0, u_-i) (Foerster et al. AAAI 2018); **baseline u_i^0 = {do-nothing / hold-position / nominal pursuit} 중 하나로 고정**(매번 바꾸면 reward hacking). terminal-only 보상 금지.
- 6-DOF: R_A = **SE(3) reachable-set**; capture judge = position + relative-velocity + approach-angle + **finisher-pointing feasibility** 동시.

## C. M2 DoD (이것만 죽어라 보여줄 것 — thin novelty 생존선)
**u_L ≠ u_L^0  ⇒  Δv_shot > 0  ∧  fire threshold crossed with fewer wasted shots.**
M2는 **경제 frontier 증명 시도 금지.** 위 세 가지(Δv_shot > 0 + threshold crossing + no wasted-shot explosion)만.

## D. 조기 sanity (구 'probe' — M2 초 1회, 별도 게이트 아님)
toy 1 limiter + 1 finisher(K=1) vs scripted bait. shaping on/off로 v_shot 차이 1회 확인 → 음성이면 재고. 의식화 금지, build 안에서.

## E. 자가 점검 (build 전): S1–S8 채움 ✓ / §A 축 위반 0 / S8 수식 닫힘 / 현실 파라미터(capacity·속도/기동비·net spec·SE(3) attitude/rate limit).

## F. Kill-switch (가정별 M2 반증 조건 — "반증가능 scaffold")
| 가정 | M2 반증 조건 |
|---|---|
| deploy-delay shaping | shaping on/off의 Δv_shot이 noise 수준 |
| limiter 역할 | COMA difference reward D_i가 0 근처 |
| finite-shot value | fire threshold crossing이 direct pursuit 대비 차이 못 만듦 |
| heterogeneity | homogeneous C2 reward와 성능 차이 없음 |
| SE(3) net viability | point-mass surrogate는 좋아 보이나 attitude/deploy-aware judge에서 붕괴 |
| economic extension | sequential raid에서 K가 binding 안 되거나 frontier 이동 없음 |

## G. OPTIONAL / RESERVED 슬롯
- **S9 raid process [M3-RESERVED economic validation · OPTIONAL 아님]**: 순차/포화 적 M (유한자원 K binding되는 곳). M2는 K=1 단일; **economic frontier 주장은 여기서만**.
- **S10 적 feint 비용 c_feint** [OPTIONAL · 후순위 방어]: miss-is-free를 가정 아닌 *구조*로. paper review 대응용.
- **S11 관측성 축** (full/delayed/hidden ammo·commit = 다른 게임) — S4 signaling 분리.
- **S12 reload/logistics** (no-reload/slow/cartridge/spent-net obstacle) — capacity binding 여부 결정.
- **S13 적 best-response 프로토콜** (scripted→optimization→self-play→OOD→관측성 ablation) — "weak adversary" 방어.
- **S14 surrogate(v_shot) 검증** (held-out·reliability curve·net param 민감도) — "reward engineering" 방어.
> 활성화: M3 결과 약하거나 리뷰어 방어 필요할 때 *그때* 해당 슬롯만. 처음부터 전부 금지(과검증 재발 방지).
