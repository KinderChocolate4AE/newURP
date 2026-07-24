# 협력형 last-mile C-UAS 포획 — 현황 및 Phase 2 계획

**리뷰용 브리핑 · 2026-07-22 (rev. 2, 리뷰 반영)**

> 핵심 연구질문: 이종 다중 방어 드론이 MARL로 공격 드론을 **협력적으로 성형(shaping)**해 포획 가능한 상태로 유도할 수 있는가. 이번 문서는 그 시스템을 개발하는 과정에서 (a) 포획 터미널의 실제 기하를 규명하고 (b) nominal 배치에서의 도달 병목을 **response margin**으로 정량화한 결과, 그리고 (c) 그 위에서 학습 기반 협력 제어(Phase 2)를 여는 계획을 정리한 것이다.
>
> **범위 명시**: 아래 결과는 **동결된 A2 공격자, safe co-design cell, 고정 firing plane, 가속 한계, 시험한 초기 geometry**라는 조건 하의 **fixed-condition discovery envelope**다. 다중 reset·attacker phase에 대한 distribution-level 확인은 Phase 2 초입 과제로 남긴다.

---

## 1. 시스템 구조 (동결)

```
MARL 협력 shaping  →  rule-based fire guard  →  rule-based terminal safety
```

발사(shot)는 learned one-shot으로 재학습하지 않는다. learned-fire는 always/never-fire collapse, premature termination, 성공 rollout 삭제, limiter policy corrosion을 일으켜 폐기했고, **shot은 rule guard로 유지**한다. MARL은 발사 전 **협력적 성형/holding**만 담당한다.

---

## 2. 지금까지 규명된 것 (검증 완료)

**(E1) 추상 회랑은 존재하나 grounded에서 friendly limiter와 교차한다.** seed 1100에서 nominal→fire-eligible shell corridor 확인(v_soft=1, p_feas>0, rule fire, exact replay, local capture). 그러나 grounded net silhouette(r_net,dir≈2.09–2.24)와 기존 limiter axis distance(1.82–2.16)가 겹쳐 **deployment-safe하지 않다**.

**(Move B) 공격자 commitment는 실재한다.** fire 전 net axis에서 ≈0.08 m·속도 ≈20 m/s·crossing ≈0.19 s로 commit; 속도를 축 수직으로 돌리면 capture 붕괴(→ metric artifact 아님). 단 folded net early capture 미검증 — Case B는 공식 judge로 승격하지 않는다.

**(Move A0) 터미널 co-design으로 deployment-safe cell이 열린다.**
$$\eta = \frac{r_{kill}}{r_{net,dir}+r_{body}+m_{safety}}$$
원점 η≈0.758(비실현) → (2.6, 2.1), body 0.2, safety 0.2, θ=0.9에서 **η=2.6/2.5=1.04>1**, 안전 cell 개방(cap>0, clr≈+0.1 m). 판정 `A0_TERMINAL_FEASIBLE_DYNAMIC_UNSOLVED`.

**(A1a) 안전 터미널은 실제 dynamic 상태·국소 self-connecting.** 터미널 box reset→발사→exact replay tier 4(cap 0.52, clr +0.1/+0.2), predecessor k=1..4 연결. ⇒ A0의 "dynamic unsolved"는 터미널 부재가 아니라 **nominal에서 REACHING 문제**.

---

## 3. A1b — 병목의 정체

**capture 터미널은 공격자를 둘러싸는 box가 아니라 finisher 발사축을 두르는 좁은 kill-ring**이다. limiter 4기가 발사축 둘레 ρ\*=r_kill=2.6 m, 축방향 x≈8(공격자[x≈14]에서 6 m 앞)에 위치하고, friendly lane r_lane≈2.5 m보다 0.1 밖이라 **clr≈+0.1 m**. 이 링을 유지하면 공격자가 nominal 거리에서 접근해도 **coast로 tier 4** — 링만 서면 연결은 trivial.

