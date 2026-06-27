# N1 — Paper Validation Anchors (Xu, Peng, Wu, *Drones* 2025, 9, 190)

Numbers pulled from the **open-access PDF** (MDPI, DOI 10.3390/drones9030190) to anchor N1's Task-5
regression test. This **complements** `N1_net_forward_model_spec.txt` (the spec has the equations;
this has the reported outputs + resolves the spec's D1–D3 flags). Attach BOTH to the N1 CC session.

> Honesty note: exact bit-reproduction is impossible (the paper never states `rho_air`, and it uses
> ABAQUS/Explicit which we re-implement in numpy). So the regression test is **"reproduce within a
> stated tolerance"**, not exact match. That is still a real external anchor — far stronger than
> self-consistency alone. Recommended approach = **Both**: paper anchor (below) + self-consistency
> invariants + Eq-11 self-check.

## Primary anchor — baseline design (Table 8 + Table 9)
Baseline launch config **(θ = 45°, v = 60 m/s, m = 35 g)**, with **S_UAV = 2 m²**:

| Metric | Reported | Notes |
|---|---|---|
| Coverage rate **C** | **2.3174** | Eq 12: `C = exp((S_NP − S_UAV)/S_NP)` |
| Hang time **T** | **1.8529 s** | from net-area-to-5% rollout (Eq 11) |
| ⇒ implied **S_NP** | **≈ 12.54 m²** | back-solved: `S_NP = S_UAV/(1 − ln C) = 2/(1−0.8405) = 12.54` |
| ⇒ equiv. disk radius | **≈ 2.0 m** | `sqrt(12.54/π)`. **Reconcile vs current tuned `net_radius = 1.5`.** |

## Secondary anchors — Pareto frontier (Tables 8 & 9)
| Sol. | θ (°) | v (m/s) | m (g) | C | T (s) |
|---|---|---|---|---|---|
| Baseline (test) | 45 | 60 | 35 | 2.3174 | 1.8529 |
| Frontier A | 65 | 90 | 25 | 2.4802 | 1.2965 |
| Frontier B | 55 | 70 | 25 | 2.4399 | 1.4828 |
| Frontier C | 65 | 60 | 35 | 2.4359 | 1.6948 |
| **Frontier D** (chosen) | 45 | 50 | 25 | 2.4257 | 1.9287 |
| **Frontier E** (chosen) | 35 | 50 | 25 | 2.3904 | 2.2373 |
| Frontier F | 25 | 50 | 25 | 2.3041 | 2.7602 |

Paper picks **D & E** as optima: D → coverage +4.7% vs baseline (large-cross-section targets);
E → hang time +20.74% (faster targets). No single scalar θ*/v*/m* — it's a Pareto set.
Use the **trend/ordering** (e.g. C monotone in the right direction across the frontier) as an extra check.

## Table 3 (effective interception area S_NP, 125 orthogonal sets) — PARTIAL
The PDF text exposed only **9 of 125 rows** (rest truncated). Useful as range/sanity, not full reproduction:
- S_NP range seen: **12.10 m² (25°,50,25 g) … 24.40 m² (65°,90,65 g)**.
- The exact baseline row (45°,60,35) is **not** in the recovered rows — use the back-solved 12.54 m² above.
- Levels (Table 2): θ ∈ {25,35,45,55,65}°, v ∈ {50,60,70,80,90} m/s, m ∈ {25,35,45,55,65} g.
- If you want the full 125-row table, grab it from the PDF's Table 3 image directly.

## Resolved spec flags D1–D3
- **D1 (drag/lift order): the paper is LINEAR in ‖v‖.** Eqs (4),(5) printed as
  `F = ½ · e · ρ_air · C · d · ‖v‖ · L` — first power, **no ‖v‖²**. The spec's "restored quadratic"
  **contradicts the paper.** To *reproduce* the paper's C/T, use **linear**. If you instead use the
  physically-standard quadratic, you are *correcting* the model and will NOT match their numbers —
  make that an explicit, documented choice (reproduce-then-note, don't silently switch).
- **D2 (hang time Eq 11): RECOVERED verbatim** (use this directly for the T anchor / self-check):
  ```
  T(α,v,m) = 6.882e−06·m³ − 0.0007043·m² − 0.0188·m + 5.104
           + (4.593e−07·m³ + 8.117e−05·m² − 0.00451·m + 0.05297)·v
           + (−1.042e−07·m³ + 7.506e−06·m² + 0.0006415e−05·m − 0.07627)·α
           + (1.502e−09·m³ − 2.706e−07·m² + 1.539e−05·m − 0.0001825)·v²
           + (4.253e−09·m³ − 7.551e−07·m² + 4.315e−05·m − 0.0007084)·v·α
           + (4.544e−10·m³ − 1.117e−08·m² − 5.634e−06·m + 0.0004625)·α²
  ```
  ⚠ Printed PDF typo in the α-linear block: `0.0006415e−05·m` carries a double exponent (likely
  `6.415e−09·m`). Sanity-check the polynomial: `T(45,60,35)` should land near the reported **1.8529 s**;
  if not, the typo term is the suspect — pin it by matching the baseline.
- **D3 (density): conflict is REAL and unreconciled in the paper.** Table 1 prints **1.44 g/cm³
  (1440 kg/m³)**; the §6 numerical example prints **ρ = 970 kg/m³** (nylon). **Use 970** — it's the
  physically correct nylon value AND the value behind the reported C/T example. Note the discrepancy.

## Other parameters (verbatim)
- Net: **5.2 m × 5.2 m**, mesh **520 mm × 520 mm** (⇒ 10×10), total net mass **170 g**, nylon.
- Rope: diameter **d = 2.181167 × 10⁻³ m** (⇒ S = πd²/4 ≈ 3.74 × 10⁻⁶ m², not printed),
  **E = 0.305 GPa**, damping ratio **0.05**, Poisson **0.3**, max allowable tensile stress **[σ_b] = 30 MPa**.
- **S_UAV = 2 m²** (UAV maneuvering cross-section, used in C).
- Aero coeffs (Eqs 6,7): **C_D = 1.1·sin³α + 0.022**, **C_L = 1.1·sin²α·cosα** (Williams).
- **ρ_air: NOT stated anywhere in the paper** → keep the spec's assumed 1.225 kg/m³; treat as a free
  parameter and run a sensitivity / calibrate it so the baseline C/T match.
- Solver: ABAQUS 2022/Explicit + MATLAB R2020b, **1 s** horizon.

## Suggested Task-5 regression test (anchor design)
1. **Spatial:** sim → measure S_NP at the target plane → `C = exp((S_NP−2)/S_NP)`; assert
   `C ≈ 2.3174` at baseline within tolerance (and ⇒ S_NP ≈ 12.5 m²). Pin a tolerance you can justify
   (numpy-vs-ABAQUS + unknown ρ_air ⇒ e.g. ±15%); calibrate ρ_air to hit baseline, then it's fixed.
2. **Temporal:** assert hang time `T ≈ 1.8529 s` at baseline; cross-check against Eq 11.
3. **Trend:** Pareto ordering across A–F (C and T move the right way with θ/v/m).
4. **Self-consistency (keep these too):** mass conservation (Σ m_node = m_w + 4·m_block), rope stress
   `4·F_max/(π·d²) ≤ 30 MPa`, anti-balling `S_E < S_NP`, monotone collapse to 5% area.
