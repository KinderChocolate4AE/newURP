# 78 — 게이트 10 iso-Π reduction validation 판정 기준 선봉인 — 2026-08-11 (**r2 addendum 2026-08-13**)

---

## r2 ADDENDUM (2026-08-13) — Tier 1 이 노출한 분해: generator similarity ≠ certificate similarity

**소급 재해석 금지**: 아래는 원 protocol 의 "원래 뜻" 이 아니라 **새 tranche 의 추가
사전등록**이다. r1 의 full-rollout 판정과 그 실패는 영구 보존한다.

### A. 실행 결과 (r1 protocol 그대로, dev tranche ep 0..2 · chi {0.8,1.6})

- **T1-L.system = PASS** — max_state_dev **0.0** · max|Δv_shot| **0.0** · witness
  mask 불일치 0 · engaged mask 불일치 0. 전 파이프라인(상태생성+witness+judge)이
  길이 스케일에 대해 **기계정밀도 정확 불변**. (사전 스모크가 숨은 길이상수 1건
  적발·수정: `SpawnSpec.r_lat = 5.0 m` — 인벤토리 미등재였다. 수정 후 정확 통과.)
- **T1-T.system = FAIL (정당한 실패 — 보존)** — normalized state 가 t=2 부터 점진
  drift (t=59 에 |Δp|/ρ ≈ 2.1e-3), 그 결과 witness mask flip 8건.
  **원인 = 동결 scripted attacker 의 하드코딩 전진 P-gain**
  `a_fwd = 4.0 * (v_ref − v_fwd) * fwd` (`attacker_ladder.py:377`;
  params.py `adversary.fwd_gain = 4.0 "1/s"`). AttackerSpec/config 밖 리터럴이라
  β 로 스케일 불가 → **숨은 무차원군 k_f·τ 가 시간변환에서 2배**가 된다.
  즉 **동결 attacker 를 포함한 closed-loop 시뮬레이터는 time-similar 하지 않다.**
  이 caveat 는 영구 유지한다. (homing_gain 은 spec 필드라 이미 스케일됨.)

### B. 분해 (새 사전등록)

두 명제가 r1 에서 한 문장으로 묶여 있었다:

```
A. generator similarity :  G_{φ'}(u) =? S_β G_φ(u)      ← T1-*.system (위 A)
B. certificate similarity: C_{θ'}(S_β z) =? C_θ(z)      ← T1-*.cert (신규, 미실행)
```

T1-T 가 깬 것은 **A** 이고, **B 는 아직 시험조차 되지 않았다.** 게이트 10 의
과학적 질문(지도 C(z) 가 무차원 상태의 함수인가)은 B 이며, attacker 가 z 에
**어떻게 도달했는지**는 조건부 certificate 정의에 들어가지 않는다 (nuisance
generator). 따라서 B 를 별도 tranche 로 시험한다.

### C. T1-*.cert 설계 (결과 열람 전 고정)

1. **오염 통제**: dev tranche (ep 0..2) 는 full-rollout drift·localization 에 이미
   노출 → **primary = untouched ep 10..14**.
2. **절차**: base 월드 1회 rollout (α=β=1) → engaged 상태를 **해석적으로 변환**
   (attacker 재적분 없음 ⇒ k_f 오염 원천 제거) → 양 표현에서 certificate 평가.
   변환: T1-L(α=2,β=1) p·limiter·net_apex·range·ρ·r_kill ×2 ·
   T1-T(α=1,β=2) v÷2 · a÷4 · τ×2 (길이·각도 불변).
3. **판정** (r1 §1 bar 승계): 상태별 `|Δv_shot| ≤ 1e-6` · witness 수 일치 ·
   (caught∧turn_feasible) mask bit 일치 · boxed 일치. 사전 assert:
   normalized invariants (p/ρ, vτ/ρ, aτ²/ρ, apex/ρ) 일치 ≤ 1e-9.
