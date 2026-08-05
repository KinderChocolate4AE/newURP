"""P50–P58: 역할 분리 배선 (docs/48).

이 파일이 지키는 것은 하나다: **역할을 동결한 팔이 기준선과 같은 규칙을 쓰고,
동결된 역할은 학습되지 않는다.** 두 성질 중 하나라도 깨지면 2x2 의 차이가
"학습의 기여"가 아니라 "구현의 차이"가 되어 실험 전체가 무의미해진다.

docs/47 §7.4 가 적은 대로 이 리포에서 반복된 사고는 전부 *"같은 규칙이 두 곳에
있고 소비자 한쪽이 안 따라왔다"* 였다 (정정 3 · 정정 8 · 결함 1 · 결함 2).
그래서 이번에는 문서가 아니라 테스트로 못을 박는다.
"""
from __future__ import annotations

import json
import subprocess

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.spawn_rand import SpawnSpec
from shepherd.scripts.mission_rollout import (ROLES, run_episode,
                                              scripted_role_actions)
from shepherd.scripts.roles_split import ARM_SPECS, aggregate
from shepherd.train.action_dims import (LIVE_DIMS, M4_LIVE_DIMS,
                                        pad_env_action, unpad_env_action)

KW = dict(system=SystemSpec(enabled=True),
          reward=RewardSpec(w_kill=0.5, enabled=True),
          attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
          spawn=SpawnSpec())

_RESULT_FIELDS = ("label", "outcome", "steps", "n_contact", "contact_ids",
                  "contact_steps", "env_limiter_loss_sum", "fire_step",
                  "wasted_fire", "min_target_dist", "clean_crossings")


def _stack(ep: int = 0):
    return build_m4_env(0, ep, **KW)


class _Recorder:
    """env.step 이 **실제로** 받은 행동을 기록한다 (술어 복제 금지 원칙의 연장:
    '정책이 무엇을 냈는가' 가 아니라 'env 가 무엇을 받았는가' 를 본다)."""

    def __init__(self, env):
        self.env, self.seen = env, []
        self._step = env.step

    def install(self):
        def step(actions):
            self.seen.append({k: np.asarray(v, float).copy()
                              for k, v in actions.items()})
            return self._step(actions)
        self.env.step = step
        return self


# ── P50: 패딩 왕복 규약 ────────────────────────────────────────────────────
def test_p50_unpad_is_left_inverse_of_pad():
    """`unpad(pad(a)) == a` 는 항상. `pad(unpad(x)) == x` 는 RESERVED 가 0 일 때만."""
    for dims in (LIVE_DIMS, M4_LIVE_DIMS):
        for aid in ("limiter_0", "finisher_0"):
            env_dim, live_idx = dims[aid.rsplit("_", 1)[0]]
            a = np.arange(1, len(live_idx) + 1, dtype=np.float32)
            assert np.array_equal(unpad_env_action(aid, pad_env_action(aid, a, dims),
                                                   dims), a)
            # RESERVED 에 값이 실린 env 행동은 왕복에서 그 값을 **잃는다**.
            x = np.arange(1, env_dim + 1, dtype=np.float32)
            back = pad_env_action(aid, unpad_env_action(aid, x, dims), dims)
            reserved = [i for i in range(env_dim) if i not in live_idx]
            assert np.array_equal(back[list(live_idx)], x[list(live_idx)])
            assert all(back[i] == 0.0 for i in reserved)


def test_p50b_unpad_rejects_wrong_width():
    with pytest.raises(ValueError):
        unpad_env_action("finisher_0", np.zeros(4, np.float32))   # env Box 는 5


# ── P51: 스크립트 역할 행동은 env Box 규약을 지킨다 ────────────────────────
def test_p51_scripted_role_actions_shapes_and_subset():
    st = _stack()
    st.env.reset(seed=0)
    both = scripted_role_actions(st.env, st.scn, st.lay)
    assert set(both) == set(st.env.limiter_ids) | {st.env.finisher_id}
    for lid in st.env.limiter_ids:
        assert both[lid].shape == (4,)
    assert both[st.env.finisher_id].shape == (5,)

    only_fin = scripted_role_actions(st.env, st.scn, st.lay, roles=("finisher",))
    assert set(only_fin) == {st.env.finisher_id}
    only_lim = scripted_role_actions(st.env, st.scn, st.lay, roles=("limiter",))
    assert set(only_lim) == set(st.env.limiter_ids)
    # 부분 호출이 전체 호출과 **같은 값**을 낸다 (역할별로 독립이어야 한다)
    for lid in st.env.limiter_ids:
        assert np.array_equal(only_lim[lid], both[lid])
    assert np.array_equal(only_fin[st.env.finisher_id], both[st.env.finisher_id])


