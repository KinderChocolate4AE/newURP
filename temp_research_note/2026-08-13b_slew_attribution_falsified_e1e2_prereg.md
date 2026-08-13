# 2026-08-13 (3차 세션) — 조준 병목의 **인과 귀속 반증**: ω cap 은 원인이 아니었다 · spine 을 modality gap 으로 격상 · E1/E2 사전등록

세션 daily log (판정형 제목 관례). 산출물 감사 → 미팅 브리핑(docs/82) 작성 중 발견.
정본 = `docs/83_aiming_attribution_correction_prereg.md`.

---

## 1. 발견 — repo 가 이미 갖고 있던 반증

ω_max 3 점 sweep {1.5, 2.0, 3.0} 을 KSAS 추가 실험으로 검토하다가, **더 강한 형태의
반사실이 이미 동결돼 있음**을 발견.

`results/slew_counterfactual.json` (docs/51 §9, 08-05 · `mobility_factorial.py`):

| 항목 | 값 |
|---|---|
| 계약 | `ratified_system()` — 현행 (legacy 아님) |
| 공격자 | A2 jink 0.6 = **T0** |
| 배치 | hold · 고정 finisher |
| 비교 | ω 2.0 → **10⁶**, 동일 CRN, n=500 paired |
| **결과** | **rescued 0 · broken 0 · Δ=0 (CI [0,0])** · FREE_CAPTURE 0.4483→0.4483 |

**조준 각속도 상한을 완전히 제거해도 500 판 중 0 건이 바뀐다.** 운동학 경계 아래
구간에서도 55% 실패가 그대로 남는다 — 그 실패는 조준 rate 때문이 아니다.

⇒ 3 점 sweep 은 **취소**. 돌렸다면 ∞ 조차 null 인 상태에서 더 약한 중복 실험이었고,
결과를 오해석할 위험까지 있었다.

## 2. 정정 — 무엇이 죽고 무엇이 사는가

**죽은 것**: *"finite slew binds first"* — `omega_max=2.0` cap 의 인과 책임.

**과잉 해석 금지**: *"slew dynamics 가 무관하다"* 까지 가면 안 된다. 명령 방향 자체가
틀리면(등속 조준 `p+vτ` vs 실제 `p+vτ+½aτ²`) 무한 authority 도 못 구한다.

**정본 문구**: *"The nominal slew-rate cap is not causally responsible for the observed
T0 boundary; the residual pointing error remains, but its source is unresolved."*

**사는 것**: ψ_med=4.26° 실측 · a\*(ψ) 기하 관계 · 경험적 경계 22.45 · 3 구간 구조.
⇒ **`aiming-limited` 유지, `slew-limited` 금지.**

**ψ 원인 후보 (미해결, 급히 고르지 않음)**: 예측 오차(estimator 문제) / 단거리 원뿔 기하
(d<R_max 면 가용 반경 d·tanθ — a\*=23.8 은 d≈5 m 발사와 수치 구분 불가; terminal geometry
문제) / 한 틱 명령 지연. 이번 반사실이 제거한 것은 **slew saturation 항 하나뿐**.

## 3. 오히려 spine 이 올라감 — modality gap

동결 아티팩트 재분석 (curve_*_reactive, T1, n=2700×2):

| 구간 | net 포획(hold) | 하드킬(intercept) |
|---|---|---|
| baseline-achievable | 0.763 | 0.063 |
| aiming-limited | **0.016** | **0.234** |
| kinematically-infeasible (a≥39.33) | **0.000** | **0.243** |

10 분위로 보면 net 은 a≈31 에서 0 으로 붕괴하는데 하드킬은 78 까지 **24% 고원**을 유지.

**핵심 메시지가 "0.3 초 동안 표적이 움직여 net 밖으로 나간다"(당연)에서 "요격 능력은
남아 있는데 비파괴 포획만 먼저 붕괴한다"(덜 당연)로 격상.** 이 서사는 slew 귀속이
죽어도 전혀 안 죽는다 — 오히려 특정 controller 기전 의존성이 사라져 더 견고하다.

**신규 spine (비준)**: *"We characterize when physical interception remains possible while
delayed single-shot non-destructive capture has already collapsed, and identify deployment
latency and residual aiming geometry as the two principal terminal constraints."*

**단 caveat**: 현재 24.3% 는 intercept arm 에서 net 이 먼저 성공하면 하드킬 기회가
censoring 되는 **경쟁위험** 때문에 하한이다. → E2 필요.

## 4. 사전등록 2 건 (docs/83, 판정규칙 결과 열람 전 동결)

