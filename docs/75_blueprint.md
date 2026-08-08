# 75 — 청사진 (BLUEPRINT) — 채택본 v3, 2026-08-09 (리뷰 12·13 교정 반영)

**리뷰 11 의 청사진 회신을 채택·확정한 문서. 우리의 실행 계약이다.**
전제: **12/18 은 URP 행정 마일스톤이지 연구 종료선이 아니다.** 아래 게이트는 전부
**과학적 kill/branch 게이트**이고 시간 게이트가 아니다. 12/18 에는 "어디까지 완결해
보고할지"만 정하고, 미완은 **미완으로 명시**하고 이후 지속한다.

- spine: *Feasibility-First Design of Cooperative Single-Shot Counter-UAS
  Interception under Deployment Latency*
- 핵심 질문: **알고리즘 성능이 아니라 — "협력 요격 메커니즘이 애초에 실현 가능한
  advantage 를 갖는 영역이 존재하는가?"**
- 정의·계약·certificate·Stage-2 규칙 = `docs/74_pivot_protocol.md` (**r3**)
- 판정·철회·폐기 = `docs/73_review10_verdicts.md` (**r3**)

---

## 0. 만약 하나만 만든다면 (최우선 산출물)

MARL 재학습도, 6DOF 도 아니다.

> reference encounter 의 같은 시각 `(e,t)` 에서
> `L^reach_{<=N,clean} <= V^reach_{<=N} <= V^rel_{<=N} <= U^rel_{<=N}` 를 계산하고,
> **그와 별도로** 반응형 attacker closed-loop 에서 `L^ctrl_{<=N}` 의 실현 가능성을
> 검증하여 **FREE / SINGLE-NEEDED / COOP-NEEDED / INFEASIBLE-N / AMBIGUOUS** 를
> 구분하는 **certificate-backed feasibility envelope**.
> (snapshot certificate 와 closed-loop rollout 값을 **하나의 sandwich 로 섞지 않는다**.)

특히 **`U^rel_{<=1} < theta <= L^reach_{<=N,clean}` 셀이 실재하는가**
(= **local certified cooperative opportunity**).
있으면 "왜 multi-agent 인가" 를 certified 하게 답한다. **없으면 즉시 "협력 불필요" 가
아니라** (A) single-agent sufficiency / (B) N-agent infeasibility / (C) unresolved
certificate gap 중 어느 경우인지 분기하고, **해당 bound 가 직접 지지하는 주장만** 한다
(C 는 결론 없음). 이 질문을 답하지 않고 MAPPO 를 더 돌리면 학습 실패와 물리적
불가능성을 또 구분하지 못한 채 계산량만 늘어난다.

## 1. 단계별 계획 (주 번호는 순서 표기일 뿐, 마감 아님)

