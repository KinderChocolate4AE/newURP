# HANDOFF — main → JAX 세션: E10 발사 게이트 학습 방어 (2026-11-19)

> JAX 세션이 아니면 "JAX 아님" 만 회신.

**E10 봉인 완료** (`docs/146`, manifest `aadc712e38a8199e`, `scripts/fs1_e10_manifest.py`) + **정본 게이트 랜딩 완료** (봉인 커밋 참조).
생산은 **parity green + GPU 확보 (사용자가 랩에 확인 중) 후**에만. 지금 할 일은 1–3 (GPU 불필요).

## 정본 랜딩 요지 (미러 대상)

- `FS1Spec.fire_gate: str = "off"` (기본 = 현행과 비트 동일) / `"robust"` (`shepherd/fs1/world.py`).
- `"robust"` 두 가지 동작:
  1. **env 게이트** (`shepherd/env.py`, FSM 직전): LOADED 에서 발사 요청이 와도 **포획 술어** (`v_shot_worst >= 1 and not boxed_in` — fire_event 에서
     `_pending_capture` 를 정하는 술어와 동일) 가 참인 tick 에만 통과. 막힌 요청 = FSM 의 gate-blocked 경로 (탄·wasted·상태 무변화, `c_fire` 미부과).
     lean 모드는 LOADED ∧ FIRE 요청 tick 에 판정을 계산한다 → **게이트 아래에서는 16 m 안 매 tick 판정 호출**.
  2. **FCS** (`world.fcs()`): r_fire 행동을 **무시**하고 arm ∧ LOADED ∧ d ≤ `r_fire_range[1]` (16 m) 이면 항상 요청. 게이트 없는 세계는 불변.
- 테스트 `tests/test_fs1_e10_gate.py` (9 종): 기본값 no-op · 차단 무소모 · 통과 발사 = 포획 술어 참 · r_fire 무시 · 라벨 의미.
- 정본 eval: `--fire-gate robust`. `rob_fire` 는 기존대로 기록 (게이트 위반 검사용 — 발사했는데 false 면 무효).

## 작업 (worktree `newURP-jax`)

0. **merge**: 정본이 한 달 이상 앞서 있다 (E9 프로브·E10 게이트). main → newURP-jax merge 후 기존 parity 스위트 green 확인.
1. **미러 + parity**: 기본값 (off) golden 비트 동일 유지 + **게이트 on spot-check** — 같은 행동열에서 정본과 (a) 발사 tick, (b) 막힌 tick 수,
   (c) 포획 결과가 일치 (f64). McNemar 절차는 기존대로.
2. **처리량 smoke**: 게이트 on 에서 학습 steps/s 를 게이트 off 와 비교해 보고 (판정이 발사 tick 1 회 → 16 m 안 매 tick). 생산 시간 추정에 쓴다.
3. **평가 재현성 preflight**: 아무 기존 slot 하나를 정본 eval 로 두 번 (`--env-seed 0`) 돌려 `episodes.jsonl` 동일 여부 보고
   (E9 에서 프로브가 torch 전역 RNG 미시드로 실행 간 재현 불가였음 — eval 경로 확인 필요).
4. *(GPU 확보 후)* **생산 15 slot**: manifest `points` 3 (τ scale 1.0 / 0.6667 / 0.5 — 전개 6 / 4 / 3 tick, smoke 에서 assert) × seed {40–44},
   cell m0.35_n1, **전 단계 fire_gate=robust** (BC 수집 · 동시학습 · 레드팀 · 평가). 레시피 = E8 과 동일 (새 BC 3000 eps → arm C-① 레시피 1.1e8).
5. **레드팀**: slot 당 det 1 개, 동결 방어 상대 **3e7**, **1e7·2e7 스냅샷 보관** (R1 의 b3_at1e7 / b3_at2e7 방식), jseed **335000 + idx·100 + seed**.
6. **보고**: pin · 산출 경로 · train-side (승률·NET 점유·감사 최종) · 처리량 → main 이 정본 평가 (seed0 380000 대역 — 학습 사용 금지) 와 판독.

## 함정 (불변)

양성 주장 금지 (판독은 main) · GPU 는 **타 사용자 점유 확인 후** 사용자 결재 받은 1 장만 (11-19 현재 server4·5·6 의 6 장 전부 타 사용자) ·
격리본 불사용 · git 은 newURP-jax 만 · 레시피·예산을 결과 보고 바꾸지 않는다 (바꿔야 하면 중단하고 main 에 보고).
