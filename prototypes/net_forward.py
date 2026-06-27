"""Flexible-net forward dynamics + effective-area metrics  (newURP N1, cone grounding).

N1 replaces the TUNED / UNGROUNDED SE(3) net-cone constants (half_angle=0.43 rad,
range_max=40 m, net_radius=1.5 m) with values DERIVED from a flexible-net forward
model, so the M2 viability judge stops resting on hand-tuned geometry. This module
is that forward model: a lumped-mass, tension-only spring-damper net with Williams
aero, integrated explicitly, exposing the effective interception area S_NP(t),
hang time T, and rope-stress / anti-balling guards. The bridge to the three cone
parameters lives in `ground_cone.py`.

Source: Xu, Peng, Wu, "Optimization Design of Flexible Net Capture System for Low,
Slow, and Small UAVs ...", Drones 2025, 9, 190 (DOI 10.3390/drones9030190).
Forward model only (paper Sec. 3); WPA / optimization narrative excluded.

Resolved spec flags (see N1_paper_anchors.md):
  D1  drag/lift are LINEAR in ||v|| in the paper (F = 1/2 e rho_air C d ||v|| L,
      first power). We use LINEAR by default (`drag_power=1.0`) to REPRODUCE the
      paper's C/T; `drag_power=2.0` is the physically-standard quadratic correction
      (documented, not silently switched -- it will NOT match the paper numbers).
  D2  hang-time polynomial Eq.(11) recovered; used only as a cross-check (`hang_eq11`).
      We MEASURE T from the rollout.
  D3  rho_rope = 970 kg/m^3 (nylon, the value behind the reported example). The
      Table-1 1440 conflict is benign: rho_rope enters ONLY damping c (eq 3), NOT
      node mass (mass = measured net mass m_w=170 g lumped), so it cannot corrupt
      inertia / the CFL bound.
  rho_air NOT stated in the paper -> assumed; calibrated once so the baseline
      effective area matches, then frozen (the single free knob).

Pure numpy (no torch). Physics params are INJECTED as kwargs. Mirrors the style of
prototypes/reachset.py.
"""
from __future__ import annotations
import numpy as np

# --- paper-fixed constants (N1_paper_anchors.md "Other parameters") -------------
D_ROPE  = 2.181167e-3          # rope diameter [m]
E_MOD   = 0.305e9              # elastic modulus [Pa]
L0      = 0.52                 # mesh cell edge / segment rest length [m]
ZETA    = 0.05                 # damping ratio
RHO_ROPE = 970.0              # rope density [kg/m^3]  (D3: 970, not 1440)
M_W     = 0.170               # total net mass [kg]  (5.2 x 5.2 m, 10x10 cells)
SIGMA_B = 30.0e6              # max allowable tensile stress [Pa]
N_SIDE  = 11                  # nodes per side (10 cells)
G_ACC   = 9.81               # gravity [m/s^2]
S_UAV_DEFAULT = 2.0          # UAV maneuvering cross-section [m^2] (used in coverage C)
RHO_AIR_DEFAULT = 1.225      # not in paper; atmospheric reference
# CALIBRATED + FROZEN: the single free knob. rho_air chosen so the baseline
# (45 deg, 60 m/s, 35 g) silhouette at ENGAGE_DIST travel == the paper's back-solved
# baseline effective area S_NP=12.54 m^2 (=> net_radius=2.0 m). 1.513 ~= atmospheric
# 1.225 (physically reasonable, not a fudge). See ground_cone.py / docs/n1_net_grounding.md.
RHO_AIR_CAL = 1.513
ENGAGE_DIST = 20.0           # pre-fixed engagement travel distance [m] at which the
                             # effective interception area is read (option-1 grounding +
                             # secondary config-ordering diagnostic). NOT tuned per-config.

_EPS = 1e-12
_EPS_V = 1e-6                 # speed below which a segment's aero is zeroed


