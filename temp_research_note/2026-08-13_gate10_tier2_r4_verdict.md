# 2026-08-13 — 게이트 10 Tier 2 r4 판정: **core-only 불충분 확정** — cone shape 과 eta 는 GOVERNING

계약 = `docs/78` r4 (§C-4, 재실행 전 봉인). tranche = ep 10..19, CAP 300.
상태수 chi 0.4/0.8/1.6 = 145/238/245. 판정 어휘 = r4 4종.

## 1. 결과 (두 arm f∈{0.8,1.25}, bar med 0.02 / p95 0.05, 문턱 n_inf ≥ 50)

| chi | group | class | n_inf (0.8 / 1.25) | drop (0.8 / 1.25) | med V0 | p95 V0 | sign V0 (0.8→1.25) | 판정 |
|---|---|---|---|---|---|---|---|---|
| 0.4 | **shape** | P | 61 / 59 | 0 / 0 | 0.144 / 0.153 | 0.96 / 0.80 | +0.31 → −0.63 | **FAIL** |
| 0.8 | **shape** | P | 101 / 104 | 0 / 0 | 0.130 / 0.129 | 0.55 / 0.77 | +0.13 → −0.48 | **FAIL** |
| 1.6 | **shape** | P | 130 / 138 | 0 / 0 | 0.030 / 0.034 | 0.11 / 0.14 | −0.02 → −0.17 | **FAIL** |
| 0.4 | eta | Z | 70 / **29** | 11 / **96** | 0.378 / 0.434 | 0.94 / 0.92 | +0.60 → −0.59 | INCONCLUSIVE (단측) |
| 0.8 | **eta** | Z | 110 / 52 | 13 / 101 | 0.228 / 0.212 | 0.51 / 0.53 | +0.49 → −0.58 | **FAIL** |
| 1.6 | **eta** | Z | 149 / 69 | 13 / 108 | 0.032 / 0.027 | 0.12 / 0.11 | +0.49 → −0.57 | **FAIL** |

## 2. 판정 (r4 어휘)

- **shape (P) = GOVERNING.** ρ_eff = R_max·tan(α) 를 **exact assert 로 고정**하고
  core (chi, kappa, mu, N) 를 기계적으로 동일하게 둔 상태에서 cone 종횡비만 바꿔도
  med|ΔV0| 이 bar 의 **1.5~7배** (0.030~0.153), 탈락 0, n_inf 59~138 로 전 chi 에서
  문턱 충족. 부호는 두 arm 이 단조 반대 (+ → −) = 계통적 의존.
  ⇒ **"cone shape is an independent governing coordinate beyond capture scale."**
  (r3 의 alpha/lam FAIL 은 core 이동 confound 였으나, scale 을 고정하고 shape 만
  분리해도 의존성이 **남았다** — 이것이 r4 의 핵심 소득.)
- **eta (Z) = GOVERNING** (chi 0.8, 1.6 에서 확정; chi 0.4 은 단측).
  med|ΔV0| 0.027~0.434, 부호 단조 반대. ⇒ **missing state coordinate**:
  동일 core 를 유지한 채 ‖v‖ 만 바꿔도 Q 가 체계적으로 변한다.
  **정직 caveat**: ×1.25 arm 은 96~108 건이 물리 상한(v_max=28.5, sprint cap)에서
  탈락 — 설계 오류가 아니라 **정당한 censoring** 이나 상한 근처 상태가 계통적으로
  빠진다. chi 0.4 은 이 때문에 ×1.25 n_inf=29 < 50 이라 등록 규칙상 INCONCLUSIVE
  (유효한 ×0.8 arm 은 n=70, med 0.378 로 bar 의 19배 — 단측 증거는 강하다).
  **결과를 본 뒤 규칙을 바꾸지 않는다.**
- (r3 승계) sig_as = **GOVERNING (U_cheap 한정)** · nu, sig_sb =
  **INACTIVE·NON-IDENTIFIABLE** · alpha, lam = **INVALID·CONFOUNDED** (shape 로 대체) ·
  sig_dt = 게이트 11 소관.

## 3. chi 의존 구조 (boundary-local 아님 — 오히려 역방향)

효과 크기가 chi 에 **단조 감소**한다: shape med 0.144 → 0.130 → 0.030,
eta med 0.378 → 0.228 → 0.032. 즉 **chi 가 클수록 conditioning 민감도가 사라진다.**
해석: high-chi 에서는 이미 대부분 상태가 infeasible 쪽으로 붕괴해 있어(게이트 7/B1)
어떤 좌표를 흔들어도 Q 가 바뀔 여지가 적다 — **floor 효과와 정합(consistent with)**.
단 **"floor 효과를 입증했다" 고 쓰지 않는다** (baseline V_0 대 교란 크기의 관계를
기존 데이터로 diagnostic plot 할 수는 있으나 별도 캠페인은 불필요).
확실한 것은 이 결과가 "경계 근방에서만 민감"(boundary-local secondary coordinate)
**은 아니라는 것** — 방향이 반대다.

