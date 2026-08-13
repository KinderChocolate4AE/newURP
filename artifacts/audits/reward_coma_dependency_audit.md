# Reward / COMA / Legacy-Dependency 감사 (Task 2)

**2026-08-08 · MARL 재개 전 진단. 코드 수정 0건.** 등록부:
`artifacts/audits/learning_signal_dependencies.tsv`.

추적 기준 코드: env.py(동결) · env_sys.py · viability.py · finisher_fsm.py ·
train/adapter.py · train/mappo.py · scripts/train_mappo.py · scripts/train_m4.py ·
spawn_rand.py · scale_v2.py · configs/l2_mappo.yaml.

---

## 1. Executive summary

- **실제 gradient 에 도달하는 항은 7개**: `Δv_shot(headline)` · `λ1·clean` ·
  `−λ2·wasted` · `−λ3·limiter_loss(근접 재계수)` · terminal(라벨별) ·
  `−c_lim·소모증분` · (aux 팔 한정) BC cosine. 전부 단일 공유 J 스트림으로
  GAE 1회 → 두 actor 가 같은 advantage 를 소비한다.
- **COMA 는 계산되지만 학습에 닿지 않는다**: `coma_mix` 는 l2_mappo.yaml 에
  없고 기본 0.0 (mappo.py:108) — M4 계열 전 런에서 `coma_D` 는 로그 전용.
  gradient 도달은 legacy 2D 라인(l2_coma*.yaml)뿐.
- **legacy geometry 의 유일한 살아있는 gradient 경로 = `layout.limiter_p0`**
  (Δv_shot 기준선). 단 v3 standby 는 `apply_standby` 가 limiter_p0 를
  재기입하므로(spawn_rand.py:294) ring 의존은 standby 활성 팔에서 자동 소멸 —
  대신 **보상 기준점이 에피소드별 랜덤 standby 자세**가 된다 (아래 §4).
- **MARL_BLOCKER 2건 + 후보 1건** (§8): (1) train_m4 가 R1/R2 플래그를
  전달하지 않아 학습 env 가 "비준 비정합" 판정된 구계약으로 돈다,
  (2) v3 배선 부재 (현 CLI 는 legacy 24 m·무반응 A2 로 조용히 학습),
  (후보) `CAPTURE_WITH_CONTACT` 종말보상 0 ↔ 지표는 비손실 성공 계수.

---

## 2. 실제 gradient 에 도달하는 reward 사슬

```
[dense, 매 스텝]  env.py:364
  J = delta_headline + 1.0·clean_crossed − 1.0·wasted_inc − 0.5·limiter_loss
      │                │                   │                └ 매 스텝 근접 재계수 (§6.3)
      │                │                   └ FSM miss 해소 시 1회
      │                └ v_soft ≥ 0.9 ∧ ¬boxed
      └ v_soft(현 배치) − v_soft(limiter_p0 배치)          ← 유일한 legacy-geometry 항

[M4 재작성, RewardSpec.enabled=True]  env_sys.py:385
  rew = 1.0·J + 1.0·terminal(label) − 0.1·new_consumed

[수집]  adapter.step → r.rewards[finisher] (공유 J)
        → train_mappo.collect_rollout → buf.rewards       (train_mappo.py:207)

[학습]  compute_gae(rewards, V, V', dones, 0.99, 0.95) → normalize
        → adv (finisher) / adv_lim (= adv 반복, coma_mix=0)
        → PPO clip pg loss (양 actor) + 0.5·vf + entropy    (mappo.py:359-448)
        → clip_grad_norm 0.5 → Adam
```

BC(aux 팔)만 보상 우회로 actor 손실에 직접 붙는다 (`L += 0.1·L_BC`).

## 3. COMA counterfactual — 상세 판정

- 계산: env.py:272-288 이 **매 스텝** `cf[i] = layout.limiter_p0[i]` 스왑으로
  N+2 회 union 평가 (batched, CRN). `coma_D` 로 info 에 실림.
- 수집: adapter → runner 가 1-스텝 시프트백으로 buf.coma_D 에 기록
  (train_mappo.py:197-199).
