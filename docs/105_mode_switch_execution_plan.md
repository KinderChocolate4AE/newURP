# 105 — net–kinetic 전환 연구의 착수 계획: G0 → finite DP → F1-E 첫 그림

- **일자·상태:** 2026-09-18 · **r4** — r0 초안 → r1 레지스트리·스크립트 경로 반영 →
  r2 G0 승인 결정 반영 (kinetic 근접 효과판정 / net 이동 원판 / 위반–거부 회계 분리 /
  attacker cue 차단) → r3 106 r2 반영 (net 포획 구간 = **전개 완료 후**
  `[t_FIRE+τ_aperture, t_spent)` · 세 정책 공유 조준 규칙 G0 고정) → r4
  [106 r3](106_mode_switch_g0_contract.md) 반영 (8.22 m = 전개 완료 시점 계산 병진
  — 실측 유효사거리 아님 · D2 거리 진단 추가; 정본 = 106 r3). 미봉인.
- **상위 질문:** [104 r6](104_next_direction_behavior_predictivity.md)의 net–kinetic mode
  전환에 따른 조건부 최소 달성비용. 본 문서는 처음 실행 가능한 부분만 계약한다.
- **권한 경계:** [89 r4](89_research_plan_r2_hybrid_marl.md)와
  [102](102_b2_scripted_prereg.md)의 B0 v3/B2/stop rule은 변경하지 않는다.
  Track B의 파라미터·정책·seed·산출물은 Track A와 분리하고 결과를 pooling하지 않는다.
- **시간 해석:** “금방 쓸 만한 소재”는 첫 그림으로 질문의 가능성을 빨리 판별한다는
  선정 기준이다. 4주 안에 세계·학습·저널 원고를 끝내겠다는 약속이 아니다.

## 1. 첫 그림이 답할 질문과 답하지 않을 질문

공격기 1대와 net shooter·kinetic interceptor 각 1대가 있는 단일 교전에서,
**net-first, kinetic-first, 관측 상태에 따른 threshold switch**를 같은 저수준
유도기·동일 시나리오·동일 자산보호/안전 기준 아래 비교한다. 비용은 net shot,
kinetic commit 및 허가된 platform sacrifice의 무차원 자원비로 먼저 표현한다.
보호·안전 결과를 비용과 함께 그려, 같은 기준을 관측상 충족하는 영역에서
효과기 선택이 달라지는지 본다.

첫 그림의 정식 명칭은 **F1-E exploratory pilot**다. 이후 G1을 통과한 F1 확인
실험과 구별한다. 첫 그림은 “어느 가정에서 이 소재를 계속 연구할 만한가”와
“구현된 사건 순서가 무엇을 만드는가”를 답한다. `VoDC`, strict recourse
region, 정보 가치, 물리적으로 검증된 최저비용 또는 안전 보장을 답하지 않는다.
비용–성공 곡선보다 **쌍으로 비교한 궤적과 first-hit 사건 그림**을 먼저 본다.

## 2. 착수 순서와 Track A 경계

| 순서 | 산출물 | 실행 장소·의존성 | 끝났다는 기준 |
|---|---|---|---|
| D0 | G0 결정 카드 | 지금, 문서 작업 | §3의 열린 물리·비용·정보·안전 결정을 한 버전으로 고정 |
| D1 | finite-grid DP 스크립트·저장 그림과 검산 | G0 직후, 로컬 NumPy | §4의 tiny brute-force 대조와 null cases 통과; toy 범위가 명시됨 |
| D2 | F1-E 별도 world·scripted 세 정책 | **B2 stop rule 판정 후**, 로컬 | §5–§7의 사건·자원 검사 통과; B0 v3 parity 훼손 없음 |
| D3 | paired rollout의 궤적·비용 그림과 실패 사례 | D2 후, 로컬 | §8의 그림·원자료·manifest 완비; 유망/무효/불명 판정 |
| D4 | G1 승격·재설계·중단 카드 | D3 후 | 필요한 물리 검증 한 축과 독립 확인 실험을 결정 |

