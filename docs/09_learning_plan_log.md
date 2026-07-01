# 09 — L2 Learning Plan & Log (MARL: MAPPO + COMA)

> **한 파일 = 플랜 + 로그.** §0–§7 = 살아있는 계획(수정 OK), §8 = append-only 작업 로그(위가 최신).
> **범위:** L2 (MARL end-to-end). 전제 = L1 + S14/N1 prep 완료 (`feat/l2-prep-wiring`).
> **소유:** 코어(게임·reward·shaping 유도·결정) = Hyunjun / AI = 구현·scaffold·디버그 보조.
> **모드:** BUILD-first (`04_action_plan.md`) — 계획·검증보다 돌아가는 것. 검증은 time-box.

---

## 0. 한눈에

- **목표:** scripted 정책 → **학습된 shaping 정책**. MAPPO **직접 구현**(black-box 금지) + **COMA** limiter credit. CTDE.
- **동결(건드리지 않음):** S1–S8 계약(`03_formalization.md`), env 계약(`shepherd/env.py`), `configs/m2_l2_train.yaml`, frozen blob 2개(`03_formalization.md`, `shepherd/game/exchange.py`).
- **L2 산출:** seed≥3 수렴 학습곡선 > baseline + wandb 곡선 + checkpoint + demo GIF.
- **현 위치:** **Phase 1 완료(2026-07-01).** from-scratch PPO 코어(`shepherd/train/ppo.py` + torch-free `gae.py`) + 토이 수렴 검증 커밋(`52a7d58`). **다음 착수점 = Phase 2A**(shepherd ParallelEnv 어댑터 smoke) — Phase 2는 2A→2B(IPPO)→2C(MAPPO)→2D(COMA) 사다리(§5).

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
- **action**: limiter `Box([accel x,y,z, pressure])` / finisher `Box([axis x,y,z, slew, fire])` (fire>0.5=발사, 비가역) / adversary `Box(accel 3)`.
- **reward**: limiter·finisher = `+J`, adversary = `−J`. info: limiter별 `coma_D`, finisher `delta_v_shot_headline`.
- **중앙 critic 입력**: `env.state()` (전 kinematic state concat) 제공됨.
- **종료**: captured / penetrated / spent_fail. **truncation**: `episode_len=80`.

**학습 config(`configs/m2_l2_train.yaml`)**

- n_limiters=4, K=1 / dt=0.05, τ_deploy=0.4, a_att_max=30, att_speed=20, kill_radius=2.0, **net_radius=2.0(N1-grounded)**, a_lim_max=30.
- **viability: n_segments=4 (S14 보수 신호로 학습)**, judge=se3_cone, n_samples=2000, cone half_angle=0.067 / range_max=29.847.
- θ_fire=0.9 / λ=(1, 1, 0.5) / COMA·headline baseline = hold_position.

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

> 각 Phase = **동작하는 산출물** + DoD + 커밋. 채택안 A/A/A. torch-free 스위트는 매 커밋 green(baseline 59 → Phase 1 후 72), frozen blob diff 0.

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

> **Phase 1 PPO 코어를 최대 재활용하며 리스크를 한 계단씩 격리.** 부산물로 **IPPO(2B) / MAPPO(2C) / MAPPO+COMA(2D)** ablation 사다리가 나옴 → §5 Phase 6 baseline 비교표로 그대로 재사용(중복 작업 0). 각 rung = 동작 산출물 + DoD + 커밋. torch-free 스위트 매 커밋 green(현 72), frozen blob diff 0.
>
> **이종(heterogeneous) 못박기:** env는 4 limiter(`Box(4)` accel+pressure) + 1 finisher(`Box(5)` axis+slew+**fire**) + scripted adversary. "N-agent 완전 공유 정책"은 **틀림** — limiter만 파라미터 공유, finisher는 별도 정책, adversary는 학습 X.

#### Phase 2A — shepherd env 어댑터 smoke (알고리즘 X, 배선만)

- **할 일:** PettingZoo ParallelEnv ↔ trainer 어댑터. dict obs flatten, agent별 action 라우팅(limiter/finisher/adversary), reward·info(`coma_D`/`delta_v_shot_headline`) 추출, `env.state()` 배선. adversary는 scripted 주입.
- **DoD:** **random 정책**이 full episode(`episode_len=80`) NaN 없이 완주 + obs/action/reward/info 배선 검증(shape·키). torch-free 스위트 green.
- **커밋:** `feat(train): shepherd ParallelEnv adapter smoke (random policy)`.

#### Phase 2B — IPPO (independent PPO, 중앙 critic 없음)

- **할 일:** Phase 1 PPO 코어를 agent별로 굴림 — **limiter = 파라미터 공유 1개 정책**(homogeneous 역할) + **finisher = 별도 정책**, 각자 **decentralized critic**. = 진짜 IPPO(MARL 표준 baseline·selection-only ablation).
- **혼합 action head 확정(여기서 close):** finisher `fire`(binary·비가역) — **Bernoulli head 권장**(fire만 분리 Bernoulli, 나머지 연속 Gaussian) vs Gaussian+threshold → 2B에서 결정·기록. §7.1 오픈항목 해소.
- **로깅:** wandb 여기서부터 켬(return / loss / entropy / KL + `Δv_shot`/`wasted_fire`/`limiter_loss`). checkpoint = Phase 1 `PPOTrainer.save/load` 재사용.
- **DoD:** IPPO return이 hold_position·scripted baseline **유의 초과**(≈ selection-only baseline, 사실상 L2 게이트 근접). NaN 0.
- **커밋:** `feat(train): IPPO (shared-limiter + separate finisher, decentralized critics)`.

