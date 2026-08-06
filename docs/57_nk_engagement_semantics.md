# 57 — NK–contact 의미 감사 + 발사 후 latest-start sweep 사전등록

**2026-08-07 · 감사 판정 먼저, sweep 은 결과 보기 전 사전등록.**

---

## 1. 질문 (리뷰 4)

R1 의 "contact event" 에 NK veto 를 적용하는 것이 인과적으로 타당한가?

```
A. 실제 물리 충돌   -> 이미 일어난 충돌을 guard 가 "거부" 할 수 없다.
                      NK 안 충돌엔 별도 손실/위험을 부과해야 한다
B. 근접 kinetic engagement opportunity
                   -> guard 가 실행을 거부할 수 있다. 단 "contact" 명칭 부정확
```

## 2. ★ 판정 = B. 근거 사슬 (비준 기록 ↔ 코드 대조)

1. **`kill_radius` 의 비준된 의미** — `roles.py:26`:
   `# explosive kamikaze kill-radius [m]`. **폭발형 카미카제 요격의 실행
   반경**이다. 반경 진입 = "기폭 가능 기하 진입"이지 충돌이 아니다.
2. **backend 에 충돌 물리가 없다** (`sim/analytic.py` — momentum/충돌 전무,
   기체는 서로 관통). "충돌 event" 는 물리에서 발생할 수 없고, 판정 overlay 로
   만 존재한다.
3. **Bernoulli(Pk) 는 요격 성공률**이지 충돌 결과 물리가 아니다 (docs/29 §14
   "기하 조건 ∧ Bernoulli(Pk)", Pk = 선언 sweep 축).
4. **미소모 규약이 B 에서만 정합**: veto 시 limiter 미소모 (docs/29 §13.3).
   실충돌이라면 충돌 자체로 손상돼야 한다. "기폭을 보류했으므로 소모 없음"
   은 B 의 인과다.
5. **NK 논리가 폭발 요격에 정확히 적용**: docs/29 §13 "파괴적 요격 금지 —
   잔해가 지키려는 것 위에 떨어진다". 기폭 보류는 이 안전 계약의 직접 구현.
6. docs/54 R1 도 처음부터 "발동 조건만 커밋→접촉으로 확장, 해소는 같은 확률
   모형" 으로 선언 — R1 의 event 는 애초에 **요격 시도**였다.

