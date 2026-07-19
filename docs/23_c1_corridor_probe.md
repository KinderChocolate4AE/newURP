# 23 — C-1 nominal-to-shell 회랑 실존 프로브 (DISCOVERY, v0.2 2026-07-19)

> **성격**: 신규 개발축(docs/09 (qqq-1) 축1 · doctrine docs/22 v0.2 §0-1) 첫 실험의 **경량 사전등록**. A-캠페인 아님, 종결 실험 아님 — 다음 개발 수를 고르는 **분기 진단**이자 (성공 시) on-manifold 장궤적 생성기. 대형 사전등록(0-e급) 금지 원칙에 따라 이 1파일로 고정; 결과 판독 후에만 confirmation 설계.
>
> **v0.2**: 3자 리뷰(조건부 승인) 채택 — 채택표 = **docs/24**. 8대 필수 반영: full defender control(finisher pointing 개방) · 4단 verdict · E1/E2/E3 사다리 · knot-CEM · lexicographic score · 넓은 seed namespace · snapshot 2-tier · 측정 3값.

## 1. 질문
A2 폐루프 공격자 + 동결 판정 아래에서, **가용한 방어자 제어**(limiter accel ×4 + finisher net-pointing; fire = 자율 rule guard)가 **nominal reset을 penetration 전에 fire-eligible shell(v_soft ≥ θ ∧ p_feas > 0)로 연결**하는가?

**방어자 제어 범위(리뷰 §4)**: 이 env의 finisher는 **고정 런처**(configs `finisher_a_max=1.0` "effectively stationary", env가 a=0 명령) → **translation 부재는 S1 설계**. 단 finisher **pointing(net cone n_F)은 v_soft에 진입**(se3_cone) → 기존 guard의 axis=[0,0,0](수동 hold)은 도달성을 과소평가. 그래서 default finisher = **point_at_attacker**(net을 공격자에 조준, obs 유래). "full defender control" = {limiter accel ×4, finisher pointing, rule-guard fire}. **translation 부재는 음성 결과와 함께 명시하는 scope 한계 — 물리 불가와 구분.** (6-DOF 백엔드 승격 시 translation DOF 재검토.)

## 2. 증거 라벨 — 4단 verdict + E-사다리 (리뷰 §2·§3)
rollout당 중첩 verdict: **SHELL_REACHED**(reset-noneligible → penetration 전 eligible, 같은 timestep v_soft≥θ ∧ p_feas>0) → **GUARD_FIRED** → **LOCAL_CAPTURE**(발사 후 arrival capture) → **MISSION_CAPTURE**(env 종말 포획). **1차 구성적 증명 = SHELL_REACHED**, capture = 상위 보너스.

캠페인 claim 사다리: **E1 pointwise**(≥1 nominal seed에서 feasible) / **E2 family**(한 controller가 여러 fresh reset 성공) / **E3 robust**(perturbation 하 비영 basin). **회랑 1개 발견 = E1** — "적어도 하나의 nominal init에서 nominal-to-shell 연결성 구성적 확인"; **distribution-level solvability 아님.** fresh 반복 성공 시 E2로 승격.

비발견 = **NOT FOUND UNDER TESTED SOLVERS**(부재 증명 아님 — infeasibility certificate 없음) → task-design 민감도로 라우팅, 논문 종결 금지.

