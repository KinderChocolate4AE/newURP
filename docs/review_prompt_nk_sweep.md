# 외부 리뷰 요청 4 — NK 의미 감사 + 발사 후 latest-start sweep

> 그대로 붙여 넣어 쓴다. 리뷰어는 리포·이전 대화 접근이 없으므로 자기완결적으로 썼다.

---

당신은 다중 에이전트 강화학습 논문의 **비판적 외부 리뷰어**다. 우리는 지난
리뷰에서 "net miss 후 폴백 실패의 원인을 분해하라"는 지시를 받아 두 가지를
했다: (1) event 의미론 감사, (2) 개입 시점 sweep. 결과가 우리 서사에 **너무
깔끔하게 들어맞는다** — "폴백 문제는 사실 발사 전 문제였다"는 결론은 다음
단계(MARL/3-way)로 자연스럽게 이어지는, 우리가 듣고 싶던 이야기다. 이번
요청의 핵심은 이것이다.

> **우리가 편한 결론으로 수렴하기 위해 탐색을 일찍 멈췄는가?**

동의해 주는 답은 쓸모가 없다. §6 의 주장 넷을 각각 무너뜨려 봐라.

## 1. 시스템 (요약)

무인기 방어. 반응형 스크립트 공격자 1기(A2, 최대가속 ~77 m/s²), 방어측:

- **limiter 4기** — 자유 이동 (a_max ~27 m/s²). `kill_radius = 0.75 m` 는
  코드 주석상 "explosive kamikaze kill-radius" — 반경 진입 시 Bernoulli(Pk)
  로 요격 해소. backend 에 충돌 물리는 없다 (기체 상호 관통).
- **finisher 1기** — 위치 고정, 그물 1발. 포획 성패는 **발사 순간** 대리
  판정으로 동결된다.
- **no-kinetic zone**: 자산 반경 `r_nk = 6 m` 안에서 파괴적 요격 금지 (비준
  근거: 잔해가 지키려는 자산 위로 떨어짐 — 도심 last-mile 법적 제약).
  property P11 "NK 안 HARD_KILL 절대 금지"가 강제 테스트로 잠겨 있다.
- 공격자의 limiter 반발은 **정확히 0.75 m 안에서만** 발동 (반발 반경 = 접촉
  반경). 즉 attacker–limiter coupling 은 접촉 직전에만 존재 — 접촉 밖에서
  limiter 가 어떻게 움직여도 공격자 궤적은 불변이다 (실측 확인).

저장된 표본: net 이 빗나간(miss) 에피소드 **7판**. 이전 실험(2×2: 개입 시점
{miss 직후, miss−5} × controller {scripted intercept, privileged CEM oracle})
은 28/28 침투였고, oracle 이 도달한 접촉 11건이 **전부 NK 안에서 veto** 됐다.

privileged oracle 선언: CEM (population 64 × 2 iter × elite 16 × solver seed
3 = **384 rollouts/point**), limiter 별 4구간 piecewise-constant 가속
(open-loop, replan 없음), rollout 은 실제 공격자 코드 closed-loop, 최종 판정은
full-fidelity env replay 라벨만. 실패는 `NO_SOLUTION_WITHIN_BUDGET`.

## 2. 이번에 한 것 ① — NK–contact 의미 감사

질문: 이미 발생한 "접촉"을 guard 가 거부하는 것은 인과적으로 이상하지 않은가?

**판정 = B (근접 kinetic engagement opportunity, 실충돌 아님).** 근거:

1. `kill_radius` 주석 = "explosive kamikaze kill-radius" (실행 반경)
2. backend 에 충돌 물리 전무 — "충돌"은 물리에서 일어날 수 없음
3. Bernoulli(Pk) = 요격 성공률이지 충돌 물리가 아님
4. veto 시 limiter **미소모** — "기폭 보류"의 인과로만 정합
5. NK 의 잔해 논리가 폭발 요격에 정확히 적용
6. 계약 개정 사전등록 자체가 "발동 조건 확장, 해소는 커밋과 동일"로 선언

따라서 NK veto 의 적용은 비준 정합 → 2×2 해석 유효. 명칭만 부정확
("contact"→"engagement" rename 을 chore 로 등재).

## 3. 이번에 한 것 ② — 발사 후 latest-start sweep

질문: limiter 가 언제부터 움직여야 NK 진입 **전에** 허용된 요격 기하를 만들
수 있는가 (latest recoverable start).

설계: 동일 7판 × s0 ∈ {fire+1, fire+3, fire+4, fire+6, fire+9(=miss 직후)} ×
privileged oracle 만 × Pk=1. **발사 전 개입은 제외**했다 — 선언한 이유:
(i) 경량 rollout 클론의 동역학 동치가 발사 후에만 성립 (발사 전엔 limiter
움직임이 대리지표 v_shot 을 바꿔 발사 시점 자체가 변함) (ii) 발사 전 개입은
"폴백 준비"가 아니라 net 게임 자체의 변경이라 질문이 다름.

