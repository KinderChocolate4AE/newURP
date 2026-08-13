"""M4 시스템 레인 — 하드킬 방아쇠 · no-kinetic zone · 5분할 결과 (docs/29 v3).

설계 (docs/29 §3, v3)
--------------------
**모드 상태기계를 두지 않는다.** 시스템에 실제로 있는 것은:

    limiter    연속 가속 3차원  +  이산 커밋 비트 1개
    finisher   연속 포인팅 3차원 +  이산 발사 비트 1개

위치 제어는 이미 전부 연속이고, 이산인 것은 되돌릴 수 없는 마지막 방아쇠뿐이다.
전이 조건을 손으로 짜는 순간 학습시키려던 중재를 스크립트로 되돌리게 되므로,
모드는 **측정 대상**이지 설계 입력이 아니다.

방아쇠 = **학습 제안 + env 가드 거부권** (네트 fire gate 와 동일한 리포 패턴):

    정책이 커밋 제안 (limiter Box(4) idx 3 > 0.5)      <- 기존 RESERVED 차원
       ↓
    env 가드 거부권
        R_nk 안에서 해소   -> 거부, limiter 미소모     (해소 시점 기준, 사전 확정)
        기하 조건 불가     -> 실패, limiter 소모
        기하 ∧ Bernoulli(Pk) -> HARD_KILL

왜 래퍼인가 (docs/29 §6)
-----------------------
하드킬은 **종료 규칙**을 바꾸므로 백엔드 프록시로는 부족하다(프록시는 env 가 반환하는
`terms` 를 못 바꾼다). 그렇다고 `env_m3` 식 서브클래스 + step() 163줄 복사는 하지
않는다 -- 리포에 복사본이 3개가 된다. 대신 **env 바깥에 래퍼**를 둔다.

    env_sys.py     방아쇠·가드·종료      (이 파일, 래퍼)
    env.py         물리·viability·FSM     (동결, 무수정)
    env_adv.py     공격자 주입            (백엔드 프록시)

셋이 서로 다른 경계에서 작동하므로 조합된다.

하드킬 기하 조건 (docs/29 §2.1, 보수적 worst-case)
------------------------------------------------
커밋 시점에 동결한다 (네트의 S5 robust judge 가 발사 시점에 동결하는 것과 동일 규약):

    r = p_att - p_lim,  v = v_att - v_lim            (커밋 시점)
    d_nom = |r + v * tau_kill|
    기하:  d_nom <= r_kill + 0.5*(a_lim - a_att)*tau_kill^2

`a_lim == a_att` 이면 여유항이 사라져 `d_nom <= r_kill` 로 퇴화한다.

torch-free.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from shepherd.game.finisher_fsm import FinisherState

__all__ = ["SystemSpec", "RewardSpec", "CommitRecord", "ModeSystemEnv",
           "PARK_POSITION", "ratified_system"]

_EPS = 1e-12

# 소진 limiter 주차점. 회랑(x in [0, 24], ring x=8)에서 충분히 멀어 v_shot 기여가 0.
# 모델링 선택으로 명시한다 (docs/29 §3.2 -- 은닉 금지).
#
# ★ 2026-08-03 P2 수정 — 1.0e4 -> 60.0.
# 주차 좌표는 **관측에 그대로 실린다**(env.py:203-213) 그리고 학습기의 RunningNorm 이
# 매 스텝 그것으로 갱신된다(train_mappo.py:143). z=1e4 로 두면 롤아웃 256 스텝만에
# limiter pz 채널이 mean 7500 / std 4330 이 되어 **살아있는 limiter 의 면외 좌표가
# 정상 채널 대비 517배 압축**된다 — 링 배치가 (8,±5,0),(8,0,±5) 이므로 편대 기하의
# 절반이 지워진다. RunningNorm 은 망각 없는 누적이라 회복 불가이고, 단 1판만 주차해도
# 100배 압축된다. (커밋이 불가능하던 시절에는 `retired` 가 항상 비어 잠들어 있던 결함.)
#
# 60.0 을 고른 근거 (튜닝 아님 -- 두 부등식이 동시에 성립하는 자릿수):
#   ① v_shot 기여 0: 공격자 궤적은 회랑 x∈[0,26]·|yz|≲6 안에 있고 도달집합 반경은
#      최대 ½·a_att_max·tau^2 = ½·78·0.3^2 = 3.51 m. 어떤 궤적점과도 50 m 이상
#      떨어지므로 no-go 반경 kill_radius(0.75)에 절대 닿지 않는다. 콘 range_max 8.22 밖.
#   ② 정규화 생존: 링 반경 5 m 의 12배 -- live 변동이 압축되지 않는다.
# P2 테스트가 ①(주차 전후 v_shot 동일)을 강제한다.
PARK_POSITION = (0.0, 0.0, 60.0)


@dataclass(frozen=True)
class SystemSpec:
    """M4 방아쇠·구역 파라미터. 전부 선언값이며 sweep 축은 그렇게 표기."""
    tau_kill: float = 0.15       # s. 2026-07-29 재선언 (docs/42): 기존 근거
                                 # "tau_deploy(0.4)의 1/4" 은 tau=0.30 이 되며 고아가 됐다.
                                 # tau 분해의 sense(0.10)+decide(0.05)=0.15 는 **같은
                                 # 센싱 사슬**이므로 하드킬 효과기에도 적용된다 -> 하한 0.15.
                                 # dt 격자 위(3틱). 하드킬을 약화시키는 불리한 방향.
                                 # {0.15, 0.20} 은 선언된 sweep 축 -- 2차 지표(비손실 비율)가
                                 # tau_kill 의 산물이 아님을 보이기 위해 필요하다.
    p_kill: float = 1.0          # 선언된 SWEEP 축. Bernoulli(Pk)
    r_nk: float = 6.0            # m. no-kinetic zone 반경 (자산 중심)
    a_lim_max: Optional[float] = None   # None -> scenario.limiter.a_max
    commit_threshold: float = 0.5       # Box(4) idx3 임계 (env fire logit 과 동일 규약)
    enabled: bool = True         # False -> 동결 env 와 bit-identical (P6)
    # R1 접촉 event resolver (docs/54 §1). 기본 off -> 기존 경로와 bit-identical (P78).
    contact_resolver: bool = False
    # ★ 반경 3종 의미 분리 (리뷰 3 -- 값이 아니라 설정 키를 먼저 분리한다):
    #     r_shape    viability surrogate 의 escape suppression 반경
    #                = scenario.limiter.kill_radius (동결 env 소관, 여기 키 없음)
    #     r_commit   예측 커밋 기하의 허용 반경 (margin 식의 기저)
    #     r_contact  실제 접촉 event 반경
    #   둘 다 None -> inner.kill_radius (전부 0.75, 기존과 bit-identical).
    #   수치 calibration 은 별도 실험 후 -- 지금은 배선 분리만.
    r_commit: Optional[float] = None
    r_contact: Optional[float] = None
    # R2 net-miss handoff (docs/54 §1). 기본 True = 현행(miss -> SPENT_FAIL 종료).
    # False 면 spent-fail 종료만 억제하고 에피소드가 계속된다 (FALLBACK).
    miss_terminates: bool = True
    # ★ R3 sham-net counterfactual (docs/83 §10.2). 기본 True = 현행(capture -> 종료).
    #   False 면 **성공한 net capture 의 종료와 무력화 효과만** 억제하고
    #   commit · 공격자 commit-응답(dodge ON / jink OFF / route 유지) ·
    #   finisher SPENT/K=0 · 하드킬 · 침투 · 절단 · RNG stream 은 전부 보존한다.
    #   근거(§12A.1 trace): 동결 env 에서 capture 는 **순수 terminal label** 이고
    #   백엔드 상태(p,v,e)를 바꾸지 않는다 -> R2 와 동일한 기계로 충분하다.
    #   E2-B 전용이며 miss_terminates=False (ratified) 와 함께 쓰는 것이 전제다.
    capture_terminates: bool = True
    # ★ E1d commit geometry intervention (docs/83 §15). 기본 None/False = 무동작.
    #   force_commit_step: 그 스텝에서 발사 자격 술어를 **정확히 1 발** 우회한다
    #     (do(F=1)). theta_fire 를 영구히 0 으로 두는 것이 아니라 그 한 스텝만
    #     교체 후 복원하며, fire_cmd 도 함께 세운다 -- 나머지 파라미터 불변.
    #   perfect_aim_at_commit: 그 스텝 판정 **직전** finisher heading 을
    #     unit(p_coast - p_fin) 로 설정해 psi=0 을 만든다 (mechanism isolation).
    #     env.py 는 vfull 을 스텝 시작 상태로 계산하므로 여기서 쓰면 판정에 반영된다.
    force_commit_step: Optional[int] = None
    perfect_aim_at_commit: bool = False
    seed_ns: str = "m4_hardkill"


def ratified_system(**overrides) -> SystemSpec:
    """비준 계약 SystemSpec — R1 contact resolver on · R2 miss handoff on.

    docs/53-54 가 구계약(접촉 무력화 없음 · miss 즉시 종료)을 "구현 비정합" 으로
    판정했고, v2/v3 측정 사슬은 전부 이 F-flags 로 돈다. 학습·평가·스윕도 같은
    계약에서 파생돼야 한다 (docs/65 §2-1 contract parity, A1/A2).

    SystemSpec 의 필드 **기본값은 바꾸지 않는다** (legacy 재현 경로 보존) --
    같은 실험 family 에 속하는 runner 가 여기서 명시적으로 파생할 뿐이다.
    """
    return SystemSpec(enabled=True, contact_resolver=True,
                      miss_terminates=False, **overrides)


@dataclass(frozen=True)
class RewardSpec:
    """M4 보상 (docs/29 §15). **`w_kill` 이 유일한 핵심 노브이며 선언된 sweep 축이다.**

    형태:
        J_M4 = dense_scale * J_env            (기존 조밀 신호: dv_shot + clean - waste - contact)
             + terminal_scale * TERMINAL      (에피소드 종료 1회)
             - c_lim * (소모된 limiter 수)

        TERMINAL   NET_CAPTURE            +b_net
                   CAPTURE_WITH_CONTACT   +b_net   <- docs/66 r1 (Q1): 동일
                                                      nondestructive utility class
                   HARD_KILL              +b_net*(1 - w_kill)
                   PENETRATED             -c_pen
                   TRUNCATED              -c_trunc <- 지평선 미격퇴 = 보상상 실패

    **보상과 지표를 분리한다**: 학습에서는 TRUNCATED 를 미격퇴로 벌하지만, 보고 지표는
    우측 절단(censored)으로 유지한다(docs/26). 둘을 같게 맞출 이유가 없고, 섞으면
    "지평선이 짧아서 이긴 것처럼 보이는" 산물이 생긴다.

    순서 불변식 (테스트로 강제): 모든 `w_kill in [0,1]` 에서
        NET_CAPTURE = CAPTURE_WITH_CONTACT >= HARD_KILL > PENETRATED = TRUNCATED
    `w_kill=0` 이면 두 성공이 동등 -> 정책은 쉬운 쪽(하드킬)을 고른다.
    `w_kill=1` 이면 하드킬 보상 0 -> 소모 비용만 남아 비손실만 값어치.
    **그 사이 어디서 뒤집히는지가 논문의 결과다** -- 값을 하나 골라 튜닝하지 않는다.

    알려진 한계 (docs/29 §15.2): 기존 `coma_D` 는 `v_shot_soft` 차분으로 계산되므로
    **커밋 차원에는 반대사실 credit 이 없다.** 배치 차원만 COMA 가 덮는다.
    """
    b_net: float = 1.0
    w_kill: float = 0.5          # <- 선언된 SWEEP 축
    c_pen: float = 1.0
    c_trunc: float = 1.0
    c_lim: float = 0.1
    dense_scale: float = 1.0
    terminal_scale: float = 1.0   # 2026-08-01 재선언. 기존 10.0 은 [E] 스케일 스모크
                                  # (docs/41) 이전 값이고, 그 실측이 sum|dense| 평균 1.00
                                  # (|TERMINAL| 최대 1.0) 을 보여 **같은 자릿수**임을
                                  # 확인했다 -> 10 은 종말항을 10배 과대평가한다.
                                  # 선언은 docs/41 에서 이미 났고 CLI 기본값만 1.0 으로
                                  # 고쳐져 있었다. 즉 선언값이 두 군데로 갈라져 있었고
                                  # (dataclass 10.0 / CLI 1.0) RewardSpec() 을 직접 만드는
                                  # 모든 호출부가 낡은 값을 받고 있었다. 선언은 여기 하나뿐.
                                  # P40c 가 CLI 와의 일치를 강제한다.
                                  # 2026-08-03: 리팩터 중 10.0 으로 되돌아간 적이 있다
                                  # (P40c 가 잡음). **이 줄은 손대지 않는다.**
    enabled: bool = False        # 기본 off -> 기존 보상 그대로 (P6 bit-identical 보존)

    def terminal(self, label: str) -> float:
        # ★ docs/66 r1 비준 (Q1): CAPTURE_WITH_CONTACT 는 nondestructive-capture
        #   utility class -- NET_CAPTURE 와 동일 +b_net. B1 trace 가 같은 tick
        #   destructive KILL 은 항상 HARD_KILL 로 라벨됨을 확인했으므로 CWC 에
        #   파괴 혼입 경로가 없다. 종전에는 명시 분기가 없어 아래 else 로
        #   떨어져 **우연히 0** 이었다 (감사 blocker 3).
        if label in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT"):
            return self.b_net
        if label == "HARD_KILL":
            return self.b_net * (1.0 - self.w_kill)
        if label == "PENETRATED":
            return -self.c_pen
        if label == "TRUNCATED":
            return -self.c_trunc
        return 0.0               # SPENT_FAIL: 의미 감사 전까지 중립 (docs/26)


@dataclass
class CommitRecord:
    """한 번의 요격 커밋. 판정에 필요한 상태를 커밋 시점에 동결한다.

    R1(docs/54 §1) 이후 접촉 event 도 이 record 를 재사용한다 -- `source` 가
    provenance("commit" | "contact")이고, 접촉은 d_nom=d_min · margin=r_contact ·
    geometric_ok=True(접촉 자체가 기하) · 즉시 해소로 채운다. 라벨 어휘는 공유.
    """
    limiter_index: int
    commit_step: int
    resolve_step: int
    d_nom: float
    margin: float                 # r_kill + 0.5*(a_lim - a_att)*tau_kill^2
    geometric_ok: bool
    resolved: bool = False
    outcome: str = ""             # KILL | GEOM_FAIL | PK_FAIL | VETO_NO_KINETIC
    consumed: bool = False
    source: str = "commit"        # "commit" | "contact" (R1 provenance, docs/54)


def _seg_min_dist(r0, r1) -> float:
    """상대 위치 선분 r0->r1 과 원점 사이 최소거리 (swept contact, docs/54 §1).

    endpoint 만 검사하면 한 스텝 안의 kill_radius 통과를 놓친다. 백엔드 적분은
    등가속(곡선)이므로 선분은 **근사**다 -- 이산 격자 계약과 같은 지위 (오류 9).
    """
    r0 = np.asarray(r0, float)
    d = np.asarray(r1, float) - r0
    dd = float(d @ d)
    t = 0.0 if dd < _EPS else float(np.clip(-(r0 @ d) / dd, 0.0, 1.0))
    return float(np.linalg.norm(r0 + t * d))


class ModeSystemEnv:
    """동결 env 를 감싸 하드킬 방아쇠와 no-kinetic 가드를 얹는다.

    PettingZoo ParallelEnv 인터페이스를 유지하고, 정의하지 않은 속성은 전부 inner
    로 위임한다 (limiter_ids / _states / _p / fsm / kill_radius / ...).
    """

    def __init__(self, inner, layout, scenario, spec: SystemSpec = SystemSpec(),
                 reward: RewardSpec = RewardSpec()):
        self.inner = inner
        self.layout = layout
        self.sc = scenario
        self.spec = spec
        self.reward_spec = reward
        self.a_lim_max = (spec.a_lim_max if spec.a_lim_max is not None
                          else float(scenario.limiter.a_max))
        self.n_kill = max(int(round(spec.tau_kill / float(inner.dt))), 1)
        self._reset_state()

    # ------------------------------------------------------------------ state
    def _reset_state(self):
        self.commits: List[CommitRecord] = []
        # ★ 2026-08-03 P3 수정 — 이미 벌점을 매긴 소모 개수.
        #   `rew` 재작성은 **매 스텝** 실행되는데 `n_consumed` 는 에피소드 누적이라,
        #   limiter 를 t 스텝에 소모하면 남은 (T−t) 스텝 내내 −c_lim 이 계속 붙었다.
        #   실측 누적 벌점 평균 7.51~9.42 (선언 의도 0.40, |종말항| 최대 1.0)
        #   = 소모 벌점 하나가 나머지 전 학습 신호의 7~17배.
        #   docstring §15 는 처음부터 **1회 부과** 형태였다 -- 구현을 선언에 맞춘다.
        self._charged: int = 0
        self.retired: set = set()
        self.pending: Dict[int, CommitRecord] = {}
        self.hard_kill = False
        self.veto_events = 0
        self.net_spent = False            # R2: net miss 후 FALLBACK 진입 여부
        self.net_spent_step: Optional[int] = None
        self.sham_capture = False         # R3: capture 종료가 억제됐는가 (docs/83 §10.2)
        self.sham_capture_step: Optional[int] = None
        self._step_i = 0
        self._seed = 0

    def _bern(self, limiter_index: int, step: int) -> bool:
        """재현 가능한 Bernoulli(Pk). SHA-256 -- 파이썬 hash() 금지."""
        if self.spec.p_kill >= 1.0:
            return True
        if self.spec.p_kill <= 0.0:
            return False
        key = f"{self.spec.seed_ns}|{self._seed}|{limiter_index}|{step}"
        h = hashlib.sha256(key.encode()).digest()
        u = int.from_bytes(h[:8], "big") / 2 ** 64
        return u < self.spec.p_kill

    # -------------------------------------------------------------------- API
    def reset(self, seed=None, options=None):
        self._reset_state()
        self._seed = 0 if seed is None else int(seed)
        return self.inner.reset(seed=seed, options=options)

    def step(self, actions):
        inner = self.inner
        spec = self.spec
        self._step_i += 1

        if not spec.enabled:
            return inner.step(actions)

        # --- 1. 커밋 제안 수집 (env 는 idx3 을 어차피 무시한다) ---------------
        lims, fin, att = inner._states()
        p_att, v_att = inner._p(att), inner._v(att)
        proposals: List[int] = []
        for i, lid in enumerate(inner.limiter_ids):
            if i in self.retired or i in self.pending:
                continue
            a = np.asarray(actions.get(lid, np.zeros(4)), float)
            if len(a) >= 4 and float(a[3]) > spec.commit_threshold:
                proposals.append(i)

        # --- 2. 커밋 시점에 판정 상태를 동결 (네트 S5 규약과 동일) ------------
        r_commit = (float(spec.r_commit) if spec.r_commit is not None
                    else float(inner.kill_radius))
        margin = (r_commit
                  + 0.5 * (self.a_lim_max - inner.a_att_max) * spec.tau_kill ** 2)
        for i in proposals:
            p_lim, v_lim = inner._p(lims[i]), inner._v(lims[i])
            rel_p = p_att - p_lim
            rel_v = v_att - v_lim
            d_nom = float(np.linalg.norm(rel_p + rel_v * spec.tau_kill))
            rec = CommitRecord(limiter_index=i, commit_step=self._step_i,
                               resolve_step=self._step_i + self.n_kill,
                               d_nom=d_nom, margin=float(margin),
                               geometric_ok=bool(d_nom <= margin))
            self.commits.append(rec)
            self.pending[i] = rec

        # --- 2b. E1d 강제 커밋 (docs/83 §15) -- 기본 off ---------------------
        forced_now = (spec.force_commit_step is not None
                      and self._step_i == int(spec.force_commit_step))
        _saved_sc = None
        if forced_now:
            from dataclasses import replace as _replace
            if spec.perfect_aim_at_commit:
                lims_f, fin_f, att_f = inner._states()
                p_a, v_a = inner._p(att_f), inner._v(att_f)
                r = (p_a + v_a * float(inner.tau_deploy)) - inner._p(fin_f)
                rn = float(np.linalg.norm(r))
                if rn > 1e-9:
                    inner.backend.by_name(inner.finisher_id).e = r / rn
            fa = np.asarray(actions.get(inner.finisher_id, np.zeros(5)), float).copy()
            if fa.size >= 5:
                fa[4] = 1.0                      # do(F=1)
                actions = dict(actions)
                actions[inner.finisher_id] = fa.astype(np.float32)
            _saved_sc = inner.sc                 # 자격 술어 우회 (한 스텝만)
            inner.sc = _replace(inner.sc, fire_gate=_replace(
                inner.sc.fire_gate, theta_fire=0.0, c_fire=0.0))

        # --- 3. 동결 env 를 그대로 한 스텝 -----------------------------------
        obs, rew, terms, truncs, infos = inner.step(actions)
        if _saved_sc is not None:
            inner.sc = _saved_sc                 # 즉시 복원

        # --- 3b. net-miss handoff (R2, docs/54 §1) -- 기본 off ---------------
        # spent-fail 종료(= 종료 ∧ ¬captured ∧ ¬penetrated ∧ fsm SPENT)만 억제.
        # captured / penetrated / hard_kill 종료는 절대 억제하지 않는다.
        # inner 는 spent_fail 이 지속돼 매 스텝 재종료를 시도하므로 net_spent
        # 동안 매번 억제하고, 자체 절단이 막히므로 지평선 절단은 래퍼가 낸다.
        handoff_now = False
        if not spec.miss_terminates and any(terms.values()):
            fi = next(iter(infos.values()), {})
            if (not fi.get("captured") and not fi.get("penetrated")
                    and inner.fsm.state is FinisherState.SPENT):
                if not self.net_spent:
                    self.net_spent = True
                    self.net_spent_step = self._step_i
                    handoff_now = True
                terms = {a: False for a in terms}
                inner.agents = list(inner.possible_agents)
                if self._step_i >= int(self.layout.episode_len):
                    truncs = {a: True for a in truncs}   # 동결 env 와 같은 지평선

        # --- 3c. R3 sham-net (docs/83 §10.2) -- 기본 off ---------------------
        # **성공한 capture 의 종료만** 억제한다. capture 는 동결 env 에서 순수
        # terminal label 이고 백엔드 상태를 바꾸지 않으므로(§12A.1 trace) R2 와
        # 같은 기계로 충분하다. 조건에 `not penetrated` 를 넣어 동시 발생 시
        # **침투 종료가 우선**하게 한다.
        # 다음 스텝부터는 resolved=False -> captured=False 이고 fsm 은 SPENT 이므로
        # **비준된 R2 억제 조건에 그대로 걸린다** -- 신규 코드는 이 한 스텝만 담당.
        sham_now = False
        if not spec.capture_terminates and any(terms.values()):
            fi = next(iter(infos.values()), {})
            if fi.get("captured") and not fi.get("penetrated"):
                if not self.sham_capture:
                    self.sham_capture = True
                    self.sham_capture_step = self._step_i
                    sham_now = True
                if not self.net_spent:        # 네트는 **실제로** 소모됐다 (K=0 유지)
                    self.net_spent = True
                    self.net_spent_step = self._step_i
                terms = {a: False for a in terms}
                inner.agents = list(inner.possible_agents)
                if self._step_i >= int(self.layout.episode_len):
                    truncs = {a: True for a in truncs}   # 동결 env 와 같은 지평선

        # --- 4. 만료 커밋 해소: 가드 -> 기하 -> Pk ---------------------------
        lims2, _, att2 = inner._states()
        p_att2 = inner._p(att2)
        d_asset = float(np.linalg.norm(p_att2 - np.asarray(self.layout.target, float)))
        resolved_now: List[CommitRecord] = []
        for i, rec in list(self.pending.items()):
            if self._step_i < rec.resolve_step:
                continue
            rec.resolved = True
            del self.pending[i]
            resolved_now.append(rec)

            # 가드 거부권: no-kinetic zone. **해소 시점 기준** (사전 확정),
            # 거부되면 limiter 는 소모되지 않는다.
            if d_asset <= spec.r_nk:
                rec.outcome = "VETO_NO_KINETIC"
                rec.consumed = False
                self.veto_events += 1
                continue

            rec.consumed = True                 # 이하 전부 limiter 소모
            self.retired.add(i)
            if not rec.geometric_ok:
                rec.outcome = "GEOM_FAIL"
            elif self._bern(i, rec.commit_step):
                rec.outcome = "KILL"
                self.hard_kill = True
            else:
                rec.outcome = "PK_FAIL"

        # --- 4b. 접촉 event resolver (R1, docs/54 §1) -- 기본 off ------------
        # 커밋 해소가 먼저다: pending limiter 는 접촉 검사에서 제외 (커밋은 바로
        # 그 접촉의 예측이므로 이중 소모 금지). 라벨 신설 없음 -- KILL 이면 기존
        # hard_kill 경로 그대로 HARD_KILL.
        contact_events: List[CommitRecord] = []
        if spec.contact_resolver:
            contact_events = self._resolve_contacts(
                p_att, [inner._p(s) for s in lims],
                p_att2, [inner._p(s) for s in lims2], d_asset)

        # --- 5. 소진 limiter 주차 (다음 스텝부터 v_shot 기여 0) --------------
        for i in self.retired:
            try:
                ag = inner.backend.by_name(inner.limiter_ids[i])
                ag.p = np.asarray(PARK_POSITION, float).copy()
                ag.v = np.zeros(3)
            except Exception:                                  # pragma: no cover
                pass

        # --- 6. 종료·info 주입 ------------------------------------------------
        if self.hard_kill:
            terms = {a: True for a in terms}
            truncs = {a: False for a in truncs}

        # --- 6b. M4 보상 (docs/29 §15) ---------------------------------------
        rs = self.reward_spec
        label = None
        if rs.enabled:
            done = any(terms.values()) or any(truncs.values())
            if done:
                label = self._outcome_label(terms, truncs, infos)
            n_consumed = sum(1 for r in self.commits if r.consumed)
            # ★ P3: **이번 스텝에 새로 소모된 개수**에만 부과한다 (증분).
            #   에피소드 전체 합 = c_lim × (총 소모 개수) 로 docstring §15 와 일치.
            new_consumed = n_consumed - self._charged
            self._charged = n_consumed
            bonus = (rs.terminal_scale * rs.terminal(label)) if label else 0.0
            rew = {a: (rs.dense_scale * float(v) + bonus - rs.c_lim * new_consumed)
                   for a, v in rew.items()}
        sysinfo = dict(
            m4_outcome=label,
            hard_kill=self.hard_kill,
            n_committed=len(self.commits),
            n_retired=len(self.retired),
            n_pending=len(self.pending),
            veto_events=self.veto_events,
            d_asset=d_asset,
            in_no_kinetic_zone=bool(d_asset <= spec.r_nk),
            resolved=[(r.limiter_index, r.outcome, round(r.d_nom, 4),
                       round(r.margin, 4)) for r in resolved_now],
            contacts=[(r.limiter_index, r.outcome, round(r.d_nom, 4))
                      for r in contact_events],
            net_spent=self.net_spent,           # R2 provenance ("net spent before failure")
            net_miss_handoff=handoff_now,       # 전이 스텝에만 True. terminal 집계 금지
            # R3 provenance (docs/83 §10.2). would_capture 는 **억제가 일어난 그
            # 스텝에만** True -- terminal 로 집계하지 말고 "포획이 성립했었다" 는
            # 사실의 기록으로만 쓴다.
            forced_commit=forced_now,            # E1d provenance (그 스텝에만 True)
            would_capture=sham_now,
            sham_capture=self.sham_capture,
            sham_capture_step=self.sham_capture_step,
        )
        for a in infos:
            infos[a] = {**infos[a], **sysinfo}
        return obs, rew, terms, truncs, infos

    def _resolve_contacts(self, p_att_pre, lims_pre, p_att_post, lims_post,
                          d_asset: float) -> List[CommitRecord]:
        """R1 접촉 event resolver (docs/54 §1). 이번 스텝의 contact records 반환.

        ★ 의미 (docs/57 감사 판정 B): 이 event 는 물리 충돌이 아니라 **근접
        kinetic engagement opportunity** 다 — kill_radius 는 폭발형 카미카제
        요격의 실행 반경(roles.py:26)이고 backend 에 충돌 물리는 없다. NK veto
        = 기폭 보류 (docs/29 §13 파괴적 요격 금지). 그래서 veto 시 미소모가
        인과적으로 맞다. "contact" 명칭 정정(→engagement)은 별도 chore.

        해소 사슬은 커밋 경로와 동일: NK veto(미소모, 재접촉 시 재평가) ->
        소모·retire -> Bernoulli(Pk). 즉시 해소 (tau_kill 지연 없음 -- 지연은
        예측 요격의 sense+decide 모형이고 접촉은 이미 일어난 사건이다).
        KILL 1회 후 잔여 접촉 미평가 (terminal success 1회).
        """
        spec = self.spec
        r_contact = (float(spec.r_contact) if spec.r_contact is not None
                     else float(self.inner.kill_radius))
        events: List[CommitRecord] = []
        for i in range(len(lims_pre)):
            if self.hard_kill:
                break
            if i in self.retired or i in self.pending:
                continue
            d_min = _seg_min_dist(np.asarray(p_att_pre, float) - np.asarray(lims_pre[i], float),
                                  np.asarray(p_att_post, float) - np.asarray(lims_post[i], float))
            if d_min > r_contact:
                continue
            rec = CommitRecord(limiter_index=i, commit_step=self._step_i,
                               resolve_step=self._step_i, d_nom=d_min,
                               margin=r_contact, geometric_ok=True,
                               resolved=True, source="contact")
            self.commits.append(rec)
            events.append(rec)
            if d_asset <= spec.r_nk:            # 커밋과 같은 거부권 (해소 시점 기준)
                rec.outcome = "VETO_NO_KINETIC"
                self.veto_events += 1
                continue
            rec.consumed = True
            self.retired.add(i)
            if self._bern(i, self._step_i):
                rec.outcome = "KILL"
                self.hard_kill = True
            else:
                rec.outcome = "PK_FAIL"
        return events

    def _outcome_label(self, terms, truncs, infos):
        """보상용 결과 라벨. mission_rollout 의 라벨 규칙과 같은 술어를 쓴다."""
        fi = next(iter(infos.values()), {})
        if self.hard_kill:
            return "HARD_KILL"
        if fi.get("captured"):
            contacted = any(
                float(np.linalg.norm(self.inner._p(self.inner._states()[2])
                                     - self.inner._p(s))) <= self.inner.kill_radius
                for s in self.inner._states()[0])
            return "CAPTURE_WITH_CONTACT" if contacted else "NET_CAPTURE"
        if fi.get("penetrated"):
            return "PENETRATED"
        if any(truncs.values()):
            return "TRUNCATED"
        return "SPENT_FAIL"

    # ------------------------------------------------------- 위임 + 헬퍼 -----
    def __getattr__(self, name):
        return getattr(self.__dict__["inner"], name)

    @property
    def kill_events(self) -> List[CommitRecord]:
        return [r for r in self.commits if r.outcome == "KILL"]

    def summary(self) -> dict:
        out = {k: 0 for k in ("KILL", "GEOM_FAIL", "PK_FAIL", "VETO_NO_KINETIC")}
        for r in self.commits:
            if r.outcome:
                out[r.outcome] += 1
        out["committed"] = sum(1 for r in self.commits if r.source == "commit")
        out["consumed"] = sum(1 for r in self.commits if r.consumed)
        out["contact_events"] = sum(1 for r in self.commits if r.source == "contact")
        return out


def make_system_env(inner, scenario, layout, spec: SystemSpec = SystemSpec()):
    """composition helper -- inner 는 이미 만들어진 ShapingParallelEnv."""
    return ModeSystemEnv(inner, layout, scenario, spec)
