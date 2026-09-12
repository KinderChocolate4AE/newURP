"""B0 v3 world contract 테스트 (docs/94 §3) — "그 세계가 코드에 실재하는가".

**민감도 테스트가 아니다.** 각 테스트는 B0 v3 계약의 한 조항이 sealed world 안에서
실제로 참인지만 확인한다. 서버 campaign 을 대체하는 것이 아니라, 서버가 필요 없는
종류의 확인이다. 전부 torch-free · 로컬 초 단위.

  t1  q_dec  = dt/tau_deploy       = 1/6  (pinned conditioning, docs/94 §1.2)
  t2  q_race = tau_lock/tau_deploy = 1/3  ∧  q_kill = tau_kill/tau_deploy = 1/2
  t3  관측 = 참값 · zero-latency (§1.3)
  t4  NET_SPENT 경로 실재 + F-계약에서 미종료 (§2-4, §2-5)
  t5  same-tick precedence = sealed discrete-time tie rule (§2-12 ④)
  t6  WAIT != tau — 기다린 시간은 지연에 산입되지 않는다 (§2-4 tau 원점)
  t8  train/eval manifest parity — RL-credit cut 이 world flags 를 바꾸지 않는다 (§2-6)

t7 (F1 hygiene) 은 pytest 가 아니라 절차다: comment-only diff 확인 + 기존 regression green.

세계: 테스트는 M2 기본값이 아니라 **캠페인 세계** (R2a resolver, tau=0.30, dt=0.05) 에서
돈다 — B0 v3 가 봉인하는 세계가 그것이기 때문이다.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from shepherd.env_sys import ModeSystemEnv
from shepherd.m4_env import build_m4_env, manifest_mismatch
from shepherd.scripts.mission_rollout import scripted_role_actions, terminal_label
from shepherd.scripts.r2a_lattice import _pins, impls
from shepherd.scripts.r2a_stage1 import SEED0, _lattice, resolve

CHI, ETA = 0.8, 3.0                      # bracket 내부 셀 (a≈31.5, v≈17.7)
Q_DEC, Q_RACE, Q_KILL = 1 / 6, 1 / 3, 1 / 2


def _impls():
    return impls(_lattice()["tau_B"])


def _kw(system=None, **over):
    kw = resolve(_impls()["R-ref"], CHI, ETA)
    if system is not None:
        kw["system"] = system
    if over:
        kw["system"] = replace(kw["system"], **over)
    return kw


def _sysenv(env) -> ModeSystemEnv:
    while not isinstance(env, ModeSystemEnv):
        env = env.inner
    return env


def _drive(**sysover) -> dict:
    """hold limiter · 자발 발사 없음. 발사는 force_commit_step 이 한 번만 낸다."""
    st = build_m4_env(SEED0, 0, **_kw(**sysover))
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=SEED0)
    fid = env.finisher_id
    r = dict(fire=None, spent=None, handoff=None, end=None, label=None, steps=0)
    for t in range(int(lay.episode_len)):
        acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                     fire_mode="never")
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, info = env.step(acts)
        fi = info[fid]
        r["steps"] = t + 1
        if fi.get("fire_event") and r["fire"] is None:
            r["fire"] = t
        if fi.get("fsm_state") == "SPENT" and r["spent"] is None:
            r["spent"] = t
        if fi.get("net_miss_handoff"):
            r["handoff"] = t
        if term.get(fid):
            r["end"], r["label"] = t, terminal_label(fi)
            break
        if trunc.get(fid):
            r["end"], r["label"] = t, "TRUNCATED"
            break
    r["se"], r["scn"], r["env"] = _sysenv(env), scn, env
    return r


# ------------------------------------------------------------ t0 (payload) ---
def test_t0_sealed_payload_is_reproducible_and_matches_r2a_provenance():
    """봉인 payload 가 R2a 산출물에서 **재생성 가능**하고 해시가 맞는지 (docs/94 §4).

    격자는 하드코딩이 아니라 `stage3_protocol` 의 nearest inside/outside 에서 유도된다 —
    그 사슬이 끊기면 봉인된 좌표계가 조용히 달라진다.
    """
    import hashlib
    import json
    import pathlib

    from shepherd.scripts.b0_v3 import build_grid

    root = pathlib.Path(__file__).resolve().parents[1]
    d = json.loads((root / "artifacts/b0/b0_v3_world_contract.json").read_text(encoding="utf-8"))

    body = dict(d)
    h = body.pop("b0_hash")
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16] == h

    g = d["grid"]
    assert g["G"] == 14 and len(g["rows"]) == 14
    assert {len(r["chi_base"]) for r in g["rows"]} == {4}
    assert g["rows"] == build_grid()["rows"], "격자가 R2a 산출물에서 재생성되지 않는다"

    st3 = json.loads((root / "artifacts/r2a/stage3_protocol.json").read_text(encoding="utf-8"))
    assert d["world"]["inherits"]["stage3_protocol"] == st3["protocol_hash"]
    for r in g["rows"]:                       # base 4점 = {lo-.04, lo, hi, hi+.04}
        lo, hi = r["chi_base"][1], r["chi_base"][2]
        assert r["chi_base"][0] == pytest.approx(lo - 0.04)
        assert r["chi_base"][3] == pytest.approx(hi + 0.04)
        assert lo < r["r2a_chi50"] <= hi + 1e-9, r      # bracket 이 chi50 을 감싼다


# ---------------------------------------------------------------- t1, t2 ---
def test_t1_q_dec_is_one_sixth_in_every_implementation():
    """q_dec 는 pinned conditioning — ledger 의 모든 구현에서 구조적으로 1/6."""
    for name, im in _impls().items():
        assert _pins(im)["q_dec"] == pytest.approx(Q_DEC, abs=1e-12), name


def test_t1b_q_dec_survives_into_the_resolved_contract_manifest():
    """runner-local assert 가 아니라 **manifest 수준**에서 읽힌다 (docs/94 §1.5)."""
    e = build_m4_env(SEED0, 0, **_kw()).contract["extra_cfg"]
    assert e["physics.dt"] / e["physics.tau_deploy"] == pytest.approx(Q_DEC, abs=1e-12)


def test_t2_timer_ratios_are_contract_fixed():
    """q_race · q_kill 은 새 좌표가 아니라 co-scale 되는 고정 비율이다."""
    for name, im in _impls().items():
        p = _pins(im)
        assert p["tau_lock_tau"] == pytest.approx(Q_RACE, abs=1e-12), name
        assert p["tau_kill_tau"] == pytest.approx(Q_KILL, abs=1e-12), name
    kw = _kw()
    e = kw["extra_cfg"]
    assert e["physics.tau_lock"] / e["physics.tau_deploy"] == pytest.approx(Q_RACE, abs=1e-12)
    assert kw["system"].tau_kill / e["physics.tau_deploy"] == pytest.approx(Q_KILL, abs=1e-12)


# -------------------------------------------------------------------- t3 ---
def test_t3_observation_is_the_true_state_with_zero_latency():
    """관측은 당 틱 참값이다 — 잡음도, 한 스텝 지연도 없다 (docs/94 §1.3).

    obs 선두 블록이 **이동 후 현재 상태와 비트 단위로 같음**을 두 시점에서 확인한다.
    """
    st = build_m4_env(SEED0, 0, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    inner = _sysenv(env).inner
    obs_d, _ = env.reset(seed=SEED0)

    def _check(obs):
        lims, fin, att = inner._states()
        n = inner.N_max
        for i, s in enumerate(lims):
            assert np.array_equal(obs[i * 9:(i + 1) * 9], np.asarray(s, np.float32)), i
        assert np.array_equal(obs[n * 9:(n + 1) * 9], np.asarray(fin, np.float32))
        assert np.array_equal(obs[(n + 1) * 9:(n + 2) * 9], np.asarray(att, np.float32))

    _check(np.asarray(obs_d[env.limiter_ids[0]], np.float32))
    acts = scripted_role_actions(env, scn, lay, limiter_mode="hold", fire_mode="never")
    acts[env.adversary_id] = np.zeros(3, np.float32)
    obs_d, _, _, _, _ = env.step(acts)
    _check(np.asarray(obs_d[env.limiter_ids[0]], np.float32))   # 한 스텝 지연 없음


# -------------------------------------------------------------------- t4 ---
def test_t4_net_spent_exists_and_does_not_terminate_under_the_f_contract():
    """NET_SPENT = FSM/env_sys 상태 전이 (§2-4) 이고, F-계약은 그 종료만 억제한다 (§2-5).

    paired: 같은 강제 발사에서 miss_terminates 만 뒤집는다.
    """
    fb = _drive(force_commit_step=1)                       # F-계약 (miss_terminates=False)
    lg = _drive(force_commit_step=1, miss_terminates=True)  # legacy 대조

    assert lg["spent"] is not None, "강제 발사가 miss 로 소진되지 않았다 — 픽스처 실패"
    assert lg["label"] == "SPENT_FAIL" and lg["end"] == lg["spent"]

    # 같은 물리: 소진 스텝이 같다. 다른 것은 그 뒤에 무슨 일이 일어나는가뿐이다.
    assert fb["spent"] == lg["spent"]
    assert fb["handoff"] == lg["spent"], "handoff 는 소진 스텝에 정확히 한 번"
    assert fb["label"] != "SPENT_FAIL", "F-계약에서 SPENT_FAIL 은 종료 라벨이 아니다"
    assert fb["steps"] > lg["steps"], "NET_FAIL 이후 물리 episode 가 계속돼야 한다"

    se = fb["se"]
    assert se.net_spent is True
    assert se.net_spent_step == fb["spent"] + 1      # _step_i 는 1-based
    assert se.inner.fsm.state.name == "SPENT" and se.inner.fsm.k == 0


# -------------------------------------------------------------------- t5 ---
def test_t5_same_tick_precedence_is_the_sealed_tie_rule():
    """Same-tick capture–penetration precedence (§2-12 ④ 봉인 문안).

    지연 capture 가 침투 술어와 **같은 이산 tick** 에 해소되면 CAPTURE 가 우선한다.
    (연속시간 물리 순서 주장 아님 — 이산시간 tie 규칙이다.)
    """
    assert terminal_label({"captured": True, "penetrated": True}) == "CAPTURED"
    assert terminal_label({"penetrated": True}) == "PENETRATED"
    assert terminal_label({"hard_kill": True, "captured": True,
                           "penetrated": True}) == "HARD_KILL"
    assert terminal_label({}) == "SPENT_FAIL"


def test_t5b_both_callers_share_one_definition():
    """사슬 복제 금지 — run_episode 와 _Driver 가 같은 함수를 부른다."""
    import shepherd.scripts.recoverability_probe as rp
    assert rp.terminal_label is terminal_label


# -------------------------------------------------------------------- t6 ---
def test_t6_wait_is_not_latency():
    """policy 가 기다린 시간은 tau 가 아니다 (§2-4).

    발사를 4 틱 늦춰도 fire -> 해소 간격은 (tau_deploy + tau_lock)/dt 로 불변.
    """
    early, late = _drive(force_commit_step=1), _drive(force_commit_step=5)
    scn, env = early["scn"], early["env"]
    want = round((env.tau_deploy + scn.finisher.tau_lock) / env.dt)

    for r in (early, late):
        assert r["fire"] is not None and r["spent"] is not None
        assert r["spent"] - r["fire"] == want, r
    assert late["fire"] - early["fire"] == 4, (early["fire"], late["fire"])


# -------------------------------------------------------------------- t9 ---
def test_t9_theta_fire_is_an_admissibility_constraint_not_a_learnable_gate():
    """결재 ⑥: `v_shot_soft < θ_fire` 이면 FIRE 는 **no-op** 이다 (docs/94 §2-2).

    정책이 학습하는 것은 admissible region **안에서의 timing** 이지 gate 가 아니다.
    """
    st = build_m4_env(SEED0, 0, **_kw())
    env, scn, lay = st.env, st.scn, st.lay
    env.reset(seed=SEED0)
    inner = _sysenv(env).inner
    fid = env.finisher_id

    lims, fin, att = inner._states()
    v = inner._vshot(inner._p(att), inner._v(att),
                     [inner._p(l) for l in lims], fin, seed=0)
    assert v.v_shot_soft < inner.theta_fire, "픽스처 전제 실패 — 이미 admissible 하다"

    k0 = inner.fsm.k
    acts = scripted_role_actions(env, scn, lay, limiter_mode="hold", fire_mode="never")
    a = np.asarray(acts[fid], np.float32).copy()
    a[4] = 1.0                                   # FIRE 를 명시적으로 낸다
    acts[fid] = a
    acts[env.adversary_id] = np.zeros(3, np.float32)
    _, _, _, _, info = env.step(acts)

    fi = info[fid]
    assert not fi.get("fire_event"), "gate 아래에서 발사가 나갔다"
    assert fi["fsm_state"] == "LOADED" and inner.fsm.k == k0, "탄이 소모됐다"


# ------------------------------------------------------------------- t10 ---
def test_t10_pre_net_contact_terminates_only_outside_the_no_kinetic_zone():
    """결재 ⑤ 의 근거 표 (docs/94 §2-7): 종료 여부가 **영역에 따라 갈린다**.

    NK 밖 → 소모·KILL·종료 / NK 안 → VETO (기폭 보류) · 미소모 · 종료 안 함.
    그래서 계약이 "illegal contact = 즉시 terminal" 이라고 적으면 거짓이 된다.
    """
    def _one(d_asset: float):
        se = _sysenv(build_m4_env(SEED0, 0, **_kw()).env)
        se.reset(seed=SEED0)
        lims, _, att = se.inner._states()
        p = se.inner._p(att).copy()              # limiter 를 공격자 위에 둔다
        lp = [se.inner._p(s).copy() for s in lims]
        lp[0] = p.copy()
        ev = se._resolve_contacts(p, lp, p, lp, d_asset)
        assert len(ev) >= 1, "접촉 event 가 생성되지 않았다"
        return se, ev[0]

    r_nk = _kw()["system"].r_nk
    se_in, rec_in = _one(r_nk - 1.0)             # NK zone 안
    assert rec_in.outcome == "VETO_NO_KINETIC"
    assert rec_in.consumed is False and se_in.hard_kill is False
    assert 0 not in se_in.retired                # limiter 미소모 -> 재접촉 시 재평가

    se_out, rec_out = _one(r_nk + 1.0)           # NK zone 밖 (p_kill = 1.0)
    assert rec_out.outcome == "KILL"
    assert rec_out.consumed is True and se_out.hard_kill is True


# -------------------------------------------------------------------- t8 ---
def test_t8_train_eval_manifest_parity_and_the_flag_trap():
    """world contract 는 entrypoint 가 아니라 manifest 로 정의된다 (§1.5).

    두 번째 assert 가 §2-6 의 구현 함정을 잠근다: RL-credit cut 을
    `miss_terminates` 로 구현하면 train/eval 이 **다른 세계**가 된다.
    """
    kw = _kw()
    a = build_m4_env(SEED0, 0, **kw).contract
    b = build_m4_env(SEED0, 7, **kw).contract        # 다른 에피소드 = 같은 계약
    assert manifest_mismatch(a, b) == []

    trap = build_m4_env(SEED0, 0, **_kw(miss_terminates=True)).contract
    assert manifest_mismatch(a, trap) == ["system.miss_terminates"]