D0·D1은 Track A의 B2 서버 실행을 방해하지 않는 작업이다. **D2 구현은 B2 stop rule을
판정하기 전에는 시작하지 않는다.** PASS이면 Track A MAPPO의 서버·인력 우선순위를
지킨다. FAIL이면 89의 봉인된 전환 경로를 먼저 처리한 뒤 Track B에 쓸 여력을
다시 결정한다. 여기서 B2 PASS를 Track B의 과학적 승인으로 오인하지 않는다.
학습된 switch·PFSP·대규모 attacker pool은 D3에서 신호가 확인된 뒤에만 서버 작업
후보가 된다.

## 3. D0 — G0 결정 카드에 반드시 채울 것

결정 카드는 [106 r3](106_mode_switch_g0_contract.md)로 **작성 완료**됐다 — 확정값·
출처·의미 구분은 106이 정본이고, 아래 표는 D0 착수 당시의 요구사항 기록으로 남긴다.

| 결정 | 권장 출발점 | G0에서 반드시 분명히 할 것 |
|---|---|---|
| kinetic mechanism | **sacrificial contact interceptor** 한 종류 | 단순 근접 event인지 물리 impact인지, time-to-go, neutralization 확률/효과, 허가된 platform loss |
| net mechanism | shooter가 실제 projectile net을 1회 발사 | launch state, 비행/개구 시간, active window, post-FIRE 접촉, spent 조건 |
| 자산 | attacker 1, mobile shooter 1, kinetic 1 | limiter를 따로 넣지 않음; 두 방어기의 기동·속도/가속 상한 |
| 탄약·재고 | net 1발, interceptor 1대, episode reset | 발사·commit 즉시 소모인지와 실패 후 남는 선택지 |
| 행동·권한 | `WAIT/SHAPE`, `NET_COMMIT`, `KINETIC_COMMIT` | 최초 mode 전환 기한, 동일 tick 이중 commit 금지, 각 policy의 post-commit fallback 권한 |
| 관측 | 위치·속도 등 사용 가능한 공통 상태로 시작 | attacker latent type·미래 결과를 policy에 누설하지 않음; FIRE/mode cue와 지연은 첫 실험에서 off인지 명시 |
| 공격자 | 기존 A2 계열의 방어자 기동 반응을 첫 후보 | 기존 A2의 `limiters` 입력에 kinetic 1대를 매핑해도 반응이 살아 있는지 검증; 퇴화하면 별도 반응 모델로 명시; cue 반응 미구현 시 적응형 cue 대응 주장 금지 |
| 보호·안전 | 104 §4.2의 배타적 first-hit 분류 | no-kill 경계, 안전 위반, breach와 성공의 same-tick 우선순위, timeout 처리 |
| 비용 | `c_N=1`, kinetic 운용+허가 손실의 무차원 비용비 | 실패·시간 비용 포함 여부, 비용을 outcome penalty로 섞지 않을 것, 원화/달러 주장 금지 |
| 출처 | 기존 repo 상수와 공개 source를 항목별 기록 | 실제 검증값/논문 anchor/임의 pilot 값 구별; kinetic effect 미검증 범위 표시 |

G0에서는 **효과기를 하나의 모델로 고정**하되 근거 없는 `p_kill=1`을 유일한
kinetic 결과로 봉인하지 않는다. 효과 모델의 외부 자료를 못 찾으면 현실적 최소비용이
아니라 “선언된 simulation plant와 효과범위 안의 비용 비교”로 남긴다.
F1-E의 새 상수는 별도 provenance 체계를 만들지 않고 `shepherd/params.py`의
`PARAMS`에 `mode_switch.*` 키로 등록한다. pilot에서 임의로 정한 값은
`Param.status = SYNTHETIC_EXPLORATORY`를 새 provenance 값으로 추가하고
`source`에 가정의 출처·용도를, `where`에 실제 소비자를 적는다. 기존 근거에서
가져온 값은 근거에 맞는 기존 status를 쓴다. `wired`는 실제 연결 경로를
기록한다. 현 `as_config()`가 새 키를 소비하지 않으므로 별도 wiring 전에는
`wired=config`라고 표시하지 않는다. 실행 manifest는 레지스트리에서 읽은
resolved 값과 출처를 스냅샷할 뿐, 별도 `synthetic_exploratory` 태그를 만들지 않는다.

## 4. D1 — finite-grid exact DP 스크립트

