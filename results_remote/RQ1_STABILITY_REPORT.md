# RQ1 Task 2 — stability study: sigma-anneal + PID-Lagrangian

**Auto-generated on disk by the detached `stability_finalize_watch.ps1` -> `finalize_stability.py`** (independent of the agent session / SSH). Commit is left to the operator.

Clean ablation on the LOCKED base (do NOT recalibrate): `tau=8 eps=0.10 lam_max=20 episodes=300 aoi_floor=0.0`, seeds {2,3,4,5,6,7}, paired. Per-platoon violation is the last-100-ep mean recomputed at tau=8 from `AoI_evolution.mat` (identical to the headline analysis). The 3 structurally-infeasible platoons are reported, not excluded.

Three arms (only the stability knob differs):

- **A baseline** — `sigma=0.3` const, integral dual (the EXISTING hard `t8e10` seeds 2-7, reused; not rerun).
- **B anneal** — `--sigma_anneal` (sigma 0.3->0.05 linearly), integral dual.
- **C pid** — `sigma=0.3` const, `--dual pid --kp 1.0 --ki 1.0 --kd 0.5`.

Motivation: (a) per-seed RL variance leaves a feasible platoon a hair over eps (sigma-anneal target); (b) the dual shows per-seed limit-cycles (PID-Lagrangian target).

## 1. Three-arm aggregate (mean +- 95%% CI over seeds 2-7, last-100-ep)

| metric | baseline (A) | anneal (B) | pid (C) |
|---|---|---|---|
| #feasible (viol<=eps) / 5 | 2.500 +- 1.447 | 2.833 +- 1.395 | 4.000 +- 0.664 |
| worst-feasible violation | 0.163 +- 0.109 | 0.286 +- 0.199 | 0.122 +- 0.041 |
| #hair-over-eps platoons (eps<viol<=eps+0.05) | 1.667 +- 1.084 | 1.167 +- 1.395 | 0.833 +- 0.790 |
| #infeasible (sacrificed) | 0.500 +- 0.575 | 0.167 +- 0.429 | 0.000 +- 0.000 |
| **lambda std, active platoons** | 1.128 +- 0.879 | 1.195 +- 0.837 | 0.692 +- 0.198 |
| lambda std, all platoons | 0.987 +- 0.696 | 1.131 +- 0.868 | 0.673 +- 0.242 |
| **viol_rate std, active platoons** | 0.087 +- 0.050 | 0.104 +- 0.052 | 0.073 +- 0.010 |
| viol_rate std, all platoons | 0.104 +- 0.051 | 0.104 +- 0.054 | 0.072 +- 0.010 |
| Tx power (dBm) | 14.52 +- 3.31 | 16.30 +- 3.86 | 14.05 +- 1.70 |
| remaining V2V demand | 4717 +- 1815 | 3436 +- 1447 | 2452 +- 420 |

*active platoon = mean lambda over the last 100 ep in (0.5, 19.5), i.e. the multiplier is genuinely working, not pinned at 0 (slack) or 20 (saturated/sacrificed). lambda/viol std over the last 100 ep is the limit-cycle metric: lower = stabler.*

## 2. (a) Does sigma-anneal reduce the hair-over-eps misses?

Per-seed, baseline vs anneal:

| seed | worst-feasible viol (base -> anneal) | #hair-over-eps (base -> anneal) | #feasible/5 (base -> anneal) |
|---|---|---|---|
| 2 | 0.366 -> 0.126 | 1 -> 2 | 2 -> 2 |
| 3 | 0.116 -> 0.125 | 3 -> 3 | 1 -> 2 |
| 4 | 0.097 -> 0.094 | 0 -> 0 | 5 -> 5 |
| 5 | 0.110 -> 0.408 | 2 -> 0 | 3 -> 2 |
| 6 | 0.179 -> 0.490 | 2 -> 0 | 2 -> 4 |
| 7 | 0.110 -> 0.474 | 2 -> 2 | 2 -> 2 |

**Totals over 30 platoon-seeds:** hair-over-eps 10 -> 7; feasible 15 -> 17; sacrificed 3 -> 1. Mean worst-feasible viol 0.163 -> 0.286.

**VERDICT (a): sigma-anneal REDUCES the hair-over-eps count** (10 -> 7) and WORSENS the mean worst-feasible violation (0.163 -> 0.286).

## 3. (b) Does PID-Lagrangian remove the dual limit-cycle?

Per-seed, baseline vs pid (active-multiplier std over the last 100 ep):

| seed | lambda std active (base -> pid) | viol_rate std active (base -> pid) | cycled-under-base-not-pid? |
|---|---|---|---|
| 2 | 2.755 -> 0.363 | 0.166 -> 0.070 | YES |
| 3 | 0.795 -> 0.727 | 0.125 -> 0.068 | no |
| 4 | 0.891 -> 0.854 | 0.049 -> 0.083 | no |
| 5 | 1.198 -> 0.652 | 0.070 -> 0.081 | YES |
| 6 | 0.730 -> 0.893 | 0.052 -> 0.058 | no |
| 7 | 0.399 -> 0.661 | 0.060 -> 0.075 | no |

**Mean over seeds:** lambda-std (active) 1.128 -> 0.692; viol_rate-std (active) 0.087 -> 0.073. Seeds that cycled under baseline but not PID: [2, 5].

**VERDICT (b): PID REDUCES the multiplier limit-cycle** (lambda-std active 1.128 -> 0.692) and REDUCES the violation-rate oscillation (viol-std active 0.087 -> 0.073).

PID feasibility unchanged-or-better as a guardrail: feasible 15 -> 24, sacrificed 3 -> 0, mean worst-feasible 0.163 -> 0.122.

## 4. Cost side — stability not bought with silent power/V2V

| arm | Tx power (dBm) | remaining V2V demand |
|---|---|---|
| baseline | 14.52 | 4717 |
| anneal | 16.30 | 3436 |
| pid | 14.05 | 2452 |

Read: anneal power ABOVE baseline, pid power <= baseline; remaining-V2V-demand moves are reported above. A stability win is only credible if power/V2V do not silently inflate.

## 5. Structurally-infeasible platoons (reported, not excluded)

- **baseline:** [(2, [2], [0.974]), (3, [0], [0.617]), (7, [0], [0.832])]
- **anneal:** [(2, [2], [1.0])]
- **pid:** none

These are the same on-floor (3-RB / 5-platoon) victims as the headline report; the stability knobs are not expected to make a structurally unservable platoon feasible (that is the `--aoi_floor` safeguard's job).

## 6. Figures

- `fig_stability_lambda.png` — per-platoon lambda_j traces over the last 100 ep, baseline vs PID (worst-baseline-cycle seed).
- `fig_stability_anneal.png` — worst-feasible per-platoon violation per seed, baseline vs sigma-anneal, with the eps line.

## 7. Reproduce

```
# from results_remote/, with ../.venv python
python scripts/analyze_stability.py --seeds 2 3 4 5 6 7 --tau 8   # console detail
python scripts/finalize_stability.py --seeds 2 3 4 5 6 7 --tau 8  # this report + figs
```
