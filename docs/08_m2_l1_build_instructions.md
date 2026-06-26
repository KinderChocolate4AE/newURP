# 08 — M2 / L1 Build Instructions (for Claude Code) · BUILD BRANCH ONLY

> **이 파일 = build 브랜치 `build/m2-l1-reduced-attitude-env` 전용 지시.** M1 정식화(`docs/03_formalization.md`)는 **freeze — 읽기만**.
> 원본 계획 = Claude Code plan-mode 산출(검수 = CONDITIONAL GO). 아래 **§2 필수 수정 5 + COMA 네이밍**을 적용해 구현. (원 plan 본문은 대화 로그 참조.)

## 0. 브랜치 (구현을 M1에 하지 말 것)
**실제 정식화 브랜치 = `m1-formalization`** (커밋 4a69976). ⚠️ 원 리뷰가 쓴 `scaffold/m1-formalization-v2-se3`는 이 repo에 **없음** — 쓰지 말 것.
```bash
cd /c/Users/Teemo/Desktop/ANDES/URP/newURP
rm -f .git/index.lock                 # flaky mount 대비
git switch m1-formalization           # status로 여기 맞는지 먼저 확인 (HEAD truncation 이력)
git switch -c build/m2-l1-reduced-attitude-env
```
이름 이유: full 6DOF가 아니라 **SE(3)-aware reduced-attitude backend**임을 이름에서 숨기지 않음.

## 1. 불변 규칙 (위반 시 중단·보고)
- `docs/03_formalization.md` **수정 금지**(오타·cross-ref 외). 충돌 감지 시 *바꾸지 말고* §F kill-switch 후보로 human 보고.
- `shepherd/game/exchange.py` **불가침**(S9/M3 reserved).
- `shepherd/game/*` **torch import 금지 · concrete backend import 금지**(sim-agnostic). env는 `sim/interface.EnvBackend`(ABC)만 소비.
- **M2 DoD = 증명할 단 하나**: `u_L ≠ u_L^0 ⇒ Δv_shot > 0 ∧ fire threshold crossed with fewer wasted shots`. **경제/exchange-frontier 주장 금지.**

## 2. 구현 전 필수 수정 (코딩 전 반영)

**R1 — finisher 용어 정밀화 (단, 계약 용어 보존).**
- 새 build 파일·주석에서 finisher를 "miss-free"로 부르지 말 것. 정확히: **"finite-magazine, irreversible net-shot; 실패한 commit은 그 샷을 소모한다(`wasted_fire`)"** = 방어자 입장 *miss-costly*.
- ⚠️ `docs/03`의 **"miss-is-free"는 frozen 계약 용어**(주로 공격자 측: 적이 거의 무비용으로 miss를 유도 = c_feint≈0 baseline, S10/M3에서 비용화). **삭제·재정의 금지** — 진짜 바꿀지는 human이 m1 브랜치에서 명시 개정으로 결정. build는 finisher-side 표현만 정밀화.

**R2 — fire gate 단일화.** `θ_fire = 0.8` 단일 소스. 스펙도 `c_fire = θ_fire·B_capture = 0.8`로 맞춰 경제식 gate와 일치. L1 scripted finisher 코드:
```python
fire_allowed = v_shot_soft >= theta_fire   # 0.8
```
`V_cont(k) − V_cont(k−1)` 경제식은 **주석/문서에만**, 구현 gate는 θ_fire 하나.

**R3 — state/obs 차원 9D 통일.** reduced-attitude state = `s_i = (p_i, v_i, e_i)` **9D**(p3+v3+e3). `ω`는 *state 아님 → slew 파라미터*: `e_{t+1} = slew(e_t, e_cmd, ω_max·dt)`. 그러면 plan의 `self 9` obs 설계가 그대로 맞음.
- 계약 주(S2는 {p,v,R,ω} 나열): 9D는 **build-tier reduced 실현** — ω를 rate-limit 파라미터로. 각속도 *동역학*이 나중에 중요해지면 state로 승격(그땐 모든 obs dim +1).

**R4 — `boxed_in`을 net-shot value와 분리 (reward-hacking 방지).** `n_feasible==0 ⇒ v_shot=1.0`은 "limiter가 봉쇄/격추"와 "net이 잡음"을 섞음 → Δv_shot가 net-shot shaping인지 단순 containment인지 혼동. `VShotResult`에 분리 필드:
```python
@dataclass(frozen=True)
class VShotResult:
    v_shot_soft: float; v_shot_worst: float
    n_feasible: int; n_total: int; boxed_in: bool
    p_feasible: float          # n_feasible / n_total
    p_limiter_blocked: float   # 1 - p_feasible
    judge: str; seed: int
```
M2 headline에서 `boxed_in`은 **별도 방어 신호로 보고**, clean net-shot threshold crossing으로 **세지 말 것**.

