# 73 — 리뷰 10~15 판정 로그 (방향 전환 심사) + 이행 목록 — r3.2

**2026-08-09 · 요청 = `docs/review_prompt_design_map_pivot.md` (리뷰 10) +
`docs/review_prompt_blueprint.md` (리뷰 11) · 대상 = spine 교체 (학습 이득 증명 →
메커니즘 성립 조건). 결과 = **전환 조건부 승인 · 현 서술로는 불승인 → 조건 이행 후
재승인**. 반론 없이 전부 수용. r0 = 리뷰 10 / r1 = 리뷰 11 (A1~A8 + 청사진) / r2 = 리뷰 12 의 수정 5+2 / **r3 = 리뷰 13 의 blocker 5 + protocol leak 6~14. 전부 지도 셀 생성 전 (Phase III 셀 0 개).**

**★ r1 최상위 정정 (리뷰 11)**: `2026-12-18` 은 **URP 행정 마일스톤이지 연구의
종료선이 아니다.** 12/18 에는 "어디까지 완결해 보고할지"만 정하고, 저널 증거 bar 는
기간과 무관하게 유지한다. **시간 때문에 C3/C5/certificate 를 잘라내지 않는다.**
r0 §8 의 "19주 축소 일정" 은 폐기하고 `docs/75_blueprint.md` 의 **과학적 게이트**로
대체한다.

## 1. 판정표

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| 1 | Q-A 축 교체 | **CONDITIONAL** | chronology 잠금 = `docs/74_pivot_protocol.md` (오늘 날짜) |
| 2 | F2 "협력 marginal value = 0" | **REJECT** | **철회.** 표현 하향 + `U_{<=1}` vs `L_{<=N}` bound 로 재설계 (r1) |
| 3 | 충분경계 upper certificate | **RATIFY (필수)** | r1: 싼 것부터 — unblockable bad mass → finite-candidate exact(MILP) → continuous outer relaxation → reachable constructive lower + 독립 judge cross-check. **★ r3 supersession: finite exact MILP 는 certificate hierarchy 에서 제외** (solver/audit auxiliary) — 후보집합은 continuous 불가능을 certify 하지 않는다 |
| 4 | Q-B 파라미터 축 승격 | **CONDITIONAL (거의 RATIFY)** | 파라미터를 4 종으로 **분류** + 구간 출처 사전 고정 |
| 5 | C5 재실행 | **CONDITIONAL** | adaptive two-stage + 결정론적 선택규칙 + **3 regime 동시** |
| 6 | F1 라벨 반전 | **REJECT — 현 regime 정의** | `0.5aτ²>ρ` 는 **proxy** 로 강등, regime 은 `V_0` + `L/U` bound 로 재정의 |
| 7 | θ_fire 축 | **CONDITIONAL** | miss-risk/탄약경제 주장 금지. "viability-envelope sensitivity" 로만 |
| 8 | 대안 프레임 | **RATIFY** | spine = *Feasibility-First Design of Cooperative Single-Shot Counter-UAS Interception under Deployment Latency* |
| 9 | Q1 증거 bar | **CONDITIONAL** | 3층(geometry certification / RL / robustness) 채택, 통계단위 = **episode** |
| 10 | 19주에 C1~C5 전폭 | **REJECT — 현 범위** | r1 정정: 12/18 은 행정 마일스톤. **시간으로 자르지 않고** 과학 게이트로 진행 (docs/75). 넣지 않는 것 = Paper 2~5 주제뿐 |
| 11 | desk-reject 문장 | **RATIFY (실재 위험)** | §4 에 전문 인용, 연구 전체의 방어 목표로 등재 |

### 1.1 리뷰 11 (봉인 검증 A1~A8) — 전부 수용

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| A1 | 봉인의 감사 가능성 | **CONDITIONAL** | pivot manifest + git tag + 외부 timestamp + 산출물 `protocol_hash` 스탬프. "verified unread" 금지 → "not inspected for scientific decision-making" (docs/74 §0, `shepherd/scripts/pivot_manifest.py`) |
| A2 | Phase II 한계 기재 | **REJECT (2 건 누락)** | **B1 counterfactual trajectory inconsistency** (반응형 공격자의 causality 절단) · **B2 common-mode bias** (같은 judge) 추가 + 독립 judge cross-check 필수 (docs/74 §2) |
| A3 | Stage-2 선택규칙 | **REJECT** | "band center" 폐기 → **certified opportunity 유병률 `p_C(z)` 의 LCB95 최대점**. primary 중복 해소(interaction 하나). eligible 점 없으면 **C5 협력 팔 미실시** (docs/74 §4) |
| A4 | `V_0/V_1^*/V_N^*` 정의 | **CONDITIONAL** | `<=N` 표기 + 3 층 분리 + bound 기반 분류 (§3, docs/74 §3.1~3.2) |
| A5 | measure (R) | **RATIFY (조건)** | θ 를 상수로 방어하지 않는다. 산출물 = `L/U` 연속 surface + θ ∈ {0.80…0.95} 슬라이스 (docs/74 §3.3) |
| A6 | 무차원 축 | **CONDITIONAL (아직 모른다)** | 후보 확장(`nu`,`lambda`,`R_standby/rho`,`R_detect/rho`,`D_asset/rho`,`alpha`) + **iso-Π collapse test** 를 그림으로 (docs/74 §3.6) |
| A7 | 표본 20~30 | **CONDITIONAL** | **replicate 를 줄이지 말고 cell 을 줄인다**: coarse 20~30 / boundary 60~100+ / Stage-2 3점 100~300 (docs/74 §3.5) |
| A8 | 동결 9 런 처리 | **RATIFY** | null 인용 원문 채택 — "**motivated, but does not validate**" · Phase III 는 "mechanism-consistent explanation" 까지만 (docs/74 §6) |

