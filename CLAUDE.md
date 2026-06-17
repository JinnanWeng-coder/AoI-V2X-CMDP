# CLAUDE.md — RQ1 per-platoon hard-constraint experiment (read this first)

> ## RQ1 STATUS (2026-06-17) — training-level campaign COMPLETE (findings 1–8 settled);
> ## frozen-DEPLOYMENT evaluation UNDER INVESTIGATION: worst-platoon protection DEGRADES when
> ## the policy is frozen — modestly for 4/6 seeds (net-mean ≈ ε), catastrophically for 2/6
> ## (s2, s5; s2 is the under-trained seed), via a marginal platoon tipping over; re-injecting
> ## the certified σ=0.3 noise does NOT fix it. CAUSE NOT YET DISCRIMINATED (under-training vs
> ## online-dual dependence). Claims 1–3 remain training-level pending that. §5
>
> Terminology: **platoon = a convoy of vehicles (1 leader + followers); NOT a
> software "platform".** Throughout, "per-platoon" means per-convoy.
>
> On disk: **283 training runs** (139 base + 12 ablation #3 global-λ + 24 ablation #4
> fixed-weight + 96 scenario sweep + 12 deployment) under `1-ModifiedMADDPGwithTDec/model/`
> (study subfolders: `ScenarioSweep/`, `ep600_deploy/`, `Legacy_300ep/`); analysis reports
> under `results_remote/` + the study folders; five manuscript "claim figures" under
> `../Manuscript/figures/`.
> All `.mat` are tracked via **Git LFS** (a fresh clone needs `git lfs install` then
> `git lfs pull` to get real data, not pointers).
>
> **Eight settled findings (each verified against raw `.mat`):**
> 1. SOFT (network-average / soft-penalty AoI) hides a starved platoon: network-mean
>    violation ≈0.18 while the worst platoon sits 0.35–0.49 (≫ ε=0.10).
> 2. HARD per-platoon CMDP (cost critic + per-platoon λ) protects the worst platoon:
>    worst-platoon violation reduction soft→PID = **0.228 ± 0.094** (n=6, ep600).
> 3. The guarantee is **not free but cheap** on converged PID data: violation −47%,
>    mean AoI −19%, **transmit power +25%**, V2V demand ≈−1% (feasible n=30, ep600).
>    (NOTE: an earlier "+62% power / +74% V2V" figure came from the INTEGRAL-dual /
>    300-ep data and is SUPERSEDED — use the PID/ep600 numbers.)
> 4. PID-Lagrangian damps the integral dual's limit-cycle: worst-platoon violation
>    late-std 0.175→0.097, strongest on the genuinely cycling seeds (s3, s7);
>    limit-cycling is NOT universal across seeds.
> 5. There is **NO truly resource-limited platoon** in this 3-RB/5-platoon scenario.
>    The 300-ep "3/30 sacrificed" platoons were UNDER-TRAINING + integral-dual
>    artifacts: ep600 rescues 2 of 3, and the seed2 1000-ep test rescues the last
>    one (soft viol→0.079, PID λ comes off the cap 20→3.6). ⇒ the "infeasibility
>    frontier" is really a **trainability/dual-stability frontier**, and the
>    `--aoi_floor` safeguard is NOT needed here (and back-fires under PID).
> 6. **Per-platoon granularity is NECESSARY** (ablation #3, `--lam_scope`): replacing
>    per-platoon λ_j with a SINGLE global multiplier — driven by the network-mean
>    (global_mean) OR the worst platoon (global_max) — FAILS to protect the worst
>    platoon (pooled worst-platoon violation ≈0.33 for both, ≈ soft's 0.354, std ~0.34),
>    while per-platoon λ_j holds it at **0.126 ± 0.024**. global_max also burns ~2×
>    transmit power (18.9 vs 9.9 dBm) and STILL fails; the global arms lower the network
>    MEAN (~0.12) but abandon the worst platoon. per-platoon wins on 5/6 seeds (seed7
>    has no starved platoon, so granularity is moot). Backs the "per-platoon" title
>    claim. See `results_remote/RQ1_ABLATION3_GLOBAL_LAMBDA.md`,
>    `../Manuscript/figures/fig_claim5_per_platoon_necessity.png`,
>    `../Manuscript/data/per_platoon_necessity_table.md`.
> 7. **A FIXED-WEIGHT threshold penalty is NOT a substitute for the dual** (ablation #4,
>    `--aoi_pen_type indicator --aoi_pen_w w`, soft mode, NO dual): same 1{AoI>τ} signal
>    as the hard constraint but a FIXED reward weight. Swept w∈{2,5,10,20}, seeds 2-7,
>    ep600. NO single w protects the worst platoon at the dual's cost — the worst-CASE
>    seed stays ≥0.248 (best case, w=10) vs the DUAL's 0.165, and even w=10 leaves the
>    hard seeds s2/s3 at 0.20/0.25 (>ε) at +35% power (13.4 vs 9.9 dBm); cheap w≤5 leaves
>    s2 fully starved (1.0); the best w is seed-dependent (no universal weight). HONEST
>    nuance: w=10's *pooled-mean* worst (0.112) slightly beats the dual (0.126), but it is
>    dragged down by easy seeds, costs +35% power, has ~4× the std, and misses the hard
>    seeds — so frame the dual's win as worst-CASE + cost + no-per-scenario-tuning, NOT
>    raw average. ⇒ "constraint vs penalty" is real on the identical signal. See
>    `results_remote/RQ1_ABLATION4_FIXEDWEIGHT.md`, `../Manuscript/data/fixed_weight_penalty_table.md`.
> 8. **A genuine RESOURCE frontier exists at load ≈ 2 platoons/RB** (`ScenarioSweep/`:
>    n_RB×platoons grid, 4 arms, seeds 2–4, ep600). At load ≥2.5 ALL arms collapse with λ
>    pinned at the cap on every seed — a real resource wall (retires the residual
>    "only-trainability" hedge; motivates RQ2/RQ3 prioritization). In the feasible band
>    (load ≤1.67, well-trained seeds 3/4) the per-platoon dual holds the worst platoon at
>    0.11–0.14 with λ OFF the cap, while soft sits 0.26–0.35. CAVEATS (honest): seed2
>    pseudo-diverges at several feasible cells (under-training artifact, finding-5 family);
>    n=3 seeds; at low load the simpler arms match the dual (granularity only matters when
>    binding) — do NOT claim cross-load dominance. Evidence:
>    `model/ScenarioSweep/RQ1_SCENARIO_SWEEP.md` + the operator's seeds-{3,4} re-analysis.
>
> **Manuscript reporting lens:** lead with the WORST-served convoy, not the network mean —
> on canonical ep600 data the worst convoy's mean AoI improves **8.14→4.29 (−47%)**, p95
> 21.5→10.7; most dramatic seed2 convoy: 12.6→3.3, per-step peak 83→25. The diluted
> network-mean (5.4→4.4, −19%) under-sells the same result.
>
> **DEPLOYMENT EVALUATION (`ep600_deploy/`) — UNDER INVESTIGATION (σ-eval done; cause open):**
> claims 1–3 are TRAINING-level (recorded with exploration noise σ=0.3 while weights+λ still
> update). Frozen-deployment tests: (i) COLD synchronized boot (AoI=100; plain `*_test*.mat`)
> deadlocks the greedy deterministic policy — a boot-protocol artifact (the same convoys
> train at AoI≈4), kept as a documented caveat. (ii) WARM start (`*_test_warm*.mat`)
> removes the deadlock, BUT the frozen DETERMINISTIC policy loses the worst-platoon guarantee:
> pid worst 0.362±0.234 ≈ soft 0.379±0.185 (pairwise pid better only 4/6), NO run ≤ε; held-out
> worse (0.65–0.70). Mechanism hypothesis: the CMDP certified the STOCHASTIC behaviour policy
> μ+N(0,0.3) — exploration noise performs implicit coordination (RB symmetry-breaking);
> noise-off deploys a different, uncertified policy. (iii) σ-eval (DONE, cause OPEN): redeploy
> the certified STOCHASTIC policy μ+N(0,σ), σ∈{0,0.05,0.1,0.3}, eval-only WARM on the 12
> checkpoints — re-injecting the certification noise does **NOT** recover the worst-platoon
> guarantee (pooled eval-A pid 0.362→0.348 ≈ soft 0.379→0.327; gap soft−pid +0.228→−0.022;
> 0/192 configs ≤ε). **BUT the failure is seed-heterogeneous and concentrated in 1–2 marginal
> platoons, NOT a network collapse:** at σ=0.3, 4/6 pid seeds degrade only mildly (worst
> 0.19–0.24, **net-mean ≈ ε**) while 2/6 blow up (s2 0.69, s5 0.56) and drag the pool; the
> tipping platoon DIFFERS from the training-worst platoon (s2 pl4→pl0, s5 pl0→pl2), and **s2 is
> the documented under-trained seed (finding 5)** — i.e. a partial regression toward the
> claim-1 failure mode (mean fine, one platoon starved). **CAUSE NOT YET DISCRIMINATED:**
> under-training/residual-robustness (→ retrain s2/s5 longer, cf. finding 5) vs a genuine
> online-dual dependence (→ light online-dual at deployment). Until a discriminating run,
> state claims 1–3 as training-level only; **do NOT claim "online-only."** All σ-eval numbers
> locally re-verified from raw `.mat` (`results_remote/RQ1_DEPLOY_EVAL_NOISE.md`; verifier +
> σ-sweep fig + per-seed breakdown in `tmp_scripts/`).
>
> **Reduced/retired claims:** "infeasibility frontier" (→ trainability frontier);
> `--aoi_floor` safeguard (unneeded, harmful under PID); "PID beats integral on
> #pass" (CI overlap at n=10 — PID's real win is sacrifice-count + limit-cycle
> removal); the +62%/+74% cost numbers (superseded by PID/ep600).
>
> **Companion docs (read as needed):**
> - **method + code architecture** → [`ARCHITECTURE.md`](ARCHITECTURE.md)
> - **run / resume / commit on the remote machine** → [`REMOTE_RUNBOOK.md`](REMOTE_RUNBOOK.md)
> - **paper writing** (claims, figures, numbers) → `../Manuscript/README_FOR_WRITING.md`
> - **per-batch run history** (chronological, some early numbers superseded) →
>   the reports under `results_remote/` (§2).

---

## 0. One-paragraph orientation

This is the Parvini AoI-MARL platoon C-V2X codebase (`1-ModifiedMADDPGwithTDec` is the
active algorithm). It compares **two ways of handling per-platoon Age-of-Information**,
selectable with `--mode`: `soft` (baseline — AoI as a `−AoI/20` reward penalty, original
Parvini behaviour) vs `hard` (the RQ1 method — AoI as a per-platoon **CMDP constraint**
`P(AoI_j>τ)≤ε` via a per-platoon **cost critic** + **Lagrange multiplier λ_j** on a
two-timescale dual). Everything else (MARL algorithm, channel model, scenario,
hyper-parameters) is identical between modes, so any difference is caused by the AoI
handling alone. RQ1's point: the **hard** mode keeps **every** platoon near ε (protecting
the worst-served convoy) where **soft** lets the weakest convoy violate badly even though
the network average looks fine. The method, the exact code edits, and the full flag list
are in `ARCHITECTURE.md`; how to actually run it is in `REMOTE_RUNBOOK.md`.

