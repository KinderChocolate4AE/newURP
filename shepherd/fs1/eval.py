"""FS1 평가 (docs/123 §4): 방어 × 상대 교차 평가 + 궤적 그림 + 학습 로그 요약.

    python -m shepherd.fs1.eval run --ckpt artifacts/fs1/run3/ckpt.pt --out artifacts/fs1/run3/eval
    python -m shepherd.fs1.eval log --log artifacts/fs1/run3/log.jsonl --window 30

방어: learned_det / learned_sto (ckpt 방어 팀) · fin12 (scripted, fallback 없음) ·
      fin12_fb (+ net 소진 후 limiter PN 인계 = 학습 pool 의 scripted_fin12) ·
      kfirst50 (+ 공격자 50 m 안 limiter 무장 = 학습 pool 의 scripted_kfirst50).
상대 그룹: ladder (P1a 24 config 순환) · rl_latest (ckpt 공격 팀) · pool (공격 pool nn
      snapshot 균등 표본 k 개 순환) · ex_NAME (--exploiter NAME=ckpt 의 공격 팀, train --exploit).
봉인 계약 = scripts/fs1_eval_manifest.py (docs/123 §8), 실행 = scripts/run_fs1_eval_server.sh.
시드: 그룹 안 episode i 의 시드 = seed + i — 모든 방어가 같은 초기 배치를 본다 (paired).
RL 공격자는 학습 때처럼 확률적 행동.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import pathlib
from collections import Counter, defaultdict

import numpy as np

from shepherd.fs1.train import (ATT_ROLES, DEF_ROLES, DISC_IN, KFIRST_R, _W, _init_worker, _team,
                                att_action, def_actions, ladder_attacker, ladder_pool,
                                scripted_def_actions)
from shepherd.fs1.world import DEFENDED, Z_DIM

DEFENDERS = ("learned_det", "learned_sto", "fin12", "fin12_fb", "kfirst50", "c5_fb", "fwd_fb",
             "mix5050", "kfirst_rand")       # E3b-1: 혼합(시드 짝홀 50/50)·파라미터 무작위 scripted
NET = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
CHUNK = 8                                   # 워커 작업 단위 (episode 수)
C5_R_D, C5_DPHI = 9.0, np.deg2rad(30.0)     # B2 RULE_COOP kw (P1c c5) — E3 D3 진단용
FWD_RHO = 0.5                               # P1d fwd (전진 호: r = max(r_d, rho·R_h))
COOP_WINDOW_D = 16.0                        # P-②c 창 정의 = 1.5a/E7-a′ 와 동일 (LOADED ∧ d ≤ 16 m)


def _arc_act(env, fwd):
    """D3 진단 방어 (docs/124 §3): c5/fwd arc limiter (조형형, FCS station 공간으로 번역) +
    finisher fin12 + fallback 무장 (net 소진 후) — fin12_fb 와 같은 무장 규칙, 위치만 다름."""
    from shepherd.agents.baselines import arc_geometry, arc_slots, min_cost_assignment
    from shepherd.fs1.world import STATION
    inn = env.inner
    lims, _, att = inn._states()
    tgt = np.asarray(inn.layout.target, float)
    p_att = inn._p(att)
    r, dphi = arc_geometry(tgt, p_att, C5_R_D, C5_DPHI, FWD_RHO if fwd else None)
    slots = arc_slots(tgt, p_att, r, dphi, n=len(env.limiter_ids))
    perm = min_cost_assignment([inn._p(l) for l in lims], slots)
    arm = 1.0 if env.sys.net_spent else 0.0
    acts = {lid: np.r_[np.clip((slots[perm[i]] - tgt) / STATION, -1, 1), arm]
            for i, lid in enumerate(env.limiter_ids)}
    acts["finisher_0"] = np.r_[env.start_station["finisher_0"], 12.0, 1.0]
    return acts


def _ep_kf_r(name, seed):
    """episode 단위 방어 문맥 (결정론 — 같은 seed 면 같은 추첨). mix5050 = 시드 짝홀로 정확 50/50,
    kfirst_rand = U[30, 70] (np.random 은 episodes() 가 seed 로 초기화한 뒤)."""
    if name == "kfirst50":
        return KFIRST_R
    if name == "mix5050":
        return KFIRST_R if seed % 2 == 0 else None     # None = fin12_fb (fallback 무장)
    if name == "kfirst_rand":
        return float(np.random.uniform(30.0, 70.0))
    return None


def _def_act(env, o, name, team, kf_r=None):
    if team is not None:
        return def_actions(team.act(o, name == "learned_det")[0], env)
    if name in ("c5_fb", "fwd_fb"):
        return _arc_act(env, name == "fwd_fb")
    acts = scripted_def_actions(env, kf_r)
    if name == "fin12":                     # fallback 없음: limiter 영구 비무장
        for l in env.limiter_ids:
            acts[l][3] = 0.0
    return acts


def _kill_phase(label, n_fire):
    """E7-c (docs/130 §2): kinetic 무력화 시점. K_FIRST = net 소진 전 kinetic (world.py 라벨
    규약) → 발사 전이면 pre_shot, 발사 후면 shot_window (net 비행 중 탈출 차단). HARD_KILL =
    net 소진 뒤 = fallback."""
    if label == "K_FIRST":
        return "shot_window" if n_fire > 0 else "pre_shot"
    if label == "HARD_KILL":
        return "fallback"
    return None


ATT_IV = ("none", "out0", "in0", "zfix", "lat0", "shuf_out", "shuf_in", "in_half")


def _att_iv(res, iv, env, k, donor):
    """E2 공격자 개입 (docs/132): 학습 residual 만 바꾼다 (autopilot 불변). 구간 in = 공격자–
    finisher 거리 ≤ COOP_WINDOW_D (창 정의와 같은 16 m), out = 그 밖. k = 현재 구간 안 step 번호
    (shuffle 용), donor = 다른 episode 의 같은 구간 residual 열 (기록 순서, 길이 넘으면 순환)."""
    if iv in ("none", "zfix"):
        return res
    inn = env.inner
    _, fin, att = inn._states()
    p = inn._p(att)
    seg_in = np.linalg.norm(p - inn._p(fin)) <= COOP_WINDOW_D
    if iv == "lat0":                                   # 자산 방향 성분만 남김 (횡방향 제거)
        u = np.asarray(inn.layout.target, float) - p
        u = u / max(np.linalg.norm(u), 1e-9)
        return (res @ u) * u
    if iv == "in_half":
        return 0.5 * res if seg_in else res
    if seg_in != (iv in ("in0", "shuf_in")):           # 개입 구간 밖이면 그대로
        return res
    if iv.startswith("shuf"):
        return np.asarray(donor[k % len(donor)], float) if donor else np.zeros(3)
    return np.zeros(3)                                 # out0 / in0


def _eval_init(spec_kw, coop_window=False, att_iv="none", donor=None, record_res=False, env_seed=None):
    _init_worker(spec_kw)
    if env_seed is not None:     # E2: env 생성 seed (기본 = worker pid) 가 m4 스택 RNG 로 새어 판정
        from shepherd.fs1.world import FS1Env, FS1Spec       # 값이 실행마다 달라짐 → 고정해 재현
        _W["env"] = FS1Env(FS1Spec(**spec_kw), seed=int(env_seed))
    _W["coop_window"] = bool(coop_window)
    _W["att_iv"] = att_iv
    _W["record_res"] = bool(record_res)
    _W["donor"] = None
    if donor:                                          # seed → {in, out}; 공여자 = 다음 seed (순환)
        d = json.loads(pathlib.Path(donor).read_text(encoding="utf-8"))
        ks = sorted(d, key=int)
        _W["donor"] = {int(s): d[ks[(i + 1) % len(ks)]] for i, s in enumerate(ks)}


def episodes(job):
    """job = (방어 이름, 방어 snap|None, 상대, 시드들, 궤적 기록 수) → episode 기록 리스트."""
    import torch
    dname, dsnap, opp, seeds, n_traj, *rest = job
    dstack = rest[0] if rest else 1
    env = _W["env"]
    od = len(next(iter(env.reset(seed=0)[0].values())))
    dteam = _team(DEF_ROLES, dsnap, od * max(dstack, 1)) if dsnap is not None else None
    ateam = (_team(ATT_ROLES, opp["snap"], od + Z_DIM, disc=(DISC_IN, Z_DIM))
             if opp["kind"] == "nn" else None)
    out = []
    for j, s in enumerate(seeds):
        np.random.seed(s); torch.manual_seed(s)
        kf_r = _ep_kf_r(dname, s)
        env.set_scripted_attacker(None if ateam else ladder_attacker(opp["ov"], opp.get("legacy", False)))
        obs, _ = env.reset(seed=s)
        inn, done, t = env.inner, False, 0
        tgt = np.asarray(inn.layout.target, float)
        rec = {"seed": s, "opp": opp["name"], "arm_d": None, "fire_d": None, "n_fire": 0,
               "v_fire": None, "p_feas": None,       # R1/R2 공통 진단 (docs/124 D4): 첫 발사 tick
               "rob_fire": None}                     # E1 2차 지표: 첫 발사 순간 robust 판정 (포획 예정)
        if _W.get("coop_window"):                    # docs/129 §7 P-②c (e7b v1.1): 창 tick 협력
            rec.update(n_win=0, n_rob=0, n_C=0, n_H=0)
        tr = [] if j < n_traj else None
        iv = _W.get("att_iv", "none")
        z0, res_log, kseg = env.z.copy(), {"in": [], "out": []}, {"in": 0, "out": 0}
        dn = (_W.get("donor") or {}).get(s)
        prev = None                     # arm D 프레임 스택 (docs/128): k=4 최신-우선 타일-초기화
        while not done:
            o = obs["finisher_0"]
            if dstack > 1:
                if prev is None:
                    prev = [o] * (dstack - 1)
                o_def = np.concatenate([o, *prev])
            else:
                o_def = o
            acts = _def_act(env, o_def, dname, dteam, kf_r)
            lims, fin, att = inn._states()
            p_att = inn._p(att)
            if ateam:
                if iv == "zfix":                         # rng 소비는 그대로, 관측 z 만 첫 추첨 고정
                    env.z = z0
                res = att_action(ateam.act(env.att_obs(o))[0], env)
                seg = "in" if np.linalg.norm(p_att - inn._p(fin)) <= COOP_WINDOW_D else "out"
                res_log[seg].append(np.round(res, 3).tolist())
                acts["adversary_0"] = _att_iv(res, iv, env, kseg[seg], (dn or {}).get(seg))
                kseg[seg] += 1
            armed = [float(acts[l][3] > 0.5) for l in env.limiter_ids]
            if (_W.get("coop_window") and inn.fsm.state.value == "LOADED"
                    and np.linalg.norm(p_att - inn._p(fin)) <= COOP_WINDOW_D):
                sd = inn._seed * 100003 + inn._step_i     # 같은 seed·조준축, limiter 만 제거
                w = inn._vshot(p_att, inn._v(att), [inn._p(x) for x in lims], fin, seed=sd)
                f = inn._vshot(p_att, inn._v(att), [], fin, seed=sd)
                rw = w.v_shot_worst >= 1.0 and not w.boxed_in
                rf = f.v_shot_worst >= 1.0 and not f.boxed_in
                rec["n_win"] += 1; rec["n_rob"] += int(rw)
                rec["n_C"] += int(rw and not rf); rec["n_H"] += int(rf and not rw)
            if rec["arm_d"] is None and any(armed):
                rec["arm_d"] = round(float(np.linalg.norm(p_att - tgt)), 2)
            obs, _, done, info = env.step(acts)
            if dstack > 1:
                prev = [o, *prev[:-1]]
            fi = info["finisher_0"]
            if fi.get("fire_event"):
                rec["n_fire"] += 1
                if rec["fire_d"] is None:
                    rec["fire_d"] = round(float(np.linalg.norm(p_att - inn._p(fin))), 2)
                    rec["v_fire"] = round(float(fi.get("v_shot_soft") or 0.0), 4)
                    rec["p_feas"] = round(float(fi.get("p_feasible") or 0.0), 4)
                    rec["rob_fire"] = bool(inn._pending_capture)   # env.py:341 (읽기만)
            if tr is not None:
                tr.append(np.r_[p_att, inn._p(fin), np.concatenate([inn._p(x) for x in lims]),
                                armed, float(bool(fi.get("fire_event")))])
            t += 1
        rec.update(label=str(fi["fs1_label"]), len=t)
        rec["kill_phase"] = _kill_phase(rec["label"], rec["n_fire"])
        if _W.get("record_res"):
            rec["res"] = res_log
        if tr is not None:
            rec["traj"] = np.array(tr, np.float32).tolist()
        out.append(rec)
    return [(dname, opp["group"], r) for r in out]


def opponent_groups(ck, a):
    """그룹 이름 → 상대 리스트 (episode i 는 리스트[i % len])."""
    att_pool = [dict(e, snap=s) for e, s in zip(ck["pools"]["att"], ck["pool_snaps"]["att"])
                if e["kind"] == "nn"]
    idx = np.unique(np.linspace(0, len(att_pool) - 1, min(a.pool_k, len(att_pool))).round().astype(int))
    g = {"ladder": ladder_pool(legacy=a.ladder == "legacy"),
         "rl_latest": [{"kind": "nn", "name": "att_latest", "snap": ck["teams"]["att"]}],
         "pool": [att_pool[i] for i in idx]}
    g = {k: v for k, v in g.items() if k in a.groups}
    import torch
    for spec in a.exploiter or []:                # NAME=PATH → 그룹 ex_NAME (모든 방어가 상대)
        name, path = spec.split("=", 1)
        snap = torch.load(path, weights_only=False)["teams"]["att"]
        g[f"ex_{name}"] = [{"kind": "nn", "name": f"ex_{name}", "snap": snap}]
    return {k: [dict(o, group=k) for o in v] for k, v in g.items()}


def summarize(recs):
    cells = defaultdict(list)
    for d, g, r in recs:
        cells[(d, g)].append(r)
    rows = []
    for (d, g), rs in sorted(cells.items()):
        c = Counter(r["label"] for r in rs)
        n, dfd = len(rs), sum(c[x] for x in DEFENDED)
        arm = [r["arm_d"] for r in rs if r["arm_d"] is not None]
        rows.append({"defender": d, "group": g, "n": n, "defended": dfd,
                     "def_rate": round(dfd / n, 4), "net": c["NET_CAPTURE"] + c["CAPTURE_WITH_CONTACT"],
                     "k_first": c["K_FIRST"], "fallback": c["HARD_KILL"],
                     "penetrated": c["PENETRATED"], "labels": dict(c),
                     "v_fire_median": (round(float(np.median([r["v_fire"] for r in rs if r.get("v_fire") is not None])), 3)
                                       if any(r.get("v_fire") is not None for r in rs) else None),
                     "arm_d_median": round(float(np.median(arm)), 1) if arm else None,
                     "fire_d_median": (round(float(np.median([r["fire_d"] for r in rs if r["fire_d"] is not None])), 1)
                                       if any(r["fire_d"] is not None for r in rs) else None)})
        kp = Counter(r.get("kill_phase") for r in rs if r.get("kill_phase"))
        rows[-1]["kill_phase"] = dict(kp)          # E7-c: D_shot = net + shot_window kinetic
        rows[-1]["d_shot"] = rows[-1]["net"] + kp.get("shot_window", 0)
        if "n_win" in rs[0]:                       # P-②c 창 tick 협력 (e7b v1.1)
            nw = sum(r["n_win"] for r in rs)
            rows[-1]["coop"] = {"n_win": nw, "n_rob": sum(r["n_rob"] for r in rs),
                                "n_C": sum(r["n_C"] for r in rs), "n_H": sum(r["n_H"] for r in rs),
                                "C": round(sum(r["n_C"] for r in rs) / nw, 5) if nw else None}
    return rows


def plot(recs, out, view, zoom=25.0):
    """(방어, 그룹) 별 궤적 PNG. 위에서 본 xy (자산 = 원점), 윗줄 ±view m · 아랫줄 ±zoom m
    (kinetic·net 교전 확대). limiter 무장 구간 = 굵은 주황."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 없음 — 그림 생략"); return
    cells = defaultdict(list)
    for d, g, r in recs:
        if "traj" in r:
            cells[(d, g)].append(r)
    for (d, g), rs in cells.items():
        fig, axs = plt.subplots(2, len(rs), figsize=(4 * len(rs), 8), squeeze=False)
        for j, r in enumerate(rs):
            T = np.asarray(r["traj"])
            f = T[:, 22] > 0.5
            for ax, w in ((axs[0, j], view), (axs[1, j], zoom)):
                ax.plot(T[:, 0], T[:, 1], "r-", lw=1)
                ax.plot(T[:, 3], T[:, 4], "b-", lw=1)
                for k in range(4):
                    x, y, arm = T[:, 6 + 3 * k], T[:, 7 + 3 * k], T[:, 18 + k] > 0.5
                    ax.plot(x, y, "-", c="0.5", lw=0.8)
                    ax.plot(np.where(arm, x, np.nan), np.where(arm, y, np.nan), "-", c="orange", lw=2.5)
                ax.plot(T[f, 3], T[f, 4], "b*", ms=12)
                ax.plot(T[-1, 0], T[-1, 1], "rx", ms=8)
                ax.plot(0, 0, "ks", ms=5)
                ax.set_xlim(-w, w); ax.set_ylim(-w, w); ax.set_aspect("equal")
            axs[0, j].set_title(f"{r['opp']} s{r['seed']}\n{r['label']} arm@{r['arm_d']} "
                                f"fire@{r['fire_d']}", fontsize=8)
        fig.suptitle(f"{d} vs {g}  (red = attacker, blue = finisher, gray = limiter, "
                     f"orange = armed, * = net fire, x = end)", fontsize=9)
        fig.tight_layout(); fig.savefig(out / f"traj_{d}_{g}.png", dpi=90); plt.close(fig)


