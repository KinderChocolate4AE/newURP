"""Server-side PSRO-lite loop for one defender lineage (runs inside a night_* tmux).
Round r: train defender D_r (init D_{r-1}) vs pool + scripted -> 3 red teams vs D_r (2 scratch + warm from the
pool member that did best vs D_r) -> RP_r = min intercept -> add the 3 red teams to the pool.
  python psro.py LINEAGE ROUNDS INIT_DEF "WORLD" "DEF_FLAGS" TRAIN_CORE RED_CORES(3, comma) [STOP_HHMM]
Results append to runs/psro_LINEAGE.jsonl."""
import sys, json, glob, os, subprocess, time

lin, rounds, init, world, dflags = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
tcore, rcores = sys.argv[6], sys.argv[7].split(",")
stop = sys.argv[8] if len(sys.argv) > 8 else "0805"  # no new round after this
HARD = sys.argv[9] if len(sys.argv) > 9 else "0820"   # running jobs are killed at this time (partial params already saved)
PY = sys.executable
SMOKE = os.environ.get("PSRO_SMOKE")  # tiny iters for a pipeline check
IT_D, IT_R, ENVS = ("2", "2", "64") if SMOKE else (os.environ.get("PSRO_IT", "1000"), "800", "4096")
POOL_N = int(os.environ.get("PSRO_POOL", "15"))  # newest red teams in the defender's training pool
RF = os.environ.get("PSRO_RF", "0.7")             # fraction of training episodes vs red teams (rest: scripted attackers)


def pool_now():  # all S2 (n=1) red teams on disk, shared across lineages, newest POOL_N
    done = [p for p in glob.glob("runs/S2*RP_*.pkl") if os.path.exists(p[:-4] + ".json")]  # finished teams only
    return sorted(done, key=os.path.getmtime)[-POOL_N:]


def run(name, cores, mem, args):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="1", XLA_PYTHON_CLIENT_MEM_FRACTION=str(mem), PYTHONUNBUFFERED="1")
    return subprocess.Popen(["taskset", "-c", cores, PY, "exp.py"] + args, env=env,
                            stdout=open(f"runs/{name}.out", "w"), stderr=subprocess.STDOUT)


def ok(p, name, others=()):
    now = time.time()
    t = time.localtime(now)
    deadline = time.mktime(t[:3] + (int(HARD[:2]), int(HARD[2:]), 0) + t[6:])
    try:
        p.wait(timeout=max(1.0, deadline - now))
    except subprocess.TimeoutExpired:
        for q in (p,) + tuple(others):
            q.kill()
        open(f"runs/psro_{lin}.jsonl", "a").write(json.dumps(dict(aborted_at=time.strftime("%H:%M"), job=name)) + "\n")
        sys.exit(f"hard stop {HARD}: killed {name}")
    if p.returncode != 0:
        sys.exit(f"{name} failed (exit {p.returncode}); see runs/{name}.out")  # fail fast, no silent retry loop


d_prev = init
for r in range(1, rounds + 1):
    if time.strftime("%H%M") >= stop:
        print("stop time reached", flush=True); break
    dname = f"{lin}_D{r}"
    if SMOKE:
        dname = "smoke_" + dname
    ok(run(dname, tcore, 0.13, ["train_def", dname, "--world", world, "--n", "1", "--iters", IT_D, "--lr", "1e-4",
                                "--envs", ENVS, "--red", ",".join(pool_now()), "--red_frac", RF, "--seed", str(100 * r + 7)]
                               + (["--init", d_prev] if d_prev != "none" else []) + dflags.split()), dname)
    dres = json.load(open(f"runs/{dname}.json"))
    vs = {k[3:]: v for k, v in dres.items() if k.startswith("vs_S2")}
    warm = "runs/" + min(vs, key=vs.get) if vs else None
    dpath = f"runs/{dname}.pkl"
    # pass only the policy-reconstruction flags to train_att
    fl = dflags.split()
    recon = []
    for i, f in enumerate(fl):
        if f in ("--fire_prior", "--lim_scale", "--nd_scale"):
            recon += [f, fl[i + 1]]
    common = ["--world", world, "--n", "1", "--iters", IT_R, "--envs", ENVS, "--def", dpath] + recon
    pre = "smoke_" if SMOKE else ""
    names = [f"{pre}S2_RP_{lin}_D{r}_s1", f"{pre}S2_RP_{lin}_D{r}_s2", f"{pre}S2_RP_{lin}_D{r}_w"]
    ps = [run(names[0], rcores[0], 0.09, ["train_att", names[0], "--seed", str(5000 + 10 * r + 1)] + common),
          run(names[1], rcores[1], 0.09, ["train_att", names[1], "--seed", str(5000 + 10 * r + 2)] + common),
          run(names[2], rcores[2], 0.09, ["train_att", names[2], "--seed", str(5000 + 10 * r + 3)] + common
              + (["--init", warm] if warm else []))]
    for p, nm in zip(ps, names):
        ok(p, nm, tuple(ps))
    rp = {nm: json.load(open(f"runs/{nm}.json"))["def_vs_this_red"] for nm in names}
    worst = min(rp, key=lambda k: rp[k]["intercept"])
    # HEADLINE = fresh_min: red teams trained against THIS round's defender (not in its training pool).
    # pool_min (aux) = min over the pool it trained against (transfer / training opponents).
    rec = dict(round=r, defender=dname, vs_script=dres["vs_script"], train_pool=sorted(vs), pool_min=min(vs.values()) if vs else None,
               warm=warm, fresh={k: {m: v[m] for m in ("intercept", "net", "lim", "leak", "timeout")} for k, v in rp.items()},
               fresh_min=rp[worst]["intercept"], fresh_min_net=rp[worst]["net"], fresh_min_lim=rp[worst]["lim"],
               fresh_min_team=worst, time=time.strftime("%H:%M"))
    open(f"runs/psro_{lin}.jsonl", "a").write(json.dumps(rec) + "\n")
    print(json.dumps(rec), flush=True)
    d_prev = dpath
