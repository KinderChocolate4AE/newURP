# 58 — 외부 리뷰 4 판정 로그 + P2′(NK-aware 재반증) 사전등록

**2026-08-07 · 프롬프트 = `review_prompt_nk_sweep.md` · 대상 = docs/57 (NK 의미 감사 + latest-start sweep)**

---

## 1. 판정표 (리뷰어)

| 주장 | 판정 | 핵심 이유 |
|---|---|---|
| 1. 판정 B 는 비준 기록이 지지 | **조건부 유지** | "현행 비준·구현 계약에서" 한정. 충돌 물리 부재 = A 의 반증이 아니라 미구현일 수도 |
| 2. 발사 시점에 kinetic 창이 이미 닫힘 | **기각** | planner 표현력·proxy 정렬(NK-밖 유도 신호 부재)·seed 분산과 미분리 |
| 3. 후행 handoff → pre-fire 로 환원 | **기각** | pre-fire 를 실행한 적 없음 + post-fire 부재도 인증 안 됨 |
| 4. coupling 한계는 caveat 로 충분 | **기각** | 접촉 전 유도 채널 부재 = 원 shepherding 질문의 검정 가능성 직접 위협 |

**총평 채택**: "탐색을 일찍 멈췄는가 → 그렇다." 현 결과의 지위 =
"현 planner 가 찾은 접촉이 모두 NK 안이었다"는 **진단**이지, "허용된
post-fire 접촉이 존재하지 않는다"는 인증이 아니다.

**최위험 미검증 가정 (리뷰어 지정)**: 현재 open-loop CEM 이 NK 밖 해가
존재한다면 현재 budget 에서 발견할 만큼의 표현력·목적함수 정렬을 갖췄다는
가정 — 35/35 NO_SOLUTION → "창이 닫힘" 논리 전체가 여기 의존.

## 2. 주장 1 반증 절차 수행 — provenance audit (2026-08-07, 완료)

R1(2026-08-06) **이전** 기록에 세 항목이 명시됐는가:

| 항목 | 출처 | 시점 | 판정 |
|---|---|---|---|
| kill event = 폭발·자폭 요격 | `roles.py:26` "explosive kamikaze kill-radius" | 커밋 45ab93d **2026-06-26** | ✅ 사전 |
| NK veto = 발동 보류 | docs/29 §13 "파괴적 요격 금지" + §13.3 커밋/해소 거부 | 2026-07-27 작성 (f42b728) | ✅ 사전 |
| veto 시 limiter 미소모 | docs/29 §13.3 "거부, limiter 는 소모되지 않음" (L357) | 2026-07-27 | ✅ 사전 |

**3/3 사전 존재 → B 는 사후 선택이 아니라 계약 복원.** 단 리뷰 한정 유지:
*"현행 비준·구현 계약에서 R1 event 는 proximal kinetic engagement
opportunity 다"* — 실제 시스템의 물리적 진실 주장이 아니다.

## 3. 반영된 문구 정정 (docs/57 §4)

- "창이 닫혀 있었다 가설 강화" 철회 → 리뷰 4 허용 문장으로 교체
- "pre-fire 로 환원" 철회 → "pre-fire 가 다음 후보 설명" 로 격하
- "비단조 = 상태별 이질성" 철회 (seed 분산·horizon 교락 미분리)

## 4. ★ P2′ 사전등록 — NK-aware proxy 재반증 (결과 보기 전 고정)

리뷰 4 §2 지정 최저가 반증. **이 arm 에서 NK-밖 후보가 하나라도 나오면
"창이 이미 닫힘" 계열 해석은 모두 무너진다.**

```
대상        동일 7판 · s0 = t_fire+1 한 시점만
dynamics    기존과 동일 (경량 클론·open-loop K=4 구간 가속 유지)
solver seed 10개 (0..9)  -- 기존 3 -> 10
budget      P64 × I2 × seed10 = 1280 rollouts / episode (결정론 count)
proxy       NK-aware lexicographic (구 proxy 의 전역-거리 tie-break 폐기):
            L1  NK-밖 무력화 (= HARD_KILL; Pk=1·resolver 상 NK-밖과 동치)
            L2  NK-밖 engagement 발생 수
            L3  NK-밖 구간(d_asset > r_nk 인 스텝)에서의 최소 swept 거리 ↓
            L4  최근접 NK-밖 접근 시점의 margin (d_asset − r_nk) ↑
            L5  penetration 지연 (종료 스텝) ↑
            ★ NK-안 접근은 어떤 우선순위에도 기여하지 않는다 -- 탐색을
              NK-안 basin 으로 끌던 신호를 제거
final       full-fidelity env replay 라벨만 (변경 없음)
판정        (a) 어느 판이든 L1 성공 or L2>0 후보 발견
                -> "닫힌 창" 해석 붕괴, docs/57 재작성
            (b) 전판 실패 -> planner adequacy 반증 1축 통과. 그래도 인증
                아님 -- 다음은 §5 순서
```

