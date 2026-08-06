# 53 — 성공 술어 재구성: robust-clean **인증**과 임무 가치의 분리

**2026-08-06 · 결정 메모. 아직 사전등록이 아니고, 계약 변경도 하지 않았다.**

---

## 0. 문제 제기

현행 성공 술어는

```
포획 = (not boxed_in) and (v_shot_worst >= 1.0)
     = 살아남은 탈출이 1 개 이상 ∧ **전부** 원뿔 안
```

이다. 이건 *"비손실 포획을 최대화하는 방어"* 가 아니라 **"한 번의 발사로 모든
가능한 탈출을 확실히 제거한 경우만 성공으로 인정하는 인증 문제"** 다.

그래서 다음 두 상태를 **거의 같은 실패**로 취급한다:

```
net 이 99.9 % 의 대응을 포획하고 miss 시 하드킬 handoff 도 가능한 상태
net 이 거의 아무 방향도 포획하지 못하는 상태
```

방어 관점에서 전혀 다른 상태다.

---

## 1. ★ 코드로 확인한 것 두 가지

### 1.1 net miss 는 **즉시 임무 종료**다 — handoff 가 구조적으로 불가능

`shepherd/env.py:356`:

```python
spent_fail = bool(self.fsm.state is FinisherState.SPENT and not captured)
```

이것이 **종료 조건**이다 (`mission_rollout.py:324` 가 `SPENT_FAIL` 라벨로 받는다).
즉 그물이 빗나가면 그 자리에서 에피소드가 끝난다:

```
limiter 재요격        없음
하드킬 handoff        없음 (커밋 비트는 탄 소진 **전**에만 작동)
두 번째 방어선        없음
```

**handoff 를 말하면서 환경은 handoff 가치를 학습할 수 없다.** 이건 개념과 구현의
**내부 모순**이지 난이도 조정 문제가 아니다.

### 1.2 `v_soft` 는 포획 **확률이 아니다**

`_assemble`: `v_shot_soft = caught[feasible].mean()` 인데 그 표본은 union 이다:

```
Block 1  uniform-in-ball 2000 개
Block 2  boundary spheres  (‖a‖ = a_max)
Block 3  bang-bang doglegs
Block 4  turn curves
```

블록마다 표본 밀도가 다르고 **확률질량 가중이 없다.** 보수적 extreme point 는
실제 A2 가 고를 가능성과도 다르다. 따라서

> `v_soft = 0.9` → 포획확률 90 %

로 읽으면 **안 된다.** 확률적 목적을 쓰려면 (a) 공격자 정책 rollout 기반 추정,
(b) 공격자 모델 분포에 대한 CVaR·분위수, (c) `v_soft`/`v_worst` 이중 지표 중
하나를 명시해야 한다. **(c) 가 현 코드에서 가장 작은 변경**이다.

---

## 2. 2b 결과의 재해석 — 이건 지금 바로 고칠 수 있다

기존:

> clean capture 가 가능한 배치는 수 cm 폭뿐이다.

정정:

> **최악의 feasible escape 까지 전부 net 안에 넣는 robust-clean certificate 가
> 수 cm 폭의 좁은 corner 다.**

즉 docs/52 §8.1d~e 는 **전체 최적 방어를 측정한 것이 아니라 Pareto frontier 의
가장 보수적인 끝점을 측정**했다. 그 바깥에는 측정되지 않은 넓은 상태가 있을 수
있다:

```
v_soft 0.95 + handoff 용이
v_soft 0.85 + 하드킬 가드 확보
v_soft 0.70 + 침투까지 충분한 시간
```

**docs/52 의 knife-edge 는 여전히 유효한 측정이다.** 다만 그것이 뜻하는 바가
*"협력 성형이 거의 불가능"* 이 아니라 *"완전 강건한 비손실 포획은 매우 좁다"* 로
바뀐다. 확률적 포획 + fallback 을 포함한 최적 방어 frontier 는 **아직 측정된 적이
없다.**

