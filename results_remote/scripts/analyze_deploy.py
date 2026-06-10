"""
[RQ1-CMDP] FROZEN-DEPLOYMENT eval analysis -- NUMBERS ONLY (no conclusions; the operator
cross-checks every value against the raw .mat).

2 canonical arms (soft base / per-platoon PID) x seeds {2..7}, each re-trained into a
*_deploy dir + a frozen-policy eval (A in-distribution, B held-out seeds 12,13,14).

Per (arm, seed):
  - TRAINING worst-platoon viol = viol_rate.mat[:, -100:].mean(axis=1).max()  (claims 1-3 self-check)
  - DEPLOY-A  worst viol = viol_rate_test.mat.max(); power = power_test.mat.mean()
  - DEPLOY-B  per held-out seed h: viol_rate_test_holdout_s{h}.max(); power_test_holdout_s{h}.mean()
SANITY:
  - each *_test.mat has n_platoon=5 rows (AoI_evolution_test rows; viol_rate_test length)
  - reward_cost.mat[:, -100:].mean ~= viol_rate.mat[:, -100:].mean  (logging cross-check)
  - reward_total.mat == reward_t1 + reward_t2
  - TRAINING worst reproduces canonical (soft ~0.35, pid ~0.13) -- pooled means reported
  - soft-deploy lambda == 0 (no dual)
Outputs results_remote/RQ1_DEPLOY_EVAL_AB.md. Exit 2 if any of the 12 runs missing.
"""
import os
import sys
import numpy as np
import scipy.io

RR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))   # results_remote/
MODEL = os.path.join(RR, "..", "1-ModifiedMADDPGwithTDec", "model")
REPORT = os.path.join(RR, "RQ1_DEPLOY_EVAL_AB.md")
SEEDS = [2, 3, 4, 5, 6, 7]
HOLD = [12, 13, 14]
ARMS = [
    ("soft", "soft", "base_ep600_deploy"),
    ("pid",  "hard", "t8e10_pid_ep600_deploy"),
]


def rundir(mode, seed, tag):
    return os.path.join(MODEL, "marl_model_%s_seed%d_%s" % (mode, seed, tag))


def load(d, name, key):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return None
    return scipy.io.loadmat(p)[key]


