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

DEFENDERS = ("learned_det", "learned_sto", "fin12", "fin12_fb", "kfirst50")
NET = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
CHUNK = 8                                   # 워커 작업 단위 (episode 수)


def _def_act(env, o, name, team):
    if team is not None:
        return def_actions(team.act(o, name == "learned_det")[0], env)
    acts = scripted_def_actions(env, KFIRST_R if name == "kfirst50" else None)
    if name == "fin12":                     # fallback 없음: limiter 영구 비무장
        for l in env.limiter_ids:
            acts[l][3] = 0.0
    return acts


def episodes(job):
    """job = (방어 이름, 방어 snap|None, 상대, 시드들, 궤적 기록 수) → episode 기록 리스트."""
    import torch
    dname, dsnap, opp, seeds, n_traj = job
    env = _W["env"]
    od = len(next(iter(env.reset(seed=0)[0].values())))
    dteam = _team(DEF_ROLES, dsnap, od) if dsnap is not None else None
    ateam = (_team(ATT_ROLES, opp["snap"], od + Z_DIM, disc=(DISC_IN, Z_DIM))
             if opp["kind"] == "nn" else None)
    out = []
    for j, s in enumerate(seeds):
        np.random.seed(s); torch.manual_seed(s)
        env.set_scripted_attacker(None if ateam else ladder_attacker(opp["ov"], opp.get("legacy", False)))
        obs, _ = env.reset(seed=s)
        inn, done, t = env.inner, False, 0
        tgt = np.asarray(inn.layout.target, float)
        rec = {"seed": s, "opp": opp["name"], "arm_d": None, "fire_d": None, "n_fire": 0}
        tr = [] if j < n_traj else None
        while not done:
            o = obs["finisher_0"]
            acts = _def_act(env, o, dname, dteam)
            if ateam:
                acts["adversary_0"] = att_action(ateam.act(env.att_obs(o))[0], env)
            lims, fin, att = inn._states()
            p_att = inn._p(att)
            armed = [float(acts[l][3] > 0.5) for l in env.limiter_ids]
            if rec["arm_d"] is None and any(armed):
                rec["arm_d"] = round(float(np.linalg.norm(p_att - tgt)), 2)
            obs, _, done, info = env.step(acts)
            fi = info["finisher_0"]
            if fi.get("fire_event"):
                rec["n_fire"] += 1
                if rec["fire_d"] is None:
                    rec["fire_d"] = round(float(np.linalg.norm(p_att - inn._p(fin))), 2)
            if tr is not None:
                tr.append(np.r_[p_att, inn._p(fin), np.concatenate([inn._p(x) for x in lims]),
                                armed, float(bool(fi.get("fire_event")))])
            t += 1
        rec.update(label=str(fi["fs1_label"]), len=t)
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
                     "arm_d_median": round(float(np.median(arm)), 1) if arm else None,
                     "fire_d_median": (round(float(np.median([r["fire_d"] for r in rs if r["fire_d"] is not None])), 1)
                                       if any(r["fire_d"] is not None for r in rs) else None)})
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
                    jobs.append((d, dsnap, opp, seeds[c:c + CHUNK], nt if c == 0 else 0))
    from shepherd.fs1.world import FS1Spec
    with mp.get_context("spawn").Pool(a.workers, initializer=_init_worker,
                                      initargs=(FS1Spec().__dict__,)) as P:
        recs = [x for part in P.map(episodes, jobs) for x in part]
    with open(out / "episodes.jsonl", "w", encoding="utf-8") as f:
        for d, g, r in recs:
            f.write(json.dumps({"defender": d, "group": g, **{k: v for k, v in r.items() if k != "traj"}}) + "\n")
    rows = summarize(recs)
    import subprocess
    meta = {"ckpt": str(a.ckpt), "ckpt_it": ck.get("it"), "ckpt_total_steps": ck.get("total_steps"),
            "episodes": a.episodes, "seed": a.seed, "defenders": a.defenders,
            "groups": {g: [o["name"] for o in v] for g, v in groups.items()},
            "exploiter": a.exploiter, "manifest": a.manifest, "ladder": a.ladder,
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
    lg = sub.add_parser("log")
    lg.add_argument("--log", required=True)
    lg.add_argument("--window", type=int, default=30)
    a = ap.parse_args(argv)
    run(a) if a.cmd == "run" else log_summary(a)


if __name__ == "__main__":
    main()
