# 물리 파라미터 가정 원장 — 각 값이 무엇 위에 서 있는가

**2026-07-29 · `params.py` / `configs/m2_l2_train.yaml` / `net_forward.py` / `n1_net_grounding.md` 전수**
**`docs/36` 은 "방어 가능한가"를 등급으로 물었고, 이 문서는 "무엇 위에 서 있는가"를 사슬로 묻는다.**

---

## 0. 보강 필요 항목 — 우선순위

**레버리지 순.** 위 3개는 각각 **여러 파라미터를 동시에** 움직인다.

| 순위 | 항목 | 흔들리면 같이 움직이는 것 | 필요한 것 | 담당 |
|:---:|---|---|---|---|
| **1** | **A1 · Xu 유효면적 기준 시점** | `rho_air` → `tau_deploy` → `range_max` → `half_angle` | **PDF 한 문단** | Human |
| **2** | **A5 · 공격자 플랫폼 등급** | `a_att_max`, `att_speed`, `adversary_omega`, `R_reach`, 포획 성립 판정 전부 | **FPV 스펙시트** | Human |
| **3** | **A6 · 능력 대등 가정** | `a_lim_max`, `limiter_v_max`, `limiter_omega`, `omega_max` | **선언만 하면 됨** (근거는 확보) | 즉시 |
| 4 | A2 · 네트 전방 모델 충실도 | `tau_deploy`, `range_max`, hang time | flat-init·wrapping 한계 명시 | 문서 |
| 5 | A7 · `kill_radius` 근거 | 하드킬 팔 전체 (3제곱) | **선언만 하면 됨** | 즉시 |
| 6 | A8 · `dt` 와 `tau` 의 양자화 | 짧은 τ 로 가면 `n_dep` 반올림 오차 15% | dt 재검토 | 즉시 |
| 7 | A3 · 등가면적 반경 = 구 근사 | `net_radius`, 포획 판정 낙관 | 최악방향 내접반경 계산 | 로컬 |
| 8 | A4 · 회랑 1차원 접근 | 일반화 주장 등급 | **부분 해제됨** (docs/37) | 진행중 |
| 9 | A9 · 지평선 | TRUNCATED 질량 | **해제됨** (160 선언) | 완료 |

**3·5·6 은 지금 선언만 하면 되고, 1·2 는 Human-lane 두 건입니다.**
나머지는 문서화 또는 이미 처리됐습니다.

---

## 1. ★ 공유 상류 가정 — 하나가 흔들리면 여러 개가 움직인다

파라미터를 하나씩 보면 놓치는 구조가 있습니다. **A1 은 단일 실패점입니다.**

```
                    Xu 2025 논문 보고값 C (Eq.12)
                              |
                              | (역산: S = S_UAV / (1 - ln C))
                              v
    [A3] 등가면적 근사 <---  S_NP = 12.54 m^2  ---> net_radius = 2.0 m
                              |                     (구 근사, 최악방향 아님)
                              |
              [A1] "이 면적은 어느 시점/거리의 것인가?"  <== ★ 미확인
                              |
                    engage_dist = 20 m 로 가정
                              |
                              v
                 rho_air = 1.513 (그 거리에서 맞도록 보정)
                    |                    |
       [A2] 전방모델 |                    |
       (flat-init,   v                    v
        wrapping 없음) tau_deploy = 0.4    range_max = 29.847
                       (병진 시간)         (붕괴 타이밍, WEAK)
                                              |
                                              v
                                    half_angle = arctan(2.0/29.847)
                                              = 0.067 rad
```

**A1 이 틀리면 `rho_air` · `tau_deploy` · `range_max` · `half_angle` 이 한꺼번에 움직입니다.**
그리고 `docs/34 §4` 는 틀렸을 가능성이 실재한다고 봅니다 — Xu 는 네트가 **t≈0.13 s 에
최대 면적**이라고 보고하는데, 우리 병진 시뮬로 그 시점의 이동거리는 **6–11 m** 입니다.
20 m 는 그 두 배이고, 만약 논문의 보고 면적이 최대 면적이면 보정 거리가 틀린 것입니다.

> `net_radius = 2.0` **만은 A1 에 독립**입니다 — 논문 C 의 역산이지 시뮬 결과가 아닙니다.
> 시뮬이 1.998 을 재현하는 것은 교차검증일 뿐입니다. **가장 튼튼한 앵커가 여기 있습니다.**

---

## 2. 보강 필요 항목 상세

### A1 · Xu 유효면적의 기준 시점 — **미확인, 최대 레버리지**

