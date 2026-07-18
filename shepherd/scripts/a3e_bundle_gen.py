"""A-3e d1-only bundles: dev-v2d1 / sealed-v2d1 (docs/21 v0.3 SS3 FROZEN;
docs/09 (kkk)). torch-free.

Composition (both variants identical; only rng/seed bases and the sealed
flag differ):
  d0 = 40 eps  : the 2 d1-admissible witnesses (sorted by speed) x 20 reps,
                 EXACT spawns (sigma 0, limiter_v 0).
  d1 = 120 eps : 24 admissible draws x 5 reps, cell-balanced 60:60, ordered
                 (cell, draw_idx, rep) lexicographic; position jitter
                 sigma = 0.005 from ONE per-cell stream
                 default_rng(rng_base + 1_000*k + int(v)), consumed in
                 episode order; velocities exact.
  reset seed   = seed_base + 10_000 * stage_idx + i   (d0 idx 0, d1 idx 1).

dev extra: embedded ZERO-CACHE for d1 -- zero-limiter + teacher-fire arm run
once per episode at build time (the L1/J1 paired gate denominator).
sealed: NO zero roll at build (policy+zero run together at the single
sealed judgment -- docs/21 SS3/SS4); meta.sealed = true.

Guards (docs/21 SS3 sealed-inviolability, CONTENT-keyed so symlinks/copies
change nothing):
  load_bundle(path) refuses meta.sealed bundles unless sealed_judgment=True;
  sealed_judgment loads refuse when the consumption marker exists; any
  manifest-sha mismatch (tamper) aborts; there is no force/bypass parameter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

import numpy as np
import yaml

from shepherd.train.a3e import A3ESpawner, D1_SIGMA

VARIANTS = {
    "dev_v2d1": {"rng_base": 75_000, "seed_base": 12_000_000, "sealed": False},
    "sealed_v2d1": {"rng_base": 95_000, "seed_base": 13_000_000,
                    "sealed": True},
}
D0_REPS, D1_REPS, K = 20, 5, 1
CONSUMED_MARKER = "results/a3e_sealed_consumed.json"


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_bundle(variant: str, spawner: A3ESpawner) -> dict:
    spec = VARIANTS[variant]
    rng0 = np.random.default_rng(0)              # d0 exact: rng unused
    d0 = []
    for w_i, t0 in enumerate(sorted(spawner.t0, key=lambda t: float(t.v))):
        sp = spawner._sb.spawn_from(t0, rng0, sigma_pos=0.0, sigma_vel=0.0)
        for rep in range(D0_REPS):
            i = w_i * D0_REPS + rep
            d0.append({"ep": i, "stage": "d0",
                       "witness": f"v{int(float(t0.v))}", "rep": rep,
                       "reset_seed": spec["seed_base"] + i,
                       "spawn": {kk: (vv.tolist()
                                      if isinstance(vv, np.ndarray) else vv)
                                 for kk, vv in sp.items()}})
    cells: dict = {}
    for e in spawner.d1:                          # file order = draw index
        cells.setdefault(int(float(e["spawn"]["att_speed"])), []).append(e)
    d1, i = [], 0
    for v in sorted(cells):
        jr = np.random.default_rng(spec["rng_base"] + 1_000 * K + v)
        for di, e in enumerate(cells[v]):
            sp = e["spawn"]
            for rep in range(D1_REPS):
                L = (np.asarray(sp["limiters"], float)
                     + jr.normal(0.0, D1_SIGMA, (len(sp["limiters"]), 3)))
                ap = (np.asarray(sp["att_p"], float)
                      + jr.normal(0.0, D1_SIGMA, 3))
                d1.append({"ep": i, "stage": "d1", "cell": f"v{v}",
                           "draw_idx": di, "rep": rep,
                           "reset_seed": spec["seed_base"] + 10_000 + i,
                           "spawn": {"limiters": L.tolist(),
                                     "limiter_v": [list(map(float, r))
                                                   for r in sp["limiter_v"]],
                                     "att_p": ap.tolist(),
                                     "att_v": list(map(float, sp["att_v"])),
                                     "att_speed": float(sp["att_speed"]),
                                     "src": f"a3e_{variant}_d1"}})
                i += 1
    return {"meta": {"variant": variant, "sealed": spec["sealed"],
                     "rng_base": spec["rng_base"],
                     "seed_base": spec["seed_base"],
                     "sigma_d1": D1_SIGMA, "k": K,
                     "composition": {"d0": len(d0), "d1": len(d1),
                                     "d0_reps": D0_REPS, "d1_reps": D1_REPS},
                     "doc": "docs/21 v0.3 SS3"},
            "stages": {"d0": {"episodes": d0}, "d1": {"episodes": d1}}}


def attach_zero_cache(bundle: dict, env_cfg: dict, m3, theta: float,
                      log=print) -> None:
    """dev only: zero-limiter + teacher-fire arm per d1 episode (frozen
    constants, stage=None -- the A-3d/A-3e eval contract)."""
    from shepherd.scripts.a3d_calibration import _lim_fn
    from shepherd.scripts.train_m3a import m3_eval_bundle
    from shepherd.train.phi_potential import teacher_fire

    def fin_fn(obs, flags):
        return np.array([0, 0, 0, 1.0 if teacher_fire(obs, theta) else 0.0],
                        np.float32)

    eps = bundle["stages"]["d1"]["episodes"]
    n_arr = 0
    for ep in eps:
        ev = m3_eval_bundle(env_cfg, m3, _lim_fn("zero", {}), fin_fn, 1,
                            int(ep["reset_seed"]), stage=None,
                            spawn_fn=lambda _i, sp=ep["spawn"]: dict(sp),
                            per_episode=True)
        r = ev["per_episode"][0]
        ep["zero_arrival"] = bool(r["arrival_capture"])
        ep["zero_reset_clean"] = bool(r["reset_clean"])
        n_arr += int(r["arrival_capture"])
        if ep["ep"] % 20 == 19:
            log(f"  zero-cache {ep['ep'] + 1}/{len(eps)} "
                f"(arrivals so far {n_arr})", flush=True)
    bundle["meta"]["zero_cache"] = {"arm": "zero+teacher", "stage": "d1",
                                    "zero_arrival_rate":
                                        round(n_arr / len(eps), 4)}


def write_with_manifest(bundle: dict, out: pathlib.Path,
                        inputs: dict) -> dict:
    out.write_text(json.dumps(bundle, indent=1))
    man = {"bundle": str(out), "sha256": _sha(out),
           "inputs_sha256": {k: _sha(pathlib.Path(p))
                             for k, p in inputs.items()},
           "gains": [1.0, 0.5],
           "gateb": ["brake", "lam2", "lam5", "lam10", "lam20",
                     "attpd_2_3", "attpd_4_4", "attpd_8_6"],
           "seed_map": {
               "episode_reset_seed": "spec.seed_base + 10000*stage_idx + i "
                                     "-> M3Adapter.reset_to(seed=...)",
               "spawn_jitter_seed": "default_rng(rng_base + 1000*k + v), "
                                    "one stream per cell, episode order",
               "bootstrap_seed": "777 (shared across all analyses; "
                                 "no independence claim)"},
           "doc": "docs/21 v0.3 SS3 (SHA-256 manifest)"}
    mp = out.with_suffix(".manifest.json")
    mp.write_text(json.dumps(man, indent=1))
    return man


def load_bundle(path: str, *, sealed_judgment: bool = False,
                repo_root: str = ".") -> dict:
    """Guarded loader (content-keyed; no force/bypass parameter exists)."""
    p = pathlib.Path(path)
    doc = json.loads(p.read_text())
    sealed = bool(doc.get("meta", {}).get("sealed"))
    mp = p.with_suffix(".manifest.json")
    if mp.exists():
        man = json.loads(mp.read_text())
        if man["sha256"] != _sha(p):
            raise PermissionError(f"bundle/manifest sha mismatch (tamper?): "
                                  f"{p}")
    elif sealed:
        raise PermissionError(f"sealed bundle without manifest refused: {p}")
    if sealed:
        if not sealed_judgment:
            raise PermissionError(
                "sealed bundle refused: only the single sealed judgment may "
                "load it (docs/21 v0.3 SS3; no bypass exists)")
        marker = pathlib.Path(repo_root) / CONSUMED_MARKER
        if marker.exists():
            raise PermissionError(
                f"sealed bundle already consumed ({marker}); re-evaluation "
                "is forbidden (docs/21 v0.3 stop rule 8)")
    return doc


def mark_sealed_consumed(repo_root: str = ".", note: str = "") -> pathlib.Path:
    marker = pathlib.Path(repo_root) / CONSUMED_MARKER
    marker.write_text(json.dumps({"consumed": True, "note": note}))
    return marker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3d_pilot.yaml")
    ap.add_argument("--bank", default="results/a3d_sbe_bank_v2.json")
    ap.add_argument("--validation",
                    default="results/a3d_bank_v2_validation.json")
    ap.add_argument("--robust-bank", default="results/a3_robust_bank_v2.json")
    ap.add_argument("--variants", nargs="+",
                    default=["dev_v2d1", "sealed_v2d1"])
    ap.add_argument("--skip-zero-cache", action="store_true",
                    help="test/debug only -- a dev bundle without the cache "
                         "cannot drive the L1/J1 gates")
    a = ap.parse_args()
    spawner = A3ESpawner(a.robust_bank, a.bank, a.validation)
    run_cfg = yaml.safe_load(open(a.config))
    env_cfg = yaml.safe_load(open(run_cfg["env_config"]))
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    for variant in a.variants:
        b = build_bundle(variant, spawner)
        if variant == "dev_v2d1" and not a.skip_zero_cache:
            print(f"{variant}: zero-cache (120 eps)...", flush=True)
            attach_zero_cache(b, env_cfg, m3, theta)
        out = pathlib.Path(f"results/a3e_bundle_{variant}.json")
        man = write_with_manifest(b, out, {
            "bank": a.bank, "validation": a.validation,
            "robust_bank": a.robust_bank, "config": a.config})
        print(f"wrote {out} sha256={man['sha256'][:12]} "
              f"(d0 {b['meta']['composition']['d0']} / "
              f"d1 {b['meta']['composition']['d1']}"
              f"{', zero-cached' if 'zero_cache' in b['meta'] else ''})",
              flush=True)


if __name__ == "__main__":
    main()
