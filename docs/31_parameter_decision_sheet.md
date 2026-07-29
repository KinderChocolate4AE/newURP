# 파라미터 결정 작성지 — Hyunjun 레인

**2026-07-27 · `docs/30` §1 의 선행 조건 · 채워서 돌려주면 sweep 축이 확정된다**

---

## 0. 규칙 두 가지

**① 정확한 값이 아니라 브래킷이면 충분하다.**
```
답 형식:   tau_deploy = [0.15, 0.35] s   근거: <한 줄>
```
sweep 이 나머지를 처리한다. `[lo, hi]` + 한 줄 근거면 그 축은 확정된다.
값을 못 정하겠으면 **"모름"** 도 유효한 답이다 — 그 축은 넓은 브래킷으로 sweep 하고 결과를 그 함수로 보고한다.

**② 수치 추출·동결은 Human-lane이다** (프로젝트 규칙 7 / WP-A3 "no direct number extraction").
AI 추출값은 전부 DRAFT 이고 비준 전에는 인용하지 않는다. 아래 "후보 출처"는 **어디를 볼지**의 힌트일 뿐이다.

---

## 1. 왜 이 작성지가 필요한가

실현가능 하한 `N_min ≈ (w³ − ρ³)/r_kill³`, `w = ½·a_att·τ_deploy²`.
탄력도를 실측하면:

```
a=78 (5" FPV), tau=0.4 기준 N_min = 30
  tau_deploy  10% 감소  ->  N_min  30 -> 16   (-47%)   탄력도 ~6
  a_att       10% 감소  ->  N_min  30 -> 22   (-27%)   탄력도 ~3
  r_kill      10% 증가  ->  N_min  30 -> 23   (-23%)   탄력도 ~-3
  net_radius  10% 증가  ->  N_min  30 -> 30   ( +0%)   경계 근처에서만 민감
```

⇒ **`tau_deploy` 하나가 6제곱으로 답을 정하는데 그 값이 `ASSUMED`(근거 없음)다.**
지금 갈래 A/B 를 판정하면 그건 연구 결과가 아니라 fixture 아티팩트다.

---

## 2. 물리 — 외부 근거가 있어야 하는 값

### T1 · 지렛대 6제곱 — 최우선

| | 현행 | 지위 |
|---|---:|---|
| **`physics.tau_deploy`** | 0.40 s | **ASSUMED** — "prototype reachset fixture" |

**답해야 할 질문**
> 네트가 발사된 뒤 **유효 요격 면적에 도달하기까지** 걸리는 시간은?
> (완전히 펴져 낙하를 마치는 시간이 아니다 — 요격에 쓸 수 있게 되는 시점)

**후보 출처**: `params.py` 의 `n1.hang_time_paper = 1.853 s` 가 Xu et al. *Drones* 9:190 에서 **MEASURED** 로 등록돼 있다. 다만 이것이
- (a) 발사 → 유효 면적 도달, 인지
- (b) 발사 → 완전 낙하 종료, 인지

가 구분돼 있지 않다. **`tau_deploy` 는 (a) 여야 한다.** 같은 파일 주석에 *"sim does NOT reproduce it (breathing-net limitation → all sim-temporal outputs untrusted)"* 라고 적혀 있어 시뮬 값으로는 대체 불가.
FRPN/Pliska Paper 1 의 engagement envelope 도 후보.

```
답:  tau_deploy = [____, ____] s      근거: ______________________
```

---

### T2 · 지렛대 3제곱

| | 현행 | 지위 |
|---|---:|---|
| **`physics.a_att_max`** | 30 m/s² (~3 g) | **ASSUMED** — 파일이 스스로 *"whether 3 g / 0.4 s is the operational FPV regime is an open assumptions-register question"* 라고 표기 |

**답해야 할 질문**
> 우리가 막겠다고 선언하는 위협 플랫폼은 무엇인가? 그 기체의 **횡기동 가속 한계**는?

**AI 추출 DRAFT (검증 대기)** — 확정 전 인용 금지:
```
무장 FPV (7~10", 탄두 탑재)  TWR 3~5    a_lat  28 ~ 48 m/s²
DJI FPV 급 (795 g, 비무장)              실측 종가속 하한 13.9 m/s²
5" 프리스타일                TWR 8~10   a_lat  78 ~ 98
레이싱                       TWR 10~14  a_lat  98 ~ 137
```
(출처: 제조사 사양 + FPV TWR 관행. **"무장 FPV TWR 3~5" 는 관행 추정이며 실측 앵커가 없다.**)

```
답:  위협 등급 = ______________   a_att_max = [____, ____] m/s²
     근거: ______________________
```

