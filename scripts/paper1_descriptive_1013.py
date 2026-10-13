"""기술 통계 (증거 1-2 · 1-3 · 1-4, 판정 아님, 2026-10-13) — 기존 정본 평가 기록만 읽는다. 새 계약·재판정 없음.

1-2 E1 의 교차 감사 행렬 (세 번째 방어 세트): slot 마다 (방어, 착취자) 4 칸의 defended /240
1-3 E1 r1.92 (χ 0.52) 판 단위 6분류 (viz/paper1_logic._cat, 창 = 장전·16 m·첫 발사 전 기록)
1-4 E1b 판별 창 길이 (n_rob tick) 와 net 포획의 관계
    .venv/Scripts/python scripts/paper1_descriptive_1013.py  → artifacts/paper1/descriptive/desc_1013.json
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "viz"))
sys.path.insert(0, str(ROOT / "scripts"))
import paper1_logic as L  # noqa: E402
import fs1_e1_manifest as M1  # noqa: E402
import fs1_e1b_manifest as M2  # noqa: E402

E1, E1B = ROOT / "artifacts/fs1/e1", ROOT / "artifacts/fs1/e1b"
NET = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")


def defended(d):
    rows = json.loads((d / "summary.json").read_text(encoding="utf-8"))["rows"]
    return {(r["defender"][8:], r["group"]): r["defended"] for r in rows}


def cross_audit_e1():
    out = {}
    for p in M1.LADDER + M1.PAIR + M1.E6_ARMS:
        for s in M1.SEEDS:
            a, b = defended(E1 / p["name"] / f"s{s}" / "eval_judge"), defended(E1 / p["name"] / f"s{s}" / "eval_judge_sto")
            out[f"{p['name']}/s{s}"] = {"det|det": a[("det", "ex_judge")], "sto|det": a[("sto", "ex_judge")],
                                        "det|sto": b[("det", "ex_judge_sto")], "sto|sto": b[("sto", "ex_judge_sto")]}
    def summ(keys):
        sl = [out[k] for k in keys]
        med = {c: float(np.median([x[c] for x in sl])) for c in ("det|det", "sto|det", "det|sto", "sto|sto")}
        per = [x["det|sto"] / x["det|det"] for x in sl if x["det|det"] > 0] + \
              [x["sto|det"] / x["sto|sto"] for x in sl if x["sto|sto"] > 0]
        return {"n_slots": len(sl), "medians": med,
                "ratio_det_line (median det|sto / median det|det)": med["det|sto"] / med["det|det"],
                "ratio_sto_line (median sto|det / median sto|sto)": med["sto|det"] / med["sto|sto"],
                "per_slot_ratio_range": [float(min(per)), float(max(per))],
                "per_slot_ratio_below_1": int(sum(r < 1 for r in per)), "per_slot_ratio_n": len(per)}
    ks = list(out)
    return {"all_55": summ(ks), "excluding_rho1.92 (floor)": summ([k for k in ks if not k.startswith("r1.92/")]),
            "slots": out}


def six_way_r192():
    rows = Counter()
    for s in M1.SEEDS:
        for x in (E1 / "r1.92" / f"s{s}" / "eval_judge" / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(x)
            if e["defender"] == "learned_det" and e["group"] == "ex_judge":
                rows[L._cat(e)] += 1
    return {c: rows[c] for c in L.CATS} | {"n": sum(rows.values())}


def window_vs_capture_e1b():
    out = {}
    for p in M2.POINTS:
        bins = Counter(); cap = Counter()
        for s in M2.SEEDS:
            for x in (E1B / p["name"] / f"s{s}" / "eval_judge" / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
                e = json.loads(x)
                if e["defender"] != "learned_det" or e["group"] != "ex_judge":
                    continue
                k = min(int(e.get("n_rob", 0)), 4)
                bins[k] += 1; cap[k] += e["label"] in NET
        out[f"{p['name']} (chi {1 / p['rho']:.3f})"] = {f"n_rob={'>=4' if k == 4 else k}": [bins[k], cap[k]] for k in range(5)}
    return out


if __name__ == "__main__":
    res = {"status": "descriptive, not a judgment; numbers partly seen earlier (E1 readout tabulation 10-12)",
           "1-2 cross_audit_E1": cross_audit_e1(), "1-3 six_way_r1.92": six_way_r192(),
           "1-4 window_vs_capture_E1b [episodes, net captures]": window_vs_capture_e1b()}
    (ROOT / "artifacts/paper1/descriptive/desc_1013.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    r = res["1-2 cross_audit_E1"]
    for k in ("all_55", "excluding_rho1.92 (floor)"):
        print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in r[k].items() if a != "medians"}, r[k]["medians"])
    print("1-3", res["1-3 six_way_r1.92"])
    for k, v in res["1-4 window_vs_capture_E1b [episodes, net captures]"].items():
        print("1-4", k, v)
