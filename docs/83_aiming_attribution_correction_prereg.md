# 83 — 조준 병목의 **인과 귀속 정정** + E1/E2 사전등록 (동결본)

- **일자**: 2026-08-13 (3차 세션) · 성격: **claim 정정 + 신규 실험 2건 사전등록 (결과 열람 전 동결)**
- **트리거**: 산출물 감사 중 `results/slew_counterfactual.json`(docs/51 §9, 08-05)이 docs/45 §9(08-01)의 인과 귀속을 반증함을 발견. 두 문서가 지금까지 연결된 적 없음.
- **규율**: docs/45 의 당시 결론은 **보존**한다 (역사 삭제 금지). 본 문서가 그 위에 DOWNGRADE 를 얹는다.

---

## 0. 한 줄 판정

> **T0 hold 구성에서 `attitude.omega_max = 2.0` 이라는 actuator slew cap 은 관측된 실질 경계의 원인이 아니다.** 잔여 조준 오차 ψ 는 여전히 관측되지만(4.26°), **그 원인은 미해결**이다. 따라서 "finite slew binds first" 는 철회하고, "residual aiming error" 로 낮춘다.

---

## 1. 반증 증거 (동결 아티팩트, 신규 실험 아님)

`shepherd/scripts/mobility_factorial.py` → `results/slew_counterfactual.json`.

**설정이 KSAS hold 곡선과 동일하다는 점이 핵심이다**:

| 항목 | 값 | 근거 |
|---|---|---|
| 계약 | `ratified_system()` — **현행 계약** (legacy 아님) | mobility_factorial.py:68 |
| 공격자 | `AttackerSpec(level="A2", jink_amp=0.6, seed=0)` = **T0** | :70 |
| limiter | `hold` | :76, :155 |
| finisher | 고정 (mobility = 0.0) | :181 |
| 비교 | ω = 2.0 → **10⁶** (`SLEW_UNLIMITED`), 동일 CRN | :181-182 |
| n | 500 paired | :218 |

결과 (`paired["고정·ω2.0 -> 고정·ω∞"][ALL]`):

```
fixed_k = 91   →   arm_k = 91
diff = 0.0,  diff_ci95 = [0.0, 0.0]
rescued_n01 = 0,   broken_n10 = 0
```

구간별: SHAPING_NEEDED n=297 에서 0.0 → 0.0 · FREE_CAPTURE n=203 에서 0.4483 → 0.4483 (소수점 일치).

**조준 각속도 상한을 완전히 제거해도 500 판 중 라벨이 바뀐 에피소드가 양방향 모두 0 건이다.** 운동학 경계 아래 구간(FREE_CAPTURE)에서도 55% 의 실패가 그대로 남는다 — 그 실패는 조준 rate 때문이 아니다.

## 2. 정확히 무엇이 배제되고 무엇이 남는가

### 배제된 것 (반증)

> ~~"유한 조준 각속도(ω_max = 2.0)가 운동학 경계보다 먼저 구속한다."~~

### 배제되지 **않은** 것 (과잉 해석 금지)

**"slew-rate dynamics 가 무관하다" 고 말하면 과하다.** cap 을 제거해도 컨트롤러가 애초에 틀린 지향을 명령하고 있다면 무한 actuator authority 는 아무것도 구하지 못한다. 예: 명령이 `p + v·τ` (등속 예측)인데 실제 표적은 `p + v·τ + ½aτ²` 에 있다면, actuator 가 명령을 무한히 빨리 따라가도 **명령 자체가 틀렸다**.

### 정본 정정 문구

> **The nominal slew-rate cap is not causally responsible for the observed T0 boundary; the residual pointing error remains, but its source is unresolved.**

### 살아남는 관측

- ψ_med = 4.26° > 0 (실측, slew_audit)
- a\*(ψ) = 2d(tanθ − ψ)/τ² = 25.75 가 경험적 붕괴(22.45 / 23.82)와 대략 일치
- 기하 관계 자체는 유효: 조준이 ψ 만큼 틀어지면 쓸 수 있는 반각이 (θ − ψ) 로 줄어든다 — **원인과 무관하게 참**