4. **표기 규율**: PASS 해도 "T1-T PASS" 라고 쓰지 않는다. 정본 표기 =
   ***"full-system T1-T failed (hidden k_f·τ); conditional-certificate T1-T passed."***
5. **Tier 2 도 같은 구조로 간다** (동일 base 상태 → 차원변환 → certificate 비교).
   fresh rollout 을 다시 쓰면 C(z) 불변성과 D(z) 분포이동이 다시 섞인다.

### C-2. T1-*.cert 실행 결과 (2026-08-13, untouched ep 10..14)

| tranche | n 상태 | max\|Δv_shot\| | witness mask 불일치 | boxed 불일치 | 판정 |
|---|---|---|---|---|---|
| **T1-L.cert** (chi 0.8 / 1.6) | 160 / 108 | **0.0 / 0.0** | 0 / 0 | 0 / 0 | **PASS** |
| **T1-T.cert** (chi 0.8 / 1.6) | 160 / 108 | **0.0 / 0.0** | 0 / 0 | 0 / 0 | **PASS** |

normalized invariants 사전 assert: max dev **0.0** (bar 1e-9). 즉 조건부 certificate
(witness 생성 + judge + v_shot) 는 길이·시간 두 축 모두에서 **bit-exact 상사불변**.
숨은 절대-시간/절대-길이 상수가 certificate 경로에는 없다는 뜻이다.

**정본 표기 (§C-4 규율)**: *"full-system T1-T failed (hidden k_f·τ in the frozen
scripted attacker); conditional-certificate T1-T passed (bit-exact)."*
산출물: `results/phase3/gate10_tier1_system.json` (T1-L PASS 6/6 · T1-T FAIL 6/6,
dev tranche 보존) · `gate10_tier1_cert.json` (신규 tranche).

### C-3. Tier 2 재설계 (r3 addendum, 2026-08-13 — 실행 전 봉인)

r1 §2.1 의 Tier 2 는 "conditioning group 을 교란해 **fresh rollout** 후 (e,t) paired
비교" 였다. r2 분해 이후 이 구조는 C(z) 불변성과 D(z) 분포이동을 다시 섞는다
(§C-5). 재설계하되 **r1 판정식·bar·교란크기·검사점은 전부 승계**하고 비교 구조만
"동일 base 상태 → 해석적 교란 → certificate 비교" 로 바꾼다.

**핵심 발견 — conditioning 7군은 동질적이지 않다.** C(z;θ) 관점에서 세 부류다:

| 부류 | group | C 안에서의 지위 | Tier 2 시험 형태 |
|---|---|---|---|
| **P — certificate 파라미터** | `alpha` (cone 반각) · `lam` (cone range/ρ) · `nu` (limiter_v_max/att_speed → L1/LN reachability) · **`sig_as`** (D_asset/ρ → `R_NK` admissibility) | z 가 아니라 θ 에 들어간다 | **고정 상태 · θ 교란 · paired 비교** (가장 깨끗) |
| **Z — 상태 좌표** | `eta` (att_speed·τ/ρ = ‖v‖ 좌표) · `sig_sb` (R_standby/ρ = limiter 위치) | **z 의 성분 자체** — 교란하면 상태가 바뀐다 | **core (chi,kappa,mu,N) 고정 · 해당 좌표만 해석적으로 이동 · Q 비교** (reduction claim = "Q 는 core 로만 결정" 의 직접 시험) |
| **G — 생성기 전용** | `sig_dt` (sense_range/ρ — attacker 감지 반경) | C 의 입력이 아니다 | 고정 상태에서 **구조적으로 무변화 = 공허** → **Tier 2 에서 제외하고 게이트 11 (system similarity) 로 이관** |

