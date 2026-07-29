# 공격자 사다리 설계 (A0–A4) — 구현 전 기획

**2026-07-27 · `docs/26` §5의 구현 명세 · 코드 작성 전 확정 문서**

> **왜 공격자가 먼저인가**: 논문의 명제가 *"협력 학습의 가치는 상대의 적응성에 비례한다"* 이면,
> **공격자 난이도가 결과 그림의 x축**이다. 축이 없으면 그림도 없다.
> 부수적으로 리스크 1(`N*_static ≈ N*_oracle`, 학습 여지 없음)이 이 축 위에서 자동 검사된다.

---

## 1. 코드 실사 — 주입 경로 문제

### 1.1 발견

`shepherd/env.py` L334–339 (**FROZEN**):

```python
committed = self.fsm.state in (FinisherState.DEPLOYING, FinisherState.LOCKED)
adv = scripted_adversary_action(
    p_att, v_att, target=self.layout.target,
    net_center=self._net_center(p_att, v_att), finisher_p=p_fin,
    limiters=lim_pos, kill_radius=self.kill_radius, a_att_max=self.adv_a_max,
    omega_att_max=8.0, v_nominal=self.v_nominal, dt=self.dt, committed=committed,
    repel_margin=1.0)
```

**공격자가 하드코딩되어 있고 dispatch 파라미터가 없다.** `env_m3.py` L340–345도 같은 블록을 그대로 복사해 갖고 있다.

### 1.2 기각한 우회안

| 안 | 기각 사유 |
|---|---|
| `env.py` 수정 | 동결. freeze 예외는 현재 1건(2A batched eval)뿐이며 여기에 쓸 이유 없음 |
| 모듈 전역 상태로 레벨 설정 | 결정론·감사성 파괴. 에피소드별 주입 불가 |
| DEAD 파라미터(`omega_att_max=8.0`) 용도 변경 | 감사 불가능한 해킹. 이 프로젝트가 가장 경계하는 종류 |
| `shepherd.env.scripted_adversary_action` 몽키패치 | 테스트에서만 허용. 프로덕션 경로에 두면 재현성 추적 불가 |

### 1.3 채택 — `env_m3.py` 선례를 따른 서브클래스

`env_m3.py`가 이미 확립한 패턴이다: *"NON-frozen M3 lane. Subclasses the FROZEN ShapingParallelEnv (which stays byte-identical) and overrides step() ONLY to swap the reward geometry."*

```
shepherd/env_adv.py                    (NEW, non-frozen)
  class AdversaryLadderEnv(ShapingParallelEnv):
      """frozen M2 mechanics, 주입형 공격자."""
      def __init__(..., attacker: Callable): self.attacker = attacker
      def step(): frozen step()의 충실한 복사 + 한 줄 교체
                  adv = self.attacker(p_att, v_att, ..., committed=committed, ...)
```

**평가에는 보상이 필요 없다.** 임무 결과(4분할)만 재므로 M2 동결 mechanics를 그대로 상속하면 충분하고, M3 보상 위에서 *학습*시킬 때만 M3 조합을 따로 만든다.

**알려진 비용**: `step()` 복사본이 3개가 된다(env / env_m3 / env_adv). 리포의 기존 관행이고 드리프트 가드가 있다(`test_env_m3.py::test_m2_equivalence_when_unboxed`). 같은 가드를 더 강한 형태로 건다 — §5 P1.

---

## 2. 사다리 정의

### 2.1 설계 규약 — 단조성(nesting)

> **A_{k+1}은 파라미터 특수화만으로 A_k를 bit-exact 재현할 수 있어야 한다.**

이게 없으면 "붕괴 지점"에 순서가 없어서 x축이 성립하지 않는다. 구현으로 강제한다:

