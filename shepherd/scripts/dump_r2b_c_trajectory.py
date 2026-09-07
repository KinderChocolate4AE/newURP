"""R2b C-arm 궤적 덤프 → 기존 WarSim 뷰어 (viz/trajectory_viewer_r2b_c.html).

    python -m shepherd.scripts.dump_r2b_c_trajectory --pick K    # 판별 (병렬 가능)
    python -m shepherd.scripts.dump_r2b_c_trajectory --render    # 3판 병합 → HTML

r2b_c_viz.PICKS 와 동일 3판 (flip 2 + nosol 1). 각 판마다 A(hold)·C(재현 plan)
2 에피소드를 dump_trajectory.dump_episode (기존 뷰어 스키마 단일 정의원) 로
덤프한다 — builder = R2b scenario_kwargs, reset seed = 7000+s, plan =
search_plan 결정론 재현. parity gate: label(캡처 계열 매핑)·steps·fire_step 이
shard/phase1 기록과 일치해야 저장. group = 뷰어 그룹 = "s{...} A-hold" /
"s{...} C-plan (권위 라벨)". 뷰어 서빙 = viz/ 에서 http.server 8777. torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                                # noqa: E402
from shepherd.scripts.dump_trajectory import dump_episode               # noqa: E402
from shepherd.scripts.r2b_c_runner import SEED0, search_plan            # noqa: E402
from shepherd.scripts.r2b_c_viz import PICKS, _pick, _records           # noqa: E402
from shepherd.scripts.r2b_phase1 import _cells, _slices                 # noqa: E402

OUT_JSON = ROOT / "results" / "viz_r2b_c_pick{k}.json"
OUT_HTML = ROOT / "viz" / "trajectory_viewer_r2b_c.html"
TEMPLATE = ROOT / "viz" / "trajectory_viewer_template.html"


def _expect_driver_label(shard_label: str) -> str:
    """뷰어 덤프는 _Driver 라벨 (CAPTURED 는 접촉 미구분) — 권위 라벨을 매핑."""
    return ("CAPTURED" if shard_label in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
            else shard_label)


def run_pick(k: int) -> None:
    cells, sls = _cells(), _slices()
    crecs, ab = _records()
    sl, chi_c, eta_c, why, kind = PICKS[k]
    s = _pick(crecs, ab, sl, chi_c, eta_c, kind)
    rec, ra = crecs[s], ab[(s, "A")]
    print(f"[dump] {why}: s={s} (A={ra['label']}, C={rec['label']})", flush=True)
    meta, best_plan, _score, _n = search_plan(s, cells, sls)
    kw = meta[5]
    builder = lambda _ep: (lambda st: (st.env, st.scn, st.lay))(  # noqa: E731
        build_m4_env(SEED0, s, **kw))
    eps = []
    for arm, auth, mode, plan in (
            ("A", ra, "hold", None),
            ("C", rec, "hold",
             best_plan[1] if best_plan[0] == "accels" else None)):
        lm = mode if plan is not None or arm == "A" else best_plan[1]
        e = dump_episode(s, builder=builder, reset_ep=SEED0 + s,
                         limiter_mode=lm, plan=plan)
        assert e["label"] == _expect_driver_label(auth["label"]), \
            f"parity FAIL s={s} {arm}: {e['label']} vs {auth['label']}"
        assert len(e["steps"]) == auth["steps"] and e["fire_step"] == auth["fire_step"], \
            f"parity FAIL s={s} {arm}: steps/fire mismatch"
        e["group"] = (f"s{s} {why} — " +
                      ("A hold" if arm == "A" else f"C plan [{auth['label']}]"))
        eps.append(e)
        print(f"[dump] s={s} {arm}: {e['label']} steps={len(e['steps'])} "
              f"fire={e['fire_step']} — parity OK", flush=True)
    p = pathlib.Path(str(OUT_JSON).format(k=k))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"pick": k, "s": s, "episodes": eps},
                            ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


def render() -> None:
    episodes = []
    for k in range(len(PICKS)):
        d = json.loads(pathlib.Path(str(OUT_JSON).format(k=k))
                       .read_text(encoding="utf-8"))
        episodes += d["episodes"]
    data = {"note": "R2b C-arm replay (B0 v2 cba024d7ee3d9f61) · A hold vs "
                    "sealed-search C plan · replay-parity gated · "
                    "권위 라벨 = c_arm/phase1_v2 shard (group 에 표기)",
            "episodes": episodes}
    tpl = TEMPLATE.read_text(encoding="utf-8")
    OUT_HTML.write_text(tpl.replace("/*__DATA__*/null",
                                    json.dumps(data, ensure_ascii=False)),
                        encoding="utf-8")
    print(f"-> {OUT_HTML} ({len(episodes)} episodes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pick", type=int, default=None)
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    if a.pick is not None:
        run_pick(a.pick)
    if a.render:
        render()


if __name__ == "__main__":
    main()
