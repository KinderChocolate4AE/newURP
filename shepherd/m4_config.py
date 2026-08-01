"""M4 운용점 — 동결 계약 위에 얹는 **선언된** 오버라이드, 한 곳에.

왜 이 파일인가
--------------
`configs/m2_l2_train.yaml` 과 `shepherd/params.py` 는 동결이다. M4 재학습은 그
계약을 바꾸지 않으면서 몇 개 값을 달리 써야 한다. `params.py` 가 설계한 방식이
정확히 이것이다:

    "FREEZE SAFETY. ... Experimenting = pass an `overrides` dict to as_config()
     (the frozen file stays untouched)."

오버라이드가 스크립트마다 흩어지면 (a) 무엇이 M4 운용점인지 아무도 모르고
(b) **결과를 본 뒤 조용히 바뀌는** 경로가 생긴다. 그래서 한 파일에 모으고,
**항목마다 날짜·근거·문서 참조를 남긴다.** 결과를 본 뒤 추가하지 않는다.

    from shepherd.m4_config import m4_config, m4_episode_config
    env, scn, lay = make_train_env(m4_config())                      # 고정 운용점
    env, scn, lay = make_train_env(m4_episode_config(seed, ep))      # + 위협 랜덤화

두 층으로 나뉜다
----------------
1. `M4_OVERRIDES`      에피소드 무관 고정값 (τ, kill_radius, 선회율, 지평선 ...)
2. `THREAT_BRACKET` + `CAPABILITY_RATIOS`
                       에피소드마다 위협 등급을 뽑고, **방어자 능력은 비율로 따라간다**

2층이 핵심이다. Pliska(RA-L)가 준 것은 절대값이 아니라 **비율**이므로
(요격기 가속/표적 가속 = 0.36, 속도 = 1.00), 위협이 흔들려도 비대칭은 보존된다.
C-2(FPV 스펙시트)가 나오면 브래킷 안의 한 점을 고르면 되고, 재학습은 안 막힌다.

torch-free.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional, Tuple

from shepherd.params import as_config

__all__ = ["M4_OVERRIDES", "M4_PROVENANCE", "TAU_DECOMPOSITION", "THREAT_BRACKET",
           "CAPABILITY_RATIOS", "SWEEP_AXES", "PENDING", "m4_config", "draw_threat",
           "m4_episode_config"]


# ===========================================================================
# 0. tau 분해 -- 커밋에서 포획 판정까지의 지연은 비행시간 하나가 아니다.
#    각 항이 외부 문헌 앵커이며 우리가 고를 수 있는 자유도가 아니다.
# ===========================================================================
TAU_DECOMPOSITION = {
    "tau_flight": (0.15, "Xu 2025 Fig.6 개방 0.13 s + 폐로 기하, dt 격자로 반올림. "
                         "네트가 실제로 나는 시간"),
    "tau_sense":  (0.10, "Pliska RA-L / Drones 10(6):420 -- LiDAR 10 Hz 1주기. "
                         "커밋 시점에 표적 위치는 최대 이만큼 낡아 있다"),
    "tau_decide": (0.05, "dt = 결정루프 1틱 (20 Hz)"),
}
# 제외한 항 (전부 tau 를 **키우는** 방향이므로, 우리 선언 0.30 은 하한이다):
TAU_OMITTED = {
    "tau_slew": "지향 오차 / omega=2 rad/s. 상태 의존이라 상수로 못 넣는다",
    "카메라 경로": "5 Hz 이면 tau_sense 가 0.20 s (LiDAR 대신). 더 보수적인 쪽을 안 씀",
}


# ===========================================================================
# 1. 고정 오버라이드. 항목 추가 = 날짜 + 근거 + 문서 참조를 함께 남긴다.
# ===========================================================================
M4_OVERRIDES: Dict[str, Any] = {
    "train.episode_len":          160,
    "physics.tau_deploy":         0.30,
    "physics.kill_radius":        0.75,
    "attitude.omega_max":         2.0,
    "train.limits.limiter_omega": 2.5,
    "train.layout.x_fire":        16.0,
    "viability.cone.range_max":   8.22,
    "viability.cone.half_angle":  0.2121,
    "physics.net_radius":         1.77,
}

M4_PROVENANCE: Dict[str, str] = {
    "train.episode_len": (
        "2026-07-29 · docs/37 §4 · 80 -> 160. "
        "스폰 랜덤화 후 ring 배치에서 TRUNCATED 13/30 (43%). H=160 에서 2/30, "
        "H=320 에서도 2/30 -> 수렴하므로 160 이 최소 충분 지평선. M4 보상이 "
        "TRUNCATED 에 -c_trunc 를 주므로 80 은 '시간이 끝나서' 벌하는 부기 산물을 "
        "만든다. 지평선은 물리 주장이 아니라 우리 부기 파라미터이므로 늘리는 쪽이 "
        "정직하다 (스폰 범위 축소는 결과를 보고 위협모형을 줄이는 것이라 금지)."
    ),
    "physics.tau_deploy": (
        "2026-07-29 · docs/40 §5 · 0.4 -> 0.30. **A1 선언 (분해 형태).** "
        "tau 는 커밋에서 포획 판정까지의 지연이고, **비행시간 하나가 아니다.** "
        "TAU_DECOMPOSITION 참조: flight 0.15 + sense 0.10 + decide 0.05 = 0.30. "
        "  · flight 0.15 = Xu Fig.6 개방 0.13 s + 폐로 기하, dt 격자 반올림 "
        "(0.13 을 그대로 쓰면 ceil(0.13/0.05)=3틱=0.15 로 +15.4% 양자화, docs/38 A8). "
        "  · sense 0.10 = LiDAR 10 Hz 1주기 (Pliska RA-L / Drones 10(6):420). "
        "커밋 시점에 표적 위치가 이만큼 낡아 있다는 것은 결과와 무관하게 참이다. "
        "  · decide 0.05 = 결정루프 1틱. "
        "0.30/0.05 = 6틱 정확 -- 격자 위(P29). "
        "**경위**: 처음에 tau=0.15(비행시간만)로 선언했더니 적형성 게이트에서 "
        "무개입(hold)이 12/12 를 잡아 조향 문제가 사라졌다. 명제 N 이 예측한 대로 "
        "w=0.5*a*tau^2 가 rho 이하였기 때문이다. 원인은 **tau 의 under-modeling** "
        "이었다 -- params.py 는 tau 를 'net deploy delay' 라고만 적고 분해한 적이 없다. "
        "**주의**: 분해는 전제(조향 필요성)를 복원하는 방향이라 self-serving 으로 "
        "보일 수 있다. 방어 논리는 (1) 각 항이 외부 문헌 값이라 우리 자유도가 아니고, "
        "(2) TAU_OMITTED(slew, 카메라 5 Hz)를 뺀 채이므로 **0.30 은 하한**이며, "
        "(3) 결과 방향과 무관하게 물리적으로 옳다는 것이다. 논문에 분해표를 명시한다. "
        "발사 설계는 Xu Table 1 baseline (45°, 60 m/s, 35 g). 그 등가면적 반경 1.997 m "
        "는 A3(최악방향)에서 1.77 로 다시 내려갔다 -- physics.net_radius 항목 참조."
    ),
    "physics.kill_radius": (
        "2026-07-29 · docs/34 §6 · 2.0 -> 0.75. **A7 선언.** "
        "기존 근거는 params.py 원문 '(no external grounding)' -- 없었다. "
        "학술 문헌에 살상반경 값이 없고(있는 것은 무기 카탈로그뿐, 추적 안 함), "
        "우리 하드킬은 탄두가 아니라 **충돌 요격**이므로 기하로 정의한다: "
        "표적 반치수 0.21 (420x420 mm, Drones 10(6):420) + 요격기 반치수 ~0.25 "
        "+ 종말 유도오차 0.10~0.40 (동 논문 위치오차 <10 cm, 탐지오차 <0.4 m) "
        "= 0.56 ~ 0.86 m. 중앙값 0.75 채택, 0.6~0.9 는 sweep 축. "
        "현행 2.0 은 부피로 12~46배 관대했다 -- **3제곱 지렛대**. "
        "하드킬을 약화시키는 불리한 방향이므로 결과 전 선언에 문제 없다."
    ),
    "attitude.omega_max": (
        "2026-07-29 · docs/34 §3.3 · 3.14159 -> 2.0. **A6 선언.** "
        "기존 값은 pi 를 그대로 쓴 것('half turn per second')이고 물리 근거가 아니었다. "
        "Pliska et al. (RA-L 2024, arXiv:2405.13542) 실기 요격기 최대 선회율 2 rad/s. "
        "2026-08-01 보강 (docs/45): 이 값은 **기체 선회율**인데 여기서는 **네트 지향축 "
        "slew** 로 쓰인다 -- 네트가 기체에 고정(body-fixed)이라는 축소자세 모형에서만 "
        "같다. 짐벌이면 더 빠르고, 그때 결론이 달라질 수 있으므로 SWEEP_AXES 에 올린다. "
        "**구속 여부 실측**: judge=se3_cone 이므로 lead 조준이 공짜가 아니라 이 값에 "
        "묶인 행동이다. hold 배치 · A1 공격자에서는 필요 시선각속도 omega_req=v_perp/d "
        "중앙값 0.043 rad/s 로 **완전 비구속(0.0%)**. 그러나 ring 배치에서는 공격자 "
        "횡속도가 0.44 -> 7.27 m/s 로 뛰며 **44.8% 에서 구속**한다. 즉 inert 였던 "
        "adversary_omega 와 달리 이 값은 운용점에 따라 결정적이다."
    ),
    "train.limits.limiter_omega": (
        "2026-07-29 · docs/34 §3.3 · 12.0 -> 2.5. **A6 선언.** "
        "기존 근거는 'demo-proven backend limit' = 데모가 돌았다는 뜻이지 물리가 아니다. "
        "Pliska 2 rad/s 대비 6배 과대였다. 2.5 는 finisher(2.0) 대비 약간의 여유."
    ),
    "viability.cone.range_max": (
        "2026-07-29 · 적형성 게이트 · 29.847 -> 8.22. **tau 선언의 필연적 귀결.** "
        "콘의 축방향 밴드는 '네트가 유효한 최대 거리'인데, 포획 판정이 tau 시점에 "
        "내려지므로 그 거리는 **tau 동안 네트가 실제로 간 거리**여야 한다. "
        "baseline 병진 = 8.22 m @ **tau_flight=0.15** (prototypes/net_forward) -- "
        "sense/decide 지연은 발사 **전**에 일어나므로 네트 병진에는 안 들어간다. "
        "29.847 은 붕괴 타이밍 기반(자체 WEAK/FLAGGED)이라 tau 와 무관하게 정해져 "
        "있었고, 그 결과 **네트가 닿을 수 없는 15 m 표적을 포획으로 판정**했다 "
        "(게이트에서 hold/ring/intercept 전부 24/24 NET_CAPTURE 로 자명해짐). "
        "폐로 정합: 발사 이격 14.22 m, tau_total 후 표적은 8.22 m -- 네트 위치와 일치."
    ),
    "physics.net_radius": (
        "2026-07-29 · docs/42 · 2.0 -> 1.77. **A3 선언.** "
        "논문 등가면적 반경은 1.997 m 이지만(docs/39 §2.2, Table 8 역산·Table 3 검증), "
        "params.py 가 스스로 경고한 대로 그것은 **등가면적 반경이고 최악방향 내접반경이 "
        "아니다** -- 포획 판정은 공격자 도달집합 **전체**가 네트 안에 들어와야 하므로 "
        "구속하는 것은 최악방향이다. tau_flight 시점 전개 형상의 최대 내접원을 재니 "
        "내접/등가 = **0.888** (면적비 0.788) -> 1.997 x 0.888 = 1.773 -> 1.77 채택. "
        "**주의(상한임)**: 측정된 0.888 은 완전 정사각형 값 0.886 과 거의 같은데, "
        "이는 flat-init 때문에 형상이 아직 평면 정사각형에 가깝기 때문이다. 실제 곡면 "
        "입구는 더 찌그러지므로 **참 비는 0.888 이하**이고 1.77 은 낙관 상한이다. "
        "우리에게 불리한 방향이고 마지막 남은 미정량 낙관 항목이었다."
    ),
    "viability.cone.half_angle": (
        f"2026-07-29 · 0.067 -> 0.2121 rad (12.2 deg). "
        f"= arctan(net_radius / range_max) = arctan(1.77/8.22). range_max 와 **연동 정의**"
        "이므로 함께 움직인다 (params.py 의 도출식 그대로). "
        "콘이 넓어지는 것은 우리에게 유리한 방향이지만, 축방향 밴드가 3.6배 짧아지는 "
        "것이 지배적이라 **순효과는 불리하다** -- 게이트가 그것을 확인했다."
    ),
    "train.layout.x_fire": (
        "2026-07-29 · docs/35 §1.3 + docs/40 §5 · 11.0 -> 16.0. "
        "네트는 tau_flight(0.15 s) 동안만 날아 8.22 m 를 가지만, 판정은 tau_total"
        "(0.30 s) 뒤에 내려진다. 공칭 접근 20 m/s 이면 요구 이격 = 8.22 + 20*0.30 "
        "= 14.22 m, finisher x=2 이므로 x_fire = 16.2 -> 16.0. "
        "**scripted baseline 트리거 전용이며 학습 정책은 이 값을 쓰지 않는다** "
        "(정책이 발사 시점을 스스로 찾는 것이 §6 의 주장)."
    ),
}


# ===========================================================================
# 2. 위협 브래킷 + 능력 비율 (에피소드 랜덤화)
# ===========================================================================
THREAT_BRACKET: Dict[str, Tuple[float, float]] = {
    # 하한 = 문헌 실측, 상한 = 선언. C-2(FPV 스펙시트)는 이 안의 한 점을 고르면 된다.
    "physics.a_att_max": (11.0, 78.0),
    "physics.att_speed": (8.0, 30.0),
}

THREAT_PROVENANCE = (
    "2026-07-29 · docs/36 C-2 · 점값(30 / 20)은 params.py 원문 'fixture' 로 근거가 "
    "없었고 점값 자체가 방어 불가이므로 **브래킷 랜덤화**로 대체한다.\n"
    "  a_att 하한 11 = Pliska 표적 실측 최대 가속 (평균 1.4); 상한 78 = 5인치 FPV 급 "
    "(docs/31 §4, AI 추출 DRAFT).\n"
    "  att_speed 하한 8 = Pliska 표적 최대 속도; 상한 30 = 선언 (문헌 실험 표적은 "
    "4~8 m/s 이므로 우리 상한은 그 4배 -- 공개된 어떤 평가보다 어렵다).\n"
    "  주의: 문헌 표적은 전부 연구용 쿼드라 **하한만 준다.** 상한은 우리 선언이다."
)

CAPABILITY_RATIOS: Dict[str, Tuple[str, float]] = {
    # 방어자 능력은 절대값이 아니라 **위협 대비 비율**로 선언한다 (Pliska 가 준 것이 비율).
    "physics.a_lim_max":            ("physics.a_att_max", 0.35),
    "train.limits.limiter_v_max":   ("physics.att_speed", 1.00),
    "train.limits.adversary_v_max": ("physics.att_speed", 1.50),
}

RATIO_PROVENANCE = (
    "2026-07-29 · docs/34 §3.3 · **A6 선언.** Pliska et al. (RA-L 2024, 실기): "
    "요격기 가속 4 m/s^2 vs 표적 최대 11 -> 비 0.36; 속도는 8 vs 8 -> 비 1.00.\n"
    "  즉 문헌의 형태는 **속도 대등, 가속 열세**다. 기존 값(a_lim = 1.00 x a_att, "
    "limiter_v_max = 4.00 x att_speed)은 방어자를 크게 과대평가하고 있었다.\n"
    "  a_lim 0.35 / v_lim 1.00 채택. adversary_v_max 1.50 은 기존 헤드룸(30/20) 유지.\n"
    "  전부 우리에게 불리한 방향이므로 결과 전 선언에 문제 없다."
)


# ===========================================================================
# 2.5 선언된 sweep 축
# ===========================================================================
# 결과가 **특정 점값의 산물이 아님**을 보이기 위해 미리 선언해 두는 축이다.
# 결과를 본 뒤 축을 추가하거나 값을 옮기는 것은 소급 변경이므로 금지한다.
SWEEP_AXES: Dict[str, Dict[str, Any]] = {
    "attitude.omega_max": {
        "target": "config",
        "default": 2.0,
        "values": (1.5, 2.0, 3.0),
        "why": (
            "네트 지향축 slew. 앵커(Pliska 2 rad/s)는 **기체** 선회율이고, 네트가 "
            "기체 고정이라는 축소자세 가정 아래에서만 지향 slew 와 같다. 짐벌 탑재면 "
            "더 빠르다. 실측상 hold 에서 0.0%, ring 에서 44.8% 구속이므로 결론이 이 "
            "값에 민감할 수 있다 -- 축으로 두고 함께 보고한다 (docs/45)."
        ),
    },
    "physics.kill_radius": {
        "target": "config",
        "default": 0.75,
        "values": (0.6, 0.75, 0.9),
        "why": "docs/34 §6 기하 유도 구간 0.56~0.86 의 실용 격자. A7 선언 시 함께 선언됨.",
    },
    "system.tau_kill": {
        "target": "SystemSpec",
        "default": 0.15,
        "values": (0.15, 0.20),
        "why": (
            "docs/42 §3. tau_kill 을 키우면 하드킬 성공이 줄어 2차 지표(비손실 비율)의 "
            "분모가 작아져 지표가 좋아 **보인다**. 2차 지표가 tau_kill 의 산물이 아님을 "
            "보이기 위한 축."
        ),
    },
}


# ===========================================================================
# 3. 아직 선언 전
# ===========================================================================
PENDING: Dict[str, str] = {
    "train.limits.adversary_omega": (
        "10.0 유지 -- **비구속임을 확인했다(2026-07-29)**. 원운동에서 필요 선회율은 "
        "omega = a/v 이고, 브래킷 최악 모서리(a=78, v=8)에서 9.75 rad/s < 10 이다. "
        "4000 draw 전수 검사에서 공격자 omega-구속 0.0%. 즉 가속 한계가 항상 먼저 "
        "묶으므로 이 값은 inert 이고 C-2 를 기다릴 필요가 없다. "
        "참고: limiter 는 반대로 omega=2.5 가 1.9% 의 draw 에서 **추가로 구속**한다 "
        "(a_lim/v_lim 최대 3.41 rad/s). 우리에게 불리한 방향이며 의도된 것은 아니지만 "
        "그대로 둔다 -- 결과를 보고 완화하면 소급 변경이 된다."
    ),
    "physics.dt": (
        "0.05 유지. tau 를 dt 격자 위(0.15)로 올려 A8 양자화를 해소했으므로 "
        "지금은 바꿀 이유가 없다. tau <= 0.10 운용으로 가면 재검토."
    ),
    "발사 설계점 7점 sweep": (
        "baseline 단일 채택. 7점(docs/33 §4)은 일반화 축으로 후속."
    ),
}


# ===========================================================================
# 4. API
# ===========================================================================
def m4_config(extra: Optional[Dict[str, Any]] = None) -> dict:
    """M4 고정 운용점. `extra` 는 실험용 추가 오버라이드(선언 대상 아님)."""
    ov: Dict[str, Any] = dict(M4_OVERRIDES)
    if extra:
        ov.update(extra)
    return as_config(ov)


def draw_threat(seed: int, episode: int, ns: str = "m4_threat") -> Dict[str, float]:
    """에피소드 위협 등급 + 비율로 따라오는 방어자 능력. SHA-256 결정론."""
    out: Dict[str, float] = {}
    for i, (key, (lo, hi)) in enumerate(sorted(THREAT_BRACKET.items())):
        h = hashlib.sha256(f"{ns}|{int(seed)}|{int(episode)}|{key}".encode()).digest()
        u = int.from_bytes(h[:8], "big") / 2 ** 64
        out[key] = float(lo + u * (hi - lo))
    for key, (src, ratio) in CAPABILITY_RATIOS.items():
        out[key] = float(out[src] * ratio)
    return out


def m4_episode_config(seed: int, episode: int,
                      extra: Optional[Dict[str, Any]] = None) -> dict:
    """고정 운용점 + 에피소드 위협 랜덤화. 에피소드마다 env 를 재구성해 쓴다."""
    ov: Dict[str, Any] = dict(M4_OVERRIDES)
    ov.update(draw_threat(seed, episode))
    if extra:
        ov.update(extra)
    return as_config(ov)


if __name__ == "__main__":                                   # pragma: no cover
    base = as_config()

    def get(cfg, dotted):
        cur = cfg
        for p in dotted.split("."):
            cur = cur[p]
        return cur

    m4 = m4_config()
    print("=" * 72)
    print("M4 운용점 = 동결 계약 + 선언된 오버라이드")
    print("=" * 72)
    for k in M4_OVERRIDES:
        print(f"\n  {k}: {get(base, k)} -> {get(m4, k)}")
        print(f"      {M4_PROVENANCE.get(k, '(근거 미기재 -- 채울 것)')}")
    print("\n" + "=" * 72)
    print("위협 브래킷 (에피소드 랜덤화)")
    print("=" * 72)
    for k, (lo, hi) in sorted(THREAT_BRACKET.items()):
        print(f"  {k}: {get(base, k)} -> U[{lo:g}, {hi:g}]")
    print(f"\n{THREAT_PROVENANCE}")
    print("\n능력 비율 (위협에 연동)")
    for k, (src, r) in CAPABILITY_RATIOS.items():
        print(f"  {k} = {r:.2f} x {src}   (기존 {get(base, k)})")
    print(f"\n{RATIO_PROVENANCE}")
    print("\n표본 draw:")
    for ep in (0, 1, 2):
        d = draw_threat(0, ep)
        print("   ep%d  " % ep + "  ".join(f"{k.split('.')[-1]}={v:.2f}"
                                           for k, v in sorted(d.items())))
    print("\n" + "=" * 72)
    print(f"선언 대기 {len(PENDING)}건")
    print("=" * 72)
    for k, v in PENDING.items():
        print(f"\n  - {k}\n      {v}")
