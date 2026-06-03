# RQ1 — 600-episode convergence re-run (t8e10, soft / hard-int / hard-PID)

**Auto-generated on disk by `ep600_driver.ps1` -> `analyze_ep600.py`** (detached). Commit left to the operator.

Motivation: three 300-ep runs (soft-s2, hard-int-s3, hard-int-s7) were under-trained -- a cap-bound platoon was still descending at ep300, so their last-100-ep window sat mid-transition. Main.py trains from scratch, so this re-runs t8e10 at **600 ep** (new `_ep600` tags; 300-ep runs untouched). Locked config otherwise identical (eta_lam=1.0, lam_max=20, tau=8, eps=0.10, PID kp=1.0 ki=1.0 kd=0.5, sigma const 0.3). Last-100-ep at 600 ep = ep[500,600).

## 1. Convergence at 600 ep (50-ep blocks; FLAT = last-3-block range <1 slot and last step <1 slot)

| arm | seed | netAoI b1 | b6 | b10 | b11 | b12 | last-3 range | verdict |
|---|---|---|---|---|---|---|---|---|
| soft | 2 | 30.0 | 14.8 | 5.4 | 6.3 | 8.7 | 3.35 | NOT-flat |
| soft | 3 | 20.7 | 6.1 | 5.5 | 5.2 | 6.0 | 0.71 | FLAT |
| soft | 4 | 27.1 | 4.6 | 5.4 | 4.9 | 5.2 | 0.47 | FLAT |
| soft | 5 | 19.4 | 6.3 | 5.8 | 5.3 | 5.2 | 0.57 | FLAT |
| soft | 6 | 35.2 | 4.7 | 4.5 | 4.5 | 4.2 | 0.34 | FLAT |
| soft | 7 | 19.1 | 6.2 | 4.7 | 4.8 | 4.6 | 0.20 | FLAT |
| int | 2 | 30.9 | 30.0 | 23.0 | 23.1 | 23.6 | 0.66 | FLAT |
| int | 3 | 29.7 | 6.5 | 4.0 | 3.9 | 4.8 | 0.84 | FLAT |
| int | 4 | 22.1 | 3.6 | 3.9 | 4.1 | 4.4 | 0.41 | FLAT |
| int | 5 | 20.2 | 3.7 | 4.8 | 3.7 | 8.9 | 5.20 | NOT-flat |
| int | 6 | 20.2 | 4.3 | 5.2 | 4.6 | 5.2 | 0.68 | FLAT |
| int | 7 | 30.2 | 14.3 | 4.6 | 4.9 | 4.0 | 0.89 | FLAT |
| pid | 2 | 19.2 | 3.8 | 4.5 | 4.6 | 4.1 | 0.53 | FLAT |
| pid | 3 | 20.8 | 4.3 | 4.2 | 5.1 | 4.3 | 0.86 | FLAT |
| pid | 4 | 19.6 | 4.1 | 4.5 | 4.6 | 4.7 | 0.26 | FLAT |
| pid | 5 | 18.4 | 4.4 | 4.2 | 4.4 | 4.5 | 0.30 | FLAT |
| pid | 6 | 16.5 | 4.1 | 3.8 | 3.8 | 4.1 | 0.36 | FLAT |
| pid | 7 | 17.5 | 4.0 | 6.6 | 4.2 | 3.9 | 2.71 | NOT-flat |

**Previously-flagged cap-bound platoons @600 ep (per-platoon mean AoI by block):**

| platoon | b1 | b6 | b10 | b11 | b12 | still descending? |
|---|---|---|---|---|---|---|
| soft s2 pl2 | 98.0 | 57.0 | 11.7 | 14.2 | 11.0 | YES |
| int s3 pl0 | 98.3 | 13.1 | 2.2 | 2.0 | 6.5 | no |
| int s7 pl0 | 96.9 | 53.8 | 5.3 | 7.8 | 3.1 | YES |

**Convergence verdict: 600 ep is INSUFFICIENT** for: soft-s2-pl2, int-s7-pl0 -- a cap-bound platoon is still descending at block 12 (drop >2 slots b11->b12). Do NOT assume 600 is enough for this 3-RB/5-platoon scenario.

## 2. Last-100-ep violation P(AoI>8): 300 ep vs 600 ep, per seed

| seed | soft 300->600 (worst-pl) | int 300->600 (worst-pl) | pid 300->600 (worst-pl) |
|---|---|---|---|
| 2 | 0.864 -> 0.491 | 0.974 -> 1.000 | 0.127 -> 0.138 |
| 3 | 0.366 -> 0.333 | 0.617 -> 0.113 | 0.194 -> 0.165 |
| 4 | 0.325 -> 0.216 | 0.097 -> 0.115 | 0.122 -> 0.115 |
| 5 | 0.364 -> 0.407 | 0.110 -> 0.171 | 0.103 -> 0.119 |
| 6 | 0.350 -> 0.327 | 0.179 -> 0.143 | 0.083 -> 0.125 |
| 7 | 0.535 -> 0.352 | 0.832 -> 0.181 | 0.101 -> 0.095 |

## 3. Headline numbers: 300 vs 600

| quantity | 300 ep | 600 ep |
|---|---|---|
| soft-vs-hard(PID) worst-platoon gap (mean +-95%CI, n=6) | 0.346 +- 0.223 | 0.228 +- 0.094 |
| integral sacrificed platoon-seeds (viol>=0.5) | 3 | 1 |
| soft sacrificed platoon-seeds (viol>=0.5) | 2 | 0 |

## 4. Do the 300-ep conclusions change at 600 ep?

- **Under-trained cap-bound platoons:** still not fully converged at 600 (see section 1) -- the 300-ep pessimism is only PARTLY relieved.

- **integral sacrificed count:** 3 (300) -> 1 (600). Drops once the cap-bound platoons finish training, as predicted.

- **soft-vs-hard(PID) worst-platoon gap:** 0.346 -> 0.228. Shrinks as the soft baseline's worst platoon finishes training. It remains positive at 600 ep, so the core RQ1 protection result survives the longer horizon.

- **PID arm:** converged by ep50 in prior analysis; at 600 ep its last-100-ep numbers should be essentially unchanged vs 300 ep (see section 2).

## 5. Caveats

- epsilon-soft: *expected* violation-rate constraint, satisfied up to violation probability eps, not per-slot.
- Single 3-RB / 5-platoon / 4-veh scenario; CIs over 6 seeds.
- If section 1 flags 600 as insufficient, the true converged worst-platoon numbers are even better than reported here -- treat 600-ep values as an upper bound on violation for those runs.
- Retained global-critic gradient bug unchanged.

## 6. Reproduce
```
python analyze_ep600.py
```
