# 10 — 명제 N: "shaping 필요성" 최소 명제 (1D 인스턴스) — DRAFT v0.1

> **상태: AI 초안 (2026-07-03) — Hyunjun 비준 전.** 정식화 코어 소유 = Hyunjun(03 규율); 이 문서는 스캐폴드다. 기호·경계값은 M2 config(`configs/m2_l2_train.yaml`)와 일치시켰고 증명은 스케치 수준. 엄밀화·논문 배치 결정 = Hyunjun-lane.
> **역할:** backdiag 수치 발견(v_shot 1.0→0.16)의 이론 격상 + "그냥 MARL 돌렸다" 리뷰 방어선. **M2 범위** — 경제/frontier 주장 없음(S6 2층 준수).

## 0. 요지 (한 문장)

miss-is-free·유한 K·deploy-delay net 게임에서, 적의 회피 여유 w가 net 반경 ρ를 넘는 한 **무-shaping 방어의 가치는 fire-gate 설정과 무관하게 0**이고, **국소 shaping(escape-lobe 마스킹)은 clean threshold crossing과 확실 포획을 강제**한다 — M2 상수로는 무-shaping plateau v_soft = ρ/w = 5/6 ≈ 0.833 < θ_fire = 0.9, shaped = 1.

## 1. 세팅 (1D deploy-delay net game; M2 상수와 정합)

- 시간 이산. 공격자 위치 x_t ∈ ℝ, 목표 = 원점(x ≤ 0 도달 = 침투), 속도 |v_t| ≤ v̄, 가속 |a| ≤ a_max.
- **finisher:** K = 1, 발사 비가역(S3), 전개지연 τ. 시각 t 발사 시 net = 구간 N_t = [c_t − ρ, c_t + ρ], **명목 endpoint** c_t = x_t + v_t·τ (env의 `net_center` 규약과 동일).
- **회피:** 발사 후 τ 동안 공격자 endpoint 도달집합(무-shaping) R_t = [c_t − w, c_t + w], **w = ½·a_max·τ²** (env `R_lat`와 동일 정의).
- **판정(S5 robust):** capture ⇔ 실현가능 endpoint 전부 ∈ N_t (v_worst = 1). soft 대용 v_soft(t) = |R′_t ∩ N_t| / |R′_t|, R′_t = kill-radius 마스킹 후 실현가능 집합(S8-①).
- **fire gate(R2, FSM 내 하드):** 발사 허용 ⇔ v_soft ≥ θ_fire.
- **limiter:** kill 반경 r의 no-go 구간(kamikaze) n개. u_L⁰ = hold(마스킹 없음).
- **miss-is-free:** 빗나간 발사는 공격자에게 무비용, k → k−1 (S10의 구조적 형태).
- **boxed_in ≠ capture:** R′ = ∅이면 clean crossing 아님(env 규약 그대로).

**가정.**
- A1 (기하) w > ρ. — M2: w = ½·30·0.4² = **2.4** > ρ = **2.0**.
- A2 (게이트) θ_fire ∈ (ρ/w, 1]. — M2: 0.9 ∈ (5/6, 1].
- A3 (정보·반응, S4) 공격자는 commit을 관측하고 τ 동안 반응하며, bang-bang ±a_max로 R_t(마스킹 시 R′_t) 내 임의 endpoint를 실현할 수 있다.
- A4 (escort 실현가능) shaping 시 limiter가 공격자 대비 상대 위치를 유지할 수 있다(v_max 여유; 또는 §4의 corridor 사전배치 변형으로 대체 가능).
- A5 (표준) 공격자 목표 = 침투. 방어 가치 = 침투 저지 확률.

## 2. 보조정리 (스케치)

**Lemma 1 (무-shaping plateau).** u_L = u_L⁰이면 모든 t·모든 공격자 정책에 대해 v_soft(t) = ρ/w (상수), v_worst(t) = 0.
*스케치.* R_t와 N_t 모두 c_t 중심이므로(평행이동 불변) |R ∩ N|/|R| = ρ/w; A1(w > ρ)에서 R ⊄ N. ∎

**Lemma 2 (보장 회피).** 마스킹 없이(R′ = R) 어떤 발사든 A3 공격자는 확실히 회피한다.
*스케치.* R ⊄ N ⇒ endpoint z ∈ R∖N 존재; A3의 bang-bang으로 실현. ∎

## 3. 명제 N (shaping의 필요·충분, 1D 인스턴스)

A1–A5 하에서:

**(a) 무-shaping ⇒ 가치 0 (보수 게이트).** θ_fire > ρ/w이면 게이트는 어떤 상태에서도 열리지 않고(Lemma 1 + R2 하드 게이트), 직진 접근이 공격자 최선반응이며 침투 확률 1. 방어 가치 0 (k는 보존되지만 무의미).

