"""
[RQ1-CMDP #4] Qu-style FIXED-WEIGHT threshold-penalty ablation -- NUMBERS ONLY
(no conclusions; the operator cross-checks every value against the raw .mat).

Arm: --mode soft --aoi_pen_type indicator --aoi_pen_w {w} --tau 8, ep600, seeds 2-7.
Same 1{AoI>tau} signal as the hard CMDP, but a FIXED reward weight and NO dual
(lambda stays 0). Run dirs: marl_model_soft_seed{S}_qind_w{w}_ep600.

For each (seed, w) reports the FINAL-window (last-100-ep = ep[500,600) at 600 ep,
recomputed at tau=8 from AoI_evolution.mat via analyze_remote.metrics):
  - worst-platoon violation P(AoI>8)
  - network-mean violation
  - mean Tx power (dBm, network mean)
and the LAMBDA==0 sanity check (soft mode => no dual ran): max |lambda| over the
whole lambda.mat MUST be 0 for every run.

Reference (existing, NOT re-run): soft base_ep600 (raw -AoI/20) and per-platoon hard
PID t8e10_pid_ep600, shown for cross-check only.
Outputs results_remote/RQ1_ABLATION4_FIXEDWEIGHT.md. Exit 2 if any qind run missing.
"""
import os
import sys
import numpy as np
from analyze_remote import metrics, folder, _load

# this script lives in results_remote/scripts/ -> HERE = results_remote/ (report root)
HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPORT = os.path.join(HERE, "RQ1_ABLATION4_FIXEDWEIGHT.md")
SEEDS = [2, 3, 4, 5, 6, 7]
WEIGHTS = [2, 5, 10, 20]
TAU = 8


def tag(w):
    return "qind_w%d_ep600" % w


def row(seed, w):
    mm = metrics("soft", seed, tag(w), TAU)
    if mm is None:
        return None
    return dict(worst=float(mm["viol"].max()),
                net=float(mm["viol"].mean()),
                power=float(np.mean(mm["power"])) if mm["power"] is not None else float("nan"))


def lam_absmax(seed, w):
    lam = _load(os.path.join(folder("soft", seed, tag(w)), "lambda.mat"), "lambda")
    if lam is None:
        return None
    return float(np.abs(lam.astype(np.float64)).max())


def ref_row(mode, seed, t):
    mm = metrics(mode, seed, t, TAU)
    if mm is None:
        return None
    return dict(worst=float(mm["viol"].max()), net=float(mm["viol"].mean()),
                power=float(np.mean(mm["power"])) if mm["power"] is not None else float("nan"))


def main():
    missing = [(w, s) for w in WEIGHTS for s in SEEDS if metrics("soft", s, tag(w), TAU) is None]
    if missing:
        sys.stderr.write("[ablation4] missing %d runs (e.g. %s) -- not writing report\n"
                         % (len(missing), missing[:4]))
        sys.exit(2)

    L = []; w_ = L.append
    w_("# RQ1 ablation #4 — Qu-style FIXED-WEIGHT threshold penalty (penalty, not constraint)\n")
    w_("**Auto-generated on disk by `scripts/ablation4_driver.ps1` -> "
       "`scripts/analyze_ablation4.py`** (detached). NUMBERS ONLY; no conclusions drawn. "
       "Operator cross-checks the raw `.mat`.\n")
    w_("Arm: `--mode soft --aoi_pen_type indicator --aoi_pen_w {w} --tau 8`, ep600, "
       "seeds {2-7}. Same `1{AoI>tau}` signal as the hard CMDP but a FIXED reward weight "
       "and NO dual (lambda stays 0). FINAL window = last-100-ep (ep[500,600)), "
       "per-platoon violation recomputed at tau=8 from `AoI_evolution.mat`. Run dirs: "
       "`marl_model_soft_seed{S}_qind_w{w}_ep600`.\n")

    w_("## 1. Per-(seed, w) FINAL-window metrics\n")
    w_("| seed | w | worst-platoon viol | network-mean viol | mean Tx power (dBm) |")
    w_("|---|---|---|---|---|")
    for wt in WEIGHTS:
        for s in SEEDS:
            r = row(s, wt)
            w_("| %d | %d | %.3f | %.3f | %.2f |" % (s, wt, r["worst"], r["net"], r["power"]))
    w_("")

    w_("## 2. Lambda==0 sanity (soft mode => no dual ran)\n")
    w_("max |lambda| over the WHOLE lambda.mat per run (MUST be 0.0):\n")
    w_("| seed | w | max|lambda| | PASS (==0) |")
    w_("|---|---|---|---|")
    all_zero = True
    for wt in WEIGHTS:
        for s in SEEDS:
            a = lam_absmax(s, wt)
            ok = (a is not None and a == 0.0)
            all_zero = all_zero and ok
            w_("| %d | %d | %s | %s |" % (s, wt, ("%.3e" % a if a is not None else "n/a"),
                                          "YES" if ok else "NO"))
    w_("")
    w_("**Lambda==0 overall: %s** (every #4 run is soft mode; no dual leaked in).\n"
       % ("PASS" if all_zero else "FAIL"))

    w_("## 3. Reference arms (existing, NOT re-run; cross-check only)\n")
    w_("| seed | arm | worst-platoon viol | network-mean viol | mean Tx power (dBm) |")
    w_("|---|---|---|---|---|")
    for s in SEEDS:
        rb = ref_row("soft", s, "base_ep600")           # raw -AoI/20 soft baseline
        rp = ref_row("hard", s, "t8e10_pid_ep600")      # per-platoon hard PID
        if rb: w_("| %d | soft_raw | %.3f | %.3f | %.2f |" % (s, rb["worst"], rb["net"], rb["power"]))
        if rp: w_("| %d | hard_pid | %.3f | %.3f | %.2f |" % (s, rp["worst"], rp["net"], rp["power"]))
    w_("")
    w_("## 4. Reproduce\n```\npython results_remote/scripts/analyze_ablation4.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[ablation4] wrote", REPORT)
    print("[ablation4] lambda==0 overall:", "PASS" if all_zero else "FAIL")


if __name__ == "__main__":
    main()
