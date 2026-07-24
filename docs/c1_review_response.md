# 리뷰 피드백 반영 결과 — Response Envelope Probe

**2026-07-22 · Arm O 착수 전 중간 보고**

주신 4개 지적을 반영했고, 그중 두 가지(①시간 단조성, ②terminal band)는 **새 실험으로 검증**했습니다. 결과를 먼저 공유드리고, 이후 Phase 2의 첫 실질 결과(Arm O controller gap)로 진행하려 합니다.

---

## ① 시간 단조성 — idle-prefix dominance audit ✅

**지적**: ρ0=4.0 행이 T=0.4(Tier2)→T=0.5(Tier0)로 비단조. 순수 feasibility라면 더 많은 시간이 성능을 낮출 수 없음(짧은 시간 해 앞에 hold를 붙여 재사용 가능).

**감사 실행**: 짧은 시간 T1의 best trajectory 앞에 (T2−T1) hold를 붙여 긴 조건 T2에서 exact replay.

| ρ0=4.0 | 0.2 | 0.3 | 0.4 | 0.5 | 0.7 | 1.0 |
|---|---|---|---|---|---|---|
| achieved | 0 | 2 | 2 | **0** | 4 | 4 |
| monotone closure | 0 | 2 | 2 | **2** | 4 | 4 |

- 4.0/T=0.5: achieved Tier0 → **closure Tier2** (idle(C@0.3) 재사용). 다른 행은 achieved부터 단조.
- ⇒ 비단조는 **controller artifact**(구조적 아님). closure는 전 행 단조. **T4 success 경계는 closure로도 불변**(idle-prefix가 새 T4를 만들지 않음) → 안전-포획 경계는 robust.
- 기전: `EARLY_ARRIVAL_OR_HOLD_FAILURE` — 시간 여유 시 naive controller가 링에 너무 일찍 도착 후 유지 실패(제안하신 taxonomy와 일치).
- 그림·문구를 **"simple-controller achieved response envelope"**로 정정, 비단조 cell에 dominance flag 표기.

---

## ② Terminal band — 0.05 m refinement ✅

**지적**: 0.1 m grid에서 2.6만 성공한 것으로 "razor-thin"은 과함.

**0.05 m 재최적화** (continuation warm + independent restart, angular/axial 자유, v_soft·p_feas·clearance 저장):

| ρT | tier | capture margin | clearance | max v_soft (θ=0.9) |
|---|---|---|---|---|
| 2.55 | **4 safe** | 0.04 | 0.05 | 1.00 |
| 2.60 | **4 safe** | 0.60 | 0.10 | 1.00 |
| 2.65 | **4 safe** | 0.29 | 0.15 | 0.93 |

- ⇒ eligible terminal band는 **razor-thin이 아니라 유한 구간**: 최소 **[2.55, 2.65] (폭 ≥0.1 m)**, 실제 edge는 (2.50, 2.55)와 (2.65, 2.70) 사이.
- **서로 다른 두 기전으로 bounded**: 안쪽(ρ↓)=**clearance 위반**(clr 0.05→0.15, ρ 작을수록 lane에 근접), 바깥쪽(ρ↑)=**hard r_kill cutoff 근방 v_soft 붕괴**(1.00→0.93→θ).
- 지적하신 대로 **바깥 edge는 evaluator의 hard-radius surrogate 산물일 정황이 큽니다** → 별도 surrogate-sensitivity 진단(hard radius vs smooth influence kernel vs A2 avoidance 기반)으로 분리 예정. 안쪽 edge는 물리적 clearance.
- 표현을 *"reoptimization localized the safe terminal set to a finite interval near ρT=r_kill=2.6 m; the outer edge is likely surrogate-driven"*로 정정. (유한 band는 controller 정밀도 요구를 다소 완화합니다.)

---

## ③ Controller 명명 ✅

H/C/P를 **fixed-formation baseline**(hold / analytic contract-and-hold / PD)으로 정정했습니다. **role-agnostic**은 O(short-horizon optimizer)와 향후 MARL(shared policy, role-emergent)에만 사용합니다. baseline의 성공은 emergent cooperation을 증명하지 않고, 실패는 협력 제어 불가능을 뜻하지 않습니다.

---

## ④ 게이트·범위·taxonomy ✅

- **게이트 문구**: "analytic rest-to-rest infeasible 영역에서는 어떤 simple arm도 deployment-safe Tier 4를 달성하지 못했다. Tier 2(링 미형성 crowding 발사)는 일부 나타났으나 analytic 하한의 반례가 아니다."
- **범위**: 현 결과는 동결된 A2·safe cell·firing plane·가속 한계·시험 초기 geometry 하의 **fixed-condition discovery envelope**. distribution-level 승격(경계 cell에서 reset seed·attacker phase·속도·limiter 각도 perturbation)은 Phase 2 초입 과제로 명시.
- **failure taxonomy 추가**: `EARLY_ARRIVAL_OR_HOLD_FAILURE`, `TERMINAL_RELATIVE_VELOCITY`, `ANGULAR_SEAL_FAILURE`, `TARGET_CENTER_TRACKING_ERROR`. 각 success cell에 winner arm 표기.

---

## 다음 (Arm O 착수 전 확인 요청)

필수 3(단조성·band·명명)이 정리됐으므로, **Phase 2의 첫 실질 결과 = Arm O의 controller gap** — slot-free role-agnostic optimizer가 simple-baseline 경계를 analytic 하한 쪽으로 얼마나 당기는지 측정하려 합니다. O가 positive-margin cell에서도 막히면 horizon / action parameterization / angular sealing / terminal velocity / target-center tracking 중 원인을 먼저 진단하고, O가 경계를 당기면 그 safe trajectory를 학습 교사(BC→continuation curriculum→guard 고정 MARL)로 씁니다.

**첨부**: 갱신 브리핑(rev.2), 정정 Figure A(simple-controller achieved envelope + dominance flag + rest-to-rest 하한).
