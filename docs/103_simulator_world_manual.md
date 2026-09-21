# 103 — 시뮬레이터 세계 설명서 (World & Interpretation Manual)

- **일자**: 2026-09-14 (**r2** — **교수 관점의 AI 검토 반영**(실제 지도교수 검토·승인 아님): 주장 강도·적용 범위 교정, 반박 2 건 철회, 범위 경계·요약 2 쪽·"확인" 3 분류 신설) · **지위**: **설명서 (해설 문서) — 새 계약도 새 실험도 만들지 않는다.**
- **목적**: 현재 시뮬레이터가 어떤 세계를 구현하고 있으며, 그 세계에서 얻은/얻을 결과를
  어디까지 해석할 수 있는지를 한 문서로 제출한다. **모델의 우수성을 변호하지 않는다.**
- **기준 시점 (이 문서가 기술하는 세계)**:

  | 항목 | 값 |
  |---|---|
  | branch | `feat/scale-up-v2` |
  | HEAD commit | `ac7cf2a` |
  | world contract | B0 v3 **SEALED** `b0_hash = 5e7b5b486b9d8a4a` (기계 정본 `artifacts/b0/b0_v3_world_contract.json`, 서술 정본 `docs/94`) |
  | 실행 대상 캠페인 | B2 scripted (`docs/102` 봉인, **미실행**) |
  | B2 manifest | `manifest_hash = 2f887776be47f538` |
  | working tree | **clean 아님** — `shepherd/scripts/mission_rollout.py` 수정분 + B2 구현 5종 untracked (§2.1) |

- **작성 원칙 (docs/94 승계)**: **세계가 코드에 실재하는 대로 적는다.** 희망 사양을 적고
  나중에 맞추지 않는다. 없는 것은 "부재" 로 적는다.
- **범위 한정**: 본 문서는 **기술(記述)** 이다. 새 구현·새 학습 신호·새 실험 과제를
  만들지 않는다. 발견된 불일치는 §2.3 과 §11.3 에 기록하고 처분은 별도 문서 소관이다.
- **정본 관계**: 본 문서는 어떤 봉인 계약도 supersede 하지 않는다. 본 문서와 `docs/94` /
  `artifacts/b0/b0_v3_world_contract.json` 이 어긋나면 **후자가 정본**이다 (§2.5 우선순위).

> ### 범위 경계 (r2 신설 — 반드시 먼저 읽을 것)
>
> **본 문서는 현행 B2 세계를 기술한다. 후속 연구의 목표 · 평가 기준 · 범위는 별도
> 결정 사항이다.**
>
> §1 에 적힌 연구 질문 · 성공의 정의 · 연구 정체성 · self-play 제외는 **현행 계획
> (`docs/89` r4 · `docs/93`) 의 상태를 기록한 것**이며, 본 문서가 후속 연구 방향을
> 확정하거나 제약하는 근거가 아니다. 평가 기준을 바꾸는 것은 계획 문서의 판올림
> 사안이고 설명서의 권한이 아니다.

**읽는 순서 (시간이 없을 때의 핵심 6 절)**: §요약 두 쪽 → §2.3 의도–구현 대조표 →
§4.3 τ₀ 가 무엇의 지연이 아닌가 → §7.4 지표 해석표 → §10.2 세 종류의 "성공" →
§11 최종 판정표. 나머지는 그 여섯 절의 근거이고, 부록 B·C 는 참조표다.

### 이 문서 자체의 지위 — §9.4 의 구분을 이 문서에도 적용한다

본 설명서는 **AI 산물**이다. §9.4 가 "AI 감사 / 사람 검토 / 독립 재현" 을 구분하라고
요구했으므로 그 규율을 이 문서에도 적용해 적는다.

- **작성 방법**: 10 개 차원(실행경로 · 물리 · 관측 · 시간 · 적대자 · 지표 · 파라미터 ·
  검증 · 결과 · 정본)을 각각 코드·문서에서 추출한 뒤, **차원마다 별도 검증자가 근거
  줄번호를 직접 열어 반박**하는 2 단계를 거쳤다. 마지막에 완결성·정직성 비평가가
  "미확인을 검증된 것처럼 쓴 문장" 을 색출했다.
- **r1 → r2 검토**: **교수 관점에서 수행된 AI 검토** 1 회. 주장 강도·적용 범위를 교정하고
  반박 2 건을 철회시켰다. **이것은 AI 감사이지 사람 검토가 아니다.**
- **사람 검토**: **아직 없다.** 이 문서는 지도교수 검토를 **받기 위한** 제출물이며,
  r2 까지의 어떤 판정도 지도교수의 승인을 뜻하지 않는다.
- **독립 재현**: 없다.
- **초안이 실제로 틀렸던 항목 (교차검증에서 정정)**: ① cone 기하를 세계 상수로 적었으나
  **셀 의존**이었다 ② 관측을 "full-state" 로 적었으나 **보호 자산·NK 구역이 관측에 없다**
  ③ `sense_range = 30 m` 를 "비구속" 으로 적었으나 limiter 소모 시 **load-bearing** 이다
  ④ 도달집합 표본을 2000 으로 적었으나 실제 witness 는 **union 중앙값 2504** 다
  ⑤ τ 분해 3 항을 뭉뚱그렸으나 미실현 항은 **`sense` 하나**다
  ⑥ `cone.range_max` 를 "출처 미확인" 으로 적었으나 **유도 근거가 명시돼 있다**
  ⑦ 두 arm 이 "컨트롤러만 다르다" 고 적었으나 **KINETIC 구간에서는 동일**하다.
- **r2 개정 (교수 관점의 AI 검토 반영 — 실제 지도교수의 검토·승인이 아니다) — 이번에는 반대 방향의 과장을 걷어냈다**:
  ⑧ 유한 표본 판정을 **"보수적 보장"** 으로 확대한 것을 철회 (§5.1)
  ⑨ `P(N|FIRE)` 상승을 **원인 분석**으로 읽은 것을 기술 수준으로 하향 (§7.4, §12)
  ⑩ **"full-state"** 와 CTDE 무이점 결론을 철회 (§3.4)
  ⑪ 타이머 구현을 **"물리 실현"** 으로 쓴 것 정정, τ 하한 논거를 `m4_config` 의 주장으로
     귀속 (§4.3, 부록 C)
  ⑫ `101-A` 기전 사슬에 대한 **반박 두 건을 재계산 후 철회** (§10.3) — δ_g 두 수치는
     측정 시점이 다르고, `RET_noeffect` 수치는 산출물에서 정확히 재현된다
  ⑬ **"정반대"** (99-N vs 99-P) 와 **"순환"** (λ2 scout) 판정 철회
  ⑭ 재현성 철회 · 학습 스택 미검증 · tunneling 을 **각각의 실제 범위로 축소**
  ⑮ 후속 연구 목표·평가 기준을 **현행 계획의 상태 기록**으로 재표기 (범위 경계 신설)
- 이 두 목록을 함께 남기는 이유는, **초안이 낙관 쪽으로 일곱 군데, 비관 쪽으로 여덟 군데
  틀렸다**는 사실 자체가 §9 의 논지에 대한 증거이기 때문이다 — **자기 코드·자기 요약과의
  대조는 방향에 관계없이 검증이 아니다.** 특히 ⑫ 는 초안이 산출물을 열어보지 않고
  노트와 `summary` 블록만 대조해서 생긴 오류다.

---

## §요약 — 세계의 정의 · 알려진 한계 · 미확인 사항 (두 쪽)

### A. 세계의 정의

| 항목 | 내용 |
|---|---|
| **무대** | legacy 24 m 회랑. 보호 자산 원점, 침투 반경 1 m. 공격기 **1**, limiter **4**, net-capturer **1** |
| **동역학** | 기체당 `[위치 3, 속도 3, 지향 단위벡터 3]`. `v ← clip(v + a_cmd·dt)`, `p ← p + v·dt`, `e ← slew`. **가속 명령 방향에 제약이 없는 등방 double integrator + 동역학적으로 결합되지 않은 율제한 지향축** (코드 자신의 명칭: `point-mass-plus-heading`) |
| **시간** | dt = Δt_dec = 0.05 s. τ₀ = τ_deploy = 0.30 s (6틱), τ_lock = 0.10 s (2틱), τ_kill = 0.15 s (3틱). 지평선 160틱 = 8.0 s |
| **net** | **물리 객체가 없다.** 발사 후 지연은 FSM 타이머, 포획은 발사 틱에 동결되는 기하 술어 |
| **포획 판정** | `(¬boxed_in) ∧ (v_shot_worst ≥ 1.0)` — 공격자 τ-도달집합의 **표본된** 실현가능 종점 전부가 finisher 원뿔 안에 들어오는가. 원뿔은 **셀 의존** (slice 0: 반각 0.212 rad · 밴드 [0, 8.22] m / slice 2: 0.273 rad · [0, 6.33] m) |
| **kinetic** | 반경 0.75 m 접촉 → 자산 6 m 안이면 기폭 보류(veto), 밖이면 `Bernoulli(p_kill = 1.0)` |
| **관측** | **65 차원, 전 방어자 동일 벡터.** 무잡음·무지연·참값 |
| **행동** | limiter `Box(4)` = 가속 3 + 커밋 비트 / finisher `Box(5)` = 지향 3 + 예약 1 + 발사 비트 / 공격자는 env 가 스크립트로 덮어씀 |
| **공격자** | **A2-nominal, 고정 규칙, 학습하지 않음.** 7 항의 합 (전방구동 · jink · 종말게이트 · route · dodge · repel · homing) |
| **성공 라벨** | `N` = CAPTURED ∧ 에피소드 누적 접촉 = ∅ / `H_fb` / `H_illegal` / `F_other` 4 분할 |

### B. 알려진 한계 (근거가 확보된 것)

1. **포획 판정의 보장 대상은 표본 집합이다.** 도달집합은 집합 수준에서 과대근사되지만
   그 뒤 **유한 표본화**된다. 연속 집합 전체를 덮었다는 증명은 이 문서에 없다 (§5.1).
2. **성립 지도는 limiter 가 완전히 부동인 조건에서 측정됐다** (`limiter_mode="hold"` =
   `zeros(4)`). 컨트롤러 비교 지도가 아니다 (§10.1).
3. **관측에 임무 기하가 없다.** 보호 자산 좌표 · `r_nk` · `d_asset` 이 65 차원에 없고,
   자산이 매 에피소드 원점 고정이라 암묵적으로 외울 수만 있다 (§3.1).
4. **τ₀ 는 물리 지연 전체를 대표하지 않는다.** 총 pending = 0.40 s 이고, 관측 잡음 ·
   측정 지연 · 통신 지연 · actuator lag 는 코드에 없다 (§4.3).
5. **두 arm 의 차이는 NET 단계에만 존재한다.** KINETIC 진입 후 `limiter_kw` 가 교체되어
   제어가 동일해진다 (§3.3).
6. **B2 primary 는 미실행이고, 그 실행 계층은 버전 관리 밖이다** (§2.1, §10.4).
7. **실행 파라미터의 다수가 `ASSUMED`** 이며, 문헌 앵커의 근거 문서는 스스로
   "AI 추출 DRAFT · 비준 전 논문 인용 금지" 를 달고 있다 (§8.3).

### C. 미확인 사항 (판단할 증거가 없는 것)

| | 항목 | 종류 |
|---|---|---|
| 1 | **그물이 실제로 기체를 무력화하는지** — 접촉·얽힘·손상 모형이 부재 | 질문의 의미를 바꿈 |
| 2 | 협력이 **필요한지**, 그리고 C arm 이득이 협력 기하 때문인지 | 〃 |
| 3 | **`Δχ50` (primary estimand)** — arm 간 계산기가 리포에 없어 **현재 산출할 수단이 없다** | 〃 |
| 4 | HARD_KILL 이 실제 치명 효과를 뜻하는지 (`p_kill = 1.0` 은 항등 함수) | 〃 |
| 5 | 학습 정책이 무엇을 달성하는지 — 현 세계 기준 산출물 0 건 | 후속 |
| 6 | λ = 3.574 slice 의 χ50 값 — exploratory scout(n=480)과 confirmatory(n=1360/행)가 최대 0.017 다르고 adjudication 기록이 없다 | 범위 제한 |
| 7 | 실기체(6DOF) 전이 · 다른 공격자 · 잡음/지연 하 강건성 | 범위 제한 |

### D. 이 요약을 읽고 하지 말아야 할 것

- 위 "알려진 한계" 를 **프로젝트의 실패**로 읽는 것. 대부분은 봉인 문서가 스스로 적어둔
  조건이거나 이번 정독에서 좁혀진 적용 범위다.
- 위 "미확인" 을 **전부 신규 실험 과제**로 바꾸는 것. C-1 과 C-4 는 이 모델이 원리적으로
  답할 수 없으며 **명시 대상이지 해소 대상이 아니다**.

---

## §0. 읽는 법 — 지위 표기 규약

이 문서의 모든 진술에는 두 축의 표기가 붙는다. **둘을 섞어 읽으면 안 된다.**

**축 A — 구현 지위** (그 항목이 코드에 있는가):

| 표기 | 뜻 |
|---|---|
| **[활성]** | 현재 실행 경로 (B2 scripted) 에서 실제로 계산된다 |
| **[비활성]** | 코드에 존재하나 현재 경로에서 호출되지 않는다 (과거 실험 / 기본 off 옵션) |
| **[문서만]** | 설계 문서에 있고 코드에 없다 |
| **[부재]** | 문서·코드 어디에도 없다 (의도적 생략) |
| **[충돌]** | 문서와 코드, 또는 코드 내부 사본끼리 다르게 말한다 |
| **[미커밋]** | 작업 트리에만 있고 `ac7cf2a` 에는 없다 |

**축 B — 근거 지위** (그 값·규칙이 무엇 위에 서 있는가):

| 표기 | 뜻 |
|---|---|
| **(물리)** | 물리 법칙에서 유도된 모델 |
| **(실측)** | 외부 실측/문헌 수치로 보정한 근사 |
| **(문헌)** | 문헌에서 가져온 가정 |
| **(규약)** | 연구를 위해 우리가 정한 처리 규칙 — 물리 주장 아님 |
| **(미확인)** | 아직 근거를 확인하지 못한 가정 |

> **규약이 일관적이라는 사실은 물리적 타당성의 근거가 아니다.** 이 문서에서 (규약) 이
> 붙은 항목은 전부 "우리가 그렇게 정했다" 이지 "세계가 그렇다" 가 아니다.

**축 C — "확인" 의 세 종류** (r2 신설). 이 문서에서 "확인" 이라는 말은 세 가지 중 하나만
뜻하며, **한 종류의 확인이 다른 종류를 함의하지 않는다.**

| 표기 | 무엇을 확인했는가 | 확인되지 않는 것 |
|---|---|---|
| **〈구현 확인〉** | 코드가 선언한 대로 계산한다 | 그 규칙이 타당한가 |
| **〈출처 확인〉** | 어떤 값이 어떤 문서·문헌에서 왔다고 **기록돼 있다** | 그 기록이 원문과 맞는가 (사람 대조 여부는 따로 적는다) |
| **〈외부 타당성 확인〉** | 모델 밖의 측정과 부합한다 | — |

> **이 프로젝트에 〈외부 타당성 확인〉 은 한 건도 없다.** 하드웨어·HIL·비행시험 기록이
> 없으므로, 이 문서의 모든 "확인" 은 〈구현 확인〉 또는 〈출처 확인〉이다.

---

## §1. 이 세계가 답하려는 질문 — 선언문

### 1.1 연구 질문

이 모델은 **하나의 질문**에 답하기 위해 만들어졌다.

> **지연되고 유한하며 비가역인 포획 효과기(net)를 가진 방어팀에서, 값싼 다수
> limiter 의 사전(pre-FIRE) 기동이 clean net capture 의 성립 경계
> χ50^net(η, λ) 를 움직이는가.**

부수 질문 (secondary, 별도 층):

> net 이 실패한 뒤의 kinetic fallback 을 포함한 전체 무력화 확률
> P_U = P_N + P_{H_fb} 는 어디까지 도달하는가.

두 질문은 **합산하지 않는다** (§7.1).

### 1.2 이 모델이 표현하는 현실 시스템의 범위

- last-mile counter-UAS 교전의 **guidance / engagement 층**. 1 공격기 vs 4 limiter +
  1 net-capturer, 24 m 급 회랑, 보호 자산 1점.
- 각 기체는 **병진 점질량 + 단위 지향축** 으로 표현된다. 가속 명령이 즉시 적용되고
  속도·가속 크기만 clamp 된다.
- **현행 계획이 선언한 연구 정체성**은 aerospace guidance/systems 이며 MARL 알고리즘
  frontier 가 아니다 (`docs/93 §1`, **미봉인 설계 노트**). 그 계획 하에서 MAPPO 는
  **high-level guidance policy** 로 규정되고 body-rate 제어가 아니다.
  — 이것은 **계획의 상태 기록**이다. 본 설명서가 후속 연구의 정체성을 확정하지 않는다
  (범위 경계 참조). 다만 **현 백엔드에 body rate 가 물리적으로 정의되지 않는다**는
  사실은 계획과 무관하게 코드 사실이다 (§5.1).

### 1.3 의도적으로 제외한 현상

아래는 전부 **코드에 없음을 확인한** 것이다 (§5.1 에 근거 줄번호).

강체 6DOF 자세동역학 · 모멘트/관성 · 추력/항력/공력 · 중력 · 바람 · 1차 actuator
지연 · 배터리/에너지 · 센서 잡음 · 측정 지연 · 통신 지연/손실 · 표적 오분류 ·
그물의 탄도 비행과 전개 형상 · 강체 충돌 물리 · 지면/장애물 · 다수 공격기 ·
재장전(K ≥ 2) · 공격자 학습(self-play).

마지막 두 항(K ≥ 2 · self-play)은 **물리적 불가능이 아니라 현행 계획의 범위 결정**이다
(`docs/89 §2`). 나머지는 구현 부재다.

### 1.4 이 모델만으로는 답할 수 없는 질문

1. **실제 기체가 이 기동을 낼 수 있는가.** 가속 벡터가 한 tick 에 임의 방향으로
   회전하는 세계이므로 airframe-level realizability 는 이 모델 밖이다 (`docs/93 §2`).
2. **그물이 실제로 기체를 무력화하는가.** 이 세계에 그물의 접촉·얽힘·손상 모형이 없다.
   NET_CAPTURE 는 **기하 술어의 성립**이지 무력화의 관측이 아니다 (§7.2).
3. **센싱이 불완전할 때도 같은 경계인가.** 관측 잡음·지연이 배선돼 있지 않다 (§3.4).
4. **A2 이외의 공격자에게도 같은 경계인가.** primary 는 A2-nominal 단일이다 (§6.5).
5. **이 지연 값(τ₀ = 0.30 s)이 특정 하드웨어에서 맞는가.** τ₀ 는 선언된 특성 척도이고,
   결과는 그 척도로 무차원화돼 있다 (§4.3).
6. **협력이 필요한가.** R2b 는 협력 necessity 를 확립하지 않았다 (§9, C049).

### 1.5 성공의 세 가지 — 같은 사건이 아니다

| 층 | 정의 | 관측 주체 | 이 문서에서의 표기 |
|---|---|---|---|
| **A. 시뮬레이터 성공** | `NET_CAPTURE` 라벨 = CAPTURED ∧ 누적 contact = ∅ | 코드의 술어 | **N** |
| **B. 실제 시스템 성공** | 실제 기체가 포획·무력화되고 자산이 보호됨 | 현실 (이 모델에 없음) | — |
| **C. 연구 가설 지지** | 협력 조향이 χ50 경계를 통계 규칙에 따라 밀었음 | §2-11 판정 규칙 | **Δχ50 > 0** |

- **A ⇏ B**: A 는 fire 시점에 동결된 도달집합 술어다. §7.2 참조.
- **A ⇏ C**: 한 판의 성공은 경계 이동이 아니다. C 는 14 행 × 3 seed 의 사전등록
  다수결 + 전역 효과 규칙을 통과해야 성립한다.
