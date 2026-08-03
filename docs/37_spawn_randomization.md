# 스폰 랜덤화 배선 — 그리고 지평선이 짧다는 발견

**2026-07-29 · `docs/36` §4 이행 · 신규 3파일, 테스트 P19–P27**

---

## 0. 요약

```
1. 배선 완료 — 동결 파일 0줄 수정. AgentKin.p0/v0/e0 재기입만으로 충분했다
2. 공격자만 흔든다 — limiter/finisher 는 기준선·프레임 계약 때문에 고정
3. ★ 배선하고 재보니 episode_len=80 이 짧다 — 링이 서면 43% 가 TRUNCATED
4. ★ H=160 에서 2/30 로 떨어지고 H=320 과 동일 -> 160 이 최소 충분 지평선
```

**3번이 이번 작업의 실질입니다.** `docs/36 §2.6` 이 위험으로만 적어둔 것이 측정됐습니다.

---

## 1. 무엇이 문제였나

`sim/analytic.py` L97-107:

```python
def reset(self, seed: int):
    """Deterministic reset to (p0, v0, e0). seed only seeds an (unused-by-
    default) RNG so a later env can add seeded jitter without breaking this
    backend's determinism contract."""
```

**훅은 처음부터 이 용도로 남겨져 있었고 한 번도 안 쓰였습니다.** `make_env.py` 는
공격자를 `p0=[24,0,0]`, `v0=[-speed,0,0]` 로 축 위에 정면 배치합니다.
⇒ **모든 에피소드의 초기조건이 비트 단위로 동일.** 변동은 viability 샘플러의
`step_seed` 뿐입니다.

클레임 사다리(FIXED_CONDITION → MULTI_RESET → DISTRIBUTION_LEVEL)에서
이 상태로는 **FIXED_CONDITION 을 영원히 못 벗어납니다.**

---

## 2. 배선 방식 — 프록시조차 필요 없었다

`AgentKin.p0/v0/e0` 는 평범한 dataclass 필드이고 `reset()` 은 거기서 복사합니다.
그리고 `layout.adversary_p0/v0` 는 **생성 시점 이후 아무도 읽지 않습니다**(확인함 —
`env.py` 는 `limiter_p0` 만 소비). 따라서:

```python
spawn_for_episode(env, spec, seed=seed, episode=ep)   # p0/v0/e0 재기입
env.reset(seed)                                        # 동결 reset 이 복사
```

**동결 파일 0줄 수정.** `env_adv.py` 의 백엔드 프록시보다도 가볍습니다.
`AdversaryOverrideBackend` 로 감싸져 있어도 `__getattr__` 위임 덕에 그대로 동작합니다.

### 왜 공격자만 흔드나

| | 흔드나 | 이유 |
|---|:---:|---|
| 공격자 | **O** | 위협은 분포다 |
| limiter | X | `layout.limiter_p0` 가 hold_position 기준선이자 COMA 반대사실(`env.py: cf[i] = layout.limiter_p0[i]`). 흔들면 기준선과 실제 배치가 어긋난다 |
| finisher | X | `spawn_bank.check_frame` 이 apex==(2,0,0) STRICT 강제. v_shot 콘의 꼭짓점 |

**프레이밍상으로도 이게 맞습니다: 우리 배치는 설계 선택이고, 위협이 분포입니다.**

---

## 3. 선언값과 그 근거 — 임의로 고른 숫자가 아니라는 것

| 필드 | 값 | 근거 |
|---|---:|---|
| `dx` | 2.0 m | x ∈ [22, 26]. 도달시간 ±0.1 s. 정책이 "몇 스텝째"를 못 외우게 하는 **최소** 폭이고 회랑 기하는 안 바꾼다 |
| `r_lat` | **5.0 m** = `ring_radius` | **방어 개구 전체.** "위협은 개구 어디로든 온다"는 위협모형 진술. 더 크면 링 바깥 우회라 문제 성격이 바뀌고, 더 작으면 링 일부가 영영 안 쓰인다. **경계값이 자연스러운 선언** |
| `psi` | 0.0 rad | 횡오프셋이 이미 방위각을 만든다 (atan(5/24)=0.21 rad=12°). 각오차는 2차 효과이고 동결 호밍이 몇 스텝 안에 지운다. 축은 열어 둠 |
| `speed_frac` | 0.0 | 동결 공격자가 `v_nominal` 로 되돌아가므로 과도현상. **의미 있는 속도 축은 `v_nominal` 자체**이고 그건 config 레벨 (docs/36 C-2 대기) |

샘플링: 횡오프셋은 **면적 균일**(`sqrt(u)`) — 반경 균일이면 중심이 과표집됩니다.
난수는 SHA-256(`derive_spawn_u`), 파이썬 `hash()` 금지 — `derive_phase` 와 동일 규약.
**축마다 독립 인덱스**를 씁니다(공유하면 축 간 상관이 생김, P23b 가 강제).

---

## 4. ★ 배선하고 재보니 나온 것 — 지평선이 짧다

`ring` 배치, 기본 스폰, 30 에피소드:

