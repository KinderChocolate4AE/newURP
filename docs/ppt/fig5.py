import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Wedge, FancyBboxPatch
plt.rcParams["font.family"]="Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"]=False
NAVY="#1E2761"; ICE="#CADCFC"; SLATE="#111111"; AMBER="#D97706"; GREEN="#2F7A4F"; RED="#B3423A"

fig, ax = plt.subplots(figsize=(10.2, 4.0), dpi=220)
# 보호 자산
ax.add_patch(Circle((0,0),1.0,fc="#E6EDF8",ec=NAVY,lw=1.6,zorder=2))
ax.plot(0,0,"*",ms=18,color=NAVY,zorder=3)
ax.text(0,-1.45,"보호 자산",ha="center",fontsize=11,color=NAVY,fontweight="bold",zorder=8)
# 네트 드론 + 발사 원뿔
ax.add_patch(Wedge((3.0,0),2.6,-15,15,fc=AMBER,alpha=0.22,ec="none",zorder=1))
ax.add_patch(Circle((3.0,0),0.52,fc="#FFFFFF",ec=NAVY,lw=2.4,zorder=5))
ax.text(3.55,1.02,"네트 드론",ha="left",va="center",fontsize=11,color=NAVY,fontweight="bold",zorder=8)
ax.text(5.72,-0.92,"네트를 쏠 수 있는 범위",ha="center",fontsize=9.3,color=AMBER,zorder=8)
# 경로제한 드론 -- **진입 방향에 수직인 3차원 원** (뒤쪽 절반은 옅게 = 원근)
from matplotlib.patches import Arc
CX, RA, RB = 8.5, 1.25, 3.05          # 원을 비스듬히 본 타원 (가로 단축)
ax.add_patch(Arc((CX,0),2*RA,2*RB,angle=0,theta1=-90,theta2=90,
                 ec=NAVY,lw=1.6,ls=(0,(4,3)),alpha=0.85,zorder=2))
ax.add_patch(Arc((CX,0),2*RA,2*RB,angle=0,theta1=90,theta2=270,
                 ec=NAVY,lw=1.4,ls=(0,(3,4)),alpha=0.30,zorder=2))
for (x,y,front) in [(CX,RB,True),(CX+RA,0.0,True),(CX,-RB,True),(CX-RA,0.0,False)]:
    ax.add_patch(Circle((x,y),0.40,fc=ICE,ec=NAVY,lw=1.5,zorder=(4 if front else 1),
                        alpha=(1.0 if front else 0.55)))
ax.annotate("", xy=(CX,RB*0.34), xytext=(CX,RB*0.74),
            arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.3),zorder=4)
ax.annotate("", xy=(CX,-RB*0.34), xytext=(CX,-RB*0.74),
            arrowprops=dict(arrowstyle="-|>",color=NAVY,lw=1.3),zorder=4)
ax.text(CX,4.30,"경로제한 드론 4대  (저비용·소모성)",ha="center",fontsize=11,color=NAVY,fontweight="bold",zorder=8)
ax.text(CX,3.76,"진입 방향에 수직인 원 위 — 위·아래·좌·우",ha="center",fontsize=9.2,color=SLATE,zorder=8)
ax.text(CX+0.9,-4.15,"회피 방향을 사방에서 깎아 좁은 통로로 몰아준다",ha="center",fontsize=9.8,color=SLATE,zorder=8)
# 공격 드론
ax.add_patch(Circle((15.0,0),0.50,fc="#FBE3E1",ec=RED,lw=2.0,zorder=5))
ax.text(15.0,1.0,"공격 드론",ha="center",fontsize=11,color=RED,fontweight="bold",zorder=8)
ax.add_patch(FancyArrowPatch((14.35,0),(10.45,0),arrowstyle="-|>",mutation_scale=16,color=RED,lw=1.9,zorder=3))
ax.add_patch(FancyArrowPatch((6.55,0),(4.0,0),arrowstyle="-|>",mutation_scale=16,color=RED,lw=1.9,
                             ls=(0,(4,3)),zorder=3))
# 결과 두 갈래 — 작은 칩
def chip(x,y,txt,col,fill,w=7.0):
    ax.add_patch(FancyBboxPatch((x,y),w,0.78,boxstyle="round,pad=0.05,rounding_size=0.16",
                                fc=fill,ec=col,lw=1.5,zorder=6))
    ax.text(x+w/2,y+0.39,txt,ha="center",va="center",fontsize=10.0,color=col,
            fontweight="bold",zorder=9)
chip(-0.5,2.55,"포획 성공  →  네트로 회수 (비손실)",GREEN,"#E9F3EC")
chip(-0.5,-3.35,"발사 창을 놓치면  →  물리 요격 (폴백)",RED,"#FBEDEC")
ax.add_patch(FancyArrowPatch((3.0,0.62),(3.0,2.48),arrowstyle="-|>",mutation_scale=13,
                             color=GREEN,lw=1.5,zorder=6))
ax.add_patch(FancyArrowPatch((3.0,-0.6),(3.0,-2.5),arrowstyle="-|>",mutation_scale=13,
                             color=RED,lw=1.5,zorder=6))
ax.text(7.5,-5.85,"하나의 학습 정책이  ‘어떻게 몰아줄지 · 언제 쏠지 · 어느 수단으로 무력화할지’  를 함께 결정한다",
        ha="center",fontsize=11.2,color=NAVY,fontweight="bold",zorder=8)
ax.set_xlim(-1.6,16.6); ax.set_ylim(-6.4,5.15); ax.set_aspect("equal"); ax.axis("off")
fig.tight_layout(); fig.savefig("fig_concept.png",bbox_inches="tight",facecolor="white")
print("ok")
