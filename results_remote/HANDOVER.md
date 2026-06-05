# RQ1 HANDOVER — single source of truth for the next session

> **Fresh agent: read `CLAUDE.md` (repo root) THEN this file. Check disk state
> before acting. Do NOT re-run any run whose `.out` already contains the marker
> `simulation took this much time`.** Everything stays inside
> `D:\Jinnan\CMDP\AoI-V2X-CMDP` (shared machine). Never `git push` (no TTY for
> creds — commit locally, report hashes, the human pushes). Never recalibrate the
> locked config; never drop a seed.

**Last updated: 2026-06-04 ~01:15 — ep600 COMPLETE (18/18), report committed.
Nothing in flight.**

> ⚠️ **This file is a CHRONOLOGICAL BATCH LOG, not current manuscript guidance.**
> Early rows (e.g. the integral/300-ep batch) report numbers that were later
> SUPERSEDED — e.g. "~1.6× power / 3 structurally-infeasible / floor bounds an
> unservable platoon" are NOT the final findings. For canonical numbers and what to
> write, use `../../Manuscript/README_FOR_WRITING.md` and
> `../../Manuscript/data/feasible_cost_table.md`. Final state: cost is ~+25% power /
> ≈0 V2V (PID/ep600); **no structurally-infeasible platoon exists** (seed2-pl2 was
> under-trained — see `RQ1_SEED2_INFEAS_REPORT.md`); the `--aoi_floor` safeguard is
> retired (back-fires under PID). Read the rows below as "what we believed at each
> step", not as the conclusion.

---

## 0. STATUS — ep600 re-run COMPLETE (no action needed)

All 18 ep600 runs finished; `RQ1_EP600_REPORT.md` + `fig_ep600_convergence.png`
written and committed. Finding: integral sacrificed platoon-seeds 3→1, soft 2→0
(int-s3/s7 were under-training, now rescued; int-s2-pl2 truly resource-limited
remains); soft-vs-hard(PID) worst-platoon gap 0.346→0.228, still clearly positive
(core result holds); PID unchanged. HONEST caveat: 600 ep still INSUFFICIENT for
soft-s2-pl2 and int-s7-pl0 (still descending at block 12 → true converged violation
even lower). The RQ1 story is complete across stability / PID phase / floor+CI /
ep600. Nothing is in flight.

