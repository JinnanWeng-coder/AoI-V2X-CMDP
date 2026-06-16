# RQ1 — STOCHASTIC-policy deployment eval (certified policy mu(s)+N(0,sigma))

**Auto-generated on disk by `scripts/deploy_noise_driver.ps1` -> `scripts/analyze_deploy_noise.py`** (detached). NUMBERS ONLY; no conclusions drawn. The operator cross-checks the raw `.mat`; **the sigma=0.3 numbers are the load-bearing deployment claim.**

Decisive test: deploy the policy the CMDP actually certified (stochastic actor `mu(s)+N(0,sigma)`) instead of its greedy determinization. Eval-only WARM rerun (env.AoI=1) from each run's frozen checkpoints; canonical config (tau=8 eps=0.10 dual=pid ep600), canonical scenario, seeds 2-7. Eval: 100 episodes, warmup 5, held-out seeds 12,13,14. sigma swept {0.05,0.1,0.3}; **sigma=0 column = deterministic warm baseline** (greedy). worst = `viol_rate_test_warm[_nNN][_holdout].max()`; power = `power_test_warm[...].mean()`.

## 1. Eval A (in-distribution): worst-platoon viol / mean power, per sigma

| arm | seed | s=0 viol/pow | s=0.05 viol/pow | s=0.1 viol/pow | s=0.3 viol/pow |
|---|---|---|---|---|---|
| soft | 2 | 0.718 / 10.03 | 0.721 / 9.94 | 0.728 / 9.99 | 0.692 / 10.42 |
| soft | 3 | 0.347 / 8.32 | 0.340 / 8.22 | 0.342 / 8.34 | 0.316 / 9.30 |
| soft | 4 | 0.431 / 9.24 | 0.427 / 9.16 | 0.442 / 9.41 | 0.408 / 9.52 |
| soft | 5 | 0.203 / 7.92 | 0.212 / 7.97 | 0.200 / 7.93 | 0.160 / 8.26 |
| soft | 6 | 0.243 / 6.47 | 0.237 / 6.41 | 0.227 / 6.52 | 0.180 / 7.35 |
| soft | 7 | 0.330 / 6.68 | 0.245 / 6.66 | 0.204 / 6.64 | 0.203 / 7.36 |
| pid | 2 | 0.662 / 13.06 | 0.678 / 13.05 | 0.702 / 13.20 | 0.688 / 13.47 |
| pid | 3 | 0.200 / 12.89 | 0.204 / 12.89 | 0.204 / 12.92 | 0.222 / 13.58 |
| pid | 4 | 0.236 / 10.76 | 0.226 / 10.49 | 0.241 / 10.66 | 0.196 / 10.32 |
| pid | 5 | 0.663 / 11.07 | 0.646 / 10.38 | 0.609 / 9.82 | 0.556 / 9.59 |
| pid | 6 | 0.241 / 8.86 | 0.245 / 8.72 | 0.245 / 8.82 | 0.241 / 9.50 |
| pid | 7 | 0.171 / 7.91 | 0.180 / 8.02 | 0.184 / 8.10 | 0.188 / 8.53 |

## 2.1 Eval B (held-out seed 12): worst-platoon viol / mean power, per sigma

| arm | seed | s=0 viol/pow | s=0.05 viol/pow | s=0.1 viol/pow | s=0.3 viol/pow |
|---|---|---|---|---|---|
| soft | 2 | 0.683 / 9.98 | 0.689 / 9.93 | 0.661 / 10.07 | 0.593 / 10.64 |
| soft | 3 | 0.313 / 7.24 | 0.305 / 7.48 | 0.301 / 7.58 | 0.324 / 8.98 |
| soft | 4 | 0.552 / 9.86 | 0.547 / 9.84 | 0.545 / 9.81 | 0.471 / 10.22 |
| soft | 5 | 0.906 / 13.68 | 0.894 / 13.34 | 0.895 / 13.30 | 0.794 / 10.19 |
| soft | 6 | 0.710 / 11.30 | 0.533 / 8.47 | 0.553 / 7.53 | 0.487 / 7.85 |
| soft | 7 | 0.571 / 7.37 | 0.582 / 7.25 | 0.589 / 7.34 | 0.607 / 8.08 |
| pid | 2 | 0.846 / 15.07 | 0.815 / 17.01 | 0.907 / 17.79 | 0.841 / 14.77 |
| pid | 3 | 1.000 / 15.91 | 1.000 / 15.83 | 1.000 / 15.74 | 0.998 / 14.95 |
| pid | 4 | 0.169 / 9.27 | 0.172 / 9.26 | 0.183 / 9.42 | 0.214 / 10.32 |
| pid | 5 | 0.864 / 17.49 | 0.874 / 17.30 | 0.863 / 17.04 | 0.657 / 14.90 |
| pid | 6 | 0.295 / 9.26 | 0.240 / 9.00 | 0.206 / 8.91 | 0.232 / 9.48 |
| pid | 7 | 0.135 / 7.21 | 0.135 / 7.22 | 0.137 / 7.41 | 0.141 / 8.88 |