def test_p51b_hold_limiter_is_all_zero_including_commit():
    """`hold` 는 가속 0 **이고 커밋 0** 이다 -- 동결 팔이 공짜 하드킬을 얻으면 안 된다."""
    st = _stack()
    st.env.reset(seed=0)
    acts = scripted_role_actions(st.env, st.scn, st.lay, roles=("limiter",),
                                 limiter_mode="hold")
    for lid in st.env.limiter_ids:
        assert np.allclose(acts[lid], 0.0), lid


# ── P52: ★ 핵심 — 두 역할 동결 == 손튜닝 기준선 ────────────────────────────
def _garbage_policy(env):
    """정책 자리에 **틀린 값**을 넣는다. 동결이 진짜면 결과가 안 변해야 한다."""
    rng = np.random.default_rng(1234)

    def policy(obs, flags):
        acts = {lid: rng.normal(size=4).astype(np.float32) * 50.0
                for lid in env.limiter_ids}
        acts[env.finisher_id] = rng.normal(size=5).astype(np.float32) * 50.0
        return acts
    return policy


# ep 1/2/4/10 은 실제로 **발사가 일어나는** 판이다. 여기서만 이 테스트에 힘이 있다
# -- hold 로 침투당하기만 하는 판은 정책이 무엇을 내든 결과가 같아서 동치 주장이
# 공허해진다(실측: ep 0/3/7 은 쓰레기 정책을 그대로 넣어도 결과가 안 변한다).
_BITE_EPISODES = [1, 2, 4, 10]


@pytest.mark.parametrize("ep", _BITE_EPISODES)
def test_p52_full_freeze_equals_scripted_baseline(ep):
    """`policy` 가 무엇을 내든 두 역할을 동결하면 기준선 경로와 **결과가 같다**.

    이것이 성립해야 LS-SS · SL-SS 차이를 학습의 기여로 읽을 수 있다.

    ★ 동시에 **음성 대조**를 건다: 같은 쓰레기 정책을 동결 없이 넣으면 결과가
    달라져야 한다. 이게 없으면 "동결이 먹혔다"와 "이 판은 무엇을 해도 똑같다"가
    구분되지 않아 테스트가 조용히 공허해진다.
    """
    a = _stack(ep)
    ra = run_episode(a.env, a.scn, a.lay, seed=100 + ep,
                     limiter_mode="hold", fire_mode="clean")

    b = _stack(ep)
    rb = run_episode(b.env, b.scn, b.lay, seed=100 + ep,
                     limiter_mode="hold", fire_mode="clean",
                     policy=_garbage_policy(b.env), scripted_roles=ROLES)
    for f in _RESULT_FIELDS:
        assert getattr(ra, f) == getattr(rb, f), f

    c = _stack(ep)                                   # 음성 대조: 동결 없음
    rc = run_episode(c.env, c.scn, c.lay, seed=100 + ep,
                     limiter_mode="hold", fire_mode="clean",
                     policy=_garbage_policy(c.env))
    assert any(getattr(ra, f) != getattr(rc, f) for f in _RESULT_FIELDS), (
        f"ep {ep}: 동결 없이도 결과가 같다 -- 이 판에는 분해능이 없다")


def test_p52b_partial_freeze_lets_the_live_role_through():
    """finisher 만 동결하면 limiter 는 정책 값이 **그대로** env 에 닿아야 한다.

    (동결이 과잉 적용돼 전부 스크립트가 되면 P52 는 통과하지만 실험은 죽는다.)
    """
    st = _stack()
    rec = _Recorder(st.env).install()
    run_episode(st.env, st.scn, st.lay, seed=0, limiter_mode="hold",
                fire_mode="clean", policy=_garbage_policy(st.env),
                scripted_roles=("finisher",), max_steps=5)
    lid = st.env.limiter_ids[0]
    seen = np.stack([s[lid] for s in rec.seen])
    assert not np.allclose(seen, 0.0)          # limiter 는 정책 값 (hold 가 아니다)
    fin = np.stack([s[st.env.finisher_id] for s in rec.seen])
    assert np.allclose(np.linalg.norm(fin[:, :3], axis=1), 1.0, atol=1e-5)  # 단위 조준축
    assert set(np.unique(fin[:, 4])) <= {0.0, 1.0}                          # 발사 비트


