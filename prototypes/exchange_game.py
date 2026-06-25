"""A2: repeated-exchange proxy -> first exchange-frontier (numpy, torch-free).

Episode: attacker advances toward the protected point; defender (K finite nets +
N cheap kamikaze limiters = shaping) fires when in range. A committed net catches
w.p. v_shot(N) (from the corridor model); else the attacker BAITS/brakes (escapes,
retreats bait_cost, defender loses 1 net). Finite TIME BUDGET (attacker can't bait
forever). P_penetration = reaches target within budget. Resource = N*c_lim +
nets_fired*c_net (limiter 20x cheaper than a net).

Key comparison: SHAPING arm (fixed K, sweep cheap limiters N) vs BUY-NETS arm
(N=0, sweep expensive nets K). If shaping is lower-left on (resource, P_pen), cheap
shaping beats buying nets = the exchange-economics contribution.
"""
import numpy as np, sys
sys.path.insert(0,"scripts"); from corridor_frontier import v_shot as corridor_vshot

D0, STEP, BAIT, NET_RANGE, T_BUDGET = 60., 6., 10., 36., 16
C_NET, C_LIM, A_LAT = 20.0, 1.0, 30.0

def vshot_of_N(N): return corridor_vshot(A_LAT, N, planar=False, n=3000)[0]  # 3D

def episode(K, N, v, rng):
    d, k, fired = D0, K, 0
    for _ in range(T_BUDGET):
        if d <= 0: return True, fired                      # penetrated
        if d <= NET_RANGE and k > 0:                       # defender fires
            fired += 1; k -= 1
            if rng.random() < v: return False, fired       # caught
            d += BAIT                                       # baited/escaped (retreat)
        else:
            d -= STEP                                       # advance
    return (d <= 0), fired                                 # budget out

def run(K, N, eps=4000, seed=0):
    v = vshot_of_N(N); rng = np.random.default_rng(seed)
    pen = 0; fsum = 0
    for _ in range(eps):
        p, f = episode(K, N, v, rng); pen += p; fsum += f
    Ppen = pen/eps; Efired = fsum/eps
    return Ppen, N*C_LIM + Efired*C_NET, v

print(f"D0={D0} step={STEP} bait={BAIT} net_range={NET_RANGE} T={T_BUDGET} c_net={C_NET} c_lim={C_LIM}")
print("\nSHAPING arm (K=2 nets fixed, sweep cheap limiters N):")
print(f"  {'N':>3}{'v_shot':>8}{'P_pen':>8}{'E[resource]':>12}")
shap=[]
for N in (0,2,4,6,8,10):
    pp,res,v=run(2,N); shap.append((res,pp)); print(f"  {N:>3}{v:>8.2f}{pp:>8.3f}{res:>12.1f}")
print("\nBUY-NETS arm (N=0 shaping, sweep expensive nets K):")
print(f"  {'K':>3}{'v_shot':>8}{'P_pen':>8}{'E[resource]':>12}")
buy=[]
for K in (1,2,3,4,6,8):
    pp,res,v=run(K,0); buy.append((res,pp)); print(f"  {K:>3}{v:>8.2f}{pp:>8.3f}{res:>12.1f}")

# figure
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(6.5,4.6))
    s=np.array(shap); b=np.array(buy)
    ax.plot(b[:,0],b[:,1],'s--',color="#c44",label='buy more nets (no shaping)')
    ax.plot(s[:,0],s[:,1],'o-',color="#27a",label='cheap-limiter shaping (K=2)')
    ax.set_xlabel('E[resource spent]  (nets×20 + limiters×1)'); ax.set_ylabel('P_penetration')
    ax.set_title('Exchange frontier: shaping vs buying nets\n(repeated bait/exhaustion proxy, lower-left = better)')
    ax.legend(); ax.grid(alpha=.3)
    for N,(r,p) in zip((0,2,4,6,8,10),shap): ax.annotate(f"N={N}",(r,p),fontsize=7,xytext=(3,3),textcoords='offset points')
    fig.tight_layout(); out="data/m2_exchange_game_frontier.png"; fig.savefig(out,dpi=130)
    print("\nFIGURE:",out)
except Exception as e: print("no fig:",e)
