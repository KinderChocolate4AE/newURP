# A1 Dynamic Connectivity — status & next tasks (2026-07-21)

Handoff note written after a sandbox container reclaim interrupted A1. Records what
is DONE, what is PENDING, and the next tasks. Canonical live state is
`project_a3d_state` memory; append-only log is `docs/09`.

## Recovery state
- The cloud sandbox container was reclaimed during an idle gap; the local clone
  reverted to an earlier snapshot. **All work committed through (gggg) is intact on
  the device** (`C:\Users\Teemo\Desktop\ANDES\URP\newURP`), md5-verified — docs/09
  (through gggg), c1_persistence/n1_temporal/c1_moveA0 scripts+results all present.
- The only casualty was the in-progress `c1_a1_connectivity.py` (never committed).
  It has been reconstructed from context, re-verified (A1a reproduces exactly), and
  committed to the device this session.
- Mount caveat: `device_stage_files` returned a STALE docs/09 snapshot (qqq-era);
  `device_bash` reads correctly (gggg present). Trust device_bash / md5, not staging,
  for docs/09. **Do NOT overwrite the device docs/09 with a local copy** — the local
  working tree is behind. Append (hhhh) onto the device's gggg base.

## A1a — DONE ✅  verdict A1A_DYNAMICALLY_CONNECTED (both cells)
- Treated the A0 static-safe witness as position-only; constructed the full state
  (limiter/attacker p+v) via the pre-commit A-3e `reset_to` contract.
- **Terminal viability**: reset_to the witness box (perp≈r_kill, zero velocity) +
  attacker fixture, fire, exact replay → **tier 4** (cap 0.52, grounded clearance
  +0.10 [cell 2.6/2.1] / +0.20 [2.6/2.0], no penetration). The safe terminal is a
  REAL dynamic fire state, not positional-only.
- **Predecessor connectivity** (k=1..4, matched AND unmatched limiter velocity): all
  connect on exact replay (coast reaches tier 4). Fires ~step 0-1; limiters barely
  move in the 0.4 s window so clearance holds.
- **Key reframe**: A0's "dynamic unsolved" was purely about REACHING the box from
  nominal — the box itself is dynamically viable and locally self-connecting.
- Artifact: `shepherd/scripts/c1_a1_connectivity.py` (--stage a1a),
  `results/c1_corridor/c1_a1.json`.

## A1b — PRELIMINARY ⏳ (NOT completed; needs a proper run)
- Question: does a role-agnostic search, warm-started from the standoff terminal
  (NOT the E1 crowd), connect the NOMINAL reset to a Tier≥4 safe fire on exact replay?
- Preliminary probes (bounded budget, sandbox):
  - Standoff corrals from nominal reach ≤ tier 1: `ring4` too sparse to box
    (max v_soft 0.18); `press2_block2` boxes (v_soft→1.0) but never fires lane-safe
    (tier 0 — over-box p_feas=0, or not simultaneous with clearance).
  - Two-arm CEM (U unrestricted / S + radial-band/angular-gap/relative-velocity
    auxiliary costs) at small budget did NOT connect (tier 0-1). Arm S pulls toward
    the standoff band (radDev 0.85 vs U 2.40) but still no eligible lane-safe fire.
  - Failure causes (decomposed): (1) no eligible fire — v_soft≥θ reached but p_feas=0
    over-box, or not simultaneous with clearance; (2) radial off-band.
- Compute lesson: full-NOMINAL rollout_g3 ≈ 1.2 s each → a real 2-arm CEM is many
  minutes; **run A1b on the SERVER, not the sandbox** (sandbox background/long jobs
  die on idle gaps — that is what interrupted this session).

## Next tasks (in order)
1. **Run A1b properly on the server** — `c1_a1_connectivity.py --stage a1b` (or both),
   both cells, adequate budget (pop≥24, iters≥15, t_open≈16-24). Warm from the
   standoff (press2_block2), NOT the E1 crowd. Verdict on REAL quantities only
   (v_soft≥θ ∧ p_feas>0 ∧ grounded clearance≥0 ∧ no penetration). Discovery = ONE
   nominal seed Tier≥4 exact replay. Per horizon save exact replay, best cap/clr
   margin, max angular gap, radial-band violation, failure time. On failure, keep the
   radial/angular/timing/post-fire decomposition. Consider a true backward horizon
   ladder (H=2→4→6→8→nominal) via reset_to with progressively more-spread limiter
   starts, warm-starting each rung — cheaper early rungs, and it isolates the horizon
   at which the connect breaks.
2. **Add docs/09 (hhhh)** documenting A1a (DONE) + A1b (result of task 1), on the
   DEVICE's gggg base (use device_bash / verified md5; the staging mount was stale).
3. **If A1b discovers (Tier≥4 exact replay)** → open corridor bank / BC / backward
   curriculum / MARL at the identified cell(s). **If not** → the decomposition names
   the fix (likely an angular-sealing standoff formation that fires with p_feas>0 while
   holding perp≥lane); iterate the formation/search before MARL. Do NOT start MARL
   until a Tier≥4 exact replay appears (user gate).
4. **folded-deployment model (init='folded')** remains the PARALLEL track (from ffff);
   full Move C opens only when a grounded folded model shows R_cap≥R_req at the 10 m
   crossing. Does not block A1.

## Design invariants (carried)
- Move B verdict fixed: HISTORY_COMMITMENT_KINEMATICS_CONFIRMED /
  CASE_B_CAPTURE_NOT_VALIDATED / GROUNDED_LOWER_BOUND_FAIL / TEMPORAL_PREMISE_UNRESOLVED.
- Primary cell (2.6, 2.1), secondary (2.6, 2.0), θ=0.9 FIXED (don't relax geometry
  and judge together). η = r_kill/(r_net_dir + r_body 0.2 + m_safety 0.2).
- No hardcoded boxer/shaper/agent slots. Auxiliary costs = search guidance only.
- Case A judge and E1 unchanged. "impossible" banned → "not found at tested budget".
