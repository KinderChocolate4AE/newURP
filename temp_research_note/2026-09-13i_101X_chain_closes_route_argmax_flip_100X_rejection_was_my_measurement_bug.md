> # ⚠ 이 노트는 `2026-09-13h` (`100-X`) 의 중심 결론을 **뒤집는다**
> `100-X` 가 "free-arc argmax separatrix 가설 기각" 이라고 쓴 것은 **제 측정 버그**였다.
> 가설은 **맞았다**. 아래 §2 에 원인, §1 에 올바른 측정.

# 2026-09-13i — `101-X`: 사슬이 닫혔다. **route argmax flip** 이 증폭원이고, `committed`/jink 는 아니다

- **지위**: exploratory post-hoc mechanistic diagnostic. 코드
  `shepherd/scripts/r2b_commit_jink_audit.py` → `artifacts/r2b/commit_jink_audit.json`.
- **계측**: `_general_action` 의 기존 `diag` 훅 (`a_raw`·`clipped`·`a_final`·`committed`·
  `route_req`). 새 계측기 없음. diag 는 순수 write 라 거동 불변.
- **정렬**: **FIRE 기준** (창 길이가 2~5 틱으로 제각각 — `100-X`/13h 는 `t_w` 기준이라
  서로 다른 국면을 섞었다. 그것도 정정 대상이다).
- 그룹 `99-X` 동결 승계. 46/46 ok.

---

## 1. 결과 — LOST 는 fire−1 에서 **전원 route 방향이 107° 뒤집힌다**

| 그룹 | fire off | `d_a_final` | `d_a_route` | **residual** | **route 각도** | **flip>0.5rad** | commit 불일치 |
|---|---|---|---|---|---|---|---|
| RET_noeffect | −1 | 0.0231 | 0.0261 | 0.0026 | **0.0026 rad** | **0/21** | 0 |
| RET_noeffect | +0 | 0.0157 | 0.0513 | 0.0412 | 0.0058 rad | 0/21 | 0 |
| **LOST** | **−1** | **16.135** | **16.986** | **0.0024** | **1.8695 rad (107°)** | **15/15** | **0** |
| LOST | +0 | 0.370 | 0.119 | 1.463 | 0.0129 rad | 4/15 | 0 |

두 가지가 동시에 성립한다:

1. **가속 차이가 통째로 route 항이다** — fire−1 에서 `d_a_final` 16.14 ≈ `d_a_route` 16.99,
   **residual 0.0024** (jink·dodge·homing·전진 항의 기여가 사실상 0).
2. **`committed` 는 갈리지 않는다** — LOST 15/15 에서 branch 의 FIRE 가 **같은 틱**이고
   commit 불일치 **0**. clip 불일치는 2/15 (부차적).

⇒ **`101-X` 가 던진 질문 ("committed 전환과 jink 불연속으로 설명되는가") 의 답은 NO** 이고,
같은 계측이 진짜 원인을 집어냈다.

### 산술이 정확히 닫힌다

$$ 16.135\ \text{m/s}^2 \times 0.05\ \text{s} = 0.807\ \text{m/s}
   \qquad(\text{관측 } \Delta v = 0.835) $$

$$ 0.807 \times 0.05 = 40.3\ \text{mm}
   \qquad(\text{관측 } \Delta p = 41.8\ \text{mm}) $$

`99-X` 가 "300 배 증폭" 이라 부른 것의 정체가 이것이다 — 증폭이 아니라 **한 틱의 거대한
지령 불연속**이고, 그 크기가 정확히 관측된 속도·위치 차이를 만든다.

## 2. ⚠ `100-X` 가 왜 틀렸나 — 제 측정 버그

`100-X` 는 `_route_accel` **원본 함수를 호출**했지만 **인자를 잘못 넣었다**:

```python
# _general_action (env 가 실제로 도는 경로)
fwd = _unit(target - p_att, v_att)     # ← 표적 방향

# 100-X 에서 내가 넣은 것
fwd = _unit(v_att)                     # ← 속도 방향
```

`fwd` 가 다르면 기저 (û, ŵ) 가 달라지고 → blockage span → free arc → 선택 arc 가 전부
달라진다. **원본 함수를 부르고도 다른 함수를 측정한 것**이다. 그래서 `100-X` 는 LOST 의
fire−1 route 차이를 **0.031** 로 쟀고 (실제 **16.99**), argmax flip 을 못 봤다.

