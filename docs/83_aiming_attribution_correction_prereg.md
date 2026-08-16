# 83 — 조준 병목의 **인과 귀속 정정** + E1/E2 사전등록 (동결본)

- **일자**: 2026-08-13 (3차 세션) · 성격: **claim 정정 + 신규 실험 2건 사전등록 (결과 열람 전 동결)**

> **▣ PREREG FREEZE STAMP** (내용 무변경 — 아래 §0~§9 는 freeze 커밋 그대로)
>
> | 항목 | 값 |
> |---|---|
> | **prereg freeze commit** | `eea71806828fed02e9670e4fcab2c8d0099c906f` (`eea7180`) |
> | harness code revision (freeze 시점) | `3087615` — `mobility_factorial.py` · `attacker_ladder.py` |
> | 직전 science commit | `43acc39` (T1 rerun Case B) |
>
> 이 블록은 freeze 직후 **provenance 스탬프로만** 추가됐다 (가설·설정·판정규칙 무수정).
> E1/E2 결과가 나온 뒤 사전등록이 작성된 것처럼 보이지 않도록, freeze 커밋이 결과
> 커밋보다 **앞선다는 사실을 git object 로 고정**하는 것이 목적이다.
>
> **결과 아티팩트에 반드시 기록할 manifest 필드** (감사 §G-② 재발 방지 — reactive
> rerun JSON 이 route_gain/sense_range 를 안 남겨 파일명으로만 T0/T1 을 구분해야 했던
> 사고의 직접 대응):
> ```
> prereg_commit · execution_commit · code_revision
> threat_class (T0/T1) · level · jink_amp · route_gain · sense_range
> limiter_mode · contract (ratified_system flags) · finisher mobility
> omega_max (2.0 / 1e6) · n · seed0 · CRN episode range
> rho · tau · cone(range_max, half_angle) · r_kill · p_kill · dt · episode_len
> ```
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

---

# 10. 개정 A1 — E2 재설계: sham-net counterfactual + R3 계약

**개정 시점: 2026-08-13, E1 결과 열람 전 · E2 미실행.** 본 개정은 researcher degree of
freedom 을 **줄이는(tightening)** 방향이다 — 자유 게인을 0 으로 확정하고, 임의
equivalence threshold 를 제거하며, 증거 등급을 낮춘다. 느슨하게 하는 개정이 아니다.

## 10.1 Blocker 해소 — capture 는 순수 terminal label 이다 (trace 완료)

`fire_mode="never"` 를 primary 로 두려던 §5 초안은 **폐기**한다. 이유: commit 은
dodge ON **+ jink OFF + route 유지**의 묶음이므로(감사 §7 타임라인), net 을 끄면
"순수 dodge 효과"가 아니라 commit-conditioned 응답 전체가 사라진다. 부호조차 예단
불가.

대신 **sham-net** 이 필요하다. 구현 가능성의 blocker 는 "capture 가 inner env 에서
neutralizing state mutation 을 일으키는가" 였고, trace 결과 **일으키지 않는다**:

| 단계 | env.py | 성격 |
|---|---|---|
| fire | `_pending_capture = (not boxed_in) and v_shot_worst >= 1.0` (:320) | bool 동결 |
| FSM | `step_fsm(..., capture=_pending_capture)` (:312) | `last_capture` 기록 |
| lock 종료 | `captured = resolved and fsm.last_capture is True` (:324) | **순수 파생 bool** |
| 종료 | `terminated_flag = captured or penetrated or spent_fail` (:357) | 플래그 |
| 정리 | `if terminated_flag or truncated_flag: self.agents = []` (:398) | 에이전트 목록 |

**공격자 neutralization·제거·freeze·위치 변경 없음.** 백엔드 물리 적분은 종료 판정
**이전**(:346-350)에 끝나므로 capture 는 사후 라벨로만 작용한다. 상태 변이는 `terms`
와 `self.agents=[]` 둘뿐이고, 후자는 **기존 R2 가 이미 되돌리는 그것**이다
(`inner.agents = list(inner.possible_agents)`, env_sys.py:335).

**추가 소득**: sham 억제 다음 스텝에서 `resolved` 가 False → `captured=False` 인데
FSM 은 SPENT 이므로 `spent_fail=True` 가 되어 **이미 비준된 R2 억제 조건에 정확히
걸린다.** ⇒ 신규 코드는 capture 가 resolve 되는 **한 스텝**만 처리하면 되고 이후는
기존 계약이 담당한다. 즉 `capture_terminates=False` 는 비준된 `miss_terminates=False`
의 구조적 대칭이다.

## 10.2 R3 계약 (env_sys.py — 동결 대상 아님, docs/54 R1/R2 전례)

**기본값 `capture_terminates = True`** — 기존 모든 science path 의미 불변.

`False` 일 때, capture 가 resolve 되는 스텝에 한해:

| 보존 | 억제 |
|---|---|
| commit 발생·타이밍 | capture 로 인한 **종료** |
| commit-conditioned attacker 응답 (dodge ON / jink OFF / route 유지) | capture 의 **neutralizing 효과** |
| finisher **SPENT / K=0 유지** (READY 복귀 금지) | — |
| hard-kill · penetration · truncation 종료 | — |
| RNG stream (불필요한 draw 추가 금지) | — |

조건은 `captured and not penetrated` (동시 발생 시 penetration 종료 우선).
기록 의무: `would_capture=True` · `sham_capture_step`.

**의미 정의**: *A would-be successful net capture is recorded, but its neutralizing
state transition and episode termination are suppressed; all commit-conditioned
attacker dynamics and all non-net terminal channels remain unchanged.*

## 10.3 E2 3-arm 재정의 (증거 등급 분리)

| Arm | 설정 | 증거 등급 |
|---|---|---|
| **E2-A** | intercept + net ON | **FROZEN HISTORICAL / DEPLOYED-SYSTEM OBSERVATION** — 이미 결과를 봤다(0.243). **confirmatory 로 재명명 금지** |
| **E2-B** | intercept + commit ON + attacker 응답 ON + **capture_terminates=False** | **PRIMARY PROSPECTIVE COUNTERFACTUAL** (신규 confirmatory) |
| **E2-C** | intercept + fire/commit never | OPTIONAL, arXiv diagnostic — commit-응답 자체를 제거 |

분해: `B−A` = competing-risk 제거 · `C−B` = commit-conditioned 응답 효과.
비용상 하나만 돌리면 **B**.

표기 정본: *"a previously frozen deployed-system arm paired with a prospectively
registered net-disabled counterfactual"* — 전체를 "preregistered two-arm experiment"
라고 부르지 않는다.

## 10.4 컨트롤러 — 자유 게인 0 (§5 튜닝 프로토콜 대체)

`intercept_limiter` (mission_rollout.py:114) 는 이미 해석적 lead-collision 유도이고
**자유 게인이 없다**: `a_max` = 능력비 고정, `margin` = `r_kill + 0.5(a_lim−a_att)τ_kill²`
(docs/29 §2.1 유도), `t_lead` = 해석해. ⇒ **§5 의 dev-seed 튜닝 프로토콜은 불필요하며
수행하지 않는다.** "hard-kill 곡선을 높이려 튜닝했다" 는 researcher DOF 가 구조적으로
소멸한다 (§5 의 의도를 더 강하게 달성).

정본 명칭: **gain-free constant-bearing intercept baseline under the registered
vehicle limits.** `margin` 유도식은 manifest 에 명시한다.

## 10.5 Estimand + 구간별 해석 (결과 전 고정)

**임의 equivalence threshold 를 만들지 않는다.** 사전등록 estimand:

```
Delta_comp = P_HK^B − P_HK^A        (paired, CRN)
보고: paired difference · CI95 · 구간별 분해 (그대로)
```

| 구간 | net 성공 | E2-B 의 역할 |
|---|---|---|
| low-χ (baseline-achievable) | 0.763 | **정보 최대** — severe competing risk. A 의 HK 0.063 을 "물리 요격 능력" 으로 읽으면 안 되는 이유를 직접 해소 |
| aiming-limited | 0.016 | competition 작지만 존재. paired difference 그대로 보고 |
| high-χ | **0/1598** | **effect estimation 영역이 아니라 implementation invariance control** |

**high-χ 는 exact wiring oracle**: capture 가 한 번도 발생하지 않으므로 intervention
이 활성화되지 않는다 ⇒ 같은 CRN 에서 **A 와 B 가 bit-exact** 여야 한다 (states ·
actions · commit steps · hard-kill steps · termination labels). `Δ_high ≠ 0` 은
과학적 결과가 아니라 **R3 구현 실패**다.

⇒ modality-gap 의 high-χ 주장은 E2-B 없이 이미 성립한다(`P_net=0`, `P_HK^A=0.243`).
E2-B 의 본체 기여는 **low/mid-χ 의 물리 요격 곡선을 competing risk 없이 복원**하는 것.

**결과 명명 규율**: E2-B 의 P_HK 를 "true physical interception probability" 라고
부르지 않는다. 정본 = *physical-interception incidence under matched
commit-conditioned threat response with net capture removed as a competing terminal
event.*

## 10.6 R3 회귀 게이트 — 4/4 통과 전 E2-B 실행 금지

| 게이트 | 내용 |
|---|---|
| **R3-A** default regression | `capture_terminates=True` 에서 과거 고정 seed 결과와 **bit-exact**. 최우선 |
| **R3-B** high-χ no-op invariance | capture 미발생 등록 T1 상태에서 A=B **bit-exact** |
| **R3-C** synthetic capture fixture | capture 가 확정 발생하는 결정적 상태: A=CAPTURED 종료 / B=`would_capture` 기록 후 계속 · 공격자 생존 · finisher SPENT |
| **R3-D** terminal isolation | B 에서도 hard-kill → 종료, penetration → 종료 유지 |

## 10.7 실행 순서 (개정)

```
[본 개정 커밋]  ← 지금 (E1 결과 열람 전, E2 미실행)
   → E1 → E1b (결과 별도 기록)
   → R3 구현 → R3-A~D 회귀 → E2-B
```

---

# 11. E1 판정 — **INCONCLUSIVE** (2026-08-13 실행·기록)

산출물: `results/e1_t1_slew_counterfactual.json` · `.log`.
**이 판정은 E1b 결과가 무엇이든 변경하지 않는다.**

## 11.1 결과

| 지표 | 값 |
|---|---|
| ω 2.0 → 10⁶ (ALL, n=500 paired CRN) | 84 → 85 captures |
| Δ | **+0.0020**, CI95 **[0.000, 0.006]** |
| rescued `n01` / broken `n10` | **1 / 0** |
| `passes` (lo > 0) | **False** |
| SHAPING_NEEDED (n=297) | 0 → 0, flip **0**, CI [0, 0] |

## 11.2 동결 규칙(§4) 적용

- `rescued = 0` → 기각 : **해당 없음** (1 건 발생)
- `rescued ≥ 1` 且 CI 가 0 제외 → 활성화 : **해당 없음** (CI 하한이 정확히 0.000)
- ✅ **`rescued ≥ 1` 但 CI 가 0 포함 → INCONCLUSIVE, 격상 금지**

T0 의 0/500 을 근거로 1/500 을 "사실상 0" 으로 반올림해 기각 판정으로 끌어오지 않는다.
사전등록이 이 경우를 명시적으로 INCONCLUSIVE 로 지정해 두었다.

## 11.3 정본 문장 (이 이상 금지)

> **A T0 counterfactual showed zero capture changes after removing the nominal
> slew-rate cap, whereas the registered T1 extension produced one rescue in 500
> paired episodes. Under the preregistered rule, evidence for a slew-sensitive
> capture channel is inconclusive; the nominal slew cap is therefore not supported
> as the dominant explanation of the practical boundary.**

high-χ 는 **registered E1 high-χ sample (n=297) 에서 0 rescue** 로 한정 표기한다
("모든 high-χ" 로 일반화 금지). modality-gap / 운동학 논증과 충돌하지 않는다.

## 11.4 ★ 금지 표현 (2026-08-13 자기 정정)

> ~~"95% 상한 0.6% 이므로 observed boundary displacement 를 설명하기엔 far too small"~~

**단위 불일치로 금지.** 0.6% 는 **포획확률 차이의 CI** 이고, 22.45 → 39.33 은
**가속도축 상의 boundary displacement** 다. 두 양은 직접 비교할 수 없다.
"경계를 설명할 만큼 작은가" 는 E1b 에서 rescue 1 건의 위치를 확인하고, 가능하면
ω=∞ 곡선의 50% 교차를 재계산한 뒤에 판단한다.

## 11.5 부수 관측 — Case B 보강 증거로 쓰지 않는다

동일 CRN 에서 T0 91 → T1 84 captures. 그러나 T0 아티팩트는 `SPENT_FAIL=32`,
E1 T1 은 `0` — **종료 계약이 다르다** (T0 런은 R2 이전). 따라서:

> numerically consistent with Case B, **but not interpretable as an attacker-only
> contrast because the termination contracts differ.**

## 11.6 아티팩트 결함 (기록)

`--out` JSON 이 **cell 요약만 저장하고 per-episode records 를 저장하지 않는다**
(`out[name] = sm`). 그 결과 **rescue 1 건의 위치(경계 부근인가 무작위인가)를 이
아티팩트만으로 특정할 수 없다.** §10 freeze stamp 가 manifest 필드는 의무화했으나
records 영속화는 명시하지 않았고, 그 공백이 그대로 드러났다 — 수치감사가 지적한
것과 같은 부류다.

해결: E1b 가 두 팔을 어차피 재실행하므로 records 를 함께 저장한다 (한계비용 0).
**단 그 위치 분석의 증거 등급은 `post-result diagnostic localization of the
preregistered E1 outcome` 이며 confirmatory 로 승격하지 않는다** — `n01=1` 이라는
사실을 이미 보고 나서 찾는 것이기 때문이다.

## 11.7 provenance

| 항목 | 값 |
|---|---|
| 판정규칙 동결 | `eea7180` (11:16:08) |
| 실행 시작 | 11:23:45 (동결 +6분 38초) ⇒ git-stamped prereg 요건 충족 |
| 실행 시점 HEAD | `2d4f748` + **dirty** (harness 미커밋; 이후 `690a294` 로 고정) |
| manifest `code_commit` | `690a294` — **JSON 쓰기 시점**의 HEAD 이지 실행 시작 시점이 아니다 |
| 실행 중 착지한 커밋 | `0d85d26` (docs/83 1 파일, 코드 무변경) |
| `code_dirty` | True (위 사유) |

---

---

# 12. E1b 프로토콜 — paired 조준오차 진단 (동결본, 결과 열람 전)

**E1 판정(§11 INCONCLUSIVE)은 본 진단 결과와 무관하게 변경하지 않는다.**
E1b 는 원인 규명 실험이 아니라 **"무한 slew 에서 ψ 가 어떻게 변하는가"** 하나를
보는 diagnostic 이다.

증거 구조:
```
Integrity  ->  Does unlimited slew change psi?  ->  Does that change align with the lone rescue?
 (gate)          (prospective diagnostic)              (post-result localization)
```

## 12.1 세 역할과 증거 등급 (혼동 금지)

| 역할 | 내용 | 증거 등급 |
|---|---|---|
| **Integrity gate** | E1 재현 확인 | 통과 조건 (실패 시 중단) |
| **Primary diagnostic** | ψ 의 paired 비교 | **prospective diagnostic** (판정규칙을 결과 전에 고정하므로) |
| **Telemetry recovery** | records 영속화 + rescue 1 건 위치 | **post-result diagnostic localization** — confirmatory 승격 **금지** |

## 12.2 Integrity gate (I1~I3) — ★ 한계 명시

| # | 검사 | E1 과 대조 가능? |
|---|---|---|
| **I1** | aggregate 재현: 84 → 85, `n01=1`, `n10=0` | **가능** — E1 JSON 에 있음 |
| **I2** | episode-wise label identity `capture_fixed[i]`, `capture_inf[i]` | **불가능** |
| **I3** | rescue episode ID 일치 | **불가능** |

**★ 정정**: E1 아티팩트는 cell 요약만 저장했으므로(§11.6) **I2·I3 를 E1 과 대조할 수
없다.** episode-wise identity 와 rescue ID 는 E1b 에서 **새로 수립되는 기준선**이며,
E1 에 대한 재현 검증이 아니다. 이는 §11.6 에 기록한 아티팩트 결함의 직접적 대가이고,
숨기지 않는다.

⇒ 실제 통과 조건은 **I1 뿐**이다. I1 불일치 시 → 분기 **D**, ψ 해석 전에 중단.
I2·I3 는 E1b 이후 모든 재실행의 기준선으로 저장한다.

## 12.3 Primary diagnostic — ψ 정의·estimand·판정 (전부 동결)

**ψ 정의**: `slew_audit.audit_episode` 의 `psi` 를 그대로 쓴다 (재정의 금지) —
`psi = arccos( ê_fin · unit(p_att + v_att·tau − p_fin) )`.
**측정창**: 각 팔 자신의 *cone 밴드 안(`0 ≤ ax ≤ range_max`) 이면서 발사 전* 스텝.
두 팔의 궤적 길이가 다를 수 있으므로 **각 팔의 창을 각자 적용**한다.