| `episode_len` | 라벨 | 평균 최소거리 | 판정 |
|---:|---|---:|---|
| **80 (현행)** | PENETRATED 17 / **TRUNCATED 13** | 1.05 | **43% 가 절단** |
| **160** | PENETRATED 28 / TRUNCATED 2 | 0.82 | 안정 |
| **320** | PENETRATED 28 / TRUNCATED 2 | 0.82 | **160 과 동일 — 수렴** |

`hold` 배치는 전 지평선에서 30/30 PENETRATED, 23.6 스텝 — **영향 없음.**
⇒ 지연은 **링과의 상호작용**에서 나옵니다. 공격자가 밀려나며 궤도를 돌고,
축 위 정면 접근이 아니면 그 지연이 4 초를 넘습니다.

### 왜 이게 중요한가

**M4 보상은 TRUNCATED 에 `-c_trunc` 를 줍니다(실패).**
`episode_len=80` 인 채로 재학습하면 정책은 **43% 의 에피소드에서 "실패했기 때문이 아니라
시간이 끝나서" 벌을 받습니다.** 그러면 §6 의 결과는 지평선의 산물이고,
"지평선이 짧아서 이긴 것처럼 보인다"는 반박을 못 막습니다 —
`RewardSpec` docstring 이 스스로 경계한 바로 그 산물입니다.

### 대응 — 두 갈래 중 하나만 정직하다

```
(a) 지평선을 늘린다 (80 -> 160)
    지평선은 우리 부기 파라미터지 물리 주장이 아니다. 160==320 수렴이 근거다.
    비용: 에피소드 길이 2배

(b) 스폰 범위를 줄인다 (r_lat 5.0 -> 2.5)
    측정: TRUNCATED 13/30 -> 2/40. 숫자는 좋아진다.
    그러나 이건 **결과를 보고 위협모형을 줄이는 것**이다. 금지.
```

**(a) 를 채택합니다.** `configs/m2_l2_train.yaml` 은 동결이므로 override 경로로 씁니다
(`as_config({"train.episode_len": 160})`) — 그게 registry 가 설계한 실험 방식이고
동결 파일은 안 건드립니다.

**잔여 2/30 은 진짜 방어 결과**(링이 끝까지 막아냄)이며 절단으로 보고합니다.

---

## 5. 신규 파일

| 파일 | 줄 | md5 |
|---|---:|---|
| `shepherd/spawn_rand.py` | 257 | `4dbd5905b79e759fda50cadd0bc3aec5` |
| `tests/test_spawn_rand.py` | 303 | `33123bddf51e6dab34c6ff364c968a68` |
| `shepherd/scripts/spawn_sweep.py` | 67 | `0a415784cc88e1088085bf9a685db62e` |

**테스트: 38 passed, 1 skipped** (기존 M4 스위트 합산 67 passed, 1 skipped — 회귀 없음).

| 성질 | 내용 |
|---|---|
| **P19 / P19b** | `enabled=False` 는 동결 경로와 bit-identical (값 + 궤적) |
| **P20 / P20b** | 결정론 · 에피소드마다 상이 · SHA-256 (프로세스 salt 무관) |
| **P21 / P21b** | 선언 범위 이탈 없음 (500 draw), 속력 보존 |
| **P22 / P22b** | `psi=0` 이면 표적 정조준, `psi>0` 이면 콘 경계 준수 |
| **P23 / P23b** | 면적 균일(중심 과표집 없음), **축 간 무상관** |
| **P24 / P24b** | 에피소드 내 불변 · 반복 적용해도 랜덤워크 없음 |
| **P25** | 스폰 적용 후에도 (seed, ep) 재현성 |
| **P26** | **시나리오 적형성** — 무방어면 어떤 스폰에서도 지평선 안에 표적 도달 |
| **P27** | **지평선 게이트** — §4 를 고정 (느림, `RUN_SLOW=1`) |

> P26 은 **무방어** 도달성만 봅니다. P27 이 **방어 하에서의** 지평선 충분성을 봅니다.
> 두 개가 갈라진 지점이 §4 의 발견입니다 — P26 은 통과하는데 임무 지표는 절단됐습니다.

---

## 6. 남은 것

```
[x] 스폰 랜덤화 배선                 <- 이 문서
[ ] episode_len 80 -> 160 선언       <- §4. 재학습 전, 결과 보기 전
[ ] docs/36 §3 7개 보정값 선언
[ ] tau 관측 1차원 (= 런처 스펙)
[ ] train_m4.py 배선 (docs/32 [D])
[ ] [E] 스케일 스모크 -> terminal_scale
--- Human-lane ---
[ ] C-1 Xu PDF 한 문단 · C-2 FPV 스펙시트 · 발사 설계점 선언
```

`speed_frac` / `psi` / `dodge_amp` 는 **축을 열어두되 기본 off** 입니다 —
C-2(FPV 스펙) 확정 후 한꺼번에 선언하는 게 맞습니다. 지금 켜면 근거 없는 범위로 돌게 됩니다.
