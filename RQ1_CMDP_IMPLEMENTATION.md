# RQ1 — per-platoon hard constraints on the Parvini codebase

This document records every decision and code change made to turn the
Parvini AoI-MARL codebase into a **soft-vs-hard** comparison for RQ1:

> reformulate per-platoon AoI as a **CMDP constraint**
> `P(AoI_j > τ) ≤ ε` enforced by a per-platoon cost critic and a
> per-platoon Lagrange multiplier `λ_j`, instead of a soft AoI reward
> penalty.

Working tree: `X:\Codex-research\RQ1-HardConstraints\AoI-V2X-backup-main\1-ModifiedMADDPGwithTDec`

---

## 1. Which base version, and why

The GitHub clone failed (network), so the code was supplied as the extracted
zip `AoI-V2X-backup-main` (no `.git`, so no history to roll back through —
the current tree is the base, which the task explicitly permits).

I diffed it against the clean baseline `X:/AoI-V2X-IEEE-TVT-2023-main-original`:

| file | state in the backup |
|---|---|
| `global_critic.py` | **identical to original → gradient bug present** (`actor_global_loss.clone().detach()` at line 125) |
| `local_critic.py` | identical to original |
| `buffer.py` | identical to original |
| `Main.py` | modified (TensorBoard + Jain logging) |
| `Environment_Platoon.py` | modified (`LAMBDA_JAIN`, `compute_jain_aoi`, Jain in global reward) |

So this backup is the **pre-gradient-fix** state (original + Jain reward +
logging), which is exactly the "gradient 没修复前的" base suggested. I chose
to **keep it as-is** rather than apply any fix, for one principled reason:

> **The per-platoon constraint is attached to the *local* actor update, not
> the global critic.** In `local_critic.py` the actor loss is
> `−Q_task1 − Q_task2 (+ constraint term)`, and that local path already
> back-propagates to the actor correctly in the original code. The global
> critic's detached-gradient bug only blocks the *interference/Jain* signal,
> which is orthogonal to the AoI constraint. Therefore the CMDP mechanism is
> testable **without** first fixing the global-critic bug — and keeping the
> bug in place makes the soft-vs-hard comparison a clean A/B (only the AoI
> handling changes).

---

## 2. The design (mapping the proposal onto this code)

CMDP objective per platoon `j`:
`max E[Σ γ^t r]  s.t.  E[Σ γ^t c_j] ≤ d_j`, with cost
`c_j(t) = 1{AoI_j(t) > τ}` (an AoI-violation indicator) and target
`E[c_j] ≤ ε`. Lagrangian primal: the actor minimises
`−Q_task1 − Q_task2 + λ_j · Q_cost_j`. Dual: `λ_j` rises by dual ascent when
platoon `j`'s episodic violation rate exceeds `ε`.

This reuses the codebase's existing **task-decomposed critic** pattern — a
cost critic is simply "one more task critic", trained on the cost signal the
same way `critic_task1/2` are trained on their rewards. Two timescales: the
actor/critics update every learn step (slot scale); the multipliers update
once per episode (CAM-frame scale), as argued in the annual review.

---

## 3. Exact code changes (all tagged `[RQ1-CMDP]` in-source)

**`Classes/buffer.py`** — carry the per-platoon cost through replay.
- added `reward_cost` memory `(mem_size, n_agents)`;
- `store_transition(... reward_cost ...)` and `sample_buffer` now include it.

**`Classes/Environment_Platoon.py`** — emit the cost and gate the soft penalty.
- `__init__`: added `constraint_mode`, `tau_aoi`, `eps_viol`,
  `aoi_penalty_coef` (set from `Main.py`).
- `act_for_training`: the soft AoI penalty `− platoon_AoI[i]/20` is now
  `− platoon_AoI[i] * self.aoi_penalty_coef` (so it can be switched off in
  hard mode); the method now also returns
  `cost_aoi = 1{platoon_AoI > tau_aoi}` (per platoon).
  Return tuple grew from 8 to 9 values (cost inserted after `global_reward`).

**`local_critic.py`** — the cost critic + the soft/hard actor objective.
- `__init__`: added `self.constraint_mode`, `self.lam`, and
  `critic_cost` + `target_critic_cost` (same shape as a task critic).
- `local_learn(... reward_cost ...)`: trains `critic_cost` by Bellman
  regression on the violation indicator; the actor objective is now
  - **soft**: `−Q_task1 − Q_task2 + 2·mean(global_loss)` (original; global
    term is detached/zero-gradient as before, AoI enters via the reward);
  - **hard**: `−Q_task1 − Q_task2 + λ_j · mean(Q_cost(s, π(s)))`.
- `update_network_parameters`: soft-updates the cost-critic target too.
- `save_models`/`load_models`: include the cost critic.

**`global_critic.py`** — thread the cost through to the agents.
- `global_learn(... reward_cost ...)`; passes `reward_cost[:, i]` into each
  agent's `local_learn`.

**`Main.py`** — configuration, dual loop, logging.
- `argparse`: `--mode {soft,hard}`, `--episodes`, `--seed`, `--tau`,
  `--eps`, `--eta_lam`, `--lam_max`, `--smoke`.
- configures `env.constraint_mode/tau_aoi/eps_viol`; sets
  `env.aoi_penalty_coef = 0` in hard mode (AoI handled only by the
  constraint) and `1/20` in soft mode.
- sets each `agent.constraint_mode` and `agent.lam = 0`.
- records the per-platoon cost, stores it in replay, passes it to
  `global_learn`.
- **two-timescale dual update** (per episode, hard mode only):
  `λ_j ← clip(λ_j + η·(viol_rate_j − ε), 0, λ_max)`.
