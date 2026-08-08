# 71 — LS-COMMIT ABLATION 최종 폴백 블록 사전등록 r0 — 비준 대기

**2026-08-08 · 리뷰 9 (docs/70) 수정안 채택. LL 0/300 · LS(0.163) 관찰 후,
결과를 더 보기 전에 **2-arm 블록 전체 + 판정 + stop rule 을 한 번에
동결**한다 (arm-ladder 규율, docs/70 §4). 이 블록이 이 연구의 **마지막
learning-contract rescue** 다. r0 = 초안 (Hyunjun 비준 대기) — 비준 전
추가 학습 시작 금지.**

★ 정직성 선언: 이 블록은 LS seed 0 의 commit 자폭 관찰에 의해 활성화된
post-failure design 이다. 폴백 자체(`limiter_commit=false` = "커밋을 정책
손에서 뗀 대조군")는 결과 전에 선언돼 있었다 (docs/29 §15.2 (b) + 학습기
config 주석). 활성화 시점이 결과 후라는 사실은 숨기지 않는다.

---

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
> All trained policies are evaluated on the same frozen IID 300-episode
> paired threat set. The primary mechanistic endpoint is SHAPING-regime
> nondestructive net capture:
>
>     Δ_shape = p_net^{LS-off, SHAPING} − p_net^{LS-live, SHAPING}
>
> **Positive blocker evidence** requires the paired, seed-resampled 95%
> bootstrap confidence-interval lower bound for Δ_shape to exceed zero.
> Overall IID net capture, total defense, FREE-regime performance,
> limiter survival, time-to-all-spent, and route-interaction statistics
> are reported as secondary or mechanistic diagnostics and cannot
> replace the primary criterion.
>
> If the primary criterion is not met, no further commit-entropy,
> limiter-cost, rollout-length, reward, or action-space rescue arm is
> run in this study. The result is reported as a failure of commit
> removal alone to recover measurable cooperative shaping under the
> frozen learning contract.
>
> If the criterion is met, the conclusion is limited to a causal
> action-space diagnosis: allowing the learned commit action impaired
> shaping acquisition or expression under this training contract. The
> commit-disabled arm remains a secondary mechanistic ablation and does
> not retroactively replace the original commit-live headline MARL
> result. A claim of learned shepherding still requires the separately
> planned active/static mechanism-attribution analysis.

## 2. 실행 계획 (비준 후)

- 신규 학습 = **9런**: LS-live seeds 1..4 (4런; seed 0 은 기존 결과 유지)
  + LS-off seeds 0..4 (5런). 서버 tmux + ntfy, CUBLAS 결정론 설정.
- config: `configs/l2_mappo_nocommit.yaml` = l2_mappo.yaml 복사 +
  `mappo.limiter_commit: false` 한 줄 — **그 외 diff 0** (블록 계약).
  LS-live 는 기존 config 그대로.
- CLI: `train_m4 --threat-layer train --finisher-policy scripted
  --seed {s} [--config configs/l2_mappo_nocommit.yaml]`.
- 평가: 전 정책 (기존 LS seed0 포함) 을 **동일 IID paired 300판**
  (iid 10000..10299, docs/63 §3.1 대역) 에서 재평가 — 평가 러너는 headline
  러너와 공용으로 작성 (regime 분해 포함). Δ_shape 는 paired +
  seed-resampled bootstrap.
- 곡선 열람 규율: 학습 중 곡선은 모니터링만, 어떤 중간 중단·재선택 금지.
  블록 전 런 완주 후 일괄 평가.
- 진단 ①③④ (docs/70 §2) 는 블록과 병렬 실행 가능 (기록용 — 블록 설계에
  소급 반영 금지).

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

## 4. 비준표 (r0 — Hyunjun 대기)

```
[ ] 2-arm 블록 동결 (LS-live 0..4 · LS-off 0..4, seed0 유지)
[ ] 두 팔 diff = limiter_commit 단 하나 (그 외 전부 동일)
[ ] primary = Δ_shape (SHAPING regime p_net, paired+seed-resampled 95% CI
    lower > 0) — 그 외 지표는 secondary/diagnostic
[ ] IID 10000..10299 공용 평가 (headline 대역과 동일)
[ ] stop rule: 블록 실패 = 본편 rescue 종료 · L-off ≠ headline 교체 ·
    성공 소급 금지
[ ] arm-ladder 일반 규율 7항 (docs/70 §4) 등재
```
