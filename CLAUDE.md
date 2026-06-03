# CLAUDE.md — RQ1 per-platoon hard-constraint experiment (read this first)

> ## ⏯️ RESUME HERE FIRST (state as of 2026-06-03 ~19:10, written before a planned reboot)
>
> **An ep600 re-run is IN FLIGHT and will be killed by the reboot. To continue:**
> ```powershell
> cd D:\Jinnan\CMDP\AoI-V2X-CMDP ; git pull
> powershell -NoProfile -ExecutionPolicy Bypass -File D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_ep600.ps1
> ```
> That one command is **idempotent**: it skips the 6 finished runs (their `.out`
> markers + `.mat` survive on disk) and re-runs ONLY the 12 missing ones from ep 0,
> then auto-writes `results_remote/RQ1_EP600_REPORT.md` + `fig_ep600_convergence.png`.
> Poll `1-ModifiedMADDPGwithTDec/logs/ep600_driver.progress.log`; the host kills
> detached procs on idle, so re-run the same command whenever the runs go stale
> (no `python.exe`, `.out` LastWriteTime old). **Do NOT re-run any run whose `.out`
> already contains `simulation took this much time`.**
>
> **ep600 experiment** (t8e10, 600 ep, locked config otherwise unchanged — tau=8
> eps=0.10 eta_lam=1.0 lam_max=20, PID kp=1 ki=1 kd=0.5, sigma const 0.3): three
> arms × seeds {2-7} = 18 runs, NEW `_ep600` tags (300-ep runs untouched). WHY:
> three 300-ep runs (soft-s2-pl2, hard-int-s3-pl0, hard-int-s7-pl0) were
> under-trained — a cap-bound platoon still descending at ep300. State at reboot
> (updated 2026-06-03 ~20:00): **soft `_base_ep600` s2-7 = 6/6 DONE; `t8e10_ep600`
> (integral) s2-7 = 6/6 DONE; `t8e10_pid_ep600` = 0/6 (wave 3 was in flight at the
> reboot — `resume_ep600.ps1` reruns ONLY these 6 PID runs).** So 12/18 done on disk.
> After all 18 finish + the report is written, **commit locally** (see HANDOVER §4
> for the exact `git add`) and report the hash — **do NOT `git push`**.
>
> **CURRENT SINGLE SOURCE OF TRUTH FOR LIVE STATE:
> [`results_remote/HANDOVER.md`](results_remote/HANDOVER.md)** — read it next for the
> full batch history (stability, PID phase, floor+CI, ep600), all detached-run
> mechanics, every report, and the unpushed local commits. Do NOT re-run any run
> whose `.out` already has the completion marker.

> You are picking up an in-progress experiment. This file tells you **what was
> changed, what to run, what success looks like, and exactly what to do next
> whether it fails or succeeds.** A companion design log lives one level up at
> `../RQ1_CMDP_IMPLEMENTATION.md` (deeper rationale + line-level diff). Read
> this file fully before touching code.

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
