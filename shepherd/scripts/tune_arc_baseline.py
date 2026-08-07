"""docs/63 r2 scripted baseline 튜닝 러너 — F4 grid 9조합 × F5 예산.

    python -m shepherd.scripts.tune_arc_baseline --dry-run
    python -m shepherd.scripts.tune_arc_baseline --combo 0 --eps 5000 5100 \\
        --out results/arc_tuning_c0.json          # 서버 샤딩 (long-run policy)
    python -m shepherd.scripts.tune_arc_baseline --aggregate "results/arc_tuning_c*.json"

계약 (docs/63 r2 — 전부 동결값, 변경 금지):
  grid      = R_d {6, 9, 12} × Δφ {π/12, π/8, π/6}   (자유도 2축, 9조합)
  예산      = 조합당 train layer episode 5000..5099 (100 paired draws)
  선택 F7   = p_net 최대; tie ① total defense ② limiter 소모 少 ③ R_d 小
  F6        = TRAIN only — 이 파일은 layer="train" 하드코딩. IID/OOD 접근 없음
  §3.1      = 이 대역 성능은 선택 전용 — headline 수치로 재사용 금지

world contract = MARL 평가와 동일 (ratified F-계약 + threat_layer draw,
docs/65 A4c — parity 는 tests/test_arc_baseline 이 manifest 로 인증).
torch-free.
"""
from __future__ import annotations

import argparse
import glob as _glob
import json
import math
import pathlib

from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_env import build_m4_env
from shepherd.scripts.mission_rollout import run_episode

__all__ = ["GRID", "TUNE_EPS", "world_kw", "run_combo", "select"]

# ── docs/63 F4 (동결) ───────────────────────────────────────────────────────
R_D = (6.0, 9.0, 12.0)
DPHI = (math.pi / 12, math.pi / 8, math.pi / 6)
GRID = tuple(dict(r_d=r, dphi=d) for r in R_D for d in DPHI)   # combo 0..8
TUNE_EPS = range(5000, 5100)                                   # F5 대역
_LAYER = "train"                                               # F6 하드코딩

_CAPTURE = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")


def world_kw() -> dict:
    """MARL 평가와 동일한 world 구성 (A4c parity 의 비교 대상)."""
    return dict(system=ratified_system(),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                threat_layer=_LAYER)


def run_combo(ci: int, eps=TUNE_EPS, log=print) -> dict:
    kw = GRID[ci]
    rows = []
    for ep in eps:
        st = build_m4_env(0, ep, **world_kw())
        r = run_episode(st.env, st.scn, st.lay, seed=ep,
                        limiter_mode="arc", fire_mode="clean", limiter_kw=kw)
        rows.append(dict(episode=ep, label=r.label, steps=r.steps,
                         n_contact=r.n_contact))
        if log:
            log(f"c{ci} ep{ep}: {r.label:>11} steps={r.steps:>4}", flush=True)
    n = len(rows)
    counts: dict = {}
    for r in rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1
    return dict(combo=ci, **{k: float(v) for k, v in GRID[ci].items()},
                n=n,
                p_net=sum(counts.get(k, 0) for k in _CAPTURE) / n,
                total_defense=1.0 - counts.get("PENETRATED", 0) / n,
                limiter_contact_mean=float(
                    sum(r["n_contact"] for r in rows)) / n,
                counts=counts, rows=rows)


def select(combos: list) -> dict:
    """F7: p_net 최대; tie ① total defense ② 접촉(소모 대리) 少 ③ R_d 小."""
    key = lambda c: (-c["p_net"], -c["total_defense"],           # noqa: E731
                     c["limiter_contact_mean"], c["r_d"])
    ranked = sorted(combos, key=key)
    return dict(selected=ranked[0]["combo"],
                r_d=ranked[0]["r_d"], dphi=ranked[0]["dphi"],
                table=[{k: c[k] for k in ("combo", "r_d", "dphi", "n",
                                          "p_net", "total_defense",
                                          "limiter_contact_mean", "counts")}
                       for c in combos],
                note=("docs/63 §3.1: 이 표는 선택 증거 — headline 수치로 "
                      "재사용 금지. 9조합 전체 의무 공개."))


def main() -> None:
    ap = argparse.ArgumentParser(description="docs/63 arc baseline tuning")
    ap.add_argument("--combo", type=int, default=None, help="0..8 (샤딩 단위)")
    ap.add_argument("--eps", type=int, nargs=2, default=[5000, 5100],
                    metavar=("A", "B"), help="tune 대역 부분구간 [A, B)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--aggregate", default=None,
                    help="glob 패턴의 combo JSON 들을 모아 F7 선택")
    a = ap.parse_args()

    if a.dry_run:
        for i, g in enumerate(GRID):
            print(f"combo {i}: r_d={g['r_d']:g} dphi={g['dphi']:.4f}")
        print(f"# 대역 {TUNE_EPS.start}..{TUNE_EPS.stop - 1} · 총 "
              f"{len(GRID) * len(TUNE_EPS)} 롤아웃 (서버 샤딩 권장)")
        return
    if a.aggregate:
        combos = [json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
                  for f in sorted(_glob.glob(a.aggregate))]
        assert len(combos) == len(GRID), f"9조합 필요, {len(combos)}개 발견"
        out = select(combos)
        print(json.dumps({k: out[k] for k in ("selected", "r_d", "dphi")},
                         indent=1))
        p = pathlib.Path(a.out or "results/arc_tuning_selected.json")
        p.write_text(json.dumps(out, indent=1, ensure_ascii=False),
                     encoding="utf-8")
        print(f"-> {p}")
        return

    assert a.combo is not None, "--combo 0..8 필요 (또는 --dry-run/--aggregate)"
    assert 5000 <= a.eps[0] and a.eps[1] <= 5100, "F5 대역 밖 (5000..5100)"
    out = run_combo(a.combo, range(a.eps[0], a.eps[1]))
    p = pathlib.Path(a.out or f"results/arc_tuning_c{a.combo}.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"c{a.combo}: p_net={out['p_net']:.3f} "
          f"total_defense={out['total_defense']:.3f} -> {p}")


if __name__ == "__main__":
    main()
