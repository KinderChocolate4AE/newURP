"""포획 확률 스윕 곡선 — x = 공격 드론 최대 기동 가속도, y = 막아낼 확률.

정용주 교수 피드백 1번. fig_line(막대 2칸)의 연속판이며 같은 슬롯에 그대로 들어간다.

**곡선이 새로 보여준 것**: 붕괴는 a* = 39.3 이 아니라 그 **앞**에서 시작한다.
  · 경계 1 (도달집합) a* = 2ρ/τ² = 39.3 -- 이 위에서는 네트 포획이 원리적으로 불가능.
                      실측 479판 중 0회, 예외 없음.
  · 경계 2 (겨냥)     a*(ψ) = 2d(tanθ − ψ)/τ². slew_audit 이 잰 잔여 조준각
                      중앙값 ψ = 4.26° 를 넣으면 **25.8**. 곡선의 50% 교차점 = **24.0**.
                      독립적으로 잰 두 값이 7% 안에서 만난다.
  · 그 사이(≈24~39) = 물리는 허용하는데 손튜닝이 못 잡는 구간.

**손튜닝 기준선의 곡선이지 학습 정책의 곡선이 아니다** — 표시에 반드시 그렇게 쓴다.
"""
import json
import math
import os
import sys

# 그림의 숫자는 **감사된 코드**에서 나온다 (경계값을 여기서 다시 적지 않는다).
# 이 파일은 <repo>/docs/ppt/ 에 있다고 가정하고 저장소 루트를 거슬러 올라간다.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.environ.get("NEWURP_ROOT") or os.path.abspath(
    os.path.join(_HERE, "..", ".."))
if not os.path.isdir(os.path.join(_ROOT, "shepherd")):
    _ROOT = "/tmp/newURP"                                    # 샌드박스 폴백
