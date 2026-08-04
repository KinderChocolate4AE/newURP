"""M4 환경 조립 — 학습기와 분리된 **torch-free** 합성 루트.

`train_m4.py` 에 두면 torch 없이는 조립을 검증할 수 없다. 리포 관례대로
환경 계층은 torch-free 로 유지하고, 학습기는 이 모듈을 import 한다.

쌓는 순서 (순서가 중요하다)
---------------------------
    make_train_env        동결 env (물리 · 종료 · 기존 보상)
    ModeSystemEnv         하드킬 방아쇠 · no-kinetic zone · M4 보상   (env 래퍼)
    attach_attacker       공격자 사다리 주입                          (백엔드 프록시)
    spawn_for_episode     초기조건 재기입                             (reset 전)
    attach_threat_obs     위협 등급 관측 확장                         (관측 래퍼)

`attach_attacker` 는 **inner** 에 붙인다 -- 백엔드 프록시이므로 래퍼 위가 아니라
안쪽 env 의 backend 를 감싸야 한다. `spawn_for_episode` 도 inner 의 AgentKin 을
고쳐야 하므로 inner 에 건다.

torch-free.
"""
from __future__ import annotations

import copy
from typing import Callable, Dict, Optional, Sequence

import numpy as np

from shepherd.agents.attacker_ladder import (AttackerSpec, derive_phase,
                                             make_attacker)
from shepherd.env_adv import attach_attacker
from shepherd.env_sys import ModeSystemEnv, RewardSpec, SystemSpec
from shepherd.m4_config import m4_config, m4_episode_config
from shepherd.obs_threat import attach_threat_obs
from shepherd.spawn_rand import SpawnSpec, spawn_for_episode
from shepherd.train.make_env import make_train_env

__all__ = ["M4Stack", "build_m4_env", "regime_of", "mission_eval"]


class M4Stack(dict):
    """조립 결과 묶음. `env / scn / lay / threat` 키를 갖는다."""
    __getattr__ = dict.__getitem__


def build_m4_env(seed: int, episode: int, *,
                 system: SystemSpec, reward: RewardSpec,
                 attacker: AttackerSpec, spawn: SpawnSpec,
                 randomize_threat: bool = True,
                 threat_obs: bool = True,
                 extra_cfg: Optional[dict] = None) -> M4Stack:
    """M4 스택 한 판."""
    if randomize_threat:
        cfg = m4_episode_config(seed, episode, extra_cfg)
    else:
        cfg = m4_config(extra_cfg)

    inner, scn, lay = make_train_env(copy.deepcopy(cfg))
    env = ModeSystemEnv(inner, lay, scn, system, reward)
    attach_attacker(inner, make_attacker(attacker),
                    phase=derive_phase(seed, episode))
    spawn_for_episode(inner, spawn, seed=seed, episode=episode)

    threat = {
        "a_att": float(cfg["physics"]["a_att_max"]),
        "att_speed": float(cfg["physics"]["att_speed"]),
        "a_lim": float(cfg["physics"]["a_lim_max"]),
        "v_lim": float(cfg["train"]["limits"]["limiter_v_max"]),
        "tau": float(cfg["physics"]["tau_deploy"]),
        "net_radius": float(cfg["physics"]["net_radius"]),
    }
    env = attach_threat_obs(env, a_att=threat["a_att"],
                            att_speed=threat["att_speed"], enabled=threat_obs)
    return M4Stack(env=env, scn=scn, lay=lay, threat=threat)


def regime_of(a_att: float, tau: float, net_radius: float) -> str:
    """명제 N (docs/10) 기준 regime.

    `w = 0.5*a_att*tau^2` 가 `rho`(net_radius) 이하이면 조향 없이도 포획된다
    -- 조향의 방어가치가 0 이다. 위협 브래킷이 이 경계를 가로지르도록
    선언되어 있다 (docs/40 §8.1, a* = 2*rho/tau^2 = 44.4 m/s^2).
    """
    return ("SHAPING_NEEDED" if 0.5 * float(a_att) * float(tau) ** 2 > float(net_radius)
            else "FREE_CAPTURE")


def mission_eval(seed0: int, episodes: int, *,
                 system: SystemSpec, reward: RewardSpec, attacker: AttackerSpec,
                 spawn: SpawnSpec, policy: Optional[Callable] = None,
                 limiter_mode: str = "hold", fire_mode: str = "clean",
                 randomize_threat: bool = True, threat_obs: bool = True,
                 baseline_commit: bool = False,
                 records: Optional[list] = None,
                 scripted_roles: Sequence[str] = ()) -> dict:
    """2층 임무 지표 (docs/29 §4) — regime 별로 쪼개서 낸다.

    **`interdiction_rate = 1 - PENETRATED` 를 그대로 쓰지 않는다.**
    그 정의는 SPENT_FAIL(탄 소진·미무력화)과 TRUNCATED(우측 절단)를 성공으로
    세므로 부풀려진다 (docs/40 §8.2 각주). 여기서는 분해해서 보고한다.

    `scripted_roles` 는 역할 분리(docs/48)용 -- `policy` 가 있어도 그 역할만
    스크립트로 덮어쓴다. 기본 `()` 이면 기존 호출부와 bit-identical.
    """
    from shepherd.scripts.mission_rollout import LABELS, run_episode

    counts = {lab: 0 for lab in LABELS}
    by_regime: Dict[str, Dict[str, int]] = {}
    for ep in range(episodes):
        st = build_m4_env(seed0, ep, system=system, reward=reward,
                          attacker=attacker, spawn=spawn,
                          randomize_threat=randomize_threat, threat_obs=threat_obs)
        r = run_episode(st.env, st.scn, st.lay, seed=seed0 + ep,
                        limiter_mode=limiter_mode, fire_mode=fire_mode,
                        policy=policy, baseline_commit=baseline_commit,
                        scripted_roles=scripted_roles)
        counts[r.label] += 1
        reg = regime_of(st.threat["a_att"], st.threat["tau"], st.threat["net_radius"])
        by_regime.setdefault(reg, {lab: 0 for lab in LABELS})[r.label] += 1
        # ★ 에피소드별 위협 draw 기록 (선택). regime 2칸이 아니라 **연속 축**으로
        #   포획 확률을 그리려면 이게 필요하다 -- 신청서 핵심 그림 1의 1차원 판.
        #   기본 None 이므로 기존 호출부는 bit-identical.
        if records is not None:
            records.append({"episode": ep, "label": r.label, "regime": reg,
                            "a_att": st.threat["a_att"], "att_speed": st.threat["att_speed"],
                            "net_radius": st.threat["net_radius"], "tau": st.threat["tau"]})

    def _split(c: Dict[str, int]) -> dict:
        m = max(sum(c.values()), 1)
        k = c["NET_CAPTURE"] + c["CAPTURE_WITH_CONTACT"]
        return {
            "n": sum(c.values()),
            "penetrated_rate": c["PENETRATED"] / m,
            "neutralized_rate": (k + c["HARD_KILL"]) / m,
            "spent_fail_rate": c["SPENT_FAIL"] / m,
            "truncated_rate": c["TRUNCATED"] / m,
            "nondestructive_frac": k / max(k + c["HARD_KILL"], 1),
        }

    # 전체 지표는 regime 분해와 **같은 식**이다 (n = sum(counts) = episodes).
    return {**_split(counts), "counts": counts,
            "by_regime": {k: _split(v) for k, v in by_regime.items()}}