| | 현행 | 지위 |
|---|---:|---|
| **`physics.kill_radius`** | 2.0 m | **ASSUMED** — *"no external grounding"* |

**답해야 할 질문**
> limiter 자폭체의 **소형 쿼드에 대한 유효 살상반경**은? (인원 살상반경이 아니라 기체 무력화 반경)

```
답:  kill_radius = [____, ____] m     근거: ______________________
```

---

### T0 · 이미 근거 있음 — 확인만

| | 현행 | 확인 사항 |
|---|---:|---|
| `physics.net_radius` | 2.00 m | **DERIVED/실측** (Xu S_NP=12.54 → √(S/π)). 단 파일 주석: *"equivalent-AREA radius, NOT worst-case inradius — r_in ≤ 2.0, 실제 네트는 최악 방향에서 더 작다."* **최악 방향 값을 쓸지 결정 필요** |
| `viability.cone.range_max` | 29.847 m | **DERIVED 이지만 "N1 WEAK/FLAGGED"** — *"sim collapse timing untrustworthy → conservative smaller value adopted"*. 유효 사거리를 실측으로 대체할 수 있는지 |
| `viability.cone.half_angle` | 0.067 rad | 위 두 값에서 유도 — 독립 결정 불필요 |

```
답:  net_radius 최악방향(inradius) 사용? Y / N   값 = ____ m
     cone range_max 실측 대체 가능? Y / N        값 = ____ m
```

---

## 3. 설계 — 근거가 아니라 **선언**이 필요한 값

물리가 아니라 우리가 정하는 것이다. 브래킷만 있으면 sweep 축이 된다.

| | 현행 | 답해야 할 질문 |
|---|---:|---|
| **limiter 플랫폼 등급** | `a_lim 30` / `v_lim 80` | 싼 shaping 기체는 무엇인가? **`v_lim = 80 m/s`(288 km/h)는 비물리** — 현실 브래킷 필요. `rho_v = v_lim/v_att_max` 가 1순위 sweep 축 |
| **`finisher.K`** | 1 shot | 네트 발사 기회를 몇 번 갖는 플랫폼인가? K=1 이 baiting 을 지배 전략으로 만든다 |
| **교전 개시 거리** | spawn `x=24 m`, horizon `4.0 s` | **어느 거리에서 탐지·교전을 시작하는가?** 이게 전체 시간 예산을 정한다 |
| **`R_nk`** | 6.0 m | 파괴적 요격 금지 반경 = **잔해 낙하 범위**. 교전 고도에 의존 |
| **`tau_kill`** | 0.1 s | 자폭체 커밋 → 기폭까지 지연. τ_deploy 와 같은 성격 |
| **`Pk`** | sweep | 기동 회피 표적에 대한 자폭 요격 성공률의 **그럴듯한 범위** |
| **`w_kill`** (M4 보상) | 미설계 | **비손실 1회가 파괴적 1회보다 몇 배 가치 있는가?** 이게 §6 의 핵심 노브 |

```
답:  limiter 등급 = ____________  v_lim = [__, __] m/s   a_lim = [__, __] m/s²
     K = ____        교전 개시 거리 = ____ m / 시간예산 = ____ s
     R_nk = ____ m   tau_kill = [____, ____] s
     Pk = [____, ____]          w_kill 배수 = [____, ____]
```

---

## 4. 우선순위 — 시간이 없으면 위에서부터

```
1  tau_deploy        6제곱. 이것만 있어도 지도의 어느 열을 읽을지 정해진다
2  a_att (위협 등급)  3제곱. 브래킷은 이미 DRAFT 로 있음 -> 검증만
3  kill_radius       3제곱
4  limiter 등급 · 교전 거리 · K
5  R_nk · tau_kill · Pk · w_kill
```

**1번만 답해도 다음 블록이 훨씬 좁아진다.** 나머지는 넓은 브래킷으로 sweep 하면 된다.

---

## 5. 그동안 내가 하는 것

이 작성지를 기다리지 않는다. **`tau` 축 위에서 oracle + 명제 N(b) 를 돌린다** — 지도를 τ 의 함수로 전부 그려두면, τ 근거가 나중에 확정돼도 **지도를 다시 그릴 필요 없이 읽을 열만 정해진다.** 그리고 그 지도 자체가 갈래 B2 의 산출물(하드웨어 요구사항 스펙 시트)이다.

같은 논리가 다른 축에도 적용된다 — **미근거 파라미터는 고정하지 말고 축으로 둔다.** 그러면 근거가 늦게 와도 작업이 낭비되지 않는다.
