# 14 — A-3b 외부 감사 브리프: 학습에 영향을 주는 전 요인 (2026-07-15)

> 용도: 제3자 감독(리포지토리 접근 없음)에게 그대로 전달 — "우리가 간과했지만 문제가 될 수 있는 것"을 지적받기 위한 자기신고서. 모든 수치 인라인. 관련 로그: docs/09 (y)~(gg), 설계: docs/11·12·13.

## 0. 한 문단 컨텍스트

협력 방공 시나리오(코리도): **리미터 4**(저가 자폭 kamikaze, kill_radius 2.0m) + **피니셔 1**(비파괴 그물, 탄수 K=1, 비가역) vs **스크립트 회피 공격자 1**. MARL(MAPPO+blended counterfactual credit)은 베이스라인 대비 우월성 검증을 통과(paired held-out, margin 하한 +10~+16). 남은 벽 = **clean 포획**(발사가치 임계 돌파 ∧ 비포위)이 모든 시도에서 held-out 0회. 원인 규명 캠페인(A-1→A-2→A-3) 끝에 **A-3b**: 실측된 robust clean 상태에서 스폰해 말단 행동부터 후진 학습. 이 브리프는 A-3b 파일럿(3-seed) 직전의 전 요인 목록이다.

## 1. 판정 계약 (전 시도 공통·불변)

- **환경 상수(frozen)**: dt 0.05s, episode_len 80, τ_deploy 0.4s, τ_lock 0.1s, 공격자 명목 속도 20m/s(가족 랜덤화 16~24), kill_radius 2.0m, net_radius 2.0m, se3_cone 판정(half_angle 0.067 rad ≈ 3.8°, range_max 29.847m), viability = 도달집합 union(n_segments 4, n_samples 2000, 스텝별 CRN seed = ep_seed·100003+step).
- **술어**: v_soft = 도달집합 중 그물 원뿔 통과 분율(soft), worst = 최악점 지표, o = p_feasible(전개 가능 방향 분율), boxed ≔ (o==0), **clean ≔ v_soft ≥ θ_fire(0.9) ∧ ¬boxed**, capture(판정) = 발사 시점 ¬boxed ∧ worst ≥ 1.0 (**커밋 시점 동결 worst-case — 궤적 결과 아님**).
- **판정 보상 J** (학습·평가 동일; A-3b는 보상 스캐폴드 0): J = 1.0·headline_M3 + 0.3·r_geo_step + 1.0·r_geo_fire + 1.0·1[clean] + 5.0·1[captured] − 1.0·wasted − 0.5·limiter_loss. headline_M3 = v_eff(full) − v_eff(hold-배치), v_eff = v_soft·1[¬boxed] (hard), r_geo = v_soft·exp(−(ln o − ln 1e-3)²/2), 클리핑 전무(signed).
- **게이트**: 파일럿 중간 게이트(사전등록) = R0 통과 ≥2/3 seed ∧ R2 도달 ≥1, or frozen-heldout(77M CRN, 200판/seed) clean 비영 ≥1 seed. 본선 Gate A = clean_cross rate의 seed-군집 bootstrap 95% 하한 > 0, Gate B = capture 존재.

## 2. 실측된 벽의 지형 (이 캠페인이 확정한 것)

1. **공간 면도날**: frozen 폭에서 clean 창 반경 방향 폭 0.05~0.2m, 무작위 도달확률 ~1e-3 (수치 프로브, 리파인 포함).
2. **콘-폭 절벽**: 정책이 half_angle 0.150에선 clean 1.0 완벽, 0.134에서 clean·발사 동시 0 (정적 폭 + 적응 시간 부여에도; 시간-램프/폭-사다리 공통). 발사-EV 수리(wasted 패널티 0.3 완화 + 발사 보너스 1.5×)로도 불변.
3. **CRN-표본 면도날 (최신 발견)**: 동일 기하가 union 표본(seed)에 따라 clean↔비clean 요동. P4 witness 4본의 fresh-seed clean 빈도 = 8/8, 4/8, 3/8, 1/8. → EV(clean 시도)는 (공간 명중률)×(표본 강건성)으로 **이중 할인** — 전 시도의 무발사 수렴은 학습된 합리성.
4. **robust-clean 실존 + 로컬 도달 가능**: E_seeds[clean] 목적 리파인먼트로 취약 witness 0.50→1.00, 0.38→0.90 (검증 seed 서로소). bank 3본(robust 0.9~1.0) 확보.
5. **수동 평형**: 발사 없이 침투 100% 저지하는 차단 정책의 판정 보상(−1.5)이 방관(≈0)보다 낮음 — J에 침투 비용 항 부재. (S-6 "교전/침투 비용" 폴백으로 등재만, A-3b 미포함.)

