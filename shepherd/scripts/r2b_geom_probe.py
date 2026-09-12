"""R2b cooperative geometry probe (docs/95 사전등록 이행).

    python -m shepherd.scripts.r2b_geom_probe --smoke              # 배선 + parity 검증
    python -m shepherd.scripts.r2b_geom_probe --run --shard K --n-shards 8

**지위 (봉인 선언, docs/95)**: frozen artifact 에 대한 **retrospective mechanism
analysis**. 새 world 도 새 campaign 도 아니다 (B0 v3 5e7b5b486b9d8a4a 불변).
descriptive — CI·가설검정 규칙 없음. **necessity 아님** (재최적화 없음).

질문: **C 가 성공하기 직전, hold 대비 어떤 escape direction 이 사라졌고 거기에 몇 대의
limiter 가 동시에 기여했는가.**

봉인 가설 3개만 측정한다 (신규 지표 fishing 금지):
  H1  dG_close(t) = p_blocked^full - p_blocked^hold      (raw p_blocked 아님!)
  H2  dV(t)       = v_shot_soft^full - v_shot_soft^hold  (proxy — authoritative 는
                    FIRE 시점 동결 `not boxed_in and v_shot_worst >= 1`)
  H3  D_i(t)      = V_full - V_{-i}  (`coma_D`, 동일 accel 표본)
      -- `dV - sum_i D_i` 는 **non-additivity diagnostic** 까지만. "synergy"/Shapley 금지.

구현 규약: rollout 은 건드리지 않는다. `env.step` 을 **기록 전용으로 wrap** 해
이동 **전** 상태에서 hold 반사실을 env 와 **같은 step_seed** 로 재구성하고, env 가 이미
info 로 주는 dV(`delta_v_shot_headline`)·D_i(`coma_D`)·p_blocked·v_shot_worst 를 받는다.
**PARITY SELF-CHECK**: 재구성한 full 쪽 (dV, p_blocked) 이 env 값과 일치해야 그 판을
채택한다 -- 이것이 hold 쪽 수치의 신뢰 근거다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.game import viability as V                               # noqa: E402
from shepherd.m4_env import build_m4_env                               # noqa: E402
from shepherd.scripts.mission_rollout import run_episode               # noqa: E402
from shepherd.scripts.r2b_c_dep_probe import sample                    # noqa: E402
from shepherd.scripts.r2b_c_runner import (                            # noqa: E402
    ART2, B0_HASH, BRANCH_HASH, SEED0, SOLVER_NS, SOLVER_SEEDS, _fresh,
    _plan_policy, search_plan)
from shepherd.scripts.r2b_phase1 import _cells, _slices                # noqa: E402

B0V3_HASH = json.loads(
    (ROOT / "artifacts/b0/b0_v3_world_contract.json").read_text(encoding="utf-8"))["b0_hash"]


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
    except Exception:                                      # pragma: no cover
        return "unknown"


OUT_DIR = ART2 / "geom_probe"
DEP_DIR = ART2 / "c_dep_probe"
PARITY_TOL = 1e-12          # 반사실 재구성은 **정확히** 같아야 한다 (같은 seed·같은 경로)
D_TOL = 1e-12               # [r1] n_plus 규약: 이하는 0 으로 처리
XI_SNAPSHOTS = (-1.0, -0.5, 0.0)      # [r1] 고정 snapshot (q_dec=1/6 -> fire-6, -3, 0)
N_THETA, N_PHI = 6, 12                # [r1] (theta, phi) 히스토그램 격자


def dep_labels() -> dict:
    """dep-probe 판정을 s 로 조인 (docs/95 §5 figure 4 의 사전등록 층화 축).

    없으면 빈 dict — probe 는 그대로 돌고 readout 에서 층화만 빠진다.
    """
    out = {}
    for f in sorted(DEP_DIR.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for r in d["records"]:
            out[r["s"]] = {"multi_dependent": r["multi_dependent"],
                           "solo_any": r["solo_any"], "loo_all": r["loo_all"],
                           "n_solo_success": r["n_solo_success"]}
    return out


def _frame(e_net, v_att) -> np.ndarray:
    """[r1] target-centered frame: e1 = capture axis · e2 = v_att 의 e1-직교 성분 · e3."""
    e1 = np.asarray(e_net, float)
    e1 = e1 / (np.linalg.norm(e1) or 1.0)
    w = np.asarray(v_att, float) - float(np.dot(v_att, e1)) * e1
    nw = np.linalg.norm(w)
    if nw < 1e-9:                                  # v_att ∥ e1 -> 임의 직교축
        w = np.cross(e1, [0.0, 0.0, 1.0])
        nw = np.linalg.norm(w) or 1.0
        if nw < 1e-9:
            w, nw = np.cross(e1, [0.0, 1.0, 0.0]), 1.0
    e2 = w / nw
    return np.stack([e1, e2, np.cross(e1, e2)])


def _counterfactual(env, p_att, v_att, lim_pos, fin, seed: int) -> tuple:
    """env.step L240-258 과 동일 경로로 full / all-hold 를 **한 표본에서** 평가.

    [r1] per-witness limiter-feasible mask 도 함께 낸다 (directional closure):
      M_close = T ∧ LF_hold ∧ ¬LF_full   /   M_open = T ∧ ¬LF_hold ∧ LF_full
    항등식 (N_close − N_open)/N_total == dG_close 가 매 틱 성립해야 한다.
    """
    assert env.n_segments > 1, "campaign world 는 union 경로 (n_segments=4)"
    hold_pos = [np.asarray(c, float) for c in env.layout.limiter_p0]
    union = V.build_reachable_union(
        p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
        n=env.n_samples, n_segments=env.n_segments, seed=seed,
        **env._vshot_kwargs(p_att, v_att, fin))
    res = V.eval_union_with_limiter_sets(union, [lim_pos, hold_pos], env.kill_radius)

    def _lf(layout):
        return np.concatenate([V._limiter_mask_from_paths(pb, layout, env.kill_radius)
                               for pb in union.path_blocks])
    lf_full, lf_hold, T = _lf(lim_pos), _lf(hold_pos), union.turn_feasible
    m_close = T & lf_hold & ~lf_full
    m_open = T & ~lf_hold & lf_full
    return res[0], res[1], union, m_close, m_open


def _logged_replay(st, s: int, plan) -> tuple:
    """봉인 plan 을 replay 하며 tick 기록. `_rollout` 과 **같은 호출 규약** (bit-identical)."""
    env = st.env
    _fresh(env)
    ticks: list = []
    snaps: list = []
    orig = env.step

    def step(*a, **k):
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        lim_pos = [env._p(x) for x in lims]
        seed = env._seed * 100003 + (env._step_i + 1)      # env 의 step_seed 와 동일
        full, hold, union, m_close, m_open = _counterfactual(
            env, p_att, v_att, lim_pos, fin, seed)

        out = orig(*a, **k)
        fi = out[4][env.finisher_id]
        # --- PARITY: 재구성한 full 이 env 의 것과 같아야 한다 -------------------
        dV_mine = float(full.v_shot_soft - hold.v_shot_soft)
        dG = float(full.p_limiter_blocked - hold.p_limiter_blocked)
        n_cl, n_op, n_tot = int(m_close.sum()), int(m_open.sum()), int(union.n_total)
        # [r1] GO 조건 5 — scalar 와 directional 분해의 항등식
        ident_ok = abs((n_cl - n_op) / n_tot - dG) <= 1e-12
        ok = (abs(dV_mine - float(fi["delta_v_shot_headline"])) <= PARITY_TOL
              and abs(float(full.p_limiter_blocked) - float(fi["p_limiter_blocked"])) <= PARITY_TOL
              and abs(float(full.v_shot_soft) - float(fi["v_shot_soft"])) <= PARITY_TOL
              and ident_ok)
        dcost = [float(out[4][lid]["coma_D"]) for lid in env.limiter_ids]
        ticks.append({
            "t": env._step_i - 1,
            "parity": bool(ok),
            # H1 — escape-channel closure (hold 반사실 차분; raw 아님)
            "p_blocked_full": float(full.p_limiter_blocked),
            "p_blocked_hold": float(hold.p_limiter_blocked),
            "dG_close": dG,
            "n_close": n_cl, "n_open": n_op, "n_total": n_tot,
            # [r1.1] H1 채널의 **활성 여부** 판별용 validity 스칼라 (양의 H1 을 만들 수
            # 없고, null 을 "측정된 0" vs "구조적 0" 으로 구분만 한다)
            "min_dist_att_lim": float(min(
                np.linalg.norm(np.asarray(c, float) - p_att) for c in lim_pos)),
            "max_lim_disp": float(max(
                np.linalg.norm(np.asarray(c, float) - np.asarray(q, float))
                for c, q in zip(lim_pos, env.layout.limiter_p0))),
            "kill_radius": float(env.kill_radius),
            "identity_ok": bool(ident_ok),
            # H2 — capturability uplift (+ authoritative predicate 동반)
            "v_soft_full": float(full.v_shot_soft),
            "v_soft_hold": float(hold.v_shot_soft),
            "dV": dV_mine,
            "v_worst_full": float(full.v_shot_worst),
            "v_worst_hold": float(hold.v_shot_worst),
            "boxed_full": bool(full.boxed_in),
            "boxed_hold": bool(hold.boxed_in),
            # H3 — per-limiter marginal (env 의 CRN 공유 counterfactual)
            "coma_D": dcost,
            "n_plus": int(sum(1 for d in dcost if d > D_TOL)),     # [r1] tol 명시
            "fire_event": bool(fi["fire_event"]),
            # 기하 그림용 (figure 2) — 이동 전 좌표
            "p_att": [float(x) for x in p_att],
            "v_att": [float(x) for x in v_att],
            "p_lims": [[float(x) for x in c] for c in lim_pos],
            "p_fin": [float(x) for x in env._p(fin)],
            "e_fin": [float(x) for x in env._e(fin)],
        })
        # snapshot 용 원자료는 에피소드 끝에 3틱만 히스토그램으로 남기고 버린다
        snaps.append((np.asarray(p_att, float), np.asarray(v_att, float),
                      np.asarray(env._e(fin), float), union.endpoints, m_close, m_open,
                      union.turn_feasible))
        return out

    env.step = step
    try:
        r = run_episode(env, st.scn, st.lay, seed=SEED0 + s,
                        policy=_plan_policy(env, plan, int(st.lay.episode_len)),
                        scripted_roles=("finisher",), fire_mode="clean")
    finally:
        env.step = orig
    return r, ticks, snaps


def _angular(snap, fire: int, t: int) -> dict:
    """[r1] 한 snapshot 의 (theta, phi) 히스토그램. theta = e1 로부터의 극각."""
    p_att, v_att, e_net, ends, m_close, m_open, T = snap
    F = _frame(e_net, v_att)
    d = np.asarray(ends, float) - p_att[None, :]
    nrm = np.linalg.norm(d, axis=1)
    d = d / np.where(nrm[:, None] > 1e-12, nrm[:, None], 1.0)
    c = d @ F.T                                            # (N,3) in (e1,e2,e3)
    theta = np.arccos(np.clip(c[:, 0], -1.0, 1.0))
    phi = np.arctan2(c[:, 2], c[:, 1])
    ti = np.clip((theta / np.pi * N_THETA).astype(int), 0, N_THETA - 1)
    pi_ = np.clip(((phi + np.pi) / (2 * np.pi) * N_PHI).astype(int), 0, N_PHI - 1)
    flat = ti * N_PHI + pi_

    def _h(mask):
        return np.bincount(flat[mask], minlength=N_THETA * N_PHI).tolist()
    return {"t": t, "xi": round((t - fire) / 6.0, 4),
            "n_theta": N_THETA, "n_phi": N_PHI,
            "h_close": _h(m_close), "h_open": _h(m_open), "h_denom": _h(T),
            "frame_e_net": [float(x) for x in F[0]], "p_att": [float(x) for x in p_att]}


def probe_scenario(s: int, rec: dict, cells: list, sls: dict, dep: dict | None = None) -> dict:
    meta, best_plan, _score, _n = search_plan(s, cells, sls)
    assert best_plan[0] == "accels", f"s={s}: 재현 plan 이 accels 아님 ({best_plan[0]})"
    kw, plan = meta[5], best_plan[1]

    r, ticks, snaps = _logged_replay(build_m4_env(SEED0, s, **kw), s, plan)
    # replay-parity gate (dep-probe 승계)
    assert (r.label, r.fire_step, r.steps) == (rec["label"], rec["fire_step"], rec["steps"]), \
        f"replay parity FAIL s={s}: {(r.label, r.fire_step, r.steps)}"
    bad = [t["t"] for t in ticks if not t["parity"]]
    fire = r.fire_step
    ang = [_angular(snaps[t], fire, t)
           for t in (int(fire + xi * 6) for xi in XI_SNAPSHOTS)
           if fire is not None and 0 <= t < len(snaps)]
    plan_arr = np.asarray(plan, float)
    return {
        "s": s, "slice": rec["slice"], "cell": rec["cell"],
        "chi": rec["chi"], "eta": rec["eta"],
        "label": r.label, "fire_step": r.fire_step, "steps": r.steps,
        "cf_parity_ok": not bad, "cf_parity_bad_ticks": bad,
        "dep": (dep or {}).get(s),                    # dep-probe 층화 라벨 (조인)
        "angular": ang,                               # [r1] xi = -1.0 / -0.5 / 0
        # ★ docs/95 r1: 영속화 필드 (다음 분석은 search=0, replay only)
        "plan": plan_arr.tolist(), "plan_kind": "accels",
        "plan_hash": hashlib.sha256(plan_arr.tobytes()).hexdigest()[:16],
        "solver_ns": SOLVER_NS, "solver_seeds": list(SOLVER_SEEDS),
        "code_commit": _commit(), "b0_v3_hash": B0V3_HASH, "r2b_b0_hash": B0_HASH,
        "telemetry_hash": hashlib.sha256(
            json.dumps(ticks, sort_keys=True).encode()).hexdigest()[:16],
        "ticks": ticks,
    }


def run_shard(shard: int, n_shards: int = 8) -> None:
    """dep-probe 와 동일한 서버 규약: 연속 샤드 · incremental 저장 · resume · ntfy."""
    from shepherd.notify import ntfy
    cells, sls = _cells(), _slices()
    scs, recs = sample()
    dep = dep_labels()
    lo, hi = shard * len(scs) // n_shards, (shard + 1) * len(scs) // n_shards
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"shard{shard:02d}.json"
    records = []
    if path.exists():                                   # resume (같은 계약일 때만)
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev["b0_hash"] == B0_HASH and prev.get("b0_v3_hash") == B0V3_HASH:
            records = prev["records"]

    def _save():
        path.write_text(json.dumps(
            {"shard": shard, "n_shards": n_shards, "sample_size": len(scs),
             "b0_hash": B0_HASH, "branch_hash": BRANCH_HASH, "b0_v3_hash": B0V3_HASH,
             "code_commit": _commit(), "prereg": "docs/95 r1",
             "hypotheses": "H1 dG_close (+directional mask) / H2 dV (+authoritative "
                           "v_worst) / H3 coma_D, n_plus",
             "records": records}, ensure_ascii=False), encoding="utf-8")

    t0 = time.time()
    for k in range(lo + len(records), hi):
        s = scs[k]
        records.append(probe_scenario(s, recs[s], cells, sls, dep))
        _save()                                          # incremental (중단 복구)
        bad = [r["s"] for r in records if not r["cf_parity_ok"]]
        print(f"[geom shard {shard}] {len(records)}/{hi - lo} s={s} "
              f"parity_bad={len(bad)} "
              f"({(time.time() - t0) / len(records):.0f} s/scn)", flush=True)
    ntfy(f"r2b geom-probe shard {shard} done: {len(records)}/{hi - lo}")


def _angular(snap, fire: int, t: int) -> dict:
    """[r1] 한 snapshot 의 (theta, phi) 히스토그램. theta = e1 로부터의 극각."""
    p_att, v_att, e_net, ends, m_close, m_open, T = snap
    F = _frame(e_net, v_att)
    d = np.asarray(ends, float) - p_att[None, :]
    nrm = np.linalg.norm(d, axis=1)
    d = d / np.where(nrm[:, None] > 1e-12, nrm[:, None], 1.0)
    c = d @ F.T                                            # (N,3) in (e1,e2,e3)
    theta = np.arccos(np.clip(c[:, 0], -1.0, 1.0))
    phi = np.arctan2(c[:, 2], c[:, 1])
    ti = np.clip((theta / np.pi * N_THETA).astype(int), 0, N_THETA - 1)
    pi_ = np.clip(((phi + np.pi) / (2 * np.pi) * N_PHI).astype(int), 0, N_PHI - 1)
    flat = ti * N_PHI + pi_

    def _h(mask):
        return np.bincount(flat[mask], minlength=N_THETA * N_PHI).tolist()
    return {"t": t, "xi": round((t - fire) / 6.0, 4),
            "n_theta": N_THETA, "n_phi": N_PHI,
            "h_close": _h(m_close), "h_open": _h(m_open), "h_denom": _h(T),
            "frame_e_net": [float(x) for x in F[0]], "p_att": [float(x) for x in p_att]}


def probe_scenario(s: int, rec: dict, cells: list, sls: dict, dep: dict | None = None) -> dict:
    meta, best_plan, _score, _n = search_plan(s, cells, sls)
    assert best_plan[0] == "accels", f"s={s}: 재현 plan 이 accels 아님 ({best_plan[0]})"
    kw, plan = meta[5], best_plan[1]

    r, ticks, snaps = _logged_replay(build_m4_env(SEED0, s, **kw), s, plan)
    # replay-parity gate (dep-probe 승계)
    assert (r.label, r.fire_step, r.steps) == (rec["label"], rec["fire_step"], rec["steps"]), \
        f"replay parity FAIL s={s}: {(r.label, r.fire_step, r.steps)}"
    bad = [t["t"] for t in ticks if not t["parity"]]
    fire = r.fire_step
    ang = [_angular(snaps[t], fire, t)
           for t in (int(fire + xi * 6) for xi in XI_SNAPSHOTS)
           if fire is not None and 0 <= t < len(snaps)]
    plan_arr = np.asarray(plan, float)
    return {
        "s": s, "slice": rec["slice"], "cell": rec["cell"],
        "chi": rec["chi"], "eta": rec["eta"],
        "label": r.label, "fire_step": r.fire_step, "steps": r.steps,
        "cf_parity_ok": not bad, "cf_parity_bad_ticks": bad,
        "dep": (dep or {}).get(s),                    # dep-probe 층화 라벨 (조인)
        "angular": ang,                               # [r1] xi = -1.0 / -0.5 / 0
        # ★ docs/95 r1: 영속화 필드 (다음 분석은 search=0, replay only)
        "plan": plan_arr.tolist(), "plan_kind": "accels",
        "plan_hash": hashlib.sha256(plan_arr.tobytes()).hexdigest()[:16],
        "solver_ns": SOLVER_NS, "solver_seeds": list(SOLVER_SEEDS),
        "code_commit": _commit(), "b0_v3_hash": B0V3_HASH, "r2b_b0_hash": B0_HASH,
        "telemetry_hash": hashlib.sha256(
            json.dumps(ticks, sort_keys=True).encode()).hexdigest()[:16],
        "ticks": ticks,
    }


def run_shard(shard: int, n_shards: int = 8) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cells, sls = _cells(), _slices()
    ss, recs = sample()
    dep = dep_labels()
    mine = [s for i, s in enumerate(ss) if i % n_shards == shard]
    out, t0 = [], time.time()
    for i, s in enumerate(mine):
        out.append(probe_scenario(s, recs[s], cells, sls, dep))
        print(f"[{shard}] {i + 1}/{len(mine)} s={s} "
              f"parity={'ok' if out[-1]['cf_parity_ok'] else 'BAD'} "
              f"({time.time() - t0:.0f}s)", flush=True)
    p = OUT_DIR / f"shard{shard:02d}.json"
    p.write_text(json.dumps(
        {"shard": shard, "n_shards": n_shards, "sample_size": len(ss),
         "b0_hash": B0_HASH, "branch_hash": BRANCH_HASH,
         "hypotheses": "docs/95 H1 dG_close / H2 dV (+authoritative v_worst) / H3 coma_D",
         "records": out}, ensure_ascii=False), encoding="utf-8")
    print(f"[{shard}] wrote {p} ({len(out)} scenarios)")


def smoke(pick: int | None = None) -> None:
    cells, sls = _cells(), _slices()
    ss, recs = sample()
    dep = dep_labels()
    s = ss[0] if pick is None else pick
    print(f"smoke: sample={len(ss)} scenarios, probing s={s} dep={dep.get(s)}")
    r = probe_scenario(s, recs[s], cells, sls, dep)
    tk = r["ticks"]
    fire = r["fire_step"]
    print(f"  label={r['label']} fire_step={fire} steps={r['steps']} ticks={len(tk)}")
    print(f"  counterfactual parity: {'ALL OK' if r['cf_parity_ok'] else r['cf_parity_bad_ticks']}")
    ang = r["angular"]
    print(f"  angular snapshots: {[a['xi'] for a in ang]} "
          f"denom={[sum(a['h_denom']) for a in ang]} "
          f"close={[sum(a['h_close']) for a in ang]} open={[sum(a['h_open']) for a in ang]}")
    print(f"  n_plus (pre-fire): {[t['n_plus'] for t in r['ticks'][:r['fire_step'] + 1]][-6:]}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sp = OUT_DIR / f"smoke_s{s}.json"
    sp.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    print(f"  saved {sp}")
    print(f"  {'t':>3} {'xi':>6} {'dG_close':>9} {'dV':>9} {'v_worst':>8} {'sum D_i':>8}")
    for t in tk[max(0, fire - 4):fire + 2]:
        xi = (t["t"] - fire) / 6.0                     # q_dec = 1/6 -> 1 tick = xi 1/6
        print(f"  {t['t']:>3} {xi:>6.2f} {t['dG_close']:>9.4f} {t['dV']:>9.4f} "
              f"{t['v_worst_full']:>8.3f} {sum(t['coma_D']):>8.4f}"
              + ("   <- FIRE" if t["fire_event"] else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--s", type=int, default=None, help="smoke 대상 시나리오")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    a = ap.parse_args()
    if a.smoke:
        smoke(a.s)
    elif a.run:
        run_shard(a.shard, a.n_shards)
    else:
        ap.error("--smoke 또는 --run 중 하나")


if __name__ == "__main__":
    main()
