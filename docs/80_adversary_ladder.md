# 80 — Adversary ladder: threat class T0~T4 + 단일축 이동 규율 (선봉인) — 2026-08-13

**지위**: 상시 설계 계약. docs/74 §7 (정의·축·measure 불변) 과 동형으로, **위협
모델의 단계적 동결**을 규정한다. 개별 캠페인은 이 문서의 클래스 하나를 지정하고
그 안에서만 주장한다.

> **★ 명칭 충돌 주의 (필수)**: 코드의 `AttackerSpec.level` 은 이미 `"A1"|"A2"|"A3"`
> 을 **다른 의미**로 쓴다 — A1 = 기본(kill-구 반발 + 커밋 후 dodge), A2 = A1 + 지속
> 횡진동/라우팅, A3 = 발사 유도(bait). 따라서 본 사다리는 **T0~T4** 로 명명한다.
> 문서·논문에서 "A2 attacker" 라고 쓰면 어느 쪽인지 알 수 없다 — **T 표기만 사용**.

---

## 1. 원칙

핵심은 "공격자를 계속 강하게 만드는 것" 이 아니다:

> **defender claim 의 수준이 올라갈 때마다, 그것을 깨뜨릴 만큼 충분히 강한 다음
> threat class 를 하나씩 도입하고, 각 단계에서는 attacker 를 freeze 한 뒤 defender
> 를 평가한다.**

이 규율을 지키면 T0 → T4 는 연구를 흔드는 원인이 아니라 **논문의 robustness
ladder** 가 된다.

**★ 순서의 의미 (오독 방지)**:

> **T0–T4 are ordered by adversary sophistication and available response
> structure, not by guaranteed monotonic difficulty; each higher class is a
> robustness challenge, not a formal dominance relation.**

잘못 학습된 T4 는 T2 보다 약할 수 있고, horizon/objective 에 따라 T3(MPC) 가 특정
기하에서 T1 보다 못할 수도 있다. 따라서 "adversary **strength** ladder" 가 아니라
**"sophistication / information-and-decision ladder"** 다. 논문의 "robust up to T3"
도 *"T3 가 T0–T2 를 dominate 한다"* 가 아니라 *"질적으로 더 풍부한 adversary
class 에서도 시험했다"* 로만 읽는다.

**정보구조 상승 (역할 인지)**: T2 = generic defenders 만 관측 (역할 구분 없음) →
T3 = defender role inference/knowledge 허용 → T4 = learned response. "적은
net-capturer 를 모른다" 는 영구적 현실가정이 아니다 — 반복 교전으로 학습하거나
기체 형상으로 역할을 구분할 수 있으므로, 역할 비공개는 **T2 한정 가정**이다.

## 2. 클래스 정의

| 클래스 | 정의 | 구현 상태 | 용도 |
|---|---|---|---|
| **T0** non-reactive | 목표 방향 전진 + open-loop 사인파 횡진동 (jink). **방어자 미관측** | ✅ `AttackerSpec(level="A2", jink_amp=0.6, route_gain=0)` = legacy | analytic mechanism isolation · 겨냥 병목 설명 · legacy 비교 |
| **T1** reactive-local | T0 + **감지 반경 내 limiter 위치 관측 → 가장 넓은 각도 틈으로 횡가속 편향** (고정 이득). 유일한 사전-커밋 전략 반응이 **단일 모드** | ✅ `route_gain=0.5, sense_range=30.0` (2026-08-13 curve_sweep 재실행) — **단일 점 설정** | **KSAS primary** · defender-aware baseline · B2 discovery |

**★ T1 은 "family" 가 아니라 "configuration" 이다 (문구 규율)**: 이번 KSAS 재실행은
`route_gain = 0.5`, `sense_range = 30.0` **고정 단일 점**이다 (Phase III 캠페인은
`route_gain ~ U[0.2,0.8]`, `sense_range ~ U[15,45]` 의 **분포**를 썼다 — 다른 물건).
따라서 논문 표현은 *"tested local reactive threat **family**"* 가 아니라
**"tested local reactive threat model"** 또는 **"tested angular-gap reactive
configuration"**. 여러 gain/sense-range 를 ensemble 로 돌린 뒤에야 "family" 가
자연스럽다.

**★ T1 의 두 번째 제한 — 시간적 제한 (2026-08-13 측정으로 발견)**: 감지 반경은
시나리오 규모와 함께 읽어야 한다.

| | KSAS 곡선 | Phase III |
|---|---|---|
| 공격자 시작 | x = 24 m | 250–350 m |
| limiter 링 | x = 8 (반경 5) | x = 50 |
| sense_range | 30 m | 15–45 m |
| 함의 | **회랑 전체 < 감지 반경 ⇒ t=0 부터 전 limiter 관측 (사실상 무제한)** | **접근 구간 200–300 m 동안 방어자 미관측 ⇒ 반응이 종말 구간에서만 활성** |