결과:

```
35/35 point 전부 PENETRATED · NO_SOLUTION_WITHIN_BUDGET 35/35
latest_recoverable_start = None (7판 전부)
engagement 42건 도달 -- 전부 VETO_NO_KINETIC (42/42)
접촉 도달률: fire+1 5/7 · fire+3 5/7 · fire+4 5/7 · fire+6 7/7 · fire+9 2/7
```

## 4. 우리의 해석 (공격 대상)

1. NK veto 의 R1 적용은 계약상 타당하다 (판정 B).
2. 발사 직후 개입조차 모든 engagement 가 NK 안 → **"발사 시점에 이미 kinetic
   창이 닫혀 있었다"는 가설이 강화**됐다 (인증 아님, budget 한정).
3. 따라서 후행 handoff 문제는 이 표본에서 **발사 전 mode scheduling 문제로
   환원**된다 — 다음 단계는 pre-fire probe (= 3-way 첫 arm).
4. 접촉 도달의 비단조(fire+6 7/7 vs fire+9 2/7)는 상태별 이질성이다.

## 5. 스스로 아는 한계 (이미 문서화)

- 7판·Pk=1·선언 budget 한정. NO_SOLUTION ≠ 물리적 부재.
- 공격자는 접촉 밖에서 사실상 open-loop — 접촉 도달성이 실제 회피형 공격자
  대비 낙관적일 수 있음 (frontier 보고 시 명시 의무 등재).
- miss 표본의 selection: miss 가 나는 판일수록 공격자가 이미 종말 구간.

## 6. 무너뜨려 볼 주장

**주장 1 — "판정 B 는 비준 기록이 지지한다."** 근거 사슬의 핵심이 코드 주석
한 줄(kamikaze)과 "충돌 물리 부재"다. 반론 후보: (a) 충돌 물리가 *없는 것*이
곧 "충돌이 아니라 기회"라는 의미론의 근거가 되는가 — 모델 누락을 의미론으로
승격한 것 아닌가? (b) 판정 A 를 택했다면 (충돌 = 실사건, NK 안 충돌엔 별도
결과 부과) 2×2/sweep 결과가 어떻게 달라졌겠는가 — 판정이 결과 해석을 바꾸는
분기라면 감사가 아니라 선택이다. 검사하라.

**주장 2 — "발사 시점에 이미 창이 닫혀 있었다."** 대안 설명을 나열하라:
(a) **planner 약함**: open-loop 4구간 가속·replan 없음·384 rollouts 는 창이
있어도 못 찾을 수 있다. 특히 "NK 진입 전 요격"은 좁은 시공간 창을 정확히
때려야 하는데, open-loop CEM 이 그런 해를 찾을 표현력이 있는가? proxy L1 이
무력화 자체라 "NK 밖에서 때려라"는 신호가 목적함수에 **없다** — L1 에 NK-밖
조건이 안 들어간 것이 탐색을 NK 안 접촉으로 끌고 갔을 가능성. (b) 비단조
(fire+9 급락)가 상태 이질성이 아니라 **CEM 분산**(seed 3)일 가능성 — 같은
point 를 seed 를 늘려 재실행하면 뒤집히는가? (c) grid 5점이 너무 성긴가?
가장 싼 반증 실험 1개를 지정하라.

**주장 3 — "후행 handoff 문제는 pre-fire scheduling 문제로 환원된다."**
"환원"이 과대 표현인지 검사하라. 이 표본은 miss 판만 selection 한 것이고,
발사 전 개입을 실험하지 않았다. "환원됐다"고 말할 수 있는 최소 증거 기준을
제시하고, 현 증거가 그에 미달하면 허용 가능한 문장을 다시 써라.

**주장 4 — "attacker coupling 한계는 명시로 충분하다."** 반발 반경 = 접촉
반경이면 이 환경의 "양치기(shepherding)" 는 접촉 전 공격자 유도 채널이
없다 — 그런데 프로젝트의 원 연구 질문이 바로 협력 성형이다. 이 한계를
caveat 로 두는 것으로 충분한가, 아니면 원 질문의 검정 가능성 자체를
위협하므로 공격자 모델 수정(반발 반경 확대 또는 회피 반응 추가)이 3-way
**전에** 와야 하는가? 순서 판단을 내려라.

## 7. 답변 형식

각 주장에 대해: **[유지 / 조건부 유지 / 기각]** + 근거 2~3문장 + (있다면)
우리가 다음에 돌려야 할 가장 싼 반증 실험 1개. 마지막에 두 가지를 골라라:
(i) 이 세션에서 가장 위험한 미검증 가정 1개, (ii) pre-fire probe 를
사전등록할 때 반드시 고정해야 할 계약 1개.