**에피소드 스칼라**: `psi_i^arm` = 그 에피소드 창 안 ψ 의 **중앙값**.
자격 스텝이 0 인 에피소드는 **paired ψ 분석에서 제외**하고 `n_excluded` 를 보고한다.

**Primary estimand**:
```
Delta_psi_i = psi_i^inf - psi_i^2.0          (paired, per episode)
보고 = median(Delta_psi) + paired bootstrap CI95
       (에피소드 단위 재표집, boot=20000, seed=0 -- paired_compare 와 동일 기계)
```

**판정 (결과 전 고정)**: **"ψ 감소" = CI95 upper < 0.** 그 외는 전부
*"not established"* 로 적는다. 다른 유의성 검정을 추가하지 않는다.

## 12.4 Rescue 위치 정의 (사후해석 방지)

rescue 에피소드가 **등록된 regime label 중 어디에 속하는지만** 보고한다:
`band_of` (curve_sweep) 의 `EASY` / `BAND_AIM` / `SHAPING_NEEDED`,
경계 = `a*(psi_med)=25.75` 와 `a*=39.33`.

**임의 폭(예: "22.45 ± w")을 새로 만들지 않는다.** 정확한 `a_att` 값과 그 에피소드의
`Delta_psi_i` 가 전체 분포 어디에 있는지는 **diagnostic 출력**으로만 낸다
(등급: post-result localization).

## 12.5 ω=∞ 50% 교차 (재계산 시) — estimator 동결

22.45 를 만든 것과 **동일 방법**만 쓴다: `_cross50` (0.5 하향 교차 선형보간) 을
`bin_edges(11, 78, a_star=39.33, per_side=4)` 8 구간 위에서.

**단 E1b 는 n=500 (곡선은 n=2700)** 이라 구간당 표본이 약 1/5 이다. 따라서 산출값은
**diagnostic estimate 로만** 표기하고 22.45 와 confirmatory 수준으로 병치하지 않는다.
구간별 표본수를 반드시 병기한다.

## 12.6 4 분기 판정표 (결과 전 고정)

| 분기 | 조건 | 판정 |
|---|---|---|
| **A** | outcome 거의 불변 **且** ψ 감소 not established | nominal slew cap attribution **추가 하향**. 원인 후보는 prediction / short-range cone / timing 으로 이동 |
| **B** | ψ 감소 확립 (CI upper < 0) **但** outcome 거의 불변 | ★ **"residual aiming error binds first" 도 causal claim 으로는 하향.** 최대 표현 = *"residual aiming error is correlated with the practical boundary, but reducing its slew-induced component did not materially recover capture."* |
| **C** | ψ 감소 확립 **且** rescue 가 등록 band 안 | **local slew-sensitive contribution 만** 인정. E1 이 INCONCLUSIVE 였으므로 *"slew contributes locally"* 까지이고 *"slew explains the boundary"* 는 여전히 금지 |
| **D** | I1 실패 또는 ψ 비정상 증가 등 telemetry 이상 | instrumentation/semantic 문제. **science 해석 중단** |

## 12.7 실행 요구사항

- 두 팔 모두 **per-episode records 영속화** (label · a_att · regime · psi 통계 · 종료 스텝).
- manifest 는 §10 freeze stamp 필드 전부 + `psi_definition="slew_audit.audit_episode"` +
  `n_excluded` 를 싣는다.
- 코드 변경은 `science:` 커밋으로 분리하고, 본 프로토콜 커밋보다 **뒤에** 온다.

---

---

# 12-A. §12.3 개정 — ψ 측정 세계 명시 (결과 열람 전, E1b 미실행)

**구현 착수 중 발견한 blocker 에 대한 정정.** metric 을 새로 만드는 것이 아니라
**측정기를 production rollout 으로 이식**하는 것이다 (instrumentation repair).

## 12A.1 발견 — `audit_episode` 는 E1 과 다른 세계다

[slew_audit.py:82-88] 은 `_zero_commit(acts)` 로 limiter 커밋을 막고
`scripted_finisher(..., clean_threshold_crossed=False)` 로 **발사를 영원히 막는다.**
`audit()` 는 `SystemSpec()` 기본값(구계약)을 쓴다(:96).

| | E1 (outcome) | audit_episode (ψ) |
|---|---|---|
| 계약 | `ratified_system()` | `SystemSpec()` |
| limiter commit | 팔별 설정 | 항상 0 |
| **finisher 발사** | `fire_mode="clean"` | **없음** (하드코딩) |
| commit 후 dodge | 발동 | 미발동 |

⇒ §12.3 을 문자 그대로 구현하면 포획 결과와 ψ 가 **다른 dynamical world** 에서
나오므로 `Δψ` 를 rescue 와 연결하는 질문 자체가 성립하지 않는다.

## 12A.2 정본 개정 문구

> **E1b measures the preregistered aiming-error geometry within the same ratified
> rollout that generates the E1 capture outcome. The geometric ψ computation is
> extracted from `slew_audit` without changing its mathematical definition and is
> shared by both the legacy audit path and the E1b telemetry path. Eligibility is
> evaluated on each arm's own realized pre-fire trajectory. Absolute E1b ψ values
> are not treated as reproductions of the historical `PSI_MED_DEG = 4.26`, because
> that quantity was measured under a different no-fire rollout contract.**

구조 변경:
```
before:  slew_audit rollout ── ψ geometry
after:   shared ψ geometry ──┬── slew_audit rollout   (동작 불변)
                             └── E1/E1b ratified rollout
```
불변: ψ 의 수학적 정의 · angle convention · eligibility predicate · aggregation rule.
변경: **measurement host rollout 만.**

## 12A.3 `PSI_MED_DEG = 4.26` 지위 하향

**historical no-fire audit metric; not directly comparable to E1b absolute ψ.**

파급 — KSAS 문구도 한 단계 조심해야 한다. 기존의 *"경계와 잔여 조준각이 둘 다
불변"* 은 **두 값의 lineage 가 다르다**(곡선 = ratified fire 세계, ψ = no-fire audit
세계). 정본:

> the empirical boundary remained approximately stable, while **a separate no-fire
> aiming audit** reported the same median residual angle **under its registered
> audit configuration**.

"동일 rollout 에서 독립적으로 측정됐다" 는 표현 **금지**. E1b 가 처음으로 capture
outcome 과 ψ telemetry 를 **같은 세계에 묶는다** — E1b 의 가치가 그만큼 커졌다.

## 12A.4 pre-fire 창 정의 (보존할 기존 semantics 가 없으므로 신규 선언)

`audit_episode` 의 실제 창은 `in_band` 뿐이고 "발사 전" 은 발사가 없어 공허하게
참이었다. 따라서 E1b 에서 새로 정의한다. ψ_t 는 `env.step` **이전** 상태로 계산된다.
`t_fire` = fire_event(LOADED→DEPLOYING) 가 일어나는 스텝 index.

| | 정의 | 지위 |
|---|---|---|
| **Primary** | `in_band ∧ t < t_fire` — **commit 스텝 자체를 제외**한 엄격 pre-commit | §12.3 의 estimand `Δψ_i` 는 이 창으로 계산 |
| **Secondary (지금 선언)** | `psi_at_commit` = t_fire 스텝의 ψ 단일값 | 포획을 실제로 결정한 조준각. 에피소드당 1 개 |

발사가 없는 에피소드는 `t_fire` 미정의 → `psi_at_commit` 없음, 별도 집계.
두 창 모두 결과 전에 고정했으므로 사후 선택 여지가 없다.

## 12A.5 E1b 질문 재정식화

- **Primary**: *Within the same outcome-generating T1 rollout, does removing the
  nominal slew cap reduce **pre-commit** aiming error?*
- **Secondary diagnostic**: *Is the lone rescued episode associated with an
  unusually negative `Δψ`?* — 12A.1 수정 이후에야 의미를 갖는다.

## 12A.6 회귀 2 층 (둘 다 통과해야 E1b 실행)

| 층 | 내용 |
|---|---|
| **REG-1 legacy audit metric** | 함수 추출 전후 `slew_audit` 의 ψ 가 **float-exact** 동일. 역사적 audit metric 이 refactor 로 바뀌지 않았음을 보장 |
| **REG-2 telemetry no-op** | 동일 고정 seed 에서 telemetry OFF/ON 의 state · action · terminal label · capture count · RNG progression 이 **bit-exact** 동일 |

---

---

# 13. E1b 판정 — **분기 B** (2026-08-13 실행·기록)

산출물: `results/e1b_aim_diag.json` · `.log`. 판정 순서는 §12.6 그대로.

## 13.1 결과

| 단계 | 결과 |
|---|---|
| **1) I1 integrity** | 84 → 85, `n01=1`, `n10=0` — E1 과 정확히 일치 **PASS** |
| **2) eligibility** | both 500 · 제외 0. `psi_at_commit` 정의: fixed 117 / inf 122 |
| **3) primary Δψ** | median **−24.99°**, CI95 **[−28.42, −20.34]** |
| **4) 동결 규칙** | `CI upper < 0` ⇒ **ψ 감소 ESTABLISHED** |
| **5) rescue** | ep224 · **BAND_AIM** · a_att 28.13 · Δψ 백분위 **41.6 (전형적)** |
| **6) crossing (진단)** | 22.89 → 22.94 (n=500, diagnostic only) |

pre-commit ψ: ω=2.0 median **33.94°** (IQR 9.88–50.24) → ω=∞ **7.85°** (5.44–9.91).
판정 원뿔 반각 = 12.15°.

## 13.2 선언된 secondary 가 기전을 특정했다

`psi_at_commit` (포획을 실제로 결정하는 조준각):

| | median |
|---|---|
| ω=2.0 | **2.320°** |
| ω=∞ | **2.320°** |
| paired Δ | **+0.000, CI95 [0.000, 0.000]** |

양쪽 발사한 **117 쌍이 100% bit-identical** (`fire_step` 까지 동일).

⇒ **slew cap 은 종말 정확도가 아니라 획득(acquisition) 시간을 소모한다.** fire gate
가 `v_shot_soft ≥ 0.9` 를 요구하므로 조준이 좋아질 때까지 쏘지 않고, 그 시점에는 두
세계가 이미 수렴해 있다. pre-commit 의 34° 는 **초기 획득 과도구간**이며 게이트가
그것을 걸러낸다 — docs/45 의 "hold 에서 ω 구속 0.0%"(정상상태 추적 미포화)와 정합.

**selection effect**: `P(good aim | fire)` 가 두 팔에서 같아진다.

rescue ep224 가 확증: ω=2.0 은 **끝내 발사 못 함**(`fire_step=None`, PENETRATED),
ω=∞ 는 41 스텝 발사 후 포획. "더 잘 조준" 이 아니라 **"아예 쏠 수 있었는가"**.
ω=∞ 에서만 발사한 에피소드 5 건(35·71·219·224·229) 중 포획은 **1 건**뿐 —
`fire opportunity 증가 ≠ capture success 증가`. 뒤에 더 큰 병목이 남아 있다.

## 13.3 판정 = 분기 B (+ 프로토콜 결함 기록)

**최대 표현 (동결)**:

> residual aiming error is correlated with the practical boundary, but **reducing its
> slew-induced component did not materially recover capture.**

⇒ `docs/45` 의 인과 귀속(§2)에 이어 **"residual aiming error binds first" 도 causal
claim 으로 하향**한다. ψ 는 실재하고 slew 가 실제로 그것을 지배하지만(25° 감소),
없애도 포획은 회복되지 않는다. 경계를 만드는 것은 조준 오차가 아니다.

**★ 프로토콜 결함 (자기 신고)**: §12.6 의 분기 **B 와 C 가 상호배타적이 아니었다.**
C 의 서술적 전제("rescue 가 등록 band 안")는 충족된다. 그러나 ① E1 이 rescue 를
**INCONCLUSIVE 로 동결**했고 그 판정은 불변이며 ② **사전 선언된** secondary 진단
질문(*"rescue 가 비정상적으로 음인 Δψ 와 결부되는가?"*)의 답이 **NO**(41.6 백분위)
이므로, 이 **사전 선언 판별자**로 B 를 택했다. 사후 기준이 아니다. ep224 의
"발사 자체 불가" 기전은 **diagnostic 관찰로만** 기록하고 격상하지 않는다.

## 13.4 남은 원인 후보 (§12A.1 잔여)

`psi_at_commit` 중앙값이 **2.32°** 로 이미 매우 작은데도 경계가 22.45 에 있다.
⇒ 조준 정확도는 원인이 아니다. 남은 후보:

1. **단거리 원뿔 기하** — 판정 원뿔은 apex 에서 벌어지므로 유효 횡반경이
   `ax·tanθ` 다. 공칭 ρ=1.77 은 `ax = R_max = 8.22` 에서만 얻는 값이고, 실제
   발사 상태의 `ax` 가 그보다 작으면 footprint 가 줄어든다.
2. **예측 오차** — 등속 조준 `p+vτ` vs 실제 `p+vτ+½aτ²` (estimator/guidance 문제).

**우선순위: 1 → 2** (1 은 기존 telemetry 로 거의 공짜, 2 는 별도 설계 필요).

---

---

# 14. E1c 진단 — **경우 ③ (compounded)** + `0/1598` 해석 정정 (EXPLORATORY)

산출물: `results/e1c_fire_decomp.json` · `.log` · `shepherd/scripts/e1c_fire_decomp.py`.
**증거 등급 = exploratory / post-result diagnostic** (E1b §13 을 본 뒤 세운 가설).
KSAS confirmatory mechanism claim 으로 **승격 금지** — "diagnostic suggests" 수준.

## 14.1 분해 `P(C|a) = P(F|a) · P(C|F,a)` (T1 · hold · ω=2.0 · n=500)

| a_att | n | **P(F\|a)** | **P(C\|F,a)** | P(C\|a) |
|---|---|---|---|---|
| 11.0–18.1 | 52 | 1.000 | 1.000 | 1.000 |
| 18.1–25.2 | 50 | 0.920 | 0.652 | 0.600 |
| 25.2–32.2 | 49 | **0.388** | **0.105** | 0.041 |
| 32.2–39.3 | 52 | **0.000** [0, 0.069] | — | 0 |
| ≥39.3 | 297 | **0.000** | — | 0 |

⇒ **경우 ③**: 22–32 부근의 practical collapse 는 "쏜 다음 실패" 하나가 아니라
**commit-eligibility 붕괴 + conditional terminal failure 의 합성**이다.

## 14.2 ★ `0/1598` 해석 정정 (claim-registry 급)

**a_att ≥ 32.2 에서 발사 0/350** (발사한 최대 a_att = 32.15). 따라서 a ≥ 39.33 의
zero 들은 **net 을 쏴서 실패한 것이 아니라 게이트가 기권한 것**이다.

증거 구조를 다시 쓰면:
- **ANALYTIC**: stated unassisted single-shot model 에서 χ ≥ 1 은 necessary-condition 위반
- **MEASURED**: registered closed-loop controller 는 그 영역에서 net capture 0
- **그러나**: 그 measured zero 는 **gate abstention 때문에 terminal physics 를 독립
  검증하지 못한다** (censored)

**금지**: *"analytic boundary above which 0/1598 shots failed"* / *"0/1598 이 analytic
경계를 실측 검증했다"*.

**정본**:
> No net captures were observed above the analytic outer bound; **however, the
> registered fire gate issued no shots in this regime, so these outcomes do not
> constitute an independent empirical test of post-commit net failure.**

## 14.3 국소 기하 예산 (기술통계)

| a_att bin | nF | ax | ρ_local=ax·tanθ | r_perp | slack | 2·slack/τ² |
|---|---|---|---|---|---|---|
| 11.0–18.1 | 52 | 6.47 | 1.394 | 0.218 | 1.148 | 25.51 |
| 18.1–25.2 | 46 | 6.38 | 1.374 | 0.359 | 1.034 | 22.98 |
| 25.2–32.2 | 19 | 6.37 | 1.372 | 0.308 | 1.103 | 24.52 |
| 전체 | 117 | **6.408** | 1.380 | — | **1.103** | **24.52** |

`ρ_nominal 1.770 → (ax 6.41 ≠ R_max 8.22) → 1.380 → (ψ 2–3°) → 1.103`.
관측 50% 교차 = 22.4–22.9.

**최대 표현**:
> The realized commit geometry **diagnostically reconciles much of the gap** between
> the nominal 39.3 m/s² outer bound and the observed practical transition.

**금지**: *"22.45 의 원인을 거의 전부 설명했다"*. 이유 — ① 기하가 fired episodes 에
조건부이고 ② fire gate 자체가 feasibility 관련량으로 selection 하며 ③ 24.5 와 22.4
사이 잔차가 있고 ④ 예측 오차 등 후보가 남아 있다.

## 14.4 ★ `ax` 안정성 해석 하향 (자기 정정)

*"selection effect 라면 a 에 따라 움직여야 한다"* 는 제 논리는 **성립하지 않는다**.
`F=1` 인 episode 만 보면 **게이트가 유리한 기하를 골라내므로 ax 가 좁은 범위에
pin 될 수 있다.**

**최대 표현**:
> Among episodes admitted by the fire gate, the realized controller–gate **operating
> point** is tightly concentrated around ax ≈ 6.4 m.

