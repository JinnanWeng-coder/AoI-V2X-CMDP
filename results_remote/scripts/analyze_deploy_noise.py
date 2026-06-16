"""
[RQ1-CMDP] STOCHASTIC-policy deployment eval analysis -- NUMBERS ONLY (no conclusions; the
operator cross-checks every value against the raw .mat; the sigma=0.3 numbers are the
load-bearing deployment claim).

The 2 canonical arms (soft base / per-platoon PID) x seeds {2..7}, eval-only WARM rerun of
the CERTIFIED STOCHASTIC policy mu(s)+N(0,sigma) for sigma in {0.05,0.1,0.3}, loaded from
each run's frozen checkpoints. Files under model/ep600_deploy/marl_model_<mode>_seed<s>_<tag>/,
suffix _warm_n{5,10,30}. The sigma=0 (deterministic warm) number is the baseline column.

Per (arm, seed, sigma) for A (in-dist) and B (held-out s12/s13/s14):
  worst-platoon viol = viol_rate_test_warm[_n<NN>][_holdout_s<h>].max()
  mean power         = power_test_warm[_n<NN>][_holdout_s<h>].mean()
Outputs results_remote/RQ1_DEPLOY_EVAL_NOISE.md. Exit 2 if any of the 36 passes missing.
"""
import os
import sys
import numpy as np
import scipy.io

RR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))   # results_remote/
DEPLOY = os.path.join(RR, "..", "1-ModifiedMADDPGwithTDec", "model", "ep600_deploy")
REPORT = os.path.join(RR, "RQ1_DEPLOY_EVAL_NOISE.md")
SEEDS = [2, 3, 4, 5, 6, 7]
HOLD = [12, 13, 14]
SIGMAS = [(0.0, ""), (0.05, "_n5"), (0.1, "_n10"), (0.3, "_n30")]   # (sigma, file-suffix); 0 = deterministic baseline
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
    m = scipy.io.loadmat(p)
    return m[key]


def metric(d, kind, nsfx, hsfx):
    # kind 'viol' or 'pow'; returns (worst-or-mean) float or None if missing
    if kind == 'viol':
        a = load(d, "viol_rate_test_warm%s%s.mat" % (nsfx, hsfx), "viol_rate_test")
        return None if a is None else float(a.astype(np.float64).max())
    a = load(d, "power_test_warm%s%s.mat" % (nsfx, hsfx), "power_test")
    return None if a is None else float(a.astype(np.float64).mean())


