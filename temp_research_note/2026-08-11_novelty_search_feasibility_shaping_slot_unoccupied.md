# 2026-08-11 — 논문 서치: "feasible/infeasible shaping" slot 은 여전히 비어 있음 (novelty 생존)

3-갈래 병렬 웹 서치 (① MARL 요격 capture 조건·수치, ② viability/reachability+학습, ③ net-capture·이종팀·shepherding).
질문: 우리와 같은 feasible/infeasible approach 를 쓴 MARL 요격 논문이 있는가 + MARL 성공 케이스들이 상정한 값(= feasible region 예시).

## 결론 (novelty 방어 헤드라인)

**우리 주장의 3축 결합 — (i) dynamic viability 변수(a_req≤ρ·a_max, LOS rate, τ_deploy), (ii) 이종 역할(path-limiter + 단발 net-capturer), (iii) "팀원의 feasibility set 안으로 공격자를 shaping" 을 협력 보상으로 — 을 모두 갖춘 논문은 없음.** 각 축을 하나씩만 건드린 부분 겹침(YES-partial)이 존재하며, 이들이 정면 방어 대상.

## Tier 1 — 반드시 인용 + 정면 구분해야 하는 부분 겹침 (YES-partial)

| 논문 | 겹치는 축 | 우리와 다른 점 |
|---|---|---|
| **Zhang et al. 2022**, "Near-optimal interception strategy for orbital pursuit-evasion using DRL", *Acta Astronautica* 198:9–25 | RL 로 상태를 capture zone 안에 "embed" 후 guidance 핸드오프 — 2단 구조가 우리와 동형 | 1-v-1 궤도역학, **추격자가 자기 자신을** 자기 capture zone 에 넣음(자기-기동), barrier 는 해석적 폐형식, 이종 팀/단발 effector 없음 |
| **Xue et al. 2025**, "Apollonius partitions based pursuit-evasion strategies via MARL", *Neurocomputing* 630 | **MARL 루프 안에서 feasibility partition 자체가 shaping 목표** (evader dominant region 을 협력적으로 축소) | partition 이 상수-속도-비 Apollonius 기하 = **C_0/C_1 급** (가속도 한계·τ_deploy 없음), homogeneous, capture=근접 |
| **Dantas et al. WEZ 계열** (arXiv:2111.04474, 2207.04188, SIGSIM-PADS 2023) + no-escape-zone BVR DRL 클러스터 | 학습된 발사 envelope(WEZ)이 RL 의사결정에 들어감 | envelope 은 **자기 자신의** 것 — 자기 위치잡기용. 팀원이 target 을 남의 envelope 로 밀어넣지 않음 |
| **Gavin & Bronz 2026**, "Intercepting an Agile Target with Net-Carrying Drones using Competitive MARL", ICUAS 2026, arXiv:2607.05939 | MARL(MAPPO+PFSP) + net 드론 3대 + 협력 전술 창발 — **동시기 prior, Huh 2026 급으로 리뷰어가 들 확률 최고** | net 이 **발사체가 아니라 기체 하부 수동 충돌 원판** — 발사 이벤트·단발 제약·feasibility set 전무. reward 는 catch 이벤트+거리 shaping. 속도비 1:1, 다회 시도 허용 |
| **Zheng et al. 2025**, "Vision-Based Cooperative MAV-Capturing-MAV", arXiv:2503.06412 (Westlake) | **net 배치 feasibility 조건을 명시 모델링** (net envelope 볼록분해 + **dwell ≥ 0.5 s**, 단발) + 다중 드론 협력 | **학습 없음** (MPC+formation), homogeneous(전원이 net-gun 보유), 조건은 트리거 체크이지 shaping 목표 아님. 성공률 64.7%, target 4 m/s |

## Tier 2 — 관련 인용 (RELATED, 한 줄 처리 가능)

