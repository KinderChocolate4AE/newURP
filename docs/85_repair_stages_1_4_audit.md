# 85 — Repair Stages 1–4 감사 기록 (repo integrity closure)

- **일자**: 2026-08-19 · **baseline**: `b330fbc` → **closure HEAD**: `180f410`
- **성격**: Reality Audit Session 1–3 이 찾은 finding 중 **CONFIRMED 인 것만** 골라
  최소 patch 로 닫은 기록. 과학 결과를 다시 만드는 작업이 아니라 provenance ·
  contract · guardrail 정비다.
- **입력**: Session 1 Reality Map · Session 2 Execution Audit(X-001~X-017) ·
  Session 3 Artifact & Claim Audit(C-001~C-013) · Session 4 Repair Plan

---

## 0. 한 줄 결론

> **executed science path 에서 outcome label 이나 확률을 바꾸는 confirmed P0 는
> 끝까지 나오지 않았다.** 유일한 P0-LATENT 는 현재 운용점에서 inert 였고, 고친
> 뒤에도 canonical label 이 하나도 움직이지 않았다.

```text
closure full suite   696 passed · 65 skipped · 0 failed   (28:57)
canonical label diff 0    (mission_eval 40ep ×2 · _Driver 25ep · frozen artifact 25/25)
소스 수정             5 커밋  (전부 rollout/물리 경로 밖이거나 bit-exact 확인)
guardrail 신설        88 건   (10 파일)
```

---

## 1. 전체 커밋 (17, `b264fa7` 은 사용자 science 커밋)

| Stage | 커밋 | 성격 |
|---|---|---|
| 1 | `ccbc126` test: expose commit-margin divergence | RED 게이트만 |
| 1 | `79bd551` test: split the R-001 gate by divergence direction | 계기 개정 |
| 1 | `202f2c7` **fix: single-source commit margin** | **소스** |
| 1 | `9597290` test: pin the two rollout cores under a semantic projection | guardrail |
| 2 | `14e58cc` test: pin resolved contracts for every live world builder | guardrail |
| 2 | `0e21aad` test: assert the contact accounting invariant | guardrail |
| 2 | `ecc87ba` test: parity on a contract-discriminating cell | guardrail |
| 2 | `79d8010` test: mark test_p63c as torch-gated | harness |
| 2 | `085ac30` **fix: split the provenance dirty flag + canonical --out** | **소스** |
| 2 | `0ec1dea` **fix: single-source the curve payload; track the figure chain** | **소스** |
| 2 | `0625bf7` test: isolate the scope probe from ambient sys.modules | 게이트 수리 |
| 3 | `983357f` **fix: consume the canonical aggregation in the dashboard** | **소스** |
| 3 | `0435abe` results: regenerate the dashboard | 파생 재생성 |
| 3 | `9804299` **fix: dump the authoritative proximity** | **소스** |
| 3 | `3791454` results: re-dump the T1 hard-kill trajectories | 재덤프 |
| 4 | `29fa621` docs: retire the orphaned a* constant + label-scope divergence | 주석 |
| 4 | `180f410` docs: close the provenance and authority drift | 문서·registry |

---

## 2. Stage 1 — P0-LATENT 및 실행 core parity

### 2.1 R-001 커밋 margin 중복 구현 (P0-LATENT)

**문제.** 커밋 기하 판정 반경이 두 곳에서 독립 계산됐다.

```text
env_sys.py:327-329      r_commit + 0.5*(a_lim - a_att)*tau_kill^2    <- 권위
mission_rollout.py:192  env.kill_radius + ...                        <- spec.r_commit 무시
```

`ratified_system()` 은 `r_commit=None` 이라 둘이 우연히 같은 값이 되고(실측
`0.42797472527106606`) 어떤 테스트도 깨지지 않았다. 그러나 `SystemSpec.r_commit`
은 살아 있는 필드이고(`tests/test_contact_resolver.py:191` 이 이미 `r_commit=2.0`
으로 인스턴스화한다) env_sys 가 "수치 calibration 은 별도 실험 후" 라고 예고해 뒀다.

