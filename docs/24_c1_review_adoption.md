# 24 — C-1 프로브 3자 리뷰 채택표 (2026-07-19)

> 리뷰 판정 = **조건부 승인**(연구 설계 통과 · 구현 사전검증 조건부). 접수본 = 세션 리뷰(docs/09 (ttt) 인용). 아래 12항 전부 처분 — 실행-전 필수 8 + 실행중/직후 보강. 코드 = `c1_corridor_probe.py` v0.2, 테스트 = `test_c1_corridor.py`(20 green, 2 env-integration 포함).

## 실행 전 필수 (8)

| # | 리뷰 지적 | 처분 | 코드/테스트 |
|---|---|---|---|
| 1 | finisher motion control scope 불명확 | **채택(정정형)**: 이 env의 finisher는 **고정 런처**(finisher_a_max=1.0·env가 a=0 명령 → translation 부재 = S1 설계). 단 **pointing(net cone n_F)은 v_soft에 진입**(se3_cone). 기존 guard는 axis=[0,0,0](수동 hold)로 이 DOF를 방치 → **default finisher = point_at_attacker**(obs 유래 net 조준)로 개방. "full defender control" = {limiter accel ×4, finisher pointing, guard fire}. **translation 부재는 음성 결과와 함께 명시하는 scope 한계**(물리 불가와 구분). | `make_finisher_fn(mode=point_at_attacker\|hold)`; `test_finisher_pointing_and_hold`·`_lead` |
| 2 | shell reach ≠ actual capture 성공 정의 혼재 (문서 verdict vs CEM 조기종료) | **채택**: rollout당 4단 verdict **SHELL_REACHED / GUARD_FIRED / LOCAL_CAPTURE / MISSION_CAPTURE**; 1차 구성적 증명 = SHELL_REACHED, CEM 조기종료도 SHELL_REACHED에서(capture는 상위 보너스). 잠금 3조건: reset-noneligible ∧ penetration-전 ∧ **같은 timestep에 v_soft≥θ ∧ p_feas>0**. | rollout rec 4필드; CEM `early_stop_reason`; `test_integration_verdict_tiers_are_nested`·same-timestep = `elig_now` |
| 3 | seed namespace 충돌(CEM 330000+draw = corral 331000 @ draw1000) | **채택**: 넓은 base 분리 CEM 330_000_000 / corral 331_000_000 / robust 332_000_000 + 구조적 인코더 `cem_seed(reset_idx, restart)=BASE+idx*10_000+restart` + **budget assert**(max < corral base). | `cem_seed`; `test_c1_rng_namespaces_structurally_disjoint`·`test_cem_seed_stride_guard` |
| 4 | "63-d obs = Markov-complete" 미증명 | **채택(철회+대체)**: 문구 철회. 2-tier 재현성 = **tier1 seed+action exact replay**(결정론) + **tier2 pre-commit reset_to 복원**(limiter p/v+att p/v·finisher/FSM fresh = A-3e (kkk) 계약; attacker pre-commit memoryless라 유효, post-commit 비적용 assert). 스모크 실측 **tier1 err 0.0 · tier2 err 0.0 / 13스텝**. | `snapshot_restore_check`; `test_integration_...restore` |
| 5 | CEM 288차원 raw = solver 실패와 물리 실패 미분리 | **채택**: knot 파라미터화(K knots piecewise-constant → t_open 확장, dim K×12; 기본 K=5=60) + corral warm-start(`_fit_knots`) + 계층(저차원 → near-shell만 full refine). | `knots_to_seq`·`_fit_knots`·`cem_optimise(knots=)`; `test_knots_expand_and_fit` |
| 6 | score() reward gaming(penetration만 막아도 가점; boxed v_soft=1) | **채택**: **lexicographic** capture > shell-eligible > joint-margin > eligible-dwell > delay/non-pen > −effort; `_TIER` 분리로 하위가 상위 역전 불가. boxed 과압축 < 임의 clean eligible 잠금. | `score_vector`/`score`; `test_score_lexicographic_ordering`(capture>shell>boxed·clean>boxed·deep>shallow·delay) |
| 7 | 같은-timestep·penetration-전 eligibility 미잠금 | **채택**: `elig_now` = 같은 스텝 v_soft≥θ ∧ p_feas>0(유한성 포함); SHELL_REACHED = ¬reset_elig ∧ first_elig < pen_at. | integration test 검증 |
| 8 | CEM winner replay 미검(반환 best_acts가 실제 승자인지) | **채택**: best = argmax **score_vector**(반환 knots=승자); CEM 스테이지가 best_acts replay 후 `replay_shell_reached` 기록. | `test_cem_deterministic_and_winner_is_returned`(replay 재현) |

## 실행 중/직후 보강 (채택)

| 리뷰 | 처분 |
|---|---|
| E1/E2/E3 claim 범위(회랑 1개 ≠ mission solvable) | **채택**: 성공 표현 = "적어도 하나의 nominal init에서 nominal-to-shell 연결성 구성적 확인"(E1). E2 = corral 최고 config fresh band(robust 스테이지), E3 = perturbation basin. docstring·docs/23에 명문화. |
| max_clean_v_soft 명칭·단일 계측 | **채택**: `M_v_given_pfeas`(개명) + `M_p_given_vsoft` + scale-정규화 `M_joint`(s_v=0.1, s_p=0.01) 3값 동시 기록 + single-frame vs sustained(연속 ≥2) 구분 + eligible_dwell. p_feas 단일표본 exploit 대응 = raw max_p_feas 저장 + robust R1 exact-replay·R2 fresh 재평가. |
| sampler bound test 일부만 | **채택**: 전 파라미터 + R1≤R0 + finite 잠금. |
| slot introspection(closure-cell 오탐) | **채택**: `fn.state` 노출, 테스트가 재할당 감지. |
| guard boundary(==θ, NaN/Inf) | **채택**: `test_guard_boundary` 6케이스. |
| robust R1–R4 | **채택**: R1 exact replay · R2 local basin(action noise) · R3 attacker-speed 변주 · **R4 feedback realizability**(obs-only PD가 기록 reference 추종 시 shell-reach 유지 = curriculum 재료 basin). |
| 실제 env 경로 regression | **채택**: 2 integration test(determinism·guard 일관성·restore 2-tier·verdict nesting), 1–2 ep 경량. |

## 미채택/유보

- 없음(전 항 채택). finisher **translation** 최적화만 이 env에서 구조적으로 불가(S1) → "pointing 개방 + translation 부재 명시"로 등가 처리. 향후 6-DOF 백엔드(project_warsim_state_sitl) 승격 시 translation DOF 재검토.

## 남은 캐비앗(정직)

- CEM knot=5·piecewise-constant는 여전히 근사 — near-shell 미도달 시 full-seq refine(CEM-3) 또는 spline/basis 확장이 다음 수(리뷰 SS6 계층 마지막 단). "NOT FOUND"는 항상 solver 계층 명시와 함께.
- point_at_attacker는 obs-유래 heuristic(리드 0 기본) — 최적 pointing 아님. pointing까지 CEM에 넣는 건 후속(현재는 개방 자체가 목적).
- 서버 실런 전까지 전 결과 = discovery. 양성 신호(E1) 후에만 confirmation(seed 확장·held-out) 설계.
