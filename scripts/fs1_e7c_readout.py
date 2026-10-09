"""E7-c 판독 (manifest `fs1_e7_manifest.build_e7c` v1.3): docs/130 §3·§7·§9 — det·sto 두 계열.

    python scripts/fs1_e7c_readout.py --root artifacts/fs1/e7c
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_manifest import C_CONDS, load_e7c  # noqa: E402
from fs1_e7b_readout import _last_steps  # noqa: E402

SEEDS, N, THR, MARGIN, FLOOR = (0, 1, 2), 240, 29, 24, 0.01
TRAIN_STEPS, EX_STEPS = 1.1e8, 1e7
LINES = {"det": ("learned_det", "ex_judge"), "sto": ("learned_sto", "ex_judge_sto")}


def _slot(root, c, s, m):
    d = root / c["name"] / f"s{s}"
    sm = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
    meta = sm["meta"]
    if meta.get("manifest") != m["manifest_hash"]:
        raise ValueError("manifest")
    want = (c["tau_scale"], c["theta_scale"], c["limiters"] == "post_shot" and "post_shot" or "a",
            c["limiters"] == "inert")
    if (meta.get("tau_scale"), meta.get("theta_scale"), meta.get("limiter_roe"),
            meta.get("limiter_inert")) != want:
        raise ValueError("condition flags")
    if _last_steps(d / "log.jsonl") < TRAIN_STEPS:
        raise ValueError("train budget")
    for ex in ("judge_exploiter", "judge_exploiter_sto"):
        if _last_steps(d / ex / "log.jsonl") < EX_STEPS:
            raise ValueError(f"{ex} budget")
    rows = {(r["defender"], r["group"]): r for r in sm["rows"]}
    out = {}
    for line, key in LINES.items():
        r = rows[key]
        if r["n"] != N:
            raise ValueError(f"completion {line}")
        kp = r.get("kill_phase", {})
        if c["limiters"] == "post_shot" and kp.get("pre_shot", 0) > 0:
            raise ValueError(f"post_shot violation {line}: pre_shot kills {kp['pre_shot']}")
        out[line] = {"d_shot": r["d_shot"], "net": r["net"], "defended": r["defended"],
                     "k_sw": kp.get("shot_window", 0), "fallback": kp.get("fallback", 0),
                     "coop": r.get("coop")}
    out["cross"] = {f"{d}_vs_{g}": rows.get((d, g), {}).get("d_shot")
                    for d in ("learned_det", "learned_sto") for g in ("ex_judge", "ex_judge_sto")}
    return out


def _maj(flags):
    return sum(bool(f) for f in flags) >= 2


def judge_line(S, line):
    """S[cond][seed][line] → §3 게이트 + §7 해석표 (P1)."""
    g = lambda c, s: S[c][s][line]["d_shot"]
    full = all(len(S[c]) == 3 for c in S)
    res = {}
    if not full:
        return {"status": "INCOMPLETE"}
    p2_open = _maj(g("P2_inert", s) >= THR for s in SEEDS)
    p1_closed = _maj(g("P1_inert", s) < THR for s in SEEDS)
    res["P_rho2L"] = "SUPPORTED" if (p2_open and p1_closed) else "NOT_SUPPORTED"
    res["P_rho2L_detail"] = {"P2_inert": [g("P2_inert", s) for s in SEEDS],
                             "P1_inert": [g("P1_inert", s) for s in SEEDS]}
    delta = [g("P1_armed", s) - g("P1_inert", s) for s in SEEDS]
    armed_open = _maj(g("P1_armed", s) >= THR for s in SEEDS)
    armed_closed = _maj(g("P1_armed", s) < THR for s in SEEDS)
    res["P_2d"] = ("COOP_PUSHES_BOUNDARY" if armed_open and _maj(d >= MARGIN for d in delta)
                   else "COOP_NULL_BELOW" if armed_closed else "NOT_SUPPORTED")
    nw = sum((S["P1_armed"][s][line]["coop"] or {}).get("n_win", 0) for s in SEEDS)
    C = (sum((S["P1_armed"][s][line]["coop"] or {}).get("n_C", 0) for s in SEEDS) / nw) if nw else 0.0
    ksw = [S["P1_armed"][s][line]["k_sw"] for s in SEEDS]

    def row(d, k):
        if d >= MARGIN:
            return "A" if (C >= FLOOR or k >= d / 2) else "B"
        if d <= -MARGIN:
            return "D"
        return "C"
    rows = [row(d, k) for d, k in zip(delta, ksw)]
    top = max(set(rows), key=rows.count)
    res["interpretation"] = {"delta": delta, "C_pooled": round(C, 5), "K_sw": ksw,
                             "rows_per_seed": rows,
                             "row": top if rows.count(top) >= 2 else "MIXED"}
    res["P2_armed_minus_inert"] = [g("P2_armed", s) - g("P2_inert", s) for s in SEEDS]
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="artifacts/fs1/e7c")
    a = ap.parse_args()
    root, m = pathlib.Path(a.root), load_e7c()
    S, invalid = {}, []
    for c in C_CONDS:
        S[c["name"]] = {}
        for s in SEEDS:
            try:
                S[c["name"]][s] = _slot(root, c, s, m)
            except Exception as e:  # noqa: BLE001
                invalid.append(f"{c['name']}/s{s}: {e}")
    out = {"manifest_hash": m["manifest_hash"], "invalid": invalid,
           "lines": {line: judge_line(S, line) for line in LINES},
           "slots": {c: {str(s): v for s, v in S[c].items()} for c in S}}
    (root / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("lines", "invalid")}, indent=2))


if __name__ == "__main__":
    main()