| 주 | 핵심 산출물 | Continue / branch 게이트 |
|---|---|---|
| 1 | **pivot manifest + 불변 태그 + 외부 timestamp** · Phase III definitions r3 · **master lattice `Z_master` 봉인(`lattice_hash`)** · Buckingham-Π 전체 도출 | manifest·`lattice_hash` 스탬프 없는 map artifact = **전부 무효** |
| 2 | `v_shot` **수렴 하네스** (2k/8k/32k) | 8k→32k 변화 **median ≤ 0.02 · 95% ≤ 0.05**. 초과 시 **지도 중단** |
| 3 | witness allocation 민감도 + measure **R/P 최종 결정** | allocation 변경으로 주요 score 가 **> 0.05** 변하면 현 R metric 폐기·재설계 |
| 4 | finite-candidate **exact threshold solver** (MILP/B&B) | synthetic truth 100% 재현 · 실제 인스턴스 **≥ 90%** 에서 certified optimum/gap 확보 |
| 5 | **greedy ↔ global audit** | greedy saturation 주장의 왜곡 정량화 → Phase II F2 해석 **최종 봉인** |
| 6 | **unblockable bad mass** certificate | soundness unit test 통과. 값이 약한 것은 실패가 아님 |
| 7 | **continuous outer relaxation** v1 (voxel/cell) | refinement 시 upper bound 가 **단조 tighten** 되는지 |
| 8 | **4A** 고정 `(e,t)` `L^reach_{<=N,clean}` (certificate) → **4B** closed-loop `L^ctrl` (실현 검사) | 4A 없이 4B 로 certificate 주장 **금지** · violation **0** · `not boxed` 확인 |
| 9 | **독립 judge cross-check (boundary-aware)** | signed margin 비교 `|m1-m2| <= eps`; **boundary 에서 먼 predicate 불일치 1 건** → 지도 중지·버그 감사 |
| 10 | **iso-Π collapse 실험** | 같은 Π 인데 paired score 차이가 허용오차 밖 → **빠진 Π 추가** |
| 11 | core 2D envelope **pilot** | FREE / AMBIGUOUS / COOP / INFEASIBLE 분포 관찰 → §3 분기 결정 |
| 12 | **boundary adaptive refinement** | 경계 근접 셀 replication 확대 (60~100+) |
| 13 | `N = 0,1,2,4,…` **cooperation audit** | `U^rel_{<=1} < theta <= L^reach_{<=N}` 셀이 **없으면 협력 C5 금지** + (A)/(B)/(C) 중 어느 분기인지 **판정 근거를 셀별로 기록** |
| 14 | main **certified map** v1 | certificate coverage 비율 + **ambiguity map 동시 생성** |
| 15 | **Stage-2 점 freeze** (CP LCB95 `p_C` argmax, `Z_master` 내) | `LCB95 > 0.05` 이고 성공 episode >= 5 인 점이 없으면 **협력 C5 미실시** |
| 16 | C5 training wave (3 regime) | 최종 시드 **8~10** 권장 |
| 17 | C5 held-out eval + **primary estimand `Gamma`** | `Gamma = delta_COOP - (delta_FREE+delta_HARD)/2`, 성공 = `LCB95(Gamma) > 0` (comparator = freeze 된 `B_N`) |
| 18 | jitter / noise / lag + 파라미터 perturbation | qualitative topology 가 깨지면 **context-of-use 축소** |
| 19 | URP 보고서 / arXiv snapshot | 저널 증거 미완이면 **미완으로 명시하고 지속** |

W11 에서 협력 opportunity 가 0 이어도 **연구 kill 이 아니다** — §3 의 ①-A/①-B/①-C 중
어느 분기인지 판정하고, **①-C(AMBIGUOUS 다수)면 negative claim 을 하지 않는다**.

## 2. 기술 부품

| 부품 | 최소 스펙 | 난이도 | 실패 시 대체 |
|---|---|---|---|
| `v_shot` harness | 2k/8k/32k · family allocation 변경 · **동일 snapshot paired** 비교 | 중 | R 폐기 → P 또는 set-based robust metric |
| finite exact solver | 고정 후보에서 threshold feasibility **exact** | 중상 | witness signature 압축 + bisection |
| continuous upper relaxation | 공간 partition 기반 **optimistic maximum coverage** | 상 | unblockable-mass + finite exact only, impossibility 주장 범위 축소 |
| unblockable bad mass | bad witness blocking-center set 의 emptiness/coverage 상한 | 중 | individual-only certificate |
| reachable constructive lower | dynamics/NK/충돌 만족 controller rollout | 상 | simpler assignment + receding-horizon scripted controller |
| dimensionless map | core 2~3 Π 축 · N 이산 · adaptive refinement | 중 | raw parameter slice + collapse 주장 없음 |
| C5 | FREE / BAND / HARD + **N=1** + MARL | GPU 상 | constructive controller validation 만 남김 |
| robustness | τ jitter · perception noise · actuator lag | 중 | context-of-use 를 명시적으로 좁힘 |

### 2.1 finite-candidate exact solver — **solver/audit auxiliary** (certificate 아님)

후보 center `i` 선택 `z_i ∈ {0,1}`, witness `j` 생존 `y_j ∈ {0,1}`,
`A_ji = 1` iff 후보 `i` 가 witness `j` 를 kill. 분모 > 0 조건에서
```
v >= theta   <=>   sum_j w_j (c_j - theta) y_j >= 0        (c_j = cone captured)
subject to   sum_i z_i <= N,  survivor 관계를 이진 제약으로
```
**주의**: 후보집합 `C ⊂ D` 이므로 θ 미달은 continuous-domain 불가능을 certify 하지 않는다.
→ **fractional objective 를 threshold-feasibility MILP** 로 변환. θ 에 대해 bisection 하면
finite-candidate optimum 도 얻는다. **동일 candidate-cover signature 위트니스를 묶어
압축**하는 것이 핵심 (864 후보 × 8k 위트니스는 가능, 32k 는 압축 필수).

### 2.2 continuous outer relaxation — 구현 형태 (채택)

