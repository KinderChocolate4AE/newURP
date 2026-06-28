# Fire-gate (theta_fire) calibration — conservative v_shot (L2 prep)

Conservative union `n_segments=4`, `n_samples=800`, `tau=0.4`, point-mass sphere, NO limiters. External label = analytic ball-in-sphere containment (`R_reach = 1/2 a tau^2 <= net_radius`).

**Recommended `theta_fire` (conservative) = 0.925.** Zero-wasted-shot band = [0.850, 1.000] (any theta here fires ONLY when robustly contained, i.e. `v_shot_worst==1`); recommendation is placed mid-band for margin against the finite-witness boundary gap. Max-F1 theta = 0.850. **Raise from the legacy 0.8** (0.8 lies BELOW 0.850 -> it would fire at intermediate containment where `worst==0`, wasting a miss-is-free shot).

Note: across both sweeps the conservative `v_shot_worst` agrees with the EXACT analytic containment label at every point — empirical evidence the conservative worst tracks true containment (it is still not a formal certificate; see the analytic helper / S14 caveat).

## Agility sweep (net_radius=2.0; contained iff a<=25 at tau=0.4)

| a_att_max | soft | worst | R_reach | contained |
|---|---|---|---|---|
| 10.000 | 1.000 | 1.000 | 0.800 | True |
| 12.500 | 1.000 | 1.000 | 1.000 | True |
| 15.000 | 1.000 | 1.000 | 1.200 | True |
| 17.500 | 1.000 | 1.000 | 1.400 | True |
| 20.000 | 1.000 | 1.000 | 1.600 | True |
| 22.500 | 1.000 | 1.000 | 1.800 | True |
| 25.000 | 1.000 | 1.000 | 2.000 | True |
| 27.500 | 0.722 | 0.000 | 2.200 | False |
| 30.000 | 0.569 | 0.000 | 2.400 | False |
| 32.500 | 0.423 | 0.000 | 2.600 | False |
| 35.000 | 0.331 | 0.000 | 2.800 | False |
| 37.500 | 0.255 | 0.000 | 3.000 | False |
| 40.000 | 0.204 | 0.000 | 3.200 | False |

## net_radius sweep (a=30; contained iff net_radius>=2.4)

| net_radius | soft | worst | R_reach | contained |
|---|---|---|---|---|
| 1.500 | 0.204 | 0.000 | 2.400 | False |
| 1.600 | 0.255 | 0.000 | 2.400 | False |
| 1.700 | 0.316 | 0.000 | 2.400 | False |
| 1.800 | 0.390 | 0.000 | 2.400 | False |
| 1.900 | 0.489 | 0.000 | 2.400 | False |
| 2.000 | 0.569 | 0.000 | 2.400 | False |
| 2.100 | 0.645 | 0.000 | 2.400 | False |
| 2.200 | 0.735 | 0.000 | 2.400 | False |
| 2.300 | 0.846 | 0.000 | 2.400 | False |
| 2.400 | 1.000 | 1.000 | 2.400 | True |
| 2.500 | 1.000 | 1.000 | 2.400 | True |
| 2.600 | 1.000 | 1.000 | 2.400 | True |
| 2.700 | 1.000 | 1.000 | 2.400 | True |
| 2.800 | 1.000 | 1.000 | 2.400 | True |
| 2.900 | 1.000 | 1.000 | 2.400 | True |
| 3.000 | 1.000 | 1.000 | 2.400 | True |

## Threshold sweep (gate vs analytic label, both sweeps combined)

| theta | fire_rate | precision | recall | f1 | wasted |
|---|---|---|---|---|---|
| 0.500 | 0.690 | 0.700 | 1.000 | 0.824 | 6 |
| 0.525 | 0.690 | 0.700 | 1.000 | 0.824 | 6 |
| 0.550 | 0.690 | 0.700 | 1.000 | 0.824 | 6 |
| 0.575 | 0.621 | 0.778 | 1.000 | 0.875 | 4 |
| 0.600 | 0.621 | 0.778 | 1.000 | 0.875 | 4 |
| 0.625 | 0.621 | 0.778 | 1.000 | 0.875 | 4 |
| 0.650 | 0.586 | 0.824 | 1.000 | 0.903 | 3 |
| 0.675 | 0.586 | 0.824 | 1.000 | 0.903 | 3 |
| 0.700 | 0.586 | 0.824 | 1.000 | 0.903 | 3 |
| 0.725 | 0.552 | 0.875 | 1.000 | 0.933 | 2 |
| 0.750 | 0.517 | 0.933 | 1.000 | 0.966 | 1 |
| 0.775 | 0.517 | 0.933 | 1.000 | 0.966 | 1 |
| 0.800 | 0.517 | 0.933 | 1.000 | 0.966 | 1 |
| 0.825 | 0.517 | 0.933 | 1.000 | 0.966 | 1 |
| 0.850 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
| 0.875 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
| 0.900 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
| 0.925 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
| 0.950 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
| 0.975 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
| 1.000 | 0.483 | 1.000 | 1.000 | 1.000 | 0 |
