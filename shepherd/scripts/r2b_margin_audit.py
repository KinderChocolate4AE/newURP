"""R2b capture-margin audit — docs/98 사전등록의 기계 이행.

    python -m shepherd.scripts.r2b_margin_audit --smoke
    python -m shepherd.scripts.r2b_margin_audit --run

**질문**: 성공한 FIRE state 들은 authoritative capture set 의 **내부에 넉넉히** 있는가,
아니면 실제 기하 **경계 근처에 몰려** 있는가.

발단: `2026-09-13d` 판독문이 "성공 plan 은 포획 경계에 걸쳐 있다" 고 적었는데 논리
오류였다 — `v_shot_worst` 는 이진 술어이고 성공이 그 술어로 **정의**되므로 46/46 이 1.0 인
것은 **동어반복**이다. 본 audit 은 여유를 **추론하지 않고 측정**한다.

지표 (docs/98 §2) — judge 는 `se3_cone`, 수용 영역은 원뿔 ∩ 축방향 밴드:

    r_j = y_j - apex ·  a_j = r_j·n̂ ·  α_j = arccos(a_j/|r_j|)
    m_lat_j = |r_j| · sin(θ_net − α_j)          (양수 = 원뿔 안쪽)
    m_ax_j  = min(a_j − range_min, range_max − a_j)
    s_j     = min(m_lat_j, m_ax_j)
    m_cap   = min over FEASIBLE witnesses of s_j

성분 (`lateral` / `axial`) 을 보존하고 **어느 제약이 binding 인지** 기록한다.

**predicate 재구현 금지**: net 파라미터는 `env._vshot_kwargs` 에서 그대로 받고, 매
witness 에서 `sign(s_j) >= 0 ⟺ union.caught[j]` 를 확인한다. 불일치 = margin 정의가
judge 와 갈라진 것이므로 **그 판 폐기**.

**유한 witness caveat (docs/98 §5)**: `v_shot_worst == 1` 은 "no **SAMPLED** witness
escapes" 이므로 표본 위 m_cap 은 참값을 **과대평가**한다 (min 을 부분집합에서 잡는다).
⇒ "여유가 작다" 는 안전, "여유가 크다" 는 **witness 증량 재확인 전까지 확정 금지**.

descriptive geometry read — 새 rollout·개입·world 없음. B0 v3 불변. torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.game import viability as V                              # noqa: E402
from shepherd.m4_env import build_m4_env                              # noqa: E402
from shepherd.provenance import stamp                                 # noqa: E402
from shepherd.scripts.mission_rollout import run_episode              # noqa: E402
from shepherd.scripts.r2b_c_runner import (                           # noqa: E402
    ART2, B0_HASH, SEED0, _fresh, _plan_policy, scenario_kwargs)
from shepherd.scripts.r2b_phase1 import _cells, _slices               # noqa: E402

B0V3_HASH = json.loads(
    (ROOT / "artifacts/b0/b0_v3_world_contract.json").read_text(encoding="utf-8"))["b0_hash"]
GEOM_DIR = ART2 / "geom_probe"
OUT = ART2 / "margin_audit.json"
SIGN_TOL = 1e-9


def load_geom() -> dict:
    out = {}
    for f in sorted(GEOM_DIR.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["b0_hash"] == B0_HASH
        for r in d["records"]:
            assert r["b0_v3_hash"] == B0V3_HASH
            out[r["s"]] = r
    return out


def _margins(endpoints, kw):
    """witness 별 (m_lat, m_ax, s). docs/98 §2 그대로 — judge 파라미터는 env 것."""
    apex = np.asarray(kw["net_apex"], float)
    n = np.asarray(kw["n_F"], float)
    n = n / (np.linalg.norm(n) or 1.0)
    r = np.asarray(endpoints, float) - apex[None, :]
    rn = np.linalg.norm(r, axis=1)
    a = r @ n
    cos = np.clip(np.where(rn < 1e-12, 1.0, a / (rn + 1e-12)), -1.0, 1.0)
    m_lat = rn * np.sin(float(kw["theta_net"]) - np.arccos(cos))
    lo = float(kw.get("range_min") or 0.0)
    hi = kw.get("range_max")
    m_ax = (a - lo) if hi is None or not np.isfinite(hi) else np.minimum(a - lo, float(hi) - a)
    return m_lat, m_ax, np.minimum(m_lat, m_ax)


def _block_ids(union):
    """witness index -> block id (0 = Block 1 uniform-in-ball, >0 = 결정론적 extreme)."""
    ids = np.concatenate([np.full(n, i, int) for i, n in enumerate(union.block_sizes)])
    assert len(ids) == union.n_total
    return ids


def audit_scenario(s: int, g: dict, cells, sls, boost=(1, 1)) -> dict:
    """`boost` = (n 배수, n_dir 배수). (1,1) = env 기본 = 봉인 지표.
    docs/98 §5 가 분기 B 에 대해 의무화한 **witness 증량 재확인** 용."""
    sl, chi_c, eta_c, chi, eta, kw_env = scenario_kwargs(s, cells, sls)
    plan = np.asarray(g["plan"], float)
    st = build_m4_env(SEED0, s, **kw_env)
    env = st.env
    fire = int(g["fire_step"])
    grab: dict = {}
    orig = env.step

    def step(*a, **k):
        if int(env._step_i) == fire:                    # 이동 전 = FIRE 판정 상태
            lims, fin, att = env._states()
            p_att, v_att = env._p(att), env._v(att)
            kwv = env._vshot_kwargs(p_att, v_att, fin)
            seed = env._seed * 100003 + (env._step_i + 1)
            union = V.build_reachable_union(
                p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
                n=env.n_samples * boost[0], n_segments=env.n_segments,
                seed=seed, n_dir=32 * boost[1], **kwv)
            lim_pos = [env._p(x) for x in lims]
            masks = [V._limiter_mask_from_paths(pb, lim_pos, env.kill_radius)
                     for pb in union.path_blocks]
            lim_feas = (np.concatenate(masks, axis=0) if masks
                        else np.ones(union.n_total, bool))
            grab.update(union=union, kwv=kwv,
                        feasible=lim_feas & union.turn_feasible)
        return orig(*a, **k)

    env.step = step
    _fresh(env)
    try:
        r = run_episode(env, st.scn, st.lay, seed=SEED0 + s,
                        policy=_plan_policy(env, plan, int(st.lay.episode_len)),
                        scripted_roles=("finisher",), fire_mode="clean")
    finally:
        env.step = orig

    if (r.label, r.fire_step, r.steps) != (g["label"], g["fire_step"], g["steps"]):
        return {"s": s, "ok": False, "why": "replay parity",
                "got": [r.label, r.fire_step, r.steps]}
    if "union" not in grab:
        return {"s": s, "ok": False, "why": "fire tick 미도달"}

    union, kwv, feas = grab["union"], grab["kwv"], grab["feasible"]
    m_lat, m_ax, sj = _margins(union.endpoints, kwv)
    caught = np.asarray(union.caught, bool)

    # ── 자기검증: 부호가 judge 의 caught 과 일치해야 한다 (재구현 아님의 증거) ──
    mism = int(np.sum((sj >= -SIGN_TOL) != caught))
    if mism:
        return {"s": s, "ok": False, "why": "sign/caught 불일치", "n_mismatch": mism}

    nf = int(feas.sum())
    if nf == 0:
        return {"s": s, "ok": False, "why": "boxed_in (feasible 0)"}

    idx = np.where(feas)[0]
    k = idx[int(np.argmin(sj[idx]))]                    # binding witness
    bid = _block_ids(union)[k]
    return {
        "s": s, "ok": True, "slice": sl, "cell": [chi_c, eta_c],
        "chi": chi, "eta": eta, "dep": g["dep"], "fire_step": fire,
        "n_total": int(union.n_total), "n_feasible": nf,
        "m_cap": float(sj[k]),
        "m_lateral_at_binding": float(m_lat[k]),
        "m_axial_at_binding": float(m_ax[k]),
        "binding": "lateral" if m_lat[k] <= m_ax[k] else "axial",
        "binding_block_id": int(bid),
        "binding_is_extreme_dir": bool(bid > 0),        # 분기 C 직접 증거
        "m_cap_q": [float(np.percentile(sj[idx], p)) for p in (0, 5, 25, 50)],
        "theta_net": float(kwv["theta_net"]),
        "range_band": [float(kwv.get("range_min") or 0.0),
                       (None if kwv.get("range_max") is None
                        else float(kwv["range_max"]))],
    }


def summarize(recs):
    ok = [r for r in recs if r["ok"]]
    multi = [r for r in ok if r["dep"]["multi_dependent"]]
    def q(v):
        a = np.asarray(v, float)
        return {"min": float(a.min()), "p5": float(np.percentile(a, 5)),
                "median": float(np.median(a)), "p95": float(np.percentile(a, 95)),
                "max": float(a.max())}
    out = {}
    for nm, g in (("multi_dependent", multi), ("all_ok", ok)):
        if not g:
            continue
        m = [r["m_cap"] for r in g]
        out[nm] = {
            "n": len(g), "m_cap_m": q(m),
            "n_negative": int(sum(x < 0 for x in m)),
            "binding": {b: sum(r["binding"] == b for r in g)
                        for b in ("lateral", "axial")},
            "binding_is_extreme_dir": int(sum(r["binding_is_extreme_dir"] for r in g)),
            "n_feasible": q([r["n_feasible"] for r in g]),
            "frac_below_1cm": float(np.mean([x < 0.01 for x in m])),
            "frac_below_10cm": float(np.mean([x < 0.10 for x in m])),
        }
    return out


def verdict(summ):
    """docs/98 §4 3-분기. 발명한 cutoff 없음 — A/B 는 '센티미터 급' 을 10 cm 로 읽고
    (지표 단위가 미터이므로 자연 경계), C 는 **정확한 집중**으로 판정한다."""
    m = summ["multi_dependent"]
    med, ext = m["m_cap_m"]["median"], m["binding_is_extreme_dir"] / m["n"]
    if m["frac_below_1cm"] > 0.5:
        return "BRANCH_C_SUSPECT", (
            f"binding margins pile up below 1 cm (median {med*100:.2f} cm, "
            f"{m['frac_below_1cm']:.0%} under 1 cm; binding witness is a deterministic "
            f"extreme direction in {ext:.0%}). Investigate judge finite-witness / "
            "discretization exploitation BEFORE any physical reading.")
    if m["frac_below_10cm"] > 0.5:
        return "BRANCH_A", (
            f"Successful FIRE states sit within centimetres of the authoritative "
            f"capture boundary (median m_cap {med*100:.2f} cm, "
            f"{m['frac_below_10cm']:.0%} under 10 cm). Because a sampled minimum "
            "OVERESTIMATES the true margin, this smallness is safe against the "
            "finite-witness bias. 'Precision capture-state threading' is licensed.")
    return "BRANCH_B", (
        f"Margins are comfortable (median m_cap {med*100:.1f} cm), so the withdrawal "
        "effect does not run through position alone -- velocity / heading changing the "
        "reachable set is the candidate. MANDATORY CAVEAT (docs/98 §5): a sampled "
        "minimum overestimates the true margin, so BRANCH_B is NOT confirmed until "
        "re-checked at higher witness count.")


def recheck(boost=(4, 2)):
    """docs/98 §5 의무 재확인 — witness 를 늘리면 m_cap 이 줄어드는가.

    표본 min 은 참값을 과대평가하므로, witness 를 늘려도 m_cap 이 버티면 그 여유는
    표본 인공물이 아니다. 크게 줄면 분기 B 는 기각된다.
    """
    cells, sls = _cells(), _slices()
    geom = load_geom()
    base = json.loads(OUT.read_text(encoding="utf-8"))
    was = {r["s"]: r["m_cap"] for r in base["records"] if r["ok"]
           and r["dep"]["multi_dependent"]}
    scs = sorted(was)
    print(f"recheck n x{boost[0]}, n_dir x{boost[1]} on {len(scs)} multi-dependent")
    now, t0 = {}, time.time()
    for i, s in enumerate(scs, 1):
        r = audit_scenario(s, geom[s], cells, sls, boost=boost)
        if not r["ok"]:
            print(f"  s={s} EXCLUDED {r['why']}")
            continue
        now[s] = r["m_cap"]
        if i % 10 == 0:
            print(f"  {i}/{len(scs)} ({(time.time()-t0)/i:.1f} s/scn)", flush=True)
    a = np.array([was[s] for s in now]); b = np.array([now[s] for s in now])
    out = {"boost": list(boost), "n": len(now),
           "m_cap_base": {"median": float(np.median(a)), "min": float(a.min())},
           "m_cap_boosted": {"median": float(np.median(b)), "min": float(b.min())},
           "ratio_median": float(np.median(b / np.maximum(a, 1e-12))),
           "n_shrunk_over_10pct": int(np.sum(b < 0.9 * a)),
           "frac_below_10cm_boosted": float(np.mean(b < 0.10))}
    base["recheck_witness_boost"] = out
    OUT.write_text(json.dumps(base, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  m_cap median {np.median(a)*100:.2f} cm -> {np.median(b)*100:.2f} cm "
          f"(ratio med {out['ratio_median']:.3f})")
    print(f"  min {a.min()*100:.2f} -> {b.min()*100:.2f} cm | "
          f"shrunk >10%: {out['n_shrunk_over_10pct']}/{len(now)} | "
          f"<10cm now {out['frac_below_10cm_boosted']:.0%}")
    return out


def run(scs=None):
    cells, sls = _cells(), _slices()
    geom = load_geom()
    scs = sorted(geom) if scs is None else scs
    t0 = time.time()
    recs = []
    for i, s in enumerate(scs, 1):
        recs.append(audit_scenario(s, geom[s], cells, sls))
        if i % 20 == 0:
            print(f"  {i}/{len(scs)}  ({(time.time()-t0)/i:.2f} s/scn)", flush=True)
    summ = summarize(recs)
    vkey, sentence = verdict(summ)
    out = {"doc": "docs/98", "b0_v3_hash": B0V3_HASH, "r2b_b0_hash": B0_HASH,
           "excluded": [{k: r[k] for k in r if k != "ok"}
                        for r in recs if not r["ok"]],
           "summary": summ, "verdict": {"branch": vkey, "sentence": sentence},
           "finite_witness_caveat": (
               "v_shot_worst == 1 means no SAMPLED witness escapes, so m_cap measured "
               "on the sample OVERESTIMATES the true margin. Small = safe; "
               "large = must be re-checked at higher witness count."),
           "records": recs, **stamp()}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\nok {len(recs)-len(out['excluded'])}/{len(recs)}  "
          f"excluded {out['excluded'][:3]}")
    for nm, v in summ.items():
        mc = v["m_cap_m"]
        print(f"  {nm}: n={v['n']}  m_cap [m] min {mc['min']:.4f} p5 {mc['p5']:.4f} "
              f"med {mc['median']:.4f} p95 {mc['p95']:.4f} max {mc['max']:.4f}")
        print(f"    <1cm {v['frac_below_1cm']:.0%}  <10cm {v['frac_below_10cm']:.0%}  "
              f"negative {v['n_negative']}  binding {v['binding']}  "
              f"extreme-dir {v['binding_is_extreme_dir']}/{v['n']}  "
              f"n_feasible med {v['n_feasible']['median']:.0f}")
    print(f"\n[{vkey}] {sentence}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--recheck", action="store_true")
    a = ap.parse_args()
    if a.smoke:
        geom = load_geom()
        run(sorted(geom)[:3])
    if a.run:
        run()
    if a.recheck:
        recheck()


if __name__ == "__main__":
    main()
