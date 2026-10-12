"""Same defender, same red teams: both / net off (limiter only) / limiter off (net only).
python netcmp.py OUT WORLD DEF.pkl|script "FLAGS" RED1.pkl,RED2.pkl,... [eps]"""
import sys, json
from rl import *

out, world, dpath, flags, reds = sys.argv[1:6]
eps = int(sys.argv[6]) if len(sys.argv) > 6 else 1000
set_world(world)
fl = flags.split()
kw = {fl[i][2:]: float(fl[i + 1]) for i in range(0, len(fl), 2)}
dpol = def_script if dpath == "script" else policy_fn(def_side(1, **kw), load(dpath))
res = {}
for r in ["script"] + reds.split(","):
    apol = att_script if r == "script" else red_pol(load(r))
    res[r] = {cfg: evaluate(1, dpol, apol, eps=eps, use_net=un, use_lim=ul)
              for cfg, un, ul in (("both", True, True), ("lim_only", False, True), ("net_only", True, False))}
    print(r, {c: (round(v["intercept"], 3), round(v["net"], 3), round(v["timeout"], 3)) for c, v in res[r].items()}, flush=True)
json.dump(dict(world=world, defender=dpath, flags=flags, res=res), open(out, "w"), indent=1, default=lambda o: o.item())