# ------------------------------------------------------------------ mesh ---------
def build_mesh(n_side=N_SIDE, l0=L0, *, shear=True, aero_on_diagonals=False):
    """11x11 lumped-mass lattice (10x10 cells). Structural H/V springs (rest l0)
    plus one diagonal shear spring per cell (rest l0*sqrt2, alternating by (i+j)%2)
    -- a square axial-only mesh has ZERO in-plane shear stiffness and yields garbage
    S_NP, so diagonals are on by default. Diagonals carry NO mass and (by default)
    NO aero. Returns a dict of static topology arrays."""
    n = n_side
    idx = lambda i, j: i * n + j
    edges, l0_edge, kind = [], [], []
    # structural horizontal + vertical
    for i in range(n):
        for j in range(n - 1):
            edges.append((idx(i, j), idx(i, j + 1))); l0_edge.append(l0); kind.append(0)
    for i in range(n - 1):
        for j in range(n):
            edges.append((idx(i, j), idx(i + 1, j))); l0_edge.append(l0); kind.append(0)
    # diagonal shear, one per cell, alternating direction
    if shear:
        for i in range(n - 1):
            for j in range(n - 1):
                if (i + j) % 2 == 0:
                    edges.append((idx(i, j), idx(i + 1, j + 1)))
                else:
                    edges.append((idx(i, j + 1), idx(i + 1, j)))
                l0_edge.append(l0 * np.sqrt(2.0)); kind.append(1)
    edges = np.asarray(edges, int)
    kind = np.asarray(kind, int)
    aero_mask = (kind == 0) if not aero_on_diagonals else np.ones(len(edges), bool)
    # cell quads (corner node order: (i,j),(i,j+1),(i+1,j+1),(i+1,j)) for area
    quads = np.asarray([[idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)]
                        for i in range(n - 1) for j in range(n - 1)], int)
    m = n // 2
    corner_ids = np.asarray([idx(0, 0), idx(0, n - 1), idx(n - 1, n - 1), idx(n - 1, 0)], int)
    midedge_ids = np.asarray([idx(0, m), idx(m, n - 1), idx(n - 1, m), idx(m, 0)], int)
    # flat reference positions in the net's own plane (centered at origin)
    u = (np.arange(n) - (n - 1) / 2.0) * l0
    UU, VV = np.meshgrid(u, u, indexing="ij")
    ref_uv = np.stack([UU.ravel(), VV.ravel()], 1)        # (n*n, 2)
    return dict(n_side=n, n_nodes=n * n, edges=edges, l0_edge=np.asarray(l0_edge, float),
                kind=kind, aero_mask=aero_mask, cell_quads=quads,
                corner_ids=corner_ids, midedge_ids=midedge_ids, ref_uv=ref_uv)


def lump_node_mass(mesh, *, m_w=M_W, m_block):
    """Lump the measured net mass m_w over nodes via per-structural-edge linear
    density (decoupled from rho_rope per D3), then add the corner block mass m_block
    to the 4 corners. Asserts mass conservation."""
    struct = mesh["kind"] == 0
    edges = mesh["edges"][struct]
    l0_e = mesh["l0_edge"][struct]
    mu = m_w / float(l0_e.sum())                          # linear density [kg/m]
    m_edge = mu * l0_e
    m_node = np.zeros(mesh["n_nodes"], float)
    np.add.at(m_node, edges[:, 0], 0.5 * m_edge)
    np.add.at(m_node, edges[:, 1], 0.5 * m_edge)
    m_node[mesh["corner_ids"]] += float(m_block)
    assert abs(m_node.sum() - (m_w + 4 * m_block)) < 1e-9, "mass lumping not conserved"
    return m_node


def edge_coeffs(mesh, *, e_mod=E_MOD, d=D_ROPE, zeta=ZETA, rho_rope=RHO_ROPE):
    """Per-edge stiffness k (eq 2) and damping c (eq 3). Returns (k_edge, c_edge, S)."""
    S = np.pi * d ** 2 / 4.0
    k_edge = e_mod * S / mesh["l0_edge"]                                  # eq 2
    c_edge = 2.0 * zeta * np.sqrt(rho_rope * k_edge * mesh["l0_edge"] * S)  # eq 3
    return k_edge, c_edge, S


