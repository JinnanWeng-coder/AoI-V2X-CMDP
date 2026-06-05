# CLAUDE.md — RQ1 per-platoon hard-constraint experiment (read this first)

> ## ✅ RQ1 EXPERIMENTAL CAMPAIGN COMPLETE (2026-06-04) — nothing in flight
>
> Terminology: **platoon = a convoy of vehicles (1 leader + followers); NOT a
> software "platform".** Throughout, "per-platoon" means per-convoy.
>
> The full RQ1 campaign is done and on disk: **151 training runs** (139 + the 12
> ablation #3 global-λ runs) under `1-ModifiedMADDPGwithTDec/model/`, seven analysis
> reports + figures under `results_remote/`, and five manuscript "claim figures" under
> `../Manuscript/figures/`. All `.mat` are tracked via **Git LFS** (a fresh clone
> needs `git lfs install` then `git lfs pull` to get real data, not pointers).
>
> **Six settled findings (each verified against raw `.mat`):**
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
>
> **Reduced/retired claims:** "infeasibility frontier" (→ trainability frontier);
> `--aoi_floor` safeguard (unneeded, harmful under PID); "PID beats integral on
> #pass" (CI overlap at n=10 — PID's real win is sacrifice-count + limit-cycle
> removal); the +62%/+74% cost numbers (superseded by PID/ep600).
>
> **Live-state companion:** [`results_remote/HANDOVER.md`](results_remote/HANDOVER.md)
> has the batch-by-batch run history and detached-driver mechanics. Nothing is in
> flight. Do NOT re-run any run whose `.out` already has the completion marker.
> The exact data→claim map and the independent re-verification protocol are in
> §9–§11 below.

> Design/implementation companion (line-level diff + rationale):
> `../RQ1_CMDP_IMPLEMENTATION.md`. The mechanism, base-version state, and "how to
> run / failure tree" are unchanged and kept in §0–§8 below for reference.

---

## 0. One-paragraph orientation

This is the Parvini AoI-MARL platoon C-V2X codebase (`1-ModifiedMADDPGwithTDec`
is the active algorithm). It has been extended to compare **two ways of
handling per-platoon Age-of-Information (AoI)**, selectable with a single
`--mode` flag:

- `--mode soft` — the **baseline**: AoI enters the reward as a soft penalty
  (`−AoI/20`). This is the original Parvini behaviour.
- `--mode hard` — the **proposed RQ1 method**: AoI is a per-platoon **CMDP
  constraint** `P(AoI_j > τ) ≤ ε`, enforced by a per-platoon **cost critic**
  and a per-platoon **Lagrange multiplier λ_j** updated by two-timescale dual
  ascent.

Everything else (MARL algorithm, channel model, scenario, hyper-parameters)
is identical between the two modes, so any difference in results is caused by
the AoI-handling change alone. The goal of RQ1 is to show that the **hard**
mode keeps **every** platoon near the target violation rate ε (protecting the
worst-served platoon), where the **soft** mode lets the weakest platoon
violate badly even though the network average looks fine.

---

## 1. Base version state (important context)

This tree is the **pre-gradient-fix** Parvini fork: it equals the clean
baseline plus a Jain reward term and logging. Concretely, compared with the
upstream original:

- `global_critic.py` is **identical to original → the actor-gradient bug is
  still present** (`actor_global_loss.clone().detach()`). The global critic
  (interference + Jain) therefore does **not** reach the actor. **This was
  left in place on purpose** — the RQ1 constraint is attached to the *local*
  actor update, which works regardless of that bug, so soft-vs-hard is a
  clean A/B. Do **not** "fix" it unless you are running a separate ablation.
- `Environment_Platoon.py` has `LAMBDA_JAIN`, `compute_jain_aoi`, and Jain in
  the global reward (inert at the actor because of the bug above).

---

## 2. What was changed (all edits tagged `[RQ1-CMDP]` in-source)