- **gradient 게이트**: mappo.py:380 `if cfg.coma_mix > 0.0` — l2_mappo.yaml 에
  키 자체가 없어 기본 0.0. **M4/역할분리/BC 전 런에서 COMA 는 학습 신호가
  아니었다.** `train/coma_D_mean` 로그를 학습 신호로 읽으면 안 된다.
- standby 가 켜지면 counterfactual 기준점도 standby 로 자동 이동
  (spawn_rand.py:294 동기화). ring 이 "reward 기준점으로 잔존" 하는 팔은
  **standby=None 인 V3-C/V3-CS** 뿐이다 (ring@50).
- 판정: **DORMANT_BY_CONFIG.** 제거/유지 판단은 하지 않는다. 단 coma_mix 를
  나중에 켤 경우, 에피소드별로 움직이는 기준점(standby jitter U[8,16] 예정)에
  대한 counterfactual 의 의미는 재선언 대상 — MUST_DOCUMENT.

## 4. Δv_shot 경로 (docs/52 §8.4 의 계약 충돌 후보)

- `vbase = v_shot(limiter_p0)` 는 **고정 기준선**(S8 비준: 스텝별 가변 기준선
  = reward hacking)이며, potential-based shaping 이 아니다 — 즉시항이 "지금
  탈출집합을 얼마나 줄였나" 만 본다.
- docs/52 §8.4 의 위험 그대로: 장기 funnel 준비 기동이 현재 v_shot 을 낮추면
  스텝 단위 음의 신호. 장기 회수는 critic/GAE 몫.
- v3 특이점: limiter 이동이 attacker 궤적을 바꾸는 **route 채널의 이득은
  Δv_shot 에 즉시 반영되지 않는다** (다음 상태의 v_shot 경유만). "shaping
  채널을 학습으로 이용하는가" 를 이 보상으로 검정할 때 반드시 명시할 것.
- 판정: MUST_DOCUMENT (docs/52 §8.4 의 "성공 궤적 위 Δv_shot 감사" 는 여전히
  미실시 — 사슬 §8.1 항목 5).

## 5. Terminal semantics (R1/R2 이후)

| label | terminal | 지표상 취급 | 일치? |
|---|---:|---|---|
| NET_CAPTURE | +1.0 | 비손실 성공 | ✓ |
| **CAPTURE_WITH_CONTACT** | **0.0 (else 분기)** | **비손실 성공으로 계수** (m4_env.py:147) | ★ **불일치** |
| HARD_KILL (commit·contact 공용) | +1−w_kill | 파괴적 성공 | ✓ |
| PENETRATED | −1.0 | 실패 | ✓ |
| TRUNCATED | −1.0 (보상) | 우측절단 (지표) | 선언된 분리 (docs/26) ✓ |
| SPENT_FAIL | 0.0 | 의미 감사 전 중립 | 선언 일치 ✓ (R2 on 시 종료 라벨로 소멸) |

- ★ `CAPTURE_WITH_CONTACT` 는 RewardSpec.terminal 의 명시 분기가 없어 0 을
  받는다. 접촉 동반 포획 = 종말보상 0 = SPENT_FAIL 과 동일 대우. v3 는
  limiter 를 공격자 근처로 보내는 설계라 이 라벨의 발생 확률이 구조적으로
  올라간다. **보상과 지표가 같은 사건을 다르게 채점** — §8 후보 참조.
- R2(miss_terminates=False)에서: miss 스텝은 done=False 로 억제 → 종말항 없음,
  단 **dense −λ2·wasted 는 그대로 1회 부과** (miss 무벌점 아님). 최종 실제
  종료 라벨로만 종말항 1회. `NET_MISS_HANDOFF` 는 info 전용 — 보상 미개입 ✓.
- destructive fallback 성공(contact→HARD_KILL) vs net capture 상대평가는
  w_kill 하나로 결정 (기본 0.5 → 1.0 vs 0.5). 선언된 sweep 축 ✓.

## 6. limiter 손실 벌점 — 이중 구조