- **C ⇏ B**: C 가 성립해도 그것은 **이 봉인된 축소차수 세계 안에서의 경계 이동**이다.

**현행 계획(`docs/89` r4 · `docs/94` §2-11)이 정한 성공의 정의는 C 하나**이며, 평균
성공률 상승 · 보상 상승 · 한 셀의 개선은 그 정의에 해당하지 않는다.

> **범위 (r2)**: 위 문장은 **현재 봉인된 평가 기준을 기술**한 것이다. 후속 연구가 다른
> 평가 기준을 채택할 수 있고, 그것은 계획 문서의 판올림 사안이다 — 본 설명서가
> 향후 평가 기준을 C 로 고정하는 근거가 아니다. 설명서의 역할은 **지금 C 가 무엇을
> 뜻하고 무엇을 뜻하지 않는지** 적는 것까지다.

---

## §2. '설계한 세계' 와 '실행되는 세계'

### 2.1 기준 버전 · 실행 경로 · 설정

**실행 경로 (B2 scripted, 한 에피소드)**:

```
b2_run.run_scenario                     scripts/b2_run.py:120-
  └ scenario_kwargs(manifest, cell, s)  b2_run.py:71   ← 격자는 manifest 가 정함
      └ r2a_stage1.resolve(impl, χ, η)  r2a_stage1.py:57   ← 무차원 → 차원값
  └ build_m4_env(seed0, s, **kw)        m4_env.py:105
      ├ m4_episode_config → as_config   m4_config.py:305 / params.py:430
      ├ make_train_env → ShapingParallelEnv(AnalyticBackend)
      ├ ModeSystemEnv(inner, ...)       env_sys.py:278   ← 커밋·가드·종료 래퍼
      ├ attach_attacker(inner, A2)      env_adv.py:130   ← 백엔드 프록시
      ├ spawn_for_episode               spawn_rand.py:230
      └ attach_threat_obs               obs_threat.py     ← 관측 뒤에 위협등급 2차원
  └ mission_rollout.run_episode         mission_rollout.py:326-
```

**래핑 순서 (바깥 → 안)**:
`ThreatObsEnv` → `ModeSystemEnv` → `ShapingParallelEnv` → `AdversaryOverrideBackend`
→ `AnalyticBackend`.

**⚠ 재현성에 관한 사실 (반드시 읽을 것)**:

| 항목 | 상태 |
|---|---|
| `docs/102` (B2 봉인 사전등록) | **커밋됨** (`b44ba42`, `ac7cf2a`) |
| `shepherd/scripts/b2_{run,manifest,readout,forced_fire}.py` | **[미커밋] untracked** |
| `tests/test_b2_contract.py` | **[미커밋] untracked** |
| `shepherd/scripts/mission_rollout.py` 의 `partition_bin` · `kinetic_fallback` | **[미커밋] modified** |
| `docs/{86,88,89,90,93}` · `artifacts/audits/external_audit_report_2026-09-07.md` | **[미커밋] untracked** |

> **즉 `ac7cf2a` 를 체크아웃하면 B2 를 실행할 수 없다.** 봉인된 사전등록은 저장소에
> 있으나 그것을 집행하는 코드는 아직 저장소에 없다. 이 설명서가 기술하는 "실행되는
> 세계" 는 **작업 트리 기준**이다.

### 2.2 파라미터는 3층으로 해석된다

이 저장소에서 "이 값이 얼마인가" 라는 질문에는 **층을 말하지 않으면 답이 없다.**

| 층 | 위치 | 역할 | 예 (kill_radius) |
|---|---|---|---|
| **L1 동결 계약** | `params.py` `PARAMS` (+ `configs/m2_l2_train.yaml`) | M2/L2 시절 비준 기준값. 동결. | 2.0 m |
| **L2 M4 운용점** | `m4_config.M4_OVERRIDES` | 날짜·근거·문서참조와 함께 선언된 오버라이드 | 0.75 m |
| **L3 캠페인 주입** | `r2a_lattice._inject` / `r2a_stage1.resolve` | (χ, η, λ) 좌표를 유지하며 전 차원량 co-scale | 0.75·(ρ/ρ_ref) |

**따라서 `params.py` 를 단독으로 인용하면 현재 세계를 틀리게 기술하게 된다.**
`params.py` 는 자신이 동결 기준선임을 명시하고 있고 (`params.py:33-38`),
`m4_config` 가 그 위에 선언적 오버라이드를 얹는 구조가 설계 의도다. 결함이 아니라
**층이며, 층을 밝히지 않는 인용이 결함**이다.

**한 셀(`r00c0`, λ=4.644, η=2.1, χ=0.56)에서 실제로 해석된 값** — 라이브 실행으로 확인:

| 양 | 값 | 층 |
|---|---|---|
| `physics.dt` | 0.05 s | L3 (= L1) |
| `physics.tau_deploy` (τ₀) | 0.30 s | L3 (L2 선언) |
| `physics.tau_lock` | 0.10 s | L3 |
| `SystemSpec.tau_kill` | 0.15 s | L3 |
| `physics.net_radius` (ρ) | 1.77 m | L3 (L2 선언) |
| `physics.kill_radius` | 0.75 m | L3 (L2 선언) |
| `viability.cone.range_max` (R_max) | **8.22 m (slice 0) / 6.3258 m (slice 2)** | L3 — **셀 의존**, §10.1 |
| `viability.cone.half_angle` | **0.21209 rad (slice 0) / 0.2728 rad (slice 2)** | L3 = arctan(ρ/R_max), **셀 의존** |
| `physics.a_att_max` | 22.109 m/s² | L3 (셀의 χ 에서 역산) |
| `physics.att_speed` | 12.464 m/s | L3 (셀의 η 에서 역산) |
| `physics.a_lim_max` | 7.738 m/s² | L3 = 0.35 × a_att |
| `train.episode_len` | 160 step = 8.0 s | L2 |
| `finisher.a_max` | **0.0** (net-capturer 는 병진하지 않는다) | L1 |
| `finisher.K` | 1 (단발) | L1 |
| `fire_gate.theta_fire` | 0.9 | L1 |

### 2.3 의도–구현 대조표 (핵심 항목)

| # | 항목 | 설계상 의도 (문서) | 실제 실행되는 정의 (코드) | 근거 | 일치 |
|---|---|---|---|---|---|
| 1 | 포획 술어 | "attacker 가 net 구 안에 있으면 포획" (env.py:305-308 첫 주석) | fire 틱에 동결: `(¬boxed_in) ∧ (v_shot_worst ≥ 1.0)` — 판정자 se3_cone 의 **도달집합 worst-case** | `env.py:316-320` · `params.py:env_frozen.capture_rule` | **차이 있음** (주석 1행 stale; 계약·registry C008 은 코드와 일치) |
| 2 | `capture_thresh` | docstring: "captured iff v_shot_soft ≥ capture_thresh" | **읽히지 않음 (DEAD)** | `params.py:env.capture_thresh` | **차이 있음** (문서화된 결함) |
| 3 | CWC 보상 | docs/94 결재 ④: hybrid mission 에서 CWC 는 clean capture 보상 **불가** (supersede) | `RewardSpec.terminal` 은 여전히 `CAPTURE_WITH_CONTACT → +b_net` | `env_sys.py:203-205` | **차이 있음 — 미이행** |
| 4 | reference fallback (PN takeover) | docs/102 §1: "world 기본, 양 arm 동일 작동" | **코드에 조종 전환이 없었다.** 2026-09-14 에 `run_episode(kinetic_fallback=…)` 로 신규 배선 | `mission_rollout.py` [미커밋] · `temp_research_note/2026-09-14c §2` | **문서만 → 미커밋 구현** |
| 5 | outcome partition (N/H_fb/H_illegal/F_other) | docs/94 §2-9 | `partition_bin()` 신규 구현 | `mission_rollout.py` [미커밋] | **문서만 → 미커밋 구현** |
| 6 | `omega_att_max = 8.0` (공격자 선회율) | env.py 가 공격자에 전달 | 스크립트 정책이 인자를 **받지만 쓰지 않는다**. 실제 slew 는 백엔드 10.0 | `params.py:env_frozen.adversary_omega_att_max` · `env_adv.py:112` | **차이 있음 (DEAD)** |
| 7 | `attitude.e_net_init` · `viability.seed` · `baselines.*_u0` | 설정으로 바꿀 수 있는 값 | **조용히 무효** (백엔드/ env 가 하드코딩) | `params.py` 각 항목 (2026-08-08 감사 C6) | **차이 있음** |
| 8 | net 전개 | "net 이 τ_deploy 후 전개된다" | net 객체·비행·형상 **없음**. 지연은 FSM 타이머, 포획은 fire 시점 동결 술어 | `finisher_fsm.py` · `env.py:316` | **차이 있음 (표현 층위)** |
| 9 | F1 주석 | "frozen at the DEPLOYING→LOCKED transition" | fire_event 에서 동결 | `env.py:305-308` | **해소됨** (2026-09-13 주석 수정, docs/94 §2-2) |
| 10 | `miss_terminates` 기본값 | 비준 F-계약은 `False` | `SystemSpec` **기본값은 `True`**; `ratified_system()` 이 명시적으로 `False` 로 파생 | `env_sys.py:118` · `:135-148` | **일치** (호출부가 파생) |

### 2.4 현재 실행에 적용되지 않는 코드 (대표)

| 범주 | 예 | 상태 |
|---|---|---|
| 과거 세대 env | `env_m3.py` (443줄) | [비활성] B2 경로 미사용 |
| 학습 스택 | `shepherd/train/*` (17 파일, MAPPO/IPPO/PPO/COMA/BC) | [비활성] — B0 v3 불변 조항이 stop rule 통과 전 MARL 실행을 금지 |
| 과거 캠페인 스크립트 | `shepherd/scripts/` 197 파일 중 a3*/c1*/e1* 계열 다수 | [비활성] 봉인된 과거 결과의 생성기 |
| 기본 off 스위치 | `capture_terminates=False` (sham-net) · `force_commit_step` · `perfect_aim_at_commit` · `threat_obs enabled=False` | [비활성] B2 에서 전부 미사용 (forced-fire 진단은 primary **이후** 별도 계정) |
| 미구현 stub | `baselines.no_shaping / selection_only / buy_nets` | `NotImplementedError` |

### 2.5 정본 충돌 시 우선순위 (제안)

문서가 서로 다르게 말할 때 적용할 순서. **본 문서가 제안하는 규칙이며 봉인이 아니다.**

