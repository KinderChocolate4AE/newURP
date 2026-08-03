# 운용점 방어가능성 감사 — 임의값 전수 조사

**2026-07-29 · `configs/m2_l2_train.yaml` + `params.py` + `env_sys.py` + `attacker_ladder.py` 전수**
**질문: 우리가 임의로 정한 게 뭐고, 그게 acceptable 한가**

---

## 0. 답 먼저

```
활성 파라미터 62개
  근거 좋음 (자랑 가능)        5개
  acceptable (설계 선언/도출)  38개
  ★ 반드시 고쳐야 함           7개   <- 심사에서 깨진다
  주의 필요 (민감도 보고 필요)  12개
+ 표에 없던 구멍               1개   <- 초기조건 랜덤화 미배선. 이게 제일 크다
```

**"우리가 임의로 정한 게 있나"의 답은 예입니다.** 대부분은 설계 선언이라 괜찮지만,
**7개는 근거가 문자 그대로 `"demo-proven"` / `"fixture"` 이고 문헌과 6–46× 어긋납니다.**

---

## 1. 등급 정의

| 등급 | 뜻 | 심사 대응 |
|---|---|---|
| **E** 외부 | 문헌 값 또는 문헌이 준 비율 | "이 논문 표 N" |
| **D** 도출 | E 로부터 명시된 공식 | 공식 제시 |
| **C** 보정 | 한 번 맞추고 동결 | 보정 대상이 정당해야 함 |
| **S** 설계선언 | 우리가 정했고 "그렇게 설계했다"가 답 | 임의지만 **acceptable** |
| **W** sweep축 | 값을 안 고르고 축으로 둠 | **가장 강한 형태** |
| **A** 임의 | 우리가 정했는데 답이 없음 | **취약** |
| **T** 튜닝잔재 | 데모 수렴용 손튜닝 | **가장 위험** |

**핵심 구분: S 와 A 는 둘 다 "우리가 정한 것"이지만 방어 가능성이 다릅니다.**
"limiter 를 4대로 정했다"는 S(설계 범위)고, "limiter 속도를 80 m/s 로 정했다"는 A(물리 주장)입니다.
**물리적 주장을 하는 값에 근거가 없으면 A 이고, 그건 고쳐야 합니다.**

---

## 2. 블록별 전수

### 2.1 physics — 8개 중 **4개가 A**

| 파라미터 | 값 | 등급 | 근거 원문 | 판정 |
|---|---:|:---:|---|---|
| `dt` | 0.05 s | **S** | "sim convention (20 Hz)" | OK — 탐지 10 Hz / 제어 100–500 Hz 사이 결정루프로 논증됨 |
| `tau_deploy` | 0.4 s | **D** | Xu baseline 병진 0.398 | OK (C-1 조건부) |
| `tau_lock` | 0.1 s | **S→E** | "S3 irreversible-commit fixture" | OK — 탐지 1주기(10 Hz)로 사후 정당화 |
| `net_radius` | 2.0 m | **D+E** | Xu S_NP + **Pliska 2.0 m 확증** | **좋음** |
| `a_att_max` | 30 m/s² | **A** | *"fixture (~3 g)"* | **점값 방어 불가 → 브래킷 필수** |
| `att_speed` | 20 m/s | **A** | *"fixture"* | **점값 방어 불가 → 브래킷 필수** |
| `kill_radius` | 2.0 m | **A** | *"(no external grounding)"* | **★ 고칠 것 → 0.6–0.9** |
| `a_lim_max` | 30 m/s² | **A** | *"fixture (= attacker authority)"* | **★ 고칠 것 → 0.35×a_att** |

> `a_lim_max = a_att_max` 는 **"방어자와 공격자가 대등하다"는 물리적 주장**인데
> 근거가 "fixture" 입니다. Pliska(RA-L 실기)는 비 0.36 입니다. 이건 그냥 틀린 주장입니다.

### 2.2 attitude — 2개 중 **1개가 A**