- **Z 부류 교란의 정의** (결과 전 고정): `eta` = ‖v‖ 를 방향 유지한 채 ×0.8/×1.25 ·
  `sig_sb` = limiter 위치를 hold 중심 기준 반경 ×0.8/×1.25 · `sig_as` = asset 위치를
  ρ 단위 거리 ×0.8/×1.25 (r_nk 동반). core Π 는 정의상 불변 (chi·kappa·mu 는 v·
  limiter 위치·asset 을 포함하지 않는다).
- **판정 bar·집계**: r1 §2.2 그대로 — Q ∈ {V_0, U_cheap, L1, LN}, informative 상태
  (0<v<1) union, `median(D_Q) ≤ 0.02 AND p95(D_Q) ≤ 0.05`, pooled informative < 50
  이면 INCONCLUSIVE. 검사점도 r1 그대로 chi ∈ {0.4, 0.8, 1.6} × kappa 0.5 × mu 0.4
  × N 4. 상태는 **untouched tranche ep 10..14** (T1-cert 와 동일 — 이미 cert
  parity 만 봤고 Q 값 분포는 미열람).
- **sig_as 분류 정정 (실행 전, 2026-08-13)**: r3 초안은 sig_as 를 Z 로 뒀으나,
  certificate 가 asset 을 소비하는 경로는 `|배치 − asset| > R_NK` (admissibility)
  **하나뿐**이다 ⇒ θ 파라미터 = **P 부류**. 교란 = `R_NK` ×0.8/×1.25.
- **실패 해석 (정정 — "지도 정의 문제" 표현 폐기)**:
  - **P 부류 FAIL** = *"해당 파라미터는 nuisance 가 아니며 core 좌표만으로는
    certificate map 을 collapse 시킬 수 없다 ⇒ 추가 governing Π-coordinate 필요."*
    (그 파라미터가 certificate 에 실제로 들어가므로 값이 변하는 것 자체는 버그가
    아니다. "구현 결함" 은 **이론상 scale-equivalent 라 사라져야 하는데 남은 경우**
    에만 쓴다.)
  - **Z 부류 FAIL** = *"동일 preregistered core 를 유지했는데 그 상태 좌표를 바꾸자
    Q 가 체계적으로 변했다 ⇒ **missing state coordinate**."*
  - 둘을 한 문장으로 합치지 않는다.
- **Z 부류 admissibility gate (필수)**: 해석적 교란 상태 z' 는 primary 집계 전
  `z' ∈ Z_admissible` 검사를 통과해야 한다 — (i) ‖v'‖ ∈ THREAT_BRACKET att_speed
  (8, 30) (ii) 전 limiter 가 Ball(asset, R_NK) 밖 (iii) registered judge domain =
  base·교란 양쪽 모두 engaged (pre-screen). **탈락률을 산출물에 기록**한다
  (unreachable artificial states 비판 차단).
- **headline 금지**: 6군 전체를 하나의 PASS/FAIL 로 합치지 않는다. 게이트 10 의
  결론은 *"Which coordinates are sufficient to parameterize the conditional
  viability map?"* 이며, 결과표는 group × class × chi 로 분해해 보고한다
  (median/p95 + **chi 별 부호와 label-flip 분리 저장** — χ=0.8 근방에서만 커지면
  global governing axis 가 아니라 **boundary-local secondary coordinate** 일 수
  있다).
- **tranche 표기**: ep 10..14 는 T1-cert 와 공유하므로 "untouched" 라 부르지 않는다.
  정확한 표기 = *"shared frozen validation tranche; no Tier-2 perturbation outcomes
  were inspected before the r3 freeze"* (outcome-adaptive contamination 아님).

### D. 최종 claim 한정 (승격 규율 갱신)

- 검증 가능: *"Conditional capture-viability certificate exhibits iso-Π collapse
  within the tested Π-set."* / *"chi is a governing similarity coordinate of the
  conditional capture-feasibility map."*
- **금지 (이번 발견으로 확정)**: *"the complete attacker–defense closed-loop system
  exhibits iso-Π collapse"* · *"chi governs the full encounter dynamics"* —
  full encounter 에는 실제로 k_f·τ 같은 controller-response group 이 존재한다.

