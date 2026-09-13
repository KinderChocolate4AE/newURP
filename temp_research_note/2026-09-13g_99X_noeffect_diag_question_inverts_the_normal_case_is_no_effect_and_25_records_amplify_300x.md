# 2026-09-13g — `99-X` 무효과 진단: **질문이 뒤집혔다.** 정상은 "무효과" 쪽이고, 나머지 25 판이 **300 배 증폭**한다

- **지위**: **exploratory post-hoc diagnostic. 새 claim gate 아님.** 사전등록 없음, 분기표
  없음. 목적은 하나 — docs/99 주력 셀(ρ=0.75)이 왜 퇴화했는지 설명. 여기 수치로
  `96-BR1` · `98-B` · `99-P` 판정을 바꾸지 않는다.
- **재실행 0** (rollout 없음; 상수 조회용 env 빌드만). 코드
  `shepherd/scripts/r2b_noeffect_diag.py` → `artifacts/r2b/noeffect_diag.json`.
- **자기검증**: branch limiter 의 coast 이중적분 모델이 저장된 `coast_disp` 와
  **max rel err 1.4e-14** 로 일치 — 지령 철회 후 limiter 궤적을 정확히 재구성할 수 있다는
  뜻이고, 그 위에서 Layer D 가 성립한다.

ρ=0.75, multi-dependent 46 판을 세 그룹으로: **LOST** 15 · **RET_effect** 10 ·
**RET_noeffect** 21 (‖Δp_A‖ < 1 mm).

---

## 1. 후보 설명 두 개가 **둘 다 기각**됐다

**(A) interaction 이 이미 끊겼다 — 기각.**

| | LOST | RET_effect | RET_noeffect |
|---|---|---|---|
| t_w 에서 최근접 limiter 거리 (med) | 8.46 m | 7.12 m | 8.93 m |
| **4/4 가 `sense_range`(30 m) 안** | **15/15** | **10/10** | **21/21** |

**전 판에서 네 대 모두 반응 반경 안**이다. 거리 5~11 m 로 30 m 근처도 아니다.
공간적 disengagement 가 아니다.

**(B) 남은 control authority 가 작다 — 기각.**

| | LOST | RET_noeffect |
|---|---|---|
| 남은 Δt | 0.150 s | 0.150 s |
| max \|a\|Δt | 1.135 m/s | 1.086 m/s |
| max ½\|a\|Δt² | **0.0888 m** | **0.0846 m** |
| t_F 에서 limiter 위치 차 | **0.1184 m** | **0.1128 m** |
| **표적 ‖Δp_A‖** | **0.0418 m** | **0.00011 m** |

**개입의 크기가 사실상 같다** (limiter 가 원래 있었을 자리에서 ~11 cm 벗어남). 그런데
표적 반응만 **400 배** 다르다. 남은 권한으로 설명되지 않는다.

## 2. [Layer D] 첫 인과 차이를 직접 쟀다 — **세 그룹이 동일하다**

스텝 $t_w$ 의 지령만 다르므로 $t_w\!+\!1$ 에서 **표적 상태는 아직 정확히 같고 limiter
위치만 갈린다.** 그 지점에서 A2 의 회피 지령(`_route_accel` 그대로 호출)을 양쪽 배치로
평가하면 **최초의 인과 차이**가 나온다:

| | LOST | RET_effect | RET_noeffect |
|---|---|---|---|
| $t_w\!+\!1$ limiter 이동차 | 0.0176 m | 0.0176 m | 0.0168 m |
| A2 회피지령 차 \|Δa\| | 0.0104 m/s² | 0.0082 m/s² | 0.0065 m/s² |
| 지령 각도차 | 0.0010 rad | 0.0009 rad | 0.0007 rad |

**세 그룹에 똑같은 크기의 섭동이 전달된다.** 입력은 같다.

## 3. [Layer E] 그래서 갈리는 것은 **증폭**이다

첫 지령 차이의 선형 예측 $\tfrac12\lvert\Delta a\rvert\,\Delta t^2$ 과 실제 표적 변위 비교:

| 그룹 | 선형 예측 | 실제 ‖Δp_A‖ | **증폭** |
|---|---|---|---|
| **RET_noeffect** (21) | 0.000100 m | 0.000109 m | **1.0×** (min 0.0, max 10) |
| **LOST** (15) | 0.000117 m | 0.041759 m | **327.6×** (49.8 ~ 1410) |
| **RET_effect** (10) | 0.000329 m | 0.066717 m | **269.5×** |