| `omega_max` | 3.14159 rad/s | **A** | *"half turn per second"* | **★ 고칠 것 → 2.0 (Pliska)** |
|---|---:|:---:|---|---|
| `e_net_init` | (1,0,0) | S | 회랑 기하 | OK |

`3.14159` 는 π 를 그대로 쓴 값입니다. 물리적 근거가 아니라 **숫자가 예뻐서** 고른 값입니다.

### 2.3 viability — 7개

| `judge` | se3_cone | S | 모델 선택 (ablation 존재) | OK |
|---|---:|:---:|---|---|
| `turn_limited` | false | — | RESERVED, 문서화된 inert | OK |
| `n_samples` | 2000 | **C** | n-cut 오차 실측 (n=500 err 0.190 > band 0.15) | **좋음** |
| `seed` | 0 | S | 재현성 관례 | OK |
| `n_segments` | 4 | **A(약)** | "S14: >1 = 보수적" — **왜 4인지는 없음** | 단조 보수성이라 방향은 안전. 민감도 1줄 |
| `cone.half_angle` | 0.067 rad | D | arctan(net_r/range_max) | range_max 에 종속 |
| `cone.range_max` | 29.847 m | **A** | *"WEAK/FLAGGED"* — 자체 문서가 신뢰불가 표기 | **★ 고칠 것 → C-1 후 재도출** |

### 2.4 fire_gate — 3개, **전부 근거 좋음**

| `theta_fire` | 0.9 | **C** | 해석적 라벨 대비 보정, zero-waste band [0.85,1.0] 실측 | **최상** |
|---|---:|:---:|---|---|
| `B_capture` | 1.0 | S | 정규화 | OK |
| `c_fire` | 0.9 | D | = θ×B (assert 로 강제) | OK |

**이 블록이 이 리포에서 근거가 가장 튼튼합니다. 나머지도 이 수준이어야 합니다.**

### 2.5 reward (기존 S6) — 3개 전부 A, 그러나 acceptable

| `lambda1/2/3` | 1.0 / 1.0 / 0.5 | **A** | *"S6 ratified weight (no sweep yet)"* | 보상가중은 설계자유도 → **민감도 보고로 충분** |
|---|---:|:---:|---|---|

### 2.6 train.layout — 회랑 기하 8개

| `target` / `target_radius` / `ring_center` / `ring_radius` / `finisher_p0` / `adversary_start_x` | — | **S** | 회랑 기하 | OK — 단 §1.3(발사창)과 정합 확인 |
|---|---:|:---:|---|---|
| `r_ring` | 2.1 m | **T** | *"L1 demo tuning"* | baseline 전용, 학습정책 무시 → **명시하면 OK** |
| `x_fire` | 11.0 m | **T** | *"L1 demo tuning"* | baseline 전용 → OK. **13–15 권고** (docs/35 §1.3) |
| `episode_len` | 80 (4 s) | **A** | env 계약 | **주의**: M4 는 TRUNCATED 를 실패로 벌한다 → **지평선 민감도 필수** |

> `episode_len` 주의 이유: 보상이 `-c_trunc` 를 주므로 **지평선이 짧으면 "빨리 못 잡으면 실패"**가 됩니다.
> 4 s 가 임의값인 채로 두면 결과가 지평선의 산물이라는 반박을 못 막습니다. 최소 2점 민감도 필요.

### 2.7 train.limits — 7개 중 **3개가 A**

| `limiter_v_max` | **80 m/s** | **A** | *"demo-proven backend limit"* | **★ 문헌 대비 10×. 고칠 것** |
|---|---:|:---:|---|---|
| `limiter_omega` | **12 rad/s** | **A** | *"demo-proven"* | **★ 문헌 대비 6×. 고칠 것** |
| `adversary_omega` | 10 rad/s | **A** | *"demo-proven"* | C-2 대기 (FPV 는 실제로 민첩하므로 과대가 아닐 수 있음) |
| `adversary_v_max` | 30 m/s | D | att_speed 20 의 헤드룸 | 종속 |
| `finisher_a_max/v_max` | 1.0 | S | finisher 는 사실상 정지 | OK |

