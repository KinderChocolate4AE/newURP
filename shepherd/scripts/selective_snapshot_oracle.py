"""단계 2b — 선택적 snapshot coverage **witness search** (docs/52 §8.2).

푸는 문제
--------
후보 발사 시각 T 에서 네 limiter 를 **각자의 도달가능집합 안 정적 위치**에
배치해 (docs/52 §5.3 env-faithful)

    ∀ b ∈ B :  ∃i  c_i 가 b 를 제거      (모든 bad 를 덮는다)
    ∃ g ∈ G :  ∀i  c_i 가 g 를 안 건드림  (good 을 하나 남긴다)

를 만족하는 배치가 **존재하는지 찾는다.** 2a 는 `∀b ∃c` 였고 이건 `∃c ∀b` 다 --
개별 가능한 위치들이 서로 다른 곳일 수 있으므로 2a 통과율이 높아도 2b 는
거의 0 일 수 있다 (docs/52 §4.5).

★ 잠근 계약 넷
--------------
A. **B/G 는 limiter 적용 *전* union 에서 뽑는다.** `_union_sets(limiters=None)`
   로 물리적으로 가능한 전체 탈출집합을 받고, endpoint 가 원뿔 안이면 good,
   밖이면 bad. 현재 `hold` limiter 가 이미 제거한 표본을 빼고 시작하면
   오라클이 **부당하게 쉬워진다.**
B. **네 limiter 전부에 위치를 배정한다.** env 에는 limiter 가 항상 4 기 있고,
   "안 쓰는" 기체도 우연히 good 을 제거할 수 있다. 그래서 각 limiter 후보군에
   **safe parking 후보**(보호 good 을 안 건드리는 위치)를 반드시 넣는다.
C. **후보는 endpoint 가 아니라 union path 에서 만든다.** hit 판정이 경로 전체에
   걸리므로(`path_len` 까지만 사용) 후보 생성도 경로 기반이어야 한다.
D. **good 보호는 hard constraint.** g* 를 제거하는 후보를 **후보 집합에서
   삭제**한 뒤 bad 덮기를 푼다. 가중합 벌점으로 두면 boxed-in 쪽으로 미끄러진다.

★ 지위 제한
-----------
witness 를 **못 찾은 것은 불가능이 아니다** (docs/52 §8.2). 실패 원인은
(1) 실제 coverage 부족 (2) 후보·탐색기 한계 (3) hold 궤적 한계 — 안 갈린다.

torch-free.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
from typing import Dict, List, Optional

import numpy as np

import shepherd.game.viability as V
from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env, regime_of
from shepherd.scripts.contact_reachability import reach_radius
from shepherd.spawn_rand import SpawnSpec

__all__ = ["snapshot_witness", "audit"]

N_CAND = 160          # limiter 당 후보 (경로 투영 + 준무작위 + safe parking)
N_GOOD_TRY = 4        # 보호 good 후보 수
N_BEAM = 4            # beam search 폭
# ★ 탐색은 **축소 표본**에서 하고 판정은 **정확 replay** 로 한다.
#   전체 bad(~2000) x 경로점(96) x 후보(160) x limiter(4) 를 매 시각 도는 것은
#   비현실적이다. 축소가 witness 를 놓칠 수는 있어도 **가짜 witness 를 만들지는
#   않는다** -- 최종 판정이 `env._vshot` 이기 때문이다 (docs/52 §8.2 지위 제한에
#   "탐색기 한계" 항목이 이미 들어 있다).
SEARCH_BAD = 400      # 탐색용 bad 부표본
SEARCH_STEP = 4       # 경로점 간격 (판정은 전체 경로로)


def _kw() -> dict:
    return dict(system=SystemSpec(), reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def _min_dist(paths, path_len, pts, chunk: int = 48):
    """(n_pts, n_paths) 최소거리. `path_len` 까지만 -- 패딩은 마지막점 반복이라
    최소값에 영향은 없지만 계약대로 명시한다 (P75b)."""
    out = np.empty((len(pts), len(paths)), np.float32)
    for a in range(0, len(pts), chunk):
        b = min(a + chunk, len(pts))
        d = np.linalg.norm(paths[None, :, :, :] - pts[a:b, None, None, :], axis=3)
        out[a:b] = d.min(axis=2)
    return out


def _candidates(center, radius, bad_paths, bad_len, rng, n=N_CAND):
    """계약 C -- **경로**에서 만든다. 절반은 bad 경로점의 구 투영, 나머지 준무작위."""
    center = np.asarray(center, float)
    pts = []
    flat = bad_paths.reshape(-1, 3)
    if len(flat):
        idx = rng.choice(len(flat), size=min(n // 2, len(flat)),
                         replace=len(flat) < n // 2)
        for q in flat[idx]:
            d = q - center
            nd = float(np.linalg.norm(d))
            pts.append(q if nd <= radius else center + d * (radius / nd))
    m = n - len(pts)
    if m > 0:
        u = rng.normal(size=(m, 3))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        r = (radius * rng.random(m) ** (1.0 / 3.0))[:, None]
        pts.extend(list(center + u * r))
    pts.append(center)                      # ★ 계약 B: safe parking 후보 (제자리)
    return np.asarray(pts, float)


def _beam_cover(cov: List[np.ndarray], n_bad: int, width: int = N_BEAM) -> tuple:
    """색 있는 set cover -- limiter 마다 **정확히 하나** (계약 B)."""
    n_lim = len(cov)
    beam = [(np.zeros(n_bad, bool), [None] * n_lim)]
    for i in range(n_lim):
        C = cov[i]
        nxt = []
        for covered, pick in beam:
            if C.shape[0] == 0:
                nxt.append((covered, pick))
                continue
            gain = (C & ~covered).sum(axis=1)
            for j in np.argsort(-gain)[:width]:
                p = list(pick); p[i] = int(j)
                nxt.append((covered | C[j], p))
        nxt.sort(key=lambda z: -int(z[0].sum()))
        beam = nxt[:width]
    covered, pick = beam[0]
    return pick, covered


def snapshot_witness(seed0: int, ep: int, *, stride: int = 2,
                     seed: int = 0) -> dict:
    from shepherd.scripts.mission_rollout import scripted_role_actions

    rng = np.random.default_rng(seed)
    st = build_m4_env(seed0, ep, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=seed0 + ep)
    fid = env.finisher_id
    a_max, v_max = float(scn.limiter.a_max), float(st.threat["v_lim"])
    dt, tau, r_kill = float(env.dt), float(env.tau_deploy), float(env.kill_radius)
    C0 = np.array([env._p(l) for l in env._states()[0]], float)
    V0 = np.array([env._v(l) for l in env._states()[0]], float)
    n_lim = len(C0)

    frames = []
    for _ in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        frames.append((env._p(att).copy(), env._v(att).copy(),
                       np.asarray(fin, float).copy()))
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="clean")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, _ = env.step(acts)
        if (term and term.get(fid)) or (trunc and trunc.get(fid)):
            break

    best, tried, wits = None, 0, []
    for k in range(0, len(frames), stride):
        p_att, v_att, fin9 = frames[k]
        kw = env._vshot_kwargs(p_att, v_att, fin9)
        # ★ 계약 A: limiter **적용 전** union 에서 B/G 를 만든다
        _, _, caught, tr = V._union_sets(
            p_att, v_att, tau=tau, a_att_max=env.a_att_max,
            limiters=None, kill_radius=r_kill,
            attacker_turn_limited=False, omega_att_max=None, e_att=None,
            n=env.n_samples, n_segments=env.n_segments, seed=0,
            net_center=None, net_radius=None, return_paths=True,
            **{kk: vv for kk, vv in kw.items()})
        bad, good = ~caught, caught
        n_bad, n_good = int(bad.sum()), int(good.sum())
        if n_bad == 0 or n_good == 0:
            continue
        tk = k * dt
        Ck, rk = C0 + V0 * tk, reach_radius(tk, a_max, v_max)
        Pb_all, Lb_all = tr.paths[bad], tr.path_len[bad]
        Pg_all, Lg_all = tr.paths[good], tr.path_len[good]
        bi = rng.choice(len(Pb_all), size=min(SEARCH_BAD, len(Pb_all)),
                        replace=False)
        gi_sub = rng.choice(len(Pg_all), size=min(SEARCH_BAD // 2, len(Pg_all)),
                            replace=False)
        Pb, Lb = Pb_all[bi][:, ::SEARCH_STEP], Lb_all[bi]
        Pg, Lg = Pg_all[gi_sub][:, ::SEARCH_STEP], Lg_all[gi_sub]
        n_bad_s = len(Pb)

        cand = [_candidates(Ck[i], rk, Pb, Lb, rng) for i in range(n_lim)]
        covb = [_min_dist(Pb, Lb, cand[i]) <= r_kill for i in range(n_lim)]
        killg = [_min_dist(Pg, Lg, cand[i]) <= r_kill for i in range(n_lim)]

        # 보호 good 우선순위: limiter 로부터 clearance 가 큰 것
        clear = np.min([killg[i].mean(axis=0) for i in range(n_lim)], axis=0)
        g_order = np.argsort(clear)[:N_GOOD_TRY]

        for gi in g_order:
            tried += 1
            keep = [~killg[i][:, gi] for i in range(n_lim)]   # ★ 계약 D
            if any(kp.sum() == 0 for kp in keep):
                continue
            cov_k = [covb[i][keep[i]] for i in range(n_lim)]
            idx_k = [np.nonzero(keep[i])[0] for i in range(n_lim)]
            pick, covered = _beam_cover(cov_k, n_bad_s)
            unc = int((~covered).sum())
            L = np.array([cand[i][idx_k[i][pick[i]]] if pick[i] is not None
                          else Ck[i] for i in range(n_lim)])
            if best is None or unc < best["n_bad_uncovered"]:
                best = {"fire_step": k, "protected_good_id": int(gi),
                        "n_bad": n_bad, "n_bad_search": n_bad_s,
                        "n_bad_uncovered": unc,
                        "limiter_positions": L.tolist(),
                        "reachable_slack": (rk - np.linalg.norm(L - Ck, axis=1)).tolist()}
            if unc == 0:
                # ★ 원래 evaluator replay (env 경로 그대로)
                vf = env._vshot(p_att, v_att, L, fin9, seed=0)
                ok = bool((not vf.boxed_in) and vf.v_shot_worst >= 1.0
                          and vf.v_shot_soft >= env.theta_fire)
                rec = {"episode": ep, "found": ok, "fire_step": k,
                       "protected_good_id": int(gi), "n_bad": n_bad,
                       "n_good": n_good, "n_bad_uncovered": 0,
                       "limiter_positions": L.tolist(),
                       "reachable_slack": (rk - np.linalg.norm(L - Ck, axis=1)).tolist(),
                       "exact_boxed_in": bool(vf.boxed_in),
                       "exact_v_worst": float(vf.v_shot_worst),
                       "exact_v_soft": float(vf.v_shot_soft),
                       "exact_n_feasible": int(vf.n_feasible),
                       "theta_fire": float(env.theta_fire),
                       "initialization": "beam(colored set cover)",
                       "optimizer_seed": seed, "tried": tried,
                       "regime": regime_of(st.threat["a_att"], st.threat["tau"],
                                           st.threat["net_radius"])}
                if ok:
                    # ★ 첫 witness 에서 멈추지 않는다 -- ep9 같은 경계해가
                    #   대표가 되면 안 된다. 고정 예산 동안 계속 모으고
                    #   m_sel = min(m_bad, m_good) 로 **가장 강건한** 것을 고른다.
                    d = np.linalg.norm(tr.paths[:, :, None, :] - L[None, None, :, :],
                                       axis=3).min(axis=1)
                    blk = (d <= r_kill).any(axis=1)
                    sg = good & ~blk
                    m_bad = float(np.min(np.max(r_kill - d[bad], axis=1)))
                    m_good = (float(np.max(np.min(d[sg] - r_kill, axis=1)))
                              if sg.any() else -np.inf)
                    rec.update(m_bad=m_bad, m_good=m_good,
                               m_sel=float(min(m_bad, m_good)),
                               n_surviving_good=int(sg.sum()))
                    wits.append(rec)
                else:
                    best = {**best, "replay_failed": rec}
    if wits:
        wits.sort(key=lambda r: (-r["m_sel"], -min(r["reachable_slack"])))
        top = wits[0]
        return {**top, "label": "EXACT_WITNESS_FOUND",
                "n_witness": len(wits),
                "m_sel_all": [round(w["m_sel"], 4) for w in wits]}
    return {"episode": ep, "found": False, "label": "NO_WITNESS_WITHIN_BUDGET",
            "best": best, "tried": tried, "n_witness": 0,
            "regime": regime_of(st.threat["a_att"], st.threat["tau"],
                                st.threat["net_radius"])}


def audit(eps: List[int], seed0: int = 0, stride: int = 2) -> dict:
    recs = [snapshot_witness(seed0, e, stride=stride) for e in eps]
    found = [r for r in recs if r["found"]]
    unc = [r["best"]["n_bad_uncovered"] for r in recs
           if not r["found"] and r.get("best")]
    nb = [r["best"]["n_bad"] for r in recs if not r["found"] and r.get("best")]
    return {"contracts": ["A: B/G 는 limiter 적용 전 union 에서",
                          "B: 네 limiter 전부 위치 배정 (safe parking 포함)",
                          "C: 후보는 union path 에서",
                          "D: good 보호는 hard constraint"],
            "status_limit": "witness 미발견 != 불가능 (docs/52 §8.2)",
            "n": len(recs), "witness": len(found),
            "median_uncovered_on_fail": float(np.median(unc)) if unc else None,
            "median_n_bad_on_fail": float(np.median(nb)) if nb else None,
            "records": recs}


def main() -> None:
    ap = argparse.ArgumentParser(description="선택적 snapshot witness (docs/52 §8.2)")
    ap.add_argument("--episodes", type=int, nargs="+", required=True)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--stride", type=int, default=2)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    r = audit(args.episodes, args.seed0, args.stride)
    for c in r["contracts"]:
        print("  계약", c)
    print(f"\n  witness {r['witness']}/{r['n']}")
    if r["median_uncovered_on_fail"] is not None:
        print(f"  실패 시 uncovered 중앙 {r['median_uncovered_on_fail']:.0f} "
              f"/ bad {r['median_n_bad_on_fail']:.0f}")
    for rec in r["records"]:
        b = rec.get("best") or {}
        print(f"    ep{rec['episode']:3d} {rec['regime'][:8]:8s} "
              f"found={str(rec['found']):5s} "
              f"uncovered {b.get('n_bad_uncovered', '-')}/{b.get('n_bad', '-')} "
              f"@t={b.get('fire_step', '-')}")
    print("★", r["status_limit"])
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"  -> {args.out}")


if __name__ == "__main__":
    main()
