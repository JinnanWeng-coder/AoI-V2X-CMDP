"""
[RQ1-CMDP] WARM-start frozen-deployment eval analysis -- NUMBERS ONLY (no conclusions;
the operator cross-checks every value against the raw .mat; the warm numbers are the
load-bearing deployment claim).

The 2 canonical arms (soft base / per-platoon PID) x seeds {2..7}, eval-only WARM rerun
(env.AoI=1 steady-state start) loaded from each run's frozen checkpoints. Files live under
model/ep600_deploy/marl_model_<mode>_seed<s>_<tag>/.

Per (arm, seed):
  - TRAINING worst-platoon viol = viol_rate.mat[:, -100:].mean(axis=1).max()
  - COLD-A   worst viol = viol_rate_test.mat.max()                 (legacy cold boot, caveat)
  - WARM-A   worst viol = viol_rate_test_warm.mat.max(); power = power_test_warm.mat.mean()
  - WARM-B   per held-out seed h: viol_rate_test_warm_holdout_s{h}.max(); power ..._warm_holdout
SANITY:
  - each viol_rate_test_warm*.mat has 5 entries
  - cold *_test*.mat untouched (verified separately via the mtime snapshot)
Outputs results_remote/RQ1_DEPLOY_EVAL_WARM.md. Exit 2 if any of the 12 runs missing warm.
"""
import os
import sys
import numpy as np
import scipy.io

RR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))   # results_remote/
DEPLOY = os.path.join(RR, "..", "1-ModifiedMADDPGwithTDec", "model", "ep600_deploy")
REPORT = os.path.join(RR, "RQ1_DEPLOY_EVAL_WARM.md")
SEEDS = [2, 3, 4, 5, 6, 7]
HOLD = [12, 13, 14]
ARMS = [
    ("soft", "soft", "base_ep600_deploy"),
    ("pid",  "hard", "t8e10_pid_ep600_deploy"),
]


def rundir(mode, seed, tag):
    return os.path.join(DEPLOY, "marl_model_%s_seed%d_%s" % (mode, seed, tag))


def load(d, name, key):
    p = os.path.join(d, name)
    if not os.path.exists(p):
        return None
    return scipy.io.loadmat(p)[key]


def main():
    missing = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            if not os.path.exists(os.path.join(rundir(mode, s, tag),
                                                "viol_rate_test_warm_holdout_s14.mat")):
                missing.append("%s s%d" % (arm, s))
    if missing:
        sys.stderr.write("[deploy-warm] missing %d warm runs (e.g. %s) -- not writing report\n"
                         % (len(missing), missing[:5]))
        sys.exit(2)

    L = []; w = L.append
    w("# RQ1 — WARM-start frozen-deployment eval (corrected steady-state boot)\n")
    w("**Auto-generated on disk by `scripts/deploy_warm_driver.ps1` -> "
      "`scripts/analyze_deploy_warm.py`** (detached). NUMBERS ONLY; no conclusions drawn. "
      "The operator cross-checks the raw `.mat`; **the WARM numbers are the load-bearing "
      "deployment claim** (the cold synchronized AoI=100 boot deadlocked the greedy policy "
      "and is retained only as a documented caveat).\n")
    w("Eval-only WARM rerun (env.AoI=1 steady-state start) from each run's frozen "
      "checkpoints; canonical config (tau=8 eps=0.10 dual=pid lam_max=20 ep600), canonical "
      "scenario, seeds 2-7. Eval: 100 episodes, warmup 5, held-out seeds 12,13,14. "
      "TRAINING worst = `viol_rate.mat[:,-100:].mean(axis=1).max()`; WARM/COLD worst = "
      "`viol_rate_test[_warm].max()`; power = `power_test_warm.mat.mean()`.\n")

    # ---- main table ----
    w("## 1. Per-(arm, seed): training worst | cold-A worst | WARM-A worst/pow | WARM-B (s12/s13/s14) worst/pow\n")
    w("| arm | seed | train worst | cold-A worst | WARM-A worst/pow | WARM-B s12 | WARM-B s13 | WARM-B s14 |")
    w("|---|---|---|---|---|---|---|---|")
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            vr = load(d, "viol_rate.mat", "viol_rate").astype(np.float64)
            tw = float(vr[:, -100:].mean(axis=1).max())
            vc = load(d, "viol_rate_test.mat", "viol_rate_test").astype(np.float64)
            cw = float(vc.max())
            vw = load(d, "viol_rate_test_warm.mat", "viol_rate_test").astype(np.float64)
            pw = load(d, "power_test_warm.mat", "power_test").astype(np.float64)
            aw = float(vw.max()); ap = float(pw.mean())
            cols = []
            for h in HOLD:
                vh = load(d, "viol_rate_test_warm_holdout_s%d.mat" % h, "viol_rate_test").astype(np.float64)
                ph = load(d, "power_test_warm_holdout_s%d.mat" % h, "power_test").astype(np.float64)
                cols.append("%.3f / %.2f" % (float(vh.max()), float(ph.mean())))
            w("| %s | %d | %.3f | %.3f | %.3f / %.2f | %s | %s | %s |"
              % (arm, s, tw, cw, aw, ap, cols[0], cols[1], cols[2]))
    w("")

    # ---- pooled WARM-A summary ----
    w("## 2. Pooled WARM-A worst-platoon violation (over seeds 2-7)\n")
    for (arm, mode, tag) in ARMS:
        warm = []
        for s in SEEDS:
            vw = load(rundir(mode, s, tag), "viol_rate_test_warm.mat", "viol_rate_test").astype(np.float64)
            warm.append(float(vw.max()))
        w("- **%s**: WARM-A worst mean=%.3f std=%.3f (per-seed %s)"
          % (arm, float(np.mean(warm)), float(np.std(warm)),
             ", ".join("%.3f" % x for x in warm)))
    w("\n(training reference: soft ~0.35, pid ~0.13)\n")

    # ---- sanity ----
    w("## 3. Sanity checks\n")
    bad = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            vw = load(d, "viol_rate_test_warm.mat", "viol_rate_test")
            if vw.reshape(-1).shape[0] != 5:
                bad.append("%s s%d warm-A len=%d" % (arm, s, vw.reshape(-1).shape[0]))
            for h in HOLD:
                vh = load(d, "viol_rate_test_warm_holdout_s%d.mat" % h, "viol_rate_test")
                if vh.reshape(-1).shape[0] != 5:
                    bad.append("%s s%d warm-B s%d len=%d" % (arm, s, h, vh.reshape(-1).shape[0]))
    w("**(a) every viol_rate_test_warm*.mat has 5 entries:** %s\n"
      % ("ALL PASS" if not bad else "FAIL: " + "; ".join(bad)))
    w("**(b) cold *_test*.mat untouched:** verified out-of-band via the mtime/size snapshot "
      "(see commit message / driver log); warm code path only ever writes the `_warm` suffix.\n")

    w("## 4. Reproduce\n```\npython results_remote/scripts/analyze_deploy_warm.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[deploy-warm] wrote", REPORT)
    print("[deploy-warm] sanity warm-rows:", "PASS" if not bad else "FAIL")


if __name__ == "__main__":
    main()
