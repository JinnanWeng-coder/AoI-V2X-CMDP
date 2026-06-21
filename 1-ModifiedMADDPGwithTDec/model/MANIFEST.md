# `model/` MANIFEST — what each study folder holds

Run-dir naming: `marl_model_<mode>_seed<N>_<tag>`. **A run's folder is organizational
only** — the analysis/figure scripts resolve a run by its NAME anywhere under `model/`
(the Manuscript figure scripts use a recursive `_R(name)` resolver), so moving runs
between study folders does not break them. New runs can be written straight into a study
folder with `--out_subdir` (see ARCHITECTURE.md §4).

| folder | study | arms (run-name tag) | seeds | compare against | report | finding |
|---|---|---|---|---|---|---|
| `Canonical_ep600/` | 3-arm reference (ep600) | `soft_*_base_ep600`, `hard_*_t8e10_ep600` (integral), `hard_*_t8e10_pid_ep600` (PID) | 2–7 | **self — the comparison anchor** | `results_remote/RQ1_EP600_REPORT.md` | findings 1–3 |
| `Ablations_ep600/global_lambda/` | #3 per-platoon vs global λ | `hard_*_t8e10_pid_ep600_glmean` / `_glmax` | 2–7 | `../../Canonical_ep600` (pid) | `results_remote/RQ1_ABLATION3_GLOBAL_LAMBDA.md` | 6 |
| `Ablations_ep600/fixed_weight/` | #4 fixed-weight penalty | `soft_*_qind_w{2,5,10,20}_ep600` | 2–7 | `../../Canonical_ep600` | `results_remote/RQ1_ABLATION4_FIXEDWEIGHT.md` | 7 |
| `Ablations_ep600/cost_source/` | A1 cost-critic necessity (`--cost_source raw`, RCPO-style: −λ·cost folded into task-2 reward, no separate Q^c) | `hard_*_t8e10_pid_ep600_rawcost` | 2–7 | `../../Canonical_ep600` PID (== `--cost_source critic`) | `results_remote/RQ1_ABLATION_COSTSOURCE.md` | A1 (defends method component c) |
| `Feasibility_ep1000/` | seed2 1000-ep | `soft/hard_seed2_*_ep1000` | 2 | `Canonical_ep600` | `results_remote/RQ1_SEED2_INFEAS_REPORT.md` | 5 |
| `ScenarioSweep/` | resource frontier | `*_rb{2,3,4}_pl{4,5,6}` (4 arms) | 2–4 | self-contained (each cell carries its own soft / pid / glmax / qind) | `ScenarioSweep/RQ1_SCENARIO_SWEEP.md` | 8 |
| `ep600_deploy/` | frozen-deployment eval | `soft_*_base_ep600_deploy`, `hard_*_t8e10_pid_ep600_deploy` (+ `*_test*` / `_test_warm*` / `_n*`) | 2–7 | training-time `.mat` in the same dir | `results_remote/RQ1_DEPLOY_EVAL_{AB,WARM,NOISE}.md` | deployment phase |
| `Deploy_seamless_800ep/` | SEAMLESS deployment (train 600 == canonical, then frozen 200-ep tail on the SAME env, σ=0.3, AoI not reset) | `soft_*_base_seamless800`, `hard_*_t8e10_pid_seamless800` (+ `*_seamless*.mat`, `Scenario_Reconstruct.pkl`) | 2–7 | this run's training `.mat` + `Canonical_ep600` (acceptance gate) | `results_remote/RQ1_DEPLOY_SEAMLESS.md` | removes the --eval_only geometry-restart + AoI-reset confounds; cause-discrimination (under-training vs online-dual). Flags: `--seamless_tail/--seamless_noise/--seamless_resume` |
| `Deploy_seamless_1200ep/` | SEAMLESS ep1000 (train **1000** + frozen 200-ep tail, σ=0.3; `memory_size`=50000 UNCHANGED) | `soft_*_base_seamless1200`, `hard_*_t8e10_pid_seamless1200` (+ `*_seamless*.mat`, `Scenario_Reconstruct.pkl`) | 2–7 | `Canonical_ep600` first-600 gate (via `viol_rate[:, :600]`, not AoI_evolution) | `results_remote/RQ1_DEPLOY_SEAMLESS1000.md` | idea-1 test: buffer-eviction reading of the ep500-600 cost-critic-loss drop (does loss keep dropping then flatten while violation stays at ε?). NO Main.py change (`--episodes 1000`) |
| `Legacy_300ep/` | retired 300-ep | τ/ε phase (non-(8,10) cells), σ-anneal, floor; + `claim4_support/` (300-ep headline + claim-4 `t8e10`±pid, n=10, + soft baseline) | 2–11 | — | inside `Legacy_300ep/` | claim 4 (in `claim4_support/`); the rest retired |

Notes
- The CMDP "reference" set is `Canonical_ep600/`; every differential ablation
  (`Ablations_ep600/*`) and the deployment runs compare against it.
- Reports live in `results_remote/` unless the table says otherwise; the five manuscript
  claim figures regenerate via `../../Manuscript/figures/scripts for images/` (resolver-based).
- Full data→claim map + verification protocol: `../../CLAUDE.md` §2/§4.
