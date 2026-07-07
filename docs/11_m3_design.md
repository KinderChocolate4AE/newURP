# 11 — M3 설계 (DRAFT v0.1, 2026-07-07) — Hyunjun 비준 대기

> 입력: L2 게이트 PASS(09 (q)) · P4 진단(09 (s)/(t)/(u)) · 피어리뷰 v2 지침 · 03 §G S9(M3-RESERVED).
> 원칙: **M2 동결 계약은 그대로 둔다.** M3 = 신규 env 변형(비동결)·신규 보상 기하. 경제(frontier) 주장은 S9 raid에서만.

## 0. 구조: M3 = M3a(캡처 개방) → M3b(S9 raid·exchange frontier)

- **M3a "capture-unlock"** — corridor 1-attacker·K=1 유지, **보상 기하만 교체**(아래 A/B) + 커리큘럼(C). 목표 = frozen 상수 eval에서 **clean crossing > 0, physical capture > 0** (= D2-B 헤드라인). P4가 실측한 findability 문제의 직접 해소 실험.
- **M3b "raid frontier"** — S9: 순차/포화 공격 M>1, 유한 그물 K binding. **exchange frontier(P_penetration vs E[자원 지출])** 를 측정된 MARL 롤아웃으로 구동(exchange.py 스텁 + prototypes/exchange_game.py 이식). 논문 main figure = frontier shift(shaping vs more-nets). M3a 정책·기법을 이월.
- 순서 근거: 캡처 없는 raid는 K 경제가 퇴화(전부 wasted 또는 무발사) → **M3a가 M3b의 전제.**

## 1. M3a 보상 설계 (P4 요건 A·B 반영)

기호: v = v_shot_soft, o = p_feasible(열린 witness 비율), boxed = (n_feasible==0), m_clean = clean 여부(v≥θ ∧ ¬boxed).

**(A) boxed·clean headline 등가 제거 — v_effective:**
```
v_eff = v · 1[¬boxed]                      # 문자형(기본). boxed → headline 기여 0
      (옵션) v · σ(margin/τ_m)             # smooth 변형 = ablation 노브
headline_M3 = Δ(v_eff)                     # M2의 Δv_soft 대체
```
근거(P4): boxed에서 v:=1.0 연속성 → clean과 headline 동일 = 두꺼운 boxed 분지의 원천. M3a에서 boxed는 **headline 0** — "패널티 소량"이 아니라 등가 자체를 제거.

**(B) clean-근접 역-U 기하 보상 r_geo:**
```
r_geo = v · g(o),   g = exp(−(ln o − ln o*)² / 2σ_g²)  (o=0이면 g=0)
o* = 1e-3 (P4 실측: clean 최적점 p_feas ∈ [4e-4, 2.4e-3]),  σ_g ≈ 1.0 (자연로그 스케일, 시작값)
```
- "too loose(o 큼)→낮음 / just right(o≈o*)→최대 / too tight(boxed, o=0)→0"의 **역-U**. 현행 단조-조임 유인의 교정. per-step 계산비 0(이미 계산되는 양).
- 관측성: **o와 boxed를 obs에 노출**(M2 vres 트리플에 이미 있는지 확인, 없으면 추가 — M3 env라 자유). λ1(clean bonus)은 유지하되 r_geo가 거기까지의 gradient를 제공.

**전체 J_M3a(초안):**
```
J = w_h·Δv_eff + w_g·r_geo + λ1·1[clean] + λ_cap·1[captured] − λ2·wasted − λ3·limiter_loss
시작값: w_h=1, w_g=1, λ1=1, λ_cap=5, λ2=1, λ3=0.5 (λ_cap만 신규·크게 — 진짜 목표)
```

**(release 지원)** P4 (u) 실측: clean은 방사 완화가 아니라 **축-정렬 채널 형상** → "compress → finisher 정렬 → 채널 release → fire" 2단 행동 필요 가능성. 보상은 r_geo가 유도; **행동 공간은 무변경**(기존 accel로 표현 가능) — 대신 진단 지표로 "release 이벤트"(o: 0→(0,o_hi] 전이)를 로깅해 학습 여부를 관측.