bad witness `j` 의 escape 궤적 `gamma_j` → blocker tube `B_j = gamma_j (+) Ball(r_kill)`.
center domain `D` 를 voxel/cell `C_q` 로 분할하고 **낙관적 incidence**
`A^outer_{jq} = 1 if C_q ∩ B_j != ∅` 를 만든다 (한 cell 이 서로 다른 위치에서 두 tube 를
건드려도 "한 center 로 둘 다 봉쇄"로 과도 인정). good witness 는 절대 안 지워진다고
추가 낙관하면
```
U_{<=N} = G / (G + B - B_removable,N)
```
cell refinement 로 optimism 이 줄어드는 구조 → **certificate convergence figure**.

### 2.3 unblockable bad mass — 최저비용 certificate (먼저 구현)

`B_j ∩ D = ∅` 인 bad witness 는 **어떤 배치로도 못 지운다.** 그 mass `U`, captured-good
mass `G` 로 `v_max <= G/(G+U)`. θ 미만이면 즉시 certificate.
**계층형**: 이걸 먼저 → 안 먹히는 셀만 continuous N-limited relaxation 으로 승급.

### 2.4 reachable constructive lower — **4A(certificate) / 4B(실현 검사) 분리**

최적 controller 를 만들 필요 없다. **하나의 구성적 증인**이면 된다:
① 예측 escape path 에서 blocking tube 후보 생성 → ② limiter 별 도달가능성 검사 →
③ agent-candidate bipartite assignment → ④ threshold-feasibility 로 target center 선택 →
⑤ bang-bang/PD 추종 → ⑥ 5~10 tick replan → ⑦ **반응형 attacker 가 있는 실제 env rollout** →
⑧ 실제 judge 가 clean fire → `L^ctrl` (**4B, certificate 아님**).
**4A** = 같은 후보를 고정 `(e,t)` 의 **같은 witness set** 에 넣고 `not boxed` 까지 확인한
`L^reach_{<=N,clean}` — **이것이 sandwich 의 오른쪽 항**이다. **★ 4A·4B 모두 MARL 보다 먼저.**

## 3. 분기 트리 (반증조건 발동 시)

| 발동 | 대체 산출물 | venue |
|---|---|---|
| ①-A single-agent sufficiency (`V_0 < theta <= L^reach_{<=1}` 지배 + coop 셀 부재) | "no certified need for multi-agent interdiction; a single reachable limiter suffices wherever a constructive solution exists" | T-AES / AST |
| ①-B mechanism infeasibility (`U^rel_{<=N} < theta` 광범위) | *Limits of Cooperative Threat-Space Shaping for Single-Shot Capture under Deployment Latency* — 핵심은 **upper certificate 강도**. "4-agent algorithm failed" 가 아니라 **firing condition 자체가 성립 불가** | T-AES / AST |
| ①-C unresolved (AMBIGUOUS 다수) | **결론 없음 — negative claim 금지.** certificate 강화 또는 문제 정의 단순화로 되돌아간다 | 투고 불가 |
| ② band 는 열리는데 MARL 이득 0 | `physical feasibility != learnability` 분리 보고. constructive controller 가 band 에서 성공하면 그것이 결과 → **Paper 2 발생** | 동일 |
| ③ exact/reachable 에서 `N_req >= 2` | **호재.** Phase II F2 관측만 철회. `U^rel_{<=1} < theta <= L^reach_{<=2}` = 진짜 cooperative necessity → N=1 vs N=2/4 가 메인 실험 | 동일 |
| ④ `v_shot` 이 allocation 민감 | 지도 **즉시 중단**. (P) branch (실제 uncertainty 분포 정의) 또는 set-based branch (worst-case containment / quantile radius / support-function). 기존 θ map 미사용 | 재설계 후 |

## 4. 논문 1 편 구조 + 필수 그림 8 장

```
1 Introduction        — "When does a cooperative interception mechanism admit a
                        realizable advantage at all?"
2 Problem & provenance— system · Phase I 원 연구 · chronology · 파라미터 출처
3 Feasibility formulation — R measure · V_0 · L^reach_{<=N} · U^rel_{<=N} ·
                        mutually-exclusive certified labels · closed-loop layer 분리 ·
                        cooperation-required certificate
4 Certification algorithms — exact finite placement · unblockable mass ·
                        continuous outer relaxation · reachable constructive controller
5 Dimensionless design space — Π groups · collapse validation
6 Certified design envelope — **논문 본체**
7 Controller-level prospective validation — C5
8 Robustness and context of use
9 Discussion — nominal null 설명 · 무엇이 requirement 가 아닌지 · limitations
```

