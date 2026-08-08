# 71 — LS-COMMIT ABLATION 최종 폴백 블록 사전등록 r1 — 비준·동결

**2026-08-08 · 리뷰 9 (docs/70) 수정안 채택. LL 0/300 · LS(0.163) 관찰 후,
결과를 더 보기 전에 **2-arm 블록 전체 + 판정 + stop rule 을 한 번에
동결**한다 (arm-ladder 규율, docs/70 §4). 이 블록이 이 연구의 **마지막
learning-contract rescue** 다.
r0 → r1 = 조건부 비준의 필수 수정 4건 이행: ① ablation 전용 IID
10300..10599 신설 (기존 10000..10299 = 이미 열람된 표본 — primary 재사용
금지) ② seed0 = index seed 분리, primary confirmatory seeds = {1,2,3,4}
③ SHAPING label pre-treatment 코드 확정 ④ commit-off 의미 = head 부재 +
배선 스펙·잠금 테스트. "causal blocker" → **causal contributor** 하향.
**r1 = 비준·동결 — 구현 인가.****

★ 정직성 선언: 이 블록은 LS seed 0 의 commit 자폭 관찰에 의해 활성화된
post-failure design 이다. 폴백 자체(`limiter_commit=false` = "커밋을 정책
손에서 뗀 대조군")는 결과 전에 선언돼 있었다 (docs/29 §15.2 (b) + 학습기
config 주석). 활성화 시점이 결과 후라는 사실은 숨기지 않는다.

---

## 0.1 코드 확정 2건 (r1 — 비준 전 검증 완료)

- **③ SHAPING/FREE = pre-treatment ✓**: `regime_of(a_att, tau, net_radius)`
  (m4_env.py) 는 에피소드 위협 draw 만의 순함수 — controller·정책·궤적과
  무관하게 에피소드마다 고정이고, 같은 IID 판은 LS-live/LS-off 에서 동일
  라벨을 갖는다. Δ_shape primary 유효.
- **④ `limiter_commit=false` 의 실제 의미 (mappo.py:312-318)**: lim_actor 가
  `GaussianActor`(연속 3축)로 생성 — **commit head 자체가 부재** (Bernoulli
  log-prob·entropy 의 PPO 기여 = 구조적으로 0; 리뷰 경우 C 이상으로 깨끗).
  단 현 M4Runner 는 adapter 프로파일을 무조건 M4_LIVE_DIMS(commit live)로
  잡아 lim_dim=3 과 불일치 — **구현 스펙**: `cfg.limiter_commit=False` 시
  limiter live dims = (0,1,2) 프로파일로 전환, `pad_env_action` 이
  idx3(commit)=0 을 결정적으로 채움 (env 는 항상 commit 0 수신).
  잠금 테스트 4항 = §2.1.

## 1. 사전등록 원문 (리뷰어 초안 — 영문 고정)

> **LS-COMMIT ABLATION — final preregistered fallback block**
>
> Purpose: determine whether the live limiter-commit action is a causal
> blocker of access to cooperative-shaping behavior under the frozen MARL
> training contract. This analysis does not replace the original
> commit-live MARL headline result.
>
> Two arms are frozen before any additional training outcomes are
> observed:
>
> - **LS-live**: learned limiter policy with `limiter_commit=true`;
>   scripted finisher; otherwise unchanged frozen training contract.
>   Training seeds = {0,1,2,3,4}. The already completed seed-0 run is
>   retained without replacement.
> - **LS-off**: identical LS contract except `limiter_commit=false`.
>   Training seeds = {0,1,2,3,4}.
>
> No reward coefficient, entropy coefficient, rollout length, optimizer
> setting, policy architecture, threat distribution, scripted finisher,
> or evaluation protocol may differ between the two arms.
>
> All trained policies are evaluated on the same frozen paired ablation
> threat set (§1.1). The primary mechanistic endpoint is SHAPING-regime
> nondestructive net capture:
>
>     Δ_shape = p_net^{LS-off, SHAPING} − p_net^{LS-live, SHAPING}
>
> **Positive evidence** requires the preregistered seed-resampled 95%
> bootstrap confidence-interval lower bound (§1.2) for the mean paired
> effect to exceed zero. Overall IID net capture, total defense,
> FREE-regime performance, limiter survival, time-to-all-spent, and
> route-interaction statistics are reported as secondary or mechanistic
> diagnostics and cannot replace the primary criterion.
>
> If the primary criterion is not met, no further commit-entropy,
> limiter-cost, rollout-length, reward, or action-space rescue arm is
> run in this study. The result is reported as a failure of commit
> removal alone to recover measurable cooperative shaping under the
> frozen learning contract.
>
> If the criterion is met, the conclusion is limited to a causal
> action-space diagnosis: *disabling commit recovered SHAPING-regime
> capture performance relative to commit-live training, supporting
> commit availability as **a causal contributor** to the observed
> failure to express cooperative shaping under this training contract.*
> ("the causal blocker" 표현 금지 — rollout·Δv_shot·horizon 병존 가능.)
> The commit-disabled arm remains a secondary mechanistic ablation and
> does not retroactively replace the original commit-live headline MARL
> result. A claim of learned shepherding still requires the separately
> planned active/static mechanism-attribution analysis.