### 1.2 리뷰 12 (r1 심사) — CONDITIONAL → 5+2 수정 후 RATIFY. 전부 이행

| # | 항목 | 판정 | 이행 |
|---|---|---|---|
| 1 | §3 ↔ §5 의 `L<=V<=U` **모순** (snapshot certificate ↔ closed-loop 량을 한 sandwich 로 합침) | **REJECT (논리 오류)** | 고정상태 sandwich `L^reach <= V^reach <= V^rel <= U^rel` 와 `L^ctrl` 을 **분리**. 순서관계 주장 금지 (§3, §5, docs/74 §3.1, docs/75 §0) |
| 2 | `W_{2:N} = ∅` → negative result 직행 | **REJECT (논리 오류)** | **3 분기** (A single-agent sufficiency / B mechanism infeasibility / C unresolved gap). C 는 **결론 없음**. docs/74 반증조건 ① 소급 수정 (§5.1) |
| 3 | 라벨이 상호배타 아님 (`FREE` ↔ `CERTIFIED SINGLE` 중첩) | **REJECT** | `SINGLE-NEEDED` / `COOP-NEEDED` 로 재명명 + 상호배타 정의. `N_req` 는 닫히지 않으면 **UNRESOLVED** (모든 상태에 존재하지 않는다) |
| 4 | `Delta_coop` 가 어느 층의 이득인지 모호 | **REJECT** | 층별 표기 `Delta^rel_N` / `Delta^reach_N` / `Delta^ctrl_N (= J(pi_N)-J(pi_1), 경험적 차이)`. 메인 논문은 `U^rel_{<=1} < theta <= L^reach_{<=N}` 한 줄로 밀고 `Delta_coop` 를 앞세우지 않는다 |
| 5 | "필요시 eta" = 잔여 자유도 | **REJECT** | **deterministic escalation rule** (§3.1): candidate Π-set 사전 고정 · core `(chi,kappa,mu)` · tolerance 통과 시 채택 · 실패 시 `eta -> alpha -> lambda -> nu -> ...` 순서 고정 · 그래도 안 되면 "no low-dimensional collapse supported" |
| + | "certificate 전 계층 강제" | **수정 권고** | **certificate hierarchy** 로 (§8): 싼 sound bound 로 닫힌 셀엔 상위 solver 미적용, 셀별 사용 수준 공개 |
| + | Q1 bar 의 "mobility 2~3 층" | **수정 권고** | `mu` 가 이미 mobility 축 → 표현 폐기. core map = validated Π-space + discrete N, non-core 는 사전 지정값 고정 + matched slice (§7) |

### 1.3 리뷰 13 (r2 심사) — CONDITIONAL → blocker 5 + leak 6~14 이행 후 RATIFY

