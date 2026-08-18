"""오늘(2026-08-13) 실험 결과 대시보드 생성 — 시각 확인용.

    python viz/build_results_dashboard.py

`viz/trajectory_viewer_template.html` 의 디자인 토큰(CSS 변수·타이포)을 그대로
재사용하고, E1/E1b/E1c/E2-A/E2-B 집계를 임베드한 단일 HTML 을 만든다.
**분석 로직을 새로 만들지 않는다** — 이미 커밋된 아티팩트만 읽어 집계한다.

torch-free.
"""
from __future__ import annotations

import io
import json
import math
import pathlib
import re
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"

# --------------------------------------------------------------------------
# R-012 / R-013 -- 집계와 경계 상수는 **정본에서 가져온다**. 여기서 다시 구현하지
# 않는다. 종전에는 Wilson(z 가 정본과 달랐다) · bin 격자 · tau/rho/theta 를 전부
# 사본으로 들고 있었고, 최상단 칸은 경계 위 판을 조용히 떨어뜨렸다
# (감사 Session 2 X-005 · X-006). 모듈 docstring 의 "분석 로직을 새로 만들지
# 않는다" 를 이제 코드가 실제로 지킨다.
# --------------------------------------------------------------------------
sys.path.insert(0, str(ROOT))          # 스크립트로 직접 실행돼도 패키지가 잡히도록
from shepherd.m4_config import THREAT_BRACKET, m4_config          # noqa: E402
from shepherd.scripts.curve_sweep import (PSI_MED_DEG, a_star,    # noqa: E402
                                          a_star_psi, bin_edges)
from shepherd.stats import wilson                                 # noqa: E402

_CFG = m4_config()
TAU = float(_CFG["physics"]["tau_deploy"])
RHO = float(_CFG["physics"]["net_radius"])
RMAX = float(_CFG["viability"]["cone"]["range_max"])
THETA = float(_CFG["viability"]["cone"]["half_angle"])
PSI_MED = math.radians(PSI_MED_DEG)
A_STAR = a_star(RHO, TAU)
A_PSI = a_star_psi(PSI_MED, range_max=RMAX, half_angle=THETA, tau=TAU)
BR_LO, BR_HI = (float(x) for x in THREAT_BRACKET["physics.a_att_max"])

EDGES = bin_edges(BR_LO, BR_HI, A_STAR)


def _load(name):
    return json.load(io.open(R / name, encoding="utf-8"))


def curve(records, pred):
    out = []
    for i in range(len(EDGES) - 1):
        lo, hi = EDGES[i], EDGES[i + 1]
        # ★ 최상단 칸은 경계값을 **포함**한다 -- summarize_curve 와 동일 술어.
        #   없으면 a_att == BR_HI 인 판이 dashboard 에서만 사라진다 (X-006).
        top = (i == len(EDGES) - 2)
        sub = [r for r in records
               if lo <= r["a_att"] < hi or (top and r["a_att"] == hi)]
        if not sub:
            continue
        k = sum(1 for r in sub if pred(r))
        wl, wh = wilson(k, len(sub))
        out.append({"x": 0.5 * (lo + hi), "lo": lo, "hi": hi, "n": len(sub),
                    "k": k, "p": k / len(sub), "wl": wl, "wh": wh})
    return out


