# M4 학습 런북 — 서버 실행용

**개정 2026-08-03** · 실행 = Hyunjun (샌드박스 SSH 불가) · 준비 = Claude
**전제**: `docs/40` (운용점 선언) · `docs/45` (두 경계) · `docs/46` (채널 분리) · `docs/47` (게이트·스윕·판정식)

> **2026-07-27 판에서 무엇이 바뀌었나.** 그 판의 [A] git 경계 · [B] 락 청소 ·
> [D] 학습 스크립트 배선 · [E] 스케일 스모크는 **전부 끝났다**. 남은 것은 서버에서
> 도는 부분뿐이고, 그 사이에 판정식이 세 번 정정됐다(정정 5·6·7). 이 문서는
> **지금 그대로 복사해서 붙이면 도는** 절차만 남긴다.

---

## 0. 순서

```
[0] 사전 확인        깨끗한 체크아웃이 import 되는가 (로컬)         ~1 분
[1] 서버 준비        pull -> venv -> 스모크                        ~10 분
[2] 기저선 2개       hold n=500 · intercept n=300                  ~35 분  (리포에 이미 있으면 건너뜀)
[3] 파일럿 3런       신호가 붙는지 본다. **여기서 멈출 수 있다**    1런 실측 x 3
[4] 본 스윕 50런     w_kill 5 x seed 5 x threat_obs 2              [3]에서 잰 시간 x 50 / jobs
[5] 집계·판정        사전 등록된 판정식 그대로                      ~1 분
```

**[3] 을 건너뛰지 않는다.** 신호가 안 붙는 상태로 50런을 태우면 나오는 것은 "협력이
안 된다"가 아니라 **"학습이 안 됐다"** 이고, 그건 논문에 못 쓴다 (docs/47 §4.3).

---

## [0] 서버에 올리기 전 — **깨끗한 체크아웃이 import 되는가** (로컬)

명시적 `git add` 규율의 부작용으로 **커밋 안 된 파일이 쌓인다.** 2026-08-03 에
`shepherd/spawn_rand.py` · `obs_threat.py` 가 미추적인 채로 남아 있었는데, 커밋된
`m4_env` · `curve_sweep` · `sweep_m4` · `train_m4` 가 전부 그걸 import 한다 — 즉
푸시된 저장소는 **clone 하면 import 조차 안 되는 상태**였다. 서버에 올라간 뒤에
알면 왕복 한 번을 버린다.

```powershell
Set-Location "C:\Users\Teemo\Desktop\ANDES\URP\newURP"
git status --short                    # ?? 가 남아 있으면 먼저 처리

$tmp = Join-Path $env:TEMP "newurp_clean"
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
git clone --quiet . $tmp              # **커밋된 것만** 복제된다
Push-Location $tmp
python scripts/check_checkout.py
Pop-Location
```

`clean checkout imports OK` 가 뜨기 전에는 **push 하지 않는다.**

이 검사가 하는 일과 안 하는 일:

* **torch 를 요구하지 않는다.** 묻는 것은 "파일이 커밋됐는가"이지 "환경이 준비됐는가"가
  아니다 (환경은 [1] 이 본다). 섞으면 venv 밖에서 못 쓰는 검사가 된다.
* import 가 **성공해도** 나온 `__file__` 이 이 트리 안인지 확인한다. `pip install -e`
  의 editable 파인더가 `shepherd.__path__` 를 원본 저장소까지 넓혀 놓아서, clone 한
  트리에 파일이 **없어도** 원본 사본이 잡혀 조용히 통과한다 (실측 확인). 이 확인이
  없으면 검사가 아무것도 못 잡는다.

---

## [1] 서버 준비

```bash
ssh <서버>
cd <리포>
git fetch && git checkout <브랜치> && git pull
git rev-parse HEAD                      # 로컬 커밋과 일치 확인 -- 다르면 중단

source .venv-l2/bin/activate
export TMPDIR=/data/hjhong/tmp
pip install -e .                        # 신규 의존성 없음

# ★ 코어가 적으면 BLAS 스레드 경합으로 5배 느려진다 (실측). 반드시 켠다.
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

python -m pytest -q                     # 스모크
python -m shepherd.m4_config            # 운용점 표
```