"selection artifact 가 아니다" 는 **아직 주장 불가**.

## 14.5 드러난 3 단 병목

```
Acquisition            slew 가 여기에 영향 (E1b: pre-commit psi 33.9 -> 7.9 deg)
   ↓
Commit eligibility     gate 가 favorable state 를 기다림. 고-a 에서는 끝내 못 얻어 **미발사**
   ↓
Conditional capture    쏴도 끝이 아님 (25–32 구간 P(C|F) = 0.105)
```

"0.30 s terminal physics" 보다 훨씬 풍부하다.

## 14.6 미해결 — 왜 E1d 가 필요한가 (지금 실행하지 않음)

a ≥ 32.2 에서 `P(C|F,a)` 를 **관측할 수 없다** (F=0). 따라서 현 데이터로는
*"32 이상은 net 물리상 실패"* 와 *"controller 가 보수적으로 거절"* 을 **경험적으로
분리할 수 없다.** analytic bound 는 있으나 closed-loop empirical validation 은 censored.

**E1d 개념 (설계만, 미실행)**: 발사 threshold 를 낮추면 pre-commit 궤적과 selection 이
함께 바뀐다 → 더 깨끗한 것은 **state-conditioned forced-commit counterfactual**.
실제 방문한 pre-commit state `z_t` 를 저장하고 동일 snapshot 에서 clone 하여
**정확히 한 번 강제 commit** (`do(F=1)`), 이후 attacker 응답·τ·net 기하·물리·
limiter hold·CRN 을 모두 동일 유지 → `P(C | do(F=1), z)` 직접 측정.
a 층 20–25 / 25–32 / 32–39.3 / ≥39.3 포함, ax·ψ 기록.

**순서 규율**: E1c 봉인 → **E2-B** → modality-gap 판정 → 필요 시 E1d 사전등록.
E1c 는 exploratory 였고 여기서 E1d 로 바로 파고들면 KSAS freeze 가 계속 밀린다.

---

---

# 15. E1d 사전등록 — **commit geometry intervention** (동결본, 미실행)

**성격**: "forced early fire" 실험이 **아니다**. `ax` 만의 순수 causal intervention 이라고
부르지도 않는다. 정확히는 **ax-targeted commit-timing intervention** 이고,
**terminal geometry mechanism-isolation experiment** 이지 controller performance
실험이 아니다. 이 라벨을 결과 보고에도 유지한다.

## 15.1 질문

> **Does moving the forced commit to a larger realized axial footprint shift the
> net-capture boundary as predicted by local cone geometry?**

동기(§14.6): a ≥ 32.2 에서 `P(C|F,a)` 를 관측할 수 없어 *"net 물리상 실패"* 와
*"controller 의 보수적 거절"* 을 분리하지 못한다.

## 15.2 ★ 설계 정정 3 건 (초안 폐기)

**(1) ω=∞ 는 조준 교란을 제거하지 못한다.** E1b 실측: ω=∞ 에서도 pre-commit ψ
중앙값 **7.85°**. 게이트가 없는 forced-fire 세계에서는 그 오차를 안고 일찍 쏜다.
ψ=7.85° 를 그대로 넣으면 `s = ax(tanθ − tanψ)` 가 크게 줄어 perfect-aim 기준
a\*≈38 이 성립하지 않는다. ⇒ primary 팔에는 **perfect-aim-at-commit counterfactual**
(commit 스텝에 cone axis 를 coast point 에 정확히 정렬, ψ=0)이 필요하다.

**(2) 온라인 `first ax ≤ target` 트리거 폐기.** dt=0.05 · v≤30 이면 한 스텝에 축방향
최대 ~1.5 m 이동 → 8.0 을 처음 통과한 순간 realized ax 가 6.5–8 로 크게 undershoot
한다. 8.0 은 R_max=8.22 에 붙어 있어 특히 위험. ⇒ **two-pass replay** 로 교체.

**(3) `θ_fire=0, c_fire=0` 대신 명시적 force-commit hook.** 원하는 개입은
`do(F=1)` 이지 `do(θ_fire=0)` 가 아니다 (후자는 게이트 관련 다른 semantics 까지
바꿀 수 있다). 계약 문구:
> at the registered forced-commit step, **bypass the eligibility predicate for exactly
> one irreversible shot**; all other system parameters remain unchanged.

## 15.3 two-pass replay 절차

```
Pass 1 (reference, 팔 간 공유)  fire 없이 롤아웃 · 각 스텝 기하(ax, psi, ...) 저장
                                -> target ax 에 가장 가까운 스텝을 commit step 으로 선택
Pass 2 (replay)                 동일 seed/CRN 재생 · **사전 선택된 그 스텝에서만** force commit
```
트리거 로직이 dynamics 에 영향을 주지 않는다. Pass 1 은 target 과 무관하므로
**세 팔이 공유**한다 (비용 절감).

**스텝 선택 규칙 (동결)**: `|ax − target|` 최소. 동률이면 이른 스텝.
밴드 밖(`ax > range_max` 또는 `ax < 0`) 스텝은 후보에서 제외.
후보가 없는 에피소드는 **제외**하고 `n_excluded` 를 보고한다.

## 15.4 팔 구성

| arm | target ax | aiming | 역할 |
|---|---|---|---|
| **D-a** | 6.5 (E1c 실측 6.41) | **ideal** (ψ=0 at commit) | 현 운용점 근처 기준 |
| **D-b** | 8.0 | **ideal** (ψ=0 at commit) | larger-footprint 반사실 |
| **D-c** | 8.0 | **actual controller, ω=∞** | slew cap 을 없애도 남는 pointing 비용 |

분해: `D-b − D-a` = larger commit geometry 효과 · `D-c − D-b` = 잔여
controller/prediction pointing imperfection 비용.
(ω=2 forced-early arm 은 우선순위 낮음 — E1b 가 이미 slew 의 acquisition 지연을 보였다.)

## 15.5 예측 (결과 전 동결)

**Primary (방향성)**:
$$a^*_{50}(\text{D-b}) \;>\; a^*_{50}(\text{D-a})$$

**Reference benchmark (pass/fail 아님)**: `2·ax_realized·tanθ / τ²`.
D-b 가 정확히 38 에서 교차해야 가설 통과라는 규칙은 **쓰지 않는다** — attacker
가속 방향 · 이산 타이밍 · 예측 모델 등이 남아 있다.

**보고 의무**: nominal target 이 아니라 **realized ax 분포**로 분석한다. 각 팔의
`ax_realized` (med/p25/p75) 와 `psi_at_commit` 을 반드시 병기한다.
*"8.0 arm 의 모든 에피소드가 정확히 8.0"* 이라고 쓰지 않는다.

## 15.6 계약 추가 (기본값 off + bit-exact 회귀)

| 필드 | 의미 |
|---|---|
| `force_commit_step: Optional[int] = None` | 그 스텝에서 발사 자격 술어를 **정확히 1 발** 우회 |
| `perfect_aim_at_commit: bool = False` | 그 스텝 직전 finisher heading 을 `unit(p_coast − p_fin)` 로 설정 (ψ=0) |

구현 경로: `AgentKin` 은 non-frozen dataclass → `e` 직접 기록 가능.
`FireGate` 는 frozen 이나 `dataclasses.replace` 로 한 스텝만 교체 후 **복원**.

**회귀 게이트 (4/4 통과 전 실행 금지)**:
| # | 내용 |
|---|---|
| **D-A** | 두 필드 기본값에서 기존 결과 **bit-exact** (최우선; 실패 시 즉시 중단) |
| **D-B** | replay 무결성 — Pass 2 의 commit 스텝 직전 상태가 Pass 1 기록과 **bit-exact** (공격자는 commit 전까지 반응하지 않고 finisher 는 이동하지 않으므로 성립해야 한다) |
| **D-C** | `perfect_aim_at_commit=True` 에서 실제로 `psi_at_commit ≈ 0` (수치 허용오차 내) |
| **D-D** | force commit 이 **정확히 1 발** (K=0 소모, 이후 재발사 없음) · 하드킬·침투·절단 종료 유지 |

## 15.7 규모·순서

n=1500/팔. Pass 1 공유 → 롤아웃 총 1500 + 4500 = **6000** (~3.5–4 h).
순서: **본 prereg 커밋 → 코드 + D-A~D 회귀 → science 커밋 → 실행 → results 커밋.**
(E2-B 에서 절차를 어긴 경험 반영 — 실행 코드는 결과 이전에 git 고정.)

## 15.8 해석 규율

- 이것은 **mechanism-isolation** 이다. D-b 의 높은 포획률을 "시스템 성능" 으로 읽지 않는다
  (perfect-aim 은 실현 불가능한 반사실이다).
- `ax` 가 유일 원인이라고 쓰지 않는다. 최대 표현 = *"moving the commit to a larger
  realized axial footprint shifted the boundary in the predicted direction"*.
- D-b 가 D-a 와 차이 없으면 **기하 가설 기각** → 예측 오차 등 다음 후보로 이동.

---

---

# 16. E2-B 판정 — **Δ_comp = 정확히 0** (2026-08-13 실행·기록)

산출물: `results/e2b_intercept_shamnet.json` · `.log`.
execution_commit = `80eefa0` (실행 전 봉인, clean tree). 분석 순서는 §10.5 그대로.

## 16.1 ① high-χ exact oracle — PASS

| 검사 | n | 불일치 |
|---|---|---|
| a ≥ 39.33 | 1,598 | **0** |
| **강화**: A 가 NET_CAPTURE 가 **아닌** 전 에피소드 | 2,274 | **0** |

비교 필드 = `episode · label · regime · a_att · att_speed · net_radius · tau`.
정본 문구: **bit-exact over all persisted paired outcome/event fields**
(궤적은 저장돼 있지 않으므로 *"trajectory bit-exact"* 라고 쓰지 않는다).
⇒ 개입 분기가 정확히 426 개 포획 에피소드에만 닿았다. **R3 배선 확증.**

## 16.2 ②③④ 결과

| | NET | HK | PEN |
|---|---|---|---|
| A (net ON) | 426 | **545** | 1,729 |
| B (sham) | 0 | **545** | 2,155 |

```
Delta_comp = P_HK^B - P_HK^A = 0.2019 - 0.2019 = +0.0000   CI95 [0.000, 0.000]
n01 = 0 · n10 = 0
A 의 NET_CAPTURE 426 건 중 B 에서 HARD_KILL 로 전환 = 0
```

구간별로도 전부 Δ = 0:

| band | n | A:net | A:HK | B:HK | Δ |
|---|---|---|---|---|---|
| EASY | 590 | 0.717 | 0.063 | 0.063 | +0.0000 |
| BAND_AIM | 512 | 0.006 | 0.234 | 0.234 | +0.0000 |
| SHAPING | 1,598 | 0.000 | 0.243 | 0.243 | +0.0000 |

## 16.3 ★ 사전 예상이 반증됐다 (자기 정정)

§10.5 는 *"low-a 에서 net 이 0.717 로 먼저 종료시키므로 E2-B 정보가 가장 크다"* 고
예상했다. **그 구간에서도 정확히 0 이었다.**

⇒ 이전 기술 **"현재 24.3% 는 경쟁위험 때문에 하한"** 은 **틀렸다.**
경쟁위험 censoring 이 존재하지 않으며, E2-A 의 하드킬 수치는 이미 uncensored 다.
보정 없이 그대로 쓴다.

## 16.4 그래서 modality gap 은 오히려 깨끗해진다

| 구간 | net capture | physical intercept |
|---|---|---|
| EASY | **0.717** | 0.063 |
| BAND_AIM | 0.006 | **0.234** |
| SHAPING (χ≥1) | 0.000 | **0.243** |

두 modality 의 유능 구간이 **부분적으로 상보적**이다 — 저-a 는 net, 고-a 는 물리
요격. *"물리 요격이 항상 낫다"* 보다 정확한 서술이다.

**결과 명명 (동결)**: E2-B 의 P_HK 를 *"true physical interception probability"* 라고
부르지 않는다. 정본 = *physical-interception incidence under matched
commit-conditioned threat response with net capture removed as a competing terminal
event.*

## 16.5 미해결 — 왜 0/426 인가

`n01 = n10 = 0` 이라는 **정확한** 0 은 통계적 우연이 아니라 구조적 이유를 시사한다.
후보: ① NK veto (`r_nk = 6.0`) — 포획이 성립하는 시점엔 이미 무-kinetic 구역 안이라
기폭이 거부됨 ② limiter 가 이미 소모됨 ③ 기하상 접촉 불가.