- **HJ-RL 계열 전체**: Hsu et al. 2021 RSS (reach-avoid RL, arXiv:2112.12288) · Li et al. (arXiv:2203.10142, viability kernel↔RL value 브리지) · ISAACS (arXiv:2212.03228) · MADR (arXiv:2510.18845) · Safe MARL via HJ (JIRS 2025). **공통점: set 은 안전 인증/학습 대상이지, 협력 shaping 보상이 아님.** 서베이 arXiv:2407.09645 하나로 계열 전체 fence-off 가능.
- **Bildik & Tsourdos 2024** (Aerospace 11:684, decoy MARL, MATD3): 우리 아이디어의 **거울상** — 희생 agent 가 팀원에게서 **멀어지게 유인**. "shaping into" 는 없음.
- **AMBUSH** (arXiv:2607.01029, PKU 2026): capture-feasibility 를 명시 계산(속도비·capture range·topology)하지만 MCTS planner, 비-RL.
- **Stagg/Von Moll 2026** (arXiv:2607.03554): engagement zone = 해석적 요격 feasibility set 의 순수형. 학습·협력 없음. Def 1 related work 앵커.
- **Zeng et al. 2022** (arXiv:2201.04180): tether-net **closing 타이밍을 PPO 로 학습** — "발사 결정이 RL 타겟"의 최근접 사례. 단일 우주기, 협력 없음.
- **Acharya et al. 2026** (arXiv:2607.10986): herd-standoff→neutralize 모드 전환 (CBF+minimax MPC, 비-RL) — **Paper 2 (Sequential Effector Mode Switching) 축과 겹침 주의**.
- Shepherding-RL 계열 (di Bernardo group arXiv:2411.05454 등): goal region 전부 **정적**. 유일한 "kill zone 으로 herding" 논문 (Mendívez Vásquez & Barca, Robotica 2023)도 정적 zone + potential field(비학습). **"팀원 capability 로 정의되는 goal region" 은 미점유.**
- 이종 역할 MARL: Kouzeghar 2023 ICRA(explore/track 역할), Drones 10(4):248(airship 센서+UAV 추격), Selmonaj(플랫폼 이종) — **effector-class 비대칭(loss-averse 단발 + expendable 지원)은 전무.**

## MARL 성공 케이스의 상정값 (= feasible region 예시 데이터)

| 논문 | N | 추격 v | 회피 v | 비(e/p) | capture 조건 | arena | 성공률 |
|---|---|---|---|---|---|---|---|
| Gavin & Bronz 2026 | 3 | ~15 m/s | 동일 기체 | **1.0** | 수동 net 원판 접촉, 10 s 내 | 32×32×16 m (evader 12×12×6) | 88–93%, t_catch 2.8–3.7 s |
| Huh 2026 (기지 prior) | 3 | — | — | — | d∈[3,10] m + cone + dwell 0.5 s | — | — |
| Zheng 2025 (비학습) | 3 | — | 4 m/s (1 m/s²) | <1 | net envelope + dwell 0.5 s, 단발 | — | 64.7% |
| Pierre/Fierro (Sandia) | 4 | 10 m/s | 10 m/s | **1.0** (형식상 v_p≤v_e) | 반경 **2 m** | 80×60 m | — |
| OPEN (Tsinghua, 기지) | 3 | 1.0 | 1.3 | 1.3 | 반경 0.3 m | 원통 r 0.9 m | — |
| DualCL (Tsinghua) | 4 | 1.0 | 2.4 | **2.4** | 반경 **0.12 m** (curriculum) | 원통 r 0.9 m | plain MAPPO **~0%** |
| Bildik decoy | 3 decoy | 30 m/s | Mach 1 미사일 | — | 기만 성공 | — | 71% |

reward 상정값 예 (Gavin & Bronz): λ_catch=10.0, λ_fail=30.0, λ_dist=0.001, λ_collPP=10.0 — 사실상 이벤트 보상 + 미세 거리 shaping. 5B step/side, JAX.

## 사용자 가설("되는 값 때려맞춤") 지지 증거

