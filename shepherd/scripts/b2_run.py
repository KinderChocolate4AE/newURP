"""B2 scripted 실행기 — manifest 소비 전용 (docs/102 §1~§4, §7).

    python -m shepherd.scripts.b2_run --smoke                    # GO smoke (docs/102 §7)
    python -m shepherd.scripts.b2_run --run --shard K --n-shards N

**이 파일은 격자를 만들지 않는다.** cell · arm · scenario id · seed · jitter · fallback
배선은 전부 `b2_manifest.json` 이 정하고 여기서는 소비만 한다 (docs/102 §2 "사후 선택
자유도 0").

**한 코드 경로**: world · attacker · FIRE · fallback 은 `_episode()` 하나를 지나며,
arm 은 **limiter controller 만** 바꾼다. "limiter control 만 다르다" 는 계약이 코드
구조로 성립해야 감사 가능하다.

**집계하지 않는다**: 에피소드당 raw outcome 만 적는다 (docs/102 §4 의 raw count
identity 는 판독기가 원 카운트로 검사한다 — 실행 중 확률을 만들면 그 검사가 무의미해진다).

서버 운영 (docs/95 런북이 geom-probe 에서 **사실이 아니었던** 항목 — 여기서는 실제로
구현하고 smoke 가 resume 까지 시험한다): incremental save · resume · shard completion
marker · ntfy. torch-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time
from typing import Optional

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env, manifest_mismatch            # noqa: E402
from shepherd.notify import ntfy, ntfy_enabled                         # noqa: E402
from shepherd.provenance import git_commit, git_dirty, world_hash      # noqa: E402
from shepherd.scripts.b2_manifest import MANIFEST, OUT_DIR, load       # noqa: E402
from shepherd.scripts.mission_rollout import partition_bin, run_episode  # noqa: E402
from shepherd.scripts.r2a_stage1 import draw_cell_jitter, resolve      # noqa: E402
from shepherd.scripts.r2b_phase1 import _slices                        # noqa: E402

SAVE_EVERY = 25                      # scenarios (= 50 ep) 마다 저장
ARM_ORDER = ("SOLO", "RULE_COOP")    # 기록·pairing 순서 고정


# ── manifest 소비 ────────────────────────────────────────────────────────────
def _index(m: dict) -> tuple:
    """(cell_id -> cell, s -> (cell, unit)) 조회표. units 의 블록을 전개한다."""
    cells = {c["cell_id"]: c for c in m["cells"]}
    blocks = [(u["s_lo"], u["s_hi"], cells[u["cell_id"]], u) for u in m["units"]]
    blocks.sort()
    return cells, blocks


def _unit_of(blocks: list, s: int) -> tuple:
    lo = 0
    hi = len(blocks) - 1
    while lo <= hi:                                   # 블록이 정렬·연속이므로 이분 탐색
        mid = (lo + hi) // 2
        if s < blocks[mid][0]:
            hi = mid - 1
        elif s >= blocks[mid][1]:
            lo = mid + 1
        else:
            return blocks[mid][2], blocks[mid][3]
    raise KeyError(f"scenario {s} 가 manifest 의 어떤 unit 에도 없다")


def scenario_kwargs(m: dict, cell: dict, s: int) -> tuple:
    """(chi, eta, build kwargs). arm 과 무관 — **한 번만** 만들어 두 arm 이 공유한다."""
    crn, sl = m["crn"], cell["lam_slice"]
    impl = _slices()[sl]
    assert abs(float(impl["R_max"]) - float(cell["R_max"])) < 1e-9, \
        f"slice {sl} 의 R_max 가 manifest cell 과 다르다 ({impl['R_max']} != {cell['R_max']})"
    chi, eta = draw_cell_jitter(crn["seed0"], s, cell["chi"], cell["eta"],
                               ns=crn["seed_ns"], jc=crn["jitter"]["chi"],
                               je=crn["jitter"]["eta"])
    kw = resolve(impl, chi, eta)
    q = kw["extra_cfg"]["physics.dt"] / kw["extra_cfg"]["physics.tau_deploy"]
    assert abs(q - 1.0 / 6.0) < 1e-12, f"q_dec gate: {q}"      # B0 v3 gates
    return chi, eta, kw


def _state_hash(env) -> str:
    """초기 world-state hash — scenario id 만 같고 초기화 경로가 갈리는 실수를 잡는다.

    id 일치만 보면 "같은 번호로 다른 판" 을 통과시킨다. 여기서는 reset 직후의
    **실제 상태 벡터**를 본다.
    """
    lims, fin, att = env._states()
    v = []
    for st in list(lims) + [fin, att]:
        v += list(np.asarray(env._p(st), float)) + list(np.asarray(env._v(st), float))
    v += list(np.asarray(env._e(fin), float))
    return hashlib.sha256(np.asarray(v, float).tobytes()).hexdigest()[:16]


# ── 한 에피소드 = 한 코드 경로 ───────────────────────────────────────────────
def _episode(m: dict, arm: str, s: int, kw: dict) -> tuple:
    """arm 하나의 에피소드. **arm 이 바꾸는 것은 limiter controller 뿐이다.**"""
    a, com, fb = m["arms"][arm], m["common"], m["fallback"]
    st = build_m4_env(m["crn"]["seed0"], s, **kw)
    seed = m["crn"]["seed0"] + s
    st.env.reset(seed=seed)                      # world-state hash 용 (run_episode 가 재reset)
    wsh = _state_hash(st.env)
    r = run_episode(st.env, st.scn, st.lay, seed=seed,
                    limiter_mode=a["limiter_mode"], limiter_kw=a["limiter_kw"],
                    fire_mode=com["fire_mode"],
                    baseline_commit=com["baseline_commit_net_phase"],
                    policy=None,
                    kinetic_fallback={"limiter_mode": fb["controller"],
                                      "baseline_commit": fb["baseline_commit"]})
    return r, st, wsh


def run_scenario(m: dict, blocks: list, s: int) -> list:
    """한 scenario 의 arm 쌍. 같은 kwargs · 같은 seed · 같은 초기 상태를 기계 검증."""
    cell, unit = _unit_of(blocks, s)
    chi, eta, kw = scenario_kwargs(m, cell, s)
    recs, stacks, hashes = [], {}, {}
    for arm in ARM_ORDER:
        r, st, wsh = _episode(m, arm, s, kw)
        stacks[arm], hashes[arm] = st, wsh
        recs.append({
            "s": s, "arm": arm, "cell_id": cell["cell_id"], "seed": unit["seed"],
            "chi": chi, "eta": eta,
            "fire": r.fire_step is not None, "fire_step": r.fire_step,
            "label": r.label, "bin": partition_bin(r), "steps": r.steps,
            "n_contact": r.n_contact,
            "hard_kill": bool(r.meta.get("hard_kill")),
            "veto_events": int(r.meta.get("veto_events") or 0),
            "net_spent_step": r.meta.get("net_spent_step"),
            "first_contact_t": r.meta.get("first_contact_t"),
            "first_engage_t": r.meta.get("first_engage_t"),
            "n_engage": int(r.meta.get("n_engage") or 0),
            "kinetic_from_t": r.meta.get("kinetic_from_t"),
        })
    # ── pairing gate (docs/102 §7-2/§7-3 + 합의된 추가 안전장치) ──────────────
    a, b = (stacks[x].contract for x in ARM_ORDER)
    diffs = manifest_mismatch(a, b)
    assert not diffs, f"s={s}: arm 간 resolved-contract 불일치 {diffs}"
    assert hashes[ARM_ORDER[0]] == hashes[ARM_ORDER[1]], \
        f"s={s}: 초기 world-state 가 arm 간 다르다 {hashes}"
    return recs


# ── shard 실행 (incremental save · resume · marker · ntfy) ───────────────────
def _shard_paths(shard: int) -> tuple:
    d = OUT_DIR / "primary"
    return d, d / f"shard{shard:02d}.json", d / f"shard{shard:02d}.done"


def _resume(path: pathlib.Path, m: dict) -> list:
    """기존 shard 에서 이어받는다. manifest 가 다르면 **이어받지 않는다**."""
    if not path.exists():
        return []
    prev = json.loads(path.read_text(encoding="utf-8"))
    if prev.get("manifest_hash") != m["manifest_hash"]:
        raise SystemExit(f"{path.name}: 다른 manifest 의 산출물 "
                         f"({prev.get('manifest_hash')} != {m['manifest_hash']}) — "
                         "덮어쓰지 않는다. 치우고 다시 시작할 것")
    recs = prev["records"]
    n_arms = len(ARM_ORDER)
    return recs[:len(recs) - len(recs) % n_arms]      # 중단된 scenario 는 버리고 재실행


def run_shard(shard: int, n_shards: int, limit: Optional[int] = None,
              out_dir: Optional[pathlib.Path] = None) -> dict:
    m = load()
    cells, blocks = _index(m)
    total = m["scenario_ids"]["n"]
    lo, hi = shard * total // n_shards, (shard + 1) * total // n_shards
    if limit is not None:
        hi = min(hi, lo + limit)
    d, path, done = _shard_paths(shard)
    if out_dir is not None:
        d = out_dir
        path, done = d / path.name, d / done.name
    d.mkdir(parents=True, exist_ok=True)
    records = _resume(path, m)
    start = lo + len(records) // len(ARM_ORDER)
    code_commit, t0 = git_commit(), time.time()
    code_dirty = bool(git_dirty())          # main() 이 --run 을 막지만 기록도 남긴다
    wh = None

    def _save(finished: bool = False) -> None:
        path.write_text(json.dumps(
            {"schema": "b2-scripted-raw-v1", "shard": shard, "n_shards": n_shards,
             "scenario_range": [lo, hi], "manifest_hash": m["manifest_hash"],
             "b0_v3_hash": m["b0_v3_hash"], "code_commit": code_commit,
             "code_dirty": code_dirty,
             "world_hash": wh, "finished": finished, "records": records},
            ensure_ascii=False), encoding="utf-8")

    ntfy(f"B2 shard {shard}/{n_shards} start s=[{start},{hi}) "
         f"(resume {len(records) // len(ARM_ORDER)})", title="b2")
    print(f"[b2 shard {shard}] manifest {m['manifest_hash']} scenarios "
          f"[{start},{hi}) ntfy={'on' if ntfy_enabled() else 'off'}", flush=True)
    try:
        for s in range(start, hi):
            recs = run_scenario(m, blocks, s)
            records.extend(recs)
            if wh is None:                    # 캠페인 전체가 한 세계여야 한다
                cell, _ = _unit_of(blocks, s)
                chi, eta, kw = scenario_kwargs(m, cell, s)
                wh = world_hash(build_m4_env(m["crn"]["seed0"], s, **kw).contract)
            if (s - start + 1) % SAVE_EVERY == 0 or s + 1 == hi:
                _save()
                el = time.time() - t0
                n = s - start + 1
                print(f"[b2 shard {shard}] {n}/{hi - start} scenarios  {el:.0f}s "
                      f"(ETA {el / n * (hi - start - n):.0f}s)", flush=True)
    except BaseException as e:                 # 중단이든 예외든 진행분은 반드시 남긴다
        _save()
        ntfy(f"B2 shard {shard} ABORT after {len(records)} ep: {type(e).__name__}",
             title="b2", priority="high")
        raise
    _save(finished=True)
    done.write_text(json.dumps(
        {"shard": shard, "n_shards": n_shards, "manifest_hash": m["manifest_hash"],
         "scenario_range": [lo, hi], "n_records": len(records),
         "elapsed_s": round(time.time() - t0, 1),
         "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False),
        encoding="utf-8")
    ntfy(f"B2 shard {shard}/{n_shards} done — {len(records)} ep "
         f"in {(time.time() - t0) / 60:.1f} min", title="b2")
    return {"shard": shard, "n_records": len(records), "path": str(path)}


# ── GO smoke (docs/102 §7) ──────────────────────────────────────────────────
def _pytest_b0_v3() -> bool:
    """§7-1. 계약 테스트는 **여기서 재구현하지 않는다** — 원본을 돌린다."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q",
                        "tests/test_b0_v3_contract.py"], cwd=ROOT,
                       capture_output=True, text=True)
    print((r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr)
          else "(no output)")
    return r.returncode == 0