**결론**: NK veto 의 R1 적용은 비준 계약과 정합하다 (P11 "NK 안 HARD_KILL
절대 금지" 를 R1 이 보존 — probe 실측도 11/11 veto 로 P11 준수).
2×2 결과의 해석 유효.

## 2.1 후속 의무

- **명칭 정정 (chore, 별도 커밋)**: "contact" → "engagement" 계열
  (`r_contact`→`r_engage`, `contact_resolver`→`engagement_resolver`,
  `CONTACT_NEUTRALIZATION`→proximity kill 표기). 이번 세션에서는 기계적
  rename 으로 새지 않고 **의미를 docstring/문서에 고정**만 한다 (docs/54
  사전등록 문서의 어휘를 소급 수정하지 않는다 — 이 문서가 정정 기록).
- **모델 한계 등재**: NK 안에서 공격자가 limiter 위치를 관통하는 비의도
  충돌은 모델에 없다 (충돌 물리 부재). frontier 보고 시 명시.

## 3. 발사 후 latest-start sweep 사전등록 (★ 결과 보기 전)

### 3.1 질문

> limiter 가 (발사 후 구간에서) 언제부터 움직여야 NK zone 진입 **전에**
> 허용된 kinetic 무력화 기하를 만들 수 있는가 — latest recoverable start.

### 3.2 왜 발사 후로 한정하는가 (선언)

발사 **전** 개입은 v_shot 을 바꿔 fire 시점·capture 동결값 자체를 바꾼다 —
(i) 경량 클론의 동역학 동치(P83d)가 발사 후에만 성립하고 (ii) 발사 전 개입은
"fallback 준비" 가 아니라 **net 게임(성형) 자체의 변경**이라 질문이 다르다.
발사 전 sweep 은 full-fidelity rollout 이 필요한 **별도 사전등록 후속**으로
둔다 (사실상 pre-fire mode scheduling = 3-way/MARL 영역).

### 3.3 설계 (§7.1 상수 재사용, 변경 없음)

```
대상       동일 7판 (ep 2·26·35·46·76·95·98)
controller privileged ORC 만 (upper-bound 질문)
grid       s0 ∈ { t_fire+1, t_fire+4, t*−5, t*−2, t*+1 }  (판별 dedup·정렬;
           t*−5·t*+1 은 2×2 와 연속성 anchor)
budget     §7.1 그대로 (CEM P64·I2·seed3 = 384 rollouts / point)
Pk         1 (deterministic lethality upper-bound probe 지위 유지)
성공       final env replay 라벨 HARD_KILL
           (P11 에 의해 KILL ⇒ 해소 시점 d_asset > r_nk — "NK 밖 무력화" 와
           동치. 커밋 경로는 미사용(비트 0) — kinetic 경로는 R1 뿐임을 명시)
보고       판별 latest recoverable start = 성공하는 최대 s0 (없으면 없음).
           NET_CAPTURE 는 s0 > t_fire 라 동결상 불가(§7.1 예측 유지) — 나오면
           구현 결함 신호로 조사. PENETRATED/TRUNCATED/NO_SOLUTION 그대로 기록
```

### 3.4 해석 (결과 보기 전 고정)

| 결과 | 허용 해석 |
|---|---|
| 일부 s0 에서 HARD_KILL | 발사 후 구간에 NK-밖 창 존재 — latest start 보고 |
| 전 grid 실패 | **발사 후 개입으로는** 이 7판·이 budget 에서 NK-밖 창을 찾지 못함 → 질문이 pre-fire mode scheduling 로 승격 (별도 사전등록) |
| s0 이 이를수록 단조 개선 아님 | 상태별 이질성 — 단조 결론 금지 |

물리적 불가능·"창이 없다" 단정 금지 (budget 한정, 오류 13 동형).

### 3.5 판정식은 결과 후 불변경.

---

## 4. ★ sweep 결과 (2026-08-07 — `results/latest_start_sweep.json`)

실행 메타: clean HEAD (sweep 배선 커밋 후) · §7.1 budget 그대로 · Pk=1 ·
per-point 384 rollouts × 35 point ≈ 5.5 h.

### 4.1 판정 (§3.4 해석표)

```
35/35 point 전부 PENETRATED · NO_SOLUTION_WITHIN_BUDGET 35/35
latest_recoverable_start = None (7판 전부)
```

**"전 grid 실패" 행 적용**: 발사 후 개입으로는 이 7판·이 budget 에서 NK-밖
kinetic 창을 찾지 못했다. → **질문은 pre-fire mode scheduling 로 승격**
(별도 사전등록 대상). 물리적 불가능·"창이 없다" 단정은 하지 않는다.

### 4.2 기전 (선언 기록 지표 내)

| fire+k | 접촉 도달 | min_swept 중앙 |
|---:|---:|---:|
| +1 | 5/7 | 0.521 |
| +3 | 5/7 | 0.413 |
| +4 | 5/7 | 0.592 |
| +6 | **7/7** | 0.271 |
| +9 | 2/7 | 0.957 |

```
접촉 도달 24/35 point · engagement event 42건 -- 전부 VETO_NO_KINETIC (42/42)
```

- 발사 직후(fire+1)부터 개입해도 **현 planner 가 찾은** 모든 engagement 는
  NK 안이다 (동일 한정: 7판·budget).
- ~~접촉 도달 비단조 = 상태별 이질성~~ **철회 (리뷰 4)**: 시작 상태·horizon·
  CEM seed 분산(3)·구간 경계가 교락 — 동일 point 반복 없이 귀속 불가.
- ~~"발사 시점에 이미 창이 닫혀 있었다" 가설 강화~~ **철회 (리뷰 4 §2 기각)**:
  이 결과는 planner 표현력·proxy 정렬·budget 한계와 **구분되지 않는다.**
  특히 구 proxy 의 tie-break(L4 전역 min 거리)는 "NK 밖에서 교전하라"는 유도
  신호가 없어 탐색을 NK 안 접촉 basin 으로 끌었을 수 있다 — 42/42 NK-안
  결과는 "밖에 해가 없다"와 "목적함수가 안으로 유도했다" 양쪽과 일치한다.

### 4.3 허용 문장 (보고서용 — 리뷰 4 확정 표현으로 교체)

> 가장 이른 post-fire 시작점을 포함한 현재 CEM sweep 에서도 NK 밖
> neutralization 을 찾지 못했고, 발견된 engagement 는 모두 NK 안이었다.
> 이는 fire 시점의 safe fallback recoverability 가 낮다는 가설을 강화하지만,
> planner 표현력·proxy 정렬·search budget 의 한계와 구분되지 않았다.
> Post-fire recoverability 는 확인되지 않았으며, pre-fire mode scheduling 이
> 다음 후보 설명이다.

("환원됐다" 는 쓰지 않는다 — pre-fire 개입을 실행한 적이 없다. 리뷰 4 §3 기각.)

### 4.4 다음 (별도 사전등록)

```
(i)  pre-fire mode scheduling probe -- full-fidelity rollout 필요 (경량 클론
     동치가 발사 전 미성립, §3.2). "언제부터 fallback-ready 기하를 준비해야
     NK-밖 창이 열리는가" 를 발사 전 축으로. = 사실상 3-way 의 첫 arm
(ii) r_nk 민감도 (계약 민감도 분석으로만 -- 성능 구제 금지, 리뷰 4 규율)
(iii) frontier 보고 시 attacker-limiter coupling 한계 명시 (docs/56 §9.2b)
```