| # | blocker | 판정 | 이행 (docs/74 r3) |
|---|---|---|---|
| 1 | `L^reach` 는 문서에만 있고 알고리즘은 `L^ctrl` 만 계산 | **치명적** | **4A/4B 분리** (§3.7): 4A = 고정 `(e,t)` 에서 `D_i^reach` 안의 배치로 **같은 witness set** 평가 → `L^reach_{<=N,clean}` (certificate) / 4B = 반응형 env rollout → `L^ctrl` (실현 검사, sandwich 에 넣지 않음). 시간축 `(x,T_s)` 폐기 → **reference encounter 시각 `(e,t)`** |
| 2 | `C_N(x)` 가 episode 인지 state 인지 불명 | **치명적** | state-level `C_N(e,t)` + **전 스텝 sound screen**(사후 선택·stride 금지) + `C_N^ep(e)` + `p_C(z)` = **prevalence under the pre-specified scenario distribution** (§4.1). **★ r3.2: r3 의 persistence `m=3` 은 폐기** — τ 가 이미 sense+decide latency 를 포함해 이중계산이었다 → **m=1(존재) primary + dwell-time 분포 secondary** |
| 3 | clean-fire 의 `not boxed-in` 이 certificate 에서 누락 | **치명적** | `g_theta = 1[v>=theta AND NOT boxed]`. **constructive lower 는 `g_theta=1` 배치만 유효**, upper 는 boxed 무시가 sound (비대칭 명시) (§3.2) |
| 4 | adaptive refinement <-> "pre-specified finite grid" 충돌 | **중대** | **master lattice `Z_master` 선봉인 + `lattice_hash`**. adaptive 는 "다음에 어느 master 점을 계산할지"만 (결정론 정책 4 단). Stage-2 점은 `Z_master` 안에서만 → compute allocation 허용 / hypothesis-space 생성 금지 (§3.8) |
| 5 | interaction 이 통계적 estimand 가 아님 | **중대** | comparator = **같은 N 기의 freeze 된 constructive controller `B_N`** (reachable 1-limiter 아님 — learning x team-size 혼합 방지). `delta_r = p_net^{MARL_N,r} - p_net^{B_N,r}`, **`Gamma = delta_COOP - (delta_FREE+delta_HARD)/2`**, 성공 = `LCB95(Gamma) > 0`. `N=1` 은 secondary mechanistic (§4.4) |

| leak | 이행 |
|---|---|
| 6 finite MILP 의 지위 | certificate hierarchy 에서 제외 → **solver/audit auxiliary**. "Failure to reach theta in the finite-candidate exact problem does not certify continuous-domain infeasibility" 등재 |
| 7 witness semantics | **path witness** (완전 궤적 + 종단 상태) → `B_j = gamma_j (+) Ball(r_kill)` 이 의미를 가짐. `v_shot` = feasible **path** witness 의 가중 coverage |
| 8 Pi 축 | **결과 보고 축 추가 폐기** → Buckingham-Pi 를 **분석적으로 먼저 완성**·전부 기록·2~3 개만 plotted·나머지 conditioning. iso-Pi = **reduction validation**. `lambda=L_axial/rho`·`R_standby/rho` 는 rho 변경 시 자동 변화 |
| 9 §7 <-> §3.9/§5-4 모순 | 반증조건 발동 = **현 Phase III 종료(falsified)** → 축·measure 변경은 **새 `Phase III-B` protocol 을 새 hash 로 사전등록** 후 재시작 (§5.1) |
| 10 `p_C` CI·eligibility | **Clopper-Pearson one-sided 95%**, 단위 = episode. eligible = `LCB95 > p_min = 0.05` **AND** 성공 episode >= 5. tie = lexicographic. eligible 없으면 **협력 C5 미실시** |
| 11 matched control metric | **normalized L_inf** 거리. FREE = 최근접 FREE 셀 / HARD = 최근접 `LOCAL-INFEASIBLE-N`. **AMBIGUOUS 를 HARD 로 쓰지 않는다** |
| 12 라벨 이름 | **`CERTIFIED LOCAL-SINGLE-NEEDED` / `LOCAL-COOP-NEEDED` / `LOCAL-INFEASIBLE-N`** (LOCAL 생략 금지). 용어 = **local certified cooperative opportunity** |
| 13 judge 일치 판정 | **boundary-aware**: signed margin `|m1-m2| <= eps` (1e-6 m / 1e-9). predicate 불일치는 `|m| <= eps` boundary case 에서만 허용, **boundary 에서 먼 불일치 1 건이면 지도 중단** |
| 14 태그 | **태그 이동 금지** → `PIVOT_LOCK_R2/R3_...` revision 명 분리. **자백: r1 에서 태그를 `-f` 로 한 번 이동시켰다** (`c6e8081`→`3aec425`, Phase III 셀 0) — 이후 없음 |

### 1.4 리뷰 15 (73·74 대조 최종) — 체크리스트 11 항 전부 이행 → RATIFY 조건 충족

