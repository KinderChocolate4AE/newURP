# 2026-10-01e — P1 판독: COMPLETE_P1, route_gain 지배·sense 30m 포화·λ/bait null — P1b 는 검정력 0 (설계 결함)

## 봉인 판정

Manifest `4629158d387c938b`, 실행 코드 `2a6bada`, harvest `a36bb18`.
**`COMPLETE_P1`** (completion·budget·paired_draws·lineage 4/4).
**`P2_PREMISE_SUPPORTED`** — 주 격자 18 config 의 clean N spread = **127** ≥ 28
(사전 등록 문턱). 정본 = `artifacts/p1_ladder/readout.json`.

## P1a 지도 요약 (defender 동결: hold limiter + scripted launcher, 280 ep/config)

| 축 | 결과 |
|---|---|
| route_gain 0.2 / 0.5 / 0.8 | **N 224~229 / 143~156 / 102~115 — 지배 축** (crossings_total 은 854→1267 로 역방향 증가) |
| jink 0.6 → 0 (depth) | N 144 → 206 — 제2 축 |
| sense_range 15 / 30 / ∞ | 15→30 효과 있음 (예: r05 156→144) · **30→∞ 전 config 완전 동일** — 이 세계 스케일에서 30 m 포화 |
| λ REF → ANTIC | ±1 episode 수준 null (crossings 차이로 override 작동 자체는 확인) |
| LAM_ZERO · bait fair/priv (depth) | nominal 과 동일 — repel·bait 항 미발동 (경로상 발동 조건 미충족) |
| anchor | T0(route0)=263 · A1-pure=**280/280** — 사다리 단조성 정합 |

- **crossing episode 는 전 config 280/280**: scripted launcher 세계의 병목은
  crossing 생성이 아니라 capture 전환이며, 공격자 반응 축이 그 전환을 229→102 로
  움직인다. crossings_total 증가 (↔ N 감소) 는 "더 오래 교전하되 못 잡는" 방향.
- **pivot 가설 캐비앗 (정직)**: docs/117 에서 강조한 "종말-한정 관측"(sense_range)
  기전은 이 suite 스케일에서 binding 이 아니다 (30 m 포화 — docs/80 §2 의 KSAS
  스케일 사례와 동형). P2 전제를 실제로 지지하는 축은 route·jink 다.
- χ50: route↑ 에 따라 행별 χ50 하강 (방어 유효 영역 축소) 방향 일관. r02 는 다수
  행 censored (p ≥ 0.5 유지 — 경계가 행 범위 위) · a1_pure 전 행 censored.

## P1b — 무효 판정 (검정력 0, 설계 결함. Δχ50 숫자를 인용 금지)

τ_a/τ₀ ∈ {0.1, 0.3} 의 행별 Δχ50 이 **전부 정확히 0.0** 이다. 이는 점질량 추상화
검증이 아니라 **test 가 자명했다는 뜻**이다: hold limiter 는 보류점 유지라
a_cmd ≡ 0 이고, 0 에 1차 지연을 걸어도 0 이므로 rollout 이 bit-identical 하다.

- 원인 = 봉인 설계 실수 (AI): docs/93 §5 는 "scripted arm (**B2 rule-based**)" 에
  plant swap 을 걸라고 했는데, docs/118 은 P1a 와의 일관성을 이유로 **hold** 를
  defender 로 봉인했다. 기동 없는 defender 에는 가속 지연이 정의상 무력하다.
- 처분: P1b 결과는 "no-op 확인" 으로만 기록하고 **plant-swap pre-check 는 미완**
  이다. **P1b-2** (별도 소계약): defender = **c5 arc limiter** (B2 RULE_COOP
  limiter_kw) + scripted launcher, τ ∈ {0, 0.1, 0.3} 자체 baseline 포함 3 arm
  paired, 동일 28-cell suite. c5 는 기동하므로 lag 가 실제로 작동한다.
  P2 학습 착수 전 완료 조건은 P1b-2 로 승계.

## 다음

1. P1b-2 소계약 봉인 + 실행 (서버 840 ep — 소규모).
2. P2 limiter-only v2 계약 초안 — 공격자 mix 는 P1a 지도에서 선정 (route 축 중심
   {0.2, 0.5, 0.8} + jink0, sense 축은 {15, 30} 만 — ∞ 는 30 과 중복이므로 제외).
3. K1 손증명 (사용자, ≤10/31) — docs/119.