1. **DualCL 의 ablation 이 결정적**: capture 반경 0.12 m + evader 2.4배 빠름 regime 에서 **plain MAPPO 성공률 ~0%** → curriculum(과제-측 조작)으로만 회복. 즉 tight-feasibility regime 에서 naive distance/event MARL 은 붕괴하며, 기존 해법은 값을 완화하거나 curriculum 으로 우회 — **state-측 viability shaping slot 은 비어 있음** (N1 논지의 외부 방증).
2. Gavin & Bronz 성공 조건: 속도비 1:1 + net 을 수동 충돌체로 단순화(발사·단발 제약 제거) + 다회 시도 허용 — 단발성 infeasibility 를 모델에서 제거한 설정.
3. 대부분의 MARL P-E: capture = 관대한 거리 임계값(기체 스케일 대비 0.3–2 m), 이벤트 보상.

## 부수 소득

- **dwell 0.5 s 가 Zheng 2025 (arXiv:2503.06412) 에서 독립적으로 등장** — Huh dwell provenance 균열(P-6) 보강용: "0.5 s dwell 은 net-capture 커뮤니티의 독립 관례" 로 인용 가능.
- Gavin & Bronz 는 Pliska FRPN 을 baseline 으로 사용 — 우리 B-계열 비교표에 참조점 추가 가능.
- 주의: arXiv 2306.02482 "Aerial Swarm Defense using Interception and Herding" 은 Chipade & Panagou 본인 논문 (중복 계상 금지).
- paywall 로 수치 미확보: Xue 2025 본문, Zhang 2022 본문, MDPI Drones 8:524 — 필요 시 개별 확보.

## 타임라인 가속 결정 (2026-08-11)

서치 결과 슬롯 양옆에 ENAC/Thales(MARL+net, 발사모델 부재)와 Westlake(feasibility+협력, 학습 부재)가 근접 → **arXiv v1 을 URP 보고서(12/18)에서 분리, 최대한 앞당김**.

- 게이트: **Ablation A (B-3 vs B-4) 유의미 gap** — 이것 없이 아이디어만 공개하면 경쟁 그룹에 로드맵만 주는 역효과.
- 목표: mid-term(~9월 초) Ablation A 신호 확인 → 2~3주 집필(Def 1 + Ablation A 중심 4~6p) → **10월 초중 arXiv v1**. B-5 full/Fig 5/6 은 v2 로.
- 선행 조건: 교수님 컨펌 — "10월 arXiv 목표"를 다음 미팅 안건으로.
- KSAS 추계 트랙은 국내 스탬프로 별도 유지.

## 원출처 링크

Tier 1: [2607.05939](https://arxiv.org/abs/2607.05939) · [2503.06412](https://arxiv.org/abs/2503.06412) · [Zhang 2022](https://www.sciencedirect.com/science/article/abs/pii/S0094576522002764) · [Xue 2025](https://www.sciencedirect.com/science/article/abs/pii/S0925231225003157) · [2111.04474](https://arxiv.org/abs/2111.04474)
Tier 2: [2112.12288](https://arxiv.org/abs/2112.12288) · [2203.10142](https://arxiv.org/abs/2203.10142) · [2212.03228](https://arxiv.org/abs/2212.03228) · [2407.09645](https://arxiv.org/abs/2407.09645) · [Aerospace 11:684](https://doi.org/10.3390/aerospace11080684) · [2607.01029](https://arxiv.org/abs/2607.01029) · [2607.03554](https://arxiv.org/abs/2607.03554) · [2201.04180](https://arxiv.org/abs/2201.04180) · [2607.10986](https://arxiv.org/abs/2607.10986) · [2411.05454](https://arxiv.org/abs/2411.05454) · [Robotica kill-zone](https://www.cambridge.org/core/journals/robotica/article/adversarial-scenarios-for-herding-uavs-and-counterswarm-techniques/B01B030956256C13A0EE0AD88BCCD8EC) · [2303.01799](https://arxiv.org/abs/2303.01799)
파라미터: [DualCL PDF](https://nicsefc.ee.tsinghua.edu.cn//nics_file/pdf/a987def6-74db-4c3d-9a57-220cd7b9324f.pdf) · [2409.15866](https://arxiv.org/html/2409.15866v3) · [SAND2022-8554C](https://www.osti.gov/servlets/purl/2003782)
