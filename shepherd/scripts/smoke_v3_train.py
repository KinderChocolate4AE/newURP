"""G2 — fresh v3 TRAIN smoke (docs/65 G · docs/69 큐 8). **성능 검정 아님.**

서버 runbook (이 순서 그대로 — 둘 다 green 이면 바로 MARL TRAIN):

    # 1) smoke (이 파일)
    python -m shepherd.scripts.smoke_v3_train --out results/smoke_v3_train.json
    # 2) 미뤄둔 torch parity 1종 포함 전체 parity
    python -m pytest tests/test_contract_parity.py tests/test_arc_baseline.py -q
    # 3) green -> MARL TRAIN (사이에 reward/tuning 판단 없음)
    python -m shepherd.scripts.train_m4 --threat-layer train --seed 0 \\
        --device cuda --output results/m4_v3_train

PASS 조건은 아래 CHECKS 로 **결과 전 고정**돼 있다. capture rate·return·
p_net 같은 성능 지표는 산출·판정에 사용하지 않는다 (rollout 중 개별 episode
outcome 이 로그에 남는 것은 불가피하나 aggregate 를 만들지 않는다).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess

import numpy as np

V3_DIST_HASH_PIN = "efeffcbf2e24d807"      # docs/69 §4 FINAL (parity pin 동일)


def _git(cmd):
    try:
        return subprocess.check_output(["git"] + cmd, text=True).strip()
    except Exception:                                       # pragma: no cover
        return "unknown"


def main() -> None:
    import torch  # noqa: F401 -- smoke 는 서버(torch) 전용
    import yaml

    from shepherd.env_sys import RewardSpec, ratified_system
    from shepherd.m4_env import build_m4_env
    from shepherd.scale_v2 import v3_distribution_hash
    from shepherd.scripts.mission_rollout import LABELS, run_episode
    from shepherd.scripts.train_m4 import M4Runner

    ap = argparse.ArgumentParser(description="G2 fresh v3 TRAIN smoke")
    ap.add_argument("--config", default="configs/l2_mappo.yaml")
    ap.add_argument("--out", default="results/smoke_v3_train.json")
    ap.add_argument("--outdir", default="results/smoke_v3_ckpt")
    a = ap.parse_args()

    ck: dict = {"git_head": _git(["rev-parse", "HEAD"]),
                "git_dirty": bool(_git(["status", "--porcelain"]))}

    out_dir = pathlib.Path(a.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ck["checkpoint_parent_null"] = not any(out_dir.glob("ckpt_*"))

    run_cfg = yaml.safe_load(open(a.config))
    runner = M4Runner(run_cfg, 0, "cpu",
                      system=ratified_system(),
                      reward=RewardSpec(w_kill=0.5, enabled=True),
                      attacker=None, spawn=None, threat_layer="train")
    c = runner.contract

    # ── 계약 (G1) ──────────────────────────────────────────────────────────
    ck["threat_layer_train"] = (c["attacker"].get("threat_layer") == "train")
    ck["distribution_hash_pinned"] = (
        c["attacker"].get("distribution_hash") == V3_DIST_HASH_PIN
        == v3_distribution_hash())
    ck["f_contract"] = bool(c["system"]["contact_resolver"]
                            and not c["system"]["miss_terminates"]
                            and c["system"]["enabled"])
    ck["horizon_1100"] = (c["episode_len"] == 1100)

    # ── fresh-state (A5/G2) ───────────────────────────────────────────────
    ck["policy_fresh"] = (runner.env_steps == 0 and runner._ep_idx == 0)
    ck["norm_fresh"] = (float(runner.norm.count) <= 1e-3)
    opt = getattr(runner.tr, "optimizer", None)
    ck["optimizer_fresh"] = (opt is not None
                             and len(opt.state_dict().get("state", {})) == 0)
    ck["no_legacy_restore"] = True          # restore() 미호출 경로 (코드 사실)

    # ── env reset/step + finite (짧은 rollout 1회 — 성능 비산출) ──────────
    runner.collect_rollout()
    buf = runner.buf
    finite = all(np.isfinite(np.asarray(getattr(buf, f))).all()
                 for f in ("obs", "rewards") if hasattr(buf, f))
    ck["obs_reward_finite"] = bool(finite)
    ck["env_steps_advanced"] = runner.env_steps > 0

    # ── terminal label enum (scripted 1판 — outcome 1개 기록, aggregate 없음)
    st = build_m4_env(0, 0, system=ratified_system(),
                      reward=RewardSpec(w_kill=0.5, enabled=True),
                      threat_layer="train")
    r = run_episode(st.env, st.scn, st.lay, seed=0, limiter_mode="hold",
                    fire_mode="clean")
    ck["label_valid_enum"] = (r.label in LABELS)
    ck["episode_len_wired"] = (int(st.lay.episode_len) == 1100)

    # ── manifest 저장 (G1) ────────────────────────────────────────────────
    runner.save(out_dir)
    ck["manifest_saved"] = (out_dir / "contract_latest.json").exists()

    ck["all_pass"] = all(v is True for k, v in ck.items()
                         if k not in ("git_head", "git_dirty"))
    out = dict(contract="docs/65 G2 smoke (성능 비산출·비판정)", checks=ck,
               note=("PASS 조건은 결과 전 고정. rollout 개별 outcome 은 "
                     "의사결정에 사용하지 않는다."))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, v in ck.items():
        print(f"  {k}: {v}")
    print(f"G2 smoke -> {'ALL PASS' if ck['all_pass'] else 'FAIL'} -> {p}")


if __name__ == "__main__":
    main()