> `"demo-proven"` 은 **"데모가 돌아갔다"**는 뜻이지 물리 근거가 아닙니다. 3개 전부 같은 출처입니다.

### 2.8 M4 SystemSpec — 신규 7개

| `p_kill` | 1.0 | **W** | 선언 sweep 축 | **좋음** |
|---|---:|:---:|---|---|
| `commit_threshold` | 0.5 | D | env fire logit 규약과 동일 | OK (일관성이 근거) |
| `enabled` | True/False | S | P6 bit-identical 게이트 | OK |
| `tau_kill` | 0.1 s | **A** | *"tau_deploy(0.4)의 1/4"* — **자기참조** | 비율로 재선언하고 **sweep 축으로** |
| `r_nk` | 6.0 m | **A** | no-kinetic zone 반경 | **S 로 승격 가능** — 교전규칙 선언이라고 명시하면 됨. sweep 권고 |
| `a_lim_max` (override) | None | D | scenario 값 상속 | OK |
| `seed_ns` | "m4_hardkill" | S | CRN 네임스페이스 | OK |

### 2.9 M4 RewardSpec — 신규 7개

| `w_kill` | 0.5 | **W** | *"선언된 SWEEP 축. 어디서 뒤집히는지가 결과"* | **최상 — 이게 모범 형태** |
|---|---:|:---:|---|---|
| `b_net` / `c_pen` / `c_trunc` | 1.0 | S | 정규화 | OK (순서 불변식은 테스트로 강제) |
| `c_lim` | 0.1 | **A** | — | 민감도 1줄 |
| `dense_scale` / `terminal_scale` | 1.0 / 10.0 | **미정** | **[E] 스케일 스모크로 결정** | 사전등록됨 → OK |

### 2.10 공격자 사다리 — 선언·동결 (최적화 금지 규율이 보호)

| `homing_gain` | 4.0 | **D** | **`adversary.fwd_gain` 상속 → 신규 자유도 0** | **좋음** |
|---|---:|:---:|---|---|
| `lam_gain/lam_range` 프리셋 5 | — | **W** | 선언 sweep 축 | 좋음 |
| `jink_amp` / `jink_freq` | 0 / 1.5 Hz | **A** | — | **선언·동결 + sweep 이면 OK** (anti-exploit rule 2) |
| `jink_terminal_r` | 3.0 m | A(약) | 유도문헌의 종말 게이트 | 부분 근거 |
| `route_probe` | 2.0×kill_radius | A | — | kill_radius 종속 → B-5 와 함께 이동 |
| `bait_threshold/range/enclosure_r` | 0.5 / (4,16) / 3.0 | **A** | — | A3 효과 미측정이라 현재 무영향 |
| `adversary.fwd_gain` | 4.0 | **T** | *"hand-tuned for the corridor"* | **동결·선언이고 방어 이전에 정해짐** — 명시하면 OK |
| `adversary.dodge_amp` | 1.8 | **T** | *"deploy-delay escape 강도"* | 동일. **공격자 강도를 결정하므로 sweep 권고** |

> 사다리의 A/T 값들이 방어되는 이유는 값 자체가 아니라 **규율**입니다 —
> *"공격자 파라미터는 선언·동결하고 절대 최적화하지 않는다(rule 2)"*.
> 이걸 논문에 명시하는 것이 개별 값을 정당화하는 것보다 강합니다.

---

## 3. ★ 반드시 고쳐야 할 7개

전부 **우리에게 불리한 방향**이라, 결과를 보기 전 지금 선언하면 소급 변경 의심이 없습니다.

