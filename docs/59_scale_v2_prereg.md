# 59 — 교전 스케일 계약 v2 사전등록 (브랜치 `feat/scale-up-v2` 격리)

**2026-08-07 · 결과를 보기 전에 쓴다. 트리거 = 궤적 뷰어 육안 검사 (Hyunjun).**

---

## 0. 근거 — 왜 스케일이 문제인가

뷰어 실측 (legacy 회랑):

```
스폰 거리 21.7~25.1 m · 공격자 14~26 m/s · 교전 전체 0.75~2.8 s
ring 대기 x=8 -- NK 경계(x=6)에서 2 m · tau_deploy 0.3 s = 성공 판의 ~40 %
공격자의 ring→NK 통과: 2 m / ~20 m/s = 0.1 s (2 tick)
```

이 스케일은 M2 셰이핑 게임의 legacy 이며 **교전 시간 자체가 비준된 적이
없다.** 이 렌즈로 기존 결과가 재해석된다 (전부 "legacy small-scale regime"
한정으로 재스코프):

- 접촉 42/42 NK-안 (docs/57·58) — NK-밖 교전 창이 기하적으로 ~2 m 폭
- 폴백 불능 — net 해소 후 잔여 비행 ~0.5 s, limiter 이동 여력 ~3 m
- LS≈SS — 편대 학습이 값어치를 만들 시간이 ~10 tick
- robust-clean knife-edge — 1초 순발력 게임의 산물일 가능성

**기존 결론은 폐기가 아니라 regime 한정이다.** 도구(계약·probe·뷰어)는 이식.

## 1. 원칙 — 하드웨어/안전 절대값 고정, 기하·시간만 확장

| 구분 | 항목 | 값 | 처리 |
|---|---|---|---|
| **고정** (하드웨어 N1 근거) | kill_radius 0.75 · net cone (half-angle 0.067, range_max 29.85) · net_radius 1.77 · tau_deploy 0.3 · a_max 들 · dt 0.05 | — | 불변 |
| **고정** (안전/법 근거) | r_nk = 6 m | — | 불변. 300 m 세계에선 2 % — NK 구속이 저절로 풀리는지가 v2 첫 관전 포인트 |
| **확장** | `train.layout.adversary_start_x` | 24 → **300** | 30 m/s 급에 ~10 s+ 대응시간 (Hyunjun 지시 "적어도 300 m") |
| **확장** | `train.episode_len` | 80 → **400** (20 s) | 300 m / 15 m/s 최악 커버. dt 유지 (적분·swept 분석이 dt=0.05 전제) |
| **확장** | `train.layout.ring_center` | (8,0,0) → **(50,0,0)** | 대기점 승격: NK 밖 + cone 상류. 공격자 20 m/s 기준 ring→NK 44 m = 2.2 s (기존 0.1 s 의 22배). **설계 변수로 승격 — 추후 sweep 축 후보** |
| **확장** | SpawnSpec.dx | 2 → **10** | 도달시간 지터 ±0.5 s (v=20). x∈[290,310] |
| 유지 | SpawnSpec.r_lat = ring_radius = 5 | — | "위협은 방어 개구 어디로든" 선언 논리 유지 (넓히면 우회 문제로 성격 변경) |
| 유지 | x_fire = 11 | — | fire_mode="x_fire" 전용 (본선 미사용). 스케일 부정합 인지만 기록 |

알려진 파생 이슈 (v2 에서 건드리지 않고 기록만):
- PARK_POSITION (0,0,60): ring 50 과 근접해져 "ring 12배" 근거가 깨진다.
  스크립트 probe 에는 무영향 (v_shot 기여 0 조건은 유지 — 공격자 회랑에서
  ≥55 m). **RL 학습 재개 전 P51 재검토 필수** 로 등재.
- 관측 좌표 크기 ~300: RunningNorm 은 학습 시점 문제 — 등재만.

## 2. 격리 규율

- 브랜치 `feat/scale-up-v2`. main 라인(feat/l2-mappo-train)과 섞지 않는다.
- 배선 = **config overlay dict 하나** (`shepherd/scale_v2.py`). 새 코드 경로
  없음. overlay 미적용 시 기존과 **비트 동일** (P85 강제).
- legacy 수치와 v2 수치를 같은 표에 섞지 않는다 (P78 규율 동형).

## 3. 검증 게이트 (결과 보기 전 선언)

```
P85  overlay 미적용 -> as_config() 기본값 기존과 동일 (비트)
P86  v2 스모크: 공격자가 300 m 를 실제로 비행해 도달, 에피소드가
     400 스텝 안에 정상 종료 (침투/포획/절단 중 하나), A2 조향 정상
V4   v2 baseline (hold/clean · F-flags · n=100): 라벨 분포 보고.
     ★ 수락대역 없음 -- v2 는 새 regime 의 첫 측정이다. 예상 방향만 기록:
     대응시간 증가로 (i) NET_CAPTURE 상승 또는 (ii) 조기 fire 낭비 증가
     중 어느 쪽이 지배하는지가 첫 질문
V5   v2 뷰어 재생성 -> 육안 재검사 (Hyunjun) -- 스폰·대기·NK 비율이
     의도대로인지. 여기서 승인 후에야 v2 위 실험 사슬 재개
```

## 4. v2 이후 순서 (뷰어 승인 후)

```
1. miss/capture 재분류 + 뷰어 대조
2. coupling gate 재론 -- 300 m 에선 반응형 공격자·shepherding 질문이
   처음으로 물리적 의미를 가짐. 경로 A/B 결정을 v2 에서 다시
3. NK-밖 창 재측정 (legacy 의 42/42 NK-안이 스케일 산물이었는지 판정)
4. 3-way 는 그 뒤
```

판정식·선언값은 결과 후 불변경. ring_center 등 "설계 변수" 의 조정은
새 사전등록으로만.