sys.path.insert(0, _ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
NAVY = "#1E2761"; SLATE = "#111111"; AMBER = "#D97706"; LIGHT = "#EEF3FB"
GREEN = "#2F7A4F"; RED = "#B3423A"; GREY = "#111111"; TEAL = "#1F7A8C"

from shepherd.m4_config import THREAT_BRACKET, m4_config
from shepherd.scripts.curve_sweep import (PSI_MED_DEG, _band_bounds, band_of,
                                          summarize_curve)

_CFG = m4_config()
LO, HI = (float(v) for v in THREAT_BRACKET["physics.a_att_max"])
PSI_DEG = PSI_MED_DEG
A_PSI, ASTAR = _band_bounds(_CFG)
CAP = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
EDGES = list(np.linspace(LO, ASTAR, 5)) + list(np.linspace(ASTAR, HI, 5))[1:]


def wilson(k, n, z=1.96):   # noqa: 그림 전용 사본 (curve_sweep 와 동일 식)
    if n == 0:
        return 0.0, 0.0, 0.0
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def load(path):
    with open(path) as f:
        d = json.load(f)
    return d["records"], d["n_done"]


def curve(rec, keyfn):
    xs, ps, los, his, ns = [], [], [], [], []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        sel = [r for r in rec if a <= r["a_att"] < b or (b == EDGES[-1] and r["a_att"] == b)]
        k = sum(1 for r in sel if keyfn(r))
        p, l, h = wilson(k, len(sel))
        xs.append((a + b) / 2); ps.append(p); los.append(l); his.append(h); ns.append(len(sel))
    return np.array(xs), np.array(ps), np.array(los), np.array(his), ns


def cross50(x, p):
    for i in range(len(p) - 1):
        if p[i] >= 0.5 > p[i + 1]:
            return x[i] + (x[i + 1] - x[i]) * (p[i] - 0.5) / (p[i] - p[i + 1])
    return float("nan")


RESULTS = os.path.join(_ROOT, "results")
hold, n_hold = load(os.path.join(RESULTS, "curve_hold.json"))
itc, n_itc = load(os.path.join(RESULTS, "curve_intercept.json"))

fig, ax = plt.subplots(figsize=(12.4, 2.55), dpi=220)
fig.subplots_adjust(left=0.058, right=0.992, top=0.775, bottom=0.335)

# ── 세 구간 ───────────────────────────────────────────────────────────────
ax.axvspan(LO, A_PSI, color="#EAF3EC", zorder=0)
ax.axvspan(A_PSI, ASTAR, color="#FBEEDB", zorder=0)
ax.axvspan(ASTAR, HI, color=NAVY, alpha=0.085, zorder=0)

ax.axvline(A_PSI, color=TEAL, lw=2.6, ls=(0, (5, 2.6)), zorder=6)
ax.axvline(ASTAR, color=AMBER, lw=3.0, zorder=6)

ax.text(A_PSI - 0.7, 1.14, f"a*(ψ = 4.3°) = {A_PSI:.0f}", ha="right", va="bottom",
        fontsize=11.5, fontweight="bold", color=TEAL)
ax.text(A_PSI - 0.7, 1.025, "겨냥 정밀도가 정하는 경계", ha="right", va="bottom",
        fontsize=8.8, color=TEAL)
ax.text(ASTAR + 0.8, 1.14, f"a* = {ASTAR:.1f}", ha="left", va="bottom",
        fontsize=12.5, fontweight="bold", color=AMBER)
ax.text(ASTAR + 0.8, 1.025, "도달 범위가 정하는 경계 · 이론 상한", ha="left", va="bottom",
        fontsize=8.8, color=AMBER)

ax.text((LO + A_PSI) / 2, 0.50, "손튜닝으로도\n잡힌다", ha="center", va="center",
        fontsize=10.2, color=GREEN, fontweight="bold", linespacing=1.35)
_band = summarize_curve({"mode": "hold", "records": hold}, cfg=_CFG)["by_band"]
_p_aim = _band["BAND_AIM"]["net_capture"]["p"]
ax.text((A_PSI + ASTAR) / 2, 0.62, "물리는 허용하는데\n손튜닝이 못 잡는다", ha="center",
        va="center", fontsize=10.2, color="#B26A00", fontweight="bold", linespacing=1.35)
ax.text((A_PSI + ASTAR) / 2, 0.36, f"{100 * _p_aim:.1f} %", ha="center", va="center",
        fontsize=13, color="#B26A00", fontweight="bold")
ax.text((ASTAR + HI) / 2, 0.86, "네트로 붙잡는 것은 원리적으로 불가능  —  한 번도 없음",
        ha="center", va="center", fontsize=10.8, color=NAVY, fontweight="bold")

SERIES = [
    (hold, lambda r: r["label"] in CAP, GREEN, "o", "-",
     "네트로 붙잡기  ·  기체 회수 가능"),
    (itc, lambda r: r["label"] in CAP or r["label"] == "HARD_KILL", RED, "s", "--",
     "부딪쳐 떨어뜨리기 포함  ·  기체 파손"),
]
x50 = None
for rec, fn, col, mk, ls, lab in SERIES:
    x, p, lo, hi, ns = curve(rec, fn)
    ax.fill_between(x, lo, hi, color=col, alpha=0.16, lw=0, zorder=2)
    ax.plot(x, p, ls, color=col, lw=2.4, marker=mk, ms=5.6, mec="white", mew=1.2,
            zorder=4, label=lab)
    if col == GREEN:
        x50 = cross50(x, p)

# ── 관측된 붕괴점 ─────────────────────────────────────────────────────────
if x50 == x50:
    ax.plot([x50], [0.5], "*", ms=15, color=TEAL, mec="white", mew=1.2, zorder=8)
    ax.annotate(f"관측 붕괴점 {x50:.1f}", xy=(x50, 0.5), xytext=(x50 - 5.6, 0.16),
                fontsize=9.4, color=TEAL, fontweight="bold", ha="right",
                arrowprops=dict(arrowstyle="-", color=TEAL, lw=1.1), zorder=8)

# ── 실제 기체가 어디 있는지 ────────────────────────────────────────────────
for xv, lab, ha in [(11, "실험 문헌의 표적", "left"), (30, "우리가 쓰던 가정값", "center"),
                    (48, "무장 FPV", "center"), (78, "5인치 경주용 FPV", "right")]:
    ax.plot([xv], [-0.055], "o", ms=6.2, color="white", mec=NAVY, mew=1.9,
            clip_on=False, zorder=9)
    ax.text(xv, -0.115, f"{xv}\n{lab}", ha=ha, va="top", fontsize=8.7,
            color=SLATE, linespacing=1.3, clip_on=False, zorder=9)

ax.set_xlim(LO, HI); ax.set_ylim(0.0, 1.0)
ax.set_yticks([0, 0.5, 1.0]); ax.set_yticklabels(["0 %", "50", "100 %"],
                                                 fontsize=9.2, color=SLATE)
ax.set_ylabel("무력화 확률", fontsize=10.0, color=SLATE, labelpad=7)
ax.set_xlabel("공격자 최대 기동 가속도  (m/s²)", fontsize=10.0,
              color=SLATE, labelpad=30)
ax.set_xticks([])
for sp in ("top", "right", "bottom"):
    ax.spines[sp].set_visible(False)
ax.spines["left"].set_color("#C8D2E4")
ax.grid(axis="y", color="#D9E2F0", lw=0.8, zorder=1)
ax.set_axisbelow(True)

leg = ax.legend(loc="upper right", bbox_to_anchor=(0.995, 0.62), fontsize=9.2,
                frameon=True, facecolor="white", edgecolor="#D5DEEC",
                framealpha=0.96, handlelength=2.2, borderpad=0.45)
leg.set_zorder(10)

ax.text(0.995, -0.52, f"띠 = 95 % 신뢰구간   ·   손튜닝 기준선 {n_hold + n_itc:,} 판",
        transform=ax.transAxes, ha="right", va="top", fontsize=9.0, color=GREY)

fig.savefig(os.path.join(_HERE, "fig_curve.png"), facecolor="white")

print(f"a*      (ψ=0)        = {ASTAR:.2f}")
print(f"a*(ψ={PSI_DEG}°)  예측  = {A_PSI:.2f}")
print(f"곡선 50% 교차 관측     = {x50:.2f}   (편차 {100 * abs(x50 - A_PSI) / A_PSI:.1f} %)")
for rec, fn, col, mk, ls, lab in SERIES:
    x, p, lo, hi, ns = curve(rec, fn)
    print(f"\n{lab}   (n={len(rec)})")
    for xi, pi, li, hi_, ni in zip(x, p, lo, hi, ns):
        print(f"  a≈{xi:5.1f}  n={ni:4d}  p={pi:.3f}  [{li:.3f}, {hi_:.3f}]")
w, h = fig.get_size_inches()
print(f"\nok curve  aspect={w / h:.3f}")