**첫 코드 산출물**은 `shepherd/scripts/mode_switch_toy_dp.py`와 저장 그림이다.
계산의 단일 정의원은 테스트 가능한 작은 `shepherd/mode_switch/toy_dp.py`에
두고 실행 스크립트는 입력·그림·결과 파일을 만든다. NumPy만 요구하며 torch나
서버 예약은 필요하지 않다. toy 파라미터도 `mode_switch.toy.*`로 레지스트리에
올리고, 실행 산출물에는 사용한 레지스트리 값·코드 버전·출력 경로를 남긴다.

### 4.1 선언할 유한 문제

- finite horizon, 1D 상대거리 또는 2D 상대위치의 작은 격자, 유한 행동/관측.
- latent attacker branch 2개와 사전 prior, 늦게 도착하는 유한 cue의 likelihood.
  결정자는 실제 branch ID가 아니라 **관측 history 또는 갱신 belief**만 본다.
- net/kinetic의 이산 launch-success·소모·안전 전이. 이 계수들은 **toy 예시값**이다.
- `Π_fixed`는 초기 정보에서 최초 mode를 고른다. 이후 관측으로 기동·발사시점은
  바꿀 수 있다. `Π_rec`는 같은 정보·저수준 제어·fallback을 쓰면서 첫 commit 전
  후기 cue에 따라 최초 mode를 선택할 수 있다. `Π_rec`가 fixed를 복제할 수 있어야 한다.
- 선언한 정책군의 결정적 정책 전부를 기본 범위로 한다. 무작위 정책까지 허용하려면
  별도 계약과 solver가 필요하다.

유한 horizon backward DP에서 `(P_prot,P_unsafe,E[C])`와 필요한 cell별 확률 벡터를
보존한다. `P_prot≥α`와 `P_unsafe≤β`는 큰 벌점 하나로 대체하지 않는다. 작은 toy에서는
정책 전수열거로 DP 결과를 독립 검산한다. Pareto pruning을 쓰더라도 실제 비교에
필요한 cell별 제약과 비용비 전체에서 지배될 때만 후보를 버린다.

### 4.2 완료 판정과 산출 그림

1. 2-step tiny case에서 brute force와 DP의 **도달 가능한 확률–비용 벡터,
   최적값·승리집합**이 일치한다. Pareto pruning을 했다면 보존된 정책 수는
   같을 필요가 없다.
2. 후기 mode-relevant 관측을 전부 가리고 동일한 동역학·저수준 제어·fallback을
   줄 때 두 정책군의 정보상 strict gap은 0이어야 한다. `Π_fixed⊆Π_rec`
   포함관계가 전체 격자에서 성립한다. cue만 제거하고 branch를 알려 주는
   상태 관측을 남기는 것은 정보-null이 아니다.
3. 한 mode가 모든 branch에서 지배하는 null case에서 순위 반전은 0이다.
4. 후기 cue가 식별력을 가질 때의 예시와 cue shuffle/null을 함께 그린다.
5. `B_rec^{oracle,finite}\setminus B_fixed^{oracle,finite}`, mode별 비용순위, 경계
   cell과 모든 toy parameter를 저장한다. strict gap이 0이면 그대로 보고한다.

이것이 **선언한 유한 toy의 exact solve**다. 연속 동역학, F1 projectile net 또는
실제 C-UAS의 불가능성을 인증하지 않는다. `M_N/M_K`를 연구자가 설정하므로
양성 reversal은 만들어낼 수 있다. D1은 104의 T2 정책군·정보구조를 검산하는
상한까지만 쓰며, 그 결과만으로 G2를 통과시키지 않는다. 복잡한 inner/outer
verification 기계장치는 이 유한 경로가 부족하다는 구체적 이유가 생길 때만 연다.

## 5. D2 — F1-E 첫 world의 contract-lite

104 §5.1의 ①–⑥을 최소 형태로 구현하고, ⑦·⑨의 **단일 교전 자원/비용 카운터**와
⑩의 작은 검사 세트를 붙인다. ③(post-FIRE attacker motion과 접촉 갱신)는
반드시 포함한다. ⑧ mode-cue latency, reload/raid inventory, 6DOF, 고충실도
얽힘 물리와 전체 통계 계약은 첫 그림에서 제외한다. 이는 F1 구조를 시험하는
**F1-E**이며 G1을 통과한 F1이 아니다.