#### Phase 2C — MAPPO (중앙 critic, CTDE)

- **할 일:** 2B 위에 **중앙 critic 1개**(`env.state()` 입력)만 추가 → CTDE. actor는 2B 그대로(decentralized 실행).
- **throughput(주의):** `v_shot`(n_segments=4, n_samples=2000, per-step union)이 최대 병목(§7) → **여기서 물림**. supersuit 벡터화를 2C 직전/병행으로 당기거나, 최소 2C DoD에 throughput 측정 + n_samples 축소/union 캐싱/CRN 재사용 튜닝(정확도-속도 trade) 포함.
- **DoD:** MAPPO return **≥ 2B(IPPO)** + 학습 안정(NaN 0, KL 정상). torch-free green.
- **커밋:** `feat(train): MAPPO (shared central critic, CTDE) on shepherd env`.

#### Phase 2D — COMA limiter credit ablation (D1-A 1단계)

- **할 일:** env의 `info[limiter_i]["coma_D"]`(**해석적** v_shot 차분)를 **limiter advantage**로 배선. baseline = hold_position(고정, S8). = 기존 Phase 3, "ablation"으로 프레이밍.
- **DoD:** `D_i` 평균 > 0(역할 검증·kill-switch 연동) ∧ **MAPPO+COMA ≥ MAPPO** ∧ `Δv_shot>0` 유지. terminal-only 보상 금지.
- **커밋:** `feat(train): COMA difference-reward credit for limiters (analytic D_i)`.
- **D1-A 2단계(Phase 6 이후 stretch):** 학습된 counterfactual critic으로 D_i 대체 → "COMA 직접 구현" 이력서 신호.

**ablation 사다리 = baseline 재사용:** 2B(IPPO) / 2C(MAPPO) / 2D(+COMA) 곡선이 그대로 Phase 6 비교표(no-shaping / selection-only / MAPPO / +COMA)로 들어감.

### Phase 4 — 재현성 마감 (벡터화·로깅은 2B/2C로 선반영)

> **2026-07-01 재구성:** wandb 로깅·checkpoint = **2B로**, supersuit 벡터화·`v_shot` throughput 튜닝 = **2C로** 당김. Phase 4는 잔여 마감만.

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

- **v_shot throughput** — 학습 루프 최대 병목 후보(§5 Phase 4 대응).
- **혼합 action head** — finisher fire(binary) 분포 처리(**Phase 2B 확정** — Bernoulli head 권장).
- **비수렴·보상 스케일·NaN** — Phase 1 토이에서 선제 차단 + 디버깅 경험 1건은 학습목표(`06`).
- **torch 샌드박스 불가** — 학습은 로컬/랩 전용, 샌드박스는 torch-free 테스트만.
- **mount truncation** — 마운트 쓰기 간헐 truncation(이번 세션 실재) → heredoc 재기록 + 재읽기 검증 규율.
- **결정 D1/D2/D3 = A/A/A 확정(2026-06-30)** — §1. 플랜이 이 기준으로 고정.

### 7.1 Phase 1 → Phase 2 이월 오픈 항목 (2026-07-01 기록)

> Phase 1 코어는 토이에서 검증됨. 아래는 shepherd env로 올릴 때(Phase 2) 재검토·해소해야 하는 것들.

- **obs normalization 미탑재** — Pendulum엔 불필요해 생략. shepherd obs는 **63-dim + 스케일 제각각**(위치/속도/attitude/FSM/vres) → **Phase 2 진입 시 running normalizer 추가**(코드에 주석 표시). 없으면 value/policy 학습 불안정 위험.
- **`init_log_std=0` (std=1) 과대 가능** — shepherd action space(accel±30 정규화 후 + pressure[0,1] + fire)가 Pendulum(±2)보다 좁아 초기 탐험이 과할 수 있음 → config로 튜닝. `clip_fraction_action` 로그로 경계-밖 학습 조기 감지(이미 배선됨).
- **action clip vs tanh squashing** — Phase 1은 clip(log-prob는 raw Gaussian 기준, 실행된 clip 액션 밀도 미보정). shepherd에서 `clip_fraction_action` 지속 상승 시 **tanh squashing(+log-det-Jacobian) 재검토**.
- **γ=0.9 는 Pendulum 튜닝값** — shepherd(`episode_len=80`, dt=0.05, 4s)용 γ/λ **재설정 필요**(config).
- **value clipping 생략** — Phase 1 plain MSE. shepherd에서 value loss 폭주 시 PPO2 value-clip 재도입 여지(구현은 config 플래그로 쉽게 추가 가능).
- **LunarLanderContinuous-v3 2차 검증 미실시** — box2d 미설치로 skip. 진짜 `terminated` 부트스트랩(=0)은 현재 **유닛테스트(`test_terminated_bootstrap_is_zero`)로만** 커버. shepherd 통합 전 end-to-end로 한 번 더 보려면 box2d 설치 후 secondary run.
- **재현성 CPU 한정** — same seed → same metrics는 **CPU deterministic**에서만 보장. CUDA는 비결정적(caveat). 랩 GPU run은 seed+config로 "근사 재현"만.
- **torch 테스트 CI 미편입** — 현재 torch 테스트는 로컬 venv에서만 green. CI(`ci.yml`)는 torch-free job만 → 추후 CPU-torch job 또는 `-m "not torch"` 유지 결정(§4.2).

---

## 8. 작업 로그 (append-only · 최신이 위)

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
