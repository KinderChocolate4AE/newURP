# M4 재학습 런북 — 서버 실행용

**2026-07-27 · 실행 = Hyunjun (샌드박스 SSH 불가) · 준비 = Claude**
**전제**: `docs/29` v4 (M4 설계·보상) · `docs/30` (로드맵) · `docs/31` (파라미터 작성지)

> **왜 재학습인가**: 기존 체크포인트는 **커밋 비트(limiter Box(4) idx 3)가 무효이던 시점**에 학습된 것이라 모드 중재를 할 수 없다. `docs/30 §3` — **§6(학습 결과)은 재학습 없이 성립하지 않는다.** 이것이 남은 일정의 유일한 병목이고, 그 앞 작업은 전부 로컬에서 끝난다.

---

## 0. 순서 요약

```
[A] git 경계        C-1 종료 산출물 / M4 신규 를 두 덩어리로 분리 커밋   (Windows 네이티브)
[B] .git 락 청소     stale lock ~100개 삭제                              (Windows 네이티브)
[C] 서버 준비        pull → REQUIRED_COMMIT 확인 → venv → 스모크         (서버)
[D] 학습 스크립트     train_m4.py 배선  ← **남은 코드 항목**              (로컬, 다음 블록)
[E] 스케일 스모크     조밀항 vs 종말항 누적 기여 실측                     (로컬)
[F] sweep 실행       w_kill × tau 도메인 랜덤화                          (서버)
[G] 임무 지표 평가    mission_rollout 로 arm 비교                        (로컬/서버)
```

**[A]~[C] 는 지금 실행 가능하고, [D] 가 남은 코드 작업이다.**

---

## [A] git 경계 — 두 덩어리 커밋

`docs/30`: 신규 7파일 + C-1 미커밋 169건이 섞여 있다. **한 커밋에 넣으면 bisect 가 망가진다.**

### A-1. 신규 M4 파일 (이번 캠페인)

```bash
cd /c/Users/Teemo/Desktop/ANDES/URP/newURP     # Git Bash 기준. PowerShell 이면 cd 만 교체

git add shepherd/agents/attacker_ladder.py \
        shepherd/env_adv.py \
        shepherd/env_sys.py \
        shepherd/scripts/mission_rollout.py \
        shepherd/scripts/rho_v_band.py \
        shepherd/scripts/oracle_capture.py \
        tests/test_attacker_ladder.py \
        tests/test_mode_system.py \
        docs/26_marl_paper_plan_2026-07-27.md \
        docs/27_attacker_ladder_design.md \
        docs/28_framing_revision_nondestructive.md \
        docs/29_m4_mode_system_design.md \
        docs/30_paper_roadmap.md \
        docs/31_parameter_decision_sheet.md \
        docs/32_m4_retrain_runbook.md

git status --short          # <-- 위 목록만 스테이징됐는지 눈으로 확인
git commit -m "feat(m4): 모드 전환 방어 시스템 — 공격자 사다리 A1-A3 · 하드킬 방아쇠 · no-kinetic zone · M4 보상

- attacker_ladder: A1 위임 + A2(jink/편대 라우팅) + A3(발사 유도, fair/privileged) + lambda 1급화
- env_adv: 백엔드 프록시로 공격자 주입 (frozen env.py 무수정, bit-identical 보장)
- env_sys: 하드킬 방아쇠 + no-kinetic zone + M4 보상 (env 래퍼)
- mission_rollout: 임무 5분할 라벨 + 에피소드 접촉 집합 + 2층 지표
- rho_v_band / oracle_capture: 능력비 밴드 · tau 축 도달가능성 상한
- docs 26-32: 프레이밍 개정 · 설계 · 로드맵 · 파라미터 작성지 · 런북
- tests: P1~P18 (29 passed, 1 skipped)
- 동결 파일(env.py / env_m3.py / adversary.py / params.py / falsifier / held-out) 무변경"
```

### A-2. C-1 종료 산출물 (별도 커밋)

```bash
git add shepherd/scripts/c1_*.py docs/2[3-5]_c1_*.md docs/c1_*.md
git status --short
git commit -m "docs(c1): certificate 캠페인 종료 산출물 — falsifier v2 · held-out · V2C"
git add -A -- results/ docs/09_learning_plan_log.md     # 남은 산출물
git commit -m "chore(c1): 캠페인 결과 파일 및 로그"
```

> **`2026URP` 루트에서 `git add -A` 절대 금지** (기존 규율). 위처럼 **경로를 명시**해서만 쓴다.

### A-3. push

```bash
git reset          # Windows 에서 push 전 필수 (마운트 index 잔여 상태 정리)
git push origin feat/l2-mappo-train
git rev-parse HEAD          # <-- REQUIRED_COMMIT 로 기록
```

---

## [B] .git 락 청소 (Windows 네이티브)

마운트에서는 `rm` 이 안 되어 과거 세션 잔재가 **~100개** 쌓여 있다.

```powershell
cd C:\Users\Teemo\Desktop\ANDES\URP\newURP\.git
Remove-Item HEAD.lock.* , index.lock.* -Force
Get-ChildItem *.lock*        # 비어 있어야 정상
```

---

## [C] 서버 준비

```bash
ssh <서버>
cd <리포>
git fetch && git checkout feat/l2-mappo-train && git pull
git rev-parse HEAD            # [A-3] 의 REQUIRED_COMMIT 과 일치 확인 -- 다르면 중단

source .venv-l2/bin/activate
export TMPDIR=/data/hjhong/tmp
pip install -e .              # 신규 의존성 없음 (torch-free 파일들)

# 스모크 (torch 불필요, 2분 내)
python -m pytest tests/test_attacker_ladder.py tests/test_mode_system.py -q
#   기대: 29 passed, 1 skipped
python -m shepherd.scripts.rho_v_band --pk 1.0 | tail -5
```