| file | change |
|---|---|
| `Classes/buffer.py` | replay now stores a per-platoon `reward_cost` |
| `Classes/Environment_Platoon.py` | `act_for_training` emits `cost_aoi = 1{AoI>τ}`; the soft penalty weight is now `aoi_penalty_coef` (0 in hard mode, 1/20 in soft); added `tau_aoi`, `eps_viol`, `constraint_mode` |
| `local_critic.py` | added `critic_cost` (+target) and `self.lam`; trains the cost critic by Bellman regression; actor objective is `−Q1−Q2+λ_j·Q_cost` in hard mode, original in soft mode |
| `global_critic.py` | `global_learn` threads `reward_cost` to each agent |
| `Main.py` | `argparse` config; per-episode dual update of `λ_j`; logs `viol_rate.mat` + `lambda.mat`; per-mode output folder |

**Mechanism in one line:** cost critic = "one more task critic" trained on the
AoI-violation indicator; the actor is pushed to minimise `λ_j · Q_cost_j`;
`λ_j` rises whenever platoon `j`'s episodic violation rate exceeds ε.
Two timescales: critics/actor update per learn-step; `λ_j` updates per episode.

---

## 3. How to run

```bash
cd 1-ModifiedMADDPGwithTDec

# headline comparison (run both; repeat seeds 3,4,5,6 for confidence intervals)
python Main.py --mode soft --episodes 500 --seed 2
python Main.py --mode hard --episodes 500 --seed 2

# quick end-to-end sanity check (≈seconds, NOT a result)
python Main.py --mode hard --smoke
```

Constraint knobs (defaults in parentheses): `--tau` AoI threshold τ in slots
(8) · `--eps` target violation prob. ε (0.10) · `--eta_lam` dual step (3.0) ·
`--lam_max` multiplier clip (20).

**Outputs** land in `1-ModifiedMADDPGwithTDec/model/marl_model_<mode>/`. The
two headline files (new) are:
- `viol_rate.mat` — per-platoon violation rate per episode `(n_platoon × n_episode)`
- `lambda.mat` — per-platoon multiplier per episode `(n_platoon × n_episode)`

plus the originals (`AoI.mat`, `Jain.mat`, `reward_*.mat`, `AoI_evolution.mat`, …).

> The `model/marl_model_soft/` and `marl_model_hard/` folders currently hold
> **3-episode smoke-test** data — overwrite them with full runs. The leftover
> `model/marl_model/` folder is unused now (label is always `_soft`/`_hard`).

---

## 4. Current progress (what is verified, what is not)

**Verified locally (smoke test, 3 ep × 20 steps, `aoi_cuda` env: numpy 1.23.5,
torch 2.11):**
- all modified files `py_compile` cleanly;
- `--mode soft` runs end-to-end, `λ` stays 0 (correct — no dual update);
- `--mode hard` runs end-to-end and the dual ascent behaves correctly — a
  platoon below ε keeps `λ=0`, the worst platoon accrues the largest `λ`
  (smoke: platoon-3 viol=1.0 → λ climbed 2.7→5.4→8.1), and both modes write
  `viol_rate.mat`/`lambda.mat`.

**NOT yet done (your job):** the actual 500-episode × ≥5-seed training that
produces the soft-vs-hard result. The smoke test only proves the wiring is
correct, not that the method converges.

---

## 5. Expected results (what success looks like)

After full training, compare the **last-100-episode mean** of `viol_rate.mat`
per platoon, soft vs hard:

- **soft (baseline):** at least one platoon (the weak/worst one) has a
  violation rate **well above ε**, while mean AoI across platoons looks
  acceptable — i.e. the average hides a starved platoon (this is the Fig-6.1
  story: under the buggy/soft setting one platoon can blow up while others are
  fine).
