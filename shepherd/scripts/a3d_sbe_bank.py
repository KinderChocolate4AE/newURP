"""A-3d SBE bank: synthetic backward-extension spawn generator (docs/17 SS1-SS2).

Question this tool answers (docs/17 SS0): R0 witnesses START at the capture
window, so a reverse curriculum has no t-k approach trajectory to spawn from.
G0's physics says a STANDING limiter cannot chase a moving window -- recovery
must begin from a state that is already ARRIVING with velocity. SBE synthesizes,
per robust witness, a closed-form deceleration-arrival profile for each limiter
(anchor = nominal ring slot -> L*) plus a back-extrapolated straight-line
attacker; because AnalyticBackend is a plain integrator (v'=clip(v+a*dt);
p'=p+v'*dt, velocity-then-position), a backward-constructed state sequence IS a
valid forward trajectory whenever the clips never bind. Only cells that pass a
4-condition verification gate are written to results/a3d_sbe_bank.json.

Method (witness x k in {1,2,4,8} x draw 12):
  * limiter arrival (closed form): u_i = cone-jittered unit(L*_i - anchor_i);
    v0 ~ U[0.3,0.8]*(a_lim_max*k*dt) -> |a_i| = v0/(k*dt) in [9,24] < 30. Constant
    decel a_i = -(v0/(k*dt))*u_i; v_j = v0*(1-j/k)*u_i (velocity AFTER j steps);
    p_start = L*_i - sum_{j=1..k} v_j*dt. Closed form is then VERIFIED by a
    forward roll and any (linear) residual is folded back into p_start once
    (a start-pos shift maps affinely to the arrival, so this makes arrival exact
    regardless of the closed-form's exact indexing).
  * attacker (back-extrapolation + forward re-verify shoot): t-k p =
    [x*+v*k*dt,0,0], v = [-v*,0,0], attacker driven by the REAL
    scripted_adversary_action (committed=False, v_nominal PINNED to v*,
    repel_margin 1.0, omega 8.0). t=0 miss -> 1D x-offset shoot (<=3).
  * repel pre-screen: attacker-limiter distance > kill_radius*1.2 over the whole
    combined roll; violation -> redraw directions (<=10), else discard the draw.

Verification gate (inclusion, ALL required, docs/17 SS1):
  (1) combined forward roll (limiter demo accels + scripted attacker) reproduces
      the witness at t=0 (limiter pos 5cm / vel 0.1 m/s; attacker pos 5cm / vel 2%);
  (2) t=0 state is clean at the witness union_seed (ev_state, a3c-style union);
  (3) robust: clean frequency over fresh seeds 7..16 (10) >= 0.9;
  (4) every demo step |v| <= 72 (=0.9*v_max) and |a| <= 24.

CLI (numpy-only, torch-free; chunk with --witness/--k for 45s sandboxes and
MERGE into an existing --out, mirroring a3c_recoverability_oracle):
  PYTHONPATH=. python3 -m shepherd.scripts.a3d_sbe_bank \
      --bank results/a3_robust_bank.json --out results/a3d_sbe_bank.json \
      --witness 0 --k 1 --draws 12
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.agents.adversary import scripted_adversary_action
from shepherd.game import viability as V
from shepherd.train.spawn_bank import APEX, load_t0

# --- frozen constants (configs/m2_l2_train.yaml; == probe/oracle values) ------
DT = 0.05                       # train.dt
TAU = 0.4                       # train.tau_deploy
A_ATT = 30.0                    # train.a_att_max
KILL_R = 2.0                    # train.kill_radius
THETA = 0.9                     # fire_gate.theta_fire
A_LIM_MAX = 30.0                # train.a_lim_max
V_LIM = 80.0                    # train.limits.limiter_v_max
ADV_V_MAX = 30.0                # train.limits.adversary_v_max
OMEGA_ATT = 8.0                 # env.step scripted_adversary_action omega_att_max
TARGET = np.zeros(3)            # train.layout.target
# nominal ring anchors: replicate make_env._ring(4, [8,0,0], 5.0) -- SBE anchor
# per docs/17 SS1 (import avoided so this stays a self-contained numpy tool).
RING_C = np.array([8.0, 0.0, 0.0])
RING_R = 5.0
N_LIM = 4
CONE = dict(judge="se3_cone", net_apex=list(APEX), n_F=[1.0, 0.0, 0.0],
            theta_net=0.067, range_min=0.0, range_max=29.847)   # == config cone

# gate tolerances / seeds (docs/17 SS1)
TOL_POS = 0.05                  # limiter+attacker pos tol [m]
TOL_LIM_VEL = 0.1               # limiter arrival vel tol [m/s]
TOL_ATT_VEL = 0.02              # attacker vel tol [fraction of v*]
REPEL_FACTOR = 1.2              # attacker-limiter clearance = kill_radius*1.2
ROBUST_SEEDS = tuple(range(7, 17))      # fresh clean seeds 7..16 (10)
ROBUST_MIN = 0.9
CONE_JITTER = np.deg2rad(15.0)          # +-15 deg arrival-direction cone
A_DEMO_MAX = 24.0                       # 0.8*a_lim_max: demo accel ceiling
V_DEMO_MAX = 0.9 * V_LIM                # 72: demo speed ceiling (gate 4)
SEED0 = 42_000_000                      # disjoint band (a3c oracle used 41e6)


def _ring():
    """Replica of make_env._ring(4, RING_C, RING_R) -- same slot angles."""
    return np.array([[RING_C[0],
                      RING_C[1] + RING_R * np.cos(2 * np.pi * i / N_LIM),
                      RING_C[2] + RING_R * np.sin(2 * np.pi * i / N_LIM)]
                     for i in range(N_LIM)])


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.array([1.0, 0.0, 0.0])


def _cone_jitter(u, rng, max_ang=CONE_JITTER):
    """Rotate unit vector u by U[0,max_ang] about a random perpendicular axis."""
    u = _unit(u)
    ref = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    perp = _unit(ref - (ref @ u) * u)
    phi = float(rng.uniform(0.0, 2 * np.pi))            # random azimuth in tangent plane
    axis = _unit(np.cos(phi) * perp + np.sin(phi) * np.cross(u, perp))
    ang = float(rng.uniform(0.0, max_ang))
    c, s = np.cos(ang), np.sin(ang)
    return _unit(u * c + np.cross(axis, u) * s + axis * (axis @ u) * (1.0 - c))


# --- integrator replicas (AnalyticBackend semantics: v'=clip(v+a*dt); p'=p+v'*dt)
def _lim_roll(p0, v0, a_demo, k):
    """Isolated open-loop limiter roll (single limiter). Returns final (p, v)."""
    p, v = p0.copy(), v0.copy()
    for _ in range(k):
        v = v + a_demo * DT
        sp = float(np.linalg.norm(v))
        if sp > V_LIM:
            v = v * (V_LIM / sp)
        p = p + v * DT
    return p, v


def _att_step(p, v, L, v_star):
    """One scripted-attacker step (committed=False, v_nominal pinned to v*)."""
    adv = scripted_adversary_action(
        p, v, target=TARGET, net_center=p + v * TAU,
        finisher_p=np.asarray(APEX, float), limiters=[row for row in L],
        kill_radius=KILL_R, a_att_max=A_ATT, omega_att_max=OMEGA_ATT,
        v_nominal=v_star, dt=DT, committed=False, repel_margin=1.0)
    v2 = v + np.asarray(adv["a"], float) * DT
    sp = float(np.linalg.norm(v2))
    if sp > ADV_V_MAX:
        v2 = v2 * (ADV_V_MAX / sp)
    return p + v2 * DT, v2


def _combined_roll(L0, Lv0, a_demo, att_p0, att_v0, v_star, k):
    """Combined k-step forward roll (open-loop limiter demo + scripted attacker).

    Returns (L_end, Lv_end, att_p_end, att_v_end, min_att_lim_dist). The attacker
    action reads the PRE-step limiter positions (env.step order)."""
    L, Lv = L0.copy(), Lv0.copy()
    ap, av = att_p0.copy(), att_v0.copy()
    min_d = float(np.min(np.linalg.norm(L - ap, axis=1)))   # t-k clearance
    for _ in range(k):
        ap_next, av_next = _att_step(ap, av, L, v_star)      # uses pre-step L
        Lv = Lv + a_demo * DT
        spd = np.linalg.norm(Lv, axis=1, keepdims=True)
        Lv = np.where(spd > V_LIM, Lv * (V_LIM / np.maximum(spd, 1e-9)), Lv)
        L = L + Lv * DT
        ap, av = ap_next, av_next
        min_d = min(min_d, float(np.min(np.linalg.norm(L - ap, axis=1))))
    return L, Lv, ap, av, min_d


def ev_state(p_att, v_att, L, seed):
    """Clean/capture-grade readout at a state (a3c-style standalone union)."""
    u = V.build_reachable_union(np.asarray(p_att, float), np.asarray(v_att, float),
                                tau=TAU, a_att_max=A_ATT, n=2000, n_segments=4,
                                seed=seed, **CONE)
    r = V.eval_union_with_limiters(u, np.asarray(L, float), KILL_R)
    return (bool((not r.boxed_in) and r.v_shot_soft >= THETA),
            float(r.v_shot_soft), float(r.v_shot_worst), bool(r.boxed_in))


# --- one draw --------------------------------------------------------------
def _draw_directions(anchors, Lstar, k, rng):
    """Sample per-limiter arrival direction (cone-jittered) + v0 -> demo accel,
    start vel, analytic start pos (before residual correction)."""
    u = np.zeros((N_LIM, 3))
    v0 = np.zeros(N_LIM)
    a_demo = np.zeros((N_LIM, 3))
    v_start = np.zeros((N_LIM, 3))
    p_start = np.zeros((N_LIM, 3))
    for i in range(N_LIM):
        ui = _cone_jitter(_unit(Lstar[i] - anchors[i]), rng)
        v0i = float(rng.uniform(0.3, 0.8)) * (A_LIM_MAX * k * DT)
        ai = v0i / (k * DT)                              # |accel|
        assert ai <= A_DEMO_MAX + 1e-6, f"|a|={ai} > {A_DEMO_MAX}"
        u[i], v0[i] = ui, v0i
        a_demo[i] = -ai * ui                             # constant decel
        v_start[i] = v0i * ui
        # p_start = L* - sum_{j=1..k} v_j*dt, v_j = v0*(1-j/k)*u
        js = np.arange(1, k + 1)
        sum_vj = v0i * float(np.sum(1.0 - js / k)) * DT
        p_start[i] = Lstar[i] - sum_vj * ui
    return u, v0, a_demo, v_start, p_start


def synth_draw(t0, k, rng, anchors, Lstar):
    """Synthesize one draw -> (entry|None, drop_reason). None = discarded."""
    v_star = float(t0.v)
    # direction draws + repel pre-screen (redraw <=10)
    ap0 = np.array([t0.x + v_star * k * DT, 0.0, 0.0])
    av0 = np.array([-v_star, 0.0, 0.0])
    a_demo = v_start = p_start = None
    for _ in range(10):
        _, _, a_demo, v_start, p_start = _draw_directions(anchors, Lstar, k, rng)
        # residual correction: fold the (linear) closed-form residual into p_start
        for i in range(N_LIM):
            p_end, _ = _lim_roll(p_start[i], v_start[i], a_demo[i], k)
            p_start[i] = p_start[i] + (Lstar[i] - p_end)
        _, _, _, _, min_d = _combined_roll(p_start, v_start, a_demo, ap0, av0,
                                           v_star, k)
        if min_d > KILL_R * REPEL_FACTOR:
            break
    else:
        return None, "repel"

    # attacker 1D x-offset shoot (<=3) so t=0 attacker pos reproduces
    for _ in range(3):
        _, _, ap_end, av_end, _ = _combined_roll(p_start, v_start, a_demo,
                                                 ap0, av0, v_star, k)
        dx = float(t0.x - ap_end[0])
        if abs(dx) <= TOL_POS:
            break
        ap0 = ap0 + np.array([dx, 0.0, 0.0])            # Newton (slope ~1)

    # final combined roll -> gate (1) reproduction errors
    L_end, Lv_end, ap_end, av_end, _ = _combined_roll(
        p_start, v_start, a_demo, ap0, av0, v_star, k)
    lim_pos_err = float(np.max(np.linalg.norm(L_end - Lstar, axis=1)))
    lim_vel_err = float(np.max(np.linalg.norm(Lv_end, axis=1)))
    att_pos_err = float(np.linalg.norm(ap_end - np.array([t0.x, 0.0, 0.0])))
    att_vel_err = float(abs(np.linalg.norm(av_end) - v_star) / max(v_star, 1e-9))
    roll_ok = (lim_pos_err <= TOL_POS and lim_vel_err <= TOL_LIM_VEL
               and att_pos_err <= TOL_POS and att_vel_err <= TOL_ATT_VEL)

    # gate (4): demo clip non-contact (|v|<=72, |a|<=24) over the k demo steps
    clip_ok = True
    for i in range(N_LIM):
        p, v = p_start[i].copy(), v_start[i].copy()
        if float(np.linalg.norm(a_demo[i])) > A_DEMO_MAX + 1e-6:
            clip_ok = False
        for _ in range(k):
            v = v + a_demo[i] * DT
            if float(np.linalg.norm(v)) > V_DEMO_MAX:
                clip_ok = False
            p = p + v * DT

    # gate (2) t=0 clean at witness union_seed + gate (3) robust over 7..16
    clean_t0, _, _, _ = ev_state(ap_end, av_end, L_end, int(t0.union_seed))
    rob = [ev_state(ap_end, av_end, L_end, s)[0] for s in ROBUST_SEEDS]
    robust_frac = float(np.mean(rob))

    kept = bool(roll_ok and clean_t0 and robust_frac >= ROBUST_MIN and clip_ok)
    demo_accels = np.repeat(a_demo[None, :, :], k, axis=0)   # k x 4 x 3 (constant)
    entry = {
        "witness": t0.src, "k": int(k), "kept": kept,
        "spawn": {"limiters": p_start.tolist(), "limiter_v": v_start.tolist(),
                  "att_p": ap0.tolist(), "att_v": av0.tolist(),
                  "att_speed": v_star},
        "demo_accels": demo_accels.tolist(),
        "verify": {"roll_err_m": max(lim_pos_err, att_pos_err),
                   "lim_pos_err": lim_pos_err, "lim_vel_err": lim_vel_err,
                   "att_pos_err": att_pos_err, "att_vel_err": att_vel_err,
                   "clean_t0": clean_t0, "robust_frac": robust_frac,
                   "clip_ok": clip_ok, "roll_ok": roll_ok},
    }
    reason = "" if kept else (
        "roll" if not roll_ok else "clean" if not clean_t0 else
        "robust" if robust_frac < ROBUST_MIN else "clip")
    return entry, reason


# --- CLI / merge -----------------------------------------------------------
def _cell_key(src, k):
    return f"{src}::k{k}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="results/a3_robust_bank.json")
    ap.add_argument("--out", default="results/a3d_sbe_bank.json")
    ap.add_argument("--witness", type=int, default=None,
                    help="witness index (else all robust witnesses)")
    ap.add_argument("--k", type=int, default=None,
                    help="single k (else 1,2,4,8)")
    ap.add_argument("--draws", type=int, default=12)
    a = ap.parse_args()

    t0s = load_t0(a.bank)
    ks = [a.k] if a.k is not None else [1, 2, 4, 8]
    idxs = range(len(t0s)) if a.witness is None else [a.witness]
    anchors = _ring()

    out_p = pathlib.Path(a.out)
    meta = {"constants": {"dt": DT, "tau": TAU, "a_att": A_ATT,
                          "kill_radius": KILL_R, "theta": THETA,
                          "a_lim_max": A_LIM_MAX, "v_lim": V_LIM,
                          "adv_v_max": ADV_V_MAX, "ring_c": RING_C.tolist(),
                          "ring_r": RING_R},
            "tol": {"pos": TOL_POS, "lim_vel": TOL_LIM_VEL,
                    "att_vel": TOL_ATT_VEL, "repel_factor": REPEL_FACTOR},
            "seeds": {"robust": list(ROBUST_SEEDS), "seed0": SEED0},
            "generated_per_cell": {}, "kept_per_cell": {}}
    if out_p.exists():
        prev = json.loads(out_p.read_text())
        meta["generated_per_cell"] = prev["meta"].get("generated_per_cell", {})
        meta["kept_per_cell"] = prev["meta"].get("kept_per_cell", {})
        entries = list(prev.get("entries", []))
    else:
        entries = []

    cells = []
    for i in idxs:
        t0 = t0s[i]
        Lstar = np.asarray(t0.limiters, float)
        for k in ks:
            key = _cell_key(t0.src, k)
            # merge: drop prior entries for this (witness,k) cell before regen
            entries = [e for e in entries
                       if _cell_key(e["witness"], e["k"]) != key]
            rng = np.random.default_rng(SEED0 + i * 100003 + k * 9973)
            kept = gen = 0
            for _ in range(a.draws):
                gen += 1
                entry, _reason = synth_draw(t0, k, rng, anchors, Lstar)
                if entry is None:                        # repel-discarded draw
                    continue
                if entry["kept"]:
                    kept += 1
                    entries.append(entry)
            meta["generated_per_cell"][key] = gen
            meta["kept_per_cell"][key] = kept
            cells.append((key, kept, gen))

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps({"meta": meta, "entries": entries}, indent=1))

    print("cell (witness::k)                          kept/generated")
    total_kept = total_gen = 0
    for key, kept, gen in cells:
        flag = "  <-- WIPED-OUT (design-void signal)" if kept == 0 else ""
        print(f"  {key:<40} {kept:>3}/{gen:<3}{flag}")
        total_kept += kept
        total_gen += gen
    print(f"  {'TOTAL (this run)':<40} {total_kept:>3}/{total_gen:<3}")
    print(f"  bank entries now: {len(entries)}")
    print("->", out_p)


if __name__ == "__main__":
    main()