| # | 파라미터 | 현행 | 권고 | 도출 |
|---|---|---:|---:|---|
| 1 | `train.limits.limiter_v_max` | 80 | **20** | Pliska 요격기 8 = 표적 8 → 비 **1.00** × att_speed |
| 2 | `physics.a_lim_max` | 30 | **10.5** | Pliska 4/11 = 비 **0.35** × a_att_max |
| 3 | `train.limits.limiter_omega` | 12 | **2–3** | Pliska 최대 선회율 2 rad/s |
| 4 | `attitude.omega_max` | 3.14159 | **2.0** | 동일 |
| 5 | `physics.kill_radius` | 2.0 | **0.75** (0.6–0.9 sweep) | 표적 0.21 + 요격기 0.25 + 종말오차 0.10–0.40 |
| 6 | `viability.cone.range_max` | 29.847 | **C-1 후 재도출** | 자체 문서가 WEAK/FLAGGED |
| 7 | `a_att_max` / `att_speed` | 30 / 20 | **브래킷 + 랜덤화** | 점값으로는 방어 불가 |

**#6 주의**: `range_max` 를 줄이면 `half_angle = arctan(net_r/range_max)` 가 **커져** v_shot 이 관대해집니다
(우리에게 유리). 동시에 축방향 밴드는 **짧아져** 불리합니다. **양방향이라 부호를 미리 단정하면 안 되고,
그래서 더더욱 결과를 보기 전에 선언해야 합니다.**

---

## 4. ★★ 표에 없던 구멍 — 초기조건 랜덤화가 배선되어 있지 않다

```
params.py: "docs/09 SS7: v_nominal, a_lat_max, amp, react_on_commit + spawn geometry
            는 ratified 2B domain-randomization knobs -- config 배선은 2B 에서 착지"
configs:    adversary_start_x: 24.0     <- 고정. 스폰 각도/오프셋 축 없음
```

**2B 가 아직 안 왔습니다. 지금 재학습하면 정책이 고정 스폰을 외웁니다.**

이건 파라미터 값 문제가 아니라 **주장 등급의 상한 문제**입니다.
클레임 거버넌스 사다리(FIXED_CONDITION → MULTI_RESET → DISTRIBUTION_LEVEL)에서
**스폰 랜덤화 없이는 FIXED_CONDITION 을 영원히 못 벗어납니다.**
Q1 논문에서 단일 초기조건 결과는 그 자체로 리젝 사유입니다.

> **재학습 전에 반드시 배선해야 합니다.** τ 관측(1차원)보다 이게 우선입니다.
> 최소: 스폰 x ∈ [22, 26], 방위각 ± φ, 횡오프셋 ± y. 전부 선언 후 동결.

---

## 5. 발사 설계점 — 이 프로젝트에서 근거가 가장 좋은 축

**(θ, v₀, m) 은 우리가 만든 값이 아닙니다. Xu Table 2 의 실험 수준값이고, 7점은 논문의 Pareto frontier 입니다.**

| 파라미터 | 값 | 등급 | 출처 |
|---|---|:---:|---|
| `theta_launch` | 25 / 35 / 45 / 55 / 65 ° | **E** | Xu Table 2 수준 |
| `v_launch` | 50 / 60 / 70 / 90 m/s | **E** | Xu Table 2 수준 |
| `m_block` | 25 / 35 g | **E** | Xu Table 2 수준 |
| 7 설계점 조합 | Baseline/A/B/C/D\*/E\*/F | **E** | Xu Table 8/9 Pareto 해 |
| ↳ `tau_deploy` | 0.253–0.505 s | **D** | 항력 포함 병진 (설계점에서 파생) |
| ↳ `net_radius` | 1.66–2.42 m | **D** | S_NP@교전거리 (설계점에서 파생) |
| 개방 시간 | 0.13 s | **E** | Xu Fig.6 Stage II 종료 |

> **τ 와 r_net 을 독립 축으로 sweep 하면 안 됩니다** (docs/33 §4) —
> 물리적으로 존재하지 않는 (τ, r) 조합을 훑게 됩니다. **설계점이 축입니다.**

