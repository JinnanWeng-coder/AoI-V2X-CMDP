"""
[RQ1-CMDP] PID tau/eps phase-diagram analysis + report (self-contained).

Re-draws the full tau/eps feasibility phase diagram under the PID dual and
compares it cell-by-cell against the OLD pure-INTEGRAL phase diagram, recomputing
both from disk with the SAME methodology (analyze_remote.metrics: per-platoon
violation recomputed at each cell's tau from AoI_evolution.mat, last-100-ep).

Outputs (results_remote/):
  fig_phase_diagram_pid.png   - PID 6-seed heatmap (mean #platoons <= eps), same
                                format as the old integral fig_phase_diagram.png.
  RQ1_PHASE_PID_REPORT.md     - PID-vs-integral table, frontier verdict, the
                                seed2-pl2 / seed3-pl0 bottleneck diagnostic, caveats.

Folder tags:  integral = marl_model_hard_seed{S}_t{T}e{E}     (E=eps*100)
              pid      = marl_model_hard_seed{S}_t{T}e{E}_pid
Refuses to write the report unless all 36 PID cells (6x6) are present (exit 2).
Does NOT touch git.
"""
import os
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_remote import metrics, ci95, folder

HERE = os.path.dirname(os.path.realpath(__file__))
OUT = HERE
REPORT = os.path.join(HERE, "RQ1_PHASE_PID_REPORT.md")
LAM_MAX = 20.0
SACR = 0.5            # viol > eps + SACR => structurally sacrificed (lambda-saturated)
TAUS = [8, 10, 12]
EPSES = [0.10, 0.15]

# OLD integral phase numbers, from the committed RQ1_REMOTE_REPORT.md s2b (n=6),
# kept only as a cross-check label; the script ALSO recomputes integral from disk.
INTEGRAL_REPORTED = {
    (8, 0.10): (2.50, 1.45, 1, 0.163, 0.109, 3),
    (8, 0.15): (4.17, 0.79, 2, 0.152, 0.011, 1),
    (10, 0.10): (3.50, 1.45, 1, 0.122, 0.047, 0),
    (10, 0.15): (3.67, 0.54, 0, 0.169, 0.020, 1),
    (12, 0.10): (3.50, 1.29, 2, 0.123, 0.056, 1),
    (12, 0.15): (4.00, 0.66, 1, 0.155, 0.008, 0),
}


def cell_tag(tau, eps, pid):
    t = "t%de%d" % (int(tau), int(round(eps * 100)))
    return t + "_pid" if pid else t


def cell_stats(seeds, tau, eps, pid):
    """Aggregate one (tau,eps) cell. Returns dict or None if no data."""
    rows = []
    for s in seeds:
        mm = metrics("hard", s, cell_tag(tau, eps, pid), tau)
        if mm is None:
            continue
        viol = mm["viol"]
        P = mm["P"]
        n_pass = int(np.sum(viol <= eps + 1e-9))
        feas = viol[viol <= eps + SACR]
        worst_feas = float(feas.max()) if feas.size else float("nan")
        n_sac = int(np.sum(viol > eps + SACR))
        rows.append(dict(seed=s, n_pass=n_pass, P=P, worst_feas=worst_feas, n_sac=n_sac))
    if not rows:
        return None
    npass = np.array([r["n_pass"] for r in rows], dtype=np.float64)
    wf = np.array([r["worst_feas"] for r in rows], dtype=np.float64)
    wf_ok = wf[~np.isnan(wf)]
    pm, pci = ci95(npass)
    wm, wci = ci95(wf_ok) if wf_ok.size else (float("nan"), 0.0)
    return dict(
        n=len(rows), rows=rows,
        pass_mean=float(pm), pass_ci=float(pci),
        strict=int(sum(r["n_pass"] == r["P"] for r in rows)),
        worst_mean=float(wm), worst_ci=float(wci),
        sac_pairs=int(sum(r["n_sac"] for r in rows)),
        sac_seeds=int(sum(1 for r in rows if r["n_sac"] > 0)),
    )


def count_present(seeds, pid):
    n = 0
    for t in TAUS:
        for e in EPSES:
            for s in seeds:
                mm = metrics("hard", s, cell_tag(t, e, pid), t)
                if mm is not None:
                    n += 1
    return n


