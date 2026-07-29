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

> 라벨 규약(2026-07-17 명문화): 엔트리 라벨 = 단순 순번 — (a)~(z) → (aa)~(zz) → 소진 시 (aaa)~ 3중자 연장. 라벨 자체에 의미 없음(커밋·문서·메모리 상호참조용 고정 ID). 정정·부속은 부모 라벨 + `-n` 서브라벨((w-1)식). 과거 라벨은 참조 보존을 위해 변경 금지.

### 2026-07-27 (wwwww) — 거시 위치 재평가 + **다음 세션 핸드오프 고정**: 최대 결손은 알고리즘이 아니라 **임무 단위 종속변수** · 논문 스파인 **B(프로토콜+결과)** 권고 · **B0(env mission harness)가 논문 성립 판정선**

- **채택**: 사용자 지시(거시 위치 평가 + 궁극 목표=MARL 협력수비 C-UAS Q1 논문 관점의 다음 세션 핸드오프). 산출 = `URP/c1_handoff_next_session_2026-07-27.md`(자기완결). **문헌·투고 사항은 상시 제약대로 일절 미포함** — "어떤 결과가 있어야 그 주장이 성립하는가"만 다룸.
- **자산 대차대조표**: **L2 MARL** — MAPPO 직접 구현 + COMA 해석적 credit · **사전등록 L2 게이트 PASS**(양 arm 하한 +10.2~+15.7) · paired **coma−mappo +1.91 CI[+0.83,+3.13]**(10-seed, 9/10 양수) · mix 역-U {0: 11.80, 0.5: 14.00, 1.0: 10.40} ⇒ **알고리즘·통계 규율은 이미 상당 수준**. **C-1** — 계층형 결정론 falsifier v2 · 3중 봉인 · 13/13 invariant · canary/containment/blind-rediscovery 프로토콜 · 결함 두 계열 · held-out 132/280 ⇒ **controller 성능이 아니라 평가 장치가 산출물**.
- **🚨 최대 결손 = 종속변수**: 지금까지 측정된 것은 전부 **shaped `margin`(대리지표) 또는 certificate 기하**이고 **임무 결과(포획·침투)는 end-to-end로 단 한 번도 측정된 적 없음**. 결손 목록 **G1 임무 지표 · G2 동일 지표 위 baseline · G3 학습정책 held-out 일반화 · G4 학습정책 adversarial 평가 · G5 clean crossing > 0 · G6 실용성 게이트**. **G1–G4는 장치 문제(만들면 해결) · G6은 범위 선언으로 우회 가능 · G5만이 실질적 존재 리스크.**
- **"하향"의 재해석**: 반복 축소는 연구 악화가 아니라 **측정 장치가 주장을 따라잡은 것**. 잡아낸 오류 유형 5종(within-class 탐색 실패 · 절단을 "일어나지 않음"으로 오독 3회 · 공허한 항등식 · 자기선택 subset 오독 · 단일조건 null 승격)은 **각각 검출 절차와 음성 대조를 보유** ⇒ **하향 이력 자체가 방법론 기여**이며 숨기지 말고 프로토콜 근거로 사용.
- **논문 프레이밍 권고**: **B(적대적·사전등록·봉인 평가 프로토콜 위의 정직한 측정 — scripted certificate controller 일반화 실패를 대조군, MARL을 본론)를 스파인으로 확정**, A(성능 논문)는 **B0~B3 판독 후 본문 섹션으로 승격 여부 결정**. **지금 A에 올인 금지** — G5는 아직 관측된 적조차 없음. B는 MARL 결과가 어떻게 나오든 성립.
- **Critical path 확정**: `B0 env mission harness → B1 freeze → B2 scripted baselines → B3 MARL 임무 측정 → B4 held-out mission conditions → B5 학습정책에 falsifier → B6 실용성 게이트(축소 가능)`. **B0→B3이 논문 성립 판정선.** harness 통과 전 어떤 controller도 mission 비교 미투입.
- **사전 결정(결과 보기 전 고정)**: **R1** 모든 arm capture=0 → 프레이밍 B 확정 + 종속변수를 **penetration rate + time-to-penetration(censoring 명시)**로 전환(*결과를 본 뒤 지표를 고르지 않기 위해 지금 기록*) · **R2** truncation 과반 → horizon 연장은 **사전등록 후 재실행·병렬 보고**(사후 조정 금지) · **R3** parity 불일치 → **B1 이후 진행 금지** · **R4** MARL이 scripted를 못 이김 → **음성 결과로 발행**(B 설계 이유) · **R5** 학습정책도 falsified → **같은 척도 위 비교라 오히려 기여**, 단 *"MARL이 강건하다"* 문면 금지.
- **봉인 재검증(2026-07-27)**: `FALSIFIER_V2_CODE_FREEZE` file/score/budget mismatch **0 · SEAL_INTACT=True** · `HELD_OUT_CONDITION_SET` 88조건 `94cc56e44aaff4d8` · `CONFIRMATORY_OUTCOME_PROTOCOL` **V2C-PROTOCOL-v2** · **invariant 13/13 PASS**. env 종료 규칙 실측 확인 — `captured|penetrated(≤1.0 m)|spent_fail`, `truncated = step_i ≥ episode_len 80`(4.0 s).
- **다음 세션 첫 5분(고정)**: ①봉인 3종+13/13 재검증(실패 시 정지) ②핸드오프 §6 수용조건 4개를 그대로 harness 스펙으로 고정(변경 금지) ③`env.step`/termination 직접 호출하는 mission rollout + 4분할 라벨 ④**positive control 4종 + off-by-one을 harness보다 먼저 작성(control-first)** ⑤parity 통과 후에만 B1 봉인.
- **한 문장**: *"알고리즘은 이미 게이트를 통과했고 평가 장치도 갖췄다. 남은 하나는 임무 단위 종속변수이며, 그것을 만드는 블록이 논문 성립 여부를 결정한다."*

### 2026-07-26 (vvvvv) — 종료 판정 **문면 보정 3건 + 최종 라벨 블록 고정**: 원인은 **둘 중 하나가 아니라 순차 노출된 두 개** · **ID↔STRESS 비율 직접 비교 금지**(STRESS subset은 강하게 자기선택) · **`0/11`은 유효하게 보존하고 일반화만 철회**

- **채택**: 외부검토 총판정(캠페인 종료 승인 — certificate-level 일반화 실패 확정, 정정 3건). 산출 = `URP/c1_v2c_closure_amendment_2026-07-26.md`. **재개가 아니라 문면 보정**이며 캠페인은 그대로 `CLOSED — CERTIFICATE-LEVEL ONLY`. 코드·데이터·봉인 **일절 불변**(재실행 없음).
- **보정 ① 원인은 둘 중 하나가 아니었다**: ~~"이전 캠페인의 null은 falsifier가 약해서가 아니라 조건이 하나였기 때문"~~ **철회**. 확정 문면 = **"legacy falsifier의 탐색력 결함도 실제로 존재했고**(within-class miss 5건이 그 증거)**, 그 결함을 고친 v2 아래에서도 단일 고정조건의 null은 외부조건 일반화의 증거가 아니었다."** 즉 *falsifier가 약했던 문제*가 해소된 뒤 *조건 다양성이 없던 문제*가 드러난 것 — **순차적으로 노출된 별개 원인 두 개**이며 앞서 정한 두 검증축(**A 탐색·검출력 / B endpoint·조건**)에 그대로 대응.
- **보정 ② ID와 STRESS의 비율은 직접 비교하지 않는다**: `IN_DISTRIBUTION` **116/218** · `STRESS` **16/62** falsified. 표면적으로 STRESS가 낮으나 **STRESS는 guard eligibility(24.0%)와 gate-valid 구성을 모두 통과한 subset 자체가 강하게 자기선택**돼 있고 어려운 pair 상당수가 **falsifier 도달 전에 탈락**. **금지**: ~~"STRESS에서 controller가 더 강했다"~~. 허용 문면 = *"STRESS에서는 post-fire gate-valid 평가까지 도달한 subset이 작고 강하게 선택돼 있으므로 해당 subset의 falsification 비율을 IN_DISTRIBUTION과 직접적인 강건성 비교로 사용할 수 없다."*
- **보정 ③ `0/11`의 지위는 보존, 일반화만 철회**: `NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2 · UNDER_ORIGINAL_SINGLE_EXTERNAL_CONDITION 11/11`은 **틀린 것이 아니라 유효하며 보존**. 철회되는 것은 ~~"그러므로 controller가 외부조건에서도 강하다"~~ 한 문장뿐. held-out 132건은 0/11을 **무효화한 것이 아니라 그 scope가 매우 좁았음을 드러낸 것**.
- **arm별 최종 회계**: `RI-SHARED-v1` gate-valid **140** / escape **79** / no-escape **61** / 구성·gate 실패 **167** — **`RI-SHARED-v1 DID NOT GENERALIZE UNDER THE SEALED HELD-OUT CERTIFICATE CAMPAIGN`**(단순 selector 성능 저하가 아니라 **shared radial-inward architecture의 certificate-level 외부조건 취약성**). `RI-GMAX` **140 / 53 / 87 / 167** — 일반화 controller가 아니라 조건별 existence reference이므로 **"일반화 실패율"로 읽지 않음**; 허용 문면 = *"외부조건별로 최대 reserve-valid inward reference를 다시 합성해도 140개 gate-valid artifact 중 53개에서 검증 반례가 존재했다"* ⇒ shared selector의 δ 선택 문제만이 아니며 **조건별 재합성으로도 현 radial-inward shaping class가 충분하지 않은 외부조건이 존재**.
- **condition 단위 결론(pair 비율보다 우선)**: gate-valid artifact가 존재한 외부조건 **35/88**, 그중 ≥1 검증 escape가 발견된 조건 **29/35** ⇒ *"현재 controller class가 certificate를 만들 수 있었던 held-out 외부조건 대부분에서 적어도 하나의 defender trajectory 또는 arm에 대한 검증 escape가 존재했다."* **`29/35`를 운용 확률로 읽지 않음** — 봉인된 설계 grid의 condition-level 기술 결과. 나머지 **53조건**은 adversarial falsification **이전에** 탈락(무발사 · SHARED reserve-valid 구성 실패 · GMAX search class 미발견 · lane/full-gate 실패).
- **최종 병목 구조 4계층**: `1 PRE_FIRE_GUARD_COVERAGE_FAILURE` → `2 CONTROLLER_CONSTRUCTION / LANE_GATE_FAILURE` → `3 CERTIFICATE-LEVEL ADVERSARIAL ESCAPE` → `4 MISSION OUTCOME — 현 C-1 캠페인에서는 관측 불가`. held-out 결과는 *"만든 certificate가 약했다"*만이 아니라 **certificate를 만드는 단계 자체가 외부조건에 좁게 작동했다**는 것을 보여줌.
- **A0 123/132의 의미**: **`OBSERVED_NEAR_CONSTANT_ATTACK_DOMINANCE · UNDER_CURRENT_HELD_OUT_CONDITIONS_AND_SEARCH`** — 고정조건에서만 나타난 우연보다 **강해진 결과**이나 여전히 **K=1 전역 충분성 · 시간가변 공격 불필요성 · 모든 escape basin이 상수 가속도**를 뜻하지 **않음**. 허용 문면 = *"현재 falsifier와 봉인된 held-out grid에서 발견된 certificate-level 반례의 대부분은 저복잡도 상수 가속도 공격으로 검출 가능했다."*
- **최종 라벨 블록(고정)**: `CAMPAIGN STATUS: CLOSED — CERTIFICATE-LEVEL ONLY` / `FIXED-CONDITION: 11/11 NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2 UNDER_ORIGINAL_SINGLE_EXTERNAL_CONDITION` / `HELD-OUT: 132/280 GATE-VALID ARM–TRAJECTORY TRIPLES FALSIFIED`(SHARED 79/140 · GMAX 53/140 · 구성·gate 실패 167 each · conditions 35/88 · ≥1 escape 29/35) / `CONTROLLER: RI-SHARED-v1 — HELD-OUT GENERALIZATION NOT SUPPORTED · RI-GMAX — CONDITION-SPECIFIC EXISTENCE CLASS ALSO PARTIALLY FALSIFIED` / `MISSION: NOT EVALUATED BY THIS HARNESS`. **추가 진단 금지** — 지금 캠페인을 다시 열면 **확증 결과를 본 뒤 분석 규칙을 추가하는 것**이 됨.
- **다음 단계 순서 원칙(사전 확정)**: `env harness validation → harness freeze → scripted baselines → RI-SHARED / RI-GMAX → MARL policy → held-out mission conditions`. **mission harness가 통과하기 전에는 `RI-SHARED`·`RI-GMAX`·MARL 중 어느 것도 mission 성능 비교에 넣지 않음.** 수용조건 4가지는 **이 캠페인 결과를 보고 바꾸지 않고** 사전 정의 그대로.
- **한 문장 결론**: *"단일 조건에서 강해 보이던 certificate-shaping controller가 held-out 외부조건에서 자주 구성되지 않거나 검증 반례를 허용했으며, 이를 신뢰성 있게 드러낸 것은 봉인된 계층형 falsifier와 조건 분리였다. 이제 mission 성능은 certificate 하네스가 아니라 실제 env termination 위에서 새로 측정해야 한다."*

### 2026-07-26 (uuuuu) — 🚨 **동결 캠페인 종료(단계 3·5·6·7·8)**: held-out 외부조건에서 **gate-valid 280 triple 중 132건(47%) `CONFIRMATORY_ESCAPE_FOUND`** — 같은 falsifier가 원래 고정조건에서는 **0/11**이었으므로 **이전 null은 고정조건의 산물** · `CLOSED — CERTIFICATE-LEVEL ONLY`

- **채택**: 외부검토 총판정(동결 캠페인을 먼저 끝내고 닫은 뒤 env 하네스로). 산출 = `shepherd/scripts/c1_v2c_step3.py` · `c1_v2c_step56.py` · `c1_v2c_step78.py` + JSON 3종 + `URP/c1_v2c_closure_2026-07-26.md`. 전 단계에서 **봉인 file_mismatch_count = 0** 유지.
- **단계 3 (원래 고정조건 미해결 11건, `V2C-` 시드)**: **`CONFIRMATORY_ESCAPE_FOUND` 0/11 · `NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2` 11/11**. best S min +0.000935 · median +0.005639 · max +0.006108(SHARED 3건은 경계에서 ~1 mm, GMAX 8건은 5~6 mm). 전제인 단계 2 blind rediscovery 5/5 통과이므로 **진단으로 읽을 자격 있음**.
- **단계 5·6 (held-out artifact 합성·봉인, falsifier 실행 전)**: eligible 307쌍에 **gate-only** 합성, 정보 누출 규칙 준수(`RESERVE_VALID`는 defender dynamics·admissibility·E_cap·E_lane·사전등록 reserve만 사용). **`RI-SHARED-v1` GATE_VALID 140 / 실패 167(`SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE`)** · **`RI-GMAX` GATE_VALID 140 / 실패 167(`NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS`)**(ID 109 valid/125 실패 · STRESS 31/42). **실패는 skip이 아니라 outcome.** δ: SHARED min 0.000 median 0.060 max 0.140 (reserve excess median 0.0104) / GMAX min 0.000 median 0.095 max 0.155 (**median 0.0018 — reserve 경계 controller가 held-out에서도 재확인**).
- **🚨 단계 7·8 (동결 falsifier)**: **280 gate-valid triple 중 132건(47.1%) falsified.** `IN_DISTRIBUTION` — `RI-SHARED-v1` **66/109** · `RI-GMAX` **50/109**, **≥1 escape condition 25/28**, 전부 escape 17/28, escape 없음 3/28. `STRESS` — `RI-SHARED-v1` **13/31** · `RI-GMAX` **3/31**, ≥1 escape condition 4/7, escape 없음 3/7. **두 arm은 서로 다른 질문에 답하므로 하나의 성공률 표로 합치지 않음.** 최초 발견 stage: **132건 중 123건이 A0(K=1 결정론)** — near-constant dominance가 held-out에서도 유지.
- **핵심 해석**: 동일 falsifier·동일 예산·동일 채점·봉인 무결 상태에서 **고정조건 11/11 null → held-out 132/280 falsify**. **바뀐 것은 외부조건뿐**이므로 **이전 캠페인의 null은 falsifier가 약해서가 아니라 조건이 하나였기 때문**. 또한 **gate-valid triple을 가진 condition은 88개 중 35개뿐**이고, 그 35개 중 **29개에서 반례 발생**(53개 조건에서는 애초에 controller 구성/gate 통과 실패).
- **controller 최종 지위(이 캠페인 범위)**: `RI-SHARED-v1` — 고정조건 4/7 falsified·남은 3건 이번 null, held-out gate-valid 140 중 **79건 falsified** ⇒ **무변경 적용은 held-out에서 일반화하지 않았다**. `RI-GMAX` — held-out gate-valid 140 중 **53건 falsified** ⇒ **조건별 재합성해도 상당수 조건에서 반례가 존재**하고 **88조건 중 53조건에서는 artifact 자체가 존재하지 않았다**. `CAPTURE_OPPORTUNITY_SHAPING_CONTROLLER` 지위는 유지되나 **그 shaping조차 held-out에서 adversarially 취약**.
- **발행 라벨**: `CONFIRMATORY_ESCAPE_FOUND` 132 · `NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2` 148 · `POST_FIRE_LANE_GATE_FAILURE` · `POST_FIRE_FULL_GATE_CERTIFICATE`. **미발행**: `MISSION_SUCCESS` · `CAPTURE_SUCCESS` · `PENETRATION_PREVENTED` · `END_TO_END_ROBUST`. **"M/N"은 condition 계층과 함께만** 사용(한 조건 내 trajectory는 독립 표본 아니고, 모든 조건이 단일 attacker boundary condition 공유).
- **종료 선언**: **`CAMPAIGN STATUS: CLOSED — CERTIFICATE-LEVEL ONLY`, 추가 진단 금지.** 답한 질문 하나 = *"봉인된 certificate-level artifact가 frozen falsifier v2 아래에서 검증 escape를 허용하는가"* → **held-out에서 상당 비율로 허용한다.** 답하지 못한 것 = 실제 포획 성공률·침투 방지율·end-to-end mission success·certificate→capture 전환(**eligible 분기는 deploy-window 절단으로 임무결과 미관측**).
- **다음**: env 기반 mission-level 하네스. 수용조건은 **이 결과를 보고 바꾸지 않고** 사전 정의 그대로 — ①종료 4분할(truncated는 right-censored) ②positive control 4종 + off-by-one ③deployment 종료까지 C-1↔env 상태 parity ④env termination = source of truth / 기존 verifier = 감사 장치, **predicate 복제 금지**. C-1 하네스는 certificate·geometry 분석기로 보존.

### 2026-07-26 (ttttt) — 거시 위치 정리(축소 2건) + **실행 단계 2 blind rediscovery 완료: 5/5, 전부 A0** · **시뮬레이터에는 mission endpoint가 이미 있었고 분석 하네스가 그 전에 끊고 있었음**

- **채택**: 외부검토 총판정(거시 진단 승인, 두 문장 축소). 산출 = `shepherd/scripts/c1_v2c_rediscovery.py` + `results/c1_corridor/c1_v2c_rediscovery.json` + `URP/c1_position_2026-07-26.md`.
- **축소 ① 근본 결함은 하나가 아니라 두 계열**: **A. 탐색·검출력 결함**(공격공간 coverage — legacy falsifier가 얇은 within-class basin을 놓침) / **B. endpoint·관측창 결함**(temporal mission outcome observability — `E_safe` 발사 의존성 · no-fire horizon truncation · eligible deploy-window truncation · `E_LANE=FULL_GATE` 공허한 동일성). 상위 공통점 = *"검증되지 않은 측정 장치의 null/certificate를 연구 결론으로 승격했다"*. **두 축은 다음 하네스에서도 별도 검증축으로 유지**(검사 방법·positive control이 다름).
- **축소 ② "escape 구조가 K=1"은 과했음 — 철회**: 확정 문면은 **`OBSERVED_NEAR_CONSTANT_ATTACK_DOMINANCE` · `UNDER_CURRENT_FIXED_CONDITION_AND_SEARCH` · `TESTED_THROUGH_K2_GLOBAL_AND_K8_LOCAL_HIERARCHY`**. **K=1 전역 충분성은 아직 자산이 아님.**
- **🎯 실행 단계 2 완료 — blind rediscovery 5/5**: 동결 falsifier v2 + **확증 시드 `V2C-`** + **알려진 반례 미seeding**. `BASE 2.8/0.30 SHARED` −0.002090 · `RH 2.8/0.15 SHARED` −0.003482 · `RH 3.2/0.25 SHARED` −0.001107 · `RH 5.0/0.55 GMAX` −0.013161 · `RH 5.0/0.55 SHARED` −0.022794 — **전부 재발견, 전부 최초 stage A0**. 봉인 검증 `file_mismatch_count = 0`. **`V2_DETECTION_REGRESSION_PASS`**. **해석 제한**: 이 5건이 v2 설계를 형성했으므로 **검출력 회귀시험일 뿐, 미해결 cell로 전이되지 않고 외부 일반성 증거 아님**. 다만 실패했다면 v2의 모든 null이 보류였으므로 **통과는 v2 null을 진단으로 읽을 자격**을 줌. 부수: 5건 전부 A0(K=1 결정론)에서 발견 — near-constant dominance와 일관.
- **구현 주의(기록)**: `c1_falsifier_v2.run_cell`이 개발 prefix `V2-`를 하드코딩하고 그 파일은 **봉인**돼 있으므로, 편의를 위해 봉인을 깨지 않고 **탐색 primitive(`k1_search`·`refine`·`segment_descent`·`s_proxy`·`s_auth`·`embed`·`temporal_starts`)와 예산 상수를 봉인 모듈에서 그대로 import**하고 **stage loop만 `V2C-` 시드로 재표현**. 시작 시 봉인 재검증.
- **🎯 핵심 재구성 — 시뮬레이터 vs 분석 하네스**: `rollout_unified`(c1_phase1d)는 **fire + deployment window만 평가**(종료 = `r.done` 또는 `steps > fire_step + n_dep + 1` = 0.50 s)인 **certificate-oriented 분석 하네스**이고, `env.py`는 **종료 = `captured | penetrated | spent_fail`, 절단 = step ≥ 80(4.0 s), 침투 = `|p_att − (0,0,0)| ≤ 1.0 m`**인 **mission-oriented 실행 환경**. ⇒ 기존 C-1 결과를 ~~"틀린 시뮬레이터 결과"~~로 부르면 안 되고, 정확히는 **"certificate 분석에는 쓸 수 있으나 mission outcome 분석에는 쓸 수 없는 하네스를 후자에도 사용했다"**. **C-1 하네스 폐기 불필요** — 역할 분리(C-1 = local certificate·escape geometry / env 기반 = end-to-end mission). **새 임무 정의를 발명할 필요 없이 하네스를 env termination에 재연결하면 됨 ⇒ 비용·위험 대폭 축소.**
- **다음 mission 하네스 최소 수용조건**: ①종료 4분할 `CAPTURED · PENETRATED · SPENT_FAIL · TRUNCATED_AT_STEP_80`(**truncated는 성공도 실패도 아닌 right-censored 보존**) ②positive control 4종(known capture/penetration/spent/long rollout) + **종료 직전·직후 한 step 차이 검사로 off-by-one 포착** ③**상태 parity** — deployment 종료까지 position·velocity·fire step·net FSM·capture/penetration 내부상태가 C-1과 env rollout에서 일치할 것, **그 뒤에만** 계속 진행 ④**정밀 verifier 유지** — `env termination = 언제 끝낼지의 source of truth`, `기존 verifier = 왜 그 verdict가 맞는지의 감사 장치`(captured→독립 adjudicator, 충돌/clearance→continuous verifier, cone→독립 predicate). **predicate 복제 구현 금지, `env.py`의 step·termination을 그대로 호출.**
- **동결 캠페인 범위 재확인**: 답하는 질문은 *"동결 certificate/artifact가 frozen falsifier v2의 adversarial search에서 깨지는가"* **하나**. 발행 가능 라벨은 **`CONFIRMATORY_ESCAPE_FOUND` · `NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2` · `POST_FIRE_FULL_GATE_CERTIFICATE`** 셋뿐. 진행 = 1 replay[5/5] · **2 rediscovery[5/5 완료]** · 4 eligibility[완료] / 남음 = 3 · 5 · 6 · 7 · 8.
- **연구 정체 계층화 권고**: **주기여 = last-mile C-UAS controller를 정직하게 검증하기 위한 계층형 평가·falsification·endpoint-audit 방법론**(stochastic falsifier의 within-class miss 사례 · deterministic hierarchical falsifier · certificate와 outcome의 분리 · guard coverage와 post-fire control의 분리 · truncation/predicate-induced non-observability · sealing·canary·containment protocol) / **부기여 = radial-inward capture-opportunity shaping controller의 구성과 고정조건 분석**. 이 구조면 **controller가 이후 깨져도 전체가 무너지지 않고**, 성공하면 방법론적으로 신뢰할 수 있는 양성 결과가 됨.
- **한 문장**: *"controller 연구가 실패한 것이 아니라, certificate-level 분석을 mission-level 평가로 오인했던 하네스 경계를 찾아냈고, 실제 mission termination을 이미 구현한 env로 평가 파이프라인을 다시 연결할 수 있게 된 상태."*

### 2026-07-26 (sssss) — 🚨 사슬 해석 정정: **eligible 에피소드는 발사 후 10 step(0.50 s)에 잘리고 그때 공격자는 asset에서 5.9 m** ⇒ **eligible 분기에서 침투는 구조적으로 관측 불가**, `E_LANE = FULL_GATE(167=167)`는 lane 효과가 아니라 **절단의 산물** · Tier 2의 140건은 mission failure가 아님

- **채택**: 외부검토 총판정(교전 사슬 승인 — 단 lane 인과 주장 보류, Tier 2를 mission failure로 부르지 말 것). 유보 확인차 `penetrated`를 별도 집계하다 **더 근본적인 사실**을 발견. 산출 = `URP/c1_v2c_chain_correction_2026-07-26.md`. **봉인·controller·guard·predicate·조건 전부 불변.**
- **Tier 2 정정**: `tier 2(E_cap ∧ ¬E_lane) = 140`, **그중 `penetrated=True`는 0건**(IN_DIST 100 · STRESS 40 전부 False). ⇒ ~~"실패는 lane 미확보 140건에 몰려 있다"~~ **철회**. 확정 라벨 = **`POST_FIRE_LANE_GATE_FAILURE`**(certificate 실패이지 **mission 실패가 아님**). 허용 문장 = *"Eligible pair에서 full-gate certificate를 얻지 못한 모든 사례는 lane 미확보 때문이었다."*
- **🚨 `E_LANE = FULL_GATE`는 공허**: **eligible 307건 전체에서 `penetrated=True` 0건**(tier2 0/140 · tier4 0/167). `¬penetrated`가 eligible 분기 전체에서 항상 참이므로 `E_LANE ⇒ ¬penetrated`는 **lane의 효과가 아니라 항등식**. ⇒ `OBSERVED_LANE_PENETRATION_SEPARATION`을 **증거로 사용하지 않음**.
- **원인 — 에피소드 절단 규칙**: `종료 = r.done 또는 steps > fire_step + n_dep + 1`(n_dep=8). 실측(eligible 24건 표본) **종료 step − fire_step = 10 (전부), 즉 0.50 s** · **종료 시 공격자 x = min 5.81 · median 5.94 · max 6.00 m**(asset=0). 20 m/s로도 약 0.3 s 더 필요 ⇒ **침투 관측 구조적 불가** → **`ELIGIBLE_BRANCH_MISSION_OUTCOME_CENSORED_BY_DEPLOY_WINDOW_TRUNCATION`**.
- **🚨 같은 결함 유형의 세 번째 사례**: ①`E_safe`가 발사에 의존해 **무발사 성공 인식 불가** ②no-fire 118건 **episode horizon 절단** ③**eligible 307건 전체 deploy-window 절단**. 공통 진단 = **`EVALUATION_WINDOW_TRUNCATES_BEFORE_THE_OUTCOME_CAN_OCCUR`**. **세 경우 모두 "관측되지 않음"이 "일어나지 않음"으로 읽히면 안 됨.**
- **704쌍 침투 회계**: no-fire 분기 **279** + eligible 분기 **0(관측 불가)** = **279/704 = 39.6%**. ⇒ `CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND`는 **전적으로 no-fire 분기에서 나오며**, eligible 분기는 **실패도 성공도 아직 아무것도 관측하지 못함**.
- **네 endpoint 구조(지시)**: **A** guard coverage `307/704 = 43.6%` · **B** opportunity shaping `167/307 = 54.4%` · **C** capture realization `0/167 = 0.0%`(+ mission outcome은 절단으로 미관측) · **D** adversarial vulnerability [남은 2·3·5–8단계]. ⇒ controller·guard·capture mechanism·falsifier의 책임이 섞이지 않음.
- **기타 라벨 정정**: `capture_margin`(min 0.0399 · median 0.5591 · max 1.0000) → **`FULL_GATE_CERTIFICATE_MARGIN_DIAGNOSTIC`**(capture 0건이므로 margin이 높아도 realization과 연결된다는 근거 없음). `NO_ESCAPE_FOUND` 금지 함의는 **일반 논리 금지**이며 *"현재 167건 전부에 frozen falsifier null이 확인됐다"*로 읽히면 안 됨 — 그 실행은 아직.
- **다음 버전 요구사항 추가**: **mission-outcome 평가에서는 deploy-window 절단(fire + n_dep + 1) 해제 필요**(현 규칙은 capture/clearance 판정용으로는 타당하나 mission outcome 판정에는 부적합) · event-driven continuation · **병렬 보고**(`V2C frozen-window` / `V2C-next event-driven`) · 신규 outcome `CAPTURE_OPPORTUNITY_WITHOUT_CAPTURE`. **현 캠페인 소급 적용 금지.**
- **현재 가장 정확한 서술**: 704쌍에서 frozen guard는 307건에서 발사 기회를 만들었고 그중 167건이 lane을 확보해 full-gate certificate에 도달했으나 **clean capture 0건**. certificate를 얻지 못한 eligible 사례는 **전부 lane 미확보** 때문이며 **certificate 실패이지 mission 실패가 아님**(eligible 분기 임무결과는 절단으로 미관측). 확인된 mission failure 279건은 **전부 무교전 분기**. controller는 **`CAPTURE_OPPORTUNITY_SHAPING_CONTROLLER`**이며 end-to-end 성공률은 현 구조로 **식별 불가**.

### 2026-07-26 (rrrrr) — 교전 사슬 정량화: **guard coverage 43.6% → lane clearance 54.4% → clean capture 0.0%** · 캠페인 endpoint는 "포획 성공"이 아니라 **capture-opportunity certificate + escape falsification**으로 확정

- **채택**: 외부검토 총판정(현 캠페인의 endpoint가 '포획 성공'이 아니라 'capture 가능성 certificate와 escape falsification'임이 확정). 산출 = `shepherd/scripts/c1_v2c_chain.py` + `results/c1_corridor/c1_v2c_chain.json` + `URP/c1_v2c_chain_2026-07-26.md`. **봉인·controller·guard·predicate·조건 전부 불변.**
- **🎯 사슬**: `PAIRS 704` → **`FIRE_ELIGIBLE 307 (43.6%)`** ← 1차 병목 guard coverage(Class C) → `E_CAPTURE 307 (100.0%)` → **`E_LANE 167 (54.4%)`** ← 2차 병목 lane clearance → `FULL_GATE_CERTIFICATE 167 (100.0%)` → **`CLEAN_CAPTURE 0 (0.0%)`** ← 끊기는 지점. 집합별 `IN_DIST` eligible 234 / lane 134 / cert 134 / capture 0 · `STRESS` 73 / 33 / 33 / 0.
- **부수 관측 2건**: `FIRE_ELIGIBLE→E_CAPTURE` 100%는 구성상 당연(발사 ⟺ eligible instant 존재) / **`E_LANE = FULL_GATE_CERTIFICATE` 정확히 일치(167=167)** — 즉 **lane 확보 사례에서는 침투가 한 건도 없었고**, lane 미확보 140건(tier 2)이 실패 쪽에 몰림. `capture_margin`(167 certificate): min 0.0399 · median 0.5591 · max 1.0000(기록 필드 그대로, 의미 재해석 안 함).
- **선택편향과 무관하게 확정되는 것**: 8개 defender trajectory는 **탈출 중심 캠페인의 미해결 cell witness**이므로 `clean capture = 0`은 **이 grid·witness 선택의 성질**이며 운용 포획률도 시스템 전반 포획 능력도 아님. **그러나 같은 데이터 안에 certificate 167건과 capture 0건이 공존** ⇒ **certificate는 capture를 함의하지 않음**(선택편향 무관).
- **금지 함의(직접 반증 보유)**: `NO_ESCAPE_FOUND ∧ FULL_GATE_CERTIFICATE ⇒ MISSION_SUCCESS` **금지** — 이 grid의 167 vs 0이 직접 반증.
- **controller 지위 재확정**: 이 결과는 controller 무효를 뜻하지 않으나, **실제 포획을 발생시키는 controller인지 포획 가능 기하를 만드는 shaping controller인지** 구분해야 하며 현재 증거는 **후자**를 지지 → **`CAPTURE_OPPORTUNITY_SHAPING_CONTROLLER`**.
- **남은 단계가 답할 수 있음**: frozen falsifier v2의 known counterexample 재발견 · unresolved artifact의 검증 escape 존재 여부 · eligible 조건에서 `RI-SHARED`의 certificate 유지 · `RI-GMAX` class의 reserve-valid artifact 합성 가능성 · post-fire escape vulnerability 위치. **답할 수 없음**: 실제 clean-capture 성공률 · end-to-end mission success rate · `NO_ESCAPE_FOUND`가 포획을 뜻하는지 · Tier 4→Tier 5 전환 여부.
- **캠페인 headline 최종 순서**: ①fire-guard coverage(704 중 397 무교전) ②직접 관측 system failure 최소 39.6% ③post-fire gate realization(eligible 307 중 certificate 167, **lane이 2차 병목**) ④actual capture 0건 ⑤adversarial robustness[남은 단계] ⑥평가 한계(engagement-독립 success predicate·event-driven endpoint 부재). ⇒ 전체 headline을 ~~"포획 성공 controller 검증"~~으로 쓰면 안 되며, 현재는 **guard coverage · capture-opportunity shaping · adversarial escape vulnerability를 분해해 검증한 fixed-condition campaign**.
- **다음 버전 outcome 1건 추가**: **`CAPTURE_OPPORTUNITY_WITHOUT_CAPTURE`**(Tier 4 → 실제 capture 전환 실패를 별도 outcome으로). event 흐름 = `fire eligibility → full-gate opportunity → deployment/capture attempt → captured or escaped → penetration / noncapture-safe / censoring`, 각 단계 **조건부 전환 보고** ⇒ 병목이 guard·lane·deployment·실제 접촉/구속 중 어디인지 분리. 코드 필드 `safe` → **`full_gate_certificate` 개명 권고**(현 캠페인은 코드 변경 없이 문서 의미만 정정).
- **현재 판정 상태**: `CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND 39.6%` · `NO_ENGAGEMENT_BRANCH_FAILURE_BOUND [39.6%, 56.4%]` · `TOTAL_SYSTEM_FAILURE_BOUND [39.6%, 100%]` · `CLEAN_CAPTURE_OBSERVED 0/704 · 0/307` · `POST_FIRE_FULL_GATE_CERTIFICATE 167/307` · **`END_TO_END_SUCCESS_RATE NOT IDENTIFIABLE UNDER FROZEN EVALUATION`**.

### 2026-07-26 (qqqqq) — 🚨 **`E_safe`는 성공 판정이 아니라 post-fire certificate** — tier 분해로 확인: **eligible 307건 중 `E_safe=True` 167건이 전부 tier 4, 실제 포획(tier 5)은 0건** · end-to-end 성공률은 현 구조로 **산출 불가**

- **채택**: 외부검토 총판정(정정 승인 — Endpoint C의 성공 판정은 현재 구조로 완성 불가). 산출 = `URP/c1_v2c_success_predicate_2026-07-26.md`(해석 정정 + 다음 버전 요구사항 등록). **코드·조건·프로토콜 봉인 불변, predicate/horizon 사후 변경 없음.**
- **`E_safe`의 실제 의미**: `E_safe = E_cap ∧ E_lane ∧ ¬penetrated`, `E_cap = eligible fire instant 존재` ⇒ **"발사 가능한 순간이 있었고 lane이 확보됐고 에피소드 안에서 아직 침투하지 않았다"**일 뿐 **포획 성공도 임무 완료도 아님**. 정확한 라벨 = **`POST_FIRE_CAPTURE_OPPORTUNITY_CERTIFICATE`** · **`FULL_GATE_CERTIFICATE_WITHOUT_PENETRATION`**.
- **🚨 tier 분해로 데이터 확인**: eligible 307건 tier 분포 **{2: 140, 4: 167}**, `safe=True`는 **tier 4에만 167건**, **tier 5(`E_safe ∧ captured ∧ clean`) = 0건**. 집합별 `IN_DIST {2:100, 4:134}` · `STRESS {2:40, 4:33}`. ⇒ **이 봉인 grid 704쌍에서 clean capture는 0건.** tier 2(140) = 발사 기회는 있었으나 **lane 미확보**. **단서**: held-out 8개 defender trajectory는 미해결 cell의 witness이고 캠페인 자체가 **탈출/근접 실패 시나리오 중심**이므로 **포획 0건은 witness 선택의 성질일 수 있으며 시스템 전반의 포획 능력으로 확장 금지**. 다만 `E_safe = 성공` 해석이 틀렸다는 결론에는 영향 없음.
- **비대칭 구조**: **실패는 `penetrated` 플래그로 직접 관측 가능**(→ `MISSION_FAILURE_NO_ENGAGEMENT 279` 유효) / **성공은 engagement-독립 terminal-success predicate가 없어 완전 판정 불가** → `SUCCESS_WITHOUT_CAPTURE_NOT_DETECTABLE_BY_FROZEN_PREDICATE` · **`END_TO_END_SUCCESS_NOT_FULLY_OBSERVABLE`**. **post-fire 307건을 전부 판정해도 독립 성공 predicate가 없으면 실패 하한만 정교해지고 성공률은 산출되지 않음.**
- **보고 시 합치기 금지(사전 확정)**: `CONFIRMATORY_ESCAPE_FOUND`(탐색이 반례 발견) · `NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2`(탐색 null) · `POST_FIRE_FULL_GATE_CERTIFICATE`(E_safe) **셋 중 어느 것도 단독으로 `MISSION_SUCCESS`를 증명하지 않음.**
- **다음 버전 필수 — engagement-독립 mission predicate**: `[engagement/controller certificate] E_cap · E_lane · POST_FIRE_FULL_GATE_CERTIFICATE` 와 `[mission outcome] PENETRATION · NONCAPTURE_SAFE_TERMINAL(fire와 독립 정의) · CAPTURED_OR_NEUTRALIZED · RIGHT_CENSORED_AT_MAX_HORIZON` **구조 분리**. `NONCAPTURE_SAFE_TERMINAL`의 구체 기준(위협영역 이탈·자산 분리거리·outward motion 유지 등)은 **결과를 보기 전에 사전등록**, **현 캠페인 소급 적용 금지**.
- **horizon 후속 설계**: **event-driven continuation**(penetration | 독립 noncapture-safe terminal | capture/neutralization | 사전등록 max horizon 중 하나까지) **우선**, 조건별 연장은 모델 의존성·선택 편향으로 차선. 보고는 **덮어쓰지 않고 병렬**(`V2C frozen-horizon` / `V2C-next event-driven`). 다음 버전 진단 필드(**판정용 아님**): `terminal_planar_distance` · `terminal_closing_speed` · `terminal_heading_relative_to_asset` · `projected_closing_time` — `τ_close = 99.52 s` 사례는 closing velocity가 사실상 0이므로 τ 단독 오독 위험.
- **현재 확정 상태**: `MISSION_FAILURE_NO_ENGAGEMENT 279`(유효) · `RIGHT_CENSORED_AT_EPISODE_HORIZON 118`(terminal 접근 63 / 비접근 55, 진단) · `MISSION_SUCCESS_WITHOUT_CAPTURE 0`(정의상 탐지 불가) · `POST_FIRE_FULL_GATE_CERTIFICATE 167`(포획 아님) · `CLEAN_CAPTURE 0`. **`CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND` 39.6% · `NO_ENGAGEMENT_BRANCH_FAILURE_BOUND` [39.6%, 56.4%] · `TOTAL_SYSTEM_FAILURE_BOUND` [39.6%, 100%] · `END_TO_END_SUCCESS_RATE` 계산 불가.**

### 2026-07-26 (ppppp) — 정정 2건: **39.6–56.4%는 전체가 아니라 no-engagement branch bound** · **`MISSION_SUCCESS_WITHOUT_CAPTURE = 0`은 정의상 보장된 값(정보 없음)** · 절단 118건 중 **55건은 asset으로 접근조차 하지 않고 있었음**

- **채택**: 외부검토 총판정(우측 절단 분해 승인 — 단 실패율 bound 명칭 수정). 산출 = `shepherd/scripts/c1_v2c_unresolved.py` 개정 + `results/c1_corridor/c1_v2c_unresolved.json` + `URP/c1_v2c_bounds_correction_2026-07-26.md`.
- **🚨 정정 ① bound 명칭**: ~~`39.6% ≤ system-level failure rate ≤ 56.4%`~~는 **오류**. post-fire eligible 307건이 미판정이므로 56.4%는 전체 상한이 될 수 없음. 정정 = **`CONFIRMED_SYSTEM_FAILURE_LOWER_BOUND` 279/704 = 39.6%** · **`NO_ENGAGEMENT_BRANCH_FAILURE_BOUND` [279, 397]/704 = [39.6%, 56.4%]** · **`TOTAL_SYSTEM_FAILURE_BOUND` [39.6%, 100%]**(상한은 307건 판정 전까지 무정보). 집합별 branch bound = `IN_DIST` **35.8%~41.5%**(no-fire 166 · 확정 143 · 절단 23) · `STRESS` **44.7%~76.0%**(231 · 136 · 95). STRESS 폭이 넓은 이유는 **95건이 창 절단**이며 추정으로 채우지 않음.
- **🚨 정정 ② `MISSION_SUCCESS_WITHOUT_CAPTURE = 0`의 의미**: `E_safe = E_cap ∧ E_lane ∧ ¬penetrated`이고 `E_cap = eligible fire instant 존재`이므로 **발사가 없으면 `E_safe`는 구조적으로 항상 False**. 즉 **동결 success predicate는 포획 없는 임무 성공을 인식할 수 없음** ⇒ **0은 관측이 아니라 정의상 보장된 값이고 정보가 없음**. 경험적 교차확인 일치(`safe=True` = eligible 307 중 167 · no-fire 397 중 0). **이전 회차의 "자연스럽게 무해해진 no-fire는 한 건도 없었습니다"를 철회**하고 라벨을 **`SUCCESS_WITHOUT_CAPTURE_NOT_DETECTABLE_BY_FROZEN_PREDICATE`**로 교체. 허용 문장은 *"동결 success predicate 아래에서 success certificate가 발행된 no-fire 사례는 0건"*뿐. **`MISSION_FAILURE_NO_ENGAGEMENT = 279`는 영향 없음** — `penetrated` 플래그를 직접 읽은 값이고 `E_safe`와 독립.
- **🚨 절단 118건의 closing time 재계산**: 이전 `8.84 m / 20 m/s ≈ 0.44 s`는 **단순 거리/공칭속도 휴리스틱**이었음. asset 방향 실제 접근속도로 `τ_close = d / max(ε, −r̂ᵀv_rel)` 계산 → **τ min 0.089 · median 0.979 · max 99.520 s(접근 중 63건)** 이고 **asset 평면으로 접근하고 있지 않은 사례 55/118**. ⇒ ~~"창만 늘리면 대부분 침투로 해소된다"~~ **불가** — 절반 가까이가 접근조차 하지 않음. 동시에 **55건이 안전해졌다는 것도 아님**(정정 ②로 판정 불가, 재접근 여부 미관측).
- **horizon 연장 후보 재서술**: ①고정 연장 ②penetration/safe 이벤트까지 실행 + 최대 horizon ③종말 projected closing time 기준 조건별 연장(규칙 사전 동결). **§3 때문에 ②·③이 ①보다 정보가 많음.** 현 캠페인 적용 금지, 새 결과는 현 결과와 나란히 보고.
- **최종 라벨 집계**: `NO_CAPTURE_ATTEMPT 397` · `MISSION_FAILURE_NO_ENGAGEMENT 279` · **`RIGHT_CENSORED_AT_EPISODE_HORIZON 118`** · `MISSION_SUCCESS_WITHOUT_CAPTURE 0`(정의상 탐지 불가).
- **변하지 않는 핵심**: 동결 held-out grid의 **최소 39.6%**에서 fire guard 무교전으로 **이미 mission failure 확인**, 추가 **16.8%(118/704)**는 **horizon 절단**. 전체 시스템 실패율은 **post-fire 307건 판정 후에야** 완성. 세 봉인 불변 — 이 회차는 **명칭·해석 정정과 진단 기록**이지 프로토콜 변경이 아님.

### 2026-07-26 (ooooo) — 미해결 118건 사유 분해: **전부 `HORIZON_ENDED_BEFORE_PENETRATION_OR_SAFE`(우측 절단)**, 애매·오류 0건 · 봉인 grid 실패 bound **39.6% ~ 56.4%** 확정

- **채택**: 외부검토 총판정(guard coverage가 1차 시스템 병목이라는 결론 강화 + 미해결 118건 사유 분해 요구). 산출 = `shepherd/scripts/c1_v2c_unresolved.py` + `results/c1_corridor/c1_v2c_unresolved.json` + `URP/c1_v2c_unresolved_2026-07-26.md`.
- **분해 결과**: **`HORIZON_ENDED_BEFORE_PENETRATION_OR_SAFE` 118**(IN_DIST 23 · STRESS 95) · `TERMINATION_STATE_AMBIGUOUS` **0** · `ROLLOUT_OR_FLAG_ERROR` **0** · `OTHER` **0**. 판정 근거는 **rollout이 이미 기록한 상태**(종료 시 공격자가 asset 평면을 지났는지)뿐이며 **새 판정 규칙을 만들지 않음**. **아무것도 재분류하지 않음** — V2C-PROTOCOL-v2의 3분할 불변.
- **에피소드 종료 시 공격자–asset 평면 거리**: **min 1.41 · median 8.84 · max 12.30 m** ⇒ **118건 모두 공격자가 접근 중인 상태에서 관측 창이 닫힘**. `safe`가 아니었던 이유는 위협 소멸이 아니라 **포획 증명서(E_cap ∧ E_lane) 부재**, `penetrated`가 아니었던 이유는 **아직 도달 전**. ⇒ 미해결은 **판정 불가능이 아니라 우측 절단**이며, STRESS 편중(95/118)도 설명됨(무발사가 많고 교전 없이 진행되다 창이 닫힘).
- **하지 않은 것**: 이들이 결국 침투했을 것이라는 **추정 금지**(관측되지 않음) · 성공에도 실패에도 **미편입**.
- **봉인 grid 실패 bound 확정**: 확정 no-engagement 실패 **279/704 = 39.6%**, 상한(미해결 전부 실패 가정) **397/704 = 56.4%** ⇒ **39.6% ≤ sealed-grid system-level failure rate ≤ 56.4%**. 집합별 확정 하한 = `IN_DIST 143/400 = 35.8%` · `STRESS 136/304 = 44.7%`. **양 끝 모두 설계된 조건 집합의 기술통계이며 운용 확률이 아님.**
- **허용되는 가장 강한 문장(지시 문면 채택)**: *"frozen fire guard가 포획 시도를 생성하지 않은 사례 중 mission outcome을 판정할 수 있었던 **279건은 모두 침투로 끝났으며, 포획 없이 자연적으로 안전해진 사례는 한 건도 관측되지 않았다**."* **금지**: ~~"no-fire 397건 전부 mission failure"~~.
- **condition-level 광범위성 재확인**: 88조건 중 `ZERO_GUARD_COVERAGE` **19** · `PARTIAL` **61** · `FULL` **8**(9.1%) ⇒ **80개 조건에서 최소 하나 이상의 defender trajectory가 발사되지 않음.** STRESS는 zero 18/38 · full 2/38이므로 이후 post-fire 결과는 **강하게 자기선택된 부분집합에 대한 조건부 결과**.
- **다음 프로토콜 개정 후보(지금 적용 금지)**: 미해결이 전부 창 절단이므로 **episode horizon 연장**이면 대부분 해소될 가능성(중앙값 8.84 m, 20 m/s 기준 약 0.44 s). **지금 바꾸는 것은 결과를 본 뒤의 사후 조정이므로 금지** — 다음 버전에서 사전등록 후 재실행하고 현 결과와 나란히 보고.
- **캠페인 질문 순서(확정)**: ①guard coverage(현재 답: 많은 조건에서 아니오 — 704 중 397에서 포획 시도 없음, 판정 가능한 279건 전부 침투) ②eligible 307쌍에서의 conditional post-fire robustness ③end-to-end mission. **post-fire controller가 아무리 강해도 guard coverage가 그대로면 end-to-end 근본 문제는 미해소.**
- **상태**: V2C-PROTOCOL-v2 SEALED(이 문서는 사유 기록일 뿐 프로토콜 변경 아님) · Endpoint A·C 완료 · Endpoint B 미산출 · Class C 등록 유지 · guard/controller 수정 금지 유지 · 남은 단계 2·3·5~8.

### 2026-07-26 (nnnnn) — **V2C-PROTOCOL-v2**: no-fire를 자동 실패로 처리하지 않고 확인 → 🚨 **397건 중 279건 침투(`MISSION_FAILURE_NO_ENGAGEMENT`), 자연 봉쇄 0건** · condition 단위로 실패가 **퍼져 있음**(full coverage 8/88) · Class C 신설

- **채택**: 외부검토 총판정(캠페인 1차 병목이 post-fire controller에서 fire-guard coverage로 이동). 산출 = `shepherd/scripts/c1_v2c_endpoints.py` + `results/c1_corridor/c1_v2c_endpoints.json` + `URP/c1_v2c_endpoints_2026-07-26.md`.
- **v1 → v2 정정**: `V2C-PROTOCOL-v1`은 **모든 no-fire를 system-level mission failure/nonattempt로 라벨**했는데 이는 공격자가 실제로 무엇을 했는지 확인하지 않은 것 → **`SUPERSEDED_BEFORE_CONTROLLER_EXECUTION`**. **`V2C-PROTOCOL-v2`**(hash `4791359431c69e5d…`) = no-fire 기본 라벨 **`NO_CAPTURE_ATTEMPT` + `FIRE_GUARD_COVERAGE_FAILURE`**(`GUARD_CONTROLLER_INTERFACE_FAILURE`는 **아키텍처 해석 라벨**로만 유지) · mission outcome **3분할** · endpoint **A/B/C 분리** · 주효과(OFAT)와 상호작용(CROSSED) **분리 보고**. **v1 eligibility 수치는 불변** — predicate 미변경, 복사가 아니라 **재유도 대조**: `v1=307 v2=307 MATCH`.
- **Endpoint A**: `POST_FIRE_ELIGIBLE 307/704` · `NO_CAPTURE_ATTEMPT 397/704`. **이 비율은 봉인 grid에서의 pair-weighted eligibility rate이며 운용 발사확률 추정치가 아님**(`IN_DIST 58.5%` · `STRESS 24.0%`도 설계된 조건 집합 내 기술통계).
- **condition 단위 coverage — 397/704가 가리던 것**: `IN_DISTRIBUTION` **ZERO 1 · PARTIAL 43 · FULL 6**(50) / `STRESS` **ZERO 18 · PARTIAL 18 · FULL 2**(38). ⇒ **실패는 소수 극단 조건에 집중된 것이 아니라 퍼져 있음** — 88조건 중 full coverage는 **8개뿐**.
- **🚨 Endpoint C — no-fire 397건의 실제 결말**: **`MISSION_FAILURE_NO_ENGAGEMENT` 279**(IN_DIST 143 · STRESS 136) · **`MISSION_SUCCESS_WITHOUT_CAPTURE` 0** · `SYSTEM_NONATTEMPT_OUTCOME_UNRESOLVED` 118(IN_DIST 23 · STRESS 95). ⇒ **자연스럽게 무해해진 no-fire는 한 건도 없었고, 판정 가능한 279건은 전부 침투**. 추정이 아니라 rollout의 `penetrated`/`safe` 플래그를 읽은 값이며, 미해결 118건은 **미해결로 보존**.
- **주효과/상호작용 분리(지시)**: v1 readout의 축별 집계는 **교차조건을 두 축에 중복 계상**하므로 인과 기여도로 읽을 수 없음. **주효과(OFAT만)** — `lateral ±0.25→4~5/8, ±1.5·3.0→8/8` · `heading ±1→2~4/8, 10°→7/8` · `cone_axis ±0.5·1.0→0/8, 6.0→8/8` · `speed 26~30→3/8` · `reset 1102만 1/8`. **상호작용(CROSSED만, 별도 표)** — `lateral×heading 136/200` · `reset×lateral 104/144` · `speed×cone 53/120`. **금지**: `"전체 실패의 x%가 lateral 때문"` 형태 진술(산출물에서도 생성하지 않음). 승인 문면 = *"시험한 near-nominal perturbation 중 fire-guard coverage가 가장 민감했던 축은 attacker lateral offset이었다"*.
- **세 endpoint 봉인**: **A** guard coverage[완료] · **B** conditional post-fire(5~7단계, 미산출) · **C** end-to-end mission[no-fire분 완료].
- **post-fire 조건부성 사전 확정**: STRESS eligible **73/304 = 24.0%**이므로 이후 결과는 *"동결 guard가 발사한 24.0% subset에서의 conditional post-fire result"*로만 서술. ~~"controller가 STRESS에 강건했다"~~ 불가. **단 eligibility가 arm-blind이므로 같은 eligible pair 내 `RI-SHARED` vs `RI-GMAX` 비교는 공정** — 문제는 arm 비교가 아니라 **eligible subset의 전체 조건 일반화**.
- **Class C 신설**: `Class A`(near-terminal razor gap) · `Class B`(gross radial displacement) · **`Class C = PRE_FIRE_GUARD_COVERAGE_FAILURE`**. **radial controller 수정으로 해결 불가**(발사 후에만 존재). 후속 프로토콜 설계 후보(**현 캠페인 변경 금지**): lateral-aware fire guard · cone axis와 firing predicate 일관화 · fire timing/coverage 재설계 · guard–controller 공동 설계 · **발사 전 shepherding으로 공격자를 guard coverage 안으로 유도**.
- **캠페인 headline 순서 재배치**: ① guard coverage가 held-out set의 주된 upstream bottleneck이며 판정 가능한 no-fire는 전부 침투 ② eligible subset의 post-fire 결과 ③ shared selector vs GMAX reference ④ Class B recovery ⑤ guard–controller co-design 필요성. **이전 1차 질문("radial inward controller가 escape를 막는가")은 2번으로 내려감.**
- **상태**: 세 봉인 유지(코드·조건·프로토콜) · 실행 1·4·C(no-fire분) 완료, 2·3·5~8 남음 · `RI-GMAX` 1 falsified/8 미해결 · `RI-SHARED` 4 falsified/3 미해결 · **guard/controller 수정 금지 유지**.

### 2026-07-26 (mmmmm) — **V2C-PROTOCOL-v1 재봉인**(no-fire 이중 endpoint) + 704쌍 arm-blind eligibility → 🚨 **397/704(56%)가 `NO_CAPTURE_ATTEMPT`, 최대 요인은 cone axis가 아니라 lateral offset — 동결 fire guard는 사실상 보어사이트 전용**

- **채택**: 외부검토 총판정(두 freeze 승인 — confirmatory protocol만 no-fire 규칙 보정 후 재봉인). 산출 = `shepherd/scripts/c1_v2c_protocol.py` + `results/c1_corridor/c1_v2c_protocol.json` + `URP/c1_v2c_protocol_2026-07-26.md`.
- **보정 범위 — 딱 하나**: confirmatory **outcome taxonomy만** 개정. **불변** = falsifier v2 코드 봉인 · held-out spec/list 봉인 · **조건 삭제·교체 없음** · fire guard 무변경 · controller 무변경. 버전 기록 = `V2C-PROTOCOL-v0`(no-fire 미분류) **`SUPERSEDED_BEFORE_FULL_CONFIRMATORY_EXECUTION`** / `V2C-PROTOCOL-v1` **`SEALED_FOR_CONFIRMATORY_EXECUTION`**, `protocol hash 87f74f7dd96aa0a1…`. **v0에서 산출된 확증 결과 0건 — 사후 재분류가 아니라 실행 전 개정.** smoke에서 본 특정 RH cell만 예외 처리하지 않고 **동일 기계적 규칙을 704쌍 전체에 일괄 적용**.
- **no-fire 이중 endpoint(지시)**: post-fire = **`NOT_ELIGIBLE_FOR_POST_FIRE_CONTROLLER_EVALUATION`** / `REASON = NO_CAPTURE_ATTEMPT_UNDER_FROZEN_FIRE_GUARD`(분모 제외하되 **모든 표에 수량 명시**) · system = **`NO_CAPTURE_ATTEMPT`** / `SYSTEM_LEVEL_MISSION_FAILURE_OR_NONATTEMPT`(**시스템 분모에 보존**). 귀속 = **`GUARD_CONTROLLER_INTERFACE_FAILURE`** — radial-controller 실패도 시스템 성공도 아님.
- **eligibility는 arm-blind**: `POST_FIRE_ELIGIBLE(condition, defender_trajectory) = 동결 guard가 유효 발사 사건을 만드는가`. predicate params `['pe','cond','tag','W']` — **arm 인자 자체가 없음**. arm에 따라 달라지면 selector가 발사 이전 동역학/guard에 개입한 것이므로 controller semantics와 모순.
- **🚨 실행 4단계 결과(704쌍)**: **`POST_FIRE_ELIGIBLE` 307/704(43.6%)** · **`NO_CAPTURE_ATTEMPT` 397/704(56.4%)**. `IN_DISTRIBUTION` 400쌍 중 eligible 234(58.5%) / `STRESS` 304쌍 중 eligible **73(24.0%)**.
- **`GUARD_COVERAGE_EFFECT` 축별 no-fire**: **`lateral_offset_m` 284/400 (71.0%)** · `heading_deg` 168/256(65.6%) · `reset_seed` 105/184(57.1%) · `cone_axis_deg` 71/168(42.3%) · `speed_mps` 62/160(38.8%). *(교차조건은 두 축에 계상)*
- **OFAT 값별 분해 — 핵심**: `lateral ±0.25 m → 4~5/8`, `±0.5 m → 4~7/8`, `±1.5 m 이상 → 8/8 전부 무발사`. `heading ±1° → 2~4/8`, `±6° → 6/8`, `10° → 7/8`. `cone_axis ±0.5°·1° → 0/8`(무해), `±3° → 4~6/8`, `6° → 8/8`. `speed 14~22 → 1/8`, `26~30 → 3/8`. `reset 전 값 → 1/40`(거의 무영향). ⇒ **동결 fire guard는 사실상 보어사이트 전용이며, 25 cm 측방 오프셋만으로 8개 중 4~5개에서 발사 자체가 없음.** smoke에서 처음 본 cone-axis는 **주된 원인이 아니었고**(±1° 이하 0), **규칙을 88조건 전체에 일괄 적용했기 때문에** lateral이 드러남 — 특정 cell만 예외 처리했다면 놓쳤을 사실.
- **함의**: post-fire controller 강건성보다 **guard coverage가 먼저 구속력**을 가짐. `STRESS`는 **24%만 eligible**이므로 그 집합의 post-fire 결론은 **작고 자기선택된 부분집합** 위에 놓임 — 결론에 반드시 부기. 조용히 제외했다면 캠페인의 **56%, 그것도 더 어려운 쪽**이 분모에서 사라졌을 것.
- **cone-axis 이중 효과 분해(지시)**: `GUARD_COVERAGE_EFFECT`(발사 여부) / `POST_FIRE_CONTROLLER_ROBUSTNESS`(발사 시 버티는가) 분리 보고.
- **gate failure는 제외가 아니라 결과(사전등록)**: `RI-SHARED-v1` → **`SHARED_CONTROLLER_CONSTRUCTION_OR_GATE_FAILURE`**(공유 아키텍처의 실패) / `RI-GMAX` → **`NO_CONTROLLER_FOUND_IN_GMAX_SEARCH_CLASS`**(해당 조건 존재성 음성). 전체 흐름 보존: `condition → fire eligibility → controller construction → full-gate validity → adversarial falsification`.
- **GMAX 정보 누출 금지(사전등록)**: 허용 = defender dynamics·E_cap·E_lane·admissibility·사전등록 reserve / **금지 = falsifier score·escape 발생 여부·adversarial margin·A0~A3 candidate 결과**. 목적함수 = `argmax δ s.t. full-gate ∧ admissibility`, **금지** = `argmax δ that survives falsification`. δ·artifact 봉인 후 falsifier 실행.
- **보고 구조 봉인**: 조건 단위 / trajectory 단위(5 라벨) / arm 단위. `"N개 중 M개"`는 **외부조건 계층과 함께만** 허용, **704쌍은 독립 표본 704개가 아님**.
- **seal 검증 출력 명칭 정정**: `budget False`가 "예산 비활성화"로 오독될 수 있어 → `file_mismatch_count` / `score_mismatch_count` / `budget_mismatch` / `SEAL_INTACT`.
- **상태**: `FALSIFIER_V2_CODE_FREEZE` SEALED(--verify `SEAL_INTACT = True`) · `HELD_OUT_CONDITION_SET` SEALED(88조건) · `CONFIRMATORY_OUTCOME_PROTOCOL` **V2C-PROTOCOL-v1 SEALED**. 실행 순서 1·4단계 완료, 2·3·5~8 미실행. `RI-GMAX` 1 falsified/8 미해결 · `RI-SHARED` 4 falsified/3 미해결.

### 2026-07-26 (lllll) — **`FALSIFIER_V2_CODE_FREEZE` 실행(SEALED)** + **held-out 외부조건 88개 봉인**(평가 전) · arm 역할 분리 · 확증 실행 순서 8단계 고정

- **채택**: 외부검토 총판정(falsifier v2 코드 freeze 승인 — confirmatory protocol freeze는 held-out 봉인 후). 산출 = `shepherd/scripts/c1_falsifier_v2_seal.py` · `c1_heldout_conditions.py` + JSON 2종 + `URP/c1_heldout_freeze_2026-07-26.md`.
- **두 freeze 분리(지시)**: **`FALSIFIER_V2_CODE_FREEZE` SEALED** / **`CONFIRMATORY_EVALUATION_FREEZE`는 held-out 목록 봉인으로 조건 충족**(실행은 다음 블록). 봉인 대상 = 9개 모듈 sha256(v2 본체·A0·K2 전역·체크리스트·V1 검증 + **채점 정의** `c1_replan_falsifier` + **authoritative 판정기** `c1_exact_clearance` + **시드 파생** `c1_phase1p_d0` + **공격자 동역학** `viability`) · 예산 상수 · **채점 함수 7종 소스 해시**(목적함수를 바꾸고 같은 falsifier라 부를 수 없게) · `d0_seed` 소스 + `V2-`(개발)/`V2C-`(확증) prefix 규약. `seal hash b3e1fc3fc676772f…`, **`--verify` → files 0 · score 0 · budget False → SEAL INTACT**(자기 위반을 탐지 못 하는 봉인은 장식이므로 포함).
- **K=1 최종 라벨**: `OBSERVED_NEAR_CONSTANT_ATTACK_DOMINANCE` · `UNDER_CURRENT_FIXED_CONDITION_AND_SEARCH` · **`TESTED_THROUGH_K2_GLOBAL_AND_K8_LOCAL_HIERARCHY`** · **`RAW_GRID_TEMPORAL_ADVANTAGE_INVALIDATED_BY_SAMPLING_DENSITY_CONFOUND`**. 금지 유지 = `ESCAPE_STRUCTURE_IS_INTRINSICALLY_K1` · `K1_IS_GLOBALLY_SUFFICIENT` · `TIME_VARYING_ATTACKS_CANNOT_IMPROVE`.
- **두 갈래 "동일 예산" 내역 기록(지시)**: authoritative 평가 수 · refinement iteration(SCALES 4 × N_PER_SCALE 96) · local-start 수(각 갈래 top-24) · stopping rule(scale 소진, segment_descent 개선 없으면 조기 종료) · incumbent 보존 규칙(매 scale 재삽입) **전부 동일**. 단 **정련 후 상수 승리가 시간가변 family의 전역 열세 증명은 아님** — 저차원 family가 최적화하기 쉬운 효과가 섞일 수 있으므로 fixed-condition empirical result로만 유지.
- **`0/45`의 지위**: *"시험한 구조화 temporal family와 현재 refinement 아래에서는 A0 incumbent 주변이든 별도 global temporal start든 더 강한 공격으로 이어지지 않았다"* — null이므로 **controller survival evidence가 아니라 attack-complexity diagnosis**. `DEVELOPMENT_BUILD` 유지.
- **held-out 외부조건 set 생성·봉인(평가 전)**: `spec hash c0868cbb3678b9cf…` · `list hash 94cc56e44aaff4d8…`. 5축 = **attacker lateral offset · heading · speed · cone_axis_deg(finisher pointing 기울임→net cone 축) · reset_seed**. **두 집합 병합 금지** — `IN_DISTRIBUTION` OFAT 16 + **CROSSED 34** = **50**, `STRESS` OFAT 14 + **CROSSED 24** = **38**, 합 **88 조건 × 8 defender trajectory = arm당 704쌍**. **OFAT만으로는 부족**하므로 교차조건(`lateral×heading` · `speed×cone` · `reset×lateral`)이 전체의 **66%(58/88)** — basin이 얇을수록 상호작용이 위험 지점이기 때문.
- **arm 역할 분리(지시의 핵심)**: **`RI-SHARED-v1` = `PRIMARY_CONFIRMATORY_CONTROLLER`**, controller·lane reserve·δ 규칙·PD gain 전부 동결한 **무변경 적용**(허용 질문: 일반화하는가) / **`RI-GMAX` = `SCENARIO_CONDITIONED_EXISTENCE_REFERENCE`**, 조건마다 δ **재탐색 = 새 합성**(허용 질문: admissible artifact가 **존재**하는가). **두 arm 결과를 같은 성공률 표에 합치는 것 금지**, `RI-GMAX`에 "일반화하는가"를 묻는 것도 금지.
- **보고 계층 고정**: `external condition → defender trajectory → controller arm`. 같은 외부조건 아래 여러 trajectory는 **독립 표본이 아니므로** `"N개 중 M개"` 단독 요약 **불허** — 외부조건별·trajectory별·arm별 **분리 보고**.
- **실현가능성 smoke test(controller·falsifier 미실행)**: 12개 (조건, trajectory) 프로브 중 **8개가 유효 발사 rollout**. **⚠️ 발견 1건 — cone 축 기울임이 발사 규칙과 상호작용**: `cone_axis_deg = ±3°, 6°`(STRESS)에서 `RH 2.8/0.15`가 **아예 발사하지 않음**. **발사하지 않는 조건은 결함이 아니라 "포획 시도가 일어나지 않는 조건"** — controller 평가에서 제외하되 **계수·보고**(조용히 버리면 캠페인이 편향).
- **확증 실행 순서(봉인)**: ①v2 코드 freeze[완료] ②held-out 목록 freeze[완료] ③알려진 반례 5건 exact replay ④5건 **fresh-search blind rediscovery**(검출력 진단 전용 — 이 5건이 v2를 형성했으므로 **일반성 증거 아님**) ⑤미해결 11건 새 확증 시드(`V2C-`) ⑥held-out `RI-SHARED-v1` 무변경 적용 ⑦held-out `RI-GMAX` 조건별 재합성·**별도 보고** ⑧그 뒤에만 survival 라벨 발행.
- **결과 라벨 제한**: `CONFIRMATORY_ESCAPE_FOUND` / `NO_ESCAPE_FOUND_UNDER_FROZEN_FALSIFIER_V2`. `SURVIVED_FALSIFIER_V2`는 반드시 **`UNDER_PRE_REGISTERED_HELD_OUT_CONDITIONS`**와 함께. **어떤 라벨도 안전 인증이나 봉인이 아님.**
- **상태**: `RI-GMAX` 1/9 falsified · 8/9 미해결 / `RI-SHARED` 4/7 falsified · 3/7 미해결 / MARL baseline provisional 유지. **이제 처음으로 외부조건이 실제로 달라지는 confirmatory campaign을 실행할 수 있는 상태.**

### 2026-07-26 (kkkkk) — 🎯 **K=2 전역 sweep에서 부호가 뒤집힘**(원시 격자는 시간변화 승 +27.2 mm → 동일 정련 후 상수 승 15/15, −22.9 mm) · v2 봉인 체크리스트 **13/13** · validation set **11+5=16**로 정정

- **채택**: 외부검토 총판정(개발 단계 결과 승인 — 단 "본질적으로 K=1"은 과함)의 정정 전항. 산출 = `shepherd/scripts/c1_falsifier_v2_k2_global.py` · `c1_falsifier_v2_freeze.py` + JSON 2종 + `URP/c1_falsifier_v2_freeze_2026-07-26.md`. `c1_falsifier_v2.py`에 **독립 global temporal starts** 추가.
- **결론 축소**: ~~"escape 구조는 본질적으로 K=1"~~ 철회 → **`OBSERVED_NEAR_CONSTANT_ATTACK_DOMINANCE` · `UNDER_CURRENT_FIXED_CONDITION_AND_SEARCH`**. 허용 문면 = *"현재 단일 공격자 초기조건·단일 cone geometry와 구현된 계층형 탐색 아래에서 발견된 최강 공격은 거의 상수였고 K=1→K=8 시간분할의 관측 이득은 0.104 mm 이하"*.
- **A1~A3 독립 global start 추가(지시 확인 항목)**: 단일 segment pulse(각 index) · 전반/후반 반대 · alternating · 크기 ramp 상·하 · 두 방향 two-phase · 방향 회전 sweep · A0와 무관한 상수 = **A1 1216 · A2 1472 · A3 1984개**, 전부 결정론. **⚠️ 첫 구현은 공허했음(기록)** — 독립 start와 상속 incumbent를 합쳐 전역 top-M을 뽑자 독립 start가 **원시 점수 55~82 mm 열세로 정련 전에 전부 탈락**, 검사 자체가 성립하지 않았음. **두 갈래에 동일 multi-scale 예산을 주고 정련 후 비교**로 수정 → **정련 후 독립이 상속을 이긴 stage-cell 0/45**, 격차 11.4~81.9 mm, 독립 갈래의 정련 이득 중앙값 **0.000 mm**(평탄 영역이라 국소 정련이 이동 못 시킴). 이것만으로는 "떨어진 시간가변 basin 부재"를 못 보이므로 K=2 전역 sweep 실시.
- **🎯 K=2 전역 sweep(192 방향² × 3 크기² = 331,776 two-phase/cell, 상수 대각선은 동일 격자의 부분집합)**: **원시 격자** — 시간변화 이득 **min +6.34 · median +27.19 · max +37.67 mm**(= "시간변화가 이긴다"로 읽힘). **동일 정련 후** — 이득 **min −25.21 · median −22.86 · max −3.42 mm**, **상수 갈래가 15/15 cell 승리**. **부호가 뒤집힘.**
- **원인 — 이 캠페인이 계속 싸워온 오류 유형의 재출현**: 거친 격자에서 two-phase family는 `192²×9 = 331,776` 표본, 상수 대각선은 `192×3 = 576` 표본 — **576배 차이**. ⇒ **차원이 다른 family를 거친 해상도에서 비교하면 측정되는 것은 family의 최적값이 아니라 표본 밀도.** 정련을 붙여야만 비교 성립하며, 정련 상수 최적(+0.0060)이 A0 독립 결과(+0.0061)와 일치해 교차 확인됨. ⇒ near-constant dominance는 **K=2에서 전역적으로 지지**되나 **K>2에 대한 진술은 아님**.
- **A1~A3의 지위(지시)**: **입증** = A0 최적점 주변에서 segment별 시간변화는 추가 이득 거의 없음 / **미입증** = 전체 K=8 공간에 별도 temporal basin 부재. ⇒ **`local attack-complexity diagnosis`로 승인, `attacker-class sufficiency` 증명으로는 보류**.
- **proxy 결론 범위 한정(지시)**: *"**평가된 A0–A3 candidate set에서** proxy ranking과 authoritative score가 사실상 일치했으므로 관측된 legacy miss의 주원인은 scoring mismatch가 아니라 **search coverage**"*. top-1 60/60 · top-5 5/5 60/60 · 오차 ≤1.33e−15 m. **유한 후보 일치**이며 전체 공격공간으로 확대 금지.
- **validation set 정정 — 15가 아니라 11+5=16**: 초기 D0 후보 16 = **`REGRESSION_COUNTEREXAMPLE_SUITE` 5** + **`CONFIRMATORY_NULL_EVALUATION` 11**. 5건 = `RH 5.0/0.55 SHARED`(D0, **"15 cell"에서 빠져 있던 cell**) · `RH 5.0/0.55 GMAX`(D2a) · `RH 2.8/0.15 SHARED` · `RH 3.2/0.25 SHARED` · `BASE 2.8/0.30 SHARED`(A0). 11건 = GMAX 8 + SHARED 3. 미해결 라벨 = **`NO_ESCAPE_FOUND_BY_DEVELOPMENT_FALSIFIER_V2` + `UNRESOLVED_PENDING_CONFIRMATORY_FALSIFIER_V2`**, ~~`SURVIVED_A3`~~·~~`A0_A3_SURVIVOR`~~ 금지. 5건 전부 **nominal-model falsification**(10 mm robust 승격 아님). 사용법 2분 — **exact regression(필수, 5/5 PASS)** vs **blind rediscovery(검출력 진단일 뿐, 설계에 쓴 반례이므로 일반성 증거 불가)**.
- **봉인 체크리스트 13/13 PASS** (⚠️ **캠페인 불변식 suite와 별개** — `c1_invariant_tests`(I1–I8, 13/13)와 하나로 보고 금지): ①표현 포함 ②incumbent 보존(bank 24→98) ③단조성 위반 0 ④독립 temporal starts ⑤multi-scale ⑥raw-bank best 보존 ⑦scenario-aware seed ⑧**paired arm CRN** ⑨알려진 반례 **5/5 replay** ⑩proxy-authoritative ranking ⑪결정성 ⑫경성 admissibility(`S(1.0001·a_max)=inf`) ⑬dev/confirmatory seed 분리(`V2-` vs `V2C-`). **⚠️ 8번은 처음 GAP이었고 그것은 검사가 틀린 것**(소스에서 문자열 `"arm"` grep → `warm_start`에 걸림). **문자열 일치는 성질의 검사가 아니므로** 시그니처 확인 + 같은 scenario·다른 arm 스트림 동일성 **행동 검사**로 교체.
- **남은 필수 단계**: **held-out 외부조건 set 미구축** — defender trajectory만 늘리면 부족하며 **attacker lateral offset · heading · speed · cone axis/finisher orientation · reset**을 봉인된 held-out에서 변화시켜야 함. 현 scope에서 survival label을 재발행해도 여전히 **매우 좁은 fixed-condition 결과**이고 **분포 수준 주장은 held-out 이후에만** 가능.
- **상태**: `RI-GMAX` 1/9 falsified · 8/9 미해결 / `RI-SHARED` 4/7 falsified · 3/7 미해결 / v2 **봉인 가능**(확증 실행 미실시) / MARL baseline **provisional 유지**.

### 2026-07-26 (jjjjj) — FALSIFIER-v2 **A0~A3 계층 + 누적 bank 실행**: 불변식 3종 15/15 · 신규 반례 0 · **A0→A3 개선폭 중앙값 0.065 mm**(= K 확장이 사실상 무의미) + 지시된 표현 정정 12건

- **채택**: 외부검토 총판정(A0 결과 승인 — falsifier 결함은 계통적이었고 `RI-SHARED`도 여러 셀에서 falsified)의 정정 12건 + A1/A2/A3·누적 bank 진행 승인. 산출 = `shepherd/scripts/c1_falsifier_v2.py` + `results/c1_corridor/c1_falsifier_v2.json` + `URP/c1_falsifier_v2_a0a3_2026-07-26.md`.
- **controller 현황(초기 D0 후보 16 기준, "생존 비율"로 쓰지 않음)**: `RI-GMAX` **1/9 `VERIFIED_FALSIFIED`** · 8/9 `UNRESOLVED_PENDING_FALSIFIER_V2` / `RI-SHARED` **4/7 `VERIFIED_FALSIFIED`** · 3/7 `UNRESOLVED_PENDING_FALSIFIER_V2`. SHARED 4건 = D0 `RH 5.0/0.55` + A0 K=1 `RH 2.8/0.15`·`RH 3.2/0.25`·`BASE 2.8/0.30`.
- **A0 반례 라벨**: `FALSIFIED_BY_DETERMINISTIC_K1_SEARCH` · `COUNTEREXAMPLE_WITHIN_LEGACY_ATTACKER_CLASS` · **`FALSIFICATION_STRENGTH = NOMINAL_MODEL_ONLY`**(S = −0.89~−3.44 mm로 사전등록 **10 mm 가산 기하오차 예산 안** ⇒ 유효하나 10 mm robust 반례는 아님).
- **표현 범위 제한(지시)**: 허용 = *"동일 attacker boundary condition·cone geometry 아래 **여러 defender trajectory**에서 within-class miss가 **반복**됐다"* / 금지 = ~~"여러 독립 scenario에서 계통적으로 실패"~~. ~~"독립 cell 14개"~~ → **`14 remaining controller–trajectory cells`**. scope 라벨 = `SINGLE_ATTACKER_INITIAL_CONDITION`(p=[15,0,0], v=[−20,0,0]) · `SINGLE_NET_CONE_GEOMETRY`(apex=[2,0,0], n_F=[1,0,0], θ=0.06281) · `MULTIPLE_DEFENDER_TRAJECTORIES`(15) · `FIXED_RESET_1100`. held-out은 최소 5종(공격자 lateral/axial offset · 초기속도 방향·크기 · cone axis/finisher 기하 · reset · defender witness) 변화 필요.
- **`S` 단위 규약 명시(지시)**: 두 항 **모두 미터, 동일 부호 규약**. `cone lateral = (half_angle − θ_net)·‖r‖`는 진짜 수직거리 `‖r‖·sin(·)`의 **소각 호길이 근사**이며 차이 `O(Δθ³)`(상대오차 <1e−7). **무차원 residual을 max 안에 넣으면 단위 오류 재발**하므로 문서화. admissibility는 항이 아니라 **경성 제약**.
- **⚠️ A0 격자 해상도 정량화(지시 6항)**: 8192 등면적 방향 → 1점당 **등면적 cap 반각 1.2661°**(최근접 간격 ~2.53°). basin 반각 0.20°/0.05°/0.02° 대비 **6.3× / 25.3× / 63.3× 거칠고**, 무작위 격자점이 basin에 들 확률 2.50% / 0.156% / 0.025%. ⇒ A0가 세 반례를 찾은 것은 **격자 덮음이 아니라 거친 상위후보에서 tangent 정련이 basin으로 내려갔기 때문**이며, 경사 없는 basin은 놓침. 따라서 GMAX 잔여 8건 = **`NO_K1_ESCAPE_FOUND_BY_A0` + `SURVIVAL_INTERPRETATION_ON_HOLD`**, ~~`A0_SURVIVED`~~ 금지.
- **A0~A3 + 누적 bank 실행**: `A0 K=1`(결정론 격자) → `A1 K=2` → `A2 K=4` → `A3 K=8`, 각 단계가 이전 incumbent를 **정확 구간반복으로 매입**. 누적 bank `B(A_n) ⊇ B(A_{n−1})` + 그 시점까지 모든 검증 반례(A3 후 96~98 entry, **표현 불가로 skip된 항목 0건** — K=8 witness는 블록상수라 K=2로 정확 축소). 정련 = multi-scale Gaussian(0.05→0.0004×a_max, 각 scale에서 incumbent 보존) + **per-segment 좌표 하강**(K>1이 실제로 사주는 자유도; 등방 Gaussian만으로는 A0 최적을 못 넘어 A1~A3가 공허해지는 것을 첫 실행에서 확인하고 추가).
- **불변식 3종 전부 통과**: 누적 bank(폐기 0) · incumbent 삽입 · **단조성 `S*(A0) ≥ S*(A1) ≥ S*(A2) ≥ S*(A3)` 15/15 assert 통과**.
- **🎯 결과 — K 확장이 거의 아무것도 사주지 않음**: **A0→A3 개선폭 min 0.012 / median 0.065 / max 0.104 mm**(15/15에서 개선은 있으나 이 규모). **신규 반례 0건**(기존 4건은 상속으로 전 단계 유지). ⇒ 이 문제의 escape 구조는 **본질적으로 K=1**이며, "D2a가 K=8이라서 찾았다"가 아니라는 앞 회차 판정을 **독립적으로 재확인**.
- **property test 10(탐색 proxy vs authoritative)**: **top-1 일치 60/60 · top-5 겹침 5/5 60/60 · best proxy 후보에서 `|proxy S − authoritative S| ≤ 1.33e−15 m`**(44/60은 정확히 0). ⇒ **proxy는 약한 고리가 아니었고 약했던 것은 탐색**.
- **명칭 정정(지시)**: ~~"legacy S 계통오차"~~ → **`OBSERVED_LEGACY_SEARCH_REGRET_LOWER_BOUND`**. `R = min(S_legacy_D1, S_legacy_D2a) − S_A0 = min 0.001239 · median 0.008601 · max 0.014543 m`, 15/15 양수. **A0도 전역최적을 증명하지 않으므로 실제 regret는 더 클 수 있는 하한**.
- **포화 반례 서술 정정(지시)**: 반례는 `‖a‖=30.0000`에서 발견됐고 방향 고정 후 크기를 낮춰도 **`[30−Δa, 30]`에서 escape 유지, Δa = 0.027~0.106 m/s² = a_max의 0.09~0.35%**. "껍질 artifact 아님"과 **`THIN_NEAR_SATURATION_RADIAL_BASIN`**을 함께 기록.
- **발견확률 지위 정정(지시)**: 영역 측도 + iid 가정 계산이므로 **model-based estimated probability**. *"legacy 부피균등 bank 모델 하에서 전체 예산이 basin을 표집할 추정 확률 0.01~0.19%(canary 5.64%)"*, 그리고 **"입증한다"가 아니라 "그 관측과 정량적으로 일관된다"**.
- **`RI-SHARED` 가설(허용 범위)**: *v1의 보수적 reference-offset 선택이 일부 defender trajectory에서 얇은 constant-acceleration escape basin을 남긴다.* **미확정**: δ가 작아서인지 · δ를 키우면 단조 해결인지 · selector만 바꾸면 충분한지. 세 반례는 `RI-SHARED-v2` CEGIS **직접 입력**, v1 기록과 **비혼합**.
- **v2 확증 설계(필수, 미실행)**: ① 코드·score·예산 봉인 ② 15 cell 전부 재실행 ③ **새 search seed** ④ 알려진 escape는 **regression canary로만** ⑤ **held-out attacker 초기조건·cone geometry 추가** ⑥ 그 뒤에만 survival 라벨 재발행. 현 빌드는 `DEVELOPMENT_BUILD`로 meta에 기록 — **null은 강도 증거가 아니고 검증된 반례만 증거**.
- **핵심 결론**: radial-inward controller class는 유망하나 shared selector v1은 여러 셀에서 실제 반례를 가지며, 기존 stochastic falsifier는 그것을 신뢰성 있게 검출하지 못했다. **controller 강도 비교보다 falsifier 검출력·외부조건 일반성 재정립이 먼저.**

### 2026-07-26 (iiiii) — 🚨 FALSIFIER-v2 **A0(K=1 명시 탐색)**: 독립 cell 14개 중 **3개에서 검증 K=1 반례** — `SEARCH_MISS`는 사고가 아니라 계통적 결함 · 부수로 **cell 독립성 붕괴** 발견

- **채택**: 외부검토 총판정(핵심 정정 승인 — falsifier 적합성이 controller 결과보다 먼저)의 라벨 체계 + 계층형 K=1 선행 탐색 지시. 산출 = `shepherd/scripts/c1_phase1p_falsifier_v2_k1.py` · `c1_phase1p_v2k1_verify.py` + JSON 2종 + `URP/c1_falsifier_v2_a0_2026-07-26.md`.
- **라벨(지시 그대로)**: `RH 5.0/0.55 f=10 / RI-GMAX` 누적 = `SURVIVED_D0` → `SURVIVED_D0_AND_D1`(**실행 기록으로 보존, 삭제 금지**) → `FALSIFIED_AT_D2A_STAGE` → `COUNTEREXAMPLE_IN_K1_SUBCLASS` → **`D1_WITHIN_CLASS_SEARCH_MISS`**(압축 최종). **금지 라벨**: `FALSIFIED_BY_K8_ONLY_ATTACK` · `RICHER_ATTACKER_CLASS_BROKE_CONTROLLER`. 나머지는 `SEARCH_MISS`가 아니라 `NO_ESCAPE_FOUND_UNDER_LEGACY_..._SEARCH` / `SURVIVAL_INTERPRETATION_SUSPENDED` / `FALSIFIER_ADEQUACY_NOT_ESTABLISHED`.
- **A0 설계**: 무작위 없음 — Fibonacci 등면적 방향격자 **8192** × 크기 명시 sweep **64** × tangent-plane 국소정련(2°→0.5°→0.125°→0.03°, 4라운드). 채점 `S(a)=max(−kill,−cone)` if `‖a‖≤a_max` else `+inf`, **escape ⟺ S<0**. 격자는 표본 proxy, 잔류 후보는 **전부 연속 판정기로 재채점**.
- **⚠️ 지시 문면 이탈 2건(기록)**: ① admissibility를 `max` 안에 넣으면 **단위 불일치**(m/s² vs m)이고 **허용집합이 닫힌 집합이므로 포화 공격에서 항 값이 정확히 0 → `S≥0` 강제 → 포화 escape 표현 불가**. **실행으로 잡힘** — 첫 실행에서 전 cell 격자 최선이 `0.000000`에 고정. **이번에 찾은 반례 3건이 전부 `‖a‖=30.0000` 정확 포화**이므로 원안대로면 하나도 못 찾음. admissibility는 경성 제약(`+inf`)으로 수정 ② 지시는 `max_a S`였으나 escape가 `S<0`이므로 정보를 갖는 극값은 **`min_a S`**.
- **🚨 결과**: `REGRESSION_CANARY` 1건 재발견(당연, 일반 성능 증거 아님) + **독립 cell 14 중 3에서 검증 K=1 반례** — `RH 2.8/0.15 SHARED`(S=−0.003441) · `RH 3.2/0.25 SHARED`(−0.000890) · `BASE 2.8/0.30 SHARED`(−0.001988). **전부 `RI-SHARED`**. `RI-GMAX` 8개 독립 cell은 정련 후에도 **S=+5.1~+6.4 mm**로 추가 falsification 0(단, **부재의 증명 아님**).
- **적대적 검증 4관문 전부 PASS**: **V1** canary의 독립 `replay` 경로 재판정 4/4 · **V2** K=1·2·4·8 verdict 동일 4/4(⇒ D0/D1/D2a가 탐색한 **바로 그 클래스 안**) · **V3** 방향 고정 크기 sweep에서 **껍질 전용 아님**(escape가 0.027~0.106 m/s² 구간 유지) · **V4** legacy `reachable_accels`는 **부피균등**(`mag=a_max·U^{1/3}`)이므로 예산 전체(48추첨×20000)에서 발견확률 **0.01~0.19%**(canary cell만 5.64% — D2a가 한 번 맞히고 D1이 못 맞힌 이유). top-48 pool은 cell당 **고유 공격 1건**이며 48건으로 세지 않음.
- **🚨 부수 발견 — cell 독립성 붕괴**: 격자 최선 S가 14 cell에서 전부 정확히 `+0.019491`로 같아 추적한 결과, **15 cell 전체에서 서로 다른 공격자 경계조건 1개**(`p=[15,0,0]`, `v=[−20,0,0]`) · **net cone 기하 1개**(`apex=[2,0,0]`, `n_F=[1,0,0]`, `θ=0.06281`) · 방어자 경로만 15개. 즉 **"고유 scenario 9"는 단일 공격자 초기조건·단일 net cone에 대한 9개 방어자 구성**. cone 항이 scenario 무관이라 격자 최선이 동일했던 것 — **버그가 아니라 설정의 성질**. `SAMPLE_STRUCTURE`에 `SINGLE_ATTACKER_BOUNDARY_CONDITION` · `SINGLE_NET_CONE_GEOMETRY` · `DEFENDER_CONFIGURATION_VARIATION_ONLY` 추가 — `FIXED_CONDITION`보다도 좁음.
- **공통 척도 비교(지시 §4 이행)**: 같은 authoritative `S`, 같은 경계 0. **탐지력 격차 = min(S_legacy_D1, S_legacy_D2a) − S_v2K1 = min 0.001239 · median 0.008601 · max 0.014543 m, 15/15 전부 양수** — legacy는 단 한 cell도 v2-A0보다 가깝게 가지 못함. 부호 뒤집힌 cell 3. ⇒ **단위 문제 없이**: *legacy falsifier의 S 계통오차(median 8.6 mm)가 살아남은 GMAX cell의 경계까지 거리(+5.1~6.4 mm)보다 크다.* 별개로 lane-reserve excess와의 비교는 지시대로 **직접 오류 상계가 아닌 경고 문장으로만** 유지.
- **미구현(다음 블록)**: A1/A2/A3 계층(K=2/4/8, 하위 최선 상속) · **누적 adversarial bank** `B_D2 = B_D0 ∪ B_D1 ∪ B_D2new ∪ B_known` + 단조성 `best(D2) ≥ best(D1) ≥ best(D0)` 강제 · **incumbent preservation** · **multi-scale sigma** · property test 10종(특히 #10 proxy 상위-k vs authoritative 상위-k recall). **v2 동결 후** 새 seed·15 cell·held-out canary로 확증.
- **상태**: `FALSIFIER-v1` 확인된 within-class miss **4건**(D2a 1 + A0 3), 기록 보존. `RI-SHARED` 6→**3 falsified**/3 잔여 · `RI-GMAX` 8 잔여. CEGIS attack set 6 → **9건**(신규 3건 전부 K=1 상수 가속도). MARL 기준선: `RI-SHARED` provisional(3 cell falsified) · `RI-GMAX` `SCENARIO_CONDITIONED_EXISTENCE_REFERENCE` · robustness ranking **HOLD**.
- **유효 유지**: controller 구성 · harness validation(canary) · class containment · 결정적 재현 · nesting test. **무효화된 것은 "탐색기의 null = 방어자의 강도"라는 해석뿐**.

### 2026-07-25 (hhhhh) — ⚠️ Phase 1P **D2a: 1건 falsify — 그런데 그 witness는 K=8이 필요 없었다** (상수 가속도 = K=1 표현 가능) ⇒ **D1 null은 자기 클래스 내 탐색 실패** · 생존 주장 전면 보류

- **채택**: 외부검토 총판정(수정승인 — D2a 진입 가능)의 preflight 3항 + D2a 본실행. 산출 = `shepherd/scripts/c1_phase1p_d1_canary.py` · `c1_phase1p_d1_diag.py` · `c1_phase1p_d2a_containment.py` · `c1_phase1p_d2a.py` · `c1_phase1p_d2a_witness_analysis.py` + 대응 JSON 5종 + `URP/c1_phase1p_d2a_preflight_2026-07-25.md` · `URP/c1_phase1p_d2a_2026-07-25.md`.
- **게이트 1 — D1 canary `D1_HARNESS_VALIDATED`**: C1 D0 escape 2건 재생 → **ESCAPE 2/2**, C2 warm-start → **후보 방출 1·1**, C3 MAXCLR **미터급**(kill +1.07246) → ESCAPE·후보 **2672**, C4 config parity 차이 키 **`['launches']`뿐**. ⇒ `cands 0`은 파이프라인 침묵이 아님. **실행 중 결함 1건 발견·수정**: C3 선택 루프가 `modes` 레코드를 `witness` 키(실제는 `scenario_id`)로 읽고 대margin 통제에 `tightest`(정의상 최소)를 쓰려 함 — **통제 자체가 무력화될 뻔함**.
- **게이트 2 — D2a containment `D2A_CONTAINMENT_VERIFIED`(4계층)**: L1 매입 `embed(a4)=repeat(a4,2)`로 `u(t)` 4096시점 동일 · L2 **bit parity**(`tobytes`) · L3 rollout·verdict parity(최악 endpoint **7.11e−15 m**, 최악 연속 margin **3.55e−15 m**) · L4 알려진 K4 escape **6건 전부 매입 후에도 ESCAPE 유지**. **D1 readout 문면 정정**: rollout의 "비트 단위 재현"은 **성립 불가**(K=8은 반스텝 2회 합성 + 더 촘촘한 substep 격자 ⇒ 정확산술에서만 동일). 비트 동일은 **제어신호**에 대해, 실질 검사는 **verdict 동일**.
- **per-cell 진단(`cands 0`은 숫자다)**: 결정성 먼저 — **15/15 cell이 D1 candidate count를 재현**. gap to threshold **min 0.000525 m · median 0.015853 m · max 0.026265 m**. `adm slack 0.0000`(BASE 4.0/0.70 C·P GMAX) = 최선 후보가 공격자 가속도 한계에 붙음. **⚠️ `SEARCH_REFINEMENT_INEFFECTIVE_AT_D1`** — 15 cell 중 **13**에서 전역 최선이 CEM refinement가 아니라 **warm-start bank argmax**에서 나옴(개선된 cell은 BASE 4.0/0.70 C·P GMAX 2건뿐).
- **D2a 예산(실행 전 고정)**: K 8 · pop 384(파라미터 차원 24→48이므로 2배) · iters 14 · n_bank 20000 · **48 bank-warm + 8 incumbent-warm = 56 searches/cell**. **K4 incumbent 매입 seeding 강제** + **중첩 단조성 `best_D2a ≥ k4_incumbent − 1e-9` 검사 15/15 통과**.
- **표면 결과**: `RI-GMAX` 9 투입 → **FALSIFIED 1** / 8 생존 · `RI-SHARED` 6 투입 → 0 / 6 생존. 유일 falsification = **`RH 5.0/0.55 f=10` / `RI-GMAX`** δ=0.135, `KILL`, 연속 margin **+0.005088 m**, hash `e9600d3132e27f72`. **D1 진단에서 이 cell의 gap이 0.525 mm로 15개 중 압도적 최소였고 — 진단이 예측했다.**
- **🚨 그러나 그 witness는 K=8이 필요 없다 — `SEARCH_MISS_INSIDE_K4_CLASS`**: ① **8개 구간 전부 동일한 상수 가속도**(‖a‖=29.8292, a_max 30.0). **K=1·2·4·8 재표현 전부 동일 margin +0.005088, 전부 escape** ⇒ 이 공격은 **K=4 클래스 안에**(K=1 안에도) 있다 ② **출처는 CEM이 아니라 원시 bank argmax**(`search_bank_seed_id 2 · restart 2`, CEM 기여 **0**) ③ **D1 자신의 48회 추첨 재생성 대조** — 최근접 표본이 **0.115° 떨어져 있었는데 점수는 −0.035021 m**, 5° 이내 **1811개**의 최고 점수도 −0.002691 m. ⇒ escape 집합이 (방향, 크기) 공간에서 **극히 얇은 조각**이며 목적함수가 표본 해상도보다 빠르게 변한다.
- **⇒ 판정 정정**: D2a는 ~~"넓힌 K=8이 K=4-견고 controller를 깼다"~~를 보이지 **않았고**, **D1의 그 cell null이 자기 클래스 내 탐색 실패였음**을 보였다. **`RH 5.0/0.55 f=10 / RI-GMAX`의 `SURVIVED_D0_AND_D1` 라벨 철회 → `SEARCH_MISS`.**
- **🚨🚨 나머지 14건으로의 파급 — `SEARCH_NOISE_DOMINATED`**: D1과 D2a의 bank 최고점수 차이(= 같은 K·같은 counts, 시드만 stage 분리한 재추첨의 잡음) = **min 0.062 mm · median 4.173 mm · max 14.389 mm**. 이를 방어 주장과 나란히 놓으면 — **`RI-GMAX`가 방어한다는 lane reserve excess는 0.3–2.4 mm**. **falsifier 자신의 탐색 잡음이 방어 주장이 걸린 여유폭보다 크다.**
- **판정**: **`SURVIVAL_CLAIMS_ON_HOLD_PENDING_FALSIFIER_UPGRADE`**. 철회 1건 + 나머지 14건은 라벨 유지하되 **`SEARCH_NOISE_DOMINATED` 태그 부착**(현 falsifier로 판별 불가). **영향받지 않는 것 4가지**: canary(파이프라인 정상) · containment(K=8 ⊃ K=4) · 결정성 15/15 · 중첩 단조성 15/15. **controller가 틀렸다는 증거가 아니라 판별력이 부족하다는 증거** — 보수적 검정의 실패가 반대 명제의 증거가 아니듯, **약한 falsifier의 null도 견고성의 증거가 아니다**.
- **falsifier 업그레이드 처방(원인 특정됨)**: ① bank 상위 M개 주변 **(방향, 크기) 국소 정련** ② **크기 축 명시 sweep**(escape는 ‖a‖=a_max의 99.4%에서 나옴) ③ CEM 초기 sigma(현 0.75·a_max)가 mm급 지형에 과대 → 재조정 ④ 업그레이드 후 **D0·D1·D2a 전 cell 재실행**(falsifier 강화 시 기존 생존 주장은 전부 재검정 대상).
- **명명·버전·범위(지시 반영)**: `cert seeds` → **`search_bank_seeds`/`replan_bank_seeds`**(실행된 `c1_phase1p_d1.py`는 키 이름 불변, 매핑만 기록, D2a부터 새 이름) · **D1-v0 `NOT EXECUTED / INVALIDATED`(witness-blind) / D1-v1 `EXECUTED`** = **"counts-preserving corrective-amended D1"** · 범위 태그 `ATTACKER_CLASS` · `RESET_SCOPE FIXED_RESET_1100` · `SAMPLE_STRUCTURE` **artifact 15 / 고유 scenario 9, 독립 표본 아님** · `CLASS_SCOPE` Class A 한정 · 예산 표현 ~~"4배 강한 공격자"~~ → **"동일 K4 클래스에서 launch 4배"**.
- **CEGIS attack set**: 기존 5건 + **D2a 신규 1건**(`e9600d3132e27f72`, 상수 가속도이므로 **K=1 공격 라이브러리**에도 등재) = **6건**.
- **MARL 관점**: `RI-GMAX`/`RI-SHARED`는 여전히 scripted baseline으로 사용 가능하나 성격이 바뀜 — ~~"D0·D1을 통과한 견고한 controller"~~ → **"현 falsifier가 깨지 못한 controller"**. 학습 정책과 비교 시 **동일 falsifier를 양쪽에 동일 적용**해야 하며, 약한 falsifier는 **양쪽을 공통으로 과대평가**함. 절대 견고성 주장은 업그레이드 이후로 연기.
- **불변**: `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · **1H 계속 보류** · C-3 · C-4 · 실용성·분포 일반성 계속 HOLD.

### 2026-07-25 (ggggg) — 🎯 Phase 1P **D1 자동 발동 완료: 15/15 `SURVIVED_D0_AND_D1`** (D0의 4배 예산에서 검증 escape 0 · 탐색 후보조차 0) — 봉인 아님, 다음은 D2a

- **채택**: 사전등록 dormant D1의 자동 발동(trigger = SURVIVED_D0). 산출 = `shepherd/scripts/c1_phase1p_d1.py` + `results/c1_corridor/c1_phase1p_d1.json` + `URP/c1_phase1p_d1_2026-07-25.md`.
- **🎯 결과**: `RI-GMAX` 9 투입 → `FALSIFIED_D1` **0** · `SURVIVED_D0_AND_D1` **9** / `RI-SHARED` 6 투입 → **0** · **6**. **CEGIS 신규 escape 0**, abort 0. **전 cell에서 `cands 0`** — CEM이 검증 이전 단계의 escape 후보조차 생성하지 못함(D0에서는 RH 5.0/0.55 SHARED가 2건을 냈던 것과 대비).
- **예산**: registry가 고정한 counts 그대로 **restarts 16 × cert seeds 3 = 48 searches/cell**(D0는 12, **4배**), K 4 · pop 192 · iters 14 · n_cert 20000. registry 문면 "counts fixed now so a future survivor cannot retro-tune the stopping point"를 준수.
- **불변식을 신뢰가 아니라 강제**: ① "artifact와 설정을 D0 이전에 봉인" → 6A의 `artifact_hash`를 **재독해 대조**, 불일치 시 해당 cell **abort**(0건 발생) ② "D1 내부 controller 재최적화 금지" → δ를 **D0 기록에서 읽기만** 하며 모듈에 δ 변경 경로 없음 ③ "verifier·objective·attacker dynamics 불변" → D0와 **동일한** `exact_min_clearance`·cone predicate·`_seg_paths_turn`.
- **⚠️ registry 문면에서의 의도적 이탈 1건(기록)**: registry는 counts와 함께 **seed 상수**(`64000201–16`, `91000101–3`)도 나열하나 이는 **C-6 이전 것이고 witness-blind** — 그대로 쓰면 모든 scenario가 같은 공격자 스트림을 받으며, 이는 이 캠페인이 두 번 확인하고 지난 회차 `replan_at`에서 **세 번째로 재발**한 결함. 따라서 **counts는 정확히 지키고 seed 값은 중앙 `d0_seed(stage_id="D1")`에서 파생**(D0 스트림과도 분리). **문자에서 벗어나 의도를 따른 것이며 자의적 변경이 아니라 기록된 이탈.**
- **누적 라벨**: `DIAGNOSTIC_NULL_CANDIDATES`(GMAX 9/10 · SHARED 7/10) → `SURVIVED_D0`(9/9 · 6/7) → **`SURVIVED_D0_AND_D1`(9/9 · 6/6)**.
- **🚫 아직 아님**: **봉인 아님** — 다음은 **D2a(K=8 nested)**이고 그 **containment test는 필수**(K=4 artifact가 K=8 하에서 **비트 단위 재현**돼야 함). D2b(K=6)는 non-nested exploratory라 생존 주장에 사용 불가. **실용성 아님** — `RI-GMAX`는 여전히 `RESERVE_BOUNDARY_CONTROLLER`(excess 0.3–2.4 mm)이며 tracking noise·actuator lag·jerk/slew·state-estimation error·model mismatch **전부 미모델링**. reset 1100 단일 `FIXED_CONDITION` · **Class A만**(Class B 2건 별도 recovery track) · 공격자 클래스 K=4.
- **MARL 관점**: **비교 기준선이 생김.** `RI-GMAX`/`RI-SHARED`는 D0·D1을 통과한 constructive controller artifact이므로 학습 정책을 **이것들에 대해** 평가할 수 있음. 다만 `FIXED_CONDITION`이며 분포 수준 목표는 아직 아님.
- **다음**: ① **D2a**(K=8 nested, containment test 필수) ② **CEGIS** — 현 attack set = RH 4.0/0.40 + MAXCLR 2건 + D0 신규 2건(D1 신규 0), 대상 = Class A 저항 1건 + Class B 2건 ③ **Class B recovery track**(terminal-ring reference + pre-fire radial recovery) ④ **실용성 게이트** — 미모델링 5종을 넣었을 때 gate가 견디는지. 이것을 통과하기 전에는 실용 controller 주장 불가.
- **불변**: `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · **1H 계속 보류** · C-3 · C-4.

### 2026-07-25 (fffff) — 🎯 Phase 1P **D0 판정: `RI-GMAX` 9/9 · `RI-SHARED` 6/7 `SURVIVED_D0`** — 캠페인 최초의 양성 결과 (봉인 아님, D1 자동 발동)

- **채택**: 외부검토 총판정(재봉인본으로 D0 진행 승인 + preflight 4항). 산출 = `shepherd/scripts/c1_phase1p_d0.py` + `results/c1_corridor/c1_phase1p_d0.json` + `URP/c1_phase1p_d0_2026-07-25.md`.
- **preflight 4항**: ① **라벨** — 9/10·7/10을 `survived`로 부르지 않고 **`DIAGNOSTIC_NULL_CANDIDATES`**로 명명, `SURVIVED_D0`는 D0 이후에만. D0 투입 = GMAX 9 + SHARED 7 = **arm–scenario 16**, **고유 scenario 9**("20 arm–scenario"는 discovery 표였고 투입량이 아님). ② **seed 중앙화** — 모듈의 **모든** 스트림이 단일 `d0_seed(stage_id, rng_role, scenario_id, reset_id, attacker_class, restart_id, base_seed)`에서 생성, `scenario_id` 항상 포함·`arm` 절대 제외(paired CRN)·`stage_id`로 D0/D1/D2 분리·`rng_role`로 warm-start/CEM/검증 분리, **프로토콜 버전 증가**(`c1-D0-inward-2026-07-25-v1`). **manifest 대조 검사 통과** — 같은 scenario·다른 arm 동일 / 다른 scenario 상이. ③ **tracking 지표 5종** 추가(`max_tracking_error = δ`는 reference 계단이지 추종 품질이 아님). ④ **`SHARED만 생존`을 자동 버그로 간주 금지** → `NONMONOTONE_DEFENSE_RESPONSE_OR_SEARCH_VARIATION`, 감사 트리거로만.
- **D0 예산(사전등록, 진단보다 엄격)**: **6 bank seeds × 2 restarts = 12 searches**(진단 8), n_bank 20000·pop 192·iters 14·K 4. 스트림은 `stage_id="D0"`로 진단과 구조적 분리.
- **🎯 결과**: **`RI-GMAX` 9 투입 → `FALSIFIED_D0` 0 · `SURVIVED_D0` 9** / **`RI-SHARED` 7 투입 → 1 · 6**. paired 셀 = **both survived 6 · gmax only 1 · both falsified 0 · `NONMONOTONE...` 0**.
- **유일한 falsification**: `RH 5.0/0.55 f=10`/`RI-SHARED` δ=0.115, 검증 escape 2건(KILL kill +0.00509 · CONE_LATERAL kill +0.00496). 같은 scenario의 `RI-GMAX`는 δ=**0.135**로 생존. **lane 여유가 더 넉넉한 쪽(SHARED excess +0.0186 vs GMAX +0.0010)이 falsify** — δ가 작아서이며 selector 보수성 가설과 일관하나 **원인 확정 아님**.
- **존재성 vs 실용성 분리**: 존재성 = "nominal model에서 lane reserve 10 mm를 만족하는 scenario-specific inward controller artifact가 상향 D0 예산의 공격자 탐색에 9/9 생존" **주장 가능**. 실용성 = **주장 불가** — `RI-GMAX`는 최대 RESERVE_VALID δ를 택해 **구조적으로 reserve 경계**(Class A 10/10에서 excess 0.3~2.4 mm)이고 **tracking noise·actuator lag·jerk/slew·state-estimation error·model mismatch 전부 미모델링**. 라벨에 **`RESERVE_BOUNDARY_CONTROLLER`** 병기. **D0/D1 생존과 실용 controller 적합성을 합치지 않음.**
- **프로토콜 버전 이력**: `RI-SHARED-v0`(witness-blind seed, diagnostic 6/10) = **`INVALIDATED_FOR_D0_SELECTION`**, **삭제하지 않고 사유와 함께 보존** / `RI-SHARED-v1`(scenario-aware paired, 7/10) = `SEALED_FOR_D0` → D0 6/7.
- **ledger**: **C-14 신설**(CONFIRMED, D0 단계). 폐기표에 `RI-SHARED-v0` 6/10 등재.
- **다음**: 사전등록 **D1 자동 발동**(trigger = D0 검증 escape 0인 controller-scenario) — K 4·pop 192·iters 14·**restarts 16**·replan seeds 16종·cert seeds 3종·n_cert 20000, 불변식 = artifact/설정은 D0 이전 봉인·D1 내부 controller 재최적화 금지·verifier/objective/attacker dynamics 불변. 대상 **15 arm–scenario**(GMAX 9 + SHARED 6). 생존 시 **D2a(K=8 nested)**. **CEGIS attack set에 D0 신규 escape 2건 즉시 추가**(기존: RH 4.0/0.40 + MAXCLR 2건).
- **🚫 아직 아님**: `SURVIVED_D0`는 **봉인이 아님**(누적 라벨의 한 단계) · reset 1100 단일 `FIXED_CONDITION` · **Class A만**(Class B 2건 별도 recovery track) · `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · **1H 계속 보류**.

### 2026-07-25 (eeeee) — 🚨 Phase 1P 6A 재봉인: **`replan_at`의 witness-blind seed 결함(C-6 재발) 발견·수정** → `RI-SHARED` 6/10 → **7/10** · δ **4분해** 도입 · `lane_reserve_excess`로 GMAX가 gate 경계 oracle임이 수치화

- **채택**: 외부검토 총판정(D0 진행 승인 + δ 지표 재분해 요구). 산출 = `URP/c1_phase1p_step6a_reseal_2026-07-25.md` + 갱신된 `shepherd/scripts/{c1_phase1p_6a_dynamic.py, c1_phase1p_6a_seal.py}` + `results/c1_corridor/c1_phase1p_6a_sealed_arms.json`.
- **🚨 D0 직전 발견한 seed 결함**: `c1_phase1p_6a_dynamic.replan_at`이 `_div_seeds(bs, "shared", "w:shared", r)`로 **scenario_id를 리터럴 상수**로 고정 → **모든 witness가 동일 공격자 스트림**. **C-6에서 확정한 witness-blind seeding이 새 함수에서 재발.** arm 이름을 빼는 것은 옳았으나(paired 비교) scenario를 빼면 안 됐음. 수정 + `scenario_id` 누락 시 **예외 발생**하도록 강제. **수정이 수치를 바꿈** — `RI-SHARED` **6/10 → 7/10**(RH 5.0/0.55 esc 2→0 · BASE 4.0/0.70 C 2→8 · BASE 3.2/0.50 C 5→7). **이전 봉인본의 진단 수치는 오염돼 있었으므로 D0는 재봉인본으로 수행.**
- **δ 4분해(지시 1항, 지적 수치와 정확히 일치)** — `BASE 3.2/0.50 C`/`RI-GMAX`, δ=0.1100: `reference_offset` **+0.1100** · `absolute_radial_displacement` **−0.0279** · **`achieved_offset_from_nominal` +0.1017(controller의 인과적 효과)** · `terminal_tracking_error` **+0.0083** · `max_tracking_error` +0.1100 · `nominal_radial_drift` +0.0739. ⇒ **"실제 내향 이동 28 mm"만 보고한 제 이전 문면은 controller 효과를 과소표현.** 올바른 판독 = "nominal ring이 73.9 mm 바깥으로 갈 예정이었으나 controller가 상쇄해 실제로는 27.9 mm 안으로 갔고, **nominal 대비 101.7 mm 내향 편차** 달성".
- **reference 불연속 기록(지시 2항)**: `max_tracking_error = δ`인 것은 **발사 순간 reference가 계단 이동**하기 때문. **위치·속도는 연속이나 reference와 명령 가속도는 불연속.** 미모델링 한계를 artifact `unmodelled_limits`에 명시 — acceleration slew rate · actuator lag · jerk bound · 저수준 sample delay · tracking noise. D0에는 영향 없으나 **실용 controller 주장의 한계**.
- **`lane_reserve_excess_m` 신설(지시 3항)**: `RI-GMAX`는 최대 RESERVE_VALID δ를 택하므로 **구조적으로 항상 reserve 경계** — Class A **10/10 전부 excess 0.3 ~ 2.4 mm**. "reserve-valid"와 "실질적으로 넉넉함"은 다르다는 지적이 수치로 확인됨.
- **arm 지위 명명**: `RI-GMAX` = **`SCENARIO_SPECIFIC_PREDICTIVE_INWARD_EXISTENCE_PROBE`** / `RI-SHARED` = **`SHARED_PREDICTIVE_RADIAL_INWARD_SELECTOR`**(fire 상태에서 δ 후보 생성 → nominal forward simulation → gate-valid grid 선택 → 저수준 PD 추종 = **model-predictive architecture**).
- **평가 단위 분리(지시 4항)**: `RI-GMAX` **survived 9/10**, `RI-SHARED` **7/10**, 고유 scenario **10**(Class A), arm–scenario 평가 **20**. **"20 중 몇 개" 식 병합 금지.** paired 결과 — **both null 7** · **GMAX only 2**(BASE 3.2/0.50 C δ 0.110 vs 0.025 · BASE 4.0/0.70 C 0.145 vs 0.060, 둘 다 SHARED의 δ가 훨씬 작음) · both escape 1(RH 4.0/0.40) · **SHARED only 0**(이상 신호 미발생).
- **D0 seed(지시 5항)**: `Hash(protocol_version, scenario_id, reset_id, attacker_class, restart_id, base_seed)` — **arm 이름 제외, scenario_id 포함**. 각 arm은 독립 최적화·검증하고 artifact 별도 저장; 공통 스트림은 paired 비교용이지 탐색 상태 공유가 아님.
- **selector 동결 유지(지시 6항)**: SHARED가 GMAX보다 낮다고 **지금 reserve·δ 공식 손대지 않음**. 개선안은 `RI-SHARED-v2`로 별도 프로토콜, **v1 결과 보존**.
- **Class B(지시 8항)**: 두 arm 모두 δ=0.200에서 escape 8건. 첫 defender class는 shifted nominal이 아니라 **terminal ring 직접 reference** + pre-fire radial recovery + 전개창 변위 제약 + bounded feedback tracking.
- **다음**: 추가 진단 없이 **봉인된 그대로 D0** — `RI-GMAX` 9 + `RI-SHARED` 7 arm–scenario. escape 발견 → `FALSIFIED_BY_ADVERSARIAL_REPLAN_D0` + CEGIS attack set 추가 / escape 0 → `SURVIVED_D0` + **사전등록 D1 자동 실행** → `SURVIVED_D0_AND_D1` → D2a. **`SHARED만 생존`이 나오면 δ 단조성 가정 붕괴 또는 artifact mismatch이므로 감사 대상.**
- **불변**: `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · **1H 계속 보류** · C-3 · C-4 · D0 예산/판정기/판정.

### 2026-07-25 (ddddd) — ✅ Phase 1P step 6A 봉인: **`RI-GMAX`(D0 후보 9/10) · `RI-SHARED`(6/10) 2-arm 분리 봉인** + 🚨 **δ 의미 정정(reference offset ≠ 이동량, 실제 28 mm)**

- **채택**: 외부검토 총판정(수정승인). 산출 = `shepherd/scripts/c1_phase1p_6a_seal.py` + `results/c1_corridor/c1_phase1p_6a_sealed_arms.json` + `URP/c1_phase1p_step6a_sealed_arms_2026-07-25.md`.
- **2-arm 분리(지시 1항)**: **`RI-GMAX`** = scenario별 최대 RESERVE_VALID δ, **scenario-specific 존재성 프로브**(하나의 controller가 아니라 scenario당 숫자 하나) / **`RI-SHARED`** = 전 scenario 동일 규칙, **공유 controller 아키텍처 후보**. **섞지 않음** — D0 결과가 "GMAX 생존·SHARED 실패 = selector 부족 / 둘 다 생존 = 강한 후보 / 둘 다 실패 = class 부족 / GMAX도 실패 = 탐색예산 artifact"로 읽히게 함.
- **controller 성격 정정(지시 2항)**: "상수 스칼라일 뿐"은 과소 표현. 2층 구조 — 고수준 = 발사 전 고정 스칼라 오프셋(open-loop), 저수준 = shifted nominal 추종 **유계 PD feedback**. = **"scenario-conditioned scalar inward offset tracked by a bounded low-level feedback controller"**. 공격자 상태에 반응하는 high-level policy는 아님.
- **selector 명명(지시 4항)**: "gate-valid 중 최대로 스냅"은 전개창 **전방 시뮬레이션**을 요구하므로 반응형 규칙이 아님 → **`PREDICTIVE_RADIAL_INWARD_SELECTOR`**, 전방 시뮬레이션을 **harness가 아니라 controller의 일부로 선언**.
- **reserve를 gate 정의에 포함(지시 3항)**: `RESERVE_VALID = E_cap ∧ m_lane ≥ 0.010 m ∧ defender admissible`. valid 집합의 **연결성을 가정하지 않고 측정** — 12/12 전부 `[0, δ_max]` 단일 구간, **비연결 0건**. 구간·선택점이 속한 run·선택점 ±5 mm gate 상태 전부 저장.
- **결과**: **Class A — `RI-GMAX` D0 후보 9/10**(RH 4.0/0.40만 esc 3), **`RI-SHARED` 6/10**(RH 4.0/0.40 esc 8 · RH 5.0/0.55 esc 2 · BASE 3.2/0.50 C esc 5 · BASE 4.0/0.70 C esc 2). **Class B(MAXCLR) 두 arm 모두 0/2**, δ=0.200에서도 esc 8.
- **포화 등급 분리(지시 6항)**: `DYNAMICALLY_ADMISSIBLE_WITH_CONTROL_RESERVE` / `..._AT_ACCELERATION_LIMIT`. 각 arm 3건이 한계 등급 — D0에는 넣되 실용 후보로는 약함. 포화 시간비율·최대 연속 포화 스텝·전개창 내 포화 여부·추종오차를 artifact에 기록.
- **🚨 δ 의미 정정 — 지시 5항의 trace가 드러냄**: `BASE 3.2/0.50 C`(δ=0.110)에서 nominal 반경은 **바깥으로 +0.0739 m** 표류하는데 actual은 **안으로 −0.0279 m**. 추종오차 = **0.1100 m = δ 정확히**. ⇒ **δ = 0.110 m는 링이 110 mm 안으로 갔다는 뜻이 아니라 nominal이 갔을 자리보다 110 mm 안쪽이라는 뜻이고, 절대 내향 이동은 28 mm.** 명령 가속도가 step 1 이후 0.1~0.7 m/s²로 거의 0인 것도 보정이 nominal을 **상쇄**하기 때문이며, lane 여유가 35.2 → 10.7 mm로 **24.5 mm만** 준 것도 28 mm 이동과 일치. **이전 문서들이 δ를 이동량처럼 읽히게 쓴 것을 정정**하고 달성 변위는 `achieved_inward_m`으로 별도 기록.
- **봉인 artifact(지시 7항)**: arm×witness마다 선택 δ·선택 규칙 문면·PD gains(kp 100·kd 20)·dt·A_MAX·reference·LANE_RESERVE·gate 5필드·admissibility 5필드·saturation 5필드·tracking_error·RESERVE_VALID 격자/구간/run/±5 mm·`defender_trajectory_sha`·`defender_velocity_sha`·reset·verifier version·진단 예산 + `artifact_hash`(SHA-256 24자). **D0 결과를 보고 δ 재조정은 rerun이 아니라 프로토콜 개정.**
- **CEGIS 입력 누적(지시 8항)**: 초기 = RH 4.0/0.40 + MAXCLR 2건의 verified escape / **추가 = D0·D1이 falsify한 모든 신규 escape**.
- **🚫 아직 아님**: `SURVIVED_DIAGNOSTIC_REPLAN`뿐. **D0 생존만으로 "봉인" 표현 금지** — D0 → 생존 시 **D1 자동** → D2a. Class B는 별도 track(발사 전 radial recovery·전개창 변위 제약·terminal-ring reference·feedback residual·full-window ring occupancy).
- **불변**: `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · **1H 계속 보류** · C-3 · C-4 · D0 예산/판정기/판정.

### 2026-07-25 (ccccc) — 🚨 Phase 1P step 6A rung 1.5: **rung 1은 geometric oracle이었음(불연속 0.0500 m) 확정** + 동역학 버전 구축 → **Class A 10건 중 gate-max δ에서 9건 null**, `BASE 3.2/0.50 C` 저항 라벨 철회, MAXCLR 2건은 진짜 저항 · **harness 버그 2건 자기신고**

- **채택**: 외부검토 총판정(rung 1 양성 신호 인정, 단 oracle/dynamic 판별 선결). 산출 = `shepherd/scripts/c1_phase1p_6a_dynamic.py` + `results/c1_corridor/c1_phase1p_6a_dynamic.json` + `URP/c1_phase1p_step6a_rung15_2026-07-25.md`.
- **🚫 철회 4건**: ① "기하가 장애물이 아니다" ② "스칼라 하나로 7개 해결"(실제로는 **scenario-specific 12개 수동값**) ③ "저항 5건은 inward로 안 닫힌다"(격자·oracle artifact) ④ rung 1의 지위 → **`RADIAL_INWARD_GEOMETRIC_ORACLE`로 격하**. **승인 라벨 = `RADIAL_INWARD_FREEDOM_PROMISING_UNDER_DIAGNOSTIC_REPLAN`.**
- **case A 확정(측정)**: `radial_inward`가 **발사시점 위치까지** δ만큼 옮기고 진입 전이를 시뮬레이션하지 않음 → 측정된 발사시점 위치 불연속 **정확히 0.0500 m(=δ)**.
- **plant 규약을 가정 않고 검증**: 로그 속도로 로그 위치를 재현하는 규약은 **semi-implicit `p+v[t+1]·dt` (오차 0.000000 m)**, explicit 0.075 m, trapezoid 0.0375 m.
- **🚨 harness 버그 2건 자기신고** — 지시하신 δ=0 재적분 잔차 검사가 **2.325 m 위치 · 10 m/s 속도**를 뱉어 잡아냄: ① 목표를 **상수 반경 ρ0−δ**로 잡아 **δ=0이 항등이 아니라 radial hold**였음(2.325 m는 적분 불일치가 아니라 그 hold의 효과) → 목표를 **nominal 경로를 δ만큼 안으로 민 것**으로 교체해 δ=0에서 추종오차 항등적 0 ② **KP=400 @ dt=0.05 → KP·dt²=1.0** 안정 한계에서 A_MAX 클립과 채터링 → **KP=100·KD=20**(ω≈10, ω·dt=0.5). **수정 후 δ=0 잔차 0.00000 m.** 이 검사가 없었으면 오염 수치를 그대로 보고했을 것.
- **admissibility 12/12 통과**: `POSITION_CONTINUITY_PASS`·`VELOCITY_CONTINUITY_PASS`·`ACCELERATION_BOUND_PASS`·`INTER_LIMITER_COLLISION_FREE`·`DEFENDER_TRAJECTORY_ADMISSIBLE` 전부 Y. 사용 최대 가속도 **7.0–30.0 m/s²**(A_MAX 30) — 절반은 10 이하로 여유, 포화는 4건.
- **공유 δ 규칙(witness 이름·escape 결과 미사용)**: `δ_raw = clip(lane_clearance_at_fire − LANE_RESERVE, 0, DELTA_MAX)` → **격자에서 gate-valid 최대값으로 스냅**. `LANE_RESERVE = 0.010 m` **lane 전용**(1L/1M의 10 mm는 attacker–limiter 상대거리용이라 재사용 금지). **스냅 필요성도 자기신고** — 규칙값이 연속이라 격자 미평가 δ를 고를 수 있고 초판에서 **음의 lane 여유 3건**이 통과했음.
- **미세 sweep(0.005 m) 결과**: **Class A nulls — 공유 규칙 6/10, gate-max δ 9/10**. **knife-edge 0건**(시험 δ에서 lane 여유 전부 +0.019 ~ +0.101 m). **`BASE 3.2/0.50 C`는 저항 사례가 아니었음** — 동역학 gate-valid δ_max **0.120 m**에서 escape 0(rung 1의 "회랑 없음"은 0.05 m 격자 + oracle artifact). 공유 규칙(6/10) < gate-max(9/10)이므로 **`lane−10mm`가 과보수적**이며 축의 실패가 아님.
- **실패 클래스 분리 확인**: **A_NEAR_TERMINAL_RAZOR_GAP 10건**(δ 5–15 cm 유효) / **B_GROSS_RADIAL_DISPLACEMENT 2건**(MAXCLR — **δ=0.200에서도 escape 8건**, 공격자↔limiter 3.7–4.1 m라 rung 0의 "2.65 m 링·0.15 m 회랑" 설명 미적용). Class B는 inward 축의 무효가 아니라 **작은 terminal 변위로 gross displacement exploit을 고칠 수 없다**는 것.
- **🚫 아직 아님**: **봉인 아님** — 0건은 `NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET`이고 라벨은 **누적**(`SURVIVED_DIAGNOSTIC_REPLAN` → `SURVIVED_D0` → **D0 생존 시 사전등록 D1 자동 발동** → `SURVIVED_D0_AND_D1` → D2a). controller 존재성·adversarial sealing 미증명. δ는 전 limiter 동일 상수 명령이며 상태 피드백·비동기·시간가변 아님.
- **ledger**: C-13 전면 개정(PROVISIONAL 유지). 폐기표에 rung 1 관련 3건 추가.
- **다음**: ① controller semantics + δ 규칙 + gate reserve + artifact **봉인** ② Class A 9건에 **D0** ③ D0 생존자에 **사전등록 D1 자동 적용** ④ 남은 Class A 1건(RH 4.0/0.40, gate-max esc 2)과 Class B 2건에 **CEGIS**(초기 defender class = 상태기반 radial inward + 전개창 radial hold + lane reserve, fire timing 동결·cone steering/tangential 닫음) ⑤ 성공 controller 이후에만 ablation.
- **불변**: `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · **1H 계속 보류** · C-3 · C-4 · D0 예산/판정기/판정.

### 2026-07-25 (bbbbb) — ✅ Phase 1P step 6A rung 0·1: 기하 재측정 → **0.15 m 내향 회랑 발견** · 단일 스칼라 `RADIAL_INWARD(δ)`로 **7/12 witness에서 full gate 유효·검증 escape 0**(봉인 아님)

- **채택**: 외부검토 판정의 step 6 재구성(최소 자유도 선정 기각 → **존재성 프로브**). 넓은 oracle을 짓기 전에 **기하가 장애물인지**를 먼저 물었음. 산출 = `shepherd/scripts/c1_phase1p_6a_probe.py` + `results/c1_corridor/{c1_phase1p_6a_geometry.json, c1_phase1p_6a_radial_inward.json}` + `URP/c1_phase1p_step6a_probe_2026-07-25.md`.
- **🎯 rung 0 기하 진단**: 검증 escape에서 공격자의 **net 축까지 수직거리 0.00–0.59 m**(중앙값 ~0.12), 공격자↔최근접 limiter **2.600–2.653 m**. 링 반경 **2.650**, `r_kill` **2.600**, lane floor **2.500**. ⇒ **탈출 공격자는 net 축을 따라 날며 kill 경계를 몇 cm 차이로 스침**, 그리고 링 위치(2.650)와 허용 최소(2.500) 사이에 **0.15 m 내향 회랑**이 있는데 **방어자가 한 번도 쓰지 않음**. 시스템 전체가 10–15 cm 밴드 안에서 동작.
- **rung 1 `RADIAL_INWARD(δ)`**: 링 자체 프레임에서 모든 limiter를 전개창 동안 δ만큼 내향. δ ∈ {0, .05, .10, .15, .20}. δ마다 **full gate 강제**(E_cap band 0.0526 · E_lane) 후 step 5와 **동일 예산**으로 공격자 재최적화, 집계 escape 전부 연속 판정기 재판정.
- **결과**: **δ=0에서 escape 12/12** → **최대 허용 δ에서 검증 escape 0이 7/12**(RH 2.8/0.15 · RH 3.2/0.25 · RH 5.0/0.55 · BASE 2.8/0.30 C · BASE 3.2/0.70 P · BASE 4.0/0.70 P · BASE 5.0/1.00 P). **E_cap이 어디서도 깨지지 않았고** 오히려 개선되기도 함(BASE 4.0/0.70 P v_soft 0.9535 → 1.0000).
- **저항 5건**: `BASE 3.2/0.50 C`(**허용 δ = 0** — lane 여유가 이미 +0.0352이고 δ=0.05에서 위반, 회랑 없음) · `RH 4.0/0.40 f=7`(δ=0.10에서 lane 정확히 +0.0000, 5건 잔존) · `BASE 4.0/0.70 C`(1건) · **`MAXCLR` 2건은 δ 0.20까지 escape 8건 불변**(max-clearance exploit 링이 바깥으로 밀려 공격자 perp 최대 2.06 m·최근접 limiter 3.7–4.1 m이라 0.20 m로는 사거리 밖).
- **🚫 봉인 아님**: 0건은 `NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET`. 비준 규칙대로 **falsifier가 못 찾은 것은 아무것도 증명하지 않음** — D0 예산과 독립 seed 필요. 또한 controller가 아니라 **균일 개방루프 스칼라 변위**이고, 작동 δ에서 **lane 여유가 +0.0000 ~ +0.0500 m뿐**이라 실제 tracking 오차가 이를 넘으면 전부 무효.
- **왜 step 4·5가 놓쳤나**: 시험한 5개입이 **전부 이 축을 비껴감** — `RING_FREEZE`/`RADIAL_HOLD`는 링을 제자리에 두거나 반경을 **유지**했지 **안으로 넣지 않았고**, `TANGENTIAL_EQUAL`은 항등, `CONE_STEER_*`는 지향만, `FIRE_SHIFT`는 시점만(+E_cap 12/12 파괴). 판정문의 **"시험한 arm들은 relaxation이 아니라 제한된 heuristic intervention"** 지적대로 **개입 공간의 한 축이 통째로 비어 있었음**.
- **ledger**: **C-13 신설(PROVISIONAL)** — 규칙 2에 따라 D0 확인 전까지 승격 없음.
- **다음**: ① 7건 null을 **D0 예산 + 독립 seed**로 확인(봉인 주장의 전제) ② 저항 5건에 **CEGIS(6B)** ③ MAXCLR 2건은 링 외향 기하가 원인인지 분리 ④ 성공 후에만 **6C ablation**(균일 δ → limiter별 → 시간가변 → shared policy).
- **불변**: 교집합 제약 계속 보류(`JOINT_FREEDOM_NECESSITY_UNRESOLVED` — δ 하나로 7건이 닫힌 것은 단일 축으로도 상당 부분이 닫힐 수 있음을 시사하나 5건이 남았고 D0 확인 전이므로 어느 쪽으로도 판정 안 함) · **1H 계속 보류** · C-3 · C-4 · D0 예산/판정기/판정.

### 2026-07-25 (aaaaa) — 🚨 Phase 1P step 5.5: full-gate(E_cap∧E_lane) 재평가 → **FIRE_SHIFT 12/12 E_cap 실패, step 5 미발견 3건 전부 무효(계상 0)** · 교집합 "틀 반박" 해석 철회

- **채택**: 외부검토 총판정(step 5 성공, 해석 1건 축소 + E_cap 선결). 산출 = `shepherd/scripts/c1_phase1p_fullgate.py` + `results/c1_corridor/{c1_phase1p_fullgate.json, c1_phase1p_null_probe.json}` + `URP/c1_phase1p_step55_fullgate_2026-07-25.md`.
- **🚫 철회**: "**교집합 제약이라는 틀 자체가 데이터에 의해 반박됐다**". `MODE_SUBSTITUTION`이 정보를 가지려면 개입이 **원래 모드를 재최적화 후에도 제거**해야 하는데, 대부분의 arm에서 원래 모드가 그대로 재발견 ⇒ **substitution이 일어날 조건에 도달하지 못함**. 교집합 가설은 **지지도 반박도 되지 않음**.
- **비준 라벨**: `TESTED_STATIC_INTERVENTIONS_INSUFFICIENT_UNDER_CONSTRAINED_REPLAN` · `MODE_SUBSTITUTION_NOT_OBSERVED` · `TESTED_INTERVENTIONS_FAILED_TO_CLOSE_SOURCE_MODES` · `JOINT_FREEDOM_NECESSITY_UNRESOLVED` · `ARTIFACT_BLOCK_RATE_NOT_CONTROLLER_EVIDENCE` · `FIRE_TIMING_SIGNAL_PROVISIONAL`. **보류**: `INTERSECTION_CONSTRAINT_REFUTED` · `CURRENT_CONTROL_FREEDOMS_IMPOSSIBLE`. step 4 차단률의 지위 = **`ARTIFACT_LEVEL_LOCAL_SENSITIVITY`**(폐기 아님 — 개입 후보 생성 스크린이고 controller 적합성의 첫 시험은 step 5).
- **재구성 정직성**: 환경은 nominal에 대해서만 `v_soft`/`p_feas`를 보고하므로 반사실 값은 재계산 필요. 정적 발사시점 스냅샷 n=2000·seed 0 재계산 시 환경 대비 **max |Δv_soft| = 0.05263**(union n_total 2504, max |Δp_feas| 0.00200) ⇒ **E_cap band 0.0526** 설정, 밴드 내 판정은 **`E_CAP_UNRESOLVED`**. 밴드는 arm이 아니라 **하네스의 성질**(NONE↔환경 대조)이라 사전 고정이 사후 선택이 아님.
- **🎯 결과**: `NONE` REPLAN_FALSIFIED 12 | `RING_FREEZE` FALSIFIED 11 + **NOT_REDISCOVERED 1** | `CONE_STEER_COVERAGE` FALSIFIED 12 | `RING_FREEZE_PLUS_COVERAGE` FALSIFIED 12 | **`FIRE_SHIFT_PLUS1` `INVALID_INTERVENTION_ECAP_FAIL` 12/12**. ring·cone·결합 arm은 **E_cap PASS 12/12 · E_lane PASS**(lane 최소 여유 +0.0352 / +0.0079 m) ⇒ 이들의 replan 실패는 **진짜 controller 적합성 실패**이며 방어자 파손 탓이 아님 — step 5 결론이 단단해짐.
- **FIRE_SHIFT 실패 경로 2종**: **`fire_step_valid=False` 11/12**(환경 자신의 `teacher_fire`가 t+1에서 발사하지 않음 — 방어자가 애초에 그 시점에 쏘기를 선택 안 함) · **`p_feas=0` 5/12** · 나머지 `v_soft` **0.286~0.667**(NONE 0.954~1.000). ⇒ **step 5 미발견 3건 전부 무효, 계상 가능 0건.** 세 원인(잔여 시간 감소 / limiter 기하 안정화 / **E_cap·lane 소멸**) 중 **세 번째가 실측**됨.
- **⚠️ 함정 기록**: `p_feas=0`이면 `VShotResult`가 `boxed_in`으로 **`v_shot_soft=1.0`을 반환**. `v_soft=1.0`만 읽으면 완벽 포획으로 보이나 실제로는 **limiter-block 신호이지 net shot이 아님**. E_cap 검사를 `p_feas ≤ 0 → FAIL`로 짜지 않았다면 **5건이 거짓 양성**으로 올라갔을 것.
- **유일한 계상 가능 null 재확인**: `RING_FREEZE` × `BASE 3.2/0.50 C`. E_cap 통과로 예산 집행이 정당화되어 판정문 8항대로 **독립 base seed 6종(211·307·401·503·601·709, 기존 7·11·23·101과 disjoint)** 재실행 → **전 seed 탐색 후보 0 · 검증 escape 0**, 총 **10개 독립 seed에서 null 재현**. **그래도 봉인 아님**(진단 예산, 12 중 1 witness). full gate 통과 방어자가 10 독립 seed에서 후보를 하나도 안 낸 **유일 사례**이므로 step 6A 단서로 보존.
- **step 6 재구성(최소 자유도 즉시 선정 기각)**: **6A 넓은 defender oracle**(limiter별 독립 radial·tangential · 시간 가변 · fire step 선택 · cone steering · feedback/oracle access, 배치 가능 controller보다 강해도 됨, `E_cap ∧ E_lane ∧ no penetration` 전면 강제) → **6B CEGIS**(verified escape set으로 defender 최적화 → 봉인 → constrained replan → 새 escape 추가 → 반복) → **6C 성공 후에만 ablation**. **불가능성은 relaxation(superset)이 필요** — 시험한 5 arm은 relaxation이 아니라 제한된 heuristic 개입이므로 불가능성 증명에 쓸 수 없음. 성립하는 것은 "현재 정의한 고정 `RING_FREEZE_PLUS_COVERAGE` 개입이 불충분했다" 뿐.
- **ledger**: C-11 Status 해석 축소, **C-12 신설**(CONFIRMED). 폐기표 2건 추가.
- **불변**: C-3·C-4·D0 예산/판정기/판정. **1H 계속 보류.**

### 2026-07-25 (zzzz) — 🚨 Phase 1P step 5: basin-level constrained replan → **MODE_SUBSTITUTION 0건** · **두 축 동시 개입(step 4 51/74 차단)이 재최적화 앞에서 12/12 전부 불변** ⇒ artifact-level 차단은 controller 적합성의 증거가 아님

- **채택**: 외부검토 판정의 step 5. 산출 = `shepherd/scripts/c1_phase1p_replan.py` + `results/c1_corridor/c1_phase1p_replan.json` + `URP/c1_phase1p_step5_replan_2026-07-25.md`. 결과 범주 3종을 **실행 전 명명**(`REDISCOVERED` / `NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET` / `MODE_SUBSTITUTION`).
- **검증**: CEM 점수는 제안일 뿐 증거가 아니므로(proposal–verification separation) 집계 escape 전부를 **개입된 방어자에 대해 연속 판정기로 재판정**. witness-arm-mode당 **최고점 4 + 최긴박 4** 사전등록. 빈도 주장 금지 유지, 점유만 보고.
- **🚨 seed 설계 오류 자기신고**: 초판이 seed에 **arm 이름을 포함** → arm마다 다른 공격자 스트림 → arm↔NONE 차이가 **개입 효과와 탐색 잡음의 혼합**이 되어 허위 `MODE_WIDENED` 2건 산출. **step 1에서 만든 paired/diversity 구분을 엉뚱한 축에 적용한 재발.** 스트림이 witness에만 의존하도록(**arm 간 CRN**) 수정 후 전면 재실행. 아래 수치는 전부 수정본.
- **결과(재발견/미발견 · KILL/CONE_LAT/CONE_AXIAL 점유 witness 수)**: `NONE` 12/0 · 12/12/0 | `RING_FREEZE` 11/**1** · 11/10/0 | `CONE_STEER_COVERAGE` 12/0 · 12/12/0 | `RING_FREEZE_PLUS_COVERAGE` 12/0 · 12/12/0 | `FIRE_SHIFT_PLUS1` 9/**3** · 9/8/0.
- **NONE 대비 분류**: RING_FREEZE = 전모드폐쇄 1·축소 1·**불변 10** / CONE_STEER_COVERAGE = **불변 12** / RING_FREEZE_PLUS_COVERAGE = **불변 12** / FIRE_SHIFT_PLUS1 = 전모드폐쇄 3·축소 1·불변 8.
- **🎯 `MODE_SUBSTITUTION` = 0건**: 어느 arm에서도 미관측. 개입이 공격자를 한 모드에서 다른 모드로 **밀어내지 않고 그냥 실패**하며 **같은 모드가 그대로 재점유**됨. ⇒ **교집합 제약은 지지받지 못함** — "아직 미증명"이 아니라 이 데이터로는 **틀 자체가 지지되지 않음**.
- **🎯 핵심 — artifact-level 차단은 replan을 견디지 못함**: `RING_FREEZE` step 4 37/74 차단 → step 5 11/12 재발견 / `CONE_STEER_COVERAGE` 20/74 → **12/12 재발견·불변 12** / **`RING_FREEZE_PLUS_COVERAGE` 51/74 차단 → 12/12 재발견·불변 12**. **두 축 동시 개입이 단일 축보다 더 많이 차단하고도 replan 하에서 아무것도 사지 못함.** ⇒ **step 4식 차단 수치는 controller 적합성의 증거로 쓸 수 없음.** 판정문의 경고가 정확했고, 실제로는 이웃이 아니라 같은 모드가 그대로 복귀.
- **🚫 step 4 해석 부분 철회**: `FIRE_SHIFT_PLUS1`을 "방어가 아니라 artifact의 발사시점 취약성 측정이며 재계획하는 공격자는 그대로 다시 푼다"고 썼으나 **부분적으로 틀림** — 9/12만 재발견, **3/12 미발견**, 모드 점유 9/8로 유일하게 감소하여 어느 arm보다 replan 하 효과가 큼. 다만 50 ms 지연은 controller 자유도가 아니고 3건의 기하 임계 미규명이며 `NOT_REDISCOVERED`는 봉인이 아니므로 **단서로만** 기록, 설계로 승격 안 함.
- **step 6 함의(솔직 정리)**: 시험한 어떤 단일축·이중축 개입도 이 크기에서는 replan 하에 escape를 닫지 못함. 갈래 셋 — ① **더 큰 개입**(그러나 step 4 실측 lane 여유가 nominal **3.5 cm**, 0.34° 조향 후 **8 mm**, 오라클 3.7° 조향은 74/74 E_lane 위반이라 기하학적 여지 거의 없음) ② **다른 종류의 자유도**(현재 후보 없음) ③ **불가능성 계열 결과**. **교집합 제약 계속 보류, 최소 자유도 조합 계속 동결 금지.**
- **🚫 주장 안 함**: `NOT_REDISCOVERED`는 **봉인 아님**(D0보다 작은 진단 예산의 null, D0로 올리면 뒤집힐 수 있음) · 시험한 5 arm이 개입 공간 전부라는 것 · **다른 개입이 substitution을 유발할 가능성 미배제** · 개입된 방어자의 E_cap(미검사, E_lane만 검사) · 빈도.
- **ledger**: **C-11 신설**(CONFIRMED). 폐기표에 "교집합 제약 확정" 최종 판정 갱신 + "FIRE_SHIFT는 취약성 측정" 부분 철회 추가.
- **불변**: C-3·C-4·D0 예산/판정기/판정.

### 2026-07-25 (yyyy) — ✅ Phase 1P step 4: artifact-level 개입 → **두 개입이 모드를 가로질러 차단** ⇒ 교집합 제약 보류 판정이 실측으로 지지됨 + **자기 개입 정의 결함 4건 자기신고**

- **채택**: 외부검토 "step 4·5 선행" 판정. 산출 = `shepherd/scripts/c1_phase1p_intervention.py` + `results/c1_corridor/c1_phase1p_intervention.json` + `URP/c1_phase1p_step4_intervention_2026-07-25.md`. 대표 artifact = step 3.5 **구간 인증 74건**(각각 nominal에서 `CERTIFIED_COLLISION_FREE`이므로 뒤집힘을 기준선 불안으로 돌릴 수 없음). 차단 술어 = `NOT(연속 kill_margin>0 AND cone_exit_margin>0)`, kill은 **연속 판정기**로 재계산(step 3.5에서 argmin 23% interior 측정). **뒤집힌 항을 기록**(step 5가 필요).
- **🚨 자기 개입 정의 결함 4건**: ① **좌표계 버그** — 링 평면을 (x,y)로 하드코딩했으나 실제는 **(y,z)**(발사시점 x=8.000 고정, (y,z) 반경 2.650·std 0.00000 vs (x,y) std 0.704). 단서는 2.65 m 링에서 **변위 중앙값 14 m**. SVD로 데이터에서 프레임 복원하도록 수정. ② 수정 후 `TANGENTIAL_EQUAL` 변위 **정확히 0.0000 m·방위 0.00°** = **항등**(링이 이미 90° 등간격) → 0/74는 정의적 0. ③ `CONE_STEER_NOM` 조향 **전 건 0.000°** = **항등**(net 축이 이미 영가속 예측점 지향) → `MEASURED_NO_OP` 분류, 구현 가능한 `CONE_STEER_COVERAGE` 신설(현재 미커버 reachable 종점 중심으로 조향, 공격자 실제 계획 미사용). ④ **`RADIAL_HOLD` ≡ `RING_FREEZE`** — 전개창 중 limiter 운동이 **순수 반경 방향**이라 결과 완전 동일(37/74·23/42·14/32·변위 중앙값 0.0396 m).
- **하네스 점검**: 항등 `NONE` **0/74** 통과 · 음성대조 `AXIAL_TIGHTEN` **0/74** 통과(step 2 `CONE_AXIAL` 미점유와 일관).
- **🎯 핵심 — 모드 교차**: `RING_FREEZE`(링 축)가 자기 모드 KILL 23/42 + **반대 모드 `CONE_LATERAL` 14/32를 전부 kill 항으로** 차단. `CONE_STEER_COVERAGE`(지향 축)가 자기 모드 13/32 + **반대 모드 `KILL` 7/42를 전부 cone 항으로** 차단. ⇒ **두 모드는 controller 축으로 깨끗이 분리되지 않으며, "링만 고치면 cone-lateral을 못 막는다"는 거짓.** 판정문이 교집합 제약을 보류한 근거가 실측 확인됨.
- **그러나 충분하지 않음**: RING_FREEZE 37/74 · CONE_STEER_COVERAGE 20/74 · **두 개입 동시 적용 51/74**(합집합 추론이 아니라 한 방어자에 동시 적용해 측정) — **23건이 둘 다 견딤**.
- **개입 크기(형용사 아닌 측정치)**: `RING_FREEZE` limiter 변위 중앙값 **0.0396 m**·최대 2.3700 m / `CONE_STEER_COVERAGE` 조향 중앙값 **0.34°**. **lane 여유가 거의 없음** — nominal **+0.0352 m**, cone steering 0.34° 후 **+0.0079 m**.
- **🚫 오라클 개입은 적법하지 않음**: `CONE_STEER_ORACLE` 72/74 차단이나 **74/74 전부 E_lane 위반**(lane 여유 **−0.9206 m**, 조향 3.70°) — 축을 3.7° 돌리면 발사선이 자기 limiter 링을 관통. "정답을 알려준 반칙"일 뿐 아니라 **기하학적으로 불가능**. `adm-only 0/0`으로 기록, 구현 가능 결과로 계수 안 함.
- **`FIRE_SHIFT` 해석 제한**: PLUS1 71/74·MINUS1 65/74(단 MINUS1은 12건 E_lane 위반)로 최고치이나, 이는 **방어가 아니라 artifact의 발사시점 취약성 측정**에 가까움 — 공격 계획이 특정 발사시점에 맞춰져 있어 시점 이동이 계획을 무효화. 재계획하는 공격자는 그대로 다시 풂. step 5가 판정.
- **Scope**: E_lane **검사함**(deploy window 전 구간 perp ≥ 2.50 m, 위반 건 제외) / E_cap **미검사**(finisher chain 의존, step 6 게이트) / 공격자 계획 **바이트 단위 동결** / reset 1100 · 12 witness · 74 artifact · `FIXED_CONDITION`.
- **ledger**: **C-10 신설**(CONFIRMED, 개입별 artifact 차단 사실). 폐기표에 "링 평면 = (x,y) 가정" 추가. "교집합 제약 확정" 항목에 step 4 반증 방향 증거 주석.
- **다음 step 5**: 같은 개입을 **고정**하고 attacker 재최적화 — escape 재발견(개입 불충분) / 미발견(`NOT_REDISCOVERED_UNDER_CONSTRAINED_REPLAN_BUDGET`) / **mode substitution**(RING_FREEZE 하에서 CONE_LATERAL로, CONE_STEER 하에서 KILL로 옮겨가는지)이 교집합 제약을 말할 **유일한** 근거. step 6 자유도 조합은 계속 **동결 금지**.

### 2026-07-25 (xxxx) — ✅ Phase 1P step 3.5: verifier 정리(판정 5건 전량 수용) → **불변식 위반 = fp 잡음 확정 · 모드 라벨 변경 0 · 74건 구간 인증** + **자기 가설 1건 반증(argmin 23% interior)** · 철회 3건

- **채택**: 외부검토 "step 3 수정승인, step 4·5 선행" 판정. step 3.5로 verifier만 정리하고 새 탐색·판정 없음. 산출 = `shepherd/scripts/c1_phase1p_verifier_audit.py` + `results/c1_corridor/c1_phase1p_verifier_audit.json` + `URP/c1_phase1p_step35_verifier_audit_2026-07-25.md`.
- **🚫 철회 3건**: ① **"step 6 교집합 제약 확정"** → step 4·5 이후로 보류. 두 모드 공존이 "하나의 개입으로 둘을 동시에 못 없앤다"를 함의하지 않음(ring stabilization이 cone-lateral까지 간접 제거할 수 있음). ② **"표본 margin이 사실상 정확 / 최소점이 격자점에 놓인다"** → A4에서 반증. ③ **"1H 보류 해제"** → **`1H 재승격 후보`로 격하**(`CONE_LATERAL` = net cone lateral exit ≠ limiter ring transit angular gap; 원인이 limiter angular gap·finisher pointing·fire timing·attacker lateral accel·ring translation·net cone 협소함 중 무엇인지 미구분).
- **허용 문면 확정**: "현재 controller와 fixed condition에서 KILL 및 CONE_LATERAL 두 연속시간 escape mechanism이 모두 실재한다. 새 controller는 두 mechanism을 함께 고려해야 한다."
- **A1 불변식 원인 규명** — 크기만으로는 원인을 못 가리므로(진짜 missed root가 작은 수 뒤에 숨을 수 있음) 세 원인을 **실험으로** 분리: ① 두 코드 경로 동일시점 거리 대조 → 위치 최대차 **3.553e-15 m**·거리 2.665e-15 m ⇒ **"서로 다른 trajectory" 배제** ② 모든 표본 시점을 후보에 **강제 주입**(적합 다항식 아닌 실제 callable로 평가) → `shipped − forced` 최대 **4.441e-16 m**, 허용오차 초과 **0** ⇒ **"후보 누락" 배제** ③ 잔여 음수 26/209, 최악 **−1.332e-15 m**(margin 크기 1e-2~1e0에 대한 double eps 스케일). 사전등록 `CERTIFIED_TOLERANCE_M=1e-12` **초과 0건** ⇒ **fp 잡음 확정, verifier mismatch 아님**. `exact_min_clearance_forced`를 코드에 상주시켜 `continuous ≤ sampled`를 **구조적으로** 보장 + argmin 시각 반환.
- **A2 모드 재배정 — 판정문 문자 그대로는 구현하지 않고 사유 명시**: 판정문의 `argmin(kill, lateral, axial)`은 이 코드베이스 부호 규약에서 틀림. `axial`은 밴드 **바깥** 부호거리라 종점이 밴드 안이면(현 기하 항상) 큰 음수 → 3-way argmin은 **209건 전부를 CONE_AXIAL로 라벨**(실제 첫 실행에서 재현). escape 조건이 `min(kill, max(lat,axi))>0`이므로 모드 비교는 `kill` vs `cone:=max(lat,axi)`, cone 내부는 max 달성 쪽. tie band 1e-9를 두 비교 모두에 적용. **결과: 라벨 변경 0/209 · MIXED_OR_BINDING_AMBIGUOUS 0 · KILL 113 / CONE_LATERAL 96(witness 12/12)** ⇒ 배정이 연속 판정에서 안정.
- **A3 구간 인증**: 사전등록 합집합(witness-mode 최긴박 24 · margin<0.5mm 31 · sampled−continuous 음수 39 · 경계밴드 0) = **74건 → `CERTIFIED_COLLISION_FREE` 74/74**, `lb ≤ numeric` 위반 0, 최대 세분화 깊이 0. **문제였던 10.8 μm artifact 인증됨**(RH 5.0/0.55 f=10 KILL, `cf24dc62e5300675`, 수치 `+1.0813650600e-05` → **인증 하한 `+1.0813479578e-05 m`**, 유리수 Bernstein `c1_phase1n_rational_bernstein_v1`).
- **🚨 A4 argmin — 제 step 3 가설 반증**: "sampled·exact가 7자리 일치하니 최소점이 격자점"은 따라 나오지 않음(평평한 interior minimum도 같은 일치 산출). argmin **시각**을 직접 측정 → 격자 노드 위 **161/209(77.0%)**, **interior 48/209(23.0%)**. attacker 경계 거리 중앙값 0.0 s·최대 4.963e-2 s, Hermite 노드 거리 중앙값 0.0 s·최대 2.440e-2 s, argmin이 강제주입 표본시점인 경우 14건. ⇒ **"격자점에 놓인다"는 일반 명제 불성립**, "breakpoint에 집중"은 부분적으로만(77%) 지지.
- **A5 층화 표집 회계**: nominal 12×2×(6+6)=**288** → selected **209**, shortfall 79가 **9개 witness-mode에서 전부 pool<12로 `select()`가 pool 크기에서 잘린** 경우(BASE 2.8/0.30 C KILL pool 2, CONE_LATERAL pool 1 등). **누락·중복 0.**
- **ledger**: C-8 Claim을 허용 문면으로 교체 + `Does not establish`에 "서로 다른 자유도가 동시에 필요하다는 것" 추가 + 강도를 `INTERVAL_CERTIFIED` 74건으로 갱신 + 1H 행 신설. **C-9 신설**(판정기 수치 무결성, CONFIRMED). 폐기표에 3건 추가.
- **불변**: C-3·C-4·D0 예산/판정기/판정.
- **다음**: **step 4 artifact-level intervention** — basin representative에 최소 개입(ring terminal hold · tangential redistribution · cone steering · fire timing shift · axial correction) 적용, 주장 가능한 것은 "해당 개입이 이 artifact를 차단했다"까지. **step 5** 같은 개입 고정 후 attacker 재최적화 — **mode substitution**(KILL 차단 시 CONE_LATERAL로 이전하는지)이 핵심 측정치이며 그 전에는 교집합 제약을 말할 수 없음. step 6 후보 목록은 작성하되 **최소 자유도 조합 동결 금지.**

### 2026-07-25 (wwww) — ✅ Phase 1P step 3: 층화 연속-clearance 감사 → **두 모드 모두 생존**(209건 감사, collision 0 · unresolved 0) ⇒ step 6 교집합 제약 확정 · 1H 보류 해제 유지

- **채택**: 1O §8 항목 3 (cluster-stratified continuous-clearance audit). 산출 = `shepherd/scripts/c1_phase1p_stratified.py` + `results/c1_corridor/c1_phase1p_stratified.json` + `URP/c1_phase1p_step3_stratified_2026-07-25.md`.
- **동기**: step 2의 모드 분할은 **표본 margin** 위에 있었음 — `kill_margin`은 공격자 구간당 24 substep의 min이지 연속 시간의 min이 아니며, 모든 표본을 통과하고도 표본 **사이에서** `r_kill` 안으로 들어갈 수 있음.
- **노출 비대칭을 명시**: `KILL`은 binding 항이 **표본으로만 얻는 바로 그 양** = **최대 노출**(연속 판정이 모드를 지운다면 여기부터) / `CONE_LATERAL`은 binding이 **종점 속성이라 이미 정확**하고 `kill_margin > cone_exit_margin > 0`이라 여유 있음 = 낮은 노출, 단 **가정하지 않고 측정**.
- **층화 표집 사전등록**: witness별·모드별 **최긴박 6(적대적) + 분위 spread 6(대표성)**. 최긴박 우선은 의도 — falsifier이므로 표본은 **실패를 찾을 확률을 최대화**하도록 고르며, spread 팔은 "칼날만 봤다"는 반론 차단용. **결과가 무엇을 뜻할지도 미리 기재**(둘 다 생존 / KILL 붕괴 → step 6 쉬워짐 / CONE_LATERAL 붕괴 → **1H 보류 해제 철회**).
- **결과**: KILL 113건 감사 → **free 113 · collision 0 · unresolved 0**, 생존 witness **12/12**(예산 초과 11/12). CONE_LATERAL 96건 → **free 96 · collision 0 · unresolved 0**, **12/12**(예산 초과 9/12). CONE_AXIAL 감사 대상 없음. ⇒ **둘 다 생존, 1H 보류 해제 유지.**
- **부수 발견 — 표본 margin이 binding artifact에서 사실상 정확**: `sampled − exact` 중앙값 **0.0000000 m**, p95 0.000187 m, 관측 최대 0.000327 m, 음수(정확값이 더 좋음) 39건. 최긴박 KILL artifact는 소수점 7자리까지 일치(`+0.0000108 → +0.0000108`) — **최소거리가 표본 사이가 아니라 격자점 위에서 발생**(limiter Hermite 노드 dt=0.05 · 공격자 구간 경계 τ/K=0.1 s가 최소점을 끌어당김). 최긴박 artifact(1e-5 m)가 낙관 상한(3.3e-4 m)보다 작은 margin으로도 뒤집히지 않은 이유.
- **분할 작동 확인**: CONE_LATERAL artifact는 `sampled 0.0000178 → exact_kill 0.0102491`처럼 크게 벌어짐 — 그 모드의 binding이 `cone_exit`이지 `kill`이 아니기 때문. 설계대로 동작.
- **🚫 주장 안 함**: 커버리지 **209/43,777 = 0.48%** — 감사 집합의 collision 0이 **풀 전체의 0을 뜻하지 않음**(다만 118/209가 최긴박 팔로 적대적 표집이었고 칼날은 감사됨) · 강도는 `NUMERICALLY_RESOLVED`이지 **구간 인증 아님** · 낙관 0.33 mm는 **관측 최대이지 증명된 상계 아님** · reset 1100 단일 · 15 중 12 witness.
- **판정**: **step 6의 교집합 제약 확정** — 두 모드가 표본이 아니라 연속 시간에서 실재하므로 링 운동만 또는 지향만 고치는 제어기는 봉인 불가. C-3·C-4·D0 예산/판정기/판정 전부 불변, 이 감사는 D0 판정을 발행하지 않음. ledger C-8에 evidence ② 추가 및 status 갱신.
- **다음 판단점**: step 4·5(artifact-level intervention, basin-level constrained replan)를 거칠지, 이 확정을 들고 바로 step 6(최소 자유도 선정)으로 갈지. 4·5는 "어느 자유도가 두 모드를 **동시에** 닫는가"를 좁히는 작업이므로 step 6 후보 목록이 넓으면 선행이 유리.

### 2026-07-25 (vvvv) — ✅ Phase 1P step 2: 탈출 MODE 정의적 분할 → **모드는 2개(KILL·CONE_LATERAL), CONE_AXIAL 0건** ⇒ 한 모드만 닫는 제어기는 봉인 불가 · **1H 보류 해제 조건 충족**

- **채택**: 1O §8 항목 2 (`D0-MODE-DIVERSITY` clustering). 산출 = `shepherd/scripts/c1_phase1p_modes.py`(+`--robustness`) + `results/c1_corridor/{c1_phase1p_modes.json, c1_phase1p_modes_robustness.json}` + `URP/c1_phase1p_step2_modes_2026-07-25.md`.
- **입력 규율**: 소비 artifact 전부 `derive_seed(mode='diversity')` 산출. step 1이 witness-blind 탐색의 정책충돌 1~28·warm충돌 14~36(0인 적 없음)을 확인했으므로, blind artifact로 clustering하면 **시스템 모드 구조가 아니라 공유 warm-start pool 구조**를 세게 됨.
- **분할은 정의적(fitting 아님)**: k·거리척도·적합중심 **없음** = 더 보기 좋은 답으로 돌릴 자유 파라미터 없음. escape는 `kill_margin>0` ∧ `cone_exit_margin>0`이므로 **binding 항(min)**이 "무엇이 거의 잡았는가"를 지목하고, `cone_exit_margin`은 이미 `lateral`(원뿔 벽)·`axial`(사거리 밴드)의 max. ⇒ 상호배타·전수적 3모드: **KILL**(limiter 근접 = 링 운동) / **CONE_LATERAL**(원뿔 벽 = 방위·지향) / **CONE_AXIAL**(밴드 이탈 = 사거리·발사시점). 이 분할을 고른 이유는 **step 6이 골라야 할 controller 자유도와 1:1 대응**하기 때문 — 제어 벡터 k-means로는 "어느 손잡이"가 안 나옴.
- **결과(존재이지 빈도 아님)**: `KILL` **OBSERVED 12/12**(최긴박 +0.00001 m, RH 5.0/0.55) · `CONE_LATERAL` **OBSERVED 12/12**(+0.00002 m, BASE 3.2/0.50 C) · `CONE_AXIAL` **NOT_OBSERVED 0/12**. escape 총 43,777건.
- **허상 가능성 2경로 모두 확인(`--robustness`)**: (a) 라벨이 잡음으로 정해졌는지 → `|km−cm|` 중앙값 **70.1 mm**(p1 0.93 mm, p5 4.6 mm), gap<0.1 mm는 **0.12%** ⇒ 실제 여유 차이로 결정됨. (b) 최긴박 sub-mm artifact에 점유가 얹혔는지 → 10 mm 가산 기하오차 예산 초과분만으로 재집계 시 **KILL 11/12 · CONE_LATERAL 9/12 · CONE_AXIAL 0/12** ⇒ 두 모드 모두 견고.
- **🎯 step 6 제약 확정**: **한 모드만 닫는 제어기는 봉인할 수 없음.** 링 운동을 고치면 원뿔 벽으로, 지향을 고치면 limiter 회피로 갈아탐 → step 6은 **교집합**을 목표해야 함. 낙관(자유도 늘리면 닫힘)도 비관(구조적 불가능)도 아니고 **제약 하나를 확정**한 것.
- **1H(방위) 보류 해제**: 1O에 적어둔 조건 "mode analysis에서 방위/transit basin이 재출현하지 않으면 계속 보류" → `CONE_LATERAL` 12/12(예산 제한 9/12) 재출현으로 **충족**. 단 **해제 = step 6 자유도 후보 자격이지 착수가 아니며**, `c1_seal_law`의 `Δφ_max ≤ 4·arcsin(r_kill/2ρ)`는 여전히 **q=ρ·z=0 제한 정리**.
- **부수 사실**: 현재 기하에서 사거리 밴드 `[0, 29.847]`은 43,777건 중 **한 건도** binding이 아님 ⇒ 축방향 범위는 이 기하에서 **설계 지렛대가 아님**(다른 ρ·밴드에서 재확인 필요).
- **🚫 주장 안 함**: 모드 **빈도**(artifact 수 21357 vs 3은 탐색 지형이지 모드 우세가 아님 — 표에서 빈도를 읽으면 안 됨) · basin **개수** · 두 모드가 **전부**라는 것(측정된 것은 세 정의적 칸의 점유) · 다른 reset·기하로의 일반화.
- **Scope**: reset 1100 단일 · 진단 예산(bank 1 × restart 2 × base seed 4) · **15 중 12 witness**(EXPLOIT 3건 제외 — `cem_O` 제어기 재구성 비용이 측정 대상과 무관). **C-3·C-4·D0 예산/판정기/판정 전부 불변.**
- **ledger**: C-8 신설(CONFIRMED / `NUMERICALLY_VERIFIED` × `FIXED_CONDITION`).
- **다음**: 3 cluster-stratified continuous-clearance audit(KILL/CONE_LATERAL 층화) → 4 artifact-level intervention(각 모드 최긴박부터) → 5 basin-level constrained replan → 6 최소 자유도 선정·봉인·D0.

### 2026-07-25 (uuuu) — ✅ Phase 1P step 1: 탈상관 재탐색 → **C-6 승격(CONFIRMED), 단 원안보다 강한 형태로 재작성** — witness-blind unique 수는 다양성 척도가 아님 (D0 판정 불변)

- **채택**: 1M escalation registry에 사전등록된 `D0-MODE-DIVERSITY` 진단. 산출 = `shepherd/scripts/c1_phase1p_diversity.py`(+`--spread`) + `results/c1_corridor/{c1_phase1p_diversity.json, c1_phase1p_diversity_spread.json}` + `URP/c1_phase1p_step1_diversity_2026-07-25.md`. **다양성 통계만 산출 — D0 판정 발행·개정·재도출 없음.** 진단 예산 = bank seed 1 × restart 2 (D0는 3×2), 축소 사실을 명시.
- **경쟁 가설 선설정**: C-6만 검증하면 확증편향이므로 **H_ATTRACTOR**(공유 정책이 포화 box corner ‖a‖=29.983이므로 두 시나리오가 같은 corner에 수렴한 것은 그 corner가 둘 다에게 최적 ⇒ 관찰은 맞고 진단이 틀림)를 같은 강도로 세움.
- **메커니즘을 코드에서 확인**(가정 아님): `audit_one`이 `acc1 = reachable_accels(a_max, n_cert, cert_seed)`(모든 witness 동일 pool) → `warm = acc1[argmax(score_for_THIS_witness)]`(witness별 선택). ⇒ **"seed 공유"보다 "warm-start 충돌"이 정확한 가설**이며 직접 측정 가능.
- **사전등록 3 scheme**: `LEGACY`(FROZEN 상수, 1J–1N이 실제로 돌린 것) / `RELABEL`(offset만 변경, **NULL** — blind 구조 유지) / `DIVERSITY`(`derive_seed(mode='diversity')`, scenario_id·witness_id 진입). 판정 규칙은 `decide()`에 **코드로** 박아 손으로 적용하지 않음.
- **단일 실행**: LEGACY unique 11/12·정책충돌 1·warm충돌 14·escape 10/12 | RELABEL **5/12·28·36**·12/12 | DIVERSITY **12/12·0·0**·12/12 → 규칙이 `C6_SUPPORTED` 반환.
- **⚠️ 규칙의 빈틈 자기신고**: 교란 분기를 `collisions(RELABEL) < collisions(LEGACY)`로 열거했으나 관측은 `28 >> 1` = **열거하지 않은 경우**. 규칙이 옳은 라벨을 냈지만 관측 상황을 실제로 추론한 분기를 거친 것은 아님 — 관측을 포괄하지 못하는 결정 규칙은 운이 좋았던 규칙.
- **offset 하나 = 표본 하나 → `--spread`로 두 족 스윕**: witness-blind offset 6종 정책충돌 **[1,28,1,2,11,16]**, warm충돌 14~36(**0인 적 없음**) / 탈상관 base seed 4종 정책·warm충돌 **전부 0**, unique **12/12 예외 없음**.
- **판정 = C-6 CONFIRMED, 문장 강화**: 원안 "unique 수가 다양성을 **과대표시**" → 개정 "**witness-blind seeding 하의 unique 수는 다양성의 척도가 아니다**" (탐색 구조 동일한데 seed 재라벨링만으로 5/12~11/12). 메커니즘 = **공유 warm-start pool** 확정.
- **H_ATTRACTOR는 부분적으로 옳음**: offset 777000000에서 12개 중 8개가 index 4663 하나로 수렴 — 강한 attractor는 실재. 그러나 탈상관 시 충돌 0이므로 **attractor 존재가 충돌을 강제하지 않으며, witness-blindness가 충돌의 필요조건**.
- **🚫 주장하지 않은 것 — escape 효율**: 단일 실행만 보면 LEGACY 10/12 → DIVERSITY 12/12라 "탈상관이 탐색 효율도 개선"을 쓰고 싶어지나, 스윕하면 blind [10,12,11,10,12,12] vs 탈상관 [12,12,10,9]로 **범위가 겹침**. 탈상관은 **다양성 교정이지 효율 개선이 아님.** n=1에서 멈췄으면 없는 주장을 하나 더 만들 뻔했음.
- **불변**: C-3(15/15 falsified, 생존자 0)·C-4(구간 인증 2건)·D0 예산/판정기/판정 전부 미변경. LEGACY가 진단 예산에서 10/12만 찾은 것은 bank seed 3→1 축소 결과이며 D0와 모순 아님.
- **다음**: 2 D0-MODE-DIVERSITY clustering — **입력은 이제 탈상관 artifact여야 함**(witness-blind artifact로 basin을 세면 basin 수가 아니라 warm-start pool 구조를 세게 됨). **빈도 주장은 계속 금지**(탐색 예산이 basin 발견 확률을 결정).

### 2026-07-25 (tttt) — ✅ Phase 1P 0a·0b: 비자명 I1 인스턴스 + D0 소급 봉인 → **Phase 1O의 I1이 명세 오류였음이 드러남**(판정 불변, 13/13 PASS)

- **채택**: 1O §8의 0a·0b를 순서대로 실행. 산출 = `shepherd/scripts/{c1_phase1p_i1_instance.py, c1_phase1p_seal.py}` + `c1_invariant_tests.py` 개정 + `results/c1_corridor/{c1_phase1p_i1_instance.json, c1_phase1p_seal_manifest.json, c1_invariant_tests.json}` + `URP/c1_phase1p_0a0b_readout_2026-07-25.md`.
- **0a 인스턴스 탐색**: 선택 규칙을 **숫자를 보기 전에** 고정(`0.02 < v_fixed < 0.98` 중 미포획 표본수 `n_gap` 최대, 동률 시 rho0→tl→arm). 64셀 중 39셀 측정 → **34셀이 `v_fixed = 1.000` 포화**, 밴드 내 5셀. 선정 = **4.0/0.40/C**. seed 11/12/13 × n 4000/20000 안정성 확인 결과 n=4000은 우연히 포화 가능(5.0/0.85/C seed 13 = 1.000) → 인스턴스를 **n=20000**으로 고정(v_fixed 0.834–0.843, gap 46–54). 가능 표본 비율이 1.3–1.8%인 것이 근본 원인.
- **🚨 교체 즉시 I1 FAIL**: v_fixed 0.839117 → v_union 0.841615. 분해하니 FIXED 블록 317 feasible/51 uncaught(0.8391), EXTRA 블록 **5 feasible/0 uncaught(1.0000)** → 풀링 후 0.8416. **비율만 +0.0025 오르고 미포획 수는 51→51 불변** = Simpson 풀링 효과이지 방어자 개선이 아님. ⇒ **1O의 I1은 단조가 아닌 통계량 위에 세워져 있었고, 포화 인스턴스라 그 사실이 가려져 있었음.**
- **오류 유형의 재발**: 동결 D0 프로토콜에 `v_soft_replan_is_verdict_input: False`(분모가 임의 탐색예산인 비율은 판정을 나르지 못함)를 박아두고, 하루 뒤 최상위 불변식을 정확히 그런 비율 위에 세웠음. ledger 폐기표에 등재.
- **재명세**: 집합 포함 `S_fixed ⊂ S_union` 하에서 실제 단조인 양으로 이동 — (a) 공유 원소가 확장 평가 경로에서 **동일 라벨**을 받을 것(복사 아닌 **재평가**), (b) **탈출집합 불감소** `|esc(S_union)| ≥ |esc(S_fixed)|`. 두 클래스를 하나의 코드 경로로 통과시키기 위해 Block-1 단일구간 가속도를 K=4 상수구간으로 승격(I2 nesting이 종점 불변 보장).
- **신설 2종**: **I1b 비자명성**(`0 < esc_fix < n_feasible` — 1O의 결함은 "셀 오선택"이 아니라 "공허한 인스턴스의 조용한 통과"였으므로 이제 자기보고), **I1c 음성대조**(공유 원소 라벨 오염 시 술어가 False로 뒤집히는지 — 한 번도 실패한 적 없는 테스트는 실패 가능성이 검증되지 않은 테스트).
- **결과 = 13/13 PASS.** 캐비앗: 여기서 "fixed class"는 Block 1 단독(boundary·bang-bang 블록 제외) — 포함관계를 코드 수준에서 깨끗이 하기 위함이며 feasible 317→307 차이의 원인.
- **0b 봉인 (`c1_phase1p_seal.py`)**: 재탐색 뒤에 봉인하면 "재탐색 전/후 봉인"이 구분 불가해지므로 선행. **19/19 파일 `FILE_CONTENT_SEAL`(바이트 sha256), 69레코드 중 `FULL_BUNDLE` 0 · `PARTIAL` 69.** 결측 = `defender_traj`·`attacker_traj`·`fire_step`·`dynamics_sha` — **저장된 적이 없음**. 재실행 복원 후 "원본의 bundle hash"로 부르면 재구성물을 봉인하고 원본을 봉인했다 주장하는 것이 되므로 **하지 않음**. `0/69`가 정직한 값.
- **봉인 자체 검증**: `--verify` → SEAL INTACT(drift 0) / 1바이트 변조 → **SEAL BROKEN**(drift 1 정확 지목) / 복원 → INTACT. 검증 불가한 봉인은 장식이라는 I1c와 같은 규율.
- **부수 발견 — C-6 두 번째 독립 증거**: 봉인이 전 레코드 공격정책 해시를 대조하며 1N 자기신고(`651beb5780870eeb`, 인증 artifact 경로)와 **다른** 공유쌍 `961fcb3bbf8aa8b7`(EXPLOIT 3.2/0.35 WS1 ≡ 3.2/0.40 WS1, **1M exploit 재판정 경로**)를 발견. 서로 다른 코드 경로에서 같은 병리 확인.
- **판정**: **C-3(15/15 falsified)·C-4(구간 인증 2건) 불변.** 폐기 = 1O 형태의 I1. 신설 = C-7(봉인 강도). **C-6은 `PROVISIONAL` 유지** — Invalidator가 지정한 탈상관 재탐색(항목 1)이 미실행이므로 규칙 2 적용. 전방 요구사항 신설: **1P 이후 artifact는 궤적·fire_step·dynamics_sha를 저장한다.**
- **다음**: 1 diversity 모드 재탐색(C-6 승격/기각 결정) → 2 D0-MODE-DIVERSITY clustering → 3 cluster-stratified 감사 → 6 최소 controller 자유도 선정·봉인·D0. 1H(방위) 계속 보류.

### 2026-07-25 (ssss) — ✅ Phase 1O governance: seed namespace · evidence identity · invariant test · claim ledger → **판정 = 검증 종료조건 4항 충족, mode analysis 진입 승인**

- **채택**: 외부검토 진단(오류 3층 분류 — ⓐ예방 가능했던 공학 결함 ⓑ주장 범위 과장 ⓒ판정기 강화의 정상적 진전). 새 실험 없음, 재발 방지 장치만. 산출 = `shepherd/scripts/{c1_governance.py, c1_invariant_tests.py}` + `URP/{c1_phase1o_governance, c1_claim_ledger}_2026-07-25.md`.
- **반복 패턴 명명**: **"제한된 객체에서 참인 명제를 전체 시스템 명제로 너무 빨리 승격"** — 5회 재발(rest-to-rest를 플랜트 하한 / restricted LP infeasible을 전체 infeasible / fixed-path remask를 dynamic certification / 10 mm를 전체 model uncertainty / 수치근을 exact). 계산이 아니라 **이름과 headline이 증거보다 한 단계 앞섰다.**
- **seed namespace**(`derive_seed`): SHA-256 기반(파이썬 `hash()` 금지 — 프로세스 salt). **`paired`**(witness_id 제외, CRN·난이도 비교) vs **`diversity`**(witness_id 포함, basin 발견) 2모드. 1J–1N은 사실상 paired로 돌며 diversity를 주장 중이었음.
- **evidence identity 2분할**: `attack_policy_hash`(제어열만, 공유 가능) vs `evidence_bundle_hash`(scenario·config·defender 궤적·attacker 제어열과 궤적·reset과 모든 seed·fire step·verifier version·판정과 margin·dynamics hash).
- **invariant property test 11/11 PASS**(`c1_invariant_tests.py`, **headline 실험보다 먼저 실행 의무**): I1 강한 attacker class는 viability 개선 없음 / I2 K=8이 K=4 nest(delta 1.8e-15 m)·I2b K=6은 nest 미주장 / I3 독립 적분기 endpoint 일치(0.0) / I4·I5·I5b seed 모드 동작·프로세스 안정 / I6 10개 필드 전부 bundle hash 변경·I6b 정책해시 공유≠번들 충돌 / **I7 sufficient screen 실패가 collision 라벨로 변환되지 않음**(24건, 오분류 0) / I8 LP 창 == judge 창(N_DEP=8).
- **claim ledger 도입**(living, `URP/c1_claim_ledger_2026-07-25.md`): headline마다 **Claim/Evidence object/Scope/Does not establish/Invalidators** 5칸 필수. 6건 등재 + 폐기 8건 사유 보존. **규칙 2(provisional)**: 새 해석은 최소 한 회차 묵힌 뒤 승격 — C-6(seed 공유)이 첫 적용.
- **강도·일반성 2축 분리**: `SEARCH_CANDIDATE`→`NUMERICALLY_VERIFIED_COUNTEREXAMPLE`→`INTERVAL_CERTIFIED_COUNTEREXAMPLE` × `FIXED_CONDITION`→`MULTI_RESET`→`DISTRIBUTION_LEVEL`. 한 단어(`certified`/`robust`/`exact`)에 두 의미 금지.
- **종료조건 4항 충족**: ①headline 뒤집는 미해결 결함 없음 ②시간·seed·hash·nesting·단조성 property test 존재 ③주요 반례가 독립 적분·clearance·predicate 전부 통과 ④남은 한계가 명시된 scope limitation. ⇒ **mode analysis·controller 설계 진입 승인.**
- **캐비앗**: I1이 이번 인스턴스에서 `v_fixed = v_union = 1.000`이라 단조성이 **비자명하게 검증되지 않음** → 다음 회차 첫 항목으로 escape 있는 셀 교체.

### 2026-07-25 (rrrr) — ✅ Phase 1N: net-cone predicate 독립성 · 유리수 전구간 인증 · 강도 집계 정의 · D2 분리 + **신규 결함(탐색 seed witness 간 공유) 자기신고**

- **채택**: 외부검토 수정 3건. 산출 = `shepherd/scripts/c1_phase1n_hardening.py` + `results/c1_corridor/c1_phase1n_hardening.json` + `URP/c1_phase1n_hardening_2026-07-25.md`.
- **N1 net-cone 독립성**: V4가 원본 `_caught_se3_cone`을 그대로 호출 → **predicate 오류로부터 비독립**이었음. **arccos 없는** 독립 구현(`ax ≥ |r|cosθ`) 추가, 11개 시험 전부 PASS(폐형식 점·range 0/29.847 경계·축 정규화 불변·1e-9 m 경계 walk·**randomized parity 20,000건 불일치 0**). ⇒ 정본 표현 = *"…together with the frozen net-cone predicate"*, **`independently verified` 단독 사용 금지**.
- **N2 유리수 인증**: 4점 보간이 대수적 정확이어도 float에서는 인증 아님 → **샘플 이후 전 계산을 `fractions.Fraction`**, 샘플은 구간 팽창(rel 1e-13/abs 1e-11). 인증 대상 = **`g(t)=‖r(t)‖²−r_kill²`(제곱근 미사용)**. 결과: 두 최소 margin 건 `CERTIFIED_COLLISION_FREE`, **margin 하한 ≥1.695 mm / ≥8.319 mm**, subdivision depth 0.
- **N3 강도 집계 정의 고정**: **`m_scenario = max over sealed verified artifacts of (min_t d(t) − r_kill)`**. artifact sha·argmin·`audited_min_margin_m`·verifier version·예산 비교 동시 저장. **12건 중 10건이 10 mm 초과.**
- **N4 D2 분리**: K=8은 K=4를 정확 nest하나 **K=6은 breakpoint 미정렬 → 정확 포함 불가**. ⇒ **D2a**(K=8, NESTED, containment 필수, 정식 escalation) / **D2b**(K=6, NOT NESTED, exploratory 전용, 생존 주장 사용 금지).
- **🚨 신규 결함(자기신고)**: 두 인증 artifact의 **제어열이 완전 동일**(max abs diff 0.0, 4세그먼트 ‖a‖=29.983 포화). 원인 = `reachable_accels`가 (a_att_max,n,seed)에만 의존하고 CEM seed도 `replan+cert`뿐 → **witness 식별자 부재, 전 witness가 같은 난수 스트림**. **D0 falsification은 무효화되지 않음**(반례는 통계적 독립 불필요)이나 **raw/unique 수가 탐색 다양성을 과대표시** ⇒ mode analysis 전 탈상관 필요. 부수 가설: 동일 포화 bang-bang 하나가 서로 다른 두 방어 배치를 모두 탈출 = **지배 escape mode 존재 시사**(진단 지위만).

### 2026-07-25 (qqqq) — ✅ Phase 1M: 1E exploit 3건 동일 판정기 이관 · 최소 margin 2건 구간 인증 · escalation 사전등록 동결

- **채택**: 외부검토 지정 필수조치. 산출 = `shepherd/scripts/{c1_interval_certificate.py, c1_phase1m_certificates.py}` + `results/c1_corridor/c1_phase1m_certificates.json` + `URP/c1_phase1m_certificates_2026-07-25.md`.
- **M1**: 1E optimizer-exploit 3건(3.2/0.35·3.2/0.40 O-WS1, 4.0/0.70 O-WS2)을 Phase 1C CEM seed로 결정론 재현 후 **1L 판정기로 재판정** → 전부 falsified, margin 0.224/0.251/2.407 m, collision·unresolved 0. ⇒ **15개 시나리오가 하나의 판정기 아래**로 통합(판정기 이원화 해소).
- **M2**: Bernstein 볼록껍질 + de Casteljau + outward rounding으로 최소 margin 2건 재결정 → 둘 다 `CERTIFIED_COLLISION_FREE`.
- **M3 escalation 사전등록(숫자까지 고정, dormant)**: **D0**(실행·동결, 결과 덮어쓰기 금지) → **D1**(트리거 = D0 verified escape 0인 controller-scenario에만 자동 발동; K/pop/iters 불변, **restart 2→16**, seed 64000201–216; controller는 D0 **전에** 봉인·D1 내 재최적화 금지·verifier/objective/attacker dynamics 불변·D0 seed 재사용 금지) → **D2**(공격자 클래스 변경, 별도 버전) → **D3**. 별도 프로토콜: **D0-MARGIN-STRENGTHENING**(FALSIFIED 불변·강도만 상향) / **D0-MODE-DIVERSITY**(`FIXED_CONDITION_CONTROLLER_DESIGN_DIAGNOSTIC`·**빈도 주장 금지**). 라벨 누적 기록.
- **용어 축소**: "exact" → **`NUMERICALLY_RESOLVED_CONTINUOUS_MINIMUM_DISTANCE`**(companion-matrix 수치근) / `ROBUSTLY_FALSIFIED_UNDER_MODEL_UNCERTAINTY` → **`CLEARANCE_ROBUST_TO_10MM_ADDITIVE_GEOMETRIC_ERROR`**(예산은 **상대거리 가산 기하오차만**; 동역학·tracking·Hermite mismatch·cone·admissibility 미포함, `meta.budget_scope`에 명문화).

### 2026-07-25 (pppp) — 🚨 Phase 1L: 정확 연속-clearance 판정 → **D0 생존자 소멸**, 그리고 1K 판독 정정

- **채택**: 외부검토 지정 "가장 먼저 할 일"(예산 증액이 아니라 V3 탈락 candidate 2건의 정확 판정). 산출 = `shepherd/scripts/{c1_exact_clearance.py, c1_phase1l_exact_adjudication.py}` + `results/c1_corridor/c1_phase1l_{exact_adjudication,survivor_adjudication}.json` + `URP/c1_phase1l_exact_adjudication_2026-07-25.md`.
- **방법**: breakpoint 합집합(공격자 `tau/K`, 리미터 Hermite `dt`)으로 구간 분할 → 각 구간에서 공격자=포물선(2차)·리미터=cubic Hermite(3차) ⇒ **`d²(t)`=6차 다항식**, 정류점 = **5차 도함수 실근**(companion matrix). 양 끝점+실근 평가 = 구간 최소거리. 계수는 4점 정확 보간(계수 대수 재유도 없음).
- **생존자 판정**: `BASE 2.8/0.30 C`의 raw candidate 2건 → unique 1건, **`VERIFIED_COLLISION_FREE`, 정확 margin +1.70 mm**, net cone escape ⇒ **`FALSIFIED_BY_ADVERSARIAL_REPLAN_D0`**. **D0 생존자 0.**
- **전건 재분류**: 12/12 falsified, **`VERIFIED_COLLISION` 0건 · `UNRESOLVED` 0건**. 정확 margin: RH 0.050–0.068 m / baseline 0.0017–0.0230 m / max-clr 0.95–1.07 m.
- **⚠ (nnnn) 판독 정정**: "독립 판정기가 38건 기각으로 한 건을 구했다"는 **틀림**. 그 38건은 **전부 보수적 스크린의 오기각**이었고 실제 충돌 0. 유효했던 부분 = **V1·V2·V5**, 결함 = **V3**(1.25배 empirical padding) → **`CONSERVATIVE_CONTINUOUS_CLEARANCE_SCREEN`**으로 격하, 판정에서 제외.
- **3분류 도입**: `VERIFIED_COLLISION_FREE` / `VERIFIED_COLLISION` / `UNRESOLVED_CONTINUOUS_CLEARANCE`(+`COLLISION_FREE_BUT_CAUGHT`, `INADMISSIBLE_ARTIFACT`). **열 분리 의무**: raw/unique/audited/not_audited/verified_escape/verified_collision/unresolved. **margin 라벨 분리**(사전등록 예산 0.010 m).

### 2026-07-25 (oooo) — ✅ Phase 1K: 독립 판정기(V1–V5) 도입 + 1E exploit 포함 재감사 + D0 프로토콜 동결 → **15건 중 14건 falsified**

- **채택**: 외부검토 비준 순서 `A구현→B검증→C재감사→D동결→E탐색`의 B·C·D. 산출 = `shepherd/scripts/{c1_replan_verify.py, c1_phase1k_frozen_audit.py}` + `results/c1_corridor/c1_phase1k_frozen_audit.json` + `URP/c1_phase1k_frozen_audit_2026-07-25.md`. **E(넓은 controller 탐색)는 착수하지 않음.**
- **B 독립 판정기**: 탐색과 **적분기·마진함수·마스킹 헬퍼 무공유** 별도 모듈. V1 제어허용성 / V2 독립 재적분 / V3 연속충돌(Lipschitz 하한) / V4 `_caught_se3_cone` / V5 exact replay.
- **C 결과**: RH 4/4 · max-clr 2/2 · **1E exploit 3/3** · legacy baseline 5/6 falsified. 유일 생존 = `BASE 2.8/0.30 C`(당시 판독; (pppp)에서 falsified로 정정). 양성대조가 RH/baseline보다 1–3 자릿수 큰 margin으로 무너져 **변별력 정상**. 결정론 bank 존재시험: RH·baseline 전부 False ⇒ escape가 **최적화 경로에서만** 나옴.
- **D 동결**(`FROZEN`): **판정 = 이진 존재 시험**. **`v_soft_replan`은 판정 입력 아님** — `(k₀+k_new)/(n₀+n_new)`가 (탐색예산)/(n_cert) 임의비의 함수. K=4·pop192·iters14·restart2 / cert seed 91000101–103 / replan 확인 63000101–2 / n_cert 20,000 / 판정기 n_sub 64 / **reset 1100 단일 → 분포 주장 금지**. **추정량 3분할**: (i)stochastic Block-1 (ii)결정론 bank **존재 시험** (iii)union falsification=판정.

### 2026-07-25 (nnnn) — 🚨 Phase 1J: ADVERSARIAL_REPLAN_FALSIFIER 구축 → **RH witness 4건 + legacy baseline 6건 전부 escape 존재**

- **채택**: 외부검토 판정 "2번(replan)을 1번(넓은 controller 탐색)보다 먼저". 산출 = `shepherd/scripts/c1_replan_falsifier.py` + `results/c1_corridor/c1_replan_falsifier{,_lowEffort}.json` + `URP/c1_phase1j_replan_falsifier_2026-07-25.md`.
- **역할 = 반증기, 인증기 아님**: escape 발견 → 실패 확정 / escape 미발견 → 해당 예산 생존. **`ADVERSARIAL_DYNAMIC_CERTIFIED` 코드에 미구현.**
- **필수 사양 4건**: ① `P_replan = P_fixed ∪ P_optimized`(union 자체 `_seg_paths_turn` 사용) — **containment 12/12 exact**(old bank만 → 기존 remask 1e-12 일치) + **monotone 12/12** ② objective = `min(kill_margin, cone_exit_margin)` [m], `>0 ⟺ escape` — 대리량 없음 ③ bank warm start ④ attacker search/confirm seed 분리(탐색 52000001–2 / 확인 63000101–2).
- **결과**: **12/12 escape 존재**(고강도). RH margin 34–66 mm / **legacy baseline 2–23 mm** / max-clr ~1 m. **substep n_t 24→192 재계산에서 kill-margin 소수 5자리 불변 ⇒ 이산화 산물 아님.**
- **⚠ 방법론 문제 발견**: `v_soft_replan`이 탐색 강도에 따라 **판정을 양방향으로 뒤집음**(FLIP 3건). 이진 escape 존재는 강도 단조(저 7/12 → 고 12/12) ⇒ 판정을 이진으로 이관 제안((oooo)에서 동결).
- **함의**: **`T*_RH-remask,grid` · `T*_simple` · `η_RH-ref` 전부 기준선 지위 상실.** 넓은 controller 탐색을 먼저 했다면 "세 번째 반복"이 됐을 것.

### 2026-07-25 (mmmm) — ✅ Phase 1I: 외부검토 Q1~Q8 회신 + 자기신고 외 결함 7건 처리

- **채택**: 외부검토 판정 전부 수용(수정 4·기각 4). 산출 = `shepherd/scripts/c1_phase1i_audit_response.py` + `results/c1_corridor/c1_phase1i_audit_response.json` + `URP/c1_phase1i_review_response_2026-07-25.md`.
- **명칭 개정**: `T*_dyn`/`T*_plant` → **`T*_RH-remask,grid`** · `ΔT_residual`/`G_closure` → `ΔT_RH-ref`/`η_RH-ref` · **"plant bound/플랜트 하한" 금지** · "폐루프 replay" → **"open-loop sequence replay in the full simulator"**. 절차 규칙 **`proposal–verification separation`** 승격(목적함수 정렬은 보조).
- **#2 off-by-one 실재·수정**: judge `n_dep = int(round(0.4/0.05)) = 8`(E_lane = f..f+8, 0.40 s) vs LP `N_DEP = 9`(f..f+9, 0.45 s) = **한 격자 과다 구속**. `N_DEP=8` 수정. **56셀 전수 재계산 feasibility flip 0**(오차 방향 보수적) — 결함은 실재, 결론 불변.
- **#3 선택편향**: 탐색(77000001–3, n=2000) → **봉인** → 확증(**91000101–3**, 미사용) n=20,000 **1회**. 4/4 통과.
- **#4 Wilson 부당**: union = Block1 20,000 + 결정론 504(2.5 %)이나 **feasible 부분집합에서 결정론 비중 5.8–9.8 %**(extreme point 과대표집) + 3seed pooling **3회 계수**. ⇒ headline은 **across-scramble t-LCB**, pooled Wilson은 참고열. 지위 = **`provisional confirmatory`**(scramble 8–10 전까지).
- **#1 fixed-ray**: 봉인 witness 4건 **LP-ρ 잔차 0.000000 m · 방위 드리프트 0° · v_tan=v_axial=0** ⇒ LP는 **"fixed-ray 1D radial subsystem의 정확한 LP"**. **`INFEASIBLE = 해당 certificate class에 해 없음`**(플랜트 진술 아님). **#7**: feedback 항 항등적 비활성 → **open-loop sequence replay**. **#5** 봉인법칙 문면 축소. **#6** `d*≤0.038` = heuristic classifier, **offline screen 전용**(보상 삽입 금지).
- **표본 정정**: constructive response witnesses **4** / unique post-fire certification states **3**(전체를 3으로 낮추는 표현은 부정확).

### 2026-07-25 (llll) — ✅ 3자 검토 브리프(1F·1G, Q1~Q8) + 1H 방위 봉인 계획

- 산출 = `URP/c1_phase1fg_review_brief_2026-07-25.md`(자기신고 6항 포함) + `URP/c1_phase1h_angular_sealing_plan_2026-07-25.md`(G0/G1/G2 게이트).
- **1H 계획 요지**: 방위 arm을 바로 만들지 않고 **G0(sham transit seal로 방위 개방의 인과효과만 분리)** 를 먼저. 터미널은 이미 30° 여유로 봉인돼 있고 열린 곳은 **transit `ρ ∈ (3.40, 5.0]`** 뿐이며 그 손해는 미측정. G1 = 방위 LP 확장(`T*_dyn,seal` 가격), G2 = MARL. **목적함수는 최소화 방향만**(1G 교훈 반영).

### 2026-07-25 (kkkk) — ✅ 1H 진단: escape 기하 분해 + **방위 봉인 법칙 유도·실측 일치**

- 산출 = `shepherd/scripts/{c1_escape_geometry.py, c1_seal_law.py}` + `results/c1_corridor/{c1_escape_geometry,c1_seal_law}.json`.
- **escape 기하(6 witness)**: 살아남은 escape 종점 perp **0.05–0.60 m, 링(2.6) 안쪽 100 %**. 통계력 있는 유일 사례(n=73) 방위 skew = null 대비 **+0.05**(무의미). 실제 기전 = **half-angle 3.84° net cone**(반경 0.067·R)에서 짧은 사거리 lateral 이탈. baseline은 escape 0건. ⇒ **잔여는 방위 문제가 아님**(직전 예단 부분 부정).
- **봉인 법칙(닫힌 형태)**: 간격 중점까지 현 길이 `2ρ·sin(Δφ/4) ≤ r_kill` ⇒ **`SEAL ⟺ Δφ_max ≤ 4·arcsin(r_kill/2ρ)`**. ρ=2.6→**120.0°** · 3.40→89.9° · 5.00→**60.3°**.
- **실측 일치**(ρ0 5.0/T 0.55/Arm L hold, actual judge, n=20k×3): 90°·105°·115°·**120° SEALED**(LCB .959/.946/.935/.909) → **125° FAIL**(.888) → 135°(.806) → 150°(.488). **측정 경계 (120°,125°] vs 예측 117.5–120° — 한 격자 일치.**
- **따름정리**: ①터미널 방위는 사실상 공짜(균등 4-ring 90°는 30° 여유) ②**균등 4-ring 봉인은 ρ ≤ 3.40부터** ⇒ nominal 다이브 5.0→2.65의 **앞 절반은 방위 개방**.

### 2026-07-25 (jjjj) — 🚨 Phase 1G: Arm L을 E1.5 authoritative judge로 감사 → **max-clr witness 8/8 기각(증거 생성기 착취)**, 변위구속으로 재수립

- **채택**: 1F 산출물을 판정기에 통과시키기 전에 확정 취급 금지. 산출 = `shepherd/scripts/{c1_phase1g.py, c1_phase1g_search.py, c1_phase1g_plot.py}` + `results/c1_corridor/c1_phase1g_{dynamic_judge,maxclr_falsified,search,rho0_knob}.json` + `witness_artifacts_1g.tar.gz` + `URP/c1_phase1g_readout_2026-07-25.md`.
- **기각**: 1F의 `solve_witness`(max-min-clearance)가 **under-constrained** — 최소여유 최대화가 **발사 후 링을 바깥으로 밀어내는 것을 보상**. n=20,000 감사: **8/8 기각**(sup_disp **1.15–2.30 m** vs 허용 0.26; static 0.84–1.00 → **actual 0.011–0.076**). **1E 착취해와 같은 형태.** ⇒ 1E = 판정기 착취 / 1G = **증거 생성기 착취**.
- **수정**: `solve_witness_hold` — 목적함수 "최소여유 최대화"→**"전개창 변위 최소화"**, `|ρ_t−ρ_f| ≤ d ≤ 0.26`(감사 스크린과 동일값) 구속 추가. 여전히 LP.
- **재수립**(당시 판독; (nnnn)에서 전량 falsified): `T*_dyn` = {2.8 .15 / 3.2 .25 / 4.0 .40 / 5.0 .55}, actual v_soft .954–.976 / LCB .939–.959. **재현성 대조**: legacy baseline 6건이 1E 값(actual .988–.995, LCB .969–.977)을 **6/6 정확 재현**, 경로 parity 불일치 0.
- **부산물**: LP 변위 `d*`가 판정 결과를 예측(`≤0.038` 통과 / `0.050` 기각) — **MC 없는 offline screen**((mmmm)에서 보상 삽입 금지로 격하).

### 2026-07-25 (iiii) — ✅ Phase 1F: 플랜트 LP 하한 + 폐루프 재생 → **기존 rest-to-rest 하한 무효 확정**(R-1/R-2)

- **채택**: 사용자 지시(R-1 제어 효율비 정밀화, R-2 nominal 결손 최소 변경량). 샌드박스에서 공개 리포 `b978f1b` 클론 실행. 산출 = `shepherd/scripts/{c1_plant_bound.py, c1_plant_bound_plot.py, c1_amax_sweep.py}` + `results/c1_corridor/{c1_plant_bound,c1_response_envelope_fine,c1_rho0_axis,c1_amax_sweep}.json` + `c1_plant_bound.png` + `URP/c1_phase1f_readout_2026-07-25.md`.
- **핵심 정정**: `T_LB = 2√(|ρ0−ρ*|/a_max)`는 **rest-to-rest 바운드**이나 인증조건(`E_cap` 스냅샷 1회 + `E_lane` 전개창 매 스텝 perp ≥ 2.50)은 **종단 정지를 요구하지 않음** ⇒ **하한이 아님**. 1B/1C의 `ΔT_residual`·`G_closure` 재정규화 대상.
- **방법**: 반경 부분문제가 시뮬레이터 자체 적분기(semi-implicit Euler)에서 **선형**(`ρ_t = ρ0 + dt²Σ(t−k)a_k`) ⇒ **LP**. 증거 수열을 폐루프 재생해 검증.
- **재현성**: 샌드박스 실행이 디바이스 `c1_response_envelope.json` 해당 셀을 `capture_margin`·`clearance_margin` 기준 **1e-12 이내 5/5 정확 재현**. a_max 패치 경로도 30에서 무섭동 재현.
- **정밀 포락선**: 4 ρ0 × 18 T × 3 arm = **216 롤아웃**(0.05 s 해상도). **1B의 `max_angular_gap_deg`는 216셀 전부 180.0** = Phase 1D 정정 ④(arctan2 degenerate)의 잔재 확인.
- **단순 arm은 여유를 못 씀**: ρ0 3.4–5.0 @T=0.5 전 셀 실패(비단조) / **a_max 30→45 전 셀 실패**(minclr 진동) ⇒ 구속 자원 = 작동 권한이 아니라 정책.

### 2026-07-25 (hhhh) — 📌 backfill 포인터: 2026-07-23~24 Phase 1/1B/1C/1D/1E는 `URP/` 문서에만 존재(로그 미기록)

- 이 로그는 (gggg) 2026-07-21 이후 **7/23~24 작업이 미기록**인 상태로 7/25를 맞았다. 해당 회차를 실행하지 않은 세션이 내용을 재구성해 적는 것은 날조 위험이 있으므로, **내용 기재 대신 문서 색인만** 남긴다.
- `URP/c1_phase1d_plan_2026-07-24.md` · `URP/c1_phase1d_E0E1_readout_2026-07-24.md` · `URP/c1_phase1d_E0E1_review_brief_2026-07-24.md` · `URP/c1_phase1e_review_response_2026-07-24.md` · `newURP/docs/c1_response_envelope_briefing.md` · `newURP/docs/c1_review_response.md`
- 코드 `shepherd/scripts/{c1_response_probe.py, c1_controller_gap.py}`(커밋 `b978f1b`까지 반영) · `{c1_phase1d.py, c1_phase1e.py}`(**디바이스 untracked**) · 결과 `results/c1_corridor/{c1_response_envelope, c1_terminal_band, c1_terminal_band_refine, c1_response_audit, c1_controller_gap, c1_containment, c1_viable_rescore, c1_dynamic_judge}.json` + `witness_artifacts.tar.gz`.
- 요지(해당 문서 기준): 1B response envelope → 1C Arm O 17셀 전부 실패 → 1D E0 per-step containment PASS·low-knot 무효 / E1 CV-swept 감사 → **E1.5 `OPTIMIZER_JUDGE_EXPLOITATION_DEMONSTRATED`**(baseline 6/6 생존, O 후보 3/3 기각). 상세는 위 문서 참조.

### 2026-07-21 (gggg) — ✅ Move A0 물리-접지 terminal 경계 probe → **판정 = A0_TERMINAL_FEASIBLE_DYNAMIC_UNSOLVED** — η>1(realizable 2.6/2.0-2.1)서 terminal safe 실존(engage-무관)이나 dynamic corridor 미해결(barrier = trajectory-level)

- **채택**: 사용자 지시(A0 boundary probe, full sweep 아님). Move B 판정 4개 carried: HISTORY_COMMITMENT_KINEMATICS_CONFIRMED / CASE_B_CAPTURE_NOT_VALIDATED / GROUNDED_LOWER_BOUND_FAIL / TEMPORAL_PREMISE_UNRESOLVED. θ=0.9 **고정**(pt1, geometry+judge 동시완화 금지). 산출 = `shepherd/scripts/c1_moveA0_probe.py`(+`_plot.py`) + `results/c1_corridor/c1_moveA0.{json,png}`. Case A·E1 불변.
- **보정 η(pt2, body+safety 필수)**: **η = r_kill_eff / (r_net_dir + r_body 0.2 + m_safety 0.2)**. 친사 lane = r_net_dir+0.4(bare net 아님). ⇒ 현재점 정직한 **η=0.758**(naive 0.89 아님).
- **물리 manifest(pt3, 자유 knob 아님)**: r_kill_eff = limiter 종말 effector 무력화 반경(realizable 2.0-2.6). r_net_dir = net directional reach = **친사 lane AND capture aperture(결합)** — 축소=더 collimated net, capture aperture도 축소(theta_net *= r_net/2.24; **apLoss=1-(r_net/2.24)²**). r_body=airframe 반경(0.2). m_safety=lane 안전버퍼(0.2). realizable core = r_kill≤2.6 ∧ r_net≥2.0.
- **terminal grid 4×4(pt4-6, Case A)**: r_kill{2.0,2.3,2.6,3.0}×r_net_dir{2.24,2.10,2.00,1.80}, seed-1100 boxer init CEM. **η<1 전부 unsafe; η>1서 terminal safe 실존.** **realizable-safe = (2.6,2.1)η1.04 · (2.6,2.0)η1.08**(cap 0.52, clr +0.1/+0.2, **apLoss 12-20%, p_feas thin 0.005**). 경계 η≈1(0.958 fail·0.985 fail·1.04 safe). safe shell = **perp≈r_kill**(narrow ~0.1m: perp<r_kill over-box p_feas→0=clean 아님, perp≫r_kill v_soft 붕괴) → η=r_kill/lane≥1 경계 유도됨. **η만으로 판정 안 함**(apLoss 병기).
- **θ-slice(pt8, boundary cell만 0.90/0.875/0.85)**: (2.6,2.1) θ 전부 safe(robust); (2.6,2.24)η0.985 θ완화도 clr~0(경계 못 넘음); (2.3,2.0)η0.958 θ무관 fail. ⇒ 결속축 = **η(clearance)**, θ 아님(dddd 2요인 중 여기선 η 지배).
- **dynamic G3(pt7, warm+standoff-ring, per-cell kill_radius/cone override)**: current·boundary·interior 3셀 **전부 tier<4 fail**. warm(E1 replay) m_clear −2.1~−2.4(E1이 perp~0.3 crowd=old-η 궤적). standoff ring(track@r_kill) **never fires**(4-ring sparse, gap seal 실패). ⇒ **η>1이 STATIC box/clear 긴장은 해소하나 DYNAMIC(이동 attacker track + escape gap seal + perp≥lane 동시)은 cheap controller로 미해결.**
- **판정 = A0_TERMINAL_FEASIBLE_DYNAMIC_UNSOLVED**: 성공게이트(pt9: realizable cell서 cap>0 ∧ clr>0 ∧ dynamic safe replay 동시) **미충족**(dynamic fail). ⇒ **full sweep+MARL blind 진입 금지**(pt10). 단 **terminal feasible interior 확인** → 다음 = 식별 셀(2.6/2.0-2.1)서 **focused dynamic co-design**(sealing standoff formation / post-fire deconfliction (zzz) / MARL), blind sweep 아님.
- **folded track(pt10)**: 병행 유지, A0 block 안 함. full Move C = grounded folded R_cap≥R_req@10m 시에만.
- **다음(선택)**: ⓐ **focused dynamic co-design**(sealing standoff 궤적 설계, (2.6,2.0-2.1)서 tier≥4 탐색; 성공 시 full dynamic sweep+MARL 개방) vs ⓑ **folded-deployment 모델**(init='folded' 구현, (ffff) 전제 최종해소). 사용자 판단.

### 2026-07-21 (ffff) — ✅ N1 temporal grounding: (eeee) 전제 검증 → **판정 = CONDITIONAL(Move C sensitivity + Move A 병행)** — grounded lower bound 미달(R_cap 1.00 < R_req 1.26 @crossing), 통과는 비물리 flat-init뿐

- **채택**: 사용자 지시(2026-07-21). 목표 = net_forward 초기 silhouette를 그대로 capture로 간주하지 말고, seed 1100 crossing(travel~10m/τ*0.19s)서 net이 **실제 capture-effective**한지 검증. 산출 = `shepherd/scripts/n1_temporal.py`(+`_plot.py`) + `results/c1_corridor/n1_temporal.{json,png}`; Move A skeleton = `c1_moveA_codesign.py` + `c1_moveA_eta.json`. Case A·E1 불변.
- **방법**: net_forward mesh snapshot(travel 5/7.5/10/12.5/15/20m; model 불변, building block 재사용). metric = max support·**connected axis inradius**·aperture·anisotropy·silhouette area·axial depth·centroid speed·**folding ratio**. **R_geom(silhouette) vs R_cap(capture-effective) 분리**. 3 band: **upper**(flat-init silhouette)/**nominal**(connected inradius, flat IC)/**lower**(folded-opening = net_radius·travel/engage, inradius cap).
- **중심 캐비앗**: net은 **flat(완전개방) launch 후 붕괴** = 실제(folded→개방)의 **정반대**. ⇒ pre-engage silhouette는 **과대평가**; net_forward는 **engage(20m)서만** Xu-anchored(rho_air 보정). init='folded' = **NotImplementedError**(미구현). folding 1.00·anisotropy 1.05·depth 0.27→3.19 = flat-init mesh는 coherent(등방·무balling)이나 **그 IC 자체가 비물리**.
- **R_req(τ*=0.19s)** = 횡offset 0.08 + |v_perp|·τ(0.285) + ½·30·τ²(0.54) + uncertainty(0.2~0.5) = **1.11~1.41m**(nom 1.26).
- **결과(crossing travel 10m)**: R_cap **lower=1.00 < R_req(전 uncertainty sweep 1.11~1.41) = FAIL**; nominal=2.59·upper=2.83(통과하나 flat-init 낙관·비-grounded). retention_plausible=True(depth 1.0>0.5·연결 aperture; 단 heuristic, Xu는 coverage/hang만 검증). fail 여유 작음(1.00 vs 1.11) → net 개방이 linear보다 조금만 빨라도 뒤집힘 = folded 모델이 결정적.
- **판정 = CONDITIONAL_MOVE_C_SENSITIVITY + MOVE_A 병행**: grounded lower bound 미달 → **Case B 미승격**(사용자 pt8: lower 또는 grounded nominal 통과 시만; nominal 통과는 flat-init 낙관이라 미인정). ⇒ **Move C = sensitivity 보류**, **Move A(engage-무관 η>1) 병행**. 전제 최종 해소 = **실제 folded-deployment net 모델(init='folded') 구현**(N1 human-lane).
- **Move A skeleton(사용자 pt10)**: static **η=r_kill/r_net_eff=2.0/2.24=0.893**; η≥1 도달 = r_kill **+0.24**(→2.24) 또는 r_net_eff **−0.24**(→2.00). η는 필요-불충분(dddd 2요인). **full sweep 보류**(NotImplementedError gate).
- **다음(선택)**: ⓐ **folded-deployment net 모델(init='folded') 구현** → 전제 최종 해소(Move C 확정/기각; N1 물리 확장) vs ⓑ **Move A full sweep 착수**(net/kill η>1 co-design, engage-무관·즉시 실행 가능). 사용자 판단 대기.

### 2026-07-21 (eeee) — ✅ Move B: capturability-PERSISTENCE 반사실 진단 → **판정 = PREMISE_NET_TEMPORAL**(history-dependent 포획 REAL이나 net 조기전개 전제 하에서만; wall↔history가 단일 미검증 전제로 환원)

- **채택**: 사용자 지시(2026-07-21). **diagnostic ONLY** — Case-A instantaneous judge·E1 불변, Case-B는 gate 양성 시에만 공식화 후보(사용자 pt7). 산출 = `shepherd/scripts/c1_persistence.py`(+`_plot.py`) + `results/c1_corridor/c1_persistence.{json,png}` + `tests/test_c1_persistence.py`(6 green).
- **재정의 질문(사용자)**: "crowded eligible state가 dynamic tube서 포획?"이 아니라 — limiter가 net lane을 **비우기 시작(release)한 뒤**에도 이전 shaping이 만든 attacker velocity/heading **commitment**가 deployment window 동안 capturability를 **유지**하는가.
- **설계**: seed 1100 exact replay(manifest = acts/obs md5 + t6..10 snapshot). release t∈{6..10} × branch{cem_tail·hold·radial·lateral_behind·greedy_clear} × evaluator{Case A instantaneous / Case B-phys bounded-accel reachable tube / Case B-A2 realized policy path}. net = **net_forward swept cone**(front=cum_travel(τ), 접지 se3 cone half-angle=Case-A와 동일) + **moving-limiter no-go**. gate = min_friendly_clearance≥0(G3 (bbbb) convention, 유지) AND Case-B p_cap>0.
- **기전 확인(probe)**: 발사 시 attacker offset **0.08m(축 위)**·v=[−20,1.5](20 m/s 접근); net front가 attacker 축거리 도달 **τ*≈0.19s(~4/8 step)**. Case-A 적격성 = **boxing**(p_feas 0.97→**1.6e-3**@t10→0@t11), net cone 사실상 무관 = 순간기하(A). 조기 crossing이라 worst-case 횡기동(½·30·τ*²≈0.34m)도 crossing-range cone 못 벗어남 = velocity-commitment 채널.
- **이중 경계(결정적)**: **(판별성)** null control(v를 축-수직 회전) → p_cap **1.00(축-commit) vs 0.00(null)** = metric 정상. **(optimistic**, cone launch부터 유효**)** p_cap≈1, gate 통과 **t6 {radial,lateral_behind,greedy_clear}**(min_clear +0.03~+0.38). **(engaged**, net이 20m engage서만 유효 포획자**)** p_cap=**0 전부** — median capture travel **9.2~11.7m ≪ engage 20m**. fresh-CRN Δp_cap 0.001; capture(step~11) < penetration(step~22) 선행(관통이 결과 뒤집지 않음).
- **판정 = PREMISE_NET_TEMPORAL**: history-dependent(velocity-commitment) 포획은 **REAL·robust**(null 판별·CRN 안정·persistence ~0.3s)하나 **오직 "net이 ~10m travel(engage의 절반)서 유효 포획자인가"라는 N1-flagged 미검증 조기전개 전제 하에서만**. ⇒ wall vs history-dependence가 **단일 전제**로 환원. blind Move C/A 아님 — **다음 = net 시간전개(조기 reach) grounding**(N1 temporal)이 그 전제를 해소.
- **persistence(그림 b)**: velocity-commitment window **~0.3s**(delay 0-5 capture alive + lane clear, delay6 붕괴). 그림 = (a) capture-clearance Pareto (b) persistence curve (c) capture-travel vs engage 전제.
- **캐비앗(plan §18)**: engaged 경계(20m 이진 open)는 보수적, optimistic(cone launch)은 낙관 — 진실은 사이(부분개방 cone 0.74m@11m), 그 gap이 곧 전제. seed 1개(일반화 미검). "impossible" 금지 → "tested solver가 engage 전 유효 포획 미확인/전제 미해소". Case-B 공식 judge 승격 = **engaged gate 통과 시에만(현재 미통과)**.
- **다음(선택)**: ⓐ **N1 temporal grounding**(net 조기 reach 검증 → 전제 해소; 성공 시 Case-B 승격→Move C corridor 두껍게) vs ⓑ 병행 **Move A**(net/kill 반경 co-design η>1, engage-무관 경로). 사용자 지시 대기.

### 2026-07-19 (dddd) — ✅ Terminal operating-envelope map (plan §9-10): safe cell 0/25(θ=0.9, η 0.38–2.08) + θ-slice → 장벽 = **2요인(radius ratio η × capture-quality θ)**, 단일 η 아님

- **채택**: 외부 plan(deployment_safe_capture_operating_envelope) 확인·실행. 산출 = `shepherd/scripts/c1_envelope.py` + `results/c1_corridor/c1_envelope.json`. Case A(순간기하 지배) = (xxx) drop-one으로 확인(발사 시 boxer 제거→v_soft 붕괴) → 기하 필요조건 r_kill≥r_net_eff tight.
- **terminal map**(seed 1100 eligible 고정, 4-limiter placement CEM, kill_radius=r_kill 가변, v_soft≥θ∧p_feas>0∧lateral clear≥r_net_eff): (r_kill,r_net_eff) 5×5 그리드(α∈{.6,.8,1,1.2,1.4}) **θ=0.9서 safe 0/25** — η=2.08까지도 미발견. 단 terminal clear는 dynamic보다 나음(known boxers terminal −0.42m vs G3 dynamic −1.85m; G3 −1.85 = post-fire 추격 = plan §12 dynamic barrier).
- **θ-slice(plan §14.1, 결정적)**: (r_kill2.4/r_net1.79, η1.34)서 θ 0.9~0.6 safe 없음 → **θ=0.5서 safe-eligible 열림(mcap .28)**; 현재점(η0.89) 어떤 θ도 안 열림. **⇒ η>1 = 필요조건이나 불충분; capture-quality(θ + 얇은 cone)가 2번째 결속.** 안전=η>1 AND θ 완화 동시. 현 grounded 점(η0.89·θ0.9) = 두 축 모두 밖.
- **refined finding(논문)**: crowding 기반 net-capture shaping의 deployment-safe operating envelope는 **kill/net 반경비 η와 capture-quality θ(cone)에 의해 공동 bounded**; 현 설계점은 밖. plan의 단일-η 경계보다 정확(2D envelope). = [[project_moat_disclosure_strategy]] (b) 작동영역.
- **캐비앗(plan §18 규율)**: placement CEM noisy(특정 셀 방향성만; 2.8/1.34가 θ.5서 미개방 = 탐색 분산). 깔끔한 논문 그림엔 **analytic 경계(r_kill≥r_net_eff + cone-masking 조건) + 검증된 solver** 필요(plan P1-P2 정련). "impossible" 표현 금지 — "tested solver 미발견/envelope 밖".
- **다음(선택)**: ⓐ envelope 정련(analytic 경계 유도 + solver 강화 + θ×η 2D heatmap = 논문 Figure 3) vs ⓑ 현 확보분으로 학회 논문 집필 착수(L0 학습+hybrid 포획+E1 회랑+grounded 제약+envelope 방향성). 산출 = c1_envelope.py·c1_envelope.json.

### 2026-07-19 (cccc) — ✅ G3 판독: **NOT_FOUND_UNDER_TESTED_G3 확정 — compress-clear Pareto가 disjoint·구조적**(kill_radius≈net_radius) → task-design 민감도 = usability envelope 결과

- **결과**(서버 `cc71495`; local warm seed1100 + cold 광역 13seed): **양 arm best_tier=2·n_tier4plus=0.** capture 잡은 전 해(Tier 2)에서 **m_clear −1.85~−2.28m**(안전선 m_clear≥0까지 ~2m 갭 = near-miss 아님); **수천 rollout 중 E_capture∧E_lane 동시 만족 = 0.** cold 절반은 capture 미도달(Tier 1, warm 없인 얇은 회랑 못 찾음).
- **판정**: CEM에 전 horizon(pre-fire 압축+post-fire 비우기) 자유를 줬는데도 0 → **제어 전략 한계 아닌 구조적**. **compress–clear Pareto가 disjoint.** 원인 = **kill_radius(2.0)≈net_radius(2.24)**: 탈출을 막을 만큼 가까운(≤kill_r) limiter는 필연적으로 net lane(≤net_r) 안. "압축할 만큼 가까움"="net에 걸림"이 파라미터에 내재. (m_clear −2 → 전개창 중 최악 limiter가 축에서 ~0.6m = post-fire 공격자 추격이 축으로 수렴.)
- **발견(논문 자산)**: "crowding 기반 capturability 제조 협력 shaping은 kill_radius≈net_radius regime에서 **deployment-infeasible**(친사 교차 불가피)." E1(추상 모델 회랑 실존) + 이 grounded 제약 = 자기완결 finding. [[project_moat_disclosure_strategy]] (b) 작동영역 산출물 직결.
- **다음(리뷰 §15·doctrine 분기 — 종결 아님)**: **task-design 민감도 스윕** = kill_radius / net_radius(및 비율)·finisher standoff·θ·horizon을 변화시켜 **compress–clear가 양립하는 regime(operating envelope) 지도** 산출. 저비용(기하 + 몇 파라미터점 G3 재평가). = usability envelope 결과 = 두 학회 논문 그림 재료. MARL 필요성/일반화는 그 위에서 재개.
- **논문 정합(현 스코프)**: 항우 학회 = 문제·그물물리 접지·회랑 존재/제약·operating envelope(방어/GNC); AI 학회 = MARL 협력 shaping·hybrid·회랑 존재(학습). 현 확보분(L0 학습+hybrid 포획+E1 회랑+grounded 제약+envelope 스윕)으로 두 편 자기완결.
- 산출 = results/c1_corridor/{g3,g3_cold}/c1_g3_search.json.

### 2026-07-19 (bbbb) — ✅ G3 deployment-aware CEM 구현 (net-lane clearance + safe-fire 분리 + 5-tier) — 배선 스모크 green(E1 winner=Tier 2 확정), 본 탐색 = 서버 대기

- **채택**(외부 "G3 decision"): G3 즉시 착수 + human-lane 병행. 산출 = `shepherd/scripts/c1_g3_deploy.py` + `tests/test_c1_g3.py`(6 green, E1 winner=Tier 2 통합락 포함).
- **분리 판정(리뷰 §5, 기존 predicate 불변)**: E_capture=1[v_soft≥θ∧p_feas>0](동결) / **E_lane=1[m_clear≥0]**(신규 safety; m_clear = 전개창 [t_f,t_f+n_dep] 내 min_i,τ[perp_to_axis − R_lane − r_body]) / E_safe=E_capture∧E_lane. **R_lane = grounded directional net reach(G2 기본 2.24m, (aaaa))** — crude tube 아님. net 축/apex는 발사 시점 동결.
- **5-tier lexicographic verdict(리뷰 §10)**: 0 invalid/1 progress/2 shell-reached-lane-unsafe(=seed 1100)/3 lane-safe-noshell/4 safe-fire/5 safe-capture. 구성적 양성 = **Tier≥4**. 연속 M_capture·M_clear로 tier 내 ranking. score_g3 lexicographic 락(테스트).
- **탐색(리뷰 §8·§9)**: role-agnostic knot-CEM + **E1 winner warm-start**(seed 1100, near-miss 보존) + release-window δu. seed 대역 340M(전 legacy·CEM 330M·corral/robust 331/332M 서로소, 락). G1(optimistic early·tag)/G2(grounded directional·primary)/G3(conservative +body+buffer·soft) 밴드.
- **스모크(샌드박스)**: baseline = E1 winner seed 1100 → **tier 2·E_cap True·E_lane False·m_clear −2.16**(grounded net lane 깊숙이 = (aaaa) 정합, 계기 정상) / search warm-start·배선 green. **본 탐색 = 서버**: 압축(sliver 형성)하면서 net lane을 비우는 compress–release–fire 회랑 존재 여부. Tier≥4 = 구성적 존재; 미발견 = NOT_FOUND_UNDER_TESTED_G3_SOLVERS(부재 증명 아님 → task-design 민감도).
- **캐비앗**: r_body=0.2 **PLACEHOLDER(human-lane)**; R_lane G2 grounded directional max; temporal folded→open transient·tether 미해결(병행). warm은 seed 1100 전용 강prior(타 seed 약prior) → 1차 런 = seed 1100 집중(작은 σ·깊은 iters)이 release 수정 탐색에 유리.
- **서버 런북**: pull→REQUIRED_COMMIT→torch-free pytest(test_c1_g3 6 green)→baseline 확인→**1차: `--stage search --seed0 1100 --draws 1 --knots 6 --pop 64 --iters 40 --sigma0 3 --t-open 32 --warm-cem results/c1_corridor/cem_warm/c1_cem.json --warm-seed 1100`**(seed 1100 release 국소 탐색)→미발견 시 cold 광역(`--draws 12 --sigma0 10`)→판독(best_tier·n_tier4plus). ntfy·OMP2·nice10·TMPDIR=/data. 산출 = results/c1_corridor/g3/c1_g3_search.json.
- **다음(방향)**: 서버 G3 탐색 → [Tier≥4] safe corridor → fresh-CRN·temporal/tether 재평가 → bank 확장 / [미발견] capture–clearance Pareto·민감도(리뷰 §15). human-lane(temporal·tether·body·mission-cost) 병행.

### 2026-07-19 (aaaa) — ✅ AI directional-silhouette G0/G1/G2: grounded net reach로 friendly-fire **Case C 확정(unsafe)** — boxer 전원 net 측방 도달 범위 안 (net_forward.py 실측)

- **실행**(`shepherd/scripts/c1_net_silhouette.py` 재사용; net_forward.py = Xu Drones 9:190 grounded, baseline θ45/v60/35g): deployed net(engage 20m) **측방 support**: max **2.24m**·p95 2.15·p50 1.67·equiv-area 2.00; **방향별 6섹터 2.09~2.24m = 거의 등방(thin escape 방향 없음)**. 등가면적 2.0 가정보다 실 max 도달 2.24m로 오히려 큼.
- **temporal(N1-flagged, 지시적)**: R_equiv vs travel — travel 5~7m(=boxer 축 범위)서 **2.9m**, 20m서 2.0m로 balling 축소. 조기 큰 값은 flat-init 과대(n1 D-notes) → engage(20m·2.0–2.24m) = 앵커값. **어느 grounded 읽기도 boxer가 clear 안 됨**: 최소 grounded R(2.0)서도 L0/L2 내부, directional max(2.24)서 전원 내부; 조기 추정(2.9)은 더 나쁨.
- **판정 = Case C(unsafe) grounded 확정**: seed 1100 boxer(축외 1.82~2.16m)가 **grounded net 측방 도달(2.0~2.24m) 안** — 친사 교차가 crude 2m tube가 아니라 **Xu-grounded net silhouette로 실증**. (zzz-1) "심각도 밴드"의 상한이 grounded로 굳음. deconfliction (zzz) 불충분·on-axis 압축 내재 결론 유효.
- **verdict 라벨 갱신**: E1_SURROGATE_EXISTS=TRUE · E1_GROUNDED_CONE_EXISTS=TRUE · **FULL_DEPLOYMENT_CLEARANCE=RISK(Case C grounded)** · DIRECTIONAL=등방 해소(thin 방향 없음) · TEMPORAL=조기 folded→open transient만 남은 escape(flagged·human-lane, 단 available sim은 조기 더 큼) · TETHER=미해결(추가만).
- **남은 human-lane(리뷰 §10)**: 조기 전개 folded→open transient(net이 boxer 지날 때 진짜 크기)·tether·body clearance·mission semantics(리뷰 §2: **core intersection = capture physics 무효 = hard**). 단 grounded 앵커는 이미 Case C라 이들은 정밀화(뒤집기 아님).
- **함의**: post-fire 패치 불가 + grounded 친사 교차 확정 → **deployment-aware corridor search(compress-off-axis / net-lane 사전 clearance) 필요**. 실 shaping = 압축∧정렬∧lane-clearance 동시 = compress–release–fire = 더 상태의존 → MARL 강화(리뷰 §12). E1 corridor 폐기 아님(warm-start/near-miss 재료).
- **다음(방향 결정)**: **G3 deployment-aware CEM** 착수(objective = capture∧shell∧**core net-lane clearance(hard)**∧nominal margin(soft), role-agnostic knot, net_forward 측방 도달로 lane 정의) vs 그 전 human-lane(temporal transient·tether·mission-cost) 확정. 산출 = results/c1_corridor/c1_net_silhouette.json.

### 2026-07-19 (zzz-1) — (zzz) 정정: net envelope는 **이미 N1-grounded**(docs/n1_net_grounding.md) — friendly-fire "미grounding" 과잉 철회; 심각도 = grounded 상한(bites)~미해결 directional/temporal extent 밴드 + G0 scoping

- **정정(리포 확인)**: `docs/n1_net_grounding.md`가 capture cone을 Xu Drones 9:190으로 grounding 완료 — **half_angle 3.8°(0.067)·net_radius 2.0m(=√(S_NP/π), S_NP 12.54㎡ 논문 baseline)·range 29.8m** = 구 tuned(0.43/40/1.5) 대체. ⇒ friendly-fire **narrow = grounded capture cone**, nominal/conservative(tube=net_r 2.0)도 **grounded net_radius 기반**. (zzz)·(yyy)의 "미grounding envelope 위 razor predicate 함정" 표현 **과잉 → 철회**(capture-viability 메모리의 "cone UNGROUNDED"는 2026-06-26 stale — 이후 N1 grounding 됨).
- **단 남은 피벗 미지수(진짜 human-lane/flagged)**: ① **net_radius 2.0 = 등가면적 disk, worst-case inradius 아님**(n1 caveat 1) — 실 directional silhouette support는 방향별 상이(deployed ~2.0 ↓ balled silhouette min 0.92㎡≈0.54m); net_forward.py `silhouette_area(X,·,n_hat)`로 방향별 계산 가능하나 deployment-state 의존 ② **deployment 시간-전개**(radius growth·forward travel) = N1에서 **NOT validated 플래그**(hang time 미재현·collapse timing 신뢰불가) ③ **tether = net 모델에 부재** ④ body clearance·mission semantics.
- **friendly-fire 심각도 = 밴드(정확 표현)**: **상한**(fully-deployed 등가 2.0m 원판) → boxer(off-axis 1.8–2.2m)가 경계/내부 = **bites**; **하한**(작은 directional/early-deploy extent ~0.5–1m) → **clear 가능**. **grounded 상한은 unsafe, 피벗 = net directional+temporal extent(N1 flagged·human-lane).** deconfliction (zzz) 결론(post-fire 패치 불충분·on-axis 압축 내재)은 상한 기준 유효.
- **G0 scoping(리뷰 §7 Phase G0 정밀화)**: (i) **이미 grounded** = capture cone·net 등가반경 (ii) **AI-computable** = deployed net **directional silhouette support**(net_forward.py, boxer 방향) → fully-deployed 상한 확정 (iii) **human-lane/flagged** = deployment 시간-전개·tether·body clearance·mission semantics(core=hard/buffer=soft/post-capture=cost). G1/G2/G3 밴드 = inradius(하한)/등가면적(nominal)/등가+tether버퍼(상한).
- **verdict 라벨(리뷰 §3)**: `E1_PHYSICAL_UNDER_SURROGATE=TRUE`(유지) / `DEPLOYMENT_CLEARANCE`= grounded 상한 UNSAFE·directional 하한 UNRESOLVED / `REAL_NET_VALIDITY=PENDING`(directional+temporal grounding).
- **권고**: 결정적 AI 스텝 = net_forward.py로 deployed 방향별 silhouette support 산출 → boxer 방향 net extent bound → friendly-fire 상한 verdict를 physics로 확정(등가면적 2.0 대신 실 directional). temporal 전개·tether = human-lane. 그 후 mission-cost 확정 → deployment-aware CEM. **대기 = 방향 결정: AI directional-silhouette G0 먼저 실행할지 vs human-lane temporal/tether 입력 먼저.**

### 2026-07-19 (zzz) — post-fire deconfliction 3-arm 테스트: **불충분(realistic envelope 전부 잔존 교차)** — 친사 교차는 on-axis 압축의 내재 산물, post-fire 패치 불가 → deployment-aware 필요; 단 envelope 미grounding 경고 (리뷰 §6·§9)

- **실험**(`shepherd/scripts/c1_deconflict.py` 재사용; seed 1100, 발사 후 limiter 제어를 3-arm으로 교체, 전개창 [11,19] envelope 3종 clearance + containment proxy): 
  - narrow(surrogate 3.8°): cem_tail **−0.07** → radial **+0.02**(간신히 clear)·hold −0.01·lateral_behind −0.03.
  - **nominal(10.3°)·conservative(+tube 2m): 전 arm 여전히 교차** — nominal −0.54~−0.68·conservative −1.65~−1.73. **가장 싼 post-fire 해결책은 realistic envelope 미해결.**
  - containment proxy vmin=**0.000 전 arm(cem_tail 포함)** = frozen-commit 모델선 post-fire 동역학 장식적(비판별) — 진짜 판별엔 deployment-dynamics 모델 필요.
- **근본 원인**: 친사 교차 = **on-axis 압축의 내재 산물** — boxer가 sliver를 만들려 공격자(net 축 위)를 ~2m 근방까지 에워쌈 → **발사 시점에 이미 net lane 안**. post-fire arm은 전개창 8스텝(~0.4s)·내부에서 출발이라 −1.7m를 못 비움. **post-fire 패치로 해결 불가 확정** → 압축 자체를 off-axis/lane-clear로 바꾸는 **deployment-aware corridor search(compress–release–fire)** 필요(리뷰 §9). = 더 상태의존 협조 → MARL 프레이밍 강화(리뷰 §12).
- **⚠ 결정적 경고(리뷰 §7)**: nominal/conservative 심각도는 **전적으로 미grounding net 기하의 함수**(cone half_angle 0.067·range = tuned surrogate; net grounding = Xu Drones 9:190 = WP-A4/CP-4 **human-lane** [[capture-viability-novelty]]). **미grounding envelope 위에 deployment-aware CEM을 세우면 리뷰가 경고한 새 razor predicate 함정.** narrow(모델 자체 cone) 한계성(−0.07)은 grounding 무관하나, nominal/conservative는 N1 grounding 선행 필요.
- **권고**: deployment-aware CEM 재설계 **전에 net 전개 envelope를 N1/Xu로 grounding**(human-lane)해 친사 clearance 기하를 물리화. 2-track: (human) net envelope grounding / (research) compress-off-axis 방향 기록. E1(현 추상 모델 실존) 유지 — "기존 corridor는 deployment-aware friendly-clearance에서 unsafe(surrogate 한계·realistic 명확)". **회랑 폐기 아님.**
- **대기 = 방향 결정(Hyunjun)**: ⓐ ground-first(net envelope N1 grounding 후 deployment-aware CEM — 권고) vs ⓑ redesign-now(미grounding surrogate로 바로 deployment-aware CEM). 계층형 mission-cost(core=hard/buffer=soft/post-capture=cost/conservative=tag)는 grounding 후 확정. 산출 = results/c1_corridor/c1_deconflict.json + c1_deconflict.py.

### 2026-07-19 (yyy) — 외부 리뷰 채택: boxer/shaper = 사후 라벨 정정(형태 고정 금지) + **friendly-fire Tier-1 진단: seed 1100 회랑이 net 전개창에서 아군 간섭 — 전 envelope RISK** (gate 아님·mission-cost 결정 대기)

- **정정 1 (boxer/shaper)**: 정책 역할 아님 = trajectory ablation의 **사후·시점 국소 기능 라벨**. 해석·clustering·warm-start에만; **corridor 생성·정책 구조 제한 금지, 역할은 상태 의존 창발 유지**. docs/25 (xxx) "role×phase 축으로" 과잉 철회 → role×phase = 여러 proposal 중 하나(warm-start), bank 생성기 = role-agnostic knot-CEM(비대칭·phase 표현 가능하면 족함). MARL 역할 하드코딩 금지.
- **정정 2 (friendly-fire 갭)**: 포획 모델은 limiter를 **오직 공격자 kill-radius no-go로만** 반영 — net 발사에 아군 limiter 걸림/경로 차단/얽힘 **미검사**(se3_cone은 공격자 끝점만 cone 대조). 실 시스템 타당성을 바꿀 수 있는 모델 갭.
- **✅ Tier-1 기하 진단**(`shepherd/scripts/c1_friendly_fire.py` 재사용; net 전개창 [t_fire, t_fire+round(τ/dt)=8], envelope 3종: narrow=현 cone 3.8° / nominal=atan(net_r/axial) / conservative=nominal+tube net_r): **seed 1100 = 전 envelope RISK** — narrow **min clearance −0.07m**(L0, cross@13)·nominal −0.68m(cross@12)·conservative −1.72m(cross@11). seed 1106도 전 RISK. **발화 순간엔 off-axis 16–23°(안전)였으나, 발사 후 limiter가 계속 공격자 추격 → 전개창 내 net lane 진입.** = CEM 개방루프가 net-lane clearance를 배운 적 없음(친사 벌점 부재).
- **판독(리뷰 §10 정합)**: E1(현 모델 물리 실존)은 유지 — 이건 **verdict 아닌 diagnostic**. 그러나 현실 net envelope에선 현 회랑이 친사 교차. → 실 shaping 문제 = **압축 ∧ net-lane clearance ∧ terminal alignment 동시** = compress–release–fire 시간 협조(고정 brake·대칭 corral·단순 개방루프보다 훨 상태의존) → **MARL 필요성 오히려 강화 가능성**. **회랑 폐기 아님·hard gate 즉시 추가 금지**(근거 없는 새 razor predicate 위험).
- **대기 = mission-cost 결정(Hyunjun, 리뷰 §9)**: 친사 얽힘의 임무 의미 = (a) 절대 금지(hard constraint) / (b) 포획 성공+비용(R−c_friendly) / (c) 접촉 허용·회수 가능(과보수 불요). limiter 소모성 vs 보존 우선·finisher 비파괴 우선순위에 연결. **결정 후에만** gate/cost 승격. 그 전 = 진단 태그만 bank metadata.
- **다음(순서, 리뷰 §12)**: ①정정 기록(**완료**) ②친사 clearance 진단(**완료 — seed 1100/1106**) ③plausible envelope 2–3(**완료**) ④태그 기록(**완료**) ⑤**mission-cost 의미 결정(Hyunjun 대기)** → 그다음 nominal envelope 안전이면 bank 확장 계속 / 대부분 unsafe면 deployment-aware corridor search(compress-release-fire)로 수정. 산출 = results/c1_corridor/c1_ff_{1100,1106}.json + c1_friendly_fire.py.

### 2026-07-19 (xxx) — ✅ ③-lite seed 1100 회랑 해부: **3 boxer + 1 shaper·2-phase 비대칭 구조** 규명 → bank builder role×phase 저차원 parameterization (docs/25, 재사용 스크립트 c1_dissect.py)

- **채택**(외부 권고): ② bank 확장 전 ③-lite 먼저 = seed 1100 1회 해부로 search space 설계. 산출 = `shepherd/scripts/c1_dissect.py`(재사용·③-full clustering 재활용) + `docs/25` + `results/c1_corridor/c1_dissect_1100.json`.
- **기전**: 회랑 = feasible set을 sliver(≈3/2000)까지 압축하되 잔여가 전부 net cone에 정렬되는 **단일 프레임 knife-edge**. t≤9 압축(p_feas 1.0→0.18·v_soft 낮음) → **t=10 v_soft 1.0 점프 + p_feas 0.0016**(cone 정렬) → t=11 완전 boxed. 공격자 직진(pre-commit dodge 없음).
- **역할(t=10 drop-one, all4 p_feas .0016/v_soft 1.0)**: L0/L1/L2 = **BOXER**(제거 시 Δp_feas +.07/+.10/+.22·v_soft 붕괴 = reachable set을 cone 안으로 압축) / **L3 = SHAPER**(Δp_feas +.002=bulk boxing 아님이나 제거 시 v_soft 1.0→0.444 = 잔여 sliver를 cone에 trim·정렬). **비대칭 3+1** — corral 대칭 편대엔 없는 역할.
- **phase(공격자 프레임 radial/tangential)**: Phase1 compress(t≤9, 전원 radial +12~+22 접근 + tangential 16~35 선회) → **Phase2 brake-and-shape(t=10 mean-radial flip)**: L0/L1/L2 radial −30/−7.5/−26 급제동·tangential 붕괴, **L3만 tangential 23.1 유지=채널 성형**.
- **corral vs CEM 결정 차이**: corral best 동일 seed **eligible 0** — p_feas 높/v_soft 낮 → 곧장 boxed(clean 창 건너뜀). shaper 부재. **CEM = brake-3+shape-1 비대칭으로 창 관통.**
- **bank builder parameterization(권고)**: blind 288-dim → **role×phase 저차원**: discrete(shaper 1개=4택)+ Phase1 boxer approach/tangential gain + τ_switch + Phase2 boxer brake gain·**shaper channel angle(cone 기준)** = 연속 ~6–10 dim. CEM winner warm-start + fresh-CRN 게이트. → ② bank builder(winner-local restart·near-miss-mean·저차원 knots)의 축.
- 캐비앗: 단일 seed 구조(다른 seed 동일 3+1 여부·cluster 수 = ②에서)·drop-one 근사(상호작용 미분리)·직진 전제(R3 속도특이 정합). **다음 = ② corridor bank builder(서버) 구현**(role×phase param·fresh-CRN 게이트·replay·dedup) → ③-full clustering.

### 2026-07-19 (www) — ✅ fresh-CRN 검증(권고 §9): seed 1100 = **진짜 thin 회랑(300/300)**, seed 1106 = CRN artifact(14/300) → 견고 E1 = 1/10(포획까지)·1106 격하; 16절 권고안 실행순서 채택

- **검증**(샌드박스 torch-free, 승리 shell state 고정·MC seed만 300 fresh 스윕 = 동역학 결정론이라 물리 불변·측정만 변): 
  - **seed 1100 @ t=10**: v_soft 1.000(min 1.0 전 300) · **P(p_feas>0)=300/300** · p_feas mean 0.00163·median 0.00160(타이트) → **frozen-CRN 우연 아님 = 실제 물리적 thin-feasibility. E1 견고.**
  - **seed 1106 @ t=11**: v_soft mean 0.99(**min 0.0**) · **P(p_feas>0)=14/300(4.7%)** · p_feas median 0 → **eligibility 대부분 frozen-CRN 산물 = near-miss로 격하.**
- **정정: 견고 E1 = 1/10(seed 1100, nominal→shell→자율포획)**, (vvv)의 "2/10"에서 1106 제외. 구성적 존재 1개면 충분. 회랑 = 진짜지만 **razor-thin(p_feas≈3/2000)이되 MC-robust**. **측정 규율 성과: 진짜 회랑 vs CRN-razor artifact 분리** — bank 확장 시 이 fresh-CRN 게이트를 admissibility 조건으로 승격(frozen eligible만으론 불충분, 1106 교훈).
- **16절 권고안(외부) 채택 = 실행 순서(§14)**: ① fresh-CRN 재평가(**완료**) → ② 제한적 CEM bank 확장(서버; 20–30 traj·≥5 seed·≥2 geometry cluster·replay 검증·dedup·**fresh-CRN 게이트**·§8 기법: corral warm 다양화·winner-국소 restart u=u_winner+δu·near-miss-as-mean·nearest-winner warm·저차원 param·geometry clustering) → ③ 회랑 기하·limiter 역할 분석 → ④ BC 웜스타트(state-conditioned·시간 memorization 금지·role/ID 유지·train/val 분리) → ⑤ **실궤적 backward curriculum**(nominal 성공궤적 t=T-1→0 후진, synthetic 아닌 on-manifold — (qqq) d1수확이 못 준 것) → ⑥ guard 고정 MARL fine-tune(L=L_PPO+λ_BC·L_BC, λ_BC↓0) → ⑦ unseen nominal seed 폐루프 평가 → ⑧ PD·brake·open-loop·online MPC 비교(MPC = 강 baseline) → ⑨ speed 18/22 domain expansion → ⑩ A3 cost-aware.
- **MARL 필요성 = 정당한 질문으로 재개방(확정 아님)**: open-loop CEM pointwise 성공·PD 실패(R4)·learned feedback 미검. 강 증거 조건 = unseen seed 일반화 ∧ PD/MPC/brake 유의 우위 ∧ 역할 분화. **핵심 지표**: P(capture|unseen seed)·P(capture|v_A≠20)·P(capture|perturb)·P(shell)·P(fire|eligible).
- **연구 질문 재정의**: (물리 실존? = **Yes**) → "특권 optimizer가 찾은 thin nominal 회랑을 **일반화 폐루프 multi-agent 정책**이 여러 seed·attacker에서 안정 생성하는가" = 원 양치기 MARL 질문 직결. doctrine 축1 positive-mechanistic 분기 확정(진단 아님). 다음 = ② CEM bank 확장(서버).

### 2026-07-19 (vvv) — ✅ C-1 CEM 완주: **E1 회랑 실존 확정** — nominal→shell 접근 회랑을 특권 solver가 구성적으로 발견(2/10 seed·1건 자율 포획), (qqq) "회랑 미검" → **존재로 전환**

- **실행**(서버, `2abf370`; warm=corral best 웜스타트 / cold=중립, 각 10 draws·knots5·pop48·iters24·t_open24): 
  - **cem_warm: SHELL_REACHED 2/10** — **seed 1100 = 자율 포획(LOCAL_CAPTURE, stop=capture)**, seed 1106 = shell 도달(무포획). 둘 다 replay=True(반환 best_acts 재현 검증).
  - cem_cold: 0/10 → **웜스타트(corral boxing basin 근방)가 결정적**; 중립 출발은 예산 내 미발견.
- **회랑 구조(궤적 실측)**: seed 1100 = len 21·first_eligible t=10·fire t=11·**penetrated False**; eligible 창 = **단일 프레임(t=10): v_soft=1.000 ∧ p_feas=0.0016**(≈3/2000 MC). seed 1106 = t=11 단일 프레임 v_soft 1.0·p_feas 0.0004. **= far/boxed 면도날의 바늘구멍을 실제로 뀀**: v_soft를 1.0까지 올리되(보통 boxing→p_feas 0) p_feas를 razor-thin 양수로 동시에 유지. 승리 궤적 obs+acts 저장됨(= on-manifold 회랑 reference).
- **강건성(robust R1–R4, warm 2 winner)**: R1 exact replay 재현 ✓(Mjoint 0.160/0.040) / **R2 action-noise basin 실존** — σ0.5→7/8·8/8, σ1.0→4/8·8/8(단일-프레임 우연 아님, 행동공간에 실 basin) / **R3 attacker-speed 특이적** — 18·22에서 전부 실패(개방루프가 nominal 속도 20에 튜닝) / **R4 feedback 미실현** — 기록 reference를 obs-only PD로 추종하면 shell 유지 실패. E2(corral fresh-band 1200+) = 0/50(스크립트 미일반화 재확인).
- **판정 = E1 확정(pointwise, ≥2 nominal seed·1건 포획)**. **(qqq) "nominal 접근 회랑 미검/무발사 = transfer 실패" → "회랑 실존, 기존 실패는 controller·curriculum·search 한계"로 전환**(doctrine 축1 성공 분기·positive-mechanistic). 단 회랑은 **thin(단일 프레임·p_feas~1e-3) + 속도-특이 + PD-hard** = "privileged-feasible but closed-loop-hard" → **학습(폐루프 MARL)의 정당성 복원**(원 질문 재강화: open-loop/PD가 못 잡는 thin state-dependent 회랑 = 학습이 메울 자리).
- **다음(제안 형식)**: ①병목 = 회랑 실존하나 thin·속도특이·PD-hard → **폐루프 컨트롤러/정책이 이 창을 seed·속도 넘어 안정 도달** ②최소 실험 = CEM 승리 궤적 2건을 reference로 (a) corridor-aware 커리큘럼(eligible 창에서 후진 = rewind이나 이번엔 **nominal-도달 실궤적**) or (b) imitation 웜스타트 후 폐루프 미세조정; 선행 = CEM 확장(draws↑·iters↑)으로 회랑 bank 크기·nominal 커버리지 측정 ③성공 시 = 다수 nominal seed 폐루프 자율 포획 = 원 질문 긍정 답(MARL이 open-loop 못하는 폐루프 성형) ④실패 시 = "controller realizability gap" 정량화 → task-design 민감도(θ·R_net·T로 창 두껍게). 
- 산출: results/c1_corridor/{cem_warm,cem_cold,c1_robust,robust_cold}. 회랑 reference = cem_warm best_trace(seed 1100·1106). discovery → E1 양성이므로 다음은 confirmation 설계 가능.

### 2026-07-19 (uuu) — C-1 baseline+corral 클라우드 실런 완주: **NOT FOUND UNDER TESTED SOLVERS(스크립트 계열)** — clean 회랑 미발견·far/boxed 이중 벽 정량화 → CEM(서버) 대기

- **실행**(샌드박스 torch-free, 정본 클론 `50f880c` + 로컬 오버레이): baseline 6-arm × 100 seed + corral 160 config(screen 10) → top-5 × 100. 산출 = `results/c1_corridor/c1_{baseline,corral}.json`. seed = reset 1100–1199. ⚠ 1차 nohup 런은 세션 갭에 컨테이너가 회수(자원 무관 — 디스크 29%·메모리 7GB 여유); setsid 재실행으로 완주. **교훈: 샌드박스 장시간 백그라운드 잡은 세션 갭에서 소멸 → 무거운 스테이지(CEM)는 서버.**
- **결과 — 전 solver clean shell 0**:
  - baseline zero/brake/lam20/attpd×3 = **전부 shell 0/100**; feasibility 열린 구간 v_soft(M_v_given_pfeas) 천장 **0.239**(θ=0.9), boxed 0 → 단순 제어는 shell에서 **멀리**.
  - corral **0/160 config**가 clean shell 도달·**0/160 guard 발사·0/160 eligible(M_joint 유한 0)**; M_v_given_pfeas 전역 max **0.224**(baseline보다도 낮음); **39/160 config가 boxing**(max 31스텝) — 단 boxed = p_feas 0 = eligible 아님; penetrated 평균 0.91.
- **판독 — far/boxed 이중 벽**: 166개 스크립트 컨트롤러(6+160) × (100/10 seed) 어느 것도 clean eligible 집합(v_soft≥θ ∧ p_feas>0)에 **한 번도 진입 못 함**. 이분법 = ⓐ 관통 허용(feasible이나 v_soft ≤0.24로 threshold 한참 아래) ⓑ 가두기(v_soft는 오르나 p_feas→0). **clean shell = 둘 사이 바늘구멍**, 스크립트 편대는 못 뀀 = 측정기가 잡으라고 설계한 boxed-vs-clean 면도날의 실증. **부재 증명 아님**(infeasibility certificate 없음) — 리뷰 규율상 강한 solver(CEM) 전 "not found" 라벨 한정.
- **다음 = CEM 서버**(개방루프 직접최적화 = 스크립트가 못 뀐 바늘구멍을 seed별로 최적화; knot-param·clean-margin 목적·A2 폐루프 내부). 커맨드: `python -m shepherd.scripts.c1_corridor_probe --stage cem --draws 20 --knots 5 --warm-from results/c1_corridor/c1_corral.json --out-dir results/c1_corridor`(warm = corral 최고=press2_block2 boxing basin이라 clean 방향 탈출 유도; stall 시 cold `--warm-from ""`·knots↑·t_open↑). CEM도 shell 0이면 → task-design 민감도(θ·R_net·T). doctrine: 어느 결과든 개발 분기, 진단 종결 아님.
- discovery 기록: E1 미발견(스크립트). 성공 궤적 snapshot 대기(CEM E1 시). 커밋 대기 = c1_{baseline,corral}.json + 본 로그.

### 2026-07-19 (ttt) — C-1 프로브 3자 리뷰(조건부 승인) 채택 → v0.2 (docs/24 채택표·docs/23 v0.2) — 20 tests green·snapshot 2-tier err 0.0

- **리뷰 판정**: 연구 설계 통과 / 구현 사전검증 **조건부 통과** — "limiter-only·고차원 open-loop CEM·불완전 snapshot·RNG namespace 구멍 때문에 '못 찾았다'의 증거력이 약해질 수 있다"는 핵심 지적. **8대 필수 + 보강 전항 채택**(docs/24 채택표).
- **8대 필수 반영**: ① **finisher scope 정정** — 이 env finisher = 고정 런처(translation 부재 = S1 설계)이나 **pointing(n_F)은 v_soft 진입** → default finisher `point_at_attacker`로 DOF 개방(구 axis=[0,0,0] hold는 도달성 과소평가); "full defender control = limiter×4 + finisher pointing", translation 부재는 scope 한계로 명시(물리 불가와 구분) ② **4단 verdict** SHELL_REACHED/GUARD_FIRED/LOCAL_CAPTURE/MISSION_CAPTURE(1차 증명 = shell 도달, CEM 조기종료도 shell) + **E1/E2/E3 사다리**(회랑 1개 = E1 pointwise, mission solvable 아님) ③ **seed namespace 넓힘** 330M/331M/332M + `cem_seed(reset,restart)` 구조 인코더 + budget assert(구 330000+draw=corral 331000 충돌 해소) ④ **"Markov-complete" 철회 → 2-tier**(seed replay + pre-commit reset_to; 스모크 **tier1 err 0.0 · tier2 err 0.0/13스텝** = 정확 on-manifold predecessor 생성 실증) ⑤ **knot-CEM**(K knots→t_open, dim K×12; corral warm-start·계층) ⑥ **lexicographic score**(capture>shell>joint>dwell>delay; boxed<clean 잠금) ⑦ 같은-timestep·pre-penetration eligibility 잠금 ⑧ **CEM winner=반환 best_acts**(argmax score_vector·replay 검증).
- **측정 3값**: M_v_given_pfeas(개명)·M_p_given_vsoft·M_joint(scale-정규화 s_v .1/s_p .01) + single-frame vs sustained + p_feas 단일표본 exploit 대응(raw 저장·R1 exact·fresh 재평가). robust R1–R4(exact/basin/attacker/**R4 feedback realizability** = PD가 reference 추종 시 shell 유지 = curriculum basin).
- **검증**: `test_c1_corridor.py` **20 green(2 env-integration 포함**: determinism·guard 일관성·snapshot 2-tier·verdict nesting) + 회귀 pfc/env_m3/a3_reverse/viability 68 green. 스모크: baseline(point/hold) 정상 · corral boxed 8–10스텝(near-miss 포착·발사 0) · CEM knot 배선 정상 · **snapshot restore 2-tier 실측 err 0.0**. **미커밋** — Windows `git reset`→push 후 서버 pull.
- **미채택 0**(finisher translation만 S1 구조적 불가 → pointing 개방으로 등가). 캐비앗: knot-CEM 근사(near-shell 미도달 시 full-seq refine이 다음 단)·point_at_attacker heuristic(리드 0)·전 결과 discovery(E1 후 confirmation). 다음 = 서버 4단계 실런.

### 2026-07-19 (sss) — ✅ C-1 회랑 실존 프로브 구현 (신규 개발축 1 · DISCOVERY) — 배선 스모크 4/4 green, 서버 실행 대기

- **위치**: doctrine(docs/22 v0.2 §0-1) 우선순위 ①(A2 nominal→shell 회랑 존재·구조) 첫 실험. A-캠페인 아님·종결 실험 아님 — **분기 진단 + (성공 시) on-manifold 장궤적 생성기**((qqq) F_hist={2:195}로 d1 수확이 못 준 긴 pre-fire 이력을 nominal 쪽에서 직접 확보). 경량 사전등록 = **docs/23**(0-e급 문서 증식 금지 원칙 준수).
- **산출**: `shepherd/scripts/c1_corridor_probe.py`(torch-free 코어; learned arm만 `--learned` 서버) + `tests/test_c1_corridor.py`(+12, 전 green) + `docs/23_c1_corridor_probe.md`. 4단계: **baseline**(zero/brake/lam20/attpd3[+hybrid]) / **corral**(scripted-corral 가족 ring4·wall3_chase1·press2_block2 랜덤서치 → screen → top-K) / **cem**(reset별 개방루프 CEM·A2 폐루프 내부·arrival 시 조기종료·corral 웜스타트 옵션) / **robust**(fresh band 1200–1299 + action-noise×att-speed 변주).
- **측정기 핵심 결정(스모크 실측 반영)**: PRIMARY 신호 = **`max_clean_v_soft`**(p_feas>0 스텝의 v_soft만) — reset 1100 corral이 **boxed 과압축**으로 v_soft 1.0 / p_feas 0을 만들되 guard 정당히 미발사(t20–22 실측) → plain max_v_soft는 게이밍. clean margin이 정본, boxed_shell_steps 별도 로깅. score()=optimiser 유도 전용(verdict=eligible, 판정 J 아님).
- **증거 라벨 규율(권고안 §3)**: 발사≥1 = CORRIDOR EXISTS(구성적) / 전 solver 실패 = **NOT FOUND UNDER TESTED SOLVERS**(부재 증명 아님 — certificate 없음). 실패 시 즉시 종결 금지 → 민감도(θ·R_net·T)로 connectivity 여는 물리 축 탐색.
- **seed 대장**: reset 1100–1199(search)/1200–1299(robust) + rng 330k(CEM)/331k(corral)/332k(robust) = **전 legacy 가족·(qqq) 950–1049·RT-2 212121과 서로소**(테스트 lock).
- **스모크(샌드박스 GitHub 무인증 클론·torch-free)**: baseline n4 = 전 arm elig 0·cleanV≈.21·len 23 (= (qqq) 무발사 정합, 계기 정상 확인) / corral 24cfg = top들 **boxed=1.00**(shell 도달·과압축 = near-miss 포착 설계대로) / cem pop10·iter4 = 배선 정상·소예산 미발견 / **회귀: c1+pfc+env_m3 50 green**. **본 런은 서버**(런북 = docs/23 §11: baseline→corral n_cfg160→cem draws20 웜스타트→robust). ⚠ 미커밋 — Windows `git reset`→push 후 서버 pull.
- **다음 수(제안 형식)**: ①병목=nominal 23스텝 창 내 fire-eligible 기하 실존 미검 ②최소 실험=본 프로브 서버 4단계 ③성공 시 corridor-aware curriculum·predecessor·brake 한계 조건의 재료 확보(nominal 해결력 직접 상승) ④실패 시 task-design 민감도(어느 물리 축이 회랑을 여는가)로 개발 방향 전환. 결과는 U-W snapshot·U-R 보고서 재료로도 절단 가능(도구일 뿐, 방향 지배 금지).

### 2026-07-19 (rrr-1) — (rrr) 후속: 연구 지휘 원칙 지시 접수 — 수확 지도 = 참고 전용, [P-1] 확정, 진단-프레이밍 격하 금지 (docs/22 → v0.2)

- **지시 요지(Hyunjun)**: 원 연구 질문 불변 — *"이종 다중 드론이 MARL을 통해 공격 드론을 협력적으로 양치기·성형하여 포획 가능한 상태로 유도할 수 있는가."* 현 상태 = 실패 후퇴가 아니라 **시스템 구조의 선명화**(협력 shaping은 MARL로 실제 학습 / shot은 learned 필수 아님 — rule guard 분리가 더 자연·안정 / hybrid = 원 문제를 더 적절하게 푸는 설계 / d1 brake 우위 = 국소 조건 미입증이지 전체 판정 아님). **기본 프레이밍** = "MARL 협력 양치기·성형 시스템을 개발하는 과정에서 terminal hybrid 분리와 local-to-mission reachability 병목을 규명·해결해 나가는 연구"; 진단 프레이밍 = 회랑 부재·후속 실패 누적 시의 fallback 한정.
- **운용 원칙(8항, 상세 = docs/22 v0.2 §0-1)**: 논문 절단·종결 = 명시 지시 시만(마감 = snapshot 수확 시점일 뿐) / U-A·U-B = 콘텐츠 보관함, 실험 라우터 아님("A3 = 자동 U-B" 폐지 — 중심 서사 강화 시 같은 축 연결) / 티어 평가 = snapshot 출판 가능성 전용(**harvest map ≠ research ceiling map**) / **회랑 프로브 = 종결 실험이 아니라 다음 개발 수 선택용 전제 진단**(존재→corridor-aware 개발 / 협소→geometry·reward·obs·planning 개선 / 부재→mission design 재설계 후 재개발 — engineering feedback이지 MARL 실패 아님) / 제안 형식 의무 = ①병목 ②최소 실험 ③성공 시 nominal 해결력 증가 ④실패 시 방향 변화 → 그 후에만 논문 활용 부가.
- **[P-1] 확정**: 8/31 트립와이어 = **현 술어·기존 predecessor/rewind 공략 캠페인의 종료선으로만** 유지. 회랑 existence·corridor construction / nominal transfer / hybrid confirmation / longer-horizon shaping / A3+ attacker / MARL necessity / 역할 분화·일반화 = **신규 개발축으로 개방**(B-fork 집필 전용 전환 없음). 신규 축은 0-e급 대형 사전등록·문서 증식 금지 — **discovery-mode 우선, 양성 시에만 confirmation**(최소선 = 판정 J·평가 경로 동결·seed 대장·증거 기록).
- **우선순위(지시 §5)**: ① A2 nominal→shell 회랑 존재·구조 ② (존재 시) 재현 privileged controller/planner ③ brake 한계가 드러나는 longer-horizon·다중 역할 조건 ④ learned limiter의 상태-의존 협력 분석 ⑤ A3 cost-aware attacker exploitability ⑥ curriculum·역할 분화·중앙 critic 발전 ⑦ nominal/broader 분포 autonomous capture. 저순위 = 티어 재평가 반복·진단 목차 정교화·실험축 조기 분리·마감 맞춤 클레임 축소·실패 시 즉시 종결 프레이밍.

### 2026-07-19 (rrr) — 논문 수확 지도 docs/22 v0.1 작성 (분할 세션 — 비준 대기 [P-1]~[P-4])

- **금일 구두 방침(Hyunjun)**: 지금 Paper A를 분리 집필하지 않음 — attacker upgrade·MARL을 계속 사용하며 성과는 URP 보고서 스파인(중간 8월 말~9월 초·최종 12/18)으로 엮음. 논문은 "수확 시점 절단"으로 전환 → **docs/22_paper_map.md v0.1** = 클레임 경계 유닛 4개(U-W 워크샵 슬라이스 / U-A 포획 해부(권고안 Paper A) / U-B MARL 필요성+S9 경제(권고안 Paper B) / U-R 보고서 스파인) + 콘텐츠 배정 매트릭스 16행 + 정직 티어 판정 + 벤ue 사다리. 입력 = 업로드 권고안(paper_scope_recommendation)·docs/20 §6·docs/12 §6·(ooo)~(qqq-1). 벤ue 마감 웹 실측: **ICRA 2027 = 서울 개최·마감 2026-09-15 / IROS 2027 = 피렌체·2027-03-01(공식 CFP 재확인 요) / AAMAS 2027 = 하노이 5월·마감 2026-10 TBC(스킵 권고 — U-B 정조준 = AAMAS 2028)**.
- **정직 티어 판정 요지**(금일 질문 "이거만으로 어느 저널?"의 답): 현 자산 = 워크샵/국내·영문 단편 **충족**(dev-only 캐비앗) / 본회·Q2 저널 = ⓐ hybrid confirmation 재현(신규 held-out 번들·5–10 seeds — sealed 소진이라 신규 대역) + ⓑ mission-level 답(회랑 판독) 필요 / Q1 = +ⓒ 필요성(A3+) or 일반성. 공격면 4 = dev-only·d1-국소·제4병목(brake .858 ≥ learned .775)·A2 고정. **회랑 프로브 = publishability 대비 최저 비용 + A3 캠페인 전제 진단**(A2 회랑 미확인 시 A3 실패 원인 분리 불능) 재확인.
- **⚠ [P-1] 충돌 개설**: 계속-연구 노선 vs docs/12 §0·21 §7 트립와이어(8/15 착수·8/31·이후 B 집필 전용) — (mmm-1) 전례상 개정 정당·무언 개정 금지. 권장 = (b) 8/31 대상을 현 술어 공략 A-캠페인으로 한정, 신규 축(A3+·회랑)은 별도 사전등록 캠페인. [P-2] 워크샵 슬라이스 = 교수님 상의 후(임박: SASE 7/31·AI학술 8/24·KSME 8/26·RiTA 8/31 — RiTA는 LNNS 아카이벌 주의). 상세 = docs/22.

### 2026-07-19 (qqq-1) — (qqq) 3자 정정 수용: **"닫힘-음성" 과잉 결론 철회** — 검정한 명제/미검 명제 분리 (docs/20 §6-보론-2 개정)

- **정정 요지**: (qqq)의 "L2·L3 닫힘-음성 · 3중 독립 증거 · 포획은 1-스텝 껍질에서만 결정" = 과잉 결론. 세 결과는 동일 가설의 독립 3검정이 아니라 **서로 다른 명제의 측정**: ① U-1 = witness 근방 local recovery **음성** ② A-3d = 특정 폐형식 합성의 robust feasibility **음성** ③ A-3e F=2 = **d1 궤적에 d2 구성용 과거 이력 부재 — 가설 기각이 아니라 실험 식별 불능**(on-manifold rewind는 검정된 적 없음). nominal 0/500 무발사 = d1-분포 정책의 **transfer 실패 증거**이지 회랑 부재 증거 아님(동일 엔트리의 "회랑 미검사" 문구와 내부 모순이었음 — 해소).
- **채택 상태 표기**: synthetic k≥2 음성 / 근방 2-step recoverability 음성 / d1-궤적 rewind k=2 **구조적 생성 불가·미판정** / nominal→shell 접근 회랑 **미검** / 재귀 ladder **현 경로 blocked·일반 falsified 아님**. 종합 문구 = "현행 synthetic 및 d1-수확 기반 horizon-extension 경로는 닫혔으나, nominal 접근 회랑과 더 긴 실궤적 기반 predecessor의 실존은 미검이다." "3중 독립 증거" → "분석·합성·학습 경로에서 각각 확인된 **세 종류의 horizon-extension 장애**".
- **연구축 2분리(후보 경로 재배치)**: **축1 = A2 하 접근 회랑 실존 검사**(trajectory optimization·MPC oracle·scripted corral·direct shooting) / **축2 = 강한 공격자 하 MARL 필요성**(A3 cost-aware MPC·A4 exploiter·self-play). A3는 회랑 확인 도구가 아니라 난도 상승축 — (qqq) 슬롯의 선택지에서 두 축을 분리.
- **부수 정정(docs/20)**: ① L4 각주 "판정 설계가 만든 난이도" 확정 표현 → "**포획 물리의 정밀도 요구 × 이진·MC 판정 설계의 결합으로 형성 — 상대 기여 미분리**"로 개방 복원 ② Q-tier hybrid 갱신: 워크샵 = **teacher-free autonomous hybrid capture**(learned fire 필요조건 아님), Q2 = **MARL shaping + autonomous guard k=1 성공 + rewind k=2 oracle 우월 + rewind k=2 learned shaping 성공** ③ ladder L2 = 현 경로 닫힘·on-manifold 미판정, L3 = blocked·일반 falsified 아님.
- 유지(검토 합치 확인): L1 재성형 기록 · learned-fire 실패 = hybrid 선택 근거 · Level 3 = autonomous replacement · 2-모드 · 제4병목 · A2 = identification opponent 한정.

### 2026-07-19 (qqq) — 수확·nominal 프로브 판독: **rewind(지평 확장) 3중 사망 확정** — 수확 풀 공집합(F=2 전원)·nominal 무발사 0/500 → 방향 결정 슬롯 개설

- **수확**(fd07664, d1 2셀 × 3소스 × 50 CRN): 성공 195/300(.65). **F_hist = {2: 195} — 전 성공이 2스텝 발사**; 학습 limiter도 brake와 동일(느긋함 가설 기각). t=F−k(t≥1) 풀 = **전 셀 × 전 k 공집합** → 후보 0, 게이트 미가동(`instrument_ok=False`는 stop-rule-6 아님 — 계기 미가동 N/A 판독). d1 = witness 1스텝 전 구조의 산술적 귀결.
- **nominal 프로브**(n=100 × 5 arms, reset 950–1049 신규 대역, dev discovery): **전 arm captured 0.000 + 발사 이벤트 0**(learned j1_e1 ×3·brake·zero; 창 ~23스텝 = 관통 시간). 가드 술어(v_soft≥θ ∧ p_feas>0)가 500판에서 1회도 미성립 — L1 성형 하에서도 접근 단계가 껍질에 접근 불가.
- **판정: Level 4(후진 지평 확장 = rewind) 3중 독립 증거로 닫힘-음성** — ① U-1 오라클 r@2+ ≡ 0(1-스텝 껍질만 생존) ② A-3d 폐형식 k≥2 σ-validation 전멸 ③ A-3e 실궤적(수확 공집합 + nominal 무발사). 분석·합성·실궤적 세 각도 동일 벽 = **"포획은 1-스텝 껍질 위에서만 결정된다"의 3중 재현**. docs/20 §6-보론-2 + ladder L2·L3 닫힘 반영.
- **맥락 고정**: witness 출처 = probe 탐색·정련 상태(docs/13 p4_probe refined_best) — **캠페인 사상 nominal 포획 관측 0**(docs/14 "전 시도의 무발사 수렴은 학습된 합리성"). 금일 프로브가 이를 hybrid에 대해 정량 확정.
- **열린 질문(미검사)**: nominal→껍질 **접근 회랑의 물리적 실존** — U-1은 껍질 근방 복원성만 측정; 23스텝 창 내 fire-eligible 기하 생성은 오라클도 미검사(witness p_feas ~2.4e-3 → 부재 가능성 상당; 부재 시 "mission 설계 과잉 난도" 자체가 발견).
- **방향 결정 슬롯(개설, Hyunjun)**: ① 회랑 실존 오라클 프로브(PFC scripted corral, discovery) ② 껍질 재무장(A3 MPC 공격자·4+1 협동으로 MAPPO-필요성 재배치) ③ B-fork 발동. 마감 계보: 신규 실험 착수 8/15·트립와이어 8/31. **선(先)기록 지시에 따라 본 엔트리 = 기록만, 방향 미정.**

### 2026-07-19 (ppp) — Discovery Arm A 판독: **hybrid 가드 검증 성공(Level 3 달성·dev)** / J1 부식 곡선 정량화 / **제4병목 실측 — brake+guard가 learned 상회** → 즉시 수확 진입(harvest hybrid 패치)

- **스윕 결과**(origin d0fe2e9 · dev d1 120판 paired vs zero-cache · d0 40판): **seed1 j1_e1 = .775 (Δ̂ +.758, LCB95 +.692)**; seed0/2 j1_e1 = .500 (Δ̂ +.483, LCB +.408); zero .017. 가드 규율 완벽 — fire_clean ≈ .98–1.0, wasted ≈ 0, d0 1.00×3. → **학습된 협동 성형이 규칙 가드로 자율 포획 체인으로 전환됨 = claim ② discovery-수준 지지, 스캐폴드 Level 3(자율 대체) 달성.**
- **J1 부식 곡선**(태그 스윕 j1_e1→e8): seed0 .500→.008(e6), seed1 .775→.25(e8), seed2 전 태그 .500 균일(ckpt sha 상이·행동 동일 — 이상 기록, 무해). j1_e1 = L1-exit 최근접 생존 스냅샷(L1-end ckpt 미저장 gap). L1 cap(.81/.82/.94) 대비 수치 갭은 가드가 아닌 **스냅샷 부식** 탓(seed1 .775 ≈ 자기 L1 cap .82; seed0/2는 j1_e1 시점에 이미 부식). J1-선정 "best" 태그는 hybrid 하 폐기.
- **제4병목(RL-필요성) 실측** — sandbox dev post-hoc(공개: 동일 dev d1 120판·동일 가드·부트스트랩 777): **brake+guard .858 (Δ̂ +.842, LCB +.783) ≒ lam20+guard .858 > learned 최고 .775.** 단일 공격자 d1 포획에는 **학습이 불필요함이 실측** — docs/20 §6 진단 그대로. MAPPO 필요성 시험대 = ① rewind k≥2(claims ladder ③; validate 12 arms에 brake/lam20 내장 → 직접 비교 예정) ② A3+ 공격자 ③ 4+1 협동.
- **결정(지시 이행)**: fire-head 튜닝 종료 유지 → **즉시 수확**. `a3e_harvest.py` hybrid 패치: fire = 규칙 가드(teacher_fire·정책 finisher 미사용), `--tag` 기본 j1_e1(per-seed hybrid argmax = 전 시드 j1_e1), 소스 3-seed 유지(성공률 .78/.50/.50 → 셀당 150판 충분). "P1′ PASS 후에만" 전제는 (ooo) hybrid 경로로 대체(discovery·공개 기록). 다음 = 서버 수확 → screen → validation+comparator → k=2 pooled 판정.

### 2026-07-19 (ooo) — P1′ 판독: **L1 = 캠페인 최초 재성형 학습(양성)** / J1 = learned trigger 결합 실패 → **hybrid 아키텍처 전환 + 2-모드 연구 프로토콜 비준** (docs/20 v0.3 §6-보론)

- **결과**(서버 `54a9bf8`; sealed 소진 완료): F0 = captured 1.00 ×3(2-eval 즉시 통과) / **L1 = Δ^teacher +.79/+.80/+.93, cap .81/.82/.94**(zero-캐시 .017; P(fire|clean) .87–.99, P(fire|nonclean) .03–.16, P(cap|¬reset-clean) .73–.94) — **action-necessary 스폰에서 리미터가 행동으로 clean을 만든 최초 증거, A-3b spawn-luck 천장 돌파(Tier 1)** / J1 = 전 seed cap 0.00 ×8 evals·추세 없음·gate 정확히 −.017(=0−2/120) / sealed = Δ̂ 0.000 ×3, **P1_FAIL 공식 기록**(d0 1.00).
- **J1 기전(eval 진단으로 확정)**: seeds 0/2 = fire_rate 1.00·P(fire|nonclean)=1.0·**clean 에피소드 0**(pfc=None) — F0(d0 = reset-clean)가 "즉시 발사" 습관을 주입했고, FSM은 v_soft≥θ **첫 표본**에서 커밋하므로 p_feas 미성립 시점의 조기 커밋 = wasted = **에피소드 종결**이 성공 중이던 shaping 궤적을 전부 삭제. seed 1 = 무발사 진동(fire 0→.5→0) = 반대 어트랙터(A-3b 양극단 재현). **재성형 실패가 아니라 "학습된 셰이핑 위에 learned one-shot trigger를 얹는 방식"의 실패** — F0 스캐폴드가 문제를 좁힌 게 아니라 조건부를 오염시킨 사례(스캐폴드-오염 실증).
- **비준 3건(Hyunjun; GPT 방법 리뷰 2건 연속 판독 포함)**: ① **hybrid 아키텍처** = MARL cooperative shaping + **rule-based autonomous terminal guard**(fire ⇔ v_soft≥θ ∧ p_feas>0 — obs[−3]/obs[−1], 동결 관측 계약 내 자율; 실계 이식 시 onboard 추정기 필요 캐비앗 명시). learned-fire 계열 중단(F0 커리큘럼 단계·fire-head 튜닝·distill 필수화 폐지 — distill은 부가 진단으로만). learned-shot 실패 = hybrid 선택의 근거 증거로 논문 편입. ② **스캐폴드 6-레벨 재정의**: 레벨 3 = "learned 대체"가 아니라 **autonomous scaffold replacement**(실구현 가능 자율 메커니즘, rule 포함); 스캐폴드마다 제거(대체) 조건 명부 의무. ③ **2-모드 프로토콜**: Discovery(1–3 seed·dev-only·비준 없음·짧은 로그) / Confirmation(양성 신호 후에만 동결·sealed·감사); Discovery 최소선 = 판정 J·평가 경로·sealed 소진·seed 대장·증거 테이블. 모든 계획 말미 = "원래 문제 해결력이 무엇만큼 느는가".
- **부기**: (a) v0.3.2 sealed 진단 arm 개정은 **무산**(sealed이 개정 착지 전 소진) — brake 비교는 dev 사후 진단으로 이동(코드·테스트는 향후 sealed용으로 보존·커밋). (b) git 히스토리 평탄화: 서버 결과 커밋(54a9bf8)이 로컬 docs 2커밋(a04842f·3e29f8d)과 분기 → 본 커밋이 54a9bf8 위에 누적본으로 재수록(내용 전량 승계 — docs/21 v0.3.2·docs/20 v0.3·(mmm-1)(nnn) 로그 텍스트 포함; 구 커밋 2개는 미푸시 폐기). (c) docs/12 §6에 A-3e P1′ 증거 행.
- **Discovery 스프린트 Arm A 착수**(`a3e_hybrid_eval.py`, dev-only): 각 seed의 J1 ckpt 스윕(j1_e1..e8·best — L1-말 스냅샷 부재 갭 명시, j1_e1 = 최근접) × [학습 리미터 + rule guard]를 dev d1 120판 paired(vs zero-캐시) + d0 40판 평가; 기록 = paired Δ·wasted·P(fire|clean/nonclean)·발사 시점 v_soft·feasible frac·d0 cap. **가드가 L1 수준(cap ~.8)을 재현하면 즉시 수확→rewind로 진행**(fire-head 튜닝에 시간 불사용). Arm B(distill) = 보류(부가 진단). 질문-의무 답: 이 실험 통과 = teacher 제거(자율 대체) 완성 = 스캐폴드 레벨 3 달성 + end-to-end 국소 포획 양성.

### 2026-07-18 (nnn) — docs/20 v0.2: 수준 사다리 L0~L5 + B 아웃라인 뼈대 부록 (거시 목표선 비준)

- Hyunjun 거시 질문("구현 가능한가·어느 수준까지 가야 하나") 논의 결과를 docs/20 §6으로 명문화: **L0(셰이핑 학습) 달성 / L1(k=1 mechanistic 포획) P1′ 시험 중 / L2(rewind k=2) 대기 / L3(재귀 사다리) 학기 규모 / L4(nominal capture-unlock) = 프레임-의존 미결(판정 면도날이 만든 난이도 → 후속 논문 질문으로 승격; 단 obs-컨트롤러 k=2~4 일부 셀 .8+ 실측 = 불가능 증명도 없음) / L5 일반화**. 목표선: 보고서 필요선 이미 충족(L0+벽 규명); 가을 논문 = L0+B 필요선에 L1 상방·L2 방법론 기여; **이번 여름 = L1 최소·L2 목표**. B 아웃라인 6절 뼈대(사다리 = 논문 구조; 병행-준비 조항의 실체) 동봉. [R-1]~[R-3] 해소 표기.

### 2026-07-18 (mmm-1) — docs/21 v0.3 → **v0.3.1: §7 중단 라우팅 분기형 개정** (Hyunjun 지적·비준; 결과 판독 전 = 사전등록 무손상)

- **지적**: "왜 이렇게 B를 급하게 가나 — 시간 많다"(잔여 6주, 1사이클 ≈ 1주). **판독**: 구 §7의 "실패 → 즉시 B"는 (i) 무결성 장치(해당 실험 구제 금지 — 양보 불가)와 (ii) docs/20 옵션 C의 "1주 컷" 라우팅이 섞여 세습된 과잉 조임 — 무결성이 요구하는 것은 (i)까지이며, 실패 후 **신규 사전등록 실험**은 정당(각 실패는 어느 분기든 B 증거 사슬을 강화). (iii) BANK FAIL 때 실제로 쓴 패턴도 자동-B가 아니라 docs/20 분기였음.
- **개정 내용**: 무결성 조항 전부 불변(구제 금지·측정기/가설 분리·source 결측·sealed 소진·pooled 규칙·증거 행) / 과학적 실패 3종(P1′ FAIL·수확 결측·pooled 기각)의 사후 라우팅 = "즉시 B" → **분기 결정(새 사전등록 실험 vs B, Hyunjun 비준)** / **신규 실험 착수 마감 2026-08-15**(이후 = B 집필·재현 패키징 전용; 트립와이어 8/31 불변) / **B 준비 병행** 조항 편입(아웃라인·그림 목록·12 §6 유지 — 전환 비용 최소화). 판정 기준·게이트·seed 일절 무변경, P1′ 진행 무영향. 3자에는 다음 접촉 시 통보(데이터 미열람 시점 라우팅 개정·기준 무변경 — 전용 라운드 불요 판단).

### 2026-07-18 (mmm) — ✅ A-3e 구현 2/2: 수확·RT-PFC·rewind 파이프라인·sealed judgment (+테스트 11, a3d/a3e 스위트 63 green) — **P1′ 런치 가능**

- **RT-PFC**(`a3e.py`): a = clip_norm(a_rec(t) + K_p(p_rec−p) + K_d(v_rec−v)), t=0 = 스냅샷·참조 소진 후 terminal hold(수확 궤적은 발사 시점 v≠0 → hold = 도착점 제동 — 테스트가 수식 그대로 락). **유닛 락 2종 = PFC≡demo 락의 유사물**: 정확-재생 항등(float32 정밀도) + 고정 perturbation(rng 212,121·σ.005·n8)에서 개방루프 대비 endpoint 오차 < 0.6×.
- **수확 하네스**(`a3e_harvest.py`, 서버·P1′ PASS 후 1회): 셀당 150판 = source 3 × 50(reset 700–749 CRN 공유·스폰 50개 셀당 공유 = source 간 동일 에피소드; draw는 j%12 라운드로빈, 지터 300k+1000k+v) → 전량 실행 후 일괄 처리(조기중단 금지) → 성공(arrival_capture ∧ clean 발사) 에피소드의 t=F−k 스냅샷(k∈{2,4,8}, t≥1·**pre-commit 구조 보장**(commit≡F) assert) → **게이트 3종**: 계약-정합 복원(reset_to→기록 가속 개방루프+teacher fire: 궤적 atol 1e-3 ∧ clean 발사 ∧ arrival 재현) → RT-1(RT-PFC 정확-재생 항등, env) → RT-2(pooled 비율 < 0.6 — **spec 조작화 1건 자기신고: per-snapshot이 아닌 pooled 평균 비율로 판정**, v0.3 문면의 기계적 독해) → state-aware dedup(τ .05/.25/.05/.25·같은 (cell,k) 풀·대표 = (cell,source,seed,F) 사전순) → source-balanced 선택(quota 4·cap 6·**≥2 seed/k 아니면 결측**). instrument 실패 = 기록·중단(게인 조정 금지). 산출 = a3e_rewind_candidates.json.
- **rewind 파이프라인**(`a3e_rewind_validate.py`, torch-free): --stage screen = candidate당 paired RT-PFC/zero 20판(seeds 750–769, 정확-스폰, 16/4/4 fail-fast; instrument_ok=false면 진입 거부) → --stage validate = 셀당 4조건 n=100(seeds 800–899, σ = 스테이지 램프 {k2 .01/k4 .015/k8 .02}, 지터 310k 셀-스트림, 속도 정확), **12 arms**(Gate-A석 = RT-PFC·demo = 기록-가속 개방루프·Gate B 8·random), 부트스트랩 777 순차(episode → draw-cluster → **source-cluster**), gap>.4 = "privileged-feasible but hand-controller-hard" 표기 → **판정 = k=2 pooled primary**(존재 셀 균등 병합, 4조건 전부; 셀별 = secondary) → **synthetic k=2 comparator**(bank v2 d2 3셀 고정 재평가, 판정 2-arm, 지터 320k — descriptive) → hypothesis = ON_MANIFOLD_ADOPTED / REJECTED_TO_B.
- **sealed judgment**(`a3e_sealed_judgment.py`, 서버 1회): 가드 로드(소진 마커 검사) → zero arm 1회(공유) + seed별 policy arm 동일-에피소드 → Δ̂_s → **PASS = ≥2/3 seed >0.10 ∧ 전원 ≥0**(순수 함수 락) + exact McNemar(b,c) 보조·d0 captured 진단 → verdict 기록 후 **소진 마커** — "sealed holdout pilot" 라벨 고정.
- 테스트 +11(RT-PFC 3·스냅샷 산술·dedup 리뷰어 케이스(속도/공격자 상이 비병합)·선택 quota/cap/결측·P1 규칙+McNemar·pooled 수학·screen fail-fast 주입·물질화 계약·arm 배선) + enumerate 테스트에 comparator 320k 대역 추가 — **a3d/a3e 스위트 63 green**. 캐비앗: 전체-트리 sandbox pytest는 torch-stub 오염으로 28 fail — **순정 트리 동일 재현 = 사전 존재 아티팩트**(서버 실측이 정본; 런북 V-체크에 명기).
- **다음 = P1′ 서버 런치**(런북: pull → REQUIRED_COMMIT 확인 → torch pytest 전체 → smoke 1-eval → 3-seed 본 런 ≈ 반나절) → sealed judgment → [PASS] 수확 → screen → validation+comparator → pooled 판정. 트립와이어 8/31.

### 2026-07-18 (lll) — ✅ A-3e 구현 1/2: 3-phase 트레이너 + d1-only 번들 (+테스트 18, 전 스위트 52 green)

- **트레이너**(`train_m3a.py` a3e 배선 + `shepherd/train/a3e.py` 신규 torch-free 코어): 동결 상수 모듈化(cadence 20,480·caps 6/8/8·total 450,560·F0 exit 0.45·Δ게이트 0.10·stall 0.05/3·부트스트랩 777) / **A3EPhases 상태기계**(F0→L1→J1 전이·2연속 게이트·consec 리셋·L1 미달 = fire unfreeze 없이 FAIL·J1 stall 기록·터미널 무연산 — 전 전이 유닛 락) / phase-구동 플래그(F0: limiter hold+동결·teacher off·fire 학습 / L1: fire 동결+teacher 발사 / J1: teacher 영구 제거·**fire-head Adam state 삭제 = fresh optimizer**·lr 스케줄 무단절(anneal none 동결)) / **게이트 eval = dev 번들 전판**(m3_eval_bundle 1콜, reset_seed 연속 정렬 lock; F0 = captured_rate(teacher-free·limiter hold) / L1 = Δ^teacher paired vs zero-캐시 / J1 = Δ^free paired) / 진단 3종(P(fire|clean)·P(fire|nonclean)·P(capture|reset¬clean)) 매 eval / **best-ckpt = (dev Δ^free, −P(fire|nonclean), −eval_idx) lexicographic**(J1 후보만·매 eval ckpt 보존) / Curriculum 대체 = _A3ECurStub(overrides 상시 None = frozen constants+judgment m3). config = `configs/m3a_a3e_p1.yaml`(total 450,560 assert·cadence assert·φ-PBRS 등 A-3d 비준 스캐폴드 불변 승계).
- **번들**(`a3e_bundle_gen.py`): dev-v2d1 {75k, 12.0M} / sealed-v2d1 {95k, 13.0M} — **d0 40**(witness 2×20, 정확 스폰·limiter_v 부재 = adapter 0-속도 계약) + **d1 120**(24 admissible draws × 5, 셀 60:60, (cell, draw, rep) 사전순, 셀당 지터 스트림 base+1,000k+v 순차 소비), reset seed = base+10,000·stage_idx+i(연속). **dev zero-캐시 내장**: zero+teacher arm 120판 실측 → **zero_arrival 2/120 (.017)**·reset_clean 0 — validation zero .03/.04와 정합, paired 게이트 분모 확보. sealed = 캐시 없음·무평가 생성(policy+zero 동시 1회는 judgment 스크립트 몫). **SHA-256 manifest**(dev 0aded4a0…/sealed d298d871…; 입력 해시·seed→API 매핑 포함) + **가드 4종**(content-키: sealed 기본 거부·복사/개명 무력·변조 sha 검출·소진 마커 재사용 거부; --force류 부재) + `mark_sealed_consumed`.
- **테스트 +18**(동결 수치 락·상태기계 7·paired-Δ 결정론·진단·best-ckpt 순서·**E-5 서약 테스트 2종**(전 지터 파생 enumerate pairwise-distinct — 71k/81k/93k/75k/95k/76k/300k/310k 전 대입값·신규 reset 대역 vs 레거시 서로소)·스포너 admissible 24/결정론·번들 조성/시드식/결정론·가드 4·zero-캐시 짝지음 계약) — a3e 18 + bank_v2 9 + validate 8 + pfc 17 = **52 green**.
- **다음 = 구현 2/2**: 수확 하네스(pre-commit 필터·계약-정합 복원게이트·state-aware dedup·source-balanced 선택) + RT-PFC(+RT-1/RT-2 락) + rewind screen/validation + **sealed judgment 스크립트** → 전부 커밋 후 **P1′ 런치**(§8 순서: 전 구현 동결 → P1′). 학습 금지 유지.

### 2026-07-18 (kkk) — ✅ A-3e 3자 회신(조건부 승인) 반영 + Hyunjun 비준 = **A-3e 동결 커밋** (docs/21 v0.3)

- **회신 요지**(접수본 = `URP/a3e_external_review_2026-07-18.md`): E-1 수정승인 / E-2 조건부 / E-3·E-4 **중요수정후승인** / E-5·E-6 수정승인 — 필수 체크리스트 20항·자유도 37건·충돌 5. **실질 적중 3건**: ① **d0 paired-arrival exit 정의상 무효**(reset-clean 앵커 → arrival_capture≡0; v0.2 공통-exit는 결함) ② **teacher 스케줄 미동결** = 최대 잔여 자유도 ③ 수확 200판 vs seed 50개 산수 불일치. 그 외 전부 정당: Markov snapshot 불완전성·source quota·dedup 차원·RT-PFC 측정기 게이트·multiplicity·comparator·seed 파생 enumerate.
- **Hyunjun 비준 2건**: ① 20항 일괄 수용(수치 구체화 포함) ② 4.1 상태 복원 = **계약-정합형**(저장 = limiter/attacker p·v = 스폰 계약의 전체 상태; **pre-commit 스냅샷만 수락**(공격자 memoryless 보장); reset_to 복원 동등성 게이트(기록 가속 개방루프 → 궤적 atol 1e-3·clean·발사 재현) — 리뷰어 원문형(full-sim-state)은 reset_to 피니셔-불가침 동결 계약과 충돌하여 대체, 의도는 게이트가 담당).
- **v0.3 동결 내용**: Tier 1/2 클레임 분리("one-step local reshaping"; PASS = Tier 2 teacher-free) / 번들 수치(d0 40 + d1 120 = 24×5 라운드로빈; dev zero-캐시·**sealed = policy+zero 동시 1회 소비**) / **3-phase**: F0(d0, limiter hold, teacher 없음, captured≥0.45 ×2, max 6-eval) → L1(d1, fire freeze + teacher gate, Δ^teacher>0.10 ×2 → **teacher 영구 해제·재투입 금지**, max 8-eval, 미달 = unfreeze 없이 FAIL) → J1(teacher-free joint, fire-optimizer fresh, Δ^free>0.10 ×2, max 8-eval); cadence 20,480·**총 cap 450,560**·진단 3종(P(fire|clean)/P(fire|nonclean)/P(capture|reset nonclean)) 의무 / best-ckpt = dev Δ^free → min P(fire|nonclean) → 이른 ckpt / P1′ = **sealed holdout pilot**(≥2/3 seed Δ̂>0.10 ∧ 전원 ≥0) / 수확 = 3 seed 전원 best-ckpt × **150판/셀**(source당 50, reset 700–749 CRN 공유) 전량-실행-후-일괄, 스냅샷 = 발사−k·pre-commit·복원게이트 통과분, state-aware dedup(τ = .05m/.25m/s/.05m/.25m/s, 순열 없음 명시), source-balanced 선택(quota 4·≤6·**≥2 seed/k 아니면 결측**) / RT-PFC 시간정렬·norm clip 명시 + **RT-1(no-jitter 항등)·RT-2(σ.005 회복 < 0.6·open-loop) 측정기 게이트**(실패 = "측정기 구현 실패" 기록·중단 — 가설 기각과 분리) / rewind: candidate당 screen 20판(750–769) → 4조건 n=100(800–899), 12 arms(Gate A석 = RT-PFC, Gate B 유지 — gap>.4 = "privileged-feasible but hand-controller-hard"), **판정 = k=2 pooled primary(안 A)** + synthetic k=2 3셀 동조건 comparator 병기(고정 재평가 = 1회 원칙 무충돌) / **지터 재배치: 수확 300k대·rewind val 310k대**(구 78k/79k 파생이 80k/81k 침범 → 이동) + **전 파생 enumerate·pairwise-disjoint 테스트 락 약속** / 777 전 분석 공통(독립성 비주장) / 중단 9종 + **rewind-v2 1회 생성 원칙 신설** + B 정의 재수록.
- **다음 = 구현**(3-phase 트레이너·d1 번들·수확/복원게이트/RT-PFC/rewind 파이프라인 + 테스트; 결과 판독 전 커밋) → P1′(서버 3-seed). 학습 금지는 구현 동결 커밋까지.

### 2026-07-18 (jjj-1) — docs/21 v0.1 → v0.2: 자기완결 3자 검토판 확장([R-3] = 검토 실시 비준)

- E-결정 6건 불변. 추가 = §1 최소 배경, §2 bank v2 FAIL 증거 전문(7셀 validation 표 + GateB_best 열), 슬롯별 근거/대안/리스크, **스펙 명확화 2건**: (i) [E-3] teacher-gating 기간은 exit 평가에서 제외(fire-head 무학습 구간 Δ 무의미) (ii) [E-4] RT-PFC의 대안 기각 논증(폐형식 재생성 = 소진·정책-자기기준 = 순환 → 유일 비순환 특권 기준선) + CRN-특이성은 fresh-CRN screen이 거르는 구조 명시. §9 자기신고 7항(RT-PFC 실측 0·dedup 임의성·near-miss 기대 편향·k=4/8 결측 가능성 등), §10 검토 출력 형식. 3자 전달본 = `URP/a3e_prereg_brief_2026-07-18.md`(동일본).
- 대기: 3자 검토 1회 → Hyunjun 비준 = A-3e 동결 커밋 → 구현 → P1′.

### 2026-07-18 (jjj) — [R-1] 비준 = **A-3e 선택** → 사전등록 초안 docs/21 v0.1 (E-1~E-6 비준 대기)

- Hyunjun [R-1] = A-3e(d1-only 파일럿 → 성공 궤적 수확 → rewind-v2). docs/21 v0.1 작성 — 신규 결정 6슬롯: **[E-1]** bank-v2-d1 = 기존 admissible 24 draws 부분집합(신규 생성 아님)·클레임 = mechanistic·D1 / **[E-2]** dev-v2d1 {75k, 12.0M}·sealed-v2d1 {95k, 13.0M}(0-e 예약분 승계, 미생성이라 무오염), 스테이지 {d0 앵커, d1}, zero-캐시 동봉, sealed 불가침 테스트 4종 / **[E-3]** P1′ = 3-seed scratch, exit = 19 v0.3 §7 동결형 구현(Wilson 폐지), step 예산 = 최소소요×1.2 룰(구현 시 확정), 판정 = sealed에서 ≥2/3 seed Δ̂>0.10 ∧ 전원 ≥0, FAIL→B / **[E-4]** 수확 = best-ckpt × d1 물질화(78k) × seeds 700–749 × 200판/셀, 성공 에피소드의 발사−k 스냅샷(k∈{2,4,8}, dedup 0.05m, per-k 12/8) + **RT-PFC**(기록-궤적 참조 PFC, 게인 (1.0,0.5) 승계) → rewind-v2 = 생성 screen(750–769, 16/4/4) → 4조건 validation(800–899, 79k, n=100) — k=2 admissible ≥1 = on-manifold 가설 채택 / **[E-5]** seed·rng 증보 전 대역 서로소 / **[E-6]** 중단 규칙 4종(각 실패 = 12 §6 증거 행) + 하드 스톱 8/31.
- 다음: E-슬롯 비준(+[R-3] 3자 1회 여부) → 구현·동결 커밋 → P1′. 학습 금지 유지(동결 전).

### 2026-07-18 (iii) — ❌ bank v2 독립 validation: **BANK FAIL 선언**(admissible = d1 2셀뿐, 규칙 기계 적용) → 재설계 분기 docs/20

- **결과**(`results/a3d_bank_v2_validation.json`, 서버 `b6b970a`; 12 arms × 700판·seeds 600–699·σ-물질화·부트스트랩 777): **d1 압승** — v16/d1 PFC .94/zero .03/Δ̂ .91(LCB95 .86), v20/d1 .95/.04/.91(.86); reset_clean 전 셀 0, p₀₁ 전 셀 0(파워 스케치의 nested 전제 실측 성립), cluster-LCB ≈ episode-LCB. **k≥2 전멸**: v16/d2 **.79 [B — 1판 차 near-miss]** / v20/d2 .61 [B](사전 저신뢰 .63 적중) / v24/d2 .81·zero **.39** [C·D](σ가 관성-공짜 부활; brake .92 > PFC .81) / v24/d3 .64 [B] / v24/d4 .66 [B]. **coverage minimum(d1∧d2 각 ≥1) 미달 → BANK FAIL** — 문턱 재조정·재생성 금지 조항 그대로 적용(near-miss 구제 없음, 기록만). **부록 A·dev-v2/sealed-v2·P1 취소.** admissible matrix(기록) = {d1: v16, v20}.
- **판독**: 생성 스크린(정확-스폰, PFC≡demo)과 validation(σ-물질화)의 괴리가 그대로 실현 — **특권 오라클조차 k≥2에서 σ-강건 도달 .8 미달**(σ 램프 .005→.02와 감쇠 .94→.61~.81 동행). action-necessity(D)는 v24/d2 외 전 셀 생존(Δ̂ .58–.91) → **벽 재정밀화: 행동 필요성이 아니라 "폐형식 후방합성(off-manifold·정지구성·이력무) 상태의 σ-강건 도달성"이 k=1 너머에서 붕괴.** 부수: hand-controller 경고 d4 유일(gap .43 — k=8만 데모-지식 필수), lam20 .65–.89 = k≤4 obs-hard 아님. 3자 B-조건(v0.3 수정분)이 설계 목적 그대로 작동한 사례.
- docs/12 §6에 A-3d 증거 행 추가. **다음 = docs/20 v0.1 재설계 분기(Hyunjun [R-1]~[R-3] 결정 대기)**: (a) A-3e = d1-only 파일럿(P1′, 클레임 mechanistic·D1) → 성공 궤적 스냅샷 수확 → rewind-v2(T-4 예약분, on-manifold d2 재구축) / (b) B-프레이밍 조기 확정 / (c) 병행(권고 — P1′ 게이트 ~1주 컷, 실패 즉시 B; 8/31 불변). 학습 금지 유지(새 사전등록 전).

### 2026-07-18 (hhh) — ✅ bank v2 1회 생성 완료(서버, 7/7 셀·제외 0·81 draws) + §6 validation 하네스 동결·커밋

- **생성 결과**(`results/a3d_sbe_bank_v2.json`, 서버 커밋 `91205cb`; meta로 동결 코드 실행 확인 — seeds 420–439·first_fit·게인 (1.0,0.5)·smoke 대역 은퇴 기록): **7/7 셀 OK, 총 81 draws.** v16/d1·d2, v20/d1·d2, v24/d3 = 12/12 무결(pfc_mean .95–1.0, zero 0); v16/d1은 300–319·400–419에 이어 **3번째 CRN 대역 재현**. **v24/d2 = 유일 fallback 셀**: 3후보 전부 목표 12 미달(9/9/3, 각 48시도) → lexicographic rule-2로 cand0 9 draws 수록 — 거부 39건/후보의 다수가 zero-공짜(zero-포획 195회 관측, len≈12) = **0-c "관성 공짜" 모드가 draw-필터에서 구조적으로 배제됨**. **v24/d4 = 12/24**(rule-1): 거부 12건에서 **zero-포획 63회·len≈17 = d4 en-route 공짜 발사 가설 실측 데이터 확보**. 구성-게이트 드랍 전 셀 0(거부 전부 스크린 단) = 폐형식 구성 안정. 캐비앗: 스크린 = 정확-스폰(PFC≡demo) 20판 — admissibility 확정 아님, σ-validation이 판정.
- **§6 [D-3] 하네스 동결**: `a3d_bankv2_validate.py` — 셀당 100판(할당 ⌊100/n⌋+잔여 index-순: 12→[9×4,8×8], 9→[12,11×8]), seed 600–699 블록 배정, **σ-물질화 = 번들 기제 그대로**(L+N(0,σ)·att_p+N(0,σ)·속도 정확복사; σ = 스테이지 sigma_pos; 지터 스트림 = rng(76,000+1,000k+v) 셀당 1개, 할당 순 소비, 양팔 공유 = 짝지음·PFC 참조는 명목 유지) / **12 arms 전 기록**(판정 = pfc·zero만; Gate B 8 = brake·λ4·attpd3; 진단 = random(90k+7·reset_seed)·demo) / **4조건 판정**(A reset_clean≤.2 ∧ B PFC≥.8 ∧ C zero≤.2 ∧ D paired-Δ LCB95>.4; outcome=arrival_capture; 경계 포함·D만 초과) / 부트스트랩 rng(777) 순차 소비: primary episode-level → sensitivity draw-cluster(보고 전용) + discordant p₀₁ 기록(nested-전제 검사) / gateb_best·pfc-gap·hand_controller_warning(>.4) 셀별 기록 / **bank 판정 = d1∧d2 각 ≥1 admissible**(1-셀 스테이지 = mechanistic-only 표기). 테스트 +8(대역 서로소·할당·지터 스트림·판정 경계·부트스트랩 결정론+discordance 민감성·**짝지음 구조 락**(동일 seed 양팔 spawn 동일·지터 에피소드별 상이·할당 순서)·Gate B 8멤버 무특권·실물 bank 형상 7셀/81/[9,12×6]) — **validation 결과 판독 전 커밋**(사전등록 준수).
- **다음 = 서버에서 validation 1회 실행**(12 arms × 700 eps ≈ 9–10h; 판정 arms만이면 ~1.7h이나 전 arm 기록이 사전등록) → 판독 → C-제외·admissible matrix 동결 → 부록 A → dev-v2/sealed-v2 + SHA-256 manifest → P1. 학습 금지 유지.

### 2026-07-17 (ggg) — ✅ 3자 회신(조건부 승인) 반영 + Hyunjun 비준 = **0-e 동결 커밋** (docs/19 v0.3)

- **회신 요지**(접수본 = `URP/a3d_0e_external_review_2026-07-17.md`): "수정 반영 후 bank v2 생성 승인" — D-1 수정승인 / D-2 수정승인 / D-3 **중요수정후승인** / D-4 V-5′수정승인·**exit식 기각** / D-5 수정승인, 충돌 4·잔여 자유도 11·체크리스트 15항. **판독**: D-3 지적이 실질 적중 — (fff)의 σ-물질화 명확화가 만든 구멍(σ 하 PFC .55짜리 셀이 gap LCB>.4 단독으로 생존)을 4조건 복구(reset_clean≤.2 ∧ PFC≥.8 ∧ zero≤.2 ∧ gap LCB>.4, outcome=arrival_capture)로 봉인. D-4도 정당(McNemar는 H₀:Δ=0라 δ_min 결합 규칙 미정의; exit_d=UCB(zero)+δ_min은 absolute 회귀). 정정 1건: attpd "수식 미정의"는 문서 누락 문제 — 코드는 `715ab70`에 동결·락 존재(v0.3에 재기술로 봉인, 코드 변경 0). 무해 확인: 학습 0–9 vs union 7–16은 상이 namespace = 누출 아님(ledger 재편만).
- **Hyunjun 비준 2건**: ① stage exit = **점추정 히스테리시스형**(dev-v2 zero-캐시, 전진 Δ̂_d>0.10 2-eval 연속 / 후퇴 UCB95(Δ_d)<0.05 ∧ stall 3; LCB 엄격형 기각 — n=80 과보수) ② 나머지 14항 리뷰어 권장안 일괄 수용.
- **v0.3 반영**(15항 전부, §12 대조표): lexicographic first-fit(target 12 → min 8 → 제외) / **생성 대역 420–439 신규**(400–419 = smoke-only 은퇴, 부분 unblinding 해소) / D-3 4조건 + 100판 draw 균등배정(⌊100/n⌋+index순 잔여) + 부트스트랩 이중(primary episode / sensitivity draw-cluster) + nested-success 전제 문구 / P1(≥2/3 seed Δ̂>0.10 ∧ 전 seed Δ̂≥0)·P2(seed-계층 부트스트랩 LCB>0.10) 분리, McNemar 보조 격하 / 번들 = validation→C-제외→matrix 동결 **후** 생성, 조성 동결(셀 균등·draw 라운드로빈·러너 assert), SHA-256 manifest, sealed 우회 테스트 4종(P1 전) / 0·1-cell 규칙(0=중단, 1=mechanistic만 — **d3·d4는 애초 1셀 = family claim 불가 명시**), coverage minimum = d1·d2 각 ≥1 아니면 bank FAIL / bank 정의문 완화("…with an observation-controller realizability audit") + obs-hard → hand-controller realizability warning / seed 대장 namespace 재편 + random arm 정의(성분별 U[−1,1]³×30, 클립 없음) + teacher 보조 진단 3종 등재.
- **코드**: `a3d_sbe_bank_v2.py` — SCREEN_SEEDS 420–439(+SMOKE_SEEDS 은퇴 기록), build_cell 선택 로직 = lexicographic `_pick()`(argmax = 비구속 진단), meta에 규칙 명기. 테스트: band 서로소(스모크 대역·600–699 포함) + **lexicographic 신규 2종**(8-한계가 12-안정을 차단하지 못함 / 전원 8이면 최앞) — bank_v2 9 + v1 회귀 9 + pfc 17 = **35 green**. 3자 전달본 `URP/a3d_0e_prereg_brief_2026-07-17.md` v0.3 동기화.
- **다음 = bank v2 1회 생성**(420–439, ≈4–7h, 셀-병렬 허용) → §6 validation(n=100, 4조건) → C-제외·matrix 동결 → 부록 A → dev-v2/sealed-v2 + manifest → P1. 학습 금지 유지.

### 2026-07-17 (fff) — docs/19 v0.1 → v0.2: 자기완결 3자 검토판 확장 — D-결정 5건 불변

- **사유**: v0.1은 결정 슬롯 위주라 3자에게 맥락 부족(Hyunjun 지적). v0.2 = 자기완결 재작성 — §1 최소 배경(게임/SBE 폐형식 R·O) · §2 경위(0-c 12셀 표 포함) · §3 0-d 실행 기록 전체(측정기 하드닝 + 리뷰 필수항목 이행표 · 게인 스캔 9조합 표 · dev 12셀 PFC 지도 · v16 재정련 기준/성적/rng 캐비앗 · witness 동결 재계산 수치 · 생성기+스모크, PFC≡demo-on-exact-spawns 정직 표기) · §4–8 [D-1]~[D-5] 각 근거/대안/리스크 · §9 σ grid + seed 대장 전 가족 · §10 자기신고 7항 · §11 검토 출력 형식. 3자 전달본 `URP/a3d_0e_prereg_brief_2026-07-17.md` 동일본으로 갱신.
- **유일한 스펙 명확화(결정 변경 아님) — [D-3] 실행면**: 독립 validation(n=100/셀, seeds 600–699)은 **σ-물질화 스폰(번들과 동일 기제, 지터 rng base 76,000 신규 스트림)**에서 수행으로 명문화 — 정확-스폰에선 PFC≡open-loop demo(테스트 lock)라 σ-물질화 없이는 폐루프 가치·σ-강건성이 측정되지 않기 때문. LCB95(paired Δ)>0.4 · 부트스트랩 10k · rng 777 불변.
- 대기 동일: **3자 검토 1회 → Hyunjun 비준 = 0-e 동결 커밋** → bank v2 1회 생성.

### 2026-07-17 (eee) — 0-e 사전등록 패키지 조립 (docs/19 v0.1) — 3자 검토 → 비준 시 0-e 동결

- **`docs/19_a3d_0e_preregistration.md`** = §8 1~3 동결 일괄본(3자 사본 = `URP/a3d_0e_prereg_brief_2026-07-17.md`): 측정기(PFC (1.0,0.5)·**Gate B family 8멤버 확정 [D-1]**: brake + λ∈{2,5,10,20} + attpd 3조합·obs-hard 문턱 0.4)·witness/coverage((ccc))·생성식(**v0 first-fit 구속 확정 [D-2]**, argmax 폐기)·**admissibility validation [D-3]**: n=100/셀·seed 600–699 신규 예약·LCB95(paired Δ PFC−zero) > ε=0.4(부트스트랩 10k·rng 777)·**V-5′ δ_min = 0.10 [D-4]**·exit 유도식 = UCB95(zero)+δ_min(수치는 validation 후 부록 A 기계 대입)·**번들 계획 [D-5]**: dev/sealed-v1 구조 폐기 기록(보존), dev-v2 = 75k/12.0M·sealed-v2 = 95k/13.0M(해시 기록·P2 전 롤 금지)·seed 대장 전 가족 표.
- 신규 결정 = [D-1]~[D-5] 5건뿐(나머지 전부 기존 비준 사양의 수치 대입). **대기: 3자 검토 1회(각 D-슬롯 승인/수정 + 누락 자유도 지적) → Hyunjun 비준 = 0-e 동결 커밋 → bank v2 1회 생성(셀-병렬 허용, ≈4–7h) → validation → 부록 A → P1.**

### 2026-07-17 (ddd) — ✅ §8-3 생성식 구현·동결 후보: bank v2 생성기(draw-level 6조건 rejection) + 테스트 7 + 스모크 PASS — 생성 실행은 0-e 이후

- **산출**: ① `a3d_sbe_bank_v2.py` — 동결 coverage 매트릭스(witness bank v2 meta에서 로드)의 셀만 생성; **draw-level paired screen 내장**(frozen 게인 (1.0,0.5)·teacher, PASS = pfc≥16/20 ∧ zero≤4/20 ∧ reset_clean≤4/20, fail-fast) + **생성 전용 seed 대역 400–419**(신규, 전 대역 서로소) + **시도 상한 48/셀·목표 12·최소 수록 8** + **v0 후보 grid {v1분포 U[0.3,0.8], U[0.5,0.8], U[0.15,0.5]} first-fit**(후보 0 = v1 분포 = "v1 최근접" tie-break의 try-순서 실현; argmax 모드 플래그 병존 — **어느 규칙이 구속력인지는 0-e에서 확정**) + 셀별 분포 리포트(시도/수락/드랍 사유/수락 v0 통계) + **zero-arm 포획 에피소드 len 히스토그램**(발사 = 에피소드 종결이므로 len ≈ commit 시점 = d4 en-route 가설 판별 프록시) ② v1 생성기 = `v0_range` 파라미터 스레딩(기본값 보존 — 기존 재생성 회귀 9 green으로 바이트-불변 확인) ③ `tests/test_a3d_bank_v2.py` +7(seed 대역 서로소·first-fit/에스컬레이션/제외/상한/드랍 카운트 로직 = 가짜 synth/screen 주입 유닛, rng 스트림 47k 대역 유일성).
- **플러밍 스모크(정보-무해 셀 v16/d1, 산출물 폐기)**: 12/12 시도 전부 수락, 구성 드랍 0·스크린 실패 0, pfc_mean .95·zero 0.0 — 400–419 대역에서도 (bbb)의 300–319 결과 재현 = **스크린의 CRN-밴드 민감성 없음**(v16 신규 witness 한정 확인). 비용 실측: ~2.5–3분/수락 draw(robust 게이트 10 union 빌드 + 40 eps) → **전체 7셀 생성 ≈ 4–7 h 단일 스레드** — 생성 시 셀-병렬(7 proc) 또는 서버 실행 검토.
- **다음 = 0-e 사전등록 패키지 조립**(측정기·witness·coverage·생성식·수치·seed 대장·번들 계획·V-5′/exit/δ_min 문구 일괄) → **3자 검토 1회** → bank v2 1회 생성. 학습 금지 유지.

### 2026-07-17 (ccc) — ✅ §8-2 마감: witness set·coverage 매트릭스 동결 — robust witness bank v2 생성

- **witness set 동결 = {v16 = transplant(신규), v20 = x16v20(기존), v24 = x20v24(기존)}.** 산출 = `results/a3_robust_bank_v2.json`(`a3d_witness_freeze.py`): v1 파일 불변 보존, x12v16 행만 교체 — 채택 limiters로 **전 수치 독립 재계산**: robust val **1.00**·cap 1.00·vmin 1.000(구 0.90 대체), σ-베이스라인 재계측 {.02→.43, .05→.12, .1→.06, .2→.01, .5→0}(타 witness와 동급 = 창 두께 정상화 확인), provenance(출처 = a3d_v16_refine.json·기준 = (aaa)·스크린 성적) 동봉, load_t0 왕복 검증(3 witnesses).
- **coverage 매트릭스 동결(bank meta 동봉, 0-e에 사전등록 문구로 재수록)**: **v16 → d1·d2 / v20 → d1·d2(d2 = 저신뢰 표기 — dev PFC .63, 미달 시 규칙 제외만) / v24 → d2·d3·d4**; d1/v24 = C 구조 제외 확정. 스테이지 커버: d1 = v20+v16 / d2 = v24+v16(+v20 저신뢰) / d3·d4 = v24. 매트릭스 = 목표 선언일 뿐 — admissibility 판정은 생성기 screen + 독립 validation(n=100)이 담당(18 §6).
- 다음 = **§8-3 생성식 동결·구현**: draw-level 6조건 rejection 필터(paired PFC/zero/비-clean screen seed 300–319 재사용? → 아니오, 생성용 신규 대역 지정 예정) + zero-arm 발사 시점 히스토그램 + **시도 상한 48/셀** + v0 후보 grid + 최소 수록 8/12 → 이후 bank v2 1회 생성.

### 2026-07-17 (bbb) — ✅ v16 재리파인 1회 실행: **ACCEPT — transplant 후보(val 1.00) 도착형 스크린 전판 만점** — witness 교체 후보 확보(동결은 다음 스텝)

- (aaa) 기준 그대로 1회 실행(`shepherd/scripts/a3d_v16_refine.py` → `results/a3d_v16_refine.json`): **stage 1** = probe 규약 v16-only 재실행(fresh rng(23) — 원 전체-스윕 실행과는 rng 스트림 위치만 상이, 결정론·문서화) → **후보 2 모두 1차 통과: own .90 / transplant 1.00**. 원 뱅크의 x12v16(.90)은 best-of 선택의 산물이었고, 도너(x20v24) 패턴 x-스케일 이식이 이번 경로에서 완전 강건(val 1.00)으로 리파인됨.
- **stage 2 도착형 paired screen**(seed 300–319, frozen 게인 (1.0,0.5), reset_clean 면도날 ≤4/20로 운용): **own = k1 0/12 탈락**(전 draw pfc 8/13 abort — dev PFC .47과 정합, "얇은 창" 실측 재확인) / **transplant = k1 8/8·k2 8/8, 전 통과 draw 20/20 PFC·0/20 zero·0/20 reset_clean** → (aaa) 선택 규칙 적용 = **transplant 채택**.
- 해석: 재리파인의 정의("더 좋은 컨트롤러가 아니라 본질적으로 더 뚱뚱한 창을 찾는 탐색") 그대로 적중 — v16의 문제는 witness 창 두께였고, 두꺼운 창은 저속에서도 실존. **v16 = d1–d2 coverage 목표 회생.**
- 다음 스텝(③ 동결): witness set = {v16-transplant(신규 등재), v20, v24} 확정 + coverage 매트릭스 동결(v16 d1–d2 / v20 d1 / v24 d2–d4) + 신규 witness의 robust bank 교체 커밋 → 이후 생성식 draw-필터.

### 2026-07-17 (aaa) — v16 재리파인 수락 기준 사전 고정 (탐색 전 커밋, 18 §4 이행) — 탐색 실행은 다음 스텝

- **1회 한정.** 기준은 본 엔트리로 동결(결과 불문 사후 변경 금지). 실패 = v16 폐기 + negative result 보존(12 §6 행) + coverage 매트릭스에서 v16 제거.
- **탐색 기계(변경 금지)**: `a3_robust_witness_probe` 기존 규약 그대로 — v=16 계열 초기점·도너-이식 후보(기존 기능 범위 내, 신규 탐색 축 추가 금지)·E_seeds[clean] greedy 리파인·search seeds 100–104 / robust validation 200–209. **수락 1차** = robust-clean val ≥ 0.9(기존 R-8 동일).
- **수락 2차(도착형 — 채택의 실질 관문, 신규)**: 1차 통과 후보에 bank v1 생성식 그대로(폐형식 감속-도착·콘 ±15°·v0 U[0.3,0.8]·\|a\|≤24) **k∈{1,2} predecessor draws 각 12본** 생성 → draw-level paired screen(frozen 계측기: PFC (c_p,c_d)=(1.0,0.5)·teacher 동반): p̂_PFC ≥ .8 ∧ p̂_zero ≤ .2 ∧ reset 비-clean, **CRN 20 seeds/draw** — **k=1·k=2 각각 통과 draw ≥ 8/12**(coverage 목표 = d1–d2, 18 §4 ⓒ). screen CRN seed 대역 = **300–319 신규 예약**(全 기존 대역과 서로소; 0-e seed 대장 등재).
- **복수 후보 선택 규칙**: robust val 최대 → tie: min(k1, k2) 통과 draw 수 최대 → tie: 리파인 스텝 최소(결정론).
- 주의: 본 screen = 탐색-시점 필터이지 admissibility 인증 아님(18 §6) — 채택 witness도 bank v2 생성·독립 validation(n=100)을 타 witness와 동일하게 통과해야 함.

### 2026-07-17 (zz) — ✅ 게인 동결 (c_p,c_d)=(1.0,0.5) + dev 12셀 PFC 재평가: v20 감쇠 = 실질 난이도(교락 해소) · v24 = d2–d4 회생 · v16 = 재리파인 트리거

- **게인 스캔**(인프라 커밋 `24c3026` = 결과 판독 전 커밋 = 선택 규칙 사전등록 순서 준수): tune 번들 = 신규 variant(rng 81k·seed 8.0M — dev 7.0M/sealed 9.0M/전 역사 seed족과 서로소, `tests/test_a3d_gain_scan.py` 락; dev·sealed 재생성 바이트-동일 회귀 확인) → 9 combo × 12셀 × 10판 = **1080판**: pooled .433–.492 **평탄**(계측기 게인-강건 = 좋은 신호) → 사전등록 규칙 적용 = **(c_p, c_d) = (1.0, 0.5)**(59/120, tie-break 미발동 순수 argmax). 산출 = `results/a3d_gain_scan.json` + `results/a3d_bundle_tune.json`.
- **dev 12셀 PFC 재평가**(frozen 게인, 30판/셀 = 360판; `results/a3d_calibration_dev_pfc.json`): screen(.8 point) **PASS 4셀 = d1/v20 .93 · d2/v24 .80 · d3/v24 .80 · d4/v24 .80** (0-c 개방루프 2셀 → 4셀; v24 d2·d4가 폐루프에서 feasibility 진입 — 단 zero 공짜 .70/.30 잔존 = draw-필터 대상). d1/v24 .03 = 구조 선점 재확인(C 유지). v16 = .47/.10/.17/.07.
- **교락 해소((uu) ③에 대한 답)**: v20 k-감쇠는 개방루프 취약이 **아니라 실질 난이도** — 지터-상쇄 PFC로도 d2 .63 / d3 .40 / d4 .37(개방루프 대비 +.10/−.07/+.04 = 이득 미미). 반면 v24는 회생. 잔여 실패 = 명목-참조 추적이 못 잡는 성분(공격자-반응 창 이동·MC 판정 잡음) — "회복 가능 셀 오폐기" 우려는 v20에선 사실상 불성립, 계측기 승격은 v24 회생으로 정당화.
- **v16 판정**: 전 셀 PFC ≤ .47 → 18 §4 비준 플로우대로 **재리파인 1회 트리거**(수락 기준 = 도착형 6조건 + coverage 목표, 탐색 **전** 고정 — 다음 구현). **coverage 매트릭스 초안(0-e 동결 대상)**: v24 → d2·d3·d4 / v20 → d1(+d2 저신뢰 조건부) / v16 → d1·d2(재리파인 목표; 3자 예시 정합). 스테이지 커버: d1 = v20 / d2 = v24(+조건부) / d3·d4 = v24.
- 생성기 스펙 큐(0d-1 구현 시): paired screen(PFC-pass ∧ zero-fail) 결합 수율 추정 — d2/v24 ~.24·d4/v24 ~.56 → 12 draws로는 최소 수록 8 미달 위험 → **draw 시도 상한 상향(예: 48시도/셀) 사전등록 필요**.
- seed 대장 += tune(rng 81k / reset 8.01M–8.08M). **다음: ⓐ v16 재리파인 probe(도착형 6조건 수락) 구현·1회 실행 → witness set·coverage 매트릭스 동결 ⓑ 생성식 draw-필터(6조건 rejection + zero 발사시점 히스토그램 + 시도 상한) 구현 → bank v2 1회 생성.**

### 2026-07-17 (yy) — ✅ 0-d Step 1 구현: Gate A PFC + Gate B family + 폐형식·trace 락 (t-free +17) — 게인 스캔·witness 재평가 대기

- **산출**: ① `shepherd/train/pfc.py` — PFC(무차원 게인 K_p=c_p/T_k²·K_d=c_d/T_k, T_k=kΔt; **nominal-앵커 참조 롤아웃** — 동역학이 결정론이라 개방루프 demo는 스폰 지터를 그대로 보존하고, PFC의 가치는 명목 참조 추적으로 그 지터를 상쇄하는 것; 참조 소진 후 터미널 홀드; norm-클립 ≤30) + Gate B family(λ-brake a=−λv·attpd = 공격자-유도 리드 포인트 PD — obs-전용, k 미사용(뱅크 메타라 구조적 불가), 생성자 시그니처에 특권 인자 금지) + 폐형식 R·O·nominal_from_bank(entry_idx = bank["entries"] 전역 인덱스, a3d_bundle_gen 그룹핑과 일치 확인) ② `a3d_calibration.py` arm 확장(pfc/lam<λ>/attpd; --bank·--cp/--cd·--gb-*; pfc/attpd 행에 params 기록; finalize = **feasibility_arm 자동 선택(pfc>demo)**·gateb_best·pfc_gateb_gap·obs_hard EXAMPLE 플래그(0.4, 0-e 확정)·note에 "point screen은 인증 아님·binding 판정 = 독립 validation LCB" 명시; 구 arm 4종 레코드 포맷 불변 = 기존 progress 재개 호환) ③ `tests/test_a3d_pfc.py` **+17 테스트**.
- **3자 필수 항목 이행**: ⓐ 폐형식 unit test — R·O vs 적분기 복제 k∈{1,2,4,8}×{v0 하한·상한} 정확 일치 + **docs/18 정정 k=1 행(0.0225–0.06) 명시 락** ⓑ **zero-coast env rollout trace 대조 PASS** — gating_env_for_spawn(d2 ep0) reset_to 후 k+2 스텝 전 구간 limiter 위치 == p0+j·v0·Δt(atol 5e-4, obs float32) = "스폰→t=0 사이 정확히 k회 이동" 시간 인덱스 계약을 실제 env 경로에서 실측 확인(bank 스크립트 k회 이동과 정합 — 3자 "k+1이면 식 재기술" 분기는 불발) ⓒ PFC ≡ demo(무지터 시 보정항 0)·**지터 상쇄 락**(σ0.02급 지터에서 endpoint 오차: 개방루프 = |δ| 보존(1e-9 정확) vs PFC < 0.6·|δ| 전 리미터).
- **검증**: 신규 17 + 인접 회귀 66(test_a3d_bank/bundles/v4prime_pin/trainer·a3_reverse·env_m3) **전부 green** — 클라우드 샌드박스에서 GitHub 클론(3ab3fb2, 리포 공개 상태라 무인증 클론 가능) 기반 실행; gymnasium/pettingzoo pip 설치로 t-free 스위트 구동 확인. arm 플러밍 스모크 1 ep(pfc len13/fire1·lam5/attpd 80스텝 무발사 — **기록 없음**; dev admissibility 측정은 §8 순서 준수 = 게인 동결 전 롤 금지).
- **다음(§8-1 잔여 → §8-2)**: ⓐ 게인 스캔 — tuning-seed 전용 에피소드(모든 기존 seed족과 서로소)에서 (c_p,c_d) grid·Gate B grid 선택 → 0-e 동결 후보 확정 ⓑ v16 PFC 재평가(§8-2) → 재리파인 1회 여부 → witness set 동결 ⓒ 생성식 draw-필터(6조건 rejection + zero-arm 발사 시점 히스토그램) 구현.

### 2026-07-17 (xx) — ✅ 비준 확정: 0d-1~5(3자 수정승인 사양 그대로) + 0d-3b = (ii) — 0-d 구현 착수

- **Hyunjun 최종 비준(18 v0.2 §10 확정)**: 0d-1 A+C / 0d-2 조건부 A / 0d-3 2-게이트 B / 0d-4 2단계 B / 0d-5 A + **0d-3b = (ii)** — Gate B 경고 셀은 training bank에 유지하되 **confirmatory(method-competence) 클레임 대상에서 제외**(2-tier 클레임 구조 18 §8.5-②와 정합). 확정 사양의 수치·seed 대장·게인 grid 문구 고정 = 0-e 일괄 사전등록 커밋.
- git 위생 확인: Windows `git reset` 실패 = plumbing 커밋 잔류 stale `HEAD.lock`(mount unlink 불가) — VM측 mv-aside 조치, 이후 HEAD·branch ref `3ab3fb2` 일치·index 정상(50KB)·워킹트리 clean·origin 동기(970b039..3ab3fb2 push 완료). 잔재(HEAD.lock.aside*·*.stale*·objects tmp_obj·URP/_to_delete/) = 전부 무해, Windows에서 일괄 삭제 가능.
- **다음 = 0-d Step 1(18 §8-1 측정기 동결)**: `shepherd/train/pfc.py`(PFC 무차원 게인 + Gate B reference-free family) + `a3d_calibration.py` arm 확장(pfc/gateb) + 폐형식 R·O unit test + teacher 판정 시점 rollout trace 대조 → 게인 스캔(tuning seed 전용, admissibility 데이터 불가침) → §8-2 witness 재평가(v16).

### 2026-07-17 (ww) — 3자 검토 접수·판독: 5/5 "수정 승인" → docs/18 v0.2(전 항목 반영) — Hyunjun 최종 비준 대기(+오픈 포인트 0d-3b)

- **검토 결과(docs/18 v0.1 대상, 접수본 = `URP/a3d_0d_external_review_2026-07-17.md`)**: 0d-1 수정 A+C / 0d-2 조건부 A / 0d-3 수정 B / 0d-4 수정 B / 0d-5 수정 A — 방향 전부 승인. 필수 정정 3: ① §1 k=1 오버슛 표 2× 오류 ② demo_cl 특권 정보 = realizability 갭(최대 누락 지적) ③ §8 순서(v16 재리파인이 재생성 뒤 = 재생성 1회 원칙 충돌).
- **우리 재검증 = 리뷰어 지적 오류 0건**: 적분기 복제 시뮬(v′=v+aΔt; p′=p+v′Δt)로 R=v0Δt(k−1)/2·O=v0Δt(k+1)/2 전 k×{v0 하한·상한} 정확 재확인(오차 ≤1e-16; demo 롤 = L* 도착·v_end≈0) — **k=1 O = 0.0225–0.06m, 표만 2× 오기·식 정상**(정정은 d1/v24 C-제외 결론을 강화) · CP 단측 95% 재계산 4/20 UB .401·0/20 .139·1/20 .216·16/20 LB .599(리뷰 수치와 소수 3자리 일치) · gap≥.4 point 중복(demo≥.8∧zero≤.2 ⇒ 자동 ≥.6) 확인 · ε=.4 파워 스케치(n=100, demo .80/zero .15 → LCB≈.56 유효 변별).
- **docs/18 → v0.2 반영(채택 매트릭스 = 18 §9, 기각 0)**: 0d-1 = v0 후보 유한 grid(≤3/셀, 상한 0.8 고정)·목적함수 max(p̂_PFC−p̂_zero) s.t. ≥.8/≤.2·tie-break = v1 분포 최근접·construction/validation seed 서로소·필터 전후 분포 보고 의무 / 0d-2 = 스테이지×witness coverage 매트릭스 탐색-전 동결·1회 한정·negative result 보존·"predecessor-construction feasibility" 스코프 / 0d-3 = **2-게이트 오라클**: Gate A = **PFC**(구 demo_cl — 특권 명시, "정보공간이 다름" 수용; 무차원 게인 K_p=c_p/T_k²·K_d=c_d/T_k 전역 1쌍, gain-tuning seed 분리) + Gate B = reference-free obs-호환 컨트롤러(brake·λ-brake·공격자-상대 유도 타깃만 — 3자 예시의 '목표'가 witness 슬롯이면 특권 누출이라 obs-유도로 한정 = 유일한 부분채택) 전 셀 기록+경고 문턱 / 0d-4 = **2단계 통계**(draw-screen n=20 paired point → 서로소 validation n=100, LCB95(paired Δ)>ε=.4; gap point 조건 삭제·경계 증량 규칙 superseded; episode vs training-seed 추론 단위 분리 명시) / 0d-5 = 공통-σ 평가 grid(전 스테이지 × {배정σ, 공통 .005} 최소, 전 arm + learned policy, 진단 전용). **§8 순서 교체**: 측정기 동결 → witness 동결 → 생성식 동결(= 0-e 사전등록 일괄커밋) → bank v2 **1회** 생성 → 번들 v2(**sealed-v1 구조 폐기 기록·sealed-v2 해시**) → 독립 판정(6 arm×n=100, 이후 생성식 재조정 금지) → V-5′/exit/δ_min 동결. 구조 채택 5(18 §8.5): **bank v2 정의 = action-necessary·forward-verified·observation-realizable predecessor synthesis**·2-tier 클레임(mechanistic policy>zero vs method vs brake — brake-강 셀 제외 금지)·암기 진단(unique draw·acceptance ratio·held-out draw·unseen CRN)·witness-단수 스코프(복수 witness/held-out geometry = P2·논문 등재)·teacher MC-spike 보조 로깅(fire-시점 robust-clean fraction, 판정 계약 불변).
- **대기: Hyunjun 최종 비준 — 0d-1~5 + 오픈 포인트 0d-3b(Gate B 지위: i 기록·경고 / ii confirmatory 클레임 제외 / iii 하드 게이트; 권고 = ii)** → 비준 후 0-d 구현 착수(§8 1단계 측정기부터; k=1 폐형식 unit test + teacher 판정 시점 rollout trace 대조 포함).

### 2026-07-17 (vv) — 0-d 결정 5건 옵션 비교·비준 문서 (docs/18) — Hyunjun·3자 비준 대기

- (uu) 설계 입력 5건을 옵션 비교·비준 체크 문서로 정식화: **`docs/18_a3d_bankv2_options.md`**(자기완결, 3자 검토 겸용; 검토용 사본 = `URP/a3d_bankv2_options_brief_2026-07-17.md`). 신규 폐형식 유도(§1): 스폰 오프셋 **R = v0Δt(k−1)/2 ⇒ k=1은 구조상 슬롯 위 스폰**(d1/v24 선점은 v0·방향 재추첨으로 구제 불능), zero 오버슛 **O = v0Δt(k+1)/2 ∝ v0** ⇒ "운동량 축소"는 저k에서 공짜를 늘리는 방향 — 옵션 A를 '축소'가 아닌 **draw-level 6조건 rejection + 셀별 v0 재보정**으로 재정의.
- 권고 패키지(비준 대상): **0d-1 A+C**(d1/v24 = C 즉시·d4/v24 = A 구제 기대·d2/v24 = A 후 잔존 시 C; B는 V-1 개정 재비준 조건의 에스컬레이션 예약) / **0d-2 조건부 A**(0d-3 재측정 → 재리파인 1회 → 실패 시 폐기+스코프 명시) / **0d-3 B**(demo_cl = clip(a_demo + K_p·Δp + K_d·Δv, |a|≤30) 승격, 개방루프 demo 진단 병기, 게인 전역 1쌍 dev-고정 — 리뷰 문면 "demo/oracle" 상정과 정합, ⑤ 측정기 정의 변경은 0-e 명시) / **0d-4 B**(문턱 .8/.2/.4 불변 + draw n_z=20 seeds + 경계 셀 ±0.07만 60판 단일 에스컬레이션) / **0d-5 A**(σ 램프 유지 + bank v2 검증에 σ-스윕 {0, 배정σ, .02} 진단 내장; d4 = robust-마진 계측지 유지).
- 결정 위상: 0d-3 → 0d-1 구현·재생성 1회 → 5-arm 재보정(zero/random/brake/demo/demo_cl) → 0d-2 판정 → 0-e 일괄 사전등록. zero-arm 발사 시점 히스토그램을 bank 검증기에 동승(d4 en-route 가설 판별). 규율 재확인: 문턱 조정 구제 금지·재생성 1회·sealed 불가침·트립와이어 8/31.
- 다음: 3자 검토 접수 → Hyunjun 비준(비준 결과 = (ww) + 0-e) → 0-d 구현 착수.

### 2026-07-17 (uu) — ✅ Phase 0-c 마감 (`970b039`): 12셀 전체 지도 — admissible **2/12**(d1/v20·d3/v24), 관성 공짜는 k-비단조(d2·d4의 v24만), v16 가족 전멸 — bank v2 설계 입력 확정

- **재현성**: 서버 1440판 중 샌드박스 선행 360판(d1/d2×zero·demo)과 겹치는 12셀 **정확 일치**(동일 번들·seed의 크로스 플랫폼 결정론 실측 — run 2a "비트-재현" 관찰의 CPU 교차판).
- **전체 표** (arrival_capture, 30판/셀, 예시 규칙 = demo≥.8 ∧ zero≤.2 ∧ gap≥.4):

| 셀 | zero | random | brake | demo | 판정 |
|---|---|---|---|---|---|
| d1/v16 | .00 | .03 | .13 | .40 | fail(demo) |
| **d1/v20** | .00 | .10 | **.93** | .83 | **PASS** |
| d1/v24 | — | — | — | — | 선점(reset_clean .97) |
| d2/v16 | .03 | .00 | .00 | .13 | fail(demo) |
| d2/v20 | .00 | .03 | .37 | .53 | fail(demo) |
| d2/v24 | **.70** | .43 | .77 | .77 | fail(zero) |
| d3/v16 | .00 | .00 | .00 | .13 | fail(demo) |
| d3/v20 | .00 | .00 | .00 | .47 | fail(demo) |
| **d3/v24** | **.00** | .00 | .63 | **.80** | **PASS** |
| d4/v16 | .00 | .00 | .00 | .07 | fail(demo) |
| d4/v20 | .00 | .00 | .00 | .33 | fail(demo) |
| d4/v24 | .30 | .00 | .00 | .77 | fail(zero) |

- **판독 5**: ① **관성 공짜 = k-비단조**: v24에서 d2 .70 → d3 .00 → d4 .30 — 핀이 d3 공짜를 소거(미핀 시절 d3 zero .57과 대조; 과도 overshoot가 창 시점과 어긋남)하되 d2(overshoot 소)·d4(장기 coast)는 잔존 → ⓑ(zero-fail 마진)는 **셀 단위**로 걸어야 함, k 단조 가정 금지 ② **v16 가족 전멸**(demo max .40): 약한 witness 창은 배치 σ+fresh CRN에서 개방루프로 못 버팀 ③ **v20 demo 감쇠**(.83→.53→.47→.33): 개방루프 재생의 지터 누적 — "셀 불능"과 "개방루프 취약"이 교락 → **feasibility 오라클을 폐루프 추적기(demo_a + K_p(p_demo−p) + K_d(v_demo−v))로 승격할지가 0-d 결정 사항**(리뷰의 demo≥.8은 개방루프 전제였음) ④ brake는 k≤2에서 강(d1/v20 .93 = demo 초과)·k≥4에서 자멸(스트랜딩) — 경쟁선으로 유지하되 스테이지별 해석 주의 ⑤ 선점은 d1/v24 한 셀 = ⓐ(스폰 비-clean)로 정확히 소거 가능.
- **0-d 설계 입력 (Hyunjun 결정 5)**: (1) v24 계열 관성 예산 — 운동량 축소 vs 측면 도착 기하 vs 해당 (k,witness) 셀 제외 (2) v16 계열 — 재리파인(신규 witness 탐색) vs 폐기(가족 폭 축소 수용) (3) feasibility 오라클 = 개방루프 demo 유지 vs 폐루프 추적기 추가(③의 교락 해소; 추가 시 admissibility의 "demo" 정의 변경 = 사전등록 문구에 명시) (4) admissibility 최종 수치(예시 .8/.2/.4 vs 완화) + zero-fail 마진의 CRN 표본 수 (5) 스테이지 σ 정책 유지 여부(감쇠의 주인이 σ 누적인지 확인용 σ-스윕은 bank v2 검증 게이트에 내장 가능). 결정 후 = bank v2 생성식 구현 → 재생성·재검증 → 번들 재생성 → 0-e 일괄 사전등록.

### 2026-07-16 (tt) — Phase 0-a·0-b 완료 + 0-c 중간 판독(d1/d2 × zero·demo, 핀·균형 번들): **bank v2 필요 확정** — 실패 모드 3분류(선점/관성 공짜/지터 취약), 유일 클린 셀 = d1/v20

- **0-a (`96b0326`)**: `gating_env_for_spawn`(V-4′ 핀, readback assert, 가족랜덤 미적용 = 번들 결정론; d0 무키 = nominal 원칙) + m3_eval_bundle per-ep 핀 라우팅·`gating_parity` 출력 + **eval_curve `cur`/`stage` = 사전-전이 기록**(+`transition` 필드; (rr) d3 오라벨 재발 방지) + 테스트 4. **0-b (`c8cf70f`)**: 균형 번들 30×{16,20,24}×{d1..d4} dev/sealed(`results/a3d_bundle_{dev,sealed}.json`, 360판씩) — 스폰 물질화(+demo_accels; bank 편집 면역)·스테이지별 σ 반영·reset seed 연속(재생 verbatim)·dev/sealed·역사 seed족 전부 서로소·**sealed = Phase 2 전 롤 금지**(러너가 --allow-sealed 없이 거부); m3_eval_bundle 핀-env 캐시(속도당 1빌드)+`per_episode` 플래그(기본 False = eval_curve 불변); calibration 러너 `a3d_calibration.py`(재개형·teacher 동반·--finalize 셀 표) + 테스트 5(균형·seed 서로소/연속·결정론 재생성·핀 소비 스키마·지터 스케일). 샌드박스 t-free green.
- **0-c 중간 (d1/d2 × zero/demo, 360판; 잔여 = brake·random·d3·d4 → 서버 1커맨드)**: arrival_capture —

| 셀 | zero | demo | gap | 판정(예시 규칙) |
|---|---|---|---|---|
| d1/v16 | .000 | .400 | .40 | FAIL(demo 낮음) |
| **d1/v20** | **.000** | **.833** | **.83** | **PASS — 유일 클린 셀** |
| d1/v24 | (reset_clean .967) | — | — | **선점**: k=1 되감기가 아직 창 안 → teacher 스폰 즉발, arrival 시험 불능 |
| d2/v16 | .033 | **.133** | .10 | FAIL: **지터 취약**(σ0.01 + fresh CRN이 약한 witness 창 파괴 — v1 검증은 정확상태 한정) |
| d2/v20 | .000 | .533 | .53 | FAIL(demo 낮음) |
| d2/v24 | **.700** | .767 | .07 | FAIL: **관성 공짜**(핀 상태에서도 — 속도 비정합이 아니라 limiter_v 자체가 해법을 나름; 리뷰 "이미 거의 해결된 상태" 실측) |

- **판독**: ① 예측 반반 — "핀 후 저k zero 확대"는 k=1에서 기각(zero 0/90, 선점 제외 전 셀 0), k=2 v24에서 강화(0.70) ② d1/v20 존재 = **SBE가 action-necessary 셀을 만들 수 있음의 실증**(개념 생존) ③ 나머지 셀 전멸 = **bank v2 필요 확정**, 생성 조건 = 실패 모드 1:1 대응: **ⓐ 스폰 비-clean**(선점 소거) **ⓑ zero-roll 실패 마진**(관성 공짜 소거 — 강한 witness에는 운동량 예산 축소/측면 도착 기하 등 설계 필요) **ⓒ demo를 배치 σ지터 × fresh CRN 하에서 검증**(취약 소거 — v1의 정확상태 검증에서 승격) = 리뷰 ⑤⑥ε + 선점 조건(자체 발견).
- 잔여 0-c: 서버 `python -m shepherd.scripts.a3d_calibration && … --finalize` → `results/a3d_calibration_dev.json` 커밋 → **0-d bank v2 생성식 설계(Hyunjun 결정: 운동량 예산·도착 기하·마진 수치) → 0-e 사전등록 일괄 커밋**. 부분 원자료 스냅샷 = outputs `a3d_calibration_partial_d1d2.jsonl`(진행 파일은 results/_calib/, gitignore).

### 2026-07-16 (ss) — 규명 + 외부 리뷰 채택: **게이팅 att_speed 미핀(오출제 3호) 확정 · (rr) d3 증분 철회 · SBE → action-necessary 재정의** — 파일럿2 긍정 주장 전면 유보, Phase 0(무학습 사전검증) 착수

- **규명((rr) ⓐ 이행; 리포트 = `results/a3d_stall_forensics.md`, 프로브 원자료 960판)**: ① "전멸 eval" = 붕괴 아닌 **全 d3 번들 측정치**(재귀속: `cur` 라벨이 전이 후 기록이라 오프바이원). trained d3 = **0~3/320 < zero 15/80 = 능동 이탈**(v24 공짜까지 소거·fire 0·len=자연 침투 길이) ② flatline = 비트동결 아닌 **수렴 + 고정 CRN + 이산 카운트**(return 미세표류 = 트레이너 정상; seed1/2 = d2 전진선 31/80에 정확히 2판 부족 고착, seed0 = 죽은 v16 34판 탓 살아있는 46판 중 87% 요구) ③ **근본 원인 = 게이팅 번들 att_speed 미핀**: `reset_to`가 att_speed 미소비 + 핀은 train rollout만(`_begin_episode`) + 공격자 env-scripted nominal 20 → **v16 全 arm 0/202(죽은 시험)·v24 무행동 0.57~0.93(공짜)·변별 v20뿐**. 코드 버그 아닌 **비준 설계 갭**(V-4 "eval nominal"과 게이팅 스폰의 자기모순) = A-3 σ·pilot1 D0 σ 이은 오출제 3호 ④ 리그(`results/a3d_mechanism_probe.json`): **brake(-30·unit(v) 1줄) 45/36/15 ≫ trained 34/29/0~3** — brake·demo는 전진선 통과, trained만 전 스테이지 미달.
- **(rr) 정정 — 외부 리뷰 지적 수용 (철회)**: (rr)의 "d3 유의 증분(31/80, p=.004)"은 **d2 측정치의 d3 오라벨**(@184320 = advance-eval, 위 ①의 오프바이원 피해를 (rr) 자신이 입음) → **철회**. 진짜 d3 = 0.000/0.000/0.013 = zero 대비 **유의한 악화**. 존속 양의 증분 = **d1뿐**(9/80 vs zero 1/80·random 2/80), 그마저 brake(45/80) 하위. Fisher 계열 p값 일괄 잠정 강등(paired 설계 부적합) — 주 추론 폐기.
- **외부 리뷰 접수·전 항목 실질 채택** (브리프 `URP/a3d_pilot2_review_brief_2026-07-16.md` → 리뷰 전문 `URP/a3d_pilot2_external_review_2026-07-16.md`, 채택 매트릭스 `URP/a3d_review_adoption_matrix_2026-07-16.md`; Hyunjun 비준 2026-07-16). 판정 요지 = "유보 정당·개정 = 오류 정정 맞음, 단 **핀+paired만으론 재개 불가** — SBE를 **action-necessary, forward-verified predecessor synthesis**로 재정의하라; 제한된 재설계·재실험 1회". 채택 핵심: ⓐ **V-4′ 게이팅 핀** = train–gate parity 복구(per-ep env 재구축, `build_m3_attacker_env` 재사용; **가족 랜덤화 미적용 = 핀만**, 번들 결정론 유지; d0(k=0)은 스폰에 att_speed 무키·t=0 즉발이라 핀 불요) + parity assert/스냅샷 ⓑ **V-5′** = paired 동일-ep contrast: exact **McNemar 단측** + Δ CI + **δ_min**(0.05~0.10, calibration 후·학습 전 고정), causal-arrival/harm discordant 분해, competence 리그 분리 보고(zero=무결성 null / brake=경쟁선 / demo=구성 상한 / oracle) ⓒ **exit 지표 교체**: captured_rate → **paired action-induced arrival**, 값은 컨트롤 calibration에서 유도·선등록 ⓓ **bank admissibility 6조건**(기존 4 + ⑤ demo 성공 ⑥ zero 규정마진 실패; gap≥ε, 예시 demo≥.8·zero≤.2·gap≥.4; P_demo는 teacher 동반 측정) ⓔ witness **균형 90판**(30×3) + **dev/sealed 번들 분리**(sealed = fresh CRN 서로소 — A-3 CRN-면도날 반영) ⓕ 추론 단위 = **training seed**(파일럿 seed별 제시·정식 10-seed·seed-cluster bootstrap = P1 Gate-A 기계 재사용) ⓖ **8항 사전 체크리스트**(Feasibility/Necessity/Headroom/Simplicity/Parity/Observability/Statistics/Integrity) = 이후 모든 스테이지 학습 착수 전 필수 ⓗ **unfreeze 기각** → teacher → clean-trigger classifier 복구 → joint 순서 ⓘ **하드 스톱**: 수정 bank·k≤2에서 LCB(Δ_{π−zero})≤0 ∧ brake 하위 지속 → 8/31 전이라도 튜닝 반복 금지·프레이밍 전환. 우리 보충 예측(매트릭스 §3): **핀 픽스는 저k zero 공짜를 오히려 확대**(k=1 구성상 zero가 t=0 정확 도착) → 저k 셀 admissibility 탈락 → **bank v2 재생성이 Phase 0 내 필요할 공산**.
- **Phase 플랜**: **P0(학습 금지)** = 0-a 핀+parity+`cur` 라벨 픽스(+테스트) → 0-b 균형 90판 dev/sealed 생성 → 0-c 5-arm calibration(zero/random/brake/demo/oracle) → 0-d bank v2(action-necessity 생성식) → 0-e V-2′/V-5′/exit 개정 일괄 커밋(δ_min·ρ·admissibility 수치 확정 = 사전등록) / **P1** = 3-seed scratch(teacher+ΔΦ 유지), 주판정 = paired causal-arrival vs zero(seed별), D1→D2 한정 / **P2**(P1 통과 시) = 10-seed·sealed·nominal-controller-consistent bank·classifier→joint·nominal transfer. **파일럿2 지위 = audit case 전용**(긍정 주장 금지·ckpt 진단 전용). 서버 규명 잔여(우선순위 개정): parity 자동검증 ≫ paired trajectory dump(d3 능동 이탈 기전: OOD 외삽/Φ 구배 역정렬/norm drift 판별) ≫ reward–advantage 분해 ≫ wandb 덤프·ckpt diff(보조).
- 산출물(본 커밋): `results/a3d_stall_forensics.md`(규명 리포트) + `results/a3d_mechanism_probe.json`(brake/demo 6 arm × 80판 per-ep — ※ 미핀 번들 측정치임을 meta에 명기). 0-a 코드는 후속 커밋.


### 2026-07-16 (rr) — ⚠️ A-3d′ 파일럿 2차: σ픽스 성공·V-5 문면 3/3 PASS — 그러나 **V-5 전제("무행동≈0") 측정 반증(무행동도 全 스테이지 PASS)** → 판정 보류, V-5′(paired contrast) 비준 대기

- **런 결과** (`79e6305`, 아티팩트 `bfdc3b9`): **D0 앵커 복원** — 첫 eval cap 0.9125/0.9125/0.900(reset_clean 0.950~0.975), 3/3 seed 20480에 d1 진입 = (qq) 픽스 의도대로 작동. 플래토: seed0 d1 arr 9/80(LCB95 0.067)·seed1/2 d2 arr 29/80(LCB95 0.269) → **V-5 문면 3/3 PASS**.
- **반증 (신규 무결성 컨트롤, 480판)**: 동일 하네스(`m3_eval_bundle`)·동일 게이팅 번들(`eval_spawn_fn`, eval_seed0 500000·ep 1:1 짝지음)·동일 teacher에서 리미터만 무행동/무작위로 교체 — zero: d1 1/80(LCB 0.003)·**d2 19/80(LCB 0.169)**·**d3 15/80(LCB 0.126)** / random(±30 uniform): d1 2/80·**d2 22/80(LCB 0.201)**·d3 7/80. **무행동 정책이 전 k≥1 스테이지에서 V-5를 통과** → docs/17 §4 "무행동·무도착 기준선 ≈ 0"은 k≥2에서 거짓(측정된 적 없는 가정이었음). **기전**: SBE 스폰이 주입한 limiter_v 관성이 a=0에서도 witness 창을 통과시키고 teacher가 그 순간 발사 = **구성이 만든 포획**. 컨트롤 정합성: null reset_clean이 실런과 정확 일치(d1 0.312=25/80·d2/d3 0.000) + spawn_capture ≡ reset_clean 항등(스폰-clean → t=0 즉발, 실런 전 seed·전 eval 동일 항등) — 실런 d1 cap 0.425 중 0.312는 teacher 공짜분.
- **contrast 재검정** (trained vs 스테이지별 최강 null, Fisher 단측): d1 seed0 9/80 vs 2/80 **p=0.028 유의** / **d2 seed1·2 29/80 vs 22/80 p=0.154 비유의**(vs zero도 p=0.060) / d3 seed1(최고 eval) 31/80 vs 15/80 **p=0.004 유의**. **판정: "arrival_capture = 재성형 등가물 1차 실증" 주장 불가. 생존 주장 = "SBE가 G0 물리 벽을 설계로 제거 + d1·d3에서 정책의 유의 증분". 주력 플래토 d2는 무행동과 미구별.** 방증: seed1·2가 d2에서 동일 29/80 수렴(게이팅 스폰 rng가 run seed 무관 → 번들 공유) = 결과의 스폰 지배.
- **V-5′ 개정안 (비준 대기 — 다음 런 착수 전 확정, 골대이동 방지 위해 본 반증 기록이 선행)**: 성공 = **동일 번들·동일 ep paired contrast** `arr(policy) − arr(zero-action)`의 LCB95 > 0 (절대 LCB 폐기). 무행동 컨트롤 = **상설 스캐폴드-무결성 게이트**(스폰이 정책이 벌지 않은 상태를 나르는 모든 캠페인에 적용). exit(captured 기준)의 공짜 성분 주석: d1 free 0.312 vs exit 0.40·d2 null 0.237 vs exit 0.30 — 자명 통과는 아니나 마진 얇음, contrast/net-지표 exit 검토. ※ 본 (rr) contrast는 MC seed 불일치 캐비앗(trained=seed1/2 런 eval_seed0 상이, ±3~5%p 판독 잡음) — **최종 재판정은 동일-seed 짝지음으로 재계산**.
- **부수 이상 3건**: ① seed0 102400 이후 21 eval 완전 flatline(예산 80% 무학습)·seed1/2 후반 동형 ② backoff 트리거 전부 **"전멸 eval"**(전 지표 0.000, fire_rate 포함) 후 즉시 복귀(seed1 d3↔d2 4회 thrash) — 정책 일시 붕괴 vs 전이 직후 오염, 규명 전 재런치 무의미 ③ **eval_curve `cur` 라벨 = 전이 후 기록이라 한 칸 어긋남**(0.000 eval은 실제 상위 d에서 측정) — 곡선 해석 주의; best.json 3/3 step 20480 고정(teacher 기간 frozen 무의미의 예상된 귀결).
- **인수 TODO 2건 (oo)**: ② **해소** — D0 σ=0 비트동일 스폰에서 reset_clean 0.950~0.975가 eval seed별로만 상이 → standalone-vs-env 경로차 아닌 θ=0.9 경계 MC 판독 잡음(n_samples 2000, 2.5~5%). ① **미해소·계획 무효화 발견** — (qq) 픽스가 D0 σ를 0.0으로 만들어 "D0 앵커에서 σ0.02 지터 후 robust 마진 재확인" 계측 위치 자체가 소멸 → **d4(σ0.02)로 재지정**.
- **산출물**: `shepherd/scripts/a3d_null_baseline.py`(상설 컨트롤 러너; ep-단위 게이팅 번들 정확 재현, 12-ep prefix로 데이터 동일성 검증) + `results/a3d_null_baseline.json`(6 arm × 80판, per-ep 0/1 벡터 포함 — paired 재판정에 재런 불요). **다음 순서**: ⓐ 정체·붕괴 규명(최우선) ⓑ V-5′ 비준 ⓒ 동일-seed paired 재판정 ⓓ d2 잔존 시 스폰/exit 재설계 → 이후에야 unfreeze(V-6).


### 2026-07-15 (qq) — ❎ A-3d 파일럿: D0 정체 = **게이트 산식 오류(자체 설계 실수)** — 재성형 가설 미테스트; A-3d′ 픽스(스테이지별 σ) 후 재런치

- **결과** (`07c94cb`, 아티팩트 `1c71d9f`): 3-seed 전원 D0 정체(전진 0, cap@369k), captured 0.21~0.26 flat, k≥1 표본 0 → V-5 형식 FAIL(미도달).
- **원인 (즉시 특정)**: sbe 전역 σ_pos 0.02가 D0에도 적용 — **A-3b R0(σ=0) 앵커 의미론을 조용히 파괴**. σ0.02의 스폰-clean = 0.27~0.42(프로브 실측 그대로: 게이팅 reset_clean 0.28~0.33 관측 일치) → teacher 하 captured 상한 ≈ 0.30 + 회복껍질(0.7×r@1 0.19) ≈ 0.43 < exit 0.45 = **구성상 통과 불가**. A-3(σ≫창)과 동형의 "잘못 출제된 시험"이 exit 문턱 쪽에서 재발 — 이번엔 진단 로깅(reset_clean_rate)이 즉시 잡음.
- 부수 관찰: D0에서 arrival_capture 0.01 blip(1/80) 산발 — σ0.02 비-clean 스폰의 1-step 껍질 회복이 간헐 발생(oracle r@1과 정합). 유의성 없음(계측만).
- **A-3d′ 픽스** (코드 소, 테스트 +2, 판정 경로 무접촉): sbe 스테이지별 `sigma_pos` 오버라이드 — **D0 = 0.0(진짜 앵커 복원)**, d1+ = 0.005→0.02 램프(보정-스케일 커리큘럼; k-스폰 지터는 도착 종점을 동일 σ만큼 흔들므로 작게 시작). exits 불변.
- 재런치: `REQUIRED_COMMIT=<본 커밋>` 동일 커맨드. 예상: D0 첫 eval에 cap ~0.9(A-3b R0 재현) → D1 진입부터가 본 실험.

### 2026-07-15 (pp) — ✅ A-3d 트레이너 구현 완료 (teacher-gate + ΔΦ PBRS + SBE k-사다리 + Wilson 게이트) — 서버 torch 테스트·파일럿 대기

- **① `shepherd/train/phi_potential.py`(신규, torch-free)**: robust potential Φ = mean_z σ((v_z−θ)/τ)·1[¬boxed] − β·std_z (**고정 Z_train = seeds 61~65**, audit 71~75 예약, n_phi 600 = 스캐폴드-충실도 선택·판정 미사용) + obs 파싱(frozen 레이아웃) + Wilson LCB/UCB + `teacher_fire`(obs[-3]≥θ ∧ obs[-1]>0). 실측: witness Φ=0.881 결정론·열화 상태 0.000·75ms/call.
- **② Curriculum `sbe` 모드**(make_env_m3): D-사다리 {d0 k0 (A-3b R0 앵커)…d4 k8, d5 nominal}, 스폰 = k0→robust witness(σ0.02·영속도) / k>0→**SBE bank 엔트리(limiter_v 정확 복사, 위치만 σ0.02 지터)**·att_speed 동반; **U-5 Wilson confidence 게이트**(80판 고정 CRN·전진 LCB>exit·후퇴 UCB<exit−0.05·sustain 불요)·cap 360k freeze·overrides() 상시 None(보상 무개입 구조 유지).
- **③ train_m3a a3d 훅**(`a3d:` 블록 없으면 전부 no-op): teacher-gate 발사(rollout+게이팅 번들, raw-obs 판독) · **fin freeze = 가중치 스냅샷-복원**(mappo.py 무접촉) · **ΔΦ write-in**(rew += α[γΦ(s′)−Φ(s)], terminal Φ≔0, phi 캐시로 스텝당 1회 평가·ep 시작 1회) · V-4 att_speed 핀(spawn→params) · U-4 분해(reset_clean/arrival_capture/spawn_capture/phi_shape_sum — ep records·rolling·eval 번들 集계 공통) · 게이팅 번들 episodes = gate.episodes(80).
- ④ `configs/m3a_a3d_pilot.yaml`(scratch 3-seed·520k) + `tests/test_a3d_trainer.py` **+9**(phi 파싱/결정론/β·Wilson·teacher·sbe 스폰 의미론(limiter_v≠0·att_speed·d0 영속도)·게이트 전진/후퇴/hold/cap·config 사전등록 정합(Z_train·k 단조·exit 단조·예산 룰·judgment 블록 = a3b와 동일)). t-free 5 스위트 70 green + 기타 회귀 기존 green.
- 캐비앗: fin freeze 중 frozen/heldout 번들은 learned(무학습 fire-head) → frozen 지표 무의미 기간(문서화, best-ckpt는 참고만·사다리 판정은 게이팅 번들); phi n=600·|Z|=5로 스텝 비용 ~+60%(520k ≈ 4h급/3-seed 병렬 예상).
- **서버(Hyunjun)**: push 후 ⓐ torch 테스트(수집≠green 교훈 — a3d 훅 경로 포함 실측) ⓑ 파일럿: `TRAIN_MODULE=shepherd.scripts.train_m3a CONFIG=configs/m3a_a3d_pilot.yaml OUT=results/m3a_a3d_pilot REQUIRED_COMMIT=<본 커밋> GPU=0 SEEDS="0 1 2"` ⓒ 마감 시 held-out 4본 불요(teacher 기간) — eval_curve/run_state + 게이팅 지표 커밋. **판정(V-5)**: arrival_capture LCB95 > 0 (k≥1 스테이지 게이팅 번들) = 재성형 등가물 최초 실증; D0 앵커에서 위임 TODO 2건(robust 마진·union 경로차) 교차 확인.

### 2026-07-15 (oo) — ✅ A-3d 위임분(bank 생성기 + reset_to 속도 주입) 검수 합격·수록 — 트레이너(ΔΦ/teacher-gate) 착수

- **위임 산출물** (Opus 4.8, 하네스 `b3c8997` 계약): `a3d_sbe_bank.py`(SBE 합성+4조건 게이트+분할/merge CLI) · `env_m3.reset_to`의 optional `limiter_v` (수 줄 diff, shape 검증) · `tests/test_a3d_bank.py` 9종 · 구현 노트(`URP/a3d_impl_notes/`).
- **검수(독립 재현)**: ① env_m3 diff 최소 확인 ② 테스트 47 green 재실행(신규 9+회귀 38) ③ **bank 전체를 샌드박스에서 재생성 → 노트 수치와 일치**(144/144 kept·roll_err max 7.1e-15·robust min 0.90/med 1.00·per-k 36×4) — 결정론 재현으로 조작·환각 배제 ④ 이산 유도 (k−1)/2 + 잔차 1회 보정 = 타당(docs/17의 (k+1)/2는 연속 근사 표기 — 17 정정 불요, 구현 노트가 정본 유도). `results/a3d_sbe_bank.json` 수록(스키마: spawn{limiters·limiter_v·att_p/v·att_speed}+demo_accels+verify).
- **인수 TODO 2건**: ① robust_frac min 0.90 임계 밀착 — 트레이너 σ_pos 0.02 지터 후 재확인(커리큘럼 D0 회귀 앵커에서 계측) ② bank clean 판정 = standalone union vs env readout 미세 경로차 — D0에서 교차 확인(파라미터 동일이라 실질 일치 예상).
- 다음 = 트레이너: phi_potential 모듈(고정 Z_train PBRS)·Curriculum sbe 모드(k-사다리+Wilson LCB/UCB 게이트)·train_m3a a3d 훅(teacher-gate·fin freeze·ΔΦ write-back·att_speed 핀·U-4 분해)·config·테스트.

### 2026-07-15 (nn) — ❎ U-1 정식 oracle: **G0 확정 (물리 지배)** — A-3c 학습 실험 생략, A-3d 설계로 직행 (사전등록 분기 이행)

- **정식 결과** (`27a8c68`, 3 witness × σ{0.02,0.05,0.1} × 스폰 12 × 후보 32, k{1,2,3}): **r@2 = r@3 = 0.00 전 셀**(스폰 108) — "정지 리미터(2스텝 15cm)는 이동 창(스텝당 0.8~1.2m)을 물리적으로 못 쫓는다"의 실측 확정. r@1만 얇게 생존: x20v24 σ0.02 **0.50**·x16v20 0.08·x12v16 0.00 (action volume 0.03~0.09 = 후보 32중 1~3개의 좁은 통로; winner robust 0.67~1.0, 단 x20v24 σ0.05는 0.0). 게이트: σ0.02 r@≤2 pooled **0.194 < 0.3**, σ0.05 r@≤3 **0.056 < 0.1** → **G0**.
- **의미**: A-3 계열의 position-noise 스폰은 대부분 **회복 불가능** — 보상·credit 설계와 무관하게 재성형 학습이 성립할 수 없는 스폰 분포였음(피드백 3분법의 "물리" 가지로 판정). 논문 진단 행 확보: "위치-잡음 후진 커리큘럼의 단기 회복가능성 상한 = 1-step 껍질(σ0.02, 최강건 witness에서만 0.5)".
- **A-3d 설계 방향 (docs/17 초안 예정)** — 되감기의 부트스트랩 문제 해결이 핵심: R0 성공 에피소드는 witness에서 **시작**하므로 t−k 접근 궤적이 존재하지 않음(그게 원래 findability 문제). 해법 = **합성 후방 연장(synthetic backward extension)**: AnalyticBackend가 단순 적분기이므로 시간 역행 적분이 유효 — witness 도착 조건(위치 = witness, 속도 ≈ 0)을 만족하는 리미터 도착 프로파일(감속-도착 폐형식)과 공격자 후방 상태(직선 역외삽 + 전방 재검증 슈팅)를 구성해 **t−k 상태를 합성**하면, witness 창에 도달하는 행동 시퀀스가 **구성상 존재 보장**(회복가능성 내장). k-사다리 1→2→4→8 후진, 스폰 dict에 리미터 속도 주입(reset_to 확장 — limiter_v 필드), 교사-게이트 발사(U-2)·ΔΦ 보상(U-3)은 그대로 이식(이제 회복 가능한 분포 위라 정당), 지표 = U-4 분해.
- 다음: A-3d 설계 문서(docs/17) → 비준 → 구현. 트립와이어 8/31까지 1 시도 사이클 여유.

### 2026-07-15 (mm) — A-3c 설계 v0.1 (docs/16, U-1~U-7 비준) + U-1 회복가능성 oracle 구현·스모크 — 정식 oracle(서버) 대기

- **docs/16**: Q1(비-clean 스폰 물리 회복가능성) → Q2(교사-게이트+ΔΦ로 재성형 학습) 순서 고정; **분기 사전등록** — G1(σ0.02 r@≤2 ≥0.3 ∧ σ0.05 r@≤3 ≥0.1) → A-3c 학습 실험(U-2 teacher-gate·U-3 PBRS ΔΦ(고정 Z_train·terminal 0·α0.5/β1.0/τ0.05)·U-4 reshape_capture 분해·U-5 confidence 게이트·U-6 진단 로깅·U-7 3-seed→confirmatory) / **G0(미달)** → 학습 생략, **A-3d 궤적-되감기 직행**(R0 정책 3본 = 검증된 성공-궤적 생성기 → t−k 스냅샷 뱅크(리미터 속도 포함), 회복가능성 구성상 보장).
- **U-1 구현** (`a3c_recoverability_oracle.py`): reset-nonclean 스폰에서 리미터 상수-가속 후보 M개를 **순수 kinematics k스텝**(무발사 구간 = 결정론; 공격자 = 실제 scripted 정책) → 종점 union 1회 평가 — recoverable@k·action volume·best Δv·winner robust. 물리 상한 명기: 정지 리미터 변위 3.75/15/34cm(k=1/2/3) vs 공격자 0.8~1.2m/스텝 → k≥2는 "추적"이 아니라 "예측 배치"만 가능.
- **스모크 (샌드박스, 참고치 — 약한 탐색·소표본)**: x16v20 σ0.05 → r@1,2 = 0/4; σ0.02 → r@1 = 1/4(vol 0.05), r@2,3 = 0/4. 물리-지배(G0) 방향 신호이나 **단정 금지** — 정식 판은 서버(3 witness × σ 3종 × 스폰 12 × 후보 32).
- **서버(Hyunjun)**: push 후 `python -m shepherd.scripts.a3c_recoverability_oracle --out results/a3c_recoverability.json` (분할: `--witness 0..2 --sigma 0.02|0.05|0.1`; ~1h급) → JSON 커밋 → G1/G0 판정 → G1이면 U-2/U-3 구현 착수, G0이면 A-3d 설계 상세화.

### 2026-07-15 (ll) — 심층 피드백 접수·검증 판독 (15 브리프 대상) — 자기-정정 1·리뷰어-정정 3·채택 9; A-3c = "회복가능성 oracle → 교사-게이트 발사 → ΔΦ 리미터 학습" (U-1~U-7 비준 대기)

> 전문 = `URP/gpt_deep_feedback_a3b_2026-07-15.md`. 원칙: 무조건 수용 금지 — 산수·코드 대조 후 채택.

**자기-정정 (우리 (kk) 판독의 오류):**
- **seed1 "선택적 발사" 철회.** 리뷰어의 무조건부-발사 모델(상태 무관 fire 0.31, prevalence 0.42) → cap 0.130·waste 0.180 예측이 관측(0.14/0.17)에 적합함을 재계산으로 확인. TPR/FPR 미계측 상태에서 선택성 주장 불가 — 정확한 표현은 **"전역 발사 성향(logit intercept)의 시드별 상이한 이동"**(seed0/2 상향 고착, seed1 하향 활주). "상태 조건부 선택 발사"의 존재는 미확인.

**리뷰어-정정 (코드·데이터 실측):**
1. §6 관측가능성 전제 — "**actor가 sample-specific clean을 알 수 없다**"는 부정확: obs[-3:] = 현재 상태의 표본 (v_soft, worst, p_feasible) — clean 지표가 관측에 직접 포함됨. 단 obs 표본(전 스텝 post-move 평가)과 판정 표본(당 스텝 재추첨)이 달라 **flip 잔여 노이즈 = robust-frac 갭**은 실재 — separability probe는 여전히 가치(예상: 높은 AUC), fire 결정 기준을 robust 기대-clean으로 두라는 결론은 유지.
2. §3 리미터 물리 — a=80 m/s²(0.1m/1스텝) 산수는 맞으나 **a_lim_max = 30**: 1스텝 3.75cm·2스텝 15cm·3스텝 34cm — 단일-스텝 불가론은 과장, 관건은 "이동하는 창(공격자 0.8~1.2m/스텝)의 2~3스텝 추적". → 불가능 단정 금지, oracle이 판정.
3. "witness도 step2+ non-clean" — 우리 oracle의 systematic 측정 아님(사례 n=1 + 이론). recoverability oracle이 정식 측정.

**채택 (9):** ① Bayes-bias 플립 프레임 — p* = 1/(R+1) ≈ 0.13~0.16 vs 스테이지 prevalence(R1 0.27~0.42 > p* > R3 0.01~0.09) → **두 모드 = 상태-무관 전역 bias의 합리적 양극단**, 커리큘럼이 최적 bias를 뒤집음 ② **인과 교착**: 즉시-발사가 리미터 transition 삭제 ↔ 재성형 부재가 대기 가치 삭제 ③ **recoverability oracle 선행**(reset-nonclean에서 리미터 행동 최적화 + step2~4 oracle fire → recoverable@k·action volume·robust recovery — 실패 원인 3분법: 물리 불능/탐사 문제/credit 문제) ④ 보상 순위: **ΔΦ robust potential(PBRS 차분형, 고정 seed bank·terminal Φ=0)** > per-limiter 현재-상태 hold-차분 D^Φ > margin level 단독(기각 — 스폰-운 지불·dwell 유도) ⑤ **teacher-gated finisher scaffold**(R0가 trigger 학습을 이미 검증 — 재성형 실험에서 fire 동시학습은 해석 혼입) ⑥ reshape_capture 6분해(spawn/reshape/missed/false/improved/recoverable-reshape) — 성공 지표 = P(capture | reset-nonclean, recoverable) LCB > 0 ⑦ LCB/UCB confidence 게이트 + 고정 80~100판 CRN bank(명시적 사전등록 개정으로) ⑧ 진단 로깅: TPR/FPR·fire-logit AUC(reset/robust-clean)·**fire vs cont PPO ratio 분리**(joint-ratio가 Bernoulli gradient를 clip할 가능성 점검) ⑨ 클레임 경계(§9 목록 그대로 — 지지: privileged-스폰 말단 습득·spawn-luck 천장·모드 분기 / 불지지: 능동 재성형·nominal 포획·선택 발사).
**기각/보류:** 강제 최소발사율·글로벌 entropy floor·fire-advantage clipping(리뷰어 자신도 비추천 — 동의), fire-head 최적화 분리(진단 ⑧ 결과 후 필요시), margin level 단독(기각).

**A-3c 설계 골자 (U-슬롯, docs/16 초안 예정):** U-1 recoverability oracle 선행 게이트(사전등록 문턱 포함) / U-2 teacher-gated finisher(reset-clean 즉발·Φ-문턱 발사·그 외 mask; TRAIN 전용 — frozen/heldout 판정은 learned policy 그대로, fire-head는 freeze→후속 unfreeze) / U-3 리미터 보상 = r_team + α·ΔΦ (Φ = mean_z σ((v_z−θ)/τ)·1[¬boxed] − β·std_z, 고정 Z_train, 차분형·terminal 0; U-3b: D^Φ는 phase 2) / U-4 지표 = reshape_capture 분해 / U-5 confidence 게이트 + 고정 bank / U-6 진단 로깅 일괄 / U-7 스코프 = 3-seed 기전 실험 → 성공 시 10-seed confirmatory (트립와이어 8/31 불변).

### 2026-07-15 (kk) — ✅ A-3b 파일럿 중간 게이트 **PASS** — 표현 가설 확정(캠페인 최초 학습 포획, R0 cap 0.95~1.00); 새 벽 = "clean일 때 쏘기"는 배웠으나 "clean으로 만들기"는 아직

- **런** (`d663a51`, 아티팩트 `4d4a750`): scratch 3-seed × 520k, captured_rate exit.
- **형식 판정 (사전등록)**: (i) R0 통과 = **3/3** (첫 eval에서 trCap 0.95/1.00/0.95, 40,960스텝에 전원 r1 전진 — 즉시-발사 습득) ∧ (ii) R2 도달 = **3/3** (seed2는 r3) → **중간 게이트 PASS** ((iii) heldout 비영은 0/200 ×3으로 미충족이나 (i)∧(ii)로 충분). **표현 가설 확정 — L-2stage 불요.** oracle→학습 체인 완결: "강제로 쏘면 된다"(jj) → "쏘라고 배울 수 있다"(본 결과).
- **새 벽의 정밀 위치 — "spawn-luck 천장"**: r1(σ0.02)~r3(σ0.1)에서 captured_rate가 **스폰-clean 베이스라인에 수렴**(r1 ~0.30 vs 베이스라인 0.27~0.42, r2 0.00~0.35 vs ~0.10, r3 0.05~0.10 vs 0.01~0.09) — 정책은 "스폰이 clean이면 쏜다"까지이고, **지터로 비-clean이 된 스폰을 능동적으로 clean으로 재성형하지 못함**. 전진/백오프 오실레이션(r1↔r2 반복, cap 368k freeze)은 베이스라인 경계에서 20판 평가 노이즈가 문턱을 넘나든 것.
- **seed1 후기 무발사 재발**: trFire 0.60(266k) → 0.05(348k) → 0.00(430k+), trCln 0.35 유지(스폰-clean 관찰만, dwell) — **무발사 어트랙터가 후기(lr 저점)에 재점화**. captured-exit이 이를 정확히 차단(clean_cross 기준이었다면 r1 전진을 계속 허용했을 것 — T-2a 반-게이밍 설계가 실전 검증됨).
- **heldout 0/200 ×3** = T-4 프레이밍대로(파일럿 = 말단 행동 습득 실험; R6/nominal 전이는 애초 범위 밖).
- **다음 갈림길**: (a) 사전등록 문언대로 10-seed 본선(동일 config — 단 구조적으로 r1~r3 정체 재현 가능성 높음, 정보/스텝 효율 낮음) vs (b) **A-3c: 재성형 벽 정면 공략** — 핵심 후보 = **L-margin(graded λ1) × robust-스폰 결합**: A-2에서 margin gradient가 무효였던 이유는 근접-clean 경험 자체가 분포에 없어서였고, A-3b 스폰이 바로 그 경험을 제조함 — 이제야 margin 신호가 데이터 지지를 가짐(σ-스테이지 한정 스캐폴드, 판정 불변). 보조 후보: 스테이지 체류 연장(sustain/stall 완화), v2 궤적 되감기, σ 세분화(0.02→0.03→0.05).

### 2026-07-15 (jj) — ✅ T-1 정식 oracle PASS (n=100/witness, pooled 0.960) → 파일럿 런치

- 서버 실측(`a3b_fire_oracle`, seed0 31M): x20v24 commit@1 1.00·clean@1 1.0·cap 1.00 / x16v20 1.00·1.0·1.00 / x12v16 0.88·1.0·0.88(waste 0.12 — 자기 robust_frac 0.90과 정합). **pooled gate 0.960 ≥ 0.8 → PASS**: R0는 해석 가능한 표현 테스트임이 확정(주입 상태에서 스텝-1 강제 발사 = clean 커밋·포획 성립). fire return(+5.4~+6.8) ≫ dwell(+1.2~+2.0) hold-조건 재확인.
- 파일럿 런치(`d663a51`, scratch 3-seed, captured_rate exit, cap 360k/total 520k, OUT=results/m3a_a3b_pilot). 아티팩트(oracle JSON 포함)는 파일럿 마감 시 일괄 커밋 예정.
- 판독 예고: ntfy는 R-전진을 알리지 않음(START/DONE + s3 전환만) — 진행은 eval_curve `cur.r_idx`/captured_rate로. 중간 게이트 = **R0 통과 ≥2 seed ∧ R2 도달 ≥1** or heldout clean 비영; R0 실패 시 13 §10 첫 행(진단 표) 경로.

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