판정식은 결과 후 불변경.

### 4.1 ★ P2′ 결과 (2026-08-07 — `results/p2prime_ep*.json`, 7 병렬 샤드)

```
7/7 PENETRATED · NO_SOLUTION_WITHIN_BUDGET 7/7 · NK-밖 engagement 0건
NK-밖 최근접 swept (판별): 0.958 / 1.345 / 2.195 / 2.733 / 2.742 / 3.117 / 3.600
  -- 전부 요격 반경 0.75 초과 (최소 1.28배)
margin_at_best 0.355 ~ 1.323 m -- 최근접 NK-밖 접근이 전부 zone 경계 직전
```

**판정 = 사전등록 (b) 분기**: planner adequacy 반증 1축 통과. 탐색 신호가
**오직 NK-밖 근접만** 보상하고 seed 10·budget 3.3× 에서도 NK-밖 접근이 요격
반경에 도달하지 못했다 — 리뷰 4 의 "proxy 가 NK-안 basin 으로 유도했다"는
대안 설명은 이 표본에서 **반증**됐다.

기전 관찰 (기록 지표 내): 구 proxy 의 전역 최근접(0.227~)이 전부 NK-안,
NK-aware 최근접(0.958~)이 전부 경계 직전 — **요격 기하의 성립 시점이 NK 경계
통과와 사실상 일치**한다. 이는 "fire 시점의 safe recoverability 낮음" 가설과
정합하나, 잔여 대안(open-loop K=4 표현력·replan 부재)이 남아 있어 인증이
아니다. 허용 문장은 docs/57 §4.3 유지 + 아래 추가:

> NK-aware 목적함수·seed 10 에서도 NK-밖 접근은 요격 반경의 1.3배 이상
> 밖에 머물렀다 (7판·open-loop CEM budget 한정).

## 5. 확정 큐 (리뷰 4 순서 — 3-way 는 뒤로)

```
1. [x] P2′ NK-aware 재반증 (§4.1 -- (b) 분기: proxy-정렬 대안 반증, NK-밖 최근접 ≥ 0.958)
2. [x] pre-fire full-env counterfactual 1 arm (§6.1 -- ep35 OUTSIDE_NK 실증
       1건, 6판 실패. oracle 확장 없이 coupling gate 이동)
3. [ ] attacker–limiter coupling adequacy gate:
       (i) manipulation check (P84, §7 사전등록) -- 0.75 밖 배치 변화 ->
           attacker 불변 실측을 artifact 로 고정
       (ii) opt-in 회피 반응 attacker 계약 사전등록 (기존 A2 보존)
       (iii) 통과 전엔 "shepherding" 을 핵심 주장으로 쓰지 않는다
4. [ ] 경로 결정: 주장 축소(interception/coverage) vs 반응형 attacker 추가
5. [ ] 그 뒤 oracle/scripted/RL 3-way
```

**pre-fire probe 필수 계약 (리뷰어 지정, 사전 고정)**: 개입 뒤 원래 fire
시각과 miss 결과를 동결하지 않는다 — attacker·viability·fire gate·net
outcome 전부 실제 env closed-loop 재계산. 원래 fire 를 고정하면 "scheduling"
이 아니라 고정 궤적 위 위치 최적화가 된다.

## 6. ★ pre-fire arm 사전등록 (2026-08-07, 결과 보기 전 — 리뷰 5 지시 반영)

> **이번 pre-fire arm 은 legacy A2 에 대한 마지막 oracle 진단이다. 결과가
> 어떻든 post-fire CEM 개선·추가 timing sweep·새 reward·RL 학습으로 확장하지
> 않는다. 종료 후 반드시 coupling adequacy gate 로 이동한다.**

질문: post-fire 에서 못 찾은 NK-밖 engagement / net opportunity 를, limiter
가 **발사 전에** 움직이면 실제 closed-loop 환경에서 만들 수 있는가 —
"원래 miss 구제"가 아니라 **mode scheduling 자체를 다시 푸는 counterfactual**.

```
대상        동일 7판 · s0 = t_fire − 5 (baseline fire 기준 checkpoint 정의만;
            개입 뒤 실제 fire 시각은 달라질 수 있어야 한다)
rollout     ★ full-fidelity env (경량 클론 금지 -- 발사 전엔 v_shot 이
            dynamics 에 인과적: fire gate·capture 동결값이 바뀐다)
동결 금지    fire 시각 · miss 여부 · attacker 궤적 · v_shot · fire gate ·
            net outcome 전부 closed-loop 재계산 (필수 계약 §5)
controller  privileged CEM, §7.1 상수 (P64·I2·elite16·seed 3 = 384/판)
proxy       NK-aware (_proxy_score_nk -- L1 에 NET_CAPTURE 포함: 임무 성공
            우선, NK-안 접근 신호 금지 유지)
final       full env replay 라벨. 보고 5분법:
            NET_CAPTURE / OUTSIDE_NK_NEUTRALIZATION(=HARD_KILL) /
            INSIDE_NK_VETO(event 수, nonterminal) / PENETRATED / NO_SOLUTION
            + 신규 fire 시각·발사 여부·miss 지속 여부
```

