# RQ1 — EXP1 (PID + aoi_floor) and EXP2 (n=10 CI tightening)

**Auto-generated on disk by `floor_ci_driver.ps1` -> `analyze_floor_ci.py`** (detached, independent of the agent session). Commit left to the operator.

Locked base (do NOT recalibrate): episodes=300, eta_lam=1.0, lam_max=20, PID gains kp=1.0 ki=1.0 kd=0.5, scenario 5 platoons x 4 veh x 3 RB, eps=0.10. Per-platoon violation recomputed at each cell's tau from `AoI_evolution.mat`, last-100-ep.

## EXP1 — does --aoi_floor 0.005 bound the truly-infeasible seed2-pl2 under PID?

Closes the loop: PID removes pseudo-infeasibility (phase study); the floor handles the ONE residual TRUE infeasibility (seed2-pl2, lambda-saturated ~20 at every tau). Per-platoon, no-floor (`t8e10_pid`) -> floor (`t8e10_pid_floor`): violation, mean AoI, final lambda.

**seed 2** (no-floor -> floor):

| platoon | viol | mean AoI | final lambda |
|---|---|---|---|
| pl0 | 0.086 -> 0.086 | 4.5 -> 4.2 | 6.7 -> 4.6 |
| pl1 | 0.095 -> 0.093 | 4.2 -> 3.5 | 1.5 -> 1.4 |
| pl2 | 0.127 -> 1.000 | 4.3 -> 100.0 | 19.9 -> 20.0 |
| pl3 | 0.093 -> 0.104 | 4.2 -> 4.1 | 3.2 -> 2.5 |
| pl4 | 0.074 -> 0.097 | 3.1 -> 3.2 | 0.0 -> 0.2 |
| **net** | 0.095 -> 0.276 | 4.1 -> 23.0 | worst-pl viol 0.127 -> 1.000 |

**seed 3** (no-floor -> floor):

| platoon | viol | mean AoI | final lambda |
|---|---|---|---|
| pl0 | 0.194 -> 0.063 | 5.4 -> 3.3 | 18.4 -> 17.2 |
| pl1 | 0.092 -> 0.085 | 3.9 -> 4.1 | 2.3 -> 3.0 |
| pl2 | 0.048 -> 0.109 | 2.5 -> 4.5 | 1.0 -> 4.7 |
| pl3 | 0.100 -> 0.092 | 4.7 -> 4.3 | 1.3 -> 1.4 |
| pl4 | 0.077 -> 0.089 | 4.0 -> 4.1 | 5.2 -> 7.3 |
| **net** | 0.102 -> 0.088 | 4.1 -> 4.0 | worst-pl viol 0.194 -> 0.109 |

**seed 4** (no-floor -> floor):

| platoon | viol | mean AoI | final lambda |
|---|---|---|---|
| pl0 | 0.096 -> 0.093 | 4.3 -> 4.4 | 12.3 -> 2.7 |
| pl1 | 0.087 -> 0.116 | 4.6 -> 4.2 | 4.1 -> 13.9 |
| pl2 | 0.122 -> 0.083 | 5.5 -> 3.8 | 2.1 -> 2.7 |
| pl3 | 0.095 -> 0.104 | 4.4 -> 4.5 | 3.1 -> 2.6 |
| pl4 | 0.036 -> 0.048 | 3.0 -> 3.0 | 12.6 -> 14.9 |
| **net** | 0.087 -> 0.089 | 4.4 -> 4.0 | worst-pl viol 0.122 -> 0.116 |