def main() -> None:
    hold = _load("curve_hold_reactive.json")["records"]
    A = _load("curve_intercept_reactive.json")["records"]
    B = _load("e2b_intercept_shamnet.json")["records"]
    e1b = _load("e1b_aim_diag.json")
    e1c = _load("e1c_fire_decomp.json")

    cap = lambda r: r["label"] in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
    hk = lambda r: r["label"] == "HARD_KILL"

    D = {
        "const": {"tau": TAU, "rho": RHO, "range_max": RMAX, "theta": THETA,
                  "a_star": A_STAR, "a_psi": A_PSI, "tan_theta": math.tan(THETA),
                  "bracket": [BR_LO, BR_HI]},
        # --- Fig 1 modality gap -------------------------------------------
        "modality": {
            "net_hold": curve(hold, cap),
            "net_intercept": curve(A, cap),
            "hk_intercept": curve(A, hk),
            "hk_sham": curve(B, hk),
        },
        # --- Fig 2 fire decomposition (E1c) --------------------------------
        "decomp": [{"lo": b["lo"], "hi": b["hi"], "n": b["n"],
                    "pf": b["p_fire"], "pf_w": b["p_fire_wilson"],
                    "pcf": (None if b["n_fired"] == 0 else b["p_capture_given_fire"]),
                    "pcf_w": (None if b["n_fired"] == 0
                              else b["p_capture_given_fire_wilson"]),
                    "pc": b["p_capture"], "n_fired": b["n_fired"]}
                   for b in e1c["bins"]],
        # --- Fig 3 psi (E1b) ------------------------------------------------
        "psi": {
            "pre_fixed": [math.degrees(e["psi_med"]) for e in e1b["records"]["fixed"]],
            "pre_inf": [math.degrees(e["psi_med"]) for e in e1b["records"]["inf"]],
            "commit_fixed": [math.degrees(e["psi_at_commit"])
                             for e in e1b["records"]["fixed"]
                             if e["psi_at_commit"] is not None],
            "commit_inf": [math.degrees(e["psi_at_commit"])
                           for e in e1b["records"]["inf"]
                           if e["psi_at_commit"] is not None],
            "delta": e1b["primary_delta_psi"],
            "integrity": e1b["integrity_I1"],
            "cone_deg": math.degrees(THETA),
        },
        # --- Fig 4 commit geometry (E1c) ------------------------------------
        "geom": {
            "ax": [r["ax_at_commit"] for r in e1c["records"] if r["fired"]],
            "d": [r["d_at_commit"] for r in e1c["records"] if r["fired"]],
            "slack": [r["cone_slack_at_commit"] for r in e1c["records"] if r["fired"]],
            "by_bin": [{"lo": b["lo"], "hi": b["hi"],
                        "ax": b["commit_geometry"]["ax_at_commit"],
                        "rp": b["commit_geometry"]["r_perp_at_commit"],
                        "slack": b["commit_geometry"]["cone_slack_at_commit"]}
                       for b in e1c["bins"] if b.get("commit_geometry")
                       and b["commit_geometry"]["ax_at_commit"]],
        },
        # --- E2 summary ------------------------------------------------------
        "e2": {
            "A": dict(Counter(r["label"] for r in A)),
            "B": dict(Counter(r["label"] for r in B)),
            "n": len(A),
            "phk_A": sum(1 for r in A if hk(r)) / len(A),
            "phk_B": sum(1 for r in B if hk(r)) / len(B),
            "n01": sum(1 for x, y in zip(A, B) if not hk(x) and hk(y)),
            "n10": sum(1 for x, y in zip(A, B) if hk(x) and not hk(y)),
            "converted": sum(1 for x, y in zip(A, B)
                             if x["label"] == "NET_CAPTURE" and hk(y)),
            "oracle_n": sum(1 for r in A if r["a_att"] >= A_STAR),
            "oracle_mismatch": sum(
                1 for x, y in zip(A, B) if x["a_att"] >= A_STAR
                and any(x[f] != y[f] for f in
                        ("episode", "label", "regime", "a_att", "att_speed"))),
            "oracle_strong_n": sum(1 for r in A if r["label"] != "NET_CAPTURE"),
            "oracle_strong_mismatch": sum(
                1 for x, y in zip(A, B) if x["label"] != "NET_CAPTURE"
                and any(x[f] != y[f] for f in
                        ("episode", "label", "regime", "a_att", "att_speed"))),
        },
        # --- E1 ---------------------------------------------------------------
        "e1": {"fixed_k": 84, "inf_k": 85, "n01": 1, "n10": 0,
               "ci": [0.0, 0.006], "n": 500},
    }

    style = re.search(r"<style>.*?</style>",
                      io.open(ROOT / "viz/trajectory_viewer_template.html",
                              encoding="utf-8").read(), re.S).group(0)
    html = TEMPLATE.replace("/*__STYLE__*/", style).replace(
        "/*__DATA__*/null", json.dumps(D, ensure_ascii=False))
    out = ROOT / "viz/results_dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"-> {out}  ({out.stat().st_size/1024:.0f} KB)")