### 1.1 Confirmatory-status and evaluation separation (r1 patch — 원문 고정)

> This block is a prospectively preregistered post-failure mechanistic
> ablation, not a replacement primary MARL experiment.
>
> The original LS seed 0 is the index seed whose observed early commit
> collapse activated this ablation. Its LS-live and LS-off paired
> results are retained and reported as mechanistic/index-seed evidence
> but are excluded from the primary confirmatory confidence interval.
>
> The primary confirmatory training seeds are {1,2,3,4}.
>
> The original headline IID episodes 10000..10299 have already been
> inspected through the LS seed-0 evaluation and are not reused as the
> primary confirmatory dataset for this post-failure ablation.
>
> Before any LS-off outcome is observed, a disjoint ablation-IID set is
> frozen as **iid episodes 10300..10599 (n=300)**. No episode property,
> regime count, or outcome from this range may be inspected before the
> range is frozen. LS-live and LS-off policies are evaluated on exactly
> the same paired draws from this set.
>
> SHAPING/FREE membership must be controller-independent and fixed for
> each IID episode before rollout (§0.1 ③ 코드 확정).

### 1.2 Bootstrap 정의 (r1 — pooling 금지)

> For each confirmatory training seed s in {1,2,3,4}, the primary paired
> effect is d_s = p_net^{LS-off,SHAPING,s} − p_net^{LS-live,SHAPING,s}.
> The highest-level bootstrap resampling unit is the **training seed**;
> paired episode resampling may be nested within each resampled seed.
> Evaluation episodes are never pooled across seeds as independent
> algorithmic replications. All per-seed d_s are published as raw data.
> Because only four prospective confirmatory training seeds are
> available, this interval is treated as a **preregistered decision
> statistic** rather than a claim of precise population-level
> uncertainty.

## 2. 실행 계획 (r1)

- 신규 학습 = **9런**: LS-live seeds 1..4 (seed 0 = 기존 결과, index 로
  유지·미교체) + LS-off seeds 0..4. 서버 tmux + ntfy, CUBLAS 결정론.
- config: `configs/l2_mappo_nocommit.yaml` = l2_mappo.yaml 복사 +
  `mappo: limiter_commit: false` 한 줄 — **그 외 diff 0** (블록 계약).
- 배선 (④ 스펙): M4Runner — `cfg.limiter_commit=False` 시 limiter live
  dims (0,1,2) 프로파일 사용, pad 가 commit=0 결정 주입. 잠금 테스트 §2.1.
- 평가: 전 정책을 **ablation IID 10300..10599 (n=300) paired** 로 일괄
  평가 (러너는 headline 러너와 공용 구현 — headline 은 여전히
  10000..10299). primary CI = seeds {1..4}, seed0 쌍은 index 증거로 병기.
- 곡선 열람 규율: 모니터링만 — 중간 중단·재선택 금지. 전 런 완주 후 일괄.
- 진단 ①③④ (docs/70 §2) 병렬 가능 (기록용 — 블록 설계 소급 반영 금지).

### 2.1 LS-off 잠금 테스트 (구현과 같은 커밋에)

```
[ ] env 에 전달되는 limiter commit 성분 == 0 (전 스텝, 결정적)
[ ] commit log-prob 의 PPO objective 기여 == 0 (head 부재 구조 확인)
[ ] commit entropy 기여 == 0
[ ] 연속 3축 loss 경로 = LS-live 와 동일 (형상·클립·스케일)
```

## 3. 지위·서술 잠금

- **L-off ≠ 새 headline.** docs/63 headline (hold vs scripted vs
  commit-live MARL) 은 그대로 보고된다. L-off 성공 시 서술 =
  "preregistered post-failure action-space ablation recovered X under a
  commit-disabled learning contract".
- CI 가 0 포함/음수 → *"disabling commit did not recover measurable
  SHAPING-regime net-capture gain under the frozen learning contract"*
  + **본편 rescue search 종료** (이후 entropy/c_lim/rollout/보상/구조
  실험은 별도 exploratory study 로 분리, docs/70 §4-6).
- 성공해도 "learned shepherding" 확정 아님 — static/active attribution
  별도 (기존 계획).

## 4. 비준표 (2026-08-08 — r1 로 동결)

```
[v] 2-arm 블록 동결 (LS-live·LS-off, seed0 = index 유지)      승인
[v] 두 팔 diff = limiter_commit 단 하나                       승인
[v] primary = Δ_shape · confirmatory seeds {1,2,3,4}          r1 이행 (seed0 CI 제외)
[v] ablation IID 10300..10599 신설 (기존 대역 재사용 금지)     r1 이행 (사전 열람 없음)
[v] SHAPING pre-treatment                                     r1 코드 확정 (§0.1)
[v] commit-off = head 부재 + 배선 스펙 + 잠금 테스트           r1 이행 (§0.1·§2.1)
[v] bootstrap seed-최상위 + nested paired (pooling 금지)      r1 이행 (§1.2)
[v] "causal contributor" 강도 ("the causal blocker" 금지)     r1 이행
[v] stop rule: 블록 실패 = rescue 종료 · headline 교체 금지   승인 (강)
[v] arm-ladder 7항 (docs/70 §4)                               등재
```

**r1 수정 4건 이행 완료 — 비준 성립, 구현 인가.**
