# RQ1 ablation #4 — Qu-style FIXED-WEIGHT threshold penalty (penalty, not constraint)

**Auto-generated on disk by `scripts/ablation4_driver.ps1` -> `scripts/analyze_ablation4.py`** (detached). NUMBERS ONLY; no conclusions drawn. Operator cross-checks the raw `.mat`.

Arm: `--mode soft --aoi_pen_type indicator --aoi_pen_w {w} --tau 8`, ep600, seeds {2-7}. Same `1{AoI>tau}` signal as the hard CMDP but a FIXED reward weight and NO dual (lambda stays 0). FINAL window = last-100-ep (ep[500,600)), per-platoon violation recomputed at tau=8 from `AoI_evolution.mat`. Run dirs: `marl_model_soft_seed{S}_qind_w{w}_ep600`.

## 1. Per-(seed, w) FINAL-window metrics

| seed | w | worst-platoon viol | network-mean viol | mean Tx power (dBm) |
|---|---|---|---|---|
| 2 | 2 | 1.000 | 0.230 | 5.42 |
| 3 | 2 | 0.974 | 0.245 | 7.46 |
| 4 | 2 | 0.081 | 0.066 | 8.54 |
| 5 | 2 | 0.192 | 0.117 | 8.08 |
| 6 | 2 | 1.000 | 0.229 | 6.02 |
| 7 | 2 | 0.993 | 0.234 | 6.43 |
| 2 | 5 | 1.000 | 0.217 | 7.35 |
| 3 | 5 | 0.162 | 0.066 | 11.55 |
| 4 | 5 | 0.059 | 0.041 | 8.67 |
| 5 | 5 | 0.079 | 0.044 | 8.69 |
| 6 | 5 | 0.051 | 0.032 | 9.53 |
| 7 | 5 | 0.082 | 0.031 | 9.11 |
| 2 | 10 | 0.200 | 0.052 | 11.88 |
| 3 | 10 | 0.248 | 0.080 | 18.41 |
| 4 | 10 | 0.034 | 0.026 | 10.36 |
| 5 | 10 | 0.040 | 0.027 | 9.33 |
| 6 | 10 | 0.097 | 0.032 | 17.97 |
| 7 | 10 | 0.056 | 0.027 | 12.56 |
| 2 | 20 | 0.237 | 0.057 | 13.70 |
| 3 | 20 | 0.250 | 0.075 | 20.46 |
| 4 | 20 | 0.067 | 0.035 | 18.91 |
| 5 | 20 | 0.080 | 0.043 | 17.94 |
| 6 | 20 | 0.085 | 0.031 | 19.62 |
| 7 | 20 | 0.099 | 0.040 | 19.21 |

## 2. Lambda==0 sanity (soft mode => no dual ran)

max |lambda| over the WHOLE lambda.mat per run (MUST be 0.0):

| seed | w | max|lambda| | PASS (==0) |
|---|---|---|---|
| 2 | 2 | 0.000e+00 | YES |
| 3 | 2 | 0.000e+00 | YES |
| 4 | 2 | 0.000e+00 | YES |
| 5 | 2 | 0.000e+00 | YES |
| 6 | 2 | 0.000e+00 | YES |
| 7 | 2 | 0.000e+00 | YES |
| 2 | 5 | 0.000e+00 | YES |
| 3 | 5 | 0.000e+00 | YES |
| 4 | 5 | 0.000e+00 | YES |
| 5 | 5 | 0.000e+00 | YES |
| 6 | 5 | 0.000e+00 | YES |
| 7 | 5 | 0.000e+00 | YES |
| 2 | 10 | 0.000e+00 | YES |
| 3 | 10 | 0.000e+00 | YES |
| 4 | 10 | 0.000e+00 | YES |
| 5 | 10 | 0.000e+00 | YES |
| 6 | 10 | 0.000e+00 | YES |
| 7 | 10 | 0.000e+00 | YES |
| 2 | 20 | 0.000e+00 | YES |
| 3 | 20 | 0.000e+00 | YES |
| 4 | 20 | 0.000e+00 | YES |
| 5 | 20 | 0.000e+00 | YES |
| 6 | 20 | 0.000e+00 | YES |
| 7 | 20 | 0.000e+00 | YES |

**Lambda==0 overall: PASS** (every #4 run is soft mode; no dual leaked in).

## 3. Reference arms (existing, NOT re-run; cross-check only)

| seed | arm | worst-platoon viol | network-mean viol | mean Tx power (dBm) |
|---|---|---|---|---|
| 2 | soft_raw | 0.491 | 0.240 | 10.12 |
| 2 | hard_pid | 0.138 | 0.099 | 11.32 |
| 3 | soft_raw | 0.333 | 0.207 | 8.85 |
| 3 | hard_pid | 0.165 | 0.115 | 13.77 |
| 4 | soft_raw | 0.216 | 0.159 | 8.00 |
| 4 | hard_pid | 0.115 | 0.099 | 8.86 |
| 5 | soft_raw | 0.407 | 0.182 | 6.90 |
| 5 | hard_pid | 0.119 | 0.101 | 8.45 |
| 6 | soft_raw | 0.327 | 0.155 | 6.75 |
| 6 | hard_pid | 0.125 | 0.095 | 8.01 |
| 7 | soft_raw | 0.352 | 0.163 | 7.08 |
| 7 | hard_pid | 0.095 | 0.080 | 9.14 |

## 4. Reproduce
```
python results_remote/scripts/analyze_ablation4.py
```
