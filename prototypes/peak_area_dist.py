"""engage_dist 를 불확실성이 아니라 설계축으로 재해석 — 최대 면적 도달 거리 측정.

Xu 2025 Drones 9(3):190 §3.2 / Fig.6: 네트는 t~0.13 s 에 최대 면적에 도달하고
그 뒤로 수축한다. 우리 engage_dist = 20 m 는 최대 면적 이후 지점일 수 있다.
이 스크립트는 각 발사 설계점에서
  (a) 최대 S_NP 시각 t_peak 와 그 때의 중심 병진 거리 travel_peak
  (b) 그 거리에서의 r_net  vs  20 m 에서의 r_net
  (c) 각 거리를 engage_dist 로 썼을 때의 tau_deploy
를 낸다. rho_air 보정값은 그대로 둔다(재보정 없음 — 같은 궤적을 다른 지점에서 읽을 뿐).
READ-ONLY: prototypes/net_forward.py 무수정.
"""
import sys, math
sys.path.insert(0, ".")
import numpy as np
from prototypes import net_forward as nf

DESIGNS = [
    ("Baseline", 45, 60, 35),
    ("A",        65, 90, 25),
    ("B",        55, 70, 25),
    ("C",        65, 60, 35),
    ("D*",       45, 50, 25),
    ("E*",       35, 50, 25),
    ("F",        25, 50, 25),
]

def tau_at(t, cum, dist):
    cum = np.asarray(cum, float); t = np.asarray(t, float)
    if cum[-1] < dist:
        return float("nan")
    return float(np.interp(dist, cum, t))

def r_at(cum, snp, dist):
    cum = np.asarray(cum, float); snp = np.asarray(snp, float)
    if cum[-1] < dist:
        return float("nan")
    return math.sqrt(float(np.interp(dist, cum, snp)) / math.pi)

hdr = f"{'sol':9s} {'th':>3s} {'v0':>3s} {'m':>3s} | {'t_peak':>7s} {'d_peak':>7s} {'r_peak':>7s} | {'tau@20':>7s} {'r@20':>6s} | {'t=0.13':>7s} {'d@0.13':>7s}"
print(hdr); print("-"*len(hdr))
rows = []
for name, th, v0, mg in DESIGNS:
    r = nf.simulate(theta_deg=th, v0=v0, m_block=mg/1000.0, horizon=1.2, engage_dist=20.0)
    t, snp, cum = r["t"], r["S_NP"], r["cum_travel"]
    i = int(np.argmax(snp))
    t_peak, d_peak, r_peak = float(t[i]), float(cum[i]), math.sqrt(float(snp[i])/math.pi)
    tau20, r20 = tau_at(t, cum, 20.0), r_at(cum, snp, 20.0)
    d013 = nf.travel_to_time(t, cum, 0.13)
    rows.append((name, th, v0, mg, t_peak, d_peak, r_peak, tau20, r20, d013))
    print(f"{name:9s} {th:3d} {v0:3d} {mg:3d} | {t_peak:7.3f} {d_peak:7.2f} {r_peak:7.3f} | {tau20:7.3f} {r20:6.3f} | {0.13:7.2f} {d013:7.2f}")

print()
print("=== 포획 성립 R_reach = 0.5*a*tau^2 <= r_net ===")
print(f"{'sol':9s} | {'@ d_peak':>22s} | {'@ 20 m':>22s}")
print(f"{'':9s} | {'tau':>6s} {'r':>6s} {'a_max':>8s} | {'tau':>6s} {'r':>6s} {'a_max':>8s}")
print("-"*62)
for (name, th, v0, mg, t_peak, d_peak, r_peak, tau20, r20, d013) in rows:
    a_peak = 2*r_peak/t_peak**2 if t_peak > 0 else float("inf")
    a20 = 2*r20/tau20**2 if tau20 > 0 else float("inf")
    print(f"{name:9s} | {t_peak:6.3f} {r_peak:6.3f} {a_peak:8.1f} | {tau20:6.3f} {r20:6.3f} {a20:8.1f}")