---

## 3. 제안하는 변경 (★ 아직 실행하지 않음)

### 3.1 miss 를 mode transition 으로

```
NET_CAPTURE  -> 성공 종료
NET_MISS     -> NET_SPENT / FALLBACK_MODE -> limiter 하드킬 등 방어 계속
```

### 3.2 인증과 임무 보상을 분리

`v_worst == 1` 은 **버리지 않는다.** 지위를 바꾼다:

```
현재  유일한 성공 술어
변경  분석용 강건성 지표 / robust-clean 라벨 / 최우선 비손실 성공 보너스
```

기본 임무가치는 결과 기반으로:

```
R = R_net − c_lim·N_lost − c_penetration + R_handoff_success
```

셰이핑도 `Δv_soft` 하나가 아니라 defense value potential 에 가깝게:

```
Φ(s) = P̂(net capture) + α·P̂(fallback | net miss) − β·P̂(penetration)
```

### 3.3 평가는 단일 성공률이 아니라 frontier

비손실 포획률 · 전체 무력화율 · 하드킬 전환율 · limiter 손실 · 침투율 ·
net 사용률 · wasted fire · handoff 성공률을 **같이** 본다. `w_kill` 이 그
frontier 를 스윕하는 축이 된다 -- 지금은 완전 clean 만 세므로 그 축을 보기 전에
대부분 상태가 0 으로 뭉개진다.

---

## 4. ★ 이것은 **동결된 계약의 변경**이다

`docs/09:1687` -- *"환경/보상/관측·행동 계약은 **동결**(학습 편의로 미변경)"*.

따라서 이 변경은 비준 절차를 밟아야 하고, 정당화는 **"학습이 잘 안 되니까"** 가
아니라 다음이어야 한다:

> **§1.1 의 내부 모순.** 시스템 개념에 mode handoff 가 있는데 환경은 net miss 에서
> 종료한다. 이는 학습 편의 조정이 아니라 **모델링 오류 수정**이다.

### 4.1 ★ 전제 확인 완료 (2026-08-06) — **모순이 맞다**

`docs/29_m4_mode_system_design.md` 는 제목부터 **"M4 — 모드 전환 방어 시스템
설계"** 이고 3 행에 이렇게 적혀 있다:

> **Hyunjun 확정: 2모드 + 1핸드오프 / 기하 + Pk**

그리고 §2 가 폴백의 근거를 이론에서 유도한다:

> **모드의 존재 이유가 이론에서 나온다. 하드킬이 폴백인 것은 임의 설계가 아니라
> `τ_kill ≪ τ_deploy` 의 귀결이다.**

```
τ_deploy 0.4 s  ->  w = ½·a·τ² = 2.40 m > ρ = 2.0 m   네트 FAIL
τ_kill   0.1 s  ->  w = 0.15 m         < r = 2.0 m   하드킬 OK (여유 13 배)
교차점 τ* = √(2r/a) = 0.365 s
```

**즉 "1 핸드오프" 는 비준된 설계이고 그 폴백이 하드킬이다.** 그런데
`env.py:356` 은 net miss 에서 에피소드를 끝낸다 -- **핸드오프가 한 번도 발동될
수 없다.**

```
비준된 설계   2 모드 + 1 핸드오프 (네트 실패 -> 하드킬 폴백)
현행 구현     네트 실패 -> SPENT_FAIL -> 즉시 종료. 폴백 없음
```

**이것은 학습 편의 조정이 아니라 구현이 비준된 설계를 따르지 않는 것이다.**
§3.1 의 정당화 근거가 성립한다.

### 4.2 같이 확인해야 할 것 (미확인)

`docs/29 §1.1` 은 *"가둠이 실패로 채점돼 있었다 ... 가둠이 치명적이면 가둠은
**성공**이다(파괴적일 뿐)"* 라고 적고 그것을 비정합으로 지목했다. 그런데
`viability` 는 **여전히** `boxed_in` 을 clean net-shot 이 아닌 별도 신호로
보고한다 (R4 SPLIT). 이것이