```
가정:  논문이 보고한 유효 포획 면적은 "발사 후 20 m 병진 시점"의 면적이다
근거:  없음. net_forward.py 주석: "pre-fixed engagement travel distance ... NOT tuned per-config"
반증:  Xu §3.2/Fig.6 — 최대 면적은 t≈0.13 s, 그때 병진은 6~11 m (docs/34 §4)
영향:  (a) 이면 rho_air 재보정 -> tau 전부 하향 (항력 과다였다는 뜻)
       (b) 이면 그 거리를 engage_dist 로 채택하고 현행 유지
비용:  PDF 한 문단
```

### A5 · 공격자 플랫폼 등급 — **미확인, 두 번째 레버리지**

```
가정:  a_att_max = 30 m/s^2, att_speed = 20 m/s 가 "실제 FPV 위협"을 대표한다
근거:  params.py 원문 = "fixture (~3 g)" / "fixture". **없다.**
외부:  문헌 표적은 전부 연구용 쿼드다 — Pliska 최대 11 (평균 1.4), MAV-capture 10 m/s^2;
       속도 0~8 / <=5 / 0~4 m/s. **하한만 준다.**
지금 할 수 있는 말: "우리 시나리오는 공개된 모든 실험보다 2.5~5배 어렵다"
필요: DJI FPV / 7인치 급 스펙시트 (Hyunjun 기존 지시)
주의: 스펙시트는 **상한을 넓히기 위한 것**이지 현 설정을 정당화하기 위한 게 아니다.
      점값은 어차피 방어 불가 -> 브래킷 랜덤화가 답이다.
```

### A6 · 능력 대등 가정 — **근거는 확보됨, 선언만 남음**

```
가정:  a_lim_max = a_att_max = 30,  limiter_v_max = 80 = 4 x att_speed
근거:  "fixture (= attacker authority)" / "demo-proven backend limit"
반증:  Pliska (RA-L, Q1, 실기) — 요격기 4 m/s^2 vs 표적 최대 11 (비 0.36),
       속도는 8 vs 8 로 동률. **속도 대등, 가속 열세**가 문헌의 형태다.
영향:  방어자를 과대평가한 채 학습하면 모드 중재 결과가 전부 낙관 편향
조치:  a_lim -> 0.35 x a_att, limiter_v_max -> 1.0 x att_speed, omega -> 2 rad/s
```

### A7 · `kill_radius` — **근거 확보됨, 선언만 남음**

```
가정:  2.0 m
근거:  params.py 원문 = "kamikaze lethality fixture (no external grounding)"
대안:  접촉 요격 기하 = 표적 반치수 0.21 + 요격기 0.25 + 종말오차 0.10~0.40
       = 0.56 ~ 0.86 m   (표적 420x420 mm, 위치오차 <10 cm, 탐지오차 <0.4 m)
영향:  현행은 부피로 12~46배 관대. **3제곱 지렛대**라 하드킬 팔을 크게 과대평가
방향:  우리에게 불리 -> 지금 선언하면 소급 의심 없음
```

### A8 · `dt` 와 `tau` 의 양자화 — **새로 발견**

```
가정:  dt = 0.05 s (20 Hz) 로 tau_deploy 를 나눠떨어지게 표현할 수 있다
현실:  분석 경로가 n_dep = round(tau_deploy / dt) 로 스텝을 센다
       tau=0.40 -> 8 스텝 (정확)
       tau=0.25 -> 5 스텝 (정확)
       tau=0.13 -> 3 스텝 = 0.15 s  ** +15% 오차 **
영향:  docs/34 §4 의 최적 발사창(tau≈0.13)으로 가면 dt=0.05 가 부정확해진다
조치:  발사 설계점을 선언할 때 dt 도 함께 본다. tau <= 0.2 를 쓸 거면 dt=0.02 급 필요
       (탐지 10 Hz / 제어 100~500 Hz 사이라는 dt 논증 자체는 유지된다 — 20 Hz 가
        결정 루프고, 적분 스텝은 별개로 잘게 가도 된다)
```

### A3 · 등가면적 반경 = 구 근사 — 낙관 방향

```
가정:  net_radius = sqrt(S_NP/pi) 인 구가 포획 볼륨이다
현실:  params.py 캐비앗 원문 — "equivalent-AREA radius, NOT worst-case inradius;
       r_in <= 2.0, so real net is smaller in the worst direction"
영향:  포획 판정이 최악방향에서 낙관적. 얼마나인지 **아직 계산 안 함**
조치:  net_forward 의 전개 형상에서 최악방향 내접반경을 재면 된다 (로컬, 반나절)
```

