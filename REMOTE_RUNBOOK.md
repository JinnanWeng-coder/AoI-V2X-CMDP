# REMOTE RUNBOOK — running RQ1 training on the remote machine

> **For the remote machine only** (`D:\Jinnan\CMDP\AoI-V2X-CMDP`). This is the *how to
> run / resume / commit* doc. For *what the experiment is and what's been found* read
> [`CLAUDE.md`](CLAUDE.md) first; for the *method and code* read
> [`ARCHITECTURE.md`](ARCHITECTURE.md). Replaces the old `results_remote/HANDOVER.md`.

Training-level campaign **complete** (283 runs on disk, incl. `model/ScenarioSweep/` and
`model/ep600_deploy/`; see CLAUDE.md for the findings ledger). Current phase:
**frozen-deployment evaluation** — the next batch is the stochastic-policy eval
(eval-only, no retraining). This runbook is the reusable procedure for any batch.

---

## 0. Golden rules (do not break)

- **Stay inside `D:\Jinnan\CMDP\AoI-V2X-CMDP`.** Other people's files live elsewhere on
  this shared machine — never touch them.
- **Never `git push` from here.** This machine has no TTY for credentials (push fails on
  `wincredman`, exit 128). **Commit locally, report the hash, the human pushes.**
- **Never recalibrate the locked config; never drop a seed.** Locked: τ=8, ε=0.10,
  λ_max=20, PID `kp=ki=1.0 kd=0.5`, η_λ=1.0, scenario 5 platoons × 4 veh × 3 RB,
  seeds 2–7, canonical horizon 600 ep.
- **Do not "fix" the global-critic gradient bug** — it is retained on purpose
  (ARCHITECTURE.md §2.1).
- **Idempotent:** never re-run a run whose `.out` already contains the marker
  `simulation took this much time`.
- Scope every commit; **never `git add -A`** (it would stage `.claude/`, checkpoints,
  TB events, logs).

---

## 1. Environment

`./.venv` (created with `--system-site-packages` over the shared `SimuV2X` conda
torch+CUDA). numpy 2.x `np.int`/`np.bool` deprecations are already patched in-tree.
Throughput ≈16 s/episode at 6× parallel when the GPU is free (slower under contention).

Run from `1-ModifiedMADDPGwithTDec/`. A run is **done** when its `.out` log under
`logs/` contains `simulation took this much time`.

---

## 2. How to run a batch

One run:
```
cd D:\Jinnan\CMDP\AoI-V2X-CMDP\1-ModifiedMADDPGwithTDec
python Main.py --mode hard --tau 8 --eps 0.10 --dual pid --kp 1.0 --ki 1.0 --kd 0.5 \
    --episodes 600 --seed <S> --out_tag t8e10_pid_ep600
```
- Run-dir = `model/marl_model_<mode>_seed<S>_<out_tag>`. Choose `--out_tag` so a new
  batch never overwrites existing runs. Full flag list: ARCHITECTURE.md §4.
- For a new ablation, change ONLY the one flag under test (e.g. `--lam_scope`,
  `--aoi_pen_type indicator --aoi_pen_w`) and the `--out_tag` suffix; keep everything
  else byte-identical to the matching existing arm so it stays a single-variable change.
- Smoke first (seconds, not a result): `python Main.py --mode hard --smoke`.

### 2.1 Frozen-deployment eval / eval-only (no retraining)

For any run whose per-run checkpoints still exist (`Classes/tmp/ddpg_<name>/`,
actor_0–4 files present):
```
$env:RQ1_CKPT_SUBDIR='tmp/ddpg_<that run's subdir>'
python Main.py --mode <soft|hard> --tau 8 [--eps 0.10 --dual pid] --seed <s> \
    --eval_only --eval_episodes 100 --eval_warmup 5 --eval_holdout_seeds 12,13,14 \
    --out_subdir ep600_deploy --out_tag <same tag as the run>
```
Minutes per run. Writes `*_test_warm*.mat` into the existing run dir (warm start is the
default; `--eval_start cold` reproduces the legacy cold-boot `*_test*.mat` names). The
eval phase is fully frozen: noise=0 (unless a future eval-noise flag is used), no
learning, no dual update, no buffer writes. NEVER delete or overwrite an existing
`*_test*` file of the other start mode.

