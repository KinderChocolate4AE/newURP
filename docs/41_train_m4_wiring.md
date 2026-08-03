# M4 학습 배선 완료 — docs/32 [D]·[E]

**2026-07-29 · 남아 있던 유일한 코드 항목**

---

## 0. 요약

```
[D] train_m4.py 배선 완료 — MAPPORunner 상속, 환경 조립만 교체
    환경 합성은 torch-free m4_env.py 로 분리 (조립을 torch 없이 검증 가능)
[D]-④ 관측 = 위협 등급 2차원 (63 -> 65). ablation 축(--no-threat-obs) 도 뚫어둠
[E] 스케일 스모크 실측 -> terminal_scale 기본값 10 -> **1.0** 로 정정
★ 실측 부산물: 조밀 신호가 희소하다 (에피소드당 sum|dense| 중앙값 0.0)
로컬 엔드투엔드 스모크 통과 (2048 스텝, 산출물 저장까지)
```

---

## 1. 배선 구조

```
m4_episode_config(seed, ep)     위협 등급 뽑기 + 능력 비율 연동
        |
  make_train_env                동결 env
        |
  ModeSystemEnv                 하드킬 방아쇠 · no-kinetic zone · M4 보상
        |
  attach_attacker(inner, ...)   공격자 사다리 (백엔드 프록시 -- inner 에 건다)
        |
  spawn_for_episode(inner, ...) 초기조건 재기입 (reset 전)
        |
  attach_threat_obs             위협 등급 관측 2차원
```

**행동 공간은 변경 없다** — limiter `Box(4)` idx 3 이 곧 커밋 비트이고,
동결 env 는 그 차원을 무시하며 `ModeSystemEnv` 가 읽는다 (docs/29 §3.1).

`MAPPORunner` 를 **상속**해서 쓴다(복사 금지). 재정의는 세 곳뿐:
`__init__`(관측 폭이 2 넓어져 액터/크리틱 크기가 달라진다) ·
`_begin_episode`(환경 조립) · `evaluate`(임무 지표).
`collect_rollout` / `update` / `rolling` / `learned_bundle` 은 그대로 상속한다.

---

## 2. [D]-④ 관측 — 결론이 바뀌었다

원래 미결은 *"τ 를 관측에 넣을 것인가"* 였다. **τ 는 이제 상수(0.30)라 그 질문이 사라졌다.**
대신 에피소드마다 바뀌는 것은 **위협 등급**이고, 그게 명제 N 경계를 가로지른다:

```
a_att < 44.4  ->  조향 없이도 포획됨
a_att > 44.4  ->  조향이 필요함
```

**같은 상태에서 최적 행동이 위협에 따라 달라진다.** MAPPO 액터는 단일 프레임 MLP
(순환 없음)라 관측만으로 `a_att` 를 추론할 수 없다. 그래서 위협 등급 2차원을
브래킷 정규화([-1,1])해서 붙인다. `state()`(중앙 크리틱)에도 같이 붙여 CTDE 일관성을 지킨다.

**반칙이 아닌 이유**: 숨은 환경 파라미터를 훔쳐보는 게 아니라 **시스템이 실제로 하는
분류**다 (Pliska 의 탐지·추적, Drones 10(6):420 의 YOLO mAP@0.5=0.96).
**한계는 명시한다**: 여기서 분류는 무오차다. 오분류 하 강건성은 future work 이고,
이 한계는 **우리에게 유리한 쪽**이므로 논문에 반드시 적는다.

`--no-threat-obs` 로 regime-blind ablation 을 돌릴 수 있다.
**이 대조군이 §6 의 핵심 증거다** — 위협을 못 보는 정책이 무엇을 잃는지가 곧
"위협의 함수로 중재한다"는 주장이다.

---

## 3. [E] 스케일 스모크 — terminal_scale 10 → 1.0

종말항 크기는 이미 안다 (`RewardSpec.terminal()` 은 0~1 상수). 실측할 것은
**에피소드당 `sum|dense|` 하나**뿐이다. `w_kill=0.5`, 16 에피소드:

| 배치 | 라벨 | 평균 길이 | **sum\|dense\|** | 스텝당 |
|---|---|---:|---:|---:|
| hold | PENETRATED 12 / NET_CAPTURE 3 / SPENT_FAIL 1 | 23.2 | **평균 1.000, 중앙 0.000** | 0.0488 |
| ring | 동일 | 23.2 | 평균 1.002, 중앙 0.005 | 0.0489 |

`|TERMINAL|` 최대 = 1.0 → **같은 자릿수는 `terminal_scale = 1.0`**.
기존 기본값 10 은 종말항을 10배 과대평가한다. CLI 기본값을 1.0 으로 정정했다.

