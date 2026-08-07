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
import hashlib
import json
from dataclasses import asdict
from typing import Callable, Dict, Optional, Sequence

import numpy as np

from shepherd.agents.attacker_ladder import (AttackerSpec, derive_phase,
                                             make_attacker)
from shepherd.env_adv import attach_attacker
from shepherd.env_sys import ModeSystemEnv, RewardSpec, SystemSpec
from shepherd.m4_config import m4_config, m4_episode_config
from shepherd.obs_threat import attach_threat_obs
from shepherd.spawn_rand import (SpawnSpec, StandbySpec, apply_standby,
                                 spawn_for_episode)
from shepherd.train.make_env import make_train_env

__all__ = ["M4Stack", "build_m4_env", "regime_of", "mission_eval",
           "contract_manifest", "manifest_mismatch", "CONTRACT_SCHEMA"]

# ── resolved-contract manifest (docs/65 A4a) ────────────────────────────────
# "같은 실험" 은 코드 entrypoint 가 아니라 **동일한 resolved world contract**
# 를 공유할 때만 성립한다 (docs/65 §9 운영 규율). 그래서 manifest 는 호출자의
# 의도(kwargs)가 아니라 **build_m4_env 가 실제로 받은 것 + 합성된 cfg** 에서
# 뽑는다 -- 전달 누락(silent legacy fallback)이 곧 hash 불일치로 드러난다.
CONTRACT_SCHEMA = "resolved-contract-v1"


