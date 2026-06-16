# Ablations_ep600 — differential ablations at the nominal point (τ=8/ε=0.10, ep600)

These are NOT self-contained: each arm here is a single variant whose **comparison
baseline lives in `../Canonical_ep600/`** (the soft baseline + the per-platoon PID dual).
Do not read them in isolation — pair each against the canonical reference.

- `global_lambda/` — **ablation #3** (finding 6): `hard_*_t8e10_pid_ep600_glmean` / `_glmax`
  = a single GLOBAL λ (network-mean / worst-driven) instead of per-platoon λ_j. Shows the
  per-platoon granularity is necessary. Report: `results_remote/RQ1_ABLATION3_GLOBAL_LAMBDA.md`.
- `fixed_weight/` — **ablation #4** (finding 7): `soft_*_qind_w{2,5,10,20}_ep600` = the same
  `1{AoI>τ}` signal as a FIXED-weight reward penalty (no dual). Shows a fixed weight is not
  a substitute for the dual. Report: `results_remote/RQ1_ABLATION4_FIXEDWEIGHT.md`.

Compare against: `../Canonical_ep600/{soft_*_base_ep600, hard_*_t8e10_pid_ep600}`.
