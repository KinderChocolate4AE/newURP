"""R2b C arm viz-first — 대표 C plan 궤적의 육안 검증 (judge artifact 배제).

    python -m shepherd.scripts.r2b_c_viz

정책 (viz-first): 새 regime 의 수치 심층 탐색 전에 궤적부터 본다. 3판:
  V1  저 η 고이득 flip  — 셀 (0, 0.60, 2.4)  A_N=0 → C_N=1 인 최소 s
  V2  저 η 고이득 flip  — 셀 (2, 0.56, 2.4)  A_N=0 → C_N=1 인 최소 s
  V3  고 η search 실패  — 셀 (0, 0.54, 3.9)  lite_no_solution ∧ C_N=0 인 최소 s
각 판마다 A(hold) 와 C(재현 plan) 를 같은 축에 나란히 그린다.

**replay-parity gate**: plan 은 봉인 search 의 결정론 재실행 (search_plan,
solver RNG 동일) 으로 재현하며, full replay 의 (label, fire_step, steps) 가
c_arm shard 기록과 일치해야만 그림을 낸다 — 불일치 시 즉시 abort (플랫폼 FP
발산/코드 회귀 검출). A(hold) 도 phase1_v2 기록과 동일 gate. torch-free + mpl.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.mission_rollout import run_episode                # noqa: E402
from shepherd.scripts.r2b_c_runner import (                             # noqa: E402
    ART2, SEED0, _rollout, search_plan)
from shepherd.scripts.r2b_phase1 import _cells, _slices                 # noqa: E402

OUT = ROOT / "figures" / "r2b_c_viz_trajectories.png"
PICKS = (  # (slice, chi_c, eta_c, 목적, predicate 이름)
    (0, 0.60, 2.4, "low-eta flip", "flip"),
    (2, 0.56, 2.4, "low-eta flip", "flip"),
    (0, 0.54, 3.9, "high-eta search fail", "nosol_fail"),
)


def _records():
    crecs = {}
    for f in sorted((ART2 / "c_arm").glob("shard*.json")):
        for r in json.loads(f.read_text(encoding="utf-8"))["records"]:
            crecs[r["s"]] = r
    ab = {}
    for f in sorted((ART2 / "phase1_v2").glob("shard*.json")):
        for r in json.loads(f.read_text(encoding="utf-8"))["records"]:
            ab[(r["s"], r["arm"])] = r
    return crecs, ab


def _pick(crecs, ab, sl, chi_c, eta_c, kind) -> int:
    cand = sorted(r["s"] for r in crecs.values()
                  if r["slice"] == sl and r["cell"] == [chi_c, eta_c])
    for s in cand:
        a_n = int(ab[(s, "A")]["label"] == "NET_CAPTURE")
        r = crecs[s]
        if kind == "flip" and r["C_N"] == 1 and a_n == 0:
            return s
        if kind == "nosol_fail" and r["lite_no_solution"] and r["C_N"] == 0:
            return s
    raise RuntimeError(f"no scenario for {(sl, chi_c, eta_c, kind)}")


def _replay(s: int, cand, kw) -> tuple:
    """telemetry 붙인 full-fidelity replay 1회 — _rollout 과 동일 경로."""
    st = build_m4_env(SEED0, s, **kw)
    tel: list = []
    from shepherd.scripts.r2b_c_runner import _fresh, _plan_policy
    _fresh(st.env)
    if cand[0] == "policy":
        r = run_episode(st.env, st.scn, st.lay, seed=SEED0 + s,
                        limiter_mode=cand[1], fire_mode="clean", telemetry=tel)
    else:
        r = run_episode(st.env, st.scn, st.lay, seed=SEED0 + s,
                        policy=_plan_policy(st.env, cand[1], int(st.lay.episode_len)),
                        scripted_roles=("finisher",), fire_mode="clean",
                        telemetry=tel)
    return r, tel, st


def _panel(ax, r, tel, st, title):
    att = np.array([f["p_att"] for f in tel])
    fin = np.array([f["p_fin"] for f in tel])
    lims = np.array([f["p_lims"] for f in tel])          # (T, n_lim, 3)
    tgt = np.asarray(st.lay.target, float)
    ax.plot(att[:, 0], att[:, 1], "-", color="tab:blue", lw=1.6, label="attacker")
    ax.plot(*att[0, :2], "o", color="tab:blue", ms=5, mfc="none")
    ax.plot(*att[-1, :2], "o", color="tab:blue", ms=7)
    ax.plot(fin[:, 0], fin[:, 1], "-", color="tab:green", lw=1.4, label="finisher")
    ax.plot(*fin[-1, :2], "s", color="tab:green", ms=6)
    for i in range(lims.shape[1]):
        ax.plot(lims[:, i, 0], lims[:, i, 1], "-", color="tab:red", lw=0.8,
                alpha=0.7, label="limiter" if i == 0 else None)
        ax.plot(*lims[0, i, :2], ".", color="tab:red", ms=4)
        ax.plot(*lims[-1, i, :2], "x", color="tab:red", ms=5)
    if r.fire_step is not None and r.fire_step < len(tel):
        pf = tel[r.fire_step]["p_fin"]
        ax.plot(pf[0], pf[1], "*", color="gold", ms=16, mec="k", label="fire")
    ax.plot(tgt[0], tgt[1], "kx", ms=9, mew=2)
    ax.set_title(f"{title}\n{r.label}  steps={r.steps}  fire={r.fire_step}  "
                 f"contact={r.n_contact}", fontsize=8)
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax.tick_params(labelsize=7)


def _cache_p(row: int) -> pathlib.Path:
    return ART2 / "c_arm" / f"viz_cache_row{row}.json"


def run_pick(row: int) -> None:
    """한 판: pick → search 재현 → parity gate → telemetry 를 캐시에 저장.
    search 가 ~6분이라 판별 병렬 실행용으로 분리 (렌더는 --render 가 담당)."""
    cells, sls = _cells(), _slices()
    crecs, ab = _records()
    sl, chi_c, eta_c, why, kind = PICKS[row]
    s = _pick(crecs, ab, sl, chi_c, eta_c, kind)
    rec, ra = crecs[s], ab[(s, "A")]
    print(f"[viz] {why}: cell ({sl}, {chi_c}, {eta_c}) -> s={s} "
          f"(A={ra['label']}, C={rec['label']})", flush=True)
    meta, best_plan, best_score, _ = search_plan(s, cells, sls)
    kw = meta[5]
    rc, tel_c, st_c = _replay(s, best_plan, kw)
    assert (rc.label, rc.fire_step, rc.steps) == \
        (rec["label"], rec["fire_step"], rec["steps"]), \
        f"C replay-parity FAIL s={s}: {(rc.label, rc.fire_step, rc.steps)} " \
        f"!= {(rec['label'], rec['fire_step'], rec['steps'])}"
    ra_r, tel_a, st_a = _replay(s, ("policy", "hold"), kw)
    assert (ra_r.label, ra_r.fire_step, ra_r.steps) == \
        (ra["label"], ra["fire_step"], ra["steps"]), f"A parity FAIL s={s}"
    _cache_p(row).write_text(json.dumps({
        "row": row, "s": s, "why": why, "cell": [sl, chi_c, eta_c],
        "plan_kind": rec["plan_kind"], "target": list(map(float, st_c.lay.target)),
        "A": {"label": ra_r.label, "steps": ra_r.steps, "fire_step": ra_r.fire_step,
              "n_contact": ra_r.n_contact, "tel": tel_a},
        "C": {"label": rc.label, "steps": rc.steps, "fire_step": rc.fire_step,
              "n_contact": rc.n_contact, "tel": tel_c}}), encoding="utf-8")
    print(f"[viz] parity OK s={s} -> cached row {row}", flush=True)


def render() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    class _R:                                    # 캐시 → _panel 용 경량 어댑터
        def __init__(self, d):
            self.label, self.steps = d["label"], d["steps"]
            self.fire_step, self.n_contact = d["fire_step"], d["n_contact"]

    class _St:
        def __init__(self, target):
            self.lay = type("L", (), {"target": target})()

    fig, axes = plt.subplots(len(PICKS), 2, figsize=(11, 4.6 * len(PICKS)))
    for row in range(len(PICKS)):
        d = json.loads(_cache_p(row).read_text(encoding="utf-8"))
        sl, chi_c, eta_c = d["cell"]
        cell_txt = f"cell ({sl}, chi {chi_c}, eta {eta_c})  s={d['s']}  [{d['why']}]"
        st = _St(d["target"])
        _panel(axes[row, 0], _R(d["A"]), d["A"]["tel"], st, f"A hold — {cell_txt}")
        _panel(axes[row, 1], _R(d["C"]), d["C"]["tel"], st,
               f"C plan ({d['plan_kind']}) — {cell_txt}")
    axes[0, 0].legend(loc="best", fontsize=7, framealpha=0.85)
    fig.suptitle("R2b C-arm viz-first: A(hold) vs sealed-search C plan — "
                 "replay-parity gated", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", type=int, default=None, help="한 판만 search+cache")
    ap.add_argument("--render", action="store_true", help="캐시 3판 → PNG")
    a = ap.parse_args()
    if a.pick is not None:
        run_pick(a.pick)
    if a.render:
        render()


if __name__ == "__main__":
    main()