**심각도 근거.** cosmetic 이 아니다 — `r_commit` 을 조이면 같은 seed 에서 라벨이
**`HARD_KILL` → `PENETRATED`** 로 뒤집힌다 (게이트가 고정).

**수리.** `env_sys.commit_margin(...)` 단일 정의원 신설, 권위 공식은 **이동만**.
소비처 4곳(`env_sys.step` · `mission_rollout._limiter_actions` · `dump_trajectory` ·
`test_contact_resolver`). `tau_k = 0.1` 고아 상수 제거.

**현재.** GREEN 10/10. canonical label diff **0** — `mission_eval` 40ep(hold ·
intercept) JSON 해시 동일, `_Driver`/`run_episode` 25ep 동일, frozen
`curve_intercept_reactive.json` 대조 25/25 유지. **science rerun 불필요.**

> `tau_k=0.1` 은 감사 카드의 초기 분류를 **하향**했다. `spec` 없는 경로는 동결 env
> 뿐이고 동결 env 는 커밋 비트를 무시하므로(`test_p78` 이 강제) outcome 에 대해
> **inert** 다. latent divergence 가 아니라 오해를 부르는 magic constant 다.

### 2.2 R-004 두 rollout core parity (X-008)

**문제.** 과학 결과가 실행 core 둘에 나뉘어 실려 있는데(헤드라인 곡선 =
`run_episode`, E1d/E1e/E3/E4/lead-time/뷰어 = `_Driver`) 두 core 를 함께 import
하는 테스트 파일이 **하나도 없었다**. Session 2 의 25판 실측은 일회성 관측이었다.

**수리.** literal equality 가 아니라 **정규화 projection** 으로 고정
(`_Driver` 는 접촉 집합을 안 세므로 `CAPTURE_WITH_CONTACT` 를 구조적으로 못 낸다).

**현재.** 35 ep / 6 arm, mismatch **0**. 희소 class 를 stochastic 에 맡기지 않고
fixture 로 겨냥했다 — `SPENT_FAIL` 은 legacy 계약 + `x_fire` 로 6/6, `TRUNCATED`
는 `episode_len=8` 로 5/5. **`CAPTURE_WITH_CONTACT` 만 rollout fixture 를 못 만들어
`UNOBSERVED` 로 명시**했다 (접촉이 쉬운 팔에선 포획이 안 나고, 포획이 나는 팔에선
접촉이 0/10). 어휘 계약 자체는 rollout 없이 구조적으로 고정했다.

---

## 3. Stage 2 — contract · reproducibility guardrail

| 카드 | 문제 | 현재 |
|---|---|---|
| **R-005** | 계약 게이트가 8 builder 중 3 만 훑음. ratified 계약을 **세 가지 철자**로 씀 | spy 로 **resolved contract** 포착해 6 builder 고정. `_build_t1 == curve` 해시 동일 확인 — docstring 의 load-bearing 주장을 contract 수준에서 못 박음 |
| **R-010** | `mission_rollout` docstring 이 자기 correctness 논거로 내세운 등식이 **어디서도 assert 안 됨** | episode-wise 등식 + 독립 경로 접촉 증언 + 비자명성. 8판 전부 `contact_steps 8 == limiter_loss 8.0`, `n_contact < 8`(중복 계수 확인) |
| **R-011** | 기존 parity 테스트가 **판별력 0 인 셀**에서 n=4 | intercept 판별 5/21 셀에서 mismatch 0. hold 는 n=25 에서도 판별 0 임을 실측해 기록 |
| **R-009** | `test_p63c` 에 torch 마커 누락 → 가짜 torch 를 잡아 엉뚱한 `TypeError` | SKIPPED 로 이동, 사유가 `_torch_status` 진단 인용 |
| **R-006 · R-025** | `code_dirty` 가 untracked 포함이라 **16/16 이 true**. `--out` 기본값 5개가 superseded 경로 | 3분할(`code_dirty`/`tracked_dirty`/`untracked_present`). clean tree 실측 `F/F/T`. 기본값을 canonical 로 옮기고 README 와 문자열로 묶음 |
| **R-007 · R-008** | `run_curve` 반환값에 계약 필드 누락. `paper_figs.py`+`figures/` 둘 다 untracked | `_payload()` 단일화로 반환 ≡ 저장본. 생성기·그림 **함께** 추적 |