| # | 항목 | 이행 |
|---|---|---|
| 1 | `stride 4` 가 `m` tick 기회를 놓칠 수 있다 (**실 논리 오류**) | stride 스캔 **금지**. **전 스텝** cheap **sound screen** (`U^cheap_{<=N} >= θ`, 위반 시 `C_N=0` 보장 = false negative 불가) 후 비싼 계산만 선별 (docs/74 §3.1) |
| 2 | Stage-2 θ 미고정 = 지도 보고 유리한 θ 선택 가능 | **`theta_S2 = 0.90` 고정** (원 시스템 동결값). 다른 θ 는 **sensitivity 전용, 선택·판정 사용 금지** (§4.1) |
| 3 | matched control 의 N 이 달라질 수 있음 (team-size confound) | `N_FREE = N_HARD = N_B`, θ 도 동일. 거리 최소화는 **같은 N 부분집합 안에서만**, N 은 거리에 넣지 않는다 (§4.3) |
| 4 | 개별 `D_i^reach` 곱집합 ≠ joint feasibility (충돌) | 4A 성공 조건에 **joint time-parameterized 궤적 N 개 구성 + 전 구간 가속·속도·NK·pairwise 충돌 동시 만족** 추가. 없으면 `L^reach` 가 sound lower 가 아니다 (§3.7) |
| 5 | parameter cell 의 단일 라벨 규칙 부재 | **단일 색 지도 폐기** → 셀마다 **label prevalence 벡터** `p_FREE/p_SINGLE/p_COOP/p_INF/p_AMB`, 핵심 surface = **`p_C` 와 `p_AMB`** 병기 (§3.9b) |
| 6 | `m=3` 이 τ 와 latency 이중계산인지 확인 | **이중계산 확인** — `M4_PROVENANCE` 원문: τ=0.30 은 "커밋에서 포획 판정까지의 지연" = flight 0.15 + **sense 0.10 + decide 0.05**. → **m=1 로 교체**, dwell-time 은 secondary |
| 7 | 73 §5 에 철회된 논리가 현재형으로 남음 | **교체** (r2 패치가 조용히 실패했던 것). §5 + **§5.1 3 분기** 신설 |
| 8 | 73 §2 의 옛 `N_req` 정의 | bound-certified 정의로 교체 + provisional 정의는 **역사 기록**으로 표기 |
| 9 | 73 §3.1 escalation rule ↔ 74 r3 §3.9 충돌 | escalation rule **superseded** 로 교체 (full Π-set 선확정 · 결과 후 축 추가 금지) |
| 10 | 73 §7 C5 요약이 구버전 | `B_N`·`Gamma`·LOCAL 용어·동일 N/θ 로 동기화. **N=1 은 secondary** 명시 |
| 11 | Phase I primary 와 null 문구 불일치 | docs/63 r2 primary = **overall paired Δ_net** 확인 → 인용문을 **"did not support the preregistered superiority claim on the paired net-capture endpoint"** 로 교체 |

### 1.5 자체 감사 (2026-08-09b) — **r3.3**. 외부 리뷰 아님, docs/76 조사 중 발견

docs/76 선행연구 조사에서 "협력 채널이 kill-sphere removal 하나뿐" 이라는 자기서술의
근거를 확인하다가 **`docs/46_channel_split.md` (2026-08-01) 를 재발견**했다. 그 문서는
채널을 이미 **분리 계측**해 두었고, 결론이 현 계약 문구와 **충돌**했다.

| # | 발견 | 판정 | 이행 (docs/74 r3.3) |
|---|---|---|---|
| 1 | docs/75 §7 · docs/74 §3.0 의 "협력 채널 하나뿐" 이 **사실과 다르다.** docs/46 이 채널 3 종을 계측했다 (봉쇄 / 횡압 / 체류) | **부정확 — 교체** | §3.0 을 **채널 대장**으로 교체. 정확한 진술 = "fixed-state certificate 가 정의상 채널 (i) 만 측정한다" (**항등식**: `V^rel_{<=N} − V_0` ≡ docs/46 의 채널 (i) 을 배치 최적화한 값) |
| 2 | 우리가 certificate 를 세운 채널 (i) 이 **선언 운용점 `r_kill=0.75` 에서 Δbest = 0.0000** 으로 실측됐다 | **중대 — 그러나 kill 아님** | docs/46 은 **손튜닝 배치**(hold/ring)로 쟀고 Phase III 는 **배치를 최적화**한다. 또 `kappa` 가 core 축이다 → §3.0.3 에 **사전 예측**(낮은 `kappa` `p_INF` 지배 / 높은 `kappa` 에서 발현)을 셀 생성 전에 기록 |
| 3 | 채널 (ii) 횡압이 **실측 음수**다 (`v⊥` 0.44→7.27, `ψ` 0.6°→28°, 평균 `v_shot` 0.394→0.036, ring 이 24 판 중 20 판 패) | **계약에 반영** | (a) `L^ctrl < L^reach` 가 **정상**임을 §3.3 에 명시 — 층 분리의 *물리적* 근거 (종전엔 규칙 선언뿐) · (b) §7 에 "이 관측을 `L^reach` 버그로 처리 금지" 추가 |
| 4 | `U^rel_{<=N} < θ` 를 채널 한정 없이 산문으로 쓰면 **docs/46 실측과 자가모순** | **금지 규칙 신설** | §3.4 채널 상속 규칙 + §5-1B 문구에 `via the static blockade channel` 강제 + §7 금지 문장 4 종. 라벨 개명은 **기각**(churn) 하고 **5 군데 중복 배치**로 대체 (항목 7 의 "조용히 실패" 재발 방지) |
| 5 | docs/46 §4.2 가 **결과 전에** 학습 목표·실패기준을 선언해 두었는데 Phase III 계약에 배선돼 있지 않았다 | **승계** | §4.4 에 `secondary (channel)` 신설 — `ch_i` / `ch_ii` / `dwell` 을 regime 별 병기. **판정 사용 금지**, `v_shot` 기준과 `p_net` 기준 `Gamma` 를 합치지 않는다 |
| 6 | `pivot_manifest.py` 가 `revision`·`tag_policy`·`supersedes`·`phase3_cells_generated_so_far` 를 **emit 하지 않는데 JSON 에는 있다** → 재실행 시 **조용히 소실** | **코드 버그 — 수정** | 스크립트가 네 필드를 생성하도록 수정 + `docs/46`·`channel_split.py` 를 `PHASE_FILES` 에 추가 (채널 증거가 이제 계약이 인용하는 자료) |