**병목은 nominal 배치에서 이 링을 제때 형성하는 것.** nominal 초기 반경 ρ0=5.0 m → 링(2.6)까지 2.4 m 수축 필요, 가용시간 0.5 s. 이상적 rest-to-rest 하한:
$$T_{form,min}=2\sqrt{|\rho_0-\rho^*|/a_{max}}=2\sqrt{2.4/30}\approx0.566\,\text{s} > T_{avail}=0.5\,\text{s}$$
즉 지연을 0으로 둬도 **response margin이 음수**($M_{resp,LB}=0.5-0.566=-0.066$ s). 관측 실패도 일관: open-loop bang-bang overshoot, PD too-slow(발사 시점 perp≈3.05), CEM 동일 basin; static 링은 coast로 tier 4.

> **결론: 실패의 원인은 capturability 부재가 아니라 초기 deployment geometry와 attacker transit time의 mismatch다.**

---

## 4. Phase 1 결과 (완료)

질문 재정의: 어느 초기 spread ρ0와 가용 response time T_available부터 tier≥4 deployment-safe capture가 열리며, 제어가 물리적 하한에 얼마나 근접하는가? (ρ0=초기 spread ≠ ρ\*=터미널 링 반경.)

### 4.1 Terminal-band calibration

각 ρT에서 angular·axial 기하를 재최적화(slot 제약 없음). 0.1 m grid에서는 2.6만 성공했으나, **0.05 m refinement에서 {2.55, 2.60, 2.65} 모두 tier-4 safe** — 따라서 eligible terminal band는 **"razor-thin"이 아니라 유한 구간**으로, 최소 **[2.55, 2.65] (폭 ≥0.1 m)**를 포함하고 실제 edge는 (2.50, 2.55)와 (2.65, 2.70) 사이에 있다. (정밀 edge 0.01–0.02 m는 후속.)

밴드는 **서로 다른 두 기전으로 bounded**된다:

- **안쪽(ρ↓) = clearance 위반** — clr이 2.55에서 0.05, 2.60에서 0.10, 2.65에서 0.15로, ρ가 작을수록 링이 friendly lane에 가까워짐(물리적 제약).
- **바깥쪽(ρ↑) = hard r_kill cutoff 근방 v_soft 붕괴** — max v_soft가 2.60에서 1.00, 2.65에서 0.93(→θ=0.9)로 접근. capture margin은 중심 2.6에서 최대(≈0.6), edge로 갈수록 감소.

> ⚠️ **정확한 표현**: Reoptimization은 safe terminal set을 ρT=r_kill=2.6 m **근방의 유한 구간**으로 확인했다(razor-thin 아님, 폭 ≥0.1 m). 바깥 edge는 evaluator의 **hard-radius surrogate 산물일 가능성이 크고**(별도 surrogate-sensitivity 진단 대상 — hard kill radius vs smooth influence kernel vs A2 avoidance 기반), 안쪽 edge는 물리적 clearance다. 이 유한 band 폭은 controller의 정밀도 요구를 다소 완화한다(정확히 2.6이 아니라 ±0.05 tolerance).

### 4.2 Response envelope (simple fixed-formation baselines)

ρ0 × T_available 격자에서 **단순 고정-포메이션 baseline**을 평가했다: **hold, analytic contract-and-hold, PD**. (이들은 role-agnostic이 아니라 handcrafted formation controller다. slot-free role-agnostic optimizer와 role-emergent MARL은 Phase 2에서 별도 평가한다. baseline의 성공이 emergent cooperation을 증명하지도, 실패가 협력 제어 불가능을 뜻하지도 않는다.)

**(a) Achieved envelope** — 각 controller가 각 조건에서 직접 달성 (best of C/P, winner 표기):