```
(a) docs/29 의 지적이 커밋 비트 경로(HARD_KILL 라벨)로 해소된 것인지
(b) 아직 남아 있는 두 번째 비정합인지
```

### 4.3 ★ 판정 = **(b), 그리고 예상보다 나쁘다** (2026-08-06)

`env_sys.py:232-292` 를 읽었다. 하드킬은 **접촉이 아니라 커밋으로 발동한다**:

```python
for i, lid in enumerate(inner.limiter_ids):
    a = actions.get(lid, ...)
    if len(a) >= 4 and float(a[3]) > spec.commit_threshold:   # ★ 커밋 비트
        proposals.append(i)
...
rec.geometric_ok = (d_nom <= margin)      # 커밋 **시점**에 동결
...
if d_asset <= spec.r_nk:   rec.outcome = "VETO_NO_KINETIC"    # 가드 거부권
elif not rec.geometric_ok: rec.outcome = "GEOM_FAIL"
elif self._bern(...):      rec.outcome = "KILL"               # Bernoulli Pk
else:                      rec.outcome = "PK_FAIL"
```

**즉 공격자가 limiter 의 `kill_radius` 를 통과해도 아무 일도 일어나지 않는다.**
접촉 기반 event resolver 가 **존재하지 않는다.** 무력화는 오직

```
커밋 비트 ∧ 커밋시점 기하 ok ∧ no-kinetic zone 밖 ∧ Bernoulli Pk 통과
```

일 때만 난다.

**따라서 `boxed_in` 은 kill certificate 가 아니라 surrogate diagnostic 이다.**
*"모든 surrogate escape 가 limiter 반경과 교차한다"* 와 *"실제 공격자가
무력화됐다"* 사이를 연결하는 것이 **환경에 없다.**

docs/29 §1.1 이 *"가둠이 치명적이면 가둠은 성공"* 이라고 적었는데, 그 **전건이
구현돼 있지 않다.** 조건문의 조건부가 미충족이므로 (a) 가 아니라 **(b)** 다.

#### 부수 확인

- 기저선 경로는 `_zero_commit` 으로 index 3 을 0 으로 만든다 -> **커밋을 절대
  안 한다** -> 하드킬 0. `hold` 의 비손실 1.00 이 여기서 설명된다.
- 스크립트 발사 규칙은 `clean_crossed = threshold_crossed and not boxed_in`
  이라 **boxed 상태에서 쏘지 않는다.** 탄 낭비는 없다.
  다만 **학습 finisher 는 관측만 보므로 boxed 상태에서 쏠 수 있다** --
  그 경우 `SPENT_FAIL` 즉시 종료다.

### 4.4 그래서 docs/52 의 어떤 표현을 고쳐야 하나

perturbation 감사의 3 분류를 이렇게 다시 쓴다:

```
덜 막음      -> net miss 위험
clean 띠     -> robust-clean net opportunity
너무 막음    -> non-clean **boxed state**.
                destructive success 인지 handoff 후보인지 **미확정**
                (접촉 resolver 가 없으므로 현재로선 아무것도 아님)
```

**knife-edge 결과 자체는 안 바뀐다** -- robust-clean certificate 가 uncovered 와
boxed 사이 수 cm 폭이라는 측정은 그대로다. **boxed 쪽을 "임무 실패" 라고 부른
해석만 보류**한다.

### 4.5 3-arm 감사 — ★ **판정표 (실행 전 고정, 2026-08-06)**

```
대상       저장된 boxed_in = True 상태 최소 20 개 (동일 상태에서 분기)
A / B      현행 코드 **무수정**. 구현 감사다
C1 / C2    격리된 counterfactual branch. **본선 환경 변경이 아니다**
규율       결과를 본 뒤 성공 정의를 바꾸지 않는다
```

