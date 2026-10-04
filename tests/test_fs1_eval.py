"""shepherd.fs1.eval: scripted 기준선 매핑과 paired 시드."""
import pytest

pytest.importorskip("torch")

from shepherd.fs1 import eval as ev
from shepherd.fs1.train import _W, ladder_pool
from shepherd.fs1.world import FS1Env


def test_fin12_never_arms_and_seeds_are_paired():
    _W["env"] = FS1Env(seed=0)
    opp = dict(ladder_pool()[0], group="ladder")
    run = lambda d: [r for _, _, r in ev.episodes((d, None, opp, [3, 4], 0))]
    fin12, kf = run("fin12"), run("kfirst50")
    assert all(r["arm_d"] is None for r in fin12)            # fallback 없음 = limiter 영구 비무장
    assert all(r["arm_d"] is not None and r["arm_d"] <= ev.KFIRST_R + 2 for r in kf)
    assert [r["seed"] for r in fin12] == [r["seed"] for r in kf] == [3, 4]


def _fake_eval(tmp, defended):
    """defended[(defender, group)] → 판독 입력 디렉터리 (나머지 셀 0)."""
    import json
    import sys
    sys.path.insert(0, "scripts")
    import fs1_eval_manifest as M
    (tmp / "eval").mkdir()
    rows = [{"defender": d, "group": g, "n": M.N, "defended": defended.get((d, g), 0), "k_first": 0}
            for d in M.DEFENDERS for g in M.GROUPS]
    meta = {"manifest": M.load()["manifest_hash"], "ckpt_total_steps": 1.1e8}
    (tmp / "eval" / "summary.json").write_text(json.dumps({"meta": meta, "rows": rows}))
    (tmp / "eval" / "episodes.jsonl").write_text("\n".join(
        json.dumps({"defender": d, "group": g, "seed": s}) for d in M.DEFENDERS for g in M.GROUPS
        for s in range(3)))
    for x in ("learned", "kfirst50"):
        (tmp / f"exploit_{x}").mkdir()
        (tmp / f"exploit_{x}" / "log.jsonl").write_text(json.dumps({"total_steps": 1e7}))
    return M.readout(tmp)["decision"]


@pytest.mark.parametrize("cells, want", [
    ({("learned_det", "pool"): 124, ("kfirst50", "pool"): 100,
      ("learned_det", "ex_learned"): 124, ("kfirst50", "ex_kfirst50"): 100}, "FS1_POSITIVE"),
    ({("learned_det", "pool"): 124, ("kfirst50", "pool"): 100,
      ("learned_det", "ex_learned"): 124, ("kfirst50", "ex_kfirst50"): 100,
      ("fin12_fb", "ladder"): 24}, "FS1_POSITIVE_NARROW"),
    ({("learned_det", "pool"): 123, ("fin12", "pool"): 100,
      ("learned_det", "ex_learned"): 200}, "FS1_NULL"),
])
def test_readout_gate(tmp_path, cells, want):
    assert _fake_eval(tmp_path, cells) == want
