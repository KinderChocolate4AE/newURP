"""V3b — net-miss handoff 감사 (docs/54 §1 R2 세부, 사전등록 후 실행).

boxed F-arm 은 접촉 kill 이 net 해소보다 항상 빨라 miss 가 발생하지 않았다
(net_spent_frac 0.000 -> (b) 검정 불가). 여기서는 miss 가 실재하는 유일한 확인
표본(hold/clean: SPENT_FAIL 32/500)과 같은 스택에서 두 플래그를 켜고 잰다.

    hold       폴백 효과기 없음 -> miss 후 국면 전환만 관측 (침투/절단 예측)
    intercept  폴백 효과기 있음 -> miss 후 무력화 표본 = (b) 실증

판정 (성능 대역 없음): (i) SPENT_FAIL 종료 0 (ii) net_spent >= 1
(iii) intercept 에서 net_spent ∧ 무력화 >= 1 (iv) hold 결말 분해 보고.
torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
from typing import List
import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.scripts.boxed_arm_audit import _sysenv
from shepherd.scripts.mission_rollout import run_episode
from shepherd.spawn_rand import SpawnSpec

__all__ = ["handoff_audit"]

NEUTRAL = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL")


def handoff_audit(n: int = 100, seed0: int = 0,
                  modes=("hold", "intercept")) -> dict:
    out = {}
    for mode in modes:
        recs: List[dict] = []
        for ep in range(n):
            st = build_m4_env(
                seed0, ep,
                system=SystemSpec(enabled=True, contact_resolver=True,
                                  miss_terminates=False),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
                spawn=SpawnSpec())
            r = run_episode(st.env, st.scn, st.lay, seed=seed0 + ep,
                            limiter_mode=mode, fire_mode="clean")
            se = _sysenv(st.env)
            recs.append(dict(episode=ep, label=r.label, steps=r.steps,
                             net_spent=bool(se.net_spent),
                             handoff_step=se.net_spent_step,
                             contact_kills=int(se.summary()["contact_events"])))
        spent = [x for x in recs if x["net_spent"]]
        out[mode] = {
            "n": n,
            "labels": {lab: sum(1 for x in recs if x["label"] == lab)
                       for lab in sorted({x["label"] for x in recs})},
            "spent_fail_terminal": sum(1 for x in recs if x["label"] == "SPENT_FAIL"),
            "net_spent": len(spent),
            "spent_then_neutralized": sum(1 for x in spent if x["label"] in NEUTRAL),
            "spent_outcomes": {lab: sum(1 for x in spent if x["label"] == lab)
                               for lab in sorted({x["label"] for x in spent})},
            "records": recs,
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="V3b net-miss handoff 감사 (docs/54)")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = handoff_audit(a.n)
    for mode, v in r.items():
        print(f"[{mode}] n={v['n']}  SPENT_FAIL종료={v['spent_fail_terminal']}  "
              f"net_spent={v['net_spent']}  miss후무력화={v['spent_then_neutralized']}")
        print(f"   labels={v['labels']}")
        print(f"   miss판 결말={v['spent_outcomes']}")
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
