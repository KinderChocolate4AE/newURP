#!/usr/bin/env python3
"""Dump per-run history curves for selected keys from wandb OFFLINE runs.

wandb >=0.17 core backend (validated round-trip on 0.28.0) keeps offline
history ONLY inside the binary run-<id>.wandb datastore: files/ has no
wandb-summary.json, and on non-tty stdout the end-of-run summary block is
not printed either. This reads the datastore records directly (0.28 moved
history keys from item.key to item.nested_key).

Usage (server, venv python):
  .venv-l2/bin/python scripts/wandb_offline_dump.py \
      --root /data/hjhong/l2/wandb/wandb \
      --keys limiter/coma_D_raw_mean train/coma_D_mean \
      --out results/coma_run2/wandb_coma_dump.json
Runs lacking the FIRST key are skipped (e.g. pre-2D runs).
"""
import argparse, glob, json, os


def read_run(path, keys):
    from wandb.proto import wandb_internal_pb2 as pb
    from wandb.sdk.internal import datastore
    ds = datastore.DataStore()
    ds.open_for_scan(path)
    group, seed, hist = "", None, []
    while True:
        try:
            data = ds.scan_data()
        except Exception:
            break
        if data is None:
            break
        rec = pb.Record()
        rec.ParseFromString(data)
        rt = rec.WhichOneof("record_type")
        if rt == "run":
            group = rec.run.run_group
            for i in rec.run.config.update:
                if i.key == "seed":
                    seed = json.loads(i.value_json)
        elif rt == "history":
            row = {(i.key or "/".join(i.nested_key)): json.loads(i.value_json)
                   for i in rec.history.item}
            if keys[0] in row:
                hist.append(row)
    return group, seed, hist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="dir holding offline-run-*/")
    ap.add_argument("--keys", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = []
    for path in sorted(glob.glob(os.path.join(a.root, "offline-run-*", "run-*.wandb"))):
        group, seed, hist = read_run(path, a.keys)
        if not hist:
            continue
        r = {"dir": os.path.basename(os.path.dirname(path)), "group": group,
             "seed": seed, "steps": [h.get("_step") for h in hist]}
        for k in a.keys:
            r[k] = [h.get(k) for h in hist]
        out.append(r)
        q = max(1, len(hist) // 4)
        lastq = sum(h[a.keys[0]] for h in hist[-q:]) / q
        print(f"[{group} seed {seed}] rows={len(hist)} "
              f"final={hist[-1][a.keys[0]]:+.5f} lastq_mean={lastq:+.5f}")
    with open(a.out, "w") as f:
        json.dump(out, f)
    print("->", a.out)


if __name__ == "__main__":
    main()
