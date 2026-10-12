"""Experiment CLI. Results -> runs/<name>.json (+ .pkl params, .log training curve).
  python exp.py baseline
  python exp.py train_def NAME --n 2 --iters 200 [--red runs/X.pkl --red_frac 0.5] [--init runs/Y.pkl] [--nores]
  python exp.py train_att NAME --n 2 --iters 200 [--def runs/Y.pkl | script] [--nores]
  python exp.py eval NAME --n 2 --def runs/Y.pkl|script --att runs/X.pkl|script [--nores]
"""
import argparse, json, os, time
from rl import *

os.makedirs("runs", exist_ok=True)


def dump(name, obj):
    json.dump(obj, open(f"runs/{name}.json", "w"), indent=1, default=lambda o: o.item())
    print(name, json.dumps(obj, default=lambda o: o.item()), flush=True)


def _dside(n, residual=True):
    return def_side(n, residual, fire_prior=a.fire_prior, lim_scale=a.lim_scale, nd_scale=a.nd_scale)


def mix_members(spec, n):  # "mix:script,runs/A.pkl,..."; "script" member = zero residual
    ps = [load(x) for x in spec[4:].split(",") if x != "script"]
    if "script" in spec[4:].split(","):
        ps = [jax.tree.map(jnp.zeros_like, ps[0])] + ps
    return ps


def defpol(path, n, residual=True):
    if path and path.startswith("mix:"):
        return mix_policy(_dside(n, residual), mix_members(path, n))
    return def_script if path in (None, "script") else policy_fn(def_side(n, residual, fire_prior=a.fire_prior,
                                                                          lim_scale=a.lim_scale, nd_scale=a.nd_scale), load(path))


def attpol(path):
    return att_script if path in (None, "script") else red_pol(load(path))


ap = argparse.ArgumentParser()
ap.add_argument("cmd"); ap.add_argument("name", nargs="?", default="baseline")
ap.add_argument("--n", type=int, default=2); ap.add_argument("--iters", type=int, default=200)
ap.add_argument("--seed", type=int, default=1); ap.add_argument("--envs", type=int, default=2048)
ap.add_argument("--red"); ap.add_argument("--red_frac", type=float, default=0.0)
ap.add_argument("--init"); ap.add_argument("--def_", "--def", dest="def_"); ap.add_argument("--att")
ap.add_argument("--nores", action="store_true"); ap.add_argument("--lr", type=float, default=3e-4)
ap.add_argument("--no_net", action="store_true"); ap.add_argument("--no_lim", action="store_true")
ap.add_argument("--eps", type=int, default=1000)
ap.add_argument("--world", default="")
ap.add_argument("--fire_prior", type=float, default=3.0); ap.add_argument("--lim_scale", type=float, default=1.0)
ap.add_argument("--nd_scale", type=float, default=1.0); ap.add_argument("--c_lim", type=float, default=0.0)
a = ap.parse_args()
WORLD_OVR = set_world(a.world)
t0 = time.time()
un, ul = not a.no_net, not a.no_lim

if a.cmd == "baseline":
    out = {}
    for n in (1, 2, 3, 4):
        out[f"n{n}_mix"] = evaluate(n, def_script, att_script, eps=a.eps)
        for k in range(3):
            out[f"n{n}_kind{k}"] = evaluate(n, def_script, att_script, eps=a.eps, kind=k)
        out[f"n{n}_netonly"] = evaluate(n, def_script, att_script, eps=a.eps, use_lim=False)
        out[f"n{n}_limonly"] = evaluate(n, def_script, att_script, eps=a.eps, use_net=False)
        print(n, out[f"n{n}_mix"], flush=True)
    dump(a.name, out)

elif a.cmd == "train_def":
    side = def_side(a.n, not a.nores, fire_prior=a.fire_prior, lim_scale=a.lim_scale, nd_scale=a.nd_scale, c_lim=a.c_lim)
    reds = [load(x) for x in a.red.split(",")] if a.red else []
    opp = make_opponent("def", att_side(), reds)
    init = load(a.init) if a.init else None
    p, h = train(side, a.n, opp, a.seed, a.iters, num_envs=a.envs, red_frac=a.red_frac if a.red else 0.0, n_red=max(len(reds), 1),
                 init=init, log=f"runs/{a.name}.log", save=f"runs/{a.name}.pkl", lr=a.lr, use_net=un, use_lim=ul)
    pol = policy_fn(side, p)
    res = dict(args=vars(a), train_sec=time.time() - t0,
               vs_script=evaluate(a.n, pol, att_script, eps=a.eps, use_net=un, use_lim=ul))
    for x, rp in zip(a.red.split(",") if a.red else [], reds):
        res["vs_" + os.path.basename(x)] = evaluate(a.n, pol, red_pol(rp), eps=a.eps, use_net=un, use_lim=ul)["intercept"]
    dump(a.name, res)

elif a.cmd == "train_att":
    dside = def_side(a.n, not a.nores, fire_prior=a.fire_prior, lim_scale=a.lim_scale, nd_scale=a.nd_scale)
    opp = defpol(a.def_, a.n, not a.nores)
    p, h = train(att_side(), a.n, opp, a.seed, a.iters, num_envs=a.envs, init=load(a.init) if a.init else None,
                 log=f"runs/{a.name}.log", save=f"runs/{a.name}.pkl", lr=a.lr, use_net=un, use_lim=ul)
    res = dict(args=vars(a), train_sec=time.time() - t0,
               def_vs_this_red=evaluate(a.n, defpol(a.def_, a.n, not a.nores), red_pol(p), eps=a.eps, use_net=un, use_lim=ul))
    dump(a.name, res)

elif a.cmd == "eval":
    dump(a.name, dict(args=vars(a), res=evaluate(a.n, defpol(a.def_, a.n, not a.nores), attpol(a.att), eps=a.eps,
                                                  use_net=un, use_lim=ul)))