**판별 불가**: 현 records 에 `veto_events` 가 에피소드별로 저장돼 있지 않다.
값싼 진단이므로 후속에서 확인한다 (이유가 ① 이면 *"net 이 되는 순간은 이미 kinetic
이 금지된 순간"* 이라는 강한 문장이 된다).

---

---

# 17. 리드타임 진단 — **"시간 부족" 가설 기각** (EXPLORATORY)

산출물: `results/lead_time_diag.json` · `results/lead.log` (랩 서버 tmux, n=300/arm).
**증거 등급 = EXPLORATORY / post-result diagnostic.** 등록 T1 이 아니라
`sense = ∞` **진단 변형**이므로 등록 T1 수치와 나란히 놓지 않는다.

## 17.1 동기

궤적 뷰어 육안 검사에서 나온 관찰 — *"공격자가 너무 가까워 대응 시간이 부족하다"*.
배경 실측(E1c 재집계): 교전 시간 median **2.00 s**, τ=0.30 이 그 **15%**,
발사 후 남은 시간 median **0.45 s**, v·τ = 5.74 m = 스폰 24 m 의 **24%**.
⇒ docs/59 가 2026-08-07 에 같은 도구로 잡은 legacy 스케일 결함이 **KSAS 캠페인에는
그대로 남아 있다** (수치감사 RED FLAG #4).

## 17.2 결과 — HK 는 리드타임에 **평평하다**

| start_x | HK | net | PEN | 교전시간 | **코스 형성** | 최근접 |
|---|---|---|---|---|---|---|
| 24 | 0.190 [0.150, 0.238] | 0.133 | 0.673 | 1.35 s | **111/300** | 1.48 m |
| 36 | 0.207 [0.165, 0.256] | 0.110 | 0.683 | 1.73 s | 262/300 | 1.38 m |
| 48 | 0.177 [0.138, 0.224] | 0.107 | 0.717 | 2.10 s | **300/300** | 1.50 m |
| 60 | 0.177 [0.138, 0.224] | 0.107 | 0.717 | **2.80 s** | **300/300** | 1.74 m |

교전 시간을 **2 배**로 늘려도 HK 는 0.190 → 0.177. CI 전부 겹치고 추세 없음.
침투는 오히려 소폭 증가(0.673 → 0.717). **코스 형성만 37% → 100%** 로 급증.

## 17.3 기전 — 마지막 0.7 m 를 못 좁힌다

접촉반경 **0.75 m** 대비 최근접 분포:

| start_x | med | p10 | 접촉권(≤0.75) 도달률 |
|---|---|---|---|
| 24 | 1.48 | 0.84 | 0.043 |
| 36 | 1.38 | 0.83 | 0.050 |
| 48 | 1.50 | 0.87 | 0.047 |
| 60 | 1.74 | 0.90 | 0.057 |

**최근접 분포가 리드타임과 무관하게 고정**이다. p10 조차 0.83~0.90 m 로 접촉반경
위에 벽처럼 걸린다. 성공한 HK 에피소드의 최근접도 네 arm 모두 0.87~0.95 m 로 동일
(접촉은 최근접 자체가 아니라 스텝 간 swept 경로로 판정되므로).

## 17.4 순서 — "늦게 도착" 이 아니다

침투 에피소드 **837 건 전부에서 최근접이 종료 이전**에 발생 (0/202, 0/205, 0/215,
0/215). ⇒ limiter 는 **제때 도착한다.** 따라붙어 1.5 m 까지 접근한 뒤 **거기서 못
좁히고** 공격자가 통과한다. 실패는 도착 시각이 아니라 **종말 근접**이다.

## 17.5 판정 (★ 2026-08-13 하향 정정)

**데이터가 확실히 말하는 것은 두 가지뿐이다:**

> ① **리드타임 부족은 아니다.**
> ② **현재 intercept controller 에서 terminal miss distance 가 약 1.4~1.7 m 에
>    고정된다.**

여기까지다. **왜 1.5 m 벽이 생기는지는 controller 와 capability 가 아직 분리되지
않았다.**

### 취소된 문구 (과잉)

> ~~"병목은 종말 기동 차이다 — `a_lim = 0.35·a_att` 대 jink `0.6·a_att` 라 마지막
> 미터에서 보정 능력을 초과한다"~~
> ~~"문헌 앵커 자체가 만드는 결과"~~

**`0.35 < 0.6` 만으로 물리적 infeasibility 가 나오지 않는다.** 요격은 상대의
순간 기동을 그대로 맞받는 문제가 아니라 **intercept set 을 선점하는 문제**다.
공격자가 바깥 arc 를 돌면 방어자는 같은 arc 를 따라갈 필요가 없고, 안쪽
chord/inner-radius 를 타면 `L_defender < L_attacker` 가 되어 순간 가속이 열세여도
반드시 불리하지 않다. 따라서 위 문장은 **mechanism hypothesis** 로만 남긴다.

### 오히려 이 조합이 핵심이다

```
course formation  37% -> 100%      (리드타임이 코스는 확실히 만들어준다)
P_HK              19% ->  18%      (그런데 결과가 안 바뀐다)
d_min            ~1.5 m 고정        (최근접 분포가 통째로 안 움직인다)
```

⇒ **"시간만 더 주면 같은 pursuit law 가 해결할 문제는 아니다"** 는 강한 증거.
다음 질문은 곧바로:

> **같은 기체 성능에서 pursuit law 만 바꾸면 1.5 m barrier 를 깰 수 있는가?**

### 현행 controller 의 성격

`intercept_limiter` (mission_rollout.py:114) 는 예측 요격점(PIP)으로 **최대가속
추격**이다. 구조적으로 공격자가 간 길을 뒤따르는 man-to-man 에 가깝다. 반면
limiter 의 원래 역할은 **길목 차단(route occupation / zone defense)** 에 가깝다.

⇒ 현재 24% 하드킬이 physical interception capability 의 상한인지, 아니면
**현행 pursuit baseline 의 구조적 한계**인지 아직 모른다. (§18 이 이를 가른다.)

## 17.6 ★ 범위 한정 (과잉 일반화 금지)

- 이 진단이 반증한 것은 *"짧은 교전이 **하드킬**을 억제한다"* **하나뿐**이다.
- **net 쪽은 열려 있다** — E1c 의 "a≥32.2 발사 0/350" 과 "ax 6.4 < R_max 8.22" 는
  게이트가 유리한 상태를 **기다리는** 문제라 리드타임 영향을 받을 수 있다.
  다만 본 진단에서 net 은 0.133 → 0.107 로 **오히려 감소**했다 (공격자도 회피할
  시간을 더 얻는다). 별도 설계가 필요하다.
- **24 m 코리도 문제 자체가 해소된 것은 아니다.** 캠페인 계약 차이(감사 §E)는 그대로.
- `sense = ∞` 변형이므로 등록 T1 과 병치 금지. 36 arm 부터는 등록 T1(sense 30)
  이었다면 전-limiter 가시 비율이 0.717 → 0.000 으로 무너졌을 조건이다.

---

---

# 18. E3 사전등록 — **controller-limited vs capability-limited** 판별 (동결본, 미실행)

§17 이 남긴 질문: 1.5 m barrier 가 **현행 pursuit law 의 한계**인가, **기체 성능의
한계**인가. 새 heuristic controller 를 하나 더 돌리는 것보다 **oracle 로 가르는
것**이 판별력이 높다.

> **미래를 다 아는 oracle 도 못 잡으면 물리 문제. oracle 은 잡는데 현행 pursuit 만
> 못 잡으면 정책 문제.**

## 18.1 arm 구성

| arm | 내용 | 역할 |
|---|---|---|
| **E3-0** | 현행 `intercept_limiter` (PIP 최대가속 추격) | 기준선 (§17 = 1.5 m) |
| **E3-1** | **cutoff / inside-line** — 공격자를 따라가지 않고 asset 쪽 통과 경로·미래 crossing point 를 선점 (route occupation 의 최단순 scripted 구현) | 정책 개선 여지 |
| **E3-2** | **offline optimal-control upper bound (oracle)** | ★ 판별자 |

## 18.1b per-limiter 분해 (결과 전 추가, 2026-08-13)

관찰: *"4 기가 같은 PIP 로 같이 달려들고 같이 놓친다"* — 그러면
`4 limiters ≠ 4 independent chances` 이고 실질적으로 **한 번의 추격을 4 대가 복제**
하는 것에 가깝다. 실패가 **완전히 상관**되면 "4 기인데 왜 20% 인가" 가 이상하지 않다.

에피소드마다 limiter `i = 0..3` 별로 저장:

| 값 | 의미 |
|---|---|
| `d_min,i` · `t_min,i` | 개별 최근접과 그 시각 |
| `t_commit,i` | 커밋 시각 (있으면) |
| `d_oracle,i` | §18.2 의 hindsight 도달 (개별) |

에피소드 요약:
`std(t_min,i)` **arrival layering** · `max−min t_min` 시간차 범위 ·
`std(d_min,i)` 공간 다양성 · 커밋 limiter 수 · 커밋 시각 spread ·
접근 방위 angular spread.

`t_min,1 ≈ t_min,2 ≈ t_min,3 ≈ t_min,4` 이고 `d_min` 도 비슷하면 시각 인상이
**숫자로 확정**된다.

**★ 이것은 아직 "학습 필요성" 이 아니라 `role/assignment structure 필요성` 의 후보
증거다.**

## 18.2 Oracle 정의 — **hindsight pathwise reachability** (닫힌 형태)

기록된 공격자 궤적 `p_A(t)` 와 limiter 초기 상태 `(p_L0, v_L0)`, 동일 한계
`(a_max, v_max)` 에 대해 이중적분기의 도달집합은 중심 `p_L0 + v_L0·t`, 반경 `R(t)`
(램프식, `contact_reachability.reach_radius` **재사용** — 새 정의 금지) 이므로

```
d_min^oracle = min_t  max(0,  |p_A(t) − (p_L0 + v_L0·t)|  −  R(t) )
```

limiter 4 기 중 **최솟값**을 취한다. 최적화 없이 궤적만으로 계산된다.

**★ 낙관 방향 (의도적)**: 드리프트-중심 근사는 `v_L0 + Δv ≤ v_max` 결합을 무시하므로
실제보다 **관대**하다. 따라서 **oracle 이 못 닿으면** capability 한계 주장이 강해진다.

### ★ 정본 명칭과 해석 한계 (필수)

이 양의 이름은 **`hindsight pathwise reachability on the realized attacker
trajectory`** 다. T1 공격자는 방어자를 보고 반응하므로 `π_L` 을 바꾸면 궤적도 바뀐다.
따라서:

| 보여주는 것 | 보여주지 **못하는** 것 |
|---|---|
| **vehicle dynamics alone do not explain the miss on that realized path** | ~~a realizable causal role-assignment policy would necessarily succeed~~ |

*"oracle 이 0.4 m 까지 갔다"* 가 *"실제 causal controller 도 0.4 m 까지 갈 수 있다"*
를 뜻하지 **않는다.** 결과 문장에 반드시 병기한다.

## 18.3 판정 (결과 전 동결) — 3 갈래

**Primary**: `P(d_oracle ≤ 0.75)` vs `P(d_actual ≤ 0.75)` (실측 0.043~0.057),
paired `Δd = d_oracle − d_actual` 중앙값 + bootstrap CI95.
**임의 문턱 신설 금지**, 방향으로 해석.

| # | 조건 | 판정 |
|---|---|---|
| **A** | actual 이 전부 동시 접근 **且** oracle 도 대부분 `> 0.75` | assignment 만으로 설명 어려움 → **registered vehicle capability 제한** 가능성. 다음은 μ 등 capability axis |
| **B** | actual 은 4 기 동시 miss (~1.5 m) **但** oracle 이 `< 0.75` 인 limiter 가 자주 존재 | **현행 pursuit 가 available geometric opportunity 를 활용하지 못한다.** 다음은 **scripted role separation** — 아직 MARL 아님 |
| **C** | oracle margin 이 크고 **且** 이후 scripted role separation 까지 성공 | `naive pursuit < structured role assignment` 확인. 그때 학습 질문이 정의됨 |

## 18.3b ★ 학습 근거의 형태 (사다리 수정)

```
① 무할당 추격  →  ② scripted 역할분리  →  ③ 학습
```
**②가 실패해야만 ③으로 가는 것이 아니다.** 오히려 ②가 성공하면 학습 질문이 더 잘
정의된다: scripted arc assignment 가 T1 에서 성공해도, **T2 연속반응에서 fixed role
pattern 이 깨지고 누가 blocker/closer 인지 동적으로 바뀌어야 한다면** —

> 학습의 근거 = ~~"scripted 가 실패했다"~~ →
> **"role assignment mechanism 은 존재하지만 fixed heuristic 으로는 adaptation 이
> 부족하다"**

## 18.3c 역할 분리의 목표 = **시간차 요격 기회**

현행 all-chase 는 `t_1 ≈ t_2 ≈ t_3 ≈ t_4`. 좋은 role separation 은 의도적으로
`t_1 < t_2 < t_3 < t_4` 를 만들거나 서로 다른 angular sector 를 덮어서,
**공격자가 첫 번째를 피하면 두 번째의 기하로 들어가게** 한다.

기능 후보 (이름보다 **staggered opportunity** 가 본질):
chaser/pressure · cutoff (inner chord 선점) · reserve (다음 escape 방향) ·
rear/asset-side (breakthrough insurance).

현행 all-chase 는 사실 *limiter* 라는 이름과도 잘 맞지 않는다.

## 18.4 눈으로 볼 것 (뷰어)

실패 에피소드에서 limiter 가 **공격자 뒤/바깥에서 쫓는지**, 아니면 공격자–asset
사이의 **안쪽 chord 를 선점할 수 있었는데 PIP 때문에 바깥으로 끌려나가는지**.
후자가 반복되면 controller-limited 의 시각적 증거다.

## 18.5 연구 프로그램에서의 위치

controller-limited 로 판명되면 B2 의 방향이 *"limiter 가속을 높인다"* 가 아니라

```
pursuit  ->  route occupation / cutoff  ->  cooperative shaping
```

으로 자연히 연결된다. limiter 의 원래 개념(길목 차단)과도 정합한다.

---

---

# 19. E3 판정 — **B: controller-limited on the realized attacker path**

산출물: `results/e3_oracle.json` · `.log` (n=300, 세계 = curve_sweep/E2-A 동일).

## 19.1 Primary (§18.3)

| | 값 |
|---|---|
| `P(d_actual ≤ 0.75)` | **0.043** [0.025, 0.073] |
| `P(d_oracle ≤ 0.75)` | **0.883** [0.842, 0.915] |
| paired `Δd` 중앙값 | **−1.262 m**, CI95 [−1.389, −1.201] |
| 최근접 중앙값 | actual **1.482** vs oracle **0.000** |

**두 층 (§18.1b)**:
`P(∃i: d_oracle,i ≤ 0.75) = 0.883` · `E[Σ 1(d_oracle,i ≤ 0.75)] = **2.84 / 4**`
(분포: 4 대 전부 가능 173 · 2 대 59 · 1 대 29 · 0 대 35 · 3 대 4).
실제 접촉 limiter 수 평균 **0.053**. **침투 203 건에서는 oracle 가능 중앙값 4.0/4.**

## 19.2 시간 동기화 — 확정

```
range(t_min)   중앙값 0.125 s · p90 0.250 s · <0.3 s 비율 93.7%
angular spread 중앙값 115.8 deg
```

⇒ 정본: **spatially diversified but temporally synchronized.**
*"4 대가 하나를 복제한다"* 는 표현은 **폐기** (방위는 116° 벌어져 있다).
원인 후보는 초기 배치가 아니라 **`shared interception timing induced by the pursuit
law`**.

## 19.3 판정 = **B** · 최대 표현 (동결)

> **There is substantial unused pathwise interception opportunity, but the baseline
> concentrates those opportunities into a single temporal layer.**

**금지**: *"a realizable causal role-assignment policy would succeed"* /
*"assignment 가 causal solution 이다"* / *"학습이 필요하다"*.
근거는 **hindsight pathwise reachability on the realized attacker trajectory** 이고
T1 은 반응하므로 `π_L` 을 바꾸면 궤적도 바뀐다. 드리프트-중심 근사도 낙관 방향이다.

## 19.4 secondary (exploratory)

- **CAPTURED 40 건은 정반대 패턴**: oracle 가능 limiter 중앙값 **0.0/4**, 실제 최근접
  2.27 m. net 이 잡는 판은 limiter 가 애초에 닿을 수 없는 기하다.
  ⇒ 데이터가 점점 **`net-friendly geometry ≠ kinetic-friendly geometry`** 를 지지한다.
  **함의**: 하드킬을 높인다고 net capture 가 함께 오른다는 보장이 없다.
- **C033 대규모 확인**: 커밋 발생 57/300 (19.0%), 커밋 수 평균 0.223, 하드킬도 정확히
  57 건 — 커밋은 하드킬 판에서만 발생한다. `margin` 0.22~0.42 m 도달은 이미 접촉권에
  들어간 뒤이므로 커밋은 **선행 결정이 아니라 사후 기록**에 가깝다.

---

# 20. E4-1 사전등록 — **temporal stagger only** (동결본, 미실행)

## 20.1 질문 (좁게)

> **Does temporal staggering alone recover interception opportunity when spatial
> deployment, vehicle capability, attacker model, and pursuit geometry are held fixed?**

지역수비 전체 구현이 **아니다**. 오직 `동시 4 대 추격 → 시간층이 분리된 4 대 추격`.

## 20.2 고정 (변경 금지)

T1 attacker · initial ring · `(a_lim, v_lim)` · contact radius · PIP/intercept 기하 ·
limiter 수 · sensing · 모든 terminal 계약.
**바뀌는 것은 limiter 별 intended interception timing 하나뿐.**

## 20.3 개입 방식

기존 `intercept_limiter` 의 PIP 를 그대로 쓰되 조준 시점만 이동:

```
aim_i = p_att + v_att * (t_lead + delta_i)      (t_lead = 기존 해석해)
delta_i in { -Δ, -Δ/3, +Δ/3, +Δ }               (limiter index 순, 고정 배정)
```
각 limiter 가 공격자 경로의 **서로 다른 미래 점**을 겨냥 → 요격 시각이 갈라진다.
그 외 로직·게인 무변경 (자유 게인 여전히 0).

### ★ Amendment A — `t_lead + δ < 0` 처리 (결과 전 동결)

`δ` 가 −0.25 s 까지 가므로 근접 상황(`t_lead < 0.25`)에서 **음의 lead time** 이 나올
수 있다. 그러면 "더 이른 요격 층" 이 아니라 **공격자의 과거 위치를 겨냥하는** 이상한
컨트롤러가 된다. 규칙:

```
t_i^eff = max(0,  t_lead + delta_i)
```

**보고 의무**: arm 마다 ① clamp 발생 episode 비율 ② limiter-level clamp 비율.
clamp 가 잦으면 *"±Δ 의 대칭적 temporal staggering"* 이라고 부르지 않고
**`horizon staggering with a zero lower bound`** 로 해석·표기한다.

### ★ Amendment B — `δ_i` 를 limiter ID 에 고정하지 않는다 (결과 전 동결)

limiter 0 이 링의 특정 방위에 늘 있는데 거기 항상 `−Δ` 를 주면 *"북쪽 = early
pressure, 남쪽 = reserve"* 처럼 **공간 역할까지 동시에 추가**된다. 그러면 HK 가
올라가도 **temporal diversity 때문인지 특정 spatial slot 에 특정 timing 을 준
것 때문인지 분리되지 않는다.**

규칙: 네 timing slot `{−Δ, −Δ/3, +Δ/3, +Δ}` 를 **에피소드마다 사전 고정된 balanced
permutation** 으로 4 기에 배정한다.

- 24 개 permutation 을 **episode index 로 순환** (`PERMS[ep % 24]`)
- **같은 에피소드에서 Δ=0.125 와 0.25 는 동일 permutation** 을 쓴다
- 캠페인 전체에서 모든 spatial limiter 가 early/mid/late/reserve 를 거의 같은 횟수
- permutation 규칙은 **결과와 무관하게 사전 고정** (본 문서가 그 고정이다)

⇒ arm 사이에서 실질적으로 변하는 것은 **temporal-spread amplitude Δ 하나**가 된다.

**Δ 사전 선언 (튜닝 금지)** — E3 관측 자연 spread 에 앵커:
```
Δ ∈ { 0,  0.125,  0.25 } s
  0      : baseline. **bit-exact 회귀 대상** (실패 시 즉시 중단)
  0.125  : 총 spread 2Δ = 0.25 s = 관측 range(t_min) 0.125 s 의 **2 배**
  0.25   : 총 spread 0.5 s = **4 배**
```
상한 근거: 공격자가 링 영역(폭 ~10 m)을 19 m/s 로 통과하는 시간 ~0.5 s.
*"잘 나오는 Δ"* 를 찾는 탐색은 하지 않는다.

## 20.4 Primary = **mechanism**, 그 다음 outcome

**HK 를 headline 으로 두지 않는다.** 먼저 개입이 실제로 걸렸는지 본다.

1. **Primary (mechanism)**: `range(t_min,i)` — baseline 0.125 s 대비 유의하게 증가?
   (paired, bootstrap CI95)
2. Secondary (outcome): `P(HK)` · `P(PENETRATED)` · `P(d_min ≤ 0.75)`
3. Tertiary: net capture 변화 (§19.4 의 상보성 때문에 **함께 오른다는 보장 없음**)

## 20.5 판정표 (결과 전 동결)

| # | 조건 | 판정 |
|---|---|---|
| **S1** | `Δt_min` 이 baseline 과 거의 동일 | **controller implementation/parameterization 실패.** scientific conclusion 금지, 재구현 |
| **S2** | stagger 성공 **且** HK 증가 | *"Temporal diversification converts unused pathwise opportunity into additional physical interception."* → "single temporal layer" 진단이 **causal mechanism 으로 승격** |
| **S3** | stagger 성공 **但** HK 불변 | 시간 동기화는 문제였으나 **충분한 원인은 아님** → 다음은 spatial cutoff / inner-chord |
| **S4** | stagger 성공 **但** HK 악화 | temporal depth 가 공격자에게 더 나은 escape sequencing 을 줄 수 있다 — **그대로 수용** |

## 20.6 위치

```
4 independent chasers -> scripted temporal/spatial roles -> reactive reassignment -> learning
```
E4-1 은 두 번째 칸의 **첫 조각**이다. 아직 MARL 을 부를 단계가 아니다.
또한 E4 는 하드킬 개선 실험이면서 동시에 **"역할 분리가 실제로 state geometry 를
바꿀 수 있는가"** 를 보는 첫 scripted mechanism test 다.

---

---

# 21. E4-1 판정 — mechanism gate **NOT MET** / outcome **POSITIVE** / attribution **UNRESOLVED**

산출물: `results/e4_stagger.json` · `.log` (n=300/arm). **S2 로 쓰지 않는다.**

## 21.1 정본 판정 문구 (동결)

> **E4-1 produced a positive physical-interception effect at the interpretable
> Δ=0.125 arm (0.190 → 0.253; paired Δ = +0.063, 95% CI [+0.017, +0.110]). However,
> the preregistered mechanism criterion was not met because the paired median change
> in the quantized `range(t_min)` endpoint was exactly zero. Post-hoc distributional
> diagnostics suggest the endpoint was insensitive to heterogeneous timing shifts,
> but these diagnostics do not retroactively establish the temporal-diversification
> mechanism. The Δ=0.25 arm is excluded from pure-stagger interpretation because the
> zero-horizon clamp activated in 98% of episodes.**

## 21.2 결과

| Δ | range(t_min) med | **HK** | net | pen | clamp(ep) |
|---|---|---|---|---|---|
| 0 | 0.125 | 0.190 [0.150, 0.238] | 0.133 | 0.677 | 0.000 |
| **0.125** | 0.150 | **0.253** [0.207, 0.305] | 0.123 | 0.623 | 0.167 |
| 0.25 | 0.200 | 0.273 [0.226, 0.326] | 0.123 | 0.603 | **0.980** |

paired vs baseline:

| Δ | Δrange(t_min) *(동결 primary)* | ΔP_HK | ΔP_net |
|---|---|---|---|
| 0.125 | **+0.000** CI [0.000, 0.000] | **+0.0633** CI [+0.0167, +0.1100] | −0.0100 CI [−0.0233, +0.0000] |
| 0.25 | +0.050 CI [+0.050, +0.100] | +0.0833 CI [+0.0300, +0.1367] | −0.0100 CI [−0.0233, +0.0000] |

## 21.3 ★ endpoint sensitivity failure (자기신고)

`range(t_min)` 은 `dt=0.05` 로 **양자화**돼 있어 이산량에 paired **중앙값** 을
primary 로 둔 것이 설계 결함이다. Δ=0.125 의 paired 중앙값 0 은 33.7% 가 정확히
0 차이이기 때문이지 개입이 안 걸려서가 아니다.

**post-hoc descriptive (승격 금지)**: 증가 44.0% / 불변 33.7% / 감소 22.3%,
paired mean **+0.0253 s**, arm 평균 0.160 → 0.185 → 0.251 s.

> *"median = 0 이므로 temporal spread 가 전혀 바뀌지 않았다"* 로 읽어서도 **안 된다.**
> 정확한 기록 = **endpoint sensitivity failure 가 드러났다.**

## 21.4 clamp 격리 (Amendment A 발동)

Δ=0.25 는 **98.0% 에피소드에서 clamp**(limiter-step 8.8%). clamp 시 `t_eff = 0` 이라
조준점이 `p_att` 자체 = **pure pursuit** 성분이 섞인다.
⇒ **`horizon staggering with a zero lower bound`** 로 별도 표기하고,
**0.190 → 0.253 → 0.273 을 dose-response 로 읽지 않는다** (0.25 는 mixed intervention).

**unclamped n=250 분석은 descriptive 이상으로 올리지 않는다** — `unclamped` 여부는
**treatment 적용 후 결정되는 변수**이므로 treatment-induced subset 조건부 분석이다.
최대 표현: *"The positive HK difference is also present descriptively among episodes
in which the intervention did not encounter the zero-horizon clamp."* (0.180 → 0.248)

## 21.5 net

`ΔP_net = −0.010` CI95 [−0.0233, +0.0000]. 최대 표현:
> **The physical-interception gain was not accompanied by an observed increase in net
> capture.**

*"trade-off 를 증명했다"* 는 **아직 아니다.** §19.4 의 상보성 관찰과 **consistent** 까지.

## 21.6 과학적 소득

같은 기체·attacker·ring·contact radius·PIP family 에서 **timing target 만** 바꿔
`19.0% → 25.3%`. 따라서 최소한:

> **registered physical capability 만으로 19% 가 고정되는 것은 아니다.**

⇒ *"`a_lim = 0.35·a_att` 라 마지막 거리를 물리적으로 못 좁힌다"* 는 단순 capability
설명은 **더 약해졌다.** 다만 **왜** 25.3% 로 올랐는지는 confirmatory 하게 temporal
diversification 이라고 못 박지 못했다.

---

# 22. 후속 사다리 (E4-1b 이후, 설계만)

## 22.1 E4-1b — temporal mechanism confirm (clamp·endpoint 문제 동시 제거)

비음수 slot 으로 clamp 를 없애고, **평균 lead 를 맞춘 control** 을 둔다:

```
control  : delta_i = D/2                    (4 기 동일)
diverse  : delta_i in {0, D/3, 2D/3, D}     (동일 평균, 분산만 증가)
```
⇒ **same mean lead, different temporal dispersion** 만 비교된다.

**Primary (신규 prereg 필요 — 이번 실패를 본 뒤이므로 새 데이터에 대해)**:
`E[range(t_min)_diverse − range(t_min)_control]` = **paired mean difference (초)**.
양자화 변수에 paired median 을 다시 쓰지 않는다.
Secondary: `P(Δrange>0)`, `P(=0)`, `P(<0)`. Outcome: `ΔP_HK`.

둘 다 confirm 되면 그때 *"Temporal diversification causally improves physical
interception under the tested T1 configuration."* 까지 갈 수 있다.

## 22.2 E4-2 → E4-3 → T2 → MARL → B2

```
E4-2  spatial role separation / cutoff (pressure · inner-chord cutoff · second cutoff · reserve)
      질문: 간 길을 따라가는 대신 길목을 선점하면 동일 capability 에서 추가 이득이 생기는가
E4-3  temporal + spatial 조합 = **strong scripted cooperative baseline**
      ★ MARL 이 반드시 넘어야 할 기준선. naive all-chase 를 MARL baseline 으로 쓰면 안 된다
T2    동일 scripted defender · attacker 만 T1 -> T2. fixed role 이 깨지는가
      안 깨짐 -> 학습 필요성 약함 / 깨짐 -> **adaptive role allocation** 문제 발생
MARL  목표 = "4 기가 협력해서 잡아라" 가 아니라 **online role allocation / reassignment**
      순서 (D_scripted,T1) -> (D_MARL,T1) -> (D_MARL,T2)
B2    net track — outcome 을 HK 로 두지 않는다. P(F) · P(C|F) · ax · cone slack ·
      commit-state certificate. limiter 의 목적은 하드킬이 아니라 z_encounter -> C_net
```

**우선순위**: `E4-1b → E4-2 → T2` 까지만 먼저. 여기서 scripted mechanism 이 안 서면
MARL 은 다시 미룬다. **KSAS 는 이 사다리를 기다리지 않는다** — 현재 modality-gap /
commit-feasibility 선에서 닫고, 사다리는 arXiv/AIAA 의 cooperative-control 절반이 된다.

---

# 23. modality gap — claim level 3 분

| Level | 내용 | 상태 |
|---|---|---|
| **1** | `P_net(a) ≠ P_HK(a)` 이고 두 성공곡선의 regime 의존성이 크게 다르다 | **확립** |
| **2** | net 이 붕괴한 BAND/high-χ 에서도 physical interception 이 상당수 존재 (BAND 0.6% vs 23.4%) | **강하게 지지** (E2-B prospective counterfactual 포함) |
| **3** | 동일 commit state `z` 에서 `z ∉ C_net ∧ z ∈ C_physical` | **미확립** — state-conditioned counterfactual 필요 |

**정본 표현**:
> **A pronounced modality gap was observed: as target maneuverability increased,
> non-destructive net capture collapsed while physical contact interception remained
> substantial. A prospective sham-net counterfactual showed that this separation was
> not caused by net capture censoring subsequent hard-kill opportunities.**

**금지**: *"We prove that every state outside the net-capture set remains kinetically
interceptable."* / `C_net ⊊ C_physical` 을 **state-wise 명제**로 서술.

**용어**: `set inclusion` 이 아니라 **modality separation / modality gap**.
E3 (CAPTURED 40 건 oracle 가능 0/4 vs 침투 4/4) 때문에 최종 그림은 포함관계보다
**부분적으로 상보적인 operating regions** 쪽이다.

**χ≥1 은 별도**: analytic claim (stated single-shot escape model 의 necessary
condition) 이고, `0 net vs 24.3% HK` 는 closed-loop outcome separation 이다.
**둘을 합치되 동일 증거라고 하지 않는다.** `0/1598` 을 물리적 불가능성의 실측 검증으로
읽는 것은 금지 (C032 gate censoring).

---

---

# 24. E4-1b 사전등록 — matched-mean temporal dispersion (동결본, 미실행)

§21 이 남긴 문제 둘을 **동시에** 제거한다: (a) zero-horizon clamp, (b) 양자화된
endpoint 에 paired **median** 을 primary 로 둔 설계 결함.
**이번 실패를 본 뒤이므로 새 데이터에 대해 새로 prereg 한다.**

## 24.1 질문

> **평균 lead 는 같은데 시간 분산만 늘리면 physical interception 이 올라가는가?**

## 24.2 설계 — same mean lead, different temporal dispersion

```
D = 0.25 s (고정)
control  : delta_i = D/2 = 0.125          (4 기 동일)
diverse  : delta_i in {0, D/3, 2D/3, D}   (평균 = 0.125 로 **동일**)
```
- 모든 δ ≥ 0 이므로 `t_lead + δ ≥ 0` → **clamp 가 구조적으로 발생하지 않는다**
  (Amendment A 발동 불가). 그래도 clamp 계수를 보고해 0 임을 확인한다.
- diverse 의 slot 배정은 §20 Amendment B 그대로 **balanced permutation**
  `PERMS[ep % 24]`. control 은 배정 자체가 무의미(전부 동일).
- **평균 horizon 이 같으므로** arm 차이는 **temporal dispersion 하나**다.

## 24.3 Primary (신규 — 양자화 대응)

```
primary = E[ range(t_min)_diverse − range(t_min)_control ]     ★ paired MEAN (초)
          + bootstrap CI95 (에피소드 재표집, 20000, seed 0)
```
**양자화 변수에 paired median 을 다시 쓰지 않는다** (§21.3 결함의 직접 대응).

Secondary (기록 의무): `P(Δrange > 0)` · `P(= 0)` · `P(< 0)`.
Outcome: `ΔP_HK` (paired + CI). Tertiary: `ΔP_net`.

## 24.4 판정 (결과 전 동결)

| # | 조건 | 판정 |
|---|---|---|
| **M1** | primary CI 가 0 제외(>0) **且** ΔP_HK CI 가 0 제외(>0) | ★ *"Temporal diversification causally improves physical interception under the tested T1 configuration."* — **temporal layering 이 causal mechanism 으로 확립** |
| **M2** | primary >0 **但** ΔP_HK CI 가 0 포함 | 분산은 만들었으나 **성능 이득 미확립** → 다음은 spatial cutoff (E4-2) |
| **M3** | primary CI 가 0 포함 | 개입이 실제 dispersion 을 만들지 못함 → **구현/파라미터 실패**, scientific conclusion 금지 |
| **M4** | primary >0 **且** ΔP_HK <0 (CI 가 0 제외) | temporal depth 가 공격자에게 순차 회피 여지를 준다 — **그대로 수용** |

## 24.5 고정

세계 = E2-A 동일 (ratified · T1 route 0.5/sense 30 · intercept · baseline_commit).
n=300/arm. 물리·ring·contact radius·PIP family·limiter 수·sensing 전부 불변.

---

---

# 25. E4-1b 판정 — **M4**: dispersion 확립, 그러나 HK **악화**

산출물: `results/e4b_matched.json` · `.log` (n=300/arm).

| | control (δ=0.125×4) | diverse ({0,⅓D,⅔D,D}) | paired Δ |
|---|---|---|---|
| **range(t_min)** *(primary, MEAN)* | 0.1335 s | 0.1757 s | **+0.0422** CI95 [+0.0240, +0.0615] |
| **P_HK** | 0.3633 | 0.2967 | **−0.0667** CI95 [−0.1167, −0.0133] |
| P_net | 0.1167 | 0.1167 | +0.0000 CI95 [−0.0167, +0.0167] |
| clamp | 0.000 | 0.000 | §24.2 구조적 예측 확인 |

secondary: Δ>0 50.0% / =0 33.0% / <0 17.0%.

## 25.1 정본 문구 (범위 한정)

> **At the registered mean lead and dispersion pattern, increasing temporal
> dispersion reduced physical interception.**

**금지**: *"temporal diversity 는 일반적으로 나쁘다"*.

## 25.2 E3 진단의 처방이 반증됐다

> **temporal synchronization 은 관찰된 failure phenotype 이지 causal bottleneck 이
> 아니었다.**

조작(`Δrange = +0.0422`, CI 가 0 배제)은 **성공**했는데 결과는 반대로 갔다. 따라서
E3 의 *"single temporal layer → layer 를 벌리면 해결"* 이라는 처방은 **반증**이다.
E3 의 §19.3 최대 표현(unused pathwise opportunity)은 여전히 유효하다 — 기회가 있다는
관찰과, 그 기회를 시간 분산으로 회수할 수 있다는 처방은 별개다.

## 25.3 ★ 새 가설 (결과를 본 뒤 생김 — confirmatory 아님)

E4-1b **control** (δ=0.125 균일, 분산 0) 의 HK 가 **0.363** 으로, E4-1 baseline
(δ=0 균일) **0.190** 보다 크게 높다. 또 E4-1 의 sym arm 은 명목 평균 δ=0 이지만
음수 쪽 clamp 때문에 **실효 horizon 평균이 양수로 밀렸을** 가능성이 있다.

⇒ 지금까지 결과가 일관되게 가리키는 방향:
> **"여러 시점으로 분산" 보다 "조금 더 앞을 본다"**

**단 이것은 cross-campaign 비교이므로 causal evidence 가 아니다.** §26 이 이를 닫는다.

---

# 26. E4-1c 사전등록 — uniform lead sweep (동결본, 미실행)

## 26.1 질문

> **Does uniformly increasing prediction horizon improve physical interception under
> otherwise identical pursuit control?**

`δ_i = δ ∀i` 이므로 **temporal dispersion 이 구조적으로 0** 이고, 변하는 것은
prediction horizon 하나뿐이다.

## 26.2 설계

```
delta_i = delta  (4 기 동일),  delta in {0, 0.125, 0.25} s
```
- δ ≥ 0 이므로 clamp 구조적 불가 (그래도 계수해 0 확인).
- permutation 불필요 (전부 동일).
- 세계·물리·attacker·ring·contact radius·PIP family 전부 §20.2 와 동일.

**★ fresh seed block 규율**: 이 가설은 **E4-1b 결과를 본 뒤** 생겼다. 따라서 기존
E4-1b control 을 재사용해 confirmatory 라고 부르지 않는다. **세 arm 모두 새 실행** 하고
**미사용 에피소드 대역 `30000..30299`** 를 쓴다 (기존 0.. / 10000.. IID 와 분리).

## 26.3 Primary / Secondary

**Primary = paired `P_HK`** (mechanism proxy 검정이 아니라 **lead horizon 자체의 causal
axis** 검정이므로). paired + bootstrap CI95.
Secondary: `d_min_best` 분포 · `P_PEN` · 실효 조준 horizon 평균 · `P_net`.

## 26.4 판정 (결과 전 동결)

| # | 조건 | 판정 |
|---|---|---|
| **U1** | `P_HK(0.125) > P_HK(0)` (CI 0 배제) | **under-leading hypothesis supported** — 기존 PIP 가 너무 가까운 미래를 겨냥하고 있었다 |
| **U2** | `P_HK(0.25) > P_HK(0.125) > P_HK(0)` | 검정 범위에서 **longer lead benefit** |
| **U3** | `P_HK(0.125) > P_HK(0)` **且** `P_HK(0.25) ≤ P_HK(0.125)` | **intermediate optimum / over-leading** |
| **U4** | 세 arm 차이 없음 (CI 전부 0 포함) | E4-1b 의 0.363 은 **campaign effect 또는 다른 구조적 차이** |

## 26.5 이후 연결

U1~U3 이면 최적 δ 를 **frozen strong pursuit baseline** 으로 고정하고, E4-2 의
**control** 로 쓴다. 그래야 E4-2 가 *"naive 19% 를 이겼다"* 가 아니라
**"이미 30%대인 competent pursuit 을 spatial role separation 이 추가로 이기는가"** 를
묻게 된다.

---

*연관: 반증 아티팩트 = results/slew_counterfactual.json · 원 주장 = docs/45 §9 · 반사실 출처 = docs/51 §9 · 순서 규율 = docs/81 · 미팅 브리핑 = docs/82 · 감사 = artifacts/audits/environment_numeric_audit_2026-08-13.md · R1/R2 계약 전례 = docs/54*

---

# 27. E4-1c 판정 — **U3 (intermediate optimum / over-leading)** [§26.4 동결 규칙 적용]

실행: `bdd5931` · `results/e4c_uniform.json` (+ `.log`) · fresh seed `30000..30299` · n=300/arm.
판정은 스크립트가 §26.4 표를 그대로 적용해 산출했다 (`verdict` 필드).

## 27.1 결과

| δ (uniform) | P_HK | Wilson 95% | P_net | P_PEN | paired ΔP_HK vs 0 | clamp |
|---|---|---|---|---|---|---|
| 0.000 | 0.1767 | [0.138, 0.224] | 0.1767 | 0.6467 | — | 0.000 |
| **0.125** | **0.3667** | [0.314, 0.423] | 0.1267 | 0.5067 | **+0.1900 [+0.1333, +0.2467]** | 0.000 |
| 0.250 | 0.3133 | [0.263, 0.368] | 0.1000 | 0.5867 | +0.1367 [+0.0633, +0.2067] | 0.000 |

paired 0.250 vs 0.125: **−0.0533 CI95 [−0.1200, +0.0100]** — 0 포함.
→ U1 충족 **且** `P_HK(0.25) ≤ P_HK(0.125)` → **U3**.

clamp 는 세 arm 모두 정확히 0 (δ ≥ 0 이므로 **구조적으로 불가**). E4-1 의 Amendment A
오염(16.7% / 98%)이 이 실험에는 존재하지 않는다.

## 27.2 기전 귀속 — E4-1b 와 합쳐 읽는다

주입된 temporal dispersion 은 **구조적으로 0** 이다 (네 limiter 가 동일 δ). 잔존
`range(t_min)` 중앙값 0.100~0.150 s 는 공간 배치에서 오는 **내생적** 산포이지 처치가
아니다. 그럼에도 P_HK 가 0.177 → 0.367 로 **거의 두 배**가 된다.

E4-1b 는 mean 을 맞춘 상태에서 dispersion 을 넣었을 때 **ΔP_HK −0.0667** [−0.1167,
−0.0133] 로 오히려 악화됨을 보였다 (§25, M4). 두 결과를 합치면 귀속은 하나로 좁혀진다:

> **E4-1 계열의 이득은 temporal dispersion 이 아니라 평균 lead horizon 의 이동에서
> 온다. 동결 baseline 의 constant-bearing PIP 해는 jinking 표적에 대해 체계적으로
> under-lead 하고 있었다.**

## 27.3 modality trade (secondary)

δ 가 커질수록 P_net 은 단조 감소한다 (0.177 → 0.127 → 0.100). 방어 성공 합계
(P_HK + P_net) 는 0.353 / **0.493** / 0.413 로 δ=0.125 가 두 축 모두에서 최적.

## 27.4 허용 / 금지 표현

- 정본: *"A one-dimensional recalibration of the pursuit lead horizon (δ = 0.125 s,
  applied uniformly with zero injected temporal dispersion) nearly doubled hard-kill,
  0.177 → 0.367. Combined with the matched-mean result of E4-1b, the effect is
  attributable to the mean lead horizon, not to temporal diversification."*
- **금지**: "학습된 정책" / "temporal staggering 이 유효했다" / "지역수비를 구현했다".
  δ 는 **고정 휴리스틱의 스칼라 하이퍼파라미터**이지 학습 산물이 아니다.
- **자기신고 한계 (중요)**: 이전 모든 baseline (C034·C035 포함) 은 **자기 튜닝
  최적점이 아닌 운용점**에서 측정됐다. "19% 는 능력 상한" 류 서술은 이 사실만으로도
  약화된다. 반대로 E4-2 는 이 δ=0.125 arm 을 control 로 써야 하며, naive 0.19 를
  이겼다는 서술은 금지한다 (§26.5).

## 27.5 다음 연결 (동결)

**frozen strong pursuit baseline := uniform δ = 0.125 s, P_HK 0.367 [0.314, 0.423]**
(seed block 30000..30299). E4-2 의 control 은 이것이다.

---

# 28. E1d 판정 — **primary 예측 REFUTED (방향 반대)** [§15.5 동결 규칙 적용]

실행: `bdd5931` · `results/e1d.json` (+ `.log`) · n=300/arm · 제외 0 · 발사 300/300 (세 arm).

## 28.1 동결 primary

> `a*₅₀(D-b) > a*₅₀(D-a)`

| arm | target ax | ideal aim | ax_realized med | ψ@commit med | P(capture) | **a*₅₀** | reference benchmark |
|---|---|---|---|---|---|---|---|
| D-a | 6.5 | ✓ | 6.4913 | 0.00° | 0.240 [0.195, 0.291] | **29.95** | 31.06 |
| D-b | 8.0 | ✓ | 7.8914 | 0.00° | 0.040 [0.023, 0.069] | **정의 불가** | 37.76 |
| D-c | 8.0 | ✗ (ω=∞) | 7.9185 | 3.50° | 0.040 [0.023, 0.069] | **정의 불가** | 37.89 |

D-b 의 `cross50` 은 `nan` 인데, 이는 결측이 아니라 **어느 a-bin 에서도 포획률이 0.5 에
도달하지 않기 때문**이다 (bin별 [0.385, 0.077, 0, 0, 0, 0, 0, 0]). 축방향 footprint 를
6.49 → 7.89 m 로 키우자 포획이 **0.240 → 0.040 으로 6 배 붕괴**했다.

→ **primary 예측 REFUTED.** 방향이 예측과 반대이며, 경계가 넓어진 게 아니라 소멸했다.

## 28.2 D-a 는 benchmark 와 일치한다

D-a 의 a*₅₀ 29.95 vs reference benchmark `2·ax·tanθ/τ²` = 31.06 (**−3.6%**). 즉 국소
cone 기하는 **현 운용점 근처에서는 맞는다**. 실패한 것은 그 식의 **외삽**이다.

## 28.3 지배 제약 규명 (**사후 — 결과를 본 뒤 도출**)

포획 조건은 도달집합 ⊂ (cone ∩ [range_min, range_max]) 이다. benchmark 식은 **측방
(각도) 항만** 담고 **축방향 far-edge 절단을 누락**한다.

| arm | 측방여유 `ax·tanθ` | **축방향여유 `R_max − ax`** | 도달반경 `½aτ²` | 축방향 binding 비율 |
|---|---|---|---|---|
| D-a | 1.398 m | 1.729 m | 2.038 m | 0.610 |
| D-b | 1.699 m | **0.329 m** | 2.038 m | **0.963** |
| D-c | 1.705 m | **0.302 m** | 2.038 m | **0.963** |

개입이 ax 를 R_max = 8.22 m 쪽으로 밀면서 축방향 여유가 1.73 → 0.33 m 로 줄었고,
지배 제약이 **측방 → 축방향**으로 갈아탔다. 보정 법칙:

> **a\* = 2·min(ax·tanθ, R_max − ax) / τ²**,  내부 최적 **ax\* = R_max/(1+tanθ) = 6.764 m**
> (그 지점의 상한 a\*_max = **32.37**)

에피소드 단위 예측 정확도 (`captured` 대비):

| arm | 기존 식 | **보정 식** |
|---|---|---|
| D-a | 0.987 | **0.993** |
| D-b | 0.670 | **0.997** |
| D-c | 0.663 | **0.997** |

D-b 의 보정 a*₅₀ 중앙값은 **7.30** — THREAT_BRACKET 하한 11 보다 낮다. 그래서 전 구간
포획 ≈ 0 이 되고 `cross50` 이 정의되지 않는다. 관측된 잔여 0.040 은 `ax_realized` 가
작게 실현된 에피소드들이다 (포획군 ax med 7.38 · 축방향여유 0.840 vs 비포획군 7.91 ·
0.313).

## 28.4 D-c 는 **설계상 무효** — pointing 비용의 null 증거가 아니다

D-c(ψ 3.50°) 와 D-b(ψ 0°) 는 **300/300 라벨 동일 · 포획 에피소드 집합 동일**이다
(`ax_realized` 는 98/300 에서 다르므로 궤적 자체는 갈렸다). 원인은 §28.3 이다: ψ=3.50°
가 만드는 측방 편차는 약 0.48 m 인데, 축방향으로 이미 1.7 m 부족한 상태라 **축방향
실패가 포화되어 측방 차이를 가려버린다**.

따라서 D-c 로부터 *"slew cap 을 없애도 남는 pointing 비용은 0"* 을 읽으면 **안 된다**.
정확한 진술은 *"이 운용점에서는 pointing 축이 binding 축이 아니었다"* 이다. E1b 의
결론과 방향은 같지만 **이유가 다르다** (E1b = fire gate 차폐, E1d = 축방향 포화).

## 28.5 허용 / 금지 표현

- 정본: *"The registered directional prediction was refuted: moving the forced commit to
  a larger axial footprint collapsed net capture (0.240 → 0.040) rather than widening the
  boundary. The local cone-geometry benchmark reproduced the boundary at the near
  operating point (29.95 vs 31.06) but failed to extrapolate, because it omits the
  far-edge range truncation that becomes binding as ax → R_max."*
- **금지**: "ax 가 유일한 원인" / D-b·D-c 의 낮은 포획률을 **시스템 성능**으로 읽기
  (perfect aim 은 실현 불가능한 반사실) / D-c 를 "pointing 비용 없음" 의 증거로 쓰기 /
  보정 법칙을 **확립된 결과**로 서술하기.
- **보정 법칙의 지위 = 사후 가설.** 세 arm 모두에서 0.99+ 로 맞지만, 이 데이터에서
  도출됐으므로 **fresh seed 확인 실험 전에는 승격 금지**.

## 28.6 다음 연결

**E1e (미실행 · 사전등록 필요)**: 보정 법칙의 내부 최적 예측을 새 seed 대역에서 검정.
`ax ∈ {5.5, 6.76, 7.5}` 3 arm, ideal aim 고정, primary = *"a*₅₀ 가 ax=6.76 에서 최대이고
양쪽에서 감소한다"* (역U자). 예측 상한 32.37. 이건 **결과를 본 뒤 만든 가설**이므로
seed 대역 `31000..31299` 를 쓴다.

---

# 29. R4 계약 — 근접거리 측정계 수리 (사전등록 · 결과 전 동결)

발견 경로: E4-1c 궤적 뷰어(§27 후속). 상세 = `temp_research_note/2026-08-14_...md` §4.

## 29.1 결함 (확정)

소진 limiter 는 `env_sys` §5 에서 **`[0,0,60]` 으로 주차**된다. 진단 루프들이 **주차 직후**
post-step 좌표로 거리를 재므로, **접촉이 일어난 바로 그 스텝의 최소거리가 63 m 로
대체**된다. 결정적 프레임이 계통적으로 소실된다.

`_Driver.step` 의 자체 swept 진단(`recoverability_probe.py:134-143`)도 **같은 결함**을
갖는다 — (i) `i in self.se.retired` 를 스텝 **이후**에 판정해 접촉한 바로 그 limiter 를
제외하고, (ii) `env._p(lims2[i])` 가 이미 주차 좌표다. 따라서 "이미 올바른 구현이
있다" 는 §4 서술은 **부정확**하며, 수리는 driver 를 포함한다.

**모순 증거 (이미 관측)**
- E3: 하드킬 57 건 중 **44 건**이 `d_min_best > r_contact` — 접촉 킬은 정의상 불가능
- E4-1c: `p_reach < P_HK` 가 **세 팔 전부**

## 29.2 계약

**권위 측정은 하나다.** `_resolve_contacts` 가 쓰는 것과 **동일한 술어·동일 입력**:

    d_swept[i] = _seg_min_dist(p_att_pre - lims_pre[i], p_att_post_raw - lims_post_raw[i])

- `*_raw` = **주차 이전** post-step 좌표. `env_sys` §4 (`lims2/att2` 취득 직후, §5 주차
  **이전**) 에서 `self.lims_post_raw` / `self.p_att_post_raw` 로 기록한다. 순수 기록이며
  물리·순서·난수에 개입하지 않는다.
- 제외 대상은 **스텝 시작 시점에 이미 retired 인 limiter** (`retired_pre` 스냅샷).
  이번 스텝에 retire 된 limiter 는 **포함**한다 — 바로 그게 측정 목표다.
- `_Driver` 가 per-limiter `d_min[i]` / `t_min[i]` 를 보유하고, 호출부는 **자체 거리
  루프를 만들지 않고** 이를 읽는다 (재발 방지).
- 커밋 경로로 해소·주차되는 limiter 는 접촉 record 가 없어 권위값이 없다. 해당 스텝은
  그 limiter 에 한해 **측정 불가로 표기하고 카운트를 보고**한다 (무언의 절단 금지).

## 29.3 회귀 게이트 (4/4 통과 전 재실행 금지)

| # | 게이트 | 취지 |
|---|---|---|
| **R4-A** | **기본 동작 bit-exact** — 라벨·`P_HK`·`P_net`·`P_PEN` 및 records JSON 이 수리 전후 완전 동일 | 수리가 **결과를 바꾸지 않음**을 먼저 증명. 실패 시 즉시 중단 |
| **R4-B** | `source="contact"` 인 모든 record 에서 `d_swept[i] ≤ r_contact + ε` (ε=1e-9), 그리고 그 값이 `rec.d_nom` 과 **부동소수 동일** | 권위 측정이 해소기와 같은 수를 낸다 |
| **R4-C** | **retirement 가 없는 에피소드**에서 구 diagnostic 과 R4 diagnostic 이 bit-exact | 수리가 **주차 오염만** 제거했음을 증명 (범위 한정) |
| **R4-D** | 캠페인 수준 `p_reach ≥ P_HK_contact` | §29.1 의 모순이 실제로 해소됐는지 |

R4-A 가 최우선이다. 실패하면 수리가 물리에 샌 것이므로 중단한다.

## 29.4 영향 claim (재평가 대상 · 결과 전 목록 동결)

**살아 있음 (재검증 불필요)**: 모든 라벨·결과확률. 따라서 E1·E1b·E1c·E2-B·E1d 의 primary,
그리고 **E4-1c 의 primary `P_HK`** (U3 판정 포함) 는 영향 없다.

| claim / 판정 | 조치 |
|---|---|
| **C034** `P(d_actual≤0.75)=0.043` vs oracle 0.883 | **숫자 정정 필수.** 참값 ≥ 0.190. oracle 측은 `p_L0+v_L0·t` 라 무영향 → 격차가 **actual 쪽에서만** 과장됐다 |
| **E3 paired Δd · `t_min` synchronization** (§19) | 재계산. "spatially diversified but temporally synchronized" 재평가 |
| **E4-1 primary `range(t_min)`** (§21, C035) | 재계산. 기존 양자화 결함 위에 중첩 |
| **E4-1b M4** (§25) | **`PENDING R4 REVALIDATION` 으로 강등.** outcome `ΔP_HK = −0.0667` [−0.1167,−0.0133] 은 살아 있으나, *"dispersion 을 성공적으로 늘렸는데 HK 가 떨어졌다"* 는 **기전 문장**은 등록 primary 가 `range(t_min)` 이었으므로 R4 후에만 재확정 가능. R4 후 `ΔE[range(t_min)] > 0` 유지 → M4 완전 복원, 아니면 outcome-negative 만 남기고 기전 귀속 철회 |
| **lead-time §17 "closest approach 1.4–1.7 m"** | **철회 또는 정정.** ep30008 의 접촉 직전값이 정확히 1.509 |
| E4-1b/E4-1c `d_min_best`·`p_reach` secondary | 재계산 |

## 29.5 재실행 목록 (동결)

**E3 · E4-1 · E4-1b · E4-1c · lead-time diagnostic.** 각 실험의 **원 seed 대역·원 n** 을
그대로 쓴다 (새 표본이 아니라 **같은 표본의 재측정**이다). R4-A 가 라벨 불변을 보장하므로
결과확률은 기존 값과 일치해야 하며, **불일치는 그 자체로 실패**다.

## 29.6 금지

- 이 계약을 이유로 **동결된 판정을 소급 수정하지 않는다**. 정정은 §30 에 **새로** 기록한다.
- 재측정 결과가 서술을 강화하는 방향이어도 **원 문장을 고쳐 쓰지 않고** 정정 항목으로 남긴다.
- 수리 과정에서 물리·순서·난수·기본값을 건드리지 않는다 (R4-A 가 강제).

---

# 31. T1-R 축대칭 semantic audit — **판정 A: T1-R 취소** (결과 미열람 상태에서 수행)

질문: defender ring 을 x 축 둘레로 회전했을 때 `F(R_x s, R_x a) = R_x F(s, a)` 인가.
만족하면 φ₀ randomization 은 새 물리 조건이 아니라 **좌표계 relabeling** 이다.

회귀 = `tests/test_t1_symmetry_audit.py` (6/6). **결과를 보기 전에** 수행·기록.

## 31.1 정확히 공변인 축

| 축 | 근거 | 메타모픽 |
|---|---|---|
| 차량 동역학 | `‖a‖≤a_max` · `‖v‖≤v_max` **등방 노름 클램프**. 중력·바닥·z 제약·고도 clamp **없음** (`sim/analytic.py:120-126`) | 소스 계약으로 고정 |
| 감지 | 3D 유클리드 `‖c−p_att‖ ≤ sense_range` (수평 range 아님, `attacker_ladder.py:206`) | 0/1200, max 1.4e-14 |
| limiter PIP | 상대벡터 노름만 사용 | 0/1200, max 3.3e-13 |
| 종말 기하 | 침투 = `‖p_att−target‖ ≤ target_radius` — **구면** (`env.py:354`) | 해석적 |
| 고정 기하 | 표적 원점 · finisher `[2,0,0]` · ring 중심 `[8,0,0]` — **전부 x 축 위** | 해석적 |

## 31.2 점별로는 깨지지만 **게이지**인 축 — jink

`_jink_accel` 은 `ref = ẑ` 로 횡평면 basis 를 만든다 (`u = unit(fwd × ẑ)`). ẑ 는 R_x 불변이
아니므로 **점별 공변성은 800/800 전부 위반** (max err 35.9).

그러나 이는 **gauge artifact** 다:
- `(u, w)` 는 fwd 에 수직인 평면의 **임의 basis 선택**이다.
- `fwd = −x̂` 에서 `(u, w) = (ŷ, −ẑ)` 이므로 **`R_x(φ) d(ang) = d(ang − φ)`** — 회전은
  위상 이동과 정확히 같다 (회귀에서 <1e-9 로 복원 확인).
- 위상 `ψ = derive_phase(seed, episode)` 는 **[0, 2π) 균일**이다. 균일분포는 이동에
  불변이므로 **jink 방향의 분포는 횡평면에서 균일 = R_x 불변**.

## 31.3 스폰 분포도 R_x 불변

기본 `SpawnSpec`: `azimuth = 0.0` (접근 방위 섹터 없음) · `psi = 0.0` (속도 각오차 없음) ·
횡오프셋 `r_lat = 5.0` = **y-z 균일 원반**. 원반은 R_x 불변 분포다.

따라서 **(공격자 초기상태, jink 위상) 의 결합분포가 R_x 불변**이다.

## 31.4 유일하게 남는 진짜 비등방성 — route tie-break

`_route_accel` 의 동률 tie-break 3 차 기준이 **"세계 +z 선호"** 다. 코드 주석이 선택 이유를
명시한다: *"세계 +z 는 y-mirror 와 **z-회전** 양쪽에 불변이므로 공변 tie-break 다."*
즉 **이 세계는 z-회전 공변성을 겨냥해 설계됐고**, T1-R 이 노리는 x-회전에서는 +z 가 불변이
아니다. 발생률 **1/800 (0.125 %)** — 공면 퇴화 근방에서만 발동.

## 31.5 판정

> **A — T1-R 은 (≈0.1 % tie-break 항을 제외하면) 좌표계 relabeling 이다.**

ring 을 φ₀ 로 회전한 세계의 결과분포는 원 세계와 같다: 모든 동역학이 R_x 공변이거나
(jink) 균일위상으로 흡수되는 gauge 이고, 공격자 초기분포 자체가 R_x 불변이며, 고정 기하는
전부 회전축 위에 있다. 따라서 **T1-R 은 robustness 증거를 만들지 못한다 → 취소.**

## 31.6 대신 열어야 할 축 (relative geometry 를 실제로 바꾸는 것)

게이지가 아닌 축은 **회전축 위의 고정 기하나 링의 90° 대칭을 깨는 것**이다:

| 후보 | 왜 게이지가 아닌가 | 비용 |
|---|---|---|
| **`SpawnSpec.azimuth > 0`** (접근 방위 섹터, ẑ 둘레) | ring 은 y-z 평면에 있어 **R_z 에 불변이 아니다**. 공격자 접근만 ẑ 로 돌리면 ring 대비 상대기하가 실제로 바뀐다. **이미 선언된 계약 파라미터** | 최저 |
| ring 반경 (5 m) | 상대 스케일 변경 | 낮음 |
| ring standoff (중심 x=8) | 교전 개시 거리 변경 | 낮음 |
| ring 90° 대칭 파괴 (비균일 배치) | 이산 대칭군 자체를 바꿈 | 중간 |

**권고**: E4-2 의 "고정 기하 착취" 우려를 막는 목적이라면 **`azimuth`** 가 정답이다 —
가장 싸고, 이미 계약에 선언돼 있으며, 게이지가 아니다.

## 31.7 방법론 교훈 (§29 와 함께)

R4 에서 `_Driver.step` 도 같은 결함이었다는 발견과 합쳐서 원칙을 갱신한다:

> **"권위 구현 하나를 재사용하면 안전하다" 가 아니라 "권위 *계약* 하나를 회귀로 강제한다".**

대칭 가정도 마찬가지다. "코드를 읽어보니 대칭 같다" 는 근거가 되지 못하며, 메타모픽
회귀로 고정해야 한다 — 실제로 이번에도 **점별 위반 800/800** 이라는 겉보기 결과가
gauge 였고, 진짜 breaker 는 1/800 짜리 tie-break 였다.

---

# 30. R4 정정 기록 (§29.6 규율: 소급 수정 없이 **새로** 기록)

실행 `7f1a925` · 결과 `13aad22` · 원 seed/원 n 그대로 재측정 (`results/*_r4.json`).

## 30.0 §29.5 게이트 — **PASS**

2400 에피소드 (E3 300 · E4-1 900 · E4-1b 600 · E4-1c 900) 전부 **라벨 불일치 0**.
결과확률이 원 값과 완전히 일치한다. 수리가 물리에 개입하지 않았음이 캠페인 수준에서
확인됐다 (회귀 R4-A 의 캠페인 확장).

## 30.1 C034 — 숫자 정정 (질적 방향은 생존)

| | 원본 | **R4** |
|---|---|---|
| `P(d_actual ≤ 0.75)` | 0.0433 | **0.1900** |
| 하드킬 중 `d_min_best > 0.75` | **44/57** (논리적 불가) | **0/57** |
| `P(d_oracle ≤ 0.75)` | 0.8833 | 0.8833 (무영향) |
| `E[reachable]` | 2.837 | 2.837 (무영향) |

oracle 은 `p_L0 + v_L0·t` 로 계산돼 주차와 무관하므로 **격차는 actual 쪽에서만 과장**돼
있었다. 정정 후 격차 = **0.190 vs 0.883**. 4.4 배 차이지만 **결론은 바뀌지 않는다** —
사용되지 않은 pathwise 요격 기회가 여전히 크다.

## 30.2 E3 temporal synchronization — 생존 (약간 강화)

`range(t_min)` 중앙값 0.125 → **0.150 s**, `≤ 0.3 s` 비율 0.953 (양쪽 동일).
*"spatially diversified but temporally synchronized"* 는 **유지**된다.

## 30.3 E4-1 등록 primary — 판정 무변화

| | 원본 | R4 |
|---|---|---|
| paired median Δrange(t_min), D=0.125 | +0.0000 CI [0,0] | **+0.0000 CI [0,0]** |
| (참고) paired mean | +0.0253 | +0.0232 |

**mechanism gate 는 여전히 NOT MET.** 원인은 주차 오염이 아니라 **dt 양자화** 였고 (기존
자기신고), R4 가 이를 구제하지 않는다. §21 판정 *"gate NOT MET / outcome POSITIVE /
attribution UNRESOLVED"* 는 **그대로 유효**하다.

## 30.4 E4-1b M4 — **완전 복원** (PENDING 해제)

| | 원본 | **R4** |
|---|---|---|
| paired mean Δrange(t_min) (diverse − control) | +0.0422 [+0.0240, +0.0615] | **+0.0442 [+0.0248, +0.0643]** |
| ΔP_HK | −0.0667 | **−0.0667** (무영향) |

등록 primary 가 R4 후에도 **strictly > 0** 이므로, §29.4 에서 강등했던 기전 문장
*"actual temporal dispersion 을 성공적으로 늘렸는데 HK 가 떨어졌다"* 를 **복원**한다.
**M4 판정 전체가 유효**하다.

## 30.5 `p_reach` 모순 해소

| 실험 | 원본 (reach / P_HK) | R4 |
|---|---|---|
| E4-1c δ=0 / .125 / .25 | 0.050/0.177 · 0.077/0.367 · 0.120/0.313 | **0.177/0.177 · 0.367/0.367 · 0.327/0.313** |
| E4-1 D=0 / .125 / .25 | 0.043/0.190 · 0.033/0.253 · 0.073/0.273 | **0.190/0.190 · 0.250/0.253 · 0.277/0.273** |
| E4-1b control / diverse | 0.057/0.363 · 0.073/0.297 | **0.357/0.363 · 0.300/0.297** |

잔여 3 건 (`reach < P_HK`) 은 **결함이 아니다** — 커밋 경로 킬이다. 커밋은 접촉을 요구하지
않고 예측으로 해소되므로 `r_contact` 안에 들어오지 않아도 성립한다. 검증: E4-1 D=0.125
ep228 = `source='commit'`, `d_nom` 0.162 (커밋 시점 **예측** 미스), 실현 swept `d_min`
0.775, `n_unmeasured = 1` — §29.2 가 측정 불가로 선언한 바로 그 경우다.

**부수 관측 (과대해석 금지)**: C033 의 *"커밋 경로는 사실상 죽어 있다"* 는 **완전히 죽은
것은 아니다** — 커밋 킬이 실재한다. 단 관측 3 건이므로 C033 을 뒤집는 증거로 쓰지 않는다.

## 30.6 lead-time — **미교정 (자기신고)**

§29.5 재실행 목록에 넣었으나 **`lead_time_diag.py` 를 배선하지 않았다** (e3_oracle 과
e4_stagger 만 수정). 따라서 `results/lead_time_r4.json` 은 원본과 **유효숫자 6 자리까지
동일**하며, 재실행이 아니라 no-op 이었다. `closest` 의 `≤0.75` 비율이 0.043 으로 E3 원본과
같은 결함 지문을 그대로 보인다.

배선 완료 (본 커밋). 스모크: arm 24.0 ep3 HARD_KILL `closest` 0.851 → **0.423**
(`r_contact` 0.75 이하로 정상화), 라벨 불변.

> **§17 "closest approach 1.4–1.7 m 로 고정" 은 여전히 미정정 상태다.**
> lead-time 재실행 전까지 이 문장을 인용하지 않는다.

## 30.7 정정 후 유효한 문장 (정본)

- C034: *"There is substantial unused pathwise interception opportunity (P(oracle ≤ 0.75)
  = 0.883 vs P(actual ≤ 0.75) = **0.190**), but the baseline concentrates those
  opportunities into a single temporal layer."*