---


**지위**: docs/75 게이트 10 의 "허용오차" 가 미봉인이었다 (2026-08-10 세션에서 발견).
이 문서가 그 **판정 통계량·허용오차·교란 설계·실패 경로**를 iso-Π 런 0 회 상태에서
선언한다. 계약 = docs/74 r3.3 §3.9 (축 발견 금지·reduction validation 만) 을 상속하며
정의·축·measure 는 일절 건드리지 않는다. **Phase III 지도 셀 = 여전히 0 개.**

**원칙**: bar 는 발명하지 않고 **이미 비준된 것을 재사용**한다 — 게이트 2·3 의
measure-convergence bar (median ≤ 0.02 · p95 ≤ 0.05). 근거: 하네스 자체의 실측 잡음
바닥이 median 0.0020–0.0038 · p95 0.0058–0.0141 (`results/phase3/measure_harness.json`)
이므로 bar 는 잡음의 3~10 배 위에 있다. reduction 이 참이면 같은 bar 를 같은 여유로
통과한다 — measure 잡음 이하의 일치를 요구하는 것은 무의미하고, 그 이상 느슨한 bar 는
게이트를 공허하게 만든다.

---

## 1. Tier 1 — 완전 상사 (구현 감사. 물리적으로 실패 불가능한 테스트)

12 개 Π 를 전부 보존하는 정확 상사변환 2 종을 선언한다:

```
T1-L (길이 ×2): rho'=2rho · r_kill'=2r_kill · a'=2a (양측) · v'=2v (양측) ·
                range'=2range · R_standby/detect/asset'=×2 · dt·tau 불변
T1-T (시간 ×2): tau'=2tau · dt'=2dt · a'=a/4 (양측) · v'=v/2 (양측) · 길이 전부 불변
```

- **CRN 규율 (전제조건)**: 시나리오·witness 의 난수 자유도는 **무차원 형태로 뽑아
  (rho, tau) 로 스케일**한다. 절대 단위로 뽑는 자유도가 하나라도 남아 있으면 그것이
  곧 숨은 차원 상수이며 — 이 테스트가 잡으라고 있는 대상이다.
- **판정**: 같은 seed 에서 상태별 `|Δv_shot| ≤ 1e-6` (무차원 절대). predicate
  (caught/blocked/boxed) 불일치는 게이트 9 규칙 승계 — signed margin `|m| ≤ 1e-6 m`
  인 boundary case 에서만 허용, boundary 밖 불일치 1 건이면 **중단·버그 감사**.
  (1e-9 는 스케일 변경 시 부동소수점 재결합 오차 때문에 과욕 — 1e-6 로 선언.)
- **실패 해석**: 물리가 아니라 (a) 코드의 무차원화 누락 또는 (b) Π 목록 미완비.
  둘 다 지도 진행 전 수정 대상이다 (버그 수정은 §7 위반이 아니다).

## 2. Tier 2 — reduction 검증 (진짜 테스트)

### 2.1 쌍 구성 (one-at-a-time 교란)

core (chi, kappa, mu, N) 와 나머지 conditioning 을 nominal 에 고정한 기준계 대
**conditioning group 하나만** 교란한 비교계. 교란 대상·순서는 docs/73 판정 5 의
결정론적 순서를 그대로 쓴다:

```
eta → alpha → lam → nu → sig_sb → sig_dt → sig_as     (7 종 전부 검사)
```

- **교란 크기**: 물리 bracket 이 봉인돼 있는 group 은 bracket 끝점
  (eta = THREAT_BRACKET att_speed 양끝). 나머지는 nominal ×0.8 / ×1.25.
  **자백**: ±20~25% 는 관례이지 근거 있는 상수가 아니다. 결론은 항상
  "이 교란 크기 범위에서" 로 한정한다 — 채널 세기/종류 한정 (docs/74 §3.0.4) 과
  같은 규율.
