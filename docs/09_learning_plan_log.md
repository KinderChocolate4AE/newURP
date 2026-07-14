# 09 — L2 Learning Plan & Log (MARL: MAPPO + COMA)

> **한 파일 = 플랜 + 로그.** §0–§7 = 살아있는 계획(수정 OK), §8 = append-only 작업 로그(위가 최신).
> **범위:** L2 (MARL end-to-end). 전제 = L1 + S14/N1 prep 완료 (`feat/l2-prep-wiring`).
> **소유:** 코어(게임·reward·shaping 유도·결정) = Hyunjun / AI = 구현·scaffold·디버그 보조.
> **모드:** BUILD-first (`04_action_plan.md`) — 계획·검증보다 돌아가는 것. 검증은 time-box.

---

## 0. 한눈에

- **목표:** scripted 정책 → **학습된 shaping 정책**. MAPPO **직접 구현**(black-box 금지) + **COMA** limiter credit. CTDE.
- **동결(건드리지 않음):** S1–S8 계약(`03_formalization.md`), env 계약(`shepherd/env.py`), `configs/m2_l2_train.yaml`, frozen blob 2개(`03_formalization.md`, `shepherd/game/exchange.py`). **유일 비준 예외(2026-07-03, §8 (d)):** env.py step() 내 batched-eval call-site 1건 — **2A에서 구현·커밋 완료(`e99ff34`, §8 (e))**, equiv lock = `tests/test_batched_eval.py`.
- **L2 산출:** seed≥3 수렴 학습곡선 > baseline + wandb 곡선 + checkpoint + demo GIF.
- **현 위치:** **Phase 1 완료(2026-07-01)** + **Phase 2A′ 완료(2026-07-03, §8 (d)).** from-scratch PPO 코어(`52a7d58`) → 2A′ 스파이크: 병목 = MC 빌드가 아니라 **per-layout eval E×7회**; **DoD(벽시계) PASS**(베이스라인도 16w≈2.9h<4h, batched 채택 시 1.5h); 비준 = **batched-eval만 env.py 동결 예외 승인(구현은 2A)** + **n_samples 2000 유지**(near-gate err 근거). **Phase 2A 완료(2026-07-03, §8 (e); `e99ff34`+`b3ff97e`):** batched-eval 구현(실측 **117→54.4ms/step, 2.16×**) + torch-free 어댑터 smoke 6종 green. **Phase 2B 트레이너 구현 완료(2026-07-03 (g), `54dfdeb`)** — §7.1 이월(obs normalizer·γ/λ 0.99/0.95)·fire **Bernoulli head 확정**·wandb·공격자 가족 랜덤화 config 전부 반영. **run 1 완료(2026-07-04, §8 (h)):** 서버 bring-up V1–V4 green → 3-seed×200k — seed1/2 margin **+5.44/+6.74** 수렴(비용-인지 셰이핑), seed0 진동 끝 −0.66 → **DoD 2/3 미통과**. 안정화 레시피(`cef170f`) → **run 2(§8 (i)): 3/3 seed last3_margin +2.64/+5.79/+2.59 — ✅ Phase 2B DoD 통과·마감(2026-07-04).** **✅ Phase 2C 완료(§8 (k), `be816f9`): MAPPO 6-seed vs_ippo 평균 +2.32 (9.05 vs 6.73), 6/6 초과** — 차단+셰이핑 결합 모드 발견(headline 13.5 > scripted 10.06). clean crossing 여전히 0 → **2D 트레이너 구현 완료(§8 (l), `df41dd8`: 해석적 D 배선 + recipe-v2)** — **다음 = 2-arm 캠페인**(mappo_run2 = recipe-v2 기준선 3-seed / coma_run1 = +COMA 3-seed, 6-proc 병렬 ~6h). **✅ 2D run 1 마감(2026-07-05, `387b4c6`): DoD-1 PASS(coma_D 全 seed 全 구간 양수) / DoD-2 FAIL(vs_mappo 평균 −1.40, 10.40 vs 11.80) / DoD-3 PASS** — mix=1 비용-실명 정량 확인(cost-gap 1.85 vs 3.0~5.1) + D-credit=차단 모드 발견 가속(2/3 vs 1/3, coma s0 peak_roll3 +16.90 역대 최고) → **폴백 arm mix 0.5 준비 완료(`l2_coma_mix05.yaml`), 착수 대기.** **✅ 2D run 2(mix=0.5) DoD 3/3 PASS → Phase 2D 마감(2026-07-05, `4b3c708`): vs_mappo 평균 +2.20(14.00 vs 11.80)·seed1 last3 +16.67 역대최고·차단 모드 3/3·mix 역-U {0: 11.80, 0.5: 14.00, 1.0: 10.40} → 다음 = Phase 4·5 마감 + L2 게이트 판정(D2-A).** 상태 총정리·피어리뷰 브리프 = **§9**(자기완결, 외부 리뷰 export용). **✅ P1 캠페인 완료(2026-07-06~07, results `52e0046`) → L2 게이트(D2-A) 본판정 PASS(사전등록 규칙: 양 arm margin 하한 +10.2~+15.7 > 0) + paired 분리 coma−mappo +1.91 CI[+0.83,+3.13](10-seed, 9/10 양수) → main recipe = mix 0.5 — 비준 대기. 신규: seeds 7·8 양 arm "발사 모드"(매판 게이트 도달·boxed 미스·조기 종료) — clean 조건만 잔여.**

---

## 1. 핵심 결정 (D1–D3 확정 2026-06-30)

> **2026-06-30 확정: D1=A, D2=A, D3=A.** 아래 표는 비교·근거 기록용. 플랜 단계(§3–6)가 이 결정 기준으로 고정됨.

### D1. COMA 구현 방식 — **A 확정** `[CONFIRMED 2026-06-30]`

env가 이미 v_shot 기반 **해석적** `coma_D`를 timestep마다 info로 내보냄(`env.py` step). 이걸 어떻게 쓸지.

| 옵션 | 이력서/연구 신호 | 난이도·수렴 | 비용 | 비고 |
|---|---|---|---|---|
| **A. 해석적 먼저 → 학습 critic 나중 (채택)** | 최종 강(둘 다 경험) | 중(점진) | 중 | 1단계=C와 동일, 2단계가 B를 흡수 → **"둘 다"의 상위호환** |
| B. 처음부터 학습된 COMA critic | 강("COMA 직접 구현") | **높음**(디버깅·수렴) | 높음 | 초기 sanity 느려짐, BUILD-first와 마찰 |
| C. 해석적 D_i만 | 약(알고리즘 신호 X) | 낮음 | 낮음 | 가장 단순·안정, 학부 신호로는 약함 |

**근거:** BUILD-first. **A-1단계**(해석적 D_i를 limiter advantage로 바로 사용)로 빠르게 수렴 확인 → **A-2단계**(학습된 counterfactual critic으로 교체)로 이력서 신호 확보. Phase 3이 A-1, A-2는 Phase 6 이후 stretch.

### D2. L2 "완료" 기준 — **A 확정** `[CONFIRMED 2026-06-30]`

| 옵션 | 결과 강도 | 도달 위험 | 문서 정합 |
|---|---|---|---|
| **A. baseline 유의 초과 = lever 졸업 (채택)** | 중 | 낮음 | `06_checklist` L2 정의·`03 §C` DoD와 일치 |
| B. + physical capture(2.0m)까지 L2 안에 | 강 | 높음(미달) | DoD 확장 |
| C. capture(2.0m) 단독 헤드라인 | 강 | 높음 | `03`(M2=lever, capture=금지선)과 충돌 |

**근거:** `03 §C` M2 DoD = `u_L≠u_L⁰ ⇒ Δv_shot>0 ∧ threshold crossing w/ fewer wasted`. **A를 L2 게이트**로, **physical capture(shaped reachable 2.4→<2.0m)는 M3 stretch/헤드라인**으로 분리(= 사실상 단계적). capture를 L2에 묶으면 미달 시 졸업 불가 리스크.

### D3. 실행 환경 — **A 확정** `[CONFIRMED 2026-06-30]`

| 옵션 | 유연성 | 셋업 복잡 | 랩 정합 |
|---|---|---|---|
| **A. 로컬-우선 + 랩 이식 (채택)** | 높음 | 중 | 높음 |
| B. 로컬 GPU만 | 중 | 낮음 | 중 |
| C. 랩 서버/클러스터(ssh)만 | 중 | 높음(ssh/slurm) | 높음 |

**근거:** config·venv로 환경 독립 유지 → 로컬에서 빠르게 디버그, 랩으로 scale. §3은 A 기준으로 작성, 랩 변형 단계 병기. **공통 제약: torch는 이 샌드박스에서 못 돌림 → 모든 학습은 로컬/랩, 샌드박스는 torch-free 테스트 전용.**

---

## 2. 동결 계약 요약 (trainer가 plug-in 하는 자리)

> 전체는 `03_formalization.md`(S1–S8) · `shepherd/env.py` · `configs/m2_l2_train.yaml`. trainer는 이걸 **읽기만** 함.

**게임(S1–S8, 2026-06-26 비준·동결)**

- S1: limiter N + SE(3) finisher 1 + 적 1. binding 자원 = finisher K-shot. **M2: K=1, 적은 scripted(학습 X).**
- S4: **CTDE** — full-state 학습 / local 실행. fire = 물리적 commitment(시그널링 X).
- S6: `J_M2 = Δv_shot + λ1·1[v≥θ_fire] − λ2·wasted_fire − λ3·limiter_loss`. **경제 frontier 주장 금지(M3).**
- S8: shaping 채널 3개(reachable 압축 / net-volume 정렬 / threshold 탄약보존), credit = **COMA D_i, baseline u_i⁰ = hold_position 고정**.
- §C DoD: `u_L≠u_L⁰ ⇒ Δv_shot>0 ∧ wasted 안 늘고 threshold crossing`.

**env 계약(`shepherd/env.py` — 완성)**

- PettingZoo ParallelEnv. agents = `limiter_0..N-1` + `finisher_0` + `adversary_0`.
- **obs**(전 에이전트 공유, full-state): `Box(dim = 9·N_max + 9 + 9 + 6 + 3)` = [limiters 9씩, finisher 9, adversary 9, FSM(k_norm+phase4+timer)=6, vres(soft,worst,p_feasible)=3].
- **CTDE 서술 주의(2026-07-03 정직화):** 전 에이전트 obs = **동일 full-state** → 현 M2는 *실행도* 공유-관측(중앙화)이며, S4(frozen 03)의 "decentralized/local 실행"은 local-obs 마스크 **미구현** 상태로는 문자 그대로 성립 안 함. 03은 diff 0이라 여기 명기: **논문 서술 = "CTDE + 공유 full-state 관측(실행은 역할별 파라미터-공유 정책)"으로 정직하게**; local-obs 마스크/관측성 ablation(S11 연계) = **2C 이후 stretch**. 부작용 캐비앗: full-state obs라 2C(MAPPO 중앙 critic)의 2B 대비 이득이 작게 나올 수 있음 — ablation 서사로는 유리, 기대치만 조정.
- **action**: limiter `Box(4) = [accel x,y,z | pressure=RESERVED]` / finisher `Box(5) = [axis x,y,z | slew=RESERVED | fire]` (fire>0.5=발사, 비가역 — env는 `fin_act[4]`를 읽음) / adversary `Box(accel 3)`. **RESERVED(2026-07-03 결정, Hyunjun):** limiter `pressure`(idx 3)·finisher `slew`(idx 3)는 **env가 수신-무시** — env.py 동결 유지(구현/제거 대신 reserved 명시). 학습기는 live 차원만 출력(limiter 3 / finisher 4=axis+fire)하고 `shepherd/train/make_env.pad_env_action()`이 reserved 인덱스에 0 패딩 → MARL 무의미 탐험 차원 차단.
- **reward**: limiter·finisher = `+J`, adversary = `−J`. info: limiter별 `coma_D`, finisher `delta_v_shot_headline`. **CRN 정확상쇄(코드에만 있던 것 문서화):** headline·coma_D는 step_seed 공유 — `n_segments>1`이면 layout-독립 reachable **union을 1회 구축** 후 limiter 마스크만 교체(정확 상쇄, ~(N+2)× 절약, `tests/test_union_equiv`), `n_segments=1`이면 동일 accels 재사용.
- **중앙 critic 입력**: `env.state()` (전 kinematic state concat) 제공됨.
- **종료**: captured / penetrated / spent_fail. **truncation**: `episode_len=80` — **2026-07-03 config 핀:** `m2_l2_train.yaml`의 `train.episode_len=80`(그 전엔 Layout dataclass 기본값에만 존재, demo 루트 `rollout_gif.build_env`는 70). **학습 env 조립은 반드시 `shepherd.train.make_env.make_train_env(cfg)` 경유**(strict: episode_len·layout·limits·cone 핀 누락 시 raise; demo 루트 재사용 금지).

**학습 config(`configs/m2_l2_train.yaml`)**

- n_limiters=4, K=1 / dt=0.05, τ_deploy=0.4, a_att_max=30, att_speed=20, kill_radius=2.0, **net_radius=2.0(N1-grounded)**, a_lim_max=30.
- **viability: n_segments=4 (S14 보수 신호로 학습)**, judge=se3_cone, n_samples=2000, cone half_angle=0.067 / range_max=29.847.
- θ_fire=0.9 / λ=(1, 1, 0.5) / COMA·headline baseline = hold_position.
- **reserved key:** `viability.turn_limited` = **parsed-but-inert**(ScenarioSpec은 읽지만 env의 v_shot 경로에 미배선 — 사실상 항상 False; viability.py는 `attacker_turn_limited` 이미 지원, wire-through는 S13/S14 활성화 시). `train:` 블록(2026-07-03 추가) = 컴포지션 핀 전용(episode_len/layout/limits) — ScenarioSpec은 무시, 비준값 무변경.

---

## 3. 환경 세팅 (Phase 0a)

> 전제: **lab/local torch venv**(샌드박스 torch 불가). 채택 D3-A = 로컬-우선 + 랩 이식.

**3.1 로컬 venv 설치**

```bash
git clone https://github.com/KinderChocolate4AE/newURP.git    # 또는 기존 클론에서 git pull
cd newURP
python3.10 -m venv .venv && source .venv/bin/activate          # py>=3.10 (pyproject)
# torch: 기본 휠이 최신 CUDA 자동 (대개 그냥 동작); 특정 CUDA 필요시 --index-url .../cuXXX 로 교체
pip install torch
pip install -e ".[env,viz,marl,dev]"   # shepherd + numpy/pettingzoo/gymnasium/matplotlib/supersuit/wandb/pytest
```

**3.2 sanity 체크 (설치 직후 1회)**

```bash
python -c "import shepherd, torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available())"
python -m pytest -q          # 기존 31 (torch-free) green — 회귀 없음 확인
python -m shepherd.scripts.rollout_gif --config configs/m2_l2_train.yaml   # env+config 동작 확인
```

**3.3 의존성 고정 (커밋 대상)**

- **DONE (2026-06-30):** `marl` extra = `["torch","supersuit","wandb"]`로 갱신 + `requirements.txt` 동기화 → `pip install -e ".[env,viz,marl,dev]"` 한 줄로 전체 설치.

**3.4 랩 이식 변형 (D3-A/C)** — 랩 컴퓨터 정보 입수 후 구체화

- 랩 서버 ssh → 동일 `python3.10 -m venv` 절차. CUDA/드라이버 버전 확인 후 torch 빌드 교체.
- 장시간 run = `tmux`/`nohup` 또는 (클러스터면) slurm 배치 `scripts/train.sbatch`(후속).
- 환경 독립 유지: 경로·디바이스는 config/CLI 인자로만(`--device cuda`), 코드 하드코딩 금지.
- **필요 정보(TBD):** GPU 모델+CUDA/드라이버, OS(우분투)·가용 Python, ssh 접속·단일서버 vs slurm, 저장경로·공유 FS, wandb 외부접속(오프라인 모드?).

---

## 4. GitHub 세팅 (Phase 0b)

> 리모트 존재: `KinderChocolate4AE/newURP`. `.gitignore`가 `*.pt`/`checkpoints/`/`runs/`/`wandb/` 이미 커버. `.gitattributes` eol=lf.

**4.1 브랜치 정리** (로컬에서 실행 — 샌드박스는 `.git/index.lock` 권한으로 git 불가)

```bash
del .git\index.lock                                  # stale lock 제거 (Windows)
git switch main && git merge --no-ff feat/l2-prep-wiring   # prep 검수 후 main 머지
git push origin main
git switch -c feat/l2-mappo-train main                # L2 작업 브랜치 분기
```

**4.2 CI — `.github/workflows/ci.yml`** (torch-free 31 테스트를 push/PR마다 자동 실행)

- **DONE (2026-06-30):** 아래 레시피로 생성(ASCII 주석). py3.10 + `.[env,viz,dev]`(torch 없이) → `pytest -q`.

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.10" }
      - run: pip install -e ".[env,viz,dev]"   # torch 없이 (game/env/viability 테스트는 torch-free)
      - run: python -m pytest -q
