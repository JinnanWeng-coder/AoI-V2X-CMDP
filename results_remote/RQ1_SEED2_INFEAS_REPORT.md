# RQ1 — seed2-pl2: structurally infeasible, or under-trained? (1000-ep test)

**Auto-generated on disk by `seed2_driver.ps1` -> `analyze_seed2.py`** (detached). Commit left to the operator.

The ONLY remaining evidence for a truly resource-limited platoon in this scenario was seed2-pl2 (the lone case still 'sacrificed' after ep600), but at 600 ep it was STILL DESCENDING (b10=11.7 b11=14.2 b12=11.0), so it might be merely under-trained. This re-runs seed2 (soft / hard-int / hard-PID) at **1000 ep**, locked config otherwise unchanged (tau=8 eps=0.10 eta_lam=1.0 lam_max=20, PID kp=1 ki=1 kd=0.5, sigma 0.3). pl2 = platoon index 2; last-100-ep at 1000 ep = ep[900,1000).

## 1. seed2-pl2 AoI trajectory @1000 ep (50-ep blocks, 20 blocks)

See `fig_seed2_infeas.png`. Tail blocks (b16..b20) and verdict per arm:

| arm | b1 | b10 | b16 | b17 | b18 | b19 | b20 | last-3 range | b19->b20 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| soft | 98.0 | 11.7 | 12.1 | 7.7 | 7.1 | 4.7 | 2.5 | 4.54 | -2.2 | DESCENDING |
| int | 98.0 | 100.0 | 78.4 | 99.0 | 100.0 | 100.0 | 90.7 | 9.27 | -9.3 | DESCENDING |
| pid | 48.6 | 4.4 | 2.9 | 2.9 | 2.5 | 3.1 | 3.4 | 0.85 | +0.3 | FLAT |

## 2. seed2-pl2 last-100-ep: 300 vs 600 vs 1000 ep

| arm | metric | 300 ep | 600 ep | 1000 ep |
|---|---|---|---|---|
| soft | viol P(AoI>8) | 0.864 | 0.491 | 0.079 |
| | mean AoI | 78.5 | 12.6 | 3.6 |
| | final lambda | 0.0 | 0.0 | 0.0 |
| int | viol P(AoI>8) | 0.974 | 1.000 | 0.990 |
| | mean AoI | 90.3 | 100.0 | 95.4 |
| | final lambda | 20.0 | 20.0 | 20.0 |
| pid | viol P(AoI>8) | 0.127 | 0.065 | 0.087 |
| | mean AoI | 4.3 | 3.3 | 3.2 |
| | final lambda | 19.9 | 18.4 | 3.6 |

## 3. Whole-network last-100-ep violation @1000 ep (all 5 platoons feasible?)

| arm | per-platoon viol | network mean | worst platoon |
|---|---|---|---|
| soft | [0.17, 0.113, 0.079, 0.094, 0.144] | 0.120 | 0.170 |
| int | [0.128, 0.086, 0.99, 0.092, 0.035] | 0.266 | 0.990 |
| pid | [0.101, 0.099, 0.087, 0.096, 0.096] | 0.096 | 0.101 |

## 4. VERDICT

**seed2-pl2 is UNDER-TRAINED, not structurally infeasible.** At 1000 ep the PID arm serves pl2 with bounded AoI (viol=0.087, mean AoI=3.2 slots) and its trajectory has FLAT by block 20; the multiplier is off the cap (lambda=3.6, is NOT saturated). A genuinely resource-limited platoon would pin viol~1.0 / AoI>>tau / lambda=20 at every horizon — pl2 does not. **Implication: NO truly-infeasible platoon remains in this 3-RB/5-platoon scenario, so the --aoi_floor safeguard is NOT strictly necessary here** (it remains useful only as belt-and-suspenders / for tighter tau-eps or richer scenarios). The soft/integral arms still leave pl2 high (soft viol=0.079, int viol=0.990) — i.e. those duals are slower / weaker on this bottleneck, not that the platoon is unservable — pl2's fate is a TRAINING-horizon and dual-rule question, not a structural one.

## 5. Caveats

- epsilon-soft: *expected* violation-rate constraint, satisfied up to violation probability eps, not per-slot.
- Single seed (2) and single 3-RB/5-platoon scenario; this resolves the ONE outstanding case, not a distribution.
- Retained global-critic gradient bug unchanged.

## 6. Reproduce
```
python results_remote/scripts/analyze_seed2.py
```
