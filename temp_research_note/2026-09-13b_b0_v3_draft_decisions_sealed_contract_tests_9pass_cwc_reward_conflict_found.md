# 2026-09-13b — B0 v3 초안 완성: 결재 ①~⑥ 봉인 문안 확정 + contract tests 11 pass + **blocker ④ 발견·해소 (CWC 보상이 illegal substitution 에 만점)**

> 본문 §1~§6 은 1차 작성분, **§7 이 검토 라운드 반영판이며 충돌 시 §7 이 정본**.

층1 종료 판정 (같은 날 앞 노트) 직후 이어진 세션. **실험 0 · 서버 0** — 코드 정독 +
문서 + 로컬 테스트뿐. 산출 = `docs/94_b0_v3_world_contract_draft.md` (13항 전부) +
`tests/test_b0_v3_contract.py` (9 passed).

## 1. 결재 3건 (사용자) — 봉인 문안 확정

- **① same-tick precedence = CAPTURE 우선**, 단 "코드 현행이니까" 가 아니라 **sealed
  discrete-time tie rule** 로 명시한다 (연속시간 물리 순서 주장 없음). 부수 규율:
  `capture_penetration_same_tick` counter 는 **로그하되 precedence 결정에 쓰지 않는다** —
  빈도가 크면 그때는 규칙을 바꾸는 게 아니라 **dt-sensitivity /
  continuous-event-resolution 문제로 층3 에서 공격**한다.
- **② boundary rule = per-seed 다수결 (3 seed → ≥2/3) ∧ global positive effect**.
  전역 CI 는 **seed-preserving hierarchical paired CI** 로 부르고, cluster 가 3 개뿐이라
  정밀한 95% frequentist guarantee 로 서술하지 않는다 (보조 증거).
  - **seed-pooled 점추정 기각 사유 (사용자)**: (+0.30, −0.02, −0.02) 도 평균은 양수 →
    **한 seed 의 대성공이 두 seed 의 실패를 덮는다**. MARL 에서 training stochasticity 는
    우리가 일반화하려는 변동원 자체이므로 이 masking 은 허용 불가. 반대로 전 seed 통과는
    seed=3 에서 worst-seed test 가 되어 진짜 효과를 버린다.
- **③ F1 = 주석 수정 + docs/09 예외 등록**. 표현은 "byte 무변경" 이 아니라
  **executable semantics unchanged / comment-only diff**. → docs/09 §13 행에 **비준 예외 2**
  로 등록 완료.

## 2. Contract tests — 세계가 코드에 실재함을 확인 (9 passed / 7.2 s)

`tests/test_b0_v3_contract.py`. **민감도 테스트가 아니다**. 캠페인 세계 (R-ref τ=0.30 ·
dt=0.05) 에서 돈다 — M2 기본값 (τ=0.4) 세계가 아니라는 점이 중요.

| t | 잠근 것 | 결과 |
|---|---|---|
| t1 | q_dec = dt/τ_deploy = 1/6 (전 구현 5종 + manifest) | PASS |
| t2 | q_race = 1/3 ∧ q_kill = 1/2 (contract-fixed ratios) | PASS |
| t3 | obs = 참값 · zero-latency (reset 직후 + 1 step 후 비트 동일) | PASS |
| t4 | NET_SPENT 실재 + F-계약에서 미종료 | PASS |
| t5 | same-tick tie rule + 정의원 1개 | PASS |
| t6 | WAIT ≠ τ | PASS |
| t8 | train/eval manifest parity + flag trap | PASS |

**실측 (t4/t6 비-공허성 증거 — force_commit 강제 발사 · hold limiter)**:

| 구성 | fire | spent | handoff | end | label | steps |
|---|---|---|---|---|---|---|
| F-계약 `force_commit_step=1` | 0 | **8** | 8 | 46 | PENETRATED | 47 |
| F-계약 `force_commit_step=5` | 4 | **12** | 12 | 48 | PENETRATED | 49 |
| legacy `miss_terminates=True` | 0 | 8 | — | **8** | **SPENT_FAIL** | 9 |

- **pending 창 = 8 틱** = (τ_deploy+τ_lock)/dt = (0.30+0.10)/0.05 — 계약의 수치가 실측됨.
- 발사를 4 틱 늦춰도 간격 8 틱 불변 → **기다린 시간은 지연이 아니다**.
- F-계약은 소진 스텝에서 안 끝나고 47~49 스텝까지 간다 → continuation 실재.

## 3. **신규 blocker ④ — "포획 성공" 술어가 코드에 4 개 있고 서로 다르다**

