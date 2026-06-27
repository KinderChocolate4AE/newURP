# M2 → L2 Bridge — Combined Claude Code Handoff: **S14 ∥ N1**

Two parallel work lanes that must both land before **L2 (MARL / outer-MAPPO)** can train on a
trustworthy signal. They are independent enough to run as **two separate Claude Code sessions**
(one per lane), but they touch overlapping files, so this single brief carries the shared context,
the coordination rules, and both full plans.

- **S14** — make the capture-viability surrogate `v_shot` *conservative* (sound over-approximation of
  the attacker's reachable set) so it stops reading optimistically.
- **N1** — replace the *tuned / ungrounded* SE(3) net-cone constants with values *derived* from the
  Paper-2 flexible-net forward model.

> **How to use:** Each of Part A (S14) and Part B (N1) is self-contained and can be pasted into its
> own CC session. Read §0–§1 first (shared constraints + coordination). For N1, also attach the file
> `N1_net_forward_model_spec.txt`. In every session: **plan first (plan mode), get approval, then implement.**

---

## 0. Shared context & global constraints (apply to BOTH lanes)

**Project.** `newURP`, M2/L1 is landed on `main` @ `d292d79`: cooperative-shaping *lever* demonstrated
(`Δv_shot > 0`), S1–S8 contract blob-frozen, 31 tests green. Two honest caveats remain open and are
exactly these two lanes — `results/m2_l1_status.md` logs them. Both feed L2.

**Repo.** `C:\Users\Teemo\Desktop\ANDES\URP\newURP` (local).

**Global constraints — verify before every commit:**

- **Torch-free / numpy only.** `shepherd/game/*` and any new model code stay torch/pettingzoo-free.
- **All 31 existing tests green:** `pip install -e .` then `pip install gymnasium pettingzoo imageio`
  (if missing), then `python -m pytest -q`.
- **Never modify the blob-frozen contract files** (frozen byte-for-byte across the whole M2 build):
  - `docs/03_formalization.md` — git blob `6a4786ee…`
  - `shepherd/game/exchange.py` — git blob `17a8c6c5…`
  - Guard: `git diff --name-only` must list **neither** before any commit.
- **Don't push** unless explicitly asked.

**Housekeeping (do once, in whichever session starts first):** delete a stale `.git/index.lock` if
present, plus two stray probe files `_host_probe.txt` and `_sync_probe.txt`. Leave `results/*.gif`
(untracked artifacts).

---

## 1. Coordination (why these are combined)

Both lanes edit overlapping files. Stay on separate branches and respect the decoupling rules below.

| File | S14 (lane 1) | N1 (lane 2) |
|---|---|---|
| `shepherd/game/viability.py` | **adds** `n_segments` conservative block | reads `_caught_se3_cone`; does **not** change it |
| `shepherd/env.py` | untouched (env keeps default `n_segments=1`) | **re-grounds** `cone_half_angle` / `cone_range_*` defaults |
| `configs/*.yaml` cone blocks | untouched | **re-grounds** `half_angle` / `range_max` / `net_radius` |
| `tests/test_viability.py` | **adds** tests (no edits to existing) | — |
| `tests/test_coma.py` | untouched | updates cone constants + DoD gate |
| `results/m2_l1_status.md` | edits the **S14** lines | edits the **N1** lines |

**Branches.** `fix/s14-conservative-reachset` (S14, already exists with an uncommitted scaffold) ∥
`feat/n1-net-grounding` (N1, create off `main`).

**Decoupling rules:**

1. **S14 test 4 (cone overshoot) must use a SYNTHETIC LOCAL cone fixture** — its own `net_apex`,
   `n_F`, `range_max`, `half_angle` defined in the test — **not** the global config constants. N1
   re-grounds those constants, so a S14 test that reads them would break on N1 merge. Use the demo
   *geometry* (τ=0.4, a_att_max=30 ⇒ `R = ½·a_max·τ² = 2.4`) with locally-defined cone params.
2. **Status-doc edits are in different sections** (S14 "Findings"/"Next" bullets vs N1 ones) → trivial
   merge.
3. **No shared test file** if S14 confines its tests to `test_viability.py` and N1 to `test_coma.py`.

**Merge order.** Independent: S14's conservative path is *opt-in* (`env.py:179` calls `v_shot` with
default `n_segments=1`, so env/DoD behavior is unchanged), and N1 only touches the cone *constants*.
Land in **either** order and rebase the second. If both are in flight, prefer landing **S14 first**
(smaller, opt-in, changes no constants), then **N1** (re-grounds constants + updates the DoD gate).

