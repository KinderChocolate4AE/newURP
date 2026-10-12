"""Trajectory plots: python viz.py out.png [n] [kind] [seed] -- scripted def vs scripted attacker."""
import sys, jax, jax.numpy as jnp, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sim import *


def trace(key, n, def_pol, att_pol, kind=None, use_net=True, use_lim=True):
    s0 = reset(key, n, use_net, use_lim, kind)
    def body(s, _):
        s2 = step(s, def_pol(s), att_pol(s))
        return s2, s2
    _, tr = jax.lax.scan(body, s0, None, length=N_CTRL)
    return jax.tree.map(np.asarray, tr)


def plot(tr, ax_xy, ax_xz, title=""):
    end = int(np.argmax(tr.status != 0)) + 1 if (tr.status != 0).any() else len(tr.status)
    tr = jax.tree.map(lambda x: x[:end], tr)
    for ax, (i, j) in ((ax_xy, (0, 1)), (ax_xz, (0, 2))):
        ax.plot(tr.ap[:, i], tr.ap[:, j], "r-", label="attacker")
        ax.plot(tr.dp[:, i], tr.dp[:, j], "b-", label="net drone")
        for k in range(tr.lp.shape[1]):
            ax.plot(tr.lp[:, k, i], tr.lp[:, k, j], "g-", lw=0.8, label="limiter" if k == 0 else None)
        on = tr.net_on.astype(bool)
        ax.plot(tr.net_p[on, i], tr.net_p[on, j], "c.", ms=3, label="net")
        ax.plot(0, 0, "k*", ms=10)
        ax.set_aspect("equal", "datalim")
    ax_xy.set_title(f"{title} status={int(tr.status[-1])} t={float(tr.t[-1]):.1f}s", fontsize=8)
    ax_xy.legend(fontsize=6)


if __name__ == "__main__":
    # python viz.py out.png n [def.pkl|script] [att.pkl|script]
    from rl import policy_fn, def_side, red_pol, load
    out = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    dp = sys.argv[3] if len(sys.argv) > 3 else "script"
    at = sys.argv[4] if len(sys.argv) > 4 else "script"
    dpol = def_script if dp == "script" else policy_fn(def_side(n), load(dp))
    apol = att_script if at == "script" else red_pol(load(at))
    fig, axs = plt.subplots(3, 6, figsize=(24, 12))
    for c in range(6):
        kind, seed = c % 3, 900 + c
        tr = trace(jax.random.PRNGKey(seed), n, dpol, apol, kind=kind)
        plot(tr, axs[0, c], axs[1, c], f"kind={kind} seed={seed}")
        end = int(np.argmax(tr.status != 0)) + 1 if (tr.status != 0).any() else len(tr.status)
        z = jax.tree.map(lambda x: x[max(0, end - 30):end], tr)  # last 3 s, x-z plane
        plot(z, axs[2, c], axs[2, c], "")
    fig.suptitle(f"def={dp} att={at}")
    fig.tight_layout(); fig.savefig(out, dpi=70)
