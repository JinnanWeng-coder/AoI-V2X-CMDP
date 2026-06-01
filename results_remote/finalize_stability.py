"""
[RQ1-CMDP] Task-2 SELF-CONTAINED finalizer. Run by the detached watcher
(stability_finalize_watch.ps1) once all 12 runs (anneal + pid, seeds 2-7) have
completed -- so the report + figures are produced ON DISK without depending on
the agent session or ScheduleWakeup.

Computes the 3-arm comparison (reusing analyze_stability.per_seed -> identical
last-100-ep viol@tau from AoI_evolution), generates the two figures, and writes
results_remote/RQ1_STABILITY_REPORT.md with numbers-driven verdicts.

Does NOT touch git (commit/push left to the operator).

Usage: python finalize_stability.py [--seeds 2 3 4 5 6 7] [--tau 8]
Exits non-zero (writes nothing) if any of the 12 runs is missing.
"""
import os
import sys
import argparse
import numpy as np

from analyze_stability import (per_seed, ARMS, ci95, make_figures, EPS, HAIR,
                               LAM_MAX, ACTIVE_LO, ACTIVE_HI, INFEAS)

HERE = os.path.dirname(os.path.realpath(__file__))
REPORT = os.path.join(HERE, "RQ1_STABILITY_REPORT.md")


def ci(arr):
    arr = [a for a in arr if a is not None and not (isinstance(a, float) and np.isnan(a))]
    if not arr:
        return float("nan"), 0.0
    return ci95(np.array(arr, dtype=np.float64))


def cifmt(arr, p=3):
    m, c = ci(arr)
    if np.isnan(m):
        return "n/a"
    return "%.*f +- %.*f" % (p, m, p, c)