> ### 질문이 뒤집힌다
>
> **`RET_noeffect` 는 이상한 쪽이 아니라 정상인 쪽이다.** 증폭 **1.0×** — 작은 섭동에
> 대한 교과서적 선형 응답이다. "아무 일도 안 일어났다" 가 아니라 **일어날 만큼만 일어났다.**
>
> 설명이 필요한 것은 나머지 **25 판**이다. 3 틱 만에 **270~330 배**는 매끄러운 동역학에서
> 나올 수 없다. **그 사이에 이산 전환(discrete switch)이 일어난다.**

(RET_effect 의 max 8.5e9 는 분모가 0 에 붙은 1 판의 산물이다 — median 만 읽는다.)

## 4. ⚠ 직전 진술 정정

`2026-09-13f` 에서 제가 *"limiter 의 영향 창이 FIRE 전에 이미 닫힌다"* 고 썼는데
**틀렸다.** 창은 닫히지 않는다 — §2 대로 섭동은 세 그룹 모두에 **동일하게 전달**된다.
갈리는 것은 **그 섭동이 증폭되는가**다. 해당 노트에 정정을 넣었다.

## 5. 어떤 전환인지는 **아직 모른다** (다음 카드)

$t_w\!+\!1$ 에서는 회피지령 각도차가 0.001 rad 로 **전환이 아직 안 일어났다**. 따라서
전환은 **그 이후 틱**에서, 작은 차이가 어떤 이산 술어의 경계를 넘기면서 일어난다. 후보:

| 후보 | 성격 |
|---|---|
| **angular-gap argmax 뒤집힘** | `_route_accel` 은 **가장 넓은 free arc** 를 고른다 — argmax 는 이산. r_block = 1.0·1.0·0.75 = **0.75 m**, 거리 ~8.5 m → 차단각 α ≈ 5°. 두 gap 이 비등하면 limiter 가 11 cm 움직여 argmax 가 바뀔 수 있다 |
| `ahead` 집합 변동 | limiter 가 전방 평면 $(c-p)\!\cdot\!\hat v>0$ 을 넘나들면 blockage 목록에서 빠진다 |
| `committed` 토글 | 커밋되면 jink 가 꺼진다 (`_jink_accel`) |
| `jink_terminal_r` (3 m) 통과 | 목표 3 m 안에서 회피 정지 |

가장 유력한 것은 **argmax 뒤집힘**이다 — 유일하게 "작은 입력 → 큰 출력" 을 자연스럽게
만드는 구조다. 확인법: $t_w$ 이후 매 틱에서 ref/branch 각각의 free-arc 선택을 비교해
**언제 갈라지는지** 찾는다 (재실행 필요 — branch 궤적 재생).

## 6. 이게 왜 중요한가 (해석은 조심해서)

사실이라면 이 세계의 협력은 **"표적을 밀어내는 것"이 아니라 "표적의 이산 선택을
뒤집는 것"** 이 된다. 그러면 `98-B`(평행이동으로 설명 안 됨) 과 `99-P`(속력이 갈림) 가
자연스럽게 이어진다 — 회피 방향 선택이 바뀌면 속도 벡터가 통째로 바뀌니까.

**다만 지금 단정하지 않는다.** §5 의 후보 중 무엇인지 아직 측정하지 않았다.
지금 말할 수 있는 것은 여기까지다:

> **The same limiter perturbation is delivered to the attacker in all three groups; what
> differs is whether it is amplified. In 21 records the attacker's response is the linear
> one (1.0x); in 25 it is amplified by a factor of a few hundred within three ticks,
> which smooth dynamics cannot produce.**

## 7. 부수 소득

- **docs/99 주력 셀 퇴화의 원인이 밝혀졌다**: 그 셀의 RETAINED 층은 "증폭이 안 일어난
  판" 들의 모임이라 모든 성분이 선형 응답 크기(~0.1 mm)에 몰려 있었다. 분모가 0 에 붙은
  이유가 이것이다.
- coast 재구성이 1.4e-14 로 맞는다는 것은 향후 **branch limiter 궤적을 재실행 없이
  재구성**해도 된다는 뜻이다 (§5 확인 작업의 절반이 공짜).