- E4-1: 판정 무변화 (gate NOT MET / outcome POSITIVE / attribution UNRESOLVED).
- E4-1b: **M4 전체 유효** — *"at matched mean lead, increasing temporal dispersion
  succeeded as an intervention (Δmean range(t_min) = +0.0442 s, CI95 strictly positive)
  yet reduced hard-kill (ΔP_HK = −0.0667)."*
- E4-1c: **무영향** — U3 판정과 P_HK 전부 그대로.

## 30.8 lead-time 재측정 — §30.6 의 자기신고 gap 해소

실행 `1cef791` · 결과 `d966204` · `results/lead_time_r4b.json` (원 arm 24/36/48/60, n=300).

**게이트**: (1) 라벨 1200 판 **전부 불변** · (2) no-op 재발 없음 (`closest` 동일 65/1200).
`P_HK` 도 arm 별 0.1900 / 0.2067 / 0.1767 / 0.1767 로 완전 일치.

### 정정값

| arm | `closest` med | `≤ r_contact` | 하드킬 중 `d > r_contact` |
|---|---|---|---|
| 24 | 1.482 → **1.433** | 0.043 → **0.190** | 44/57 → **0/57** |
| 36 | 1.384 → **1.235** | 0.050 → **0.207** | 47/62 → **0/62** |
| 48 | 1.495 → **1.293** | 0.047 → **0.177** | 39/53 → **0/53** |
| 60 | 1.736 → **1.667** | 0.057 → **0.177** | 36/53 → **0/53** |

