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


def _fake_eval(tmp, defended, v2=None):
    """defended[(defender, group)] → 판독 입력 디렉터리 (나머지 셀 0). v2 = {defender: 공칭 사다리
    defended} 이면 v2 addendum 판정을 돌려준다."""
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
    v1 = M.readout(tmp)
    if v2 is None:
        return v1["decision"]
    (tmp / "eval_v2").mkdir()
    rows = [{"defender": d, "group": "ladder", "n": M.N, "defended": v2.get(d, 0)} for d in M.DEFENDERS]
    meta = {"manifest": M.load_v2()["manifest_hash"], "ladder": "nominal"}
    (tmp / "eval_v2" / "summary.json").write_text(json.dumps({"meta": meta, "rows": rows}))
    (tmp / "eval_v2" / "episodes.jsonl").write_text("\n".join(
        json.dumps({"defender": d, "group": "ladder", "seed": s}) for d in M.DEFENDERS for s in range(3)))
    return M.readout_v2(tmp, v1)["decision"]


def test_v2_ladder_governs_narrow(tmp_path):
    pos = {("learned_det", "pool"): 124, ("kfirst50", "pool"): 100,
           ("learned_det", "ex_learned"): 124, ("kfirst50", "ex_kfirst50"): 100}
    # v1 사다리 (legacy) 는 동률 → POSITIVE, v2 공칭 사다리에서 −24 → NARROW
    assert _fake_eval(tmp_path, pos, v2={"kfirst50": 24}) == "FS1_POSITIVE_NARROW"


@pytest.mark.parametrize("ds, want", [
    (["FS1_POSITIVE", "FS1_NULL", "FS1_POSITIVE_NARROW"], "FS1_CONFIRMED"),
    (["FS1_POSITIVE_NARROW", "FS1_POSITIVE_NARROW", "FS1_POSITIVE"], "FS1_CONFIRMED_NARROW"),
    (["FS1_POSITIVE", "FS1_NULL", "INVALID_FS1E"], "FS1_NOT_CONFIRMED"),
])
def test_r4_confirmation(ds, want):
    import sys
    sys.path.insert(0, "scripts")
    import fs1_eval_manifest as M
    assert M.confirm(ds) == want


def test_r4p_stack_pieces():
    import numpy as np
    from shepherd.fs1.train import def_shaping, pfsp_w, LAMBDA_DIST
    from shepherd.fs1.world import FS1Env, FS1Spec
    # 시간 채널: 기본 65-D bit-exact, r4p 는 66-D 이고 마지막 채널 = t/episode_len
    e = FS1Env(FS1Spec(obs_time=True), seed=0)
    obs, _ = e.reset(seed=7)
    assert len(obs["finisher_0"]) == 66 and obs["finisher_0"][-1] == 0.0
    acts = {l: np.zeros(4) for l in e.limiter_ids}
    acts["finisher_0"] = np.zeros(5); acts["adversary_0"] = np.zeros(3)
    obs, _, _, _ = e.step(acts)
    assert abs(obs["finisher_0"][-1] - 1 / 800) < 1e-9
    assert len(FS1Env(FS1Spec(), seed=0).reset(seed=7)[0]["finisher_0"]) == 65
    # potential shaping: 할인 합 = −Φ(s0) (PBRS 성질), raw 경로는 기존과 동일
    g, dists = 0.997, [200.0, 150.0, 90.0, 30.0]
    prev = -LAMBDA_DIST / (1 - g) * dists[0]
    phi0, disc, acc = prev, 1.0, 0.0
    for t, d in enumerate(dists[1:], 1):
        dr, prev = def_shaping(d, prev, g, t == len(dists) - 1, True)
        acc += disc * dr; disc *= g
    assert abs(acc - (-phi0)) < 1e-12
    assert def_shaping(123.0, 0.0, g, False, False)[0] == -LAMBDA_DIST * 123.0
    # f_var: 붕괴 구간 (x≈0.055) 에서 전패 상대 가중이 낮아야 함
    assert pfsp_w(0.055) > 0.8 and pfsp_w(0.055, fvar=True) < 0.06
    assert abs(pfsp_w(0.5, fvar=True) - 0.251) < 1e-9