> docs/29 §15.3 은 *"종말 신호가 조밀항에 묻힌다"* 를 걱정했는데 **측정은 반대**다.
> 조밀 신호가 오히려 희소하다.

### 3.1 ★ 부산물 — 조밀 신호가 희소하다

`sum|dense|` 의 **중앙값이 0.0** 이다. 즉 **대부분의 에피소드에서 조밀 보상이 문자 그대로 0**
이고, 소수 에피소드만 최대 7 까지 튄다. 그리고 hold 와 ring 이 거의 동일하다 —
적형성 게이트에서 본 것과 같은 얘기다(조향이 `v_shot` 을 잘 못 움직인다).

**함의**: 학습 신호가 사실상 종말항 하나다. 그러면 docs/29 §15.2 의
**커밋 차원 credit assignment 위험(`coma_D` 가 `v_shot_soft` 차분이라 커밋을 못 덮는다)**
이 그대로 현실화될 수 있다. 폴백(규칙 기반 커밋 가드 + 배치만 학습)은 이미 사전등록돼 있다.
**첫 학습에서 발사가 안 나오면 그 폴백으로 간다.** 지금 값을 만지지 않는다.

---

## 4. 임무 지표 — `interdiction_rate` 를 안 쓴다

기존 `interdiction_rate = 1 − PENETRATED` 는 SPENT_FAIL(탄 소진·미무력화)과
TRUNCATED(우측 절단)를 성공으로 센다 (docs/40 §8.2 각주). `mission_eval` 은 분해해 낸다:

```
penetrated_rate     침투
neutralized_rate    실제 무력화 (NET_CAPTURE + CAPTURE_WITH_CONTACT + HARD_KILL)
spent_fail_rate     탄 소진, 미무력화
truncated_rate      우측 절단
nondestructive_frac 2차 지표 = 포획 / (포획 + 하드킬)
by_regime           ★ 위 전부를 FREE_CAPTURE / SHAPING_NEEDED 로 쪼갠 것
```

`by_regime` 이 §6 의 핵심 표가 된다.

`mission_rollout.run_episode` 에 `policy=` 훅을 **추가**했다(기본 None → 기존 경로와
bit-identical, P36 이 강제). 라벨링 술어를 복제하지 않고 학습 정책을 평가하기 위해서다.

---

## 5. 신규/변경 파일

| 파일 | md5 | |
|---|---|---|
| `shepherd/obs_threat.py` | `6300e64ec60672c66dbb62bd2588ef18` | 신규 · torch-free |
| `shepherd/m4_env.py` | `21fd7463d9bdc650c56cc7fa33206d89` | 신규 · torch-free 합성 루트 |
| `shepherd/scripts/train_m4.py` | `bcfbaba4a9eede15faea334709f83fd6` | 신규 · 학습기 + CLI |
| `shepherd/scripts/scale_smoke.py` | `4a1f0bd99e213e8efb01a7538ba68fa1` | 신규 · [E] |
| `shepherd/scripts/mission_rollout.py` | `e0bf105842e0cb367d995f2e10ee2e64` | **변경** · policy 훅 추가 |
| `tests/test_m4_wiring.py` | `c6cc0f4c7a59a90e31b281f6006625ef` | 신규 · P33–P37 |

**M4 스위트 전체 87 passed, 2 skipped** (회귀 없음).

| 성질 | 내용 |
|---|---|
| P33 | 스택 조립·스텝·M4 info 주입 |
| P34 | 위협 관측 정확히 +2 차원, ablation 은 원폭, `state()` 동시 확장, 값 일치 |
| P35 / P35b | **두 regime 이 모두 생성됨**(쏠림 없음) · 경계가 명제 N 과 일치 |
| P36 / P36b | **policy 훅이 기본 경로를 안 바꾼다** · 주면 실제로 쓰인다 |
| P37 | 2층 지표가 regime 별로 쪼개져 나오고 비율 합이 1 |

---

## 6. 로컬 엔드투엔드 스모크

```
python -m shepherd.scripts.train_m4 --total-env-steps 2048 --eval-episodes 4

[M4] tau = 0.3 = tau_flight(0.15) + tau_sense(0.1) + tau_decide(0.05)
[M4] 명제 N 경계 a* = 44.4 m/s^2, 브래킷 [11, 78] -> 가로지름 OK
[M4] w_kill=0.5 공격자=A2/LAM_REF 위협랜덤화=ON 위협관측=ON
[seed 0] upd 2/2 step=2048 ret=-8.298 | 무력화 0.00 침투 1.00 비손실 0.00
         | free_cap 0.06 shape_cap 0.00 shape_hk 0.00
```