- **hard (proposed):** **every** platoon's violation rate is pulled to **≤ ε
  (or close)**, the worst-platoon AoI is bounded, and `lambda.mat` shows
  `λ_j` **concentrated on the bottleneck platoon and converging** (not
  diverging). Expect a modest cost in mean AoI / throughput — that is the
  honest price of the tail guarantee, and is acceptable.

The headline figure to produce is a **grouped bar chart of per-platoon
violation rate (soft vs hard)** with the ε line drawn — hard bars under ε,
soft weak-platoon bar far above. (A Tier-0 toy in
`X:/Codex-research/per_platoon_constraint_demo` already shows this shape;
this experiment reproduces it in the full simulator.)

---

## 6. If it FAILS — diagnosis decision tree

Work top to bottom; each row is "symptom → cause → fix".

1. **Crash with `np.int`/`np.bool` AttributeError** → numpy ≥ 1.24 on the
   remote machine (upstream code uses deprecated aliases) → either install
   `numpy<1.24`, or replace `np.int`→`int` and `np.bool`→`bool` in `Main.py`
   and `Classes/buffer.py`. (Local run used numpy 1.23.5, so this is purely a
   remote-environment issue.)

2. **Soft run shows ~0 violations for ALL platoons** → **τ is too loose; the
   constraint is not binding → you can prove nothing.** This is the single
   most likely "silent failure". Fix: **lower `--tau`** (try 6, then 5) until
   the soft run shows a clearly violating platoon. Calibrate τ on the SOFT run
   first, then use the same τ for hard. (Mean AoI under the trained policy is
   ≈5 slots, p90 ≈8–10, so τ=8 may be only weakly binding — expect to lower
   it.)

3. **Hard run: `λ` diverges to `lam_max` for everyone and AoI blows up** →
   either (a) the constraint is **infeasible** (τ too tight / ε too small for
   the resource pool) → loosen τ or raise ε; or (b) **dual step too large** →
   lower `--eta_lam` (try 1.0); or (c) the cost critic is buried in
   exploration noise → see item 6.

4. **Hard run: `λ` stays ≈0 and hard ≈ soft** → cost signal not biting →
   check (i) `agent.constraint_mode == 'hard'` actually propagated, (ii)
   `env.aoi_penalty_coef == 0` in hard mode, (iii) the soft run isn't already
   satisfying ε (i.e. τ too loose — item 2), (iv) raise `--eta_lam`.

5. **Hard improves the worst platoon but cost critic loss never drops** → the
   cost critic is not learning. The actor (and all local critics, incl. cost)
   only update every `update_actor_interval = 2` steps via `global_learn`;
   confirm `global_learn` is being called and `reward_cost` is non-zero in the
   buffer. Optionally give the cost critic its own learning rate.

6. **Works early, destabilises late** → this is the known Year-1 failure mode
   (actor exploration noise σ=0.3 dominates reward variance, ~78%). Fix:
   **anneal σ from 0.3→0.05** (in `Main.py`, `noise` is fixed at 0.3 and used
   in `Agent.choose_action`; make it decay with episode), and/or switch the
   dual from pure integral to **PID-Lagrangian** (the single `λ` update line
   in `Main.py` is the hook: add Kp/Ki/Kd terms).

If after items 2–6 the hard mode still cannot beat soft on worst-platoon
violation **in any binding-but-feasible τ/ε regime**, report that honestly —
it would mean the per-platoon constraint does not help in this simulator, which
is itself a valid (if disappointing) RQ1 finding.

---

## 7. If it SUCCEEDS — recommended next steps (in order)

1. **Statistics & figure.** Run ≥5 seeds for both modes; report mean + 95% CI
   of per-platoon violation rate and worst-platoon AoI; produce the
   soft-vs-hard per-platoon violation-rate bar chart (the RQ1 paper figure)
   and the `λ_j` convergence trace.
2. **τ/ε sweep → infeasibility frontier.** Sweep τ and ε to map where the
   constraint is feasible vs not. This phase diagram is a result in its own
   right and directly seeds RQ2.
