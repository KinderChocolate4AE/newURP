# Dead code / Zombie experiment / Unreachable branch 감사 (Task 3)

**2026-08-08.** 등록부: `artifacts/audits/code_liveness_registry.tsv` (스크립트
134 + 모듈 + config-flag). 방법: 참조 그래프 전수 스캔(에이전트 3종: liveness ·
config 도달성 · duplicate) + 본 세션의 현행-체인 교정.

---

## 1. SAFE_DELETE — **0건 (삭제 없음)**

전수 스캔에서 완전 무참조(ZERO-REF)는 **3건**뿐이었고, 셋 다 SAFE_DELETE
10조건을 통과하지 못한다:

| 파일 | 탈락 조건 |
|---|---|
| `c1_moveA0_plot.py` | 조건 5·6·10 — 참조되는 probe(`c1_moveA0_probe`)의 그림 생성기로 추정. 산출 그림이 docs 에 들어갔는지(=유일 재현 스크립트인지) 정적 탐색으로 확증 불가 |
| `c1_persistence_plot.py` | 동일 (`c1_persistence` 는 tests 가 지키는 LIVE probe) |
| `n1_temporal_plot.py` | 동일 (`n1_temporal` 은 docs/09·a1 참조) |

규율 §7 ("import 0 → 삭제 가능" 추론 금지, "현재 실행 안 됨 → 쓸모없음" 금지)
에 따라 셋 다 **UNCERTAIN — 삭제 금지**. 재분류 경로: 다음 세션에서 각 plot
스크립트의 출력 파일명을 docs/figures·results 와 대조해 (a) 그림 원천이면
ARCHIVE_ONLY 승격, (b) 어디에도 산출물이 없으면 그때 SAFE_DELETE.

**따라서 이번 세션의 코드 삭제·삭제 커밋은 없다.** pytest 는 감사 시작
provenance 로 1회 실행 (508 passed / 1 failed(로컬 cp949 산물) / 61 skipped
(torch 부재)) — 삭제가 없으므로 후행 재실행 불요.

## 2. ARCHIVE_ONLY (삭제 금지 — 증거 재현)

- **v2/v3 직전 사슬 완료 감사 10종**: boxed_arm_audit · contact_exact_audit ·
  pk_sweep_audit · handoff_audit · coupling_gate(P84) · contact_reachability ·
  coverage_oracle · selective_snapshot_oracle · witness_margin_audit ·
  temporal_support — docs/52~58 의 수치 원천.
- **C1 캠페인 클러스터 ~49종** (`c1_*`): 상호 import 폐쇄 성분(테스트·러너
  미도달)이지만 docs/09·23~25 결과 사슬. 예외 3종은 LIVE (corridor_probe ·
  g3_deploy · persistence — tests 가 지킴).
- **A/A3 캠페인 종료분**: a2_fire_mode_diagnosis · a3b_fire_oracle ·
  a3c_recoverability_oracle · a3d_null_baseline · a3d_v16_refine ·
  a3d_witness_freeze · a3e_harvest · a3e_hybrid_eval · a3e_nominal_probe ·
  analyze_gate_a · train_ppo_toy · spike_throughput · p4_* · n1_temporal ·
  oracle_capture · rho_v_band.
- **configs**: l2_coma*.yaml (COMA 2D 재현 — coma_mix>0 의 유일 산지) ·
  m3a_*.yaml · l2_ippo.yaml · ppo_toy.yaml.

## 3. LIVE (교정 포함)

