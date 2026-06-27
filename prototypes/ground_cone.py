"""N1 BRIDGE: flexible-net forward model -> SE(3) cone constants (with provenance).

Maps the net forward-model outputs (prototypes/net_forward.py) to the three SE(3)
net-cone parameters that the M2 viability judge (shepherd/game/viability.py::
_caught_se3_cone) currently sets to TUNED / UNGROUNDED values:
    cone_half_angle = 0.43 rad,  cone_range_max = 40 m,  net_radius = 1.5 m.

Grounding philosophy (decided with PI -- "honest grounding, not perfect net dynamics"):
  * net_radius  -- STRONG, baseline-anchored. = sqrt(S_NP/pi) at the paper baseline
    effective area (back-solved S_NP=12.54 m^2, which the calibrated sim reproduces).
  * half_angle  -- baseline-anchored. Sweep the target-approach direction off the
    deployed-net axis on the baseline deployed snapshot; half_angle = max off-axis
    angle where the projected silhouette still covers S_UAV.
  * range_max   -- WEAK (flagged). The sim's collapse timing is NOT trustworthy
    (flat-init no-wrapping net breathes; hang time not reproduced). We report several
    estimates and adopt the CONSERVATIVE (smallest) one, because an over-large
    range_max inflates the cone volume and can artificially rescue the lever -- so it
    is the #1 suspect at the DoD flip check.

Limitations recorded honestly (NOT hidden): the model reproduces the baseline
effective area but UNDER-predicts the Table-3 config spread (~23%), and does not
reproduce hang time (temporal). See docs/n1_net_grounding.md.

Pure numpy. Run: `python prototypes/ground_cone.py`.
"""
from __future__ import annotations
import numpy as np
import net_forward as nf

# current TUNED / UNGROUNDED constants being replaced
TUNED = dict(half_angle=0.43, range_max=40.0, net_radius=1.5)
BASELINE = dict(theta_deg=45, v0=60, m_block=0.035)     # paper baseline operating point
PAPER_BASELINE_SNP = nf.S_NP_BASELINE                   # 12.54 m^2 (back-solved from C)
PAPER_BASELINE_T = 1.8529                               # paper hang time [s] (NOT reproduced)


def half_angle_geometric(net_radius, range_max):
    """Cone half-angle [rad] = the TIGHTEST cone whose lateral half-width still
    contains the physical net's capture cylinder (radius net_radius) out to
    range_max:  theta = arctan(net_radius / range_max). Self-consistent with the
    other two grounded constants; conservative (a wider cone would over-claim capture).

    NOTE: the plan's original idea (sweep the target-approach angle and take where the
    deployed silhouette still covers S_UAV) is DEGENERATE here -- the deployed net is a
    3D billowed blob whose silhouette exceeds S_UAV from almost any direction (sweep
    pins at the ~80 deg ceiling), conflating net SHAPE with capture-direction tolerance.
    The geometric subtended-angle is the defensible grounding instead."""
    return float(np.arctan(net_radius / range_max))


def ground(verbose=True):
    """Compute the three grounded cone constants + provenance. Returns a dict."""
    r = nf.simulate(rho_air=nf.RHO_AIR_CAL, **BASELINE)

    # --- net_radius (STRONG, baseline-anchored) ---
    net_radius = float(np.sqrt(PAPER_BASELINE_SNP / np.pi))      # = 1.998 m
    sim_net_radius = r["net_radius"]                            # sim confirmation

    # --- range_max (WEAK; conservative = smallest estimate) ---
    sim_cov_travel = r["range_cov_travel"]                      # sim coverage-window travel
    paper_T_travel = nf.travel_to_time(r["t"], r["cum_travel"], PAPER_BASELINE_T)  # paper-T travel
    range_estimates = {"sim_coverage_window": sim_cov_travel, "paper_T_travel": paper_T_travel}
    range_max = float(min(range_estimates.values()))           # conservative (no cone inflation)

    # --- half_angle (geometric, self-consistent with net_radius + range_max) ---
    half_angle = half_angle_geometric(net_radius, range_max)

    grounded = dict(half_angle=half_angle, range_min=0.0, range_max=range_max,
                    net_radius=net_radius)
    prov = dict(
        operating_point=BASELINE, rho_air_cal=nf.RHO_AIR_CAL, engage_dist=nf.ENGAGE_DIST,
        sim_S_NP_engage=r["S_NP_engage"], paper_baseline_S_NP=PAPER_BASELINE_SNP,
        sim_net_radius=sim_net_radius, range_estimates=range_estimates,
        sim_coverage_C=r["coverage_C"], F_max=r["F_max"], rope_stress_MPa=r["rope_stress"] / 1e6,
        hang_T_sim=r["hang_T_sim"], paper_T=PAPER_BASELINE_T,
        guard_stress_ok=r["guard_stress_ok"], guard_cfl_ok=r["guard_cfl_ok"],
    )

    if verbose:
        print("=== N1 cone grounding (flexible-net forward model, Xu Drones 9:190) ===")
        print(f"operating point: theta={BASELINE['theta_deg']} deg, v={BASELINE['v0']} m/s, "
              f"m_block={BASELINE['m_block']*1000:.0f} g; rho_air={nf.RHO_AIR_CAL} (calibrated)")
        print(f"sim baseline: S_NP@{nf.ENGAGE_DIST:.0f}m={r['S_NP_engage']:.2f} m^2 "
              f"(paper {PAPER_BASELINE_SNP}), C={r['coverage_C']:.4f} (paper 2.3174), "
              f"F_max={r['F_max']:.1f} N, stress={r['rope_stress']/1e6:.2f} MPa (<= 30)")
        print()
        print(f"{'param':12s} {'tuned':>8s} {'GROUNDED':>10s}  provenance")
        print(f"{'net_radius':12s} {TUNED['net_radius']:>8.2f} {net_radius:>10.3f}  "
              f"sqrt(S_NP/pi), S_NP=12.54 (paper baseline); sim confirms {sim_net_radius:.3f}  [STRONG]")
        print(f"{'half_angle':12s} {TUNED['half_angle']:>8.2f} {half_angle:>10.3f}  "
              f"= {np.degrees(half_angle):.1f} deg; arctan(net_radius/range_max), tightest cone "
              f"containing net cylinder  [self-consistent]")
        print(f"{'range_max':12s} {TUNED['range_max']:>8.2f} {range_max:>10.3f}  "
              f"conservative min of {{sim_cov={sim_cov_travel:.1f}, paperT={paper_T_travel:.1f}}} m  [WEAK -- flagged]")
        print()
        print("LIMITATIONS (honest): (1) range_max WEAK -- sim collapse timing unreliable "
              "(breathing/no-wrap); suspect first at DoD flip. (2) hang time NOT reproduced "
              f"(sim {r['hang_T_sim']:.2f}s vs paper {PAPER_BASELINE_T}s). (3) Table-3 config "
              "spread under-predicted ~23% (config ordering correct; secondary diagnostic only).")
    return grounded, prov


if __name__ == "__main__":
    ground(verbose=True)