- **6.1 c_lim (M4)**: 소모 이벤트당 −0.1 **1회** (P3 증분 수정 확인,
  env_sys.py:379-385). retirement 이후 반복 없음 ✓. commit 소모와 contact
  소모 동일 부과 ✓. VETO = 미소모 = 무벌점 ✓.
- **6.2 λ3·limiter_loss (동결 env dense)**: env.py:360 이 **매 스텝** "공격자
  kill_radius 안 limiter 수" 를 재계수 — 이벤트가 아니라 상태 벌점이다.
  - legacy(R1 off): 접촉해도 limiter 가 제거되지 않으므로 공격자가 근접을
    유지하는 동안 **스텝마다 반복 부과**.
  - R1 on: contact kill → PARK 이동으로 이후 계수 중단. 단 **NK zone 안
    veto 접촉은 limiter 잔존 → 반복 부과 지속**.
  - 같은 물리 사건에 c_lim(1회)과 λ3(지속) 두 벌점이 계약 플래그에 따라
    다른 시간 구조로 붙는다 — MUST_DOCUMENT.

## 7. Observation / normalization 의존

- RunningNorm 은 **누적 무망각** (train_mappo.py:159 update=True) — PARK 사건
  (2026-08-03 P2) 의 원인 구조 그대로. 관측엔 raw 좌표가 실린다.
- v2/v3 에서 바뀌는 것: 좌표 스케일 24→300+ · episode_len 80→1100(TRAIN) ·
  standby R jitter U[8,16] · 방위 랜덤 스폰 · attacker 속도 8~30. 정규화
  통계의 평균/분산 구조가 legacy 체크포인트와 양립 불가 — **legacy ckpt/norm
  재사용 금지** (경로 조사만, 수정 없음).