def test_p53_frozen_limiter_reaches_env_as_zero():
    """동결된 limiter 가 **env 에 닿는 값**이 0 이다 (제안이 아니라 도착 기준)."""
    st = _stack()
    rec = _Recorder(st.env).install()
    run_episode(st.env, st.scn, st.lay, seed=0, limiter_mode="hold",
                fire_mode="clean", policy=_garbage_policy(st.env),
                scripted_roles=("limiter",), max_steps=5)
    for s in rec.seen:
        for lid in st.env.limiter_ids:
            assert np.allclose(s[lid], 0.0)


def test_p53b_default_path_is_untouched():
    """`scripted_roles=()` 는 기존 정책 경로와 bit-identical 이어야 한다."""
    st = _stack()
    rec = _Recorder(st.env).install()
    run_episode(st.env, st.scn, st.lay, seed=0, policy=_garbage_policy(st.env),
                max_steps=4)
    st2 = _stack()
    rec2 = _Recorder(st2.env).install()
    run_episode(st2.env, st2.scn, st2.lay, seed=0,
                policy=_garbage_policy(st2.env), scripted_roles=(), max_steps=4)
    assert len(rec.seen) == len(rec2.seen)
    for s1, s2 in zip(rec.seen, rec2.seen):
        for k in s1:
            assert np.array_equal(s1[k], s2[k]), k


# ── torch 구간: 동결 역할의 액터가 학습되지 않는다 ─────────────────────────
torch = pytest.importorskip("torch")

from shepherd.train.mappo import MAPPOConfig, MAPPORollout, MAPPOTrainer  # noqa: E402
from shepherd.scripts.train_mappo import MAPPORunner                      # noqa: E402
from shepherd.scripts.train_m4 import ARMS, arm_of                        # noqa: E402

OBS, N = 12, 3


def _cfg(**kw):
    base = dict(hidden_sizes=(16, 16), epochs=2, minibatch_size=8,
                rollout_steps=16, seed=0, device="cpu")
    base.update(kw)
    return MAPPOConfig.from_dict(base)


def _fill(trainer, size=16):
    rng = np.random.default_rng(0)
    buf = MAPPORollout(size, trainer.obs_dim, trainer.n, lim_dim=trainer.lim_dim)
    for _ in range(size):
        obs = rng.normal(size=trainer.obs_dim).astype(np.float32)
        x_l = np.concatenate([np.tile(obs, (trainer.n, 1)),
                              np.eye(trainer.n, dtype=np.float32)], axis=1)
        raw_l, logp_l = trainer.lim_actor.act(torch.as_tensor(x_l))
        raw_f, logp_f = trainer.fin_actor.act(torch.as_tensor(obs[None, :]))
        raw_l, raw_f = raw_l.numpy(), raw_f[0].numpy()
        clip_l = raw_l.copy(); clip_l[:, :3] = np.clip(clip_l[:, :3], -1, 1)
        clip_f = raw_f.copy(); clip_f[:3] = np.clip(clip_f[:3], -1, 1)
        buf.add(obs=obs, lim_raw=raw_l, lim_clip=clip_l,
                lim_logp=logp_l.numpy(), fin_raw=raw_f, fin_clip=clip_f,
                fin_logp=float(logp_f[0].item()),
                rewards=float(rng.normal()), values=float(rng.normal()),
                next_values=float(rng.normal()), dones=float(rng.integers(0, 2)))
    return buf


def _snapshot(mod):
    return [p.detach().clone() for p in mod.parameters()]


def _changed(mod, before) -> bool:
    return any(not torch.equal(a, b) for a, b in zip(_snapshot(mod), before))