### A2 · 네트 전방 모델 충실도

```
D1  항력이 ||v|| 에 선형 (논문 재현 목적). 물리 표준은 2차 -> 문서화된 이탈
D3  rho_rope 970 vs Table-1 1440 충돌. 감쇠에만 들어가고 질량은 실측 170 g 이라 무해
flat-init  접힘->펴짐 천이가 없다. t=0 에 이미 27 m^2 -> **t < 0.13 s 구간 무효**
wrapping   얽힘 없음 -> 네트가 "숨쉰다"(0.66 s 붕괴 후 재개방) -> hang time 재현 실패
영향:  tau(병진)는 견딤. range_max(붕괴)는 **못 견딤** -> WEAK 표기의 실체
```

### A4 · 회랑 1차원 정면 접근 — **부분 해제됨**

```
과거:  p0=[24,0,0], v0=[-20,0,0] 고정. 모든 에피소드 초기조건 비트 동일
현재:  docs/37 — x ±2 m, 횡 5 m 원판(면적균일), 표적 정조준
남은것: 방위각(psi) / 속력(speed_frac) / dodge_amp 는 축만 열고 off (A5 대기)
```

### A9 · 지평선 — **해제 완료**

```
과거:  episode_len = 80 (4 s). ring 배치 + 랜덤 스폰에서 TRUNCATED 13/30
현재:  160 선언 (shepherd/m4_config.py). H=160 과 H=320 이 동일 -> 수렴 확인
```

---

## 3. 전체 파라미터 × 가정 사슬

### 3.1 physics

| 파라미터 | 값 | 서 있는 가정 | 사슬 |
|---|---:|---|---|
| `dt` | 0.05 s | **A8** · 20 Hz 가 결정 루프 (탐지 10 / 제어 100–500 사이) | 독립 — 단 τ 양자화와 결합 |
| `tau_deploy` | 0.4 s | **A1 · A2** | Xu C → S_NP → rho_air@20 m → 병진시간 |
| `tau_lock` | 0.1 s | 탐지 1주기(10 Hz)면 불가역 커밋이 자연스럽다 | 독립. 사후 정당화 |
| `net_radius` | 2.0 m | **A3** (+ Xu 의 C 와 Eq.12 가 정확하다) | **A1 에 독립** ← 가장 튼튼 |
| `a_att_max` | 30 m/s² | **A5** | 없음 |
| `att_speed` | 20 m/s | **A5** | 없음 |
| `kill_radius` | 2.0 m | **A7** | 없음 |
| `a_lim_max` | 30 m/s² | **A6** | `a_att_max` 에 결박(= 1.0×) |

### 3.2 attitude · viability · fire_gate

| 파라미터 | 값 | 서 있는 가정 | 사슬 |
|---|---:|---|---|
| `attitude.omega_max` | 3.14159 | **A6** (+ "반 바퀴/초"라는 수사) | 없음 |
| `viability.judge` | se3_cone | 콘이 네트 볼륨의 타당한 대리 | ablation 존재 |
| `viability.n_samples` | 2000 | **오차 실측**으로 결정 (n=500 err 0.190 > band 0.15) | **자립** |
| `viability.n_segments` | 4 | >1 이면 보수적(단조). 왜 4인지는 없음 | 방향만 안전 |
| `cone.half_angle` | 0.067 rad | `net_radius` / `range_max` | **A1 종속** |
| `cone.range_max` | 29.847 m | **A2** (붕괴 타이밍) — 자체 WEAK 표기 | **A1 · A2 이중 종속** |
| `fire_gate.theta_fire` | 0.9 | **해석적 라벨 대비 보정**, band [0.85,1.0] 실측 | **자립** |
| `fire_gate.c_fire` | 0.9 | = θ×B (assert 강제) | 도출 |

### 3.3 회랑 기하 · 백엔드 한계

