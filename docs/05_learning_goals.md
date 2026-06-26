# newURP — Learning Goals & Career-Signal Milestones

> 개발 트랙: **연구 프로젝트를 *통해* 수행**(별도 연습 아님). 목표 = (1) MARL 풀스택 end-to-end 구현, (2) physical AI 입문.
> 원칙: 연구 milestone(M1–M4)을 *의도적으로 + 가시적으로*(public repo·clean code·writeup·demo) 하면 **기여 + 논문 + 포트폴리오 + 역량**이 한 프로젝트에서 동시에 나온다.

## 학습 사다리 (연구 M1–M4에 매핑) — 각: 역량 / 산출물 / 신호

### L1 — Multi-agent ENV 바닥부터  [연구 M2]
- 역량: env 설계(obs/action/reward), 이종 역할, 6-DOF 동역학 통합(SE3 backend), Gym/PettingZoo API.
- 산출물: 동작하는 `shepherd` env + scripted 정책 rollout + render/gif.
- 신호: (교수) 연구 env를 정식화+구현 · (HR) "custom multi-agent RL environment 설계".

### L2 — MARL 알고리즘 end-to-end  [연구 M2/M3]
- 역량: CTDE, **MAPPO 핵심을 직접 구현**(black-box 아님), **COMA** credit assignment, HAPPO 비교; 학습루프·vectorized env·wandb 로깅·checkpoint·seed·재현성.
- 산출물: 수렴하는 학습 + learning curve; from-scratch MAPPO 모듈.
- 신호: (교수) 알고리즘 깊이 · (HR) "MAPPO/HAPPO + COMA를 PyTorch로 직접 구현" — 최상위 RL-engineer 신호.

### L3 — 평가/ablation/분석 엄밀성  [연구 M3]
- 역량: 통계(seed·bootstrap CI), ablation(no-shaping/selection/buy-nets baseline), 수렴·reward-hacking 진단, exchange-frontier·regime-map 분석, 정직한 한계.
- 산출물: 실측 exchange-frontier + ablation 표 + figure.
- 신호: (교수) 연구 방법론+정직 과학 · (HR) "엄밀한 실험 평가·ablation·통계 분석" + figure.

### L4 — Adversarial / self-play / robustness  [연구 M3, S13]
- 역량: reactive best-response 적, self-play 안정화, OOD/held-out 평가.
- 산출물: reactive·self-play 적 상대 결과 + robustness study.
- 신호: (교수) best-response bar 통과 · (HR) "self-play, adversarial robustness".

### L5 — Physical-AI 입문  [Paper-2/lab 방향]
- 역량: 6-DOF rigid-body, **ROS2 메시지 계약**(state/setpoint/sensor), **PX4-ROS2-Gazebo SITL**, domain randomization/reality-gap, 랩 스택.
- 산출물: policy↔sim ROS2-interface seam + Gazebo/PX4 SITL spot-check(시나리오 1개라도).
- 신호: (교수/랩) physical-AI + 랩스택 능숙 · (HR) "sim-to-real, ROS2, PX4/Gazebo" — robotics+RL 수요 조합.

### L6 — Capstone 신호  [연구 M4+]
- 역량: 기술 글쓰기, demo 제작, 발표.
- 산출물: arXiv preprint + **public GitHub repo**(clean·재현가능·README·results) + **demo GIF/video** + poster/짧은 talk.
- 신호: (교수) 실제 게재 가능 기여 · (HR) 포트폴리오 핵심 — 1저자 preprint + 오픈소스 repo + demo.

## 평가자별 매력 포인트

- **교수 / advisor**: 깊이(정식화+알고리즘을 *직접 소유*) · 엄밀 방법론(seed/CI/ablation/정직한 한계) · 진짜 novel 기여 + preprint · 독립적 프로젝트 추진.
- **조교 / 연구실 동료**: 랩스택 능숙(ROS2/PX4/Gazebo) · 남이 돌릴 수 있는 재현가능 코드 · 협업·온보딩 용이 · 하드웨어 역량.
- **HR / 리크루터 (robotics+RL / physical-AI)**: **삼박자** — (1) 클릭 가능한 *public 포트폴리오*(GitHub: clean code+README+재현 결과+demo), (2) 수요 키워드 역량(MARL/MAPPO/PyTorch/Isaac/Gazebo/ROS2/sim-to-real), (3) *end-to-end 소유*("env→algorithm→train→eval→deploy") + preprint · 그리고 명료한 커뮤니케이션(writeup/demo).

## 매력 증폭기 (싸고 신호 큰 것)

- 학습된 shepherding 정책 **demo GIF/video** (리크루터가 제일 좋아함).
- "**이 명령으로 Fig X 재현**" — 재현성 = 즉각 신뢰.
- README·이력서에 **명명된 역량**(HR 키워드 스캔 대응).
- **preprint**(워크샵이라도) — 학부생 최강 신호.
- 아이디어 설명 **블로그/스레드** 한 편.
- **단위테스트 + CI** 뱃지 — 엔지니어링 위생.
- **발표 시점에 repo public 전환**(우선권 확보 전엔 private).

## 잊지 말 원칙
실제 프로젝트를 이 신호들을 *방출*하도록 instrument 하라. 연구 M1–M4 각각에 쌍둥이 학습 L1–L6 —
같은 일을 *가시화*. 한 프로젝트로 기여·논문·포트폴리오·풀스택 MARL+physical-AI 역량을 동시에 졸업.