def plot_heatmap(seeds, pid_grid):
    fig, ax = plt.subplots(figsize=(1.6 * len(EPSES) + 2, 1.1 * len(TAUS) + 2))
    M = np.full((len(TAUS), len(EPSES)), np.nan)
    for i, t in enumerate(TAUS):
        for k, e in enumerate(EPSES):
            c = pid_grid.get((t, e))
            if c:
                M[i, k] = c["pass_mean"]
    im = ax.imshow(M, cmap="RdYlGn", vmin=0, vmax=5, aspect="auto")
    ax.set_xticks(range(len(EPSES))); ax.set_xticklabels(["%.2f" % e for e in EPSES])
    ax.set_yticks(range(len(TAUS))); ax.set_yticklabels(["%g" % t for t in TAUS])
    ax.set_xlabel(r"target violation $\epsilon$")
    ax.set_ylabel(r"AoI threshold $\tau$ (slots)")
    for i in range(len(TAUS)):
        for k in range(len(EPSES)):
            if not np.isnan(M[i, k]):
                ax.text(k, i, "%.1f" % M[i, k], ha="center", va="center", fontsize=11)
    ax.set_title("PID dual: mean #platoons (of 5) driven $\\leq\\epsilon$\n"
                 "(green=all 5 feasible, %d seeds)" % len(seeds))
    fig.colorbar(im, ax=ax, label="#platoons satisfied")
    fig.tight_layout()
    f = os.path.join(OUT, "fig_phase_diagram_pid.png")
    fig.savefig(f, dpi=150); plt.close(fig)
    return f