```
shepherd/agents/attacker_ladder.py      (NEW)
  A1 = scripted_adversary_action 을 그대로 위임하는 얇은 래퍼
       -> A1 bit-exactness는 "기본값을 잘 맞춰서"가 아니라 문자 그대로의 위임으로 보장
  A2 = A1 + (jink_amp, route_gain);  둘 다 0 이면 A1 경로로 폴백
  A3 = A2 + (bait_gain, bait_threshold);  0 이면 A2
```

**`agents/adversary.py`는 건드리지 않는다.** A1의 정의는 기존 파일이고, 변경하면 과거 전 결과가 무효가 된다.

### 2.2 각 층

| 층 | 이름 | 추가 능력 | 새 파라미터 | 무엇을 깨뜨리는가 |
|---|---|---|---|---|
| **A0** | `OPEN_LOOP` | — 직선/고정 S-curve, state 무시 | — | (폐기, 재구현 안 함) |
| **A1** | `REACTIVE_COMMIT` | 전진 P-drive · **커밋 후에만** 횡회피(amp 1.8) · kill-radius 경질 반발 | 현행 | 전개지연만 이용. 사전 배치는 못 깸 |
| **A2** | `CONTINUOUS_EVASION` | **① 커밋 전 지속 jink**(위상 시드) **② limiter 배치 인지 라우팅** — 반발이 아니라 링의 최대 간극으로 사전 편향 | `jink_amp`, `jink_freq`, `route_gain` | **정적 기하 배치**. 반응이 아니라 우회 |
| **A3** | `COMMIT_BAITING` | 포획 가능해 *보이는* 자세로 접근해 발사를 유도 → 커밋 확인 후 최대 회피 | `bait_gain`, `bait_threshold` | **K=1 자원 규율.** 유도 성공 = 침투 확정 |
| **A4** | `BEST_RESPONSE` | 동결 방어자에 대해 A3 파라미터/소형 정책을 선언된 예산 안에서 최적화 | (탐색) | 모든 고정 정책. **learned도 여기서 깨진다** |

### 2.3 A2 — 두 항의 근거

**① jink (커밋 전 지속 회피)**. A1은 `amp = 1.8 if committed else 0.0` — 커밋 전 진폭이 0이라 직진한다. 명제 N의 가정 A3는 *"공격자는 τ 동안 bang-bang ±a_max로 R 내 임의 endpoint를 실현한다"* 인데, **A1은 그 가정을 커밋 후에만 부분적으로 행사한다.** 즉 지금까지의 실험은 이론이 상정한 공격자보다 약한 상대를 썼다. jink는 이론과 실험을 맞추는 항이다.

제약: **횡방향 전용, 전진 성분 불변.** 위상은 에피소드 시드에서 유도(§4). 목표를 놓치고 배회하면 침투율이 엉뚱한 이유로 떨어진다 — P2가 이걸 잡는다.

**② 라우팅**. A1의 반발은 `dist ≤ repel_margin·r_kill` 일 때만 켜지는 **접촉 회피**다. A2는 limiter 배치를 보고 **미리** 최대 간극 쪽으로 접근 방향을 편향한다. 이게 정적 링을 깨는 항이고, 논문 명제의 핵심 기전이다 — 사전 배치는 예측 가능하므로 우회당한다.

### 2.4 A3 — 두 변형

베이팅은 방어자의 발사 조건 추정을 요구한다.

```
A3-fair       관측 가능 대리량만 사용 (finisher까지 거리 · 네트 축 정렬 ·
              limiter 포위도) -> "지금 쏠 만해 보이는가" 를 기하로 추정
A3-privileged env의 v_shot_soft 를 직접 읽음 -> 베이팅 능력의 상한
```

**A3-fair가 논문 본문의 주 baseline, A3-privileged는 상한/positive control.**
둘을 분리하는 이유: A3-fair가 안 통하면 그건 *"현실 공격자는 발사 조건을 추정 못 한다"* 는 결과이고, A3-privileged가 통하면 *"추정만 가능해지면 무너진다"* 는 별개 결과다. 하나로 합치면 둘 다 못 말한다.