---

## 6. 랜덤화 축 — 목록과 판정

| 축 | 범위 | 등급 | acceptable? |
|---|---|:---:|---|
| **발사 설계점** | 7점 이산 | **E** | **최상** — 논문이 이미 평가한 점만 씀 |
| **`w_kill`** | 0 / .25 / .5 / .75 / 1 | **W** | **최상** — 뒤집히는 지점이 곧 결과 |
| `p_kill` | 선언 sweep | W | 좋음 |
| `tau_kill` | `tau_deploy` 비율 sweep | W | 좋음 (자기참조 상수보다 나음) |
| `kill_radius` | 0.6–0.9 | D | 좋음 (§3-5) |
| `r_nk` | 선언 sweep | S | OK — 교전규칙 선언 |
| 공격자 레벨 | A2 학습 / A3 평가 | S | 좋음 — 일반화 확인 형태 |
| `lambda` 프리셋 | 5개 | W | 좋음 |
| seed | 5 (paired) | S | 좋음 |
| **`a_att` / `att_speed`** | 브래킷 | **A→DRAFT** | **C-2 필요.** 문헌은 하한만 준다 |
| **스폰 기하** | **미배선** | — | **★ 배선 필수 (§4)** |
| `dodge_amp` | 미sweep | T | **sweep 권고** — 공격자 강도를 결정 |
| `episode_len` | 미sweep | A | **최소 2점 민감도** |

---

## 7. 총평 — acceptable 한가

**블록별로 갈립니다.**

```
fire_gate        해석적 라벨 대비 보정 + band 실측        -> 모범
viability 샘플러  오차 실측으로 n 결정                    -> 모범
net_radius       외부 2건 교차 확증                       -> 모범
공격자 사다리     값은 임의지만 "최적화 금지" 규율이 방어   -> OK
M4 보상          w_kill 을 값이 아니라 축으로 둠           -> 모범

train.limits     "demo-proven" 3개                       -> 취약
physics 4개      "fixture" 4개                           -> 취약
attitude         pi 를 그냥 씀                            -> 취약
range_max        자체 문서가 WEAK/FLAGGED                 -> 취약
스폰 랜덤화       미배선                                   -> 주장 등급 상한
```

**패턴이 명확합니다: 최근에 만든 것(fire_gate, viability, M4)은 근거가 좋고,
초기 L1 데모에서 넘어온 것(`train.limits`, `physics` fixture, `attitude`)이 전부 임의값입니다.**
데모를 돌리려고 정한 값이 그대로 물리 주장으로 승격돼 남아 있는 구조입니다.

> **답: 지금 상태로는 acceptable 하지 않습니다. §3 의 7개 + §4 의 스폰 랜덤화를
> 처리하면 acceptable 합니다.** 전부 로컬 작업이고, 재학습 전에 끝납니다.

---

## 8. 재학습 전 체크리스트

```
[ ] §4  스폰/초기조건 랜덤화 배선          <- 최우선. 없으면 FIXED_CONDITION 상한
[ ] §3  7개 보정값 선언 (전부 불리한 방향)  <- 결과 보기 전
[ ] §3-6 range_max: C-1 해결 후 재도출     <- 양방향이라 사전 선언 필수
[ ] docs/35 B-7 폐로 기하 정합 (x_fire 13-15)
[ ] tau 관측 1차원 (= 런처 스펙, 은닉 파라미터 아님)
[ ] episode_len 2점 민감도 계획
[ ] dodge_amp sweep 축 추가
[ ] [E] 스케일 스모크 -> terminal_scale 확정
--- Human-lane (병렬) ---
[ ] C-1 Xu PDF 한 문단 (유효면적 기준 시점)
[ ] C-2 FPV 스펙시트 (a_att, att_speed, adversary_omega 동시 확정)
[ ] 발사 설계점 선언: 7점 랜덤화 / 단일 고정 / 3점 축소
```
