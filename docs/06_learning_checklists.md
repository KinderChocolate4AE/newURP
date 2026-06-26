# newURP — 06 Learning Checklists

> `05_learning_goals.md`의 L1–L6를 잘게 쪼갠 체크리스트. **개념·용어**는 "한 문장으로 설명 가능"하면 체크 / **실습**은 "실제로 돌아가면" 체크. 각 L의 **✅ 완료 기준**을 채우면 그 milestone 졸업.

## L0 — 공통 엔지니어링 위생 (전 구간에 깔림)
**개념·용어**
- [ ] git: branch / commit / push / PR / merge
- [ ] `.gitignore` · `.gitattributes`(LF/CRLF) 역할
- [ ] venv/conda 가상환경, `requirements.txt`/`pyproject.toml`
- [ ] 재현성: seed · deterministic · config(yaml/hydra)
- [ ] 로깅 도구(wandb / tensorboard) 개념
- [ ] 단위테스트(pytest) · CI(GitHub Actions) 개념

**실습·경험**
- [ ] newURP venv 셋업 → `import shepherd` 통과
- [ ] pytest 1개 작성·통과 (예: env reset 결정론)
- [ ] wandb 프로젝트 만들어 더미 곡선 1개 로깅
- [ ] (선택) GitHub Actions로 pytest 자동 실행 + 뱃지

## L1 — Multi-agent ENV 바닥부터
**개념·용어**
- [ ] MDP / POMDP / **Dec-POMDP** 차이 (state vs observation)
- [ ] **CTDE** (centralized training, decentralized execution)
- [ ] Gymnasium API: `reset` / `step` / spaces(Box·Discrete) / `terminated` vs `truncated`
- [ ] **PettingZoo** Parallel vs AEC API
- [ ] reward 설계: sparse vs dense · potential-based shaping
- [ ] 이종 에이전트(역할별 obs/action) · permutation invariance
- [ ] 상대좌표/기준틀 (LOS, body vs world frame)

**실습·경험**
- [ ] 최소 단일-에이전트 env `reset`/`step` 구현 + render
- [ ] 다중 에이전트로 확장: limiter×N + finisher×1 + adversary×1
- [ ] 역할별 obs/action/reward 정의
- [ ] numpy `v_shot`(prototypes/reachset) → env reward/info 연결
- [ ] scripted 정책 rollout → **render GIF 1개**
- [ ] env 단위테스트(space 일치 · 결정론)
- [ ] **✅ L1 완료**: scripted 정책으로 에피소드가 끝까지 돌고 GIF가 나온다

## L2 — MARL 알고리즘 end-to-end
**개념·용어**
- [ ] policy gradient → REINFORCE → **actor-critic** → advantage → **GAE**
- [ ] **PPO**: clipped objective · ratio · KL · value loss · entropy · rollout/minibatch/epoch
- [ ] **MAPPO**: 공유 vs 비공유 파라미터 · centralized value(global state)
- [ ] **HAPPO/HATRPO**: sequential update · 단조개선 보장
- [ ] credit assignment + **COMA**(counterfactual baseline, 한 에이전트 action marginalize)
- [ ] on-policy vs off-policy · vectorized env

**실습·경험**
- [ ] PPO 코어 from-scratch 구현(단일) — 또는 한 줄씩 읽고 재현
- [ ] **MAPPO 코어 루프 직접 구현** (black-box 호출 금지)
- [ ] vectorized env로 병렬 rollout
- [ ] wandb: return / loss / entropy / KL 곡선 로깅
- [ ] checkpoint 저장·재개 · seed ≥ 3
- [ ] shepherd env에서 **수렴** (random/scripted 능가 = sanity floor)
- [ ] **COMA 차분보상**으로 limiter credit 구현
- [ ] MAPPO vs HAPPO(또는 baseline) 짧은 비교 run
- [ ] 디버깅 경험: 비수렴 / 보상 스케일 / NaN 중 1건 해결
- [ ] **✅ L2 완료**: seed 여러 개로 학습 곡선이 baseline을 유의하게 넘는다

