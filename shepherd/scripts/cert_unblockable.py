"""Phase III 게이트 6 — unblockable bad mass certificate + 전 스텝 cheap screen.

    python -m shepherd.scripts.cert_unblockable --episodes 10 --out results/phase3/cert_unblockable.json

정의 (docs/74 §3.6-1 · docs/75 §2.3 · docs/77 [D])
--------------------------------------------------
bad path witness `j` (turn-feasible 이고 ~caught) 의 blocker tube
`B_j = gamma_j ⊕ Ball(r_kill)` 가 admissible center domain `D` 와 만나지 않으면
**어떤 배치로도 그 witness 를 못 지운다**. 그 수 `U`, caught-good 수 `G` 로

    v_max = G / (G + U)        (U > 0 이면 boxed_in 도 불가능)

이 `V^rel_{<=N}` 의 sound upper bound 다 (N 무관 — N 은 level 2 relaxation 에서만
조인다). **같은 코드가 docs/74 §3.1 의 전 스텝 sound screen**:

    screen(e,t) = 1[ v_max(e,t) >= theta ]
    screen = 0  =>  V^rel < theta  =>  C_N(e,t) = 0 보장 (false negative 불가)

admissible domain D (선언 — 결과 열람 전 고정)
----------------------------------------------
docs/74 §3.6-1 은 D 를 "연속 admissible domain" 으로만 봉인했다. 여기서는
**D = R^3 \\ Ball(asset, r_nk)** 로 선언한다 (docs/57 NK kinetic-veto 계약과 정합:
NK 존 안에서는 kinetic 봉쇄가 거부되므로 center 가 어디든 그 안의 contact 는 무효).
D 를 실제보다 **크게** 잡는 방향의 오류는 U 를 줄여 상한을 약하게 만들 뿐
unsound 하지 않다 — 반대 방향(과소 D)은 금지. 따라서 NK 존 외 추가 배제는 넣지
않는다. tube ⊆ Ball(asset, r_nk) 판정은

    max_t |p_j(t) - asset| <= r_nk - r_kill

(r_kill >= r_nk 이면 항상 U = 0 = 공허 — 정직하게 보고).

값이 약한 것(U=0 다수)은 실패가 아니다 (docs/75 게이트 6). soundness unit test 는
`tests/test_cert_unblockable.py`.

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.game import viability as V
from shepherd.m4_env import build_m4_env
from shepherd.scripts.measure_harness import THETA, _lattice_hash, _world_kw, collect_states
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

__all__ = ["unblockable_mass", "cheap_screen", "unblockable_from_union"]


def unblockable_mass(path_blocks, caught, turn_feasible, *, asset, r_nk, r_kill):
    """배열 기반 코어. path_blocks = [(n_b, T_b, 3), ...] (union 순서), caught /
    turn_feasible = (M,). 반환: dict(G, B, U, v_max, boxed_possible)."""
    asset = np.asarray(asset, float)
    max_d = np.concatenate([
        np.linalg.norm(pb - asset[None, None, :], axis=2).max(axis=1)
        for pb in path_blocks])                              # (M,) max_t |p - asset|
    caught = np.asarray(caught, bool)
    tf = np.asarray(turn_feasible, bool)
    inside_nk = max_d <= (float(r_nk) - float(r_kill))       # tube ⊆ NK ball
    good = caught & tf
    bad = ~caught & tf
    G = int(good.sum())
    B = int(bad.sum())
    U = int((bad & inside_nk).sum())
    if G == 0:
        # caught witness 가 하나도 없으면 (layout 무관량) not-boxed 인 어떤 배치에서도
        # v = 0/feasible = 0 이다. g_theta 는 boxed 를 제외하므로 (docs/74 §3.2)
        # C_N 판정용 sound 상한은 0 — U=0 이어도 1.0 으로 공허해지지 않는다.
        # (2026-08-09 pilot preview 에서 원거리 상태 전부가 이 경로로 AMB 희석되던
        #  것을 조인 것. 상한을 낮추는 방향 = sound tightening.)
        v_max = 0.0
    else:
        v_max = G / (G + U)
    return dict(G=G, B=B, U=U, v_max=float(v_max),
                # U > 0 이면 unblockable witness 가 항상 feasible -> boxed 불가
                boxed_possible=bool(U == 0))


def unblockable_from_union(union, *, asset, r_nk, r_kill):
    """ReachableUnion 래퍼 (build_reachable_union 산출물에 그대로 적용)."""
    return unblockable_mass(union.path_blocks, union.caught, union.turn_feasible,
                            asset=asset, r_nk=r_nk, r_kill=r_kill)


def cheap_screen(union, *, asset, r_nk, r_kill, theta=THETA):
    """docs/74 §3.1 전 스텝 sound screen. 0 이면 C_N(e,t)=0 보장 (false negative 불가)."""
    m = unblockable_from_union(union, asset=asset, r_nk=r_nk, r_kill=r_kill)
    return int(m["v_max"] >= float(theta)), m


# ── harness 상태 스캔 ────────────────────────────────────────────────────────

def run(episodes, *, stride=25, n=8000, theta=THETA, log=print) -> dict:
    states = collect_states(episodes, stride=stride, log=log)
    st0 = build_m4_env(0, int(episodes[0]), **_world_kw())
    base = _base_env(st0.env)
    asset = np.asarray(st0.lay.target, float)
    r_nk = float(getattr(getattr(st0.env, "spec", None), "r_nk", 6.0))
    r_kill = float(base.kill_radius)
    if log:
        log(f"states = {len(states)} · asset {asset.tolist()} · r_nk {r_nk} · r_kill {r_kill}")

    rows, n_screen0 = [], 0
    for i, s in enumerate(states):
        kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
        union = V.build_reachable_union(
            s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
            n=n, n_segments=4, n_dir=32, seed=int(s["t"]), **kw)
        sc, m = cheap_screen(union, asset=asset, r_nk=r_nk, r_kill=r_kill, theta=theta)
        n_screen0 += (sc == 0)
        rows.append(dict(ep=s["ep"], t=s["t"], screen=sc, **m))
        if log and (i + 1) % 20 == 0:
            log(f"  {i+1}/{len(states)}", flush=True)

    Us = np.array([r["U"] for r in rows])
    vmaxs = np.array([r["v_max"] for r in rows])
    return dict(
        contract_doc="docs/74 §3.6-1·§3.1 · docs/75 §2.3 게이트 6 · docs/77 [D]",
        domain_D="R^3 minus Ball(asset, r_nk)  (docs/57 NK kinetic-veto; 선언 후 고정)",
        theta=float(theta), r_nk=r_nk, r_kill=r_kill,
        vacuous=bool(r_kill >= r_nk),
        n_states=len(states), episodes=[int(e) for e in episodes], stride=stride,
        n_witness_cfg=dict(n=n, n_segments=4, n_dir=32),
        summary=dict(
            n_states_U_positive=int((Us > 0).sum()),
            n_states_screen0=int(n_screen0),
            frac_screen0=float(n_screen0 / max(len(rows), 1)),
            v_max_min=float(vmaxs.min()) if len(vmaxs) else None,
            v_max_median=float(np.median(vmaxs)) if len(vmaxs) else None,
            U_max=int(Us.max()) if len(Us) else 0),
        states=rows,
        note=("screen=0 인 상태는 C_N=0 보장 -> 비싼 계산(L^reach/U^rel/solver) 은 "
              "screen=1 인 step ±10 tick 에만 적용 (docs/74 §3.1). "
              "U=0 다수(값이 약함)는 실패가 아니다 (docs/75 게이트 6)."),
        **stamp(artifact="phase3_cert_unblockable", lattice_hash=_lattice_hash()))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="게이트 6 unblockable bad mass + cheap screen")
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--ep0", type=int, default=0)
    ap.add_argument("--stride", type=int, default=25)
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--out", default="results/phase3/cert_unblockable.json")
    a = ap.parse_args(argv)

    out = run(range(a.ep0, a.ep0 + a.episodes), stride=a.stride, n=a.n)
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    s = out["summary"]
    print(f"[게이트 6] states {out['n_states']} · U>0 {s['n_states_U_positive']} · "
          f"screen=0 {s['n_states_screen0']} ({s['frac_screen0']:.1%}) · "
          f"v_max min {s['v_max_min']:.4f} / median {s['v_max_median']:.4f}")
    if out["vacuous"]:
        print("[경고] r_kill >= r_nk -> 항상 U=0 (공허). 정직 보고.")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