산출물: `ckpt_mappo_*.pt` · `obs_norm_*.json` · `threat_log_*.json`(에피소드별 위협·regime·하드킬)
· `mission_curve.json` · `summary.json`.

**미학습 정책이 100% 침투당한다** — 시나리오가 랜덤 정책에 자명하지 않다는 정상 신호다.

---

## 7. 서버로 넘길 것

```
[A] git 커밋·푸시                         (Windows 네이티브)
[C] 서버 pull -> venv -> 스모크           python -m pytest tests/ -q
                                          python -m shepherd.scripts.op_gate --n 12
[F] sweep 실행
```

| 축 | 값 | 성격 |
|---|---|---|
| `--w-kill` | 0.0 / 0.25 / 0.5 / 0.75 / 1.0 | **선언된 sweep 축 — 뒤집히는 지점이 결과** |
| `--seed` | 5 | paired 비교 |
| `--no-threat-obs` | on/off | **regime-blind ablation — §6 의 대조군** |
| 공격자 | 학습 A2 / 평가 A3 | 일반화 확인 |

`5 x 5 x 2 = 50 런`. **`--no-threat-randomization` 은 쓰지 않는다** (게이트 미통과 조건).

### 검증 게이트 (결과 보기 전 고정)

```
G-1  P6 재확인      커밋 비트 0 인 정책은 동결 env 와 bit-identical
G-2  스케일         terminal_scale=1.0 (실측 근거 §3)
G-3  퇴화 검사      w_kill=1 에서도 "차라리 뚫리게 두는" 해로 가지 않는지
G-4  2층 지표       무력화율 · 비손실 비율을 **둘 다**, **regime 별로**
G-5  라벨           SEARCH_CANDIDATE / FIXED_CONDITION 유지
G-6  ★ 커밋 학습    발사 사건이 0 이면 docs/29 §15.2 폴백(규칙 기반 커밋 가드)으로.
                    사전등록된 경로이며 결과를 본 뒤 만든 것이 아니다
```

---

## §3-보론 — 계측 경로 버그 확인 (2026-08-03). **선언은 바뀌지 않는다**

§3 의 `terminal_scale = 1.0` 은 그대로다. 아래는 그 선언을 **다시 여는 것이 아니라**,
선언의 근거를 만든 계측 경로에 버그가 있었고 그것이 선언값을 움직이는지 확인한 기록이다.

**무엇이었나.** 커밋 비트는 limiter 행동 벡터 `idx3` 에 실려 있다. `run_episode` 는
`_zero_commit` 으로 눌러 두지만(정정 3 의 수정), `scale_smoke._episode` 는 그 수정을
받지 못했다. 그리고 `ring` 은 **네 대 모두 `idx3 = 1`** 을 내보낸다. 즉 [E] 의 `ring`
은 게이트·기저선의 `ring` 과 다른 행동 분포였다. `hold` 는 `idx3` 이 원래 0 이라 무해.

**선언값이 움직이는가 — 실측 (48판, w_kill=0.5).**

| mode | 현행(버그) `sum\|dense\|` | 수정 후 | 도출되는 `terminal_scale` |
|---|---|---|---|
| hold | 1.042 | 1.042 (동일) | 1 → **1** |
| ring | 1.044 | **1.328** | 1 → **1** |

스크립트는 `10^round(log10(ratio))` 로 반올림하므로 1 에서 10 으로 넘어가려면
`ratio > 3.16` 이어야 한다. 최악값이 **1.328** 이라 2.4배 여유가 있다.
라벨 분포도 양쪽 동일(35 PENETRATED / 9 NET_CAPTURE / 4 SPENT_FAIL) — 결과가 바뀌는
종류가 아니라 보상 회계만 어긋난 것이다.

**따라서 `terminal_scale = 1.0` 은 불변이고, 재선언하지 않는다.** 결과가 같더라도
사후에 다시 선언하는 모양을 만들면 "마음에 드는 값이 나올 때까지 다시 쟀다"는 반론에
문을 열어 준다. 사전 등록의 값은 그걸 하지 않는 데서 나온다.

**고친 것.** `scale_smoke._episode` 에 `_zero_commit(acts)` 한 줄. `P40e` 가
(i) 그 줄이 실제 경로에서 실행되는지, (ii) `ring` 이 여전히 `idx3=1` 을 실어서 그
가드가 유의미한지 — 둘 다 고정한다. `_episode` 를 `run_episode` 로 통째 접는 것은
`run_episode` 가 스텝별 dense 합을 노출하지 않아 별건으로 남긴다.