즉 **`aiming-limited` 는 살리고 `slew-limited` 는 버린다.**

## 3. 잔여 ψ 의 원인 후보 (미해결 — 급히 고르지 않는다)

```
psi_residual = f(prediction error, command/sample delay, fire geometry, slew saturation, ...)
```

이번 반사실이 제거한 것은 마지막 항(**slew saturation 의 outcome 기여 ≈ 0, T0 한정**) 하나뿐이다. 남은 주요 후보 둘은 **논문의 의미가 서로 다르다**:

| 후보 | 내용 | 성격 |
|---|---|---|
| **Prediction error** | 등속 조준 `p + v·τ` 가 가속하는 표적에 대해 틀림 | **estimator / guidance 문제** |
| **Short-range cone geometry** | 실제 발사거리 d < R_max 이면 가용 횡반경이 `d·tanθ` 라 공칭 ρ=1.77 을 다 못 씀. a\*=23.8 은 d≈5 m 발사와 수치적으로 구분 불가 | **terminal geometry 문제** |

(부가 후보: 한 틱 명령 지연 — ω_req·dt 규모.)

**따라서 현 시점 최대 허용 진술**:

> observed residual aiming error predicts an earlier practical boundary, **while its causal source remains unresolved.**

---

## 4. E1 사전등록 — T1 ω=∞ paired counterfactual

**목적**: 인과 귀속 판정 **단 하나**. (기존 선언축 `omega_max {1.5, 2.0, 3.0}` **3 점 sweep 은 취소한다** — ∞ 조차 null 인 상태에서 3.0 을 도는 것은 더 약한 형태의 중복 실험이고, 1.5/3.0 은 문헌 브라켓이 아니라 선언이라 "왜 그 범위인가" 에 답이 없다.)

**가설**: `H: ω_max = 2 → ∞` 가 **T1** outcome 을 변화시키는가. T0 null 로부터 T1 을 추정하지 않는다 — T1 은 route 반응으로 궤적 family 가 다르고, v⊥ 가 커지면 ω_req 가 커져 cap 이 비로소 구속할 수 있다.

**설정 (T0 반사실과 단일축만 다름)**:

| 항목 | 값 |
|---|---|
| 스크립트 | `mobility_factorial.py` (기존), mobility = 0.0 |
| 공격자 | `AttackerSpec(level="A2", jink_amp=0.6, route_gain=0.5, sense_range=30.0, seed=0)` = **T1** |
| 팔 | ω = 2.0 vs `SLEW_UNLIMITED`, 동일 CRN |
| n | 500 paired, seed0 = 0 |
| 나머지 | `ratified_system()`, hold, M4 운용점 — 전부 T0 반사실과 동일 |

**1차 지표**: `rescued_n01`, `broken_n10`, Δ 포획률 + CI95 (paired).

**판정 규칙 (결과 열람 전 동결)**:

| 결과 | 판정 | 조치 |
|---|---|---|
| `rescued_n01 = 0` | slew-cap 인과 귀속 **T1 에서도 기각** | finite-slew 인과 표현 KSAS 에서 완전 제거. Ω = ω·τ 를 Map B 축으로 이관 |
| `rescued_n01 ≥ 1` **且** Δ CI 가 0 제외 | **T1 반응성이 slew-민감 실패 채널을 활성화** | 구간별(EASY/BAND_AIM/SHAPING) 분해 보고. Case B 의 0.83→0.763 에 기전을 붙임 |
| `rescued_n01 ≥ 1` **但** CI 가 0 포함 | INCONCLUSIVE | 그대로 보고. 문구 격상 금지 |

**E1b 동반 진단 (같은 런, 필수)**: 두 팔에서 `slew_audit` 로 ψ 분포를 재측정한다.