**`-m` 실행 필수.** 파일 경로로 직접 부르면 import 가 깨진다.

### 스모크 결과 읽는 법

| 마지막 줄 | 뜻 |
|---|---|
| `452 passed, 2 skipped` | **정상.** 이 상태에서만 다음으로 넘어간다 |
| `412 passed, 42 skipped` | **venv 를 안 켰다.** torch 가 없어 torch 표시 항목이 건너뛰어졌다. `source .venv-l2/bin/activate` 후 다시 |
| `... 28 failed` + `_Base` / `Sequential` / `as_tensor` 류 `TypeError` | 같은 원인(torch 없음)인데 `tests/conftest.py` 가 없는 구버전이다. pull 먼저 |

세 번째 줄이 왜 저렇게 보이는지: `tests/test_a3e.py` 가 torch-free 경로를 재려고
**가짜 torch** 를 `sys.modules` 에 심는다. torch 가 진짜면 무해하지만, 없으면 그 뒤의
모든 torch 테스트가 가짜를 받아 알아볼 수 없는 형태로 깨진다. `tests/conftest.py` 가
그걸 감지해 깨끗한 skip 으로 바꾼다. **torch 버전 문제가 아니다.**

`python -m shepherd.m4_config` 출력에서 이 네 줄을 눈으로 확인한다:

```
physics.tau_deploy   0.3         physics.net_radius   1.77
physics.kill_radius  0.75        attitude.omega_max   2.0
```

---

## [2] 기저선 — 학습이 이겨야 할 상대

```bash
python -m shepherd.scripts.sweep_m4 --baseline  500 --baseline-out  $PWD/results/hold_baseline.json
python -m shepherd.scripts.sweep_m4 --reference 300 --reference-out $PWD/results/intercept_baseline.json
```

**절대경로로 쓴다.** 상대경로로 떼어 놓고 돌리다가 다 계산해 놓고 저장 줄에서
`FileNotFoundError` 로 n=300 을 통째로 날린 적이 있다.

| 기저선 | 무엇 | 왜 두 개인가 |
|---|---|---|
| `hold` (n=500) | 무개입 | **1차 판정식의 상대.** SHAPING_NEEDED 에서 0/297 |
| `intercept` (n=300) | 최강 손튜닝 (요격 + 커밋) | 2차 참조. "hold 는 이겼는데 손튜닝은 못 이겼다"를 구분하려고 |

리포에 이미 두 파일이 있으면 **다시 안 재도 된다.** 단 `bands` 키가 없는 구판이면
다시 재야 한다 (`jq` 는 없을 수 있으므로 파이썬으로):

```bash
python - <<'PY'
import json
for f in ("results/hold_baseline.json", "results/intercept_baseline.json"):
    d = json.load(open(f))
    print(f, "| n=", d["n"], "| mode=", d["limiter_mode"],
          "| commit=", d.get("baseline_commit"), "| bands=", "bands" in d)
PY
```

둘 다 `bands= True` 면 이 절은 건너뛴다.

### ★ 대신 결정론 대조를 한다 (2분)

동결 수치는 **다른 기계에서** 잰 것이고, 사전 등록된 문턱값이 전부 그 파일에서 나온다.
이 기계가 같은 숫자를 내는지는 한 번 확인해야 한다. `results/curve_hold.json` 의 앞
50판이 `hold_baseline` 과 **같은 draw** 이므로 대조가 성립한다.

```bash
python -m shepherd.scripts.curve_sweep --mode hold --episodes 50 --out /tmp/det.json >/dev/null
python - <<'PY'
import json
new = json.load(open("/tmp/det.json"))["records"]
ref = json.load(open("results/curve_hold.json"))["records"][:len(new)]
bad  = [(a["episode"], a["label"], b["label"])
        for a, b in zip(new, ref) if a["label"] != b["label"]]
same = all(abs(a["a_att"] - b["a_att"]) < 1e-12 for a, b in zip(new, ref))
print(f"라벨 불일치 {len(bad)}/{len(new)}   위협 draw 일치 {same}")
print("OK -- 동결 수치가 이 기계에서 재현된다" if not bad and same else bad[:5])
PY
```

