# AoI-V2X-CMDP — per-platoon hard-constraint RL for platoon C-V2X (RQ1)

A fork of the Parvini AoI-MARL platoon C-V2X codebase (active algorithm:
`1-ModifiedMADDPGwithTDec`) that recasts per-platoon Age-of-Information from a soft
reward penalty (`−AoI/20`) into a per-platoon **CMDP constraint** `P(AoI_j>τ)≤ε`,
solved by a per-platoon cost critic + Lagrange multiplier (two-timescale dual).
Upstream baseline: `AoI-V2X-IEEE-TVT-2023` (Parvini et al.) — see `LICENSE`.

**Status (2026-06-11):** training-level findings settled (worst-convoy protection, cost,
PID dual, two necessity ablations, resource frontier at ≈2 platoons/RB); frozen-deployment
evaluation in progress (deterministic deployment loses the guarantee — stochastic-policy
eval pending). Details: `CLAUDE.md`.

**Start here:**
- [`CLAUDE.md`](CLAUDE.md) — current experiment status, findings, data→claim map (**all agents read first**).
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the method + code architecture (cost critic, dual, exact edits, flags).
- [`REMOTE_RUNBOOK.md`](REMOTE_RUNBOOK.md) — how to run/resume/commit training on the remote machine.
- `../Manuscript/README_FOR_WRITING.md` — paper-writing guide (claims, figures, data).

Data (`*.mat`) is Git-LFS tracked: `git lfs install && git lfs pull` after cloning.
