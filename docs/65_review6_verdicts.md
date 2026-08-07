# 65 — 외부 리뷰 6 판정 로그 (리셋 전 전수 감사) + 통합 실행 큐

**2026-08-08 · 대상 = docs/64 §8 판정 요청 7건 (원천 감사 = `artifacts/audits/` 7파일).
이 문서가 이후 실행 순서의 정본이다 — docs/64 §9 의 큐는 본 문서 §8 로 대체.
r1 (같은 날) = Hyunjun 비준 반영: §2 blocker 재편 **승인** · CWC **원칙 승인**
(실제 값은 B1→truth table 비준 후 확정) · C4 rename 전략 **승인** · docs/61
재오픈 없음. 구조 수정 2건 — A4 parity 를 A4a/b/c 3단계로 분리 (미존재
runner 를 미리 검사하던 dependency 해소), Phase B 를 B1→B3 비준→B2→B4 로
재배열. 사다리 15→18단계 (새 연구 추가 아님 — dependency 풀어쓰기).**

---

## 1. 판정표 (리뷰어)

| 요청 | 판정 | 핵심 이유 |
|---|---|---|
| 1. blocker 완전성·순서 | **조건부 기각** | 성격이 다른 항목이 동일 레벨에 혼재. 구 #1+#2 를 **train/eval contract parity 단일 최상위 blocker** 로 통합, RunningNorm/fresh-state 를 blocker 로 **승격**, docs 정정은 hygiene 으로 강등 (runtime 복구를 늦추면 안 됨) |
| 2. CAPTURE_WITH_CONTACT | **(a) 명시적 terminal reward class 권고** | 문제는 값 0 이 아니라 **else 분기에 떨어져 우연히 0** 이라는 것. nondestructive capture 라면 NET_CAPTURE 와 동일 terminal 이 자연스럽고, (b) 중립은 동결된 endpoint 의미까지 재설명해야 해 부자연 |
| 3. Δv_shot route 비반영 | **학습 blocker 아님 / attribution limitation** | next-state·terminal 경로로 gradient 도달은 가능. 지금 reward 재설계 금지 — 문서상 limitation 으로 잠그고 MARL 후 attribution (Phase I) 으로 이월 |
| 4. COMA 오독 | **좁게 정정** | coma_D = diagnostic quantity. 과거 학습-신호 인용 미발견이면 전면 수정 불요. `train/coma_D_mean` 이름은 위험 — namespace 변경 또는 metadata 명시. **coma_mix>0 은 새 learning contract** (단순 toggle 아님) |
| 5. 허용 문장 강도 | **대부분 유지** | pre-fire ep35 만 하향: "창(window)" → "**NK-밖 engagement opportunity 의 첫 witness**". NK 42/42 는 engagement 어휘로. P94 문장 유지 (논문에선 "V3-FULL nominal 50 paired natural trajectory" 범위 병기) |
| 6. 정적 감사 맹점 | **targeted runtime audit 필요** | 3종: (A) resolved-config manifest 비교 — 코드 줄이 아니라 **constructed env object** 비교, (B) checkpoint/stateful audit → fresh-state 규율로 단순화, (C) terminal-event precedence truth table + executable test |
| 7. 정정 잔존 재발 | **semantic grep + claim registry 로 충분** | exact-string grep 부족 — 철회 시 동의어 토큰 전역 검색 + hit 3분류 (수정/historical 유지/별개 claim). `claim_registry.tsv` = "이 문장을 아직 써도 되는가" 의 authoritative lookup 으로 정본화 |

**총평 채택**: 이번 감사의 결론은 "reward 재설계" 가 아니라 —
**"MARL 이라고 부를 모든 코드 경로가 먼저 동일한 v3 세계를 실행해야 한다."**
같은 실험이라 부르는 모든 runner 의 mission contract parity 복구가 최우선이며,
이것이 학습 전에 발견된 것이 이번 감사의 최대 성과다.

## 2. blocker 사다리 재편 (판정 1 반영)

