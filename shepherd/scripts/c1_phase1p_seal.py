"""C-1 Phase 1P step 0b — retro-seal the existing D0 evidence.

Why now, before the diversity re-search
---------------------------------------
Phase 1O introduced `evidence_bundle_hash` but the D0 artifacts (1J-1N) predate it.
If the seal is applied after the re-search, "sealed before re-search" and "sealed
after re-search" become indistinguishable, and the re-search stops being able to
falsify anything about the originals.  So the originals get sealed first.

What this DOES NOT do
---------------------
It does not manufacture a full `evidence_bundle_hash` for records that never stored
the fields.  The stored D0 JSONs are SUMMARIES: they keep verdicts, margins, seeds
and (sometimes) the attacker control sequence, but not the defender trajectory or
the attacker trajectory.  Reconstructing those by re-running and then calling the
result "the original artifact's bundle hash" would seal a reconstruction while
claiming to have sealed the original -- the exact promote-too-early pattern this
campaign keeps hitting.

So the seal has two clearly separated strengths, and every record says which it has:

  FILE_CONTENT_SEAL   sha256 over the file bytes.  Exact, independently checkable,
                      no reconstruction, no interpretation.  Every file gets this.
  BUNDLE_FIELD_AUDIT  per record, which of evidence_bundle_hash's 12 fields are
                      actually present in what was stored.  Records with full
                      coverage get a real evidence_bundle_hash; records without get
                      `partial_bundle_hash` over the present subset, labelled
                      PARTIAL, and the missing field names are listed.

`--verify` recomputes everything and diffs against a previously written manifest.
A seal that cannot be checked is decoration, so the check ships with the seal.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, subprocess, tarfile

import numpy as np

from shepherd.scripts import c1_governance as G

SEAL_VERSION = "c1-seal-1P-2026-07-25"

# the 12 fields evidence_bundle_hash requires
BUNDLE_FIELDS = ("scenario_id", "config_sha", "defender_traj", "attacker_seg_acc",
                 "attacker_traj", "reset_id", "seeds", "fire_step",
                 "verifier_version", "verdict", "margin_m", "dynamics_sha")

D0_FILES = [
    "results/c1_corridor/c1_replan_falsifier.json",
    "results/c1_corridor/c1_replan_falsifier_lowEffort.json",
    "results/c1_corridor/c1_phase1k_frozen_audit.json",
    "results/c1_corridor/c1_phase1l_exact_adjudication.json",
    "results/c1_corridor/c1_phase1l_survivor_adjudication.json",
    "results/c1_corridor/c1_phase1m_certificates.json",
    "results/c1_corridor/c1_phase1n_hardening.json",
    "results/c1_corridor/witness_artifacts.tar.gz",
    "results/c1_corridor/witness_artifacts_1g.tar.gz",
]

# source files whose content defines the verdicts (sealed so a later edit is visible)
D0_CODE = [
    "shepherd/scripts/c1_replan_falsifier.py",
    "shepherd/scripts/c1_replan_verify.py",
    "shepherd/scripts/c1_exact_clearance.py",
    "shepherd/scripts/c1_interval_certificate.py",
    "shepherd/scripts/c1_phase1k_frozen_audit.py",
    "shepherd/scripts/c1_phase1l_exact_adjudication.py",
    "shepherd/scripts/c1_phase1m_certificates.py",
    "shepherd/scripts/c1_phase1n_hardening.py",
    "shepherd/scripts/c1_governance.py",
    "shepherd/game/viability.py",
]


def sha_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "<unavailable>"


def _rows_of(doc, path):
    """Yield (record_id, dict) for the record-bearing lists in a D0 result file."""
    name = pathlib.Path(path).stem
    for key in ("rows", "M1_exploit_readjudication", "M2_interval_certificates"):
        v = doc.get(key)
        if isinstance(v, list):
            for i, r in enumerate(v):
                if isinstance(r, dict):
                    yield "%s:%s[%d]:%s" % (name, key, i, r.get("tag", "?")), r
    n3 = doc.get("N3_strength_aggregation")
    if isinstance(n3, dict) and isinstance(n3.get("rows"), list):
        for i, r in enumerate(n3["rows"]):
            yield "%s:N3[%d]:%s" % (name, i, r.get("scenario", "?")), r


def _present_fields(rec, doc):
    """Which evidence_bundle_hash fields the STORED record actually carries."""
    meta = doc.get("meta", {}) or {}
    fp = meta.get("frozen_protocol", {}) or {}
    have = {}
    if rec.get("tag") or rec.get("scenario"):
        have["scenario_id"] = rec.get("tag") or rec.get("scenario")
    if rec.get("config_sha"):
        have["config_sha"] = rec["config_sha"]
    for k_rec, k_bundle in (("top_escape_acc", "attacker_seg_acc"),
                            ("acc", "attacker_seg_acc")):
        if isinstance(rec.get(k_rec), list) and rec[k_rec]:
            have[k_bundle] = rec[k_rec]
    if fp.get("reset") is not None:
        have["reset_id"] = fp["reset"]
    seeds = {}
    for k in ("cert_seeds", "replan_seeds_search", "replan_seeds_confirm"):
        if fp.get(k):
            seeds[k] = fp[k]
    if rec.get("cem_seed") is not None:
        seeds["cem_seed"] = rec["cem_seed"]
    if seeds:
        have["seeds"] = seeds
    if rec.get("verifier_version"):
        have["verifier_version"] = rec["verifier_version"]
    if rec.get("verdict"):
        have["verdict"] = rec["verdict"]
    for k in ("best_exact_margin_m", "best_verified_certified_margin_m",
              "numerically_resolved_margin_m", "best_numerically_resolved_margin_m",
              "m_scenario_m"):
        if rec.get(k) is not None:
            have["margin_m"] = rec[k]
            break
    # defender_traj / attacker_traj / fire_step / dynamics_sha are NOT stored in the
    # D0 summaries.  They are deliberately left absent rather than reconstructed.
    return have


def build(root: pathlib.Path):
    files, records = [], []
    for rel in D0_FILES + D0_CODE:
        p = root / rel
        if not p.exists():
            files.append({"path": rel, "status": "MISSING"})
            continue
        ent = {"path": rel, "status": "SEALED", "sha256": sha_file(p),
               "bytes": p.stat().st_size,
               "kind": "code" if rel in D0_CODE else "result"}
        if rel.endswith(".tar.gz"):
            with tarfile.open(p, "r:gz") as tf:
                ent["members"] = sorted(m.name for m in tf.getmembers() if m.isfile())
        files.append(ent)

    for rel in D0_FILES:
        if not rel.endswith(".json"):
            continue
        p = root / rel
        if not p.exists():
            continue
        doc = json.loads(p.read_text())
        for rid, rec in _rows_of(doc, rel):
            have = _present_fields(rec, doc)
            missing = [f for f in BUNDLE_FIELDS if f not in have]
            ent = {"record_id": rid, "source_file": rel,
                   "fields_present": sorted(have), "fields_missing": missing,
                   "coverage": "%d/%d" % (len(have), len(BUNDLE_FIELDS))}
            if not missing:
                ent["seal_strength"] = "FULL_BUNDLE"
                ent["evidence_bundle_hash"] = G.evidence_bundle_hash(**have)
            else:
                ent["seal_strength"] = "PARTIAL"
                ent["partial_bundle_hash"] = hashlib.sha256(
                    json.dumps({"seal": SEAL_VERSION, "protocol": G.PROTOCOL_VERSION,
                                **{k: (np.asarray(v).round(12).tolist()
                                       if k == "attacker_seg_acc" else v)
                                   for k, v in sorted(have.items())}},
                               sort_keys=True, default=str).encode()).hexdigest()[:24]
            if "attacker_seg_acc" in have:
                ent["attack_policy_hash"] = G.attack_policy_hash(have["attacker_seg_acc"])
            records.append(ent)

    n_full = sum(1 for r in records if r["seal_strength"] == "FULL_BUNDLE")
    pol = {}
    for r in records:
        if "attack_policy_hash" in r:
            pol.setdefault(r["attack_policy_hash"], []).append(r["record_id"])
    shared = {k: v for k, v in pol.items() if len(v) > 1}

    return {"meta": {"seal_version": SEAL_VERSION, "protocol": G.PROTOCOL_VERSION,
                     "git_head": git_head(),
                     "strengths": {
                         "FILE_CONTENT_SEAL": "sha256 over file bytes; exact, no reconstruction",
                         "FULL_BUNDLE": "all 12 evidence_bundle_hash fields present in storage",
                         "PARTIAL": "hash over the present subset only; missing fields listed"},
                     "not_reconstructed": ["defender_traj", "attacker_traj", "fire_step",
                                           "dynamics_sha"],
                     "note": "D0 result files are summaries. Trajectories were never stored, "
                             "so no record can reach FULL_BUNDLE without a re-run. A re-run "
                             "would seal a reconstruction, not the original, so it is not done "
                             "here. Trajectory storage is a forward requirement from 1P on."},
            "n_files": len(files), "n_sealed": sum(1 for f in files if f["status"] == "SEALED"),
            "n_records": len(records), "n_full_bundle": n_full,
            "n_partial": len(records) - n_full,
            "shared_attack_policy_hashes": shared,
            "files": files, "records": records}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_seal_manifest.json")
    ap.add_argument("--verify", action="store_true",
                    help="recompute and diff against the existing manifest")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    out = pathlib.Path(a.out)
    cur = build(root)

    if a.verify:
        if not out.exists():
            print("!! no manifest at %s -- nothing to verify" % out)
            return 2
        old = json.loads(out.read_text())
        oldf = {f["path"]: f for f in old["files"]}
        newf = {f["path"]: f for f in cur["files"]}
        drift, gone, added = [], [], []
        for k, v in newf.items():
            if k not in oldf:
                added.append(k)
            elif oldf[k].get("sha256") != v.get("sha256"):
                drift.append({"path": k, "sealed": oldf[k].get("sha256"),
                              "now": v.get("sha256")})
        for k in oldf:
            if k not in newf:
                gone.append(k)
        oldr = {r["record_id"]: r for r in old["records"]}
        rdrift = [r["record_id"] for r in cur["records"]
                  if r["record_id"] in oldr
                  and (oldr[r["record_id"]].get("evidence_bundle_hash")
                       or oldr[r["record_id"]].get("partial_bundle_hash"))
                  != (r.get("evidence_bundle_hash") or r.get("partial_bundle_hash"))]
        ok = not (drift or gone or added or rdrift)
        print("== seal verify ==")
        print("   files checked   %d" % len(newf))
        print("   content drift   %d %s" % (len(drift), [d["path"] for d in drift]))
        print("   missing / added %d / %d" % (len(gone), len(added)))
        print("   record drift    %d %s" % (len(rdrift), rdrift[:5]))
        print("   -> %s" % ("SEAL INTACT" if ok else "SEAL BROKEN"))
        return 0 if ok else 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cur, indent=1, default=float))
    print("== D0 retro-seal ==")
    print("   files sealed        %d / %d" % (cur["n_sealed"], cur["n_files"]))
    print("   records             %d  (FULL_BUNDLE %d, PARTIAL %d)"
          % (cur["n_records"], cur["n_full_bundle"], cur["n_partial"]))
    print("   never stored        %s" % ", ".join(cur["meta"]["not_reconstructed"]))
    if cur["shared_attack_policy_hashes"]:
        print("   shared attack policies (C-6 evidence):")
        for h, ids in cur["shared_attack_policy_hashes"].items():
            print("     %s  <- %s" % (h, ids))
    print("wrote", out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