| 지위 | 위치 | 하는 일 |
|---|---|---|
| **권위** | `mission_rollout` label | CAPTURED ∧ **에피소드 누적** contact = ∅ (R2a/R2b 가 쓴 술어) |
| 사본 1 | `env_sys._outcome_label` | 같은 precedence 사슬, 그러나 contact 을 **종료 tick 에서만** 검사 |
| 사본 2 | `RewardSpec.terminal` | **CAPTURE_WITH_CONTACT 에 clean 과 같은 +b_net** (docs/66 r1 Q1 비준) |
| 사본 3 | `m4_env.label_rates` | `p_net` = NET_CAPTURE **+** CWC |

- **사본 2 가 blocker**: hybrid mission 에서 CWC = NET_PRE/NET_PENDING 중 kinetic 접촉 =
  **illegal substitution** 인데, 보상은 clean capture 와 동점을 준다. §3.2/§3.3 이 **구조로**
  막으려던 실패 모드를 reward 가 사주는 형태. 가정이 아니라 **현재 배선**
  (`train_m4.py:504-507` 이 `RewardSpec(enabled=True)`).
- **docs/66 r1 Q1 이 자동 승계되지 않는 이유**: 그 비준의 기준은 **파괴성** (CWC 는
  nondestructive 이므로 동등) 이었고, hybrid 의 기준은 **doctrine** (net 실패 전 kinetic
  접촉 금지) 이다. 기준이 다르므로 **명시적 supersede 결재**가 필요하다.
- **도달 경로가 실재**: `p_kill=1.0` 이라 접촉은 보통 즉시 HARD_KILL 이지만,
  **no-kinetic zone 안의 접촉은 veto** 되어 kill 도 소모도 없다 → 그 뒤 포획이 성립하면
  권위 술어는 CWC, 사본 1 은 NET_CAPTURE 로 갈린다. **vetoed contact 도 doctrine 위반이므로
  B0 v3 에서는 H_illegal** (kill 이 없었다는 것과 무관).

## 3b. 전체 regression (결재 ③ 둘째 검증) — **§7 이 supersede (RED 해소됨)**

**735 passed · 34 skipped · 1 failed** (전 테스트 파일 실행 완료; 1차 `-x` 가 중간에
멈춰 남은 19 파일은 별도 실행으로 채움). 유일 실패 =
`test_results_lineage.py::test_every_entry_classified` — **기존 RED, 본 세션 무관**:
`results/viz_r2b_c_pick{0,1,2}.json` 이 커밋 **cd74b63 (2026-09-07)** 에서
`results/README.md` 계보 표 갱신 없이 들어왔다. 가드가 설계대로 작동한 것이고,
bucket 분류 (LEGACY-REGIME vs CANONICAL) 는 캠페인 맥락 판단이라 **임의 조치하지 않음**.
리팩터를 직접 덮는 `test_rollout_core_parity` · `test_terminal_truth_table` 는 PASS.

## 4. 부수 정리 (t5 가 요구한 최소 변경)

라벨 사슬 `hard_kill → captured → penetrated` 이 **세 곳에 복제**돼 있었다
(`run_episode` · `recoverability_probe._Driver` · `env_sys._outcome_label`). 앞의 둘을
`mission_rollout.terminal_label(fi)` **단일 정의원**으로 통합 (bit-identical). 세 번째는
다른 함수 (CWC 분기 + TRUNCATED) 이므로 통합 대신 **비권위로 명기**. 복제가 남아 있으면
§2-12 ④ 를 봉인해도 한쪽만 바뀌는 사고가 가능하다.

## 5. 봉인까지 남은 것 (2개) — **§7 이 supersede (④ 결재 완료 → 1개)**

1. **§0 ④ 결재** — CWC 보상 supersede 여부 (비준된 결정을 뒤집는 것이므로 사용자 몫).
   실제 `r_illegal` 수치는 B0 가 아니라 **training contract** 에서 봉인.
2. **평가 격자 + G 확정** (§2-10/§2-11) — 재료 = R2a 경계 (η별 χ50) + 공통 유효 부분격자 +
   λ 2 slice + A. 이것만 정해지면 봉인 payload 가 닫힌다. 봉인 스크립트는 그 뒤에 쓴다
   (미완성 payload 를 해시하지 않는다).

## 6. 이 세션의 순가치 (한 줄)

> 세계를 **쓴** 게 아니라 **읽어서 적었고**, 그 과정에서 봉인 직전에 reward 가 금지된
> 행동에 만점을 주고 있다는 것을 찾았다 — 학습을 돌린 뒤였으면 결과 전체가 오염됐을 종류.

---

## 7. [추가 — 초안 검토 라운드] 결재 ④⑤⑥ + blocker 3건 해소

검토에서 **봉인 전 blocker 5건** 이 나왔고 전부 닫았다. ④ 는 APPROVE.

