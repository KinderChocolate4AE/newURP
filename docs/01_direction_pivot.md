# ANDES URP 방향전환 노트 (2026-06-24)

> 상태: 제안 — Hyunjun 검토 대기. 정본 계획(URP_action_plan_v0.7 / work_split / ai_worklist)은 이 노트 비준 후 개정.
> 근거: 2026-06-24 novelty 적대 감사(EN 5각도) + game-value/economics 점유 검증(EN 3각도) + 중국어 sweep(CNKI 3각도). 전부 deep-research 하네스.

---

## 0. 한 줄

**old:** "Dynamic Capture Viability Shaping" — 협력팀이 적을 net-capturer의 동적 capture-viability set으로 몰아 *capturability를 제조*한다.
**new (load-bearing):** **협력 shaping을, 유한·비가역·miss-is-free 비파괴 finisher의 *교환-경제학(exchange economics)*의 lever로 쓴다** — MARL로.

전환의 본질: "포획을 만든다"(전술/메커니즘, 점령됨) → "비파괴 방어가 *경제적으로 언제 성립하고, 협력이 그 교환비를 어떻게 옮기나*"(문제/구조, 빈칸).

---

## 1. 왜 전환하나 (기조)

- 사업화→논문화. '수단'(CBBA+RL)→'문제'. fidelity/재현도 < **usability + novelty + 나의 완전한 이해**.
- 우선순위: ① 모든 구석을 내가 이해 ② 실제로 novel.
- 해자: **학술 우선권**(공개 선점) + **상업 go-through-me**(암묵지·툴링 불가결성; 특허 배제는 포기). → 논문=광고판, 해자=레시피·스택·정량지도 보유.
- flag-planting 거부: "남이 2년 안에 도달할 자리에 먼저 깃발"은 해자가 아님. 공개 즉시 추월됨.

---

## 2. 무엇이 무너졌나 (감사 결과)

**"manufacturing capturability" 헤드라인 = 개념 선점.**
- Von Moll, Maity, Pachter, Shishika, Dorothy 2025, *Target Defense Using a Turret + Mobile Defender Team* (arXiv:2509.09777, AFRL) — 이종팀; defender가 적을 작동제한 finisher(turret)의 도달집합으로 몰아넣음 = "특정 finisher 위한 capturability 제조"의 해석적 선례. **+ 같은 그룹이 many-vs-many 확장 예고 = 우리 구도로 직진.**
- Chen, Hu, Gao, Jing 2024, *Luring cooperative capture guidance* (Astrodynamics 8(4):675) — inducer가 적을 유인→다른 teammate가 요격. (ii)의 직격.

**3-way 각 다리 개별 선점.** (i) net 전개 동역학 = 단독 사망(Drones 9:190 FEM; Pliska FRPN RA-L 2024; Liu arXiv:2506.03297 multi-UAV net+MAPPO). (ii) shape-for-finisher = 개념 선점(위). (iii) 학습 capturability surrogate = Choi 2026(Aerospace 13:347, GPR but *선택*용); het-role MARL(Drones 2026 10(4):248).

**두 큰 프레임 모두 60년 점령(검증).**
- 차분게임 **value/barrier "viable-defense region"** (Isaacs→Von Moll/Shishika/Yan/Bakolas/Tomlin). 단 capture가 예외 없이 반경-point·재시도 무한·kinetic·파괴적. **유한탄·비가역·miss-free 전무**(순차 capture는 본인들이 open problem이라 명시).
- 방공 **OR 유한자원+교환비 경제학** (Manne 1958 WTA; Hughes 1995 salvo; Armstrong 2014 Iron Dome; Davis-Robbins-Lunday 2017 동적 유한재고 ADP; Han-Lunday-Robbins 2016 deplete-then-penetrate DAD). 단 사수=고정능력, shaping/비파괴/教換比-as-shaping 전무.

→ 그러므로 "그들 게임에 net 끼워 현실화"만이면 **약한 기여**(현실화). Hyunjun 직감대로.

---

## 3. 살아남은 빈 자리 (검증됨)

**OPEN seam (EN 5+3, 中 3 전원 OPEN 판정):** 협력 SHAPING을 — 유한·비가역·**miss-is-free** 비파괴 finisher의 **교환-경제학의 lever**로 — MARL로. 세 재료(유한발 경제=shoot-look-shoot / 비파괴 협력몰이=StringNet / 교전-shaping이 미래 capture 악화=sequential-intruders)가 *따로* 존재하나 **아무도 안 합침.**

**왜 전술 굴레를 벗어나나:** 전술이 아니라 *게임의 payoff 구조에 대한 진술 + 그걸 옮기는 mechanism(shaping)*. 새 전술이 나와도 안 낡음. capacity-exhaustion(적이 net 소진 후 본 공격)은 *치명적 버그가 아니라 중심 변수*로 흡수 — "net 소진에 적이 feint 몇 번? 그 교환이 누구에게 유리?".

**왜 더 강한 해자인가:** 제어/MARL × 방공 OR 경제학 × net 도메인의 *교차*라 차분게임 그룹도 OR 그룹도 robotics-herding 그룹도 자연히 못 옴 = go-through-me의 실체.

**miss-is-free 비대칭(뿌리):** 빗나간 net은 적엔 공짜·방어엔 자원 소모. kinetic 방어엔 없는 비대칭(근접만 해도 위협). 이게 net 방어가 경제적으로 취약한 이유이자 우리 문제의 *고유 구조*.

---

## 4. 핵심 기여 (정밀화 대상 — §8에서 정식화)

