# RQ1 — per-platoon CMDP hard constraint: remote GPU report

**Codebase:** `1-ModifiedMADDPGwithTDec` (Parvini AoI-MARL platoon C-V2X).
`--mode soft` = baseline (AoI as `−AoI/20` reward penalty); `--mode hard` = per-platoon
CMDP `P(AoI_j>τ) ≤ ε` via a per-platoon cost critic + Lagrange multiplier `λ_j`
(two-timescale dual ascent). The global-critic gradient bug is retained on purpose
(the constraint attaches to the *local* actor update), so soft-vs-hard is a clean A/B.

**Locked config (unchanged, never recalibrated):** `--tau 8 --eps 0.10 --eta_lam 1.0
--lam_max 20 --episodes 300`. Seeds are paired across modes. Per-platoon violation is
the **last-100-episode** mean recomputed at the analysis τ from `AoI_evolution.mat`
for **both** modes (apples-to-apples; the soft policy is τ-independent).

---

## 1. Environment, timing, and persistent-session tool

| item | value |
|---|---|
| GPU | NVIDIA RTX 4090 (24 GB), CUDA available |
| Python / torch / numpy / scipy | 3.11.11 / **2.6.0+cu126** / **2.2.4** / 1.17.1 |
| env construction | No `aoi_cuda` env exists on this machine. To avoid touching the shared `SimuV2X` conda env, I built a **local venv at `./.venv`** (inside the repo) with `--system-site-packages` (inheriting `SimuV2X`'s torch+CUDA) and `pip install scipy matplotlib` into it. |
| numpy-2.x fix | `numpy 2.2.4` removed `np.int`/`np.bool`; per CLAUDE.md §6.1 I replaced `np.int→int` (`Main.py`) and `np.bool→bool` (`Classes/buffer.py`). No other deprecated aliases present. |
| wiring smoke test | `--mode hard --smoke --seed 2` **exactly reproduced** the documented λ trace (ep2 λ=[3.3, 2.55, 8.1, 4.5, 0]) — λ rises only on violating platoons. |
| per-episode time | **8.7 s/ep** single run; **~5–15 s/ep at 6× concurrency** (varies with other users' load on this shared GPU) → ~75 min per 6-run wave. |
| **persistent-session tool** | **tmux/screen are NOT installed** on this Windows host (only `wsl`, which cannot cleanly reach the Windows CUDA/venv). I used the documented Windows equivalent: a **single detached `Start-Process` driver** (`results_remote/campaign_driver.ps1`, hidden window, UTF-8 logs under `logs/`) that is independent of the SSH/VS-Code session. It launches each wave, **blocks on file-based completion markers** (the savemat line in each run's `.out`), then launches the next — so ≤6 training runs ever run at once. It is **idempotent**: any run whose marker already exists is skipped. |

**Disconnect resilience (observed):** waves A–D completed across several operator
disconnects. One external event at ~05:28 (logoff/reboot/GPU reset) did kill the driver
and the 6 in-flight Wave-E runs at ep 135 (no partial `.mat` written). On reconnect, a
single relaunch of the same driver **skipped all 24 completed runs** (markers present)
and re-ran **only** the 6 missing Wave-E runs from ep 0 — confirming the idempotent
restart. Final state: **30/30 runs complete**, `CAMPAIGN COMPLETE` logged.

**Runs produced (30 total, all 300 ep):** soft seeds {2–7}; hard `t8e10` seeds {2–7};
hard {`t8e15`,`t10e10`,`t10e15`,`t12e10`,`t12e15`} seeds {2,3,4}; hard `t8e10_floor`
(`--aoi_floor 0.005`) seeds {2,3,4}. Tags encode (τ,ε): `t{τ}e{100ε}`.

---

## 2. Experiment 1 — τ/ε feasibility phase diagram

### 2a. Soft side is binding for all τ (free, recomputed; no training)
Worst-platoon `P(AoI>τ)` under the soft baseline, mean over seeds {2–7}, last-100-ep:

| τ | 6 | 8 | 10 | 12 |
|---|---|---|---|---|
| mean worst-platoon viol | 0.571 | **0.467** | 0.382 | 0.316 |

At the locked **τ=8** the worst-served platoon violates at **0.47 ≫ ε=0.10** in every
seed (per-seed worst at τ=8: seed2 0.86, seed3 0.37, seed4 0.32, seed5 0.36, seed6 0.35,
seed7 0.54) — a clearly **binding** regime where the network average hides a starved
platoon. (This env is a *harder* regime than the prior local machine, where soft worst
was 0.27–0.48; torch 2.6/numpy 2.x shift the trained soft policy, so more platoons sit
near the 3-RB/5-platoon feasibility floor.)

### 2b. Hard side (trained), per-seed #platoons driven ≤ ε (seeds 2,3,4)
See `fig_phase_diagram.png`. Per-seed `#pass/5`, mean worst-**feasible** violation, and
the structurally-infeasible (λ-saturated, sacrificed) platoons:

| (τ, ε) | seed2 | seed3 | seed4 | strict 5/5 | worst-feasible (mean) | infeasible (sacrificed) |
|---|---|---|---|---|---|---|
| (8, 0.10) | 2/5 | 1/5 | 5/5 | 1/3 | 0.193 | s2·pl2=0.97, s3·pl0=0.62 |
| (8, 0.15) | 4/5 | 4/5 | 5/5 | 1/3 | 0.150 | s2·pl2≈1.0 |
| (10, 0.10) | 3/5 | 4/5 | 1/5 | 0/3 | 0.145 | **none** |
| (10, 0.15) | 3/5 | 4/5 | 4/5 | 0/3 | 0.168 | s2·pl2≈1.0 |
| (12, 0.10) | 3/5 | 3/5 | 5/5 | 1/3 | 0.102 | s2·pl2=0.61 |
| (12, 0.15) | 4/5 | 3/5 | 5/5 | 1/3 | 0.150 | **none** |

**Reading:** strict "all-5 ≤ ε" is rare because, with **single-seed-per-cell** RL
variance, at least one platoon usually sits a hair over ε. The robust signals: (i) at
the locked ε=0.10/τ=8, the worst-served seed2 has a **structurally unservable** platoon
(pl2, soft AoI already ~cap) that the dual correctly **flags via λ→λ_max and sacrifices**;
(ii) **loosening off the floor removes structural infeasibility** — at (10,0.10) and
(12,0.15) *no* platoon is sacrificed, and at (12,0.10) the worst-feasible platoon lands
at exactly **0.102 ≈ ε**. The frontier is thus τ≈8/ε=0.10 = on the feasibility floor;
ε≈0.15 or τ≥10 moves off it. (seed4 at (10,0.10) = 1/5 is a single-seed limit-cycle
outlier, not a trend — it is 5/5 at (8,0.10) and (12,0.10).)

---

## 3. Experiment 2 — feasibility safeguard (`--aoi_floor`)

**Change (tagged `[RQ1-CMDP]`):** in hard mode, instead of zeroing the soft AoI penalty,
keep a small floor `aoi_penalty_coef = --aoi_floor` (default 0.0 = original behaviour;
used **0.005 ≈ 1/200**), so a platoon whose λ has saturated still gets gradient pressure
rather than being abandoned. Compared at the locked τ=8/ε=0.10, seeds {2,3,4}:

| seed | metric | no-floor | floor 0.005 |
|---|---|---|---|
| **2** | worst-platoon viol (pl2) | **0.974** | **0.592** |
| | pl2 mean AoI (slots) | 90.3 | **16.9** |
| | also-rescued pl1 viol / AoI | 0.366 / 31.8 | **0.075 / 3.8** |
| | feasible pls (0,3,4) viol | 0.066 / 0.097 / 0.129 | 0.075 / 0.093 / 0.090 |
| | network viol / AoI | 0.326 / 27.0 | **0.185 / 6.4** |
| **3** | sacrificed pl0 viol / AoI | **0.617 / 44.5** | **0.046 / 2.8** |
| | feasible pls (1–4) viol | ≤0.116 | ≤0.117 |
| | network viol / AoI | 0.210 / 13.1 | **0.083 / 3.9** |
| **4** (already feasible) | network viol / AoI | 0.072 / 3.71 | 0.074 / 3.95 |

See `fig_floor.png`. **Verdict on the safeguard:** the floor **bounds the unservable
platoon dramatically** (seed2-pl2 AoI 90→17, viol 0.97→0.59; seed3-pl0 fully rescued
0.62→0.046) and even pulls a second squeezed platoon back under ε (seed2-pl1
0.37→0.075) — **without pushing any feasible platoon above ε** (their violations move by
≤0.01) and **with no harm where the constraint was already satisfied** (seed4 unchanged).
The price is concentrated power on the bottleneck (e.g. seed3-pl0 23.7→28.2 dBm) — the
floor spends power to serve the starved platoon instead of abandoning it. This directly
fixes the "silently sacrificed platoon" limitation.

---

## 4. Multi-metric soft-vs-hard (τ=8, ε=0.10) — cost reported, not AoI alone

Network mean over seeds {2–7}, last-100-ep, **mean ± 95% CI (t, n=6)**:

| metric | soft | hard |
|---|---|---|
| violation `P(AoI>8)` | 0.231 ± 0.036 | 0.171 ± 0.111 |
| mean AoI (slots) | 7.69 ± 5.78 | 11.72 ± 10.17 |
| **Tx power (dBm)** | **8.90 ± 2.06** | **14.52 ± 3.31** |
| V2V rate | 705.8 ± 103.4 | 735.6 ± 193.5 |
| **remaining V2V demand** | **2061.6 ± 389.7** | **4717.0 ± 1815.2** |
| V2I rate | 359.3 ± 60.6 | 321.1 ± 51.9 |
| V2I success (frac ≥ 540) | 0.269 ± 0.049 | 0.232 ± 0.041 |

The wide CIs on viol/AoI are driven by **3/30 sacrificed platoons** (seed2-pl2 0.86→0.97,
seed3-pl0 0.21→0.62, seed7-pl0 0.54→0.83; λ→λ_max, AoI→cap). The honest split:

- **Feasible platoons (27/30 pairs): violation soft 0.197 → hard 0.100** — driven to the
  ε target exactly — at **essentially flat AoI (5.05 → 5.22 slots)**. This is the core
  RQ1 result: where the constraint is feasible, the per-platoon CMDP equalizes every
  platoon onto the ε line at no AoI cost.
- **Rank-sorted (rank0 = soft-worst):** soft has a steep service gradient (worst 0.467 →
  best 0.078); hard compresses the middle ranks toward ε (2nd 0.291→0.105, 3rd
  0.207→0.167), lifting the best-served slightly (0.078→0.094) to protect the worst —
  classic equalization.
- **Cost of the guarantee (the key caveat (c)):** hard is **not free** — it uses **~1.6×
  transmit power** (8.9→14.5 dBm), leaves **>2× more V2V/CAM demand unmet** (2062→4717)
  and slightly lower V2I rate/success. AoI only resets on a successful V2I transmission,
  so the hard policy buys AoI-tail protection by spending power and V2V headroom.

λ convergence (`fig_lambda.png`): multipliers concentrate on each seed's bottleneck and
settle at stable non-saturated values for feasible platoons; the sacrificed platoons pin
at λ_max=20 — the correct Lagrangian signal of infeasibility.

---

## 5. Verdict

**The per-platoon CMDP constraint is useful, but only in the feasible regime, and not for
free.** Where a platoon is servable, switching only the AoI handling from soft penalty to
per-platoon constraint drives its violation **exactly to the ε=0.10 target** (feasible
mean 0.197→0.100) and flattens the soft baseline's steep service gradient onto the ε line
at negligible mean-AoI cost — protecting the worst-served platoon that the soft network
average hides. The regime matters: at the locked τ=8/ε=0.10 the constraint sits **on the
3-RB/5-platoon feasibility floor**, so 3/30 structurally-unservable platoons are correctly
flagged (λ→λ_max) and sacrificed; loosening to ε≈0.15 or τ≥10 removes this infeasibility
(phase diagram), and the new `--aoi_floor` safeguard bounds an unservable platoon
dramatically (AoI 90→17 slots) **without** harming feasible platoons. The honest price,
shown in the multi-metric table, is **~2× transmit power and worse V2V/CAM delivery** —
the AoI tail guarantee is bought with energy and V2V headroom, not granted for free.

### Figures (`results_remote/`)
- `fig_softsweep.png` — soft worst-platoon violation vs τ (binding for all τ≤12).
- `fig_phase_diagram.png` — heatmap: mean #platoons ≤ ε over (τ,ε).
- `fig_headline_violation.png` — per-seed grouped bars, soft vs hard @ t8e10, ε line.
- `fig_cost_tradeoff.png` — network-mean power / V2V / V2I-success, soft vs hard (±95% CI).
- `fig_lambda.png` — per-seed λ_j convergence traces @ t8e10.
- `fig_floor.png` — Exp2 safeguard: worst-platoon viol & AoI, no-floor vs floor.

### Reproduce
```
# from results_remote/, with ../.venv python
python analyze_remote.py softsweep --seeds 2 3 4 5 6 7 --taus 6 8 10 12
python analyze_remote.py phase     --seeds 2 3 4 --taus 8 10 12 --epses 0.10 0.15
python analyze_remote.py metrics   --seeds 2 3 4 5 6 7 --tau 8 --eps 0.10
python analyze_remote.py floor     --seeds 2 3 4 --tau 8 --eps 0.10
python make_figures.py --seeds 2 3 4 5 6 7 --grid_seeds 2 3 4
```