---

## 3. Detached-run mechanics (tmux/screen unavailable)

Each batch is driven by a hidden, orphaned `Start-Process` PowerShell driver under
`results_remote/scripts/` that survives SSH/agent disconnect. Every driver:
- processes a spec list in **waves of ≤6**;
- gives each run its own checkpoint dir `RQ1_CKPT_SUBDIR=tmp/ddpg_<name>` and `.out` log
  under `logs/`;
- blocks on the completion marker, is **idempotent** (skips finished runs), and
  **self-finalizes** (runs its analysis → writes the report + figure, no git) guarded by
  a `*.finalized` sentinel;
- has a one-command `resume_*.ps1` for restart after an idle-kill.

Scripts live in `results_remote/scripts/` (drivers, `resume_*.ps1`, `analyze_*.py`).
Shared loader `analyze_remote.py`: `metrics()` recomputes last-100-ep per-platoon
violation at a given τ from `AoI_evolution.mat`; `AoI.mat` is the per-episode trajectory
source.

> Caveat: a driver's per-wave wait has a 600-min timeout; if a wave is resumed late and
> exceeds it the driver may exit before finishing and skip its self-finalize. In that
> case run the batch's `analyze_*.py` manually (from `results_remote/`, with the
> `../.venv` python) once all `.out` markers exist.

Resume an interrupted batch:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\scripts\resume_<batch>.ps1
```

---

## 4. Commit a finished batch (local only — human pushes)

```
cd D:\Jinnan\CMDP\AoI-V2X-CMDP
# stage ONLY this batch's new run dirs + its report/figure/scripts (never -A):
git add 1-ModifiedMADDPGwithTDec/model/marl_model_<...this batch...> ^
        results_remote/<REPORT>.md results_remote/scripts/<batch scripts>
git status --short        # verify ONLY intended files (no .claude/, checkpoints, logs, TB)
git commit -m "RQ1 <batch>: <N> runs + report"
# git push   <-- HUMAN ONLY (no TTY for creds here)
```
`.mat` are Git-LFS pointers — confirm with `git show :<path>/AoI.mat` (should print
`version https://git-lfs...`). `.png` under `model/` is gitignored; reports/figures
under `results_remote/` are tracked normally. Report the commit hash; the human runs
`git push origin main` (and `git lfs push origin main` if LFS objects didn't auto-upload).

---

## 5. Report back (to the operator)

(1) repo status + commit hash; (2) a compact per-run metrics table (final-window
worst-platoon violation, network-mean violation, mean power); (3) any sanity check the
batch needs (e.g. `lambda.mat`==0 for soft-mode arms; λ_j identical across platoons for
global-λ arms). **Do not draw conclusions** — the operator cross-checks every number
against the raw `.mat`.

---

## 6. Troubleshooting

| symptom | cause → fix |
|---|---|
| `np.int`/`np.bool` AttributeError | numpy ≥1.24 → use `numpy<1.24`, or the in-tree patch is already applied; check the venv. |
| soft run shows ~0 violations for ALL platoons | τ too loose, constraint not binding → lower `--tau` until the soft run shows a clearly violating platoon (calibrate on soft first). |
| hard run: `λ` pins at `lam_max` for everyone, AoI blows up | (a) τ too tight / ε too small → loosen; (b) dual step too large → lower `--eta_lam`; (c) cost critic buried in noise. |
| hard run: `λ` stays ≈0 and hard ≈ soft | cost signal not biting → check `agent.constraint_mode=='hard'` propagated, `env.aoi_penalty_coef==0` in hard mode, and that the soft run isn't already meeting ε (τ too loose). |
| run killed mid-wave | re-run `resume_<batch>.ps1`; it skips finished `.out` markers and reruns only the in-flight wave. |
