"""발사 정책 진단 — 결손이 '못 배웠다' 인가 '배울 수 없다' 인가 (docs/48 §9 [1]).

WHY
---
역할 분리(docs/48 §8.3)에서 `SL`(hold 편대 + 학습 발사)이 해석적 발사 규칙보다
**나빴다**(0.137 vs 0.182). 편대는 고정돼 있었으므로 차이는 발사에서만 온다.
그런데 그 사실만으로는 두 가지가 안 갈린다:

    (A) 배울 수 없다   관측에 판단 근거가 없다 -> 어떤 RL 도 못 한다 (표현의 한계)
    (B) 못 배웠다      근거는 있는데 최적화가 못 찾았다 (확률 붕괴 · credit)

(A) 라면 다음 작업은 관측 설계이고, (B) 라면 발사 헤드다. 완전히 다른 작업이라
갈라놓고 시작해야 한다. 그리고 (A) 는 **학습 없이** 잴 수 있다 -- 지도학습으로
상한을 재면 된다.

두 모드
-------
    --probe        관측 -> `clean_net_threshold_crossed` 지도학습 상한.
                   체크포인트 불필요. (A) 를 판정한다
    --policy DIR   학습된 finisher 의 발사 확률을 실제로 뜯어본다.
                   체크포인트 필요 (서버). (B) 의 기전을 특정한다

양성 대조 (필수)
----------------
`--probe` 는 반드시 **치팅 특징**(`v_shot_soft` 단독)도 같이 낸다. 그게 1.0 이
안 나오면 데이터 파이프라인이 틀린 것이지 표현의 한계가 아니다. P52 에서
배운 것과 같은 이유다 -- 음성/양성 대조 없는 측정은 조용히 공허해진다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List, Optional, Tuple

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.scripts.mission_rollout import scripted_role_actions
from shepherd.spawn_rand import SpawnSpec

__all__ = ["collect_fire_dataset", "auc", "probe", "obs_index_v_shot",
           "policy_audit"]


# ── 지표 ────────────────────────────────────────────────────────────────────
def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """ROC AUC (Mann-Whitney U). sklearn 없이. 한쪽 클래스가 비면 nan."""
    s = np.asarray(scores, float).ravel()
    y = np.asarray(labels).ravel().astype(bool)
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float)
    ranks[order] = np.arange(1, len(s) + 1, dtype=float)
    # 동점 보정 (평균 순위) -- 붕괴한 정책은 점수가 전부 같아서 이게 없으면
    # AUC 가 0.5 가 아니라 임의값이 된다. 그 경우가 정확히 우리가 찾는 것이다.
    su = np.unique(s)
    if len(su) < len(s):
        for v in su:
            m = s == v
            ranks[m] = ranks[m].mean()
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def obs_index_v_shot(env) -> int:
    """관측 벡터에서 `v_shot_soft` 의 위치. env.py `_obs_vector` 의 배치를 따른다.

    9*N_max (limiters) + 9 (finisher) + 9 (attacker) + 6 (k,phase4,timer)
    -> [v_shot_soft, v_shot_worst, p_feasible]  (위협 관측 2 차원은 그 **뒤**)
    """
    return 9 * int(env.N_max) + 9 + 9 + 6


# ── 데이터 수집 ─────────────────────────────────────────────────────────────
def collect_fire_dataset(episodes: int = 120, seed0: int = 0, *,
                         limiter_mode: str = "hold",
                         w_kill: float = 0.5) -> Dict[str, np.ndarray]:
    """`fire_mode="never"` 로 굴려 **궤적 전체**에 라벨을 붙인다.

    쏘면 에피소드가 거기서 끝나 버려 그 뒤의 게이트 개폐를 못 본다. 발사를
    끄면 침투/절단까지 가므로 표본이 편향 없이 모인다. 편대는 `SL` 팔과 같은
    `hold` 로 둔다 -- 그 팔이 본 것과 같은 상태 분포여야 상한이 의미가 있다.
    """
    kw = dict(system=SystemSpec(enabled=True),
              reward=RewardSpec(w_kill=w_kill, enabled=True),
              attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
              spawn=SpawnSpec())
    X, y, ep_id, vshot, feas, boxed = [], [], [], [], [], []
    for ep in range(episodes):
        st = build_m4_env(seed0, ep, **kw)
        env, scn, lay = st.env, st.scn, st.lay
        idx = obs_index_v_shot(env)
        obs_d, _ = env.reset(seed=seed0 + ep)
        fid = env.finisher_id
        for _ in range(int(lay.episode_len)):
            o = np.asarray(obs_d[fid], np.float32).copy()
            acts = scripted_role_actions(env, scn, lay, limiter_mode=limiter_mode,
                                         fire_mode="never")
            acts[env.adversary_id] = np.zeros(3, np.float32)
            obs_d, _, term, trunc, info = env.step(acts)
            fi = info[fid]
            X.append(o)
            y.append(bool(fi.get("clean_net_threshold_crossed", False)))
            vshot.append(float(fi.get("v_shot_soft", 0.0)))
            feas.append(float(fi.get("p_feasible", 0.0)))
            boxed.append(bool(fi.get("boxed_in", False)))
            ep_id.append(ep)
            if (term and term.get(fid)) or (trunc and trunc.get(fid)):
                break
    return {"X": np.asarray(X, np.float32), "y": np.asarray(y, bool),
            "ep": np.asarray(ep_id, int), "v_shot_soft": np.asarray(vshot, float),
            "p_feasible": np.asarray(feas, float), "boxed_in": np.asarray(boxed, bool),
            "v_idx": obs_index_v_shot(build_m4_env(seed0, 0, **kw).env),
            "theta_fire": float(build_m4_env(seed0, 0, **kw).env.theta_fire)}


# ── 지도학습 상한 ───────────────────────────────────────────────────────────
def _fit_logistic(Xtr, ytr, Xte, epochs=300, hidden=0, seed=0):
    import torch
    import torch.nn as nn
    g = torch.Generator().manual_seed(seed)
    torch.manual_seed(seed)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    xt = torch.as_tensor((Xtr - mu) / sd, dtype=torch.float32)
    yt = torch.as_tensor(ytr.astype(np.float32))
    xe = torch.as_tensor((Xte - mu) / sd, dtype=torch.float32)
    d = xt.shape[1]
    net = (nn.Linear(d, 1) if not hidden else
           nn.Sequential(nn.Linear(d, hidden), nn.ReLU(), nn.Linear(hidden, 1)))
    opt = torch.optim.Adam(net.parameters(), lr=1e-2)
    # 클래스 불균형 보정 (교차 자체는 드물다)
    pos = max(float(yt.sum()), 1.0)
    w = torch.as_tensor((len(yt) - pos) / pos, dtype=torch.float32)
    lossf = nn.BCEWithLogitsLoss(pos_weight=w)
    for _ in range(epochs):
        opt.zero_grad()
        loss = lossf(net(xt).squeeze(-1), yt)
        loss.backward()
        opt.step()
    with torch.no_grad():
        return net(xe).squeeze(-1).numpy(), float(loss.item()), g


def probe(data: Dict[str, np.ndarray], train_frac: float = 0.6) -> dict:
    """관측만으로 `clean_crossed` 를 얼마나 맞힐 수 있는가 = **학습의 상한**.

    분할은 **에피소드 단위**다. 스텝 단위로 자르면 같은 궤적이 양쪽에 들어가
    시간 상관 때문에 AUC 가 부풀려진다.
    """
    X, y, ep = data["X"], data["y"], data["ep"]
    eps = np.unique(ep)
    cut = int(len(eps) * train_frac)
    tr = np.isin(ep, eps[:cut])
    te = ~tr
    out = {
        "n_steps": int(len(y)), "n_episodes": int(len(eps)),
        "base_rate": float(y.mean()),
        "n_pos": int(y.sum()),
        "theta_fire": float(data["theta_fire"]),
        "split": {"train_ep": int(cut), "test_ep": int(len(eps) - cut)},
    }
    if y[te].sum() == 0 or (~y[te]).sum() == 0:          # pragma: no cover
        out["note"] = "테스트 구간에 한쪽 클래스가 없다 -- episodes 를 늘릴 것"
        return out

    # ① 양성 대조: 치팅 특징 하나 (v_shot_soft 실측값). 1.0 이 안 나오면 배선이 틀렸다
    out["control_vshot_auc"] = auc(data["v_shot_soft"][te], y[te])
    # ② 관측 안의 v_shot_soft 차원 하나만
    v = X[:, int(data["v_idx"])]
    out["obs_vshot_dim_auc"] = auc(v[te], y[te])
    # ③ 그 차원에 단일 임계 -- 해석적 규칙의 절반(boxed_in 없이)을 재현하는가
    pred = v >= float(data["theta_fire"])
    out["single_threshold"] = {
        "accuracy": float((pred[te] == y[te]).mean()),
        "recall": float(pred[te][y[te]].mean()),
        "precision": float(y[te][pred[te]].mean()) if pred[te].any() else None,
        "_note": "틀리는 쪽은 boxed_in -- 그건 관측에 없다",
    }
    # ④ 전체 관측 선형
    s_lin, _, _ = _fit_logistic(X[tr], y[tr], X[te])
    out["obs_linear_auc"] = auc(s_lin, y[te])
    # ⑤ 전체 관측 MLP (액터와 같은 폭)
    s_mlp, _, _ = _fit_logistic(X[tr], y[tr], X[te], hidden=128, epochs=600)
    out["obs_mlp_auc"] = auc(s_mlp, y[te])
    # ⑥ boxed_in 이 얼마나 비싼가 -- 교차 중 boxed 로 죽는 비율
    thr = v >= float(data["theta_fire"])
    out["boxed_in_cost"] = {
        "threshold_crossed_steps": int(thr.sum()),
        "of_which_boxed": int((thr & data["boxed_in"]).sum()),
        "frac_boxed": float((thr & data["boxed_in"]).mean() / max(thr.mean(), 1e-12)),
    }
    return out


# ── 학습된 발사 정책 뜯어보기 (체크포인트 필요) ─────────────────────────────
def policy_audit(ckpt_dir: str, episodes: int = 60, seed0: int = 0,
                 limiter_mode: str = "hold") -> dict:
    """학습된 finisher 의 **발사 확률**을 스텝마다 뽑아 게이트와 대조한다.

    보는 것:
      p_fire 분포        0/1 로 굳었으면 확률 붕괴 (파일럿 p=0.0002 / 0.9999)
      게이트 조건부      E[p | 교차] vs E[p | 비교차]. 같으면 **눈감고 쏜다**
      AUC                p_fire 가 교차를 구분하는가. 0.5 면 정보 없음
    """
    import torch

    from shepherd.train.mappo import MAPPOTrainer
    from shepherd.train.obs_norm import RunningNorm

    d = pathlib.Path(ckpt_dir)
    ck = d / "ckpt_mappo_final.pt"
    if not ck.exists():
        ck = d / "ckpt_mappo_latest.pt"
    tr = MAPPOTrainer.load(str(ck), map_location="cpu")
    kw = dict(system=SystemSpec(enabled=True),
              reward=RewardSpec(w_kill=0.5, enabled=True),
              attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
              spawn=SpawnSpec())
    norm = RunningNorm(tr.obs_dim)
    nz = d / "obs_norm_final.json"
    if not nz.exists():
        nz = d / "obs_norm_latest.json"
    if nz.exists():
        norm.load_state_dict(json.loads(nz.read_text()))

    P, Y, fired = [], [], []
    for ep in range(episodes):
        st = build_m4_env(seed0, ep, **kw)
        env, scn, lay = st.env, st.scn, st.lay
        obs_d, _ = env.reset(seed=seed0 + ep)
        fid = env.finisher_id
        for _ in range(int(lay.episode_len)):
            o = np.asarray(obs_d[fid], np.float32)
            with torch.no_grad():
                t = torch.as_tensor(norm.normalize(o)[None, :])
                # MixedActor 의 발사 헤드 = `fire_logit` (mappo.py). 표본이 아니라
                # **확률**을 본다 -- 붕괴는 표본에서는 안 보이고 확률에서 보인다.
                p = float(torch.sigmoid(tr.fin_actor.fire_logit(t))[0, 0])
            acts = scripted_role_actions(env, scn, lay, limiter_mode=limiter_mode,
                                         fire_mode="never")
            acts[env.adversary_id] = np.zeros(3, np.float32)
            obs_d, _, term, trunc, info = env.step(acts)
            fi = info[fid]
            P.append(p)
            Y.append(bool(fi.get("clean_net_threshold_crossed", False)))
            fired.append(bool(fi.get("fire_event", False)))
            if (term and term.get(fid)) or (trunc and trunc.get(fid)):
                break
    P, Y = np.asarray(P, float), np.asarray(Y, bool)
    q = np.nanpercentile(P, [0, 1, 25, 50, 75, 99, 100]).tolist()
    return {
        "ckpt": str(ck), "n_steps": int(len(P)), "base_rate": float(Y.mean()),
        "p_fire": {"mean": float(np.nanmean(P)), "std": float(np.nanstd(P)),
                   "quantiles_0_1_25_50_75_99_100": q,
                   "frac_below_1e-3": float(np.mean(P < 1e-3)),
                   "frac_above_0p99": float(np.mean(P > 0.99))},
        "conditional": {"E[p | 교차]": float(np.nanmean(P[Y])) if Y.any() else None,
                        "E[p | 비교차]": float(np.nanmean(P[~Y])) if (~Y).any() else None},
        "auc_p_vs_crossing": auc(P, Y),
        "_read": ("AUC ~0.5 이고 조건부 두 값이 같으면 정책은 게이트를 안 보고 쏜다. "
                  "p 가 0 이나 1 로 굳었으면 확률 붕괴다."),
    }


def aim_audit(ckpt_dir: str, episodes: int = 60, seed0: int = 0) -> dict:
    """★ 조준축 진단 — `--policy` 가 **못 보는** 절반 (docs/48 §11).

    `policy_audit` 은 스크립트가 굴리는 궤적 위에서 정책의 발사 **확률만** 본다.
    즉 그동안 env 에 들어간 조준축은 계속 스크립트의 것이었다. 그런데 finisher
    는 발사 비트만 내는 게 아니라 **조준축 3차원**도 낸다. 그리고 `v_shot_soft`
    는 그 축에 의존한다 -- 축이 나쁘면 **게이트가 아예 덜 열린다.**

    그래서 같은 시드·같은 편대(hold)로 두 궤적을 나란히 굴린다:

        A  스크립트 조준   (기준)
        B  학습 조준       (발사 비트는 양쪽 다 0 으로 강제)

    발사를 끄는 이유는 두 궤적을 끝까지 같은 길이로 비교하기 위해서다 -- 한쪽만
    쏘면 거기서 끝나 버려 그 뒤의 게이트 개폐를 못 본다.

    읽는 법: B 의 게이트 개방률이 A 보다 크게 낮으면 결손은 발사 타이밍이 아니라
    **조준**이다.
    """
    import torch

    from shepherd.train.mappo import MAPPOTrainer
    from shepherd.train.obs_norm import RunningNorm

    d = pathlib.Path(ckpt_dir)
    ck = d / "ckpt_mappo_final.pt"
    if not ck.exists():
        ck = d / "ckpt_mappo_latest.pt"
    tr = MAPPOTrainer.load(str(ck), map_location="cpu")
    norm = RunningNorm(tr.obs_dim)
    nz = d / "obs_norm_final.json"
    if not nz.exists():
        nz = d / "obs_norm_latest.json"
    if nz.exists():
        norm.load_state_dict(json.loads(nz.read_text()))

    kw = dict(system=SystemSpec(enabled=True),
              reward=RewardSpec(w_kill=0.5, enabled=True),
              attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
              spawn=SpawnSpec())

    def _roll(learned_axis: bool) -> Tuple[np.ndarray, List[float]]:
        vs, ep_max = [], []
        for ep in range(episodes):
            st = build_m4_env(seed0, ep, **kw)
            env, scn, lay = st.env, st.scn, st.lay
            obs_d, _ = env.reset(seed=seed0 + ep)
            fid = env.finisher_id
            hi = np.asarray(env.action_space(fid).high, np.float32)[:3]
            best = 0.0
            for _ in range(int(lay.episode_len)):
                acts = scripted_role_actions(env, scn, lay, limiter_mode="hold",
                                             fire_mode="never")
                if learned_axis:
                    o = np.asarray(obs_d[fid], np.float32)
                    with torch.no_grad():
                        t = torch.as_tensor(norm.normalize(o)[None, :])
                        raw = tr.fin_actor.mean(t)[0].numpy()
                    axis = np.clip(raw[:3], -1.0, 1.0) * hi
                    a = np.zeros(5, np.float32)
                    a[:3] = axis                     # 발사 비트(idx4) = 0 고정
                    acts[fid] = a
                acts[env.adversary_id] = np.zeros(3, np.float32)
                obs_d, _, term, trunc, info = env.step(acts)
                v = float(info[fid]["v_shot_soft"])
                vs.append(v)
                best = max(best, v)
                if (term and term.get(fid)) or (trunc and trunc.get(fid)):
                    break
            ep_max.append(best)
        return np.asarray(vs, float), ep_max

    th = float(build_m4_env(seed0, 0, **kw).env.theta_fire)
    out = {"ckpt": str(ck), "theta_fire": th, "episodes": episodes}
    for name, learned in (("scripted_aim", False), ("learned_aim", True)):
        v, em = _roll(learned)
        em = np.asarray(em, float)
        out[name] = {
            "n_steps": int(len(v)),
            "gate_open_rate": float((v >= th).mean()),
            "episodes_with_any_open": float((em >= th).mean()),
            "v_shot_mean": float(v.mean()),
            "v_shot_p90": float(np.percentile(v, 90)),
            "ep_max_mean": float(em.mean()),
        }
    a, b = out["scripted_aim"], out["learned_aim"]
    out["delta"] = {
        "gate_open_rate": b["gate_open_rate"] - a["gate_open_rate"],
        "episodes_with_any_open": (b["episodes_with_any_open"]
                                   - a["episodes_with_any_open"]),
        "ep_max_mean": b["ep_max_mean"] - a["ep_max_mean"],
    }
    out["_read"] = ("learned_aim 의 게이트 개방률이 뚜렷이 낮으면 결손은 발사 "
                    "타이밍이 아니라 **조준**이다. 비슷하면 조준은 무죄다.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="발사 정책 진단 (docs/48 §9)")
    ap.add_argument("--probe", action="store_true",
                    help="관측 -> 교차 지도학습 상한 (체크포인트 불필요)")
    ap.add_argument("--policy", default=None,
                    help="체크포인트 디렉터리 (예: results/m4_roles/SL_s0/seed0)")
    ap.add_argument("--aim", default=None,
                    help="조준축 진단. 같은 디렉터리를 준다 -- 학습 조준 vs "
                         "스크립트 조준의 게이트 개방률을 비교한다")
    ap.add_argument("--episodes", type=int, default=120)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    res = {}
    if a.probe or not (a.policy or a.aim):
        data = collect_fire_dataset(a.episodes, a.seed0)
        res["probe"] = probe(data)
    if a.policy:
        res["policy"] = policy_audit(a.policy, min(a.episodes, 60), a.seed0)
    if a.aim:
        res["aim"] = aim_audit(a.aim, min(a.episodes, 60), a.seed0)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(res, indent=2, ensure_ascii=False))
        print(f"\n# 저장: {p}")


if __name__ == "__main__":
    main()