def main():
    # presence gate (require the LAST eval-B file for every run)
    missing = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            if not os.path.exists(os.path.join(rundir(mode, s, tag), "viol_rate_test_holdout_s14.mat")):
                missing.append("%s s%d" % (arm, s))
    if missing:
        sys.stderr.write("[deploy] missing %d runs (e.g. %s) -- not writing report\n"
                         % (len(missing), missing[:5]))
        sys.exit(2)

    L = []; w = L.append
    w("# RQ1 — frozen-deployment eval (Experiment A in-distribution / B held-out)\n")
    w("**Auto-generated on disk by `scripts/deploy_driver.ps1` -> `scripts/analyze_deploy.py`** "
      "(detached). NUMBERS ONLY; no conclusions drawn. Operator cross-checks the raw `.mat`.\n")
    w("Re-train the 2 canonical arms into NEW `*_deploy` dirs (canonical `_ep600` runs "
      "untouched), then append a FROZEN-policy eval (actor noise=0, no learning/dual/buffer; "
      "AoI reset + warmup discarded). Locked config (tau=8 eps=0.10 dual=pid kp=ki=1.0 kd=0.5 "
      "lam_max=20 ep600), canonical scenario (5 platoons x 4 veh x 3 RB), seeds 2-7. Eval: 100 "
      "episodes, warmup 5, held-out seeds 12,13,14. TRAINING worst = "
      "`viol_rate.mat[:,-100:].mean(axis=1).max()`; DEPLOY worst = `viol_rate_test.max()`; "
      "power = `power_test.mat.mean()`.\n")

    # ---- main table ----
    w("## 1. Per-(arm, seed): training worst | deploy-A worst/pow | deploy-B (s12/s13/s14) worst/pow\n")
    w("| arm | seed | train worst | A worst / pow | B s12 worst/pow | B s13 worst/pow | B s14 worst/pow |")
    w("|---|---|---|---|---|---|---|")
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            vr = load(d, "viol_rate.mat", "viol_rate").astype(np.float64)
            tw = float(vr[:, -100:].mean(axis=1).max())
            va = load(d, "viol_rate_test.mat", "viol_rate_test").astype(np.float64)
            pa = load(d, "power_test.mat", "power_test").astype(np.float64)
            aw = float(va.max()); ap = float(pa.mean())
            cols = []
            for h in HOLD:
                vh = load(d, "viol_rate_test_holdout_s%d.mat" % h, "viol_rate_test").astype(np.float64)
                ph = load(d, "power_test_holdout_s%d.mat" % h, "power_test").astype(np.float64)
                cols.append("%.3f / %.2f" % (float(vh.max()), float(ph.mean())))
            w("| %s | %d | %.3f | %.3f / %.2f | %s | %s | %s |"
              % (arm, s, tw, aw, ap, cols[0], cols[1], cols[2]))
    w("")

    # ---- pooled training self-check (claims 1-3) ----
    w("## 2. Training-time self-check (pooled over seeds 2-7)\n")
    for (arm, mode, tag) in ARMS:
        worst = []
        for s in SEEDS:
            vr = load(rundir(mode, s, tag), "viol_rate.mat", "viol_rate").astype(np.float64)
            worst.append(float(vr[:, -100:].mean(axis=1).max()))
        w("- **%s**: training worst-platoon viol mean=%.3f std=%.3f (per-seed %s)"
          % (arm, float(np.mean(worst)), float(np.std(worst)),
             ", ".join("%.3f" % x for x in worst)))
    w("\n(canonical reference: soft ~0.35, pid ~0.13)\n")

    # ---- sanity ----
    w("## 3. Sanity checks\n")
    # (a) *_test rows == 5
    bad_rows = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            ae = load(d, "AoI_evolution_test.mat", "AoI_evolution_test")
            va = load(d, "viol_rate_test.mat", "viol_rate_test")
            if ae.shape[0] != 5:
                bad_rows.append("%s s%d A-evo rows=%d" % (arm, s, ae.shape[0]))
            if va.reshape(-1).shape[0] != 5:
                bad_rows.append("%s s%d viol_test len=%d" % (arm, s, va.reshape(-1).shape[0]))
            for h in HOLD:
                vh = load(d, "viol_rate_test_holdout_s%d.mat" % h, "viol_rate_test")
                if vh.reshape(-1).shape[0] != 5:
                    bad_rows.append("%s s%d B-s%d len=%d" % (arm, s, h, vh.reshape(-1).shape[0]))
    w("**(a) every *_test has n_platoon=5:** %s\n"
      % ("ALL PASS" if not bad_rows else "FAIL: " + "; ".join(bad_rows)))

    # (b) reward_cost ~= viol_rate (both last-100, per-platoon)
    cost_maxdiff = 0.0; cost_rows = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            rc = load(d, "reward_cost.mat", "reward_cost").astype(np.float64)
            vr = load(d, "viol_rate.mat", "viol_rate").astype(np.float64)
            diff = float(np.abs(rc[:, -100:].mean(axis=1) - vr[:, -100:].mean(axis=1)).max())
            cost_maxdiff = max(cost_maxdiff, diff)
            cost_rows.append("%s s%d %.3e" % (arm, s, diff))
    w("**(b) reward_cost[:, -100:].mean ~= viol_rate[:, -100:].mean:** max abs diff over all "
      "runs = %.3e (per-run: %s)\n" % (cost_maxdiff, "; ".join(cost_rows)))

    # (c) reward_total == reward_t1 + reward_t2
    tot_maxdiff = 0.0
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            rt = load(d, "reward_total.mat", "reward_total").astype(np.float64)
            r1 = load(d, "reward_t1.mat", "reward_t1").astype(np.float64)
            r2 = load(d, "reward_t2.mat", "reward_t2").astype(np.float64)
            tot_maxdiff = max(tot_maxdiff, float(np.abs(rt - (r1 + r2)).max()))
    w("**(c) reward_total == reward_t1 + reward_t2:** max abs diff over all runs = %.3e\n"
      % tot_maxdiff)

    # (d) soft-deploy lambda == 0
    lam_absmax = 0.0; lam_bad = []
    for s in SEEDS:
        lam = load(rundir("soft", s, "base_ep600_deploy"), "lambda.mat", "lambda").astype(np.float64)
        a = float(np.abs(lam).max())
        lam_absmax = max(lam_absmax, a)
        if a != 0.0:
            lam_bad.append("s%d max|lam|=%.2e" % (s, a))
    w("**(d) soft-deploy lambda == 0:** %s (max |lambda| over soft runs = %.2e)\n"
      % ("ALL PASS" if not lam_bad else "FAIL: " + "; ".join(lam_bad), lam_absmax))

    w("## 4. Reproduce\n```\npython results_remote/scripts/analyze_deploy.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[deploy] wrote", REPORT)
    print("[deploy] sanity rows/cost/total/lambda:",
          "PASS" if not bad_rows else "FAIL",
          "%.1e" % cost_maxdiff, "%.1e" % tot_maxdiff,
          "PASS" if not lam_bad else "FAIL")


if __name__ == "__main__":
    main()