def run(a):
    import torch
    ck = torch.load(a.ckpt, weights_only=False)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    groups = opponent_groups(ck, a)
    jobs = []
    for d in a.defenders:
        dsnap = ck["teams"]["def"] if d.startswith("learned") else None
        for g, opps in groups.items():
            for k, opp in enumerate(opps):
                seeds = [a.seed + i for i in range(a.episodes) if i % len(opps) == k]
                # 궤적: 단일 상대 그룹은 앞 traj 판, 다중 상대 그룹은 앞 traj 개 상대의 첫 판
                nt = a.traj if len(opps) == 1 else int(k < a.traj)
                for c in range(0, len(seeds), CHUNK):
                    jobs.append((d, dsnap, opp, seeds[c:c + CHUNK], nt if c == 0 else 0,
                                 a.def_stack))
    from shepherd.fs1.world import FS1Spec
    spec = FS1Spec(obs_time=a.stack == "r4p", mu=a.mu, nu=a.nu, tau_scale=a.tau_scale,
                   theta_scale=a.theta_scale, aim=a.aim, limiter_roe=a.limiter_roe,
                   limiter_inert=a.limiter_inert)
    with mp.get_context("spawn").Pool(a.workers, initializer=_eval_init,
                                      initargs=(spec.__dict__, a.coop_window, a.att_iv, a.att_donor,
                                                bool(a.record_res), a.env_seed)) as P:
        recs = [x for part in P.map(episodes, jobs) for x in part]
    if a.record_res:                                   # E2 shuffle 공여 파일 (첫 방어 기준, seed → in/out)
        res = {str(r["seed"]): r["res"] for d, g, r in recs if d == a.defenders[0]}
        pathlib.Path(a.record_res).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.record_res).write_text(json.dumps(res), "utf-8")
    with open(out / "episodes.jsonl", "w", encoding="utf-8") as f:
        for d, g, r in recs:
            f.write(json.dumps({"defender": d, "group": g,
                                **{k: v for k, v in r.items() if k not in ("traj", "res")}}) + "\n")
    rows = summarize(recs)
    import subprocess
    meta = {"ckpt": str(a.ckpt), "ckpt_it": ck.get("it"), "ckpt_total_steps": ck.get("total_steps"),
            "episodes": a.episodes, "seed": a.seed, "defenders": a.defenders,
            "groups": {g: [o["name"] for o in v] for g, v in groups.items()},
            "exploiter": a.exploiter, "manifest": a.manifest, "ladder": a.ladder, "stack": a.stack,
            "mu": a.mu, "nu": a.nu, "def_stack": a.def_stack, "tau_scale": a.tau_scale,
            "theta_scale": a.theta_scale, "aim": a.aim, "coop_window": a.coop_window,
            "limiter_roe": a.limiter_roe, "limiter_inert": a.limiter_inert,
            "att_iv": a.att_iv, "att_donor": a.att_donor, "env_seed": a.env_seed,
            "git": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
            "seeds_by_group": {g: [r["seed"] for d, gg, r in recs if gg == g and d == a.defenders[0]]
                               for g in groups}}
    (out / "summary.json").write_text(json.dumps({"meta": meta, "rows": rows}, indent=2), "utf-8")
    print_table(rows)
    plot(recs, out, a.view)