| 구성 | 구현 단위 | 첫 버전의 명시적 한계 |
|---|---|---|
| 모바일 shooter | 기존 `mobile_finisher_accel`을 별도 world adapter에서 호출 | 기존 B0 v3 stationary finisher를 조용히 교체하지 않음 |
| attacker | 기존 A2 계열 생성/응답을 새 자산 배치에 맞춰 adapter화; kinetic을 A2의 limiter 입력에 대응시키는 후보를 검사 | 원래 4 limiter용 route law가 1대에서 퇴화할 수 있음; mode cue 반응은 구현·기록한 경우에만 언급 |
| live net | `ready → deploying → active → spent`, **이동하는 원판**: FIRE 시 고정되는 법선 (106 §1.2 **공유 조준 규칙**), 등속 중심, 전개 중 개구 `R(t)` (**deploying 구간 포획 불가** — `R(t)`는 상태 표시일 뿐), 유효시간 만료 시에만 spent (조기 miss 추정 금지) — 106 §1.2 | FIRE 순간 `pending_capture` 동결 금지; 전개/얽힘의 현실 검증 아님 |
| net 접촉 | **전개 완료 후 active 구간(`t_FIRE+τ_aperture ≤ t_cross < t_spent`)**에 표적 상대 궤적이 **원판 평면을 통과**하고 통과점 반경거리 ≤ `R_net`일 때만 capture (tick 사이 통과 보간 포함; 보간 `t_cross`가 deploying이면 capture 아님) — **중심까지의 구면 거리 판정 금지** (106 §1.2) | swept/보간 통과 검사로 tunneling 방지 필요 |
| kinetic | 별도 이동체의 시간·충돌조건·허가 손실/실패 기록 | 기존 근접 `p_kill=1`을 실물 impact로 부르지 않음 |
| mode | WAIT, 첫 NET/KINETIC commit, 실패 확인 후 허용된 fallback | 최초 mode 선택과 post-commit fallback을 구분 |
| 안전·자원 | no-kill guard, first-hit 분류, 1 shot/1 platform 카운터 | episode reset 비용만; raid 절약 주장 금지 |

각 step은 **관측 → 유도·mode 요청 → commit guard → 양측/투사체 적분 →
swept 접촉·breach·unsafe 판정 → first-hit 우선순위 → 소모/기록** 순으로
정의한다. breach 또는 unsafe와 성공이 한 tick에 겹치면 성공을 먼저 세지
않는 보수적 규칙을 G0에 명시한다. 발사 전 예측 게이트가 실제 post-FIRE
성공을 미리 결정하지 못하게 한다. shooter, kinetic, attacker의 실제 상한이
config와 backend에서 일치하는지도 검사한다.

**예상 파일 경계** — 새 namespace를 써서 봉인 코드를 건드리지 않는다:

| 파일 | 책임 |
|---|---|
| `shepherd/mode_switch/world.py` | F1-E 상태, net/kinetic 전이, first-hit·자원 회계 |
| `shepherd/mode_switch/policies.py` | 세 정책과 동일 저수준 guidance/fallback adapter |
| `shepherd/scripts/mode_switch_pilot.py` | 공통 scenario/seed, 비용비 sweep, manifest·원자료 |
| `shepherd/scripts/mode_switch_viz.py` | 사건을 표시한 궤적과 비용–성공 그림 |
| `tests/test_mode_switch_world.py` | §7의 사건 불변식과 중요한 반사실 |

재사용 후보는 `shepherd/agents/mobile_finisher.py`,
`shepherd/agents/attacker_ladder.py`, 기존 scripted intercept/fallback 로직과
`shepherd/params.py`다. 실제 호출 전에 각각이 **1 shooter + 1 kinetic** 배치를
받는지 확인한다. `shepherd/env.py`, `env_sys.py`,
`scripts/mission_rollout.py` 및 B2 runner의 봉인 경로는 수정 대상이 아니다.

## 6. 비교군과 첫 실험 방법

