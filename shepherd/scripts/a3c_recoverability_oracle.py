"""A-3c U-1: short-horizon recoverability oracle (docs/16; docs/09 (ll) adoption 3).

Question (reviewer's top gap): are reset-NONCLEAN spawns from the R1..R3
distributions actually recoverable -- can SOME limiter action sequence, over
k=1..3 steps, reshape the geometry so that an oracle fire at step k+1 commits
clean (and captures)? Without this number, the next training failure cannot
be attributed among {physics impossible / exploration too hard / credit wrong}.

Method (cheap by construction):
  * draw spawns from bank witness + sigma jitter; keep reset-nonclean ones
    (reset clean read at the spawn's own eval seed);
  * during the reshape phase NOTHING stochastic moves the dynamics (no fire
    -> no commit -> adversary dodge state unchanged; unions affect flags only)
    so candidate limiter constant-accel vectors (4x3, |a|<=a_lim_max) are
    rolled forward with PURE kinematics (backend integrator replicated:
    v += a*dt with speed clip, p += v*dt; attacker via the actual
    scripted_adversary_action; finisher static);
  * ONE union evaluation per candidate endpoint (pre-move state at step k+1)
    decides clean; capture-grade = worst >= 1; robust recheck of the winner
    on fresh seeds.

Outputs per (witness, sigma, k): recoverable@k rate over spawns, action
volume (fraction of candidates succeeding | recoverable), best delta v_soft,
winner robust rate. Pre-registered proceed threshold lives in docs/16 SS2.

CLI (numpy-only; chunk with --witness/--sigma for 45s sandboxes):
  PYTHONPATH=. python3 -m shepherd.scripts.a3c_recoverability_oracle \
      --bank results/a3_robust_bank.json --out results/a3c_recoverability.json
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.agents.adversary import scripted_adversary_action
from shepherd.game import viability as V
from shepherd.train.spawn_bank import APEX, load_t0, spawn_from

# frozen constants (configs/m2_l2_train.yaml; == probe/oracle values)
TAU, A_ATT, KILL_R, THETA, DT = 0.4, 30.0, 2.0, 0.9, 0.05
V_NOM, OMEGA_ATT = 20.0, 8.0
A_LIM, V_LIM = 30.0, 80.0
TARGET = np.zeros(3)
CONE = dict(judge="se3_cone", net_apex=list(APEX), n_F=[1.0, 0.0, 0.0],
            theta_net=0.067, range_min=0.0, range_max=29.847)
SEED0 = 41_000_000            # disjoint from train/eval/heldout/oracle bands
ROBUST = (5, 6, 7)


def ev_state(p_att, v_att, L, seed):
    u = V.build_reachable_union(p_att, v_att, tau=TAU, a_att_max=A_ATT,
                                n=2000, n_segments=4, seed=seed, **CONE)
    r = V.eval_union_with_limiters(u, np.asarray(L, float), KILL_R)
    return (bool((not r.boxed_in) and r.v_shot_soft >= THETA),
            float(r.v_shot_soft), float(r.v_shot_worst), bool(r.boxed_in))


def roll(spawn, acc, k):
    """Pure-kinematics k-step rollout (reshape phase, no fire): limiters under
    constant accel `acc` (4,3); attacker under the actual scripted policy."""
    L = np.asarray(spawn["limiters"], float).copy()
    Lv = np.zeros_like(L)
    p, v = np.asarray(spawn["att_p"], float).copy(), np.asarray(
        spawn["att_v"], float).copy()
    for _ in range(k):
        adv = scripted_adversary_action(
            p, v, target=TARGET, net_center=p + v * TAU,
            finisher_p=np.asarray(APEX, float), limiters=list(L),
            kill_radius=KILL_R, a_att_max=A_ATT, omega_att_max=OMEGA_ATT,
            v_nominal=V_NOM, dt=DT, committed=False, repel_margin=1.0)
        v2 = v + np.asarray(adv["a"], float) * DT
        sp = np.linalg.norm(v2)
        if sp > 24.0:                       # adversary_v_max-ish clamp
            v2 = v2 * (24.0 / sp)
        p = p + v2 * DT
        v = v2
        Lv2 = Lv + acc * DT
        spd = np.linalg.norm(Lv2, axis=1, keepdims=True)
        Lv2 = np.where(spd > V_LIM, Lv2 * (V_LIM / np.maximum(spd, 1e-9)), Lv2)
        L = L + Lv2 * DT
        Lv = Lv2
    return p, v, L


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="results/a3_robust_bank.json")
    ap.add_argument("--witness", type=int, default=None)
    ap.add_argument("--sigma", type=float, default=None,
                    help="single sigma (else 0.02,0.05,0.1)")
    ap.add_argument("--n-spawns", type=int, default=12)
    ap.add_argument("--n-cands", type=int, default=32)
    ap.add_argument("--ks", default="1,2,3")
    ap.add_argument("--out", default="results/a3c_recoverability.json")
    a = ap.parse_args()
    t0s = load_t0(a.bank)
    sigmas = [a.sigma] if a.sigma is not None else [0.02, 0.05, 0.1]
    ks = [int(x) for x in a.ks.split(",")]
    out_p = pathlib.Path(a.out)
    rep = (json.loads(out_p.read_text()) if out_p.exists()
           else {"meta": {"n_spawns": a.n_spawns, "n_cands": a.n_cands,
                          "seed0": SEED0, "robust_seeds": list(ROBUST),
                          "a_lim_max": A_LIM}, "rows": []})
    rng = np.random.default_rng(7)
    idxs = range(len(t0s)) if a.witness is None else [a.witness]
    for i in idxs:
        t0 = t0s[i]
        for sig in sigmas:
            spawns = []
            tries = 0
            while len(spawns) < a.n_spawns and tries < a.n_spawns * 40:
                tries += 1
                sp = spawn_from(t0, rng, sigma_pos=float(sig), sigma_vel=0.02)
                seed = SEED0 + tries + int(sig * 1000) * 977 + i * 131071
                clean0, v0, _, _ = ev_state(sp["att_p"], sp["att_v"],
                                            sp["limiters"], seed)
                if not clean0:              # reset-NONCLEAN only
                    spawns.append((sp, seed, v0))
            row = {"src": t0.src, "sigma": sig, "n": len(spawns),
                   "reset_nonclean_frac": (len(spawns) / max(tries, 1))}
            for k in ks:
                rec = vol = 0
                dvs, rob = [], []
                for sp, seed, v0 in spawns:
                    accs = rng.uniform(-A_LIM, A_LIM,
                                       (a.n_cands, 4, 3)) / np.sqrt(3.0)
                    hits, best_dv, best_acc = 0, -1.0, None
                    for c in range(a.n_cands):
                        p, v, L = roll(sp, accs[c], k)
                        ok, vs, worst, _ = ev_state(p, v, L, seed + 7919 * (k + 1))
                        if ok and worst >= 1.0:
                            hits += 1
                            if vs - v0 > best_dv:
                                best_dv, best_acc = vs - v0, accs[c]
                    if hits > 0:
                        rec += 1
                        vol += hits / a.n_cands
                        dvs.append(best_dv)
                        rr = 0
                        for rs in ROBUST:
                            p, v, L = roll(sp, best_acc, k)
                            ok, _, worst, _ = ev_state(p, v, L, seed * 31 + rs)
                            rr += int(ok and worst >= 1.0)
                        rob.append(rr / len(ROBUST))
                n = max(len(spawns), 1)
                row[f"recoverable@{k}"] = rec / n
                row[f"action_volume@{k}"] = (vol / rec) if rec else 0.0
                row[f"best_dv@{k}"] = float(np.mean(dvs)) if dvs else None
                row[f"winner_robust@{k}"] = float(np.mean(rob)) if rob else None
            rep["rows"] = [r for r in rep["rows"]
                           if not (r["src"] == row["src"]
                                   and r["sigma"] == row["sigma"])] + [row]
            ks_str = " ".join(f"r@{k}={row[f'recoverable@{k}']:.2f}"
                              f"(vol {row[f'action_volume@{k}']:.2f})"
                              for k in ks)
            print(f"[{i}] {t0.src} sigma={sig}: n={row['n']} "
                  f"nonclean_frac={row['reset_nonclean_frac']:.2f} {ks_str}")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(rep, indent=1))
    print("->", out_p)


if __name__ == "__main__":
    main()