**R5 — monotonicity 테스트를 corridor fixture 전용으로.** `more/closer limiters ⇒ v_shot↑`은 **일반 명제 아님**(free-evasion에선 v_shot이 떨어질 수 있음 — proto `exchange_frontier`에서 확인됨). 테스트명·범위 축소:
```
test_corridor_escape_ring_monotonicity
```
의미: **검증된 corridor fixture에서 escape ring을 막는 방향으로 limiter 추가 시 v_shot 증가**(채널 ① 생존)만 확인. 전역 단조 금지.

**COMA / baseline 분리 (이름 명확화).** 두 baseline을 코드·info에서 분리:
- **headline**: 전체 shaping rollout vs hold-position rollout → `info["delta_v_shot_headline"]`, `compute_headline_delta(...)`.
- **COMA counterfactual**: 같은 timestep·같은 accel sample에서 limiter i만 baseline로 치환 → `D_i = v_shot(u_i, u_-i) − v_shot(u_i^0, u_-i)` → `info["coma_D"]`, `compute_coma_difference(...)`.
- 둘을 섞지 말 것. (CRN 공통 accel로 D_i 노이즈 상쇄는 유지.)

## 3. 커밋 구조 (gate마다 멈춤)
1. **specs/config** — `configs/m2_default.yaml`, `shepherd/game/roles.py`, `pyproject.toml`/`requirements.txt`(+`pettingzoo`) → `build: M2 scenario specs and config`
2. **viability core** — `shepherd/game/viability.py`, `tests/test_viability.py` → **GATE** `pytest tests/test_viability.py` (R4 분리·R5 fixture + **포팅 회귀**: `turn_limited=False · judge=point_mass · seed=0`이 `prototypes/reachset.py` __main__ 출력 재현) → `build: SE3-aware v_shot viability core`
3. **FSM + backend** — `shepherd/game/finisher_fsm.py`, `shepherd/sim/analytic.py` → `build: irreversible finisher FSM + reduced-attitude analytic backend`
4. **agents + env** — `shepherd/agents/{adversary,baselines}.py`, `shepherd/game/env.py`, `tests/test_env_spaces.py`, `tests/test_coma.py` → **GATE** `pytest tests/test_env_spaces.py tests/test_coma.py` (R2 fire gate·R3 9D·COMA 분리) → `build: PettingZoo M2 shaping env`
5. **GIF rollout** — `shepherd/scripts/rollout_gif.py`, `results/.gitkeep` → **GATE** `python -m shepherd.scripts.rollout_gif --config configs/m2_default.yaml` → `build: scripted M2 rollout GIF` (= **L1 DONE**)
각 커밋 후 `git --no-pager diff HEAD~1` 보여줄 것.

## 4. Claude Code 첫 지시 (붙여넣기용)
```
Work ONLY on branch build/m2-l1-reduced-attitude-env (create it from m1-formalization — NOT from any "scaffold/..." branch, which does not exist).
Read docs/03_formalization.md (frozen contract) and docs/08 (this file) first. Do not modify docs/03 except typo-level cross-refs. Do not touch shepherd/game/exchange.py. shepherd/game/* stays torch-free and imports no concrete backend.
Before coding, apply these corrections:
1. Describe the finisher as "finite-magazine irreversible net-shot; a missed commitment consumes the shot (wasted_fire)". Do NOT call it "miss-free", and do NOT edit the contract term "miss-is-free" in docs/03 — flag any conflict to me instead.
2. Single fire gate: set c_fire = theta_fire * B_capture = 0.8; code uses `fire_allowed = v_shot_soft >= theta_fire`.
3. Use 9D reduced-attitude state (p,v,e); omega is a slew-rate parameter, not a state dim (keep obs dims as in the plan).
4. Add p_feasible / p_limiter_blocked to VShotResult and report boxed_in separately — do NOT count boxed_in as a clean net-shot threshold crossing.
5. Make the monotonicity test corridor-fixture-specific (test_corridor_escape_ring_monotonicity), not global; also add a port-fidelity regression: turn_limited=False, judge=point_mass, seed=0 must reproduce prototypes/reachset.py __main__ output.
Separate baselines: info["delta_v_shot_headline"] (full vs hold-position rollout) and info["coma_D"] (per-timestep counterfactual, shared accel samples).
Implement in 5 commits: specs/config -> viability/tests (GATE) -> FSM/backend -> agents/env/tests (GATE) -> rollout GIF (GATE). Show git diff after each commit.
The ONLY thing M2 must show: u_L != u_L^0 => delta v_shot > 0 AND fire threshold crossed with fewer wasted shots. No economic / exchange-frontier claims.
```

## 5. Human(Hyunjun) 확인 필요
- **R1 계약 용어**: "miss-is-free"의 정확한 의미 pin down — (방어자) "샷 소모 외 비파괴·비치명" vs (공격자) "무비용 bait(c_feint≈0)". build는 보존; 바꿀 거면 m1에서 명시 개정.
- **파라미터 비준**: `c_fire = 0.8`, `θ_fire = 0.8`, `θ_net`는 첫 GIF 보고 `m2_default.yaml`에서 튜닝(코드 변경 X).
- 위 5개 수정 반영 = 최종 GO.
