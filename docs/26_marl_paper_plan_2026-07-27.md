# MARL 논문 기획 — 핸드오프 정합 + 위협 모델 재정의

**2026-07-27 · 자기완결 문서 · 이전 두 핸드오프(Claude판·GPT판)를 대체함**

> **1순위 원칙(이번 세션 확정)**: 모든 작업은 *"Q1 MARL 논문에 어떤 그림/표로 들어가는가"* 를 먼저 답한 뒤에만 착수한다.
> 답이 "평가 장치를 만든다"이면 그 작업은 논문 기여가 아니라 비용이다.
> **문헌·학회·투고 작업 금지 제약은 그대로 유효.** 이 문서의 외부 수치는 *플랫폼 하드웨어 사양*이며 문헌 조사가 아니다.

---

## 0. 핸드오프 정합 판정

### 0.1 두 핸드오프의 공통 결론과 그것이 왜 문제인가

두 문서는 서로 다른 정밀도로 **같은 결론**에 도달했다: (a) 다음 작업 = mission harness(B0), (b) 논문 프레이밍 = **B(프로토콜/평가 방법론 논문)** 권고.
GPT판이 기술적으로 더 정확하다. 그러나 **방향이 같고 비용만 크다.**

### 0.2 기각 사유 3건

**① 지휘 원칙 정면 위반.**
- 원칙 3항 = *"진단-프레이밍 격하 금지. 진단 연구는 실패 충분 누적 시의 fallback."* → 두 문서 모두 프레이밍 B를 **권고**로 승격. GPT §16은 *"주기여 = 평가 방법론 / 부기여 = controller"* 로 확정.
- 원칙 7항 = *"신규 축은 0-e급 대형 사전등록·문서 증식 금지, discovery-mode 우선."* → B0 수용조건 4개 + Tier A/B positive control + parity + B1 14항 봉인 + 통계 계획 = 정확히 금지된 형태.

**② 이미 리포에 적혀 있는 답을 "미지의 물리 리스크"로 취급.**

`shepherd/params.py` (2026-07-03):

```
"derived.R_reach": Param(2.4, "m", "DERIVED", "doc-only",
    "0.5 * a_att_max * tau_deploy^2 (free reachable ball radius)",
    "= 0.5*30*0.4^2; net_radius 2.0 < 2.4 -> baseline-net absolute capture
     honestly fails; L2 target = shaped reachable radius < 2.0 m"),
```

그리고 `docs/10_shaping_necessity_prop.md`(명제 N, AI 초안 2026-07-03, **Hyunjun 비준 전**)는 이를 정리로 만들어 두었다:

> **명제 N(a)**: 회피 여유 `w = ½·a_max·τ²` 가 네트 반경 `ρ` 를 넘는 한, **무-shaping 방어의 가치는 fire-gate 설정과 무관하게 0**이다. *"실패는 게이트가 아니라 구조(w > ρ)다."*

⇒ **`capture = 0`, `clean crossing = 0`은 발견될 사실이 아니라 파라미터의 귀결이고, 그 사실은 이미 정리로 적혀 있다.** 현행값 `w = 2.40 > ρ = 2.00`. 같은 `params.py`가 경계까지 명시한다: `a_att ≤ 25` 또는 `τ ≤ 0.365 s`에서 포획 복귀. **현행 운용점은 경계 바로 바깥이다.**
이 상태를 봉인하고 재면 산출물은 *"엄밀하게 측정된 0"* 이다. 두 핸드오프 다 이 두 파일을 읽지 않았다.

**③ MARL 논문의 필수 결과가 없다.** 두 문서 어디에도 *정책이 무엇을 학습했는가*(역할 분화, 도달집합 압축 기전, 게이트 타이밍) 분석이 없다. 종속변수를 margin→capture로 바꿔도 이게 없으면 "MARL을 도구로 쓴 평가 논문"으로 읽힌다.

### 0.3 GPT판에서 채택하는 항목