핵심 모듈 전부(env/env_sys/viability/fsm/m4_*/train/* 등 — registry 참조)에
더해, **탐색 에이전트가 약참조로 오분류한 현행 체인 4종을 LIVE 로 교정**했다:

- `threat_v3_gates.py` (P87~P94 러너 — docs 가 게이트 ID 로만 참조해 grep 누락)
- `scale_v2_baseline.py` (V4) · `scale_v3_baseline.py` (V6)
- `dump_trajectory.py` (V7 뷰어 덤프)

또한 tests 가 지키는 a3d/a3e/c1 일부(레거시지만 회귀 대상)는 LIVE 로 남는다 —
"연구선 종료 ≠ dead code" 원칙.

## 4. UNCERTAIN — §1 의 plot 3종 (삭제 금지)

## 5. Zombie config flags (선언됐지만 안 읽힘)

| 항목 | 실태 | 비고 |
|---|---|---|
| `viability.turn_limited` (+`sampler.n_azimuth`/`turn_safety`) | roles 파싱 후 env 경로 소비자 0 (tests 만) | params RESERVED 등재와 일치 |
| `env.capture_thresh` / `omega_att_max=8.0` | 미독 | params DEAD 등재와 일치 |
| ★ `scripted.limiter_pressure` (params.py:276 "env ignores idx3") | **서술이 낡아 위험** — M4 는 idx3 을 커밋 비트로 재사용, baselines 는 1.0 을 쓰고 `_zero_commit`(mission_rollout:142) 만이 전 기저선의 스텝1 전원커밋을 막는다 | 레지스트리 재분류 필요 (다음 세션) |
| `scripted.finisher_slew_cmd` | unpad 가 폐기 — 진짜 inert | |
| `LimiterSpec.loss_cost` · `FinisherSpec.e_net` · `ScenarioSpec.n_adversaries` · `headline_u0`/`coma_u0` · `ViabilitySpec.seed` | 독자 0. 특히 `attitude.e_net_init` 레지스트리 값 변경은 **조용히 무효** (make_env.py:109 하드코딩) | params.py:144/184-187 의 소비자 서술 3건이 오기 |
| `FireGate.B_capture`/`c_fire` | 자기일관 assert 전용 | |
| `m4_config.SWEEP_AXES`/`PENDING` | 런타임 소비자 0 (문서·테스트 전용) | 의도된 prose-as-code |
| `M4_OVERRIDES["train.layout.x_fire"]=16` | fire_mode="x_fire" 전용 — 프로덕션 미사용 | docs/59 기 인지 |
| l2_mappo.yaml `randomize:` 블록 + `env_config:` | **M4 러너가 조용히 무시** (rand_cfg=None, m4_config() 사용) | 2C 경로에서만 유효 |
| A3 `bait_*` 필드 · `SpawnSpec.psi`/`speed_frac` · `randomized_config` | 프로덕션 setter/호출자 0 (선언 축으로 보존) | DORMANT |

## 6. Unreachable branches (코드는 있지만 산지가 없음)

- `fire_mode="x_fire"` (mission_rollout:219) — CLI `--fire` 와 tests 만.
  **"learned" 라는 fire_mode 는 존재하지 않는다** (learned 발사 = policy 경유,
  fire_mode 무시).
- `limiter_mode "brake"/"lam20"` (mission_rollout:178-182) — 산지 0.
  results JSON 의 brake/lam* 이름들은 **별개 표**(a3d_bankv2 Gate-B bank)의
  것 — 혼동 주의.
- `limiter_mode "ring"/"intercept"` — legacy 스윕 경로에서만 도달
  (spawn_sweep 기본값 ring, sweep_m4 intercept). 현 체인은 전부 hold.
- viability `attacker_turn_limited=True` — env·스크립트 산지 0 (tests 만).
  `_feasible_turn`·turn-curve 세그먼트는 env 에서 도달 불가.
- `judge="point_mass"` — dataclass 기본값이라 **직접 생성 시 조용히 ablation
  judge 가 되는 잠재 트랩** (YAML 은 전부 se3_cone; 의도 사용은
  fire_gate_calibration 뿐).

## 7. ★ 예상 밖 legacy-live paths (가장 중요)

1. **학습기·평가기가 구계약으로 돈다** — `train_m4.build_specs` 는
   `contact_resolver`/`miss_terminates` 를 전달하지 않고(→ R1/R2 off),
   `sweep_m4.measure_baseline` 도 bare `SystemSpec()`. 반면 현행 baseline
   체인(scale_v2/v3, threat_v3_gates, dump_trajectory)은 전부 명시적으로
   `contact_resolver=True, miss_terminates=False`. **학습/legacy-스윕 계열과
   v2/v3 측정 계열은 서로 다른 계약 위에 있다** (Task 2 blocker 1 과 동일
   발견의 config-측 확인).
2. **`mission_eval` 이 `standby`/`extra_cfg` 를 build_m4_env 에 전달하지
   않는다** (m4_env.py:123-125) — 평가 경로는 V3-FULL 을 평가할 수 없고
   v3 attacker 를 줘도 조용히 legacy 기하로 돈다.
3. **`n_segments=1` legacy 낙관 신호가 아직 살아 있는 유일한 곳 =
   rollout_gif + m2_default.yaml** (episode_len 70 · theta 0.8 플롯 포함).
   렌더 전용 루트라 실험 오염은 없으나, GIF 를 증거처럼 읽으면 안 된다.
4. **rollout_gif 는 스크립트 규칙을 인라인 복제하며 `_zero_commit` 을 안
   쓴다** — M2 env 에선 idx3 이 무시돼 무해하지만, M4 스택에 재사용하는 순간
   스텝 1 전원 하드킬 커밋이 된다. 재사용 금지 트랩으로 등재.
5. `train_m4.py:125` — `"hold" if limiter_policy == "hold" else "hold"`
   동어반복: `--limiter-policy` 는 hold 외 스크립트 편대를 선택할 수 없다.
6. **docs/61 TRAIN 분포는 100% 미배선** — `v3_train`/`episode_len_train=1100`
   grep 히트 0 (P92 대기와 일치; "배선됐다" 로 착각 금지).

## 8. DUPLICATE_REFACTOR_CANDIDATE (보고만 — 이번 세션 통합 금지)

blast-radius 순 (상세 file:line 은 duplicate 에이전트 결과 — 아래 요약):

1. **스크립트 기저선 규칙 인라인 복제 6곳** (rollout_gif · channel_split ·
   signal_audit · scale_smoke · slew_audit · oracle_capture) — docs/48 §3.1
   "한 곳 원칙" 의 위반 사례군. rollout_gif(_zero_commit 누락)와
   scale_smoke(ring 모드 발산 주석)는 이미 실제 발산 1건씩 보유.
2. **hand-rolled rollout 루프 17개 스크립트** (mission_rollout.run_episode
   미사용) — 그중 4곳은 underscore-private(`_limiter_actions`/`_zero_commit`)
   을 import (channel_split · slew_audit · signal_audit · scale_smoke).
3. **라벨 재구현 4곳 의미 상이**: recoverability_probe(contact 분리 없음) ·
   threat_v3_gates("OTHER") · signal_audit(NET_CAPTURE 가 contact 미검사 —
   정본과 이름 충돌·의미 상이) · scale_smoke(m4_outcome 경유). "성공" 집합도
   2종 (mobility_factorial vs signal_audit — HARD_KILL 포함 여부 상이).
4. **M4 kwargs 번들 ~18곳 복제** (+tests 6곳); contact_exact_audit 는 다른
   스크립트의 `_kw` 를 import — 공유 상수 부재의 증상.
5. SHA-256 유도 4변형 (spawn_rand 정본 / attacker_ladder / m4_config —
   해시 키에 i 미사용 / env_sys — episode 필드 없음·의도된 상이 아키텍처).
6. Wilson 은 통합 완료 — 잔여는 curve_sweep 의 이름 shadow 와
   phi_potential 경유 우회 import 3곳.

## 9. 실제 삭제한 파일 — **없음**

## 10. 삭제 후 테스트 — 해당 없음 (삭제 0건). Provenance pytest = 508 passed /
1 failed (로컬 cp949 산물, 알려짐) / 61 skipped (torch 부재).

---

*규율 준수: SAFE_DELETE 판정 0건 → 코드 변경 0. duplicate 는 보고만.*