| arm | 무엇 | 지위 |
|---|---|---|
| **A** | 발사 안 함, 커밋 안 함, 현행대로 진행 | 현행 감사 |
| **B** | 즉시 발사, 현행대로 | 현행 감사 |
| **C1** | 발사하되 **종료만 억제**, 기존 커밋/하드킬 경로 유지 | 계약 후보 prototype |
| **C2** | C1 + **접촉 resolver**(`d <= kill_radius` -> 무력화 event) | 계약 후보 prototype |

**C1 과 C2 를 섞지 않는다** -- 섞으면 *"handoff 의 효과"* 와 *"새 접촉 resolver 의
효과"* 를 분리할 수 없다.

기록: 실제 접촉 여부·시각 · limiter 최소거리 · 최종 라벨 · 침투 · `boxed_in`
지속 · limiter 소모.

**사전 해석표:**

| 관측 | 의미 |
|---|---|
| A 에서 실제 접촉 후에도 침투 | 접촉 resolver 부재가 임무 결과를 왜곡 |
| A 에서 실제 접촉이 거의 없음 | `boxed_in` 과 A2 실제 궤적 사이 **fidelity 문제** |
| B 가 즉시 `SPENT_FAIL` | handoff 계약 불일치의 런타임 확인 |
| C1 만으로 회복 | **즉시 종료**가 주된 비정합 |
| C1 실패, C2 에서 회복 | **접촉 resolver 부재**가 추가 병목 |
| C2 도 실패 | boxed surrogate 가 실제 무력화 가능성을 보장하지 않음 |

### 4.5b ★ 3-arm 결과 (2026-08-06, boxed 상태 17 판)

| arm | n | 접촉 | 침투 | 하드킬 | 무력화 | 최소거리 중앙 | 종료 스텝 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A** 현행·무발사 | 17 | **0.765** | **1.000** | 0.000 | 0.000 | 0.487 | 36 |
| **B** 현행·즉시발사 | 17 | 0.706 | 0.000 | 0.000 | 0.000 | 0.551 | **25** |
| **C1** 종료 억제 | 17 | 0.706 | **0.941** | 0.000 | 0.000 | 0.551 | 25 |
| **C2** + 접촉 resolver | 17 | 0.706 | **0.235** | 0.000 | **0.706** | 0.604 | 24 |

(`kill_radius = 0.75`. 최소거리 중앙 0.487~0.604 는 전부 그 **안쪽**이다.)

#### A — fidelity 문제가 **아니다**. resolver 부재가 맞다

`boxed_in` 상태에서 **실제 A2 가 76.5 % 에서 limiter 의 `kill_radius` 안으로
들어간다.** surrogate 가 실제 궤적을 헛짚은 게 아니다. 그런데 **침투가 100 %** 다.

> 판정표의 *"A 에서 실제 접촉 후에도 침투 -> 접촉 resolver 부재가 임무 결과를
> 왜곡"* 에 해당한다. **확정.**

#### B — 침투 0.000 을 성공으로 읽으면 안 된다

`SPENT_FAIL` 로 **스텝 25 에 끝나서** 침투 판정에 도달하지 못한 것이다
(A 는 36 까지 간다). 상태기계 비정합의 런타임 확인이지 방어 성공이 아니다.

#### C1 vs C2 — ★ **즉시 종료는 주 비정합이 아니다**

```
C1 (종료만 억제)          침투 0.941, 하드킬 0     <- 거의 안 바뀐다
C2 (+ 접촉 resolver)      침투 0.235, 무력화 0.706  <- 여기서 회복
```

종료를 막아도 폴백이 **작동하지 않는다.** 커밋 비트가 없으니 하드킬 경로가
발동하지 않고, 공격자는 limiter 를 통과해 그대로 침투한다.

> 판정표의 *"C1 은 실패, C2 에서 회복 -> **접촉 resolver 부재가 추가 병목**"*
> 에 해당한다. **확정.**

#### 정리