@pytest.mark.torch
@pytest.mark.parametrize("frz", ["limiter", "finisher"])
def test_p54_frozen_actor_does_not_move(frz):
    """동결된 역할의 파라미터는 update() 후 **정확히** 같고, 나머지는 움직인다."""
    torch.manual_seed(3)
    tr = MAPPOTrainer(OBS, N, _cfg(limiter_commit=True,
                                   **{f"freeze_{frz}": True}))
    buf = _fill(tr)
    b_l, b_f, b_c = (_snapshot(tr.lim_actor), _snapshot(tr.fin_actor),
                     _snapshot(tr.critic))
    stats = tr.update(buf)

    frozen, live = ((tr.lim_actor, b_l), (tr.fin_actor, b_f)) \
        if frz == "limiter" else ((tr.fin_actor, b_f), (tr.lim_actor, b_l))
    assert not _changed(*frozen), f"{frz} 액터가 움직였다 -- 동결이 안 걸렸다"
    assert _changed(*live), "살아있는 액터가 안 움직였다 -- 손실에서 같이 빠졌다"
    assert _changed(tr.critic, b_c), "크리틱은 항상 학습되어야 한다"
    assert stats[f"freeze/{frz}"] == 1.0
    assert all(np.isfinite(v) for v in stats.values())


@pytest.mark.torch
def test_p54b_frozen_limiter_commit_rate_is_renamed():
    """동결 팔에서 커밋률은 '제안' 이지 일어난 일이 아니다 -- 키 이름이 달라야 한다."""
    torch.manual_seed(3)
    tr = MAPPOTrainer(OBS, N, _cfg(limiter_commit=True, freeze_limiter=True))
    s = tr.update(_fill(tr))
    assert "limiter/commit_rate" not in s
    assert "limiter/commit_rate_proposed" in s

    torch.manual_seed(3)
    tr2 = MAPPOTrainer(OBS, N, _cfg(limiter_commit=True))
    s2 = tr2.update(_fill(tr2))
    assert "limiter/commit_rate" in s2


@pytest.mark.torch
def test_p55_defaults_are_off_and_bit_identical():
    """freeze 기본값은 False 이고, 그때 update 는 이 배선 이전과 같아야 한다.

    같은 시드에서 freeze 키를 **주지 않은** 러너와 **False 로 준** 러너가
    파라미터까지 동일함을 본다 (선언이 조용히 경로를 바꾸지 않았다는 증거).
    """
    assert MAPPOConfig.from_dict({}).freeze_limiter is False
    assert MAPPOConfig.from_dict({}).freeze_finisher is False

    outs = []
    for extra in ({}, {"freeze_limiter": False, "freeze_finisher": False}):
        torch.manual_seed(7)
        tr = MAPPOTrainer(OBS, N, _cfg(limiter_commit=True, **extra))
        tr.update(_fill(tr))
        outs.append([p.detach().clone() for p in tr.parameters()])
    assert all(torch.equal(a, b) for a, b in zip(*outs))


@pytest.mark.torch
def test_p56_parent_hooks_are_identity_by_default():
    """`MAPPORunner` 의 훅은 기본이 항등/no-op 이다 (2B/2C 경로 불변)."""
    live = {"limiter_0": np.ones(3, np.float32)}
    assert MAPPORunner._override_live(object(), live, None) is live
    assert MAPPORunner._observe_step(object(), None) is None


@pytest.mark.torch
def test_p57_both_frozen_is_refused():
    """두 역할 동시 동결은 학습 팔이 아니다 -- CLI 와 학습기 양쪽에서 막는다."""
    with pytest.raises(ValueError):
        arm_of("hold", "scripted")
    torch.manual_seed(0)
    tr = MAPPOTrainer(OBS, N, _cfg(freeze_limiter=True, freeze_finisher=True))
    with pytest.raises(ValueError):
        tr.update(_fill(tr))


def _write_run(root, arm, seed, shape_k, shape_n, aim_p=0.0):
    d = root / f"{arm}_s{seed}"
    d.mkdir(parents=True)
    (d / "summary.json").write_text(json.dumps({
        "seed": seed, "w_kill": 0.5, "arm": arm,
        "limiter_policy": ARM_SPECS[arm][0], "finisher_policy": ARM_SPECS[arm][1],
        "final_eval": {"n": 300, "neutralized_rate": 0.1,
                       "nondestructive_frac": 1.0,
                       "by_regime": {"SHAPING_NEEDED":
                                     {"n": shape_n,
                                      "neutralized_rate": shape_k / shape_n}}},
        "final_eval_bands": {"BAND_AIM": {"n": 60,
                                          "neutralized": {"p": aim_p},
                                          "net_capture": {"p": aim_p}}},
    }))