def main():
    # presence gate: every (arm,seed,sigma>0) must have its B-s14 file
    missing = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            for (sig, nsfx) in SIGMAS:
                if sig == 0.0:
                    continue
                if not os.path.exists(os.path.join(d, "viol_rate_test_warm%s_holdout_s14.mat" % nsfx)):
                    missing.append("%s s%d %s" % (arm, s, nsfx))
    if missing:
        sys.stderr.write("[deploy-noise] missing %d passes (e.g. %s) -- not writing report\n"
                         % (len(missing), missing[:6]))
        sys.exit(2)

    L = []; w = L.append
    w("# RQ1 — STOCHASTIC-policy deployment eval (certified policy mu(s)+N(0,sigma))\n")
    w("**Auto-generated on disk by `scripts/deploy_noise_driver.ps1` -> "
      "`scripts/analyze_deploy_noise.py`** (detached). NUMBERS ONLY; no conclusions drawn. "
      "The operator cross-checks the raw `.mat`; **the sigma=0.3 numbers are the load-bearing "
      "deployment claim.**\n")
    w("Decisive test: deploy the policy the CMDP actually certified (stochastic actor "
      "`mu(s)+N(0,sigma)`) instead of its greedy determinization. Eval-only WARM rerun "
      "(env.AoI=1) from each run's frozen checkpoints; canonical config (tau=8 eps=0.10 "
      "dual=pid ep600), canonical scenario, seeds 2-7. Eval: 100 episodes, warmup 5, held-out "
      "seeds 12,13,14. sigma swept {0.05,0.1,0.3}; **sigma=0 column = deterministic warm "
      "baseline** (greedy). worst = `viol_rate_test_warm[_nNN][_holdout].max()`; power = "
      "`power_test_warm[...].mean()`.\n")

    sig_hdr = " | ".join("s=%.2g %s" % (sig, "(det)" if sig == 0 else "") for (sig, _) in SIGMAS)

    # ---- A in-distribution ----
    w("## 1. Eval A (in-distribution): worst-platoon viol / mean power, per sigma\n")
    w("| arm | seed | " + " | ".join("s=%.2g viol/pow" % sig for (sig, _) in SIGMAS) + " |")
    w("|---|---|" + "---|" * len(SIGMAS))
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            cells = []
            for (sig, nsfx) in SIGMAS:
                v = metric(d, 'viol', nsfx, ""); p = metric(d, 'pow', nsfx, "")
                cells.append("%.3f / %.2f" % (v, p) if v is not None else "  -  ")
            w("| %s | %d | %s |" % (arm, s, " | ".join(cells)))
    w("")

    # ---- B held-out (one block per held-out seed) ----
    for h in HOLD:
        w("## 2.%d Eval B (held-out seed %d): worst-platoon viol / mean power, per sigma\n" % (h - 11, h))
        w("| arm | seed | " + " | ".join("s=%.2g viol/pow" % sig for (sig, _) in SIGMAS) + " |")
        w("|---|---|" + "---|" * len(SIGMAS))
        hsfx = "_holdout_s%d" % h
        for (arm, mode, tag) in ARMS:
            for s in SEEDS:
                d = rundir(mode, s, tag)
                cells = []
                for (sig, nsfx) in SIGMAS:
                    v = metric(d, 'viol', nsfx, hsfx); p = metric(d, 'pow', nsfx, hsfx)
                    cells.append("%.3f / %.2f" % (v, p) if v is not None else "  -  ")
                w("| %s | %d | %s |" % (arm, s, " | ".join(cells)))
        w("")

    # ---- pooled A summary per sigma ----
    w("## 3. Pooled eval-A worst-platoon violation (over seeds 2-7), per arm x sigma\n")
    w("| arm | " + " | ".join("s=%.2g" % sig for (sig, _) in SIGMAS) + " |")
    w("|---|" + "---|" * len(SIGMAS))
    for (arm, mode, tag) in ARMS:
        cells = []
        for (sig, nsfx) in SIGMAS:
            vals = [metric(rundir(mode, s, tag), 'viol', nsfx, "") for s in SEEDS]
            vals = [v for v in vals if v is not None]
            cells.append("%.3f+-%.3f" % (float(np.mean(vals)), float(np.std(vals))) if vals else "-")
        w("| %s | %s |" % (arm, " | ".join(cells)))
    w("\n(training reference: soft ~0.35, pid ~0.13)\n")

    # ---- sanity ----
    w("## 4. Sanity checks\n")
    bad = []
    for (arm, mode, tag) in ARMS:
        for s in SEEDS:
            d = rundir(mode, s, tag)
            for (sig, nsfx) in SIGMAS:
                if sig == 0.0:
                    continue
                for hsfx in [""] + ["_holdout_s%d" % h for h in HOLD]:
                    a = load(d, "viol_rate_test_warm%s%s.mat" % (nsfx, hsfx), "viol_rate_test")
                    if a is None or a.reshape(-1).shape[0] != 5:
                        bad.append("%s s%d %s%s" % (arm, s, nsfx, hsfx))
    w("**(a) every viol_rate_test_warm_n*.mat has 5 entries:** %s\n"
      % ("ALL PASS" if not bad else "FAIL: " + "; ".join(bad)))
    w("**(b) deterministic *_test_warm* + cold *_test* untouched:** verified out-of-band via "
      "the mtime/size snapshot (see commit message / driver log); the noise path only ever "
      "writes the `_n{5,10,30}` suffix.\n")

    w("## 5. Reproduce\n```\npython results_remote/scripts/analyze_deploy_noise.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[deploy-noise] wrote", REPORT)
    print("[deploy-noise] sanity warm_n-rows:", "PASS" if not bad else "FAIL")


if __name__ == "__main__":
    main()