세 정책 모두 같은 초기 자산, 관측 변수, 저수준 guidance, **FIRE 조준 규칙
(106 §1.2 — 관측 기반 결정론 lead + fallback)**, fallback 가능 시점,
no-kill guard와 exogenous scenario/seed를 쓴다.

1. **Fixed net-first:** 최초 효과기를 net으로 정하되 발사시점·기동은 관측에
   반응할 수 있다. net 실패가 확인되면 허용된 kinetic fallback을 사용한다.
2. **Fixed kinetic-first:** 최초 효과기를 kinetic으로 정한다. **kinetic commit 뒤
   net 복귀는 world 규칙(106 §1.4 = 104 §3.2 규칙 5)이 금지하므로 net fallback이
   없다.** 이 fallback 비대칭은 세 정책 공통의 world 전이에서 오는 것이며(숨기지
   않고 결과 보고에 명시), net-first만 kinetic fallback을 가진다.
3. **Threshold switch:** 같은 관측으로 추정한 net 접촉 여유와 kinetic 안전창
   여유를 비교해 WAIT/NET/KINETIC 중 하나를 선택한다. threshold와 사용 변수는
   `mode_switch.policy.*` 레지스트리 항목과 실행 산출물에 기록한다. 미래 참값·latent attacker ID·counterfactual
   성공 결과를 입력으로 주지 않는다.

처음에는 비용비와 net delay/kinetic safe-window 중 **한 축씩** 바꾸고, 정책을
같은 scenario ID로 paired 평가한다. 보고서는 원자료의
`N_safe/K_safe/B/K_illegal/C_unsafe/L_unauth/O_timeout` first-hit count,
net shot 수, kinetic commit/허가 손실 수, **guard 거부·효과 보류 요청 카운터**
(`n_reject_commit`/`n_withhold_effect`, 106 §1.8 — outcome과 별도 회계),
**net capture 거리 진단**(포획 시 **FIRE 시점 shooter 위치** 기준 중심 이동거리
`d_cap`의 값·분포와 `d_net_anchor = 8.22 m` 초과 비율, 106 §1.2 — anchor 구간 밖
외삽 영역 포획의 물리 타당성 진단이며 성공률·비용의 판정 기준이 아니다),
경험적 보호·안전 비율과 비용 벡터를 모두 낸다. 현 계약에서 `K_illegal`은 guard가
구조적으로 차단하고 `C_unsafe`/`L_unauth`는 발생 기제가 없으므로 (106 §1.8)
`P_unsafe≤β`의 자명 충족을 **안전 우위·동일 안전 문턱 하 최저비용의 실증으로
쓰지 않는다.** 같은 경험적 `α,β` 문턱에서 세 정책을 기술적으로 비교할 수 있으나
표본 신뢰경계 없이 “feasible”이나 “최저비용”이라 쓰지 않는다.
원화·달러 대신 `c_N=1` 기준 무차원 비용비의 break-even 후보를 그린다.

첫 비교는 **정보, action authority, fallback 비대칭(위 2번)이 섞인 탐색**이다.
threshold switch가 이겨도 정보 가치·strict recourse gain으로 해석하지 않는다.
계속 연구하기로 결정하면
104 §7.5의 no-late-information, cue shuffle, matched policy-class
대조군을 G1 이후 별도 확인 실험에 포함한다.

## 7. 구현 검사의 최소 세트

- net 결과가 FIRE 순간에 동결되지 않는다. 같은 발사 상태에서 post-FIRE
  attacker 경로만 바꾸면 contact와 miss가 달라지는 사례가 있어야 한다.
- 한 step의 접촉/breach/unsafe가 동시에 일어나도 배타적 first-hit
  결과는 정확히 하나이고, 보호 성공이 위반을 덮지 않는다.
- spent net 재발사와 이미 소모한 interceptor 재사용은 불가능하다.
- no-kill guard는 동일 상대위치에서 kinetic commit을 일관되게 거부한다.
- swept contact를 검사해 net과 target이 한 step 사이에서 통과하는 경우의
  미검출 여부를 확인한다.
- fixed와 switch의 동일 seed는 동일 initial state/attacker exogenous draw를
  쓰고, 달라지는 경로는 정책의 작용 이후로 제한된다.
