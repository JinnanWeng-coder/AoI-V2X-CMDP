# Legacy_300ep — retired / superseded 300-episode process runs

Archived here to declutter `model/`. These are **NOT** part of the live RQ1 result set —
kept for provenance only. Current findings + the live data→claim map are in
`../../CLAUDE.md`; the canonical converged data is the `*_ep600` set in `model/` root.

## What's here — 3 retired studies

- **τ/ε phase grid (non-(8,10) cells)** — `hard_seedN_t{10,12}e{10,15}(_pid)` and
  `hard_seedN_t8e15(_pid)`, seeds 2–7 (the `t10e10`/`t12e10` cells also seeds 8–11). The
  τ/ε "infeasibility frontier" this mapped is **SUPERSEDED** by the resource-frontier
  sweep in `../ScenarioSweep/`. Report `RQ1_PHASE_PID_REPORT.md`; figures
  `fig_phase_diagram.png`, `fig_phase_diagram_pid.png`.
- **σ-anneal** — `hard_seedN_t8e10_anneal`, seeds 2–7. Tested and **REJECTED** (trades
  tail misses for higher worst-case variance + power). Report `RQ1_STABILITY_REPORT.md`;
  figures `fig_stability_anneal.png`, `fig_stability_lambda.png`.
- **`--aoi_floor`** — `hard_seedN_t8e10(_pid)_floor`, seeds 2,3,4. **RETIRED** (no truly
  infeasible platoon exists, and the floor back-fires under PID). Report
  `RQ1_FLOOR_AND_CI_REPORT.md`; figures `fig_floor.png`, `fig_pid_floor.png`.

`scripts/` holds these studies' drivers / analyzers / resume scripts (archival).

## Important notes (what is deliberately NOT here)

- **The phase grid's (8,10) cell is NOT here.** `hard_seed*_t8e10` / `_t8e10_pid` (300 ep)
  stay in `model/` root because they are **LIVE**: claim-4 (integral-vs-PID limit-cycle)
  and the n=10 CI headline. The phase report's (8,10) row is computed from those root runs.
- **The shared loader `analyze_remote.py` stays in `../../results_remote/scripts/`** (still
  used by the live ep600 / seed2 analyzers). Re-running the archived analyzers here would
  need their `analyze_remote` import path fixed — they are archival, not maintained.