1. **[최상위] train/eval contract parity** — train · evaluation · sweep ·
   curve · factorial · scripted-baseline 전 경로가 동일 계약 실행. parity
   확인 필드 (실제 생성된 env 기준):
   `R1 resolver · R2 miss/handoff · standby · extra_cfg · threat-v3 spec ·
   spawn/init · episode_len · judge · n_segments · Pk · r_nk ·
   terminal label semantics · reward spec`
2. **[승격] fresh-state 규율** — v3 첫 학습 = fresh policy/RunningNorm/
   optimizer, legacy ckpt·norm restore 금지. resume 지원 시 env-contract
   hash/version assert.
3. **[계약 결정] CAPTURE_WITH_CONTACT** — reward contract decision (§3).
4. **[prereg 전제] P92/P93/P95 + docs/63** — 기존 큐 그대로.
5. **[hygiene] docs/50:183 · params 오기 4건** — 반드시 고치되 runtime
   parity 복구를 지연시키지 않는다.

## 3. 계약 — 비준 결과 (r1)

- **CAPTURE_WITH_CONTACT — 원칙 비준, 값은 B1 후 확정.** 비준 문구:
  > *CWC principle ratified: terminal reward must be explicitly mapped to
  > its mission utility class; accidental `else=0` is prohibited. Exact
  > mapping is fixed immediately after B1 event-semantics trace and
  > before B2 implementation.*

  B1 semantics trace 의 분기 판정 기준:
  1. net 성공 + engagement geometry 동반, kinetic neutralization 미발생
     → `NET_CAPTURE` utility class (동일 terminal).
  2. 실제 Pk success/destructive neutralization 발생인데 후속 코드가 CWC 로
     명명 → **w_kill 계열 재판정**.
  3. NK veto + net capture 중첩 → nondestructive 쪽 가능성 높으나 truth
     table 로 확정.

  이 순서라 "결과를 보고 reward 를 고르는 것" 이 아니다.
- **COMA**: 현 MARL 은 coma_mix=0 유지. 활성화는 새 사전등록 (random standby
  에서 `cf = layout.limiter_p0` 의 counterfactual 의미 재정의 필수).
- **Δv_shot**: 재설계 금지. limitation 문서화 + Phase I 이월.

## 4. 허용/금지 문장 갱신 (즉시 발효 — docs/64 §7 위에 patch)

- pre-fire ep35: ~~"NK-밖 창 개방 가능성의 첫 사례"~~ →
  **"NK-밖 engagement opportunity 의 첫 witness"** (window 는 시간 지속 함의).
- NK 42/42: "해당 7개 legacy miss-conditioned episode 와 해당 solver budget
  에서 발견된 42개 **engagement** 는 모두 NK 내부" (contact 어휘 대체).
- MARL gain 시 금지: "Δv_shot reward 가 shepherding 을 학습시켰다" —
  허용: "현 reward contract 아래 학습된 policy 가 성능 개선을 보였다"
  (+ static/active attribution 은 별도).
- MARL 무이득 시 금지: "channel 은 있었는데 못 배웠으므로 shepherding 은
  학습 불가능" — P88/P94 는 **environment controllability** 이지 현 PPO
  contract 의 learnability 가 아니다.
- coma_D: "coma_mix=0 일 때 diagnostic only, gradient contribution 0" 명시.
- knife-edge: `certificate` 는 항상 "robust-clean **predicate** 의
  certificate" 범위 유지 (physical feasibility 상한으로 확장 금지).

## 5. 재발 방지 규율 (등재)

1. **철회/강등 시 semantic grep 의무** — 관련 token·동의어 전역 검색, 각
   hit 를 수정 / historical 유지 / 별개 claim 중 하나로 판정.
2. **claim_registry.tsv 정본화** — 새 문장 작성 전 status
   (ACTIVE/DOWNGRADED/RETRACTED/PENDING/CONFLICT) lookup. 논문 자동 생성
   아님 — "써도 되는가" 의 단일 참조표.
3. **deprecated claim pattern scan** — 영구 금지 표현 소수를 regex 파일로
   CI scan (보조장치; 의미론적 정본은 registry).

