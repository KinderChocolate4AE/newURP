"""B: realism sensitivity — does back-diagonal (braking) escape break the cheap lever?
Adds a backward offset (brake) to the goal-constrained lateral-dodge attacker; the
net is committed at the forward-predicted position (ballistic, irreversible). A
braking attacker ends BEHIND net_center -> escapes the committed net, and the
cheap LATERAL ring can't block a backward move. Sweeps retreat freedom D_back."""
import numpy as np
V,TAU,NET_R,KILL_R=20.,0.4,1.5,1.0
A_LAT=30.0; R_LAT=0.5*A_LAT*TAU**2
xh=np.array([1.,0,0]); NC=V*TAU*xh

def lateral_ring(N,planar):
    if N==0: return None
    rr=0.5*(NET_R+R_LAT)
    if planar: return np.array([[NC[0],rr,0.],[NC[0],-rr,0.]])
    ph=np.linspace(0,2*np.pi,N,endpoint=False)
    return np.array([[NC[0],rr*np.cos(p),rr*np.sin(p)] for p in ph])

def vshot(planar,Dback,N,n=12000,seed=5):
    rng=np.random.default_rng(seed)
    if planar: lat=np.stack([np.zeros(n),rng.uniform(-1,1,n)*R_LAT,np.zeros(n)],1)
    else:
        th=rng.uniform(0,2*np.pi,n);mg=R_LAT*np.sqrt(rng.uniform(0,1,n))
        lat=np.stack([np.zeros(n),mg*np.cos(th),mg*np.sin(th)],1)
    dback=rng.uniform(0,Dback,n)
    ep=NC[None]+lat-dback[:,None]*xh[None]
    lim=lateral_ring(N,planar); feas=np.ones(n,bool)
    if lim is not None:
        for L in lim: feas &= ~(np.linalg.norm(ep-L[None],axis=1)<=KILL_R)
    caught=np.linalg.norm(ep-NC[None],axis=1)<=NET_R
    nf=int(feas.sum())
    v=float(caught[feas].mean()) if nf else 1.0
    # bait cost: among feasible ESCAPERS, mean penetration lost (= d_back)
    esc=feas&~caught; baitcost=float(dback[esc].mean()) if esc.any() else 0.0
    return v,baitcost,nf

print(f"R_lat={R_LAT:.2f}m net_r={NET_R} kill_r={KILL_R}  (net committed at forward-predicted pos)")
print("\n(1) cheap lever vs retreat freedom  [planar N=2 ring ; 3D N=8 ring]")
print(f"  {'D_back(m)':>9}{'v_shot(planar,N2)':>18}{'v_shot(3D,N8)':>15}{'bait_cost(m)':>13}")
for Db in (0.0,0.3,0.6,1.0,1.5,2.5):
    vp,_,_=vshot(True,Db,2); vd,bc,_=vshot(False,Db,8)
    print(f"  {Db:>9.1f}{vp:>18.3f}{vd:>15.3f}{bc:>13.2f}")

print("\n(2) to RESTORE v_shot>=0.95 under retreat, must also guard behind (3D ring N):")
print(f"  {'D_back':>7}{'N*(3D,lateral-only ring)':>26}")
for Db in (0.0,0.6,1.5):
    nstar=next((N for N in range(0,30) if vshot(False,Db,N)[0]>=0.95),'>29')
    print(f"  {Db:>7.1f}{str(nstar):>26}")
