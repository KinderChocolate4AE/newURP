"""B2 primary 완료·계보 점검기 — **판독(b2_readout) 전 필수, 읽기 전용.**

    python -m shepherd.scripts.b2_check                          # primary/
    python -m shepherd.scripts.b2_check --dir <path> [--expect-commit <hash>]

판독기는 manifest hash 만 대조한다 (docs/102 §4). 여기서는 그 앞의 **완주·계보
균일성**을 강제한다 — 2026-09-18 계보 정리에서 합의된 별도 점검:

  1 shard 집합    shard 0..N-1 전부 존재 · n_shards 일치 · finished=True · .done 마커
  2 코드 계보     모든 shard 의 code_commit 동일 (+ --expect-commit 대조) ·
                  code_dirty=False (미기록 = 구버전 실행기 = FAIL) ·
                  world_hash 단일·non-null · b0_v3_hash = manifest
  3 커버리지      records 의 scenario id 합집합 = [0, N) 정확히 (결손 0 · 중복 0)
  4 arm pairing   scenario 마다 ARM_ORDER 정확히 한 쌍 · (cell_id, seed, chi, eta)
                  일치 · manifest unit 과 일치
  5 총량          총 레코드 = len(ARM_ORDER) x N

**과학 판정이 아니다** — 집계·확률·stop rule 없음 (그건 b2_readout / W5 별도).
torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.b2_manifest import OUT_DIR, load                 # noqa: E402
from shepherd.scripts.b2_run import ARM_ORDER, _index, _unit_of        # noqa: E402

PRIMARY_DIR = OUT_DIR / "primary"


def check(d: pathlib.Path, expect_commit: str | None = None) -> list:
    """[(이름, ok, 상세)] — 전부 ok 여야 판독 착수."""
    m = load()
    _cells, blocks = _index(m)
    total = m["scenario_ids"]["n"]
    out = []

    files = sorted(d.glob("shard*.json"))
    if not files:
        return [("1_shards", False, f"{d}: shard 파일이 없다")]
    blobs = {}
    for f in files:
        b = json.loads(f.read_text(encoding="utf-8"))
        blobs[b["shard"]] = (f, b)

    # 1 shard 집합
    n_shards = {b["n_shards"] for _, b in blobs.values()}
    ok_set = len(n_shards) == 1
    ns = next(iter(n_shards))
    missing = sorted(set(range(ns)) - set(blobs)) if ok_set else []
    unfinished = [f.name for f, b in blobs.values() if not b.get("finished")]
    nodone = [f.name for f, b in blobs.values()
              if not f.with_suffix(".done").exists()]
    out.append(("1_shards", ok_set and not missing and not unfinished and not nodone,
                f"n_shards={sorted(n_shards)} 결손={missing} "
                f"미완주={unfinished} .done없음={nodone}"))

    # 2 코드 계보
    commits = {b.get("code_commit") for _, b in blobs.values()}
    dirty = [f.name for f, b in blobs.values() if b.get("code_dirty") is not False]
    worlds = {b.get("world_hash") for _, b in blobs.values()}
    mh = [f.name for f, b in blobs.values()
          if b.get("manifest_hash") != m["manifest_hash"]
          or b.get("b0_v3_hash") != m["b0_v3_hash"]]
    ok_lin = (len(commits) == 1 and "unknown" not in commits and not dirty
              and worlds and len(worlds) == 1 and None not in worlds and not mh)
    if expect_commit is not None:
        ok_lin &= commits == {expect_commit}
    out.append(("2_lineage", ok_lin,
                f"commit={sorted(str(c) for c in commits)} "
                f"(expect={expect_commit or '-'}) dirty/미기록={dirty} "
                f"world={sorted(str(w) for w in worlds)} hash불일치={mh}"))

    # 3 커버리지 + 4 pairing + 5 총량 (record 단위 — shard 라벨을 믿지 않는다)
    recs = [r for _, b in blobs.values() for r in b["records"]]
    per_s: dict = {}
    for r in recs:
        per_s.setdefault(r["s"], []).append(r)
    cnt = Counter(r["s"] for r in recs)
    miss_s = total - len(per_s)
    dup_s = sum(1 for s, c in cnt.items() if c != len(ARM_ORDER))
    stray = [s for s in per_s if not 0 <= s < total]
    out.append(("3_coverage", miss_s == 0 and dup_s == 0 and not stray,
                f"scenario {len(per_s)}/{total} (결손 {miss_s} · "
                f"쌍아님 {dup_s} · 범위밖 {len(stray)})"))

    bad_pair = 0
    for s, rs in per_s.items():
        cell, unit = _unit_of(blocks, s)
        arms = sorted(r["arm"] for r in rs)
        keys = {(r["cell_id"], r["seed"], r["chi"], r["eta"]) for r in rs}
        if (arms != sorted(ARM_ORDER) or len(keys) != 1
                or next(iter(keys))[:2] != (cell["cell_id"], unit["seed"])):
            bad_pair += 1
    out.append(("4_pairing", bad_pair == 0,
                f"arm쌍/CRN/manifest-unit 불일치 scenario {bad_pair}개"))

    want = total * len(ARM_ORDER)
    out.append(("5_total", len(recs) == want, f"records {len(recs):,}/{want:,}"))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="B2 완료·계보 점검 (판독 전 필수)")
    ap.add_argument("--dir", default=str(PRIMARY_DIR))
    ap.add_argument("--expect-commit", default=None,
                    help="봉인한 실행 snapshot 의 short hash (없으면 균일성만 검사)")
    a = ap.parse_args(argv)
    res = check(pathlib.Path(a.dir), a.expect_commit)
    for name, ok, detail in res:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    ok_all = all(ok for _, ok, _ in res)
    print(("PASS — b2_readout 착수 가능" if ok_all
           else "FAIL — 판독 금지 (완주/계보 미충족)"))
    raise SystemExit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