## 2.2 Eval B (held-out seed 13): worst-platoon viol / mean power, per sigma

| arm | seed | s=0 viol/pow | s=0.05 viol/pow | s=0.1 viol/pow | s=0.3 viol/pow |
|---|---|---|---|---|---|
| soft | 2 | 0.982 / 12.84 | 0.983 / 12.84 | 0.970 / 12.28 | 0.929 / 11.45 |
| soft | 3 | 0.514 / 8.66 | 0.521 / 8.88 | 0.528 / 8.97 | 0.544 / 9.96 |
| soft | 4 | 0.489 / 10.28 | 0.490 / 10.18 | 0.486 / 10.29 | 0.412 / 9.71 |
| soft | 5 | 0.244 / 8.51 | 0.237 / 8.38 | 0.246 / 8.49 | 0.217 / 8.78 |
| soft | 6 | 0.707 / 11.41 | 0.706 / 7.29 | 0.709 / 6.69 | 0.708 / 7.52 |
| soft | 7 | 0.499 / 7.50 | 0.516 / 7.60 | 0.528 / 7.76 | 0.571 / 8.67 |
| pid | 2 | 0.935 / 16.61 | 0.868 / 16.17 | 0.679 / 15.21 | 0.609 / 12.65 |
| pid | 3 | 1.000 / 16.89 | 1.000 / 16.93 | 1.000 / 16.85 | 0.979 / 16.18 |
| pid | 4 | 0.447 / 13.44 | 0.444 / 13.35 | 0.457 / 13.46 | 0.370 / 12.09 |
| pid | 5 | 0.720 / 22.64 | 0.682 / 21.23 | 0.588 / 18.26 | 0.506 / 14.52 |
| pid | 6 | 0.998 / 11.45 | 0.998 / 11.74 | 0.998 / 11.44 | 0.930 / 10.88 |
| pid | 7 | 0.178 / 8.36 | 0.179 / 8.35 | 0.196 / 8.63 | 0.265 / 9.84 |

## 2.3 Eval B (held-out seed 14): worst-platoon viol / mean power, per sigma

| arm | seed | s=0 viol/pow | s=0.05 viol/pow | s=0.1 viol/pow | s=0.3 viol/pow |
|---|---|---|---|---|---|
| soft | 2 | 0.904 / 13.11 | 0.903 / 12.97 | 0.804 / 12.77 | 0.708 / 11.84 |
| soft | 3 | 0.705 / 8.31 | 0.677 / 7.91 | 0.657 / 8.05 | 0.585 / 8.76 |
| soft | 4 | 0.792 / 11.00 | 0.799 / 10.96 | 0.825 / 11.17 | 0.832 / 11.28 |
| soft | 5 | 0.855 / 18.03 | 0.859 / 17.95 | 0.847 / 17.61 | 0.699 / 14.64 |
| soft | 6 | 0.857 / 9.19 | 0.859 / 9.17 | 0.862 / 9.24 | 0.596 / 8.38 |
| soft | 7 | 0.346 / 9.00 | 0.356 / 8.86 | 0.373 / 9.10 | 0.382 / 8.98 |
| pid | 2 | 0.441 / 11.38 | 0.442 / 11.36 | 0.442 / 11.39 | 0.420 / 11.50 |
| pid | 3 | 0.915 / 23.11 | 0.886 / 20.96 | 0.868 / 19.12 | 0.614 / 16.83 |
| pid | 4 | 0.900 / 13.82 | 0.907 / 13.69 | 0.902 / 13.49 | 0.816 / 12.75 |
| pid | 5 | 1.000 / 23.39 | 1.000 / 23.24 | 1.000 / 23.20 | 1.000 / 22.20 |
| pid | 6 | 0.721 / 12.43 | 0.758 / 12.58 | 0.768 / 12.47 | 0.768 / 12.41 |
| pid | 7 | 1.000 / 16.84 | 0.999 / 16.70 | 0.998 / 16.61 | 0.932 / 15.85 |

## 3. Pooled eval-A worst-platoon violation (over seeds 2-7), per arm x sigma

| arm | s=0 | s=0.05 | s=0.1 | s=0.3 |
|---|---|---|---|---|
| soft | 0.379+-0.169 | 0.364+-0.176 | 0.357+-0.187 | 0.327+-0.185 |
| pid | 0.362+-0.214 | 0.363+-0.212 | 0.364+-0.209 | 0.348+-0.198 |

(training reference: soft ~0.35, pid ~0.13)

## 4. Sanity checks

**(a) every viol_rate_test_warm_n*.mat has 5 entries:** ALL PASS

**(b) deterministic *_test_warm* + cold *_test* untouched:** verified out-of-band via the mtime/size snapshot (see commit message / driver log); the noise path only ever writes the `_n{5,10,30}` suffix.

## 5. Reproduce
```
python results_remote/scripts/analyze_deploy_noise.py
```