def contract_manifest(*, system, reward, attacker, spawn, standby,
                      randomize_threat, threat_obs, extra_cfg, cfg,
                      dist_ref=None) -> dict:
    """실제 생성 입력 + 합성 cfg 에서 계약 필드를 뽑아 hash 를 붙인다.

    에피소드별 위협 draw(physics.a_att_max 등)는 **분포의 표본**이지 계약이
    아니므로 넣지 않는다 -- 같은 runner 의 manifest 는 에피소드와 무관하게
    동일해야 parity 비교가 성립한다. `dist_ref` 가 있으면 (threat_layer 경로)
    attacker/standby 도 분포의 표본이므로 점 스펙 대신 분포 참조로 기록한다.
    """
    m = {
        "schema": CONTRACT_SCHEMA,
        "system": asdict(system),
        "reward": asdict(reward),
        "attacker": dict(dist_ref) if dist_ref else asdict(attacker),
        "spawn": asdict(spawn),
        "standby": (dict(dist_ref) if dist_ref
                    else None if standby is None else asdict(standby)),
        "randomize_threat": bool(randomize_threat),
        "threat_obs": bool(threat_obs),
        "extra_cfg": ({} if not extra_cfg
                      else {k: extra_cfg[k] for k in sorted(extra_cfg)}),
        "episode_len": int(cfg["train"]["episode_len"]),
        "judge": str(cfg["viability"]["judge"]),
        "n_segments": int(cfg["viability"]["n_segments"]),
    }
    m["hash"] = hashlib.sha256(
        json.dumps(m, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return m


def manifest_mismatch(a: dict, b: dict, allow: Sequence[str] = ()) -> list:
    """두 manifest 의 불일치 경로 목록. `allow` 에 선언된 축(예: "reward.w_kill",
    "attacker.label")만 예외 -- 그 외 mismatch 는 다른 세계다 (fail 대상)."""
    diffs = []
    for k in sorted(set(a) | set(b)):
        if k in ("hash",):
            continue
        va, vb = a.get(k), b.get(k)
        if isinstance(va, dict) and isinstance(vb, dict):
            for kk in sorted(set(va) | set(vb)):
                if va.get(kk) != vb.get(kk) and f"{k}.{kk}" not in allow:
                    diffs.append(f"{k}.{kk}")
        elif va != vb and k not in allow:
            diffs.append(k)
    return diffs


class M4Stack(dict):
    """조립 결과 묶음. `env / scn / lay / threat / contract` 키를 갖는다."""
    __getattr__ = dict.__getitem__


def build_m4_env(seed: int, episode: int, *,
                 system: SystemSpec, reward: RewardSpec,
                 attacker: Optional[AttackerSpec] = None,
                 spawn: Optional[SpawnSpec] = None,
                 standby: Optional[StandbySpec] = None,
                 randomize_threat: bool = True,
                 threat_obs: bool = True,
                 extra_cfg: Optional[dict] = None,
                 threat_layer: Optional[str] = None) -> M4Stack:
    """M4 스택 한 판. `standby` 기본 None = 기존과 bit 동일 (docs/60 P87).

    `threat_layer` ("train"/"iid", docs/61) 를 주면 attacker/standby/spawn/
    extra_cfg 를 **에피소드별 `draw_threat_v3` draw 로 구성**한다 — 이때 점
    스펙 인자를 함께 주면 ValueError (silent override 금지, docs/65 A4b).
    manifest 의 attacker/standby 는 점 스펙 대신 분포 참조(layer +
    distribution hash)로 기록된다 — 같은 layer 의 모든 에피소드가 같은
    world contract 를 공유함을 hash 동일성으로 검사할 수 있다.
    """
    dist_ref = None
    if threat_layer is not None:
        from shepherd.scale_v2 import draw_threat_v3, v3_distribution_hash
        if attacker is not None or standby is not None or extra_cfg is not None \
                or spawn is not None:
            raise ValueError(
                "threat_layer 와 점 스펙(attacker/spawn/standby/extra_cfg)을 "
                "동시에 줄 수 없다 -- draw 가 전부 구성한다 (docs/65 A4b)")
        d = draw_threat_v3(seed, episode, threat_layer)
        attacker, spawn, standby = d["attacker"], d["spawn"], d["standby"]
        extra_cfg = d["cfg"]
        dist_ref = {"threat_layer": threat_layer,
                    "distribution_hash": v3_distribution_hash()}
    elif attacker is None or spawn is None:
        raise ValueError("attacker/spawn 은 필수다 (threat_layer 미사용 시)")
    if randomize_threat:
        cfg = m4_episode_config(seed, episode, extra_cfg)
    else:
        cfg = m4_config(extra_cfg)

    inner, scn, lay = make_train_env(copy.deepcopy(cfg))
    env = ModeSystemEnv(inner, lay, scn, system, reward)
    attach_attacker(inner, make_attacker(attacker),
                    phase=derive_phase(seed, episode))
    if standby is not None:
        apply_standby(inner, standby, seed=seed, episode=episode)
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
    contract = contract_manifest(system=system, reward=reward, attacker=attacker,
                                 spawn=spawn, standby=standby,
                                 randomize_threat=randomize_threat,
                                 threat_obs=threat_obs, extra_cfg=extra_cfg,
                                 cfg=cfg, dist_ref=dist_ref)
    return M4Stack(env=env, scn=scn, lay=lay, threat=threat, contract=contract)


def regime_of(a_att: float, tau: float, net_radius: float) -> str:
    """명제 N (docs/10) 기준 regime.

    `w = 0.5*a_att*tau^2` 가 `rho`(net_radius) 이하이면 조향 없이도 포획된다
    -- 조향의 방어가치가 0 이다. 위협 브래킷이 이 경계를 가로지르도록
    선언되어 있다 (docs/40 §8.1, a* = 2*rho/tau^2 = 44.4 m/s^2).
    """
    return ("SHAPING_NEEDED" if 0.5 * float(a_att) * float(tau) ** 2 > float(net_radius)
            else "FREE_CAPTURE")


def mission_eval(seed0: int, episodes: int, *,
                 system: SystemSpec, reward: RewardSpec,
                 attacker: Optional[AttackerSpec] = None,
                 spawn: Optional[SpawnSpec] = None,
                 policy: Optional[Callable] = None,
                 standby: Optional[StandbySpec] = None,
                 extra_cfg: Optional[dict] = None,
                 threat_layer: Optional[str] = None,
                 limiter_kw: Optional[dict] = None,
                 limiter_mode: str = "hold", fire_mode: str = "clean",
                 randomize_threat: bool = True, threat_obs: bool = True,
                 baseline_commit: bool = False,
                 records: Optional[list] = None,
                 scripted_roles: Sequence[str] = (),
                 mobility: float = 0.0,
                 omega_max: float | None = None) -> dict:
    """2층 임무 지표 (docs/29 §4) — regime 별로 쪼개서 낸다.

    **`interdiction_rate = 1 - PENETRATED` 를 그대로 쓰지 않는다.**
    그 정의는 SPENT_FAIL(탄 소진·미무력화)과 TRUNCATED(우측 절단)를 성공으로
    세므로 부풀려진다 (docs/40 §8.2 각주). 여기서는 분해해서 보고한다.

    `scripted_roles` 는 역할 분리(docs/48)용 -- `policy` 가 있어도 그 역할만
    스크립트로 덮어쓴다. 기본 `()` 이면 기존 호출부와 bit-identical.

    `mobility` 는 이동성 요인 실험(docs/51)용 포획기 병진 가속 상한이다.
    **기본 0.0 = 고정** -> 지금까지의 모든 결과가 난 조건이고 bit-identical.
    0 이 아니면 `apply_mobility` 가 명령·백엔드 클램프를 **함께** 푼다.
    `omega_max` 는 조준 슬루 상한 override 다 (기본 None = 건드리지 않음).

    초기조건과 공격자 난수는 `mobility`·`omega_max` 와 무관하게 `(seed0, ep)` 로만
    정해지므로 이 인자만 바꾼 호출들은 전부 **paired CRN** 이다 (P73).

    `standby`/`extra_cfg` 는 `build_m4_env` 로 그대로 전달된다 (docs/65 A3 --
    종전에는 버려져서 v3 스펙을 줘도 **조용히 legacy 기하**로 평가됐다).
    기본 None = 기존 호출부와 bit-identical. 반환 dict 의 `contract` 키가
    실제로 평가된 세계의 resolved manifest 다 (A4a).

    `threat_layer` ("train"/"iid") 를 주면 에피소드별 `draw_threat_v3` 로
    구성된다 (docs/61; 점 스펙 인자와 동시 사용 금지 -- build_m4_env 가
    거부한다). IID episode 대역 분리(10000..)는 호출자 규율 (docs/61 §3).
    """
    from shepherd.agents.mobile_finisher import apply_mobility, apply_slew_limit
    from shepherd.scripts.mission_rollout import LABELS, run_episode

    counts = {lab: 0 for lab in LABELS}
    by_regime: Dict[str, Dict[str, int]] = {}
    contract: Optional[dict] = None
    for ep in range(episodes):
        st = build_m4_env(seed0, ep, system=system, reward=reward,
                          attacker=attacker, spawn=spawn, standby=standby,
                          extra_cfg=extra_cfg, threat_layer=threat_layer,
                          randomize_threat=randomize_threat, threat_obs=threat_obs)
        if contract is None:
            contract = st.contract
        if mobility > 0.0:
            apply_mobility(st.env, a_max=mobility)
        if omega_max is not None:                  # 무한 슬루 반사실 (docs/51 §9)
            apply_slew_limit(st.env, omega_max)
        r = run_episode(st.env, st.scn, st.lay, seed=seed0 + ep,
                        limiter_mode=limiter_mode, fire_mode=fire_mode,
                        policy=policy, baseline_commit=baseline_commit,
                        scripted_roles=scripted_roles, limiter_kw=limiter_kw)
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
            "by_regime": {k: _split(v) for k, v in by_regime.items()},
            "contract": contract}
