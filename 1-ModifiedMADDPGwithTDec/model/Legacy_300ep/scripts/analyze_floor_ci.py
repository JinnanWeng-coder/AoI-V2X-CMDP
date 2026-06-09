"""
[RQ1-CMDP] EXP1 (PID + aoi_floor) + EXP2 (n=10 CI) analysis + report.

EXP1: does --aoi_floor 0.005 BOUND the truly-infeasible seed2-pl2 (lambda-saturated
under PID) without harming feasible platoons? Compares seeds {2,3,4} no-floor
(t8e10_pid) vs floor (t8e10_pid_floor), per platoon: violation, mean AoI, final lambda.

EXP2: re-evaluate the CI-critical cells {t8e10,t10e10,t12e10} at eps=0.10 with the
EXPANDED seed set {2..11} (n=10) for both duals, plus soft baseline, to see whether
the n=6 phase claims survive: #pass/5, worst-feasible violation, and the soft-vs-hard
worst-platoon gap, each with a 95% t-CI; PID vs integral side by side; n=6 vs n=10.

All per-platoon violation recomputed at each cell's tau from AoI_evolution.mat
(analyze_remote.metrics). Outputs under results_remote/:
  fig_pid_floor.png, RQ1_FLOOR_AND_CI_REPORT.md.
Refuses to write the report unless all required runs are present (exit 2). No git.
"""
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from analyze_remote import metrics, folder

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPORT = os.path.join(HERE, "RQ1_FLOOR_AND_CI_REPORT.md")
EPS = 0.10
LAM_MAX = 20.0
SACR = 0.5
CELLS = [8, 10, 12]                       # tau values, all at eps=0.10
SEEDS6 = [2, 3, 4, 5, 6, 7]
SEEDS10 = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
T_CRIT = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447,
          8: 2.365, 9: 2.306, 10: 2.262, 11: 2.228, 12: 2.201}


def ci95(arr):
    arr = np.asarray([a for a in arr if a is not None and not np.isnan(a)], dtype=np.float64)
    n = arr.size
    if n == 0:
        return float("nan"), 0.0
    m = arr.mean()
    if n < 2:
        return float(m), 0.0
    sd = arr.std(ddof=1)
    return float(m), float(T_CRIT.get(n, 1.96) * sd / np.sqrt(n))


def tag(tau, dual, floor=False):
    t = "t%de10" % tau
    if dual == "pid":
        t += "_pid"
    if floor:
        t += "_floor"
    return t


# ------------------------ EXP1 ------------------------ #
def exp1_rows():
    out = []
    for s in (2, 3, 4):
        mn = metrics("hard", s, "t8e10_pid", 8)          # no-floor PID
        mf = metrics("hard", s, "t8e10_pid_floor", 8)    # PID + floor
        if mn is None or mf is None:
            return None
        out.append((s, mn, mf))
    return out


def exp1_figure(rows):
    seeds = [r[0] for r in rows]
    # worst-platoon violation and worst-platoon AoI, no-floor vs floor
    wv_n = [r[1]["viol"].max() for r in rows]
    wv_f = [r[2]["viol"].max() for r in rows]
    wa_n = [r[1]["aoi"].max() for r in rows]
    wa_f = [r[2]["aoi"].max() for r in rows]
    x = np.arange(len(seeds)); w = 0.38
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].bar(x - w/2, wv_n, w, label="no-floor", color="#c44")
    ax[0].bar(x + w/2, wv_f, w, label="floor 0.005", color="#4a4")
    ax[0].axhline(EPS, ls="--", color="k", lw=1, label=r"$\epsilon=0.10$")
    ax[0].set_xticks(x); ax[0].set_xticklabels(["s%d" % s for s in seeds])
    ax[0].set_title("worst-platoon violation"); ax[0].set_ylabel("P(AoI>8)")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3, axis="y")
    ax[1].bar(x - w/2, wa_n, w, label="no-floor", color="#c44")
    ax[1].bar(x + w/2, wa_f, w, label="floor 0.005", color="#4a4")
    ax[1].set_xticks(x); ax[1].set_xticklabels(["s%d" % s for s in seeds])
    ax[1].set_title("worst-platoon mean AoI (slots)"); ax[1].set_ylabel("AoI")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3, axis="y")
    fig.suptitle("EXP1: PID + --aoi_floor 0.005 vs no-floor (seeds 2,3,4)")
    fig.tight_layout()
    f = os.path.join(HERE, "fig_pid_floor.png")
    fig.savefig(f, dpi=150); plt.close(fig)
    return f


