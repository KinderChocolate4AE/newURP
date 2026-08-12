# 79 — 게이트 7 contract: U^rel_{≤N} continuous outer relaxation — 2026-08-12 **r2**

**r2 (2026-08-12, temporal-semantics repair — r1 dry-run 이 semantic defect 를 노출한 뒤 개정)**

- **r1 지위**: 배선(parity·monotone·nesting)은 유효했으나 **non-discriminative** —
  reachability horizon 이 미명세 상태에서 episode 경과시간 (T=t·dt, 실측 18 s →
  d_max 332 m) 으로 인스턴스화됨. 전 bad witness 가 공통 출발점 p_att 를 가지므로
  (fixed-state 구조상 자연), 낙관 배치가 그 근방에 허용되어 U≡1.0 (공허·sound).
  **r1 에서 분기 판정을 내리지 않는다** (G7-4 최종 판정 아님 — spatial relaxation
  의 한계가 아니라 temporal reference-frame mismatch).
- **진단 반사실 (비확증)**: 동일 상태에서 T=τ 치환 시 U4 1.0 → 0.078. 이 값은
  **r2 채택의 근거가 아니라 r1 underspecification 발견의 진단**으로만 기록한다.
  r2 채택 근거는 결과와 독립: **fixed-state certificate 의 causal horizon 은
  미래다** — 과거 경과시간은 이미 snapshot 상태 (p_i(t), v_i(t)) 에 반영돼 있어
  새 control authority 를 제공할 수 없다.
- **r2 핵심 정의**: `R_i^rel = 현 snapshot limiter 상태에서 [0, τ_deploy] 의
  outer reachable set`. episode initial state·elapsed time 사용 금지.
  포함관계 규율 (r1 의 "상한은 덜 허용해야 tight" 논증 폐기):
  `F_constructive ⊆ F_physical ⊆ F_relaxation` — 상한 feasible set 의 축소는
  `F_physical ⊆ F_rel,new` 가 보장될 때만 허용된다. r2 의 R_i^rel 은 향후
  실제 도달가능 집합의 outer superset 이면서 r1 의 elapsed-time superset 보다
  엄밀히 작은 relaxation 이므로 적법.
- **오염 통제**: r1 dry-run 의 19 상태 (chi1.2·kappa0.2, ep 0–1) + 진단 상태
  (ep0 t360–362) = **development set — r2 confirmatory 집계에서 제외**.
  r2 primary tranche = **미접촉 에피소드 20..39** (동일 draw 경로·동일 predicate).
- **τ 2층 의미론** (claim 분리 — 혼용 금지):
  (A) capture physics: τ=0.30 s 는 optimistic lower-bound deployment delay
  (누락 latency 항은 전부 증가 방향, χ∝τ²) — 이 층에선 lower-bound 표현 유효.
  (B) 게이트 7: 같은 τ 가 limiter 의 미래 이동시간이기도 하므로 τ 증가는
  공격자·limiter reach 를 **동시에** 키운다 → U4(τ) 단조성 미보장, negative
  result 의 더 큰 τ 로의 자동 확장 주장 금지. 안전 문구: *"Gate 7 evaluates
  whether limiters, from their contemporaneous snapshot states, can affect the
  escape bundle within the modeled 0.30-s deployment window."*
  τ∈{0.3, 0.4, 0.5, 0.6} sweep 은 추후 **비확증 sensitivity** 로만 (main 과 분리).
- **신규 unit gate**: **G7-F** elapsed-time invariance — 동일 물리 snapshot 에
  t 메타데이터만 바꿔도 U^rel 동일. **G7-E′** — reach 상계를 snapshot 속도 포함
  τ-horizon 형 `min(v_max·T, |v0|·T + ½·a_max·T²)` 로 갱신해 반례 탐색.
- **금지 유지**: NK-존 추가 금지 · 기타 신규 tightening 금지 · optional blocking
  relaxation 유지 · 나머지 r1 조항 (solver bound semantics, nested grid, A_ijk
  no-false-negative, G7-1~4 분기, H4-lower 처리) 전부 불변.
