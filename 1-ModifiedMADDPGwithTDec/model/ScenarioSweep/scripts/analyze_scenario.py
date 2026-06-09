"""
[RQ1-CMDP] SCENARIO SWEEP analysis -- NUMBERS ONLY (no conclusions; the operator
cross-checks every value against the raw .mat and makes the load-vs-(viol,power) figure).

8 cells (n_RB in {2,3,4} x platoons in {4,5,6}, excluding nominal rb3/pl5) x 4 arms x
seeds {2,3,4}. Arms: soft base / per-platoon PID / global_max / fixed-w10 indicator.
All ep600, tau=8.

Per (cell, arm, seed):
  - worst-platoon violation = viol_rate.mat[:, -100:].mean(axis=1).max()   (per the spec)
  - mean Tx power           = power.mat.mean()
SANITY:
  - n_platoon rows: viol_rate.mat rows == platoons P (auto-sizing worked)
  - global_max: lambda.mat rows identical across platoons each episode
  - fixed-w10 (soft): lambda.mat == 0
Outputs model/ScenarioSweep/RQ1_SCENARIO_SWEEP.md. Exit 2 if any of the 96 runs missing.
"""
import os
import sys
import numpy as np
import scipy.io

# this script lives in model/ScenarioSweep/scripts/ -> the sweep root (which holds
# both the 96 run dirs AND the report) is one up.
SS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MODEL = SS                          # the 96 marl_model_*_rb*_pl* dirs live here
REPORT = os.path.join(SS, "RQ1_SCENARIO_SWEEP.md")
SEEDS = [2, 3, 4]
# cells (rb, pl) in priority order
CELLS = [(2, 6), (2, 5), (2, 4), (3, 4), (3, 6), (4, 4), (4, 5), (4, 6)]
# arm -> (mode, tag-stem, kind)
ARMS = [
    ("soft_base", "soft", "base_ep600"),
    ("pid",       "hard", "t8e10_pid_ep600"),
    ("glmax",     "hard", "t8e10_pid_ep600_glmax"),
    ("qind_w10",  "soft", "qind_w10_ep600"),
]


def rundir(mode, seed, stem, rb, pl):
    return os.path.join(MODEL, "marl_model_%s_seed%d_%s_rb%d_pl%d" % (mode, seed, stem, rb, pl))


def load(d, name, key):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return None
    return scipy.io.loadmat(p)[key]


def main():
    # presence gate
    missing = []
    for (rb, pl) in CELLS:
        for (arm, mode, stem) in ARMS:
            for s in SEEDS:
                if not os.path.exists(os.path.join(rundir(mode, s, stem, rb, pl), "viol_rate.mat")):
                    missing.append("%s s%d rb%d pl%d" % (arm, s, rb, pl))
    if missing:
        sys.stderr.write("[scenario] missing %d runs (e.g. %s) -- not writing report\n"
                         % (len(missing), missing[:5]))
        sys.exit(2)

    L = []; w = L.append
    w("# RQ1 — scenario sweep (resource-frontier supplement)\n")
    w("**Auto-generated on disk by `scripts/scenario_driver.ps1` -> "
      "`scripts/analyze_scenario.py`** (detached). NUMBERS ONLY; no conclusions drawn. "
      "Operator cross-checks the raw `.mat` and makes the load-vs-(viol,power) figure.\n")
    w("Varies ONLY the scenario (n_RB, n_veh); locked CMDP config fixed (tau=8 eps=0.10 "
      "dual=pid kp=ki=1.0 kd=0.5 lam_max=20 ep600). 8 cells (n_RB in {2,3,4} x platoons "
      "in {4,5,6}, excluding nominal rb3/pl5) x 4 arms x seeds {2,3,4} = 96 runs. "
      "worst-platoon violation = `viol_rate.mat[:,-100:].mean(axis=1).max()`; mean power "
      "= `power.mat.mean()`.\n")

    # ---- main table ----
    w("## 1. Per-(cell, arm, seed): worst-platoon violation | mean Tx power (dBm)\n")
    w("| cell (rb,pl) | arm | seed2 viol/pow | seed3 viol/pow | seed4 viol/pow |")
    w("|---|---|---|---|---|")
    for (rb, pl) in CELLS:
        for (arm, mode, stem) in ARMS:
            cells = []
            for s in SEEDS:
                d = rundir(mode, s, stem, rb, pl)
                vr = load(d, "viol_rate.mat", "viol_rate").astype(np.float64)
                pw = load(d, "power.mat", "power").astype(np.float64)
                worst = float(vr[:, -100:].mean(axis=1).max())
                cells.append("%.3f / %.2f" % (worst, pw.mean()))
            w("| rb%d,pl%d | %s | %s | %s | %s |" % (rb, pl, arm, cells[0], cells[1], cells[2]))
    w("")

    # ---- sanity ----
    w("## 2. Sanity checks\n")
    # (a) n_platoon rows
    bad_rows = []
    for (rb, pl) in CELLS:
        for (arm, mode, stem) in ARMS:
            for s in SEEDS:
                vr = load(rundir(mode, s, stem, rb, pl), "viol_rate.mat", "viol_rate")
                if vr.shape[0] != pl:
                    bad_rows.append("%s s%d rb%d pl%d rows=%d" % (arm, s, rb, pl, vr.shape[0]))
    w("**(a) n_platoon rows == P (auto-sizing):** %s\n"
      % ("ALL PASS (every viol_rate.mat has P rows)" if not bad_rows else "FAIL: " + "; ".join(bad_rows)))
    # (b) global_max lambda identical across platoons
    glmax_bad = []
    glmax_maxspread = 0.0
    for (rb, pl) in CELLS:
        for s in SEEDS:
            lam = load(rundir("hard", s, "t8e10_pid_ep600_glmax", rb, pl), "lambda.mat", "lambda").astype(np.float64)
            spread = float((lam.max(axis=0) - lam.min(axis=0)).max())
            glmax_maxspread = max(glmax_maxspread, spread)
            if spread != 0.0:
                glmax_bad.append("s%d rb%d pl%d spread=%.2e" % (s, rb, pl, spread))
    w("**(b) global_max lambda identical across platoons:** %s (max spread over all "
      "glmax runs = %.2e)\n" % ("ALL PASS" if not glmax_bad else "FAIL: " + "; ".join(glmax_bad), glmax_maxspread))
    # (c) fixed-w10 lambda == 0
    qind_bad = []
    qind_absmax = 0.0
    for (rb, pl) in CELLS:
        for s in SEEDS:
            lam = load(rundir("soft", s, "qind_w10_ep600", rb, pl), "lambda.mat", "lambda").astype(np.float64)
            a = float(np.abs(lam).max())
            qind_absmax = max(qind_absmax, a)
            if a != 0.0:
                qind_bad.append("s%d rb%d pl%d max|lam|=%.2e" % (s, rb, pl, a))
    w("**(c) fixed-w10 (soft) lambda == 0:** %s (max |lambda| over all qind runs = %.2e)\n"
      % ("ALL PASS" if not qind_bad else "FAIL: " + "; ".join(qind_bad), qind_absmax))

    w("## 3. Reproduce\n```\npython 1-ModifiedMADDPGwithTDec/model/ScenarioSweep/scripts/analyze_scenario.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[scenario] wrote", REPORT)
    print("[scenario] sanity rows/glmax/qind:",
          "PASS" if not bad_rows else "FAIL",
          "PASS" if not glmax_bad else "FAIL",
          "PASS" if not qind_bad else "FAIL")


if __name__ == "__main__":
    main()
