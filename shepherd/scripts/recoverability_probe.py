"""miss 7판 recoverability 2×2 probe (docs/56, ★ §7.1 상수 선언 후 구현).

지위: deterministic lethality(Pk=1) 아래의 저장된 7개 miss 상태 recoverability
upper-bound probe. 성공률 추정·일반 mode-handoff 성능 평가가 아니다.

구성
----
- 분기: 같은 seed 결정론 재실행 -> s0 부터 limiter 행동만 교체 (checkpoint =
  재실행; 상태 직렬화 없음). 공격자·finisher·발사 규칙은 원 계약 그대로
  closed-loop (docs/56 §2 -- 고정 궤적 재생 금지).
- privileged planner: CEM (P=64, I=2, elite 16, seed 3) × 경량 클론 rollout.
  경량 클론 = viability.n_samples 축소(16). 발사 후 dynamics 는 v_shot 무관
  (A2 bait_privileged=False · FSM 발사게이트 소진) -- P83d 가 bit 동일성 강제.
- proxy(lexicographic L1 무력화 ≻ L2 침투회피 ≻ L3 시각 ≻ L4 거리 tie-break)
  는 후보 선택 전용. **최종 판정은 full-fidelity env replay 의 terminal 라벨만.**

torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec, _seg_min_dist
from shepherd.m4_env import build_m4_env
from shepherd.scripts.boxed_arm_audit import _sysenv
from shepherd.scripts.mission_rollout import scripted_role_actions
from shepherd.spawn_rand import SpawnSpec

__all__ = ["run_probe", "MISS_EPISODES"]

# V3b hold/clean miss 7판 (results/handoff_audit.json)
MISS_EPISODES = (2, 26, 35, 46, 76, 95, 98)
SEED0 = 0

# §7.1 선언 상수 (docs/56 -- 결과 이전 커밋 6fcafa4)
K_SEG = 4            # limiter 별 piecewise-constant 가속 구간 수
POP = 64             # CEM population / iteration
ITERS = 2            # CEM iterations
ELITE = 16           # 25 %
SOLVER_SEEDS = (0, 1, 2)
CLONE_N_SAMPLES = 16  # 경량 클론 (dynamics 무관 -- P83d 로 강제)
EPISODE_LEN = 80


def _flags():
    return dict(system=SystemSpec(enabled=True, contact_resolver=True,
                                  miss_terminates=False, p_kill=1.0),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def _build(ep: int, *, n_samples: Optional[int] = None):
    extra = {"viability.n_samples": int(n_samples)} if n_samples else None
    st = build_m4_env(SEED0, ep, **_flags(), extra_cfg=extra)
    return st.env, st.scn, st.lay


def _analytic_backend(env):
    """프록시 사슬 밑의 AnalyticBackend."""
    b = env.inner.backend if hasattr(env, "inner") else env.backend
    while hasattr(b, "_inner"):
        b = b._inner
    return b


class _Driver:
    """run_episode 의 스텝 규약을 그대로 미러한 수동 구동자.

    mission_rollout.run_episode L293-309 와 같은 순서/부수효과를 유지한다
    (_last_v_shot_soft 주입 · prev_clean 추적) -- P83c 가 V3b 재현을 강제.
    """

    def __init__(self, env, scn, lay, ep: int):
        self.env, self.scn, self.lay, self.ep = env, scn, lay, ep
        env.reset(seed=SEED0 + ep)
        self.se = _sysenv(env)
        self.fid = env.finisher_id
        self.fire_mode = "clean"          # P84 채널 격리용 (기본 = 기존과 동일)
        self.prev_clean = False
        self.t = -1                       # 마지막으로 실행한 loop index
        self.fire_step: Optional[int] = None
        self.handoff_step: Optional[int] = None
        self.done = False
        self.label: Optional[str] = None
        self.min_swept: float = np.inf    # 개입 후 진단용 (구 proxy L4)
        self.first_kill_step: Optional[int] = None
        # P2' NK-aware 추적 (docs/58 §4): NK-밖 스텝에서의 최소 swept 와
        # 그 시점 margin. NK-안 접근은 여기 기여하지 않는다.
        self.min_out_swept: float = np.inf
        self.margin_at_best: float = -np.inf

    def step(self, limiter_override: Optional[Dict[str, np.ndarray]] = None,
             limiter_mode: str = "hold") -> dict:
        env, scn, lay = self.env, self.scn, self.lay
        self.t += 1
        lims, fin, att = env._states()
        pre_lims = [env._p(s).copy() for s in lims]
        p_att_pre = env._p(att).copy()

        acts = scripted_role_actions(env, scn, lay, limiter_mode=limiter_mode,
                                     fire_mode=self.fire_mode,
                                     prev_clean=self.prev_clean,
                                     states=(lims, fin, att))
        if limiter_override is not None:
            acts.update(limiter_override)
        acts[env.adversary_id] = np.zeros(3, np.float32)

        _, _, term, trunc, info = env.step(acts)
        fi = info.get(self.fid) or next(iter(info.values()), {})
        # run_episode L305 미러
        try:
            (env.inner if hasattr(env, "inner") else env)._last_v_shot_soft = \
                float(fi.get("v_shot_soft", 0.0))
        except Exception:                                     # pragma: no cover
            pass
        self.prev_clean = bool(fi.get("clean_net_threshold_crossed", False))
        if fi.get("fire_event") and self.fire_step is None:
            self.fire_step = self.t
        if fi.get("net_miss_handoff"):
            self.handoff_step = self.t

        # 진단: swept 최소거리 (retired 제외, resolver 와 같은 술어)
        lims2, _, att2 = env._states()
        step_min = np.inf
        for i in range(len(lims2)):
            if i in self.se.retired:
                continue
            d = _seg_min_dist(p_att_pre - pre_lims[i],
                              env._p(att2) - env._p(lims2[i]))
            step_min = min(step_min, d)
        self.min_swept = min(self.min_swept, step_min)
        # NK-밖 스텝만 (P2', docs/58 §4)
        d_asset = float(np.linalg.norm(env._p(att2)
                                       - np.asarray(lay.target, float)))
        if d_asset > float(self.se.spec.r_nk) and step_min < self.min_out_swept:
            self.min_out_swept = step_min
            self.margin_at_best = d_asset - float(self.se.spec.r_nk)
        if self.se.hard_kill and self.first_kill_step is None:
            self.first_kill_step = self.t

        if term.get(self.fid):
            self.done = True
            self.label = ("HARD_KILL" if fi.get("hard_kill") else
                          "CAPTURED" if fi.get("captured") else
                          "PENETRATED" if fi.get("penetrated") else "SPENT_FAIL")
        elif trunc.get(self.fid):
            self.done = True
            self.label = "TRUNCATED"
        return fi

    # limiter Box(4) 행동 dict 생성 -----------------------------------------
    def limiter_acts_from_plan(self, plan: np.ndarray, s0: int) -> Dict[str, np.ndarray]:
        """plan: (4, K_SEG, 3). 현재 스텝 t+1 에 적용할 구간 가속."""
        step_in = (self.t + 1) - s0
        H = EPISODE_LEN - s0
        seg = min(int(step_in * K_SEG // max(H, 1)), K_SEG - 1)
        out = {}
        env = self.env
        for i, lid in enumerate(env.limiter_ids):
            a = plan[i, seg]
            out[lid] = np.array([a[0], a[1], a[2], 0.0], np.float32)
        return out


def replay_baseline(ep: int, *, n_samples: Optional[int] = None,
                    max_steps: int = EPISODE_LEN) -> _Driver:
    """hold/clean 원 replay (V3b 재현 경로). 종료까지 굴린다."""
    env, scn, lay = _build(ep, n_samples=n_samples)
    d = _Driver(env, scn, lay, ep)
    for _ in range(max_steps):
        d.step()
        if d.done:
            break
    return d


def drive_to(ep: int, s0: int, *, n_samples: Optional[int] = None) -> _Driver:
    """분기 지점 직전(s0-1)까지 원 행동으로 결정론 재실행."""
    env, scn, lay = _build(ep, n_samples=n_samples)
    d = _Driver(env, scn, lay, ep)
    for _ in range(s0):
        d.step()
        if d.done:
            break
    return d


# ------------------------------------------------------------- state clone --
_CLONE_FIELDS = ("commits", "retired", "pending", "hard_kill", "veto_events",
                 "net_spent", "net_spent_step", "_charged", "_step_i", "_seed")


def transfer_state(src: _Driver, dst: _Driver) -> _Driver:
    """src(full) 의 현 상태를 dst(경량 클론)에 이식한다 (P83d 가 동치 강제).

    dst 는 재사용 가능 -- 아래 필드가 상태의 전부라는 주장 자체를 P83d 가 검증.
    """
    import copy as _copy
    bs, bd = _analytic_backend(src.env), _analytic_backend(dst.env)
    bd._t = bs._t
    for a_s, a_d in zip(bs.agents, bd.agents):
        a_d.p = a_s.p.copy(); a_d.v = a_s.v.copy(); a_d.e = a_s.e.copy()
    es, ed = src.se.inner, dst.se.inner
    ed.fsm = es.fsm
    ed._step_i = es._step_i
    ed._seed = es._seed
    ed._pending_capture = es._pending_capture
    ed.agents = list(es.agents)
    ed._last_v_shot_soft = getattr(es, "_last_v_shot_soft", None)
    for f in _CLONE_FIELDS:
        setattr(dst.se, f, _copy.deepcopy(getattr(src.se, f)))
    dst.t = src.t
    dst.prev_clean = src.prev_clean
    dst.fire_step, dst.handoff_step = src.fire_step, src.handoff_step
    dst.done, dst.label = src.done, src.label
    dst.min_swept = np.inf
    dst.min_out_swept = np.inf
    dst.margin_at_best = -np.inf
    dst.first_kill_step = src.first_kill_step
    return dst


def clone_at(src: _Driver, ep: int, *,
             n_samples: Optional[int] = CLONE_N_SAMPLES) -> _Driver:
    """n_samples=None -> full-fidelity 클론 (pre-fire arm 용, docs/58 §6)."""
    env, scn, lay = _build(ep, n_samples=n_samples)
    return transfer_state(src, _Driver(env, scn, lay, ep))


# ---------------------------------------------------------------- planner ---
@dataclass
class PlanResult:
    plan: object                     # ("accels", ndarray) | ("policy", str)
    proxy: tuple
    no_solution: bool
    rollouts: int


def _proxy_score(d: _Driver, s0: int) -> tuple:
    """lexicographic (큰 쪽 우수): L1 무력화 ≻ L2 침투회피 ≻ L3 -시각 ≻ L4 -거리."""
    neutral = 1 if d.label in ("HARD_KILL", "CAPTURED") else 0
    no_pen = 0 if d.label == "PENETRATED" else 1
    t_kill = d.first_kill_step if d.first_kill_step is not None else EPISODE_LEN + 1
    return (neutral, no_pen, -t_kill, -float(d.min_swept))


def _proxy_score_nk(d: _Driver, s0: int) -> tuple:
    """P2' NK-aware lexicographic (docs/58 §4). NK-안 접근은 기여 금지.

    L1 NK-밖 무력화(HARD_KILL; Pk=1·P11 상 동치) ≻ L2 NK-밖 kill event 수 ≻
    L3 NK-밖 스텝 최소 swept ↓ ≻ L4 최근접 NK-밖 접근의 margin ↑ ≻
    L5 침투 지연(종료 스텝) ↑
    """
    kill = 1 if d.label in ("HARD_KILL", "CAPTURED") else 0
    out_kills = sum(1 for r in d.se.commits
                    if r.source == "contact" and r.outcome == "KILL")
    return (kill, out_kills, -float(d.min_out_swept),
            float(d.margin_at_best), d.t + 1)


def _rollout(src: _Driver, s0: int, plan, reuse: _Driver,
             score_fn=_proxy_score) -> tuple:
    d = transfer_state(src, reuse)
    while not d.done and d.t + 1 < EPISODE_LEN:
        if plan[0] == "accels":
            d.step(limiter_override=d.limiter_acts_from_plan(plan[1], s0))
        else:
            d.step(limiter_mode=plan[1])
        # ModeSystemEnv 절단은 wrapper 가 냄; loop 상한은 안전망
    return score_fn(d, s0)


def _sample_ball(rng, shape, a_max):
    """단위공 내 균일 × a_max (§7.1 선언 파라미터화)."""
    g = rng.normal(size=shape)
    g /= np.maximum(np.linalg.norm(g, axis=-1, keepdims=True), 1e-12)
    r = rng.uniform(size=shape[:-1] + (1,)) ** (1.0 / 3.0)
    return g * r * a_max


def _clip_ball(x, a_max):
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return np.where(n > a_max, x * (a_max / np.maximum(n, 1e-12)), x)


def plan_cem(src: _Driver, ep: int, s0: int, a_max: float, *,
             seeds: Sequence[int] = SOLVER_SEEDS,
             score_fn=_proxy_score,
             clone_n_samples: Optional[int] = CLONE_N_SAMPLES) -> PlanResult:
    """§7.1: CEM P=64·I=2·elite16. seeds/score_fn/clone 충실도는 확장점.

    clone_n_samples=None -> full-fidelity rollout (pre-fire, docs/58 §6 --
    발사 전엔 v_shot 이 dynamics 에 인과적이라 경량 클론 금지).
    """
    best_plan, best_score = None, None
    rollouts = 0
    structured = [("policy", "intercept"), ("policy", "hold")]
    reuse = clone_at(src, ep, n_samples=clone_n_samples)   # 클론 1개 재사용
    for ss in seeds:
        rng = np.random.default_rng(97 + 1000 * ss + ep)
        mean = np.zeros((4, K_SEG, 3))
        std = np.full((4, K_SEG, 3), a_max / 2.0)
        for it in range(ITERS):
            cands = []
            if it == 0:
                cands.extend(structured)            # 구조 후보 (P 에 포함)
            n_rand = POP - len(cands)
            if it == 0:
                sam = _sample_ball(rng, (n_rand, 4, K_SEG, 3), a_max)
            else:
                sam = _clip_ball(mean[None] + std[None] * rng.normal(
                    size=(n_rand, 4, K_SEG, 3)), a_max)
            cands.extend(("accels", s) for s in sam)
            scored = []
            for c in cands:
                scored.append((_rollout(src, s0, c, reuse, score_fn), c))
                rollouts += 1
            scored.sort(key=lambda x: x[0], reverse=True)
            if best_score is None or scored[0][0] > best_score:
                best_score, best_plan = scored[0][0], scored[0][1]
            elite = [c[1][1] for c in scored[:ELITE] if c[1][0] == "accels"]
            if elite:
                e = np.stack(elite)
                mean, std = e.mean(axis=0), e.std(axis=0) + 1e-3
    no_solution = best_score[0] < 1          # L1 무력화 후보 없음
    return PlanResult(best_plan, best_score, no_solution, rollouts)


# ------------------------------------------------------------------ arms ----
def run_arm(ep: int, arm: str, t_star: int, s0: Optional[int] = None, *,
            seeds: Sequence[int] = SOLVER_SEEDS,
            score_fn=_proxy_score,
            clone_n_samples: Optional[int] = CLONE_N_SAMPLES) -> dict:
    """arm ∈ *-INT | *-ORC. s0 미지정 시 2×2 규약 (T0=t*+1 / TP=t*−5).

    docs/57 §3 sweep · docs/58 §4 P2' 는 s0/seeds/score_fn 만 바꿔 같은 경로를
    재사용한다 (공식 복제 금지). 최종 판정 = full env replay 라벨.
    """
    if s0 is None:
        s0 = (t_star + 1) if arm.startswith("T0") else (t_star - 5)
    out = dict(episode=ep, arm=arm, s0=s0, t_star=t_star)

    plan = None
    if arm.endswith("ORC"):
        # ★ planning 기준 상태는 full env 로 몰고 가서 클론에 이식한다 --
        #   light env 를 처음부터 굴리면 fire gate(v_soft)가 달라 fire 시점이
        #   어긋날 수 있다. 이식 경로만 쓴다 (P83d 가 동치 강제).
        src_full = drive_to(ep, s0)
        a_max = float(src_full.scn.limiter.a_max)
        pr = plan_cem(src_full, ep, s0, a_max, seeds=seeds, score_fn=score_fn,
                      clone_n_samples=clone_n_samples)
        plan = pr.plan
        out.update(no_solution_within_budget=pr.no_solution,
                   proxy_score=[float(x) for x in pr.proxy],
                   rollouts=pr.rollouts,
                   plan_kind=plan[0] if plan else None)
        src = src_full
    else:
        src = drive_to(ep, s0)
        plan = ("policy", "intercept")
        out.update(no_solution_within_budget=None, rollouts=0,
                   plan_kind="policy")

    # ---- 최종: full-fidelity env replay (proxy 와 분리 -- P83g) ----------
    d = src
    d.min_swept = np.inf
    d.min_out_swept = np.inf
    d.margin_at_best = -np.inf
    while not d.done and d.t + 1 < EPISODE_LEN:
        if plan[0] == "accels":
            d.step(limiter_override=d.limiter_acts_from_plan(plan[1], s0))
        else:
            d.step(limiter_mode=plan[1])

    se = d.se
    lims, _, att = d.env._states()
    out.update(
        label=d.label,
        fire_step=d.fire_step,
        handoff_step=d.handoff_step,
        miss_still_occurred=bool(se.net_spent),
        first_kill_step=d.first_kill_step,
        steps=d.t + 1,
        min_swept_after=None if not np.isfinite(d.min_swept) else round(float(d.min_swept), 3),
        min_out_swept=None if not np.isfinite(d.min_out_swept) else round(float(d.min_out_swept), 3),
        margin_at_best=None if not np.isfinite(d.margin_at_best) else round(float(d.margin_at_best), 3),
        d_asset_final=round(float(np.linalg.norm(
            d.env._p(att) - np.asarray(d.lay.target, float))), 3),
        limiter_consumed=len(se.retired),
        contact_order=[(r.limiter_index, r.commit_step, r.outcome)
                       for r in se.commits if r.source == "contact"],
        lim_min_dist=[round(float(np.linalg.norm(d.env._p(att) - d.env._p(l))), 3)
                      for l in lims],
    )
    # 3분법 (docs/56 §6.1) + PRE_MISS 분리
    if d.label in ("HARD_KILL",):
        out["bucket"] = ("POST_MISS_NEUTRALIZATION" if se.net_spent
                         else "PRE_MISS_NEUTRALIZATION")
    elif d.label == "CAPTURED":
        out["bucket"] = "EARLY_PREP_NET_CAPTURE"
    elif d.label == "PENETRATED":
        out["bucket"] = "PENETRATED"
    else:
        out["bucket"] = d.label
    return out


def run_probe(episodes: Sequence[int] = MISS_EPISODES) -> dict:
    meta = {"contract": "docs/56 §7.1 (커밋 6fcafa4)", "Pk": 1.0,
            "clone_n_samples": CLONE_N_SAMPLES,
            "pop": POP, "iters": ITERS, "elite": ELITE,
            "solver_seeds": list(SOLVER_SEEDS)}
    rows: List[dict] = []
    for ep in episodes:
        base = replay_baseline(ep)
        t_star = base.handoff_step
        rec = dict(episode=ep, t_star=t_star, fire_step=base.fire_step,
                   base_label=base.label, base_steps=base.t + 1)
        rows.append({"arm": "BASE", **rec})
        assert t_star is not None, f"ep{ep}: handoff 미관측 -- V3b 재현 실패"
        for arm in ("T0-INT", "T0-ORC", "TP-INT", "TP-ORC"):
            rows.append(run_arm(ep, arm, t_star))
    return {"meta": meta, "records": rows}


def run_sweep(episodes: Sequence[int] = MISS_EPISODES) -> dict:
    """docs/57 §3 — 발사 후 latest-start sweep (ORC 만, §7.1 budget 불변).

    grid = {t_fire+1, t_fire+4, t*−5, t*−2, t*+1} (판별 dedup·정렬).
    성공 = final env replay 라벨 HARD_KILL (P11 로 NK-밖 무력화와 동치).
    """
    meta = {"contract": "docs/57 §3 (커밋 d15f01a)", "Pk": 1.0,
            "controller": "ORC only", "budget_per_point": POP * ITERS * len(SOLVER_SEEDS)}
    rows: List[dict] = []
    for ep in episodes:
        base = replay_baseline(ep)
        t_star, t_fire = base.handoff_step, base.fire_step
        assert t_star is not None and t_fire is not None
        grid = sorted({t_fire + 1, t_fire + 4, t_star - 5, t_star - 2, t_star + 1})
        rec = dict(episode=ep, t_fire=t_fire, t_star=t_star, grid=grid)
        rows.append({"arm": "BASE", **rec})
        latest = None
        for s0 in grid:
            r = run_arm(ep, "SW-ORC", t_star, s0=s0)
            r["fire_relative"] = s0 - t_fire
            rows.append(r)
            if r["label"] == "HARD_KILL":
                latest = max(latest, s0) if latest is not None else s0
        rows.append({"arm": "VERDICT", "episode": ep,
                     "latest_recoverable_start": latest})
    return {"meta": meta, "records": rows}


def run_p2prime(episodes: Sequence[int] = MISS_EPISODES) -> dict:
    """P2' — NK-aware proxy 재반증 (docs/58 §4, 커밋 500172e 사전등록).

    fire+1 한 시점 · seed 10 · NK-aware lexicographic. NK-밖 후보 1개면
    "닫힌 창" 해석 붕괴.
    """
    meta = {"contract": "docs/58 §4 (커밋 500172e)", "Pk": 1.0,
            "s0": "t_fire+1", "solver_seeds": list(range(10)),
            "proxy": "nk_aware", "budget_per_ep": POP * ITERS * 10}
    rows: List[dict] = []
    for ep in episodes:
        base = replay_baseline(ep)
        assert base.fire_step is not None and base.handoff_step is not None
        r = run_arm(ep, "P2-ORC", base.handoff_step, s0=base.fire_step + 1,
                    seeds=tuple(range(10)), score_fn=_proxy_score_nk)
        r["t_fire"] = base.fire_step
        rows.append(r)
        print(f"ep{ep:>3}: {r['label']:>11} nosol={r['no_solution_within_budget']} "
              f"out_swept={r['min_out_swept']} margin={r['margin_at_best']} "
              f"proxy={r['proxy_score']}", flush=True)
    return {"meta": meta, "records": rows}


def run_prefire(episodes: Sequence[int] = MISS_EPISODES) -> dict:
    """pre-fire arm (docs/58 §6, 결과 이전 커밋 사전등록) — legacy A2 마지막
    oracle 진단. s0 = t_fire−5, rollout·final 모두 full-fidelity, fire 시각·
    miss·v_shot·attacker 전부 closed-loop 재계산 (동결 금지 계약).
    """
    from shepherd.notify import ntfy
    meta = {"contract": "docs/58 §6", "Pk": 1.0, "s0": "t_fire-5",
            "rollout": "full-fidelity (clone_n_samples=None)",
            "solver_seeds": list(SOLVER_SEEDS), "proxy": "nk_aware",
            "budget_per_ep": POP * ITERS * len(SOLVER_SEEDS)}
    rows: List[dict] = []
    for ep in episodes:
        base = replay_baseline(ep)
        assert base.fire_step is not None and base.handoff_step is not None
        s0 = base.fire_step - 5
        r = run_arm(ep, "PF-ORC", base.handoff_step, s0=s0,
                    seeds=SOLVER_SEEDS, score_fn=_proxy_score_nk,
                    clone_n_samples=None)
        r["base_fire_step"] = base.fire_step
        r["new_fire_step"] = r.get("fire_step")      # 개입 후 실제 fire 시각
        n_veto = sum(1 for c in r.get("contact_order", [])
                     if c[2] == "VETO_NO_KINETIC")
        r["inside_nk_veto_events"] = n_veto
        # 5분법 (docs/58 §6)
        r["report_label"] = (
            "NET_CAPTURE" if r["label"] == "CAPTURED" else
            "OUTSIDE_NK_NEUTRALIZATION" if r["label"] == "HARD_KILL" else
            r["label"])
        rows.append(r)
        print(f"ep{ep:>3}: {r['report_label']:>26} nosol={r['no_solution_within_budget']} "
              f"fire {r['base_fire_step']}->{r['new_fire_step']} "
              f"veto_ev={n_veto} out_swept={r['min_out_swept']}", flush=True)
        ntfy(f"prefire ep{ep}: {r['report_label']} "
             f"nosol={r['no_solution_within_budget']}")
    return {"meta": meta, "records": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="recoverability probe (docs/56·57·58)")
    ap.add_argument("--episodes", type=int, nargs="*", default=list(MISS_EPISODES))
    ap.add_argument("--sweep", action="store_true",
                    help="docs/57 발사 후 latest-start sweep 실행")
    ap.add_argument("--p2prime", action="store_true",
                    help="docs/58 §4 NK-aware 재반증 실행")
    ap.add_argument("--prefire", action="store_true",
                    help="docs/58 §6 pre-fire arm 실행 (full-fidelity)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.prefire:
        r = run_prefire(tuple(a.episodes))
        if a.out:
            p = pathlib.Path(a.out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(r, indent=2, ensure_ascii=False),
                         encoding="utf-8")
            print(f"  -> {a.out}")
        return
    if a.p2prime:
        r = run_p2prime(tuple(a.episodes))
        if a.out:
            p = pathlib.Path(a.out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(r, indent=2, ensure_ascii=False),
                         encoding="utf-8")
            print(f"  -> {a.out}")
        return
    if a.sweep:
        r = run_sweep(tuple(a.episodes))
        for x in r["records"]:
            if x["arm"] == "BASE":
                print(f"ep{x['episode']:>3}: fire@{x['t_fire']} t*={x['t_star']} "
                      f"grid={x['grid']}")
            elif x["arm"] == "VERDICT":
                print(f"ep{x['episode']:>3}: latest_recoverable_start = "
                      f"{x['latest_recoverable_start']}")
            else:
                print(f"   s0={x['s0']:>3} (fire{x['fire_relative']:+d}) "
                      f"{x['label']:>11} {x['bucket']:>26} "
                      f"nosol={x.get('no_solution_within_budget')}")
        if a.out:
            p = pathlib.Path(a.out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(r, indent=2, ensure_ascii=False),
                         encoding="utf-8")
            print(f"  -> {a.out}")
        return
    r = run_probe(tuple(a.episodes))
    print(f"{'ep':>4} {'arm':>7} {'s0':>4} {'label':>12} {'bucket':>26} "
          f"{'miss?':>6} {'kill@':>6} {'nosol':>6}")
    for x in r["records"]:
        if x["arm"] == "BASE":
            print(f"{x['episode']:>4} {'BASE':>7} {'-':>4} {x['base_label']:>12} "
                  f"{'':>26} {'':>6} {'':>6} {'':>6}")
            continue
        print(f"{x['episode']:>4} {x['arm']:>7} {x['s0']:>4} {x['label']:>12} "
              f"{x['bucket']:>26} {str(x['miss_still_occurred']):>6} "
              f"{str(x['first_kill_step']):>6} "
              f"{str(x.get('no_solution_within_budget')):>6}")
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
