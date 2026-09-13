"""R2b velocity-state decomposition — docs/99 사전등록의 기계 이행.

    python -m shepherd.scripts.r2b_velocity_decomp

**재실행 0** — steer probe 가 저장한 $t_F^C$ 스냅샷만 읽는다.

`98-B` 로 확정된 것은 **"position translation alone is insufficient"** 하나뿐이다.
속도·heading 이 원인이라는 것은 **후보**이며, 본 분해가 어느 성분이 층을 가르는지 본다.

지표 (docs/99 §2) — reference 속도 $v^C$, branch 속도 $v^W$:

    ds     = |v^W| - |v^C|                       (속력 변화, 부호 유지)
    dtheta = arccos( v^W·v^C / (|v^W||v^C|) )    (heading 변화)
    dv_par = (v^W - v^C)·v̂^C
    dv_perp= |(v^W - v^C) - dv_par·v̂^C|

층화 (docs/99 §3): 각 rho 에서 **AUTH-LOST vs AUTH-RETAINED**. 주력 셀 = **rho 0.75**
(같은 개입에서 15 잃고 31 유지 → timing 고정한 채 무엇이 갈렸는지 보인다).

**어휘 (docs/99 §5)**: 본 분해는 **연관**이다. 같은 개입이 네 성분을 동시에 움직이므로
어느 성분도 "원인" 이라 쓰지 않는다. 도달집합 모양은 본 문서가 재지 않는다.

descriptive association analysis — CI·가설검정 없음. torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PROBE = ROOT / "artifacts/r2b/steer_probe"
OUT = ROOT / "artifacts/r2b/velocity_decomp.json"
B0V3_HASH = "5e7b5b486b9d8a4a"
RHOS = (0.0, 0.25, 0.5, 0.75)
PRIMARY_RHO = 0.75
COMPONENTS = ("abs_dv_par", "dv_perp", "dtheta", "abs_ds")
DEGEN = 1e-9
SELFCHECK_TOL = 1e-9
RATIO_FLOOR = 1.5          # docs/99 §4 — 근거 없는 제 판단값. 근처면 확정 금지.


def load():
    recs = []
    for f in sorted(PROBE.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["b0_v3_hash"] == B0V3_HASH
        recs += d["records"]
    return [r for r in recs if r["ref_parity_ok"] and r["dep"]["multi_dependent"]]


def decompose(delta):
    """docs/99 §2. 자기검증: dv_par^2 + dv_perp^2 == dv_norm^2."""
    vc = np.asarray(delta["ref"]["v_att"], float)
    vw = np.asarray(delta["branch"]["v_att"], float)
    nc, nw = float(np.linalg.norm(vc)), float(np.linalg.norm(vw))
    dv = vw - vc
    if nc < DEGEN:
        return None, "degenerate |v^C|"
    hat = vc / nc
    par = float(dv @ hat)
    perp = float(np.linalg.norm(dv - par * hat))
    if abs(par * par + perp * perp - delta["dv_norm"] ** 2) > SELFCHECK_TOL:
        return None, "self-check: par^2+perp^2 != dv_norm^2"
    th = (None if nw < DEGEN else
          float(np.arccos(np.clip(float(vw @ vc) / (nw * nc), -1.0, 1.0))))
    return {"ds": nw - nc, "abs_ds": abs(nw - nc), "dtheta": th,
            "dv_par": par, "abs_dv_par": abs(par), "dv_perp": perp,
            "dp_norm": delta["dp_norm"], "dv_norm": delta["dv_norm"]}, None


def _med(v):
    v = [x for x in v if x is not None]
    return float(np.median(v)) if v else None


def strata(recs, rho):
    lost, ret, skipped, missing = [], [], [], 0
    for r in recs:
        b = next(x for x in r["branches"]
                 if abs(x["rho"] - rho) < 1e-9 and x["limiter"] is None)
        if not b["reached_ref_fire"]:
            missing += 1
            continue
        d, why = decompose(b["delta_at_ref_fire"])
        if d is None:
            skipped.append((r["s"], why))
            continue
        (lost if b["delta_at_ref_fire"]["d_v_worst"] < 0 else ret).append(d)
    return lost, ret, skipped, missing


NULL_EFFECT = 1e-3          # dp < 1 mm = 개입이 표적에 사실상 아무 일도 안 했다


def summarize(lost, ret):
    keys = COMPONENTS + ("dp_norm", "ds", "dv_par", "dv_norm")
    out = {"n_lost": len(lost), "n_retained": len(ret), "median": {}, "ratio": {},
           # [실행 후 추가 · 진단 전용] 분기 판정 규칙은 건드리지 않는다.
           # ratio 는 median 비이므로 한 층이 통째로 "아무 일도 안 일어난" 판이면
           # 분모가 0 에 붙어 네 성분이 동시에 폭발한다 -> 비교가 무의미해진다.
           "frac_null_effect": {
               "lost": (float(np.mean([d["dp_norm"] < NULL_EFFECT for d in lost]))
                        if lost else None),
               "retained": (float(np.mean([d["dp_norm"] < NULL_EFFECT for d in ret]))
                            if ret else None)}}
    for k in keys:
        ml, mr = _med([d[k] for d in lost]), _med([d[k] for d in ret])
        out["median"][k] = {"lost": ml, "retained": mr}
        out["ratio"][k] = (None if not ml or not mr or abs(mr) < 1e-12
                           else float(abs(ml) / abs(mr)))
    return out


def verdict(s):
    """docs/99 §4 — 네 성분 중 최대 median 비가 분기를 정한다. 최대 < 1.5 면 99-N.

    **분기 키는 봉인 규칙 그대로 산출한다.** 아래 degeneracy 경고는 결과를 본 뒤
    추가한 **주석**이며 어떤 분기가 나오는지를 바꾸지 않는다 (docs/99 §4 불변).
    """
    rs = {k: s["ratio"][k] for k in COMPONENTS if s["ratio"][k] is not None}
    if not rs:
        return "99-N", "성분 비를 계산할 수 없다 (층이 비었거나 median 0)."
    top = max(rs, key=rs.get)
    r, dp = rs[top], s["ratio"].get("dp_norm")
    near = abs(r - RATIO_FLOOR) < 0.25
    fn = s.get("frac_null_effect", {}).get("retained")
    degen = fn is not None and fn > 0.5
    if r < RATIO_FLOOR:
        return "99-N", (
            f"No component separates the strata (max median ratio {r:.2f} on {top}, "
            f"below the declared floor {RATIO_FLOOR}). Attacker velocity alone does not "
            "distinguish AUTH-LOST from AUTH-RETAINED -- capturer-relative geometry / "
            "pointing state is the next place to look.")
    key = {"abs_dv_par": "99-P", "abs_ds": "99-P",
           "dtheta": "99-D", "dv_perp": "99-D"}[top]
    lbl = "speed / timing steering" if key == "99-P" else "directional steering"
    note = ""
    if near:
        note = (f" CAUTION: the ratio sits within 0.25 of the declared floor "
                f"{RATIO_FLOOR}, so per docs/99 §4 this branch is NOT declared final.")
    if degen:
        note += (f" DEGENERATE CELL: {fn:.0%} of the RETAINED stratum has "
                 "|dp| < 1 mm, i.e. the intervention did essentially nothing there. "
                 "The median ratio then divides by ~0 and every component inflates "
                 "together, so this cell cannot say WHICH component separates the "
                 "strata. Read a cell where both strata actually moved.")
    if dp is not None and dp >= r:
        note += (f" CAUTION: displacement separates the strata at least as strongly "
                 f"(dp ratio {dp:.2f} >= {r:.2f}), which weakens any velocity reading.")
    return key, (f"AUTH-LOST records are distinguished primarily by {top} "
                 f"(median ratio {r:.2f} vs retained) -> {lbl}.{note}")


def main():
    recs = load()
    per = {}
    for rho in RHOS:
        lost, ret, skipped, missing = strata(recs, rho)
        per[str(rho)] = {**summarize(lost, ret), "skipped": skipped,
                         "n_not_reached_ref_fire": missing}
    vkey, sentence = verdict(per[str(PRIMARY_RHO)])
    secondary = {k: verdict(per[str(k)]) for k in (0.25, 0.5)}
    out = {"doc": "docs/99", "b0_v3_hash": B0V3_HASH,
           "stratum": "multi-dependent", "n_records": len(recs),
           "primary_rho": PRIMARY_RHO, "ratio_floor": RATIO_FLOOR,
           "by_rho": per, "verdict": {"branch": vkey, "sentence": sentence},
           "secondary_rho_verdicts": {str(k): {"branch": v[0], "sentence": v[1]}
                                      for k, v in secondary.items()},
           "vocabulary": ("association only -- the same intervention moves all four "
                          "components at once, so no component is called the cause; "
                          "reachable-set shape is not measured here")}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"multi-dependent {len(recs)} records · primary rho {PRIMARY_RHO}\n")
    for rho in RHOS:
        s = per[str(rho)]
        print(f"rho {rho:<5g} LOST {s['n_lost']:>2} / RET {s['n_retained']:>2} "
              f"(not reached {s['n_not_reached_ref_fire']}, skipped {len(s['skipped'])})")
        for k in COMPONENTS + ("dp_norm",):
            m, rt = s["median"][k], s["ratio"][k]
            if m["lost"] is None or m["retained"] is None:
                continue
            tag = "  <-- control" if k == "dp_norm" else ""
            print(f"    {k:<11} lost {m['lost']:>8.4f}  ret {m['retained']:>8.4f}  "
                  f"ratio {rt:>6.2f}{tag}")
    print(f"\n[PRIMARY rho={PRIMARY_RHO}] [{vkey}] {sentence}")
    for k, (bk, sn) in secondary.items():
        print(f"\n[secondary rho={k}] [{bk}] {sn}")


if __name__ == "__main__":
    main()
