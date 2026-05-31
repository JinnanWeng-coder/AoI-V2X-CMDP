# RQ1 soft-vs-hard summary (tau=8, eps=0.10, seeds [2, 3, 4, 5, 6, 7])

## Pass/fail and success fraction

**SUCCESS FRACTION (hard satisfies ALL 5 platoons <= eps): 1/6 seeds.** Mean-AoI improves under hard in 5/6 seeds.

| seed | #platoons<=eps | all<=eps | worst-hard viol | worst-FEASIBLE-hard | meanAoI soft->hard |
|---|---|---|---|---|---|
| 2 | 4/5 | no | 1.000 | 0.099 | 10.36 -> 23.11 (WORSE) |
| 3 | 5/5 | YES | 0.098 | 0.098 | 4.99 -> 3.83 (improve) |
| 4 | 4/5 | no | 0.101 | 0.101 | 4.66 -> 3.70 (improve) |
| 5 | 4/5 | no | 0.105 | 0.105 | 4.92 -> 3.62 (improve) |
| 6 | 4/5 | no | 0.106 | 0.106 | 4.68 -> 3.51 (improve) |
| 7 | 2/5 | no | 0.111 | 0.111 | 4.64 -> 3.86 (improve) |

worst-FEASIBLE-platoon hard viol per seed: [0.099, 0.098, 0.101, 0.106, 0.106, 0.111] (mean 0.103) -- where it is ~eps, hard drove the binding platoon to the boundary.

## Per-seed (last-100-ep viol recomputed @tau)

**seed 2** soft viol [0.385, 0.122, 0.482, 0.196, 0.079] (worst 0.481@pl2); hard viol [0.072, 0.086, 1.0, 0.096, 0.099] (worst 1.000@pl2)

**seed 3** soft viol [0.264, 0.088, 0.341, 0.071, 0.209] (worst 0.341@pl2); hard viol [0.069, 0.092, 0.098, 0.093, 0.09] (worst 0.098@pl2)

**seed 4** soft viol [0.13, 0.354, 0.065, 0.044, 0.212] (worst 0.354@pl1); hard viol [0.088, 0.03, 0.085, 0.101, 0.078] (worst 0.101@pl3)

**seed 5** soft viol [0.199, 0.069, 0.212, 0.095, 0.291] (worst 0.291@pl4); hard viol [0.065, 0.066, 0.034, 0.097, 0.106] (worst 0.105@pl4)

**seed 6** soft viol [0.259, 0.037, 0.196, 0.271, 0.072] (worst 0.271@pl3); hard viol [0.058, 0.059, 0.106, 0.056, 0.098] (worst 0.106@pl2)

**seed 7** soft viol [0.132, 0.175, 0.274, 0.091, 0.086] (worst 0.274@pl2); hard viol [0.057, 0.105, 0.111, 0.09, 0.101] (worst 0.111@pl2)

## Rank-sorted (rank0 = worst-served by soft), mean +/- 95%%CI over seeds

| rank | soft viol | hard viol | soft meanAoI | hard meanAoI |
|---|---|---|---|---|
| worst | 0.335 +/- 0.083 | 0.233 +/- 0.396 | 10.88 | 19.66 |
| 2nd | 0.251 +/- 0.077 | 0.069 +/- 0.025 | 6.19 | 3.50 |
| 3rd | 0.177 +/- 0.038 | 0.083 +/- 0.020 | 5.09 | 3.88 |
| 4th | 0.089 +/- 0.021 | 0.092 +/- 0.006 | 3.38 | 3.87 |
| best | 0.064 +/- 0.020 | 0.086 +/- 0.020 | 2.99 | 3.78 |

network mean viol: soft 0.183 -> hard 0.113; network mean AoI: soft 5.71 -> hard 6.94
