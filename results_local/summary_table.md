# RQ1 soft-vs-hard summary (tau=8, eps=0.10, seeds [2, 3, 4])

## Per-seed (last-100-ep viol recomputed @tau)

**seed 2** soft viol [0.385, 0.122, 0.482, 0.196, 0.079] (worst 0.481@pl2); hard viol [0.072, 0.086, 1.0, 0.096, 0.099] (worst 1.000@pl2)

**seed 3** soft viol [0.264, 0.088, 0.341, 0.071, 0.209] (worst 0.341@pl2); hard viol [0.069, 0.092, 0.098, 0.093, 0.09] (worst 0.098@pl2)

**seed 4** soft viol [0.13, 0.354, 0.065, 0.044, 0.212] (worst 0.354@pl1); hard viol [0.088, 0.03, 0.085, 0.101, 0.078] (worst 0.101@pl3)

## Rank-sorted (rank0 = worst-served by soft), mean +/- 95%%CI over seeds

| rank | soft viol | hard viol | soft meanAoI | hard meanAoI |
|---|---|---|---|---|
| worst | 0.392 +/- 0.193 | 0.376 +/- 1.345 | 15.32 | 35.40 |
| 2nd | 0.287 +/- 0.219 | 0.073 +/- 0.011 | 6.77 | 3.81 |
| 3rd | 0.178 +/- 0.106 | 0.091 +/- 0.011 | 5.21 | 4.13 |
| 4th | 0.092 +/- 0.072 | 0.088 +/- 0.009 | 3.36 | 3.75 |
| best | 0.065 +/- 0.045 | 0.098 +/- 0.011 | 2.69 | 4.00 |

network mean viol: soft 0.203 -> hard 0.145; network mean AoI: soft 6.67 -> hard 10.22