def print_table(rows):
    print("| defender | group | defended/n | net | K_FIRST | fallback | pen | arm_d med | fire_d med |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| {defender} | {group} | {defended}/{n} | {net} | {k_first} | {fallback} | {penetrated} "
              "| {arm_d_median} | {fire_d_median} |".format(**r))


def log_summary(a):
    """학습 로그를 iter 창 단위로 요약: 학습 측 × 상대 유형 (script/nn) 별 라벨 합."""
    recs = [json.loads(l) for l in open(a.log, encoding="utf-8")]
    print("| it | side | vs | n | def_win | NET | K_FIRST | HARD_KILL | PEN |")
    print("|---|---|---|---|---|---|---|---|---|")
    for lo in range(0, recs[-1]["it"] + 1, a.window):
        win = [r for r in recs if lo <= r["it"] < lo + a.window]
        for side in ("def", "att"):
            for kind in ("script", "nn"):
                c = Counter()
                for r in win:
                    if r["side"] == side:
                        c.update(r.get("labels_by_kind", {}).get(kind, {}))
                n = sum(c.values())
                if not n:
                    continue
                net = c["NET_CAPTURE"] + c["CAPTURE_WITH_CONTACT"]
                dw = sum(c[x] for x in DEFENDED) / n
                print(f"| {lo}-{lo + a.window - 1} | {side} | {kind} | {n} | {dw:.3f} | {net} "
                      f"| {c['K_FIRST']} | {c['HARD_KILL']} | {c['PENETRATED']} |")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--ckpt", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--episodes", type=int, default=48, help="(방어, 그룹) 셀당 episode 수")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 2))
    r.add_argument("--defenders", nargs="+", default=list(DEFENDERS), choices=DEFENDERS)
    r.add_argument("--groups", nargs="+", default=["ladder", "rl_latest", "pool"])
    r.add_argument("--pool-k", type=int, default=4, help="공격 pool nn snapshot 표본 수")
    r.add_argument("--exploiter", nargs="+", default=None, metavar="NAME=PATH",
                   help="fresh exploiter ckpt (train --exploit 산출물) → 그룹 ex_NAME")
    r.add_argument("--traj", type=int, default=4, help="셀당 궤적 그림 episode 수")
    r.add_argument("--view", type=float, default=120.0, help="그림 반폭 (m, 자산 중심)")
    r.add_argument("--manifest", default=None, help="봉인 manifest hash (기록용)")
    r.add_argument("--ladder", choices=["nominal", "legacy"], default="nominal",
                   help="사다리 공격자 구성. legacy = eval v1 (jink 0 변형, docs/123 §8.1)")
    r.add_argument("--stack", choices=["r4", "r4p"], default="r4",
                   help="ckpt 의 학습 stack 과 일치시킬 것 (r4p = 관측 66-D)")
    r.add_argument("--mu", type=float, default=0.35, help="E3 cell: 방어 가속비 (FS1Spec.mu)")
    r.add_argument("--nu", type=float, default=1.0, help="E3 cell: 방어 속도비 (FS1Spec.nu)")
    r.add_argument("--tau-scale", type=float, default=1.0, help="E7-b 세계 변형 (FS1Spec)")
    r.add_argument("--theta-scale", type=float, default=1.0, help="E7-b 세계 변형 (FS1Spec)")
    r.add_argument("--aim", choices=["cv", "ma"], default="cv", help="E7-b FCS 조준 (FS1Spec)")
    r.add_argument("--limiter-roe", choices=["a", "post_shot"], default="a",
                   help="E7-c (docs/130): post_shot = 첫 발사 전 limiter kinetic 차단")
    r.add_argument("--limiter-inert", action="store_true",
                   help="E7-c: physics.kill_radius = 0 (판정 폐쇄·kinetic 동시 0)")
    r.add_argument("--coop-window", action="store_true",
                   help="P-②c (docs/129 §7, e7b v1.1): 창 tick 마다 limiter 有/無 판정 재계산")
    r.add_argument("--att-iv", choices=ATT_IV, default="none",
                   help="E2 (docs/132) 공격자 residual 개입. none = 기존과 비트 동일")
    r.add_argument("--att-donor", default=None, help="shuf_* 공여 residual 파일 (--record-res 산출물)")
    r.add_argument("--record-res", default=None, metavar="PATH",
                   help="RL 공격자 residual 을 구간 (in/out) 별로 PATH 에 기록 (shuffle 공여용)")
    r.add_argument("--env-seed", type=int, default=None,
                   help="워커 env 생성 seed 고정 (기본 None = pid, 기존 동작). 실행 간 비트 재현용")
    r.add_argument("--def-stack", type=int, default=1,
                   help="방어 obs 프레임 스택 k (arm D, docs/128: 최신-우선, 타일-초기화; "
                        "학습 ckpt 와 일치시킬 것)")
    lg = sub.add_parser("log")
    lg.add_argument("--log", required=True)
    lg.add_argument("--window", type=int, default=30)
    a = ap.parse_args(argv)
    run(a) if a.cmd == "run" else log_summary(a)


if __name__ == "__main__":
    main()