### Running the two lanes (sequential)
One folder, one lane at a time — simplest, zero cross-import risk. Do **S14 first** (smaller, opt-in,
changes no constants), land it, then **N1** off the updated `main`.

```bash
cd C:\Users\Teemo\Desktop\ANDES\URP\newURP
del .git\index.lock                       # clear the stale lock first (if present)
del _host_probe.txt _sync_probe.txt       # stray probe files (leave results\*.gif)

# Lane 1 — S14 (branch already exists, scaffold present):
git switch fix/s14-conservative-reachset
#   ...CC session: paste Part A, finish, `python -m pytest -q` green, commit...
git switch main
git merge --no-ff fix/s14-conservative-reachset      # land S14 before starting N1

# Lane 2 — N1 (fresh branch off the now-updated main):
git switch -c feat/n1-net-grounding main
#   ...CC session: paste Part B + attach N1_net_forward_model_spec.txt, finish, pytest green, commit...
git switch main
git merge --no-ff feat/n1-net-grounding
```

Because S14's conservative path is opt-in and N1 only re-grounds constants, running S14 → merge → N1
means N1 starts from a `main` that already contains S14. The decoupling rules above still apply (esp.
S14 test 4 uses a **synthetic local cone**, so N1's constant re-grounding can't break it); the only
file both touch is the two distinct sections of `results/m2_l1_status.md` (trivial).

---

## 2. Part A — **S14: Conservative reachable-set surrogate**

### Context
`v_shot` (`shepherd/game/viability.py`) scores per-shot capture/containment by Monte-Carlo sampling
the attacker's τ-reachable set. Today it uses a single-segment constant-accel model:
`endpoint = x + v·τ + ½·a·τ²` with one accel held over the whole horizon, sampled uniform-in-ball
(`‖a‖ ≤ a_max`). A real discrete closed-loop attacker re-plans (piecewise / bang-bang / curving), so
the surrogate **under-bounds** the true reachable set and reads optimistically. The demo logs this:
in `m2_clean_viability_demo`, `viability_capture=True` but `trajectory_capture=False` — "the attacker
overshoots and exits the cone." Before L2 trains on `v_shot`, the surrogate must become **conservative
(a sound over-approximation)**: it must stop claiming capture/containment the richer attacker can
break — i.e. `v_shot_worst` must drop to 0 wherever an extreme reachable point escapes.

An uncommitted scaffold (branch `fix/s14-conservative-reachset`, current `git diff`) already adds an
opt-in `n_segments` knob, a piecewise integrator, and a union path. **Known shortfall:** the
multi-segment block samples uniform-in-ball per segment (CLT-clusters away from the boundary) and uses
a tighter per-segment turn cone `ω·(τ/K)`, so the union "doesn't shrink" only trivially and never
actually OVER-bounds. This task replaces that random piecewise block with **extreme-point / boundary
sampling** that genuinely exposes escapes.

### Key facts established during exploration
- **Free double integrator (no turn limit):** the single-segment ball is already the EXACT reachable
  endpoint set. Max displacement-from-coast over `‖a(t)‖ ≤ a_max` is `a_max·τ²/2` in any direction
  (constant max-accel is optimal), so the true set = `B(x+vτ, ½·a_max·τ²)`. The gap is **not** set
  size — it's that uniform-in-ball under-samples the boundary sphere `‖a‖=a_max`, exactly where
  escapes live. **Fix = sample the boundary.**