| 항목 | 채택 형태 |
|---|---|
| Tier A(flag 배선) vs Tier B(dynamic end-to-end) 분리 | 채택 — 단 경량 스모크 테스트로. 봉인 절차 아님 |
| `spent_fail`을 자동 임무실패로 해석 금지 | 채택 — `K=1` 소진 후 공격자 거취는 별도 관측 |
| 동시 flag / 종료 우선순위 검사 | 채택 — `env.py` L323–351 순서 그대로 기록 |
| held-out에서 기존 8개 fixed defender trajectory 재사용 금지 | **채택(중요)** — MARL에서 defender 궤적은 정책 출력 |
| C-1 산출물과 신규 작업의 git 경계 | 채택 — 블록 종료 시 별도 커밋 스크립트 |
| `rollout_unified` 보존, 역할 분리 | 채택 |

### 0.4 기각 항목

| 항목 | 사유 |
|---|---|
| 프레이밍 B를 스파인으로 | 원칙 3항 위반. **R5(강건성 섹션)로 강등** |
| 첫 숫자 전 B1 14항 봉인 + 통계계획 확정 | 원칙 7항 위반. 봉인은 **확증 실행 시점**에 |
| `RI-SHARED` / `RI-GMAX`를 임무 baseline으로 | 종료된 certificate 캠페인의 sunk cost. **"과거 scripted 시도" 참조로만** |
| "B3까지가 방향 결정선" | 역전 — 방향은 **기하적 가능성**이 정하고 측정은 그 뒤 |
| 동결 불변량 유지 | **Hyunjun 기각(2026-07-27)**: *"그건 불변이라고 보기 어려워"* |

---

## 1. 이론 → 현실: 오늘 확정된 것

### 1.1 기존 이론 (docs/10 명제 N, 비준 전)

`w = ½·a_att·τ²`, `ρ = r_net`, `r = r_kill` 일 때 1D 인스턴스에서:

- **(a) 필요성** — `w > ρ` 이면 무-shaping 가치 = 0. 게이트를 어떻게 놓아도 마찬가지.
- **(b) 충분성** — `r ≥ (w − ρ)/2` 이면 **limiter 2기**로 escape lobe를 마스킹해 clean crossing과 확실 포획을 **강제**할 수 있다.
- 무-shaping plateau `v_soft = ρ/w`; M2 상수에서 `5/6 ≈ 0.833`, `θ_fire = 0.9` 는 shaping-forcing 창 `(ρ/w, 1]` 안.
- 명시적 캐비앗: *"존재 ≠ 컨트롤러 — 동역학·역할분담 하에서 escort를 **찾는** 것이 MARL(L2)의 몫."*

### 1.2 실 플랫폼을 대입하면 (오늘의 새 사실)

`τ = 0.4 s`, `ρ = 2.00 m`(Xu et al. *Drones* 9:190 S_NP = 12.54 m²에서 유도 — **유일하게 실측 기반인 값**), `r_kill = 2.0 m`:

| 공격자 등급 | a_att [m/s²] | w [m] | w/ρ | plateau ρ/w | 명제 N(b) 요구 r | **r_kill=2.0 충족?** |
|---|---:|---:|---:|---:|---:|:---:|
| 포획 경계 | 25 | 2.00 | 1.00 | 1.000 | 0.00 | OK |
| **현행 fixture** | **30** | **2.40** | **1.20** | 0.833 | 0.20 | OK |
| 무장 FPV (TWR 4) | 38 | 3.04 | 1.52 | 0.658 | 0.52 | OK |
| 무장 FPV (TWR 5) | 48 | 3.84 | 1.92 | 0.521 | 0.92 | OK |
| **구성 붕괴 경계** | **75** | **6.00** | **3.00** | 0.333 | **2.00** | 경계 |
| 5" 프리스타일 (TWR 8) | 78 | 6.24 | 3.12 | 0.321 | 2.12 | **FAIL** |
| 레이싱 (TWR 10) | 98 | 7.84 | 3.92 | 0.255 | 2.92 | **FAIL** |
| 레이싱 (TWR 14) | 137 | 10.96 | 5.48 | 0.182 | 4.48 | **FAIL** |

