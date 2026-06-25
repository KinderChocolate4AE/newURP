"""Corridor exchange-frontier (newURP M2 first CLEAN result, numpy, torch-free).

Goal-constrained reactive attacker (default): constant forward speed v toward the
protected point, lateral dodge bounded by a_lat_max, avoids kamikaze kill-radii.
Net commits on the forward path (net_center = predicted forward pos). Cheap
kamikaze limiters guard the LATERAL escape ring (NOT the forward/net-ward path).
v_shot = frac of feasible (non-suicidal) lateral dodges still caught by the net;
best-escape attacker => v_shot_worst=1 iff NO feasible lateral escape exists.

CAVEAT (defender-optimistic): forbids backward/diagonal retreat (real pilot would
bait + back-diagonal escape + exploit reload). That richer adversary = S13.
"""
import numpy as np
V, TAU, NET_R, KILL_R = 20.0, 0.4, 1.5, 1.0
xhat = np.array([1.,0,0])

def lateral_accels(a_lat_max, planar, n=6000, seed=3):
    rng = np.random.default_rng(seed)
    if planar:                                  # dodge in y only (±y)
        ay = rng.uniform(-1,1,n)*a_lat_max
        a = np.stack([np.zeros(n), ay, np.zeros(n)],1)
    else:                                       # dodge anywhere in y-z disk
        th = rng.uniform(0,2*np.pi,n); mag = a_lat_max*np.sqrt(rng.uniform(0,1,n))
        a = np.stack([np.zeros(n), mag*np.cos(th), mag*np.sin(th)],1)
    a[0]=0.0
    return a

def ring_limiters(N, ncx, r_ring, planar):
    if N==0: return None
    if planar:                                  # ±y pair(s)
        ys = [r_ring,-r_ring][:N] if N<=2 else np.linspace(-r_ring,r_ring,N)
        return np.array([[ncx,y,0.] for y in np.atleast_1d(ys)])
    ph = np.linspace(0,2*np.pi,N,endpoint=False)
    return np.array([[ncx, r_ring*np.cos(p), r_ring*np.sin(p)] for p in ph])

def v_shot(a_lat_max, N, planar, n=6000):
    x=np.zeros(3); a=lateral_accels(a_lat_max,planar,n)
    nc = x + V*TAU*xhat
    ep = x[None]+V*TAU*xhat[None]+0.5*a*TAU**2
    R_lat = 0.5*a_lat_max*TAU**2
    lim = ring_limiters(N, nc[0], 0.5*(NET_R+R_lat), planar)
    feas=np.ones(n,bool)
    if lim is not None:
        s=np.linspace(0,TAU,20)[:,None]
        for i in range(n):
            pts=x[None]+V*s*xhat[None]+0.5*a[i][None]*s**2
            if (np.linalg.norm(pts[:,None,:]-lim[None],axis=2)<=KILL_R).any(): feas[i]=False
    caught=np.linalg.norm(ep-nc[None],axis=1)<=NET_R
    nf=int(feas.sum())
    if nf==0: return 1.0,1.0,0,R_lat
    fc=caught[feas]; return float(fc.mean()),(1.0 if fc.all() else 0.0),nf,R_lat

for planar in (True,False):
    tag = "PLANAR (±y dodge)" if planar else "3D (y-z disk dodge)"
    print(f"\n=== {tag} ===  v={V} tau={TAU} net_r={NET_R} kill_r={KILL_R}")
    a=30.0; print(f"(1) v_shot vs N  (a_lat_max={a}, R_lat={0.5*a*TAU**2:.2f}m)")
    print(f"  {'N':>3}{'v_soft':>8}{'worst':>6}{'n_feas':>7}")
    for N in ([0,1,2,3,4] if planar else [0,2,3,4,5,6,8,10]):
        s,w,nf,_=v_shot(a,N,planar); print(f"  {N:>3}{s:>8.3f}{w:>6.0f}{nf:>7}")
    print("(2) N*(a_lat_max) for v_shot>=0.95:")
    for al in (16,22,28,34,40):
        Ns=range(0,13)
        nstar=next((N for N in Ns if v_shot(al,N,planar)[0]>=0.95),None)
        print(f"   a_lat={al:>3}  R_lat={0.5*al*TAU**2:>4.2f}  N*={nstar}")