| 파라미터 | 값 | 서 있는 가정 |
|---|---:|---|
| `target` / `target_radius` | (0,0,0) / 1.0 | 설계 선언 (보호점) |
| `ring_center` / `ring_radius` | (8,0,0) / 5.0 | 설계 선언. **우연히 최적 발사창 6–11 m 안** (docs/34 §4) |
| `finisher_p0` | (2,0,0) | 설계 선언. `spawn_bank` 가 STRICT 강제 |
| `adversary_start_x` | 24.0 | **A4** — 이제 ±2 m 랜덤화 |
| `r_ring` | 2.1 | L1 데모 튜닝. **baseline 전용, 학습정책 무시** |
| `x_fire` | 11.0 | L1 데모 튜닝. baseline 전용. docs/35 는 13–15 권고 |
| `episode_len` | **160** | **A9 해제** — 수렴 실측 |
| `limiter_v_max` | 80 | **A6** |
| `limiter_omega` | 12 | **A6** |
| `adversary_omega` | 10 | **A5** |
| `adversary_v_max` | 30 | `att_speed` 의 헤드룸 (파생) |
| `finisher_a_max/v_max` | 1.0 | 설계 선언 (finisher 는 사실상 정지) |

### 3.4 M4 신규 (env_sys)

| 파라미터 | 값 | 서 있는 가정 |
|---|---:|---|
| `tau_kill` | 0.1 s | `tau_deploy` 의 1/4 — **자기참조**. τ 가 바뀌면 같이 움직여야 |
| `p_kill` | 1.0 | 선언 sweep 축 |
| `r_nk` | 6.0 m | 교전규칙 선언 (no-kinetic zone) |
| `commit_threshold` | 0.5 | env fire logit 규약과 동일 (일관성이 근거) |
| `w_kill` | 0.5 | **선언 sweep 축 — 뒤집히는 지점이 결과** |
| `b_net`/`c_pen`/`c_trunc` | 1.0 | 정규화. 순서 불변식은 P13 이 강제 |
| `c_lim` | 0.1 | 없음 → 민감도 |
| `dense_scale`/`terminal_scale` | 1.0 / 10.0 | **[E] 스케일 스모크로 결정 예정** (사전등록) |

### 3.5 공격자 사다리 — 값이 아니라 **규율**이 방어한다

| 파라미터 | 값 | 서 있는 가정 |
|---|---:|---|
| `homing_gain` | 4.0 | `adversary.fwd_gain` **상속 → 신규 자유도 0** |
| `adversary.fwd_gain` | 4.0 | 회랑용 손튜닝. **방어 설계 이전에 정해짐** |
| `adversary.dodge_amp` | 1.8 | 동일. 공격자 강도를 결정 → sweep 권고 |
| `lam_gain`/`lam_range` | 프리셋 5 | 선언 sweep 축 |
| `jink_amp`/`jink_freq` | 0 / 1.5 Hz | 없음. **선언·동결 + 최적화 금지(rule 2)가 방어** |
| `jink_terminal_r` | 3.0 m | 유도 문헌의 종말 게이트 (거동 정의, 튜닝 아님) |
| `bait_*` | 0.5 / (4,16) / 3.0 | 없음. A3 효과 미측정이라 현재 무영향 |

> **사다리에서 개별 값을 정당화하려 하면 안 됩니다.** 정당화하는 것은
> *"공격자 파라미터는 선언·동결하고 절대 최적화하지 않는다"* 는 규율이고,
> 그게 논문에 쓸 문장입니다.

---

## 4. 무엇을 하면 무엇이 풀리나

```
A1 (PDF 한 문단)      -> rho_air · tau_deploy · range_max · half_angle  4개 동시 확정
A5 (FPV 스펙시트)      -> a_att · att_speed · adversary_omega + 브래킷 랜덤화 개시
A6 (선언)             -> a_lim · limiter_v_max · limiter_omega · omega_max  4개
A7 (선언)             -> kill_radius + 하드킬 팔 재평가
A8 (dt 재검토)        -> 짧은 tau 운용 가능 여부
A3 (로컬 반나절)      -> net_radius 의 낙관 폭 정량화
```

**A6 · A7 은 오늘 선언 가능하고, 그것만으로 `docs/36` 의 "고쳐야 할 7개" 중 5개가 닫힙니다.**
남는 둘(`range_max`, `a_att/att_speed`)이 정확히 A1 · A5 이고, 둘 다 Human-lane 입니다.

---

## 5. 오늘 반영된 것

| | |
|---|---|
| `shepherd/m4_config.py` (신규) | M4 운용점 선언 한 곳. 현재 `train.episode_len: 160` **하나뿐** |
| `tests/test_m4_config.py` (신규) | P28 — 선언 목록 밖 오버라이드 금지 · 근거·날짜 필수 · 동결 YAML 무변경 |

`M4_PROVENANCE` 에 항목별 날짜·근거·문서참조를 강제하고, `PENDING` 에 §0 의
선언 대기 7건을 적어 두었습니다. **결과를 본 뒤 조용히 추가되는 경로를 막는 것이
이 파일의 목적입니다.**