- PARK (0,0,60) 재검토: 근거 ① (v_shot 기여 0) 은 v2/v3 에서도 성립
  (공격자 관측 최대 z≈23, PARK 까지 >37 m ≫ 0.75). 근거 ② ("링 반경의
  12배 → 정규화 생존") 은 legacy 서사 — standby R=12 면 5배, 좌표 300 스케일
  에선 오히려 PARK 가 상대적으로 작다. 결론은 유지되나 주석 근거가 낡음.
  docs/59 의 "P51 재검토 필수" 등재 유지.
- threat_obs 2축(a_att, att_speed)은 관측되지만 **v3 TRAIN 분포축(route_gain·
  sense_range 등)은 관측에 없다** — 정책엔 암묵 randomization. 결과 해석 시
  "위협 반응성은 비관측 축" 임을 명시해야 한다.

## 8. 판정

### MARL_BLOCKER

1. **학습 env 가 구계약으로 돈다** — `train_m4.build_specs` (train_m4.py:448)
   는 `SystemSpec(tau_kill, p_kill, r_nk, enabled=True)` 만 만들고
   `contact_resolver`/`miss_terminates` 를 전달하지 않는다 → 기본 off.
   즉 지금 학습을 재개하면 docs/53-54 가 **구현 비정합으로 판정한 계약**
   (접촉해도 무력화 없음 · miss 즉시 종료)에서 배운다. v2/v3 실험 사슬은
   전부 F-flags(둘 다 on)에서 측정했으므로, 학습과 평가·probe 의 세계가
   갈라진다 — 무엇을 학습하는지 해석 불능.
2. **v3 배선 부재** — train_m4 는 `m4_config()`(legacy 24 m) + `SpawnSpec()`
   기본 + `AttackerSpec(level∈{A1,A2,A3})` 만 노출한다. scale_v2 overlay ·
   THREAT_V3 · standby · `draw_threat_v3`(P92, 미구현) 어느 것도 학습 CLI 에
   연결돼 있지 않다. 현 상태로 돌리면 **조용히 legacy 무반응 A2 회랑**을
   학습한다. (docs/61 비준 + P92/P93/P95 + 배선이 선행 조건 — 이미 계획된
   사항이지만, "빠뜨리면 조용히 legacy 로 돈다" 는 성질 때문에 blocker 로
   등재한다.)
   - **평가 경로도 같은 구멍** (Task 3 config 감사 교차확인): `mission_eval`
     (m4_env.py:123-125) 은 `build_m4_env` 를 부를 때 **`standby` 와
     `extra_cfg` 를 전달하지 않는다** — build_m4_env 가 둘 다 받는데도.
     따라서 train_m4.evaluate / sweep_m4 / curve_sweep / mobility_factorial
     전부 V3-FULL 팔을 평가할 수 없고, v3 attacker spec 을 줘도 **조용히
     legacy 기하 위에서** 평가된다. 재배선 목록에 mission_eval 포함 필수.

### MARL_BLOCKER 후보 (계약 결정 필요 — 다음 세션 판단)

3. **CAPTURE_WITH_CONTACT 종말보상 0 ↔ 지표 비손실 성공** (§5). v3 기하에서
   발생 빈도가 올라갈 수 있어, 켜기 전에 (a) 별도 terminal 값 선언 또는
   (b) "접촉 동반 포획은 무보상 중립" 을 명시 비준 중 하나가 필요하다.
   이 감사는 어느 쪽도 권고하지 않는다 — 결정 대상임을 보고할 뿐.

### MUST_DOCUMENT

- COMA 는 전 M4 런에서 gradient 미도달 (coma_mix=0) — coma_D 로그 해석 주의.
- Δv_shot 기준선: standby 팔 = 에피소드별 standby 자세 / V3-C·CS = ring@50.
- Δv_shot 순간성 (docs/52 §8.4) + v3 route 채널 비반영.
- λ3 근접 재계수의 R1 on/off 의미 차 (§6.2) 및 c_lim 과의 이중 구조.
- R2 에서도 miss 는 dense −λ2 로 1회 벌점.
- RunningNorm 누적 + v2/v3 스케일 → legacy ckpt/norm 재사용 금지.
- 위협 반응성 축은 비관측 (threat_obs 는 a_att·att_speed 만).
- TRUNCATED: 보상 −1 vs 지표 우측절단 (선언된 분리, 혼용 금지).

### SENSITIVITY_LATER

- theta_fire=0.9 (legacy 기하 보정값) 의 v3 재보정 여부.
- ent_coef_limiter=0.0 + 커밋 Bernoulli 헤드 → 확률 붕괴 감시
  (limiter/commit_rate 0.000/1.000 고착 여부).
- c_lim=0.1·w_kill=0.5·terminal_scale=1.0 스케일 상호작용 (docs/29 선언 sweep
  축 안에서).

### NO_ISSUE_FOUND (추적했으나 영향 없음)

- adversary 보상(−J + M4 재작성) — 소비자 없음 (공격자 스크립트).
- l2_mappo.yaml `randomize:` 블록 — M4 경로에서 rand_cfg=None 으로 무시
  (train_m4.py:185; 위협 랜덤화는 m4_config draw 가 담당).
- env.capture_thresh · omega_att_max=8.0 — params.py DEAD 등재 일치.
- freeze/BC 플래그 기본값 경로 — P55/P65 bit-identical 확인 구조.

## 9. "존재하지만 실제 학습에는 영향 없는 설정" 목록

| 설정 | 위치 | 이유 |
|---|---|---|
| coma_mix/coma_gamma/coma_lam | MAPPOConfig (l2_mappo.yaml 미기재) | 기본 0.0 → advD 미혼합 |
| l2_mappo.yaml randomize 블록 | config | M4 runner 가 rand_cfg=None |
| adversary 보상 | env.py:394 | 스크립트 공격자 — 미소비 |
| env.capture_thresh | env.py:89 | 저장만, 미독 (params DEAD) |
| omega_att_max=8.0 | env.py:345 | 수신 함수가 미사용 (params DEAD) |
| viability.turn_limited | roles.ViabilitySpec | parsed-but-inert (params RESERVED) |
| bc_lambda/freeze_* 기본값 | MAPPOConfig | 0/False 경로 = bit-identical |

---

*규율 준수: reward 수정·권고 없음. 모든 판정은 영향 경로 + blocker 근거로만.*