**성격**: 전부 **Phase III 셀 0 개 상태**에서의 정정이다 (`phase3_cells_generated_so_far = 0`).
결과를 보고 정의를 바꾼 것이 아니라 **결과 생성 전에 자기서술을 자료와 일치시킨 것**이다.
방향성 자기점검: 항목 2 는 **우리에게 불리한** 발견이고 (certificate 채널이 선언점에서 0),
그것을 숨기지 않고 사전 예측으로 등재했다 — 유리한 방향의 변경이 아니므로 선언 위험 없음
(docs/46 §5 규율과 동일 기준).

## 2. 즉시 철회하는 문장 3건 + 1 (오늘 기록에서 하향)

| 철회 | 대체 표현 |
|---|---|
| "결정 대역 = a_att ∈ [36, 39]" | "seed 0 의 선택된 스냅샷 · 테스트된 relaxed 탐색에서 **문턱 교차가 관측된 이산 점들**" (연속 구간도, 실제 시스템 feasibility band 도 아니다) |
| "N_req = 1 → 협력의 marginal value 가 기하적으로 존재하지 않는다" | "테스트된 relaxed 배치 탐색에서 발견된 모든 문턱 교차는 **첫 번째 봉쇄 구**로 달성됐고, 추가 구에서 표본 이득이 없었다" |
| "병목은 봉쇄 공급량이 아니다" | "후보 조밀화·구 추가가 빠르게 포화 → **요격기 수 단독이 지배적 병목은 아닐 수 있다**는 시사" |
| "그리디이므로 달성가능 하한" | "**relaxed static-placement 문제의 최적에 대한 하한**". 실제 시스템 최적 `V_N^actual` 과는 **순서관계 없음** (teleporting 배치가 1기에 유리하게 편향) |

또한 `N_req` 정의 오류 수정: `v_hold ≥ θ` 인 점(a_att 15/20/30)은 **N_req = 0** 이다.
당시 적용한 provisional 정의는 `N_req = min{N ≥ 0 : V_N^* ≥ θ}` 였으나 **r2 이후
bound-certified 정의로 superseded** 되었다 (역사 기록):

```
N_req = 0            if V_0 >= theta
N_req = k (k >= 1)   if U^rel_{<=k-1} < theta <= L^reach_{<=k,clean}
그 외                 UNRESOLVED   (certificate 가 닫히지 않으면 존재하지 않는다)
```

## 3. 채택하는 재정의 (새 연구에만 적용 — 동결 블록은 불변)

**★ r1 교체 (리뷰 11 A4)**: 단일 `V_N^*` 폐기 → **"최대 N" 표기 + 3 층 분리**.
정확히 N 기 강제는 단조성을 깨고, snapshot relaxed 값을 episode-level actual 의 상한으로
쓸 수 없다 (limiter 가 공격자 궤적을 바꾼다). 상세 = `docs/74` §3.1~3.2.