행동: 커밋 전에는 **회피를 억제**하고 네트 축에 정렬해 포획 가능해 보이게 한다(feint) → 커밋 비트가 뜨는 즉시 최대 회피. `bait_gain = 0`이면 억제가 사라져 A2로 복귀.

### 2.5 A4 — 이 블록에서 구현하지 않음

falsifier core 재사용 + policy-coupled adapter 필요. `docs/26` R5 소관. **다만 A3 설계는 A4가 탐색할 파라미터 공간이 되도록 지금 잡는다** — A4를 나중에 붙이려고 A3를 다시 쓰지 않기 위해.

---

## 3. 난이도 축

두 축이 곱해진다.

```
행동 등급   A1 / A2 / A3-fair / A3-privileged     (이산, nesting으로 순서 보장)
물리 기민성 a_att ∈ {30, 48, 75, 78, 137} m/s²    (연속, 플랫폼 브래킷 docs/26 §4)
```

그림: `x = a_att`, `계열 = 행동 등급`, `y = 침투율`.
**붕괴 = 침투율이 임계를 넘는 첫 a_att.** 방어 arm(static ring / learned / oracle)마다 곡선군이 하나씩 나오고, **붕괴점의 격차가 헤드라인**이다.

속도는 등급별 동반(`docs/26` §4.3): 20 / 30 / 39 / 39 / 39 m/s.

---

## 4. 착취 방지 규칙 (가장 중요)

이 프로젝트는 1F에서 **증거 생성기 착취**를 이미 겪었다(max-clr LP witness 8/8). 공격자는 그 위험이 더 크다 — 손으로 세게 만들면 뭐든 무너뜨릴 수 있다.

```
규칙 1  물리 파라미터(a_att, v, omega)는 플랫폼 브래킷에서만 온다.
        손으로 고르지 않는다.

규칙 2  A2/A3의 행동 파라미터(jink_amp, route_gain, bait_gain, ...)는
        사전에 근거를 적어 선언하고 고정한다. 최적화하지 않는다.
        대신 민감도 sweep을 결과와 함께 보고한다.

규칙 3  최적화되는 층은 A4 하나뿐이며, falsifier 규율
        (선언 예산 · seed namespace · proposal-verification 분리) 아래에서만 한다.

규칙 4  어떤 방어 arm의 결과를 본 뒤에 공격자 파라미터를 바꾸지 않는다.
        바꿔야 하면 새 프로토콜 버전으로 선언하고 기존 결과와 병렬 보고한다.
```

규칙 2가 규칙 3보다 먼저인 이유: A2/A3를 최적화하면 *"어느 방어자를 상대로 최적화했는가"* 가 결과를 결정해버린다. 선언 후 고정이 더 싸고 더 방어 가능하다.

**시드 규율**: jink 위상 등 공격자 난수는 `c1_governance.derive_seed`(SHA-256) `paired` 모드. **같은 공격자 실현이 모든 방어 arm에 적용되어야 한다**(CRN paired 비교).

---

## 5. 검증 property (구현과 동시에 작성, 실험보다 먼저)

`tests/test_attacker_ladder.py`

| | property | 성격 | 실패 시 |
|---|---|---|---|
| **P1** | `AdversaryLadderEnv(attacker=A1)` ≡ `ShapingParallelEnv`, 동일 시드에서 **전 궤적·전 info 필드 bit-identical** | **강제** | 사다리 무효. 진행 정지 |
| **P1b** | `A2(jink=0, route=0)` ≡ `A1`, `A3(bait=0)` ≡ `A2` (nesting) | **강제** | 난이도 축에 순서 없음. 진행 정지 |
| **P2** | **무방어 상대 전 층 침투율 = 1.0** | **강제** | 공격자 자해. jink가 목표를 놓치고 있음 |
| **P3** | 고정 참조 방어자 상대 침투율이 층에 대해 단조 비감소 | **보고만** | 강제 아님 — 실패하면 그 자체가 발견(회피가 방어자를 돕는 경우) |

