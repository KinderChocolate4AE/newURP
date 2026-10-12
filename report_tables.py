"""Markdown tables for REPORT.md straight from runs/*.json(l). python report_tables.py > runs/tables.md"""
import json, glob, os

J = lambda p: json.load(open(p))
pct = lambda x: "—" if x is None else f"{100 * x:.1f}"


def row(*c):
    print("| " + " | ".join(str(x) for x in c) + " |")


def rp_of(names):
    rs = {n: J(f"runs/{n}.json")["def_vs_this_red"] for n in names if os.path.exists(f"runs/{n}.json")}
    w = min(rs, key=lambda k: rs[k]["intercept"])
    return rs, w


print("### S2 (n=1, 8 seed × 1000 판) — 간판 = 그 방어 전용 새 레드팀 3개 중 최악 (fresh)\n")
row("방어", "vs 스크립트 요격 (net / lim / 누출)", "fresh 최악 요격 (net / lim / 누출 / 시간초과)", "fresh 3개", "판당 limiter 소모 (스크립트 / fresh 최악)", "학습 풀 상대 최소 (보조, 전이)")
row(*["---"] * 6)
fixed = [("원 스크립트 (기준선)", "runs/S2_baseline.json", "n1_mix", ["S2_RP_script_s1", "S2_RP_script_s2", "S2_RP_script_s3"], None),
         ("GK 스크립트", "runs/S2GK_script_vs_script.json", "res", ["S2GK_RP_script_s1", "S2GK_RP_script_s2", "S2GK_RP_script_s3"], None),
         ("e4 (학습, 원 prior)", "runs/S2_e4_c02_fp1.json", "vs_script", ["S2_RP_e4_s1", "S2_RP_e4_s2", "S2_RP_e4_w"], "runs/S2_e4_c02_fp1.json")]
for name, f, key, reds, poolf in fixed:
    v = J(f)[key]
    rs, w = rp_of(reds)
    fw = rs[w]
    pm = None
    if poolf:
        d = J(poolf); pm = min(x for k, x in d.items() if k.startswith("vs_S2"))
    row(name, f"{pct(v['intercept'])} ({pct(v['net'])} / {pct(v['lim'])} / {pct(v['leak'])})",
        f"**{pct(fw['intercept'])}** ({pct(fw['net'])} / {pct(fw['lim'])} / {pct(fw['leak'])} / {pct(fw['timeout'])})",
        " / ".join(pct(rs[k]["intercept"]) for k in rs), f"{v['lim']:.3f} / {fw['lim']:.3f}", pct(pm))
for lin in ("A", "B", "C"):
    p = f"runs/psro_{lin}.jsonl"
    if not os.path.exists(p):
        continue
    for l in open(p):
        d = json.loads(l)
        if "aborted_at" in d:
            row(f"{lin}: 강제 종료 {d['aborted_at']} ({d['job']})", "", "", "", "", ""); continue
        v = d["vs_script"]; fw = d["fresh"][d["fresh_min_team"]]
        row(f"{d['defender']} ({d['time']})", f"{pct(v['intercept'])} ({pct(v['net'])} / {pct(v['lim'])} / {pct(v['leak'])})",
            f"**{pct(fw['intercept'])}** ({pct(fw['net'])} / {pct(fw['lim'])} / {pct(fw['leak'])} / {pct(fw['timeout'])})",
            " / ".join(pct(x["intercept"]) for x in d["fresh"].values()), f"{v['lim']:.3f} / {fw['lim']:.3f}", pct(d["pool_min"]))

print("\n### 전이 숫자 (그 방어 전용 레드팀이 아님 — 이전 방어용 레드팀 상대)\n")
row("방어", "이전 방어용 레드팀 상대 최소 (전이)", "전용 새 레드팀 상대 최소 (fresh)")
row("---", "---", "---")
for name, f, reds in (("e4", "runs/S2_e4_c02_fp1.json", ["S2_RP_e4_s1", "S2_RP_e4_s2", "S2_RP_e4_w"]),
                      ("f3", "runs/S2_f3_hist3_ls1.json", None), ("g1", "runs/S2GK_g1.json", None)):
    d = J(f); tm = min(x for k, x in d.items() if k.startswith("vs_S2"))
    fr = pct(rp_of(reds)[0][rp_of(reds)[1]]["intercept"]) if reds else "측정 안 함 (PSRO 시작점으로만 사용)"
    row(name, pct(tm), fr)