def smoke(n: int = 3) -> bool:
    """배선·계약 확인만. **성능 gate 를 넣지 않는다** (docs/102 §7)."""
    m = load()
    cells, blocks = _index(m)
    ok = {}

    print(f"[1] B0 v3 계약 테스트 (tests/test_b0_v3_contract.py)")
    ok["1_b0_v3_contract"] = _pytest_b0_v3()

    # 경계 밴드 셀 하나 + 바깥 셀 하나에서 n scenario 씩
    picks = []
    for cid in (m["cells"][1]["cell_id"], m["cells"][0]["cell_id"]):
        u = next(x for x in m["units"] if x["cell_id"] == cid and x["seed"] == 0)
        picks += list(range(u["s_lo"], u["s_lo"] + n))
    recs = []
    for s in picks:
        recs += run_scenario(m, blocks, s)         # §7-2/§7-3 assert 가 내부에 있다
    ok["2_manifest_parity"] = True                 # run_scenario 의 assert 통과 = 성립
    ok["3_crn_pairing"] = True

    ids = {arm: [r["s"] for r in recs if r["arm"] == arm] for arm in ARM_ORDER}
    ok["3_crn_pairing"] = ids[ARM_ORDER[0]] == ids[ARM_ORDER[1]] == picks * 1 or \
        ids[ARM_ORDER[0]] == ids[ARM_ORDER[1]]

    from shepherd.scripts.mission_rollout import BINS
    bins = [r["bin"] for r in recs]
    ok["4_partition"] = all(b in BINS for b in bins) and len(bins) == len(recs)

    # §7-5 raw count identity: N 은 전부 FIRE 안에 있다 (원 카운트로)
    n_N = sum(1 for r in recs if r["bin"] == "N")
    n_fire = sum(1 for r in recs if r["fire"])
    n_N_fire = sum(1 for r in recs if r["bin"] == "N" and r["fire"])
    ok["5_raw_count_identity"] = (n_N == n_N_fire)

    # §7-7 latch/fallback semantics: NET_PRE/PENDING 접촉은 예외 없이 H_illegal,
    #      H_fb 는 예외 없이 NET_SPENT 이후 접촉
    lat, fbk = True, True
    for r in recs:
        ns = r["net_spent_step"]
        pre = [t for t in (r["first_contact_t"], r["first_engage_t"]) if t is not None]
        if any(ns is None or t + 1 <= ns for t in pre):
            lat &= r["bin"] == "H_illegal"
        if r["bin"] == "H_fb":              # 정당 fallback = NET_SPENT 이후 접촉뿐
            fbk &= (ns is not None and all(t + 1 > ns for t in pre)
                    and r["steps"] > ns)
        if r["bin"] == "N":
            lat &= r["n_contact"] == 0 and r["n_engage"] == 0
    ok["7_latch_and_fallback"] = bool(lat and fbk)

    # 운영 배선: resume 이 실제로 되는가 (docs/95 가 틀렸던 바로 그 지점)
    tmp = OUT_DIR / "smoke"
    for f in (tmp / "shard00.json", tmp / "shard00.done"):
        if f.exists():
            f.unlink()
    run_shard(0, 1, limit=2, out_dir=tmp)
    whole = json.loads((tmp / "shard00.json").read_text(encoding="utf-8"))
    part = dict(whole, finished=False,
                records=whole["records"][:len(ARM_ORDER)])   # 1 scenario 만 끝난 척
    (tmp / "shard00.json").write_text(json.dumps(part, ensure_ascii=False),
                                      encoding="utf-8")
    (tmp / "shard00.done").unlink()
    run_shard(0, 1, limit=2, out_dir=tmp)
    resumed = json.loads((tmp / "shard00.json").read_text(encoding="utf-8"))
    # 이어받은 결과가 통째 실행과 **레코드 단위로 같아야** resume 이 옳다.
    ok["ops_resume"] = (resumed["records"] == whole["records"]
                        and len(whole["records"]) == 2 * len(ARM_ORDER)
                        and resumed["finished"] and (tmp / "shard00.done").exists())

    print(f"\n  scenarios={len(picks)} episodes={len(recs)}  "
          f"FIRE={n_fire}  N={n_N}  bins={{{', '.join(sorted(set(bins)))}}}")
    for k in sorted(ok):
        print(f"  [{'PASS' if ok[k] else 'FAIL'}] {k}")
    print("  [ -- ] 6_forced_fire_bit_identical -> b2_forced_fire --smoke (별도 러너)")
    return all(ok.values())


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="B2 scripted runner (docs/102)")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--n-shards", type=int, default=8)
    ap.add_argument("--limit", type=int, default=None, help="shard 안 scenario 상한 (시험용)")
    ap.add_argument("--n", type=int, default=3, help="smoke scenario 수/셀")
    a = ap.parse_args(argv)
    if not MANIFEST.exists():
        ap.error("manifest 가 없다 — 먼저 python -m shepherd.scripts.b2_manifest")
    if a.smoke:
        raise SystemExit(0 if smoke(a.n) else 1)
    elif a.run:
        dirty = git_dirty()
        if dirty:                            # primary 는 clean snapshot 에서만 돈다
            raise SystemExit(
                "[b2] --run 거부: 실행 코드(shepherd/, tests/)가 커밋되지 않아 "
                "기록될 code_commit 으로 재현할 수 없다. 먼저 커밋할 것:\n  "
                + "\n  ".join(dirty))
        r = run_shard(a.shard, a.n_shards, a.limit)
        print(f"wrote {r['path']} ({r['n_records']} records)")
    else:
        ap.error("--smoke 또는 --run 중 하나")


if __name__ == "__main__":
    main()