- new headline outputs `viol_rate.mat` and `lambda.mat`
  (`n_platoon × n_episode`); results saved under a **per-mode** folder
  `model/marl_model_soft/` vs `model/marl_model_hard/` so the two runs do
  not overwrite each other.

No other files were touched. The MARL algorithm, channel model, scenario,
and hyper-parameters are unchanged — the **only** difference between the two
runs is how per-platoon AoI is handled (soft reward vs hard constraint).

---

## 4. How to run (remote machine)

```bash
cd AoI-V2X-backup-main/1-ModifiedMADDPGwithTDec
python Main.py --mode soft --episodes 500 --seed 2     # baseline
python Main.py --mode hard --episodes 500 --seed 2     # proposed
# repeat for seeds 3,4,5,6 for CIs
```
Key outputs per run (under `model/marl_model_<mode>/`):
`viol_rate.mat` (per-platoon violation rate per episode),
`lambda.mat` (per-platoon multiplier per episode), plus the original
`AoI.mat`, `Jain.mat`, `reward_*.mat`, etc.

Constraint knobs: `--tau` (AoI threshold τ in slots, default 8),
`--eps` (target violation prob. ε, default 0.10), `--eta_lam` (dual step,
default 3.0), `--lam_max` (multiplier clip, default 20).

---

## 5. Smoke test (done locally — not full training)

Environment: `C:/Users/67497/anaconda3/envs/aoi_cuda/python.exe`
(numpy 1.23.5, torch 2.11.0). `--smoke` = 3 episodes × 20 steps.

- `py_compile` on all six modified files: **OK**.
- `--mode soft --smoke`: runs end-to-end; `λ` stays `[0,0,0,0,0]` (no dual
  update in soft mode); `viol_rate.mat` (5×3) written. ✓
- `--mode hard --smoke`: runs end-to-end; dual ascent active and correct —

  | episode | per-platoon viol_rate | per-platoon λ |
  |---|---|---|
  | 0 | `[0.20, 0.05, 1.00, 1.00, 0.10]` | `[0.3, 0.0, 2.7, 2.7, 0.0]` |
  | 1 | `[0.90, 0.70, 1.00, 0.40, 0.00]` | `[2.7, 1.8, 5.4, 3.6, 0.0]` |
  | 2 | `[0.30, 0.35, 1.00, 0.40, 0.00]` | `[3.3, 2.55, 8.1, 4.5, 0.0]` |

  Exactly the intended behaviour: a platoon below ε (platoon 2 at 0.05) keeps
  `λ=0`; the worst platoon (platoon 3, viol=1.0) accrues the largest `λ`
  (8.1). The multiplier concentrates pressure on the bottleneck platoon —
  the per-platoon protection a single global weight cannot give.

  Note: at episode 0 the soft and hard runs show the *same* `viol_rate`
  (`[0.2,0.05,1,1,0.1]`), confirming the two configurations are identical
  except for the constraint mechanism that then diverges them.

This is a wiring/▶correctness smoke test only. It does **not** show
converged behaviour — the headline soft-vs-hard result (hard keeps all
platoons near ε while soft lets the weak platoon violate) requires the full
500-episode × ≥5-seed runs on the remote machine.

---

## 6. Honest caveats / things to watch in full training

1. **ε-soft, not literal hard.** This enforces an *expected* violation-rate
   constraint via Lagrangian relaxation; it holds in the long-run average
   after convergence, not on every slot. (Consistent with the review's
   "satisfied up to violation probability ε" framing.)
2. **Multiplier stability.** Five `λ_j` updated together can oscillate;
   `--eta_lam` and `--lam_max` are the knobs. Pure integral dual ascent is
   used here; if it chatters, switch to PID (Kp/Ki/Kd) — the hook is the
   single `λ` update line in `Main.py`.
3. **σ exploration noise.** The Year-1 finding (σ=0.3 ≈ 78 % of reward
   variance) still applies: the cost critic trains on the same noisy
   trajectories, so a σ-anneal schedule is the recommended precondition
   before reading too much into the hard-mode curves.
4. **Gradient bug retained on purpose.** The global-critic interference/Jain
   signal still does not reach the actor; this is fine for the AoI-constraint
   A/B but means network-utility shaping is inert. Fixing it is a separate
   axis (a later branch) and is *not* required for the RQ1 soft-vs-hard story.
5. **Checkpoints share `Classes/tmp/ddpg`.** The `.mat` results are per-mode
   (separate folders), but network checkpoints use the same agent labels, so
   running hard after soft overwrites the saved weights. Irrelevant for the
   `.mat`-based results; namespace the checkpoint dir if you need both.

---

## 7. File inventory

```
RQ1-HardConstraints/
  RQ1_CMDP_IMPLEMENTATION.md         <- this document
  AoI-V2X-backup-main/               <- the codebase (edited in place)
    1-ModifiedMADDPGwithTDec/
      Main.py                  [RQ1-CMDP] argparse, dual loop, viol/lambda logging
      local_critic.py          [RQ1-CMDP] cost critic + soft/hard actor objective
      global_critic.py         [RQ1-CMDP] threads reward_cost through
      Classes/
        buffer.py              [RQ1-CMDP] stores reward_cost
        Environment_Platoon.py [RQ1-CMDP] emits cost, gates soft penalty
        networks.py            (unchanged; CriticNetwork reused for the cost critic)
      model/
        marl_model_soft/       soft-mode .mat outputs (incl. viol_rate, lambda)
        marl_model_hard/       hard-mode .mat outputs (incl. viol_rate, lambda)
```
