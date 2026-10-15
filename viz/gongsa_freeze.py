"""공사 원고 (spine docs/140) — 10/18 수치 동결 표 + 단락 논리 사슬 (대시보드가 소비).

원칙: 원고에 쓸 표기 ("frozen") 와 원자료에서 다시 계산한 표기 ("value") 를 나란히 둔다.
  PASS  = 같다 · CHECK = 다르다 (원고 표기나 원자료 중 하나를 사람이 고친다) · EXT = 외부 문헌 (코드 검증 대상 아님).
판정을 새로 만들지 않는다. 숫자의 뜻·조건은 각 행의 label / cond / note 에 적는다.
실행: python viz/gongsa_freeze.py → artifacts/paper1/freeze_1018.{json,md}. CHECK 가 있으면 exit 1.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import paper1_logic as P  # noqa: E402

A = P.A
med = statistics.median


def _f(x, nd):
    return f"{x:.{nd}f}"


def _pct(n, nd=1, of=240):
    return f"{100 * n / of:.{nd}f}%"


def _row(i, para, what, frozen, value, src, label, cond="", note=""):
    return {"id": i, "para": para, "what": what, "frozen": frozen, "value": value,
            "status": "PASS" if frozen == value else "CHECK", "src": src, "label": label, "cond": cond, "note": note}


def _dmax_plane(R, w, th):
    """사거리 끝이 축 방향 평면일 때 축을 φ 기울여 늘릴 수 있는 D_max: x sin(θ−φ) ≥ w, x cosφ + w ≤ R."""
    lo, hi = 0.0, th
    for _ in range(80):  # (R−w)·sin(θ−φ)/cosφ = w 의 근 (φ 에 단조 감소)
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if (R - w) * math.sin(th - mid) / math.cos(mid) > w else (lo, mid)
    return (R - w) / math.cos(lo)


def rows(root):
    root = pathlib.Path(root)
    an = P.analytic(root)
    th, R, a, tau, dt, V, w = (math.radians(an["theta_deg"]), an["R"], an["a"], an["tau"], an["dt"], an["V"], an["r"])
    half = R * math.tan(th)
    chi, chig = 1 / an["rho"], 1 / an["rho0"]
    chiT = lambda T: chig * (1 - T * V / R)
    a_of = lambda c: c * 2 * half / tau ** 2
    armc1 = P._j(root, f"{A}/armc1/readout.json")
    mu = float(re.match(r"m([\d.]+)_", next(iter(armc1["cells"]))).group(1))
    src_k = [f"{A}/e7a/probe.json (consts)", f"{A}/e7a3/overlay.json (V_bar)"]
    out = []

    # ---- §3 상수 --------------------------------------------------------------
    out.append(_row("F01", "3-1·3-2 표 1", "기준 상수",
                    "dt 0.05 s · τ 0.30 s · θ 12.15° · R_max 8.22 m · ρ 1.77 m · a 20.45 m/s² · V_c 23.01 m/s · 방어 가속 7.16 m/s² (0.35배)",
                    f"dt {_f(dt, 2)} s · τ {_f(tau, 2)} s · θ {_f(an['theta_deg'], 2)}° · R_max {_f(R, 2)} m · ρ {_f(half, 2)} m · "
                    f"a {_f(a, 2)} m/s² · V_c {_f(V, 2)} m/s · 방어 가속 {_f(mu * a, 2)} m/s² ({mu:g}배)",
                    src_k + [f"{A}/armc1/readout.json (셀 m0.35)"], "정의", "KSAS 기준 조건"))
    out.append(_row("F02", "3-3", "도망 거리·χ", "w 0.92 m · χ 0.52", f"w {_f(w, 2)} m · χ {_f(chi, 2)}",
                    src_k, "정의", "w = ½aτ², χ = w/ρ"))

    # ---- §4 해석 ---------------------------------------------------------------
    out.append(_row("F03", "4-1 (2-2)", "존재 경계 (KSAS 인용)", "χ*_geom 0.808 · D_min 4.37 m · D_max 7.30 m · a 31.8 m/s² (τ 0.30 s)",
                    f"χ*_geom {_f(chig, 3)} · D_min {_f(w / math.sin(th), 2)} m · D_max {_f(R - w, 2)} m · "
                    f"a {_f(a_of(chig), 1)} m/s² (τ {_f(tau, 2)} s)",
                    src_k, "해석 (층 1)", "최대 기동으로 즉시 회피하는 위협, 점질량·등방 가속"))
    out.append(_row("F04", "4-2·요-3·6-1", "실용 창 경계 χ*_T", "0.355 (T_req 0.2 s) · 0.412 (0.175 s)",
                    f"{_f(chiT(0.2), 3)} (T_req 0.2 s) · {_f(chiT(0.175), 3)} (0.175 s)",
                    src_k + ["artifacts/paper1/window_check.json"], "해석 (층 2)", "정면 접근 기준 · T_req 는 예시값 (운용 요구 주체가 정함)"))
    Ts = (0.1, 0.2, 0.3)
    out.append(_row("F05", "4-2·표 1 하단·6-1", "T_req 표",
                    "0.1/0.2/0.3 s → χ*_T 0.582/0.355/0.129 → a ≤ 22.9/14.0/5.1 m/s²",
                    "/".join(f"{T:g}" for T in Ts) + " s → χ*_T " + "/".join(_f(chiT(T), 3) for T in Ts) +
                    " → a ≤ " + "/".join(_f(a_of(chiT(T)), 1) for T in Ts) + " m/s²",
                    src_k, "해석 (층 2)", f"τ {_f(tau, 2)} s, 이 net 기하 (반각 12.15°·사거리 8.22 m) 전용"))
    out.append(_row("F06", "4-2·6-3", "창 길이 극한·속도 한계", "χ→0 극한 0.36 s · V_c 한계 41 m/s (R 8.22 m) · 125 m/s (R 25 m)",
                    f"χ→0 극한 {_f(R / V, 2)} s · V_c 한계 {R / 0.2:.0f} m/s (R {_f(R, 2)} m) · {25 / 0.2:.0f} m/s (R 25 m)",
                    src_k, "해석 (층 2)", "T_req 0.2 s"))
    Tw = (R / V) * (1 - chi / chig)
    out.append(_row("F07", "4-4 → 5-2 조건", "현행 모델 net 의 정면 창 (χ 0.52)", "약 0.13 s", f"약 {_f(Tw, 2)} s",
                    src_k, "해석 (층 2)", "정면 기준값 — 측정값 아님", f"반올림 전 {_f(Tw, 4)} s (소수 둘째 자리 반올림)"))
    tl = {t["class"]: t for t in P.threat_ladder(root, an)}
    pick = [("DJI Mavic 3 (틸트 35°)", "Mavic급"), ("DJI Phantom 4 (틸트 42°)", "Phantom급"),
            ("표준 쿼드 (Foehn 2021)", "표준 쿼드"), ("레이싱 쿼드 (추력비 4)", "레이싱")]

    def _acc(x):
        return f"≈{x:.0f}" if x > 30 else f"{x:.1f}"
    out.append(_row("F08", "4-4·그림 2", "위협 등급별 χ (τ 0.30 s)",
                    "계수 0.0254 · Mavic급 6.9→0.175 · Phantom급 8.8→0.224 · 표준 쿼드 17.4→0.442 · 레이싱 ≈39→0.99",
                    f"계수 {_f(tau ** 2 / (2 * half), 4)} · " + " · ".join(
                        f"{lbl} {_acc(tl[k]['a'])}→{_f(1 / tl[k]['rho'], 2 if tl[k]['a'] > 30 else 3)}" for k, lbl in pick),
                    src_k + ["temp_research_note/2026-10-11b_e3_t0_anchor_real_nets_rho_2p8_to_4p4_vs_a20_huh_dwell_in_paper_uncited.md"],
                    "조건부 (위협 가속은 사양에서 도출)", "이상적 반응 회피자 · 이 net 기하 전용",
                    "가속 도출 출처 (제조사 사양) 가 장부 docs/131 에 W 행으로 없음 → 행 추가 필요"))
    Dm2, Dmin = _dmax_plane(R, w, th), w / math.sin(th)
    out.append(_row("F09", "4-2 각주", "사거리 끝 평면 효과", "D_max 7.30 → 7.33 m (창 길이 +0.9%)",
                    f"D_max {_f(R - w, 2)} → {_f(Dm2, 2)} m (창 길이 +{100 * ((Dm2 - Dmin) / (R - w - Dmin) - 1):.1f}%)",
                    src_k, "해석 (층 2)", "축 기울기 최적화, 가까운 끝 D_min 불변"))
    chig_d = 1 / (math.tan(th) * (1 + 1 / math.sin(th - 0.05)))
    out.append(_row("F10", "4-3·6-3", "조준 오차 δ 0.05 rad", "χ*_geom 0.808 → 0.645 (−20%)",
                    f"χ*_geom {_f(chig, 3)} → {_f(chig_d, 3)} ({100 * (chig_d / chig - 1):.0f}%)".replace("-", "−"),
                    src_k, "해석 (층 1)", "정확식 χ*_geom(δ) = 1/[tanθ(1+1/sin(θ−δ))] — 선형 근사와 섞지 않음"))
    sens = lambda t: (math.cos(t) / (1 + math.sin(t))) ** 2 / math.sin(t)
    s1, s2 = sens(th), sens(math.radians(3.4))
    out.append(_row("F11", "4-3·6-3", "경계의 조준 오차 민감도 |dχ*/dδ|", "3.1 /rad (12.15°) · 15 /rad (3.4°) · 약 5배",
                    f"{_f(s1, 1)} /rad (12.15°) · {s2:.0f} /rad (3.4°) · 약 {s2 / s1:.0f}배",
                    [], "해석 (층 1)", "χ*_geom²/sinθ"))
    ac = P._j(root, "artifacts/paper1/assumption_check.json")
    base = next(r for r in ac["rows"] if r["kind"] == "base")
    react = next(r for r in ac["rows"] if r["kind"] == "reaction" and abs(r["tau_r"] - 0.15) < 1e-9)
    f_r = ((tau - 0.15) / tau) ** 2
    out.append(_row("F12", "4-3·4-4", "회피 반응 지연 τ_r 0.15 s", "χ × 1/4 (수치 경계 4.0배)",
                    f"χ × 1/{1 / f_r:.0f} (수치 경계 {react['numeric'] / base['numeric']:.1f}배)",
                    ["artifacts/paper1/assumption_check.json"], "해석 + 수치 확인", "χ_eff = χ[(τ−τ_r)/τ]²"))
    wc = P._j(root, "artifacts/paper1/window_check.json")
    n_ok = sum(r["pass"] for r in ac["rows"])
    out.append(_row("F13", "4-2·4-3 (검증 문장)", "수치 검증",
                    "창 길이 식 75/75 PASS (최대 차 0.003 s) · 가정 민감도 12/12 PASS (최대 상대 오차 ≤ 1%)",
                    f"창 길이 식 {sum(r['pass'] for r in wc['rows'])}/{wc['n']} {wc['verdict']} (최대 차 {_f(wc['max_abs_err_s'], 3)} s) · "
                    f"가정 민감도 {n_ok}/{len(ac['rows'])} {ac['verdict']} (최대 상대 오차 "
                    + ("≤ 1%" if ac["max_abs_rel_err"] <= 0.01 else f"{100 * ac['max_abs_rel_err']:.2f}%") + ")",
                    ["artifacts/paper1/window_check.json", "artifacts/paper1/assumption_check.json"],
                    "수치 검증 (사전 허용치)", "허용치: 창 max(2%, 0.05 s) / 가정 2%",
                    "가정 민감도 최대 상대 오차 1.02% — '≤ 1%' 표기는 틀림 → '약 1%' 또는 '2% 허용치 안' 으로"))

    # ---- 4-5 프로브 --------------------------------------------------------------
    pr = P.probe(root)
    nvar = len(P._j(root, f"{A}/e7a/probe.json")["rho"])
    out.append(_row("F14", "4-5·그림 3 캡션", "시뮬레이션 검증 (프로브)", "순위상관 0.93 (반복 0.94) · 경계 일치 11/12 · 사양 변형 12",
                    f"순위상관 {_f(pr['spearman']['첫 실행'][0], 2)} (반복 {_f(pr['spearman']['같은 seed 재실행'][0], 2)}) · "
                    f"경계 일치 {pr['overlay_agree']} · 사양 변형 {nvar}",
                    [f"{A}/e7a/probe.json", f"{A}/e7a2/probe.json", f"{A}/e7a3/overlay.json"], "확정 (층 3, 검증용)",
                    "비공진화 공격자 · 쏘지 않는 기록 (낙관)", "동점 보정 순위상관 (저장값 0.951 은 쓰지 않음). 재실행 = 같은 seed (독립 재현 아님)"))

    # ---- §5 학습 방어 다섯 가지 ----------------------------------------------------
    e3 = P._j(root, f"{A}/e3/stage1/stage1_readout.json")
    b1r = P._j(root, f"{A}/e3b/phase1/readout.json")
    b2r = P._j(root, f"{A}/e3b/phase2/readout.json")
    armd = P._j(root, f"{A}/armd/readout.json")
    r1v = [c["ceiling_s"] for c in e3["cells"]]
    r2v = [c[k] for c in b1r["cells"] for k in ("ceil_M1", "ceil_M2")]
    r3d = [s["ceil_det"] for c in b2r["cells"].values() for arm in ("armA", "armB") for s in c[arm]["seeds"].values()]
    r3s = [s["ceil_sto"] for c in b2r["cells"].values() for arm in ("armA", "armB") for s in c[arm]["seeds"].values()]
    r4d = [s["ceil_det"] for s in armc1["cells"]["m0.35_n1"]["seeds"].values()]
    r4n = [r["net"] for r in P.current_net(root)["rows"]]
    r5s = [s["ceil_sto"] for c in armd["cells"].values() for s in c["seeds"].values()]
    mx = max(max(r1v), max(r2v), max(r3d), max(r4d), max(r5s))
    out.append(_row("F15", "5-2·표 2", "학습 방어 다섯 가지 (판정 계열)",
                    "고정 규칙 0–2% · 혼합 1–5 · 동시학습 결정적 1–11 · 판정 흉내 2–4 (net 만 1–3) · 기억+확률 ≤ 15 → 15판 이하 (약 6% 이하)",
                    f"고정 규칙 0–{math.ceil(100 * max(r1v) / 240)}% · 혼합 {min(r2v)}–{max(r2v)} · 동시학습 결정적 {min(r3d)}–{max(r3d)} · "
                    f"판정 흉내 {min(r4d)}–{max(r4d)} (net 만 {min(r4n)}–{max(r4n)}) · 기억+확률 ≤ {max(r5s)} → "
                    f"{mx}판 이하 (약 {round(100 * mx / 240)}% 이하)",
                    [f"{A}/e3/stage1/stage1_readout.json", f"{A}/e3b/phase1/readout.json", f"{A}/e3b/phase2/readout.json",
                     f"{A}/armc1/readout.json", f"{A}/armd/readout.json"],
                    f"{e3.get('decision', 'E3_BAND_EMPTY')} · {b1r['decision']} · {b2r['decision']} · {armc1['decision']} · {armd['decision']}",
                    "χ 0.52 한 점 · 레드팀 1천만 step · 240판",
                    f"판정 계열이 처방마다 다름 (고정 = ceiling_s 전 격자, 혼합 = M1/M2, 동시학습·판정 흉내 = 결정적, 기억 = 확률적). "
                    f"동시학습 확률 {min(r3s)}–{max(r3s)} 은 다른 모드용 레드팀 상대 (표 2 각주)"))
    out.append(_row("F15b", "5-2", "같은 셀 (판정 흉내 발사, 방어 가속 0.35배)", "2–4 (0.8–1.7%)",
                    f"{min(r4d)}–{max(r4d)} ({_pct(min(r4d))[:-1]}–{_pct(max(r4d))})",
                    [f"{A}/armc1/readout.json"], armc1["decision"], "χ 0.52 · 1천만 step"))

    # ---- 5-3 평가 방법 배율 --------------------------------------------------------
    ca = P.cross_audit(root)
    rs = sorted(ca["ratios"])
    out.append(_row("F16", "5-3·6-2·그림 4", "평가 방법 배율 (판정 2세트, 비교 4)", "중앙값 2.6–3.8배 (2.57 · 2.67 · 2.92 · 3.77) · 개별 0.5–17배",
                    f"중앙값 {_f(rs[0], 1)}–{_f(rs[-1], 1)}배 (" + " · ".join(_f(x, 2) for x in rs) + ") · "
                    f"개별 {_f(ca['slot_range'][0], 1)}–{ca['slot_range'][1]:.0f}배",
                    [f"{A}/e7b/readout.json", f"{A}/e7b2/readout.json", f"{A}/e7c/readout.json"], "확정 (비율 주장)",
                    "본 시뮬레이션, 레드팀 예산 1천만 step", f"slot 비교 {ca['n_slot']} (정합 천장 0 인 {ca['n_zero']} 제외)"))
    dd = P._j(root, "artifacts/paper1/descriptive/desc_1013.json")["1-2 cross_audit_E1"]
    third = (dd["all_55"]["ratio_det_line (median det|sto / median det|det)"],
             dd["all_55"]["ratio_sto_line (median sto|det / median sto|sto)"])
    lo3 = min(rs + list(third))
    out.append(_row("F17", "5-3", "세 번째 독립 방어 세트 포함 (기술)", "세 독립 방어 세트, 중앙값 1.9–3.8배",
                    f"세 독립 방어 세트, 중앙값 {_f(lo3, 1)}–{_f(rs[-1], 1)}배",
                    ["artifacts/paper1/descriptive/desc_1013.json"], "기술통계 (판정 아님)", "본 시뮬레이션, 1천만 step",
                    f"세 번째 세트 전체 55 slot = {_f(third[0], 2)} / {_f(third[1], 2)} → 하한 2.0. "
                    "1.9 는 바닥 점 (χ 0.52) 을 뺀 50 slot 의 1.88 — 어느 쪽을 쓸지 결정 필요"))
    r0 = P._j(root, f"{A}/r0/readout.json")
    cells = [c for s in r0["slots"].values() for c in s["cells"].values()]
    infl = sorted(((r["ratio"], r["lower95"]) for s in r0["slots"].values() for r in s["ratios"].values()), key=lambda x: x[1])
    over = [x for x in infl if x[1] > 1.5]
    under = [x for x in infl if x[1] <= 1.5]
    sds = [c["sd"] for c in cells]
    out.append(_row("F18", "5-3", "평가 반복성", "SD 2–7판 · BINOMIAL 8/8 · 과대평가 4칸 중 3칸 하한 2.0–8.0배 · 나머지 1.6배 (하한 1.4) · INFLATION_PARTIAL",
                    f"SD {min(sds):.0f}–{max(sds):.0f}판 · BINOMIAL {sum(c['label'] == 'R0_BINOMIAL' for c in cells)}/{len(cells)} · "
                    f"과대평가 {len(infl)}칸 중 {len(over)}칸 하한 {_f(over[0][1], 1)}–{_f(over[-1][1], 1)}배 · "
                    + " · ".join(f"나머지 {_f(r, 1)}배 (하한 {_f(lb, 1)})" for r, lb in under) + f" · {r0['inflation']}",
                    [f"{A}/r0/readout.json", "docs/135 §4"], r0["inflation"], "같은 방어·같은 레드팀, 환경 난수만 변경",
                    "칸 기준 = 하한 > 1.5 (docs/135 §2)"))

    # ---- 레드팀 예산 (R1) --------------------------------------------------------
    man = lambda f: (root / A / f).read_text(encoding="utf-8")
    ex = re.search(r'"exploiter": "[^"]*?(\de\+\d\d)', man("e7b_manifest.json")).group(1)
    df = re.search(r'"train": "[^"]*?(\d\.\de\d)', man("armc1_manifest.json")).group(1)
    r3e = max(re.findall(r"total-steps (\de\+\d\d)", man("r1_manifest.json")), key=float)
    out.append(_row("F19", "3-4 표 1b·5-1·6-2·7-1", "학습 예산", "레드팀 1e+07 step · 방어 학습 1.1e8 step · 강화 레드팀 3e+07 step",
                    f"레드팀 {ex} step · 방어 학습 {df} step · 강화 레드팀 {r3e} step",
                    [f"{A}/e7b_manifest.json", f"{A}/armc1_manifest.json", f"{A}/r1_manifest.json"], "설정",
                    "6-2 비용 문장: 3천만 vs 1.1억 (레드팀이 방어 학습보다 짧음)"))
    r1 = P._j(root, f"{A}/r1/readout.json")
    d = r1["d_b1_minus_b3"]
    out.append(_row("F20", "5-3·6-1 (★결재 10-14)", "레드팀 예산 3배 (같은 방어)",
                    "중앙값 20 → 8/240 (8.3% → 3.3%), −12 · d 양수 15/15, 중앙값 14 · BUDGET_UNDERTRAINED",
                    f"중앙값 {r1['median']['orig']:.0f} → {r1['median']['b3']:.0f}/240 ({_pct(r1['median']['orig'])} → {_pct(r1['median']['b3'])}), "
                    f"−{r1['median']['orig'] - r1['median']['b3']:.0f} · d 양수 {sum(x > 0 for x in d)}/{len(d)}, 중앙값 {med(d):.0f} · {r1['label']}",
                    [f"{A}/r1/readout.json", "docs/138 판독"], r1["label"], "본 시뮬레이션, 1천만 vs 3천만 step, 미수렴",
                    "공사 본문은 비율·방향만 (15 slot·중앙 14 는 쓰지 않음). 20 = 원래 1e7 착취자 재평가 (env-seed 0)"))
    pl = P.plateau(root)["결정적"]
    out.append(_row("F21", "6-1 (★결재 10-14)", "기준 이상 사양 천장 (중앙값 기준 10% 미만)",
                    "중앙값 21/240 (8.8%) < 10% · seed 범위 7–41",
                    f"중앙값 {pl['ceil_med']:.0f}/240 ({_pct(pl['ceil_med'])}) {'<' if pl['ceil_med'] / 240 < 0.10 else '≥'} 10% · "
                    f"seed 범위 {pl['ceil_range'][0]}–{pl['ceil_range'][1]}",
                    [f"{A}/e7b/readout.json"], "확정 (E7-b, 1천만 step)", "본 시뮬레이션, 레드팀 1천만 step, 중앙값 기준",
                    f"천장 = net 포획 + 직접 요격 (net 만 중앙값 {pl['net_med']:.0f}). 원고 'net 포획 10% 미만' 이면 'net 포획만 중앙값 "
                    f"{pl['net_med']:.0f}/240' 또는 '방어 성공' 으로 표현 맞출 것. 최대 41/240 = 17% → 중앙값 한정 필수"))

    # ---- ◇결재 A4 (기술통계) -----------------------------------------------------
    dsc = P._j(root, "artifacts/paper1/descriptive/desc_1013.json")
    six = dsc["1-3 six_way_r1.92"]
    win = six["창 뒤에 쏘고 놓침"] + six["창이 있었는데 안 쏨"]
    wl = dsc["1-4 window_vs_capture_E1b [episodes, net captures]"]
    d0 = wl["d0 (chi 0.520)"]
    d0w = sum(v[0] for k, v in d0.items() if k != "n_rob=0") / sum(v[0] for v in d0.values())
    d4 = wl["d4 (chi 0.435)"]
    ge4 = [v["n_rob=>=4"][1] / v["n_rob=>=4"][0] for v in wl.values()]
    out.append(_row("F22", "4-2 끝 (◇결재 A4, 대기)", "창 발생·미발사·창 길이별 포획",
                    "창 발생 53% (29–53%) · 그중 미발사 87% · 포획 2.9% → 16.3% · 0.2 s 이상 창 7–16%",
                    f"창 발생 {100 * win / six['n']:.0f}% ({100 * d0w:.0f}–{100 * win / six['n']:.0f}%) · 그중 미발사 "
                    f"{100 * six['창이 있었는데 안 쏨'] / win:.0f}% · 포획 {100 * d4['n_rob=1'][1] / d4['n_rob=1'][0]:.1f}% → "
                    f"{100 * d4['n_rob=>=4'][1] / d4['n_rob=>=4'][0]:.1f}% · 0.2 s 이상 창 {100 * min(ge4):.0f}–{100 * max(ge4):.0f}%",
                    ["artifacts/paper1/descriptive/desc_1013.json"], "기술통계 (판정 아님) · 결재 대기",
                    "전이 구간 학습 사다리 자료 (χ 0.52 점 + 촘촘한 사다리)",
                    "주의 3: (1) 전부 전이 구간 실험 자료 — spine 의 '전이 구간 숫자 공사판 미사용' 과 충돌. "
                    "(2) 29–53% 는 seed 산포가 아니라 두 실험 (χ 0.52 의 두 seed 세트) 차이. (3) 2.9% → 16.3% 는 χ 0.435 점 (현행 0.52 아님)"))

    # ---- 외부 문헌 (코드 검증 대상 아님) -------------------------------------------------
    for line in (root / "docs/131_paper1_v0_evidence_ledger.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(W\d+)\s*(✓|\(✓ 미러\))?\s*\|\s*(.+?)\s*\|", line)
        if m:
            chk = {"✓": "main 원문 대조 완료", "(✓ 미러)": "미러만 대조 — law.go.kr 원문 대조 필요"}.get(m.group(2), "main 미대조")
            out.append({"id": m.group(1), "para": "§1·§2·6-3", "what": m.group(3)[:90], "frozen": "—", "value": "—",
                        "status": "EXT", "src": ["docs/131 §3b"], "label": chk, "cond": "보도·발표에 따르면", "note": ""})
    return out


# ------------------------------------------------------------- 단락 논리 사슬 --
# 문장은 원고 문장이 아니라 색인 (docs/140 단계 2). 숫자는 F 행 참조로만.
CHAIN = [
    ("서론", [("요-3", "χ 에 접근 속도를 더한 설계 기준 · 다섯 가지 모두 낮음 · 평가 방법 배율", ["F04", "F15", "F16"]),
             ("1-1", "요격 드론이 실전 수단 · net 포획 요격기 조달 · 국내는 net 아님", ["W1", "W2", "W3", "W12", "W13"]),
             ("1-2", "전개 중 회피가 요구 성능에서 빠짐 · 무엇을 상대로 재느냐가 숫자를 바꿈 → 정량 기준 부재", []),
             ("1-3·1-4", "두 질문 (무엇을 요구 / 어떻게 재나) · KSAS 경계 계승 + 속력 확장", [])]),
    ("배경", [("2-1", "전개 시간의 독립 실측 공개 자료 없음 → ③ 세움", ["W4"]),
             ("2-2", "선행 포획 기준 (거리·각도·유지) · KSAS χ 와 남긴 속력 문제 → ① 세움", ["F03"]),
             ("2-3", "작전운용성능이 운용시험 대상을 정함 · 국외 '적응하는 적대자' · 국내 공개 지침 미발견 → ② 세움",
              ["W6", "W7", "W8", "W9", "W11"])]),
    ("분석 틀", [("3-1·3-2", "교전 모델 · net 기준 조건 = KSAS", ["F01"]),
                ("3-3", "보장 포획 순간 · 창의 세 층 (존재 경계 / 실용 창 / 측정 창)", ["F02"]),
                ("3-4", "시험 조건표 (표 1b) — 숫자는 이 조건 한정", ["F19"])]),
    ("분석 1 — 요구 성능", [("4-1", "존재 경계 (층 1, 인용) — 위치·조준·시점 무관", ["F03"]),
                         ("4-2", "정면 창 = χ 의 직선 → χ ≤ χ*_T, T_req·V_c < R_max (층 2, 설계 기준)",
                          ["F04", "F05", "F06", "F09", "F13"]),
                         ("4-3", "반응 지연·추적 지연·조준 오차 → 실측해야 할 상수 (③)", ["F10", "F11", "F12", "F13"]),
                         ("4-4", "위협 등급별: 넉넉 / T_req 미달 / 창 없음 · 현행 모델 net 은 미달", ["F08", "F07"]),
                         ("4-5", "구현에서도 순서가 같다 (층 3, 검증용)", ["F14"])]),
    ("분석 2 — 시험평가", [("5-1", "그 방어·그 모드 전용 레드팀 · 예산은 시험 조건", ["F19"]),
                        ("5-2", "χ 0.52 에서 다섯 가지 모두 사전 기준 미달 (절대 주장, 한정)", ["F07", "F15", "F15b"]),
                        ("5-3", "같은 방어를 다르게 재면 부풀려짐 · 레드팀 강도도 숫자를 정함 (비율 주장)",
                         ["F16", "F17", "F18", "F20"])]),
    ("결론", [("6-1", "① 요구 성능 명시 항목 + 필요조건 (충족해도 보장 안 함)", ["F05", "F20", "F21"]),
             ("6-2", "② 적응형 레드팀 + 시험 조건 보고 · 비용", ["F16", "F19", "W8"]),
             ("6-3", "③ 전개 시간 τ(D)·조준 정확도 실측 → τ·δ → χ → 창 → 시험 한 사슬", ["F10", "F11", "F06", "W5", "W7", "W13"]),
             ("7", "한계 · 후속 (AIAA) 한 줄 · 결론", ["F19", "F20"])]),
    ("◇결재 대기", [("A2(3)", "기동력 열세가 큰 사양에서는 하드웨어 요구 성능이 먼저", []),
                  ("A4", "창이 있어도 대부분 쏘지 않았다 — T_req 충족 ≠ 포획", ["F22"])]),
]


def model(root):
    rs = rows(root)
    ids = {r["id"] for r in rs}
    missing = sorted({i for _, ps in CHAIN for _, _, refs in ps for i in refs} - ids)
    if missing:
        raise RuntimeError(f"CHAIN 이 없는 행을 참조: {missing}")
    count = {k: sum(r["status"] == k for r in rs) for k in ("PASS", "CHECK", "EXT")}
    return {"rows": rs, "chain": CHAIN, "count": count}


def _md(m):
    L = ["# 공사 원고 수치 동결 표 (10/18) — 자동 생성, 손으로 고치지 말 것", "",
         "생성: `python viz/gongsa_freeze.py` · 원자료 재계산 · spine = docs/140", "",
         f"PASS {m['count']['PASS']} · **CHECK {m['count']['CHECK']}** · EXT (외부 문헌) {m['count']['EXT']}", "",
         "| ID | 원고 위치 | 무엇 | 원고 표기 | 재계산 | 상태 | 라벨 | 조건 | 비고 | 출처 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in m["rows"]:
        L.append("| " + " | ".join(str(x).replace("|", "/") for x in (
            r["id"], r["para"], r["what"], r["frozen"], r["value"],
            f"**{r['status']}**" if r["status"] == "CHECK" else r["status"],
            r["label"], r["cond"], r["note"], "<br>".join(r["src"]))) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    m = model(root)
    out = root / "artifacts/paper1"
    (out / "freeze_1018.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "freeze_1018.md").write_text(_md(m), encoding="utf-8")
    for r in m["rows"]:
        if r["status"] == "CHECK":
            print(f"CHECK {r['id']} {r['what']}\n  원고 {r['frozen']}\n  재계산 {r['value']}\n  {r['note']}")
    print(m["count"])
    sys.exit(1 if m["count"]["CHECK"] else 0)