3. **Add the PRR constraint (second cost head).** Currently only AoI is
   constrained. The repo's `V2V_success` is a delivery-completion proxy, **not
   3GPP PRR** — implement a proper per-platoon PRR first, then add a second
   `critic_cost`/`λ` exactly like the AoI one.
4. **Stability hardening.** Fold in σ-anneal and PID-Lagrangian (item 6 above)
   as standard, even if not strictly needed, for robustness across seeds.
5. **Optional ablation: fix the global-critic gradient bug** on a separate
   branch and re-run, to show the constraint result is independent of the
   global-critic path.
6. **Scale to RQ2/RQ3.** The same cost-critic + per-platoon-λ machinery
   extends to traffic-class-differentiated constraints (RQ2, CAM/DENM) and to
   PL-coordinated groupcast (RQ3). Reuse this exact pattern; do not rebuild.

---

## 8. Conventions & gotchas

- **Two output modes never share `.mat` folders** (`marl_model_soft` vs
  `marl_model_hard`), but they **do share** the network checkpoint dir
  `Classes/tmp/ddpg` — running hard after soft overwrites the saved weights.
  Irrelevant for the `.mat`-based results; namespace the checkpoint dir if you
  need to keep both sets of weights.
- **ε-soft, not literal hard.** This enforces an *expected* violation-rate
  constraint (holds in long-run average after convergence), not a per-slot
  guarantee. Describe results as "satisfied up to violation probability ε".
- **Don't change the scenario/hyper-params** when comparing soft vs hard — the
  whole point is that only the AoI-handling differs.
- **Seeds:** `--seed` controls all RNGs. Use the same seed set for soft and
  hard so the comparison is paired.
- Full design rationale and the exact line-level diff: `../RQ1_CMDP_IMPLEMENTATION.md`.

---

## 9. Experiment inventory — what is under `model/` and under what conditions

Run-dir naming: `marl_model_<mode>_seed<N>_<tag>`.
`<mode>` = `soft` (AoI as −AoI/20 reward penalty, baseline) or `hard` (per-platoon
CMDP). `<tag>` encodes (τ,ε) and variant: `t{τ}e{100·ε}` (e.g. `t8e10` = τ=8, ε=0.10),
optionally suffixed `_pid` (PID-Lagrangian dual instead of pure integral),
`_anneal` (σ exploration annealed 0.3→0.05), `_floor` (--aoi_floor 0.005),
`_ep600` / `_ep1000` (longer horizon), `_glmean` / `_glmax` (ablation #3: single
global λ driven by network-mean / worst violation, `--lam_scope`). No suffix on a hard run = integral dual,
300 ep. soft tag is always `_base`. **Locked config unless a tag says otherwise:**
episodes=300, τ=8, ε=0.10, η_λ=1.0, λ_max=20, PID kp=ki=1.0 kd=0.5, σ=0.3 const,
scenario 5 platoons × 4 veh × 3 RB. Every run dir holds 12 `.mat`
(AoI, AoI_evolution, viol_rate, lambda, power, demand, V2I, V2V, Jain, reward_t1/t2/global).

