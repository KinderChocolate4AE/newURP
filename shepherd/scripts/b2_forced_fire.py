"""B2 forced-fire micro-arm — **diagnostic only** (docs/102 §5).

    python -m shepherd.scripts.b2_forced_fire --smoke
    python -m shepherd.scripts.b2_forced_fire --run --shard K --n-shards N

> **성능 arm 이 아니다.** primary scripted 비교와 **pooling 금지**. 묻는 질문은 하나:
> 낮은 P(N) 이 FIRE gate censoring 때문인가, FIRE 이후 attainability 때문인가.

primary 와 **별도 계정**이다 (별도 디렉터리 · 별도 schema · 별도 러너). 표본은 고르지
않는다 — docs/102 §5.4 의 기계 규칙 그대로 "§5.3 의 28 boundary-band cell 에서
`FIRE = 0` 으로 끝난 **전** 에피소드" 이며, 그래서 primary **이후**에만 돌 수 있다
(primary 결과가 표본을 정의한다 — 선택이 아니라 정의).

2-pass (e1d 규약 승계):
  pass 1  해당 arm 의 원 실행 재생 + 매 틱 축방향 좌표 a(t) 기록
  선택    t* = argmin_t |a(t) - a_target|, 동률이면 가장 이른 t.
          a_target = (range_min + range_max)/2 — 봉인된 cone band 의 중점
  pass 2  같은 CRN + force_commit_step = t* + 1 (**1-based**) + fire_mode="never"
          + perfect_aim_at_commit=False

제거되는 것은 **오직** v_shot_soft >= theta_fire admissibility gate 하나다. torch-free.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import sys
import time
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                               # noqa: E402
from shepherd.notify import ntfy                                       # noqa: E402
from shepherd.provenance import git_commit, git_dirty                  # noqa: E402
from shepherd.scripts.b2_manifest import OUT_DIR, load                 # noqa: E402
from shepherd.scripts.b2_run import (ARM_ORDER, _index, _unit_of,      # noqa: E402
                                     scenario_kwargs)
from shepherd.scripts.mission_rollout import partition_bin, run_episode  # noqa: E402
from shepherd.scripts.slew_audit import aim_geometry                   # noqa: E402

ACCOUNT = "diagnostic_forced_fire"       # ★ primary 와 절대 섞지 않는 계정 이름
FF_DIR = OUT_DIR / "forced_fire"
PRIMARY_DIR = OUT_DIR / "primary"
SAVE_EVERY = 25


# ── 표본 = primary 의 정의상 대상 전체 (선택 아님) ───────────────────────────
def sample(m: dict, primary_dir: pathlib.Path = PRIMARY_DIR) -> list:
    """§5.3 boundary band (chi_lo, chi_hi) 28 cell x `FIRE = 0` 에피소드 **전부**."""
    band = {c["cell_id"] for c in m["cells"] if c["boundary_band"]}
    assert len(band) == 28, f"boundary band 가 28 cell 이 아니다: {len(band)}"
    out = []
    for f in sorted(primary_dir.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["manifest_hash"] == m["manifest_hash"], \
            f"{f.name}: 다른 manifest 의 primary 산출물"
        for r in d["records"]:
            if r["cell_id"] in band and not r["fire"]:
                out.append({"s": r["s"], "arm": r["arm"], "cell_id": r["cell_id"],
                            "seed": r["seed"]})
    out.sort(key=lambda r: (r["s"], ARM_ORDER.index(r["arm"])))
    return out


# ── 2-pass ──────────────────────────────────────────────────────────────────
def _run(m: dict, arm: str, s: int, kw: dict, *, force_t: Optional[int] = None,
         fire_mode: Optional[str] = None):
    """arm 한 판. `force_t` (0-based) 가 있으면 pass 2 (게이트 우회 + fire 금지)."""
    a, com, fb = m["arms"][arm], m["common"], m["fallback"]
    kw = dict(kw)
    if force_t is not None:
        # ★ _step_i 는 1-based -> t + 1 (docs/102 §5.1 필수조항 2).
        kw["system"] = dataclasses.replace(
            kw["system"], force_commit_step=int(force_t) + 1,
            perfect_aim_at_commit=False)
    st = build_m4_env(m["crn"]["seed0"], s, **kw)
    tele: list = []
    r = run_episode(st.env, st.scn, st.lay, seed=m["crn"]["seed0"] + s,
                    limiter_mode=a["limiter_mode"], limiter_kw=a["limiter_kw"],
                    fire_mode=(fire_mode or ("never" if force_t is not None
                                             else com["fire_mode"])),
                    baseline_commit=com["baseline_commit_net_phase"], policy=None,
                    kinetic_fallback={"limiter_mode": fb["controller"],
                                      "baseline_commit": fb["baseline_commit"]},
                    telemetry=tele)
    return r, st, tele


def _axial(tele: list, tau: float, rmax: float) -> list:
    """틱별 축방향 좌표 a(t). psi/ax 의 단일 정의원 = slew_audit.aim_geometry."""
    rows = []
    for e in tele:
        g = aim_geometry(e["p_att"], e["v_att"], e["p_fin"], e["e_fin"],
                         tau=tau, range_max=rmax)
        if g is not None:
            rows.append({"t": e["t"], "ax": g["ax"], "in_band": g["in_band"]})
    return rows


def _select(rows: list, target: float) -> Optional[int]:
    """|a(t) - a_target| 최소, **동률이면 가장 이른 t** (docs/102 §5.2).

    docs/102 는 e1d 와 달리 band 안으로 후보를 제한하지 않았다 — 문안 그대로
    전 틱에서 argmin 하고, 뽑힌 틱이 band 안이었는지는 기록만 한다.
    """
    if not rows:
        return None
    return int(min(rows, key=lambda r: (abs(r["ax"] - target), r["t"]))["t"])


def probe(m: dict, blocks: list, item: dict, *, wiring_only: bool = False) -> dict:
    """`wiring_only` 는 **배선 시험 전용**이다 (docs/102 의 표본 정의가 아니다).

    정본 표본은 primary 에서 `FIRE = 0` 으로 끝난 판이고, 그런 판은 pass 1 을
    `fire_mode="clean"` 으로 돌려도 발사가 없다 — 즉 `"never"` 와 궤적이 같다.
    `wiring_only` 는 그 동치를 이용해 **발사했던 판**에도 같은 2-pass 기계를
    걸어보는 것뿐이며, 레코드에 `wiring_only=True` 로 못박아 진단 산출물과
    절대 섞이지 않게 한다.
    """
    s, arm = item["s"], item["arm"]
    cell, _ = _unit_of(blocks, s)
    chi, eta, kw = scenario_kwargs(m, cell, s)
    tau = float(kw["extra_cfg"]["physics.tau_deploy"])
    rmax = float(kw["extra_cfg"]["viability.cone.range_max"])
    rmin = 0.0                       # params.py viability.cone.range_min (봉인값)
    target = 0.5 * (rmin + rmax)

    r1, _st1, tele1 = _run(m, arm, s, kw,
                           fire_mode=("never" if wiring_only else None))
    assert r1.fire_step is None, f"s={s} {arm}: pass 1 에서 발사가 일어났다 (표본 오류)"
    rows = _axial(tele1, tau, rmax)
    t_star = _select(rows, target)
    if t_star is None:
        return {"account": ACCOUNT, "s": s, "arm": arm, "cell_id": cell["cell_id"],
                "seed": item["seed"], "t_star": None, "skipped": "no_axial_row"}
    r2, _st2, tele2 = _run(m, arm, s, kw, force_t=t_star)
    sel = next(x for x in rows if x["t"] == t_star)
    # §7-6: 개입 **이전** 궤적은 pass 1 과 bit-identical 이어야 한다.
    pre_ok = all(tele1[i] == tele2[i] for i in range(min(t_star, len(tele2))))
    return {
        "account": ACCOUNT, "wiring_only": bool(wiring_only),
        "s": s, "arm": arm, "cell_id": cell["cell_id"],
        "seed": item["seed"], "chi": chi, "eta": eta,
        "a_target": target, "t_star": t_star, "ax_at_t_star": sel["ax"],
        "in_band_at_t_star": sel["in_band"], "n_axial_rows": len(rows),
        "pre_intervention_identical": bool(pre_ok),
        "forced_fired": r2.fire_step is not None,
        "label": r2.label, "bin": partition_bin(r2), "steps": r2.steps,
        "fire_step": r2.fire_step, "n_contact": r2.n_contact,
        "n_engage": int(r2.meta.get("n_engage") or 0),
        "hard_kill": bool(r2.meta.get("hard_kill")),
        "net_spent_step": r2.meta.get("net_spent_step"),
    }


# ── shard 실행 (primary 와 같은 운영 배선, **별도 파일**) ────────────────────
def run_shard(shard: int, n_shards: int, limit: Optional[int] = None,
              out_dir: Optional[pathlib.Path] = None,
              primary_dir: pathlib.Path = PRIMARY_DIR) -> dict:
    m = load()
    _cells, blocks = _index(m)
    items = sample(m, primary_dir)
    mine = [x for i, x in enumerate(items) if i % n_shards == shard]
    if limit is not None:
        mine = mine[:limit]
    d = out_dir or FF_DIR
    d.mkdir(parents=True, exist_ok=True)
    path, done = d / f"shard{shard:02d}.json", d / f"shard{shard:02d}.done"
    records = []
    if path.exists():
        prev = json.loads(path.read_text(encoding="utf-8"))
        if prev.get("manifest_hash") != m["manifest_hash"]:
            raise SystemExit(f"{path.name}: 다른 manifest 의 산출물 — 치우고 다시 시작")
        records = prev["records"]
    code_commit, t0 = git_commit(), time.time()
    code_dirty = bool(git_dirty())          # main() 이 --run 을 막지만 기록도 남긴다

    def _save(finished: bool = False) -> None:
        path.write_text(json.dumps(
            {"schema": "b2-forced-fire-raw-v1", "account": ACCOUNT,
             "shard": shard, "n_shards": n_shards, "n_sample": len(items),
             "manifest_hash": m["manifest_hash"], "b0_v3_hash": m["b0_v3_hash"],
             "code_commit": code_commit, "code_dirty": code_dirty,
             "finished": finished,
             "pooling": "primary 와 pooling 금지 (docs/102 §5)",
             "records": records}, ensure_ascii=False), encoding="utf-8")

    ntfy(f"B2 forced-fire shard {shard}/{n_shards} start "
         f"({len(records)}/{len(mine)} done)", title="b2-ff")
    try:
        for i in range(len(records), len(mine)):
            records.append(probe(m, blocks, mine[i]))
            if (i + 1) % SAVE_EVERY == 0 or i + 1 == len(mine):
                _save()
                print(f"[b2-ff shard {shard}] {i + 1}/{len(mine)}  "
                      f"{time.time() - t0:.0f}s", flush=True)
    except BaseException as e:
        _save()
        ntfy(f"B2 forced-fire shard {shard} ABORT: {type(e).__name__}",
             title="b2-ff", priority="high")
        raise
    _save(finished=True)
    done.write_text(json.dumps(
        {"shard": shard, "n_shards": n_shards, "account": ACCOUNT,
         "manifest_hash": m["manifest_hash"], "n_records": len(records),
         "elapsed_s": round(time.time() - t0, 1),
         "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False),
        encoding="utf-8")
    ntfy(f"B2 forced-fire shard {shard} done — {len(records)} probes", title="b2-ff")
    return {"shard": shard, "n_records": len(records), "path": str(path)}


# ── smoke: docs/102 §7-6 (게이트만 바뀌는가) ────────────────────────────────
def smoke(n: int = 2, primary_dir: pathlib.Path = PRIMARY_DIR) -> bool:
    m = load()
    _cells, blocks = _index(m)
    if not any(primary_dir.glob("shard*.json")):
        print(f"primary 산출물이 없다 ({primary_dir}) — forced-fire 는 primary 이후에만 "
              "돈다 (표본이 primary 결과로 정의되므로). smoke 를 위해 "
              "--primary-dir 로 소규모 primary 산출물을 가리킬 것")
        return False
    items, wiring = sample(m, primary_dir)[:n], False
    if not items:                      # 이 산출물에 FIRE=0 판이 없다 -> 배선만 시험
        wiring = True
        band = {c["cell_id"] for c in m["cells"] if c["boundary_band"]}
        pool = []
        for f in sorted(primary_dir.glob("shard*.json")):
            for r in json.loads(f.read_text(encoding="utf-8"))["records"]:
                if r["cell_id"] in band:
                    pool.append({"s": r["s"], "arm": r["arm"],
                                 "cell_id": r["cell_id"], "seed": r["seed"]})
        items = pool[:n]
        print("표본이 비었다 (이 primary 산출물에 FIRE=0 판이 없다) — "
              "**배선 전용 (wiring_only)** 으로 전환한다. 진단 산출물이 아니다.")
        if not items:
            print("경계밴드 레코드 자체가 없다 — primary 산출물을 확인할 것")
            return False
    ok = {"6_pre_intervention_identical": True, "6b_gate_only_path": True,
          "6c_step_convention": True}
    for it in items:
        r = probe(m, blocks, it, wiring_only=wiring)
        print(f"  s={r['s']} {r['arm']} t*={r['t_star']} ax={r.get('ax_at_t_star')} "
              f"forced_fired={r.get('forced_fired')} label={r.get('label')} "
              f"bin={r.get('bin')} pre_identical={r.get('pre_intervention_identical')}")
        ok["6_pre_intervention_identical"] &= bool(r.get("pre_intervention_identical"))
        # fire_mode="never" 이므로 발사가 있었다면 그 경로는 게이트 우회뿐이다
        ok["6b_gate_only_path"] &= (r.get("fire_step") is None
                                    or r["fire_step"] == r["t_star"])
        ok["6c_step_convention"] &= (not r.get("forced_fired")
                                     or r["fire_step"] == r["t_star"])
    for k in sorted(ok):
        print(f"  [{'PASS' if ok[k] else 'FAIL'}] {k}")
    return all(ok.values())


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="B2 forced-fire diagnostic (docs/102 §5)")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--primary-dir", default=str(PRIMARY_DIR))
    a = ap.parse_args(argv)
    pd = pathlib.Path(a.primary_dir)
    if a.smoke:
        raise SystemExit(0 if smoke(a.n, pd) else 1)
    elif a.run:
        dirty = git_dirty()
        if dirty:                            # b2_run 과 동일한 clean-snapshot 규율
            raise SystemExit(
                "[b2-ff] --run 거부: 실행 코드(shepherd/, tests/)가 커밋되지 않아 "
                "기록될 code_commit 으로 재현할 수 없다. 먼저 커밋할 것:\n  "
                + "\n  ".join(dirty))
        r = run_shard(a.shard, a.n_shards, a.limit, primary_dir=pd)
        print(f"wrote {r['path']} ({r['n_records']} probes)")
    else:
        ap.error("--smoke 또는 --run 중 하나")


if __name__ == "__main__":
    main()