## L3 — 평가 / ablation / 분석
**개념·용어**
- [ ] 통계: seed · **bootstrap CI** · effect size(Cohen's d/h) · 유의성
- [ ] **ablation** 설계 (한 변수만 격리)
- [ ] baseline 정의: no-shaping / selection-only / buy-nets / heuristic-ring
- [ ] reward hacking · sanity floor · 수렴 기준
- [ ] **exchange-frontier** · regime-map · Pareto front

**실습·경험**
- [ ] 공통 eval harness(seed·CI·metric) — WarSim harness 패턴 재사용
- [ ] baseline 4종을 같은 harness로 측정
- [ ] MARL rollout에서 **exchange-frontier**(P_penetration vs resource) 산출
- [ ] regime-map sweep (capacity × 속도/기동비)
- [ ] ablation 표 + CI
- [ ] reward-hacking 점검(E_req↓인데 P_capture 안 오름 탐지)
- [ ] paper-grade figure 2~3장(matplotlib)
- [ ] 한계절 정직하게 작성
- [ ] **✅ L3 완료**: "shaping이 frontier를 옮긴다"가 baseline 대비 CI로 보인다

## L4 — adversarial / self-play / robustness
**개념·용어**
- [ ] best-response · Nash · Stackelberg
- [ ] **self-play** 안정화: past-policy pool · league · PSRO · fictitious play
- [ ] curriculum learning
- [ ] OOD 일반화 · held-out 분포
- [ ] reactive 적(S13): bait → 뒤-옆 대각 급기동 → reload 타이밍 exploit

**실습·경험**
- [ ] reactive 적(closed-loop, `state` 소비) 구현
- [ ] self-play 루프(past-policy pool) + scripted fallback
- [ ] held-out 적 class(미학습 파라미터) 평가
- [ ] robustness: 적 강도별 성능 곡선
- [ ] 관측성 ablation (full / partial / hidden ammo)
- [ ] **✅ L4 완료**: 학습 정책이 미학습·반응형 적에도 frontier 우위 유지

## L5 — physical-AI 입문
**개념·용어**
- [ ] 6-DOF rigid body: **SE(3)** · quaternion/rotation matrix · body vs world · angular rate
- [ ] reduced-attitude / pointing control
- [ ] **sim-to-real gap** · domain randomization · system identification
- [ ] **ROS2**: node/topic/msg · pub-sub · NED vs ENU · px4_msgs
- [ ] **PX4** · **SITL** · **Gazebo** · MAVLink · EKF2
- [ ] cascaded control(pos→vel→att→rate) · RotorPy

**실습·경험**
- [ ] WarSim SE3 6-DOF rollout 돌려 동역학/제어 스택 이해
- [ ] policy↔sim **ROS2 메시지 계약(seam)** 정의
- [ ] PX4-ROS2-Gazebo SITL 설치 → 드론 1대 Gazebo 비행
- [ ] 학습 정책을 Gazebo SITL에서 **1 시나리오 spot-check**
- [ ] domain randomization 실험(파라미터 변동 → robustness)
- [ ] (stretch) HIL / 실기체 노출
- [ ] **✅ L5 완료**: 정책이 6-DOF SITL에서 한 시나리오라도 돌아간다

## L6 — capstone 신호
**개념·용어**
- [ ] 논문 구조(abstract / intro / related / method / results / limitations)
- [ ] arXiv · preprint · venue(conf / journal / workshop)
- [ ] 재현성 패키징 · 라이선스(MIT/Apache)
- [ ] 기술 글쓰기 · demo 제작

**실습·경험**
- [ ] 논문 섹션 초고 작성(05/04 docs 기반)
- [ ] 정책 **demo GIF/video** 제작
- [ ] repo 정리: README · "Fig X 재현" 스크립트 · requirements · tests · CI
- [ ] README/이력서/LinkedIn에 명명 역량 추가
- [ ] (우선권 결정 후) **arXiv preprint 공개** + repo public 전환
- [ ] (stretch) 블로그/스레드 1편 · 포스터/발표
- [ ] **✅ L6 완료**: public repo + preprint + demo가 한 링크로 보인다

---

## 이력서·포트폴리오 키워드 (채워질수록 체크)
- [ ] MARL (MAPPO · HAPPO · COMA) · PyTorch
- [ ] custom multi-agent Gymnasium/PettingZoo environment
- [ ] CTDE · self-play · credit assignment
- [ ] 6-DOF · sim-to-real · ROS2 · PX4 · Gazebo
- [ ] 통계적 평가 · ablation · 재현가능 오픈소스 repo
- [ ] 1저자 preprint + demo
