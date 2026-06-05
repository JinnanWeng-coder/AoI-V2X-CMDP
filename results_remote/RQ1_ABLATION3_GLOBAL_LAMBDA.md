# RQ1 ablation #3 — per-platoon vs single GLOBAL Lagrange multiplier

**Auto-generated on disk by `ablation3_driver.ps1` -> `analyze_ablation3.py`** (detached). NUMBERS ONLY; no conclusions drawn. Operator cross-checks the raw `.mat`.

Control arms replace per-platoon `lambda_j` with ONE global multiplier driven by network-MEAN (`global_mean`) or WORST (`global_max`) violation. Config matches the existing per-platoon PID ep600 runs byte-for-byte except `--lam_scope` + `--out_tag`: mode=hard tau=8 eps=0.10 dual=pid kp=1 ki=1 kd=0.5 lam_max=20 episodes=600, seeds {2-7}. FINAL window = last-100-ep (ep[500,600)), per-platoon violation recomputed at tau=8 from `AoI_evolution.mat`.

## 1. Per-(seed, scope) FINAL-window metrics

| seed | scope | worst-platoon viol | network-mean viol | mean Tx power (dBm) |
|---|---|---|---|---|
| 2 | glmean | 0.984 | 0.244 | 10.54 |
| 2 | glmax | 0.986 | 0.230 | 16.24 |
| 3 | glmean | 0.492 | 0.133 | 23.83 |
| 3 | glmax | 0.379 | 0.147 | 22.93 |
| 4 | glmean | 0.155 | 0.119 | 9.06 |
| 4 | glmax | 0.179 | 0.127 | 19.93 |
| 5 | glmean | 0.121 | 0.098 | 8.03 |
| 5 | glmax | 0.223 | 0.145 | 19.87 |
| 6 | glmean | 0.185 | 0.098 | 7.94 |
| 6 | glmax | 0.138 | 0.059 | 20.72 |
| 7 | glmean | 0.053 | 0.043 | 12.28 |
| 7 | glmax | 0.063 | 0.035 | 13.97 |

Reference (existing per-platoon PID ep600, NOT re-run; shown for cross-check only):

| seed | scope | worst-platoon viol | network-mean viol | mean Tx power (dBm) |
|---|---|---|---|---|
| 2 | per_platoon | 0.138 | 0.099 | 11.32 |
| 3 | per_platoon | 0.165 | 0.115 | 13.77 |
| 4 | per_platoon | 0.115 | 0.099 | 8.86 |
| 5 | per_platoon | 0.119 | 0.101 | 8.45 |
| 6 | per_platoon | 0.125 | 0.095 | 8.01 |
| 7 | per_platoon | 0.095 | 0.080 | 9.14 |

## 2. Lambda-equality sanity check (global_* must have identical lambda_j across platoons)

max |lambda_j - lambda_k| over ALL episodes & platoon pairs (0.0 => a single global multiplier, as required):

| seed | scope | max platoon spread of lambda | PASS (==0) |
|---|---|---|---|
| 2 | glmean | 0.000e+00 | YES |
| 2 | glmax | 0.000e+00 | YES |
| 3 | glmean | 0.000e+00 | YES |
| 3 | glmax | 0.000e+00 | YES |
| 4 | glmean | 0.000e+00 | YES |
| 4 | glmax | 0.000e+00 | YES |
| 5 | glmean | 0.000e+00 | YES |
| 5 | glmax | 0.000e+00 | YES |
| 6 | glmean | 0.000e+00 | YES |
| 6 | glmax | 0.000e+00 | YES |
| 7 | glmean | 0.000e+00 | YES |
| 7 | glmax | 0.000e+00 | YES |

**Lambda-equality overall: PASS** (all global_* runs use a single shared multiplier).

## 3. Reproduce
```
python results_remote/scripts/analyze_ablation3.py
```