**(a′) 무-shaping ⇒ 가치 0 (느슨한 게이트).** θ ≤ ρ/w로 낮춰 발사를 허용해도 발사 시점의 v_worst = 0이고(Lemma 1) Lemma 2로 확실 miss. miss-is-free ⇒ 사후 게임은 k−1로 동형 ⇒ k 귀납으로 가치 0.
**∴ 게이트를 어떻게 놓아도 무-shaping 가치 = 0. 실패는 게이트가 아니라 구조(w > ρ)다.**

**(b) 2-limiter lobe-마스킹 ⇒ crossing 강제 + 확실 포획.** r ≥ (w−ρ)/2이면 kill 구간 2개를 c_t ± (ρ + (w−ρ)/2)에 두어 escape lobe L± = c_t ± (ρ, w]를 마스킹하되, core (c_t − δ, c_t + δ), δ = ρ − max(0, r − (w−ρ)/2) > 0을 남길 수 있다. 그러면 R′_t ⊆ N_t, R′_t ≠ ∅ ⇒ **v_soft = 1 ≥ θ_fire, v_worst = 1**: escort가 유지되는 매 스텝 clean crossing이 강제되고, 첫 crossing에서 발사하면 **모든** 공격자 정책에 대해 포획(낭비 0). standoff x_fire ≥ v̄τ + ρ + ε에서 교전하면 침투 전에 resolve. 접근을 거부하면 침투 없음 ⇒ 방어 가치 1.
*스케치.* 구성 대입(M2: r=2.0): 마스크 중심 c ± 2.2, 커버 (c+0.2, c+4.2)·(c−4.2, c−0.2) → lobe 완전 마스킹, core = [c−0.2, c+0.2] ⊆ N, p_feasible = 0.4/4.8 = 1/12 > 0 (boxed 아님). 포획은 S5 worst-case 판정이 fire 시점에 동결되므로 A3 반응으로도 탈출 불가. escort 유지는 A4. ∎

**따름정리 (M2 상수 대입).** a_max = 30, τ = 0.4, ρ = 2.0 ⇒ plateau = 5/6 ≈ 0.833.
(i) 보정 θ_fire = 0.9는 정확히 **shaping-forcing 창** (5/6, 1] 안에 있다.
(ii) Δv_shot(headline) = 1 − 5/6 = **1/6 > 0** — M2 DoD 3요소(Δv>0 ∧ clean crossing ∧ wasted 비증가)가 (b)에서 전부 구성적으로 성립하고 (a)에서 전부 부재.
(iii) 레거시 θ = 0.8 < 5/6은 무-shaping plateau에서도 발사 = (a′) 경로 — `fire_gate_calibration`이 실측한 "0.8은 중간 containment에서 낭비"의 이론형.
(iv) 실측 zero-waste 밴드 [0.85, 1.0] 하한이 1D plateau 0.833 바로 위 — 일관성 체크(예측 주장 아님, §4).

## 4. 변형·캐비앗 (정직)

- **corridor 변형(A4 제거):** last-mile 방어에선 초크포인트 사전배치가 자연스럽다 — 공격자가 게이트 구간을 지나는 순간 (b)의 마스킹이 성립. escort 추적 실현가능성 논쟁을 회피하는 논문용 대안.
- **1D는 3D의 사영:** env의 실제 plateau는 샘플링·SE(3) cone·S14 union 때문에 5/6과 다를 수 있음. (iv)는 일관성 체크.
- **존재 ≠ 컨트롤러:** 명제는 shaping 정책의 *존재*를 주장할 뿐 컨트롤러를 주지 않는다 — 동역학·역할분담 하에서 escort를 *찾는* 것이 MARL(L2)의 몫. 이 명제는 학습을 대체하는 게 아니라 학습 문제의 필요성을 정당화한다.
- **backdiag 연결:** 마스킹 안 된 retreat lobe = backdiag 실측(1.0→0.16)의 메커니즘.
- **경제 주장 없음:** K-binding frontier 문장은 S9/M3에서만(S6 2층).

## 5. Hyunjun TODO (비준 전 체크)

- [ ] A3 bang-bang 실현가능성·A4 두 변형(escort vs corridor) 중 논문 채택안 결정
- [ ] Lemma 1을 순수 모델 명제로 둘지, env의 샘플-기반 soft 판정과 정합 서술로 갈지
- [ ] env `boxed_in` ε vs core 폭(p_feasible = 1/12) 확인 — 필요시 r·배치로 core 폭 조정
- [ ] (a′) miss-is-free 귀납을 S10과 연결할지, 논문 배치(method 명제 vs appendix)
