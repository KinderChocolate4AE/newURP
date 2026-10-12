"""Apply the S2 selection rule (LAB_LOG 03:08) to runs/sweep_*.json."""
import json, glob, os
rows = []
for f in sorted(glob.glob("runs/sweep_*.json")):
    d = json.load(open(f)); name = os.path.basename(f)[6:-5]
    net = d["netonly"]["intercept"] * 100
    for n in (1, 2, 3, 4):
        both = d[f"both_n{n}"]["intercept"] * 100; lim = d[f"limonly_n{n}"]["intercept"] * 100
        dnet, dlim = both - lim, both - net
        ok = 40 <= both <= 80 and dnet >= 10 and dlim >= 10
        V = max(0, 40 - both) + max(0, both - 80) + max(0, 10 - dnet) + max(0, 10 - dlim)
        rows.append((name, n, both, net, lim, dnet, dlim, ok, V))
print(f"{'regime':24s} n  both  net1  lim1  dNet  dLim ok   V")
for r in rows:
    print(f"{r[0]:24s} {r[1]} {r[2]:5.1f} {r[3]:5.1f} {r[4]:5.1f} {r[5]:5.1f} {r[6]:5.1f} {'Y' if r[7] else '.'} {r[8]:5.1f}")
ok = [r for r in rows if r[7]]
if ok:
    best = max(ok, key=lambda r: (round(min(r[5], r[6])), -abs(r[2] - 60), -r[1]))
    print("SELECTED (rule satisfied):", best)
else:
    best = min(rows, key=lambda r: r[8]); print("NONE satisfy; min violation:", best)
