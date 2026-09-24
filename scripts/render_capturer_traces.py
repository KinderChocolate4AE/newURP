"""Capturer trace JSON → 그림 (torch-free; viz-first 규율의 소비 단계).

`scripts/b0_v3_capturer_diagnostic.py`(서버)가 남긴 trace_*.json을 읽어 에피소드당
PNG 한 장을 만든다: (a) XY 평면 기하 — 공격자 궤적·limiter·finisher 자세축과 교사축,
(b) 교사축과의 각도 시계열 + cone 반각, (c) v_shot triple·FIRE 확률·발사/crossing 사건.

    python -m scripts.render_capturer_traces artifacts/marl/b0_v3_pilot/diagnostic/traces
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def render_trace(trace: dict, out_png: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    steps = trace["steps"]
    t = np.array([s["t"] for s in steps])
    p_att = np.array([s["p_att"] for s in steps])
    p_fin = np.array(steps[0]["p_fin"])
    lims = np.array([s["p_lims"] for s in steps])          # (T, 4, 3)
    e_fin = np.array([s["e_fin"] for s in steps])
    teach = np.array([s["teacher_axis"] for s in steps])
    ang_att = np.array([s.get("ang_att_teacher_deg", np.nan) for s in steps])
    ang_cmd = np.array([s.get("ang_cmd_teacher_deg", np.nan) for s in steps])
    ang_mu = np.array([s.get("ang_mean_teacher_deg", np.nan) for s in steps])
    v_soft = np.array([s["v_soft"] for s in steps])
    v_worst = np.array([s["v_worst"] for s in steps])
    p_feas = np.array([s["p_feasible"] for s in steps])
    fire_p = np.array([s.get("fire_prob", np.nan) for s in steps])
    crossings = [s["t"] for s in steps if s.get("clean_prev")]
    res = trace["result"]

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    mode = trace.get("mode", trace.get("arm", "trace"))
    fig.suptitle(f"{mode} | {trace['cell_id']} sid={trace['scenario_id']} "
                 f"| {res['bin']} ({res['outcome']}, {res['steps']} steps, "
                 f"fire@{res['fire_step']}, crossings={res['clean_crossings']})")

    ax = axes[0]
    ax.plot(p_att[:, 0], p_att[:, 1], "-", color="tab:red", lw=1.5,
            label="attacker")
    ax.scatter(*p_att[0, :2], color="tab:red", marker="o", s=30)
    for i in range(lims.shape[1]):
        ax.plot(lims[:, i, 0], lims[:, i, 1], "-", color="tab:blue",
                alpha=0.4, lw=0.8)
    ax.scatter(*p_fin[:2], color="k", marker="^", s=60, label="finisher")
    tg = trace.get("target", [0, 0, 0])
    ax.scatter(tg[0], tg[1], color="tab:green", marker="*", s=80, label="asset")
    for k in range(0, len(steps), max(1, len(steps) // 12)):
        ax.arrow(p_fin[0], p_fin[1], 3 * e_fin[k, 0], 3 * e_fin[k, 1],
                 color="0.5", alpha=0.4, head_width=0.15)
    ax.arrow(p_fin[0], p_fin[1], 4 * teach[-1, 0], 4 * teach[-1, 1],
             color="tab:orange", alpha=0.9, head_width=0.2)
    ax.set_aspect("equal"); ax.legend(fontsize=8)
    ax.set_title("XY (gray=attitude, orange=teacher axis)")

    ax = axes[1]
    ax.plot(t, ang_att, label="attitude vs teacher", color="k")
    if np.isfinite(ang_cmd).any():
        ax.plot(t, ang_cmd, label="sampled cmd vs teacher", color="tab:purple",
                alpha=0.6, lw=0.8)
    if np.isfinite(ang_mu).any():
        ax.plot(t, ang_mu, label="policy mean vs teacher", color="tab:blue",
                lw=1.2)
    half = trace.get("cone_half_angle_rad")
    if half:
        ax.axhline(np.degrees(half), color="tab:red", ls="--", lw=0.8,
                   label=f"cone half-angle {np.degrees(half):.1f}°")
    ax.set_ylim(0, 185); ax.set_xlabel("t"); ax.set_ylabel("deg")
    ax.legend(fontsize=8); ax.set_title("aim error vs teacher")

    ax = axes[2]
    ax.plot(t, v_soft, label="v_shot_soft", color="tab:blue")
    ax.plot(t, v_worst, label="v_shot_worst", color="tab:cyan", lw=0.8)
    ax.plot(t, p_feas, label="p_feasible", color="0.6", lw=0.8)
    if np.isfinite(fire_p).any():
        ax.plot(t, fire_p, label="P(fire)", color="tab:purple", lw=0.8)
    ax.axhline(trace.get("theta_fire", 0.9), color="tab:red", ls="--", lw=0.8,
               label="theta_fire")
    for c in crossings:
        ax.axvline(c, color="tab:green", alpha=0.25, lw=0.8)
    if res["fire_step"] is not None:
        ax.axvline(res["fire_step"], color="k", ls=":", lw=1.2, label="FIRE")
    ax.set_ylim(-0.05, 1.3); ax.set_xlabel("t"); ax.legend(fontsize=7)
    ax.set_title("gate/fire (green=clean crossing)")

    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+", type=Path,
                   help="trace_*.json 파일 또는 디렉터리")
    p.add_argument("--out-dir", type=Path, default=None)
    a = p.parse_args(argv)
    files: list[Path] = []
    for path in a.paths:
        files.extend(sorted(path.glob("trace_*.json")) if path.is_dir()
                     else [path])
    if not files:
        raise SystemExit("no trace files found")
    for f in files:
        trace = json.loads(f.read_text(encoding="utf-8"))
        out = (a.out_dir or f.parent) / (f.stem + ".png")
        out.parent.mkdir(parents=True, exist_ok=True)
        render_trace(trace, out)
        print(out)


if __name__ == "__main__":
    main()
