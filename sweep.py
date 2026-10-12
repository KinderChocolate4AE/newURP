"""Regime sweep (scripted defense only, no learning). python sweep.py SHARD NSHARDS
Per regime: both / limiter-only for n=1..4, net-only (limiters off). Seeds 100001-4 x 500 eps (screening)."""
import sys, json
from rl import *

LIM_WEAK = "lim_a=25,lim_v=40,kill_r=2.0,lim_tau=0.15"
ATT_STRONG = "att_v=40,att_a=30,att_tau=0.1"
SENS_BAD = "trk_sp=3,trk_sv=3,trk_lag=3"
REGIMES = {
    "R0_nominal": "", "R1_lim_a25": "lim_a=25", "R2_lim_v40": "lim_v=40", "R3_kill2": "kill_r=2.0",
    "R4_lim_tau15": "lim_tau=0.15", "R5_att_v40": "att_v=40", "R6_att_a30": "att_a=30", "R7_att_tau10": "att_tau=0.1",
    "R8_noise3": "trk_sp=3,trk_sv=3", "R9_lag3": "trk_lag=3",
    "C1_limweak": LIM_WEAK, "C2_attstrong": ATT_STRONG, "C3_sensbad": SENS_BAD,
    "C4_limweak_attstrong": LIM_WEAK + "," + ATT_STRONG, "C5_all": LIM_WEAK + "," + ATT_STRONG + "," + SENS_BAD,
    "C6_attstrong_sensbad": ATT_STRONG + "," + SENS_BAD,
}
NOMINAL = {k: v for k, v in vars(P).items() if not k.startswith("_")}

def red(shard, nsh):
    """Short red team (400 it, 1 seed) vs scripted defense n=2 per regime. Reference only (not in selection rule)."""
    for i, (name, spec) in enumerate(REGIMES.items()):
        if i % nsh != shard:
            continue
        for k, v in NOMINAL.items():
            setattr(P, k, v)
        set_world(spec)
        p, _ = train(att_side(), 2, def_script, 2001, 400, log=f"runs/sweepred_{name}.log")
        r = evaluate(2, def_script, red_pol(p), eps=500, seeds=EVAL_SEEDS[:4])
        json.dump(dict(spec=spec, red400=r), open(f"runs/sweepred_{name}.json", "w"), indent=1, default=lambda o: o.item())
        print(name, "red400", round(r["intercept"], 3), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "red":
        red(int(sys.argv[2]), int(sys.argv[3])); sys.exit()
    shard, nsh = int(sys.argv[1]), int(sys.argv[2])
    seeds = EVAL_SEEDS[:4]
    for i, (name, spec) in enumerate(REGIMES.items()):
        if i % nsh != shard:
            continue
        for k, v in NOMINAL.items():
            setattr(P, k, v)
        set_world(spec)
        ev = lambda n, **kw: evaluate(n, def_script, att_script, eps=500, seeds=seeds, **kw)
        out = dict(spec=spec, netonly=ev(2, use_lim=False))
        for n in (1, 2, 3, 4):
            out[f"both_n{n}"] = ev(n)
            out[f"limonly_n{n}"] = ev(n, use_net=False)
        json.dump(out, open(f"runs/sweep_{name}.json", "w"), indent=1, default=lambda o: o.item())
        print(name, {k: round(v["intercept"], 3) for k, v in out.items() if k != "spec"}, flush=True)
