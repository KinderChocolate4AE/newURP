# newURP_action_plan (v2 — 2026-06-24) [CURRENT · supersedes URP_action_plan_v0.7 (LEGACY)]

## 0. 현재 상황 (기록)

- **목적 전환**: novelty/moat 극대화 → **robotics+RL 진로 milestone + 실제 저널 게재 경험 + RL/physical-AI 학습** (URP-scoped). novelty = thin-but-honest intersection 수용.
- **novelty 정밀화** (감사 EN5+3·中3·본문4·GPT 검증): 방어 핵심 = "협력 shaping이 유한·비가역·miss-free 비파괴 finisher의 **exchange-frontier**를 움직인다"(MARL). 기여 = regime-map **결과**(조합 아님), best-response 적 하 frontier-shift 증명 시에만 진짜. arXiv-우선권·hold-recipe 압박 완화, **코드 공개 OK**(portfolio·인용).
- **운영 교훈(중대)**: 지금까지 검증·probe·적대 audit에 과투자, **build 0**. → 본 계획은 BUILD/학습에 에너지 집중. 검증은 time-box·최소.
- **자산**: WarSim SE3(6-DOF) · E*req(→per-shot value) · pointing/action-space 결정 · harness. 정본 = newURP*\*; 구 docs = LEGACY.

## 1. 최종 산출물 (가장 먼저 정의)

**제출된 논문**(현실 venue: 좋은 학회/응용 저널, workshop 디딤돌) — regime-map/frontier-shift 결과 — 를 **작동하는 MARL 시스템 + 공개 코드**가 뒷받침.
이중 가치: 논문=게재 경험·진로 신호 / 시스템+스킬=RL·physical-AI 학습 자산. **둘 다 같은 build에서 나옴.**
품질 기준(현실적, moat-defense 아님): 정직한 related-work 포지셔닝(Atkinson&Kress·Von Moll·Chen·StringNet·Choi·Bildik·围捕/拦截 survey) · frontier-shift 결과+CI · bounded regime-map 1장 · 재현 코드 공개.

## 2. Milestone 체크리스트 — 최종에서 역순 · 중요도순

> 규율: 각 M = checkpoint이자 **동작하는 산출물**(표·계획 아님). BUILD/학습 우선, 검증은 ⏱time-box.

### ★ M-FINAL — 논문 제출 + 공개 코드

- [ ] §I 문제 / §II 정직 related-work / §III game+reward / §IV MARL 결과·regime-map / §V 한계 작성
- [ ] 코드·재현 스크립트 공개
- [ ] venue 결정·제출 (⏱ 결정 1주 내)

### ★ M3 — 결과: frontier-shift 시연 (헤드라인 실험)

- [ ] exchange-frontier 측정: P_penetration vs E[nets spent], shaping on/off
- [ ] regime-map: (capacity × 속도/기동비) 위 shaping 우세 영역
- [ ] best-response-ish 적: scripted bait → (가능시) self-play 1단계
- [ ] 정직 보고(shaping 안 통하는 regime 포함). **DoD = frontier가 _움직임_(capture↑ 아님)**
- ⏱ 통계 경량: seed≥3 + CI (과한 통계 워크스트림 금지)

### ★★ M2 — BUILD: MARL 학습 작동 (학습·에너지의 심장)

- [ ] WarSim env 확장: 유한-탄 finisher(K·전개지연·비가역 fire) + miss-free payoff + per-shot value(E_req→v_shot)
- [ ] MARL 학습 루프 수렴 (MAPPO 먼저; HAPPO 비교는 옵션)
- [ ] baselines: no-shaping(finisher 단독) / selection-only / fixed-formation
- [ ] **조기 sanity**(구 'probe' 대체 — 별도 의식 아님, build 안에서 1회): shaping이 v_shot/frontier를 움직이나 → 음성이면 그때 재고
- ← **RL/physical-AI 학습 대부분 여기서 발생** (구현·reward·credit·학습/평가·sim)

### M1 — 최소 정식화 (LEAN — 며칠, 주 아님)

- [ ] scaffold 핵심 S1-S8 채움; S8 = deploy-delay reachable-set v_shot + COMA credit (→ newURP_M1_formalization_scaffold)
- [ ] 기본값 = **K=1 또는 작은 순차 M** (유한자원이 binding되게)
- [ ] **OPTIONAL S9-S14는 명시적으로 미루고 M2 진입** — 완벽 정식화로 build 지연 금지

### M0 — 토대 (지금)

- [x] 구 docs LEGACY 표시 + 현재 상황 기록
- [ ] WarSim build 환경 점검(학습 돌릴 준비) · 자산 동결 · 본 계획 확정

## 3. 의존/실행 순서 (앞으로)

M0 → M1(며칠) → **M2 build(주력·학습)** → M3 결과 → M-final 제출.
**규율: build가 막히면 검증/정식화로 회피 금지.** 최소 형식화 후 즉시 build. 검증은 결과 해석에 필요한 최소만. 적대 audit 반복 금지(novelty 충분히 확인됨).

## 4. 학습 산출물 (1급 목표 — 논문과 동급)

MARL(MAPPO/HAPPO) 구현 · multi-agent reward/credit(COMA) · 학습/평가 규율 · 6DOF 동역학 sim.

- OPTIONAL **physical-AI stretch**: sim-to-real 한 발 / LiCS 랩 PX4-ROS2-Gazebo (URP 본체는 6-DOF/SE3) — 랩·진로 정합.

## 5. 운영 규칙 (구판 대비 핵심 변화)

1. **BUILD-first**: 계획·검증보다 돌아가는 것. 매 M = 동작 산출.
2. **검증 time-box**: 통계 경량(seed≥3+CI); 적대 audit·probe 의식화 금지.
3. **개방 OK**: 코드 공개가 목표(학습·진로)에 부합.
4. Hyunjun이 코어(게임·reward·shaping 유도) 소유; AI = 구현·scaffold·디버그 보조.
5. mount/git 규율 준수.
