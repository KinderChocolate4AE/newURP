"""paper-R2a Stage 0 — 동결 곡선 2,700판의 (chi, eta) 재집계 → 행별 chi50(eta) + envelope.

    python -m shepherd.scripts.r2a_stage0 [--out artifacts/r2a/stage0_envelope.json]

지위: **exploratory / design data** (브리프 §5 Stage 0). 새 표본이 아니라 재집계다 —
`curve_hold_reactive.json` 의 라벨을 건드리지 않는다. 산출물 hash 가 lattice 봉인에
들어간다. 결과는 tau_B 게이트·envelope·margin 역산의 입력이지 증거가 아니다.

행별 추정 (§6.4): primary = 행별 binomial isotonic (PAV, p 는 chi 에 비증가) /
secondary = logistic fit (기울기 → delta_chi50 역산, §6.1) / transparency = raw bin.
교차 없음 = censored, raw-bin 다중 교차 = 단조성 flag. 경계 외삽 금지.
torch-free (numpy + scipy.optimize).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np
from scipy.optimize import minimize

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.r2a_lattice import (ETA_GRID, ETA_STEP, W_BOUNDARY,   # noqa: E402
                                          chi_eta)

SRC = "results/curve_hold_reactive.json"
DIAG_DP = 0.10          # logistic 기울기 역산은 **진단 전용** (r4-C: delta_chi 정의에 쓰지 않는다)
N_BOOT = 500
RAW_BINS = 8


def load(root: pathlib.Path) -> np.ndarray:
    """(chi, eta, capture) 행렬. cp949 산출물이라 숫자만 읽는다."""
    d = json.loads((root / SRC).read_text(encoding="utf-8", errors="replace"))
    out = []
    for r in d["records"]:
        c, e = chi_eta(r["a_att"], r["att_speed"], r["tau"], r["net_radius"])
        out.append((c, e, 1.0 if r["label"] == "NET_CAPTURE" else 0.0))
    return np.asarray(out)


def pav_decreasing(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators: x 오름차순 정렬된 y 에 비증가 단조 적합."""
    vals, wts, cnt = [], [], []
    for v in y:
        vals.append(float(v)); wts.append(1.0); cnt.append(1)
        while len(vals) > 1 and vals[-2] < vals[-1]:       # 위반 = 증가
            v2 = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / (wts[-2] + wts[-1])
            wts[-2] += wts[-1]; cnt[-2] += cnt[-1]
            vals.pop(); wts.pop(); cnt.pop(); vals[-1] = v2
    return np.repeat(vals, cnt)


def cross50(x: np.ndarray, p: np.ndarray) -> float:
    """비증가 p 가 0.5 를 아래로 가르는 chi (선형보간). 없으면 NaN (censored)."""
    if p[0] < 0.5 or p[-1] >= 0.5:
        return float("nan")
    i = int(np.argmax(p < 0.5))                           # 첫 0.5 미만
    x0, x1, p0, p1 = x[i - 1], x[i], p[i - 1], p[i]
    return float(x0 + (x1 - x0) * (p0 - 0.5) / (p0 - p1)) if p0 != p1 else float(x1)


def chi50_isotonic(chi: np.ndarray, y: np.ndarray) -> float:
    o = np.argsort(chi)
    return cross50(chi[o], pav_decreasing(chi[o], y[o]))


def logistic(chi: np.ndarray, y: np.ndarray) -> dict:
    """p = sigmoid(b0 + b1·chi). chi50 = −b0/b1, |dp/dchi| at chi50 = |b1|/4."""
    def nll(b):
        z = b[0] + b[1] * chi
        return float(np.sum(np.logaddexp(0, z) - y * z))
    b = minimize(nll, x0=[2.0, -3.0], method="Nelder-Mead").x
    slope = abs(b[1]) / 4.0
    c50 = -b[0] / b[1] if b[1] != 0 else float("nan")
    return {"b0": float(b[0]), "b1": float(b[1]), "chi50": float(c50),
            "slope_at_chi50": float(slope),
            "diag_dchi_per_0p1": float(DIAG_DP / slope) if slope > 0 else float("nan")}


def raw_bins(chi: np.ndarray, y: np.ndarray, k: int = RAW_BINS) -> list[dict]:
    edges = np.quantile(chi, np.linspace(0, 1, k + 1))
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (chi >= lo) & (chi <= hi)
        out.append({"lo": float(lo), "hi": float(hi), "n": int(m.sum()),
                    "p": float(y[m].mean()) if m.any() else float("nan")})
    return out