- ω=∞ 에서 **ψ_med 가 4.26° 근방으로 유지** → 잔여 오차는 actuator 가 아니라 **명령/예측** 측 → §3 후보를 prediction error / geometry 로 좁힘 (강한 소득)
- ω=∞ 에서 **ψ_med → 0 인데 outcome 은 불변** → ψ 는 실재하되 **경계를 지배하지 않음** → a\*(ψ) 일치가 우연일 가능성 → aiming 서사 자체를 하향해야 함

**두 결과 모두 보고 대상이다. 어느 쪽도 "실패" 가 아니다.**

**비용**: 1,000 판 (곡선 한 arm 2,700 판의 약 0.37 배). 취소한 3 점 sweep(5,400 판)보다 싸다.

## 5. E2 사전등록 — 전용 물리요격(hard-kill) baseline

**목적**: modality gap `C_net ⊊ C_physical` 의 상단 곡선을 **경쟁위험 없이** 측정. 현재 intercept arm 의 0.24 는 net 이 먼저 성공하면 하드킬 기회가 censoring 되므로 **하한**이다.

**엄격 고정 (변경 금지)**: T1 공격자 · 동일 CRN · 동일 기체 가속/속도 비율 · `r_kill = 0.75` · `p_kill = 1.0` · 동일 접촉 물리 · 동일 spawn · `ratified_system()`.

**바뀌는 것은 controller objective 하나뿐**: 물리 접촉/요격 최대화. **net 비활성화** (`fire_mode="never"`) — 이것이 경쟁위험을 제거하는 장치다.

**컨트롤러**: 접촉 지향 scripted pursuit (lead-pursuit / PN 계열). 설계는 결과 열람 전 고정.

**튜닝 프로토콜 (제조 방지의 핵심)**:
1. 게인 튜닝은 **dev seed 대역에서만** 수행 (confirmatory 대역 0..2699 과 겹치지 않는 별도 band, 예: 20000..20199).
2. 튜닝 기준은 **하나만** 사전 선언 (접촉률 또는 최소 근접거리 중 택1 — 실행 시 명시).
3. 게인을 한 번 고정한 뒤 confirmatory 곡선에 진입. **confirmatory 결과를 본 뒤 재튜닝 금지.**

**1차 지표**: a_att 10 분위별 `P_HK^dedicated` + Wilson CI. Fig 1 의 상단 곡선.

**해석 계약**: 이 값은 물리 요격 능력의 **constructive lower bound** 이지 최적값이 아니다. **"보기 좋은 80%" 를 목표로 하지 않는다** — 80% 면 80%, 45% 면 45%, 25% 면 25% 를 그대로 쓴다. 그래야 modality gap 이 제조된 것이 아니다.

**비용**: confirmatory 2,700 판 + dev 200 판 ≈ 곡선 한 arm.

---

## 6. 용어·문구 규율 (즉시 발효)

| 금지 | 허용 |
|---|---|
| "finite slew binds first" / "유한 조준 각속도가 먼저 구속" | "residual aiming error 가 더 이른 실질 경계와 결부된다" |
| "slew-limited" 구간명 | **"aiming-limited"** 또는 "pointing-limited" (source unresolved 병기) |
| "조준 각속도 경계를 검증했다" | "관측된 잔여 조준 오차가 더 이른 경계를 예측하며, 그 인과 원인은 미해결" |
| "slew dynamics 는 무관하다" | "**nominal slew-rate cap** 은 T0 hold 결과를 설명하지 못한다" (cap 한정) |
| spine 에 `τ_deploy × 겨냥 각속도` | spine 에 **`deployment latency + residual aiming geometry`** |

**KSAS 신규 spine 문장 (비준)**:

> We characterize when physical interception remains possible while delayed single-shot non-destructive capture has already collapsed, and identify **deployment latency and residual aiming geometry** as the two principal terminal constraints observed in the tested configuration.

국문:

