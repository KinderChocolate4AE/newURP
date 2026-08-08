# 70 — 외부 리뷰 9 판정 로그 (LS commit 퇴화 + 다음 팔) + 반영

**2026-08-08 · 프롬프트 = `review_prompt_ls_pathology.md` · 대상 = LL 0/300 ·
LS 0.163 진단과 다음 팔 선택. 반영 = docs/71 r0 (LS-COMMIT ABLATION 최종
폴백 블록 사전등록 초안, 비준 대기).**

---

## 1. 판정표 (리뷰어)

| 주장 | 판정 | 핵심 이유 |
|---|---|---|
| 1. LS 0.163 = finisher-only | **조건부 유지** | 8/8 궤적 근거는 강함 (공격자 250 m+ · sense ≤45 m 라 route 영향 가능성 사실상 0). 단 8/300 으로 300판 일반화는 과함 → **전수 audit 후** "functionally reduced to a finisher-dominated controller after an early transient" 까지 격상 가능. "literal finisher-only bit-identical" 금지 (초반 GEOM_FAIL event·reward history 존재) |
| 2. commit 자폭 국소최적 | **조건부 유지** | actuator 소멸 기제(P(survive k)≈(1−q)^k, q=0.44~0.80)는 유지 가능. 단 **학습 기전 3종(gradient 차단·−0.4 묻힘·entropy 0)은 미확정** — 분리 서술 의무 |
| 3. LL = 두 병목 재현 | **기각에 가까운 조건부** | LL/LS 는 별도 학습 정책이지 controlled intervention 아님. 상한 = "consistent with, but does not identify" — "legacy 재현" 금지. LL 진단(all-spent 시점·fire rate·gate open·eligible-but-no-fire) 후에만 강화 |
| 4. 대안 credit 설명 3종 | **유지** | (i) rollout 256: cut bootstrap 정확하면 구현 오류 아님, 단 commit(t=6~17)↔outcome(수백 스텝 뒤) credit 약화 가능 — 그러나 c_lim 은 **즉시** 부과라 절단만으론 조기 commit 선호 설명 불가 (ii) Δv_shot 상호작용 반경 밖 무신호 = **더 강한 대안** (iii) horizon 희석 가능. **commit-off 실패 ≠ commit 가설 기각** — "제거만으로 learnability 복원 실패" 로 서술 |
| 5. "cooperative shaping 학습 안 됨" | **기각** | `learned` 는 내부 학습 주장 — 관찰은 "상호작용 진입 전 actuator 제거". 상한 = "no measurable cooperative-shaping contribution was **expressed**" (§5 문장 상한) |

**총평 채택**: "commit → early GEOM_FAIL → limiter 소멸" 은 거의 직접 관찰 /
"commit 제거 → shaping 학습 가능" 은 전혀 미검정. **(a) 단독 즉시 실행
반대** — 결과 보고 행동공간을 줄여 쉬운 문제로 바꿨다는 공격에 취약.
**수정안 채택: LS-live vs LS-off, seeds 0..4, 단일 최종 confirmatory block
을 지금 동결** (docs/71). 이 블록 실패 시 learning-contract rescue 종료.

## 2. 저비용 진단 4종 ((a) 여부 재선택용 아님 — 기록용)

| # | 진단 | 상태 |
|---|---|---|
| ① | LS 300판 all-spent 전수 audit (t_first/all_spent · all-spent 시점 d_asset · sensing 진입 전 소모 비율 · 생존 수) | 서버 threat_log 재읽기 — 실행 예정 |
| ② | spent-agent PPO mask 확인 | **완료 (2026-08-08 코드 판독)**: mappo.py·adapter.py 에 mask 부재 — 소모 후에도 행동이 loss 에 들어간다. 즉 "gradient 0" 이 아니라 **world 와 무인과인 행동이 shared advantage 를 계속 받는 noncausal noisy credit** (진단 2 의 서술 정정) |
| ③ | commit-step reward/advantage audit | rollout 버퍼 미보존 — 재수집 1회 필요 (진단 전용, 학습 아님) |
| ④ | 기존 LS weight 의 eval-time commit=0 replay | 서버 1회 — "acceleration head 뒤에 의미 있는 행동이 숨어 있었나" (learnability 검정 아님 명시) |

## 3. commit-off 의 지위 (잠금)

> **L-off is a secondary mechanistic ablation, not a replacement primary
> MARL arm.**

L-off 가 scripted 를 크게 이겨도 "원래 headline MARL 성공" 소급 금지 —
"A preregistered post-failure action-space ablation recovered X under a
commit-disabled learning contract" 로만. docs/63 §2-5 의 "headline MARL 은
commit live" 전제 문구는 **유효 유지** (원 headline 은 commit-live 결과).

## 4. 일반형 arm-ladder stop rule (P95 교훈 동형 — 규율 등재)

```
1. primary contract 결과는 절대 교체하지 않는다
2. 실패 후 허용 팔 = 결과 전에 존재가 선언된 것만
3. 첫 adaptive activation 시점에 남은 팔 전체 + 순서/판정/stop rule 을
   한 번에 동결한다
4. 한 팔의 결과를 보고 다음 hyperparameter 를 고르지 않는다
5. 마지막 선언 팔 실패 = 본편 rescue search 종료
6. 이후 reward/entropy/rollout/architecture 실험 = 별도 exploratory study
7. 성공한 fallback 은 원 primary 의 성공으로 소급하지 않는다
```

이번 적용: 마지막 허용 팔 = **LS-off** (docs/71 블록). entropy·c_lim·
rollout·reward 순차 rescue 는 하지 않는다.

## 5. 문장 상한 (즉시 발효)

- LS: *"Under the frozen commit-live LS contract, no measurable
  cooperative-shaping contribution was expressed; the evaluated policy
  rapidly consumed its limiter actuators through unsuccessful commit
  proposals, leaving subsequent mission performance finisher-dominated."*
  (300판 전수 audit 전 = "evaluated policy" / 후 = exact fraction)
- LL: *"produced zero neutralizations in the 300-episode evaluation"* +
  *"consistent with simultaneous limiter-consumption and learned-finisher
  difficulties"* — "legacy firing-credit failure reproduced" **금지**.
- 전체: *"The reactive shepherding channel exists and is mission-relevant,
  but the frozen commit-live MARL contract did not produce measurable
  cooperative shaping in its first trained policies."*
- 금지 목록: "cooperative shaping is unlearnable" · "MARL cannot learn
  shepherding" · "formation learning failed despite accessing the
  relevant interaction" (접근 자체가 없었던 것이 문제).

---

*비준 대기 (Hyunjun): docs/71 r0 — 2-arm 블록 동결 · Δ_shape primary ·
5-seed · stop rule. 비준 전 어떤 추가 학습도 시작하지 않는다. 진단 ①③④
는 비준 무관 실행 가능 (기록용).*