## 2. 커리큘럼 (요건 C — scaffolding 전용)

| stage | 학습 상수 | 종료 조건 |
|---|---|---|
| S1 wide-clean | cone half_angle ×3 (0.20), θ_fire 0.8, σ_g ×2 | clean_cross(학습 eval) > 0.2 지속 |
| S2 transition | half_angle·θ·σ_g 선형 복원(→0.067/0.9/1.0) | frozen 상수 도달 |
| S3 final frozen | **전부 frozen 상수**, r_geo·w_g 축소(0.3) | 판정용 |

- **eval은 전 스테이지 frozen 상수 + held-out CRN**(P1 하네스 재사용). 커리큘럼 성공은 main claim 금지 — 최종 정책이 frozen에서 내는 clean/capture만 판정.
- 함정 대응: sparse-λ1 재실패 방지 = r_geo(近접 신호), headline farming 방지 = (A), boxed 고착 방지 = boxed headline 0.

## 3. 학습 실행 계획 (M3a)

- **레시피 = P1 확정 main recipe(coma mix 0.5, recipe-v2)** 기본.
- **웜스타트 질문(비준 필요):** P4 (u)에서 기존 정책은 boxed 분지 심부 → 웜스타트가 덫일 수 있음. **추천 = 2-arm 소규모 결선**: warm(mix0.5 best-ckpt) 3-seed vs scratch 3-seed × S1만(200k) → clean 발견률로 본선 arm 선택(사전등록).
- 본선: 선택 arm × 10-seed × S1→S3 전체(500k+). 판정(사전등록): frozen held-out에서 **clean_cross_rate seed-군집 하한 > 0**(1차 게이트) / **capture_rate > 0 관측**(D2-B 헤드라인, existence 서술) / L2 헤드라인 지표 비열화(non-inferiority, margin −1 이내).
- 인프라: coma_D류 지표 wandb-only 금지(직접 기록), 러너에 o·boxed·release 이벤트 로깅 추가, ntfy 훅.

## 4. M3b — S9 raid·exchange frontier (개요만, 상세는 M3a 중 별도 설계)

- env: 파도형 공격 M∈{3,5}, K∈{1,2,3}(binding), 자원 회계 = exchange.py 이식(2-통화: 소모성 limiter vs 희소 net).
- 측정: 정책군 {M3a 정책, no-shaping+more-nets, scripted}에 대해 **P_pen vs E[지출] frontier**; 공격자 = scripted 가족 + bait/exhaustion 변형(+선택: exploiter probe).
- main figure = frontier shift; 보조 = capture envelope(2.4→<2.0m 여부), robustness(가족 분포 변화).
- 빌드 박스: 2–3주 상한(스코프 크리프 금지) — M2 env 재사용 + wave 스케줄러 + 회계 레이어.

## 5. 리스크

| 리스크 | 대응 |
|---|---|
| r_geo 게이밍(o만 맞추고 v 낮음) | r_geo = v·g(o) 곱형 + 판정은 clean/capture만 |
| 웜스타트 boxed 고착 | §3 2-arm 결선(사전등록) |
| 커리큘럼→frozen 전이에서 붕괴 | S2 선형 anneal + best-ckpt + last-3 판정 유지 |
| o* 오지정 | o* 스윕은 S1에서만 {3e-4,1e-3,3e-3} 소규모 허용(사전등록) |
| M3b 스코프 크리프 | 2–3주 박스, frontier 1장 목표 고정 |
| 일정(제출 가을) | M3a 2주 + M3b 3주 + P3 1주(병렬) + 집필 4주 |

## 6. 비준 체크리스트 (Hyunjun)

1. M3a→M3b 순서 및 M3a 보상식(§1 A/B, 시작 가중치) — 특히 **v_eff 문자형 vs smooth 기본값**
2. o* = 1e-3 (P4 실측 근거) + S1 한정 소규모 스윕 허용 여부
3. 커리큘럼 3-스테이지 상수(§2 표)
4. 웜스타트 2-arm 결선(§3) 설계
5. M3a 판정 기준(clean 하한>0 = 게이트, capture>0 = 헤드라인 existence)
6. M3b 박스(M, K 값, 2–3주 상한)
