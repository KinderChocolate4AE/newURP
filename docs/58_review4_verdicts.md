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

## 5. 확정 큐 (리뷰 4 순서 — 3-way 는 뒤로)

```
1. [ ] P2′ NK-aware 재반증 (§4)
2. [ ] pre-fire full-env counterfactual 1 arm (t_fire−5, ★ fire 시각·miss
       여부·v_shot·attacker 전부 closed-loop 재계산 -- fire 동결 금지.
       라벨 {NET_CAPTURE, OUTSIDE_NK_NEUTRALIZATION, INSIDE_NK_VETO,
       PENETRATED, NO_SOLUTION} 분리. 별도 사전등록 후 실행)
3. [ ] attacker–limiter coupling adequacy gate:
       (i) manipulation check -- 0.75 밖 배치 변화 -> attacker 불변 실측 고정
       (ii) opt-in 회피 반응 attacker 계약 사전등록 (기존 A2 보존)
       (iii) 통과 전엔 "shepherding" 을 핵심 주장으로 쓰지 않는다
4. [ ] 경로 결정: 주장 축소(interception/coverage) vs 반응형 attacker 추가
5. [ ] 그 뒤 oracle/scripted/RL 3-way
```

**pre-fire probe 필수 계약 (리뷰어 지정, 사전 고정)**: 개입 뒤 원래 fire
시각과 miss 결과를 동결하지 않는다 — attacker·viability·fire gate·net
outcome 전부 실제 env closed-loop 재계산. 원래 fire 를 고정하면 "scheduling"
이 아니라 고정 궤적 위 위치 최적화가 된다.
