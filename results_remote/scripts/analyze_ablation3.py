"""
[RQ1-CMDP #3] per-platoon vs GLOBAL multiplier ablation -- NUMBERS ONLY (no
conclusions; the operator cross-checks every value against the raw .mat).

For each (seed, scope) reports the FINAL-window (last-100-ep = ep[500,600) at 600 ep,
recomputed at tau=8 from AoI_evolution.mat via analyze_remote.metrics):
  - worst-platoon violation P(AoI>8)
  - network-mean violation
  - mean Tx power (dBm, network mean)
and the LAMBDA-EQUALITY sanity check: for every global_* run, all per-platoon columns
of lambda.mat must be EQUAL across platoons each episode (definition of a single
global multiplier). Reports the max |lambda_j - lambda_k| over all episodes/platoons.

Arms: glmean = marl_model_hard_seed{S}_t8e10_pid_ep600_glmean
      glmax  = marl_model_hard_seed{S}_t8e10_pid_ep600_glmax
      (per_platoon reference = existing marl_model_hard_seed{S}_t8e10_pid_ep600)
Outputs results_remote/RQ1_ABLATION3_GLOBAL_LAMBDA.md. Exit 2 if any global run
missing. No git.
"""
import os
import sys
import numpy as np
from analyze_remote import metrics, folder, _load

HERE = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
REPORT = os.path.join(HERE, "RQ1_ABLATION3_GLOBAL_LAMBDA.md")
SEEDS = [2, 3, 4, 5, 6, 7]
TAU = 8
SCOPES = [("glmean", "t8e10_pid_ep600_glmean"),
          ("glmax",  "t8e10_pid_ep600_glmax")]
REF = ("per_platoon", "t8e10_pid_ep600")


def row(seed, tag):
    mm = metrics("hard", seed, tag, TAU)
    if mm is None:
        return None
    return dict(worst=float(mm["viol"].max()),
                net=float(mm["viol"].mean()),
                power=float(np.mean(mm["power"])) if mm["power"] is not None else float("nan"))


def lam_equality(seed, tag):
    """max |lambda_j - lambda_k| over all episodes (0 => single global multiplier)."""
    lam = _load(os.path.join(folder("hard", seed, tag), "lambda.mat"), "lambda")
    if lam is None:
        return None
    lam = lam.astype(np.float64)                      # [P, nep]
    spread = lam.max(axis=0) - lam.min(axis=0)        # per-episode platoon spread
    return float(spread.max())


def main():
    missing = [(sc, s) for sc, tag in SCOPES for s in SEEDS
               if metrics("hard", s, tag, TAU) is None]
    if missing:
        sys.stderr.write("[ablation3] missing %d runs (e.g. %s) -- not writing report\n"
                         % (len(missing), missing[:4]))
        sys.exit(2)

    L = []; w = L.append
    w("# RQ1 ablation #3 — per-platoon vs single GLOBAL Lagrange multiplier\n")
    w("**Auto-generated on disk by `ablation3_driver.ps1` -> `analyze_ablation3.py`** "
      "(detached). NUMBERS ONLY; no conclusions drawn. Operator cross-checks the raw "
      "`.mat`.\n")
    w("Control arms replace per-platoon `lambda_j` with ONE global multiplier driven "
      "by network-MEAN (`global_mean`) or WORST (`global_max`) violation. Config "
      "matches the existing per-platoon PID ep600 runs byte-for-byte except "
      "`--lam_scope` + `--out_tag`: mode=hard tau=8 eps=0.10 dual=pid kp=1 ki=1 kd=0.5 "
      "lam_max=20 episodes=600, seeds {2-7}. FINAL window = last-100-ep (ep[500,600)), "
      "per-platoon violation recomputed at tau=8 from `AoI_evolution.mat`.\n")

    w("## 1. Per-(seed, scope) FINAL-window metrics\n")
    w("| seed | scope | worst-platoon viol | network-mean viol | mean Tx power (dBm) |")
    w("|---|---|---|---|---|")
    for s in SEEDS:
        for sc, tag in SCOPES:
            r = row(s, tag)
            w("| %d | %s | %.3f | %.3f | %.2f |" % (s, sc, r["worst"], r["net"], r["power"]))
    w("")
    w("Reference (existing per-platoon PID ep600, NOT re-run; shown for cross-check only):\n")
    w("| seed | scope | worst-platoon viol | network-mean viol | mean Tx power (dBm) |")
    w("|---|---|---|---|---|")
    for s in SEEDS:
        r = row(s, REF[1])
        if r is None:
            w("| %d | %s | n/a | n/a | n/a |" % (s, REF[0])); continue
        w("| %d | %s | %.3f | %.3f | %.2f |" % (s, REF[0], r["worst"], r["net"], r["power"]))
    w("")

    w("## 2. Lambda-equality sanity check (global_* must have identical lambda_j across platoons)\n")
    w("max |lambda_j - lambda_k| over ALL episodes & platoon pairs (0.0 => a single "
      "global multiplier, as required):\n")
    w("| seed | scope | max platoon spread of lambda | PASS (==0) |")
    w("|---|---|---|---|")
    all_pass = True
    for s in SEEDS:
        for sc, tag in SCOPES:
            sp = lam_equality(s, tag)
            ok = (sp is not None and sp == 0.0)
            all_pass = all_pass and ok
            w("| %d | %s | %s | %s |" %
              (s, sc, ("%.3e" % sp if sp is not None else "n/a"), "YES" if ok else "NO"))
    w("")
    w("**Lambda-equality overall: %s** (all global_* runs %s a single shared "
      "multiplier).\n" % ("PASS" if all_pass else "FAIL",
                          "use" if all_pass else "do NOT all use"))

    w("## 3. Reproduce\n```\npython analyze_ablation3.py\n```")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("[ablation3] wrote", REPORT)
    print("[ablation3] lambda-equality overall:", "PASS" if all_pass else "FAIL")


if __name__ == "__main__":
    main()