1. **코드의 실행 경로** — 무엇이 계산되는가의 최종 심급.
2. **기계 정본 JSON** — `artifacts/b0/b0_v3_world_contract.json`, `b2_scripted/manifest.json`.
3. **서술 정본 (봉인 문서)** — `docs/94`, `docs/102`, `docs/89 r4`.
4. **연구노트** `temp_research_note/` (최신 일자 우선).
5. **일반 docs/** (봉인 표기 없는 것).
6. **`CLAUDE.md` 요약 / `docs/00_status.md`** — **가장 낮음.** 둘 다 과거 스냅샷이며
   현재 세계와 어긋난다 (§11.3 U-8).

단, **1 이 2·3 과 어긋나면 그것은 "코드가 이긴다" 가 아니라 "미이행 또는 계약 위반"
으로 §2.3 에 기록해야 하는 사건**이다. 위 순서는 *기술*의 우선순위이지 *권한*의
우선순위가 아니다.

---

## §3. 상태 · 관측 · 행동

### 3.1 정보 접근표 — 세 층의 분리

| 층 | 내용 | 누가 보는가 | 근거 |
|---|---|---|---|
| **W. 세계 상태** | 6 기체의 (p, v, e) 전부 · FSM 상태·타이머·잔탄 · commit/contact 기록 · retired/pending 집합 · net_spent_step · veto 카운터 | 시뮬레이터 내부 | `analytic.py:137` · `env_sys.py:298-` |
| **O_def. 방어자 관측** | **65 차원 벡터 1개. 4 limiter 와 finisher 가 전부 동일한 벡터를 받는다.** | 방어자 정책 | `env.py:207-218`, `env.py:410` |
| **O_att. 공격자 관측** | 스크립트가 인자로 받는 묶음 (§3.5) — 관측 벡터를 쓰지 않는다 | scripted A2 | `env_adv.py:139-165` |
| **E. 평가자 전용** | 에피소드 누적 contact 집합 · `first_contact_t` · `first_engage_t` · `net_spent_step` · `hard_kill` · CommitRecord 전체 · telemetry | 판정·사후분석 only | `mission_rollout.py:374-` |

> **핵심 1**: 기체 운동학에 대해서는 **부분관측이 아니다.** 모든 방어자가 **같은 65 차원
> 벡터**를 받는다 (라이브 확인: `all(obs['limiter_0'] == obs[k])` = True). 따라서
> "분산 관측 하 협력" 을 주장할 수 없다 — 이 세계의 협력은 **공통 관측 위의 행동 분화**다.
>
> **핵심 2 (교차검증에서 정정된 사항)**: 그러나 **임무 기하는 관측에 없다.**
> `layout.target` · `target_radius` · `r_nk` · `d_asset` 가 **65 차원 어디에도 실리지
> 않는다.** 침투 판정 · NK 거부권 · arc slot 배치가 전부 `target` 을 쓰는데 정책은 그것을
> 받지 못한다. 이것이 문제가 되지 않는 이유는 단 하나 — **`target` 이 전 에피소드
> `[0,0,0]` 으로 고정**이라 암묵적으로 외울 수 있기 때문이다. 즉 "관측 가능" 이 아니라
> **"세계가 고정이라 관측이 불필요"** 다. 자산 위치를 랜덤화하면 현 관측으로는 임무를
> 풀 수 없다 — 이것은 일반화 주장의 직접적 한계다.

### 3.2 변수 사전 — 관측 벡터 65 차원 (요약, 전체는 부록 B)

`[limiter 0..3] × 9 + finisher 9 + adversary 9` = 54 (각 9 = 위치 3 · 속도 3 · 지향
단위벡터 3, **월드 관성계 · SI · 정규화 없음**) + `[k_norm, FSM one-hot 4, timer]` = 6
+ `[v_shot_soft, v_shot_worst, p_feasible]` = 3 + **위협 등급 2** = **65**.
갱신 시점은 전부 **이동 후 (post-move)** (`env.py:389-391`).
성분별 의미·단위·비고는 **부록 B**.

**마지막 2 성분에 대한 명시적 이상화 선언** — `obs_threat.py` 자신이 적고 있고, 이
설명서가 그것을 승계한다:

> 정책에 공격자의 **참 최대가속과 참 속도 등급**을 오차 없이 준다. 실제 체계의
> 표적 분류는 잡음과 오분류가 있다. **이 이상화는 우리에게 유리한 방향이며**,
> 오분류 하 강건성은 이 모델 밖(층3)이다.

### 3.3 행동 공간

| 에이전트 | 공간 | 성분 | 실제 사용 |
|---|---|---|---|
| limiter i (×4) | `Box(4)`, 앞 3 성분 ±a_lim_max (셀에서 ±7.738), 4번째 [0,1] | `[a_x, a_y, a_z, commit_bit]` | 가속 = 명령 그대로 (clamp 후). `commit_bit > 0.5` 는 **`ModeSystemEnv` 가 읽는 kinetic 커밋 제안**이며 동결 env 는 무시 |
| finisher | `Box(5)`, `[-1,-1,-1,0,0]`…1 | `[e_x, e_y, e_z, (reserved), fire_bit]` | 앞 3 = 지향 명령 (slew ω=2.0 rad/s 로 율제한). idx3 은 **수신 후 무시**. `idx4 > 0.5` = FIRE |
| adversary | `Box(3)` ±22.1 | — | **env 가 스크립트로 덮어쓴다. 외부 입력은 무시된다** (`env.py:344`) |

**B2 두 arm 이 실제로 넣는 것** (`docs/102 §1`):

- **SOLO**: `hold_position_limiter()` = `zeros(4)` — 가속 0, 커밋 0. 완전 정지 유지.
- **RULE_COOP**: `arc_redeploy_limiter(...)` = 배정 slot 으로 PD 호밍
  (`kp=8.0, kd=4.0`, `r_d=9.0, dφ=π/6`), 커밋 비트 0.
- **두 arm 은 limiter 컨트롤러만 다르다.** finisher · 발사 규칙 · 공격자 · CRN 동일.

> **⚠ 그런데 그 차이는 NET 단계에만 존재한다 (교차검증 신규 발견)**: `kinetic_fallback`
> 이 KINETIC 진입 후 `limiter_kw` 를 **통째로 교체**하는데, manifest 의 `fallback` 필드에
> `limiter_kw` 키가 없어 `None` 이 된다. 따라서 RULE_COOP 의 `{r_d 9.0, dφ π/6}` 가
> **버려지고 두 arm 의 제어가 KINETIC 구간에서 완전히 동일해진다.**
>
> 귀결: **arm 효과는 NET_PRE / NET_PENDING 구간에만 존재한다.** 이것은 "컨트롤러만
> 다르다" 보다 강한 제약이며, net 실패 후 구간이 길어지는 hard regime (높은 χ) 에서
> **arm 차이가 구조적으로 희석**된다. B2 판독은 이 사실 위에서 읽어야 한다 (§11.3 U-3).

### 3.4 이상화 선언 — 관측은 참값이다

- 방어자 관측과 FIRE 판정 입력 (`v_shot_soft`, `boxed_in`) 은 **당 틱 참값**에서 즉석
  계산된다. buffer · 필터 · 측정 나이 · 잡음 주입 코드가 **배선돼 있지 않다**
  (`docs/94 §1.3` 이 전수 확인으로 선언; 본 설명서가 재확인).
- **이것은 측정 결과가 아니라 세계의 정의다.** 따라서 이 세계에서
  **t_obs ≡ t_fire** 이고 **τ_real ≡ τ_deploy by construction** 이다.
- 유일한 지연성 정보 채널은 A3-privileged 공격자에게 주는 `v_shot_soft` 1-step leak
  (`env_adv.py:161`) 이며, **A2-nominal 인 현 캠페인에는 해당 없음** [비활성].
- **관측은 "공통" 이지 "완전" 이 아니다** (r2 정정 — 초안이 여기서 다시 혼동했다).
  모든 에이전트가 같은 벡터를 받는다는 사실은 그 벡터가 **세계 상태 전체**라는 뜻이
  아니다. 실제로 임무 기하(§3.1 핵심 2)와 평가자 전용 정보(부록 B 말미)는 관측 밖이다.
  따라서 이 문서로 인정되는 것은 **"공통 관측을 제공한다"** 까지이며,
  **"centralized critic 이 추가로 볼 것이 없다" 거나 "CTDE 의 이점이 없다" 는 결론으로
  나아갈 수 없다.** 학습 구조의 이점 유무는 이 설명서가 답할 문제가 아니다.

### 3.5 공격자에게 주어지는 정보

`env_adv._gather()` 가 매 틱 넘기는 것: 공격자 자기 (p, v) · 보호 자산 좌표 ·
예측 net_center (= p_att + v_att·τ₀) · finisher 위치 · **전 limiter 위치** ·
kill_radius · 자기 능력 한계 · dt · **`committed` 비트 (FSM 이 DEPLOYING/LOCKED 인가)** ·
경과시간 t · jink 위상.

- `sense_range = 30 m` 는 **route 항에만** 적용되는 limiter 감지 반경이다
  (`attacker_ladder.py:208`). 회랑 기하상 최대 거리 ≈ 20.6 m (실측 365 tick max 19.02 m)
  이므로 **limiter 가 살아 있는 동안에는 구속하지 않는다.**
  **단 이것은 교차검증에서 정정됐다**: limiter 가 소모되면 `PARK_POSITION = (0,0,60)` 으로
  텔레포트되고 **그 좌표가 필터 없이 공격자에게 전달**된다. 주차점은 전방 조건
  `(c − p)·f̂ > 0` 을 통과하므로 **오직 `sense_range` 가 그 인공물을 가린다.**
  즉 retire 가 한 번이라도 일어나면 이 반경은 route 기하를 바꾸는 **load-bearing 필터**다
  (`sense = ∞` 면 arcsin(0.75/63) ≈ 0.012 rad 의 가짜 blockage 가 추가되어 1e-9 수준
  양자화 argmax 를 뒤집을 수 있다).
- 공격자는 **finisher 의 발사 여부(`committed`)를 즉시 안다.** 이는 "물리적 커밋의
  관측" 으로 선언된 채널이지 전략적 신호가 아니다 (`adversary.py` docstring).

---

## §4. 시간과 사건

### 4.1 "한 스텝" 안에서 일어나는 일의 순서

`ModeSystemEnv.step(actions)` 한 번 = 0.05 s. 순서는 **고정**이다.

| 순서 | 하는 일 | 위치 |
|---|---|---|
| 1 | `_step_i += 1` (**1-based**) | `env_sys.py:340` |
| 2 | limiter 커밋 제안 수집 (idx3 > 0.5) | `env_sys.py:345-356` |
| 3 | 커밋 기하를 **제안 시점 상태로 동결** → `CommitRecord(resolve_step = now + n_kill)` | `env_sys.py:358-371` |
| 4 | (옵션) 강제 커밋 개입 — B2 primary 에서는 off | `env_sys.py:373-392` |
| 5 | **`inner.step()` 진입** — 아래 5a~5h | `env_sys.py:395` |
| 5a | **이동 전** 상태로 도달집합 표본 생성 + v_shot 계산 (full · hold 기준 · COMA 반사실) | `env.py:266-289` |
| 5b | FIRE 게이트 판정 및 FSM 1틱 전진 | `env.py:295-311` |
| 5c | fire_event 이면 **포획 값 동결**: `(¬boxed_in) ∧ (v_shot_worst ≥ 1)` | `env.py:312-320` |
| 5d | 공격자 행동 계산 (프록시가 A2 로 교체) | `env.py:334-341` → `env_adv.py:88` |
| 5e | **백엔드 전진** (v ← clip(v + a·dt), p ← p + v·dt, e ← slew) | `analytic.py` |
| 5f | **이동 후** 침투 판정 · SPENT_FAIL 판정 · 종료 플래그 | `env.py:346-352` |
| 5g | `limiter_loss` = **이동 전** 상태에서 kill_radius 안의 limiter 수 | `env.py:354-355` |
| 5h | 보상 J 계산 · **이동 후** 상태로 관측 재계산 | `env.py:357-391` |
| 6 | net-miss handoff: `miss_terminates=False` 이므로 spent-fail 종료만 억제하고 `net_spent_step` 기록 | `env_sys.py:400-418` |
| 7 | 만료된 커밋 해소: **NK 거부권 → 기하 → Bernoulli(p_kill)** | `env_sys.py:455-` |
| 8 | 접촉 event resolver: **이동 전/후 선분의 최소거리**가 r_contact 이하면 같은 사슬 | `env_sys.py:543-590` |
| 9 | 결과 라벨 · 보상 terminal 적용 | `env_sys.py:590-618` |

> **주의해야 할 비대칭**: 계약의 contact 술어 (§7.2) 는 **이동 전 점 상태**를 보고,
> env 의 engagement resolver 는 **이동 전·후를 잇는 선분**을 본다. 두 술어는 같은
> 반경 0.75 m 를 쓰지만 **같은 사건 집합을 만들지 않는다.** 실측 반례:
> pre 0.764 m > 0.75 > post 0.501 m — resolver 만 접촉을 본다
> (`temp_research_note/2026-09-14c §3`). 이 비대칭이 partition 을 조용히 틀리게 할
> 뻔했고, 그래서 `partition_bin` 이 **세 소스**를 함께 본다.

#### ⚠ 이 비대칭은 **검사한 표본에서 계약 술어가 관측되지 않는** 형태로 나타난다

**계약의 권위 술어(이동 전 점 스캔)는 실측에서 사실상 발동하지 않는다.**

| 실측 | 표본 | `first_contact_t` (계약 술어) | `first_engage_t` (resolver) |
|---|---|---|---|
| 본 문서 작성 중 직접 실행 | SOLO arm 60 ep (12 cell × 5) | **0** | **2** |
| 교차검증 에이전트 | 100 ep | **0** | HARD_KILL 8 건 전부 |

원인은 이산화다. 본 실행에서 `v_att + v_lim` 상한은 **33.59 m/s** 이고
× dt 0.05 s = **1.679 m** 인 반면 kill 구의 지름은 2 × 0.75 = **1.5 m** 다. 즉
**공격자가 틱 사이로 구를 통과(tunneling)** 한다. 점 샘플링 술어는 원리적으로 이 사건을
볼 수 없다.

재현:

```
# 60 ep, SOLO arm → first_contact_t not None: 0 / first_engage_t not None: 2
# bins {'N': 38, 'F_other': 22}, labels {'NET_CAPTURE': 38, 'PENETRATED': 22}
```

**귀결 — 반드시 분리해 써야 한다**:

| | 계약 술어 | 실효 판정자 |
|---|---|---|
| 정의 | `‖p_att − p_lim‖ ≤ kill_radius`, **이동 전 점** | `_seg_min_dist(pre, post) ≤ r_contact`, **swept 선분** |
| 봉인 지위 | `docs/94 §2-7` 이 **"단일 정의원"** 으로 봉인 | 계약 문안에 없음 |
| 실측 발동 | **0 / 100 ep** | HARD_KILL 8/8 |

**정확한 범위 (r2)**: 말할 수 있는 것은 **"검사한 표본(60 + 100 ep)에서 계약 술어의
발동이 관측되지 않았고, 실효 판정은 swept resolver 가 했다"** 까지다. 이산화 논거는
그것이 **우연이 아닐 가능성**을 설명하지만, 전 격자·전 arm 에서 항상 0 이라는 것을
증명하지는 않는다 (특히 limiter 가 움직이는 arm 은 미측정).

그 범위에서 남는 실무적 귀결은 분명하다: **`H_illegal` 계수를 봉인 문안만 보고
재현하려 하면 관측된 접촉을 놓친다.** `partition_bin` 이 세 소스를 보는 것은 편의가
아니라 그래서이며, 이 이탈은 `docs/94` · `docs/102` 에 amendment 로 등재되지 않았다
(§11.3 U-11).

### 4.2 시간 상수

| 양 | 값 | 틱 | 지위 | 무차원군 |
|---|---|---|---|---|
| `dt_phys` = `Δt_dec` | 0.05 s | 1 | **(규약)** — 수치 적분 격자이자 판단 주기. **둘이 결합 고정** | `q_dec = 1/6` (pinned) |
| `τ₀` ≡ `τ_deploy` | 0.30 s | 6 | **(문헌)** 분해 선언 = flight 0.15 (Xu 2025 Fig.6) + sense 0.10 (Pliska RA-L, LiDAR 10 Hz) + decide 0.05 | χ, η 의 τ |
| `τ_lock` | 0.10 s | 2 | **(규약)** outcome 적용 지연 + 침투 race 창 | `q_race = 1/3` (contract-fixed) |
| `τ_kill` | 0.15 s | 3 | **(문헌)** sense+decide 사슬 재사용 | `q_kill = 1/2` (contract-fixed) |
| `W_net` | ≡ τ_lock | 2 | **vacuous** — 포획 수명의 인과 채널이 이 세계에 없다 | ω_net 승격 안 함 |
| horizon | 8.0 s | 160 | **(규약)** 부기 파라미터 — 물리 주장 아님 | — |

세 비율은 `r2a_lattice._inject` 에서 τ 와 **함께 co-scale** 되어 구조적으로 고정된다.
새 좌표가 아니라 **고정 conditioning** 이다.

### 4.3 τ₀ 는 무엇의 지연이고, 무엇의 지연이 아닌가 — 정면 답변

**τ₀ 는 실제 물리 지연 전체를 대표하지 않는다.** 세 값을 항상 함께 적는다.

| 구간 | 값 |
|---|---|
| viability / deployment scale | **τ₀ = 0.30 s** |
| 추가 적용 + race 지연 | `q_race·τ₀` = **0.10 s** |
| **FIRE → 결과 확정까지 총 pending** | **(1 + q_race)·τ₀ = 0.40 s (8 틱)** |

**분해 3 항 중 무엇이 실현되고 무엇이 안 되는가** (교차검증으로 좁힌 결과 — 초안이
"분해 전체가 미실현" 쪽으로 읽힐 수 있어 정정한다):

**용어를 먼저 분리한다 (r2 정정)**: 타이머가 있다는 것은 **시간 지연을 대리하는 규약이
구현됐다**는 뜻이다. 그것만으로 **해당 물리 현상이 실현됐다**고 쓰면 안 된다. 아래 표의
"구현" 열은 전자만을 뜻한다.

| 항 | 값 | 지연으로서 구현됐는가 | 대응 물리 현상이 모델에 있는가 |
|---|---|---|---|
| `flight` | 0.15 s | **예** — 발사 후 FSM 타이머로 구현 | **아니다.** 비행하는 그물 객체·탄도·전개 형상이 없다. 타이머는 그 비행시간을 **대리**한다 |
| `sense` | 0.10 s | **아니다.** 관측이 당 틱 참값이라 대응 기제가 없다 (§3.4) | 아니다 |
| `decide` | 0.05 s | **예, 단 이중 계상.** scripted clean 트리거가 직전 틱 info(`prev_clean`)를 쓰므로 1 틱 결정 지연이 별도로 존재 (실측: 임계 통과 t=21, 발사 t=22) | 해당 없음 (판단 주기) |

**따라서 정확한 문장은 세 가지다**: ① 지연으로서 **구현되지 않은** 항은 `sense` 0.10
하나다. ② `flight` 0.15 는 **타이머 규약으로 구현**됐을 뿐 그물의 비행이 모사된 것은
아니다. ③ "sensing 성분을 분해했다" 는 여전히 **금지**다.

**τ₀ 에 들어 있지 않은 것**:

- actuator lag — 노브 자체가 없다 (`analytic.py`: 명령 가속 즉시 적용).
- 통신 지연 · 처리 지연 · 관측 잡음 — 없음.
- 정책의 의도적 WAIT — **지연이 아니다.** 기다린 시간은 latency 에 산입하지 않는다.
- τ_kill (0.15 s) — 이것은 **limiter kinetic 경로**의 지연이며 net 지연과 별개 사슬이다.
  게다가 접촉 resolver 경로는 **즉시 해소**되어 τ_kill 을 겪지 않는다 — 그리고 §4.1 에
  따르면 하드킬은 사실상 그 즉시 경로로만 일어난다.
- **τ_slew 는 "제외" 가 아니다.** `m4_config.TAU_OMITTED` 가 slew 를 제외 항으로 적었지만,
  판정자가 `se3_cone` 이라 **지향축 slew (ω = 2.0 rad/s) 가 포획 성립에 직접 구속**한다
  (실측: hold 배치 0.0% 구속, ring 배치 **44.8% 구속**). 지연 목록에서 빠졌을 뿐
  세계에서 빠진 것이 아니다.

**정본 claim 형식 (이 형식으로만 쓴다)**:

> For the sealed reduced-order world at fixed temporal-resolution conditioning
> q_dec = 1/6 and fixed timer ratios (q_race = 1/3, q_kill = 1/2), the net-capture
> boundary is characterized in (χ, η, λ).

**해석 금지 3종** (`docs/94 §1.2` 봉인): ① q_dec 1/6→1/12 의 χ50 ≈ +0.15 는
temporal-resolution conditioning 이지 "판단 주기의 인과 효과" 가 아니다 (cadence 와
수치 해상도가 동시에 이동). ② τ₀ → 0 은 **특이(singular) 순간효과기 극한**이며 매끄러운
외삽 대상이 아니다. ③ 관측 지연 성분이 없으므로 어떤 결과도 "sensing 분해" 로 주장 금지.

### 4.4 대표 에피소드 하나의 시간선

셀 `r00c0` (χ 0.56, η 2.1, λ 4.644), SOLO arm 기준의 전형적 진행. 틱 = 0.05 s.

```
t=0.00 (틱 0)   reset. 공격자 p≈(25.5, −0.9, 2.3), v≈(−12.4, +0.4, −1.1) [스폰 지터 반영]
                limiter 4 기 x=8 링 (반경 5 m), finisher (2,0,0) 정지, 자산 원점
                관측 65 차원 산출 (이동 전 상태 기준의 v_shot 포함)
   ↓ 매 틱: 도달집합 2000×4 segment 표본 → v_shot_(soft|worst) 재계산
   ↓         공격자 = 전방 P-드라이브 + jink(진폭 0.6·a_lat, 1.5 Hz) + route 편향(0.5)
   ↓                  + kill_radius 1.0 배 안에서 강한 반발
t≈1.0~2.5       공격자가 cone 축 밴드 [0, 8.22] m 안으로 진입. v_shot_soft 상승
t=t_F           `v_shot_soft ≥ 0.9` ∧ fire_cmd=1  →  **FIRE (비가역)**
                · k: 1 → 0, 상태 LOADED → DEPLOYING
                · CommitMeta 동결 (t_fire, p_F, v_F, e_net, net_center, v_shot_at_commit)
                · **포획 값 동결**: pending_capture = (¬boxed_in) ∧ (v_shot_worst ≥ 1)
t_F + 0.30 s    (6 틱) DEPLOYING → LOCKED
   ↓            이 창 동안 **매 틱 침투가 검사되고 capture 는 구조적으로 False**
   ↓            → 침투가 자명하게 이긴다 (F2 race)
t_F + 0.40 s    (8 틱) LOCKED 만료 = **해소 틱**
                · pending_capture=True  → CAPTURED → (contact 0 이면) **N**
                · False → SPENT → `miss_terminates=False` 이므로 종료 억제,
                          `net_spent_step` 기록 → 다음 틱부터 **KINETIC**
KINETIC 이후     limiter 가 reference fallback (PN intercept + commit) 으로 전환 [미커밋]
                접촉/커밋 → NK 거부권(d_asset ≤ 6 m) → 기하 → Bernoulli(1.0) → HARD_KILL
종료             capture | penetration(자산 1 m 이내) | hard_kill | t = 160 틱 절단
```

### 4.5 사건 규약표 — 같은 틱에 두 사건이 일어날 때

**이 표의 모든 행은 (규약) 이다. 연속시간 물리 순서를 주장하지 않는다.**

| # | 동시 발생 | 판정 | 코드 근거 |
|---|---|---|---|
| ① | 포획 해소 ∧ body contact | **H_illegal 우선** (clean 정의상 포획 실패) | `partition_bin` [미커밋] |
| ② | NET_SPENT ∧ 같은 틱 capture | **N 우선** | FSM 해소 순서 |
| ③ | NET_SPENT 확정 틱의 limiter contact | **KINETIC 은 다음 control tick 부터** | off-by-one 차단 |
| ④ | 포획 해소 ∧ 침투 동시 | **CAPTURE 우선 — sealed discrete-time tie rule** | `mission_rollout.py:361-372` 라벨 사슬 `hard_kill → captured → penetrated` |

- ④ 의 **동시발생 빈도(`capture_penetration_same_tick`)는 로그하되 precedence 결정에
  쓰지 않는다.** 빈도가 크면 규칙을 바꾸는 것이 아니라 dt 민감도 문제로 다룬다.
- `hard_kill` 이 라벨 사슬 최상단이므로 `hard_kill ∧ captured` 동시 = HARD_KILL 이다.
- `env_sys` 의 "침투 우선" 조항은 sham-net (`capture_terminates=False`) 전용이며 [비활성].

### 4.6 종료 이후에 계산되지 않는 것

- 종료 틱 이후 물리 적분·관측·보상 계산이 없다 (`env.py:409`: `self.agents = []`).
- `miss_terminates=False` 는 **spent-fail 종료만** 억제한다. capture · penetration ·
  hard_kill 종료는 **절대 억제하지 않는다.** 지평선 절단은 래퍼가 낸다.
- 학습 층에서는 별도로 **NET_FAIL 에서 RL credit 을 끊어야** 한다 (GAE/return terminal
  처리). 이는 `SystemSpec` 플래그로 구현하면 manifest hash 가 갈리므로 **training
  wrapper 계층**의 일이다 — **현재 미구현** [문서만] (§11.3 U-5).

---

## §5. 물리 표현과 생략

> "3DOF 라 단순하다" 는 이 절의 답이 아니다. 아래는 **무엇이 계산되고 무엇이 계산되지
> 않으며 어떤 주장이 거기 의존하는가**의 목록이다. 현실성에 단일 점수를 매기지 않는다.

### 5.1 계산되는 것 — 표현–생략–주장 대응표

| 구성요소 | 실제 표현하는 현상 | 생략·축약한 현상 | 지위 | 영향받는 주장 |
|---|---|---|---|---|
| **병진 동역학** | `v ← clip(v + a_cmd·dt, v_max)`, `p ← p + v·dt`. semi-implicit Euler. 가속 크기만 `‖a‖ ≤ a_max` 로 clamp | 질량·추력·항력·공력·중력·바람. **가속 방향이 한 틱에 임의로 회전한다** | **(규약)** | 모든 결과. airframe realizability 는 이 모델 밖 (`docs/93`) |
| **자세** | 단위 지향축 `e` 하나. `omega_max`(finisher 2.0, limiter 2.5, adversary 10.0 rad/s) 로 대원(great-circle) 율제한 slew | 각속도 상태(p,q,r)·모멘트·관성·자세→가속 사상·롤 동역학 | **(규약)** | finisher pointing 이 구속 조건이 되는 결과 (docs/45: ring 에서 44.8% 구속) |
| **net (그물)** | **물체가 없다.** τ_deploy·τ_lock 은 FSM 타이머, 포획은 fire 틱에 동결된 도달집합 술어 | 그물 탄도 비행 · 전개 형상 · 개방 면적의 시간 변화 · 얽힘 · 관통 | **(규약)** — 상류 면적만 (실측) | "net 이 물리적으로 실현돼 있다" 는 **단독 표현 금지** (docs/94) |
| **포획 판정 (se3_cone)** | finisher 정점에서 지향축 방향 원뿔: 반각 0.2121 rad, 축방향 밴드 [0, 8.22] m. 공격자 τ-도달집합의 **모든** 실현가능 종점이 원뿔 안이면 포획 | 그물이 실제 그 원뿔을 채우는지 | 반각·R_max = **(실측 유도)**, 원뿔 근사 = **(규약)** | χ50 경계 전체. §8 A1 이 이 사슬의 단일 실패점 |
| **도달집합** | `n_segments = 4` 이므로 **union 경로**를 탄다: 단일세그먼트 블록(`n_samples = 2000`) ∪ 경계구 32 방향 ∪ bang-bang dogleg ∪ turn-curve. **실측 실현가능 witness 중앙값 2504.** 매 스텝 계산되는 `reachable_accels(2000)` 는 union 분기에서 **소비되지 않는다** (순수 낭비) | 실제 폐루프 재계획 · 속도 한계 결합. **그리고 연속 도달집합의 표본화되지 않은 부분** | **(규약)** | **보장의 대상은 표본 집합이다** — 아래 참조. 표본 인공물 논의는 2000 이 아니라 **2504-witness union 위**에서 해야 한다 |
| **kinetic 교전** | contact/commit → **no-kinetic zone 거부권** (`d_asset ≤ 6 m` → 기폭 보류, limiter 미소모) → 기하 → `Bernoulli(p_kill = 1.0)` | 폭발 물리 · 파편 · 파괴 반경 분포 · 실제 충돌 | 반경 0.75 m = **(실측 유도)**, `p_kill = 1.0` = **(규약, 선언된 sweep 축)** | H_fb · H_illegal · P_U 전부 |
| **접촉 반경 세 종** | `r_shape` = 0.75 (도달집합 no-go), `r_commit` = 0.75, `r_contact` = 0.75 | 셋이 의미가 다른데 **현재 값이 같다** (분리는 배선만 돼 있고 수치 보정 미실시) | **(규약)** | 하드킬이 커밋 경로가 아니라 **접촉 resolver 에 지배됨** (registry C033) |
| **소진 limiter** | `PARK_POSITION = (0,0,60)` 으로 주차 | 실제 소멸/추락 | **(규약)** | 관측 정규화 붕괴를 막기 위한 선택 — 근거가 코드에 명시됨 (`env_sys.py`) |
| **회랑 기하** | 자산 원점, 반경 1 m 침투 · limiter 링 x=8 반경 5 · finisher (2,0,0) · 공격자 x≈24 스폰 | 지면 · 장애물 · 건물 · 고도 제한 | **(규약)** | legacy 24 m 회랑 한정 — 전 결과의 조건 |
| **공격자 수** | 1 | 다수·편대·포화 공격 | **(규약)** | 자원 교환 경제 주장 전부 (이 모델에 없음) |
| **탄약** | K = 1 단발 | 재장전 · 다발 | **(규약)** | K ≥ 2 는 계약 밖 |

#### 보장의 대상은 표본 집합이다 (r2 정정 — 초안의 과잉 주장)

초안은 "과대근사이므로 포획 판정은 보수적" 이라고 썼다. **이 결론은 근거보다 강하다.**
두 단계를 구분해야 한다.

| 단계 | 하는 일 | 이 단계가 주는 것 |
|---|---|---|
| ① 집합 수준 과대근사 | 단일세그먼트 볼 ∪ 경계구 32 방향 ∪ bang-bang dogleg ∪ turn-curve | 참 도달집합보다 **넓은 후보 집합** |
| ② 유한 표본화 | 그 합집합에서 유한 표본 추출 (실현가능 witness 중앙값 2504) | **그 표본에 대한 진술** |

`v_shot_worst = 1` 은 **②의 표본 전부가 원뿔 안**이라는 뜻이다. ①이 넓다는 사실은
**표본되지 않은 점이 원뿔 밖에 있을 가능성을 배제하지 않는다.** 즉 —

- **말할 수 있다**: "검사한 witness 집합 안에서는 탈출이 없었다."
- **말할 수 없다**: "포획 판정은 보수적이다" · "모든 실현가능 탈출이 포획된다" ·
  "거짓 양성이 없다."

연속 집합 전체에 대한 포함 증명(예: Lipschitz 상수 + 격자 간격에 기반한 covering 논법,
또는 구간 산술 인증)은 **이 문서에도 리포에도 없다.** `margin_audit` 이 유한 witness 하에서
`m_cap` 이 참 마진을 **과대추정**한다고 적은 것이 바로 이 문제의 한 단면이다 (§10.3).

> **따라서 §5.1 의 해당 행은 "(규약, 보수적)" 이 아니라 "(규약)" 이며, 보수성은
> **주장이 아니라 미확인 항목**이다 (§11.3 U-19).

### 5.2 명시적 부재 — grep 으로 확인한 것

아래는 **코드에 없음을 확인**한 항목이다. 있다고 오해되기 쉬운 것만 적는다.

| 부재 항목 | 확인 근거 | 왜 부재인가 | 무엇을 주장할 수 없게 되는가 |
|---|---|---|---|
| 센서 잡음 | `obs_threat` · `env_adv` · `env` 전수 (docs/94 §1.3) | 구현 결정 — 층3(W10) 이월 | 잡음 하 강건성 |
| 측정 지연 / 측정 나이 | 〃 | 〃 | τ₀ 의 sense 성분이 **실현되지 않음** (§4.3) |
| 1차 actuator lag | `analytic.py:109-131` — a_max clamp + v_max clip + heading slew 뿐 | 노브 자체가 없음 | 구동기 대역폭 관련 결론 |
| 통신 지연·손실 | 전 코드 | 중앙집중 관측 세계 | 분산 통신 하 협력 |
| 표적 오분류 | `obs_threat` 가 참값 주입 | 이상화 선언 | 분류 오차 하 성능 |
| 강체 충돌 물리 | 백엔드에 충돌 없음 (docs/57 판정 B) | "contact" 는 **근접 kinetic engagement opportunity** 이지 물리 충돌이 아님 | "실제로 부딪혔다" |
| net 지속 물리 | `W_net` vacuous 판정 (docs/94 §2-4) | 포획이 fire 시점 단일 술어라 "포획 가능 상태가 유지되는 시간" 이라는 물리가 없음 | ω_net 을 좌표로 승격 |
| self-play 공격자 | `attacker_ladder` 는 전부 스크립트 | 이번 학기 제외 | best-response 하 강건성 |

**층1 민감도 screen 의 결론 (정확한 문장만 인용 가능)** — `docs/94 §1.4`:

> Layer-1 physical/environment sensitivity audit completed with **no clean executable
> perturbation candidate** under the current simulator architecture.

**금지 표현**: "추가 민감성 없음" · "robustness demonstrated" · "민감도 검증 완료".
정확한 문장은 **"clean candidate 없음으로 pre-B0 sensitivity screen 종료"** 뿐이다.

---

## §6. 상대 행동과 실험 모집단

### 6.1 A2-nominal 의 정확한 구조

공격자는 **고정 규칙**이다. 학습하지 않고, 에피소드 간 갱신되지 않는다
(`agents/attacker_ladder.py`, `agents/adversary.py`). A2-nominal 의 가속 명령은
다음 항의 합을 `‖a‖ ≤ a_att_max` 로 clamp 한 것이다.

| 항 | 식 / 규칙 | 파라미터 | 반응 대상 |
|---|---|---|---|
| **전방 구동** | `a_fwd = k_f·(v_nominal − v·f̂)·f̂`, f̂ = 자산 방향 | `k_f = 4.0` 1/s | 자산 위치 (고정) |
| **jink (지속 횡진동)** | 진폭 `0.6·a_lat_max`, 주파수 1.5 Hz, 위상 = SHA-256(seed, episode) | `jink_amp 0.6` | **아무것도 반응하지 않음 — 개루프 시간함수** |
| **jink 종말 게이트** | `d_target ≤ 3.0 m` 이면 jink 중단 | `jink_terminal_r 3.0` | 자산 거리 |
| **route (각도-간극 편향)** | limiter 배치의 angular gap 을 골라 그쪽으로 횡가속 | `route_gain 0.5`, `sense_range 30 m` | **limiter 위치** |
| **dodge (커밋 후 회피)** | `committed` 이면 net_center 반대 방향 횡가속 `1.8·a_lat_max`. **커밋 전에는 0** | `amp 1.8` | **FIRE 여부** |
| **repel (강한 반발)** | limiter kill_radius 의 1.0 배 안이면 최대가속으로 밀어냄 | `repel_margin 1.0` | limiter 근접 |
| **homing** | 횡속도 감쇠 = 회피 후 시선축 복귀 | `homing_gain 4.0` 1/s | 자기 속도 |

**결정론성**: 위 전부가 결정론적이다. 유일한 난수 소비는 **에피소드 시작 시 jink 위상**
(SHA-256 유도) 과 스폰 지터다. 같은 seed → 같은 궤적. `AttackerSpec` 은 frozen
dataclass 이고 에피소드 내·간 갱신 경로가 없다.

**⚠ dodge 항의 기전에 관한 정정 (교차검증 신규 발견)**: dodge 는 "net_center 반대 방향"
으로 정의돼 있으나, 이 세계에서 `net_center = p_att + v_att·τ₀` 이다. 따라서
`off = p_att − net_center = −v_att·τ₀` 이고, 이것을 `to_net` (= `net_center − p_att` 의
단위벡터) 방향 성분으로 사영해 빼면 **횡성분이 항등적으로 0** 이 된다 (실측 잔차 9e-16).
결과적으로 `dodge_dir` 은 fallback 인 `unit(f̂ × ẑ)` 로 **퇴화**한다.

> 즉 **"공격자가 그물을 피한다" 는 서술은 이 구현에서 성립하지 않는다.** 커밋 후 발생하는
> 것은 net 기하와 무관한 **고정 방향 횡가속**이다. `net_center` 는 여전히 live 값이지만
> (공격자 궤적을 바꾸므로), 그 값이 담고 있어야 할 **기하 정보는 전달되지 않는다.**

**route 항의 사각지대**: 유일한 defender-aware 채널인 route 는 `d_target ≤ 3.0 m`
(`jink_terminal_r`) 에서 **꺼진다.** 즉 종말 구간에서 공격자는 limiter 배치에 전혀
반응하지 않는다.

### 6.2 이 문서에서의 용어 정의 — 섞어 쓰지 않는다

| 용어 | 이 문서에서의 정의 | A2 가 이것인가 |
|---|---|---|
| **반응형 (reactive)** | 에피소드 내에서 상대의 **현재 상태**를 읽어 행동이 달라진다 | **예** — limiter 위치(route/repel)와 FIRE 비트(dodge)에 반응 |
| **적응형 (adaptive)** | 경험을 통해 **정책 자체가 갱신**된다 | **아니오** — 학습 코드 없음 |
| **최적 대응 (best-response)** | 방어자 정책에 대해 최적화된 상대 | **아니오** — 고정 규칙 |
| **강건함 (robust)** | 선언된 교란 집합 전체에서 결론이 유지됨 | **미확립** — A-family robustness 는 층3 |
| **일반화 (generalize)** | 학습에 쓰지 않은 분포에서도 성능 유지 | **미측정** — held-out 평가 없음 |

> **따라서**: A2 가 반응한다는 사실은 "이 반응이 현실 공격자의 보편적 행동 법칙" 이라는
> 뜻이 **전혀 아니다.** A2 는 **우리가 작성한 7 항 합의 고정 규칙**이며, 그 규칙의
> 계수(0.6 · 0.5 · 1.8 · 30 m) 는 §8 기준으로 **(규약)** 이다.

### 6.3 초기조건과 환경 분포

| 축 | 분포 | 근거 |
|---|---|---|
| 공격자 스폰 | 기준점 x≈24 m 에서 `dx = 2.0 m` 종방향 · `r_lat = 5.0 m` 횡방향 지터, 속도는 자산 방향 | `SpawnSpec(dx=2.0, r_lat=5.0)` |
| limiter 초기 배치 | x=8 평면의 반경 5 m 링 4 슬롯 (고정) | `train.layout.ring_*` |
| 위협 등급 (a, v) | **셀이 정한다** — `dims_from(χ, η, τ, ρ)` 로 역산한 결정값 + 셀 내부 지터 (χ ±0.01, η ±0.15) | `draw_cell_jitter` |
| jink 위상 | SHA-256(seed, episode) → [0, 2π) | `derive_phase` |
| 평가 격자 | **G = 14 행** = λ ∈ {4.644, 3.574} × η ∈ {2.1 … 3.9} (7). 행당 χ 4 점 `{χ_lo−0.04, χ_lo, χ_hi, χ_hi+0.04}` → **56 셀** | `docs/94 §2-10a`, `b2_manifest` |
| 표본 | 셀당 **n = 300 / seed**, **seed = 3**, arm 2 종, paired CRN → **100,800 ep** | `docs/102 §2.1` |

**중요**: `build_m4_env(randomize_threat=True)` 가 에피소드마다 위협을 뽑지만,
`resolve()` 의 `extra_cfg` 가 **그 draw 를 덮어쓴다** (a, v 및 비율 파생값 전부).
즉 위협은 **셀이 결정**하며 무작위 draw 는 실효가 없다 (`r2a_stage1.py:70` 주석
"★draw 파생값 덮어쓰기 (mu 보존)").

### 6.4 평가에서 제외되는 것

- **THREAT bracket 밖**: a ∉ [11, 78] m/s², v ∉ [8, 30] m/s. **bracket 은 구속하지 않는다**
  — 구속하는 것은 예산이다.
  **단 봉인 문서의 숫자는 틀렸다 (교차검증 신규 발견)**: `b0_v3_world_contract.json:104`
  과 `b0_v3.py:73-75` 가 "realized a 16.5..27.5" 라고 적었지만, 같은 파일의
  `grid.rows` (χ 0.38~0.66) 를 `dims_from(χ, η, τ, ρ)` 로 역산하면 실제 실현값은
  **a ∈ [14.95, 25.96]** (지터 포함 14.55~26.35) 이다. v 만 일치한다. 결재 ⑦ 이 χ base
  규칙을 대칭 `{lo−0.04, lo, hi, hi+0.04}` 로 바꾼 뒤 **문자열만 남은 것**으로 보인다.
  결론(bracket 이 구속하지 않음)은 유지되지만, **재현 불가능한 수치가 SEALED 문서에 박혀
  있고 어떤 테스트도 이를 검증하지 않는다** (§11.3 U-12).
- **기권(NO FIRE)은 제외가 아니라 실패다.** `P(N)` 의 분모에 남는다.
  **censoring 보정 금지** (`docs/94` 과학 층).
- **격자 밖으로 잘린 χ50**: 사전등록된 확장 규칙(방향당 ±0.04, 최대 2회) 후에도
  censored 이면 **one-sided bound 로 보고**한다. 확장 trigger 는 **오직 censoring**
  이며 "효과가 커 보여서" 확장하는 것은 금지된다.
- **secondary `S_C` replay set** (R2b 재생, R_rec 전용) 은 primary 와 **혼합 금지**.

### 6.5 현재 결과가 어떤 모집단에 대한 결과인가 — 한 문장

> 현재의 모든 수치는 **legacy 24 m 회랑의 봉인된 축소차수 3DOF 세계에서, 단일
> A2-nominal 스크립트 공격자 1 기에 대해, q_dec = 1/6 과 고정 타이머 비율 아래,
> capability-ratio 족(μ = 0.35, ν = 1.00)으로 방어자 능력이 위협에 연동된 채,
> (χ, η, λ) 격자 위에서 얻은 결과**이며, 그 밖의 어떤 모집단에 대해서도 진술하지 않는다.

---

## §7. 학습 신호 · 결과 판정 · 보고 지표 · 진단량

### 7.1 네 층은 서로 다른 것이다

| 층 | 무엇인가 | 어디에 있는가 | 현재 상태 |
|---|---|---|---|
| **학습 신호** | 정책 경사에 들어가는 스칼라 | `env.py:357` + `env_sys.py:501-513` | **계산됨** (`RewardSpec.enabled=True`) — 단 B2 는 스크립트 arm 이라 **소비자가 없다** |
| **결과 판정** | 에피소드가 어느 bin 인가 | `mission_rollout.partition_bin` [미커밋] | 4분할 N / H_fb / H_illegal / F_other |
| **보고 지표** | 논문에 싣는 수 | `b2_readout.py` [미커밋] | P(N) · P(FIRE) · P(N\|FIRE) · P(H_illegal) · P_U · χ50 · Δχ50 |
| **진단량** | 사후 설명 전용 | telemetry · `veto_events` · `capture_penetration_same_tick` · forced-fire | **성능으로 보고 금지** |

**학습 objective 로 과학 층과 시스템 층을 합산하는 것은 금지된다** (`docs/94 §2-9`).

### 7.2 "포획 성공" 술어가 코드에 **네 개** 있다

이것은 결함 보고가 아니라 **이 세계의 사실**이며, 어떤 수를 읽을 때 어느 술어인지
모르면 그 수를 잘못 읽게 된다.

| # | 위치 | 판정 방식 | B0 v3 지위 |
|---|---|---|---|
| **권위** | `mission_rollout` label (`:384`) | CAPTURED ∧ **에피소드 누적** contact = ∅ | **N 의 정의.** R2a/R2b 가 쓴 술어 |
| 사본 1 | `env_sys._outcome_label` (`:590-618`) | 같은 사슬이나 contact 을 **종료 틱에서만** 검사 | **N 판정에 사용 금지** — 초기 접촉 후 종료 틱에 떨어져 있으면 NET_CAPTURE 로 읽는다. **그런데 보상 라벨은 이것을 쓴다** (`env_sys.py:504`) |
| 사본 2 | `RewardSpec.terminal` (`:197-211`) | `CAPTURE_WITH_CONTACT` 에 **NET_CAPTURE 와 같은 +b_net** | docs/94 결재 ④ 가 supersede 선언 — **코드 미반영** [충돌] |
| 사본 3 | `m4_env.label_rates` | `p_net` = NET_CAPTURE **+** CAPTURE_WITH_CONTACT | legacy 2층 지표 — **과학 지표 아님** |

**결과**: 현재 배선에서 MARL 을 돌리면 **정책은 illegal substitution 에 clean capture 와
같은 보상을 받는다.** 이는 가정이 아니라 지금의 코드다 (`RewardSpec.enabled=True` +
사본 2). B0 v3 가 막으려던 실패 모드를 보상이 사준다. **stop rule 통과 전 MARL 금지
조항이 현재 이 위험을 실질적으로 차단하고 있다** (§11.3 U-4).

**NET_CAPTURE 가 뜻하지 않는 것**: 이 술어는 fire 틱에 동결된 **도달집합 기하 조건**이다.
그물이 실제로 기체에 닿았다거나, 기체가 손상되었다거나, 기체가 안전하게 회수되었다는
관측은 이 세계에 **존재하지 않는다.**

그리고 N = 1 의 정확한 뜻은 **"그 순간 공격자의 *표본된* 실현가능 회피 종점 전부가
finisher 의 원뿔 안에 있었다"** 다 — "모든 실현가능 종점" 이 아니다 (§5.1 의 보장 범위).

### 7.3 보상 함수 전수

**층 1 — env 조밀 보상** (`env.py:357-359`), 전 방어자 공통, 공격자는 `−J`:

```
J_env = Δv_shot_headline
      + λ1 · 1[clean threshold crossed]        λ1 = 1.0
      − λ2 · (이번 틱 낭비 발사 증분)            λ2 = 1.0
      − λ3 · (이동 전 kill_radius 안 limiter 수)  λ3 = 0.5
```

`Δv_shot_headline` = 현 배치의 `v_shot_soft` − **hold_position 기준 배치**의 `v_shot_soft`
(같은 도달집합 표본, CRN 상쇄). limiter 개별 credit 은 `coma_D_i` = 자신만 hold 로
바꿨을 때의 차분 — **info 로 노출되며 보상에는 들어가지 않는다.**

**층 2 — M4 terminal** (`env_sys.py:501-513`), `enabled=True`:

```
J_M4 = 1.0·J_env + 1.0·TERMINAL(label) − 0.1·(이번 틱 새로 소모된 limiter 수)
```

| label | TERMINAL | 비고 |
|---|---|---|
| `NET_CAPTURE` | **+1.0** | |
| `CAPTURE_WITH_CONTACT` | **+1.0** | ⚠ docs/94 결재 ④ 가 supersede 했으나 코드 미반영 |
| `HARD_KILL` | **+0.5** | `b_net·(1 − w_kill)`, `w_kill = 0.5` (**선언된 sweep 축**) |
| `PENETRATED` | −1.0 | |
| `TRUNCATED` | −1.0 | 지평선 미격퇴 = 보상상 실패 |
| `SPENT_FAIL` | 0.0 | 의미 감사 전까지 중립 |

- `label` 은 **사본 1** 로 계산된다 — 즉 보상이 쓰는 라벨과 과학 지표가 쓰는 라벨이
  **다른 술어**다. 이 divergence 는 비준된 것이며 `tests/test_terminal_truth_table.py::test_row12`
  가 의도적으로 고정한다.
- **보상과 지표를 일부러 다르게 둔다**: 학습은 TRUNCATED 를 벌하지만 보고 지표는
  우측 절단으로 유지한다.

### 7.4 지표 해석표

각 지표에 **분모 · 조건부 · 제외 · 집계 단위**를 붙인다. 마지막 두 열이 이 표의 요점이다.

| 지표 | 분모 | 집계 단위 | **좋아지면 말할 수 있는 문장** | **그래도 말할 수 없는 문장** |
|---|---|---|---|---|
| **P(N)** | 셀의 전 에피소드 (기권 포함) | cell × seed | "이 셀에서 clean net capture 술어의 성립 빈도가 올랐다." | "포획 확률이 올랐다." (술어 ≠ 포획) · "경계가 밀렸다." (한 셀은 경계가 아니다) |
| **P(FIRE)** | 〃 | cell × seed | "정책이 admissible 영역 안에서 더 자주 쐈다." | "게이트가 완화됐다." (게이트는 고정 admissibility constraint) |
| **P(N\|FIRE)** | **발사한 에피소드만** | cell × seed | **"발사된 에피소드 집합에서 조건부 성공률이 높아졌다."** — 여기까지만 | **"발사 후 달성도가 개선됐다"** (인과 해석). 분모 집합의 **구성이 달라져도 이 값은 달라진다** — 정책이 어려운 판을 덜 쏘기만 해도 오른다. 또 "안 쏜 판도 좋아졌다" |
| **P(H_illegal)** | 전 에피소드 | cell × seed | "doctrine 위반(net 전 kinetic 접촉) 빈도." | "성공률" — **이것은 성공 지표가 아니다.** KILL 로 끝난 것과 NK veto 로 기폭 보류된 것을 **반드시 분해**해 보고 |
| **P_U = P_N + P_H_fb** | 전 에피소드 | cell × seed | "정당한 fallback 포함 총 무력화 빈도." | "MARL 진입 사유." — **P_U 는 primary pass 가 될 수 없다** (docs/89 §10) |
| **χ50(η, λ)** | 행 단위 isotonic fit | row × arm × seed | "이 행에서 p = 0.5 를 지나는 χ 위치." | 격자 밖으로 잘리면(censored) 값 자체가 없다 — one-sided bound |
| **Δχ50** | paired, 같은 CRN | row × seed → 다수결 | "사전등록 3조건(행 12/14 · slice 5/7 · 전역 CI 하한>0)을 통과하면 **경계를 밀었다**." | 조건 미통과 시 "밀리는 경향" 이라고 쓰는 것 |
| **R_rec** | `(p_learned − p_A)/(p_C − p_A)`, 같은 S_C | descriptive | "search benchmark 대비 학습 정책의 상대 위치." | **"상한의 몇 % 회수"** — p_C 는 upper bound 가 아니며 R_rec > 1 이 가능 |
| **v_shot_soft** | 실현가능 표본 | 틱 | "도달집합 중 포획되는 표본 비율." | **"포획 확률 0.9"** (registry C011 — 블록별 밀도 상이, 확률질량 가중 없음) |
| **coma_D_i** | — | 틱 | "limiter i 를 hold 로 바꿨을 때의 v_shot 차분." | "limiter i 의 기여도" — **커밋 차원에는 반사실 credit 이 없다** (배치 차원만) |

**이름이 비슷한데 다른 것을 재는 쌍** (혼용 시 오독):

| A | B | 차이 |
|---|---|---|
| `m4_env.label_rates` 의 `p_net` | 과학 층 `P(N)` | 전자는 CWC 를 **포함**한다. 후자는 CWC 를 H_illegal 로 뺀다 |
| `_outcome_label` 의 NET_CAPTURE | `mission_rollout` 의 NET_CAPTURE | 전자는 종료 틱 접촉만, 후자는 에피소드 누적 접촉 |
| `HARD_KILL` (라벨) | `H_fb` (bin) | 라벨은 phase 무관. bin 은 **NET_SPENT 이후**만 정당 |
| `p_C` (R2b C arm) | 상한 | **upper bound 아님** — "search-based attainment benchmark" |

### 7.5 θ_fire 게이트 — 학습되는 것과 학습되지 않는 것

> **Learned fire timing subject to a fixed admissibility gate.** 정책은 **고정된
> θ_fire-admissible 영역 안에서의 발사 시점**을 고른다. 게이트 자체를 배우지 않는다.
> `v_shot_soft < θ_fire` 인 상태에서는 정책이 FIRE 를 아무리 내도 **물리적으로 발사가
> 일어나지 않는다** (`finisher_fsm.step_fsm`).

- **금지 어휘**: "학습 컨트롤러가 기존 게이트의 censoring 을 해소/회수했다."
- 게이트 보수성이 궁금하면 그것은 학습 arm 이 아니라 **forced-fire micro-arm** 이
  답한다 — **진단 전용, primary 와 pooling 금지, 별도 예산 계정** (`docs/102 §5`).
- forced-fire 는 **오직 `v_shot_soft ≥ θ_fire` admissibility 술어 한 스텝만** 우회한다.
  궤적·제어기·공격자·포획 술어는 건드리지 않으며, `perfect_aim_at_commit = False` 가
  강제된다. 발사 시점 선택은 **완전히 기계적** (축방향 좌표가 cone band 중점에 가장
  가까운 틱, 동률이면 가장 이른 틱).
- **실행 전 경고**: smoke 60 판에서 `P(FIRE) = 1.000` 이었다. primary 에서도 같으면
  forced-fire 표본이 **0** 이 된다. 그 자체가 판독의 한 줄이며 (게이트 censoring 이
  원인이 아님 → attainability/controller-limited), **규칙은 바꾸지 않는다.**

---

## §8. 파라미터 출처 장부

### 8.1 저장소가 이미 쓰고 있는 출처 등급

`shepherd/params.py` 는 자체 STATUS 범례를 갖고 있고, 그것이 교수님이 요구한 구분과
거의 일치한다. 본 설명서는 그 범례를 그대로 쓰고 **매핑**만 밝힌다.

| params.py STATUS | 이 문서의 근거 지위 | 뜻 |
|---|---|---|
| `MEASURED` | (실측) | 외부 공표 수치에 앵커됨 (Xu et al. *Drones* 2025 9:190) |
| `DERIVED` | (실측 유도) | MEASURED 값에서 명시된 식으로 계산 |
| `CALIBRATED` | (실측 보정) | 측정에 한 번 맞춘 뒤 동결 |
| `ASSUMED` | **(규약)** 또는 (미확인) | 시나리오 가정 — **외부 근거 없음** |
| `TUNED` | **(규약)** | 데모/수렴용 손튜닝 — **명시적 비물리** |
| `RESERVED` | — | 계약에 있으나 의도적으로 무효 |
| `DEAD` | — | 코드가 받지만 **행동에 영향 없음** |

> **주의**: `ASSUMED` 가 압도적 다수다. 즉 **이 세계의 대부분의 상수는 "그럴듯하지만
> 외부 근거가 없는" 선언값**이다. params.py 자신이 그렇게 적고 있다
> (`"ASSUMED  scenario assumption -- plausible, NOT externally grounded (most of the
> M2 fixture)"`).

### 8.2 현 운용점의 핵심 상수 — 출처 추적 (전체 표는 부록 C)

부록 C 가 항목별 **값 · 단위 · 출처 · 선택 이유 · 검증 지위**를 담는다. 본문에서는
그 표에서 읽어내야 할 **세 가지 결론**만 §8.3~§8.5 에 적는다.

### 8.3 선언된 탐색 범위 ≠ 검증된 현실 범위

**엄격히 구분한다.**

> **⚠ 이 절 전체에 걸리는 상위 경고 (교차검증 신규 발견)**: 아래 "문헌에 실제로 나온 값"
> 열의 근거 문서 `docs/34` · `docs/35` · `docs/39` 는 **머리말에 "전 수치 = AI 추출
> DRAFT, 비준 전 논문 인용 금지"** 를 달고 있다. 그런데 `m4_config.M4_PROVENANCE` 는
> 같은 값들을 **"A6 / A7 선언"** 으로 확정 서술하고 코드에 반영했다. 즉 **"AI 가 PDF 에서
> 뽑았고 사람이 원문 대조를 아직 안 한 값"이 운용점으로 굳어 있다.**
> 또한 `tests/test_net_forward.py` 자신이 Xu 앵커를 **"calibration-anchored — an anchor,
> not independent evidence"** 라 적었고, hang time 1.853 s 재현은 **약 23% 과소예측**으로
> documented discrepancy 로 잠겨 있다.
>
> **따라서 아래 첫 행은 "문헌에 나온 값" 이 아니라 "문헌에서 뽑았다고 기록된 값 (사람 대조
> 미완)" 으로 읽어야 한다.** 논문 인용 전에 원문 대조가 필요하다 (§11.3 U-13).

| 구분 | 해당 항목 |
|---|---|
| **문헌에서 뽑았다고 기록된 값 (사람 원문 대조 미완 · AI 추출 DRAFT)** | `a_att` 하한 11 · `att_speed` 하한 8 · Pliska 비율 0.36/1.00 · 기체 선회율 2 rad/s · Xu `S_NP = 12.54 m²` · Xu 개방시간 0.13 s · LiDAR 10 Hz |
| **문헌을 참고해 우리가 선택한 값** | τ₀ = 0.30 (분해 합) · kill_radius 0.75 (기하 합성 중앙값) · ρ = 1.77 (최악방향 하향) · half_angle (유도) |
| **계산·구현 편의로 정한 값** | dt 0.05 · episode_len 160 · `PARK_POSITION` · `step_seed_multiplier` 100003 · n_samples 2000 |
| **탐색을 위해 선언한 범위** | `a_att` 상한 **78** · `att_speed` 상한 **30** · sweep 축 {kill_radius 0.6/0.75/0.9}, {omega_max 1.5/2/3}, {tau_kill 0.15/0.20}, {p_kill}, {w_kill} · χ/η/λ 격자 전체 |
| **현실에서 타당하다고 확인된 범위** | **없음.** 이 세계의 어떤 범위도 하드웨어 실측으로 검증된 바 없다 |

> **따라서 "THREAT bracket a ∈ [11, 78]" 을 "현실적 위협 범위" 라고 쓰면 안 된다.**
> 하한만 실측이고 상한은 선언이다. `m4_config.THREAT_PROVENANCE` 가 그렇게 적고 있다:
> *"문헌 표적은 전부 연구용 쿼드라 **하한만 준다.** 상한은 우리 선언이다."*

### 8.4 변경 이력 — 결과를 보고 바꾼 것이 있는가

| 시점 | 변경 | 이유 | 방향 |
|---|---|---|---|
| 2026-07-29 | τ_deploy 0.4 → 0.30 | **결과를 보고 바꿨다.** τ=0.15(비행시간만)로 두니 무개입 hold 가 12/12 를 잡아 조향 문제가 사라졌고, 원인이 τ 의 under-modeling 이라 판단해 분해 재선언 | ⚠ **self-serving 방향 (전제 복원)** — `m4_config` 가 이 위험을 스스로 명시하고, 방어 논리 3 가지를 적어 둠 |
| 2026-07-29 | kill_radius 2.0 → 0.75 | 기존 근거가 "no external grounding" | 하드킬 **약화** (불리한 방향) |
| 2026-07-29 | omega_max 3.14 → 2.0 | π 는 물리 근거 아님 | 방어자 **약화** |
| 2026-07-29 | a_lim 1.00 → 0.35 × a_att | Pliska 비율 | 방어자 **약화** |
| 2026-07-29 | 위협 점값 → 브래킷 랜덤화 | 점값 방어 불가 | 중립 |
| 2026-07-29 | episode_len 80 → 160 | TRUNCATED 43% 부기 산물 | 중립 (스폰 축소는 금지) |
| 2026-08-01 | terminal_scale 10.0 → 1.0 | 실측상 dense 항과 같은 자릿수 | 중립 |
| 2026-08-28 | cone clearance 법칙 `tan` → `sin` | 내접구 규약 정정 | 기존 수치 약 14% 낙관이었음 |
| 2026-09-13 | ρ 2.0 → 1.77 (A3 최악방향) | 등가면적 구 근사가 낙관 | 방어자 **약화** |

**규율**: 변경 대부분이 **우리에게 불리한 방향**이고 **결과 열람 전 선언**됐다.
예외는 τ_deploy 이며, 그 위험은 문서에 명시돼 있다. **이 예외를 숨기지 않는 것이
장부의 요점이다.**

### 8.5 출처 미확인 — 그대로 표시

| ID | 항목 | 무엇이 미확인인가 | 레버리지 |
|---|---|---|---|
| **A1** | Xu 유효면적의 **기준 시점/거리** | 논문 보고 면적이 "발사 후 20 m 병진 시점" 이라는 가정에 **근거가 없다**. 반증 가능성 실재: Xu 는 최대 면적을 t≈0.13 s 로 보고하는데 그때 병진은 6–11 m | **최대** — `rho_air` → `tau_deploy` → `range_max` → `half_angle` 이 한꺼번에 움직인다. **단일 실패점** |
| **A5** | 공격자 플랫폼 등급 | FPV 스펙시트 미확보 → `a_att` 상한 78 · `att_speed` 상한 30 이 선언 | 높음 |
| **A2** | 네트 전방 모델 충실도 | flat-init · wrapping 없음 | 중간 |
| **A3′** | ρ 의 내접/등가 비 0.888 | flat-init 탓에 정사각형 값에 가까움 → **참 비는 그 이하**, 즉 1.77 은 **낙관 상한** | 중간 — `m4_config` 가 "마지막 남은 미정량 낙관 항목" 으로 자기 기록 |
| — | A2 계수 (0.6 / 0.5 / 1.8) | 외부 근거 없음. **A-family envelope 는 국소 2×2 만 시험됨** | 중간 |

**`net_radius` 만은 A1 에 독립**이다 — 논문 C 의 역산이지 시뮬 결과가 아니다. 이 사슬의
가장 튼튼한 앵커가 여기 있다.

### 8.6 dead / inert 파라미터

7 건이 확인됐다 (`capture_thresh` · `adversary_omega_att_max` · `e_net_init` ·
`viability.seed` · `baselines.*_u0` · `turn_limited` · `finisher_slew_cmd`). **전부
문서화된 것**이며 목록은 부록 C.2. 요점은 "설정 파일의 값을 바꿔도 조용히 아무 일도
일어나지 않는 항목이 존재한다" 는 것이다.

---

## §9. 검증이 무엇을 확인했는가

> "테스트 통과" · "감사 완료" 는 이 절의 답이 아니다.

### 9.1 검증 종류별로 무엇이 확인되고 무엇이 확인되지 않는가

| 종류 | 확인할 수 있는 것 | **그것만으로는 확인되지 않는 것** | 이 저장소의 사례 |
|---|---|---|---|
| **코드·규약 일관성** | 선언한 규칙대로 계산되는가 | **규칙이 현실적인가** | `tests/test_b0_v3_contract.py` · `test_b2_contract.py` · `test_terminal_truth_table.py` · `test_contract_parity.py` · `test_source_constant_hygiene.py` |
| **수치적 검토** | 결과가 수치 선택(n, dt, 보간 규약)에 얼마나 의존하는가 | **실제 시스템에서도 같은가** | n-cut spike (n=500 불안전) · chord-swept 두 규약 16/17 일치 · `test_derived_constants_r3.py` |
| **외부 자료 비교** | 특정 측면이 외부 근거와 부합하는가 | **모델 전체가 타당한가** | Xu 2025 면적 역산 재현 (1.998 vs 2.0) · Pliska 비율 채택 |
| **회귀·재현** | 코드 변경이 기존 산출을 바꾸지 않았는가 | **관측하지 않은 조건에도 일반적인가** | `test_sealed_replay_parity.py` · golden files · bit-identical 검사 |
| **독립 검토·재현** | 다른 사람이 결과를 추적·확인했는가 | 〃 | **§9.4 참조 — 이 칸이 가장 비어 있다** |

### 9.2 실측한 테스트 현황 (2026-09-14, 본 설명서 작성 중 실행)

```
PYTHONIOENCODING=utf-8 python -m pytest tests/ -q
```

| 항목 | 값 |
|---|---|
| 테스트 파일 | 90 |
| **결과** | **802 passed · 65 skipped · 0 failed** (41 분 28 초) |
| skip 사유 | **torch 미설치** → conftest 가 torch 표시 **63 건** 을 건너뜀 (+ 기타 2) |

> **정직 표기**: 실패는 0 이다. 그러나 **"전체 통과" 는 아니다** — skip 된 65 건은
> **이 실행에서 수행되지 않았다**. 여기에 학습 스택(MAPPO / PPO / GAE / value-norm /
> obs-norm / BC) 테스트가 통째로 들어간다. 즉 **이 실행이 검증한 것은 B2 scripted 경로
> 이고, MARL 경로 테스트는 확인한 실행에서 수행되지 않았다** (그 이전 이력은 확인하지
> 않았으므로 "한 번도" 라고는 쓰지 않는다 — §9.3-보 와 동일 규율).
>
> 그리고 §9.1 이 말한 대로, 802 건이 통과했다는 것은 **선언한 규칙대로 계산된다**는
> 뜻이지 **그 규칙이 현실적이라는 뜻이 아니다.**

### 9.3 감사 기록 — 대상 · 기준 · 결과 · 남은 한계

| 감사 | 대상 | 비교 기준 | 결과 | **남은 한계** | 수행 주체 |
|---|---|---|---|---|---|
| `external_audit_report_2026-09-07.md` | claim registry 52건 + 아티팩트 208 + KSAS draft_r5 + R2a/R2b | 외부 감사자(**GPT**)의 적대적 질문 | 다수 문안 하향·2건 신규 등록·"ACTIVE ≠ 강한 증거" 범례 도입 | **감사자가 저장소에 접근할 수 없었다** — 우리가 요약한 문서 하나만 읽었다. 요약이 빠뜨린 것은 감사되지 않았다 | **AI 감사** |
| R2b closure 감사 (2회) | R2b 봉인 사슬·C arm | 적대적 재검토 | Q2 **FAIL** → "cooperation" 기전 어휘 전면 폐기, "협력 효과" → **limiter-control opportunity** 로 재명명 | 어휘 교정이지 새 증거 아님 | **AI 감사** |
| `environment_numeric_audit_2026-08-13.md` | 환경 수치 | — | KSAS PASS w/ caveats | 자기 코드 대비 | AI |
| `dead_code_zombie_audit.md` · `code_liveness_registry.tsv` | 죽은 코드 | grep + 호출부 | 목록화 | **최신성 보장 없음** — 본 설명서가 §2.4 에서 재확인 | AI |
| `claim_evidence_code_audit.md` | 주장–증거–코드 매치 | — | GAP 5건 등록 (C0xx) | 〃 | AI |
| **W2 code audit (2026-09-13)** | Q1/Q3/Q4 층1 후보 | **코드 정독** (실험 0 · 서버 0) | 층1 종료 · `τ_lock` race 발견 | 정독은 실행이 아니다 | AI |
| **B2 구현 검증 (2026-09-14)** | partition 규칙 | **시뮬레이터의 authoritative trace** (`info["contacts"]`, `net_spent_step`) | s=901 이 H_fb 로 오분류될 뻔한 것을 실측으로 포착 | 표본 60 ep smoke | AI, **단 비교 기준이 자기 재구현이 아님** |

### 9.3-보. 검증 장치 자체의 한계 (교차검증 신규 발견)

"게이트가 green" 이라는 사실이 무엇을 뜻하는지도 검증돼야 한다. 아래는 **초록불이지만
그 초록불이 재는 것이 생각보다 적은** 항목들이다.

| 장치 | 초록불이 실제로 뜻하는 것 | 뜻하지 않는 것 |
|---|---|---|
| B0 v3 봉인 게이트 "contract tests 12 passed · regression 0 failed" | 봉인 직전 실행은 **770 passed · 65 skipped · 0 failed** | **skip 65 에 torch 부재 63 건이 포함** → **확인한 두 실행(봉인 직전 770/65/0, 본 문서 802/65/0)에서는 MAPPO / PPO / GAE / train_m4 CLI 계약 테스트가 수행되지 않았다.** (그 이전 이력은 확인하지 않았으므로 "한 번도" 라고는 쓰지 않는다.) 또 `conftest` 자신이 "skip 이 2 개를 넘으면 멈추라" 고 적은 조건을 두 실행 모두 위반한다 |
| contract test `t0` (봉인 해시) | 같은 파일 안의 body 로 같은 파일 안의 hash 를 재계산 = **손편집 탐지** | 봉인 내용의 정당성. 외부 대조는 `grid.rows == build_grid()` 와 `stage3_protocol` hash 두 항뿐 |
| contract test `t10` (`r_nk = 6.0`) | 리터럴이 리터럴과 같다 | **값이 틀려도 영원히 green.** `environment_numeric_audit` 이 `r_nk` 를 "UNKNOWN 근거 · HIDDEN + CLAIM-CRITICAL" 로 등급 |
| GO smoke "7/7 PASS" | 러너가 돈다 | `2_manifest_parity` 는 **무조건 `True` 로 선대입**. `3_crn_pairing` 은 `A==B==picks*1 or A==B` 라 **뒤 절이 앞 절을 흡수**해 manifest 지정 scenario 소비 여부를 검사하지 않음. `7_latch` 는 `partition_bin` 의 `_pre_kinetic` 을 **재진술한 자기일관성 검사** (안전망 분기는 재진술조차 안 됨) |
| B0 v3 `gates` 5 항목 | `tests/test_b0_v3_contract.py` 만 지목 | **B2 실행 불변식을 지키는 `test_b2_contract.py` 16 건이 어느 gate 에도 등재되지 않았다.** `b2_run --smoke` 도 b0 테스트만 서브프로세스로 돌린다 |
| `identity_ok` (raw count 항등식) | `counts['N'] == n_N_fire` | **구조적으로 항상 참.** bin `N` 이려면 FSM 이 LOADED→DEPLOYING 을 반드시 거쳤으므로 `fire=True` 가 강제된다. `P(N) = P(FIRE)·P(N|FIRE)` 의 **수치 재구성은 어디에서도 수행되지 않는다** |
| partition "상호배타·완전" | 순차 `if/return` 이라 구조적 partition 은 자명 | (i) **PENETRATED 와 doctrine 위반이 같은 `H_illegal` 로 합쳐지는 흡수 경로**가 있다. (ii) `_pre_kinetic` 은 `net_spent_step` 이 `None` 이면 **무조건 True** 를 반환하는데 그 값은 래퍼 `__getattr__` 위임에 의존한다 — 위임이 끊기면 **예외 없이** 모든 접촉 에피소드가 `H_illegal` 로 오분류된다 |

### 9.4 세 가지를 반드시 구분한다

| 구분 | 이 프로젝트의 현황 |
|---|---|
| **AI 감사** | 사실상 **전부**. 위 표의 모든 행. 감사 5종 + registry 3종 전부 병렬 subagent 산물이며, `environment_numeric_audit` 은 **"본 보고서의 모든 RECOMMENDED ACTION 은 제안일 뿐 미실행"** 을 자인한다 |
| **사람의 검토** | 지도교수 컨펌은 **연구 방향·계약 결재** 수준 (docs/94 결재 ①~⑦). **코드 라인 단위 사람 검토 기록은 없다** |
| **독립 재현** | **없다.** 다른 사람이 이 코드를 돌려 같은 수를 얻은 기록이 저장소에 없다. 교차 머신 앵커는 `test_sealed_replay_parity` 한 층뿐이다 |
| **외부 측정 대조** | **없다.** 하드웨어 실험·비행 시험·HIL 기록이 없다. 외부 대조는 **문헌 수치 인용**뿐이고, 그 인용조차 §8.3 의 AI-추출-DRAFT 경고가 걸린다 |

> **"외부 감사 PASS" 라고 쓰면 안 된다** (교차검증 지적): 2026-09-07 감사는 감사자가
> **저장소에 접근하지 못한 채 우리가 쓴 요약 문서 하나만** 읽었고, C001 / C002 / C004
> 수치는 **재검증 불가라고 자인**했으며, KSAS 제출 판정은 **조건부 HOLD** 였다. 그리고
> 그 보고서 파일 자체가 **untracked** 다.

### 9.5 자체 재구현 일치 ≠ 원 실행 기록 일치 — 실제 사례

**`100-X` 사건 (2026-09-13h → i)**: route-argmax separatrix 가설이 한 번 **기각**됐다가,
다음 날 그 기각이 **자기 측정 버그** 였음이 드러나 뒤집혔다
(`2026-09-13i_101X_chain_closes_route_argmax_flip_100X_rejection_was_my_measurement_bug.md`).

원인은 **자기 코드끼리 비교**했기 때문이다. 그래서 `docs/102 §7` 이 규율을 박았다:

> **6·7 의 대조는 우리 재구현이 아니라 simulator 의 authoritative trace 와 한다.**
> `100-X` 가 자기 코드끼리 비교해 버그를 놓친 전례가 있다.

이 규율은 2026-09-14 B2 구현에서 실제로 작동해 partition 오분류를 잡았다 (§9.3 마지막 행).

**본 설명서에서 새로 확인한 사실과 인용한 사실의 구분**:

| 새로 확인 (본 문서 작성 중 직접 실행/정독) | 기존 기록에서 인용 |
|---|---|
| 관측 차원 **65** 및 전 방어자 동일 벡터 (라이브 `env.reset`) | docs/94 의 계약 조항 |
| 셀 `r00c0` 의 해석된 파라미터 전 값 | R2a/R2b 판독 수치 |
| 행동 공간 Box 경계 (limiter ±7.738, finisher 5차원) | claim registry 등급 |
| `finisher.a_max = 0.0` (net-capturer 비병진) | 감사 보고서 판정 |
| B2 구현 5종 + `partition_bin`/`kinetic_fallback` 이 **untracked/미커밋** (`git status`) | docs/38 의 A1~A9 가정 사슬 |
| `RewardSpec.terminal` 의 CWC = +b_net **미수정** (코드 정독) | temp_research_note 의 사건 경위 |
| pytest **802 pass / 65 skip / 0 fail** (41분 28초, 실제 실행) | — |
| **tunneling 실측**: SOLO 60 ep 에서 계약 술어 0 회 / resolver 2 회 발동 (직접 실행) | — |
| **관측에 `r_nk` · `d_asset` 부재** 를 65 차원 전수 대조로 확인 (직접 실행) | — |

---

## §10. 현재까지 얻은 결과와 그 증거 지위

### 10.1 성립 지도 χ50(η, λ) 는 **무엇을 고정한 채** 얻은 결과인가

R2a 캠페인이 만든 경계 지도는 아래가 **전부 고정된 상태**에서 측정됐다. 하나라도
움직이면 그 지도는 그 조건의 지도가 아니다.

> **가장 먼저 적어야 하는 고정 조건 (교차검증에서 확인)**: R2a Stage 0~4 와 scout 의
> **모든 러너가 `limiter_mode="hold"` 로 `run_episode` 를 호출한다.** 그리고
> `hold_position_limiter()` 는 `zeros(4)` — 가속 0, 커밋 0 — 을 낸다.
>
> **즉 현재의 성립 지도는 "방어 limiter 가 전혀 움직이지 않는 조건에서 net 포획이
> 성립하는 경계"** 다. 컨트롤러 비교 지도가 아니다. 이 한 문장을 빼고 χ50 지도를
> 인용하면 지도가 무엇의 지도인지 오독된다.

| 축 | 고정값 | 근거 |
|---|---|---|
| **limiter 제어** | **`hold` = `zeros(4)`, 완전 부동** | `baselines.hold_position_limiter` |
| 세계 | legacy **24 m 회랑**, 자산 원점, 침투 반경 1 m | `train.layout.*` |
| 백엔드 | **축소차수 3DOF** (점질량 + 지향축). 6DOF transfer 는 별도 gate | `sim/analytic.py`, `docs/93` |
| 공격자 | **A2-nominal 단일** — jink 0.6 · route 0.5 · sense 30 m · dodge 1.8 · 고정 규칙 | `r2a_stage1.resolve` 기본값 |
| 공격자 수 | **1** | — |
| 관측 | **무잡음 · 무지연 · 전 방어자 공통 65 차원**, 위협 등급 참값 제공. **임무 기하는 관측 밖** | §3.1, §3.4 |
| 시간 조건화 | **q_dec = 1/6** (dt 와 결합 고정) · **q_race = 1/3** · **q_kill = 1/2** | `_inject` co-scale |
| 능력 족 | **μ = a_lim/a_att = 0.35** · **ν = v_lim/v_att = 1.00** · adversary v 헤드룸 1.50 | `CAPABILITY_RATIOS` |
| 탄약 | **K = 1** 단발 | `FinisherSpec.K` |
| 발사 자격 | **θ_fire = 0.9 고정 admissibility gate** | `fire_gate` |
| finisher | **병진 불가** (`a_max = 0`), 지향만 ω = 2.0 rad/s | `FinisherSpec` |
| 판정자 | **se3_cone**, 도달집합 union (실측 실현가능 witness 중앙값 **2504**) | `viability` |
| kinetic | `p_kill = 1.0` · `r_nk = 6 m` · `r_contact = 0.75 m` | `SystemSpec` |
| 지평선 | 160 step = 8.0 s | L2 |
| 스폰 | dx 2.0 m · r_lat 5.0 m 지터 | `SpawnSpec` |
| **cone 기하** | **셀 의존 — 세계 상수가 아니다** (아래) | `r2b_phase1._slices` |

**cone 기하는 두 slice 로 갈린다** (교차검증 정정 — 본 설명서 초안이 8.22/0.2121 을
세계 상수로 적었던 것을 바로잡는다):

| λ slice | 행 | `cone.range_max` | `cone.half_angle` | 공통 |
|---|---|---|---|---|
| slice 0 (λ = 4.644) | 1–7 | **8.22 m** | **0.2121 rad** | `net_radius` 1.77 · `range_min` 0.0 |
| slice 2 (λ = 3.574) | 8–14 | **6.3258 m** | **0.2728 rad** | 〃 |

λ = R_max/ρ 가 격자의 **세 번째 축**이므로 cone 이 고정이면 λ dose test 와 slice 분할
자체가 성립하지 않는다. 56 셀 중 **28 셀이 6.3258/0.2728 로 돈다.**

**두 λ slice 의 증거 등급이 다르다** — 같은 표에 놓을 때 반드시 표기한다:

| λ | 출처 | n | 등급 |
|---|---|---|---|
| **4.644** | `stage2_readout` | 4,800 | **confirmatory** |
| **3.574** | `scout_l2_envelope` | 480 | **exploratory scout** |

봉인 문안: *"scout 추정치는 confirmatory 증거로 재승격되지 않는다."*
학습 arm 비교는 이 격자 위의 **새로운 confirmatory 평가**다.

**R2a 의 collapse 판정은 PARTIAL_3D 다** (C045): (χ, η) 2-D collapse 는 **기각**됐고,
선언된 교란·조건화 변수 아래에서 **λ 가 추가 좌표로 필요**하다. 즉 "두 무차원수로
경계가 정리된다" 는 주장은 **성립하지 않는다**.

### 10.2 세 종류의 "성공" — 증거 지위가 전혀 다르다

교수님이 지목한 구분이다. 이 프로젝트에서 **양성 결과는 가장 배치 불가능한 대상에서만
나왔다.** 이것이 현재 증거 구조의 핵심이며 숨기면 안 된다.

| | **① 탐색으로 얻은 성공 계획** | **② 학습된 정책** | **③ 실행 가능한 정책** |
|---|---|---|---|
| 이 프로젝트의 실체 | **R2b C arm** — 시나리오마다 CEM 으로 limiter plan 을 오프라인 탐색 (lite rollout 384/시나리오) 후 최종 판정용 full-fidelity 재생 1회 | **B-3 / B-4 / B-5 MARL arm** | **rule arm** — hold(SOLO) · arc(RULE_COOP) · intercept |
| 결과 | **Δp_CA_net = +0.370**, CI [+0.353, +0.388], 14/14 행, 양 slice 7/7 | **없음 — 미실행** | **P1 양성 기준 미충족**: Δp_net = −0.001, CI [−0.004, +0.001], 5/14 행 |
| 무엇을 아는가 | 그 시나리오에 대해 **좋은 계획이 존재한다** | — | **그 규칙으로는 못 한다** |
| 왜 배치 불가인가 | 시나리오를 **미리 알고** 오프라인 탐색을 수행한다. 온라인 관측만으로 재현할 방법이 없다 | — | 배치 가능 |
| 명명 규율 | **search-based attainment benchmark.** **upper bound 아님** (R_rec > 1 가능) · **Δχ50 아님** | — | — |

**이 셋 사이에서 말할 수 있는 것과 없는 것**:

- 말할 수 있다: *"rule-based null 은 limiter control 에 이용 가능한 기회가 **없다**는
  뜻이 아니다. 규칙 기반 arm 은 사전등록 기준을 못 넘었고, 특권적 봉인예산 탐색은
  훨씬 높은 달성도를 냈다. 이는 더 표현력 있는 배치 가능 컨트롤러 — 학습 컨트롤러 포함 —
  의 평가를 **동기화**한다."* (C049 감사 교체 문안)
- 말할 수 없다: 협력이 필요하다 · 그 이득이 협력 기하 때문이다 · **MARL 이 그 benchmark 를
  회수할 것이다.** C049 가 이 셋을 명시적으로 부정한다.

### 10.3 선택된 사례 분석 — 표본이 어떻게 골라졌는가

**먼저 선택 규칙 자체를 적는다 (교차검증으로 코드에서 확정)**: `sample()` 이 셀마다
`(C_N == 1) ∧ (plan_kind == 'accels')` 인 시나리오를 **s 오름차순 앞 5 개**씩 고른다.
28 cell × 5 = **140 판**. 즉 **3 중 선택**이다 — ① 성공한 판만 ② accels-best 계획만
③ 앞 5 개만.

그리고 dep / geom / steer / margin / velocity / noeffect / route **7 개 probe 는 독립
표본이 아니라 이 140 판의 재분석**이다. 뒤쪽 네 probe 는 그 안의 **46 판**
(multi-dependent) 위에 서고, 최종 기전 사슬은 **15 판** (LOST) 위에 선다.

> **금지 표현**: "7 축 독립 검증" · "여러 독립 실험이 같은 결론". 같은 140 판을 일곱 번
> 다르게 본 것이다.

아래 분석들은 전부 **선택된 판**을 뜯어본 것이다. 전체로 일반화하지 않는다.

| 분석 | 표본 선택 방식 | 일반화할 수 없는 이유 |
|---|---|---|
| **C arm plan-class 분해** | Δp 를 계획 종류별로 사후 분해: accels-best 1962판이 +0.3675 (전체 +0.370 의 **99.2%**, in-class +0.524), intercept-best 818판은 `C_N == B_N` **818/818 완전 재생** (기여 0.8%), hold-best 20판 기여 0 | **descriptive attribution 이지 기전 증거가 아니다.** "gain 이 accels-best class 에 집중" 까지만 |
| **robust-clean witness** (C009) | SHAPING 19판 중 witness **8**, **전부 knife-edge** (margin ≤ 2.3 cm) | Pareto frontier 의 **가장 보수적 끝점** 측정. legacy small-scale regime 한정. "NO_WITNESS = 불가능" 금지 |
| **pre-fire existence witness** (C022) | ep35 **1/7** 이 NK-밖 무력화 달성 | **존재 증인 1건.** "shepherding 성공" 일반화 금지 |
| **자연 fallback 창** (C025) | ep1 **n = 1** 육안+수치 관찰 | 일반화 금지 |
| **geom / steer / margin / velocity-decomp probe** (2026-09-13c~f) | 경계 근방의 선택 셀. velocity-decomp 는 **primary cell 이 degenerate** 해 secondary 로 판정 | 셀 선택이 결론에 개입할 수 있음. 각 노트가 자기 한계를 기록 |
| **no-effect 진단** (2026-09-13g) | 25 records 가 효과를 **~300 배 증폭**하는 구조 발견 | "무효과가 정상" 이 기준선 |
| **route-argmax 사슬** (100-X → 101-X → 101-A) | 100-X 가 가설을 **기각**했다가 다음 날 그 기각이 **자기 측정 버그**로 판명돼 뒤집힘 | §9.5. 남는 한정어는 `route_boundary_audit.json` 의 `evidence_grade` 가 **`exploratory`** 라는 것, 그리고 표본이 위 15 판이라는 것뿐이다. **초안이 여기 적었던 두 가지 반박은 철회한다 — 아래 참조** |
| **margin audit (m_cap ≈ 11 cm)** | 위 46 판 | **"확인된 여유" 로 읽으면 안 된다**: 산출물 자신이 finite witness 하에서 `m_cap` 이 참 마진을 **과대추정**한다고 적었고, witness ×4 · n_dir ×2 재검에서 median 은 오히려 0.11217 → **0.11261 m 로 상승**했으며 46 판 중 **10 판이 10% 초과 축소**됐다. 봉인 BRANCH_B 논거("margins are comfortable")는 산출물 안에서 이미 반박돼 있다 |
| **velocity decomposition** | 주 셀 degenerate → 보조 셀로 판정 | 보조 셀 ρ = 0.25 는 **99-N = 판별 효과 미검출**이고 ρ = 0.5 는 99-P 다. **"정반대" 가 아니다** (r2 정정): 효과를 **검출하지 못한 것**은 **반대 방향 효과를 검출한 것**과 다르다. 정확한 한정어는 "두 셀 중 한 셀에서만 층 분리가 검출됐다" 이며, 그것만으로도 한쪽만 인용하면 안 된다 |

#### r2 에서 철회한 반박 두 건 — 확인해 보니 제 지적이 틀렸다

설명서 초안이 `101-A` 기전 사슬에 대해 두 가지 반박을 적었다. **둘 다 성립하지 않는다.**
본 개정에서 직접 재계산해 확인했다.

| 초안의 반박 | 확인 결과 | 판정 |
|---|---|---|
| "노트와 JSON 의 δ_g 중앙값이 갈린다 (0.0249 vs 0.0208)" | **측정 시점이 다르다.** 0.0208 = `delta_g_pre_flip_median` (**flip 직전**), 0.0249 = 대조군 표의 **fire−1** 값. 노트가 각각 "flip 직전" 과 "(fire−1, 같은 tick)" 으로 명시하고 있다 | **철회** |
| "`RET_noeffect δ_g min 0.03575` 는 산출물에 대응 필드가 없다 — 노트에만 있는 수치" | **산출물에 있다.** `records[].rows[]` 에서 `fire_off == -1` 행의 `delta_g_ref` 를 모아 재계산하면 노트의 세 쌍이 **정확히 재현**된다: LOST 0.02489 / 0.00195, RET_noeffect **0.06222 / 0.03575**, RET_effect 0.12516 / 0.06029 | **철회** |

재현:

```
# artifacts/r2b/route_boundary_audit.json 의 records[].rows[] 에서 fire_off == -1 수집
# → group 별 median/min 이 101-A 노트의 대조군 표와 일치
```

`summary` 블록의 `delta_g_pre_flip_*` 가 `RET_noeffect` 에서 `null` 인 것은 그 그룹의
`n_flip = 0` 이기 때문이며 (flip 이 없으면 flip-직전 값이 정의되지 않는다), **누락이
아니다.** 남는 지적은 "fire−1 대조는 `summary` 에 집계돼 있지 않아 per-record 로
내려가야 읽힌다" 는 **탐색 편의 문제**뿐이다.

> **교훈**: 초안의 이 두 문장은 §9.5 가 경고한 것과 같은 실수다 — **산출물을 열어보지
> 않고 노트와 요약 블록만 대조**했다. 비판 쪽으로도 같은 규율이 적용된다.

### 10.4 아직 존재하지 않는 결과

| 항목 | 상태 |
|---|---|
| **B2 scripted primary** | **미실행.** `artifacts/r2b/b2_scripted/` 에 `manifest.json` 과 smoke fixture 만 존재. `primary/` 디렉터리 자체가 없다. 예산 100,800 ep ≈ 60 h 직렬 (랩서버 샤딩 필수) |
| **forced-fire 진단** | primary 이후에만. 표본이 0 일 수 있음 (§7.5) |
| **MARL 학습 arm** | **미실행** — B0 v3 불변 조항이 stop rule 통과 전 금지 |
| **6DOF / airframe transportability** | `docs/93` 은 **미봉인 설계 노트**. 실행 슬롯 W10+ |
| **하드웨어 / HIL / 비행시험** | **없음** |
| **held-out 공격자 평가** | 없음 |
| **독립 재현** | 없음 |

---

## §11. 무엇을 믿고 진행할 수 있는가 — 최종 판정표

### 11.1 주요 주장 판정

판정: **[지지]** 현재 지지됨 / **[조건부]** 특정 모델·정책·분포에 한정 /
**[미확인]** 판단할 증거 없음 / **[철회]** 기존 설명 유지 불가.

| # | 주장 | 판정 | 조건 / 근거 | 판단을 바꿀 수 있는 근거의 종류 |
|---|---|---|---|---|
| V-1 | 이 세계에서 clean net capture 는 fire 틱 동결 술어 `(¬boxed_in) ∧ (v_shot_worst ≥ 1)` 이며 봉쇄는 포획이 아니다 | **[지지]** | 코드 계약 (C008) | 코드 변경뿐 |
| V-2 | `v_shot_soft` 는 포획 확률이 아니다 | **[지지]** | 코드 (C011) | — |
| V-3 | (χ, η) 2-D collapse 는 **기각**되고 λ 가 추가 좌표로 필요하다 | **[조건부]** | R2a Stage 3, PARTIAL_3D (C045). 선언된 교란·조건화 변수 하 | 새 교란 축에서의 재검 |
| V-3b | **λ 감소(cone 종횡비 축소)가 성립 경계를 불리한 방향으로 민다** | **[지지]** | Stage 4 **독립 dose test** — 3 level (λ 4.644 / 4.109 / 3.574), 6 cell × 400 = 7,200 ep, paired CRN, 전 6 셀 `direction_ok`, pooled dp_L1 −0.140 / dp_L2 −0.303. A2-nominal · hold 한정 | — |
| V-3c | **현재 성립 지도는 limiter 가 전혀 움직이지 않는 조건에서 측정됐다** | **[지지]** | R2a Stage 0~4·scout 전 러너가 `limiter_mode="hold"` = `zeros(4)` | — |
| V-4 | 국소 3-D 경계의 두 λ slice 가 특성화됐다 (χ50(η) at λ ∈ {4.644, 3.574}) | **[조건부]** | A2-nominal · q_dec = 1/6 · capability-ratio 족 한정 (C044) | confirmatory 재측정 |
| V-4b | **λ = 3.574 slice 의 χ50 값으로 무엇을 쓸 것인가** | **[미확인 · 종류 2]** | 봉인 격자의 λ2 행 중심이 **n = 480 exploratory scout** (산출물 자신이 "not evidence") 이고, Stage 3 confirmatory 값 (행당 n = 1360) 은 그와 최대 **0.017** 다르다. **어느 쪽을 쓸지 adjudication 기록이 없다.** — **초안이 여기 붙였던 "순환" 판정은 철회한다** (r2): 탐색 자료로 평가 위치를 정하고 **독립 자료로 평가**하는 것은 정당한 설계다. 순환을 주장하려면 어떤 자료·판단이 재사용됐는지 보여야 하고, 그 근거를 확보하지 못했다 | adjudication 결정 |
| V-5 | **`intercept` 컨트롤러**는 사전등록 P1 양성 기준을 **충족하지 못했다** | **[지지]** | Δp_net = −0.001, CI [−0.004, +0.001], 5/14 행, 11,200 시나리오 paired CRN (C047). **"rule-based 일반" 이 아니라 "이 한 컨트롤러" 다.** `arc` 는 미측정 | 다른 rule 컨트롤러 측정 |
| V-6 | 봉인 예산의 limiter-plan **탐색**이 hold 대비 NET_CAPTURE 달성도를 크게 올렸다 (Δp_CA_net = +0.370, CI [+0.353, +0.388], 14/14 행) | **[조건부]** | **search-based attainment benchmark** — 배치 가능한 정책도, 상한도, Δχ50 도 아니다 (C048) | — |
| V-7 | 따라서 limiter control 에 이용 가능한 기회가 **없다고 말할 수 없다** | **[지지]** | C049 (감사 교체 문안) | — |
| V-8 | 그 이득이 **협력 기하** 때문이다 | **[미확인 · 종류 1]** | 어휘 자체가 폐기됨. single / independent / coordinated **necessity ablation 미실시** | necessity ablation |
| V-9 | 협력이 **필요하다** | **[미확인 · 종류 1]** | 미확립 (c8) | 〃 |
| V-10 | MARL 이 search benchmark 를 회수할 것이다 | **[미확인 · 종류 1]** | C049 가 명시적으로 부정 | 학습 arm 실행 |
| V-11 | 학습 협력 조향이 경계를 민다 (Δχ50 > 0) | **[미확인 · 종류 1]** | **학습 arm 미실행.** B2 scripted 조차 primary 미실행 | B2 → stop rule → MARL |
| V-12 | 하드킬은 explicit kamikaze commit 이 아니라 **접촉 resolver 에 지배**된다 | **[지지]** | E3 n=300, 커밋 limiter 중앙값 0.0/4 (C033) | — |
| V-13 | a ≥ a\*(39.33) 구간의 net capture 0 은 발사 후 실패가 아니라 **게이트 기권(censored)** 이다 | **[지지]** | E1c: a ≥ 32.2 에서 발사 0/350 (C032) | — |
| V-14 | 성립 상계는 단일 값이 아니라 3 계층 (39.33 > 31.77 > 27.03) | **[조건부]** | 기준 운용점 한정. 32.37 은 `tan` 규약 superseded (C042) | 규약 재정정 |
| V-15 | 관측은 무잡음·무지연 참값이며 모든 에이전트가 같은 벡터를 본다 | **[지지]** | 세계의 **정의** (§3.4). 1 스텝 지연 채널 2 개는 모두 무해 | — |
| V-15b | **정책이 보호 자산·NK 구역·발사 임계를 관측으로 안다** | **[철회]** | 65 차원에 `target` · `target_radius` · `r_nk` · `d_asset` 이 **없다.** 침투 판정·NK veto·arc slot 이 전부 `target` 을 쓰는데 정책은 못 받는다. `target` 이 전 에피소드 `[0,0,0]` 고정이라 **암묵적으로 외울 수만 있다** | 자산 위치 랜덤화 |
| V-15c | **계약의 권위 접촉 술어가 실제 판정을 한다** | **[조건부로 반증]** | **검사한 표본(60 + 100 ep)에서 0 회 발동.** 이산화 논거가 이를 뒷받침한다 (틱당 이동 1.679 m > 구 지름 1.5 m). 실효 판정자는 swept 선분 resolver 이며 계약 문안에 없다. **전 격자·전 arm 에서 항상 0 이라는 증명은 아니다** | limiter 가 움직이는 arm 에서의 측정 · dt 축소 |
| V-16 | τ₀ = 0.30 s 가 실제 물리 지연 전체를 대표한다 | **[철회]** | 총 pending 은 0.40 s 이고, sense 성분 0.10 s 는 **선언의 근거일 뿐 시뮬에서 실현되지 않는다** | 관측 지연 구현 |
| V-17 | 층1 물리 민감도가 없다 / robustness 가 입증됐다 | **[철회]** | 정확한 문장은 **"clean candidate 없음으로 screen 종료"** 뿐 | 층3 실행 |
| V-18 | 시뮬레이터 NET_CAPTURE 는 실제 무력화를 뜻한다 | **[미확인 · 종류 1]** | 그물 접촉·손상 모형이 **부재**. 라벨은 기하 술어 | 하드웨어 시험 |
| V-19 | 이 결과가 6DOF/실기체로 옮겨간다 | **[미확인 · 종류 2]** | `docs/93` transportability gate 미실행. "자세 시간상수를 χ 가 흡수한다" 는 **가설이지 주장이 아니다** | frozen-policy plant swap |
| V-20 | A2 이외의 공격자에게도 같은 경계다 | **[미확인 · 종류 2]** | 국소 2×2 family envelope 만 시험 (C046). worst-family 경계 위치 미추정 | A-family 층3 arm |
| V-21 | 잡음·지연·구동기 지연 하에서도 같은 경계다 | **[미확인 · 종류 2]** | 전부 미배선 | 층3 |
| V-22 | 다수 공격자·재장전(K≥2) 로 확장된다 | **[미확인 · 종류 3]** | 계약 밖 | 별도 계약 |
| V-23 | **HARD_KILL 라벨이 실제 파괴/치명 효과를 뜻하고 `r_nk` 가 안전을 보장한다** | **[미확인 · 종류 1]** | `p_kill = 1.0` 이라 `_bern` 은 **해시조차 소비하지 않는 항등 함수**다. `kill_radius` 는 `params.py` 가 스스로 "no external grounding" 이라 적은 값. `r_nk = 6.0` 은 감사가 **"UNKNOWN 근거"** 로 등급했고 계약 테스트가 리터럴을 자기 기준으로 삼아 **영원히 green** | 외부 lethality 근거 |
| V-24 | **현행 B2 작업 트리를 지정 커밋만으로 복원할 수 있다** | **[철회]** | B2 실행 계층(러너 4종 · 계약 테스트 · manifest)이 **버전 관리 밖**이고, 이미 생산된 smoke 산출물의 `code_commit = ac7cf2a` 는 **그 커밋에 없는 필드**(`bin`, `kinetic_from_t`)를 담고 있다. `provenance.git_commit()` 은 dirty/untracked 를 보지 않는다. 또 `manifest_hash` 가 `code_commit` 을 포함하므로 **B2 를 커밋하면 hash 가 바뀌어 `_resume` 이 기존 shard 를 거부**한다. **범위 한정 (r2)**: 이것은 **현 B2 작업분에 한정**된 판정이며, **과거에 봉인된 R2a/R2b 결과의 재현성을 철회하는 근거가 아니다** — 그 산출물들은 커밋된 코드와 봉인 해시를 갖고 있다 | 커밋 + hash 정책 결정 |
| V-25 | **`Δχ50` (primary estimand) 가 계산돼 있다** | **[미확인 · 종류 1]** | **arm 간 Δχ50 계산기가 리포에 없다.** `r2a_stage3_readout` 의 `d_chi` 는 **λ slice 간 차분**이며 단일 arm 으로만 적합된다. `R_rec` 계산기도 없다. 즉 **현재 리포에 그 수를 산출할 수단이 없다** (과거 산출 이력은 확인하지 않았으므로 "한 번도" 라고는 쓰지 않는다) | 계산기 구현 |

### 11.2 미확인의 분류

| 종류 | 뜻 | 해당 |
|---|---|---|
| **1 — 질문의 의미를 바꿀 수 있음** | 이것이 뒤집히면 "우리가 무엇을 묻고 있었나" 가 달라진다 | V-8 · V-9 · V-10 · V-11 · V-18 · **V-23** · **V-25** |
| **2 — 적용 범위를 제한** | 결과는 살지만 조건이 좁아진다 | **V-4b** · V-19 · V-20 · V-21 |
| **3 — 후속으로 남김** | 현재 질문에 영향 작음 | V-22 |
| **[철회]** | 기존 설명을 유지할 수 없다 | V-15b (자산 미관측) · V-16 (τ₀ 대표성) · V-17 (민감도) · V-24 (**B2 작업 트리** 복원 가능성 — 과거 봉인 결과 아님) |
| **[조건부로 반증]** | 검사한 범위에서 반증됐으나 전역 증명 아님 | V-15c (권위 술어 미발동 — 검사 표본 한정) |

**모든 항목을 신규 실험 과제로 바꾸지 않는다.** V-18 (그물의 실제 무력화) 과 V-23
(HARD_KILL 의 치명성) 은 이 URP 범위에서 해소 불가이며 **해소 대상이 아니라 명시
대상**이다. U-19 · U-20 은 보고 규율로 흡수할 수 있고 반드시 실험을 필요로 하지 않는다.

### 11.3 이 설명서를 쓰면서 새로 드러난 미해결 항목

| ID | 항목 | 종류 | 왜 지금 중요한가 |
|---|---|---|---|
| **U-1** | `RewardSpec.terminal` 의 `CAPTURE_WITH_CONTACT = +b_net` 이 docs/94 결재 ④ 의 supersede 를 **아직 반영하지 않음** | 코드-계약 불일치 | MARL 을 켜는 순간 정책이 illegal substitution 에 clean capture 와 같은 보상을 받는다 |
| **U-2** | B2 구현 5종 + `partition_bin` + `kinetic_fallback` 이 **untracked / 미커밋** | 재현성 | `ac7cf2a` 에서 B2 를 실행할 수 없다 |
| **U-3** | `reference fallback` 의 컨트롤러 선택(`intercept` + `baseline_commit=True`)이 **구현자 판단**이며 봉인 문서에 없음 | 계약 공백 | P_U 값 전체가 이 선택에 의존 |
| **U-4** | 보상 라벨(`_outcome_label`, 사본1)과 과학 라벨(권위 술어)이 다른 술어 | 비준된 divergence | 두 층을 섞어 읽으면 안 됨 |
| **U-5** | NET_FAIL 에서의 RL-credit cut 이 **문서만** 있고 코드에 없음 | 미구현 | MARL 진입 전 필수 |
| **U-6** | 셀 내 지터(χ ±0.01, η ±0.15)가 `docs/102` 에 명시되지 않아 **승계로 처리**됨 | 계약 공백 | manifest `crn.jitter` 로 노출은 돼 있음 |
| **U-7** | forced-fire 표본이 **0 이 될 가능성** (smoke 에서 P(FIRE) = 1.000) | 설계 위험 | 진단 arm 이 공전할 수 있음 |
| **U-8** | `CLAUDE.md` 부록 A (2026-06-13) 와 `docs/00_status.md` (2026-06-24) 가 **현재 세계와 크게 어긋남** — Tiered C_0~C_3, Huh 2026 정면 비교, B-1~B-5, Fig 2/3/5/6 프레임은 이후 여러 차례 pivot 됨 | 정본 혼선 | 새 참여자가 가장 먼저 읽을 문서가 가장 낡았다 |
| **U-9** | ρ = 1.77 의 내접/등가 비 0.888 이 **낙관 상한** (flat-init 탓) | 출처 한계 | χ = aτ²/2ρ 의 분모. 참 ρ 가 더 작으면 χ 가 커진다 |
| **U-10** | pytest **802 pass / 65 skip / 0 fail** — skip 65 건은 **torch 미설치로 이 기계에서 미실행**이며 학습 스택이 여기 포함. 봉인 게이트 실행(770/65/0)도 같은 skip 수 → **확인한 두 실행에서는 학습 스택 테스트가 수행되지 않았다** (그 이전 이력 미확인). 두 실행 모두 `conftest` 의 "skip 2 초과 시 중단" 조건을 위반 | 검증 공백 | MARL 진입 전 torch 환경에서 재실행 필요 |
| **U-11** | **검사한 표본(60 + 100 ep)에서 계약의 권위 접촉 술어가 발동하지 않았다** (이산화/tunneling 논거). 실효 판정자(swept resolver)가 계약 문안에 없고 amendment 미등재. **limiter 가 움직이는 arm 은 미측정** | 계약 이탈 (범위 한정) | 봉인 문안만으로 `H_illegal` 을 재현하면 관측된 접촉을 놓친다 |
| **U-12** | B0 v3 JSON 이 자기 격자와 모순되는 "realized a 16.5..27.5" 를 봉인 (실제 14.95..25.96). 검증 테스트 없음 | 봉인 문서 오류 | 결론은 불변이나 수치가 재현 불가 |
| **U-13** | 문헌 앵커의 근거 문서(`docs/34·35·39`)가 **"AI 추출 DRAFT · 비준 전 논문 인용 금지"** 인데 `m4_config` 는 확정 선언으로 서술 | 출처 등급 불일치 | **논문 인용 전 사람 원문 대조 필수** |
| **U-14** | **arm 간 `Δχ50` 계산기와 `R_rec` 계산기가 리포에 없다** | 지표 부재 | B0 v3 primary estimand 를 현재 산출할 수단이 없다 |
| **U-15** | `manifest_hash` 가 `code_commit` 을 포함 → B2 스택을 커밋하면 hash 가 바뀌어 `_resume` 이 기존 shard 를 거부 | provenance ↔ 재현성 기계적 충돌 | 커밋 시점 정책 결정 필요 |
| **U-16** | GO smoke 항목 중 `2_manifest_parity` 무조건 True · `3_crn_pairing` 흡수 절 · `7_latch` 자기일관성. `test_b2_contract.py` 16 건이 어느 gate 에도 미등재 | 게이트 실효성 | primary 실행 전 점검 대상 |
| **U-17** | `_pre_kinetic` 이 `net_spent_step is None` 이면 무조건 True 반환 — 값은 래퍼 `__getattr__` 위임 의존. 위임이 끊기면 **예외 없이** 전 접촉 에피소드가 `H_illegal` 로 오분류 | 조용한 실패 경로 | assert 추가 여지 |
| **U-18** | finisher 능력 정의원이 둘 (`FinisherSpec.a_max = 0.0` vs backend `KinematicLimits(a_max=1.0)`), 상호 assert 없음 | 정의원 분기 | 현재는 무해 (0 이 이김) |
| **U-19** | **포획 판정의 보수성이 표본 집합 밖으로 확장되는지 미확인** — 연속 도달집합에 대한 포함 증명(covering 논법 / 구간 산술 인증)이 없다 | 보장 범위 | `v_shot_worst = 1` 의 거짓 양성 가능성을 배제할 수단이 현재 없다 (§5.1) |
| **U-20** | `P(N\|FIRE)` 의 분모 집합 구성 변화를 보정할 설계가 없다 | 인과 해석 공백 | 조향 개선과 발사 판단 개선의 분리에 별도 arm 또는 propensity 보정이 필요 (§12) |

---

## §12. 합격 기준에 대한 직접 답변

### 이 세계에서 무엇이 실제로 계산되는가

6 개 점질량 기체의 병진 운동과 지향축 하나씩(총 9 차원 × 6)을 0.05 s 간격 semi-implicit
Euler 로 적분한다. 매 틱 공격자의 τ = 0.30 s 도달집합을 2000 표본 × 4 segment 로
집합 수준에서 과대근사한 뒤 **유한 표본화**하고 (실측 실현가능 witness 중앙값 2504),
그 **표본** 종점들이 finisher 정점의 원뿔 (**slice 0: 반각 0.212 rad · 밴드 [0, 8.22] m /
slice 2: 0.273 rad · [0, 6.33] m** — **셀 의존이다**) 안에 드는 비율(`v_shot_soft`)과
**표본 전부가** 드는지 여부(`v_shot_worst`)를 계산한다. **연속 집합 전체에 대한 보장은
아니다.**
`v_shot_soft ≥ 0.9` 이고 정책이 FIRE 를 내면 그 틱에 포획 결과가 **동결**되고, 8 틱 뒤
그 동결값이 적용된다. 그 사이 침투는 매 틱 검사된다. limiter 는 반경 0.75 m 안에서
접촉 사건을 만들고 (접촉은 기하 검사를 정의상 통과한다), 자산 6 m 안이면 **거부권으로
기폭이 보류**되고 밖이면 `Bernoulli(1.0)` 으로 하드킬이 된다. 예측 커밋 경로는 여기에
`τ_kill = 3 틱` 지연과 별도 기하 문턱이 붙지만, 실측상 **접촉 resolver 가 먼저 판정을
끝내므로 커밋 경로는 지배적이지 않다** (C033). **그물·공력·잡음·지연·자세동역학은
계산되지 않는다.**

### 무엇이 물리적 근거이고 무엇이 우리가 정한 가정인가

**물리 근거**: 점질량 적분 자체. 도달집합의 과대근사 성질. 원뿔 기하. 그 이상은 없다 —
"3DOF" 라는 말이 항공역학 3DOF 를 뜻한다고 읽으면 안 된다. 실제는 **가속 명령 방향이
무제약인 등방 double integrator + 동역학적으로 결합되지 않은 율제한 지향축**이며,
코드 자신이 `point-mass-plus-heading` 이라 부른다. 추력축 정렬·받음각·비행경로각 제약이
전부 없다.

**문헌에서 뽑았다고 기록된 앵커**: `net_radius` 1.77 (Xu 논문 C 역산의 최악방향 하향) ·
`a_att` 하한 11 · `att_speed` 하한 8 · 능력비 0.35/1.00 · 기체 선회율 2 rad/s ·
LiDAR 10 Hz. **단 그 근거 문서들이 스스로 "AI 추출 DRAFT · 비준 전 논문 인용 금지" 를
달고 있고**, Xu 앵커는 테스트 자신이 "an anchor, not independent evidence" 라 적었으며
hang time 재현은 약 23% 과소예측으로 잠겨 있다.

**나머지는 전부 우리가 정한 것이다.** τ₀ 의 합성, kill_radius 의 합성, 위협 상한
78/30, A2 의 7 항 계수, dt, 지평선, `p_kill = 1.0`, 회랑 기하, 동시발생 우선순위,
소진 limiter 주차 좌표. `params.py` 의 STATUS 를 세면 **`ASSUMED` 가 다수**다.
그리고 이 사슬 전체의 상류에 **A1 (Xu 유효면적의 기준 시점) 이 미확인 단일 실패점**으로
서 있다.

### 좋은 학습 결과가 나오면 정확히 무엇을 알아낸 것인가

사전등록 3 조건(행 12/14 · 각 slice 5/7 · 전역 paired CI 하한 > 0, seed 다수결 위)을
통과했다면 알아낸 것은 **하나**다:

> **이 봉인된 축소차수 세계에서, A2-nominal 단일 공격자에 대해, 고정 θ_fire admissibility
> 아래, 학습된 limiter 조향이 clean net capture 술어의 성립 경계 χ50(η, λ) 를
> rule-based 대비 밀었다.**

`P(FIRE|χ)` 와 `P(N|FIRE, χ)` 를 함께 보고하면 **경계 이동이 어느 항을 통해 나타났는지
기술**할 수 있다. **단 이 분해는 원인을 분리하지 않는다** (r2 정정): 조건부 성공률은
분모 집합의 **구성 변화**만으로도 움직이므로, "조향이 좋아졌다 / 발사 판단이 좋아졌다" 는
**이 두 수만으로는 판별되지 않는다.** 인과 분리에는 별도 설계 (발사 시점을 외부에서
고정한 arm, 또는 propensity 보정) 가 필요하다.

그리고 두 가지 전제가 먼저 해결돼야 이 문장 자체를 쓸 수 있다:
**① `Δχ50` 계산기가 아직 없다** (U-14) — 지금 상태로는 그 수를 낼 수단 자체가 없다.
**② arm 효과는 NET 단계에만 존재한다** (§3.3) — KINETIC 구간에서 두 arm 은 동일하다.

### 그 결과가 나와도 아직 무엇은 알 수 없는가

협력이 **필요한지** (V-9) · 이득이 **협력 기하 때문인지** (V-8) · 다른 공격자에게도
같은지 (V-20) · 잡음·지연·구동기 하에서도 같은지 (V-21) · **실제 기체가 그 기동을 낼 수
있는지** (V-19) · 그리고 **그물이 실제로 기체를 무력화하는지** (V-18). 마지막 항목은
이 모델이 원리적으로 답할 수 없으며, 시뮬레이터의 성공 라벨과 현실의 손상·안전성
사이의 간극은 **하드웨어 증거로만** 메워진다. 이 프로젝트에는 그 증거가 **하나도 없다.**

---

## 부록

### 부록 A. 실행 스택 한 장 요약

```
ThreatObsEnv            위협등급 2차원을 관측 뒤에 붙임 (참값, 무오차)
  └ ModeSystemEnv       커밋 제안 수집 · NK 거부권 · Bernoulli(p_kill) · 접촉 resolver
                        · net-miss handoff · M4 terminal 보상 · 결과 라벨
      └ ShapingParallelEnv   도달집합 v_shot · FIRE 게이트 · FSM · 조밀 보상 J_env
          └ AdversaryOverrideBackend   A2 스크립트 공격자 주입 (백엔드 프록시)
              └ AnalyticBackend        점질량 + 지향축 적분
```

### 부록 B. 변수 사전 — 관측 벡터 65 차원 전체

인덱스는 0-based. 좌표계 **월드 관성계**, 단위 SI, **정규화 없음** (마지막 2 성분 제외).
갱신 시점은 전부 **이동 후 (post-move)** (`env.py:389-391`).

| 인덱스 | 성분 | 물리적 의미 | 단위 | 접근 주체 | 비고 |
|---|---|---|---|---|---|
| 0–35 | limiter i ∈ {0..3} 의 `[p(3), v(3), e(3)]` | 위치·속도·지향 단위벡터 | m, m/s, – | 전 방어자 | i ≥ 실제 기수면 `zeros(9)` padding. **소진 limiter 는 `PARK_POSITION = (0,0,60)` 으로 주차되어 그 좌표가 그대로 실린다** |
| 36–44 | finisher `[p, v, e]` | 〃 | 〃 | 전 방어자 | `a_max = 0` 이므로 p, v 는 사실상 상수 |
| 45–53 | adversary `[p, v, e]` | 공격자 **참값** 위치·속도·지향 | 〃 | 전 방어자 | **추정값 아님** (§3.4) |
| 54 | `k_norm` = k / K | 잔탄 비율 | – | 전 방어자 | K = 1 이므로 {0, 1} |
| 55–58 | FSM 상태 one-hot | LOADED / DEPLOYING / LOCKED / SPENT | – | 전 방어자 | **mission mode bit 의 실체** — 신규 배선 불요 |
| 59 | `fsm.timer` | 현 단계 잔여 카운트다운 | s | 전 방어자 | |
| 60 | `v_shot_soft` | **검사한 실현가능 표본** 중 포획되는 **비율** | – | 전 방어자 | **포획 확률이 아니다** (C011). FIRE 게이트의 입력 |
| 61 | `v_shot_worst` | **검사한 실현가능 표본 전부**가 포획되면 1, 아니면 0 | – | 전 방어자 | robust judge — 포획 동결값의 근거. **"모든 실현가능 탈출" 이 아니다**: 보장 대상은 표본 집합이다 (§5.1) |
| 62 | `p_feasible` | no-go 필터 통과 표본 비율 | – | 전 방어자 | `1 − p_limiter_blocked` |
| 63–64 | 위협 등급 특징 | `a_att_max`, `att_speed` 를 bracket [11,78]·[8,30] 로 [-1,1] 선형사상 (클립 안 함) | – | 전 방어자 | **에피소드의 참 위협 등급, 무오차** |

**평가자 전용 (관측에 없음)**: 에피소드 누적 contact 집합 · `first_contact_t` ·
`first_engage_t` · `n_engage` · `net_spent_step` · `hard_kill` · `CommitRecord` 전체 ·
`veto_events` · telemetry.

### 부록 C. 파라미터 장부

#### C.1 현 운용점의 핵심 상수 — 출처 추적

값은 **L2/L3 (현재 운용점)** 기준. L1 동결값과 다르면 괄호로 병기.

| 항목 | 값 | 단위 | 출처 | 선택 이유 | 검증 지위 |
|---|---|---|---|---|---|
| `net_radius` (ρ) | **1.77** (L1 2.0) | m | Xu 2025 Eq.12 보고값 C 역산 `S_NP = 12.54 m²` → 등가면적 반경 1.997 (docs/39 Table 8 역산·Table 3 검증) → **최악방향 내접반경으로 하향**: `내접/등가 = 0.888` → **1.77** | 포획 판정이 도달집합 **전체** 포함을 요구하므로 구속하는 것은 최악방향 | **부분 확인 — 그리고 낙관 상한**: 측정된 0.888 은 완전 정사각형 값 0.886 과 거의 같은데 이는 flat-init 탓이며 **참 비는 그 이하**. `m4_config` 가 "마지막 남은 미정량 낙관 항목" 으로 자기 기록 |
| `tau_deploy` (τ₀) | **0.30** (L1 0.4) | s | **분해 선언**: flight 0.15 (Xu Fig.6 개방 0.13 s + dt 격자 반올림) + sense 0.10 (Pliska RA-L / *Drones* 10(6):420, LiDAR 10 Hz 1주기) + decide 0.05 (1틱) | **`m4_config` 자신의 방어 논거**: "각 항이 외부 문헌 값이라 우리 자유도가 아님 · 제외항(slew, 카메라 5 Hz)이 τ 를 키우는 방향이므로 0.30 은 하한" | **〈출처 확인〉 부분** — 세 항의 출처 기록은 있다. **그러나 위 방어 논거는 증명이 아니다** (r2 정정): 문헌값의 **선택 · 결합 · 현 모델로의 적용**에는 연구자 가정이 들어간다. 따라서 **"0.30 은 하한" 은 주장이며 확인된 사실이 아니다.** 게다가 slew 는 제외항이 아니라 실제로 구속한다 (§4.3), `sense` 는 구현되지 않았다. `m4_config` 가 이 항목을 "self-serving 으로 보일 수 있다" 고 스스로 적음 |
| `kill_radius` | **0.75** (L1 2.0) | m | 기하 유도: 표적 반치수 0.21 (420×420 mm) + 요격기 반치수 ~0.25 + 종말 유도오차 0.10~0.40 = **0.56~0.86**, 중앙값 채택 | 기존 2.0 은 "no external grounding" 이었고 부피로 12~46 배 관대 (3제곱 지렛대) | **부분 확인** — 구성 항은 문헌, 합성은 우리 선언. **{0.6, 0.75, 0.9} 선언된 sweep 축** |
| `cone.range_max` (R_max) | **8.22 (slice 0) / 6.3258 (slice 2)** (L1 29.847) | m | **τ 선언의 귀결**: 콘 축방향 밴드는 "네트가 실제로 간 거리" 여야 한다 → baseline 병진 **8.22 m @ τ_flight = 0.15 s** (`prototypes/net_forward`). sense/decide 지연은 발사 **전**이라 네트 병진에 안 들어감 | L1 29.847 은 붕괴 타이밍 기반(자체 WEAK/FLAGGED)이라 τ 와 무관했고, 그 결과 **네트가 닿을 수 없는 15 m 표적을 포획으로 판정**했다 (게이트에서 hold/ring/intercept 전부 24/24 NET_CAPTURE) | **부분 확인** — 유도 사슬 명시적이나 상류 A1 에 의존 |
| `cone.half_angle` | **0.21209 (slice 0) / 0.2728 (slice 2)** | rad | `arctan(ρ / R_max)` — slice 0 은 arctan(1.77/8.22), slice 2 는 arctan(1.77/6.3258) | 유도값 — 자유 파라미터 아님. **λ = R_max/ρ 가 격자 축이므로 두 값이 달라야 한다** | **확인** (`r2a_stage1.py:77`) |
| `theta_fire` | 0.9 | – | `fire_gate_calibration.py` 가 정확 해석 라벨 대비 zero-wasted-shot 밴드 [0.85, 1.0] 산출, 권고 0.925 | 0.9 는 밴드 안. legacy 0.8 은 밴드 **아래** | **확인 (CALIBRATED)** — 단 자기 시뮬 대비 보정 |
| `omega_max` (finisher) | **2.0** (L1 3.14159) | rad/s | Pliska 실기 **기체** 선회율 2 rad/s | L1 값은 π 를 그대로 쓴 것 — 물리 근거 아니었음 | **부분 확인** — 앵커는 기체 선회율이고 **네트가 기체 고정**이라는 가정 하에서만 지향 slew 와 같다. 실측: hold 0.0% 구속, **ring 44.8% 구속**. **{1.5, 2.0, 3.0} sweep 축** |
| `limiter_omega` | 2.5 (L1 12.0) | rad/s | Pliska 2 rad/s 대비 finisher 여유 | L1 근거는 "demo-proven" = 데모가 돌았다는 뜻 | **부분 확인** — 1.9% draw 에서 **추가 구속** (불리한 방향, 의도 아님, 그대로 둠) |
| `a_lim_max` | 0.35 × a_att | m/s² | Pliska RA-L 실기: 요격기 4 vs 표적 11 → **비 0.36** | 문헌이 준 것은 절대값이 아니라 **비율** | **부분 확인** — 기존 1.00 배는 방어자 과대평가 |
| `limiter_v_max` | 1.00 × att_speed | m/s | Pliska: 8 vs 8 → 비 1.00 | 〃 | **부분 확인** |
| `THREAT a_att` | **[11, 78]** | m/s² | **하한 11 = Pliska 표적 실측 최대가속** / **상한 78 = 선언** (5인치 FPV 급, docs/31 §4 "AI 추출 DRAFT") | 점값(30)이 근거 없어 브래킷 랜덤화로 대체 | **하한 확인 / 상한 미확인** |
| `THREAT att_speed` | **[8, 30]** | m/s | **하한 8 = Pliska 표적 실측 최대속도** / **상한 30 = 선언** | 문헌 실험 표적은 4~8 m/s | **하한 확인 / 상한 미확인** |
| `x_fire` | 16.0 (L1 11.0) | m | 요구 이격 = 8.22 + 20×0.30 = 14.22, finisher x=2 → 16.2 → 16.0 | **scripted baseline 트리거 전용 — 학습 정책은 쓰지 않는다** | 유도 확인 |
| `dt` | 0.05 | s | 20 Hz 관례 | τ 를 dt 격자 위(6틱)에 올려 양자화 해소 | **(규약)** `ASSUMED` |
| `p_kill` | 1.0 | – | **선언된 sweep 축** | lethality calibration 아님 (C015) | **(규약)** |
| `tau_kill` | 0.15 | s | sense(0.10)+decide(0.05) 사슬 재사용 | dt 격자 위(3틱). 하드킬을 **약화**시키는 방향 | **부분 확인** — **{0.15, 0.20} sweep 축** |
| `r_nk` | 6.0 | m | no-kinetic zone 반경 | 자산 근처 파괴적 요격 금지 doctrine | **(규약)** |
| `episode_len` | 160 step (8 s) | – | 스폰 랜덤화 후 TRUNCATED 수렴 실측 (80→43%, 160→2/30, 320→2/30) | **부기 파라미터이지 물리 주장 아님.** 늘리는 쪽이 정직 (스폰 축소는 금지) | **(규약)** — 근거는 자기 측정 |
| A2 `jink/route/dodge/sense` | 0.6 / 0.5 / 1.8 / 30 m | – | — | 봉인된 A2-nominal 점 | **(규약)** — 외부 근거 없음 |
| `n_samples` | 2000 | – | 2A′ spike: n=500 에서 err_max 0.190 > zero-waste 밴드폭 0.15 → 불안전 | 게이트 근처 수치 안정성 | **확인 (CALIBRATED)** |
| `adversary_omega` | 10.0 | rad/s | 브래킷 최악 모서리(a=78, v=8)에서 필요 ω = a/v = 9.75 < 10 | 4000 draw 전수 검사에서 **구속 0.0%** | **확인 — inert** |

#### C.2 dead / inert 파라미터

| 항목 | 상태 | 근거 |
|---|---|---|
| `env.capture_thresh = 0.95` | **DEAD** — 저장만 되고 읽히지 않음 | docstring 과 실제 규칙 불일치 |
| `env_frozen.adversary_omega_att_max = 8.0` | **DEAD** — 스크립트 정책이 받지만 안 씀. 실제 slew 는 백엔드 10.0 | `env_adv.py:112` 주석이 "DEAD 이지만 동일하게" |
| `attitude.e_net_init` | **INERT** — 백엔드가 `[1,0,0]` 하드코딩 | 2026-08-08 감사 C6 |
| `viability.seed` | **INERT** — 런타임은 스텝별 seed 를 명시 인자로 받음 | 〃 |
| `baselines.headline_u0` / `coma_u0` | **INERT** — env 가 `layout.limiter_p0` 하드코딩 | 〃 |
| `viability.turn_limited` | **RESERVED** — 파싱되나 env 경로 미배선 | `params.py` |
| `scripted.finisher_slew_cmd` (Box(5) idx3) | **RESERVED** — 수신 후 무시 | 〃 |
| `adversary.repel_margin_default = 1.5` | **미실행** — 동결 env 가 1.0 으로 덮어씀 | 〃 |

#### C.3 한 셀의 완전한 파라미터 해석 재생 (`r00c0`)

```
PYTHONIOENCODING=utf-8 python -c "
from shepherd.scripts.b2_manifest import load
from shepherd.scripts.b2_run import scenario_kwargs, _index
m=load(); c,b=_index(m); cell=m['cells'][0]
print(scenario_kwargs(m, cell, m['units'][0]['s_lo']))"
```

### 부록 D. 금지 어휘 목록 (문서 전체 규율)

| 쓰지 말 것 | 대신 |
|---|---|
| "협력 효과" | **limiter-control opportunity** |
| C arm 을 "upper bound" | **search-based attainment benchmark** |
| "cooperation-is-meaningless is rejected" / "exploitable cooperative geometry" | C049 문안 |
| "robustness demonstrated" / "민감도 검증 완료" / "추가 민감성 없음" | "clean candidate 없음으로 screen 종료" |
| "net 이 물리적으로 실현돼 있다" (단독) | "fire-time viability horizon 과 지연 outcome-resolution timer 두 기제로 구현" |
| "terminal failure" (C_illegal) | **irreversible failure latch** (outcome/credit rule) |
| "학습 컨트롤러가 게이트 censoring 을 해소" | 금지 — 게이트는 고정 admissibility |
| "포획 확률 0.9" (v_shot_soft) | "실현가능 탈출 중 포획 표본 비율" |
| "상한의 몇 % 회수" (R_rec) | "search benchmark 대비 상대 위치" |
| "body-rate low-level MARL" | **high-level guidance policy** |
| "airframe-level realizability" | engagement/guidance-level cooperation |

**r2 추가 — 비관 쪽 과장도 금지한다** (이번 개정에서 실제로 걸러낸 표현):

| 쓰지 말 것 | 대신 |
|---|---|
| "포획 판정은 보수적이다" · "모든 실현가능 탈출이 포획된다" | "검사한 witness 집합 안에서는 탈출이 없었다" |
| `P(N\|FIRE)` 상승 = "발사 후 달성도 개선" | "발사된 에피소드 집합에서 조건부 성공률이 높아졌다" |
| "관측이 full-state 이므로 CTDE 이점이 없다" | "공통 관측을 제공한다" (여기까지) |
| `flight` 성분이 "물리적으로 실현됐다" | "타이머 규약으로 구현됐다" |
| "τ₀ = 0.30 은 하한이다" (단정) | "`m4_config` 가 하한이라고 주장한다 — 증명은 없다" |
| "노트와 산출물 수치가 갈린다" (측정 시점 확인 없이) | 측정 시점을 먼저 대조한 뒤 판단 |
| 효과 **미검출**을 "정반대 결과" 로 | "한 셀에서만 검출됐다" |
| 탐색 자료로 평가 위치를 정한 설계를 "순환" 으로 | 재사용된 자료·판단을 구체적으로 지목하거나 판정 보류 |
| "현재 결과는 재현 불가" (전체) | "해당 B2 작업 트리를 지정 커밋만으로 복원할 수 없음" |
| "학습 스택은 한 번도 검증되지 않았다" | "확인한 실행에서는 수행되지 않았다" |
| 소표본 0 회 관측을 "예외가 아니라 규칙" 으로 | "검사한 표본에서 관측되지 않았음" |

### 부록 E. 참조 문서

| 문서 | 지위 |
|---|---|
| `artifacts/b0/b0_v3_world_contract.json` | **기계 정본** (world contract) |
| `docs/94_b0_v3_world_contract_draft.md` | **서술 정본** (SEALED) |
| `docs/102_b2_scripted_prereg.md` | B2 봉인 사전등록 |
| `docs/89_research_plan_r2_hybrid_marl.md` r4 | 달력·학습 스펙 정본 |
| `docs/91_delay_inventory.md` v2.1 | 시간 구조 정본 |
| `docs/92_layer1_sensitivity_candidates.md` | 층1 screen |
| `docs/93_airframe_transportability_gate.md` | 6DOF gate (미봉인 설계 노트) |
| `docs/35 · 38 · 40` | 파라미터 앵커·가정 원장·운용점 선언 |
| `artifacts/audits/claim_registry.tsv` | 주장 54행 + 허용 scope + 금지 문안 |
| `shepherd/params.py` | L1 동결 레지스트리 (+ STATUS 범례) |
| `shepherd/m4_config.py` | L2 운용점 + provenance |
| `temp_research_note/2026-09-14c` | B2 구현 기록 (문서-코드 공백 2건) |