def _write_baseline(p, k=0, n=297, hi=0.0128):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "n": 500, "neutralized_rate": 0.182,
        "by_regime": {"SHAPING_NEEDED": {"n": n, "k": k, "neutralized_rate": k / n,
                                         "wilson_lo": 0.0, "wilson_hi": hi}},
        "bands": {"BAND_AIM": {"neutralized": {"p": 0.01}}}}))


def test_p59_aggregate_verdict_follows_declared_rule(tmp_path):
    """판정은 선언된 규칙 그대로여야 한다 -- 기저 상한을 넘는 팔만 통과한다."""
    root = tmp_path / "runs"
    # LS 는 확실히 넘고(30/183), SL/LL 은 못 넘는다(0/183)
    for s in (0, 1, 2):
        _write_run(root, "LS", s, 30, 183, aim_p=0.3)
        _write_run(root, "SL", s, 0, 183)
        _write_run(root, "LL", s, 0, 183)
    base = tmp_path / "hold_baseline.json"
    _write_baseline(base)

    out = aggregate(str(root), str(base), str(tmp_path / "missing.json"))
    assert out["tests"]["H_lim"]["passed"] is True
    assert out["tests"]["H_lim"]["strong"] is True          # 3/3 시드가 개별로도 통과
    assert out["tests"]["H_fin"]["passed"] is False
    assert out["tests"]["H_syn"]["passed"] is False         # LL 이 LS 상한을 못 넘는다
    assert out["arms"]["LS"]["shape_n"] == 3 * 183          # 시드 풀링
    assert out["attribution_shape"]["limiter_only(LS-SS)"] == pytest.approx(30 / 183)
    assert out["attribution_shape"]["finisher_only(SL-SS)"] == 0.0
    assert "통과: H_lim" in out["verdict"]
    # 규칙이 출력에 실려 있어야 한다 (사후 변경이 드러나도록)
    assert out["rules"]["H_lim"].startswith("LS 의 Wilson 하한")


def test_p59b_pooling_dependent_verdict_is_labelled(tmp_path):
    """한 시드가 끌고 간 통과는 '강함' 이 아니라 '풀링 의존' 으로 적힌다."""
    root = tmp_path / "runs"
    _write_run(root, "LS", 0, 40, 183)      # 이 시드만 크게 통과
    _write_run(root, "LS", 1, 0, 183)
    _write_run(root, "LS", 2, 0, 183)
    base = tmp_path / "hold_baseline.json"
    _write_baseline(base)
    out = aggregate(str(root), str(base), str(tmp_path / "missing.json"))
    assert out["tests"]["H_lim"]["passed"] is True
    assert out["tests"]["H_lim"]["strong"] is False
    assert out["arms"]["LS"]["seeds_beating_baseline"] == 1
    assert "풀링 의존" in out["verdict"]


def test_p59c_strong_threshold_is_a_majority_not_a_constant(tmp_path):
    """'강함' 기준은 시드 수에서 나온 **과반**이다 (5시드에서 2/5 는 다수가 아니다).

    상수 2 로 하드코딩돼 있으면 시드를 3 -> 5 로 늘렸을 때 기준이 조용히
    느슨해진다. 사전등록(docs/48 §4)이 '과반' 이라고 적힌 이유이고, 여기가
    그 문장이 코드와 붙어 있는 지점이다.
    """
    base = tmp_path / "hold_baseline.json"
    _write_baseline(base)

    def _strong_for(n_beat, n_seeds):
        root = tmp_path / f"runs_{n_beat}_{n_seeds}"
        for s in range(n_seeds):
            _write_run(root, "LS", s, 30 if s < n_beat else 0, 183)
        out = aggregate(str(root), str(base), str(tmp_path / "missing.json"))
        t = out["tests"]["H_lim"]
        assert out["arms"]["LS"]["n_runs"] == n_seeds
        return t["passed"], t["strong"]

    assert _strong_for(2, 3) == (True, True)      # 3시드: 과반 = 2
    assert _strong_for(1, 3) == (True, False)
    assert _strong_for(3, 5) == (True, True)      # 5시드: 과반 = 3
    assert _strong_for(2, 5) == (True, False)     # 2/5 는 '풀링 의존'