`≤ r_contact` 비율이 arm 별 `P_HK` 와 **정확히 일치**한다 (E3 와 같은 정합성 신호).
논리적 모순 (하드킬인데 접촉권 밖) 은 네 arm 모두 **완전 해소**.

### §17 "closest approach 1.4–1.7 m" — 두 겹으로 정정

**(a) 원 수치는 pooled 통계였고 오염돼 있었다.** 정정 후 pooled 중앙값 band =
**1.24–1.67 m** (원 1.38–1.74).

**(b) 더 중요한 것 — 'wall' 은 침투 부분집합에서 읽어야 하고, 그 하한은 정의상 인공물이다.**

| arm | 침투 n | `closest` med | min |
|---|---|---|---|
| 24 | 202 | 1.554 → **1.510** | 0.755 → 0.755 |
| 36 | 205 | 1.541 → **1.425** | 0.801 → 0.761 |
| 48 | 215 | 1.654 → **1.510** | 0.804 → 0.752 |
| 60 | 215 | 2.257 → **2.182** | 0.753 → 0.752 |

침투 최소값이 네 arm 모두 **0.752–0.761 m**, 즉 `r_contact = 0.75` **바로 위**에 붙어 있고
`≤ 0.75` 인 침투는 **0 건**이다. 이는 물리적 벽이 아니라 **정의상 하한**이다 — 접촉권에
들어온 에피소드는 접촉 event 로 해소되므로 침투로 남을 수 없다.

