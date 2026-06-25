# newURP STATUS — 2026-06-24  (방향전환 · novelty · 검증 · 앞으로)

> 한눈 요약 문서. 상세 근거: `direction_pivot_2026-06-24.md`, `newURP_action_plan.md`,
> `newURP_M1_formalization_scaffold.md`, `GPT_ANDES_verification_pack_2026-06-24.txt`,
> 그리고 `WarSim/scripts/{reachset.py(→andes/),corridor_frontier,backdiag_sensitivity,exchange_game}.py` + `WarSim/data/m2_*.png`.

---

## 1. 방향 전환 (왜·무엇)

- **문제**: last-mile counter-UAS. 이종 협력팀 = **다수 *저가 자폭 kamikaze* path-limiter**(폭약 kill-radius) + **1 비파괴 net-capturer**. 양치기식 협력수비.
- **old → new 헤드라인**:
  - old: CBBA+RL(수단 중심) → "manufacturing capturability"(개념 선점됨: Von Moll turret+defender, Chen luring).
  - **new(정본 claim): 협력 shaping이 *유한·비가역·miss-free 비파괴 finisher(net)의 교환-경제학(exchange frontier)*을 움직인다 — MARL.** 싼 kamikaze가 적을 몰아 희소 net의 발당 가치를 올린다.
- **기조**: usability > fidelity(3DOF 유지) · novelty = *thin-but-honest intersection 수용* · 목적 = **robotics+RL 진로 milestone + 저널 게재 경험 + RL/physical-AI 학습**(URP-scoped) · moat 완화 → **코드 공개 OK**(portfolio·인용) · arXiv-우선권 압박 완화 → 현실 venue.
- **운영 교훈**: 초반 검증/probe에 과투자(build 0) → 지금은 **build-first, 검증 time-box**.
- **잠금 결정**: S4 적이 commit 관측·τ 동안 반응(worst-case v_shot) · S8 hard no-go + reachable-set v_shot · limiter = 싼 자폭 kamikaze(위협=herd, net=비파괴 takedown) · 방어자 2통화(싼 shaper + 희소 net)=cost-asymmetry 엔진 · default reactive 적(goal-constrained + 측면 dodge + kamikaze 회피 + commit 반응); back-diagonal·bait·reload는 S13로 보류.

---

## 2. Novelty (정밀화된 현 위치)

- **3 서브클레임**: (i) net 전개 동역학 = *단독 사망*(부품으로만) · (ii) finisher 위한 shaping = *개념 선점*(Von Moll/Chen) · (iii) 학습 capturability surrogate = *dented*(Choi 2026, 선택용). → 방어 가능 = **셋의 fusion + exchange-frontier 결과**.
- **점령된 두 큰 프레임(인정·차별화 대상)**: 차분게임 value/barrier(60년) · 방공 OR 유한자원+교환비 경제(60년, **Atkinson&Kress 2025 포함**).
- **방어 가능 핵심 = 두 분야가 안 만나는 다리**: 협력 *mobile shaping*이 *비파괴·miss-free·유한* finisher의 교환비를 *움직인다*(학습으로). 어느 분야도 단독으로 안 함.
- **BAR(필수 기준)**: best-response 적 하에서 *frontier가 이동*함을 실험으로 보여야 진짜(capture↑ 아님). → **A2 proxy에서 1차 demonstrated.**
- **must-cite-and-diverge**: Von Moll turret+defender(2509.09777)·Chen luring(Astrodynamics 2024)·Von Moll TRP(TAES 2022)·StringNet(2021)·Choi(Aerospace 2026)·Atkinson&Kress(Oper.Res. 2025)·Hughes salvo·Bildik decoys(2024)·狼群(智能系统 2021)·围捕/多弹 survey.

---

## 3. 검증된 내용 (no killer; thesis proxy-demonstrated)

**(a) 선행연구 (seam OPEN ~90–94%)** — EN 5각도 + EN 3각도(game-value/경제) + 中 3각도(CNKI) + 본문 정독 4편 + GPT 적대리뷰(우리가 재검증). 단일 killer 없음.
- 신규 must-cite(진짜·DENTS): **Atkinson&Kress 2025** — exchange-frontier *배경*을 점령 → "frontier 자체"는 우리 것 아님, 교집합으로만 방어.
- GPT 환각 적발: "Tirishchuk&Siritsa"(가짜; 실제 인접 = Bildik decoys, CLEARS).
- 잔여 리스크: CNKI/万方 석박사 학위논문 본문(공개검색 밖) → 공개 전 1패스 권장.

**(b) Build/sim (torch 無, numpy 4 산출물 + 2 figure)** — 방향 통째로 de-risk:
1. `reachset.py` — v_shot 코어(S8 lever): 적 τ-reachable set ∩ net 부피, kamikaze no-go가 R_A 축소.
2. `corridor_frontier.py` (+fig) — **lever 실재**(v_shot 단조 상승). 교환비 regime-map N*(agility): 평면 flat≈2, 3D 5→10 증가.
3. `backdiag_sensitivity.py` — **single-shot은 후퇴-회피에 취약**(v_shot 1.0→0.16; 측면 ring으론 복구 N*>29). bait는 적의 침투를 깎음 → **반복/교환 게임이 필연**.
4. `exchange_game.py` (+fig) — **첫 exchange-frontier: 싼 shaping이 buy-nets를 지배**(P_pen→0 @ resource 28[N=8,K=2] vs 39.6[K=3 nets]; shaping은 총비용도 낮춤). = **기여 thesis proxy 증명.**
- 공통 caveat: 단일-세그먼트·정적 v_shot·휴리스틱 정책·단일 적·defender-optimistic(back-diagonal이면 절대수치↓, 상대우위는 견고).

---

## 4. 앞으로 (build-first)

**다음(주력) = (A) torch/lab 빌드**:
- [ ] reactive 적: `threats.py`에 `state` 소비 subclass(goal-constrained + 측면 dodge + kamikaze 회피 + commit 반응) — default부터.
- [ ] reachset/v_shot을 Gym env(`role_env.py`)에 wiring + 유한-탄 finisher(이미 `effectors.py`에 ammo/fire/전개지연 존재) + miss-free payoff.
- [ ] COMA 차분보상으로 limiter 신용할당(`rewards.py` 확장).
- [ ] MAPPO 학습 → **휴리스틱 배치를 *학습* 정책으로 대체**, 실측 exchange-frontier.
- (torch는 lab venv. 나는 lab-ready 코드 작성, Hyunjun이 실행.)

**그 다음**: M3 = 실측 frontier-shift(vs no-shaping/selection/buy-nets, best-response 적) → 논문(현실 venue, 코드 공개).

**정직 하드닝(필요시·일괄 아님)**: S13 richer 적(back-diagonal+bait+reload) · S14 surrogate 검증 · 통계 경량(seed≥3+CI).

**잔여/정리**: CNKI 학위논문 본문 패스(공개 전) · `corridor_frontier.py` 데모루프 `__main__`로 · 긴 novelty 메모 consolidation.

**학습 산출물(1급)**: MARL(MAPPO/HAPPO)·credit(COMA)·학습/평가·동역학 sim. + 옵션 physical-AI stretch(sim-to-real / LiCS PX4-ROS2-Gazebo).