def cfl_dt(k_edge, m_node, *, safety=0.2):
    """Explicit-integration stability bound: omega_max = sqrt(k_max / m_node_min)
    (min over the LIGHT interior node, never the heavy corners). dt = safety*2/omega."""
    k_max = float(k_edge.max())
    m_min = float(m_node.min())
    omega_max = np.sqrt(k_max / m_min)
    return safety * 2.0 / omega_max


# ------------------------------------------------------ initial config -----------
def _plane_basis(e_launch):
    """Orthonormal (e_u, e_v) spanning the plane perpendicular to e_launch."""
    e = np.asarray(e_launch, float)
    e = e / (np.linalg.norm(e) + _EPS)
    world = np.array([0.0, 0.0, 1.0]) if abs(e[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e_u = np.cross(e, world); e_u /= np.linalg.norm(e_u) + _EPS
    e_v = np.cross(e, e_u);   e_v /= np.linalg.norm(e_v) + _EPS
    return e_u, e_v


def initial_state(mesh, *, theta_deg, v0, launch_origin=(0.0, 0.0, 0.0), init="flat"):
    """Net launched FLAT, plane perpendicular to launch direction, rigid initial
    velocity v0 along e_launch = [cos th, 0, sin th]. `init='folded'` is a documented
    hook (NOT implemented) -- flat is the least-faithful corner of the model
    (over-states early S_NP, under-states snap shock) but OK for deployed coverage.
    Returns (X, Vel, e_launch)."""
    if init != "flat":
        raise NotImplementedError("only init='flat' is implemented (folded is a hook)")
    th = np.radians(theta_deg)
    e_launch = np.array([np.cos(th), 0.0, np.sin(th)])
    e_u, e_v = _plane_basis(e_launch)
    uv = mesh["ref_uv"]
    X = np.asarray(launch_origin, float)[None, :] + uv[:, 0:1] * e_u[None, :] + uv[:, 1:2] * e_v[None, :]
    Vel = np.tile(v0 * e_launch, (mesh["n_nodes"], 1))
    return X, Vel, e_launch


# ------------------------------------------------------------- dynamics ----------
def step(X, Vel, mesh, k_edge, c_edge, m_node, *, dt, d=D_ROPE, rho_air=RHO_AIR_DEFAULT,
         g=G_ACC, drag_power=1.0):
    """One symplectic (semi-implicit) Euler step. Tension-only springs (eq 1, with a
    Tmag>=0 clamp so damping can't synthesize compression on a slackening edge) +
    per-structural-segment Williams aero (eq 4-7, LINEAR in ||v|| via drag_power=1)
    + gravity. Returns (X_new, Vel_new, Tmag_max)."""
    e = mesh["edges"]; a, b = e[:, 0], e[:, 1]
    l0_e = mesh["l0_edge"]

    # --- tension (eq 1) ---
    dvec = X[b] - X[a]
    L = np.linalg.norm(dvec, axis=1)
    ehat = dvec / (L[:, None] + _EPS)
    Ldot = np.einsum("ij,ij->i", Vel[b] - Vel[a], ehat)
    Tmag = k_edge * (L - l0_e) + c_edge * Ldot
    Tmag = np.where(L > l0_e, np.maximum(Tmag, 0.0), 0.0)   # tension-only + clamp
    Ft = Tmag[:, None] * ehat
    F = np.zeros_like(X)
    np.add.at(F, a, Ft)
    np.add.at(F, b, -Ft)

    # --- aero (eq 4-7), structural segments only ---
    ae = mesh["aero_mask"]
    aa, bb = a[ae], b[ae]
    vseg = 0.5 * (Vel[aa] + Vel[bb])
    sp = np.linalg.norm(vseg, axis=1)
    vhat = vseg / (sp[:, None] + _EPS)
    that = ehat[ae]
    cx = np.cross(vhat, that)
    sin_a = np.clip(np.linalg.norm(cx, axis=1), 0.0, 1.0)        # sin(alpha)=||vhat x that||
    cos_a = np.sqrt(np.maximum(1.0 - sin_a ** 2, 0.0))
    CD = 1.1 * sin_a ** 3 + 0.022                                # eq 6
    CL = 1.1 * sin_a ** 2 * cos_a                                # eq 7
    Le = L[ae]
    q = 0.5 * rho_air * d * Le * sp ** float(drag_power)          # D1: linear default
    F_D = (q * CD)[:, None] * (-vhat)                            # eq 4, e_D = -vhat
    eL_raw = np.cross(cx, vhat)                                  # (vhat x that) x vhat
    eL = eL_raw / (np.linalg.norm(eL_raw, axis=1)[:, None] + _EPS)
    F_L = (q * CL)[:, None] * eL                                 # eq 5
    F_aero = F_D + F_L
    F_aero[sp < _EPS_V] = 0.0
    assert np.isfinite(F_aero).all(), "non-finite aero force (degenerate geometry)"
    np.add.at(F, aa, 0.5 * F_aero)
    np.add.at(F, bb, 0.5 * F_aero)

    # --- gravity + integrate ---
    F[:, 2] -= m_node * g
    Vel_new = Vel + dt * F / m_node[:, None]
    X_new = X + dt * Vel_new
    return X_new, Vel_new, float(Tmag.max())


# --------------------------------------------------------------- areas -----------
def _plane_2d(n_hat):
    """Orthonormal 2D basis (e_u, e_v) spanning the plane normal to n_hat."""
    n = np.asarray(n_hat, float); n = n / (np.linalg.norm(n) + _EPS)
    a = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    eu = np.cross(n, a); eu /= np.linalg.norm(eu) + _EPS
    ev = np.cross(n, eu); ev /= np.linalg.norm(ev) + _EPS
    return eu, ev


def quad_area_proj(p0, p1, p2, p3, n_hat):
    """Projected area of a single (possibly non-planar) quad onto the plane normal
    to n_hat, via two-triangle area vectors (signed sum; used for the g2 guard quads)."""
    A = 0.5 * (np.cross(p1 - p0, p2 - p0) + np.cross(p2 - p0, p3 - p0))
    return float(abs(A @ n_hat))


def cellsum_area_mesh(X, cell_quads, n_hat):
    """Sum over cells of |cell-area-vector . n_hat|. DIAGNOSTIC ONLY: over-counts
    folded overlap (floors ~2 m^2 when the net balls up) -> NOT used for S_NP. Kept
    to expose the over-count vs the true silhouette (N1 risk 7)."""
    p0 = X[cell_quads[:, 0]]; p1 = X[cell_quads[:, 1]]
    p2 = X[cell_quads[:, 2]]; p3 = X[cell_quads[:, 3]]
    A = 0.5 * (np.cross(p1 - p0, p2 - p0) + np.cross(p2 - p0, p3 - p0))
    return float(np.sum(np.abs(A @ n_hat)))


def silhouette_area(X, cell_quads, n_hat, *, ngrid=96):
    """S_NP = TRUE projected silhouette (union, not per-cell sum) onto the plane
    normal to n_hat, by rasterizing the deformed-mesh triangles into an occupancy
    grid. Required for validity: unlike cellsum it correctly collapses toward 0 when
    the net balls up (per-cell sum floors ~2 m^2 from counting overlapping folds).
    Per-triangle bbox culling keeps it cheap."""
    eu, ev = _plane_2d(n_hat)
    P = np.stack([X @ eu, X @ ev], 1)                       # (nodes, 2)
    lo = P.min(0); hi = P.max(0); span = hi - lo
    if span[0] <= _EPS or span[1] <= _EPS:
        return 0.0
    nx = ny = int(ngrid)
    dx = span[0] / nx; dy = span[1] / ny
    occ = np.zeros((ny, nx), bool)
    tris = np.concatenate([cell_quads[:, [0, 1, 2]], cell_quads[:, [0, 2, 3]]], 0)
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
        if abs(den) < _EPS:
            continue
        wx = GX - a[0]; wy = GY - a[1]
        d20 = wx * v0[0] + wy * v0[1]
        d21 = wx * v1[0] + wy * v1[1]
        u = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        inside = (u >= 0) & (w >= 0) & (u + w <= 1)
        occ[j0:j1, i0:i1] |= inside
    return float(occ.sum() * dx * dy)


def coverage(S_NP, S_UAV=S_UAV_DEFAULT):
    """Eq 12 coverage rate C = exp((S_NP - S_UAV)/S_NP). NOTE: saturating in S_NP --
    not a sensitive validation anchor (use S_NP / T)."""
    return float(np.exp((S_NP - S_UAV) / S_NP))


def rope_stress(F_max, d=D_ROPE):
    """Guard g3 reference stress 4*F_max/(pi*d^2) [Pa]."""
    return float(4.0 * F_max / (np.pi * d ** 2))


# -------------------------------------------------- hang-time Eq.(11) ------------
def hang_eq11(theta_deg, v, m_g, *, alpha_lin_fix=6.415e-9):
    """Paper Eq.(11) hang-time polynomial (D2), m in GRAMS, v in m/s, alpha=theta deg.
    The PDF's alpha-linear term prints a double-exponent typo (0.0006415e-05*m);
    `alpha_lin_fix` is the reconstructed coefficient (default 6.415e-9), pinned by the
    frontier anchors. Used as a CROSS-CHECK only; T is measured from the rollout."""
    m, v, al = float(m_g), float(v), float(theta_deg)
    return (6.882e-6 * m ** 3 - 0.0007043 * m ** 2 - 0.0188 * m + 5.104
            + (4.593e-7 * m ** 3 + 8.117e-5 * m ** 2 - 0.00451 * m + 0.05297) * v
            + (-1.042e-7 * m ** 3 + 7.506e-6 * m ** 2 + alpha_lin_fix * m - 0.07627) * al
            + (1.502e-9 * m ** 3 - 2.706e-7 * m ** 2 + 1.539e-5 * m - 0.0001825) * v ** 2
            + (4.253e-9 * m ** 3 - 7.551e-7 * m ** 2 + 4.315e-5 * m - 0.0007084) * v * al
            + (4.544e-10 * m ** 3 - 1.117e-8 * m ** 2 - 5.634e-6 * m + 0.0004625) * al ** 2)


# ----------------------------------------------------------- simulate ------------
def travel_to_time(t_series, cum_travel, t_query):
    """Centroid path length integrated up to t_query (linear interp on the recorded
    cumulative-travel series). Used to ground range_max from an externally supplied
    hang time (option-2: temporal extent is paper-sourced, not sim-derived)."""
    t = np.asarray(t_series, float); c = np.asarray(cum_travel, float)
    if not len(t):
        return 0.0
    return float(np.interp(min(t_query, t[-1]), t, c))


def simulate(*, theta_deg, v0, m_block, target_vhat=None, horizon=3.5,
             s_uav=S_UAV_DEFAULT, hang_frac=0.05, drag_power=1.0,
             rho_rope=RHO_ROPE, rho_air=RHO_AIR_CAL, m_w=M_W, d=D_ROPE,
             e_mod=E_MOD, l0=L0, zeta=ZETA, sigma_b=SIGMA_B, g=G_ACC,
             shear=True, k_diag_scale=1.0, dt=None, safety=0.2, samp_dt=0.01,
             engage_dist=ENGAGE_DIST, ngrid=96, launch_origin=(0.0, 0.0, 0.0)):
    """Roll out one launch config (theta[deg], v0[m/s], m_block[kg]).

    S_NP = TRUE silhouette (spec-correct; cellsum kept only as an over-count
    diagnostic). The SPATIAL grounding product is `S_NP_engage` = silhouette at
    `engage_dist` centroid travel (-> net_radius), with the deployed shape there
    (`X_snapshot`) used for half_angle. This metric is calibrated to the paper
    baseline (rho_air=RHO_AIR_CAL) and carries the correct config ordering
    (secondary diagnostic) though it under-predicts the Table-3 spread.

    TEMPORAL outputs (hang_T_sim, T_cov) are a DOCUMENTED DISCREPANCY, NOT validated:
    the flat-init no-wrapping net breathes (collapses then re-opens) so it does NOT
    reproduce the paper's monotone hang time -- range_max is grounded CONSERVATIVELY
    downstream (see ground_cone). `S_NP_eff` (mean over the first coverage pass) is
    config-invariant (~17 m^2) and kept only as a diagnostic, NOT for grounding."""
    mesh = build_mesh(n_side=N_SIDE, l0=l0, shear=shear)
    m_node = lump_node_mass(mesh, m_w=m_w, m_block=m_block)
    k_edge, c_edge, S = edge_coeffs(mesh, e_mod=e_mod, d=d, zeta=zeta, rho_rope=rho_rope)
    if k_diag_scale != 1.0:                      # k_diag sensitivity knob (numerical device)
        k_edge = k_edge.copy(); k_edge[mesh["kind"] == 1] *= float(k_diag_scale)

    dt_cfl = cfl_dt(k_edge, m_node, safety=safety)
    if dt is None:
        dt = dt_cfl
    dt_stable = cfl_dt(k_edge, m_node, safety=1.0)
    guard_cfl_ok = dt < dt_stable
    assert guard_cfl_ok, (f"dt={dt:.2e}s violates CFL: need dt<2/omega_max={dt_stable:.2e}s "
                          f"(explicit integration will blow up)")

    X, Vel, e_launch = initial_state(mesh, theta_deg=theta_deg, v0=v0,
                                     launch_origin=launch_origin)
    n_hat = e_launch if target_vhat is None else (np.asarray(target_vhat, float)
                                                  / (np.linalg.norm(target_vhat) + _EPS))
    quads = mesh["cell_quads"]; cp = mesh["corner_ids"]; me = mesh["midedge_ids"]
    sil = lambda Y: silhouette_area(Y, quads, n_hat, ngrid=ngrid)
    S_des = sil(X)                                        # flat designed silhouette (~26 m^2)
    hang_thresh = hang_frac * S_des

    n_steps = int(round(horizon / dt))
    samp_every = max(1, int(round(samp_dt / dt)))
    t_hist, snp_hist, se_hist, snpc_hist, cum_hist, csum_hist = [], [], [], [], [], []
    X_all, snap_snp = [], []
    F_max = 0.0
    centroid_prev = X.mean(0)
    cum_travel = 0.0
    T_cov = np.inf; hang_T = np.inf; window_open = True

    for s in range(1, n_steps + 1):
        X, Vel, Tmag_max = step(X, Vel, mesh, k_edge, c_edge, m_node, dt=dt, d=d,
                                rho_air=rho_air, g=g, drag_power=drag_power)
        F_max = max(F_max, Tmag_max)
        centroid = X.mean(0)
        cum_travel += float(np.linalg.norm(centroid - centroid_prev))
        centroid_prev = centroid
        if s % samp_every == 0 or s == n_steps:
            t = s * dt
            S_NP = sil(X)
            t_hist.append(t); snp_hist.append(S_NP); cum_hist.append(cum_travel)
            se_hist.append(quad_area_proj(X[me[0]], X[me[1]], X[me[2]], X[me[3]], n_hat))
            snpc_hist.append(quad_area_proj(X[cp[0]], X[cp[1]], X[cp[2]], X[cp[3]], n_hat))
            csum_hist.append(cellsum_area_mesh(X, quads, n_hat))
            X_all.append(X.copy())
            if window_open and S_NP >= s_uav:
                snap_snp.append(S_NP)
            if window_open and S_NP < s_uav:
                window_open = False; T_cov = t
            if hang_T == np.inf and S_NP < hang_thresh:
                hang_T = t

    t_arr = np.asarray(t_hist); snp_arr = np.asarray(snp_hist)
    cum_arr = np.asarray(cum_hist)
    # PRIMARY effective area = silhouette at engage_dist centroid travel (calibrated,
    # config-sensitive). Snapshot = deployed shape nearest engage_dist (for half_angle).
    if len(cum_arr) and cum_arr[-1] >= engage_dist:
        S_NP_engage = float(np.interp(engage_dist, cum_arr, snp_arr))
        eng_idx = int(np.argmin(np.abs(cum_arr - engage_dist)))
        X_snapshot = X_all[eng_idx] if eng_idx < len(X_all) else X.copy()
    else:                                                   # never travels engage_dist
        S_NP_engage = float(snp_arr[-1]) if len(snp_arr) else 0.0
        X_snapshot = X.copy()
    # diagnostic mean over first coverage pass (config-invariant ~17; NOT for grounding)
    S_NP_eff = float(np.asarray(snap_snp).mean()) if snap_snp else (
        float(snp_arr.max()) if len(snp_arr) else 0.0)
    range_cov_travel = travel_to_time(t_arr, cum_arr, T_cov) if np.isfinite(T_cov) else float(cum_travel)

    se_arr = np.asarray(se_hist); snpc_arr = np.asarray(snpc_hist)
    return dict(
        # time series
        t=t_arr, S_NP=snp_arr, S_E=se_arr, S_NP_corner=snpc_arr,
        S_cellsum=np.asarray(csum_hist), cum_travel=cum_arr,
        # SPATIAL grounding (baseline-anchored)
        S_des=S_des, S_NP_engage=S_NP_engage, engage_dist=float(engage_dist),
        net_radius=float(np.sqrt(S_NP_engage / np.pi)), S_NP_eff=S_NP_eff,
        coverage_C=coverage(S_NP_engage, s_uav), F_max=F_max, rope_stress=rope_stress(F_max, d),
        X_snapshot=X_snapshot, e_launch=e_launch, n_hat=n_hat, cell_quads=quads,
        # TEMPORAL (documented discrepancy -- NOT validated)
        hang_T_sim=float(hang_T), T_cov=float(T_cov), range_cov_travel=float(range_cov_travel),
        # guards
        guard_stress_ok=bool(rope_stress(F_max, d) <= sigma_b),
        guard_antiball_ok=bool(np.all(se_arr < snpc_arr)) if len(se_arr) else False,
        guard_cfl_ok=bool(guard_cfl_ok),
        # provenance
        dt=dt, dt_cfl=dt_cfl, n_steps=n_steps, drag_power=float(drag_power),
        rho_rope_used=float(rho_rope), rho_air_used=float(rho_air),
        operating_point=(float(theta_deg), float(v0), float(m_block * 1000.0)),
    )


# ------------------------------------------------------- paper anchors -----------
# N1_paper_anchors.md Tables 8 & 9 (Pareto frontier): (name, theta, v, m_g, C, T_s).
# T column kept ONLY for the documented discrepancy -- NOT a validation target.
FRONTIER = [
    ("baseline", 45, 60, 35, 2.3174, 1.8529),
    ("A",        65, 90, 25, 2.4802, 1.2965),
    ("B",        55, 70, 25, 2.4399, 1.4828),
    ("C",        65, 60, 35, 2.4359, 1.6948),
    ("D",        45, 50, 25, 2.4257, 1.9287),
    ("E",        35, 50, 25, 2.3904, 2.2373),
    ("F",        25, 50, 25, 2.3041, 2.7602),
]

# N1_paper_anchors.md Table 3 (DIRECT effective interception area S_NP, no C-inversion):
# only the two endpoint rows were cleanly recovered from the PDF (config<->S_NP pairing
# flagged garbled for the other 7 -> needs PDF re-confirmation, human lane). These two
# are the load-bearing SPATIAL anchors with frozen rho_air after baseline calibration.
TABLE3_ANCHORS = [          # (theta, v, m_g, S_NP_m2)
    (25, 50, 25, 12.10),    # reported minimum
    (65, 90, 65, 24.40),    # reported maximum
]
# baseline S_NP back-solved from C=2.3174 (used as the rho_air calibration target):
S_NP_BASELINE = 12.54


if __name__ == "__main__":
    print("=== net_forward.py sanity (D1=linear / D3=rho_rope=970; S_NP=silhouette) ===")
    print(f"d={D_ROPE:.3e}m  L0={L0}m  E={E_MOD:.3e}Pa  zeta={ZETA}  rho_rope={RHO_ROPE}  "
          f"m_w={M_W}kg  rho_air={RHO_AIR_DEFAULT}")
    msh = build_mesh()
    print(f"nodes={msh['n_nodes']}  edges={len(msh['edges'])} "
          f"(struct={(msh['kind']==0).sum()} diag={(msh['kind']==1).sum()})  cells={len(msh['cell_quads'])}")
    mn = lump_node_mass(msh, m_block=0.035)
    ke, ce, Sx = edge_coeffs(msh)
    print(f"sum(m_node)={mn.sum()*1000:.1f}g (=m_w+4*35g={170+140}g)  "
          f"m_node_min={mn.min()*1000:.3f}g  k_max={ke.max():.1f}N/m  dt_cfl={cfl_dt(ke,mn):.2e}s")

    r = simulate(theta_deg=45, v0=60, m_block=0.035)
    print(f"\n-- baseline (45 deg, 60 m/s, 35 g), rho_air={RHO_AIR_CAL} (calibrated) --")
    print(f"S_des(flat)={r['S_des']:.2f}  S_NP_engage@{r['engage_dist']:.0f}m={r['S_NP_engage']:.2f}m^2 "
          f"(paper back-solved {S_NP_BASELINE})  net_radius={r['net_radius']:.3f}m  C={r['coverage_C']:.4f}")
    print(f"F_max={r['F_max']:.2f}N  stress={r['rope_stress']/1e6:.3f}MPa (<= {SIGMA_B/1e6})  "
          f"guards: stress={r['guard_stress_ok']} antiball={r['guard_antiball_ok']} cfl={r['guard_cfl_ok']}")
    print(f"   [TEMPORAL = documented discrepancy, NOT validated] hang_T_sim={r['hang_T_sim']:.3f}s "
          f"(paper 1.853, breathing/no-wrap)  T_cov={r['T_cov']:.3f}s  range_cov_travel={r['range_cov_travel']:.1f}m")

    print(f"\nconfig-ordering secondary diagnostic (S_NP @ {ENGAGE_DIST:.0f}m, pre-fixed; ordering only):")
    print(f"{'cfg':8s} {'th':>3s} {'v':>3s} {'m':>3s} | {'S_NP':>6s} {'r_eq':>6s} "
          f"{'F(N)':>6s} {'MPa':>6s} | {'hangTsim':>8s} {'Tpaper':>6s} {'(paperSnp)':>10s}")
    paper_snp = {"baseline": 12.54, "F": 12.10, "A": 24.40}
    for name, th, v, mg, Cpap, Tpap in FRONTIER:
        rr = simulate(theta_deg=th, v0=v, m_block=mg / 1000.0)
        ps = paper_snp.get(name, "")
        print(f"{name:8s} {th:>3d} {v:>3d} {mg:>3d} | {rr['S_NP_engage']:>6.2f} {rr['net_radius']:>6.3f} "
              f"{rr['F_max']:>6.2f} {rr['rope_stress']/1e6:>6.3f} | "
              f"{rr['hang_T_sim']:>8.3f} {Tpap:>6.3f} {str(ps):>10s}")

    print(f"\nTable-3 endpoints (under-predicted spread, documented limitation):")
    for th, v, mg, snp in TABLE3_ANCHORS:
        rr = simulate(theta_deg=th, v0=v, m_block=mg / 1000.0)
        print(f"   ({th},{v},{mg}g): sim S_NP@{ENGAGE_DIST:.0f}m={rr['S_NP_engage']:.2f}  paper={snp}  "
              f"rel={abs(rr['S_NP_engage']-snp)/snp*100:.1f}%")

    cs = r['S_cellsum']; sn = r['S_NP']
    print(f"\nover-count check (risk 7): min cellsum={cs.min():.2f} vs min silhouette={sn.min():.2f} "
          f"(silhouette collapses, cellsum floors)")
    rd = simulate(theta_deg=45, v0=60, m_block=0.035, rho_rope=1440.0)
    print(f"D3 micro-check rho_rope 970->1440: dS_NP_eff={rd['S_NP_eff']-r['S_NP_eff']:+.3f}m^2  "
          f"dF_max={rd['F_max']-r['F_max']:+.3f}N (damping-only, expect small)")