- **보고 의무 추가**: 상태별 `n_sigs`(reachable-covering signature 수) ·
  `frac_bad_touched`(reachable cell 이 하나라도 건드리는 bad tube 비율) ·
  `ΔU = U4 − U1`. 목적: 게이트 7 이 닫히더라도 **"blocker 수의 효과"** 와
  **"deployment window 내 인과 도달 자체 불가"** 를 구분해 보고한다
  (후자면 결론은 "cooperation fails" 가 아니라 "window too short for any
  limiter to causally influence the escape bundle from sampled snapshots").

- **|v₀| ≤ v_max invariant**: `d_max_outer` 의 `v_max·τ` 항이 상계이려면 snapshot
  limiter 속력이 v_lim 이하여야 한다. adapter 가 상태별 검사 (위반 시 invalid) —
  실측: hold 모드 limiter 는 정확히 정지 (미접촉 ep 50 에서 max |v₀| = 0.000).

### r2 primary 판독 표 (결과 열람 전 고정 — closed fraction 단독 판독 금지)

| primary 패턴 | 해석 | 분기 |
|---|---|---|
| `U4<θ` · **대부분 n_sigs=0** · U4≈U1≈baseline | blocker 수 부족이 아니라 **τ-window 내 어떤 limiter 도 escape bundle 에 인과 개입 불가** | **①-B (reachability-limited)** — headline 은 "temporal authority 부재", 설계 변수가 "몇 기" → "언제부터 shaping" 으로 이동 |
| `U4<θ` · n_sigs>0 · ΔU>0 | 협력이 upper feasibility 를 올리지만 θ 미달 | **①-B (cooperation helps but cannot rescue)** — 협력 한계량 정량화, 최선의 결과 |
| `U4<θ` · n_sigs>0 · ΔU≈0 | reachable 봉쇄 존재하나 blocker 수의 한계효용 ≈ 0 | **①-B (blocker-count saturation)** |
| `U1<θ≤U4` 상당수 | N=4 협력 가능성이 상한 수준에서 생존 | **AMB 유지 / G7-2** → lower optimizer |
| 대부분 `U4≥θ` | r2 relaxation 도 판별력 부족 | **①-C** (더 이상 정의 수정 없음) |
| refinement/nesting/soundness 위반 | 방향 무관 | **artifact invalid** |

`frac_bad_touched` 병독: n_sigs=0·touched=0 = causal reach failure / touched≪1 =
coverage 희박 / touched 높은데 U4<θ = geometry·score 구조가 rescue 차단 /
touched≈1·U4≥θ = 낙관성 잔존. **τ=0.30 headline 은 "registered 0.30-s deployment
window 에서" 로 한정** — 더 큰 τ 로의 확장은 τ sweep (비확증) 이후에만.

---

## (이하 r1 본문 — r2 에서 명시 수정된 조항 외 전부 유효)

**r1 (2026-08-12, 구현 착수 전·결과 0 상태에서 개정)**: 교차검증 후속 검토가 지적한
false-INF 경로 4종을 봉합 — ① R_i outer-superset 의무 (FATAL) · ② solver
best-bound semantics (FATAL) · ③ objective = registered v_shot 직접 최적화 (FATAL) ·
④ nested dyadic grid + 부등호 `≥` 정정. 추가: A_ijk no-false-negative 규칙 ·
G7-1 "대부분" 정량화 (사전 threshold) · 수치 인증 여유 · G7-A exact-truth 정의.
r0 대비 질문·범위·분기 구조는 불변, soundness 조항만 강화.

**지위**: 게이트 10 판정 기준 (docs/78) 과 동형의 선봉인 문서. 교차검증 v2
(`third_party_feedback.md` §19) 와 후속 게이트-7 설계 지침을 적분해 **구현 시작 전에**
질문·soundness 의무·unit gate·분기 규칙을 고정한다. 이 문서를 본 뒤 결과에 맞춰
수정하는 것은 docs/74 §7 위반이다 (수정은 새 리비전 + 새 태그로만).

선행 진단 (완료): F-0a ✅ Case 1 (스크린 무죄, false-INF 0/210) · F-0b ✅ island 0/1300
(H3 강약화) · F-0c skip (조건 미충족). 판세 갱신: **①-B scoped negative ~80 : 미해결·재설계 ~20.**
남은 주 경쟁가설 = **H4-upper** ("AMB 는 상한이 헐거워서 남았나") — 게이트 7 이 이것만 답한다.

---

## 1. 단일 질문 (이것 외 금지)

```
AMB 상태 z 에서   U^rel_{≤N}(z) < θ = 0.9   인가?   (N ≤ 4, U^rel_{≤1} 병산)
```

- **YES → INF 가 sound 하게 닫힌다** (constructive 하한이 0 이어도 무관 — sound 상한이
  θ 미만이면 어떤 solver 로도 COOP 는 존재 불가).
- **NO → "COOP 있음" 이 아니라 AMB 유지.** 이 구분을 흐리는 서술 금지.

## 2. Relaxation 정의 (낙관 방향 고정 — 모든 근사는 defender 유리 쪽으로만)

- **배치 후보 영역 [FATAL 조항 — r2 로 semantics 확정]**: `D ∩ R_i^rel`.
  **r2**: `R_i^rel` = **현 snapshot limiter 상태 (p_i(t), v_i(t)) 에서 미래
  horizon [0, τ_deploy] 의 outer reachable set** — 거리 상계
  `min(v_max·τ, |v_i(t)|·τ + ½·a_max·τ²)` (두 상계의 min 도 상계; G7-E′ 로 봉인).
  episode 경과시간 사용 금지 (G7-F 로 봉인). `R_i^true ⊆ R_i^rel` 필수 —
  reachability predicate 의 **false negative 금지** (inner approximation 이면
  실제 0.92 가 가능한 배치를 놓쳐 false-INF).
- witness j 의 blocker tube `B_j = γ_j ⊕ Ball(r_kill)` (기존 게이트 6 정의 재사용).
- **낙관 사건 행렬 + no-false-negative 규칙**: `A_ijk = 1 ⇔ C_k ∩ B_j ∩ R_i^rel ≠ ∅`.
  cell 내 서로 다른 점이라야 각각 막을 수 있는 witness 들도 **동시 차단 credit**.
  수치 교차판정이 애매하면 (tolerance 경계) **반드시 1 (blockable) 쪽으로**:
  false positive (못 막는데 1) 는 상한을 느슨하게 할 뿐 sound, false negative
  (막을 수 있는데 0) 는 **금지**.
- **objective 봉인 [FATAL 조항 — 선택 A]**:
  `U^rel_{≤N}(z) = max_{배치} v_shot^rel(z, 배치)` — **registered `v_shot` 산식
  (`eval_union_with_limiter_sets`) 자체를 직접 최적화**한다. "blocked bad mass
  최대화" 등의 proxy objective 는 v_shot optimum 과의 대수적 동치가 증명되지 않는 한
  금지 (proxy optimum ≠ relaxation optimum 이면 false-INF). witness family·
  turn-feasible 필터·G=0 조임 등 나머지 전부 게이트 6/pilot 과 동일, 차단 판정
  predicate 만 cell-level A_ijk 로 대체.
- **N-배정**: ≤N 기의 limiter 를 cell 에 배정 (구조상 multiple-choice max-coverage
  /MILP). **서로 다른 limiter 의 동일 cell 선택 허용** (collision/packing 무시 —
  낙관 방향). N≤4·cell 유한 → 전수 또는 exact MILP.
- **solver bound semantics [FATAL 조항]**: maximization 에서 timeout/non-optimal
  종료 시의 incumbent 는 `U* ≥ incumbent` 인 **하한**이다 — 절대 `U^rel` 로 쓰지
  않는다. **INF 판정에 쓸 수 있는 것은 exact OPTIMAL 해 또는 solver 의 certified
  global best bound 뿐.** `best_bound < θ` 일 때만 INF, `best_bound ≥ θ` 또는
  certified bound 부재 시 **AMB 유지**. 결과 JSON 에 solver status·incumbent·
  best_bound·optimality gap 전부 기록.
- **refinement grid**: 동일 origin·동일 bounding domain 의 **fixed-origin dyadic
  nested partition** — 각 fine cell 은 정확히 하나의 parent coarse cell 의 subset
  (`∀C^{h/2} ∃C^h: C^{h/2} ⊆ C^h`). 이 조건 하에서만 `U^(h/2) ≤ U^(h)` 가 보장된다
  (origin/clipping 이 바뀌면 monotonicity 자체가 무의미). monotone tightening 이
  correctness signature — 단 **등호 허용** (coarse 에서 이미 exact 이면 상수열도 정상).
- **수치 인증 여유**: θ 비교는 outward rounding (상한 쪽 eps_num = 1e-9 가산) 후
  수행. v_shot 이 정수 witness count 비율로 환원 가능하면 exact rational 비교 우선.

## 3. Unit gates (전부 PASS 전 서버 long-run 금지)

| gate | 내용 | PASS 기준 |
|---|---|---|
| **G7-A** synthetic truth | **exact truth V\*** 를 아는 소형 geometry 4종: clearly blockable / clearly unblockable / N=1 불가·N=2 가능 / **outer-relaxation trap** (두 witness 를 같은 cell 의 상이점만이 막음). V\* 는 analytic 또는 exhaustive **exact** enumeration (유한 case 환원) 으로만 정의 — brute-force 로 "찾은" V_found 는 truth 자격 없음. trap fixture 는 의도적으로 coarse h 에서 `U_h > V*` 가 나고 refinement 로 `U ↓ V*` 하도록 설계 (낙관 방향 검증) | 전 케이스 `U^rel ≥ V*`. **위반 1건 = 게이트 7 전체 무효** |
| **G7-B** refinement monotonicity | nested dyadic h, h/2, h/4 | 전 인스턴스 `U_h ≥ U_{h/2} ≥ U_{h/4}` (등호 허용, 역전 = 구현 버그) |
| **G7-C** random placement domination | 연속 배치 수천 표본의 최고값 V_found | 항상 `V_found ≤ U^rel` (regression guard, proof 아님) |
| **G7-D** N nesting | N = 1..4 | `U_{≤1} ≤ U_{≤2} ≤ U_{≤3} ≤ U_{≤4}`. **U^rel_{≤1} 산출 의무** — 최초로 SINGLE/COOP/INF 형식 분리 기반 제공 |
| **G7-E** reachability 방향성 | `_reach_ok` outer-superset 증명 (§2 첫 조항) | 무작위 (T, v_max, a_max) 표본에서 실제 도달 가능 지점이 predicate false 가 되는 반례 0 |

## 4. 실행 범위 (전체 40셀 금지 — AMB-only)

1. pilot: chi ∈ {0.8, 1.2, 1.6} × kappa {0.2, 1.1} × N=4 (+U^rel_{≤1}), mu=0.4.
   **chi=1.2 최우선** — 여기서 `L_4=0 ∧ U^rel_4<0.9` 가 refinement 안정으로 닫히면
   논문 핵심 그림. chi=0.8 은 negative-control (easy-side sanity).
2. 이후 **AMB 상태만** adaptive 확장. cheap 상한이 이미 INF 인 상태의 재계산 금지.

## 5. 분기 규칙 (기존 "AMB→INF 면 ①-B 확정" 을 대체)

**판정은 원칙적으로 cell 단위로만 보고한다** (global "대부분" 재량 제거). headline
사용 조건만 아래처럼 수치로 선등록한다 — threshold 는 결과 0 상태인 지금 선언하는
동결값이다:

| Case | 조건 (사전 정의) | 판정 |
|---|---|---|
| **G7-1** | **primary 셀 (chi ∈ {1.2, 1.6} × kappa {0.2, 1.1} × N=4) 각각에서** engaged 상태의 certified-INF 비율 (cheap-INF + 게이트7-INF) **≥ 0.95** 이고 잔여 AMB ≤ 0.05, 그리고 refinement 안정 (`U_h ≥ U_{h/2} ≥ U_{h/4}`, 최종값 `< θ − eps_num`) | **①-B scoped negative 확정.** headline 상한: *"Within the registered fixed-state static-blockade model, up to four path-limiters cannot recover net-capture feasibility in the high-chi regime over the tested attacker-induced state distribution."* 셀별 수치 표 필수 병기 |
| **G7-2** | 어느 primary 셀이든 AMB 잔여 > 0.05 (`U^rel ≥ θ` 또는 certified bound 부재, `L=0`) | **①-C.** 이때만 H4-lower (continuous constructive optimizer) 를 **잔여 AMB 셀 한정** 투입 |
| **G7-3** | 임의 상태에서 `U^rel_{≤1} < θ ≤ L_4` 또는 강한 constructive 양성 | **COOP branch 재개** (F-0b 이후 가능성 낮음) |
| **G7-4** | refinement h/4 까지 상한이 실질 불변인데 θ 위 (`U_{h/4} ≥ θ`, `U_h − U_{h/4} < 0.02`) | relaxation quality 문제 = **①-C** (solver 확전 금지) |

## 6. H4-lower 처리 (결과 전 고정)

- **후보 배치 확장 금지** — 결과 본 뒤 lower 강화는 researcher degrees of freedom 재개방.
- **positive control 실측 완료 (2026-08-12)**: 동일 LN 파이프라인이 pilot chi 0.4 에서
  LN_max **1.0** (N1·N4), chi 0.8 에서 **0.981/0.990** — detector 는 양성을 낼 능력이
  있고 chi≥1.2 의 LN≡0 은 detector 사망이 아니다.
- 구현 동일성: certificate core (`viability.py`) 는 pilot↔F-0 전 커밋에서 무변경,
  pilot 스크립트는 `8da6e43` ↔ 현 HEAD 동일 (git diff 0). **provenance 각주**: 일부
  pilot 샤드 스탬프 `993cc5b` 는 스크립트 커밋 이전 시점 — 서버 dirty-tree 실행으로
  추정, 이후 커밋 `8da6e43` 과 동일 코드로 간주하되 각주로 남긴다.
  **후속 (게이트 7 비차단)**: "동일 코드로 간주" 를 논문 증거로 쓰지 않기 위해,
  clean HEAD 에서 chi 0.4/0.8 positive-control 셀 몇 개를 재실행해 LN_max ≈ 1.0
  재현으로 provenance 를 닫는다 (서버 여유 시).

## 7. 부속 확정 사항 (게이트 7 범위 밖, 서술 규율)

- **κ onset**: κ* = 3.0/ρ = 3.0/1.77 ≈ **1.69 — Z_master kappa 축 (max 1.20) 밖**.
  즉 사전 예측 발현점은 봉인 격자 안에서 시험 불가 — 시험하려면 격자 확장
  **새 사전등록** 필요 (게이트 7 에 섞지 않는다). κ-flat 서술 금지 유지:
  *"no κ sensitivity over the tested pre-onset range"* 까지만.
- **chi claim hierarchy**: ① observed certificate boundary ✅ → ② pre-screen-independent
  ✅ (F-0a) → ③ dimensionless collapse / scaling law — **게이트 10 iso-Π 이후에만**.
  현재 ①–② 확보. "chi is the governing parameter" 류 서술은 ③ 전 금지.
- 동결 유지: MARL 재학습 금지 · richer attacker 금지 · F-0c skip.

## 8. 산출물 규칙 · 구현 순서

`shepherd/scripts/gate7_relaxation.py` (본체) + `tests/test_gate7_soundness.py`
(G7-A~E). 모든 결과 JSON 은 `stamp(artifact="phase3_gate7_...", lattice_hash=...)`
필수 + solver status·incumbent·best_bound·gap (§2). unit gate 결과도 JSON
(`results/phase3/gate7_unitgates.json`).

구현 순서 (test-first): **① `eval_union_with_limiter_sets` 정독** — (a) limiter 가
witness 를 제거하는 정확한 지점 (b) good/bad/feasible witness 정의 (c) v_shot
분자·분모의 배치 의존성 (d) `n_feasible==0`/`G==0` 특수 케이스. 여기서 proxy
objective 동치 여부를 판정한 뒤에만 formulation → ② G7-A fixtures 4종 작성 →
③ 최소 solver → G7-A PASS → ④ G7-B nested refinement → ⑤ G7-D N nesting →
⑥ G7-C random domination → ⑦ clean stamped 로컬 pilot → ⑧ 서버 chi=1.2.