## 3. A-3b 학습 파이프라인 — 가동 요인 전수

### 3.1 스폰 시스템 (유일한 스캐폴드)
- bank 3본: (x,v) = (12,16), (16,20), (20,24); 각각 리미터 4 절대좌표 + 공격자 [x,0,0], 속도 [−v,0,0]; 피니셔는 항상 자기 명목 자세(apex [2,0,0], 축 [1,0,0]) — **불가침**.
- 시작 시 R-8 게이트: frozen 환경 재계산으로 robust_clean_frac ≥ 0.9 (fresh seed 10개) 미달 witness 드롭, 전멸 시 중단.
- **상태만 주입**: 공격자 v_nominal·스크립트 컨트롤러·가족 랜덤화 파라미터는 불변. ⚠ 따라서 가족 draw(att_speed 16~24)와 스폰 속도(witness v±2%)가 불일치하면 공격자가 스폰 직후 명목 속도로 가감속 — 스폰 순간 viability는 witness와 일치하나 이후 궤적은 draw 의존.
- 리미터 스폰 속도 = 0 (witness는 위치만 정의).
- obs 정규화(RunningNorm)가 privileged 스폰 분포로 초기화 — R6(nominal) 전이 시 분포 drift.

### 3.2 커리큘럼 (R-사다리)
- R0: σ=0 (bank 3본 그대로; 스폰-clean ≈ 0.9~1.0), exit = train-eval clean ≥ 0.45 지속 2-eval. **표현 가설 테스트의 본체.**
- R1: σ_pos 0.02m (스폰-clean 실측 0.27~0.42), exit 0.17 ≈ 0.5×베이스라인.
- R2: 0.05 (베이스라인 0.08~0.12), exit 0.10 (floor = eval 20판의 2판 해상도).
- R3: 0.10 (베이스라인 0.01~0.09), exit 0.10 — **베이스라인 초과 요구 = 여기서부터 "스폰 운"이 아니라 능동 셰이핑이 필요.**
- R4: 0.20 + 공격자 후진 5m (베이스라인 ≈0), exit 0.10. R5: 0.50 + 후진 15m, exit 0.10. R6: nominal 스폰, exit = frozen-heldout clean 최근-3 비영.
- 기계: 전진 = exit 충족 2-eval 연속, 백오프 = 비충족 stall 3-eval(k>0), 예산 cap 300k 도달 시 동결(stall 스테이지 = 증거). eval 케이던스 20,480 스텝.
- 게이팅 평가: train-eval 번들만 현 스테이지 스폰(결정론 draw, seed 424243+r·991+ep) 사용; frozen 번들·heldout은 스폰 경로 자체가 없음(소스-lock 테스트).

### 3.3 보상·크레딧
- 학습 보상 = §1의 판정 J 그대로 (A-2와 달리 graded λ1·λ2 완화 등 전부 제거).
- 리미터 크레딧 = blended: 0.5·공유 J + 0.5·per-limiter hold-counterfactual(coma_D, 해석적). ⚠ 스폰 상태에서 hold-counterfactual의 기준(명목 초기 위치)이 멀리 있어 coma_D 스케일이 명목 대비 커질 수 있음.
- headline의 hold-배치 기준도 동일 이슈(v_eff(hold)가 스폰 기하에선 거의 0 → headline ≈ v_eff(full)).

### 3.4 정책·최적화
- MAPPO(CTDE), 중앙 critic 입력 = 공유 obs 63차원. 액터: 리미터 공유정책(one-hot) 가속 3+압력, 피니셔 축 3+슬루+**발사 = Bernoulli 헤드**(초기 로짓 0 → p≈0.5 — R0 초기 탐색에 유리). hidden 128×128, ortho init, value-norm, obs RunningNorm.
- recipe-v2: lr 3e-4 linear anneal(floor 0.1), γ 0.99, λ 0.95, clip 0.2, target_kl 0.02, epochs 10, minibatch 256, rollout 1024, ent_coef 리미터 0.0/피니셔 0.003, coma_γ/λ 0.99/0.95. 총 450k 스텝, scratch(웜스타트 없음 — A-3에서 warm=scratch 동일 실패 + 습관 상속 회피), 3-seed.
- ⚠ 스폰이 말단 근방이라 에피소드가 매우 짧아짐(수~수십 스텝) → rollout 1024 내 에피소드 수 급증, GAE가 에피소드 경계를 자주 넘음(표준 처리이나 value 학습 분포가 명목 대비 이질적).

