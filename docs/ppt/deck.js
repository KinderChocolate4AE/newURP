const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE";

const NAVY="1E2761", ICE="CADCFC", SLATE="4A5568", AMBER="D97706",
      GREEN="2F7A4F", RED="B3423A", LIGHT="EEF3FB", WHITE="FFFFFF", GREY="8A94A6";
const KR = "Malgun Gothic";

function title(s,t,sub){
  s.addText(t,{x:0.55,y:0.30,w:12.3,h:0.62,fontSize:29,bold:true,color:NAVY,fontFace:KR,margin:0});
  if(sub) s.addText(sub,{x:0.55,y:0.94,w:12.3,h:0.36,fontSize:13.5,color:SLATE,fontFace:KR,margin:0});
}
function card(s,x,y,w,h,fill,line){
  s.addShape(p.ShapeType.roundRect,{x,y,w,h,fill:{color:fill||LIGHT},
    line:{color:line||"D5DEEC",width:1},rectRadius:0.08});
}
function foot(s,txt){
  s.addText(txt,{x:0.55,y:6.96,w:12.3,h:0.32,fontSize:11.5,italic:true,color:NAVY,fontFace:KR,margin:0});
}

/* ═════════ 1장 ═════════ */
let s = p.addSlide();
title(s,"지금까지 한 일과 현재 위치",
        "요격 시스템을 만들고 → 물리값을 확정하고 → 학습 준비를 마쳤습니다  ·  2026년 8월 2일");

s.addImage({path:"fig_concept.png", x:0.50, y:1.32, w:7.30, h:4.49});

const C1=[
 ["요격 시스템을 만들었다",
  "네트로 붙잡는 길과 물리적으로 부딪쳐 떨어뜨리는 길, 두 가지를 하나의 학습 정책이 상황에 따라 골라 쓰도록 구현했습니다. 공격 드론 쪽도 회피 실력을 3단계로 만들어, 어려운 상대에게도 통하는지 볼 수 있게 했습니다."],
 ["가정으로 쓰던 값을 실제 논문 값으로 바꿨다",
  "네트가 실제로 덮는 반경, 네트가 펼쳐지는 데 걸리는 시간, 방어 드론과 공격 드론의 성능 차이 — 근거 없이 감으로 정해 두었던 값 7개를 찾아내 실험 결과가 있는 논문 값으로 교체했습니다."],
 ["학습을 걸기 전에 전제를 검사하게 했다",
  "값을 하나 고칠 때마다 “이 조건에서 협력이 의미가 있기는 한가”를 자동으로 되묻는 장치를 붙였습니다. 이번 기간에 네 번 걸렸고, 그 네 건이 3장의 내용입니다. 학습을 돌리기 전에 전부 발견했습니다."]];
