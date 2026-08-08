"""docs/71 primary 판정기 — LS-COMMIT ABLATION Δ_shape (사전등록 §1.1/§1.2).

    python -m shepherd.scripts.analyze_ls_commit --eval-dir results/iid_abl \\
        --out results/iid_abl/primary_delta_shape.json

읽는 것 = `eval_iid.py` 산출 JSON 들 (`{arm}_seed{k}*.json`). 이 파일이 계약을
코드로 못박는다:

  primary endpoint  Δ_shape = p_net^{LS-off,SHAPING} − p_net^{LS-live,SHAPING}
  confirmatory      training seeds (1, 2, 3, 4)          <- 상수. 인자로 못 바꾼다
  index (제외)      training seed 0 = 이 ablation 을 촉발한 index seed.
                    별도 블록으로 병기하되 **primary CI 계산에 들어가지 않는다**
  bootstrap         최상위 재표집 단위 = training seed, 그 안에서 paired
                    episode 재표집 (nested). 시드 간 episode pooling 금지 (§1.2)
  판정              two-sided 95% CI 하한 > 0 = positive evidence.
                    one-sided 95% 하한도 같이 보고하되 판정식은 위 하나다.
  대역              ablation = iid 10300..10599 (eval_iid.BANDS)

paired 성립 조건은 **가정이 아니라 검사**다: 같은 episode id 의 두 팔 행이
같은 `world_hash` · 같은 `regime` 이어야 하고, 아니면 판정 대신 예외를 낸다.
SHAPING/FREE 는 rollout 전에 정해진 pre-treatment 라벨이다 (docs/71 §0.1③).

torch-free.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pathlib
import re
from typing import Dict, List

import numpy as np

from shepherd.scripts.eval_iid import BANDS

__all__ = ["CONFIRMATORY_SEEDS", "INDEX_SEED", "PRIMARY_BAND", "SHAPING",
           "load_arm", "paired_seed", "primary", "analyze"]

# ── 사전등록 상수 (docs/71 — 코드 수준 잠금) ─────────────────────────────────
CONFIRMATORY_SEEDS = (1, 2, 3, 4)
INDEX_SEED = 0
PRIMARY_BAND = "ablation"           # eval_iid.BANDS["ablation"] = (10300, 300)
SHAPING = "SHAPING_NEEDED"
CAPTURE = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")     # p_net 정의 (label_rates 동형)
B_BOOT = 10_000
RNG_SEED = 7
ARMS = ("ls-live", "ls-off")


def load_arm(eval_dir: str, arm: str) -> Dict[int, List[dict]]:
    """`{arm}_seed{k}*.json` 들을 training seed 별로 병합 (샤드 허용).

    대역 완전성 = 선언된 대역의 episode 집합과 **정확히 일치**해야 한다
    (누락·중복·초과 전부 예외). 샤드를 하나 빼먹고 판정하는 사고를 막는다.
    """
    ep0, n = BANDS[PRIMARY_BAND]
    want = set(range(ep0, ep0 + n))
    by_seed: Dict[int, List[dict]] = {}
    for f in sorted(glob.glob(os.path.join(eval_dir, f"{arm}_seed*.json"))):
        m = re.search(rf"{re.escape(arm)}_seed(\d+)", os.path.basename(f))
        if not m:
            continue
        d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        if d.get("band") != PRIMARY_BAND:
            raise ValueError(f"{f}: band={d.get('band')} != {PRIMARY_BAND}")
        if d.get("arm") != arm:
            raise ValueError(f"{f}: arm={d.get('arm')} != {arm}")
        if int(d.get("training_seed", -1)) != int(m.group(1)):
            raise ValueError(f"{f}: 파일명 seed 와 training_seed 불일치")
        by_seed.setdefault(int(m.group(1)), []).extend(d["rows"])
    if not by_seed:
        raise SystemExit(f"{eval_dir} 에 {arm}_seed*.json 이 없다")
    for s, rows in by_seed.items():
        eps = [r["episode"] for r in rows]
        if len(eps) != len(set(eps)):
            raise ValueError(f"{arm} seed{s}: 중복 episode (샤드가 겹쳤다)")
        if set(eps) != want:
            miss, extra = sorted(want - set(eps)), sorted(set(eps) - want)
            raise ValueError(f"{arm} seed{s}: 대역 불완전 "
                             f"(누락 {len(miss)} 개, 대역 외 {len(extra)} 개)")
        rows.sort(key=lambda r: r["episode"])
    return by_seed


def paired_seed(live: List[dict], off: List[dict]) -> Dict[str, np.ndarray]:
    """한 training seed 의 paired SHAPING 지표. world/regime 동일성을 검사한다."""
    for a, b in zip(live, off):
        if a["episode"] != b["episode"]:
            raise ValueError("paired 정렬 실패 (episode 불일치)")
        if a["world_hash"] != b["world_hash"]:
            raise ValueError(
                f"ep{a['episode']}: 두 팔의 world_hash 가 다르다 -- 같은 IID "
                f"episode 가 같은 world draw 를 만들지 않았다 (paired 무효)")
        if a["regime"] != b["regime"]:
            raise ValueError(
                f"ep{a['episode']}: regime 이 팔에 따라 다르다 "
                f"({a['regime']} vs {b['regime']}) -- pre-treatment 라벨 위반")
    idx = [i for i, a in enumerate(live) if a["regime"] == SHAPING]
    if not idx:
        raise ValueError("SHAPING 판이 0 개다 -- Δ_shape 가 성립하지 않는다")
    net = lambda rows: np.array(                                    # noqa: E731
        [1.0 if rows[i]["label"] in CAPTURE else 0.0 for i in idx], float)
    return {"live": net(live), "off": net(off), "n_shaping": len(idx)}


def _boot(pairs: Dict[int, Dict[str, np.ndarray]], rng, b: int = B_BOOT) -> np.ndarray:
    """§1.2: 최상위 = training seed 재표집, 그 안에서 paired episode 재표집.

    두 팔에 **같은 episode 인덱스**를 쓴다 (paired). 시드 간 episode 는 절대
    한 통에 섞지 않는다 -- 그러면 4 시드가 1200 판의 독립 반복처럼 보인다.
    """
    seeds = sorted(pairs)
    k = len(seeds)
    stats = np.empty(b)
    for i in range(b):
        pick = rng.choice(k, size=k, replace=True)
        ds = []
        for j in pick:
            p = pairs[seeds[j]]
            m = len(p["live"])
            idx = rng.integers(0, m, size=m)            # paired: 같은 인덱스
            ds.append(float(p["off"][idx].mean() - p["live"][idx].mean()))
        stats[i] = float(np.mean(ds))
    return stats


def primary(pairs: Dict[int, Dict[str, np.ndarray]]) -> dict:
    """confirmatory 시드들만으로 Δ_shape 판정 통계를 낸다."""
    missing = [s for s in CONFIRMATORY_SEEDS if s not in pairs]
    if missing:
        raise SystemExit(f"confirmatory seed {missing} 의 두 팔 평가가 없다 "
                         f"-- 9 런 완주 후 일괄 평가가 전제다 (docs/71 §2)")
    use = {s: pairs[s] for s in CONFIRMATORY_SEEDS}     # index seed 는 여기서 배제
    per_seed = {s: float(p["off"].mean() - p["live"].mean()) for s, p in use.items()}
    dist = _boot(use, np.random.default_rng(RNG_SEED))
    ci = [float(np.percentile(dist, 2.5)), float(np.percentile(dist, 97.5))]
    return {
        "confirmatory_seeds": list(CONFIRMATORY_SEEDS),
        "index_seed_excluded": INDEX_SEED,
        "delta_shape_per_seed": per_seed,                # §1.2 raw 공개 의무
        "p_net_shaping_per_seed": {
            s: {"ls_live": float(p["live"].mean()), "ls_off": float(p["off"].mean()),
                "n_shaping": int(p["n_shaping"])} for s, p in use.items()},
        "delta_shape_point": float(np.mean(list(per_seed.values()))),
        "ci95": ci,
        "lower95_one_sided": float(np.percentile(dist, 5.0)),
        "b_boot": B_BOOT, "rng_seed": RNG_SEED,
        "decision_statistic": "two-sided 95% CI lower bound (ci95[0]) > 0",
        "positive_evidence": bool(ci[0] > 0.0),
    }


def analyze(eval_dir: str) -> dict:
    by_arm = {a: load_arm(eval_dir, a) for a in ARMS}
    seeds = sorted(set(by_arm["ls-live"]) & set(by_arm["ls-off"]))
    pairs = {s: paired_seed(by_arm["ls-live"][s], by_arm["ls-off"][s])
             for s in seeds}
    out = {
        "contract_doc": "docs/71 §1.1/§1.2 primary — Δ_shape",
        "band": PRIMARY_BAND, "episodes": list(BANDS[PRIMARY_BAND]),
        "seeds_available": seeds,
        "primary": primary(pairs),
    }
    if INDEX_SEED in pairs:                 # 병기 -- primary 에 들어가지 않는다
        p = pairs[INDEX_SEED]
        out["index_seed"] = {
            "seed": INDEX_SEED,
            "status": ("이 ablation 을 촉발한 index seed. mechanistic 증거로만 "
                       "보고하며 primary CI 에서 제외된다 (docs/71 §1.1)"),
            "p_net_shaping": {"ls_live": float(p["live"].mean()),
                              "ls_off": float(p["off"].mean())},
            "delta_shape": float(p["off"].mean() - p["live"].mean()),
            "n_shaping": int(p["n_shaping"])}
    pr = out["primary"]
    out["verdict"] = (
        "positive evidence: disabling commit recovered SHAPING-regime net "
        "capture (causal contributor, NOT 'the causal blocker'). headline 은 "
        "교체되지 않는다 (docs/71 §3)"
        if pr["positive_evidence"] else
        "disabling commit did not recover measurable SHAPING-regime "
        "net-capture gain under the frozen learning contract -> 본편 rescue "
        "search 종료 (docs/71 §3 stop rule)")
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="docs/71 Δ_shape primary 판정")
    ap.add_argument("--eval-dir", required=True,
                    help="eval_iid 산출 디렉터리 ({arm}_seed{k}*.json)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    out = analyze(a.eval_dir)
    pr = out["primary"]
    print(f"Δ_shape = {pr['delta_shape_point']:+.4f}  "
          f"CI95 [{pr['ci95'][0]:+.4f}, {pr['ci95'][1]:+.4f}]  "
          f"(one-sided 95% 하한 {pr['lower95_one_sided']:+.4f})")
    for s, d in sorted(pr["delta_shape_per_seed"].items()):
        q = pr["p_net_shaping_per_seed"][s]
        print(f"  seed{s}: live {q['ls_live']:.3f} -> off {q['ls_off']:.3f} "
              f"(d={d:+.3f}, n_shaping={q['n_shaping']})")
    if "index_seed" in out:
        i = out["index_seed"]
        print(f"  [index seed{i['seed']} — primary 제외] "
              f"live {i['p_net_shaping']['ls_live']:.3f} -> "
              f"off {i['p_net_shaping']['ls_off']:.3f} (d={i['delta_shape']:+.3f})")
    print(out["verdict"])
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"-> {p}")


if __name__ == "__main__":
    main()
