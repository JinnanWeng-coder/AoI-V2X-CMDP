# RQ1 — WARM-start frozen-deployment eval (corrected steady-state boot)

**Auto-generated on disk by `scripts/deploy_warm_driver.ps1` -> `scripts/analyze_deploy_warm.py`** (detached). NUMBERS ONLY; no conclusions drawn. The operator cross-checks the raw `.mat`; **the WARM numbers are the load-bearing deployment claim** (the cold synchronized AoI=100 boot deadlocked the greedy policy and is retained only as a documented caveat).

Eval-only WARM rerun (env.AoI=1 steady-state start) from each run's frozen checkpoints; canonical config (tau=8 eps=0.10 dual=pid lam_max=20 ep600), canonical scenario, seeds 2-7. Eval: 100 episodes, warmup 5, held-out seeds 12,13,14. TRAINING worst = `viol_rate.mat[:,-100:].mean(axis=1).max()`; WARM/COLD worst = `viol_rate_test[_warm].max()`; power = `power_test_warm.mat.mean()`.

## 1. Per-(arm, seed): training worst | cold-A worst | WARM-A worst/pow | WARM-B (s12/s13/s14) worst/pow

| arm | seed | train worst | cold-A worst | WARM-A worst/pow | WARM-B s12 | WARM-B s13 | WARM-B s14 |
|---|---|---|---|---|---|---|---|
| soft | 2 | 0.491 | 0.690 | 0.718 / 10.03 | 0.683 / 9.98 | 0.982 / 12.84 | 0.904 / 13.11 |
| soft | 3 | 0.332 | 0.593 | 0.347 / 8.32 | 0.313 / 7.24 | 0.514 / 8.66 | 0.705 / 8.31 |
| soft | 4 | 0.216 | 0.478 | 0.431 / 9.24 | 0.552 / 9.86 | 0.489 / 10.28 | 0.792 / 11.00 |
| soft | 5 | 0.407 | 0.416 | 0.203 / 7.92 | 0.906 / 13.68 | 0.244 / 8.51 | 0.855 / 18.03 |
| soft | 6 | 0.327 | 0.150 | 0.243 / 6.47 | 0.710 / 11.30 | 0.707 / 11.41 | 0.857 / 9.19 |
| soft | 7 | 0.352 | 0.372 | 0.330 / 6.68 | 0.571 / 7.37 | 0.499 / 7.50 | 0.346 / 9.00 |
| pid | 2 | 0.138 | 1.000 | 0.662 / 13.06 | 0.846 / 15.07 | 0.935 / 16.61 | 0.441 / 11.38 |
| pid | 3 | 0.165 | 1.000 | 0.200 / 12.89 | 1.000 / 15.91 | 1.000 / 16.89 | 0.915 / 23.11 |
| pid | 4 | 0.115 | 0.144 | 0.236 / 10.76 | 0.169 / 9.27 | 0.447 / 13.44 | 0.900 / 13.82 |
| pid | 5 | 0.119 | 0.585 | 0.663 / 11.07 | 0.864 / 17.49 | 0.720 / 22.64 | 1.000 / 23.39 |
| pid | 6 | 0.125 | 0.140 | 0.241 / 8.86 | 0.295 / 9.26 | 0.998 / 11.45 | 0.721 / 12.43 |
| pid | 7 | 0.095 | 1.000 | 0.171 / 7.91 | 0.135 / 7.21 | 0.178 / 8.36 | 1.000 / 16.84 |

## 2. Pooled WARM-A worst-platoon violation (over seeds 2-7)

- **soft**: WARM-A worst mean=0.379 std=0.169 (per-seed 0.718, 0.347, 0.431, 0.203, 0.243, 0.330)
- **pid**: WARM-A worst mean=0.362 std=0.214 (per-seed 0.662, 0.200, 0.236, 0.663, 0.241, 0.171)

(training reference: soft ~0.35, pid ~0.13)

## 3. Sanity checks

**(a) every viol_rate_test_warm*.mat has 5 entries:** ALL PASS

**(b) cold *_test*.mat untouched:** verified out-of-band via the mtime/size snapshot (see commit message / driver log); warm code path only ever writes the `_warm` suffix.

## 4. Reproduce
```
python results_remote/scripts/analyze_deploy_warm.py
```
