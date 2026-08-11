# 78 — 게이트 10 iso-Π reduction validation 판정 기준 선봉인 — 2026-08-11

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