* **OK** → 동결본 그대로 쓰고 [3] 으로.
* **불일치** → 그것 자체가 결과다. 이 기계에서 기저선 2개를 다시 재고(위 명령),
  문서에 **"기저선은 서버 기준"** 이라고 못 박는다. 넘어가면 판정 전체가 흔들린다.

> ★ `intercept` 참조는 반드시 `--reference` 로 잰다. 커밋 비트는 limiter 행동
> 벡터(idx 3)에 실려 있어서 `limiter_mode="hold" + baseline_commit=True` 는 **hold 와
> 완전히 같은 결과**를 낸다 (정정 8, docs/45 §9.6). 300판을 헛돌린 적이 있다.

---

## [3] 파일럿 3런 — **여기가 진짜 게이트다**

```bash
mkdir -p $PWD/results/m4_pilot
for s in 0 1 2; do
  setsid nohup python -m shepherd.scripts.train_m4 \
    --seed $s --w-kill 0.5 --output $PWD/results/m4_pilot/s$s \
    > $PWD/results/m4_pilot/s$s.log 2>&1 < /dev/null &
done
```

`setsid nohup ... < /dev/null &` 로 띄운다. 그냥 `&` 로 띄우면 로그아웃할 때 죽는다.
**파일 존재만 보고 "진행 중"이라고 판단하지 않는다** — 로그 마지막 줄을 본다.

### 무엇을 보는가

```
[seed 0] upd 120/488 ... | free_cap 0.62 shape_cap 0.00 shape_hk 0.04
[seed 0] 밴드 EASY: 네트 0.83 / 무력화 0.83 (n=61)  BAND_AIM: 네트 0.01 / 무력화 0.12 (n=58) ...
```

`signal_audit` 실측: 무작위 탐색은 SHAPING_NEEDED 에서 성공을 **0/23** 회 찾았고,
목적 있는 요격은 **15/182** 를 찾았다. 즉 이건 구조적 0 이 아니라 **희소 탐색 문제**다.
`shape_hk` 가 0 에서 올라오는지가 그 질문의 답이다.

### 진행/중단 — 지금 선언한다 (결과 보기 전)

| 파일럿 결과 | 다음 |
|---|---|
| 3런 중 하나라도 `shape_hk > 0` 또는 `BAND_AIM 무력화 > 0` | **[4] 진행** |
| 3런 전부 둘 다 정확히 0 | **[4] 중단.** 탐색을 먼저 고친다 (하드킬 커리큘럼 / 요격 시연 warm-start). 태워도 나오는 건 "학습 실패"뿐이다 |

> 이건 **계산 자원 게이트이지 판정 게이트가 아니다.** 1차 판정식(docs/47 §4.3)은
> 손대지 않는다. 여기서 정하는 건 "50런을 태울 가치가 있는가" 하나뿐이다.

### 시간 재기

```bash
tail -n 2 results/m4_pilot/s0.log                 # 진행 확인
python - <<'PY'
import json, pathlib
for f in sorted(pathlib.Path("results/m4_pilot").rglob("summary.json")):
    d = json.loads(f.read_text()); b = d["final_eval_bands"]
    print(f.parent.name,
          "overall", round(d["final_eval"]["neutralized_rate"], 3),
          "| BAND_AIM 무력화", round(b["BAND_AIM"]["neutralized"]["p"], 3),
          f'(n={b["BAND_AIM"]["n"]})')
PY
```

1런 벽시계를 `T` 라 하면 **[4] 의 벽시계 = T × 50 / jobs**. 여기서 정한다.

---

## [4] 본 스윕 — 50런

```bash
python -m shepherd.scripts.sweep_m4 --dry-run                        # 명령 50개 눈으로 확인
python -m shepherd.scripts.sweep_m4 --run --jobs 4 --root $PWD/results/m4_sweep
```