```
Local fixed-state problem  (같은 고정 encounter state x 에서만 정의된다)
------------------------------------------------------------------------
V^rel_{<=N}(x)         최대 N 개 static kill sphere, 연속 admissible placement domain
                       어디든 (mechanism oracle)
V^reach_{<=N}(e,t)     center 를 D_i^reach(e,t) (reference encounter 시각 t 까지
                       실제 동역학·NK·충돌 제약으로 도달 가능한 집합) 로 제한
L^reach_{<=N,clean}(e,t) 도달가능 + **not boxed** 배치가 달성한 값 (constructive)
U^rel_{<=N}(x)         V^rel_{<=N}(x) 의 sound upper bound

  => 고정 상태 문제에서만:
     L^reach_{<=N} <= V^reach_{<=N} <= V^rel_{<=N} <= U^rel_{<=N}

Closed-loop problem   (별도 층 — 위 sandwich 와 섞지 않는다)
------------------------------------------------------------
L^ctrl_{<=N}(x0; pi_c) 반응형 attacker 가 있는 원 환경에서 명시적 controller 가
                       달성한 값. **L^ctrl 과 고정상태 relaxed 상한 사이의 순서관계는
                       주장하지 않는다.**

Certified labels  (상호배타 — Fig 6 에서 한 셀에 한 색)
-------------------------------------------------------
FREE                          : V_0 >= theta
CERTIFIED LOCAL-SINGLE-NEEDED : V_0 < theta <= L^reach_{<=1,clean}
CERTIFIED LOCAL-COOP-NEEDED   : U^rel_{<=1} < theta <= L^reach_{<=N,clean}
CERTIFIED LOCAL-INFEASIBLE-N  : U^rel_{<=N} < theta
AMBIGUOUS               : 그 외 (지도에 그린다 — 숨기지 않는다)

N_req = 0               : V_0 >= theta
N_req = k (k >= 1)      : U^rel_{<=k-1} < theta <= L^reach_{<=k,clean}
그 외                   : **N_req = UNRESOLVED** (모든 상태에 N_req 가 존재하지 않는다)

층별 협력 이득 (하나의 Delta_coop 표기 금지)
--------------------------------------------
Delta^rel_N   = V^rel_{<=N}   - V^rel_{<=1}
Delta^reach_N = V^reach_{<=N} - V^reach_{<=1}
Delta^ctrl_N  = J(pi_N) - J(pi_1)   ← 특정 controller 간 **경험적 차이**일 뿐이며
                                      "optimal cooperative marginal value" 가 아니다
W_{2:N} = { x : N_req(x) in [2, N] }   (UNRESOLVED 는 포함하지 않는다)
```
**핵심 한 줄**: `U^rel_{<=1} < theta <= L^reach_{<=N}` — 왼쪽은 *1 기를 이상적으로
배치해도 안 된다* 는 상한 certificate, 오른쪽은 *실제 도달 가능한 N 기 배치가 된다* 는
constructive certificate. 이 둘이 함께 성립하면 "왜 N>1 인가" 가 증명된다.
메인 논문에서 `Delta_coop` 를 크게 밀지 않는다 — 이 한 줄이 더 직접적이다.

- `chi = a_att·tau^2 / (2·rho_net)` 은 **free-capture analytic proxy** 로 강등.
  **"필요 경계는 닫힌형 a* = 2rho/tau^2" 문장은 삭제**(포획면이 등방 볼이 아니라
  SE(3) 원뿔 + 축방향 밴드이므로 scalar 비교로 clean-fire 필요조건을 정의할 수 없다).
- 축: raw 6 knob 대신 **무차원**. core = `chi`, `kappa = r_kill/rho`,
  `mu = a_lim/a_att`. 확장은 §3.1 의 **escalation rule** 로만 (임의 추가 금지).
  6D Cartesian sweep 폐기.

### 3.1 무차원 축 — **r3 에서 정책 교체 (escalation rule 폐기)**

r2 의 deterministic escalation rule (`eta -> alpha -> lambda -> ...` 순 축 추가) 은
**리뷰 13 에서 superseded** 되었다. 현 정책 = `docs/74` r3 §3.9:

- governing equation·기하에서 **full Π-set 을 결과 전에 분석적으로 확정**하고 전부 기록.
- 그중 **2~3 개만 plotted axes**, 나머지는 **fixed conditioning variables**.
- iso-Π test 는 **reduction validation** (축 발견법 아님).
- **결과를 본 뒤 새 축·새 measure 추가 금지.** 필요하면 현 Phase III 를 종료하고
  **Phase III-B 를 새 protocol hash 로** 사전등록한다.

- **★ 동결 경계**: 진행 중인 docs/71 ablation 은 `regime_of` (기존 정의·기존 이름)
  로 계속 판정한다. 위 재정의는 **새 연구의 언어**이고 동결 블록에 소급 적용하지
  않는다 (그렇게 하면 primary 를 결과 후 바꾸는 것이 된다).

## 4. 방어 목표 (desk-reject 문장 — 원문)

> "The manuscript retrospectively recasts a failed MARL study as a systems-design
> result, but its claimed viability boundaries and requirements are properties of
> an unvalidated simulator whose decisive latency, kill radius, firing threshold,
> and threat capability were chosen by the authors rather than grounded in a
> physical context of use."

이 문장을 막는 것이 이 연구 라인 전체의 정의다 (기간 무관). 대응 축: (i) `v_shot` measure 정의·수렴,
(ii) upper/lower certificate 분리, (iii) 파라미터 분류 + 구간 출처 사전 고정,
(iv) hardware/context anchor 1 개 (없으면 "requirement" 대신 **design envelope /
parametric requirement curve** 로 표기), (v) latency/noise spot-check.

## 5. 즉시 착수 3 (리뷰 10 지정 · 리뷰 11 이 순위를 재확인)

