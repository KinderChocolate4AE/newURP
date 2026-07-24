"""N1 TEMPORAL grounding -- is the net actually capture-effective at seed 1100's
crossing (travel ~10 m / tau ~0.19 s)?  (docs/09 (ffff); resolves the (eeee)
PREMISE_NET_TEMPORAL). Move B promoted the wall-vs-history question to ONE premise:
does the net catch BEFORE its 20 m engage anchor? This script answers it by
separating the GEOMETRIC silhouette from a CAPTURE-EFFECTIVE radius, with honest
lower/nominal/upper temporal bands.

THE CENTRAL CAVEAT (net_forward docstring; docs/n1_net_grounding D-notes): the net
is launched FLAT (init='flat') -- fully open at t=0, then it COLLAPSES/breathes.
That is the OPPOSITE of a real net (folded at launch, opening gradually). So the
flat-init silhouette OVER-states the early reach: net_forward is ANCHORED/validated
ONLY at engage (20 m, where rho_air was calibrated to the Xu back-solved area
S_NP=12.54). Everything pre-engage is model extrapolation from an unphysical IC
(init='folded' is a NotImplementedError hook). We therefore report THREE bands:
  upper    = trust the flat-init silhouette outright (over-estimate, FLAGGED).
  nominal  = capture-effective = connected axis-centered INRADIUS on the flat-init
             mesh (accounts for holes/folds/anisotropy, but keeps the flat IC).
  lower    = correct for the unphysical flat IC: a folded net opens ~linearly from
             ~0 at launch to net_radius at engage -> R_cap_lower = net_radius *
             clip(travel/engage,0,1), capped by the connected inradius.

Per snapshot (travel 5/7.5/10/12.5/15/20 m): directional max support, connected
axis-centered min inradius, projected connected aperture, anisotropy, mesh
(silhouette) area, axial depth, centroid speed, folding/balling indicator.

R_req(tau*) for the seed-1100 committed attacker = current lateral offset +
bounded lateral reach (|v_perp|*tau + 1/2 a_att_max tau^2) + target/model
uncertainty (swept). Verdict at tau*=0.19 s: R_cap(band) >= R_req AND a
retention/entanglement plausibility flag. Case B promotes ONLY if the LOWER bound
(or a sufficiently grounded nominal) passes (user pt 8). torch-free.

Xu-validated observables (compare, pt 4): S_NP@engage (Table-3 anchors 12.10 /
24.40; baseline 12.54 the rho_air calibration target), coverage C. TEMPORAL /
early-deployment is NOT validated (documented discrepancy) -> the whole pre-engage
band is flagged.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, "prototypes")
import net_forward as NF          # noqa: E402

# seed-1100 fire geometry (from the c1 probe): attacker on the net axis
ATT_OFFSET0 = 0.08               # lateral offset at fire (m)
ATT_VPERP = 1.5                  # lateral (perp-to-axis) velocity component (m/s)
A_ATT_MAX = 30.0                 # attacker accel bound (m/s^2)
TAU_STAR = 0.19                  # net-front-reaches-attacker crossing time (s)
TARGET_TRAVELS = (5.0, 7.5, 10.0, 12.5, 15.0, 20.0)
UNCERTAINTY_BAND = (0.20, 0.35, 0.50)   # target/model uncertainty sweep (m)


# ------------------------------------------------------- snapshot capture ----
def rollout_snapshots(target_travels, *, theta_deg=45, v0=60, m_g=35,
                      horizon=0.6, ngrid=140):
    """Re-run the net_forward integration (its own building blocks, model
    UNCHANGED) capturing (X, Vel) at each target cumulative-travel. Returns the
    snapshots + the launch axis n_hat and engage anchor."""
    mesh = NF.build_mesh(n_side=NF.N_SIDE, l0=NF.L0, shear=True)
    m_node = NF.lump_node_mass(mesh, m_w=NF.M_W, m_block=m_g / 1000.0)
    k_edge, c_edge, S = NF.edge_coeffs(mesh)
    dt = NF.cfl_dt(k_edge, m_node, safety=0.2)
    X, Vel, e_launch = NF.initial_state(mesh, theta_deg=theta_deg, v0=v0)
    n_hat = e_launch
    n_steps = int(round(horizon / dt))
    centroid_prev = X.mean(0)
    cum = 0.0
    targets = list(target_travels)
    snaps = []
    ti = 0
    for s in range(1, n_steps + 1):
        X, Vel, _ = NF.step(X, Vel, mesh, k_edge, c_edge, m_node, dt=dt,
                            rho_air=NF.RHO_AIR_CAL)
        centroid = X.mean(0)
        cum += float(np.linalg.norm(centroid - centroid_prev))
        centroid_prev = centroid
        while ti < len(targets) and cum >= targets[ti]:
            snaps.append({"target_travel": targets[ti], "cum_travel": cum,
                          "tau": s * dt, "X": X.copy(), "Vel": Vel.copy()})
            ti += 1
        if ti >= len(targets):
            break
    return {"snaps": snaps, "mesh": mesh, "n_hat": np.asarray(n_hat, float),
            "engage_dist": float(NF.ENGAGE_DIST), "dt": float(dt),
            "S_des": float(NF.silhouette_area(
                NF.initial_state(mesh, theta_deg=theta_deg, v0=v0)[0],
                mesh["cell_quads"], n_hat, ngrid=ngrid))}


# ------------------------------------------------------------- metrics -------
def _plane_basis(n_hat):
    n = n_hat / (np.linalg.norm(n_hat) + 1e-12)
    a = np.array([0., 0, 1.]) if abs(n[2]) < 0.9 else np.array([0., 1., 0.])
    eu = np.cross(n, a); eu /= np.linalg.norm(eu) + 1e-12
    ev = np.cross(n, eu); ev /= np.linalg.norm(ev) + 1e-12
    return eu, ev


def _rasterize(P, tris, ngrid=140):
    """Occupancy grid of the projected triangles + (dx,dy,lo). P=(nodes,2)."""
    lo = P.min(0); hi = P.max(0); span = hi - lo
    if span[0] <= 1e-9 or span[1] <= 1e-9:
        return None
    nx = ny = int(ngrid)
    dx = span[0] / nx; dy = span[1] / ny
    occ = np.zeros((ny, nx), bool)
    A2, B2, C2 = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
    for k in range(len(tris)):
        a, b, c = A2[k], B2[k], C2[k]
        i0 = max(0, int((min(a[0], b[0], c[0]) - lo[0]) / dx))
        i1 = min(nx, int((max(a[0], b[0], c[0]) - lo[0]) / dx) + 1)
        j0 = max(0, int((min(a[1], b[1], c[1]) - lo[1]) / dy))
        j1 = min(ny, int((max(a[1], b[1], c[1]) - lo[1]) / dy) + 1)
        if i1 <= i0 or j1 <= j0:
            continue
        xs = lo[0] + (np.arange(i0, i1) + 0.5) * dx
        ys = lo[1] + (np.arange(j0, j1) + 0.5) * dy
        GX, GY = np.meshgrid(xs, ys)
        v0 = c - a; v1 = b - a
        d00 = v0 @ v0; d01 = v0 @ v1; d11 = v1 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-12:
            continue
        wx = GX - a[0]; wy = GY - a[1]
        d20 = wx * v0[0] + wy * v0[1]; d21 = wx * v1[0] + wy * v1[1]
        uu = (d11 * d20 - d01 * d21) / den
        ww = (d00 * d21 - d01 * d20) / den
        inside = (uu >= 0) & (ww >= 0) & (uu + ww <= 1)
        occ[j0:j1, i0:i1] |= inside
    return {"occ": occ, "dx": dx, "dy": dy, "lo": lo, "nx": nx, "ny": ny}


def _connected_component(occ, ci, cj):
    """BFS component of occ containing (ci,cj); returns mask (empty if center off)."""
    ny, nx = occ.shape
    mask = np.zeros_like(occ)
    if not (0 <= cj < ny and 0 <= ci < nx) or not occ[cj, ci]:
        return mask
    from collections import deque
    q = deque([(cj, ci)]); mask[cj, ci] = True
    while q:
        j, i = q.popleft()
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nj, nii = j + dj, i + di
            if 0 <= nj < ny and 0 <= nii < nx and occ[nj, nii] and not mask[nj, nii]:
                mask[nj, nii] = True; q.append((nj, nii))
    return mask


def _inradius_at_center(comp_mask, ci, cj, dx, dy):
    """Largest axis-centered disk fully inside the connected component: distance
    from center to the nearest NON-component cell. The mask is PADDED with a False
    border first, so a net that fills its own bounding box measures the distance to
    its TRUE boundary (else distance_transform_edt, which ignores out-of-array,
    over-states the inradius)."""
    if not comp_mask.any():
        return 0.0
    padded = np.zeros((comp_mask.shape[0] + 2, comp_mask.shape[1] + 2), bool)
    padded[1:-1, 1:-1] = comp_mask
    pj, pi = cj + 1, ci + 1
    try:
        from scipy.ndimage import distance_transform_edt
        edt = distance_transform_edt(padded, sampling=(dy, dx))
        return float(edt[pj, pi])
    except Exception:                       # manual ring-grow fallback
        ny, nx = padded.shape
        best = 0.0
        for r in range(1, int(max(nx, ny))):
            hit_edge = False
            for a in np.linspace(0, 2 * np.pi, 8 * r, endpoint=False):
                j = int(round(pj + r * np.sin(a))); i = int(round(pi + r * np.cos(a)))
                if not (0 <= j < ny and 0 <= i < nx) or not padded[j, i]:
                    hit_edge = True; break
            if hit_edge:
                break
            best = r * min(dx, dy)
        return best


def snapshot_metrics(X, Vel, n_hat, cell_quads, ngrid=140):
    """All per-snapshot coherence + reach metrics."""
    n_hat = n_hat / (np.linalg.norm(n_hat) + 1e-12)
    c = X.mean(0)
    rel = X - c
    axial = rel @ n_hat
    perp_vec = rel - np.outer(axial, n_hat)
    perp = np.linalg.norm(perp_vec, axis=1)
    eu, ev = _plane_basis(n_hat)
    P = np.stack([X @ eu, X @ ev], 1)                       # projected nodes
    # sector anisotropy
    az = np.arctan2(perp_vec @ ev, perp_vec @ eu)
    sect = []
    for kk in range(8):
        loa, hia = -np.pi + kk * np.pi / 4, -np.pi + (kk + 1) * np.pi / 4
        m = (az >= loa) & (az < hia)
        sect.append(float(perp[m].max()) if m.any() else 0.0)
    sect = np.asarray(sect)
    anis = float(sect.max() / (sect[sect > 0].min() + 1e-9)) if (sect > 0).any() else np.inf
    # areas
    S_NP = NF.silhouette_area(X, cell_quads, n_hat, ngrid=ngrid)
    S_cellsum = NF.cellsum_area_mesh(X, cell_quads, n_hat)
    folding = float(S_cellsum / (S_NP + 1e-9))              # >1 folds overlap
    R_geom = float(np.sqrt(max(S_NP, 0.0) / np.pi))
    # rasterize -> connected aperture + inradius at the axis center (= centroid proj)
    tris = np.concatenate([cell_quads[:, [0, 1, 2]], cell_quads[:, [0, 2, 3]]], 0)
    ras = _rasterize(P, tris, ngrid=ngrid)
    cproj = np.array([c @ eu, c @ ev])
    if ras is None:
        inr = aperture_r = 0.0
    else:
        ci = int(np.clip((cproj[0] - ras["lo"][0]) / ras["dx"], 0, ras["nx"] - 1))
        cj = int(np.clip((cproj[1] - ras["lo"][1]) / ras["dy"], 0, ras["ny"] - 1))
        comp = _connected_component(ras["occ"], ci, cj)
        aperture_area = float(comp.sum() * ras["dx"] * ras["dy"])
        aperture_r = float(np.sqrt(aperture_area / np.pi))
        inr = _inradius_at_center(comp, ci, cj, ras["dx"], ras["dy"])
    return {"max_support": float(perp.max()), "min_sector_support": float(sect.min()),
            "anisotropy": anis, "S_NP": float(S_NP), "S_cellsum": float(S_cellsum),
            "folding_ratio": folding, "R_geom": R_geom,
            "connected_aperture_r": aperture_r, "inradius": float(inr),
            "axial_depth": float(axial.max() - axial.min()),
            "centroid_speed": float(np.linalg.norm(Vel.mean(0)))}


# --------------------------------------------------------- bands + verdict ---
def r_req(tau, unc):
    return float(ATT_OFFSET0 + abs(ATT_VPERP) * tau + 0.5 * A_ATT_MAX * tau ** 2 + unc)


def build(target_travels=TARGET_TRAVELS, ngrid=140):
    roll = rollout_snapshots(target_travels, ngrid=ngrid)
    n_hat = roll["n_hat"]; quads = roll["mesh"]["cell_quads"]
    engage = roll["engage_dist"]
    rows = []
    for sn in roll["snaps"]:
        m = snapshot_metrics(sn["X"], sn["Vel"], n_hat, quads, ngrid=ngrid)
        tr = sn["cum_travel"]
        # bands
        R_upper = m["R_geom"]                                       # flat-init silhouette
        R_nominal = m["inradius"]                                   # connected axis inradius
        R_lower = min(m["inradius"],
                      net_radius_engage_placeholder(tr, engage))    # folded-opening cap
        rows.append({**{k: m[k] for k in m}, "target_travel": sn["target_travel"],
                     "cum_travel": tr, "tau": sn["tau"],
                     "R_upper": R_upper, "R_nominal": R_nominal, "R_lower": R_lower})
    # net_radius at engage = R_geom of the snapshot closest to engage travel
    eng_row = min(rows, key=lambda r: abs(r["cum_travel"] - engage))
    net_radius_engage = eng_row["R_geom"]
    # R_req at tau* over the uncertainty sweep
    reqs = {f"unc_{u}": r_req(TAU_STAR, u) for u in UNCERTAINTY_BAND}
    req_nom = r_req(TAU_STAR, UNCERTAINTY_BAND[1])
    # interpolate each band to tau*/travel~10
    def at_star(key):
        trv = [r["cum_travel"] for r in rows]; val = [r[key] for r in rows]
        return float(np.interp(10.0, trv, val))
    Rc = {"upper": at_star("R_upper"), "nominal": at_star("R_nominal"),
          "lower": at_star("R_lower")}
    # coherence at the crossing
    fold_star = float(np.interp(10.0, [r["cum_travel"] for r in rows],
                                [r["folding_ratio"] for r in rows]))
    anis_star = float(np.interp(10.0, [r["cum_travel"] for r in rows],
                                [r["anisotropy"] for r in rows]))
    depth_star = float(np.interp(10.0, [r["cum_travel"] for r in rows],
                                 [r["axial_depth"] for r in rows]))
    # retention/entanglement plausibility (heuristic, NOT Xu-validated): needs some
    # axial depth to wrap (not a taut flat sheet) AND a coherent connected aperture.
    retention = bool(depth_star > 0.5 and Rc["nominal"] > req_nom * 0.8)
    # verdict per user pt 8-9
    pass_lower = Rc["lower"] >= req_nom
    pass_nominal = Rc["nominal"] >= req_nom
    pass_upper = Rc["upper"] >= req_nom
    nominal_grounded = False        # flat-init IC unphysical -> nominal NOT grounded
    if pass_lower:
        verdict = "STRONG_PASS_MOVE_C"
    elif pass_nominal and nominal_grounded:
        verdict = "STRONG_PASS_MOVE_C"
    elif pass_nominal or pass_upper:
        verdict = "CONDITIONAL_MOVE_C_SENSITIVITY_PLUS_MOVE_A"
    else:
        verdict = "FAIL_MOVE_A"
    note = _verdict_note(verdict, Rc, req_nom, engage, fold_star)
    return {"meta": {"tau_star": TAU_STAR, "crossing_travel": 10.0,
                     "engage_dist": engage, "target_travels": list(target_travels),
                     "att_offset0": ATT_OFFSET0, "att_vperp": ATT_VPERP,
                     "a_att_max": A_ATT_MAX, "S_des": roll["S_des"],
                     "net_radius_engage": net_radius_engage,
                     "flat_init_caveat": "net launched FLAT (open) then collapses = "
                     "OPPOSITE of a real folded->opening net; pre-engage silhouette is "
                     "an over-estimate; only S_NP@engage is Xu-anchored",
                     "bands": "upper=flat-init silhouette / nominal=connected axis "
                     "inradius (flat IC) / lower=folded-opening (net_radius*travel/engage "
                     "capped by inradius)",
                     "retention_caveat": "heuristic; Xu validates coverage C & hang T, "
                     "NOT single-target entanglement"},
            "snapshots": rows,
            "R_req_tau_star": reqs, "R_req_nominal": req_nom,
            "R_cap_at_crossing": Rc,
            "coherence_at_crossing": {"folding_ratio": fold_star,
                                      "anisotropy": anis_star, "axial_depth": depth_star},
            "retention_plausible": retention,
            "pass": {"lower": bool(pass_lower), "nominal": bool(pass_nominal),
                     "upper": bool(pass_upper), "nominal_grounded": nominal_grounded},
            "verdict": verdict, "note": note}


def net_radius_engage_placeholder(travel, engage, net_radius=2.0):
    """Folded-opening lower model: reach grows ~linearly from ~0 (folded) at launch
    to net_radius at engage; flat beyond. Conservative correction for the unphysical
    flat IC."""
    return net_radius * float(np.clip(travel / engage, 0.0, 1.0))


def _verdict_note(verdict, Rc, req, engage, fold):
    base = (f"R_cap@crossing lower={Rc['lower']:.2f} nominal={Rc['nominal']:.2f} "
            f"upper={Rc['upper']:.2f} m  vs  R_req~{req:.2f} m.")
    if verdict == "STRONG_PASS_MOVE_C":
        return base + (" Lower (grounded) bound clears R_req -> net IS capture-effective "
                       "pre-engage -> premise resolved POSITIVE -> Move C.")
    if verdict == "CONDITIONAL_MOVE_C_SENSITIVITY_PLUS_MOVE_A":
        return base + (f" Passes only under the OPTIMISTIC/nominal (flat-init) reading; "
                       f"the grounded LOWER bound (folded-opening) does NOT clear R_req, "
                       f"and the flat IC is unphysical (folding~{fold:.2f}), so the nominal "
                       f"is not itself grounded -> Case B NOT promoted -> Move C held as a "
                       f"SENSITIVITY, Move A pursued in parallel. Resolving requires a real "
                       f"folded-deployment net model (init='folded', currently unimplemented).")
    return base + (" No band clears R_req at a grounded reading -> premise resolved "
                   "NEGATIVE (net not an effective catcher at ~10 m under the honest "
                   "folded-opening bound) -> Move A.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/n1_temporal.json")
    ap.add_argument("--ngrid", type=int, default=140)
    a = ap.parse_args()
    out = build(ngrid=a.ngrid)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"crossing tau*={out['meta']['tau_star']}s travel~10m  engage={out['meta']['engage_dist']}m")
    print(f"{'travel':>7} {'tau':>5} {'Rgeom':>6} {'inrad':>6} {'apert':>6} "
          f"{'Rlow':>5} {'fold':>5} {'anis':>6} {'depth':>6} {'cspd':>6}")
    for r in out["snapshots"]:
        print(f"{r['cum_travel']:>7.1f} {r['tau']:>5.2f} {r['R_geom']:>6.2f} "
              f"{r['inradius']:>6.2f} {r['connected_aperture_r']:>6.2f} "
              f"{r['R_lower']:>5.2f} {r['folding_ratio']:>5.2f} {r['anisotropy']:>6.2f} "
              f"{r['axial_depth']:>6.2f} {r['centroid_speed']:>6.1f}")
    Rc = out["R_cap_at_crossing"]; req = out["R_req_nominal"]
    print(f"\nR_cap@crossing: lower={Rc['lower']:.2f} nominal={Rc['nominal']:.2f} "
          f"upper={Rc['upper']:.2f} m   R_req~{req:.2f} m "
          f"(sweep {out['R_req_tau_star']})")
    print(f"retention_plausible={out['retention_plausible']}  "
          f"pass={out['pass']}")
    print(f"\nVERDICT: {out['verdict']}\n  {out['note']}")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