### 3.1 `code_dirty` 포렌식 (H-2 해소)

플래그가 `git status --porcelain` 이라 **untracked 를 포함**한다 — 실행이 자기 출력을
레포에 쓰는 순간 참이 된다. 각 artifact 의 `code_commit` → 기록 커밋 사이
`shepherd/` diff 를 보면:

```text
14/16   차이 0                -> dirty 는 출력 파일이었다
 2/16   자기 생성기 신규 생성   -> 실행 코드 = e1c 633105c · e3 717e3c1
        (같은 창의 slew_audit 변경은 r_perp 필드 순수 추가라 psi/ax 불변)
```

**대규모 rerun 불필요.** 과거 artifact 는 backfill 하지 않고(docs/81 §1-2)
`results/README.md` 에 의미 변경 시점과 두 예외를 기록했다.

---

## 4. Stage 3 — visualization / diagnostic drift

### 4.1 R-012 · R-013 dashboard (X-005 · X-006)

`viz/build_results_dashboard.py` 는 docstring 에 "분석 로직을 새로 만들지 않는다"
고 적고 실제로는 Wilson · bin 격자 · 경계 상수를 전부 다시 구현했다.

- **z 가 달랐다**: `stats` 1.959964 vs dashboard 1.959963984540054 (차 ~5e-10).
  `test_p44j` 가 바로 이 재발을 막으려 있었는데 두 모듈만 **이름으로** 확인해
  `viz/` 를 못 봤다 (2026-08-03 사고의 사각지대 재발).
- **최상단 bin 이 경계 위 판을 누락**: 현 아티팩트에 `a_att == 78.0` 인 판이 없어
  잠복 상태였다. 합성 판으로 실증 (patch 전 0 vs 정본 1).

**현재.** 지역 구현 삭제 후 정본 import, 상수도 config 에서 유도. 재생성 결과
**수치 56건만 · 최대 4.6e-10 · 구조 차이 0**. `test_p44j` 를 **경로 스캔**으로 확장.

### 4.2 R-014 뷰어 근접거리 (X-007)

뷰어가 `d_lim_min` 을 "최근접 limiter" + "(접촉권)" 으로 보여줬는데, 그 값은
**화면 보정 좌표 위의 post-step 끝점 거리** — R4 가 superseded 로 선언한 계열이다.
권위값 `_Driver.d_min` 은 같은 driver 위에 있으면서 덤프되지 않았다.

**수리.** `d_lim_min` → `d_lim_min_display` 개명, 스텝별 `d_swept_min` 과
에피소드 수준 `proximity{d_min,t_min,n_unmeasured,contract}` 추가. 주차 표시 보정
자체는 **유지**(제거하면 접촉 프레임이 다시 63 m 로 사라진다).

**현재.** 기존 `viz_traj_t1_hk.json`(C033 증거)은 **보존**, 신규
`viz_traj_t1_hk_r5.json` 이 canonical. 8/8 에피소드에서 라벨·스텝·commit record
**완전 일치** — 기록 필드만 늘었고 물리는 안 건드렸다. ep3 의 `d_min[0]=0.423` 이
해소기 `d_nom` 0.423 과 일치.

---

## 5. Stage 4 — docs / registry authority

역사 문서는 **본문 값을 고쳐 쓰지 않았다.** forward pointer · staleness banner ·
superseded-by 로만 처리 (append-only, docs/83 §29.6 · docs/81 §1-2).

| 카드 | 처리 |
|---|---|
| R-015 | docs/83 §17 · §19 에 SUPERSEDED POINTER (→ §30.1/§30.2/§30.8/§30.9) |
| R-016 | docs/82 에 SNAPSHOT 배너 — 행 (i) `0.043` 인용 금지(C039), 행 (c) T0 n=2700 부재 |
| R-017 | registry 에 `Superseded by` 열 신설 + C034 → C039 back-link |
| R-019 | docs/82 §3(g) 를 **paired 로 재서술** (주장이 강해짐) |
| R-020 | C033 "사문" → "접촉 resolver 가 지배", follow-up 종료 |
| R-022 | docs/84 §6 `r_ring` 각주 (표의 반경 5 는 맞고 `lay.r_ring=2.1` 은 다른 양) |
| R-018 | 소스 4곳의 `a* = 44.4` 정정 (rho=2.0 시절 고아값, 실제 39.33) |
| R-021 | `_outcome_label` docstring 에 범위 차이 명시 (비준된 B1 divergence) |
| README | `code_dirty` 의미 변경 시점 · `viz_traj_t1_hk_r5.json` canonical 계약 |