**E1 — T1 ω=∞ paired 반사실** (n=500×2, 곡선 한 arm 의 0.37 배). T0 null 로부터 T1 을
추정하지 않는다 (route 반응으로 궤적 family 가 다름 → v⊥↑ → ω_req↑ → cap 이 비로소
구속할 수 있음). 판정: rescued=0 → slew 인과 표현 완전 제거 + Ω 를 Map B 로 이관 /
rescued≥1 且 CI 가 0 제외 → **T1 반응성이 slew-민감 채널을 활성화** (Case B 의
0.83→0.763 에 기전을 붙임) / CI 가 0 포함 → INCONCLUSIVE, 격상 금지.
**E1b 동반 진단**: 두 팔에서 ψ 분포 재측정 → ψ 가 유지되면 actuator 가 아니라 명령/예측
측으로 원인 범위 축소 (강한 소득).

**E2 — 전용 hard-kill pursuit baseline** (confirmatory 2,700 + dev 200). 물리 전부 고정
(T1·CRN·r_kill 0.75·p_kill 1.0·접촉 물리·spawn·계약), **바뀌는 것은 controller objective
하나 + net 비활성화**(경쟁위험 제거). 튜닝은 dev seed 대역에서만, 기준 하나 사전 선언,
게인 고정 후 confirmatory 진입, **결과 보고 재튜닝 금지**. 80% 든 25% 든 그대로 쓴다 —
그래야 gap 이 제조된 것이 아니다.

## 5. B2 함의 (기록만, 결정 아님)

docs/45 §3.1 실측: hold 는 v⊥ 0.44 · ω 구속 **0.0%**, ring 은 v⊥ **7.27** · 구속 **44.8%**.
⇒ **Ω = ω·τ 는 Map A(종말)의 활성 축이 아니라 Map B(shaping)의 축.** 조준 권한은 단독
종말 문제에선 비구속이고, limiter 가 v⊥ 를 키우는 순간 지배 좌표가 된다.

⇒ B2 shaping objective 는 단항이 아니다:
`J_shape = J_escape_compression − λ·J_aiming_burden` (burden 후보: |v⊥|, LOS rate, ψ_pred).
**지금 reward 에 넣지 않는다** — B2 에서 기전 endpoint 로 먼저 측정 (T_lead↑ 시 escape
certificate·v⊥·LOS rate·최종 C_net 을 동시에).
**B2 첫 capability 축 = μ = a_lim/a_att** (현 파일럿 0.4 단일점): 결과가 NO 일 때 "기전
부재" 와 "limiter 권한 부족" 을 구분하려면 필수. Gate 7 ①-B1 도 엄밀히는
*"at the registered limiter authority (μ=0.4)"* 한정어 필요.

## 6. 반영 완료 (코드 수정 0, 실험 실행 0)

| 파일 | 조치 |
|---|---|
| `docs/83_aiming_attribution_correction_prereg.md` | 신규 — 정정 + E1/E2 사전등록 정본 |
| `docs/45_slew_boundary.md` | 상단 append-only DOWNGRADE 포인터 (원문 보존, 단독 인용 방지) |
| `artifacts/audits/claim_registry.tsv` | **C031** 추가 (DOWNGRADED, 14 열 정합 확인) |
| `docs/82_advisor_meeting_brief.md` | spine 교체 · 명제 (b) 하향 + (b′) modality gap 신설 · 합의항목 A0 신설 · 리스크 0 번 신설 |
| `docs/81_post_audit_workflow.md` | **P1 개정** — 실험 2 건 추가, 순수 기록 단계 아님을 명시 |

## 7. 다음 트리거

- **E1·E2 실행** (승인 필요 — P1 범위 확대이므로). 그 뒤 문서 정정 → 기록 4 건 → P1 freeze.
- 미팅 시 최우선 안건 = docs/82 §5-A0 (spine 교체 + 기전 정정 승인).
- 커밋 미실시. untracked: docs/83 · docs/82 · docs/81(수정) · docs/45(수정) · registry(수정) · 본 로그.

**메타 교훈**: 08-01 주장과 08-05 반증이 **8 일간 연결되지 않았다.** 개별 실험은 전부
정직하게 기록됐는데 *상호 참조*가 없었다. 산출물 감사가 아니었으면 반증된 인과 주장이
그대로 인쇄될 뻔했다 — docs/50:183 좀비 사례와 같은 구조. claim registry 의 
"Known counterevidence" 열이 이 역할을 하도록 설계돼 있었으나, 신규 반사실이 기존 행에
역방향으로 연결되지 않았다. **정정 규율: 새 반사실을 등록할 때 그것이 반증하는 기존
claim 행을 반드시 역참조한다.**