**자기검증이 왜 못 잡았나**: `100-X` 의 자기검증은 "재구현 gap 이 `_route_accel` 출력
방향과 일치하는가" 였는데, `_gaps` 와 `_route` **양쪽 다 같은 잘못된 `fwd`** 를 썼다.
**내 코드를 내 코드와 비교**한 것이라 구조적으로 통과할 수밖에 없었다.

> **교훈 (규율로 승격할 것)**: 자기검증은 **authoritative 산출물**과 대조해야 한다.
> 이번에 통한 방법은 `diag["route_req"]` 처럼 **env 가 실제로 쓴 값을 받아 쓰는 것**이다.
> "원본 함수를 호출했다" 는 것만으로는 부족하다 — **인자도 원본 경로의 것**이어야 한다.

`100-X` 판독문(13h)에 이 정정을 머리말로 달았다. 13h 의 다른 관찰 —
$\varepsilon_\theta$ 가 중앙값에 앉았다는 고지, $\delta_g$ 방향 — 은 **같은 잘못된 `fwd`
위에서 계산된 것이므로 함께 무효**다.

## 3. 그래서 지금 서 있는 메커니즘 사슬

$$ \text{limiter 지령 철회}\ \rightarrow\ \text{limiter 위치 } \sim\!11\,\text{cm 변화}
   \ \rightarrow\ \textbf{A2 free-arc argmax flip (107°)} $$
$$ \rightarrow\ \Delta a_{final} \approx 16\ \text{m/s}^2 \ (\text{1 tick})
   \ \rightarrow\ \Delta v \approx 0.84\ \text{m/s}
   \ \rightarrow\ \Delta p \approx 42\ \text{mm at } t_F^C $$
$$ \rightarrow\ \text{capture 술어 상실} $$

이는 앞선 결과들과 **전부 정합적**이다:

- `98-B` **평행이동으로 설명 안 됨** — 맞다. 원인은 회피 *방향 선택*의 전환이고 위치는 결과다.
- `99-P` **속력이 층을 가름** — 맞다. 107° 방향 전환이 속도 벡터를 통째로 바꾼다.
- `99-X` **입력 섭동은 세 그룹 동일** — 맞다. 갈리는 것은 **그 섭동이 argmax 를 넘기느냐**다.

## 4. 확정 / 미확정

**확정 (본 노트)**

- LOST 15/15 에서 fire−1 에 **route 방향 107° 전환**, 가속차 16 m/s², **residual ≈ 0**.
- `committed`/jink 가설 **기각** (commit 불일치 0/15, FIRE 시점 15/15 동일).
- 산술이 닫힌다 (지령차 → Δv → Δp 가 관측과 일치).

**미확정 / 주의**

- `RET_effect` 10 판은 양상이 다르다 (fire−3 에 flip 4/10, fire−1 residual 2.79) — **단일
  설명으로 묶지 않는다.** 별도 관찰 필요.
- **왜 그 판들이 argmax 경계 근처에 있었는가** 는 여전히 미답. `100-X` 의 $\delta_g$
  측정은 무효라 다시 재야 한다 (**올바른 `fwd` 로**).
- 이것은 **sealed scripted A2 의 argmax 불연속**에서 나온 메커니즘이다. "민첩한 회피자
  일반" 으로 일반화하지 않는다 (docs/100 §5 금지 조항 유지). learned/PFSP 에서 같은
  **behavioral decision-boundary exploitation** 이 나타나는지가 일반성의 시험대다.
- 어휘는 여전히 **잠정**: *cooperative mode-switch steering* /
  *trajectory steering through discrete evader route-choice transitions*.

## 5. 방법론

오늘 같은 계열의 오류가 **세 번** 났다: docs/98 (비교 대상을 규칙 밖에 둠) · docs/99
(분모 퇴화 가드 없음) · `100-X` (**자기 코드와 자기 코드를 비교**). 공통점은
**대조 기준을 authoritative 한 것으로 잡지 않았다**는 것이다.

다음 사전등록부터 규칙 본문에 박는다: **모든 자기검증은 "내가 계산한 값" 이 아니라
"시뮬레이터가 실제로 쓴 값" 과 대조한다.**