> 물리적 요격이 여전히 가능한 상태에서 지연을 갖는 단발 비파괴 포획은 이미 붕괴하는 영역을 규명하고, 검정한 구성에서 관측된 두 종말 제약으로 **전개 지연**과 **잔여 조준 기하**를 제시한다.

## 7. 문서 파급 + 일정 영향

| 문서 | 조치 |
|---|---|
| `docs/45` §0/§9 | 상단에 append-only DOWNGRADE 포인터 추가 (원문 보존). 단독 인용 방지 — docs/50:183 좀비 사례 재발 방지 |
| `artifacts/audits/claim_registry.tsv` | **C031** 신규 행: 인과 귀속 DOWNGRADED |
| `docs/82` | spine 문장 교체 + 명제 (b) 행 갱신 + 합의 항목 추가 |
| `docs/81` | **P1 개정**: KSAS 잔여가 기록 4 건 → 기록 4 건 + **E1·E2 실험 2 건** + 문서 정정 3 건 |

**일정 영향을 정직하게 적는다**: docs/81 P1 은 "동결 직전, 잔여 전부 기록 수준" 이었다. 본 정정으로 **KSAS 제출 전 실험 2 건이 추가**되며, P1 이 순수 기록 단계가 아니게 된다. 이는 감사 §G 의 범위 확대이고, 승인 주체는 사용자/지도교수다.

## 8. B2 함의 (여기서 결정하지 않고 기록만)

**Ω = ω_max·τ 는 Map A(종말 modality)의 활성 축이 아니라 Map B(state-shaping)의 축이다.** 근거는 docs/45 §3.1 실측:

| 배치 | v⊥ 중앙 | ω_req > 2.0 구속률 |
|---|---|---|
| hold | 0.44 | **0.0%** |
| **ring** | **7.27** | **44.8%** |

즉 조준 권한은 단독 종말 문제에서는 비구속이고, **limiter 가 개입해 v⊥ 를 키우는 순간 지배 좌표가 된다.** 이것이 docs/45 §4 의 (i)/(ii) 상쇄 — 도달집합 압축(이득) vs 조준 부담 증가(손해) — 의 물리적 실체다.

따라서 B2 의 shaping objective 는 단항이 아니다:

```
J_shape = J_escape_compression  −  λ · J_aiming_burden
                (good)                     (bad)
aiming burden 후보: |v_perp| · |LOS rate| · psi_predicted
```

**단, 지금 reward 에 넣지 않는다** — B2 에서 **기전 endpoint 로 먼저 측정**한다: T_lead 를 늘렸을 때 (a) escape certificate 개선? (b) v⊥ 악화? (c) LOS rate 악화? (d) 최종 C_net 순효과? 를 **동시에** 본다.

**B2 첫 capability 축 = μ = a_lim/a_att** (현 파일럿 0.4 단일점). 결과가 NO 일 때 "기전이 없다" 와 "limiter 권한이 애초에 부족했다" 를 구분하려면 필수. Gate 7 ①-B1 도 엄밀히는 *"at the registered limiter authority (μ=0.4)"* 한정어가 필요하다.

---

## 9. 실행 순서 (개정)

```
E1 (T1 omega=inf 반사실)  ─┐
E2 (전용 HK pursuit)      ─┴→ 문서 정정 4곳 → KSAS 기록 4건 → P1 freeze → 제출
                                                    ↓
                                        R1~R3 → arXiv v0
                                                    ↓
                                    B2: mu 먼저 → escape↔aiming trade-off 측정
                                                    ↓
                                    필요 시 omega_max 를 B2 capability 축으로 재도입
```

*연관: 반증 아티팩트 = results/slew_counterfactual.json · 원 주장 = docs/45 §9 · 반사실 출처 = docs/51 §9 · 순서 규율 = docs/81 · 미팅 브리핑 = docs/82 · 감사 = artifacts/audits/environment_numeric_audit_2026-08-13.md*