1. **문제:** 유한·비가역·miss-is-free 비파괴 finisher + 협력 limiter 팀 vs 자원을 소진시키려는 적응형 적. 목표 = "방어가 +가치를 갖는 자원영역(net capacity × 속도/기동비 × 팀크기 × net spec)" + 협력이 그 영역을 어디로 미는가 + 교환비.
2. **방법:** E_req를 **per-shot value(발당 가치)**로 승격 → shaping 보상이 *그 발당 가치를 높이거나 적의 cost-to-defeat를 올리도록*. 학습 = MARL(이종 역할).
3. **산출(공개):** 프레임 + 존재/기전 + bounded envelope 1개. **(보유): 정량 전체 지도·튜닝 정책·E_req 보정본·스택.**

---

## 5. 자산 회계 (유지 / 추가 / 폐기·강등)

**유지:** WarSim SE3(6-DOF) substrate; E_req 4항(→per-shot value로 재해석); shaping/herding 메커니즘; reduced-attitude pointing + strategy-agnostic action space 결정(2026-06-12); harness(통계 경량 유지).
**추가(신규 lift):** 유한-탄 상태 + 소진 동역학; 교환비/비용 목적함수; **자원을 소진시키는 적응형 적**(self-play); game-value(또는 그 학습 근사) 층.
**폐기·강등:** "manufacturing capturability" 헤드라인(개념 선점); T0 외부 anchor-as-gate(→현실 파라미터 출처로만 경량화); N1 citable-PASS 중장비(→"현실 regime에 gap 존재" 수준); §11 Q1-레버/Phase F venue 최적화 과중; J.6 전체 code 공개(→레퍼런스 최소만, 해자).

---

## 6. 정면 인용 + 차별화 (must-cite-and-diverge)

| 군 | 대표 | 우리 차별 |
|---|---|---|
| teammate-conditioned shaping (해석) | Von Moll 2025 (arXiv:2509.09777); Chen 2024 (Astrodynamics 8(4):675); Von Moll 2022 TRP (TAES, 10.1109/TAES.2022.3176599) | finisher 조건이 *기하/운동학*(turret 각도·zero-overload)이 아니라 **net 전개 viability set**; 해석 아닌 **학습 surrogate**; 단발이 아닌 **유한·비가역·miss-free 경제** |
| 비파괴 협력 herding | StringNet (Chipade-Panagou, Front.Robot.AI 2021, 10.3389/frobt.2021.640446) | "net"=대형 장벽이지 발사형 유한자원 아님; finisher 경제 0 |
| 협력 net + MARL | Liu 2025 (arXiv:2506.03297); Huh 2026 (Machines 14(4):413) | homogeneous·추격(shaping 아님)·net 경제 0 |
| capturability 기반 선택 | Choi 2026 (Aerospace 13(4):347) | predict-then-**select**(표적 불변) vs predict-then-**shape** |
| 방공 OR 경제학 | Manne 1958; Hughes 1995; Armstrong 2014 (Iron Dome); Davis-Robbins-Lunday 2017 (EJOR, 10.1016/j.ejor.2016.11.023); Han-Lunday-Robbins 2016 (INFORMS JOC, 10.1287/ijoc.2016.0690) | 사수=고정; 우리는 **maneuver-shaping이 교환비의 lever** + **비파괴** finisher |
| 차분게임 value | Garcia-Casbeer-Pachter; Yan-Shi-Zhong; turret service-time (arXiv:2302.02186) | 유한·비가역·비파괴 capture 모델 (그들 open problem) |
| 中: 가장 가까움 | 狼群劳动分工 (智能系统学报 2021 16(1):125-133, 10.11992/tis.202007043) | 이종역할+비용 있으나 bio-rule(MARL 아님)·kinetic·비용≠교환비 |
| 中: 围捕 정전/RL-PE | 多机器人协同围捕综述 (自动化学报 2024 50(12), 10.16383/j.aas.c240114); 耿远卓 2023 (自动化学报 49(5), 10.16383/j.aas.c220204) | 대칭 point-capture·무한·연료는 *자기* 예산; 비파괴/교환비 0 |

---

## 7. 리스크 / 미해결

- **CNKI/万方 페이월 잔여(중요):** EN+中 visible lit은 OPEN이나, 중국 석박사 학위논문에 "consume-then-penetrate 게임화"가 숨었을 잔여 가능성. → commit 전/공개 전 본문 1패스(또는 한국어·중국어 네이티브 확인) 권장. 현 확신 ~90%(상향).
- **더 큰 lift:** game-economics 층은 신규 모델링. 첫 논문은 *tractable* 인스턴스로(아래 §8).
- **공간이 빠르게 닫힘:** RL+net(Gavin 2026 arXiv:2603.16279)·multi-UAV net MARL(Liu 2025)·AFRL turret+defender 확장 → **arXiv 우선권 타임스탬프 우선**(moat 정합).
- **novelty=fusion-level:** 각 조각은 선점 → 항상 *교집합*으로 방어(현실화 프레이밍 금지).

---

## 8. 다음 (의존 순서)

1. **게임·목적함수 정밀 정식화** — finisher 상태(잔탄·비가역·전개지연), miss-is-free payoff, exchange-ratio 목적, shaping이 그것을 옮기는 경로(E_req→per-shot value). (Hyunjun 주도 = 우선순위 ①)
2. **CNKI/万方 본문 확인 sweep** — §7 잔여 리스크 닫기.
3. **최소 모델 probe** — 팀 vs 적: 방어 가치를 (capacity × 속도/기동비)로 특성화 + 협력이 viable 영역을 미는 방향 1장. WarSim 위 최소 추가로.
4. 비준되면 → action_plan/work_split/ai_worklist 개정(§5 폐기·강등 반영) + arXiv 우선권 일정.