# ------------------------ EXP2 ------------------------ #
def cell_pass_worst(seeds, tau, dual):
    """Return per-seed (n_pass, worst_feasible) lists for one cell."""
    npass, worst = [], []
    for s in seeds:
        mm = metrics("hard", s, tag(tau, dual), tau)
        if mm is None:
            continue
        viol = mm["viol"]
        npass.append(int(np.sum(viol <= EPS + 1e-9)))
        feas = viol[viol <= EPS + SACR]
        worst.append(float(feas.max()) if feas.size else float("nan"))
    return npass, worst


def soft_hard_gap(seeds, tau):
    """Per-seed (soft worst-platoon viol@tau) - (hard PID worst-platoon viol@tau)."""
    gaps, soft_w, hard_w = [], [], []
    for s in seeds:
        ms = metrics("soft", s, "base", tau)
        mh = metrics("hard", s, tag(tau, "pid"), tau)
        if ms is None or mh is None:
            continue
        sw = float(ms["viol"].max()); hw = float(mh["viol"].max())
        soft_w.append(sw); hard_w.append(hw); gaps.append(sw - hw)
    return gaps, soft_w, hard_w


def present_count(seeds, tau, dual):
    return sum(metrics("hard", s, tag(tau, dual), tau) is not None for s in seeds)