| ρ0 \ T_lead | 0.2 | 0.3 | 0.4 | 0.5 | 0.7 | 1.0 | (LB) |
|---|---|---|---|---|---|---|---|
| **2.8** | T4 (C) | T4 | T4 | T4 | T4 | T4 | 0.16 |
| **3.2** | t2 (C) | t2 | t2 | **T4 (C)** | T4 | T4 | 0.28 |
| **4.0** | – | t2 (C) | t2 | **–** ⚑ | **T4** | T4 | 0.43 |
| **5.0** | – | – | – | t2 (C) | t2 | **T4 (P)** | 0.57 |

⚑ = 비단조 cell (아래 감사 참조). T4=safe exact replay, t2=eligible fire·lane-blocked, –=무발사.

**(b) Idle-prefix dominance audit (단조성 감사).** 순수 feasibility라면 시간이 늘어 성능이 나빠질 수 없다(짧은 시간 해에 idle-prefix를 붙여 재사용 가능). ρ0=4.0의 T=0.4(t2)→T=0.5(무발사)는 비단조였는데, 감사 결과:

| ρ0=4.0 | 0.2 | 0.3 | 0.4 | 0.5 | 0.7 | 1.0 |
|---|---|---|---|---|---|---|
| achieved | 0 | 2 | 2 | **0** | 4 | 4 |
| **monotone closure** | 0 | 2 | 2 | **2** | 4 | 4 |

4.0/T=0.5는 짧은 시간 해 C(@0.3)를 idle-prefix하면 **tier 2 회복** → 비단조는 **controller artifact**(구조적 아님), closure는 전 행 단조. 기전은 `EARLY_ARRIVAL_OR_HOLD_FAILURE`(시간이 많을 때 naive controller가 링에 너무 일찍 도착·유지 실패). **T4 success 경계는 closure로도 불변** — idle-prefix가 새 T4를 만들지 않으므로 안전-포획 경계는 robust하다.

### 4.3 관측·판정

- compact 배치(ρ0=2.8)는 전 영역 T4; success 경계가 ρ0↑ 따라 우측 이동하며 analytic 하한을 정성 추종.
- **현 nominal 운용점 (5.0, 0.5)의 실패가 response margin으로 정확히 설명**(5.0은 T=1.0에서만 열림, $M_{resp,LB}=-0.066$ s).
- simple-baseline 경계와 analytic 하한 사이 밴드 = **learned/optimized 협력 제어가 좁힐 여지**(controller gap).

```
RESPONSE_ENVELOPE_IDENTIFIED  (simple-controller achieved + monotone closure)
SAFE_CAPTURE_FEASIBLE_WITH_POSITIVE_MARGIN
```

게이트(정확한 문구): **analytic rest-to-rest infeasible 영역에서는 어떤 simple arm도 deployment-safe Tier 4를 달성하지 못했다. Unsafe eligibility인 Tier 2는 일부 나타났다** — Tier 2는 링을 형성하지 못한 채 안쪽으로 crowding해 발사한 결과이므로 analytic 하한의 반례가 아니다.

---

## 5. Phase 2 — 계획

### 5.1 순서 (권장)

1. **단조성 감사** ✅ (idle-prefix dominance — 완료; closure 단조)
2. **Terminal band refinement** ✅ (0.05 grid: band ⊇ [2.55, 2.65], 폭 ≥0.1 m — razor-thin 아님; inner=clearance / outer=v_soft-cutoff; 정밀 edge 0.01–0.02 m·surrogate 민감도는 후속)
3. **Arm O** — slot-free role-agnostic short-horizon optimizer로 각 경계 cell의 controller gap 측정 (analytic 하한 vs simple-baseline 경계). O가 positive-margin cell서도 실패하면 horizon·action parameterization·angular sealing·terminal velocity·target-center tracking 중 무엇이 막는지 먼저 진단.
4. O가 찾은 **safe trajectories 저장** → 최고의 학습 교사.
5. **BC / trajectory imitation**.
6. **actual-trajectory continuation curriculum**.
7. **guard 고정 MARL fine-tuning** (shared policy, role-emergent).

### 5.2 학습 분포 (response envelope 기반)

