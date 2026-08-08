"""docs/71 §1.1/§1.2 — IID paired 평가 러너 + primary 판정기의 계약 잠금.

여기서 지키는 것은 "코드가 돈다" 가 아니라 **과학적 계약**이다:
  P72a  world identity = (EVAL_WORLD_SEED=0, episode) 뿐 — arm·training seed 비의존
  P72b  regime = rollout 전에 결정 (pre-treatment) · controller 비의존
  P72c  대역은 선언된 둘 (headline 10000.., ablation 10300..) 만
  P72d  primary 는 confirmatory seeds (1..4) 만 쓰고 index seed 0 을 배제
  P72e  world_hash / regime 불일치는 조용히 넘어가지 않는다 (paired 무효 = 예외)

torch 불요 (scripted 팔 + 합성 행으로 검사한다).
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from shepherd.m4_env import build_m4_env, label_rates, regime_of
from shepherd.scripts import analyze_ls_commit as A
from shepherd.scripts import eval_iid as E


def test_p72a_world_identity_is_episode_only():
    """같은 episode -> 같은 world. 다른 episode -> 다른 world."""
    assert E.EVAL_WORLD_SEED == 0 and E.EVAL_LAYER == "iid"
    for ep in (10300, 10317, 10599):
        assert E.world_hash(ep) == E.world_hash(ep), "world_hash 가 불안정하다"
    hs = {E.world_hash(ep) for ep in range(10300, 10320)}
    assert len(hs) == 20, "서로 다른 episode 가 같은 world 해시를 냈다"
    # world 구성 인자에 policy training seed 가 들어갈 자리가 없어야 한다
    assert "seed" not in E.world_kw() and E.world_kw()["threat_layer"] == "iid"


def test_p72b_regime_is_pre_treatment_over_the_whole_band():
    """대역 전체에서 regime 은 world spec 만으로 정해지고 두 regime 이 다 있다."""
    ep0, n = E.BANDS["ablation"]
    counts = {}
    for ep in range(ep0, ep0 + n):
        st = build_m4_env(E.EVAL_WORLD_SEED, ep, **E.world_kw())
        reg = regime_of(st.threat["a_att"], st.threat["tau"], st.threat["net_radius"])
        assert reg in ("SHAPING_NEEDED", "FREE_CAPTURE")
        counts[reg] = counts.get(reg, 0) + 1
    assert counts.get("SHAPING_NEEDED", 0) >= 100, counts   # Δ_shape 의 표본 근거
    assert counts.get("FREE_CAPTURE", 0) >= 50, counts


def test_p72b2_regime_and_world_do_not_depend_on_the_controller():
    """★ 서로 다른 controller 로 같은 episode 를 굴려도 regime·world 가 같다.

    이게 Δ_shape 의 성립 근거다. 만약 regime 이 궤적에 의존했다면 두 팔의
    SHAPING 집합이 달라져 paired 비교 자체가 무효다.
    """
    eps = range(10300, 10302)
    hold, _ = E.eval_episodes(eps, arm="hold", log=None)
    arc, _ = E.eval_episodes(eps, arm="arc",
                             ep_kw=dict(E.SCRIPTED_ARMS["arc"]), log=None)
    assert [r["regime"] for r in hold] == [r["regime"] for r in arc]
    assert [r["world_hash"] for r in hold] == [r["world_hash"] for r in arc]
    assert [r["episode"] for r in hold] == list(eps)


def test_p72c_only_declared_bands_are_allowed():
    assert E._band_of(10_300, 300) == "ablation"
    assert E._band_of(10_000, 300) == "headline"
    for bad in ((10_301, 300), (10_300, 200), (12_000, 300)):
        with pytest.raises(SystemExit, match="선언되지 않은"):
            E._band_of(*bad)


# ── primary 판정기 (합성 행) ────────────────────────────────────────────────
def _rows(seed_effect: float, rng, ep0=10_300, n=300, live_base=0.05):
    """대역 전체를 덮는 합성 행 두 벌 (live, off). regime 은 실제 draw 를 쓴다."""
    live, off = [], []
    for ep in range(ep0, ep0 + n):
        st = build_m4_env(E.EVAL_WORLD_SEED, ep, **E.world_kw())
        reg = regime_of(st.threat["a_att"], st.threat["tau"], st.threat["net_radius"])
        wh = E.world_hash(ep, st)
        p_off = live_base + (seed_effect if reg == "SHAPING_NEEDED" else 0.0)
        live.append(dict(episode=ep, regime=reg, world_hash=wh,
                         label=("NET_CAPTURE" if rng.random() < live_base
                                else "PENETRATED")))
        off.append(dict(episode=ep, regime=reg, world_hash=wh,
                        label=("NET_CAPTURE" if rng.random() < p_off
                               else "PENETRATED")))
    return live, off


def _write(tmp_path, arm, seed, rows, band="ablation"):
    ep0, n = E.BANDS[band]
    (tmp_path / f"{arm}_seed{seed}.json").write_text(json.dumps(dict(
        arm=arm, band=band, training_seed=seed, episode_start=ep0,
        episode_end=ep0 + n - 1, rows=rows)), encoding="utf-8")


def _campaign(tmp_path, effect, seeds=(0, 1, 2, 3, 4)):
    rng = np.random.default_rng(11)
    for s in seeds:
        live, off = _rows(effect, rng)
        _write(tmp_path, "ls-live", s, live)
        _write(tmp_path, "ls-off", s, off)


def test_p72d_primary_uses_confirmatory_seeds_and_excludes_the_index_seed(tmp_path):
    assert A.CONFIRMATORY_SEEDS == (1, 2, 3, 4) and A.INDEX_SEED == 0
    _campaign(tmp_path, effect=0.30)
    out = A.analyze(str(tmp_path))
    pr = out["primary"]
    assert sorted(pr["delta_shape_per_seed"]) == [1, 2, 3, 4], \
        "index seed 가 primary 에 섞였다"
    assert out["index_seed"]["seed"] == 0 and "제외" in out["index_seed"]["status"]
    assert pr["positive_evidence"] and pr["ci95"][0] > 0.0
    assert pr["decision_statistic"].startswith("two-sided 95% CI")


def test_p72d2_null_effect_does_not_produce_positive_evidence(tmp_path):
    _campaign(tmp_path, effect=0.0)
    pr = A.analyze(str(tmp_path))["primary"]
    assert not pr["positive_evidence"], pr["ci95"]
    assert pr["ci95"][0] <= 0.0 <= pr["ci95"][1]
    assert "종료" in A.analyze(str(tmp_path))["verdict"]      # stop rule 문구


def test_p72e_broken_pairing_raises_instead_of_judging(tmp_path):
    """world_hash / regime 불일치 · 대역 불완전 = 판정 금지."""
    _campaign(tmp_path, effect=0.0, seeds=(1, 2, 3, 4))
    p = tmp_path / "ls-off_seed1.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["rows"][7]["world_hash"] = "deadbeefdeadbeef"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="world_hash"):
        A.analyze(str(tmp_path))

    d["rows"][7]["world_hash"] = json.loads(
        (tmp_path / "ls-live_seed1.json").read_text(encoding="utf-8")
    )["rows"][7]["world_hash"]
    d["rows"][7]["regime"] = "FREE_CAPTURE" if d["rows"][7]["regime"] == \
        "SHAPING_NEEDED" else "SHAPING_NEEDED"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="regime"):
        A.analyze(str(tmp_path))

    d["rows"] = d["rows"][:-1]                       # 샤드 하나 누락
    d["rows"][7]["regime"] = json.loads(
        (tmp_path / "ls-live_seed1.json").read_text(encoding="utf-8")
    )["rows"][7]["regime"]
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="대역 불완전"):
        A.analyze(str(tmp_path))


def test_p72f_missing_confirmatory_seed_blocks_the_verdict(tmp_path):
    _campaign(tmp_path, effect=0.2, seeds=(0, 1, 2))      # seed 3, 4 미완주
    with pytest.raises(SystemExit, match="confirmatory seed"):
        A.analyze(str(tmp_path))


def test_p72g_p_net_definition_is_shared_with_label_rates():
    """분석기의 p_net 정의가 `label_rates` 와 같은 라벨 집합이어야 한다."""
    counts = {"NET_CAPTURE": 3, "CAPTURE_WITH_CONTACT": 2, "HARD_KILL": 1,
              "PENETRATED": 4, "SPENT_FAIL": 0, "TRUNCATED": 0}
    assert label_rates(counts)["p_net"] == 5 / 10
    assert set(A.CAPTURE) == {"NET_CAPTURE", "CAPTURE_WITH_CONTACT"}


def test_p72h_non_final_ckpt_tag_cannot_enter_the_verdict(tmp_path):
    """`--ckpt-tag latest` 스모크 산출물이 판정에 섞이면 안 된다."""
    _campaign(tmp_path, effect=0.0, seeds=(1, 2, 3, 4))
    p = tmp_path / "ls-off_seed2.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["ckpt_tag"] = "latest"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="ckpt_tag"):
        A.analyze(str(tmp_path))
