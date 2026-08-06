# 55 — 외부 리뷰 3 판정 로그 (계약 개정 검증)

**2026-08-06 · 프롬프트 = `review_prompt_contract_revision.md` · 대상 = docs/54 R1/R2 + V2/V3/V3b**

---

## 1. 판정표 (리뷰어)

| 주장 | 판정 | 핵심 이유 |
|---|---|---|
| 1. 대역 밖이지만 사전등록 위반 아님 | **조건부 유지** | primary 대역 FAIL / 사전등록 기전 귀속 PASS -- 두 줄로 분리 보고해야 |
| 2. swept 가 endpoint 보다 참에 가까움 | **조건부 유지** | "더 나은 근사"까지만. 실 이차 궤적 검증 필요 |
| 3. contact Pk 재사용은 보수적 | **기각** | 어느 방향으로 보수적인지 물리 근거 없음. "구현 격리를 위한 임시 재사용" 만 허용 |
| 4. 폴백 0/7 은 전술 난도 신호 | **기각** | selection · straw man · 늦은 handoff · n=7 · resolver 의미론이 교락 |

**가장 위험한 미검증 가정 (리뷰어 지정)**:

> swept 로 `kill_radius` 안에 든 사건이 실제 무력화 시도가 성립하는 물리적
> 접촉이며, 거기에 기존 commit Pk 를 적용해도 된다는 가정. (r_shape / r_commit
> / r_contact 세 의미가 같은 0.75 에 동시 재사용되는 것도 위험 요인.)

## 2. 반영 완료 (2026-08-06, 같은 날)

- docs/54 §3.1: **V2 FAIL/PASS 두 줄 판정** + contingency (swept-only 5판 =
  침투 4 + 무결말 1(ep44), 누수 없음) + "무력화 1.000 = Pk=1 semantics check"
  표기. "V2 통과" 표현 금지 명문화.
- docs/54 V3b 결과: "전술 난이도 신호" 표현 철회, 대안 설명 5종 병기,
  2×2 counterfactual replay (handoff 시점 × controller 강도) 를 3-way 보다
  앞선 판정 도구로 등재.
- docs/54 §3.2: 반증 실험 (A) 실 궤적 접촉 검증 (chord false positive 수,
  3건 이상이면 "15/17 강건" 철회) + (B) Pk sweep {0..1}×seed 3 사전등록.

## 3. 액션 큐 (리뷰어 우선순위, 미착수분)

```
[x] (A) 실 궤적 검증 (docs/54 §3.2) -- 적분기 = semi-implicit Euler 확정,
      0.033 상한 논법 철회. 두 interpolation 규약 간 판정 불일치 1/17(ep19),
      16/17 은 두 규약 판정 일치 (연속 물리 접촉 인증 아님).
      "3건 철회 기준"은 커밋 시각으로 사전등록 증명 불가 -> 민감도 결과로 강등
[x] (B) Pk sweep = resolver sanity + 임무 민감도 분석 -- 이항 sanity 전 구간
      PASS, 중간 Pk 에서 재시도 효과 +0.12~0.13 관측(상수 아님, Pk=1 포화).
      재시도 = 전부 서로 다른 limiter (PK_FAIL 은 소모, 동일 limiter 재시도는
      veto 후에만). physical lethality calibration 아님
[x] r_shape / r_commit / r_contact 설정 키 분리 -- 값 전부 0.75 유지,
      독립성 테스트 포함 (1e19ecf). 수치 calibration 은 이후 별도
```

**확정 큐 (리뷰 3 최종, 2026-08-06)**:

```
1. [x] 전체 회귀 476 passed / 0 failed + legacy baseline (hold n=500,
       R1 이전 참조 대비) **BIT-IDENTICAL** (2026-08-06, 반경 키 추가 뒤)
2. [x] 2×2 의 early-prep 의미·closed-loop 재실행 계약 사전등록 = docs/56
3. miss 7판 deterministic-lethality recoverability probe (2×2)
     ★ "miss−5" = fallback 선행 준비(T−5 prep)이지 조기 handoff 아님.
       완전 전환(T−5 switch)은 별도 arm·별도 사전등록
     ★ 고정 궤적 재생 금지 -- CRN 재실행 + branch 후 closed-loop
4. 결과에 따라 조기 시점 / controller 강도 / state selection 분해
5. oracle / scripted / RL frontier 비교 (docs/54 §4)
6. limiter MARL 이 frontier 를 실제로 이동시키는지 재평가
```

## 4. 거시 프레임 (리뷰어 종합 — 채택)

- 기존 환경의 질문 = "완전 robust-clean 상태를 만들 수 있는가" (인증 문제).
- 비준된 시스템의 질문 = "net 우선 + 실패 시 destructive fallback 의 최적
  운용점" (frontier 문제). **개정의 의미 = 후자를 처음으로 측정 가능하게 한 것.**
- docs/52 knife-edge 는 폐기가 아니라 지위 변경: frontier 의 가장 보수적 끝점.
- 논문 질문 재서술 (채택):

  > 협력 성형이 net 포획 가능성을 얼마나 높이며, 완전한 robust-clean 포획이
  > 불가능하거나 지나치게 좁은 경우에도 mode handoff 를 통해 전체 방어 성능과
  > 비손실성을 어떤 frontier 로 개선하는가.