### 5.1 R-018 에서 나온 부수 발견 — 철회된 주장이 소스에 살아 있었다

`curve_sweep` 모듈 docstring 이 이렇게 적고 있었다:

> 붕괴 50% 교차 = 24.06 … 두 값이 6.6 % 안에서 만난다 = **두 번째 경계의 검증**

"두 독립 계측 일치로 검증" 은 registry **C031 의 금지 문구**다 (ω=∞ paired
반사실 0/500 flip 으로 인과 귀속이 배제됨). 숫자(24.06 → 22.45, 6.6 % → 12.4 %)와
주장(→ "consistent with") 을 함께 낮추고 금지 사유를 적었다.

**Session 3 의 문서 감사가 소스 docstring 까지는 훑지 않은 사각지대**였다. 후속으로
`test_claim_hygiene` 의 스캔 범위를 `shepherd/**/*.py` 까지 확장했다.

### 5.2 registry 재작성 무결성

TSV 를 csv 로 왕복하면 전 줄이 재인용된다. 의미론적 정본이므로 필드 단위로 검증:
**47 행 유지 · ID 손실/중복/공백 0 · 의도치 않은 필드 변경 0 건** (의도한 8 필드 +
신설 열만). diff 48/48 은 재인용 때문이지 내용 변경이 아니다.

---

## 6. 신설 guardrail (88 건 / 10 파일)

| 파일 | 건수 | 무엇을 고정하나 |
|---|---:|---|
| `test_commit_margin_single_source.py` | 10 | 커밋 반경 단일 정의원 · outcome-material 성 |
| `test_rollout_core_parity.py` | 9 | 두 실행 core 의 semantic projection + class 별 커버리지 |
| `test_builder_contract_parity.py` | 12 | 6 builder 의 resolved contract · `_build_t1 == curve` |
| `test_contact_accounting.py` | 5 | episode-wise 접촉 계정 등식 |
| `test_curve_eval_parity.py` | 6 | 판별력 있는 셀에서의 경로 parity |
| `test_provenance_stamp.py` | 16 | dirty 3분할 4-way 정책 · scope 폐쇄성 · canonical `--out` |
| `test_curve_payload_and_figures.py` | 15 | 반환 ≡ 저장본 · 그림 사슬 추적 |
| `test_dashboard_aggregation_parity.py` | 6 | dashboard ≡ 정본 집계 · 경계 판 보존 |
| `test_viewer_proximity_authority.py` | 5 | 뷰어 권위 근접거리 · 해소기 정합 |
| `test_source_constant_hygiene.py` | 4 | 소스 주석 상수 ↔ config |

**전 카드에 mutation 을 걸어 이빨을 실증**했다 (게이트가 통과한다는 것과 게이트가
무언가를 잡는다는 것은 다른 사실이다).

---

## 7. 이 세션에서 반복해서 걸린 것 — 9 건

전부 **격리 실패**였고, 매번 mutation 이나 실제 실행이 잡았다. 방법론 기록으로 남긴다.

| # | 형태 | 어디서 |
|---|---|---|
| 1 | 상수 충돌 — fixture `kill_radius=2.0` 과 하드코딩 `r_commit=2.0` 이 겹쳐 divergence 상쇄 | R-001 게이트 초안 |
| 2 | 퇴화 항 — `a_lim == a_att` 라 가속 항이 0, tau 축이 무의미 | R-001 게이트 초안 |
| 3 | fix 이후에만 열리는 사각지대 — 고쳐지면 `CommitRecord` 자체가 사라져 관측 불가 | R-001 patch 직후 |
| 4 | 조용히 무시된 config 키 — `train.limits.limiter_kill_radius` 는 존재하지 않음 | R-004 탐색 |
| 5 | **무효한 mutation** — rollout seed 가 `p_kill=1.0` 에서 inert | R-011 |
| 6 | 주변 트리 상태 의존 — clean tree 를 전제한 게이트 | R-025 초안 |
| 7 | 전역 `sys.modules` 오염을 생성기 의존으로 오인 | R-025 scope 프로브 |
| 8 | 자릿수 다른 값의 exact 비교 (`d_nom` 3자리 vs `d_min` 4자리) | R-014 게이트 초안 |
| 9 | 아티팩트 구조 오독 (`{"note","episodes":[...]}`) | R-014 게이트 초안 |

