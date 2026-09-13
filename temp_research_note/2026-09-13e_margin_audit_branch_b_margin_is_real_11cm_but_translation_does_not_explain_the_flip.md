# 2026-09-13e — capture-margin audit: **BRANCH B**. 여유는 실재(중앙값 11 cm)하고 표본 인공물이 아니며, **평행이동만으로는 술어 뒤집힘이 설명되지 않는다**

- **입력**: geom_probe 봉인 plan 140 판의 reference FIRE state. **140/140 ok, 제외 0.**
- **코드**: `shepherd/scripts/r2b_margin_audit.py` → `artifacts/r2b/margin_audit.json`.
  규칙은 docs/98 에서 **실행 전 봉인** (`be5c0cc`).
- **자기검증 통과**: 전 witness 에서 `sign(s_j) ≥ 0 ⟺ union.caught[j]` — margin 정의가
  judge 와 갈라지지 않았다는 증거 (predicate 재구현 아님). **음수 m_cap 0 건** (성공 판은
  반드시 내부여야 하므로 이것도 자기검증).

---

## 1. 측정값 (primary = multi-dependent 46)

| | |
|---|---|
| $m_{cap}$ | **median 11.2 cm** · min 0.81 · p5 2.5 · p95 23.5 · max 27.6 cm |
| < 1 cm / < 10 cm | 2% / 39% |
| binding 제약 | **lateral 44/46** (원뿔 반각), axial 2 |
| binding witness 가 결정론적 extreme 방향 | 30/46 (65%) |
| 참고 척도 | `net_radius` 1.77 m · `kill_radius` 0.75 m · 원뿔 반각 med 0.212 rad |

**즉 "경계에 딱 얹혀 있다" 는 아니다.** 여유가 0 근처에 몰려 있지 않다. 철회한 문장이
틀렸다는 것이 수치로 확인됐다.

## 2. 분기 C 기각 — 여유는 **표본 인공물이 아니다**

docs/98 §5 가 분기 B 에 의무화한 witness 증량 재확인 (n ×4, n_dir ×2, 46 판):

| | base | boosted |
|---|---|---|
| $m_{cap}$ median | 11.22 cm | **11.26 cm** (ratio med 0.982) |
| min | 0.81 cm | 0.79 cm |
| 10% 이상 줄어든 판 | — | 10/46 |

표본 min 은 참값을 **과대평가**하므로 witness 를 늘리면 줄어야 하는데 **1.8% 밖에 안
줄었다.** ⇒ CEM 이 judge 의 유한 witness 가장자리를 exploit 한 것이 아니다. **분기 C 기각.**

## 3. ⚠ 봉인 규칙의 **라벨은 맞고 근거는 틀렸다** (정직하게 기록)

봉인 규칙은 `frac(<10cm) = 39%` 가 과반 미달이므로 **BRANCH_B** 를 냈다. 그런데 규칙에
같이 적어둔 근거 문장 — *"Margins are comfortable, so the effect does not run through
position alone"* — 은 **실제 수치가 반박한다**:

$$ m_{cap} \approx 11.2\ \text{cm} \qquad\text{vs}\qquad \lVert\Delta p_A\rVert \approx 9.6\ \text{cm} $$

**여유와 개입 변위가 같은 크기다.** 여유는 "넉넉" 하지 않다. 즉 제가 사전등록에서
**크기 판정(<10cm 과반)에 메커니즘 결론을 직접 묶은 것이 설계 오류**였다 — 비교 대상인
$\Delta p$ 를 규칙 안에 넣지 않았다. docs/98 은 봉인 문서이므로 **고치지 않고** 여기 기록한다.

## 4. [POST-HOC] 올바른 논거 — 같은 판에서 $\Delta p$ 와 $m_{cap}$ 을 직접 비교

**사전등록에 없던 분석이다. 관찰로만 보고한다.**

| ρ | n | $\Delta p / m_{cap}$ med | $\Delta p > m_{cap}$ | 그중 auth 상실 | **$\Delta p \le m_{cap}$ 인데 auth 상실** |
|---|---|---|---|---|---|
| 0.25 | 45 | **0.99** | 47% | 100% | **96%** |
| 0.50 | 46 | 0.85 | 39% | 94% | **75%** |
| 0.75 | 46 | 0.01 | 11% | 40% | 32% |

핵심은 마지막 열이다: **표적 질량중심이 여유보다 *덜* 움직였는데도 술어가 96% 뒤집혔다.**
도달집합이 통째로 평행이동한 것이라면 $\Delta p < m_{cap}$ 일 때 술어는 유지돼야 한다.
유지되지 않았다.

⇒ **평행이동만으로 설명되지 않는다.** 속도·heading 변화가 **도달집합의 모양 자체**를 바꿔
원뿔 밖으로 witness 를 밀어낸다. 이것이 분기 B 가 원래 말하려던 것이며, 봉인 규칙이
쓴 근거보다 **이 비교가 훨씬 강한 논거**다.

## 5. 그래서 지금 확정된 것 / 아닌 것

**확정**

- 이른 limiter 지령 철회가 결과를 파괴한다 (steer probe, BRANCH 1 — 여유와 무관하게
  개입 대비 결과로만 서 있다).
- 의존은 **궤적 매개**다 (near-FIRE 순간 기여 0 + 이른 철회가 파괴).
- 성공 FIRE state 의 포획 여유는 **실재하고 (~11 cm) 표본 인공물이 아니다**.
- 그 뒤집힘은 **표적 위치 평행이동만으로 설명되지 않는다** (§4, post-hoc).

**확정 아님**

- "경계에 얹는다 / precision threading" — **기각됨** (§1).
- 속도·heading 중 **무엇이** 도달집합을 얼마나 바꾸는지 — 미측정. $\Delta v$ ·
  $\Delta\hat v$ 는 이미 steer probe 에 저장돼 있으므로 **재실행 없이** 분해 가능.
- 왜 하필 여유가 ~11 cm 인가 (CEM 이 최적화를 멈춘 지점인지, 세계의 성질인지).

## 6. 어휘 (확정)

- ✅ **"trajectory-mediated cooperative state steering"** — 채택 가능.
- ❌ **"precision capture-state threading"** · "경계에 얹는다" — **기각** (여유 11 cm).
- ❌ "the capture margin was 9.6 cm" — 9.6 cm 는 변위, 여유는 11.2 cm. 둘을 섞지 않는다.
- 새로 허용: **"the withdrawal-induced state change is commensurate with the available
  capture margin, and is not accounted for by translation of the attacker alone."**

## 7. training contract 함의 (유지·강화)

메커니즘이 **도달집합의 모양 변화**라면, 현재 순간에서 limiter 기하만 치환하는
instantaneous counterfactual (`delta_headline`, `coma_D`) 은 더더욱 이것을 볼 수 없다 —
그 반사실은 표적 상태를 **고정**하기 때문이다. 의심의 핵심은 계수 크기가 아니라
**credit assignment 의 causal horizon** 이다. W6 전 봉인에서 계수 조정으로 해결하지 않는다.

## 8. 다음 카드 후보

1. **$\Delta v$ / $\Delta\hat v$ 분해** — 재실행 0, steer probe 저장분만으로 "무엇이
   도달집합을 바꿨는가" 를 정량화. 가장 싸고 가장 직접적.
2. reward potential $\Phi(x_t)$ 후보 설계 — 단 1 이후.
3. docs/97 결재 · repo-R2/R3.
