# RQ1 — tau/eps feasibility phase diagram under the PID dual

**Auto-generated on disk by `phase_pid_driver.ps1` -> `analyze_phase_pid.py`** (detached, independent of the agent session). Commit left to the operator.

Re-draws the full tau/eps phase diagram under PID-Lagrangian (`--dual pid --kp 1.0 --ki 1.0 --kd 0.5`, the stability-study gains) and compares cell-by-cell to the OLD pure-integral diagram. Both sides are recomputed from disk with identical methodology (per-platoon violation recomputed at each cell's tau from `AoI_evolution.mat`, last-100-ep). Locked base: episodes=300, lam_max=20, aoi_floor=0.0, 5 platoons x 4 veh x 3 RB, seeds {2,3,4,5,6,7} (n=6/cell). The structurally-infeasible platoons are reported, not excluded.

Motivation: the old integral phase diagram concluded *loosening tau/eps reduces but does not buy strict feasibility; 3/30 platoons sacrificed*. PID later dominated integral at t8e10 (sacrificed 3->0), suggesting some integral sacrifices were **pseudo-infeasibility** (limit-cycle mis-kills). This re-draw tests whether that holds across the whole grid.

## 1. PID phase heatmap

See `fig_phase_diagram_pid.png` (same format as the old `fig_phase_diagram.png` for side-by-side).

## 2. PID vs integral, per cell (n=6, mean +- 95%% CI)

| (tau, eps) | #pass/5 INT | #pass/5 PID | strict 5/5 INT->PID | worst-feasible INT->PID | #sacrificed INT->PID |
|---|---|---|---|---|---|
| (8, 0.10) | 2.50 +- 1.45 | **4.00 +- 0.66** | 1 -> 1 | 0.163 +- 0.109 -> 0.122 +- 0.041 | 3 -> **0** |
| (8, 0.15) | 4.17 +- 0.79 | **3.00 +- 1.33** | 2 -> 1 | 0.152 +- 0.011 -> 0.244 +- 0.085 | 1 -> **0** |
| (10, 0.10) | 3.50 +- 1.45 | **3.67 +- 1.08** | 1 -> 1 | 0.122 +- 0.047 -> 0.138 +- 0.086 | 0 -> **0** |
| (10, 0.15) | 3.67 +- 0.54 | **3.50 +- 1.45** | 0 -> 2 | 0.169 +- 0.020 -> 0.164 +- 0.038 | 1 -> **1** |
| (12, 0.10) | 3.50 +- 1.29 | **3.50 +- 1.10** | 2 -> 1 | 0.123 +- 0.056 -> 0.125 +- 0.037 | 1 -> **0** |
| (12, 0.15) | 4.00 +- 0.66 | **3.17 +- 1.03** | 1 -> 1 | 0.155 +- 0.008 -> 0.190 +- 0.047 | 0 -> **0** |

Totals over the 6 cells (36 platoon-seeds each): **sacrificed (lambda-saturated) platoon-seeds INT 6 -> PID 1**. Off-floor cells (everything except t8e10) that sacrifice NOBODY under PID: **4 / 5**. Cells averaging >=4.5/5 pass under PID: **0 / 6**.

## 3. Frontier verdict

**SOFTENED, not overturned.** PID removes part of the integral sacrifice (6->1) and tightens the feasible cells, but the frontier shape stands: the on-floor cell t8e10 and the single cap-bound platoon(s) remain resource-limited, not cured by the dual rule.

## 4. Bottleneck diagnostic — do seed2-pl2 / seed3-pl0 recover at looser tau?

Each residual bottleneck tracked at eps=0.10, tau in {8,10,12} under PID (viol@tau, mean AoI, final lambda; SAT = lambda saturated at lam_max=20 => truly resource-limited):

- **seed2-pl2**: tau8: viol=0.127 AoI=4.3 lam=19.9(SAT) | tau10: viol=0.305 AoI=9.2 lam=20.0(SAT) | tau12: viol=0.128 AoI=6.2 lam=19.7(SAT)
- **seed3-pl0**: tau8: viol=0.194 AoI=5.4 lam=18.4(ok) | tau10: viol=0.066 AoI=3.8 lam=11.1(ok) | tau12: viol=0.038 AoI=3.9 lam=4.6(ok)

Reading: if viol falls and lambda comes OFF saturation as tau loosens, the platoon was tau-bound (recoverable); if lambda stays SAT with high AoI at all tau, it is structurally resource-limited (the `--aoi_floor` safeguard's job, not the dual's).

## 5. Caveats

- n=6 seeds/cell: cell means carry wide CIs; read sacrificed-count and the directional frontier, not single-cell point estimates.
- epsilon-soft, not literal hard: this is an *expected* violation-rate constraint (holds in long-run average after convergence), **satisfied up to violation probability eps**, not a per-slot guarantee.
- Scenario/config locked and identical to the integral grid (only the dual rule differs), so the PID-vs-integral shift is attributable to the dual.
- The retained global-critic gradient bug is unchanged (orthogonal to the local-actor constraint).

## 6. Reproduce

```
# from results_remote/, with ../.venv python
python scripts/analyze_phase_pid.py --seeds 2 3 4 5 6 7
```