| run-class (tag) | seeds | conditions | which batch / what it tests |
|---|---|---|---|
| `soft_seedN_base` | 2–11 | 300 ep, soft baseline | headline + n=10 CI; the comparison baseline |
| `hard_seedN_t8e10` | 2–11 | 300 ep, integral dual, τ8/ε.10 | headline hard arm; n=10 CI; limit-cycle source |
| `hard_seedN_t8e10_pid` | 2–11 | 300 ep, PID dual | headline PID arm; n=10 CI |
| `hard_seedN_t{8,10,12}e{10,15}` | 2–7 | 300 ep, integral | τ/ε phase diagram (integral) |
| `hard_seedN_t{8,10,12}e{10,15}_pid` | 2–7 | 300 ep, PID | τ/ε phase diagram (PID) — frontier re-judged |
| `hard_seedN_t8e10_anneal` | 2–7 | 300 ep, σ-anneal | stability ablation arm B (σ-anneal — rejected) |
| `hard_seedN_t8e10_floor` | 2,3,4 | 300 ep, integral + floor | feasibility safeguard under integral |
| `hard_seedN_t8e10_pid_floor` | 2,3,4 | 300 ep, PID + floor | safeguard under PID (back-fires → retired) |
| `soft_seedN_base_ep600`, `hard_seedN_t8e10_ep600`, `hard_seedN_t8e10_pid_ep600` | 2–7 | **600 ep** | convergence re-run (three arms); the **canonical converged data** for claims 1–3 |
| `soft_seed2_base_ep1000`, `hard_seed2_t8e10_ep1000`, `hard_seed2_t8e10_pid_ep1000` | 2 | **1000 ep** | seed2-pl2 infeasibility test (claim 5: it's under-trained, not infeasible) |
| `hard_seedN_t8e10_pid_ep600_glmean`, `..._glmax` | 2–7 | **600 ep**, PID, single global λ | ablation #3 (claim 6): per-platoon vs global multiplier — `--lam_scope` |

(There is also a stray `marl_model_<...>` early-test dir or two; ignore anything
not matching the table.)

**Which data backs which claim (canonical = ep600 t8e10 three-arm, seeds 2–7):**
- Claim 1 (soft hides starvation): `soft_*_base_ep600`.
- Claim 2 (protection): `soft_*_base_ep600` vs `hard_*_t8e10_pid_ep600`.
- Claim 3 (cost): same pair as Claim 2.
- Claim 4 (PID vs limit-cycle): `hard_*_t8e10` (integral) vs `hard_*_t8e10_pid`, **300 ep**
  (limit-cycle is a 300-ep phenomenon; ep600 mostly converges it away).
- Claim 5 (no true infeasibility): the three `*_ep1000` seed2 runs (+ ep600 context).
- Claim 6 (per-platoon necessity): `hard_*_t8e10_pid_ep600` (per-platoon) vs the
  `..._glmean` / `..._glmax` global arms, with `soft_*_base_ep600` for context.

---

## 10. `results_remote/` — what each file proves

Seven reports, each auto-generated by a detached driver then committed; all numbers in
them were cross-checked against raw `.mat` by the supervising agent.

| file | batch / condition | what it establishes |
|---|---|---|
| `RQ1_REMOTE_REPORT.md` | headline + integral τ/ε phase + floor + multi-metric, 6 seeds, 300 ep | first end-to-end soft-vs-hard story (integral-era; some numbers later superseded) |
| `RQ1_STABILITY_REPORT.md` | σ-anneal vs PID vs baseline, t8e10, 6 seeds | PID dominates integral (sacrificed 3→0, λ-std down, cheaper); σ-anneal rejected |
| `RQ1_PHASE_PID_REPORT.md` | PID τ/ε phase diagram, 6 seeds | frontier under PID: SOFTENED not overturned (grid sacrifices integral 6 → PID 1) |
| `RQ1_FLOOR_AND_CI_REPORT.md` | PID+floor (n=3) and n=10 CI on 3 cells | floor back-fires under PID; n=10 — soft-vs-PID gap holds; PID-#pass advantage weakens (CI overlap) |
| `RQ1_EP600_REPORT.md` | 600-ep re-run, three arms | under-training relief: integral sacrificed 3→1, gap 0.346→0.228 (still +); 600 still insufficient for 2 platoons |
| `RQ1_SEED2_INFEAS_REPORT.md` | seed2 1000-ep, three arms | seed2-pl2 is under-trained NOT infeasible (PID λ off the cap; soft viol→0.079) → no true-infeasible platoon |
| `RQ1_ABLATION3_GLOBAL_LAMBDA.md` | per-platoon vs global λ (glmean/glmax), 6 seeds, ep600 | claim 6: a single global multiplier (mean- or max-driven) fails to protect the worst platoon; per-platoon is necessary (`--lam_scope`) |
| `HANDOVER.md` | — | live-state log: batch history, detached-driver mechanics, commit list |

Figures in `results_remote/` (`fig_*.png`) are the per-batch figures; the **five
manuscript-grade claim figures** live separately in `../Manuscript/figures/`
(`fig_claim1..5_*.png`, regenerable via `../Manuscript/make_claim_figures.py`;
fig_claim5 via `../Manuscript/make_claim5_figure.py`).

---

## 11. Independent re-verification protocol (for an auditing agent)

Goal: confirm Claims 1–4 and 6 and that `Manuscript/figures/fig_claim*.png` are
faithful — using the raw `.mat` directly, NOT by trusting the reports.

Setup: `git lfs install && git lfs pull` (else `.mat` are pointers). Use a Python
with scipy + numpy<1.24 + matplotlib. Violation of a run = read its
`AoI_evolution.mat` (shape 5×100×100 = platoon × last-100-ep × step) and compute
`P(AoI>τ) = (AoI_evolution > 8).mean(axis=(1,2))` → one value per platoon (τ=8).

Check each claim (canonical data: ep600 t8e10 three-arm, seeds 2–7 = 30 platoon-seed pairs):
- **Claim 1** — for each `soft_*_base_ep600`: network-mean violation = mean over 5
  platoons; worst = max over 5. Expect mean ≈0.18, worst 0.35–0.49 (worst ≫ ε). →
  reproduces `fig_claim1_average_hides.png` (grey=mean, red=worst, per seed).
- **Claim 2** — pool the 5 per-platoon violations of all 6 seeds into 30 values for
  soft and for PID; sort by soft. Expect soft fans out to ~0.49, PID compressed near
  ε. Per-seed worst-platoon gap = soft.max − pid.max; mean over 6 seeds ≈ **0.228 ±
  0.094** (t-interval). → reproduces `fig_claim2_protection.png`.
- **Claim 3** — keep the 30 pairs where PID violation < 0.5 (all 30 qualify); for
  soft and PID compute mean±CI of: violation (from AoI_evolution), mean AoI
  (`AoI.mat[:, -100:].mean`), power (`power.mat`.mean), remaining V2V demand
  (`demand.mat`.mean). Expect ≈ violation −47%, AoI −19%, power +25%, demand ≈−1%.
  → reproduces `fig_claim3_cost.png`. (The "feasible n=30, SAC=0.5" wording just
  means "no run was excluded as sacrificed".)
- **Claim 4** — use the **300-ep** `hard_*_t8e10` vs `hard_*_t8e10_pid`. For each,
  take the worst platoon's per-episode `viol_rate.mat` row; its last-100-ep std is
  the limit-cycle amplitude. Expect mean integral ≈0.175 vs PID ≈0.097, with the
  gap concentrated on seeds 3 and 7. → reproduces `fig_claim4_pid_stability.png`.
- **Claim 6** — for `hard_*_t8e10_pid_ep600` (per-platoon) vs `..._glmean` / `..._glmax`:
  worst-platoon final viol = `viol_rate.mat[:, -100:].mean(axis=1).max()`; mean power =
  `power.mat.mean()`. Expect per-platoon worst ≈0.126±0.024 vs both global ≈0.33 (≈soft),
  and global_max power ≈18.9 vs per-platoon ≈9.9 dBm. Sanity: each global run's
  `lambda.mat` rows are identical across platoons (a single shared λ). → reproduces
  `fig_claim5_per_platoon_necessity.png` (regen via `Manuscript/make_claim5_figure.py`).

Each claim figure is generated by `Manuscript/make_claim_figures.py`; re-running it
must reproduce the committed PNGs. Report any number that does NOT match the figure
or the §0 summary — discrepancies are the whole point of the audit. Honest negative
findings (a claim weaker than stated) must be reported, not smoothed over.