```
[확립]  boxed_in 은 실제 접촉을 잘 예측한다 (76.5 %) -- fidelity 문제 아님
[확립]  접촉해도 아무 일이 없어 100 % 침투한다 -- **접촉 resolver 부재**
[확립]  즉시 종료만 고치면 침투 0.941 -> 거의 안 바뀐다
[확립]  접촉 resolver 를 넣으면 무력화 0.706 · 침투 0.235
[주의]  C1/C2 는 **격리 prototype** 이다. 본선 계약이 아니다
[주의]  B 의 침투 0.000 은 조기 종료로 측정이 잘린 것
```

**따라서 계약 개정의 우선순위가 뒤집힌다** -- `NET_MISS -> FALLBACK` 보다
**접촉 event resolver 가 먼저**다. handoff 만 넣으면 폴백이 여전히 커밋 비트에
의존해 작동하지 않는다.

재현: `python -m shepherd.scripts.boxed_arm_audit --n 60`

### 4.6 (구) 남은 판정 실험

`boxed_in = True` 상태를 저장해 3 arm 으로 replay:

```
A  발사 안 함, limiter 현 제어 유지     <- ★ 제일 중요
B  즉시 발사
C  발사 안 함, 커밋/폴백 resolver 활성
```

기록: 이후 A2 궤적 · limiter 최소거리 · `kill_radius` 접촉 시각 · 무력화 여부 ·
limiter 소모 · 최종 라벨 · 침투 · `boxed_in` 지속 여부.

§4.3 으로 **A 의 결과는 이미 예측된다** -- 접촉해도 아무 일 없이 공격자가
지나가고 침투할 것이다. 그래도 실측으로 확인해야 `boxed_in` 을 어떻게
재라벨링할지 정할 수 있다.

**★ 규율: `boxed_in` 을 곧바로 성공으로 재라벨링하지 않는다.** surrogate 교차와
실제 무력화 사이를 **event resolver 가 연결한 뒤에만** 파괴적 성공으로 채점한다.

---

## 5. 알고리즘 한계와 물리 한계를 가르는 조건

목적함수를 바꾸면 "어디서 더 이상 안 좋아지는가" 가 보인다. 그러나 그것이
**물리 한계인지 알고리즘 한계인지** 가르려면 **같은 목적함수**에 대해

```
trajectory optimization / MPC oracle   <- 상한
strong scripted controller             <- 손설계 기준
learned policy                         <- 측정 대상
```

셋을 비교해야 한다. 오라클과 RL 이 붙으면 그 부근이 환경의 물리적 frontier 이고,
벌어지면 알고리즘 격차다. **이 비교 없이 "한계를 봤다" 고 쓰지 않는다.**

---

## 6. 지금 상태

```
[x] net miss 가 종료라는 것 — 코드 확인 (env.py:356)
[x] v_soft 가 확률이 아니라는 것 — 코드 확인 (_assemble + union 구성)
[x] docs/52 2b 결과의 재해석 — Pareto frontier 의 보수적 끝점
[x] ★ mode handoff 가 비준된 시스템 서술에 있는가 -> **있다** (docs/29:
      "2모드 + 1핸드오프", 폴백=하드킬은 τ_kill≪τ_deploy 의 귀결) (§4.1)
[x] -> 구현이 설계를 안 따름. 계약 변경의 정당화 근거 성립
[x] ★ `boxed_in` 채점 판정 -> **(b) 두 번째 비정합.** 접촉 event resolver 가
      아예 없다. 하드킬은 커밋 비트로만 발동 (§4.3)
[x] docs/52 perturbation 3 분류 표현 정정 (§4.4)
[x] boxed 3-arm replay 실측 (§4.5b) -- 예측대로 A 침투 1.000.
      ★ C1(종료억제) 0.941 / C2(접촉 resolver) 0.235 -> **resolver 가 먼저**
[ ] 계약 변경 사전등록 (§3.1~3.3) + **접촉 resolver** 를 범위에 포함
[ ] 어느 쪽이든 §5 의 3-way 비교 없이 "물리 한계" 라고 쓰지 않는다
```
