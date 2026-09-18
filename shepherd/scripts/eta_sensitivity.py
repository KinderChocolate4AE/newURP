"""eta(=att_speed·tau/rho) post-hoc 민감도: 동결 곡선의 속력 삼분위 재집계.

    python shepherd/scripts/eta_sensitivity.py [--out results/eta_sensitivity.json]

**새 표본이 아니라 재집계다.** 동결된 `curve_hold_reactive.json` /
`curve_intercept_reactive.json` 의 기록을 밴드별로 나눈 뒤 att_speed 삼분위로
다시 세는 것뿐이며, 라벨·결과확률은 건드리지 않는다.

지위: **post-hoc / diagnostic** (사전등록 아님, 결과를 본 뒤 세운 질문).
KSAS 본문은 이 값을 "사후 민감도 분석" 으로만 인용한다 — 기전 주장 금지.
동기: Gate 10 Tier2 r4 가 eta 를 GOVERNING 으로 판정했으므로, 헤드라인 곡선이
eta 에 대해 주변화돼 있는지 확인한다.

정본 재사용 (docs/85 R-012 교훈: viz 가 Wilson·격자를 재구현해 z 가 갈렸다):
  밴드 분할 = `curve_sweep.band_of`   ·   구간추정 = `shepherd.stats.wilson`
torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_config import m4_config                       # noqa: E402
from shepherd.scripts.curve_sweep import band_of               # noqa: E402
from shepherd.stats import wilson                              # noqa: E402

ARMS = {"hold": "results/curve_hold_reactive.json",
        "intercept": "results/curve_intercept_reactive.json"}


def _load(path: pathlib.Path) -> list[dict]:
    # 동결 아티팩트는 cp949 로 쓰인 것이 섞여 있다 (local-env quirk) -- 숫자만 읽는다.
    txt = path.read_text(encoding="utf-8", errors="replace")
    return json.loads(txt)["records"]


def terciles(rows: list[dict]) -> list[dict]:
    """att_speed 오름차순 삼분위. 나머지는 마지막 조각에 붙인다."""
    rows = sorted(rows, key=lambda r: r["att_speed"])
    t = len(rows) // 3
    cuts = [rows[:t], rows[t:2 * t], rows[2 * t:]]
    out = []
    for name, g in zip(("v_low", "v_mid", "v_high"), cuts):
        if not g:
            continue
        k = sum(1 for r in g if r["label"] == "NET_CAPTURE")
        lo, hi = wilson(k, len(g))
        out.append({
            "tercile": name, "n": len(g), "net_capture": k,
            "p": k / len(g), "wilson95": [lo, hi],
            "v_range": [g[0]["att_speed"], g[-1]["att_speed"]],
            # a_att 균형 = 독립 추출이 의도대로 작동했는지의 확인 (교락 배제)
            "a_att_mean": sum(r["a_att"] for r in g) / len(g),
        })
    return out


def run(root: pathlib.Path) -> dict:
    cfg = m4_config()
    tau = float(cfg["physics"]["tau_deploy"])
    rho = float(cfg["physics"]["net_radius"])
    out: dict = {"note": "post-hoc re-aggregation of frozen curves; no new samples",
                 "tau": tau, "rho": rho, "arms": {}}
    for arm, rel in ARMS.items():
        rows = _load(root / rel)
        bands: dict = {}
        for r in rows:
            bands.setdefault(band_of(r["a_att"], cfg), []).append(r)
        out["arms"][arm] = {
            "source": rel, "n": len(rows),
            "bands": {b: terciles(g) for b, g in sorted(bands.items())},
        }
    # eta 지지구간 (Gate10 r4 §4.2 의 support 보고 의무와 같은 정신)
    sp = [r["att_speed"] for r in _load(root / ARMS["hold"])]
    out["eta_support"] = {"v_min": min(sp), "v_max": max(sp),
                          "eta_min": min(sp) * tau / rho, "eta_max": max(sp) * tau / rho}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/eta_sensitivity.json")
    a = ap.parse_args()
    res = run(ROOT)
    (ROOT / a.out).write_text(json.dumps(res, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    for arm, d in res["arms"].items():
        print(f"[{arm}] n={d['n']}")
        for band, rows in d["bands"].items():
            for r in rows:
                lo, hi = r["wilson95"]
                print(f"  {band:15s} {r['tercile']:6s} v[{r['v_range'][0]:5.1f},"
                      f"{r['v_range'][1]:5.1f}] a_mean={r['a_att_mean']:6.2f}"
                      f"  {r['net_capture']:4d}/{r['n']:4d} = {r['p']:.3f}"
                      f"  CI95[{lo:.3f},{hi:.3f}]")
    e = res["eta_support"]
    print(f"eta support: [{e['eta_min']:.3f}, {e['eta_max']:.3f}]  -> {a.out}")


if __name__ == "__main__":
    main()
