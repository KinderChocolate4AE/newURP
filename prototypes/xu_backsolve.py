"""A1 추정 v2 — brentq NaN 브래킷 버그 수정 (고항력에서 네트가 거리에 도달 못함)."""
import sys, math
sys.path.insert(0, ".")
import numpy as np
from prototypes import net_forward as nf

S_UAV = 2.0
C_PAPER = {"Test":2.3174,"A":2.4802,"B":2.4399,"C":2.4359,"D":2.4257,"E":2.3904,"F":2.3041}
DESIGN = {"Test":(45,60,35),"A":(65,90,25),"B":(55,70,25),"C":(65,60,35),
          "D":(45,50,25),"E":(35,50,25),"F":(25,50,25)}
paper = {k: S_UAV/(1.0-math.log(C)) for k, C in C_PAPER.items()}

def snp_at(th, v, mg, dist, rho, horizon=3.0):
    r = nf.simulate(theta_deg=th, v0=v, m_block=mg/1000.0, horizon=horizon,
                    engage_dist=dist, rho_air=rho)
    cum, snp = np.asarray(r["cum_travel"]), np.asarray(r["S_NP"])
    if not len(cum) or cum[-1] < dist: return float("nan")
    return float(np.interp(dist, cum, snp))

RHOS = [0.3,0.6,1.0,1.3,1.513,1.8,2.2,2.8,3.5,4.5,6.0]
print(f"{'dist':>5s} {'rho*':>6s} {'base':>6s} | " + " ".join(f"{k:>6s}" for k in "ABCDEF")
      + f" | {'MAE%':>6s} {'스프레드':>8s} {'순서':>4s}")
print("-"*92)
order_paper = sorted("ABCDEF", key=lambda k: paper[k])
spread_paper = paper["A"]/paper["F"]
best = None
for dist in (7, 9, 12, 15, 20, 25, 30):
    # baseline 이 12.53 에 가장 가까운 rho 찾기 (NaN 건너뜀)
    cand = [(abs(snp_at(45,60,35,dist,r)-paper["Test"]), r) for r in RHOS]
    cand = [(e, r) for e, r in cand if np.isfinite(e)]
    if not cand: print(f"{dist:5.0f}  (전 rho 에서 도달 실패)"); continue
    err0, rho = min(cand)
    base = snp_at(45,60,35,dist,rho)
    vals = [snp_at(*DESIGN[k], dist, rho) for k in "ABCDEF"]
    if any(not np.isfinite(v) for v in vals):
        print(f"{dist:5.0f} {rho:6.3f} {base:6.2f} |  일부 설계점 미도달"); continue
    mae = float(np.mean([abs(v-paper[k])/paper[k]*100 for v,k in zip(vals,"ABCDEF")]))
    order_sim = sorted("ABCDEF", key=lambda k: vals["ABCDEF".index(k)])
    sp = max(vals)/min(vals)
    ok = "O" if order_sim == order_paper else "X"
    print(f"{dist:5.0f} {rho:6.3f} {base:6.2f} | " + " ".join(f"{v:6.2f}" for v in vals)
          + f" | {mae:6.1f} {sp:8.2f} {ok:>4s}")
    if best is None or mae < best[1]: best = (dist, mae, rho, ok)

print("\n논문 값" + " "*13 + "| " + " ".join(f"{paper[k]:6.2f}" for k in "ABCDEF")
      + f" | {0.0:6.1f} {spread_paper:8.2f}")
print(f"논문 순서: {' < '.join(order_paper)}")
if best:
    print(f"\n>>> 최소 MAE 거리 {best[0]} m (MAE {best[1]:.1f}%, rho {best[2]:.3f}, 순서 {best[3]})")
