# N1 — Net-Physics Grounding of the SE(3) Cone Constants

**Goal.** Replace the M2 viability judge's **tuned / ungrounded** SE(3) net-cone constants
(`half_angle = 0.43 rad`, `range_max = 40 m`, `net_radius = 1.5 m`) with values **derived from a
flexible-net forward model**, with provenance — so capture stops resting on hand-tuned geometry.

**Sources.** `N1_net_forward_model_spec.txt` (equations) + `N1_paper_anchors.md` (reported outputs +
flag resolutions), both from Xu, Peng, Wu, *Drones* 2025, 9, 190 (DOI 10.3390/drones9030190), net
forward model only (Sec. 3); WPA/optimization narrative excluded.

**Artifacts.** `prototypes/net_forward.py` (forward model), `prototypes/ground_cone.py` (this bridge),
`tests/test_net_forward.py` (regression).

---

## Result (grounded constants)

| param | tuned | **grounded** | provenance | strength |
|---|---|---|---|---|
| `net_radius` | 1.50 m | **1.998 m** | `sqrt(S_NP/π)`, `S_NP = 12.54 m²` (paper baseline); sim reproduces 1.998 | **STRONG** |
| `half_angle` | 0.43 rad | **0.067 rad** (3.8°) | `arctan(net_radius / range_max)` — tightest cone containing the net's capture cylinder | self-consistent |
| `range_max` | 40.0 m | **29.8 m** | conservative `min{sim coverage-window travel 29.8, paper-T travel 69.0}` | **WEAK (flagged)** |
| `range_min` | 0.0 m | 0.0 m | unchanged | — |

Operating point: **θ=45°, v=60 m/s, m_block=35 g** (paper baseline). Single free knob **ρ_air = 1.513**
(calibrated; **~24% above atmospheric 1.225** — it absorbs the model's drag shortfall, so "≈ atmospheric"
is a generous description; not a fudge but flagged). Baseline sim: `S_NP@20m = 12.54 m²` (paper 12.54),
`C = 2.3175` (paper 2.3174), `F_max = 14.7 N`, rope stress `3.95 MPa ≤ 30`.

---

## Forward model (resolved flags)

Lumped-mass (11×11 = 121 nodes), tension-only spring-damper (eq 1–3, `Tmag≥0` clamp), Williams aero
(eq 4–7), gravity, symplectic Euler with a hard CFL bound (`dt < 2/ω_max`, ω off the light interior
node). Diagonal shear springs (else a square axial mesh has zero shear stiffness → garbage area).

- **D1 — drag/lift LINEAR in ‖v‖** (`drag_power=1.0`) to *reproduce* the paper. Quadratic is exposed as
  a documented physical-correction variant (`drag_power=2.0`, will not match paper numbers).
- **D2 — hang-time Eq 11 DROPPED as a cross-check.** As transcribed it gives `T(45,60,35)=2.54 s` vs
  the reported `1.853 s` (off 0.69 s; the one flagged α-typo is numerically negligible → PDF extraction
  unreliable beyond it). Not used.
- **D3 — ρ_rope = 970 kg/m³.** The Table-1 1440 conflict is benign: ρ_rope enters only damping
  `c = 2ζ√(ρ k L0 S)`, not node mass (mass = measured `m_w`=170 g lumped). 970→1440 shifts baseline
  `F_max` by <1 N, `S_NP` by <0.01 m². Micro-checked.

**Effective area = true SILHOUETTE** (rasterized union), not the per-cell-sum. Required: when the net
balls up, the per-cell sum *over-counts* folded overlap and floors at ~2.2 m², whereas the silhouette
correctly collapses toward 0 (min 0.92 m²). The cell-sum is kept only as the over-count diagnostic
(N1 risk 7).

---

## Bridge derivations

