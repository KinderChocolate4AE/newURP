"""D1 — 선언한 유한 toy 의 exact solve (docs/105 §4, docs/106 §3).

목적: docs/104 T2 의 정책군·정보구조(양화 순서) 검산 **까지만**.
계수는 전부 SYNTHETIC_EXPLORATORY toy 예시값 (params.py `mode_switch.toy.*`).
연속 물리, F1 projectile net, 실제 C-UAS 의 불가능성을 인증하지 않으며,
p_net/p_kin 을 연구자가 정하므로 양성 reversal 은 만들어낼 수 있다 (105 §4.2).

모형 (유한·전수해석 가능):
  - 시간 t=0..T-1 이 곧 접근 거리 (결정론 접근). t==T 에 미요격이면 breach.
  - latent branch θ∈{0,1}, prior P(θ=1)=prior. t_cue 에 정확도 q 의 cue 1회
    (P(cue=θ)=q). 정책은 branch ID 가 아니라 (phase, t, cue) 정보상태만 본다.
    t_cue=None 은 cue 완전 마스킹 (정보-null 대조, 105 §4.2-2).
  - net: 1발, commit 후 tau_net step 뒤 resolve, P(성공|θ)=p_net[θ].
    commit 합법 조건 t+tau_net <= T-1.
  - kinetic: 즉시 resolve, t <= t_roe 만 합법 (닫히는 ROE 창),
    안전위반확률 pu(t)=pu0+pu_slope*t, 성공 P=p_kin[θ]. 비용 rho (net=1).
    kinetic commit 후 net 복귀 금지 (106 §1.4 = 104 §3.2 규칙 5).
  - first-hit 배타 outcome 의 toy 축약: {N_safe, K_safe, C_unsafe, B} 만
    존재 (K_illegal 은 guard 사전차단, L_unauth/timeout 없음 — 106 §3).

정책군 (104 §4.6 의 toy 구현):
  - Pi_rec  = 도달가능 정보상태 위 결정적 Markov 정책 전부.
  - Pi_fixed = Pi_rec 중 최초 commit mode 가 경로(=cue 값)에 독립인 것.
    구성상 Pi_fixed ⊆ Pi_rec (embedding 이 자동 성립).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Dict, FrozenSet, List, Optional, Tuple

PRE, NETF = "PRE", "NET_FAILED"
WAIT, NET, KIN = "WAIT", "NET", "KIN"

State = Tuple[str, int, Optional[int]]          # (phase, t, cue) cue∈{None,0,1}
Vec = Tuple[float, float, float]                # (P_prot, P_unsafe, E[cost]) | θ
Policy = Dict[State, str]

_EPS = 1e-9
_ROUND = 10


@dataclass(frozen=True)
class ToyParams:
    T: int
    t_cue: Optional[int]
    t_roe: int
    tau_net: int
    p_net: Tuple[float, float]
    p_kin: Tuple[float, float]
    pu0: float
    pu_slope: float
    prior: float                # P(θ=1)
    q: float                    # P(cue=θ)
    rho: float                  # kinetic 비용 / net 비용
    alpha: float
    beta: float


def default_params(**over) -> ToyParams:
    """단일 정의원 = params.py 레지스트리 (docs/105 §3·§4)."""
    from shepherd.params import PARAMS
    kw = {f: PARAMS[f"mode_switch.toy.{f}"].value
          for f in ToyParams.__dataclass_fields__}
    kw = {k: (tuple(v) if isinstance(v, (list, tuple)) else v) for k, v in kw.items()}
    kw.update(over)
    return ToyParams(**kw)


# ── 상태·행동 ────────────────────────────────────────────────────────────────
def legal_actions(p: ToyParams, s: State) -> Tuple[str, ...]:
    phase, t, _ = s
    acts = [WAIT]
    if phase == PRE and t + p.tau_net <= p.T - 1:
        acts.append(NET)
    if t <= p.t_roe:
        acts.append(KIN)
    return tuple(acts)


def _cue_states(p: ToyParams, phase: str, t: int, cue: Optional[int]) -> List[State]:
    """시각 t 도달 시 cue 가 새로 도착하면 두 값으로 분기, 아니면 단일 상태."""
    if cue is None and p.t_cue is not None and t >= p.t_cue:
        return [(phase, t, 0), (phase, t, 1)]
    return [(phase, t, cue)]


def root_states(p: ToyParams) -> List[State]:
    return _cue_states(p, PRE, 0, None)


def decision_states(p: ToyParams) -> List[State]:
    """모든 행동을 허용한 forward closure (정책 무관 도달가능 결정상태)."""
    seen, stack = set(), list(root_states(p))
    while stack:
        s = stack.pop()
        if s in seen or s[1] >= p.T:
            continue
        seen.add(s)
        phase, t, cue = s
        for a in legal_actions(p, s):
            if a == WAIT:
                if t + 1 < p.T:
                    stack.extend(_cue_states(p, phase, t + 1, cue))
            elif a == NET:
                stack.extend(_cue_states(p, NETF, t + p.tau_net, cue))
            # KIN 은 즉시 종결 — 후속 상태 없음
    return sorted(seen, key=lambda s: (s[1], s[0], -1 if s[2] is None else s[2]))


# ── 정책 평가 (θ 조건부 exact 재귀) ─────────────────────────────────────────
def _cue_prob(p: ToyParams, c: int, theta: int) -> float:
    return p.q if c == theta else 1.0 - p.q


def evaluate_theta(p: ToyParams, pol: Policy, s: State, theta: int,
                   memo: Optional[dict] = None) -> Vec:
    """상태 s 에서 branch θ 조건부 (P_prot, P_unsafe, E[cost])."""
    if memo is None:
        memo = {}
    key = (s, theta)
    if key in memo:
        return memo[key]
    phase, t, cue = s
    a = pol[s]

    def _mix(nphase: str, nt: int) -> Vec:
        if nt >= p.T:                                   # breach
            return (0.0, 0.0, 0.0)
        outs = _cue_states(p, nphase, nt, cue)
        if len(outs) == 1:
            return evaluate_theta(p, pol, outs[0], theta, memo)
        acc = [0.0, 0.0, 0.0]
        for ns in outs:
            w = _cue_prob(p, ns[2], theta)
            v = evaluate_theta(p, pol, ns, theta, memo)
            for i in range(3):
                acc[i] += w * v[i]
        return tuple(acc)

    if a == WAIT:
        out = _mix(phase, t + 1)
    elif a == NET:
        pn = p.p_net[theta]
        vf = _mix(NETF, t + p.tau_net)
        out = (pn + (1.0 - pn) * vf[0], (1.0 - pn) * vf[1],
               1.0 + (1.0 - pn) * vf[2])
    elif a == KIN:
        pu = p.pu0 + p.pu_slope * t
        pk = p.p_kin[theta]
        out = ((1.0 - pu) * pk, pu, p.rho)
    else:                                               # pragma: no cover
        raise ValueError(a)
    memo[key] = out
    return out


def evaluate(p: ToyParams, pol: Policy,
             prior: Optional[float] = None) -> Tuple[Vec, Vec, Vec]:
    """(무조건부 vec, θ=0 조건부, θ=1 조건부). root 의 cue 분기 포함."""
    pr1 = p.prior if prior is None else prior
    memo: dict = {}
    per_theta = []
    for theta in (0, 1):
        acc = [0.0, 0.0, 0.0]
        roots = root_states(p)
        for rs in roots:
            w = 1.0 if rs[2] is None else _cue_prob(p, rs[2], theta)
            v = evaluate_theta(p, pol, rs, theta, memo)
            for i in range(3):
                acc[i] += w * v[i]
        per_theta.append(tuple(acc))
    v0, v1 = per_theta
    mean = tuple((1.0 - pr1) * v0[i] + pr1 * v1[i] for i in range(3))
    return mean, v0, v1


# ── 정책 열거와 class 분류 ───────────────────────────────────────────────────
def enumerate_policies(p: ToyParams) -> List[Policy]:
    states = decision_states(p)
    choices = [legal_actions(p, s) for s in states]
    return [dict(zip(states, combo)) for combo in itertools.product(*choices)]


def first_commit_modes(p: ToyParams, pol: Policy) -> FrozenSet[str]:
    """정책의 트리에서 경로별 최초 commit mode 집합 (∅ = never-commit)."""
    out: set = set()

    def walk(s: State) -> None:
        phase, t, cue = s
        if t >= p.T:
            return
        a = pol[s]
        if a in (NET, KIN):
            out.add(a)
            return
        if t + 1 < p.T:
            for ns in _cue_states(p, phase, t + 1, cue):
                walk(ns)

    for rs in root_states(p):
        walk(rs)
    return frozenset(out)


def is_fixed(p: ToyParams, pol: Policy) -> bool:
    return len(first_commit_modes(p, pol)) <= 1


def feasible(p: ToyParams, vec: Vec) -> bool:
    return vec[0] >= p.alpha - _EPS and vec[1] <= p.beta + _EPS


def class_summary(p: ToyParams, pols: List[Policy],
                  prior: Optional[float] = None) -> dict:
    """정책 리스트의 feasibility 와 feasible 중 최소비용."""
    best = None
    n_feas = 0
    for pol in pols:
        mean, _, _ = evaluate(p, pol, prior)
        if feasible(p, mean):
            n_feas += 1
            if best is None or mean[2] < best[2]:
                best = mean
    return {"feasible": n_feas > 0, "n_feasible": n_feas,
            "min_cost": None if best is None else best[2],
            "best_vec": best}


def split_classes(p: ToyParams) -> Tuple[List[Policy], List[Policy]]:
    """(rec 전부, fixed 부분집합). Pi_fixed ⊆ Pi_rec 이 구성상 성립."""
    rec = enumerate_policies(p)
    fixed = [pol for pol in rec if is_fixed(p, pol)]
    return rec, fixed


# ── winning grid 와 strict region ────────────────────────────────────────────
def strict_grid(p: ToyParams, p0s: Tuple[float, ...],
                rhos: Tuple[float, ...]) -> dict:
    """초기 cell (prior, rho) 격자의 class winning set 과 strict 차집합.

    category: 0 = 둘 다 infeasible, 1 = 둘 다 feasible,
              2 = rec 만 (= strict cell), 3 = fixed 만 (발생하면 버그).
    """
    cells = []
    for rho in rhos:
        row = []
        for p0 in p0s:
            pp = replace(p, prior=p0, rho=rho)
            rec, fixed = split_classes(pp)
            r = class_summary(pp, rec)
            f = class_summary(pp, fixed)
            cat = {(False, False): 0, (True, True): 1,
                   (True, False): 2, (False, True): 3}[(r["feasible"], f["feasible"])]
            row.append({"p0": p0, "rho": rho, "cat": cat,
                        "rec_min_cost": r["min_cost"], "fixed_min_cost": f["min_cost"]})
        cells.append(row)
    n_strict = sum(1 for row in cells for c in row if c["cat"] == 2)
    assert not any(c["cat"] == 3 for row in cells for c in row), \
        "fixed feasible but rec not — Pi_fixed ⊆ Pi_rec 위반 (버그)"
    return {"p0s": list(p0s), "rhos": list(rhos), "cells": cells,
            "n_strict": n_strict}


# ── mode-rank (post-cue 정보상태별 선호 mode) ───────────────────────────────
def posterior(p: ToyParams, cue: int, prior: Optional[float] = None) -> float:
    """P(θ=1 | cue)."""
    pr1 = p.prior if prior is None else prior
    l1 = _cue_prob(p, cue, 1) * pr1
    l0 = _cue_prob(p, cue, 0) * (1.0 - pr1)
    return l1 / (l1 + l0)


def mode_value_at(p: ToyParams, s: State, mode: str) -> Optional[Vec]:
    """정보상태 s 에서 mode 를 지금 commit 할 때의 posterior 조건부 최선값.

    toy 단순화 (docs/106 §3): 제약을 s 조건부 벡터에 적용한다 (episode
    무조건부 제약의 국소 대용). feasible 한 continuation 이 없으면 None.
    """
    phase, t, cue = s
    assert cue is not None, "post-cue 상태 전용"
    if mode not in legal_actions(p, s):
        return None
    w1 = posterior(p, cue)
    best = None
    for pol in enumerate_policies(p):
        if pol[s] != mode:
            continue
        memo: dict = {}
        v0 = evaluate_theta(p, pol, s, 0, memo)
        v1 = evaluate_theta(p, pol, s, 1, memo)
        mean = tuple((1.0 - w1) * v0[i] + w1 * v1[i] for i in range(3))
        if feasible(p, mean) and (best is None or mean[2] < best[2]):
            best = mean
    return best


def rank_table(p: ToyParams) -> List[dict]:
    """도달가능 post-cue PRE 상태의 mode 선호표와 reversal 여부."""
    rows = []
    by_t: Dict[int, dict] = {}
    for s in decision_states(p):
        phase, t, cue = s
        if phase != PRE or cue is None:
            continue
        vN = mode_value_at(p, s, NET)
        vK = mode_value_at(p, s, KIN)
        pref = None
        if vN and vK:
            pref = NET if vN[2] <= vK[2] else KIN
        elif vN:
            pref = NET
        elif vK:
            pref = KIN
        by_t.setdefault(t, {})[cue] = pref
        rows.append({"t": t, "cue": cue, "pref": pref,
                     "net": vN, "kin": vK})
    n_rev = sum(1 for prefs in by_t.values()
                if len(prefs) == 2 and None not in prefs.values()
                and prefs[0] != prefs[1])
    return rows, n_rev


# ── 검산: 도달가능 벡터집합의 DP vs 전수열거 (105 §4.2-1) ───────────────────
def _round_pair(v0: Vec, v1: Vec) -> Tuple[Vec, Vec]:
    return (tuple(round(x, _ROUND) for x in v0),
            tuple(round(x, _ROUND) for x in v1))


def achievable_brute(p: ToyParams) -> FrozenSet:
    out = set()
    for pol in enumerate_policies(p):
        _, v0, v1 = evaluate(p, pol)
        out.add(_round_pair(v0, v1))
    return frozenset(out)


def achievable_dp(p: ToyParams) -> FrozenSet:
    """상태별 도달가능 (v_θ0, v_θ1) 집합의 backward DP.

    시간이 단조증가하는 DAG 라 한 정책 트리 안에서 같은 상태가 두 분기에
    나타나지 않으므로 후속상태 선택의 cartesian product 가 exact 하다.
    """
    @lru_cache(maxsize=None)
    def A(s: State) -> FrozenSet:
        phase, t, cue = s
        out = set()
        for a in legal_actions(p, s):
            if a == KIN:
                pu = p.pu0 + p.pu_slope * t
                pair = tuple(((1.0 - pu) * p.p_kin[th], pu, p.rho)
                             for th in (0, 1))
                out.add(_round_pair(*pair))
                continue
            if a == WAIT:
                nphase, nt, cost0 = phase, t + 1, 0.0
            else:                                       # NET
                nphase, nt, cost0 = NETF, t + p.tau_net, 1.0
            if nt >= p.T:                               # breach
                out.add(_round_pair((0, 0, cost0), (0, 0, cost0)))
                continue
            succ = _cue_states(p, nphase, nt, cue)
            for sel in itertools.product(*(A(ns) for ns in succ)):
                pair = []
                for th in (0, 1):
                    acc = [0.0, 0.0, cost0]
                    for ns, sv in zip(succ, sel):
                        w = (1.0 if ns[2] == cue
                             else _cue_prob(p, ns[2], th))
                        for i in range(3):
                            acc[i] += w * sv[th][i]
                    if a == NET:
                        pn = p.p_net[th]
                        acc = [pn + (1.0 - pn) * acc[0], (1.0 - pn) * acc[1],
                               1.0 + (1.0 - pn) * (acc[2] - cost0)]
                    pair.append(tuple(acc))
                out.add(_round_pair(*pair))
        return frozenset(out)

    roots = root_states(p)
    if len(roots) == 1:
        return A(roots[0])
    out = set()
    for sel in itertools.product(*(A(rs) for rs in roots)):
        pair = []
        for th in (0, 1):
            acc = [0.0, 0.0, 0.0]
            for rs, sv in zip(roots, sel):
                w = _cue_prob(p, rs[2], th)
                for i in range(3):
                    acc[i] += w * sv[th][i]
            pair.append(tuple(acc))
        out.add(_round_pair(*pair))
    return frozenset(out)