- **FIRE cue 차단 검사 (106 §1.7):** FIRE 여부만 다르고 공격자·방어자 운동학,
  시간, 난수 상태가 같은 쌍에서 공격자 행동(가속 명령)이 동일해야 한다.
  `react_on_commit=False`만으로는 불충분하다 — A2의 `committed`는 dodge 외에
  jink·bait 게이트에도 들어가므로 `committed=False` 고정과 함께, `net_center`
  (FIRE 무관 운동학 예측식 고정)·`v_shot_soft`(미전달) 등 파생 입력을 통한
  **간접 누설도 같은 검사로 확인**한다.
- 방어기 기동만 바꾼 paired 사례에서 A2의 행동이 실제로 달라지는지 계측한다
  (위 cue 차단 검사와 **별도**). 1대 입력에서 반응이 사라지면 “반응형 공격자”
  사례로 세지 않는다.
- 작은 dt 반감 사례에서 event 순서와 주요 분류가 안정적인지 확인한다.
  불안정하면 F1-E 수치를 결론에 쓰지 않고 적분/사건 순서를 고친다.
- B0 v3 resolved-contract manifest와 B2 실행 파일은 변경되지 않았음을
  diff/해시로 확인한다.

이 검사는 첫 그림을 **정확하게 디버그**하기 위한 것이다. 통과해도
net deployment·kinetic effect의 외부 타당성을 대신하지 않는다.

## 8. D3 판독과 다음 분기

**먼저 볼 그림:** 같은 초기조건에서 각 정책의 attacker/shooter/interceptor 및
net 중심 궤적에 FIRE, deploy, active, contact, kinetic commit, breach,
no-kill 경계와 자산보호 경계를 겹친다. 성공과 실패 사례를 모두 고른다.
그다음 비용비별 경험적 보호·안전 비율과 resource vector를 함께 보인다.
성공률만 올리고 안전을 악화시키는 정책의 비용을 “절약”이라고 부르지 않는다.

| 관찰 | 다음 조치 |
|---|---|
| 전환이 여러 비용비·상황에서 의미 있게 달라지고 궤적으로 설명됨 | G1 물리 parity·source-lock의 좁은 실험을 설계 |
| 한 mode가 전 영역 지배 | 전환 주장 축소; dominant-mode 조건 또는 세계 가정 오류 확인 |
| switch 이득이 cue 삭제/동일 authority 대조에서 사라짐 | 정보/권한 효과로 분리하여 새 질문 설정 |
| `p_kill` 또는 net aperture 임의값 하나에만 의존 | 해당 parameter source-lock 또는 범위 분석 전까지 비용 결론 보류 |
| 발사시점 술어를 동결해도 결과가 같음 | live-net 메커니즘 재검토; 새 world 구현 의미 부족 |
| policy가 전부 실패 | 저수준 guidance·초기 배치·안전 guard부터 진단; “mode change 무가치” 결론 금지 |

이 판독에서는 수치의 사후 최적화와 world 수정을 허용하지만 변경된
`mode_switch.*` 레지스트리 값·상태와 실행 산출물을 버전별로 기록한다.
**확인 단계 승격 시에는 독립 데이터·고정된 world/정책/축/seed·§9의
동시추론 계약을 새로 작성**한다. toy의 strict gap, F1-E의 비용 차이,
F1의 물리적 순위 반전은 서로 다른 증거층으로 보존한다. G2는 toy 양성만으로
통과하지 않는다. G6의 kinetic F3 실험은 외부 effect 근거가 없으면
의무처럼 약속하지 않고 simulation plant 한계를 명시한다.

## 9. 지금 당장 할 일

1. D0 G0 결정 카드의 표를 한 번에 채우고 공개 source/임의 pilot 값을 분리한다.
2. D1 finite DP 스크립트의 아주 작은 2-step 모델부터 구현해 brute force와
   대조하고 그림을 저장한다.
3. Track A의 B2 stop rule 판정과 산출물 계보를 확인한다.
4. 그 판정 이후에만 D2 새 모듈을 만들고, **첫 결과는 궤적 시각화부터** 확인한다.

추가 구현·서버 학습·출판 범위는 D3에서 실제로 관찰한 병목에 따라 정한다.