- **Reduced-attitude (turn-limited):** the single fixed cone (½-angle `ω·τ` about the frozen heading)
  genuinely UNDER-approximates, because a closed-loop attacker re-points each step and curves past it.
  **Fix = max-rate turning sequences that sweep the full `±ω·τ` heading envelope** (sound over-approx).
- **Limiters:** a single parabola that gets killed can be dodged by a dogleg → bang-bang multi-segment
  controls expand the feasible set (sound: more reachable, never fewer).
- **Soundness direction:** over-approximating the attacker's reachable set can only find MORE escapes,
  never falsely claim containment. Boundary points ⊂ the true free ball (exact); the `±ωτ` cone is a
  deliberate over-approx of the single turn cone.
- `env.py:179` calls `v_shot` with default `n_segments=1` → env / DoD behavior unchanged; conservative
  path is fully opt-in. All 31 tests use the default path.

### Implementation — `shepherd/game/viability.py`
**Frozen / untouched (port fidelity):** `reachable_accels`, `_feasible_limiter`, `_feasible_turn`,
`_caught_point_mass`, `_caught_se3_cone`, `_v_shot_with_accels`, and the `n_segments <= 1` branch of
`v_shot`. These keep the prototype bit-exact.

**Rework the conservative block** (replace the scaffold's uniform-in-ball multi-segment generator; keep
the piecewise integrator `_segments_endpoints_feasible`, `_caught_mask`, `_assemble` — general & correct):

1. `_extreme_dirs(n_dir, seed)` → unit directions covering the sphere: deterministic axis-aligned
   `±x,±y,±z`, a Fibonacci-sphere grid, plus random directions. Including the axis-aligned + heading
   extremes makes the pure-forward `a_max` endpoint always present (deterministic demonstration).
2. `_boundary_accels(a_att_max, dirs)` → single-direction controls at `‖a‖ = a_max` (the exact
   boundary of the free reachable ball). For the no-turn / point_mass / cone case this is the workhorse
   that exposes the overshoot escape.
3. `_bangbang_segments(a_att_max, dirs, n_segments, …)` → K-segment max-magnitude controls with a
   direction switch partway (doglegs to dodge limiters; curves when directions rotate).
4. `_turn_curve_segments(e_att, omega, tau, a_att_max, n_segments)` → only when
   `attacker_turn_limited`: max-rate turning sequences sweeping the full `±ω·τ` envelope. **Precision
   note:** to actually *rotate* the heading, each segment's accel must sit at the **`ω·h` cone EDGE**
   of the current heading (it needs a component perpendicular to `v` — accel purely *along* the heading
   only grows speed and does not curve). Each step stays within `ω·h` of the current heading so it
   passes the per-segment check in `_segments_endpoints_feasible`, yet the heading sweeps to directions
   the single fixed `ω·τ` cone rejects.
5. `_v_shot_multiseg_union(…)`: union of
   - the **single-segment uniform-in-ball block** (verbatim — guarantees the conservative
     feasible/reachable set is a SUPERSET, so `v_shot_worst` is monotone non-increasing), and
   - the **extreme-point blocks** above (boundary spheres + bang-bang doglegs + turn curves),
     integrated through `_segments_endpoints_feasible` and judged via `_caught_mask`. Assemble with
     `_assemble` (R4 boxed-in split preserved). Factor the array-building into a private
     `_union_sets(…) -> (endpoints, feasible, caught)` so tests can assert the subset relationship
     directly; `_v_shot_multiseg_union` just calls `_assemble` on it.

