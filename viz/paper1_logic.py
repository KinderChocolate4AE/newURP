"""Paper 1 v0 논리 지도 — 대시보드용 view model (build_research_evidence_dashboard.py 가 소비).

원칙: 숫자를 손으로 적지 않는다. 모든 숫자는 빌드 시점에 원자료 (artifacts/fs1/*) 에서 다시 계산한다.
문장은 논문 문장이 아니라 근거 색인 (spine = docs/136, 장부 = docs/131). 판정을 새로 만들지 않는다.
결정론: 파일 목록은 정렬, 시각 정보 없음.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import statistics

A = "artifacts/fs1"
NET = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
MESSAGES = {
    "①": "net 사양 요구조건 — 보장 포획 창은 ρ (net 반폭 ÷ 펼쳐지는 동안 도망칠 수 있는 거리) 와 반각이, "
         "쓸 만한 길이는 여기에 사거리 ÷ 속도가 정한다",
    "②": "평가 방법 — 학습 방어는 그 방어 전용으로 학습된 착취자로 재야 한다 (아니면 2.6–3.8 배 부풀려진다)",
}
CUT_LINE = "필요조건은 해석이 정하고, 도달 수준은 적응 회피자가 정한다"
STATUS = {"확정": "원자료 재계산", "해석": "유도 — 사용자 재유도 필요", "기술통계": "사후 집계, 판정 아님",
          "대기": "봉인된 실험, 결과 대기", "조건부": "외부 자료·가정 조건부"}


def _j(root, rel):
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _eps(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _med(xs):
    return statistics.median(xs) if xs else None


def _g(v, nd=3):
    return f"{v:.{nd}g}" if isinstance(v, float) else str(v)


# ------------------------------------------------------------------ 해석 상수 --
def analytic(root):
    k = _j(root, f"{A}/e7a/probe.json")["consts"]
    vbar = _j(root, f"{A}/e7a3/overlay.json")["V_bar"]
    th, R, a, tau, dt = k["theta0"], k["range_max"], k["a_att"], k["tau0"], k["dt"]
    r = 0.5 * a * tau ** 2
    rho = R * math.tan(th) / r
    rho0 = 1 / math.cos(th) + math.tan(th)
    rstar = lambda T: rho0 / (1 - T * vbar / R)
    rho0_d = lambda d: math.tan(th) * (1 + 1 / math.sin(th - d))
    return {"theta_deg": math.degrees(th), "R": R, "a": a, "tau": tau, "dt": dt, "V": vbar, "r": r, "rho": rho,
            "rho0": rho0, "win_max_s": R / vbar, "rho_star_02": rstar(4 * dt), "rho_star_0175": rstar(3.5 * dt),
            "V_crit": R / (4 * dt), "aim_exact_005": rho0_d(0.05), "aim_lin_005": rho0 + 0.05 / math.sin(th),
            "aim_slope": 1 / math.sin(th), "pred_window_s_current": (R / vbar) * (1 - rho0 / rho)}


def threat_ladder(root, an):
    """모델 net (FS1 기하) 기준 위협 등급별 ρ. 위협 a = 노트 2026-10-11b (사양 틸트각·추력비에서 도출)."""
    classes = [("DJI Mavic 3 (틸트 35°)", 6.87), ("DJI Phantom 4 (틸트 42°)", 8.83), ("표준 쿼드 (Foehn 2021)", 17.4),
               ("FS1 공격자", an["a"]), ("레이싱 쿼드 (추력비 4)", 38.8), ("극한 레이서 (Song 2023)", 117.0)]
    out = []
    for name, a in classes:
        rho = an["rho"] * an["a"] / a
        out.append({"class": name, "a": a, "rho": rho, "window": rho >= an["rho0"]})
    return out


# ---------------------------------------------------------------- 실험 집계 ---
def current_net(root):
    rd = _j(root, f"{A}/armc1/readout.json")["cells"]["m0.35_n1"]["seeds"]
    rows, has_win = [], False
    for p in sorted((root / A / "armc1" / "m0.35_n1").glob("s*/eval/episodes.jsonl")):
        d = [e for e in _eps(p) if e["defender"] == "learned_det" and e["group"] == "ex_judge"]
        has_win = has_win or ("n_rob" in d[0])
        rows.append({"seed": p.parents[1].name, "fired_eps": sum(e["n_fire"] > 0 for e in d),
                     "net": sum(e["label"] in NET for e in d), "n": len(d)})
    return {"ceil_det": [rd[s]["ceil_det"] for s in sorted(rd)], "rows": rows, "window_recorded": has_win}


def plateau(root):
    out = {}
    for line, exp, key, dn, g in (("결정적", "e7b", "ceil_det", "learned_det", "ex_judge"),
                                  ("확률적", "e7b2", "ceil_sto", "learned_sto", "ex_judge_sto")):
        rd = _j(root, f"{A}/{exp}/readout.json")["variants"]
        ceil = [s[key] for v in rd.values() for s in v["seeds"].values()]
        nets, dec, outside = [], [], 0
        for p in sorted((root / A / exp).glob("*/s*/eval/episodes.jsonl")):
            d = [e for e in _eps(p) if e["defender"] == dn and e["group"] == g]
            w = [e for e in d if e.get("n_rob", 0) > 0]
            nets.append(sum(e["label"] in NET for e in d))
            dec.append((len(w), sum(e["n_fire"] > 0 for e in w), nets[-1]))
            outside += sum(e["label"] in NET for e in d if e.get("n_rob", 0) == 0)
        per_var = {vn: _med([s[key] for s in v["seeds"].values()]) for vn, v in rd.items()}
        out[line] = {"ceil_med": _med(ceil), "ceil_range": (min(ceil), max(ceil)), "net_med": _med(nets),
                     "per_variant": {f"{rd[vn]['rho']:.2f}{' ma' if vn.endswith('ma') else ''}": m
                                     for vn, m in per_var.items()},
                     "win_eps_range": (min(x[0] for x in dec), max(x[0] for x in dec)),
                     "win_eps_med": _med([x[0] for x in dec]), "fired_after_win_med": _med([x[1] for x in dec]),
                     "net_in_dec_med": _med([x[2] for x in dec]), "captures_outside_window": outside,
                     "slots": len(dec)}
    return out


def probe(root):
    ov = _j(root, f"{A}/e7a3/overlay.json")["summary"]
    sp = {name: _j(root, f"{A}/{d}/probe.json")["p_rho1"]["spearman"]
          for name, d in (("E7-a (첫 실행)", "e7a"), ("E7-a′ (재실행)", "e7a2"), ("E7-a3 (재실행, 겹쳐 보기용)", "e7a3"))}
    return {"overlay_agree": ov["classification_agree"], "overlay_spearman": ov["spearman_pred_vs_obs"], "spearman": sp}


def cross_audit(root):
    b, b2 = _j(root, f"{A}/e7b/readout.json")["variants"], _j(root, f"{A}/e7b2/readout.json")["variants"]
    c = _j(root, f"{A}/e7c/readout.json")["slots"]
    S = lambda src, f: _med([f(s) for v in src.values() for s in v["seeds"].values()])
    C = lambda k: _med([s["cross"][k] for v in c.values() for s in v.values()])
    m = {"기본 규칙 (천장 = net + 직접 요격)": {
            "결정적: 같은/다른": (S(b, lambda s: s["ceil_det"]), S(b2, lambda s: s["det_vs_sto_exploiter"])),
            "확률적: 같은/다른": (S(b2, lambda s: s["ceil_sto"]), S(b, lambda s: s["ceil_sto"]))},
         "두 번째 규칙 (천장 = net + 발사 후 직접 요격)": {
            "결정적: 같은/다른": (C("learned_det_vs_ex_judge"), C("learned_det_vs_ex_judge_sto")),
            "확률적: 같은/다른": (C("learned_sto_vs_ex_judge_sto"), C("learned_sto_vs_ex_judge"))}}
    ratios = [mis / mat for blk in m.values() for (mat, mis) in blk.values()]
    return {"matrix": m, "ratios": ratios}


def queue(root):
    """봉인된 후속 실험: manifest 해시와 harvest 된 판독 유무 (로컬 기준)."""
    items = [("E2 공격자 기동 개입", "docs/132", f"{A}/ami_manifest.json", f"{A}/ami/readout.json", "verdict"),
             ("E4 손잡이별 collapse 프로브", "docs/133", f"{A}/e4_manifest.json", f"{A}/e4/readout.json", None),
             ("E1 전이 구간 학습 사다리", "docs/134", f"{A}/e1_manifest.json", f"{A}/e1/readout.json", "verdict"),
             ("R0 평가 반복성", "docs/135 (예정)", None, None, None)]
    out = []
    for name, doc, man, rd, key in items:
        h = _j(root, man)["manifest_hash"] if man and (root / man).exists() else None
        res = None
        if rd and (root / rd).exists():
            r = _j(root, rd)
            res = (json.dumps(r.get(key), ensure_ascii=False) if key else
                   ", ".join(f"{k}: {r[k]['verdict']}" for k in ("P-E4a", "P-E4b", "P-E4c") if k in r))
        out.append({"name": name, "doc": doc, "hash": h, "readout": res})
    return out


def gaps(root):
    """docs/131 의 gap 행 (| G숫자 | 항목 | 상태 | ...)."""
    rows = []
    for line in (root / "docs/131_paper1_v0_evidence_ledger.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(G\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", line)
        if m:
            rows.append({"id": m.group(1), "item": m.group(2), "state": m.group(3)})
    return sorted(rows, key=lambda r: int(r["id"][1:]))


def figures(root):
    return [p.relative_to(root).as_posix() for p in sorted((root / "artifacts/paper1").glob("*.png"))]


# ------------------------------------------------------------------ 논리 사슬 --
def chain(root):
    an = analytic(root)
    cn, pl, pr, ca = current_net(root), plateau(root), probe(root), cross_audit(root)
    tl = threat_ladder(root, an)
    det, sto = pl["결정적"], pl["확률적"]
    nodes = [
        {"id": "L1", "msg": "①", "sec": "§4-2", "status": "해석",
         "claim": "보장 포획 창이 존재할 필요충분조건: ρ ≥ secθ + tanθ (반각만의 함수)",
         "nums": [f"반각 {an['theta_deg']:.1f}° → 경계 {an['rho0']:.3f}",
                  f"모델 net: τ {an['tau']} s, a {an['a']:.2f} → 도망 거리 {an['r']:.3f} m, ρ {an['rho']:.3f}"],
         "caveats": ["보조 세션 유도 → 사용자 재유도 후 사용 (AI 사용 명시)", "'불가능' 은 경계 미만에서만, 모델 안에서"],
         "src": [f"{A}/e7a/probe.json", "temp_research_note/2026-10-08_P-rho2_rho_star_derivation_k1_session.md"]},
        {"id": "L2", "msg": "①", "sec": "§4-3", "status": "해석",
         "claim": "0.2초 실용 창: ρ ≥ ρ* 그리고 0.2초 × 속도 < 사거리 (두 조건 모두)",
         "nums": [f"창 길이 상한 {an['win_max_s']:.3f} s (사거리 ÷ 속도 {an['V']})",
                  f"ρ*(0.2 s) {an['rho_star_02']:.3f} · ρ*(0.175 s) {an['rho_star_0175']:.3f}",
                  f"속도 한계 {an['V_crit']:.1f} m/s (사거리 {an['R']} m 에서)",
                  f"현행 ρ 의 예측 창 {an['pred_window_s_current']:.3f} s"],
         "caveats": ["등록은 학습 실험 전, 단 프로브 지도를 본 뒤 (blind 아님)", "정면 직선 접근 = 가장 짧은 경로 (보수)"],
         "src": [f"{A}/e7a3/overlay.json", "temp_research_note/2026-10-08c_p_rho2_registered_rho_star_2p81_v_bar_fixed_from_world_spec.md"]},
        {"id": "L3", "msg": "①", "sec": "§4-4", "status": "해석",
         "claim": "조준 오차는 창 존재 경계를 올린다 (δ ≥ 반각이면 창 없음)",
         "nums": [f"기울기 1/sinθ = {an['aim_slope']:.2f} /rad",
                  f"δ 0.05 rad: 정확 {an['aim_exact_005']:.3f} vs 선형 근사 {an['aim_lin_005']:.3f} (섞지 말 것)"],
         "caveats": ["추적 지연 식 [τ/(τ+L)]² 은 새 유도 — 사용자 확인 전 Remark 금지"], "src": []},
        {"id": "L4", "msg": "①", "sec": "§4-5 그림 2", "status": "조건부",
         "claim": "같은 모델 net 이 위협 등급에 따라 창이 넉넉하기도, 아예 없기도 하다 (필요 τ ∝ 1/√a)",
         "nums": [f"{t['class']}: a {t['a']:.3g} → ρ {t['rho']:.2f} ({'창 있음' if t['window'] else '창 없음'})" for t in tl],
         "caveats": ["모델 net 기하 전용 (실물 net 은 반각·사거리가 달라 경계도 다름)",
                     "위협 a 는 사양에서 도출, 전투 FPV 는 공개 자료 없음", "이상적 반응 회피자 가정"],
         "src": ["temp_research_note/2026-10-11b_e3_t0_anchor_real_nets_rho_2p8_to_4p4_vs_a20_huh_dwell_in_paper_uncited.md"]},
        {"id": "L5", "msg": "①", "sec": "§6.1", "status": "확정",
         "claim": "현행 모델 net (ρ 1.92): 전용 착취자 상대 천장이 바닥이고, 발사까지 가는 판이 드물다",
         "nums": [f"천장 (net + 직접 요격) seed별 {cn['ceil_det']} /240"] +
                 [f"{r['seed']}: 발사한 판 {r['fired_eps']} · net 포획 {r['net']} /{r['n']}" for r in cn["rows"]] +
                 [f"창 발생 수 기록: {'있음' if cn['window_recorded'] else '없음 → 창이 안 생겼는지/안 쐈는지 구분 불가'}"],
         "caveats": ["오프라인 AUC (6개 중 5개 ≥ 0.9) 는 판별 능력일 뿐 실전 발사 시점이 아님, 집계 규칙 사후 확정",
                     "같은 지표 (창 발생) 는 전이 사다리 ρ 1.92 점이 줌"],
         "src": [f"{A}/armc1/readout.json", "temp_research_note/2026-10-07h_armc1_null_detection_ok_window_generation_is_the_bottleneck.md"]},
        {"id": "L6", "msg": "①", "sec": "§6.2 그림 3(a)", "status": "확정",
         "claim": "프로브 창은 ρ 와 함께 커지고, 등록 경계가 열림/닫힘을 거의 맞힌다",
         "nums": [f"순위상관 (ρ, 창): " + " · ".join(f"{k} {v:.3f}" for k, v in pr["spearman"].items()),
                  f"등록 경계 겹치기: 일치 {pr['overlay_agree']}, 순위상관 (예측, 관측) {pr['overlay_spearman']:.3f}"],
         "caveats": ["프로브 = 비적응 (구세계 적응) 공격자, 쏘지 않는 기록", "예측은 관측보다 0.5–1.3 tick 높음 (상한)",
                     "ρ 가 클 때 창이 5 tick 에서 멈추는 이유 미확인"],
         "src": [f"{A}/e7a/probe.json", f"{A}/e7a2/probe.json", f"{A}/e7a3/overlay.json"]},
        {"id": "L7", "msg": "①", "sec": "§6.2 그림 3(b)", "status": "확정",
         "claim": "net 사양을 올리면 천장은 바닥에서 오르지만 ρ 3.9–11.8 에서는 평평하다",
         "nums": [f"결정적: 천장 중앙값 {det['ceil_med']} (범위 {det['ceil_range'][0]}–{det['ceil_range'][1]}), net 만 {det['net_med']}",
                  f"확률적: 천장 중앙값 {sto['ceil_med']} (범위 {sto['ceil_range'][0]}–{sto['ceil_range'][1]}), net 만 {sto['net_med']}",
                  "결정적 변형별: " + ", ".join(f"ρ {k} → {_g(v)}" for k, v in det["per_variant"].items()),
                  "확률적 변형별: " + ", ".join(f"ρ {k} → {_g(v)}" for k, v in sto["per_variant"].items())],
         "caveats": ["착취자 1천만 step · a 20.45 · 교전 설정 하나 조건부", "ρ 1.92–3.92 사이 학습 점 없음 (전이 사다리 대기)",
                     "천장 정의: 기본 규칙 = net + 직접 요격"],
         "src": [f"{A}/e7b/readout.json", f"{A}/e7b2/readout.json"]},
        {"id": "L8", "msg": "①", "sec": "§6.2-6 그림 4", "status": "기술통계",
         "claim": "평탄부에서는 창이 상당히 생기지만, 생긴 창의 tick 에 쏘지 못하는 손실이 크다",
         "nums": [f"결정적: 창이 생긴 판 {det['win_eps_range'][0]}–{det['win_eps_range'][1]} (중앙값 {det['win_eps_med']}), "
                  f"창 뒤 발사 {det['fired_after_win_med']}, net 포획 {det['net_in_dec_med']} ({det['slots']} slot 중앙값)",
                  f"확률적: 창이 생긴 판 {sto['win_eps_range'][0]}–{sto['win_eps_range'][1]} (중앙값 {sto['win_eps_med']}), "
                  f"창 뒤 발사 {sto['fired_after_win_med']}, net 포획 {sto['net_in_dec_med']}",
                  f"창 기록 밖 포획: 결정적 {det['captures_outside_window']}, 확률적 {sto['captures_outside_window']} (창은 장전·16 m 이내만 셈)"],
         "caveats": ["사후 집계 — 판정 아님", "같은 설계의 판정 흉내 발사 머리 (ρ 1.92 와 동일) → 실제 긴장",
                     "원인 단정 금지 — 공격자 기동 개입 실험 판독 전"],
         "src": [f"{A}/e7b", f"{A}/e7b2"]},
        {"id": "L9", "msg": "②", "sec": "§6.3 그림 5", "status": "확정",
         "claim": "다른 정책용 착취자로 재면 천장이 2.6–3.8 배 부풀려진다 (세 실험에서 반복)",
         "nums": [f"{blk}: " + " · ".join(f"{k} {_g(mat)} / {_g(mis)}" for k, (mat, mis) in rows.items())
                  for blk, rows in ca["matrix"].items()] +
                 ["배율 (다른 ÷ 같은): " + ", ".join(f"{x:.2f}" for x in ca["ratios"])],
         "caveats": ["규칙마다 천장 정의가 달라 행렬끼리 숫자 비교 금지 — 행렬 안의 비율만", "이 모델·이 학습 예산 조건부"],
         "src": [f"{A}/e7b/readout.json", f"{A}/e7b2/readout.json", f"{A}/e7c/readout.json"]},
    ]
    links = [("L1", "L2", "창이 있으려면 → 쓸 만한 길이까지"), ("L2", "L3", "이상 조건에서 → 오차가 있으면"),
             ("L2", "L4", "경계를 → 위협 등급별로 읽으면"), ("L2", "L5", "현행 ρ 는 1.24–2.81 사이 → 학습 방어는"),
             ("L5", "L7", "사양을 올리면 → 천장은"), ("L6", "L7", "창은 해석대로 열리지만 → 천장은 따로"),
             ("L7", "L8", "평탄부는 어디서 → 손실 분해"), ("L7", "L9", "이 천장 숫자들은 → 정합 감사로 잰 것")]
    return {"messages": MESSAGES, "cut_line": CUT_LINE, "status": STATUS, "nodes": nodes, "links": links,
            "analytic": an, "queue": queue(root), "gaps": gaps(root), "figures": figures(root)}


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    m = chain(root)
    for n in m["nodes"]:
        print(n["id"], n["status"], n["claim"])
        for x in n["nums"]:
            print("   ", x)
    print("queue", m["queue"])
    print("gaps", len(m["gaps"]), "figures", m["figures"])