C1.forEach((c,i)=>{
  const y=1.34+i*1.51;
  card(s,8.05,y,4.78,1.43,LIGHT);
  s.addText(c[0],{x:8.27,y:y+0.10,w:4.34,h:0.30,fontSize:13,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
  s.addText(c[1],{x:8.27,y:y+0.42,w:4.34,h:0.92,fontSize:10.1,color:SLATE,fontFace:KR,margin:0,lineSpacingMultiple:1.14});
});

card(s,0.50,5.90,12.33,0.98,"F4F8FF");
s.addText("연구계획서에 적어둔 단계 대비 현재 위치",
  {x:0.74,y:5.97,w:6.0,h:0.26,fontSize:11.5,bold:true,color:NAVY,fontFace:KR,margin:0});
const STEP=[["1단계","완료",GREEN,"시뮬레이터 · 비교 기준선 · 학습 전 사전 점검"],
            ["2단계","준비 완료 · 착수 대기",AMBER,"학습 기준선 · 비교 실험"],
            ["3단계 이후","대기",GREY,"논문 핵심 그림 · 최종 보고서"]];
STEP.forEach((r,i)=>{
  const x=0.74+i*3.97;
  s.addShape(p.ShapeType.roundRect,{x:x,y:6.26,w:3.75,h:0.54,fill:{color:WHITE},
    line:{color:"D5DEEC",width:1},rectRadius:0.06});
  s.addText([{text:r[0]+"  ",options:{bold:true,color:NAVY,fontSize:11.5}},
             {text:r[1],options:{bold:true,color:r[2],fontSize:11}}],
    {x:x+0.16,y:6.29,w:3.45,h:0.24,fontFace:KR,margin:0,valign:"middle"});
  s.addText(r[3],{x:x+0.16,y:6.53,w:3.45,h:0.24,fontSize:9.6,color:SLATE,fontFace:KR,margin:0,valign:"middle"});
});

foot(s,"이번 기간 산출물 — 자동 검증 447항목 전부 통과 · 설계·검증 문서 20편.   학습 준비는 마쳤고, 계산 자원 배정에 맞춰 다음 단계로 넘어갑니다.");
s.addNotes("1장은 무엇을 만들었나. 그림 하나로 교전 구도 전체를 설명하고, 오른쪽 세 장이 이번 기간에 한 일.");

/* ═════════ 2장 ═════════ */
s = p.addSlide();
title(s,"핵심 성과 — 경계가 하나가 아니라 둘이었습니다",
        "수식이 준 경계 39.3 은 실측에서 예외가 없었고(1,635판 중 0회), 곡선은 그보다 앞선 23.8 에서 무너집니다 — 그 사이가 학습이 먹을 자리입니다");

s.addImage({path:"fig_mech.png", x:0.50, y:1.34, w:4.88, h:2.80});

/* ─ ① τ 카드 ─ */
card(s,5.62,1.34,7.21,0.86,LIGHT);
s.addText("①  발사에서 포획까지 걸리는 시간 τ 를 셋으로 쪼갰습니다  —  0.30 초",
  {x:5.82,y:1.40,w:6.81,h:0.24,fontSize:12.4,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
s.addText([{text:"네트가 날아가 펼쳐지는 0.15  +  표적을 다시 보는 0.10  +  판단 0.05  (초).  ",options:{bold:true}},
           {text:"이 지연을 잰 선행 연구가 없어(검색 범위 = 네트 포획 드론 문헌) 세 단계로 쪼개 실험 논문·센서 사양에서 가져왔고, 일부러 뺀 항목이 있어 “적어도 이만큼”인 하한값입니다."}],
  {x:5.82,y:1.66,w:6.81,h:0.48,fontSize:9.5,color:SLATE,fontFace:KR,margin:0,lineSpacingMultiple:1.10});

/* ─ ② 첫 번째 경계 카드 ─ */
card(s,5.62,2.28,7.21,0.88,"FDF6EA","E8D4B4");
s.addText("②  첫 번째 경계 — 도달 범위가 정합니다  (왼쪽 그림)",
  {x:5.82,y:2.34,w:6.81,h:0.24,fontSize:12.4,bold:true,color:AMBER,fontFace:KR,margin:0,valign:"middle"});
s.addText([{text:"τ 동안 공격 드론은 옆으로 w = ½·a·τ² 만큼 빠져나갈 수 있습니다. 이게 네트가 덮는 반경 ρ 보다 커지면 네트를 어디에 놓아도 못 잡습니다. 경계는 "},
           {text:"a* = 2ρ / τ² = 39.3 m/s²",options:{bold:true,color:AMBER}},
           {text:" 이고, 이 위에서 네트 포획은 "},
           {text:"1,635 판 중 0 회",options:{bold:true,color:NAVY}},
           {text:" — 예외가 없었습니다."}],
  {x:5.82,y:2.60,w:6.81,h:0.50,fontSize:9.5,color:SLATE,fontFace:KR,margin:0,lineSpacingMultiple:1.10});

/* ─ ③ 두 번째 경계 카드 ─ */
card(s,5.62,3.24,7.21,1.02,"F0F7F9","BBD6DC");
s.addText("③  두 번째 경계 — 도달 범위가 아니라 겨냥 정밀도가 정합니다",
  {x:5.82,y:3.30,w:6.81,h:0.24,fontSize:12.4,bold:true,color:"1F7A8C",fontFace:KR,margin:0,valign:"middle"});
s.addText([{text:"실제로는 완벽히 겨눌 수 없습니다. 남는 조준각을 따로 쟀더니 중앙값 4.3° 였고, 이걸 넣은 a*(ψ) = 2d (tanθ − ψ) / τ² 는 "},
           {text:"25.8",options:{bold:true,color:"1F7A8C"}},
           {text:" 입니다. 곡선이 실제로 무너지는 지점은 "},
           {text:"23.8",options:{bold:true,color:"1F7A8C"}},
           {text:" — 전혀 다른 방법으로 잰 두 값이 7.5 % 안에서 만납니다.\n"},
           {text:"몰아주는 배치가 이득을 못 낸 이유도 이것입니다  ",options:{bold:true,color:NAVY}},
           {text:"— 옆방향 속도를 0.4 → 7.3 m/s 로 키워 이 경계를 왼쪽으로 밀었습니다."}],
  {x:5.82,y:3.56,w:6.81,h:0.64,fontSize:9.5,color:SLATE,fontFace:KR,margin:0,lineSpacingMultiple:1.10});

s.addImage({path:"fig_curve.png", x:0.83, y:4.38, w:11.67, h:2.40});

s.addText([{text:"연구계획서의 진행/중단 기준 → 통과.  ",options:{bold:true,color:GREEN}},
           {text:"수식이 예측한 위치에서 경계가 관측됐고, 두 번째 경계는 예측→검증까지 닫혔습니다.   "},
           {text:"학습이 이겨야 할 수도 정해집니다 : ",options:{bold:true,color:NAVY}},
           {text:"겨냥 구간에서 손튜닝이 부딪쳐 내는 15.5 % 를, 기체를 부수지 않고."}],
  {x:0.62,y:6.82,w:12.09,h:0.30,fontSize:10.4,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
s.addNotes("경계 1: a* = 2ρ/τ² = 39.3 (완벽 정렬 가정). 경계 2: a*(ψ) = 2d(tanθ − ψ)/τ², ψ = slew_audit 실측 4.26° → 25.8. 곡선 50% 교차 23.8 (hold n=1500). 곡선은 손튜닝 기준선의 것이지 학습 정책의 것이 아님.");

/* ═════════ 3장 ═════════ */
s = p.addSlide();
title(s,"사전 점검이 네 번 걸러냈습니다 — 네 번째는 원인까지 찾았습니다",
        "네 건 모두 학습을 돌리기 전에 발견했습니다. 50회 학습을 태운 뒤였다면 전부 사후 발견이었을 것들입니다");

const ITEMS=[
 ["1","실제 값을 넣었더니 협력이 필요 없어졌다",
  "근거 없이 쓰던 0.4초를 실제로 풀어 보니 0.15초였습니다. 그만큼 빠르면 네트 드론 혼자서 12번 중 12번을 다 막아 — 협력을 연구할 상황 자체가 없어집니다. 원인은 지연을 너무 짧게 본 것이어서, 탐지·판단 시간을 더해 0.30초로 정정했습니다.",
  GREEN,"해결"],
 ["2","네트가 닿지도 못하는 거리를 포획으로 세고 있었다",
  "포획 판정 범위는 29.8 m 로 잡혀 있었는데, 그 시간 동안 네트가 실제로 날아가는 거리는 8.2 m 였습니다. 닿을 수 없는 표적을 성공으로 집계하던 셈입니다. 발사 가능 범위를 네트가 실제로 가는 거리로 다시 계산했습니다.",
  GREEN,"해결"],
 ["3","비교 기준선이 공짜로 물리 요격을 쓰고 있었다",
  "“사용하지 않음”으로 문서화돼 있던 입력 자리를 새 기능이 재사용하면서 충돌해, 비교용 기준선의 방어 드론 4대가 첫 순간에 전부 요격에 돌입하고 있었습니다. 못 잡았다면 논문에 실을 비교 기준선이 전부 무의미해집니다.",
  GREEN,"해결"],
 ["4","몰아주는 배치로는 이득이 나오지 않았습니다",
  [{text:"현상  ",options:{bold:true,color:NAVY}},
   {text:"같은 조건 48회를 짝지어 비교했더니, 몰아주는 배치가 있으나 없으나 48번 모두 같은 결과였습니다.\n"},
   {text:"원인  ",options:{bold:true,color:NAVY}},
   {text:"협력에 반대 방향 두 효과가 함께 있기 때문입니다 — 도망갈 길은 막아 주지만, 그 과정에서 옆방향 속도가 실려 네트 드론이 겨냥을 따라가지 못합니다. 2장 ②에서 이 손해의 크기를 수치로 닫았습니다.\n"},
   {text:"단, 부딪쳐 떨어뜨리는 배치는 다릅니다  ",options:{bold:true,color:AMBER}},
   {text:"경계 위에서 731회 중 52회(7.1%), 그 앞 겨냥 구간에서 226회 중 35회(15.5%)를 막습니다. 전부 부딪쳐 떨어뜨린 것이고 대가는 비손실 포기입니다(무력화 중 67%만 네트 회수).\n"},
   {text:"그래서 학습의 목표가 분명해집니다  ",options:{bold:true,color:NAVY}},
   {text:"“비손실을 지키면서 그 영역을 방어할 수 있는가.” 두 효과를 따로 재는 장치를 만들고 이 질문을 학습 목표로 미리 선언했습니다."}],
  AMBER,"원인 규명"]];
const YS=[1.36,2.44,3.52,4.60], HS=[1.02,1.02,1.02,1.50];
ITEMS.forEach((it,i)=>{
  const y=YS[i], h=HS[i];
  card(s,0.50,y,8.15,h, i===3 ? "FDF3F2" : LIGHT, i===3 ? "E8C4C0" : "D5DEEC");
  s.addShape(p.ShapeType.ellipse,{x:0.70,y:y+(h-0.46)/2,w:0.46,h:0.46,fill:{color:it[3]},line:{color:it[3]}});
  s.addText(it[0],{x:0.70,y:y+(h-0.46)/2,w:0.46,h:0.46,fontSize:15,bold:true,color:WHITE,
    fontFace:"Calibri",align:"center",valign:"middle",margin:0});
  s.addText(it[1],{x:1.30,y:y+0.07,w:5.60,h:0.28,fontSize:12.4,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
  s.addText(it[4],{x:7.00,y:y+0.07,w:1.45,h:0.28,fontSize:11,bold:true,color:it[3],fontFace:KR,margin:0,align:"right",valign:"middle"});
  s.addText(it[2],{x:1.30,y:y+0.37,w:6.60,h:h-0.44,fontSize:9.9,color:SLATE,fontFace:KR,margin:0,lineSpacingMultiple:1.12});
});

card(s,8.85,1.36,3.98,2.22,"F4F8FF");
s.addText("계획서가 이미 승인해 둔 경로",{x:9.06,y:1.46,w:3.56,h:0.28,fontSize:13,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
s.addText("중간 결과가 미미할 때의 대응으로 신청서에 미리 적어둔 문장",
  {x:9.06,y:1.76,w:3.56,h:0.24,fontSize:9.5,color:GREY,fontFace:KR,margin:0,valign:"middle"});
s.addText("“어디서 협력이 의미가 있고 어디서 약한지, 그 경계 분석에 집중한다 … 경계를 규명하는 것 자체가 학술 가치 있는 결과”",
  {x:9.06,y:2.04,w:3.56,h:0.92,fontSize:10.4,italic:true,color:SLATE,fontFace:KR,margin:0,lineSpacingMultiple:1.14});
s.addText("4번은 이 경로 안에 있고, 그 산출물인 “경계”는 이미 2장에서 확보했습니다. 게다가 원인까지 나와 결과가 한 단계 더 나아갔습니다.",
  {x:9.06,y:2.88,w:3.56,h:0.66,fontSize:10.4,bold:true,color:NAVY,fontFace:KR,margin:0,lineSpacingMultiple:1.14});

card(s,8.85,3.68,3.98,2.44,LIGHT);
s.addText("다음 단계",{x:9.06,y:3.78,w:3.56,h:0.28,fontSize:13,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
[["학습 시험 가동","3회 — 신호가 실제로 붙는지 확인"],
 ["본 학습","40회 — 계산 서버에서 약 3일"],
 ["공격자 난이도 상향","회피가 더 정교한 상대 2단계 추가 (3 → 5단계)"],
 ["핵심 그림 채우기","학습 정책의 곡선을 2장 기준선 곡선 위에 겹치기"],
 ["기체 사양 좁히기","지금은 등급 범위를 매 회 무작위로 훑는 중"]].forEach((r,i)=>{
  const y=4.10+i*0.39;
  s.addText("▸ "+r[0],{x:9.06,y:y,w:3.56,h:0.21,fontSize:10.8,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
  s.addText(r[1],{x:9.24,y:y+0.19,w:3.38,h:0.21,fontSize:9.1,color:SLATE,fontFace:KR,margin:0,valign:"middle"});
});


card(s,0.50,6.26,12.33,0.70,"F4F8FF","C6D6EE");
s.addText([{text:"경계 위에서 네트로 잡는 것은 1,635회 중 0회 — 손튜닝으로 막는 유일한 길은 물리 요격이고, 그 대가는 비손실 포기입니다.   ",options:{bold:true}},
           {text:"네 건 모두 학습을 돌리기 전에 발견했습니다. 평가 기준과 표본 수도 결과를 보기 전에 미리 정해 두었습니다.",options:{italic:true}}],
  {x:0.78,y:6.26,w:11.80,h:0.70,fontSize:11.2,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
s.addNotes("4번은 지도가 필요한 모델링 판단. 결과 방향과 무관하게 물리적으로 옳은 형태로 구현하는 방식을 제안.");

/* ═════════ 4장 · 부록 ═════════ */
s = p.addSlide();
title(s,"부록 — 용어와 값의 출처",
        "본문에 쓴 숫자는 전부 아래 표의 출처에서 왔습니다. 근거 없이 정한 값은 남아 있지 않습니다");

/* ── 용어 · 값 · 출처 (전폭) ─────────────────────────────────────── */
const TW=[2.30,5.90,1.30,2.78];          /* 열 너비 합 = 12.28 */
const TX=[0.55]; TW.forEach((w,i)=>TX.push(TX[i]+w));
s.addShape(p.ShapeType.rect,{x:0.55,y:1.46,w:12.28,h:0.32,fill:{color:NAVY},line:{color:NAVY}});
["용어","이 연구에서의 뜻","우리 값","출처"].forEach((t,i)=>
  s.addText(t,{x:TX[i]+0.10,y:1.46,w:TW[i]-0.18,h:0.32,fontSize:10.2,bold:true,
    color:WHITE,fontFace:KR,margin:0,valign:"middle",align:i===2?"center":"left"}));
const TERMS=[
 ["네트 드론","네트를 쏘아 공격 드론을 통째로 붙잡는 방어 드론","1 대","우리 설정"],
 ["경로제한 드론","공격 드론의 갈 길을 좁히는 드론. 학습 대상","4 대","우리 설정"],
 ["보호 자산","공격 드론이 도달하면 실패로 판정하는 지점","원점","우리 설정"],
 ["네트 반경  ρ","최악 방향에서 네트가 확실히 덮는 반경. 등가면적 반경(1.997 m)이 아니라 최대 내접원","1.77 m","Xu 2025 · Drones 9(3):190"],
 ["전개 지연  τ","발사 결심부터 포획 판정까지. 네트 비행 0.15 + 재관측 0.10 + 판단 0.05","0.30 s","Xu 2025 + 센서 사양"],
 ["협력 필요 경계  a*","완벽히 겨눴을 때의 상한. 넘으면 네트로는 불가능.   a* = 2ρ / τ²","39.3 m/s²","본 연구 유도"],
 ["겨냥 경계  a*(ψ)","남는 조준각 ψ 를 넣은 경계.   a*(ψ) = 2d (tanθ − ψ) / τ²,   ψ 실측 4.3°","25.8 m/s²","본 연구 · ψ 실측"],
 ["무력화","공격 드론을 막는 데 성공. 네트 포획과 물리 요격을 모두 포함","—","우리 정의"],
 ["비손실","무력화 중 기체가 온전한 비율. 우리 2차 지표","—","우리 정의"],
 ["물리 요격 성립 거리","표적 반치수 0.21 + 요격기 0.25 + 유도오차 0.1~0.4","0.75 m","Drones 2026 · 10(6):420"],
 ["지향 각속도 한계","네트를 겨눌 때 방향을 돌릴 수 있는 최대 속도","2.0 rad/s","Pliska 2024 · RA-L"],
 ["공격자 최대 기동 가속도","매 판 무작위로 뽑는 위협 등급. 방어자 능력은 비례해 따라감(가속 0.35배)","11~78 m/s²","Pliska 2024 · RA-L"]];
let ty=1.78;
TERMS.forEach((r,i)=>{
  const h=0.32;
  if(i%2===1) s.addShape(p.ShapeType.rect,{x:0.55,y:ty,w:12.28,h:h,fill:{color:"F6F9FE"},line:{color:"F6F9FE"}});
  s.addText(r[0],{x:TX[0]+0.10,y:ty,w:TW[0]-0.18,h:h,fontSize:10.0,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
  s.addText(r[1],{x:TX[1]+0.10,y:ty,w:TW[1]-0.18,h:h,fontSize:9.6,color:SLATE,fontFace:KR,margin:0,valign:"middle",lineSpacingMultiple:1.05});
  s.addText(r[2],{x:TX[2]+0.05,y:ty,w:TW[2]-0.10,h:h,fontSize:10.2,bold:true,color:r[2]==="—"?GREY:NAVY,fontFace:KR,margin:0,valign:"middle",align:"center"});
  s.addText(r[3],{x:TX[3]+0.10,y:ty,w:TW[3]-0.18,h:h,fontSize:9.3,color:GREY,fontFace:KR,margin:0,valign:"middle"});
  s.addShape(p.ShapeType.line,{x:0.55,y:ty+h,w:12.28,h:0,line:{color:"E3EAF5",width:0.75}});
  ty+=h;
});

/* ── 참고문헌 ───────────────────────────────────────────────────── */
card(s,0.55,5.70,12.28,0.94,"F4F8FF","C6D6EE");
s.addText("참고문헌",{x:0.78,y:5.74,w:2.6,h:0.22,fontSize:11.5,bold:true,color:NAVY,fontFace:KR,margin:0,valign:"middle"});
s.addText([
 {text:"[1] ",options:{bold:true,color:NAVY}},
 {text:"Xu, R.; Peng, Q.; Wu, H. “Optimization Design of Flexible Net Capture System for Low, Slow, and Small Unmanned Aerial Vehicles Based on Improved Multi-Objective Wolf Pack Algorithm.” Drones 2025, 9(3), 190.  doi:10.3390/drones9030190\n"},
 {text:"[2] ",options:{bold:true,color:NAVY}},
 {text:"Pliska, M.; Vrba, M.; Báča, T.; Saska, M. “Towards Safe Mid-Air Drone Interception: Strategies for Tracking & Capture.” IEEE Robotics and Automation Letters 2024, 9(10), 8810–8817.  arXiv:2405.13542\n"},
 {text:"[3] ",options:{bold:true,color:NAVY}},
 {text:"Rothe, J. et al. “Autonomous Drone-on-Drone Interception Using an Integrated LiDAR–Vision Detection System for High-Precision Capture.” Drones 2026, 10(6), 420.\n"},
 {text:"[4] ",options:{bold:true,color:NAVY}},
 {text:"Gavin, Bronz. “Intercepting an Agile Target with Net-Carrying Drones using Competitive Multi-Agent Reinforcement Learning.” arXiv:2607.05939 (preprint) — 가장 가까운 경쟁 연구"}],
 {x:0.78,y:5.96,w:11.85,h:0.62,fontSize:7.2,color:SLATE,fontFace:KR,margin:0,valign:"top",lineSpacingMultiple:1.08});

/* ── 연구비 집행 ─────────────────────────────────────────────────── */
card(s,0.55,6.78,12.28,0.52,LIGHT);
s.addText([{text:"연구비 집행  ",options:{bold:true,color:NAVY,fontSize:11}},
           {text:"Claude Max 구독 — 월 $＿＿＿ × ＿＿＿ 개월 = $＿＿＿",options:{fontSize:11}},
           {text:"      사용처 : 코드 작성 · 문헌 대조 · 검증 스크립트 작성",options:{fontSize:10}}],
  {x:0.78,y:6.78,w:11.85,h:0.52,color:SLATE,fontFace:KR,margin:0,valign:"middle"});

s.addNotes("부록. 교수님 피드백 3번(용어 정의)에 대응. 본문 숫자는 전부 이 표에서 옴. 연구비 금액은 채워 넣을 것.");

p.writeFile({fileName:"URP_중간보고_2026-08-03.pptx"}).then(f=>console.log("written",f));