**리뷰 11 "만약 하나만 고른다면" (r3.2 최종 문구 — r2 패치가 조용히 실패해 철회된
논리가 남아 있었다. 리뷰 15 항목 7 이 잡았다)**: 동일 `(e,t)` fixed-state 에서
`L^reach_{<=N,clean} <= V^reach_{<=N} <= V^rel_{<=N} <= U^rel_{<=N}` 를 계산하고,
`L^ctrl` 은 **별도로** 검증한다 (하나의 sandwich 로 섞지 않는다). 그 위에서
**FREE / LOCAL-SINGLE-NEEDED / LOCAL-COOP-NEEDED / LOCAL-INFEASIBLE-N / AMBIGUOUS**
의 **prevalence** 를 파라미터 점마다 보고한다 (셀 하나를 한 색으로 칠하지 않는다).

핵심 질문 = `U^rel_{<=1} < theta_S2 <= L^reach_{<=N,clean}` 인 상태가 실재하는가
(= **local certified cooperative opportunity**, `theta_S2 = 0.90` 고정).
**COOP cell 부재 시 "협력 불필요" 로 직행하지 않고** 아래 §5.1 세 경우로 분기하며,
**unresolved 에서는 negative claim 을 하지 않는다.**

### 5.1 협력 셀 부재의 3 분기 (negative claim 규율 — 리뷰 12 항목 2)

| 경우 | 지지 조건 | 허용되는 주장 |
|---|---|---|
| **A. single-agent sufficiency** | `V_0 < theta <= L^reach_{<=1,clean}` 가 지배적이고 COOP 부재 | "No certified need for multi-agent interdiction was found; all certified feasible non-FREE cells were single-agent sufficient." (AMBIGUOUS 에 대해서는 **침묵**) |
| **B. local mechanism infeasibility** | `U^rel_{<=N} < theta` 가 광범위 | "even N cooperative limiters cannot establish the **local** firing condition **via the static blockade channel**" (A 와 다른 결론). **채널 한정 필수 — r3.3.** 빼면 docs/46 실측 채널 (ii)·(iii) 과 자가모순 |
| **C. unresolved certificate gap** | AMBIGUOUS prevalence 가 높음 | **결론 없음. negative claim 금지** |

negative claim 은 **해당 bound 가 직접 지지하는 경우에만** 한다.


1. **`v_shot` measure 고정** — 2000 위트니스 "비율"이 어떤 measure 를 근사하는지
   정의하고 witness allocation·수렴(2k/8k/32k)·sampling-family 가중 민감도를 검증.
   이게 없으면 theta·band·requirement 전부 sampling artifact 공격 대상.
2. **regime 재정의 + certificate 분리 + N=1 대조군 승격** (§3). relaxed oracle 과
   reachable-system feasibility 를 절대 섞지 않는다.
3. **pivot protocol 잠금** — 오늘 결과를 exploratory 로 봉인, 지도 구성·범위·
   C5 선택규칙·inside/outside 대조·반증조건을 **결과 보기 전에** 고정.
   → `docs/74_pivot_protocol.md`

## 6. 폐기 3

1. `SHAPING_NEEDED` / `FREE_CAPTURE` 라는 **이름** (새 연구에서. 데이터가 정의를
   반증했다 — 동결 블록의 코드 라벨은 그대로 둔다).
2. 6 raw 파라미터 대규모 Cartesian sweep → 무차원 2~3 축.
3. **"MARL 이 이기는 논문"에 대한 미련.** MARL 은 이제 **mechanism validation
   instrument** 이고, 논문의 독립변수는 알고리즘이 아니라 feasibility 구조다.

### 6.1 리뷰 11 추가 sunk-cost (버릴 것)

4. **"2000 witness" 에 대한 애착** — 물리 상수가 아니다. 수렴이 8k/32k 를 요구하면 바꾼다
   (손실 = 기존 수치 비교성, 이득 = metric credibility).
5. **arc scripted 를 "강한 baseline" 으로 계속 키우는 일** — Phase I historical
   comparator 로 충분. 새 기준선은 `N=0`, `N=1`, constructive `N`, oracle `U_{<=N}`.
6. **COMA 배선을 "있으니 언젠가 쓴다"** — 계수 0 인 채로 두는 것은 sunk-cost invitation.
   새 hypothesis 가 credit assignment 를 요구할 때만 켠다.
7. **dense `Delta v_shot` reward 를 불변 과학객체로 취급** — Phase I historical
   contract 안에서만 불변이다. metric 자체가 Phase III 에서 수정될 수 있다.
8. **`a_att ~ U[11,78]` 를 세계의 위협분포처럼 취급** — 한 scenario distribution 일 뿐.
   envelope 논문에서는 uniform draw 보다 **conditional curve** 가 먼저다.

### 6.2 리뷰 11 이 지적한 우리의 자기기만 2 건 (등재)

1. **"certificate 만 잘 만들면 Phase I 실패 원인이 밝혀진다"** — 아니다. certificate 는
   특정 mechanism 의 feasibility 구조만 밝힌다. Phase I 실패는 feasibility · exploration ·
   credit assignment · reward · architecture 가 **동시에** 원인일 수 있다.
