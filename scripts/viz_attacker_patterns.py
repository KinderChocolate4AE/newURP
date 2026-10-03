"""P1a 공격자 패턴 궤적 뷰어 (읽기 전용 재생 — 봉인 결과·판정 불변).

P1a (manifest `4629158d387c938b`) 평가 episode 를 (config, cell, sid) 로 결정론
재생해 기존 trajectory viewer 템플릿으로 묶는다. 뷰어의 그룹 = config label 이라
route_gain / sense_range / jink / λ / bait 성향별 공격자 궤적을 나란히 평가할 수
있다. 각 재생은 봉인 record 의 outcome 과 대조해 `replay` 블록으로 표기한다
(불일치 episode 는 참고용 플래그 — 수치 주장에 쓰지 않는다).

    python -m scripts.viz_attacker_patterns                        # 전 config
    python -m scripts.viz_attacker_patterns --configs t1f_r05_s30_ref a1_pure
    python -m scripts.viz_attacker_patterns --rows 0 6 13 --sids-per-cell 1
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import pathlib

from scripts.p1_ladder import _overrides
from scripts.p1_ladder_manifest import load as load_p1_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
P1_CONFIG_DIR = ROOT / "artifacts" / "p1_ladder" / "configs"
OUT_JSON = ROOT / "results" / "viz_attacker_patterns.json"
OUT_HTML = ROOT / "viz" / "attacker_patterns_viewer.html"
TEMPLATE = ROOT / "viz" / "trajectory_viewer_template.html"
DEFAULT_ROWS = (0, 6, 13)              # 경계 高·中·低 χ 행 (P1a 지도 기준)


def _episode_plan(b2: dict, rows: tuple, sids_per_cell: int, sealed_epc: int):
    from shepherd.scripts.b0_v3_mappo_pilot import boundary_cells
    cells = boundary_cells(b2)
    for ci, cell in enumerate(cells):
        if int(cell["row"]) not in rows:
            continue
        for j in range(sids_per_cell):
            yield cell, ci * sealed_epc + j


def _builder(b2: dict, ev: dict, cell: dict, sid: int, overrides: dict):
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b0_v3_mappo_pilot import scenario_kwargs

    def build(_ep: int):
        chi, eta, kw = scenario_kwargs(b2, cell, sid, seed0=ev["seed0"],
                                       seed_ns=ev["namespace"])
        kw = dict(kw)
        kw["attacker"] = replace(kw["attacker"], **overrides)
        st = build_m4_env(ev["seed0"], sid, **kw)
        return st.env, st.scn, st.lay

    return build


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--configs", nargs="*", default=None,
                    help="P1a config label 부분집합 (기본 = 전 24종)")
    ap.add_argument("--rows", type=int, nargs="*", default=list(DEFAULT_ROWS))
    ap.add_argument("--sids-per-cell", type=int, default=1)
    ap.add_argument("--out-html", default=str(OUT_HTML))
    ap.add_argument("--out-json", default=str(OUT_JSON))
    a = ap.parse_args(argv)

    from shepherd.scripts.b2_manifest import load as load_b2_manifest
    from shepherd.scripts.dump_trajectory import dump_episode

    manifest, b2 = load_p1_manifest(), load_b2_manifest()
    ev = manifest["evaluation"]
    sealed_epc = int(ev["episodes_per_cell"])
    configs = [c for c in manifest["attacker"]["configs"]
               if a.configs is None or c["label"] in a.configs]
    if a.configs and len(configs) != len(a.configs):
        raise SystemExit(f"unknown config label in {a.configs}")

    episodes, matched, total = [], 0, 0
    for config in configs:
        label = config["label"]
        sealed = {(r["cell_id"], r["scenario_id"]): r
                  for r in json.loads((P1_CONFIG_DIR / f"{label}.json").read_text(
                      encoding="utf-8"))["records"]}
        overrides = _overrides(config)
        for cell, sid in _episode_plan(b2, tuple(a.rows), a.sids_per_cell,
                                       sealed_epc):
            e = dump_episode(
                sid, builder=_builder(b2, ev, cell, sid, overrides),
                reset_ep=int(ev["seed0"]) + sid, limiter_mode="hold")
            rec = sealed.get((cell["cell_id"], sid))
            e["group"] = label
            e["replay"] = {
                "config": label, "cell_id": cell["cell_id"],
                "row": int(cell["row"]), "chi_role": cell["chi_role"],
                "scenario_id": sid,
                "sealed_outcome": None if rec is None else rec["outcome"],
                "sealed_bin": None if rec is None else rec["bin"],
                "dump_label": e["label"],
                "match": rec is not None and e["label"] == rec["outcome"],
            }
            total += 1
            matched += int(e["replay"]["match"])
            episodes.append(e)
        print(f"{label}: {sum(1 for x in episodes if x['group'] == label)} ep "
              f"(누적 재생일치 {matched}/{total})", flush=True)

    data = dict(
        note=(f"P1a attacker-pattern replay · manifest {manifest['manifest_hash']}"
              f" · hold limiter + scripted launcher · 재생일치 {matched}/{total}"
              " · 읽기 전용 (봉인 판정 불변)"),
        episodes=episodes)
    out_json, out_html = pathlib.Path(a.out_json), pathlib.Path(a.out_html)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tpl = TEMPLATE.read_text(encoding="utf-8")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(tpl.replace("/*__DATA__*/null",
                                    json.dumps(data, ensure_ascii=False)),
                        encoding="utf-8")
    print(f"재생일치 {matched}/{total}\n-> {out_json}\n-> {out_html}")
    if matched != total:
        print("경고: 재생 불일치 episode 존재 — 뷰어는 참고용, 수치 인용 금지")


if __name__ == "__main__":
    main()