**EXP1 verdict (NEGATIVE / seed-dependent under PID).** The closing-the-loop
hypothesis ("PID removes pseudo-infeasibility; the floor handles the one true
infeasibility") does **NOT** hold under PID, and is in fact REVERSED on the headline
seed:
- **seed2 (the structurally-infeasible case): the floor makes pl2 dramatically
  WORSE** — viol 0.127 -> **1.000**, mean AoI 4.3 -> **100.0** slots (fully abandoned,
  AoI pinned at the cap, lambda saturated 19.9 -> 20.0). Crucially, under PID the
  *no-floor* baseline already kept pl2 near-feasible (viol 0.127, AoI 4.3); adding the
  0.005 AoI floor perturbed that balance and the policy starved pl2 entirely. It also
  nudged a feasible platoon over eps (s4pl1 0.087 -> 0.116).
- **seed3: the floor HELPS** — pl0 rescued 0.194 -> 0.063 (AoI 5.4 -> 3.3), net viol
  0.102 -> 0.088.
- **seed4 (already feasible): roughly neutral** — net AoI 4.4 -> 4.0, one platoon
  nudged just over eps (s4pl1 0.087 -> 0.116).

So under PID the floor's effect on the bottleneck is **seed-dependent and can be
catastrophic** (seed2), unlike the uniformly-positive floor result observed earlier
under the INTEGRAL dual (where seed2-pl2 went AoI 90 -> 17). Interpretation: PID
alone already nearly serves the bottleneck on seed2 (AoI 4.3, not the integral-era
90), so there is little true infeasibility left for the floor to fix, and the extra
penalty term instead destabilizes a delicately-balanced policy. n=3 (seeds 2,3,4);
do not over-read, but the seed2 reversal is unambiguous and is reported, not hidden.

## EXP2 — do the phase claims survive at n=10? (seeds 2-11)

CI-critical cells at eps=0.10, both duals, n=6 (seeds 2-7) vs n=10 (seeds 2-11).

### #platoons passing (<=eps) per cell

| cell | integral n=6 | integral n=10 | pid n=6 | pid n=10 |
|---|---|---|---|---|
| t8e10 | 2.50 +- 1.45 | 2.70 +- 0.96 | 4.00 +- 0.66 | **3.70 +- 0.68** |
| t10e10 | 3.50 +- 1.45 | 3.60 +- 0.90 | 3.67 +- 1.08 | **3.80 +- 0.74** |
| t12e10 | 3.50 +- 1.29 | 3.90 +- 0.86 | 3.50 +- 1.10 | **3.20 +- 0.94** |

### worst-feasible violation per cell (n=10)

| cell | integral n=10 | pid n=10 |
|---|---|---|
| t8e10 | 0.141 +- 0.059 | 0.119 +- 0.023 |
| t10e10 | 0.122 +- 0.027 | 0.127 +- 0.046 |
| t12e10 | 0.116 +- 0.030 | 0.119 +- 0.021 |

### soft-vs-hard(PID) worst-platoon violation gap (n=10)

Per seed: soft worst-platoon P(AoI>tau) minus hard-PID worst-platoon P(AoI>tau); positive = hard protects the worst-served platoon.

| cell | soft worst | hard-PID worst | gap (mean +- 95%CI) |
|---|---|---|---|
| t8e10 | 0.443 | 0.119 | **0.324 +- 0.118** |
| t10e10 | 0.355 | 0.127 | **0.228 +- 0.096** |
| t12e10 | 0.284 | 0.119 | **0.165 +- 0.145** |

**EXP2 verdict (mixed — two claims hold, one weakens).**
- **"No off-floor cell reaches strict feasibility" — HOLDS.** At n=10 no CI-cell
  averages >=4.5/5 pass (best is t12e10 integral 3.90 and t10e10 PID 3.80). The
  central phase-diagram conclusion survives the larger sample.
- **Soft-vs-hard(PID) worst-platoon protection — HOLDS STRONGLY.** The gap stays
  large and (at tau=8,10) clearly positive: 0.324 +- 0.118 (t8e10), 0.228 +- 0.096
  (t10e10), 0.165 +- 0.145 (t12e10). Switching only the AoI handling to a per-platoon
  PID constraint cuts the worst-served platoon's violation by ~0.32 at tau=8. This is
  the core RQ1 result and it is robust at n=10.
- **"PID beats integral on #pass at t8e10" — WEAKENS.** The n=6 point estimate
  (2.50 -> 4.00) shrinks to 2.70 vs 3.70 at n=10, and the 95% CIs now OVERLAP
  (integral [1.74, 3.66] vs PID [3.02, 4.38]) -> the PID #pass advantage is
  directional but **no longer statistically clean** at n=10. (PID's headline win
  remains the sacrifice-count / limit-cycle removal from the stability + phase
  studies, not raw #pass at this single cell.)

## Caveats

- epsilon-soft: *expected* violation-rate constraint, **satisfied up to violation probability eps**, not a per-slot guarantee.
- Still a single 3-RB / 5-platoon / 4-veh scenario; CIs are over seeds, not over scenarios.
- Retained global-critic gradient bug unchanged (orthogonal to the local-actor constraint).

## Reproduce
```
python analyze_floor_ci.py
```
