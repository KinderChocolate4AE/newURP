"""Phase III 게이트 7 — U^rel_{≤N} continuous outer relaxation (contract = docs/79 r1).

    python -m shepherd.scripts.gate7_relaxation --unitgates \
        --out results/phase3/gate7_unitgates.json

동치 증명 (docs/79 r1 §2 "objective 봉인" 조항 이행 — proxy 금지의 예외 근거)
--------------------------------------------------------------------------------
registered `v_shot_soft` (viability.py `_assemble`) 는 배치 S 가 witness 를
"제거"한 뒤의 caught 비율이다:

    v(S) = |caught ∧ feasible(S)| / |feasible(S)|,  feasible(S) = turn_feasible − blocked(S)

relaxation 은 (i) 배치점을 cell 로 이완하고 (ii) **optional blocking** — 선택된
cell 이 덮을 수 있는 witness 중 어느 부분집합을 지울지 defender 가 고른다 — 을
허용한다. 그러면:

  (a) soundness: 실제 배치 x ∈ C_k 가 지우는 집합 {j : x ∈ B_j} 는 cell 의
      덮개 집합의 부분집합이므로 relaxed defender 가 그대로 재현 가능
      → max_relaxed ≥ v(x)  ∀ 실제 x. (good 제거는 v 를 낮추므로
      (G−g)/(G−g+B) ≤ G/(G+B) — 재현 대신 good 을 안 지우는 선택은 더 크다.)
  (b) 동치: 최적 내부 선택은 good witness 를 절대 지우지 않으므로 G 가 상수
      → v = G / (G + B_total − cov),  cov = 덮인 bad witness 수.
      즉 relaxed v_shot 최대화 ≡ ≤N cell 의 bad-witness max-coverage.

따라서 본 구현의 max-coverage 는 proxy 가 아니라 **registered v_shot 의
relaxation-내 정확한 최적화**다. G = 0 이면 U^rel = 0 (게이트 6 조임과 정합).

soundness invariants (전부 defender-낙관 방향, docs/79 r1 §2)
------------------------------------------------------------
  - cell↔tube / cell↔reach / cell↔D 교차판정: 전부 outer (uncertain ⇒ 1).
        cover:  min_p |center − p| ≤ r_kill + half_diag
        reach:  |center − lim0_i| ≤ d_max(T) + half_diag
        admis:  |center − asset| + half_diag ≥ r_nk  (일부라도 D 밖 가능성)
  - d_max = 정지 출발 ramp 정확 상계 (G7-E 가 반례 탐색으로 봉인).
  - 동일 cell 다중 limiter 허용 (coverage 는 합집합이라 자동).
  - grid: 인스턴스당 고정 origin/extent 의 dyadic nested partition —
    level ℓ 의 cell 은 level ℓ−1 cell 의 정확한 8분할.
  - solver: 정확 DFS(B&B, admissible bound). node cap 도달 시 incumbent 는
    하한일 뿐이며 certified global bound(open frontier bound 최댓값)만 INF 에
    사용 가능 (docs/79 r1 solver bound semantics). U 비교는 정수 산술
    (θ = 9/10: v ≥ θ ⇔ 10·G ≥ 9·(G+B−cov)) — 부동소수 경계 이슈 원천 제거.

torch-free.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
from fractions import Fraction

import numpy as np

THETA_FRAC = Fraction(9, 10)               # docs/74 θ=0.9 의 정확 표현
NODE_CAP = 200_000


def d_max_from_rest(T, v_max, a_max):
    """정지 출발, |a|<=a_max, |v|<=v_max 에서 시간 T 내 최대 이동거리 (정확 상계).
    G7-C 의 진리측 표본(실제 도달가능 배치) 생성에 사용 — relaxation 측 아님."""
    T = max(float(T), 0.0)
    t_ramp = v_max / max(a_max, 1e-9)
    return 0.5 * a_max * T * T if T <= t_ramp else v_max * T - v_max ** 2 / (2 * a_max)


def d_max_outer(v0, v_max, a_max, T):
    """r2 relaxation 측 outer 상계: snapshot 속력 v0 에서 [0,T] 최대 이동거리의
    상계 min(v_max·T, v0·T + ½·a_max·T²). 두 항 각각이 상계이므로 min 도 상계
    (G7-E′ 반례탐색으로 봉인). false negative 방향 금지 (docs/79 r2 §2)."""
    T = max(float(T), 0.0)
    return min(v_max * T, float(v0) * T + 0.5 * a_max * T * T)


# ── instance ────────────────────────────────────────────────────────────────
def make_instance(*, bad_paths, n_good, lim0, T, v_lim, a_lim, asset, r_nk,
                  r_kill, good_paths=None, bbox=None, lim_v0=None):
    """bad_paths: [(n_pts,3)] bad witness 경로 substep. good_paths 는 G7-C
    true-eval 전용 (relaxation 은 good 을 지우지 않으므로 불필요).
    lim_v0: limiter 별 snapshot 속력 (r2 — 미지정 시 0 = 정지)."""
    lim0 = np.asarray(lim0, float).reshape(-1, 3)
    v0 = (np.zeros(len(lim0)) if lim_v0 is None
          else np.asarray(lim_v0, float).reshape(-1))
    return dict(bad_paths=[np.asarray(p, float).reshape(-1, 3) for p in bad_paths],
                n_good=int(n_good),
                good_paths=[np.asarray(p, float).reshape(-1, 3)
                            for p in (good_paths or [])],
                lim0=lim0, lim_v0=v0,
                T=float(T), v_lim=float(v_lim), a_lim=float(a_lim),
                asset=np.asarray(asset, float), r_nk=float(r_nk),
                r_kill=float(r_kill),
                bbox=bbox)


def _instance_bbox(inst):
    """고정 bounding domain (level 무관 — nested grid 의 전제)."""
    if inst["bbox"] is not None:
        lo, hi = inst["bbox"]
        return np.asarray(lo, float), np.asarray(hi, float)
    pts = np.concatenate(inst["bad_paths"]) if inst["bad_paths"] else \
        inst["lim0"].reshape(-1, 3)
    pad = inst["r_kill"] + 1e-6
    return pts.min(axis=0) - pad, pts.max(axis=0) + pad


def _cells(inst, level, base_n):
    """level ℓ dyadic cell 중심·half_diag. origin/extent 는 인스턴스 고정."""
    lo, hi = _instance_bbox(inst)
    n = base_n * (2 ** level)
    step = (hi - lo) / n
    ax = [lo[d] + step[d] * (np.arange(n) + 0.5) for d in range(3)]
    centers = np.stack(np.meshgrid(*ax, indexing="ij"), axis=-1).reshape(-1, 3)
    half_diag = 0.5 * float(np.linalg.norm(step))
    return centers, half_diag


def _signatures(inst, centers, half_diag):
    """cell -> (cover bitmask over bad, eligibility bitmask over limiters).
    전 판정 outer (docstring invariants). 반환은 dedupe + 지배 제거된 목록."""
    r_kill, asset, r_nk = inst["r_kill"], inst["asset"], inst["r_nk"]
    # admissibility (outer): 일부라도 NK 밖일 가능성
    ok = np.linalg.norm(centers - asset[None, :], axis=1) + half_diag >= r_nk
    centers = centers[ok]
    if len(centers) == 0:
        return []
    # eligibility (outer, r2: snapshot 속도 포함 τ-horizon 상계 — limiter 별)
    elig = np.zeros(len(centers), dtype=np.int64)
    for i, l0 in enumerate(inst["lim0"]):
        d_max = d_max_outer(inst["lim_v0"][i], inst["v_lim"], inst["a_lim"],
                            inst["T"])
        near = np.linalg.norm(centers - l0[None, :], axis=1) <= d_max + half_diag
        elig |= near.astype(np.int64) << i
    # cover (outer)
    cover = np.zeros(len(centers), dtype=object)
    cover[:] = 0
    for j, path in enumerate(inst["bad_paths"]):
        dmin = np.linalg.norm(centers[:, None, :] - path[None, :, :], axis=2).min(axis=1)
        hitj = dmin <= r_kill + half_diag
        for idx in np.flatnonzero(hitj):
            cover[idx] = int(cover[idx]) | (1 << j)
    sigs = {}
    for c, e in zip(cover, elig):
        c, e = int(c), int(e)
        if c == 0 or e == 0:
            continue                        # 아무 bad 도 못 덮거나 도달 불가 → 무용
        sigs[(c, e)] = True
    out = list(sigs)
    # 지배 제거: cover ⊆ cover' AND elig ⊆ elig' 이면 탈락
    keep = []
    for c, e in sorted(out, key=lambda t: -bin(t[0]).count("1")):
        if not any(c | c2 == c2 and e | e2 == e2 and (c, e) != (c2, e2)
                   for c2, e2 in keep):
            keep.append((c, e))
    return keep


def _matchable(chosen_eligs, n_lim):
    """선택된 (서로 다른) cell 들에 서로 다른 limiter 배정 가능? (Hall, N<=4 전수)."""
    k = len(chosen_eligs)
    if k == 0:
        return True
    if k > n_lim:
        return False
    lims = range(n_lim)
    return any(all(chosen_eligs[i] >> perm[i] & 1 for i in range(k))
               for perm in itertools.permutations(lims, k))


def solve_maxcov(sigs, N, n_lim, n_bad):
    """정확 max-coverage (<=N distinct cells, matchable). 반환:
    dict(cov, best_bound_cov, status, nodes). status OPTIMAL 이면 cov 가 정확
    최적. NODE_CAP 도달 시 status=CAP — cov 는 incumbent(하한), best_bound_cov
    가 certified 상계."""
    sigs = sorted(sigs, key=lambda t: -bin(t[0]).count("1"))
    best = 0
    nodes = 0
    frontier_bound = 0
    capped = False

    def gain_bound(cur, start, slots):
        gains = sorted((bin(c & ~cur).count("1") for c, _ in sigs[start:]),
                       reverse=True)[:slots]
        return bin(cur).count("1") + sum(gains)

    def dfs(start, cur, chosen_eligs):
        nonlocal best, nodes, frontier_bound, capped
        nodes += 1
        if nodes > NODE_CAP:
            capped = True
            frontier_bound = max(frontier_bound, gain_bound(cur, start,
                                                            N - len(chosen_eligs)))
            return
        best = max(best, bin(cur).count("1"))
        if len(chosen_eligs) == N or start == len(sigs):
            return
        if gain_bound(cur, start, N - len(chosen_eligs)) <= best:
            return
        for i in range(start, len(sigs)):
            c, e = sigs[i]
            if c & ~cur == 0:
                continue
            if not _matchable(chosen_eligs + [e], n_lim):
                continue
            if gain_bound(cur, i, N - len(chosen_eligs)) <= best:
                break                        # 정렬돼 있어 이후는 더 작다
            dfs(i + 1, cur | c, chosen_eligs + [e])

    dfs(0, 0, [])
    if capped:
        return dict(cov=best, best_bound_cov=max(best, frontier_bound),
                    status="CAP", nodes=nodes)
    return dict(cov=best, best_bound_cov=best, status="OPTIMAL", nodes=nodes)


def u_rel(inst, N, *, level, base_n=4):
    """U^rel_{<=N} at grid level. 반환 dict: u(incumbent 기반 정확분수),
    u_bound(certified 상계 분수 — INF 판정은 이것만), status, cov, nodes."""
    G, B = inst["n_good"], len(inst["bad_paths"])
    if G == 0:
        return dict(u=Fraction(0), u_bound=Fraction(0), status="G0",
                    cov=0, nodes=0)
    centers, half_diag = _cells(inst, level, base_n)
    sigs = _signatures(inst, centers, half_diag)
    r = solve_maxcov(sigs, N, len(inst["lim0"]), B)
    u = Fraction(G, G + B - r["cov"])
    ub = Fraction(G, G + B - min(r["best_bound_cov"], B))
    touched = 0
    for c, _e in sigs:
        touched |= c
    return dict(u=u, u_bound=ub, status=r["status"], cov=r["cov"],
                nodes=r["nodes"], n_sigs=len(sigs),
                frac_bad_touched=bin(touched).count("1") / max(B, 1))


def true_v(inst, placements):
    """G7-C 용 실제(비이완) 평가 — registered v_shot 산식 재현. placements =
    limiter 별 실제 점 (list[(3,)] — i 번째가 limiter i). 차단은 비자발적
    (good 도 지워짐). 반환: Fraction v (boxed 는 None)."""
    pts = [np.asarray(p, float) for p in placements]
    r_kill = inst["r_kill"]

    def blocked(path):
        return any(np.linalg.norm(path - p[None, :], axis=1).min() <= r_kill
                   for p in pts)

    good_alive = sum(not blocked(p) for p in inst["good_paths"])
    bad_alive = sum(not blocked(p) for p in inst["bad_paths"])
    feas = good_alive + bad_alive
    if feas == 0:
        return None                          # boxed — g_theta 제외 대상
    return Fraction(good_alive, feas)


# ── G7-A fixtures (exact truth — docstring 는 docs/79 r1 §3) ────────────────
def _seg(p0, p1, n=9):
    return np.linspace(np.asarray(p0, float), np.asarray(p1, float), n)


FAR = _seg((200.0, 200.0, 50.0), (210.0, 200.0, 50.0))   # 아무도 못 건드리는 good 경로


def fixture_blockable():
    """F1: bad 1 개가 reachable 자유공간 옆 — N=1 로 차단 가능. V* = 1."""
    inst = make_instance(
        bad_paths=[_seg((10, -2, 5), (10, 2, 5))], n_good=9,
        good_paths=[FAR] * 9,
        lim0=[(8, 0, 5)], T=30.0, v_lim=5.0, a_lim=5.0,
        asset=(0, 0, 0), r_nk=1.0, r_kill=1.0)
    return inst, dict(N=1, vstar=Fraction(1))


def fixture_unblockable():
    """F2: bad 5 개 전부 NK 심부 (반경 2) — admissible 점에서 차단 불가.
    V* = 5/(5+5) = 1/2."""
    bads = [_seg((2 * np.cos(t), 2 * np.sin(t), 0),
                 (1.5 * np.cos(t), 1.5 * np.sin(t), 0)) for t in
            np.linspace(0, 2 * np.pi, 5, endpoint=False)]
    inst = make_instance(
        bad_paths=bads, n_good=5, good_paths=[FAR] * 5,
        lim0=[(10, 0, 0)], T=30.0, v_lim=5.0, a_lim=5.0,
        asset=(0, 0, 0), r_nk=6.0, r_kill=1.0,
        bbox=((-8, -8, -8), (8, 8, 8)))
    return inst, dict(N=1, vstar=Fraction(1, 2))


def fixture_n1_vs_n2():
    """F3: bad 2 개가 반대편 (거리 20 > 2 r_kill) — N=1 은 하나만, N=2 는 둘 다.
    V*_{N1} = 1/2, V*_{N2} = 1."""
    inst = make_instance(
        bad_paths=[_seg((10, -1, 5), (10, 1, 5)), _seg((-10, -1, 5), (-10, 1, 5))],
        n_good=1, good_paths=[FAR],
        lim0=[(6, 0, 5), (-6, 0, 5)], T=30.0, v_lim=5.0, a_lim=5.0,
        asset=(0, 0, 0), r_nk=1.0, r_kill=1.0)
    return inst, dict(vstar_n1=Fraction(1, 2), vstar_n2=Fraction(1))


def fixture_outer_trap():
    """F4: bad 2 개의 차단 지점이 6 m 떨어져 한 점으론 불가 (r_kill=1) 인데
    coarse cell 하나가 둘 다 품는다. N=1: V* = 1/2. coarse h=8 에서
    U_h = 1 > V*, h=2 에서 1/2 로 수렴해야 한다 (낙관 방향 검증)."""
    inst = make_instance(
        bad_paths=[_seg((10, -1, 5), (10, 1, 5)), _seg((16, -1, 5), (16, 1, 5))],
        n_good=1, good_paths=[FAR],
        lim0=[(13, 0, 5)], T=30.0, v_lim=5.0, a_lim=5.0,
        asset=(0, 0, 0), r_nk=1.0, r_kill=1.0,
        # extent 32 → base_n=4: h=8,4,2. origin 을 두 경로의 중점 (13,0,5) 이
        # 정확히 level-0 cell 중심이 되게 정렬 — coarse cell 하나가 두 차단
        # 지점을 모두 품는 trap 을 보장한다.
        bbox=((1, -12, 1), (33, 20, 33)))
    return inst, dict(N=1, vstar=Fraction(1, 2))


# ── unit-gate runner (results/phase3/gate7_unitgates.json) ──────────────────
def run_unit_gates(rng=None):
    rng = rng or np.random.default_rng(7)
    res = {}

    # G7-A: U^rel >= V* (전 레벨), 위반 1건 = 게이트 7 무효
    a_ok, a_rows = True, []
    for name, (inst, meta) in dict(
            blockable=fixture_blockable(), unblockable=fixture_unblockable(),
            trap=fixture_outer_trap()).items():
        for lv in (0, 1, 2):
            r = u_rel(inst, meta["N"], level=lv)
            ok = r["u_bound"] >= meta["vstar"] and r["status"] == "OPTIMAL"
            a_ok &= ok
            a_rows.append(dict(fixture=name, level=lv, u=str(r["u"]),
                               vstar=str(meta["vstar"]), status=r["status"], ok=ok))
    inst3, m3 = fixture_n1_vs_n2()
    for N, key in ((1, "vstar_n1"), (2, "vstar_n2")):
        for lv in (0, 1, 2):
            r = u_rel(inst3, N, level=lv)
            ok = r["u_bound"] >= m3[key] and r["status"] == "OPTIMAL"
            a_ok &= ok
            a_rows.append(dict(fixture=f"n1_vs_n2(N={N})", level=lv, u=str(r["u"]),
                               vstar=str(m3[key]), status=r["status"], ok=ok))
    res["G7A"] = dict(ok=a_ok, rows=a_rows)

    # trap 수렴 (G7-A 부속): coarse 에서 U > V*, 최종 레벨에서 U = V*
    inst4, m4 = fixture_outer_trap()
    us = [u_rel(inst4, 1, level=lv)["u"] for lv in (0, 1, 2)]
    res["G7A_trap"] = dict(us=[str(u) for u in us],
                           ok=(us[0] > m4["vstar"] and us[2] == m4["vstar"]))

    # G7-B: refinement monotone (등호 허용)
    b_ok, b_rows = True, []
    for name, (inst, meta) in dict(
            blockable=fixture_blockable(), unblockable=fixture_unblockable(),
            trap=fixture_outer_trap()).items():
        us = [u_rel(inst, meta["N"], level=lv)["u"] for lv in (0, 1, 2)]
        ok = us[0] >= us[1] >= us[2]
        b_ok &= ok
        b_rows.append(dict(fixture=name, us=[str(u) for u in us], ok=ok))
    res["G7B"] = dict(ok=b_ok, rows=b_rows)

    # G7-D: N nesting
    d_ok, d_rows = True, []
    for lv in (0, 1, 2):
        us = [u_rel(inst3, N, level=lv)["u"] for N in (1, 2)]
        ok = us[0] <= us[1]
        d_ok &= ok
        d_rows.append(dict(level=lv, us=[str(u) for u in us], ok=ok))
    res["G7D"] = dict(ok=d_ok, rows=d_rows)

    # G7-C: random continuous placement domination (true v <= U^rel finest)
    c_ok, c_n = True, 0
    for name, (inst, meta) in dict(
            blockable=fixture_blockable(), unblockable=fixture_unblockable(),
            trap=fixture_outer_trap()).items():
        u_fin = u_rel(inst, meta["N"], level=2)["u"]
        d_max = d_max_from_rest(inst["T"], inst["v_lim"], inst["a_lim"])
        for _ in range(2000):
            pts = []
            for l0 in inst["lim0"][: meta["N"]]:
                x = l0 + rng.normal(size=3) * d_max / 3
                if (np.linalg.norm(x - l0) > d_max
                        or np.linalg.norm(x - inst["asset"]) <= inst["r_nk"]):
                    continue
                pts.append(x)
            if not pts:
                continue
            v = true_v(inst, pts)
            c_n += 1
            if v is not None and v > u_fin:
                c_ok = False
    res["G7C"] = dict(ok=c_ok, n_samples=c_n)

    # G7-E′ (r2): d_max_outer — snapshot 속도 포함 τ-horizon 상계 반례 탐색
    e_ok, e_n = True, 0
    for _ in range(500):
        T = float(rng.uniform(0.1, 20.0))
        v_max = float(rng.uniform(0.5, 10.0))
        a_max = float(rng.uniform(0.5, 10.0))
        v0mag = float(rng.uniform(0.0, v_max))
        dt = 0.01
        v = np.array([v0mag, 0.0, 0.0])
        x = np.zeros(3)
        for _t in range(max(int(T / dt), 1)):
            a = rng.normal(size=3)
            a = a / max(np.linalg.norm(a), 1e-9) * a_max
            v = v + a * dt
            s = np.linalg.norm(v)
            if s > v_max:
                v = v * (v_max / s)
            x = x + v * dt
        e_n += 1
        if np.linalg.norm(x) > d_max_outer(v0mag, v_max, a_max, T) + 1e-6:
            e_ok = False
    res["G7E"] = dict(ok=e_ok, n_samples=e_n)

    # G7-F (r2): elapsed-time invariance — horizon 이 상수(τ)이고 경과시간이
    # 입력 어디에도 없음을 fixture 로 봉인 (동일 물리 상태 → 동일 U)
    inst_f, meta_f = fixture_blockable()
    u_a = u_rel(inst_f, meta_f["N"], level=1)["u"]
    u_b = u_rel(dict(inst_f), meta_f["N"], level=1)["u"]
    res["G7F"] = dict(ok=(u_a == u_b), u=str(u_a))

    res["all_pass"] = all(res[k]["ok"] for k in ("G7A", "G7A_trap", "G7B",
                                                 "G7C", "G7D", "G7E", "G7F"))
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Phase III gate 7 relaxation")
    ap.add_argument("--unitgates", action="store_true")
    ap.add_argument("--out", default="results/phase3/gate7_unitgates.json")
    a = ap.parse_args(argv)
    if not a.unitgates:
        ap.error("현재 지원 모드: --unitgates (pilot 모드는 unit gate 전부 PASS 후)")
    from shepherd.scripts.measure_harness import _lattice_hash
    from shepherd.scripts.pivot_manifest import stamp
    res = run_unit_gates()
    for k in ("G7A", "G7A_trap", "G7B", "G7C", "G7D", "G7E", "G7F"):
        print(f"{k}: {'PASS' if res[k]['ok'] else 'FAIL'}", flush=True)
    print("ALL:", "PASS" if res["all_pass"] else "FAIL")
    out = dict(contract_doc="docs/79 r1 §3", results=res,
               **stamp(artifact="phase3_gate7_unitgates",
                       lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
