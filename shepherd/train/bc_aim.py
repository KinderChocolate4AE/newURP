"""조준 헤드 시연 기반 초기화 — 교사 축 · cosine BC 손실 (docs/49 §5).

WHY
---
docs/48 §12: 학습된 조준축이 게이트를 못 연다 (개방률 0.61x). 그리고 그 결손은
표현의 한계가 아니다 -- docs/49 §1.1 이 교사 축을 관측에서 **선형으로** 각오차
1.65° 로 복원했다. 즉 라벨은 공짜이고 목표 함수는 배울 수 있다. 그런데 보상만
으로는 기울기가 없다 (`signal_audit`: 무작위 탐색 수익 std 가 종말항의 0.32 %).

교사는 **기준선과 같은 함수여야 한다** (docs/48 §3.1 한 곳 원칙). 그래서
`baselines.scripted_finisher` 를 **직접 호출해서** 축 성분만 떼어 쓴다 -- 식을
여기 다시 적지 않는다. 다시 적으면 그 순간 두 곳이 되고, 이 리포가 반복해서
겪은 사고(정정 3 · 정정 8 · 결함 1 · 결함 2)가 한 번 더 생긴다. P64 가 이
동치를 강제한다.

torch 는 손실 함수에서만 쓴다 (수집·교사는 torch-free).
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from shepherd.agents.baselines import scripted_finisher

# 환경 스택(gymnasium/pettingzoo)은 **함수 안에서** import 한다. `mappo.py` 가
# 손실 함수 하나 때문에 이 모듈을 import 하는데, 거기서 env 전체를 끌고 오면
# 학습기 계층이 무거워진다 (리포 관례: 학습기는 env-import 를 최소로).

__all__ = ["teacher_axis", "collect_bc_dataset", "bc_cosine_loss", "warmup_aim",
           "AIM_BC_MODES"]

AIM_BC_MODES = ("none", "warm", "aux")


def teacher_axis(env) -> np.ndarray:
    """스크립트 finisher 의 **조준축 성분**. 식을 복제하지 않는다.

    `scripted_finisher` 는 Box(5) = [axis(3), slew, fire] 를 낸다. 축은
    `clean_threshold_crossed` 에 의존하지 않으므로(발사 비트만 바뀐다) 그 인자는
    무엇을 주든 축이 같다 -- P64 가 그것까지 확인한다.
    """
    lims, fin, att = env._states()
    a = scripted_finisher(env._p(fin), env._p(att), env._v(att),
                          tau=env.tau_deploy, clean_threshold_crossed=False)
    return np.asarray(a, np.float32)[:3]


def _kw(w_kill: float = 0.5) -> dict:
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.spawn_rand import SpawnSpec
    return dict(system=SystemSpec(enabled=True),
                reward=RewardSpec(w_kill=w_kill, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())


def collect_bc_dataset(episodes: int = 120, seed0: int = 0, *,
                       limiter_mode: str = "hold") -> Dict[str, np.ndarray]:
    """워밍업(`warm`)용 교사 궤적. **발사는 끈다.**

    쏘면 에피소드가 거기서 끝나 뒤쪽 상태를 못 본다. 조준은 궤적 전체에서
    필요하므로 `fire_mode="never"` 로 끝까지 굴린다. 편대는 `SL` 계열과 같은
    `hold` -- 그 팔이 볼 분포에서 라벨을 받아야 워밍업이 의미가 있다.

    주의(docs/49 §2.1): 이건 **교사 분포**다. 정책 자신의 궤적이 아니므로
    분포 이동이 남는다. `aux` 모드는 그 문제가 없다.
    """
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.mission_rollout import scripted_role_actions

    X, Y, ep_id = [], [], []
    for ep in range(episodes):
        st = build_m4_env(seed0, ep, **_kw())
        env, scn, lay = st.env, st.scn, st.lay
        obs_d, _ = env.reset(seed=seed0 + ep)
        fid = env.finisher_id
        for _ in range(int(lay.episode_len)):
            X.append(np.asarray(obs_d[fid], np.float32).copy())
            Y.append(teacher_axis(env))
            acts = scripted_role_actions(env, scn, lay, limiter_mode=limiter_mode,
                                         fire_mode="never")
            acts[env.adversary_id] = np.zeros(3, np.float32)
            obs_d, _, term, trunc, _ = env.step(acts)
            ep_id.append(ep)
            if (term and term.get(fid)) or (trunc and trunc.get(fid)):
                break
    return {"X": np.asarray(X, np.float32), "Y": np.asarray(Y, np.float32),
            "ep": np.asarray(ep_id, int)}


# ----------------------------------------------------------------- torch ---
def bc_cosine_loss(pred, target):
    """`1 − cos(â, a*)`. 축은 **방향만** 의미가 있으므로 MSE 가 아니라 코사인이다.

    정책의 조준 출력은 `clip(mean, −1, 1) * high` 로 env 에 들어가는데
    (`high = 1`), 코사인은 스케일 불변이라 클립 전 `mean` 에 그대로 걸면 된다.
    클립 뒤에 걸면 경계 밖에서 기울기가 죽는다.
    """
    import torch
    p = pred / pred.norm(dim=-1, keepdim=True).clamp_min(1e-9)
    t = target / target.norm(dim=-1, keepdim=True).clamp_min(1e-9)
    return (1.0 - (p * t).sum(-1)).mean()


def warmup_aim(fin_actor, norm, X: np.ndarray, Y: np.ndarray, *,
               steps: int = 400, lr: float = 1e-3, batch: int = 256,
               seed: int = 0, device: str = "cpu") -> Dict[str, float]:
    """조준 헤드(`fin_actor.mean`)만 지도학습한다.

    **발사 헤드와 크리틱은 건드리지 않는다** (P66). 워밍업이 발사 정책까지
    바꿔 버리면 docs/48 §11 이 "발사 비트는 무죄" 라고 확인한 상태가 사라지고
    무엇이 달라졌는지 귀속이 안 된다.

    관측 정규화는 학습기와 **같은 것**을 쓴다 -- 워밍업이 다른 정규화로 맞추면
    RL 첫 스텝에서 조준이 어긋난다.
    """
    import torch

    torch.manual_seed(seed)
    dev = torch.device(device)
    xn = np.stack([norm.normalize(x) for x in X]).astype(np.float32)
    xt = torch.as_tensor(xn, device=dev)
    yt = torch.as_tensor(np.asarray(Y, np.float32), device=dev)
    opt = torch.optim.Adam(fin_actor.mean.parameters(), lr=lr)
    rng = np.random.default_rng(seed)
    n = xt.shape[0]
    last = float("nan")
    for _ in range(int(steps)):
        idx = torch.as_tensor(rng.integers(0, n, size=min(batch, n)), device=dev)
        opt.zero_grad()
        loss = bc_cosine_loss(fin_actor.mean(xt[idx]), yt[idx])
        loss.backward()
        opt.step()
        last = float(loss.item())
    with torch.no_grad():
        cos = 1.0 - float(bc_cosine_loss(fin_actor.mean(xt), yt).item())
        ang = float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))
    return {"bc_loss": last, "train_cosine": cos, "train_angle_deg": ang,
            "n_steps": int(steps), "n_samples": int(n)}