def bottleneck_diag(seeds_pl):
    """seeds_pl: list of (seed, platoon_idx). Track each at tau in {8,10,12}, eps=0.10."""
    lines = []
    for (s, pl) in seeds_pl:
        row = ["seed%d-pl%d" % (s, pl)]
        for t in TAUS:
            mm = metrics("hard", s, cell_tag(t, 0.10, True), t)
            if mm is None:
                row.append("(missing)"); continue
            viol = mm["viol"][pl]
            aoi = mm["aoi"][pl]
            lam = mm["lam_final"][pl] if mm["lam_final"] is not None else float("nan")
            sat = "SAT" if (not np.isnan(lam) and lam >= LAM_MAX - 0.5) else "ok"
            row.append("tau%d: viol=%.3f AoI=%.1f lam=%.1f(%s)" % (t, viol, aoi, lam, sat))
        lines.append(row)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4, 5, 6, 7])
    a = ap.parse_args()
    seeds = a.seeds

    present = count_present(seeds, pid=True)
    need = len(TAUS) * len(EPSES) * len(seeds)
    if present < need:
        sys.stderr.write("[phase_pid] only %d/%d PID cells present -- not writing report\n"
                         % (present, need))
        sys.exit(2)

    pid_grid = {}
    int_grid = {}
    for t in TAUS:
        for e in EPSES:
            pid_grid[(t, e)] = cell_stats(seeds, t, e, pid=True)
            int_grid[(t, e)] = cell_stats(seeds, t, e, pid=False)

    figpath = plot_heatmap(seeds, pid_grid)

    # ---- totals for the verdict ----
    pid_sac_total = sum(c["sac_pairs"] for c in pid_grid.values() if c)
    int_sac_total = sum(c["sac_pairs"] for c in int_grid.values() if c)
    pid_offfloor_clear = sum(1 for (t, e), c in pid_grid.items()
                             if c and (t, e) != (8, 0.10) and c["sac_pairs"] == 0)
    pid_strict_cells = sum(1 for c in pid_grid.values() if c and c["pass_mean"] >= 4.5)

    L = []
    w = L.append
    w("# RQ1 — tau/eps feasibility phase diagram under the PID dual\n")
    w("**Auto-generated on disk by `phase_pid_driver.ps1` -> `analyze_phase_pid.py`** "
      "(detached, independent of the agent session). Commit left to the operator.\n")
    w("Re-draws the full tau/eps phase diagram under PID-Lagrangian "
      "(`--dual pid --kp 1.0 --ki 1.0 --kd 0.5`, the stability-study gains) and "
      "compares cell-by-cell to the OLD pure-integral diagram. Both sides are "
      "recomputed from disk with identical methodology (per-platoon violation "
      "recomputed at each cell's tau from `AoI_evolution.mat`, last-100-ep). "
      "Locked base: episodes=300, lam_max=20, aoi_floor=0.0, 5 platoons x 4 veh x "
      "3 RB, seeds {2,3,4,5,6,7} (n=6/cell). The structurally-infeasible platoons "
      "are reported, not excluded.\n")
    w("Motivation: the old integral phase diagram concluded *loosening tau/eps "
      "reduces but does not buy strict feasibility; 3/30 platoons sacrificed*. PID "
      "later dominated integral at t8e10 (sacrificed 3->0), suggesting some "
      "integral sacrifices were **pseudo-infeasibility** (limit-cycle mis-kills). "
      "This re-draw tests whether that holds across the whole grid.\n")

    w("## 1. PID phase heatmap\n")
    w("See `fig_phase_diagram_pid.png` (same format as the old "
      "`fig_phase_diagram.png` for side-by-side).\n")

    w("## 2. PID vs integral, per cell (n=6, mean +- 95%% CI)\n")
    w("| (tau, eps) | #pass/5 INT | #pass/5 PID | strict 5/5 INT->PID | "
      "worst-feasible INT->PID | #sacrificed INT->PID |")
    w("|---|---|---|---|---|---|")
    for t in TAUS:
        for e in EPSES:
            ip = int_grid[(t, e)]
            pp = pid_grid[(t, e)]
            if not pp:
                w("| (%g, %.2f) | - | NO DATA | - | - | - |" % (t, e)); continue
            istr = ("%.2f +- %.2f" % (ip["pass_mean"], ip["pass_ci"])) if ip else "n/a"
            pstr = "%.2f +- %.2f" % (pp["pass_mean"], pp["pass_ci"])
            i_strict = ip["strict"] if ip else "n/a"
            i_worst = ("%.3f +- %.3f" % (ip["worst_mean"], ip["worst_ci"])) if ip else "n/a"
            p_worst = "%.3f +- %.3f" % (pp["worst_mean"], pp["worst_ci"])
            i_sac = ip["sac_pairs"] if ip else "n/a"
            w("| (%g, %.2f) | %s | **%s** | %s -> %s | %s -> %s | %s -> **%s** |" %
              (t, e, istr, pstr, i_strict, pp["strict"], i_worst, p_worst, i_sac, pp["sac_pairs"]))
    w("")
    w("Totals over the 6 cells (36 platoon-seeds each): **sacrificed (lambda-saturated) "
      "platoon-seeds INT %d -> PID %d**. Off-floor cells (everything except t8e10) "
      "that sacrifice NOBODY under PID: **%d / 5**. Cells averaging >=4.5/5 pass "
      "under PID: **%d / 6**.\n" % (int_sac_total, pid_sac_total, pid_offfloor_clear, pid_strict_cells))

    # ---- verdict ----
    overturned = (pid_sac_total <= int_sac_total * 0.34) and (pid_strict_cells >= 3)
    softened = (pid_sac_total < int_sac_total) and not overturned
    if overturned:
        verdict = ("**OVERTURNED.** Under PID the off-floor frontier becomes "
                   "essentially feasible: sacrifices collapse %d->%d and >=3 cells "
                   "reach near-strict 5/5. The old integral negative result was "
                   "substantially pseudo-infeasibility (limit-cycle mis-kills)." %
                   (int_sac_total, pid_sac_total))
    elif softened:
        verdict = ("**SOFTENED, not overturned.** PID removes part of the integral "
                   "sacrifice (%d->%d) and tightens the feasible cells, but the "
                   "frontier shape stands: the on-floor cell t8e10 and the single "
                   "cap-bound platoon(s) remain resource-limited, not cured by the "
                   "dual rule." % (int_sac_total, pid_sac_total))
    else:
        verdict = ("**UNCHANGED.** PID does not move the feasibility frontier "
                   "(sacrifices %d->%d); the old integral conclusion stands." %
                   (int_sac_total, pid_sac_total))
    w("## 3. Frontier verdict\n")
    w(verdict + "\n")

    w("## 4. Bottleneck diagnostic — do seed2-pl2 / seed3-pl0 recover at looser tau?\n")
    w("Each residual bottleneck tracked at eps=0.10, tau in {8,10,12} under PID "
      "(viol@tau, mean AoI, final lambda; SAT = lambda saturated at lam_max=%g => "
      "truly resource-limited):\n" % LAM_MAX)
    for row in bottleneck_diag([(2, 2), (3, 0)]):
        w("- **%s**: %s" % (row[0], " | ".join(row[1:])))
    w("")
    w("Reading: if viol falls and lambda comes OFF saturation as tau loosens, the "
      "platoon was tau-bound (recoverable); if lambda stays SAT with high AoI at "
      "all tau, it is structurally resource-limited (the `--aoi_floor` safeguard's "
      "job, not the dual's).\n")

    w("## 5. Caveats\n")
    w("- n=6 seeds/cell: cell means carry wide CIs; read sacrificed-count and the "
      "directional frontier, not single-cell point estimates.")
    w("- epsilon-soft, not literal hard: this is an *expected* violation-rate "
      "constraint (holds in long-run average after convergence), **satisfied up to "
      "violation probability eps**, not a per-slot guarantee.")
    w("- Scenario/config locked and identical to the integral grid (only the dual "
      "rule differs), so the PID-vs-integral shift is attributable to the dual.")
    w("- The retained global-critic gradient bug is unchanged (orthogonal to the "
      "local-actor constraint).\n")

    w("## 6. Reproduce\n")
    w("```")
    w("# from results_remote/, with ../.venv python")
    w("python analyze_phase_pid.py --seeds 2 3 4 5 6 7")
    w("```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[phase_pid] wrote", REPORT)
    print("[phase_pid] wrote", figpath)


if __name__ == "__main__":
    main()