```

- trainer 테스트(torch 필요)는 추후 CPU torch step 분리 또는 `@pytest.mark.torch` 별도 job. 초기엔 torch-free job만.

**4.3 시크릿·아티팩트 위생**

- `WANDB_API_KEY`는 **로컬 env / GitHub Secrets**로만. 코드·config 커밋 금지(`wandb/`는 이미 ignore).
- 체크포인트(`*.pt`/`checkpoints/`)·`runs/`는 ignore 유지 → 레포 미포함. 공유는 wandb artifact/릴리스.

**4.4 (선택) 위생 강화** — main branch protection(PR+CI green), README CI 뱃지, dependabot(후순위).

**4.5 mount git 규율 (중요)**

- ANDES 마운트 간헐적 truncation → `git add` 후 **staged blob 검증**(`git show :path | tail`/size), BAD면 bash heredoc 재기록 후 재-add. `/tmp` 휘발·root 없음. (이번 세션도 requirements/pyproject/09-doc truncation 발생 → heredoc/재기록으로 복구.)

---

## 5. 액션 플랜 (Phase 1–6) — BUILD-first

> 각 Phase = **동작하는 산출물** + DoD + 커밋. 채택안 A/A/A. 스위트는 매 커밋 green(baseline 59 → Phase 1 후 **72 수집 = torch-free 65 + torch-marked 7**; torch 7은 로컬/랩 venv 전용 — "torch-free 72"로 적었던 과거 표기는 부정확, §8 2026-07-03 정정), frozen blob diff 0.

### Phase 1 — PPO 코어 (단일 에이전트, from-scratch) ✅ **DONE (2026-07-01, `52a7d58`)**

- **할 일:** `shepherd/train/ppo.py` — actor-critic, GAE, clipped objective, value/entropy loss, rollout/minibatch/epoch. Gaussian 연속 정책. → **완료.**
- **sanity 환경:** Gymnasium 토이(Pendulum-v1) — env 무관하게 코어 검증. → **완료.**
- **DoD:** 토이에서 return 수렴(랜덤 초과) + seed 고정 재현. → **충족.** eval return seed 0/1/2 = **−131.4 / −185.8 / −156.4** (random ≈ −1200…−1600); seed 0 독립 2회 −131.4(CPU deterministic).
- **커밋:** `feat(train): from-scratch PPO core + toy convergence` (`52a7d58`).
- **산출 파일:**
  - `shepherd/train/gae.py` — **torch-free** numpy GAE + adv-norm. per-step `next_values`로 truncation=`V(final_obs)` / termination=0 부트스트랩(shepherd가 truncation-dominant라 핵심).
  - `shepherd/train/ppo.py` — `ActorCritic`(분리 MLP, **state-independent** Gaussian log-std), `RolloutBuffer`(raw+clip action 분리 저장→ratio 정확), `PPOConfig` dataclass, `PPOTrainer`(clipped surrogate + **plain MSE** value(clip 생략) + entropy, **rollout-level adv-norm 1회**, grad clip, **checkpoint save/load**).
  - `shepherd/scripts/train_ppo_toy.py` + `configs/ppo_toy.yaml` — config/CLI 주도, **plain env + manual reset**(autoreset 모호성 회피, Phase 2 PettingZoo로 전이), deterministic eval, 곡선+weights 저장. `results/ppo_toy/`.
  - `tests/test_ppo_gae.py`(torch-free 6) + `tests/test_ppo_update.py`(`importorskip`+`@pytest.mark.torch` 7). `pyproject.toml`에 `torch` 마커 등록.
- **확정된 설계 결정(사용자 승인):** state-independent log-std / value-clip 생략 / action **clip**(log-prob는 raw Gaussian 기준, exact ratio) / adv-norm **rollout-level 1회** / raw·env action 분리 / `compute_gae` **per-step next_values 시그니처** / update 테스트는 "loss 감소" 대신 구조 불변식(finite·ratio≈1·param-move·KL≥0·grad-clip).
- **리스크(해소):** advantage 정규화·보상 스케일 → 토이에서 확인 완료. gymnasium 1.3.0 autoreset("next-step" mode) → plain env+manual reset로 회피(프로브로 확인).

### Phase 2 — single-agent PPO → MAPPO 사다리 (shepherd env, CTDE) `[재구성 2026-07-01]`

> **Phase 1 PPO 코어를 최대 재활용하며 리스크를 한 계단씩 격리.** 부산물로 **IPPO(2B) / MAPPO(2C) / MAPPO+COMA(2D)** ablation 사다리가 나옴 → §5 Phase 6 baseline 비교표로 그대로 재사용(중복 작업 0). 각 rung = 동작 산출물 + DoD + 커밋. 스위트 매 커밋 green(현 torch-free 65 + torch 7 = 72 수집), frozen blob diff 0.
>
> **이종(heterogeneous) 못박기:** env는 4 limiter(`Box(4)` accel+pressure[RESERVED]) + 1 finisher(`Box(5)` axis+slew[RESERVED]+**fire**) + scripted adversary. "N-agent 완전 공유 정책"은 **틀림** — limiter만 파라미터 공유, finisher는 별도 정책, adversary는 학습 X.

#### Phase 2A — shepherd env 어댑터 smoke ✅ **DONE (2026-07-03, §8 (e) — `e99ff34`+`b3ff97e`)**

> **결과 요약:** batched-eval 구현(additive `viability.eval_union_with_limiter_sets` + env.py call-site 1건, +29/−10) → **실측 54.4ms/step(2.16×)**, equiv lock 5종(스왑 전 green→스왑 후 green). 어댑터 `shepherd/train/adapter.py`(torch-free) + smoke 6종. DoD 캐비앗: random 정책은 ~23스텝 자연종료(penetrated) — 80스텝 truncation은 test-only episode_len 오버라이드로 검증; fire 스팸은 R2 게이트 전량 기각(commit 체인 = 2B+). 원래 계획(아래)은 기록용.


- **(선행 DONE 2026-07-03)** 컴포지션 루트 `shepherd/train/make_env.py`: `make_train_env(cfg)`(strict config 핀 — episode_len 80·layout·kinematic limits·cone, 누락 시 raise) + `LIVE_DIMS`/`live_action_dim`/`pad_env_action`(reserved-dim 0 패딩) + `tests/test_make_env.py` 8종(torch-free). 어댑터는 이 루트 위에서 시작 — `rollout_gif.build_env`(demo 70) 재사용 금지.
- **할 일:** PettingZoo ParallelEnv ↔ trainer 어댑터. dict obs flatten, agent별 action 라우팅(limiter/finisher/adversary; live-dim 정책 출력 → `pad_env_action`), reward·info(`coma_D`/`delta_v_shot_headline`) 추출, `env.state()` 배선. adversary는 scripted 주입.
- **(추가 2026-07-03, 2A′ 비준)** **batched-eval 반영:** additive `viability.eval_union_with_limiter_sets`(가칭) + `env.py` step() 내 6-eval call-site 1건 교체 — env.py 동결의 **비준된 유일 예외**. 조건: 기존 `eval_union_with_limiters` 대비 **비트-동일 equiv 테스트 lock**(스파이크에서 12상태 mismatch 0 선검증). obs-lite는 보류(비준 안 됨).
- **DoD:** **random 정책**이 full episode(`episode_len=80`) NaN 없이 완주 + obs/action/reward/info 배선 검증(shape·키). torch-free 스위트 green.
- **커밋:** `feat(train): shepherd ParallelEnv adapter smoke (random policy)`.

#### Phase 2A′ — v_shot throughput 스파이크 ✅ **DONE (2026-07-03, §8 (d) — 측정-전용, frozen 전부 diff 0)**

> **결과 요약:** 병목 = per-layout 거리마스크 **eval E≈14ms×7회/step**(빌드 B≈3.6ms 아님). ① n 축소는 near-gate에서 위험(n=500 err_max 0.190 > zero-waste 밴드폭 0.15) → **n_samples 2000 유지 비준**; ⑤ **batched eval**(unique 리미터 8개 공유, 비트-동일 2.4×) 신규 발견 → **env.py 동결 유일 예외로 비준, 구현 = 2A**; ② cadence는 batched 채택 시 무의미 → 미구현; ③ 2-way eff 0.83 실측. **DoD(벽시계 경로) PASS.** 상세 = `results/spike_throughput/spike_results.md`. 원래 계획(아래)은 기록용.

- **왜 승격:** 실측 **~133 ms/step**(샌드박스 CPU, n_segments=4 · n_samples=2000 · per-step coma_D 포함) → 1e6 step ≈ **37 h/단일 env**. MAPPO 통상 1e6–1e7 step이라 현 상태로는 학습 불가 수준 — 원래 2C에서 물기로 했으나 **2B(IPPO)도 같은 env를 쓰므로** 2A 직후로 당김.
- **순서(정확도-속도 trade 측정과 함께):** ① `n_samples` 축소 스윕(CRN 유지; v_shot 분산·판정 일치율 체크) ② `coma_D` 계산 주기화(매 스텝 → k-스텝마다; S8 계약은 baseline 고정만 요구) ③ supersuit 병렬 env. **S14 보수-신호 계약 때문에 `n_segments` 축소는 최후 수단.**
- **DoD:** steps/sec **≥10×** 또는 "1e6 step ≤ 4 h(병렬 포함)" 경로 확보 + 정확도 열화 측정 기록.
- **(2026-07-03 갱신)** 학습은 **LiCS 랩 서버** 사용 확정 → ③ 병렬 env의 코어 여유 ↑, DoD 벽시계 경로는 서버 코어 수 기준 재산정. 단 ①(n_samples)·②(coma_D 주기화)는 **디버그 반복속도**(로컬 단일 env 루프) 때문에 여전히 유효 — 스파이크 자체는 유지.
- **커밋:** `perf(env): v_shot throughput spike (n_samples sweep, coma_D cadence, vectorization)`.

#### Phase 2B — IPPO (independent PPO, 중앙 critic 없음) ✅ **DONE (2026-07-04, §8 (i) — run 2 `f7ae506`: 3/3 seed last3_margin > 0)**

- **할 일:** Phase 1 PPO 코어를 agent별로 굴림 — **limiter = 파라미터 공유 1개 정책**(homogeneous 역할) + **finisher = 별도 정책**, 각자 **decentralized critic**. = 진짜 IPPO(MARL 표준 baseline·selection-only ablation).
- **혼합 action head 확정(여기서 close):** finisher `fire`(binary·비가역) — **Bernoulli head 권장**(fire만 분리 Bernoulli, 나머지 연속 Gaussian) vs Gaussian+threshold → 2B에서 결정·기록. §7.1 오픈항목 해소.
- **로깅:** wandb 여기서부터 켬(return / loss / entropy / KL + `Δv_shot`/`wasted_fire`/`limiter_loss`). checkpoint = Phase 1 `PPOTrainer.save/load` 재사용.
- **DoD:** IPPO return이 hold_position·scripted baseline **유의 초과**(≈ selection-only baseline, 사실상 L2 게이트 근접). NaN 0.
- **커밋:** `feat(train): IPPO (shared-limiter + separate finisher, decentralized critics)`.

#### Phase 2C — MAPPO (중앙 critic, CTDE) ✅ **DONE (2026-07-05, §8 (k) — 6-seed vs_ippo 全 양수, 평균 +2.32)**

- **할 일:** 2B 위에 **중앙 critic 1개**(`env.state()` 입력)만 추가 → CTDE. actor는 2B 그대로(decentralized 실행).
- **throughput:** ~~여기서 물림~~ → **2A′로 승격(2026-07-03, 실측 133 ms/step 근거)**. 2C에서는 잔여 튜닝(중앙 critic 추가 비용 측정)만.
- **DoD:** MAPPO return **≥ 2B(IPPO)** + 학습 안정(NaN 0, KL 정상). torch-free green.
- **커밋:** `feat(train): MAPPO (shared central critic, CTDE) on shepherd env`.

#### Phase 2D — COMA limiter credit ablation (D1-A 1단계) — 🔧 **트레이너 구현 완료(2026-07-05 (l), `df41dd8`); 2-arm 캠페인 = 랩 서버**

- **할 일:** env의 `info[limiter_i]["coma_D"]`(**해석적** v_shot 차분)를 **limiter advantage**로 배선. baseline = hold_position(고정, S8). = 기존 Phase 3, "ablation"으로 프레이밍.
- **DoD:** `D_i` 평균 > 0(역할 검증·kill-switch 연동) ∧ **MAPPO+COMA ≥ MAPPO** ∧ `Δv_shot>0` 유지. terminal-only 보상 금지.
- **커밋:** `feat(train): COMA difference-reward credit for limiters (analytic D_i)`.
- **D1-A 2단계(Phase 6 이후 stretch):** 학습된 counterfactual critic으로 D_i 대체 → "COMA 직접 구현" 이력서 신호.

**ablation 사다리 = baseline 재사용:** 2B(IPPO) / 2C(MAPPO) / 2D(+COMA) 곡선이 그대로 Phase 6 비교표(no-shaping / selection-only / MAPPO / +COMA)로 들어감.

### Phase 4 — 재현성 마감 (벡터화·로깅은 2B/2C로 선반영)

> **2026-07-01 재구성:** wandb 로깅·checkpoint = **2B로**, supersuit 벡터화·`v_shot` throughput 튜닝 = **2A′/2C로** 당김. Phase 4는 잔여 마감만.

- **할 일:** seed≥3 배치 실행 표준화 + checkpoint resume **동일 궤적** 검증(2B save/load 위) + wandb 곡선 정리(2B에서 켠 로깅). (미당겼으면 여기서 supersuit 벡터화 마감.)
- **DoD:** 3 seed 배치 + checkpoint resume 동일 궤적 + wandb 곡선 완비.
- **커밋:** `feat(train): reproducibility pass (seed>=3, checkpoint resume, wandb)`.

### Phase 5 — 조기 sanity (`03 §D`, build 안 1회)

- **할 일:** shaping on/off `Δv_shot` 차이 + 학습 정책이 hold_position·scripted baseline 초과하는지 1회 확인.
- **DoD:** `Δv_shot>0`이 noise 이상(kill-switch 통과). 음성이면 **즉시 재고**(보상/credit/관측).
- **커밋:** 결과 §8 로그 + `results/` 곡선.

### Phase 6 — 수렴 → L2 게이트 (D2-A)

- **할 일:** seed≥3 본 학습. baseline 4종(no-shaping=finisher 단독 / selection-only / fixed-formation / hold) 비교. (옵션) HAPPO 짧은 비교.
- **✅ L2 완료 게이트(D2-A):** **seed≥3 학습곡선이 baseline 유의 초과**(J·Δv_shot). demo GIF 1개.
- **커밋:** `feat(train): converged shaping policy > baseline (L2 gate)` + `results/` 곡선·GIF.
- **다음:** L3(exchange-frontier·regime-map·ablation) / D2-B physical capture(2.0m)=M3 헤드라인.

---

## 6. 게이트 & kill-switch 연동 (`03 §F`)

| 가정 | M2 반증 조건 → 트리거되면 |
|---|---|
| deploy-delay shaping | `Δv_shot` on/off가 noise 수준 → shaping 채널/보상 재고 |
| limiter 역할 | COMA `D_i ≈ 0` → limiter 무용, 역할/관측 재설계 |
| finite-shot value | fire threshold crossing이 direct pursuit 대비 차이 X |
| SE(3) net viability | point_mass는 좋아 보이나 se3_cone judge에서 붕괴 |

- **L2 게이트(D2-A):** §5 Phase 6 = seed≥3 baseline 유의 초과.
- **검증 time-box:** 통계 경량(seed≥3 + CI). 적대 audit·probe 의식화 금지(`04` 운영규칙).

---

## 7. 리스크 / 오픈 항목

- **v_shot throughput — 해소(2A′ 완료, §8 (d))** — 재실측 117ms/step; 병목 = per-layout eval(빌드 아님). 벽시계 DoD PASS(16w≈2.9h, batched 시 1.5h). batched-eval 구현 완료(§8 (e), `e99ff34`) — 실측 54.4ms/step. n_samples 축소는 near-gate 위험으로 기각(2000 유지), obs-lite 보류.
- **혼합 action head — 해소(2B, §8 (g))** — **Bernoulli head 채택·구현**(`MixedActorCritic`; 저장 fire = 정확한 {0,1} 샘플 → PPO ratio 정확).
- **비수렴·보상 스케일·NaN** — Phase 1 토이에서 선제 차단 + 디버깅 경험 1건은 학습목표(`06`).
- **torch 샌드박스 불가** — 학습은 로컬/랩 전용, 샌드박스는 torch-free 테스트만.
- **mount truncation** — 마운트 쓰기 간헐 truncation(이번 세션 실재) → heredoc 재기록 + 재읽기 검증 규율.
- **결정 D1/D2/D3 = A/A/A 확정(2026-06-30)** — §1. 플랜이 이 기준으로 고정.
- **공격자 상태분포 편향 [비준 2026-07-03]** — scripted keystone(반응형이긴 함: commit-후 dodge + kill-radius 반발)이 방문 안 하는 상태는 정책이 못 배움. v_shot이 기동 **집합** 지표(S14)라 성공기준 오염은 아니고 분포 문제. 대응 2단계: ① **M2 안 — scripted 파라미터 랜덤화**(v_nominal·a_lat_max·amp·react_on_commit·스폰 기하 = 공격자 가족 도메인 랜덤화; 정상성 유지, 2B 진입 시 config로 **[구현 §8 (g): `attacker_rand.py`+`l2_ippo.yaml`, adv_a_max 하향-전용]**) ② **L2 게이트 후 — exploiter probe**(방어자 freeze → adversary에 PPO, reward=−J 배선 기존재 → exploitability 수치 1개 = 논문용; co-training 아님). 공동 학습(self-play/alternating BR) = **S13 deferred** — Gavin arXiv:2603.16279가 1v1 net competitive PPO 선점, self-play 자체는 novelty 아님(팀 shaping+유한탄 주장은 무관하게 성립).

### 7.1 Phase 1 → Phase 2 이월 오픈 항목 (2026-07-01 기록)

> Phase 1 코어는 토이에서 검증됨. 아래는 shepherd env로 올릴 때(Phase 2) 재검토·해소해야 하는 것들.

- **obs normalization 미탑재** — Pendulum엔 불필요해 생략. shepherd obs는 **63-dim + 스케일 제각각**(위치/속도/attitude/FSM/vres) → **Phase 2 진입 시 running normalizer 추가**(코드에 주석 표시). 없으면 value/policy 학습 불안정 위험.
- **`init_log_std=0` (std=1) 과대 가능** — shepherd action space(accel±30 정규화 후 + fire; pressure/slew는 RESERVED로 정책 출력에서 제외 2026-07-03)가 Pendulum(±2)보다 좁아 초기 탐험이 과할 수 있음 → config로 튜닝. `clip_fraction_action` 로그로 경계-밖 학습 조기 감지(이미 배선됨).
- **action clip vs tanh squashing** — Phase 1은 clip(log-prob는 raw Gaussian 기준, 실행된 clip 액션 밀도 미보정). shepherd에서 `clip_fraction_action` 지속 상승 시 **tanh squashing(+log-det-Jacobian) 재검토**.
- **γ=0.9 는 Pendulum 튜닝값** — shepherd(`episode_len=80`, dt=0.05, 4s)용 γ/λ **재설정 필요**(config).
- **value clipping 생략** — Phase 1 plain MSE. shepherd에서 value loss 폭주 시 PPO2 value-clip 재도입 여지(구현은 config 플래그로 쉽게 추가 가능).
- **LunarLanderContinuous-v3 2차 검증 미실시** — box2d 미설치로 skip. 진짜 `terminated` 부트스트랩(=0)은 현재 **유닛테스트(`test_terminated_bootstrap_is_zero`)로만** 커버. shepherd 통합 전 end-to-end로 한 번 더 보려면 box2d 설치 후 secondary run.
- **재현성 CPU 한정** — same seed → same metrics는 **CPU deterministic**에서만 보장. CUDA는 비결정적(caveat). 랩 GPU run은 seed+config로 "근사 재현"만.
- **torch 테스트 CI 미편입** — 현재 torch 테스트는 로컬 venv에서만 green. CI(`ci.yml`)는 torch-free job만 → 추후 CPU-torch job 또는 `-m "not torch"` 유지 결정(§4.2).

---

## 8. 작업 로그 (append-only · 최신이 위)

### 2026-07-15 (ii) — ✅ A-3b′ 구현 + oracle 스모크 3/3 잠정 PASS — 서버 정식 oracle(n≥100) → 파일럿 런치 대기

- T-1~T-5 일괄 비준 → 구현. 신규 1 + 수정 3 + 테스트 +1.
- **① T-1 oracle** (`shepherd/scripts/a3b_fire_oracle.py`): bank×N fresh CRN(seed0 31M, 전 대역과 서로소), FIRE arm(매 스텝 강제 발사 — FSM R2 게이트가 v≥θ 표본에서만 커밋, sub-θ 명령은 무시라 wasted 없음)·DWELL arm(무발사) — 4시점 계측 + γ-할인 return 비교. **스모크(n 4~6/witness, 샌드박스)**: commit@1 = 0.75/1.00/1.00, **clean@1 = 1.0 전원**, capture = 0.75/1.00/1.00, pooled gate 0.917 → 잠정 PASS(정식 = 서버 n≥100). **스텝 2+ 커밋 1건은 비-clean** — "스텝 1 아니면 창 밖" 리뷰 지적 실증.
- **② T-2 dwell-annuity 실측**: hold-리미터 조건에서 **fire(+4.9~+6.8) ≫ dwell(+0.6~+1.7)** — 연금은 차단이 있어야 유지되므로 무-차단 스폰에선 발사가 argmax. → **T-2b(ep_len 스캐폴드) 불발동·보류**(연금 착취는 학습된 차단 시에만 가능 — captured_rate exit가 그 경로의 사다리 게이밍을 차단; 파일럿에서 fire_rate·captured 시계열 감시). T-2a는 구현: Curriculum reverse `exit_metric`(clean_cross_rate|captured_rate 검증), a3b config = **captured_rate**.
- **③ T-3**: cap 300k→**360k**, total 450k→**520k** (config 주석에 근거 명기).
- ④ 테스트 +1(captured_rate 게이팅: dwell-게이밍 무전진·capture로 전진·bogus 거부) + config 단언(exit_metric·cap) — A-3 스위트 17/17, M3계 회귀 green.
- **서버 시퀀스(Hyunjun)**: push → torch 테스트 → **정식 oracle**: `python -m shepherd.scripts.a3b_fire_oracle --n 100 --dwell-n 10 --out results/a3b_fire_oracle.json` (witness당 분할 가능: `--witness 0..2`) → **pooled ≥ 0.8 확인** → 파일럿: `TRAIN_MODULE=shepherd.scripts.train_m3a CONFIG=configs/m3a_a3b_pilot.yaml OUT=results/m3a_a3b_pilot REQUIRED_COMMIT=<본 커밋> GPU=0 SEEDS="0 1 2"`. oracle FAIL 시 런치 금지(13 §9 T-1) → 진단 표(13 §10) 첫 행 경로.

### 2026-07-15 (hh) — 외부 감사 리뷰 접수 (14 브리프 대상) — 정정 2·채택 5; A-3b′ 수정안 비준 대기

> 전문 = `URP/gpt_review_a3b_2026-07-15.md` (Hyunjun 보관). 총평: "무발사 = 현 MDP 표본 하의 합리적 수렴; 병목은 PPO가 아니라 판정 기하→기대수익→advantage→전이의 상류" — 캠페인 자체 결론과 정합. 이하 판독.

**반박/정정 (코드 실측):**
1. **first-action 타이밍 우려 → 구조적으로 해소**: env step()은 **pre-move 상태에서 판정**(viability 평가 → FSM/fire commit → backend.step 순). 스텝 1 발사는 주입 상태 그대로 판정되고, capture도 commit 시점 동결 worst-case(전개 8스텝 지연은 재판정 없음). 단 리뷰의 우려는 두 형태로 잔존: (a) 스텝 1 union은 reset과 다른 CRN 표본(step_seed) → flip 위험 — robust bank(0.9~1.0)가 정확히 이를 위해 존재 (b) **스텝 2+ 발사는 공격자 0.8~1.2m 이동 후 = 창 밖** → R0는 사실상 "스텝 1 발사 습득" 테스트로 협소함(리뷰 지적 이 형태로 유효). → oracle이 실측 확정.
2. **deterministic eval의 Bernoulli**: `(p > 0.5)` 엄격 부등 → 초기 로짓 0은 eval 무발사, 훈련 rollout은 샘플링(p≈0.5 탐색) — 우려 해소. A-3 첫 eval fire 0.10은 초기 학습 로짓 이동분.

**채택 (A-3b′ 수정, 비준 대상 T-1~T-5):**
- **T-1 forced-first-fire oracle = 파일럿 선행 게이트 (최우선)**: bank 3본 × ≥100 fresh CRN — reset/commit(스텝1 pre-move)/스텝2-발사 대조/resolution 4시점의 v_soft·o·boxed·worst·clean·capture + **dwell-vs-fire 귀속 return 실측**(hold-still vs forced-fire 누적 J, γ 0.99). 통과 기준: commit-clean ≥ 0.8. 미달 시 R0 해석 불능(리뷰 문구 채택).
- **T-2 dwell-annuity 결함 대응**: level-form headline+r_geo 매 스텝 지급 + 발사 = 에피소드 조기 종결 → witness 상태에서 할인 dwell 수익(~1.2/step × 55 ≈ 66) ≫ fire 경로(≈27) — **"발사가 연금을 끊는다"**: 全 캠페인 무발사 수렴의 제3 기전 후보(공간·표본 면도날에 추가). 대응 2단: ① **R-exit 지표 교체 clean_cross → captured_rate**(dwelling은 capture 불가 → 게이밍 차단; 동시에 리뷰 §통계 지적 해소 — 무발사 baseline capture=0이므로 어떤 capture도 곧 학습 증거; 문턱 0.45/0.17/0.10 유지, bank robust_capture 0.9~1.0이라 도달 가능) ② **ep_len 스테이지 스캐폴드 후보**(R0 ~20스텝: dwell 상한 ≈ fire 수익으로 인센티브 균형) — oracle의 dwell-vs-fire 실측 후 조건부 비준.
- **T-3 예산 정정**: 7 스테이지 × 지속2 × 20,480 = 286,720 vs cap 300k(여유 13k < eval 1회) = "한 번이라도 미끄러지면 R6 기계적 불능" — **cap 360k·total 520k 상향**. (A-2 340k 정정과 동일 유형 재발 — 사다리 예산은 최소소요 ×1.2 룰 채택.)
- **T-4 재프레이밍**: A-3b 파일럿 = end-to-end 후진 커리큘럼 검증이 아니라 **말단 행동 습득 실험**(R0~R3 중심; 리뷰 용어 "terminal-state randomization" 인정). config-only 스폰(리미터 속도 0·컨트롤러 이력 무) 한계 명시 → **v2 = 성공 궤적 스냅샷 되감기**(R0/R1 성공 정책의 clean-fire 궤적에서 t−1,−2,... 상태 뱅크) 예약; R5→R6 리미터 보간 스테이지 = confirmatory 전 필수 확정(파일럿과 무관).
- **T-5 진단 표 채택**(실패 위치 → 최우선 원인 매핑, 13 §10 수록) + 짧은 에피소드 = 저우선(truncation bootstrap 기존 테스트 확인만).

### 2026-07-14 (gg) — ✅ A-3b 구현 완료: robust-witness probe(bank 3본 확보) + R-8 게이트 + 창-스케일 사다리 config — scratch 3-seed 파일럿 대기

- R-6~R-8 비준 → 구현·실행. **판정 경로 불변**(probe = 분석 lane, 학습 아님).
- **① robust-witness probe** (`shepherd/scripts/a3_robust_witness_probe.py`): E_seeds[clean] 목적의 greedy 리파인먼트 — **비용 트릭: (x,v)당 union을 seed별 1회만 빌드, 후보 평가는 캐시 union의 저가 eval**(리파인 = ~1000 eval, ~1000 빌드 아님 → 샌드박스 완주). CRN 위생: search seeds 100–104 / **validation 200–209 서로소**, 수락 = val ≥ 0.9. 후보 = 자기 witness + 도너(x20v24) 패턴 이식(공격자-상대, x축 속도비 스케일).
- **② probe 결과 (샌드박스 실행, 결정론 rng23·`results/a3_robust_bank.json` 커밋)**: **bank 3본 수락** — x20v24 val **1.00**/cap 1.00, x16v20 **0.50 → 1.00**(리파인먼트가 취약 witness를 완전 강건으로 이동 — robust-clean이 로컬 탐색으로 도달 가능함 실증), x12v16 0.38 → **0.90**; x16v20u1은 0.70 reject(동일 (x,v) u0 확보로 무방). **σ-베이스라인**(스폰-clean, R-7 상대화 근거): σ0.02 → 0.27~0.42, 0.05 → 0.08~0.12, 0.1 → 0.01~0.09, 0.2 → ≈0, 0.5 → 0 (A-3 R1 전멸의 정량 확정).
- **③ R-8 게이트**: `spawn_bank.verify_t0(robust_min=, robust_seeds=)` — 강건성 진단을 드롭 게이트로 승격; Curriculum reverse가 `verify_robust_min`/`verify_robust_seeds` 전달. 테스트: 구 T0 뱅크에 0.9 게이트 적용 시 실제로 탈락 발생 lock.
- **④ config `m3a_a3b_pilot.yaml`**: bank 스폰·R0(σ=0, **exit 0.45 = 표현 테스트 본체**)→R1(0.02/0.17)→R2(0.05/0.10 floor)→R3(0.10/0.10 — 베이스라인 ~0.05 초과 요구 = 셰이핑 시작)→R4(0.2+rw5)→R5(0.5+rw15)→R6(nominal); exit floor 0.10 = eval 20판 해상도(2판). 450k·scratch 3-seed; **warmref 생략**(A-3에서 warm=scratch 동일 실패 + 교란이 스폰측이었음 — 사유 기록). 테스트 +4(뱅크 로딩·R-8 게이트·이식 수학·사다리 단조성), A-3 스위트 16/16 + M3계 회귀 35 green.
- **파일럿 중간 게이트 (사전등록)**: **R0 통과 ≥2 seed** ∧ R2(σ0.05) 도달 ≥1 seed, or frozen-heldout clean 비영 ≥1 seed. **R0 실패 = (이번에야말로) 표현 가설 기각 → L-2stage 순서 논의.** 스폰은 이제 fresh-seed 하에서도 ~90–100% clean이므로 "즉시 발사"만 배우면 R0는 통과된다 — 못 배우면 행동 표현의 문제.
- **서버(Hyunjun)**: push 후 ⓐ torch 테스트 ⓑ (선택) probe 서버 재현(`python -m shepherd.scripts.a3_robust_witness_probe --iters 100` — 결정론, bank 일치 확인) ⓒ `TRAIN_MODULE=shepherd.scripts.train_m3a CONFIG=configs/m3a_a3b_pilot.yaml OUT=results/m3a_a3b_pilot REQUIRED_COMMIT=<본 커밋> GPU=0 SEEDS="0 1 2"`.

### 2026-07-14 (ff) — ❌ A-3 파일럿 중간 게이트 FAIL — 단 **L-2stage 신호 미발동**: R1 교란 2건 실측(σ≫창 + T0 3/4 union-표본 비강건) + **robust witness 실존** → A-3b 수정안 제안

- **런** (`5430246`, 아티팩트 `aaf51cf`): scratch 3-seed + warmref 1-seed **전부 r_max=0**(R1 정체, 전진 0회), train-eval clean 全 0.00(fire 첫 eval 0.10 → 0), cap @307k, heldout 0/200 ×4 (방관 3본 ret ≈0·pen 100%, warmref 무발사-차단 ret −1.18·pen 0% — (aa) 수동 평형 재현). 형식 판정: (i) R1 통과 0/3 (ii) R3 도달 0 (iii) heldout 비영 0 → **A-3(현 파라미터) kill**.
- **교란 1 — σ ≫ 창 폭**: 스폰-시점 clean 확률 실측(frozen env·fresh seeds·n=10/σ): σ_pos **0.5(R1값) → 0/10**, 0.1 → 0/10, 0.02 → 0/10, **σ=0 → 3/10**. R1은 말단 체인 학습이 아니라 "0.5m 밖에서 면도날 찾기" = 원문제 재출제였음. exit_clean ≥ 0.5는 구성상 도달 불가 — 정책이 완벽해도 통과 못 함.
- **교란 2 — T0 비강건**: witness별 fresh-seed(100~107) clean 빈도 = **x20v24u0 8/8 (v_soft 고정 1.00)** / x16v20u0 4/8 / x12v16u0 3/8 / x16v20u1 1/8. P4 witness는 "자기 union seed 하에서의" capture-grade였고 3/4는 CRN 표본 교체 시 창이 닫힘. (verify_t0의 robust-seed 진단이 이를 잡도록 설계돼 있었으나 스모크에서 생략·서버 미실행 — 교훈: 설계한 진단은 실행까지가 진단.)
- **사전등록 해석 판단**: "(i) 실패 = 표현 가설 기각 → L-2stage"는 **발동 안 함** — R1 스폰이 사실상 전혀 clean이 아니었으므로(0/10) 표현 가설을 테스트하지 못함. 표현 가설 = 미판정 유지.
- **신규 발견 (캠페인 최중요 증거)**: clean 술어는 공간 면도날(ρ 0.05~0.2m)에 더해 **CRN-표본 차원의 면도날** — 동일 기하가 union 표본에 따라 clean↔비clean 요동. A-1/A-2 무발사 붕괴의 심층 설명 완성: EV(clean 시도) = 공간 명중률 × 표본 강건성 **이중 할인** → 발사 포기는 학습된 합리성. **단 robust witness 실존**(x20v24u0, 8/8) → robust-clean 집합 비어있지 않음 = A-3 노선 폐기 불요, 재파라미터화로 충분.
- **A-3b 수정안 (docs/13 v0.3 부록 §8, 비준 대기 R-6~R-8)**: ① **robust-witness probe**(분석 lane, 학습 아님): P4 refinement를 E_seeds[clean](10 seeds) 목적으로 재실행 → robust_clean_frac ≥ 0.9 bank(현 1본 → 목표 ≥3본, (x,v) 그리드 확장) ② 스폰 = robust bank만 ③ **σ-사다리 창-스케일 재설정**: R0 σ 0.02부터 기하급수(0.02→0.05→0.1→0.2→0.5→...) ④ **exit 상대화**: exit_clean = 0.5 × (스테이지별 스폰-clean 베이스라인, probe로 사전 측정 — 절대문턱은 스폰-clean<1에서 과엄격) ⑤ L-2stage 논의는 "표현 테스트가 성립한" A-3b 실패 후에만.

### 2026-07-14 (ee) — ✅ A-3(L-reverse) 구현 완료: 스폰 주입 + T0 재구성·재검증(4/4 실측) + reverse 커리큘럼 — scratch 3-seed 파일럿 대기

- R-1~R-5 일괄 비준 → 구현. **frozen 계약·판정 경로 무변경**; 신규 2 + 수정 3 + config 2 + 테스트 +12.
- ① `shepherd/train/spawn_bank.py`(신규): probe `refined_best` → T0 로딩(capture-grade만)·**STRICT 프레임 체크**(apex [2,0,0] = layout finisher_p0, 불일치 시 변환 없이 raise)·`spawn_from`(σ_pos/σ_vel 지터 + rewind_dx 접근-역방향 후진)·`verify_t0`(frozen 조립 루트 재계산, 미재현 DROP·전멸 raise) + CLI. **샌드박스 실측: T0 4/4 PASS**(전부 v_soft 1.000·worst 1.000·p_feas 4.0e-4~2.4e-3) — R-1 게이트 그린; robust-seed 진단은 서버 몫.
- ② `env_m3.reset_to`(TRAIN-ONLY): 정상 reset 후 backend AgentKin 오버라이드(리미터 4 + 공격자 pos/vel; **피니셔 불가침**) → viability·obs 재계산 + m3 트래커 재시드; RotorPy형 백엔드는 별도 주입 어댑터 필요 명시. ③ `make_env_m3`: Curriculum **`reverse` 모드** — `overrides()` 상시 None(frozen 상수 + judgment m3 = R-5 "보상 무개입"이 구조적으로 보장), `spawn()`(rollout)·`eval_spawn_fn()`(게이팅 번들, 스테이지-안정 결정론 draw)·R-사다리 전진/백오프/cap(A-2 기계 재사용; cap = stall 스테이지 증거)·R5(nominal) exit = heldout clean 최근-3 비영·T0 검증은 생성자(env_cfg 경유; 테스트는 verify_t0:false); `M3Adapter.reset_to` 패스스루. ④ `train_m3a`: `_begin_episode` 스폰 시임, `m3_eval_bundle(spawn_fn=)`은 **train-eval 게이팅 번들 전용**(frozen/judgment 번들·heldout 하네스는 스폰 경로 부재 — 소스-lock 테스트), `evaluate()` reverse-인지.
- ⑤ configs: `m3a_a3_pilot.yaml`(scratch·R1~R5·400k) / `m3a_a3_warmref.yaml`(**warm_start + wandb group만 상이** — R-2 참고런, arm 선택 사용 금지). ⑥ `tests/test_a3_reverse.py` +12(로딩/프레임 STRICT/spawn_from 결정론·rewind 방향/reset_to capture-grade 재현·피니셔 불가침/어댑터/eval 격리 소스-lock/reverse 전이·백오프·cap·exit/nominal 종단 필수/config diff lock) — **t-free 전 스위트 green**(청크: 기타 80+4skip / coma 8 / M3계 47+1skip / viability·net_forward 23).
- 캐비앗: 스폰은 **상태만** 주입(v_nominal·컨트롤러 불변 — 스폰 순간 viability는 probe와 일치, 이후 거동은 env 소관); scratch obs-norm이 privileged 스폰 분포로 초기화됨(R5 전이 시 norm drift 캐비앗).
- **파일럿(서버, Hyunjun)**: push 후 ⓐ torch 테스트 ⓑ (선택) `python -m shepherd.train.spawn_bank`로 robust-seed 진단 커밋 ⓒ scratch 3-seed: `TRAIN_MODULE=shepherd.scripts.train_m3a CONFIG=configs/m3a_a3_pilot.yaml OUT=results/m3a_a3_pilot REQUIRED_COMMIT=<본 커밋> GPU=0 SEEDS="0 1 2"` (+ warmref 1-seed: `CONFIG=configs/m3a_a3_warmref.yaml OUT=results/m3a_a3_warmref SEEDS="0"`) ⓓ **중간 게이트(13 §4)**: (i) R1 통과 ≥2 seed ∧ (ii) R3 도달 ≥1 or (iii) heldout clean 비영 — **(i) 실패 = 표현 가설 기각 신호 → L-2stage 순서 조정**.

### 2026-07-14 (dd) — A-3(L-reverse) 설계 초안 v0.1 — 비준 대기

- Hyunjun 결정: A-2 kill 후 다음 레버 = **A-3 L-reverse** (S-6 수동성-비용은 보류 — 발사 강제로는 release-채널 기하를 못 가르침, (cc) 증거 정합).
- 설계 = **`docs/13_a3_reverse_design.md` v0.1**: 단일 가설 "clean은 학습 가능, 스폰 분포가 발견을 막을 뿐" — 콘 폭 상시 frozen 고정(폭 사다리 폐지)·보상 스캐폴드 0·커리큘럼 = 스폰 분포만(P4 probe capture-grade 4본 재구성 T0 → σ/Δx 후진 확장 R1~R5, adaptive 전진/백오프 기계 재사용)·scratch 기본(warm 습관 상속 회피, 참고런 1-seed)·중간 게이트 = R1 통과∧R3 도달 or heldout clean 비영, **R1 실패 = 표현 가설 기각 위험 → L-2stage 신호**. 구현 리스크 1순위 = 백엔드 상태 주입(RotorPy state set 경로).
- 대기: R-1~R-5 비준 → 구현(스폰 주입 + 재구성기 + reverse 커리큘럼 + config + 테스트) → scratch 3-seed 파일럿.

### 2026-07-14 (cc) — ❌ A-2 파일럿 중간 게이트 FAIL → 레버 kill; 벽 정밀화 (0.1335, 0.1501] — 다음 = A-3(L-reverse) 제안

- **런**: `9584177` · 3-seed · 550k · WARM (`results/m3a_a2_pilot`, 아티팩트 `3830021`).
- **사다리 거동 (3 seed 동일 패턴)**: k 1→2→3 순항(각 폭 train-eval clean 1.0) → **k=4(ha 0.1335) 즉사**(clean·fire 동시 0, 1~3 eval 내) → 백오프로 k=3 복귀 시 **즉시 회복**(clean 1.0) → 재도전 k=4 재즉사 → cap(340k) freeze @ k=3. 이벤트 시퀀스가 3 seed 스텝 단위까지 동일(동일 warm ckpt + 포화 지표).
- **중간 게이트 판정 (사전등록 12 §7 S-4)**: (i) ha<0.1274에서 clean≥0.1 지속 — **미달**(지속 최대 폭 = k=3, ha 0.1501; k=4는 0.1335로 기준 폭에도 못 미침) (ii) frozen-heldout clean 비영 ≥1 seed — **0/200 × 3 전멸**. → **FAIL, A-2 번들 kill.**
- **소득 (증거 3건)**:
  ① **벽 정밀화**: A-1(시간-램프 통과)과 달리 **정적 폭 + 3~6 eval 적응 시간을 줘도** 0.1335는 못 넘고 0.1501은 완벽 → 벽 = **(0.1335, 0.1501]** (A-1 브래킷 [0.127, 0.146]과 정합, 상계가 더 조여짐).
  ② **인센티브 가설 기각 강화**: λ2_scale 0.3 상시(폭 미완주로 복원 미발동) + w_gf 1.5에도 fire가 clean과 **동시** 사멸 — 발사-EV 수리가 무효 → 남는 가설 = 좁은 폭의 clean은 방사형 정책으로 표현/발견 불가한 release-채널 기하 (P4 (u) 실측 정합).
  ③ **쌍안정성**: 동일 정책이 0.1501에선 완벽, 0.1335에선 침묵, 복귀 시 즉시 회복(파국적 망각 아님) — 행동 "열화"가 아니라 "스위치-오프". graded λ1(τ 0.05)로도 k=4에서 margin gradient가 안 잡힘 = 그 폭에서 근접-clean 상태 자체에 도달 못 함.
- **S-6 검토 (발동 조건 "λ2 완화에도 fire 사멸" 충족)**: **보류 권고** — 수동성 비용은 k=4에서 발사를 강제할 뿐 release-채널 기하를 가르치지 못함(boxed/wasted 스팸 예상). 증거가 인센티브 아닌 표현/발견 문제를 지시.
- **다음 = A-3 (L-reverse, 사다리 NF 열 그대로)**: P4 probe의 capture-grade clean-fire 상태 4본 근방 스폰 → release→fire 말단 체인 학습 → 스폰 후진 확장(eval 스폰 frozen 유지). 설계 문서 → 비준 → 구현. 증거 테이블 A-2 행 = 12 §6.

### 2026-07-14 (bb) — ✅ A-2 구현 완료: NF 번들 L-fire + L-margin (+L-adaptive) — 서버 torch 테스트·3-seed 파일럿 대기

- **원칙 준수(12 §1)**: frozen 계약·판정 경로 무변경 — 스캐폴드 3종 전부 **stage-주입 전용**, 판정 m3(기본값 lam2_scale 1.0·clean_margin_tau 0.0)는 **비트-동일 lock**(test_default_params_bit_identical_to_ratified_j); run-config `m3:` 블록은 스캐폴드 키 설정 불가(STRICT 키 검사 유지) → 판정 J·Gate A/B 정의 불변.
- 구현: ① `env_m3.py` — M3Params `lam2_scale`/`clean_margin_tau` + `m3_step_terms(clean_margin=…)`: τ>0 시 λ1 binary → **graded σ(margin/τ)·1[¬boxed]**(`l1_term` 반환), wasted 항 = `l2·lam2_scale`; env가 clean_margin = v_soft − θ_stage 상시 전달. ② `make_env_m3.py` — `SCAFFOLD_KEYS=(w_gf, lam2_scale, clean_margin_tau)` 스테이지 옵션(미지 키 거부 유지) + **Curriculum `adaptive` 모드**: 폭-사다리 k/8 (전진 = 현재 폭 train-eval clean≥0.1 지속 2-eval; 백오프 = 비-ok stall 3-eval, k>0; **cap 340k freeze = stall 폭 증거**; 폭 도달 후 lam2 60k 선형 복원; s2 exit = 폭 도달 ∧ 복원 완료 ∧ heldout clean 최근-3 비영) + `describe()`. ③ `train_m3a.py` — eval_curve point에 `cur`(k·half_angle·capped) 1줄. ④ `configs/m3a_a2_pilot.yaml` — s1 블록에 스캐폴드 3종(w_gf 1.5·lam2_scale 0.3·τ 0.05), judgment `m3:` = full_staged와 동일, 550k·WARM(coma_run2/seed1). ⑤ `tests/test_a2_scaffolds.py` **+14**(판정 비트-동일·graded 시그모이드/boxed 게이트/margin 필수·lam2 wasted-한정·스테이지 플럼빙·adaptive 전진/백오프/cap/복원/exit·staged 회귀).
- **S-4 부속 정정**: L-adaptive S2 상한 300k → **340k** — 8스텝×지속2×케이던스 20,480 = 327,680 최소 소요라 300k는 완주 수학적 불가(구현 중 발견; 12 §3 표·§7 반영).
- 테스트: 신규 14/14 + t-free 전 스위트 green(샌드박스 실측, viability·net_forward 포함 — 스크래치 트리 실패 2건은 `prototypes/` 미복사, 코드 무죄). torch 몫(웜스타트 경로 등)은 서버 실측 필요((w-1) 교훈).
- **파일럿(서버, Hyunjun)**: push 후 ⓐ torch 테스트 확인 ⓑ `TRAIN_MODULE=shepherd.scripts.train_m3a CONFIG=configs/m3a_a2_pilot.yaml OUT=results/m3a_a2_pilot REQUIRED_COMMIT=<본 커밋> GPU=0 SEEDS="0 1 2" bash scripts/run_ippo_seeds_parallel.sh` ⓒ 종료 후 eval_curve `cur.k`/stall 폭 + frozen/heldout clean → **중간 게이트**(12 §7 S-4: clean≥0.1 지속 @ ha<0.1274 or heldout clean 비영 ≥1 seed) → 통과 시 10-seed 본선 / 미달 시: fire 사멸 지속이면 **S-6 폴백** 검토, 아니면 A-3(L-reverse).

### 2026-07-14 (aa) — ✅ Step 0 진단 판독: **NO_FIRE 10/10 합의** → 브랜치 NF, A-2 = L-fire + L-margin (+L-adaptive) [사다리 기계적 확정]

- **판정** (`results/m3a_heldout/a2_fire_mode.json`, `5f43027`): 전 10 seed **NO_FIRE** — held-out 2,000 에피소드에서 발사 **전무**(fire_ep_frac 0.000), wasted 全 0. (x) 캐비앗 해소: warm boxed_fire=0은 "깨끗해서"가 아니라 **발사를 안 해서**였음.
- **붕괴 = 절벽(연속 열화 아님)**: eval_curve 전 seed 동일 패턴 — ha 0.1455에서 clean 0.6~0.7·fire 0.6~0.7·boxedF 0.0(건강한 clean 발사) → 바로 다음 eval, ha 0.1274에서 clean 0.0·fire 0.0 **동시 사멸**. **절벽 폭 = ha [0.1274, 0.1455]**(frozen 0.067의 약 2×; eval 케이던스 ~20k 해상도, 시간-선형 램프라 전 seed 동일 지점). boxed-발사 중간상 없음 — "clean 발사"→"무발사" 이산 전환. 기전: 콘 축소로 EV(발사) = w_gf·v·g(o)+λ1·P(clean)+λ_cap·P(cap)−λ2·P(wasted) 부호 음전(P(clean)·g(o) 급락, P(wasted)→1), binary λ1과 미세 g(o)는 절벽 너머 gradient 0 — NF 가설 정합.
- **수동 평형 발견(신규 증거)**: held-out 종점 2모드 — **방관형 8 seed**(len 23·pen 100%·ret ≈0) vs **무발사-차단형 2 seed**(s3/s6: len 80·**pen 0%**·ret −1.5·dwellF 0.06/0.13). 판정 J 하에서 **"아무것도 안 함"(≈0) > "차단"(−1.5)** — hold-대비 headline + λ3가 작전상 우월한 교전(침투 0%)을 수동성보다 낮게 가격(J에 침투 비용 부재). M3a J의 구조적 캐비앗 = 벽 논문 진단 서사의 증거 행.
- **A-2 확정(12 §4 NF 열, 기계적)**: **L-fire**(S2 동안 λ2 1.0→0.3, 램프 완료 후 3-eval에 걸쳐 복원 + w_gf 1.0→1.5) + **L-margin**(λ1 binary → graded σ((v−θ_stage)/τ_m), τ_m 0.05, ¬boxed 게이트, S3 진입 시 binary 복원) + **L-adaptive**(폭-스텝 8 이산화·전진 = 현재 폭 train-eval clean≥0.1 최근-2 지속·stall 3-eval 시 1스텝 백오프·S2 상한 300k). **파일럿 중간 게이트 정량화**: train-eval clean≥0.1 지속 @ **ha < 0.1274**(A-1 사멸 폭 개선) or frozen-heldout clean 비영 ≥1 seed.
- **수정안 후보(S-6, 비준 판단)**: 수동 평형 대응 "교전/침투 스캐폴드 비용"은 **A-2 미포함 권고**(번들 confound 3요소 초과 방지) — A-2 파일럿에서 λ2 완화에도 fire 사멸 지속 시의 **사전등록 폴백**으로만 12에 기재.
- 대기: 12 §7 **S-1~S-5 비준**(+S-6 폴백 기재 여부) → A-2 구현(env_m3 스캐폴드 항 + Curriculum adaptive ramp + config + 테스트) → 3-seed 파일럿.

### 2026-07-14 (z) — 방침: A-전력 레버 사다리 캠페인 전환 (트립와이어 8/31) + Step 0 실패-모드 진단 도구 — 비준·서버 실행 대기

- **방침 전환 (Hyunjun):** (y) 갈림길의 "A 1~2회 제한 → B"를 **A-전력 레버 사다리 캠페인**으로 개정 — novelty의 본체는 capture-unlock 성공이라는 판단. 시도당 가설 1개·실패도 기전 증거로 계측(음성=자산 정합)·**하드 트립와이어 2026-08-31**(이후 신규 A-런 금지 → B 프레이밍 확정). 예산 ~6주 = A-2~A-5. 교수님 공유 = 통보형("A 전력·트립와이어·실패 시 B"). 사전등록 = **`docs/12_a_campaign.md` v0.1** (레버 풀 7종·브랜치별 사다리·시도 프로토콜·비준 체크리스트 S-1~S-5) — **진단 데이터 접촉 전 커밋**으로 임계·순서 고정.
- **Step 0 (학습 런 아님):** `shepherd/scripts/a2_fire_mode_diagnosis.py` — (y) 아티팩트로 무발사/boxed-발사/clean-miss 판별(사전등록 임계: fire_ep_frac<0.05 → NO_FIRE; boxed_at_fire≥0.5 → BOXED_FIRE; else CLEAN_MISS; 합의 ≥70% seed, 미달 MIXED) + eval_curve로 **S2 붕괴 폭 계측**(램프 분율 → half_angle/θ 환산; s2 진입 = eval 라벨 근사 캐비앗). numpy-only·torch 불요. 산출 브랜치(NF/BF/CM) → 12 §4 사다리에서 A-2 레버 기계적 확정. 합성 3-모드 데이터로 분류·MIXED·붕괴 계측(램프 0.40 → half_angle 0.147) 검증 완료(샌드박스).
- **서버 (Hyunjun):** pull 후 `python -m shepherd.scripts.a2_fire_mode_diagnosis --heldout-glob 'results/m3a_heldout/m3a_full_seed*.json' --curves-glob 'results/m3a_full/seed*/eval_curve.json' --out results/m3a_heldout/a2_fire_mode.json` (TMPDIR=/data 권장, (y) ops 캐비앗) → 결과 JSON 커밋·회수 → A-2 구현 착수(브랜치 확정 후).
- 다음: ① 진단 회수 → ② 12 비준(S-1~S-5) → ③ A-2 구현(스캐폴드 항 + L-adaptive 램프)·테스트 → ④ 3-seed 파일럿.

### 2026-07-09 (y) — ❌ M3a 본선(full staged) 완료 → Gate A/B 미달 (10-seed held-out CRN): capture-unlock = findability 벽 확정

- **본선:** warm-start(coma_run2/seed1)·`mode: staged` S1→S3·10-seed·500k (`configs/m3a_full_staged.yaml`, `6d56e62`), GPU 웨이브 2회(0-4/5-9).
- **결과:** 전 10 seed **s2 정지**(s3 미도달), in-training frozen clean=0·cap=0·ret≈0(−1.0~0.0).
- **정식 판정(`analyze_gate_a`, held-out CRN 77M+i·200 eps/seed·B=10k·rng7):** **Gate A FAIL**(clean_cross point 0.0·one-sided 95% 하한 0.0·CI[0,0]) · **Gate B FAIL**(total capture 0, 0/10 seeds) · strong/paper-grade FAIL. 아티팩트 `results/m3a_heldout/{m3a_full_seed*.json,gate_a.*}`.
- **해석:** S1(넓은 콘)선 clean 발사 학습 성공(전 seed s1→s2 전환) → S2 anneal서 콘 좁히자 clean 붕괴, s2 탈출조건(frozen clean>0 지속) 미충족. **P4 "feasibility 무죄, findability 유죄"가 본선 held-out으로 확정**(하드 0, 샘플 노이즈 배제).
- **프레이밍(음성=자산):** ① M2 레버(L2 게이트 PASS) ② M3 capture-unlock findability 벽(이 결과) ③ P4 기하 진단(clean 채널 ρ 0.05~0.2m·p_feas~1e-3 면도날) 3조각 정합 = 방어 가능한 논문 서사.
- **다음 갈림길(교수님 상의):** A. 보상 재처방(P4 A/B/C: hard v_eff 강화·clean-margin 역-U·near-capture 항·채널-폭 커리큘럼; p_feas~1e-3라 RL 미발견 고위험) vs B. 스코프 동결(M2 레버+findability 진단으로 프레이밍 확정). 기본선 = A 1~2회 제한 시도 → 실패 시 B. 착수 전 fire_rate 실패 모드 진단(무발사 vs boxed-발사).
- **ops 캐비앗:** 서버 루트(`/`) 100% full 발생(seed4 heredoc temp 실패 원인) — 학습·데이터는 /data(6.9T 여유)라 무영향, 원인=타 사용자/시스템, TMPDIR=/data 우회·admin 통보 권장.

### 2026-07-07 (x) — ✅ M3a play-in 완료 → WARM arm 선택 (rule 2); 본선 staged config + Gate-A 하네스 준비

- **Play-in 판정 (`5249ece`, s1_only 200k × {warm,scratch} × 3-seed):** `analyze_m3a_playin` → rule 1(frozen clean_cross) 0.0=0.0 동률 → **rule 2(boxed_fire) warm 0.0 < scratch 0.111 → WARM** (사전등록 tie-eps 0.02, decided_by_rule=2; diagnostic sel_score −0.014 vs −0.079). `results/m3a_playin/decision.json`.
- **캐비앗(중요):** 양 arm 모두 **frozen clean=0·capture=0**, 반면 S1-scaffold train clean=1.0·capture_count ~37850/34822. **정상** — s1_only는 S2 anneal 미수행이라 frozen 전이 압력 0. play-in = "초기 정책 선택"만; **Gate A/B(clean-unlock·capture existence)는 전부 본선 frozen held-out 판정 몫**(37k = 넓은 콘 캡처, capture-unlock 아님).
- **관찰:** warm이 scratch보다 덜 boxed(0 vs 0.111) → 사전등록 rule-4(warm의 L2 boxed-분지 상속 우려로 동률 시 scratch 우선) 우려가 데이터로 반증. ⚠ warm boxed_fire=0이 "깨끗해서"인지 "발사를 덜 해서"인지는 summary `fire_rate` 확인 필요.
- **본선 준비물(신규 2, 코드 변경 0):** ① `configs/m3a_full_staged.yaml` = warm-start(coma_run2/seed1)·`mode: staged`·500k·10-seed·**`--o-star` 미사용**. ② `shepherd/scripts/analyze_gate_a.py` = clean_cross_rate seed-cluster one-sided 95% 하한>0(Gate A) + capture existence(Gate B) + strong/paper-grade tier; analyze_p1 부트스트랩(B=10k·rng7) 재사용. train_m3a의 s1_only 가드는 `--o-star` 한정이라 staged 무관(확인 완료).
- **다음:** 본선 staged 10-seed(코어 여유 없으면 웨이브) → `eval_heldout_m3`(77M CRN)로 각 seed best-ckpt held-out → `analyze_gate_a` Gate 판정 → (Gate A PASS ∧ capture≥2 seeds면) M3b(S9 raid) 진입. o* 스윕은 S1이 이미 clean=1.0 자명 해결이라 저가치 → optional.

### 2026-07-07 (w) — M3a 구현 완료: env 변형 + 커리큘럼 트레이너 + 결선·판정 도구 — 서버 결선(3+3 S1 200k) 대기

> docs/11 v0.2 전 조항 코드화. **frozen 계약 무변경(기존 파일 수정 0, 신규 9파일).**
> ① `shepherd/env_m3.py` — `M3ShapingEnv` = frozen step 사본 + 보상 교체: v_eff **hard 게이트 main**(smooth=ablation 노브, 기본 금지), headline_M3 = hold-대비 level형 **signed**(클리핑 전무; 순수함수 `m3_step_terms`로 분리·테스트 lock), 역-U `g(o)`(g(0)=0, ln-대칭), r_geo **step/fire 분리**, J = w_h·headline_M3 + w_g·r_geo_step + w_gf·r_geo_fire + λ1·clean + λ_cap·capture − λ2·wasted − λ3·loss; **coma_D·delta_v_shot_headline은 M2 그대로**(공유 J만 교체 — 비준 범위 준수), near-capture 항 부재 명문화(수정 4). **obs 무변경 확정**: 설계 "o·boxed 노출 확인/추가" → 확인 결과 o=p_feasible가 이미 obs[-1]이고 boxed ≡ (o==0) 파생 가능 → 추가 없이 63-dim 유지 = **웜스타트 ckpt 형상 호환**(테스트 lock). fire-체인 로깅 = per-fire 레코드(v/v_eff/o/n_feasible/boxed/clean + captured/wasted는 해소 시점 기입, fire_step, release_event_before_fire, boxed_dwell_before_fire, |ln o−ln o*|) + per-step release_event(o: 0→(0,o_hi], **o_hi=1e-2는 구현 선택 — 비준 항목 아님**)·boxed_dwell.
> ② `shepherd/train/make_env_m3.py` — STRICT M3 조립 루트(`make_train_env` 경유 → 기존 핀 전부 상속; 스테이지 θ는 c_fire 동시 갱신으로 FireGate R2 assert 통과; l1/l2/l3 = frozen 시나리오 reward 단일 출처, env 생성자에서 교차검증), `M3Adapter`(M3_FLAG_KEYS 확장), `Curriculum`(S1 exit = train-eval clean>0.2 지속 sustain_evals ∧ boxed_fire<0.5 ∧ fire>0 / S2 = 선형 복원 ramp 완료 ∧ frozen-heldout clean 최근-3 비영, 미충족 시 S2 HOLD / `s1_only` = 플레이인·스윕 모드). **eval은 전 경로 stage=None = frozen 상수 + judgment m3(σ_g 1.0·w_g 0.3 = S3형)** — 스테이지와 무관하게 판정 지표 동일.
> ③ `shepherd/scripts/train_m3a.py` — P1 main recipe(coma_mix 0.5·recipe-v2) 러너: per-episode 재조립에 스테이지 주입(가족 랜덤화와 동일 경로), **frozen-eval(판정 proxy) + train-eval(S1 exit·o* 선택지표) 이중 번들**, best-ckpt = last-3 frozen **사전등록 참고점수** clean + 0.5·cap − 0.5·boxed_fire − 0.2·boxed_dwell_frac(선택 지표 ≠ 보고 지표 명시), 웜스타트 = actor/critic/value-norm + frozen obs-norm 로드·**optimizer fresh(문서화된 선택)**·obs_dim/n assert, `--o-star`는 `s1_only` 모드에서만 허용(**S1-한정 스윕 강제**, frozen-heldout은 monitoring only), ntfy 훅(NTFY_TOPIC, best-effort).
> ④ configs `m3a_s1_scratch.yaml`/`m3a_s1_warm.yaml` — **warm_start 블록 외 전 항목 동일**(테스트 lock); m3 블록 = judgment 값(o* 1e-3·σ_g 1.0·w_g 0.3·w_gf 1.0·λ_cap 5·hard), curriculum.s1 = 0.20/0.8/σ_g 2.0/w_g 1.0(run-1 시작값 w_g=1은 S1/S2 스캐폴드로 구현, §1·§2 정합); staged 키 사전 기입(s1_min 100k·sustain 3·s2_steps 150k — **s2_steps·sustain은 구현 선택**). warm ckpt = `results/coma_run2/seed1`(P1 최고 seed) — **런치 전 Hyunjun 확인 항목**.
> ⑤ `shepherd/scripts/eval_heldout_m3.py` — P1 held-out CRN 하네스(77M+i, 200판, 학습 seed 서로소 유지)의 M3-frozen판(fire-체인 포함; Gate A/B 입력). ⑥ `shepherd/scripts/analyze_m3a_playin.py` — 결선 선택규칙 **① clean ② boxed_fire ③ heldout clean ④ 동률 시 scratch** 사전등록 구현(`decide_playin`, tie-eps 0.02 = 사전등록 선택, 테스트 lock).
> 테스트 **+27**(t-free 21 / torch 6) → 수집 t-free 132 **전부 green(샌드박스 실측)** + torch 41(서버 몫). frozen 4종 + 기존 전 파일 diff 0(git status로 확인).

- **(w-1) 서버 torch 1차 실행 결과(2026-07-07): 169 pass / 3 fail — 全 3건 테스트 결함, 코드 무죄(수정 커밋 본 항목).** ① `test_warm_start_loads_weights_and_norm`(신규) — `next(parameters())`가 log_std(전 seed 0-초기화)라 "seed 다름" 비교가 항상 동일 → 첫 weight 행렬 비교로 수정. ② `test_coma_mix_zero_is_exact_2c`(2D 유산, **서버 첫 실행**) — mix=0 단락(`if coma_mix > 0.0`)은 코드상 정확하나, 멀티스레드 CPU matmul 리덕션 순서 비결정으로 ~1e-6 지터 → `torch.set_num_threads(1)` 핀. ③ `test_runner_coma_writeback_smoke`(2D 유산, 서버 첫 실행) — rollout=8은 공격자 τ-도달집합이 kill 구체에 닿기 전(엔게이지 ~15–20스텝, 스폰 시 full==hold라 D≡0)이라 전제 불충족 → rollout=64. 교훈: torch 테스트는 "수집"만으로 green 간주 금지 — 2C/2D 유산분 서버 실측은 이번이 최초.

- **(w-2) (w-1) 진단 2건 정정 — 서버 재실행이 비트-동일 실패값을 반환(지터 가설 반증):** ② 진짜 원인 = `_fill`이 torch **전역 RNG**로 액션 샘플 → buf_b가 buf_a fill 이후 상태에서 시작(obs만 numpy라 기존 전제조건이 오도 통과) → 각 fill 전 재시드 + 액션 블록 동일성 전제 추가(스레드 핀은 유지). ③ 진짜 원인 = **지오메트리**: nominal 링이 축에서 5 m·kill 2 m라 랜덤 정책으론 어떤 horizon에도 마스크가 안 물림(D≡0) → 테스트-전용 엔게이지 강제(ring_radius 1.5·spawn x 14·랜덤화 off), numpy 복제 검증 = 64스텝 중 21스텝 D≠0(|D|max 1.0, 최초 44). 교훈: 결정론적 실패(값 재현)는 지터 가설 즉시 기각 근거.

- **다음(서버, Hyunjun):** ⓐ push 후 torch 테스트 41 green 확인 ⓑ warm ckpt 경로/seed 확인 ⓒ **결선 3+3**: `TRAIN_MODULE=shepherd.scripts.train_m3a CONFIG=configs/m3a_s1_scratch.yaml OUT=results/m3a_playin/scratch REQUIRED_COMMIT=<본 커밋> bash scripts/run_ippo_seeds_parallel.sh` + warm 동형(SEEDS "0 1 2", GPU 분리 권장) ⓓ (병행 가능) o* 스윕 {3e-4,3e-3} × 1~2 seed = `--o-star` ⓔ 결선 후 `analyze_m3a_playin`(+선택: `eval_heldout_m3`로 규칙③ 입력) → 본선 arm 확정. **본선(10-seed S1→S3) 전 잔여 도구 1건**: Gate A/paper-grade용 seed-군집 bootstrap 하한 스크립트(analyze_p1 계열, clean_cross/capture 대상) — 캠페인 시작 전 커밋해 사전등록 유지 예정.

### 2026-07-07 (v) — M3a 설계 조건부 비준 → v0.2 확정, 구현 착수 승인

> 리뷰어 조건부 비준 + Hyunjun 승인. `docs/11_m3_design.md` v0.2 = 수정 4건 반영: ① **headline signed 불변식**(음수 유지·positive-only 클리핑 금지; Δ 의미 = M2-일관 hold-대비 level형으로 확정, 시간차형·smooth v_eff = ablation 노브) ② **o* 스윕 = S1-한정 scaffold 선택**(선택지표 = S1 train-eval 지표만, frozen held-out은 monitoring only) ③ **S1/S2 종료조건 강화**(S1: clean>0.2 ∧ boxed_fire<0.5 ∧ fire>0 / S2: frozen 도달 ∧ frozen-heldout clean 비영) + 웜스타트 결선 규칙(clean→boxed_fire→frozen clean→**동률 시 scratch**) ④ **판정 tier**(Gate A clean 하한>0 / Gate B capture existence / strong ≥2 seeds or ≥1% / paper-grade 하한>0) + M3b 진입조건(Gate A ∧ capture ≥2 seeds). fire-체인 분해 로깅 필수 목록(release_event·boxed_dwell 포함), r_geo step/fire 분리 + 게이밍 폴백(w_g→0.3~0.5), near-capture 보조항 = 2차 처방 예약.

- 다음 = **M3a 구현**: env 변형(m3 config + reward 모듈 + o/boxed obs) → 테스트(레벨형 signed headline lock·boxed→0 lock·역-U 형상) → 웜스타트 결선 3+3-seed(S1 200k, 서버).


### 2026-07-07 (u) — ✅ P4 서버 증거-잠금 완료: 40/40 발사 = boxed 분지 심부 — "release 채널" 필요성 실측 확보

> `p4_fire_geometry.py` 실측(4 정책 × 10판, nominal·fresh CRN 85M+): **fire_event 40/40에서 δ=0 boxed(n_open=0, 게이트 실측 v=1.000·clean=False)**. 방사 완화 스윕: **d_clean = None 전원**(+1.0 m까지 clean 부재), d_unbox = mappo_s7 >1.0 m / mappo_s8·coma_s7 +0.85~1.0 m / coma_s8 +0.2~0.25 m. 증거 = `results/p4_probe/fire_geom_*.json`.

- **잠긴 문장:** "Learned fire-mode policies sit **deep inside** the adjacent boxed basin, not near the razor-thin clean window; no clean configuration exists within +1.0 m of purely radial relaxation of their fire-moment geometry."
- **핵심 함의(설계 요건 B·함정 ③의 실측 근거):** clean은 "덜 조인" 상태가 아니라 **비-방사(축 정렬 채널) 형상** — 단순 완화 학습 신호로는 도달 불가, **compress→release 2단 행동**이 데이터로 지지됨. (s)의 (t) 예상("unbox +O(10cm)")보다 강한 결과 — 정책들은 창 옆이 아니라 분지 바닥에 있음.
- 서술적 노트: coma(blended) 정책이 mappo보다 얕게 조임(unbox 0.2 vs >1.0 m) — 과압축 경향 차이, n=2/2라 descriptive만.
- **P4 종결.** 다음 = M3 설계(요건 A·B·C + release 행동 지원).


### 2026-07-07 (t) — 리뷰 지침 채택: 프레이밍 교정 + M3 설계 3대 요건 + 서버 증거-잠금 스크립트 준비

> P4 (s) 결과에 대한 리뷰어 지침 접수·채택. **프레이밍 교정: "M2 계약 무죄" → "feasibility 무죄, findability 유죄"** — M2 계약은 clean을 불가능하게 만들지 않았으나 clean 학습에 부적합한 reward topology(boxed·clean headline 등가 + 면도날 창)를 만든다. 논문 배치 = failure analysis/design diagnosis(리뷰어 제공 영문 문단 verbatim 채택). **L2 추가 학습 금지 — 서버 lane은 진단만.**

- **서버 증거-잠금 스크립트 = `shepherd/scripts/p4_fire_geometry.py`(torch·서버 전용):** fire-모드 4본(mappo/coma × s7/s8, best-ckpt)을 nominal env에 10판 롤아웃, **fire_event 시점**의 ① env 게이트 실측값(v_soft·worst·p_feas·boxed·clean) ② pre-move 기하 스냅샷 ③ **radial 섭동 스윕**(리미터를 공격자 탄도축에서 δ∈[−0.2,+1.0] m 방사 이동) → δ_to_unboxed·δ_to_clean 부호거리. 기대 = "learned fire-mode sits in the adjacent boxed basin, not near the razor-thin clean basin" 문장 확보.
- **M3 설계 3대 요건(리뷰 채택, 설계 착수 시 반영):** **(A) boxed·clean headline 등가 제거** — boxed 시 v:=1.0을 그대로 headline으로 쓰지 말 것; `v_effective = v_soft·I(¬boxed)` 또는 `v_soft·σ(clean_margin/τ)`형 clean-호환 viability 분리(패널티 소량 부과로는 부족 가능). **(B) clean-근접 셰이핑** — 5~20 cm 창은 binary λ1로 못 찾음; signed clean-margin 보상 + "too loose / just right(clean capture-grade) / too tight(boxed)" 3분해로 **역-U형 기하 보상**(현행 단조 조임 보상이 over-compress→boxed의 원인). **(C) 커리큘럼 = 탐색 scaffolding 전용** — 학습 중 채널 폭 완화(θ·tolerance)→복원, **eval은 반드시 frozen 상수**, curriculum 성공을 main claim으로 쓰지 않음(3-스테이지: wide-clean → transition → final frozen).
- **함정 3종(기록):** ① boxed penalty만으론 headline farming 지속 가능 ② sparse clean bonus는 재실패 ③ **compress→release 2단 행동 필요 가능성** — clean capture는 "압축 → finisher 정렬 → clean 채널 하나 열어주기(release) → 발사"일 공산; 현 L2는 compress→over-compress→boxed. limiter의 "비켜서기"가 학습 가능해야 함(중요 발견 후보).
- 우선순위 재확인: 서버 진단(학습 아님) → **M3 설계**(A·B·C 필수 반영) → P3(L2 방어용, 그 다음) → P2 optional.


### 2026-07-07 (s) — ✅ P4 분석 lane: clean-fire reachable set **실존 확인** (capture-grade 포함) — 벽의 정체 = "면도날 창 옆의 뚱뚱한 boxed 분지"

> 리뷰 v2 체크리스트 ④(θ_fire=0.9 ∧ clean 동시 만족 reachable set 실존?)를 frozen 상수 그대로 수치 프로브로 판정. **답: 실존 — 4/4 대표 상태(x∈{12,16,20}, v∈{16,20,24}, union seed 0·1)에서 v_soft=1.0 ∧ ¬boxed 구성 발견, 전부 v_shot_worst=1.0(= capture-grade: 모든 feasible 도주가 그물 콘 안).** 도구 = `shepherd/scripts/p4_clean_probe.py`(numpy-only; 링 그리드 + 12-dim 랜덤 탐색 + 국소 정련), 증거 = `results/p4_probe/probe_*.json`.

- **단, 창이 면도날임:** 링-가족 그리드에서 clean 창 폭 = **ρ 방향 0.05~0.20 m**(항상 ρ≈kill_radius 2.0 부근, c=0.75), 정련 최적점의 p_feasible = **0.0004~0.0024**(2504 witness 중 1~6개만 도주 가능, 그 전부가 콘 안). 정련 기하 = 탄도 튜브를 ~2 m에서 감싸는 어긋난 나선형 4기 — cm급 협응 요구.
- **체크리스트 답변:** ① boxed 판정 과보수 아님(clean 구성과 명확 분리) — 진짜 범인은 **boxed 시 v_soft:=1.0 연속성 선택** → ⑥ **확인: 포위가 clean과 headline이 동일**(잘 조여 boxed로 떨어져도 보상 손해 0; clean의 추가 이득 = λ1/step + capture인데 탐색이 그 영역을 못 밟음). ② clean 정의 vs capture 기하 정합(capture-grade가 clean 창 내부에 존재). ③ "잘 조일수록 boxed" 정량화: 창에서 ρ 5~20 cm만 좁혀도 boxed 분지 — **뚱뚱한 boxed 분지 바로 옆에 붙은 hairline**. ⑤ λ1 관측성: 자연 구성공간에서 clean 영역 측도 ~10⁻³ → 무유도 탐색으로 사실상 관측 불가.
- **결론(리뷰 v2의 M3-전-필수 질문에 대한 답):** clean 0은 **계약의 구조적 불가능이 아니라 발견가능성(findability) 문제.** M2 동결 계약은 무죄 — M3 설계 입력: (a) clean 채널을 넓히는 커리큘럼(net_radius/half_angle/θ 스케줄 후 복원) (b) clean-근접 potential 셰이핑 또는 lobe-open 기하 prior (c) M3 보상 설계에서 boxed의 v:=1.0 headline 등가 재고(동결 아님 — M3는 신규 env). 추가 보너스: clean 구성은 공격자가 kill-radius에 안 들어가므로 **λ3 손실비용도 0** — clean이 boxed보다 전 항목에서 우월한데 오직 못 찾을 뿐.
- **캐비앗:** 정적 스냅샷 분석(리미터 순간 배치 가정 — 도달 동역학·공격자 closed-loop 반응 미포함), 링-가족+국소탐색(실존 증명이지 전수 지도 아님), 대표 상태 4점.
- **후속(서버 lane, 선택):** fire-모드 정책 4본(s7·s8×2arm)의 발사 시점 p_feasible/기하 측정 → "boxed 분지에 앉아 있음" 실측 확인(스크립트는 eval_heldout 확장으로 소품).


### 2026-07-07 (r) — 피어리뷰 v2 접수: "L2 게이트 PASS 방어 가능" — 클레임 문구 확정·우선순위 개편(P4 선행)·보조 통계 완비

> 전문 = `ANDES/URP/gpt_peer_review_L2_v2_2026-07-07.md`. 판정: **게이트 PASS 외부 확인**(scope 한정어 "under the frozen L2 scenario and reward contract" 필수), paired 분리 = "frozen setting 한정 blended > shared-only" defendable, 기전·일반화·capture = 여전히 open. 발사 모드 = main 아님·**중요 diagnostic**(제공 문구 채택).

- **채택 ① 논문 클레임 문단 = 리뷰어 교정본 verbatim**(§4 대체): 게이트 수치 → paired +1.91 CI → discovery는 "higher observed rate" descriptive → 결구 "stronger L2 training recipe **in this frozen setting**; mechanism·physical capture·generalization = open follow-up". 금지 목록 유지.
- **채택 ② 통계 표기:** 게이트 = one-sided 하한(사전등록 그대로), 효과 보고 = two-sided 95% CI 병기, seed = 최상위 군집 단위 유지, mode discovery 통계 claim 금지.
- **보조 통계 완비(기존 held-out 200판 데이터로 즉시 계산 — 전부 bootstrap 결론과 일치):** paired diff 9/10 양수 → **sign test one-sided p=0.0107**; **paired-t +1.909, two-sided 95% CI [+0.497, +3.322] (t=3.06, df=9)**; **exact sign-flip permutation(2¹⁰) one-sided p=0.0029**; **split-half 일관성**(ep0–99 vs 100–199): paired diff +1.934(8/10) / +1.885(9/10), coma 게이트 마진 +13.36 / +13.34 — 6.1·6.3 대응(독립 CRN set B는 여유 시 400판 확장으로 상위 호환 가능).
- **채택 ③ 우선순위 개편: P4(clean-condition 진단) → M3 → P3(소규모 병렬) → P2(optional/appendix).** 근거: 발사 모드로 게이트 도달이 열린 지금, clean이 왜 안 열리는지 모르고 M3 설계하면 M3에서 clean 0 재발 위험. **P4 = 학습 런 이전에 분석 진단 우선** — 리뷰 체크리스트 6항: boxed 판정 과보수성 / clean 정의 vs capture 기하 정합 / "잘 조일수록 boxed" 구조 모순 / **θ_fire=0.9 ∧ clean 동시 만족 reachable set 실존**(핵심; 명제 N 연장) / λ1 관측가능성 / 포위-장려 보상 모순. 진단 재료 기존재: fire-모드 정책 4본(s7·s8×2 arm) rollout + env 기하 검사.
- P2 판단 확정: M3-main 논문 → optional(가설 문구 "consistent with ... but unconfirmed" 사용); credit 논문으로 키울 때만 mandatory.


### 2026-07-07 (q) — ✅ P1 캠페인 완료: L2 게이트 본판정 PASS + main recipe 분리 확정 + "발사 모드" 발견 (`52e0046`)

> seed {0..9}×2 arm(레시피 동일) → held-out CRN 200판/ckpt(전부 best-ckpt, 코드 핀 `c58fceb` 단일) → 사전등록 규칙((p)) 그대로 판정. **① L2 게이트(D2-A): 양 arm PASS** — seed-군집 margin one-sided 95% 하한 = coma +12.59(vs scripted)/+15.65(vs hold), mappo +10.24/+13.28 (전부 ≫0). **② paired coma−mappo = +1.91, 95% CI [+0.83, +3.13] — 분리(separated)**, per-seed 9/10 양수(최대 s1 +6.37, 유일 음수 s9 −0.28) → **main recipe = coma mix 0.5 확정(사전등록 결정규칙)**. ③ mode discovery 80%(coma) vs 60%(mappo); arm 평균 return +16.41 vs +14.50.

- **리뷰 (o) 대응 현황:** Fatal-2(n=3 통계) **해소** — 10-seed·held-out·paired·CI 배제. Major-2(selection bias) **해소** — 선택(best-ckpt)/보고(held-out) 분리 실증: 학습기 eval과 held-out 일치(예: mappo s1 9.99/9.99), eval-overfit 신호 없음. Major-3(용어) 채택 유지. **잔여:** Fatal-1(클레임 하향 유지 — capture·clean 여전히 0), Major-1(P3 safe-scripted), Major-4(P2 cost-aware D — "기전" 주장은 여전히 보류, 현 주장은 성능 분리까지).
- **신규 발견 — "발사 모드"(train seeds 7·8, 양 arm 공통):** len≈29·penetrated 0·**wasted 1.00/판·fire 1.00/판**·clean 0 — v_soft≥0.9 게이트에 매 판 도달(boxed 경유)하고 발사(미스) 후 조기 종료, headline 16.0~17.8 선banking. 같은 train seed에서 arm 무관 발생 = **공격자 가족 랜덤화 draw가 게이트-도달 행동을 가르침**(rand 스트림이 train seed 함수). 함의: fire 체인의 남은 벽은 게이트 도달이 아니라 **clean(비-boxed) 조건** — 명제 N의 lobe-마스킹 서사와 정합, P4 진단 설계에 직접 정보(θ 완화보다 boxed 해소가 관건일 수 있음).
- **분포 노트:** coma는 8/10 seed가 차단 모드(blocking rate 0.99~1.00)로 수렴해 분산 작음(14.2~19.0); mappo는 3-모드 혼재(차단 6·셰이핑-only 2·발사 2)로 분산 큼(10.0~18.2). cost-gap도 coma 중앙값 ~1.5로 mappo보다 균질 — 3-seed 시점의 "s2 비효율(5.13)" 우려는 10-seed에선 꼬리 사례(s9 4.95)로 위치.
- **선언(비준 대기):** §5 Phase 6 = L2 게이트 **충족**. 다음 = ① 게이트 비준 + main recipe 고정(coma mix0.5 best-ckpt 10본 = M3 warm-start 후보) ② Phase 5 rollout GIF(차단·발사 모드 각 1) ③ M3 착수; P2(기전)·P3(baseline)·P4(fire 진단)는 M3와 병행 가능한 소규모 lane.


### 2026-07-05 (p) — P1 하네스 구현 + 프로토콜 사전등록 — 캠페인 대기

> 피어리뷰 (o) P1 실행분. **held-out paired eval 하네스 2본 + 테스트 8종** 구현, 아래 프로토콜을 **런 시작 전에 동결**(사전등록 — selection/reporting 분리 위반·사후 규칙 변경 방지).

- **`shepherd/scripts/eval_heldout.py`(torch):** 고정 ckpt(기본 `best`, 부재 시 `latest` 폴백을 meta에 기록) + 동결 obs-norm 로드 → **NOMINAL env, CRN held-out seeds `77_000_000+i`**(학습 eval seed `s·1e6+500k`·학습 episode seed와 전 캠페인 seed 0..9에서 서로소 — 테스트로 lock), 에피소드별 레코드(ret/len/headline/clean/wasted/captured/penetrated/truncated/fire_events/boxed_steps) + git_head·ckpt sha 기록. scripted/hold 베이스라인도 동일 CRN으로.
- **`shepherd/scripts/analyze_p1.py`(torch-free):** ① mode label = `truncated ∧ ¬penetrated ∧ ¬captured`(=차단), seed의 "발견" = blocking_rate ≥ 0.5 ② **seed-cluster hierarchical bootstrap**(seed 복원추출 → seed 내 에피소드 복원추출, B=10,000, rng 7) ③ **게이트 규칙: arm의 seed-군집 mean CRN margin의 one-sided 95% 하한 > 0을 scripted·hold 둘 다 충족 → L2 게이트(D2-A) PASS** ④ arm 비교 = 공통 train-seed paired diff(같은 CRN 에피소드), CI가 0 포함 시 "분리 안 됨"으로 보고(우월 주장 금지 — 리뷰 금지 claim 준수) ⑤ cost-gap·clean·fire·mode discovery rate 병기.
- **캠페인 설계(사전등록):** arms = `l2_mappo.yaml→results/mappo_run2` vs `l2_coma_mix05.yaml→results/coma_run2`(레시피 동일), **seeds {0..9}** = 기존 {0,1,2} 재사용 + 신규 {3..9}×2 arm = 14런(6-proc 야간 배치 3-5/6-8/9). 평가 = 20 ckpt × 200 에피소드. **결정규칙:** 게이트 PASS → L2 본판정 승격(D2-A 충족 선언); paired diff 분리 시 해당 arm = main recipe, 미분리 시 "동급 + discovery rate 차이"로 서술하고 recipe는 discovery rate·cost-gap 종합으로 선정(서술 강도 하향).
- 테스트 +8(t-free 6: 라벨·CRN 불일치 검출·margin/cost-gap·bootstrap 복원·게이트/paired 통합·비분리 케이스 + torch 2: 표면·seed 서로소) → **수집 146 = t-free 111 + torch 35**. frozen 4종 무접촉(eval은 make_train_env 재사용, env.py diff 0).


### 2026-07-05 (o) — 외부 피어리뷰 접수(§9 브리프 대상): "L2 게이트 조건부 pass / 논문 main 불가" — 대응 계획 수립

> 리뷰 전문 사본 = `ANDES/URP/gpt_peer_review_L2_2026-07-05.md`(repo 밖). 요지: **Fatal 2**(① fire 체인 미개봉 → "no-fire blocking policy" 공격 가능 = claim 하향 필요 ② n=3, 차단 모드 발견=이산 사건 → 통계 미달) + **Major 4**(약한 scripted baseline / last-3·best-ckpt selection bias / "COMA" 명명 과함 / 역-U 대안가설 미배제). 프레이밍 권고 = **M3 main, L2는 gate+training insight**(기존 방학 계획과 정합). 리뷰 자체 판정: "L2 gate로는 꽤 강함."

- **즉시 채택(문서·용어, 실험 불요):** ① 안전 claim 문구 채택 — "frozen L2 reward contract 하에서 CTDE MARL이 hold/scripted 대비 capture-viability surrogate를 크게 올리는 cost-aware shaping/blocking 행동을 학습; blended global-local counterfactual credit이 mode discovery를 개선(preliminary, seed-limited)". 금지 claim 4종(net-capture 학습·통계적 우월·역-U 기전 확증·fire 체인 해결) 준수. ② 논문 용어 "per-limiter hold-counterfactual credit (difference reward)"로 하향(코드명 `coma_D` 유지). ③ §9는 export 스냅샷으로 보존(수정 없음), 본 (o)가 대응 기록.
- **실험 우선순위(리뷰 채택, 실행 비준 대기):** **P1** = MAPPO vs mix0.5 **seed 3→8~10 확장 + held-out CRN paired eval 하네스**(선택지표 last-3/best-ckpt ↔ 보고지표 분리; seed-cluster paired diff + hierarchical bootstrap CI; mode discovery rate 별도 보고) — L2 게이트 판정을 논문급으로. 추산 14런 ≈ 6-proc 야간 배치 2~3회. **P2** = cost-aware D ablation(local 신호에 per-limiter loss-cost 포함, 3-seed) — 역-U 기전 직접 검증(mix 0.25/0.75보다 날카로움). **P3** = safe-scripted(비용 회피 barrier) baseline. **P4** = fire-chain 진단(θ_fire 0.8/0.75 완화 — **비동결 진단 전용 config**, test-only episode_len 선례 패턴; 완화→개방 여부→복원 유지 여부).
- **판정 함의:** L2 게이트(D2-A)는 "3-seed 서술적 초과"로는 조건부 — P1 완료 후 본판정으로 승격. Phase 4·5(재현성·sanity·rollout GIF)는 P1과 병행 가능.
- 다음 액션: P1 하네스 설계·구현(신규 WP; 코드/런북 = AI, 서버 실행 = Hyunjun) → P1 캠페인 → 게이트 본판정 → M3.


### 2026-07-05 (n) — ✅ Phase 2D 마감: mix=0.5 폴백 arm DoD 3/3 통과 — 역대 최고 지속 성능 + mix 3점 ablation 완성 (`4b3c708`)

> coma_run2(mix=0.5, 3-seed×500k recipe-v2): last3 = **+14.04/+16.67/+11.28 (mean 14.00)** → **vs_mappo 평균 +2.20**(2/3 seed 양수, s2 −0.52 캐비앗) ∧ coma_D 全 seed 全 구간 양수(lastq +0.040/+0.061/+0.047, Q1→Q4 단조 상승) ∧ headline +16.4~+17.8 → **2D DoD(D>0 ∧ COMA≥MAPPO ∧ Δv_shot>0) 통과 — Phase 2D 마감.** seed1 last3 **+16.67 = 전 실험 통틀어 최고 지속 성능**(직전 최고 = mappo_run2 s0 +14.97; peak_roll3 +16.91@eval23 = 종반 지속형, 일시 피크 아님).

- **차단 모드 도달 3/3**(mappo 1/3 · mix=1 2/3 대비) — 全 seed last3에서 len 80·pen 0·waste 0: D-credit의 발견-가속이 블렌드에서도 유지됨.
- **비용 신호 복원 확인:** cost-gap(headline−return) = {2.61, **1.08**, 5.13} — s1은 mappo 최고 seed(1.85)보다도 비용-효율적. 단 seed 간 편차 잔존(s2 5.13 ≈ mix=1 수준) — mix=0.5는 평균을 올리되 분포는 넓다는 캐비앗.
- **mix 3점 ablation 완성(全 arm recipe-v2 동일 통제):** mean return = mix 0 → **11.80** / 0.5 → **14.00** / 1.0 → **10.40** — **역-U**. per-limiter credit은 "적당량"이 최적: 문자형(1.0)은 −λ3 비용-실명, 무-credit(0)은 차단 모드 발견 저속. 2C↔2D 연결하는 논문 그림/표 재료.
- clean_cross·captured 여전히 全 0 — fire/capture 체인 미개봉(명제 N plateau 정합; λ1 커리큘럼 등은 후속 논의 대상).
- **다음(§5 잔여):** Phase 4 재현성 마감 점검(2B/2C 선반영분 확인) → Phase 5 조기 sanity(03 §D) + 차단 모드 rollout GIF → **Phase 6 = L2 게이트 판정(D2-A: seed≥3 baseline 유의 초과 — dod_margin 데이터 +8.2~+13.6으로 이미 충족권, 판정 문서화·비준 절차 필요).** 스윕(mix 세분화·하이퍼)은 게이트 직전 유보 원칙 유지; 게이트 후 exploiter probe(§7).


### 2026-07-05 (m) — ✅ 2D run 1 마감: DoD-1 PASS / DoD-2 FAIL / DoD-3 PASS — mix=1 비용-실명 정량 확인, 폴백 arm 준비 (`387b4c6`)

> 500k×recipe-v2 2-arm 캠페인: arm A `mappo_run2` last3 = +14.97/+9.99/+10.43(**ref mean +11.80**; 2C 200k의 9.05 대비 +30% = recipe-v2 효과) / arm B `coma_run1`(mix=1.0) = +14.21/+8.27/+8.72(mean 10.40) → **vs_mappo 평균 −1.40, 1/3 seed만 양수 = DoD-2 FAIL.** `limiter/coma_D_raw_mean` 全 seed 全 구간 양수(Q1→Q4 상승, last-quarter +0.032~+0.050, min>0) = **DoD-1 PASS**; headline 全 양수(+11.6~+17.2) = **DoD-3 PASS**. 증거 = `results/coma_run1/wandb_coma_dump.json`.

- **진단 ① 비용-실명 정량(사전 등록 캐비앗 (l) 적중):** cost-gap(=headline−return ≈ λ3 limiter loss-cost 지출) — mappo {1.85, 0.00, 0.00} vs coma {3.03, 3.33, 5.09}. 같은 차단 모드(len 80·pen 0) 매칭 비교로도 1.85 vs 3.03/5.09 = **1.6~2.8×**: mix=1에서 limiter 그래디언트가 공유 J의 −λ3 항을 못 보는 구조적 결과. 셰이핑-only 모드(len 23·pen 1.0)는 cost-gap 정확히 0 — 비용은 장기 차단 기동에서만 발생.
- **진단 ② D-credit = 차단 모드 발견 가속기:** 차단 모드 도달 coma 2/3 vs mappo 1/3, 도달 시점 조기화(coma s0/s2 ≈ eval 7–8 vs mappo s0 eval 20). **coma s0 peak_roll3 +16.90 = 역대 최고**(후반 진동으로 last3 +14.21 — best-sustained ckpt 저장분이 유효). mappo s0는 500k 종점에서도 상승 중(+15.8 final). n=3 캐비앗.
- **모드 지도(2D 기준 재확인):** len 80·pen 0 = 차단+셰이핑 / len 23·pen 1.0 = 셰이핑-only. clean_cross·captured·wasted 全 seed 0 유지 — capture 미개봉, 2C s1의 boxed-crossing 발사도 소멸(발사 시도 자체 0).
- **→ 결론: (l) 문서화 폴백 arm 발동 근거 완비.** D의 발견-가속 + 공유 J의 비용 신호를 **mix 0.5**로 결합 = `configs/l2_coma_mix05.yaml`(그 외 l2_coma.yaml과 동일; `mappo_ref=results/mappo_run2` 실존 → 이번엔 vs_mappo_last3 자동 로깅 활성). 3-seed, `OUT=results/coma_run2`. DoD 동일(D>0 ∧ vs_mappo≥0 ∧ headline>0). 착수 = Hyunjun 비준 대기.
- **인프라 노트:** ① wandb 0.28 offline = `WANDB_DIR/wandb/offline-run-*/run-*.wandb` **바이너리-only**(files/에 요약 json 없음, non-tty에선 종료 summary 블록도 미출력) → 히스토리 파서 `scripts/wandb_offline_dump.py` 추가(0.28 합성 런 왕복 검증; `key`→`nested_key` 마이그레이션 대응). ② coma_D류 지표를 wandb에만 싣지 말 것 — 차기 런 전 train_curve/summary 직접 기록 패치 후보. ③ 서버 git identity 설정 완료. ④ `.gitignore` 보강: `.venv-l2/`·`results/_*/`.


### 2026-07-05 (l) — Phase 2D 구현(해석적 COMA 배선) + 학습공학 recipe-v2 (`df41dd8`) — 캠페인 대기

> 학습공학 결정(Hyunjun 승인 "추천경로"): ① 500k steps + **lr anneal floor 0.1**(0-동결이 2C run-1 seeds 2/5 저분지 고착 원인 후보) ② rollout 512→1024·minibatch 256(업데이트당 ~12 에피소드 → advantage 분산 절반) ③ **best-sustained ckpt**(rolling last-3 margin 최고점 보존, 판정은 계속 last-3 — seed 2 중반 피크 유실 방지). critic 강화는 기각(실측 ev 0.85–0.95 = 건강). 스윕은 L2 게이트 직전으로 유보.

- **2D 배선(`shepherd/train/mappo.py`+러너):** `coma_mix∈[0,1]` — limiter advantage = (1−mix)·A_shared + mix·normalize(A_D). **A_D = 1-step 시프트된 해석적 coma_D의 (γλ)-할인 forward 합**(`coma_advantages`, compute_gae V≡0 재사용). **시프트 근거(인과성):** env.step은 pre-move 상태에서 coma_D를 계산 → step t 반환분은 행동 t−1의 결과물 — 러너가 한 행 뒤로 write-back(에피소드/rollout 꼬리 행은 D=0, rollout당 1행 손실 문서화). **γ_d=0.99·λ_d=0.95 기본**(transit 구간 크레딧; γ_d=0이면 문자적 매시점 D_i — ablation 노브). mix=0 = 2C와 완전 동일(가비지-coma 불변성 테스트로 lock).
- **⚠ 설계 캐비앗(Hyunjun 확인 요망):** mix=1(비준 문자형)에서는 limiter 그래디언트가 공유 J의 −λ3 손실비용 항을 안 봄 → 2B의 '비용-인지' 행동이 퇴행할 수 있음. 퇴행 시 폴백 arm = mix 0.5(config 노브 기존재). D-리턴 γλ-할인·1-step 시프트는 D1-A "바로 사용"의 시간축 해석 — 사후 비준 대상.
- **캠페인 설계:** arm A = `l2_mappo.yaml` recipe-v2 3-seed(`results/mappo_run2`) — 레시피 변경분 통제한 **2D의 공정 비교선**; arm B = `l2_coma.yaml`(= v2 + mix 1.0) 3-seed(`results/coma_run1`, `mappo_ref`로 vs_mappo 자동 로깅 — 병렬 실행이라 최종 비교는 오프라인). 6-proc 병렬 ≈ 6h. **2D DoD: `limiter/coma_D_raw_mean`>0 ∧ vs_mappo(last3) ≥ 0 ∧ Δv_shot>0 유지.**
- **테스트 +5** (coma 수학 손계산 대조·mix=0 불변성·reset zero 가드·write-back smoke) → **수집 138 = torch-free 105 + torch 33**. frozen 4종 diff 0.
- **⚠ 마운트 사고 이력(이번 세션):** Edit 툴 편집분이 **크기-보존 torn-view/플래핑**으로 3 py + yaml 1 손상 — git은 clean으로 인식(스탯 기반), `git add`가 구버전을 staging하는 사고 1회(`21642ee`→`df41dd8` amend로 교정). **대책 확립: 이 마운트에서 Edit 툴 사용 금지(heredoc/splice 전용) + staged-blob을 md5가 아니라 파싱으로 검증**(yaml/py 내용 assert). HEAD-바이트 강제 재기록(`git show HEAD:f > f`)이 뷰 리셋에 유효.

### 2026-07-05 (k) — ✅ Phase 2C 완료: MAPPO 6-seed, DoD 통과 (`be816f9`)

> 6-seed 병렬(코어 여유 활용, SEEDS 확장만으로 통계 2배) × 200k, 안정화 레시피 동일. **DoD(MAPPO ≥ IPPO) 통과: vs_ippo(last3) 6/6 양수, 평균 +2.318 (MAPPO 9.050 vs IPPO-3seed 6.732, +34%)**, min/max +0.44/+3.86. 베이스라인 margin +4.11~+7.53(2B보다 강함). NaN 0. §2의 "이득 작을 수 있음" 캐비앗은 비관으로 판명 — 단 비교 캐비앗 유지: 2C−2B = {중앙 critic, value-norm, ortho-init} 3요소, seed 수 6 vs 3.

- **질적 발견 ① 차단+셰이핑 결합 모드(seeds 2·3):** len 80·penetrated 0 유지하며 headline **12.6/13.5** — scripted(10.06)와 run-1 차단 모드(headline 음수)를 모두 초과. value-norm'd 중앙 critic이 80-스텝 장기 차단의 리턴 스케일을 제대로 가격한 결과로 해석((h) 진단의 직접 검증). 침투 저지 + reachable-set 압축 동시 달성 = 현재까지 최강 전술 결과(capture만 남음).
- **질적 발견 ② boxed-crossing 발사(seed 1):** wasted 1.0/판 = v_soft≥0.9 게이트 도달이 매 판 발생, 단 boxed_in이라 clean 아님 → 미스. 게이트 벽이 "포위 경유"로 뚫리기 시작 — clean(비-boxed) 도달이 다음 관문.
- **clean crossing 全 seed 0회 유지** → 2D(COMA per-limiter credit) 동기 그대로. λ1 보너스 미발화 상태에서 이 수익 — crossing 열리면 추가 상승 여지.
- seed 2 중반 eval 1점 −8.06 급락 후 회복 — last-3 판정이 이런 스냅샷 노이즈를 정확히 흡수해줌(판정 설계 검증).
- **다음 = Phase 2D:** env info의 해석적 `coma_D`를 limiter advantage로 배선(S8 baseline=hold 고정), DoD = D_i>0 ∧ MAPPO+COMA ≥ MAPPO ∧ Δv_shot>0 유지. 러너는 2C 것 재사용(advantage 대체만).

### 2026-07-04 (j) — Phase 2C 트레이너 구현: MAPPO 중앙 critic (`7e0e98d`) — 서버 런 대기

> 설계 결정 2건 비준(Hyunjun): ① **중앙 critic 입력 = 공유 obs 63차원** — 계획 문구의 문자적 env.state()(기구학 54)는 FSM(탄약·발사 상태)·v-트리플이 빠져 commit 전후 가치 변화를 못 가격함; obs 63 = state 54 + FSM 6 + vres 3 = 엄밀한 상위집합(§2 CTDE 정직화 노트와 정합). ② **MAPPO 트릭 ON** — value-target normalization + orthogonal init(hidden √2·policy head 0.01·value head 1.0). **ablation 캐비앗 명시: 2C−2B 차이 = {중앙 critic, value-norm, ortho-init} 3요소** — IPPO→MAPPO 비교 해석 시 서술할 것.

- **`shepherd/train/value_norm.py`(torch-free):** 리턴-타깃 러닝 정규화 — critic은 정규화 공간에서 학습, 부트스트랩·로깅은 denormalize. 근거 = (h) 진단의 "호위(~23스텝)↔차단(80스텝) 모드 간 리턴 스케일 드리프트로 critic 타깃 흔들림" — 타깃 정규화가 value-loss 지형을 정상화. 테스트 5종(torch-free).
- **`shepherd/train/mappo.py`:** GaussianActor/MixedActor(2B head 시맨틱 그대로, per-role critic 제거) + CentralCritic + **MAPPORollout: env step당 가치 스트림 1개** — 협력 공유 J라 GAE 1회·advantage 전 역할 공유(2B의 "N+1 critic이 같은 타깃 중복 학습" 아티팩트 제거) + MAPPOTrainer(단일 옵티마이저, 역할별 KL 진단, target-KL(max of roles) epoch early-stop, set_lr, ckpt에 value-norm 동승, explained_var 진단).
- **`shepherd/scripts/train_mappo.py` + `configs/l2_mappo.yaml`:** 안정화-2B 러너 패턴 전부 계승(obs RunningNorm·가족 랜덤화·lr linear anneal·eval 20판·last-3 판정) + **`ippo_ref`(results/ippo_run2) 자동 로드 → `vs_ippo` margin 로깅**(2C DoD = MAPPO ≥ IPPO 판정 재료 내장). 2B 대비 신규 진단 = critic/explained_var.
- **런처 일반화(`scripts/run_ippo_seeds_parallel.sh`):** TRAIN_MODULE·CONFIG 환경변수 — 2C: `TRAIN_MODULE=shepherd.scripts.train_mappo CONFIG=configs/l2_mappo.yaml OUT=results/mappo_run1`.
- **테스트:** +13(value_norm 5 torch-free + mappo 8 torch) → **수집 133 = torch-free 105 + torch 28**. 샌드박스 torch-free 28종 재확인 green. frozen 4종 diff 0.
- **다음(Hyunjun):** push → 서버 pull(ippo_run2 untracked 충돌 시 mv-aside) → 병렬 런처로 3-seed. 기대치 조정(§2 캐비앗): full-state obs라 2B critic도 이미 전역 정보를 봄 — 2C 이득은 {단일 가치 스트림·타깃 정규화} 경유가 주라 **작을 수 있음**; DoD는 "≥ IPPO"(동등 이상)로 설계돼 있음.

### 2026-07-04 (i) — ✅ Phase 2B 마감: 안정화 run 2, 3/3 seed DoD 통과 (`f7ae506`)

> run 2a 사고 기록: 첫 재런이 **구코드 비트-단위 재현**으로 판명(서버 pull 누락 — eval 10판·last3 키 부재·16자리 동일 수치가 증거) → 폐기. 부산물: 동일 코드·시드·GPU·휠이면 CUDA 200k-step 학습도 비트-재현됨(재현성 각주감). 대책 = 런처의 ancestor 체크(REQUIRED_COMMIT 미포함 시 launch 거부).

- **run 2 (안정화 레시피, 3-seed 병렬):** last3_margin(판정 지표) = **seed0 +2.642 / seed1 +5.793 / seed2 +2.589** — 全 양수, seed0 꼬리 6-eval 전부 양수(진동 소멸), 말기 KL→0(anneal 동결 의도대로), NaN 0. **§5 2B DoD("hold·scripted 유의 초과, NaN 0") 충족 — 2B 마감.** 베이스라인 동일(hold 0.000/scripted 3.058). capture 0·clean crossing 0회는 설계·기대대로(net 2.0<reach 2.4; 협응 한계 = 2C/2D 동기).
- **병렬 실행 도입:** `scripts/run_ippo_seeds_parallel.sh`(`fb03c30`+`51586e4`) — seed당 1프로세스, 같은 GPU CUDA time-slicing(VRAM 0.5GB×3), CPU가 실자원이라 프로세스당 BLAS 2스레드 캡+nice 10(총 ≤9/24코어), PYTHONUNBUFFERED 실시간 로그, 종료 시 last3 요약 자동 출력. 벽시계 6.5h→~2.4h(sps 23.5×3). run 2는 이 런처로 실행.
- **관찰:** 안정화 후 수렴점이 run 1 대비 보수적(seed1 8.85 유지, seed0/2 ~5.7) — anneal이 최고점 사냥 대신 분지 안착을 고정한 효과로 해석(판정은 어차피 margin>0). eval 20판 + last-3 평균으로 스냅샷 노이즈 억제 확인.
- **다음 = Phase 2C(MAPPO):** 2B actor 그대로 + `env.state()` 중앙 critic 추가; value-norm(PopArt)·ortho-init 후보 이월분 여기서 검토; 병렬 런처 재사용.

### 2026-07-04 (h) — 2B run 1 결과(2/3 초과) + 진단 + 안정화 레시피(`cef170f`) — 재런 대기

> 서버 bring-up(Server 4, RTX 4090): py3.8뿐 → /data에 miniconda py3.10 → venv; torch 2.12.1 cu 휠 부재 → **2.6.0+cu124** 대체(API 전부 호환, CUDA는 원래 비트-재현 비대상); **V1–V4 green(pytest 118)**. 학습 sps≈29(env CPU-bound, GPU는 업데이트만). 곡선·summary = `results/ippo/`(`99937a1`).

- **run 1 (3 seeds × 200k, config 그대로):** 베이스라인 hold 0.000 / scripted 3.058. **seed1 = 8.50(margin +5.44, 81k 이후 7–10 지속)**, **seed2 = 9.80(+6.74, 단조 상승)**, seed0 = 2.39(**−0.66**, 진동 −5.2~+8.0, 82k 피크 +4.9). NaN 0·낭비발사 ≈0. **DoD(3-seed 유의 초과)는 미통과(2/3).**
- **발견 ① 비용-인지 셰이핑 = 우월성의 원천:** scripted는 headline 10.06을 벌지만 리미터 kill-radius 노출로 −7.0 지불(net 3.06); seed2는 headline 9.90을 **손실 ~0**으로(9.80). 학습이 "같은 Δv_shot을 희생 없이"로 이김 — λ3 비용축이 학습 가치 주장의 실증 근거.
- **발견 ② 차단 모드(seed0):** len 80·penetrated 0 — scripted 불가능한 정성적 신행동. 단 J가 Δv_shot 중심이라 저보상 + 차단 중 headline 음수 구간 존재(차단↔v_shot 상충 가능). S6 동결 유지 — 관찰만 기록(M3 논의 재료).
- **발견 ③ clean crossing 全 seed 0회:** λ1 무발화·fire 침묵(게이트 규율은 유지). 독립 학습으로는 θ_fire=0.9 협응(lobe 마스킹)이 안 나옴 — scripted도 동일(명제 N plateau 정합) → **2C(중앙 critic)/2D(COMA credit) 진입 근거가 데이터로 확보.**
- **seed0 진단:** (a) 다봉 보상 지형 — 호위-셰이핑 vs 차단 분지 사이 경계 착석, eval마다 모드 플립 (b) 상수 lr 3e-4 + 고정 10 epoch → 후반에도 드리프트 지속(KL 0.01–0.03 유지가 증거) (c) 공유 J + 팀 모드 스위칭 → critic 타깃 통째 이동, advantage 노이즈 증폭(MARL 비정상성 — 2C/2D 완화 대상) (d) 최종 1점 결정론 판정 = 진동 과장 아티팩트.
- **조치(`cef170f`, SOTA 표준·최소침습·비교성 보존):** ppo.py additive — `PPOConfig.target_kl`(기본 None = Phase-1 불변) epoch-평균 KL 초과 시 잔여 epoch skip + `epochs_ran` 진단 + `set_lr()` 스케줄 훅 / 러너 `loop.lr_anneal=linear`(양 역할 lr→0) / **판정 지표 = last-3-eval 평균 margin**(`dod_margin_last3`) / eval 10→20판 / 양 역할 target_kl=0.02(run 1에서 finisher KL 0.02–0.03 hot). 테스트 +2(early-stop 경계·set_lr) → **120 수집 = torch-free 100 + torch 20**. value-norm(PopArt)·ortho-init·병렬 env는 **2C 이월**(레시피 비교성).
- **다음 = 재런(Hyunjun):** push → 서버 `git pull` → 동일 명령 3 seeds(레시피 변경이라 전 seed 공정 재판정). **2B 마감 기준 = 각 seed last3_margin > 0 ∧ NaN 0.**

### 2026-07-03 (g) — Phase 2B 트레이너 구현: IPPO (`54dfdeb`) + 32f991f lane 위 착수

> 리뷰 lane `32f991f` 확정·검증(env.py 미변경·`python -m shepherd.params` drift OK·n_samples 2000·yaml 3키 additive 값불변)은 직전 세션 완료 — 그 HEAD 위에 2B 트레이너를 얹음. **학습 실행은 아직**: DoD(베이스라인 유의 초과) 판정은 랩 서버 런. frozen 4종(env.py·03·m2_l2_train.yaml·exchange.py) diff 0.

- **`shepherd/train/ippo.py`:** `MixedActorCritic` — finisher 혼합 head **Bernoulli 확정**(§5 2B 오픈항목 close): axis 3 Gaussian + fire Bernoulli, 저장 fire = 정확한 {0,1} 샘플 → PPO ratio 정확(Gaussian+threshold 기각 사유: 실행 액션에 없는 밀도를 저장 — Phase 1이 박스에서 수용한 clipped-density 워트가 hard binary에선 악화). `MixedPPOTrainer` = Phase-1 `PPOTrainer` 상속(update/save/load 그대로, 네트워크만 교체; `(obs_dim, act_dim, cfg)` 시그니처 유지 → ckpt roundtrip 무변경). `limiter_inputs` = **one-hot agent-id 부착**: env obs가 전 에이전트 동일 full-state(§2 CTDE 정직화)라 ID 없는 공유 정책은 순열-퇴화(4기 동일 분포 → 비대칭 escape-lobe 역할 불가). env 동결 무접촉(트레이너측 부착).
- **`shepherd/train/obs_norm.py`(torch-free):** RunningNorm — §7.1 'obs normalization 미탑재' 해소. env step당 1회 update(공유 obs), eval 동결, ckpt 동승, one-hot은 비정규화.
- **`shepherd/train/attacker_rand.py`(torch-free):** §7 (c) ① 구현 — per-episode iid 공격자 **가족** 랜덤화, strict `make_train_env`를 deep-copy cfg로 재조립(frozen YAML/dict 무변조 = 테스트 lock). 구현 가족 = {att_speed, adversary_start_x, adversary_omega, adv_a_max}; **adv_a_max 하향-전용 [21,30]** — 백엔드 KinematicLimits.a_max가 physics.a_att_max(30)와 동일 소스라 초과분은 조용히 클램프될 것 + actual≤surrogate가 S14 보수성 유지. a_lat_max는 adv_a_max 기본값 경유로 커버; amp(1.8)·react_on_commit은 frozen env.py가 고정 인자로 호출해 배선 불가(가족 밖). **surrogate physics.a_att_max 불변**(θ_fire 0.9·zero-waste 밴드 캘리브레이션 보호). eval은 nominal 고정(베이스라인 비교성).
- **`shepherd/scripts/train_ippo.py` + `configs/l2_ippo.yaml`:** 러너 — 정책은 **정규화 [-1,1] 액션 공간**(러너가 env bounds로 스케일; raw ±30에 std 1이면 박스 ~3%만 탐험 + LOG_STD clamp(e²≈7.4)로 박스 스케일 도달 불가), **γ/λ = 0.99/0.95 재설정**(§7.1: 0.9는 Pendulum 토이 튜닝), decentralized critic 2개(`env.state()` 미소비 = 2C 몫), wandb 옵션(offline-friendly, 부재 시 자동 skip) + JSON 곡선 상시, eval = hold_position·scripted_shaping 베이스라인과 **동일 시드** 비교(`dod_margin` 로깅), 전역 시딩 러너 소유(ppo.py 계약 복제). 트레이너 노브는 l2_ippo.yaml 전용(frozen m2_l2_train.yaml은 read-only 포인터).
- **테스트:** +19 — obs_norm 6 + attacker_rand 5(torch-free, 샌드박스 green; frozen-cfg 무변조·surrogate 불변 lock 포함) + train_ippo 8(torch-marked: mixed-head log-prob 수동 대조·{0,1} fire·ckpt roundtrip·러너 8-step 실환경 smoke·eval 번들). 수집 = **100 torch-free + 18 torch = 118**. 기존 make_env·env_spaces 28 green 재확인(회귀 0). 커밋은 stale index.lock/HEAD.lock mv-aside 후 정상(staged/HEAD blob md5 검증).
- **다음 = 서버 실행(Hyunjun):** push → bring-up(V1–V4) → `python -m shepherd.scripts.train_ippo --config configs/l2_ippo.yaml --device cuda --seeds 0 1 2 --output results/ippo` (tmux). 개산: 512 env-step/update, 54ms/step(샌드박스 실측) 기준 200k step ≈ 3h/seed — env가 CPU-bound라 GPU는 update만; 서버 단일코어 성능에 따라 ±. DoD 판정 = eval `dod_margin` > 0 유의(seed≥3).

### 2026-07-03 (f) — 코드리뷰 lane 마무리: 파라미터 레지스트리 + GPT 리뷰(gae/ppo/make_env) 하드닝

> (e)의 "병렬 세션 충돌 기록"에 언급된 코드리뷰 lane 산출물의 마무리 커밋. (e)가 torn-read로 HEAD 복원했던 gae.py 검증·roles.py docstring은 여기서 재적용(정상 변경이었음). m2_l2_train.yaml 키 추가는 Hyunjun이 "깃헙 작업 마무리" 지시로 비준.

- **`shepherd/params.py` 신설 (파라미터 단일 조작점):** 전 파라미터 ~100개 레지스트리 — value/units/**status(MEASURED·DERIVED·CALIBRATED·ASSUMED·TUNED·RESERVED·DEAD)**/wired(config·kwarg·frozen-code·code-default·doc-only)/consumer/provenance. `as_config(overrides)` → `make_train_env()` (동결 YAML 무접촉 실험 경로) · `as_ppo_config()` · `check_frozen_yaml()` = 레지스트리↔동결 m2_l2_train.yaml drift 검증 (`python -m shepherd.params`). **리뷰 발견 dead param 2건 문서화:** ① env `capture_thresh=0.95` — 저장만 되고 미사용 (실제 포획판정 = fire 시점 `worst>=1 ∧ ¬boxed`, env.py frozen이라 문서화만) ② env→scripted adversary `omega_att_max=8.0` — 함수가 미사용 (실제 heading slew = backend `adversary_omega=10.0`).
- **GPT 리뷰 반영 — `ppo.py`:** ① update()에 **buf.full 가드** (부분 rollout의 zero-tail 학습 차단) ② minibatch shuffle **RNG를 trainer state로** (매 update 동일 permutation 재생 버그 — 학습 궤적이 바뀌므로 Phase 1 기록 수치의 bit-재현은 커밋 `52a7d58` 기준으로만 유효) ③ **log_std forward clamp [-5, 2]** ④ clip_fraction_action **tolerance 비교** ⑤ unused import 제거. **전역 시딩 = 러너 소유로 명문화** — `train_ppo_toy.seed_everything`이 이미 담당 (docstring에 소유권 명시, MAPPO 러너도 복제할 것).
- **GPT 리뷰 반영 — `gae.py`:** 입력검증 추가 — rewards 1-D · gamma/lam ∈ [0,1] · dones ∈ {0,1} (+ 테스트 1종).
- **GPT 리뷰 반영 — `make_env.py`:** ① **하드코딩 backend limits 승격** — finisher_a_max/finisher_v_max/adversary_omega를 `train.limits` **필수** 키로 (m2_l2_train.yaml **additive 핀, 값 = 기존 하드코딩과 동일(1.0/1.0/10.0) → 동작 무변경**) ② `_req` Mapping 타입검사 ③ layout 벡터 `_vec3` 길이검증 ④ x_fire 몽키패치 경고 주석 강화 (Layout은 frozen env.py 소속) ⑤ **reserved-dim 패딩 유틸 분리** → `shepherd/train/action_dims.py` (make_env가 re-export — adapter.py 기존 import 무접촉 호환, smoke 6종 green 확인) + `pad_env_actions(expected_agents=)` 누락-agent 가드.
- **경미 수정:** rollout_gif.render() θ_fire 기준선 하드코딩 0.8 → config 값 표시 (summary["theta_fire"]) · m2_clean_viability_demo.yaml net_radius=1.5 stale 주석 정정 (pre-N1 legacy; grounded = 2.0) · roles.py judge docstring `{point_mass, se3}` → `{point_mass, se3_cone}`.
- **테스트:** +8 (make_env 4 · ppo_update 3 · gae 1) → **전체 99 수집 = torch-free 89 + torch-marked 10, 로컬 venv(torch 2.12.1+cpu) 전부 green** (adapter smoke·batched-eval 포함). frozen 계약: env.py(=e99ff34 비준 예외 반영본)·03·exchange.py diff 0.
- **리뷰 판정 요약:** 계획(09) ↔ 코드 정합 — 실질 모순 없음. GPT 이월 항목 = per-agent GAE done 시맨틱·중앙 critic 버퍼 재설계 → 2B/2C 설계 항목(기존 계획과 일치).

### 2026-07-03 (e) — Phase 2A 완료: batched-eval 구현 + 어댑터 smoke (`e99ff34`+`b3ff97e`)

- **⑤ batched-eval 구현(비준된 env.py 유일 동결 예외):** additive `viability.eval_union_with_limiter_sets`(기존 함수 무변경) + env.py step() call-site 1건 교체(+29/−10 단일 영역, legacy n_segments=1 경로 원문 보존). **equiv lock = `tests/test_batched_eval.py` 5종** — 함수-레벨(양 judge·turn-limited·kr=0·empty·boxed, 全 필드 비트-동일) + env-레벨(step() coma_D/headline/v-triple == sequential 재계산 참조; **스왑 전 green 확인 후 스왑, 스왑 후에도 green** = 진짜 lock). **실측 env.step 117.3→54.4ms(2.16×)** — 2A′ 모델 프로젝션(74ms)보다 좋음(모델 비관 편향과 정합).
- **어댑터(`shepherd/train/adapter.py`, torch-free):** make_train_env 강제, live-dim 정책→`pad_env_action`, adversary zeros 주입(env-scripted), coma_D/headline 크레딧 분리 추출, `env.state()` 노출(2C 중앙 critic), `collect_episode`(GAE 부트스트랩용 terminal obs 포함 T+1), `random_policy`(bounds 준수·fire Bernoulli). smoke 6종: full-episode NaN-free(2 seeds)·**R2 게이트가 fire 스팸 전량 기각**(v_soft≪0.9 → fire_event 0·k=1·wasted 0; commit 체인 도달은 shaping 필요 = 2B+)·truncation 분기(test-only episode_len=5 오버라이드, frozen YAML 무접촉)·CTDE 공유 full-state obs·reserved-dim 패딩/bounds·seed 재현성.
- **✅ 2A DoD 충족(정직 캐비앗):** "episode_len=80 완주"는 이 corridor에서 불가능(scripted 적이 ~23스텝에 penetrate = 자연 종료) — full-episode-to-natural-end + 명시적 truncation 분기 검증으로 충족 처리.
- **검증:** 커밋 트리를 `git archive`로 추출해 독립 실행 — **71 green**(batched 5 + smoke 6 + union_equiv·coma·make_env·env_spaces·nsegments·ppo_gae·viability). fire_gate_calibration·net_forward(무접촉 도메인)은 push 후 CI 관례. 수집 = **84 torch-free + 7 torch = 91**.
- **⚠ 병렬 세션 충돌 기록:** 작업 중 트리에서 별도 세션(코드리뷰 lane, 로컬 py3.14) 산출물 발견 — `shepherd/params.py`(파라미터 레지스트리)·`shepherd/train/action_dims.py`(패딩 유틸 분리) 미추적 + `make_env.py` 리팩터 WIP(샌드박스 뷰에서 널바이트 torn-write). **전부 커밋 미포함·미접촉** — 마무리·커밋은 Hyunjun 로컬 몫(리팩터 문구상 m2_l2_train.yaml 키 추가 언급 = frozen 비준 필요 사안 포함).
- **⚠ 마운트 대란 기록(이번 세션 계보):** viability.py Edit 절단 1건(heredoc 복구) → gae.py·roles.py·tests/test_env_spaces.py torn-read(HEAD 바이트로 복원; git index는 clean이었음 = 뷰-손상) → **`.git/index` 자체 널바이트 손상 2회** → mv-aside + **`GIT_INDEX_FILE=/tmp` plumbing**(hash-object/write-tree/commit-tree/update-ref, /tmp 사본 md5 검증)으로 커밋. 대형 파일 Edit 툴 사용 중단, python-splice/heredoc 고정.
- **다음 = Phase 2B(IPPO):** limiter 파라미터-공유 정책 + finisher 별도 정책(decentralized critics), obs running normalizer(§7.1), fire **Bernoulli head 확정**, wandb 로깅 시작, scripted 공격자 파라미터 랜덤화 config(§7), γ/λ 재설정. **랩 venv 필요(torch)** — 샌드박스는 여기까지.

### 2026-07-03 (d) — Phase 2A′ 완료: v_shot throughput 스파이크 (측정-전용, frozen diff 0)

- **실측 프로파일(샌드박스 2-core):** env.step **117ms**(중앙값 116, 이전 기록 133과 정합) — 병목은 MC 빌드가 아니라 **per-layout 거리마스크 eval E≈14ms×7회**(vfull/vbase/coma×4 + post-move obs `vres2` 재빌드). union 빌드 B≈3.6ms, 낭비 draw(union 경로에서 미사용 `reachable_accels`) 0.25ms. random 정책 에피소드 ≈**23스텝**에 penetrated 종료(80 아님).
- **① n_samples(CRN-paired, 같은 상태·seed):** bank 상태(비관여, v_soft≤0.22)에선 err_max≤0.04·판정일치 100%(공허 — 리미터 마스크가 안 물림). **near-gate 합성 상태(리미터 링 관여, ref v_soft 0.51–0.97)에선 err_max: n=1000→0.088, n=500→0.190 > zero-waste 밴드폭 0.15** → 축소 위험. 속도 knee도 n≈500(그 밑은 extreme 블록이 E 지배, 이득 정체). **비준: 학습 n_samples=2000 유지**, n-cut은 디버그 오버라이드 전용(비준값 무변경).
- **⑤ batched eval(신규, exact):** 6 layout이 unique 리미터 **8개**(현재4+p0 4)만 공유 → 거리마스크 1회 + layout별 boolean-any = **59.9→25.3ms(2.4×), 12상태 전수 비트-동일(mismatch 0)**. **비준: env.py 동결의 유일 예외로 승인** — additive viability 헬퍼 + step() call-site 교체 + equiv 테스트 lock, **구현은 2A에서**. obs-lite(vres2 제거/재사용, 추가 ~20ms)는 obs 의미 변경이라 **보류**.
- **② cadence:** k=4 ≈ 1.5×(모델 프로젝션). batched 채택 시 사실상 무의미(6-eval→~2E) → 미구현. **③ 병렬:** 2-way efficiency 0.83 실측.
- **✅ DoD(벽시계 경로) PASS:** 1e6 step = 베이스라인 그대로도 **16w ≈ 2.94h < 4h**; batched 채택 시 1.52h(16w)/0.76h(32w). 단일 env 10×는 미달(exact 조합 최대 ~2.8×) — DoD가 OR 조건이라 게이트 통과. 정확도 열화 기록 완비(near-gate 캐비앗 포함).
- **산출:** `shepherd/scripts/spike_throughput.py`(profile/sweep/batched/gate/parallel/report 페이즈) + `results/spike_throughput/`(spike_results.md + profile·batched·gate·parallel.json + sweep_rows.jsonl + state_bank.json). **캐비앗:** 컴포넌트-합 모델은 실측 대비 ~20% 비관적(143.8 vs 117.3) — 표는 비관 측 기준; 절대치는 랩 서버에서 재측정.
- **마운트 truncation 3건 재발·복구**(spike 스크립트 Write 2회 + 09 문서 Edit 중 1회 → heredoc 재기록, md5×2+파스 검증). 규율 유지.
- **다음 = Phase 2A:** 어댑터 smoke + 비준된 batched-eval env.py 반영·equiv lock.

### 2026-07-03 (c) — 공격자 강도 논의 → 랜덤화+exploiter probe 비준

- **Hyunjun 문제제기:** "약한 scripted 적 상대로 학습하면 무의미 수렴 아닌가 → 공격자도 학습 필요?" **정리:** (a) keystone 공격자는 이미 closed-loop 반응형(commit-후 dodge), (b) v_shot = 기동 집합 지표라 성공기준은 오염 안 됨, (c) 단 **상태분포 편향은 실재** → §7 신규 오픈 항목으로 비준: ① M2 scripted 파라미터 랜덤화(2B 진입 시) ② L2 게이트 후 exploiter probe(freeze 방어자 + adversary PPO = exploitability 측정, co-training 아님) ③ self-play = S13 유지(Gavin 선점, novelty 아님). env·계약 diff 0 — 문서만 변경.

### 2026-07-03 (b) — 명제 N 초안 + LiCS 서버 결정 반영

- **`docs/10_shaping_necessity_prop.md` 신설(DRAFT v0.1, AI 초안 — Hyunjun 비준 대기):** novelty 보강 ①의 실행. 1D deploy-delay net 인스턴스에서 (a) 무-shaping이면 게이트 설정과 무관하게 방어가치 0(보수 게이트 = 침묵, 느슨한 게이트 = miss-is-free 귀납으로 낭비), (b) 2-limiter escape-lobe 마스킹이면 v_soft 5/6→1로 clean crossing 강제 + worst-case 확실 포획. M2 상수 정합: plateau ρ/w = 5/6 ≈ 0.833, θ_fire = 0.9 ∈ (5/6,1] = shaping-forcing 창, Δv = 1/6, 레거시 0.8 낭비의 이론형, zero-waste 밴드 [0.85,1] 하한과 일관. 비준 체크리스트 = 문서 §5.
- **LiCS 랩 서버 사용 확정(사용자)** → 2A′에 반영: 병렬화 여유 ↑, DoD 벽시계 재산정; n_samples·coma_D 주기화는 디버그 반복속도 때문에 유지.

### 2026-07-03 — 코드-문서 정합 스위프(실질 이슈 6건) + novelty 지형 업데이트

**정합 스위프 (전부 env.py·03·exchange.py·roles.py diff 0 유지; 결정 3건 = Hyunjun 비준):**
1. **컴포지션 루트 함정 해소** — `shepherd/train/make_env.py` 신설: `make_train_env(cfg)` strict 핀(episode_len·layout·limits·cone 누락 시 raise). `m2_l2_train.yaml`에 `train:` 블록 추가(**기존 비준값 무변경**, episode_len=80 최초 config 명기 — 그 전엔 Layout 기본값에만 존재, demo 루트는 70). `rollout_gif.build_env`에 경고 주석.
2. **죽은 action 차원 → RESERVED + 어댑터 마스킹 [비준]** — pressure/slew는 env 수신-무시로 명시(§2), 학습기는 live 차원만 출력 + `pad_env_action` 0 패딩. 구현/제거안 기각(동결 유지).
3. **CTDE 서술 정직화 [비준]** — §2에 "실행도 full-state 공유(중앙화)" 명기, 논문 서술 지침 + local-obs 마스크 = 2C 후 stretch. 03 frozen이라 09에서 계약 주석으로.
4. **`turn_limited` = reserved 문서화 [비준]** — parsed-but-inert 명기(configs 주석 + §2). wire-through는 S13/S14 때.
5. **기록 정정** — "torch-free 72"는 부정확: **72 수집 = torch-free 65 + torch-marked 7**(§5 정정). CRN 정확상쇄(union 1회 구축 + 마스크 교체) 코드→§2 문서화.
6. **00_status '앞으로' 절에 09 포인터 + 06 실습 박스 실측 체크.**
- **테스트:** `tests/test_make_env.py` 8종 추가(모두 green, torch-free) → 수집 65+8=**73 torch-free + 7 torch = 80**. 전체 스위트는 샌드박스 45초 제한으로 로컬 재확인 불가(무거운 MC) — **push 후 GitHub Actions로 확정**.
- **마운트 truncation 6건 재발·복구**(m2_l2_train.yaml·m2_default.yaml·rollout_gif.py·00·06·09) — heredoc 재기록 + AST/파스·tail 검증. 규율 유지. stale `index.lock`은 mv-aside 후 커밋 정상(`c489f5d`, staged/HEAD blob md5 검증).
- **계획 현실성(실측 기반):** 133 ms/step → **throughput 스파이크를 2A′(2A 직후 반나절)로 승격**(§5). 잔여 ~8.5주 추정: 2A 1–2일 → 2A′ 0.5–1일 → 2B 1–2주(§7.1 이월 전부 여기서 터짐, 최대 리스크) → 2C 3–5일 → 2D 2–3일 → Phase 4–6 1–1.5주 ⇒ **L2 게이트 ≈ 8월 초·중순 = 현실적**. M3(S9 raid env)는 신규 build 2–3주(exchange.py 13줄 stub, env는 K=1 고정) → **방학 목표 = L2 게이트 + M3 1차 frontier-shift 그림 1장 + 초고 스켈레톤, 제출은 가을**.

**Novelty 지형 업데이트 (2026-07-03 검색; 3-way 교집합 생존, 다리들 붐빔):**
- **Gavin arXiv:2603.16279 실재 확인** — 1v1 net 요격 competitive PPO(JAX 고충실도) → **"net+RL" 단독 다리 완전 사망**(부품으로만). 팀 shaping·유한탄 경제 없음 = 교집합 무사. must-cite.
- **Von Moll turret+defender = IEEE 정식 게재**(ieeexplore 11303548) — arXiv 인용 갱신 필요. 같은 그룹 **multi-attacker conical 확장 진행 중(arXiv:2509.13564)** → 선점 시간 압박 실재.
- must-cite-adjacent 추가 후보: **adversarial/safe herding reach-avoid(arXiv:2509.08460)**, **RL 요격 우선순위 배분(arXiv:2508.00641, 공개코드)**.
- intro 동기 강화: 2026 cost-exchange 담론 — CSIS interceptor-inventory 고갈 분석, MWI cost-exchange-logic 기고.
- **보강 옵션 우선순위(build 지연 최소 기준):** ① **"shaping 필요성" 최소 명제**(miss-is-free+유한 K에서 shaping 없으면 best-response 적이 v_shot<θ_fire 유지 → 방어가치 0; 1D 인스턴스 명제+스케치, Hyunjun-lane 사고 작업, 코드 불필요 — backdiag 1.0→0.16의 이론 격상) ② **S14 = "provably non-optimistic training signal" 프레이밍**(기존 코드 재프레이밍 = 구조적 기여) ③ **fire-gate θ*를 shoot-look-shoot doctrine 결과로 접속**(fire_gate_calibration 산출물 재사용, 그림 1장 공짜) ④ 해석적 counterfactual credit은 헤드라인 불가(COMA·Agogino/Tumer·AAMAS'24 프리아트) — method bullet + D1-A 2단계 ablation으로만.

### 2026-07-01 (b) — Phase 2 사다리 재구성
- **§5 Phase 2를 4-rung 사다리로 재작성**(2A adapter smoke → 2B IPPO → 2C MAPPO → 2D COMA ablation). 기존 통짜 "Phase 2 MAPPO + Phase 3 COMA" 흡수. GPT 제안 채택 + 4개 보정: (1) 이종 env라 "N-agent 완전 공유"는 틀림 → limiter만 공유·finisher 별도·adversary scripted 명시, (2) 혼합 action head(finisher fire Bernoulli)는 finisher 정책 첫 등장하는 **2B에서 확정**, (3) 2D COMA = **해석적 `coma_D` 먼저**(D1-A 1단계, 학습 critic은 Phase 6+), (4) `v_shot` throughput 병목은 **2C에서 물림** → supersuit 벡터화/n_samples 튜닝 2C로 당김.
- **부산물:** 2B/2C/2D = IPPO/MAPPO/+COMA **ablation 사다리** → Phase 6 baseline 비교표로 그대로 재사용(중복 0).
- **Phase 4 축소:** wandb·checkpoint→2B, 벡터화·throughput→2C 로 선반영, Phase 4는 재현성 마감만. §7 혼합 action head 포인터 2B로 갱신.
- **다음 세션 착수점 = Phase 2A**(shepherd ParallelEnv 어댑터 smoke, random 정책).

### 2026-07-01 (a)
- **Phase 1 완료 — from-scratch 단일 에이전트 PPO 코어 + 토이 수렴.** 커밋 `52a7d58` (브랜치 `feat/l2-mappo-train`).
- **산출:** `shepherd/train/gae.py`(torch-free GAE, per-step next_values로 truncation/termination 부트스트랩 분리) · `shepherd/train/ppo.py`(ActorCritic·RolloutBuffer·PPOConfig·PPOTrainer + checkpoint save/load) · `shepherd/scripts/train_ppo_toy.py` + `configs/ppo_toy.yaml` · 테스트 2종(gae torch-free 6 + update/checkpoint torch 7) · `pyproject.toml` `torch` 마커.
- **plan-mode 리뷰 반영(사용자 must-fix 5 + nice-to-have 5):** ① gymnasium 1.3.0 autoreset 프로브 → **plain env + manual reset**로 회피, `compute_gae` **per-step next_values** 시그니처로 보강(mid-rollout truncation 테스트 추가) ② RolloutBuffer **raw+env action 분리 저장** + `clip_fraction_action` 로깅 ③ update 테스트 "loss 감소" 제거 → finite/ratio≈1/param-move/KL≥0/grad-clip ④ adv-norm **rollout-level 1회**(이중 정규화 금지) ⑤ GAE 테스트명 termination/truncation 정확화 / eval deterministic 곡선 분리 · DoD 완화(eval·seed≥3·1seed≥−300) · 재현성 CPU-only · `init_log_std` config화 · PPOConfig dataclass.
- **DoD 검증:** Pendulum-v1 seed 0/1/2 eval return **−131.4 / −185.8 / −156.4** (random ≈ −1200…−1600), 단조 상승, seed 0 재현 −131.4. 곡선 json/png + checkpoint(`*.pt`, gitignored) = `results/ppo_toy/`.
- **가드레일:** 동결 계약(env.py·03·m2_l2_train.yaml·exchange.py) diff 0. torch-free 스위트 **59→72** green(회귀 0). weights 커밋 제외.
- **사용자 추가 요청:** checkpoint 저장(`PPOTrainer.save/load`) 배선 + roundtrip 테스트. 이 문서(§0/§5/§7/§8) Phase 1 반영 + 오픈 항목(§7.1) 기록.
- **다음:** Phase 2 MAPPO(shepherd env, CTDE) — 역할별 actor + 중앙 critic(`env.state()`), 혼합 action head(finisher fire) 확정, obs normalizer 진입(§7.1).

### 2026-06-30
- **이 문서 생성.** L2 플랜+로그 단일화(`docs/09`).
- 레포 상태 확인: remote `KinderChocolate4AE/newURP`, 브랜치 `feat/l2-prep-wiring`(main 앞섬 3커밋), CI 없음, py3.10, `.gitignore` ML 아티팩트 커버, `.gitattributes` eol=lf, trainer 미존재.
- 동결 계약 요약(§2): env obs/act/reward/state·`m2_l2_train.yaml` 값.
- 결정 D1(COMA)/D2(L2기준)/D3(환경) 비교표 제시 → **D1=A, D2=A, D3=A 확정.** (A: 해석적 D_i 먼저→학습 critic 나중 / A: baseline 유의 초과=L2, capture=M3 / A: 로컬-우선+랩 이식)
- **Phase 0b 레포 세팅:** `marl` extra에 supersuit·wandb 추가(`requirements.txt`+`pyproject.toml`), `.github/workflows/ci.yml`(torch-free pytest, py3.10) 생성·검증.
- **mount truncation 발생·복구:** requirements/pyproject/09-doc가 한글 주석 부근에서 잘림 → heredoc ASCII 재기록 + 재읽기 검증으로 복구. 샌드박스 git 커밋 불가(index.lock 권한).
- 다음 액션: (로컬) `.git/index.lock` 삭제 → venv 설치 → `pytest` 31 green → setup 커밋 → prep→main 머지·push → `feat/l2-mappo-train` 분기 → Phase 1 PPO 코어.
---

## 9. 상태 총정리 — 피어리뷰 브리프 (2026-07-05 기준, 자기완결)

> 이 섹션은 외부 리뷰(GPT 등)에 단독 export하는 용도로 자기완결로 작성. 세부 근거는 §8 로그 (g)~(n)과 결과 디렉토리 참조.

### 9.0 문제 설정 (1문단 요약)

last-mile C-UAS 협력수비: 회랑을 침투하는 **반응형 scripted 공격 드론 1기**를 상대로, **limiter 4기**(셰이핑 기동으로 공격자의 도달가능집합을 압축)와 **finisher 1기**(net-capture 발사, 탄 K=1)가 협력. 학습 대상은 limiter+finisher 정책(공격자는 환경). 성공의 대리 지표 **v_shot** = net-capture viability의 MC surrogate(n=2000); 보상은 공유 J = 연속 셰이핑 headline(Δv_shot) + λ1·clean-crossing 보너스(1.0) − λ2·낭비 발사(1.0) − λ3·limiter loss-cost(0.5). 발사 게이트 = v_soft≥θ_fire(0.9)∧clean(비-boxed). 에피소드 80스텝(침투 시 조기 종료). 환경/보상/관측·행동 계약은 **동결**(학습 편의로 미변경; 유일 예외 = 비트-동일 batched-eval 최적화). CTDE + 공유 full-state 관측(63-dim), limiter 공유 정책 + one-hot ID. 학습 중 공격자 가족 랜덤화(속도·스폰·회피 ω·가속 하향-전용), eval은 nominal 고정. env가 per-limiter 해석적 counterfactual **coma_D**(hold 베이스라인, CRN) 제공.

### 9.1 학습 사다리 결과 (Phase 1 → 2D, 전부 마감)

| Phase | 세팅 | 결과 (last-3-eval 평균 판정) | 판정 |
|---|---|---|---|
| 1 PPO 코어 | Pendulum 검증 | seed 0/1/2 = −131/−186/−156 (random −1200~−1600) | ✅ |
| 2A(+2A′) | 어댑터·처리량 | env.step 117→54.4ms(2.16×, 비트-동일 lock 5종) | ✅ |
| 2B IPPO | 200k×3s + 안정화 | last3 margin(vs 최강 baseline) +2.64/+5.79/+2.59 → 평균 return **6.73** | ✅ 3/3 |
| 2C MAPPO | 200k×6s, 중앙 critic | vs IPPO **+2.32**(9.05 vs 6.73, +34%), 6/6 양수 | ✅ |
| 2D mix=1.0 | 500k×3s recipe-v2 | vs MAPPO **−1.40**(10.40 vs 11.80), 1/3 양수 | ❌ (예측된 실패) |
| 2D mix=0.5 | 500k×3s recipe-v2 | vs MAPPO **+2.20**(14.00 vs 11.80), 2/3 양수, s1 **+16.67 역대최고** | ✅ 2D 마감 |

- 베이스라인: hold(정지)·scripted(스크립트 셰이핑, headline 10.06이나 loss-cost 7.0 지출 → net ≈3.06). 전 학습 arm이 크게 초과(최근 margins +8.2~+13.6).
- 레시피 진화: 2B 안정화(obs RunningNorm·target_kl 0.02 조기중단·lr linear anneal·**last-3-eval 판정**·eval 20판) → recipe-v2(500k·rollout 1024·mb 256·anneal floor 0.1·best-sustained ckpt).
- 2D 비교는 3-arm 동일-레시피 통제: **coma_mix = {0, 0.5, 1.0} → mean {11.80, 14.00, 10.40} = 역-U.**

### 9.2 행동 모드 지도 & 핵심 발견

1. **모드 2개:** 셰이핑-only(len≈23, 침투 1.0, return≈headline≈10, 비용 0) vs **차단+셰이핑**(len 80, 침투 0, return 14~17). 후자 도달률 = MAPPO 1/3 → mix1.0 2/3 → mix0.5 **3/3**, 도달 시점도 조기화(eval ~20 → 7–8). 차단+셰이핑 = 침투 저지와 도달가능집합 압축의 동시 달성(현재 최강 전술).
2. **비용-인지가 RL 우월성의 원천:** scripted는 headline을 λ3 지출로 사고(net 3.06), 학습 정책은 유사 headline을 거의 무비용으로 달성.
3. **mix 역-U의 기전(정량):** cost-gap(=headline−return≈λ3 지출)이 MAPPO {1.85,0,0} / mix1.0 {3.03,3.33,5.09} / mix0.5 {2.61,**1.08**,5.13}. 문자형 COMA(mix=1)는 limiter 그래디언트가 −λ3 항을 구조적으로 못 봄(사전 등록 캐비앗 적중) → **per-limiter credit = 탐색(차단 모드 발견) 가속기, 비용 책정 = 공유 신호 몫, 블렌드가 최적.** coma_D 신호 자체는 전 런 전 구간 양수(말기 +0.03~+0.06)·학습 중 단조 증가.
4. **fire 체인 미개봉:** clean crossing·capture·wasted 全 seed 0 유지(발사 규율은 학습됨 — 스팸 없음). θ_fire=0.9 > plateau ρ/w=5/6라 셰이핑 강제 창 안 — 무-credit/독립 학습으로 안 열리는 것까지는 명제 N(10_shaping_necessity_prop.md 초안)과 정합. capture는 M3 stretch로 분리된 상태.
5. **판정 프로토콜 유효성:** eval 스냅샷 급락(예: 2C s2 −8 후 회복)을 last-3 판정이 설계대로 흡수; CUDA도 조건 고정 시 200k-step 비트-재현 사례 확보.

### 9.3 Threats to validity (리뷰 요청 포인트)

- **표본:** seed 3(2C만 6). 차단 모드 발견이 사실상 이산 사건이라 seed 간 분산 큼 — mix0.5도 per-seed vs_mappo는 2/3(s2 −0.52).
- **비교선 민감도:** 2D ref(11.80)가 MAPPO s0(14.97) 하나에 지배됨. mean-of-means 비교의 한계.
- **혼입:** 2C−2B 차이 = {중앙 critic, value-norm, ortho-init} 3요소(분해 안 함). 2D는 동일-레시피 통제로 이 문제 없음.
- **mix 해상도:** {0, 0.5, 1.0} 3점뿐. 역-U의 대안 가설(예: normalize(A_D)의 분산-감소 아티팩트) 미배제.
- **통계 정식화 미비:** "baseline 유의 초과"(L2 게이트 D2-A)의 검정 방식 미확정 — 현재는 3-seed last3 평균의 부호/크기 서술.
- **공격자 분포:** scripted 반응형 + 가족 랜덤화까지만. exploitability 측정(방어자 freeze + 공격자 PPO probe)은 게이트 후 예정.
- **coma_D 시간축:** env의 coma_D는 pre-move 계산이라 1-step 시프트 후 (γλ)-할인 forward 합으로 사용 — 이 시간축 해석은 사후 비준 대상.
- **surrogate 의존:** headline이 v_shot MC(n=2000)에 의존; near-gate 구간 n 축소 시 오차가 zero-waste 밴드폭 초과함은 측정 완료(그래서 2000 유지).
- **미달 영역:** clean crossing·physical capture 0 — 게이트 주장 범위는 "J·Δv_shot 유의 초과"로 한정됨.

### 9.4 리뷰 질문 (외부 리뷰어에게)

1. **L2 게이트 판정의 통계 정식화**: 3-seed last3 평균에 대해 무엇이 적절한가 — seed-level bootstrap CI, baseline 에피소드 분포 대비 비모수 검정, 아니면 seed 확장(비용: seed당 ~1h GPU)?
2. **mix 역-U 해석의 강건성**: 비용-실명 기전 외 대안 설명을 배제할 최소 추가 실험은? (예: mix 0.25/0.75 2점? A_D 비정규화 1-arm?)
3. **비교 프로토콜**: vs_mappo를 mean-of-means 대신 paired-seed 또는 pooled-episode로 바꿔야 하는가?
4. **논문 프레이밍**: (a) L2는 게이트로만 쓰고 M3 frontier-shift를 main으로 vs (b) 역-U+비용-실명 정량을 학습 파트 main result로 승격 — 어느 쪽이 강한가?
5. **fire 체인**: clean crossing 0 상태에서 λ1 커리큘럼(게이트 완화→복원) 시도 가치 vs M3로 직행?
6. 지금 우선순위에서 빠져 있는 최고 가치 실험 1개는?

### 9.5 재현 스펙 (요약)

- 커밋 체인(브랜치 `feat/l2-mappo-train`): Phase1 `52a7d58` → 2A `e99ff34` → 2B `54dfdeb`/안정화 `cef170f`/결과 `f7ae506` → 2C `7e0e98d`/결과 `be816f9` → 2D `df41dd8`/run1 `387b4c6`/mix05 `4a28e65`/run2 `4b3c708` → 본 브리프 시점 HEAD `b34a974`.
- 실행: `scripts/run_ippo_seeds_parallel.sh`(TRAIN_MODULE/CONFIG/OUT 환경변수; 코드-신선도 ancestor 가드), configs = `l2_ippo/l2_mappo/l2_coma/l2_coma_mix05.yaml`, 시나리오 동결 = `configs/m2_l2_train.yaml`. seeds {0,1,2}(2C {0..5}), RTX 4090 1장 time-slicing, torch 2.6.0+cu124. CUDA 비결정 캐비앗(단 조건 고정 비트-재현 사례 있음).
- 결과: `results/{ippo_run2, mappo_run1, mappo_run2, coma_run1, coma_run2}/seed*/{summary,eval_curve,train_curve}.json`; coma_D 커브 = `results/coma_run*/wandb_coma_dump.json`(wandb 0.28 offline 바이너리 파서 `scripts/wandb_offline_dump.py`).
- 테스트 138 수집(torch-free 105 / torch 33), frozen 계약 4종 diff 0, mix=0 ⇒ 2C 동일성 lock 테스트 포함.
