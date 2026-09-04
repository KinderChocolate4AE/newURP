"""R2a provenance spot-check — frozen curve 의 route_gain/sense_range 귀속 검증.

    python -m shepherd.scripts.r2a_provenance [--episodes 60] [--out artifacts/r2a/provenance_route_sense.json]

감사 브리프 (review_prompt_r2a_pins_evasion.txt) Q2 판정 이행. 1차 증거 =
`results/curve_hold_reactive.manifest.json` (생성 커밋 43acc39 동봉 sidecar:
route_gain 0.5 · sense_range 30.0 · run commit edf34d9). 본 스크립트는 그 lineage 의
**검증**이다 — exact replay 비교 순위 (감사 지시): 결정론(연속 metric 포함) >
per-episode metric divergence > terminal label. frozen 아티팩트는 라벨만 저장하므로
frozen-대조는 라벨·위협 draw bit-exact 까지, config 판별력은 후보 vs 대조 config 의
metric·라벨 분기로 세운다.

선택 에피소드 = 경계 밴드 (chi ∈ [0.45, 0.75]) 우선 — 라벨이 config 에 가장 민감한
구간. 원본 JSON 무수정 (sidecar 원칙). torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.curve_sweep import _default_kw                    # noqa: E402
from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.mission_rollout import run_episode                # noqa: E402
from shepherd.scripts.r2a_lattice import chi_eta                        # noqa: E402

FROZEN = "results/curve_hold_reactive.json"
CANDIDATE = {"route_gain": 0.5, "sense_range": 30.0}     # manifest 가 주장하는 config
CONTROL = {"route_gain": 0.0, "sense_range": float("inf")}  # legacy 비반응형 대안


def _replay(ep: int, cfg: dict) -> dict:
    """run_curve 의 내부 루프와 동일 경로 (build_m4_env + run_episode, hold/clean)."""
    kw = _default_kw(0.5, "A2", 0.6, cfg["route_gain"], cfg["sense_range"])
    st = build_m4_env(0, ep, **kw)
    r = run_episode(st.env, st.scn, st.lay, seed=0 + ep,
                    limiter_mode="hold", fire_mode="clean",
                    policy=None, baseline_commit=False)
    return {"label": r.label, "steps": r.steps,
            "min_target_dist": float(r.min_target_dist),
            "fire_step": r.fire_step, "clean_crossings": r.clean_crossings,
            "a_att": st.threat["a_att"], "att_speed": st.threat["att_speed"]}


def run(n_eps: int = 60, n_det: int = 10) -> dict:
    frozen = json.loads((ROOT / FROZEN).read_text(encoding="utf-8", errors="replace"))
    recs = frozen["records"]
    boundary = [r for r in recs
                if 0.45 <= chi_eta(r["a_att"], r["att_speed"], r["tau"], r["net_radius"])[0] <= 0.75]
    eps = [r["episode"] for r in boundary[:n_eps]]
    frozen_by_ep = {r["episode"]: r for r in recs}

    rows, det_ok = [], True
    for ep in eps:
        cand = _replay(ep, CANDIDATE)
        ctrl = _replay(ep, CONTROL)
        fz = frozen_by_ep[ep]
        rows.append({"episode": ep, "frozen_label": fz["label"],
                     "cand": cand, "ctrl": ctrl,
                     "draw_bitexact": cand["a_att"] == fz["a_att"] and cand["att_speed"] == fz["att_speed"]})
    for ep in eps[:n_det]:                                # 결정론: 동일 config 2회 완전 일치
        a, b = _replay(ep, CANDIDATE), _replay(ep, CANDIDATE)
        det_ok &= (a == b)

    cand_match = sum(r["cand"]["label"] == r["frozen_label"] for r in rows)
    ctrl_match = sum(r["ctrl"]["label"] == r["frozen_label"] for r in rows)
    label_disc = [r["episode"] for r in rows if r["cand"]["label"] != r["ctrl"]["label"]]
    metric_disc = [r["episode"] for r in rows
                   if abs(r["cand"]["min_target_dist"] - r["ctrl"]["min_target_dist"]) > 1e-9
                   or r["cand"]["steps"] != r["ctrl"]["steps"]]
    verdict = ("CONFIRMED" if cand_match == len(rows) and det_ok
               and len(metric_disc) > 0 and ctrl_match < len(rows)
               else "NOT_CONFIRMED")
    return {"sidecar_lineage": "results/curve_hold_reactive.manifest.json (commit 43acc39; run commit edf34d9)",
            "candidate": CANDIDATE, "control": {"route_gain": 0.0, "sense_range": "inf"},
            "n_episodes": len(rows), "selection": "first 60 boundary-band episodes (chi in [0.45, 0.75])",
            "deterministic_replay_ok": det_ok,
            "candidate_label_match": [cand_match, len(rows)],
            "control_label_match": [ctrl_match, len(rows)],
            "draw_bitexact_all": all(r["draw_bitexact"] for r in rows),
            "label_discriminating_eps": label_disc,
            "metric_discriminating_eps_n": len(metric_disc),
            "verdict": verdict,
            "verdict_rule": "CONFIRMED iff candidate 라벨 전수 일치 AND 결정론 재현 AND "
                            "config 간 metric 분기 존재 AND control 이 전수 일치는 아님",
            "rows": rows}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=60)
    ap.add_argument("--out", default="artifacts/r2a/provenance_route_sense.json")
    a = ap.parse_args(argv)
    res = run(a.episodes)
    p = ROOT / a.out
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"verdict {res['verdict']}  cand {res['candidate_label_match']} "
          f"ctrl {res['control_label_match']}  det {res['deterministic_replay_ok']} "
          f"draw_bitexact {res['draw_bitexact_all']}  label_disc {len(res['label_discriminating_eps'])} "
          f"metric_disc {res['metric_discriminating_eps_n']}")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
