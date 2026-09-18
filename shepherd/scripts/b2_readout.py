"""B2 판독기 — raw shard 를 읽어 집계하는 **유일한** 곳 (docs/102 §4, §6).

    python -m shepherd.scripts.b2_readout                  # primary
    python -m shepherd.scripts.b2_readout --forced-fire    # 별도 계정 (pooling 금지)

실행기는 집계하지 않는다. 집계가 실행 중에 일어나면 docs/102 §4 의 **raw count
identity** (P(N) = P(FIRE)·P(N|FIRE) 를 확률이 아니라 **원 카운트**로 확인) 가
자기검증이 되어버린다 — 여기서는 항상 원 레코드에서 다시 센다.

**B2 는 측정만 한다.** 여기에 W5 stop rule 도, 행/slice gate 도 넣지 않는다
(docs/102 §6). paired Δ 는 **cell x seed** 단위이며 seed pooling 은 금지다.
torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.b2_forced_fire import ACCOUNT, FF_DIR             # noqa: E402
from shepherd.scripts.b2_manifest import OUT_DIR, load                  # noqa: E402
from shepherd.scripts.b2_run import ARM_ORDER                           # noqa: E402
from shepherd.scripts.mission_rollout import BINS                       # noqa: E402

PRIMARY_DIR = OUT_DIR / "primary"
OUT = OUT_DIR / "readout.json"
FF_OUT = OUT_DIR / "forced_fire_readout.json"


def _load_shards(d: pathlib.Path, m: dict) -> tuple:
    recs, shards = [], []
    for f in sorted(d.glob("shard*.json")):
        blob = json.loads(f.read_text(encoding="utf-8"))
        assert blob["manifest_hash"] == m["manifest_hash"], \
            f"{f.name}: 다른 manifest 의 산출물 — 섞지 않는다"
        shards.append({"file": f.name, "finished": blob.get("finished"),
                       "n": len(blob["records"]),
                       "code_commit": blob.get("code_commit")})
        recs += blob["records"]
    return recs, shards


def _rates(rs: list) -> dict:
    """한 (cell, arm, seed) 묶음의 **원 카운트**와 그로부터의 비율."""
    n = len(rs)
    c = Counter(r["bin"] for r in rs)
    n_fire = sum(1 for r in rs if r["fire"])
    n_N_fire = sum(1 for r in rs if r["fire"] and r["bin"] == "N")
    out = {"n": n, "counts": {b: c.get(b, 0) for b in BINS},
           "n_fire": n_fire, "n_N_given_fire": n_N_fire,
           "n_hard_kill": sum(1 for r in rs if r["hard_kill"]),
           "n_veto": sum(1 for r in rs if r["veto_events"]),
           "identity_ok": c.get("N", 0) == n_N_fire}      # §4 raw count identity
    if n:
        out.update(p_N=c.get("N", 0) / n, p_fire=n_fire / n,
                   p_N_given_fire=(n_N_fire / n_fire) if n_fire else None,
                   p_H_illegal=c.get("H_illegal", 0) / n,
                   p_U=(c.get("N", 0) + c.get("H_fb", 0)) / n)   # secondary system metric
    return out


def readout(primary_dir: pathlib.Path = PRIMARY_DIR,
            out: pathlib.Path | None = None) -> dict:
    """`out` 미지정 시 정본 경로. 비정본 dir 를 읽을 때는 그 옆에 쓴다 —
    smoke 산출물이 정본 readout 을 덮는 사고를 구조적으로 막는다."""
    m = load()
    recs, shards = _load_shards(primary_dir, m)
    cells = {c["cell_id"]: c for c in m["cells"]}

    # ── 무결성: 에피소드당 정확히 한 bin · arm pairing · 중복 없음 ──────────
    assert all(r["bin"] in BINS for r in recs), "알 수 없는 bin"
    seen = Counter((r["s"], r["arm"]) for r in recs)
    dup = [k for k, v in seen.items() if v > 1]
    assert not dup, f"중복 레코드 {dup[:5]}"
    by_arm = {a: sorted(r["s"] for r in recs if r["arm"] == a) for a in ARM_ORDER}
    paired = by_arm[ARM_ORDER[0]] == by_arm[ARM_ORDER[1]]

    groups = defaultdict(list)
    for r in recs:
        groups[(r["cell_id"], r["arm"], r["seed"])].append(r)

    cell_rows, deltas = {}, []
    for (cid, arm, sd), rs in sorted(groups.items()):
        cell_rows[f"{cid}|{arm}|{sd}"] = _rates(rs)
    # paired Δ = cell x seed 단위 (seed pooling 금지 — docs/102 §2.1)
    for cid in sorted({k.split("|")[0] for k in cell_rows}):
        for sd in sorted({int(k.split("|")[2]) for k in cell_rows
                          if k.split("|")[0] == cid}):
            a = cell_rows.get(f"{cid}|{ARM_ORDER[0]}|{sd}")
            b = cell_rows.get(f"{cid}|{ARM_ORDER[1]}|{sd}")
            if not a or not b or not a["n"] or not b["n"]:
                continue
            deltas.append({
                "cell_id": cid, "seed": sd, "n_solo": a["n"], "n_rule": b["n"],
                "delta_p_N": b["p_N"] - a["p_N"],
                "delta_p_fire": b["p_fire"] - a["p_fire"],
                "delta_p_U": b["p_U"] - a["p_U"],
                "delta_p_H_illegal": b["p_H_illegal"] - a["p_H_illegal"],
                "eta": cells[cid]["eta"], "chi": cells[cid]["chi"],
                "lam_slice": cells[cid]["lam_slice"],
            })

    tot = _rates(recs)
    res = {
        "schema": "b2-readout-v1", "manifest_hash": m["manifest_hash"],
        "b0_v3_hash": m["b0_v3_hash"], "shards": shards,
        "n_records": len(recs), "n_scenarios": len(by_arm[ARM_ORDER[0]]),
        "arm_pairing_ok": paired,
        "identity_ok_all": all(v["identity_ok"] for v in cell_rows.values()),
        "overall": {a: _rates([r for r in recs if r["arm"] == a]) for a in ARM_ORDER},
        "overall_both_arms": tot,
        "by_cell_arm_seed": cell_rows,
        "paired_delta_cell_seed": deltas,
        "scope": "측정 전용. W5 stop rule · 행/slice gate 는 여기서 적용하지 않는다 "
                 "(docs/102 §6). fallback P_U 는 secondary system metric",
    }
    dest = out or (OUT if primary_dir == PRIMARY_DIR else primary_dir / "readout.json")
    dest.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    res["written_to"] = str(dest)
    return res


def forced_fire_readout(ff_dir: pathlib.Path = FF_DIR,
                        out: pathlib.Path | None = None) -> dict:
    """§5.5 — 이 조합만 본다. **primary 와 pooling 금지** (별도 파일·별도 계정)."""
    m = load()
    recs, shards = _load_shards(ff_dir, m)
    assert all(r.get("account") == ACCOUNT for r in recs), "계정이 섞였다"
    live = [r for r in recs if r.get("t_star") is not None]
    n_forced = sum(1 for r in live if r.get("forced_fired"))
    n_cap = sum(1 for r in live if r.get("bin") == "N")
    res = {
        "schema": "b2-forced-fire-readout-v1", "account": ACCOUNT,
        "manifest_hash": m["manifest_hash"], "shards": shards,
        "n_probed": len(recs), "n_selected": len(live),
        "n_skipped_no_axial": len(recs) - len(live),
        "n_forced_fired": n_forced,
        "n_in_band_at_t_star": sum(1 for r in live if r.get("in_band_at_t_star")),
        "pre_intervention_identical_all": all(
            r.get("pre_intervention_identical") for r in live),
        "n_net_capture_after_force": n_cap,
        "recovery_rate_given_forced": (n_cap / n_forced) if n_forced else None,
        "bins": dict(Counter(r.get("bin") for r in live)),
        "reading": "P(FIRE) 매우 낮음 + forced-fire 가 capture 회복 -> gate-limited; "
                   "FIRE 는 나오는데 P(N|FIRE) 낮음 -> attainability/controller-limited; "
                   "forced 해도 실패 -> gate 가 핵심 원인 아님 (docs/102 §5.5)",
        "pooling": "primary 와 pooling 금지",
    }
    dest = out or (FF_OUT if ff_dir == FF_DIR else ff_dir / "readout.json")
    dest.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    res["written_to"] = str(dest)
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="B2 readout (docs/102 §4/§5.5/§6)")
    ap.add_argument("--forced-fire", action="store_true")
    ap.add_argument("--dir", default=None, help="shard 디렉터리 (기본 primary/forced_fire)")
    a = ap.parse_args(argv)
    if a.forced_fire:
        r = forced_fire_readout(pathlib.Path(a.dir) if a.dir else FF_DIR)
        print(f"forced-fire: probed {r['n_probed']} selected {r['n_selected']} "
              f"forced {r['n_forced_fired']} -> N {r['n_net_capture_after_force']} "
              f"(pre-identical {r['pre_intervention_identical_all']})")
        print(f"  -> {r['written_to']}")
        return
    r = readout(pathlib.Path(a.dir) if a.dir else PRIMARY_DIR)
    print(f"records {r['n_records']}  scenarios {r['n_scenarios']}  "
          f"paired {r['arm_pairing_ok']}  identity {r['identity_ok_all']}")
    for arm in ARM_ORDER:
        o = r["overall"][arm]
        print(f"  {arm:<10} n={o['n']:<6} P(N)={o.get('p_N'):.3f} "
              f"P(FIRE)={o.get('p_fire'):.3f} "
              f"P(N|FIRE)={o.get('p_N_given_fire')} "
              f"P(H_ill)={o.get('p_H_illegal'):.3f} P_U={o.get('p_U'):.3f}")
    print(f"  paired deltas: {len(r['paired_delta_cell_seed'])} (cell x seed)")
    print(f"  -> {r['written_to']}")


if __name__ == "__main__":
    main()
