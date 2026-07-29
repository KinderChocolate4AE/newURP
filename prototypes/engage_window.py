"""정정: engage_dist 는 '초기 이격'이 아니라 '네트의 요격까지 병진거리'다.
접근하는 공격자에 대해서는  net_travel(t) + v_att*t = separation  을 풀어야 한다.
prototypes/net_forward.py 무수정, read-only."""
import sys, math
sys.path.insert(0, ".")
import numpy as np
from prototypes import net_forward as nf

DESIGNS = [("Baseline",45,60,35),("A",65,90,25),("B",55,70,25),("C",65,60,35),
           ("D*",45,50,25),("E*",35,50,25),("F",25,50,25)]
T_OPEN = 0.13

def solve(t, cum, snp, sep, v_att):
    t = np.asarray(t,float); cum = np.asarray(cum,float); snp = np.asarray(snp,float)
    f = cum + v_att*t - sep                    # 0 에서 요격
    idx = np.where(f >= 0)[0]
    if not len(idx): return (float("nan"),)*3
    i = idx[0]
    if i == 0: return float(t[0]), float(cum[0]), math.sqrt(snp[0]/math.pi)
    w = -f[i-1]/(f[i]-f[i-1])
    ti = float(t[i-1] + w*(t[i]-t[i-1])); ci = float(cum[i-1] + w*(cum[i]-cum[i-1]))
    si = float(snp[i-1] + w*(snp[i]-snp[i-1]))
    return ti, ci, math.sqrt(max(si,0)/math.pi)

for v_att in (20.0, 30.0):
    print(f"===== 공격자 접근속도 {v_att:.0f} m/s · 초기 이격 9.0 m (env x_fire=11, finisher x=2) =====")
    print(f"{'sol':9s} | {'tau':>6s} {'net travel':>10s} {'r_net':>6s} {'model':>6s} | {'a_max':>7s} | {'a=48':>5s} {'a=78':>5s} {'a=137':>6s}")
    print("-"*80)
    for name, th, v0, mg in DESIGNS:
        r = nf.simulate(theta_deg=th, v0=v0, m_block=mg/1000.0, horizon=1.2, engage_dist=20.0)
        tau, trav, rn = solve(r["t"], r["cum_travel"], r["S_NP"], 9.0, v_att)
        amax = 2*rn/tau**2
        flag = "OK" if tau >= T_OPEN else "OVER"
        cells = " ".join(f"{('OK' if 0.5*a*tau**2 <= rn else 'X'):>5s}" for a in (48,78,137))
        print(f"{name:9s} | {tau:6.3f} {trav:10.2f} {rn:6.3f} {flag:>6s} | {amax:7.1f} | {cells}")
    print()
