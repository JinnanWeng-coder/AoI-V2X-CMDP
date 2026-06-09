# RQ1 — scenario sweep (resource-frontier supplement)

**Auto-generated on disk by `scripts/scenario_driver.ps1` -> `scripts/analyze_scenario.py`** (detached). NUMBERS ONLY; no conclusions drawn. Operator cross-checks the raw `.mat` and makes the load-vs-(viol,power) figure.

Varies ONLY the scenario (n_RB, n_veh); locked CMDP config fixed (tau=8 eps=0.10 dual=pid kp=ki=1.0 kd=0.5 lam_max=20 ep600). 8 cells (n_RB in {2,3,4} x platoons in {4,5,6}, excluding nominal rb3/pl5) x 4 arms x seeds {2,3,4} = 96 runs. worst-platoon violation = `viol_rate.mat[:,-100:].mean(axis=1).max()`; mean power = `power.mat.mean()`.

## 1. Per-(cell, arm, seed): worst-platoon violation | mean Tx power (dBm)

| cell (rb,pl) | arm | seed2 viol/pow | seed3 viol/pow | seed4 viol/pow |
|---|---|---|---|---|
| rb2,pl6 | soft_base | 0.994 / 17.49 | 0.991 / 17.64 | 0.634 / 12.35 |
| rb2,pl6 | pid | 1.000 / 19.40 | 0.999 / 24.76 | 1.000 / 25.37 |
| rb2,pl6 | glmax | 1.000 / 23.02 | 1.000 / 26.20 | 1.000 / 23.83 |
| rb2,pl6 | qind_w10 | 0.996 / 20.75 | 0.985 / 21.97 | 0.986 / 25.47 |
| rb2,pl5 | soft_base | 0.739 / 15.04 | 0.668 / 17.75 | 0.465 / 10.78 |
| rb2,pl5 | pid | 0.866 / 17.79 | 0.939 / 20.47 | 0.751 / 23.35 |
| rb2,pl5 | glmax | 0.989 / 18.01 | 0.853 / 26.54 | 0.811 / 25.53 |
| rb2,pl5 | qind_w10 | 0.940 / 15.27 | 0.998 / 20.37 | 0.571 / 21.88 |
| rb2,pl4 | soft_base | 0.399 / 7.18 | 0.664 / 18.17 | 0.383 / 7.97 |
| rb2,pl4 | pid | 0.401 / 16.77 | 0.517 / 23.66 | 0.370 / 11.31 |
| rb2,pl4 | glmax | 0.773 / 25.60 | 0.968 / 21.43 | 0.541 / 24.26 |
| rb2,pl4 | qind_w10 | 0.079 / 11.72 | 0.609 / 23.04 | 0.918 / 23.68 |
| rb3,pl4 | soft_base | 0.494 / 6.64 | 0.301 / 7.97 | 0.276 / 7.70 |
| rb3,pl4 | pid | 0.186 / 12.17 | 0.116 / 15.68 | 0.112 / 8.92 |
| rb3,pl4 | glmax | 0.082 / 7.64 | 0.125 / 19.24 | 0.085 / 12.10 |
| rb3,pl4 | qind_w10 | 0.041 / 8.33 | 0.096 / 17.62 | 0.037 / 9.72 |
| rb3,pl6 | soft_base | 0.466 / 8.68 | 0.798 / 12.99 | 0.279 / 8.87 |
| rb3,pl6 | pid | 0.369 / 18.30 | 0.328 / 21.15 | 0.630 / 23.95 |
| rb3,pl6 | glmax | 0.436 / 19.44 | 0.577 / 27.58 | 0.810 / 28.14 |
| rb3,pl6 | qind_w10 | 0.201 / 18.18 | 0.097 / 18.75 | 0.496 / 27.02 |
| rb4,pl4 | soft_base | 0.171 / 5.59 | 0.189 / 6.63 | 0.338 / 7.40 |
| rb4,pl4 | pid | 0.111 / 8.17 | 0.103 / 10.91 | 0.111 / 7.97 |
| rb4,pl4 | glmax | 0.089 / 7.39 | 0.075 / 20.16 | 0.206 / 9.69 |
| rb4,pl4 | qind_w10 | 0.007 / 6.26 | 0.022 / 9.30 | 0.019 / 7.40 |
| rb4,pl5 | soft_base | 0.315 / 6.58 | 0.247 / 7.73 | 0.451 / 7.22 |
| rb4,pl5 | pid | 0.995 / 15.10 | 0.169 / 10.43 | 0.104 / 8.43 |
| rb4,pl5 | glmax | 0.068 / 16.64 | 0.078 / 8.61 | 0.096 / 8.98 |
| rb4,pl5 | qind_w10 | 0.121 / 11.15 | 0.047 / 10.65 | 0.019 / 8.93 |
| rb4,pl6 | soft_base | 0.534 / 8.31 | 0.197 / 7.05 | 0.465 / 9.73 |
| rb4,pl6 | pid | 0.304 / 15.44 | 0.119 / 9.55 | 0.123 / 12.05 |
| rb4,pl6 | glmax | 0.079 / 13.65 | 0.051 / 13.07 | 0.180 / 16.63 |
| rb4,pl6 | qind_w10 | 0.103 / 9.49 | 0.093 / 10.04 | 0.163 / 13.98 |

## 2. Sanity checks

**(a) n_platoon rows == P (auto-sizing):** ALL PASS (every viol_rate.mat has P rows)

**(b) global_max lambda identical across platoons:** ALL PASS (max spread over all glmax runs = 0.00e+00)

**(c) fixed-w10 (soft) lambda == 0:** ALL PASS (max |lambda| over all qind runs = 0.00e+00)

## 3. Reproduce
```
python results_remote/scripts/analyze_scenario.py
```