> **금지**: 침투 최소거리 ~0.75 m 를 *"공격자가 물리적으로 더 좁히지 못한다"* 의 증거로
> 인용. 그것은 라벨 정의의 동어반복이다.

**(c) 원 결론 자체는 생존한다.** 교전시간을 2 배 (arm 24 → 60) 로 늘려도 `P_HK` 는
0.190 / 0.207 / 0.177 / 0.177 로 평평하고, 침투 최근접 중앙값은 오히려 **증가**한다
(1.510 → 2.182). 즉 *"짧은 교전시간이 하드킬을 억제한다"* 는 가설은 여전히 **기각**이다.
침투 837/837 에서 최근접이 terminal **이전**에 발생한다는 사실도 불변.

### 정본 (정정 후)

> *"Doubling the engagement horizon did not increase hard-kill (0.190 / 0.207 / 0.177 /
> 0.177) and did not reduce the closest approach among penetrations (median 1.51 → 2.18 m).
> The apparent floor near r_contact is definitional — episodes entering contact range are
> resolved as contact events and cannot remain penetrations."*

**§30.6 의 인용 금지 해제.** 단 인용은 위 정본 문장으로 하고, 원 "1.4–1.7 m" 표기는 쓰지
않는다.

## 30.9 lead-time 주장 축소 (§30.8 후속 확정)

§30.8(b) 를 근거로 §17 의 "wall" 을 **기전 증거에서 완전히 철회**한다. `r_contact` 바로
위에 붙는 하한은 물리가 아니라 **outcome-label geometry 가 만든 selection boundary** 다.

lead-time 진단이 남기는 것은 **outcome 수준 null 하나뿐**이다:

> **2× more engagement time did not increase P_HK** (0.190 / 0.207 / 0.177 / 0.177).

침투 최근접 중앙값 증가(1.510 → 2.182 m) 는 이 null 을 **보조**할 뿐, 독립 증거로 쓰지
않는다 (같은 selection boundary 위의 통계다).

---

# 32. E1e 사전등록 — 보정 capture-bound 의 fresh confirmation (결과 전 동결)

§28.3 에서 **사후** 도출한 보정 법칙을 미사용 seed 에서 검정한다. E1d 의 D-a/D-b 재현이
목적이 **아니다** — 결과를 보고 만든 piecewise law 자체가 시험 대상이다.

## 32.1 검정 대상

$$s(a_x)=\min\bigl(a_x\tan\theta,\; R_{\max}-a_x\bigr), \qquad a^*(a_x)=\frac{2\,s(a_x)}{\tau^2}$$

near side 는 lateral cone clearance 가, `ax* = R_max/(1+tanθ)` 이후로는 **far-edge range
clearance** 가 지배 → **inverted-U**.

동결 상수 (`m4_config`): `τ = 0.30` · `R_max = 8.22` · `θ = 0.212100 rad (12.1524°)` ·
`tanθ = 0.215339` · **`ax* = 6.763546 m`**.

## 32.2 Arms (n=300/arm, 동일 에피소드 = paired)