해석 (결과 보기 전 고정, 리뷰 5):

| 결과 | 허용 해석 |
|---|---|
| NET_CAPTURE 발생 | limiter 사전 움직임이 fallback 이 아니라 **net game 자체를 개선** — pre-fire shaping/pre-positioning 증거. 단 attacker 는 반응하지 않았으므로 **shepherding 성공이라 부르지 않는다** |
| OUTSIDE_NK_NEUTRALIZATION 발생 | fallback 은 추격 국면이 아니라 **사전 safe kinetic geometry 준비 문제** — 2모드 설계의 의미 회복 |
| 전판 PENETRATED | "현 legacy A2 에서 현재 oracle family 로 recoverability 증거를 찾지 못했다" 로 닫고 **coupling gate 로 이동** (oracle 확장 금지) |

판정식은 결과 후 불변경.

### 6.1 ★ pre-fire 결과 (2026-08-07 — 서버 7 병렬, `results/prefire_ep*.json`, 커밋 7f8d56b)

```
ep 35   OUTSIDE_NK_NEUTRALIZATION   ★ 캠페인 최초 NK-밖 kinetic 무력화
        s0=10(fire−5) -> fire 원래대로 15 발사 -> net 비행 중 step 21-22 에
        limiter 0 이 d_asset 7.95 m (NK margin +2.6) 에서 KILL. miss 해소(23)
        전 종결 -- "miss 구제"가 아니라 mode scheduling 재해결
나머지 6판  PENETRATED · NO_SOLUTION (NK-밖 최근접 margin 0.35~0.94 -- 경계
        직전에서 요격 반경 미달 0.85~2.25)
관측    fire 시각 7/7 불변 (발견된 계획이 gate 를 교란하지 않았다는 관측 --
        "교란 불가" 아님) · INSIDE_NK_VETO 0건 (NK-aware 탐색의 산물)
```

**판정 (사전 고정 해석표 적용)**:
- OUTSIDE_NK_NEUTRALIZATION 행 발동: **"fallback 은 추격 국면이 아니라 사전
  safe kinetic geometry 준비 문제"** 의 실증 1건 — 2모드 설계의 의미가 처음
  으로 실측에서 회복됐다.
- 단 **1/7** — 상태별 이질성, 단일 "가능/불가능" 결론 금지. **shepherding
  성공이라 부르지 않는다** (공격자 무반응·privileged oracle·budget 한정).
- NET_CAPTURE 0건 — pre-fire shaping 이 net game 을 개선한 증거는 없음.
- **§6 첫 줄 규율 이행**: oracle 확장 없이 coupling gate 로 이동.

허용 문장:

> 발사 5 tick 전 개입에서 privileged planner 는 7판 중 1판(ep35)에서 net
> 비행 중 NK 밖 무력화를 달성했다 — post-fire 전 구간에서 0건이던 safe
> kinetic window 가 pre-fire 준비로 열릴 수 있음을 보인 첫 사례다. 나머지
> 6판은 현 budget 에서 실패했고, 공격자가 limiter 에 반응하지 않는 legacy
> A2 계약 아래의 결과다.

## 7. ★ P84 사전등록 — coupling Gate 1: manipulation check (결과 보기 전)

목적: "0.75 m 밖에서 limiter 배치는 공격자 행동에 인과효과가 없다" 를 코드
추론이 아니라 **결과 artifact 로 공식 고정** — 원 연구 질문(협력 성형)의
검정 가능성 판정 자료다.

```
대상       miss 7판 × 시점 2 (s0 = t_fire−5 · t*+1)
처치       s0 에서 limiter 4기를 공격자로부터 전부 >= 2 m 떨어진 상이한
           구성 3종으로 순간이동: swap(대각 교환) · line(일렬) · far(10 m 후방)
채널 격리   fire_mode="never" 로 진행 (net-side 경로 -- committed 플래그 경유
           간접 결합 -- 차단. 남는 후보 채널은 repel 뿐)
관측       이후 T=10 스텝(hold)의 공격자 위치 시퀀스 vs baseline(무처치)
판정       (i) 밖 구성 3종 전부에서 공격자 궤적이 baseline 과 bit 동일
               -> "직접 coupling 부재" 공식 확정
           (ii) positive control (limiter 1기를 0.74 m 안) 은 1스텝 내 발산
               -> 검사의 검정력 증명. 발산 안 하면 검사 무효
결과 무관   경로 결정(A 주장 축소 / B 반응형 attacker)은 별도 -- 이 gate 는
           결정의 사실 기반만 제공한다