**(Historical) the ep600 re-run was driven by the same detached pattern; if you
ever need to resume an interrupted batch, the idempotent one-liner is:**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\scripts\resume_ep600.ps1
```
NOTE: the driver's per-wave wait has a 600-min timeout; if a wave is resumed late
and exceeds it, the driver may exit before the runs finish and skip its self-
finalize. In that case run `python scripts/analyze_ep600.py` manually (from
`results_remote/`, with `../.venv` python) once all 18 `.out` markers exist — that
is exactly what happened on the final PID wave and how the report was produced.

**ep600 experiment** (`results_remote/ep600_driver.ps1` / `analyze_ep600.py` /
`resume_ep600.ps1`): t8e10, `--episodes 600`, locked config otherwise unchanged
(tau=8 eps=0.10 eta_lam=1.0 lam_max=20, PID kp=1 ki=1 kd=0.5, sigma const 0.3 — NO
`--sigma_anneal`). Three arms × seeds {2-7} = 18 runs, NEW `_ep600` tags so the
300-ep runs are NOT overwritten:
- soft → `marl_model_soft_seed{S}_base_ep600`
- hard integral → `marl_model_hard_seed{S}_t8e10_ep600`
- hard PID → `marl_model_hard_seed{S}_t8e10_pid_ep600`

**WHY:** raw-`.mat` convergence analysis (50-ep blocks of `AoI.mat`) showed three
300-ep runs are UNDER-TRAINED — a single cap-bound platoon is only rescued in the
last 50 ep and still descending at ep300 (soft-s2 pl2: …100,100,57; hard-int-s3
pl0: …97,76,13; hard-int-s7 pl0: …97,98,54), so their last-100-ep window sits
mid-transition. Main.py trains from scratch (no resume), so "extend" = re-run at
600 ep. PID runs were already converged by ep50.

**State at reboot (updated 2026-06-03 ~20:00 — 12/18 done on disk):** soft
`_base_ep600` **6/6 DONE**; integral `t8e10_ep600` **6/6 DONE**; PID
`t8e10_pid_ep600` **0/6** (wave 3 was in flight at the reboot — killed, no partial
`.mat`). So `resume_ep600.ps1` reruns ONLY the **6 PID runs**, then self-writes the
report.

**ANALYSIS (auto, after all 18 done)** — `analyze_ep600.py` writes
`RQ1_EP600_REPORT.md`: (1) 50-ep blocked trajectory (12 blocks) of network-mean AoI
for all 18 + per-platoon AoI for the 3 flagged cap-bound platoons, with a FLAT /
NOT-flat / INSUFFICIENT verdict per run (states plainly if 600 ep is still not
enough); (2) 300-vs-600 last-100-ep per-platoon violation, soft-vs-hard(PID)
worst-platoon gap (±95% CI), integral "sacrificed" count (≥0.5); (3) which 300-ep
conclusions change. The blocking was validated to reproduce the documented
under-training pattern exactly before launch.

**After all 18 + report exist → COMMIT (see §4), report hash, do NOT push.**

---

## 1. Project + what is DONE (all committed locally, none pushed)

Codebase `1-ModifiedMADDPGwithTDec` (Parvini AoI-MARL platoon C-V2X). `--mode soft`
(AoI as `-AoI/20` reward penalty, baseline) vs `--mode hard` (per-platoon CMDP
`P(AoI_j>tau)<=eps` via a cost critic + per-platoon Lagrange multiplier `lambda_j`,
two-timescale dual). Dual rule selectable: `--dual integral` (default) or
`--dual pid --kp --ki --kd` (PID-Lagrangian, Stooke 2020). `--sigma_anneal` anneals
actor noise 0.3→0.05. `--aoi_floor` keeps a small AoI penalty for saturated
platoons. Global-critic gradient bug retained on purpose (orthogonal to the
local-actor constraint). Code change detail: `../RQ1_CMDP_IMPLEMENTATION.md`.

**Locked config (NEVER recalibrate): tau=8 eps=0.10 eta_lam=1.0 lam_max=20,
PID kp=1.0 ki=1.0 kd=0.5, scenario 5 platoons × 4 veh × 3 RB, seeds paired.**

| batch | report | headline finding |
|---|---|---|
| 6-seed headline + tau/eps phase (INTEGRAL) + aoi_floor safeguard | `RQ1_REMOTE_REPORT.md` | feasible platoons driven 0.197→0.100 at flat AoI; ~1.6× power; 3/30 structurally-infeasible flagged; floor bounds an unservable platoon (AoI 90→17). |
| stability: σ-anneal vs PID-Lagrangian | `RQ1_STABILITY_REPORT.md` | **PID removes the dual limit-cycle** (λ-std 1.13→0.69) AND improves feasibility (feasible 15→24/30, sacrificed 3→0) cheaper; σ-anneal MIXED (cuts hair-over-ε but worsens worst-feasible + more power). PID is the win. |
| PID τ/ε phase diagram (30 runs) | `RQ1_PHASE_PID_REPORT.md` | frontier **SOFTENED not overturned**: sacrifices integral 6 → PID 1; seed3-pl0 is τ-recoverable, **seed2-pl2 is truly resource-limited** (λ≈20 at all τ). |
| EXP1 PID+aoi_floor + EXP2 n=10 CI (31 runs) | `RQ1_FLOOR_AND_CI_REPORT.md` | EXP1 **NEGATIVE/seed-dependent**: under PID the floor BREAKS seed2-pl2 (AoI 4.3→100); seed3 helps. EXP2 at n=10: soft-vs-hard(PID) worst-platoon gap HOLDS (0.324±0.118 @τ8); "no cell ≥4.5/5" HOLDS; "PID>integral #pass at t8e10" WEAKENS (CIs overlap). |
| **ep600 convergence re-run (18 runs)** | `RQ1_EP600_REPORT.md` | **IN FLIGHT — see §0.** Tests whether 600 ep flattens the under-trained transition and which 300-ep numbers change. |

**Commits (local only, NOT pushed — human pushes & cross-checks raw `.mat`):**
- `d14dab1` — EXP1 (PID+aoi_floor) + EXP2 (n=10 CI): 31 runs + report + figure
- `04669cf` — PID phase diagram: 30 runs + report + figure
- `95e83ea` — stability: σ-anneal + PID: report + 2 figures + 12 LFS .mat
- `8ccecd0` — stability HANDOVER + driver/analysis scripts
- `c6fc6e9` — Main.py: `--sigma_anneal` + `--dual pid` flags
- `3ecc1a5` — Git LFS tracking of all run `.mat`
- (the **ep600 commit is still PENDING** — make it after §0 completes.)

All run `.mat` are tracked via **Git LFS** (`.gitattributes`:
`1-ModifiedMADDPGwithTDec/model/**/*.mat`).

---

## 2. Detached-run mechanics (same pattern every batch)

tmux/screen unavailable → a hidden, orphaned `Start-Process` driver under
`results_remote/` that survives SSH/agent disconnect. Each driver: processes a spec
list in waves of ≤6, per-run `RQ1_CKPT_SUBDIR=tmp/ddpg_<name>`, per-run `.out` logs
under `logs/`, blocks on completion markers, is **idempotent** (skips runs whose
marker exists), and **self-finalizes** (runs its analysis → report + figure, no git)
guarded by a `*.finalized` sentinel. Each has a one-command `resume_*.ps1`.
Env: `./.venv` (system-site-packages over shared `SimuV2X` conda torch+CUDA; numpy
2.x `np.int/np.bool` already patched). ~16 s/ep at 6× when GPU is free (slower under
contention). A run is "done" when its `.out` has `simulation took this much time`.

Driver/analysis/resume scripts per batch (all in `results_remote/`):
`stability_driver.ps1`/`analyze_stability.py`/`finalize_stability.py`/`resume_stability.ps1`;
`phase_pid_driver.ps1`/`analyze_phase_pid.py`/`resume_phase_pid.ps1`;
`floor_ci_driver.ps1`/`analyze_floor_ci.py`/`resume_floor_ci.ps1`;
`ep600_driver.ps1`/`analyze_ep600.py`/`resume_ep600.ps1`. Shared loader:
`analyze_remote.py` (`metrics()` recomputes last-100-ep per-platoon violation at a
given τ from `AoI_evolution.mat`; `AoI.mat` = per-platoon mean AoI EVERY episode →
trajectory source).

---

## 3. Done-check for ep600

```powershell
$L="D:\Jinnan\CMDP\AoI-V2X-CMDP\1-ModifiedMADDPGwithTDec\logs"; $n=0
foreach($a in 'soft_seed{0}_base_ep600','hard_seed{0}_t8e10_ep600','hard_seed{0}_t8e10_pid_ep600'){
 foreach($s in 2..7){ if(Select-String ($L+'\'+($a -f $s)+'.out') -SimpleMatch 'simulation took' -Quiet){$n++} }}
"ep600 markers: $n/18; report: " + (Test-Path 'D:\Jinnan\CMDP\AoI-V2X-CMDP\results_remote\RQ1_EP600_REPORT.md')
```

---

## 4. COMMIT the ep600 batch (after all 18 + report exist; local only)

```
cd D:\Jinnan\CMDP\AoI-V2X-CMDP
git add 1-ModifiedMADDPGwithTDec/model/marl_model_soft_seed{2,3,4,5,6,7}_base_ep600 ^
        1-ModifiedMADDPGwithTDec/model/marl_model_hard_seed{2,3,4,5,6,7}_t8e10_ep600 ^
        1-ModifiedMADDPGwithTDec/model/marl_model_hard_seed{2,3,4,5,6,7}_t8e10_pid_ep600 ^
        results_remote/RQ1_EP600_REPORT.md results_remote/fig_ep600_convergence.png ^
        results_remote/ep600_driver.ps1 results_remote/analyze_ep600.py results_remote/resume_ep600.ps1 ^
        CLAUDE.md results_remote/HANDOVER.md
# VERIFY staged = ONLY those .mat (216 = 18×12) + report + figure + 3 scripts + the 2 docs.
# NO checkpoints (Classes/tmp/ddpg_*), TB events (runs/**/events.out.*), logs/, or .claude/.
git status --short | grep -v '^?? \.claude/$'    # should show only intended staged files
git commit -m "RQ1 ep600 convergence re-run: 18 runs (t8e10 soft/int/pid) + report"
# git push   <-- HUMAN ONLY (no TTY for creds in agent context)
```
Note: `.mat` are LFS pointers; confirm with `git show :<path>/AoI.mat | head -1`
(should print `version https://git-lfs...`). `.png` under `model/` is gitignored;
the report/figure live under `results_remote/` (tracked normally).

---

## 5. TL;DR
Read `CLAUDE.md` + this file. Disk survived the reboot; the 6 soft ep600 runs are
done. Run `resume_ep600.ps1`, let it finish the 12 hard runs + write the report,
summarize the convergence verdict + 300-vs-600 changes, then COMMIT per §4 and
report the hash. Do not push, do not recalibrate, do not drop a seed.