def test_p59d_declared_seed_axis_is_five(tmp_path):
    """선언된 시드 축(docs/48 §2)과 실행기의 기본값이 같아야 한다."""
    from shepherd.scripts.roles_split import DEFAULT_ARMS, SEEDS, plan
    assert SEEDS == (0, 1, 2, 3, 4)
    # 기본 팔은 docs/48 의 2x2 뿐이다 -- docs/49 팔(SL-BCw/BCa)은 --arms 로 고른다.
    # 기본에 섞이면 "역할 분리 15런"의 정의가 조용히 바뀐다.
    assert DEFAULT_ARMS == ("LL", "LS", "SL")
    cmds = plan("results/m4_roles")
    assert len(cmds) == len(DEFAULT_ARMS) * len(SEEDS) == 15
    assert {n.split("_s")[1] for n, _ in cmds} == {"0", "1", "2", "3", "4"}
    bc = plan("results/m4_roles", arms=("SL-BCw", "SL-BCa"))
    assert len(bc) == 10
    assert all("--aim-bc" in c for _, c in bc)


# ── P61~P62: 실행 풀 + 알림 (9시간짜리를 무인으로 돌리는 장치) ──────────────
def test_p61_pool_never_exceeds_jobs_and_splits_logs(tmp_path, monkeypatch):
    """★ 슬롯을 넘겨 띄우지 않는다. `sweep_m4` 루프는 순간 `jobs+1` 이 된다.

    공용 서버에서 '코어 10개만 쓴다' 고 약속하고 도는 작업이라, 이 1개가
    약속을 깬다. 동시에 런별 로그가 갈리는지도 같이 본다.
    """
    from shepherd.scripts.roles_split import run_pool

    peak = {"n": 0}
    real_popen = subprocess.Popen
    live = []

    class _P:
        def __init__(self, cmd, stdout=None, stderr=None):
            self.returncode = None
            self._left = 2                      # 두 번 poll 하면 끝난다
            live.append(self)
            peak["n"] = max(peak["n"], len(live))

        def poll(self):
            self._left -= 1
            if self._left <= 0:
                self.returncode = 0
                if self in live:
                    live.remove(self)
                return 0
            return None

        def terminate(self):                    # pragma: no cover
            pass

    monkeypatch.setattr(subprocess, "Popen", _P)
    cmds = [(f"r{i}", ["x", "--output", str(tmp_path / f"r{i}")]) for i in range(9)]
    failed = run_pool(cmds, jobs=3, poll_s=0.0)

    assert failed == []
    assert peak["n"] <= 3, f"동시 실행이 {peak['n']} 까지 갔다 (jobs=3)"
    for i in range(9):
        assert (tmp_path / f"r{i}" / "train.log").exists()
    assert subprocess.Popen is _P and real_popen is not _P     # monkeypatch 확인


def test_p61b_pool_reports_failures_without_stopping(tmp_path, monkeypatch):
    """한 런이 죽어도 나머지는 끝까지 돈다. 실패 목록으로 돌아온다."""
    from shepherd.scripts.roles_split import run_pool

    class _P:
        def __init__(self, cmd, stdout=None, stderr=None):
            self._bad = cmd[-1].endswith("r1")
            self.returncode = None
            self._left = 1

        def poll(self):
            self._left -= 1
            if self._left <= 0:
                self.returncode = 3 if self._bad else 0
                return self.returncode
            return None

        def terminate(self):                    # pragma: no cover
            pass

    monkeypatch.setattr(subprocess, "Popen", _P)
    cmds = [(f"r{i}", ["x", "--output", str(tmp_path / f"r{i}")]) for i in range(4)]
    assert run_pool(cmds, jobs=2, poll_s=0.0) == ["r1"]


def test_p62_ntfy_is_a_noop_without_topic_and_never_raises(monkeypatch):
    """알림이 학습을 죽이면 안 된다 -- 토픽 없으면 no-op, 있어도 예외를 삼킨다."""
    import urllib.request

    from shepherd.notify import ntfy, ntfy_enabled

    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    assert ntfy_enabled() is False

    def _boom(*a, **k):                         # pragma: no cover - 호출되면 실패
        raise AssertionError("토픽이 없는데 네트워크를 건드렸다")
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    ntfy("nothing happens")                     # no-op 이어야 한다

    monkeypatch.setenv("NTFY_TOPIC", "t")
    assert ntfy_enabled() is True

    def _fail(*a, **k):
        raise OSError("network down")
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    ntfy("서버가 죽어도 여기서 예외가 나오면 안 된다")     # 삼켜야 한다


