# HANDOFF — main → JAX: E7-b′ (sto 감사) → E7-c 순서로 발사 (2026-10-09, 사용자 승인)

봉인: E7-b′ = docs/129 §8 + manifest `build_e7b2` **`d25bf6e6dedf31ea`** / E7-c v1.2 = docs/130 §9 +
`build_e7c` **`46cea2edfd601f10`**. server4 GPU 1장 (서버 룰), CPU 점유 최소. 발사 전 nvidia-smi.

## 1단계 — E7-b′: 착취자만 15개 (방어 재학습 없음)

- 대상: E7-b 동결 방어 `/data/hjhong/fs1jax/e7b/<variant>/s<seed>/ckpt.pt` (pin eef7c27 산출).
- `--exploit <ckpt> --exploit-sto`, 1e7, **변형 세계 플래그 동일** (E7-b 착취자와 같은 τ/θ/aim),
  jseed **281000 + vi·1000 + seed** (vi = 변형 순서 t0.7_h1.0_cv, t0.7_h1.5_cv, t0.5_h1.0_cv,
  t0.5_h1.5_cv, t0.5_h1.0_ma).
- 출력: `/data/hjhong/fs1jax/e7b/<variant>/s<seed>/judge_exploiter_sto/{ckpt.pt, log.jsonl, config.json}`
  (config 에 `exploit_sto: true` 확인). 기존 `judge_exploiter/` 는 건드리지 말 것.
- 완료 보고 → main 이 server4 정본 평가 (`run_fs1_e7b2_eval.sh`) 발사. **E7-c 는 E7-b′ 착취자
  학습이 끝나면 바로 이어서 시작해도 됨** (평가는 CPU 라 GPU 와 충돌 없음).

## 2단계 — E7-c (pin 후보 80afb2a)

- 4 조건 (cond_idx 순서: P1_armed τ0.85·post_shot / P1_inert τ0.85·inert / P2_armed τ1.0 θ1.5·
  post_shot / P2_inert τ1.0 θ1.5·inert) × seed {0,1,2} = 12 run. 조건별 BC 신규 (E7-b 래퍼에
  limiter_roe/limiter_inert 추가), arm C-① 레시피 r4p + 증류, 1.1e8, mu 0.35 nu 1.0 aim cv.
- 착취자 **두 종류** (run 당 2개): det 상대 `judge_exploiter/` (jseed 279000 + cond_idx·1000 +
  seed) + **sto 상대 `judge_exploiter_sto/`** (`--exploit-sto`, jseed **283000 + cond_idx·1000 +
  seed**). 둘 다 1e7, 조건 플래그 동일.
- 출력 `/data/hjhong/fs1jax/e7c/<cond>/s<seed>/`. 발사 전 pin 확정 보고 (80afb2a 또는 후속).

## 함정 (불변)

양성 주장 금지 · server4 GPU 1장만 · git 은 newURP-jax 만 · jseed 대역 혼동 금지 (279000 det /
281000 E7-b′ sto / 283000 E7-c sto) · 첫 slot 정상 확인 후 sweep.