1. **`net_radius` (STRONG).** The net's deployed effective interception area at the baseline is the
   paper's back-solved `S_NP = S_UAV/(1 − ln C) = 2/(1 − ln 2.3174) = 12.54 m²`. Equivalent-disk radius
   `√(12.54/π) = 1.998 m`. The calibrated sim independently reproduces `S_NP@20m = 12.54` (so 1.998),
   confirming the baseline is physically in-regime. **1.5 → 2.0 m.**

2. **`range_max` (WEAK — flagged).** The axial reach where the net is capture-effective. Two estimates:
   (a) sim coverage-window centroid travel (while silhouette ≥ S_UAV) = **29.8 m**; (b) ∫v over the
   paper-reported hang time (1.853 s) = **69.0 m**. The sim's collapse timing is **not trustworthy**
   (see limitations), and an over-large `range_max` inflates the cone and can artificially rescue the
   lever, so we adopt the **conservative (smaller) 29.8 m**. **40 → 29.8 m.**

3. **`half_angle` (self-consistent).** The cone half-angle is grounded geometrically as the *tightest*
   cone whose lateral half-width still contains the net's physical capture cylinder (radius
   `net_radius`) out to `range_max`: `arctan(1.998/29.8) = 0.067 rad ≈ 3.8°`. The plan's original idea —
   sweep the target-approach angle and take where the deployed silhouette still covers S_UAV — is
   **degenerate** here: the deployed net is a 3D billowed blob whose silhouette exceeds S_UAV from
   almost any direction (the sweep pins at the ~80° ceiling), conflating net *shape* with
   capture-direction tolerance. **0.43 → 0.067 rad.** The tuned 0.43 rad implied a net radius of
   `range·tan(0.43) ≈ 14 m` at 30 m — i.e. it was a wildly over-sized, optimistic cone. Shrinking it is
   exactly the correction N1 exists to make.

---

## Validation (what is / isn't anchored)

**Validated (`tests/test_net_forward.py`):**
- Baseline effective area reproduced: `S_NP@20m ≈ 12.54 m²`, `C ≈ 2.3174` (note: ρ_air is *calibrated*
  to this point, so it is an anchor, not independent evidence — see limitation 3).
- Self-consistency invariants: mass conservation (`Σ m_node = m_w + 4 m_block`), rope stress `≤ σ_b`,
  silhouette collapses below 5% while the per-cell sum floors (risk 7), CFL assertion fires on too-large
  `dt`, D3 density swap benign.
- `k_diag` sensitivity: grounded `net_radius` stable across diagonal-stiffness scale ×0.5/×1/×2 (the
  grounding is not an artifact of the numerical shear spring).
- **Secondary diagnostic (ordering only, pre-fixed 20 m):** config ordering is correct —
  `S_NP@20m`: lo (25,50,25) 9.1 < base 12.5 < hi (65,90,65) 18.8 (paper 12.1 / 12.54 / 24.4).

**NOT validated — honest limitations:**
1. **Hang time T not reproduced.** Flat-init (no folded→opening transient) + no wrapping/entanglement
   (spec scope: *"geometric coverage, not wrapping"*) → the net **breathes** (collapses ~0.66 s then
   re-opens) instead of latching. Sim first-collapse ≈ 0.66 s vs paper 1.853 s. Therefore all
   sim-temporal quantities (incl. the `range_max` sim estimate) are untrustworthy → `range_max` is
   flagged WEAK and grounded conservatively.
2. **Table-3 config spread under-predicted (~23%).** The flat-init model lacks the config-dependent
   opening peak, so the multi-point S_NP spread (paper 12.1–24.4) is compressed; only the *ordering* is
   right (secondary diagnostic). Full 9-row Table-3 reconfirmation needs the PDF (human lane).
3. **Baseline is calibration-anchored.** With one free knob (ρ_air) fit to the baseline, baseline
   reproduction is by construction; the independent signal is the config ordering + self-consistency.

