"""
[RQ1-CMDP] tau-calibration helper.

The soft policy trajectory is tau-independent (in soft mode the cost critic is
trained but never used in the actor loss), so a single soft run lets us read off
the per-platoon AoI-violation rate P(AoI_j > tau) at ANY tau, for the last 100
training episodes, directly from AoI_evolution.mat
(shape = [n_platoon, 100, n_step_per_episode], per-step AoI for the last 100 ep).

Usage:
    python calibrate_tau.py                # scans all soft seeds found
    python calibrate_tau.py --mode soft    # explicit
"""
import os
import argparse
import numpy as np
import scipy.io

HERE = os.path.dirname(os.path.realpath(__file__))
MODEL_DIR = os.path.join(HERE, "..", "1-ModifiedMADDPGwithTDec", "model")

TAUS = [4, 5, 6, 7, 8, 9, 10]


def load_aoi_evolution(mode, seed):
    path = os.path.join(MODEL_DIR, "marl_model_%s_seed%d" % (mode, seed), "AoI_evolution.mat")
    if not os.path.exists(path):
        return None
    return scipy.io.loadmat(path)["AoI_evolution"].astype(np.float64)  # [P, 100, T]


def viol_at_tau(aoi_evo, tau):
    # mean over (last-100 episodes, steps) of 1{AoI > tau}, per platoon
    return np.mean(aoi_evo > tau, axis=(1, 2))  # [P]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="soft")
    ap.add_argument("--seeds", type=int, nargs="*", default=[2, 3, 4])
    args = ap.parse_args()

    found = []
    per_seed = {}
    for s in args.seeds:
        evo = load_aoi_evolution(args.mode, s)
        if evo is None:
            print("  (missing) %s seed %d" % (args.mode, s))
            continue
        found.append(s)
        per_seed[s] = evo
        nP = evo.shape[0]
        meanAoI = evo.mean(axis=(1, 2))
        p90 = np.percentile(evo, 90, axis=(1, 2))
        p95 = np.percentile(evo, 95, axis=(1, 2))
        print("\n=== %s seed %d  (last-100-ep per-step AoI, shape %s) ===" % (args.mode, s, evo.shape))
        print("  per-platoon mean AoI :", np.round(meanAoI, 2))
        print("  per-platoon p90  AoI :", np.round(p90, 2))
        print("  per-platoon p95  AoI :", np.round(p95, 2))
        for tau in TAUS:
            v = viol_at_tau(evo, tau)
            print("  tau=%2d  viol=%s  worst=%.3f (platoon %d)" %
                  (tau, np.round(v, 3), v.max(), int(v.argmax())))

    if len(found) >= 1:
        # average across seeds
        nP = per_seed[found[0]].shape[0]
        print("\n========== AVERAGE OVER SEEDS %s ==========" % found)
        print("%-6s | %-40s | %-8s | %-6s" % ("tau", "per-platoon viol (mean over seeds)", "worst", "mean"))
        for tau in TAUS:
            vs = np.stack([viol_at_tau(per_seed[s], tau) for s in found], axis=0)  # [n_seed, P]
            vmean = vs.mean(axis=0)
            print("tau=%-2d | %-40s | %.3f    | %.3f" %
                  (tau, np.round(vmean, 3), vmean.max(), vmean.mean()))
        print("\nBinding-regime guidance: pick the largest tau whose worst-platoon")
        print("viol is clearly > ~0.3 while the network MEAN stays modest (so the")
        print("average 'looks fine' but the worst platoon is starved).")


if __name__ == "__main__":
    main()
