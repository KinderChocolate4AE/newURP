"""임무 수준 롤아웃 — env 종료 규칙을 직접 호출하는 5분할 계측기 (docs/28 §2.2).

WHY (docs/26 §0.2)
------------------
지금까지 측정된 종속변수는 전부 shaped margin(대리지표) 또는 certificate 기하였다.
C-1 분석 하네스(`rollout_unified`)는 발사 후 0.50 s 에 행정 종료하므로 임무 결과를
구조적으로 관측할 수 없다. 이 파일은 그것을 대체하지 않는다 -- **역할이 다르다**:

    rollout_unified      certificate · escape geometry · continuous-clearance 분석용
    mission_rollout      end-to-end 종료 · 포획 · 침투 · 접촉 · 절단 평가용

`rollout_unified` 는 수정하지 않는다.

채점 (docs/28 §2.2)
-------------------
논문의 스파인은 **비손실 격추**다. 따라서 limiter 가 실제로 살상반경에 접촉하면
그건 성공이 아니라 **부분 실패**다 -- 이 한 줄이 "그냥 박으면 된다"를 봉쇄하고
논문을 조향 문제로 만든다.

    outcome  CAPTURED | PENETRATED | SPENT_FAIL | TRUNCATED     (env, 배타)
    contact  한 번이라도 살상반경에 든 limiter 의 **집합 크기** (에피소드 수준)
    label    NET_CAPTURE           CAPTURED & contact == 0     <- 순수 조향
             CAPTURE_WITH_CONTACT  CAPTURED & contact >  0     <- 물리 차단 혼입
             PENETRATED / SPENT_FAIL / TRUNCATED

docs/28 은 KINETIC_CONTACT 를 배타 라벨로 스케치했지만, 접촉은 논리적으로 결과가
아니라 **수식어**다. 위 형태가 배타적이면서 순도 구분을 보존한다 (개정).

주의: env.py L353 의 `limiter_loss` 는 **스텝별 합**이라 같은 limiter 가 여러 스텝
중복 계수된다. 에피소드 라벨에는 쓸 수 없어 여기서 집합을 따로 센다. 술어는 env 와
동일하고(`||p_att - c|| <= kill_radius`), env 와 같은 **이동 전** 상태에서 평가한다
-- 그래서 누적 `contact_steps` 가 env 의 `limiter_loss` 합과 일치해야 한다(자체 검사).

TRUNCATED 는 성공도 실패도 아닌 **우측 절단**으로 보존한다. `SPENT_FAIL` 의 임무적
의미는 감사 전까지 보류한다 (docs/26 §0.3) -- 자동 임무실패로 해석하지 않는다.

torch-free.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from shepherd.agents.baselines import (arc_redeploy_limiter, arc_slots,
                                       brake_limiter, hold_position_limiter,
                                       lambda_brake_limiter, min_cost_assignment,
                                       scripted_finisher,
                                       scripted_shaping_limiter)

__all__ = ["MissionResult", "run_episode", "run_batch", "summarize",
           "intercept_limiter", "intercept_lead_time", "scripted_role_actions",
           "LABELS", "LIMITER_MODES", "ROLES"]

LABELS = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL",
          "PENETRATED", "SPENT_FAIL", "TRUNCATED")
LIMITER_MODES = ("hold", "ring", "intercept", "brake", "lam20", "arc")
ROLES = ("limiter", "finisher")


@dataclass
class MissionResult:
    label: str
    outcome: str                        # env 배타 결과
    seed: int
    steps: int
    n_contact: int                      # 접촉 limiter 집합 크기 (에피소드 수준)
    contact_ids: tuple = ()
    contact_steps: int = 0              # 스텝별 접촉 합 (env limiter_loss 합과 대조용)
    env_limiter_loss_sum: float = 0.0
    fire_step: Optional[int] = None
    wasted_fire: int = 0
    min_target_dist: float = float("inf")
    clean_crossings: int = 0
    limiter_mode: str = ""
    attacker: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def captured(self) -> bool:
        return self.outcome == "CAPTURED"

    @property
    def net_capture(self) -> bool:
        return self.label == "NET_CAPTURE"


def intercept_lead_time(rel_p, v_att, v_lim_max):
    """선도 충돌 해: |rel_p + v_att*t| = v_lim_max*t 의 최소 양의 근.

        (|v_att|^2 - v_max^2) t^2 + 2 (rel_p . v_att) t + |rel_p|^2 = 0

    `|v_att| < v_max` 이면 근이 정확히 하나 (항상 요격 가능).
    **`|v_att| > v_max`(느린 요격체)면 근이 0개 또는 2개** -- 즉 기하가 허락할 때만
    요격 가능하다. 이 판별식이 곧 docs/29 §12.2 의 "꼬리 추격 불가 · 선도 차단 가능"
    을 대수적으로 표현한 것이다. 근이 없으면 None.
    """
    rel_p = np.asarray(rel_p, float); v_att = np.asarray(v_att, float)
    a = float(v_att @ v_att) - float(v_lim_max) ** 2
    b = 2.0 * float(rel_p @ v_att)
    c = float(rel_p @ rel_p)
    if abs(a) < 1e-12:
        return None if abs(b) < 1e-12 else (-c / b if -c / b > 0 else None)
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        return None                                   # 요격 불가 기하
    sq = float(np.sqrt(disc))
    roots = sorted(r for r in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)) if r > 1e-9)
    return roots[0] if roots else None


def intercept_limiter(i, p_lim, v_lim, p_att, v_att, *, tau_kill, a_max, margin,
                      v_max=None):
    """하드킬 baseline arm: 선도 충돌점으로 최대 가속 + 기하 충족 시 커밋.

    "그냥 박는다" arm 이다. 네트 없이 limiter 만으로 막는 경우의 대조군이며
    `N*_without_net` 을 재는 도구다 (docs/29 §12.3). 교과서적 constant-bearing
    유도이므로 손튜닝이 아니다 -- baseline 을 약하게 두면 straw man 이 된다.
    """
    p_lim = np.asarray(p_lim, float); v_lim = np.asarray(v_lim, float)
    p_att = np.asarray(p_att, float); v_att = np.asarray(v_att, float)
    rel_p = p_att - p_lim
    t_lead = intercept_lead_time(rel_p, v_att, v_max if v_max else a_max)
    aim = p_att + v_att * (t_lead if t_lead is not None else tau_kill)
    err = aim - p_lim
    n = float(np.linalg.norm(err))
    a_cmd = (err / n) * a_max if n > 1e-12 else np.zeros(3)
    rel_v = v_att - v_lim
    d_nom = float(np.linalg.norm(rel_p + rel_v * tau_kill))
    commit = 1.0 if d_nom <= margin else 0.0
    return np.array([a_cmd[0], a_cmd[1], a_cmd[2], commit], dtype=np.float32)


def _limiter_v_max(env, scn):
    """백엔드의 실제 limiter 속도 한계 (권위 소스). 없으면 scenario 로 폴백."""
    try:
        return float(env.backend.by_name(env.limiter_ids[0]).limits.v_max)
    except Exception:                                          # pragma: no cover
        return float(getattr(scn.limiter, "v_max", 80.0))


def _zero_commit(acts):
    """★ Box(4) idx3 을 0 으로 눌러 커밋을 막는다.

    `params.py` 는 `scripted.limiter_pressure = 1.0` 을 *"RESERVED -- env
    receives-and-ignores"* 로 문서화했다. 동결 env 에서는 참이었지만 **M4 가 그
    차원을 커밋 비트로 재사용한다**(docs/29 §3.1, 임계 0.5). 그래서 스크립트
    베이스라인을 그대로 M4 스택에 넣으면 **1스텝째에 전 limiter 가 하드킬을
    커밋**해 버린다(실측: n_committed=4). 그러면 baseline 의 조향은 의미가 없어지고
    hold/ring/intercept 가 구분되지 않는다.

    베이스라인의 기본값은 **커밋 안 함**이다 -- 공짜 하드킬을 주지 않는 보수적 쪽.
    하드킬 baseline 이 필요하면 `baseline_commit=True` 로 명시적으로 켠다.
    """
    for k, v in list(acts.items()):
        a = np.asarray(v, np.float32).copy()
        if a.shape[-1] >= 4:
            a[3] = 0.0
            acts[k] = a
    return acts


def _limiter_actions(env, scn, lay, mode, lims, p_att, v_att, limiter_kw=None):
    if mode == "hold":
        return {lid: hold_position_limiter() for lid in env.limiter_ids}
    if mode == "arc":
        # docs/63 r2 scripted baseline. 자유도 = (r_d, dphi) 뿐 -- 반드시
        # 호출부가 grid 값을 명시한다 (silent default 금지, F4).
        if not limiter_kw or "r_d" not in limiter_kw or "dphi" not in limiter_kw:
            raise ValueError(
                "limiter_mode='arc' 는 limiter_kw={'r_d':..,'dphi':..} 필수 "
                "(docs/63 F4 grid)")
        n = len(env.limiter_ids)
        slots = arc_slots(lay.target, p_att, limiter_kw["r_d"],
                          limiter_kw["dphi"], n=n)
        pos = [env._p(lims[i]) for i in range(n)]
        perm = min_cost_assignment(pos, slots)
        return {lid: arc_redeploy_limiter(pos[i], env._v(lims[i]),
                                          slots[perm[i]],
                                          a_max=scn.limiter.a_max)
                for i, lid in enumerate(env.limiter_ids)}
    if mode == "intercept":
        spec = getattr(env, "spec", None)
        tau_k = 0.1 if spec is None else spec.tau_kill
        a_lim = getattr(env, "a_lim_max", scn.limiter.a_max)
        margin = env.kill_radius + 0.5 * (a_lim - env.a_att_max) * tau_k ** 2
        return {lid: intercept_limiter(
                    i, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                    tau_kill=tau_k, a_max=scn.limiter.a_max, margin=margin,
                    v_max=_limiter_v_max(env, scn))
                for i, lid in enumerate(env.limiter_ids)}
    # ★ 제4병목 계측 arm (docs/20 §6). 관측 전용 단순 컨트롤러 -- 학습이
    #   이것들을 못 넘으면 "RL 이 필요하다" 를 주장할 수 없다.
    if mode in ("brake", "lam20"):
        a_max = scn.limiter.a_max
        fn = brake_limiter if mode == "brake" else lambda_brake_limiter
        return {lid: fn(env._v(lims[i]), a_max)
                for i, lid in enumerate(env.limiter_ids)}
    if mode == "ring":
        return {lid: scripted_shaping_limiter(
                    i, env.N, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                    tau=env.tau_deploy, a_max=scn.limiter.a_max,
                    r_ring=lay.r_ring, dt=env.dt)
                for i, lid in enumerate(env.limiter_ids)}
    raise ValueError(f"unknown limiter mode {mode!r}; allowed: {LIMITER_MODES}")


def scripted_role_actions(env, scn, lay, *, roles: Sequence[str] = ROLES,
                          limiter_mode: str = "hold", fire_mode: str = "clean",
                          prev_clean: bool = False, baseline_commit: bool = False,
                          states=None, limiter_kw=None) -> Dict[str, np.ndarray]:
    """스크립트 역할의 **env Box** 행동. `roles` 에 든 역할만 낸다.

    WHY 한 곳에만 두는가 (docs/48 §3)
    ---------------------------------
    역할 분리 실험은 "한쪽만 스크립트로 고정한 팔"을 만든다. 그 팔의 스크립트
    역할이 기준선(`hold`)의 같은 역할과 **비트 단위로 같은 규칙**이어야 격차의
    귀속이 성립한다. 규칙을 두 군데 두면 갈라지고, 갈라지면 LS-SS 차이가
    "학습의 기여"가 아니라 "두 구현의 차이"가 된다. 그래서 기준선 경로와
    동결 경로가 **이 함수 하나**를 공유한다 (P52 가 동치를 강제한다).

    `states` 는 호출부가 이미 뽑아 둔 `env._states()` 를 재사용하기 위한 것이다
    (같은 스텝에서 두 번 뽑으면 값은 같지만 낭비다).
    """
    lims, fin, att = env._states() if states is None else states
    p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
    acts: Dict[str, np.ndarray] = {}
    if "limiter" in roles:
        acts.update(_limiter_actions(env, scn, lay, limiter_mode, lims, p_att,
                                     v_att, limiter_kw=limiter_kw))
        if not baseline_commit:
            _zero_commit(acts)              # idx3 = 커밋 비트 (M4). 기본 OFF
    if "finisher" in roles:
        if fire_mode == "clean":
            trig = bool(prev_clean)
        elif fire_mode == "x_fire":
            trig = bool(p_att[0] <= lay.x_fire)
        elif fire_mode == "never":
            trig = False
        else:
            raise ValueError(f"unknown fire_mode {fire_mode!r}")
        acts[env.finisher_id] = scripted_finisher(
            p_fin, p_att, v_att, tau=env.tau_deploy, clean_threshold_crossed=trig)
    return acts


def run_episode(env, scn, lay, *, seed: int = 0, limiter_mode: str = "hold",
                fire_mode: str = "clean", max_steps: Optional[int] = None,
                attacker_name: str = "", policy=None,
                baseline_commit: bool = False,
                scripted_roles: Sequence[str] = (),
                limiter_kw=None) -> MissionResult:
    """한 에피소드. env.step / env termination 을 그대로 호출한다 (술어 복제 금지).

    fire_mode:
      "clean"  직전 스텝의 clean_net_threshold_crossed 에서 발사 제안 (원칙적)
      "x_fire" lay.x_fire 위치 트리거 (레거시 데모 baseline 과 동일)
      "never"  발사 안 함 (무개입 상한 확인용)
    FSM 의 fire gate(R2) 가 최종 판정하므로 어느 쪽이든 제안일 뿐이다.

    policy: 주면 limiter/finisher 행동을 이 콜러블이 정한다 (학습 정책 평가용).
      signature: policy(obs, flags) -> {agent_id: action}. limiter_mode/fire_mode
      는 무시된다. **주지 않으면 기존 경로와 bit-identical** 이다.

    scripted_roles: 역할 분리(docs/48). 여기 든 역할은 `policy` 가 무엇을 내든
      **스크립트로 덮어쓴다** -- 그 역할에 한해 `limiter_mode` / `fire_mode` 가
      다시 유효해진다. 기본 `()` 이면 기존 경로와 bit-identical.
      정책의 그 역할 출력은 계산은 되지만 env 에 닿지 않는다.
    """
    obs_d, _ = env.reset(seed=seed)
    obs = obs_d[env.limiter_ids[0]] if policy is not None else None
    flags: dict = {}
    horizon = int(lay.episode_len if max_steps is None else max_steps)

    contact: set = set()
    contact_steps = 0
    loss_sum = 0.0
    fire_step: Optional[int] = None
    clean_crossings = 0
    min_dist = float("inf")
    outcome = "TRUNCATED"
    prev_clean = False
    steps = 0
    target = np.asarray(lay.target, float)

    for t in range(horizon):
        lims, fin, att = env._states()
        p_att = env._p(att)          # v_att / p_fin 은 scripted_role_actions 안에서 뽑는다

        # --- 접촉 집계: env L353 과 동일 술어 · 동일(이동 전) 상태 -------------
        for i, s in enumerate(lims):
            if float(np.linalg.norm(p_att - env._p(s))) <= env.kill_radius:
                contact.add(i)
                contact_steps += 1

        min_dist = min(min_dist, float(np.linalg.norm(p_att - target)))

        if policy is not None:
            # 학습 정책 평가 경로. limiter_mode / fire_mode 는 무시된다.
            acts = dict(policy(obs, flags))
            if scripted_roles:              # 역할 분리 (docs/48): 해당 역할만 덮어쓴다
                acts.update(scripted_role_actions(
                    env, scn, lay, roles=scripted_roles, limiter_mode=limiter_mode,
                    fire_mode=fire_mode, prev_clean=prev_clean,
                    baseline_commit=baseline_commit, states=(lims, fin, att),
                    limiter_kw=limiter_kw))
        else:
            acts = scripted_role_actions(
                env, scn, lay, roles=ROLES, limiter_mode=limiter_mode,
                fire_mode=fire_mode, prev_clean=prev_clean,
                baseline_commit=baseline_commit, states=(lims, fin, att),
                limiter_kw=limiter_kw)
        acts[env.adversary_id] = np.zeros(3, np.float32)   # env-scripted; 무시됨

        obs_next, _, term, trunc, info = env.step(acts)
        steps = t + 1
        fi = info[env.finisher_id]
        if policy is not None:
            obs, flags = obs_next[env.limiter_ids[0]], fi

        loss_sum += float(fi.get("limiter_loss", 0.0))
        # A3-privileged 채널: 직전 스텝 v_shot_soft 를 공격자에게 흘린다(1스텝 지연).
        # fair 변형은 이 값을 무시하고 관측 대리량만 쓴다.
        try:
            (env.inner if hasattr(env, "inner") else env)._last_v_shot_soft = \
                float(fi.get("v_shot_soft", 0.0))
        except Exception:                                      # pragma: no cover
            pass
        prev_clean = bool(fi.get("clean_net_threshold_crossed", False))
        clean_crossings += int(prev_clean)
        if fi.get("fire_event") and fire_step is None:
            fire_step = t

        terminated = bool(term[env.finisher_id]) if term else False
        truncated = bool(trunc[env.finisher_id]) if trunc else False
        if terminated:
            if fi.get("hard_kill"):
                outcome = "HARD_KILL"          # M4: 파괴적 성공 (docs/29 §4)
            elif fi.get("captured"):
                outcome = "CAPTURED"
            elif fi.get("penetrated"):
                outcome = "PENETRATED"
            else:
                outcome = "SPENT_FAIL"       # env L349: SPENT and not captured
            break
        if truncated:
            outcome = "TRUNCATED"
            break

    # 종료 후 상태로 최소거리 한 번 더 (침투는 이동 후 판정이므로)
    try:
        att2 = env._states()[2]
        min_dist = min(min_dist, float(np.linalg.norm(env._p(att2) - target)))
    except Exception:                                     # pragma: no cover
        pass

    if outcome == "CAPTURED":
        label = "NET_CAPTURE" if not contact else "CAPTURE_WITH_CONTACT"
    else:
        label = outcome
    sysinfo = {k: fi.get(k) for k in ("n_committed", "n_retired", "veto_events")} \
        if "fi" in dir() else {}

    return MissionResult(
        label=label, outcome=outcome, seed=int(seed), steps=steps,
        n_contact=len(contact), contact_ids=tuple(sorted(contact)),
        contact_steps=contact_steps, env_limiter_loss_sum=loss_sum,
        fire_step=fire_step, wasted_fire=int(env.fsm.wasted_fire),
        min_target_dist=min_dist, clean_crossings=clean_crossings,
        limiter_mode=limiter_mode, attacker=attacker_name,
    )


def run_batch(env, scn, lay, seeds: Sequence[int], **kw) -> List[MissionResult]:
    return [run_episode(env, scn, lay, seed=int(s), **kw) for s in seeds]


def summarize(results: Sequence[MissionResult]) -> dict:
    n = max(len(results), 1)
    counts = {lab: sum(1 for r in results if r.label == lab) for lab in LABELS}
    return dict(
        n=len(results),
        counts=counts,
        rates={lab: counts[lab] / n for lab in LABELS},
        net_capture_rate=counts["NET_CAPTURE"] / n,
        hard_kill_rate=counts["HARD_KILL"] / n,
        # 2층 지표 (docs/29 §4): 1차 = 침투 저지율, 2차 = 비손실 비율
        interdiction_rate=1.0 - counts["PENETRATED"] / n,
        nondestructive_frac=(
            (counts["NET_CAPTURE"] + counts["CAPTURE_WITH_CONTACT"])
            / max(counts["NET_CAPTURE"] + counts["CAPTURE_WITH_CONTACT"]
                  + counts["HARD_KILL"], 1)),
        penetration_rate=counts["PENETRATED"] / n,
        mean_contact=float(np.mean([r.n_contact for r in results])) if results else 0.0,
        contact_free_frac=(sum(1 for r in results if r.n_contact == 0) / n),
        mean_min_dist=float(np.mean([r.min_target_dist for r in results])) if results else 0.0,
    )


def _main(argv=None):                                     # pragma: no cover
    from shepherd.params import as_config
    from shepherd.train.make_env import make_train_env

    ap = argparse.ArgumentParser(description="mission-level rollout (5분할 라벨)")
    ap.add_argument("--limiter", default="hold", choices=list(LIMITER_MODES))
    ap.add_argument("--fire", default="clean", choices=["clean", "x_fire", "never"])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--seed0", type=int, default=0)
    args = ap.parse_args(argv)

    env, scn, lay = make_train_env(as_config())
    res = run_batch(env, scn, lay, range(args.seed0, args.seed0 + args.seeds),
                    limiter_mode=args.limiter, fire_mode=args.fire)
    s = summarize(res)
    print(f"limiter={args.limiter} fire={args.fire} n={s['n']}")
    for lab in LABELS:
        print(f"  {lab:<22} {s['counts'][lab]:3d}  ({s['rates'][lab]:.2f})")
    print(f"  mean_contact={s['mean_contact']:.2f}  "
          f"contact_free={s['contact_free_frac']:.2f}  "
          f"mean_min_dist={s['mean_min_dist']:.2f}")


if __name__ == "__main__":                                # pragma: no cover
    _main()
