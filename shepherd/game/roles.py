"""Role + resource specs (sim-agnostic, torch-free, no concrete-backend import).

- limiter:   cheap, cost-bearing kamikaze; explosive kill-radius = credible no-go
             threat that compresses the attacker's deploy-delay reachable set.
             A limiter is a *mobile constraint*, not a consumable missile; its loss
             is a cost term (S1).
- finisher:  ONE non-destructive net-capturer with a finite magazine K and an
             irreversible fire. A net-shot deploys after tau_deploy and locks for
             tau_lock. A missed commit CONSUMES the shot (wasted_fire) -- i.e. the
             shot is finite-magazine and miss-costly to the defender (R1). Net axis
             is reduced-attitude pointing: n_F = R_F . e_net, slew-rate limited by
             omega_max (R3 -- omega is a parameter, NOT a state dimension).
- adversary: goal-constrained (must penetrate) + evasive; see agents/adversary.py.

Physical spec VALUES are injected/read-only (assumptions register, configs/*.yaml),
never hardcoded. ScenarioSpec.from_dict consumes a parsed config dict.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True)
class LimiterSpec:
    """Cost-bearing shaping limiter (S1): a mobile no-go constraint."""
    kill_radius: float          # explosive kamikaze kill-radius [m]
    a_max: float                # setpoint/accel limit [m/s^2]
    loss_cost: float = 1.0      # per-limiter loss cost (reward lambda3 term)


@dataclass(frozen=True)
class FinisherSpec:
    """Finite-magazine, irreversible net-shot finisher (S1/S2/S3)."""
    K: int                      # finite magazine; the binding scarce resource (M2: K=1)
    tau_deploy: float           # net deploy delay [s]
    tau_lock: float             # post-fire lock [s]
    net_radius: float           # net capture radius [m]
    omega_max: float            # net-axis slew-rate limit [rad/s] (R3 parameter)
    e_net: tuple[float, float, float] = (1.0, 0.0, 0.0)   # initial net-pointing axis
    # ★ 2026-08-05 이동성 요인 실험 (docs/51). 0.0 = 위치 고정 = 지금까지의
    #   모든 결과가 난 조건. 기본값 0 이 회귀 방어다 -- 이 필드를 모르는
    #   호출부는 전부 고정 포획기를 그대로 받는다 (P69).
    a_max: float = 0.0          # 병진 가속 상한 [m/s^2]. 0 이면 병진 없음


@dataclass(frozen=True)
class AdversarySpec:
    """Bounded-maneuver, goal-constrained attacker (S3)."""
    a_att_max: float            # bounded accel [m/s^2]
    speed: float                # nominal forward speed [m/s]


@dataclass(frozen=True)
class FireGate:
    """Single fire-gate source of truth (R2): fire iff v_shot_soft >= theta_fire.

    The economic gate c_fire = theta_fire * B_capture is documented here and
    asserted for consistency; the runtime gate uses theta_fire alone.
    """
    theta_fire: float = 0.8
    B_capture: float = 1.0
    c_fire: float = 0.8

    def __post_init__(self) -> None:
        expected = self.theta_fire * self.B_capture
        if abs(self.c_fire - expected) > 1e-9:
            raise ValueError(
                f"fire_gate inconsistent (R2): c_fire={self.c_fire} != "
                f"theta_fire*B_capture={expected}"
            )


@dataclass(frozen=True)
class ViabilitySpec:
    """v_shot reachable-set surrogate config (commit 2)."""
    judge: str = "point_mass"   # {point_mass, se3_cone}
    turn_limited: bool = False  # False = single-segment constant-accel reachable set
    n_samples: int = 2000
    seed: int = 0
    n_segments: int = 1         # S14: 1 = legacy single-segment reachable set (bit-exact
                                # with the frozen prototype); >1 = conservative EXTREME-POINT
                                # union (boundary spheres + bang-bang doglegs) -- the
                                # trustworthy L2 training signal (over-approx, never optimistic).


@dataclass(frozen=True)
class RewardSpec:
    """S6 reward weights: J = dv_shot + l1*1[v>=theta] - l2*wasted_fire - l3*limiter_loss."""
    lambda1: float = 1.0
    lambda2: float = 1.0
    lambda3: float = 0.5


@dataclass(frozen=True)
class ScenarioSpec:
    """Full M2 scenario assembled from a parsed config dict (sim-agnostic)."""
    n_limiters: int
    n_adversaries: int
    dt: float
    limiter: LimiterSpec
    finisher: FinisherSpec
    adversary: AdversarySpec
    fire_gate: FireGate
    viability: ViabilitySpec
    reward: RewardSpec
    # fixed credit-assignment baselines (S8): names only, resolved by agents/env
    headline_u0: str = "hold_position"
    coma_u0: str = "hold_position"

    @classmethod
    def from_dict(cls, cfg: dict[str, Any]) -> "ScenarioSpec":
        """Build from a parsed configs/*.yaml mapping. Values are injected here."""
        sc = cfg["scenario"]
        ph = cfg["physics"]
        at = cfg["attitude"]
        fg = cfg["fire_gate"]
        vi = cfg["viability"]
        rw = cfg["reward"]
        bl = cfg.get("baselines", {})
        return cls(
            n_limiters=int(sc["n_limiters"]),
            n_adversaries=int(sc["n_adversaries"]),
            dt=float(ph["dt"]),
            limiter=LimiterSpec(
                kill_radius=float(ph["kill_radius"]),
                a_max=float(ph["a_lim_max"]),
            ),
            finisher=FinisherSpec(
                K=int(sc["finisher"]["K"]),
                tau_deploy=float(ph["tau_deploy"]),
                tau_lock=float(ph["tau_lock"]),
                net_radius=float(ph["net_radius"]),
                omega_max=float(at["omega_max"]),
                e_net=tuple(float(x) for x in at["e_net_init"]),  # type: ignore[arg-type]
            ),
            adversary=AdversarySpec(
                a_att_max=float(ph["a_att_max"]),
                speed=float(ph["att_speed"]),
            ),
            fire_gate=FireGate(
                theta_fire=float(fg["theta_fire"]),
                B_capture=float(fg["B_capture"]),
                c_fire=float(fg["c_fire"]),
            ),
            viability=ViabilitySpec(
                judge=str(vi["judge"]),
                turn_limited=bool(vi["turn_limited"]),
                n_samples=int(vi["n_samples"]),
                seed=int(vi["seed"]),
                n_segments=int(vi.get("n_segments", 1)),   # S14: optional; default 1 (legacy)
            ),
            reward=RewardSpec(
                lambda1=float(rw["lambda1"]),
                lambda2=float(rw["lambda2"]),
                lambda3=float(rw["lambda3"]),
            ),
            headline_u0=str(bl.get("headline_u0", "hold_position")),
            coma_u0=str(bl.get("coma_u0", "hold_position")),
        )
