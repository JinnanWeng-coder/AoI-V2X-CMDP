# RQ1 HANDOVER — single source of truth for the next session

> **Fresh agent: read THIS, then `CLAUDE.md` (repo root), then
> `results_remote/RQ1_STABILITY_REPORT.md`. Check disk state before acting.
> Do NOT re-run any run whose `.out` already contains the completion marker
> `simulation took this much time`.** Everything stays inside
> `D:\Jinnan\CMDP\AoI-V2X-CMDP` (shared machine).

Last updated by the agent at the start of the stability runs (PID wave in flight).

---

## 1. Project state — three experiment batches

The codebase (`1-ModifiedMADDPGwithTDec`) compares per-platoon AoI handling:
`--mode soft` (AoI as `-AoI/20` reward penalty, baseline) vs `--mode hard`
(per-platoon CMDP `P(AoI_j>tau)<=eps` via a cost critic + per-platoon Lagrange
multiplier `lambda_j`, two-timescale dual). The global-critic gradient bug is
retained on purpose (constraint attaches to the local actor) so soft-vs-hard is
a clean A/B. See `RQ1_CMDP_IMPLEMENTATION.md` for the code change.

| batch | status | what it shows |
|---|---|---|
| **(1) 6-seed headline** (soft vs hard @ tau8 eps10, seeds 2-7) | **DONE** | Where feasible, hard drives per-platoon violation **0.197->0.100** (to the eps target) at ~flat AoI; cost ~1.6x Tx power, ~1.7x remaining V2V demand; 3/30 structurally-infeasible platoons flagged via `lambda->lam_max`. |
| **(2) tau/eps phase diagram** (hard, taus {8,10,12} x eps {0.10,0.15}, 6 seeds/cell) + `--aoi_floor` safeguard (seeds 2-4) | **DONE** | Loosening tau/eps reduces but does **not** buy strict feasibility (no off-floor cell averages >=4.5/5 pass at n=6). `--aoi_floor 0.005` bounds an unservable platoon (AoI 90->17) without harming feasible ones. |
| **(3) stability study** = sigma-anneal arm + PID-Lagrangian arm | **RUNNING** (anneal done, PID in flight) | Tests two residual failure modes: (a) per-seed RL variance leaves a feasible platoon a hair over eps -> **sigma-anneal**; (b) dual limit-cycles -> **PID-Lagrangian**. Clean ablation, one knob at a time. Result lands in `RQ1_STABILITY_REPORT.md`. |

Full results of (1)+(2): `results_remote/RQ1_REMOTE_REPORT.md`.

**45 archived runs** (all 300 ep): soft s{2-7}; hard `t8e10` s{2-7}; hard
{`t8e15`,`t10e10`,`t10e15`,`t12e10`,`t12e15`} s{2-7}; hard `t8e10_floor` s{2,3,4}.
All `.mat` are tracked via **Git LFS** (`.gitattributes`:
`1-ModifiedMADDPGwithTDec/model/**/*.mat`). Tar fallback:
`results_remote/raw/all_runs_mat.tar.gz` + `MANIFEST.txt`.

---

## 2. Stability study mechanics (batch 3)

**Code (Main.py, tagged `[RQ1-CMDP]`, both default = existing behaviour):**
- `--sigma_anneal` — linearly anneal actor noise `--sigma_start 0.3 -> --sigma_end 0.05`
  over training. Default off => noise const 0.3.
- `--dual {integral,pid}` with `--kp --ki --kd` — `integral` (default) is the
  EXACT current pure-integral dual (kept byte-for-byte; verified it reproduces
  the documented smoke lambda trace `ep2=[3.3,2.55,8.1,4.5,0]`). `pid` is
  PID-Lagrangian (Stooke 2020) on `e=(viol_rate_j-eps)`, same `[0,lam_max]` clip;
  with `kp=kd=0, ki=eta_lam` it reduces to integral.

**Locked config (do NOT recalibrate): `tau=8 eps=0.10 eta_lam=1.0 lam_max=20
episodes=300 aoi_floor=0.0`, seeds {2,3,4,5,6,7}, paired.**

**Three arms** (only the stability knob differs):
- **A baseline** — sigma const, integral = the EXISTING hard `t8e10` s{2-7} (REUSE, do not rerun).
- **B anneal** — `--sigma_anneal`, integral. Tag **`t8e10_anneal`**, 6 runs.
- **C pid** — sigma const, `--dual pid --kp 1.0 --ki 1.0 --kd 0.5`. Tag **`t8e10_pid`**, 6 runs.

**Scripts (in `results_remote/`):**
- `stability_driver.ps1` — detached, idempotent driver. Runs wave B then wave C
  (concurrency 6, per-run `RQ1_CKPT_SUBDIR=tmp/ddpg_<name>`), blocks on each
  wave's completion markers, then runs the finalizer. Skips any run whose marker
  already exists.