**세 가지 판독.**

1. **현행 fixture(30 m/s²)는 현실 위협 스펙트럼의 최하단**이다. 그런데 거기서조차 이미 `w/ρ = 1.20` 으로 필요성 조건(a)이 발화한다.
2. **명제 N(b)의 충분성 구성 자체가 `a_att > 75 m/s²` 에서 붕괴한다** (`w ≤ 2·r_kill + ρ = 6.0 m` 이 조건). 즉 *"2기면 충분"* 은 toy regime에서만 참이다. 실 프리스타일/레이싱급에서는 2기로 lobe를 덮을 수 없다.
3. **하드웨어로는 못 메운다.** TWR 8급 상대로 네트만으로 풀려면 직경 12.5 m 네트(Xu의 5.2 m 네트의 2.4배)이거나 0.226 s 전개가 필요하다. 둘 다 실물 범위 밖이다. plateau가 0.833 → 0.18로 무너지므로 shaping이 감당해야 할 일의 양이 4배 이상 늘어난다.

> ⇒ **열린 양은 정확히 하나다: 3D·실 regime에서 몇 기가 필요한가 = N\*.**
> 1D 명제는 `N* = 2` 를 toy regime에서만 준다. 실 regime의 `N*(a_att, 기하, 공격자 등급)` 은 닫힌 형태가 없다.
> 그리고 그 배치를 *반응하는* 공격자 상대로 실시간에 찾는 것이 MARL 문제다 — 명제 N이 스스로 MARL의 몫이라 지목한 지점.

### 1.3 이 논증이 캠페인 이력을 살리는 방식

`clean crossing = 0` · `held-out 132/280 falsified` · `RI-SHARED 일반화 실패` — 전부 **"단일 사격 기하는 부족하다"(명제 N(a))의 실험적 확인**으로 재해석된다. 폐기가 아니라 이론의 검증이다.

---

## 2. 논문 결과 골격 (헤드라인: 포획 가능영역 확장)

| | 결과 | 종속변수 | 상태 |
|---|---|---|---|
| **R0** | 필요성 — 명제 N + 실 플랫폼 브래킷 오버레이, N(b) 붕괴 경계 | 해석 + 시뮬 확인 | §1 완료, 그림화 + Hyunjun 비준 필요 |
| **R1** | **가능영역 지도** — (a_att × τ_deploy × N_lim × 공격자 등급) 위 escape / containment / capture 3분할 | 임무 결과 4분할 | 미실행 ← **이번 블록** |
| **R2** | **헤드라인** — **N\*(a_att): 동일 포획률을 만드는 최소 limiter 수**. static ring vs **learned** vs oracle 하한 | **N\*** | R1 후 |
| **R3** | **기전** — 역할 분화 · 도달집합 압축 시계열 · 게이트 타이밍 분포 · 궤적 오버레이 | 정성+정량 | rollout 재분석 |
| **R4** | **credit assignment** — COMA vs MAPPO vs IPPO, mix {0, 0.5, 1.0} | N\* 및 임무 결과 | 체크포인트 보유 |
| **R5** | **강건성** — 공격자 사다리 A1→A4 · held-out 88조건 · falsifier를 정책에 | 위와 동일 | C-1 자산 재사용 |

### 왜 N\*가 헤드라인 종속변수인가

