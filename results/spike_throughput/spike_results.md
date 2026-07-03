# Phase 2A' -- v_shot throughput spike results

baseline env.step (n=2000, k=1): mean 117.3 ms (median 116.0, p90 127.6); fixed overhead (non-viability) ~25.1 ms

## lever 1 -- n_samples sweep (CRN-paired vs n=2000, same state+seed)

| n | B ms | E ms | err_soft mean | err_soft max | headline err max | gate agree | worst agree | coma sign | coma err max |
|---|---|---|---|---|---|---|---|---|---|
| 2000 | 4.1 | 15.8 | 0.0000 | 0.0000 | 0.0000 | 1.000 | 1.000 | 1.000 | 0.0000 |
| 1000 | 3.6 | 11.6 | 0.0007 | 0.0103 | 0.0000 | 1.000 | 1.000 | 1.000 | 0.0000 |
| 500 | 3.1 | 8.6 | 0.0019 | 0.0276 | 0.0000 | 1.000 | 1.000 | 1.000 | 0.0000 |
| 250 | 3.4 | 9.2 | 0.0021 | 0.0371 | 0.0000 | 1.000 | 1.000 | 1.000 | 0.0000 |
| 125 | 3.6 | 8.7 | 0.0026 | 0.0407 | 0.0000 | 1.000 | 1.000 | 1.000 | 0.0000 |

## lever 2 -- coma_D cadence projection T(n, k) [ms/step, single env]

| n | k=1 | k=2 | k=4 | k=8 | k=4 + obs-lite |
|---|---|---|---|---|---|
| 2000 | 143.8 | 112.2 | 96.5 | 88.6 | 76.6 |
| 1000 | 113.6 | 90.3 | 78.7 | 72.9 | 63.5 |
| 500 | 91.4 | 74.2 | 65.6 | 61.3 | 53.9 |
| 250 | 96.6 | 78.1 | 68.9 | 64.3 | 56.2 |
| 125 | 93.4 | 75.9 | 67.2 | 62.8 | 54.9 |

## lever 1b -- NEAR-GATE accuracy (synthesized engaged states)

8 states with ref v_soft [0.606, 0.511, 0.636, 0.828, 0.804, 0.763, 0.851, 0.967] (limiter ring carving escape lobes -- where shaping puts the system):

| n | err mean | err max | gate agree | worst agree |
|---|---|---|---|---|
| 1000 | 0.0247 | 0.0885 | 1.000 | 1.000 |
| 500 | 0.0386 | 0.1900 | 1.000 | 1.000 |
| 250 | 0.0482 | 0.1717 | 1.000 | 1.000 |

READ: on ENGAGED states the n-cut error is ~5x the bank-state error
(n=500 err_max 0.19 > zero-waste band width 0.15; n=1000 err_max ~0.09).
n_samples reduction is NOT safe near the fire gate -> prefer the EXACT
levers (batched eval, obs-lite) and keep n=2000 for reward/gate paths;
n-cuts only for debug loops. Speed knee is ~n=500 anyway (extreme blocks
dominate E below that).

## lever 5 -- shared-distance batched eval (EXACT, needs env.py call-site)

6x separate eval 59.9 ms -> batched 25.3 ms (2.4x), mismatches 0/12 states (0 = bit-identical VShotResults).

## lever 3 -- parallel envs

sandbox nproc=2: 2-way efficiency 0.83 (serial 5.4s vs wall 3.3s)

| recipe | ms/step | steps/s 1 env | 1e6 steps, W workers (eff 0.85) |
|---|---|---|---|
| baseline | 143.8 | 7.0 | 16w 2.94 h / 32w 1.47 h |
| n2000 batched (exact) | 74.4 | 13.4 | 16w 1.52 h / 32w 0.76 h |
| n2000 batched obs-lite | 54.5 | 18.3 | 16w 1.11 h / 32w 0.56 h |
| n1000 k4 | 78.7 | 12.7 | 16w 1.61 h / 32w 0.80 h |
| n500 k4 | 65.6 | 15.2 | 16w 1.34 h / 32w 0.67 h |
| n500 k4 obs-lite | 53.9 | 18.5 | 16w 1.10 h / 32w 0.55 h |
| n500 batched obs-lite | 42.0 | 23.8 | 16w 0.86 h / 32w 0.43 h |
| n250 k4 obs-lite | 56.2 | 17.8 | 16w 1.15 h / 32w 0.57 h |

state-bank v_soft range: [0.000, 0.220] (median 0.000) -- near-gate coverage context.

notes:
- obs-lite = drop/reuse the post-move vres2 union rebuild (obs v-triple only;
  needs an additive env.py param -> freeze decision, see docs/09 SS8).
- coma cadence k needs an env-side skip (frozen env computes coma_D every step);
  S8 only fixes the BASELINE, cadence is contract-legal per docs/09 SS5 2A'.
- batched eval (lever 5) makes cadence mostly moot: all 6 layouts cost ~2 evals.
- state bank = no-fire random-policy visitation on the training corridor;
  gate-agreement stats inherit that distribution (near-gate density caveat).