def row_summary(chi: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> dict:
    c50 = chi50_isotonic(chi, y)
    boots = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(chi), len(chi))
        boots.append(chi50_isotonic(chi[i], y[i]))
    boots = np.asarray(boots)
    ok = boots[~np.isnan(boots)]
    ci = [float(np.quantile(ok, 0.025)), float(np.quantile(ok, 0.975))] if len(ok) > 20 else None
    rb = raw_bins(chi, y)
    ps = [b["p"] for b in rb]
    n_cross = sum(1 for a, b in zip(ps[:-1], ps[1:]) if (a >= 0.5) != (b >= 0.5))
    lg = logistic(chi, y)
    return {"n": int(len(chi)), "p_mean": float(y.mean()),
            "chi_range": [float(chi.min()), float(chi.max())],
            "chi50_isotonic": c50, "censored": bool(np.isnan(c50)),
            "chi50_boot_ci95": ci, "boot_censored_frac": float(np.isnan(boots).mean()),
            "logistic": lg, "raw_bins": rb, "raw_crossings": n_cross,
            "monotonicity_flag": n_cross > 1}


def run(root: pathlib.Path, seed: int = 0) -> dict:
    data = load(root)
    rng = np.random.default_rng(seed)
    rows, envelope = {}, {}
    # lattice 행 + 정보용 바깥 행 (격자 밖 = 봉인 대상 아님, 단조성 관찰용)
    extra = [round(ETA_GRID[0] - ETA_STEP, 3), round(ETA_GRID[-1] + ETA_STEP, 3),
             round(ETA_GRID[-1] + 2 * ETA_STEP, 3), round(ETA_GRID[-1] + 3 * ETA_STEP, 3)]
    for eta in sorted(ETA_GRID + extra):
        m = (data[:, 1] >= eta - ETA_STEP / 2) & (data[:, 1] < eta + ETA_STEP / 2)
        if m.sum() < 30:
            continue
        s = row_summary(data[m, 0], data[m, 2], rng)
        s["on_lattice"] = eta in ETA_GRID
        rows[str(eta)] = s
        if s["on_lattice"] and not s["censored"]:
            ci = s["chi50_boot_ci95"]
            s["ci_within_W"] = bool(ci and (ci[1] - ci[0]) / 2 <= W_BOUNDARY)
            envelope[str(eta)] = [s["chi50_isotonic"] - W_BOUNDARY, s["chi50_isotonic"] + W_BOUNDARY]
    pooled = chi50_isotonic(data[:, 0], data[:, 2])
    out = {"status": "exploratory/design — Stage 0 re-aggregation, not evidence",
           "source": SRC, "n": int(len(data)),
           # D-2 (감사 r2): 세계 선언을 데이터의 실제 세계로 정합. 구 hash lineage 유지.
           "world": {"threat": "A2-reactive", "jink_amp": 0.6, "jink_freq_hz": 1.5,
                     "route_gain": 0.5, "sense_range_m": 30.0,
                     "lineage": "results/curve_hold_reactive.manifest.json (commit 43acc39, "
                                "run commit edf34d9)",
                     "verification": "artifacts/r2a/provenance_route_sense.json"},
           "supersedes": {"stage0": ["3878260e937f9b05", "4c26cf1a2a4d9ab8"],
                          "reason": "D-2 world correction A1->A2; then A-prime q_dec "
                                    "reclassification (governing conditioning coordinate)"},
           "q_dec": {"value": 1.0 / 6.0, "definition": "T_decision/tau (== dt/tau here)",
                     "status": "governing conditioning coordinate — the frozen curve and "
                               "every R2a implementation share q_dec = 1/6"},
           "eta_step": ETA_STEP, "W_boundary": W_BOUNDARY, "seed": seed, "n_boot": N_BOOT,
           "pooled_chi50_isotonic": pooled,
           "rows": rows, "envelope": envelope,
           "envelope_rule": "B(eta) = chi50_isotonic ± W_boundary (fixed boundary half-width, "
                            "independent of map grid); lattice rows only, censored excluded. "
                            "Logistic slope is diagnostic only (r4-C)."}
    out["hash"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:16]
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/r2a/stage0_envelope.json")
    a = ap.parse_args(argv)
    res = run(ROOT)
    p = ROOT / a.out; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"stage0 hash {res['hash']}  n {res['n']}  pooled chi50 {res['pooled_chi50_isotonic']:.3f}")
    print(f"{'eta':>6} {'n':>4} {'p':>5} {'chi50':>6} {'CI95':>15} {'logit50':>7} {'diag':>6}  flag")
    for e, r in res["rows"].items():
        ci = r["chi50_boot_ci95"]
        print(f"{e:>6} {r['n']:>4} {r['p_mean']:.2f} {r['chi50_isotonic']:>6.3f} "
              f"{('[%.3f,%.3f]' % tuple(ci)) if ci else '-':>15} {r['logistic']['chi50']:>7.3f} "
              f"{r['logistic']['diag_dchi_per_0p1']:>6.3f}  "
              f"{'CENS' if r['censored'] else ''}{'MONO' if r['monotonicity_flag'] else ''}"
              f"{'' if r['on_lattice'] else ' (off-lattice)'}"
              f"{'' if r.get('ci_within_W', True) else ' CI>W'}")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
