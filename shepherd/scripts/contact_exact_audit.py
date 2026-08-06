"""리뷰 3 반증 (A) — chord 검출을 실제 step 내부 이차 궤적으로 검증 (docs/54 §3.2).

17 kill event 스텝에서 backend 상태로 상대 궤적을 재구성한다:

    a_rel = (v_rel(t+dt) - v_rel(t)) / dt        (구분 상수 가속 가정)
    r(s)  = r0 + v_rel(t)*s + 0.5*a_rel*s^2,  s in [0, dt]

모형 자기검사 |r(dt) - r1| < 1e-6 을 먼저 통과해야 결과를 쓴다 (재구성이
backend 적분과 일치하는가). 판정: d_exact > r_contact 인 event 수 = chord
false positive. 사전 기대 = 경계 여유 < 0.033 m 인 2건(ep19·47)만 위험,
**3건 이상이면 "15/17 강건" 철회** (docs/54 §3.2, 결과 후 불변경).
torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
import numpy as np

from shepherd.env_sys import SystemSpec, _seg_min_dist
from shepherd.m4_env import build_m4_env
from shepherd.scripts.boxed_arm_audit import _kw, _sysenv
from shepherd.scripts.mission_rollout import scripted_role_actions

__all__ = ["exact_audit"]

EPISODES = (3, 12, 15, 17, 18, 19, 29, 30, 34, 41, 42, 44, 47, 49, 51, 52, 57)


def _min_dist_quadratic(r0, v0, a, dt, n=2001):
    s = np.linspace(0.0, dt, n)[:, None]
    path = r0[None, :] + v0[None, :] * s + 0.5 * a[None, :] * s ** 2
    return float(np.min(np.linalg.norm(path, axis=1)))


def exact_audit(seed0: int = 0) -> dict:
    rows = []
    for ep in EPISODES:
        st = build_m4_env(seed0, ep, **_kw())
        env, scn, lay = st.env, st.scn, st.lay
        env.reset(seed=seed0 + ep)
        se = _sysenv(env)
        fid = env.finisher_id
        dt = float(env.dt)
        branched = fired = False
        prev = None
        post_cap = {}

        # ★ 주차(stage 5)가 event 직후 소진 limiter 를 PARK 로 옮기므로, 실제
        #   post-step 물리 상태는 resolver 호출 시점(주차 전)에 가로채야 한다.
        #   첫 실행에서 모형 자기검사가 이걸 잡았다 (max err 63 -- 주차 좌표).
        from shepherd.env_sys import ModeSystemEnv

        def spy(p_att_pre, lims_pre, p_att_post, lims_post, d_asset):
            ls, _, at = se.inner._states()
            post_cap["state"] = ([(se.inner._p(s).copy(), se.inner._v(s).copy())
                                  for s in ls],
                                 se.inner._p(at).copy(), se.inner._v(at).copy())
            return ModeSystemEnv._resolve_contacts(
                se, p_att_pre, lims_pre, p_att_post, lims_post, d_asset)

        se._resolve_contacts = spy

        for t in range(int(lay.episode_len)):
            lims, fin, att = env._states()
            vf = env._vshot(env._p(att), env._v(att), [env._p(l) for l in lims],
                            fin, seed=0)
            if vf.boxed_in and not branched:
                branched = True
                se.spec = SystemSpec(enabled=True, contact_resolver=True)
            acts = scripted_role_actions(env, scn, lay, limiter_mode="intercept",
                                         fire_mode="never")
            if branched and not fired:
                a = np.asarray(acts[fid], np.float32).copy()
                if len(a) >= 5:
                    a[4] = 1.0
                    acts[fid] = a
                    fired = True
            acts[env.adversary_id] = np.zeros(3, np.float32)
            prev = ([(env._p(l).copy(), env._v(l).copy()) for l in lims],
                    env._p(att).copy(), env._v(att).copy())
            n_before = len(se.commits)
            env.step(acts)
            new = se.commits[n_before:]
            for rec in new:
                if rec.source != "contact":
                    continue
                i = rec.limiter_index
                (lims1, p_a1, v_a1) = post_cap["state"]   # 주차 전 스냅샷
                (lims0, p_a0, v_a0) = prev
                p_l0, v_l0 = lims0[i]
                p_l1, v_l1 = lims1[i]
                r0 = p_a0 - p_l0
                r1 = p_a1 - p_l1
                v0 = v_a0 - v_l0
                v1 = v_a1 - v_l1
                a_rel = (v1 - v0) / dt
                model_err = float(np.linalg.norm(r0 + v0 * dt + 0.5 * a_rel * dt ** 2 - r1))
                rows.append(dict(
                    episode=ep, step=rec.commit_step, limiter=i, outcome=rec.outcome,
                    d_chord=round(float(_seg_min_dist(r0, r1)), 4),
                    d_exact=round(_min_dist_quadratic(r0, v0, a_rel, dt), 4),
                    d_endpoints=round(float(min(np.linalg.norm(r0), np.linalg.norm(r1))), 4),
                    a_rel_norm=round(float(np.linalg.norm(a_rel)), 2),
                    model_err=model_err))
            if getattr(env, "hard_kill", False):
                break
    r_c = 0.75
    kills = [r for r in rows if r["outcome"] == "KILL"]
    return dict(
        r_contact=r_c,
        model_check_pass=all(r["model_err"] < 1e-6 for r in rows),
        max_model_err=max((r["model_err"] for r in rows), default=None),
        n_kill=len(kills),
        chord_false_positive=[r["episode"] for r in kills if r["d_exact"] > r_c],
        events=rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="리뷰3 (A) 실 궤적 접촉 검증")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = exact_audit()
    print(f"model check: {'PASS' if r['model_check_pass'] else 'FAIL'} "
          f"(max err {r['max_model_err']:.2e})")
    print(f"{'ep':>4} {'lim':>3} {'outcome':>8} {'endpoint':>8} {'chord':>7} {'exact':>7}")
    for e in r["events"]:
        print(f"{e['episode']:>4} {e['limiter']:>3} {e['outcome']:>8} "
              f"{e['d_endpoints']:>8.3f} {e['d_chord']:>7.3f} {e['d_exact']:>7.3f}")
    print(f"\nchord false positive (d_exact > {r['r_contact']}): "
          f"{r['chord_false_positive'] or '없음'}")
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
