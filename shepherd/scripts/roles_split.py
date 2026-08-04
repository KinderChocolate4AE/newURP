"""역할 분리 2x2 — 실행기 + 귀속 집계기 (docs/48).

왜 이걸 하는가 (docs/48 §1)
---------------------------
파일럿은 학습이 `hold` 보다 **나빴다**. 그런데 그 결과를 알고리즘의 결론으로
읽을 수가 없다. `hold` 는 무개입이 아니라 **해석적 발사 규칙**이 붙은 기준선이고
(`발사 off` 는 0.000), 그 사이에 쓸 기준선이 비어 있기 때문이다. 즉

    LL 이 SS 보다 나쁘다  ->  "협력 성형을 못 배웠다" 인가
                             "학습된 발사 타이밍이 해석적 규칙보다 나쁘다" 인가

둘이 구분되지 않는다. 역할을 하나씩 스크립트로 고정하면 구분된다.

    팔    limiter      finisher     읽는 것
    ---   ----------   ----------   --------------------------------------
    SS    hold         스크립트     기준선 (학습 없음. sweep_m4 --baseline 500)
    LS    학습         스크립트     발사를 고정했을 때 **편대 학습**의 단독 기여
    SL    hold         학습         편대를 고정했을 때 **발사 학습**의 단독 기여
    LL    학습         학습         결합 (= 파일럿 구성)

사용
----
    python -m shepherd.scripts.roles_split --dry-run
    python -m shepherd.scripts.roles_split --run --jobs 3
    python -m shepherd.scripts.roles_split --aggregate results/m4_roles

`SS` 는 여기서 돌리지 않는다 -- 학습이 없으므로 `results/hold_baseline.json`
(n=500) 을 그대로 쓴다. 같은 파일을 스윕도 쓰므로 두 실험의 기준선이 동일하다.

torch 를 직접 쓰지 않는다 (자식 프로세스가 쓴다).
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import subprocess
import sys
from typing import Dict, List, Optional

from shepherd.scripts.sweep_m4 import BAND, SHAPE
from shepherd.stats import wilson

__all__ = ["ARM_SPECS", "SEEDS", "W_KILL", "plan", "aggregate", "verdict_rules"]

# ── 선언: 축과 팔 (결과 보기 전에 고정) ─────────────────────────────────────
#   w_kill 은 스윕 축이 아니라 **고정**이다. 여기서 묻는 것은 "어느 역할이
#   격차를 만드는가" 이지 "어떤 보상 가중치가 좋은가" 가 아니다. 파일럿과 같은
#   0.5 로 둬서 파일럿(결함 위에서 돌긴 했지만)과 구성이 비교 가능하게 한다.
W_KILL = 0.5
SEEDS = (0, 1, 2, 3, 4)
ARM_SPECS = {                       # arm -> (limiter_policy, finisher_policy)
    "LL": ("learned", "learned"),
    "LS": ("learned", "scripted"),
    "SL": ("hold", "learned"),
}


def tag(arm: str, seed: int) -> str:
    return f"{arm}_s{seed}"


def plan(root: str, total_steps: Optional[int] = None,
         eval_eps: Optional[int] = None,
         final_eval_eps: Optional[int] = None,
         seeds=SEEDS, arms=tuple(ARM_SPECS)) -> List[tuple]:
    cmds = []
    for arm, s in itertools.product(arms, seeds):
        lim, fin = ARM_SPECS[arm]
        out = str(pathlib.Path(root) / tag(arm, s))
        c = [sys.executable, "-m", "shepherd.scripts.train_m4",
             "--w-kill", str(W_KILL), "--seed", str(s), "--output", out,
             "--limiter-policy", lim, "--finisher-policy", fin]
        if total_steps is not None:
            c += ["--total-env-steps", str(total_steps)]
        if eval_eps is not None:
            c += ["--eval-episodes", str(eval_eps)]
        if final_eval_eps is not None:
            c += ["--final-eval-episodes", str(final_eval_eps)]
        cmds.append((tag(arm, s), c))
    return cmds


# ── 선언: 판정 규칙 (docs/48 §4). 결과를 보기 전에 고정 ─────────────────────
def verdict_rules() -> dict:
    """판정식을 **데이터로** 낸다 -- 집계 출력에 그대로 실려 사후 변경이 드러난다."""
    return {
        "primary_metric": f"{SHAPE} 영역 무력화율 (docs/47 §4.3 그대로. 바꾸지 않는다)",
        "baseline": "results/hold_baseline.json 의 SHAPING_NEEDED Wilson 상한",
        "H_lim": "LS 의 Wilson 하한 > SS 의 Wilson 상한  -> 편대 학습의 단독 순이득",
        "H_fin": "SL 의 Wilson 하한 > SS 의 Wilson 상한  -> 발사 학습의 단독 순이득",
        "H_syn": "LL 의 Wilson 하한 > max(LS 상한, SL 상한) -> 결합 상승작용",
        "pooling": ("1차 판정은 시드 풀링 Wilson 으로 한다. 풀링은 시드 분산을 0 으로 "
                    "가정하므로, **시드 과반**이 개별로도 기저를 넘을 때만 '강한' "
                    "판정으로 적는다 (5시드 -> 3, 3시드 -> 2). 아니면 '풀링 의존'"),
        "attribution": ("귀속은 차분으로 보고하되 유의성 주장은 하지 않는다: "
                        "lim=LS-SS, fin=SL-SS, syn=LL-LS-SL+SS"),
        "secondary": ("전체 무력화율 · 비손실 비율 · BAND_AIM 은 **보고만** 한다. "
                      "1차 판정식에 넣지 않는다 (docs/47 §4.4 P45b)"),
        "null_case": ("세 팔 모두 기저를 못 넘으면 그것이 결과다: 어느 역할을 "
                      "학습시켜도 무개입+해석적 발사를 못 넘는다 (신청서 §4.7 폴백 (v))"),
    }


# ── 집계 ────────────────────────────────────────────────────────────────────
def _load(root: pathlib.Path) -> List[dict]:
    rows = []
    for f in sorted(root.rglob("summary.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:                                   # pragma: no cover
            continue
        ev = d.get("final_eval") or {}
        reg = (ev.get("by_regime") or {}).get(SHAPE, {})
        n_s = int(reg.get("n", 0) or 0)
        if not n_s:
            continue
        bands = d.get("final_eval_bands") or {}
        aim = bands.get(BAND) or {}
        k_s = int(round(float(reg.get("neutralized_rate", 0.0)) * n_s))
        lo, hi = wilson(k_s, n_s)
        rows.append({
            "run": f.parent.name,
            "arm": d.get("arm"),
            "limiter_policy": d.get("limiter_policy"),
            "finisher_policy": d.get("finisher_policy"),
            "seed": d.get("seed"), "w_kill": d.get("w_kill"),
            "n_eval": ev.get("n"),
            "shape_n": n_s, "shape_k": k_s,
            "shape_rate": reg.get("neutralized_rate"),
            "shape_wilson_lo": lo, "shape_wilson_hi": hi,
            "neutralized": ev.get("neutralized_rate"),
            "nondestructive": ev.get("nondestructive_frac"),
            "aim_n": int(aim.get("n") or 0),
            "aim_neutralized": (aim.get("neutralized") or {}).get("p"),
            "aim_net_capture": (aim.get("net_capture") or {}).get("p"),
        })
    return rows


def _pool(rows: List[dict]) -> dict:
    n = sum(r["shape_n"] for r in rows)
    k = sum(r["shape_k"] for r in rows)
    lo, hi = wilson(k, n)
    return {"n_runs": len(rows), "shape_n": n, "shape_k": k,
            "shape_rate": (k / n if n else None),
            "shape_wilson_lo": lo, "shape_wilson_hi": hi,
            "seeds": sorted(r["seed"] for r in rows)}


def aggregate(root: str, baseline_path: str = "results/hold_baseline.json",
              reference_path: str = "results/intercept_baseline.json") -> dict:
    """docs/48 §4 판정식. 규칙은 `verdict_rules()` 에 데이터로 실려 함께 나온다."""
    rows = _load(pathlib.Path(root))
    out: Dict[str, object] = {"rules": verdict_rules(), "n_runs": len(rows)}
    if not rows:
        out["note"] = "summary.json / final_eval 을 찾지 못했다"
        return out

    bp = pathlib.Path(baseline_path)
    if not bp.exists():
        out["note"] = (f"기저선이 없다: {bp}. "
                       f"`python -m shepherd.scripts.sweep_m4 --baseline 500` 을 먼저 돌릴 것")
        out["arms"] = {a: _pool([r for r in rows if r["arm"] == a])
                       for a in sorted({r["arm"] for r in rows})}
        return out
    base = json.loads(bp.read_text())
    b = base["by_regime"].get(SHAPE, {"n": 0, "k": 0, "wilson_hi": 1.0})
    b_hi = float(b.get("wilson_hi", 1.0))
    b_rate = float(b.get("neutralized_rate", 0.0) or 0.0)
    out["baseline_SS"] = {"shape_n": b.get("n"), "shape_k": b.get("k"),
                          "shape_rate": b_rate, "shape_wilson_hi": b_hi,
                          "overall_neutralized": base.get("neutralized_rate"),
                          "band_aim_neutralized": (
                              ((base.get("bands", {}).get(BAND) or {})
                               .get("neutralized") or {}).get("p"))}

    ref = None
    rp = pathlib.Path(reference_path)
    if rp.exists():
        ref = json.loads(rp.read_text())
        rb = ref["by_regime"].get(SHAPE, {})
        out["reference_intercept"] = {"shape_rate": rb.get("neutralized_rate"),
                                      "shape_wilson_hi": rb.get("wilson_hi")}

    arms: Dict[str, dict] = {}
    for a in sorted({r["arm"] for r in rows if r["arm"]}):
        g = [r for r in rows if r["arm"] == a]
        p = _pool(g)
        p["beats_baseline_pooled"] = bool(p["shape_wilson_lo"] > b_hi)
        p["seeds_beating_baseline"] = sum(int(r["shape_wilson_lo"] > b_hi) for r in g)
        p["per_seed"] = [{k: r[k] for k in
                          ("seed", "shape_n", "shape_k", "shape_rate",
                           "shape_wilson_lo", "shape_wilson_hi", "neutralized",
                           "nondestructive", "aim_n", "aim_neutralized",
                           "aim_net_capture")} for r in sorted(g, key=lambda x: x["seed"])]
        p["overall_neutralized_mean"] = _mean([r["neutralized"] for r in g])
        p["nondestructive_mean"] = _mean([r["nondestructive"] for r in g])
        p["aim_neutralized_mean"] = _mean([r["aim_neutralized"] for r in g])
        p["aim_net_capture_mean"] = _mean([r["aim_net_capture"] for r in g])
        arms[a] = p
    out["arms"] = arms

    # ── 판정 (선언된 규칙 그대로) ────────────────────────────────────────────
    def _lo(a):
        return arms[a]["shape_wilson_lo"] if a in arms else None

    def _hi(a):
        return arms[a]["shape_wilson_hi"] if a in arms else None

    def _strong(a):
        """풀링만이 아니라 **시드 과반**도 넘었는가.

        시드 수에 따라 자동으로 간다 (3시드 -> 2, 5시드 -> 3). 하드코딩하면
        시드를 늘렸을 때 기준이 조용히 느슨해진다 -- 5시드에서 2/5 는 다수가
        아니다."""
        if a not in arms:
            return None
        need = (arms[a]["n_runs"] + 1) // 2
        return bool(arms[a]["beats_baseline_pooled"]
                    and arms[a]["seeds_beating_baseline"] >= need)

    tests = {
        "H_lim": {"arm": "LS", "passed": (None if "LS" not in arms
                                          else bool(_lo("LS") > b_hi)),
                  "strong": _strong("LS")},
        "H_fin": {"arm": "SL", "passed": (None if "SL" not in arms
                                          else bool(_lo("SL") > b_hi)),
                  "strong": _strong("SL")},
        "H_syn": {"arm": "LL",
                  "passed": (None if not {"LL", "LS", "SL"} <= set(arms)
                             else bool(_lo("LL") > max(_hi("LS"), _hi("SL")))),
                  "strong": _strong("LL")},
    }
    out["tests"] = tests

    # 귀속 차분 (점추정만. 유의성 주장 없음 -- 규칙에 그렇게 선언했다)
    def _rate(a):
        return arms[a]["shape_rate"] if a in arms else None
    attr = {}
    if "LS" in arms:
        attr["limiter_only(LS-SS)"] = _rate("LS") - b_rate
    if "SL" in arms:
        attr["finisher_only(SL-SS)"] = _rate("SL") - b_rate
    if {"LL", "LS", "SL"} <= set(arms):
        attr["synergy(LL-LS-SL+SS)"] = _rate("LL") - _rate("LS") - _rate("SL") + b_rate
    if "LL" in arms:
        attr["joint(LL-SS)"] = _rate("LL") - b_rate
    out["attribution_shape"] = attr

    # 2차(보고용) — BAND_AIM. 여기가 사전 실측으로 개선 여지가 확인된 유일한 칸이다.
    out["band_aim_report"] = {
        "baseline_SS": out["baseline_SS"]["band_aim_neutralized"],
        "reference_intercept": (((ref or {}).get("bands", {}).get(BAND) or {})
                                .get("neutralized") or {}).get("p"),
        **{a: arms[a]["aim_neutralized_mean"] for a in arms},
        "_note": "보고 전용. 1차 판정식에 들어가지 않는다 (docs/47 §4.4 P45b).",
    }

    passed = [k for k, v in tests.items() if v["passed"]]
    if not passed:
        out["verdict"] = (
            "★ 어느 역할을 학습시켜도 SS(무개입+해석적 발사)를 못 넘었다 -- "
            "역할 분리로도 격차가 회수되지 않는다 (docs/48 §4 null_case). "
            "이 경우 결손은 '어느 한 역할' 이 아니라 학습 문제 자체에 있다")
    else:
        out["verdict"] = ("통과: " + ", ".join(passed) + ". "
                          + "; ".join(f"{k}={'강함' if tests[k]['strong'] else '풀링 의존'}"
                                      for k in passed))
    out["runs"] = rows
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="역할 분리 2x2 (docs/48)")
    ap.add_argument("--root", default="results/m4_roles")
    ap.add_argument("--total-env-steps", type=int, default=None)
    ap.add_argument("--eval-episodes", type=int, default=None)
    ap.add_argument("--final-eval-episodes", type=int, default=None)
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--arms", nargs="+", default=list(ARM_SPECS),
                    choices=list(ARM_SPECS))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--aggregate", default=None)
    ap.add_argument("--baseline-out", default="results/hold_baseline.json")
    ap.add_argument("--reference-out", default="results/intercept_baseline.json")
    a = ap.parse_args(argv)

    if a.aggregate:
        print(json.dumps(aggregate(a.aggregate, a.baseline_out, a.reference_out),
                         indent=2, ensure_ascii=False))
        return

    cmds = plan(a.root, a.total_env_steps, a.eval_episodes,
                a.final_eval_episodes, tuple(a.seeds), tuple(a.arms))
    if a.dry_run or not a.run:
        print(f"# {len(cmds)} 런 = 팔 {len(a.arms)} x 시드 {len(a.seeds)}  "
              f"(w_kill={W_KILL} 고정)")
        print("# SS 칸은 학습이 없다 -- results/hold_baseline.json (n=500) 을 쓴다")
        for _, c in cmds:
            print(" ".join(c))
        print(f"\n# 집계:  python -m shepherd.scripts.roles_split --aggregate {a.root}")
        return

    running = []
    for name, c in cmds:
        running.append((name, subprocess.Popen(c)))
        while len([p for _, p in running if p.poll() is None]) >= max(a.jobs, 1):
            for _, p in running:
                if p.poll() is None:
                    p.wait(); break
    for name, p in running:
        if p.wait() != 0:
            print(f"[FAIL] {name}", file=sys.stderr)
    print(json.dumps(aggregate(a.root, a.baseline_out, a.reference_out),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