## 6. targeted runtime audit 3종 (판정 6)

- **A. resolved-contract manifest**: TRAIN/EVAL/SWEEP/SCRIPTED-BASELINE env
  를 실제 생성해 §2-1 필드 dump·비교. 허용된 차이 외 mismatch = fail.
- **B. stateful object**: RunningNorm · optimizer · RNG · scheduler ·
  cached config · serialized metadata — 첫 학습은 fresh-state 로 단순화.
- **C. terminal-event precedence**: 같은 tick 의 NET event / engagement /
  NK veto / Pk / SPENT / termination 중첩 — truth table + executable test
  (전체 Cartesian product 불요). CAPTURE_WITH_CONTACT 가 이미 이 조합
  문제의 신호.

---

## 7. 당장 하지 않을 것 (금지 목록)

reward 가중치 재튜닝 · route_gain 수정 · threat 분포 재오픈 · r_nk 조정 ·
COMA 활성화 · learned-fire 부활 · oracle 확장 · old checkpoint warm-start ·
OOD 결과 본 뒤 scripted baseline 수정 · Δv_shot 의 route-specific reward
즉시 재설계. **순서는 계약 정합성 복구 → 기존 prereg queue → baseline
freeze → MARL.**

## 8. 통합 실행 큐 (정본 — 하나도 빠뜨리지 않음)

### Phase A — MARL runtime contract 복구
- A1 train_m4 R1/R2 전달 복구 (legacy default 전역 변경 금지 — v3 spec 에서
  명시 전달). **목표 재정의 (r1)**: "flag 를 전달한다" 가 아니라 **모든
  runner 가 하나의 canonical EnvSpec/SystemSpec 에서 파생되는 방향** —
  대규모 refactor 는 불요하되, kwargs 18곳 개별 패치의 재발산을 manifest
  test 의 `expected != resolved → hard fail` 로 막는다.
- A2 sweep_m4 + evaluation runner 전 경로 (train/eval/sweep/curve/factorial/
  scripted-baseline) 동일 수정
- A3 mission_eval 의 standby/extra_cfg 전달 복구 (silent legacy fallback 제거)
- **A4a (지금)** resolved-contract manifest infrastructure — 실제 env object
  에서 `contract/version · R1 resolver · R2 miss/handoff · standby ·
  extra_cfg · spawn/init · episode_len · judge · n_segments · Pk · r_nk ·
  reward spec · terminal semantics` 를 canonical serialization/hash 로
  뽑는 helper + comparison test. 현존 경로 (train/eval/sweep/curve/
  factorial) 를 **V3-NOMINAL equivalent contract** 에서 비교.
- **A4b (E1/P92 이후)** TRAIN distribution 생성 후 TRAIN ↔ EVAL/IID-
  compatible construction parity — `threat distribution/version/hash`
  포함 재인증.
- **A4c (F/docs/63 이후)** scripted runner 도 동일 manifest 사용 —
  **"controller 만 다르고 world contract 는 동일"** 검사.
- A5 fresh-state training 규율 (§2-2; prereg 명시). **기록 의무 (r1)**:
  fresh 사용 사실뿐 아니라 artifact 에 저장 — `normalizer initialization =
  fresh · normalizer count at start · checkpoint parent = null`. 향후
  resume 은 `hash(ckpt 시점 env contract) == hash(현재 env contract)`
  아니면 reject.
- A6 hidden legacy default 감사 — **분류 확정 (r1)**:
  - `judge="point_mass"` 가 evidence runner 에서 reachable → **BLOCK**
  - `n_segments=1` GIF, visualization only → **NON-EVIDENCE** 격리
  - rollout_gif `_zero_commit` trap → evidence 용 사용 금지 또는 env
    helper 재사용
  - 단, **논문에 행동 예시로 들어가는 순간 GIF 도 evidence** — 최종 figure
    생성 runner 는 production contract 를 쓴다.

### Phase B — terminal/reward contract 정리 (**순서 재배열 r1: B1→B3→B2→B4**)
- B1 CAPTURE_WITH_CONTACT 를 만드는 event combination 재추적 (§3 분기
  판정 기준 적용)