- `stability_finalize_watch.ps1` — detached watcher: polls for all 12 markers,
  then runs `finalize_stability.py`. Idempotent via `logs/stability.finalized`
  sentinel. (Belt-and-suspenders with the driver's own finalize step.)
- `finalize_stability.py` — computes the 3-arm table (reuses
  `analyze_stability.per_seed` -> last-100-ep viol@tau from `AoI_evolution.mat`),
  writes the 2 figures + `RQ1_STABILITY_REPORT.md` with numbers-driven verdicts.
  **Refuses to write a partial report** (exits 2 unless all 12 runs present).
- `analyze_stability.py` — human-readable console version of the same analysis.
- `resume_stability.ps1` — one-command reboot-resume (see below).

**Where outputs land:**
- per-run `.mat`: `1-ModifiedMADDPGwithTDec/model/marl_model_hard_seed{S}_t8e10_anneal/`
  and `.../_t8e10_pid/` (headline files `viol_rate.mat`, `lambda.mat`, plus
  `AoI_evolution.mat`, `power.mat`, `demand.mat`, ...).
- report + figures: `results_remote/RQ1_STABILITY_REPORT.md`,
  `fig_stability_lambda.png` (lambda traces baseline vs PID),
  `fig_stability_anneal.png` (worst-feasible viol baseline vs anneal).
- logs/markers: `1-ModifiedMADDPGwithTDec/logs/hard_seed{S}_<tag>.out`,
  driver/watch progress logs, `stability.finalized` sentinel.

---

## 3. Is it done? + reboot-resume

**Done when:** all 12 `.out` files contain `simulation took this much time`
**and** `results_remote/RQ1_STABILITY_REPORT.md` exists (the finalizer wrote it).
Quick check:
```powershell
$L="D:\Jinnan\CMDP\AoI-V2X-CMDP\1-ModifiedMADDPGwithTDec\logs"
(2..7 | % { @('t8e10_anneal','t8e10_pid') | % { $t=$_ } } ) | Out-Null
$n=0; foreach($s in 2..7){ foreach($t in 't8e10_anneal','t8e10_pid'){ if(Select-String "$L\hard_seed${s}_$t.out" -SimpleMatch 'simulation took' -Quiet){$n++} }}
"markers: $n/12; report: " + (Test-Path 'D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\RQ1_STABILITY_REPORT.md')
```

**Reboot-resume (idempotent — skips finished runs, reruns only missing, then
finalizes; relaunches driver + watcher detached, no git):**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\resume_stability.ps1
```
Persistent-session note: tmux/screen are NOT installed; the Windows equivalent
is the hidden orphaned `Start-Process` used above (independent of SSH/agent).
Env: `./.venv` (system-site-packages over the shared `SimuV2X` conda torch+CUDA;
numpy 2.x => `np.int/np.bool` already patched). ~15-20 s/ep at 6x on this shared
GPU; ~75-100 min/wave.

---

## 4. Open items for the human (git — DO NOT let an agent push)

Two local commits already made (NOT pushed):
- `3ecc1a5` — Task 1: Git LFS tracking of all 540 `.mat` (45 runs).
- `c6fc6e9` — Task 2 code: `--sigma_anneal` + `--dual pid` flags.

**Pending Task-2 results commit** (left on disk for the human; agents must not
commit/push it per instruction). After the 12 runs + report exist:
```
cd D:\Jinnan\CMDP\AoI-V2X-CMDP
git add results_remote/RQ1_STABILITY_REPORT.md results_remote/HANDOVER.md ^
        results_remote/fig_stability_lambda.png results_remote/fig_stability_anneal.png ^
        results_remote/stability_driver.ps1 results_remote/stability_finalize_watch.ps1 ^
        results_remote/resume_stability.ps1 results_remote/analyze_stability.py ^
        results_remote/finalize_stability.py ^
        1-ModifiedMADDPGwithTDec/model/marl_model_hard_seed*_t8e10_anneal ^
        1-ModifiedMADDPGwithTDec/model/marl_model_hard_seed*_t8e10_pid
git commit -m "RQ1 stability study: sigma-anneal + PID arms (12 runs) + report"
git push        # human runs this; LFS objects push too
```
**Credential note:** `git push` has no TTY in non-interactive mode on this host
(credential store can't prompt) — **the human pushes manually**. Agents commit
locally only and report hashes.

---

## 5. TL;DR for a fresh agent
If you are a fresh agent: read this + `CLAUDE.md` + `RQ1_STABILITY_REPORT.md`
first, check disk state (markers / report / sentinel), and **do not re-run any
completed run** — if the stability run was interrupted, use the one-command
reboot-resume in §3; if it is finished, summarize the verdicts and leave the git
commit/push to the human.
