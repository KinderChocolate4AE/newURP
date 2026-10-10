# 132 — E2 (AMI) 공격자 기전 개입 계약: 감사 천장 포화의 원인 분해

- **일자**: 2026-10-11 · **봉인**: `scripts/fs1_ami_manifest.py` → `artifacts/fs1/ami_manifest.json`
  (판정 상수의 단일 원천 = manifest. 이 문서와 다르면 manifest 가 우선).
- **결재**: 사용자 2026-10-10 ("A" 승인), 2026-10-11 ("근거 최대 확보 후 집필 — 당장 시작").
  범위 보강 = 지도교수 2026-10-11 (셔플 대조군 + α 0.5 용량 + E6 양방향 트리거).
- **gap**: docs/131 G1 (ρ 3.9–11.8 에서 정합 감사 천장이 ~8–9% 로 평평한 이유), 가설 D3 (창 거부 접근 기하).
- **절단선 위치**: ③ "도달 수준은 적응 회피자가 정한다" 의 기전 다리.

## 1. 질문

E7-b 의 동결 방어를 상대로 한 전용 착취자 (1e7) 의 학습 행동 중 **어느 성분**이 net 천장을 묶는가.
그 성분은 **상태에 맞춘 적응** 인가, 아니면 **그냥 움직임의 양 (에너지)** 인가.

## 2. 설계 (새 학습 없음)

- **slot**: E7-b 5 변형 × seed 3 = 15 (체크포인트 재사용, `/data/hjhong/fs1jax/e7b/<variant>/s<seed>/`).
- **계열**: det (판정) = learned_det vs `judge_exploiter` · sto (재현) = learned_sto vs `judge_exploiter_sto`.
- **arm** (공격자 = autopilot + 학습 residual; 개입은 residual 만 바꾼다):

| arm | 내용 |
|---|---|
| base | 개입 없음 (+ 구간별 residual 기록 = 셔플 공여) |
| out0 | 공격자–finisher 거리 > 16 m 에서 residual 0 (순수 homing 접근) |
| in0 | ≤ 16 m 에서 residual 0 (16 m = 기존 창 정의) |
| zfix | 기동 스킬 z 를 episode 시작값으로 고정 (rng 소비 불변) |
| lat0 | residual 을 공격자→자산 축에 사영 (횡방향 제거) |
| shuf_out / shuf_in | 해당 구간 residual 을 다른 episode (다음 seed, 순환) 의 base residual 열로 교체 — 같은 에너지, 상태와 무관 |
| in_half | ≤ 16 m residual × 0.5 (용량) |

- **평가**: 240판, E7-b 와 같은 seed (276000 + 변형·1000), 모든 arm paired. `--env-seed 0` 고정.
- **지표**: 주 = net (NET_CAPTURE + CAPTURE_WITH_CONTACT). A안에서는 둔해진 공격자가 limiter kinetic 에도
  더 잘 걸리므로 전체 방어 수는 보고만 한다. 보고: defended / K_FIRST / fallback / 침투, 창 점유
  (robust tick ≥ 1 인 episode 수, robust tick 합), 발사 episode 수.

## 3. 사전 판정 (det 계열 = 판정)

- Δ_X(slot) = net_X − net_base.
- **재현 점검**: base 의 15-slot net 중앙값이 E7-b net_det 중앙값 ± 6 안 (sto: E7-b′ net_sto) — 아니면
  `INVALID_REPRO` (파이프라인 결함, 중단).
- **LIFT(X)** (X ∈ out0, in0, zfix, lat0): 중앙값 Δ_X ≥ +8/240 **그리고** 15 slot 중 ≥ 10 개 양수.
- **구간 S ∈ {out, in} 에서 LIFT(S0) 일 때**: 중앙값(Δ_S0 − Δ_shufS) ≥ 0.5 × 중앙값 Δ_S0 → `ADAPTIVE_S`
  (같은 에너지의 무관한 residual 이 효과의 절반도 재현하지 못함), 아니면 `ENERGY_S`.
- **분기**:
  - `AMI_ADAPTIVE` — ADAPTIVE_S 가 하나라도 → 천장은 구간 S 의 상태 의존 residual 이 묶는다.
  - `AMI_ATTACKER_NONADAPTIVE` — LIFT 는 있으나 ADAPTIVE 없음.
  - `AMI_NOT_ATTACKER` — 네 개입 모두 LIFT 없음 → 이 공격자 측 제거로는 평탄부가 풀리지 않는다 (방어 측 후보).
- sto 계열: 같은 규칙, 재현용. 불일치 → "계열 의존" 으로 둘 다 보고.
- in_half: Δ 와 Δ_in0 의 상대 위치 보고 (판정 없음).

## 4. E6 트리거 (결과 전 양방향 기재)

- `AMI_ADAPTIVE` 또는 `AMI_ATTACKER_NONADAPTIVE` → E6 (학습 세계에서 a 를 실제로 낮춘 점: ρ 3.92, a ≈ 10.0,
  a_def 고정 μ' ≈ 0.72, 차이는 Λ = V²/(a·R_max) 로 명명) 을 E1 계약의 조건부 arm 으로 둔다.
- `AMI_NOT_ATTACKER` → E6 는 저널판으로.
- E6 의 가설·게이트는 E6 실행 전에 그 계약에서 봉인한다. E6 결과는 무조건 보고한다.

## 5. 발견 기록 (봉인 전, 2026-10-11)

- 정본 eval 워커는 env 를 `seed=os.getpid()` 로 만들고, 이 seed 가 m4 스택 RNG 로 새어 들어간다
  (reset 에서 다시 seed 되지 않음). smoke 에서 label·길이는 같고 v_fire 가 달라졌다. → **이전 정본 평가들은
  분포상 동등하지만 실행 간 비트 재현은 아니다.** AMI 는 `--env-seed 0` 으로 고정해 arm 간 짝맞춤을 보장한다
  (기본값 None = 기존 동작, 비트 동일 확인: smoke ckpt 4 ep 궤적까지 일치).
- 그래서 base 는 E7-b 와 숫자가 정확히 같을 수 없다 → 재현 점검은 중앙값 허용 차 (±6) 로 둔다.

## 6. 해석 한계

- 1e7 착취자 조건부. 개입은 착취자의 학습 내용을 지우는 것이지, 다른 최적 공격자를 만드는 것이 아니다.
- residual 을 지운 공격자는 방어가 학습 때 본 적이 없는 분포다 → LIFT 는 "그 성분이 천장을 묶는다" 의
  충분 근거가 아니라 필요 성분 후보다.
- 16 m 구간 경계는 기존 창 정의를 재사용 (새로 고르지 않음).
- not_evidence_for: 세계 천장, 공격자 최적성, 실물 위협 행동, E7-b/b′ 판정과의 pooling, 협력 어휘.

## 7. 실행

- `scripts/run_fs1_ami_eval.sh` (server4 CPU, WORKERS=6, tmux `=ami_e2`, ntfy) → `scripts/fs1_ami_readout.py`
  → `artifacts/fs1/ami/readout.json`. 공여 residual 은 repo 밖 `/data/hjhong/l2/ami_res/`.
- 규모: 2 계열 × 15 slot × 8 arm = 240 평가 × 240판, 예상 2–3 시간.