def test_p62b_train_m3a_ntfy_delegates_to_the_single_definition(monkeypatch):
    """`train_m3a.ntfy` 는 복사본이 아니라 `shepherd.notify` 를 부른다."""
    import shepherd.notify as notify_mod
    import shepherd.scripts.train_m3a as m3a

    seen = []
    monkeypatch.setattr(notify_mod, "ntfy",
                        lambda msg, title="shepherd", priority=None:
                        seen.append((msg, title)))
    monkeypatch.setattr(m3a, "_ntfy", notify_mod.ntfy)
    m3a.ntfy("hello")
    assert seen == [("hello", "m3a")]


def test_p62c_push_summary_carries_the_verdict(tmp_path):
    """알림 본문에 **판정과 팔별 수치**가 실린다 (끝났다는 말만 오면 쓸모없다)."""
    from shepherd.scripts.roles_split import summarize_for_push

    root = tmp_path / "runs"
    for s in range(5):
        _write_run(root, "LS", s, 30, 183)
        _write_run(root, "SL", s, 0, 183)
        _write_run(root, "LL", s, 0, 183)
    base = tmp_path / "hold_baseline.json"
    _write_baseline(base)
    v = aggregate(str(root), str(base), str(tmp_path / "missing.json"))

    msg = summarize_for_push(v, [])
    assert "LS: 150/915" in msg
    assert "H_lim=O" in msg and "H_fin=X" in msg
    assert v["verdict"] in msg
    assert "★ 실패" not in msg

    msg2 = summarize_for_push(v, ["LL_s3"])
    assert msg2.startswith("★ 실패 1런: LL_s3")


def test_p60_null_case_is_the_reported_result(tmp_path):
    """세 팔 모두 못 넘으면 그것이 결과다 -- '결과 없음' 이 아니라 판정이 나와야 한다."""
    root = tmp_path / "runs"
    for arm in ARM_SPECS:
        for s in (0, 1, 2):
            _write_run(root, arm, s, 0, 183)
    base = tmp_path / "hold_baseline.json"
    _write_baseline(base)
    out = aggregate(str(root), str(base), str(tmp_path / "missing.json"))
    assert all(v["passed"] is False for v in out["tests"].values())
    assert "못 넘었다" in out["verdict"]
    assert out["band_aim_report"]["_note"].startswith("보고 전용")


def test_p60b_missing_baseline_refuses_to_judge(tmp_path):
    """기저선이 없으면 판정하지 않는다 (조용히 0 을 기저로 삼지 않는다)."""
    root = tmp_path / "runs"
    _write_run(root, "LS", 0, 5, 183)
    out = aggregate(str(root), str(tmp_path / "nope.json"), str(tmp_path / "x.json"))
    assert "tests" not in out and "verdict" not in out
    assert "기저선이 없다" in out["note"]


@pytest.mark.torch
def test_p58_arm_table_matches_cli_choices():
    """`ARMS` 의 키 집합이 CLI choices 의 2x2 에서 SS 만 뺀 것과 정확히 같다."""
    from shepherd.scripts.train_m4 import build_parser_defaults
    d = build_parser_defaults()
    assert (d.limiter_policy, d.finisher_policy, d.aim_bc) == \
        ("learned", "learned", "none")
    # docs/48 의 2x2 (aim_bc=none) 에서 SS 칸만 빠져 있어야 한다
    base = {k for k in ARMS if k[2] == "none"}
    full = {(l, f, "none") for l in ("learned", "hold")
            for f in ("learned", "scripted")}
    assert base == full - {("hold", "scripted", "none")}
    assert arm_of("learned", "learned") == "LL"
    # docs/49 의 조준 BC 팔은 **발사가 학습일 때만** 존재한다
    assert {ARMS[k] for k in ARMS if k[2] != "none"} == {"SL-BCw", "SL-BCa"}
    assert all(k[1] == "learned" for k in ARMS if k[2] != "none")
    with pytest.raises(ValueError):
        arm_of("learned", "scripted", "warm")      # 스크립트 발사 + BC 는 무의미