| arm | target ax | 지배 제약 (예측) | `s` | **보정 `a*`** | 기존 법칙 `a*` |
|---|---|---|---|---|---|
| **E-1** | 5.50 | lateral | 1.1844 | **26.32** | 26.32 (동일) |
| **E-2** | 6.75 | lateral (간발) | 1.4535 | **32.30** | 32.30 (동일) |
| **E-3** | **7.20** | **far-edge** | 1.0200 | **22.67** | **34.45** |
| **E-4** | 7.90 | far-edge | 0.3200 | **7.11** | 37.76 |

**E-3 (7.20) 이 판별점이다.** 두 법칙이 6.75 대비 **반대 방향**을 예측하는 유일한 미관측
지점 — 기존 법칙은 증가(34.45 > 32.30), 보정 법칙은 감소(22.67 < 32.30). E-1 은 두 법칙이
같은 값이라 판별력이 없고(형태 확인용), E-4 는 E1d 에서 이미 관측됐다.

공통: T1 세계 · `ideal aim (ψ=0)` · ω 기본값 · force-commit semantics 는 E1d 와 동일
(`force_commit_step` = **1-based `_step_i` 규약**) · two-pass replay (Pass 1 은 4 arm 공유) ·
**fresh seeds `31000..31299`**.

## 32.3 Primary — **shape** (a*₅₀ 아님)

E1d 에서 `cross50` 이 `nan` 이 된 전례가 있으므로 primary 를 단일 임계값에 두지 않는다.
paired bootstrap (20 000 resample) CI95 가 0 을 배제해야 한다.

| # | 예측 |
|---|---|
| **H1** | `P_C(6.75) > P_C(5.50)` |
| **H2** | `P_C(6.75) > P_C(7.90)` |
| **H3 (판별)** | **`P_C(7.20) < P_C(6.75)`** — 기존 법칙은 반대를 예측 |

## 32.4 판정 (결과 전 동결)

| # | 조건 | 판정 |
|---|---|---|
| **E1e-A** | H1 ∧ H2 ∧ H3 | **보정 법칙 확인.** 사후 → confirmatory 로 승격 |
| **E1e-B** | H1 ∧ H2, H3 실패 | 내부 최적은 존재하나 **위치/형태 오설정**. 승격 보류 |
| **E1e-C** | `P_C(7.90) ≥ P_C(6.75)` (단조 증가) | **보정 법칙 반증**, 기존 lateral-only 법칙 복권 |
| **E1e-D** | 그 외 / 비일관 | INCONCLUSIVE |

## 32.5 Secondary

- **S1 (episode-level)**: 마진 $m = a^*(a_x^{\rm realized}) - a_{\rm att}$ 를 사전등록.
  `m > 0 ⇒ capture` 분류 정확도를 arm 별로 보고. **수락 기준 ≥ 0.95** (E1d 사후값
  0.993/0.997/0.997 은 같은 데이터에서 나왔으므로 기준으로 쓰지 않는다).
- **S2**: arm 별 `a*₅₀` 와 예측값(26.32 / 32.30 / 22.67 / 7.11) 의 차. E-4 는 예측 `a*` 가
  위협 브래킷 하한 11 미만이라 **`cross50` 이 정의되지 않는 것 자체가 예측**이다.
- **S3 (참고, pass/fail 아님)**: 브래킷 `a ~ U[11,78]` 균일 가정 하 주변 예측 포획률
  **0.229 / 0.318 / 0.174 / 0.000**. E1d 에서 이 근사가 20 % 과대예측(D-a 예측 0.299 vs
  관측 0.240)이었으므로 **calibration 참고값**으로만 쓴다.
- **S4**: 모든 분석은 **realized ax** 로 한다 (nominal target 아님, E1d 교훈). realized ax
  분포와 `ψ_at_commit` 을 arm 별로 병기.

## 32.6 회귀 (실행 전 통과 필수)

| # | 게이트 |
|---|---|
| **E-A** | `force_commit_step` 기본값 무변화 bit-exact (E1d D-A 와 동일 취지, 최우선) |
| **E-B** | seed 대역 `31000..31299` 가 기존 캠페인(0.. / 10000.. / 30000..)과 **미교차** |
| **E-C** | Pass 1 이 4 arm 에서 **완전 동일** (공유 검증) |
| **E-D** | 강제 커밋이 에피소드당 **정확히 1 발**, 탄 미소모 (E1d D-D 와 동일) |

## 32.7 금지 (결과와 무관하게)

- **"net capture physics 를 설명했다"** — 이 식은 **idealized forced-commit terminal
  geometry** 의 법칙일 뿐이다.
- perfect aim (ψ=0) 은 **실현 불가능한 반사실**이다. arm 별 포획률을 시스템 성능으로 읽기 금지.
- 최대 표현: *"Under the registered idealized commit counterfactual, the active geometric
  constraint switches from lateral cone clearance to far-edge range clearance, producing an
  interior optimal axial commit distance."*
- **실제 closed-loop 에서 그 `ax*` 에 도달할 수 있는가는 별개 문제**이며, 본 실험은 그에
  대해 아무것도 말하지 않는다 (B2 / cooperative shaping 질문으로 남긴다).

---

# 33. E1e 판정 — **E1e-A (보정 법칙 확인, 사후 → confirmatory 승격)**

실행 `47268e1` (회귀 5/5) · 결과 `e3d1fbd` · `results/e1e.json` · fresh seeds
`31000..31299` · n=300/arm · Pass 1 4-arm 공유 · ideal aim (psi=0).
판정은 스크립트가 §32.4 동결표를 그대로 적용해 산출했다.

## 33.1 Primary — shape (§32.3), 세 가설 전부 성립

| # | 대조 | 차 | CI95 | 판정 |
|---|---|---|---|---|
| H1 | P_C(6.75) − P_C(5.50) | **+0.0433** | [+0.0200, +0.0700] | HOLDS |
| H2 | P_C(6.75) − P_C(7.90) | **+0.2400** | [+0.1933, +0.2900] | HOLDS |
| **H3 (판별)** | P_C(6.75) − P_C(7.20) | **+0.1033** | [+0.0700, +0.1400] | **HOLDS** |

**H3 가 이 실험의 전부다.** ax 7.20 에서 기존 lateral-only 법칙은 a* 34.45 (증가) 를,
보정 법칙은 22.67 (감소) 를 예측했다. 관측은 **감소** — 미관측 지점에서 두 법칙이 반대
방향을 예측했고 보정 법칙이 맞았다.

역 U 형태 확인:

| arm | ax (realized med) | **P_C** | Wilson 95% |
|---|---|---|---|
| E-1 | 5.4810 | 0.2333 | [0.189, 0.284] |
| **E-2** | **6.7244** | **0.2767** | [0.229, 0.330] |
| E-3 | 7.1938 | 0.1733 | [0.135, 0.220] |
| E-4 | 7.8041 | 0.0367 | [0.021, 0.065] |

정점이 E-2 (realized ax 6.7244) 이고 예측 최적은 `ax* = 6.7635` 다.
**단, 4 점만으로 최적의 위치를 특정했다고 쓰지 않는다** — 확인된 것은 *"가운데가 양쪽보다
높다"* 이지 *"최적이 6.76 에 있다"* 가 아니다.

## 33.2 Secondary

**S1 (사전등록 수락 기준 ≥ 0.95) — PASS.** episode-level 마진 `m = a*(ax_realized) − a_att`
의 `m > 0 ⇒ capture` 분류 정확도: **0.9967 / 0.9933 / 0.9900 / 1.0000**. 기준을 결과 전에
동결했으므로 이번 값은 rubber stamp 가 아니다.

**S2 — 형태는 맞고 수준은 계통적으로 낙관.**

| arm | a*₅₀ (관측) | 예측 a* | 비 |
|---|---|---|---|
| E-1 | 22.39 | 26.32 | 0.8509 |
| E-2 | 27.03 | 32.30 | 0.8368 |
| E-3 | 19.59 | 22.67 | 0.8641 |
| E-4 | **정의 불가** | 7.11 | — (**예측대로**) |

비 = **0.8506 ± 0.0111** (세 팔). 편차가 극히 작다 = 잡음이 아니라 **계통 편향**이다.
E-4 의 `cross50` 이 정의되지 않는 것은 §32.5 S2 가 예측한 그대로다 (예측 a* 7.11 <
브래킷 하한 11).

> **새 소득 (사후, 확인 필요 아님 — 관측 사실)**: 보정 법칙은 a* 의 **점 예측기가 아니라
> 약 15 % 낙관적인 단측(상한) 경계**다. 세 팔에서 비가 0.837 ~ 0.864 로 안정적이다.
> 이는 프로젝트의 *optimistic outer bound* framing 과 정합한다.

**S3 (참고, pass/fail 아님)**: 주변 예측 포획률 vs 관측 —
E-1 0.229 vs 0.2333 (**+0.004**) · E-2 0.318 vs 0.2767 (−0.041) ·
E-3 0.174 vs 0.1733 (**−0.001**) · E-4 0.000 vs 0.0367 (+0.037).
E-1/E-3 은 거의 일치하고 E-2 에서 과대예측한다.

**S4**: 전 분석이 realized ax 기준. psi_at_commit 은 네 팔 모두 정확히 0.0000 deg
(perfect aim 계약대로).

## 33.3 정본 / 금지

- **정본 (§32.7 최대 표현, 이제 fresh seed 로 확인됨)**:
  *"Under the registered idealized commit counterfactual, the active geometric constraint
  switches from lateral cone clearance to far-edge range clearance, producing an interior
  optimal axial commit distance."*
- 추가 정본: *"The resulting bound is optimistic by a stable factor of about 15 percent
  across the tested arms and should be used as a one-sided bound, not as a point predictor."*
- **금지 (§32.7 유지)**: "net capture physics 를 설명했다" / perfect aim 결과를 **시스템
  성능**으로 읽기 / **최적 위치를 6.76 으로 특정** / closed-loop 에서 그 ax 에 도달
  가능하다는 주장 (별개 문제, B2 / cooperative shaping 으로 남긴다).

## 33.4 상태 전이

- §28.3 의 보정 법칙: **사후(post-hoc) → confirmatory 승격.** C038 의 *"fresh seed 확인 전
  승격 금지"* 조건 해제.
- E1d 판정(§28, primary REFUTED)은 **그대로 유효**하다. E1e 는 E1d 를 뒤집는 것이 아니라
  E1d 가 남긴 사후 가설을 닫는다.

## 33.5 ★ arXiv v0 science freeze

**docs/84 §5 의 계획대로, 본 판정 커밋을 arXiv v0 의 science freeze point 로 선언한다.**
이후 실험(새 geometry 축 · E4-2 · T2 · MARL · Δ_coop 층)은 **v0 와 병렬인 다음 branch**
이며 v0 본문에 들어가지 않는다. v0 는 이제 **집필 단계**다.

---

# 34. E1e 이후 성립 상계의 계층화 — rho-bound 와 cone-geometry ceiling

E1e(§33) 의 함의를 별도 기록한다. **단순한 문장 수정이 아니라 기존 headline bound 의
수학적 지위를 한 단계 정교화한 것**이므로, 나중에 `39.3` 이 왜 남아 있고 `32.4` 가 왜
새로 생겼는지 혼란이 없도록 여기에 고정한다.

> **고정 표현**: *"39.3 은 틀렸다"* 가 **아니라** *"39.3 은 유효하지만 loose outer bound
> 였다"* 로 쓴다.

## 34.1 판정

E1e 는 E1d 를 보고 사후 제안된 `s(ax) = min(ax*tan(theta), R_max - ax)` 의 **형상 예측을
fresh seed 에서 확인**했다. 판별점 `ax = 7.20 m` 에서 기존 lateral-only 법칙은 증가를,
보정 법칙은 감소를 예측했고 관측은 감소였다 (H3 = +0.1033, CI95 [+0.0700, +0.1400]).
따라서 이 piecewise clearance law 는 post-hoc 설명에서 **confirmatory-supported
mechanism** 으로 승격한다.

단, 확인된 것은 **shape / direction** 이다. 폐루프가 최적 commit geometry 에 도달할 수
있음이나 최적의 정확한 위치를 확인한 것이 **아니다**.

## 34.2 기존 chi = 1 경계의 지위

    chi = a_att * tau^2 / (2 rho) < 1,      rho = R_max * tan(theta)

**등록값 검증**: `rho = 1.770000` vs `R_max*tan(theta) = 8.22 * 0.215339 = 1.770085`
(차 8.5e-5). 즉 **rho 는 자유 파라미터가 아니라 cone 의 최대사거리에서의 측방 반폭**이다
(이 대수 의존은 Π inventory 가 이미 적발했다).

기준 운용점에서

    a*_rho = 2 rho / tau^2 = 39.33 m/s^2

이 식은 여전히 **자유 회피 표적에 대한 단독 포획의 유효한 필요조건**이다. 그러나 등록된
cone geometry 에서는 rho 전체를 **어느 axial commit 위치에서도** 실제 clearance 로 쓸 수
없다. `ax = R_max` 에서 lateral half-width 는 rho 에 도달하지만 **axial range slack 은 0**
이다.

⇒ 39.33 은 틀린 경계가 아니라 **등록 cone geometry 를 무시한 loose outer necessary bound**.

## 34.3 등록 cone geometry 의 tighter ceiling

사용 가능한 clearance 는 `s(ax) = min(ax*tan, R_max - ax)` 이고 최대는 두 항이 같은 지점:

| 양 | 식 | 값 |
|---|---|---|
| `ax*` | `R_max / (1 + tan)` | **6.7635 m** |
| `s_max` | `R_max*tan / (1 + tan)` | **1.4565 m** = **0.8229 rho** |
| `a*_geom` | `2 s_max / tau^2` | **32.37 m/s^2** |
| `chi*_geom` | `s_max / rho` | **0.8229** |

따라서 기준 운용점의 analytic hierarchy 는

    a*_rho = 39.33   >   a*_geom = 32.37

이며, **32.37 < a_att < 39.33 구간은 rho-based 필요조건만 보면 열려 있지만 등록 cone
geometry 를 포함하면 이미 닫힌다.**

## 34.4 E1e empirical level 과의 구분 — 세 수준을 섞지 않는다

E1e 최선 arm (E-2) 의 관측 임계는 `a*_50 ~ 27.03 m/s^2` (chi ~ 0.687) 이다. 그러나 이는
**hold + forced commit + perfect aim** 계약의 결과이며 **T1 intercept 폐루프 곡선과 직접
결합하면 안 된다**. 또 보정 법칙은 E1e 자체 실측 대비 약 **15 %** 낙관이다
(`a*_50 / 예측 = 0.8506 +- 0.0111`).

| 값 | 성격 |
|---|---|
| **39.33** | loose outer necessary bound (rho 전체 가용 가정) |
| **32.37** | 등록 cone geometry 의 **analytic** ceiling |
| **27.03** | E1e forced-commit **empirical** (다른 계약) |

**세 값을 하나의 동일한 empirical curve 의 경계처럼 취급하지 않는다.**
마지막 화살표만 *analytic → empirical + different contract* 로 시각적으로 구분한다.

## 34.5 논문 영향

### KSAS — 최소 개입

- **§2.1**: 등록 기하에서 `rho = R_max * tan(theta)` 임을 명시.
- **§2.2**: 식 (3) 뒤에 한 문장 (동결):

  > 단, 등록된 원뿔형 포획 기하에서는 rho = R_max·tanθ 의 전체 폭과 축방향 여유를
  > 동시에 확보할 수 없으므로, 식 (3) 은 tight 한 경계가 아니라 외곽 필요조건이다.

  필요하면 바로 다음 문장에만:

  > 해당 기하를 포함한 해석적 천장은 32.4 m/s² 로 낮아진다.

- **Fig. 2**: 기존대로 **chi = 1 만** 표시. E1e empirical point 는 표시하지 않는다
  (계약이 다르다).
- 32.4 를 언급하더라도 **새 결과축으로 전개하지 않는다** — KSAS 에서 세 층을 다 설명하면
  논문 핵심이 mechanism archaeology 로 빠진다.

이 최소 개입만으로도 현행 초고의 오류 — **"open gap 전체가 controller 문제"** — 가 제거된다.
간극의 일부(39.3 → 32.4)는 controller 가 아니라 **기하가 닫은 것**이다.

### arXiv v0 — feasibility analysis 의 핵심 mechanism

    naive net-width bound 39.3
        -> finite-cone geometry 32.4
        -> achieved forced-commit 27.0

계층으로 제시한다 (docs/84 §2 의 "E1d → E1e 를 핵심 mechanism figure 로 승격" 이 이것).

## 34.6 금지 해석 (E1e 가 지지하지 않는 것)

- "폐루프 controller 가 `ax* = 6.7635 m` 에 도달한다."
- "6.7635 m 가 실험적으로 확인된 정확한 최적 commit 위치다." (4 점 = 형태만)
- "32.37 m/s² 가 T1 closed-loop 의 관측 붕괴점이다."
- "27.03 m/s² 와 기존 chi ~ 0.66 aiming boundary 가 같은 mechanism 이다."
  (위치가 우연히 가깝지만 설명이 다르다 — 조준이 아니라 기하. 철회된 주장을 부활시키지 않는다.)
- "E1e 가 intercept-mode failure 의 원인을 설명했다."
- **"39.3 m/s² 경계가 잘못되었다."**
