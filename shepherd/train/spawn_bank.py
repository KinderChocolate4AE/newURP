"""A-3 L-reverse spawn bank (docs/13 SS1/SS2, R-1..R-5 ratified; docs/09 (dd)).

T0 = capture-grade clean-fire witnesses measured by the P4 probe
(results/p4_probe/probe_s*.json `refined_best`), reconstructed into TRAIN-ONLY
spawn dicts for M3ShapingEnv.reset_to().

Frame contract (STRICT, no silent transforms): the probe pinned the net apex
at [2,0,0] with axis [1,0,0]; these must equal the env layout finisher_p0 and
the composition root's finisher e0 (m2_l2_train.yaml does). On mismatch we
raise instead of rotating (docs/13 SS1).

Sampling (R1..R4): T0 + Gaussian jitter (sigma_pos on limiters+attacker
position, sigma_vel fractional on attacker speed) + attacker rewind
(rewind_dx meters BACK along the approach direction = away from the target).
R5/nominal: spawn=None -> ordinary frozen reset (family randomization as
usual). The attacker's post-spawn behavior stays the env's scripted policy
(v_nominal unchanged -- spawn injects state only; documented caveat).

Re-verification (R-1 gate): every reconstructed T0 state is replayed through
the FROZEN composition root (stage=None) with the probe's own union seed;
capture-grade must reproduce (v_soft >= theta AND p_feasible > 0 AND
worst >= 1) or the state is DROPPED. All dropped -> raise (A-3 design void,
docs/13 SS1). Fresh-seed robustness is logged as a diagnostic only.

CLI (numpy-only):
  PYTHONPATH=. python3 -m shepherd.train.spawn_bank \
      --probe-glob 'results/p4_probe/probe_s*.json' \
      --env-config configs/m2_l2_train.yaml --out results/a3_t0_verify.json
"""
from __future__ import annotations

import argparse
import copy
import glob as globmod
import json
import pathlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

__all__ = ["T0State", "load_t0", "check_frame", "spawn_from", "verify_t0"]

APEX = (2.0, 0.0, 0.0)      # probe net apex == layout finisher_p0 (STRICT)
N_F = (1.0, 0.0, 0.0)       # probe cone axis == composition-root finisher e0
ROBUST_SEEDS = (7, 8, 9)    # diagnostic-only fresh union seeds


@dataclass(frozen=True)
class T0State:
    src: str
    x: float
    v: float
    union_seed: int
    limiters: Tuple[Tuple[float, float, float], ...]
    v_soft: float
    worst: float
    p_feas: float


def load_t0(probe_glob: str) -> List[T0State]:
    """Parse probe JSONs -> capture-grade refined_best witnesses (docs/13 SS1)."""
    out: List[T0State] = []
    paths = sorted(globmod.glob(probe_glob))
    if not paths:
        raise FileNotFoundError(f"no probe files match {probe_glob!r}")
    for path in paths:
        d = json.loads(pathlib.Path(path).read_text())
        cst = d.get("constants", {})
        if "net_apex" in cst and not (
                np.allclose(cst["net_apex"], APEX) and np.allclose(cst["n_F"], N_F)):
            raise ValueError(f"{path}: probe frame != apex {APEX}/axis {N_F} "
                             "(STRICT, docs/13 SS1 -- no silent transform)")
        for s in d.get("states", []):
            rb = s.get("refined_best")
            if not (s.get("capture_grade_found") and rb):
                continue
            out.append(T0State(
                src=f"{pathlib.Path(path).name}:x{s['x']:g}v{s['v']:g}u{s['union_seed']}",
                x=float(s["x"]), v=float(s["v"]),
                union_seed=int(s["union_seed"]),
                limiters=tuple(tuple(float(c) for c in row)
                               for row in rb["limiters"]),
                v_soft=float(rb["v_soft"]), worst=float(rb["worst"]),
                p_feas=float(rb["p_feas"])))
    if not out:
        raise ValueError(f"no capture-grade T0 states under {probe_glob!r}")
    return out


def check_frame(env_cfg: Dict) -> None:
    """STRICT frame check: layout finisher_p0 must equal the probe apex."""
    fin_p0 = np.asarray(env_cfg["train"]["layout"]["finisher_p0"], float)
    if not np.allclose(fin_p0, APEX):
        raise ValueError(f"layout finisher_p0 {fin_p0.tolist()} != probe apex "
                         f"{list(APEX)} (docs/13 SS1: raise, don't transform)")


