"""M4 학습 스윕 — 실행기 + 집계기 (docs/47 §4.3 판정식).

1차 질문은 하나다: **학습 정책이 무개입(hold) 을 이기는가.**

`docs/46` 은 손튜닝 배치(ring/intercept)가 hold 를 이기지 못한다는 것을 두 채널로
분해해 보였다. 판정식은 **결과를 보기 전에** 선언되어 있다 (docs/47 §4.3 정정판):

    1차   SHAPING_NEEDED 영역의 무력화율이 hold 기저(0/297)를 유의하게 넘는가
          -> Wilson 하한 > hold 의 Wilson 상한 (0.0128)
    2차   비손실 비율은 **w_kill 축을 따라 정책끼리** 비교한다 (단조성)
    참조  최강 손튜닝 기준선 intercept+커밋 (15/182 = 8.2%, Wilson 상한 0.1315)
          hold 만 넘는 것은 약한 기준이므로 이 값도 함께 보고한다. 넘으면 강한 결과,
          못 넘으면 "무개입보다는 낫지만 최선의 손튜닝은 못 이긴다" 가 결과다.

    [정정 2026-08-01, 결과 전] 처음 선언은 "hold 대비 무력화율과 비손실 비율을 둘 다
    개선" 이었다. **성립 불가능한 조건이다** -- 스크립트 기준선은 `baseline_commit=False`
    라 구조적으로 하드킬을 못 하므로 hold 의 비손실 비율은 자명하게 1.00 이고 어떤
    정책도 그것을 '개선' 할 수 없다 (n=200 실측 확인). 또한 전체 평균 무력화율은
    regime 격차(shape 0.000 vs free 0.397)를 가린다.

축 (선언)
---------
    w_kill      {0.0, 0.25, 0.5, 0.75, 1.0}      RewardSpec 의 유일한 핵심 노브
    seed        {0, 1, 2, 3, 4}                   시드 분산
    threat_obs  {on, off}                         regime-blind 대조군 (§6 ablation)
                                                  = 5 x 5 x 2 = 50 런

`SWEEP_AXES` (omega_max · kill_radius · tau_kill) 는 **1차 스윕 뒤**에 승자 설정
하나에 대해서만 돌린다 -- 강건성 확인이지 탐색이 아니다. 여기서 같이 돌리면
50 -> 900 런이 되고, 그건 "좋은 값 찾기" 가 되어 선언 규율을 깬다.

사용
----
    python -m shepherd.scripts.sweep_m4 --baseline 500       # hold 기저선 (한 번만)
    python -m shepherd.scripts.sweep_m4 --dry-run            # 명령 50개만 출력
    python -m shepherd.scripts.sweep_m4 --run --jobs 4       # 이 기계에서 실행
    python -m shepherd.scripts.sweep_m4 --aggregate results/m4_sweep

torch 를 직접 쓰지 않는다 (자식 프로세스가 쓴다).
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import subprocess
import sys

__all__ = ["plan", "aggregate", "wilson", "measure_baseline", "SHAPE"]

from shepherd.scripts.curve_sweep import summarize_bands
from shepherd.stats import wilson          # 판정식이 걸린 식 -- 정의는 shepherd/stats.py 한 곳뿐

SHAPE = "SHAPING_NEEDED"
BAND = "BAND_AIM"          # docs/47 §4.4 -- 보고 축. 1차 판정식에는 들어가지 않는다.
FREE = "FREE_CAPTURE"


def measure_baseline(n: int = 500, seed0: int = 0, mode: str = "hold") -> dict:
    """손튜닝 기저선을 **한 번만** 잰다. 런마다 다시 잴 필요가 없다.

    `mode="intercept"` 는 2차 참조(최강 손튜닝)다. ★ 커밋 비트는 limiter 행동에
    실려 있으므로 `limiter_mode` 와 `baseline_commit` 을 **같이** 켜야 한다 --
    `hold + commit` 은 `hold` 와 완전히 같다 (정정 8, docs/45 §9.6).
    """
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, ratified_system
    from shepherd.m4_env import mission_eval
    from shepherd.spawn_rand import SpawnSpec

    recs: list = []
    # ★ docs/65 A2 — 기저선도 학습과 **같은 비준 계약**에서 잰다. 종전의 bare
    #   SystemSpec() 기저선(docs/47 hold 0/297 등)은 legacy 구계약 산물이며
    #   재집계 시 그 한정을 병기한다. 새 측정과 옛 JSON 을 섞지 않는다.
    r = mission_eval(seed0, n, system=ratified_system(),
                     reward=RewardSpec(w_kill=0.5, enabled=True),
                     attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                     spawn=SpawnSpec(), limiter_mode=mode,
                     baseline_commit=(mode == "intercept"), records=recs)
    out = {"contract": r.get("contract"), "n": n, "limiter_mode": mode,
           "baseline_commit": (mode == "intercept"), "attacker": "A2/jink0.6",
           "neutralized_rate": r["neutralized_rate"],
           "nondestructive_frac": r["nondestructive_frac"],
           "counts": r["counts"], "by_regime": {}}
    for reg, v in r["by_regime"].items():
        k = int(round(v["neutralized_rate"] * v["n"]))
        lo, hi = wilson(k, v["n"])
        out["by_regime"][reg] = {"n": v["n"], "k": k,
                                 "neutralized_rate": v["neutralized_rate"],
                                 "wilson_lo": lo, "wilson_hi": hi}
    # ★ 세 칸 기저선. 학습 런과 **같은 함수**로 집계해야 비교가 성립한다 (docs/47 §4.4).
    out["bands"] = summarize_bands(recs)
    out["_note"] = ("비손실 비율은 hold 와 비교하지 않는다 -- 스크립트 기준선은 "
                    "구조적으로 하드킬을 못 해 자명하게 1.00 이다 (docs/47 §4.3).")
    return out

W_KILL = (0.0, 0.25, 0.5, 0.75, 1.0)
SEEDS = (0, 1, 2, 3, 4)
THREAT_OBS = (True, False)


def tag(w, s, obs):
    return f"w{w:g}_s{s}_obs{'1' if obs else '0'}"


def plan(root: str, total_steps: int | None, eval_eps: int | None) -> list:
    cmds = []
    for w, s, obs in itertools.product(W_KILL, SEEDS, THREAT_OBS):
        out = str(pathlib.Path(root) / tag(w, s, obs))
        c = [sys.executable, "-m", "shepherd.scripts.train_m4",
             "--w-kill", str(w), "--seed", str(s), "--output", out]
        if not obs:
            c.append("--no-threat-obs")
        if total_steps is not None:
            c += ["--total-env-steps", str(total_steps)]
        if eval_eps is not None:
            c += ["--eval-episodes", str(eval_eps)]
        cmds.append((tag(w, s, obs), c))
    return cmds


# --------------------------------------------------------------- 집계 ---
def _load(root: pathlib.Path) -> list:
    rows = []
    for f in sorted(root.rglob("summary.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:                                   # pragma: no cover
            continue
        ev = d.get("final_eval") or d.get("final") or {}
        reg = (ev.get("by_regime") or {}).get(SHAPE, {})
        n_s = int(reg.get("n", 0) or 0)
        bands = d.get("final_eval_bands") or {}
        aim = bands.get(BAND) or {}
        rows.append({
            "run": f.parent.name,
            "seed": d.get("seed"), "w_kill": d.get("w_kill"),
            "threat_obs": d.get("threat_obs"), "attacker": d.get("attacker"),
            "aim_n": int((aim.get("n") or 0)),
            "aim_neutralized": (aim.get("neutralized") or {}).get("p"),
            "aim_net_capture": (aim.get("net_capture") or {}).get("p"),
            "n_eval": ev.get("n"),
            "neutralized": ev.get("neutralized_rate"),
            "nondestructive": ev.get("nondestructive_frac"),
            "shape_n": n_s,
            "shape_k": int(round(float(reg.get("neutralized_rate", 0.0)) * n_s)),
            "shape_rate": reg.get("neutralized_rate"),
        })
    return rows


def aggregate(root: str, baseline: dict | None = None,
              baseline_path: str | None = None,
              reference: dict | None = None,
              reference_path: str | None = None) -> dict:
    """docs/47 §4.3 판정식.

    1차: SHAPING_NEEDED 무력화율의 Wilson 하한 > hold 기저의 Wilson 상한
    2차: 비손실 비율의 w_kill 축 단조성 (hold 대비 아님)
    """
    import numpy as np
    rows = [r for r in _load(pathlib.Path(root)) if r["shape_n"]]
    if not rows:
        return {"n": 0, "note": "summary.json / final_eval 을 찾지 못했다"}

    if baseline is None and baseline_path:
        baseline = json.loads(pathlib.Path(baseline_path).read_text())
    if baseline is None:
        baseline = measure_baseline(500)
    b = baseline["by_regime"].get(SHAPE, {"n": 0, "k": 0, "wilson_hi": 1.0})
    b_hi = float(b.get("wilson_hi", 1.0))

    if reference is None and reference_path and pathlib.Path(reference_path).exists():
        reference = json.loads(pathlib.Path(reference_path).read_text())
    r_hi = None
    if reference:
        rb = reference["by_regime"].get(SHAPE, {})
        r_hi = float(rb.get("wilson_hi")) if rb.get("wilson_hi") is not None else None

    out = {"n_runs": len(rows),
           "baseline_hold": {"shape_n": b.get("n"), "shape_k": b.get("k"),
                             "shape_rate": b.get("neutralized_rate"),
                             "shape_wilson_hi": b_hi,
                             "overall_neutralized": baseline.get("neutralized_rate")},
           "by_w_kill": {}, "runs_beating_baseline": 0, "verdict": None}
    if reference:
        rb = reference["by_regime"].get(SHAPE, {})
        out["reference_intercept"] = {
            "limiter_mode": reference.get("limiter_mode"),
            "shape_n": rb.get("n"), "shape_k": rb.get("k"),
            "shape_rate": rb.get("neutralized_rate"),
            "shape_wilson_hi": r_hi,
            "nondestructive_frac": reference.get("nondestructive_frac")}

    beats = 0
    for r in rows:
        lo, hi = wilson(r["shape_k"], r["shape_n"])
        r["shape_wilson_lo"], r["shape_wilson_hi"] = lo, hi
        r["beats_baseline"] = bool(lo > b_hi)
        r["beats_reference"] = bool(r_hi is not None and lo > r_hi)
        beats += int(r["beats_baseline"])

    for w in sorted({r["w_kill"] for r in rows}):
        g = [r for r in rows if r["w_kill"] == w]
        out["by_w_kill"][str(w)] = {
            "n_runs": len(g),
            "shape_rate_med": float(np.median([r["shape_rate"] for r in g])),
            "shape_wilson_lo_med": float(np.median([r["shape_wilson_lo"] for r in g])),
            "overall_neutralized_med": float(np.median([r["neutralized"] for r in g])),
            "nondestructive_med": float(np.median([r["nondestructive"] for r in g])),
            "runs_beating_baseline": sum(r["beats_baseline"] for r in g),
            "runs_beating_reference": sum(r.get("beats_reference", False) for r in g),
        }

    # 2차: w_kill 을 올리면 비손실 비율이 오르는가 (정책 간 비교)
    ws = sorted(out["by_w_kill"], key=float)
    nd = [out["by_w_kill"][w]["nondestructive_med"] for w in ws]
    out["secondary_nondestructive_monotone"] = all(
        nd[i] <= nd[i + 1] + 1e-9 for i in range(len(nd) - 1))
    out["secondary_nondestructive_by_w_kill"] = dict(zip(ws, nd))

    # ── BAND_AIM (보고 축, docs/47 §4.4) ──────────────────────────────────
    #   1차 판정에는 쓰지 않는다. 다만 여기가 유일하게 "개선 여지가 있다"고
    #   **사전 실측으로** 확인된 구간이므로, 판정과 별개로 항상 같이 낸다.
    aim = [r for r in rows if r.get("aim_neutralized") is not None]
    if aim:
        b = (baseline or {}).get("bands", {}).get(BAND) or {}
        out["band_aim"] = {
            "n_runs": len(aim),
            "baseline_net_capture": (b.get("net_capture") or {}).get("p"),
            "baseline_neutralized": (b.get("neutralized") or {}).get("p"),
            "reference_neutralized": (((reference or {}).get("bands", {})
                                       .get(BAND) or {}).get("neutralized") or {}).get("p"),
            "run_neutralized_med": float(np.median([r["aim_neutralized"] for r in aim])),
            "run_net_capture_med": float(np.median([r["aim_net_capture"] for r in aim])),
            "run_n_med": float(np.median([r["aim_n"] for r in aim])),
            "_note": "보고 전용. 1차 판정식(§4.3)은 SHAPING_NEEDED 로 고정돼 있다.",
        }
    else:
        out["band_aim"] = {"n_runs": 0,
                           "_note": "summary.json 에 final_eval_bands 가 없다 -- 구버전 런"}

    obs_on = [r for r in rows if r["threat_obs"]]
    obs_off = [r for r in rows if not r["threat_obs"]]
    if obs_on and obs_off:
        out["threat_obs_ablation"] = {
            "on_shape_rate_med": float(np.median([r["shape_rate"] for r in obs_on])),
            "off_shape_rate_med": float(np.median([r["shape_rate"] for r in obs_off])),
        }
    out["runs_beating_baseline"] = beats
    ref_beats = sum(r.get("beats_reference", False) for r in rows)
    out["runs_beating_reference"] = int(ref_beats)
    if not beats:
        out["verdict"] = ("★ 협력의 순이득 없음 (docs/47 §4.3 선언 판정식) -- "
                          "hold 기저를 넘은 런이 없다")
    elif r_hi is not None and not ref_beats:
        out["verdict"] = (f"부분 순이득 -- {beats}/{len(rows)} 런이 무개입(hold)은 넘었으나 "
                          f"최선의 손튜닝(intercept, 상한 {r_hi:.4f})은 하나도 넘지 못했다")
    else:
        out["verdict"] = (f"협력의 순이득 있음 -- hold 초과 {beats}/{len(rows)}"
                          + (f", 최선의 손튜닝 초과 {ref_beats}/{len(rows)}" if r_hi is not None else ""))
    out["runs"] = rows
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="M4 학습 스윕 (docs/46 §4.2)")
    ap.add_argument("--root", default="results/m4_sweep")
    ap.add_argument("--total-env-steps", type=int, default=None)
    ap.add_argument("--eval-episodes", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--aggregate", default=None)
    ap.add_argument("--baseline", type=int, default=None,
                    help="hold 기저선을 이 판수로 재서 --baseline-out 에 저장하고 끝낸다")
    ap.add_argument("--baseline-out", default="results/hold_baseline.json")
    ap.add_argument("--reference", type=int, default=0,
                    help="최강 손튜닝 기준선(intercept+커밋)을 이 판수로 재서 "
                         "--reference-out 에 저장하고 끝낸다")
    ap.add_argument("--reference-out", default="results/intercept_baseline.json",
                    help="최강 손튜닝 기준선(intercept+커밋). 2차 참조")
    a = ap.parse_args(argv)

    if a.baseline or a.reference:
        n, mode, dest = ((a.baseline, "hold", a.baseline_out) if a.baseline
                         else (a.reference, "intercept", a.reference_out))
        b = measure_baseline(n, mode=mode)
        p = pathlib.Path(dest); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(b, indent=2, ensure_ascii=False))
        print(json.dumps(b, indent=2, ensure_ascii=False))
        print(f"\n# 저장: {p}")
        return

    if a.aggregate:
        bp = a.baseline_out if pathlib.Path(a.baseline_out).exists() else None
        rp = a.reference_out if pathlib.Path(a.reference_out).exists() else None
        print(json.dumps(aggregate(a.aggregate, baseline_path=bp, reference_path=rp),
                         indent=2, ensure_ascii=False))
        return

    cmds = plan(a.root, a.total_env_steps, a.eval_episodes)
    if a.dry_run or not a.run:
        print(f"# {len(cmds)} 런 (w_kill {len(W_KILL)} x seed {len(SEEDS)} x obs {len(THREAT_OBS)})")
        for _, c in cmds:
            print(" ".join(c))
        print(f"\n# 집계:  python -m shepherd.scripts.sweep_m4 --aggregate {a.root}")
        return

    running = []
    for name, c in cmds:
        running.append((name, subprocess.Popen(c)))
        while len([p for _, p in running if p.poll() is None]) >= max(a.jobs, 1):
            for _, p in running:
                if p.poll() is None:
                    p.wait(); break
    for name, p in running:
        rc = p.wait()
        if rc != 0:
            print(f"[FAIL] {name} rc={rc}", file=sys.stderr)
    print(json.dumps(aggregate(a.root), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