- **"드론 한 대를 막을 때 최대효용"이 곧 N\***(Hyunjun 2026-07-27 지시).
- **명제 N(b)의 유일한 일반화 경로다.** 1D·toy에서 2, 실 regime에서 미지 — 논문이 채우는 빈칸이 명확하다.
- **capture rate보다 강건하다.** 어떤 운용점에서 capture rate가 0이어도 N\*는 sweep 위에서 정의되므로 결과가 비지 않는다. 두 핸드오프가 두려워한 "전 arm capture=0" 시나리오가 구조적으로 사라진다.
- **정규화된다.** `N*_oracle ≤ N*_learned ≤ N*_static` 3중 부등식으로 학습의 가치가 상한·하한 사이 위치로 표현된다.
- **경제학 축과 직결**(메모의 exchange-frontier). 단 이번 논문은 *물리적 소요 수량*까지만, 비용·교환비 주장은 S9 유보(S6 2층 준수).

**MARL의 주장**: 학습된 팀은 압축을 *공격자가 갈 곳*에 배치하므로 정적 링보다 **적은 수**로 같은 포획률을 만든다.
`N*_learned < N*_static` → 양성 / `≈ N*_static` → 음성이지만 결과(정적 기하가 이미 최적) / `≈ N*_oracle` → 강한 양성.

---

## 3. 파라미터 지위 재분류 — 무엇이 임의값인가

`params.py`의 STATUS 필드가 이미 정직하게 분류해 두었다. **`ASSUMED`/`TUNED`는 동결 대상이 아니라 sweep 축이다.**

| 파라미터 | 현행값 | 지위 | 판정 |
|---|---:|---|---|
| `physics.a_att_max` | 30 m/s² | **ASSUMED** — 파일이 스스로 *"3 g / 0.4 s가 운용 FPV regime인지는 open question"* 이라 명시 | **sweep 축 ①** |
| `physics.att_speed` | 20 m/s | ASSUMED "fixture" | **sweep 축 ②** — DJI FPV 최고속도의 약 절반 |
| `scenario.n_limiters` | 4 | ASSUMED, 주석: *"Fig-7-style N ablation is future work"* | **sweep 축 ③ = N\*** |
| `physics.tau_deploy` | 0.4 s | ASSUMED "prototype fixture" | **sweep 축 ④** |
| `physics.a_lim_max` | 30 m/s² | ASSUMED "= attacker authority" | **sweep 축 ⑤ — 방어자 기동 우위 0인 설정** |
| `physics.kill_radius` | 2.0 m | ASSUMED "no external grounding" | **sweep 축 ⑥ — 명제 N(b) 붕괴 경계를 직접 움직임** |
| `physics.net_radius` | 2.00 m | **DERIVED / 실측 기반** (Xu S_NP) | **유지** — 유일한 외부 앵커 |
| `viability.cone.half_angle` | 0.067 rad | DERIVED from net_radius | 유지(net_radius 종속) |
| `train.limits.limiter_v_max` | **80 m/s** | ASSUMED | **비물리 — 288 km/h. 가속은 쿼드급, 속도는 미사일급. 불일치 시정 필요** |
| `train.limits.adversary_v_max` | 30 m/s | ASSUMED | 실 플랫폼과 정합(DJI FPV 38.9) |
| `viability.turn_limited` | **False** | **RESERVED — parsed-but-inert** | **미배선. §3 하단 참조** |
| `env.capture_thresh` | 0.95 | **DEAD** — 저장되지만 읽히지 않음 | 문서화만(env.py 동결) |
| `env_frozen.adversary_omega_att_max` | 8.0 rad/s | **DEAD** — 정책이 받지만 안 씀(실제는 backend 10.0) | 문서화만 |

**`viability.turn_limited = False` 의 의미**: 현재 도달집합은 **등방 가속 원뿔 근사**다. 실제 쿼드는 추력 벡터를 돌리려면 먼저 자세를 회전해야 하므로 0.4 s 창 안의 실 도달집합은 **더 작고 비등방**이다. 즉 현행 모델은 공격자에게 **관대**하고, `w = ½aτ²` 는 상한이다. 이 스위치를 켜는 것은 튜닝이 아니라 **모델 충실도 개선**이며, 명제 N(b) 붕괴 경계를 유리한 쪽으로 움직인다. 실 agility를 넣을 때 반드시 같이 켜야 공정하다.