Update the `v_shot` / `n_segments` docstrings: `n_segments>1` adds the conservative boundary +
bang-bang + turn-curve extreme-point set (not just more MC samples) and is the trustworthy capture
signal; `n_segments=1` is the frozen legacy surrogate. Torch-free / numpy only throughout.

### Tests — `tests/test_viability.py` (add, don't modify existing)
1. **Port fidelity unchanged** — existing `test_port_fidelity_*` and
   `test_reachable_accels_matches_prototype` must still pass untouched (verify, don't edit).
2. **No-shrink / superset** — on a fixture, every feasible single-segment endpoint is present in the
   conservative union's feasible collection (assert via `_union_sets`; true by construction since the
   single block is concatenated verbatim).
3. **Worst monotone** — `v_shot_worst(n_segments>1) <= v_shot_worst(1)` on a fixture (plus an
   equal-case fixture where both stay caught, to show it's not vacuously always 0).
4. **S14 fix in action (cone overshoot, SYNTHETIC LOCAL cone — see §1 decoupling rule 1)** — point an
   SE(3) cone forward with `range_max` set just below `center_x + R` (`R = ½·a_max·τ² = 2.4` at τ=0.4,
   a_att_max=30) so the pure-forward `a_max` boundary endpoint overshoots the axial band and exits the
   cone. Tune (against the fixed seed=0 sample, with a small margin so it's not razor-thin) so
   single-segment `v_shot_worst == 1.0` (uniform-in-ball never lands the exact forward extreme) but
   conservative `v_shot_worst == 0.0` (boundary set always includes it) — the surrogate now agrees with
   `trajectory_capture=False`. Define the cone params locally in the test; do NOT read global config
   constants (N1 re-grounds those).
5. **(Optional) Turn-curve escape** — turn-limited fixture where the curving sequence reaches an
   endpoint outside the single fixed `ω·τ` cone, flipping a contained worst to an escape.

### Docs
Update the S14 line(s) in `results/m2_l1_status.md` (the "Findings" S14 caveat and the "Next" S14
bullet): the conservative `n_segments>1` reachable set (boundary + bang-bang + turn-curve extreme
points) over-bounds the closed-loop attacker; on the demo cone geometry it now exposes the overshoot
escape (`v_shot_worst → 0`), agreeing with `trajectory_capture=False`, so `v_shot` no longer
under-bounds. Note it is opt-in (env/DoD default still single-segment) pending L2 adoption.

### S14 verification → commit on `fix/s14-conservative-reachset`
```
pip install -e .
pip install gymnasium pettingzoo imageio   # if missing
python -m pytest -q                          # all green (31 existing + new)
git diff --name-only                         # neither frozen blob file appears
```

---

## 3. Part B — **N1: Flexible-net forward model + cone grounding**

> **Attach `N1_net_forward_model_spec.txt`** to the CC session — the equations + parameters extracted
> from Xu et al., *Drones* 2025, 9, 190. It is the net **forward model only**; treat its flags D1–D3 as
> MUST-resolve before trusting numbers. **Branch:** create `feat/n1-net-grounding` off `main`.

### Why N1 exists (the actual goal)
The repo's SE(3) net-cone judge (`shepherd/game/viability.py::_caught_se3_cone`) currently uses
**TUNED / UNGROUNDED** constants, flagged dishonest in `results/m2_l1_status.md`:
`cone_half_angle = 0.43 rad`, `cone_range_max = 40 m`, `net_radius = 1.5 m`. They live in
`shepherd/env.py` (cone defaults ~lines 69–70; `net_radius` from scenario), `configs/m2_default.yaml`
+ `configs/m2_clean_viability_demo.yaml` `cone:` blocks, and `tests/test_coma.py` (`THETA=0.43`,
`net_radius`). **N1's job:** replace these with values DERIVED from the net forward model, with provenance.

### Central deliverable — the BRIDGE (this is the point of N1)
The spec gives net-dynamics outputs (`S_NP(t)`, coverage `C`, hang time `T`, launch envelope over
`X=[theta,v,m]`). It does **not** give the cone parameters. Build the mapping:
- `net_radius` ← equivalent-disk radius of the deployed effective area: `sqrt(S_NP/π)`. Sanity-check vs
  current 1.5 m (expect `S_NP ≈ 7 m²`; the 5.2×5.2 m net's 27 m² flat area projects down in flight).
- `range_max` ← integrate the block/net trajectory; take the range over the COVERAGE WINDOW (while
  `S_NP ≥ S_UAV`, i.e. until hang-time `T`). Sanity vs current 40 m.
- `half_angle` ← **sweep target approach angle OFF the finisher axis**; the half-angle where coverage
  (`S_NP ≥ S_UAV`) still holds. (Not a direct forward-model output — needs the sweep. Weakest link.)

Document each derivation + the operating point `(theta,v,m)` it assumes.

### Tasks
1. **Net forward model** in numpy (`prototypes/net_forward.py`, mirroring `prototypes/reachset.py`
   style): lumped-mass nodes, tension-only spring-damper (spec eq 1–3), aero drag+lift (eq 4–7) with
   `alpha = angle(segment tangent, relative airflow)` and `sin(alpha)=‖vhat × that‖`, Newton
   integration (eq 10). **EXPLICIT** time-stepping with a stability-safe `dt` (`dt < ~2/ω_max`,
   `ω_max ~ sqrt(k/m_node)` ⇒ here `~1.6e-3 s`) — assert the CFL-like bound or it blows up. Outputs:
   `S_NP(t)`, `S_E(t)`, max tension, `T`.
2. **Resolve spec flags** D1 (drag exponent: quadratic vs linear), D2 (hang-time eq discarded → measure
   `T` from rollout), D3 (`rho` 970 vs 1440 — affects damping `c`; `rho_air` assume 1.225) against the
   source before using numbers.
3. **Feasibility guards:** g3 rope stress `4·F_max/(π·d²) ≤ sigma_b`; g2 anti-balling `S_E(t) < S_NP(t)`.
4. **Grounding script/doc** that emits the three cone params (+ provenance) from 1–3 at the chosen
   operating point, with a comparison table vs the current tuned `0.43 / 40 / 1.5`.
5. **VALIDATION:** reproduce ≥1 paper data point (baseline 45°/60/35 g coverage, or the reported
   optimum) within a stated tolerance; record it as a regression test.
6. **Wire grounded values** into configs + env defaults + `tests/test_coma.py`. Grounding LEGITIMATELY
   changes the cone constants and therefore some DoD-gate expectations — update those tests
   deliberately and call out each change in the commit message. Then update `results/m2_l1_status.md`:
   flip N1 from PENDING to grounded and remove the "ungrounded/tuned" caveat where it no longer applies.

### N1 constraints (in addition to §0 globals)
- Do NOT alter the single-segment reachset port-fidelity tests (`test_port_fidelity_*`,
  `test_reachable_accels_matches_prototype`) — unrelated to the cone.
- Tests that change MUST change only because of grounding — itemize them in the commit message.

### N1 deliverables → commit on `feat/n1-net-grounding`
`prototypes/net_forward.py` + grounding script/doc + grounded cone params wired in + validation test +
status-doc update, all green. Start by reading `N1_net_forward_model_spec.txt`,
`shepherd/game/viability.py` (`_caught_se3_cone`), `shepherd/env.py`, the two config cone blocks, and
`tests/test_coma.py` — then give me the plan.

---

## 4. Shared verification (both lanes, before any commit)
```
pip install -e .
pip install gymnasium pettingzoo imageio     # if missing
python -m pytest -q                            # all green
git diff --name-only                           # must NOT list docs/03_formalization.md or shepherd/game/exchange.py
```
Frozen blobs to protect: `docs/03_formalization.md` (`6a4786ee…`), `shepherd/game/exchange.py` (`17a8c6c5…`).