def collect(seeds, tau):
    arm_rows = {}
    for name, tag in ARMS:
        rows = [per_seed(s, tag, tau) for s in seeds]
        arm_rows[name] = [r for r in rows if r is not None]
    return arm_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4, 5, 6, 7])
    ap.add_argument("--tau", type=float, default=8.0)
    a = ap.parse_args()
    seeds, tau = a.seeds, a.tau

    arm_rows = collect(seeds, tau)
    # require all three arms fully present before writing a report
    for name, _ in ARMS:
        if len(arm_rows[name]) < len(seeds):
            sys.stderr.write("[finalize] arm %s has %d/%d seeds -- NOT writing report yet\n"
                             % (name, len(arm_rows[name]), len(seeds)))
            sys.exit(2)

    make_figures(arm_rows, seeds)

    def col(name, key, scale=1.0):
        return cifmt([r[key] * scale for r in arm_rows[name]])

    def colp(name, key, p):
        return cifmt([r[key] for r in arm_rows[name]], p)

    def mean_of(name, key):
        v = [r[key] for r in arm_rows[name] if not np.isnan(r[key])]
        return float(np.mean(v)) if v else float("nan")

    def total(name, key):
        return sum(r[key] for r in arm_rows[name])

    base, ann, pid = arm_rows["baseline"], arm_rows["anneal"], arm_rows["pid"]
    bd = {r["seed"]: r for r in base}
    ad = {r["seed"]: r for r in ann}
    pd = {r["seed"]: r for r in pid}

    # ---- verdict numbers ----
    base_hair, ann_hair = total("baseline", "n_hair"), total("anneal", "n_hair")
    base_feas, ann_feas = total("baseline", "n_feas"), total("anneal", "n_feas")
    base_wf, ann_wf = mean_of("baseline", "worst_feas"), mean_of("anneal", "worst_feas")
    base_sac, ann_sac = total("baseline", "n_infeas"), total("anneal", "n_infeas")

    base_lstd = mean_of("baseline", "lam_std_active")
    pid_lstd = mean_of("pid", "lam_std_active")
    base_vstd = mean_of("baseline", "vio_std_active")
    pid_vstd = mean_of("pid", "vio_std_active")
    pid_feas, pid_sac = total("pid", "n_feas"), total("pid", "n_infeas")
    pid_wf = mean_of("pid", "worst_feas")

    def tag_delta(old, new, lower_is_better=True, rel=0.05):
        if np.isnan(old) or np.isnan(new):
            return "INCONCLUSIVE"
        d = new - old
        thr = rel * max(abs(old), 1e-9)
        if lower_is_better:
            if d < -thr:
                return "REDUCES"
            if d > thr:
                return "WORSENS"
            return "NO MATERIAL CHANGE"
        else:
            if d > thr:
                return "IMPROVES"
            if d < -thr:
                return "WORSENS"
            return "NO MATERIAL CHANGE"

    ann_hair_v = tag_delta(base_hair, ann_hair, lower_is_better=True)
    ann_wf_v = tag_delta(base_wf, ann_wf, lower_is_better=True)
    pid_lstd_v = tag_delta(base_lstd, pid_lstd, lower_is_better=True)
    pid_vstd_v = tag_delta(base_vstd, pid_vstd, lower_is_better=True)

    # seeds that cycled under baseline but not PID
    cyc_seeds = []
    for s in seeds:
        if s in bd and s in pd:
            lb, lp = bd[s]["lam_std_active"], pd[s]["lam_std_active"]
            if (not np.isnan(lb)) and (not np.isnan(lp)) and lb > 0.5 and lp < 0.7 * lb:
                cyc_seeds.append(s)

    # cost side
    base_pow, ann_pow, pid_pow = mean_of("baseline", "power"), mean_of("anneal", "power"), mean_of("pid", "power")
    base_dem, ann_dem, pid_dem = mean_of("baseline", "demand"), mean_of("anneal", "demand"), mean_of("pid", "demand")

    L = []
    w = L.append
    w("# RQ1 Task 2 — stability study: sigma-anneal + PID-Lagrangian\n")
    w("**Auto-generated on disk by the detached `stability_finalize_watch.ps1` -> "
      "`finalize_stability.py`** (independent of the agent session / SSH). Commit "
      "is left to the operator.\n")
    w("Clean ablation on the LOCKED base (do NOT recalibrate): `tau=8 eps=0.10 "
      "lam_max=20 episodes=300 aoi_floor=0.0`, seeds {2,3,4,5,6,7}, paired. "
      "Per-platoon violation is the last-100-ep mean recomputed at tau=%g from "
      "`AoI_evolution.mat` (identical to the headline analysis). The 3 "
      "structurally-infeasible platoons are reported, not excluded.\n" % tau)
    w("Three arms (only the stability knob differs):\n")
    w("- **A baseline** — `sigma=0.3` const, integral dual (the EXISTING hard "
      "`t8e10` seeds 2-7, reused; not rerun).")
    w("- **B anneal** — `--sigma_anneal` (sigma 0.3->0.05 linearly), integral dual.")
    w("- **C pid** — `sigma=0.3` const, `--dual pid --kp 1.0 --ki 1.0 --kd 0.5`.\n")
    w("Motivation: (a) per-seed RL variance leaves a feasible platoon a hair over "
      "eps (sigma-anneal target); (b) the dual shows per-seed limit-cycles "
      "(PID-Lagrangian target).\n")

    w("## 1. Three-arm aggregate (mean +- 95%% CI over seeds 2-7, last-100-ep)\n")
    w("| metric | baseline (A) | anneal (B) | pid (C) |")
    w("|---|---|---|---|")
    w("| #feasible (viol<=eps) / 5 | %s | %s | %s |" %
      (col("baseline", "n_feas"), col("anneal", "n_feas"), col("pid", "n_feas")))
    w("| worst-feasible violation | %s | %s | %s |" %
      (col("baseline", "worst_feas"), col("anneal", "worst_feas"), col("pid", "worst_feas")))
    w("| #hair-over-eps platoons (eps<viol<=eps+%.2f) | %s | %s | %s |" %
      (HAIR, col("baseline", "n_hair"), col("anneal", "n_hair"), col("pid", "n_hair")))
    w("| #infeasible (sacrificed) | %s | %s | %s |" %
      (col("baseline", "n_infeas"), col("anneal", "n_infeas"), col("pid", "n_infeas")))
    w("| **lambda std, active platoons** | %s | %s | %s |" %
      (col("baseline", "lam_std_active"), col("anneal", "lam_std_active"), col("pid", "lam_std_active")))
    w("| lambda std, all platoons | %s | %s | %s |" %
      (col("baseline", "lam_std_all"), col("anneal", "lam_std_all"), col("pid", "lam_std_all")))
    w("| **viol_rate std, active platoons** | %s | %s | %s |" %
      (col("baseline", "vio_std_active"), col("anneal", "vio_std_active"), col("pid", "vio_std_active")))
    w("| viol_rate std, all platoons | %s | %s | %s |" %
      (col("baseline", "vio_std_all"), col("anneal", "vio_std_all"), col("pid", "vio_std_all")))
    w("| Tx power (dBm) | %s | %s | %s |" %
      (colp("baseline", "power", 2), colp("anneal", "power", 2), colp("pid", "power", 2)))
    w("| remaining V2V demand | %s | %s | %s |" %
      (colp("baseline", "demand", 0), colp("anneal", "demand", 0), colp("pid", "demand", 0)))
    w("")
    w("*active platoon = mean lambda over the last 100 ep in (%.1f, %.1f), i.e. the "
      "multiplier is genuinely working, not pinned at 0 (slack) or %.0f (saturated/"
      "sacrificed). lambda/viol std over the last 100 ep is the limit-cycle metric: "
      "lower = stabler.*\n" % (ACTIVE_LO, ACTIVE_HI, LAM_MAX))

    w("## 2. (a) Does sigma-anneal reduce the hair-over-eps misses?\n")
    w("Per-seed, baseline vs anneal:\n")
    w("| seed | worst-feasible viol (base -> anneal) | #hair-over-eps (base -> anneal) | #feasible/5 (base -> anneal) |")
    w("|---|---|---|---|")
    for s in seeds:
        if s in bd and s in ad:
            b, n = bd[s], ad[s]
            w("| %d | %.3f -> %.3f | %d -> %d | %d -> %d |" %
              (s, b["worst_feas"], n["worst_feas"], b["n_hair"], n["n_hair"],
               b["n_feas"], n["n_feas"]))
    w("")
    w("**Totals over 30 platoon-seeds:** hair-over-eps %d -> %d; feasible %d -> %d; "
      "sacrificed %d -> %d. Mean worst-feasible viol %.3f -> %.3f.\n" %
      (base_hair, ann_hair, base_feas, ann_feas, base_sac, ann_sac, base_wf, ann_wf))
    w("**VERDICT (a): sigma-anneal %s the hair-over-eps count** (%d -> %d) and "
      "%s the mean worst-feasible violation (%.3f -> %.3f).\n" %
      (ann_hair_v, base_hair, ann_hair, ann_wf_v, base_wf, ann_wf))

    w("## 3. (b) Does PID-Lagrangian remove the dual limit-cycle?\n")
    w("Per-seed, baseline vs pid (active-multiplier std over the last 100 ep):\n")
    w("| seed | lambda std active (base -> pid) | viol_rate std active (base -> pid) | cycled-under-base-not-pid? |")
    w("|---|---|---|---|")
    for s in seeds:
        if s in bd and s in pd:
            b, p = bd[s], pd[s]
            lb, lp = b["lam_std_active"], p["lam_std_active"]
            cyc = (not np.isnan(lb)) and (not np.isnan(lp)) and lb > 0.5 and lp < 0.7 * lb
            w("| %d | %.3f -> %.3f | %.3f -> %.3f | %s |" %
              (s, lb, lp, b["vio_std_active"], p["vio_std_active"], "YES" if cyc else "no"))
    w("")
    w("**Mean over seeds:** lambda-std (active) %.3f -> %.3f; viol_rate-std (active) "
      "%.3f -> %.3f. Seeds that cycled under baseline but not PID: %s.\n" %
      (base_lstd, pid_lstd, base_vstd, pid_vstd, (cyc_seeds or "none")))
    w("**VERDICT (b): PID %s the multiplier limit-cycle** (lambda-std active "
      "%.3f -> %.3f) and %s the violation-rate oscillation (viol-std active "
      "%.3f -> %.3f).\n" %
      (pid_lstd_v, base_lstd, pid_lstd, pid_vstd_v, base_vstd, pid_vstd))
    w("PID feasibility unchanged-or-better as a guardrail: feasible %d -> %d, "
      "sacrificed %d -> %d, mean worst-feasible %.3f -> %.3f.\n" %
      (base_feas, pid_feas, base_sac, pid_sac, base_wf, pid_wf))

    w("## 4. Cost side — stability not bought with silent power/V2V\n")
    w("| arm | Tx power (dBm) | remaining V2V demand |")
    w("|---|---|---|")
    w("| baseline | %.2f | %.0f |" % (base_pow, base_dem))
    w("| anneal | %.2f | %.0f |" % (ann_pow, ann_dem))
    w("| pid | %.2f | %.0f |" % (pid_pow, pid_dem))
    w("")
    pow_note = ("anneal power %s baseline, pid power %s baseline" % (
        "<=" if ann_pow <= base_pow + 0.5 else "ABOVE",
        "<=" if pid_pow <= base_pow + 0.5 else "ABOVE"))
    w("Read: %s; remaining-V2V-demand moves are reported above. A stability win is "
      "only credible if power/V2V do not silently inflate.\n" % pow_note)

    w("## 5. Structurally-infeasible platoons (reported, not excluded)\n")
    for name in ("baseline", "anneal", "pid"):
        sac = [(r["seed"], r["infeas_idx"], np.round(r["viol"][r["infeas_idx"]], 3).tolist())
               for r in arm_rows[name] if r["infeas_idx"]]
        w("- **%s:** %s" % (name, sac or "none"))
    w("\nThese are the same on-floor (3-RB / 5-platoon) victims as the headline "
      "report; the stability knobs are not expected to make a structurally "
      "unservable platoon feasible (that is the `--aoi_floor` safeguard's job).\n")

    w("## 6. Figures\n")
    w("- `fig_stability_lambda.png` — per-platoon lambda_j traces over the last "
      "100 ep, baseline vs PID (worst-baseline-cycle seed).")
    w("- `fig_stability_anneal.png` — worst-feasible per-platoon violation per "
      "seed, baseline vs sigma-anneal, with the eps line.\n")

    w("## 7. Reproduce\n")
    w("```")
    w("# from results_remote/, with ../.venv python")
    w("python analyze_stability.py --seeds 2 3 4 5 6 7 --tau 8   # console detail")
    w("python finalize_stability.py --seeds 2 3 4 5 6 7 --tau 8  # this report + figs")
    w("```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[finalize] wrote", REPORT)


if __name__ == "__main__":
    main()