## 3. 고정(불변) · 넓은 seed 대장 (리뷰 §9)
- **고정**: 판정 J · 평가 경로 · θ · guard 술어 · dynamics · action bounds · nominal reset 분포. 학습 없음, sealed 미접촉.
- **seed(구조적 비충돌·budget assert·테스트 lock)**: reset **1100–1199**(search)/**1200–1299**(robust). rng = CEM `330_000_000 + reset_idx*10_000 + restart` · corral `331_000_000` · robust `332_000_000+`. (구 `330000+draw` = corral 331000 충돌 해소.) (qqq) 950–1049 · RT-2 212121 불가침.

## 4. 측정기 (리뷰 §5 — 3값 + 게이밍 차단)
매 스텝 (v_soft, p_feas) 기록. 3값 동시: **M_v_given_pfeas**(p_feas>0 스텝의 max v_soft, 구 max_clean_v_soft 개명) · **M_p_given_vsoft**(v_soft≥θ 스텝의 max p_feas) · **M_joint**(scale-정규화 `min((v_soft−θ)/s_v, p_feas/s_p)`, s_v=0.1·s_p=0.01, eligible일 때만). + single-frame vs sustained(연속 ≥2) 구분 + eligible_dwell + boxed_shell_steps. **boxed 과압축**(v_soft 1.0 / p_feas 0)은 스모크 실측 실패모드 — clean margin이 정본. score()=optimiser 유도 전용, verdict=SHELL_REACHED.

## 5. 단계 (`--stage`)
- **baseline**: zero/brake/lam20/attpd3[+`--learned`]. `--finisher point_at_attacker|hold`(ablation). 스모크 n4: 전 arm shell 0·M_v≈.218·boxed 0(=(qqq) 정합, 계기 정상).
- **corral**: scripted-corral 가족(ring4/wall3_chase1/press2_block2, R1≤R0) 랜덤서치 → screen → top-K. 스모크 24cfg: top **boxed 8–10 스텝**(shell 도달·과압축 = near-miss 포착, 발사 0 = 정당).
- **cem**: **knot 파라미터화**(K knots piecewise-constant → t_open, dim K×12) 개방루프 최적화, A2 폐루프 내부, corral warm-start(`_fit_knots`), **SHELL_REACHED 조기종료**(best = argmax score_vector = 반환 승자). 계층: 저차원 → near-shell만 full refine.
- **robust(리뷰 §11)**: R1 exact replay · R2 local basin(action noise) · R3 attacker-speed 변주 · **R4 feedback realizability**(obs-only PD가 기록 reference 추종 시 shell-reach 유지 = curriculum basin). corral 최고 config는 fresh band 1200–1299(E2).

## 6. 저장 + snapshot 2-tier (리뷰 §8 — "Markov-complete" 철회)
eligible/top rollout = full 63-d obs 열 + action + v_soft/p_feas + seed 아카이브. **재현성 2-tier**: **tier1** = seed+action exact replay(결정론, 스모크 err 0.0) / **tier2** = pre-commit **reset_to 복원**(limiter p/v + att p/v, finisher/FSM fresh = A-3e (kkk) 계약; attacker pre-commit memoryless라 유효, post-commit 비적용 assert; 스모크 err 0.0/13스텝). → 성공 궤적 = **정확한 on-manifold predecessor 생성기**(rewind harvest가 못 준 장궤적). "63-d obs = Markov-complete" 문구 철회.

## 7. 성공 시 다음 수 (리뷰 §7 · 권고안 §7)
E1 확인 → corridor clustering → family 구조 → privileged imitation → curriculum 초기상태를 회랑 위에 → teacher removal → nominal 분포 확장 → brake/heuristic 대비 learned 평가 → A3. (fresh 반복 성공이 E2, perturbation basin이 E3.)

## 8. 실패 시 다음 수 (리뷰 §8)
solver/horizon/action-bound/limiter-수/attacker-reaction/predicate/spawn-geometry 분리 → best M_joint 분석 → 민감도(θ 0.90→0.88→0.85 · R_net 2.0→2.4 · T 23→40)로 connectivity 여는 물리 축 탐색. 정확 표현: "강한 privileged search에서도 현 조건 회랑 미발견 — solver 한계와 물리 연속성 부족 분리 후 task-design 민감도로 전환." = engineering feedback, MARL 실패 아님.

## 9. MARL 연결 (권고안 §9)
프로브 = MARL 대체 아님, 전제 진단 + 데이터 생성. 회랑 발견 후 직접 물음: "단순 감쇠 controller가 이 회랑을 안정 추종/생성하는가?"(제4병목 재검정 무대 = longer-horizon·다중 회랑·역할 분화·A3).

## 10. 실행 원칙
Discovery: 1–3 초기조건군·다수 restart·dev-only·짧은 로그·신규 대역·핵심 판정만 고정·대형 사전등록 금지·양성 후에만 confirmation. 모든 보고 말미: **"이 결과가 nominal 포획 해결력을 무엇만큼 늘렸는가."**

## 11. 서버 런북
Windows `git reset`→push → 서버 pull → REQUIRED_COMMIT → torch-free pytest(`tests/test_c1_corridor.py`, 20 green) → 스모크 → 본 런: `--stage baseline`(+`--learned`) → `--stage corral --n-cfg 160 --top-k 5` → `--stage cem --draws 20 --knots 5 --warm-from results/c1_corridor/c1_corral.json` → `--stage robust`. TMPDIR=/data·ntfy·OMP 2·nice 10. 산출 = `results/c1_corridor/c1_{baseline,corral,cem,robust}.json`.