### 3.5 공격자
- 스크립트 반응형: 목표 지향 + 측면 회피 + kamikaze 반발(margin 1.0m) + 커밋 관측 시 회피 증폭 1.8, ω_max 8. 학습 시 가족 랜덤화(att_speed 16~24, start_x 20~28 — 스폰 시 무효, ω 8~12, adv_a_max 21~30), 평가는 명목.
- self-play/최적 회피자 없음(exploiter probe는 게이트 후 예약) — "이 공격자에 대한" 결과임.

### 3.6 평가·선택·재현성
- best-ckpt 선택 = frozen 번들 sel_score(clean + 0.5·cap − 0.5·boxed_fire − 0.2·dwell)의 최근-3 이동평균. ⚠ **R0~R5 동안 frozen 성과가 0에 머물면 best-ckpt가 사다리 진전을 반영하지 못함** — heldout(중간 게이트 (iii))은 best-ckpt로 평가되므로, R-사다리에서만 유능한 정책은 (iii)에 불리. (i)(ii)는 train-eval 기반이라 무관.
- 재현성: CPU 결정론만 보장(CUDA 비결정), REQUIRED_COMMIT 가드, 결정론 스폰 draw. heldout CRN 77M+i는 학습 seed와 서로소.

## 4. 자가 식별 리스크 (우선순위 순)

1. **R5→R6 리미터-스폰 갭**: R-사다리는 공격자만 후진(최대 15m)시키고 **리미터는 witness 패턴 근방(σ≤0.5m)에 고정** — R6(nominal)의 리미터 초기 위치는 링(중심 [8,0,0], 반경 5m)으로 전혀 다름. 공격자 분포는 연결되지만 리미터 분포는 한 번에 점프. R6 전이 실패의 최유력 후보.
2. **best-ckpt 선택 vs 사다리 진전 불일치** (§3.6) — 중간 게이트 (iii)에만 영향.
3. **가족 draw–스폰 속도 불일치** (§3.1) — R0~R2에서 공격자가 즉시 가감속하며 witness 기하 이탈. 발사가 스텝 1~2에 일어나면 무해하나, 학습 초기(발사 못 배움)엔 상태가 빠르게 면도날 밖으로.
4. **짧은 에피소드의 최적화 부작용** (§3.4).
5. **coma_D/headline의 기준-배치 의미 변화** (§3.3) — 크레딧 스케일 왜곡 가능.
6. **판정 자체의 표본 면도날**: Gate A는 clean "발생률"을 요구하는데 clean 술어가 CRN 표본에 민감 — robust-clean 관점에서 게이트 정의 재고 여지(단 게이트는 캠페인 불변 계약).
7. σ_vel이 R0에서 0 → 3본 고정 스폰의 극단적 저다양성(의도된 암기 단계이나 과적합 후 R1 전이 마찰 가능).

## 5. 감독자에게 요청하는 검토 질문

1. R0가 "행동 표현 가설"(즉시 발사를 배울 수 있는가)을 정말 순수하게 테스트하는가? 남은 혼입 요인은?
2. 리스크 1(R6 리미터 갭)은 치명적인가? 중간 스테이지(리미터 위치를 witness→링으로 보간)를 지금 넣어야 하나, 아니면 파일럿 증거를 기다리나?
3. exit 문턱(베이스라인×0.5, floor 0.10)의 통계적 함정은? (eval 20판, 지속 2-eval 규칙 포함)
4. 사다리 백오프-오실레이션(A-2에서 관측)이 A-3b에서 재현될 조건은? cap 300k 예산은 7-스테이지에 충분한가(최소 소요 ≈ 287k)?
5. 보상 J를 스캐폴드 없이 쓰는 결정(교란 제거)과, 알려진 J 결함(침투 비용 부재·binary λ1)의 긴장 — A-3b 맥락에서 후자가 다시 물 수 있는 경로는?
6. blended credit(0.5)·value-norm·짧은 에피소드의 조합에서 예상되는 학습 병리는?
7. 이 목록에 **없는** 것 중, 이런 류의 "실측 상태 후진 커리큘럼"이 통상 실패하는 알려진 원인은? (예: 상태 주입과 시뮬레이터 내부 상태의 불일치, 정규화 통계, 종결 조건 등)