def test_e3b_mixture_defenders():
    import numpy as np
    from shepherd.fs1.eval import _ep_kf_r
    from shepherd.fs1.train import KFIRST_R
    assert _ep_kf_r("mix5050", 2) == KFIRST_R and _ep_kf_r("mix5050", 3) is None   # 짝홀 50/50
    np.random.seed(7)
    rs = {_ep_kf_r("kfirst_rand", 7) for _ in range(8)}
    assert all(30.0 <= r <= 70.0 for r in rs) and len(rs) > 1
    # paired 평가: mix5050 짝수 seed = kfirst 무장 (~50 m), 홀수 seed = fallback (늦은 무장)
    _W["env"] = FS1Env(seed=0)
    opp = dict(ladder_pool()[0], group="ladder")
    recs = {r["seed"]: r for _, _, r in ev.episodes(("mix5050", None, opp, [2, 3], 0))}
    assert recs[2]["arm_d"] is not None and recs[2]["arm_d"] > 25
    assert recs[3]["arm_d"] is None or recs[3]["arm_d"] < 10


def test_e3_band_selection_and_mu_nu():
    import sys
    sys.path.insert(0, "scripts")
    import fs1_e3_manifest as E
    assert E.select_cells({"a": 47, "b": 48, "c": 216, "d": 217, "e": 3}) == ["b", "c"]
    from shepherd.fs1.world import FS1Env, FS1Spec
    e = FS1Env(FS1Spec(mu=0.7), seed=0)
    assert abs(e.inner.backend.by_name(e.limiter_ids[0]).limits.a_max / 7.1587 - 2.0) < 1e-3
    assert abs(e.att_a_max - 20.453) < 1e-2          # 공격자 불변


def test_k_viab_adds_fire_tick_bonus_only():
    import numpy as np
    from shepherd.fs1.world import FS1Env, FS1Spec
    # 같은 seed 로 arm A(0) vs arm B(0.2): 보상 차이는 발사 tick 의 0.2·v_shot_soft 하나뿐
    def run(k):
        e = FS1Env(FS1Spec(k_viab=k), seed=0)
        obs, _ = e.reset(seed=205)
        tot, vfire, done = 0.0, None, False
        while not done:
            acts = {l: np.zeros(4) for l in e.limiter_ids}
            acts["finisher_0"] = np.r_[0, 0, 0, 12.0, 1.0]
            acts["adversary_0"] = np.zeros(3)
            obs, r, done, info = e.step(acts)
            tot += r["finisher_0"]
            if info["finisher_0"].get("fire_event"):
                vfire = float(info["finisher_0"]["v_shot_soft"])
        return tot, vfire
    a, va = run(0.0)
    b, vb = run(0.2)
    assert va is not None and va == vb                 # 행동 불변 (보상만 다름)
    assert abs((b - a) - 0.2 * va) < 1e-9


def test_ladder_nominal_restores_p1a_spec():
    from shepherd.fs1.train import ladder_attacker
    S = {p["name"]: ladder_attacker(p["ov"]).spec for p in ladder_pool()}
    L = {p["name"]: ladder_attacker(p["ov"], True).spec for p in ladder_pool(legacy=True)}
    assert S["t1f_r05_s30_ref"].jink_amp == 0.6 and L["t1f_r05_s30_ref"].jink_amp == 0.0
    assert S["t0_route0"] != S["a1_pure"] and L["t0_route0"] == L["a1_pure"]
    assert S["t0_route0"].sense_range == float("inf") and S["t1f_r02_s15_ref"].sense_range == 15.0


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