---

## 1. Locked configuration (reference; never recalibrate)

τ=8, ε=0.10, λ_max=20, PID `kp=ki=1.0 kd=0.5`, η_λ=1.0 (integral arm), scenario
**5 platoons × 4 veh × 3 RB**, seeds **2–7**, canonical horizon **600 episodes**. The
headline `hard` policy uses the **PID-Lagrangian** dual. Every run writes the per-run
`.mat` set (`viol_rate`, `lambda`, `AoI`, `AoI_evolution`, `power`, `demand`, `V2I`,
`V2V`, `Jain`, `reward_t1/t2/cost/total`; since 2026-06-11 also `critic_loss_cost` +
`cost_force` = λ_j·mean Q^c, while `reward_global` is no longer written — older runs
differ accordingly). Runs with `--eval_episodes` additionally hold frozen-deployment
eval files `*_test*(_warm)(_holdout_s{seed}).mat` (see ARCHITECTURE.md §4/§5).

---

## 2. Experiment inventory — what is under `model/`

Run-dir naming: `marl_model_<mode>_seed<N>_<tag>`. `<mode>` = `soft` (AoI as −AoI/20
penalty) or `hard` (per-platoon CMDP). `<tag>` encodes (τ,ε) and variant:
`t{τ}e{100·ε}` (e.g. `t8e10`), optionally suffixed `_pid` (PID dual vs integral),
`_anneal` (σ-anneal — rejected), `_floor` (--aoi_floor — retired), `_ep600`/`_ep1000`
(horizon), `_glmean`/`_glmax` (ablation #3 single global λ, `--lam_scope`). No suffix on
a hard run = integral dual, 300 ep. soft tag is `_base` (raw −AoI/20) or `_qind_w{w}`
(ablation #4 fixed-weight 1{AoI>τ} penalty, `--aoi_pen_type indicator --aoi_pen_w`); the
scenario sweep adds `_rb{R}_pl{P}` (`--n_RB`/`--n_veh`). **Every run now lives in a study
subfolder of `model/`** (no loose runs in root): `Canonical_ep600/` (the 3-arm reference),
`Ablations_ep600/{global_lambda,fixed_weight}/` (#3/#4), `Feasibility_ep1000/` (seed2
1000-ep), `ScenarioSweep/` (resource frontier), `ep600_deploy/` (deployment eval),
`Legacy_300ep/` (retired 300-ep + `claim4_support/`). **Full map: `model/MANIFEST.md`.** A
run's folder is organizational ONLY — the analysis/figure scripts resolve a run by NAME
anywhere under `model/` (and new runs can target a folder with `--out_subdir`), so the
by-name references in the table/claim-map below stay valid regardless of folder.

| run-class (tag) | seeds | conditions | what it tests |
|---|---|---|---|
| `Legacy_300ep/claim4_support/ soft_seedN_base` | 2–11 | 300 ep, soft baseline | the 300ep headline / n=10 CI baseline (paired with the t8e10 runs there). **300ep — archived**; the LIVE baseline is `soft_*_base_ep600` |
| `Legacy_300ep/claim4_support/ hard_seedN_t8e10`, `_t8e10_pid` | 2–11 | 300 ep, integral vs PID | claim-4 limit-cycle data + n=10 CI headline. **300ep — archived; a 600ep support is planned** |
| `Legacy_300ep/ hard_seedN_t{10,12}e{10,15}(_pid)`, `_t8e15(_pid)` | 2–7 (t10/12e10 also 8–11) | 300 ep | **RETIRED** τ/ε phase grid, non-(8,10) cells (superseded by `ScenarioSweep/`). The (8,10) cell = the `t8e10` rows above, kept in root (claim-4/headline). |
| `Legacy_300ep/ hard_seedN_t8e10_anneal` | 2–7 | 300 ep, σ-anneal | **RETIRED** stability ablation (σ-anneal — rejected) |
| `Legacy_300ep/ hard_seedN_t8e10(_pid)_floor` | 2,3,4 | 300 ep, +floor | **RETIRED** feasibility safeguard (back-fires under PID) |
| `soft_seedN_base_ep600`, `hard_seedN_t8e10_ep600`, `hard_seedN_t8e10_pid_ep600` | 2–7 | **600 ep** | convergence re-run (three arms); **canonical converged data** for claims 1–3 |
| `soft/hard_seed2_..._ep1000` | 2 | **1000 ep** | seed2-pl2 infeasibility test (claim 5: under-trained, not infeasible) |
| `hard_seedN_t8e10_pid_ep600_glmean`, `..._glmax` | 2–7 | **600 ep**, single global λ | ablation #3 (claim 6): per-platoon vs global multiplier |
| `soft_seedN_qind_w{2,5,10,20}_ep600` | 2–7 | **600 ep**, fixed-weight 1{AoI>τ} penalty | ablation #4 (claim 7): fixed-weight penalty vs dual |
| `ScenarioSweep/ *_rb{2,3,4}_pl{4,5,6}` (4 arms) | 2,3,4 | **600 ep**, varies n_RB/platoons | resource-frontier sweep (self-contained; scripts + report inside the folder) |
| `ep600_deploy/ soft_seedN_base_ep600_deploy`, `hard_seedN_t8e10_pid_ep600_deploy` | 2–7 | 600 ep retrain (bitwise == canonical) + frozen-deployment eval (A in-dist `*_test*`, B held-out `*_holdout_s{12,13,14}`) | deployment-level test of claims 1–3. COLD boot (plain `*_test*`) = deadlock artifact; WARM (`*_test_warm*`, eval-only from checkpoints) = deterministic policy LOSES the guarantee (pid 0.362 ≈ soft 0.379, no run ≤ε); σ-eval (`*_test_warm_n{5,10,30}*`, certified stochastic policy μ+N(0,σ)) does NOT recover it (gap +0.228→−0.022, 0/192 ≤ε) but failure is seed-heterogeneous / 1–2 marginal platoons (4/6 seeds net-mean≈ε; s2/s5 catastrophic) — cause (under-training vs online-dual) under investigation, see header box |

**Which data backs which claim** (canonical = ep600 t8e10 three-arm, seeds 2–7):
- Claim 1 (soft hides starvation): `soft_*_base_ep600`.
- Claim 2 (protection) / Claim 3 (cost): `soft_*_base_ep600` vs `hard_*_t8e10_pid_ep600`.
- Claim 4 (PID vs limit-cycle): `Legacy_300ep/claim4_support/hard_*_t8e10` (integral) vs `..._t8e10_pid`, **300 ep** (archived; 600ep support planned).
- Claim 5 (no true infeasibility): the three `*_ep1000` seed2 runs (+ ep600 context).
- Claim 6 (per-platoon necessity): `hard_*_t8e10_pid_ep600` vs `..._glmean`/`..._glmax`,
  with `soft_*_base_ep600` for context.
- Claim 7 (fixed-weight ≠ dual): `soft_*_qind_w{2,5,10,20}_ep600` vs
  `hard_*_t8e10_pid_ep600`, with `soft_*_base_ep600` for context.

---

## 3. `results_remote/` — what each report proves

Six live reports in `results_remote/` (table below), each auto-generated by a detached
driver then committed; all numbers cross-checked against raw `.mat`. (Chronological batch
logs — early rows may report numbers later superseded; trust the findings box above + the
Manuscript canon.) Retired process reports moved to `model/Legacy_300ep/` (incl. the 300ep
headline `RQ1_REMOTE_REPORT.md` under `claim4_support/`); the scenario-sweep report is in
`model/ScenarioSweep/` (see note under the table).

| file | batch / condition | what it establishes |
|---|---|---|
| `RQ1_EP600_REPORT.md` | 600-ep re-run, three arms | under-training relief: sacrificed 3→1, gap 0.346→0.228 (still +) |
| `RQ1_SEED2_INFEAS_REPORT.md` | seed2 1000-ep | seed2-pl2 under-trained NOT infeasible → no true-infeasible platoon |
| `RQ1_ABLATION3_GLOBAL_LAMBDA.md` | per-platoon vs global λ, 6 seeds, ep600 | claim 6: a single global multiplier fails; per-platoon is necessary |
| `RQ1_ABLATION4_FIXEDWEIGHT.md` | fixed-weight penalty (w 2/5/10/20), ep600 | claim 7: no fixed weight matches the dual (worst-case seed ≥0.25 vs 0.165) |
| `RQ1_DEPLOY_EVAL_AB.md` | frozen DETERMINISTIC eval, COLD boot, 12 runs | the cold synchronized AoI=100 boot deadlocks the greedy policy (artifact: same convoys train at AoI≈4) |
| `RQ1_DEPLOY_EVAL_WARM.md` | frozen DETERMINISTIC eval, WARM start (eval-only from checkpoints) | deadlock removed, but deterministic deployment loses the guarantee (pid 0.362±0.234 ≈ soft; no run ≤ε) → stochastic-policy σ-eval (below) |
| `RQ1_DEPLOY_EVAL_NOISE.md` | frozen STOCHASTIC eval, WARM, σ∈{0,0.05,0.1,0.3} (eval-only, certified μ+N(0,σ)) | re-injecting the certification noise does NOT recover the worst-platoon guarantee (pid≈soft at every σ; gap +0.228→−0.022; 0/192 configs ≤ε) — but failure is seed-heterogeneous / 1–2 marginal platoons (4/6 seeds net-mean≈ε; s2/s5 catastrophic, s2 under-trained); cause (under-training vs online-dual) UNDER INVESTIGATION |

**Retired to `model/Legacy_300ep/`** (with their figs + scripts): `RQ1_STABILITY_REPORT.md`
(σ-anneal — rejected), `RQ1_PHASE_PID_REPORT.md` (τ/ε phase — superseded by
`ScenarioSweep/`), `RQ1_FLOOR_AND_CI_REPORT.md` (floor — retired); plus
`fig_phase_diagram(_pid).png`, `fig_stability_*.png`, `fig_(pid_)floor.png`. The 300ep
claim-4 / headline data (t8e10±pid n=10, `RQ1_REMOTE_REPORT.md`, fig_headline_violation /
lambda / cost_tradeoff / softsweep) is under `model/Legacy_300ep/claim4_support/` — a 600ep
support is planned.

Per-batch figures (`results_remote/fig_*.png`) are batch-specific; the five
manuscript-grade claim figures live in `../Manuscript/figures/` (`fig_claim1..5`).
Several remaining `results_remote/` figures are integral-era and RETIRED for the paper
(see `../Manuscript/README_FOR_WRITING.md`).

---

## 4. Independent re-verification protocol (for an auditing agent)

Goal: confirm Claims 1–4, 6 and 7 and that `../Manuscript/figures/fig_claim*.png` are
faithful — from the raw `.mat` directly, NOT by trusting the reports.

Setup: `git lfs install && git lfs pull` (else `.mat` are pointers). Use a Python with
scipy + numpy<1.24. Violation of a run = read `AoI_evolution.mat` (5×100×100 = platoon ×
last-100-ep × step) and compute `P(AoI>τ) = (AoI_evolution>8).mean(axis=(1,2))` → one
value per platoon (τ=8). Network-mean = mean over 5 platoons; worst = max over 5.

- **Claim 1** — `soft_*_base_ep600`: expect mean ≈0.18, worst 0.35–0.49 (≫ε). →
  `fig_claim1_average_hides.png`.
- **Claim 2** — pool 5 per-platoon violations × 6 seeds (30 values) for soft & PID; per-seed
  worst-platoon gap soft.max−pid.max ≈ **0.228 ± 0.094**. → `fig_claim2_protection.png`.
- **Claim 3** — soft vs PID (all 30 feasible) of violation / mean AoI (`AoI.mat[:,-100:].mean`)
  / power (`power.mat`.mean) / V2V demand (`demand.mat`.mean): ≈ −47% / −19% / +25% / ≈−1%.
  → `fig_claim3_cost.png`.
- **Claim 4** — **300-ep** `Legacy_300ep/claim4_support/hard_*_t8e10` vs `..._t8e10_pid`:
  worst platoon's per-episode `viol_rate.mat` last-100-ep std ≈ 0.175 (integral) → 0.097
  (PID), concentrated on s3,s7. → `fig_claim4_pid_stability.png` (300ep; 600ep support planned).
- **Claim 6** — `hard_*_t8e10_pid_ep600` vs `..._glmean`/`..._glmax`: worst =
  `viol_rate.mat[:,-100:].mean(axis=1).max()`, power = `power.mat.mean()`. Expect
  per-platoon worst ≈0.126±0.024 vs both global ≈0.33; global_max power ≈18.9 vs ≈9.9 dBm.
  Sanity: each global run's `lambda.mat` rows are identical across platoons (single shared
  λ). → `fig_claim5_per_platoon_necessity.png`.
- **Claim 7** — `soft_*_qind_w{2,5,10,20}_ep600` vs `hard_*_t8e10_pid_ep600`: worst and
  power as above; confirm `lambda.mat`==0 (soft mode). Expect worst-CASE seed (max over
  seeds) ≥0.248 for every fixed w vs 0.165 for the dual; w=10 costs ≈13.4 dBm vs 9.9 and
  still leaves s2/s3 >ε. (Do NOT over-read w=10's pooled-mean worst 0.112 — finding 7.)

Report any number that does NOT match the figure or the findings box — discrepancies are
the whole point. Honest negative findings (a claim weaker than stated) must be reported.

---

## 5. Next steps (priority order)

1. **σ-eval DONE, CAUSE OPEN — stochastic-policy deployment eval.** Eval-noise option added
   (`--eval_noise σ`, commit `9de5ab1`); eval-only σ∈{0,0.05,0.1,0.3} re-run of the 12
   `ep600_deploy` policies (`353cbbf`), locally re-verified from raw `.mat`. Re-injecting the
   certified σ=0.3 noise does NOT recover the worst-platoon guarantee (gap +0.228→−0.022;
   0/192 configs ≤ε), BUT the failure is seed-heterogeneous: 4/6 pid seeds degrade only
   mildly (worst 0.19–0.24, net-mean ≈ ε), only s2/s5 are catastrophic (on a shifting marginal
   platoon; s2 is the under-trained seed). **Discriminate the cause before any claim change:**
   (a) retrain s2/s5 longer (ep1000, cf. finding 5) + re-eval → tests under-training; (b) LIGHT
   online-dual at deployment (freeze policy, keep λ_j updating) → if it cheaply recovers the
   marginal platoons, this becomes a positive "online-dual deployment" contribution. Both need
   a remote batch; first deepen the local `.mat` analysis (AoI traces of the tipping platoons,
   end-of-training λ_j trajectories).
   **Mechanism caveat found while scoping this (Main.py ~L668):** the `--eval_only` σ-eval
   RESTARTS the scenario from the seed's INITIAL geometry (not the certified training-end
   geometry) and resets AoI=1 — two confounds. **IMPLEMENTED FIX → `Deploy_seamless_800ep`:**
   new flags `--seamless_tail N` / `--seamless_noise σ` / `--seamless_resume PKL` (Main.py)
   train 600 ep (== canonical, acceptance-gated) then continue the SAME env FROZEN for 200 ep
   at σ=0.3 with AoI NOT reset, and dump `Scenario_Reconstruct.pkl` (env+RNG+dual) so a later
   batch branches from the exact ep600 state (σ-sweep / online-dual) — resume verified
   bit-exact locally. Driver `results_remote/scripts/deploy_seamless_driver.ps1` +
   `analyze_seamless.py`. **This is now the FIRST discriminating run** (does the guarantee
   survive frozen deployment on the certified geometry?); run it on the remote before (a)/(b).
2. **claim-4 600-ep support** (planned retrain of the 300-ep integral-vs-PID comparison,
   currently archived in `Legacy_300ep/claim4_support/`). Any retrain now auto-produces
   the new `critic_loss_cost.mat`/`cost_force.mat` diagnostics (the cost-critic convergence
   curve rides along for free).
3. **Scenario-sweep firm-up** (optional): more seeds in the binding band (load 1.5–2.5)
   and/or seed2 at ep1000, to harden finding 8 beyond n=3 and quantify the divergence rate.
4. **Real 3GPP PRR as a second cost head** (delivery proxy → true multi-constraint CMDP) —
   the biggest methodological gap for a journal version.
5. **Power as an explicit constraint** (does the AoI guarantee survive a power cap? —
   would fully neutralize the "+25% power" trade-off critique).
6. **Optional:** fixed-bug ablation (un-detach the global critic); reuse the cost-critic +
   per-platoon-λ machinery for RQ2 (CAM/DENM classes) and RQ3.
