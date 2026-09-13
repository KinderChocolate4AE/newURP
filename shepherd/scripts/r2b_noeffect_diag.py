"""99-X — `W_0.75` 가 왜 무효과가 되는가: **exploratory diagnostic** (재실행 0).

    python -m shepherd.scripts.r2b_noeffect_diag

**지위 — 명확히 해 둔다**: 이것은 **post-hoc diagnostic** 이며 **새 claim gate 가 아니다.**
사전등록도 새 분기표도 만들지 않는다. 목적은 단 하나 — docs/99 의 **주력 셀(ρ=0.75)이
왜 퇴화했는지 설명하는 것**. 여기서 나온 어떤 수치도 `96-BR1` · `98-B` · `99-P` 판정을
바꾸지 않는다.

배경: ρ=0.75 에서 AUTH-RETAINED 31 건 중 **21 건이 ‖Δp_A‖ < 1 mm** — 지령을 거뒀는데
표적이 1 mm 도 다르게 움직이지 않았다. 후보 설명 두 가지:

  (1) **interaction 이 이미 끊김** — t_w 에서 limiter 가 attacker 의 행동 반경 밖
      (`sense_range` = 30 m) 이라 존재하든 말든 반응이 같다.
  (2) **남은 control authority 가 작음** — 상수 가속도 plan 이라 t_w 까지 limiter 가 이미
      속도를 얻었고 남은 시간이 짧다. 지령을 끊어도 coast 궤적이 원 plan 과 거의 같다:

          Δv_L ≈ |a_L| Δt          Δp_L ≈ ½ |a_L| Δt²      (Δt = (t_F − t_w)·dt)

      위치 차이가 **남은 시간의 제곱**으로 줄므로 late withdrawal 이 no-op 이 되는 것은
      자연스럽다.

세 층으로 본다 — A 행동 반경 · B 남은 지령 권한 · C 실제 개입 흔적.
데이터는 전부 steer_probe / geom_probe 에 저장돼 있다. torch-free.
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.agents.attacker_ladder import _route_accel, _unit      # noqa: E402
from shepherd.m4_env import build_m4_env                             # noqa: E402
from shepherd.scripts.r2b_c_runner import SEED0, scenario_kwargs     # noqa: E402
from shepherd.scripts.r2b_phase1 import _cells, _slices              # noqa: E402
OUT = ROOT / "artifacts/r2b/noeffect_diag.json"
DT = 0.05                 # physics.dt
SENSE_RANGE = 30.0        # A2-nominal
RHO = 0.75
NULL_EFFECT = 1e-3        # ‖Δp_A‖ < 1 mm


def load():
    st, gm = {}, {}
    for f in sorted(glob.glob(str(ROOT / "artifacts/r2b/steer_probe/shard*.json"))):
        for r in json.loads(open(f, encoding="utf-8").read())["records"]:
            st[r["s"]] = r
    for f in sorted(glob.glob(str(ROOT / "artifacts/r2b/geom_probe/shard*.json"))):
        for r in json.loads(open(f, encoding="utf-8").read())["records"]:
            gm[r["s"]] = r
    return st, gm


def route_dir(spec, p_att, v_att, lims, kill_radius, a_lat_max, target):
    """A2 의 angular-gap 회피 지령 (`_route_accel` 그대로 호출 — 재구현 아님).

    env 배선: `repel_margin=1.0`, `a_lat_max` 미지정 -> `a_att_max` (env.py L344-349).
    """
    fwd = _unit(v_att)
    d_target = float(np.linalg.norm(np.asarray(target, float) - p_att))
    return _route_accel(spec, p_att=p_att, v_att=v_att, fwd=fwd, limiters=lims,
                        kill_radius=kill_radius, repel_margin=1.0,
                        a_lat_max=a_lat_max, d_target=d_target)


def layer_d(r, b, tw, ticks, env, spec):
    """[D] **첫 인과 차이**. 스텝 t_w 의 지령만 다르므로 t_w+1 에서 표적 상태는 아직
    동일하고 limiter 위치만 갈린다 -> 그 지점에서 A2 의 회피 지령을 양쪽으로 평가하면
    '같은 크기의 limiter 섭동이 왜 표적 반응을 400배 다르게 만드는가' 를 직접 본다."""
    t1 = tw + 1
    if t1 not in ticks:
        return None
    p_att = np.asarray(ticks[t1]["p_att"], float)
    v_att = np.asarray(ticks[t1]["v_att"], float)
    lim_ref = np.asarray(ticks[t1]["p_lims"], float)
    # branch: t_w 스텝에서 무지령 -> 등속 coast (coast 모델은 1e-14 로 검증됨)
    lim_br = (np.asarray(b["p_lims_at_tw"], float)
              + np.asarray(b["v_lims_at_tw"], float) * DT)
    kw = dict(kill_radius=env.kill_radius, a_lat_max=env.adv_a_max,
              target=env.layout.target)
    a_ref = route_dir(spec, p_att, v_att, list(lim_ref), **kw)
    a_br = route_dir(spec, p_att, v_att, list(lim_br), **kw)
    na, nb = float(np.linalg.norm(a_ref)), float(np.linalg.norm(a_br))
    ang = (float(np.arccos(np.clip(float(a_ref @ a_br) / (na * nb), -1.0, 1.0)))
           if na > 1e-12 and nb > 1e-12 else None)
    return {"lim_shift_at_t1": float(np.max(np.linalg.norm(lim_ref - lim_br, axis=1))),
            "a_route_ref": na, "a_route_branch": nb,
            "a_route_delta": float(np.linalg.norm(a_ref - a_br)),
            "route_angle_rad": ang,
            "route_off_both": bool(na < 1e-12 and nb < 1e-12)}


def diag(r, g, env=None, spec=None):
    """한 판의 W_0.75 full-withdrawal branch 에 대한 A/B/C 층."""
    b = next(x for x in r["branches"]
             if abs(x["rho"] - RHO) < 1e-9 and x["limiter"] is None)
    if not b["reached_ref_fire"]:
        return None
    tw, fire = b["t_withdraw"], r["ref"]["fire_step"]
    dt = (fire - tw) * DT
    ticks = {t["t"]: t for t in r["ref"]["ticks"]}
    p_att_tw = np.asarray(ticks[tw]["p_att"], float)
    p_lim_tw = np.asarray(b["p_lims_at_tw"], float)          # prefix 동일 = ref 와 같음
    v_lim_tw = np.asarray(b["v_lims_at_tw"], float)

    # ── A. behavioral reachability: t_w 에서 limiter 가 attacker 반응 반경 안인가 ──
    d = np.linalg.norm(p_lim_tw - p_att_tw[None, :], axis=1)

    # ── B. 남은 control authority: 상수 가속도 plan 의 segment 0 ────────────────
    a = np.asarray(g["plan"], float)[:, 0, :]                # (4,3) 실제 실행되는 성분
    an = np.linalg.norm(a, axis=1)
    dv_pred = an * dt                                        # |a| Δt
    dp_pred = 0.5 * an * dt * dt                             # ½ |a| Δt²

    # ── C. 실제 개입 흔적 ────────────────────────────────────────────────────
    # branch limiter 는 t_w 이후 무지령 -> 직선 coast. 저장된 coast_disp 와 대조해
    # 이중적분 모델이 맞는지 **자기검증**한다.
    coast_pred = np.linalg.norm(v_lim_tw, axis=1) * (b["coast_eval_t"] - tw) * DT
    coast_obs = np.asarray(b["coast_disp"], float)
    # t_F 에서 limiter 위치 차이 (ref 실측 vs branch coast 예측)
    p_lim_ref_fire = np.asarray(ticks[fire]["p_lims"], float)
    p_lim_branch_fire = p_lim_tw + v_lim_tw * dt
    lim_gap = np.linalg.norm(p_lim_ref_fire - p_lim_branch_fire, axis=1)

    dp_att = b["delta_at_ref_fire"]["dp_norm"]
    lost = b["delta_at_ref_fire"]["d_v_worst"] < 0
    d4 = layer_d(r, b, tw, ticks, env, spec) if env is not None else None
    return {
        "D": d4,
        "s": r["s"], "t_withdraw": tw, "fire_step": fire, "dt_remaining_s": dt,
        "group": "LOST" if lost else ("RET_noeffect" if dp_att < NULL_EFFECT
                                      else "RET_effect"),
        "dp_att": dp_att,
        # A
        "min_dist_lim_att_at_tw": float(d.min()),
        "n_within_sense_range": int((d <= SENSE_RANGE).sum()),
        # B
        "max_dv_pred": float(dv_pred.max()), "max_dp_pred": float(dp_pred.max()),
        "max_a_seg0": float(an.max()),
        # C
        "max_lim_gap_at_fire": float(lim_gap.max()),
        "coast_selfcheck_max_rel_err": float(
            np.max(np.abs(coast_obs - coast_pred) / np.maximum(coast_pred, 1e-9))),
    }


def q(v):
    a = np.asarray(v, float)
    return {"min": float(a.min()), "median": float(np.median(a)),
            "max": float(a.max())}


def main():
    st, gm = load()
    cells, sls = _cells(), _slices()
    recs = []
    for s, r in sorted(st.items()):
        if not (r["ref_parity_ok"] and r["dep"]["multi_dependent"]):
            continue
        kw = scenario_kwargs(s, cells, sls)[5]
        stk = build_m4_env(SEED0, s, **kw)          # rollout 없음 — 상수만 꺼낸다
        d = diag(r, gm[s], env=stk.env, spec=kw["attacker"])
        if d:
            recs.append(d)
    groups = {}
    for g in ("LOST", "RET_effect", "RET_noeffect"):
        sub = [d for d in recs if d["group"] == g]
        if not sub:
            continue
        groups[g] = {
            "n": len(sub),
            "A_min_dist_lim_att_at_tw_m": q([d["min_dist_lim_att_at_tw"] for d in sub]),
            "A_n_within_sense_range": q([d["n_within_sense_range"] for d in sub]),
            "A_all_four_inside": int(sum(d["n_within_sense_range"] == 4 for d in sub)),
            "B_dt_remaining_s": q([d["dt_remaining_s"] for d in sub]),
            "B_max_dv_pred_ms": q([d["max_dv_pred"] for d in sub]),
            "B_max_dp_pred_m": q([d["max_dp_pred"] for d in sub]),
            "C_max_lim_gap_at_fire_m": q([d["max_lim_gap_at_fire"] for d in sub]),
            "C_dp_att_m": q([d["dp_att"] for d in sub]),
            "D_lim_shift_at_t1_m": q([d["D"]["lim_shift_at_t1"] for d in sub if d["D"]]),
            "D_a_route_delta": q([d["D"]["a_route_delta"] for d in sub if d["D"]]),
            "D_route_angle_rad": q([d["D"]["route_angle_rad"] for d in sub
                                    if d["D"] and d["D"]["route_angle_rad"] is not None]),
            "D_n_route_off_both": int(sum(bool(d["D"] and d["D"]["route_off_both"])
                                          for d in sub)),
            # [E] 증폭률 = 실제 표적 변위 / 첫 지령 차이의 선형 예측 (½|da|dt²).
            # 1 근처 = 매끄러운 선형 반응. >>1 = 그 사이에 이산 전환이 일어났다.
            "E_linear_pred_dp_m": q([0.5 * d["D"]["a_route_delta"]
                                     * d["dt_remaining_s"] ** 2
                                     for d in sub if d["D"]]),
            "E_amplification": q([d["dp_att"] / max(0.5 * d["D"]["a_route_delta"]
                                                    * d["dt_remaining_s"] ** 2, 1e-12)
                                  for d in sub if d["D"]]),
        }
    sc = max(d["coast_selfcheck_max_rel_err"] for d in recs)
    out = {"doc": "99-X exploratory diagnostic (post-hoc, NOT a claim gate)",
           "purpose": "explain why the docs/99 primary cell (rho=0.75) degenerated",
           "rho": RHO, "sense_range_m": SENSE_RANGE, "dt_s": DT,
           "n_records": len(recs), "groups": groups,
           "coast_model_selfcheck_max_rel_err": sc,
           "records": recs}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"W_{RHO} · multi-dependent {len(recs)} 판 · sense_range {SENSE_RANGE} m")
    print(f"coast 이중적분 모델 자기검증: max rel err {sc:.2e}\n")
    for g, v in groups.items():
        print(f"[{g}] n={v['n']}")
        print(f"  A  min dist limiter-attacker @t_w : "
              f"med {v['A_min_dist_lim_att_at_tw_m']['median']:>6.2f} m "
              f"(min {v['A_min_dist_lim_att_at_tw_m']['min']:.2f}, "
              f"max {v['A_min_dist_lim_att_at_tw_m']['max']:.2f})   "
              f"4/4 within sense_range: {v['A_all_four_inside']}/{v['n']}")
        print(f"  B  remaining dt {v['B_dt_remaining_s']['median']:.3f} s  ->  "
              f"max |a|dt  med {v['B_max_dv_pred_ms']['median']:>6.3f} m/s   "
              f"max ½|a|dt² med {v['B_max_dp_pred_m']['median']:>7.4f} m")
        print(f"  C  limiter gap @fire med "
              f"{v['C_max_lim_gap_at_fire_m']['median']:>7.4f} m   "
              f"attacker dp med {v['C_dp_att_m']['median']:>8.5f} m")
        print(f"  D  @t_w+1 limiter shift med "
              f"{v['D_lim_shift_at_t1_m']['median']:>7.4f} m  ->  "
              f"A2 route |da| med {v['D_a_route_delta']['median']:>8.4f} m/s^2  "
              f"angle med {v['D_route_angle_rad']['median']:>7.4f} rad  "
              f"(route off in both: {v['D_n_route_off_both']}/{v['n']})")
        print(f"  E  linear prediction of dp med "
              f"{v['E_linear_pred_dp_m']['median']:.6f} m  vs actual "
              f"{v['C_dp_att_m']['median']:.6f} m  ->  "
              f"AMPLIFICATION med {v['E_amplification']['median']:>9.1f}x "
              f"(min {v['E_amplification']['min']:.1f}, "
              f"max {v['E_amplification']['max']:.0f})")


if __name__ == "__main__":
    main()