| Fig | 내용 | 막는 반박 |
|---|---|---|
| 1 | system + cone + reachable witnesses + kill tube | "메커니즘이 모호하다" |
| 2 | Phase I→II→III chronology | "실패 후 스토리를 바꿨다" |
| 3 | witness 수렴 / allocation 민감도 | "0.9 가 sampling artifact 다" |
| 4 | 고정상태 `L^reach / V / U^rel` **certificate sandwich** + solver 수렴 (closed-loop 값은 별도 패널) | "불가능 주장이 heuristic 이다" · "두 문제를 섞었다" |
| 5 | **iso-Π collapse** | "축 선택이 arbitrary 하다" |
| 6 | main certified envelope (FREE/SINGLE/COOP/INFEASIBLE/**AMBIGUOUS**) | 논문의 핵심 |
| 7 | `N = 0,1,2,4,…` / `W_{2:N}` + 셀별 certificate 수준 | "4 기가 왜 필요한가" · "어떤 셀이 어떤 근거로 닫혔나" |
| 8 | C5 3-regime **interaction** + robustness inset | "좋은 점 골라 RL 돌렸다" |

**Fig 6 에서 AMBIGUOUS 를 숨기지 않는 것**이 매우 중요하다.

## 5. 투고 전략

| 순위 | venue | 프레이밍 |
|---|---|---|
| 1 | **IEEE T-AES** | **systems design + verification + collaborative autonomy**. complex aerospace/defense system 의 organization·design·integration·operation 과 Intelligent Systems (collaborative teaming, V&V) 가 scope. "새 MAPPO" 로 쓰면 약해진다 |
| 2 | **Aerospace Science and Technology** | interception mechanics · dimensionless design · latency/capability trade · flight-system 해석을 앞세움 |
| 조건부 | **JGCD** | certificate·reachable controller 가 강해지고 RL 비중이 작아질수록 매력 증가 |

투고 시점은 **증거 bar 충족 시점**에 따른다 (12/18 과 무관).

## 6. KSAS 추계 초록 (마감 임박) — 안전한 구조

Phase II 를 **넣어도 된다. 단 "결과"가 아니라 preliminary diagnostic 으로.**

1. cooperative net interception 문제 → 2. nominal preregistered controller study 에서
특정 기존 regime 의 capture 0 → 3. 이를 설명하기 위한 **exploratory geometry analysis** →
4. tested relaxed placement 에서 threshold-crossing 여부가 **파라미터에 강하게 의존**한다는
예비 관측 → 5. limitations (single realization · static relaxed placement · no
reachability · finite witness) → 6. 결론: **controller 비교 전에 parameterized
feasibility analysis 가 필요하다** + prospective study 진행 중.

**쓰면 안 되는 문장**: "협력 결정대역은 36–39 m/s² 였다" · "1 기면 충분함을 발견했다" ·
"MARL 실패 원인은 전개지연이었다". (docs/73 §2 철회 목록과 충돌)

## 7. 5 년 논문 라인 (C-UAS 한 문제를 5 년 파지 않는다 — 점진적 추상화)

| # | 논문 | 핵심 기여 | 선행조건 | 성격 | 시점 |
|---|---|---|---|---|---|
| **P1** | Feasibility envelope | cooperative mechanism 의 **certified existence/absence** | 현재 연구 | aerospace systems | 학부 |
| **P2** | Certificate-guided cooperative control | envelope 안으로 state 를 **몰아가는** controller/RL | P1 의 `L/U` framework | robotics/control | 학부 후반~대학원 초 |
| **P3** | Finite-shot optimal stopping | θ gate 를 **expected utility / stopping** 으로 제거 | P1 + 성공/실패 통계 | stochastic control | 대학원 초기 |
| **P4** | Cooperative latency reduction | 협력을 물리적 봉쇄가 아니라 **sensing/aiming 정보 획득**으로 확장 | P2/P3 | multi-robot autonomy | 대학원 |
| **P5** | 6DOF + hardware/HIL | model hierarchy + sim-to-real | P2/P4 | robotics systems | 대학원 |

- **α optimal stopping** → **P3**. 지금 넣으면 P1 의 질문이 퍼진다.
- **β sensing/aim latency 협력** → **P4, 강하게 추천**. 현재 협력 채널이 kill-sphere
  removal 하나뿐인 것이 인공적 위험이므로, 정보적 협력으로 가면 robotics/MARL relevance 가 커진다.
- **γ multi-shot/reload** → 독립 우선순위 낮음. P3 의 finite-ammunition 에 흡수.
  질적으로 다른 cooperative allocation 문제를 만들면 독립 가능.
- **δ SE(3)/6DOF/hardware** → P1 직후 아님. **P2/P3 의 algorithmic 기여 이후.**
  point-mass 를 6DOF 로 바꾸기만 한 논문은 기여가 약하다.

## 8. 공개 자산 전략 (우선순위)

1. **certificate/feasibility benchmark (최고 가치)** — 입력 = encounter state · geometry ·
   dynamics budget · N · θ, 출력 = constructive lower · relaxed upper · ambiguity ·
   minimum-agent certificate. **application-agnostic** 으로 만들어 후속 논문에서 재사용.
2. **reproducible experiment contract** — seed manifest · scenario split · hashes ·
   paired evaluation harness. "또 하나의 MARL environment" 보다 차별화된다.
3. **simulator** — 공개하되 **자산의 중심으로 만들지 않는다.** 이름/추상화를 가능한 한
   generic 하게 (*cooperative finite-shot interception benchmark*).

## 9. 하드웨어 전이 시점

- **시뮬만으로 말할 수 있는 최대**: "Within the stated model and context of use, we
  characterize/certify the parameterized feasibility envelope."
- **시뮬만으로 말하면 안 되는 것**: "실제 Counter-UAS 시스템은 τ ≤ 0.21 s 여야 한다."
  → measured sensing latency · compute latency · net deployment timing · 실제 요격기
  dynamic envelope 중 최소 일부의 anchor 필요.
- 단계: point mass → actuator lag/noise/jitter → 6DOF → software/processor-in-the-loop →
  benchtop perception/deployment timing → 실제 비행. **현재 단계에서 첫 3~4 단계까지 가능.**

## 10. 커리어 정합 (주 연구자)

- **이 라인이 주는 것**: multi-agent control · MARL · reachability/viability ·
  constrained optimization · V&V · hypothesis discipline · failure diagnosis ·
  system-level robotics thinking.
- **이 라인만으로 부족한 것**: 실제 robot stack · perception/state estimation ·
  ROS2/PX4 계열 · 범용 RL benchmark 경험 · 더 강한 control/optimization 이론 ·
  하드웨어 실험.
- **행동**: 대학원 전까지 최소 하나는 **방산 맥락을 제거한 일반 multi-robot 문제**에 같은
  도구를 적용한다. 정체성을 "Counter-UAS MARL 연구자" 에서
  **"multi-agent autonomy 에서 feasibility 를 먼저 규명하고 learning 을 그 위에 올리는
  연구자"** 로 옮긴다 (P2 부터).

## 11. 장기 리스크와 조기경보

| 리스크 | 조기경보 지표 | 대응 |
|---|---|---|
| 모든 "발견"이 witness generator artifact | allocation 변경 시 `V` shift > 0.05 · 8k→32k 경계 이동 · 독립 judge 불일치 | 다른 작업보다 **먼저 metric 수정** |
| 실제 multi-agent 영역 부재 | `W_{2:N} ≈ ∅` (넓은 범위) | 편대 접고 negative systems / single-agent optimal interception 으로 분기 |
| certificate gap 이 안 닫힘 | `L^reach_{<=N} << theta << U^rel_{<=N}` 인 AMBIGUOUS 셀만 가득 = 분기 ①-C | 더 정교한 최적화가 아니라 **문제 정의 단순화**. negative claim 금지 |
| realism 넣으면 topology 반전 | jitter/noise/lag 에서 협력 band 소멸 | **"requirement" 언어 금지** |
| 연구가 코드 수리 프로젝트가 됨 | central figure 가 안 생기는데 reward·COMA·entropy·MAPPO head·scripted baseline 만 만지고 있음 | **즉시 경보** — §0 하나로 복귀 |

## 12. 자기기만 감시 2 건 (docs/73 §6.2 와 동일 — 상시 게시)

1. **"certificate 만 잘 만들면 Phase I 실패 원인이 밝혀진다"** — 아니다. Phase I 실패는
   feasibility · exploration · credit assignment · reward · architecture 가 동시에
   원인일 수 있다.
2. **"무차원 지도가 나오면 그 자체로 systems requirement"** — 아니다. 실물 anchor 없이는
   **model-conditional design envelope** 다.
