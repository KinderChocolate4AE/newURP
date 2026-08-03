import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"] = False
NAVY="#1E2761"; SLATE="#111111"; GREEN="#2F7A4F"; RED="#B3423A"

fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=220)
ax.axis("off"); ax.set_aspect("equal")
ax.set_xlim(0, 17.6); ax.set_ylim(0, 10.0)

ax.text(0.15, 9.50, "네트를 쏘고 실제로 덮이기까지  τ 초가 걸린다",
        fontsize=15.0, color=NAVY, fontweight="bold")
ax.text(0.15, 8.80, "그 사이 공격자는 옆으로  w = ½ · a · τ²  만큼 빠져나갈 수 있다",
        fontsize=12.2, color=SLATE)

def panel(y0, cy, rho, w_r, ok, head, sub):
    C = GREEN if ok else RED
    ax.add_patch(Rectangle((0.10, y0), 17.40, 3.85,
                           fc=("#F2F8F4" if ok else "#FCF2F1"), ec="none", zorder=0))
    ax.text(0.50, y0 + 3.32, head, fontsize=14.0, color=C, fontweight="bold")
    ax.text(0.50, y0 + 2.72, sub, fontsize=11.6, color=SLATE)
    ax.add_patch(Circle((1.30, cy), 0.32, fc="#FFFFFF", ec=NAVY, lw=1.9, zorder=4))
    ax.add_patch(FancyArrowPatch((1.76, cy), (5.70, cy), arrowstyle="-|>",
                                 mutation_scale=15, color=NAVY, lw=1.8, zorder=4))
    ax.text(3.65, cy + 0.36, "네트 발사", ha="center", fontsize=11.0, color=SLATE)
    ax.text(3.65, cy - 0.92, "τ 초 뒤 판정", ha="center", fontsize=10.5, color=SLATE, style="italic")
    cx = 9.60
    ax.add_patch(Circle((cx, cy), w_r, fc=C, alpha=0.20, ec="none", zorder=2))
    ax.add_patch(Circle((cx, cy), w_r, fc="none", ec=C, lw=1.9, ls=(0, (4, 2)), zorder=3))
    ax.add_patch(Circle((cx, cy), rho, fc="none", ec=NAVY, lw=2.4, zorder=4))
    ax.plot([cx], [cy], "o", ms=5, color=NAVY, zorder=5)
    ax.annotate("네트가 덮는 반경 ρ", xy=(cx + rho*0.71, cy + rho*0.71),
                xytext=(11.90, cy + 1.05), fontsize=10.8, color=NAVY, va="center",
                arrowprops=dict(arrowstyle="-", color=NAVY, lw=0.9), zorder=6)
    ax.annotate("공격자가 빠져나가는 거리 w", xy=(cx - w_r*0.71, cy - w_r*0.71),
                xytext=(11.90, cy - 1.40), fontsize=10.8, color=C, va="center",
                arrowprops=dict(arrowstyle="-", color=C, lw=0.9), zorder=6)

panel(4.55, 5.90, 1.25, 0.70, True,
      "w < ρ   →   네트 안에 갇힌다", "느린 공격자 — 네트 드론이 혼자서 잡는다")
panel(0.30, 2.05, 1.25, 1.70, False,
      "w > ρ   →   네트 밖으로 빠져나간다", "민첩한 공격자 — 몰아주지 않으면 못 잡는다")

fig.savefig("fig_mech.png", bbox_inches="tight", facecolor="white", pad_inches=0.04)
print("ok mech")
