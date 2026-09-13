"""R2b trajectory-level state steering probe — docs/96 사전등록의 기계 이행.

    python -m shepherd.scripts.r2b_steer_probe --smoke
    python -m shepherd.scripts.r2b_steer_probe --run --shard K --n-shards 8

**질문**: 성공 C trajectory 의 limiter 지령을 $t_rho$ 부터 제거하면, **반응형** 표적의
미래 상태가 원래 FIRE 시각 $t_F^C$ 에서 달라지고 그 결과 capture-ready 조건을 잃는가.
docs/95 §7.5 BRANCH 2 판정이 지정한 후속 카드 (geometry probe 와 **다른 질문** — 그쪽은
같은 state 에서 limiter **위치**가 순간 viability 를 바꾸는지를 물었다).

**지위**: descriptive causal-suffix analysis. CI·가설검정 없음. **necessity 아님**
(재최적화 없음). B0 v3 (`5e7b5b486b9d8a4a`) 불변.

개입 (docs/96 §2b) — `plan` 배열은 **불변**이고 policy 만 감싼다:

    W_rho        : 호출 인덱스 i >= t_rho 에서 전 limiter 지령 가속도 0
    W_rho^(j)    : 같은 구간에서 limiter j 만 0

`t_rho = (n * fire_step) // d`, `(n,d) ∈ {(0,1),(1,4),(1,2),(3,4)}` — **정수 산술**
(float round 금지, off-by-one 자유도 0). withdrawal 은 **스텝 t_rho 의 지령에 이미
적용**되므로 원 plan 이 마지막으로 적용되는 스텝은 t_rho - 1 이고, 공유 prefix 는
**이동 전 상태 기준 t <= t_rho** 에서 bit-exact 여야 한다.

**어휘**: W_rho 는 zero-acceleration *command withdrawal* 이다. rho > 0 에서는
v_L(t_rho) != 0 이므로 limiter 가 **coast** 한다 — "세웠다 / 제거했다" 가 아니다.
**W_0 만이 legacy hold** 와 동치다.

**attacker 는 반드시 다시 전개된다** — reference 의 attacker state 를 복사해 쓰지
않는다. run_episode 가 매 스텝 현재 상태로 scripted A2 를 호출하므로 구조적으로 보장되고,
prefix parity 가 그 사실을 tick 단위로 검증한다.

표본 = geom_probe 140 판 (동일 표본이라야 세 진단이 같은 판 위에서 붙는다).
**search 비용 0** — plan 이 geom_probe shard 에 영속화돼 있다. torch-free.
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

from shepherd.m4_env import build_m4_env                               # noqa: E402
from shepherd.scripts.mission_rollout import run_episode               # noqa: E402
from shepherd.scripts.r2b_c_runner import (                           # noqa: E402
    ART2, B0_HASH, SEED0, _fresh, _plan_policy, scenario_kwargs)
from shepherd.scripts.r2b_phase1 import _cells, _slices                # noqa: E402

B0V3_HASH = json.loads(
    (ROOT / "artifacts/b0/b0_v3_world_contract.json").read_text(encoding="utf-8"))["b0_hash"]

GEOM_DIR = ART2 / "geom_probe"
OUT_DIR = ART2 / "steer_probe"
# docs/96 §3.1 — 정수 분기 격자. label 은 넷 다 유지한다 (t_rho 가 겹쳐도 dedupe 금지).
RHO_GRID = ((0, 1), (1, 4), (1, 2), (3, 4))
TAU0 = 6                      # q_dec = 1/6 -> 1 tick = xi 1/6 (docs/95 시간축)


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
    except Exception:                                      # pragma: no cover
        return "unknown"


def load_geom() -> dict:
    """geom_probe shard -> {s: record}. plan 이 여기 영속화돼 있어 search = 0."""
    out = {}
    for f in sorted(GEOM_DIR.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["b0_hash"] == B0_HASH, f"{f.name}: r2b b0 hash 불일치"
        for r in d["records"]:
            assert r["b0_v3_hash"] == B0V3_HASH, f"s={r['s']}: world hash 불일치"
            out[r["s"]] = r
    return out


def t_rho(fire: int, n: int, d: int) -> int:
    """docs/96 §3.1 정수 정의 — 부동소수 미개입."""
    return (n * fire) // d


def _withdraw_policy(env, plan, horizon: int, t_w: int, j=None):
    """원 plan policy 를 감싸 i >= t_w 에서 지령을 0 으로 만든다.

    내부 `_plan_policy` 를 **매 스텝 그대로 호출**하므로 (반환값만 덮어쓴다) 그 내부
    세그먼트 카운터가 reference 와 동일하게 전진한다 — prefix 가 구조적으로 bit-exact.
    zeros(4) 는 `agents/baselines.hold_position_limiter()` 와 같은 액션이므로
    t_w = 0 · j = None 이면 legacy hold 와 동치다 (GO 조건 ②).
    """
    inner = _plan_policy(env, plan, horizon)
    lim_ids = list(env.limiter_ids)
    zero = np.zeros(4, np.float32)
    t = {"i": -1}

    def policy(obs, flags):
        t["i"] += 1
        acts = dict(inner(obs, flags))
        if t["i"] >= t_w:
            if j is None:
                for lid in lim_ids:
                    acts[lid] = zero.copy()
            else:
                acts[lim_ids[j]] = zero.copy()
        return acts
    return policy


def _traj_replay_hold(st, s: int):
    """native `limiter_mode="hold"` 경로를 **같은 기록기**로 재생 (GO 조건 ② 전용).

    policy 를 주지 않는 legacy 경로 — limiter/finisher 를 모두 `scripted_role_actions`
    가 낸다. W_0 와 tick 단위로 일치해야 한다.
    """
    return _traj_replay(st, s, None, limiter_mode="hold")


def _traj_replay(st, s: int, policy, limiter_mode: str = "hold"):
    """policy 로 한 판 재생하며 **이동 전** 상태와 info 를 tick 마다 적재.

    `env.step` 을 기록 전용으로 wrap 한다 (r2b_geom_probe._logged_replay 선례 —
    호출 규약을 바꾸지 않으므로 bit-identical). `env._step_i` 는 orig 안에서 증가하므로
    wrap 진입 시점의 값이 run_episode 루프 인덱스 t 와 같다 (docs/96 §3.1).
    """
    env = st.env
    _fresh(env)
    ticks: list = []
    orig = env.step

    def step(*a, **k):
        lims, fin, att = env._states()
        rec = {"t": int(env._step_i),
               "p_att": env._p(att).tolist(), "v_att": env._v(att).tolist(),
               "p_lims": [env._p(x).tolist() for x in lims],
               "v_lims": [env._v(x).tolist() for x in lims]}
        out = orig(*a, **k)
        fi = out[4][env.finisher_id]
        rec["v_worst"] = float(fi["v_shot_worst"])
        rec["boxed"] = bool(fi["boxed_in"])
        rec["fire_event"] = bool(fi["fire_event"])
        ticks.append(rec)
        return out

    env.step = step
    try:
        if policy is None:                     # legacy 경로 (GO ② 비교 대상)
            r = run_episode(env, st.scn, st.lay, seed=SEED0 + s,
                            limiter_mode=limiter_mode, fire_mode="clean")
        else:
            r = run_episode(env, st.scn, st.lay, seed=SEED0 + s, policy=policy,
                            scripted_roles=("finisher",), fire_mode="clean")
    finally:
        env.step = orig
    return r, ticks


def _prefix_ok(ref: list, br: list, t_w: int) -> bool:
    """이동 전 상태 기준 t <= t_w 가 bit-exact 인가 (docs/96 GO 조건 ③)."""
    if len(br) <= min(t_w, len(ref) - 1):
        return False
    for t in range(min(t_w, len(ref) - 1) + 1):
        a, b = ref[t], br[t]
        for k in ("p_att", "v_att", "p_lims", "v_lims"):
            if np.asarray(a[k]).tolist() != np.asarray(b[k]).tolist():
                return False
    return True


def _delta(ref_tick: dict, br_tick: dict) -> dict:
    """원 FIRE 시각 t_F^C 에서의 상태 차이. **벡터와 norm 을 모두 보존**한다
    (새 estimand 가 아니라 이후 target-centered 시각화를 위한 원자료)."""
    dp = np.asarray(br_tick["p_att"]) - np.asarray(ref_tick["p_att"])
    dv = np.asarray(br_tick["v_att"]) - np.asarray(ref_tick["v_att"])
    a, b = np.asarray(ref_tick["v_att"]), np.asarray(br_tick["v_att"])
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    cos = float(np.dot(a, b) / (na * nb)) if na > 1e-12 and nb > 1e-12 else 1.0
    return {"dp_vec": dp.tolist(), "dp_norm": float(np.linalg.norm(dp)),
            "dv_vec": dv.tolist(), "dv_norm": float(np.linalg.norm(dv)),
            "dheading_rad": float(np.arccos(np.clip(cos, -1.0, 1.0))),
            "d_v_worst": br_tick["v_worst"] - ref_tick["v_worst"],
            "d_boxed": int(br_tick["boxed"]) - int(ref_tick["boxed"]),
            "ref": {k: ref_tick[k] for k in ("p_att", "v_att", "v_worst", "boxed")},
            "branch": {k: br_tick[k] for k in ("p_att", "v_att", "v_worst", "boxed")}}


def _category(label: str, reached_ref_fire: bool, br_ticks: list) -> tuple:
    """docs/96 §5 의 사전 정의 4 범주. P/T 는 결측이 아니라 **개입의 결과**다."""
    if reached_ref_fire:
        return ("S" if label == "NET_CAPTURE" else "L"), False
    return ("P" if label == "PENETRATED" else "T"), True


def _branch_record(ref, ref_ticks, st, s, plan, horizon, fire, n, d, j):
    t_w = t_rho(fire, n, d)
    r, ticks = _traj_replay(st, s, _withdraw_policy(st.env, plan, horizon, t_w, j))
    reached = len(ticks) > fire
    cat, pre_term = _category(r.label, reached, ticks)
    tw_ref, tw_br = ref_ticks[min(t_w, len(ref_ticks) - 1)], ticks[min(t_w, len(ticks) - 1)]
    end = ticks[fire] if reached else ticks[-1]
    lim_tw = np.asarray(tw_br["v_lims"])
    rec = {
        "rho": round(n / d, 4), "rho_frac": [n, d], "t_withdraw": t_w,
        "xi_withdraw": round((t_w - fire) / TAU0, 4),
        "limiter": j,                                  # None = full withdrawal
        "label": r.label, "branch_fire_step": r.fire_step, "steps": r.steps,
        "category": cat, "pre_reference_terminal": pre_term,
        "reached_ref_fire": reached,
        "prefix_parity_ok": _prefix_ok(ref_ticks, ticks, t_w),
        # coast 증거 — 이 수치 없이 withdrawal 결과를 해석하지 않는다 (docs/96 §2b)
        "speed_lim_at_tw": [float(np.linalg.norm(v)) for v in lim_tw],
        "coast_disp": [float(np.linalg.norm(np.asarray(end["p_lims"][i])
                                            - np.asarray(tw_br["p_lims"][i])))
                       for i in range(len(tw_br["p_lims"]))],
        "coast_eval_t": int(end["t"]),
        "p_lims_at_tw": tw_br["p_lims"], "v_lims_at_tw": tw_br["v_lims"],
        "p_lims_at_tw_ref": tw_ref["p_lims"],
    }
    rec["delta_at_ref_fire"] = _delta(ref_ticks[fire], ticks[fire]) if reached else None
    if pre_term:
        rec["terminal"] = {"label": r.label, "step": r.steps - 1,
                           "last_t": int(ticks[-1]["t"])}
    return rec


def probe_scenario(s: int, g: dict, cells: list, sls: dict) -> dict:
    """한 판: reference parity -> 4 rho x (full + 4 LOO) branch. search = 0."""
    sl, chi_c, eta_c, chi, eta, kw = scenario_kwargs(s, cells, sls)
    plan = np.asarray(g["plan"], float)
    ph = hashlib.sha256(plan.tobytes()).hexdigest()[:16]
    assert ph == g["plan_hash"], f"s={s}: plan hash 불일치 {ph} != {g['plan_hash']}"

    st = build_m4_env(SEED0, s, **kw)
    horizon = int(st.lay.episode_len)
    ref, ref_ticks = _traj_replay(st, s, _plan_policy(st.env, plan, horizon))
    # GO ① reference replay parity — 틀리면 이 판의 branch 전부 폐기
    parity = ((ref.label, ref.fire_step, ref.steps)
              == (g["label"], g["fire_step"], g["steps"]))
    if not parity:
        return {"s": s, "ref_parity_ok": False,
                "ref_got": [ref.label, ref.fire_step, ref.steps],
                "ref_expected": [g["label"], g["fire_step"], g["steps"]],
                "branches": [], "b0_v3_hash": B0V3_HASH, "r2b_b0_hash": B0_HASH}

    fire = int(ref.fire_step)
    cache: dict = {}
    branches = []
    for n, d in RHO_GRID:                      # t_rho 가 겹쳐도 **4 개 전부 기록**
        for j in (None, 0, 1, 2, 3):
            key = (t_rho(fire, n, d), j)
            if key not in cache:
                cache[key] = _branch_record(ref, ref_ticks, st, s, plan,
                                            horizon, fire, n, d, j)
            rec = dict(cache[key])             # 계산은 캐시, 레코드는 rho 별로 유지
            rec.update(rho=round(n / d, 4), rho_frac=[n, d])
            branches.append(rec)

    rt = ref_ticks[fire]
    return {
        "s": s, "slice": sl, "cell": [chi_c, eta_c], "chi": chi, "eta": eta,
        "dep": g["dep"], "ref_parity_ok": True,
        "ref": {"label": ref.label, "fire_step": fire, "steps": ref.steps,
                "authoritative_at_fire": bool((not rt["boxed"]) and rt["v_worst"] >= 1),
                "v_worst_at_fire": rt["v_worst"], "boxed_at_fire": rt["boxed"],
                "ticks": ref_ticks},          # reference 궤적만 전량 보존 (viz 원자료)
        "branches": branches,
        "plan_hash": g["plan_hash"], "plan_kind": g["plan_kind"],
        "code_commit": _commit(), "b0_v3_hash": B0V3_HASH, "r2b_b0_hash": B0_HASH,
    }


# ── smoke: docs/96 GO 조건 5 종 (결과 방향은 gate 가 아니다) ────────────────────
def smoke(s: int = 2001) -> None:
    cells, sls = _cells(), _slices()
    geom = load_geom()
    assert s in geom, f"s={s} 가 geom_probe 표본에 없다"
    print(f"[smoke] geom_probe sample = {len(geom)} · target s={s}")
    t0 = time.time()
    r = probe_scenario(s, geom[s], cells, sls)
    dt = time.time() - t0

    # ① reference replay parity
    assert r["ref_parity_ok"], f"GO1 FAIL: {r.get('ref_got')} != {r.get('ref_expected')}"
    fire = r["ref"]["fire_step"]
    print(f"[GO1] reference parity OK — label={r['ref']['label']} fire={fire} "
          f"steps={r['ref']['steps']} · plan_hash {r['plan_hash']}")

    # ② W_0 == legacy zero-acceleration hold — **tick 단위 bit-identical**
    sl, cc, ec, chi, eta, kw = scenario_kwargs(s, cells, sls)
    st = build_m4_env(SEED0, s, **kw)
    plan = np.asarray(geom[s]["plan"], float)
    horizon = int(st.lay.episode_len)
    r_w0, tk_w0 = _traj_replay(st, s, _withdraw_policy(st.env, plan, horizon, 0, None))
    r_hold, tk_hold = _traj_replay_hold(st, s)
    assert (r_w0.label, r_w0.fire_step, r_w0.steps) == \
        (r_hold.label, r_hold.fire_step, r_hold.steps), \
        f"GO2 FAIL (outcome): {(r_w0.label, r_w0.fire_step, r_w0.steps)} != " \
        f"{(r_hold.label, r_hold.fire_step, r_hold.steps)}"
    assert len(tk_w0) == len(tk_hold), f"GO2 FAIL: tick 수 {len(tk_w0)} != {len(tk_hold)}"
    for ta, tb in zip(tk_w0, tk_hold):
        for k in ("p_att", "v_att", "p_lims", "v_lims", "v_worst", "boxed"):
            assert ta[k] == tb[k], f"GO2 FAIL: t={ta['t']} 의 {k} 불일치"
    print(f"[GO2] W_0 == legacy hold, **bit-identical over {len(tk_w0)} ticks** — "
          f"{r_hold.label} fire={r_hold.fire_step} steps={r_hold.steps}")

    # ③ shared-prefix parity (전 branch)
    bad = [(b["rho"], b["limiter"]) for b in r["branches"] if not b["prefix_parity_ok"]]
    assert not bad, f"GO3 FAIL: prefix parity 깨진 branch {bad}"
    print(f"[GO3] shared-prefix bit-exact — {len(r['branches'])} branches")

    # ④ reference-clock integrity: branch FIRE 가 달라도 snapshot 은 t_F^C 에서
    diff = [(b["rho"], b["limiter"], b["branch_fire_step"]) for b in r["branches"]
            if b["branch_fire_step"] not in (None, fire)]
    for b in r["branches"]:
        if b["delta_at_ref_fire"] is not None:
            assert b["delta_at_ref_fire"]["ref"]["p_att"] == r["ref"]["ticks"][fire]["p_att"], \
                "GO4 FAIL: reference snapshot 이 t_F^C 가 아니다"
    print(f"[GO4] reference clock fixed at t_F^C={fire} — "
          f"branch FIRE 가 다른 경우 {len(diff)} 건 (기록만, 판정 미사용)")

    # ⑤ edge case + 결측/NaN
    tw = sorted({(b["rho"], b["t_withdraw"]) for b in r["branches"]})
    assert len(r["branches"]) == 20, f"GO5 FAIL: branch 수 {len(r['branches'])} != 20"
    assert len({b["rho"] for b in r["branches"]}) == 4, "GO5 FAIL: rho label 4 개 유지 실패"
    flat = json.dumps(r)
    assert "NaN" not in flat and "Infinity" not in flat, "GO5 FAIL: NaN/Inf 존재"
    print(f"[GO5] edge OK — t_withdraw by rho {tw} "
          f"(중복 tick 은 dedupe 하지 않고 label 4 개 유지)")

    cat = {}
    for b in r["branches"]:
        cat[b["category"]] = cat.get(b["category"], 0) + 1
    print(f"[smoke] {dt:.0f} s/scenario (21 replays) · outcome 분포 {cat} "
          f"— **방향은 GO 조건이 아니다** (docs/96 §3 GO 규율)")
    print("[smoke] ALL PASS (5/5)")


def run_shard(shard: int, n_shards: int = 8) -> None:
    from shepherd.notify import ntfy
    cells, sls = _cells(), _slices()
    geom = load_geom()
    scs = sorted(geom)
    lo, hi = shard * len(scs) // n_shards, (shard + 1) * len(scs) // n_shards
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"shard{shard:02d}.json"
    records = []
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev["b0_v3_hash"] == B0V3_HASH and prev["b0_hash"] == B0_HASH:
            records = prev["records"]

    def _save():
        path.write_text(json.dumps(
            {"shard": shard, "n_shards": n_shards, "sample_size": len(scs),
             "b0_hash": B0_HASH, "b0_v3_hash": B0V3_HASH, "doc": "docs/96",
             "rho_grid": [list(x) for x in RHO_GRID], "code_commit": _commit(),
             "records": records}, ensure_ascii=False), encoding="utf-8")

    t0 = time.time()
    for k in range(lo + len(records), hi):
        s = scs[k]
        records.append(probe_scenario(s, geom[s], cells, sls))
        _save()
        print(f"[steer shard {shard}] {len(records)}/{hi - lo}  "
              f"({(time.time() - t0) / len(records):.0f} s/scn)", flush=True)
    ntfy(f"r2b steer-probe shard {shard} done: {len(records)}/{hi - lo}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-s", type=int, default=2001)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    a = ap.parse_args()
    if a.smoke:
        smoke(a.smoke_s)
    if a.run:
        run_shard(a.shard, a.n_shards)


if __name__ == "__main__":
    main()