- B3 terminal-event precedence truth table **문서 확정 + Hyunjun contract
  결정을 B2 구현보다 먼저** (구현이 truth table 을 역정의하는 것 방지) —
  조합: net capture only / engagement only / engagement+NK veto /
  engagement+Pk / capture+engagement / miss+handoff / miss+later
  engagement / spent / penetration / truncation × final label·terminal
  여부·reward·limiter/net spent
- B2 terminal utility 구현 (B3 비준안 그대로; else=0 제거)
- B4 B3 표 ↔ 코드 일치 executable test
- B5 limiter 이중 벌점 (c_lim 1회 vs λ3 재계수) trace — 값 튜닝 금지.
  확인 대상은 오직 "동일 physical event 가 실제로 어떤 시점에 몇 번
  reward 에 들어가는가". 의도와 다르면 별도 contract decision 상정

### Phase C — 문서/registry 정정 (hygiene)
- C1 docs/50:183 철회 claim 제거 (역사 기록 유지)
- C2 docs/48 §5 privilege 문구 historical 표시
- C3 CONTACT_NEUTRALIZATION = 분석 카테고리 (HARD_KILL + source) 명시
- C4 contact→engagement: 논문/최신 docs = engagement, legacy symbol =
  compatibility name 분리 (완전 rename 은 별도 chore commit)
- C5 capture_thresh: deprecated/ignored + 실제 predicate 위치 registry 명시
  (env logic 불변)
- C6 params.py 오기 4건 (limiter_pressure idx3 = M4 commit bit ·
  e_net_init · headline_u0/coma_u0 · ViabilitySpec.seed)
- C7 legacy scope qualifier 보강 (R1/R2 = F-flags arm · knife-edge = legacy
  regime · NK 42/42 = 7 episode+budget · old oracle = 해당 parameterization)
- C8 pre-fire ep35 표현 하향 (§4)
- C9 claim_registry.tsv 정본화 (유지 artifact 승격, status 갱신 규율)
- C10 deprecated claim regex scan 추가 (경량). **r1**: 명백히 철회된
  claim 만 **hard fail**, 정당한 역사적 인용 (철회 기록 자신 등) 은
  historical section allowlist 로 예외 처리

### Phase D — COMA / logging 정리
- D1 coma_D diagnostic-only 명시 (코드 주석 + 실험 metadata + docs)
- D2 로그 namespace `train/coma_D_mean` → `diagnostic/coma_D_mean` (기존
  분석 script 파손 시 rename 보류·metadata 명시로 대체)
- D3 현 MARL coma_mix=0 유지
- D4 향후 활성화 시 새 사전등록 (counterfactual 재정의)

### Phase E — 동결된 v3 TRAIN prerequisite (기존 큐)
- E1 P92 draw_threat_v3 배선 correctness (deterministic draw · 9-cell
  coverage · bounds · nesting)
- E2 P93 침투 보존 (defender removed → 50/50 PENETRATED · TRUNCATED 0)
  → episode_len_train=1100 확정
- E3 P95 realized reactivity (paired CRN, R_route mean·median 이 같은
  speed regime 내 weak<med<strong; 실패 = **taxonomy failure**, MARL
  failure 해석 금지). **추가 금지 (r1)**: strong 의 realized response 가
  약해 보인다는 이유로 `route_gain` 상향 금지 — P95 의 목적은 threat
  difficulty tuning 이 아니라 **라벨의 semantic validity**

### Phase F — docs/63 scripted baseline 사전 동결
- F1 관측 (사용 가능한 state/bearing) · F2 역할 할당 규칙 family ·
  F3 motion/redeployment rule family · F4 hyperparameter 목록 ·
  F5 tuning budget (조합/episode/seed) · F6 tuning dataset = TRAIN only
  (**IID/OOD 절대 금지**) · F7 selection criterion (TRAIN metric) ·
  F8 final freeze (commit/hash 고정, MARL 결과 전 변경 금지)