**Meta (honest closure).** Spatial grounding is firm (`net_radius`, `half_angle`); temporal is not
achievable with this model (`range_max` weak/flagged, T paper-sourced). N1's purpose is honest
grounding, not perfect net dynamics — this is the correct close. Folded-init fidelity is **deferred**.

---

## Downstream / DoD impact — flip is REAL physics (discriminator-confirmed)

Wiring the grounded cone into the M2 gate **flips** the lever demo (capture disappears). A judge-vs-judge
discriminator + a reachable-radius comparison show this is **robust physics, not a cone-approximation
artifact**:

- **Physical heart — net_radius vs reachable radius.** In the DoD fixture (`a_att_max=30`,
  `τ_deploy=0.4`) the attacker's τ-reachable ball has radius
  `R_reach = ½·a_att_max·τ² = 2.40 m`. The grounded `net_radius = 2.0 m < 2.40 m`, so the net **cannot
  cover the full escape spread** — capture fails *robustly*, independent of cone-vs-sphere and of
  `range_max`. This is driven by the STRONG `net_radius` (and the fixture's attacker agility), not by the
  weak `range_max`.
- **Discriminator (grounded, scripted shaping).** `point_mass` r=2.0 → no capture (does not even reach
  the fire threshold); `se3_cone` 3.8° → no capture; even a 2.25 m sphere fires but its worst-case
  escapes (`v_shot_worst=0`). The sphere fails too ⇒ the cone's conservatism is **not** the cause.
- **Correction to an earlier framing.** A prior decomposition that froze `half_angle` at the tuned 0.43
  while shrinking `range_max` suggested "`range_max` isn't the culprit." That is misleading: in the
  grounded world `half_angle = arctan(net_radius/range_max)` is a *function* of `range_max`, and the cone
  is narrower than the physical 2 m net at close range. The honest statement is geometric — **the 2 m net
  cannot contain the 2.4 m reachable ball**; the cone is one expression of it.

**Capture condition (stated honestly, not over-claimed).** Worst-case capture (`v_shot_worst=1`) requires
`net_radius ≥ R_reach = ½·a_att_max·τ²`. PI-confirmed against actual v_shot on the fixture:
`net_radius=2.0 → soft=0.584, worst=0` (escape exists); `2.25 → soft=0.829, fires but worst=0`
(fires-then-escapes); `2.4 → soft=1.0, worst=1` (contains). The honest claim is therefore **"this 2.0 m
net cannot contain THIS attacker's reachable ball"**, NOT "physical nets cannot capture." The door stays
open and **L2's job is quantified**: shrink the *shaped* reachable radius from 2.4 m to below 2.0 m
(~17%) via limiters — the lever already moves v_shot (`Δv_shot>0`), L2 must move it *enough*.

> Footnote: `R_reach` is conditioned on the fixture's **attacker agility** (`a_att_max=30`, `τ=0.4`),
> themselves scenario parameters — the flip is conditioned on them, not universal.

The lever **survives** grounding (`Δv_shot>0`; max_delta 0.46–0.94 across judges) — only *absolute
capture* dies. The M2 capture demonstration was an artifact of the over-sized tuned cone (effective
radius `≈ range·tan(0.43) ≈ 13.7 m`). This is the honest outcome the S14∥N1 effort was built to reach:
the **core science (shaping moves v_shot) is robust**; what dies is absolute capture under an unphysical
cone — now a quantified L2 target, not a failure.

**Decision (PI).** Both grounded judges fail ⇒ flip is robust ⇒ the honest close is **(a) re-baseline
the M2 DoD under the physical cone**: keep the lever (`Δv_shot>0`) as the demonstrated result, drop
*absolute capture* from the DoD claim, and retain the tuned cone only as an explicitly-labelled
*optimistic showcase*. Wiring (`tests/test_coma.py` `THETA`→0.067, `range_max`→29.8, `net_radius`→2.0,
demo expectations) is pending that call. The judge `_caught_se3_cone` itself is untouched.