축 = `w_kill {0, 0.25, 0.5, 0.75, 1.0}` × `seed {0..4}` × `threat_obs {on, off}` = **50 런**.

`--jobs` 는 코어 수 / 2 를 넘기지 않는다 (각 런이 이미 벡터 연산을 돈다).

**`SWEEP_AXES`(omega_max · kill_radius · tau_kill)는 여기서 같이 돌리지 않는다.**
1차 스윕이 끝난 뒤 **승자 설정 하나에 대해서만** 돌린다 — 강건성 확인이지 탐색이 아니다.
같이 돌리면 50 → 900 런이 되고, 그건 "좋은 값 찾기"가 되어 선언 규율을 깬다.

### 런이 죽었을 때

```bash
python -m shepherd.scripts.train_m4 --seed 3 --w-kill 0.75 \
  --output $PWD/results/m4_sweep/w0.75_s3_obs1 --resume
```

`--resume` 은 체크포인트에서 이어 간다. 재개된 런은 `summary.json` 의 `resumed_from`
으로 표시되므로 집계에서 구분된다. **죽은 런을 조용히 빼지 않는다** — 빼면 생존
편향이다. 살리거나, 실패로 세거나 둘 중 하나.

---

## [5] 집계와 판정

```bash
python -m shepherd.scripts.sweep_m4 --aggregate $PWD/results/m4_sweep \
  | tee results/m4_sweep/aggregate.json
```

### 1차 판정 — 사전 등록 (docs/47 §4.3). **고치지 않는다**

`SHAPING_NEEDED` 영역의 무력화율이 `hold` 기저의 Wilson 상한을 넘는 런의 수.

| 출력 | 뜻 |
|---|---|
| `순이득 없음` | hold 를 넘은 런이 0 — 신청서 §4.7 폴백 (v) 로 보고 |
| `부분 순이득` | hold 는 넘었으나 intercept 참조는 하나도 못 넘음 |
| `순이득 있음` | 둘 다 넘음 |

### 2차 — 같이 보고한다

* **비손실 비율의 `w_kill` 단조성.** hold 와 비교하지 않는다 — 스크립트 기준선은
  구조적으로 하드킬을 못 해 자명하게 1.00 이다.
* **`threat_obs` ablation.** regime 을 못 보는 정책이 얼마나 손해 보는가.
* **`BAND_AIM`** (`a*(ψ)=25.8 ≤ a < a*=39.3`). 손튜닝 네트 포획 **1.0 %** (3/518) vs
  물리 요격 **15.5 %** (35/226). 개선 여지가 사전 실측으로 확인된 유일한 구간이다.
  **보고 전용이고 1차 판정식에 들어가지 않는다** (docs/47 §4.4). 경계값은
  `curve_sweep.PSI_MED_DEG` / `band_of()` 에 못 박혀 있고 P44h·P44i 가 지킨다.

---

## 절대 하지 말 것

| | 왜 |
|---|---|
| 결과를 본 뒤 판정식·표본 수·축을 바꾸기 | 소급 변경. 사전 등록 전체가 무효가 된다 |
| 봉인 파일 수정 (`env.py`, `env_m3.py`, `adversary.py`, `params.py`, `configs/m2_l2_train.yaml`) | 동결 계약 |
| 공격자 파라미터 튜닝 | Anti-exploitation rule 2. 공격자는 선언·동결이고 최적화 대상이 아니다 |
| `2026URP` 루트에서 `git add -A` | 무관한 169건이 딸려 들어간다 |
| 샌드박스 mount 에서 `git` 실행 | Windows 네이티브 git 에서만 |
| 안 좋은 런 빼고 집계 | 생존 편향 |
| CLI 기본값으로 선언값 덮어쓰기 | 정정 6 이 그거였다. `--tau-kill` 등은 주지 말고 선언값을 쓴다 |

---

## 알려진 위험

