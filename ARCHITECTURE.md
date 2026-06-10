# ARCHITECTURE & METHOD — RQ1 per-platoon AoI constraint

> What this file is: the **method** (the CMDP formulation) and the **code
> architecture** (how that method maps onto the Parvini codebase, and the exact
> edits). Audience: an agent writing the paper's Method section, or anyone reading
> the code. **Current experiment status, findings and the data→claim map live in
> [`CLAUDE.md`](CLAUDE.md); how to run/resume on the remote machine lives in
> [`REMOTE_RUNBOOK.md`](REMOTE_RUNBOOK.md).** Replaces the old
> `RQ1_CMDP_IMPLEMENTATION.md`.

Active algorithm: `1-ModifiedMADDPGwithTDec/` (the other upstream variants are not
used by RQ1). Local tree: `X:\Codex-research\RQ1-HardConstraints\AoI-V2X-CMDP`;
remote tree: `D:\Jinnan\CMDP\AoI-V2X-CMDP`. Upstream baseline for the diff:
`X:\AoI-V2X-IEEE-TVT-2023-main-original` (Parvini et al.).

---

## 1. Method — AoI as a per-platoon CMDP constraint

The baseline (`--mode soft`) puts Age-of-Information into the **reward** as a soft
penalty `−AoI_j/20` (Parvini/Qu style). The proposed method (`--mode hard`) instead
makes per-platoon AoI a **constraint**:

```
per platoon j:   max  E[ Σ γ^t r_t ]   s.t.   E[ Σ γ^t c_j(t) ] ≤ d_j
cost             c_j(t) = 1{ AoI_j(t) > τ }        (an AoI-violation indicator)
target           E[c_j] ≤ ε                        (a chance constraint on the AoI tail)
```

Lagrangian relaxation gives a per-platoon multiplier `λ_j`. The actor minimises the
**primal** objective `−Q¹_j − Q²_j + λ_j · Q^c_j`; the multiplier is raised by **dual
ascent** whenever platoon `j`'s episodic violation rate exceeds ε. This is a
*price→level* reframing: AoI moves from a fixed-weight reward term into a constraint
whose price (`λ_j`) is *solved for*, per platoon, until the violation level ε is met.

**Two timescales.** Actor + critics update every learn step (slot scale); each `λ_j`
updates once per episode (CAM-frame scale).

```
λ_j ← clip( λ_j + η·(viol_rate_j − ε), 0, λ_max )          # integral dual
```

The headline policy uses a **PID-Lagrangian** dual (Stooke 2020) on the error
`e = viol_rate_j − ε`, which damps the integral dual's limit-cycle:

```
I_j  ← clip( I_j + ki·e , 0, λ_max )
λ_j  = clip( kp·e + I_j + kd·(e − e_prev) , 0, λ_max )      # kp=kd=0,ki=η ⇒ integral
```

---

## 2. Architecture — how the method maps onto the code

The codebase already uses a **task-decomposed critic** pattern (per agent: an actor +
two task critics `critic_task1` (V2V/power) and `critic_task2` (V2I+AoI), plus a global
TD3 twin critic). The constraint is added with **minimal surgery**:

- **Cost critic = "one more task critic".** Each agent gets a third critic
  `critic_cost` (+ `target_critic_cost`), identical in shape to a task critic
  (`CriticNetwork` reused), trained by Bellman regression on the cost signal
  `reward_cost = 1{AoI_j>τ}` exactly as the task critics are trained on their rewards.
- **Soft/hard actor-loss switch.** In `local_critic.local_learn` the actor objective
  branches on `constraint_mode`:
  - `soft`: `−Q¹ − Q² + 2·mean(global_loss)` (original; the global term is the
    retained detached/zero-gradient add — AoI enters via the reward penalty);
  - `hard`: `−Q¹ − Q² + λ_j · mean(Q^c(s, π(s)))`.
- **Per-platoon multiplier.** Each agent owns `self.lam`; `Main.py` updates the vector
  `λ` once per episode (integral or PID).
- **Two-timescale loop** lives in `Main.py`'s episode loop (slow `λ` update) vs the
  per-step `learn` (fast critics/actor).

### 2.1 Base-version state — the retained global-critic bug (intentional)
This tree is the **pre-gradient-fix** Parvini fork (baseline + a Jain reward term +
logging). `global_critic.py` is **identical to the upstream original**, so the
`actor_global_loss.clone().detach()` makes the global critic's interference/Jain signal
**not reach the actor**. This is **left in place on purpose**: the RQ1 constraint
attaches to the *local* actor path (`−Q¹−Q²+λ·Q^c`), which back-propagates correctly
regardless of the global-critic bug. Keeping the bug makes soft-vs-hard a clean A/B
where **only the AoI handling differs**. Do **not** "fix" it except as a deliberate,
separate ablation.

---

## 3. Exact code changes (every edit tagged `[RQ1-CMDP]` in-source)

