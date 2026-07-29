"""rho_v 작동 밴드 확인 — docs/29 §12.4 의 1순위 축 (임계 실험).

WHY
---
`rho_v = v_lim / v_att_max` 를 내리면 방어가 **실제로 약해진다**. 이종성이 구조적으로
성립하려면 limiter 가 공격자보다 열세여야 하지만(docs/29 §12), 너무 열세면 아무것도
막지 못한다. **작동 밴드가 비어 있으면 이후 실험이 전부 무의미**하므로 먼저 찍는다.

현행값 `v_lim = 80`, `v_att_max = 30` -> `rho_v = 2.67` (limiter 가 2.67배 빠름).

판정선 (docs/29 §12, 결과 보기 전 고정)
--------------------------------------
  밴드 있음   어떤 (rho_v, rho_a) 에서 침투 저지가 발생 -> 그 밴드에서 이후 실험
  밴드 없음   전 격자에서 침투 100%  -> 임무 설계 재검토 (F4 조항)

라벨: SEARCH_CANDIDATE / FIXED_CONDITION / DISCOVERY·NON-EVIDENTIAL.
방어자 낙관 설정(Pk=1)으로 **상한**을 먼저 본다 — 여기서 비면 어디서도 비어 있다.

torch-free.
"""
from __future__ import annotations

import argparse
from typing import List

import numpy as np

from shepherd.agents.attacker_ladder import (A1_SPEC, AttackerSpec, derive_phase,
                                             make_attacker)
from shepherd.env_adv import attach_attacker
from shepherd.env_sys import ModeSystemEnv, SystemSpec
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import run_episode
from shepherd.train.make_env import make_train_env

A2_SPEC = AttackerSpec(level="A2", jink_amp=0.35, route_gain=0.4, label="A2")
ATTACKERS = {"A1": A1_SPEC, "A2": A2_SPEC}


def cell(rho_v, rho_a, arm, attacker_key, *, p_kill=1.0, r_nk=6.0, seed=0,
         v_att_max=30.0, a_att=30.0):
    v_lim = rho_v * v_att_max
    a_lim = rho_a * a_att
    inner, scn, lay = make_train_env(as_config({
        "train.limits.limiter_v_max": float(v_lim),
        "physics.a_lim_max": float(a_lim),
    }))
    env = ModeSystemEnv(inner, lay, scn, SystemSpec(p_kill=p_kill, r_nk=r_nk))
    spec = ATTACKERS[attacker_key]
    attach_attacker(env.inner, make_attacker(spec), phase=derive_phase(spec.seed, seed))
    fire = "never" if arm == "intercept" else "x_fire"
    r = run_episode(env, scn, lay, seed=seed, limiter_mode=arm, fire_mode=fire,
                    attacker_name=spec.name())
    s = env.summary()
    return dict(rho_v=rho_v, rho_a=rho_a, arm=arm, attacker=attacker_key,
                label=r.label, steps=r.steps, contact=r.n_contact,
                interdicted=r.label not in ("PENETRATED", "TRUNCATED"),
                kill=s["KILL"], geom_fail=s["GEOM_FAIL"], pk_fail=s["PK_FAIL"],
                veto=s["VETO_NO_KINETIC"], committed=s["committed"],
                min_d=r.min_target_dist)


def main(argv=None):
    ap = argparse.ArgumentParser(description="rho_v 작동 밴드 확인")
    ap.add_argument("--pk", type=float, default=1.0)
    ap.add_argument("--r-nk", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    RHO_V = [0.4, 0.6, 0.8, 1.0, 1.5, 2.67]
    RHO_A = [0.5, 1.0]
    rows: List[dict] = []

    print(f"# rho_v BAND CHECK   Pk={args.pk}  R_nk={args.r_nk}  seed={args.seed}")
    print("# SEARCH_CANDIDATE / FIXED_CONDITION / NON-EVIDENTIAL\n")
    for att in ("A1", "A2"):
        r = cell(1.0, 1.0, "hold", att, p_kill=args.pk, r_nk=args.r_nk, seed=args.seed)
        rows.append(r)
        print(f"[{att}] hold(대조)  -> {r['label']:<12} min_d={r['min_d']:.2f}")
    print()
    hdr = f"{'att':>3} {'arm':>9} {'rho_a':>5} |" + "".join(
        f"{v:>10.2f}" for v in RHO_V)
    for att in ("A1", "A2"):
        for arm in ("ring", "intercept"):
            print(hdr if (att == "A1" and arm == "ring") else "")
            for ra in RHO_A:
                cells = []
                for rv in RHO_V:
                    r = cell(rv, ra, arm, att, p_kill=args.pk, r_nk=args.r_nk,
                             seed=args.seed)
                    rows.append(r)
                    tag = {"NET_CAPTURE": "NET", "CAPTURE_WITH_CONTACT": "NETc",
                           "HARD_KILL": "KILL", "PENETRATED": "pen",
                           "SPENT_FAIL": "spent", "TRUNCATED": "trunc"}[r["label"]]
                    cells.append(f"{tag:>10}")
                print(f"{att:>3} {arm:>9} {ra:>5.1f} |" + "".join(cells))

    n_int = sum(1 for r in rows if r["interdicted"])
    print(f"\n# 침투 저지 셀 {n_int}/{len(rows)}")
    if n_int == 0:
        print("# >>> 밴드 없음 — F4 조항 발동. 임무 설계 재검토")
    else:
        best = [r for r in rows if r["interdicted"]]
        print("# >>> 밴드 있음. 저지 셀:")
        for r in best[:20]:
            print(f"#     {r['attacker']} {r['arm']:>9} rho_v={r['rho_v']:.2f} "
                  f"rho_a={r['rho_a']:.1f} -> {r['label']} "
                  f"(kill={r['kill']} veto={r['veto']} contact={r['contact']})")
    return rows


if __name__ == "__main__":
    main()