**5번이 가장 위험했다.** mutation 이 RED 를 안 내는 것을 "게이트 통과" 로 읽었으면
검증되지 않은 게이트를 커밋할 뻔했다. 원인을 파고들어 `env_sys` 의 `_seed` 가
`_bern()` 의 p_kill Bernoulli 에만 쓰인다는 것을 확인하고 world 인덱스로 다시 했다.

> **원칙**: *No parity without discriminating coverage. No configured knob without
> resolved-value verification.* — 그리고 그 따름정리로, **mutation 자체도 판별력을
> 검증해야 한다.**

---

## 8. 현재 상태

```text
HEAD                180f410   (tracked worktree clean)
full suite          696 passed · 65 skipped · 0 failed   (28:57)
confirmed P0        없음
canonical outcome   변화 0
```

**남은 것**

- **Stage 5 (KSAS 원고)** — 정본은 `docs/KSAS2026_추계_본문_v3.docx` (2026-08-17
  갱신). 새 spine(지연 → χ 상계 → cone geometry → T1 폐루프)은 이미 반영됐으나
  **숫자는 아직 T0 legacy** 다. 별도 freeze 블록으로 진행.
- **Stage 6 (cleanup)** — R-024(`channel_split` ψ 이관) 가능.
  R-023(`pilot_report` 은퇴)은 **H-4 대기**.
- **미해결 human decision** — H-4: LS seeds 1–4 체크포인트와 `results/m4_pilot/`
  가 랩 서버에 있는가.
- **Tooling debt — F-1 (2026-08-19, 기록만 · 게이트 무수정)**: R-025 scope probe 의
  생성기 판별이 substring(`"stamp(" in src`)이라 **호출과 판독을 구분하지 못한다**.
  - false positive 실례: evidence dashboard **판독자**
    (`viz/build_research_evidence_dashboard.py`)의 helper 명(`_find_stamp`)이 걸려
    RED → 개명으로 해소. 현 휴리스틱에 대한 회피이지 근본 구분이 아니다.
  - false negative 가 더 위험: 별칭 import(`import stamp as _s`)·`getattr` 경유
    호출 생성기는 놓치고, `n_gens >= 15` 가드는 대량 붕괴만 잡지 한 개 누락은 못
    잡는다.
  - 교차검증(2026-08-19): 현 리포는 양방향 깨끗 — substring 21 = AST 실제 호출 21,
    FP/FN 0. import-무호출 판독자 1건 = 위 dashboard (단, `stamp` 심볼이 아니라
    `pivot_manifest` **모듈** import 이며 용도는 `dirty_state` 정본 소비 —
    snapshot 게이트가 강제하므로 제거 대상 아님).
  - 최소 수리 = AST 호출부 탐지(pivot_manifest 에서 import 된 별칭 집합 대조).
    게이트 자체의 수정이므로 RED-first + mutation(별칭 호출 생성기 주입) 규율이
    그대로 적용된다.

**여기서 하지 않은 것 (의도적)**

- 과거 artifact backfill — 그때의 값은 그때의 계약 아래에서 사실이다.
- 역사 문서 본문 수정 — pointer/banner 로만 처리.
- science rerun — 어느 카드도 요구하지 않았고, 요구했다면 human decision 이었다.
- 결과에 맞춘 assertion 완화 — 8번의 허용오차는 서로 다른 자릿수 반올림 때문이지
  결과를 통과시키기 위해서가 아니다 (근거를 주석에 남겼다).

---

*Last updated: 2026-08-19. baseline `b330fbc` → closure `180f410`.*