**`-m` invocation 필수** (기존 규율 — 직접 경로 실행 시 import 깨짐).

---

## [D] 학습 스크립트 배선 — **남은 코드 항목**

`shepherd/scripts/train_m4.py` 를 `train_mappo.py` 기반으로 만든다. 필요한 변경은 **네 군데뿐**이다.

```python
# 1) 환경 생성: 래퍼 두 겹을 씌운다
from shepherd.env_sys import ModeSystemEnv, SystemSpec, RewardSpec
from shepherd.env_adv import attach_attacker
from shepherd.agents.attacker_ladder import AttackerSpec, make_attacker, derive_phase

inner, scn, lay = make_train_env(cfg)                       # 기존 composition root
env = ModeSystemEnv(inner, lay, scn,
                    SystemSpec(tau_kill=..., p_kill=..., r_nk=...),
                    RewardSpec(w_kill=W, enabled=True))     # <-- 보상 ON
attach_attacker(env.inner, make_attacker(ATTACKER_SPEC),
                phase=derive_phase(seed, episode))          # 에피소드마다 위상 갱신

# 2) 행동 공간: 변경 없음. limiter Box(4) idx 3 이 곧 커밋 비트다 (docs/29 §3.1)

# 3) tau 도메인 랜덤화 (docs/29 §15.5): attacker_rand 의 딥카피 패턴을 그대로 확장
cfg_ep = copy.deepcopy(cfg)
cfg_ep["physics"]["tau_deploy"] = float(rng.uniform(*TAU_RANGE))
#    -> 에피소드마다 env 재구성. 기존 build_attacker_env 와 같은 방식

# 4) 관측: tau 를 정책이 볼 수 있어야 한다
#    tau 가 에피소드마다 바뀌는데 관측에 없으면 정책이 regime 을 구분할 수 없다.
#    frozen env.py 의 obs 는 못 바꾸므로 ModeSystemEnv 에서 concat 하거나,
#    tau 를 고정한 채 별도 런으로 나눈다. **둘 중 하나를 선언하고 고정할 것.**
```

> **④ 가 유일한 설계 미결이다.** tau 를 관측에 넣지 않으면 정책이 regime blind 가 되어
> "평균적으로 무난한" 해로 수렴하고, 그러면 §6 의 *"모드 중재를 tau 의 함수로 배운다"*
> 주장이 성립하지 않는다. **관측 확장 쪽을 권장**한다(래퍼에서 obs 뒤에 tau 1차원 추가).

---

## [E] 스케일 스모크 (학습 전 필수, docs/29 §15.3)

조밀항은 스텝당 `O(0.1~1)` × ~24 스텝, 종말항은 1회다. **그대로면 종말 신호가 묻힌다.**

```
한 에피소드에서 sum(dense) 와 terminal_scale*TERMINAL 의 절대값을 각각 출력해
같은 자릿수인지 확인한다. 아니면 terminal_scale 을 조정하되,
**결과를 보기 전에** 조정하고 그 값을 기록한다.
```

---

## [F] sweep 구성

| 축 | 값 | 성격 |
|---|---|---|
| `w_kill` | 0.0 / 0.25 / 0.5 / 0.75 / 1.0 | **선언된 sweep 축** — 뒤집히는 지점이 결과 |
| `tau_deploy` | 에피소드마다 `U[0.15, 0.40]` | 도메인 랜덤화 (docs/31 T1 근거 확정 전) |
| 공격자 | A2 (학습) / A3-fair (평가) | 학습은 A2, 평가는 A3 로 일반화 확인 |
| seed | 5 | paired 비교 (`derive_seed`) |
| 알고리즘 | MAPPO / MAPPO+COMA | C2 의 credit-assignment 축 |

`5 (w_kill) × 5 (seed) × 2 (알고리즘) = 50 런`. 기존 L2 런 예산을 그대로 쓰면 된다.
**GPU 1장 원칙 유지**(워크로드 CPU-bound).

---

## [G] 검증 게이트 (결과 보기 전 고정)

```
G-1  P6 재확인    커밋 비트 0 인 정책은 동결 env 와 bit-identical
G-2  스케일       조밀/종말 기여가 같은 자릿수
G-3  퇴화 검사    w_kill=1 에서도 정책이 "차라리 뚫리게 두는" 해로 가지 않는지
                 (P13 이 보상 순서를 보장하지만 학습 결과도 확인)
G-4  2층 지표     1차 침투 저지율 · 2차 비손실 비율을 **둘 다** 보고
G-5  라벨         SEARCH_CANDIDATE / FIXED_CONDITION 유지. 승격은 A3 + 다중 조건 후
```

**사전 등록(docs/29 §5) 재확인**: 전 `w_kill` 에서 항상-하드킬로 수렴하면 그것이 결과다. 인위적으로 너프하지 않는다.

---

## 알려진 위험

| | |
|---|---|
| **커밋 차원 학습 실패** | `coma_D` 가 커밋 차원을 못 덮는다(docs/29 §15.2). `J1 learned-fire` 재현 위험. 폴백(규칙 기반 커밋 가드 + 학습은 배치만)은 사전 등록됨 |
| **tau 관측 미결** | [D]-④. 정하지 않고 돌리면 §6 주장이 성립하지 않는다 |
| **A3 효과 미측정** | 현 운용점에서 베이팅이 `v_shot_soft` 를 못 움직인다(A2 0.447 vs A3 0.424). 발사 결정이 marginal 한 regime 에서만 의미가 있고, 그건 **학습된 finisher** 가 생겨야 나타난다. 튜닝하지 않고 그대로 둔다 |