⇒ KSAS 재실행에서 30 m 는 제약이 아니다. 그러나 **Phase III 의 T1 은 "단일 반응
모드" 일 뿐 아니라 "종말 한정 반응" 이기도 하다** — 이전에 H3a("무반응 공격자")
기각 근거로 "route_gain ≥ 0.2 가 전 에피소드" 를 든 것은 **기각 자체는 유효하나
불완전한 서술**이었다 (certificate 가 평가한 engaged 상태는 종말 구간이라 거기선
실제로 limiter 가 보인다). 이 시간적 제한은 **pre-commit shaping (T_lead/B2) 질문에
직접 걸린다**: 공격자가 보지 못하는 구간의 shaping 에는 반응이 없고, 보이기
시작하면 이미 종말이다. B2 설계 시 **sense_range 를 명시적 실험 변수로 둘 것**.
| **T2** richer reactive | 압력 크기에 **연속 비례**하는 heading **+ speed** 조절. scripted, 비학습 | ⬜ 미구현 (게이트7 F-0c 용 설계만 존재, 조건 미충족 보류) | **arXiv robustness** · B2 mechanism stress test |
| **T3** planning | MPC/궤적 최적화 adversary | ⬜ | 국제학회·저널 robustness |
| **T4** learned | self-play 학습 adversary | ⬜ | learned defender 의 robustness 주장 시 |

## 3. T2 설계 원칙 (구현 전 봉인 — 역-허수아비 방지)

> **capture 를 어렵게 만드는 행동을 직접 코딩하지 않는다. attacker 자신의
> 합리적 objective 를 코딩한다.**

```
J_A = w_p · J_asset-progress  +  w_r · J_threat-avoidance  +  w_s · J_smoothness
      (물리 제약: accel/turn 한계 준수)
```

**금지 (이것을 넣으면 evaluation attacker 가 아니라 oracle adversary 가 된다)**:
"net-capturer 와 멀어져라" · "capture feasibility 를 최소화해라" · "defender 가
원하는 heading 의 반대로 가라" — 즉 **우리 certificate 를 알고 피하게 만드는 항**.
이는 후속 worst-case 실험용이지 T2 baseline 으로는 과하다.

**역할 정보 비공개**: T2 는 limiter 와 net-capturer 를 **구별하지 않는다**
(observed defenders → generic threat field). 침입자가 "저것은 단발 net-capturer" 를
완벽히 안다는 가정은 강하다. role-aware adversary 는 **T3 이상의 별도 robustness**.

## 4. 단일축 이동 규율 (가장 중요)

**defender sophistication 과 attacker sophistication 을 동시에 올리지 않는다.**

```
(D0, T1) → (D1, T1) → (D1, T2) → ...
```

먼저 **동일 attacker 에서 defender 개선**을 보고, 그다음 **동일 defender 를 더 강한
attacker 로 stress-test** 한다. 둘을 한 번에 바꾸면 "이전 결과가 틀린 건가, attacker
가 바뀐 건가" 를 구분할 수 없다.

## 5. 지면별 범위 (결과 열람 전 고정)

| 지면 | attacker 범위 | 표현 |
|---|---|---|
| **KSAS 2p** | **T1 까지만** | *"tested local reactive threat family"* — T2 를 넣으면 2페이지가 attacker design paper 가 된다 |
| **arXiv v0** | T1 + **T2 robustness slice** (대규모 캠페인 불필요) | 확인 항목 2개: ① 성립/겨냥 경계가 T2 에서도 대략 유지되는가 ② 종말-창 결론(①-B1)이 T2 에서도 유지되는가 |
| **B2 / MARL** | 사다리 표 필수 (defender × T0..T3) | "MARL 이 T1 문법을 exploit 한 것인지, 실제 shaping mechanism 을 학습한 것인지" 를 구분하기 위해 |

## 6. null 해석 함정 (2026-08-13 재실행에 즉시 적용)

T1 재실행 결과가 T0(legacy) 와 비슷하게 나와도 **"reactivity does not matter" 로
읽지 않는다.** 허용되는 최대 문장:

> *"The tested angular-gap reactive mode did not materially shift the observed
> boundary under this configuration."*

근거: 30판 예비에서 **궤적은 갈라졌는데(19→41 스텝, max|Δp| 1.50 m) 결과 레이블은
동일**했다 — 반응이 궤적을 바꾸면서도 결과를 안 바꾸는 패턴이 실재한다. null 로부터
"반응성 일반" 으로 확대하는 것은 금지.

## 7. 연구 질문의 4층 구조 (이 사다리가 여는 것)

```
physics   : 어떤 state 가 capturable 한가?          ← Phase III-A/게이트10 (상당부분 완료)
control   : defender 가 그 state 를 만들 수 있는가?  ← 게이트7/B1 (terminal 은 불가 확정)
game      : attacker 가 회피 반응해도 만들 수 있는가? ← **B2 부터 본격 개시 (T1→T2)**
learning  : 그 전략을 MARL 이 학습할 수 있는가?       ← 최종
```

앞의 두 층은 상당 부분 닫혔고, **B2 가 game layer 의 시작점**이다. 이 사다리는 그
층을 실험 설계로 만든 것이다.