## 4. 게이트 10 최종 답 — 성분별 sufficient coordinate set

목표 진술(r4 §C-4)대로 "각 성분 Q 의 충분좌표"로 답한다:

```
C_{V_0}   : core (chi, kappa, mu) + **cone shape** + **eta**            (sig_as 무관)
C_{L_1,L_N}: 위와 같음 + T̃_reach = T_reach/tau (미등록 상태좌표, Π 노트 §D)
C_{U_cheap}: core + **sig_as** (= R_NK)                                  (r3)
```

⇒ **core-only 매개변수화는 불충분함이 확정**되었다.

**정본 표현 (2026-08-13 정정 — "최소 sufficient set" 표현 금지)**:
> The conditional certificate requires **at least** (chi, kappa, mu, N, cone shape,
> eta) **over the tested perturbations**; additional component-specific coordinates
> remain (σ_as for U_cheap; T̃_reach for L_1/L_N), and unregistered Π-groups stay
> frozen at nominal.

"최소" 라고 부를 수 없는 이유: 미등록 Π 가 nominal 동결 상태이고, T̃_reach 처럼
구조적으로 들어가지만 아직 sweep 하지 않은 좌표가 있다.

### 4.1 성분별 표 (게이트 10 의 최종 산출물 — 단일 PASS/FAIL 대체)

| Q 성분 | 확인된 추가 governing | inactive / non-identifiable | unresolved / scope |
|---|---|---|---|
| V_0 | **cone shape, eta** | — | 미등록 동결 Π |
| L_1 | (추가 clean governing 미확정) | nu | T̃_reach · shape/eta 의 성분별 효과 |
| L_N | (추가 clean governing 미확정) | nu, sig_sb (tested regime) | T̃_reach |
| U_cheap | **sig_as (= R_NK)** | — | 기타 frozen geometry |

### 4.2 eta support 보고 의무 (정정)

+25% arm 의 estimand 는 전체 상태분포가 아니라 **support 제한 효과**다:
`Z_+ = {z : 1.25‖v(z)‖ ≤ 28.5}` ⇔ `‖v‖ ≤ 22.8`. 따라서 eta 결과에는 항상
`n_base / n_− / n_+` 를 병기한다 (본 tranche: 145/134/49 · 238/225/137 ·
245/232/137). `n_common = |Z_− ∩ Z_+|` 는 **해석용 diagnostic** 이며 판정 기준이
아니다 (본 실행은 미저장 — Z_+ ⊂ Z_− 가 근사 성립하므로 n_+ 가 하한).
정본 문장:
> η is governing **in the tested physically admissible support** at chi = 0.8 and
> 1.6; the positive perturbation at chi = 0.4 remains unresolved because of
> upper-speed censoring.

"η 는 전체 map 에서 governing" 이라는 무제한 일반화 금지.

## 5. claim 규율 (갱신 — 이전 금지 유지 + 신규)

- **금지 확정**: *"C 는 core (chi,kappa,mu,N) 의 함수"* — 반증됨.
- **chi 승격**: *"chi is a governing similarity coordinate"* 는 여전히 가능하지만
  **"유일하거나 충분한" 이 아님**을 반드시 병기. 정확한 형태 =
  *"chi is one of several governing coordinates of the conditional capture-viability
  map; core-only collapse is rejected (cone shape and eta are governing)."*
- 지도 보고 시 cone shape·eta 는 **nominal 고정 조건**으로 명시 (scoped map).
- 상사성 결론(Tier 1)은 영향 없음 — L/T 상사불변은 bit-exact 로 유지되며,
  이번 결과는 "무차원 좌표계의 **차원(개수)**" 에 대한 것이지 상사성 자체가 아니다.

## 6. 다음

게이트 10 종료. → **게이트 11 (closed-loop scripted system similarity)**:
`fwd_gain` explicit 승격 → S-L 회귀 · S-T 재falsify. 그 뒤 T_lead/B2.
별도 사전등록 대기: nu 재시험 (τ-지평선 regime) · T̃_reach 축 sweep ·
eta 의 상한 censoring 을 피하는 대안 교란 설계.

산출물: `results/phase3/gate10_tier2r4_chi{04,08,16}.json` (+ .log).
