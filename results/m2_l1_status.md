# M2 / L1 — Status Summary

Branch `build/m2-l1-reduced-attitude-env` (7 commits) · 31 tests green · the frozen S1–S8 contract (`docs/03_formalization.md`) and `shepherd/game/exchange.py` (S9/M3 reserved) were untouched throughout.

## Status (honest)
| Item | State |
|---|---|
| M2/L1 env infrastructure | **DONE** |
| M2 clean *viability* demonstration | **DONE** |
| M2 physical / *trajectory* capture demonstration | **NOT YET** |
| S14 surrogate-fidelity issue | **EXPLICITLY LOGGED** |
| N1 physical-net grounding | **PENDING** |

**One-line claim.** Cooperative shaping raises the (optimistic) per-shot viability value — the **lever**, `Δv_shot > 0`, robust. **Physical capture is not yet established**; it is open along two axes (S14 surrogate fidelity + N1 net grounding), both logged, neither conflated with the lever.

## What was built (torch-free, lab-runnable)
- `shepherd/game/` (sim-agnostic): `viability` (SE(3) `se3_cone` + `point_mass` judges; R4 `boxed_in` split; CRN `_v_shot_with_accels` shared-sample core), `roles` (`FireGate`, `c_fire = θ_fire·B`), `finisher_fsm` (LOADED→DEPLOYING→LOCKED→SPENT; irreversible; single gate `v_shot_soft ≥ θ_fire`), `exchange` (RESERVED, untouched).
- `shepherd/sim/`: `interface` (EnvBackend ABC) + `analytic` (9D reduced-attitude kinematics).
- `shepherd/agents/`: reactive goal-constrained adversary; `hold_position` baseline (COMA u_L⁰).
- `shepherd/env.py`: PettingZoo ParallelEnv at **top level** (keeps `game/*` PettingZoo-free; backend **injected** — env never imports `sim.analytic`).
- `shepherd/scripts/rollout_gif.py`: composition root + GIF renderer.

## Findings
1. **Lever is real.** `u_L ≠ u_L⁰ ⇒ Δv_shot > 0` (shaping moves the per-shot value) — in the env, not just the numpy proxy.
2. **Regime-dependent.** Clean closure needs enough agile limiters (~8, high accel) vs a slow threat; the conservative default *boxes* (containment) instead. → the M3 regime-map seed.
3. **SE(3) cone > point-mass sphere.** The directional cone gives a cleaner lever — validates the 6-DOF/SE(3) modeling choice.
4. **Capture is model-dependent — two honest caveats, shown on the demo panel, not conflated:**
   - **S14 (surrogate fidelity).** The single-segment *continuous* reachable set under-bounds the discrete *closed-loop* attacker → `v_shot` is **optimistic**. In `m2_clean_viability_demo`: `viability_capture = True` but `trajectory_capture` (same cone) `= False` — the actual attacker overshoots and exits the cone.
   - **N1 (physical-net grounding).** The SE(3) cone (`half_angle ≈ 0.43`, `range_max = 40`, `net_radius = 1.5`) is **ungrounded/tuned** — pending Paper 2 net physics (Xu et al., *Drones* 9:190). `tight_net_probe_1p5m = False` (a tight physical net would miss).

## Artifacts
- `results/m2_rollout_default.gif` — conservative default scenario: **boxing/containment**, honestly labeled, **not** a clean capture.
- `results/m2_clean_viability_demo.gif` — representative clean **viability**-threshold demo under the (ungrounded) cone, with explicit **S14 + N1** caveats printed on the panel.

## DoD (`docs/03` §C) — what is / isn't shown
- **Shown:** `Δv_shot > 0` (lever, robust); clean (non-boxed) viability threshold crossing with fewer wasted shots than the hold baseline — *under the cone surrogate*.
- **NOT shown:** actual-trajectory / physical-net capture (S14 + N1 open).

## Next
- **S14 (recommended first).** Make the reachable-set surrogate conservative (multi-segment / proper bound) so `v_shot` is trustworthy — otherwise L2 trains on, and a learned policy is fooled by, an optimistic signal. Torch-free.
- **N1 (Hyunjun human-lane, WP-A4/CP-4).** Ground the cone (`half_angle`, `range`) to Paper 2 net physics; replace the tuned values with a finite physical range. *(Tuned constants live in `configs/m2_default.yaml` + `configs/m2_clean_viability_demo.yaml` cone blocks, `shepherd/env.py` `cone_half_angle`/`cone_range_max` defaults, and `tests/test_coma.py`.)*
- **L2 (MAPPO/COMA, torch / lab venv).** Replace scripted policies with a learned shaping policy → measured frontier. The learning-goal core; meaningful once S14 makes `v_shot` trustworthy.
- **M3.** Sweep the capture↔containment regime boundary (this build's seed) → paper headline result.

---
*Generated at L1 milestone; the representative artifact and tests show the lever and the two surrogate caveats without conflation.*