2. **"무차원 지도가 나오면 그 자체로 systems requirement"** — 아니다. 실물 anchor 없이는
   **model-conditional design envelope** 다. 이 구분을 끝까지 지키면 논문이 더 강해진다.

## 7. Q1 증거 bar (수용 요약 — 상세는 리뷰 원문)

- **geometry**: a_att 당 1 에피소드 금지 → 조건당 **20~30 독립 realization**,
  경계 adaptive refinement, witness 수렴(2k/8k/32k spot-check), 가중 민감도,
  greedy ↔ global/upper-bound solver 비교, relaxed ↔ reachable 분리.
  **통계단위 = episode** (위트니스 2000 을 독립표본으로 bootstrap = pseudoreplication).
- **map**: **core map = validated low-dimensional Π-space + discrete N**.
  non-core dimensionless group 은 사전 지정 값으로 고정하고 matched collapse /
  robustness slice 로만 검사한다 (`mu` 가 이미 mobility/capability 축이므로 "mobility
  2~3 층" 이라는 별도 표현은 폐기 — r2). 공격자 분포 적분 포함.
- **learning (C5, r3.2 동기화)**: **LOCAL-COOP-NEEDED / FREE / LOCAL-INFEASIBLE-N**
  3 matched regime (**동일 N = N_B**, **동일 θ_S2 = 0.90**), 점당 시드 **8~10 권장
  (5 최소)**, held-out 수백 paired.
  primary = `Gamma = delta_COOP − (delta_FREE + delta_HARD)/2`, 성공 = `LCB95(Gamma) > 0`,
  `delta_r = p_net^{MARL_N,r} − p_net^{B_N,r}` (`B_N` = 결과 열람 전 freeze 한
  **same-N constructive non-learning controller**).
  기준선 = hold · arc scripted(historical) · `B_N` · **reachable 1-limiter** ·
  oracle `U^rel` envelope. **`N=1` 은 secondary mechanistic control 이며 primary
  comparator 가 아니다** (learning × team-size 혼합 금지).
- **통계**: 시드 최상위 hierarchical CI, paired 차이, effect size + 95% CI,
  0 카운트는 binomial 상한 병기, 지도 경계에도 bootstrap band.
- **realism**: 대표 3 regime × 2~3 점에서 delay jitter · sensing noise · actuator lag
  spot-check (주인공이 tau 인데 judge 에 stochasticity 가 없으면 반드시 찔린다).

## 8. 일정 — r1: 시간 게이트 폐기, 과학적 게이트로 대체

r0 의 "19주 축소판" 은 **폐기**한다 (리뷰 11: 12/18 은 행정 마일스톤). 주차별 산출물과
**kill/branch 게이트**는 `docs/75_blueprint.md` §1 에 있고, 각 게이트는 시간이 아니라
숫자(수렴폭·불일치율·certificate coverage·`W_{2:N}` 존재 여부)로 발동한다.

- 12/18 에 제출하는 것 = URP 보고서 + arXiv snapshot. **미완 부분은 미완으로 명시**하고
  이후 지속한다.
- 저널 투고 시점은 증거 bar 충족 시점에 따른다 (12/18 과 무관).
- 유지 = C2 + C3(무차원 축) + C5 + **certificate hierarchy** (r2 정정: "전 계층
  강제" 폐기). 모든 셀에 모든 certificate 를 강제하지 않는다 — **싼 sound bound 로
  분류가 닫히는 셀에는 상위 solver/relaxation 을 적용하지 않고**, 어떤 certificate
  수준을 썼는지 셀별로 지도·metadata 에 공개한다. (예: unblockable bad mass 만으로
  `U^rel_{<=4} < 0.82 < 0.90` 이 나온 셀에 continuous B&B 를 돌리는 것은 과학적 가치가
  거의 없다.) **넣지 않음** = optimal stopping · sensing-latency cooperation ·
  multi-shot · 6DOF 재구축 (= Paper 2~5, `docs/75_blueprint.md` §4).

## 9. 상위 발견의 재서술 (리뷰어 제안 채택)

> **기존 연구 설계가 '협력이 필요한 영역'을 실제 cooperative advantage 존재와
> 무관한 scalar kinematic proxy 로 정의하고 있었고, 그 결과 policy learning 전에
> 확인했어야 할 feasibility question 이 빠져 있었다.**

이것이 논문의 상위 주장이다. `[36,39]` · `N_req=1` · "병목은 tau·theta·cone" 을
확정 사실로 밀면 그 순간 전환이 goalpost moving 으로 보인다 — §2 의 하향 표현을
모든 산출물·발표에 적용한다.

**★ r2 (리뷰 12) — 두 문장을 절대 합치지 않는다**:
- "기존 설계에 feasibility question 이 빠져 있었다" = **지금 확정 가능한
  methodological finding.**
- "그 feasibility question 이 Phase I 실패를 설명한다" = **아직 hypothesis.**