**P2가 이 블록의 핵심 안전장치다.** 공격자를 강하게 만들다가 실제로는 약하게 만드는 실수를 잡는다. 값싸고 결정적이다.

P3를 강제하지 않는 이유: 강제하면 통과할 때까지 튜닝하게 되고 그게 규칙 2 위반이다.

---

## 6. 블록 산출물과 순서

```
1  shepherd/scripts/mission_rollout.py     env.step 직접 호출 · 4분할 라벨
                                           (침투율을 재야 아무것도 채점 못 함)
2  shepherd/agents/attacker_ladder.py      A1 위임 래퍼 + A2
3  shepherd/env_adv.py                     AdversaryLadderEnv
4  tests/test_attacker_ladder.py           P1 / P1b / P2 / P3
5  A2 붕괴 sweep (a_att × 방어 arm)        첫 곡선
6  A3 구현                                 다음 블록
```

**1번이 2번보다 먼저인 이유**: P2를 채점하려면 침투 라벨이 필요하다. mission harness가 *"장치를 만든다"* 가 아니라 **공격자 검증 계측기**로 들어온다 — 동기가 구체적이다.

`mission_rollout.py`는 최소 범위: `env.step`/termination 직접 호출, 4분할 라벨(`CAPTURED`/`PENETRATED`/`SPENT_FAIL`/`TRUNCATED@80`), 동시 flag·우선순위 그대로 기록. **predicate 복제 금지, `rollout_unified` 무수정.**

### 라벨링 (claim governance)

```
강도   = SEARCH_CANDIDATE
일반성 = FIXED_CONDITION
모드   = DISCOVERY / NON-EVIDENTIAL
```
봉인·사전등록은 확증 실행 시점에만.

---

## 7. 사전 확정 사항 (결과 보기 전 고정)

```
붕괴 정의     침투율 > 50% 가 되는 첫 a_att,  N_limiters = 4 고정
             (포획률이 아니라 침투율 — truncation이 성공도 실패도 아니므로)
비교 단위     (a_att × 행동 등급 × 평가 시드), 모든 방어 arm에 동일 실현 적용
공격자 파라미터 §4 규칙대로 선언 후 고정. 결과 보고 변경 금지
A1 결과      본문 단독 게재 금지 (docs/26 §5.3)
```

---

## 8. 예상되는 실패 모드

| | 징후 | 판독 |
|---|---|---|
| **F1** | P1 실패 — 서브클래스가 frozen env와 다른 궤적 | 복사 오류. 즉시 정지, 라인 단위 대조 |
| **F2** | P2 실패 — A2가 무방어 상대 침투율 < 1 | jink가 전진을 갉아먹음. 횡방향 사영 재확인 |
| **F3** | A2에서도 곡선이 안 벌어짐 | 정적 기하가 강함(리스크 1 현실화). A3까지 가서 재판정 — A3에서도 안 벌어지면 명제 기각, 압축 대신 타이밍·역할 축으로 이동 |
| **F4** | 전 층에서 모든 arm 침투율 ≈ 1 | 운용점이 이미 붕괴 영역. a_att 하단(또는 τ 하단)으로 축을 내림 — **결과를 본 뒤가 아니라 F4 조건을 지금 적어두므로 소급 아님** |
| **F5** | A3-fair가 발사를 못 유도 | 결과로 보고("현실 공격자는 발사 조건 추정 불가"). A3-privileged 상한과 대비 |

---

## 9. 이 블록이 논문의 어느 칸인가

```
A2/A3 구현      -> §6 결과 그림의 x축 그 자체 (인프라 아님)
P1/P1b/P2       -> §6의 신뢰성 근거 (방법 섹션 3문단)
A2 붕괴 sweep   -> §6 첫 곡선
mission_rollout -> §5·§6 전체의 종속변수 계측기
```

`docs/26` 원칙: *답이 "평가 장치를 만든다"이면 논문 기여가 아니라 비용*. 이 블록은 **전부 §6으로 들어간다.**