- **④ CWC 보상 supersede = APPROVE**. docs/66 r1 Q1 은 hybrid mission 에 한해 supersede.
  B0 는 semantics 만 (CWC 는 성공이 아니다), 수치는 training contract.
- **⑤ `C_illegal` = irreversible failure latch (즉시 terminal 아님)**. 코드 확인 결과
  **종료 여부가 영역에 따라 갈린다** — NK zone 밖 contact 는 `KILL` 로 즉시 종료,
  NK zone 안은 `VETO_NO_KINETIC` (기폭 보류·미소모) 로 **종료하지 않고** 이후 capture 가능.
  그래서 "즉시 terminal" 은 거짓 서술이었다. latch 는 권위 술어 (누적 contact = ∅) 가
  이미 하고 있는 일이라 신규 구현도 거의 없다. → **t10 이 이 dichotomy 를 잠근다.**
- **⑥ hard θ_fire gate = 유지, admissibility constraint 로 명시**. 학습되는 것은
  *fixed admissible region 안에서의 firing timing*. **"gate censoring 회수" 주장 전면 폐기**
  — `v_shot_soft < θ_fire` 면 FIRE 는 물리적으로 no-op 이다. → **t9 가 잠근다.**
- **문구 정정**: §2-12 ① 의 "NET_CAPTURE ∧ contact" 는 정의상 동시 참 불가 →
  **"raw CAPTURED resolution ∧ contact"**.
- **τ₀ NIT**: τ₀ 는 총 FIRE→resolution 지연이 아니다. τ₀ 0.30 / q_race·τ₀ 0.10 /
  총 pending (1+q_race)τ₀ = 0.40 — 셋을 항상 함께 적는다.
- **seed rule 연산 순서 고정**: seed 다수결은 **행 단계에서 한 번만**, slice/전역 gate 는
  그 flag 위에서 센다 (중첩 해소).
- **R_rec 은 새 격자에서 계산 불가** → **R2b exact `S_C` 를 secondary fixed replay set 으로
  유지**하고 R_rec 은 거기서만. 두 집합 수치 혼합 금지.
