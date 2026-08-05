"""P63: 발사 진단 하네스 (docs/48 §9 [1]).

이 진단의 결론은 *"관측에 판단 근거가 있다"* 이고, 그 근거는 관측 벡터의 특정
차원 하나다. 그러면 **그 차원의 위치가 곧 결론의 전제**가 된다 -- `env.py` 의
`_obs_vector` 배치가 바뀌면 인덱스가 조용히 엉뚱한 곳을 가리키고, 진단은
"근거가 없다" 로 뒤집힌다. 그래서 인덱스를 실측으로 못박는다.

양성 대조도 같이 건다. `control_vshot_auc` 가 1.0 이 아니면 그건 표현의 한계가
아니라 파이프라인이 틀린 것이다 (P52 에서 배운 것과 같은 이유).
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.scripts.fire_audit import (auc, collect_fire_dataset,
                                         obs_index_v_shot, probe)
from shepherd.scripts.mission_rollout import scripted_role_actions
from shepherd.spawn_rand import SpawnSpec

KW = dict(system=SystemSpec(enabled=True),
          reward=RewardSpec(w_kill=0.5, enabled=True),
          attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
          spawn=SpawnSpec())


def test_p63_auc_edges():
    assert auc(np.array([0., 1., 2., 3.]), np.array([0, 0, 1, 1])) == 1.0
    assert auc(np.array([3., 2., 1., 0.]), np.array([0, 0, 1, 1])) == 0.0
    # 전부 동점(= 확률 붕괴)에서 0.5 가 나와야 한다. 동점 보정이 없으면 임의값이다
    assert auc(np.array([0.5] * 6), np.array([0, 1, 0, 1, 1, 0])) == 0.5
    assert np.isnan(auc(np.array([1., 2.]), np.array([0, 0])))


def test_p63b_v_shot_index_points_at_the_real_channel():
    """★ 관측 인덱스가 env 가 보고하는 `v_shot_soft` 와 **같은 값**이어야 한다.

    이 진단의 결론 전체가 이 한 줄에 걸려 있다. `_obs_vector` 배치가 바뀌면
    인덱스가 조용히 엉뚱한 차원을 가리키고 결론이 뒤집힌다.

    **정렬 주의**: `env.step` 이 돌려주는 관측은 **이동 후** 상태이고,
    같은 호출의 `info["v_shot_soft"]` 는 **이동 전** 상태에서 계산된다
    (env.py 는 술어를 이동 전에 평가한다 -- mission_rollout 의 접촉 집계와
    같은 규약). 그래서 짝은 *스텝 직전의 관측* ↔ *그 스텝의 info* 다.
    수집기(`collect_fire_dataset`)도 정확히 그 짝으로 쌓는다.

    `v_shot` 은 몬테카를로(`n_samples=2000`)라 두 계열이 **비트 동일하지 않다**
    -- 같은 양의 다른 draw 다 (실측 평균 |차| 0.003, 최대 0.027). 그래서 상관과
    임계 일치로 본다. 느슨한 허용오차만 두면 잘못된 짝도 통과하므로, **음성
    대조**로 '이동 후 관측' 짝이 더 나쁘다는 것까지 확인한다.
    """
    pre, post, inf = [], [], []
    for ep in range(4):
        st = build_m4_env(0, ep, **KW)
        env, scn, lay = st.env, st.scn, st.lay
        idx = obs_index_v_shot(env)
        obs_d, _ = env.reset(seed=ep)
        fid = env.finisher_id
        for _ in range(int(lay.episode_len)):
            pre.append(float(np.asarray(obs_d[fid])[idx]))   # 스텝 **직전** 관측
            acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                         fire_mode="never")
            acts[env.adversary_id] = np.zeros(3, np.float32)
            obs_d, _, term, trunc, info = env.step(acts)
            inf.append(float(info[fid]["v_shot_soft"]))       # 그 스텝의 info
            post.append(float(np.asarray(obs_d[fid])[idx]))   # 이동 **후** 관측
            if (term and term.get(fid)) or (trunc and trunc.get(fid)):
                break
    pre, post, inf = np.array(pre), np.array(post), np.array(inf)
    assert len(pre) >= 40
    th = float(build_m4_env(0, 0, **KW).env.theta_fire)

    r_pre = float(np.corrcoef(pre, inf)[0, 1])
    r_post = float(np.corrcoef(post, inf)[0, 1])
    assert r_pre > 0.999, r_pre
    assert float(((pre >= th) == (inf >= th)).mean()) == 1.0
    # 음성 대조: 틀린 짝은 눈에 띄게 나빠야 한다 (아니면 이 검사는 공허하다)
    assert r_post < r_pre - 0.05, (r_pre, r_post)
    # 위협 관측 2 차원은 **뒤**에 붙는다 -- 인덱스가 그것에 밀리지 않는지
    off = build_m4_env(0, 0, threat_obs=False, **KW).env
    assert obs_index_v_shot(off) == idx


def test_p63c_probe_positive_control_and_threshold():
    """양성 대조 1.0 + 단일 임계가 라벨을 재현한다 (= 표현의 한계가 아니다)."""
    d = collect_fire_dataset(episodes=30, seed0=0)
    assert d["y"].sum() > 0, "교차가 한 번도 안 났다 -- episodes 를 늘릴 것"
    r = probe(d, train_frac=0.6)
    assert r["control_vshot_auc"] == pytest.approx(1.0, abs=1e-9)
    assert r["obs_vshot_dim_auc"] == pytest.approx(1.0, abs=1e-9)
    # 관측 차원 하나에 임계 하나로 라벨이 재현된다
    assert r["single_threshold"]["recall"] == pytest.approx(1.0, abs=1e-9)
    assert 0.0 < r["base_rate"] < 0.5


@pytest.mark.torch
def test_p63e_aim_audit_compares_like_with_like(tmp_path):
    """조준 진단의 두 팔은 **같은 궤적 길이**여야 한다.

    발사를 끈 상태에서 finisher 의 조준축은 동역학을 바꾸지 않는다 (자세만
    바뀌고 종료는 침투/절단으로 결정된다). 길이가 갈리면 두 팔이 다른 판을
    비교하고 있다는 뜻이라 게이트 개방률 비교가 성립하지 않는다.
    """
    torch = pytest.importorskip("torch")
    from shepherd.scripts.fire_audit import aim_audit
    from shepherd.train.mappo import MAPPOConfig, MAPPOTrainer

    st = build_m4_env(0, 0, **KW)
    obs_dim = st.env.observation_space(st.env.possible_agents[0]).shape[0]
    torch.manual_seed(0)
    tr = MAPPOTrainer(obs_dim, st.env.N,
                      MAPPOConfig.from_dict({"hidden_sizes": (16, 16),
                                             "limiter_commit": True,
                                             "device": "cpu"}))
    tr.save(tmp_path / "ckpt_mappo_final.pt")

    r = aim_audit(str(tmp_path), episodes=3, seed0=0)
    a, b = r["scripted_aim"], r["learned_aim"]
    assert a["n_steps"] == b["n_steps"] > 0        # 같은 판을 비교하는가
    assert 0.0 <= a["gate_open_rate"] <= 1.0
    assert set(r["delta"]) == {"gate_open_rate", "episodes_with_any_open",
                               "ep_max_mean"}
    assert r["theta_fire"] > 0


def test_p63d_collect_labels_match_the_env_predicate():
    """수집기의 라벨이 env 의 술어와 같다 (술어 복제 금지 -- info 를 그대로 쓴다)."""
    d = collect_fire_dataset(episodes=12, seed0=0)
    thr = d["X"][:, int(d["v_idx"])] >= d["theta_fire"]
    # clean = threshold_crossed AND NOT boxed_in  (env.py L290-291)
    assert np.array_equal(d["y"], thr & ~d["boxed_in"])