def spawn_from(t0: T0State, rng: Optional[np.random.Generator] = None, *,
               sigma_pos: float = 0.0, sigma_vel: float = 0.0,
               rewind_dx: float = 0.0) -> Dict:
    """One spawn dict from a T0 witness (+R-stage perturbation, docs/13 SS2)."""
    L = np.asarray(t0.limiters, float).copy()
    att_p = np.array([t0.x, 0.0, 0.0])
    att_v = np.array([-t0.v, 0.0, 0.0])
    if rng is not None and sigma_pos > 0.0:
        L = L + rng.normal(0.0, sigma_pos, L.shape)
        att_p = att_p + rng.normal(0.0, sigma_pos, 3)
    if rng is not None and sigma_vel > 0.0:
        att_v = att_v * (1.0 + float(rng.normal(0.0, sigma_vel)))
    if rewind_dx > 0.0:
        vn = float(np.linalg.norm(att_v))
        att_p = att_p - (att_v / max(vn, 1e-9)) * rewind_dx   # back along approach
    return {"limiters": L, "att_p": att_p, "att_v": att_v, "src": t0.src}


def verify_t0(states: List[T0State], env_cfg: Dict,
              robust_seeds: Tuple[int, ...] = ROBUST_SEEDS
              ) -> Tuple[List[T0State], List[Dict]]:
    """R-1 gate: replay each T0 through the FROZEN composition root; drop
    non-reproducing states; raise if none survive (docs/13 SS1)."""
    from shepherd.env_m3 import M3Params                       # lazy (no cycle)
    from shepherd.train.make_env_m3 import make_m3_train_env
    check_frame(env_cfg)
    theta = float(env_cfg["fire_gate"]["theta_fire"])
    rw = env_cfg["reward"]
    m3 = M3Params(l1=float(rw["lambda1"]), l2=float(rw["lambda2"]),
                  l3=float(rw["lambda3"]))

    def readout(seed: int, t0: T0State) -> Dict:
        env, _, _ = make_m3_train_env(copy.deepcopy(env_cfg), m3, stage=None)
        obs, _ = env.reset_to(spawn_from(t0), seed=seed)
        tail = np.asarray(obs[env.possible_agents[0]], float)[-3:]
        return {"v_soft": float(tail[0]), "worst": float(tail[1]),
                "p_feas": float(tail[2])}

    survivors, report = [], []
    for t0 in states:
        r0 = readout(t0.union_seed, t0)
        ok = (r0["v_soft"] >= theta and r0["p_feas"] > 0.0
              and r0["worst"] >= 1.0)
        rob = []
        for s in robust_seeds:                                 # diagnostic only
            rr = readout(s, t0)
            rob.append(bool(rr["v_soft"] >= theta and rr["p_feas"] > 0.0))
        row = {"src": t0.src, "probe": {"v_soft": t0.v_soft, "worst": t0.worst,
                                        "p_feas": t0.p_feas},
               "env_at_union_seed": r0, "pass": bool(ok),
               "robust_clean_frac": float(np.mean(rob)) if rob else None}
        report.append(row)
        if ok:
            survivors.append(t0)
    if not survivors:
        raise RuntimeError("T0 re-verification: ALL states dropped -- A-3 "
                           "design void per docs/13 SS1 (log to docs/09)")
    return survivors, report


def main() -> None:
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-glob", default="results/p4_probe/probe_s*.json")
    ap.add_argument("--env-config", default="configs/m2_l2_train.yaml")
    ap.add_argument("--out", default="results/a3_t0_verify.json")
    ap.add_argument("--robust-seeds", default="7,8,9")
    a = ap.parse_args()
    env_cfg = yaml.safe_load(open(a.env_config))
    states = load_t0(a.probe_glob)
    seeds = tuple(int(s) for s in a.robust_seeds.split(",") if s != "")
    survivors, report = verify_t0(states, env_cfg, robust_seeds=seeds)
    for r in report:
        e = r["env_at_union_seed"]
        print(f"{'PASS' if r['pass'] else 'DROP':>4} {r['src']:<40} "
              f"v_soft={e['v_soft']:.3f} worst={e['worst']:.3f} "
              f"p_feas={e['p_feas']:.2e} robust={r['robust_clean_frac']}")
    print(f"survivors: {len(survivors)}/{len(states)}")
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"report": report,
                               "survivors": [t.src for t in survivors]}, indent=1))
    print("->", out)


if __name__ == "__main__":
    main()
