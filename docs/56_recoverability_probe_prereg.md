# 56 — miss 7판 recoverability probe 사전등록 (2×2 + 별도 switch arm)

**2026-08-06 · 결과를 보기 전에 쓴다. 리뷰 3 후속 계약 2건(early-prep 의미 분리 ·
closed-loop 재실행) 반영. 실행은 다음 세션.**

---

## 0. 질문

V3b 에서 scripted 폴백의 miss 후 무력화가 0/7 이었다 (docs/54). 이 probe 는
그 원인을 분해한다:

> 폴백이 실패한 이유가 (전환 자체가 불가능해서)인가, (miss 확인 후에야 움직여
> 너무 늦어서)인가, (controller 가 약해서)인가?

**결과는 성공률 추정이 아니라 7개 저장 상태에 대한 반증 probe 다.**

## 1. ★ 용어 계약 — "miss−5" 는 조기 handoff 가 아니다

```
T0        기존 계약: net miss 확인(handoff step) 뒤 fallback controller 시작
T−5 prep  handoff step − 5 tick 부터 limiter fallback controller 활성.
          finisher 의 원래 net 발사 결정은 유지 (이미 발사돼 net 은 비행 중).
          = "fallback 선행 준비 / 병렬 pre-positioning". 조기 handoff 아님.
T−5 switch (별도 arm, 2×2 밖) net 전략 자체를 포기하고 destructive 로 완전
          전환. 비손실 기회를 희생하는 다른 정책이므로 2×2 에 섞지 않는다.
```

첫 실행은 **2×2 (T0 / T−5 prep × controller 2종)** 만. T−5 switch 는 2×2
판독 후 별도 사전등록.

## 2. ★ closed-loop 재실행 계약 (고정 궤적 재생 금지)

공격자는 반응형이다. 개입 후 공격자 궤적은 바뀌어야 한다.

```
허용   같은 seed 로 결정론적 재실행 -> branch step 에서 limiter 제어만 전환
       -> 이후 attacker·defender 모두 closed-loop 로 계속 (V2/V3 감사와 동일
       CRN-branch 패턴. 상태 직렬화 불필요 — 재실행이 곧 checkpoint)
금지   원래 miss 에피소드의 공격자 궤적을 고정 + limiter 만 새 controller 로
       이동 (기하적 counterfactual 일 뿐 reactive A2 recoverability 검증 아님)
```

## 3. Arm (2×2)

| arm | 준비 시작 | controller |
|---|---|---|
| T0-INT | 실제 miss 직후 (handoff step) | 기존 intercept |
| T0-ORC | 실제 miss 직후 | privileged oracle/MPC |
| TP-INT | handoff step − 5 부터 병렬 준비 | 기존 intercept |
| TP-ORC | handoff step − 5 부터 병렬 준비 | privileged oracle/MPC |

공통 조건 (전 arm 동일):

- 대상 = V3b hold/clean 의 miss 7판: **ep 2 · 26 · 35 · 46 · 76 · 95 · 98**
  (handoff step 21·21·24·23·21·16·22, `results/handoff_audit.json`)
- `Pk = 1` — **"deterministic lethality 아래의 recoverability upper-bound
  probe"** 로 명시한다. lethality 질문이 아니라 기하 질문이다.
- 동일 contact resolver · 동일 no-kinetic veto · 동일 limiter 소모 계약
  (`contact_resolver=True, miss_terminates=False`)
- net 발사는 원래 규칙(clean) 유지. T−5 시점은 발사 후·해소 전 구간임을
  실측으로 확인해 기록한다 (아니면 그 판은 별도 표기).

## 4. 기록 지표 (판 단위)

```
net capture 여부 · (새) miss 발생 여부와 시각 · contact neutralization ·
commit hard-kill · penetration · 최초 contact 까지 시간 ·
개입 시점의 자산까지 남은 거리 · limiter 별 최소거리와 접촉 순서 ·
limiter 소모 수 · 원래 miss 상태가 개입 후에도 miss 로 남는지
```

★ **분리 라벨**: T−5 prep 개입으로 net 이 맞아 버리면 "fallback 성공"으로
세지 않고 `EARLY_PREP_NET_CAPTURE` 로 분리한다 — limiter 의 조기 움직임이
net 기하까지 바꿨다는 뜻이다.

## 5. privileged controller 자격 (이름만 oracle 인 휴리스틱 금지)

최소 요건 (전부):

- 짧은 horizon 에서 limiter 가속열을 **직접 최적화** (후보열 shooting 가능)
- **attacker 반응을 rollout 에 포함** (cloned env closed-loop)
- 목적함수 = contact/commit 도달 또는 penetration 방지
- backend dynamics 와 action bound 를 정확히 사용 (semi-implicit Euler,
  a_max/v_max clip — `analytic.py:109` 그대로)
