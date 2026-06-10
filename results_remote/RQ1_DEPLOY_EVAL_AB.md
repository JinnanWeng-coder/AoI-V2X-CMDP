# RQ1 — frozen-deployment eval (Experiment A in-distribution / B held-out)

**Auto-generated on disk by `scripts/deploy_driver.ps1` -> `scripts/analyze_deploy.py`** (detached). NUMBERS ONLY; no conclusions drawn. Operator cross-checks the raw `.mat`.

Re-train the 2 canonical arms into NEW `*_deploy` dirs (canonical `_ep600` runs untouched), then append a FROZEN-policy eval (actor noise=0, no learning/dual/buffer; AoI reset + warmup discarded). Locked config (tau=8 eps=0.10 dual=pid kp=ki=1.0 kd=0.5 lam_max=20 ep600), canonical scenario (5 platoons x 4 veh x 3 RB), seeds 2-7. Eval: 100 episodes, warmup 5, held-out seeds 12,13,14. TRAINING worst = `viol_rate.mat[:,-100:].mean(axis=1).max()`; DEPLOY worst = `viol_rate_test.max()`; power = `power_test.mat.mean()`.

## 1. Per-(arm, seed): training worst | deploy-A worst/pow | deploy-B (s12/s13/s14) worst/pow

| arm | seed | train worst | A worst / pow | B s12 worst/pow | B s13 worst/pow | B s14 worst/pow |
|---|---|---|---|---|---|---|
| soft | 2 | 0.491 | 0.690 / 9.65 | 0.683 / 9.98 | 0.982 / 12.84 | 0.904 / 13.10 |
| soft | 3 | 0.332 | 0.593 / 9.18 | 0.312 / 7.24 | 0.513 / 8.64 | 0.975 / 18.55 |
| soft | 4 | 0.216 | 0.478 / 7.07 | 0.552 / 9.86 | 0.489 / 10.28 | 0.793 / 11.00 |
| soft | 5 | 0.407 | 0.416 / 7.45 | 0.906 / 13.68 | 0.244 / 8.51 | 0.855 / 18.03 |
| soft | 6 | 0.327 | 0.150 / 5.42 | 0.710 / 11.30 | 0.707 / 11.41 | 0.857 / 9.19 |
| soft | 7 | 0.352 | 0.372 / 6.80 | 0.571 / 7.37 | 0.499 / 7.50 | 0.346 / 9.00 |
| pid | 2 | 0.138 | 1.000 / 15.11 | 1.000 / 18.12 | 1.000 / 16.97 | 1.000 / 15.04 |
| pid | 3 | 0.165 | 1.000 / 14.98 | 1.000 / 15.91 | 1.000 / 16.89 | 1.000 / 23.13 |
| pid | 4 | 0.115 | 0.144 / 8.89 | 0.169 / 9.27 | 0.447 / 13.44 | 0.900 / 13.82 |
| pid | 5 | 0.119 | 0.585 / 16.18 | 1.000 / 28.95 | 1.000 / 27.96 | 1.000 / 23.39 |
| pid | 6 | 0.125 | 0.140 / 8.26 | 0.295 / 9.26 | 0.998 / 11.45 | 0.721 / 12.43 |
| pid | 7 | 0.095 | 1.000 / 11.89 | 1.000 / 11.72 | 1.000 / 13.99 | 1.000 / 21.70 |

## 2. Training-time self-check (pooled over seeds 2-7)

- **soft**: training worst-platoon viol mean=0.354 std=0.083 (per-seed 0.491, 0.332, 0.216, 0.407, 0.327, 0.352)
- **pid**: training worst-platoon viol mean=0.126 std=0.022 (per-seed 0.138, 0.165, 0.115, 0.119, 0.125, 0.095)

(canonical reference: soft ~0.35, pid ~0.13)

## 3. Sanity checks

**(a) every *_test has n_platoon=5:** ALL PASS

**(b) reward_cost[:, -100:].mean ~= viol_rate[:, -100:].mean:** max abs diff over all runs = 4.143e-05 (per-run: soft s2 4.143e-05; soft s3 2.197e-05; soft s4 5.847e-06; soft s5 2.161e-05; soft s6 4.391e-06; soft s7 1.758e-05; pid s2 2.271e-06; pid s3 5.700e-06; pid s4 7.522e-06; pid s5 5.969e-06; pid s6 5.862e-06; pid s7 4.236e-06)

**(c) reward_total == reward_t1 + reward_t2:** max abs diff over all runs = 3.906e-03

**(d) soft-deploy lambda == 0:** ALL PASS (max |lambda| over soft runs = 0.00e+00)

## 4. Reproduce
```
python results_remote/scripts/analyze_deploy.py
```