def main():
    # ---- presence gate ----
    missing = []
    for s in (2, 3, 4):
        if metrics("hard", s, "t8e10_pid_floor", 8) is None:
            missing.append("floor s%d" % s)
    for tau in CELLS:
        for dual in ("pid", "integral"):
            for s in (8, 9, 10, 11):
                if metrics("hard", s, tag(tau, dual), tau) is None:
                    missing.append("%s s%d" % (tag(tau, dual), s))
    for s in (8, 9, 10, 11):
        if metrics("soft", s, "base", 8) is None:
            missing.append("soft s%d" % s)
    if missing:
        sys.stderr.write("[floor_ci] missing %d runs (e.g. %s) -- not writing report\n"
                         % (len(missing), ", ".join(missing[:6])))
        sys.exit(2)

    rows = exp1_rows()
    figpath = exp1_figure(rows)

    L = []; w = L.append
    w("# RQ1 — EXP1 (PID + aoi_floor) and EXP2 (n=10 CI tightening)\n")
    w("**Auto-generated on disk by `floor_ci_driver.ps1` -> `analyze_floor_ci.py`** "
      "(detached, independent of the agent session). Commit left to the operator.\n")
    w("Locked base (do NOT recalibrate): episodes=300, eta_lam=1.0, lam_max=20, PID "
      "gains kp=1.0 ki=1.0 kd=0.5, scenario 5 platoons x 4 veh x 3 RB, eps=0.10. "
      "Per-platoon violation recomputed at each cell's tau from `AoI_evolution.mat`, "
      "last-100-ep.\n")

    # ---------------- EXP1 ----------------
    w("## EXP1 — does --aoi_floor 0.005 bound the truly-infeasible seed2-pl2 under PID?\n")
    w("Closes the loop: PID removes pseudo-infeasibility (phase study); the floor "
      "handles the ONE residual TRUE infeasibility (seed2-pl2, lambda-saturated ~20 at "
      "every tau). Per-platoon, no-floor (`t8e10_pid`) -> floor (`t8e10_pid_floor`): "
      "violation, mean AoI, final lambda.\n")
    for (s, mn, mf) in rows:
        w("**seed %d** (no-floor -> floor):\n" % s)
        w("| platoon | viol | mean AoI | final lambda |")
        w("|---|---|---|---|")
        P = mn["P"]
        for j in range(P):
            ln = mn["lam_final"][j] if mn["lam_final"] is not None else float("nan")
            lf = mf["lam_final"][j] if mf["lam_final"] is not None else float("nan")
            w("| pl%d | %.3f -> %.3f | %.1f -> %.1f | %.1f -> %.1f |" %
              (j, mn["viol"][j], mf["viol"][j], mn["aoi"][j], mf["aoi"][j], ln, lf))
        w("| **net** | %.3f -> %.3f | %.1f -> %.1f | worst-pl viol %.3f -> %.3f |" %
          (mn["viol"].mean(), mf["viol"].mean(), mn["aoi"].mean(), mf["aoi"].mean(),
           mn["viol"].max(), mf["viol"].max()))
        w("")
    # EXP1 verdict numbers (seed2 is the infeasible headline; pl2 index 2)
    s2n, s2f = rows[0][1], rows[0][2]
    pl2_aoi_n, pl2_aoi_f = s2n["aoi"][2], s2f["aoi"][2]
    pl2_v_n, pl2_v_f = s2n["viol"][2], s2f["viol"][2]
    # feasible-platoon harm check across seeds 3,4 (and seed2 feasible pls)
    harmed = []
    for (s, mn, mf) in rows:
        for j in range(mn["P"]):
            if mn["viol"][j] <= EPS + 1e-9 and mf["viol"][j] > EPS + 0.01:
                harmed.append("s%dpl%d(%.3f->%.3f)" % (s, j, mn["viol"][j], mf["viol"][j]))
    w("**EXP1 verdict:** seed2-pl2 (the truly-infeasible platoon) AoI %.1f -> %.1f "
      "slots, viol %.3f -> %.3f under the floor. Feasible platoons pushed above eps "
      "by >0.01: %s. So the floor %s bounds the unservable platoon %s harming feasible "
      "ones.\n" % (pl2_aoi_n, pl2_aoi_f, pl2_v_n, pl2_v_f, (harmed or "NONE"),
                   "bounds" if pl2_aoi_f < pl2_aoi_n else "does NOT improve",
                   "without" if not harmed else "but DOES"))

    # ---------------- EXP2 ----------------
    w("## EXP2 — do the phase claims survive at n=10? (seeds 2-11)\n")
    w("CI-critical cells at eps=0.10, both duals, n=6 (seeds 2-7) vs n=10 (seeds 2-11).\n")
    w("### #platoons passing (<=eps) per cell\n")
    w("| cell | integral n=6 | integral n=10 | pid n=6 | pid n=10 |")
    w("|---|---|---|---|---|")
    pass10 = {}
    for tau in CELLS:
        i6 = ci95(cell_pass_worst(SEEDS6, tau, "integral")[0])
        i10 = ci95(cell_pass_worst(SEEDS10, tau, "integral")[0])
        p6 = ci95(cell_pass_worst(SEEDS6, tau, "pid")[0])
        p10v = cell_pass_worst(SEEDS10, tau, "pid")[0]
        p10 = ci95(p10v)
        pass10[tau] = (i10, p10)
        w("| t%de10 | %.2f +- %.2f | %.2f +- %.2f | %.2f +- %.2f | **%.2f +- %.2f** |" %
          (tau, i6[0], i6[1], i10[0], i10[1], p6[0], p6[1], p10[0], p10[1]))
    w("")
    w("### worst-feasible violation per cell (n=10)\n")
    w("| cell | integral n=10 | pid n=10 |")
    w("|---|---|---|")
    for tau in CELLS:
        iw = ci95(cell_pass_worst(SEEDS10, tau, "integral")[1])
        pw = ci95(cell_pass_worst(SEEDS10, tau, "pid")[1])
        w("| t%de10 | %.3f +- %.3f | %.3f +- %.3f |" % (tau, iw[0], iw[1], pw[0], pw[1]))
    w("")
    w("### soft-vs-hard(PID) worst-platoon violation gap (n=10)\n")
    w("Per seed: soft worst-platoon P(AoI>tau) minus hard-PID worst-platoon "
      "P(AoI>tau); positive = hard protects the worst-served platoon.\n")
    w("| cell | soft worst | hard-PID worst | gap (mean +- 95%CI) |")
    w("|---|---|---|---|")
    for tau in CELLS:
        gaps, sw, hw = soft_hard_gap(SEEDS10, tau)
        gm, gc = ci95(gaps)
        w("| t%de10 | %.3f | %.3f | **%.3f +- %.3f** |" %
          (tau, np.nanmean(sw), np.nanmean(hw), gm, gc))
    w("")
    # EXP2 verdict
    t8 = pass10[8]
    sep = (t8[1][0] - t8[1][1]) > (t8[0][0] + t8[0][1])  # pid lower CI > integral upper CI?
    any_strict = any(pass10[tau][1][0] >= 4.5 for tau in CELLS)
    w("**EXP2 verdict:** at n=10, t8e10 #pass integral %.2f vs PID %.2f "
      "(%s separated by 95%% CI). Any CI-cell reaching >=4.5/5 mean pass at n=10: "
      "%s. The n=6 phase claims %s at n=10.\n" %
      (t8[0][0], t8[1][0], "CLEARLY" if sep else "NOT cleanly",
       "YES" if any_strict else "NO",
       "hold" if (t8[1][0] > t8[0][0]) else "weaken"))

    w("## Caveats\n")
    w("- epsilon-soft: *expected* violation-rate constraint, **satisfied up to "
      "violation probability eps**, not a per-slot guarantee.")
    w("- Still a single 3-RB / 5-platoon / 4-veh scenario; CIs are over seeds, not "
      "over scenarios.")
    w("- Retained global-critic gradient bug unchanged (orthogonal to the local-actor "
      "constraint).\n")
    w("## Reproduce\n```\npython analyze_floor_ci.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[floor_ci] wrote", REPORT)
    print("[floor_ci] wrote", figpath)


if __name__ == "__main__":
    main()