| | |
|---|---|
| **희소 탐색** | SHAPING_NEEDED 에서 무작위 탐색이 성공을 못 찾는다(0/23). [3] 이 이걸 본다. 구조적 0 은 아니다 — 목적 있는 요격은 15/182 를 찾았다 |
| **커밋 차원 학습 실패** | `coma_D` 가 커밋 차원을 못 덮을 수 있다 (docs/29 §15.2). 폴백(규칙 기반 커밋 가드 + 배치만 학습)은 사전 등록됨 |
| **`omega_max` 민감도** | 네트가 기체 고정이라는 축소자세 가정 아래 값이다. 짐벌이면 두 번째 경계가 오른쪽으로 움직인다. `SWEEP_AXES` 에 올려 두었고 1차 스윕 뒤에 확인한다 (docs/45 §5) |
| **A3 효과 미측정** | 현 운용점에서 베이팅이 `v_shot_soft` 를 못 움직인다. **학습된 finisher** 가 생겨야 나타나는 효과라 지금은 그대로 둔다 |

---

## 부록 — 로컬에서 이미 잰 것 (서버에서 다시 안 재도 됨)

| 산출물 | 파일 · 스크립트 | 무엇 |
|---|---|---|
| hold 기저선 | `results/hold_baseline.json` | n=500. SHAPING 0/297 |
| intercept 참조 | `results/intercept_baseline.json` | n=300. SHAPING 하드킬 15/182 |
| 포획 확률 곡선 | `results/curve_hold.json` · `curve_intercept.json` | n=1500 / 1200. 두 경계 검증 (docs/45 §9) |
| 겨냥각 ψ | `shepherd.scripts.slew_audit` | 중앙값 4.26° → `a*(ψ) = 25.8` |
| 채널 분리 | `shepherd.scripts.channel_split` | ring 이 v⊥ 를 0.44 → 7.27 m/s 로 키운다 |
| 학습 신호 | `shepherd.scripts.signal_audit` | 무작위 탐색 수익 std 가 종말항의 0.32 % |
| 곡선 그림 | `docs/ppt/fig8.py` | 경계 2개 · Wilson 띠. `NEWURP_ROOT` 로 경로 지정 가능 |


---

## [3.5] 역할 분리 2×2 — 50런 스윕보다 **먼저** (2026-08-04, docs/48)

파일럿이 게이트 STOP 이었고, 그 결과는 원인을 역할에 귀속시키지 못한다
(`hold` 가 무개입이 아니라 해석적 발사 규칙이라서다 — docs/47 §7.2, docs/48 §1).
귀속 없이 50런을 태우면 같은 해석 불능에 다시 걸린다. 그래서 순서를 바꾼다.

```bash
# 기저선이 이미 있으면 0) 은 건너뛴다 (부록 표 참조)
python -m shepherd.scripts.roles_split --dry-run            # 명령 9개
python -m shepherd.scripts.roles_split --run --jobs 9       # 3 팔 x 3 시드, 500k
python -m shepherd.scripts.roles_split --aggregate results/m4_roles
```

| 팔 | `--limiter-policy` | `--finisher-policy` | 읽는 것 |
|---|---|---|---|
| LL | `learned` | `learned` | 결합 (= 파일럿 구성, 결함 수정 후 재측정) |
| LS | `learned` | `scripted` | 편대 학습의 단독 기여 |
| SL | `hold` | `learned` | 발사 학습의 단독 기여 |
| SS | — | — | **안 돌린다.** `results/hold_baseline.json` (n=500) |

비용: 파일럿과 동일(500k×9). 같은 기계 순차 ≈ 15시간, 9 병렬 ≈ 1.7시간.
`--resume` 살아 있다. 판정식은 `--aggregate` 출력에 **함께 실려** 나오므로
사후 변경이 눈에 띈다. 상세는 `docs/48`.

**멈춤 조건**: 집계의 `tests` 가 전부 `passed: false` 면 그것이 결과다 —
역할 분리로도 회수되지 않는다는 뜻이고, 그때는 스윕이 아니라 학습 문제
(발사 헤드 확률 붕괴 · PBRS) 로 간다.