| file | change |
|---|---|
| `Classes/buffer.py` | replay stores a parallel per-platoon `reward_cost` `(mem_size, n_agents)`; `store_transition`/`sample_buffer` carry it. |
| `Classes/Environment_Platoon.py` | `__init__` adds `constraint_mode`, `tau_aoi`, `eps_viol`, `aoi_penalty_coef`, and (#4) `aoi_pen_type`/`aoi_pen_w`. `act_for_training` emits `cost_aoi = 1{platoon_AoI>tau_aoi}` (returned after `global_reward`) and applies the AoI reward penalty by shape: `raw` = `−AoI·aoi_penalty_coef` (original), `indicator` = `−aoi_pen_w·1{AoI>τ}` (#4). |
| `local_critic.py` | adds `critic_cost` + `target_critic_cost` and `self.lam`/`self.constraint_mode`; `local_learn` trains the cost critic by Bellman regression on `reward_cost`, then the actor objective switches soft/hard (see §2). `update_network_parameters`, `save_models`, `load_models` include the cost critic. |
| `global_critic.py` | `global_learn` threads `reward_cost[:, i]` into each agent's `local_learn`. (The detached global-gradient bug is untouched — §2.1.) |
| `Main.py` | argparse (§4); per-episode dual update of `λ` with the `--lam_scope` branch (#3) and integral/PID (`--dual`); logs `viol_rate.mat` + `lambda.mat`; per-run output folder via `--out_tag`. |

`Classes/networks.py` is unchanged — `CriticNetwork` is reused for the cost critic.
The MARL algorithm, channel model, scenario and hyper-parameters are otherwise
identical between modes, so any difference in results is from the AoI handling alone.

---

## 4. Flag reference (current `Main.py` argparse)

| flag | default | meaning |
|---|---|---|
| `--mode {soft,hard}` | soft | soft = `−AoI/20` reward penalty; hard = per-platoon CMDP |
| `--episodes` | 500 | training episodes (canonical campaign uses 600) |
| `--seed` | 2 | all RNGs; pair seeds across arms |
| `--tau` | 8.0 | AoI threshold τ (slots); violation if AoI>τ |
| `--eps` | 0.10 | target violation probability ε |
| `--eta_lam` | 3.0 | integral dual step η (canonical uses 1.0) |
| `--lam_max` | 20 | multiplier clip |
| `--dual {integral,pid}` | integral | dual rule; **headline uses pid** |
| `--kp / --ki / --kd` | 1.0/1.0/0.5 | PID-Lagrangian gains (kp=kd=0,ki=η ⇒ integral) |
| `--sigma_anneal` (+`--sigma_start` 0.3 / `--sigma_end` 0.05) | off | anneal actor noise (tested, **rejected** — see CLAUDE.md) |
| `--aoi_floor` | 0.0 | hard-mode soft-penalty floor (tested, **retired** — back-fires under PID) |
| `--lam_scope {per_platoon,global_mean,global_max}` | per_platoon | **ablation #3**: per-platoon λ_j vs a single global multiplier |
| `--aoi_pen_type {raw,indicator}` (+`--aoi_pen_w` 5.0) | raw | **ablation #4**: raw vs fixed-weight threshold penalty (use with `--mode soft`) |
| `--out_tag` | "" | suffix for the run's output folder (run isolation) |
| `--out_subdir` | "" | optional subfolder under `model/` for all outputs (e.g. `ep600_deploy`) |
| `--eval_episodes` (+`--eval_warmup` 5) | 0 | **frozen-deployment eval**: after training (or with `--eval_only`), run N deterministic episodes — noise=0, no learning, no dual, no buffer |
| `--eval_holdout_seeds` | "" | comma-separated held-out seeds → Experiment B (fresh `new_random_game` per seed) |
| `--eval_start {warm,cold}` | warm | eval initial AoI: warm=1 slot (steady-state; files `*_test_warm*.mat`), cold=100 (legacy cold-boot, plain `*_test*.mat` — deadlocks the greedy policy; kept as the documented caveat) |
| `--eval_only` | off | skip training; load this run's checkpoints (env var `RQ1_CKPT_SUBDIR`) and run only the eval |
| `--smoke` | off | tiny end-to-end wiring test (≈seconds; NOT a result) |

**Locked config for the campaign (do NOT recalibrate):** τ=8, ε=0.10, λ_max=20,
PID `kp=ki=1.0 kd=0.5`, η_λ=1.0 (integral arm), scenario 5 platoons × 4 veh × 3 RB,
canonical horizon **600 episodes**, seeds 2–7.

---

## 5. Outputs (per run, under `1-ModifiedMADDPGwithTDec/model/<run-dir>/`)

Training `.mat` per run (Git-LFS tracked): `viol_rate.mat` and `lambda.mat`
(`n_platoon × n_episode`, the RQ1 headline outputs); `AoI.mat`, `Jain.mat`,
`reward_t1/t2/cost/total.mat` (per-episode); `AoI_evolution.mat`
(`n_platoon × last-100-ep × step`), `power.mat`, `demand.mat`, `V2I.mat`, `V2V.mat`
(per-step, rolling last 100 ep); plus two cost-critic diagnostics:
`critic_loss_cost.mat` (per-episode Bellman MSE of Q^c — is the cost critic converging?)
and `cost_force.mat` (per-episode `λ_j·mean Q^c(s,π(s))` — the constraint force on the
actor). `reward_global.mat` is **no longer written** (inert at the actor due to the
retained detached global critic); runs recorded before 2026-06-11 still contain it and
lack the two diagnostics. With `--eval_episodes`, the frozen-deployment eval adds
`viol_rate_test*/AoI_evolution_test*/power_test*` (`_warm` suffix for the warm start,
`_holdout_s{seed}` for Experiment B). Run-dir naming and the full inventory are in
`CLAUDE.md` §2.

---

## 6. Pointers
- **Current findings / what each run proves / audit protocol** → `CLAUDE.md`.
- **Run & resume on the remote machine** → `REMOTE_RUNBOOK.md`.
- **Paper claims / figures / numbers to write** → `../Manuscript/README_FOR_WRITING.md`.