---

## 4. 플랫폼 스펙 브래킷 (AI 추출 DRAFT — Hyunjun 검증 대기)

> 프로젝트 규율(WP-A3 rule 7: 수치 추출·동결 = Human-lane)에 따라 **DRAFT 표기**. 확정 전 인용 금지.

### 4.1 실측 앵커

| 항목 | 값 |
|---|---|
| DJI FPV 최고속도 (M 모드) | 140 km/h = **38.9 m/s** |
| DJI FPV 0→100 km/h | **2 s** → 평균 종가속 13.9 m/s² (≈1.42 g, 항력 포함) |
| DJI FPV 이륙중량 | 795 g |
| FPV 프리스타일 TWR | 8:1 – 10:1 |
| FPV 레이싱 TWR | 10:1 – 14:1+ |

### 4.2 유도 브래킷 — 기동(횡)가속 상한 `g·√(TWR² − 1)`

| 등급 | TWR | a_lat 상한 [m/s²] | 비고 |
|---|---:|---:|---|
| 무장 FPV (7–10", 탄두 탑재) | 3 – 5 | **28 – 48** | 페이로드가 TWR을 크게 낮춤. **주력 위협 등급** |
| DJI FPV급 (795 g, 비무장) | — | 실측 종가속 하한 13.9 | 카메라 드론, TWR 미공개 |
| 5" 프리스타일 | 8 – 10 | 78 – 98 | |
| 레이싱 | 10 – 14 | 98 – 137 | |

**⚠ 상한 vs 실사용**: 위는 *추력 한계*다. 0.4 s 창 안 실사용값은 자세 회전 시간 때문에 더 낮다 — 그 격차를 모델링하는 것이 `turn_limited` 스위치(§3)이며, **논문에서 도달집합 모델 충실도 주장을 지탱하는 지점**이다.

### 4.3 권고 시나리오 등급 (sweep 축 ①의 눈금)

```
LOW      a_att = 30    (현행 fixture 보존 = reference point)
MID      a_att = 48    (무장 FPV 상단, TWR 5)         <- 주력 위협
BREAK    a_att = 75    (명제 N(b) 2-limiter 구성 붕괴 경계)
HIGH     a_att = 78    (5" 프리스타일, TWR 8)
EXTREME  a_att = 137   (레이싱 상한, 스트레스)
```
속도 동반: 20 / 30 / 39 / 39 / 39 m/s.

---

## 5. 공격자 모델 사다리 — 논문 필수 구성요소

### 5.1 현행 공격자의 실제 상태 (`agents/adversary.py` 실사)

```python
amp = 1.8 if (committed and react_on_commit) else 0.0
```

> **커밋 전 lateral dodge 진폭 = 0.** 공격자는 finisher가 발사를 커밋할 때까지 **직진**한다(kill-radius 반발만 있음).

즉 지금까지 방어자는 **커밋 전에 회피하지 않는 공격자**를 상대로 평가되어 왔다. docstring도 인정한다: *"No loiter / bait / self-play / deception here (that richer adversary = S13, deferred)."*

**이론과의 불일치**: 명제 N의 가정 A3는 *"공격자는 commit을 관측하고 τ 동안 bang-bang ±a_max로 R 내 임의 endpoint를 실현한다"* 이다. A1 공격자는 A3를 부분적으로만 만족한다(커밋 후에만, 그것도 amp 1.8의 고정 방향 dodge). **즉 현행 실험은 이론이 상정한 공격자보다 약한 상대를 쓰고 있다.**

### 5.2 사다리

| 층 | 명칭 | 능력 | 지지하는 주장 | 상태 |
|---|---|---|---|---|
| **A0** | `OPEN_LOOP` | 직선/고정 S-curve, state 무시 | 없음 (straw man) | 폐기 |
| **A1** | `REACTIVE_COMMIT` | 전진 + **커밋 후에만** 회피 + kill-radius 반발 | 전개지연 탈출(S8 채널 i) | **현행** |
| **A2** | `CONTINUOUS_EVASION` | 커밋 전 지속 jink(위상 랜덤), limiter 배치 인지 우회 | **명제 N 가정 A3의 실제 행사** | 구현 필요 |
| **A3** | `COMMIT_BAITING` | marginal한 순간 발사를 유도 → 회피. `K=1`이면 유도 성공 = 침투 확정 | **지배 반격 전략에 대한 강건성** | 구현 필요 (S13) |
| **A4** | `BEST_RESPONSE` | 동결 방어자에 대해 학습/최적화된 공격자 | 적대적 상한 | falsifier core 재사용 |

### 5.3 논문 요구사항 (사전 확정)

```
헤드라인 결과(R2)는 A2 이상에서 성립해야 한다.
주 baseline은 A3 (bait 가능 공격자).
A4는 R5(강건성) 섹션.
A1 단독 보고 = 리젝 사유. 논문 본문에 A1-only 수치를 올리지 않는다.
```

**A3가 왜 결정적인가**: `K = 1`(단발)에서 **발사를 유도하고 회피하면 그 뒤는 무방비**다. 유일한 지배 전략이고, 현행 공격자는 실행할 수 없다. A3 없이 낸 수치는 "straw man을 이겼다"로 읽힌다. 동시에 A3는 `θ_fire = 0.9`(보수적 zero-waste 밴드)가 왜 그 값이어야 하는지를 실험적으로 정당화하는 실험이기도 하다 — 명제 N 따름정리 (iii)의 실증.

---

## 6. 이번 블록 — 가능영역 지도 + oracle 상한

**Hyunjun 승인 범위(Q3)**: 지도 + oracle 상한.

### 6.1 산출물

| 파일 | 내용 |
|---|---|
| `mission_rollout.py` | `env.step`/termination 직접 호출, 4분할 라벨(`CAPTURED`/`PENETRATED`/`SPENT_FAIL`/`TRUNCATED@80`), 동시 flag·우선순위 그대로 기록. **predicate 복제 금지, `rollout_unified` 무수정** |
| `mission_controls.py` | Tier A(flag 배선) + Tier B(dynamic 경로) 경량 스모크. 라벨 `CAPTURE_FLAG_WIRING_VALIDATED` / `END_TO_END_CAPTURE_PATH_VALIDATED` |
| `reach_boundary.py` | §1 경계의 시뮬 확인 — 해석 예측(명제 N) vs env 실측, `turn_limited` on/off 대조 |
| `nstar_sweep.py` | **N\*(a_att, 공격자 등급, 배치∈{static ring, oracle})** |
| `attacker_a2.py` | A2 지속 회피 공격자 (A3는 다음 블록) |

### 6.2 oracle 상한의 정의

```
ORACLE_PLACEMENT_UPPER_BOUND
  전지적 방어자: 공격자의 전 궤적을 사전에 알고
  limiter 배치와 발사 시점을 오프라인 최적화
  -> N*_oracle(a_att, 공격자 등급) = 포획을 만드는 최소 limiter 수
```

**의미**: `N*_oracle`이 유한하면 **그 운용점은 원리적으로 풀린다** — 이후 학습 실패는 알고리즘 문제이지 과제 불가능이 아니다. 발산하면 임무 설계를 바꿔야 한다. **G5(포획 존재 리스크)를 미지의 물리 리스크에서 계산된 경계로 바꾼다.**
1D 검산: `a = 30`에서 `N*_oracle = 2` 가 나와야 한다(명제 N(b) 구성). **이것이 oracle의 정합성 검사다.**

### 6.3 라벨링 규율 (claim governance 준수)

```
강도   = SEARCH_CANDIDATE      (INTERVAL_CERTIFIED 아님)
일반성 = FIXED_CONDITION        (DISTRIBUTION_LEVEL 아님)
모드   = DISCOVERY / NON-EVIDENTIAL
```
확증 실행 시점에만 봉인·사전등록(원칙 7항: 양성 시에만 confirmation). 새 해석은 **한 회차 provisional** 후 승격.

### 6.4 판정선

| 결과 | 다음 수 |
|---|---|
| 어떤 운용 밴드에서 `N*_oracle` 유한 & 배치 가능(≲10) | **R2 착수** — 그 밴드에서 학습 정책 평가 |
| `N*_oracle`이 전 밴드에서 발산 | **임무 재설계** — 교전거리 확대 / τ 단축 / 다중 finisher. 원칙 4항: *engineering feedback, MARL 실패 아님* |
| `N*_static` 이 이미 oracle에 근접 | 학습 여지 없음 → 압축 외 협력 축(타이밍·역할)으로 이동 |
| `a=30`에서 `N*_oracle ≠ 2` | **oracle 구현 결함** — 명제 N(b)와 불일치. 진행 정지 후 원인 규명 |

### 6.5 하지 않는 것

- B1 봉인 · 통계 계획 확정 (확증 시점으로 이월)
- `RI-SHARED` / `RI-GMAX` 임무 평가
- C-1 캠페인 재개 (`CLOSED — CERTIFICATE-LEVEL ONLY` 유지)
- 재학습 (기존 체크포인트 우선)

---

## 7. Hyunjun 결정 대기 항목

1. **docs/10 명제 N 비준** — §5 TODO 4항(A3 bang-bang 실현가능성, escort vs corridor 변형 채택, Lemma 1 서술 층위, (a′) 배치)이 미결. R0가 논문 §II가 되려면 필요.
2. **§4 플랫폼 수치 검증** — AI 추출 DRAFT. 특히 "무장 FPV TWR 3–5" 는 관행 추정이며 실측 앵커 없음.
3. **`limiter_v_max = 80 m/s` 시정 방향** — 물리 정합(쿼드급 ~40) vs 현행 유지(과거 결과 호환).

---

## 8. 이월 제약 (변경 없음)

```
1. 문헌·학회·투고 작업 금지. 연구 진척만.
2. 하드닝 파일 = device_commit_files(md5 검증). git add/commit/push는
   Hyunjun 네이티브 Windows git에서만. 2026URP 루트에서 `git add -A` 금지.
3. 봉인 파일(falsifier v2 · held-out 88조건 · V2C 프로토콜) 수정 금지.
   결과를 본 뒤 규칙을 바꾸는 소급 변경 금지.
4. 금지 용어: `v_soft_replan`을 verdict라 부르지 않음 ·
   `ADVERSARIAL_DYNAMIC_CERTIFIED` 금지 · "exact" 대신 `NUMERICALLY_RESOLVED_...`
5. proposal–verification separation: optimizer는 제안 생성기, objective 값은 증거 아님.
6. 보수적 sufficient test의 실패는 반대 명제의 증거가 아니다.
7. certificate-level 결과와 mission-level 결과를 항상 분리한다.
8. `spent_fail`을 자동 임무실패로 해석하지 않는다.
```

**동결 불변량 항목은 §3으로 대체됨** — `ASSUMED`/`TUNED` 파라미터는 사전 선언된 sweep 축, `net_radius`(DERIVED)만 유지.

---

## 9. 한 문장

> 이 프로젝트에는 이미 *"shaping이 없으면 방어 가치는 0이고 2기면 충분하다"* 는 1D 정리가 있다(docs/10, 비준 전).
> 실 FPV 스펙을 넣으면 **필요성은 더 강해지고 충분성 구성은 `a_att > 75 m/s²` 에서 붕괴한다.**
> 남는 열린 양은 **N\*** — 실 regime·3D에서 한 대를 막는 데 필요한 협력 기체 수 — 이고,
> MARL의 주장은 *학습된 팀이 정적 배치보다 적은 수로 같은 포획을 만든다* 는 검증 가능한 부등식이다.