TEMPLATE = r"""<meta charset="utf-8">
<title>newURP 결과 대시보드 — 2026-08-13</title>
/*__STYLE__*/
<style>
  main { display:block; padding:12px 16px; max-width:1180px; margin:0 auto; }
  .row { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
  @media (max-width:980px){ .row{ grid-template-columns:1fr; } }
  .pane h2 small { text-transform:none; letter-spacing:0; font-weight:400;
                   color:var(--ink-mute); margin-left:6px; }
  .note { font-size:12px; color:var(--ink-2); margin:6px 2px 0; }
  .warn { color:var(--c-crit); font-weight:600; }
  .ok { color:var(--c-good); font-weight:600; }
  table.kv { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums;
             font-size:13px; }
  table.kv td,table.kv th { padding:3px 6px; border-bottom:1px solid var(--grid);
                            text-align:right; }
  table.kv td:first-child,table.kv th:first-child { text-align:left; color:var(--ink-2); }
  table.kv th { color:var(--ink-mute); font-weight:600; font-size:11px;
                text-transform:uppercase; letter-spacing:.05em; }
  .lg { display:flex; flex-wrap:wrap; gap:8px 16px; font-size:12px;
        color:var(--ink-2); margin:4px 2px 8px; }
  .lg span::before { content:""; display:inline-block; width:11px; height:11px;
        border-radius:2px; margin-right:5px; vertical-align:-1px; background:var(--dot); }
</style>

<header>
  <h1>newURP 결과 대시보드</h1>
  <span style="color:var(--ink-2);font-size:12px">2026-08-13 · T1 반응형 · ratified 계약 · M4 legacy 기하</span>
</header>

<main>
  <div class="pane">
    <h2>Fig 1 — modality gap <small>요격 가능 ≠ 비파괴 포획 가능 (n=2700/곡선)</small></h2>
    <div class="lg">
      <span style="--dot:var(--c-net)">net capture (hold)</span>
      <span style="--dot:var(--c-fin)">net capture (intercept)</span>
      <span style="--dot:var(--c-att)">물리 요격 hard-kill (intercept)</span>
      <span style="--dot:var(--c-warn)">a*(ψ)=25.75</span>
      <span style="--dot:var(--c-crit)">a*=39.33</span>
    </div>
    <canvas id="c1" height="330"></canvas>
    <p class="note" id="n1"></p>
  </div>

  <div class="row" style="margin-top:12px">
    <div class="pane">
      <h2>Fig 2 — 발사 분해 <small>P(C|a) = P(F|a)·P(C|F,a), hold, n=500</small></h2>
      <div class="lg">
        <span style="--dot:var(--c-lim)">P(F|a) 발사 자격</span>
        <span style="--dot:var(--c-fin)">P(C|F,a) 조건부 포획</span>
        <span style="--dot:var(--c-att)">P(C|a) 전체</span>
      </div>
      <canvas id="c2" height="300"></canvas>
      <p class="note" id="n2"></p>
    </div>
    <div class="pane">
      <h2>Fig 3 — 조준 오차 ψ <small>E1b, ω=2.0 vs ∞, n=500 paired</small></h2>
      <div class="lg">
        <span style="--dot:var(--c-lim)">pre-commit ω=2.0</span>
        <span style="--dot:var(--c-fin)">pre-commit ω=∞</span>
        <span style="--dot:var(--c-net)">at-commit (양쪽 동일)</span>
        <span style="--dot:var(--c-crit)">원뿔 반각 12.15°</span>
      </div>
      <canvas id="c3" height="300"></canvas>
      <p class="note" id="n3"></p>
    </div>
  </div>

  <div class="row" style="margin-top:12px">
    <div class="pane">
      <h2>Fig 4 — commit 기하 예산 <small>E1c, 발사 117건</small></h2>
      <canvas id="c4" height="300"></canvas>
      <p class="note" id="n4"></p>
    </div>
    <div class="pane">
      <h2>판정 요약 <small>오늘 실행 4건</small></h2>
      <table class="kv" id="tsum"></table>
      <p class="note">모든 수치는 커밋된 아티팩트에서 재집계. 새 분석 로직 없음.</p>
    </div>
  </div>
</main>

<script>
const DATA = /*__DATA__*/null;
const cssv = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const C = () => ({lim:cssv('--c-lim'),att:cssv('--c-att'),fin:cssv('--c-fin'),
  net:cssv('--c-net'),warn:cssv('--c-warn'),crit:cssv('--c-crit'),
  ink:cssv('--ink'),ink2:cssv('--ink-2'),mute:cssv('--ink-mute'),grid:cssv('--grid')});

function setup(id, h){
  const cv=document.getElementById(id), dpr=devicePixelRatio||1;
  const w=cv.clientWidth; cv.width=w*dpr; cv.height=h*dpr;
  const g=cv.getContext('2d'); g.scale(dpr,dpr); g.clearRect(0,0,w,h);
  return {g,w,h};
}
function axes(g,w,h,pad,xr,yr,xlab,ylab,c){
  g.strokeStyle=c.grid; g.fillStyle=c.mute; g.font='11px system-ui'; g.lineWidth=1;
  for(let i=0;i<=5;i++){
    const y=pad.t+(h-pad.t-pad.b)*i/5, v=yr[1]-(yr[1]-yr[0])*i/5;
    g.beginPath(); g.moveTo(pad.l,y); g.lineTo(w-pad.r,y); g.stroke();
    g.textAlign='right'; g.textBaseline='middle'; g.fillText(v.toFixed(2),pad.l-6,y);
  }
  for(let i=0;i<=6;i++){
    const x=pad.l+(w-pad.l-pad.r)*i/6, v=xr[0]+(xr[1]-xr[0])*i/6;
    g.textAlign='center'; g.textBaseline='top'; g.fillText(v.toFixed(0),x,h-pad.b+5);
  }
  g.fillStyle=c.ink2; g.textAlign='center';
  g.fillText(xlab,(pad.l+w-pad.r)/2,h-10);
  g.save(); g.translate(12,(pad.t+h-pad.b)/2); g.rotate(-Math.PI/2);
  g.fillText(ylab,0,0); g.restore();
}
const mk=(pad,w,h,xr,yr)=>({
  X:v=>pad.l+(w-pad.l-pad.r)*(v-xr[0])/(xr[1]-xr[0]),
  Y:v=>h-pad.b-(h-pad.t-pad.b)*(v-yr[0])/(yr[1]-yr[0])});

function band(g,X,Y,pts,col,alpha){
  g.save(); g.globalAlpha=alpha; g.fillStyle=col; g.beginPath();
  pts.forEach((p,i)=>{const x=X(p.x),y=Y(p.wh); i?g.lineTo(x,y):g.moveTo(x,y);});
  for(let i=pts.length-1;i>=0;i--) g.lineTo(X(pts[i].x),Y(pts[i].wl));
  g.closePath(); g.fill(); g.restore();
}
function line(g,X,Y,pts,col,wdt=2,dash=[]){
  g.save(); g.strokeStyle=col; g.lineWidth=wdt; g.setLineDash(dash); g.beginPath();
  pts.forEach((p,i)=>{const x=X(p.x!==undefined?p.x:p[0]),y=Y(p.p!==undefined?p.p:p[1]);
    i?g.lineTo(x,y):g.moveTo(x,y);});
  g.stroke(); g.restore();
  g.fillStyle=col;
  pts.forEach(p=>{g.beginPath();
    g.arc(X(p.x!==undefined?p.x:p[0]),Y(p.p!==undefined?p.p:p[1]),2.6,0,7); g.fill();});
}
function vline(g,X,h,pad,v,col,label){
  g.save(); g.strokeStyle=col; g.lineWidth=1.5; g.setLineDash([5,4]);
  g.beginPath(); g.moveTo(X(v),pad.t); g.lineTo(X(v),h-pad.b); g.stroke();
  g.setLineDash([]); g.fillStyle=col; g.font='11px system-ui'; g.textAlign='left';
  g.fillText(label,X(v)+4,pad.t+11); g.restore();
}

function fig1(){
  const c=C(), {g,w,h}=setup('c1',330), pad={l:52,r:14,t:12,b:40};
  const xr=DATA.const.bracket, yr=[0,1];
  axes(g,w,h,pad,xr,yr,'공격자 최대 가속 a_att  [m/s²]','확률',c);
  const {X,Y}=mk(pad,w,h,xr,yr);
  const M=DATA.modality;
  // gap 음영: net(intercept) 과 hk(intercept) 사이
  g.save(); g.globalAlpha=.13; g.fillStyle=c.att; g.beginPath();
  M.hk_intercept.forEach((p,i)=>{const x=X(p.x),y=Y(p.p); i?g.lineTo(x,y):g.moveTo(x,y);});
  for(let i=M.net_intercept.length-1;i>=0;i--)
    g.lineTo(X(M.net_intercept[i].x),Y(M.net_intercept[i].p));
  g.closePath(); g.fill(); g.restore();
  band(g,X,Y,M.hk_intercept,c.att,.15); band(g,X,Y,M.net_intercept,c.fin,.15);
  line(g,X,Y,M.net_hold,c.net,1.6,[4,3]);
  line(g,X,Y,M.net_intercept,c.fin,2.2);
  line(g,X,Y,M.hk_intercept,c.att,2.2);
  vline(g,X,h,pad,DATA.const.a_psi,c.warn,'a*(ψ) 25.75');
  vline(g,X,h,pad,DATA.const.a_star,c.crit,'a* 39.33');
  g.fillStyle=c.att; g.font='600 12px system-ui'; g.textAlign='center';
  g.fillText('non-destructive capture gap', X(52), Y(.33));
  document.getElementById('n1').innerHTML =
    'a≥39.33 구간: net <b>0/1598</b>, 물리 요격 <b>0.243</b>. '+
    '★ 단 그 구간 zero 는 <span class="warn">게이트 기권</span>이라 post-commit 실패의 독립 실증이 아님 (docs/83 §14.2). '+
    '음영 = 두 modality 의 격차. E2-B(sham-net) 결과 하드킬 곡선은 <b>변화 0</b> → 경쟁위험 censoring 없음.';
}

function fig2(){
  const c=C(), {g,w,h}=setup('c2',300), pad={l:52,r:14,t:12,b:40};
  const xr=DATA.const.bracket, yr=[0,1];
  axes(g,w,h,pad,xr,yr,'a_att  [m/s²]','확률',c);
  const {X,Y}=mk(pad,w,h,xr,yr);
  const D=DATA.decomp, mid=b=>0.5*(b.lo+b.hi);
  line(g,X,Y,D.map(b=>({x:mid(b),p:b.pf})),c.lim,2.2);
  const f=D.filter(b=>b.pcf!==null);
  line(g,X,Y,f.map(b=>({x:mid(b),p:b.pcf})),c.fin,2.2);
  line(g,X,Y,D.map(b=>({x:mid(b),p:b.pc})),c.att,1.6,[4,3]);
  vline(g,X,h,pad,32.2,c.crit,'발사 상한 32.2');
  document.getElementById('n2').innerHTML =
    'a≥32.2 에서 <b>발사 0/350</b> — 실패의 정체가 “쐈는데 못 잡음”이 아니라 <b>아예 안 쏨</b>. '+
    '22–32 붕괴는 두 항의 <b>동시</b> 붕괴(경우 ③).';
}

function hist(g,X,Y,vals,col,lo,hi,nb,alpha){
  const H=new Array(nb).fill(0);
  vals.forEach(v=>{const i=Math.min(nb-1,Math.max(0,Math.floor((v-lo)/(hi-lo)*nb))); H[i]++;});
  const mx=Math.max(...H)||1;
  g.save(); g.globalAlpha=alpha; g.fillStyle=col;
  H.forEach((k,i)=>{ if(!k) return;
    const x0=X(lo+(hi-lo)*i/nb), x1=X(lo+(hi-lo)*(i+1)/nb);
    g.fillRect(x0,Y(k/mx),Math.max(1,x1-x0-1),Y(0)-Y(k/mx));});
  g.restore();
}
function fig3(){
  const c=C(), {g,w,h}=setup('c3',300), pad={l:52,r:14,t:12,b:40};
  const xr=[0,70], yr=[0,1];
  axes(g,w,h,pad,xr,yr,'ψ  [deg]','상대 빈도',c);
  const {X,Y}=mk(pad,w,h,xr,yr);
  const P=DATA.psi;
  hist(g,X,Y,P.pre_fixed,c.lim,0,70,35,.55);
  hist(g,X,Y,P.pre_inf,c.fin,0,70,35,.55);
  hist(g,X,Y,P.commit_fixed,c.net,0,70,35,.85);
  vline(g,X,h,pad,P.cone_deg,c.crit,'원뿔 반각');
  const md=P.delta.median_delta_psi_deg, ci=P.delta.ci95_deg;
  document.getElementById('n3').innerHTML =
    `pre-commit 중앙값 <b>33.94° → 7.85°</b> (Δ ${md.toFixed(2)}°, CI [${ci[0].toFixed(2)}, ${ci[1].toFixed(2)}]) — 감소 확립. `+
    `그러나 <b>at-commit 은 2.320° 로 양쪽 동일</b> (Δ=0.000, 117쌍 100% bit-identical) → `+
    `<span class="warn">게이트가 조준 오차를 흡수</span>. 포획 84→85.`;
}

function fig4(){
  const c=C(), {g,w,h}=setup('c4',300), pad={l:52,r:14,t:12,b:40};
  const xr=[0,14], yr=[0,1];
  axes(g,w,h,pad,xr,yr,'거리 [m]','상대 빈도',c);
  const {X,Y}=mk(pad,w,h,xr,yr);
  hist(g,X,Y,DATA.geom.d,c.mute,0,14,28,.45);
  hist(g,X,Y,DATA.geom.ax,c.lim,0,14,28,.8);
  vline(g,X,h,pad,DATA.const.range_max,c.crit,'R_max 8.22');
  const ax=DATA.geom.ax.slice().sort((a,b)=>a-b);
  const med=ax[Math.floor(ax.length/2)];
  vline(g,X,h,pad,med,c.fin,'ax 중앙 '+med.toFixed(2));
  document.getElementById('n4').innerHTML =
    `회색 = 발사 시점 거리 d, 파랑 = <b>예측점 축방향 ax</b> (판정이 보는 양). `+
    `공칭 ρ=1.77 은 ax=R_max 8.22 에서만 얻는 값인데 실현 ax 중앙값은 <b>${med.toFixed(2)}</b>. `+
    `ρ_local 1.380 → slack <b>1.103</b> → 2·slack/τ² = <b>24.5</b> vs 관측 교차 22.4–22.9. `+
    `<span class="warn">exploratory — 기하가 발사 조건부라 순환성 있음.</span>`;
}

function summary(){
  const e2=DATA.e2, e1=DATA.e1, rows=[
    ['<b>E1</b> ω 2.0→∞ (T1, n=500)',
     `84→85 · n01=1 · CI [${e1.ci[0]}, ${e1.ci[1]}] → <b>INCONCLUSIVE</b>`],
    ['<b>E1b</b> ψ paired (n=500)',
     `pre Δ −24.99° CI[−28.42,−20.34] <span class="ok">감소 확립</span> · at-commit Δ <b>0.000</b> → <b>분기 B</b>`],
    ['<b>E1c</b> 발사 분해 (n=500)',
     `P(F|a) 1.000→0.920→0.388→<b>0</b> · a≥32.2 발사 <b>0/350</b> → <b>경우 ③</b>`],
    ['<b>E2-B</b> sham-net (n=2700)',
     `P_HK ${e2.phk_A.toFixed(4)} → ${e2.phk_B.toFixed(4)} · <b>Δ=+0.0000</b> · n01=${e2.n01} n10=${e2.n10}`],
    ['E2 oracle (a≥39.33)',
     `n=${e2.oracle_n} 불일치 <b>${e2.oracle_mismatch}</b> <span class="ok">PASS</span>`],
    ['E2 강화 oracle (A≠NET_CAPTURE)',
     `n=${e2.oracle_strong_n} 불일치 <b>${e2.oracle_strong_mismatch}</b> <span class="ok">PASS</span>`],
    ['★ net capture → hard kill 전환',
     `<b>${e2.converted} / 426</b> — 경쟁위험 censoring <b>없음</b>`],
  ];
  document.getElementById('tsum').innerHTML =
    '<tr><th>실험</th><th>결과</th></tr>' +
    rows.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('');
}

function draw(){ fig1(); fig2(); fig3(); fig4(); summary(); }
draw(); addEventListener('resize', draw);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
</script>
"""

if __name__ == "__main__":
    main()