Stage 1 feasible interior(margin≫0, compact) → Stage 2 boundary continuation(margin→0⁺: cue 지연·spread 확대·latency·velocity perturbation) → Stage 3 sensor/visual 혼합(overlay만 먼저, stochastic 구현은 나중) → Stage 4 소량 infeasible(penetration delay·graceful fallback·no-waste fire, 분포 지배 금지).

### 5.3 능력 검정 (논문 claim보다 우선)

> 학습 컨트롤러가 물리적으로 가능한 response envelope 경계에 얼마나 근접하는가?

analytic 하한 대비 extra response time, rule/PD/optimizer 대비 경계 접근성, unseen cue-time·attacker-speed 일반화, safe-capture basin 폭, state-dependent role emergence로 검정.

---

## 6. 리뷰 반영 요약 (외부 리뷰 전 필수 3 + 권고)

| 항목 | 상태 |
|---|---|
| ① 시간 단조성 / idle-prefix dominance audit | ✅ 완료 — 비단조=controller artifact, closure 단조, T4 경계 불변 |
| ② terminal band 국소 refinement | ✅ 완료 — 0.05 grid서 band ⊇ [2.55, 2.65] (razor-thin 아님, 폭 ≥0.1 m); inner=clearance / outer=v_soft cutoff (surrogate 의심) |
| ③ H/C/P(fixed-formation baseline) vs O(role-agnostic) 구분 | ✅ 문구 수정 |
| 프레이밍 범위 (fixed-condition discovery envelope) | ✅ 반영 |
| 게이트 문구 (Tier4 실패 vs Tier2 존재) | ✅ 수정 |
| taxonomy 추가 | ✅ 아래 |
| 그림 (winner arm·dominance flag·achieved/closure·margin) | ✅ 갱신 |

**Failure taxonomy (추가분 포함)**: `KINEMATIC_NEGATIVE_MARGIN` · `RADIAL_OVERSHOOT` · `RADIAL_TOO_SLOW` · `ANGULAR_SEAL_FAILURE`(radial 링은 맞으나 max angular gap으로 v_soft 실패) · `CLEARANCE_VIOLATION` · `CAPTURE_MARGIN_FAIL` · `EARLY_ARRIVAL_OR_HOLD_FAILURE`(시간 여유에도 조기 도착·유지 실패) · `TERMINAL_RELATIVE_VELOCITY`(위치는 맞으나 잔여 radial/tangential 속도로 다음 step 이탈) · `TARGET_CENTER_TRACKING_ERROR`(고정 축 링은 형성했으나 moving attacker 중심 추적 부족) · `PENETRATION` · `REPLAY_FAIL`.

---

## 부록 — 고정 값·정의

| 기호 | 값 | 의미 |
|---|---|---|
| r_kill / ρ\* | 2.6 m | kill 반경 = 터미널 링 반경 |
| r_net_dir | 2.1 (2.0 secondary) | grounded net silhouette |
| r_body, m_safety | 0.2, 0.2 | body·안전 여유 |
| r_lane | ≈2.5 | r_net_dir+r_body+m_safety |
| θ | 0.9 | eligibility 임계 (v_soft≥θ) |
| η | 1.04 (원 0.758) | r_kill/r_lane |
| a_max | 30 m/s² | limiter 가속 한계 |
| v_closing | 20 m/s | 접근 속도 |
| x_fire | ≈14 m | 발사면 |
| ρ0 | 5.0 (nominal) | 초기 반경 spread |

**analytic radial 하한** (verdict 아님, ideal rest-to-rest): $T_{radial,LB}=2\sqrt{|\rho_0-\rho^*|/a_{max}}$.
**Tier**: 0 무발사 / 1 eligible만 / 2 eligible·lane 미확보 / 3 lane만 / **4 safe(eligible+lane+무관통, exact replay)** / 5 arrival.
**원칙**: 물리 불가능(negative margin) ≠ 학습 실패. "impossible" → "not found at tested budget". 공식 judge·동역학·evaluator 동결.