- **F9 objective access 분리 (r1 추가)** — `runtime observations` 와
  `offline tuning metrics` 를 분리 선언. offline tuner 가 TRAIN
  NET_CAPTURE 를 보는 것 = 가능 / runtime controller 가 env 내부 oracle
  quantity (`v_shot`, reachable set, hidden attacker parameter) 에 접근
  = **금지** (별도 privileged baseline 으로 선언하지 않는 한)

### Phase G — MARL 실행 전 마지막 확인
- G1 full resolved contract dump 저장 (git HEAD · dirty · env contract ·
  threat distribution hash · reward spec · RunningNorm state · seed
  namespace)
- G2 fresh v3 training smoke — obs/reward finite · label 정상 · horizon ·
  normalization · parity 만 확인. **이걸 보고 reward/tuning 변경 금지.**

### Phase H — MARL 본 실험
hold vs docs/63 scripted vs MARL, 동일 TRAIN/IID 계약, docs/61
lexicographic endpoint 그대로.

### Phase I — mechanism attribution (MARL 결과 후)
"learned shepherding" 판정 단계. 성능만으로 선언 금지 — V3-FULL 에서
active learned limiter vs static/disabled counterpart 비교 (필요조건) +
route-mediated mechanism 차단 시 gain 유지 여부 (강한 추가 attribution).
**개념 구분 (r1)**: static counterpart 하나로는 **learned movement** 효과와
**attacker route response** 효과가 섞인다 — 예: `learned active+route ON /
frozen geometry+route ON / learned active+route OFF` 류의 개입이 유용.
단 **지금 이 arm 들을 prereg 하는 것 아님** — attribution 단계에서 별도
설계라는 지위 유지.

### Phase J — generalization / falsification
IID → OOD-Z → **OOD-CPA (핵심 falsifier)** → OOD-TIMING → OOD-CORNER →
A4 optimizer/self-play falsifier. OOD 성공 = "사전등록된 반례 탐색 통과"
로만 표현 (일반화 증명 아님).

### 18단계 실행 사다리 (r1 최종 — dependency 반영)

```
[1]  A1~A3   runtime pass-through 복구
[2]  A4a+A5+A6  manifest harness · 현존 runner parity · fresh-state 규율
[3]  B1      CWC 실제 semantics trace
[4]  B3 truth table 비준 → B2 구현 → B4 test → B5 penalty trace
[5]  C + D   문서/registry/COMA diagnostic hygiene
[6]  P92     TRAIN distribution 배선
[7]  A4b     TRAIN/EVAL resolved-contract parity 재인증
[8]  P93     penetration 보존 → episode_len_train=1100 확정
[9]  P95     realized taxonomy validation
[10] docs/63 설계·비준·freeze
[11] A4c     scripted runner world-contract parity
[12] G1/G2   final manifest + fresh smoke
[13] MARL TRAIN
[14] headline hold vs scripted vs MARL
[15] mechanism attribution
[16] IID
[17] OOD-Z / CPA / TIMING / CORNER
[18] A4 optimizer/self-play falsifier
```

(15→18 은 새 연구 추가가 아니라, 원래 A4 가 미래에 존재하지 않는
TRAIN/scripted runner 까지 미리 검사하도록 적혀 있던 dependency 를
풀어쓴 것.)

---

## 9. 최종 비준 기록 (r1, 2026-08-08, Hyunjun)

- §2 blocker 재편: **승인** (순서 유지).
- §3 CWC 방침: **원칙 승인** — `NET_CAPTURE 동일 reward` 라는 실제 값은
  **B1 → truth table 비준 이후 확정**.
- C4 rename 전략: **승인** (최신 docs/논문 = engagement, legacy symbol =
  compatibility name).
- docs/61: **재오픈하지 않음.**

**최우선 운영 규율 (재발 방지의 핵심)**:

> 앞으로 `train` · `eval` · `sweep` · `scripted` 라는 이름은 코드
> entrypoint 가 아니라 **동일한 resolved world contract 를 공유할 때만**
> 같은 실험 family 로 취급한다.