- 실패는 `NO_SOLUTION_WITHIN_BUDGET` 으로 기록. **oracle 실패를 물리적
  불가능으로 읽지 않는다** (오류 13 동형).

budget·horizon 등 상수는 구현 시 **실행 전에** 이 문서에 추가 선언한다.

## 6. 해석표 (결과 보기 전 고정)

| 결과 | 허용되는 해석 |
|---|---|
| T0-ORC 0/7 · TP-ORC 성공 | handoff 가 아니라 **시점**이 병목 |
| T0-ORC 성공 · T0-INT 실패 | 기존 fallback controller 가 약함 |
| TP-INT 도 성공 | 값싼 pre-positioning 만으로 회복 가능 |
| 개입 후 net capture 증가 | fallback 뿐 아니라 shaping/net 기하가 바뀜 (`EARLY_PREP_NET_CAPTURE`) |
| 전 arm 실패 | **해당 7개 상태에서** recoverability 결손 증거 강화 (일반화 금지) |
| 일부만 성공 | 상태별 recoverability 이질적 — 단일 "mode change 가능/불가능" 결론 금지 |

## 6.1 결과 라벨 3분법 (합산 금지)

```
EARLY_PREP_NET_CAPTURE      조기 준비가 애초에 net miss 를 없앰 (net 기하 변화)
POST_MISS_NEUTRALIZATION    miss 후 폴백이 살림 (contact / commit hard-kill,
                            net_spent=True 에서만)
PRE_MISS_NEUTRALIZATION     (2026-08-06b 추가 선언, 실행 전) T−5 prep 구간에서
                            net 해소 **전에** 접촉 무력화가 난 경우 -- miss 가
                            발생하지 않았으므로 "miss 후 폴백" 과 합산 금지
PENETRATED                  실패
```

"조기 준비가 fallback 을 살렸다" 와 "조기 준비가 miss 자체를 없앴다" 는 다른
주장이다 — 절대 한 칸에 합치지 않는다. 이번 probe 의 지위는 **"저장된 7개
miss 상태에서 deterministic lethality 를 가정한 recoverability 반증 실험"**
이며 성공률 추정·일반 mode-handoff 성능 평가가 아니다.

## 6.2 목적함수 계약 — proxy 와 최종 판정 분리

optimizer 내부 proxy 를 "접촉 거리 최소화" 하나로 두지 않는다 (자산 반대편
꼬리 추격도 좋은 해로 평가되는 결함). **최종 성공 판정은 반드시 실제 env
replay 의 terminal 라벨** (`NET_CAPTURE / CONTACT_NEUTRALIZATION /
COMMIT_HARD_KILL / PENETRATED`) 로 하고, proxy 점수는 후보 선택에만 쓴다.

## 7. ★ 실행 환경 격리 게이트 (리뷰 3 후속 — 재현성 최대 위험)

**이번 세션(2026-08-06)의 모든 감사·회귀는 dirty tree 위에서 실행됐다**:
HEAD `0450c74` + 이전 세션 미커밋 변경 8파일 (+282/−16, `env.py`·`viability.py`
포함). patch 는 세션 내내 불변이었으므로 세션 내 비교(P78 pre/post 등)는
유효하다. 스냅샷 = `artifacts/pre_oracle_worktree_2026-08-06.patch`
(sha256 `f402b0c4…d163e6fb`, meta 동봉).

2×2 실행은 다음 중 하나로만 한다:

```
권장   0450c74 에서 clean branch/worktree 생성 -> oracle 구현 -> 2×2 실행
차선   혼재 유지 시, 실행 직전에 git rev-parse HEAD · status · diff --stat ·
       diff > patch 를 다시 뜨고, 결과 JSON 에 다음을 필수 기록:
       HEAD commit · dirty 여부 · patch sha256 · config · solver seed ·
       budget 상수
```

## 7.1 privileged controller 상수 선언 (2026-08-06b, ★ 결과 보기 전 고정)

**분기 정의**: `t*` = `net_miss_handoff` 관측 loop index (V3b 재현으로 재확인).
개입 시작 s0: **T0 = t*+1** (miss 확인 후 첫 행동) / **T−5 prep = t*−5**.
s0 부터 limiter 4기의 행동만 controller 가 낸다. finisher·공격자·발사 규칙은
원 계약 그대로.

