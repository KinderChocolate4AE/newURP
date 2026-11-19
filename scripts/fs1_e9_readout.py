"""E9 = 비이상성 접힘 판독 (docs/144 v1.1, manifest fs1_e9_manifest). 판정 규칙은 manifest 의 verdict 만 쓴다.

    python scripts/fs1_e9_readout.py --dir artifacts/fs1/e9
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fs1_e4_manifest as E4  # noqa: E402
import fs1_e9_manifest as M  # noqa: E402

SLOTS = ("ex_kfirst50", "ex_fin12_fb", "ex_mix5050", "ex_kfirst_rand")


def wiring(npz: dict) -> dict:
    """v1.1: 같은 실행 안에서 복제 셀 wiring_dup_base 의 rb == 기준점 t1.0_h1.0_cv 의 rb (slot 별
    비트 일치). 하나라도 다르면 실행 무효 (결과 아님)."""
    return {s: bool(np.array_equal(npz[f"{s}.wiring_dup_base.rb"], npz[f"{s}.t1.0_h1.0_cv.rb"]))
            for s in SLOTS}


def monotone(win: dict) -> dict:
    """보고 전용: 기준점마다 L·δ 증가에 따른 창의 비증가 여부."""
    out = {}
    for b in M.BASES:
        out[b] = {"L": [win[b]] + [win[f"{b}_L{k}"] for k in M.LAGS],
                  "d": [win[b]] + [win[f"{b}_d{d}"] for d in M.DELTAS]}
        out[b] = {k: {"windows": v, "non_increasing": bool(all(x >= y for x, y in zip(v, v[1:])))}
                  for k, v in out[b].items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/fs1/e9")
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    h = M.load()["manifest_hash"]
    probe = json.loads((d / "probe.json").read_text(encoding="utf-8"))
    k = probe["consts"]
    assert abs(k["tau0"] - E4.TAU0) < 1e-12 and abs(k["theta0"] - E4.TH0) < 1e-12
    assert abs(k["range_max"] - E4.RMAX) < 1e-9 and abs(k["a_att"] - E4.A0) < 1e-6 and abs(k["dt"] - E4.DT) < 1e-12
    npz = dict(np.load(d / "rows.npz"))
    wire = wiring(npz)
    win = probe["variant_window_med"]
    out = {"manifest_hash": h, "wiring_dup_bit_exact": wire, "void": not all(wire.values())}
    if not out["void"]:
        out["P-E9"] = M.verdict(win)
        out["report_monotone"] = monotone(win)
        out["report_N_pred"] = {c["name"]: round(max(0.0, 1 - E4.rho0({**c, "hs": (E4.TH0 - c["delta"]) / E4.TH0})
                                                    * M.chi_eff(c)) * E4.n_inf(c), 3)
                                for c in M.GRID if c["family"] in M.FAMILIES}
    (d / "readout.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("wiring:", wire, "| VOID" if out["void"] else "")
    for fam, v in out.get("P-E9", {}).items():
        print(fam, v["verdict"], "informative", v["n_informative"], "failing", v["failing"])
        for n, c in v["cells"].items():
            print(f"  {n:22s} chi_eff {c['chi_eff']:.3f} win {c['window']:4.1f} ref {c['window_ref']:4.1f} "
                  f"gap {c['gap']:+.1f} base {c['window_base']:4.1f}")


if __name__ == "__main__":
    main()
