"""SS8-2 close-out (docs/09 (ccc)): freeze the witness set + coverage matrix.

Produces results/a3_robust_bank_v2.json -- the v1 witness bank with the
x12v16 row REPLACED by the (bbb)-accepted v16_refine transplant candidate
(val 1.00; arrival screen k1 8/8 + k2 8/8). v1 is preserved untouched
(artifact-preservation rule, docs/18 SS8-5 analog). The frozen coverage
matrix is embedded in the v2 bank meta so it travels with the artifact;
the Phase 0-e commit restates it as pre-registration text.

Stats for the replaced row are RECOMPUTED from scratch on the probe's
validation unions (200..209) + sigma baselines (fresh rng(23)) -- no
carry-over from the refine run's numbers.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np

from shepherd.scripts.a3_robust_witness_probe import (
    ACCEPT_MIN, VAL_SEEDS, sigma_baselines, stats, union_for)
from shepherd.train.spawn_bank import load_t0

V1 = "results/a3_robust_bank.json"
REFINE = "results/a3d_v16_refine.json"
OUT = "results/a3_robust_bank_v2.json"

COVERAGE = {                      # frozen targets (docs/09 (ccc); 0-e restate)
    "v16": ["d1", "d2"],
    "v20": ["d1", "d2"],          # d2 = low-confidence (dev PFC .63);
                                  # miss -> rule-based cell exclusion only
    "v24": ["d2", "d3", "d4"],    # d1/v24 = structural C-exclusion (R==0)
}


def main():
    bank = json.loads(pathlib.Path(V1).read_text())
    ref = json.loads(pathlib.Path(REFINE).read_text())
    assert ref["verdict"] == "ACCEPT", "no accepted v16 candidate"
    ch = ref["chosen"]
    L = np.asarray(ch["limiters"], float)
    x, v = float(ch["x"]), float(ch["v"])

    uv = [union_for(x, v, s) for s in VAL_SEEDS]
    val_cl, val_cap, val_vmin = stats(uv, L)
    assert val_cl >= ACCEPT_MIN, f"recompute val {val_cl} < {ACCEPT_MIN}"
    sig = sigma_baselines(uv, L, np.random.default_rng(23))

    rows = [s for s in bank["states"]
            if not (s["x"] == x and s["v"] == v)]
    old = [s for s in bank["states"] if s["x"] == x and s["v"] == v]
    assert len(old) == 1, f"expected 1 old v16 row, got {len(old)}"
    row = dict(old[0])
    row.update({
        "candidate": "v16_refine_transplant",
        "search_clean_frac": None,
        "robust_clean_frac": round(float(val_cl), 3),
        "robust_capture_frac": round(float(val_cap), 3),
        "v_soft_min_val": round(float(val_vmin), 3),
        "capture_grade_found": True,
        "refined_best": {"limiters": L.tolist(),
                         "v_soft": float(val_vmin), "worst": 1.0,
                         "p_feas": 1e-3},
        "sigma_baselines": sig,
        "provenance": {"from": REFINE, "criteria": "docs/09 (aaa)",
                       "screen": "k1 8/8, k2 8/8, all 20/20 PFC / 0/20 zero",
                       "replaced_val": old[0]["robust_clean_frac"]},
    })
    bank["states"] = rows + [row]
    bank["witness_freeze"] = {
        "date": "2026-07-17", "log": "docs/09 (ccc)",
        "coverage_matrix": COVERAGE,
        "note": "targets only; admissibility verdicts come from the bank-v2 "
                "generator screen + independent validation (docs/18 SS6). "
                "v1 bank preserved at results/a3_robust_bank.json."}
    pathlib.Path(OUT).write_text(json.dumps(bank, indent=1))

    t0s = load_t0(OUT)                          # roundtrip check
    got = [t for t in t0s if float(t.v) == 16.0]
    assert len(got) == 1
    assert np.allclose(np.asarray(got[0].limiters, float), L)
    print(f"v16 row replaced: val={val_cl:.2f} cap={val_cap:.2f} "
          f"vmin={val_vmin:.3f} (old val={old[0]['robust_clean_frac']})")
    print(f"load_t0 roundtrip OK ({len(t0s)} witnesses) -> {OUT}")
    print("sigma_baselines:", {k: round(float(v_), 2)
                               for k, v_ in (sig or {}).items()})


if __name__ == "__main__":
    main()