- **lineage RED 해소**: 기존 4종 어디에도 안 맞아서 (**NEXT-BRANCH 는 "confirmatory 사용
  금지" 라 C047~C049 와 충돌**) **`R2-CAMPAIGN` 상태를 신설**하고 `viz_r2b_*` 행 추가.
  한 줄 metadata 가 아니라 **상태 어휘 추가**였다는 점은 명시해 둔다. → 재실행 64 passed.

**현재**: contract tests **11 passed** · 전체 regression **0 failed** · 결재 ①~⑥ 반영 완료.
**봉인까지 남은 것 = 평가 격자 + G 확정 하나.**

## 8. 후보 평가 격자 (docs/94 §2-10a) — 실측 조립

**G = 14 를 새로 만들 필요가 없었다**: `artifacts/r2a/stage3_protocol.json` 의 `cells_rule`
이 이미 *"two micro-grid (0.02) points bracketing that slice's chi50"* = nearest
inside/outside 이고, 7 η × 2 λ (4.644 / 3.574) = **14 행** 구조가 그대로 있다. R2b 판정
형식 (12/14 · 5/7) 을 수치까지 재사용 가능.

확인된 사실 4가지:

1. **χ50 은 14 행 어디에서도 0.02 격자 위에 없다 (0/14)** — "χ50 자체를 셀로" 는 불가능.
   nearest inside/outside 가 유일한 기계적 규칙 (= 이미 R2a 가 한 일).
2. **THREAT bracket 은 이 구간에서 구속하지 않는다** — a ∈ [16.5, 27.5] vs [11, 78],
   v ∈ [12.4, 23.0] vs [8, 30]. 구속은 bracket 이 아니라 **예산**이다.
3. **2점 bracket 은 이동을 탐지만 하고 측정은 못 한다** — 0.02 넘게 밀면 두 셀 다 inside 가
   되어 χ50^learned 가 censored. Δχ50 이 estimand 이므로 **outer anchor 는 필수**.
4. **역방향 동일** — docs/89 가 예고한 **B-3 붕괴** 시 χ50 이 격자 아래로 벗어나 reward 축
   Δχ50 이 보고 불가 → **inner anchor 대칭 배치**.

예산 지배항 = **A-family (×4)**. R2a 선례 ("family worst-case 는 Stage 3 밴드 셀에만") 대로
primary 는 A2-nom 단일 권고. 5점/행 · n=200 · A2-nom = 126,000 ep ≈ 52 h serial / 6.5 h (8샤드).

**남은 결정 3개**: (a) χ 점 수·n (b) λ=3.574 행 앵커가 **exploratory scout (n=480)** 라는
비대칭을 계약에 명기할지 (권고: 명기하고 유지) (c) 이동폭이 격자를 넘을 때의 **사전 확장
규칙** (R2a two-step 승계).

## 9. 결재 ⑦ (격자) + payload 생성 — **승인만 남음**

**확정 사양**: G = 14 · base **4** χ/row · n = **300**/cell/seed · **A2-nominal 단일** ·
3 arm × 3 seed paired CRN · censoring-triggered **±0.04 최대 2회** 확장.

- **5점이 아니라 4점**인 이유 (사용자 판정): χ50 이 lo/hi 사이에 있으므로 4점 =
  중심 기준 ≈ {−0.05, −0.01, +0.01, +0.05} 의 **대칭 support**. 바깥에 한 점을 더 얹은
  5점 안은 **"학습은 좋아질 것" 이라는 기대를 평가 설계에 심는 것** — B-3 붕괴 가능성을
  이미 인정한 이상 대칭이 맞다. 범위 부족은 점을 더 두는 게 아니라 **확장 규칙**으로 푼다.
- **n=300**: 다섯째 점보다 **seed 별 χ50 추정 정밀도**가 seed-majority 판정에 더 값어치.
- **A2-nominal 단일의 대가**: claim 을 **χ50^net(η, λ | A2-nominal)** 로 조건화.
  A-family robustness 는 층3(W10) frozen-policy arm 으로 분리, **pooling 금지**.
- **확장 규칙의 핵심은 trigger**: **censoring 만이** trigger 다 ("효과가 커 보여서" 확장은
  adaptive cherry-picking). 한 arm×seed 라도 censored 이면 **row 전체 확장** (seed 별 χ50 을
  판정에 쓰므로 한 seed 가 잘리면 seed-majority 가 불완전).
- **λ=3.574 유지 + provenance 명기**: scout 추정치는 **grid-centering 용 design input 일 뿐
  confirmatory 증거로 재승격되지 않는다**.

**payload 생성 완료**: `artifacts/b0/b0_v3_world_contract.json`,
**`b0_hash = 5e7b5b486b9d8a4a`**, exit `B2_WORLD_CONTRACT_FROZEN`.
승계 = `lattice_R2a_P3 b7b3f6440e5b83eb` · `stage3_protocol eb3a85e702020167` ·
`r2b_b0_v2 cba024d7ee3d9f61`. 격자는 **R2a 산출물에서 유도** (하드코딩 아님) — `t0` 이
재생성·해시·bracket 성질(lo < χ50 ≤ hi, 14/14)을 잠근다. contract tests **12 passed**.

base episodes = 14×4×300×3×3 = **151,200** (≈ 62.6 h serial, 7.8 h @8샤드).

**→ §10 에서 승인·봉인 완료.**

## 10. **B0 v3 SEAL — 승인·봉인 완료 (2026-09-13)**

$$b0\_hash = 5e7b5b486b9d8a4a \quad exit = B2\_WORLD\_CONTRACT\_FROZEN$$

봉인 직전 기계 체크 8종 전부 통과:

| # | 체크 | 결과 |
|---|---|---|
| 1 | `b0_v3.py` 재실행 | 같은 hash, **byte-identical** |
| 2 | contract tests | **12/12** |
| 3 | 전체 regression | **770 passed · 65 skipped · 0 failed** (단일 완전 실행 29.5 분) |
| 4 | bracket `lo < χ50 ≤ hi` | **14/14** |
| 5 | base cells 중복 | **56 = 14×4, 중복 0** |
| 6 | G / row gate / slice gate | 14 · 12/14 · 5/7 직렬화 확인 |
| 7 | A2-nominal primary / `S_C` secondary | 분리 확인 |
| 8 | extension rule + 방향당 최대 2 회 | 직렬화 확인 |

**봉인 이후 규율**: 조항·격자·판정 규칙 변경은 **v4 + 새 hash**, 기존 v3 결과와 **pooling
금지**. claim registry 등재는 **사용자 트랙** — 본 봉인은 *계약*이지 *claim* 이 아니므로
자동 등재하지 않았다.

**커밋 3단 감사 사슬** (사용자 지정): hygiene → contract spec → SEAL. seal 커밋에는
science code 를 넣지 않는다 (봉인하다가 코드 한 줄 같이 고치는 사고 차단).

## 11. 이 봉인의 성격 (한 줄)

> 원래 계획은 B0 전에 sensitivity campaign 을 하나 더 도는 것이었다. 실제로는 코드 정독이
> **무의미·미구현·confounded 후보를 제거**했고, 그 결과 v3 는 *실험을 더 해서 강해진 계약*
> 이 아니라 **무슨 실험을 하면 안 되는지까지 알게 돼서 강해진 계약**이다.