- **검사 점** (전부 Z_master 격자값, pilot 격자와 정렬):
  `chi ∈ {0.4, 0.8, 1.6}` (preview 관측 gradient 의 아래/경계/위) × `kappa = 0.5`
  × `mu = 0.4` × `N = 4`. 3 점 × 7 group × 2 계 (기준/교란) × **20 episode** (CRN
  paired). 서버 샤딩 (long-run policy).

### 2.2 paired 통계량과 bar

```
D_Q(e,t) = | Q^base(e,t) − Q^pert(e,t) |,   Q ∈ { V_0, U_cheap, L1, LN }
집계 대상 = informative 상태 (0 < v < 1) — 어느 한쪽이라도 informative 면 포함 (union)
           ("접근 구간 희석" 함정 방지 — docs/77 §4-1 비준 규칙 승계)

(z, group) PASS  ⟺  4 개 Q 전부  median(D_Q) ≤ 0.02  AND  p95(D_Q) ≤ 0.05
공허 가드        :  pooled informative 상태 수 < 50 이면 PASS 아닌 INCONCLUSIVE
                    (공허 변이 함정 — docs/77 §4-2 재발 방지)
reduction 채택   ⟺  선언된 21 개 (z, group) 조합 전부 PASS
```

**논문 표기용 유도 공식** (숫자는 동결, 유도는 공식으로 제시):

> equivalence margin (δ_med, δ_p95) = (0.02, 0.05) — the pre-ratified
> measure-convergence tolerance of the harness itself; a valid reduction must be
> indistinguishable from the harness's own sampling-noise bar
> (measured floor: median 0.0020–0.0038, p95 0.0058–0.0141 ⇒ δ ≥ 3× floor).

**주의 (bar 를 런타임에 다시 계산하지 않는다)**: δ = f(실측 잡음) 형태의 자기보정
공식을 봉인하는 안은 **기각**했다 — 런 시점 잡음이 크면 bar 가 저절로 풀리는 구멍이
생긴다. 숫자를 지금 동결하고 유도만 공식으로 남긴다.

### 2.3 secondary (보고 전용 — 판정 사용 금지)

- (z, group) 별 라벨 prevalence 차이 `‖Δp‖_∞` 와 dominant-label 일치 여부.
  n = 20 에서 SE ≈ 0.11 이라 검정력이 없다 — **기술 통계로만** 보고한다
  (Stage-2 θ 슬라이스와 같은 지위).

## 3. 실패 경로 (사전 선언 — REJECT ≠ 프로젝트 종료)

1. 어떤 (z, group) 이 FAIL → **저차원 collapse claim REJECT** + 그 group 이 범인.
   결과 구제를 위한 축 추가·bar 완화 금지 (docs/74 §7).
2. 범인 group 은 지도 결론의 **conditioning 한정**으로 명시한다 — "지도는 (chi,
   kappa, mu, N | 나머지 nominal, 단 <group> 의존 확인됨) 의 함수" 라는 scoped claim
   은 그 자체로 보고 가능한 결과다.
3. 그 group 을 축으로 승격해야 지도가 성립한다고 판단되면 — 현 Phase III 종료,
   **Phase III-B 를 새 protocol_hash 로 사전등록** (docs/74 §5.1).
4. 7 종 전부 통과하지 못하고 원인 특정도 안 되면 정직한 종착지는
   **"no low-dimensional collapse supported"** — 이것도 결과다.

## 4. 산출물 규칙

- 모든 산출물에 표준 스탬프 (`protocol_hash · lattice_hash · …`, docs/74 §0-4) +
  **이 문서의 해시** (r3.4 부터 protocol_hash 구성 파일에 포함).
- 실행 시점: [G] 단계 (docs/77 §1). [E] 본실행·[F] 과 독립이므로 서버 여유 시
  선행 가능 — 단 Tier 1 은 CRN 무차원화 규율 구현 확인 후.