```
planning horizon          H = episode_len(80) − s0  (잔여 전 구간, open-loop 1회
                          계획 — 모형이 정확 클론이므로 replan 불요, 실행=계획)
action parameterization   limiter 4기 × K=4 구간 piecewise-constant 가속.
                          각 구간 벡터 = a_lim_max · u, u ~ 단위공 내 균일
                          (‖a‖ <= a_lim_max 구조적 보장, backend clip 그대로)
population                P = 64 / iteration (구조 후보 2개 포함: 전-구간
                          lead-intercept 유도 · hold)
optimizer                 CEM, I = 2 iterations (elite 16 = 25%, 정규분포 재적합)
solver seeds              S = 3 (rollout 후보 샘플링 rng 만 관장)
evaluation budget         P×I = 128 rollouts / (episode, arm, seed);
                          arm 당 총 384. wall-clock 기준 금지, 결정론적 count 만
lexicographic objective   L1 무력화 달성(1/0) ≻ L2 침투 회피(1/0) ≻
                          L3 최초 무력화 시각(이를수록 우수) ≻
                          L4 swept 최소거리 min (동률 tie-break 전용 —
                          단독 목적함수 금지: 꼬리추격 결함 방지)
proxy / final 분리        proxy = 경량 클론 rollout 의 위 점수 (후보 선택 전용).
                          final = 선택 계획을 full-fidelity env 로 replay 한
                          terminal 라벨 {NET_CAPTURE, CONTACT_NEUTRALIZATION,
                          COMMIT_HARD_KILL, PENETRATED, TRUNCATED} 만 인정
NO_SOLUTION_WITHIN_BUDGET 384 rollouts 안에 L1=1 후보 없음. 그래도 최량 proxy
                          후보를 final replay 하고 그 라벨을 별도 기록
privileged 정보           (i) 전 에이전트 진상태 p·v·e (공격자 포함)
                          (ii) 정확한 시뮬레이터 클론 (A2 결정론 phase 포함)
                          (iii) 미래 반응 rollout. 이 셋 외 접근 금지
closed-loop 조건          rollout·final replay 모두 공격자는 실제 A2 코드로
                          매 스텝 재계산. 궤적 고정 재생 금지 (§2)
경량 클론                 rollout 은 viability n_samples 축소 클론 사용.
                          근거: A2 는 bait_privileged=False 라 v_shot 비의존,
                          발사 후 FSM 은 v_shot 을 읽지 않음 -> 발사 후 dynamics
                          는 v_shot 무관. **P83 자기검사로 강제**: 원 행동
                          재생 시 공격자 궤적이 full env 와 bit-identical
```

**★ 구조적 예측 (결과 보기 전)**: capture 는 **발사 시점에 동결**된다
(`env.py:320` `_pending_capture` = fire 순간의 robust judge). 7판 모두
fire step < t*−5 로 실측되면 `EARLY_PREP_NET_CAPTURE` 는 이 env 계약에서
**구조적으로 도달 불가**다 — 그 경우 해당 칸은 "관측 0 = 검정 불가(계약상
불가능)" 로 보고하고, 성공/실패 어느 쪽으로도 세지 않는다. fire step 은
판별로 실측해 기록한다.

**★ 구조 사실 (P83e 첫 실행이 발견, 2×2 이전 기록)**: env 는
`repel_margin=1.0` 하드코딩(env.py:346) → 공격자의 limiter 반발 발동 반경 =
`1.0 × kill_radius = 0.75 m` = **접촉 반경과 동일**. 따라서 이 env 계약에서
공격자 궤적은 접촉 반경 밖 limiter 위치에 의존하지 않는다 (V3b 의
hold/intercept 궤적 동일의 구조적 원인). closed-loop 재계산은 매 스텝
수행되며(§2 준수), 이 사실은 probe 해석에 반영한다: **회복 문제가 사실상
"준-개루프 공격자 궤적에 대한 추격 도달성"으로 축소**되고, 접촉 직전 1스텝의
반발만이 회피로 작동한다.

## 7.2 자격 자기검사 (P83 계열 — 실패 시 2×2 실행 금지)

```
P83a  동일 seed -> 계획·결과 결정론적 동일
P83b  후보·실행 가속 bound 위반 0 (파라미터화 구조 보장 + 실측 확인)
P83c  intervention off -> V3b 원 replay 재현 (라벨·steps 동일)
P83d  경량 클론 상태이식 후 원 행동 재생 -> full env 와 공격자 궤적 bit-identical
P83e  limiter 를 repel 반경 안으로 넣으면 공격자 궤적이 재계산되어 달라짐
P83f  budget 소진·L1 후보 없음 -> NO_SOLUTION_WITHIN_BUDGET 플래그
P83g  분류는 proxy 점수가 아니라 final env 라벨만 사용 (API 분리)
```

## 8. 실행 전 체크리스트

```
[x] 전체 회귀 476/0 + legacy baseline (hold n=500) 비트 동일 (2026-08-06)
[x] worktree 혼재 스냅샷 (artifacts/pre_oracle_worktree_2026-08-06.patch)
[ ] clean worktree (0450c74 기준) 생성 -- 권장 경로
[ ] privileged controller 구현 + §7.1 상수 선언 + 자격 자기검사
[ ] T−5 가 발사 후 구간인지 7판 실측
[ ] 2×2 실행 → §6 해석표 + §6.1 3분법으로만 판독
[ ] (그 뒤) T−5 switch 별도 사전등록
```
