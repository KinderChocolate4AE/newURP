"""P1c standoff 궤적 뷰어 (읽기 전용 재생 — 봉인 결과·판정 불변).

P1c (manifest = artifacts/p1c_standoff/manifest.json) 평가 episode 를
(k, attacker, arm, cell, sid) 로 결정론 재생해 기존 trajectory viewer 템플릿으로
묶는다. 그룹 = `k{k}_{attacker}_{arm}`. 각 재생은 봉인 record 의 (steps, fire) 와
대조해 `replay` 블록으로 표기한다 (불일치 episode 는 참고용 — 수치 주장 금지).

    python -m scripts.viz_p1c_standoff
    python -m scripts.viz_p1c_standoff --scales 1 4 --rows 0 6 13
"""
from __future__ import annotations

import argparse
import json
import pathlib

from scripts.p1c_standoff import OUT, _build_scaled, _overrides
from scripts.p1c_standoff_manifest import ARMS, ATTACKERS, load as load_p1c_manifest
from scripts.viz_attacker_patterns import DEFAULT_ROWS, ROOT, TEMPLATE, _episode_plan

OUT_JSON = ROOT / "results" / "viz_p1c_standoff.json"
OUT_HTML = ROOT / "viz" / "p1c_standoff_viewer.html"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scales", type=int, nargs="*", default=[1, 2, 4])
    ap.add_argument("--rows", type=int, nargs="*", default=list(DEFAULT_ROWS))
    ap.add_argument("--sids-per-cell", type=int, default=1)
    a = ap.parse_args(argv)

    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    from shepherd.scripts.dump_trajectory import dump_episode

    manifest, b2 = load_p1c_manifest(), load_b2_manifest()
    ev = manifest["evaluation"]
    sealed_epc = int(ev["episodes_per_cell"])
    c5 = b2["arms"]["RULE_COOP"]["limiter_kw"]

    episodes, matched, total = [], 0, 0
    for k in a.scales:
        for att in ATTACKERS:
            ov = _overrides(att)
            for arm in ARMS:
                group = f"k{k}_{att['label']}_{arm}"
                sealed = {(r["cell_id"], r["scenario_id"]): r for r in json.loads(
                    (OUT / "arms" / f"{group}.json").read_text(encoding="utf-8"))["records"]}
                for cell, sid in _episode_plan(b2, tuple(a.rows), a.sids_per_cell,
                                               sealed_epc):
                    def build(_ep, cell=cell, sid=sid):
                        st = _build_scaled(ev, b2, cell, sid, ov, k)[2]
                        return st.env, st.scn, st.lay
                    e = dump_episode(sid, builder=build, reset_ep=int(ev["seed0"]) + sid,
                                     limiter_mode=("hold" if arm == "hold" else "arc"),
                                     limiter_kw=(None if arm == "hold" else c5))
                    rec = sealed.get((cell["cell_id"], sid))
                    ok = (rec is not None and len(e["steps"]) == rec["steps"]
                          and (e["fire_step"] is not None) == rec["fire"])
                    e["group"] = group
                    e["replay"] = {"k": k, "attacker": att["label"], "arm": arm,
                                   "cell_id": cell["cell_id"], "row": int(cell["row"]),
                                   "scenario_id": sid,
                                   "sealed_bin": None if rec is None else rec["bin"],
                                   "sealed_steps": None if rec is None else rec["steps"],
                                   "dump_label": e["label"], "match": ok}
                    total += 1
                    matched += int(ok)
                    episodes.append(e)
                print(f"{group}: 누적 재생일치 {matched}/{total}", flush=True)

    data = dict(note=(f"P1c standoff replay · manifest {manifest['manifest_hash']}"
                      f" · 재생일치(steps·fire) {matched}/{total} · 읽기 전용"),
                episodes=episodes)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    OUT_HTML.write_text(TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__DATA__*/null", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print(f"재생일치 {matched}/{total}\n-> {OUT_JSON}\n-> {OUT_HTML}")
    if matched != total:
        print("경고: 재생 불일치 episode 존재 — 뷰어는 참고용, 수치 인용 금지")


if __name__ == "__main__":
    main()
